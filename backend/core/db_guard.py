"""
db_guard.py — Runtime SQLite safeguard.

Patches sqlite3.connect to raise RuntimeError, preventing any accidental
sqlite3.connect() call in application code.

Safety notes:
- We patch only sqlite3.connect, NOT the sqlite3 module itself.
  Third-party libraries that merely `import sqlite3` are unaffected.
- Telethon's SQLiteSession uses its own internal file I/O and does NOT
  call sqlite3.connect(), so Telegram session handling is unaffected.

Import this module FIRST in main.py and celery_app.py.
"""
import sqlite3
import logging

_logger = logging.getLogger(__name__)

_original_connect = sqlite3.connect


def _blocked_connect(*args, **kwargs):
    raise RuntimeError(
        "sqlite3.connect() is disabled in this application. "
        "All database access must use PostgreSQL via SQLAlchemy. "
        "If you see this error from a third-party library, contact the project maintainers."
    )


# Apply patch
sqlite3.connect = _blocked_connect  # type: ignore[assignment]

_logger.debug("db_guard: sqlite3.connect has been patched — PostgreSQL-only mode active.")
