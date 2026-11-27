"""Independent M4 tests for M3's published scheduling and facilities contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from clinic_management.domain.facilities.enums import RoomStatus, RoomType
from clinic_management.domain.facilities.room import Room
from clinic_management.domain.scheduling.appointment import Appointment
from clinic_management.domain.scheduling.enums import AppointmentStatus
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.time_slot import TimeSlot

CLINIC_ID = UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
ROOM_ID = UUID("00000000-0000-0000-0000-000000000004")

SLOT_START = datetime(2026, 11, 2, 9, 0, 0, tzinfo=UTC)
SLOT_END = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)


# ======================================================================
# TimeSlot Contract Tests
# ======================================================================


def test_time_slot_rejects_naive_datetime() -> None:
    """Verify that TimeSlot rejects naive datetimes lacking UTC timezone info."""
    naive_start = datetime(2026, 11, 2, 9, 0, 0)
    naive_end = datetime(2026, 11, 2, 10, 0, 0)
    with pytest.raises(ValidationError):
        TimeSlot(start=naive_start, end=naive_end)


def test_time_slot_rejects_inverted_or_zero_interval() -> None:
    """Verify that start >= end is rejected as an invalid interval."""
    with pytest.raises(ValidationError):
        TimeSlot(start=SLOT_END, end=SLOT_START)

    with pytest.raises(ValidationError):
        TimeSlot(start=SLOT_START, end=SLOT_START)


def test_time_slot_duration() -> None:
    """Verify that TimeSlot computes positive duration correctly."""
    slot = TimeSlot(start=SLOT_START, end=SLOT_END)
    assert slot.duration() == timedelta(hours=1)


def test_time_slot_adjacent_slots_do_not_overlap() -> None:
    """Verify that half-open interval [start, end) allows adjacent bookings without overlap."""
    slot1 = TimeSlot(start=SLOT_START, end=SLOT_END)
    adjacent = TimeSlot(
        start=SLOT_END,
        end=SLOT_END + timedelta(hours=1),
    )
    assert slot1.overlaps(adjacent) is False
    assert adjacent.overlaps(slot1) is False


def test_time_slot_intersecting_slots_overlap() -> None:
    """Verify that intersecting intervals correctly report an overlap."""
    slot1 = TimeSlot(start=SLOT_START, end=SLOT_END)
    intersecting = TimeSlot(
        start=SLOT_START + timedelta(minutes=30),
        end=SLOT_END + timedelta(minutes=30),
    )
    assert slot1.overlaps(intersecting) is True
    assert intersecting.overlaps(slot1) is True


def test_time_slot_half_open_contains_semantics() -> None:
    """Verify that [start, end) contains start but excludes end."""
    slot = TimeSlot(start=SLOT_START, end=SLOT_END)
    assert slot.contains(SLOT_START) is True
    assert slot.contains(SLOT_START + timedelta(minutes=30)) is True
    assert slot.contains(SLOT_END) is False


# ======================================================================
# Appointment Lifecycle Contract Tests
# ======================================================================


def test_appointment_lifecycle_scheduled_to_completed() -> None:
    """Verify standard appointment flow: SCHEDULED -> CHECKED_IN -> COMPLETED."""
    slot = TimeSlot(start=SLOT_START, end=SLOT_END)
    appt = Appointment(
        id=UUID("00000000-0000-0000-0000-000000000080"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        room_id=ROOM_ID,
        slot=slot,
        status=AppointmentStatus.SCHEDULED,
        updated_at=SLOT_START - timedelta(days=1),
    )
    # Check in
    checkin_time = SLOT_START - timedelta(minutes=10)
    appt.check_in(at=checkin_time)

    # Complete
    complete_time = SLOT_START + timedelta(minutes=45)
    appt.complete(at=complete_time)


def test_appointment_cannot_complete_directly_from_scheduled() -> None:
    """Verify that completing an appointment without checking in is forbidden."""
    slot = TimeSlot(start=SLOT_START, end=SLOT_END)
    appt = Appointment(
        id=UUID("00000000-0000-0000-0000-000000000081"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        room_id=ROOM_ID,
        slot=slot,
        status=AppointmentStatus.SCHEDULED,
        updated_at=SLOT_START - timedelta(days=1),
    )
    with pytest.raises(InvalidTransitionError):
        appt.complete(at=SLOT_END)


def test_appointment_early_no_show_is_rejected() -> None:
    """Verify that marking no-show before the slot ends is rejected."""
    slot = TimeSlot(start=SLOT_START, end=SLOT_END)
    appt = Appointment(
        id=UUID("00000000-0000-0000-0000-000000000082"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        room_id=ROOM_ID,
        slot=slot,
        status=AppointmentStatus.SCHEDULED,
        updated_at=SLOT_START - timedelta(days=1),
    )
    # Attempt no-show before slot ends (at 09:30 for a 09:00-10:00 appointment)
    before_end = SLOT_START + timedelta(minutes=30)
    with pytest.raises((ValidationError, InvalidTransitionError)):
        appt.mark_no_show(at=before_end)


def test_appointment_cancellation_requires_reason() -> None:
    """Verify that cancelling an appointment requires a non-empty reason."""
    slot = TimeSlot(start=SLOT_START, end=SLOT_END)
    appt = Appointment(
        id=UUID("00000000-0000-0000-0000-000000000083"),
        clinic_id=CLINIC_ID,
        patient_id=PATIENT_ID,
        doctor_id=DOCTOR_ID,
        room_id=ROOM_ID,
        slot=slot,
        status=AppointmentStatus.SCHEDULED,
        updated_at=SLOT_START - timedelta(days=1),
    )
    with pytest.raises(ValidationError):
        appt.cancel("   ", at=SLOT_START - timedelta(hours=2))


# ======================================================================
# Room Contract Tests
# ======================================================================


def test_room_service_lifecycle() -> None:
    """Verify Room is bookable when active and unbookable when out of service."""
    room = Room(
        id=ROOM_ID,
        clinic_id=CLINIC_ID,
        number="101-A",
        kind=RoomType.CONSULTATION,
        capacity=1,
        status=RoomStatus.ACTIVE,
        status_reason=None,
    )
    assert room.is_bookable() is True

    room.mark_out_of_service("Scheduled sanitization.")
    assert room.is_bookable() is False

    room.restore_service()
    assert room.is_bookable() is True
