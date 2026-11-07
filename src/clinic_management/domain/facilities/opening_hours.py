"""Opening hours configuration for a clinic's weekly schedule.

Models a clinic's regular opening times as a set of weekday-local-time
periods, together with the clinic's IANA timezone.  Coverage checks convert
timezone-aware ``TimeSlot`` instants into the clinic's local time before
comparing against the configured periods.

Design decision — boundary at exactly closing time:
    A slot ending precisely at the closing time is treated as fully covered,
    because the slot uses a half-open ``[start, end)`` interval and the
    closing time is the exclusive upper bound of the period.  Formally:
    *the period covers all instants t such that opens_at <= t < closes_at*.
    This is consistent with ``TimeSlot`` semantics.

Design decision — overnight periods:
    ``OpeningPeriod`` represents a same-day local interval.  Periods that
    cross midnight must be split into two separate periods (one ending at
    midnight, one starting at midnight on the next day).
"""

from __future__ import annotations

import zoneinfo
from dataclasses import dataclass
from datetime import date, time, timedelta

from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot


@dataclass(frozen=True, kw_only=True)
class OpeningPeriod:
    """Immutable same-day local-time opening interval for one weekday.

    Attributes:
        weekday: ISO weekday integer (0 = Monday, 6 = Sunday).
        opens_at: Local time the clinic opens (inclusive).
        closes_at: Local time the clinic closes (exclusive upper bound).
    """

    weekday: int
    opens_at: time
    closes_at: time

    def __post_init__(self) -> None:
        """Validate weekday range and that opens_at < closes_at.

        Raises:
            ValidationError: If weekday is out of range or the period is
                degenerate (opens_at >= closes_at).
        """
        if not isinstance(self.weekday, int) or not 0 <= self.weekday <= 6:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="opening_period.weekday.invalid",
                safe_details={"field": "weekday"},
            )
        if not isinstance(self.opens_at, time) or not isinstance(self.closes_at, time):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="opening_period.time.invalid",
                safe_details={"field": "opens_at"},
            )
        if self.opens_at >= self.closes_at:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="opening_period.interval.invalid",
                safe_details={"field": "opens_at"},
            )


@dataclass(frozen=True, kw_only=True)
class OpeningHours:
    """Immutable weekly opening-hours configuration for a clinic.

    Attributes:
        timezone: IANA timezone identifier (e.g. ``"Africa/Algiers"``).
        periods: Tuple of ``OpeningPeriod`` instances defining when each
            weekday is open.  May be empty (always closed).
    """

    timezone: str
    periods: tuple[OpeningPeriod, ...]

    def __post_init__(self) -> None:
        """Validate the timezone identifier and the periods container.

        Raises:
            ValidationError: If the timezone is unknown or periods is not a
                tuple.
        """
        if not isinstance(self.timezone, str) or not self.timezone:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="opening_hours.timezone.invalid",
                safe_details={"field": "timezone"},
            )
        try:
            zoneinfo.ZoneInfo(self.timezone)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="opening_hours.timezone.unknown",
                safe_details={"field": "timezone"},
            )
        if not isinstance(self.periods, tuple):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="opening_hours.periods.invalid",
                safe_details={"field": "periods"},
            )

    def covers(self, slot: TimeSlot) -> bool:
        """Return True only if the *entire* slot falls within opening hours.

        The slot's aware instants are converted to the clinic's local
        timezone before comparing against the configured periods.

        A slot is covered when every instant from ``slot.start`` (inclusive)
        up to — but not including — ``slot.end`` lies within at least one
        ``OpeningPeriod`` on the matching weekday.

        A slot that spans multiple weekdays is handled by converting both
        endpoints separately and verifying each portion is covered.

        Args:
            slot: Timezone-aware half-open interval to test.

        Returns:
            True if the slot is fully covered by opening hours.
        """
        tz = zoneinfo.ZoneInfo(self.timezone)
        local_start = slot.start.astimezone(tz)
        # slot.end is exclusive, so the last covered instant is just before it.
        # For coverage checking we test the interval using local calendar dates.
        local_end = slot.end.astimezone(tz)

        # Collect all local dates spanned by the slot.
        dates = _dates_spanned(local_start, local_end, tz)

        for local_date in dates:
            weekday = local_date.weekday()

            # Determine the portion of the slot that falls on this date.
            day_start = local_start if local_date == local_start.date() else _midnight(local_date, tz)

            # The end of the coverage check on this date:
            # either the actual slot end or midnight of the next day.
            next_day = _midnight(_next_date(local_date), tz)
            day_end = local_end if local_end <= next_day else next_day

            # Find periods for this weekday.
            day_periods = [p for p in self.periods if p.weekday == weekday]
            if not day_periods:
                return False

            # The day portion must be fully covered by one or more periods.
            # We test coverage of [day_start.time(), day_end.time()) against
            # the union of day_periods.  Because we work with same-day times
            # we can compare time objects directly.
            if not _time_range_covered(
                _as_time(day_start),
                _as_time(day_end),
                _exact_midnight(local_date, day_end),
                day_periods,
            ):
                return False

        return True


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _dates_spanned(
    local_start: object,  # datetime in local tz
    local_end: object,  # datetime in local tz
    tz: zoneinfo.ZoneInfo,
) -> list[date]:
    """Return all calendar dates touched by [local_start, local_end)."""
    from datetime import datetime as _dt

    assert isinstance(local_start, _dt)
    assert isinstance(local_end, _dt)

    result: list[date] = []
    current = local_start.date()
    end_date = local_end.date()
    # If local_end is exactly midnight it belongs to the previous date's slot
    if _as_time(local_end) == time(0, 0) and local_end > local_start:
        end_date = _prev_date(end_date)

    while current <= end_date:
        result.append(current)
        current = _next_date(current)
    return result


def _midnight(d: date, tz: zoneinfo.ZoneInfo) -> object:
    """Return midnight (00:00) on *d* in *tz* as an aware datetime."""
    from datetime import datetime as _dt

    return _dt(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)


def _next_date(d: date) -> date:
    return d + timedelta(days=1)


def _prev_date(d: date) -> date:
    return d - timedelta(days=1)


def _as_time(dt: object) -> time:
    """Extract the local time portion from a datetime."""
    from datetime import datetime as _dt

    assert isinstance(dt, _dt)
    return dt.time().replace(tzinfo=None)


def _exact_midnight(local_date: date, local_end: object) -> bool:
    """Return True if *local_end* is exactly midnight of the *next* day."""
    from datetime import datetime as _dt

    assert isinstance(local_end, _dt)
    return local_end.date() == _next_date(local_date) and local_end.time() == time(0, 0)


def _time_range_covered(
    t_start: time,
    t_end: time,
    end_is_midnight_next_day: bool,
    periods: list[OpeningPeriod],
) -> bool:
    """Return True if [t_start, t_end) is fully covered by *periods*.

    When *end_is_midnight_next_day* is True, t_end is treated as the
    end-of-day boundary (i.e., covers up to but not including midnight).

    Args:
        t_start: Inclusive start time.
        t_end: Exclusive end time (may be ``time(0, 0)`` for midnight sentinel).
        end_is_midnight_next_day: Treat end as end-of-day if True.
        periods: Candidate opening periods for this weekday.

    Returns:
        True if the range is fully covered.
    """
    # Normalise sentinel: midnight-next-day means the slot runs until the
    # end of the opening period whose closes_at may be as late as time(23,59,…)
    # or the period covers the full day.  We represent "end of day" as
    # time(24,0) conceptually by using fractional-minutes comparison.
    # Simpler: convert to minutes-since-midnight for arithmetic.
    start_m = _to_minutes(t_start)
    end_m = 24 * 60 if end_is_midnight_next_day else _to_minutes(t_end)

    # Merge period coverage into sorted intervals and check full coverage.
    covered_intervals: list[tuple[int, int]] = []
    for p in periods:
        covered_intervals.append((_to_minutes(p.opens_at), _to_minutes(p.closes_at)))

    covered_intervals.sort()
    # Walk through sorted intervals and verify continuous coverage.
    covered_up_to = start_m
    for p_start, p_end in covered_intervals:
        if p_start > covered_up_to:
            # Gap between current coverage and next period.
            return False
        covered_up_to = max(covered_up_to, p_end)
        if covered_up_to >= end_m:
            return True

    return covered_up_to >= end_m


def _to_minutes(t: time) -> int:
    """Convert a time to minutes since midnight."""
    return t.hour * 60 + t.minute
