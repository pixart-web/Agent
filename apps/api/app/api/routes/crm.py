from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.crm.schemas import (
    CrmActivitiesInput,
    CrmActivitiesOutput,
    CrmContactInput,
    CrmContactOutput,
    CrmContactsOutput,
    CrmOrganizationInput,
    CrmOrganizationOutput,
    CrmOrganizationsInput,
    CrmOrganizationsOutput,
    CrmSearchContactsInput,
)
from app.crm.service import CrmService
from app.db.session import get_db
from app.execution.context import ExecutionContext
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.user import User

router = APIRouter(prefix="/crm", tags=["crm"])


def _context(user_id: UUID) -> ExecutionContext:
    identifier = uuid4()
    return ExecutionContext(
        user_id=user_id,
        command_id=identifier,
        task_id=identifier,
        action_id=identifier,
        execution_id=identifier,
        correlation_id=identifier,
        credentials=EnvironmentCredentialProvider(),
    )


def _service(db: Session) -> CrmService:
    return CrmService(sessionmaker(bind=db.get_bind(), expire_on_commit=False))


@router.get("/contacts", response_model=CrmContactsOutput)
def search_contacts(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    query: str | None = None,
    organization_id: UUID | None = None,
    contact_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> CrmContactsOutput:
    return _service(db).search_contacts(
        _context(user.id),
        CrmSearchContactsInput(
            query=query,
            organization_id=organization_id,
            status=contact_status,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/contacts/{contact_id}", response_model=CrmContactOutput)
def get_contact(
    contact_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CrmContactOutput:
    return _service(db).get_contact(_context(user.id), CrmContactInput(contact_id=contact_id))


@router.get("/organizations", response_model=CrmOrganizationsOutput)
def list_organizations(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    query: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> CrmOrganizationsOutput:
    return _service(db).list_organizations(
        _context(user.id),
        CrmOrganizationsInput(query=query, limit=limit, offset=offset),
    )


@router.get("/organizations/{organization_id}", response_model=CrmOrganizationOutput)
def get_organization(
    organization_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CrmOrganizationOutput:
    return _service(db).get_organization(
        _context(user.id), CrmOrganizationInput(organization_id=organization_id)
    )


@router.get("/activities", response_model=CrmActivitiesOutput)
def list_activities(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    contact_id: UUID | None = None,
    organization_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> CrmActivitiesOutput:
    return _service(db).list_activities(
        _context(user.id),
        CrmActivitiesInput(
            contact_id=contact_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        ),
    )
