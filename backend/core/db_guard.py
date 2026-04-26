"""
db_guard.py — Runtime SQLite safeguard.

Patches sqlite3.connect to raise RuntimeError, preventing any accidental
sqlite3.connect() call. This ensures the application remains strictly
PostgreSQL-only after the StringSession migration.
"""
import sqlite3
import logging
from typing import Any

_logger = logging.getLogger(__name__)

def _guarded_connect(database: Any, *args, **kwargs) -> sqlite3.Connection:
    """
    Guarded version of sqlite3.connect.
    Blocks ALL SQLite connections to enforce PostgreSQL-only mode.
    """
    error_msg = (
        f"[db_guard] Blocked sqlite3.connect('{database}'). "
        "This application must use PostgreSQL via SQLAlchemy exclusively. "
        "If this error originates from Telethon, the StringSession migration has failed "
        "or a code path is incorrectly falling back to file-based sessions."
    )
    _logger.critical(error_msg)
    raise RuntimeError(error_msg)

# Apply patch
sqlite3.connect = _guarded_connect  # type: ignore[assignment]

_logger.info("db_guard: sqlite3.connect has been patched — STRICT PostgreSQL-only mode active.")
