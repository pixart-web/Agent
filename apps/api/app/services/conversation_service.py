from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.command import Command
from app.models.conversation import Conversation, ConversationMessage
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.command import CommandRead
from app.schemas.conversation import ConversationDetailRead, ConversationTurnRead
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

KIKO_ACKNOWLEDGEMENT = (
    "Criei um comando operacional para este pedido. Podes agora rever o plano, "
    "acompanhar a execução e aprovar ações sensíveis."
)


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.conversations = ConversationRepository(session)

    def create(self, user_id: UUID, content: str) -> ConversationTurnRead:
        user = self._active_user(user_id)
        conversation = Conversation(
            workspace_id=user.active_workspace_id,
            created_by_user_id=user.id,
            title=self._title(content),
        )
        self.session.add(conversation)
        self.session.flush()
        return self._append(conversation, user, content)

    def append(self, conversation_id: UUID, user_id: UUID, content: str) -> ConversationTurnRead:
        user = self._active_user(user_id)
        conversation = self.conversations.get_scoped(conversation_id, user_id)
        if conversation is None or conversation.archived_at is not None:
            raise WorkflowNotFoundError("Conversation not found")
        return self._append(conversation, user, content)

    def list(self, user_id: UUID, limit: int, offset: int) -> list[Conversation]:
        return self.conversations.list_scoped(user_id, limit, offset)

    def detail(
        self, conversation_id: UUID, user_id: UUID, limit: int, offset: int
    ) -> ConversationDetailRead:
        conversation = self.conversations.get_scoped(conversation_id, user_id)
        if conversation is None:
            raise WorkflowNotFoundError("Conversation not found")
        return ConversationDetailRead(
            conversation=conversation,
            messages=self.conversations.list_messages(conversation.id, limit, offset),
        )

    def _append(self, conversation: Conversation, user: User, content: str) -> ConversationTurnRead:
        try:
            command = Command(
                user_id=user.id,
                workspace_id=conversation.workspace_id,
                conversation_id=conversation.id,
                input=content,
            )
            user_message = ConversationMessage(
                conversation_id=conversation.id,
                author_user_id=user.id,
                role="user",
                content=content,
            )
            self.session.add_all([command, user_message])
            self.session.flush()
            kiko_message = ConversationMessage(
                conversation_id=conversation.id,
                command_id=command.id,
                role="kiko",
                content=KIKO_ACKNOWLEDGEMENT,
            )
            conversation.updated_at = utc_now()
            self.session.add(kiko_message)
            self.session.commit()
            for item in (conversation, user_message, kiko_message, command):
                self.session.refresh(item)
        except Exception:
            self.session.rollback()
            raise
        return ConversationTurnRead(
            conversation=conversation,
            messages=[user_message, kiko_message],
            command=CommandRead.model_validate(command),
        )

    def _active_user(self, user_id: UUID) -> User:
        user = self.session.get(User, user_id)
        if user is None or user.active_workspace_id is None:
            raise WorkflowConflictError("An active workspace is required")
        return user

    @staticmethod
    def _title(content: str) -> str:
        first_line = content.splitlines()[0].strip()
        return first_line[:157] + "..." if len(first_line) > 160 else first_line
