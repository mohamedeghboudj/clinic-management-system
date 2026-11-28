"""Domain-level text validation helpers for clinical content fields."""

from __future__ import annotations

from clinic_management.domain.shared.errors import ValidationError


def validate_clinical_text(
    value: str,
    *,
    field: str,
    max_length: int,
) -> str:
    """Strip, validate, and return clinical free-text content.

    Leading and trailing whitespace is removed.  The value must be
    non-empty after stripping and must not exceed *max_length* characters.
    Internal paragraph structure (newlines, indentation) is preserved.

    Args:
        value: Raw text to validate.
        field: Logical field name included in the error details.
        max_length: Maximum allowed character count after stripping.

    Returns:
        The stripped, validated text.

    Raises:
        ValidationError: If the text is empty, whitespace-only, or exceeds
            *max_length*.
    """
    if not isinstance(value, str):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key=f"clinical.{field}.invalid",
            safe_details={"field": field},
        )

    stripped = value.strip()

    if not stripped:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key=f"clinical.{field}.empty",
            safe_details={"field": field},
        )

    if len(stripped) > max_length:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key=f"clinical.{field}.too_long",
            safe_details={"field": field, "max_length": str(max_length)},
        )

    return stripped
