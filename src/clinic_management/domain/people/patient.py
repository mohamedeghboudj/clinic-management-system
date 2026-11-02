"""Patient domain entity representing a person registered at a specific clinic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(eq=False, kw_only=True)
class Patient(Entity):
    """Domain entity representing a person's registration at a clinic.

    Attributes:
        id: Unique identifier for this patient record.
        version: Aggregate root version for optimistic concurrency (defaults to 0).
        clinic_id: Identifier of the clinic where the patient is registered.
        person_id: Identifier of the underlying Person entity.
        patient_number: Clinic-scoped unique patient identifier string.
        emergency_contact: Optional emergency contact channels.
        archived_at: UTC timestamp when the patient was archived, or None if active.
    """

    id: UUID
    version: int = 0
    clinic_id: UUID
    person_id: UUID
    patient_number: str
    emergency_contact: ContactInfo | None = None
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate local invariants and identifier formats.

        Raises:
            ValidationError: If any identifier, number, version, or timestamp is invalid.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)
        require_uuid(self.person_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="patient.version.invalid",
                safe_details={"field": "version"},
            )

        clean_number = require_non_empty(
            self.patient_number,
            field="patient_number",
            max_length=50,
        )

        if self.emergency_contact is not None and not isinstance(
            self.emergency_contact, ContactInfo
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="patient.emergency_contact.invalid",
                safe_details={"field": "emergency_contact"},
            )

        if self.archived_at is not None:
            require_utc(self.archived_at)

        object.__setattr__(self, "patient_number", clean_number)

    def is_active(self) -> bool:
        """Return whether the patient record is currently active.

        Returns:
            True if the patient is not archived, False otherwise.
        """
        return self.archived_at is None

    def archive(self, *, at: datetime) -> None:
        """Archive an active patient record at the specified UTC timestamp.

        Args:
            at: Aware UTC timestamp when the archival takes place.

        Raises:
            ValidationError: If ``at`` is naive or has a non-zero UTC offset.
            InvalidTransitionError: If the patient is already archived.
        """
        require_utc(at)

        if not self.is_active():
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="patient.already_archived",
                safe_details={"patient_id": str(self.id)},
            )

        self.archived_at = at

    def restore(self) -> None:
        """Restore an archived patient record back to active status.

        Raises:
            InvalidTransitionError: If the patient is not currently archived.
        """
        if self.is_active():
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="patient.not_archived",
                safe_details={"patient_id": str(self.id)},
            )

        self.archived_at = None

