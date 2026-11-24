"""Identifier dependency, separate from business document numbering."""

from typing import Protocol
from uuid import UUID


class IdGenerator(Protocol):
    """Supply entity identifiers, never invoice or patient sequence numbers."""

    def new_id(self) -> UUID:
        """Generate the next entity identifier.

        Returns:
            A UUID suitable for identifying a new entity.
        """
        ...
