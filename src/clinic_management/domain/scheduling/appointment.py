"""Appointment aggregate root and its lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.scheduling.enums import AppointmentStatus
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot, require_aware


@dataclass(eq=False, kw_only=True)
class Appointment(Entity):
    """Aggregate root representing a scheduled clinic appointment.

    Attributes:
        id: Unique appointment identifier.
        version: Aggregate root version for optimistic concurrency.
        clinic_id: Clinic in which the appointment takes place.
        patient_id: Patient attending the appointment.
        doctor_id: Doctor conducting the appointment.
        room_id: Room allocated for the appointment.
        slot: Time interval reserved for the appointment.
        status: Current lifecycle status.
        reason_summary: Optional brief description of the visit reason.
        cancellation_reason: Reason supplied when cancelling (required).
        updated_at: Timestamp of the most recent status change.

    Note:
        Availability checks (overlaps with other appointments) are the
        responsibility of the application use case, not this entity.
    """

    id: UUID
    version: int = 0
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    room_id: UUID
    slot: TimeSlot
    updated_at: datetime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    reason_summary: str | None = None
    cancellation_reason: str | None = None

    def __post_init__(self) -> None:
        """Validate identifiers, slot, status, and timestamps.

        Raises:
            ValidationError: If any required field is missing or invalid.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)
        require_uuid(self.patient_id)
        require_uuid(self.doctor_id)
        require_uuid(self.room_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment.version.invalid",
                safe_details={"field": "version"},
            )

        if not isinstance(self.slot, TimeSlot):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment.slot.invalid",
                safe_details={"field": "slot"},
            )

        if not isinstance(self.status, AppointmentStatus):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment.status.invalid",
                safe_details={"field": "status"},
            )

        if self.reason_summary is not None:
            if not isinstance(self.reason_summary, str) or not self.reason_summary.strip():
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="appointment.reason_summary.invalid",
                    safe_details={"field": "reason_summary"},
                )
            object.__setattr__(self, "reason_summary", self.reason_summary.strip())

        if self.cancellation_reason is not None:
            if (
                not isinstance(self.cancellation_reason, str)
                or not self.cancellation_reason.strip()
            ):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="appointment.cancellation_reason.invalid",
                    safe_details={"field": "cancellation_reason"},
                )
            object.__setattr__(
                self, "cancellation_reason", self.cancellation_reason.strip()
            )

        require_aware(self.updated_at, "updated_at")

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def check_in(self, *, at: datetime) -> None:
        """Transition from SCHEDULED to CHECKED_IN.

        Args:
            at: Timezone-aware timestamp of the check-in event.

        Raises:
            ValidationError: If *at* is naive.
            InvalidTransitionError: If the current status is not SCHEDULED.
        """
        require_aware(at, "at")
        self._transition_to(AppointmentStatus.CHECKED_IN, at=at)

    def complete(self, *, at: datetime) -> None:
        """Transition from CHECKED_IN to COMPLETED.

        Args:
            at: Timezone-aware timestamp of completion.

        Raises:
            ValidationError: If *at* is naive.
            InvalidTransitionError: If the current status is not CHECKED_IN.
        """
        require_aware(at, "at")
        self._transition_to(AppointmentStatus.COMPLETED, at=at)

    def cancel(self, reason: str, *, at: datetime) -> None:
        """Transition from SCHEDULED or CHECKED_IN to CANCELLED.

        Args:
            reason: Non-empty text explaining the cancellation.
            at: Timezone-aware timestamp of cancellation.

        Raises:
            ValidationError: If *reason* is empty or *at* is naive.
            InvalidTransitionError: If the current status does not permit
                cancellation.
        """
        require_aware(at, "at")
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment.cancellation_reason.required",
                safe_details={"field": "reason"},
            )
        self._transition_to(AppointmentStatus.CANCELLED, at=at)
        self.cancellation_reason = reason.strip()

    def mark_no_show(self, *, at: datetime) -> None:
        """Transition from SCHEDULED to NO_SHOW.

        A no-show should only be recorded after the appointment slot has ended.
        This method does NOT enforce the timing rule — the calling use case is
        responsible for checking that ``at >= slot.end`` before calling.

        Args:
            at: Timezone-aware timestamp when the no-show is recorded.

        Raises:
            ValidationError: If *at* is naive.
            InvalidTransitionError: If the current status is not SCHEDULED.
        """
        require_aware(at, "at")
        self._transition_to(AppointmentStatus.NO_SHOW, at=at)

    def reschedule(self, slot: TimeSlot, *, at: datetime) -> None:
        """Assign a new time slot while remaining in the SCHEDULED state.

        Rescheduling is only permitted when the appointment is SCHEDULED.
        It does not check for conflicts with other appointments — that check
        belongs to the application use case.

        Args:
            slot: New timezone-aware half-open time interval.
            at: Timezone-aware timestamp of the reschedule action.

        Raises:
            ValidationError: If *slot* is not a ``TimeSlot`` or *at* is naive.
            InvalidTransitionError: If the appointment is not SCHEDULED.
        """
        require_aware(at, "at")
        if not isinstance(slot, TimeSlot):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="appointment.slot.invalid",
                safe_details={"field": "slot"},
            )
        if self.status is not AppointmentStatus.SCHEDULED:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="appointment.reschedule.not_scheduled",
                safe_details={"status": self.status.value},
            )
        self.slot = slot
        self.updated_at = at

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _transition_to(self, target: AppointmentStatus, *, at: datetime) -> None:
        """Apply a validated status transition and update the timestamp.

        Args:
            target: The desired next status.
            at: Timestamp of the transition (already validated as aware).

        Raises:
            InvalidTransitionError: If the transition is not permitted.
        """
        if not self.status.can_transition_to(target):
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="appointment.transition.invalid",
                safe_details={
                    "from_status": self.status.value,
                    "to_status": target.value,
                },
            )
        self.status = target
        self.updated_at = at
