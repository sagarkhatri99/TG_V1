from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
from datetime import datetime, timedelta

# Task dispatchers are imported lazily inside the restart endpoint to avoid heavy imports at startup

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
        # Clamp progress values between 0 and 100 to avoid UI showing >100%
        safe_progress = max(0, min(100, job.progress or 0))
        safe_completion = max(0.0, min(100.0, float(job.completion_percentage or 0.0)))
        job_data.append({
            "id": job.id,
            "telegram_account_id": job.telegram_account_id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": safe_progress,
            "total_tasks": job.total_tasks,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message,
            "user_description": job.user_description,
            "messages_sent": job.messages_sent or 0,
            "messages_planned": job.messages_planned or 0,
            "completion_percentage": safe_completion
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
    
    safe_progress = max(0, min(100, job.progress or 0))
    safe_completion = max(0.0, min(100.0, float(job.completion_percentage or 0.0)))
    return {
        "id": job.id,
        "telegram_account_id": job.telegram_account_id,
        "job_type": job.job_type,
        "config": config,
        "status": job.status,
        "progress": safe_progress,
        "total_tasks": job.total_tasks,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
        "user_description": job.user_description,
        "messages_sent": job.messages_sent or 0,
        "messages_planned": job.messages_planned or 0,
        "completion_percentage": safe_completion
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

@router.post("/{job_id}/restart")
async def restart_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Restart a job by creating a NEW job with a new ID and dispatching it."""
    
    old_job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not old_job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")
    
    if old_job.status in ['running', 'pending']:
        raise HTTPException(status_code=400, detail="Job is already running or pending")

    # Create a new job copying relevant fields
    new_job = Job(
        user_id=old_job.user_id,
        telegram_account_id=old_job.telegram_account_id,
        job_type=old_job.job_type,
        config=old_job.config,
        status='pending',
        user_description=(old_job.user_description or '') + " (restarted)"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Dispatch based on job type (lazy import)
    from importlib import import_module
    dispatched = False
    try:
        task_map = {
            'group_monitor': ('group_monitor.tasks', 'group_monitor_task'),
            'mass_dm_account': ('mass_dm_account.tasks', 'mass_dm_account_task'),
            'mass_dm_bot': ('mass_dm_bot.tasks', 'mass_dm_bot_task'),
            'auto_promo': ('auto_promo.tasks', 'auto_promo_task'),
        }
        if new_job.job_type in task_map:
            module_name, func_name = task_map[new_job.job_type]
            module = import_module(module_name)
            task_func = getattr(module, func_name)
            task_func.delay(new_job.id)
            dispatched = True
    except Exception as e:
        # If dispatch fails, mark job failed
        new_job.status = 'failed'
        new_job.error_message = f"Dispatch failed: {str(e)}"
        db.commit()
        raise

    return {
        "status": "restarted",
        "message": "New job created and dispatched",
        "old_job_id": old_job.id,
        "new_job_id": new_job.id,
        "dispatched": dispatched
    }

@router.get("/{job_id}/result")
async def get_job_result(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Get the result of a job"""

    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not owned by user")

    if job.status != 'completed':
        raise HTTPException(status_code=400, detail="Job is not yet completed")

    if not job.result_path:
        raise HTTPException(status_code=404, detail="Result file not found for this job")

    # In a real application, you would return a URL to a file on a cloud storage service like S3.
    # For this example, we'll just return the path to the file on the local server.
    return {"result_url": f"/downloads/{job.result_path}"}

@router.put("/{job_id}/status")
async def update_job_status(
    job_id: int,
    status: str = Form(...),
    error_message: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Update the status of a job (for internal use by Celery)"""

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = status
    if error_message:
        job.error_message = error_message

    if status == 'completed':
        job.completed_at = datetime.utcnow()

    db.commit()

    return {"status": "updated"}

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

@router.get("/reports")
async def get_job_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Get comprehensive job reports and statistics"""
    
    # Get overall job statistics
    total_jobs = db.query(func.count(Job.id)).filter(Job.user_id == current_user.id).scalar()
    
    # Jobs by status
    job_status_stats = db.query(
        Job.status,
        func.count(Job.id).label('count')
    ).filter(Job.user_id == current_user.id).group_by(Job.status).all()
    
    # Jobs by type
    job_type_stats = db.query(
        Job.job_type,
        func.count(Job.id).label('count'),
        func.avg(Job.completion_percentage).label('avg_completion')
    ).filter(Job.user_id == current_user.id).group_by(Job.job_type).all()
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_jobs = db.query(func.count(Job.id)).filter(
        Job.user_id == current_user.id,
        Job.created_at >= thirty_days_ago
    ).scalar()
    
    # Message statistics
    message_stats = db.query(
        func.sum(Job.messages_sent).label('total_sent'),
        func.sum(Job.messages_planned).label('total_planned'),
        func.avg(Job.completion_percentage).label('avg_completion')
    ).filter(Job.user_id == current_user.id).first()
    
    # Success rate
    completed_jobs = db.query(func.count(Job.id)).filter(
        Job.user_id == current_user.id,
        Job.status == 'completed'
    ).scalar()
    
    # Recent completed jobs with details
    recent_completed = db.query(Job).filter(
        Job.user_id == current_user.id,
        Job.status == 'completed',
        Job.completed_at >= thirty_days_ago
    ).order_by(Job.completed_at.desc()).limit(10).all()
    
    # Format job status stats
    status_breakdown = {status: count for status, count in job_status_stats}
    
    # Format job type stats
    type_breakdown = [{
        "job_type": job_type,
        "count": count,
        "avg_completion": round(float(max(0.0, min(100.0, (avg_completion or 0)))), 2)
    } for job_type, count, avg_completion in job_type_stats]
    
    # Format recent completed jobs
    recent_jobs_data = []
    for job in recent_completed:
        recent_jobs_data.append({
            "id": job.id,
            "job_type": job.job_type,
            "user_description": job.user_description,
            "completion_percentage": job.completion_percentage or 0.0,
            "messages_sent": job.messages_sent or 0,
            "messages_planned": job.messages_planned or 0,
            "completed_at": job.completed_at,
            "duration_hours": round((job.completed_at - job.started_at).total_seconds() / 3600, 2) if job.started_at and job.completed_at else None
        })
    
    return {
        "summary": {
            "total_jobs": total_jobs,
            "jobs_last_30_days": recent_jobs,
            "completion_rate": round((completed_jobs / total_jobs * 100), 2) if total_jobs > 0 else 0,
            "total_messages_sent": message_stats.total_sent or 0,
            "total_messages_planned": message_stats.total_planned or 0,
            "overall_completion_percentage": round(float(message_stats.avg_completion or 0), 2)
        },
        "status_breakdown": status_breakdown,
        "job_type_breakdown": type_breakdown,
        "recent_completed_jobs": recent_jobs_data
    }
