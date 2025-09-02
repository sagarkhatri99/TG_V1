from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import get_db
import json
from pydantic import BaseModel
from .tasks import auto_promo_task

router = APIRouter()

from typing import Optional

class AutoPromoRequest(BaseModel):
    account_id: int
    target_group: str
    promo_message: str
    interval_seconds: Optional[int] = None
    use_random_interval: bool = False
    min_interval: Optional[int] = None
    max_interval: Optional[int] = None
    stop_after_hours: Optional[int] = None

@router.post("/create-job")
async def create_auto_promo_job(request: AutoPromoRequest, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == request.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if request.use_random_interval and (request.min_interval is None or request.max_interval is None):
        raise HTTPException(status_code=400, detail="min_interval and max_interval are required for random interval.")

    job_config = {
        "target_group": request.target_group,
        "promo_message": request.promo_message,
        "interval_seconds": request.interval_seconds,
        "use_random_interval": request.use_random_interval,
        "min_interval": request.min_interval,
        "max_interval": request.max_interval,
        "stop_after_hours": request.stop_after_hours,
    }

    new_job = Job(
        telegram_account_id=request.account_id,
        job_type='auto_promo',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    auto_promo_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Auto promo job created successfully."}

# Old endpoints are now deprecated.
# from fastapi import Form
# from .service import start_auto_promo_auth, verify_and_start_promo

# @router.post("/start-auth")
# async def start_auth(
#     api_id: int = Form(...),
#     api_hash: str = Form(...),
#     phone_number: str = Form(...)
# ):
#     try:
#         await start_auto_promo_auth(api_id, api_hash, phone_number)
#         return {"success": True, "message": "OTP sent to your phone"}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/start")
# async def start_promo(
#     api_id: int = Form(...),
#     api_hash: str = Form(...),
#     phone_number: str = Form(...),
#     otp: str = Form(...),
#     target_group: str = Form(...),
#     promo_message: str = Form(...),
#     interval_seconds: int = Form(...)
# ):
#     try:
#         result = await verify_and_start_promo(
#             api_id, api_hash, phone_number, otp,
#             target_group, promo_message, interval_seconds
#         )
#         return {"message": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
