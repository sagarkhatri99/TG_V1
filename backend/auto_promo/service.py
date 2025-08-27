from telethon import TelegramClient
import asyncio
from models import Job, TelegramAccount
from sqlalchemy.orm import Session
from core.session_manager import session_manager
import json
import logging

logger = logging.getLogger(__name__)

import random
import time
from datetime import datetime, timedelta

async def execute_auto_promo_job(job: Job, db: Session):
    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
        if not account:
            raise Exception("Account not found")

        config = json.loads(job.config)
        target_group = config.get('target_group')
        promo_message = config.get('promo_message')
        interval_seconds = config.get('interval_seconds', 3600)
        use_random_interval = config.get('use_random_interval', False)
        min_interval = config.get('min_interval')
        max_interval = config.get('max_interval')
        stop_after_hours = config.get('stop_after_hours')

        client = await session_manager.get_client(account)

        stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None

        async with client:
            group = await client.get_entity(target_group)
            while True:
                # Check for stop conditions
                db.refresh(job)
                db.refresh(account)
                if job.status != 'running' or account.status != 'active':
                    logger.info(f"Auto promo job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
                    if job.status == 'running':
                        job.status = 'paused'
                    break

                if stop_time and datetime.utcnow() >= stop_time:
                    logger.info(f"Auto promo job {job.id} reached its time limit of {stop_after_hours} hours.")
                    job.status = 'completed'
                    break

                await client.send_message(group, promo_message)
                logger.info(f"Sent promo message to {target_group} for job {job.id}")

                job.progress = (job.progress or 0) + 1
                db.commit()

                sleep_time = interval_seconds
                if use_random_interval and min_interval and max_interval:
                    sleep_time = random.randint(min_interval, max_interval)

                logger.info(f"Job {job.id} sleeping for {sleep_time} seconds.")
                await asyncio.sleep(sleep_time)

        if job.status == 'running':
            job.status = 'completed'
        job.completed_at = datetime.utcnow()
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
