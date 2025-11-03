import os
import asyncio
from datetime import datetime

from telethon import TelegramClient
from telethon.sessions import StringSession

from database import SessionLocal
from models import TelegramAccount
from core.config import settings

SESSIONS_DIR = os.getenv("SESSIONS_DIR", "/app/sessions")

async def migrate_account(account: TelegramAccount) -> bool:
    """Attempt to migrate a file-based session for the given account into DB StringSession.
    Returns True on success, False otherwise.
    """
    session_path = os.path.join(SESSIONS_DIR, f"account_{account.id}.session")
    if not os.path.exists(session_path):
        return False

    # Resolve API credentials
    try:
        api_id = int(account.api_id) if getattr(account, "api_id", None) else settings.TELEGRAM_API_ID
    except Exception:
        api_id = settings.TELEGRAM_API_ID
    api_hash = account.api_hash if getattr(account, "api_hash", None) else settings.TELEGRAM_API_HASH
    if not api_id or not api_hash:
        print(f"[account {account.id}] Missing API credentials; cannot migrate.")
        return False

    client = TelegramClient(session_path, api_id, api_hash)
    try:
        await client.connect()
        # Try to extract a session string
        session_str = None
        try:
            session_str = str(client.session)  # works if underlying session is StringSession already
        except Exception:
            session_str = None
        if not session_str and hasattr(client.session, "save"):
            try:
                session_str = client.session.save()
            except Exception:
                session_str = None
        if not session_str:
            print(f"[account {account.id}] Could not export session to string; re-auth may be required.")
            return False
        # Persist to DB
        db = SessionLocal()
        try:
            acc = db.query(TelegramAccount).filter(TelegramAccount.id == account.id).first()
            if acc:
                acc.session_string = session_str
                acc.last_activity = datetime.utcnow()
                db.commit()
                print(f"[account {account.id}] Migrated session to DB.")
                return True
        finally:
            db.close()
        return False
    finally:
        await client.disconnect()

async def main():
    db = SessionLocal()
    try:
        accounts = db.query(TelegramAccount).all()
    finally:
        db.close()

    migrated = 0
    for account in accounts:
        try:
            ok = await migrate_account(account)
            if ok:
                migrated += 1
        except Exception as e:
            print(f"[account {account.id}] Migration error: {e}")
    print(f"Done. Migrated {migrated} account sessions.")

if __name__ == "__main__":
    asyncio.run(main())