from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from celery import current_app as celery_app
from database import get_db
from models import AccountHealth, TelegramAccount, User
from routers.auth import get_current_user
import redis
import os

router = APIRouter(prefix="/api/health", tags=["health"])

redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

@router.get("/accounts")
async def get_account_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get health data for all user's accounts"""
    # Get all accounts for current user
    accounts = db.query(TelegramAccount).filter(
        TelegramAccount.user_id == current_user.id
    ).all()
    
    health_data = []
    for account in accounts:
        # Get or create health record
        health = db.query(AccountHealth).filter(
            AccountHealth.account_id == account.id
        ).first()
        
        if not health:
            # Create default health record if doesn't exist
            health = AccountHealth(
                account_id=account.id,
                health_score=100.0,
                status="healthy",
                messages_sent_today=0,
                groups_joined_today=0,
                api_calls_today=0,
                flood_wait_count=0,
                spam_error_count=0,
                auth_error_count=0,
                generic_error_count=0,
                is_restricted=False,
                error_history=[]
            )
            db.add(health)
            db.commit()
            db.refresh(health)
        
        health_data.append({
            "id": health.id,
            "account_id": account.id,
            "account_nickname": account.nickname,
            "account_phone": account.phone_number,
            "health_score": health.health_score,
            "status": health.status,
            "messages_sent_today": health.messages_sent_today,
            "groups_joined_today": health.groups_joined_today,
            "api_calls_today": health.api_calls_today,
            "flood_wait_count": health.flood_wait_count,
            "spam_error_count": health.spam_error_count,
            "auth_error_count": health.auth_error_count,
            "generic_error_count": health.generic_error_count,
            "is_restricted": health.is_restricted,
            "restriction_reason": health.restriction_reason,
            "restriction_until": health.restriction_until,
            "last_activity": health.last_activity,
            "last_error_time": health.last_error_time,
            "error_history": health.error_history or []
        })
    
    return health_data

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

    # Workers check
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()

        if not active:
            checks["checks"]["workers"] = {"status": "warning", "message": "No workers found"}
            checks["status"] = "degraded"
        else:
            checks["checks"]["workers"] = {
                "status": "ok",
                "active_workers": list(active.keys())
            }

    except Exception as e:
        checks["checks"]["workers"] = {"status": "failed", "error": str(e)}
        checks["status"] = "unhealthy"

    return checks
