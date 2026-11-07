"""Half-open time interval value object for scheduling use.

Semantics: ``[start, end)`` — start is inclusive, end is exclusive.
Both endpoints must be timezone-aware datetimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from clinic_management.domain.shared.errors import ValidationError


def require_aware(value: datetime, field: str) -> datetime:
    """Require a timezone-aware datetime, rejecting naive values.

    Args:
        value: Datetime instance to validate.
        field: Field name used in the error detail for context.

    Returns:
        The same datetime if it is timezone-aware.

    Raises:
        ValidationError: If ``value`` is not a datetime or is naive (no tzinfo).
    """
    if not isinstance(value, datetime):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="time_slot.timestamp.invalid",
            safe_details={"field": field},
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="time_slot.timestamp.naive",
            safe_details={"field": field},
        )
    return value


@dataclass(frozen=True, kw_only=True)
class TimeSlot:
    """Immutable half-open time interval ``[start, end)``.

    Both ``start`` and ``end`` must be timezone-aware datetimes and
    ``start`` must be strictly before ``end``.

    Attributes:
        start: Inclusive beginning of the interval.
        end: Exclusive end of the interval.
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Validate that both endpoints are aware and form a valid interval.

        Raises:
            ValidationError: If either endpoint is naive or if start >= end.
        """
        require_aware(self.start, "start")
        require_aware(self.end, "end")
        if self.start >= self.end:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="time_slot.interval.invalid",
                safe_details={"field": "slot"},
            )

    def overlaps(self, other: TimeSlot) -> bool:
        """Return whether this slot overlaps another using half-open semantics.

        Two adjacent intervals (where one ends exactly where the other begins)
        do NOT overlap.

        Args:
            other: Another time slot to test against.

        Returns:
            True if the intervals share any common instant (excluding the
            boundary where one slot ends and the other starts).
        """
        # Half-open [a.start, a.end) ∩ [b.start, b.end) is non-empty
        # iff a.start < b.end AND b.start < a.end.
        return self.start < other.end and other.start < self.end

    def contains(self, instant: datetime) -> bool:
        """Return whether *instant* falls within this half-open interval.

        An instant equal to ``start`` IS contained. An instant equal to
        ``end`` is NOT contained (exclusive upper bound).

        Args:
            instant: A timezone-aware datetime to test.

        Returns:
            True if ``start <= instant < end``.
        """
        return self.start <= instant < self.end

    def duration(self) -> timedelta:
        """Return the length of the interval as a positive timedelta.

        Returns:
            Positive timedelta representing the gap from start to end.
        """
        return self.end - self.start
