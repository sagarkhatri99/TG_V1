import os
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Eager validation of required environment variables.
# Any missing or invalid value causes an immediate Exception at import time
# so the process refuses to start rather than failing silently later.
# ---------------------------------------------------------------------------

def _require_env(name: str, *, reject_sqlite: bool = False) -> str:
    """Read a required env var, raise clearly if missing or invalid."""
    value = os.getenv(name)
    if not value:
        raise Exception(
            f"Required environment variable '{name}' is not set. "
            "Set it in your .env file or docker-compose environment section."
        )
    if reject_sqlite and "sqlite" in value.lower():
        raise Exception(
            f"'{name}' contains 'sqlite' which is not allowed. "
            "Use a PostgreSQL connection string "
            "(e.g. postgresql://user:password@host:5432/dbname)."
        )
    return value


# Validated at import time — process will not start if any of these are missing
_raw_db_url: str = _require_env("DATABASE_URL", reject_sqlite=True)
_redis_url: str = _require_env("REDIS_URL")
_celery_broker_url: str = _require_env("CELERY_BROKER_URL")


def mask_db_url(url: str) -> str:
    """Return a URL with the password replaced by *** for safe logging."""
    return re.sub(r"(?<=://)([^:]+):([^@]+)@", r"\1:***@", url)


class Settings:
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database — pre-validated; expose as class attribute for convenience
    DATABASE_URL: str = _raw_db_url

    # Redis / Celery — pre-validated
    REDIS_URL: str = _redis_url
    CELERY_BROKER_URL: str = _celery_broker_url

    # Telegram API
    TELEGRAM_API_ID: Optional[int] = (
        int(os.getenv("TELEGRAM_API_ID")) if os.getenv("TELEGRAM_API_ID") else None
    )
    TELEGRAM_API_HASH: Optional[str] = os.getenv("TELEGRAM_API_HASH")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Security — must be set in production
    @property
    def SECRET_KEY(self) -> str:
        key = os.getenv("SECRET_KEY")
        if not key:
            if self.ENVIRONMENT == "production":
                raise ValueError("SECRET_KEY must be set in production environment")
            from secrets import token_urlsafe
            return token_urlsafe(32)
        return key

    # CORS
    @property
    def ALLOWED_ORIGINS(self) -> list:
        if self.ENVIRONMENT == "production":
            return [os.getenv("PRODUCTION_DOMAIN", "https://yourdomain.com")]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
        ]

    # Rate Limiting
    GLOBAL_MESSAGE_LIMIT: int = 30   # messages per minute globally
    USER_DAILY_LIMIT: int = 50       # DMs per day per account
    GROUP_DAILY_LIMIT: int = 100     # Group messages per day per account


settings = Settings()

# Module-level aliases — support `from core.config import DATABASE_URL`
DATABASE_URL: str = _raw_db_url
REDIS_URL: str = _redis_url
CELERY_BROKER_URL: str = _celery_broker_url
