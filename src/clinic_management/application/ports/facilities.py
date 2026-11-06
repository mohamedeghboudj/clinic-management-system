"""Abstract repository ports for the facilities domain.

These interfaces define the data-access contract that use cases depend on.
They are implemented by infrastructure adapters (Week 2+).
"""

from __future__ import annotations

import abc
from uuid import UUID

from clinic_management.application.ports.pagination import Page, PageRequest
from clinic_management.domain.facilities.clinic import Clinic
from clinic_management.domain.facilities.room import Room


class ClinicRepository(abc.ABC):
    """Abstract repository for ``Clinic`` aggregate roots."""

    @abc.abstractmethod
    def get(self, clinic_id: UUID) -> Clinic | None:
        """Retrieve a clinic by its unique identifier.

        Args:
            clinic_id: Unique clinic identifier.

        Returns:
            The ``Clinic`` entity, or ``None`` if not found.
        """

    @abc.abstractmethod
    def add(self, clinic: Clinic) -> None:
        """Persist a new clinic.

        Args:
            clinic: The new ``Clinic`` entity to store.

        Raises:
            ConflictError: If a clinic with the same ID already exists.
        """

    @abc.abstractmethod
    def save(self, clinic: Clinic, *, expected_version: int) -> None:
        """Persist changes to an existing clinic.

        Args:
            clinic: The ``Clinic`` with updated state.
            expected_version: The version the caller read; used for optimistic
                concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match.
            NotFoundError: If no clinic with this ID exists.
        """


class RoomRepository(abc.ABC):
    """Abstract repository for ``Room`` entities within a clinic."""

    @abc.abstractmethod
    def get(self, clinic_id: UUID, room_id: UUID) -> Room | None:
        """Retrieve a room by clinic and room identifiers.

        Args:
            clinic_id: Clinic that owns the room.
            room_id: Unique room identifier.

        Returns:
            The ``Room`` entity, or ``None`` if not found.
        """

    @abc.abstractmethod
    def add(self, room: Room) -> None:
        """Persist a new room.

        Args:
            room: The new ``Room`` entity to store.

        Raises:
            ConflictError: If a room with the same ID already exists.
        """

    @abc.abstractmethod
    def list_active(self, clinic_id: UUID, page: PageRequest) -> Page[Room]:
        """Return a paginated list of active rooms in the given clinic.

        Args:
            clinic_id: Clinic whose rooms to list.
            page: Pagination parameters.

        Returns:
            A page of ``Room`` entities with status ACTIVE.
        """

    @abc.abstractmethod
    def save(self, room: Room, *, expected_version: int) -> None:
        """Persist changes to an existing room.

        Args:
            room: The ``Room`` with updated state.
            expected_version: The version the caller read; used for optimistic
                concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match.
            NotFoundError: If no room with this ID exists.
        """
