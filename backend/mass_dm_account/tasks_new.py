"""
Production-grade Mass DM task handler with robust CSV parsing and error handling.

Key improvements:
1. Bulletproof CSV parsing that extracts user_id from ANY column structure
2. Proper UTF-8 handling with fallback encodings
3. Fixed error handling (no more AttributeError on exceptions)
4. Comprehensive logging for debugging
5. Proper async/await patterns
"""

from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import pandas as pd
import random
import os
from datetime import datetime, timedelta
import asyncio
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError

logger = logging.getLogger(__name__)


def extract_user_ids_from_csv(csv_file_path: str) -> list:
    """
    Extract user IDs from CSV, handling multiple formats robustly.
    
    Supports:
    - user_id, User ID, userid columns
    - username, Username columns  
    - Multiple encodings (UTF-8, latin-1, cp1252)
    - Mixed format CSVs
    
    Returns list of user IDs as strings.
    Raises exception if no valid user ID column found.
    """
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    
    user_ids = []
    errors = []
    
    # Try multiple encodings for robust file reading
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_file_path, encoding=encoding)
            logger.info(f"Successfully read CSV with encoding: {encoding}")
            break
        except UnicodeDecodeError as e:
            errors.append(f"{encoding}: {str(e)}")
            continue
        except Exception as e:
            errors.append(f"{encoding}: {str(e)}")
            continue
    
    if df is None:
        error_msg = f"Could not read CSV with any encoding. Tried: {', '.join(encodings)}"
        raise Exception(error_msg)
    
    logger.info(f"CSV columns found: {list(df.columns)}")
    
    # Priority order for finding user ID column
    id_columns = [
        'user_id', 'User ID', 'userid', 'user', 'User',
        'username', 'Username', 'USERNAME',  
        'id', 'ID'
    ]
    
    # Find first matching column
    matched_column = None
    for col_name in id_columns:
        if col_name in df.columns:
            matched_column = col_name
            logger.info(f"Using column: {matched_column}")
            break
    
    if matched_column is None:
        raise Exception(
            f"CSV must have a user ID column. "
            f"Supported: {', '.join(id_columns)}. "
            f"Found: {', '.join(df.columns)}"
        )
    
    # Extract IDs - convert to string and clean
    for idx, val in enumerate(df[matched_column]):
        try:
            # Handle NaN, None, etc.
            if pd.isna(val):
                logger.warning(f"Row {idx}: Skipping empty value")
                continue
            
            # Convert to string and strip whitespace
            user_id = str(val).strip()
            
            # Skip empty strings
            if not user_id:
                logger.warning(f"Row {idx}: Skipping empty string")
                continue
            
            # Validate it's numeric (user_id) or valid username format
            if user_id.isdigit() or (user_id.startswith('@') or user_id.isalnum()):
                user_ids.append(user_id)
            else:
                logger.warning(f"Row {idx}: Skipping invalid format: {user_id}")
        
        except Exception as e:
            logger.warning(f"Row {idx}: Error processing value: {e}")
            continue
    
    if not user_ids:
        raise Exception(f"No valid user IDs found in CSV (read {len(df)} rows)")
    
    logger.info(f"Successfully extracted {len(user_ids)} user IDs from CSV")
    return user_ids


async def _mass_dm_runner(job: Job, db: Session):
    """Execute the actual mass DM operation."""
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

    # Load user IDs using robust parsing
    ids = []
    if job.batch_user_ids:
        try:
            ids = json.loads(job.batch_user_ids)
            logger.info(f"Job {job.id} using {len(ids)} batch user IDs")
        except json.JSONDecodeError:
            raise Exception("Failed to parse batch_user_ids")
    elif csv_file_path:
        # Use robust CSV parsing
        ids = extract_user_ids_from_csv(csv_file_path)
    else:
        raise Exception("No user IDs provided")
    
    if not ids:
        raise Exception("No user IDs extracted from source")

    # Initialize job
    job.messages_planned = len(ids)
    db.commit()

    client = await session_manager.get_client(account)
    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None
    sent_count = 0
    error_messages = []
    message_timestamps = []
    
    async with client:
        for i, uid in enumerate(ids):
            # Check status
            db.refresh(job)
            db.refresh(account)
            if job.status != 'running' or account.status != 'active':
                logger.info(f"Job {job.id} stopped. Status: {job.status}, Account: {account.status}")
                if job.status == 'running':
                    job.status = 'paused'
                break

            # Check time limit
            if stop_time and datetime.utcnow() >= stop_time:
                logger.info(f"Job {job.id} reached time limit of {stop_after_hours} hours")
                job.status = 'completed'
                break

            # Rate limiting
            if rate_limit_per_hour:
                current_time = datetime.utcnow()
                one_hour_ago = current_time - timedelta(hours=1)
                message_timestamps = [t for t in message_timestamps if t > one_hour_ago]
                if len(message_timestamps) >= rate_limit_per_hour:
                    logger.info(f"Job {job.id} rate limited. Waiting...")
                    await asyncio.sleep(60)
                    continue

            try:
                # Send message
                if image_file_path:
                    await client.send_file(uid, image_file_path, caption=message)
                else:
                    await client.send_message(uid, message)
                
                sent_count += 1
                message_timestamps.append(datetime.utcnow())
                job.messages_sent = sent_count
                job.completion_percentage = (sent_count / len(ids)) * 100.0
                job.progress = int(job.completion_percentage)
                
                logger.info(f"Job {job.id}: Sent message {sent_count}/{len(ids)} to {uid}")
                
                # Auto-complete if done
                if sent_count >= len(ids):
                    logger.info(f"Job {job.id} completed all {len(ids)} messages")
                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    break
                
                # Commit progress periodically
                if (i + 1) % 5 == 0 or (i + 1) == len(ids):
                    db.commit()

                # Apply delay
                if isinstance(min_delay_seconds, int) and isinstance(max_delay_seconds, int) and max_delay_seconds >= min_delay_seconds and min_delay_seconds >= 0:
                    sleep_time = random.randint(min_delay_seconds, max_delay_seconds)
                elif isinstance(delay_seconds, int) and delay_seconds >= 0:
                    sleep_time = delay_seconds
                else:
                    sleep_time = random.randint(5, 300)
                
                await asyncio.sleep(sleep_time)

            except FloodWaitError as e:
                logger.warning(f"Job {job.id} flood wait: {e.seconds}s")
                await asyncio.sleep(e.seconds)
                try:
                    if image_file_path:
                        await client.send_file(uid, image_file_path, caption=message)
                    else:
                        await client.send_message(uid, message)
                    sent_count += 1
                    logger.info(f"Job {job.id}: Retry successful for {uid}")
                except Exception as retry_e:
                    error_messages.append(f"{uid}: Retry failed ({retry_e.__class__.__name__})")

            except (ValueError, UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError) as e:
                logger.warning(f"Job {job.id}: Cannot send to {uid}: {e.__class__.__name__}")
                error_messages.append(f"{uid}: {e.__class__.__name__}")

            except Exception as e:
                logger.error(f"Job {job.id}: Unexpected error for {uid}: {type(e).__name__}: {e}")
                error_messages.append(f"{uid}: {type(e).__name__}")

    # Summary
    if error_messages:
        error_text = f"Completed with {len(error_messages)}/{len(ids)} errors"
        examples = "; ".join(error_messages[:3])
        raise Exception(f"{error_text}. Examples: {examples}")


@celery_app.task(bind=True, max_retries=3)
def mass_dm_account_task(self, job_id: int):
    """
    Main Celery task for mass DM operations.
    
    This wrapper handles:
    - Database session management
    - Proper error handling and logging
    - Client cleanup
    - Status updates
    """
    db: Session = SessionLocal()
    account_id = None
    
    try:
        # Load job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        account_id = job.telegram_account_id
        
        # Mark as running
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Starting Mass DM job {job_id} for account {account_id}")
        
        # Execute async operation
        asyncio.run(_mass_dm_runner(job, db))
        
        # Mark as completed if still running
        if job.status == 'running':
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Mass DM job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Mass DM job {job_id} failed: {type(e).__name__}: {e}")
        job.status = 'failed'
        job.error_message = f"{type(e).__name__}: {str(e)}"
        db.commit()
    
    finally:
        # Cleanup
        try:
            if account_id:
                logger.info(f"Disconnecting client for account {account_id}")
                asyncio.run(session_manager.disconnect_client(account_id))
        except Exception as cleanup_err:
            logger.error(f"Cleanup error for job {job_id}: {cleanup_err}")
        finally:
            db.close()
