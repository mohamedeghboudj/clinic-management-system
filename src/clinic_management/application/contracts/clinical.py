"""Safe clinical-entry summary DTO for paginated history listings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class ClinicalEntrySummary:
    """Immutable projection of a clinical entry for history index pages.

    This DTO intentionally omits narrative content so that paginated
    history listings never expose clinical detail beyond type, author
    and amendment status.
    """

    entry_id: UUID
    patient_id: UUID
    kind: str
    author_id: UUID
    recorded_at: datetime
    amended: bool

    def __post_init__(self) -> None:
        """Validate identity fields, kind label, and timestamp invariants.

        Raises:
            ValidationError: If any identity field is not a UUID, the kind
                label is empty, or the timestamp is not aware UTC.
        """
        require_uuid(self.entry_id)
        require_uuid(self.patient_id)
        require_uuid(self.author_id)
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.entry_summary.kind.invalid",
            )
        require_utc(self.recorded_at)
        if not isinstance(self.amended, bool):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.entry_summary.amended.invalid",
            )
