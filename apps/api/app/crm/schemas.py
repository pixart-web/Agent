from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    TypeAdapter,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrmContactMethodInput(StrictModel):
    method_type: Literal["email", "phone"]
    value: str = Field(min_length=3, max_length=320)
    label: str | None = Field(default=None, max_length=64)
    is_primary: bool = False

    @model_validator(mode="after")
    def validate_value(self) -> "CrmContactMethodInput":
        if self.method_type == "email":
            TypeAdapter(EmailStr).validate_python(self.value)
        else:
            digits = "".join(character for character in self.value if character.isdigit())
            if not 7 <= len(digits) <= 20:
                raise ValueError("Phone numbers must contain between 7 and 20 digits")
        return self


class CrmAddressInput(StrictModel):
    kind: str = Field(default="business", min_length=1, max_length=32)
    line1: str = Field(min_length=1, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    country_code: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")


class CrmOrganizationCreateInput(StrictModel):
    name: str = Field(min_length=1, max_length=255)
    website: AnyHttpUrl | None = None
    status: Literal["active", "inactive", "archived"] = "active"
    source: str = Field(default="manual", min_length=1, max_length=64)
    address: CrmAddressInput | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)


class CrmContactCreateInput(StrictModel):
    full_name: str = Field(min_length=1, max_length=255)
    organization_id: UUID | None = None
    job_title: str | None = Field(default=None, max_length=255)
    website: AnyHttpUrl | None = None
    status: Literal["active", "inactive", "archived"] = "active"
    source: str = Field(default="manual", min_length=1, max_length=64)
    methods: list[CrmContactMethodInput] = Field(default_factory=list, max_length=20)
    address: CrmAddressInput | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_methods(self) -> "CrmContactCreateInput":
        identities = [(item.method_type, item.value.casefold()) for item in self.methods]
        if len(identities) != len(set(identities)):
            raise ValueError("Contact methods must be unique")
        for method_type in ("email", "phone"):
            if sum(item.is_primary for item in self.methods if item.method_type == method_type) > 1:
                raise ValueError(f"Only one primary {method_type} is allowed")
        return self


class CrmContactUpdateInput(StrictModel):
    contact_id: UUID
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    organization_id: UUID | None = None
    clear_organization: bool = False
    job_title: str | None = Field(default=None, max_length=255)
    clear_job_title: bool = False
    website: AnyHttpUrl | None = None
    clear_website: bool = False
    status: Literal["active", "inactive", "archived"] | None = None
    methods: list[CrmContactMethodInput] | None = Field(default=None, max_length=20)
    tags: list[str] | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_update(self) -> "CrmContactUpdateInput":
        changed = self.model_fields_set - {"contact_id"}
        if not changed:
            raise ValueError("At least one contact field must be updated")
        if self.clear_organization and self.organization_id is not None:
            raise ValueError("Cannot set and clear organization together")
        if self.clear_job_title and self.job_title is not None:
            raise ValueError("Cannot set and clear job title together")
        if self.clear_website and self.website is not None:
            raise ValueError("Cannot set and clear website together")
        return self


class CrmSearchContactsInput(StrictModel):
    query: str | None = Field(default=None, min_length=1, max_length=255)
    organization_id: UUID | None = None
    status: Literal["active", "inactive", "archived"] | None = None
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class CrmContactInput(StrictModel):
    contact_id: UUID


class CrmOrganizationsInput(StrictModel):
    query: str | None = Field(default=None, min_length=1, max_length=255)
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class CrmOrganizationInput(StrictModel):
    organization_id: UUID


class CrmActivitiesInput(StrictModel):
    contact_id: UUID | None = None
    organization_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_target(self) -> "CrmActivitiesInput":
        if self.contact_id is None and self.organization_id is None:
            raise ValueError("A contact or organization is required")
        return self


class CrmNoteInput(StrictModel):
    contact_id: UUID | None = None
    organization_id: UUID | None = None
    body: str = Field(min_length=1, max_length=20_000)
    source: str = Field(default="manual", min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_target(self) -> "CrmNoteInput":
        if (self.contact_id is None) == (self.organization_id is None):
            raise ValueError("Exactly one contact or organization is required")
        return self


class CrmLinkEmailInput(StrictModel):
    contact_id: UUID | None = None
    organization_id: UUID | None = None
    email_reference_id: UUID

    @model_validator(mode="after")
    def validate_target(self) -> "CrmLinkEmailInput":
        if (self.contact_id is None) == (self.organization_id is None):
            raise ValueError("Exactly one contact or organization is required")
        return self


class CrmLinkEventInput(StrictModel):
    contact_id: UUID | None = None
    organization_id: UUID | None = None
    calendar_reference_id: UUID

    @model_validator(mode="after")
    def validate_target(self) -> "CrmLinkEventInput":
        if (self.contact_id is None) == (self.organization_id is None):
            raise ValueError("Exactly one contact or organization is required")
        return self


class CrmContactMethodOutput(StrictModel):
    id: UUID
    method_type: str
    value: str
    label: str | None
    is_primary: bool


class CrmAddressOutput(StrictModel):
    id: UUID
    kind: str
    line1: str
    line2: str | None
    city: str
    region: str | None
    postal_code: str | None
    country_code: str


class CrmContactOutput(StrictModel):
    id: UUID
    organization_id: UUID | None
    full_name: str
    job_title: str | None
    website: str | None
    status: str
    source: str
    methods: list[CrmContactMethodOutput]
    addresses: list[CrmAddressOutput]
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class CrmOrganizationOutput(StrictModel):
    id: UUID
    name: str
    website: str | None
    status: str
    source: str
    addresses: list[CrmAddressOutput]
    tags: list[str]
    member_count: int
    created_at: datetime
    updated_at: datetime


class CrmOrganizationsOutput(StrictModel):
    organizations: list[CrmOrganizationOutput]
    limit: int
    offset: int


class CrmContactsOutput(StrictModel):
    contacts: list[CrmContactOutput]
    limit: int
    offset: int


class CrmActivityOutput(StrictModel):
    id: UUID
    contact_id: UUID | None
    organization_id: UUID | None
    activity_type: str
    subject: str
    details: dict[str, object]
    source: str
    occurred_at: datetime
    email_reference_id: UUID | None
    calendar_reference_id: UUID | None


class CrmActivitiesOutput(StrictModel):
    activities: list[CrmActivityOutput]
    limit: int
    offset: int


class CrmNoteOutput(StrictModel):
    id: UUID
    contact_id: UUID | None
    organization_id: UUID | None
    body: str
    source: str
    created_at: datetime


class CrmLinkOutput(StrictModel):
    activity_id: UUID
    contact_id: UUID | None
    organization_id: UUID | None
    reference_id: UUID
    status: Literal["linked"] = "linked"
