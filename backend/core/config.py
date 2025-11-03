import os
from typing import Optional

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tg_tools.db")

    # Telegram API
    TELEGRAM_API_ID: Optional[int] = (
        int(os.getenv("TELEGRAM_API_ID")) if os.getenv("TELEGRAM_API_ID") else None
    )
    TELEGRAM_API_HASH: Optional[str] = os.getenv("TELEGRAM_API_HASH")
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Redis (for Celery)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # Rate Limiting
    GLOBAL_MESSAGE_LIMIT: int = 30  # messages per minute globally
    USER_DAILY_LIMIT: int = 50      # DMs per day per account
    GROUP_DAILY_LIMIT: int = 100    # Group messages per day per account

settings = Settings()
