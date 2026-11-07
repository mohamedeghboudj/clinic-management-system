"""Staff profile domain entity representing a clinic employee."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)
from clinic_management.domain.shared.validation import require_non_empty


@dataclass(eq=False, kw_only=True)
class StaffProfile(Entity):
    """Domain entity representing a person's employment at a specific clinic.

    Attributes:
        id: Unique identifier for this staff profile.
        version: Aggregate root version for optimistic concurrency (defaults to 0).
        clinic_id: Identifier of the clinic employing the staff member.
        person_id: Identifier of the underlying Person entity.
        staff_number: Clinic-scoped unique staff identifier string.
        hired_on: Calendar date of hiring.
        active: Whether this staff member is currently active.
    """

    id: UUID
    version: int = 0
    clinic_id: UUID
    person_id: UUID
    staff_number: str
    hired_on: date
    active: bool = True

    def __post_init__(self) -> None:
        """Validate local invariants and identifier formats.

        Raises:
            ValidationError: If any identifier, staff number, version, or date is invalid.
        """
        require_uuid(self.id)
        require_uuid(self.clinic_id)
        require_uuid(self.person_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="staff.version.invalid",
                safe_details={"field": "version"},
            )

        clean_number = require_non_empty(
            self.staff_number,
            field="staff_number",
            max_length=50,
        )

        if not isinstance(self.hired_on, date) or isinstance(self.hired_on, bool):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="staff.hired_on.invalid",
                safe_details={"field": "hired_on"},
            )

        if type(self.active) is not bool:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="staff.active.invalid",
                safe_details={"field": "active"},
            )

        object.__setattr__(self, "staff_number", clean_number)

    def activate(self) -> None:
        """Mark this staff profile as active.

        Raises:
            InvalidTransitionError: If the staff profile is already active.
        """
        if self.active:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="staff.already_active",
                safe_details={"staff_id": str(self.id)},
            )
        self.active = True

    def deactivate(self) -> None:
        """Mark this staff profile as inactive.

        Raises:
            InvalidTransitionError: If the staff profile is already inactive.
        """
        if not self.active:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="staff.already_inactive",
                safe_details={"staff_id": str(self.id)},
            )
        self.active = False

