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
import os
from datetime import datetime, timedelta
import asyncio
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError
from telethon import TelegramClient

logger = logging.getLogger(__name__)

class MassDMError(Exception):
    """Custom exception for mass DM failures."""
    def __init__(self, message, errors):
        super().__init__(message)
        self.message_text = message  # Store message as attribute
        self.errors = errors

async def _mass_dm_runner(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    message = config.get('message')
    stop_after_hours = config.get('stop_after_hours')
    csv_file_path = config.get('csv_file_path')
    image_file_path = config.get('image_file_path')
    rate_limit_per_hour = config.get('rate_limit_per_hour')
    delay_seconds = config.get('delay_seconds')
    min_delay_seconds = config.get('min_delay_seconds')
    max_delay_seconds = config.get('max_delay_seconds')

    if image_file_path and not os.path.exists(image_file_path):
        raise FileNotFoundError(f"Image file not found at {image_file_path}")

    # Check if this is a batch job with pre-assigned user IDs
    ids = []
    if job.batch_user_ids:
        # Use pre-assigned batch user IDs
        try:
            ids = json.loads(job.batch_user_ids)
            logger.info(
                f"Job {job.id} using batch user IDs. "
                f"Batch {job.batch_number}/{job.total_batches} - {len(ids)} users"
            )
        except json.JSONDecodeError:
            raise Exception("Failed to parse batch_user_ids")
    elif csv_file_path:
        # Use traditional CSV file approach
        try:
            user_data = pd.read_csv(csv_file_path)
            # Handle both old (capitalized) and new (lowercase) formats
            if 'user_id' in user_data.columns:
                ids = user_data['user_id'].tolist()
            elif 'User ID' in user_data.columns:
                ids = user_data['User ID'].tolist()
            elif 'username' in user_data.columns:
                ids = user_data['username'].tolist()
            elif 'Username' in user_data.columns:
                ids = user_data['Username'].tolist()
            else:
                raise Exception("CSV must have a 'user_id'/'User ID' or 'username'/'Username' column.")
        except FileNotFoundError:
            raise Exception(f"CSV file not found at path: {csv_file_path}")
    else:
        raise Exception("No user IDs provided (either batch_user_ids or csv_file_path required)")
    
    # Initialize job with total planned messages
    job.messages_planned = len(ids)
    db.commit()

    client = await session_manager.get_client(account)
    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None
    sent_count = 0
    error_messages = []
    message_timestamps = []
    
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
                if image_file_path:
                    await client.send_file(uid, image_file_path, caption=message)
                else:
                    await client.send_message(uid, message)
                
                sent_count += 1
                message_timestamps.append(datetime.utcnow())
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

            except FloodWaitError as e:
                logger.warning(f"Flood wait error for job {job.id}: {e}. Retrying in {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                # Retry sending after flood wait
                try:
                    if image_file_path:
                        await client.send_file(uid, image_file_path, caption=message)
                    else:
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

async def _execute_mass_dm_with_client_cache(job_id: int, db: Session, client_cache: dict):
    """Execute mass DM job with cached Telegram client for better concurrency"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return
    
    account_id = job.telegram_account_id
    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
    
    if not account:
        raise Exception(f"Account {account_id} not found")
    
    job.status = 'running'
    job.started_at = datetime.utcnow()
    db.commit()
    
    try:
        await _mass_dm_runner(job, db)
    except MassDMError as e:
        job.status = 'failed'
        error_summary = ", ".join(e.errors[:5])
        if len(e.errors) > 5:
            error_summary += f" and {len(e.errors) - 5} more."
        job.error_message = f"{e.message_text} Examples: {error_summary}"
    except Exception as e:
        logger.error(f"Error executing Mass DM job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
    else:
        if job.status == 'running':
            job.status = 'completed'
        job.completed_at = datetime.utcnow()
    finally:
        db.commit()
        db.close()

@celery_app.task(bind=True, max_retries=3)
def mass_dm_account_task(self, job_id: int):
    """Synchronous wrapper for async mass DM task"""
    db: Session = SessionLocal()
    account_id = None
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found.")
            return
        
        account_id = job.telegram_account_id
        asyncio.run(_execute_mass_dm_with_client_cache(job_id, db, {}))
        
    except Exception as e:
        logger.error(f"Error executing Mass DM Account job {job_id}: {e}")
    finally:
        try:
            if account_id:
                logger.info(f"Disconnecting client for account {account_id} from job {job_id}")
                asyncio.run(session_manager.disconnect_client(account_id))
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup for job {job_id}: {cleanup_error}")
        finally:
            db.close()
