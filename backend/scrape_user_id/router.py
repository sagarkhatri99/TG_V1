from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse
from .tasks import scrape_users_task
from models import Job
from sqlalchemy.orm import Session
import json
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from database import get_db
from models import User
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency

router = APIRouter()

class StartAuthRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str

class VerifyScrapeRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str
    code: str
    group_username: str

@router.post("/start-auth")
async def start_auth(request: StartAuthRequest, current_user: User = Depends(plan_based_dependency("scrape"))):
    try:
        async with Client(f"scrape_{request.phone_number}", request.api_id, request.api_hash, in_memory=True) as app:
            await app.send_code(request.phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify")
async def verify_scrape(request: VerifyScrapeRequest, current_user: User = Depends(plan_based_dependency("scrape"))):
    try:
        async with Client(f"scrape_{request.phone_number}", request.api_id, request.api_hash, in_memory=True) as app:
            try:
                await app.sign_in(request.phone_number, request.code)
            except SessionPasswordNeeded:
                await app.check_password(request.password)
        return {"success": True, "message": "Verification successful. Ready to scrape."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def run_scrape(
    phone_number: str,
    api_id: int,
    api_hash: str,
    group_username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("scrape"))
):
    job_config = {
        "phone": phone_number,
        "api_id": api_id,
        "api_hash": api_hash,
        "group": group_username,
    }

    new_job = Job(
        user_id=current_user.id,
        job_type='scrape_users',
        config=json.dumps(job_config),
        status='pending'
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    scrape_users_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Scraping job started."}

@router.get("/download/{job_id}")
def download_csv(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("scrape"))):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")

    if job.status != 'completed' or not job.result_path:
        raise HTTPException(status_code=400, detail="Job is not yet completed or result file not found")

    return FileResponse(job.result_path, media_type="text/csv", filename=f"participants_{job.id}.csv")
