from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.conversation import Conversation, ConversationMessage
from app.workspaces.scope import active_workspace_id


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_scoped(self, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == active_workspace_id(user_id),
            )
        )

    def list_scoped(self, user_id: UUID, limit: int, offset: int) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(
                    Conversation.workspace_id == active_workspace_id(user_id),
                    Conversation.archived_at.is_(None),
                )
                .order_by(Conversation.updated_at.desc(), Conversation.id)
                .limit(limit)
                .offset(offset)
            )
        )

    def list_messages(
        self, conversation_id: UUID, limit: int, offset: int
    ) -> list[ConversationMessage]:
        return list(
            self.session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at, ConversationMessage.id)
                .limit(limit)
                .offset(offset)
            )
        )

    def list_commands(self, conversation_id: UUID, command_ids: list[UUID]) -> list[Command]:
        if not command_ids:
            return []
        return list(
            self.session.scalars(
                select(Command)
                .where(
                    Command.conversation_id == conversation_id,
                    Command.id.in_(command_ids),
                )
                .order_by(Command.created_at, Command.id)
            )
        )
