"""Internal validation helpers for billing domain entities and value objects."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from clinic_management.domain.shared.errors import ValidationError


def require_uuid_value(value: UUID, message_key: str = "billing.uuid.invalid") -> UUID:
    """Validate that a field is a UUID instance.

    Args:
        value: Identifier value to verify.
        message_key: Translation key for validation failure.

    Returns:
        The validated UUID.

    Raises:
        ValidationError: If value is not a UUID instance.
    """
    if not isinstance(value, UUID):
        raise ValidationError(code="INVALID_VALUE", message_key=message_key)
    return value


def require_optional_uuid(
    value: UUID | None,
    message_key: str = "billing.uuid.invalid",
) -> UUID | None:
    """Validate that an optional field is either None or a UUID instance.

    Args:
        value: Optional identifier value to verify.
        message_key: Translation key for validation failure.

    Returns:
        None or the validated UUID.

    Raises:
        ValidationError: If value is neither None nor a UUID.
    """
    if value is not None and not isinstance(value, UUID):
        raise ValidationError(code="INVALID_VALUE", message_key=message_key)
    return value


def require_non_empty_text(value: str, message_key: str) -> str:
    """Trim boundary whitespace and require a non-empty string.

    Args:
        value: Raw string input to validate.
        message_key: Translation key for validation failure.

    Returns:
        Trimmed non-empty string.

    Raises:
        ValidationError: If value is not a string or is blank after trimming.
    """
    if not isinstance(value, str):
        raise ValidationError(code="INVALID_VALUE", message_key=message_key)
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(code="INVALID_VALUE", message_key=message_key)
    return cleaned


def require_aware_datetime(
    value: datetime,
    message_key: str = "billing.datetime.naive",
) -> datetime:
    """Require a timezone-aware datetime object.

    Args:
        value: Datetime instant to validate.
        message_key: Translation key for validation failure.

    Returns:
        The validated timezone-aware datetime.

    Raises:
        ValidationError: If value is not a timezone-aware datetime.
    """
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(code="INVALID_VALUE", message_key=message_key)
    return value
