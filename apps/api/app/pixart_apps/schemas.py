from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AppStatus = Literal["unsupported", "requires_setup", "available", "unavailable"]


class PixartApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    description: str | None
    base_url: str | None
    api_version: str | None
    docs_url: str | None
    status: AppStatus
    last_health_status: str | None
    last_health_at: datetime | None


class PixartApplicationCreate(BaseModel):
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    api_version: str | None = Field(default=None, max_length=32)
    docs_url: str | None = Field(default=None, max_length=500)

    @field_validator("base_url", "docs_url")
    @classmethod
    def _http_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not value.startswith(("https://", "http://")):
            raise ValueError("Use a full http(s) address")
        return value.rstrip("/")


class PixartApplicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    api_version: str | None = Field(default=None, max_length=32)
    docs_url: str | None = Field(default=None, max_length=500)
    status: AppStatus | None = None

    _http_url = field_validator("base_url", "docs_url")(PixartApplicationCreate._http_url.__func__)
