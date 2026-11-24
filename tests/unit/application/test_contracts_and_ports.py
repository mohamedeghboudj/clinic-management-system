"""Unit tests for Application contracts and ports (DTOs, interfaces, paging)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from clinic_management.application.contracts.access import AuthenticatedSession
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.contracts.people import PatientSummary
from clinic_management.application.ports.accounts import AccountRepository
from clinic_management.application.ports.identity_provider import IdentityProvider
from clinic_management.application.ports.passwords import PasswordHasher
from clinic_management.application.ports.people import (
    PatientRepository,
    PersonRepository,
    StaffRepository,
)
from clinic_management.application.ports.sessions import SessionRepository
from clinic_management.domain.access.enums import Role
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.shared.errors import ValidationError


class TestAuthenticatedSessionDTO:
    """Tests for AuthenticatedSession DTO."""

    def _make_principal(self) -> Principal:
        """Create a valid Principal instance for testing."""
        return Principal(
            account_id=uuid4(),
            clinic_id=uuid4(),
            membership_id=uuid4(),
            staff_id=None,
            patient_id=None,
            roles=frozenset({Role.SECRETARY}),
            auth_version=1,
        )

    def test_valid_authenticated_session(self) -> None:
        """Valid AuthenticatedSession construction."""
        principal = self._make_principal()
        now = datetime.now(UTC)
        dto = AuthenticatedSession(
            principal=principal,
            access_token="acc_token_123",
            refresh_token="ref_token_456",
            expires_at=now + timedelta(hours=1),
        )
        assert dto.principal == principal
        assert dto.access_token == "acc_token_123"
        assert dto.refresh_token == "ref_token_456"

    def test_token_fields_excluded_from_repr(self) -> None:
        """access_token and refresh_token must not appear in __repr__."""
        principal = self._make_principal()
        dto = AuthenticatedSession(
            principal=principal,
            access_token="secret_access_jwt",
            refresh_token="secret_refresh_jwt",
            expires_at=datetime.now(UTC),
        )
        r = repr(dto)
        assert "secret_access_jwt" not in r
        assert "secret_refresh_jwt" not in r
        assert "access_token" not in r
        assert "refresh_token" not in r

    def test_invalid_tokens_raise(self) -> None:
        """Empty tokens or naive expires_at raise ValidationError."""
        principal = self._make_principal()
        with pytest.raises(ValidationError):
            AuthenticatedSession(
                principal=principal,
                access_token="",
                refresh_token="valid",
                expires_at=datetime.now(UTC),
            )
        with pytest.raises(ValidationError):
            AuthenticatedSession(
                principal=principal,
                access_token="valid",
                refresh_token="   ",
                expires_at=datetime.now(UTC),
            )
        with pytest.raises(ValidationError):
            AuthenticatedSession(
                principal=principal,
                access_token="valid",
                refresh_token="valid",
                expires_at=datetime.now(),  # naive
            )


class TestPatientSummaryDTO:
    """Tests for PatientSummary DTO."""

    def test_valid_patient_summary(self) -> None:
        """Valid PatientSummary creation."""
        pid = uuid4()
        summary = PatientSummary(
            patient_id=pid,
            patient_number="P-001",
            display_name="John Doe",
            phone="+213550123456",
            version=0,
        )
        assert summary.patient_id == pid
        assert summary.patient_number == "P-001"
        assert summary.display_name == "John Doe"
        assert summary.phone == "+213550123456"
        assert summary.version == 0

    def test_patient_summary_optional_phone_none(self) -> None:
        """PatientSummary allows phone to be None."""
        summary = PatientSummary(
            patient_id=uuid4(),
            patient_number="P-001",
            display_name="Jane Doe",
            phone=None,
            version=2,
        )
        assert summary.phone is None

    def test_invalid_summary_fields_raise(self) -> None:
        """Invalid strings or negative version raise ValidationError."""
        pid = uuid4()
        with pytest.raises(ValidationError):
            PatientSummary(
                patient_id=pid,
                patient_number="",
                display_name="Jane",
                phone=None,
                version=0,
            )
        with pytest.raises(ValidationError):
            PatientSummary(
                patient_id=pid,
                patient_number="P-1",
                display_name="   ",
                phone=None,
                version=0,
            )
        with pytest.raises(ValidationError):
            PatientSummary(
                patient_id=pid,
                patient_number="P-1",
                display_name="Jane",
                phone="   ",
                version=0,
            )
        with pytest.raises(ValidationError):
            PatientSummary(
                patient_id=pid,
                patient_number="P-1",
                display_name="Jane",
                phone=None,
                version=-1,
            )


class TestPaginationContract:
    """Tests for shared cursor-based PageRequest and Page contract."""

    def test_page_request_defaults(self) -> None:
        """PageRequest provides default limit 25 and None cursor."""
        pr = PageRequest()
        assert pr.limit == 25
        assert pr.cursor is None

    def test_page_request_custom(self) -> None:
        """PageRequest validates valid limit and ASCII printable cursor."""
        pr = PageRequest(limit=50, cursor="cursor-token-123")
        assert pr.limit == 50
        assert pr.cursor == "cursor-token-123"

    def test_page_request_invalid_limits(self) -> None:
        """Invalid limits (out of 1..100 or non-int) raise ValidationError."""
        with pytest.raises(ValidationError):
            PageRequest(limit=0)
        with pytest.raises(ValidationError):
            PageRequest(limit=101)
        with pytest.raises(ValidationError):
            PageRequest(limit=-1)

    def test_page_request_malformed_cursor(self) -> None:
        """Empty, non-ASCII, non-printable, or overly long cursors raise ValidationError."""
        with pytest.raises(ValidationError):
            PageRequest(cursor="")
        with pytest.raises(ValidationError):
            PageRequest(cursor="invalid whitespace cursor")
        with pytest.raises(ValidationError):
            PageRequest(cursor="bad\x00char")
        with pytest.raises(ValidationError):
            PageRequest(cursor="a" * 2049)

    def test_page_immutable_container(self) -> None:
        """Page requires an immutable tuple container and enforces MAX_PAGE_SIZE."""
        with pytest.raises(ValidationError):
            Page(items=[1, 2, 3], next_cursor=None)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            Page(items=tuple(range(101)), next_cursor=None)

    def test_page_has_next_and_continuation_cursor(self) -> None:
        """Page has_next reflects continuation cursor presence correctly."""
        page_with_next = Page(items=(1, 2, 3), next_cursor="next-ptr-99")
        assert page_with_next.has_next() is True
        assert page_with_next.next_cursor == "next-ptr-99"

        terminal_page = Page(items=(1, 2, 3), next_cursor=None)
        assert terminal_page.has_next() is False
        assert terminal_page.next_cursor is None

    def test_page_validates_next_cursor_shape(self) -> None:
        """Page validates that next_cursor adheres to cursor rules."""
        with pytest.raises(ValidationError):
            Page(items=(1, 2), next_cursor="bad space cursor")


class TestPortsAreAbstract:
    """Ensure all declared application ports cannot be instantiated directly."""

    def test_abstract_ports_cannot_be_instantiated(self) -> None:
        """Ports should be abstract classes."""
        with pytest.raises(TypeError):
            PasswordHasher()  # type: ignore[abstract]

        with pytest.raises(TypeError):
            IdentityProvider()  # type: ignore[abstract]

        with pytest.raises(TypeError):
            PersonRepository()  # type: ignore[abstract]

        with pytest.raises(TypeError):
            PatientRepository()  # type: ignore[abstract]

        with pytest.raises(TypeError):
            StaffRepository()  # type: ignore[abstract]

        with pytest.raises(TypeError):
            AccountRepository()  # type: ignore[abstract]

        with pytest.raises(TypeError):
            SessionRepository()  # type: ignore[abstract]
