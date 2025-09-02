from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import get_db
import json
from pydantic import BaseModel
from typing import Optional
import shutil
import os
import tempfile
from .tasks import mass_dm_account_task

router = APIRouter()

class MassDMAccountRequest(BaseModel):
    account_id: int
    message: str
    stop_after_hours: Optional[int] = None

@router.post("/create-job")
async def create_mass_dm_account_job(
    account_id: int = Form(...),
    message: str = Form(...),
    stop_after_hours: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Save the uploaded CSV file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as temp_file:
        shutil.copyfileobj(csv_file.file, temp_file)
        temp_file_path = temp_file.name

    job_config = {
        "message": message,
        "stop_after_hours": stop_after_hours,
        "csv_file_path": temp_file_path,
    }

    new_job = Job(
        telegram_account_id=account_id,
        job_type='mass_dm_account',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    mass_dm_account_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM Account job created successfully."}

# Old endpoints deprecated
# from .service import start_dm_auth, send_mass_dm_account_with_otp
# ...
