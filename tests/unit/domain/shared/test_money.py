"""Unit tests for the Money value object and rounding helpers."""

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


def test_money_creation_and_quantization() -> None:
    """Money normalizes finite Decimals using ROUND_HALF_UP and normalizes -0.00."""
    val = Money(amount=Decimal("10.005"), currency="DZD")
    assert val.amount == Decimal("10.01")
    assert val.currency == "DZD"
    assert not val.is_zero()

    neg_zero = Money(amount=Decimal("-0.001"), currency="DZD")
    assert neg_zero.amount == Decimal("0.00")
    assert neg_zero.is_zero()


@pytest.mark.parametrize("bad_amount", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_money_rejects_nonfinite_decimals(bad_amount: Decimal) -> None:
    """NaN and infinite values are rejected with ValidationError."""
    with pytest.raises(ValidationError):
        quantize_amount(bad_amount, "DZD")


def test_money_rejects_unsupported_currency_and_non_decimal() -> None:
    """Unsupported currencies and non-Decimal amounts fail validation."""
    with pytest.raises(ValidationError):
        Money(amount=Decimal("1.00"), currency="USD")
    with pytest.raises(ValidationError):
        quantize_amount(1.5, "DZD")  # type: ignore[arg-type]


def test_money_arithmetic_and_comparisons() -> None:
    """Addition, subtraction, multiplication, and comparison preserve exact decimals."""
    a = Money(amount=Decimal("100.10"), currency="DZD")
    b = Money(amount=Decimal("40.05"), currency="DZD")

    assert a.add(b) == Money(amount=Decimal("140.15"), currency="DZD")
    assert a.subtract(b) == Money(amount=Decimal("60.05"), currency="DZD")
    assert a.multiply(Decimal("2.5")) == Money(amount=Decimal("250.25"), currency="DZD")

    assert a.compare(b) == 1
    assert b.compare(a) == -1
    assert a.compare(Money(amount=Decimal("100.10"), currency="DZD")) == 0


def test_money_rejects_invalid_operands() -> None:
    """Arithmetic and helpers reject non-Money or out-of-range rate operands."""
    base = Money(amount=Decimal("50.00"), currency="DZD")
    with pytest.raises(ValidationError):
        base.add("not-money")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        base.multiply(Decimal("NaN"))
    with pytest.raises(ValidationError):
        sum_money(["bad"], "DZD")  # type: ignore[list-item]
    with pytest.raises(ValidationError):
        percentage_of("bad", Decimal("0.1"))  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        percentage_of(base, Decimal("-0.01"))
    with pytest.raises(ValidationError):
        percentage_of(base, Decimal("1.01"))


def test_sum_money_and_percentage_of() -> None:
    """sum_money handles empty iterables and percentage_of computes exact rates."""
    empty = sum_money((), "DZD")
    assert empty.is_zero()

    total = sum_money(
        (
            Money(amount=Decimal("10.00"), currency="DZD"),
            Money(amount=Decimal("20.55"), currency="DZD"),
        ),
        "DZD",
    )
    assert total.amount == Decimal("30.55")
    assert percentage_of(total, Decimal("0.10")).amount == Decimal("3.06")
