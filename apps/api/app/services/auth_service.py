from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.security.access_tokens import create_access_token
from app.security.email import normalize_email
from app.security.passwords import hash_password, verify_password_or_dummy
from app.security.refresh_tokens import generate_refresh_token, hash_refresh_token


class DuplicateEmailError(Exception):
    """Raised when registration uses an existing email."""


class InvalidCredentialsError(Exception):
    """Raised for every invalid login combination."""


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token cannot be accepted."""


@dataclass(frozen=True)
class AuthResult:
    user: User
    access_token: str
    refresh_token: str


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.settings = get_settings()

    def _build_refresh_token(
        self,
        user_id: UUID,
        user_agent: str | None,
        ip_address: str | None,
        family_id: UUID | None = None,
    ) -> tuple[str, RefreshToken]:
        raw_token = generate_refresh_token()
        token = RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_token),
            family_id=family_id or uuid4(),
            expires_at=utc_now() + timedelta(days=self.settings.refresh_token_expire_days),
            user_agent=user_agent[:1000] if user_agent else None,
            ip_address=ip_address[:64] if ip_address else None,
        )
        return raw_token, token

    def register(
        self,
        data: UserCreate,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        normalized_email = normalize_email(str(data.email))
        if self.users.get_by_email(normalized_email) is not None:
            raise DuplicateEmailError

        try:
            user = User(
                email=normalized_email,
                password_hash=hash_password(data.password),
                full_name=data.full_name,
            )
            self.users.add(user)
            self.session.flush()
            raw_refresh, refresh = self._build_refresh_token(
                user.id,
                user_agent,
                ip_address,
            )
            self.refresh_tokens.add(refresh)
            self.session.commit()
            self.session.refresh(user)
        except IntegrityError as error:
            self.session.rollback()
            raise DuplicateEmailError from error
        except Exception:
            self.session.rollback()
            raise

        return AuthResult(
            user=user,
            access_token=create_access_token(user.id),
            refresh_token=raw_refresh,
        )

    def login(
        self,
        email: str,
        password: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        user = self.users.get_by_email(normalize_email(email))
        password_hash = user.password_hash if user is not None else None
        if not verify_password_or_dummy(password, password_hash):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InvalidCredentialsError

        try:
            user.last_login_at = utc_now()
            raw_refresh, refresh = self._build_refresh_token(
                user.id,
                user_agent,
                ip_address,
            )
            self.refresh_tokens.add(refresh)
            self.session.commit()
            self.session.refresh(user)
        except Exception:
            self.session.rollback()
            raise

        return AuthResult(
            user=user,
            access_token=create_access_token(user.id),
            refresh_token=raw_refresh,
        )

    def refresh(
        self,
        raw_token: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        token = self.refresh_tokens.get_by_hash_for_update(hash_refresh_token(raw_token))
        if token is None:
            self.session.rollback()
            raise InvalidRefreshTokenError

        now = utc_now()
        if token.revoked_at is not None:
            self.refresh_tokens.revoke_family(token.family_id, now)
            self.session.commit()
            raise InvalidRefreshTokenError

        if _as_utc(token.expires_at) <= now:
            token.revoked_at = now
            self.session.commit()
            raise InvalidRefreshTokenError

        user = self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            self.refresh_tokens.revoke_family(token.family_id, now)
            self.session.commit()
            raise InvalidRefreshTokenError

        try:
            raw_refresh, replacement = self._build_refresh_token(
                user.id,
                user_agent,
                ip_address,
                family_id=token.family_id,
            )
            self.refresh_tokens.add(replacement)
            self.session.flush()
            token.revoked_at = now
            token.replaced_by_id = replacement.id
            self.session.commit()
            self.session.refresh(user)
        except Exception:
            self.session.rollback()
            raise

        return AuthResult(
            user=user,
            access_token=create_access_token(user.id),
            refresh_token=raw_refresh,
        )

    def logout(self, raw_token: str | None) -> None:
        if raw_token is None:
            return

        token = self.refresh_tokens.get_by_hash_for_update(hash_refresh_token(raw_token))
        if token is not None and token.revoked_at is None:
            token.revoked_at = utc_now()
            self.session.commit()
        else:
            self.session.rollback()
