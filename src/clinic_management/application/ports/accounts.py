"""Repository ports for UserAccount and ClinicMembership entities."""

from __future__ import annotations

import abc
from uuid import UUID

from clinic_management.domain.access.account import UserAccount
from clinic_management.domain.access.membership import ClinicMembership


class AccountRepository(abc.ABC):
    """Abstract repository for UserAccount and ClinicMembership entities."""

    @abc.abstractmethod
    def get_by_username(self, username: str) -> UserAccount | None:
        """Look up a UserAccount by its unique username.

        Args:
            username: Login username to search for.

        Returns:
            The UserAccount entity, or None if not found.
        """

    @abc.abstractmethod
    def add(self, account: UserAccount) -> None:
        """Persist a new UserAccount entity.

        Args:
            account: The UserAccount to add.

        Raises:
            ConflictError: If an account with the same ID or username exists.
        """

    @abc.abstractmethod
    def get_membership(self, account_id: UUID, clinic_id: UUID) -> ClinicMembership | None:
        """Retrieve the ClinicMembership for an account in a specific clinic.

        Args:
            account_id: Identifier of the UserAccount.
            clinic_id: Identifier of the clinic.

        Returns:
            The ClinicMembership entity, or None if not found.
        """

    @abc.abstractmethod
    def add_membership(self, membership: ClinicMembership) -> None:
        """Persist a new ClinicMembership entity.

        Args:
            membership: The ClinicMembership to add.

        Raises:
            ConflictError: If a membership with the same ID already exists.
        """

    @abc.abstractmethod
    def save_membership(self, membership: ClinicMembership, *, expected_version: int) -> None:
        """Persist changes to an existing ClinicMembership entity.

        Args:
            membership: The ClinicMembership with updated state.
            expected_version: Version for optimistic concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match expected_version.
            NotFoundError: If no ClinicMembership with this ID exists.
        """

    @abc.abstractmethod
    def save(self, account: UserAccount, *, expected_version: int) -> None:
        """Persist changes to an existing UserAccount entity.

        Args:
            account: The UserAccount with updated state.
            expected_version: Version for optimistic concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match expected_version.
            NotFoundError: If no UserAccount with this ID exists.
        """
