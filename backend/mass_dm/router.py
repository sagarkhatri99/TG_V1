from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
import os
import shutil
from .tasks import mass_dm_account_task, mass_dm_bot_task
from typing import Optional

router = APIRouter()

@router.post("/account/create")
async def create_mass_dm_account_job(
    account_id: int = Form(...),
    message: str = Form(...),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("mass_dm"))
):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    csv_path = os.path.join(upload_dir, f"mass_dm_{current_user.id}_{csv_file.filename}")

    with open(csv_path, "wb") as buffer:
        shutil.copyfileobj(csv_file.file, buffer)

    job_config = {
        "message": message,
        "csv_path": csv_path,
    }

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=account_id,
        job_type='mass_dm_account',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    mass_dm_account_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM (account) job created successfully."}

@router.post("/bot/create")
async def create_mass_dm_bot_job(
    bot_token: str = Form(...),
    message: str = Form(...),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("mass_dm"))
):
    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    csv_path = os.path.join(upload_dir, f"mass_dm_bot_{current_user.id}_{csv_file.filename}")

    with open(csv_path, "wb") as buffer:
        shutil.copyfileobj(csv_file.file, buffer)

    job_config = {
        "bot_token": bot_token,
        "message": message,
        "csv_path": csv_path,
    }

    new_job = Job(
        user_id=current_user.id,
        job_type='mass_dm_bot',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    mass_dm_bot_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM (bot) job created successfully."}