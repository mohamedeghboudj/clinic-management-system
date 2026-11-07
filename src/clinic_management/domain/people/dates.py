"""Birth date validation and age calculation utilities."""

from __future__ import annotations

import calendar
from datetime import date

from clinic_management.domain.shared.errors import ValidationError


def validate_birth_date(birth_date: date, *, reference_date: date) -> date:
    """Validate that a birth date is a valid date not in the future relative to a reference date.

    Args:
        birth_date: The birth date to validate.
        reference_date: Explicit reference date (typically today/now's date).

    Returns:
        The validated birth date.

    Raises:
        ValidationError: If birth_date or reference_date are not date instances,
            or if birth_date is after reference_date.
    """
    if not isinstance(birth_date, date) or isinstance(birth_date, bool):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="person.birth_date.invalid",
            safe_details={"field": "birth_date"},
        )

    if not isinstance(reference_date, date) or isinstance(reference_date, bool):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="person.reference_date.invalid",
            safe_details={"field": "reference_date"},
        )

    if birth_date > reference_date:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="person.birth_date.future",
            safe_details={"field": "birth_date"},
        )

    return birth_date


def age_on(birth_date: date, *, on_date: date) -> int:
    """Calculate the completed whole years of age on an explicit reference date.

    For individuals born on February 29 (leap year), their anniversary in a non-leap
    year is celebrated on March 1. Therefore, in a non-leap year, they have not reached
    their birthday on February 28; they reach it on March 1.

    Args:
        birth_date: The birth date.
        on_date: Explicit reference date for the age calculation.

    Returns:
        The completed age in integer years.

    Raises:
        ValidationError: If birth_date or on_date are invalid, or if on_date is
            before birth_date.
    """
    validate_birth_date(birth_date, reference_date=on_date)

    # Initial year difference
    years = on_date.year - birth_date.year

    # Determine whether the anniversary in on_date.year has occurred yet
    if birth_date.month == 2 and birth_date.day == 29:
        if calendar.isleap(on_date.year):
            birthday_this_year = date(on_date.year, 2, 29)
        else:
            # Per project specification: March 1 in non-leap years
            birthday_this_year = date(on_date.year, 3, 1)
    else:
        birthday_this_year = date(on_date.year, birth_date.month, birth_date.day)

    if on_date < birthday_this_year:
        years -= 1

    return years

