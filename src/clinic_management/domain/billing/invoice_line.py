"""Immutable invoice line snapshot with deterministic decimal calculation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.billing._validation import (
    require_non_empty_text,
    require_optional_uuid,
    require_uuid_value,
)
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money, percentage_of


@dataclass(frozen=True, kw_only=True)
class InvoiceLine:
    """Snapshot an agreed billable service line on a patient invoice."""

    line_id: UUID
    description: str
    quantity: Decimal
    unit_price: Money
    discount_amount: Money
    tax_rate: Decimal
    source_service_id: UUID | None
    source_consultation_id: UUID | None

    def __post_init__(self) -> None:
        """Validate line identifiers, description, quantities, discount and tax bounds.

        Raises:
            ValidationError: If any line field violates financial invariants.
        """
        require_uuid_value(self.line_id, "invoice.line.id.invalid")
        require_optional_uuid(self.source_service_id, "invoice.line.service_id.invalid")
        require_optional_uuid(
            self.source_consultation_id,
            "invoice.line.consultation_id.invalid",
        )
        cleaned_desc = require_non_empty_text(
            self.description,
            "invoice.line.description.empty",
        )
        object.__setattr__(self, "description", cleaned_desc)

        if (
            not isinstance(self.quantity, Decimal)
            or not self.quantity.is_finite()
            or self.quantity <= Decimal("0")
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.line.quantity.invalid",
            )
        if not isinstance(self.unit_price, Money) or self.unit_price.amount < Decimal("0.00"):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.line.unit_price.invalid",
            )
        if (
            not isinstance(self.discount_amount, Money)
            or self.discount_amount.currency != self.unit_price.currency
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.line.discount.currency_mismatch",
            )
        gross = self.unit_price.multiply(self.quantity)
        if (
            self.discount_amount.amount < Decimal("0.00")
            or self.discount_amount.amount > gross.amount
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.line.discount.out_of_bounds",
            )
        if (
            not isinstance(self.tax_rate, Decimal)
            or not self.tax_rate.is_finite()
            or self.tax_rate < Decimal("0")
            or self.tax_rate > Decimal("1")
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.line.tax_rate.invalid",
            )

    def subtotal(self) -> Money:
        """Calculate the quantized line subtotal after subtracting discount from gross.

        Returns:
            Quantized Money representing gross minus discount_amount.
        """
        gross = self.unit_price.multiply(self.quantity)
        return gross.subtract(self.discount_amount)

    def tax(self) -> Money:
        """Calculate the quantized tax amount on the discounted line subtotal.

        Returns:
            Quantized Money representing subtotal multiplied by tax_rate.
        """
        return percentage_of(self.subtotal(), self.tax_rate)

    def total(self) -> Money:
        """Calculate the final line total including discount and tax.

        Returns:
            Quantized Money equal to subtotal plus tax.
        """
        return self.subtotal().add(self.tax())
