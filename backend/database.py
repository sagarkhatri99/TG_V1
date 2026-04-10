import logging
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pool configuration — conservative values for stable production operation
# ---------------------------------------------------------------------------
_POOL_SIZE = 5
_MAX_OVERFLOW = 10
_POOL_TIMEOUT = 30
_POOL_RECYCLE = 1800  # 30 min — prevents stale connection errors

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    pool_timeout=_POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=_POOL_RECYCLE,
    connect_args={
        "options": "-c statement_timeout=30000"  # 30 s per-statement timeout (PostgreSQL)
    },
)

logger.info(
    "DB engine created — pool_size=%d, max_overflow=%d, pool_timeout=%ds, pool_recycle=%ds",
    _POOL_SIZE,
    _MAX_OVERFLOW,
    _POOL_TIMEOUT,
    _POOL_RECYCLE,
)

# ---------------------------------------------------------------------------
# Pool usage logging (DEBUG level — only active when LOG_LEVEL=DEBUG)
# ---------------------------------------------------------------------------
@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_conn, connection_record, connection_proxy):
    pool = engine.pool
    logger.debug(
        "DB pool checkout — size: %d, checked-out: %d, overflow: %d",
        pool.size(),
        pool.checkedout(),
        pool.overflow(),
    )


@event.listens_for(engine, "checkin")
def _on_checkin(dbapi_conn, connection_record):
    pool = engine.pool
    logger.debug(
        "DB pool checkin  — size: %d, checked-out: %d, overflow: %d",
        pool.size(),
        pool.checkedout(),
        pool.overflow(),
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a database session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
