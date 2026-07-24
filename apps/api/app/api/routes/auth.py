from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.auth_cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.origin import require_allowed_origin
from app.api.dependencies.rate_limit import auth_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, AuthResponse
from app.schemas.user import UserCreate, UserLogin, UserPublic
from app.services.auth_service import (
    AuthResult,
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _request_context(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


def _auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        access_token=result.access_token,
        user=UserPublic.model_validate(result.user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_allowed_origin),
        Depends(auth_rate_limit("register")),
    ],
)
def register(
    data: UserCreate,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    user_agent, ip_address = _request_context(request)
    try:
        result = AuthService(db).register(data, user_agent, ip_address)
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from error

    set_refresh_cookie(response, result.refresh_token)
    return _auth_response(result)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[
        Depends(require_allowed_origin),
        Depends(auth_rate_limit("login")),
    ],
)
def login(
    data: UserLogin,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    user_agent, ip_address = _request_context(request)
    try:
        result = AuthService(db).login(
            str(data.email),
            data.password,
            user_agent,
            ip_address,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    set_refresh_cookie(response, result.refresh_token)
    return _auth_response(result)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    dependencies=[
        Depends(require_allowed_origin),
        Depends(auth_rate_limit("refresh")),
    ],
)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_COOKIE_NAME),
    ] = None,
) -> AccessTokenResponse | JSONResponse:
    if refresh_token is None:
        return _invalid_refresh_response()

    user_agent, ip_address = _request_context(request)
    try:
        result = AuthService(db).refresh(refresh_token, user_agent, ip_address)
    except InvalidRefreshTokenError:
        return _invalid_refresh_response()

    set_refresh_cookie(response, result.refresh_token)
    return AccessTokenResponse(access_token=result.access_token)


def _invalid_refresh_response() -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid refresh token"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    clear_refresh_cookie(response)
    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def logout(
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_COOKIE_NAME),
    ] = None,
) -> Response:
    AuthService(db).logout(refresh_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(response)
    return response


@router.get("/me", response_model=UserPublic)
def me(
    user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    return UserPublic.model_validate(user)
