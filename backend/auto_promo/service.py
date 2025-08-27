from telethon import TelegramClient
import asyncio
from models import Job, TelegramAccount
from sqlalchemy.orm import Session
from core.session_manager import session_manager
import json
import logging

logger = logging.getLogger(__name__)

async def execute_auto_promo_job(job: Job, db: Session):
    try:
        job.status = 'running'
        db.commit()

        account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
        if not account:
            raise Exception("Account not found")

        config = json.loads(job.config)
        target_group = config.get('target_group')
        promo_message = config.get('promo_message')
        interval_seconds = config.get('interval_seconds', 3600)

        client = await session_manager.get_client(account)

        async with client:
            group = await client.get_entity(target_group)
            while True:
                # Refresh job and account from DB to check for status changes
                db.refresh(job)
                db.refresh(account)
                if job.status != 'running' or account.status != 'active':
                    logger.info(f"Auto promo job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
                    if job.status == 'running':
                        job.status = 'paused' # If stopped for other reasons, pause it
                    break

                await client.send_message(group, promo_message)
                logger.info(f"Sent promo message to {target_group} for job {job.id}")

                # Update progress (e.g., based on number of messages sent)
                job.progress = (job.progress or 0) + 1
                db.commit()

                await asyncio.sleep(interval_seconds)

        if job.status == 'running':
            job.status = 'completed' # Should not be reached for infinite jobs, but as a safeguard
        db.commit()

    except Exception as e:
        logger.error(f"Error executing auto promo job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()

# Old service functions are deprecated.
# pending_clients = {}

# async def start_auto_promo_auth(api_id: int, api_hash: str, phone_number: str):
#     ...

# async def verify_and_start_promo(
#     api_id: int,
#     api_hash: str,
#     phone_number: str,
#     code: str,
#     target_group: str,
#     promo_message: str,
#     interval_seconds: int,
# ):
#     ...
