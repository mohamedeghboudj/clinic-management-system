"""Physical address value object."""

from __future__ import annotations

import re
from dataclasses import dataclass

from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.validation import require_non_empty

# ISO 3166-1 alpha-2 standard: two uppercase ASCII letters
_COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")


@dataclass(frozen=True, kw_only=True)
class Address:
    """Immutable value object representing a physical address.

    Required fields:
        line1: Street address or primary line.
        city: City or locality name.
        country_code: Two-letter ISO 3166-1 alpha-2 country code (e.g., 'DZ', 'FR').

    Optional fields:
        region: State, province, wilaya, or administrative region.
        postal_code: Postal code or ZIP code (no country-specific assumptions).
    """

    line1: str
    city: str
    country_code: str
    region: str | None = None
    postal_code: str | None = None

    def __post_init__(self) -> None:
        """Validate address fields and normalize country code.

        Raises:
            ValidationError: If required fields are empty/whitespace or country code is invalid.
        """
        clean_line1 = require_non_empty(self.line1, field="line1", max_length=200)
        clean_city = require_non_empty(self.city, field="city", max_length=100)

        # Validate and normalize country_code
        if not isinstance(self.country_code, str):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="address.country_code.invalid",
                safe_details={"field": "country_code"},
            )
        upper_country = self.country_code.strip().upper()
        if not _COUNTRY_CODE_PATTERN.match(upper_country):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="address.country_code.invalid",
                safe_details={"field": "country_code"},
            )

        # Optional region validation
        clean_region: str | None = None
        if self.region is not None:
            clean_region = require_non_empty(self.region, field="region", max_length=100)

        # Optional postal code validation: must not be empty string if provided
        clean_postal: str | None = None
        if self.postal_code is not None:
            clean_postal = require_non_empty(self.postal_code, field="postal_code", max_length=20)

        object.__setattr__(self, "line1", clean_line1)
        object.__setattr__(self, "city", clean_city)
        object.__setattr__(self, "country_code", upper_country)
        object.__setattr__(self, "region", clean_region)
        object.__setattr__(self, "postal_code", clean_postal)

