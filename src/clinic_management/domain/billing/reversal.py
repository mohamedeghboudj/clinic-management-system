"""Immutable payment reversal record and pure reversal-bound validation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.billing._validation import (
    require_aware_datetime,
    require_non_empty_text,
    require_uuid_value,
)
from clinic_management.domain.billing.payment import Payment
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money, sum_money


@dataclass(frozen=True, eq=False, kw_only=True)
class PaymentReversal(Entity):
    """Record an authorized positive correction against a previously posted payment."""

    id: UUID
    clinic_id: UUID
    payment_id: UUID
    amount: Money
    reason: str
    reversed_at: datetime
    reversed_by: UUID
    idempotency_key: UUID

    def __post_init__(self) -> None:
        """Validate identifiers, positive reversal amount, reason and timestamp.

        Raises:
            ValidationError: If any reversal invariant is violated.
        """
        require_uuid_value(self.id, "reversal.id.invalid")
        require_uuid_value(self.clinic_id, "reversal.clinic_id.invalid")
        require_uuid_value(self.payment_id, "reversal.payment_id.invalid")
        require_uuid_value(self.reversed_by, "reversal.reversed_by.invalid")
        require_uuid_value(self.idempotency_key, "reversal.idempotency_key.invalid")
        require_aware_datetime(self.reversed_at, "reversal.reversed_at.naive")

        if not isinstance(self.amount, Money) or self.amount.amount <= Decimal("0.00"):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="reversal.amount.nonpositive",
            )
        cleaned_reason = require_non_empty_text(self.reason, "reversal.reason.empty")
        object.__setattr__(self, "reason", cleaned_reason)


def validate_reversal(
    payment: Payment,
    amount: Money,
    existing: Sequence[PaymentReversal],
) -> None:
    """Validate that a proposed reversal does not exceed the remaining payment amount.

    Args:
        payment: Original posted Payment being reversed.
        amount: Positive Money amount proposed for reversal.
        existing: Previously recorded reversals against the same payment.

    Raises:
        ValidationError: If links/currencies mismatch, IDs duplicate, or bounds are exceeded.
    """
    if not isinstance(payment, Payment):
        raise ValidationError(code="INVALID_VALUE", message_key="reversal.payment.invalid")
    if (
        not isinstance(amount, Money)
        or amount.currency != payment.amount.currency
        or amount.amount <= Decimal("0.00")
    ):
        raise ValidationError(code="INVALID_VALUE", message_key="reversal.amount.invalid")

    seen_ids: set[UUID] = set()
    for item in existing:
        if not isinstance(item, PaymentReversal):
            raise ValidationError(code="INVALID_VALUE", message_key="reversal.existing.invalid")
        if (
            item.clinic_id != payment.clinic_id
            or item.payment_id != payment.id
            or item.amount.currency != payment.amount.currency
            or item.id in seen_ids
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="reversal.link.mismatch")
        seen_ids.add(item.id)

    already_reversed = sum_money((item.amount for item in existing), payment.amount.currency)
    proposed_total = already_reversed.add(amount)
    if proposed_total.compare(payment.amount) > 0:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="reversal.exceeds_payment",
        )
