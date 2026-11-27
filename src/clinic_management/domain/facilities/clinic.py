"""Clinic aggregate root representing a single healthcare facility."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.facilities.opening_hours import OpeningHours
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.address import Address
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.validation import require_non_empty

# Minimal ISO 4217 three-letter currency code pattern.
_CURRENCY_CODE_LENGTH = 3


@dataclass(eq=False, kw_only=True)
class Clinic(Entity):
    """Domain entity representing a healthcare clinic.

    There is one active clinic in Sprint 1, but the model allows multiple
    clinics by design — do not hard-code a single-clinic assumption.

    Attributes:
        id: Unique identifier for this clinic.
        version: Aggregate root version for optimistic concurrency.
        name: Display name of the clinic.
        contact: Contact information (phone / email).
        address: Optional physical address of the clinic.
        timezone: IANA timezone identifier for the clinic.
        currency: ISO 4217 three-letter currency code (e.g. ``"DZD"``).
        opening_hours: Weekly opening schedule.
        active: Whether the clinic is currently accepting appointments.
    """

    id: UUID
    version: int = 0
    name: str
    contact: ContactInfo
    timezone: str
    currency: str
    opening_hours: OpeningHours
    address: Address | None = None
    active: bool = True

    def __post_init__(self) -> None:
        """Validate identifiers, required strings and timezone/currency codes.

        Raises:
            ValidationError: If any required field is missing or invalid, or if
                the opening-hours timezone does not match the clinic timezone.
        """
        require_uuid(self.id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.version.invalid",
                safe_details={"field": "version"},
            )

        clean_name = require_non_empty(self.name, field="name", max_length=200)
        object.__setattr__(self, "name", clean_name)

        if not isinstance(self.contact, ContactInfo):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.contact.invalid",
                safe_details={"field": "contact"},
            )

        if self.address is not None and not isinstance(self.address, Address):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.address.invalid",
                safe_details={"field": "address"},
            )

        clean_tz = require_non_empty(self.timezone, field="timezone", max_length=100)
        object.__setattr__(self, "timezone", clean_tz)

        clean_currency = require_non_empty(self.currency, field="currency", max_length=10)
        if len(clean_currency) != _CURRENCY_CODE_LENGTH or not clean_currency.isalpha():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.currency.invalid",
                safe_details={"field": "currency"},
            )
        object.__setattr__(self, "currency", clean_currency.upper())

        if not isinstance(self.opening_hours, OpeningHours):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.opening_hours.invalid",
                safe_details={"field": "opening_hours"},
            )

        # The opening-hours schedule must use the same timezone as the clinic.
        if self.opening_hours.timezone != self.timezone:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.timezone.mismatch",
                safe_details={"field": "opening_hours"},
            )

        if type(self.active) is not bool:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.active.invalid",
                safe_details={"field": "active"},
            )

    def update_opening_hours(self, schedule: OpeningHours) -> None:
        """Replace the clinic's opening-hours configuration.

        The new schedule's timezone must match the clinic's own timezone.

        Args:
            schedule: Replacement ``OpeningHours`` value object.

        Raises:
            ValidationError: If *schedule* is not an ``OpeningHours`` instance
                or its timezone does not match the clinic timezone.
        """
        if not isinstance(schedule, OpeningHours):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.opening_hours.invalid",
                safe_details={"field": "opening_hours"},
            )
        if schedule.timezone != self.timezone:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinic.timezone.mismatch",
                safe_details={"field": "opening_hours"},
            )
        self.opening_hours = schedule

    def deactivate(self) -> None:
        """Mark the clinic as inactive.

        Note:
            This does not automatically cancel existing appointments.
            The calling use case is responsible for handling downstream
            effects on scheduled appointments.
        """
        self.active = False
