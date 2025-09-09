from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import csv
import os
import asyncio
from datetime import datetime, timedelta
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

async def _group_monitor_runner(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    group_usernames = config.get('group_usernames', [])
    keywords = config.get('keywords', [])
    monitored_users = config.get('monitored_users', [])
    limit = config.get('limit', 100)

    client = await session_manager.get_client(account)

    found_messages = []
    processed_messages = 0
    error_messages = []

    # Set the time window to the last 7 days
    offset_date = datetime.utcnow() - timedelta(days=7)

    async with client:
        for group_username in group_usernames:
            try:
                group = await client.get_entity(group_username)
            except (ValueError, TypeError):
                logger.warning(f"Could not find group '{group_username}' for job {job.id}. Skipping.")
                error_messages.append(f"Group '{group_username}' not found.")
                continue

            async for message in client.iter_messages(group, limit=limit):
                # Stop if the message is older than the offset date
                if message.date.replace(tzinfo=None) < offset_date:
                    break

                processed_messages += 1
                msg_text = message.text or ""
                sender_username = getattr(message.sender, 'username', None) if message.sender else None

                if (
                    any(keyword.lower() in msg_text.lower() for keyword in keywords)
                    or (sender_username in monitored_users if sender_username else False)
                ):
                    found_messages.append({
                        "group": group_username,
                        "user": sender_username,
                        "text": msg_text,
                        "timestamp": message.date.isoformat() if message.date else ""
                    })

                if processed_messages % 10 == 0:
                    job.progress = (processed_messages / (limit * len(group_usernames))) * 100
                    db.commit()

    if not found_messages and error_messages:
        raise Exception(f"Job failed. Could not find any of the specified groups. Errors: {', '.join(error_messages)}")

    filename = f"/app/job_results/monitored_messages_job_{job.id}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["group", "user", "text", "timestamp"])
        writer.writeheader()
        for msg in found_messages:
            writer.writerow(msg)

    if error_messages:
        job.error_message = f"Completed with some errors: {', '.join(error_messages)}"
        db.commit()


@celery_app.task(bind=True, max_retries=3)
def group_monitor_task(self, job_id: int):
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

        asyncio.run(_group_monitor_runner(job, db))

        job.status = 'completed'
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Group monitor job {job.id} completed successfully.")

    except FloodWaitError as e:
        logger.warning(f"Flood wait error for job {job_id}: {e}. Retrying in {e.seconds} seconds.")
        self.retry(countdown=e.seconds)
    except Exception as e:
        logger.error(f"Error executing group monitor job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            logger.info(f"Disconnecting client for account {account_id} from job {job_id}")
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()
