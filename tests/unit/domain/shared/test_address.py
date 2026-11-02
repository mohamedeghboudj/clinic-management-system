"""Tests for Address value object."""

from __future__ import annotations

import pytest

from clinic_management.domain.shared.address import Address
from clinic_management.domain.shared.errors import ValidationError


class TestAddress:
    """Tests for Address value object."""

    def test_valid_address_minimal(self) -> None:
        """Minimal address with required fields only."""
        addr = Address(line1="123 Didouche Mourad", city="Algiers", country_code="DZ")
        assert addr.line1 == "123 Didouche Mourad"
        assert addr.city == "Algiers"
        assert addr.country_code == "DZ"
        assert addr.region is None
        assert addr.postal_code is None

    def test_valid_address_full(self) -> None:
        """Full address with all optional fields."""
        addr = Address(
            line1="  45 Rue Larbi Ben M'hidi  ",
            city="  Oran  ",
            country_code="dz",
            region="  Oran Province  ",
            postal_code="  31000  ",
        )
        assert addr.line1 == "45 Rue Larbi Ben M'hidi"
        assert addr.city == "Oran"
        assert addr.country_code == "DZ"  # Normalized uppercase
        assert addr.region == "Oran Province"
        assert addr.postal_code == "31000"

    def test_address_immutability(self) -> None:
        """Address is a frozen dataclass and cannot be modified."""
        addr = Address(line1="123 Main St", city="Algiers", country_code="DZ")
        with pytest.raises((AttributeError, TypeError)):
            addr.line1 = "New St"  # type: ignore[misc]

    @pytest.mark.parametrize("empty_line1", ["", "   ", "\t"])
    def test_empty_line1_rejected(self, empty_line1: str) -> None:
        """Empty or whitespace line1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Address(line1=empty_line1, city="Algiers", country_code="DZ")
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "line1"

    @pytest.mark.parametrize("empty_city", ["", "   ", "\t"])
    def test_empty_city_rejected(self, empty_city: str) -> None:
        """Empty or whitespace city raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Address(line1="123 Main St", city=empty_city, country_code="DZ")
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "city"

    @pytest.mark.parametrize(
        "invalid_code",
        ["", "D", "DZA", "12", "D1", "dz1", "ALGERIA", "   "],
    )
    def test_invalid_country_code_rejected(self, invalid_code: str) -> None:
        """Country codes not conforming to ISO 3166-1 alpha-2 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Address(line1="123 Main St", city="Algiers", country_code=invalid_code)
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "country_code"

    def test_empty_region_if_provided_rejected(self) -> None:
        """Whitespace-only region raises ValidationError if explicitly provided."""
        with pytest.raises(ValidationError) as exc_info:
            Address(line1="123 Main St", city="Algiers", country_code="DZ", region="   ")
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "region"

    def test_empty_postal_code_if_provided_rejected(self) -> None:
        """Whitespace-only postal_code raises ValidationError if explicitly provided."""
        with pytest.raises(ValidationError) as exc_info:
            Address(line1="123 Main St", city="Algiers", country_code="DZ", postal_code="   ")
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "postal_code"

    def test_arbitrary_international_postal_codes_accepted(self) -> None:
        """Arbitrary international postal code formats are accepted without assumptions."""
        for code in ["16000", "75001", "SW1A 1AA", "K1A 0B1", "00100"]:
            addr = Address(
                line1="Some St",
                city="Some City",
                country_code="FR",
                postal_code=code,
            )
            assert addr.postal_code == code

