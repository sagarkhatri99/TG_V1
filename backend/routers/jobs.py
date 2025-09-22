from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from datetime import datetime

router = APIRouter()

@router.get("/list")
async def list_jobs(
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """List jobs with optional filters"""
    
    query = db.query(Job).filter(Job.user_id == current_user.id)
    
    if account_id:
        # Also ensure the requested account belongs to the user
        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found or not owned by user")
        query = query.filter(Job.telegram_account_id == account_id)
    
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.order_by(Job.created_at.desc()).all()
    
    job_data = []
    for job in jobs:
        job_data.append({
            "id": job.id,
            "telegram_account_id": job.telegram_account_id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "total_tasks": job.total_tasks,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message
        })
    
    return {"jobs": job_data}

@router.get("/{job_id}")
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Get job details"""
    
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")
    
    config = {}
    try:
        config = json.loads(job.config) if job.config else {}
    except:
        pass
    
    return {
        "id": job.id,
        "telegram_account_id": job.telegram_account_id,
        "job_type": job.job_type,
        "config": config,
        "status": job.status,
        "progress": job.progress,
        "total_tasks": job.total_tasks,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message
    }

@router.post("/{job_id}/pause")
async def pause_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Pause a job"""
    
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")
    
    if job.status not in ['running', 'pending']:
        raise HTTPException(status_code=400, detail="Job cannot be paused")
    
    job.status = 'paused'
    db.commit()
    
    return {"status": "paused"}

@router.post("/{job_id}/resume")
async def resume_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Resume a paused job"""
    
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")
    
    if job.status != 'paused':
        raise HTTPException(status_code=400, detail="Job is not paused")
    
    job.status = 'pending'
    db.commit()
    
    return {"status": "resumed"}

@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Delete a job"""
    
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")
    
    db.delete(job)
    db.commit()
    
    return {"status": "deleted"}