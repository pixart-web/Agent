from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user, get_current_superuser
from app.api.dependencies.origin import require_allowed_origin
from app.db.session import get_db
from app.models.user import User
from app.pixart_apps.schemas import (
    PixartApplicationCreate,
    PixartApplicationRead,
    PixartApplicationUpdate,
)
from app.pixart_apps.service import (
    HealthChecksDisabledError,
    PixartAppConflictError,
    PixartAppContractError,
    PixartAppService,
    UnsafeHealthTargetError,
)

router = APIRouter(tags=["pixart-apps"])


@router.get("/pixart-apps", response_model=list[PixartApplicationRead])
def list_pixart_apps(
    _user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PixartApplicationRead]:
    return [PixartApplicationRead.model_validate(app) for app in PixartAppService(db).list()]


@router.post(
    "/platform-admin/pixart-apps",
    response_model=PixartApplicationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_allowed_origin)],
)
def register_pixart_app(
    data: PixartApplicationCreate,
    user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PixartApplicationRead:
    try:
        app = PixartAppService(db).create(data, user.id)
    except PixartAppConflictError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="A Pixart product with this key already exists"
        ) from error
    return PixartApplicationRead.model_validate(app)


@router.patch(
    "/platform-admin/pixart-apps/{app_id}",
    response_model=PixartApplicationRead,
    dependencies=[Depends(require_allowed_origin)],
)
def update_pixart_app(
    app_id: UUID,
    data: PixartApplicationUpdate,
    user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PixartApplicationRead:
    try:
        app = PixartAppService(db).update(app_id, data, user.id)
    except LookupError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pixart product not found") from error
    except PixartAppContractError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Record the API address, version and documentation before marking it available",
        ) from error
    return PixartApplicationRead.model_validate(app)


@router.post(
    "/platform-admin/pixart-apps/{app_id}/health",
    response_model=PixartApplicationRead,
    dependencies=[Depends(require_allowed_origin)],
)
def check_pixart_app_health(
    app_id: UUID,
    user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PixartApplicationRead:
    try:
        app = PixartAppService(db).check_health(app_id, user.id)
    except LookupError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pixart product not found") from error
    except HealthChecksDisabledError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Health checks of Pixart products are disabled"
        ) from error
    except UnsafeHealthTargetError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return PixartApplicationRead.model_validate(app)
