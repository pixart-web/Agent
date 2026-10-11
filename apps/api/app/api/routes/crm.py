import csv
import hashlib
import io
import json
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.crm.errors import CrmConflictError, CrmNotFoundError, CrmValidationError
from app.crm.schemas import (
    CrmActivitiesInput,
    CrmActivitiesOutput,
    CrmContactCreateInput,
    CrmContactInput,
    CrmContactOutput,
    CrmContactsOutput,
    CrmContactUpdateInput,
    CrmOrganizationCreateInput,
    CrmOrganizationInput,
    CrmOrganizationOutput,
    CrmOrganizationsInput,
    CrmOrganizationsOutput,
    CrmOrganizationUpdateInput,
    CrmSearchContactsInput,
)
from app.crm.service import CrmService
from app.db.session import get_db
from app.execution.context import ExecutionContext
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.knowledge import WorkspaceMember
from app.models.user import User

router = APIRouter(prefix="/crm", tags=["crm"])
MAX_CRM_IMPORT_BYTES = 1_000_000
MAX_CRM_IMPORT_ROWS = 1_000


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


def _require_editor(db: Session, user: User) -> None:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace edit permission is required")


def _raise_crm(error: Exception) -> None:
    if isinstance(error, CrmNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, CrmConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, CrmValidationError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


def _safe_csv(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


async def _read_import(upload: UploadFile) -> tuple[bytes, list[dict[str, str]]]:
    if upload.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        raise HTTPException(status_code=415, detail="Only CSV imports are supported")
    content = await upload.read(MAX_CRM_IMPORT_BYTES + 1)
    if len(content) > MAX_CRM_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="CRM import exceeds 1 MB")
    try:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error) as error:
        raise HTTPException(status_code=422, detail="Invalid UTF-8 CSV file") from error
    if len(rows) > MAX_CRM_IMPORT_ROWS:
        raise HTTPException(status_code=422, detail="CRM import exceeds 1,000 rows")
    return content, rows


def _preview_rows(rows: list[dict[str, str]], existing_names: set[str]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    preview = []
    for index, row in enumerate(rows, start=2):
        record_type = (row.get("record_type") or "").strip().casefold()
        name = (row.get("name") or "").strip()
        errors: list[str] = []
        if record_type not in {"organization", "contact"}:
            errors.append("record_type must be organization or contact")
        if not name:
            errors.append("name is required")
        identity = (record_type, name.casefold())
        duplicate = identity in seen or (
            record_type == "organization" and name.casefold() in existing_names
        )
        if duplicate:
            errors.append("duplicate record")
        tags = [value.strip() for value in (row.get("tags") or "").split(",") if value.strip()]
        try:
            if record_type == "organization" and name:
                CrmOrganizationCreateInput(
                    name=name,
                    website=row.get("website") or None,
                    tags=tags,
                    source="csv_import",
                )
            elif record_type == "contact" and name:
                methods = []
                if row.get("email"):
                    methods.append(
                        {"method_type": "email", "value": row["email"], "is_primary": True}
                    )
                if row.get("phone"):
                    methods.append(
                        {"method_type": "phone", "value": row["phone"], "is_primary": True}
                    )
                CrmContactCreateInput(
                    full_name=name,
                    job_title=row.get("job_title") or None,
                    methods=methods,
                    tags=tags,
                    source="csv_import",
                )
        except ValidationError:
            errors.append("record fields are invalid")
        seen.add(identity)
        preview.append(
            {
                "row": index,
                "record_type": record_type,
                "name": name,
                "valid": not errors,
                "errors": errors,
            }
        )
    return preview


@router.get("/export")
def export_crm(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    resource: Literal["organizations", "contacts"] = "organizations",
    export_format: Annotated[Literal["csv", "json"], Query(alias="format")] = "csv",
) -> Response:
    service = _service(db)
    if resource == "organizations":
        values = service.list_organizations(
            _context(user.id), CrmOrganizationsInput(limit=100, offset=0)
        ).organizations
        rows = [
            {
                "id": item.id,
                "name": item.name,
                "website": item.website,
                "status": item.status,
                "tags": ",".join(item.tags),
            }
            for item in values
        ]
    else:
        values = service.search_contacts(
            _context(user.id), CrmSearchContactsInput(limit=100, offset=0)
        ).contacts
        rows = [
            {
                "id": item.id,
                "name": item.full_name,
                "job_title": item.job_title,
                "status": item.status,
                "email": next(
                    (method.value for method in item.methods if method.method_type == "email"), ""
                ),
                "tags": ",".join(item.tags),
            }
            for item in values
        ]
    if export_format == "json":
        return Response(
            json.dumps(rows, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="crm-{resource}.json"'},
        )
    output = io.StringIO()
    fields = list(rows[0]) if rows else (["id", "name", "status"])
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows([{key: _safe_csv(value) for key, value in row.items()} for row in rows])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="crm-{resource}.csv"'},
    )


@router.post("/import/preview")
async def preview_crm_import(
    upload: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_editor(db, user)
    content, rows = await _read_import(upload)
    existing = {
        item.name.casefold()
        for item in _service(db)
        .list_organizations(_context(user.id), CrmOrganizationsInput(limit=100, offset=0))
        .organizations
    }
    preview = _preview_rows(rows, existing)
    return {
        "fingerprint": hashlib.sha256(content).hexdigest(),
        "rows": preview,
        "valid_rows": sum(item["valid"] for item in preview),
        "invalid_rows": sum(not item["valid"] for item in preview),
    }


@router.post("/import/confirm")
async def confirm_crm_import(
    upload: Annotated[UploadFile, File()],
    fingerprint: Annotated[str, Form(min_length=64, max_length=64)],
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    _require_editor(db, user)
    content, rows = await _read_import(upload)
    if hashlib.sha256(content).hexdigest() != fingerprint:
        raise HTTPException(status_code=409, detail="Import file changed after preview")
    service = _service(db)
    existing_values = service.list_organizations(
        _context(user.id), CrmOrganizationsInput(limit=100, offset=0)
    ).organizations
    existing = {item.name.casefold() for item in existing_values}
    preview = _preview_rows(rows, existing)
    if any(not item["valid"] for item in preview):
        raise HTTPException(status_code=422, detail="Import contains invalid or duplicate rows")
    organizations = {item.name.casefold(): str(item.id) for item in existing_values}
    created = 0
    for row in rows:
        record_type = row["record_type"].strip().casefold()
        name = row["name"].strip()
        tags = [value.strip() for value in (row.get("tags") or "").split(",") if value.strip()]
        if record_type == "organization":
            value = service.create_organization(
                _context(user.id),
                CrmOrganizationCreateInput(
                    name=name,
                    website=row.get("website") or None,
                    tags=tags,
                    source="csv_import",
                ),
                governed=False,
            )
            organizations[name.casefold()] = str(value.id)
        else:
            organization_name = (row.get("organization_name") or "").strip().casefold()
            methods = []
            if row.get("email"):
                methods.append({"method_type": "email", "value": row["email"], "is_primary": True})
            if row.get("phone"):
                methods.append({"method_type": "phone", "value": row["phone"], "is_primary": True})
            service.create_contact(
                _context(user.id),
                CrmContactCreateInput(
                    full_name=name,
                    organization_id=organizations.get(organization_name),
                    job_title=row.get("job_title") or None,
                    methods=methods,
                    tags=tags,
                    source="csv_import",
                ),
                governed=False,
            )
        created += 1
    return {"created": created, "fingerprint": fingerprint}


@router.post(
    "/organizations", response_model=CrmOrganizationOutput, status_code=status.HTTP_201_CREATED
)
def create_organization(
    value: CrmOrganizationCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CrmOrganizationOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_organization(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.patch("/organizations/{organization_id}", response_model=CrmOrganizationOutput)
def update_organization(
    organization_id: UUID,
    value: CrmOrganizationUpdateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CrmOrganizationOutput:
    _require_editor(db, user)
    if value.organization_id != organization_id:
        raise HTTPException(status_code=422, detail="Organization id does not match path")
    try:
        return _service(db).update_organization(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.post("/contacts", response_model=CrmContactOutput, status_code=status.HTTP_201_CREATED)
def create_contact(
    value: CrmContactCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CrmContactOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_contact(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


@router.patch("/contacts/{contact_id}", response_model=CrmContactOutput)
def update_contact(
    contact_id: UUID,
    value: CrmContactUpdateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CrmContactOutput:
    _require_editor(db, user)
    if value.contact_id != contact_id:
        raise HTTPException(status_code=422, detail="Contact id does not match path")
    try:
        return _service(db).update_contact(_context(user.id), value, governed=False)
    except (CrmNotFoundError, CrmConflictError, CrmValidationError) as error:
        _raise_crm(error)


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
