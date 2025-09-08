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
from telethon.errors import FloodWaitError, ChatWriteForbiddenError

logger = logging.getLogger(__name__)

async def _auto_promo_runner(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    target_group = config.get('target_group')
    promo_message = config.get('promo_message')
    interval_seconds = config.get('interval_seconds', 3600)
    use_random_interval = config.get('use_random_interval', False)
    min_interval = config.get('min_interval')
    max_interval = config.get('max_interval')
    stop_after_hours = config.get('stop_after_hours')

    client = await session_manager.get_client(account)
    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None

    async with client:
        try:
            group = await client.get_entity(target_group)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Target group '{target_group}' not found or invalid. Please check the username or ID.") from e

        while True:
            db.refresh(job)
            db.refresh(account)
            if job.status != 'running' or account.status != 'active':
                logger.info(f"Auto promo job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
                if job.status == 'running':
                    job.status = 'paused'
                break

            if stop_time and datetime.utcnow() >= stop_time:
                logger.info(f"Auto promo job {job.id} reached its time limit of {stop_after_hours} hours.")
                job.status = 'completed'
                break
            
            try:
                await client.send_message(group, promo_message)
                logger.info(f"Sent promo message to {target_group} for job {job.id}")
                
                job.progress = (job.progress or 0) + 1
                db.commit()

            except ChatWriteForbiddenError as e:
                raise Exception(f"Cannot send message to '{target_group}'. The account may not have permission to post, or it might be a channel where posting is restricted.") from e
            except FloodWaitError as e:
                logger.warning(f"Flood wait error for job {job.id}: {e}. Retrying in {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                continue # Skip to the next iteration's sleep

            sleep_time = interval_seconds
            if use_random_interval and min_interval and max_interval:
                sleep_time = random.randint(min_interval, max_interval)

            logger.info(f"Job {job.id} sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)

@celery_app.task(bind=True, max_retries=3)
def auto_promo_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return
    
    account_id = job.telegram_account_id

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        asyncio.run(_auto_promo_runner(job, db))

        if job.status == 'running':
            job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error executing auto promo job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            logger.info(f"Disconnecting client for account {account_id} from job {job_id}")
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()