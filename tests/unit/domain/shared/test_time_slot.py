"""Unit tests for the TimeSlot value object."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot, require_aware

# Fixed timestamps used throughout tests for determinism.
_TZ_UTC = UTC
_TZ_PLUS1 = timezone(timedelta(hours=1))
_TZ_PLUS2 = timezone(timedelta(hours=2))

T0 = datetime(2026, 11, 6, 8, 0, tzinfo=_TZ_UTC)   # 08:00 UTC
T1 = datetime(2026, 11, 6, 9, 0, tzinfo=_TZ_UTC)   # 09:00 UTC
T2 = datetime(2026, 11, 6, 10, 0, tzinfo=_TZ_UTC)  # 10:00 UTC
T3 = datetime(2026, 11, 6, 11, 0, tzinfo=_TZ_UTC)  # 11:00 UTC


class TestRequireAware:
    """Tests for the require_aware helper function."""

    def test_aware_datetime_accepted(self) -> None:
        """An aware datetime is returned unchanged."""
        result = require_aware(T0, "start")
        assert result is T0

    def test_naive_datetime_rejected(self) -> None:
        """A naive datetime raises ValidationError."""
        naive = datetime(2026, 11, 6, 8, 0)
        with pytest.raises(ValidationError) as exc_info:
            require_aware(naive, "start")
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "start"

    def test_non_datetime_rejected(self) -> None:
        """A non-datetime value raises ValidationError."""
        with pytest.raises(ValidationError):
            require_aware("2026-11-06T08:00:00Z", "start")  # type: ignore[arg-type]

    def test_aware_different_timezone_accepted(self) -> None:
        """Any timezone-aware datetime is accepted regardless of offset."""
        aware_plus1 = datetime(2026, 11, 6, 9, 0, tzinfo=_TZ_PLUS1)
        result = require_aware(aware_plus1, "end")
        assert result is aware_plus1


class TestTimeSlotConstruction:
    """Tests for TimeSlot construction and validation."""

    def test_valid_slot_accepted(self) -> None:
        """A valid half-open interval is accepted."""
        slot = TimeSlot(start=T0, end=T1)
        assert slot.start == T0
        assert slot.end == T1

    def test_start_equal_end_rejected(self) -> None:
        """Zero-duration slot (start == end) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TimeSlot(start=T0, end=T0)
        assert exc_info.value.code == "INVALID_VALUE"

    def test_start_after_end_rejected(self) -> None:
        """Reversed interval (start > end) is rejected."""
        with pytest.raises(ValidationError):
            TimeSlot(start=T1, end=T0)

    def test_naive_start_rejected(self) -> None:
        """Naive start datetime raises ValidationError."""
        naive = datetime(2026, 11, 6, 8, 0)
        with pytest.raises(ValidationError):
            TimeSlot(start=naive, end=T1)

    def test_naive_end_rejected(self) -> None:
        """Naive end datetime raises ValidationError."""
        naive = datetime(2026, 11, 6, 9, 0)
        with pytest.raises(ValidationError):
            TimeSlot(start=T0, end=naive)

    def test_slot_is_immutable(self) -> None:
        """TimeSlot is a frozen dataclass and cannot be mutated."""
        slot = TimeSlot(start=T0, end=T1)
        with pytest.raises((TypeError, AttributeError)):
            slot.start = T2  # type: ignore[misc]


class TestTimeSlotOverlaps:
    """Tests for TimeSlot.overlaps() using half-open interval semantics."""

    def test_overlapping_slots_detected(self) -> None:
        """Two slots sharing time overlap."""
        a = TimeSlot(start=T0, end=T2)   # [08:00, 10:00)
        b = TimeSlot(start=T1, end=T3)   # [09:00, 11:00)
        assert a.overlaps(b) is True
        assert b.overlaps(a) is True

    def test_adjacent_slots_do_not_overlap(self) -> None:
        """Adjacent half-open intervals sharing only an endpoint do NOT overlap."""
        a = TimeSlot(start=T0, end=T1)   # [08:00, 09:00)
        b = TimeSlot(start=T1, end=T2)   # [09:00, 10:00)
        assert a.overlaps(b) is False
        assert b.overlaps(a) is False

    def test_completely_separate_slots_do_not_overlap(self) -> None:
        """Non-adjacent slots with a gap do not overlap."""
        a = TimeSlot(start=T0, end=T1)   # [08:00, 09:00)
        b = TimeSlot(start=T2, end=T3)   # [10:00, 11:00)
        assert a.overlaps(b) is False
        assert b.overlaps(a) is False

    def test_identical_slots_overlap(self) -> None:
        """Two identical slots fully overlap."""
        a = TimeSlot(start=T0, end=T2)
        b = TimeSlot(start=T0, end=T2)
        assert a.overlaps(b) is True

    def test_contained_slot_overlaps_container(self) -> None:
        """A slot fully inside another overlaps it."""
        outer = TimeSlot(start=T0, end=T3)   # [08:00, 11:00)
        inner = TimeSlot(start=T1, end=T2)   # [09:00, 10:00)
        assert outer.overlaps(inner) is True
        assert inner.overlaps(outer) is True

    def test_overlaps_uses_aware_comparison_across_timezones(self) -> None:
        """Timezone-aware datetimes representing the same instant overlap."""
        # 09:00 UTC == 10:00 +01:00
        a = TimeSlot(start=T0, end=T1)   # [08:00, 09:00) UTC
        b_start = datetime(2026, 11, 6, 9, 30, tzinfo=_TZ_PLUS1)   # 08:30 UTC
        b_end = datetime(2026, 11, 6, 10, 30, tzinfo=_TZ_PLUS1)    # 09:30 UTC
        b = TimeSlot(start=b_start, end=b_end)
        assert a.overlaps(b) is True


class TestTimeSlotContains:
    """Tests for TimeSlot.contains() half-open boundary semantics."""

    def test_start_instant_is_contained(self) -> None:
        """The start instant (inclusive) is inside the slot."""
        slot = TimeSlot(start=T0, end=T2)
        assert slot.contains(T0) is True

    def test_end_instant_is_not_contained(self) -> None:
        """The end instant (exclusive upper bound) is NOT inside the slot."""
        slot = TimeSlot(start=T0, end=T2)
        assert slot.contains(T2) is False

    def test_midpoint_is_contained(self) -> None:
        """An instant strictly between start and end is contained."""
        slot = TimeSlot(start=T0, end=T2)
        assert slot.contains(T1) is True

    def test_before_start_is_not_contained(self) -> None:
        """An instant before start is not contained."""
        slot = TimeSlot(start=T1, end=T2)
        before = T0
        assert slot.contains(before) is False

    def test_after_end_is_not_contained(self) -> None:
        """An instant after end is not contained."""
        slot = TimeSlot(start=T0, end=T1)
        assert slot.contains(T2) is False

    def test_contains_across_timezones(self) -> None:
        """contains() compares aware datetimes correctly across timezones."""
        slot = TimeSlot(start=T0, end=T2)
        # T1 (09:00 UTC) is the same as 10:00 +01:00
        t1_plus1 = datetime(2026, 11, 6, 10, 0, tzinfo=_TZ_PLUS1)
        assert slot.contains(t1_plus1) is True


class TestTimeSlotDuration:
    """Tests for TimeSlot.duration()."""

    def test_one_hour_slot(self) -> None:
        """A one-hour slot has duration of 3600 seconds."""
        slot = TimeSlot(start=T0, end=T1)
        assert slot.duration() == timedelta(hours=1)

    def test_thirty_minute_slot(self) -> None:
        """A 30-minute slot has the correct duration."""
        end = T0 + timedelta(minutes=30)
        slot = TimeSlot(start=T0, end=end)
        assert slot.duration() == timedelta(minutes=30)

    def test_duration_is_positive(self) -> None:
        """Duration is always positive for valid intervals."""
        slot = TimeSlot(start=T0, end=T3)
        assert slot.duration() > timedelta(0)

    def test_different_timezone_representations_same_duration(self) -> None:
        """Duration is timezone-independent for equivalent aware datetimes."""
        start_utc = datetime(2026, 11, 6, 8, 0, tzinfo=_TZ_UTC)
        end_plus1 = datetime(2026, 11, 6, 10, 0, tzinfo=_TZ_PLUS1)  # 09:00 UTC
        slot = TimeSlot(start=start_utc, end=end_plus1)
        assert slot.duration() == timedelta(hours=1)
