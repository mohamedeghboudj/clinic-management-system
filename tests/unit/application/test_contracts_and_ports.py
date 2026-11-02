"""Unit tests for Application contracts and ports (DTOs, interfaces, pagination)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from clinic_management.application.contracts.access import AuthenticatedSession
from clinic_management.application.contracts.people import PatientSummary
from clinic_management.application.ports.pagination import Page, PageRequest
from clinic_management.application.ports.passwords import PasswordHasher
from clinic_management.application.ports.identity_provider import IdentityProvider
from clinic_management.application.ports.repositories import (
    AccountRepository,
    PatientRepository,
    PersonRepository,
    SessionRepository,
    StaffRepository,
)
from clinic_management.domain.access.enums import Role
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.shared.errors import ValidationError


class TestAuthenticatedSessionDTO:
    """Tests for AuthenticatedSession DTO."""

    def _make_principal(self) -> Principal:
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


class TestPaginationPort:
    """Tests for PageRequest and Page pagination structures."""

    def test_page_request_valid(self) -> None:
        """PageRequest validates positive page and page_size."""
        pr = PageRequest(page=1, page_size=20)
        assert pr.page == 1
        assert pr.page_size == 20

    def test_page_request_invalid(self) -> None:
        """Invalid page numbers raise ValidationError."""
        with pytest.raises(ValidationError):
            PageRequest(page=0, page_size=10)
        with pytest.raises(ValidationError):
            PageRequest(page=1, page_size=0)

    def test_page_computation(self) -> None:
        """Page calculates total_pages and has_next correctly."""
        page = Page(items=(1, 2, 3), total=10, page=1, page_size=3)
        assert page.total_pages == 4
        assert page.has_next is True

        last_page = Page(items=(10,), total=10, page=4, page_size=3)
        assert last_page.has_next is False


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

