from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import get_db
from routers.accounts import router as accounts_router
from routers.jobs import router as jobs_router
from scrape_user_id.router import router as scrape_router
from group_monitor.router import router as monitor_router
from mass_dm_bot.router import router as dm_bot_router
from mass_dm_account.router import router as dm_account_router
from auto_promo.router import router as auto_promo_router
from routers.auth import router as auth_router, get_current_user
from routers.proxies import router as proxies_router
from routers.admin import router as admin_router
from routers.subscriptions import router as subscriptions_router
from routers.health import router as health_router
from routers.templates import router as templates_router
from group_joiner.router import router as group_joiner_router
from core.session_manager import session_manager
from core.config import settings
from core.logging import setup_json_logging, get_logger, set_correlation_id

from models import TelegramAccount, MessageLog, UserInteraction

# Setup structured JSON logging
setup_json_logging(environment=settings.ENVIRONMENT, log_level="INFO")
logger = get_logger(__name__)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="TG Tools Backend", version="2.0.0")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to set correlation ID for request tracing
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    await set_correlation_id(request)
    response = await call_next(request)
    return response

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.url.path}")
    return {"detail": "Rate limit exceeded. Please try again later."}, 429

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup - JSON logging and rate limiting enabled")

@app.get("/")
def read_root():
    return {"message": "TG Tools Backend v2.0 is running"}

@app.get("/health")
@limiter.limit("100/minute")
def health_check(request: Request):
    return {"status": "ok", "version": "2.0.0"}

@app.get("/stats")
@limiter.limit("30/minute")
def system_stats(request: Request, db: Session = Depends(get_db)):
    active_accounts = db.query(TelegramAccount).filter(TelegramAccount.status == 'active').count()
    # System-wide sessions (total open clients)
    active_sessions = len(session_manager.active_clients)
    return {
        "active_sessions": active_sessions,
        "active_accounts": active_accounts,
        "system_status": "operational",
        "safety_features": {
            "rate_limiting": "active",
            "ban_prevention": "active",
            "cooldown_tracking": "active",
            "ai_integration": "available"
        }
    }

@app.get("/api/me/stats")
@limiter.limit("30/minute")
def my_stats(request: Request, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    # per-user active accounts - single query with count
    active_accounts = db.query(func.count(TelegramAccount.id)).filter(
        TelegramAccount.user_id == current_user.id, 
        TelegramAccount.status == 'active'
    ).scalar() or 0
    # per-user active sessions - single query, cache all account IDs
    user_account_ids = set([row[0] for row in db.query(TelegramAccount.id).filter(
        TelegramAccount.user_id == current_user.id
    ).all()])
    active_sessions = sum(1 for acc_id in session_manager.active_clients.keys() if acc_id in user_account_ids)
    return {"active_accounts": active_accounts, "active_sessions": active_sessions}

@app.get("/api/accounts/{account_id}/stats")
@limiter.limit("30/minute")
def account_stats(request: Request, account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Batch all message log queries into single query with GROUP BY
    message_stats = db.query(
        func.count(MessageLog.id).label('total'),
        func.sum(func.cast(MessageLog.delivery_status == 'sent', type_=type(1))).label('successful'),
        func.sum(func.cast(MessageLog.delivery_status == 'failed', type_=type(1))).label('failed')
    ).filter(MessageLog.telegram_account_id == account_id).first()
    
    total_messages = message_stats.total or 0
    successful_messages = message_stats.successful or 0
    failed_messages = message_stats.failed or 0
    unique_users = db.query(func.count(UserInteraction.id)).filter(UserInteraction.telegram_account_id == account_id).scalar() or 0
    success_rate = (successful_messages / total_messages * 100) if total_messages else 0.0
    
    return {
        "account_id": account_id,
        "nickname": account.nickname,
        "phone_number": account.phone_number,
        "status": account.status,
        "trust_score": account.trust_score,
        "statistics": {
            "total_messages": total_messages,
            "successful_messages": successful_messages,
            "failed_messages": failed_messages,
            "success_rate_percent": round(success_rate, 2),
            "unique_users_contacted": unique_users,
            "daily_message_count": account.daily_message_count
        },
        "dates": {
            "created_at": account.created_at,
            "last_activity": account.last_activity
        }
    }

# Include routers
app.include_router(accounts_router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(scrape_router, prefix="/api/scrape-users", tags=["Scrape User IDs"])
app.include_router(monitor_router, prefix="/api/group-monitor", tags=["Group Monitor"])
app.include_router(dm_bot_router, prefix="/api/mass-dm-bot", tags=["Mass DM Bot"])
app.include_router(dm_account_router, prefix="/api/mass-dm-account", tags=["Mass DM Account"])
app.include_router(auto_promo_router, prefix="/api/auto_promo", tags=["Auto Promo"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(proxies_router, prefix="/api/proxies", tags=["Proxies"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(templates_router)
app.include_router(health_router)  # Health router has its own prefix
app.include_router(group_joiner_router, prefix="/api/group-joiner", tags=["Group Joiner"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port="8000")