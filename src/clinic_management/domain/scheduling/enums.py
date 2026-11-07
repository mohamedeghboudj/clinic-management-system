"""Appointment status enumeration and transition rules for scheduling."""

from __future__ import annotations

from enum import Enum


class AppointmentStatus(Enum):
    """Lifecycle state of an appointment.

    Valid transitions::

        SCHEDULED  → CHECKED_IN
        SCHEDULED  → NO_SHOW
        SCHEDULED  → CANCELLED
        CHECKED_IN → COMPLETED
        CHECKED_IN → CANCELLED

    States that cannot transition further:
        COMPLETED: Appointment history is immutable after completion.
        NO_SHOW: Terminal state.
        CANCELLED: Terminal state.

    Active reservations are appointments with status SCHEDULED or CHECKED_IN.
    """

    SCHEDULED = "SCHEDULED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

    def is_active(self) -> bool:
        """Return whether this status counts as an active reservation.

        Returns:
            True for SCHEDULED and CHECKED_IN.
        """
        return self in _ACTIVE_STATUSES

    def can_transition_to(self, target: AppointmentStatus) -> bool:
        """Return whether a direct transition to *target* is permitted.

        Args:
            target: The desired next status.

        Returns:
            True if the transition appears in the allowed table.
        """
        return target in _ALLOWED_TRANSITIONS.get(self, frozenset())


_ACTIVE_STATUSES = frozenset({AppointmentStatus.SCHEDULED, AppointmentStatus.CHECKED_IN})

# Forward-reference-safe: populated after the class body is evaluated.
_ALLOWED_TRANSITIONS: dict[AppointmentStatus, frozenset[AppointmentStatus]] = {}


def _init_transitions() -> None:
    S = AppointmentStatus
    _ALLOWED_TRANSITIONS.update(
        {
            S.SCHEDULED: frozenset({S.CHECKED_IN, S.NO_SHOW, S.CANCELLED}),
            S.CHECKED_IN: frozenset({S.COMPLETED, S.CANCELLED}),
            S.COMPLETED: frozenset(),
            S.NO_SHOW: frozenset(),
            S.CANCELLED: frozenset(),
        }
    )


_init_transitions()
