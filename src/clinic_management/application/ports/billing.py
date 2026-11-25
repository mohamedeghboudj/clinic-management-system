"""Repository and numbering ports for clinic-scoped billing persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from clinic_management.application.contracts.billing import InvoiceSummary
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.billing.payment import Payment
from clinic_management.domain.billing.reversal import PaymentReversal


class InvoiceRepository(Protocol):
    """Define clinic-scoped persistence operations for patient invoices."""

    def get(self, clinic_id: UUID, invoice_id: UUID) -> Invoice | None:
        """Return an invoice by clinic and ID, or None if not found.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            invoice_id: Target invoice identifier.

        Returns:
            Matching Invoice aggregate or None.
        """
        ...

    def get_for_update(self, clinic_id: UUID, invoice_id: UUID) -> Invoice | None:
        """Load an invoice with an exclusive transaction lock for payment/void updates.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            invoice_id: Target invoice identifier to lock within the active UoW.

        Returns:
            Locked Invoice aggregate or None.
        """
        ...

    def add(self, invoice: Invoice) -> None:
        """Stage a newly created invoice in the current Unit of Work.

        Args:
            invoice: New Invoice aggregate to persist.
        """
        ...

    def save(self, invoice: Invoice, *, expected_version: int) -> None:
        """Persist changes to an existing invoice guarded by optimistic concurrency.

        Args:
            invoice: Modified Invoice aggregate.
            expected_version: Version read prior to modification;
                raises ConcurrencyError on mismatch.
        """
        ...

    def list_for_patient(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        page: PageRequest,
    ) -> Page[InvoiceSummary]:
        """Return a bounded, deterministically ordered page of patient invoices.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            patient_id: Patient whose invoices are requested.
            page: Bounded pagination cursor and limit.

        Returns:
            Page of InvoiceSummary projections.
        """
        ...


class PaymentRepository(Protocol):
    """Define clinic-scoped persistence operations for payments and reversals."""

    def list_for_invoice(self, clinic_id: UUID, invoice_id: UUID) -> tuple[Payment, ...]:
        """Return all posted payments for a single invoice within the clinic.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            invoice_id: Target invoice identifier.

        Returns:
            Immutable tuple of posted Payment records.
        """
        ...

    def list_reversals(self, clinic_id: UUID, payment_id: UUID) -> tuple[PaymentReversal, ...]:
        """Return all recorded reversals for a single payment within the clinic.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            payment_id: Target payment identifier.

        Returns:
            Immutable tuple of PaymentReversal records.
        """
        ...

    def add(self, payment: Payment) -> None:
        """Stage an immutable posted payment in the current Unit of Work.

        Args:
            payment: Validated Payment entity to append.
        """
        ...

    def add_reversal(self, reversal: PaymentReversal) -> None:
        """Stage an immutable payment reversal in the current Unit of Work.

        Args:
            reversal: Validated PaymentReversal entity to append.
        """
        ...

    def get_by_key(self, clinic_id: UUID, actor_id: UUID, key: UUID) -> Payment | None:
        """Look up a previously committed payment by clinic, actor and idempotency key.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            actor_id: Staff account identifier that submitted the command.
            key: Client-supplied idempotency key UUID.

        Returns:
            Previously recorded Payment or None.
        """
        ...


class InvoiceNumberGenerator(Protocol):
    """Allocate unique clinic-scoped sequential invoice numbers per calendar year."""

    def next_number(self, clinic_id: UUID, year: int) -> str:
        """Return the next unique invoice number for the specified clinic and year.

        Args:
            clinic_id: Authenticated clinic scope identifier.
            year: Four-digit issuance year.

        Returns:
            Formatted unique invoice document number string.
        """
        ...
