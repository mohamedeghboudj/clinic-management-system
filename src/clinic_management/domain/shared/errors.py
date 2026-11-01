"""Stable failure categories whose default representations omit private data."""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,79}\Z")
_MESSAGE_KEY = re.compile(r"[a-z][a-z0-9_.]{0,119}\Z")


class ClinicError(Exception):
    """Describe a safe failure without exposing its cause or contextual values.

    Callers must restrict ``safe_details`` to reviewed, non-sensitive UI facts.
    Exceptions never render those values automatically. Preserve technical
    causes using exception chaining at the adapter boundary.
    """

    def __init__(
        self,
        *,
        code: str,
        message_key: str,
        safe_details: Mapping[str, str] | None = None,
    ) -> None:
        """Copy a machine-readable failure contract without logging its values.

        Args:
            code: Stable uppercase machine code published in the error catalogue.
            message_key: Translation key, never a human or technical message.
            safe_details: Explicitly reviewed non-sensitive presentation facts.

        Raises:
            ValueError: If the code, key or detail structure is invalid.
        """
        if not _CODE.fullmatch(code) or not _MESSAGE_KEY.fullmatch(message_key):
            raise ValueError("Invalid error contract identifier")
        details = dict(safe_details or {})
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in details.items()):
            raise ValueError("Error details must be a string mapping")
        self.code = code
        self.message_key = message_key
        self.safe_details: Mapping[str, str] = MappingProxyType(details)
        super().__init__(code)

    def __repr__(self) -> str:
        """Return only the error category and machine code for diagnostics.

        Returns:
            A representation excluding detail values and exception causes.
        """
        return f"{type(self).__name__}(code={self.code!r})"


class ValidationError(ClinicError):
    """Reject invalid input or a locally inconsistent business value."""


class NotFoundError(ClinicError):
    """Reject an operation requiring a resource that does not exist."""


class AuthenticationError(ClinicError):
    """Reject credentials or an expired, disabled or invalid session."""


class PermissionDeniedError(ClinicError):
    """Reject access without disclosing restricted resource contents."""


class ConflictError(ClinicError):
    """Reject a conflicting reservation, identifier or command request."""


class ConcurrencyError(ConflictError):
    """Reject a save whose expected aggregate version is stale."""


class InvalidTransitionError(ClinicError):
    """Reject a lifecycle move that the current state does not permit."""


class ConfigurationError(ClinicError):
    """Prevent startup when required configuration is invalid or incomplete."""


class DependencyUnavailableError(ClinicError):
    """Report that a required external dependency cannot serve the operation."""


class PersistenceError(ClinicError):
    """Report a storage failure without leaking a driver exception."""
