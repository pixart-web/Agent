from sqlalchemy.orm import Session

from app.models.transactional_email import TransactionalEmailOutbox


class TransactionalEmailRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, message: TransactionalEmailOutbox) -> None:
        self.session.add(message)
