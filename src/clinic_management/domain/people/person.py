"""Person domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from clinic_management.domain.people.dates import age_on as calculate_age_on
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.address import Address
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(eq=False, kw_only=True)
class Person(Entity):
    """Domain entity representing an individual in the clinic system.

    Attributes:
        id: Unique identifier for the person.
        version: Aggregate root version for optimistic concurrency (defaults to 0).
        given_name: First name (accents and Unicode preserved).
        family_name: Last name / surname (accents and Unicode preserved).
        birth_date: Optional birth date.
        contact: Contact channels (phone, email).
        address: Optional physical address.
    """

    id: UUID
    version: int = 0
    given_name: str
    family_name: str
    contact: ContactInfo
    birth_date: date | None = None
    address: Address | None = None

    def __post_init__(self) -> None:
        """Validate local invariants without reading the system clock.

        Raises:
            ValidationError: If identifiers, names, versions, or types are invalid.
        """
        require_uuid(self.id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="person.version.invalid",
                safe_details={"field": "version"},
            )

        clean_given = require_non_empty(self.given_name, field="given_name", max_length=100)
        clean_family = require_non_empty(self.family_name, field="family_name", max_length=100)

        if not isinstance(self.contact, ContactInfo):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="person.contact.invalid",
                safe_details={"field": "contact"},
            )

        if self.birth_date is not None and (
            not isinstance(self.birth_date, date) or isinstance(self.birth_date, bool)
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="person.birth_date.invalid",
                safe_details={"field": "birth_date"},
            )

        if self.address is not None and not isinstance(self.address, Address):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="person.address.invalid",
                safe_details={"field": "address"},
            )

        object.__setattr__(self, "given_name", clean_given)
        object.__setattr__(self, "family_name", clean_family)

    def full_name(self) -> str:
        """Return the combined given and family name, preserving Unicode accents.

        Returns:
            The formatted full name string in 'given_name family_name' order.
        """
        return f"{self.given_name} {self.family_name}"

    def age_on(self, on_date: date) -> int | None:
        """Calculate the person's age on an explicit reference date.

        Args:
            on_date: Explicit reference date for the calculation.

        Returns:
            Age in whole completed years, or None if the person's birth date is unknown.

        Raises:
            ValidationError: If the birth date is in the future relative to on_date.
        """
        if self.birth_date is None:
            return None
        return calculate_age_on(self.birth_date, on_date=on_date)

    def update_contact(self, contact: ContactInfo, address: Address | None) -> None:
        """Update the person's contact info and optional address.

        Args:
            contact: New ContactInfo value object.
            address: New Address value object, or None to clear address.

        Raises:
            ValidationError: If contact or address types are invalid.
        """
        if not isinstance(contact, ContactInfo):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="person.contact.invalid",
                safe_details={"field": "contact"},
            )
        if address is not None and not isinstance(address, Address):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="person.address.invalid",
                safe_details={"field": "address"},
            )

        self.contact = contact
        self.address = address

