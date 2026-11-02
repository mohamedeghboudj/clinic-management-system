"""Immutable, metadata-only hints staged with the business transaction."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.errors import ValidationError

EVENT_TYPES = frozenset(
    {
        "PATIENT_REGISTERED",
        "ACCESS_CHANGED",
        "APPOINTMENT_BOOKED",
        "APPOINTMENT_RESCHEDULED",
        "PATIENT_CHECKED_IN",
        "APPOINTMENT_CANCELLED",
        "CONSULTATION_FINALIZED",
        "PRESCRIPTION_ISSUED",
        "INVOICE_ISSUED",
        "PAYMENT_RECORDED",
        "PAYMENT_REVERSED",
        "LOW_STOCK_DETECTED",
    }
)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Identify a committed business change without including clinical content."""

    event_id: UUID
    event_type: str
    clinic_id: UUID
    entity_id: UUID
    entity_version: int
    actor_id: UUID
    occurred_at: datetime
    correlation_id: UUID

    def __post_init__(self) -> None:
        """Validate identifiers, allowlisted event type and authoritative time.

        Raises:
            ValidationError: If an identifier, type, version or time is invalid.
        """
        for value in (
            self.event_id,
            self.clinic_id,
            self.entity_id,
            self.actor_id,
            self.correlation_id,
        ):
            require_uuid(value)
        require_utc(self.occurred_at)
        if self.event_type not in EVENT_TYPES:
            raise ValidationError(code="INVALID_VALUE", message_key="event.type.invalid")
        if type(self.entity_version) is not int or self.entity_version < 0:
            raise ValidationError(code="INVALID_VALUE", message_key="event.version.invalid")
