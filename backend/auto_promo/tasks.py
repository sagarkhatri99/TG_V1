"""
auto_promo/tasks.py

Refactored for serial execution and stability:
- Fix 1: Single asyncio.run() caller.
- Fix 3: Short-lived DB sessions (get_short_session).
- Fix E: AccountSnapshot used for Telethon client creation.
- Fix A: Redis-based per-account locking.
- Gap 9: Idempotency guard at task start.
"""

import asyncio
import json
import logging
import os
import sqlite3
import random
from datetime import datetime, timedelta
from redis import Redis

from celery.exceptions import SoftTimeLimitExceeded
from celery_app import celery_app
from core.account_protection import rate_limiter, sync_health_to_db
from core.db_utils import get_short_session, snapshot_account
from core.human_aware_task import HumanAwareTask
from core.session_manager import session_manager
from models import Job, TelegramAccount
from sqlalchemy.orm import joinedload
from telethon.errors import ChatWriteForbiddenError, FloodWaitError
from utils.template_processor import process_template_variations

logger = logging.getLogger(__name__)


async def _auto_promo_runner(job_id: int, account_snap, config: dict):
    """Async runner for auto promo jobs."""
    target_group = config.get("target_group")
    raw_promo_message = config.get("promo_message", "")
    image_file_path = config.get("image_file_path")
    rate_limit_per_hour = config.get("rate_limit_per_hour")
    interval_seconds = config.get("interval_seconds", 3600)
    use_random_interval = config.get("use_random_interval", False)
    min_interval = config.get("min_interval")
    max_interval = config.get("max_interval")
    stop_after_hours = config.get("stop_after_hours")

    if image_file_path and not os.path.exists(image_file_path):
        raise FileNotFoundError(f"Image file not found at {image_file_path}")

    # Initial setup
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            if stop_after_hours and rate_limit_per_hour:
                estimated_messages = stop_after_hours * rate_limit_per_hour
            elif stop_after_hours:
                estimated_messages = stop_after_hours
            else:
                estimated_messages = 24
            job.messages_planned = estimated_messages
            job.messages_sent = 0

    client = await session_manager.get_client(account_snap)
    stop_time = (
        datetime.utcnow() + timedelta(hours=stop_after_hours)
        if stop_after_hours
        else None
    )
    message_timestamps = []

    try:
        async with client:
            try:
                group = await client.get_entity(target_group)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Target group '{target_group}' not found or invalid. "
                    "Please check the username or ID."
                ) from e

            last_yield_time = datetime.utcnow()
            yield_interval_minutes = 30

            while True:
                # Check job/account status externally
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    account = db.query(TelegramAccount).filter(
                        TelegramAccount.id == account_snap.id
                    ).first()

                    if not job or not account or job.status != "running" or account.status != "active":
                        logger.info(
                            f"Auto promo job {job_id} stopped. Status: {job.status if job else 'deleted'}"
                        )
                        break

                    # Check for yield break
                    current_time = datetime.utcnow()
                    if (current_time - last_yield_time).total_seconds() > (
                        yield_interval_minutes * 60
                    ):
                        logger.info(
                            f"Auto promo job {job_id} taking a brief 30s break"
                        )
                        # We just sleep, the short session above will close
                        # and be re-opened after sleep
                
                # Check for yield after session close
                if (datetime.utcnow() - last_yield_time).total_seconds() > (yield_interval_minutes * 60):
                    await asyncio.sleep(30)
                    last_yield_time = datetime.utcnow()
                    continue

                if stop_time and datetime.utcnow() >= stop_time:
                    logger.info(f"Auto promo job {job_id} reached its time limit.")
                    with get_short_session() as db:
                        job = db.query(Job).filter(Job.id == job_id).first()
                        if job:
                            job.status = "completed"
                    break

                # Rate limiting
                if rate_limit_per_hour:
                    cutoff = datetime.utcnow() - timedelta(hours=1)
                    message_timestamps = [t for t in message_timestamps if t > cutoff]
                    if len(message_timestamps) >= rate_limit_per_hour:
                        logger.info(f"Job {job_id} reached rate limit. Waiting...")
                        await asyncio.sleep(60)
                        continue

                try:
                    current_promo_message = process_template_variations(raw_promo_message)
                    if image_file_path:
                        await client.send_file(group, image_file_path, caption=current_promo_message)
                    else:
                        await client.send_message(group, current_promo_message)

                    message_timestamps.append(datetime.utcnow())
                    logger.info(f"Sent promo message to {target_group} for job {job_id}")

                    # Update message tracking
                    with get_short_session() as db:
                        job = db.query(Job).filter(Job.id == job_id).first()
                        if job:
                            job.messages_sent = (job.messages_sent or 0) + 1
                            if job.messages_planned > 0:
                                job.completion_percentage = (job.messages_sent / job.messages_planned) * 100.0
                            else:
                                job.completion_percentage = min((job.messages_sent / 10) * 100.0, 100.0)
                            job.progress = int(job.completion_percentage)

                            if job.completion_percentage >= 100.0:
                                logger.info(f"Job {job_id} completed (100% reached).")
                                job.status = "completed"
                                job.completed_at = datetime.utcnow()
                                break

                except ChatWriteForbiddenError as e:
                    raise RuntimeError(
                        f"Cannot send message to '{target_group}'. Account restricted or channel private."
                    ) from e
                except FloodWaitError as e:
                    logger.warning(
                        f"Flood wait error for job {job_id}: {e}. Waiting {e.seconds}s"
                    )
                    # sync_health_to_db is self-sufficient
                    sync_health_to_db(account_snap.id, extra_stats={
                        "messages_sent_today": 0 # We'll sync real count at the end
                    })
                    await asyncio.sleep(e.seconds)
                    continue

                sleep_time = interval_seconds
                if use_random_interval and min_interval and max_interval:
                    sleep_time = random.randint(min_interval, max_interval)

                logger.info(f"Job {job_id} sleeping for {sleep_time} seconds.")
                await asyncio.sleep(sleep_time)

    finally:
        # Fix 1: disconnect inside the async scope
        await session_manager.disconnect_client(account_snap.id)


@celery_app.task(
    base=HumanAwareTask,
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def auto_promo_task(self, job_id: int):
    """Celery task wrapper for auto promo operation."""
    account_id = None

    # ── Gap 9: Idempotency guard ──────────────────────────────────────────────
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"auto_promo_task: job {job_id} not found")
            return
        if job.status not in ("queued", "pending"):
            logger.warning(
                f"auto_promo_task: job {job_id} status '{job.status}', skipping"
            )
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
        logger.warning(
            f"auto_promo_task: account {account_id} is locked. Job {job_id} will retry."
        )
        raise self.retry(countdown=30, max_retries=20)

    try:
        # ── Fix E: Snapshot Account ───────────────────────────────────────────
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

        # ── Fix 1: Single asyncio.run() ───────────────────────────────────────
        asyncio.run(_auto_promo_runner(job_id, account_snap, config))

        # ── Final Status Update ───────────────────────────────────────────────
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status == "running":
                job.status = "completed"
                job.completed_at = datetime.utcnow()

    except Exception as e:
        logger.error(f"auto_promo_task: job {job_id} failed: {e}")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
        raise e

    finally:
        if account_id:
            # Sync final health state
            with get_short_session() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                sent = job.messages_sent if job else 0
            sync_health_to_db(account_id, extra_stats={"messages_sent_today": sent})
        lock.release()