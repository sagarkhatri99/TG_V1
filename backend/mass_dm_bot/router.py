from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import Job
from database import get_db
import json
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from .tasks import mass_dm_bot_task

router = APIRouter()

@router.post("/create-job")
async def create_mass_dm_bot_job(
    bot_token: str = Form(...),
    message: str = Form(...),
    stop_after_hours: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Step 1: Create job to get an ID
    initial_job_config = {
        "bot_token": bot_token,
        "message": message,
        "stop_after_hours": stop_after_hours,
    }
    new_job = Job(
        telegram_account_id=None,
        job_type='mass_dm_bot',
        config=json.dumps(initial_job_config),
        status='pending'
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
    }
    new_job.config = json.dumps(final_job_config)
    db.commit()

    # Step 4: Dispatch the task
    mass_dm_bot_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM Bot job created successfully."}