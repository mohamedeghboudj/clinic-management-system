"""Delivery boundary for committed update hints."""

from collections.abc import Sequence
from typing import Protocol

from clinic_management.domain.shared.events import DomainEvent


class EventPublisher(Protocol):
    """Deliver committed events at least once; receivers deduplicate IDs."""

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Deliver a bounded batch after its transaction has committed.

        Args:
            events: Metadata-only committed events in dispatch order.

        Raises:
            DependencyUnavailableError: If delivery cannot currently complete.
        """
        ...
