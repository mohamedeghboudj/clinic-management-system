"""Abstract repository ports for the scheduling domain.

These interfaces define the data-access contract that use cases depend on.
They are implemented by infrastructure adapters (Week 2+).

The ``AppointmentRepository.find_overlaps`` query is advisory: it does not
prevent concurrent database races.  Applications requiring strong conflict
prevention must use database-level locking in addition to this check.
"""

from __future__ import annotations

import abc
from datetime import date
from uuid import UUID

from clinic_management.application.ports.pagination import Page, PageRequest
from clinic_management.application.contracts.scheduling import AppointmentSummary
from clinic_management.domain.scheduling.appointment import Appointment
from clinic_management.domain.shared.time_slot import TimeSlot


class AppointmentRepository(abc.ABC):
    """Abstract repository for ``Appointment`` aggregate roots.

    All queries are scoped to a clinic to prevent cross-clinic data leaks.
    """

    @abc.abstractmethod
    def get(self, clinic_id: UUID, appointment_id: UUID) -> Appointment | None:
        """Retrieve an appointment by clinic and appointment identifiers.

        Args:
            clinic_id: Clinic that owns the appointment.
            appointment_id: Unique appointment identifier.

        Returns:
            The ``Appointment`` entity, or ``None`` if not found.
        """

    @abc.abstractmethod
    def add(self, appointment: Appointment) -> None:
        """Persist a new appointment.

        Args:
            appointment: The new ``Appointment`` to store.

        Raises:
            ConflictError: If an appointment with the same ID already exists.
        """

    @abc.abstractmethod
    def save(self, appointment: Appointment, *, expected_version: int) -> None:
        """Persist changes to an existing appointment.

        Args:
            appointment: The ``Appointment`` with updated state.
            expected_version: The version the caller read; used for optimistic
                concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match.
            NotFoundError: If no appointment with this ID exists.
        """

    @abc.abstractmethod
    def find_overlaps(
        self,
        clinic_id: UUID,
        slot: TimeSlot,
        *,
        doctor_id: UUID | None,
        room_id: UUID | None,
        exclude_id: UUID | None = None,
    ) -> tuple[Appointment, ...]:
        """Return active appointments that overlap *slot* for the given resource(s).

        At least one of *doctor_id* or *room_id* must be supplied.  When both
        are provided, the query returns conflicts for the doctor **or** the
        room (union semantics).

        Only appointments with status SCHEDULED or CHECKED_IN count as
        conflicts.  Results are bounded to the requested ``TimeSlot``.

        This lookup is advisory.  It does not prevent concurrent double-booking
        at the database level.

        Args:
            clinic_id: Clinic scope for the query.
            slot: The time interval to check for overlaps.
            doctor_id: If supplied, include conflicts for this doctor.
            room_id: If supplied, include conflicts for this room.
            exclude_id: Appointment ID to exclude from results (useful when
                rescheduling so the existing appointment is not flagged).

        Returns:
            Tuple of overlapping active appointments.

        Raises:
            ValidationError: If neither *doctor_id* nor *room_id* is supplied.
        """

    @abc.abstractmethod
    def list_for_doctor(
        self,
        clinic_id: UUID,
        doctor_id: UUID,
        day: date,
        page: PageRequest,
    ) -> Page[AppointmentSummary]:
        """Return a paginated list of appointments for a doctor on a specific day.

        Results are ordered chronologically within the day and scoped to the
        clinic.

        Args:
            clinic_id: Clinic scope for the query.
            doctor_id: Doctor whose appointments to list.
            day: Calendar date (clinic-local) to filter by.
            page: Pagination parameters.

        Returns:
            A page of ``AppointmentSummary`` DTOs.
        """
