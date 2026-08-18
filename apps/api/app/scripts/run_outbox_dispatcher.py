import signal
import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.execution.dispatcher import OutboxDispatcher

_stopping = False


def _stop(_signum, _frame) -> None:
    global _stopping
    _stopping = True


def main() -> None:
    settings = get_settings()
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    dispatcher = OutboxDispatcher(
        SessionLocal,
        batch_size=settings.outbox_batch_size,
        max_attempts=settings.outbox_max_attempts,
    )
    while not _stopping:
        dispatcher.dispatch_once()
        time.sleep(settings.outbox_poll_interval_seconds)


if __name__ == "__main__":
    main()
