"""AuditEntry: immutable, append-only record of a security-sensitive action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(frozen=True, kw_only=True)
class AuditEntry:
    """Immutable, append-only record of a security-sensitive action.

    Audit entries must never be modified after creation.  They must not
    contain passwords, raw tokens, or free-form clinical narrative; use
    ``reason_code`` for structured context.  Failed authentication may have
    no known actor (``actor_id`` is None in that case).

    Attributes:
        id: Unique identifier for this audit entry.
        clinic_id: Clinic context in which the action occurred.
        actor_id: Account identifier of the actor, or None for unauthenticated
                  failures (e.g. failed login attempts).
        action: Machine-readable action identifier (e.g. ``"PATIENT_ACCESSED"``).
        resource_type: Type of resource affected (e.g. ``"Patient"``).
        resource_id: Identifier of the affected resource, or None.
        outcome: Outcome code (e.g. ``"SUCCESS"`` or ``"DENIED"``).
        occurred_at: UTC timestamp when the action occurred.
        correlation_id: Identifier for correlating related audit entries.
        reason_code: Optional structured reason code (not free clinical text).
    """

    id: UUID
    clinic_id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    outcome: str
    occurred_at: datetime
    correlation_id: UUID

    reason_code: str | None = None

    def __post_init__(self) -> None:
        """Validate all fields on construction.

        Raises:
            ValidationError: If any identifier, timestamp, or string field is invalid.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)

        if self.actor_id is not None:
            require_uuid(self.actor_id)
        if self.resource_id is not None:
            require_uuid(self.resource_id)

        require_uuid(self.correlation_id)
        require_utc(self.occurred_at)

        require_non_empty(self.action, field="action", max_length=200)
        require_non_empty(self.resource_type, field="resource_type", max_length=200)
        require_non_empty(self.outcome, field="outcome", max_length=100)

        if self.reason_code is not None:
            require_non_empty(self.reason_code, field="reason_code", max_length=200)

