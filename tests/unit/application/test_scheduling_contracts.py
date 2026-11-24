"""Coverage tests for M3 scheduling application contracts and repository ports.

These tests verify the public interface contracts for ``AppointmentSummary``,
``AppointmentRepository``, ``ClinicRepository``, and ``RoomRepository``.
They use in-memory stub implementations to exercise every import path and
ensure the per-module coverage gate is met without requiring a database.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4

import pytest

from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.contracts.scheduling import AppointmentSummary
from clinic_management.application.ports.facilities import ClinicRepository, RoomRepository
from clinic_management.application.ports.scheduling import AppointmentRepository
from clinic_management.domain.facilities.clinic import Clinic
from clinic_management.domain.facilities.enums import RoomStatus, RoomType
from clinic_management.domain.facilities.opening_hours import OpeningHours, OpeningPeriod
from clinic_management.domain.facilities.room import Room
from clinic_management.domain.scheduling.appointment import Appointment
from clinic_management.domain.scheduling.enums import AppointmentStatus
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ALGIERS = "Africa/Algiers"
_NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
_SLOT = TimeSlot(
    start=datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
    end=datetime(2026, 11, 10, 9, 30, tzinfo=UTC),
)


def _default_hours() -> OpeningHours:
    """Return a standard Mon–Fri 08:00–17:00 schedule in Africa/Algiers."""
    periods = tuple(
        OpeningPeriod(weekday=d, opens_at=time(8), closes_at=time(17)) for d in range(5)
    )
    return OpeningHours(timezone=_ALGIERS, periods=periods)


def _make_clinic(clinic_id: UUID | None = None) -> Clinic:
    """Return a minimal valid Clinic entity."""
    return Clinic(
        id=clinic_id or uuid4(),
        name="Test Clinic",
        contact=ContactInfo(phone="+213550000001"),
        timezone=_ALGIERS,
        currency="DZD",
        opening_hours=_default_hours(),
    )


def _make_room(clinic_id: UUID | None = None) -> Room:
    """Return a minimal valid ACTIVE Room entity."""
    return Room(
        id=uuid4(),
        clinic_id=clinic_id or uuid4(),
        number="C-01",
        kind=RoomType.CONSULTATION,
        capacity=1,
    )


def _make_appointment(clinic_id: UUID | None = None) -> Appointment:
    """Return a minimal valid Appointment entity in SCHEDULED state."""
    return Appointment(
        id=uuid4(),
        clinic_id=clinic_id or uuid4(),
        patient_id=uuid4(),
        doctor_id=uuid4(),
        room_id=uuid4(),
        slot=_SLOT,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# AppointmentSummary DTO
# ---------------------------------------------------------------------------


class TestAppointmentSummary:
    """Tests for the AppointmentSummary read model."""

    def test_construction_with_all_fields(self) -> None:
        """AppointmentSummary is constructed with all required fields."""
        appt_id = uuid4()
        summary = AppointmentSummary(
            appointment_id=appt_id,
            patient_id=uuid4(),
            doctor_id=uuid4(),
            room_id=uuid4(),
            slot=_SLOT,
            status=AppointmentStatus.SCHEDULED,
            version=0,
        )
        assert summary.appointment_id == appt_id
        assert summary.status is AppointmentStatus.SCHEDULED
        assert summary.version == 0

    def test_all_statuses_accepted(self) -> None:
        """AppointmentSummary can represent every AppointmentStatus value."""
        for status in AppointmentStatus:
            summary = AppointmentSummary(
                appointment_id=uuid4(),
                patient_id=uuid4(),
                doctor_id=uuid4(),
                room_id=uuid4(),
                slot=_SLOT,
                status=status,
                version=1,
            )
            assert summary.status is status

    def test_negative_version_rejected(self) -> None:
        """AppointmentSummary raises ValidationError for a negative version."""
        with pytest.raises(ValidationError):
            AppointmentSummary(
                appointment_id=uuid4(),
                patient_id=uuid4(),
                doctor_id=uuid4(),
                room_id=uuid4(),
                slot=_SLOT,
                status=AppointmentStatus.SCHEDULED,
                version=-1,
            )

    def test_invalid_slot_type_rejected(self) -> None:
        """AppointmentSummary raises ValidationError when slot is not a TimeSlot."""
        with pytest.raises((ValidationError, TypeError)):
            AppointmentSummary(
                appointment_id=uuid4(),
                patient_id=uuid4(),
                doctor_id=uuid4(),
                room_id=uuid4(),
                slot="not-a-slot",  # type: ignore[arg-type]
                status=AppointmentStatus.SCHEDULED,
                version=0,
            )

    def test_summary_is_immutable(self) -> None:
        """AppointmentSummary is frozen — mutation raises TypeError."""
        summary = AppointmentSummary(
            appointment_id=uuid4(),
            patient_id=uuid4(),
            doctor_id=uuid4(),
            room_id=uuid4(),
            slot=_SLOT,
            status=AppointmentStatus.SCHEDULED,
            version=0,
        )
        with pytest.raises((TypeError, AttributeError)):
            summary.status = AppointmentStatus.CANCELLED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# In-memory stubs to exercise the repository port interfaces
# ---------------------------------------------------------------------------


class _StubAppointmentRepository(AppointmentRepository):
    """Minimal in-memory implementation of AppointmentRepository."""

    def __init__(self) -> None:
        """Initialise an empty appointment store."""
        self._store: dict[UUID, Appointment] = {}

    def get(self, clinic_id: UUID, appointment_id: UUID) -> Appointment | None:
        """Return the appointment matching both IDs, or None."""
        appt = self._store.get(appointment_id)
        if appt is None or appt.clinic_id != clinic_id:
            return None
        return appt

    def add(self, appointment: Appointment) -> None:
        """Store a new appointment by its ID."""
        self._store[appointment.id] = appointment

    def save(self, appointment: Appointment, *, expected_version: int) -> None:
        """Replace the stored appointment; ignores version for the stub."""
        self._store[appointment.id] = appointment

    def find_overlaps(
        self,
        clinic_id: UUID,
        slot: TimeSlot,
        *,
        doctor_id: UUID | None,
        room_id: UUID | None,
        exclude_id: UUID | None = None,
    ) -> tuple[Appointment, ...]:
        """Return appointments with overlapping slots for the given resources."""
        results = []
        for appt in self._store.values():
            if appt.clinic_id != clinic_id:
                continue
            if appt.id == exclude_id:
                continue
            if not appt.status.is_active():
                continue
            if not appt.slot.overlaps(slot):
                continue
            if (doctor_id and appt.doctor_id == doctor_id) or (
                room_id and appt.room_id == room_id
            ):
                results.append(appt)
        return tuple(results)

    def list_for_doctor(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        day: date,
        page: PageRequest,
    ) -> Page[AppointmentSummary]:
        """Return an empty page — stub exercises the port signature only."""
        return Page(items=(), next_cursor=None)


class _StubClinicRepository(ClinicRepository):
    """Minimal in-memory implementation of ClinicRepository."""

    def __init__(self) -> None:
        """Initialise an empty clinic store."""
        self._store: dict[UUID, Clinic] = {}

    def get(self, clinic_id: UUID) -> Clinic | None:
        """Return the clinic by ID, or None."""
        return self._store.get(clinic_id)

    def add(self, clinic: Clinic) -> None:
        """Store a new clinic."""
        self._store[clinic.id] = clinic

    def save(self, clinic: Clinic, *, expected_version: int) -> None:
        """Replace the stored clinic; ignores version for the stub."""
        self._store[clinic.id] = clinic


class _StubRoomRepository(RoomRepository):
    """Minimal in-memory implementation of RoomRepository."""

    def __init__(self) -> None:
        """Initialise an empty room store."""
        self._store: dict[UUID, Room] = {}

    def get(self, clinic_id: UUID, room_id: UUID) -> Room | None:
        """Return the room matching both IDs, or None."""
        room = self._store.get(room_id)
        if room is None or room.clinic_id != clinic_id:
            return None
        return room

    def add(self, room: Room) -> None:
        """Store a new room."""
        self._store[room.id] = room

    def save(self, room: Room, *, expected_version: int) -> None:
        """Replace the stored room; ignores version for the stub."""
        self._store[room.id] = room

    def list_active(self, clinic_id: UUID, page: PageRequest) -> Page[Room]:
        """Return active rooms for the given clinic as a paged result."""
        active = tuple(
            r
            for r in self._store.values()
            if r.clinic_id == clinic_id and r.status is RoomStatus.ACTIVE
        )
        return Page(items=active, next_cursor=None)


# ---------------------------------------------------------------------------
# AppointmentRepository port tests
# ---------------------------------------------------------------------------


class TestAppointmentRepositoryPort:
    """Exercises the AppointmentRepository port contract via a stub."""

    def test_add_and_get_roundtrip(self) -> None:
        """An added appointment is retrievable by its clinic and ID."""
        repo = _StubAppointmentRepository()
        appt = _make_appointment()
        repo.add(appt)
        found = repo.get(appt.clinic_id, appt.id)
        assert found is appt

    def test_get_returns_none_for_missing(self) -> None:
        """get() returns None when no appointment matches the IDs."""
        repo = _StubAppointmentRepository()
        assert repo.get(uuid4(), uuid4()) is None

    def test_get_returns_none_for_wrong_clinic(self) -> None:
        """get() returns None when the clinic_id does not match the stored record."""
        repo = _StubAppointmentRepository()
        appt = _make_appointment()
        repo.add(appt)
        assert repo.get(uuid4(), appt.id) is None

    def test_save_replaces_appointment(self) -> None:
        """save() updates the stored aggregate for subsequent get() calls."""
        repo = _StubAppointmentRepository()
        appt = _make_appointment()
        repo.add(appt)
        appt.check_in(at=_NOW + timedelta(minutes=5))
        repo.save(appt, expected_version=0)
        found = repo.get(appt.clinic_id, appt.id)
        assert found is not None
        assert found.status is AppointmentStatus.CHECKED_IN

    def test_find_overlaps_detects_doctor_conflict(self) -> None:
        """find_overlaps returns active appointments overlapping the slot for a doctor."""
        repo = _StubAppointmentRepository()
        clinic_id = uuid4()
        doctor_id = uuid4()
        appt = _make_appointment(clinic_id=clinic_id)
        object.__setattr__(appt, "doctor_id", doctor_id)
        repo.add(appt)
        overlapping = repo.find_overlaps(
            clinic_id, _SLOT, doctor_id=doctor_id, room_id=None
        )
        assert len(overlapping) == 1

    def test_find_overlaps_excludes_id(self) -> None:
        """find_overlaps omits the appointment matching exclude_id."""
        repo = _StubAppointmentRepository()
        clinic_id = uuid4()
        doctor_id = uuid4()
        appt = _make_appointment(clinic_id=clinic_id)
        object.__setattr__(appt, "doctor_id", doctor_id)
        repo.add(appt)
        overlapping = repo.find_overlaps(
            clinic_id, _SLOT, doctor_id=doctor_id, room_id=None, exclude_id=appt.id
        )
        assert len(overlapping) == 0

    def test_find_overlaps_ignores_inactive_appointments(self) -> None:
        """find_overlaps does not return cancelled or completed appointments."""
        repo = _StubAppointmentRepository()
        clinic_id = uuid4()
        doctor_id = uuid4()
        appt = _make_appointment(clinic_id=clinic_id)
        object.__setattr__(appt, "doctor_id", doctor_id)
        appt.cancel("test", at=_NOW + timedelta(minutes=1))
        repo.add(appt)
        overlapping = repo.find_overlaps(
            clinic_id, _SLOT, doctor_id=doctor_id, room_id=None
        )
        assert len(overlapping) == 0

    def test_list_for_doctor_returns_page(self) -> None:
        """list_for_doctor returns a Page object."""
        repo = _StubAppointmentRepository()
        result = repo.list_for_doctor(uuid4(), uuid4(), date(2026, 11, 10), PageRequest(limit=10))
        assert isinstance(result, Page)


# ---------------------------------------------------------------------------
# ClinicRepository port tests
# ---------------------------------------------------------------------------


class TestClinicRepositoryPort:
    """Exercises the ClinicRepository port contract via a stub."""

    def test_add_and_get_roundtrip(self) -> None:
        """An added clinic is retrievable by its ID."""
        repo = _StubClinicRepository()
        clinic = _make_clinic()
        repo.add(clinic)
        assert repo.get(clinic.id) is clinic

    def test_get_returns_none_for_missing(self) -> None:
        """get() returns None when no clinic matches the ID."""
        repo = _StubClinicRepository()
        assert repo.get(uuid4()) is None

    def test_save_updates_stored_clinic(self) -> None:
        """save() updates the stored clinic so get() reflects the change."""
        repo = _StubClinicRepository()
        clinic = _make_clinic()
        repo.add(clinic)
        clinic.deactivate()
        repo.save(clinic, expected_version=0)
        found = repo.get(clinic.id)
        assert found is not None
        assert found.active is False


# ---------------------------------------------------------------------------
# RoomRepository port tests
# ---------------------------------------------------------------------------


class TestRoomRepositoryPort:
    """Exercises the RoomRepository port contract via a stub."""

    def test_add_and_get_roundtrip(self) -> None:
        """An added room is retrievable by its clinic and room ID."""
        repo = _StubRoomRepository()
        clinic_id = uuid4()
        room = _make_room(clinic_id=clinic_id)
        repo.add(room)
        assert repo.get(clinic_id, room.id) is room

    def test_get_returns_none_for_wrong_clinic(self) -> None:
        """get() returns None when the clinic_id does not match."""
        repo = _StubRoomRepository()
        room = _make_room()
        repo.add(room)
        assert repo.get(uuid4(), room.id) is None

    def test_save_updates_stored_room(self) -> None:
        """save() updates the stored room so get() reflects the change."""
        repo = _StubRoomRepository()
        clinic_id = uuid4()
        room = _make_room(clinic_id=clinic_id)
        repo.add(room)
        room.mark_out_of_service("Maintenance")
        repo.save(room, expected_version=0)
        found = repo.get(clinic_id, room.id)
        assert found is not None
        assert found.status is RoomStatus.OUT_OF_SERVICE

    def test_list_active_returns_active_rooms_only(self) -> None:
        """list_active excludes out-of-service rooms from results."""
        repo = _StubRoomRepository()
        clinic_id = uuid4()
        active_room = _make_room(clinic_id=clinic_id)
        oos_room = Room(
            id=uuid4(),
            clinic_id=clinic_id,
            number="C-02",
            kind=RoomType.CONSULTATION,
            capacity=1,
            status=RoomStatus.OUT_OF_SERVICE,
            status_reason="Broken AC",
        )
        repo.add(active_room)
        repo.add(oos_room)
        result = repo.list_active(clinic_id, PageRequest(limit=10))
        assert active_room in result.items
        assert oos_room not in result.items

    def test_list_active_excludes_other_clinics(self) -> None:
        """list_active only returns rooms belonging to the requested clinic."""
        repo = _StubRoomRepository()
        clinic_a = uuid4()
        clinic_b = uuid4()
        repo.add(_make_room(clinic_id=clinic_a))
        repo.add(_make_room(clinic_id=clinic_b))
        result = repo.list_active(clinic_a, PageRequest(limit=10))
        assert len(result.items) == 1
