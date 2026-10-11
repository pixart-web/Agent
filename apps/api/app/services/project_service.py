from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.client_management import CrmClient
from app.models.knowledge import WorkspaceMember
from app.models.project import (
    Project,
    ProjectActivity,
    ProjectCommand,
    ProjectMember,
    ProjectMilestone,
    ProjectTask,
)
from app.repositories.command_repository import CommandRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMilestoneCreate,
    ProjectMilestoneUpdate,
    ProjectUpdate,
)
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError
from app.workspaces.scope import active_workspace_id


@dataclass(frozen=True)
class ProjectDetailData:
    project: Project
    counts: tuple[int, int]
    members: list
    milestones: list
    tasks: list
    commands: list
    activity: list


class ProjectService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.tasks = TaskRepository(session)
        self.commands = CommandRepository(session)

    def _project(self, project_id: UUID, user_id: UUID, *, lock: bool = False) -> Project:
        project = self.projects.get_owned(project_id, user_id, lock=lock)
        if project is None:
            raise WorkflowNotFoundError("Project not found")
        return project

    def _client(self, client_id: UUID | None, user_id: UUID) -> None:
        if client_id is None:
            return
        client = self.session.scalar(
            select(CrmClient).where(
                CrmClient.id == client_id,
                CrmClient.workspace_id == active_workspace_id(user_id),
            )
        )
        if client is None:
            raise WorkflowNotFoundError("Client not found")

    def _activity(self, project: Project, user_id: UUID, event: str, description: str) -> None:
        self.projects.add(
            ProjectActivity(
                project_id=project.id,
                actor_user_id=user_id,
                event_type=event,
                description=description,
            )
        )

    def create(self, user_id: UUID, data: ProjectCreate) -> Project:
        try:
            self._client(data.client_id, user_id)
            workspace_id = self.session.scalar(select(active_workspace_id(user_id)))
            if workspace_id is None:
                raise WorkflowConflictError("Select an active workspace first")
            project = Project(
                workspace_id=workspace_id,
                owner_user_id=user_id,
                **data.model_dump(),
            )
            self.projects.add(project)
            self.session.flush()
            self.projects.add(ProjectMember(project_id=project.id, user_id=user_id, role="owner"))
            self._activity(project, user_id, "project.created", f"Created project {project.name}")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(project)
        return project

    def list(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        status: str | None,
        client_id: UUID | None,
        search: str | None,
    ):
        projects = self.projects.list_owned(user_id, limit, offset, status, client_id, search)
        return projects, self.projects.progress([project.id for project in projects])

    def detail(self, project_id: UUID, user_id: UUID) -> ProjectDetailData:
        project = self._project(project_id, user_id)
        counts = self.projects.progress([project.id]).get(project.id, (0, 0))
        return ProjectDetailData(
            project,
            counts,
            self.projects.members(project.id),
            self.projects.milestones(project.id),
            self.projects.tasks(project.id),
            self.projects.commands(project.id),
            self.projects.activity(project.id),
        )

    def update(self, project_id: UUID, user_id: UUID, data: ProjectUpdate) -> Project:
        try:
            project = self._project(project_id, user_id, lock=True)
            values = data.model_dump(exclude_unset=True)
            if "client_id" in values:
                self._client(values["client_id"], user_id)
            starts_on = values.get("starts_on", project.starts_on)
            due_on = values.get("due_on", project.due_on)
            if starts_on and due_on and due_on < starts_on:
                raise WorkflowConflictError("due_on cannot be before starts_on")
            for field, value in values.items():
                setattr(project, field, value)
            self._activity(project, user_id, "project.updated", "Updated project details")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(project)
        return project

    def add_member(self, project_id: UUID, user_id: UUID, data: ProjectMemberCreate) -> None:
        try:
            project = self._project(project_id, user_id)
            membership = self.session.scalar(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == project.workspace_id,
                    WorkspaceMember.user_id == data.user_id,
                )
            )
            if membership is None:
                raise WorkflowNotFoundError("Workspace member not found")
            self.projects.add(ProjectMember(project_id=project.id, **data.model_dump()))
            self._activity(project, user_id, "member.added", f"Added project member {data.user_id}")
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError("User is already a project member") from error
        except Exception:
            self.session.rollback()
            raise

    def remove_member(self, project_id: UUID, member_id: UUID, user_id: UUID) -> None:
        try:
            project = self._project(project_id, user_id)
            member = self.session.scalar(
                select(ProjectMember).where(
                    ProjectMember.id == member_id,
                    ProjectMember.project_id == project.id,
                )
            )
            if member is None:
                raise WorkflowNotFoundError("Project member not found")
            if member.user_id == project.owner_user_id:
                raise WorkflowConflictError("The project owner cannot be removed")
            self.session.delete(member)
            self._activity(
                project, user_id, "member.removed", f"Removed project member {member.user_id}"
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def add_milestone(
        self, project_id: UUID, user_id: UUID, data: ProjectMilestoneCreate
    ) -> ProjectMilestone:
        try:
            project = self._project(project_id, user_id)
            milestone = ProjectMilestone(project_id=project.id, **data.model_dump())
            self.projects.add(milestone)
            self._activity(project, user_id, "milestone.created", f"Created milestone {data.title}")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(milestone)
        return milestone

    def update_milestone(
        self, project_id: UUID, milestone_id: UUID, user_id: UUID, data: ProjectMilestoneUpdate
    ) -> ProjectMilestone:
        try:
            project = self._project(project_id, user_id)
            milestone = self.projects.milestone(project.id, milestone_id)
            if milestone is None:
                raise WorkflowNotFoundError("Milestone not found")
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(milestone, field, value)
            self._activity(
                project, user_id, "milestone.updated", f"Updated milestone {milestone.title}"
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(milestone)
        return milestone

    def link(self, project_id: UUID, resource_id: UUID, user_id: UUID, kind: str) -> None:
        try:
            project = self._project(project_id, user_id)
            if kind == "task":
                if self.tasks.get_owned(resource_id, user_id) is None:
                    raise WorkflowNotFoundError("Task not found")
                model = ProjectTask
            else:
                if self.commands.get_owned(resource_id, user_id) is None:
                    raise WorkflowNotFoundError("Command not found")
                model = ProjectCommand
            self.projects.link(model, project.id, resource_id)
            self._activity(project, user_id, f"{kind}.linked", f"Linked {kind} {resource_id}")
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError(f"{kind.title()} is already linked") from error
        except Exception:
            self.session.rollback()
            raise

    def unlink(self, project_id: UUID, resource_id: UUID, user_id: UUID, kind: str) -> None:
        try:
            project = self._project(project_id, user_id)
            model = ProjectTask if kind == "task" else ProjectCommand
            if not self.projects.unlink(model, project.id, resource_id):
                raise WorkflowNotFoundError(f"Linked {kind} not found")
            self._activity(project, user_id, f"{kind}.unlinked", f"Unlinked {kind} {resource_id}")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
