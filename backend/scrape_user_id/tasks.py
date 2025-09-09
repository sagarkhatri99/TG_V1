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
from datetime import datetime

logger = logging.getLogger(__name__)

async def _scrape_users_runner(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found for this job.")

    config = json.loads(job.config)
    group_username = config.get('group_username')
    if not group_username:
        raise Exception("Group username is missing from job config.")

    client = await session_manager.get_client(account)

    scraped_users = []
    processed_count = 0

    async with client:
        try:
            group = await client.get_entity(group_username)
            async for user in client.iter_participants(group):
                scraped_users.append({
                    'user_id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': user.phone
                })
                processed_count += 1
                if processed_count % 100 == 0:
                    job.progress = processed_count # A simple progress indicator
                    db.commit()

        except Exception as e:
            raise Exception(f"Failed to scrape group '{group_username}': {e}")

    # Save to CSV
    filename = f"/app/job_results/scraped_users_job_{job.id}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['user_id', 'username', 'first_name', 'last_name', 'phone'])
        writer.writeheader()
        writer.writerows(scraped_users)

    job.progress = processed_count
    job.total_tasks = processed_count # Store the final count
    db.commit()


@celery_app.task(bind=True, max_retries=3)
def scrape_users_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job with ID {job_id} not found.")
        return

    account_id = job.telegram_account_id

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        asyncio.run(_scrape_users_runner(job, db))

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Scrape users job {job.id} completed successfully.")

    except Exception as e:
        logger.error(f"Error executing scrape users job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            logger.info(f"Disconnecting client for account {account_id} from scrape job {job_id}")
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()
