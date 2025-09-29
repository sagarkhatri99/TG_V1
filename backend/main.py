from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging

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
from core.session_manager import session_manager

from models import TelegramAccount, MessageLog, UserInteraction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TG Tools Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Database setup is handled by Alembic in entrypoint.sh")

@app.get("/")
def read_root():
    return {"message": "TG Tools Backend v2.0 is running"}

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/stats")
def system_stats(db: Session = Depends(get_db)):
    active_accounts = db.query(TelegramAccount).filter(TelegramAccount.status == 'active').count()
    # System-wide sessions (total open clients)
    active_sessions = len(session_manager.active_clients)
    db.close()
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
def my_stats(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    # per-user active accounts
    active_accounts = db.query(TelegramAccount).filter(TelegramAccount.user_id == current_user.id, TelegramAccount.status == 'active').count()
    # per-user active sessions (intersection of client's active account ids)
    user_account_ids = set([row.id for row in db.query(TelegramAccount.id).filter(TelegramAccount.user_id == current_user.id).all()])
    active_sessions = sum(1 for acc_id in session_manager.active_clients.keys() if acc_id in user_account_ids)
    db.close()
    return {"active_accounts": active_accounts, "active_sessions": active_sessions}

@app.get("/api/accounts/{account_id}/stats")
def account_stats(account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    total_messages = db.query(MessageLog).filter(MessageLog.telegram_account_id == account_id).count()
    successful_messages = db.query(MessageLog).filter(MessageLog.telegram_account_id == account_id, MessageLog.delivery_status == 'sent').count()
    failed_messages = db.query(MessageLog).filter(MessageLog.telegram_account_id == account_id, MessageLog.delivery_status == 'failed').count()
    unique_users = db.query(UserInteraction).filter(UserInteraction.telegram_account_id == account_id).count()
    success_rate = (successful_messages / total_messages * 100) if total_messages else 0.0
    db.close()
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port="8000")