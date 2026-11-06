"""Tests for ContactInfo value object and contact validation utilities."""

from __future__ import annotations

import pytest

from clinic_management.domain.shared.contact import (
    ContactInfo,
    normalize_phone,
    validate_email,
)
from clinic_management.domain.shared.errors import ValidationError


class TestValidateEmail:
    """Tests for validate_email utility."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("user@example.com", "user@example.com"),
            ("  USER@EXAMPLE.COM  ", "user@example.com"),
            ("doctor.ahmed@clinic.dz", "doctor.ahmed@clinic.dz"),
            ("first+tag@sub.domain.org", "first+tag@sub.domain.org"),
        ],
    )
    def test_valid_emails_normalized(self, raw: str, expected: str) -> None:
        """Valid emails are lower-cased and stripped."""
        assert validate_email(raw) == expected

    @pytest.mark.parametrize(
        "invalid_email",
        [
            "",
            "   ",
            "not-an-email",
            "@no-local.com",
            "no-domain@",
            "spaces in@address.com",
            "double@@at.com",
            "user@.com",
            "user@domain.",
        ],
    )
    def test_invalid_emails_raise_validation_error(self, invalid_email: str) -> None:
        """Invalid email formats raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_email(invalid_email)
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "contact.email.invalid"

    @pytest.mark.parametrize("non_str", [None, 123, True, []])
    def test_non_string_email_raises_validation_error(self, non_str: object) -> None:
        """Non-string email inputs raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_email(non_str)  # type: ignore[arg-type]


class TestNormalizePhone:
    """Tests for normalize_phone utility."""

    @pytest.mark.parametrize(
        ("raw", "region", "expected"),
        [
            ("0550123456", "DZ", "+213550123456"),
            ("0661234567", "DZ", "+213661234567"),
            ("0770987654", "DZ", "+213770987654"),
            ("0550 12 34 56", "DZ", "+213550123456"),
            ("0550-12-34-56", "DZ", "+213550123456"),
            ("+213550123456", "DZ", "+213550123456"),
            ("+12025550123", "US", "+12025550123"),
            ("+33123456789", "FR", "+33123456789"),
            ("213550123456", "DZ", "+213550123456"),
        ],
    )
    def test_valid_phone_numbers_normalized(self, raw: str, region: str, expected: str) -> None:
        """Valid local and international numbers normalize to E.164 format."""
        assert normalize_phone(raw, region=region) == expected

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "",
            "   ",
            "abc",
            "+123",  # Too short for E.164 (min 7 digits)
            "+1234567890123456",  # Too long for E.164 (max 15 digits)
            "0000000000",  # Invalid prefix
            "12345",
        ],
    )
    def test_invalid_phone_raises_validation_error(self, invalid_phone: str) -> None:
        """Invalid phone numbers raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            normalize_phone(invalid_phone)
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.message_key == "contact.phone.invalid"

    @pytest.mark.parametrize("non_str", [None, 123, True, []])
    def test_non_string_phone_raises_validation_error(self, non_str: object) -> None:
        """Non-string phone inputs raise ValidationError."""
        with pytest.raises(ValidationError):
            normalize_phone(non_str)  # type: ignore[arg-type]


class TestContactInfo:
    """Tests for ContactInfo value object."""

    def test_empty_contact_info(self) -> None:
        """ContactInfo with no arguments is empty."""
        contact = ContactInfo()
        assert contact.phone is None
        assert contact.email is None
        assert contact.is_empty() is True

    def test_contact_info_with_phone_only(self) -> None:
        """ContactInfo with phone only normalizes phone and is not empty."""
        contact = ContactInfo(phone="0550123456")
        assert contact.phone == "+213550123456"
        assert contact.email is None
        assert contact.is_empty() is False

    def test_contact_info_with_email_only(self) -> None:
        """ContactInfo with email only normalizes email and is not empty."""
        contact = ContactInfo(email="Ahmed@Clinic.dz")
        assert contact.phone is None
        assert contact.email == "ahmed@clinic.dz"
        assert contact.is_empty() is False

    def test_contact_info_with_both(self) -> None:
        """ContactInfo with both fields normalizes both."""
        contact = ContactInfo(phone="+213550123456", email="test@example.com")
        assert contact.phone == "+213550123456"
        assert contact.email == "test@example.com"
        assert contact.is_empty() is False

    def test_contact_info_immutability(self) -> None:
        """ContactInfo fields cannot be mutated after creation."""
        contact = ContactInfo(phone="0550123456", email="user@example.com")
        with pytest.raises((AttributeError, TypeError)):
            contact.phone = "+213000000000"  # type: ignore[misc]

    def test_invalid_phone_in_contact_info_raises_validation_error(self) -> None:
        """Supplying invalid phone raises ValidationError on creation."""
        with pytest.raises(ValidationError) as exc_info:
            ContactInfo(phone="invalid-phone")
        assert exc_info.value.code == "INVALID_VALUE"

    def test_invalid_email_in_contact_info_raises_validation_error(self) -> None:
        """Supplying invalid email raises ValidationError on creation."""
        with pytest.raises(ValidationError) as exc_info:
            ContactInfo(email="not_an_email")
        assert exc_info.value.code == "INVALID_VALUE"

