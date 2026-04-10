"""
db_guard.py — Runtime SQLite safeguard.

Patches sqlite3.connect to raise RuntimeError, preventing any accidental
sqlite3.connect() call for the main application database.

Telethon Compatibility:
- Telethon's SQLiteSession uses sqlite3.connect() for .session files.
- We allow these specifically while blocking everything else.

Import this module FIRST in main.py and celery_app.py.
"""
import sqlite3
import logging
from typing import Any

_logger = logging.getLogger(__name__)

_original_connect = sqlite3.connect


def _guarded_connect(database: Any, *args, **kwargs) -> sqlite3.Connection:
    """
    Guarded version of sqlite3.connect.
    Allows connections to .session files (Telethon) but blocks others.
    """
    # If the database is a string and looks like a Telegram session, allow it.
    if isinstance(database, str) and ".session" in database.lower():
        _logger.debug("db_guard: allowing SQLite connection to session file: %s", database)
        return _original_connect(database, *args, **kwargs)

    # Block everything else
    raise RuntimeError(
        f"sqlite3.connect({database}) is disabled in this application. "
        "The main application database must use PostgreSQL via SQLAlchemy. "
        "If this is a third-party library requiring SQLite, it must be explicitly exempted in core/db_guard.py."
    )


# Apply patch
sqlite3.connect = _guarded_connect  # type: ignore[assignment]

_logger.info("db_guard: sqlite3.connect has been patched — PostgreSQL-only mode active (Telethon exempted).")
