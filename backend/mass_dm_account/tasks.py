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
from celery.exceptions import SoftTimeLimitExceeded
from core.account_protection import rate_limiter, AccountHealthStatus, sync_health_to_db
from utils.template_processor import process_template_variations

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
            # Usernames can be: @name, digits, alphanumeric with underscores, underscores
            is_numeric = user_id.isdigit()
            is_username = user_id.startswith('@') or bool(user_id and all(c.isalnum() or c == '_' for c in user_id))
            
            if is_numeric or is_username:
                # Clean up username - ensure @ prefix if it doesn't start with digits
                if is_username and not user_id.startswith('@') and not user_id.isdigit():
                    user_ids.append(f"@{user_id}" if not user_id.startswith('@') else user_id)
                else:
                    user_ids.append(user_id)
            else:
                logger.warning(f"Row {idx}: Skipping invalid format: {user_id}")
        
        except Exception as e:
            logger.warning(f"Row {idx}: Error processing value: {e}")
            continue
    
    if not user_ids:
        raise Exception(f"No valid user IDs found in CSV (read {len(df)} rows)")
    
    # DEDUPLICATE while preserving order
    seen = set()
    deduplicated_ids = []
    for uid in user_ids:
        if uid not in seen:
            seen.add(uid)
            deduplicated_ids.append(uid)
    
    if len(deduplicated_ids) < len(user_ids):
        logger.warning(f"CSV contained {len(user_ids)} rows but only {len(deduplicated_ids)} unique user IDs (removed {len(user_ids) - len(deduplicated_ids)} duplicates)")
    
    logger.info(f"Successfully extracted {len(deduplicated_ids)} unique user IDs from CSV")
    return deduplicated_ids


def _normalize_user_id(uid) -> int | str:
    """
    Convert user ID to proper format for Telethon.
    IDs must be integers, usernames stay as strings with @ prefix.
    """
    uid_str = str(uid).strip()
    
    # If it's a username (starts with @), keep it as is
    if uid_str.startswith('@'):
        return uid_str
    
    # Try to convert to integer
    try:
        return int(uid_str)
    except ValueError:
        logger.warning(f"Cannot convert '{uid_str}' to integer, treating as username")
        return uid_str


async def _send_message_with_retry(
    client, uid, message: str, image_file_path: str, job_id: int, result_dict: dict,
    delay_seconds: int = None, min_delay_seconds: int = None, max_delay_seconds: int = None
) -> tuple[str, bool, str]:
    """
    Send a single message with retry logic and error handling.
    Applies random delay BEFORE sending to space out messages.
    Returns (user_id_str, success, error_message)
    """
    uid_original = str(uid).strip()
    uid_normalized = _normalize_user_id(uid)
    
    # Apply delay BEFORE sending message
    if isinstance(min_delay_seconds, int) and isinstance(max_delay_seconds, int) and max_delay_seconds >= min_delay_seconds and min_delay_seconds >= 0:
        sleep_time = random.randint(min_delay_seconds, max_delay_seconds)
        logger.debug(f"Job {job_id}: Waiting {sleep_time}s before sending to {uid_original}")
        await asyncio.sleep(sleep_time)
    elif isinstance(delay_seconds, int) and delay_seconds >= 0:
        logger.debug(f"Job {job_id}: Waiting {delay_seconds}s before sending to {uid_original}")
        await asyncio.sleep(delay_seconds)
    
    try:
        if image_file_path:
            await client.send_file(uid_normalized, image_file_path, caption=message)
        else:
            await client.send_message(uid_normalized, message)
        logger.info(f"Job {job_id}: Sent message to {uid_original}")
        result_dict['sent'] += 1
        return (uid_original, True, "")
    
    except FloodWaitError as e:
        """
        CRITICAL PROTECTION: Handle Telegram FloodWait
        - Log severity categorization
        - Track account health
        - Implement progressive backoff
        - Auto-stop if account at risk
        """
        flood_seconds = getattr(e, 'seconds', 30)
        logger.warning(f"Job {job_id}: Flood wait {flood_seconds}s for {uid_original}")
        
        # Use rate limiter to handle flood intelligently
        account_id = result_dict.get('account_id')
        if account_id:
            should_continue, action, details = rate_limiter.handle_flood_incident(
                account_id, flood_seconds, job_id
            )
            
            # Log flood incident details
            logger.critical(
                f"FLOOD INCIDENT DETAILS: Job {job_id}, Account {account_id}, "
                f"Action: {action}, Messages this hour: {details.get('hour_messages')}, "
                f"Messages today: {details.get('day_messages')}, "
                f"Severity: {details.get('severity')}"
            )
            
            # If account suspended, stop immediately
            if not should_continue:
                result_dict['should_stop'] = True
                result_dict['stop_reason'] = f"FLOOD PROTECTION ENGAGED: {action}"
                # Sync health to DB on critical flood stop
                sync_health_to_db(account_id, db, extra_stats={
                    "messages_sent_today": result_dict.get('sent', 0)
                })
                return (uid_original, False, f"Account protection triggered: {action}")
            
            # If continuing, use extended backoff delay
            if action == "CONTINUE_WITH_BACKOFF":
                backoff_seconds = int(flood_seconds * 1.5) + 10  # Extra safety margin
                logger.warning(f"Job {job_id}: Applying backoff delay {backoff_seconds}s before retry")
                await asyncio.sleep(backoff_seconds)
        else:
            # Fallback if account_id not available
            await asyncio.sleep(flood_seconds + 10)
        
        # Attempt retry
        try:
            if image_file_path:
                await client.send_file(uid_normalized, image_file_path, caption=message)
            else:
                await client.send_message(uid_normalized, message)
            logger.info(f"Job {job_id}: Retry successful for {uid_original} after flood wait")
            result_dict['sent'] += 1
            return (uid_original, True, "")
        except Exception as retry_e:
            return (uid_original, False, f"Retry failed: {retry_e.__class__.__name__}")
    
    except (UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError) as e:
        logger.warning(f"Job {job_id}: Cannot send to {uid_original}: {e.__class__.__name__}")
        return (uid_original, False, e.__class__.__name__)
    
    except Exception as e:
        logger.error(f"Job {job_id}: Unexpected error for {uid_original}: {type(e).__name__}: {e}")
        return (uid_original, False, type(e).__name__)


async def _mass_dm_runner(job: Job, db: Session):
    """
    Execute the actual mass DM operation with AsyncIO pooling.
    Supports 10-20 concurrent message sends per job.
    """
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    raw_message_template = config.get('message', '')
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

    # Get authenticated client - will fail if account not logged in
    try:
        client = await session_manager.get_client(account)
    except RuntimeError as auth_err:
        logger.error(f"Job {job.id}: Authentication failed: {auth_err}")
        raise Exception(f"Account not authenticated. Please log in to this account first. ({str(auth_err)})")
    
    stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None
    error_messages = []
    message_timestamps = []
    result_dict = {'sent': 0, 'account_id': account.id, 'should_stop': False, 'stop_reason': ''}
    
    # PROTECTION: Initialize account in rate limiter
    rate_limiter.update_account_stats(account.id)
    
    # PROTECTION: Check account health before starting
    health = rate_limiter.get_account_health(account.id)
    if health['health_status'] in ['suspended', 'restricted']:
        raise Exception(
            f"Account {account.id} is {health['health_status']}. "
            f"Cannot start job. Consecutive floods: {health['consecutive_floods']}"
        )
    
    logger.info(
        f"Job {job.id}: Account health check - Status: {health['health_status']}, "
        f"Messages this hour: {health['hour_messages']}, Messages today: {health['day_messages']}, "
        f"Current delays: {health['current_min_delay']}-{health['current_max_delay']}s"
    )
    
    # Use dynamic delays from rate limiter if available
    if health['current_min_delay'] > (min_delay_seconds or 0):
        min_delay_seconds = health['current_min_delay']
        max_delay_seconds = health['current_max_delay']
        logger.info(f"Job {job.id}: Using adjusted delays {min_delay_seconds}-{max_delay_seconds}s due to flood history")
    
    async with client:
        # SEQUENTIAL sending with proper delay spacing (not concurrent)
        # This ensures delays are properly applied between messages
        for i, uid in enumerate(ids):
            # PROTECTION: Check if we should stop due to flood protection
            if result_dict.get('should_stop'):
                logger.error(
                    f"Job {job.id}: AUTO-STOPPING due to flood protection. "
                    f"Reason: {result_dict['stop_reason']}"
                )
                job.status = 'paused'
                break
            
            # PROTECTION: Check account rate limits
            is_safe, reason = rate_limiter.check_rate_limits(account.id)
            if not is_safe:
                logger.warning(f"Job {job.id}: Rate limit reached - {reason}. Stopping job.")
                job.status = 'paused'
                job.error_message = f"Rate limit reached: {reason}"
                break
            
            # Check global status
            db.refresh(job)
            db.refresh(account)
            if job.status != 'running' or account.status != 'active':
                logger.info(f"Job {job.id} stopped. Status: {job.status}, Account: {account.status}")
                break
            
            if stop_time and datetime.utcnow() >= stop_time:
                logger.info(f"Job {job.id} reached time limit of {stop_after_hours} hours")
                job.status = 'completed'
                break
            
            # Rate limiting check
            if rate_limit_per_hour:
                current_time = datetime.utcnow()
                one_hour_ago = current_time - timedelta(hours=1)
                message_timestamps[:] = [t for t in message_timestamps if t > one_hour_ago]
                if len(message_timestamps) >= rate_limit_per_hour:
                    logger.info(f"Job {job.id}: Rate limit reached, waiting 60s")
                    await asyncio.sleep(60)
                    continue
            
            # APPLY DELAY BEFORE EACH MESSAGE SEND
            if i > 0:  # Skip delay for first message
                if isinstance(min_delay_seconds, int) and isinstance(max_delay_seconds, int) and max_delay_seconds >= min_delay_seconds and min_delay_seconds >= 0:
                    sleep_time = random.randint(min_delay_seconds, max_delay_seconds)
                    logger.info(f"Job {job.id}: Waiting {sleep_time}s before sending message {i+1}/{len(ids)}")
                    await asyncio.sleep(sleep_time)
                elif isinstance(delay_seconds, int) and delay_seconds >= 0:
                    logger.info(f"Job {job.id}: Waiting {delay_seconds}s before sending message {i+1}/{len(ids)}")
                    await asyncio.sleep(delay_seconds)
                else:
                    # Default fallback delay
                    default_delay = random.randint(30, 120)
                    logger.info(f"Job {job.id}: Applying default delay {default_delay}s before sending message {i+1}/{len(ids)}")
                    await asyncio.sleep(default_delay)
            
            # Evaluate template for this specific message
            current_message = process_template_variations(raw_message_template)
            
            # Send message WITHOUT additional delay (delay already applied above)
            uid_str, success, error_msg = await _send_message_with_retry(
                client, uid, current_message, image_file_path, job.id, result_dict,
                delay_seconds=None,  # No delay inside function - already applied above
                min_delay_seconds=None,
                max_delay_seconds=None
            )
            
            if success:
                message_timestamps.append(datetime.utcnow())
                logger.info(f"Job {job.id}: Successfully sent message {i+1}/{len(ids)} to {uid_str}")
            else:
                error_messages.append(f"{uid_str}: {error_msg}")
                logger.warning(f"Job {job.id}: Failed to send message {i+1}/{len(ids)} to {uid_str}: {error_msg}")
            
            # Update progress
            job.messages_sent = result_dict['sent']
            job.completion_percentage = (result_dict['sent'] / len(ids)) * 100.0
            job.progress = int(job.completion_percentage)
            
            # Commit progress after EVERY message (was every 5 messages)
            # This ensures real-time progress updates visible to users
            db.commit()
            logger.info(f"Job {job.id}: Progress {result_dict['sent']}/{len(ids)} ({job.progress}%)")
    
    # Final update
    job.messages_sent = result_dict['sent']
    job.completion_percentage = (result_dict['sent'] / len(ids)) * 100.0
    job.progress = int(job.completion_percentage)
    
    # PROTECTION: Track sent messages for rate limiting
    rate_limiter.update_account_stats(account.id, messages_sent=result_dict['sent'])
    
    # PROTECTION: Get final account health
    final_health = rate_limiter.get_account_health(account.id)
    
    # Auto-complete
    if result_dict['sent'] >= len(ids):
        logger.info(
            f"Job {job.id} completed successfully! All {len(ids)} messages sent. "
            f"Account health: {final_health['health_status']}"
        )
        # PROTECTION: Reset flood counter on successful completion
        rate_limiter.record_flood_recovery(account.id)
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
    elif result_dict.get('should_stop'):
        logger.warning(
            f"Job {job.id} paused due to flood protection after {result_dict['sent']}/{len(ids)} messages. "
            f"Reason: {result_dict['stop_reason']}"
        )
        job.error_message = f"Paused: {result_dict['stop_reason']}"
        if job.status == 'running':
            job.status = 'paused'
    
    db.commit()
    
    # Summary with protection status
    logger.info(
        f"Job {job.id} final status: {job.status}, "
        f"Sent: {result_dict['sent']}/{len(ids)}, "
        f"Account health: {final_health['health_status']}, "
        f"Hour messages: {final_health['hour_messages']}, "
        f"Day messages: {final_health['day_messages']}"
    )
    
    if error_messages:
        error_text = f"Completed with {len(error_messages)}/{len(ids)} errors"
        examples = "; ".join(error_messages[:3])
        logger.warning(f"Job {job.id}: {error_text}. Examples: {examples}")
    
    if final_health['consecutive_floods'] > 0:
        logger.critical(
            f"⚠️  ACCOUNT AT RISK: Job {job.id} - Account {account.id} has {final_health['consecutive_floods']} "
            f"consecutive flood incidents. Status: {final_health['health_status']}. "
            f"Last incident: {final_health['recent_incidents'][-1] if final_health['recent_incidents'] else 'None'}"
        )


from core.human_aware_task import HumanAwareTask

@celery_app.task(base=HumanAwareTask, bind=True, max_retries=3)
def mass_dm_account_task(self, job_id: int):
    """
    Main Celery task for mass DM operations.
    
    This wrapper handles:
    - Database session management
    - Proper error handling and logging
    - Client cleanup
    - Status updates
    - Event loop management for Telethon async operations
    """
    db: Session = SessionLocal()
    account_id = None
    loop = None
    
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
        
        # Create and run event loop properly for Celery prefork worker
        try:
            # Try to get existing event loop (in case it exists from parent)
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No event loop exists, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async operation
        loop.run_until_complete(_mass_dm_runner(job, db))
        
        # Mark as completed if still running
        if job.status == 'running':
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Mass DM job {job_id} completed successfully")
        
    except SoftTimeLimitExceeded:
        logger.warning(f"Mass DM job {job_id} hit soft time limit — pausing with progress saved")
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = 'paused'
                job.error_message = (
                    f"Paused: Celery soft time limit reached. "
                    f"Progress saved: {job.messages_sent}/{job.messages_planned} messages sent."
                )
                db.commit()
        except Exception as pause_err:
            logger.error(f"Failed to pause job {job_id} on SoftTimeLimitExceeded: {pause_err}")

    except Exception as e:
        logger.error(f"Mass DM job {job_id} failed: {type(e).__name__}: {e}", exc_info=True)
        if db and job:
            job.status = 'failed'
            job.error_message = f"{type(e).__name__}: {str(e)}"
            try:
                db.commit()
            except Exception as commit_err:
                logger.error(f"Failed to update job status: {commit_err}")
    
    finally:
        # Cleanup
        try:
            if account_id and loop:
                # Sync final account health before disconnecting
                sync_health_to_db(account_id, db, extra_stats={
                    "messages_sent_today": job.messages_sent if job else 0
                })
                logger.info(f"Disconnecting client for account {account_id}")
                loop.run_until_complete(session_manager.disconnect_client(account_id))
        except Exception as cleanup_err:
            logger.error(f"Cleanup error for job {job_id}: {cleanup_err}")
        finally:
            if loop and not loop.is_closed():
                try:
                    loop.close()
                except Exception as loop_err:
                    logger.warning(f"Error closing event loop: {loop_err}")
            if db:
                db.close()
