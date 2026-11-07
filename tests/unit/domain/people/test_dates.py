"""Unit tests for date validation and age calculation."""

from __future__ import annotations

from datetime import date

import pytest

from clinic_management.domain.people.dates import age_on, validate_birth_date
from clinic_management.domain.shared.errors import ValidationError


class TestValidateBirthDate:
    """Tests for validate_birth_date helper."""

    def test_valid_birth_date_in_past(self) -> None:
        """A birth date before the reference date is accepted."""
        b_date = date(1990, 5, 15)
        ref_date = date(2026, 11, 2)
        assert validate_birth_date(b_date, reference_date=ref_date) == b_date

    def test_valid_birth_date_equal_to_reference_date(self) -> None:
        """A birth date born today (equal to reference date) is accepted."""
        today = date(2026, 11, 2)
        assert validate_birth_date(today, reference_date=today) == today

    def test_future_birth_date_rejected(self) -> None:
        """A birth date after the reference date raises ValidationError."""
        future_date = date(2027, 1, 1)
        ref_date = date(2026, 11, 2)
        with pytest.raises(ValidationError) as exc_info:
            validate_birth_date(future_date, reference_date=ref_date)
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "person.birth_date.future"
        assert exc_info.value.safe_details["field"] == "birth_date"

    @pytest.mark.parametrize("invalid_birth", [None, "2000-01-01", 20000101, True, False])
    def test_invalid_birth_date_type_rejected(self, invalid_birth: object) -> None:
        """Non-date birth_date inputs raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_birth_date(invalid_birth, reference_date=date(2026, 1, 1))  # type: ignore[arg-type]
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "person.birth_date.invalid"

    @pytest.mark.parametrize("invalid_ref", [None, "2026-01-01", 12345, True, False])
    def test_invalid_reference_date_type_rejected(self, invalid_ref: object) -> None:
        """Non-date reference_date inputs raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_birth_date(date(2000, 1, 1), reference_date=invalid_ref)  # type: ignore[arg-type]
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "person.reference_date.invalid"


class TestAgeOn:
    """Tests for age_on calculation."""

    def test_age_on_exact_birthday(self) -> None:
        """Age on the exact day of birthday equals full year difference."""
        birth = date(1995, 6, 20)
        on = date(2025, 6, 20)
        assert age_on(birth, on_date=on) == 30

    def test_age_one_day_before_birthday(self) -> None:
        """Age one day before birthday is years - 1."""
        birth = date(1995, 6, 20)
        on = date(2025, 6, 19)
        assert age_on(birth, on_date=on) == 29

    def test_age_one_day_after_birthday(self) -> None:
        """Age one day after birthday is full years."""
        birth = date(1995, 6, 20)
        on = date(2025, 6, 21)
        assert age_on(birth, on_date=on) == 30

    def test_age_newborn_zero_years(self) -> None:
        """A child under 1 year old has age 0."""
        birth = date(2026, 1, 15)
        on = date(2026, 11, 2)
        assert age_on(birth, on_date=on) == 0

    def test_age_on_birth_date_is_zero(self) -> None:
        """Age on day of birth is 0."""
        today = date(2026, 11, 2)
        assert age_on(today, on_date=today) == 0

    def test_feb_29_birthday_in_leap_year(self) -> None:
        """Feb 29 birthday in another leap year (e.g. 2000 -> 2004)."""
        birth = date(2000, 2, 29)
        # On Feb 28 of leap year 2004: still 3 years old
        assert age_on(birth, on_date=date(2004, 2, 28)) == 3
        # On Feb 29 of leap year 2004: reaches 4
        assert age_on(birth, on_date=date(2004, 2, 29)) == 4
        # On March 1 of leap year 2004: 4
        assert age_on(birth, on_date=date(2004, 3, 1)) == 4

    def test_feb_29_birthday_in_non_leap_year_march_1_convention(self) -> None:
        """Feb 29 birthday uses March 1 as anniversary in non-leap years."""
        birth = date(2000, 2, 29)
        # 2001 is not a leap year.
        # On February 28, 2001: still 0 years old (anniversary is March 1)
        assert age_on(birth, on_date=date(2001, 2, 28)) == 0
        # On March 1, 2001: reaches 1 year old
        assert age_on(birth, on_date=date(2001, 3, 1)) == 1
        # On March 2, 2001: 1 year old
        assert age_on(birth, on_date=date(2001, 3, 2)) == 1

        # Check another non-leap year (2025, 25 years later)
        assert age_on(birth, on_date=date(2025, 2, 28)) == 24
        assert age_on(birth, on_date=date(2025, 3, 1)) == 25

    def test_future_reference_date_rejected_by_age_on(self) -> None:
        """When on_date is before birth_date, age_on raises ValidationError."""
        birth = date(2020, 1, 1)
        on = date(2019, 12, 31)
        with pytest.raises(ValidationError):
            age_on(birth, on_date=on)

