"""
core/session_manager.py

Manages Telethon TelegramClient lifecycle across Celery workers.

Key design decisions (see implementation plan addenda for rationale):
- active_clients is keyed by (pid, account_id) — process-safe, no cross-process leaks.
- Only StringSession is used — no file-based sessions.
- disconnect_client suppresses sqlite3.OperationalError on DB write (Stage 0.5 hotfix).
- _create_client accepts any duck-type with the same attributes as TelegramAccount
  (including AccountSnapshot from core/db_utils.py) — no ORM session needed.
"""

from __future__ import annotations

import logging
import os
import random
import sqlite3
from datetime import datetime
from typing import Dict, Tuple, Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from database import SessionLocal
from models import TelegramAccount, Proxy
from core.config import settings
from core.proxy_utils import build_proxy_config

logger = logging.getLogger(__name__)

# Cache key type: (pid, account_id)
_CacheKey = Tuple[int, int]


class SessionManager:
    def __init__(self, session_folder: str = "/app/sessions"):
        # session_folder retained for audit compatibility only.
        # No new .session files are written by this class.
        self.session_folder = session_folder
        os.makedirs(self.session_folder, exist_ok=True)

        # Keyed by (pid, account_id) — process-isolated, prevents cross-process
        # ghost sessions in prefork worker pools.
        self.active_clients: Dict[_CacheKey, TelegramClient] = {}

    # ------------------------------------------------------------------
    # Cache key helper
    # ------------------------------------------------------------------

    def _key(self, account_id: int) -> _CacheKey:
        """Return a process-safe cache key for account_id."""
        return (os.getpid(), account_id)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_client(self, account, allow_unauth: bool = False) -> TelegramClient:
        """
        Return a connected TelegramClient for the given account.

        account may be a TelegramAccount ORM instance or an AccountSnapshot
        dataclass — any object with .id, .api_id, .api_hash, .session_string,
        .proxy_id, .proxy attributes.

        Args:
            account:     Account object (ORM or AccountSnapshot).
            allow_unauth: Skip authorization check (for initial verification flow).
        """
        key = self._key(account.id)
        if key not in self.active_clients:
            self.active_clients[key] = await self._create_client(account)
        client = self.active_clients[key]

        if not client.is_connected():
            try:
                await client.connect()
            except (EOFError, OSError) as e:
                if not allow_unauth:
                    raise RuntimeError(
                        f"Cannot connect to Telegram for account {account.id}. "
                        f"The session is not authenticated. "
                        f"Please log in first via the frontend. Error: {e}"
                    )
                logger.info(f"Account {account.id} connecting for initial verification")

        if not allow_unauth:
            try:
                if not await client.is_user_authorized():
                    raise RuntimeError(
                        f"Account {account.id} is not authorized. "
                        f"Please log in via the frontend."
                    )
            except Exception as auth_check_err:
                logger.warning(
                    f"Could not verify auth status for account {account.id}: {auth_check_err}"
                )

        return client

    async def disconnect_client(self, account_id: int) -> None:
        """
        Persist the current StringSession to DB and disconnect the client.

        Stage 0.5 hotfix: sqlite3.OperationalError during the DB write is
        suppressed with a warning — the client is always disconnected even if
        session persistence fails. This stops the 'database is locked' errors
        in routers/accounts.py (/test, /resume, /verify) immediately.

        After Fix 4 (StringSession-only), file-based sqlite3.OperationalError
        will no longer occur from the session layer — this suppression becomes
        belt-and-suspenders only.
        """
        key = self._key(account_id)
        client = self.active_clients.pop(key, None)
        if not client:
            return

        # Step 1: extract the session string
        session_str: Optional[str] = None
        try:
            if hasattr(client.session, "save"):
                session_str = client.session.save()
            else:
                s = str(client.session)
                session_str = None if "<telethon.sessions" in s else s
        except Exception as save_err:
            logger.warning(
                f"disconnect_client: could not get session string for account "
                f"{account_id}: {save_err}"
            )

        # Step 2: persist session string to DB
        if session_str:
            db = SessionLocal()
            try:
                account = (
                    db.query(TelegramAccount)
                    .filter(TelegramAccount.id == account_id)
                    .first()
                )
                if account:
                    account.session_string = session_str
                    account.last_activity = datetime.utcnow()
                    db.commit()
            except sqlite3.OperationalError as db_lock_err:
                # Stage 0.5 hotfix: suppress DB-locked errors — session will
                # be persisted on the next successful disconnect.
                logger.warning(
                    f"disconnect_client: DB locked while saving session for account "
                    f"{account_id} — session NOT persisted this cycle. "
                    f"Error: {db_lock_err}"
                )
                try:
                    db.rollback()
                except Exception:
                    pass
            except Exception as db_err:
                logger.warning(
                    f"disconnect_client: could not persist session for account "
                    f"{account_id}: {db_err}"
                )
                try:
                    db.rollback()
                except Exception:
                    pass
            finally:
                db.close()

        # Step 3: always disconnect — even if session persist failed
        try:
            if client.is_connected():
                await client.disconnect()
        except Exception as disc_err:
            logger.warning(
                f"disconnect_client: error during Telegram disconnect for account "
                f"{account_id}: {disc_err}"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _create_client(self, account) -> TelegramClient:
        """
        Create a new TelegramClient bound to a StringSession from DB.

        Accepts any duck-type with: .id, .api_id, .api_hash, .session_string,
        .proxy_id, .proxy attributes (ORM TelegramAccount or AccountSnapshot).

        Fix 4: File-based session fallback removed. Only StringSession is used.
        Any account whose session_string is a short filename (from /import-sessions)
        must be migrated to a real StringSession string before Stage 1 deploys.
        """
        # 1. Resolve proxy
        proxy_details = None
        proxy_obj = None

        if getattr(account, "proxy", None) is not None:
            # Eagerly-loaded ORM relationship or ProxySnapshot dataclass
            proxy_obj = account.proxy
        elif getattr(account, "proxy_id", None):
            # Fallback: load from DB (only hits for ORM objects whose proxy
            # relationship was not eagerly loaded — AccountSnapshot always has
            # proxy pre-loaded via snapshot_account())
            try:
                db = SessionLocal()
                try:
                    proxy_obj = (
                        db.query(Proxy)
                        .filter(Proxy.id == account.proxy_id)
                        .first()
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(
                    f"Failed to fetch proxy for account {account.id} from DB: {e}"
                )

        if proxy_obj:
            try:
                proxy_config = build_proxy_config(proxy_obj)
                proxy_details = proxy_config.get("telethon")
                logger.info(
                    f"Using proxy for account {account.id}: {proxy_config.get('details')}"
                )
            except Exception as e:
                error_msg = (
                    f"Account {account.id} has an invalid proxy assigned. "
                    f"Connection aborted. Error: {e}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        # 2. Resolve API credentials
        try:
            api_id = (
                int(account.api_id)
                if getattr(account, "api_id", None) and str(account.api_id).strip()
                else settings.TELEGRAM_API_ID
            )
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(
                f"Invalid api_id for account {account.id}: "
                f"{getattr(account, 'api_id', None)}, error: {e}"
            )
            api_id = settings.TELEGRAM_API_ID

        api_hash = (
            account.api_hash
            if getattr(account, "api_hash", None) and str(account.api_hash).strip()
            else settings.TELEGRAM_API_HASH
        )

        if not api_id or not api_hash:
            error_msg = (
                f"Telegram API credentials not configured for account {account.id}. "
            )
            if not api_id:
                error_msg += (
                    f"api_id is missing (account.api_id='{getattr(account, 'api_id', None)}', "
                    f"env.TELEGRAM_API_ID='{settings.TELEGRAM_API_ID}'). "
                )
            if not api_hash:
                api_hash_preview = (
                    str(getattr(account, "api_hash", None) or "")[:10] or "None"
                )
                error_msg += f"api_hash is missing (preview='{api_hash_preview}...'). "
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # 3. Build StringSession — Fix 4: NO file-based session fallback.
        # If session_string is a short filename (legacy /import-sessions account),
        # it will fail here. Run the Stage 0 migration first.
        session_string = getattr(account, "session_string", None)
        if (
            session_string
            and "<telethon.sessions" not in session_string
            and len(session_string) > 10
        ):
            try:
                sess = StringSession(session_string)
                logger.info(f"Using StringSession for account {account.id}")
            except Exception as e:
                logger.warning(
                    f"Invalid session string for account {account.id}, "
                    f"starting fresh StringSession: {e}"
                )
                sess = StringSession()
        else:
            logger.info(
                f"No valid session string for account {account.id}, "
                f"starting fresh StringSession"
            )
            sess = StringSession()

        # 4. Create and return the client
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
            loop=None,  # Use current event loop
        )
        # Suppress Telethon's interactive auth prompts — background workers
        # must never block on stdin.
        client._no_warning_tfl_user_newbies = True
        return client

    # ------------------------------------------------------------------
    # Device fingerprint randomisation
    # ------------------------------------------------------------------

    def _generate_device_model(self) -> str:
        models = [
            "iPhone 12 Pro", "iPhone 13", "iPhone 14",
            "Samsung Galaxy S21", "Google Pixel 6",
        ]
        return random.choice(models)

    def _generate_system_version(self) -> str:
        versions = ["15.7.1", "16.1.2", "16.3.1", "16.4.1", "12", "13", "14"]
        return random.choice(versions)

    def _generate_app_version(self) -> str:
        versions = ["9.3.1", "9.4.0", "9.4.1", "9.5.0", "9.5.1"]
        return random.choice(versions)


# Module-level singleton — one per process (prefork workers get their own copy)
session_manager = SessionManager(session_folder="/app/sessions")
