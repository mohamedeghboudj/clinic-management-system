"""Synthetic public-API fixtures owned by M1, independent of M5's test helpers."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.billing.enums import InvoiceStatus, PaymentMethod
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.billing.invoice_line import InvoiceLine
from clinic_management.domain.billing.payment import Payment
from clinic_management.domain.billing.reversal import PaymentReversal
from clinic_management.domain.shared.money import Money

AT = datetime(2026, 11, 1, 10, tzinfo=UTC)
CLINIC_ID = UUID(int=2)
INVOICE_ID = UUID(int=1)
PAYMENT_ID = UUID(int=10)


def amount(value: str) -> Money:
    """Create an exact-decimal synthetic DZD value.

    Args:
        value: Decimal text.

    Returns:
        The submitted Money implementation.
    """
    return Money(amount=Decimal(value), currency="DZD")


def line(
    *,
    identifier: int = 100,
    price: str = "1000",
    quantity: str = "1",
    discount: str = "0",
    tax_rate: str = "0",
    service_id: UUID | None = None,
    consultation_id: UUID | None = None,
) -> InvoiceLine:
    """Build one immutable invoice line through its public constructor.

    Args:
        identifier: Unique line fixture integer.
        price: Exact unit price.
        quantity: Exact fractional quantity.
        discount: Exact discount amount.
        tax_rate: Fractional tax rate.
        service_id: Optional catalogue reference.
        consultation_id: Optional source visit reference.

    Returns:
        An actual InvoiceLine, never a replacement implementation.
    """
    return InvoiceLine(
        line_id=UUID(int=identifier),
        description="Synthetic service",
        quantity=Decimal(quantity),
        unit_price=amount(price),
        discount_amount=amount(discount),
        tax_rate=Decimal(tax_rate),
        source_service_id=service_id,
        source_consultation_id=consultation_id,
    )


def draft(lines: Sequence[InvoiceLine] | None = None) -> Invoice:
    """Create a draft invoice with explicit clinic and patient scope.

    Args:
        lines: Optional caller-owned lines; defaults to a 1000 DZD example.

    Returns:
        An actual draft aggregate.
    """
    return Invoice(
        id=INVOICE_ID,
        clinic_id=CLINIC_ID,
        patient_id=UUID(int=3),
        currency="DZD",
        lines=(line(),) if lines is None else lines,
    )


def issued() -> Invoice:
    """Issue the synthetic 1000 DZD draft using explicit authoritative time.

    Returns:
        An issued invoice with all required metadata.
    """
    value = draft()
    value.issue("M1-SYN-0001", at=AT, due_on=AT.date())
    return value


def status_of(value: Invoice) -> InvoiceStatus:
    """Read current state afresh after a mutating domain operation.

    Args:
        value: Invoice being exercised.

    Returns:
        Its current state without retaining static narrowing across mutations.
    """
    return value.status


def posted(
    value: str = "400",
    *,
    identifier: int = 10,
    clinic_id: UUID = CLINIC_ID,
    invoice_id: UUID = INVOICE_ID,
) -> Payment:
    """Create a posted payment with no real financial or identity data.

    Args:
        value: Positive amount to post.
        identifier: Unique payment fixture integer.
        clinic_id: Clinic scope, overridable for negative cases.
        invoice_id: Invoice link, overridable for negative cases.

    Returns:
        The actual immutable posted record.
    """
    return Payment(
        id=UUID(int=identifier),
        clinic_id=clinic_id,
        invoice_id=invoice_id,
        amount=amount(value),
        method=PaymentMethod.CASH,
        received_at=AT,
        received_by=UUID(int=4),
        idempotency_key=UUID(int=identifier + 1000),
        external_reference=None,
    )


def reversal(
    value: str = "100",
    *,
    identifier: int = 20,
    clinic_id: UUID = CLINIC_ID,
    payment_id: UUID = PAYMENT_ID,
) -> PaymentReversal:
    """Build an immutable correction linked to one posted payment.

    Args:
        value: Positive reversal amount.
        identifier: Unique correction fixture integer.
        clinic_id: Clinic scope, overridable for negative cases.
        payment_id: Parent link, overridable for negative cases.

    Returns:
        The submitted PaymentReversal implementation.
    """
    return PaymentReversal(
        id=UUID(int=identifier),
        clinic_id=clinic_id,
        payment_id=payment_id,
        amount=amount(value),
        reason="Synthetic correction",
        reversed_at=AT,
        reversed_by=UUID(int=4),
        idempotency_key=UUID(int=identifier + 1000),
    )
