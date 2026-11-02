"""Private validation for M1 envelopes; no dependency on future feature helpers."""

from datetime import datetime, timedelta
from uuid import UUID

from clinic_management.domain.shared.errors import ValidationError


def require_uuid(value: UUID) -> None:
    """Require an actual UUID instead of accepting an unparsed transport string.

    Args:
        value: Parsed identifier supplied by the application boundary.

    Raises:
        ValidationError: If the value is not a UUID.
    """
    if not isinstance(value, UUID):
        raise ValidationError(code="INVALID_VALUE", message_key="shared.uuid.invalid")


def require_utc(value: datetime) -> None:
    """Require an aware UTC instant for authoritative envelope timestamps.

    Args:
        value: Instant to validate without consulting a clock.

    Raises:
        ValidationError: If the timestamp is naive or has a nonzero UTC offset.
    """
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValidationError(code="INVALID_VALUE", message_key="shared.timestamp.invalid")
