"""
core/account_lock.py

Redis-backed per-account execution lease.

Guarantees that at most one Celery task acts on a given Telegram account at
a time, even across multiple workers and replicas.

Design:
- Lock key: "account_lock:{account_id}"
- Lock value: "job:{job_id}"  (no pid — retries run in a new process)
- Re-entry: same job_id can re-acquire its own lock (refreshes TTL)
- Contention: a different job_id attempting to acquire returns False
- TTL: matches task_time_limit in celery_app.py (43200s = 12h)
"""

import logging
import os

import redis

from core.config import settings

logger = logging.getLogger(__name__)

# TTL must match task_time_limit in celery_app.py
_LOCK_TTL_SECONDS: int = 43200  # 12 hours

_redis_client: redis.Redis = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def _lock_key(account_id: int) -> str:
    return f"account_lock:{account_id}"


def _lock_value(job_id: int) -> str:
    return f"job:{job_id}"


def acquire_account_lock(account_id: int, job_id: int) -> bool:
    """
    Attempt to acquire an exclusive lease for account_id.

    Returns True if:
      - The lock was not held and has been acquired.
      - The lock is already held by this same job_id (re-entry / retry safe).
        In this case the TTL is refreshed.

    Returns False if a DIFFERENT job holds the lock.
    """
    key = _lock_key(account_id)
    value = _lock_value(job_id)

    # Atomic SET NX EX — only sets if key does not exist
    acquired = _redis_client.set(key, value, nx=True, ex=_LOCK_TTL_SECONDS)
    if acquired:
        logger.debug(f"account_lock: acquired lock for account {account_id} (job {job_id})")
        return True

    # Key already exists — check if WE hold it (retry re-entry)
    current_holder = _redis_client.get(key)
    if current_holder == value:
        # Same job: refresh TTL so long-running retries don't expire mid-task
        _redis_client.expire(key, _LOCK_TTL_SECONDS)
        logger.debug(
            f"account_lock: re-acquired lock for account {account_id} (job {job_id}), TTL refreshed"
        )
        return True

    logger.warning(
        f"account_lock: account {account_id} is locked by '{current_holder}', "
        f"job {job_id} cannot acquire"
    )
    return False


def release_account_lock(account_id: int) -> None:
    """
    Release the lock for account_id.

    Safe to call even if the lock has already expired or was released.
    """
    key = _lock_key(account_id)
    deleted = _redis_client.delete(key)
    if deleted:
        logger.debug(f"account_lock: released lock for account {account_id}")
    else:
        logger.debug(f"account_lock: lock for account {account_id} was already gone (expired or never held)")


def get_lock_holder(account_id: int) -> str | None:
    """
    Return the current lock holder value (e.g. 'job:42') or None if unlocked.
    Used for logging and debugging only.
    """
    return _redis_client.get(_lock_key(account_id))
