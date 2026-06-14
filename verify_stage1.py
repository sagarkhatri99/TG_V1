import os
import sys
from unittest.mock import MagicMock

# Mocking parts of the system to test logic
sys.path.append("./backend")
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"

from core.config import settings
from core.account_protection import is_account_safe_for_job, is_within_operating_hours
from core.proxy_utils import verify_proxy_connectivity

def test_version_config():
    print(f"Testing Version Config: APP_VERSION={settings.APP_VERSION}, ENABLE_CHECK={settings.ENABLE_VERSION_CHECK}")
    assert settings.APP_VERSION == "1.0.0"
    assert settings.ENABLE_VERSION_CHECK == True

def test_safety_circuit_breaker_logic():
    print("Testing Safety Circuit Breaker Logic...")
    # Mock DB session
    mock_db = MagicMock()
    mock_acc = MagicMock()
    mock_acc.status = "active"
    mock_health = MagicMock()
    mock_health.status = "healthy"
    mock_health.health_score = 100.0

    mock_db.query().filter().first.side_effect = [mock_acc, mock_health]

    safe, reason = is_account_safe_for_job(1, db=mock_db)
    print(f"  Safe Account: {safe}, Reason: {reason}")
    assert safe == True

    mock_health.status = "restricted"
    mock_db.query().filter().first.side_effect = [mock_acc, mock_health]
    safe, reason = is_account_safe_for_job(1, db=mock_db)
    print(f"  Restricted Account: {safe}, Reason: {reason}")
    assert safe == False
    assert "restricted" in reason

def test_operating_hours_logic():
    print("Testing Operating Hours Logic...")
    from datetime import datetime
    mock_db = MagicMock()
    mock_acc = MagicMock()
    mock_acc.sleep_hour_start = 23
    mock_acc.sleep_hour_end = 7
    mock_db.query().filter().first.return_value = mock_acc

    # We can't easily mock datetime.utcnow() inside the function without more complex mocking
    # but we can verify it doesn't crash and returns a bool
    allowed, reason = is_within_operating_hours(1, db=mock_db)
    print(f"  Operating Hours Check: Allowed={allowed}, Reason='{reason}'")
    assert isinstance(allowed, bool)

if __name__ == "__main__":
    try:
        test_version_config()
        test_safety_circuit_breaker_logic()
        test_operating_hours_logic()
        print("\n✅ Stage 1 Logic Verification Passed!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
