# -- Randomised Delay Utility --
# Introduces non-deterministic sleep intervals to emulate human browsing cadence.
# Critical for anti-bot evasion across rate-limited marketplace endpoints.

import time
import random

def random_sleep(min_seconds: float, max_seconds: float) -> None:
    # Block execution for a uniformly distributed random duration between bounds
    time.sleep(random.uniform(min_seconds, max_seconds))
