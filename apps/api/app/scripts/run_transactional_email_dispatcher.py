import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.scripts._loop import StopFlag, run_forever
from app.services.transactional_email_service import TransactionalEmailDispatcher


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    stop = StopFlag().install()

    def step() -> None:
        with SessionLocal() as session:
            TransactionalEmailDispatcher(session, settings).dispatch_batch()

    run_forever(
        step,
        name="transactional_email_dispatcher",
        interval_seconds=2,
        should_stop=lambda: stop.stopping,
    )


if __name__ == "__main__":
    main()
