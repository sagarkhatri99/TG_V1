from telethon import TelegramClient
import pandas as pd
import time
import random
import asyncio
import json
from models import Job, TelegramAccount
from sqlalchemy.orm import Session
from core.session_manager import session_manager
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def execute_mass_dm_account_job(job: Job, db: Session):
    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
        if not account:
            raise Exception("Account not found")

        config = json.loads(job.config)
        message = config.get('message')
        stop_after_hours = config.get('stop_after_hours')
        csv_file_path = config.get('csv_file_path')

        user_data = pd.read_csv(csv_file_path)
        if 'user_id' in user_data.columns:
            ids = user_data['user_id'].tolist()
        elif 'username' in user_data.columns:
            ids = user_data['username'].tolist()
        else:
            raise Exception("CSV must have a 'user_id' or 'username' column.")

        client = await session_manager.get_client(account)

        stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None

        sent_count = 0
        async with client:
            for uid in ids:
                # Check for stop conditions
                db.refresh(job)
                db.refresh(account)
                if job.status != 'running' or account.status != 'active':
                    logger.info(f"Mass DM job {job.id} stopped. Job status: {job.status}, Account status: {account.status}")
                    if job.status == 'running':
                        job.status = 'paused'
                    break

                if stop_time and datetime.utcnow() >= stop_time:
                    logger.info(f"Mass DM job {job.id} reached its time limit of {stop_after_hours} hours.")
                    job.status = 'completed'
                    break

                try:
                    await client.send_message(uid, message)
                    sent_count += 1
                    job.progress = (sent_count / len(ids)) * 100
                    db.commit()

                    sleep_time = random.randint(5, 300)
                    logger.info(f"Job {job.id} sent message to {uid}, sleeping for {sleep_time} seconds.")
                    await asyncio.sleep(sleep_time)

                except Exception as e:
                    logger.error(f"Failed to send message to {uid} for job {job.id}: {e}")
                    pass # Continue to next user

        if job.status == 'running':
            job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error executing Mass DM Account job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()

# Old service functions deprecated
# ...
