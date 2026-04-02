from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
from core.human_aware_task import HumanAwareTask
from core.account_protection import rate_limiter, sync_health_to_db
import json
import logging
import random
import time
from datetime import datetime, timedelta
import asyncio
import os
from telethon.errors import FloodWaitError, ChatWriteForbiddenError
from celery.exceptions import SoftTimeLimitExceeded
from utils.template_processor import process_template_variations

logger = logging.getLogger(__name__)

async def _auto_promo_runner(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    target_group = config.get('target_group')
    raw_promo_message = config.get('promo_message', '')
    image_file_path = config.get('image_file_path')
    rate_limit_per_hour = config.get('rate_limit_per_hour')
    interval_seconds = config.get('interval_seconds', 3600)
    use_random_interval = config.get('use_random_interval', False)
    min_interval = config.get('min_interval')
    max_interval = config.get('max_interval')
    stop_after_hours = config.get('stop_after_hours')

    if image_file_path and not os.path.exists(image_file_path):
        raise FileNotFoundError(f"Image file not found at {image_file_path}")

    client = await session_manager.get_client(account)
    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None
    message_timestamps = []
    
    # For auto promo, we track messages as they are sent over time
    # Initialize with estimated planned messages based on rate and duration
    if stop_after_hours and rate_limit_per_hour:
        estimated_messages = stop_after_hours * rate_limit_per_hour
    elif stop_after_hours:
        estimated_messages = stop_after_hours  # Assume 1 message per hour by default
    else:
        estimated_messages = 24  # Default to 24 if no limit specified
    
    job.messages_planned = estimated_messages
    job.messages_sent = 0
    db.commit()

    async with client:
        try:
            group = await client.get_entity(target_group)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Target group '{target_group}' not found or invalid. Please check the username or ID.") from e

        last_yield_time = datetime.utcnow()
        yield_interval_minutes = 30  # Yield for other tasks every 30 minutes
        
        while True:
            db.refresh(job)
            db.refresh(account)
            
            # Check if we should yield to allow other tasks to run
            current_time = datetime.utcnow()
            if (current_time - last_yield_time).total_seconds() > (yield_interval_minutes * 60):
                logger.info(f"Auto promo job {job.id} taking a brief break after {yield_interval_minutes} minutes to allow other tasks")
                db.commit()  # Save current state
                await asyncio.sleep(30)  # Brief 30-second break
                last_yield_time = current_time
            
            if job.status != 'running' or account.status != 'active':
                logger.info(f"Auto promo job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
                if job.status == 'running':
                    job.status = 'paused'
                break

            if stop_time and datetime.utcnow() >= stop_time:
                logger.info(f"Auto promo job {job.id} reached its time limit of {stop_after_hours} hours.")
                job.status = 'completed'
                break

            # Rate limiting
            if rate_limit_per_hour:
                current_time = datetime.utcnow()
                one_hour_ago = current_time - timedelta(hours=1)
                message_timestamps = [t for t in message_timestamps if t > one_hour_ago]
                if len(message_timestamps) >= rate_limit_per_hour:
                    logger.info(f"Job {job.id} reached rate limit of {rate_limit_per_hour}/hour. Waiting...")
                    await asyncio.sleep(60) # Wait a minute before checking again
                    continue
            
            try:
                current_promo_message = process_template_variations(raw_promo_message)
                if image_file_path:
                    await client.send_file(group, image_file_path, caption=current_promo_message)
                else:
                    await client.send_message(group, current_promo_message)

                message_timestamps.append(datetime.utcnow())
                logger.info(f"Sent promo message to {target_group} for job {job.id}")
                
                # Update message tracking
                job.messages_sent = (job.messages_sent or 0) + 1
                if job.messages_planned > 0:
                    job.completion_percentage = (job.messages_sent / job.messages_planned) * 100.0
                else:
                    job.completion_percentage = min((job.messages_sent / 10) * 100.0, 100.0)  # Fallback calculation
                job.progress = int(job.completion_percentage)  # Keep existing progress field for compatibility
                
                # Auto-complete job when 100% reached
                if job.completion_percentage >= 100.0:
                    logger.info(f"Job {job.id} completed (100% reached). Marking as completed.")
                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    break  # Exit the loop
                
                db.commit()


            except ChatWriteForbiddenError as e:
                raise Exception(f"Cannot send message to '{target_group}'. The account may not have permission to post, or it might be a channel where posting is restricted.") from e
            except FloodWaitError as e:
                logger.warning(f"Flood wait error for job {job.id}: {e}. Retrying in {e.seconds} seconds.")
                # Sync health score to DB after flood event
                sync_health_to_db(account.id, db, extra_stats={
                    "messages_sent_today": job.messages_sent or 0
                })
                await asyncio.sleep(e.seconds)
                continue # Skip to the next iteration's sleep

            sleep_time = interval_seconds
            if use_random_interval and min_interval and max_interval:
                sleep_time = random.randint(min_interval, max_interval)

            logger.info(f"Job {job.id} sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)

@celery_app.task(base=HumanAwareTask, bind=True, max_retries=3)
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

    except SoftTimeLimitExceeded:
        logger.warning(f"Auto promo job {job_id} hit soft time limit — pausing with progress saved")
        try:
            if job:
                job.status = 'paused'
                job.error_message = (
                    f"Paused: Celery soft time limit reached. "
                    f"Progress saved: {job.messages_sent or 0}/{job.messages_planned or 0} messages sent."
                )
                db.commit()
        except Exception as pause_err:
            logger.error(f"Failed to pause auto promo job {job_id} on SoftTimeLimitExceeded: {pause_err}")

    except Exception as e:
        logger.error(f"Error executing auto promo job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            # Sync final health state to DB
            sync_health_to_db(account_id, db, extra_stats={
                "messages_sent_today": job.messages_sent or 0
            })
            logger.info(f"Disconnecting client for account {account_id} from job {job_id}")
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()