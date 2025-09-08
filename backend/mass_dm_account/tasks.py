from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import pandas as pd
import random
import time
from datetime import datetime, timedelta
import asyncio
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError

logger = logging.getLogger(__name__)

class MassDMError(Exception):
    """Custom exception for mass DM failures."""
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors

async def _mass_dm_runner(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    message = config.get('message')
    stop_after_hours = config.get('stop_after_hours')
    csv_file_path = config.get('csv_file_path')

    try:
        user_data = pd.read_csv(csv_file_path)
        if 'user_id' in user_data.columns:
            ids = user_data['user_id'].tolist()
        elif 'username' in user_data.columns:
            ids = user_data['username'].tolist()
        else:
            raise Exception("CSV must have a 'user_id' or 'username' column.")
    except FileNotFoundError:
        raise Exception(f"CSV file not found at path: {csv_file_path}")

    client = await session_manager.get_client(account)
    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None
    sent_count = 0
    error_messages = []
    
    async with client:
        for i, uid in enumerate(ids):
            db.refresh(job)
            db.refresh(account)
            if job.status != 'running' or account.status != 'active':
                logger.info(f"Mass DM job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
                if job.status == 'running':
                    job.status = 'paused'
                break

            if stop_time and datetime.utcnow() >= stop_time:
                logger.info(f"Mass DM job {job.id} reached its time limit of {stop_after_hours} hours.")
                job.status = 'completed'
                break

            try:
                await client.send_message(uid, message)
                sent_count += 1
                job.progress = (sent_count / len(ids)) * 100
                
                if (i + 1) % 5 == 0 or (i + 1) == len(ids):
                    db.commit()

                sleep_time = random.randint(5, 300)
                logger.info(f"Job {job.id} sent message to {uid}, sleeping for {sleep_time} seconds.")
                await asyncio.sleep(sleep_time)

            except FloodWaitError as e:
                logger.warning(f"Flood wait error for job {job.id}: {e}. Retrying in {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                # Retry sending after flood wait
                try:
                    await client.send_message(uid, message)
                except Exception as retry_e:
                    error_messages.append(f"Failed to send to {uid} after flood wait: {retry_e.__class__.__name__}")

            except (ValueError, UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError) as e:
                logger.warning(f"Could not send message to {uid} for job {job.id}: {e.__class__.__name__}")
                error_messages.append(f"Could not send to {uid}: {e.__class__.__name__}")

            except Exception as e:
                logger.error(f"An unexpected error occurred for job {job.id} sending to {uid}: {e}")
                error_messages.append(f"Unexpected error for {uid}: {e.__class__.__name__}")

    if error_messages:
        raise MassDMError(f"Job completed with {len(error_messages)} errors.", error_messages)

@celery_app.task(bind=True, max_retries=3)
def mass_dm_account_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        asyncio.run(_mass_dm_runner(job, db))

        if job.status == 'running':
            job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except MassDMError as e:

        job.status = 'failed'
        # Store a summary of errors
        error_summary = ", ".join(e.errors[:5])
        if len(e.errors) > 5:
            error_summary += f" and {len(e.errors) - 5} more."
        job.error_message = f"{e.message} Examples: {error_summary}"
        db.commit()
    except Exception as e:
        logger.error(f"Error executing Mass DM Account job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            logger.info(f"Disconnecting client for account {account_id} from job {job_id}")
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()