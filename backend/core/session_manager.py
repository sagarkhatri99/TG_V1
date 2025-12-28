from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import random
from typing import Dict
import logging
import os
from datetime import datetime

from database import SessionLocal
from models import TelegramAccount, Proxy
from core.config import settings
from core.proxy_utils import build_proxy_config

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, session_folder: str = "/app/sessions"):
        # Retain folder reference for optional migration compatibility, but
        # StringSession eliminates the need for file-based sessions.
        self.session_folder = session_folder
        os.makedirs(self.session_folder, exist_ok=True)
        # Cache active clients per account id
        self.active_clients: Dict[int, TelegramClient] = {}

    async def get_client(self, account: TelegramAccount) -> TelegramClient:
        """Return a connected TelegramClient using a DB-backed StringSession.
        If client is not cached, create it. Ensure it's connected before returning.
        
        CRITICAL: Will raise RuntimeError if session is not authenticated.
        """
        if account.id not in self.active_clients:
            self.active_clients[account.id] = await self._create_client(account)
        client = self.active_clients[account.id]
        
        # Check if client is already authenticated (has valid session)
        if not client.is_connected():
            try:
                await client.connect()
            except (EOFError, OSError) as e:
                # EOFError means Telethon is trying to read from stdin (unauthenticated session)
                raise RuntimeError(
                    f"Cannot connect to Telegram for account {account.id}. "
                    f"The account session is not authenticated. "
                    f"Please log in first via the frontend. Error: {e}"
                )
        
        # Verify client is authenticated
        try:
            if not await client.is_user_authorized():
                raise RuntimeError(
                    f"Account {account.id} is not authorized. "
                    f"Please log in first via the frontend."
                )
        except Exception as auth_check_err:
            logger.warning(f"Could not verify auth status for account {account.id}: {auth_check_err}")
        
        return client

    async def _create_client(self, account: TelegramAccount) -> TelegramClient:
        """Create a new TelegramClient bound to a StringSession from DB."""
        # Build proxy dictionary if present, with strict error handling.
        # Build proxy dictionary if present, with strict error handling.
        # 1. Try to get proxy object
        proxy_obj = None
        if getattr(account, "proxy", None):
            proxy_obj = account.proxy
        elif getattr(account, "proxy_id", None):
            try:
                with SessionLocal() as db:
                     proxy_obj = db.query(Proxy).filter(Proxy.id == account.proxy_id).first()
            except Exception as e:
                logger.error(f"Failed to fetch proxy for account {account.id} from DB: {e}")

        if proxy_obj:
            try:
                # Use unified builder
                proxy_config = build_proxy_config(proxy_obj)
                proxy_details = proxy_config.get("telethon")
                
                # Log consistent proxy info with masked credentials
                logger.info(f"Using proxy for account {account.id}: {proxy_config.get('details')}")
                
            except Exception as e:
                error_msg = f"Account {account.id} has an invalid proxy assigned. Connection aborted. Error: {e}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        # Prefer per-account API keys; fallback to env
        try:
            api_id = int(account.api_id) if getattr(account, "api_id", None) and str(account.api_id).strip() else settings.TELEGRAM_API_ID
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Invalid api_id for account {account.id}: {account.api_id}, error: {e}")
            api_id = settings.TELEGRAM_API_ID
        
        api_hash = account.api_hash if getattr(account, "api_hash", None) and str(account.api_hash).strip() else settings.TELEGRAM_API_HASH

        if not api_id or not api_hash:
            error_msg = f"Telegram API credentials not configured for account {account.id}. "
            if not api_id:
                error_msg += f"api_id is missing or invalid (account.api_id='{account.api_id}', env.TELEGRAM_API_ID='{settings.TELEGRAM_API_ID}'). "
            if not api_hash:
                error_msg += f"api_hash is missing or invalid (account.api_hash='{account.api_hash[:10] if account.api_hash else None}...', env.TELEGRAM_API_HASH='{settings.TELEGRAM_API_HASH[:10] if settings.TELEGRAM_API_HASH else None}...'). "
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Use DB-backed StringSession; None creates an empty session to be authenticated later
        session_string = getattr(account, "session_string", None)
        if session_string and "<telethon.sessions" not in session_string and len(session_string) > 10:
            try:
                sess = StringSession(session_string)
            except Exception as e:
                logger.warning(f"Invalid session string for account {account.id}, starting fresh: {e}")
                sess = StringSession()
        else:
            logger.info(f"No valid session string for account {account.id}, starting fresh")
            sess = StringSession()

        client = TelegramClient(
            sess,
            api_id,
            api_hash,
            proxy=proxy_details,
            device_model=self._generate_device_model(),
            system_version=self._generate_system_version(),
            app_version=self._generate_app_version(),
            lang_code="en",
            system_lang_code="en-US",
            # CRITICAL: Prevent Telethon from trying to read phone from stdin
            # This would cause EOFError in background workers
            loop=None,  # Let Telethon use the current event loop
        )
        # Mark client to not prompt for auth
        client._no_warning_tfl_user_newbies = True
        return client

    async def disconnect_client(self, account_id: int):
        """Persist the current StringSession to DB and disconnect the client."""
        client = self.active_clients.pop(account_id, None)
        if not client:
            return
        # Attempt to persist the session string before disconnecting
        try:
            session_str = None
            # StringSession returns a string via save() method
            try:
                if hasattr(client.session, "save"):
                    session_str = client.session.save()
                else:
                    # Fallback to __str__ if save() is not available
                    session_str = str(client.session)
                    # Ensure it's not the object representation
                    if "<telethon.sessions" in session_str:
                        session_str = None
            except Exception as save_error:
                logger.warning(f"Failed to get session string: {save_error}")
                session_str = None
            if session_str:
                db = SessionLocal()
                try:
                    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
                    if account:
                        account.session_string = session_str
                        account.last_activity = datetime.utcnow()
                        db.commit()
                finally:
                    db.close()
        except Exception as e:
            logger.warning(f"Failed to persist session for account {account_id}: {e}")
        # Finally, disconnect
        if client.is_connected():
            await client.disconnect()

    def _generate_device_model(self) -> str:
        models = ["iPhone 12 Pro", "iPhone 13", "iPhone 14", "Samsung Galaxy S21", "Google Pixel 6"]
        return random.choice(models)
    
    def _generate_system_version(self) -> str:
        versions = ["15.7.1", "16.1.2", "16.3.1", "16.4.1", "12", "13", "14"]
        return random.choice(versions)
    
    def _generate_app_version(self) -> str:
        versions = ["9.3.1", "9.4.0", "9.4.1", "9.5.0", "9.5.1"]
        return random.choice(versions)

session_manager = SessionManager(session_folder="/app/sessions")
