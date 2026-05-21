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
from typing import Optional

from celery_app import celery_app
from models import Job
from core.db_utils import get_short_session
from core.task_registry import TASK_MAP, get_queue_for_job

logger = logging.getLogger(__name__)


def _load_due_jobs(now: datetime) -> list[tuple[int, str, Optional[int]]]:
    """Read-only phase: load due jobs and fail unknown types."""
    due_jobs: list[tuple[int, str, Optional[int]]] = []
    unknown_job_ids: list[int] = []

    with get_short_session() as db:
        rows = db.query(Job).filter(
            Job.status == "scheduled",
            Job.scheduled_at <= now,
        ).all()

        for job in rows:
            if job.job_type not in TASK_MAP:
                unknown_job_ids.append(job.id)
                continue
            due_jobs.append((job.id, job.job_type, job.telegram_account_id))

    if unknown_job_ids:
        with get_short_session() as db:
            unknown_jobs = db.query(Job).filter(Job.id.in_(unknown_job_ids)).all()
            for job in unknown_jobs:
                job.status = "failed"
                job.error_message = f"Unknown job type for scheduling: {job.job_type}"

    return due_jobs


def _dispatch_job(job_id: int, job_type: str, account_id: Optional[int]) -> str:
    """Dispatch phase: send task to celery and return task id."""
    module_name, func_name = TASK_MAP[job_type]
    task_func = getattr(import_module(module_name), func_name)
    queue = get_queue_for_job(job_type, account_id)
    result = task_func.apply_async(args=[job_id], queue=queue)
    logger.info(
        f"Scheduler: dispatched job {job_id} ({job_type}) "
        f"-> queue '{queue}', task_id={result.id}"
    )
    return result.id


def _mark_dispatched(job_id: int, task_id: str) -> None:
    """Persist queued state and celery task id in one commit."""
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "queued"
            job.celery_task_id = task_id


def _mark_dispatch_failed(job_id: int, error_message: str) -> None:
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = error_message


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
        now = datetime.utcnow()
        job_data = _load_due_jobs(now)
        if not job_data:
            return {"dispatched": 0}

        logger.info(f"Scheduler: found {len(job_data)} due scheduled job(s)")

        # Dispatch phase only: no query-selection logic mixed here.
        for job_id, job_type, account_id in job_data:
            try:
                task_id = _dispatch_job(job_id, job_type, account_id)
                _mark_dispatched(job_id, task_id)
                dispatched.append(job_id)
            except Exception as e:
                logger.error(f"Scheduler: failed to dispatch job {job_id} ({job_type}): {e}")
                _mark_dispatch_failed(job_id, f"Scheduler dispatch failed: {e}")
                failed.append(job_id)

    except Exception as e:
        logger.error(f"dispatch_scheduled_jobs: unexpected error: {e}")

    return {
        "dispatched": len(dispatched),
        "job_ids": dispatched,
        "failed": failed,
    }
