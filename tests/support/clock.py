"""A controllable clock that does not depend on wall time."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from clinic_management.domain.shared._invariants import require_utc
from clinic_management.domain.shared.errors import ValidationError


@dataclass(kw_only=True)
class FrozenClock:
    """Supply an explicitly controlled aware UTC instant."""

    current: datetime

    def __post_init__(self) -> None:
        """Require an aware UTC starting point.

        Raises:
            ValidationError: If the initial timestamp is not aware UTC.
        """
        require_utc(self.current)

    def now(self) -> datetime:
        """Read the configured instant without advancing it.

        Returns:
            The current deterministic UTC timestamp.
        """
        return self.current

    def advance(self, delta: timedelta) -> None:
        """Advance a test clock monotonically.

        Args:
            delta: Nonnegative amount of simulated elapsed time.

        Raises:
            ValidationError: If a negative duration is supplied.
        """
        if delta < timedelta(0):
            raise ValidationError(code="INVALID_VALUE", message_key="clock.delta.invalid")
        self.current += delta
