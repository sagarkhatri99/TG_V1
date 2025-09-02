from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job
from database import SessionLocal
from telegram import Bot
import pandas as pd
import time
import random
import asyncio
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def _mass_dm_bot_runner(job: Job, db: Session):
    config = json.loads(job.config)
    bot_token = config.get('bot_token')
    message = config.get('message')
    stop_after_hours = config.get('stop_after_hours')
    csv_file_path = config.get('csv_file_path')

    bot = Bot(token=bot_token)

    user_data = pd.read_csv(csv_file_path)
    if 'chat_id' in user_data.columns:
        ids = user_data['chat_id'].tolist()
    else:
        raise Exception("CSV must have a 'chat_id' column for bot-based DMs.")

    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None

    sent_count = 0
    for i, uid in enumerate(ids):
        db.refresh(job)
        if job.status != 'running':
            logger.info(f"Mass DM Bot job {job.id} stopped. Job status: {job.status}")
            if job.status == 'running':
                job.status = 'paused'
            break

        if stop_time and datetime.utcnow() >= stop_time:
            logger.info(f"Mass DM Bot job {job.id} reached its time limit of {stop_after_hours} hours.")
            job.status = 'completed'
            break

        await bot.send_message(chat_id=uid, text=message)
        sent_count += 1
        job.progress = (sent_count / len(ids)) * 100
        
        # Commit progress in batches of 5
        if sent_count % 5 == 0 or sent_count == len(ids):
            db.commit()

        sleep_time = random.randint(5, 300)
        logger.info(f"Job {job.id} sent message to {uid}, sleeping for {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

@celery_app.task(bind=True, max_retries=3)
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

    except Exception as e:
        logger.error(f"Error executing Mass DM Bot job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()