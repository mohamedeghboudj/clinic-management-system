"""Repository ports for Person, Patient, StaffProfile, and DoctorProfile entities."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING
from uuid import UUID

from clinic_management.domain.people.doctor_profile import DoctorProfile
from clinic_management.domain.people.patient import Patient
from clinic_management.domain.people.person import Person
from clinic_management.domain.people.staff_profile import StaffProfile

if TYPE_CHECKING:
    from clinic_management.application.contracts.paging import Page, PageRequest
    from clinic_management.application.contracts.people import PatientSummary


class PersonRepository(abc.ABC):
    """Abstract repository for Person entities.

    PersonRepository.get must only expose a person who has a Patient or
    StaffProfile relationship in the supplied clinic. Adding a Person alone
    does not grant visibility.
    """

    @abc.abstractmethod
    def get(self, clinic_id: UUID, person_id: UUID) -> Person | None:
        """Retrieve a Person visible through a clinic relationship.

        Args:
            clinic_id: The clinic scoping the visibility check.
            person_id: The unique identifier of the Person.

        Returns:
            The Person entity, or None if not visible in this clinic.
        """

    @abc.abstractmethod
    def add(self, person: Person) -> None:
        """Persist a new Person entity.

        Args:
            person: The Person to add.

        Raises:
            ConflictError: If a Person with the same ID already exists.
        """

    @abc.abstractmethod
    def save(self, person: Person, *, expected_version: int) -> None:
        """Persist changes to an existing Person entity.

        Args:
            person: The Person with updated state.
            expected_version: The version the caller read; used for optimistic
                              concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match expected_version.
            NotFoundError: If no Person with this ID exists.
        """


class PatientRepository(abc.ABC):
    """Abstract repository for Patient entities."""

    @abc.abstractmethod
    def get(self, clinic_id: UUID, patient_id: UUID) -> Patient | None:
        """Retrieve a Patient by clinic and patient identifiers.

        Args:
            clinic_id: Clinic scoping the lookup.
            patient_id: The unique identifier of the Patient.

        Returns:
            The Patient entity, or None if not found.
        """

    @abc.abstractmethod
    def add(self, patient: Patient) -> None:
        """Persist a new Patient entity.

        Args:
            patient: The Patient to add.

        Raises:
            ConflictError: If a Patient with the same ID already exists.
        """

    @abc.abstractmethod
    def save(self, patient: Patient, *, expected_version: int) -> None:
        """Persist changes to an existing Patient entity.

        Args:
            patient: The Patient with updated state.
            expected_version: Version for optimistic concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match expected_version.
            NotFoundError: If no Patient with this ID exists.
        """

    @abc.abstractmethod
    def search(
        self,
        clinic_id: UUID,
        query: str,
        page: PageRequest,
    ) -> Page[PatientSummary]:
        """Search patients within a clinic and return a paginated summary.

        Args:
            clinic_id: Clinic to search within.
            query: Search text to match against patient name or number.
            page: Pagination parameters.

        Returns:
            A page of matching PatientSummary DTOs.
        """


class StaffRepository(abc.ABC):
    """Abstract repository for StaffProfile and DoctorProfile entities."""

    @abc.abstractmethod
    def get(self, clinic_id: UUID, staff_id: UUID) -> StaffProfile | None:
        """Retrieve a StaffProfile by clinic and staff identifiers.

        Args:
            clinic_id: Clinic scoping the lookup.
            staff_id: The unique identifier of the StaffProfile.

        Returns:
            The StaffProfile entity, or None if not found.
        """

    @abc.abstractmethod
    def get_doctor(self, clinic_id: UUID, doctor_id: UUID) -> DoctorProfile | None:
        """Retrieve a DoctorProfile by clinic and doctor identifiers.

        Args:
            clinic_id: Clinic scoping the lookup.
            doctor_id: The unique identifier of the DoctorProfile.

        Returns:
            The DoctorProfile entity, or None if not found.
        """

    @abc.abstractmethod
    def add(self, staff: StaffProfile) -> None:
        """Persist a new StaffProfile entity.

        Args:
            staff: The StaffProfile to add.

        Raises:
            ConflictError: If a StaffProfile with the same ID already exists.
        """

    @abc.abstractmethod
    def add_doctor(self, doctor: DoctorProfile) -> None:
        """Persist a new DoctorProfile entity.

        Args:
            doctor: The DoctorProfile to add.

        Raises:
            ConflictError: If a DoctorProfile with the same ID already exists.
        """

    @abc.abstractmethod
    def save(self, staff: StaffProfile, *, expected_version: int) -> None:
        """Persist changes to an existing StaffProfile entity.

        Args:
            staff: The StaffProfile with updated state.
            expected_version: Version for optimistic concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match expected_version.
            NotFoundError: If no StaffProfile with this ID exists.
        """

    @abc.abstractmethod
    def save_doctor(self, doctor: DoctorProfile, *, expected_version: int) -> None:
        """Persist changes to an existing DoctorProfile entity.

        Args:
            doctor: The DoctorProfile with updated state.
            expected_version: Version for optimistic concurrency control.

        Raises:
            ConcurrencyError: If the stored version does not match expected_version.
            NotFoundError: If no DoctorProfile with this ID exists.
        """
