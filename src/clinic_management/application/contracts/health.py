"""Explicit process state and safe component health results."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from clinic_management.domain.shared._invariants import require_utc
from clinic_management.domain.shared.errors import ValidationError


class RuntimeState(StrEnum):
    """Name observable runtime states without creating mutable global state."""

    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    MAINTENANCE = "MAINTENANCE"
    RECOVERING = "RECOVERING"
    STOPPING = "STOPPING"


class HealthStatus(StrEnum):
    """Describe availability of one dependency or process component."""

    OK = "OK"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, kw_only=True)
class ComponentHealth:
    """Expose readiness facts without connection strings or failure messages."""

    component: str
    status: HealthStatus
    checked_at: datetime
    code: str | None

    def __post_init__(self) -> None:
        """Validate a bounded technical component name and UTC timestamp.

        Raises:
            ValidationError: If the component, state, time or code is invalid.
        """
        require_utc(self.checked_at)
        if (
            self.component not in {"backend", "database", "realtime", "logging", "backup"}
            or not isinstance(self.status, HealthStatus)
            or (self.code is not None and self.code not in HEALTH_CODES)
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="health.result.invalid")


HEALTH_CODES = frozenset(
    {"DEPENDENCY_UNAVAILABLE", "SCHEMA_INCOMPATIBLE", "BACKUP_STALE", "LOGGING_UNAVAILABLE"}
)
