"""Group Joiner Celery task — joins Telegram groups one by one with spacing."""

from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import asyncio
from datetime import datetime
from telethon.errors import FloodWaitError, ChannelsTooMuchError, InviteHashInvalidError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
import random

logger = logging.getLogger(__name__)


async def _group_join_runner(job: Job, db: Session):
    """Async runner: iterates through groups list and joins each one."""
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    groups: list[str] = config.get('groups', [])
    min_delay_seconds: int = max(10, config.get('min_delay_seconds', 30))
    max_delay_seconds: int = max(min_delay_seconds, config.get('max_delay_seconds', 60))

    if not groups:
        raise Exception("No groups found in job config")

    job.messages_planned = len(groups)
    job.messages_sent = 0
    db.commit()

    try:
        client = await session_manager.get_client(account)
    except RuntimeError as e:
        raise Exception(f"Account not authenticated: {str(e)}")

    joined = 0
    skipped = 0
    failed = []
    
    async def _execute_join(handle: str):
        if handle.startswith('+'):
            await client(ImportChatInviteRequest(handle[1:]))
        elif handle.lower().startswith('joinchat/'):
            await client(ImportChatInviteRequest(handle.split('/', 1)[1]))
        else:
            target = int(handle) if handle.lstrip('-').isdigit() else handle
            await client(JoinChannelRequest(target))

    async with client:
        for i, group_handle in enumerate(groups):
            # Check job status (allow external pause)
            db.refresh(job)
            if job.status != 'running':
                logger.info(f"Group join job {job.id} stopped externally at {i}/{len(groups)}")
                break

            try:
                await _execute_join(group_handle)
                joined += 1
                logger.info(f"Job {job.id}: Joined group {group_handle} ({i+1}/{len(groups)})")

            except UserAlreadyParticipantError:
                logger.info(f"Job {job.id}: Already in {group_handle}, skipping")
                skipped += 1

            except ChannelsTooMuchError:
                msg = "Account has joined too many channels/groups. Telegram limit reached."
                logger.error(f"Job {job.id}: {msg}")
                job.error_message = msg
                job.status = 'failed'
                db.commit()
                return

            except FloodWaitError as e:
                wait = getattr(e, 'seconds', 60)
                logger.warning(f"Job {job.id}: Flood wait {wait}s before joining {group_handle}")
                await asyncio.sleep(wait)
                # Retry once
                try:
                    await _execute_join(group_handle)
                    joined += 1
                except Exception as retry_e:
                    failed.append(f"{group_handle}: retry failed - {retry_e}")

            except (InviteHashInvalidError, Exception) as e:
                err_name = type(e).__name__
                logger.warning(f"Job {job.id}: Cannot join {group_handle}: {err_name}")
                failed.append(f"{group_handle}: {err_name}")

            # Update progress after each group
            job.messages_sent = joined + skipped
            job.completion_percentage = (job.messages_sent / len(groups)) * 100.0
            job.progress = int(job.completion_percentage)
            db.commit()

            # Delay between joins (skip delay after last group)
            if i < len(groups) - 1:
                delay = random.randint(min_delay_seconds, max_delay_seconds)
                logger.info(f"Job {job.id}: Waiting {delay}s before next join...")
                await asyncio.sleep(delay)

    # Final summary
    summary = f"Joined: {joined}, Already member: {skipped}, Failed: {len(failed)}"
    if failed:
        summary += f". Failures: {'; '.join(failed[:3])}"

    job.messages_sent = joined + skipped
    job.completion_percentage = (job.messages_sent / len(groups)) * 100.0
    job.progress = int(job.completion_percentage)
    job.error_message = summary if failed else None
    logger.info(f"Job {job.id} group join complete: {summary}")


@celery_app.task(bind=True, max_retries=1, name='group_joiner.tasks.group_join_task')
def group_join_task(self, job_id: int):
    """Celery task wrapper for group join operation."""
    db: Session = SessionLocal()
    account_id = None
    loop = None

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Group join job {job_id} not found")
            return

        account_id = job.telegram_account_id
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"Starting group join job {job_id} for account {account_id}")

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(_group_join_runner(job, db))

        if job.status == 'running':
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Group join job {job_id} completed")

    except Exception as e:
        logger.error(f"Group join job {job_id} failed: {type(e).__name__}: {e}", exc_info=True)
        if db and job:
            job.status = 'failed'
            job.error_message = f"{type(e).__name__}: {str(e)}"
            try:
                db.commit()
            except Exception:
                pass
    finally:
        try:
            if account_id and loop:
                loop.run_until_complete(session_manager.disconnect_client(account_id))
        except Exception as e:
            logger.error(f"Cleanup error for group join job {job_id}: {e}")
        finally:
            if loop and not loop.is_closed():
                try:
                    loop.close()
                except Exception:
                    pass
            if db:
                db.close()
