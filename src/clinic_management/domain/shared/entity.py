"""Identity equality without imposing dataclass mutability on subclasses."""

from __future__ import annotations

from uuid import UUID


class Entity:
    """Provide identity behavior for concrete entities declaring their ID field.

    Dataclass subclasses must use ``eq=False`` and declare ``id: UUID``.
    Versions belong to concurrently editable aggregate roots, not this base.
    """

    id: UUID

    def same_identity(self, other: Entity) -> bool:
        """Return whether both entities have the same concrete type and UUID.

        Args:
            other: Entity to compare with this instance.

        Returns:
            Whether the concrete entity type and identifier both match.
        """
        return type(self) is type(other) and self.id == other.id

    def __eq__(self, other: object) -> bool:
        """Compare concrete entity identities rather than mutable attributes.

        Args:
            other: Object participating in the equality comparison.

        Returns:
            False for non-entities, otherwise the identity comparison.
        """
        return isinstance(other, Entity) and self.same_identity(other)

    __hash__ = None  # type: ignore[assignment]
