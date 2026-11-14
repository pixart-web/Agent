from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.approval_request import ApprovalRequest
from app.models.command import Command
from app.models.conversation import Conversation, ConversationMessage
from app.models.plan import Plan
from app.models.supervisor_run import SupervisorRun
from app.models.task import Task
from app.models.user import User
from app.models.workflow_enums import ApprovalStatus
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.command import CommandRead
from app.schemas.conversation import (
    ConversationDetailRead,
    ConversationOperationRead,
    ConversationPlanRead,
    ConversationTurnRead,
)
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

    def list_conversations(self, user_id: UUID, limit: int, offset: int) -> list[Conversation]:
        return self.conversations.list_scoped(user_id, limit, offset)

    def detail(
        self, conversation_id: UUID, user_id: UUID, limit: int, offset: int
    ) -> ConversationDetailRead:
        conversation = self.conversations.get_scoped(conversation_id, user_id)
        if conversation is None:
            raise WorkflowNotFoundError("Conversation not found")
        messages = self.conversations.list_messages(conversation.id, limit, offset)
        command_ids = [item.command_id for item in messages if item.command_id is not None]
        commands = self.conversations.list_commands(conversation.id, command_ids)
        return ConversationDetailRead(
            conversation=conversation,
            messages=messages,
            operations=self._operations(commands),
        )

    def _operations(self, commands: list[Command]) -> list[ConversationOperationRead]:
        if not commands:
            return []
        command_ids = [item.id for item in commands]
        plans = list(
            self.session.scalars(
                select(Plan).where(Plan.command_id.in_(command_ids), Plan.is_current.is_(True))
            )
        )
        plans_by_command = {item.command_id: item for item in plans}
        plan_ids = [item.id for item in plans]
        tasks = (
            list(
                self.session.scalars(
                    select(Task)
                    .where(Task.plan_id.in_(plan_ids))
                    .order_by(Task.updated_at, Task.id)
                )
            )
            if plan_ids
            else []
        )
        tasks_by_plan: dict[UUID, list[Task]] = {}
        for task in tasks:
            tasks_by_plan.setdefault(task.plan_id, []).append(task)
        task_ids = [item.id for item in tasks]
        pending_by_task: dict[UUID, int] = {}
        if task_ids:
            for approval in self.session.scalars(
                select(ApprovalRequest).where(
                    ApprovalRequest.task_id.in_(task_ids),
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                )
            ):
                pending_by_task[approval.task_id] = pending_by_task.get(approval.task_id, 0) + 1
        runs = list(
            self.session.scalars(
                select(SupervisorRun)
                .where(SupervisorRun.command_id.in_(command_ids))
                .order_by(SupervisorRun.created_at.desc(), SupervisorRun.id.desc())
            )
        )
        latest_run_by_command: dict[UUID, SupervisorRun] = {}
        for run in runs:
            latest_run_by_command.setdefault(run.command_id, run)

        result: list[ConversationOperationRead] = []
        for command in commands:
            plan = plans_by_command.get(command.id)
            plan_tasks = tasks_by_plan.get(plan.id, []) if plan else []
            task_counts: dict[str, int] = {}
            for task in plan_tasks:
                task_counts[task.status.value] = task_counts.get(task.status.value, 0) + 1
            run = latest_run_by_command.get(command.id)
            latest_error = next(
                (item.error_message for item in reversed(plan_tasks) if item.error_message),
                run.error_message if run else None,
            )
            result.append(
                ConversationOperationRead(
                    command=CommandRead.model_validate(command),
                    plan=(
                        ConversationPlanRead(
                            id=plan.id,
                            title=plan.title,
                            objective=plan.objective,
                            status=plan.status,
                        )
                        if plan
                        else None
                    ),
                    supervisor_status=run.status if run else None,
                    task_counts=task_counts,
                    pending_approvals=sum(pending_by_task.get(item.id, 0) for item in plan_tasks),
                    latest_error=latest_error,
                )
            )
        return result

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
