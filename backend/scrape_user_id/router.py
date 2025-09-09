from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from database import get_db
from models import Job, TelegramAccount
from .tasks import scrape_users_task

router = APIRouter()

class ScrapeUsersRequest(BaseModel):
    account_id: int
    group_username: str

@router.post("/create-job")
async def create_scrape_users_job(request: ScrapeUsersRequest, db: Session = Depends(get_db)):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == request.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.status != 'active':
        raise HTTPException(status_code=400, detail=f"Account '{account.nickname}' is not active.")

    job_config = {
        "group_username": request.group_username,
        "account_id": request.account_id
    }

    new_job = Job(
        telegram_account_id=request.account_id,
        job_type='scrape_users',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    scrape_users_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Scrape users job created successfully."}
