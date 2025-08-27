from telethon import TelegramClient
import csv
import json
from models import Job, TelegramAccount
from sqlalchemy.orm import Session
from core.session_manager import session_manager
import logging

logger = logging.getLogger(__name__)

async def execute_group_monitor_job(job: Job, db: Session):
    try:
        job.status = 'running'
        db.commit()

        account = db.query(TelegramAccount).filter(TelegramAccount.id == job.telegram_account_id).first()
        if not account:
            raise Exception("Account not found")

        config = json.loads(job.config)
        group_usernames = config.get('group_usernames', [])
        keywords = config.get('keywords', [])
        monitored_users = config.get('monitored_users', [])
        limit = config.get('limit', 100)

        client = await session_manager.get_client(account)

        found_messages = []
        async with client:
            for group_username in group_usernames:
                try:
                    group = await client.get_entity(group_username)
                except Exception as e:
                    logger.error(f"Error fetching group {group_username} for job {job.id}: {e}")
                    continue

                async for message in client.iter_messages(group, limit=limit):
                    msg_text = message.text or ""
                    sender_username = getattr(message.sender, 'username', None) if message.sender else None

                    if (
                        any(keyword.lower() in msg_text.lower() for keyword in keywords)
                        or (sender_username in monitored_users if sender_username else False)
                    ):
                        found_messages.append({
                            "group": group_username,
                            "user": sender_username,
                            "text": msg_text,
                            "timestamp": message.date.isoformat() if message.date else ""
                        })

        filename = f"monitored_messages_job_{job.id}.csv"
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["group", "user", "text", "timestamp"])
            writer.writeheader()
            for msg in found_messages:
                writer.writerow(msg)

        job.status = 'completed'
        job.progress = 100
        db.commit()
        logger.info(f"Group monitor job {job.id} completed successfully.")

    except Exception as e:
        logger.error(f"Error executing group monitor job {job.id}: {e}")
        job.status = 'failed'
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()


# Old service functions are deprecated.
# from telethon import TelegramClient
# import csv
# import datetime

# pending_clients = {}

# async def start_monitor_auth(api_id: int, api_hash: str, phone_number: str):
#     session_name = f"temp_monitor_{phone_number}"
#     client = TelegramClient(session_name, api_id, api_hash)
#     await client.connect()
#     await client.send_code_request(phone_number)
#     pending_clients[phone_number] = (client, api_id, api_hash)
#     return True

# async def verify_monitor_otp_and_monitor(
#     api_id: int,
#     api_hash: str,
#     phone_number: str,
#     code: str,
#     group_usernames: list,
#     keywords: list,
#     monitored_users: list,
#     limit: int = 100
# ):
#     ...
