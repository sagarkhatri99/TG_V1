"""
core/task_registry.py

Single source of truth for Celery task dispatch metadata.

Import this wherever tasks need to be dispatched dynamically.
Do NOT define TASK_MAP or task_map inline in routers or other modules —
that creates drift when a new job type is added.

To add a new job type:
  1. Add an entry to TASK_MAP below.
  2. Classify it in TELETHON_JOB_TYPES or BOT_JOB_TYPES.
  3. Add it to celery_app.py task_routes.
  4. If it is a Telethon job type, restart worker-long with the updated
     CELERY_ACCOUNT_QUEUES env var (or wait for sync_worker_queues beat task).
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Task map — job_type → (module_path, function_name)
# ---------------------------------------------------------------------------

TASK_MAP: dict[str, tuple[str, str]] = {
    "auto_promo":      ("auto_promo.tasks",       "auto_promo_task"),
    "mass_dm_account": ("mass_dm_account.tasks",  "mass_dm_account_task"),
    "mass_dm_bot":     ("mass_dm_bot.tasks",       "mass_dm_bot_task"),
    "group_monitor":   ("group_monitor.tasks",     "group_monitor_task"),
    "group_join":      ("group_joiner.tasks",       "group_join_task"),
    "scrape_users":    ("scrape_user_id.tasks",    "scrape_users_task"),
}

# ---------------------------------------------------------------------------
# Job type classification
# ---------------------------------------------------------------------------

# These job types bind to a single Telegram account session.
# They MUST be routed to per-account queues and cannot run concurrently
# for the same account.
TELETHON_JOB_TYPES: frozenset[str] = frozenset({
    "auto_promo",
    "mass_dm_account",
    "group_monitor",
    "group_join",
    "scrape_users",
})

# These job types use a bot token (not an account session).
# They can run concurrently and stay on the shared long_tasks queue.
BOT_JOB_TYPES: frozenset[str] = frozenset({
    "mass_dm_bot",
})


# ---------------------------------------------------------------------------
# Queue routing helper
# ---------------------------------------------------------------------------

def get_queue_for_job(job_type: str, account_id: Optional[int]) -> str:
    """
    Return the Celery queue name for a given job dispatch.

    Telethon jobs are routed to a per-account queue so they execute
    serially for each account. Bot jobs use the shared long_tasks queue.

    Args:
        job_type:   The job_type string (e.g. 'auto_promo').
        account_id: The telegram_account_id of the job, or None.

    Returns:
        Queue name string, e.g. 'account_5' or 'long_tasks'.
    """
    if job_type in TELETHON_JOB_TYPES and account_id:
        return f"account_{account_id}"
    return "long_tasks"
