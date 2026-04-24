"""
mass_dm_bot/tasks.py

Refactored for stability:
- Fix 1: Single asyncio.run() caller.
- Fix 3: Short-lived DB sessions (get_short_session).
- Gap 9: Idempotency guard at task start.
- Redis Locking: lock:bot:{md5(bot_token)} (serial execution per bot)
"""

import asyncio
import json
import logging
import os
import random
import hashlib
from datetime import datetime, timedelta

import pandas as pd
from redis import Redis
from celery.exceptions import SoftTimeLimitExceeded
from celery_app import celery_app
from core.db_utils import get_short_session
from core.human_aware_task import HumanAwareTask
from models import Job
from telegram import Bot
from telegram.error import BadRequest, Forbidden, TelegramError
from utils.template_processor import process_template_variations

logger = logging.getLogger(__name__)


class MassDMBotError(Exception):
    """Custom exception for mass DM bot failures."""

    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors


async def _mass_dm_bot_runner(job_id: int, config: dict):
    """Async runner for bot-based mass DM jobs."""
    bot_token = config.get("bot_token")
    raw_message = config.get("message", "")
    stop_after_hours = config.get("stop_after_hours")
    csv_file_path = config.get("csv_file_path")
    delay_seconds = config.get("delay_seconds")
    min_delay_seconds = config.get("min_delay_seconds")
    max_delay_seconds = config.get("max_delay_seconds")

    if not bot_token:
        raise ValueError("Bot token is missing from the job configuration.")

    bot = Bot(token=bot_token)

    try:
        user_data = pd.read_csv(csv_file_path)
        if "chat_id" in user_data.columns:
            ids = user_data["chat_id"].tolist()
        else:
            raise ValueError("CSV must have a 'chat_id' column for bot-based DMs.")
    except FileNotFoundError:
        raise ValueError(f"CSV file not found at path: {csv_file_path}")

    # Initial setup
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.messages_planned = len(ids)

    stop_time = (
        datetime.utcnow() + timedelta(hours=stop_after_hours)
        if stop_after_hours
        else None
    )
    sent_count = 0
    error_messages = []

    for i, uid in enumerate(ids):
        # Check for pause/cancel
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job or job.status != "running":
                logger.info(
                    f"Mass DM Bot job {job_id} stopped. Status: {job.status if job else 'deleted'}"
                )
                break

        if stop_time and datetime.utcnow() >= stop_time:
            logger.info(
                f"Mass DM Bot job {job_id} reached its time limit of {stop_after_hours} hours."
            )
            with get_short_session() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "completed"
            break

        try:
            current_message = process_template_variations(raw_message)
            await bot.send_message(chat_id=uid, text=current_message)
            sent_count += 1

            # Update progress
            with get_short_session() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.messages_sent = sent_count
                    job.completion_percentage = (sent_count / len(ids)) * 100.0
                    job.progress = int(job.completion_percentage)

                    # Auto-complete job when all messages sent
                    if sent_count >= len(ids):
                        logger.info(
                            f"Job {job_id} completed (all {len(ids)} messages sent)."
                        )
                        job.status = "completed"
                        job.completed_at = datetime.utcnow()
                        break

            # Delay
            if i < len(ids) - 1:
                if (
                    isinstance(min_delay_seconds, int)
                    and isinstance(max_delay_seconds, int)
                    and max_delay_seconds >= min_delay_seconds
                    and min_delay_seconds >= 0
                ):
                    sleep_time = random.randint(min_delay_seconds, max_delay_seconds)
                elif isinstance(delay_seconds, int) and delay_seconds >= 0:
                    sleep_time = delay_seconds
                else:
                    sleep_time = random.randint(5, 300)
                logger.debug(f"Job {job_id} sent message to {uid}, sleeping {sleep_time}s")
                await asyncio.sleep(sleep_time)

        except (BadRequest, Forbidden) as e:
            logger.warning(f"Could not send message to {uid} for job {job_id}: {e.message}")
            error_messages.append(f"Could not send to {uid}: {e.message}")
        except TelegramError as e:
            logger.error(
                f"A Telegram error occurred for job {job_id} sending to {uid}: {e.message}"
            )
            error_messages.append(f"Telegram error for {uid}: {e.message}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred for job {job_id} sending to {uid}: {e}"
            )
            error_messages.append(f"Unexpected error for {uid}: {e.__class__.__name__}")

    if error_messages:
        raise MassDMBotError(
            f"Job completed with {len(error_messages)} errors.", error_messages
        )


@celery_app.task(
    base=HumanAwareTask,
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def mass_dm_bot_task(self, job_id: int):
    """Celery task wrapper for bot-based mass DM operation."""

    # ── Gap 9: Idempotency Guard ──────────────────────────────────────────────
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"mass_dm_bot_task: job {job_id} not found")
            return
        if job.status not in ("queued", "pending"):
            logger.warning(
                f"mass_dm_bot_task: job {job_id} has status '{job.status}', skipping"
            )
            return
        config = json.loads(job.config) if job.config else {}
        job.status = "running"
        job.started_at = datetime.utcnow()
    # session closed

    # ── Redis Lock ──────────────────────────────────────────────────────────
    redis_client = Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"), decode_responses=True)
    
    bot_token = config.get("bot_token", "default")
    bot_hash = hashlib.md5(bot_token.encode()).hexdigest()
    lock = redis_client.lock(f"lock:bot:{bot_hash}", timeout=3600, blocking_timeout=0)

    if not lock.acquire(blocking=False):
        logger.warning(f"mass_dm_bot_task: bot {bot_hash[:8]}... is locked. Job {job_id} will retry.")
        raise self.retry(countdown=30, max_retries=20)

    try:
        # ── Run async runner ──────────────────────────────────────────────────
        asyncio.run(_mass_dm_bot_runner(job_id, config))

    except SoftTimeLimitExceeded:
        logger.warning(f"Mass DM Bot job {job_id} hit soft time limit — pausing")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "paused"
                job.error_message = (
                    f"Paused: Celery soft time limit reached. Progress saved: "
                    f"{job.messages_sent or 0}/{job.messages_planned or 0} messages sent."
                )

    except MassDMBotError as e:
        logger.error(f"Mass DM Bot job {job_id} finished with errors: {e.errors}")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                error_summary = ", ".join(e.errors[:5])
                if len(e.errors) > 5:
                    error_summary += f" and {len(e.errors) - 5} more."
                job.error_message = f"{e.message} Examples: {error_summary}"

    except Exception as e:
        logger.error(f"mass_dm_bot_task: job {job_id} failed: {e}")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
        raise e
    finally:
        lock.release()