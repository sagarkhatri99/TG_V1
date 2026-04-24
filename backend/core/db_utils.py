"""
core/db_utils.py

Database session utilities and snapshot dataclasses.

Rules:
- Use get_short_session() for every DB operation in task runners and routers.
- Never hold a get_short_session() session open across an await or asyncio.sleep().
- Use snapshot_account() to copy ORM data to plain Python before the session closes.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

from database import SessionLocal

logger = logging.getLogger(__name__)


@contextmanager
def get_short_session():
    """
    Yield a SQLAlchemy session scoped to a single operation block.

    - Commits on clean exit.
    - Rolls back on exception, then re-raises.
    - Always closes the session (returns connection to pool).

    Usage::

        with get_short_session() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            job.status = 'running'
        # session closed, connection returned to pool

    NEVER hold this open across an await or asyncio.sleep().
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Snapshot dataclasses — plain Python, safe to use after session closes
# ---------------------------------------------------------------------------

@dataclass
class ProxySnapshot:
    """Immutable copy of a Proxy ORM row. No SQLAlchemy dependency."""
    id: int
    proxy_url: str
    proxy_type: str
    country_code: Optional[str]
    status: str
    ip_address: Optional[str]
    provider: Optional[str]


@dataclass
class AccountSnapshot:
    """
    Immutable copy of a TelegramAccount ORM row plus its eagerly-loaded Proxy.
    Pass this to session_manager instead of the ORM object so the session can
    be closed before any async Telethon call.
    """
    id: int
    api_id: str
    api_hash: str
    session_string: Optional[str]
    proxy_id: Optional[int]
    proxy: Optional[ProxySnapshot]
    phone_number: str


def snapshot_account(account) -> AccountSnapshot:
    """
    Copy all fields needed by session_manager from an ORM TelegramAccount
    into a plain AccountSnapshot.

    MUST be called while the SQLAlchemy session is still open (so that the
    eagerly-loaded proxy relationship is accessible).

    Usage::

        with get_short_session() as db:
            account = (
                db.query(TelegramAccount)
                .options(joinedload(TelegramAccount.proxy))
                .filter(TelegramAccount.id == account_id)
                .first()
            )
            snap = snapshot_account(account)
        # session closed — snap is safe to use anywhere
    """
    proxy_snap: Optional[ProxySnapshot] = None
    if account.proxy is not None:
        p = account.proxy
        proxy_snap = ProxySnapshot(
            id=p.id,
            proxy_url=p.proxy_url,
            proxy_type=p.proxy_type,
            country_code=p.country_code,
            status=p.status,
            ip_address=p.ip_address,
            provider=p.provider,
        )

    return AccountSnapshot(
        id=account.id,
        api_id=account.api_id,
        api_hash=account.api_hash,
        session_string=account.session_string,
        proxy_id=account.proxy_id,
        proxy=proxy_snap,
        phone_number=account.phone_number,
    )
