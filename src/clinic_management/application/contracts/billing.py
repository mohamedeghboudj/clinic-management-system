"""Application DTO contracts for invoice and billing queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from clinic_management.domain.billing._validation import require_uuid_value
from clinic_management.domain.billing.enums import InvoiceStatus
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.money import Money


@dataclass(frozen=True, kw_only=True)
class InvoiceSummary:
    """Represent a safe, clinic-scoped projection of an invoice and its debt."""

    invoice_id: UUID
    patient_id: UUID
    number: str | None
    status: InvoiceStatus
    total: Money
    outstanding: Money
    due_on: date | None
    version: int

    def __post_init__(self) -> None:
        """Validate summary fields, currency matching and version number.

        Raises:
            ValidationError: If any DTO field violates contract invariants.
        """
        require_uuid_value(self.invoice_id, "invoice.summary.id.invalid")
        require_uuid_value(self.patient_id, "invoice.summary.patient_id.invalid")
        if not isinstance(self.status, InvoiceStatus):
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.summary.status")
        if (
            not isinstance(self.total, Money)
            or not isinstance(self.outstanding, Money)
            or self.total.currency != self.outstanding.currency
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.summary.money")
        if self.due_on is not None and (
            not isinstance(self.due_on, date) or isinstance(self.due_on, datetime)
        ):
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.summary.due_on")
        if type(self.version) is not int or self.version < 0:
            raise ValidationError(code="INVALID_VALUE", message_key="invoice.summary.version")
