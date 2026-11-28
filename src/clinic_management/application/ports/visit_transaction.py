"""Transaction-bound repository bundle for the connected visit."""

from __future__ import annotations

from typing import Protocol, Self
from uuid import UUID

from clinic_management.application.contracts.visit import (
    CommandContext,
    CommandReceipt,
    ServiceSnapshot,
)
from clinic_management.application.ports.billing import (
    InvoiceNumberGenerator,
    InvoiceRepository,
    PaymentRepository,
)
from clinic_management.application.ports.clinical import (
    ClinicalRepository,
    ServiceCatalogRepository,
)
from clinic_management.application.ports.facilities import ClinicRepository, RoomRepository
from clinic_management.application.ports.people import (
    PatientRepository,
    PersonRepository,
    StaffRepository,
)
from clinic_management.application.ports.scheduling import AppointmentRepository
from clinic_management.application.ports.unit_of_work import UnitOfWork


class ReceiptRepository(Protocol):
    """Persist the metadata used for replay in the business transaction."""

    def lock_and_find(
        self, ctx: CommandContext, *, operation: str, digest: bytes
    ) -> CommandReceipt | None:
        """Serialize competing uses of a key and compare request identity.

        Args:
            ctx: Authenticated clinic, actor and command key.
            operation: Stable command name.
            digest: Hash of the canonical validated request and target.

        Returns:
            A matching committed receipt, or None for a fresh command.

        Raises:
            ConflictError: If a previous use bound different input to the key.
        """
        ...

    def save(self, ctx: CommandContext, receipt: CommandReceipt, *, digest: bytes) -> None:
        """Stage the outcome before committing its business transaction.

        Args:
            ctx: Verified command context.
            receipt: Result metadata for the held key.
            digest: Original validated request digest.
        """
        ...


class BillableVisitSource(Protocol):
    """Expose only the billable facts of a finalized visit on the active connection."""

    def snapshot(
        self, clinic_id: UUID, patient_id: UUID, consultation_id: UUID, service_id: UUID
    ) -> ServiceSnapshot:
        """Read an active service after checking the visit and patient relationship.

        Args:
            clinic_id: Verified clinic.
            patient_id: Intended invoice recipient.
            consultation_id: Finalized visit.
            service_id: Requested active catalogue entry.

        Returns:
            Source identifier, description and exact price.

        Raises:
            NotFoundError: If a source is missing or inaccessible.
            InvalidTransitionError: If the visit is ineligible for invoicing.
        """
        ...


class VisitTransaction(UnitOfWork, Protocol):
    """Expose repositories bound to one transaction and connection."""

    def __enter__(self) -> Self:
        """Begin a scope and retain the typed repository bundle.

        Returns:
            This active transaction.
        """
        ...

    @property
    def billing_source(self) -> BillableVisitSource:
        """Return the clinical-to-billing projection bound to this transaction."""
        ...

    @property
    def persons(self) -> PersonRepository:
        """Return the transaction-scoped persons repository."""
        ...

    @property
    def patients(self) -> PatientRepository:
        """Return the transaction-scoped patients repository."""
        ...

    @property
    def staff(self) -> StaffRepository:
        """Return the transaction-scoped staff repository."""
        ...

    @property
    def clinics(self) -> ClinicRepository:
        """Return the transaction-scoped clinics repository."""
        ...

    @property
    def rooms(self) -> RoomRepository:
        """Return the transaction-scoped rooms repository."""
        ...

    @property
    def appointments(self) -> AppointmentRepository:
        """Return the transaction-scoped appointments repository."""
        ...

    @property
    def clinical(self) -> ClinicalRepository:
        """Return the transaction-scoped clinical repository."""
        ...

    @property
    def catalog(self) -> ServiceCatalogRepository:
        """Return the transaction-scoped catalog repository."""
        ...

    @property
    def invoices(self) -> InvoiceRepository:
        """Return the transaction-scoped invoices repository."""
        ...

    @property
    def payments(self) -> PaymentRepository:
        """Return the transaction-scoped payments repository."""
        ...

    @property
    def numbers(self) -> InvoiceNumberGenerator:
        """Return the transaction-scoped numbers repository."""
        ...

    @property
    def receipts(self) -> ReceiptRepository:
        """Return the transaction-scoped receipts repository."""
        ...


class TransactionFactory(Protocol):
    """Supply a new transaction for each use case."""

    def __call__(self, *, clinic_id: UUID) -> VisitTransaction:
        """Construct a tenant-scoped transaction.

        Args:
            clinic_id: Clinic resolved from the verified request context.

        Returns:
            A fresh context manager with its repositories.
        """
        ...
