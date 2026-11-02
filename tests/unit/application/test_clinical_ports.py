"""Verification tests for clinical application ports and protocols."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from clinic_management.application.contracts.clinical import ClinicalEntrySummary
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.ports.clinical import (
    ClinicalRepository,
    ServiceCatalogRepository,
)
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.consultation import Consultation
from clinic_management.domain.clinical.prescription import Prescription
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.clinical.service_catalog import ServiceCatalogItem
from clinic_management.domain.shared.money import Money

CLINIC_ID = UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
NOW = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)


class _InMemoryClinicalRepository:
    """In-memory stub implementing ClinicalRepository protocol."""

    def __init__(self) -> None:
        """Initialize in-memory stores."""
        self.consultations: dict[UUID, Consultation] = {}
        self.entries: dict[UUID, ClinicalEntry] = {}
        self.amendments: dict[UUID, ClinicalAmendment] = {}
        self.prescriptions: dict[UUID, Prescription] = {}

    def get_consultation(self, clinic_id: UUID, consultation_id: UUID) -> Consultation | None:
        """Retrieve a consultation."""
        c = self.consultations.get(consultation_id)
        return c if c and c.clinic_id == clinic_id else None

    def add_consultation(self, consultation: Consultation) -> None:
        """Add a consultation."""
        self.consultations[consultation.id] = consultation

    def save_consultation(self, consultation: Consultation, *, expected_version: int) -> None:
        """Save a consultation."""
        self.consultations[consultation.id] = consultation

    def append_entry(self, entry: ClinicalEntry) -> None:
        """Append an entry."""
        self.entries[entry.id] = entry

    def append_amendment(self, amendment: ClinicalAmendment) -> None:
        """Append an amendment."""
        self.amendments[amendment.id] = amendment

    def get_entry(self, clinic_id: UUID, entry_id: UUID) -> ClinicalEntry | None:
        """Retrieve an entry."""
        e = self.entries.get(entry_id)
        return e if e and e.clinic_id == clinic_id else None

    def list_amendments(self, clinic_id: UUID, entry_id: UUID) -> tuple[ClinicalAmendment, ...]:
        """List amendments."""
        return tuple(
            a
            for a in self.amendments.values()
            if a.clinic_id == clinic_id and a.entry_id == entry_id
        )

    def list_history(
        self,
        clinic_id: UUID,
        patient_id: UUID,
        page: PageRequest,
    ) -> Page[ClinicalEntrySummary]:
        """List history summaries."""
        items = tuple(
            ClinicalEntrySummary(
                entry_id=e.id,
                patient_id=e.patient_id,
                kind=e.kind,
                author_id=e.author_id,
                recorded_at=e.recorded_at,
                amended=False,
            )
            for e in self.entries.values()
            if e.clinic_id == clinic_id and e.patient_id == patient_id
        )
        return Page(items=items, next_cursor=None)

    def get_prescription(self, clinic_id: UUID, prescription_id: UUID) -> Prescription | None:
        """Retrieve a prescription."""
        p = self.prescriptions.get(prescription_id)
        return p if p and p.clinic_id == clinic_id else None

    def add_prescription(self, prescription: Prescription) -> None:
        """Add a prescription."""
        self.prescriptions[prescription.id] = prescription

    def save_prescription(self, prescription: Prescription, *, expected_version: int) -> None:
        """Save a prescription."""
        self.prescriptions[prescription.id] = prescription


class _InMemoryServiceCatalogRepository:
    """In-memory stub implementing ServiceCatalogRepository protocol."""

    def __init__(self) -> None:
        """Initialize item store."""
        self.items: dict[UUID, ServiceCatalogItem] = {}

    def get(self, clinic_id: UUID, service_id: UUID) -> ServiceCatalogItem | None:
        """Get an item by id."""
        item = self.items.get(service_id)
        return item if item and item.clinic_id == clinic_id else None

    def add(self, service: ServiceCatalogItem) -> None:
        """Add a service item."""
        self.items[service.id] = service

    def save(self, service: ServiceCatalogItem, *, expected_version: int) -> None:
        """Save a service item."""
        self.items[service.id] = service

    def list_active(self, clinic_id: UUID, page: PageRequest) -> Page[ServiceCatalogItem]:
        """List active items."""
        active_items = tuple(
            i for i in self.items.values() if i.clinic_id == clinic_id and i.active
        )
        return Page(
            items=active_items,
            next_cursor=None,
        )


def test_clinical_repository_protocol_runtime_check() -> None:
    """Verify in-memory clinical repository satisfies runtime protocol check."""
    repo = _InMemoryClinicalRepository()
    assert isinstance(repo, ClinicalRepository)

    consultation = Consultation(
        id=UUID("00000000-0000-0000-0000-000000000010"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        appointment_id=UUID("00000000-0000-0000-0000-000000000011"),
        doctor_id=DOCTOR_ID,
        note="Initial checkup note.",
        created_at=NOW,
        updated_at=NOW,
    )
    repo.add_consultation(consultation)
    assert repo.get_consultation(CLINIC_ID, consultation.id) == consultation
    repo.save_consultation(consultation, expected_version=0)

    entry = ClinicalEntry(
        id=UUID("00000000-0000-0000-0000-000000000020"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        consultation_id=consultation.id,
        author_id=DOCTOR_ID,
        kind="vitals",
        content="BP: 120/80",
        recorded_at=NOW,
    )
    repo.append_entry(entry)
    assert repo.get_entry(CLINIC_ID, entry.id) == entry

    amendment = ClinicalAmendment(
        id=UUID("00000000-0000-0000-0000-000000000025"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        entry_id=entry.id,
        author_id=DOCTOR_ID,
        reason="Vitals update",
        replacement_content="BP: 125/80",
        recorded_at=NOW,
    )
    repo.append_amendment(amendment)
    assert repo.list_amendments(CLINIC_ID, entry.id) == (amendment,)

    page = repo.list_history(CLINIC_ID, PATIENT_ID, PageRequest(limit=10))
    assert len(page.items) == 1
    assert page.next_cursor is None

    prescription = Prescription(
        id=UUID("00000000-0000-0000-0000-000000000030"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
    )
    repo.add_prescription(prescription)
    assert repo.get_prescription(CLINIC_ID, prescription.id) == prescription
    repo.save_prescription(prescription, expected_version=0)


def test_service_catalog_repository_protocol_runtime_check() -> None:
    """Verify in-memory service catalog repository satisfies runtime protocol check."""
    catalog = _InMemoryServiceCatalogRepository()
    assert isinstance(catalog, ServiceCatalogRepository)

    item = ServiceCatalogItem(
        id=UUID("00000000-0000-0000-0000-000000000040"),
        clinic_id=CLINIC_ID,
        code="CONS-GP",
        description="General GP Consultation",
        price=Money(amount=Decimal("2000.00"), currency="DZD"),
    )
    catalog.add(item)
    catalog.save(item, expected_version=0)
    assert catalog.get(CLINIC_ID, item.id) == item
    active_page = catalog.list_active(CLINIC_ID, PageRequest(limit=10))
    assert len(active_page.items) == 1
    assert active_page.next_cursor is None
