from telegram import Bot
import pandas as pd
from typing import IO
import time
async def send_mass_dm_bot(bot_token: str, csv_file: IO, message: str) -> str:
    bot = Bot(token=bot_token)
    try:
        user_data = pd.read_csv(csv_file)
        if 'chat_id' in user_data.columns:
            ids = user_data['chat_id'].tolist()
        elif 'user_id' in user_data.columns:
            ids = user_data['user_id'].tolist()
        elif 'username' in user_data.columns:
            ids = user_data['username'].tolist()
        else:
            return "CSV must have a 'chat_id', 'user_id', or 'username' column."
        sent = 0
        for uid in ids:
            try:
                await bot.send_message(chat_id=uid, text=message)
                sent += 1
                time.sleep(5)  # To avoid hitting rate limits
            except Exception as e:
                pass
        return f"Sent message to {sent} users."
    except Exception as e:
        return f"Error: {e}"