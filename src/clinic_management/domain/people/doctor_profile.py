"""Doctor profile domain entity representing a doctor associated with a staff profile."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(eq=False, kw_only=True)
class DoctorProfile(Entity):
    """Domain entity representing a doctor associated with a staff profile at a clinic.

    Attributes:
        id: Unique identifier for this doctor profile.
        version: Aggregate root version for optimistic concurrency (defaults to 0).
        clinic_id: Identifier of the clinic.
        staff_id: Identifier of the associated StaffProfile entity.
        specialty: Medical specialty of the doctor (e.g., Cardiology, General Practice).
        licence_number: Medical licence identifier string.
        active: Whether this doctor profile is currently active.
    """

    id: UUID
    version: int = 0
    clinic_id: UUID
    staff_id: UUID
    specialty: str
    licence_number: str
    active: bool = True

    def __post_init__(self) -> None:
        """Validate local invariants and identifier formats.

        Raises:
            ValidationError: If identifiers, strings, version, or active status are invalid.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)
        require_uuid(self.staff_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="doctor.version.invalid",
                safe_details={"field": "version"},
            )

        clean_specialty = require_non_empty(
            self.specialty,
            field="specialty",
            max_length=100,
        )
        clean_licence = require_non_empty(
            self.licence_number,
            field="licence_number",
            max_length=50,
        )

        if type(self.active) is not bool:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="doctor.active.invalid",
                safe_details={"field": "active"},
            )

        object.__setattr__(self, "specialty", clean_specialty)
        object.__setattr__(self, "licence_number", clean_licence)

    def activate(self) -> None:
        """Mark this doctor profile as active.

        Raises:
            InvalidTransitionError: If the doctor profile is already active.
        """
        if self.active:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="doctor.already_active",
                safe_details={"doctor_id": str(self.id)},
            )
        self.active = True

    def deactivate(self) -> None:
        """Mark this doctor profile as inactive.

        Raises:
            InvalidTransitionError: If the doctor profile is already inactive.
        """
        if not self.active:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="doctor.already_inactive",
                safe_details={"doctor_id": str(self.id)},
            )
        self.active = False

