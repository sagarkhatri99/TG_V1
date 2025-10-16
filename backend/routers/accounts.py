from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import asyncio

from database import get_db
from models import TelegramAccount, Job, User
from core.session_manager import session_manager
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
from core.ban_prevention import ban_prevention
from datetime import datetime
import random

router = APIRouter()

class AccountCreate(BaseModel):
    nickname: str
    phone_number: str
    api_id: int
    api_hash: str
    
class AccountUpdate(BaseModel):
    nickname: Optional[str] = None
    phone_number: Optional[str] = None
    api_id: Optional[int] = None
    api_hash: Optional[str] = None

@router.post("/create")
async def create_account(
    api_id: int = Form(...),
    api_hash: str = Form(...),
    phone_number: str = Form(...),
    nickname: str = Form(...),
    proxy_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("accounts"))
):
    # Subscription plan limits
    if current_user.subscription_plan != 'enterprise':
        ACCOUNT_LIMITS = {
            "free": 1,
            "pro": 5,
        }
        account_limit = ACCOUNT_LIMITS.get(current_user.subscription_plan, 0)
        user_accounts_count = db.query(TelegramAccount).filter(TelegramAccount.user_id == current_user.id).count()
        if user_accounts_count >= account_limit:
            raise HTTPException(status_code=403, detail=f"Account limit of {account_limit} reached for your plan.")

    existing = db.query(TelegramAccount).filter(TelegramAccount.phone_number == phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="This phone number is already registered.")

    account = TelegramAccount(
        user_id=current_user.id,
        phone_number=phone_number,
        api_id=str(api_id),
        api_hash=api_hash,
        nickname=nickname,
        proxy_id=proxy_id,
        status='pending_verification',
        trust_score=random.randint(30, 60),
        created_at=datetime.utcnow()
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"account_id": account.id, "status": "created", "next_step": "verify_phone"}

class AccountUpdate(BaseModel):
    proxy_id: Optional[int] = None
    nickname: Optional[str] = None

@router.patch("/{account_id}", response_model=AccountUpdate)
async def update_account(account_id: int, account_update: AccountUpdate, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    if account_update.proxy_id is not None:
        account.proxy_id = account_update.proxy_id
    if account_update.nickname is not None:
        account.nickname = account_update.nickname

    db.commit()
    db.refresh(account)
    return account

@router.post("/{account_id}/send-code")
async def send_verification_code(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    try:
        # Get a cached client to maintain the auth state
        client = await session_manager.get_client(account)
        await client.send_code_request(account.phone_number)
        # Add a small delay to allow for network operations like DC migration
        await asyncio.sleep(1)
        return {"status": "code_sent", "message": "OTP sent to your phone"}
    except Exception as e:
        # If something goes wrong, disconnect to ensure a fresh start next time
        await session_manager.disconnect_client(account_id)
        raise HTTPException(status_code=400, detail=f"Failed to send code: {str(e)}")

@router.post("/{account_id}/verify")
async def verify_account(account_id: int, otp_code: str = Form(...), password: Optional[str] = Form(None), db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    try:
        # Get the same cached client that sent the code
        client = await session_manager.get_client(account)
        
        if password:
            await client.sign_in(phone=account.phone_number, code=otp_code, password=password)
        else:
            await client.sign_in(phone=account.phone_number, code=otp_code)
        
        # On success, perform connection test to verify account is working
        try:
            # Test connection immediately after verification
            me = await client.get_me()
            if me:
                account.status = 'active'
                account.last_activity = datetime.utcnow()
                db.commit()
                await session_manager.disconnect_client(account_id)
                return {
                    "status": "verified", 
                    "account_id": account.id,
                    "connection_test": "passed",
                    "user_info": {
                        "user_id": me.id,
                        "username": me.username,
                        "first_name": me.first_name
                    }
                }
            else:
                account.status = 'error'
                db.commit()
                await session_manager.disconnect_client(account_id)
                return {
                    "status": "verified_but_connection_failed", 
                    "account_id": account.id,
                    "message": "Account verified but connection test failed"
                }
        except Exception as test_error:
            # If connection test fails, still mark as verified but with error status
            account.status = 'error'
            account.last_activity = datetime.utcnow()
            db.commit()
            await session_manager.disconnect_client(account_id)
            return {
                "status": "verified_but_connection_failed", 
                "account_id": account.id,
                "message": f"Account verified but connection test failed: {str(test_error)}"
            }
    except Exception as e:
        # If verification fails, disconnect to ensure a fresh start next time
        await session_manager.disconnect_client(account_id)
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")


@router.get("/list")
async def list_accounts(db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    accounts = db.query(TelegramAccount).filter(TelegramAccount.user_id == current_user.id).all()
    account_data = []
    for account in accounts:
        try:
            risk_score = await ban_prevention.assess_account_risk(account, db)
        except:
            risk_score = 0.0
        account_data.append({
            "id": account.id,
            "nickname": account.nickname,
            "phone_number": account.phone_number,
            "status": account.status,
            "trust_score": account.trust_score,
            "risk_score": risk_score,
            "last_activity": account.last_activity,
            "daily_message_count": account.daily_message_count,
            "created_at": account.created_at
        })
    return {"accounts": account_data}

@router.post("/{account_id}/test")
async def test_account_connection(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    try:
        client = await session_manager.get_client(account)
        async with client:
            me = await client.get_me()
        
        account.last_activity = datetime.utcnow()
        db.commit()
        
        if me:
            return {"status": "connected", "user_id": me.id, "username": me.username, "first_name": me.first_name}
        else:
            raise HTTPException(status_code=400, detail="Connection test failed: Could not get user info.")
    except Exception as e:
        account.status = 'error'
        db.commit()
        raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")
    finally:
        # Always disconnect after a test to avoid leaving a stale client in the cache
        await session_manager.disconnect_client(account_id)

@router.post("/{account_id}/pause")
async def pause_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    account.status = 'paused'
    db.commit()
    
    from models import Job
    running_jobs = db.query(Job).filter(
        Job.telegram_account_id == account_id,
        Job.status.in_(['pending', 'running'])
    ).all()
    for job in running_jobs:
        job.status = 'paused'
    db.commit()
    return {"status": "paused", "jobs_affected": len(running_jobs)}

@router.post("/{account_id}/resume")
async def resume_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    # Test connection before resuming
    try:
        client = await session_manager.get_client(account)
        async with client:
            me = await client.get_me()
        
        if me:
            account.status = 'active'
            account.last_activity = datetime.utcnow()
            db.commit()
            return {
                "status": "resumed", 
                "connection_test": "passed",
                "user_info": {
                    "user_id": me.id, 
                    "username": me.username, 
                    "first_name": me.first_name
                }
            }
        else:
            account.status = 'error'
            db.commit()
            raise HTTPException(status_code=400, detail="Connection test failed: Could not get user info")
    except Exception as e:
        account.status = 'error'
        db.commit()
        raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")
    finally:
        # Always disconnect after test
        await session_manager.disconnect_client(account_id)

@router.delete("/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    # Delete associated jobs
    db.query(Job).filter(Job.telegram_account_id == account_id).delete()
    
    # Disconnect and remove the client session
    await session_manager.disconnect_client(account_id)
    
    # Delete the account from DB
    db.delete(account)
    db.commit()
    
    # Delete the session file
    session_path = os.path.join("/app/sessions", f"account_{account_id}.session")
    if os.path.exists(session_path):
        os.remove(session_path)
        
    return {"status": "success", "message": "Account and all associated data deleted"}