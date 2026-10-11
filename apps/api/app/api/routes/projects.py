from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import (
    ProjectActivityRead,
    ProjectCommandRead,
    ProjectCreate,
    ProjectDetail,
    ProjectMemberCreate,
    ProjectMemberRead,
    ProjectMilestoneCreate,
    ProjectMilestoneRead,
    ProjectMilestoneUpdate,
    ProjectRead,
    ProjectResourceLink,
    ProjectStatus,
    ProjectTaskRead,
    ProjectUpdate,
)
from app.services.project_service import ProjectDetailData, ProjectService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_read(project, counts: tuple[int, int] = (0, 0)) -> ProjectRead:
    total, completed = counts
    return ProjectRead(
        **ProjectRead.model_validate(project).model_dump(
            exclude={"task_count", "completed_task_count", "progress_percentage"}
        ),
        task_count=total,
        completed_task_count=completed,
        progress_percentage=round(completed * 100 / total) if total else 0,
    )


def _detail(data: ProjectDetailData) -> ProjectDetail:
    return ProjectDetail(
        **_project_read(data.project, data.counts).model_dump(),
        members=[
            ProjectMemberRead(
                id=member.id,
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=member.role,
                created_at=member.created_at,
            )
            for member, user in data.members
        ],
        milestones=[ProjectMilestoneRead.model_validate(item) for item in data.milestones],
        tasks=[ProjectTaskRead.model_validate(item) for item in data.tasks],
        commands=[ProjectCommandRead.model_validate(item) for item in data.commands],
        activity=[ProjectActivityRead.model_validate(item) for item in data.activity],
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    client_id: UUID | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> list[ProjectRead]:
    projects, progress = ProjectService(db).list(
        user.id, limit, offset, project_status, client_id, search.strip() if search else None
    )
    return [_project_read(project, progress.get(project.id, (0, 0))) for project in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectRead:
    try:
        return _project_read(ProjectService(db).create(user.id, data))
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectDetail:
    try:
        return _detail(ProjectService(db).detail(project_id, user.id))
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectRead:
    try:
        return _project_read(ProjectService(db).update(project_id, user.id, data))
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)


@router.post("/{project_id}/members", status_code=status.HTTP_204_NO_CONTENT)
def add_member(
    project_id: UUID,
    data: ProjectMemberCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        ProjectService(db).add_member(project_id, user.id, data)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: UUID,
    member_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        ProjectService(db).remove_member(project_id, member_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/milestones",
    response_model=ProjectMilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
def add_milestone(
    project_id: UUID,
    data: ProjectMilestoneCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectMilestoneRead:
    try:
        return ProjectMilestoneRead.model_validate(
            ProjectService(db).add_milestone(project_id, user.id, data)
        )
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=ProjectMilestoneRead)
def update_milestone(
    project_id: UUID,
    milestone_id: UUID,
    data: ProjectMilestoneUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectMilestoneRead:
    try:
        return ProjectMilestoneRead.model_validate(
            ProjectService(db).update_milestone(project_id, milestone_id, user.id, data)
        )
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)


def _link(
    project_id: UUID, data: ProjectResourceLink, user: User, db: Session, kind: str
) -> Response:
    try:
        ProjectService(db).link(project_id, data.resource_id, user.id, kind)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/tasks", status_code=status.HTTP_204_NO_CONTENT)
def link_task(
    project_id: UUID,
    data: ProjectResourceLink,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    return _link(project_id, data, user, db, "task")


@router.post("/{project_id}/commands", status_code=status.HTTP_204_NO_CONTENT)
def link_command(
    project_id: UUID,
    data: ProjectResourceLink,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    return _link(project_id, data, user, db, "command")


def _unlink(project_id: UUID, resource_id: UUID, user: User, db: Session, kind: str) -> Response:
    try:
        ProjectService(db).unlink(project_id, resource_id, user.id, kind)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_task(
    project_id: UUID,
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    return _unlink(project_id, task_id, user, db, "task")


@router.delete("/{project_id}/commands/{command_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_command(
    project_id: UUID,
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    return _unlink(project_id, command_id, user, db, "command")
