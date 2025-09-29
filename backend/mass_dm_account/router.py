from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from .tasks import mass_dm_account_task
from datetime import datetime, timedelta

router = APIRouter()

class MassDMAccountRequest(BaseModel):
    account_id: int
    message: str
    stop_after_hours: Optional[int] = None

@router.post("/create-job")
async def create_mass_dm_account_job(
    account_id: int = Form(...),
    message: str = Form(...),
    user_description: Optional[str] = Form(None),
    stop_after_hours: Optional[int] = Form(None),
    rate_limit_per_hour: Optional[int] = Form(None),
    delay_seconds: Optional[int] = Form(None),
    min_delay_seconds: Optional[int] = Form(None),
    max_delay_seconds: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("mass_dm"))
):
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

    job_config = {
        "message": message,
        "stop_after_hours": stop_after_hours,
        "rate_limit_per_hour": rate_limit_per_hour,
        "delay_seconds": delay_seconds,
        "min_delay_seconds": min_delay_seconds,
        "max_delay_seconds": max_delay_seconds,
    }

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=account_id,
        job_type='mass_dm_account',
        config=json.dumps(job_config),
        status='pending',
        user_description=user_description
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # Handle CSV file
    csv_file_path = os.path.join(upload_dir, f"mass_dm_{new_job.id}.csv")
    try:
        with open(csv_file_path, "wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)
        job_config["csv_file_path"] = csv_file_path
    except Exception as e:
        new_job.status = 'failed'
        new_job.error_message = f"Failed to save CSV file: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to save CSV file: {e}")

    # Handle optional image file
    if image_file:
        image_file_path = os.path.join(upload_dir, f"mass_dm_image_{new_job.id}_{image_file.filename}")
        try:
            with open(image_file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            job_config["image_file_path"] = image_file_path
        except Exception as e:
            new_job.status = 'failed'
            new_job.error_message = f"Failed to save image file: {e}"
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to save image file: {e}")

    # Update job config with file paths
    new_job.config = json.dumps(job_config)
    db.commit()

    # Step 4: Dispatch the task
    mass_dm_account_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM Account job created successfully."}
