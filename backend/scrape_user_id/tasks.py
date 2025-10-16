from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import pandas as pd
from datetime import datetime
import asyncio
import os
from pyrogram import Client

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, queue='telegram_jobs')
def scrape_users_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return

    config = json.loads(job.config)
    phone = config.get('phone')
    api_id = config.get('api_id')
    api_hash = config.get('api_hash')
    group = config.get('group')

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        async def _scrape():
            async with Client(f"scrape_{phone}", api_id, api_hash, in_memory=True) as app:
                participants = []
                async for member in app.get_chat_members(group):
                    participants.append({
                        'user_id': member.user.id,
                        'username': member.user.username,
                        'first_name': member.user.first_name,
                        'last_name': member.user.last_name,
                    })

                result_dir = "/app/results"
                os.makedirs(result_dir, exist_ok=True)
                result_path = os.path.join(result_dir, f"participants_{phone}.csv")
                df = pd.DataFrame(participants)
                df.to_csv(result_path, index=False)
                job.result_path = result_path

        asyncio.run(_scrape())

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error executing scrape users job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()