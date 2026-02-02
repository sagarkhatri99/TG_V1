from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import asyncio
import json

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
        # allow_unauth=True allows sending code for new accounts that aren't authorized yet
        client = await session_manager.get_client(account, allow_unauth=True)
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
        # allow_unauth=True since we're in the process of authorizing
        client = await session_manager.get_client(account, allow_unauth=True)
        
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


@router.get("/")
async def list_accounts_root(db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    """
    Alias for /list to support standard RESTful conventions
    """
    return await list_accounts(db, current_user)

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
            "created_at": account.created_at,
            "sleep_hour_start": account.sleep_hour_start,
            "sleep_hour_end": account.sleep_hour_end,
            "daily_message_limit": account.daily_message_limit,
            "proxy_id": account.proxy_id
        })
    # Return array directly, not wrapped in object
    return account_data


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
async def resume_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
        error_msg = str(e)
        if "api_id" in error_msg or "api_hash" in error_msg or "API credentials" in error_msg:
            error_msg = "Invalid or missing Telegram API credentials. Please ensure your account has valid api_id and api_hash configured."
        raise HTTPException(status_code=400, detail=f"Connection test failed: {error_msg}")
    finally:
        # Always disconnect after test
        await session_manager.disconnect_client(account_id)

@router.delete("/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("accounts"))):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    try:
        # Import all necessary models for deletion
        from models import (
            Campaign, CampaignUserInteraction, CampaignPendingTask,
            CampaignMessageTracking, CampaignReply, CampaignLog,
            MessageLog, ActionLog, AccountHealth, UserInteraction, Proxy
        )

        # 1. Delete campaign-related data in the correct order (children first)
        # Get all campaigns for this account
        campaign_ids = [c.id for c in db.query(Campaign).filter(Campaign.telegram_account_id == account_id).all()]

        if campaign_ids:
            # Get all interaction IDs for these campaigns
            interaction_ids = [i.id for i in db.query(CampaignUserInteraction).filter(CampaignUserInteraction.campaign_id.in_(campaign_ids)).all()]

            if interaction_ids:
                # Delete campaign logs related to interactions
                db.query(CampaignLog).filter(CampaignLog.campaign_user_interaction_id.in_(interaction_ids)).delete(synchronize_session=False)
                # Delete campaign replies
                db.query(CampaignReply).filter(CampaignReply.campaign_user_interaction_id.in_(interaction_ids)).delete(synchronize_session=False)
                # Delete campaign message tracking
                db.query(CampaignMessageTracking).filter(CampaignMessageTracking.campaign_user_interaction_id.in_(interaction_ids)).delete(synchronize_session=False)
                # Delete pending tasks
                db.query(CampaignPendingTask).filter(CampaignPendingTask.campaign_user_interaction_id.in_(interaction_ids)).delete(synchronize_session=False)

            # Delete campaign logs not tied to interactions
            db.query(CampaignLog).filter(CampaignLog.campaign_id.in_(campaign_ids)).delete(synchronize_session=False)
            # Delete campaign user interactions
            db.query(CampaignUserInteraction).filter(CampaignUserInteraction.campaign_id.in_(campaign_ids)).delete(synchronize_session=False)
            # Delete campaigns
            db.query(Campaign).filter(Campaign.telegram_account_id == account_id).delete(synchronize_session=False)

        # 2. Delete jobs
        db.query(Job).filter(Job.telegram_account_id == account_id).delete(synchronize_session=False)

        # 3. Delete message logs
        db.query(MessageLog).filter(MessageLog.telegram_account_id == account_id).delete(synchronize_session=False)

        # 4. Delete action logs
        db.query(ActionLog).filter(ActionLog.account_id == account_id).delete(synchronize_session=False)

        # 5. Delete account health
        db.query(AccountHealth).filter(AccountHealth.account_id == account_id).delete(synchronize_session=False)

        # 6. Delete user interactions
        db.query(UserInteraction).filter(UserInteraction.telegram_account_id == account_id).delete(synchronize_session=False)

        # 7. Clear proxy assignment (important: don't delete the proxy, just unassign it)
        db.query(Proxy).filter(Proxy.assigned_account_id == account_id).update(
            {"assigned_account_id": None},
            synchronize_session=False
        )

        # 8. Disconnect and remove the client session
        await session_manager.disconnect_client(account_id)

        # 9. Finally, delete the telegram account
        db.delete(account)
        db.commit()

        # 10. Delete the session file
        session_path = os.path.join("/app/sessions", f"account_{account_id}.session")
        if os.path.exists(session_path):
            os.remove(session_path)

        return {"status": "success", "message": "Account and all associated data deleted"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")

class AccountOperatingHours(BaseModel):
    sleep_hour_start: int  # 0-23
    sleep_hour_end: int    # 0-23
    daily_message_limit: Optional[int] = None

@router.patch("/{account_id}/operating-hours")
async def update_account_operating_hours(
    account_id: int,
    settings_data: AccountOperatingHours,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("accounts"))
):
    """Update account operating hours and daily limits (applies to all activities: Mass DM, Auto Promo, Campaigns)."""
    from services.campaign.account_status_cache import invalidate_account_cache

    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Validate sleep hours
    if not (0 <= settings_data.sleep_hour_start <= 23):
        raise HTTPException(status_code=400, detail="sleep_hour_start must be 0-23")
    if not (0 <= settings_data.sleep_hour_end <= 23):
        raise HTTPException(status_code=400, detail="sleep_hour_end must be 0-23")

    # Apply settings
    account.sleep_hour_start = settings_data.sleep_hour_start
    account.sleep_hour_end = settings_data.sleep_hour_end

    if settings_data.daily_message_limit is not None:
        account.daily_message_limit = settings_data.daily_message_limit
    
    db.commit()
    
    # Invalidate cache to force re-check
    invalidate_account_cache(account_id)

    return {
        "message": "Account operating hours updated successfully",
        "account_id": account_id,
        "updated_at": datetime.utcnow().isoformat(),
        "settings": {
            "sleep_hour_start": account.sleep_hour_start,
            "sleep_hour_end": account.sleep_hour_end,
            "daily_message_limit": account.daily_message_limit
        }
    }


@router.post("/import-sessions")
async def import_sessions(
    files: List[UploadFile] = File(...),
    proxy_mappings: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("accounts"))
):
    """
    Bulk import Telegram accounts from .session files and .json metadata.

    Expected files:
    - .session files (SQLite Telethon sessions)
    - .json files (metadata with app_id, app_hash, phone, etc.)

    Files are paired by basename (e.g., 6285641920523.session + 6285641920523.json)

    Optional proxy_mappings: JSON string mapping basename to proxy_id
    """
    from telethon import TelegramClient
    from telethon.sessions import SQLiteSession

    results = {"success": [], "errors": [], "summary": {}}

    # Parse proxy mappings if provided
    proxy_map = {}
    if proxy_mappings:
        try:
            proxy_map = json.loads(proxy_mappings)
        except:
            pass

    # Group files by basename
    session_files = {}
    json_files = {}

    for file in files:
        basename = file.filename.replace('.session', '').replace('.json', '')
        if file.filename.endswith('.session'):
            session_files[basename] = file
        elif file.filename.endswith('.json'):
            json_files[basename] = file

    # Process each session
    for basename, session_file in session_files.items():
        try:
            # 1. Save .session file permanently to backend/sessions/
            session_dir = "/app/sessions"
            os.makedirs(session_dir, exist_ok=True)
            session_path = os.path.join(session_dir, f"{basename}.session")

            with open(session_path, 'wb') as f:
                content = await session_file.read()
                f.write(content)

            # 2. Parse JSON metadata
            metadata = {}
            if basename in json_files:
                json_content = await json_files[basename].read()
                metadata = json.loads(json_content.decode('utf-8'))

            api_id = metadata.get('app_id')
            api_hash = metadata.get('app_hash')

            if not api_id or not api_hash:
                results["errors"].append({
                    "file": session_file.filename,
                    "error": "Missing app_id or app_hash in JSON metadata"
                })
                os.remove(session_path)  # Clean up
                continue

            # 3. Validate session (NO CONVERSION - just validate)
            client = TelegramClient(
                session_path.replace('.session', ''),
                int(api_id),
                api_hash
            )

            await client.connect()

            if not await client.is_user_authorized():
                results["errors"].append({
                    "file": session_file.filename,
                    "error": "Session expired or unauthorized"
                })
                await client.disconnect()
                os.remove(session_path)
                continue

            # Get user info
            me = await client.get_me()
            await client.disconnect()

            # 4. Check if account already exists
            phone = metadata.get('phone', basename)
            if not phone.startswith('+'):
                phone = f"+{phone}"

            existing = db.query(TelegramAccount).filter(
                TelegramAccount.phone_number == phone
            ).first()

            if existing:
                results["errors"].append({
                    "file": session_file.filename,
                    "error": f"Account with phone {phone} already exists"
                })
                os.remove(session_path)
                continue

            # 5. Create account record (store FILENAME, not converted session)
            proxy_id = proxy_map.get(basename) if basename in proxy_map else None

            account = TelegramAccount(
                user_id=current_user.id,
                phone_number=phone,
                api_id=str(api_id),
                api_hash=api_hash,
                session_string=basename,  # ✅ FILENAME ONLY (no conversion!)
                nickname=metadata.get('first_name', me.first_name or basename),
                proxy_id=proxy_id,  # Assign proxy if provided
                status='active',
                trust_score=random.randint(40, 70),
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )

            db.add(account)
            db.commit()
            db.refresh(account)

            results["success"].append({
                "phone": account.phone_number,
                "name": account.nickname,
                "account_id": account.id
            })

        except Exception as e:
            results["errors"].append({
                "file": session_file.filename,
                "error": str(e)
            })
            db.rollback()
            # Clean up session file on error
            session_path = os.path.join("/app/sessions", f"{basename}.session")
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                except:
                    pass

    results["summary"] = {
        "total_files": len(files),
        "imported": len(results["success"]),
        "failed": len(results["errors"])
    }

    return results
