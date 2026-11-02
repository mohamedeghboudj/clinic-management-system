"""Author verification tests for consultation, record entry and amendment models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from clinic_management.application.contracts.clinical import ClinicalEntrySummary
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.consultation import Consultation
from clinic_management.domain.clinical.enums import ConsultationStatus
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.clinical.validation import validate_clinical_text
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)

CLINIC_ID = UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
APPOINTMENT_ID = UUID("00000000-0000-0000-0000-000000000004")
NOW = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=30)


# ======================================================================
# Text Validation Helper Tests
# ======================================================================


def test_validate_clinical_text_strips_and_preserves_paragraphs() -> None:
    """Verify that clinical text is stripped of outer whitespace but preserves layout."""
    raw = "  \nFirst line.\n\nSecond line.  \n"
    validated = validate_clinical_text(raw, field="note", max_length=1000)
    assert validated == "First line.\n\nSecond line."


def test_validate_clinical_text_rejects_empty_or_whitespace() -> None:
    """Verify that empty or whitespace-only text raises ValidationError."""
    with pytest.raises(ValidationError) as exc:
        validate_clinical_text("   \n\t  ", field="note", max_length=100)
    assert exc.value.code == "INVALID_VALUE"
    assert exc.value.message_key == "clinical.note.empty"


def test_validate_clinical_text_rejects_exceeding_max_length() -> None:
    """Verify that text exceeding maximum length raises ValidationError."""
    with pytest.raises(ValidationError) as exc:
        validate_clinical_text("A" * 51, field="note", max_length=50)
    assert exc.value.code == "INVALID_VALUE"
    assert exc.value.message_key == "clinical.note.too_long"


# ======================================================================
# Consultation Tests
# ======================================================================


def test_consultation_lifecycle_draft_to_final() -> None:
    """Verify standard consultation draft composition, note updating, and finalization."""
    consultation = Consultation(
        id=UUID("00000000-0000-0000-0000-000000000010"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        appointment_id=APPOINTMENT_ID,
        doctor_id=DOCTOR_ID,
        note="Patient presents with mild fever.",
        created_at=NOW,
        updated_at=NOW,
    )
    assert consultation.status is ConsultationStatus.DRAFT
    assert consultation.version == 0
    assert consultation.finalized_at is None

    # Update note in draft
    consultation.update_note("Patient presents with mild fever and cough.", at=LATER)
    assert consultation.note == "Patient presents with mild fever and cough."
    assert consultation.updated_at == LATER

    # Finalize
    final_time = LATER + timedelta(minutes=15)
    consultation.finalize(at=final_time)
    assert consultation.status is ConsultationStatus.FINAL
    assert consultation.finalized_at == final_time
    assert consultation.version == 1


def test_consultation_finalized_note_cannot_be_updated() -> None:
    """Verify that editing a finalized consultation raises InvalidTransitionError."""
    consultation = Consultation(
        id=UUID("00000000-0000-0000-0000-000000000011"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        appointment_id=APPOINTMENT_ID,
        doctor_id=DOCTOR_ID,
        note="Initial clinical note.",
        created_at=NOW,
        updated_at=NOW,
    )
    consultation.finalize(at=LATER)

    with pytest.raises(InvalidTransitionError) as exc:
        consultation.update_note("Attempted silent edit.", at=LATER + timedelta(hours=1))
    assert exc.value.code == "INVALID_TRANSITION"


def test_consultation_cannot_be_finalized_twice() -> None:
    """Verify that finalising an already final consultation raises InvalidTransitionError."""
    consultation = Consultation(
        id=UUID("00000000-0000-0000-0000-000000000012"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        appointment_id=APPOINTMENT_ID,
        doctor_id=DOCTOR_ID,
        note="Final note.",
        created_at=NOW,
        updated_at=NOW,
    )
    consultation.finalize(at=LATER)

    with pytest.raises(InvalidTransitionError) as exc:
        consultation.finalize(at=LATER + timedelta(minutes=5))
    assert exc.value.code == "INVALID_TRANSITION"


def test_consultation_rejects_naive_timestamp() -> None:
    """Verify that naive timestamps are rejected during construction."""
    naive_time = datetime(2026, 11, 2, 10, 0, 0)
    with pytest.raises(ValidationError):
        Consultation(
            id=UUID("00000000-0000-0000-0000-000000000013"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            appointment_id=APPOINTMENT_ID,
            doctor_id=DOCTOR_ID,
            note="Note text.",
            created_at=naive_time,
            updated_at=NOW,
        )


# ======================================================================
# ClinicalEntry and ClinicalAmendment Tests
# ======================================================================


def test_clinical_entry_is_immutable_and_validates_fields() -> None:
    """Verify that ClinicalEntry is frozen and enforces kind and content rules."""
    entry = ClinicalEntry(
        id=UUID("00000000-0000-0000-0000-000000000020"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        consultation_id=UUID("00000000-0000-0000-0000-000000000010"),
        author_id=DOCTOR_ID,
        kind="consultation_note",
        content="Patient has normal blood pressure.",
        recorded_at=NOW,
    )
    assert entry.kind == "consultation_note"
    assert entry.content == "Patient has normal blood pressure."

    with pytest.raises(FrozenInstanceError):
        entry.content = "New content"  # type: ignore[misc]


def test_clinical_amendment_applies_to_matching_entry() -> None:
    """Verify that an amendment correctly verifies matching entry, patient, and clinic IDs."""
    entry_id = UUID("00000000-0000-0000-0000-000000000021")
    entry = ClinicalEntry(
        id=entry_id,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        consultation_id=None,
        author_id=DOCTOR_ID,
        kind="consultation_note",
        content="Blood pressure was 120/80.",
        recorded_at=NOW,
    )
    amendment = ClinicalAmendment(
        id=UUID("00000000-0000-0000-0000-000000000030"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        entry_id=entry_id,
        author_id=DOCTOR_ID,
        reason="Typographical correction of measured reading.",
        replacement_content="Blood pressure was 130/80.",
        recorded_at=LATER,
    )
    assert amendment.applies_to(entry) is True

    # Mismatched entry
    other_entry = ClinicalEntry(
        id=UUID("00000000-0000-0000-0000-000000000022"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        consultation_id=None,
        author_id=DOCTOR_ID,
        kind="consultation_note",
        content="Other note.",
        recorded_at=NOW,
    )
    assert amendment.applies_to(other_entry) is False


def test_clinical_amendment_rejects_empty_reason() -> None:
    """Verify that an amendment without a reason raises ValidationError."""
    with pytest.raises(ValidationError) as exc:
        ClinicalAmendment(
            id=UUID("00000000-0000-0000-0000-000000000031"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            entry_id=UUID("00000000-0000-0000-0000-000000000021"),
            author_id=DOCTOR_ID,
            reason="   ",
            replacement_content="Corrected note.",
            recorded_at=NOW,
        )
    assert exc.value.code == "INVALID_VALUE"


# ======================================================================
# DTO Contract Tests
# ======================================================================


def test_clinical_entry_summary_dto() -> None:
    """Verify ClinicalEntrySummary DTO validates fields and preserves projection."""
    summary = ClinicalEntrySummary(
        entry_id=UUID("00000000-0000-0000-0000-000000000060"),
        patient_id=PATIENT_ID,
        kind="prescription",
        author_id=DOCTOR_ID,
        recorded_at=NOW,
        amended=False,
    )
    assert summary.kind == "prescription"
    assert summary.amended is False
