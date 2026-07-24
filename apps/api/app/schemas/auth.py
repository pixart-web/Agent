from pydantic import BaseModel

from app.schemas.user import UserPublic


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(AccessTokenResponse):
    user: UserPublic
