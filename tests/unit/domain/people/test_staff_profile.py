"""Unit tests for the StaffProfile domain entity."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest

from clinic_management.domain.people.staff_profile import StaffProfile
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError


class TestStaffProfileConstruction:
    """Tests for StaffProfile entity construction and field validation."""

    def test_valid_default_active_staff_profile(self) -> None:
        """StaffProfile constructed with default active=True."""
        sid = uuid4()
        cid = uuid4()
        pid = uuid4()
        hired = date(2024, 3, 1)

        profile = StaffProfile(
            id=sid,
            clinic_id=cid,
            person_id=pid,
            staff_number="STF-001",
            hired_on=hired,
        )

        assert profile.id == sid
        assert profile.version == 0
        assert profile.clinic_id == cid
        assert profile.person_id == pid
        assert profile.staff_number == "STF-001"
        assert profile.hired_on == hired
        assert profile.active is True

    def test_valid_explicit_inactive_staff_profile(self) -> None:
        """StaffProfile constructed with active=False."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="  STF-002  ",
            hired_on=date(2023, 1, 15),
            active=False,
        )

        assert profile.staff_number == "STF-002"
        assert profile.active is False

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
            "staff_number": "STF-001",
            "hired_on": date(2025, 1, 1),
        }
        base.update(kwargs)
        with pytest.raises(ValidationError):
            StaffProfile(**base)  # type: ignore[arg-type]

    @pytest.mark.parametrize("invalid_version", [-1, -50, 1.5, "0", True])
    def test_invalid_version_raises_validation_error(self, invalid_version: object) -> None:
        """Invalid version integers raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StaffProfile(
                id=uuid4(),
                version=invalid_version,  # type: ignore[arg-type]
                clinic_id=uuid4(),
                person_id=uuid4(),
                staff_number="STF-001",
                hired_on=date(2025, 1, 1),
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "version"

    @pytest.mark.parametrize("empty_num", ["", "   ", "\t\n"])
    def test_empty_or_whitespace_staff_number_rejected(self, empty_num: str) -> None:
        """Empty or whitespace staff number raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StaffProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                staff_number=empty_num,
                hired_on=date(2025, 1, 1),
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "staff_number"

    def test_staff_number_too_long_rejected(self) -> None:
        """Staff number exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StaffProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                staff_number="X" * 51,
                hired_on=date(2025, 1, 1),
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "staff_number"

    @pytest.mark.parametrize("invalid_hired", ["2025-01-01", 20250101, True, False, None])
    def test_invalid_hired_on_type_rejected(self, invalid_hired: object) -> None:
        """Non-date hired_on values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StaffProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                staff_number="STF-001",
                hired_on=invalid_hired,  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "hired_on"

    @pytest.mark.parametrize("invalid_active", [None, 1, 0, "True", "False"])
    def test_invalid_active_type_rejected(self, invalid_active: object) -> None:
        """Non-bool active values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StaffProfile(
                id=uuid4(),
                clinic_id=uuid4(),
                person_id=uuid4(),
                staff_number="STF-001",
                hired_on=date(2025, 1, 1),
                active=invalid_active,  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "active"


class TestStaffProfileTransitions:
    """Tests for StaffProfile activation and deactivation transitions."""

    def test_deactivate_active_staff_profile(self) -> None:
        """Active staff profile deactivates successfully."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
            active=True,
        )
        profile.deactivate()
        assert profile.active is False

    def test_deactivate_inactive_staff_profile_raises_invalid_transition(self) -> None:
        """Deactivating an already inactive staff profile raises InvalidTransitionError."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
            active=False,
        )
        with pytest.raises(InvalidTransitionError) as exc_info:
            profile.deactivate()
        assert exc_info.value.code == "INVALID_TRANSITION"
        assert exc_info.value.message_key == "staff.already_inactive"
        assert str(profile.id) in exc_info.value.safe_details["staff_id"]

    def test_activate_inactive_staff_profile(self) -> None:
        """Inactive staff profile activates successfully."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
            active=False,
        )
        profile.activate()
        assert profile.active is True

    def test_activate_active_staff_profile_raises_invalid_transition(self) -> None:
        """Activating an already active staff profile raises InvalidTransitionError."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
            active=True,
        )
        with pytest.raises(InvalidTransitionError) as exc_info:
            profile.activate()
        assert exc_info.value.code == "INVALID_TRANSITION"
        assert exc_info.value.message_key == "staff.already_active"
        assert str(profile.id) in exc_info.value.safe_details["staff_id"]

    def test_repeated_activate_deactivate_cycles(self) -> None:
        """Staff profile can cycle between active and inactive states."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
        )
        assert profile.active is True

        profile.deactivate()
        assert profile.active is False

        profile.activate()
        assert profile.active is True

        profile.deactivate()
        assert profile.active is False


class TestStaffProfileEntityIdentity:
    """Tests verifying M1 Entity identity behavior for StaffProfile."""

    def test_same_id_equals_regardless_of_attributes(self) -> None:
        """Two StaffProfile instances with same id evaluate equal (M1 Entity contract)."""
        sid = uuid4()
        p1 = StaffProfile(
            id=sid,
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
            active=True,
        )
        p2 = StaffProfile(
            id=sid,
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-999",
            hired_on=date(2020, 1, 1),
            active=False,
        )
        assert p1 == p2
        assert p1.same_identity(p2) is True

    def test_different_id_not_equal(self) -> None:
        """Two StaffProfile instances with different ids evaluate unequal."""
        cid = uuid4()
        pid = uuid4()
        p1 = StaffProfile(
            id=uuid4(),
            clinic_id=cid,
            person_id=pid,
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
        )
        p2 = StaffProfile(
            id=uuid4(),
            clinic_id=cid,
            person_id=pid,
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
        )
        assert p1 != p2

    def test_staff_profile_hash_disabled(self) -> None:
        """StaffProfile entities cannot be hashed (M1 Entity contract)."""
        profile = StaffProfile(
            id=uuid4(),
            clinic_id=uuid4(),
            person_id=uuid4(),
            staff_number="STF-001",
            hired_on=date(2025, 1, 1),
        )
        with pytest.raises(TypeError, match="unhashable"):
            hash(profile)

