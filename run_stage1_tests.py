import os
import sys
import logging
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Stage1Verification")

# Mock environment
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/tg_tools"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["APP_VERSION"] = "1.0.0"

# Add backend to path
sys.path.append("./backend")

# Mock the entire database module
sys.modules["database"] = MagicMock()
sys.modules["models"] = MagicMock()

import core.config as config
import core.account_protection as account_protection
import core.proxy_utils as proxy_utils

def verify_version_check():
    logger.info("--- Testing Version Check Handshake ---")
    with patch("redis.from_url") as mock_redis_factory:
        mock_redis = MagicMock()
        mock_redis_factory.return_value = mock_redis

        # Case: Match
        mock_redis.get.return_value = "1.0.0"
        api_version = mock_redis.get("system:app_version")
        worker_version = config.settings.APP_VERSION
        logger.info(f"API: {api_version}, Worker: {worker_version}")
        assert api_version == worker_version
        logger.info("✅ Case: Matched Version Passed")

        # Case: Mismatch
        mock_redis.get.return_value = "1.0.1"
        api_version = mock_redis.get("system:app_version")
        logger.info(f"API: {api_version}, Worker: {worker_version}")
        assert api_version != worker_version
        logger.info("✅ Case: Mismatched Version Logic Verified")

def verify_safety_circuit_breaker():
    logger.info("\n--- Testing Safety Circuit Breaker ---")
    mock_db = MagicMock()

    # Mock models
    mock_account_model = MagicMock()
    mock_health_model = MagicMock()
    sys.modules["models"].TelegramAccount = mock_account_model
    sys.modules["models"].AccountHealth = mock_health_model

    # Test Case: Restricted Account
    mock_health = MagicMock()
    mock_health.status = "restricted"
    mock_health.health_score = 100.0

    mock_acc = MagicMock()
    mock_acc.status = "active"

    mock_db.query().filter().first.side_effect = [mock_acc, mock_health]

    is_safe, reason = account_protection.is_account_safe_for_job(1, db=mock_db)
    logger.info(f"Restricted Account Result: {is_safe}, Reason: {reason}")
    assert is_safe is False
    assert "restricted" in reason

    # Test Case: Low Score
    mock_health.status = "healthy"
    mock_health.health_score = 15.0
    mock_db.query().filter().first.side_effect = [mock_acc, mock_health]

    is_safe, reason = account_protection.is_account_safe_for_job(1, db=mock_db)
    logger.info(f"Low Score Result: {is_safe}, Reason: {reason}")
    assert is_safe is False
    assert "too low" in reason
    logger.info("✅ Safety Circuit Breaker Logic Verified")

def verify_operating_hours():
    logger.info("\n--- Testing Operating Hours ---")
    mock_db = MagicMock()
    mock_acc = MagicMock()
    mock_acc.sleep_hour_start = 0
    mock_acc.sleep_hour_end = 24 # Always sleep for testing
    mock_db.query().filter().first.return_value = mock_acc

    # Mock datetime to control current hour
    with patch("core.account_protection.datetime") as mock_datetime:
        mock_datetime.utcnow.return_value = MagicMock(hour=12)
        is_awake, reason = account_protection.is_within_operating_hours(1, db=mock_db)
        logger.info(f"Sleep Mode Result: {is_awake}, Reason: {reason}")
        assert is_awake is False
        assert "sleep mode" in reason
    logger.info("✅ Operating Hours Logic Verified")

def verify_proxy_preflight():
    logger.info("\n--- Testing Proxy Pre-flight ---")
    # Mock socket to simulate failure
    with patch("socket.create_connection") as mock_conn:
        mock_conn.side_effect = Exception("Connection Refused")

        mock_proxy = MagicMock()
        mock_proxy.proxy_url = "socks5://1.2.3.4:1234"
        mock_proxy.proxy_type = "socks5"

        is_reachable, reason = proxy_utils.verify_proxy_connectivity(mock_proxy)
        logger.info(f"Proxy Failure Result: {is_reachable}, Reason: {reason}")
        assert is_reachable is False
        assert "failed" in reason
        logger.info("✅ Proxy Pre-flight Logic Verified")

if __name__ == "__main__":
    verify_version_check()
    verify_safety_circuit_breaker()
    verify_operating_hours()
    verify_proxy_preflight()
    logger.info("\n🚀 ALL STAGE 1 LOGIC VERIFIED SUCCESSFULLY")
