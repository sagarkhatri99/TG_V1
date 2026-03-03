from celery import Celery
from celery.schedules import crontab
import os

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('CELERY_CONFIG_MODULE', 'core.config')

celery_app = Celery(
    "worker",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=[
        'auto_promo.tasks',
        'group_monitor.tasks',
        'mass_dm_account.tasks',
        'mass_dm_bot.tasks',
        'scrape_user_id.tasks',
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
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,       # 2 hour hard limit
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
        'core.cleanup_tasks.*': {'queue': 'celery'},
    },
)

if __name__ == '__main__':
    celery_app.start()