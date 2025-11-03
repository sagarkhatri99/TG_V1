from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from .service import start_scrape_auth, verify_and_scrape, scrape_with_existing_account
from database import get_db
from models import User, TelegramAccount, Job
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import os

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

class ScrapeWithAccountRequest(BaseModel):
    account_id: int
    group_username: str

@router.post("/start-auth")
async def start_auth(request: StartAuthRequest, current_user: User = Depends(plan_based_dependency("scrape"))):
    try:
        await start_scrape_auth(request.api_id, request.api_hash, request.phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-scrape")
async def verify_scrape(request: VerifyScrapeRequest, current_user: User = Depends(plan_based_dependency("scrape"))):
    try:
        count = await verify_and_scrape(
            request.api_id,
            request.api_hash,
            request.phone_number,
            request.code,
            request.group_username
        )
        return {"message": f"Scraped {count} users from {request.group_username}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape-with-account")
async def scrape_with_account(
    request: ScrapeWithAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("scrape"))
):
    """Scrape users using an existing Telegram account"""
    try:
        # Verify account belongs to user
        account = db.query(TelegramAccount).filter(
            TelegramAccount.id == request.account_id,
            TelegramAccount.user_id == current_user.id
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found or not owned by user")
        
        # Create a job for this scraping task
        from models import Job
        import json
        
        new_job = Job(
            user_id=current_user.id,
            telegram_account_id=account.id,
            job_type='scrape_users',
            config=json.dumps({'group_username': request.group_username}),
            status='pending',
            user_description=f"Scraping users from {request.group_username}"
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        
        # Dispatch the task
        from scrape_user_id.tasks import scrape_users_task
        scrape_users_task.delay(new_job.id)
        
        return {
            "success": True,
            "message": f"Scrape job started for {request.group_username}",
            "job_id": new_job.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
def download_csv(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("scrape"))
):
    """Download the scraped CSV file for a job"""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == 'scrape_users'
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")
    
    # Try to find the result file
    # Files are named: participants_{phone_number}_{timestamp}.csv
    # We'll search for files matching this pattern for this job
    results_dir = "/app/job_results"
    
    if not os.path.exists(results_dir):
        raise HTTPException(status_code=404, detail="Results directory not found")
    
    # Find the most recent file that matches the job (by timestamp)
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    matching_files = []
    for filename in os.listdir(results_dir):
        if filename.startswith(f"participants_{account.phone_number}_"):
            matching_files.append(filename)
    
    if not matching_files:
        raise HTTPException(status_code=404, detail="Result file not found. Job may still be processing.")
    
    # Use the most recently created file
    filepath = os.path.join(results_dir, sorted(matching_files)[-1])
    
    def file_iterator(file_path, chunk_size=8192):
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except FileNotFoundError:
            raise
    
    try:
        from os.path import basename
        return StreamingResponse(
            file_iterator(filepath),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={basename(filepath)}"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result file not found.")
