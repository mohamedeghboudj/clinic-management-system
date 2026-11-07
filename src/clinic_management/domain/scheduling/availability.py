"""Availability value objects and stateless scheduling policies.

``ScheduleException`` represents an immutable unavailable interval for a
single resource (doctor, room, clinic closure, etc.).

``AvailabilityRule`` is a pure, stateless policy object that checks whether a
requested ``TimeSlot`` is available given the clinic's opening hours and a
set of pre-fetched schedule exceptions.  It makes no database calls.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.facilities.opening_hours import OpeningHours
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot, require_aware
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(frozen=True, kw_only=True)
class ScheduleException:
    """Immutable record of an unavailable interval for a single resource.

    Use this for leave periods, clinic closures, room maintenance windows and
    similar one-off interruptions.  Recurrence (e.g., weekly leave) is a
    future design concern and must be expanded into individual
    ``ScheduleException`` instances at query time.

    Attributes:
        resource_id: Identifier of the affected resource (doctor, room, etc.).
        slot: The unavailable time interval (half-open, timezone-aware).
        reason_code: Short machine-readable code describing the type of
            exception (e.g. ``"ANNUAL_LEAVE"``, ``"MAINTENANCE"``).
    """

    resource_id: UUID
    slot: TimeSlot
    reason_code: str

    def __post_init__(self) -> None:
        """Validate identifiers, slot type and reason code.

        Raises:
            ValidationError: If any field is missing or invalid.
        """
        require_uuid(self.resource_id)
        if not isinstance(self.slot, TimeSlot):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="schedule_exception.slot.invalid",
                safe_details={"field": "slot"},
            )
        clean_reason = require_non_empty(self.reason_code, field="reason_code", max_length=50)
        object.__setattr__(self, "reason_code", clean_reason)


class AvailabilityRule:
    """Stateless policy for checking whether a time slot is available.

    This class makes no database calls.  The caller must supply the opening
    hours configuration and any relevant pre-fetched schedule exceptions for
    the resource(s) being queried.
    """

    def allows(
        self,
        slot: TimeSlot,
        opening_hours: OpeningHours,
        exceptions: Sequence[ScheduleException],
    ) -> bool:
        """Return True if the slot is within opening hours and free of exceptions.

        Args:
            slot: The timezone-aware half-open interval to test.
            opening_hours: The clinic's weekly opening schedule.
            exceptions: Pre-fetched schedule exceptions for the queried
                resource.  Only exceptions relevant to the resource should
                be supplied; this method does not filter by resource ID.

        Returns:
            True if the slot is within opening hours AND does not overlap
            any exception.
        """
        if not within_opening_hours(slot, opening_hours):
            return False
        for exc in exceptions:
            if slot.overlaps(exc.slot):
                return False
        return True


def within_opening_hours(slot: TimeSlot, schedule: OpeningHours) -> bool:
    """Delegate to the canonical opening-hours coverage check.

    Args:
        slot: The timezone-aware half-open interval to test.
        schedule: The clinic's weekly opening schedule.

    Returns:
        True if the slot is fully covered by opening hours.
    """
    return schedule.covers(slot)
