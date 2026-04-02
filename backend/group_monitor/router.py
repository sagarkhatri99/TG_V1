from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from .tasks import group_monitor_task
from datetime import datetime, timedelta
import os

router = APIRouter()

class GroupMonitorRequest(BaseModel):
    account_id: int
    group_usernames: List[str]
    keywords: List[str]
    monitored_users: List[str]
    limit: int = 100
    days: Optional[int] = None  # Number of days back to include (e.g., 1 or 7)
    scheduled_at: Optional[str] = None  # ISO8601 datetime string for deferred start

@router.post("/create-job")
async def create_group_monitor_job(request: GroupMonitorRequest, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("monitor"))):
    if current_user.subscription_plan == 'pro':
        if current_user.job_counter_last_reset < datetime.utcnow() - timedelta(days=30):
            current_user.jobs_created_this_month = 0
            current_user.job_counter_last_reset = datetime.utcnow()
            db.commit()
        if current_user.jobs_created_this_month >= 500:
            raise HTTPException(status_code=403, detail="You have reached your monthly job limit of 500.")

    account = db.query(TelegramAccount).filter(TelegramAccount.id == request.account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")
    if account.status != 'active':
        raise HTTPException(status_code=400, detail="Selected Telegram account is not verified/active.")

    job_config = {
        "group_usernames": request.group_usernames,
        "keywords": request.keywords,
        "monitored_users": request.monitored_users,
        "limit": request.limit,
        "days": request.days if request.days in [1, 7] else None
    }

    # Parse scheduled_at if provided
    scheduled_at_dt = None
    if request.scheduled_at:
        try:
            scheduled_at_dt = datetime.fromisoformat(request.scheduled_at.replace('Z', '+00:00'))
            if scheduled_at_dt.tzinfo is not None:
                import pytz
                scheduled_at_dt = scheduled_at_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at format. Use ISO8601, e.g. 2026-03-20T10:00:00Z")

    is_scheduled = scheduled_at_dt is not None and scheduled_at_dt > datetime.utcnow()
    initial_status = 'scheduled' if is_scheduled else 'pending'

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=request.account_id,
        job_type='group_monitor',
        config=json.dumps(job_config),
        status=initial_status,
        scheduled_at=scheduled_at_dt
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Only dispatch immediately if not scheduled for later
    if not is_scheduled:
        group_monitor_task.delay(new_job.id)

    if current_user.subscription_plan == 'pro':
        current_user.jobs_created_this_month += 1
        db.commit()

    return {"job_id": new_job.id, "message": "Group monitor job created successfully."}

# The old endpoints are now deprecated.
# I am commenting them out for now, in case I need to refer to them.

# from .service import start_monitor_auth, verify_monitor_otp_and_monitor
# class StartMonitorAuthRequest(BaseModel):
#     api_id: int
#     api_hash: str
#     phone_number: str

# class VerifyMonitorRequest(BaseModel):
#     api_id: int
#     api_hash: str
#     phone_number: str
#     code: str
#     group_usernames: List[str]
#     keywords: List[str]
#     monitored_users: List[str]
#     limit: Optional[int] = 100

# @router.post("/start-auth")
# async def start_auth(request: StartMonitorAuthRequest):
#     try:
#         await start_monitor_auth(request.api_id, request.api_hash, request.phone_number)
#         return {"success": True, "message": "OTP sent to your phone"}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/verify-monitor")
# async def verify_monitor(request: VerifyMonitorRequest):
#     try:
#         result = await verify_monitor_otp_and_monitor(
#             request.api_id,
#             request.api_hash,
#             request.phone_number,
#             request.code,
#             request.group_usernames,
#             request.keywords,
#             request.monitored_users,
#             request.limit or 100
#         )
#         return {"message": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
def download_csv(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("monitor"))):
    job = db.query(Job).join(TelegramAccount).filter(Job.id == job_id, TelegramAccount.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")

    filename = f"/app/job_results/monitored_messages_job_{job_id}.csv"

    # Allow downloading partial results if the file exists, regardless of job status
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Result file not found.")

    def file_iterator(file_path, chunk_size=8192):
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except FileNotFoundError:
            raise

    try:
        from os.path import basename
        return StreamingResponse(
            file_iterator(filename),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={basename(filename)}"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result file not found.")
