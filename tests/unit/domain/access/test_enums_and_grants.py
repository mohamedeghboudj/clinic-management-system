"""Unit tests for Role, Permission, AccessScope enums and RoleGrant value object."""

from __future__ import annotations

import pytest

from clinic_management.domain.access.enums import AccessScope, Permission, Role
from clinic_management.domain.access.grants import RoleGrant
from clinic_management.domain.shared.errors import ValidationError


class TestRoleEnum:
    """Tests for the Role enumeration."""

    def test_all_five_roles_exist(self) -> None:
        """All five documented roles must be present."""
        assert Role.OWNER
        assert Role.MANAGER
        assert Role.DOCTOR
        assert Role.NURSE
        assert Role.SECRETARY

    def test_role_has_string_value(self) -> None:
        """Role enum values are their string names."""
        assert Role.OWNER.value == "OWNER"
        assert Role.SECRETARY.value == "SECRETARY"

    def test_roles_are_comparable_by_identity(self) -> None:
        """Same role accessed twice is the same object."""
        assert Role.DOCTOR is Role.DOCTOR

    def test_role_count(self) -> None:
        """Exactly five roles are defined."""
        assert len(list(Role)) == 5


class TestPermissionEnum:
    """Tests for the Permission enumeration."""

    def test_all_fourteen_permissions_exist(self) -> None:
        """All fourteen documented permissions must be present."""
        expected = {
            "PATIENT_READ", "PATIENT_WRITE",
            "APPOINTMENT_READ", "APPOINTMENT_WRITE",
            "CLINICAL_READ", "CLINICAL_WRITE",
            "PRESCRIBE",
            "BILLING_READ", "BILLING_WRITE",
            "PAYMENT_RECORD", "PAYMENT_REVERSE",
            "FINANCE_REPORT",
            "STAFF_MANAGE",
            "ROLE_MANAGE",
        }
        actual = {p.value for p in Permission}
        assert actual == expected

    def test_permission_count(self) -> None:
        """Exactly fourteen permissions are defined."""
        assert len(list(Permission)) == 14

    def test_permission_has_string_value(self) -> None:
        """Permission enum values are their string names."""
        assert Permission.PATIENT_READ.value == "PATIENT_READ"
        assert Permission.ROLE_MANAGE.value == "ROLE_MANAGE"


class TestAccessScopeEnum:
    """Tests for the AccessScope enumeration."""

    def test_all_three_scopes_exist(self) -> None:
        """All three documented scopes must be present."""
        assert AccessScope.CLINIC
        assert AccessScope.ASSIGNED
        assert AccessScope.OWN

    def test_scope_count(self) -> None:
        """Exactly three scopes are defined."""
        assert len(list(AccessScope)) == 3


class TestRoleGrant:
    """Tests for the RoleGrant frozen value object."""

    def _make_grant(
        self,
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

    def test_valid_grant_construction(self) -> None:
        """A RoleGrant with valid fields is constructed successfully."""
        grant = self._make_grant()
        assert grant.role is Role.DOCTOR
        assert grant.permission is Permission.PATIENT_READ
        assert grant.scope is AccessScope.CLINIC
        assert "name" in grant.fields

    def test_grant_with_empty_fields(self) -> None:
        """An empty frozenset is valid — it means no fields are authorised."""
        grant = self._make_grant(fields=frozenset())
        assert grant.fields == frozenset()

    def test_grant_is_immutable(self) -> None:
        """Modifying a RoleGrant attribute raises AttributeError."""
        grant = self._make_grant()
        with pytest.raises(AttributeError):
            grant.role = Role.NURSE  # type: ignore[misc]

    def test_grant_equality(self) -> None:
        """Two grants with identical fields are equal."""
        g1 = self._make_grant()
        g2 = self._make_grant()
        assert g1 == g2

    def test_grant_different_roles_not_equal(self) -> None:
        """Grants with different roles are not equal."""
        g1 = self._make_grant(role=Role.DOCTOR)
        g2 = self._make_grant(role=Role.NURSE)
        assert g1 != g2

    def test_invalid_role_raises(self) -> None:
        """Non-Role values for role are rejected."""
        with pytest.raises(ValidationError):
            RoleGrant(
                role="DOCTOR",  # type: ignore[arg-type]
                permission=Permission.PATIENT_READ,
                scope=AccessScope.CLINIC,
                fields=frozenset(),
            )

    def test_invalid_permission_raises(self) -> None:
        """Non-Permission values for permission are rejected."""
        with pytest.raises(ValidationError):
            RoleGrant(
                role=Role.DOCTOR,
                permission="PATIENT_READ",  # type: ignore[arg-type]
                scope=AccessScope.CLINIC,
                fields=frozenset(),
            )

    def test_invalid_scope_raises(self) -> None:
        """Non-AccessScope values for scope are rejected."""
        with pytest.raises(ValidationError):
            RoleGrant(
                role=Role.DOCTOR,
                permission=Permission.PATIENT_READ,
                scope="CLINIC",  # type: ignore[arg-type]
                fields=frozenset(),
            )

    def test_non_frozenset_fields_raises(self) -> None:
        """Passing a list instead of frozenset for fields is rejected."""
        with pytest.raises(ValidationError):
            RoleGrant(
                role=Role.DOCTOR,
                permission=Permission.PATIENT_READ,
                scope=AccessScope.CLINIC,
                fields=["name"],  # type: ignore[arg-type]
            )

    def test_field_set_with_empty_string_raises(self) -> None:
        """An empty string in the fields set is rejected."""
        with pytest.raises(ValidationError):
            RoleGrant(
                role=Role.DOCTOR,
                permission=Permission.PATIENT_READ,
                scope=AccessScope.CLINIC,
                fields=frozenset({""}),
            )

    def test_grant_is_hashable(self) -> None:
        """RoleGrant instances can be used in sets and as dict keys."""
        grant = self._make_grant()
        s = {grant}
        assert grant in s

    def test_multiple_fields_in_grant(self) -> None:
        """A grant can carry multiple field names."""
        grant = self._make_grant(fields=frozenset({"name", "dob", "phone"}))
        assert len(grant.fields) == 3

