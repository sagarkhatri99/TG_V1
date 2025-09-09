from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import get_db
import json
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
from .tasks import group_monitor_task

router = APIRouter()

class GroupMonitorRequest(BaseModel):
    account_id: int
    group_usernames: List[str]
    keywords: List[str]
    monitored_users: List[str]
    limit: int = 100

@router.post("/create-job")
async def create_group_monitor_job(request: GroupMonitorRequest, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == request.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    job_config = {
        "group_usernames": request.group_usernames,
        "keywords": request.keywords,
        "monitored_users": request.monitored_users,
        "limit": request.limit
    }

    new_job = Job(
        telegram_account_id=request.account_id,
        job_type='group_monitor',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    group_monitor_task.delay(new_job.id)

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

