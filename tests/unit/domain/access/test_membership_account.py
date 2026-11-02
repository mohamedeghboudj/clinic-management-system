"""Unit tests for ClinicMembership and UserAccount domain entities."""

from __future__ import annotations

from uuid import uuid4

import pytest

from clinic_management.domain.access.account import UserAccount
from clinic_management.domain.access.enums import Role
from clinic_management.domain.access.membership import ClinicMembership
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_membership(**kwargs) -> ClinicMembership:
    defaults = dict(
        id=uuid4(),
        account_id=uuid4(),
        clinic_id=uuid4(),
    )
    defaults.update(kwargs)
    return ClinicMembership(**defaults)


def _make_account(**kwargs) -> UserAccount:
    defaults = dict(
        id=uuid4(),
        person_id=uuid4(),
        username="drsmith",
        password_hash="$argon2id$v=19$m=65536,t=3,p=1$abc$xyz",
    )
    defaults.update(kwargs)
    return UserAccount(**defaults)


# ---------------------------------------------------------------------------
# ClinicMembership tests
# ---------------------------------------------------------------------------


class TestClinicMembershipConstruction:
    """Tests for ClinicMembership construction and validation."""

    def test_valid_minimal_membership(self) -> None:
        """Membership with required fields only is valid."""
        m = _make_membership()
        assert m.version == 0
        assert m.active is True
        assert m.roles == frozenset()
        assert m.staff_id is None
        assert m.patient_id is None

    def test_membership_with_staff_and_roles(self) -> None:
        """Membership with staff_id and initial roles is valid."""
        m = _make_membership(
            staff_id=uuid4(),
            roles=frozenset({Role.DOCTOR, Role.NURSE}),
        )
        assert Role.DOCTOR in m.roles
        assert Role.NURSE in m.roles

    def test_membership_with_patient_id(self) -> None:
        """Patient membership carries a patient_id."""
        m = _make_membership(patient_id=uuid4())
        assert m.patient_id is not None

    def test_invalid_version_raises(self) -> None:
        """Negative version is rejected."""
        with pytest.raises(ValidationError):
            _make_membership(version=-1)

    def test_non_int_version_raises(self) -> None:
        """Float version is rejected."""
        with pytest.raises(ValidationError):
            _make_membership(version=1.0)  # type: ignore[arg-type]

    def test_non_uuid_account_id_raises(self) -> None:
        """String account_id is rejected."""
        with pytest.raises(ValidationError):
            _make_membership(account_id="not-a-uuid")  # type: ignore[arg-type]

    def test_non_bool_active_raises(self) -> None:
        """Integer 1 used for active is rejected."""
        with pytest.raises(ValidationError):
            _make_membership(active=1)  # type: ignore[arg-type]

    def test_roles_with_non_role_member_raises(self) -> None:
        """Passing a string in roles is rejected."""
        with pytest.raises(ValidationError):
            _make_membership(roles=frozenset({"DOCTOR"}))  # type: ignore[arg-type]

    def test_roles_as_list_raises(self) -> None:
        """Passing a list instead of frozenset for roles is rejected."""
        with pytest.raises(ValidationError):
            _make_membership(roles=[Role.DOCTOR])  # type: ignore[arg-type]


class TestClinicMembershipGrantRevoke:
    """Tests for role grant and revoke on ClinicMembership."""

    def test_grant_role_adds_to_roles(self) -> None:
        """Granting a role adds it to the frozenset."""
        m = _make_membership()
        m.grant_role(Role.MANAGER)
        assert Role.MANAGER in m.roles

    def test_grant_role_twice_is_idempotent(self) -> None:
        """Granting the same role twice results in one copy."""
        m = _make_membership()
        m.grant_role(Role.DOCTOR)
        m.grant_role(Role.DOCTOR)
        assert m.roles.count(Role.DOCTOR) if hasattr(m.roles, "count") else Role.DOCTOR in m.roles
        assert len([r for r in m.roles if r is Role.DOCTOR]) == 1

    def test_revoke_role_removes_it(self) -> None:
        """Revoking an existing role removes it."""
        m = _make_membership(roles=frozenset({Role.NURSE}))
        m.revoke_role(Role.NURSE)
        assert Role.NURSE not in m.roles

    def test_revoke_absent_role_is_no_op(self) -> None:
        """Revoking a role not in the set leaves the set unchanged."""
        m = _make_membership()
        m.revoke_role(Role.OWNER)
        assert m.roles == frozenset()

    def test_grant_invalid_value_raises(self) -> None:
        """Granting a non-Role value raises ValidationError."""
        m = _make_membership()
        with pytest.raises(ValidationError):
            m.grant_role("OWNER")  # type: ignore[arg-type]

    def test_revoke_invalid_value_raises(self) -> None:
        """Revoking a non-Role value raises ValidationError."""
        m = _make_membership()
        with pytest.raises(ValidationError):
            m.revoke_role(42)  # type: ignore[arg-type]


class TestClinicMembershipDeactivate:
    """Tests for ClinicMembership.deactivate."""

    def test_deactivate_active_membership(self) -> None:
        """Deactivating an active membership sets active to False."""
        m = _make_membership()
        m.deactivate()
        assert m.active is False

    def test_deactivate_already_inactive_raises(self) -> None:
        """Deactivating an already inactive membership raises InvalidTransitionError."""
        m = _make_membership(active=False)
        with pytest.raises(InvalidTransitionError):
            m.deactivate()


# ---------------------------------------------------------------------------
# UserAccount tests
# ---------------------------------------------------------------------------


class TestUserAccountConstruction:
    """Tests for UserAccount entity construction and validation."""

    def test_valid_account_construction(self) -> None:
        """A UserAccount with all valid fields is constructed successfully."""
        acct = _make_account()
        assert acct.enabled is True
        assert acct.auth_version == 1
        assert acct.must_change_password is False
        assert acct.version == 0

    def test_username_is_stripped(self) -> None:
        """Leading/trailing whitespace in username is stripped."""
        acct = _make_account(username="  drsmith  ")
        assert acct.username == "drsmith"

    def test_empty_username_raises(self) -> None:
        """Empty username is rejected."""
        with pytest.raises(ValidationError):
            _make_account(username="")

    def test_empty_hash_raises(self) -> None:
        """Empty password_hash is rejected."""
        with pytest.raises(ValidationError):
            _make_account(password_hash="")

    def test_negative_version_raises(self) -> None:
        """Negative version raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_account(version=-1)

    def test_auth_version_zero_raises(self) -> None:
        """auth_version of 0 is rejected (must be >= 1)."""
        with pytest.raises(ValidationError):
            _make_account(auth_version=0)

    def test_non_bool_enabled_raises(self) -> None:
        """Integer used for enabled is rejected."""
        with pytest.raises(ValidationError):
            _make_account(enabled=1)  # type: ignore[arg-type]

    def test_password_hash_not_in_repr(self) -> None:
        """The password_hash must not appear in the repr."""
        acct = _make_account(password_hash="$argon2id$supersecret")
        r = repr(acct)
        assert "supersecret" not in r
        assert "password_hash" not in r


class TestUserAccountDisableEnable:
    """Tests for UserAccount.disable and enable transitions."""

    def test_disable_enabled_account(self) -> None:
        """Disabling an enabled account sets enabled to False and bumps auth_version."""
        acct = _make_account()
        old_version = acct.auth_version
        acct.disable()
        assert acct.enabled is False
        assert acct.auth_version == old_version + 1

    def test_disable_already_disabled_raises(self) -> None:
        """Disabling an already disabled account raises InvalidTransitionError."""
        acct = _make_account(enabled=False)
        with pytest.raises(InvalidTransitionError):
            acct.disable()

    def test_enable_disabled_account(self) -> None:
        """Enabling a disabled account sets enabled to True."""
        acct = _make_account(enabled=False)
        acct.enable()
        assert acct.enabled is True

    def test_enable_already_enabled_raises(self) -> None:
        """Enabling an already enabled account raises InvalidTransitionError."""
        acct = _make_account()
        with pytest.raises(InvalidTransitionError):
            acct.enable()


class TestUserAccountPasswordAndSession:
    """Tests for password hash replacement and session invalidation."""

    def test_replace_password_hash_changes_hash_and_bumps_version(self) -> None:
        """Replacing the password hash stores new hash and increments auth_version."""
        acct = _make_account()
        old_version = acct.auth_version
        acct.replace_password_hash("$argon2id$newhash")
        assert acct.password_hash == "$argon2id$newhash"
        assert acct.auth_version == old_version + 1

    def test_replace_password_hash_empty_raises(self) -> None:
        """Replacing with an empty hash raises ValidationError."""
        acct = _make_account()
        with pytest.raises(ValidationError):
            acct.replace_password_hash("")

    def test_invalidate_sessions_bumps_version(self) -> None:
        """invalidate_sessions increments auth_version."""
        acct = _make_account()
        v0 = acct.auth_version
        acct.invalidate_sessions()
        assert acct.auth_version == v0 + 1

    def test_multiple_invalidations_accumulate(self) -> None:
        """Each call to invalidate_sessions increments the version once."""
        acct = _make_account()
        v0 = acct.auth_version
        acct.invalidate_sessions()
        acct.invalidate_sessions()
        assert acct.auth_version == v0 + 2

    def test_disable_then_enable_version_incremented_once(self) -> None:
        """disable bumps auth_version; enable does not."""
        acct = _make_account()
        v0 = acct.auth_version
        acct.disable()
        assert acct.auth_version == v0 + 1
        acct.enable()
        assert acct.auth_version == v0 + 1

