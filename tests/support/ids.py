"""Explicit deterministic UUID sequences for fixtures."""

from collections.abc import Sequence
from uuid import UUID

from clinic_management.domain.shared._invariants import require_uuid


class SequenceIdGenerator:
    """Consume copied fixture UUIDs and fail clearly instead of randomizing."""

    def __init__(self, values: Sequence[UUID]) -> None:
        """Copy and validate the supplied finite identifier sequence.

        Args:
            values: Unique fixture IDs in the intended consumption order.

        Raises:
            ValueError: If duplicate identifiers are supplied.
            ValidationError: If a supplied identifier is not a UUID.
        """
        self._values = tuple(values)
        self._index = 0
        for value in self._values:
            require_uuid(value)
        if len(set(self._values)) != len(self._values):
            raise ValueError("Fixture identifiers must be unique")

    def new_id(self) -> UUID:
        """Consume the next supplied fixture identifier.

        Returns:
            The next UUID in the copied sequence.

        Raises:
            RuntimeError: If the explicit sequence is exhausted.
        """
        if self._index >= len(self._values):
            raise RuntimeError("Fixture identifier sequence exhausted")
        value = self._values[self._index]
        self._index += 1
        return value
