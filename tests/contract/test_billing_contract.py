"""Independent M1 tests for M5's published contracts, pending M5 implementation."""

from collections.abc import Callable, Sequence
from datetime import date, datetime
from decimal import Decimal
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType
from typing import Protocol, cast
from uuid import UUID

import pytest

from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError
from tests.support.fault_injection import assign_unchecked
from tests.support.fixtures import FIXED_TIME

pytestmark = pytest.mark.billing_contract
PREFIX = "clinic_management.domain."


class MoneyContract(Protocol):
    """Describe only M5's published immutable money surface."""

    @property
    def amount(self) -> Decimal:
        """Return the exact decimal amount."""
        ...

    def add(self, other: MoneyContract) -> MoneyContract:
        """Return a new same-currency amount.

        Args:
            other: Money to add without mutating either operand.
        """
        ...


class InvoiceContract(Protocol):
    """Describe the minimal invoice behavior tested independently by M1."""

    def lines(self) -> tuple[object, ...]:
        """Return an immutable view of owned billing lines."""
        ...

    def total(self) -> MoneyContract:
        """Return the exact issued/draft line total."""
        ...

    def issue(self, number: str, *, at: datetime, due_on: date) -> None:
        """Issue the draft with a server-allocated number and explicit dates.

        Args:
            number: Supplied unique document number.
            at: Aware issue instant supplied by the fixture.
            due_on: Due date supplied by the fixture.
        """
        ...

    def add_line(self, line: object) -> None:
        """Add a line only while the invoice is a draft.

        Args:
            line: M5's immutable line object.
        """
        ...


class BalanceContract(Protocol):
    """Describe the required derived outstanding amount on M5's balance result."""

    @property
    def outstanding(self) -> MoneyContract:
        """Return remaining invoice debt after net posted payments."""
        ...


def dependency(suffix: str) -> ModuleType:
    """Load an implemented M5 dependency or explicitly report its absence.

    Args:
        suffix: Documented relative module name under the domain package.

    Returns:
        The implementation module; a missing module causes an explicit skip.
    """
    name = PREFIX + suffix
    if find_spec(name) is None:
        pytest.skip(f"Pending M5 implementation: {name}")
    return import_module(name)


def call(suffix: str, symbol: str, **values: object) -> object:
    """Call a documented constructor/function at an explicit dynamic test boundary.

    Args:
        suffix: Implementation module to load.
        symbol: Published class/function name to verify.
        values: Explicit named contract inputs, never arbitrary production data.

    Returns:
        The constructed value or pure calculation result.
    """
    factory = cast("Callable[..., object]", getattr(dependency(suffix), symbol))
    return factory(**values)


def money(amount: str, currency: str = "DZD") -> MoneyContract:
    """Build exact-decimal M5 money using the team's demo currency.

    Args:
        amount: Decimal-string fixture amount.
        currency: Explicit currency, including mismatch cases.

    Returns:
        M5's money value through its published structural surface.
    """
    return cast(
        "MoneyContract", call("shared.money", "Money", amount=Decimal(amount), currency=currency)
    )


def enum_value(kind: str, name: str) -> object:
    """Read a documented billing enum member without fabricating its implementation.

    Args:
        kind: Published enum class name.
        name: Published member name.

    Returns:
        The actual M5 enum member.
    """
    return cast("object", getattr(getattr(dependency("billing.enums"), kind), name))


def invoice_line() -> object:
    """Build a one-service 1000 DZD line with zero demo discount/tax.

    Returns:
        An actual M5 line, not a replacement implementation.
    """
    return call(
        "billing.invoice_line",
        "InvoiceLine",
        line_id=UUID(int=40),
        description="Synthetic consultation",
        quantity=Decimal("1"),
        unit_price=money("1000"),
        discount_amount=money("0"),
        tax_rate=Decimal("0"),
        source_service_id=UUID(int=41),
        source_consultation_id=UUID(int=42),
    )


def invoice(lines: Sequence[object]) -> InvoiceContract:
    """Construct M5's draft with every required published constructor field.

    Args:
        lines: Caller-owned sequence whose copy behavior will be tested.

    Returns:
        M5's actual draft invoice through its minimal published contract.
    """
    return cast(
        "InvoiceContract",
        call(
            "billing.invoice",
            "Invoice",
            id=UUID(int=1),
            version=0,
            clinic_id=UUID(int=10),
            patient_id=UUID(int=2),
            currency="DZD",
            lines=lines,
            status=enum_value("InvoiceStatus", "DRAFT"),
            number=None,
            issued_at=None,
            due_on=None,
            void_reason=None,
            voided_at=None,
        ),
    )


def payment() -> object:
    """Construct a 400 DZD posted payment against the synthetic 1000 DZD invoice.

    Returns:
        M5's actual immutable payment record.
    """
    return call(
        "billing.payment",
        "Payment",
        id=UUID(int=20),
        clinic_id=UUID(int=10),
        invoice_id=UUID(int=1),
        amount=money("400"),
        method=enum_value("PaymentMethod", "CASH"),
        received_at=FIXED_TIME,
        received_by=UUID(int=11),
        idempotency_key=UUID(int=30),
        external_reference=None,
    )


def test_decimal_arithmetic_and_money_immutability() -> None:
    """0.1 plus 0.2 is exactly 0.3, and values cannot be mutated after creation."""
    first = money("0.10")
    assert first.add(money("0.20")).amount == Decimal("0.30")
    assert first.amount == Decimal("0.10")
    with pytest.raises(AttributeError):
        assign_unchecked(first, "amount", Decimal("9"))


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_amounts_are_rejected(amount: str) -> None:
    """Financial values never admit NaN/infinity into comparisons or totals."""
    with pytest.raises(ValidationError):
        money(amount)


def test_half_up_rounding_matches_the_explicit_demo_policy() -> None:
    """The documented DZD policy rounds a half-cent upward using decimal math."""
    result = call("shared.money", "quantize_amount", value=Decimal("1.005"), currency="DZD")
    assert result == Decimal("1.01")


def test_currency_mismatch_is_rejected() -> None:
    """Unsupported currency creation or mixed-currency arithmetic must fail."""
    with pytest.raises(ValidationError):
        money("1", "USD").add(money("1", "DZD"))


def test_invoice_snapshots_are_owned_and_issued_lines_cannot_change() -> None:
    """Clearing caller input cannot erase lines and issuance prevents later edits."""
    lines = [invoice_line()]
    value = invoice(lines)
    lines.clear()
    assert len(value.lines()) == 1
    assert value.total().amount == Decimal("1000.00")
    value.issue("DEMO-0001", at=FIXED_TIME, due_on=FIXED_TIME.date())
    with pytest.raises(InvalidTransitionError):
        value.add_line(invoice_line())


def test_partial_payment_and_excess_allocation() -> None:
    """400 paid on 1000 leaves exactly 600; another 601 is rejected."""
    value = invoice([invoice_line()])
    value.issue("DEMO-0001", at=FIXED_TIME, due_on=FIXED_TIME.date())
    posted = payment()
    balance = call(
        "billing.balance", "calculate_balance", invoice=value, payments=(posted,), reversals=()
    )
    outstanding = cast("BalanceContract", balance).outstanding
    assert outstanding.amount == Decimal("600.00")
    with pytest.raises(ValidationError):
        call(
            "billing.balance",
            "validate_payment",
            invoice=value,
            amount=money("601"),
            payments=(posted,),
            reversals=(),
        )
    call(
        "billing.balance",
        "validate_payment",
        invoice=value,
        amount=money("600"),
        payments=(posted,),
        reversals=(),
    )


def test_reversal_bounds_preserve_original_payment() -> None:
    """A 400 payment with 100 reversed can reverse at most another 300."""
    posted = payment()
    reversal = call(
        "billing.reversal",
        "PaymentReversal",
        id=UUID(int=21),
        clinic_id=UUID(int=10),
        payment_id=UUID(int=20),
        amount=money("100"),
        reason="Synthetic correction",
        reversed_at=FIXED_TIME,
        reversed_by=UUID(int=11),
        idempotency_key=UUID(int=31),
    )
    with pytest.raises(ValidationError):
        call(
            "billing.reversal",
            "validate_reversal",
            payment=posted,
            amount=money("301"),
            existing=(reversal,),
        )
    call(
        "billing.reversal",
        "validate_reversal",
        payment=posted,
        amount=money("300"),
        existing=(reversal,),
    )
