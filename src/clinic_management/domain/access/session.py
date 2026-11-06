"""Session domain entity for managing authenticated user sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(eq=False, kw_only=True)
class Session(Entity):
    """Domain entity representing an authenticated user session.

    The ``refresh_token_hash`` stores a hash of the refresh token — never the
    raw token itself.  Sessions are invalidated when they expire, are revoked,
    or their ``auth_version`` no longer matches the account's current value.

    Attributes:
        id: Unique identifier for this session.
        account_id: Identifier of the associated UserAccount.
        auth_version: Authentication version at the time of session creation.
        refresh_token_hash: Hash of the refresh token (never the raw token).
        created_at: UTC timestamp when the session was created.
        expires_at: UTC timestamp after which the session is no longer valid.
        revoked_at: UTC timestamp when the session was revoked, or None.
    """

    id: UUID
    account_id: UUID
    auth_version: int
    refresh_token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate all identifiers, timestamps, and version on construction.

        Raises:
            ValidationError: If any field has an invalid type or value, or if
                             expires_at is not after created_at.
        """
        require_uuid(self.id)
        require_uuid(self.account_id)

        if type(self.auth_version) is not int or self.auth_version < 1:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="session.auth_version.invalid",
                safe_details={"field": "auth_version"},
            )

        require_non_empty(self.refresh_token_hash, field="refresh_token_hash", max_length=500)
        require_utc(self.created_at)
        require_utc(self.expires_at)

        if self.expires_at <= self.created_at:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="session.expires_at.not_after_created",
                safe_details={"field": "expires_at"},
            )

        if self.revoked_at is not None:
            require_utc(self.revoked_at)

    def __repr__(self) -> str:
        """Return a diagnostic representation that excludes the token hash.

        Returns:
            A string showing the session id, account, and validity window.
        """
        return (
            f"Session(id={self.id!r}, account_id={self.account_id!r}, "
            f"expires_at={self.expires_at!r}, revoked_at={self.revoked_at!r})"
        )

    def is_valid(self, *, at: datetime, current_auth_version: int) -> bool:
        """Return whether the session is currently valid.

        A session is valid when it has not expired, has not been revoked, and
        its ``auth_version`` matches the account's current authentication
        version.

        Args:
            at: Explicit reference time for expiry evaluation.
            current_auth_version: The account's current authentication version.

        Returns:
            True if the session is valid at the given reference time.
        """
        if self.revoked_at is not None:
            return False
        if at >= self.expires_at:
            return False
        return self.auth_version == current_auth_version

    def revoke(self, *, at: datetime) -> None:
        """Mark this session as revoked at the given UTC timestamp.

        Args:
            at: Aware UTC timestamp when the revocation takes place.

        Raises:
            ValidationError: If ``at`` is naive or has a non-zero UTC offset.
            InvalidTransitionError: If the session is already revoked.
        """
        require_utc(at)
        if self.revoked_at is not None:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="session.already_revoked",
                safe_details={"session_id": str(self.id)},
            )
        self.revoked_at = at

