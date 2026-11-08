"""Synthetic infrastructure probes, not substitute patient or billing models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.events import DomainEvent

FIXED_TIME = datetime(2026, 11, 1, 9, tzinfo=UTC)
EVENT_ID = UUID(int=100)
AUDIT_ID = UUID(int=200)


@dataclass(eq=False, kw_only=True)
class ProbeEntity(Entity):
    """Expose mutable fixture state to prove copy and rollback behavior."""

    id: UUID
    version: int = 0
    value: int = 0


@dataclass(frozen=True, kw_only=True)
class AuditFixture:
    """Satisfy the audit protocol without implementing M2's clinical access model."""

    id: UUID
    clinic_id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    outcome: str
    occurred_at: datetime
    correlation_id: UUID
    reason_code: str | None


def event_fixture(*, event_id: UUID = EVENT_ID) -> DomainEvent:
    """Construct a metadata-only synthetic event for transaction verification.

    Args:
        event_id: Explicit identifier allowing duplicate and replay scenarios.

    Returns:
        A valid event envelope containing only synthetic fixture identifiers.
    """
    return DomainEvent(
        event_id=event_id,
        event_type="PATIENT_REGISTERED",
        clinic_id=UUID(int=10),
        entity_id=UUID(int=1),
        entity_version=0,
        actor_id=UUID(int=11),
        occurred_at=FIXED_TIME,
        correlation_id=UUID(int=12),
    )


def audit_fixture(*, entry_id: UUID = AUDIT_ID) -> AuditFixture:
    """Construct an immutable audit protocol fixture with no clinical fields.

    Args:
        entry_id: Explicit ID for successful or duplicate-entry verification.

    Returns:
        A synthetic append-only audit fact matching M2's documented field shape.
    """
    return AuditFixture(
        id=entry_id,
        clinic_id=UUID(int=10),
        actor_id=UUID(int=11),
        action="PATIENT_WRITE",
        resource_type="patient",
        resource_id=UUID(int=1),
        outcome="success",
        occurred_at=FIXED_TIME,
        correlation_id=UUID(int=12),
        reason_code=None,
    )
