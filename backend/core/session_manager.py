from telethon import TelegramClient
import asyncio
import random
from typing import Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, session_folder="sessions"):
        self.session_folder = session_folder
        os.makedirs(self.session_folder, exist_ok=True)

    async def get_client(self, account) -> TelegramClient:
        """Create a Telegram client for an account."""
        return await self._create_client(account)

    async def _create_client(self, account):
        """Create a new client with anti-detection features"""

        proxy = None
        if hasattr(account, 'proxy') and account.proxy:
            proxy_parts = account.proxy.proxy_url.split(':')
            proxy = {
                'proxy_type': account.proxy.proxy_type,
                'addr': proxy_parts[0],
                'port': int(proxy_parts[1]),
            }

        session_path = os.path.join(self.session_folder, f"account_{account.id}.session")

        client = TelegramClient(
            session_path,
            int(account.api_id),
            account.api_hash,
            proxy=proxy,
            device_model=self._generate_device_model(),
            system_version=self._generate_system_version(),
            app_version=self._generate_app_version(),
            lang_code="en",
            system_lang_code="en-US",
        )

        return client

    def _generate_device_model(self) -> str:
        """Generate random device model for anti-detection"""
        models = [
            "iPhone 12 Pro", "iPhone 13", "iPhone 14", "Samsung Galaxy S21",
            "Samsung Galaxy S22", "Google Pixel 6", "Google Pixel 7",
            "OnePlus 9", "OnePlus 10", "Xiaomi Mi 12"
        ]
        return random.choice(models)

    def _generate_system_version(self) -> str:
        """Generate random system version"""
        versions = ["15.7.1", "16.1.2", "16.3.1", "16.4.1", "12", "13", "14"]
        return random.choice(versions)

    def _generate_app_version(self) -> str:
        """Generate random Telegram app version"""
        versions = ["9.3.1", "9.4.0", "9.4.1", "9.5.0", "9.5.1"]
        return random.choice(versions)

# Global session manager instance
session_manager = SessionManager(session_folder="/app/sessions")