from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.crm.client_schemas import (
    Client360Output,
    ClientCreateInput,
    ClientInput,
    ClientListInput,
    ClientOutput,
    ClientsOutput,
    ClientUpdateInput,
    OpportunitiesOutput,
    OpportunityCreateInput,
    OpportunityListInput,
    OpportunityOutput,
    OpportunityUpdateInput,
    PipelineCreateInput,
    PipelineListInput,
    PipelineOutput,
    PipelinesOutput,
    ProjectListInput,
    ProjectsOutput,
)
from app.crm.client_service import ClientManagementService
from app.crm.errors import CrmConflictError, CrmNotFoundError, CrmValidationError
from app.db.session import get_db
from app.execution.context import ExecutionContext
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.knowledge import WorkspaceMember
from app.models.user import User

router = APIRouter(prefix="/crm", tags=["crm"])


def _context(user_id: UUID) -> ExecutionContext:
    identifier = uuid4()
    return ExecutionContext(
        user_id=user_id,
        command_id=identifier,
        task_id=identifier,
        action_id=identifier,
        execution_id=identifier,
        correlation_id=identifier,
        credentials=EnvironmentCredentialProvider(),
    )


def _service(db: Session) -> ClientManagementService:
    return ClientManagementService(sessionmaker(bind=db.get_bind(), expire_on_commit=False))


def _require_editor(db: Session, user: User) -> None:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace edit permission is required")


def _raise_crm(error: Exception) -> None:
    if isinstance(error, CrmNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, CrmConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, CrmValidationError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


@router.post("/clients", response_model=ClientOutput, status_code=status.HTTP_201_CREATED)
def create_client(
    value: ClientCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ClientOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_client(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.patch("/clients/{client_id}", response_model=ClientOutput)
def update_client(
    client_id: UUID,
    value: ClientUpdateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ClientOutput:
    _require_editor(db, user)
    if value.client_id != client_id:
        raise HTTPException(status_code=422, detail="Client id does not match path")
    try:
        return _service(db).update_client(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.post("/pipelines", response_model=PipelineOutput, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    value: PipelineCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PipelineOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_pipeline(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.post(
    "/opportunities", response_model=OpportunityOutput, status_code=status.HTTP_201_CREATED
)
def create_opportunity(
    value: OpportunityCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OpportunityOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_opportunity(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityOutput)
def update_opportunity(
    opportunity_id: UUID,
    value: OpportunityUpdateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OpportunityOutput:
    _require_editor(db, user)
    if value.opportunity_id != opportunity_id:
        raise HTTPException(status_code=422, detail="Opportunity id does not match path")
    try:
        return _service(db).update_opportunity(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.get("/clients", response_model=ClientsOutput)
def list_clients(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    query: str | None = Query(default=None, min_length=1, max_length=255),
    client_status: Literal["prospect", "active", "paused", "former", "archived"] | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> ClientsOutput:
    return _service(db).list_clients(
        _context(user.id),
        ClientListInput(
            query=query,
            status=client_status,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/clients/{client_id}/360", response_model=Client360Output)
def get_client_360(
    client_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Client360Output:
    return _service(db).get_client_360(_context(user.id), ClientInput(client_id=client_id))


@router.get("/clients/{client_id}/projects", response_model=ProjectsOutput)
def list_projects(
    client_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    project_status: Literal["planned", "active", "blocked", "completed", "cancelled"]
    | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> ProjectsOutput:
    return _service(db).list_projects(
        _context(user.id),
        ProjectListInput(
            client_id=client_id,
            status=project_status,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/pipelines", response_model=PipelinesOutput)
def list_pipelines(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> PipelinesOutput:
    return _service(db).list_pipelines(
        _context(user.id),
        PipelineListInput(limit=limit, offset=offset),
    )


@router.get(
    "/clients/{client_id}/opportunities",
    response_model=OpportunitiesOutput,
)
def list_opportunities(
    client_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    opportunity_status: Literal["open", "won", "lost", "cancelled"] | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> OpportunitiesOutput:
    return _service(db).list_opportunities(
        _context(user.id),
        OpportunityListInput(
            client_id=client_id,
            status=opportunity_status,
            limit=limit,
            offset=offset,
        ),
    )
