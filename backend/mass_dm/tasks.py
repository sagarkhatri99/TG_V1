from celery_app import celery_app
from sqlalchemy.orm import Session
from models import Job, TelegramAccount
from database import SessionLocal
from core.session_manager import session_manager
import json
import logging
import pandas as pd
import asyncio
import random
import time
from pyrogram import Client
from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid

logger = logging.getLogger(__name__)

async def _mass_dm_account(job: Job, db: Session):
    account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
    if not account:
        raise Exception("Account not found")

    config = json.loads(job.config)
    message = config.get('message')
    csv_path = config.get('csv_path')

    df = pd.read_csv(csv_path)

    client = await session_manager.get_client(account)

    for index, row in df.iterrows():
        target = row['user_id'] if 'user_id' in row else row['username']
        try:
            await client.send_message(target, message)
            time.sleep(random.randint(1, 5))
        except (UserIsBlocked, PeerIdInvalid):
            logger.warning(f"Could not send message to {target}. User has blocked the account or the user ID is invalid.")
        except FloodWait as e:
            logger.warning(f"Flood wait of {e.value} seconds.")
            await asyncio.sleep(e.value)

@celery_app.task(bind=True, max_retries=3, queue='telegram_jobs')
def mass_dm_account_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return

    account_id = job.telegram_account_id

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        asyncio.run(_mass_dm_account(job, db))

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error executing mass DM (account) job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        if account_id:
            asyncio.run(session_manager.disconnect_client(account_id))
        db.close()

async def _mass_dm_bot(job: Job, db: Session):
    config = json.loads(job.config)
    message = config.get('message')
    csv_path = config.get('csv_path')
    bot_token = config.get('bot_token')

    df = pd.read_csv(csv_path)

    async with Client(":memory:", bot_token=bot_token) as bot:
        for index, row in df.iterrows():
            chat_id = row['chat_id']
            try:
                await bot.send_message(chat_id, message)
                time.sleep(random.randint(1, 5))
            except FloodWait as e:
                logger.warning(f"Flood wait of {e.value} seconds.")
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Could not send message to {chat_id}: {e}")

@celery_app.task(bind=True, max_retries=3, queue='telegram_jobs')
def mass_dm_bot_task(self, job_id: int):
    db: Session = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found.")
        return

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        asyncio.run(_mass_dm_bot(job, db))

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error executing mass DM (bot) job {job_id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()