from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.project import (
    Project,
    ProjectActivity,
    ProjectCommand,
    ProjectMember,
    ProjectMilestone,
    ProjectTask,
)
from app.models.task import Task
from app.models.user import User
from app.workspaces.scope import active_workspace_id


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, value: object) -> None:
        self.session.add(value)

    def get_owned(self, project_id: UUID, user_id: UUID, *, lock: bool = False) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id,
            Project.workspace_id == active_workspace_id(user_id),
        )
        if lock:
            statement = statement.with_for_update(of=Project)
        return self.session.scalar(statement)

    def list_owned(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        status: str | None,
        client_id: UUID | None,
        search: str | None,
    ) -> list[Project]:
        statement = select(Project).where(Project.workspace_id == active_workspace_id(user_id))
        if status:
            statement = statement.where(Project.status == status)
        if client_id:
            statement = statement.where(Project.client_id == client_id)
        if search:
            statement = statement.where(
                or_(
                    Project.name.icontains(search, autoescape=True),
                    Project.description.icontains(search, autoescape=True),
                )
            )
        return list(
            self.session.scalars(
                statement.order_by(Project.updated_at.desc(), Project.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def progress(self, project_ids: list[UUID]) -> dict[UUID, tuple[int, int]]:
        if not project_ids:
            return {}
        statement = (
            select(
                ProjectTask.project_id,
                func.count(Task.id),
                func.sum(case((Task.status == "completed", 1), else_=0)),
            )
            .join(Task, Task.id == ProjectTask.task_id)
            .where(ProjectTask.project_id.in_(project_ids))
            .group_by(ProjectTask.project_id)
        )
        return {row[0]: (int(row[1]), int(row[2] or 0)) for row in self.session.execute(statement)}

    def members(self, project_id: UUID) -> list[tuple[ProjectMember, User]]:
        rows = self.session.execute(
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at, ProjectMember.id)
        )
        return [(row[0], row[1]) for row in rows]

    def milestones(self, project_id: UUID) -> list[ProjectMilestone]:
        return list(
            self.session.scalars(
                select(ProjectMilestone)
                .where(ProjectMilestone.project_id == project_id)
                .order_by(ProjectMilestone.due_on, ProjectMilestone.created_at)
            )
        )

    def tasks(self, project_id: UUID) -> list[Task]:
        return list(
            self.session.scalars(
                select(Task)
                .join(ProjectTask, ProjectTask.task_id == Task.id)
                .where(ProjectTask.project_id == project_id)
                .order_by(Task.created_at.desc())
            )
        )

    def commands(self, project_id: UUID) -> list[Command]:
        return list(
            self.session.scalars(
                select(Command)
                .join(ProjectCommand, ProjectCommand.command_id == Command.id)
                .where(ProjectCommand.project_id == project_id)
                .order_by(Command.created_at.desc())
            )
        )

    def activity(self, project_id: UUID) -> list[ProjectActivity]:
        return list(
            self.session.scalars(
                select(ProjectActivity)
                .where(ProjectActivity.project_id == project_id)
                .order_by(ProjectActivity.created_at.desc(), ProjectActivity.id.desc())
                .limit(100)
            )
        )

    def milestone(self, project_id: UUID, milestone_id: UUID) -> ProjectMilestone | None:
        return self.session.scalar(
            select(ProjectMilestone).where(
                ProjectMilestone.id == milestone_id,
                ProjectMilestone.project_id == project_id,
            )
        )

    def link(
        self, model: type[ProjectTask] | type[ProjectCommand], project_id: UUID, resource_id: UUID
    ) -> None:
        field = "task_id" if model is ProjectTask else "command_id"
        self.add(model(project_id=project_id, **{field: resource_id}))

    def unlink(
        self, model: type[ProjectTask] | type[ProjectCommand], project_id: UUID, resource_id: UUID
    ) -> bool:
        field = ProjectTask.task_id if model is ProjectTask else ProjectCommand.command_id
        value = self.session.scalar(
            select(model).where(model.project_id == project_id, field == resource_id)
        )
        if value is None:
            return False
        self.session.delete(value)
        return True
