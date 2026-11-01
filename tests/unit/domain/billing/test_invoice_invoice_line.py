"""Unit tests for Invoice, InvoiceLine, DTO contracts and validation helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from clinic_management.application.contracts.billing import InvoiceSummary
from clinic_management.application.ports.billing import (
    InvoiceNumberGenerator,
    InvoiceRepository,
    PaymentRepository,
)
from clinic_management.domain.billing._validation import require_optional_uuid, require_uuid_value
from clinic_management.domain.billing.enums import InvoiceStatus
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.billing.invoice_line import InvoiceLine
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError
from clinic_management.domain.shared.money import Money

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
CLINIC_ID = UUID(int=10)
PATIENT_ID = UUID(int=20)


def make_line(
    line_id: int = 1,
    price: str = "1000.00",
    quantity: str = "1",
    discount: str = "0.00",
    tax_rate: str = "0.00",
    service_id: int | None = 100,
    consultation_id: int | None = 200,
) -> InvoiceLine:
    """Create a valid synthetic InvoiceLine for testing."""
    return InvoiceLine(
        line_id=UUID(int=line_id),
        description="Consultation service",
        quantity=Decimal(quantity),
        unit_price=Money(amount=Decimal(price), currency="DZD"),
        discount_amount=Money(amount=Decimal(discount), currency="DZD"),
        tax_rate=Decimal(tax_rate),
        source_service_id=UUID(int=service_id) if service_id is not None else None,
        source_consultation_id=(UUID(int=consultation_id) if consultation_id is not None else None),
    )


def make_draft_invoice(lines: tuple[InvoiceLine, ...] = ()) -> Invoice:
    """Create a synthetic draft Invoice for testing."""
    return Invoice(
        id=UUID(int=1),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        currency="DZD",
        lines=lines,
    )


def status_of(invoice: Invoice) -> InvoiceStatus:
    """Return the current status without mypy carrying over earlier narrowing."""
    return invoice.status


def test_invoice_line_calculations_and_validation() -> None:
    """InvoiceLine computes subtotal, tax and total and rejects invalid inputs."""
    line = make_line(price="500.00", quantity="2", discount="100.00", tax_rate="0.10")
    assert line.subtotal() == Money(amount=Decimal("900.00"), currency="DZD")
    assert line.tax() == Money(amount=Decimal("90.00"), currency="DZD")
    assert line.total() == Money(amount=Decimal("990.00"), currency="DZD")

    with pytest.raises(ValidationError):
        make_line(quantity="0")
    with pytest.raises(ValidationError):
        make_line(price="-1.00")
    with pytest.raises(ValidationError):
        make_line(discount="1001.00")
    with pytest.raises(ValidationError):
        make_line(tax_rate="1.5")
    with pytest.raises(ValidationError):
        InvoiceLine(
            line_id=UUID(int=1),
            description="   ",
            quantity=Decimal("1"),
            unit_price=Money(amount=Decimal("10.00"), currency="DZD"),
            discount_amount=Money(amount=Decimal("0.00"), currency="DZD"),
            tax_rate=Decimal("0"),
            source_service_id=None,
            source_consultation_id=None,
        )


def test_invoice_draft_editing_issuance_and_void_lifecycle() -> None:
    """Invoice enforces draft line modifications, issuance checks and zero-paid voiding."""
    line1 = make_line(line_id=1, price="1000.00", service_id=10, consultation_id=20)
    line2 = make_line(line_id=2, price="500.00", service_id=11, consultation_id=20)
    inv = make_draft_invoice((line1,))
    inv.add_line(line2)
    assert len(inv.lines()) == 2
    assert inv.total() == Money(amount=Decimal("1500.00"), currency="DZD")

    with pytest.raises(ValidationError):
        inv.add_line(make_line(line_id=1, service_id=99, consultation_id=99))
    with pytest.raises(ValidationError):
        inv.add_line(make_line(line_id=3, service_id=10, consultation_id=20))

    inv.remove_line(UUID(int=2))
    assert len(inv.lines()) == 1
    with pytest.raises(ValidationError):
        inv.remove_line(UUID(int=999))

    inv.issue("INV-2026-0001", at=NOW, due_on=date(2026, 11, 15))
    assert status_of(inv) == InvoiceStatus.ISSUED

    with pytest.raises(InvalidTransitionError):
        inv.add_line(line2)
    with pytest.raises(InvalidTransitionError):
        inv.remove_line(UUID(int=1))
    with pytest.raises(InvalidTransitionError):
        inv.issue("INV-2026-0002", at=NOW, due_on=date(2026, 11, 15))

    with pytest.raises(InvalidTransitionError):
        inv.void(
            "Error",
            net_paid=Money(amount=Decimal("100.00"), currency="DZD"),
            at=NOW,
        )
    inv.void(
        "Billed wrong patient",
        net_paid=Money(amount=Decimal("0.00"), currency="DZD"),
        at=NOW,
    )
    assert status_of(inv) == InvoiceStatus.VOID


def test_invoice_validation_failures() -> None:
    """Empty draft cannot be issued and invalid constructor states raise ValidationError."""
    empty_inv = make_draft_invoice()
    with pytest.raises(ValidationError):
        empty_inv.issue("INV-1", at=NOW, due_on=NOW.date())
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=InvoiceStatus.ISSUED,
            number=None,
            issued_at=NOW,
            due_on=date(2026, 11, 15),
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=InvoiceStatus.ISSUED,
            number="INV-1",
            issued_at=None,
            due_on=None,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=InvoiceStatus.VOID,
            number="INV-1",
            issued_at=NOW,
            due_on=date(2026, 11, 15),
            void_reason=None,
            voided_at=NOW,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=InvoiceStatus.VOID,
            number="INV-1",
            issued_at=NOW,
            due_on=date(2026, 11, 15),
            void_reason="cancelled",
            voided_at=None,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=cast("InvoiceStatus", "INVALID"),
            number=None,
            issued_at=None,
            due_on=None,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=InvoiceStatus.ISSUED,
            number="   ",
            issued_at=NOW,
            due_on=date(2026, 11, 15),
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            status=InvoiceStatus.VOID,
            number="INV-1",
            issued_at=NOW,
            due_on=date(2026, 11, 15),
            void_reason="   ",
            voided_at=NOW,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(price="1000.00"), make_line(price="500.00", line_id=1)),
            status=InvoiceStatus.DRAFT,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(
                make_line(line_id=1, service_id=10, consultation_id=20),
                make_line(line_id=2, service_id=10, consultation_id=20),
            ),
            status=InvoiceStatus.DRAFT,
        )


def test_invoice_summary_contract_validation() -> None:
    """InvoiceSummary validates identifiers, currency and date types."""
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=cast("UUID", "not-a-uuid"),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=date(2026, 11, 15),
            version=0,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=cast("UUID", "not-a-uuid"),
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=date(2026, 11, 15),
            version=0,
        )


def test_internal_billing_validation_helpers() -> None:
    """Cover internal validation helper branches in _validation.py."""
    with pytest.raises(ValidationError):
        require_uuid_value(cast("UUID", "not-a-uuid"))
    with pytest.raises(ValidationError):
        require_optional_uuid(cast("UUID", "not-a-uuid"))
    assert require_optional_uuid(None) is None


def test_ports_protocol_existence() -> None:
    """Ensure protocol ports can be referenced without error."""
    assert InvoiceRepository is not None
    assert PaymentRepository is not None
    assert InvoiceNumberGenerator is not None


def test_invoice_summary_accepts_valid_values() -> None:
    """InvoiceSummary accepts valid values with and without a due date."""
    summary = InvoiceSummary(
        invoice_id=UUID(int=1),
        patient_id=PATIENT_ID,
        number=None,
        status=InvoiceStatus.DRAFT,
        total=Money(amount=Decimal("100.00"), currency="DZD"),
        outstanding=Money(amount=Decimal("100.00"), currency="DZD"),
        due_on=None,
        version=0,
    )
    assert summary.due_on is None
    dated = InvoiceSummary(
        invoice_id=UUID(int=1),
        patient_id=PATIENT_ID,
        number="INV-1",
        status=InvoiceStatus.ISSUED,
        total=Money(amount=Decimal("100.00"), currency="DZD"),
        outstanding=Money(amount=Decimal("50.00"), currency="DZD"),
        due_on=date(2026, 11, 15),
        version=1,
    )
    assert dated.due_on == date(2026, 11, 15)


def test_invoice_summary_rejects_invalid_status_money_due_on_and_version() -> None:
    """InvoiceSummary rejects bad status, money, due date and version values."""
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=cast("InvoiceStatus", "ISSUED"),
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=date(2026, 11, 15),
            version=0,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=cast("Money", "100.00"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=date(2026, 11, 15),
            version=0,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="USD"),
            due_on=date(2026, 11, 15),
            version=0,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=NOW,
            version=0,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=cast("date", "2026-11-15"),
            version=0,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=date(2026, 11, 15),
            version=-1,
        )
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=UUID(int=1),
            patient_id=PATIENT_ID,
            number="INV-1",
            status=InvoiceStatus.ISSUED,
            total=Money(amount=Decimal("100.00"), currency="DZD"),
            outstanding=Money(amount=Decimal("0.00"), currency="DZD"),
            due_on=date(2026, 11, 15),
            version=cast("int", True),
        )


def test_invoice_rejects_bad_version_line_type_and_empty_issued() -> None:
    """Invoice rejects invalid versions, non-line items and issued invoices without lines."""
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            version=-1,
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(make_line(),),
            version=cast("int", True),
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(cast("InvoiceLine", "not-a-line"),),
        )
    with pytest.raises(ValidationError):
        Invoice(
            id=UUID(int=1),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            currency="DZD",
            lines=(),
            status=InvoiceStatus.ISSUED,
            number="INV-1",
            issued_at=NOW,
            due_on=date(2026, 11, 15),
        )
