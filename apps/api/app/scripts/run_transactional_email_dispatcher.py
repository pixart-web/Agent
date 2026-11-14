import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.transactional_email_service import TransactionalEmailDispatcher


def main() -> None:
    settings = get_settings()
    while True:
        with SessionLocal() as session:
            TransactionalEmailDispatcher(session, settings).dispatch_batch()
        time.sleep(2)


if __name__ == "__main__":
    main()
