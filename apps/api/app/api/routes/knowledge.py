from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.knowledge.errors import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
    KnowledgePermissionError,
)
from app.knowledge.schemas import (
    KnowledgeCreate,
    KnowledgeList,
    KnowledgeRead,
    KnowledgeSearch,
    KnowledgeSearchResult,
    KnowledgeUpdate,
    MemberAdd,
    MemberList,
    MemberRead,
    WorkspaceCreate,
    WorkspaceList,
    WorkspaceRead,
)
from app.knowledge.service import KnowledgeService
from app.models.user import User

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _service(db: Session) -> KnowledgeService:
    return KnowledgeService(sessionmaker(bind=db.get_bind(), expire_on_commit=False))


def _raise(error: Exception) -> None:
    if isinstance(error, KnowledgeNotFoundError):
        raise HTTPException(status_code=404, detail="Resource not found") from error
    if isinstance(error, KnowledgePermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    if isinstance(error, KnowledgeConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise error


@router.post("/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    value: WorkspaceCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceRead:
    try:
        return _service(db).create_workspace(user.id, value)
    except KnowledgeConflictError as error:
        _raise(error)


@router.get("/workspaces", response_model=WorkspaceList)
def list_workspaces(
    user: Annotated[User, Depends(get_current_active_user)], db: Annotated[Session, Depends(get_db)]
) -> WorkspaceList:
    return _service(db).list_workspaces(user.id)


@router.get("/workspaces/{workspace_id}/members", response_model=MemberList)
def list_members(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MemberList:
    try:
        return _service(db).list_members(user.id, workspace_id)
    except KnowledgeNotFoundError as error:
        _raise(error)


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    workspace_id: UUID,
    value: MemberAdd,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    try:
        return _service(db).add_member(user.id, workspace_id, value)
    except (KnowledgeNotFoundError, KnowledgePermissionError, KnowledgeConflictError) as error:
        _raise(error)


@router.post(
    "/workspaces/{workspace_id}/items",
    response_model=KnowledgeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    workspace_id: UUID,
    value: KnowledgeCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeRead:
    try:
        return _service(db).create_item(user.id, workspace_id, value)
    except (KnowledgeNotFoundError, KnowledgePermissionError) as error:
        _raise(error)


@router.get("/workspaces/{workspace_id}/items", response_model=KnowledgeList)
def list_items(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    include_drafts: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> KnowledgeList:
    try:
        return _service(db).list_items(
            user.id, workspace_id, include_drafts=include_drafts, limit=limit, offset=offset
        )
    except KnowledgeNotFoundError as error:
        _raise(error)


@router.patch("/workspaces/{workspace_id}/items/{item_id}", response_model=KnowledgeRead)
def update_item(
    workspace_id: UUID,
    item_id: UUID,
    value: KnowledgeUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeRead:
    try:
        return _service(db).update_item(user.id, workspace_id, item_id, value)
    except (KnowledgeNotFoundError, KnowledgePermissionError, KnowledgeConflictError) as error:
        _raise(error)


@router.post("/workspaces/{workspace_id}/items/{item_id}/approve", response_model=KnowledgeRead)
def approve_item(
    workspace_id: UUID,
    item_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeRead:
    try:
        return _service(db).approve_item(user.id, workspace_id, item_id)
    except (KnowledgeNotFoundError, KnowledgePermissionError, KnowledgeConflictError) as error:
        _raise(error)


@router.post("/workspaces/{workspace_id}/search", response_model=KnowledgeSearchResult)
def search_knowledge(
    workspace_id: UUID,
    value: KnowledgeSearch,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeSearchResult:
    try:
        return _service(db).search(user.id, workspace_id, value)
    except KnowledgeNotFoundError as error:
        _raise(error)
