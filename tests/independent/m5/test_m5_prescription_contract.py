"""Independent M5 contract and boundary tests for M4 prescription and catalogue models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from clinic_management.application.contracts.clinical import ClinicalEntrySummary
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.ports.clinical import (
    ClinicalRepository,
    ServiceCatalogRepository,
)
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.consultation import Consultation
from clinic_management.domain.clinical.enums import PrescriptionStatus
from clinic_management.domain.clinical.medication import Medication
from clinic_management.domain.clinical.prescription import (
    Prescription,
    PrescriptionItem,
)
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.clinical.service_catalog import ServiceCatalogItem
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.money import Money

CLINIC_ID = UUID("10000000-0000-0000-0000-000000000001")
PATIENT_ID = UUID("20000000-0000-0000-0000-000000000002")
DOCTOR_ID = UUID("30000000-0000-0000-0000-000000000003")
CONSULTATION_ID = UUID("50000000-0000-0000-0000-000000000005")
PRESCRIPTION_ID = UUID("80000000-0000-0000-0000-000000000008")
SERVICE_ID = UUID("90000000-0000-0000-0000-000000000009")

T0 = datetime(2026, 11, 2, 9, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(minutes=15)
NAIVE_DT = datetime(2026, 11, 2, 9, 0, 0)
NON_UTC_DT = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone(timedelta(hours=1)))


class _DummyClinicalRepository:
    """Structural fake satisfying the ClinicalRepository protocol."""

    def get_consultation(self, clinic_id: UUID, consultation_id: UUID) -> Consultation | None:
        """Return None for consultation lookup."""
        _ = (clinic_id, consultation_id)
        return None

    def add_consultation(self, consultation: Consultation) -> None:
        """Accept a new consultation."""
        _ = consultation

    def save_consultation(self, consultation: Consultation, *, expected_version: int) -> None:
        """Accept an updated consultation."""
        _ = (consultation, expected_version)

    def append_entry(self, entry: ClinicalEntry) -> None:
        """Accept an immutable clinical entry."""
        _ = entry

    def append_amendment(self, amendment: ClinicalAmendment) -> None:
        """Accept an immutable clinical amendment."""
        _ = amendment

    def get_entry(self, clinic_id: UUID, entry_id: UUID) -> ClinicalEntry | None:
        """Return None for clinical entry lookup."""
        _ = (clinic_id, entry_id)
        return None

    def list_amendments(self, clinic_id: UUID, entry_id: UUID) -> tuple[ClinicalAmendment, ...]:
        """Return an empty tuple of amendments."""
        _ = (clinic_id, entry_id)
        return ()

    def list_history(
        self, clinic_id: UUID, patient_id: UUID, page: PageRequest
    ) -> Page[ClinicalEntrySummary]:
        """Return an empty page of clinical entry summaries."""
        _ = (clinic_id, patient_id, page)
        return Page(items=(), next_cursor=None)

    def get_prescription(self, clinic_id: UUID, prescription_id: UUID) -> Prescription | None:
        """Return None for prescription lookup."""
        _ = (clinic_id, prescription_id)
        return None

    def add_prescription(self, prescription: Prescription) -> None:
        """Accept a new prescription."""
        _ = prescription

    def save_prescription(self, prescription: Prescription, *, expected_version: int) -> None:
        """Accept an updated prescription."""
        _ = (prescription, expected_version)


class _DummyServiceCatalogRepository:
    """Structural fake satisfying the ServiceCatalogRepository protocol."""

    def get(self, clinic_id: UUID, service_id: UUID) -> ServiceCatalogItem | None:
        """Return None for service lookup."""
        _ = (clinic_id, service_id)
        return None

    def add(self, service: ServiceCatalogItem) -> None:
        """Accept a new service catalog item."""
        _ = service

    def save(self, service: ServiceCatalogItem, *, expected_version: int) -> None:
        """Accept an updated service catalog item."""
        _ = (service, expected_version)

    def list_active(self, clinic_id: UUID, page: PageRequest) -> Page[ServiceCatalogItem]:
        """Return an empty page of active services."""
        _ = (clinic_id, page)
        return Page(items=(), next_cursor=None)


def _sample_item(name: str = "Amoxicillin") -> PrescriptionItem:
    """Create a valid baseline PrescriptionItem for independent tests."""
    return PrescriptionItem(
        medication=Medication(name=name, strength="500 mg", form="capsule"),
        dose="1 capsule",
        route="oral",
        frequency="three times daily",
        duration="7 days",
        instructions="Take after meals.",
    )


def test_medication_is_frozen_and_normalizes_optional_fields() -> None:
    """Medication strips whitespace, allows None optionals, and is immutable."""
    med = Medication(name="  Metformin ", strength=" 850 mg ", form=" tablet ")
    assert med.name == "Metformin"
    assert med.strength == "850 mg"
    assert med.form == "tablet"

    with pytest.raises(FrozenInstanceError):
        med.name = "Other"  # type: ignore[misc]


def test_prescription_item_is_frozen_and_validates_all_directions() -> None:
    """PrescriptionItem trims strings, permits None instructions, and is immutable."""
    item = PrescriptionItem(
        medication=Medication(name="Cetirizine"),
        dose=" 10 mg ",
        route=" oral ",
        frequency=" once daily ",
        duration=" 5 days ",
        instructions=None,
    )
    assert item.dose == "10 mg"
    assert item.route == "oral"
    assert item.frequency == "once daily"
    assert item.duration == "5 days"
    assert item.instructions is None

    with pytest.raises(FrozenInstanceError):
        item.dose = "20 mg"  # type: ignore[misc]


def test_prescription_defensive_copy_and_rehydration_timestamps() -> None:
    """Prescription copies caller item list defensively and validates rehydrated UTC times."""
    caller_items = [_sample_item("Amoxicillin"), _sample_item("Ibuprofen")]
    rehydrated = Prescription(
        id=PRESCRIPTION_ID,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        consultation_id=CONSULTATION_ID,
        items=caller_items,
        status=PrescriptionStatus.CANCELLED,
        issued_at=T0,
        cancel_reason="Replaced with alternative regimen.",
        cancelled_at=T1,
        version=2,
    )
    caller_items.clear()
    assert len(rehydrated.items()) == 2
    assert rehydrated.get_items() == rehydrated.items()
    assert rehydrated.issued_at == T0
    assert rehydrated.cancelled_at == T1
    assert rehydrated.version == 2

    with pytest.raises(ValidationError):
        Prescription(
            id=PRESCRIPTION_ID,
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            items=[_sample_item()],
            status=PrescriptionStatus.ISSUED,
            issued_at=NAIVE_DT,
        )

    with pytest.raises(ValidationError):
        Prescription(
            id=PRESCRIPTION_ID,
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            items=[_sample_item()],
            status=PrescriptionStatus.CANCELLED,
            cancelled_at=NON_UTC_DT,
        )


@pytest.mark.parametrize(
    "bad_field",
    ["id", "clinic_id", "patient_id", "doctor_id", "consultation_id"],
)
def test_prescription_rejects_invalid_uuids(bad_field: str) -> None:
    """Prescription validates all required and optional UUID identifiers."""
    kwargs: dict[str, object] = {
        "id": PRESCRIPTION_ID,
        "clinic_id": CLINIC_ID,
        "patient_id": PATIENT_ID,
        "doctor_id": DOCTOR_ID,
        "consultation_id": CONSULTATION_ID,
    }
    kwargs[bad_field] = "invalid-uuid"
    with pytest.raises(ValidationError):
        Prescription(**kwargs)  # type: ignore[arg-type]


def test_prescription_transition_guards_and_failure_atomicity() -> None:
    """Failed issue or cancel calls preserve existing Prescription state and version."""
    prescription = Prescription(
        id=PRESCRIPTION_ID,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
    )
    item1 = _sample_item("Medication A")
    item2 = _sample_item("Medication B")
    prescription.add_item(item1)
    prescription.add_item(item2)
    prescription.remove_item(0)
    assert prescription.items() == (item2,)

    with pytest.raises(ValidationError):
        prescription.issue(at=NAIVE_DT)
    assert prescription.status is PrescriptionStatus.DRAFT
    assert prescription.issued_at is None
    assert prescription.version == 0

    prescription.issue(at=T0)
    assert prescription.status.value == PrescriptionStatus.ISSUED.value
    assert prescription.version == 1

    with pytest.raises(InvalidTransitionError):
        prescription.issue(at=T1)

    with pytest.raises(ValidationError):
        prescription.cancel("   ", at=T1)
    assert prescription.status.value == PrescriptionStatus.ISSUED.value
    assert prescription.cancel_reason is None
    assert prescription.cancelled_at is None
    assert prescription.version == 1

    with pytest.raises(ValidationError):
        prescription.cancel("Valid reason", at=NAIVE_DT)
    assert prescription.status.value == PrescriptionStatus.ISSUED.value
    assert prescription.version == 1


def test_service_catalog_item_validates_zero_and_negative_money_prices() -> None:
    """ServiceCatalogItem accepts zero Money price and rejects negative Money amounts."""
    free_service = ServiceCatalogItem(
        id=SERVICE_ID,
        clinic_id=CLINIC_ID,
        code="  FOLLOW-UP  ",
        description="  Post-op checkup  ",
        price=Money(amount=Decimal("0.00"), currency="DZD"),
        duration_minutes=None,
    )
    assert free_service.code == "FOLLOW-UP"
    assert free_service.description == "Post-op checkup"
    assert free_service.price.is_zero() is True
    assert free_service.duration_minutes is None

    negative_price = Money(amount=Decimal("-50.00"), currency="DZD")
    with pytest.raises(ValidationError) as neg_exc:
        ServiceCatalogItem(
            id=SERVICE_ID,
            clinic_id=CLINIC_ID,
            code="CONS-NEG",
            description="Invalid negative service",
            price=negative_price,
        )
    assert neg_exc.value.code == "INVALID_VALUE"
    assert neg_exc.value.message_key == "clinical.service_catalog.price.negative"

    with pytest.raises(ValidationError) as change_neg_exc:
        free_service.change_price(negative_price)
    assert change_neg_exc.value.message_key == "clinical.service_catalog.price.negative"
    assert free_service.version == 0


def test_clinical_and_service_catalog_repository_protocols_are_runtime_checkable() -> None:
    """Structural fakes implementing the documented port methods satisfy isinstance checks."""
    assert isinstance(_DummyClinicalRepository(), ClinicalRepository)
    assert isinstance(_DummyServiceCatalogRepository(), ServiceCatalogRepository)
    assert not isinstance(object(), ClinicalRepository)
    assert not isinstance(object(), ServiceCatalogRepository)
