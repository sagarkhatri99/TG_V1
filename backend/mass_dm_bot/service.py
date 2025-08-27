from telegram import Bot
import pandas as pd
import time
import random
import asyncio
import json
from models import Job
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def execute_mass_dm_bot_job(job: Job, db: Session):
    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        config = json.loads(job.config)
        bot_token = config.get('bot_token')
        message = config.get('message')
        stop_after_hours = config.get('stop_after_hours')
        csv_file_path = config.get('csv_file_path')

        bot = Bot(token=bot_token)

        user_data = pd.read_csv(csv_file_path)
        if 'chat_id' in user_data.columns:
            ids = user_data['chat_id'].tolist()
        elif 'user_id' in user_data.columns:
            ids = user_data['user_id'].tolist()
        elif 'username' in user_data.columns:
            ids = user_data['username'].tolist()
        else:
            raise Exception("CSV must have a 'chat_id', 'user_id', or 'username' column.")

        stop_time = datetime.utcnow() + timedelta(hours=stop_after_hours) if stop_after_hours else None

        sent_count = 0
        for uid in ids:
            # Check for stop conditions
            db.refresh(job)
            if job.status != 'running':
                logger.info(f"Mass DM Bot job {job.id} stopped. Job status: {job.status}")
                if job.status == 'running':
                    job.status = 'paused'
                break

            if stop_time and datetime.utcnow() >= stop_time:
                logger.info(f"Mass DM Bot job {job.id} reached its time limit of {stop_after_hours} hours.")
                job.status = 'completed'
                break

            try:
                await bot.send_message(chat_id=uid, text=message)
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
        logger.error(f"Error executing Mass DM Bot job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()

# Old service functions deprecated
# ...