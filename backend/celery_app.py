from celery import Celery
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
    ]
)

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
    worker_max_tasks_per_child=1000,
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,       # 2 hour hard limit
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    beat_schedule={
        'cleanup-stuck-jobs': {
            'task': 'core.cleanup_tasks.cleanup_stuck_jobs',
            'schedule': 300.0,  # Run every 5 minutes
        },
        'worker-health-check': {
            'task': 'core.cleanup_tasks.worker_health_check',
            'schedule': 600.0,  # Run every 10 minutes
        },
    },
    task_routes={
        'auto_promo.tasks.auto_promo_task': {'queue': 'long_tasks'},
        'group_monitor.tasks.group_monitor_task': {'queue': 'short_tasks'},
        'mass_dm_account.tasks.mass_dm_account_task': {'queue': 'long_tasks'},
        'mass_dm_bot.tasks.mass_dm_bot_task': {'queue': 'long_tasks'},
        'scrape_user_id.tasks.scrape_users_task': {'queue': 'short_tasks'},
        'core.cleanup_tasks.*': {'queue': 'celery'},  # Default queue for cleanup tasks
    },
)

if __name__ == '__main__':
    celery_app.start()