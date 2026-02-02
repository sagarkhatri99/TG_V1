from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
from core.human_aware_task import HumanAwareTask
import logging
import csv
import os
import asyncio
from datetime import datetime
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

async def _scrape_runner(job: Job, db: Session):
    """Async runner for scraping users from a group"""
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    import json
    config = json.loads(job.config)
    group_username = config.get('group_username', '')
    
    if not group_username:
        raise Exception("Group username not provided")

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"participants_{account.phone_number}_{timestamp}.csv"
    filepath = f"/app/job_results/{filename}"
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    logger.info(f"Starting scrape for group {group_username} using account {account.phone_number}")
    
    # Get client from session manager
    client = await session_manager.get_client(account)
    
    try:
        async with client:
            # Get the group entity
            group = await client.get_entity(group_username)
            
            # Get all participants
            participants = await client.get_participants(group, aggressive=True)
            
            # Write to CSV
            with open(filepath, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 'Phone'])
                for i, user in enumerate(participants):
                    writer.writerow([
                        user.id,
                        user.username or '',
                        user.first_name or '',
                        user.last_name or '',
                        user.phone or ''
                    ])
                    
                    # Update progress every 100 users
                    if (i + 1) % 100 == 0:
                        job.progress = min(95, int((i + 1) / len(participants) * 100))
                        job.messages_sent = i + 1
                        job.messages_planned = len(participants)
                        job.completion_percentage = job.progress
                        db.commit()
            
            logger.info(f"Scraped {len(participants)} participants to {filepath}")
            
            # Update job with final count
            job.messages_sent = len(participants)
            job.messages_planned = len(participants)
            db.commit()
            
            return len(participants)
    finally:
        # Disconnect client
        await session_manager.disconnect_client(account.id)


@celery_app.task(base=HumanAwareTask, bind=True, max_retries=3)
def scrape_users_task(self, job_id: int):
    """Celery task for scraping users from a Telegram group"""
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

        participant_count = asyncio.run(_scrape_runner(job, db))

        job.status = 'completed'
        job.progress = 100
        job.completion_percentage = 100.0
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Scrape job {job.id} completed successfully. Scraped {participant_count} users.")

    except FloodWaitError as e:
        logger.warning(f"Flood wait error for job {job.id}: {e}. Retrying in {e.seconds} seconds.")
        self.retry(countdown=e.seconds)
    except Exception as e:
        logger.error(f"Error executing scrape job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()
