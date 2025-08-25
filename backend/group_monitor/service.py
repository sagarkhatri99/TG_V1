from telethon import TelegramClient
import csv
import datetime

pending_clients = {}

async def start_monitor_auth(api_id: int, api_hash: str, phone_number: str):
    session_name = f"temp_monitor_{phone_number}"
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    await client.send_code_request(phone_number)
    pending_clients[phone_number] = (client, api_id, api_hash)
    return True

async def verify_monitor_otp_and_monitor(
    api_id: int,
    api_hash: str,
    phone_number: str,
    code: str,
    group_usernames: list,
    keywords: list,
    monitored_users: list,
    limit: int = 100
):
    session_name = f"monitor_{phone_number}"

    if phone_number in pending_clients:
        client, _, _ = pending_clients.pop(phone_number)
    else:
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()

    await client.sign_in(phone=phone_number, code=code)

    found_messages = []
    async with client:
        for group_username in group_usernames:
            try:
                group = await client.get_entity(group_username)
            except Exception as e:
                print(f"Error fetching group {group_username}: {e}")
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

    filename = f"monitored_messages_{phone_number}.csv"
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["group", "user", "text", "timestamp"])
        writer.writeheader()
        for msg in found_messages:
            writer.writerow(msg)

    return f"Found {len(found_messages)} matching messages."
