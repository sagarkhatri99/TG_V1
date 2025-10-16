from fastapi import APIRouter, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from typing import List
from .tasks import monitor_groups_task

router = APIRouter()

@router.post("/create")
async def create_group_monitor_job(
    account_id: int = Form(...),
    groups: List[str] = Form(...),
    keywords: List[str] = Form(...),
    users: List[str] = Form(...),
    limit: int = Form(100),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("monitor"))
):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    job_config = {
        "groups": groups,
        "keywords": keywords,
        "users": users,
        "limit": limit,
    }

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=account_id,
        job_type='group_monitor',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    monitor_groups_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Group monitor job created successfully."}