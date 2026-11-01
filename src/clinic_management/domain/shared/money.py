"""Exact decimal money value object and currency-safe rounding helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    DecimalException,
    InvalidOperation,
    localcontext,
)

from clinic_management.domain.shared.errors import ValidationError

SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"DZD"})
CURRENCY_QUANTUM: Decimal = Decimal("0.01")
QUANTIZE_PRECISION: int = 28


def _require_currency(currency: str) -> str:
    """Validate that a currency code matches the supported clinic policy.

    Args:
        currency: ISO currency identifier to check.

    Returns:
        The validated currency code.

    Raises:
        ValidationError: If the currency is not a supported string code.
    """
    if not isinstance(currency, str) or currency not in SUPPORTED_CURRENCIES:
        raise ValidationError(code="INVALID_VALUE", message_key="money.currency.unsupported")
    return currency


def _require_decimal(value: Decimal, message_key: str) -> Decimal:
    """Require an exact finite Decimal, rejecting floats, bools, NaN and infinities.

    Args:
        value: Numeric value supplied by caller.
        message_key: Translation key to use on failure.

    Returns:
        The validated finite Decimal.

    Raises:
        ValidationError: If the value is not a finite Decimal instance.
    """
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValidationError(code="INVALID_VALUE", message_key=message_key)
    return value


def quantize_amount(value: Decimal, currency: str) -> Decimal:
    """Validate and round a finite decimal amount using the currency policy.

    Args:
        value: Finite decimal amount to round.
        currency: Supported currency code governing scale and rounding.

    Returns:
        Quantized Decimal with two fractional digits using ROUND_HALF_UP.

    Raises:
        ValidationError: If the amount is non-finite, out of bounds, or currency is unsupported.
    """
    _require_currency(currency)
    clean = _require_decimal(value, "money.amount.invalid")
    try:
        with localcontext() as ctx:
            ctx.prec = QUANTIZE_PRECISION
            rounded = clean.quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValidationError(code="INVALID_VALUE", message_key="money.amount.invalid") from exc
    return Decimal("0.00") if rounded == Decimal("-0.00") else rounded


@dataclass(frozen=True, kw_only=True)
class Money:
    """Represent an immutable monetary amount in an explicit supported currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        """Validate currency and quantize the stored decimal amount.

        Raises:
            ValidationError: If the amount is non-finite or currency is unsupported.
        """
        validated_currency = _require_currency(self.currency)
        quantized = quantize_amount(self.amount, validated_currency)
        object.__setattr__(self, "currency", validated_currency)
        object.__setattr__(self, "amount", quantized)

    def _require_same_currency(self, other: Money) -> None:
        """Verify that another Money operand shares this currency.

        Args:
            other: Operand to compare against this instance.

        Raises:
            ValidationError: If other is not a Money instance with matching currency.
        """
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValidationError(code="INVALID_VALUE", message_key="money.currency.mismatch")

    def add(self, other: Money) -> Money:
        """Return the sum of two same-currency monetary amounts.

        Args:
            other: Money value to add.

        Returns:
            New Money instance with the exact sum.

        Raises:
            ValidationError: If currencies do not match.
        """
        self._require_same_currency(other)
        with localcontext() as ctx:
            ctx.prec = QUANTIZE_PRECISION + 2
            total = self.amount + other.amount
        return Money(amount=total, currency=self.currency)

    def subtract(self, other: Money) -> Money:
        """Return the difference of two same-currency monetary amounts.

        Args:
            other: Money value to subtract.

        Returns:
            New Money instance with the exact difference.

        Raises:
            ValidationError: If currencies do not match.
        """
        self._require_same_currency(other)
        with localcontext() as ctx:
            ctx.prec = QUANTIZE_PRECISION + 2
            difference = self.amount - other.amount
        return Money(amount=difference, currency=self.currency)

    def multiply(self, quantity: Decimal) -> Money:
        """Multiply this monetary amount by a finite decimal quantity.

        Computes the exact intermediate product independent of caller Decimal
        context precision, then quantizes once using the currency rounding policy.

        Args:
            quantity: Finite decimal factor to multiply by.

        Returns:
            New quantized Money instance.

        Raises:
            ValidationError: If quantity is not a finite Decimal or overflows bounds.
        """
        factor = _require_decimal(quantity, "money.quantity.invalid")
        exact_precision = max(
            QUANTIZE_PRECISION,
            len(self.amount.as_tuple().digits) + len(factor.as_tuple().digits) + 2,
        )
        try:
            with localcontext() as ctx:
                ctx.prec = exact_precision
                product = self.amount * factor
        except DecimalException as exc:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="money.quantity.invalid",
            ) from exc
        return Money(
            amount=quantize_amount(product, self.currency),
            currency=self.currency,
        )

    def compare(self, other: Money) -> int:
        """Compare this monetary value with another of the same currency.

        Args:
            other: Money value to compare against.

        Returns:
            -1 if less than other, 0 if equal, or 1 if greater than other.

        Raises:
            ValidationError: If currencies do not match.
        """
        self._require_same_currency(other)
        if self.amount < other.amount:
            return -1
        if self.amount > other.amount:
            return 1
        return 0

    def is_zero(self) -> bool:
        """Return whether the monetary amount is exactly zero.

        Returns:
            True if the quantized amount equals zero, otherwise False.
        """
        return self.amount == Decimal("0.00")


def sum_money(values: Iterable[Money], currency: str) -> Money:
    """Sum a sequence or iterable of Money values in an explicit currency.

    Args:
        values: Iterable of Money instances to total.
        currency: Expected currency for all items and empty-sum fallback.

    Returns:
        Total Money in the specified currency, or zero when empty.

    Raises:
        ValidationError: If currency is unsupported or any item mismatches.
    """
    total = Money(amount=Decimal("0.00"), currency=currency)
    for item in values:
        if not isinstance(item, Money):
            raise ValidationError(code="INVALID_VALUE", message_key="money.item.invalid")
        total = total.add(item)
    return total


def percentage_of(value: Money, rate: Decimal) -> Money:
    """Calculate a fractional rate of a monetary value.

    Args:
        value: Base Money value.
        rate: Finite decimal fraction between 0 and 1 inclusive.

    Returns:
        Quantized Money representing value multiplied by rate.

    Raises:
        ValidationError: If value is invalid or rate is outside [0, 1].
    """
    if not isinstance(value, Money):
        raise ValidationError(code="INVALID_VALUE", message_key="money.value.invalid")
    clean_rate = _require_decimal(rate, "money.rate.invalid")
    if clean_rate < Decimal("0") or clean_rate > Decimal("1"):
        raise ValidationError(code="INVALID_VALUE", message_key="money.rate.out_of_range")
    return value.multiply(clean_rate)
