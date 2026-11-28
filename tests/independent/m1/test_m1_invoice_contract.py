"""Independent invoice arithmetic, snapshot and lifecycle acceptance tests."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from clinic_management.application.contracts.billing import InvoiceSummary
from clinic_management.domain.billing.enums import InvoiceStatus
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError
from tests.independent.m1.billing_fixtures import (
    AT,
    CLINIC_ID,
    INVOICE_ID,
    amount,
    draft,
    issued,
    line,
    status_of,
)
from tests.support.fault_injection import assign_unchecked


@pytest.mark.parametrize(
    ("price", "quantity", "discount", "rate", "subtotal", "tax", "total"),
    [
        ("0.05", "3", "0.01", "0.10", "0.14", "0.01", "0.15"),
        ("19.99", "1.5", "0.99", "0.15", "29.00", "4.35", "33.35"),
        ("10.05", "2", "1.10", "0.195", "19.00", "3.71", "22.71"),
    ],
)
def test_line_formula_rounds_gross_then_discount_then_tax(
    price: str, quantity: str, discount: str, rate: str, subtotal: str, tax: str, total: str
) -> None:
    """Invoice values follow independently calculated fractional-quantity examples."""
    item = line(price=price, quantity=quantity, discount=discount, tax_rate=rate)
    assert item.subtotal().amount == Decimal(subtotal)
    assert item.tax().amount == Decimal(tax)
    assert item.total().amount == Decimal(total)


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "sNaN", "Infinity"])
def test_line_rejects_nonpositive_or_nonfinite_quantity(quantity: str) -> None:
    """A line cannot bill an invalid quantity even with otherwise valid money."""
    with pytest.raises(ValidationError):
        line(quantity=quantity)


@pytest.mark.parametrize("rate", ["-0.01", "1.01", "NaN", "Infinity"])
def test_line_rejects_invalid_fractional_tax(rate: str) -> None:
    """Line-level tax policy is bounded to finite fractions in [0, 1]."""
    with pytest.raises(ValidationError):
        line(tax_rate=rate)


@pytest.mark.parametrize("discount", ["-0.01", "1000.01"])
def test_line_discount_cannot_create_negative_or_inflated_charges(discount: str) -> None:
    """A discount stays between zero and the rounded gross amount."""
    with pytest.raises(ValidationError):
        line(discount=discount)


def test_owned_immutable_snapshots_and_sum_of_rounded_lines() -> None:
    """Caller mutation cannot alter owned lines; totals sum rounded line amounts."""
    original = [
        line(identifier=100, price="0.01", quantity="0.5"),
        line(identifier=101, price="0.01", quantity="0.5"),
    ]
    value = draft(original)
    original.clear()
    assert len(value.lines()) == 2
    assert isinstance(value.lines(), tuple)
    assert value.total() == amount("0.02")
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(value.lines()[0], "description", "Changed")
    value.issue("M1-SYN-0002", at=AT, due_on=AT.date())
    with pytest.raises(InvalidTransitionError):
        value.remove_line(UUID(int=100))
    assert len(value.lines()) == 2


def test_duplicate_line_and_source_rejections_do_not_partially_modify_the_draft() -> None:
    """Rejected duplicate IDs or service/visit pairs leave the original draft intact."""
    first = line(service_id=UUID(int=8), consultation_id=UUID(int=9))
    value = draft([first])
    for duplicate in (first, replace(first, line_id=UUID(int=101))):
        with pytest.raises(ValidationError):
            value.add_line(duplicate)
        assert value.lines() == (first,)
        assert value.status is InvoiceStatus.DRAFT


def test_rejected_issuance_preserves_all_draft_metadata() -> None:
    """Input failures occur before any invoice fields change."""
    value = draft()
    invalid = [
        (" ", AT, AT.date()),
        ("M1-SYN-3", AT.replace(tzinfo=None), AT.date()),
        ("M1-SYN-3", AT, AT.date() - timedelta(days=1)),
    ]
    for number, at, due in invalid:
        with pytest.raises(ValidationError):
            value.issue(number, at=at, due_on=due)
        assert (value.status, value.number, value.issued_at, value.due_on) == (
            InvoiceStatus.DRAFT,
            None,
            None,
            None,
        )
        assert value.total() == amount("1000")


def test_payment_reconciliation_gates_voiding_and_preserves_document_history() -> None:
    """Unreconciled money blocks void; a zero-net void retains original evidence."""
    value = issued()
    history = (value.number, value.issued_at, value.lines())
    with pytest.raises(InvalidTransitionError):
        value.void("Synthetic correction", net_paid=amount("0.01"), at=AT)
    assert status_of(value) is InvoiceStatus.ISSUED
    value.void("Synthetic correction", net_paid=amount("0"), at=AT)
    assert status_of(value) is InvoiceStatus.VOID
    assert (value.number, value.issued_at, value.lines()) == history
    with pytest.raises(InvalidTransitionError):
        value.issue("M1-SYN-4", at=AT, due_on=AT.date())
    with pytest.raises(InvalidTransitionError):
        value.add_line(line(identifier=102))


@pytest.mark.parametrize("due", [date(2026, 10, 31), AT])
@pytest.mark.parametrize("status", [InvoiceStatus.ISSUED, InvoiceStatus.VOID])
def test_rehydration_cannot_bypass_the_issue_due_date_invariant(
    due: date, status: InvoiceStatus
) -> None:
    """Posted-state constructors reject the same invalid due dates as issue()."""
    with pytest.raises(ValidationError):
        Invoice(
            id=INVOICE_ID,
            clinic_id=CLINIC_ID,
            patient_id=UUID(int=3),
            currency="DZD",
            lines=(line(),),
            status=status,
            number="M1-SYN-0001",
            issued_at=AT,
            due_on=due,
            void_reason="Synthetic correction" if status is InvoiceStatus.VOID else None,
            voided_at=AT if status is InvoiceStatus.VOID else None,
        )


def test_due_date_must_be_a_date_on_the_public_transition_too() -> None:
    """A datetime is not silently accepted as the issue() due-date calendar value."""
    value = draft()
    with pytest.raises(ValidationError):
        value.issue("M1-SYN-5", at=AT, due_on=datetime.fromisoformat(AT.isoformat()))


def test_invoice_summary_is_frozen_and_exposes_only_the_published_billing_projection() -> None:
    """The query DTO has no clinical narrative, account credentials or mutable state."""
    summary = InvoiceSummary(
        invoice_id=INVOICE_ID,
        patient_id=UUID(int=3),
        number="M1-SYN-0001",
        status=InvoiceStatus.ISSUED,
        total=amount("1000"),
        outstanding=amount("600"),
        due_on=AT.date(),
        version=1,
    )
    assert {field.name for field in fields(summary)} == {
        "invoice_id",
        "patient_id",
        "number",
        "status",
        "total",
        "outstanding",
        "due_on",
        "version",
    }
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(summary, "outstanding", amount("0"))


@pytest.mark.parametrize("version", [-1, True])
def test_invoice_summary_rejects_invalid_versions(version: int) -> None:
    """Negative versions and booleans cannot become concurrency metadata."""
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=INVOICE_ID,
            patient_id=UUID(int=3),
            number=None,
            status=InvoiceStatus.DRAFT,
            total=amount("1000"),
            outstanding=amount("1000"),
            due_on=None,
            version=version,
        )


def test_invoice_summary_rejects_datetime_due_dates() -> None:
    """The transport query contract preserves the calendar-date field type too."""
    with pytest.raises(ValidationError):
        InvoiceSummary(
            invoice_id=INVOICE_ID,
            patient_id=UUID(int=3),
            number="M1-SYN-0001",
            status=InvoiceStatus.ISSUED,
            total=amount("1000"),
            outstanding=amount("600"),
            due_on=AT,
            version=1,
        )
