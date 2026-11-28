"""Independent payment, reversal, scope, debt and overdue acceptance cases."""

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from itertools import permutations
from uuid import UUID

import pytest

from clinic_management.domain.billing.balance import calculate_balance, validate_payment
from clinic_management.domain.billing.enums import SettlementStatus
from clinic_management.domain.billing.reversal import validate_reversal
from clinic_management.domain.shared.errors import ValidationError
from tests.independent.m1.billing_fixtures import (
    AT,
    CLINIC_ID,
    INVOICE_ID,
    amount,
    draft,
    issued,
    posted,
    reversal,
)
from tests.support.fault_injection import assign_unchecked


@pytest.mark.parametrize(
    ("paid", "debt", "status"),
    [
        ("0", "1000", SettlementStatus.UNPAID),
        ("400", "600", SettlementStatus.PARTIAL),
        ("1000", "0", SettlementStatus.PAID),
    ],
)
def test_derived_settlement_matches_exact_net_funds(
    paid: str, debt: str, status: SettlementStatus
) -> None:
    """Unpaid, partial and paid examples have explicit independent expected balances."""
    payments = () if paid == "0" else (posted(paid),)
    result = calculate_balance(issued(), payments, ())
    assert result.total == amount("1000")
    assert result.net_paid == amount(paid)
    assert result.outstanding == amount(debt)
    assert result.settlement is status


def test_multiple_payment_and_reversal_order_does_not_change_the_balance() -> None:
    """Ledger facts are order-independent and each correction reduces its own payment."""
    payments = (
        posted("100", identifier=10),
        posted("200", identifier=11),
        posted("300", identifier=12),
    )
    corrections = (
        reversal("40", identifier=20, payment_id=UUID(int=10)),
        reversal("60", identifier=21, payment_id=UUID(int=11)),
    )
    for ordered_payments in permutations(payments):
        for ordered_reversals in permutations(corrections):
            result = calculate_balance(issued(), ordered_payments, ordered_reversals)
            assert result.net_paid == amount("500")
            assert result.outstanding == amount("500")
            assert result.settlement is SettlementStatus.PARTIAL


def test_reversed_money_can_be_replaced_without_rejecting_historical_gross_receipts() -> None:
    """1000 received, 500 reversed and 500 received again settles a 1000 invoice."""
    payments = (posted("1000"), posted("500", identifier=11))
    result = calculate_balance(issued(), payments, (reversal("500"),))
    assert result.net_paid == amount("1000")
    assert result.outstanding == amount("0")
    assert result.settlement is SettlementStatus.PAID


@pytest.mark.parametrize("value", ["0", "-0.01", "600.01"])
def test_proposed_payment_rejects_nonpositive_or_excess_amount(value: str) -> None:
    """The 600 remaining after a 400 payment is a strict upper allocation bound."""
    with pytest.raises(ValidationError):
        validate_payment(issued(), amount(value), (posted(),), ())


def test_exact_remaining_payment_is_allowed_without_mutating_ledger_facts() -> None:
    """Snapshot validation permits the exact balance and posts no records itself."""
    payment = posted()
    history = [payment]
    validate_payment(issued(), amount("600"), history, ())
    assert history == [payment]
    assert payment.amount == amount("400")
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(payment, "amount", amount("999"))
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(reversal(), "reason", "Changed")


def test_unissued_or_void_invoices_cannot_receive_new_payments() -> None:
    """Only the issued state can pass pure allocation validation."""
    void = issued()
    void.void("Synthetic correction", net_paid=amount("0"), at=AT)
    for invoice in (draft(), void):
        with pytest.raises(ValidationError):
            validate_payment(invoice, amount("1"), (), ())


@pytest.mark.parametrize(
    ("clinic_id", "invoice_id"),
    [(UUID(int=999), INVOICE_ID), (CLINIC_ID, UUID(int=999))],
)
def test_payment_scope_cannot_be_mixed_between_invoices_or_clinics(
    clinic_id: UUID, invoice_id: UUID
) -> None:
    """A matching amount never compensates for a wrong clinic or invoice link."""
    with pytest.raises(ValidationError):
        calculate_balance(issued(), (posted(clinic_id=clinic_id, invoice_id=invoice_id),), ())


@pytest.mark.parametrize(
    ("clinic_id", "payment_id"),
    [(UUID(int=999), UUID(int=10)), (CLINIC_ID, UUID(int=999))],
)
def test_reversal_scope_and_parent_links_are_checked(clinic_id: UUID, payment_id: UUID) -> None:
    """Foreign or orphan corrections cannot reduce this invoice's debt."""
    with pytest.raises(ValidationError):
        calculate_balance(
            issued(), (posted(),), (reversal(clinic_id=clinic_id, payment_id=payment_id),)
        )


def test_duplicate_posted_ids_and_duplicate_reversal_ids_are_rejected() -> None:
    """Duplicate history rows cannot count the same received or reversed funds twice."""
    payment, correction = posted(), reversal()
    with pytest.raises(ValidationError):
        calculate_balance(issued(), (payment, payment), ())
    with pytest.raises(ValidationError):
        calculate_balance(issued(), (payment,), (correction, correction))


def test_reversal_remaining_bound_and_invalid_history_are_checked() -> None:
    """After 100 of 400 is reversed, another 300 is valid but 300.01 is not."""
    payment, correction = posted(), reversal()
    validate_reversal(payment, amount("300"), (correction,))
    for value in ("0", "-0.01", "300.01"):
        with pytest.raises(ValidationError):
            validate_reversal(payment, amount(value), (correction,))
    with pytest.raises(ValidationError):
        validate_reversal(payment, amount("1"), (correction, correction))
    with pytest.raises(ValidationError):
        calculate_balance(issued(), (payment,), (reversal("400.01"),))
    assert payment.amount == amount("400")


def test_overpayment_and_void_reconciliation_cannot_be_hidden_by_a_summary() -> None:
    """Invalid ledger allocations fail before a plausible-looking summary is returned."""
    with pytest.raises(ValidationError):
        calculate_balance(issued(), (posted("1000.01"),), ())
    void = issued()
    void.void("Synthetic correction", net_paid=amount("0"), at=AT)
    with pytest.raises(ValidationError):
        calculate_balance(void, (posted(),), ())
    corrected = calculate_balance(void, (posted(),), (reversal("400"),))
    assert corrected.outstanding == amount("0")
    assert corrected.net_paid == amount("0")


def test_overdue_depends_on_explicit_date_debt_and_issued_state() -> None:
    """The due day itself is not overdue; paid or unissued documents are not overdue."""
    balance = calculate_balance(issued(), (posted(),), ())
    due = AT.date()
    assert not balance.is_overdue(due_on=due, on_date=due, issued=True)
    assert balance.is_overdue(due_on=due, on_date=due + timedelta(days=1), issued=True)
    assert not balance.is_overdue(due_on=due, on_date=due + timedelta(days=1), issued=False)
    assert not balance.is_overdue(due_on=None, on_date=due + timedelta(days=1), issued=True)
    paid = calculate_balance(issued(), (posted("1000"),), ())
    assert not paid.is_overdue(due_on=due, on_date=due + timedelta(days=1), issued=True)


@pytest.mark.parametrize("value", ["0", "-0.01"])
def test_posted_payment_and_reversal_constructors_require_positive_amounts(value: str) -> None:
    """Invalid immutable ledger facts fail even before any allocation helper runs."""
    with pytest.raises(ValidationError):
        posted(value)
    with pytest.raises(ValidationError):
        reversal(value)


def test_posted_records_reject_naive_timestamps_on_construction() -> None:
    """Both posted record types require timezone-aware authoritative instants."""
    with pytest.raises(ValidationError):
        replace(posted(), received_at=AT.replace(tzinfo=None))
    with pytest.raises(ValidationError):
        replace(reversal(), reversed_at=AT.replace(tzinfo=None))
