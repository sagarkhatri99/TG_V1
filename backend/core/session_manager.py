"""
core/session_manager.py

Manages Telethon TelegramClient lifecycle across Celery workers.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from typing import Dict, Tuple, Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from database import SessionLocal
from models import TelegramAccount, Proxy
from core.config import settings
from core.proxy_utils import build_proxy_config
from core.db_utils import get_short_session

logger = logging.getLogger(__name__)

# Cache key type: (pid, account_id)
_CacheKey = Tuple[int, int]


class SessionManager:
    def __init__(self):
        # Keyed by (pid, account_id) — process-isolated
        self.active_clients: Dict[_CacheKey, TelegramClient] = {}

    def _key(self, account_id: int) -> _CacheKey:
        """Return a process-safe cache key for account_id."""
        return (os.getpid(), account_id)

    async def get_client(self, account, allow_unauth: bool = False) -> TelegramClient:
        """Return a connected TelegramClient for the given account."""
        key = self._key(account.id)
        if key not in self.active_clients:
            self.active_clients[key] = await self._create_client(account)
        client = self.active_clients[key]

        if not client.is_connected():
            try:
                await client.connect()
                # Persist session string immediately after connection
                if hasattr(client.session, "save"):
                    session_str = client.session.save()
                    if session_str:
                        with get_short_session() as db:
                            acc = db.query(TelegramAccount).filter(TelegramAccount.id == account.id).first()
                            if acc:
                                acc.session_string = session_str
                                db.commit()
            except (EOFError, OSError) as e:
                if not allow_unauth:
                    raise RuntimeError(f"Cannot connect for account {account.id}: {e}")
                logger.info(f"Account {account.id} connecting for initial verification")

        if not allow_unauth:
            try:
                if not await client.is_user_authorized():
                    raise RuntimeError(f"Account {account.id} is not authorized.")
            except Exception as auth_check_err:
                logger.warning(f"Auth verify failed for account {account.id}: {auth_check_err}")

        return client

    async def disconnect_client(self, account_id: int) -> None:
        """
        Disconnect the client and persist the final StringSession to DB.
        Lifecycle: disconnect -> extract -> persist.
        """
        try:
            key = self._key(account_id)
            client = self.active_clients.pop(key, None)
            if not client:
                return

            # Step 1: Disconnect first so Telethon flushes state
            if client.is_connected():
                try:
                    await client.disconnect()
                except Exception as disc_err:
                    logger.warning(f"disconnect_client error {account_id}: {disc_err}")

            # Step 2: Extract session AFTER disconnect (freshest state)
            session_str: Optional[str] = None
            try:
                if hasattr(client.session, "save"):
                    session_str = client.session.save()
            except Exception as save_err:
                logger.warning(f"session extract error {account_id}: {save_err}")

            # Step 3: Persist to DB
            if session_str:
                try:
                    with get_short_session() as db:
                        acc = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
                        if acc:
                            acc.session_string = session_str
                            acc.last_activity = datetime.utcnow()
                            db.commit()
                except Exception as db_err:
                    logger.warning(f"session persist error {account_id}: {db_err}")

        except Exception as e:
            logger.error(f"disconnect_client: FATAL unhandled exception {account_id}: {e}")

    async def _create_client(self, account) -> TelegramClient:
        """Create a new TelegramClient bound to a StringSession from DB."""
        # 1. Resolve proxy
        proxy_details = None
        proxy_obj = getattr(account, "proxy", None)
        
        if not proxy_obj and getattr(account, "proxy_id", None):
            with SessionLocal() as db:
                proxy_obj = db.query(Proxy).filter(Proxy.id == account.proxy_id).first()

        if proxy_obj:
            try:
                proxy_config = build_proxy_config(proxy_obj)
                proxy_details = proxy_config.get("telethon")
            except Exception as e:
                logger.error(f"Invalid proxy for account {account.id}: {e}")
                raise ValueError(f"Invalid proxy: {e}")

        # 2. Resolve API credentials
        api_id = int(account.api_id) if getattr(account, "api_id", None) else settings.TELEGRAM_API_ID
        api_hash = account.api_hash if getattr(account, "api_hash", None) else settings.TELEGRAM_API_HASH

        if not api_id or not api_hash:
            raise RuntimeError(f"API credentials missing for account {account.id}")

        # 3. Build StringSession
        session_string = getattr(account, "session_string", None)
        if session_string and len(session_string) > 10 and "<tele" not in session_string:
            sess = StringSession(session_string)
        else:
            sess = StringSession()

        # 4. Create client
        client = TelegramClient(
            sess, api_id, api_hash, proxy=proxy_details,
            device_model=self._generate_device_model(),
            system_version=self._generate_system_version(),
            app_version=self._generate_app_version(),
            lang_code="en", system_lang_code="en-US"
        )
        client._no_warning_tfl_user_newbies = True
        return client

    def _generate_device_model(self) -> str:
        return random.choice(["iPhone 13", "iPhone 14", "Samsung S22", "Pixel 7"])

    def _generate_system_version(self) -> str:
        return random.choice(["16.1", "16.4", "13", "14"])

    def _generate_app_version(self) -> str:
        return random.choice(["9.4.0", "9.5.1"])


# Module-level singleton
session_manager = SessionManager()
