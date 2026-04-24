"""
scrape_user_id/tasks.py

Fix 1: Single asyncio.run() — disconnect_client moved inside runner's finally block.
Fix 2: Per-process session key (in session_manager).
Fix 3: Short-lived DB sessions — no session held across await calls.
Fix E: snapshot_account() used before passing account to session_manager.
Gap 9: Idempotency guard + status='running' set at task start.
Fix A: Per-account Redis lock acquired before runner, released in finally.
"""

import asyncio
import csv
import json
import logging
import os
import sqlite3
from datetime import datetime

from celery_app import celery_app
from core.account_lock import acquire_account_lock, release_account_lock, get_lock_holder
from core.db_utils import get_short_session, snapshot_account
from core.human_aware_task import HumanAwareTask
from core.session_manager import session_manager
from models import Job, TelegramAccount
from sqlalchemy.orm import joinedload
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


async def _scrape_runner(job_id: int, account_id: int, account_snap, config: dict) -> int:
    """
    Async runner for scraping users from a Telegram group.

    All DB writes use short sessions — no session object is alive across awaits.
    disconnect_client is in the finally block of this runner (Fix 1).
    """
    group_username = config.get("group_username", "")
    if not group_username:
        raise ValueError("group_username not provided in job config")

    # Build output file path using phone number from snapshot
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"participants_{account_snap.phone_number}_{timestamp}.csv"
    filepath = f"/app/job_results/{filename}"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    logger.info(
        f"Scrape job {job_id}: scraping '{group_username}' "
        f"with account {account_snap.id}"
    )

    client = await session_manager.get_client(account_snap)

    try:
        async with client:
            group = await client.get_entity(group_username)
            participants = await client.get_participants(group, aggressive=True)

            total = len(participants)
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["User ID", "Username", "First Name", "Last Name", "Phone"]
                )
                for i, user in enumerate(participants):
                    writer.writerow(
                        [
                            user.id,
                            user.username or "",
                            user.first_name or "",
                            user.last_name or "",
                            user.phone or "",
                        ]
                    )
                    # Checkpoint progress every 100 users
                    if (i + 1) % 100 == 0:
                        with get_short_session() as db:
                            job = db.query(Job).filter(Job.id == job_id).first()
                            if job:
                                job.progress = min(95, int((i + 1) / total * 100))
                                job.messages_sent = i + 1
                                job.messages_planned = total
                                job.completion_percentage = float(job.progress)

            # Final count write
            with get_short_session() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.messages_sent = total
                    job.messages_planned = total

            logger.info(f"Scrape job {job_id}: scraped {total} participants → {filepath}")
            return total

    except FloodWaitError as e:
        logger.warning(f"FloodWaitError in scrape_users_task: waiting {e.seconds}s")
        await asyncio.sleep(e.seconds)
        raise # Re-raise to trigger Celery retry


    finally:
        # Fix 1: disconnect inside the async scope — same event loop
        await session_manager.disconnect_client(account_snap.id)


@celery_app.task(
    base=HumanAwareTask,
    bind=True,
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
)
def scrape_users_task(self, job_id: int):
    """Celery task for scraping users from a Telegram group."""
    account_id = None

    # ── Gap 9: Load job + idempotency guard ─────────────────────────────────
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"scrape_users_task: job {job_id} not found")
            return
        if job.status not in ("queued", "pending"):
            logger.warning(
                f"scrape_users_task: job {job_id} has status '{job.status}', "
                f"skipping to prevent duplicate execution"
            )
            return
        account_id = job.telegram_account_id
        config = json.loads(job.config) if job.config else {}
        job.status = "running"
        job.started_at = datetime.utcnow()
    # session closed

    # ── Fix A: acquire per-account lock ─────────────────────────────────────
    if not acquire_account_lock(account_id, job_id):
        holder = get_lock_holder(account_id)
        logger.warning(
            f"scrape_users_task: account {account_id} locked by {holder}. "
            f"Job {job_id} will retry."
        )
        raise self.retry(countdown=90, max_retries=2)

    try:
        # ── Load + snapshot account (Fix E) ──────────────────────────────────
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
        # session closed — account_snap is a plain dataclass

        # ── Run the async scraper ─────────────────────────────────────────────
        participant_count = asyncio.run(
            _scrape_runner(job_id, account_id, account_snap, config)
        )

        # ── Mark complete ─────────────────────────────────────────────────────
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "completed"
                job.progress = 100
                job.completion_percentage = 100.0
                job.completed_at = datetime.utcnow()

        logger.info(
            f"scrape_users_task: job {job_id} completed. "
            f"Scraped {participant_count} users."
        )

    except Exception as e:
        logger.error(f"scrape_users_task: job {job_id} failed: {e}")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                # Do not mark failed if it's a retryable error
                retryable = (ConnectionError, TimeoutError, OSError)
                if not isinstance(e, retryable):
                    job.status = "failed"
                    job.error_message = str(e)
        raise

    finally:
        # Fix A: always release lock
        if account_id:
            release_account_lock(account_id)
