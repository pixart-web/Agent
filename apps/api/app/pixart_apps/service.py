"""Pixart ecosystem registry. Registration and edits are platform-admin actions (audited);
the only network call is an optional, read-only GET of the product's /health endpoint."""

import ipaddress
import socket
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.audit_log import AuditLog
from app.models.pixart_application import PixartApplication
from app.models.workflow_enums import ActorType
from app.pixart_apps.schemas import PixartApplicationCreate, PixartApplicationUpdate

HEALTH_TIMEOUT_SECONDS = 5.0


class PixartAppConflictError(Exception):
    pass


class PixartAppContractError(Exception):
    """An app cannot be marked available without a recorded API contract."""


class HealthChecksDisabledError(Exception):
    pass


class UnsafeHealthTargetError(Exception):
    pass


def _host_is_private(host: str) -> bool:
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def health_target(base_url: str, allow_private: bool) -> str:
    """The URL to probe, or UnsafeHealthTargetError. HTTPS is required for public hosts;
    private, loopback and link-local addresses are refused unless explicitly allowed."""
    parts = urlsplit(base_url)
    host = parts.hostname or ""
    if parts.username or parts.password or not host:
        raise UnsafeHealthTargetError("The product address is not valid")
    private = _host_is_private(host)
    if private and not allow_private:
        raise UnsafeHealthTargetError("Private network addresses are not allowed")
    if parts.scheme != "https" and not (private and allow_private):
        raise UnsafeHealthTargetError("The product address must use HTTPS")
    return f"{parts.scheme}://{parts.netloc}/health"


class PixartAppService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[PixartApplication]:
        return list(self.db.scalars(select(PixartApplication).order_by(PixartApplication.name)))

    def get(self, app_id: UUID) -> PixartApplication:
        app = self.db.get(PixartApplication, app_id)
        if app is None:
            raise LookupError
        return app

    def create(self, data: PixartApplicationCreate, actor_id: UUID) -> PixartApplication:
        app = PixartApplication(**data.model_dump(), status="unsupported")
        self.db.add(app)
        try:
            self.db.flush()
        except IntegrityError as error:
            self.db.rollback()
            raise PixartAppConflictError from error
        self._audit(actor_id, "platform.pixart_app_registered", app.id, None, app.key)
        self.db.commit()
        self.db.refresh(app)
        return app

    def update(
        self, app_id: UUID, data: PixartApplicationUpdate, actor_id: UUID
    ) -> PixartApplication:
        app = self.get(app_id)
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(app, field, value)
        if app.status == "available" and not (app.api_version and app.docs_url and app.base_url):
            self.db.rollback()
            raise PixartAppContractError
        self._audit(
            actor_id,
            "platform.pixart_app_updated",
            app.id,
            None,
            {key: str(value) for key, value in changes.items()},
        )
        self.db.commit()
        self.db.refresh(app)
        return app

    def check_health(self, app_id: UUID, actor_id: UUID) -> PixartApplication:
        settings = get_settings()
        if not settings.pixart_apps_health_checks_enabled:
            raise HealthChecksDisabledError
        app = self.get(app_id)
        if not app.base_url:
            raise UnsafeHealthTargetError("The product has no address")
        url = health_target(app.base_url, settings.pixart_apps_allow_private_hosts)
        try:
            response = httpx.get(url, timeout=HEALTH_TIMEOUT_SECONDS, follow_redirects=False)
            result = "healthy" if response.status_code == 200 else "error"
        except httpx.HTTPError:
            result = "unreachable"
        app.last_health_status = result
        app.last_health_at = utc_now()
        self._audit(actor_id, "platform.pixart_app_health_checked", app.id, None, result)
        self.db.commit()
        self.db.refresh(app)
        return app

    def _audit(
        self, actor_id: UUID, event_type: str, resource_id: UUID, previous: object, value: object
    ) -> None:
        self.db.add(
            AuditLog(
                actor_type=ActorType.USER,
                actor_id=actor_id,
                event_type=event_type,
                resource_type="pixart_application",
                resource_id=resource_id,
                metadata_payload={"previous": previous, "value": value},
                correlation_id=uuid4(),
            )
        )
