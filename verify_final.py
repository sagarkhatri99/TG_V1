import sys
import os
from unittest.mock import MagicMock

sys.path.append("./backend")
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"

def test_imports():
    print("Testing imports...")
    from core.config import settings
    from core.account_protection import is_account_safe_for_job, is_within_operating_hours
    from core.proxy_utils import verify_proxy_connectivity
    from mass_dm_account.tasks import mass_dm_account_task
    from auto_promo.tasks import auto_promo_task
    from group_joiner.tasks import group_join_task
    from group_monitor.tasks import group_monitor_task
    from scrape_user_id.tasks import scrape_users_task
    print("✅ All imports successful.")

if __name__ == "__main__":
    test_imports()
