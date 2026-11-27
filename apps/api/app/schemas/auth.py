from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(AccessTokenResponse):
    user: UserPublic


class RegistrationResponse(BaseModel):
    email: str
    verification_required: bool = True


class MessageResponse(BaseModel):
    message: str


class SessionRead(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str | None
    ip_address: str | None
    current: bool


class MfaChallengeResponse(BaseModel):
    """Returned by login instead of tokens when the account uses two-factor authentication."""

    mfa_required: bool = True
    mfa_token: str


class MfaVerifyRequest(BaseModel):
    mfa_token: str = Field(min_length=1, max_length=2048)
    code: str = Field(min_length=6, max_length=32)


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=32)


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    code: str = Field(min_length=6, max_length=32)


class MfaStatus(BaseModel):
    enabled: bool
    enabled_at: datetime | None
    recovery_codes_remaining: int
    setup_pending: bool


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaRecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]
