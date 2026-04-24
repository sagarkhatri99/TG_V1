"""
group_monitor/tasks.py

Fix 1: Single asyncio.run() — disconnect_client inside runner's finally block.
Fix 2: Per-process session key (in session_manager).
Fix 3: Short-lived DB sessions — no session held across iter_messages awaits.
Fix E: snapshot_account() used before passing account to session_manager.
Gap 9: Idempotency guard + status='running' set at task start.
Fix A: Per-account Redis lock.
"""

import asyncio
import csv
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

from celery_app import celery_app
from core.account_lock import acquire_account_lock, release_account_lock, get_lock_holder
from core.db_utils import get_short_session, snapshot_account
from core.human_aware_task import HumanAwareTask
from core.session_manager import session_manager
from models import Job, TelegramAccount
from sqlalchemy.orm import joinedload
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


async def _group_monitor_runner(job_id: int, account_snap, config: dict) -> None:
    """
    Async runner for monitoring messages in Telegram groups.

    All DB writes use short sessions opened per-operation and immediately
    closed. No session is held open across iter_messages awaits (Fix 3).
    disconnect_client is called in this runner's finally block (Fix 1).
    """
    group_usernames = config.get("group_usernames", [])
    keywords = config.get("keywords", [])
    monitored_users = config.get("monitored_users", [])
    limit = config.get("limit", 100)
    days = config.get("days")  # optional int

    offset_date = None
    if isinstance(days, int) and days > 0:
        offset_date = datetime.utcnow() - timedelta(days=days)

    filename = f"/app/job_results/monitored_messages_job_{job_id}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    client = await session_manager.get_client(account_snap)

    error_messages = []
    processed_messages = 0

    try:
        async with client:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["group", "user", "text", "timestamp"]
                )
                writer.writeheader()

                for group_username in group_usernames:
                    try:
                        group = await client.get_entity(group_username)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Group monitor job {job_id}: could not find "
                            f"'{group_username}'. Skipping."
                        )
                        error_messages.append(f"Group '{group_username}' not found.")
                        continue

                    actual_limit = None if (days and days > 0) else limit
                    messages_checked = 0
                    matched_count = 0

                    logger.info(
                        f"Group monitor job {job_id}: monitoring '{group_username}', "
                        f"days={days}"
                    )

                    async for message in client.iter_messages(
                        group, limit=actual_limit
                    ):
                        messages_checked += 1

                        if offset_date is not None and message.date:
                            if message.date.replace(tzinfo=None) < offset_date:
                                logger.info(
                                    f"Group monitor job {job_id}: reached messages "
                                    f"older than {days} days at msg {messages_checked}"
                                )
                                break

                        processed_messages += 1
                        msg_text = message.text or ""
                        sender_username = (
                            getattr(message.sender, "username", None)
                            if message.sender
                            else None
                        )

                        matches = False
                        if keywords and any(
                            kw.lower() in msg_text.lower() for kw in keywords
                        ):
                            matches = True
                        if (
                            monitored_users
                            and sender_username
                            and sender_username in monitored_users
                        ):
                            matches = True

                        if matches:
                            matched_count += 1
                            writer.writerow(
                                {
                                    "group": group_username,
                                    "user": sender_username or "Unknown",
                                    "text": msg_text,
                                    "timestamp": (
                                        message.date.isoformat()
                                        if message.date
                                        else ""
                                    ),
                                }
                            )
                            f.flush()

                        # Progress checkpoint every 50 messages (Fix 3: short session)
                        if messages_checked % 50 == 0:
                            if days:
                                pct = min(
                                    90, (messages_checked / 1000) * 100
                                )
                            else:
                                total_expected = max(
                                    1, limit * max(1, len(group_usernames))
                                )
                                pct = min(
                                    99, (processed_messages / total_expected) * 100
                                )
                            with get_short_session() as db:
                                job = db.query(Job).filter(
                                    Job.id == job_id
                                ).first()
                                if job:
                                    job.progress = pct

                    logger.info(
                        f"Group monitor job {job_id}: finished '{group_username}' — "
                        f"checked {messages_checked}, matched {matched_count}"
                    )

        # Write any accumulated error messages
        if error_messages:
            with get_short_session() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.error_message = (
                        f"Completed with some errors: {', '.join(error_messages)}"
                    )

    except FloodWaitError as e:
        logger.warning(f"FloodWaitError in group_monitor_task: waiting {e.seconds}s")
        await asyncio.sleep(e.seconds)
        raise # Re-raise to trigger Celery retry


    finally:
        # Fix 1: disconnect inside the async scope
        await session_manager.disconnect_client(account_snap.id)


@celery_app.task(
    base=HumanAwareTask,
    bind=True,
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
)
def group_monitor_task(self, job_id: int):
    """Celery task for monitoring Telegram group messages."""
    account_id = None

    # ── Gap 9: idempotency guard ──────────────────────────────────────────────
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"group_monitor_task: job {job_id} not found")
            return
        if job.status not in ("queued", "pending"):
            logger.warning(
                f"group_monitor_task: job {job_id} has status '{job.status}', "
                f"skipping"
            )
            return
        account_id = job.telegram_account_id
        config = json.loads(job.config) if job.config else {}
        job.status = "running"
        job.started_at = datetime.utcnow()
    # session closed

    # ── Fix A: per-account lock ───────────────────────────────────────────────
    if not acquire_account_lock(account_id, job_id):
        holder = get_lock_holder(account_id)
        logger.warning(
            f"group_monitor_task: account {account_id} locked by {holder}. "
            f"Job {job_id} will retry."
        )
        raise self.retry(countdown=90, max_retries=2)

    try:
        # ── Fix E: snapshot account ───────────────────────────────────────────
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

        # ── Run the async monitor ─────────────────────────────────────────────
        asyncio.run(_group_monitor_runner(job_id, account_snap, config))

        # ── Mark complete ─────────────────────────────────────────────────────
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "completed"
                job.progress = 100
                job.completed_at = datetime.utcnow()

        logger.info(f"group_monitor_task: job {job_id} completed")

    except Exception as e:
        logger.error(f"group_monitor_task: job {job_id} failed: {e}")
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                # Do not mark failed if it's a retryable error
                retryable = (ConnectionError, TimeoutError, OSError)
                if not isinstance(e, retryable):
                    job.status = "failed"
                    job.error_message = str(e)
        raise e

    finally:
        if account_id:
            release_account_lock(account_id)
