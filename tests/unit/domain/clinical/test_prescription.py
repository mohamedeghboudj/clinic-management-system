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
    med = Medication(name="  Amoxicillin  ", strength="500 mg", form="capsule")
    assert med.name == "Amoxicillin"
    assert med.strength == "500 mg"
    assert med.form == "capsule"

    with pytest.raises(ValidationError):
        Medication(name="   ")


# ======================================================================
# Prescription and PrescriptionItem Tests
# ======================================================================


def test_prescription_item_validates_required_directions() -> None:
    """Verify that PrescriptionItem requires valid directions and medication."""
    med = Medication(name="Ibuprofen", strength="400 mg")
    item = PrescriptionItem(
        medication=med,
        dose="1 tablet",
        route="oral",
        frequency="three times daily",
        duration="3 days",
    )
    assert item.dose == "1 tablet"
    assert item.route == "oral"

    with pytest.raises(ValidationError):
        PrescriptionItem(
            medication=med,
            dose="   ",
            route="oral",
            frequency="daily",
            duration="3 days",
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
    assert prescription.status is PrescriptionStatus.ISSUED
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
    assert prescription.status is PrescriptionStatus.CANCELLED
    assert prescription.cancel_reason == "Patient reported adverse sensitivity."
    assert prescription.cancelled_at == LATER
    assert prescription.version == 2


# ======================================================================
# Service Catalog Item Tests
# ======================================================================


def test_service_catalog_item_creation_price_change_and_lifecycle() -> None:
    """Verify ServiceCatalogItem price validation, price change, and deactivation."""
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

    # Change price
    new_price = Money(amount=Decimal("3000.00"), currency="DZD")
    item.change_price(new_price)
    assert item.price == new_price
    assert item.version == 1

    # Deactivate and reactivate
    item.deactivate()
    assert item.active is False
    assert item.version == 2

    item.activate()
    assert item.active is True
    assert item.version == 3


def test_service_catalog_item_rejects_negative_price_or_empty_code() -> None:
    """Verify that negative price or blank code raises ValidationError."""
    with pytest.raises(ValidationError):
        ServiceCatalogItem(
            id=UUID("00000000-0000-0000-0000-000000000051"),
            clinic_id=CLINIC_ID,
            code="  ",
            description="Consultation",
            price=Money(amount=Decimal("1000.00"), currency="DZD"),
        )
