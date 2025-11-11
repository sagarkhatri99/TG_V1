import os
from typing import Optional

class Settings:
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
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
    
    # Security - SECRET_KEY must be set in production
    @property
    def SECRET_KEY(self) -> str:
        key = os.getenv("SECRET_KEY")
        if not key:
            if self.ENVIRONMENT == "production":
                raise ValueError("SECRET_KEY must be set in production environment")
            # Generate random key for development
            from secrets import token_urlsafe
            return token_urlsafe(32)
        return key
    
    # CORS - Strictly configured per environment
    @property
    def ALLOWED_ORIGINS(self) -> list:
        if self.ENVIRONMENT == "production":
            # Production: only specified domain
            return [os.getenv("PRODUCTION_DOMAIN", "https://yourdomain.com")]
        else:
            # Development: localhost variants
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8000",
            ]
    
    # Rate Limiting
    GLOBAL_MESSAGE_LIMIT: int = 30  # messages per minute globally
    USER_DAILY_LIMIT: int = 50      # DMs per day per account
    GROUP_DAILY_LIMIT: int = 100    # Group messages per day per account

settings = Settings()
