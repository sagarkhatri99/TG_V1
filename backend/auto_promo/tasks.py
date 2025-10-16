from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import random
import time
from datetime import datetime, timedelta
import asyncio
import os
from pyrogram.errors import FloodWait, ChatWriteForbidden

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, queue='telegram_jobs')
def send_promo(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return

    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account or job.status != 'running' or account.status != 'active':
        logger.info(f"Auto promo job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
        if job.status == 'running':
            job.status = 'paused'
        db.commit()
        return

    config = json.loads(job.config)
    target_group = config.get('target_group')
    promo_message = config.get('promo_message')
    image_file_path = config.get('image_file_path')
    interval_seconds = config.get('interval_seconds', 3600)
    use_random_interval = config.get('use_random_interval', False)
    min_interval = config.get('min_interval')
    max_interval = config.get('max_interval')

    try:
        async def _send():
            client = await session_manager.get_client(account)
            async with client:
                group = await client.get_entity(target_group)
                if image_file_path:
                    await client.send_file(group, image_file_path, caption=promo_message)
                else:
                    await client.send_message(group, promo_message)
        asyncio.run(_send())

        job.messages_sent = (job.messages_sent or 0) + 1
        db.commit()

        sleep_time = interval_seconds
        if use_random_interval and min_interval and max_interval:
            sleep_time = random.randint(min_interval, max_interval)

        send_promo.apply_async(args=[job_id], countdown=sleep_time)

    except Exception as e:
        logger.error(f"Error sending promo for job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, queue='telegram_jobs')
def auto_promo_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()
        send_promo.delay(job_id)
    except Exception as e:
        logger.error(f"Error starting auto promo job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()