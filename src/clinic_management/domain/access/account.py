"""UserAccount domain entity for application authentication."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.validation import require_non_empty

_REPR_SAFE_FIELDS = frozenset(
    {"id", "version", "person_id", "username", "enabled", "auth_version", "must_change_password"}
)


@dataclass(eq=False, kw_only=True)
class UserAccount(Entity):
    """Domain entity representing a user's application credentials and status.

    The ``password_hash`` field stores an encoded hash produced by the
    PasswordHasher port — never a plaintext password.  It is intentionally
    excluded from ``__repr__`` to prevent accidental exposure in logs.

    Attributes:
        id: Unique identifier for this account.
        version: Aggregate root version for optimistic concurrency (defaults to 0).
        person_id: Identifier of the associated Person entity.
        username: Unique login username.
        password_hash: Encoded password hash (never a plaintext password).
        enabled: Whether this account may authenticate.
        auth_version: Monotonic counter invalidating sessions on security changes.
        must_change_password: Whether the user must change their password on next login.
    """

    id: UUID
    version: int = 0
    person_id: UUID
    username: str
    password_hash: str
    enabled: bool = True
    auth_version: int = 1
    must_change_password: bool = False

    def __post_init__(self) -> None:
        """Validate identifiers, version, username, and hash format.

        Raises:
            ValidationError: If any field fails its local invariant check.
        """
        require_uuid(self.id)
        require_uuid(self.person_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="account.version.invalid",
                safe_details={"field": "version"},
            )

        clean_username = require_non_empty(self.username, field="username", max_length=150)

        clean_hash = require_non_empty(self.password_hash, field="password_hash", max_length=500)

        if type(self.enabled) is not bool:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="account.enabled.invalid",
                safe_details={"field": "enabled"},
            )

        if type(self.auth_version) is not int or self.auth_version < 1:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="account.auth_version.invalid",
                safe_details={"field": "auth_version"},
            )

        if type(self.must_change_password) is not bool:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="account.must_change_password.invalid",
                safe_details={"field": "must_change_password"},
            )

        object.__setattr__(self, "username", clean_username)
        object.__setattr__(self, "password_hash", clean_hash)

    def __repr__(self) -> str:
        """Return a representation that excludes the password hash.

        Returns:
            A diagnostic string with only safe, non-sensitive fields.
        """
        return (
            f"UserAccount(id={self.id!r}, username={self.username!r}, "
            f"enabled={self.enabled!r}, auth_version={self.auth_version!r})"
        )

    def disable(self) -> None:
        """Disable this account, preventing further authentication.

        Raises:
            InvalidTransitionError: If the account is already disabled.
        """
        if not self.enabled:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="account.already_disabled",
                safe_details={"account_id": str(self.id)},
            )
        self.enabled = False
        self._bump_auth_version()

    def enable(self) -> None:
        """Re-enable a previously disabled account.

        Raises:
            InvalidTransitionError: If the account is already enabled.
        """
        if self.enabled:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="account.already_enabled",
                safe_details={"account_id": str(self.id)},
            )
        self.enabled = True

    def replace_password_hash(self, encoded_hash: str) -> None:
        """Replace the stored password hash with a newly computed one.

        The caller is responsible for producing ``encoded_hash`` through the
        PasswordHasher port.  Plaintext passwords must never be passed here.
        Replacing the hash also invalidates all existing sessions.

        Args:
            encoded_hash: Encoded hash string produced by the PasswordHasher port.

        Raises:
            ValidationError: If the supplied string is empty or invalid.
        """
        clean = require_non_empty(encoded_hash, field="password_hash", max_length=500)
        self.password_hash = clean
        self._bump_auth_version()

    def invalidate_sessions(self) -> None:
        """Increment the authentication version to invalidate all open sessions.

        Any session whose ``auth_version`` no longer matches the account's
        current ``auth_version`` must be rejected by the server.
        """
        self._bump_auth_version()

    def _bump_auth_version(self) -> None:
        """Increment auth_version by one.

        Returns:
            None
        """
        self.auth_version += 1

