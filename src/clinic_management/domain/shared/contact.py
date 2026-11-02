"""Contact information value object and email/phone validation utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass

from clinic_management.domain.shared.errors import ValidationError

# RFC 5322 simplified pattern for practical email syntax validation
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# E.164 phone number pattern: optional +, 7 to 15 digits
_E164_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")


def validate_email(value: str) -> str:
    """Validate and normalize an email address string.

    The address is stripped of surrounding whitespace and converted to lower case.
    Basic RFC 5322 structural compliance is enforced.

    Args:
        value: Email address string to validate.

    Returns:
        The normalized lower-case email address.

    Raises:
        ValidationError: If the email is not a string, is empty, or has an invalid format.
    """
    if not isinstance(value, str):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="contact.email.invalid",
            safe_details={"field": "email"},
        )

    stripped = value.strip().lower()
    if not stripped or len(stripped) > 254:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="contact.email.invalid",
            safe_details={"field": "email"},
        )

    if not _EMAIL_PATTERN.match(stripped):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="contact.email.invalid",
            safe_details={"field": "email"},
        )

    return stripped


def normalize_phone(value: str, region: str = "DZ") -> str:
    """Validate and normalize a phone number for the specified region.

    Strips whitespace, dashes, dots, and parentheses. If the number has a leading '+',
    it is treated as international E.164. Otherwise, region-specific prefix rules are applied:
    - Region "DZ" (Algeria, default clinic region): 9 or 10 digits starting with 0 or local digit.
      E.g., "0550123456" -> "+213550123456".
    - Other regions or already international: requires standard E.164 format.

    Args:
        value: Raw phone number string.
        region: ISO two-letter country code for local number interpretation (default "DZ").

    Returns:
        The normalized phone number in E.164 format (with leading '+').

    Raises:
        ValidationError: If the value is not a string, empty, or cannot be parsed as a valid phone.
    """
    if not isinstance(value, str):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="contact.phone.invalid",
            safe_details={"field": "phone"},
        )

    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-().]", "", value)
    if not cleaned:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="contact.phone.invalid",
            safe_details={"field": "phone"},
        )

    upper_region = region.upper().strip() if isinstance(region, str) else ""

    if cleaned.startswith("+"):
        digits_only = cleaned[1:]
        if not digits_only.isdigit() or not _E164_PATTERN.match(cleaned):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="contact.phone.invalid",
                safe_details={"field": "phone"},
            )
        return cleaned

    # Local Algerian number normalization: e.g. "0550123456" -> "+213550123456"
    # Valid Algerian mobile/landline prefixes typically start with 0 followed by 2, 3, 4 (landlines) or 5, 6, 7, 8, 9
    if upper_region == "DZ":
        if cleaned.startswith("0") and len(cleaned) == 10 and cleaned.isdigit() and cleaned[1] != "0":
            return "+213" + cleaned[1:]
        if cleaned.startswith("213") and len(cleaned) == 12 and cleaned.isdigit() and cleaned[3] != "0":
            return "+" + cleaned
        if len(cleaned) == 9 and cleaned.isdigit() and cleaned[0] in "567":
            return "+213" + cleaned
        # Any other 0-prefixed number for DZ is invalid
        if cleaned.startswith("0"):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="contact.phone.invalid",
                safe_details={"field": "phone"},
            )

    # Fallback: check if the digits form a valid E.164 number with added '+'
    candidate = "+" + cleaned
    if _E164_PATTERN.match(candidate):
        return candidate

    raise ValidationError(
        code="INVALID_VALUE",
        message_key="contact.phone.invalid",
        safe_details={"field": "phone"},
    )


@dataclass(frozen=True, kw_only=True)
class ContactInfo:
    """Immutable value object holding optional contact channels for an entity."""

    phone: str | None = None
    email: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize supplied contact values.

        Raises:
            ValidationError: If any supplied field fails validation.
        """
        if self.phone is not None:
            normalized_phone = normalize_phone(self.phone)
            object.__setattr__(self, "phone", normalized_phone)

        if self.email is not None:
            normalized_email = validate_email(self.email)
            object.__setattr__(self, "email", normalized_email)

    def is_empty(self) -> bool:
        """Return True if neither phone nor email is provided.

        Returns:
            True if all contact fields are None, False otherwise.
        """
        return self.phone is None and self.email is None
