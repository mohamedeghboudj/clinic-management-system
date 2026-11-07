"""Scheduling-domain DTOs for read-side queries and list results.

``AppointmentSummary`` is a lightweight data transfer object returned by
repository search and list methods.  It exposes only the information needed
for appointment list views and does not carry clinical content.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.scheduling.enums import AppointmentStatus
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot


@dataclass(frozen=True, kw_only=True)
class AppointmentSummary:
    """Lightweight read model for appointment list and schedule views.

    This DTO is returned by paginated repository queries and does not expose
    clinical content such as prescriptions or consultation notes.

    Attributes:
        appointment_id: Unique appointment identifier.
        patient_id: Patient attending the appointment.
        doctor_id: Doctor conducting the appointment.
        room_id: Room allocated for the appointment.
        slot: Time interval reserved for the appointment.
        status: Current lifecycle status.
        version: Aggregate root version at the time of the query.
    """

    appointment_id: UUID
    patient_id: UUID
    doctor_id: UUID
    room_id: UUID
    slot: TimeSlot
    status: AppointmentStatus
    version: int

    def __post_init__(self) -> None:
        """Validate identifiers, slot, status and version on construction.

        Raises:
            ValidationError: If any field is missing or invalid.
        """
        require_uuid(self.appointment_id)
        require_uuid(self.patient_id)
        require_uuid(self.doctor_id)
        require_uuid(self.room_id)

        if not isinstance(self.slot, TimeSlot):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment_summary.slot.invalid",
                safe_details={"field": "slot"},
            )

        if not isinstance(self.status, AppointmentStatus):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment_summary.status.invalid",
                safe_details={"field": "status"},
            )

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment_summary.version.invalid",
                safe_details={"field": "version"},
            )
