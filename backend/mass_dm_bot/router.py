from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import Job, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from .tasks import mass_dm_bot_task
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/create-job")
async def create_mass_dm_bot_job(
    bot_token: str = Form(...),
    message: str = Form(...),
    user_description: Optional[str] = Form(None),
    stop_after_hours: Optional[int] = Form(None),
    delay_seconds: Optional[int] = Form(None),
    min_delay_seconds: Optional[int] = Form(None),
    max_delay_seconds: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    scheduled_at: Optional[str] = Form(None),  # ISO8601 datetime string for deferred start
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

    # Step 1: Create job to get an ID
    initial_job_config = {
        "bot_token": bot_token,
        "message": message,
        "stop_after_hours": stop_after_hours,
    }
    # Parse scheduled_at if provided
    scheduled_at_dt = None
    if scheduled_at:
        try:
            scheduled_at_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            if scheduled_at_dt.tzinfo is not None:
                import pytz
                scheduled_at_dt = scheduled_at_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at format. Use ISO8601, e.g. 2026-03-20T10:00:00Z")

    is_scheduled = scheduled_at_dt is not None and scheduled_at_dt > datetime.utcnow()
    initial_status = 'scheduled' if is_scheduled else 'pending'

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=None,
        job_type='mass_dm_bot',
        config=json.dumps(initial_job_config),
        status=initial_status,
        scheduled_at=scheduled_at_dt,
        user_description=user_description
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Step 2: Save the file to the shared uploads volume
    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"mass_dm_bot_{new_job.id}.csv")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)
    except Exception as e:
        new_job.status = 'failed'
        new_job.error_message = f"Failed to save uploaded file: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    # Step 3: Update job config with the file path
    final_job_config = {
        "bot_token": bot_token,
        "message": message,
        "stop_after_hours": stop_after_hours,
        "csv_file_path": file_path,
        "delay_seconds": delay_seconds,
        "min_delay_seconds": min_delay_seconds,
        "max_delay_seconds": max_delay_seconds,
    }
    new_job.config = json.dumps(final_job_config)
    db.commit()

    # Step 4: Dispatch the task (only if not scheduled)
    if not is_scheduled:
        mass_dm_bot_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM Bot job created successfully."}