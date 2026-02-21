from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from typing import Optional
import os
import shutil
from .tasks import auto_promo_task
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/create-job")
async def create_auto_promo_job(
    account_id: int = Form(...),
    target_group: str = Form(...),
    promo_message: Optional[str] = Form(None),  # Now optional if template_id is provided
    template_id: Optional[int] = Form(None),  # NEW: Template ID for message generation
    user_description: Optional[str] = Form(None),
    interval_seconds: Optional[int] = Form(None),
    use_random_interval: bool = Form(False),
    min_interval: Optional[int] = Form(None),
    max_interval: Optional[int] = Form(None),
    stop_after_hours: Optional[int] = Form(None),
    rate_limit_per_hour: Optional[int] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("auto_promo"))
):
    # Validate either promo_message or template_id is provided
    if not promo_message and not template_id:
        raise HTTPException(
            status_code=400,
            detail="Either 'promo_message' or 'template_id' must be provided"
        )
    if current_user.subscription_plan == 'pro':
        if current_user.job_counter_last_reset < datetime.utcnow() - timedelta(days=30):
            current_user.jobs_created_this_month = 0
            current_user.job_counter_last_reset = datetime.utcnow()
            db.commit()
        if current_user.jobs_created_this_month >= 500:
            raise HTTPException(status_code=403, detail="You have reached your monthly job limit of 500.")

    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")
    
    # If template_id is provided, fetch and validate it
    if template_id:
        from models import MessageTemplate
        template = db.query(MessageTemplate).filter(
            MessageTemplate.id == template_id,
            MessageTemplate.user_id == current_user.id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found or not owned by user")
        
        # Store template content for use in job config
        promo_message = template.content  # Fallback for job config

    if use_random_interval and (min_interval is None or max_interval is None):
        raise HTTPException(status_code=400, detail="min_interval and max_interval are required for random interval.")

    job_config = {
        "target_group": target_group,
        "promo_message": promo_message,
        "template_id": template_id,  # NEW: Store template_id for message generation
        "interval_seconds": interval_seconds,
        "use_random_interval": use_random_interval,
        "min_interval": min_interval,
        "max_interval": max_interval,
        "stop_after_hours": stop_after_hours,
        "rate_limit_per_hour": rate_limit_per_hour,
    }

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=account_id,
        job_type='auto_promo',
        config=json.dumps(job_config),
        status='pending',
        user_description=user_description
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    if image_file:
        upload_dir = "/app/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        image_file_path = os.path.join(upload_dir, f"promo_image_{new_job.id}_{image_file.filename}")
        try:
            with open(image_file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            job_config["image_file_path"] = image_file_path
            new_job.config = json.dumps(job_config)
            db.commit()
        except Exception as e:
            new_job.status = 'failed'
            new_job.error_message = f"Failed to save image file: {e}"
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to save image file: {e}")

    auto_promo_task.delay(new_job.id)

    if current_user.subscription_plan == 'pro':
        current_user.jobs_created_this_month += 1
        db.commit()

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
