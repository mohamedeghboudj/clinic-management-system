"""Standard-library implementation of the authoritative clock port."""

from datetime import UTC, datetime


class SystemClock:
    """Read the backend host clock; deployment must maintain clock sync."""

    def now(self) -> datetime:
        """Read an aware UTC instant from the operating system.

        Returns:
            The current UTC datetime, without converting client timestamps.
        """
        return datetime.now(UTC)
