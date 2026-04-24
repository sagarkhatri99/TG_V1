"""
group_joiner/tasks.py

Refactored for stability and serial execution:
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
import random
import sqlite3
from datetime import datetime
from redis import Redis

from celery_app import celery_app
from core.db_utils import get_short_session, snapshot_account
from core.human_aware_task import HumanAwareTask
from core.session_manager import session_manager
from models import Job, TelegramAccount
from sqlalchemy.orm import joinedload
from telethon.errors import (
    ChannelsTooMuchError,
    FloodWaitError,
    InviteHashInvalidError,
    UserAlreadyParticipantError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

logger = logging.getLogger(__name__)


async def _group_join_runner(job_id: int, account_snap, config: dict):
    """Async runner: iterates through groups list and joins each one."""
    groups: list[str] = config.get("groups", [])
    min_delay_seconds: int = max(10, config.get("min_delay_seconds", 30))
    max_delay_seconds: int = max(min_delay_seconds, config.get("max_delay_seconds", 60))

    if not groups:
        raise ValueError("No groups found in job config")

    # Initial setup
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.messages_planned = len(groups)
            job.messages_sent = 0

    client = await session_manager.get_client(account_snap)

    joined = 0
    skipped = 0
    failed = []

    async def _execute_join(handle: str):
        if handle.startswith("+"):
            await client(ImportChatInviteRequest(handle[1:]))
        elif handle.lower().startswith("joinchat/"):
            await client(ImportChatInviteRequest(handle.split("/", 1)[1]))
        else:
            target = int(handle) if handle.lstrip("-").isdigit() else handle
            await client(JoinChannelRequest(target))

    try:
        async with client:
            for i, group_handle in enumerate(groups):
                # Check job status for external pause/cancel
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if not job or job.status != "running":
                        logger.info(
                            f"Group join job {job_id} stopped externally at {i}/{len(groups)}"
                        )
                        break

                try:
                    await _execute_join(group_handle)
                    joined += 1
                    logger.info(
                        f"Job {job_id}: Joined group {group_handle} ({i+1}/{len(groups)})"
                    )

                except UserAlreadyParticipantError:
                    logger.info(f"Job {job_id}: Already in {group_handle}, skipping")
                    skipped += 1

                except ChannelsTooMuchError:
                    msg = "Account has joined too many channels/groups. Telegram limit reached."
                    logger.error(f"Job {job_id}: {msg}")
                    with get_short_session() as db:
                        job = db.query(Job).filter(Job.id == job_id).first()
                        if job:
                            job.error_message = msg
                            job.status = "failed"
                    return

                except FloodWaitError as e:
                    wait = getattr(e, "seconds", 60)
                    logger.warning(
                        f"Job {job_id}: Flood wait {wait}s before joining {group_handle}"
                    )
                    await asyncio.sleep(wait)
                    # Retry once
                    try:
                        await _execute_join(group_handle)
                        joined += 1
                    except Exception as retry_e:
                        failed.append(f"{group_handle}: retry failed - {retry_e}")

                except (InviteHashInvalidError, Exception) as e:
                    err_name = type(e).__name__
                    logger.warning(f"Job {job_id}: Cannot join {group_handle}: {err_name}")
                    failed.append(f"{group_handle}: {err_name}")

                # Update progress after each group
                with get_short_session() as db:
                    job = db.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.messages_sent = joined + skipped
                        job.completion_percentage = (job.messages_sent / len(groups)) * 100.0
                        job.progress = int(job.completion_percentage)

                # Delay between joins (skip delay after last group)
                if i < len(groups) - 1:
                    delay = random.randint(min_delay_seconds, max_delay_seconds)
                    logger.info(f"Job {job_id}: Waiting {delay}s before next join...")
                    await asyncio.sleep(delay)

        # Final summary
        summary = f"Joined: {joined}, Already member: {skipped}, Failed: {len(failed)}"
        if failed:
            summary += f". Failures: {'; '.join(failed[:3])}"

        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.messages_sent = joined + skipped
                job.completion_percentage = (job.messages_sent / len(groups)) * 100.0
                job.progress = int(job.completion_percentage)
                if failed:
                    job.error_message = summary
                logger.info(f"Job {job_id} group join complete: {summary}")

    finally:
        # Fix 1: disconnect inside the same async scope
        await session_manager.disconnect_client(account_snap.id)


@celery_app.task(
    base=HumanAwareTask,
    bind=True,
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
)
def group_join_task(self, job_id: int):
    """Celery task wrapper for group join operation."""
    account_id = None

    # ── Gap 9: Idempotency Guard ──────────────────────────────────────────────
    with get_short_session() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"group_join_task: job {job_id} not found")
            return
        if job.status not in ("queued", "pending"):
            logger.warning(
                f"group_join_task: job {job_id} has status '{job.status}', skipping"
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
            f"group_join_task: account {account_id} is locked. Job {job_id} will retry."
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
        # session closed

        logger.info(f"Starting group join job {job_id} for account {account_id}")

        # ── Fix 1: Single asyncio.run() ───────────────────────────────────────
        asyncio.run(_group_join_runner(job_id, account_snap, config))

        # ── Final Status Update ───────────────────────────────────────────────
        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status == "running":
                job.status = "completed"
                job.completed_at = datetime.utcnow()
        logger.info(f"Group join job {job_id} completed")

    except Exception as e:
        logger.error(f"group_join_task: job {job_id} failed: {e}")
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
        lock.release()
