"""Ports for clinical-care persistence and service-catalog access."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from clinic_management.application.contracts.clinical import ClinicalEntrySummary
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.consultation import Consultation
from clinic_management.domain.clinical.prescription import Prescription
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.clinical.service_catalog import ServiceCatalogItem


@runtime_checkable
class ClinicalRepository(Protocol):
    """Persistence boundary for consultations, clinical entries, and prescriptions.

    Every mutable aggregate operation is scoped by ``clinic_id`` to enforce
    tenant isolation.  ``save_*`` methods require an ``expected_version`` to
    enable optimistic-concurrency control at the infrastructure layer.
    """

    def get_consultation(
        self, clinic_id: UUID, consultation_id: UUID
    ) -> Consultation | None:
        """Retrieve a consultation by its identifier within a clinic.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            consultation_id: Unique identifier of the consultation.

        Returns:
            The matching consultation, or ``None`` if it does not exist
            within the given clinic scope.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def add_consultation(self, consultation: Consultation) -> None:
        """Persist a newly created consultation.

        Args:
            consultation: Fully constructed consultation aggregate to insert.

        Raises:
            ConflictError: If a consultation with the same identity already
                exists.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def save_consultation(
        self, consultation: Consultation, *, expected_version: int
    ) -> None:
        """Persist an updated consultation with optimistic-concurrency control.

        Args:
            consultation: Modified consultation aggregate to persist.
            expected_version: Version the caller last read; the store must
                reject the write if the persisted version differs.

        Raises:
            ConcurrencyError: If the persisted version does not match
                ``expected_version``.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def append_entry(self, entry: ClinicalEntry) -> None:
        """Persist a new clinical entry as an append-only record.

        Args:
            entry: Immutable clinical entry to append.

        Raises:
            ConflictError: If an entry with the same identity already exists.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def append_amendment(self, amendment: ClinicalAmendment) -> None:
        """Persist a clinical amendment linked to an existing entry.

        Args:
            amendment: Amendment record to append to the entry's history.

        Raises:
            ConflictError: If an amendment with the same identity already
                exists.
            NotFoundError: If the referenced entry does not exist.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def get_entry(
        self, clinic_id: UUID, entry_id: UUID
    ) -> ClinicalEntry | None:
        """Retrieve a clinical entry by its identifier within a clinic.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            entry_id: Unique identifier of the clinical entry.

        Returns:
            The matching clinical entry, or ``None`` if it does not exist
            within the given clinic scope.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def list_amendments(
        self, clinic_id: UUID, entry_id: UUID
    ) -> tuple[ClinicalAmendment, ...]:
        """Return all amendments for a clinical entry in chronological order.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            entry_id: Identifier of the clinical entry whose amendments are
                requested.

        Returns:
            An immutable tuple of amendments ordered by creation time,
            empty when no amendments exist.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def list_history(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        page: PageRequest,
    ) -> Page[ClinicalEntrySummary]:
        """Return a paginated summary of clinical entries for a patient.

        Results are ordered reverse-chronologically and projected into
        ``ClinicalEntrySummary`` DTOs that omit clinical narrative content.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            patient_id: Identifier of the patient whose history is queried.
            page: Pagination parameters including limit and optional cursor.

        Returns:
            A page of clinical-entry summaries with an optional
            continuation cursor.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def get_prescription(
        self, clinic_id: UUID, prescription_id: UUID
    ) -> Prescription | None:
        """Retrieve a prescription by its identifier within a clinic.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            prescription_id: Unique identifier of the prescription.

        Returns:
            The matching prescription, or ``None`` if it does not exist
            within the given clinic scope.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def add_prescription(self, prescription: Prescription) -> None:
        """Persist a newly created prescription.

        Args:
            prescription: Fully constructed prescription aggregate to insert.

        Raises:
            ConflictError: If a prescription with the same identity already
                exists.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def save_prescription(
        self, prescription: Prescription, *, expected_version: int
    ) -> None:
        """Persist an updated prescription with optimistic-concurrency control.

        Args:
            prescription: Modified prescription aggregate to persist.
            expected_version: Version the caller last read; the store must
                reject the write if the persisted version differs.

        Raises:
            ConcurrencyError: If the persisted version does not match
                ``expected_version``.
            PersistenceError: If the underlying store is unreachable.
        """
        ...


@runtime_checkable
class ServiceCatalogRepository(Protocol):
    """Persistence boundary for service-catalog items within a clinic.

    All operations are scoped by ``clinic_id`` to enforce tenant isolation.
    Mutable ``save`` uses ``expected_version`` for optimistic-concurrency
    control.
    """

    def get(
        self, clinic_id: UUID, service_id: UUID
    ) -> ServiceCatalogItem | None:
        """Retrieve a service-catalog item by its identifier within a clinic.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            service_id: Unique identifier of the service-catalog item.

        Returns:
            The matching service-catalog item, or ``None`` if it does not
            exist within the given clinic scope.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def add(self, service: ServiceCatalogItem) -> None:
        """Persist a newly created service-catalog item.

        Args:
            service: Fully constructed service-catalog item to insert.

        Raises:
            ConflictError: If a service-catalog item with the same identity
                already exists.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def save(
        self, service: ServiceCatalogItem, *, expected_version: int
    ) -> None:
        """Persist an updated service-catalog item with concurrency control.

        Args:
            service: Modified service-catalog item to persist.
            expected_version: Version the caller last read; the store must
                reject the write if the persisted version differs.

        Raises:
            ConcurrencyError: If the persisted version does not match
                ``expected_version``.
            PersistenceError: If the underlying store is unreachable.
        """
        ...

    def list_active(
        self, clinic_id: UUID, page: PageRequest
    ) -> Page[ServiceCatalogItem]:
        """Return a paginated list of active service-catalog items.

        Args:
            clinic_id: Tenant-scoped clinic identifier.
            page: Pagination parameters including limit and optional cursor.

        Returns:
            A page of active service-catalog items with an optional
            continuation cursor.

        Raises:
            PersistenceError: If the underlying store is unreachable.
        """
        ...
