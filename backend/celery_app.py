import core.db_guard  # noqa: F401 — must be first; patches sqlite3.connect before any other import
from celery import Celery
from celery.signals import worker_init, task_prerun, task_postrun, task_failure, task_retry
from core.logging import worker_logger, error_logger
from celery.schedules import crontab
import os
import time
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Broker / backend — read from validated settings (no silent defaults)
# ---------------------------------------------------------------------------
from core.config import settings as _settings

celery_app = Celery(
    "worker",
    broker=_settings.CELERY_BROKER_URL,
    backend=os.environ.get("CELERY_RESULT_BACKEND", _settings.REDIS_URL),
    include=[
        'auto_promo.tasks',
        'group_monitor.tasks',
        'mass_dm_account.tasks',
        'mass_dm_bot.tasks',
        'scrape_user_id.tasks',
        'group_joiner.tasks',
        'core.cleanup_tasks',
        'tasks.maintenance_tasks',  # Daily health reset and cleanup
    ]
)

from kombu import Queue

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,  # Faster worker recycling
    task_soft_time_limit=21600,  # 6 hour soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=43200,       # 12 hour hard limit (kills worker process)
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    task_queues=(
        Queue('default', routing_key='task.#', priority=5),
        Queue('long_tasks', routing_key='long.#', priority=3),
        Queue('short_tasks', routing_key='short.#', priority=8),
        Queue('celery', routing_key='celery.#', priority=5),
    ),
    task_queue_max_priority=10,
    task_default_priority=5,
    beat_schedule={
        'cleanup-stuck-jobs': {
            'task': 'core.cleanup_tasks.cleanup_stuck_jobs',
            'schedule': 300.0,  # Run every 5 minutes
        },
        'worker-health-check': {
            'task': 'core.cleanup_tasks.worker_health_check',
            'schedule': 600.0,  # Run every 10 minutes
        },
        'reset-daily-health-midnight': {
            'task': 'reset_daily_health_counters',
            'schedule': crontab(hour=0, minute=0),  # Every day at 00:00 UTC
        },
        'cleanup-error-history-weekly': {
            'task': 'cleanup_old_error_history',
            'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Every Sunday at 02:00 UTC
        },
    },
    task_routes={
        'auto_promo.tasks.auto_promo_task': {'queue': 'long_tasks'},
        'group_monitor.tasks.group_monitor_task': {'queue': 'short_tasks'},
        'mass_dm_account.tasks.mass_dm_account_task': {'queue': 'long_tasks'},
        'mass_dm_bot.tasks.mass_dm_bot_task': {'queue': 'long_tasks'},
        'scrape_user_id.tasks.scrape_users_task': {'queue': 'short_tasks'},
        'group_joiner.tasks.group_join_task': {'queue': 'long_tasks'},
        'core.cleanup_tasks.*': {'queue': 'celery'},
    },
)

# ---------------------------------------------------------------------------
# Worker startup: verify DATABASE_URL + wait for DB to be reachable
# ---------------------------------------------------------------------------
@worker_init.connect
def on_worker_init(sender=None, **kwargs):
    """Log the DATABASE_URL and verify DB connectivity before accepting tasks."""
    from core.config import settings, mask_db_url
    from core.logging import setup_json_logging
    from database import engine
    from sqlalchemy import text

    # Initialize JSON logging for the worker
    setup_json_logging(environment=settings.ENVIRONMENT, log_level="INFO")

    masked = mask_db_url(settings.DATABASE_URL)
    logger.info(
        "✅ [Worker] Starting — DATABASE_URL: %s | host: %s",
        masked,
        sender.hostname if sender else "unknown",
    )

    # Log queue and concurrency info from worker options
    worker_opts = getattr(sender, "options", {}) or {}
    queues = worker_opts.get("queues") or os.environ.get("QUEUES", "(default)")
    concurrency = worker_opts.get("concurrency") or os.environ.get("CELERYD_CONCURRENCY", "(auto)")
    logger.info("[Worker] Queues: %s | Concurrency: %s", queues, concurrency)

    max_retries = 10
    retry_interval = 5  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ [Worker] Database connection verified on attempt %d.", attempt)
            return
        except Exception as exc:
            logger.warning(
                "⚠️  [Worker] DB not reachable (attempt %d/%d): %s — retrying in %ds...",
                attempt,
                max_retries,
                exc,
                retry_interval,
            )
            if attempt < max_retries:
                time.sleep(retry_interval)

    raise RuntimeError(
        f"[Worker] PostgreSQL is not reachable after {max_retries} attempts. "
        "Worker startup aborted."
    )


@task_prerun.connect
def on_task_start(task_id, task, args, kwargs, **_):
    worker_logger.info(f"TASK START | {task.name} | id={task_id}")

@task_postrun.connect
def on_task_done(task_id, task, retval, state, **_):
    worker_logger.info(f"TASK DONE  | {task.name} | id={task_id} | state={state}")

@task_failure.connect
def on_task_fail(task_id, exception, einfo, **_):
    error_logger.error(f"TASK FAIL  | id={task_id} | error={exception}", exc_info=einfo)

@task_retry.connect
def on_task_retry(request, reason, **_):
    worker_logger.warning(f"TASK RETRY | id={request.id} | reason={reason}")

if __name__ == "__main__":
    celery_app.start()