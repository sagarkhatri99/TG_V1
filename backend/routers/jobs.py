from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Job, TelegramAccount
from database import get_db
import json
from datetime import datetime

router = APIRouter()

@router.get("/list")
async def list_jobs(
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List jobs with optional filters"""
    
    query = db.query(Job)
    
    if account_id:
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
    db: Session = Depends(get_db)
):
    """Get job details"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
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
    db: Session = Depends(get_db)
):
    """Pause a job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in ['running', 'pending']:
        raise HTTPException(status_code=400, detail="Job cannot be paused")
    
    job.status = 'paused'
    db.commit()
    
    return {"status": "paused"}

@router.post("/{job_id}/resume")
async def resume_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Resume a paused job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != 'paused':
        raise HTTPException(status_code=400, detail="Job is not paused")
    
    job.status = 'pending'
    db.commit()
    
    return {"status": "resumed"}

@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Delete a job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    
    return {"status": "deleted"}

import os
from fastapi.responses import StreamingResponse

@router.get("/download/{job_id}")
def download_job_result(job_id: int, db: Session = Depends(get_db)):
    """Download the result CSV for a completed job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != 'completed':
        raise HTTPException(status_code=400, detail="Job is not yet complete.")

    # Determine the filename based on the job type
    if job.job_type == 'group_monitor':
        filename = f"monitored_messages_job_{job_id}.csv"
    elif job.job_type == 'scrape_users':
        filename = f"scraped_users_job_{job_id}.csv"
    else:
        raise HTTPException(status_code=400, detail=f"Job type '{job.job_type}' does not produce a downloadable result.")

    file_path = f"/app/job_results/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Result file not found. It may have been deleted or the job may have completed with no results.")

    def file_iterator(path, chunk_size=8192):
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        file_iterator(file_path),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )