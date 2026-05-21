from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from database import get_db
from routers.auth import get_current_user
from celery_app import celery_app
from datetime import datetime, timedelta
from core.dm_health_policy import get_tier_policy
from models import AccountHealth, TelegramAccount, User, MessageLog, Job
import redis
import os
import json

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
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)

    for account in accounts:
        # 1. Get health record
        health = db.query(AccountHealth).filter(AccountHealth.account_id == account.id).first()
        if not health:
            health = AccountHealth(account_id=account.id, health_score=100.0, status="healthy", error_history=[])
            db.add(health)
            db.commit()
            db.refresh(health)

        # 2. Aggregations from MessageLog (Actual outcome truth)
        msg_counts = db.query(
            func.count(MessageLog.id).filter(MessageLog.timestamp >= hour_ago, MessageLog.delivery_status == 'sent').label('hour_sent'),
            func.count(MessageLog.id).filter(MessageLog.timestamp >= day_ago, MessageLog.delivery_status == 'sent').label('day_sent')
        ).filter(MessageLog.telegram_account_id == account.id).first()

        # 3. Active Job and Lock Info
        lock_holder = redis_client.get(f"lock:account:{account.id}")
        active_job = db.query(Job).filter(
            Job.telegram_account_id == account.id,
            Job.status == "running"
        ).first()

        # 4. Policy Info
        tier = getattr(account, 'account_trust_tier', 'warming') or 'warming'
        policy = get_tier_policy(tier)
        
        # 5. Recommendation Logic
        recommendation = "Normal operations. Monitor health score."
        if health.health_score < 80:
            recommendation = "Health score low. Consider increasing delays or pausing cold outreach."
        if health.flood_wait_count > 2:
            recommendation = "Multiple flood waits detected. Manual rest recommended."
        if tier == 'new':
            recommendation = "New account. Keep daily volume under 20 DMs."

        # 6. Error Summary
        error_summary = ""
        if active_job and active_job.error_message:
            error_summary = active_job.error_message
        elif health.error_history:
            # Latest error from history
            try:
                history = health.error_history if isinstance(health.error_history, list) else json.loads(health.error_history)
                if history:
                    error_summary = history[-1].get('error', '')
            except:
                pass

        health_data.append({
            "id": health.id,
            "account_id": account.id,
            "account_nickname": account.nickname,
            "account_phone": account.phone_number,
            "trust_tier": tier,
            "warmup_stage": account.warmup_stage,
            "health_score": health.health_score,
            "status": health.status,
            "messages_sent_hour": msg_counts.hour_sent if msg_counts else 0,
            "messages_sent_today": msg_counts.day_sent if msg_counts else 0,
            "enforced_min_delay": policy.min_delay,
            "enforced_max_delay": policy.max_delay,
            "active_job_id": active_job.id if active_job else None,
            "active_job_type": active_job.job_type if active_job else None,
            "lock_holder": lock_holder,
            "is_restricted": health.is_restricted,
            "last_activity": health.last_activity,
            "latest_error_summary": error_summary,
            "recommendation_reason": recommendation,
            "api_calls_today": health.api_calls_today,
            "flood_wait_count": health.flood_wait_count,
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
