"""People-domain DTOs: PatientSummary."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class PatientSummary:
    """Lightweight read model for patient list and search results.

    This DTO is used for read-side queries and search results.  Actual
    database querying, joining, and mapping are Week 2 responsibilities.

    Attributes:
        patient_id: Unique identifier of the Patient entity.
        patient_number: Clinic-scoped unique patient identifier string.
        display_name: Human-readable name for the patient (e.g. full name).
        phone: Optional phone number for the patient, or None.
        version: Optimistic concurrency version of the Patient entity.
    """

    patient_id: UUID
    patient_number: str
    display_name: str
    phone: str | None
    version: int

    def __post_init__(self) -> None:
        """Validate all fields on construction.

        Raises:
            ValidationError: If patient_id, strings, or version are invalid.
        """
        require_uuid(self.patient_id)

        if not isinstance(self.patient_number, str) or not self.patient_number.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="patient_summary.patient_number.invalid",
                safe_details={"field": "patient_number"},
            )
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="patient_summary.display_name.invalid",
                safe_details={"field": "display_name"},
            )
        if self.phone is not None and (
            not isinstance(self.phone, str) or not self.phone.strip()
        ):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="patient_summary.phone.invalid",
                safe_details={"field": "phone"},
            )
        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="patient_summary.version.invalid",
                safe_details={"field": "version"},
            )

