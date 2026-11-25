"""Unit tests for Payment, PaymentReversal, BalanceSummary and balance calculation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from clinic_management.application.contracts.billing import InvoiceSummary
from clinic_management.domain.billing.balance import (
    BalanceSummary,
    calculate_balance,
    validate_payment,
)
from clinic_management.domain.billing.enums import PaymentMethod, SettlementStatus
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.billing.invoice_line import InvoiceLine
from clinic_management.domain.billing.payment import Payment
from clinic_management.domain.billing.reversal import PaymentReversal, validate_reversal
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
CLINIC_ID = UUID(int=10)
PATIENT_ID = UUID(int=20)
ACTOR_ID = UUID(int=30)


def make_line(price: str = "1000.00") -> InvoiceLine:
    """Create a valid synthetic InvoiceLine for testing."""
    return InvoiceLine(
        line_id=UUID(int=1),
        description="Consultation service",
        quantity=Decimal("1"),
        unit_price=Money(amount=Decimal(price), currency="DZD"),
        discount_amount=Money(amount=Decimal("0.00"), currency="DZD"),
        tax_rate=Decimal("0"),
        source_service_id=UUID(int=100),
        source_consultation_id=UUID(int=200),
    )


def test_payment_reversal_and_balance_calculation() -> None:
    """BalanceSummary derives UNPAID, PARTIAL, PAID, voided and overdue states accurately."""
    inv = Invoice(
        id=UUID(int=1),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        currency="DZD",
        lines=(make_line("1000.00"),),
    )
    inv.issue("INV-01", at=NOW, due_on=date(2026, 11, 10))

    unpaid = calculate_balance(inv, (), ())
    assert unpaid.settlement == SettlementStatus.UNPAID
    assert unpaid.outstanding == Money(amount=Decimal("1000.00"), currency="DZD")
    assert not unpaid.is_overdue(due_on=inv.due_on, on_date=date(2026, 11, 10), issued=True)
    assert unpaid.is_overdue(due_on=inv.due_on, on_date=date(2026, 11, 11), issued=True)

    p1 = Payment(
        id=UUID(int=50),
        clinic_id=CLINIC_ID,
        invoice_id=inv.id,
        amount=Money(amount=Decimal("400.00"), currency="DZD"),
        method=PaymentMethod.CASH,
        received_at=NOW,
        received_by=ACTOR_ID,
        idempotency_key=UUID(int=60),
        external_reference="REC-01",
    )
    r1 = PaymentReversal(
        id=UUID(int=51),
        clinic_id=CLINIC_ID,
        payment_id=p1.id,
        amount=Money(amount=Decimal("100.00"), currency="DZD"),
        reason="Cash count correction",
        reversed_at=NOW,
        reversed_by=ACTOR_ID,
        idempotency_key=UUID(int=61),
    )

    partial = calculate_balance(inv, (p1,), (r1,))
    assert partial.net_paid == Money(amount=Decimal("300.00"), currency="DZD")
    assert partial.outstanding == Money(amount=Decimal("700.00"), currency="DZD")
    assert partial.settlement == SettlementStatus.PARTIAL

    validate_payment(
        inv,
        Money(amount=Decimal("700.00"), currency="DZD"),
        (p1,),
        (r1,),
    )
    with pytest.raises(ValidationError):
        validate_payment(
            inv,
            Money(amount=Decimal("700.01"), currency="DZD"),
            (p1,),
            (r1,),
        )

    p2 = Payment(
        id=UUID(int=52),
        clinic_id=CLINIC_ID,
        invoice_id=inv.id,
        amount=Money(amount=Decimal("700.00"), currency="DZD"),
        method=PaymentMethod.CARD,
        received_at=NOW,
        received_by=ACTOR_ID,
        idempotency_key=UUID(int=62),
    )
    paid = calculate_balance(inv, (p1, p2), (r1,))
    assert paid.settlement == SettlementStatus.PAID
    assert paid.outstanding.is_zero()


def test_void_balance_and_dto_validation() -> None:
    """Voided invoices report zero outstanding and InvoiceSummary validates fields."""
    inv = Invoice(
        id=UUID(int=1),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        currency="DZD",
        lines=(make_line("500.00"),),
    )
    inv.issue("INV-02", at=NOW, due_on=date(2026, 11, 10))
    inv.void("Duplicate", net_paid=Money(amount=Decimal("0.00"), currency="DZD"), at=NOW)

    bal = calculate_balance(inv, (), ())
    assert bal.outstanding.is_zero()
    assert bal.settlement == SettlementStatus.UNPAID

    summary = InvoiceSummary(
        invoice_id=inv.id,
        patient_id=PATIENT_ID,
        number=inv.number,
        status=inv.status,
        total=bal.total,
        outstanding=bal.outstanding,
        due_on=inv.due_on,
        version=inv.version,
    )
    assert summary.invoice_id == inv.id

    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=inv.id,
            patient_id=PATIENT_ID,
            number=inv.number,
            status=inv.status,
            total=bal.total,
            outstanding=bal.outstanding,
            due_on=inv.due_on,
            version=-1,
        )


def test_reversal_and_balance_error_branches() -> None:
    """Invalid links, duplicate records and naive timestamps fail validation."""
    inv = Invoice(
        id=UUID(int=1),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        currency="DZD",
        lines=(make_line("200.00"),),
    )
    inv.issue("INV-03", at=NOW, due_on=date(2026, 11, 10))
    p1 = Payment(
        id=UUID(int=70),
        clinic_id=CLINIC_ID,
        invoice_id=inv.id,
        amount=Money(amount=Decimal("200.00"), currency="DZD"),
        method=PaymentMethod.CASH,
        received_at=NOW,
        received_by=ACTOR_ID,
        idempotency_key=UUID(int=80),
    )
    r1 = PaymentReversal(
        id=UUID(int=71),
        clinic_id=CLINIC_ID,
        payment_id=p1.id,
        amount=Money(amount=Decimal("50.00"), currency="DZD"),
        reason="Partial refund",
        reversed_at=NOW,
        reversed_by=ACTOR_ID,
        idempotency_key=UUID(int=81),
    )
    validate_reversal(p1, Money(amount=Decimal("150.00"), currency="DZD"), (r1,))
    with pytest.raises(ValidationError):
        validate_reversal(p1, Money(amount=Decimal("151.00"), currency="DZD"), (r1,))
    with pytest.raises(ValidationError):
        calculate_balance(inv, (p1, p1), ())
    with pytest.raises(ValidationError):
        calculate_balance(inv, (p1,), (r1, r1))

    summary = calculate_balance(inv, (p1,), (r1,))
    with pytest.raises(ValidationError):
        summary.is_overdue(
            due_on=inv.due_on, on_date=cast("date", datetime(2026, 11, 1, tzinfo=UTC)), issued=True
        )
    with pytest.raises(ValidationError):
        summary.is_overdue(
            due_on=cast("date", datetime(2026, 11, 1, tzinfo=UTC)),
            on_date=date(2026, 11, 1),
            issued=True,
        )
    with pytest.raises(ValidationError):
        BalanceSummary(
            invoice_id=inv.id,
            total=Money(amount=Decimal("10.00"), currency="DZD"),
            net_paid=Money(amount=Decimal("0.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("10.00"), currency="DZD"),
            settlement=cast("SettlementStatus", "INVALID"),
        )
    with pytest.raises(ValidationError):
        Payment(
            id=UUID(int=72),
            clinic_id=CLINIC_ID,
            invoice_id=inv.id,
            amount=Money(amount=Decimal("10.00"), currency="DZD"),
            method=PaymentMethod.CASH,
            received_at=NOW,
            received_by=ACTOR_ID,
            idempotency_key=UUID(int=82),
            external_reference="   ",
        )
    with pytest.raises(ValidationError):
        PaymentReversal(
            id=UUID(int=73),
            clinic_id=CLINIC_ID,
            payment_id=p1.id,
            amount=Money(amount=Decimal("10.00"), currency="DZD"),
            reason="   ",
            reversed_at=NOW,
            reversed_by=ACTOR_ID,
            idempotency_key=UUID(int=83),
        )
    with pytest.raises(ValidationError):
        validate_payment(
            inv,
            Money(amount=Decimal("10.00"), currency="USD"),
            (p1,),
            (r1,),
        )
    with pytest.raises(ValidationError):
        validate_reversal(
            p1,
            Money(amount=Decimal("10.00"), currency="USD"),
            (r1,),
        )
    with pytest.raises(ValidationError):
        Payment(
            id=UUID(int=74),
            clinic_id=CLINIC_ID,
            invoice_id=inv.id,
            amount=Money(amount=Decimal("10.00"), currency="DZD"),
            method=PaymentMethod.CASH,
            received_at=datetime(2026, 11, 1, 10, 0),
            received_by=ACTOR_ID,
            idempotency_key=UUID(int=84),
        )
    with pytest.raises(ValidationError):
        PaymentReversal(
            id=UUID(int=75),
            clinic_id=CLINIC_ID,
            payment_id=p1.id,
            amount=Money(amount=Decimal("10.00"), currency="DZD"),
            reason="Refund",
            reversed_at=datetime(2026, 11, 1, 10, 0),
            reversed_by=ACTOR_ID,
            idempotency_key=UUID(int=85),
        )
    with pytest.raises(ValidationError):
        validate_reversal(
            cast("Payment", "not-a-payment"), Money(amount=Decimal("10.00"), currency="DZD"), ()
        )
    with pytest.raises(ValidationError):
        validate_reversal(p1, Money(amount=Decimal("-1.00"), currency="DZD"), ())
    with pytest.raises(ValidationError):
        validate_reversal(
            p1,
            Money(amount=Decimal("10.00"), currency="DZD"),
            cast("Sequence[PaymentReversal]", ("not-a-reversal",)),
        )
    with pytest.raises(ValidationError):
        Payment(
            id=UUID(int=76),
            clinic_id=CLINIC_ID,
            invoice_id=inv.id,
            amount=Money(amount=Decimal("-10.00"), currency="DZD"),
            method=PaymentMethod.CASH,
            received_at=NOW,
            received_by=ACTOR_ID,
            idempotency_key=UUID(int=86),
        )
    with pytest.raises(ValidationError):
        Payment(
            id=UUID(int=77),
            clinic_id=CLINIC_ID,
            invoice_id=inv.id,
            amount=Money(amount=Decimal("10.00"), currency="DZD"),
            method=cast("PaymentMethod", "INVALID"),
            received_at=NOW,
            received_by=ACTOR_ID,
            idempotency_key=UUID(int=87),
        )
