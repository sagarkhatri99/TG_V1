from telethon import TelegramClient
import pandas as pd
from typing import IO
import time
import random
import asyncio

# In-memory store for pending OTP logins per phone number
pending_clients = {}

async def start_dm_auth(api_id: int, api_hash: str, phone_number: str):
    session_name = f"temp_dm_{phone_number}"
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    await client.send_code_request(phone_number)
    pending_clients[phone_number] = (client, api_id, api_hash)
    return True

async def send_mass_dm_account_with_otp(
    api_id: int,
    api_hash: str,
    phone_number: str,
    otp: str,
    csv_file: IO,
    message: str,
    session_name: str = None
) -> str:
    try:
        user_data = pd.read_csv(csv_file)
        if 'user_id' in user_data.columns:
            ids = user_data['user_id'].tolist()
        elif 'username' in user_data.columns:
            ids = user_data['username'].tolist()
        else:
            return "CSV must have a 'user_id' or 'username' column."
        sent = 0
        if not session_name:
            session_name = f"dm_{phone_number}"
        # Step 1: Complete login with OTP if pending
        if phone_number in pending_clients:
            client, api_id, api_hash = pending_clients.pop(phone_number)
        else:
            client = TelegramClient(session_name, api_id, api_hash)
            await client.connect()
        await client.sign_in(phone=phone_number, code=otp)
        # Step 2: Send DMs
        async with client:
            for uid in ids:
                try:
                    await client.send_message(uid, message)
                    sent += 1
                    await asyncio.sleep(random.randint(5, 300))
                except Exception:
                    pass
        return f"Sent message to {sent} users."
    except Exception as e:
        return f"Error: {e}"
