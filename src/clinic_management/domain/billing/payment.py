"""Immutable payment record representing funds received against an issued invoice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.billing._validation import (
    require_aware_datetime,
    require_non_empty_text,
    require_uuid_value,
)
from clinic_management.domain.billing.enums import PaymentMethod
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money


@dataclass(frozen=True, eq=False, kw_only=True)
class Payment(Entity):
    """Record a positive payment received by clinic staff against an invoice."""

    id: UUID
    clinic_id: UUID
    invoice_id: UUID
    amount: Money
    method: PaymentMethod
    received_at: datetime
    received_by: UUID
    idempotency_key: UUID
    external_reference: str | None = None

    def __post_init__(self) -> None:
        """Validate identifiers, positive amount, payment method and aware timestamp.

        Raises:
            ValidationError: If any payment invariant is violated.
        """
        require_uuid_value(self.id, "payment.id.invalid")
        require_uuid_value(self.clinic_id, "payment.clinic_id.invalid")
        require_uuid_value(self.invoice_id, "payment.invoice_id.invalid")
        require_uuid_value(self.received_by, "payment.received_by.invalid")
        require_uuid_value(self.idempotency_key, "payment.idempotency_key.invalid")
        require_aware_datetime(self.received_at, "payment.received_at.naive")

        if not isinstance(self.amount, Money) or self.amount.amount <= Decimal("0.00"):
            raise ValidationError(code="INVALID_VALUE", message_key="payment.amount.nonpositive")
        if not isinstance(self.method, PaymentMethod):
            raise ValidationError(code="INVALID_VALUE", message_key="payment.method.invalid")
        if self.external_reference is not None:
            cleaned_ref = require_non_empty_text(
                self.external_reference,
                "payment.external_reference.empty",
            )
            object.__setattr__(self, "external_reference", cleaned_ref)
