from enum import StrEnum


class CommandStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RiskLevel(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CodexRunStatus(StrEnum):
    CREATED = "created"
    WAITING_APPROVAL = "waiting_approval"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SupervisorRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskActionStatus(StrEnum):
    PROPOSED = "proposed"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskExecutionStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ActorType(StrEnum):
    USER = "user"
    KIKO = "kiko"
    SUPERVISOR = "supervisor"
    AGENT = "agent"
    WORKER = "worker"
    SYSTEM = "system"


TERMINAL_COMMAND_STATUSES = frozenset(
    {
        CommandStatus.COMPLETED,
        CommandStatus.FAILED,
        CommandStatus.CANCELLED,
    }
)
