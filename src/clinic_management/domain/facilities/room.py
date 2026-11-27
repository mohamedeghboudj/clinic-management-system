"""Consultation room domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.facilities.enums import RoomStatus, RoomType
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(eq=False, kw_only=True)
class Room(Entity):
    """Domain entity representing a physical room within a clinic.

    Attributes:
        id: Unique identifier for this room.
        version: Aggregate root version for optimistic concurrency.
        clinic_id: Identifier of the clinic that owns this room.
        number: Short human-readable room identifier (e.g. ``"C-01"``).
        kind: Category of room.
        capacity: Maximum number of patients the room can accommodate.
        status: Current operational status.
        status_reason: Optional free-text reason for an out-of-service status.

    Note:
        Occupancy is derived from active reservations, not stored here.
        Do not add a ``Room.book()`` method.  Appointment scheduling is the
        single source of reservation information.
    """

    id: UUID
    version: int = 0
    clinic_id: UUID
    number: str
    kind: RoomType
    capacity: int
    status: RoomStatus = RoomStatus.ACTIVE
    status_reason: str | None = None

    def __post_init__(self) -> None:
        """Validate identifiers, number, capacity and status.

        Raises:
            ValidationError: If any field fails its invariant.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="room.version.invalid",
                safe_details={"field": "version"},
            )

        clean_number = require_non_empty(self.number, field="number", max_length=20)
        object.__setattr__(self, "number", clean_number)

        if not isinstance(self.kind, RoomType):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="room.kind.invalid",
                safe_details={"field": "kind"},
            )

        if type(self.capacity) is not int or self.capacity < 1:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="room.capacity.invalid",
                safe_details={"field": "capacity"},
            )

        if not isinstance(self.status, RoomStatus):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="room.status.invalid",
                safe_details={"field": "status"},
            )

        if self.status_reason is not None:
            clean_reason = require_non_empty(
                self.status_reason, field="status_reason", max_length=500
            )
            object.__setattr__(self, "status_reason", clean_reason)

    def mark_out_of_service(self, reason: str) -> None:
        """Set the room status to OUT_OF_SERVICE with an explanatory reason.

        Args:
            reason: Non-empty text explaining why the room is out of service.

        Note:
            This does NOT automatically cancel existing appointments in this
            room.  The calling use case is responsible for downstream effects.

        Raises:
            ValidationError: If *reason* is empty or whitespace-only.
        """
        clean_reason = require_non_empty(reason, field="reason", max_length=500)
        self.status = RoomStatus.OUT_OF_SERVICE
        self.status_reason = clean_reason

    def restore_service(self) -> None:
        """Return the room to ACTIVE status and clear the status reason."""
        self.status = RoomStatus.ACTIVE
        self.status_reason = None

    def is_bookable(self) -> bool:
        """Return whether the room can currently accept new appointments.

        Returns:
            True only if the room status is ``ACTIVE``.
        """
        return self.status is RoomStatus.ACTIVE
