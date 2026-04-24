"""
core/cleanup_tasks.py

Periodic beat tasks for job cleanup and worker health monitoring.

Gap 8 fix: replaced long-held SessionLocal() with get_short_session() to
return DB connections to the pool promptly. Added orphaned account lock
release for jobs that have exceeded task_time_limit.
"""

import logging
from datetime import datetime, timedelta

from celery_app import celery_app
from models import Job
from core.db_utils import get_short_session

logger = logging.getLogger(__name__)

# Matches task_time_limit in celery_app.py (12 hours) + 1h grace
_ORPHAN_THRESHOLD_HOURS = 13


@celery_app.task
def cleanup_stuck_jobs():
    """
    Periodic task to clean up jobs that should be completed but are still running.
    Resolves edge cases where jobs don't properly mark themselves as completed.

    Also releases orphaned Redis account locks for jobs that have exceeded
    the hard kill timeout — prevents new jobs from being blocked indefinitely
    by a dead worker's lock.
    """
    from core.account_lock import release_account_lock

    fixed_count = 0
    try:
        with get_short_session() as db:
            # ── 1. Mark 100%-complete jobs as completed ──────────────────────
            stuck_jobs = db.query(Job).filter(
                Job.status == "running",
                Job.completion_percentage >= 100.0,
            ).all()

            for job in stuck_jobs:
                logger.info(
                    f"Cleanup: job {job.id} is 100% complete but still 'running'. "
                    f"Marking as completed."
                )
                job.status = "completed"
                if not job.completed_at:
                    job.completed_at = datetime.utcnow()
                fixed_count += 1

            # ── 2. Mark jobs older than orphan threshold as failed ───────────
            # These have exceeded task_time_limit + grace period and are
            # almost certainly orphaned (worker was hard-killed).
            cutoff = datetime.utcnow() - timedelta(hours=_ORPHAN_THRESHOLD_HOURS)
            old_running_jobs = db.query(Job).filter(
                Job.status == "running",
                Job.started_at < cutoff,
            ).all()

            for job in old_running_jobs:
                logger.warning(
                    f"Cleanup: job {job.id} has been running since {job.started_at} "
                    f"(> {_ORPHAN_THRESHOLD_HOURS}h). Marking as failed."
                )
                job.status = "failed"
                job.error_message = (
                    f"Job timeout — marked failed by cleanup task after "
                    f"{_ORPHAN_THRESHOLD_HOURS}h. Worker may have been killed."
                )
                if not job.completed_at:
                    job.completed_at = datetime.utcnow()
                fixed_count += 1

                # Release orphaned account lock so the next queued job can start
                if job.telegram_account_id:
                    try:
                        release_account_lock(job.telegram_account_id)
                        logger.info(
                            f"Cleanup: released orphaned lock for account "
                            f"{job.telegram_account_id} (job {job.id})"
                        )
                    except Exception as lock_err:
                        logger.warning(
                            f"Cleanup: could not release lock for account "
                            f"{job.telegram_account_id} (job {job.id}): {lock_err}"
                        )

        # get_short_session() commits on clean exit

        if fixed_count > 0:
            logger.info(f"Cleanup: fixed {fixed_count} stuck/orphaned job(s).")
        else:
            logger.debug("Cleanup: no stuck jobs found.")

    except Exception as e:
        logger.error(f"cleanup_stuck_jobs failed: {e}")


@celery_app.task
def worker_health_check():
    """
    Task to check worker health and log capacity usage.
    """
    try:
        from celery_app import celery_app as app

        inspect = app.control.inspect()
        active_tasks = inspect.active()
        reserved_tasks = inspect.reserved()

        if active_tasks:
            total_active = sum(len(tasks) for tasks in active_tasks.values())
            logger.info(
                f"Worker health check: {total_active} active tasks across all workers"
            )
            for worker, tasks in active_tasks.items():
                logger.info(f"  {worker}: {len(tasks)} active tasks")

        return {"status": "healthy", "active_tasks": active_tasks}

    except Exception as e:
        logger.error(f"Error in worker health check: {e}")
        return {"status": "error", "message": str(e)}