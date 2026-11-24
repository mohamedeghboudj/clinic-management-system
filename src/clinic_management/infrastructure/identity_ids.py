"""Random UUID identity adapter without document-numbering behavior."""

from uuid import UUID, uuid4


class UuidGenerator:
    """Generate UUID version 4 identifiers using the standard library."""

    def new_id(self) -> UUID:
        """Generate a new UUID for an entity or command envelope.

        Returns:
            A newly generated version 4 UUID.
        """
        return uuid4()
