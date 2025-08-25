import csv
import os
import logging
from telethon import TelegramClient

logger = logging.getLogger(__name__)
pending_clients = {}

async def start_scrape_auth(api_id: int, api_hash: str, phone_number: str):
    session_name = f"temp_scrape_{phone_number}"
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    await client.send_code_request(phone_number)
    pending_clients[phone_number] = (client, api_id, api_hash)
    return True

async def verify_and_scrape(
    api_id: int,
    api_hash: str,
    phone_number: str,
    code: str,
    group_username: str
) -> int:
    # Clean the phone number for filenames (remove the '+')
    clean_phone = phone_number.replace('+', '')
    filename = f"participants_{clean_phone}.csv"
    cwd = os.getcwd()

    logger.info(f"Scraping participants for {phone_number} into file: {filename}")
    logger.info(f"Current working directory: {cwd}")

    # Retrieve or create client
    if phone_number in pending_clients:
        client, _, _ = pending_clients.pop(phone_number)
    else:
        session_name = f"scrape_{phone_number}"
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()

    await client.sign_in(phone=phone_number, code=code)

    async with client:
        group = await client.get_entity(group_username)
        participants = await client.get_participants(group, aggressive=True)

        with open(filename, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['User ID', 'Username', 'First Name', 'Last Name'])
            for user in participants:
                writer.writerow([
                    user.id,
                    user.username or '',
                    user.first_name or '',
                    user.last_name or ''
                ])

    logger.info(f"Wrote {len(participants)} rows to {filename}")
    return len(participants)
