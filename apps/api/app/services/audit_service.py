from uuid import UUID

from sqlalchemy.orm import Session

from app.execution.context_safety import sanitize_execution_payload
from app.models.audit_log import AuditLog
from app.models.workflow_enums import ActorType
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: Session) -> None:
        self.repository = AuditRepository(session)

    def record(
        self,
        *,
        actor_type: ActorType,
        actor_id: UUID | None,
        event_type: str,
        resource_type: str,
        resource_id: UUID,
        metadata: dict[str, object],
        correlation_id: UUID,
    ) -> AuditLog:
        log = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_payload=sanitize_execution_payload(metadata),
            correlation_id=correlation_id,
        )
        self.repository.add(log)
        return log
