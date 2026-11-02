"""Verification tests for shared Money value object and rounding helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import (
    Money,
    percentage_of,
    quantize_amount,
    sum_money,
)


def test_money_creation_and_currency_validation() -> None:
    """Verify Money creation with supported currency and reject unsupported currencies."""
    m = Money(amount=Decimal("150.50"), currency="DZD")
    assert m.amount == Decimal("150.50")
    assert m.currency == "DZD"

    # Unsupported currency
    with pytest.raises(ValidationError) as exc:
        Money(amount=Decimal("100.00"), currency="USD")
    assert exc.value.message_key == "money.currency.unsupported"

    # Non-string currency
    with pytest.raises(ValidationError):
        Money(amount=Decimal("100.00"), currency=123)  # type: ignore[arg-type]

    # Non-decimal amount
    with pytest.raises(ValidationError):
        Money(amount=100.0, currency="DZD")  # type: ignore[arg-type]

    # Non-finite decimal
    with pytest.raises(ValidationError):
        Money(amount=Decimal("NaN"), currency="DZD")

    with pytest.raises(ValidationError):
        Money(amount=Decimal("Infinity"), currency="DZD")


def test_quantize_amount_negative_zero_and_rounding() -> None:
    """Verify quantize_amount maps -0.00 to 0.00 and uses ROUND_HALF_UP."""
    rounded = quantize_amount(Decimal("-0.001"), "DZD")
    assert rounded == Decimal("0.00")

    half_up = quantize_amount(Decimal("10.005"), "DZD")
    assert half_up == Decimal("10.01")


def test_money_add_and_subtract() -> None:
    """Verify Money addition and subtraction with matching and mismatched currencies."""
    m1 = Money(amount=Decimal("100.00"), currency="DZD")
    m2 = Money(amount=Decimal("50.25"), currency="DZD")

    added = m1.add(m2)
    assert added.amount == Decimal("150.25")

    subtracted = m1.subtract(m2)
    assert subtracted.amount == Decimal("49.75")

    # Mismatched currency or non-Money
    with pytest.raises(ValidationError):
        m1.add("50.00")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        m1.subtract("50.00")  # type: ignore[arg-type]


def test_money_multiply() -> None:
    """Verify Money multiplication by Decimal factor and bounds handling."""
    m = Money(amount=Decimal("200.00"), currency="DZD")
    result = m.multiply(Decimal("1.5"))
    assert result.amount == Decimal("300.00")

    # Non-decimal factor
    with pytest.raises(ValidationError):
        m.multiply(1.5)  # type: ignore[arg-type]

    # Non-finite factor
    with pytest.raises(ValidationError):
        m.multiply(Decimal("NaN"))


def test_money_compare_and_is_zero() -> None:
    """Verify Money comparison branches and is_zero predicate."""
    m_zero = Money(amount=Decimal("0.00"), currency="DZD")
    m_100 = Money(amount=Decimal("100.00"), currency="DZD")
    m_200 = Money(amount=Decimal("200.00"), currency="DZD")
    m_100_dup = Money(amount=Decimal("100.00"), currency="DZD")

    assert m_zero.is_zero() is True
    assert m_100.is_zero() is False

    assert m_100.compare(m_200) == -1
    assert m_200.compare(m_100) == 1
    assert m_100.compare(m_100_dup) == 0

    with pytest.raises(ValidationError):
        m_100.compare("100")  # type: ignore[arg-type]


def test_sum_money() -> None:
    """Verify summing Money iterables including empty iterable and invalid items."""
    # Empty sum returns zero Money
    empty_total = sum_money([], currency="DZD")
    assert empty_total.amount == Decimal("0.00")
    assert empty_total.currency == "DZD"

    # Non-empty sum
    items = [
        Money(amount=Decimal("10.00"), currency="DZD"),
        Money(amount=Decimal("20.50"), currency="DZD"),
    ]
    total = sum_money(items, currency="DZD")
    assert total.amount == Decimal("30.50")

    # Invalid item in iterable
    with pytest.raises(ValidationError):
        sum_money([Money(amount=Decimal("10.00"), currency="DZD"), "invalid"], currency="DZD")  # type: ignore[list-item]


def test_percentage_of() -> None:
    """Verify percentage_of calculation and range validation."""
    m = Money(amount=Decimal("1000.00"), currency="DZD")
    assert percentage_of(m, Decimal("0.20")).amount == Decimal("200.00")
    assert percentage_of(m, Decimal("0.00")).amount == Decimal("0.00")
    assert percentage_of(m, Decimal("1.00")).amount == Decimal("1000.00")

    # Non-Money value
    with pytest.raises(ValidationError):
        percentage_of("1000", Decimal("0.10"))  # type: ignore[arg-type]

    # Non-decimal rate
    with pytest.raises(ValidationError):
        percentage_of(m, 0.10)  # type: ignore[arg-type]

    # Rate out of range (< 0 or > 1)
    with pytest.raises(ValidationError):
        percentage_of(m, Decimal("-0.01"))

    with pytest.raises(ValidationError):
        percentage_of(m, Decimal("1.01"))
