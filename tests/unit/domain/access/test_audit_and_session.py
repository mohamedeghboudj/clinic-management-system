"""Unit tests for AuditEntry and Session domain entities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from clinic_management.domain.access.audit import AuditEntry
from clinic_management.domain.access.session import Session
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audit(**kwargs) -> AuditEntry:
    defaults = dict(
        id=uuid4(),
        clinic_id=uuid4(),
        actor_id=uuid4(),
        action="PATIENT_ACCESSED",
        resource_type="Patient",
        resource_id=uuid4(),
        outcome="SUCCESS",
        occurred_at=datetime.now(UTC),
        correlation_id=uuid4(),
        reason_code=None,
    )
    defaults.update(kwargs)
    return AuditEntry(**defaults)


def _make_session(**kwargs) -> Session:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid4(),
        account_id=uuid4(),
        auth_version=1,
        refresh_token_hash="$argon2id$hashedrefreshtoken",
        created_at=now,
        expires_at=now + timedelta(days=7),
        revoked_at=None,
    )
    defaults.update(kwargs)
    return Session(**defaults)


# ---------------------------------------------------------------------------
# AuditEntry tests
# ---------------------------------------------------------------------------

class TestAuditEntryConstruction:
    """Tests for AuditEntry immutable record."""

    def test_valid_audit_entry_with_actor(self) -> None:
        """AuditEntry with actor and all fields valid."""
        audit = _make_audit(reason_code="ROUTINE_ACCESS")
        assert audit.action == "PATIENT_ACCESSED"
        assert audit.outcome == "SUCCESS"
        assert audit.reason_code == "ROUTINE_ACCESS"
        assert audit.actor_id is not None

    def test_valid_audit_entry_unknown_actor(self) -> None:
        """AuditEntry supports unknown actor for unauthenticated failures."""
        audit = _make_audit(actor_id=None, outcome="FAILURE", reason_code="INVALID_CREDENTIALS")
        assert audit.actor_id is None
        assert audit.outcome == "FAILURE"

    def test_audit_entry_is_immutable(self) -> None:
        """Modifying an AuditEntry attribute raises AttributeError."""
        audit = _make_audit()
        with pytest.raises(AttributeError):
            audit.action = "MODIFIED"  # type: ignore[misc]

    def test_naive_timestamp_raises(self) -> None:
        """Naive occurred_at raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_audit(occurred_at=datetime.now())

    def test_non_utc_timestamp_raises(self) -> None:
        """Non-zero UTC offset raises ValidationError."""
        tz_plus_2 = timezone(timedelta(hours=2))
        with pytest.raises(ValidationError):
            _make_audit(occurred_at=datetime.now(tz_plus_2))

    def test_empty_action_raises(self) -> None:
        """Empty action string raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_audit(action="")

    def test_empty_resource_type_raises(self) -> None:
        """Empty resource_type raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_audit(resource_type="   ")

    def test_empty_outcome_raises(self) -> None:
        """Empty outcome raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_audit(outcome="")


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

class TestSessionConstruction:
    """Tests for Session construction and invariants."""

    def test_valid_session_construction(self) -> None:
        """Valid session is constructed with active state."""
        session = _make_session()
        assert session.auth_version == 1
        assert session.revoked_at is None

    def test_refresh_token_not_in_repr(self) -> None:
        """Refresh token hash is excluded from session repr."""
        session = _make_session(refresh_token_hash="secret_refresh_hash")
        r = repr(session)
        assert "secret_refresh_hash" not in r
        assert "refresh_token_hash" not in r

    def test_expires_at_before_created_at_raises(self) -> None:
        """expires_at <= created_at raises ValidationError."""
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            _make_session(created_at=now, expires_at=now - timedelta(seconds=1))

    def test_expires_at_equal_created_at_raises(self) -> None:
        """expires_at == created_at raises ValidationError."""
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            _make_session(created_at=now, expires_at=now)

    def test_auth_version_less_than_one_raises(self) -> None:
        """auth_version < 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_session(auth_version=0)


class TestSessionValidityAndRevocation:
    """Tests for Session.is_valid and revoke behavior."""

    def test_is_valid_when_active(self) -> None:
        """Session is valid within its expiry window and matching auth_version."""
        now = datetime.now(UTC)
        session = _make_session(created_at=now, expires_at=now + timedelta(hours=1))
        assert session.is_valid(at=now + timedelta(minutes=30), current_auth_version=1) is True

    def test_is_invalid_when_expired(self) -> None:
        """Session is invalid when at >= expires_at."""
        now = datetime.now(UTC)
        session = _make_session(created_at=now, expires_at=now + timedelta(hours=1))
        assert session.is_valid(at=now + timedelta(hours=1), current_auth_version=1) is False
        assert session.is_valid(at=now + timedelta(hours=2), current_auth_version=1) is False

    def test_is_invalid_when_auth_version_mismatch(self) -> None:
        """Session is invalid when account auth_version does not match."""
        now = datetime.now(UTC)
        session = _make_session(auth_version=1, created_at=now, expires_at=now + timedelta(hours=1))
        assert session.is_valid(at=now + timedelta(minutes=10), current_auth_version=2) is False

    def test_revoke_active_session(self) -> None:
        """Revoking an active session records revoked_at and makes it invalid."""
        now = datetime.now(UTC)
        session = _make_session(created_at=now, expires_at=now + timedelta(hours=1))
        revoke_time = now + timedelta(minutes=10)
        session.revoke(at=revoke_time)
        assert session.revoked_at == revoke_time
        assert session.is_valid(at=now + timedelta(minutes=15), current_auth_version=1) is False

    def test_revoke_already_revoked_session_raises(self) -> None:
        """Revoking an already revoked session raises InvalidTransitionError."""
        now = datetime.now(UTC)
        session = _make_session(created_at=now, expires_at=now + timedelta(hours=1))
        session.revoke(at=now + timedelta(minutes=5))
        with pytest.raises(InvalidTransitionError):
            session.revoke(at=now + timedelta(minutes=10))

    def test_revoke_with_naive_timestamp_raises(self) -> None:
        """Revoke with naive timestamp raises ValidationError."""
        session = _make_session()
        with pytest.raises(ValidationError):
            session.revoke(at=datetime.now())

