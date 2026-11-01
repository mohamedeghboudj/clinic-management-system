"""Derived invoice balance calculation and payment allocation validation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.billing._validation import require_uuid_value
from clinic_management.domain.billing.enums import InvoiceStatus, SettlementStatus
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.billing.payment import Payment
from clinic_management.domain.billing.reversal import PaymentReversal, validate_reversal
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money, sum_money


@dataclass(frozen=True, kw_only=True)
class BalanceSummary:
    """Represent the derived financial position of an invoice."""

    invoice_id: UUID
    total: Money
    net_paid: Money
    outstanding: Money
    settlement: SettlementStatus

    def __post_init__(self) -> None:
        """Validate summary fields and currency consistency.

        Raises:
            ValidationError: If fields are invalid or currencies do not match.
        """
        require_uuid_value(self.invoice_id, "balance.invoice_id.invalid")
        if (
            not isinstance(self.total, Money)
            or not isinstance(self.net_paid, Money)
            or not isinstance(self.outstanding, Money)
            or self.total.currency != self.net_paid.currency
            or self.total.currency != self.outstanding.currency
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="balance.money.invalid")
        if not isinstance(self.settlement, SettlementStatus):
            raise ValidationError(code="INVALID_VALUE", message_key="balance.settlement.invalid")

    def is_overdue(self, *, due_on: date | None, on_date: date, issued: bool) -> bool:
        """Determine whether an issued invoice with positive debt is past its due date.

        Args:
            due_on: Invoice due date, if any.
            on_date: Explicit reference date for the overdue evaluation.
            issued: Whether the invoice is currently in ISSUED state.

        Returns:
            True if issued, due_on is before on_date, and outstanding > 0.

        Raises:
            ValidationError: If date arguments are invalid.
        """
        if not isinstance(on_date, date) or isinstance(on_date, datetime):
            raise ValidationError(code="INVALID_VALUE", message_key="balance.on_date.invalid")
        if due_on is not None and (not isinstance(due_on, date) or isinstance(due_on, datetime)):
            raise ValidationError(code="INVALID_VALUE", message_key="balance.due_on.invalid")
        return bool(
            issued
            and due_on is not None
            and due_on < on_date
            and self.outstanding.amount > Decimal("0.00")
        )


def _index_validated_payments(
    invoice: Invoice,
    payments: Sequence[Payment],
) -> dict[UUID, Payment]:
    """Verify payment links, uniqueness and currency against the target invoice.

    Args:
        invoice: Target Invoice aggregate.
        payments: Sequence of posted Payment records.

    Returns:
        Mapping of payment ID to validated Payment instance.

    Raises:
        ValidationError: If any payment does not belong to the invoice or duplicates ID.
    """
    by_id: dict[UUID, Payment] = {}
    for item in payments:
        if (
            not isinstance(item, Payment)
            or item.clinic_id != invoice.clinic_id
            or item.invoice_id != invoice.id
            or item.amount.currency != invoice.currency
            or item.id in by_id
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="balance.payment.mismatch")
        by_id[item.id] = item
    return by_id


def _validate_grouped_reversals(
    invoice: Invoice,
    payments_by_id: dict[UUID, Payment],
    reversals: Sequence[PaymentReversal],
) -> None:
    """Verify reversal links, uniqueness and per-payment bounds.

    Args:
        invoice: Target Invoice aggregate.
        payments_by_id: Validated payments keyed by payment UUID.
        reversals: Sequence of PaymentReversal records.

    Raises:
        ValidationError: If any reversal is unlinked, duplicated, or exceeds its payment.
    """
    seen_reversals: set[UUID] = set()
    grouped: dict[UUID, list[PaymentReversal]] = {pid: [] for pid in payments_by_id}
    for rev in reversals:
        if (
            not isinstance(rev, PaymentReversal)
            or rev.clinic_id != invoice.clinic_id
            or rev.payment_id not in payments_by_id
            or rev.amount.currency != invoice.currency
            or rev.id in seen_reversals
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="balance.reversal.mismatch")
        parent = payments_by_id[rev.payment_id]
        validate_reversal(parent, rev.amount, grouped[rev.payment_id])
        grouped[rev.payment_id].append(rev)
        seen_reversals.add(rev.id)


def calculate_balance(
    invoice: Invoice,
    payments: Sequence[Payment],
    reversals: Sequence[PaymentReversal],
) -> BalanceSummary:
    """Derive net paid, outstanding debt and settlement status for an invoice.

    Args:
        invoice: Invoice whose balance is being calculated.
        payments: Posted payments associated with the invoice.
        reversals: Posted reversals associated with those payments.

    Returns:
        Immutable BalanceSummary reflecting exact decimal totals.

    Raises:
        ValidationError: If links mismatch or net payments exceed the invoice total.
    """
    if not isinstance(invoice, Invoice):
        raise ValidationError(code="INVALID_VALUE", message_key="balance.invoice.invalid")

    payments_by_id = _index_validated_payments(invoice, payments)
    _validate_grouped_reversals(invoice, payments_by_id, reversals)

    total = invoice.total()
    gross_paid = sum_money((p.amount for p in payments), invoice.currency)
    total_reversed = sum_money((r.amount for r in reversals), invoice.currency)
    net_paid = gross_paid.subtract(total_reversed)

    if net_paid.compare(total) > 0:
        raise ValidationError(
            code="PAYMENT_EXCEEDS_BALANCE",
            message_key="balance.net_paid.exceeds_total",
        )

    zero = Money(amount=Decimal("0.00"), currency=invoice.currency)
    if invoice.status == InvoiceStatus.VOID:
        if not net_paid.is_zero():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="balance.void_invoice.nonzero_paid",
            )
        return BalanceSummary(
            invoice_id=invoice.id,
            total=total,
            net_paid=zero,
            outstanding=zero,
            settlement=SettlementStatus.UNPAID,
        )

    outstanding = total.subtract(net_paid)
    if net_paid.is_zero():
        settlement = SettlementStatus.UNPAID
    elif outstanding.is_zero():
        settlement = SettlementStatus.PAID
    else:
        settlement = SettlementStatus.PARTIAL

    return BalanceSummary(
        invoice_id=invoice.id,
        total=total,
        net_paid=net_paid,
        outstanding=outstanding,
        settlement=settlement,
    )


def validate_payment(
    invoice: Invoice,
    amount: Money,
    payments: Sequence[Payment],
    reversals: Sequence[PaymentReversal],
) -> None:
    """Verify that a proposed payment is valid and does not exceed outstanding debt.

    Args:
        invoice: Issued Invoice receiving the payment.
        amount: Positive Money amount being paid.
        payments: Existing posted payments on the invoice.
        reversals: Existing posted reversals on those payments.

    Raises:
        ValidationError: If the invoice is not issued, amount is invalid, or payment exceeds debt.
    """
    if not isinstance(invoice, Invoice) or invoice.status != InvoiceStatus.ISSUED:
        raise ValidationError(
            code="INVALID_VALUE",
            message_key="payment.invoice.not_issued",
        )
    if (
        not isinstance(amount, Money)
        or amount.currency != invoice.currency
        or amount.amount <= Decimal("0.00")
    ):
        raise ValidationError(code="INVALID_VALUE", message_key="payment.amount.invalid")

    summary = calculate_balance(invoice, payments, reversals)
    if amount.compare(summary.outstanding) > 0:
        raise ValidationError(
            code="PAYMENT_EXCEEDS_BALANCE",
            message_key="payment.amount.exceeds_outstanding",
        )
