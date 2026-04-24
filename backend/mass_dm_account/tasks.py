"""
mass_dm_account/tasks.py

Refactored for production stability and serialization:
- Fix 1: Single asyncio.run() caller.
- Fix 3: Short-lived DB sessions (get_short_session).
- Fix E: AccountSnapshot used for Telethon client creation.
- Fix A: Redis-based per-account locking.
- Fix B: Progress checkpointing with stable ORDER BY.
- Gap 9: Idempotency guard at task start.
- core.account_protection.sync_health_to_db is now self-sufficient (Fix 3/Stage 2).
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
from redis import Redis
from celery.exceptions import SoftTimeLimitExceeded
from celery_app import celery_app
from core.account_protection import rate_limiter, sync_health_to_db
from core.db_utils import get_short_session, snapshot_account
from core.human_aware_task import HumanAwareTask
from core.session_manager import session_manager
from models import Job, TelegramAccount
from sqlalchemy.orm import joinedload
from telethon.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    UserBlockedError,
    UserIsBotError,
    UserPrivacyRestrictedError,
)
from utils.template_processor import process_template_variations

logger = logging.getLogger(__name__)


def extract_user_ids_from_csv(csv_file_path: str) -> list[str]:
    """Extract user IDs from CSV, handling multiple formats robustly."""
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    df = None

    for encoding in encodings:
        try:
            df = pd.read_csv(csv_file_path, encoding=encoding)
            logger.info(f"Successfully read CSV with encoding: {encoding}")
            break
        except Exception:
            continue

    if df is None:
        raise ValueError(f"Could not read CSV with any encoding: {encodings}")

    id_columns = [
        "user_id", "User ID", "userid", "user", "User",
        "username", "Username", "USERNAME", "id", "ID"
    ]

    matched_column = next((col for col in id_columns if col in df.columns), None)
    if matched_column is None:
        raise ValueError(f"CSV missing user ID column. Found: {list(df.columns)}")

    user_ids = []
    for val in df[matched_column]:
        if pd.isna(val):
            continue
        uid = str(val).strip()
        if not uid:
            continue

        if uid.isdigit() or uid.startswith("@") or all(c.isalnum() or c == "_" for c in uid):
            if not uid.isdigit() and not uid.startswith("@"):
                user_ids.append(f"@{uid}")
            else:
                user_ids.append(uid)

    # De-duplicate preserving order
    seen = set()
    return [x for x in user_ids if not (x in seen or seen.add(x))]


def _normalize_user_id(uid: str) -> int | str:
    """Normalize user ID for Telethon."""
    uid = uid.strip()
    if uid.startswith("@"):
        return uid
    try:
        return int(uid)
    except ValueError:
        return uid


async def _send_message_with_retry(
    client, uid: str, message: str, image_file_path: str, job_id: int,
    account_id: int, result_dict: dict,
    delay_config: dict
) -> tuple[str, bool, str]:
    """Sends a single message with Telegram flood protection logic."""
    uid_normalized = _normalize_user_id(uid)

    # Delay BEFORE sending
    min_delay = delay_config.get("min", 30)
    max_delay = delay_config.get("max", 120)
    sleep_time = random.randint(min_delay, max_delay)
    await asyncio.sleep(sleep_time)

    try:
        if image_file_path:
            await client.send_file(uid_normalized, image_file_path, caption=message)
        else:
            await client.send_message(uid_normalized, message)

        result_dict["sent"] += 1
        return uid, True, ""

    except FloodWaitError as e:
        flood_seconds = e.seconds
        logger.warning(f"Job {job_id}: FloodWait {flood_seconds}s for {uid}")

        should_continue, action, details = rate_limiter.handle_flood_incident(
            account_id, flood_seconds, job_id
        )

        if not should_continue:
            result_dict["should_stop"] = True
            result_dict["stop_reason"] = f"Protection triggered: {action}"
            # sync_health_to_db now opens its own session if db=None
            sync_health_to_db(account_id, extra_stats={"messages_sent_today": result_dict["sent"]})
            return uid, False, f"Flood stop: {action}"

        # Continue with backoff
        backoff = int(flood_seconds * 1.5) + 10
        await asyncio.sleep(backoff)

        # One retry
        try:
            if image_file_path:
                await client.send_file(uid_normalized, image_file_path, caption=message)
            else:
                await client.send_message(uid_normalized, message)
            result_dict["sent"] += 1
            return uid, True, ""
        except Exception as retry_e:
            return uid, False, f"Retry failed: {type(retry_e).__name__}"

    except (UserPrivacyRestrictedError, UserIsBotError, UserBlockedError, ChatWriteForbiddenError) as e:
        return uid, False, type(e).__name__
    except Exception as e:
        logger.error(f"Job {job_id}: Unexpected error for {uid}: {e}")
        return uid, False, type(e).__name__


async def _mass_dm_runner(job_id: int, account_snap, config: dict):
    """
    Async runner: sends messages sequentially with progress checkpointing.
    """
    account_id = account_snap.id
    raw_template = config.get("message", "")
    stop_after_hours = config.get("stop_after_hours")
    csv_file_path = config.get("csv_file_path")
    image_file_path = config.get("image_file_path")
    rate_limit_per_hour = config.get("rate_limit_per_hour")
    min_delay = config.get("min_delay_seconds")
    max_delay = config.get("max_delay_seconds")

    if image_file_path and not os.path.exists(image_file_path):
        raise FileNotFoundError(f"Image not found: {image_file_path}")

    # 1. Load targets (Stable ORDER BY or CSV order)
    # Fix B: determinism for checkpointing
    all_ids = []
    already_sent = 0

    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        if job.batch_user_ids:
            all_ids = json.loads(job.batch_user_ids)
        elif csv_file_path:
            all_ids = extract_user_ids_from_csv(csv_file_path)

        if not all_ids:
            raise ValueError("No targets found")

        already_sent = job.messages_sent or 0
        job.messages_planned = len(all_ids)

    # Slice targets based on progress checkpoint (Fix B)
    ids_to_process = all_ids[already_sent:]
    if not ids_to_process:
        logger.info(f"Job {job_id}: Already finished ({already_sent}/{len(all_ids)})")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "completed"
                job.completion_percentage = 100.0
        return

    # 2. Protection Init
    rate_limiter.update_account_stats(account_id)
    health = rate_limiter.get_account_health(account_id)
    if health["health_status"] in ("suspended", "restricted"):
        raise RuntimeError(f"Account {account_id} is {health['health_status']}")

    # Adjust delays based on health history
    active_min = max(min_delay or 30, health["current_min_delay"])
    active_max = max(max_delay or 120, health["current_max_delay"])
    delay_config = {"min": active_min, "max": active_max}

    client = await session_manager.get_client(account_snap)

    stop_time = (
        datetime.utcnow() + timedelta(hours=stop_after_hours)
        if stop_after_hours
        else None
    )
    result_dict = {"sent": already_sent, "should_stop": False, "stop_reason": ""}
    message_timestamps = []

    try:
        async with client:
            for i, uid in enumerate(ids_to_process):
                # Protection checks
                if result_dict["should_stop"]:
                    logger.error(f"Job {job_id}: Auto-stop: {result_dict['stop_reason']}")
                    break

                is_safe, reason = rate_limiter.check_rate_limits(account_id)
                if not is_safe:
                    with get_short_session() as db:
                        job = db.query(Job).filter(Job.id == job_id).first()
                        if job:
                            job.status = "paused"
                            job.error_message = f"Rate limit reached: {reason}"
                    break

                # External stop check
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if not job or job.status != "running":
                        logger.info(f"Job {job_id} stopped externally")
                        break

                if stop_time and datetime.utcnow() >= stop_time:
                    with get_short_session() as db:
                        job = db.query(Job).filter(Job.id == job_id).first()
                        if job:
                            job.status = "completed"
                    break

                # Hour rate limit check
                if rate_limit_per_hour:
                    cutoff = datetime.utcnow() - timedelta(hours=1)
                    message_timestamps = [t for t in message_timestamps if t > cutoff]
                    if len(message_timestamps) >= rate_limit_per_hour:
                        logger.info(f"Job {job_id}: Hour limit reached, sleeping 60s")
                        await asyncio.sleep(60)
                        # don't increment i, loop again
                        continue

                # Process template
                current_msg = process_template_variations(raw_template)

                # Send
                _, success, err = await _send_message_with_retry(
                    client, uid, current_msg, image_file_path, job_id, account_id,
                    result_dict, delay_config
                )

                if success:
                    message_timestamps.append(datetime.utcnow())

                # Fix B: Update progress checkpoint
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.messages_sent = result_dict["sent"]
                        total = len(all_ids)
                        job.completion_percentage = (job.messages_sent / total) * 100.0
                        job.progress = int(job.completion_percentage)

                        if job.messages_sent >= total:
                            job.status = "completed"
                            job.completed_at = datetime.utcnow()
                            rate_limiter.record_flood_recovery(account_id)

        # Final health sync
        rate_limiter.update_account_stats(account_id, messages_sent=result_dict["sent"])
        sync_health_to_db(account_id, extra_stats={"messages_sent_today": result_dict["sent"]})

    finally:
        # Fix 1: Disconnect in same loop
        await session_manager.disconnect_client(account_id)


@celery_app.task(
    base=HumanAwareTask,
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def mass_dm_account_task(self, job_id: int):
    """Celery task wrapper for mass DM account operation."""
    account_id = None

    # ── Gap 9: Idempotency guard ──────────────────────────────────────────────
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"mass_dm_account_task: job {job_id} not found")
            return
        if job.status not in ("queued", "pending"):
            logger.warning(f"mass_dm_account_task: job {job_id} status '{job.status}'")
            return
        account_id = job.telegram_account_id
        config = json.loads(job.config) if job.config else {}
        job.status = "running"
        job.started_at = datetime.utcnow()
    # session closed

    # ── Redis Lock ──────────────────────────────────────────────────────────
    redis_client = Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"), decode_responses=True)
    lock = redis_client.lock(f"lock:account:{account_id}", timeout=3600, blocking_timeout=0)

    if not lock.acquire(blocking=False):
        logger.warning(f"mass_dm_account_task: account {account_id} is locked. Job {job_id} will retry.")
        raise self.retry(countdown=30, max_retries=20)

    try:
        # ── Fix E: Snapshot account ───────────────────────────────────────────
        with get_short_session() as db:
            account = (
                db.query(TelegramAccount)
                .options(joinedload(TelegramAccount.proxy))
                .filter(TelegramAccount.id == account_id)
                .first()
            )
            if not account:
                raise RuntimeError(f"Account {account_id} not found")
            account_snap = snapshot_account(account)

        # ── Run async runner ──────────────────────────────────────────────────
        asyncio.run(_mass_dm_runner(job_id, account_snap, config))

    except Exception as e:
        logger.error(f"mass_dm_account_task: job {job_id} failed: {e}")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
        raise e
    finally:
        if account_id:
            # Final health sync
            rate_limiter.update_account_stats(account_id) # Ensure latest stats
            sync_health_to_db(account_id)
        
        lock.release()
