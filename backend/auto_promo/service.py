from telethon import TelegramClient
import asyncio
from database import get_db
from models import TelegramAccount
import logging

logger = logging.getLogger(__name__)
pending_clients = {}

async def start_auto_promo_auth(api_id: int, api_hash: str, phone_number: str):
    """
    Starts Telegram authentication by sending an OTP to the given phone.
    """
    session_name = f"temp_auto_promo_{phone_number}"
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    await client.send_code_request(phone_number)
    pending_clients[phone_number] = (client, api_id, api_hash)
    return True

async def verify_and_start_promo(
    api_id: int,
    api_hash: str,
    phone_number: str,
    code: str,
    target_group: str,
    promo_message: str,
    interval_seconds: int,
):
    """
    Verifies the OTP, logs in, and starts sending promo messages at intervals to the target group.
    """
    session_name = f"auto_promo_{phone_number}"

    if phone_number in pending_clients:
        client, _, _ = pending_clients.pop(phone_number)
    else:
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()

    await client.sign_in(phone=phone_number, code=code)

    async def promo_task():
        async with client:
            group = await client.get_entity(target_group)
            while True:
                # Re-fetch account status from DB
                db = next(get_db())
                account = db.query(TelegramAccount).filter(TelegramAccount.phone_number == phone_number).first()
                db.close()             
                if not account or account.status != 'active':
                    logger.info(f"Auto promo stopped: account {phone_number} status={account.status if account else 'not found'}")
                    break

                await client.send_message(group, promo_message)
                logger.info(f"Sent promo message to {target_group} for account {phone_number}")
                await asyncio.sleep(interval_seconds)

    asyncio.create_task(promo_task())

    return "Auto promo started successfully."
