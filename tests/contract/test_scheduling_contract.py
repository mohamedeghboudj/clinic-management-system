"""Independent M4 tests for M3's published scheduling and facilities contracts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType
from typing import Protocol, cast
from uuid import UUID

import pytest

from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)

pytestmark = pytest.mark.scheduling_contract
PREFIX = "clinic_management.domain."

CLINIC_ID = UUID("00000000-0000-0000-0000-000000000001")
PATIENT_ID = UUID("00000000-0000-0000-0000-000000000002")
DOCTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
ROOM_ID = UUID("00000000-0000-0000-0000-000000000004")

SLOT_START = datetime(2026, 11, 2, 9, 0, 0, tzinfo=UTC)
SLOT_END = datetime(2026, 11, 2, 10, 0, 0, tzinfo=UTC)


class TimeSlotContract(Protocol):
    """Minimal TimeSlot protocol for contract testing."""

    start: datetime
    end: datetime

    def overlaps(self, other: TimeSlotContract) -> bool:
        """Return whether this interval overlaps another."""
        ...

    def contains(self, instant: datetime) -> bool:
        """Return whether an aware instant falls within [start, end)."""
        ...

    def duration(self) -> timedelta:
        """Return the positive time difference between start and end."""
        ...


class AppointmentContract(Protocol):
    """Minimal Appointment protocol for contract testing."""

    slot: TimeSlotContract
    version: int

    def check_in(self, *, at: datetime) -> None:
        """Transition from SCHEDULED to CHECKED_IN."""
        ...

    def complete(self, *, at: datetime) -> None:
        """Transition from CHECKED_IN to COMPLETED."""
        ...

    def cancel(self, reason: str, *, at: datetime) -> None:
        """Cancel the appointment with a mandatory reason."""
        ...

    def mark_no_show(self, *, at: datetime) -> None:
        """Mark as no-show after the slot has elapsed."""
        ...

    def reschedule(self, slot: TimeSlotContract, *, at: datetime) -> None:
        """Reschedule while in SCHEDULED status."""
        ...


class RoomContract(Protocol):
    """Minimal Room protocol for contract testing."""

    def is_bookable(self) -> bool:
        """Return whether the room can be reserved."""
        ...

    def mark_out_of_service(self, reason: str) -> None:
        """Take room out of service."""
        ...

    def restore_service(self) -> None:
        """Restore room to active service."""
        ...


def dependency(suffix: str) -> ModuleType:
    """Load an implemented M3 dependency or explicitly skip if not yet merged.

    Args:
        suffix: Documented relative module name under the domain package.

    Returns:
        The implementation module.
    """
    name = PREFIX + suffix
    if find_spec(name) is None:
        pytest.skip(f"Pending M3 implementation: {name}")
    return import_module(name)


def call(suffix: str, symbol: str, **values: object) -> object:
    """Instantiate a class or call a function from an M3 module.

    Args:
        suffix: Implementation module name.
        symbol: Exported symbol to invoke.
        values: Named keyword arguments.

    Returns:
        The constructed object or result.
    """
    factory = cast("Callable[..., object]", getattr(dependency(suffix), symbol))
    return factory(**values)


# ======================================================================
# TimeSlot Contract Tests
# ======================================================================


def test_time_slot_rejects_naive_datetime() -> None:
    """Verify that TimeSlot rejects naive datetimes lacking UTC timezone info."""
    naive_start = datetime(2026, 11, 2, 9, 0, 0)
    naive_end = datetime(2026, 11, 2, 10, 0, 0)
    with pytest.raises(ValidationError):
        call("shared.time_slot", "TimeSlot", start=naive_start, end=naive_end)


def test_time_slot_rejects_inverted_or_zero_interval() -> None:
    """Verify that start >= end is rejected as an invalid interval."""
    with pytest.raises(ValidationError):
        call("shared.time_slot", "TimeSlot", start=SLOT_END, end=SLOT_START)

    with pytest.raises(ValidationError):
        call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_START)


def test_time_slot_duration() -> None:
    """Verify that TimeSlot computes positive duration correctly."""
    slot = cast(
        TimeSlotContract,
        call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END),
    )
    assert slot.duration() == timedelta(hours=1)


def test_time_slot_adjacent_slots_do_not_overlap() -> None:
    """Verify that half-open interval [start, end) allows adjacent bookings without overlap."""
    slot1 = cast(
        TimeSlotContract,
        call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END),
    )
    adjacent = cast(
        TimeSlotContract,
        call(
            "shared.time_slot",
            "TimeSlot",
            start=SLOT_END,
            end=SLOT_END + timedelta(hours=1),
        ),
    )
    assert slot1.overlaps(adjacent) is False
    assert adjacent.overlaps(slot1) is False


def test_time_slot_intersecting_slots_overlap() -> None:
    """Verify that intersecting intervals correctly report an overlap."""
    slot1 = cast(
        TimeSlotContract,
        call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END),
    )
    intersecting = cast(
        TimeSlotContract,
        call(
            "shared.time_slot",
            "TimeSlot",
            start=SLOT_START + timedelta(minutes=30),
            end=SLOT_END + timedelta(minutes=30),
        ),
    )
    assert slot1.overlaps(intersecting) is True
    assert intersecting.overlaps(slot1) is True


def test_time_slot_half_open_contains_semantics() -> None:
    """Verify that [start, end) contains start but excludes end."""
    slot = cast(
        TimeSlotContract,
        call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END),
    )
    assert slot.contains(SLOT_START) is True
    assert slot.contains(SLOT_START + timedelta(minutes=30)) is True
    assert slot.contains(SLOT_END) is False


# ======================================================================
# Appointment Lifecycle Contract Tests
# ======================================================================


def test_appointment_lifecycle_scheduled_to_completed() -> None:
    """Verify standard appointment flow: SCHEDULED -> CHECKED_IN -> COMPLETED."""
    slot = call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END)
    status_enum = getattr(dependency("scheduling.enums"), "AppointmentStatus")
    appt = cast(
        AppointmentContract,
        call(
            "scheduling.appointment",
            "Appointment",
            id=UUID("00000000-0000-0000-0000-000000000080"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            room_id=ROOM_ID,
            slot=slot,
            status=status_enum.SCHEDULED,
            updated_at=SLOT_START - timedelta(days=1),
        ),
    )
    # Check in
    checkin_time = SLOT_START - timedelta(minutes=10)
    appt.check_in(at=checkin_time)

    # Complete
    complete_time = SLOT_START + timedelta(minutes=45)
    appt.complete(at=complete_time)


def test_appointment_cannot_complete_directly_from_scheduled() -> None:
    """Verify that completing an appointment without checking in is forbidden."""
    slot = call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END)
    status_enum = getattr(dependency("scheduling.enums"), "AppointmentStatus")
    appt = cast(
        AppointmentContract,
        call(
            "scheduling.appointment",
            "Appointment",
            id=UUID("00000000-0000-0000-0000-000000000081"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            room_id=ROOM_ID,
            slot=slot,
            status=status_enum.SCHEDULED,
            updated_at=SLOT_START - timedelta(days=1),
        ),
    )
    with pytest.raises(InvalidTransitionError):
        appt.complete(at=SLOT_END)


def test_appointment_early_no_show_is_rejected() -> None:
    """Verify that marking no-show before the slot ends is rejected."""
    slot = call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END)
    status_enum = getattr(dependency("scheduling.enums"), "AppointmentStatus")
    appt = cast(
        AppointmentContract,
        call(
            "scheduling.appointment",
            "Appointment",
            id=UUID("00000000-0000-0000-0000-000000000082"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            room_id=ROOM_ID,
            slot=slot,
            status=status_enum.SCHEDULED,
            updated_at=SLOT_START - timedelta(days=1),
        ),
    )
    # Attempt no-show before slot ends
    before_end = SLOT_START + timedelta(minutes=30)
    with pytest.raises((ValidationError, InvalidTransitionError)):
        appt.mark_no_show(at=before_end)


def test_appointment_cancellation_requires_reason() -> None:
    """Verify that cancelling an appointment requires a non-empty reason."""
    slot = call("shared.time_slot", "TimeSlot", start=SLOT_START, end=SLOT_END)
    status_enum = getattr(dependency("scheduling.enums"), "AppointmentStatus")
    appt = cast(
        AppointmentContract,
        call(
            "scheduling.appointment",
            "Appointment",
            id=UUID("00000000-0000-0000-0000-000000000083"),
            clinic_id=CLINIC_ID,
            patient_id=PATIENT_ID,
            doctor_id=DOCTOR_ID,
            room_id=ROOM_ID,
            slot=slot,
            status=status_enum.SCHEDULED,
            updated_at=SLOT_START - timedelta(days=1),
        ),
    )
    with pytest.raises(ValidationError):
        appt.cancel("   ", at=SLOT_START - timedelta(hours=2))


# ======================================================================
# Room Contract Tests
# ======================================================================


def test_room_service_lifecycle() -> None:
    """Verify Room is bookable when active and unbookable when out of service."""
    room_type = getattr(dependency("facilities.enums"), "RoomType").CONSULTATION
    room_status = getattr(dependency("facilities.enums"), "RoomStatus")
    room = cast(
        RoomContract,
        call(
            "facilities.room",
            "Room",
            id=ROOM_ID,
            clinic_id=CLINIC_ID,
            number="101-A",
            kind=room_type,
            capacity=1,
            status=room_status.ACTIVE,
            status_reason=None,
        ),
    )
    assert room.is_bookable() is True

    room.mark_out_of_service("Scheduled sanitization.")
    assert room.is_bookable() is False

    room.restore_service()
    assert room.is_bookable() is True
