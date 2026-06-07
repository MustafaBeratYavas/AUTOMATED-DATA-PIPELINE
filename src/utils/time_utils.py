"""Timing helpers used to vary browser interaction cadence."""

import random
import time


def random_sleep(min_seconds: float, max_seconds: float) -> None:
    """Sleep for a random duration inside the provided bounds."""
    time.sleep(random.uniform(min_seconds, max_seconds))
