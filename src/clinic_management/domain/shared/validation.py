"""Shared text and field validation helpers for domain entities and value objects."""

from __future__ import annotations

from clinic_management.domain.shared.errors import ValidationError


def require_non_empty(
    value: str,
    *,
    field: str,
    max_length: int | None = None,
) -> str:
    """Validate that a string value is non-empty and optionally within length bounds.

    Leading and trailing whitespace is stripped. The resulting string must have
    a length greater than zero. If ``max_length`` is provided, the stripped
    length must not exceed it.

    Args:
        value: Input string to validate.
        field: Field name used for contextual error reporting.
        max_length: Optional maximum character count allowed after stripping.

    Returns:
        The stripped non-empty string.

    Raises:
        ValidationError: If the value is not a string, is empty or whitespace-only,
            or exceeds the specified maximum length.
    """
    if not isinstance(value, str):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="validation.type_error",
            safe_details={"field": field},
        )

    stripped = value.strip()
    if not stripped:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="validation.empty",
            safe_details={"field": field},
        )

    if max_length is not None and len(stripped) > max_length:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="validation.too_long",
            safe_details={"field": field, "max_length": str(max_length)},
        )

    return stripped

