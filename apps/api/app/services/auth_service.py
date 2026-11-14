from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.commercial.service import provision_trial
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.account_token import AccountToken
from app.models.knowledge import Workspace, WorkspaceMember
from app.models.refresh_token import RefreshToken
from app.models.transactional_email import TransactionalEmailOutbox
from app.models.user import User
from app.repositories.account_token_repository import AccountTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.transactional_email_repository import TransactionalEmailRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.security.access_tokens import create_access_token
from app.security.account_tokens import (
    encrypt_email_payload,
    generate_account_token,
    hash_account_token,
)
from app.security.email import normalize_email
from app.security.passwords import hash_password, verify_password_or_dummy
from app.security.refresh_tokens import generate_refresh_token, hash_refresh_token


class InvalidCredentialsError(Exception):
    """Raised for every invalid login combination."""


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token cannot be accepted."""


class EmailVerificationRequiredError(Exception):
    """Raised after valid credentials are supplied for an unverified account."""


class InvalidAccountTokenError(Exception):
    """Raised when a verification or recovery token is unusable."""


class AccountTokenRateLimitedError(Exception):
    """Raised when a token is requested inside the resend cooldown."""


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
        self.account_tokens = AccountTokenRepository(session)
        self.transactional_email = TransactionalEmailRepository(session)
        self.settings = get_settings()

    def _queue_account_token(self, user: User, purpose: str) -> str:
        now = utc_now()
        raw_token = generate_account_token()
        expiry_minutes = (
            self.settings.email_verification_expire_minutes
            if purpose == "email_verification"
            else self.settings.password_reset_expire_minutes
        )
        self.account_tokens.consume_active(user.id, purpose, now)
        self.account_tokens.add(
            AccountToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=hash_account_token(raw_token),
                expires_at=now + timedelta(minutes=expiry_minutes),
            )
        )
        self.transactional_email.add(
            TransactionalEmailOutbox(
                user_id=user.id,
                recipient=user.email,
                template=purpose,
                encrypted_payload=encrypt_email_payload(
                    {"token": raw_token, "full_name": user.full_name},
                    self.settings.auth_secret_key,
                ),
                available_at=now,
            )
        )
        return raw_token

    def _enforce_resend_cooldown(self, user: User, purpose: str) -> None:
        latest = self.account_tokens.latest_for_user(user.id, purpose)
        if latest is None:
            return
        elapsed = utc_now() - _as_utc(latest.created_at)
        if elapsed < timedelta(seconds=self.settings.account_token_resend_cooldown_seconds):
            raise AccountTokenRateLimitedError

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
    ) -> User | None:
        normalized_email = normalize_email(str(data.email))
        if self.users.get_by_email(normalized_email) is not None:
            return None

        try:
            user = User(
                email=normalized_email,
                password_hash=hash_password(data.password),
                full_name=data.full_name,
                terms_accepted_at=utc_now(),
                privacy_accepted_at=utc_now(),
                terms_version=self.settings.legal_terms_version,
                privacy_version=self.settings.legal_privacy_version,
                email_verified_at=(
                    None if self.settings.auth_require_email_verification else utc_now()
                ),
            )
            self.users.add(user)
            self.session.flush()
            workspace = Workspace(
                name=f"{user.full_name}'s Workspace",
                slug=f"personal-{user.id.hex}",
                created_by_user_id=user.id,
            )
            self.session.add(workspace)
            self.session.flush()
            self.session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role="owner",
                    created_by_user_id=user.id,
                )
            )
            provision_trial(self.session, workspace.id)
            user.active_workspace_id = workspace.id
            if self.settings.auth_require_email_verification:
                self._queue_account_token(user, "email_verification")
            self.session.commit()
            self.session.refresh(user)
        except IntegrityError:
            self.session.rollback()
            return None
        except Exception:
            self.session.rollback()
            raise

        return user

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
        if user.email_verified_at is None:
            raise EmailVerificationRequiredError

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

    def resend_verification(self, email: str) -> None:
        user = self.users.get_by_email(normalize_email(email))
        if user is None or user.email_verified_at is not None or not user.is_active:
            return
        self._enforce_resend_cooldown(user, "email_verification")
        try:
            self._queue_account_token(user, "email_verification")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def verify_email(self, raw_token: str) -> User:
        token = self.account_tokens.get_by_hash_for_update(
            hash_account_token(raw_token), "email_verification"
        )
        now = utc_now()
        if token is None or token.consumed_at is not None or _as_utc(token.expires_at) <= now:
            self.session.rollback()
            raise InvalidAccountTokenError
        user = self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            self.session.rollback()
            raise InvalidAccountTokenError
        token.consumed_at = now
        user.email_verified_at = user.email_verified_at or now
        self.session.commit()
        self.session.refresh(user)
        return user

    def request_password_reset(self, email: str) -> None:
        user = self.users.get_by_email(normalize_email(email))
        if user is None or not user.is_active or user.email_verified_at is None:
            return
        self._enforce_resend_cooldown(user, "password_reset")
        try:
            self._queue_account_token(user, "password_reset")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def reset_password(self, raw_token: str, password: str) -> None:
        token = self.account_tokens.get_by_hash_for_update(
            hash_account_token(raw_token), "password_reset"
        )
        now = utc_now()
        if token is None or token.consumed_at is not None or _as_utc(token.expires_at) <= now:
            self.session.rollback()
            raise InvalidAccountTokenError
        user = self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            self.session.rollback()
            raise InvalidAccountTokenError
        user.password_hash = hash_password(password)
        token.consumed_at = now
        self.account_tokens.consume_active(user.id, "password_reset", now)
        self.refresh_tokens.revoke_all_for_user(user.id, now)
        self.session.commit()

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password_or_dummy(current_password, user.password_hash):
            raise InvalidCredentialsError
        user.password_hash = hash_password(new_password)
        self.refresh_tokens.revoke_all_for_user(user.id, utc_now())
        self.session.commit()

    def update_profile(self, user: User, full_name: str, language: str, timezone: str) -> User:
        user.full_name = full_name
        user.language = language
        user.timezone = timezone
        self.session.commit()
        self.session.refresh(user)
        return user

    def list_sessions(self, user_id: UUID, current_raw_token: str | None) -> list[RefreshToken]:
        current_hash = hash_refresh_token(current_raw_token) if current_raw_token else None
        sessions = self.refresh_tokens.list_active_for_user(user_id, utc_now())
        for session in sessions:
            session.is_current = session.token_hash == current_hash
        return sessions

    def revoke_session(self, user_id: UUID, token_id: UUID) -> bool:
        changed = self.refresh_tokens.revoke_for_user(token_id, user_id, utc_now())
        self.session.commit()
        return changed > 0

    def revoke_all_sessions(self, user_id: UUID) -> int:
        changed = self.refresh_tokens.revoke_all_for_user(user_id, utc_now())
        self.session.commit()
        return changed
