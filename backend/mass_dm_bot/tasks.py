from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job
from database import SessionLocal
from core.human_aware_task import HumanAwareTask
from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden
import pandas as pd
import time
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
import logging
from utils.template_processor import process_template_variations

logger = logging.getLogger(__name__)

class MassDMBotError(Exception):
    """Custom exception for mass DM bot failures."""
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors

async def _mass_dm_bot_runner(job: Job, db: Session):
    config = json.loads(job.config)
    bot_token = config.get('bot_token')
    message = process_template_variations(config.get('message', ''))
    stop_after_hours = config.get('stop_after_hours')
    csv_file_path = config.get('csv_file_path')
    delay_seconds = config.get('delay_seconds')
    min_delay_seconds = config.get('min_delay_seconds')
    max_delay_seconds = config.get('max_delay_seconds')

    if not bot_token:
        raise Exception("Bot token is missing from the job configuration.")

    bot = Bot(token=bot_token)

    try:
        user_data = pd.read_csv(csv_file_path)
        if 'chat_id' in user_data.columns:
            ids = user_data['chat_id'].tolist()
        else:
            raise Exception("CSV must have a 'chat_id' column for bot-based DMs.")
    except FileNotFoundError:
        raise Exception(f"CSV file not found at path: {csv_file_path}")
    
    # Initialize job with total planned messages
    job.messages_planned = len(ids)
    db.commit()

    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None
    sent_count = 0
    error_messages = []

    for i, uid in enumerate(ids):
        db.refresh(job)
        if job.status != 'running':
            logger.info(f"Mass DM Bot job {job.id} stopped. Status: {job.status}")
            if job.status == 'running':
                job.status = 'paused'
            break

        if stop_time and datetime.utcnow() >= stop_time:
            logger.info(f"Mass DM Bot job {job.id} reached its time limit of {stop_after_hours} hours.")
            job.status = 'completed'
            break
        
        try:
            await bot.send_message(chat_id=uid, text=message)
            sent_count += 1
            job.messages_sent = sent_count
            job.completion_percentage = (sent_count / len(ids)) * 100.0
            job.progress = int(job.completion_percentage)  # Keep existing progress field for compatibility

            # Auto-complete job when all messages sent
            if sent_count >= len(ids):
                logger.info(f"Job {job.id} completed (all {len(ids)} messages sent). Marking as completed.")
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                db.commit()
                break  # Exit the loop

            if (i + 1) % 5 == 0 or (i + 1) == len(ids):
                db.commit()

            if isinstance(min_delay_seconds, int) and isinstance(max_delay_seconds, int) and max_delay_seconds >= min_delay_seconds and min_delay_seconds >= 0:
                sleep_time = random.randint(min_delay_seconds, max_delay_seconds)
            elif isinstance(delay_seconds, int) and delay_seconds >= 0:
                sleep_time = delay_seconds
            else:
                sleep_time = random.randint(5, 300)
            logger.info(f"Job {job.id} sent message to {uid}, sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)

        except (BadRequest, Forbidden) as e:
            logger.warning(f"Could not send message to {uid} for job {job.id}: {e.message}")
            error_messages.append(f"Could not send to {uid}: {e.message}")
        except TelegramError as e:
            logger.error(f"A Telegram error occurred for job {job.id} sending to {uid}: {e.message}")
            error_messages.append(f"Telegram error for {uid}: {e.message}")
        except Exception as e:
            logger.error(f"An unexpected error occurred for job {job.id} sending to {uid}: {e}")
            error_messages.append(f"Unexpected error for {uid}: {e.__class__.__name__}")

    if error_messages:
        raise MassDMBotError(f"Job completed with {len(error_messages)} errors.", error_messages)

@celery_app.task(base=HumanAwareTask, bind=True, max_retries=3)
def mass_dm_bot_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return
    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        asyncio.run(_mass_dm_bot_runner(job, db))

        if job.status == 'running':
            job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except MassDMBotError as e:
        logger.error(f"Mass DM Bot job {job.id} finished with errors: {e.errors}")
        job.status = 'failed'
        error_summary = ", ".join(e.errors[:5])
        if len(e.errors) > 5:
            error_summary += f" and {len(e.errors) - 5} more."
        job.error_message = f"{e.message} Examples: {error_summary}"
        db.commit()
    except Exception as e:
        logger.error(f"Error executing Mass DM Bot job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()