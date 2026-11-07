"""Unit tests for Principal and ResourceContext."""

from __future__ import annotations

from uuid import uuid4

import pytest

from clinic_management.domain.access.enums import Role
from clinic_management.domain.access.policy import ResourceContext
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.shared.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_principal(**kwargs) -> Principal:
    defaults = dict(
        account_id=uuid4(),
        clinic_id=uuid4(),
        membership_id=uuid4(),
        staff_id=None,
        patient_id=None,
        roles=frozenset({Role.DOCTOR}),
        auth_version=1,
    )
    defaults.update(kwargs)
    return Principal(**defaults)


def _make_resource(clinic_id=None, **kwargs) -> ResourceContext:
    if clinic_id is None:
        clinic_id = uuid4()
    defaults = dict(
        clinic_id=clinic_id,
        patient_id=None,
        assigned_staff_ids=frozenset(),
        available_fields=frozenset({"name", "dob"}),
    )
    defaults.update(kwargs)
    return ResourceContext(**defaults)


# ---------------------------------------------------------------------------
# Principal tests
# ---------------------------------------------------------------------------


class TestPrincipalConstruction:
    """Tests for Principal value object construction."""

    def test_valid_principal_with_staff(self) -> None:
        """A principal with staff_id is constructed successfully."""
        p = _make_principal(staff_id=uuid4())
        assert p.staff_id is not None
        assert p.patient_id is None
        assert Role.DOCTOR in p.roles

    def test_valid_principal_with_patient(self) -> None:
        """A principal with patient_id is constructed successfully."""
        p = _make_principal(patient_id=uuid4(), roles=frozenset())
        assert p.patient_id is not None

    def test_minimal_principal_no_staff_or_patient(self) -> None:
        """A principal with neither staff nor patient id is valid."""
        p = _make_principal()
        assert p.staff_id is None
        assert p.patient_id is None

    def test_principal_is_immutable(self) -> None:
        """Modifying a Principal attribute raises AttributeError."""
        p = _make_principal()
        with pytest.raises(AttributeError):
            p.roles = frozenset()  # type: ignore[misc]

    def test_invalid_auth_version_zero_raises(self) -> None:
        """auth_version of 0 is rejected."""
        with pytest.raises(ValidationError):
            _make_principal(auth_version=0)

    def test_invalid_auth_version_negative_raises(self) -> None:
        """Negative auth_version is rejected."""
        with pytest.raises(ValidationError):
            _make_principal(auth_version=-5)

    def test_non_uuid_account_id_raises(self) -> None:
        """String used as account_id is rejected."""
        with pytest.raises(ValidationError):
            _make_principal(account_id="not-a-uuid")  # type: ignore[arg-type]

    def test_non_role_in_roles_raises(self) -> None:
        """A string in the roles frozenset is rejected."""
        with pytest.raises(ValidationError):
            _make_principal(roles=frozenset({"DOCTOR"}))  # type: ignore[arg-type]

    def test_non_frozenset_roles_raises(self) -> None:
        """A list used for roles is rejected."""
        with pytest.raises(ValidationError):
            _make_principal(roles=[Role.DOCTOR])  # type: ignore[arg-type]

    def test_has_role_true(self) -> None:
        """has_role returns True for a role in the set."""
        p = _make_principal(roles=frozenset({Role.NURSE, Role.MANAGER}))
        assert p.has_role(Role.NURSE) is True
        assert p.has_role(Role.MANAGER) is True

    def test_has_role_false(self) -> None:
        """has_role returns False for a role not in the set."""
        p = _make_principal(roles=frozenset({Role.NURSE}))
        assert p.has_role(Role.OWNER) is False


# ---------------------------------------------------------------------------
# ResourceContext tests
# ---------------------------------------------------------------------------


class TestResourceContextConstruction:
    """Tests for ResourceContext value object construction."""

    def test_valid_minimal_resource_context(self) -> None:
        """ResourceContext with required fields is constructed successfully."""
        rc = _make_resource()
        assert rc.patient_id is None
        assert rc.assigned_staff_ids == frozenset()

    def test_resource_context_with_patient_and_staff(self) -> None:
        """ResourceContext with patient_id and assigned_staff_ids is valid."""
        staff_id = uuid4()
        rc = _make_resource(
            patient_id=uuid4(),
            assigned_staff_ids=frozenset({staff_id}),
        )
        assert staff_id in rc.assigned_staff_ids

    def test_resource_context_is_immutable(self) -> None:
        """Modifying a ResourceContext attribute raises AttributeError."""
        rc = _make_resource()
        with pytest.raises(AttributeError):
            rc.clinic_id = uuid4()  # type: ignore[misc]

    def test_non_uuid_clinic_id_raises(self) -> None:
        """String clinic_id is rejected."""
        with pytest.raises(ValidationError):
            ResourceContext(
                clinic_id="bad",  # type: ignore[arg-type]
                patient_id=None,
                assigned_staff_ids=frozenset(),
                available_fields=frozenset(),
            )

    def test_non_frozenset_assigned_staff_raises(self) -> None:
        """A list used for assigned_staff_ids is rejected."""
        with pytest.raises(ValidationError):
            ResourceContext(
                clinic_id=uuid4(),
                patient_id=None,
                assigned_staff_ids=[uuid4()],  # type: ignore[arg-type]
                available_fields=frozenset(),
            )

    def test_non_frozenset_available_fields_raises(self) -> None:
        """A list used for available_fields is rejected."""
        with pytest.raises(ValidationError):
            ResourceContext(
                clinic_id=uuid4(),
                patient_id=None,
                assigned_staff_ids=frozenset(),
                available_fields=["name"],  # type: ignore[arg-type]
            )

