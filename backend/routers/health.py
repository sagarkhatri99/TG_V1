from fastapi import APIRouter, Depends
from sqlalchemy import text
from celery import current_app as celery_app
from database import get_db
import redis
import os

router = APIRouter(prefix="/api/health", tags=["health"])

redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

@router.get("/diagnose")
def diagnose():
    checks = {"status": "healthy", "checks": {}}

    # Redis check
    try:
        redis_client.ping()
        checks["checks"]["redis"] = "ok"
    except Exception as e:
        checks["checks"]["redis"] = {"status": "failed", "error": str(e)}
        checks["status"] = "unhealthy"

    # Database check
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        checks["checks"]["db"] = "ok"
    except Exception as e:
        checks["checks"]["db"] = {"status": "failed", "error": str(e)}
        checks["status"] = "unhealthy"

    # Celery broker check
    try:
        celery_app.connection().ensure_connection(max_retries=3)
        checks["checks"]["celery_broker"] = "ok"
    except Exception as e:
        checks["checks"]["celery_broker"] = {"status": "failed", "error": str(e)}
        checks["status"] = "unhealthy"

    # Workers check (CRITICAL: Check for campaign worker)
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()

        if not active:
            checks["checks"]["workers"] = {"status": "warning", "message": "No workers found"}
            checks["status"] = "degraded"
        else:
            has_campaign_worker = any('campaign' in str(w).lower() for w in active.keys())
            checks["checks"]["workers"] = {
                "status": "ok",
                "active_workers": list(active.keys()),
                "has_campaign_worker": has_campaign_worker
            }

            if not has_campaign_worker:
                checks["status"] = "degraded"
                checks["checks"]["workers"]["warning"] = "campaign worker not found"

    except Exception as e:
        checks["checks"]["workers"] = {"status": "failed", "error": str(e)}
        checks["status"] = "unhealthy"

    return checks
