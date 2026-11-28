"""Repository ports for Session entities."""

from __future__ import annotations

import abc
from datetime import datetime
from uuid import UUID

from clinic_management.domain.access.session import Session


class SessionRepository(abc.ABC):
    """Abstract repository for Session entities."""

    @abc.abstractmethod
    def get(self, session_id: UUID) -> Session | None:
        """Retrieve a Session by its unique identifier.

        Args:
            session_id: The unique identifier of the Session.

        Returns:
            The Session entity, or None if not found.
        """

    @abc.abstractmethod
    def add(self, session: Session) -> None:
        """Persist a new Session entity.

        Args:
            session: The Session to add.

        Raises:
            ConflictError: If a Session with the same ID already exists.
        """

    @abc.abstractmethod
    def revoke(self, session_id: UUID, *, at: datetime) -> None:
        """Revoke a session by its identifier.

        Args:
            session_id: Identifier of the session to revoke.
            at: UTC timestamp for the revocation record.

        Raises:
            NotFoundError: If no session with the given ID exists.
        """
