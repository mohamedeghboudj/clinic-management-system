"""Independent financial-boundary tests based on the member guide, not coverage gaps."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from decimal import ROUND_DOWN, Decimal, localcontext
from typing import cast

import pytest

from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import (
    Money,
    percentage_of,
    quantize_amount,
    sum_money,
)
from tests.support.fault_injection import assign_unchecked


def money(value: str) -> Money:
    """Build a synthetic DZD amount from an exact string.

    Args:
        value: Exact decimal fixture text.

    Returns:
        The submitted implementation's Money instance.
    """
    return Money(amount=Decimal(value), currency="DZD")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.004", "0.00"),
        ("0.005", "0.01"),
        ("0.006", "0.01"),
        ("-0.004", "0.00"),
        ("-0.005", "-0.01"),
        ("-0.006", "-0.01"),
        ("1.005", "1.01"),
        ("-1.005", "-1.01"),
    ],
)
def test_rounding_boundaries_are_symmetric_half_up(value: str, expected: str) -> None:
    """Both signs round half cents away from zero under the stated DZD policy."""
    with localcontext() as context:
        context.rounding = ROUND_DOWN
        result = quantize_amount(Decimal(value), "DZD")
    assert result == Decimal(expected)
    assert result.as_tuple().exponent == -2
    if result == 0:
        assert not result.is_signed()


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_all_nonfinite_decimal_forms_are_rejected(value: str) -> None:
    """Quiet/signalling NaN and infinities never become monetary values."""
    with pytest.raises(ValidationError):
        money(value)


@pytest.mark.parametrize("value", [True, 1, 1.25, "1.00", None])
def test_inexact_or_untyped_amounts_are_rejected(value: object) -> None:
    """The domain rejects floats and coercions rather than silently converting them."""
    with pytest.raises(ValidationError):
        Money(amount=cast("Decimal", value), currency="DZD")


@pytest.mark.parametrize("currency", ["", "dzd", "DZD ", "USD"])
def test_unsupported_currency_codes_are_not_normalized_silently(currency: str) -> None:
    """Only the explicitly configured DZD currency is accepted in Week 1."""
    with pytest.raises(ValidationError):
        Money(amount=Decimal("1"), currency=currency)


@pytest.mark.parametrize(
    ("price", "quantity", "expected"),
    [
        ("2.35", "0.5", "1.18"),
        ("-2.35", "0.5", "-1.18"),
        ("0.01", "0.5", "0.01"),
        ("1.01", "1.00494", "1.01"),
    ],
)
def test_fractional_multiplication_rounds_the_exact_product_once(
    price: str, quantity: str, expected: str
) -> None:
    """Published fractional-quantity examples have independent expected cent totals."""
    original = money(price)
    result = original.multiply(Decimal(quantity))
    assert result.amount == Decimal(expected)
    assert original.amount == Decimal(price)


def test_decimal_arithmetic_returns_new_values_and_preserves_inputs() -> None:
    """Exact addition/subtraction and comparisons do not mutate frozen operands."""
    first, second = money("0.10"), money("0.20")
    total = first.add(second)
    assert total.amount == Decimal("0.30")
    assert total.subtract(first) == second
    assert first.subtract(second).amount == Decimal("-0.10")
    assert (first.compare(second), second.compare(first), first.compare(money("0.10"))) == (
        -1,
        1,
        0,
    )
    assert (first.amount, second.amount) == (Decimal("0.10"), Decimal("0.20"))
    assert total is not first and total is not second
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(first, "amount", Decimal("9.99"))


def test_generator_sum_is_single_pass_and_has_an_explicit_empty_currency() -> None:
    """A streamed total consumes each source once and empty sums retain DZD."""
    visited: list[str] = []

    def values() -> Iterator[Money]:
        """Yield an observable synthetic stream without materializing it twice.

        Yields:
            Immutable exact-decimal values.
        """
        for value in ("1.01", "2.02", "-0.03"):
            visited.append(value)
            yield money(value)

    assert sum_money(values(), "DZD").amount == Decimal("3.00")
    assert visited == ["1.01", "2.02", "-0.03"]
    assert sum_money(iter(()), "DZD") == money("0")
    with pytest.raises(ValidationError):
        sum_money(iter(()), "USD")


@pytest.mark.parametrize(("rate", "expected"), [("0", "0.00"), ("0.025", "0.01"), ("1", "0.20")])
def test_percentage_bounds_use_fractional_rates(rate: str, expected: str) -> None:
    """Zero, half-cent tax and the inclusive upper rate have exact expected results."""
    assert percentage_of(money("0.20"), Decimal(rate)).amount == Decimal(expected)


@pytest.mark.parametrize("rate", ["-0.0001", "1.0001", "NaN", "sNaN", "Infinity"])
def test_invalid_percentage_rates_raise_domain_errors(rate: str) -> None:
    """Invalid fractional rates fail through the shared error contract."""
    with pytest.raises(ValidationError):
        percentage_of(money("100"), Decimal(rate))


def test_unsupported_numeric_magnitudes_raise_domain_validation() -> None:
    """Unrepresentable construction uses the same safe domain failure category."""
    with pytest.raises(ValidationError):
        money("1E+1000000")


@pytest.mark.parametrize(
    ("precision", "quantity"),
    [(4, "1.00494"), (28, "1.0049504950495049504950495049")],
)
def test_multiplication_is_not_double_rounded_by_the_ambient_context(
    precision: int, quantity: str
) -> None:
    """Valid fractional quantities must preserve the specified exact gross formula."""
    value = money("1.01")
    with localcontext() as context:
        context.prec = precision
        result = value.multiply(Decimal(quantity))
    # Both exact products are strictly below 1.015, so one quantization gives 1.01.
    assert result.amount == Decimal("1.01")


def test_finite_factor_overflow_is_translated_to_a_domain_error() -> None:
    """Unsupported finite magnitude must not leak a raw Decimal exception."""
    with pytest.raises(ValidationError):
        money("1.01").multiply(Decimal("1E+1000000"))
