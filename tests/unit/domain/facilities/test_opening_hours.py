"""Unit tests for OpeningPeriod and OpeningHours."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, timezone

import pytest

from clinic_management.domain.facilities.opening_hours import (
    OpeningHours,
    OpeningPeriod,
)
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot

# IANA timezone identifiers used in tests.
_ALGIERS = "Africa/Algiers"
_PARIS = "Europe/Paris"
_LONDON = "Europe/London"


def _make_hours(
    timezone: str = _ALGIERS,
    periods: list[OpeningPeriod] | None = None,
) -> OpeningHours:
    """Helper to construct OpeningHours with sensible defaults."""
    if periods is None:
        # Monday–Friday 08:00–17:00
        periods = [OpeningPeriod(weekday=d, opens_at=time(8), closes_at=time(17)) for d in range(5)]
    return OpeningHours(timezone=timezone, periods=tuple(periods))


def _utc_slot(
    year: int,
    month: int,
    day: int,
    h_start: int,
    m_start: int,
    h_end: int,
    m_end: int,
) -> TimeSlot:
    """Build a UTC TimeSlot."""
    return TimeSlot(
        start=datetime(year, month, day, h_start, m_start, tzinfo=UTC),
        end=datetime(year, month, day, h_end, m_end, tzinfo=UTC),
    )


class TestOpeningPeriodConstruction:
    """Tests for OpeningPeriod value object validation."""

    def test_valid_period_accepted(self) -> None:
        """A valid weekday-time period is accepted."""
        p = OpeningPeriod(weekday=0, opens_at=time(8), closes_at=time(17))
        assert p.weekday == 0
        assert p.opens_at == time(8)
        assert p.closes_at == time(17)

    @pytest.mark.parametrize("weekday", [-1, 7, 10])
    def test_invalid_weekday_rejected(self, weekday: int) -> None:
        """Weekday outside 0–6 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OpeningPeriod(weekday=weekday, opens_at=time(8), closes_at=time(17))
        assert exc_info.value.safe_details["field"] == "weekday"

    def test_opens_at_equal_closes_at_rejected(self) -> None:
        """Zero-length period is rejected."""
        with pytest.raises(ValidationError):
            OpeningPeriod(weekday=0, opens_at=time(8), closes_at=time(8))

    def test_opens_at_after_closes_at_rejected(self) -> None:
        """Reversed times are rejected."""
        with pytest.raises(ValidationError):
            OpeningPeriod(weekday=0, opens_at=time(17), closes_at=time(8))

    def test_period_is_immutable(self) -> None:
        """OpeningPeriod is a frozen dataclass."""
        p = OpeningPeriod(weekday=1, opens_at=time(9), closes_at=time(18))
        with pytest.raises((TypeError, AttributeError)):
            p.weekday = 2  # type: ignore[misc]


class TestOpeningHoursConstruction:
    """Tests for OpeningHours value object validation."""

    def test_valid_schedule_accepted(self) -> None:
        """Valid timezone and periods are accepted."""
        hours = _make_hours()
        assert hours.timezone == _ALGIERS

    def test_unknown_timezone_rejected(self) -> None:
        """An unrecognised IANA timezone raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OpeningHours(timezone="Invalid/Timezone", periods=())
        assert exc_info.value.safe_details["field"] == "timezone"

    def test_empty_timezone_rejected(self) -> None:
        """An empty timezone string raises ValidationError."""
        with pytest.raises(ValidationError):
            OpeningHours(timezone="", periods=())

    def test_empty_periods_accepted(self) -> None:
        """Zero periods (always closed) is a valid configuration."""
        hours = OpeningHours(timezone=_ALGIERS, periods=())
        assert hours.periods == ()

    def test_schedule_is_immutable(self) -> None:
        """OpeningHours is frozen."""
        hours = _make_hours()
        with pytest.raises((TypeError, AttributeError)):
            hours.timezone = _PARIS  # type: ignore[misc]


class TestOpeningHoursCovers:
    """Tests for OpeningHours.covers(slot: TimeSlot) -> bool."""

    # Africa/Algiers is UTC+1 year-round (no DST).

    def test_slot_fully_inside_opening_hours_covered(self) -> None:
        """A slot fully within opening hours returns True.

        Africa/Algiers = UTC+1.  Clinic opens 08:00 local = 07:00 UTC.
        A slot 09:00–10:00 UTC = 10:00–11:00 local → inside [08:00, 17:00).
        """
        hours = _make_hours(_ALGIERS)
        # 2026-11-09 is a Monday (weekday 0).
        slot = _utc_slot(2026, 11, 9, 9, 0, 10, 0)
        assert hours.covers(slot) is True

    def test_slot_starting_before_opening_not_covered(self) -> None:
        """A slot that starts before opening time is not covered.

        09:00 local Monday, clinic opens 10:00 local.
        """
        p = OpeningPeriod(weekday=0, opens_at=time(10), closes_at=time(17))
        hours = OpeningHours(timezone=_ALGIERS, periods=(p,))
        # 08:30 local = 07:30 UTC  (UTC+1)
        slot = TimeSlot(
            start=datetime(2026, 11, 9, 7, 30, tzinfo=UTC),
            end=datetime(2026, 11, 9, 9, 0, tzinfo=UTC),
        )
        assert hours.covers(slot) is False

    def test_slot_ending_after_closing_not_covered(self) -> None:
        """A slot that ends after closing time is not covered.

        Clinic closes 17:00 local.  Slot ends at 17:30 local.
        """
        hours = _make_hours(_ALGIERS)
        # 16:00–17:30 local = 15:00–16:30 UTC (UTC+1)
        slot = TimeSlot(
            start=datetime(2026, 11, 9, 15, 0, tzinfo=UTC),
            end=datetime(2026, 11, 9, 16, 30, tzinfo=UTC),
        )
        assert hours.covers(slot) is False

    def test_slot_exactly_at_boundaries_covered(self) -> None:
        """A slot from opening to closing is fully covered.

        08:00–17:00 local = 07:00–16:00 UTC (UTC+1).
        """
        hours = _make_hours(_ALGIERS)
        slot = TimeSlot(
            start=datetime(2026, 11, 9, 7, 0, tzinfo=UTC),
            end=datetime(2026, 11, 9, 16, 0, tzinfo=UTC),
        )
        assert hours.covers(slot) is True

    def test_slot_on_closed_weekday_not_covered(self) -> None:
        """A slot on a weekday with no periods is not covered.

        Default schedule is Mon–Fri.  2026-11-07 is a Saturday (weekday 5).
        """
        hours = _make_hours(_ALGIERS)  # Mon–Fri only
        slot = _utc_slot(2026, 11, 7, 9, 0, 10, 0)
        assert hours.covers(slot) is False

    def test_empty_schedule_never_covers(self) -> None:
        """With no periods the schedule never covers any slot."""
        hours = OpeningHours(timezone=_ALGIERS, periods=())
        slot = _utc_slot(2026, 11, 9, 9, 0, 10, 0)
        assert hours.covers(slot) is False

    def test_multiple_periods_covering_different_parts_of_day(self) -> None:
        """Multiple periods on the same day are unioned correctly.

        Morning session 08:00–12:00 and afternoon 14:00–17:00.
        A slot from 09:00–11:00 local should be covered.
        """
        morning = OpeningPeriod(weekday=0, opens_at=time(8), closes_at=time(12))
        afternoon = OpeningPeriod(weekday=0, opens_at=time(14), closes_at=time(17))
        hours = OpeningHours(timezone=_ALGIERS, periods=(morning, afternoon))
        # 09:00–11:00 local = 08:00–10:00 UTC (UTC+1)
        slot = _utc_slot(2026, 11, 9, 8, 0, 10, 0)
        assert hours.covers(slot) is True

    def test_slot_in_gap_between_periods_not_covered(self) -> None:
        """A slot that falls in a gap between two periods is not covered.

        Morning 08:00–12:00, afternoon 14:00–17:00.
        A slot 12:30–13:30 local falls in the gap.
        """
        morning = OpeningPeriod(weekday=0, opens_at=time(8), closes_at=time(12))
        afternoon = OpeningPeriod(weekday=0, opens_at=time(14), closes_at=time(17))
        hours = OpeningHours(timezone=_ALGIERS, periods=(morning, afternoon))
        # 12:30–13:30 local = 11:30–12:30 UTC (UTC+1)
        slot = _utc_slot(2026, 11, 9, 11, 30, 12, 30)
        assert hours.covers(slot) is False

    def test_slot_crossing_midnight_not_covered_by_same_day_period(self) -> None:
        """A slot crossing midnight is not covered when only one day is configured.

        A slot from 23:00 Mon to 01:00 Tue is covered only if both weekdays
        have appropriate periods.
        """
        # Only Monday configured
        p_mon = OpeningPeriod(weekday=0, opens_at=time(8), closes_at=time(23, 59))
        hours = OpeningHours(timezone=_ALGIERS, periods=(p_mon,))
        # 23:00 Mon to 01:00 Tue (local UTC+1) = 22:00 Mon to 00:00 Tue UTC
        slot = TimeSlot(
            start=datetime(2026, 11, 9, 22, 0, tzinfo=UTC),
            end=datetime(2026, 11, 10, 0, 0, tzinfo=UTC),
        )
        assert hours.covers(slot) is False

    def test_timezone_conversion_applied_correctly(self) -> None:
        """Coverage check converts aware slot instants to the clinic timezone.

        Europe/London in winter is UTC+0.  Africa/Algiers is UTC+1.
        A slot that looks inside clinic hours in UTC may be outside in
        Africa/Algiers local time.
        """
        # Clinic: Algiers (UTC+1), opens 08:00 local.
        # Slot: 06:30–07:30 UTC = 07:30–08:30 local → starts before opening.
        hours = _make_hours(_ALGIERS)
        slot = TimeSlot(
            start=datetime(2026, 11, 9, 6, 30, tzinfo=UTC),
            end=datetime(2026, 11, 9, 7, 30, tzinfo=UTC),
        )
        assert hours.covers(slot) is False

    def test_slot_given_in_non_utc_timezone_handled_correctly(self) -> None:
        """A slot expressed in a non-UTC timezone is converted before comparison."""
        hours = _make_hours(_ALGIERS)
        paris_tz = timezone(timedelta(hours=2))  # Approximate Paris winter offset
        # 10:00–11:00 Paris (UTC+2) = 08:00–09:00 UTC = 09:00–10:00 Algiers local
        slot = TimeSlot(
            start=datetime(2026, 11, 9, 10, 0, tzinfo=paris_tz),
            end=datetime(2026, 11, 9, 11, 0, tzinfo=paris_tz),
        )
        assert hours.covers(slot) is True
