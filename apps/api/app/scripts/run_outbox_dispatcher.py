import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.execution.dispatcher import OutboxDispatcher
from app.scripts._loop import StopFlag, run_forever


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    stop = StopFlag().install()
    dispatcher = OutboxDispatcher(
        SessionLocal,
        batch_size=settings.outbox_batch_size,
        max_attempts=settings.outbox_max_attempts,
    )
    run_forever(
        dispatcher.dispatch_once,
        name="outbox_dispatcher",
        interval_seconds=settings.outbox_poll_interval_seconds,
        should_stop=lambda: stop.stopping,
    )


if __name__ == "__main__":
    main()
