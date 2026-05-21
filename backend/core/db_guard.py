import sqlite3
import logging
import os
import inspect
from typing import Any

_logger = logging.getLogger(__name__)

# Original connect method
_original_connect = sqlite3.connect

# Environment control: default to false (Log-only mode) for safety initially
STRICT_MODE = os.getenv("STRICT_DB_GUARD", "false").lower() == "true"

# Callers that are explicitly allowed to use SQLite (e.g. library internals, tests)
ALLOWED_CALLERS = [
    "telethon/sessions",
    "pytest",
    "unittest",
]

def _guarded_connect(database: Any, *args, **kwargs) -> sqlite3.Connection:
    """
    Guarded version of sqlite3.connect.
    If STRICT_MODE is true, blocks unauthorized SQLite connections.
    Otherwise, logs a warning with the caller's stack trace.
    """
    # Check the call stack to see who is calling sqlite3.connect
    stack = inspect.stack()
    caller_info = "unknown"
    is_allowed = False
    
    for frame in stack:
        filename = frame.filename
        # Check if caller is in allow-list
        if any(allowed in filename for allowed in ALLOWED_CALLERS):
            is_allowed = True
            break
        if "db_guard.py" not in filename:
            caller_info = f"{filename}:{frame.lineno} in {frame.function}"

    if is_allowed:
        return _original_connect(database, *args, **kwargs)

    error_msg = (
        f"[db_guard] SQLite connection attempted to '{database}' by {caller_info}. "
        "This application is configured to use PostgreSQL via SQLAlchemy exclusively."
    )

    if STRICT_MODE:
        _logger.critical(f"BLOCKING: {error_msg}")
        raise RuntimeError(error_msg)
    else:
        _logger.warning(f"ADVISORY: {error_msg}")
        return _original_connect(database, *args, **kwargs)

# Apply patch
sqlite3.connect = _guarded_connect  # type: ignore[assignment]

if STRICT_MODE:
    _logger.info("db_guard: STRICT PostgreSQL-only mode active.")
else:
    _logger.info("db_guard: ADVISORY mode active (logging SQLite attempts).")
