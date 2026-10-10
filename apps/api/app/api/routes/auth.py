from contextlib import suppress
from typing import Annotated
from uuid import UUID

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
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    MessageResponse,
    SessionRead,
)
from app.schemas.user import (
    EmailRequest,
    PasswordResetConfirm,
    TokenRequest,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.services.auth_service import (
    AccountTokenRateLimitedError,
    AuthResult,
    AuthService,
    EmailVerificationRequiredError,
    InvalidAccountTokenError,
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
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(require_allowed_origin),
        Depends(auth_rate_limit("register")),
    ],
)
def register(
    data: UserCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    user_agent, ip_address = _request_context(request)
    AuthService(db).register(data, user_agent, ip_address)
    return MessageResponse(message="If the address is eligible, a verification email was queued")


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
    except EmailVerificationRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
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


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    dependencies=[Depends(require_allowed_origin), Depends(auth_rate_limit("verify-email"))],
)
def verify_email(
    data: TokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    try:
        AuthService(db).verify_email(data.token)
    except InvalidAccountTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        ) from error
    return MessageResponse(message="Email verified")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    dependencies=[Depends(require_allowed_origin), Depends(auth_rate_limit("resend-verification"))],
)
def resend_verification(
    data: EmailRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    with suppress(AccountTokenRateLimitedError):
        AuthService(db).resend_verification(str(data.email))
    return MessageResponse(message="If the account is eligible, a verification email was queued")


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    dependencies=[Depends(require_allowed_origin), Depends(auth_rate_limit("password-reset"))],
)
def request_password_reset(
    data: EmailRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    with suppress(AccountTokenRateLimitedError):
        AuthService(db).request_password_reset(str(data.email))
    return MessageResponse(message="If the account is eligible, a password reset email was queued")


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    dependencies=[
        Depends(require_allowed_origin),
        Depends(auth_rate_limit("password-reset-confirm")),
    ],
)
def confirm_password_reset(
    data: PasswordResetConfirm,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    try:
        AuthService(db).reset_password(data.token, data.password)
    except InvalidAccountTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        ) from error
    return MessageResponse(message="Password reset completed")


@router.get("/me", response_model=UserPublic)
def me(
    user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    return UserPublic.model_validate(user)


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_active_user)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> list[SessionRead]:
    sessions = AuthService(db).list_sessions(user.id, refresh_token)
    return [
        SessionRead(
            id=item.id,
            created_at=item.created_at,
            expires_at=item.expires_at,
            user_agent=item.user_agent,
            ip_address=item.ip_address,
            current=bool(getattr(item, "is_current", False)),
        )
        for item in sessions
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def revoke_session(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_active_user)],
) -> Response:
    if not AuthService(db).revoke_session(user.id, session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def revoke_all_sessions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_active_user)],
) -> Response:
    AuthService(db).revoke_all_sessions(user.id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(response)
    return response
