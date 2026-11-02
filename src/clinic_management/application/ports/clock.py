"""Clock dependency for reproducible authoritative timestamps."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Supply UTC instants without hiding time dependencies in domain methods."""

    def now(self) -> datetime:
        """Read the current authoritative aware UTC instant.

        Returns:
            A timezone-aware datetime with zero UTC offset.
        """
        ...
