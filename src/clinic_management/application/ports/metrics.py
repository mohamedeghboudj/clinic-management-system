"""Replaceable low-cardinality measurement boundary."""

from typing import Protocol


class MetricsRecorder(Protocol):
    """Collect operation/outcome metrics without patient or user labels."""

    def increment(self, name: str, *, outcome: str) -> None:
        """Record one completed observation.

        Args:
            name: Registered operation name.
            outcome: Registered terminal outcome.
        """
        ...

    def observe(self, name: str, seconds: float, *, outcome: str) -> None:
        """Record an elapsed monotonic duration in seconds.

        Args:
            name: Registered operation name.
            seconds: Finite nonnegative duration.
            outcome: Registered terminal outcome.
        """
        ...
