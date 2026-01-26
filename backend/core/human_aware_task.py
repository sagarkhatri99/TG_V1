
from celery import Task
import logging
import random
import time

logger = logging.getLogger(__name__)

class HumanAwareTask(Task):
    """
    Abstract base task that simulates human-like behavior.
    Adds random delays and checks "working hours".
    """
    abstract = True

    def __call__(self, *args, **kwargs):
        # Simulate human delay before starting task
        delay = random.uniform(0.5, 2.0)
        time.sleep(delay)
        return super().__call__(*args, **kwargs)
