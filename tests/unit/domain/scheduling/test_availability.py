"""Unit tests for ScheduleException and AvailabilityRule."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest

from clinic_management.domain.facilities.opening_hours import OpeningHours, OpeningPeriod
from clinic_management.domain.scheduling.availability import (
    AvailabilityRule,
    ScheduleException,
    within_opening_hours,
)
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot

_ALGIERS = "Africa/Algiers"  # UTC+1 all year

# A fixed Monday.  2026-11-09 is a Monday.
_MON_09_00_UTC = datetime(2026, 11, 9, 8, 0, tzinfo=UTC)   # 09:00 Algiers local
_MON_09_30_UTC = datetime(2026, 11, 9, 8, 30, tzinfo=UTC)  # 09:30 Algiers local
_MON_10_00_UTC = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)   # 10:00 Algiers local


def _business_hours() -> OpeningHours:
    """Mon–Fri 08:00–17:00 Africa/Algiers."""
    periods = tuple(
        OpeningPeriod(weekday=d, opens_at=time(8), closes_at=time(17)) for d in range(5)
    )
    return OpeningHours(timezone=_ALGIERS, periods=periods)


def _slot(h_start: int, m_start: int, h_end: int, m_end: int, day: int = 9) -> TimeSlot:
    """Build a TimeSlot on 2026-11-{day} in UTC."""
    return TimeSlot(
        start=datetime(2026, 11, day, h_start, m_start, tzinfo=UTC),
        end=datetime(2026, 11, day, h_end, m_end, tzinfo=UTC),
    )


def _exception(slot: TimeSlot, reason: str = "MAINTENANCE") -> ScheduleException:
    return ScheduleException(resource_id=uuid4(), slot=slot, reason_code=reason)


# ---------------------------------------------------------------------------
# ScheduleException
# ---------------------------------------------------------------------------

class TestScheduleException:
    """Construction and validation of ScheduleException."""

    def test_valid_exception_accepted(self) -> None:
        exc = _exception(_slot(8, 0, 9, 0))
        assert exc.reason_code == "MAINTENANCE"

    def test_empty_reason_code_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ScheduleException(resource_id=uuid4(), slot=_slot(8, 0, 9, 0), reason_code="  ")
        assert exc_info.value.safe_details["field"] == "reason_code"

    def test_invalid_slot_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScheduleException(
                resource_id=uuid4(),
                slot="not-a-slot",  # type: ignore[arg-type]
                reason_code="LEAVE",
            )

    def test_exception_is_immutable(self) -> None:
        exc = _exception(_slot(8, 0, 9, 0))
        with pytest.raises((TypeError, AttributeError)):
            exc.reason_code = "CHANGED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AvailabilityRule
# ---------------------------------------------------------------------------

class TestAvailabilityRule:
    """Tests for AvailabilityRule.allows()."""

    def test_slot_inside_hours_no_exceptions_allowed(self) -> None:
        """Available slot within opening hours with no exceptions → True."""
        rule = AvailabilityRule()
        # 09:00–09:30 Algiers local = 08:00–08:30 UTC
        slot = _slot(8, 0, 8, 30)
        assert rule.allows(slot, _business_hours(), []) is True

    def test_slot_outside_opening_hours_not_allowed(self) -> None:
        """Slot that falls outside opening hours → False."""
        rule = AvailabilityRule()
        # 06:00–07:00 local = 05:00–06:00 UTC — before clinic opens
        slot = _slot(5, 0, 6, 0)
        assert rule.allows(slot, _business_hours(), []) is False

    def test_slot_overlapping_exception_not_allowed(self) -> None:
        """Slot that overlaps a schedule exception → False."""
        rule = AvailabilityRule()
        slot = _slot(8, 0, 8, 30)       # 09:00–09:30 local
        exc = _exception(_slot(8, 15, 9, 0))  # Overlapping exception
        assert rule.allows(slot, _business_hours(), [exc]) is False

    def test_slot_adjacent_to_exception_not_blocked(self) -> None:
        """Adjacent slots (not overlapping) are not blocked by an exception.

        Half-open intervals: exception ends at 09:00 local, slot starts at 09:00.
        These are adjacent, not overlapping → slot is allowed.
        """
        rule = AvailabilityRule()
        # Exception: 08:00–09:00 local = 07:00–08:00 UTC
        exc = _exception(_slot(7, 0, 8, 0))
        # Slot: 09:00–09:30 local = 08:00–08:30 UTC (adjacent to exception end)
        slot = _slot(8, 0, 8, 30)
        assert rule.allows(slot, _business_hours(), [exc]) is True

    def test_multiple_exceptions_one_overlaps_not_allowed(self) -> None:
        """With multiple exceptions, a single overlap blocks the slot."""
        rule = AvailabilityRule()
        slot = _slot(8, 0, 8, 30)
        exc_no_overlap = _exception(_slot(10, 0, 11, 0))
        exc_overlap = _exception(_slot(8, 15, 9, 0))
        assert rule.allows(slot, _business_hours(), [exc_no_overlap, exc_overlap]) is False

    def test_multiple_exceptions_none_overlap_allowed(self) -> None:
        """When no exception overlaps the slot, it is allowed."""
        rule = AvailabilityRule()
        slot = _slot(8, 0, 8, 30)
        excs = [_exception(_slot(9, 0, 10, 0)), _exception(_slot(10, 0, 11, 0))]
        assert rule.allows(slot, _business_hours(), excs) is True

    def test_slot_on_weekend_blocked(self) -> None:
        """A slot on a closed day (Saturday) is not allowed."""
        rule = AvailabilityRule()
        # 2026-11-07 is Saturday
        sat_slot = TimeSlot(
            start=datetime(2026, 11, 7, 8, 0, tzinfo=UTC),
            end=datetime(2026, 11, 7, 8, 30, tzinfo=UTC),
        )
        assert rule.allows(sat_slot, _business_hours(), []) is False


# ---------------------------------------------------------------------------
# within_opening_hours
# ---------------------------------------------------------------------------

class TestWithinOpeningHours:
    """Tests for the within_opening_hours delegate function."""

    def test_delegates_to_opening_hours_covers(self) -> None:
        """within_opening_hours returns same result as schedule.covers()."""
        hours = _business_hours()
        slot = _slot(8, 0, 8, 30)
        assert within_opening_hours(slot, hours) == hours.covers(slot)

    def test_slot_outside_returns_false(self) -> None:
        hours = _business_hours()
        slot = _slot(5, 0, 6, 0)
        assert within_opening_hours(slot, hours) is False
