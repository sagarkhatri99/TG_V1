"""
Celery and Flower configuration for task monitoring.
Enables centralized monitoring of background jobs and workers.
"""

from kombu import Exchange, Queue

# Celery Broker Configuration (Redis)
broker_url = "redis://redis:6379/0"
result_backend = "redis://redis:6379/1"

# Task Configuration
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True

# Task Execution Options
task_track_started = True  # Track when tasks start
task_acks_late = True  # Acknowledge tasks after completion, not before
task_reject_on_worker_lost = True  # Reject tasks if worker dies

# Worker Configuration
worker_prefetch_multiplier = 4  # Prefetch up to 4 tasks per worker
worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks to avoid memory leaks
worker_disable_rate_limits = False  # Enable rate limiting

# Retry Configuration
task_autoretry_for = (Exception,)
task_max_retries = 3
task_default_retry_delay = 60  # 1 minute

# Queue Configuration
task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("long_tasks", Exchange("long_tasks"), routing_key="long_tasks"),
    Queue("short_tasks", Exchange("short_tasks"), routing_key="short_tasks"),
)

task_routes = {
    "mass_dm_account.tasks.mass_dm_account_task": {"queue": "long_tasks"},
    "group_monitor.tasks.group_monitor_task": {"queue": "long_tasks"},
    "mass_dm_bot.tasks.mass_dm_bot_task": {"queue": "long_tasks"},
    "auto_promo.tasks.auto_promo_task": {"queue": "long_tasks"},
}

# Flower Configuration (monitoring and management UI)
# Accessed at http://localhost:5555
flower_persistent = True  # Keep stats across restarts
flower_db = "flower_db"  # Store stats in redis key
flower_max_tasks = 100000  # Keep last 100k tasks in memory
flower_enable_events = True  # Enable Celery event monitoring
