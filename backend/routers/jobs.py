from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, nullslast, desc
from typing import List, Optional
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
import json
import csv
import io
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
    # Get all completed jobs, prioritize those with completed_at timestamps
    recent_completed = db.query(Job).filter(
        Job.user_id == current_user.id,
        Job.status == 'completed'
    ).order_by(nullslast(desc(Job.completed_at)), desc(Job.created_at)).limit(10).all()
    
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

@router.get("/reports/download")
async def download_job_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """Download comprehensive job reports as CSV"""
    
    # Get all jobs for the user
    jobs = db.query(Job).filter(
        Job.user_id == current_user.id
    ).order_by(Job.created_at.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Job ID',
        'Job Type',
        'Description',
        'Status',
        'Created At',
        'Started At',
        'Completed At',
        'Messages Sent',
        'Messages Planned',
        'Completion %',
        'Duration (hours)',
        'Error Message'
    ])
    
    # Write job data
    for job in jobs:
        duration = None
        if job.started_at and job.completed_at:
            duration = round((job.completed_at - job.started_at).total_seconds() / 3600, 2)
        elif job.started_at and job.status == 'running':
            duration = round((datetime.utcnow() - job.started_at).total_seconds() / 3600, 2)
        
        writer.writerow([
            job.id,
            job.job_type,
            job.user_description or 'N/A',
            job.status,
            job.created_at.strftime('%Y-%m-%d %H:%M:%S') if job.created_at else 'N/A',
            job.started_at.strftime('%Y-%m-%d %H:%M:%S') if job.started_at else 'N/A',
            job.completed_at.strftime('%Y-%m-%d %H:%M:%S') if job.completed_at else 'N/A',
            job.messages_sent or 0,
            job.messages_planned or 0,
            round(float(job.completion_percentage or 0), 2),
            duration if duration else 'N/A',
            job.error_message or 'N/A'
        ])
    
    # Add summary statistics
    output.write('\n\n')  # Empty lines
    writer.writerow(['SUMMARY STATISTICS'])
    writer.writerow([''])
    
    # Calculate stats
    total_jobs = len(jobs)
    completed_jobs = len([j for j in jobs if j.status == 'completed'])
    running_jobs = len([j for j in jobs if j.status == 'running'])
    failed_jobs = len([j for j in jobs if j.status == 'failed'])
    pending_jobs = len([j for j in jobs if j.status == 'pending'])
    
    total_sent = sum([j.messages_sent or 0 for j in jobs])
    total_planned = sum([j.messages_planned or 0 for j in jobs])
    
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Jobs', total_jobs])
    writer.writerow(['Completed Jobs', completed_jobs])
    writer.writerow(['Running Jobs', running_jobs])
    writer.writerow(['Failed Jobs', failed_jobs])
    writer.writerow(['Pending Jobs', pending_jobs])
    writer.writerow(['Completion Rate (%)', round((completed_jobs / total_jobs * 100), 2) if total_jobs > 0 else 0])
    writer.writerow(['Total Messages Sent', total_sent])
    writer.writerow(['Total Messages Planned', total_planned])
    writer.writerow(['Success Rate (%)', round((total_sent / total_planned * 100), 2) if total_planned > 0 else 0])
    
    # Prepare for download
    output.seek(0)
    
    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"job_reports_{timestamp}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/mass-dm-template/download")
async def download_mass_dm_template(
    current_user: User = Depends(get_current_user)
):
    """
    Download a sample CSV template for Mass DM.

    Template includes examples for both user_id and username columns.
    Demonstrates that user_id is prioritized if both columns are present.
    """
    csv_content = """user_id,username,first_name,notes
1234567890,john_doe,John,Example with User ID
,jane_smith,Jane,Example with username only
9876543210,alice_example,Alice,Both ID and username (ID will be used)
5555555555,,Bob,User ID only (most reliable method)
"""

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=mass_dm_template.csv"
        }
    )
