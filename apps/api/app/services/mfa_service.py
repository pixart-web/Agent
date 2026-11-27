"""TOTP multi-factor authentication: enrolment, verification and recovery codes."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.user import User
from app.security import totp
from app.security.account_tokens import decrypt_secret, encrypt_secret
from app.security.passwords import verify_password_or_dummy


class MfaCodeInvalidError(Exception):
    """The one-time code or recovery code was not accepted."""


class MfaStateError(Exception):
    """The requested change does not fit the account's current MFA state."""


class MfaPasswordInvalidError(Exception):
    """The account password given to confirm a change was wrong."""


@dataclass(frozen=True)
class MfaSetup:
    secret: str
    otpauth_uri: str


class MfaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.key = get_settings().auth_secret_key

    def start_setup(self, user: User) -> MfaSetup:
        if user.mfa_enabled:
            raise MfaStateError("Two-factor authentication is already enabled")
        secret = totp.generate_secret()
        user.mfa_pending_secret_encrypted = encrypt_secret(secret, self.key)
        self.session.commit()
        return MfaSetup(secret=secret, otpauth_uri=totp.provisioning_uri(secret, user.email))

    def enable(self, user: User, code: str) -> list[str]:
        if user.mfa_enabled:
            raise MfaStateError("Two-factor authentication is already enabled")
        if not user.mfa_pending_secret_encrypted:
            raise MfaStateError("Start two-factor setup first")
        secret = decrypt_secret(user.mfa_pending_secret_encrypted, self.key)
        step = totp.verify_code(secret, code, utc_now(), None)
        if step is None:
            raise MfaCodeInvalidError
        codes = totp.generate_recovery_codes()
        user.mfa_secret_encrypted = user.mfa_pending_secret_encrypted
        user.mfa_pending_secret_encrypted = None
        user.mfa_enabled_at = utc_now()
        user.mfa_last_used_step = step
        user.mfa_recovery_code_hashes = [totp.hash_recovery_code(item) for item in codes]
        self.session.commit()
        return codes

    def check(self, user: User, code: str) -> bool:
        """Accept a current TOTP code or an unused recovery code; stage the change on success.
        The caller commits."""
        if not user.mfa_enabled or user.mfa_secret_encrypted is None:
            return False
        secret = decrypt_secret(user.mfa_secret_encrypted, self.key)
        step = totp.verify_code(secret, code, utc_now(), user.mfa_last_used_step)
        if step is not None:
            user.mfa_last_used_step = step
            return True
        if totp.looks_like_recovery_code(code):
            digest = totp.hash_recovery_code(code)
            remaining = list(user.mfa_recovery_code_hashes or [])
            if digest in remaining:
                remaining.remove(digest)
                user.mfa_recovery_code_hashes = remaining
                return True
        return False

    def disable(self, user: User, password: str, code: str) -> None:
        if not user.mfa_enabled:
            raise MfaStateError("Two-factor authentication is not enabled")
        if not verify_password_or_dummy(password, user.password_hash):
            raise MfaPasswordInvalidError
        if not self.check(user, code):
            self.session.rollback()
            raise MfaCodeInvalidError
        user.mfa_secret_encrypted = None
        user.mfa_pending_secret_encrypted = None
        user.mfa_enabled_at = None
        user.mfa_last_used_step = None
        user.mfa_recovery_code_hashes = None
        self.session.commit()

    def regenerate_recovery_codes(self, user: User, code: str) -> list[str]:
        if not user.mfa_enabled:
            raise MfaStateError("Two-factor authentication is not enabled")
        if not self.check(user, code):
            self.session.rollback()
            raise MfaCodeInvalidError
        codes = totp.generate_recovery_codes()
        user.mfa_recovery_code_hashes = [totp.hash_recovery_code(item) for item in codes]
        self.session.commit()
        return codes

    @staticmethod
    def recovery_codes_remaining(user: User) -> int:
        return len(user.mfa_recovery_code_hashes or []) if user.mfa_enabled else 0
