from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os

from database import get_db
from models import TelegramAccount, Job
from core.session_manager import session_manager
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
    db: Session = Depends(get_db)
):
    existing = db.query(TelegramAccount).filter(TelegramAccount.phone_number == phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account already exists")

    account = TelegramAccount(
        phone_number=phone_number,
        api_id=str(api_id),
        api_hash=api_hash,
        nickname=nickname,
        status='pending_verification',
        trust_score=random.randint(30, 60),
        created_at=datetime.utcnow()
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"account_id": account.id, "status": "created", "next_step": "verify_phone"}

@router.post("/{account_id}/send-code")
async def send_verification_code(account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        client = await session_manager.get_client(account)
        await client.connect()
        await client.send_code_request(account.phone_number)
        return {"status": "code_sent", "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to send code: {str(e)}")

@router.post("/{account_id}/verify")
async def verify_account(account_id: int, otp_code: str = Form(...), db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        client = await session_manager.get_client(account)
        await client.sign_in(phone=account.phone_number, code=otp_code)
        account.session_string = client.session.save()
        account.status = 'active'
        account.last_activity = datetime.utcnow()
        db.commit()
        return {"status": "verified", "account_id": account.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")

@router.get("/list")
async def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(TelegramAccount).all()
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
async def test_account_connection(account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        client = await session_manager.get_client(account)
        await client.connect()
        me = await client.get_me()
        account.last_activity = datetime.utcnow()
        db.commit()
        return {
            "status": "connected",
            "user_id": me.id,
            "username": me.username,
            "first_name": me.first_name
        }
    except Exception as e:
        account.status = 'error'
        db.commit()
        raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")

@router.post("/{account_id}/pause")
async def pause_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

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
async def resume_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.status = 'active'
    db.commit()
    return {"status": "resumed"}

@router.delete("/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Delete associated jobs
    db.query(Job).filter(Job.telegram_account_id == account_id).delete()

    # Delete the account
    db.delete(account)
    db.commit()

    # Delete the session file
    session_path = os.path.join("/app/sessions", f"account_{account_id}.session")
    if os.path.exists(session_path):
        os.remove(session_path)

    return {"status": "success", "message": "Account and all associated data deleted"}
