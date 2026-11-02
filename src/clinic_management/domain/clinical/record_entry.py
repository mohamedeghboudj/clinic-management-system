"""Append-only clinical record entry — an immutable history fact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.clinical.validation import validate_clinical_text
from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.errors import ValidationError

_CONTENT_MAX_LENGTH: int = 100_000
_KIND_MAX_LENGTH: int = 100


@dataclass(frozen=True, kw_only=True)
class ClinicalEntry:
    """Immutable clinical record entry written once and never mutated.

    ``ClinicalEntry`` is an append-only historical fact.  Because it is
    immutable after creation it is modelled as a frozen dataclass with
    its own ``id`` rather than as a mutable ``Entity`` subclass.

    Attributes:
        id: Unique entry identifier.
        clinic_id: Owning clinic.
        patient_id: Patient the entry belongs to.
        consultation_id: Associated consultation, if any.
        author_id: Clinician who authored the entry.
        kind: Entry classification tag (e.g. ``"examination"``,
            ``"lab_result"``).
        content: Free-text clinical content.
        recorded_at: UTC instant the entry was recorded.
    """

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    consultation_id: UUID | None
    author_id: UUID
    kind: str
    content: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Validate all invariants on construction.

        Raises:
            ValidationError: If any field violates its domain constraint.
        """
        for uid in (self.id, self.clinic_id, self.patient_id, self.author_id):
            require_uuid(uid)

        if self.consultation_id is not None:
            require_uuid(self.consultation_id)

        require_utc(self.recorded_at)

        # --- kind ---
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.entry.kind.empty",
                safe_details={"field": "kind"},
            )
        object.__setattr__(self, "kind", self.kind.strip())

        if len(self.kind) > _KIND_MAX_LENGTH:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.entry.kind.too_long",
                safe_details={"field": "kind", "max_length": str(_KIND_MAX_LENGTH)},
            )

        # --- content ---
        validated_content = validate_clinical_text(
            self.content,
            field="content",
            max_length=_CONTENT_MAX_LENGTH,
        )
        object.__setattr__(self, "content", validated_content)
