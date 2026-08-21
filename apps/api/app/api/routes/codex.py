from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.workflow_enums import CodexRunStatus
from app.repositories.codex_run_repository import CodexRunRepository
from app.schemas.codex import CodexRunRead

router = APIRouter(prefix="/codex/runs", tags=["codex"])


@router.get("", response_model=list[CodexRunRead])
def list_codex_runs(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    run_status: Annotated[CodexRunStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CodexRunRead]:
    runs = CodexRunRepository(db).list_owned(
        user.id,
        status=run_status,
        limit=limit,
        offset=offset,
    )
    return [CodexRunRead.model_validate(run) for run in runs]


@router.get("/{run_id}", response_model=CodexRunRead)
def get_codex_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CodexRunRead:
    run = CodexRunRepository(db).get_owned(run_id, user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codex run not found")
    return CodexRunRead.model_validate(run)
