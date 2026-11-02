"""IdentityProvider port: interface for authentication and session resolution."""

from __future__ import annotations

import abc
from datetime import datetime

# AuthenticatedSession is imported lazily via TYPE_CHECKING to avoid a
# circular dependency between ports and contracts.
from typing import TYPE_CHECKING
from uuid import UUID

from clinic_management.domain.access.principal import Principal

if TYPE_CHECKING:
    from clinic_management.application.contracts.access import AuthenticatedSession


class IdentityProvider(abc.ABC):
    """Abstract port for authentication and principal resolution.

    Concrete implementations belong to the infrastructure layer (Week 2).
    This port is deliberately separate from M1's IdGenerator contract.

    The contract specifies the failure modes that callers must handle:
    invalid credentials, disabled accounts, expired sessions, and revoked
    sessions are all communicated through ``AuthenticationError`` from the
    shared errors module.
    """

    @abc.abstractmethod
    def authenticate(
        self,
        username: str,
        password: str,
        *,
        at: datetime,
    ) -> AuthenticatedSession:
        """Authenticate a user and return an active session.

        Args:
            username: The user's login name.
            password: The plaintext password to verify.
            at: Explicit reference time for session expiry calculation.

        Returns:
            An ``AuthenticatedSession`` containing the principal and tokens.

        Raises:
            AuthenticationError: If the credentials are invalid, the account
                is disabled, or any other authentication failure occurs.
        """

    @abc.abstractmethod
    def resolve_principal(
        self,
        access_token: str,
        *,
        clinic_id: UUID,
        at: datetime,
    ) -> Principal:
        """Resolve a verified Principal from an access token.

        The returned Principal is constructed by the server after verifying
        the token, session validity, and clinic membership.  It must never be
        constructed from client-supplied JSON.

        Args:
            access_token: The opaque access token issued at authentication.
            clinic_id: The clinic context the caller is requesting access to.
            at: Explicit reference time for expiry and version evaluation.

        Returns:
            A verified, immutable ``Principal``.

        Raises:
            AuthenticationError: If the token is invalid, expired, revoked,
                or the membership is not found for the given clinic.
        """

    @abc.abstractmethod
    def revoke(self, session_id: UUID, *, at: datetime) -> None:
        """Revoke a session, preventing further use of its tokens.

        Args:
            session_id: Identifier of the session to revoke.
            at: Explicit reference time for the revocation timestamp.

        Raises:
            NotFoundError: If no session with the given ID exists.
            AuthenticationError: If the session is already revoked.
        """

