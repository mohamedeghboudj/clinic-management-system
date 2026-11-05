"""Author verification tests for medication, prescription and service catalog models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from clinic_management.domain.clinical.enums import PrescriptionStatus
from clinic_management.domain.clinical.medication import Medication
from clinic_management.domain.clinical.prescription import Prescription, PrescriptionItem
from clinic_management.domain.clinical.service_catalog import ServiceCatalogItem
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.money import Money

CLINIC_ID = UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
NOW = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=30)


# ======================================================================
# Medication Tests
# ======================================================================


def test_medication_validates_non_empty_name() -> None:
    """Verify that Medication requires a non-empty name and normalizes strings."""
    med = Medication(name="  Amoxicillin  ", strength=" 500 mg ", form=" capsule ")
    assert med.name == "Amoxicillin"
    assert med.strength == "500 mg"
    assert med.form == "capsule"

    # Only name
    med_only = Medication(name="Aspirin")
    assert med_only.name == "Aspirin"
    assert med_only.strength is None
    assert med_only.form is None

    # Empty name or non-string
    with pytest.raises(ValidationError):
        Medication(name="   ")

    with pytest.raises(ValidationError):
        Medication(name=123)  # type: ignore[arg-type]

    # Empty strength or non-string
    with pytest.raises(ValidationError):
        Medication(name="Aspirin", strength="   ")

    with pytest.raises(ValidationError):
        Medication(name="Aspirin", strength=500)  # type: ignore[arg-type]

    # Empty form or non-string
    with pytest.raises(ValidationError):
        Medication(name="Aspirin", form="   ")

    with pytest.raises(ValidationError):
        Medication(name="Aspirin", form=123)  # type: ignore[arg-type]


# ======================================================================
# Prescription and PrescriptionItem Tests
# ======================================================================


def test_prescription_item_validates_required_directions() -> None:
    """Verify that PrescriptionItem requires valid directions and medication."""
    med = Medication(name="Ibuprofen", strength="400 mg")
    item = PrescriptionItem(
        medication=med,
        dose=" 1 tablet ",
        route=" oral ",
        frequency=" three times daily ",
        duration=" 3 days ",
        instructions=" with water ",
    )
    assert item.dose == "1 tablet"
    assert item.route == "oral"
    assert item.frequency == "three times daily"
    assert item.duration == "3 days"
    assert item.instructions == "with water"

    # Non-medication
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication="not-a-medication",  # type: ignore[arg-type]
            dose="1 tablet",
            route="oral",
            frequency="daily",
            duration="3 days",
        )

    # Empty dose / non-string
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="   ",
            route="oral",
            frequency="daily",
            duration="3 days",
        )
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose=1,  # type: ignore[arg-type]
            route="oral",
            frequency="daily",
            duration="3 days",
        )

    # Empty route / non-string
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="1 tablet",
            route="   ",
            frequency="daily",
            duration="3 days",
        )

    # Empty frequency
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="1 tablet",
            route="oral",
            frequency="   ",
            duration="3 days",
        )

    # Empty duration
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="1 tablet",
            route="oral",
            frequency="daily",
            duration="   ",
        )

    # Empty instructions or non-string
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="1 tablet",
            route="oral",
            frequency="daily",
            duration="3 days",
            instructions="   ",
        )
    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="1 tablet",
            route="oral",
            frequency="daily",
            duration="3 days",
            instructions=123,  # type: ignore[arg-type]
        )


def test_prescription_lifecycle_draft_issue_and_cancel() -> None:
    """Verify full prescription lifecycle: adding items, issuing, and cancelling."""
    med = Medication(name="Paracetamol", strength="500 mg", form="tablet")
    item = PrescriptionItem(
        medication=med,
        dose="1 tablet",
        route="oral",
        frequency="every 8 hours",
        duration="5 days",
        instructions="Take with food.",
    )
    prescription = Prescription(
        id=UUID("00000000-0000-0000-0000-000000000040"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        consultation_id=None,
    )
    assert prescription.status is PrescriptionStatus.DRAFT
    assert len(prescription.items()) == 0

    # Cannot issue without items
    with pytest.raises(ValidationError) as exc:
        prescription.issue(at=NOW)
    assert exc.value.code == "INVALID_VALUE"

    # Add item and issue
    prescription.add_item(item)
    assert len(prescription.items()) == 1
    assert prescription.items()[0] == item

    prescription.issue(at=NOW)
    assert prescription.status.value == PrescriptionStatus.ISSUED.value
    assert prescription.issued_at == NOW
    assert prescription.version == 1

    # Cannot modify issued prescription
    item2 = PrescriptionItem(
        medication=med,
        dose="2 tablets",
        route="oral",
        frequency="once daily",
        duration="3 days",
    )
    with pytest.raises(InvalidTransitionError):
        prescription.add_item(item2)

    with pytest.raises(InvalidTransitionError):
        prescription.remove_item(0)

    # Cancel issued prescription with reason
    prescription.cancel("Patient reported adverse sensitivity.", at=LATER)
    assert prescription.status.value == PrescriptionStatus.CANCELLED.value
    assert prescription.cancel_reason == "Patient reported adverse sensitivity."
    assert prescription.cancelled_at == LATER
    assert prescription.version == 2

    # Cannot cancel already cancelled
    with pytest.raises(InvalidTransitionError):
        prescription.cancel("Already cancelled", at=LATER)

    # Cannot cancel with empty reason
    draft_p = Prescription(
        id=UUID("00000000-0000-0000-0000-000000000041"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
    )
    with pytest.raises(ValidationError):
        draft_p.cancel("   ", at=NOW)
    with pytest.raises(ValidationError):
        draft_p.cancel(123, at=NOW)  # type: ignore[arg-type]

    # Can cancel from DRAFT
    draft_p.cancel("No longer needed", at=NOW)
    assert draft_p.status is PrescriptionStatus.CANCELLED


def test_prescription_item_management_and_validation() -> None:
    """Verify Prescription item addition, removal, and constructor invariants."""
    med = Medication(name="Paracetamol", strength="500 mg")
    item = PrescriptionItem(
        medication=med,
        dose="1 tablet",
        route="oral",
        frequency="once daily",
        duration="3 days",
    )
    cid = UUID("00000000-0000-0000-0000-000000000099")
    prescription = Prescription(
        id=UUID("00000000-0000-0000-0000-000000000042"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        consultation_id=cid,
        items=[item],
    )
    assert prescription.consultation_id == cid
    assert prescription.get_items() == (item,)

    # Add invalid item
    with pytest.raises(ValidationError):
        prescription.add_item("not-an-item")  # type: ignore[arg-type]

    # Remove item out of range
    with pytest.raises(ValidationError):
        prescription.remove_item(-1)
    with pytest.raises(ValidationError):
        prescription.remove_item(5)

    # Valid remove
    prescription.remove_item(0)
    assert len(prescription.items()) == 0

    # Invalid status in constructor
    with pytest.raises(ValidationError):
        Prescription(
            id=UUID("00000000-0000-0000-0000-000000000043"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            status="INVALID",  # type: ignore[arg-type]
        )

    # Invalid item in constructor
    with pytest.raises(ValidationError):
        Prescription(
            id=UUID("00000000-0000-0000-0000-000000000043"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            items=["invalid"],  # type: ignore[list-item]
        )


# ======================================================================
# Service Catalog Item Tests
# ======================================================================


def test_service_catalog_item_creation_and_price_change() -> None:
    """Verify ServiceCatalogItem price validation and price modification."""
    price = Money(amount=Decimal("2500.00"), currency="DZD")
    item = ServiceCatalogItem(
        id=UUID("00000000-0000-0000-0000-000000000050"),
        clinic_id=CLINIC_ID,
        code="CONS-GP",
        description="General Practitioner Consultation",
        price=price,
        duration_minutes=30,
    )
    assert item.code == "CONS-GP"
    assert item.price == price
    assert item.active is True
    assert item.version == 0

    new_price = Money(amount=Decimal("3000.00"), currency="DZD")
    item.change_price(new_price)
    assert item.price == new_price
    assert item.version == 1


def test_service_catalog_item_activation_lifecycle() -> None:
    """Verify that catalogue items can be deactivated and reactivated."""
    item = ServiceCatalogItem(
        id=UUID("00000000-0000-0000-0000-000000000052"),
        clinic_id=CLINIC_ID,
        code="CONS-SP",
        description="Specialist Consultation",
        price=Money(amount=Decimal("4000.00"), currency="DZD"),
    )
    item.deactivate()
    assert item.active is False
    assert item.version == 1

    item.activate()
    assert bool(item.active) is True
    assert item.version == 2


def test_service_catalog_item_rejects_negative_price_or_empty_code() -> None:
    """Verify that negative price or blank code raises ValidationError."""
    price = Money(amount=Decimal("1000.00"), currency="DZD")

    # Empty code
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="  ",
            description="Consultation",
            price=price,
        )

    # Non-str code
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code=123,  # type: ignore[arg-type]
            description="Consultation",
            price=price,
        )

    # Empty description or non-str
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="CONS",
            description="   ",
            price=price,
        )
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="CONS",
            description=None,  # type: ignore[arg-type]
            price=price,
        )

    # Non-Money price
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="CONS",
            description="Consultation",
            price="1000",  # type: ignore[arg-type]
        )

    # Invalid duration minutes
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="CONS",
            description="Consultation",
            price=price,
            duration_minutes=0,
        )
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="CONS",
            description="Consultation",
            price=price,
            duration_minutes="30",  # type: ignore[arg-type]
        )

    # Change price invalid
    item = ServiceCatalogItem(
        id=UUID("00000000-0000-0000-0000-000000000053"),
        clinic_id=CLINIC_ID,
        code="CONS",
        description="Consultation",
        price=price,
    )
    with pytest.raises(ValidationError):
        item.change_price("invalid")  # type: ignore[arg-type]
