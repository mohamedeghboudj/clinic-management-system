"""Independent M5 contract and boundary tests for M4 consultation deliverables."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from clinic_management.application.contracts.clinical import ClinicalEntrySummary
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.consultation import Consultation
from clinic_management.domain.clinical.enums import (
    ConsultationStatus,
    PrescriptionStatus,
)
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.clinical.validation import validate_clinical_text
from clinic_management.domain.shared.errors import (
    ValidationError,
)

CLINIC_ID = UUID("10000000-0000-0000-0000-000000000001")
OTHER_CLINIC_ID = UUID("10000000-0000-0000-0000-000000000099")
PATIENT_ID = UUID("20000000-0000-0000-0000-000000000002")
OTHER_PATIENT_ID = UUID("20000000-0000-0000-0000-000000000099")
DOCTOR_ID = UUID("30000000-0000-0000-0000-000000000003")
APPOINTMENT_ID = UUID("40000000-0000-0000-0000-000000000004")
CONSULTATION_ID = UUID("50000000-0000-0000-0000-000000000005")
ENTRY_ID = UUID("60000000-0000-0000-0000-000000000006")
AMENDMENT_ID = UUID("70000000-0000-0000-0000-000000000007")

T0 = datetime(2026, 11, 2, 9, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(minutes=20)
T2 = T0 + timedelta(minutes=45)
NAIVE_DT = datetime(2026, 11, 2, 9, 0, 0)
NON_UTC_DT = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone(timedelta(hours=1)))


def _make_consultation(
    *,
    status: ConsultationStatus = ConsultationStatus.DRAFT,
    finalized_at: datetime | None = None,
    note: str = "Initial clinical assessment note.",
) -> Consultation:
    """Construct a valid baseline Consultation aggregate for independent tests."""
    return Consultation(
        id=CONSULTATION_ID,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        appointment_id=APPOINTMENT_ID,
        doctor_id=DOCTOR_ID,
        note=note,
        created_at=T0,
        updated_at=T0,
        status=status,
        finalized_at=finalized_at,
    )


def test_enums_expose_expected_lifecycle_values() -> None:
    """Clinical status enumerations expose the documented string values."""
    assert ConsultationStatus.DRAFT.value == "DRAFT"
    assert ConsultationStatus.FINAL.value == "FINAL"
    assert PrescriptionStatus.DRAFT.value == "DRAFT"
    assert PrescriptionStatus.ISSUED.value == "ISSUED"
    assert PrescriptionStatus.CANCELLED.value == "CANCELLED"


def test_validate_clinical_text_exact_length_boundaries_and_safe_details() -> None:
    """Clinical text helper allows exact max_length and reports safe_details on overflow."""
    exact = "N" * 50
    assert validate_clinical_text(f"  {exact}\n ", field="note", max_length=50) == exact

    with pytest.raises(ValidationError) as exc_info:
        validate_clinical_text("N" * 51, field="note", max_length=50)
    assert exc_info.value.code == "INVALID_VALUE"
    assert exc_info.value.message_key == "clinical.note.too_long"
    assert exc_info.value.safe_details == {"field": "note", "max_length": "50"}


def test_consultation_rehydration_with_final_state_and_entity_identity() -> None:
    """Consultation supports valid FINAL rehydration and compares by Entity ID."""
    rehydrated = _make_consultation(
        status=ConsultationStatus.FINAL,
        finalized_at=T1,
        note="  Finalized assessment note.  ",
    )
    assert rehydrated.status is ConsultationStatus.FINAL
    assert rehydrated.finalized_at == T1
    assert rehydrated.note == "Finalized assessment note."

    duplicate_identity = _make_consultation(note="Different draft note text")
    assert rehydrated == duplicate_identity


def test_consultation_rejects_invalid_status_and_bad_finalized_at() -> None:
    """Consultation construction rejects non-enum status and non-UTC finalized_at."""
    with pytest.raises(ValidationError) as status_exc:
        Consultation(
            id=CONSULTATION_ID,
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            appointment_id=APPOINTMENT_ID,
            doctor_id=DOCTOR_ID,
            note="Valid note.",
            created_at=T0,
            updated_at=T0,
            status="DRAFT",  # type: ignore[arg-type]
        )
    assert status_exc.value.message_key == "clinical.consultation.status.invalid"

    with pytest.raises(ValidationError):
        _make_consultation(status=ConsultationStatus.FINAL, finalized_at=NAIVE_DT)

    with pytest.raises(ValidationError):
        _make_consultation(status=ConsultationStatus.FINAL, finalized_at=NON_UTC_DT)


@pytest.mark.parametrize(
    "bad_field",
    ["id", "clinic_id", "patient_id", "appointment_id", "doctor_id"],
)
def test_consultation_rejects_non_uuid_identifiers(bad_field: str) -> None:
    """Every identifier on Consultation must be a valid UUID instance."""
    kwargs: dict[str, object] = {
        "id": CONSULTATION_ID,
        "clinic_id": CLINIC_ID,
        "patient_id": PATIENT_ID,
        "appointment_id": APPOINTMENT_ID,
        "doctor_id": DOCTOR_ID,
        "note": "Valid clinical note.",
        "created_at": T0,
        "updated_at": T0,
    }
    kwargs[bad_field] = "not-a-uuid"
    with pytest.raises(ValidationError):
        Consultation(**kwargs)  # type: ignore[arg-type]


def test_consultation_update_note_and_finalize_preserve_state_on_invalid_inputs() -> None:
    """Failed update_note or finalize calls do not partially mutate draft state."""
    consultation = _make_consultation(note="Original draft note.")

    with pytest.raises(ValidationError):
        consultation.update_note("   ", at=T1)
    assert consultation.note == "Original draft note."
    assert consultation.updated_at == T0

    with pytest.raises(ValidationError):
        consultation.update_note("Valid replacement.", at=NAIVE_DT)
    assert consultation.note == "Original draft note."
    assert consultation.updated_at == T0

    with pytest.raises(ValidationError):
        consultation.finalize(at=NON_UTC_DT)
    assert consultation.status is ConsultationStatus.DRAFT
    assert consultation.finalized_at is None
    assert consultation.version == 0

    consultation.finalize(at=T2)
    assert consultation.status.value == ConsultationStatus.FINAL.value
    assert consultation.finalized_at == T2
    assert consultation.updated_at == T2
    assert consultation.version == 1


def test_clinical_entry_validates_uuids_timestamps_and_exact_limits() -> None:
    """ClinicalEntry enforces UUIDs, UTC timestamps, and 100/100_000 length caps."""
    max_kind = "k" * 100
    max_content = "c" * 100_000
    entry = ClinicalEntry(
        id=ENTRY_ID,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        consultation_id=None,
        author_id=DOCTOR_ID,
        kind=f"  {max_kind}  ",
        content=max_content,
        recorded_at=T0,
    )
    assert entry.kind == max_kind
    assert len(entry.content) == 100_000
    assert entry.consultation_id is None

    with pytest.raises(ValidationError):
        ClinicalEntry(
            id=ENTRY_ID,
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            consultation_id="bad-consultation-id",  # type: ignore[arg-type]
            author_id=DOCTOR_ID,
            kind="examination",
            content="Valid content.",
            recorded_at=T0,
        )

    with pytest.raises(ValidationError):
        ClinicalEntry(
            id=ENTRY_ID,
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            consultation_id=CONSULTATION_ID,
            author_id=DOCTOR_ID,
            kind="examination",
            content="c" * 100_001,
            recorded_at=T0,
        )


def test_clinical_amendment_validates_reason_bounds_and_preserves_entry() -> None:
    """ClinicalAmendment enforces the 2,000-char reason limit and keeps original entry intact."""
    entry = ClinicalEntry(
        id=ENTRY_ID,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        consultation_id=CONSULTATION_ID,
        author_id=DOCTOR_ID,
        kind="examination",
        content="Initial observation: temperature 37.2 C.",
        recorded_at=T0,
    )

    max_reason = "R" * 2_000
    amendment = ClinicalAmendment(
        id=AMENDMENT_ID,
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        entry_id=ENTRY_ID,
        author_id=DOCTOR_ID,
        reason=f"  {max_reason}  ",
        replacement_content="  Corrected observation: temperature 38.2 C.  ",
        recorded_at=T1,
    )
    assert amendment.reason == max_reason
    assert amendment.replacement_content == "Corrected observation: temperature 38.2 C."
    assert amendment.applies_to(entry) is True
    assert entry.content == "Initial observation: temperature 37.2 C."

    with pytest.raises(FrozenInstanceError):
        amendment.reason = "Tampered reason"  # type: ignore[misc]

    with pytest.raises(ValidationError) as reason_exc:
        ClinicalAmendment(
            id=AMENDMENT_ID,
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            entry_id=ENTRY_ID,
            author_id=DOCTOR_ID,
            reason="R" * 2_001,
            replacement_content="Corrected text.",
            recorded_at=T1,
        )
    assert reason_exc.value.code == "INVALID_VALUE"
    assert reason_exc.value.message_key == "clinical.amendment.reason.too_long"
    assert reason_exc.value.safe_details == {"field": "reason", "max_length": "2000"}


def test_clinical_entry_summary_omits_sensitive_narrative_fields() -> None:
    """ClinicalEntrySummary DTO exposes only index metadata and rejects invalid inputs."""
    field_names = {f.name for f in fields(ClinicalEntrySummary)}
    assert field_names == {
        "entry_id",
        "patient_id",
        "kind",
        "author_id",
        "recorded_at",
        "amended",
    }
    assert "content" not in field_names
    assert "note" not in field_names
    assert "replacement_content" not in field_names

    summary = ClinicalEntrySummary(
        entry_id=ENTRY_ID,
        patient_id=PATIENT_ID,
        kind="examination",
        author_id=DOCTOR_ID,
        recorded_at=T0,
        amended=True,
    )
    assert summary.amended is True

    with pytest.raises(ValidationError):
        ClinicalEntrySummary(
            entry_id=ENTRY_ID,
            patient_id=PATIENT_ID,
            kind="examination",
            author_id=DOCTOR_ID,
            recorded_at=NAIVE_DT,
            amended=False,
        )
