"""Patient invoice aggregate root enforcing draft editing, issuance and void rules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.billing._validation import (
    require_aware_datetime,
    require_non_empty_text,
    require_uuid_value,
)
from clinic_management.domain.billing.enums import InvoiceStatus
from clinic_management.domain.billing.invoice_line import InvoiceLine
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError
from clinic_management.domain.shared.money import Money, quantize_amount, sum_money


@dataclass(eq=False, kw_only=True)
class Invoice(Entity):
    """Manage a clinic invoice lifecycle from draft construction through issuance."""

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    currency: str
    status: InvoiceStatus = InvoiceStatus.DRAFT
    number: str | None = None
    issued_at: datetime | None = None
    due_on: date | None = None
    void_reason: str | None = None
    voided_at: datetime | None = None
    version: int = 0
    _lines: list[InvoiceLine] = field(default_factory=list, init=False, repr=False)

    def __init__(
        self,
        *,
        id: UUID,
        clinic_id: UUID,
        patient_id: UUID,
        currency: str,
        lines: Sequence[InvoiceLine] = (),
        status: InvoiceStatus = InvoiceStatus.DRAFT,
        number: str | None = None,
        issued_at: datetime | None = None,
        due_on: date | None = None,
        void_reason: str | None = None,
        voided_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        """Initialize and validate an invoice aggregate root and its initial lines."""
        self.id = id
        self.clinic_id = clinic_id
        self.patient_id = patient_id
        self.currency = currency
        self.status = status
        self.number = number
        self.issued_at = issued_at
        self.due_on = due_on
        self.void_reason = void_reason
        self.voided_at = voided_at
        self.version = version
        self._lines = []

        require_uuid_value(self.id, "invoice.id.invalid")
        require_uuid_value(self.clinic_id, "invoice.clinic_id.invalid")
        require_uuid_value(self.patient_id, "invoice.patient_id.invalid")
        quantize_amount(Decimal("0.00"), self.currency)
        if type(self.version) is not int or self.version < 0:
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.version.invalid")
        if not isinstance(self.status, InvoiceStatus):
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.status.invalid")

        for item in lines:
            self._validate_candidate_line(item)
            self._lines.append(item)
        self._validate_status_invariants()

    def lines(self) -> tuple[InvoiceLine, ...]:
        """Return an immutable tuple snapshot of the invoice lines.

        Returns:
            Tuple of InvoiceLine objects owned by this invoice.
        """
        return tuple(self._lines)

    def _validate_candidate_line(self, line: InvoiceLine) -> None:
        """Check that a new line matches currency and avoids duplicate IDs or services.

        Args:
            line: Candidate InvoiceLine to verify against existing lines.

        Raises:
            ValidationError: If currency mismatches or line/service is duplicated.
        """
        if not isinstance(line, InvoiceLine) or line.unit_price.currency != self.currency:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.line.currency_mismatch",
            )
        for existing in self._lines:
            if existing.line_id == line.line_id:
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="invoice.line.duplicate_id",
                )
            if (
                line.source_service_id is not None
                and line.source_consultation_id is not None
                and existing.source_service_id == line.source_service_id
                and existing.source_consultation_id == line.source_consultation_id
            ):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="invoice.line.duplicate_service",
                )

    def _validate_status_invariants(self) -> None:
        """Enforce required metadata for ISSUED and VOID invoice states.

        Raises:
            ValidationError: If status-specific fields are missing or inconsistent.
        """
        if self.status in {InvoiceStatus.ISSUED, InvoiceStatus.VOID}:
            if not self._lines:
                raise ValidationError(code="INVALID_VALUE", message_key="invoice.lines.empty")
            self.number = require_non_empty_text(
                self.number or "",
                "invoice.number.required",
            )
            if self.issued_at is None or not isinstance(self.due_on, date):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="invoice.issue_dates.required",
                )
            require_aware_datetime(self.issued_at, "invoice.issued_at.naive")
            if isinstance(self.due_on, datetime) or self.due_on < self.issued_at.date():
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="invoice.due_on.invalid",
                )
        if self.status == InvoiceStatus.VOID:
            self.void_reason = require_non_empty_text(
                self.void_reason or "",
                "invoice.void_reason.required",
            )
            if self.voided_at is None:
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="invoice.voided_at.required",
                )
            require_aware_datetime(self.voided_at, "invoice.voided_at.naive")

    def add_line(self, line: InvoiceLine) -> None:
        """Append a billable line while the invoice is in DRAFT status.

        Args:
            line: Immutable InvoiceLine to add.

        Raises:
            InvalidTransitionError: If the invoice is not in DRAFT state.
            ValidationError: If the line currency or uniqueness check fails.
        """
        if self.status != InvoiceStatus.DRAFT:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="invoice.add_line.not_draft",
            )
        self._validate_candidate_line(line)
        self._lines.append(line)

    def remove_line(self, line_id: UUID) -> None:
        """Remove a line by ID while the invoice is in DRAFT status.

        Args:
            line_id: Identifier of the line to remove.

        Raises:
            InvalidTransitionError: If the invoice is not in DRAFT state.
            ValidationError: If line_id is not present on the draft invoice.
        """
        if self.status != InvoiceStatus.DRAFT:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="invoice.remove_line.not_draft",
            )
        require_uuid_value(line_id, "invoice.line.id.invalid")
        for index, existing in enumerate(self._lines):
            if existing.line_id == line_id:
                del self._lines[index]
                return
        raise ValidationError(code="INVALID_VALUE", message_key="invoice.line.not_found")

    def total(self) -> Money:
        """Return the exact sum of all rounded invoice line totals.

        Returns:
            Total Money in the invoice currency.
        """
        return sum_money((line.total() for line in self._lines), self.currency)

    def issue(self, number: str, *, at: datetime, due_on: date) -> None:
        """Transition a draft invoice with at least one line to ISSUED status.

        Args:
            number: Server-allocated unique clinic invoice number.
            at: Authoritative aware issuance timestamp.
            due_on: Payment due date on or after the issuance date.

        Raises:
            InvalidTransitionError: If the invoice is not currently DRAFT.
            ValidationError: If the invoice has no lines or dates/number are invalid.
        """
        if self.status != InvoiceStatus.DRAFT:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="invoice.issue.not_draft",
            )
        if not self._lines:
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.issue.empty_lines")
        cleaned_number = require_non_empty_text(number, "invoice.number.required")
        require_aware_datetime(at, "invoice.issued_at.naive")
        if not isinstance(due_on, date) or isinstance(due_on, datetime) or due_on < at.date():
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.due_on.invalid")
        self.number = cleaned_number
        self.issued_at = at
        self.due_on = due_on
        self.status = InvoiceStatus.ISSUED

    def void(self, reason: str, *, net_paid: Money, at: datetime) -> None:
        """Void an issued invoice only when net posted payments equal zero.

        Args:
            reason: Non-empty audit reason for voiding the document.
            net_paid: Current net paid Money derived from payments and reversals.
            at: Authoritative aware void timestamp.

        Raises:
            InvalidTransitionError: If the invoice is not ISSUED or has net payments.
            ValidationError: If reason, currency or timestamp is invalid.
        """
        if self.status != InvoiceStatus.ISSUED:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="invoice.void.not_issued",
            )
        cleaned_reason = require_non_empty_text(reason, "invoice.void_reason.required")
        require_aware_datetime(at, "invoice.voided_at.naive")
        if not isinstance(net_paid, Money) or net_paid.currency != self.currency:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="invoice.void.currency_mismatch",
            )
        if not net_paid.is_zero():
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="invoice.void.has_unreconciled_payments",
            )
        self.void_reason = cleaned_reason
        self.voided_at = at
        self.status = InvoiceStatus.VOID
