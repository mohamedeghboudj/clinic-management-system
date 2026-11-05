"""Service catalogue item aggregate for billable clinical services."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money


@dataclass(eq=False, kw_only=True)
class ServiceCatalogItem(Entity):
    """Mutable aggregate representing a billable service in the catalogue.

    Each item belongs to a single clinic and carries a monetary price.
    Items can be activated or deactivated without deletion to preserve
    referential integrity in historical billing records.

    Attributes:
        id: Unique catalogue item identifier.
        clinic_id: Owning clinic.
        code: Short code uniquely identifying the service within the
            clinic (e.g. ``"CONS-GP"``).
        description: Human-readable description of the service.
        price: Monetary price charged for the service.
        duration_minutes: Expected duration in minutes, or ``None`` if
            not time-bound.
        active: Whether the item is currently offered.
        version: Optimistic-concurrency version counter.
    """

    id: UUID
    clinic_id: UUID
    code: str
    description: str
    price: Money
    duration_minutes: int | None = None
    active: bool = True
    version: int = 0

    def __post_init__(self) -> None:
        """Validate all invariants on construction.

        Raises:
            ValidationError: If any field violates its domain constraint.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)

        # --- code ---
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.service_catalog.code.empty",
                safe_details={"field": "code"},
            )
        self.code = self.code.strip()

        # --- description ---
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.service_catalog.description.empty",
                safe_details={"field": "description"},
            )
        self.description = self.description.strip()

        # --- price ---
        _validate_price(self.price)

        # --- duration_minutes ---
        if self.duration_minutes is not None:
            if not isinstance(self.duration_minutes, int) or self.duration_minutes <= 0:
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="clinical.service_catalog.duration.invalid",
                    safe_details={"field": "duration_minutes"},
                )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def change_price(self, price: Money) -> None:
        """Update the catalogue item price.

        Args:
            price: New non-negative monetary price.

        Raises:
            ValidationError: If *price* is not a valid ``Money`` with a
                non-negative amount.
        """
        _validate_price(price)
        self.price = price
        self.version += 1

    def deactivate(self) -> None:
        """Mark the catalogue item as inactive.

        Inactive items are hidden from new billing but retained for
        historical reference.
        """
        self.active = False
        self.version += 1

    def activate(self) -> None:
        """Restore the catalogue item to active status."""
        self.active = True
        self.version += 1


def _validate_price(price: Money) -> None:
    """Validate that *price* is a ``Money`` instance with a non-negative amount.

    Args:
        price: Value to validate.

    Raises:
        ValidationError: If the value is not a ``Money`` or has a
            negative amount.
    """
    if not isinstance(price, Money):
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="clinical.service_catalog.price.invalid",
            safe_details={"field": "price"},
        )
    if price.amount < 0:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="clinical.service_catalog.price.negative",
            safe_details={"field": "price"},
        )
