"""Unit tests for AccessPolicy — authorization enforcement."""

from __future__ import annotations

from uuid import uuid4

import pytest

from clinic_management.domain.access.enums import AccessScope, Permission, Role
from clinic_management.domain.access.grants import RoleGrant
from clinic_management.domain.access.policy import AccessPolicy, ResourceContext
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.shared.errors import PermissionDeniedError, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_grant(
    role: Role = Role.DOCTOR,
    permission: Permission = Permission.PATIENT_READ,
    scope: AccessScope = AccessScope.CLINIC,
    fields: frozenset[str] | None = None,
) -> RoleGrant:
    return RoleGrant(
        role=role,
        permission=permission,
        scope=scope,
        fields=fields if fields is not None else frozenset({"name", "dob"}),
    )


def _make_principal(
    clinic_id=None,
    roles=None,
    staff_id=None,
    patient_id=None,
    auth_version=1,
) -> Principal:
    if clinic_id is None:
        clinic_id = uuid4()
    return Principal(
        account_id=uuid4(),
        clinic_id=clinic_id,
        membership_id=uuid4(),
        staff_id=staff_id,
        patient_id=patient_id,
        roles=roles if roles is not None else frozenset({Role.DOCTOR}),
        auth_version=auth_version,
    )


def _make_resource(
    clinic_id=None,
    patient_id=None,
    assigned_staff_ids=None,
    available_fields=None,
) -> ResourceContext:
    if clinic_id is None:
        clinic_id = uuid4()
    return ResourceContext(
        clinic_id=clinic_id,
        patient_id=patient_id,
        assigned_staff_ids=assigned_staff_ids or frozenset(),
        available_fields=available_fields if available_fields is not None else frozenset({"name", "dob"}),
    )


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------

class TestAccessPolicyConstruction:
    """Tests for AccessPolicy construction validation."""

    def test_valid_empty_policy(self) -> None:
        """An AccessPolicy with no grants is valid (deny-all)."""
        policy = AccessPolicy(grants=())
        assert policy.grants == ()

    def test_valid_policy_with_grants(self) -> None:
        """An AccessPolicy with grants is constructed successfully."""
        policy = AccessPolicy(grants=(_make_grant(),))
        assert len(policy.grants) == 1

    def test_non_tuple_grants_raises(self) -> None:
        """Passing a list for grants is rejected."""
        with pytest.raises(ValidationError):
            AccessPolicy(grants=[_make_grant()])  # type: ignore[arg-type]

    def test_non_role_grant_in_grants_raises(self) -> None:
        """Passing a non-RoleGrant item in grants tuple is rejected."""
        with pytest.raises(ValidationError):
            AccessPolicy(grants=("not_a_grant",))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# require() tests — positive (allowed)
# ---------------------------------------------------------------------------

class TestAccessPolicyRequireAllowed:
    """Tests for AccessPolicy.require() — cases that should be permitted."""

    def test_clinic_scope_grant_permits(self) -> None:
        """A CLINIC-scope grant permits access within the same clinic."""
        clinic_id = uuid4()
        policy = AccessPolicy(grants=(_make_grant(scope=AccessScope.CLINIC),))
        principal = _make_principal(clinic_id=clinic_id)
        resource = _make_resource(clinic_id=clinic_id)
        policy.require(principal, Permission.PATIENT_READ, resource)  # no exception

    def test_assigned_scope_grant_permits_assigned_staff(self) -> None:
        """An ASSIGNED-scope grant permits access when staff is in assigned_staff_ids."""
        clinic_id = uuid4()
        staff_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(scope=AccessScope.ASSIGNED),)
        )
        principal = _make_principal(clinic_id=clinic_id, staff_id=staff_id)
        resource = _make_resource(
            clinic_id=clinic_id,
            assigned_staff_ids=frozenset({staff_id}),
        )
        policy.require(principal, Permission.PATIENT_READ, resource)

    def test_own_scope_grant_permits_matching_patient(self) -> None:
        """An OWN-scope grant permits access when patient_id matches."""
        clinic_id = uuid4()
        patient_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(scope=AccessScope.OWN),)
        )
        principal = _make_principal(
            clinic_id=clinic_id, patient_id=patient_id
        )
        resource = _make_resource(clinic_id=clinic_id, patient_id=patient_id)
        policy.require(principal, Permission.PATIENT_READ, resource)

    def test_owner_role_with_explicit_grant_is_permitted(self) -> None:
        """OWNER with an explicit grant is authorised (no automatic bypass)."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(role=Role.OWNER, permission=Permission.CLINICAL_READ),)
        )
        principal = _make_principal(clinic_id=clinic_id, roles=frozenset({Role.OWNER}))
        resource = _make_resource(clinic_id=clinic_id)
        policy.require(principal, Permission.CLINICAL_READ, resource)


# ---------------------------------------------------------------------------
# require() tests — negative (denied)
# ---------------------------------------------------------------------------

class TestAccessPolicyRequireDenied:
    """Tests for AccessPolicy.require() — cases that must be denied."""

    def test_empty_policy_denies_all(self) -> None:
        """A policy with no grants denies every request."""
        policy = AccessPolicy(grants=())
        principal = _make_principal()
        resource = _make_resource(clinic_id=principal.clinic_id)
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_READ, resource)

    def test_wrong_clinic_is_denied(self) -> None:
        """Cross-clinic access is denied even with a matching grant."""
        clinic_a = uuid4()
        clinic_b = uuid4()
        policy = AccessPolicy(grants=(_make_grant(scope=AccessScope.CLINIC),))
        principal = _make_principal(clinic_id=clinic_a)
        resource = _make_resource(clinic_id=clinic_b)
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_READ, resource)

    def test_wrong_permission_is_denied(self) -> None:
        """Requesting PATIENT_WRITE when only PATIENT_READ is granted is denied."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(permission=Permission.PATIENT_READ),)
        )
        principal = _make_principal(clinic_id=clinic_id)
        resource = _make_resource(clinic_id=clinic_id)
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_WRITE, resource)

    def test_wrong_role_is_denied(self) -> None:
        """Principal with NURSE role denied when only DOCTOR role has grant."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(role=Role.DOCTOR),)
        )
        principal = _make_principal(clinic_id=clinic_id, roles=frozenset({Role.NURSE}))
        resource = _make_resource(clinic_id=clinic_id)
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_READ, resource)

    def test_assigned_scope_denied_when_not_assigned(self) -> None:
        """ASSIGNED-scope grant denied when staff is not in assigned_staff_ids."""
        clinic_id = uuid4()
        staff_id = uuid4()
        other_staff_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(scope=AccessScope.ASSIGNED),)
        )
        principal = _make_principal(clinic_id=clinic_id, staff_id=staff_id)
        resource = _make_resource(
            clinic_id=clinic_id,
            assigned_staff_ids=frozenset({other_staff_id}),
        )
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_READ, resource)

    def test_own_scope_denied_when_patient_id_mismatches(self) -> None:
        """OWN-scope grant denied when patient_id does not match."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(scope=AccessScope.OWN),)
        )
        principal = _make_principal(clinic_id=clinic_id, patient_id=uuid4())
        resource = _make_resource(clinic_id=clinic_id, patient_id=uuid4())
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_READ, resource)

    def test_owner_without_explicit_clinical_grant_is_denied(self) -> None:
        """OWNER role without an explicit clinical grant is denied — no automatic bypass."""
        clinic_id = uuid4()
        policy = AccessPolicy(grants=())  # no clinical grants
        principal = _make_principal(clinic_id=clinic_id, roles=frozenset({Role.OWNER}))
        resource = _make_resource(clinic_id=clinic_id)
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.CLINICAL_READ, resource)

    def test_assigned_scope_denied_when_staff_id_is_none(self) -> None:
        """ASSIGNED-scope denied when the principal has no staff_id."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(scope=AccessScope.ASSIGNED),)
        )
        principal = _make_principal(clinic_id=clinic_id, staff_id=None)
        resource = _make_resource(
            clinic_id=clinic_id, assigned_staff_ids=frozenset({uuid4()})
        )
        with pytest.raises(PermissionDeniedError):
            policy.require(principal, Permission.PATIENT_READ, resource)


# ---------------------------------------------------------------------------
# allowed_fields() tests
# ---------------------------------------------------------------------------

class TestAccessPolicyAllowedFields:
    """Tests for AccessPolicy.allowed_fields()."""

    def test_returns_intersection_of_grant_and_available_fields(self) -> None:
        """Only fields both authorised and available are returned."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(
                _make_grant(fields=frozenset({"name", "dob", "phone"})),
            )
        )
        principal = _make_principal(clinic_id=clinic_id)
        resource = _make_resource(
            clinic_id=clinic_id,
            available_fields=frozenset({"name", "dob"}),  # phone not available
        )
        fields = policy.allowed_fields(principal, Permission.PATIENT_READ, resource)
        assert fields == frozenset({"name", "dob"})

    def test_empty_grant_fields_returns_empty(self) -> None:
        """A grant with empty fields returns no authorised fields."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(fields=frozenset()),)
        )
        principal = _make_principal(clinic_id=clinic_id)
        resource = _make_resource(clinic_id=clinic_id)
        fields = policy.allowed_fields(principal, Permission.PATIENT_READ, resource)
        assert fields == frozenset()

    def test_unmatched_grant_returns_empty_fields(self) -> None:
        """When no grant matches, no fields are returned."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(permission=Permission.PATIENT_WRITE),)
        )
        principal = _make_principal(clinic_id=clinic_id)
        resource = _make_resource(clinic_id=clinic_id)
        fields = policy.allowed_fields(principal, Permission.PATIENT_READ, resource)
        assert fields == frozenset()

    def test_multiple_grants_union_fields(self) -> None:
        """Fields from multiple matching grants are unioned, then intersected with available."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(
                _make_grant(role=Role.DOCTOR, fields=frozenset({"name"})),
                _make_grant(role=Role.NURSE, fields=frozenset({"dob"})),
            )
        )
        principal = _make_principal(
            clinic_id=clinic_id,
            roles=frozenset({Role.DOCTOR, Role.NURSE}),
        )
        resource = _make_resource(
            clinic_id=clinic_id,
            available_fields=frozenset({"name", "dob"}),
        )
        fields = policy.allowed_fields(principal, Permission.PATIENT_READ, resource)
        assert fields == frozenset({"name", "dob"})

    def test_fields_not_in_available_are_excluded(self) -> None:
        """Fields authorised by grant but absent from available_fields are excluded."""
        clinic_id = uuid4()
        policy = AccessPolicy(
            grants=(_make_grant(fields=frozenset({"name", "ssn"})),)
        )
        principal = _make_principal(clinic_id=clinic_id)
        resource = _make_resource(
            clinic_id=clinic_id,
            available_fields=frozenset({"name"}),
        )
        fields = policy.allowed_fields(principal, Permission.PATIENT_READ, resource)
        assert "ssn" not in fields
        assert "name" in fields

