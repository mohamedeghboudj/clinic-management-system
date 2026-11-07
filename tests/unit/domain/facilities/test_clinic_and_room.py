"""Unit tests for the Clinic and Room domain entities."""

from __future__ import annotations

from datetime import time
from uuid import uuid4

import pytest

from clinic_management.domain.facilities.clinic import Clinic
from clinic_management.domain.facilities.enums import RoomStatus, RoomType
from clinic_management.domain.facilities.opening_hours import OpeningHours, OpeningPeriod
from clinic_management.domain.facilities.room import Room
from clinic_management.domain.shared.address import Address
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.errors import ValidationError

_ALGIERS = "Africa/Algiers"


def _default_hours(tz: str = _ALGIERS) -> OpeningHours:
    periods = tuple(
        OpeningPeriod(weekday=d, opens_at=time(8), closes_at=time(17)) for d in range(5)
    )
    return OpeningHours(timezone=tz, periods=periods)


def _make_clinic(**kwargs) -> Clinic:
    defaults = dict(
        id=uuid4(),
        name="Polyclinique Centrale",
        contact=ContactInfo(phone="+213550123456"),
        timezone=_ALGIERS,
        currency="DZD",
        opening_hours=_default_hours(_ALGIERS),
    )
    defaults.update(kwargs)
    return Clinic(**defaults)


def _make_room(**kwargs) -> Room:
    defaults = dict(
        id=uuid4(),
        clinic_id=uuid4(),
        number="C-01",
        kind=RoomType.CONSULTATION,
        capacity=1,
    )
    defaults.update(kwargs)
    return Room(**defaults)


# ---------------------------------------------------------------------------
# Clinic tests
# ---------------------------------------------------------------------------

class TestClinicConstruction:
    """Construction and field validation for the Clinic entity."""

    def test_valid_clinic_accepted(self) -> None:
        """A fully valid clinic is constructed without errors."""
        clinic = _make_clinic()
        assert clinic.active is True
        assert clinic.currency == "DZD"
        assert clinic.version == 0

    def test_name_stripped(self) -> None:
        """Leading/trailing whitespace in name is stripped."""
        clinic = _make_clinic(name="  Clinic Name  ")
        assert clinic.name == "Clinic Name"

    def test_empty_name_rejected(self) -> None:
        """Empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _make_clinic(name="   ")
        assert exc_info.value.safe_details["field"] == "name"

    def test_currency_uppercased(self) -> None:
        """Currency code is uppercased on construction."""
        clinic = _make_clinic(currency="dzd")
        assert clinic.currency == "DZD"

    def test_invalid_currency_length_rejected(self) -> None:
        """Currency code that is not 3 alpha chars raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_clinic(currency="DZ")

    def test_numeric_currency_rejected(self) -> None:
        """Non-alphabetic currency code raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_clinic(currency="123")

    def test_timezone_mismatch_rejected(self) -> None:
        """Opening hours timezone that differs from clinic timezone raises ValidationError."""
        hours_paris = _default_hours("Europe/Paris")
        with pytest.raises(ValidationError) as exc_info:
            _make_clinic(timezone=_ALGIERS, opening_hours=hours_paris)
        assert exc_info.value.code == "INVALID_VALUE"
        assert "timezone" in exc_info.value.message_key

    def test_address_accepted_as_optional(self) -> None:
        """Clinic without address is valid; with Address it is also valid."""
        clinic_no_addr = _make_clinic(address=None)
        assert clinic_no_addr.address is None

        addr = Address(line1="1 Rue de la Paix", city="Alger", country_code="DZ")
        clinic_with_addr = _make_clinic(address=addr)
        assert clinic_with_addr.address == addr

    def test_negative_version_rejected(self) -> None:
        """Negative version raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_clinic(version=-1)

    def test_invalid_contact_type_rejected(self) -> None:
        """Non-ContactInfo contact raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_clinic(contact="contact@clinic.dz")  # type: ignore[arg-type]


class TestClinicMethods:
    """Behaviour of Clinic mutation methods."""

    def test_update_opening_hours_succeeds_with_matching_timezone(self) -> None:
        """Replacing opening hours with same timezone is accepted."""
        clinic = _make_clinic()
        new_hours = OpeningHours(
            timezone=_ALGIERS,
            periods=(OpeningPeriod(weekday=6, opens_at=time(9), closes_at=time(13)),),
        )
        clinic.update_opening_hours(new_hours)
        assert clinic.opening_hours is new_hours

    def test_update_opening_hours_rejects_timezone_mismatch(self) -> None:
        """update_opening_hours raises if the new schedule has a different timezone."""
        clinic = _make_clinic()
        hours_paris = _default_hours("Europe/Paris")
        with pytest.raises(ValidationError):
            clinic.update_opening_hours(hours_paris)

    def test_deactivate_sets_active_false(self) -> None:
        """deactivate() sets active to False."""
        clinic = _make_clinic()
        assert clinic.active is True
        clinic.deactivate()
        assert clinic.active is False

    def test_deactivate_idempotent(self) -> None:
        """Calling deactivate twice does not raise."""
        clinic = _make_clinic()
        clinic.deactivate()
        clinic.deactivate()
        assert clinic.active is False


class TestClinicEntityIdentity:
    """M1 Entity identity semantics for Clinic."""

    def test_same_id_equals(self) -> None:
        cid = uuid4()
        c1 = _make_clinic(id=cid, name="A")
        c2 = _make_clinic(id=cid, name="B")
        assert c1 == c2

    def test_different_id_not_equal(self) -> None:
        c1 = _make_clinic()
        c2 = _make_clinic()
        assert c1 != c2

    def test_clinic_not_hashable(self) -> None:
        with pytest.raises(TypeError):
            hash(_make_clinic())


# ---------------------------------------------------------------------------
# Room tests
# ---------------------------------------------------------------------------

class TestRoomConstruction:
    """Construction and field validation for the Room entity."""

    def test_valid_room_accepted(self) -> None:
        """A valid room is constructed with ACTIVE status."""
        room = _make_room()
        assert room.status is RoomStatus.ACTIVE
        assert room.is_bookable() is True
        assert room.status_reason is None

    def test_zero_capacity_rejected(self) -> None:
        """Zero or negative capacity raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_room(capacity=0)
        with pytest.raises(ValidationError):
            _make_room(capacity=-1)

    def test_empty_room_number_rejected(self) -> None:
        """Empty/whitespace room number raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_room(number="   ")

    def test_room_number_stripped(self) -> None:
        """Room number is stripped of surrounding whitespace."""
        room = _make_room(number="  C-01  ")
        assert room.number == "C-01"

    def test_invalid_kind_rejected(self) -> None:
        """Non-RoomType kind raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_room(kind="CONSULTATION")  # type: ignore[arg-type]

    def test_negative_version_rejected(self) -> None:
        """Negative version raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_room(version=-1)


class TestRoomMethods:
    """Behaviour of Room lifecycle methods."""

    def test_mark_out_of_service_sets_status(self) -> None:
        """mark_out_of_service sets status and reason."""
        room = _make_room()
        room.mark_out_of_service("Scheduled maintenance")
        assert room.status is RoomStatus.OUT_OF_SERVICE
        assert room.status_reason == "Scheduled maintenance"
        assert room.is_bookable() is False

    def test_mark_out_of_service_empty_reason_rejected(self) -> None:
        """Empty reason for out-of-service raises ValidationError."""
        room = _make_room()
        with pytest.raises(ValidationError):
            room.mark_out_of_service("   ")

    def test_restore_service_clears_status_and_reason(self) -> None:
        """restore_service sets ACTIVE and clears reason."""
        room = _make_room()
        room.mark_out_of_service("Maintenance")
        room.restore_service()
        assert room.status is RoomStatus.ACTIVE
        assert room.status_reason is None
        assert room.is_bookable() is True

    def test_out_of_service_room_is_not_bookable(self) -> None:
        """is_bookable returns False for OUT_OF_SERVICE room."""
        room = _make_room(status=RoomStatus.OUT_OF_SERVICE, status_reason="Broken AC")
        assert room.is_bookable() is False

    def test_room_has_no_book_method(self) -> None:
        """Room does not expose a book() method."""
        assert not hasattr(Room, "book")

    def test_all_room_types_accepted(self) -> None:
        """Every RoomType value can be used to construct a Room."""
        for kind in RoomType:
            room = _make_room(kind=kind)
            assert room.kind is kind


class TestRoomEntityIdentity:
    """M1 Entity identity semantics for Room."""

    def test_same_id_equals(self) -> None:
        rid = uuid4()
        r1 = _make_room(id=rid, number="A-01")
        r2 = _make_room(id=rid, number="A-99")
        assert r1 == r2

    def test_different_id_not_equal(self) -> None:
        r1 = _make_room()
        r2 = _make_room()
        assert r1 != r2

    def test_room_not_hashable(self) -> None:
        with pytest.raises(TypeError):
            hash(_make_room())
