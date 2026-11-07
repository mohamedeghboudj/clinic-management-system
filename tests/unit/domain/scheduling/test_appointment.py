"""Unit tests for Appointment lifecycle and AppointmentStatus transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from clinic_management.domain.scheduling.appointment import Appointment
from clinic_management.domain.scheduling.enums import AppointmentStatus
from clinic_management.domain.shared.errors import InvalidTransitionError, ValidationError
from clinic_management.domain.shared.time_slot import TimeSlot

# ---------------------------------------------------------------------------
# Fixed test data
# ---------------------------------------------------------------------------

_T_BASE = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)   # 09:00 UTC Monday
_T_END  = datetime(2026, 11, 10, 9, 30, tzinfo=UTC)  # 09:30 UTC
_T_AT   = datetime(2026, 11, 10, 9, 5,  tzinfo=UTC)  # 09:05 UTC — during slot

_SLOT = TimeSlot(start=_T_BASE, end=_T_END)


def _make_appointment(**kwargs) -> Appointment:
    defaults = dict(
        id=uuid4(),
        clinic_id=uuid4(),
        patient_id=uuid4(),
        doctor_id=uuid4(),
        room_id=uuid4(),
        slot=_SLOT,
        updated_at=_T_BASE,
    )
    defaults.update(kwargs)
    return Appointment(**defaults)


# ---------------------------------------------------------------------------
# AppointmentStatus transition table
# ---------------------------------------------------------------------------

class TestAppointmentStatusTransitions:
    """Unit tests for the AppointmentStatus.can_transition_to table."""

    @pytest.mark.parametrize("target", [
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.NO_SHOW,
        AppointmentStatus.CANCELLED,
    ])
    def test_scheduled_valid_transitions(self, target: AppointmentStatus) -> None:
        assert AppointmentStatus.SCHEDULED.can_transition_to(target) is True

    @pytest.mark.parametrize("target", [
        AppointmentStatus.COMPLETED,
        AppointmentStatus.SCHEDULED,
    ])
    def test_scheduled_invalid_transitions(self, target: AppointmentStatus) -> None:
        assert AppointmentStatus.SCHEDULED.can_transition_to(target) is False

    @pytest.mark.parametrize("target", [
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    ])
    def test_checked_in_valid_transitions(self, target: AppointmentStatus) -> None:
        assert AppointmentStatus.CHECKED_IN.can_transition_to(target) is True

    @pytest.mark.parametrize("target", [
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.NO_SHOW,
    ])
    def test_checked_in_invalid_transitions(self, target: AppointmentStatus) -> None:
        assert AppointmentStatus.CHECKED_IN.can_transition_to(target) is False

    @pytest.mark.parametrize("status", [
        AppointmentStatus.COMPLETED,
        AppointmentStatus.NO_SHOW,
        AppointmentStatus.CANCELLED,
    ])
    def test_terminal_statuses_have_no_valid_transitions(
        self, status: AppointmentStatus
    ) -> None:
        for target in AppointmentStatus:
            assert status.can_transition_to(target) is False

    def test_active_status_set(self) -> None:
        assert AppointmentStatus.SCHEDULED.is_active() is True
        assert AppointmentStatus.CHECKED_IN.is_active() is True
        assert AppointmentStatus.COMPLETED.is_active() is False
        assert AppointmentStatus.CANCELLED.is_active() is False
        assert AppointmentStatus.NO_SHOW.is_active() is False


# ---------------------------------------------------------------------------
# Appointment construction
# ---------------------------------------------------------------------------

class TestAppointmentConstruction:
    """Construction and field validation for Appointment."""

    def test_valid_appointment_created_as_scheduled(self) -> None:
        """Default status is SCHEDULED."""
        appt = _make_appointment()
        assert appt.status is AppointmentStatus.SCHEDULED
        assert appt.version == 0
        assert appt.cancellation_reason is None

    def test_naive_updated_at_rejected(self) -> None:
        """Naive updated_at raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_appointment(updated_at=datetime(2026, 11, 10, 9, 0))

    def test_invalid_slot_type_rejected(self) -> None:
        """Non-TimeSlot slot raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_appointment(slot="not-a-slot")  # type: ignore[arg-type]

    def test_negative_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_appointment(version=-1)

    def test_reason_summary_stripped(self) -> None:
        """reason_summary is stripped of surrounding whitespace."""
        appt = _make_appointment(reason_summary="  Routine check  ")
        assert appt.reason_summary == "Routine check"

    def test_empty_reason_summary_rejected(self) -> None:
        """Empty reason_summary raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_appointment(reason_summary="   ")


# ---------------------------------------------------------------------------
# check_in
# ---------------------------------------------------------------------------

class TestAppointmentCheckIn:
    """Tests for Appointment.check_in()."""

    def test_check_in_from_scheduled_succeeds(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        assert appt.status is AppointmentStatus.CHECKED_IN
        assert appt.updated_at == _T_AT

    def test_check_in_from_checked_in_raises(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        with pytest.raises(InvalidTransitionError) as exc_info:
            appt.check_in(at=_T_AT)
        assert exc_info.value.code == "INVALID_TRANSITION"

    def test_check_in_from_cancelled_raises(self) -> None:
        appt = _make_appointment()
        appt.cancel("Patient request", at=_T_AT)
        with pytest.raises(InvalidTransitionError):
            appt.check_in(at=_T_AT)

    def test_check_in_naive_timestamp_rejected(self) -> None:
        appt = _make_appointment()
        with pytest.raises(ValidationError):
            appt.check_in(at=datetime(2026, 11, 10, 9, 5))


# ---------------------------------------------------------------------------
# complete
# ---------------------------------------------------------------------------

class TestAppointmentComplete:
    """Tests for Appointment.complete()."""

    def test_complete_from_checked_in_succeeds(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        t_complete = _T_END + timedelta(minutes=1)
        appt.complete(at=t_complete)
        assert appt.status is AppointmentStatus.COMPLETED
        assert appt.updated_at == t_complete

    def test_complete_from_scheduled_raises(self) -> None:
        appt = _make_appointment()
        with pytest.raises(InvalidTransitionError):
            appt.complete(at=_T_END)

    def test_complete_from_completed_raises(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        appt.complete(at=_T_END)
        with pytest.raises(InvalidTransitionError):
            appt.complete(at=_T_END + timedelta(minutes=5))

    def test_completed_appointment_in_history(self) -> None:
        """A completed appointment is not active."""
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        appt.complete(at=_T_END)
        assert appt.status.is_active() is False


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------

class TestAppointmentCancel:
    """Tests for Appointment.cancel()."""

    def test_cancel_from_scheduled_preserves_reason(self) -> None:
        appt = _make_appointment()
        appt.cancel("Patient request", at=_T_AT)
        assert appt.status is AppointmentStatus.CANCELLED
        assert appt.cancellation_reason == "Patient request"

    def test_cancel_from_checked_in_succeeds(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        appt.cancel("Doctor unavailable", at=_T_AT + timedelta(minutes=5))
        assert appt.status is AppointmentStatus.CANCELLED

    def test_cancel_from_completed_raises(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        appt.complete(at=_T_END)
        with pytest.raises(InvalidTransitionError):
            appt.cancel("Too late", at=_T_END + timedelta(seconds=1))

    def test_cancel_empty_reason_raises(self) -> None:
        appt = _make_appointment()
        with pytest.raises(ValidationError) as exc_info:
            appt.cancel("   ", at=_T_AT)
        assert exc_info.value.safe_details["field"] == "reason"

    def test_cancel_naive_timestamp_raises(self) -> None:
        appt = _make_appointment()
        with pytest.raises(ValidationError):
            appt.cancel("reason", at=datetime(2026, 11, 10, 9, 5))

    def test_cancel_reason_stripped(self) -> None:
        appt = _make_appointment()
        appt.cancel("  Patient request  ", at=_T_AT)
        assert appt.cancellation_reason == "Patient request"


# ---------------------------------------------------------------------------
# mark_no_show
# ---------------------------------------------------------------------------

class TestAppointmentMarkNoShow:
    """Tests for Appointment.mark_no_show()."""

    def test_no_show_from_scheduled_after_slot_end(self) -> None:
        """mark_no_show succeeds for a SCHEDULED appointment."""
        appt = _make_appointment()
        after_end = _T_END + timedelta(minutes=5)
        appt.mark_no_show(at=after_end)
        assert appt.status is AppointmentStatus.NO_SHOW
        assert appt.updated_at == after_end

    def test_no_show_before_slot_end_is_allowed_by_entity(self) -> None:
        """The entity does NOT enforce timing; use case is responsible.

        Calling mark_no_show before slot.end succeeds at the entity level
        because the business rule (at >= slot.end) is enforced by the
        application use case, not the entity.
        """
        appt = _make_appointment()
        before_end = _T_BASE + timedelta(minutes=1)
        appt.mark_no_show(at=before_end)
        assert appt.status is AppointmentStatus.NO_SHOW

    def test_no_show_from_checked_in_raises(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        with pytest.raises(InvalidTransitionError):
            appt.mark_no_show(at=_T_END + timedelta(minutes=1))

    def test_no_show_naive_timestamp_raises(self) -> None:
        appt = _make_appointment()
        with pytest.raises(ValidationError):
            appt.mark_no_show(at=datetime(2026, 11, 10, 9, 35))


# ---------------------------------------------------------------------------
# reschedule
# ---------------------------------------------------------------------------

class TestAppointmentReschedule:
    """Tests for Appointment.reschedule()."""

    def test_reschedule_from_scheduled_succeeds(self) -> None:
        appt = _make_appointment()
        new_slot = TimeSlot(
            start=datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
            end=datetime(2026, 11, 10, 11, 30, tzinfo=UTC),
        )
        t_reschedule = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)
        appt.reschedule(new_slot, at=t_reschedule)
        assert appt.slot == new_slot
        assert appt.updated_at == t_reschedule
        assert appt.status is AppointmentStatus.SCHEDULED

    def test_reschedule_from_checked_in_raises(self) -> None:
        appt = _make_appointment()
        appt.check_in(at=_T_AT)
        new_slot = TimeSlot(
            start=datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
            end=datetime(2026, 11, 10, 11, 30, tzinfo=UTC),
        )
        with pytest.raises(InvalidTransitionError) as exc_info:
            appt.reschedule(new_slot, at=_T_AT)
        assert exc_info.value.code == "INVALID_TRANSITION"

    def test_reschedule_from_cancelled_raises(self) -> None:
        appt = _make_appointment()
        appt.cancel("reason", at=_T_AT)
        new_slot = TimeSlot(
            start=datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
            end=datetime(2026, 11, 10, 11, 30, tzinfo=UTC),
        )
        with pytest.raises(InvalidTransitionError):
            appt.reschedule(new_slot, at=_T_AT)

    def test_reschedule_invalid_slot_type_raises(self) -> None:
        appt = _make_appointment()
        with pytest.raises(ValidationError):
            appt.reschedule("not-a-slot", at=_T_AT)  # type: ignore[arg-type]

    def test_reschedule_naive_timestamp_raises(self) -> None:
        appt = _make_appointment()
        new_slot = TimeSlot(
            start=datetime(2026, 11, 10, 11, 0, tzinfo=UTC),
            end=datetime(2026, 11, 10, 11, 30, tzinfo=UTC),
        )
        with pytest.raises(ValidationError):
            appt.reschedule(new_slot, at=datetime(2026, 11, 9, 10, 0))


# ---------------------------------------------------------------------------
# Entity identity
# ---------------------------------------------------------------------------

class TestAppointmentEntityIdentity:
    """M1 Entity identity semantics for Appointment."""

    def test_same_id_equals(self) -> None:
        aid = uuid4()
        a1 = _make_appointment(id=aid)
        a2 = _make_appointment(id=aid)
        assert a1 == a2

    def test_different_id_not_equal(self) -> None:
        a1 = _make_appointment()
        a2 = _make_appointment()
        assert a1 != a2

    def test_appointment_not_hashable(self) -> None:
        with pytest.raises(TypeError):
            hash(_make_appointment())
