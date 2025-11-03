from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job
from database import SessionLocal
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@celery_app.task
def cleanup_stuck_jobs():
    """
    Periodic task to clean up jobs that should be completed but are still running.
    This helps resolve edge cases where jobs don't properly mark themselves as completed.
    """
    db: Session = SessionLocal()
    try:
        # Find jobs that are still running but should be completed
        stuck_jobs = db.query(Job).filter(
            Job.status == 'running',
            Job.completion_percentage >= 100.0
        ).all()
        
        completed_count = 0
        for job in stuck_jobs:
            logger.info(f"Found stuck job {job.id} with {job.completion_percentage}% completion. Marking as completed.")
            job.status = 'completed'
            if not job.completed_at:
                job.completed_at = datetime.utcnow()
            completed_count += 1
        
        # Also check for very old running jobs that might be stuck
        old_running_jobs = db.query(Job).filter(
            Job.status == 'running',
            Job.started_at < datetime.utcnow() - timedelta(hours=24)  # Running for more than 24 hours
        ).all()
        
        for job in old_running_jobs:
            logger.warning(f"Found very old running job {job.id} (started: {job.started_at}). Marking as failed.")
            job.status = 'failed'
            job.error_message = "Job timeout - marked as failed by cleanup task"
            if not job.completed_at:
                job.completed_at = datetime.utcnow()
            completed_count += 1
        
        if completed_count > 0:
            db.commit()
            logger.info(f"Cleanup task completed. Fixed {completed_count} stuck jobs.")
        else:
            logger.debug("Cleanup task completed. No stuck jobs found.")
            
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        db.rollback()
    finally:
        db.close()

@celery_app.task
def worker_health_check():
    """
    Task to check worker health and capacity
    """
    try:
        import celery
        from celery_app import celery_app as app
        
        inspect = app.control.inspect()
        active_tasks = inspect.active()
        reserved_tasks = inspect.reserved()
        
        if active_tasks:
            total_active = sum(len(tasks) for tasks in active_tasks.values())
            logger.info(f"Worker health check: {total_active} active tasks across all workers")
            
            # Log worker capacity usage
            for worker, tasks in active_tasks.items():
                logger.info(f"Worker {worker}: {len(tasks)} active tasks")
        
        return {"status": "healthy", "active_tasks": active_tasks}
        
    except Exception as e:
        logger.error(f"Error in worker health check: {e}")
        return {"status": "error", "message": str(e)}