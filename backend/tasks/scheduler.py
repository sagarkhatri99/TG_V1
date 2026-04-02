"""
Celery Beat scheduler task: dispatches jobs that have been set to 'scheduled' status
and whose scheduled_at time has elapsed. Runs every 60 seconds via Celery Beat.
"""
from celery_app import celery_app
from database import SessionLocal
from models import Job
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Task type → (module, function name)
TASK_MAP = {
    'mass_dm_account': ('mass_dm_account.tasks', 'mass_dm_account_task'),
    'auto_promo':      ('auto_promo.tasks', 'auto_promo_task'),
    'group_monitor':   ('group_monitor.tasks', 'group_monitor_task'),
    'scrape_users':    ('scrape_user_id.tasks', 'scrape_user_id_task'),
    'group_join':      ('group_joiner.tasks', 'group_join_task'),
    'mass_dm_bot':     ('mass_dm_bot.tasks', 'mass_dm_bot_task'),
}


@celery_app.task(name='tasks.scheduler.dispatch_scheduled_jobs')
def dispatch_scheduled_jobs():
    """
    Runs every 60 seconds via Celery Beat.
    Picks up all jobs where status='scheduled' and scheduled_at <= now(),
    sets them to 'pending', and dispatches the appropriate Celery task.
    """
    db = SessionLocal()
    dispatched = []
    failed = []

    try:
        now = datetime.utcnow()
        due_jobs = db.query(Job).filter(
            Job.status == 'scheduled',
            Job.scheduled_at <= now
        ).all()

        if not due_jobs:
            return {"dispatched": 0}

        logger.info(f"Scheduler: found {len(due_jobs)} due scheduled job(s)")

        from importlib import import_module

        for job in due_jobs:
            try:
                if job.job_type not in TASK_MAP:
                    logger.warning(f"Scheduler: unknown job_type '{job.job_type}' for job {job.id}")
                    job.status = 'failed'
                    job.error_message = f"Unknown job type for scheduling: {job.job_type}"
                    db.commit()
                    continue

                module_name, func_name = TASK_MAP[job.job_type]
                module = import_module(module_name)
                task_func = getattr(module, func_name)

                # Transition to pending then dispatch
                job.status = 'pending'
                db.commit()

                task_func.delay(job.id)
                dispatched.append(job.id)
                logger.info(f"Scheduler: dispatched job {job.id} ({job.job_type})")

            except Exception as e:
                logger.error(f"Scheduler: failed to dispatch job {job.id}: {e}")
                job.status = 'failed'
                job.error_message = f"Scheduler dispatch failed: {str(e)}"
                db.commit()
                failed.append(job.id)

    except Exception as e:
        logger.error(f"Scheduler task error: {e}")
    finally:
        db.close()

    return {"dispatched": len(dispatched), "job_ids": dispatched, "failed": failed}
