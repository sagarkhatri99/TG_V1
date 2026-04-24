"""
tasks/scheduler.py

Celery Beat scheduler: dispatches jobs whose scheduled_at time has elapsed.
Runs every 60 seconds via Celery Beat.

Gap 8 fix: replaced long-held SessionLocal with a two-phase short-session
pattern — DB session closes before apply_async fires, so the connection is
returned to the pool before Celery picks up the task.

Gap 4 fix: single db.commit() after apply_async sets both status='queued'
and celery_task_id atomically.

Uses core/task_registry.py as the single source of truth for TASK_MAP and
queue routing — no inline copy of the map.
"""

import logging
from datetime import datetime
from importlib import import_module

from celery_app import celery_app
from models import Job
from core.db_utils import get_short_session
from core.task_registry import TASK_MAP, get_queue_for_job

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.scheduler.dispatch_scheduled_jobs")
def dispatch_scheduled_jobs():
    """
    Runs every 60 seconds via Celery Beat.
    Picks up all jobs where status='scheduled' and scheduled_at <= now(),
    dispatches the appropriate Celery task to the correct queue.
    """
    dispatched = []
    failed = []

    try:
        # ── Phase 1: load due jobs, transition to 'queued' ──────────────────
        # Short session — closes before any apply_async call.
        job_data: list[tuple[int, str, int | None]] = []  # (job_id, job_type, account_id)

        with get_short_session() as db:
            now = datetime.utcnow()
            due_jobs = db.query(Job).filter(
                Job.status == "scheduled",
                Job.scheduled_at <= now,
            ).all()

            if not due_jobs:
                return {"dispatched": 0}

            logger.info(f"Scheduler: found {len(due_jobs)} due scheduled job(s)")

            for job in due_jobs:
                if job.job_type not in TASK_MAP:
                    logger.warning(
                        f"Scheduler: unknown job_type '{job.job_type}' for job {job.id}"
                    )
                    job.status = "failed"
                    job.error_message = f"Unknown job type for scheduling: {job.job_type}"
                    failed.append(job.id)
                    continue

                # Transition status now — before dispatch
                job.status = "queued"
                job_data.append((job.id, job.job_type, job.telegram_account_id))
        # ── DB session closed — connection returned to pool ──────────────────

        # ── Phase 2: dispatch each job, write celery_task_id ────────────────
        for job_id, job_type, account_id in job_data:
            try:
                module_name, func_name = TASK_MAP[job_type]
                task_func = getattr(import_module(module_name), func_name)
                queue = get_queue_for_job(job_type, account_id)

                # Dispatch first
                result = task_func.apply_async(args=[job_id], queue=queue)

                # Single commit: status='queued' + celery_task_id together (Gap 4 fix)
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.status = "queued"
                        job.celery_task_id = result.id
                # get_short_session commits on exit

                dispatched.append(job_id)
                logger.info(
                    f"Scheduler: dispatched job {job_id} ({job_type}) "
                    f"→ queue '{queue}', task_id={result.id}"
                )

            except Exception as e:
                logger.error(
                    f"Scheduler: failed to dispatch job {job_id} ({job_type}): {e}"
                )
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.status = "failed"
                        job.error_message = f"Scheduler dispatch failed: {e}"
                failed.append(job_id)

    except Exception as e:
        logger.error(f"dispatch_scheduled_jobs: unexpected error: {e}")

    return {
        "dispatched": len(dispatched),
        "job_ids": dispatched,
        "failed": failed,
    }
