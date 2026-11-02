"""Append-only clinical amendment — an immutable correction record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.clinical.validation import validate_clinical_text
from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.errors import ValidationError

_REASON_MAX_LENGTH: int = 2_000
_CONTENT_MAX_LENGTH: int = 100_000


@dataclass(frozen=True, kw_only=True)
class ClinicalAmendment:
    """Immutable amendment that corrects a previously recorded clinical entry.

    Amendments are append-only: once created they cannot be modified or
    deleted.  They reference the original ``ClinicalEntry`` by its
    ``entry_id`` and carry the corrected content together with a
    mandatory reason for the change.

    Attributes:
        id: Unique amendment identifier.
        clinic_id: Owning clinic.
        patient_id: Patient the amendment belongs to.
        entry_id: Identifier of the original ``ClinicalEntry`` being
            amended.
        author_id: Clinician who authored the amendment.
        reason: Mandatory human-readable reason for the correction.
        replacement_content: Corrected clinical content replacing the
            original entry text.
        recorded_at: UTC instant the amendment was recorded.
    """

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    entry_id: UUID
    author_id: UUID
    reason: str
    replacement_content: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Validate all invariants on construction.

        Raises:
            ValidationError: If any field violates its domain constraint.
        """
        for uid in (
            self.id,
            self.clinic_id,
            self.patient_id,
            self.entry_id,
            self.author_id,
        ):
            require_uuid(uid)

        require_utc(self.recorded_at)

        # --- reason ---
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.amendment.reason.empty",
                safe_details={"field": "reason"},
            )
        stripped_reason = self.reason.strip()
        if len(stripped_reason) > _REASON_MAX_LENGTH:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.amendment.reason.too_long",
                safe_details={
                    "field": "reason",
                    "max_length": str(_REASON_MAX_LENGTH),
                },
            )
        object.__setattr__(self, "reason", stripped_reason)

        # --- replacement_content ---
        validated_content = validate_clinical_text(
            self.replacement_content,
            field="replacement_content",
            max_length=_CONTENT_MAX_LENGTH,
        )
        object.__setattr__(self, "replacement_content", validated_content)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def applies_to(self, entry: ClinicalEntry) -> bool:
        """Check whether this amendment targets the given clinical entry.

        The match requires that the entry identifier, patient identifier,
        and clinic identifier all agree.

        Args:
            entry: The clinical entry to test against.

        Returns:
            ``True`` if all three identifiers match, ``False`` otherwise.
        """
        return (
            self.entry_id == entry.id
            and self.patient_id == entry.patient_id
            and self.clinic_id == entry.clinic_id
        )
