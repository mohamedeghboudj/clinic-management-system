"""Doctor–patient consultation aggregate with draft/final lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.clinical.enums import ConsultationStatus
from clinic_management.domain.clinical.validation import validate_clinical_text
from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)

_NOTE_MAX_LENGTH: int = 50_000


@dataclass(eq=False, kw_only=True)
class Consultation(Entity):
    """Mutable aggregate capturing a single clinical consultation.

    A consultation starts in ``DRAFT`` status, allowing the doctor to
    compose and revise the clinical note.  Once the note is satisfactory
    the consultation is finalized, after which its content becomes
    immutable.

    Attributes:
        id: Unique consultation identifier.
        clinic_id: Owning clinic identifier.
        patient_id: Patient being consulted.
        appointment_id: Linked scheduling appointment.
        doctor_id: Attending physician.
        note: Free-text clinical note.
        status: Current lifecycle status.
        created_at: UTC instant the consultation was created.
        updated_at: UTC instant of the most recent modification.
        finalized_at: UTC instant the consultation was finalized, or
            ``None`` while still in draft.
        version: Optimistic-concurrency version counter.
    """

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    appointment_id: UUID
    doctor_id: UUID
    note: str
    created_at: datetime
    updated_at: datetime
    status: ConsultationStatus = ConsultationStatus.DRAFT
    finalized_at: datetime | None = None
    version: int = 0

    def __post_init__(self) -> None:
        """Validate all invariants on construction.

        Raises:
            ValidationError: If any field violates its domain constraint.
        """
        for uid in (
            self.id,
            self.clinic_id,
            self.patient_id,
            self.appointment_id,
            self.doctor_id,
        ):
            require_uuid(uid)

        require_utc(self.created_at)
        require_utc(self.updated_at)

        if self.finalized_at is not None:
            require_utc(self.finalized_at)

        self.note = validate_clinical_text(
            self.note,
            field="note",
            max_length=_NOTE_MAX_LENGTH,
        )

        if not isinstance(self.status, ConsultationStatus):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.consultation.status.invalid",
            )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def update_note(self, note: str, *, at: datetime) -> None:
        """Replace the clinical note while the consultation is still a draft.

        Args:
            note: New note content (will be stripped and validated).
            at: UTC instant of the update.

        Raises:
            InvalidTransitionError: If the consultation has already been
                finalized.
        """
        if self.status is not ConsultationStatus.DRAFT:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="clinical.consultation.update_note.not_draft",
            )
        require_utc(at)
        self.note = validate_clinical_text(
            note,
            field="note",
            max_length=_NOTE_MAX_LENGTH,
        )
        self.updated_at = at

    def finalize(self, *, at: datetime) -> None:
        """Transition the consultation from ``DRAFT`` to ``FINAL``.

        The note must be non-empty (guaranteed by construction), and the
        consultation must currently be in ``DRAFT`` status.

        Args:
            at: UTC instant of finalization.

        Raises:
            InvalidTransitionError: If the consultation is already
                finalized.
        """
        if self.status is not ConsultationStatus.DRAFT:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="clinical.consultation.finalize.not_draft",
            )
        require_utc(at)
        self.status = ConsultationStatus.FINAL
        self.finalized_at = at
        self.updated_at = at
        self.version += 1
