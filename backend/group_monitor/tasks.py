from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import os

logger = logging.getLogger(__name__)

async def _monitor_groups(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    groups = config.get('groups', [])
    keywords = config.get('keywords', [])
    users = config.get('users', [])
    limit = config.get('limit', 100)

    results = []

    client = await session_manager.get_client(account)

    offset_date = datetime.utcnow() - timedelta(days=7)

    for group in groups:
        try:
            async for message in client.get_chat_history(group, limit=limit, offset_date=offset_date):
                if not message.text:
                    continue

                match = False
                if any(keyword.lower() in message.text.lower() for keyword in keywords):
                    match = True

                if message.from_user and message.from_user.username in users:
                    match = True

                if match:
                    results.append({
                        'group': group,
                        'message_id': message.id,
                        'sender_id': message.from_user.id,
                        'sender_username': message.from_user.username,
                        'message': message.text,
                        'date': message.date
                    })
        except Exception as e:
            logger.error(f"Error monitoring group {group} for job {job.id}: {e}")

    if results:
        result_dir = "/app/results"
        os.makedirs(result_dir, exist_ok=True)
        result_path = os.path.join(result_dir, f"group_monitor_{job.id}.csv")
        df = pd.DataFrame(results)
        df.to_csv(result_path, index=False)
        job.result_path = result_path


@celery_app.task(bind=True, max_retries=3, queue='telegram_jobs')
def monitor_groups_task(self, job_id: int):
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

        asyncio.run(_monitor_groups(job, db))

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error executing group monitor job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()