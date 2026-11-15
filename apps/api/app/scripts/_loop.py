"""Resilient polling loop for long-running dispatchers.

A transient failure (for example PostgreSQL restarting) must not kill a dispatcher: the error
is logged, the loop backs off exponentially (capped) and resumes. SIGTERM/SIGINT stop it
cleanly between iterations.
"""

import logging
import signal
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class StopFlag:
    def __init__(self) -> None:
        self.stopping = False

    def __call__(self, _signum: int, _frame: object) -> None:
        self.stopping = True

    def install(self) -> "StopFlag":
        signal.signal(signal.SIGTERM, self)
        signal.signal(signal.SIGINT, self)
        return self


def run_forever(
    step: Callable[[], object],
    *,
    name: str,
    interval_seconds: float,
    should_stop: Callable[[], bool],
    sleep: Callable[[float], None] = time.sleep,
    max_backoff_seconds: float = 30.0,
) -> None:
    failures = 0
    while not should_stop():
        try:
            step()
        except Exception:
            failures += 1
            delay = min(max_backoff_seconds, interval_seconds * (2 ** min(failures, 10)))
            logger.exception("%s iteration failed; retrying in %.1fs", name, delay)
            sleep(delay)
            continue
        if failures:
            logger.info("%s recovered after %d failed iteration(s)", name, failures)
            failures = 0
        sleep(interval_seconds)
