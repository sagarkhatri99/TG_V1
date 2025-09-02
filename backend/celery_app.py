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
)

if __name__ == '__main__':
    celery_app.start()
