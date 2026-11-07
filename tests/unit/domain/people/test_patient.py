"""Unit tests for the Patient domain entity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from clinic_management.domain.people.patient import Patient
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError


@pytest.fixture
def sample_emergency_contact() -> ContactInfo:
    """Fixture returning a valid emergency ContactInfo."""
    return ContactInfo(phone="0550123456", email="emergency@clinic.dz")


class TestPatientConstruction:
    """Tests for Patient entity construction and validation."""

    def test_valid_minimal_patient(self) -> None:
        """Patient with required fields only (active, no emergency contact)."""
        pid = uuid4()
        cid = uuid4()
        person_id = uuid4()

        patient = Patient(
            id=pid,
            clinic_id=cid,
            person_id=person_id,
            patient_number="PAT-2026-0001",
        )

        assert patient.id == pid
        assert patient.version == 0
        assert patient.clinic_id == cid
        assert patient.person_id == person_id
        assert patient.patient_number == "PAT-2026-0001"
        assert patient.emergency_contact is None
        assert patient.archived_at is None
        assert patient.is_active() is True

    def test_valid_patient_with_emergency_contact(
        self, sample_emergency_contact: ContactInfo
    ) -> None:
        """Patient constructed with emergency contact."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="  PAT-0042  ",
            emergency_contact=sample_emergency_contact,
        )

        assert patient.patient_number == "PAT-0042"
        assert patient.emergency_contact == sample_emergency_contact
        assert patient.is_active() is True

    def test_valid_archived_patient_construction(self) -> None:
        """Patient constructed directly in an archived state."""
        archive_time = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-ARCHIVED",
            archived_at=archive_time,
        )

        assert patient.archived_at == archive_time
        assert patient.is_active() is False

    @pytest.mark.parametrize(
        ("field_name", "kwargs"),
        [
            ("id", {"id": "invalid-uuid"}),
            ("clinic_id", {"clinic_id": 12345}),
            ("person_id", {"person_id": None}),
        ],
    )
    def test_invalid_identifiers_raise_validation_error(
        self, field_name: str, kwargs: dict[str, object]
    ) -> None:
        """Non-UUID identifiers raise ValidationError."""
        base: dict[str, object] = {
            "id": uuid4(),
            "clinic_id": uuid4(),
            "person_id": uuid4(),
            "patient_number": "PAT-001",
        }
        base.update(kwargs)
        with pytest.raises(ValidationError):
            Patient(**base)  # type: ignore[arg-type]

    @pytest.mark.parametrize("invalid_version", [-1, -10, 1.5, "0", True])
    def test_invalid_version_raises_validation_error(self, invalid_version: object) -> None:
        """Invalid version integers raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Patient(
                id=uuid4(),
                version=invalid_version,  # type: ignore[arg-type]
                clinic_id=uuid4(),
                person_id=uuid4(),
                patient_number="PAT-001",
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "version"

    @pytest.mark.parametrize("empty_num", ["", "   ", "\t\n"])
    def test_empty_or_whitespace_patient_number_rejected(self, empty_num: str) -> None:
        """Empty or whitespace patient number raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Patient(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                patient_number=empty_num,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "patient_number"

    def test_patient_number_too_long_rejected(self) -> None:
        """Patient number exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Patient(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                patient_number="X" * 51,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "patient_number"

    def test_invalid_emergency_contact_type_rejected(self) -> None:
        """Non-ContactInfo emergency_contact raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Patient(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                patient_number="PAT-001",
                emergency_contact="0550123456",  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "emergency_contact"

    def test_naive_archived_at_on_construction_rejected(self) -> None:
        """Naive datetime for archived_at on construction raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Patient(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                patient_number="PAT-001",
                archived_at=datetime(2026, 11, 1, 10, 0),  # Naive
            )
        assert exc_info.value.code == "INVALID_VALUE"

    def test_non_utc_archived_at_on_construction_rejected(self) -> None:
        """Non-zero UTC offset timestamp raises ValidationError."""
        non_utc = datetime(2026, 11, 1, 10, 0, tzinfo=timezone(timedelta(hours=1)))
        with pytest.raises(ValidationError) as exc_info:
            Patient(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                patient_number="PAT-001",
                archived_at=non_utc,
            )
        assert exc_info.value.code == "INVALID_VALUE"


class TestPatientLifecycleTransitions:
    """Tests for archive, restore, and state transitions."""

    def test_archive_active_patient_succeeds(self) -> None:
        """Archiving an active patient sets archived_at and marks inactive."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
        )
        assert patient.is_active() is True

        archive_time = datetime(2026, 11, 2, 10, 30, tzinfo=UTC)
        patient.archive(at=archive_time)

        assert patient.is_active() is False
        assert patient.archived_at == archive_time

    def test_archive_already_archived_raises_invalid_transition(self) -> None:
        """Archiving an already-archived patient raises InvalidTransitionError."""
        archive_time = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
            archived_at=archive_time,
        )

        with pytest.raises(InvalidTransitionError) as exc_info:
            patient.archive(at=datetime(2026, 11, 2, 11, 0, tzinfo=UTC))

        assert exc_info.value.code == "INVALID_TRANSITION"
        assert exc_info.value.message_key == "patient.already_archived"
        assert str(patient.id) in exc_info.value.safe_details["patient_id"]

    def test_archive_rejects_naive_timestamp(self) -> None:
        """Passing a naive datetime to archive raises ValidationError."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
        )
        with pytest.raises(ValidationError):
            patient.archive(at=datetime(2026, 11, 2, 10, 0))

    def test_archive_rejects_non_utc_timestamp(self) -> None:
        """Passing a non-zero UTC offset timestamp to archive raises ValidationError."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
        )
        non_utc = datetime(2026, 11, 2, 10, 0, tzinfo=timezone(timedelta(hours=2)))
        with pytest.raises(ValidationError):
            patient.archive(at=non_utc)

    def test_restore_archived_patient_succeeds(self) -> None:
        """Restoring an archived patient resets archived_at and marks active."""
        archive_time = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
            archived_at=archive_time,
        )
        assert patient.is_active() is False

        patient.restore()

        assert patient.is_active() is True
        assert patient.archived_at is None

    def test_restore_active_patient_raises_invalid_transition(self) -> None:
        """Restoring an already-active patient raises InvalidTransitionError."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
        )
        assert patient.is_active() is True

        with pytest.raises(InvalidTransitionError) as exc_info:
            patient.restore()

        assert exc_info.value.code == "INVALID_TRANSITION"
        assert exc_info.value.message_key == "patient.not_archived"
        assert str(patient.id) in exc_info.value.safe_details["patient_id"]

    def test_repeated_archive_and_restore_cycle(self) -> None:
        """Patient can undergo multiple valid archive and restore cycles."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
        )

        t1 = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)
        t2 = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)

        # First cycle
        patient.archive(at=t1)
        assert patient.is_active() is False
        assert patient.archived_at == t1

        patient.restore()
        assert patient.is_active() is True
        assert patient.archived_at is None

        # Second cycle
        patient.archive(at=t2)
        assert patient.is_active() is False
        assert patient.archived_at == t2

        patient.restore()
        assert patient.is_active() is True
        assert patient.archived_at is None


class TestPatientEntityIdentity:
    """Tests verifying M1 Entity identity behavior for Patient."""

    def test_same_id_equals_regardless_of_attributes(self) -> None:
        """Two Patient instances with same id evaluate equal (M1 Entity contract)."""
        pid = uuid4()
        cid1 = uuid4()
        cid2 = uuid4()

        p1 = Patient(id=pid, clinic_id=cid1, person_id=uuid4(), patient_number="PAT-001")
        p2 = Patient(id=pid, clinic_id=cid2, person_id=uuid4(), patient_number="PAT-999")

        assert p1 == p2
        assert p1.same_identity(p2) is True

    def test_different_id_not_equal(self) -> None:
        """Two Patient instances with different ids evaluate unequal."""
        cid = uuid4()
        person_id = uuid4()

        p1 = Patient(id=uuid4(), clinic_id=cid, person_id=person_id, patient_number="PAT-001")
        p2 = Patient(id=uuid4(), clinic_id=cid, person_id=person_id, patient_number="PAT-001")

        assert p1 != p2

    def test_patient_hash_disabled(self) -> None:
        """Patient entities cannot be hashed (M1 Entity contract)."""
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            patient_number="PAT-001",
        )
        with pytest.raises(TypeError, match="unhashable"):
            hash(patient)

