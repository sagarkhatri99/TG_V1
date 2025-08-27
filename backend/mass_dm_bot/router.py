from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import Job
from database import get_db
import json
from pydantic import BaseModel
from typing import Optional
import shutil

router = APIRouter()

@router.post("/create-job")
async def create_mass_dm_bot_job(
    bot_token: str = Form(...),
    message: str = Form(...),
    stop_after_hours: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Save the uploaded CSV file to a temporary location
    temp_file_path = f"/app/job_results/temp_{csv_file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(csv_file.file, buffer)

    job_config = {
        "bot_token": bot_token,
        "message": message,
        "stop_after_hours": stop_after_hours,
        "csv_file_path": temp_file_path,
    }

    new_job = Job(
        # This job is not tied to a specific TelegramAccount, so telegram_account_id is null
        telegram_account_id=None,
        job_type='mass_dm_bot',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    db.close()

    return {"job_id": new_job.id, "message": "Mass DM Bot job created successfully."}

# Old endpoints deprecated
# from .service import send_mass_dm_bot
# ...
