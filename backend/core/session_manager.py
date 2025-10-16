from pyrogram import Client
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
        # This cache holds active client connections.
        self.active_clients: Dict[int, Client] = {}

    async def get_client(self, account) -> Client:
        """Get a cached client or create a new one."""
        if account.id not in self.active_clients:
            self.active_clients[account.id] = await self._create_client(account)
        
        client = self.active_clients[account.id]
        if not client.is_connected:
            await client.start()
        return client

    async def _create_client(self, account):
        """Create a new client instance."""
        session_path = os.path.join(self.session_folder, f"account_{account.id}")

        proxy = None
        if account.proxy:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(account.proxy.proxy_url)
                proxy = {
                    "scheme": parsed_url.scheme,
                    "hostname": parsed_url.hostname,
                    "port": parsed_url.port,
                }
            except Exception as e:
                logger.error(f"Failed to parse proxy URL {account.proxy.proxy_url}: {e}")

        client = Client(
            name=session_path,
            api_id=int(account.api_id),
            api_hash=account.api_hash,
            proxy=proxy,
            device_model=self._generate_device_model(),
            system_version=self._generate_system_version(),
            app_version=self._generate_app_version(),
            lang_code="en",
            system_lang_code="en-US",
        )
        return client

    async def disconnect_client(self, account_id: int):
        """Disconnect and remove a client from the cache."""
        client = self.active_clients.pop(account_id, None)
        if client and client.is_connected:
            await client.stop()

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