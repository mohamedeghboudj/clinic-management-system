"""Access-domain DTOs: AuthenticatedSession."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from clinic_management.domain.access.principal import Principal
from clinic_management.domain.shared.errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class AuthenticatedSession:
    """Immutable DTO returned after a successful authentication.

    The ``access_token`` and ``refresh_token`` fields are intentionally
    excluded from ``__repr__`` to prevent accidental exposure in logs.

    No real token generation is performed in Week 1.

    Attributes:
        principal: Verified, server-constructed authentication context.
        access_token: Opaque bearer token for API requests (excluded from repr).
        refresh_token: Opaque token for obtaining a new access token (excluded
                       from repr; the raw token must never be stored).
        expires_at: UTC timestamp when the access token expires.
    """

    principal: Principal
    access_token: str
    refresh_token: str
    expires_at: datetime

    def __post_init__(self) -> None:
        """Validate principal type, token strings, and expiry timestamp.

        Raises:
            ValidationError: If principal, tokens, or expires_at are invalid.
        """
        if not isinstance(self.principal, Principal):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="authenticated_session.principal.invalid",
                safe_details={"field": "principal"},
            )
        if not isinstance(self.access_token, str) or not self.access_token.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="authenticated_session.access_token.invalid",
                safe_details={"field": "access_token"},
            )
        if not isinstance(self.refresh_token, str) or not self.refresh_token.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="authenticated_session.refresh_token.invalid",
                safe_details={"field": "refresh_token"},
            )
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="authenticated_session.expires_at.invalid",
                safe_details={"field": "expires_at"},
            )

    def __repr__(self) -> str:
        """Return a diagnostic representation excluding sensitive token fields.

        Returns:
            A string with only the principal and expiry timestamp.
        """
        return (
            f"AuthenticatedSession(principal={self.principal!r}, "
            f"expires_at={self.expires_at!r})"
        )

