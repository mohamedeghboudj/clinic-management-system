"""Unit tests for the DoctorProfile domain entity."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from clinic_management.domain.people.doctor_profile import DoctorProfile
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError


class TestDoctorProfileConstruction:
    """Tests for DoctorProfile entity construction and field validation."""

    def test_valid_default_active_doctor_profile(self) -> None:
        """DoctorProfile constructed with default active=True."""
        doc_id = uuid4()
        cid = uuid4()
        staff_id = uuid4()

        doctor = DoctorProfile(
            id=doc_id,
            clinic_id=cid,
            staff_id=staff_id,
            specialty="Cardiology",
            licence_number="MED-12345",
        )

        assert doctor.id == doc_id
        assert doctor.version == 0
        assert doctor.clinic_id == cid
        assert doctor.staff_id == staff_id
        assert doctor.specialty == "Cardiology"
        assert doctor.licence_number == "MED-12345"
        assert doctor.active is True

    def test_valid_explicit_inactive_doctor_profile(self) -> None:
        """DoctorProfile constructed with active=False."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="  General Practice  ",
            licence_number="  LIC-999  ",
            active=False,
        )

        assert doctor.specialty == "General Practice"
        assert doctor.licence_number == "LIC-999"
        assert doctor.active is False

    @pytest.mark.parametrize(
        ("field_name", "kwargs"),
        [
            ("id", {"id": "invalid-uuid"}),
            ("clinic_id", {"clinic_id": 12345}),
            ("staff_id", {"staff_id": None}),
        ],
    )
    def test_invalid_identifiers_raise_validation_error(
        self, field_name: str, kwargs: dict[str, object]
    ) -> None:
        """Non-UUID identifiers raise ValidationError."""
        base: dict[str, object] = {
            "id": uuid4(),
            "clinic_id": uuid4(),
            "staff_id": uuid4(),
            "specialty": "Pediatrics",
            "licence_number": "LIC-001",
        }
        base.update(kwargs)
        with pytest.raises(ValidationError):
            DoctorProfile(**base)  # type: ignore[arg-type]

    @pytest.mark.parametrize("invalid_version", [-1, -5, 1.5, "0", True])
    def test_invalid_version_raises_validation_error(self, invalid_version: object) -> None:
        """Invalid version integers raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DoctorProfile(
                id=uuid4(),
                version=invalid_version,  # type: ignore[arg-type]
                clinic_id=uuid4(),
                staff_id=uuid4(),
                specialty="Pediatrics",
                licence_number="LIC-001",
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "version"

    @pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
    def test_empty_or_whitespace_specialty_rejected(self, empty_val: str) -> None:
        """Empty or whitespace specialty raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DoctorProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                staff_id=uuid4(),
                specialty=empty_val,
                licence_number="LIC-001",
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "specialty"

    def test_specialty_too_long_rejected(self) -> None:
        """Specialty exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DoctorProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                staff_id=uuid4(),
                specialty="S" * 101,
                licence_number="LIC-001",
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "specialty"

    @pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
    def test_empty_or_whitespace_licence_number_rejected(self, empty_val: str) -> None:
        """Empty or whitespace licence_number raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DoctorProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                staff_id=uuid4(),
                specialty="Dermatology",
                licence_number=empty_val,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "licence_number"

    def test_licence_number_too_long_rejected(self) -> None:
        """Licence number exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DoctorProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                staff_id=uuid4(),
                specialty="Dermatology",
                licence_number="L" * 51,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "licence_number"

    @pytest.mark.parametrize("invalid_active", [None, 1, 0, "True", "False"])
    def test_invalid_active_type_rejected(self, invalid_active: object) -> None:
        """Non-bool active values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DoctorProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                staff_id=uuid4(),
                specialty="Cardiology",
                licence_number="LIC-001",
                active=invalid_active,  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "active"


class TestDoctorProfileTransitions:
    """Tests for DoctorProfile activation and deactivation transitions."""

    def test_deactivate_active_doctor_profile(self) -> None:
        """Active doctor profile deactivates successfully."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Cardiology",
            licence_number="LIC-001",
            active=True,
        )
        doctor.deactivate()
        assert doctor.active is False

    def test_deactivate_inactive_doctor_profile_raises_invalid_transition(self) -> None:
        """Deactivating an already inactive doctor profile raises InvalidTransitionError."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Cardiology",
            licence_number="LIC-001",
            active=False,
        )
        with pytest.raises(InvalidTransitionError) as exc_info:
            doctor.deactivate()
        assert exc_info.value.code == "INVALID_TRANSITION"
        assert exc_info.value.message_key == "doctor.already_inactive"
        assert str(doctor.id) in exc_info.value.safe_details["doctor_id"]

    def test_activate_inactive_doctor_profile(self) -> None:
        """Inactive doctor profile activates successfully."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Cardiology",
            licence_number="LIC-001",
            active=False,
        )
        doctor.activate()
        assert doctor.active is True

    def test_activate_active_doctor_profile_raises_invalid_transition(self) -> None:
        """Activating an already active doctor profile raises InvalidTransitionError."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Cardiology",
            licence_number="LIC-001",
            active=True,
        )
        with pytest.raises(InvalidTransitionError) as exc_info:
            doctor.activate()
        assert exc_info.value.code == "INVALID_TRANSITION"
        assert exc_info.value.message_key == "doctor.already_active"
        assert str(doctor.id) in exc_info.value.safe_details["doctor_id"]

    def test_repeated_activate_deactivate_cycles(self) -> None:
        """Doctor profile can cycle between active and inactive states."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Cardiology",
            licence_number="LIC-001",
        )
        assert doctor.active is True

        doctor.deactivate()
        assert doctor.active is False

        doctor.activate()
        assert doctor.active is True

        doctor.deactivate()
        assert doctor.active is False


class TestDoctorProfileEntityIdentity:
    """Tests verifying M1 Entity identity behavior for DoctorProfile."""

    def test_same_id_equals_regardless_of_attributes(self) -> None:
        """Two DoctorProfile instances with same id evaluate equal (M1 Entity contract)."""
        doc_id = uuid4()
        d1 = DoctorProfile(
            id=doc_id,
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Neurology",
            licence_number="LIC-1",
            active=True,
        )
        d2 = DoctorProfile(
            id=doc_id,
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Pediatrics",
            licence_number="LIC-2",
            active=False,
        )
        assert d1 == d2
        assert d1.same_identity(d2) is True

    def test_different_id_not_equal(self) -> None:
        """Two DoctorProfile instances with different ids evaluate unequal."""
        cid = uuid4()
        sid = uuid4()
        d1 = DoctorProfile(
            id=uuid4(),
            clinic_id=cid,
            staff_id=sid,
            specialty="Neurology",
            licence_number="LIC-1",
        )
        d2 = DoctorProfile(
            id=uuid4(),
            clinic_id=cid,
            staff_id=sid,
            specialty="Neurology",
            licence_number="LIC-1",
        )
        assert d1 != d2

    def test_doctor_profile_hash_disabled(self) -> None:
        """DoctorProfile entities cannot be hashed (M1 Entity contract)."""
        doctor = DoctorProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            staff_id=uuid4(),
            specialty="Neurology",
            licence_number="LIC-1",
        )
        with pytest.raises(TypeError, match="unhashable"):
            hash(doctor)

