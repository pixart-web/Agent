from typing import Literal

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    database: Literal["healthy", "unavailable"]
    redis: Literal["healthy", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    services: ServiceHealth
