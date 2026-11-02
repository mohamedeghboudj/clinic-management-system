"""Prescription aggregate with draft / issued / cancelled lifecycle."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from uuid import UUID

from clinic_management.domain.clinical.enums import PrescriptionStatus
from clinic_management.domain.clinical.medication import Medication
from clinic_management.domain.shared._invariants import require_utc, require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)


def _validate_non_empty_str(value: str, *, field_name: str) -> str:
    """Strip and validate that a string field is non-empty.

    Args:
        value: Raw string to validate.
        field_name: Logical field name for error details.

    Returns:
        The stripped string.

    Raises:
        ValidationError: If the value is not a non-empty string.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            code="INVALID_VALUE",
            message_key=f"clinical.prescription_item.{field_name}.empty",
            safe_details={"field": field_name},
        )
    return value.strip()


@dataclass(frozen=True, kw_only=True)
class PrescriptionItem:
    """Immutable value object representing a single medication line item.

    Attributes:
        medication: The prescribed medication.
        dose: Dosage amount (e.g. ``"1 tablet"``).
        route: Route of administration (e.g. ``"oral"``).
        frequency: Dosing frequency (e.g. ``"twice daily"``).
        duration: Treatment duration (e.g. ``"7 days"``).
        instructions: Optional free-text patient instructions.
    """

    medication: Medication
    dose: str
    route: str
    frequency: str
    duration: str
    instructions: str | None = None

    def __post_init__(self) -> None:
        """Validate all item fields.

        Raises:
            ValidationError: If any required field is empty or the
                medication is not a ``Medication`` instance.
        """
        if not isinstance(self.medication, Medication):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.prescription_item.medication.invalid",
                safe_details={"field": "medication"},
            )

        object.__setattr__(
            self, "dose", _validate_non_empty_str(self.dose, field_name="dose"),
        )
        object.__setattr__(
            self, "route", _validate_non_empty_str(self.route, field_name="route"),
        )
        object.__setattr__(
            self,
            "frequency",
            _validate_non_empty_str(self.frequency, field_name="frequency"),
        )
        object.__setattr__(
            self,
            "duration",
            _validate_non_empty_str(self.duration, field_name="duration"),
        )

        if self.instructions is not None:
            if not isinstance(self.instructions, str) or not self.instructions.strip():
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="clinical.prescription_item.instructions.empty",
                    safe_details={"field": "instructions"},
                )
            object.__setattr__(self, "instructions", self.instructions.strip())


@dataclass(eq=False, kw_only=True)
class Prescription(Entity):
    """Mutable aggregate representing a medication prescription.

    A prescription begins in ``DRAFT`` status and may have items added
    or removed.  Once it contains at least one item it can be issued.
    A draft or issued prescription may be cancelled with a mandatory
    reason.

    Attributes:
        id: Unique prescription identifier.
        clinic_id: Owning clinic.
        patient_id: Patient receiving the prescription.
        doctor_id: Prescribing physician.
        consultation_id: Associated consultation, if any.
        status: Current lifecycle status.
        issued_at: UTC instant the prescription was issued, or ``None``.
        cancel_reason: Human-readable cancellation reason, or ``None``.
        cancelled_at: UTC instant the prescription was cancelled, or
            ``None``.
        version: Optimistic-concurrency version counter.
    """

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    consultation_id: UUID | None = None
    status: PrescriptionStatus = PrescriptionStatus.DRAFT
    issued_at: datetime | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    version: int = 0
    _items: list[PrescriptionItem] = field(
        init=False, default_factory=list, repr=False,
    )

    def __init__(
        self,
        *,
        id: UUID,
        clinic_id: UUID,
        patient_id: UUID,
        doctor_id: UUID,
        consultation_id: UUID | None = None,
        items: Sequence[PrescriptionItem] = (),
        status: PrescriptionStatus = PrescriptionStatus.DRAFT,
        issued_at: datetime | None = None,
        cancel_reason: str | None = None,
        cancelled_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        """Initialize and validate a prescription aggregate and its line items.

        Args:
            id: Unique identifier for the prescription.
            clinic_id: Scoped clinic identifier.
            patient_id: Target patient identifier.
            doctor_id: Authoring doctor identifier.
            consultation_id: Optional linked consultation identifier.
            items: Sequence of prescription items to copy defensively.
            status: Initial lifecycle status.
            issued_at: Aware UTC instant if already issued.
            cancel_reason: Reason if already cancelled.
            cancelled_at: Aware UTC instant if already cancelled.
            version: Optimistic concurrency version counter.

        Raises:
            ValidationError: If any identifier, time or status is invalid.
        """
        self.id = id
        self.clinic_id = clinic_id
        self.patient_id = patient_id
        self.doctor_id = doctor_id
        self.consultation_id = consultation_id
        self.status = status
        self.issued_at = issued_at
        self.cancel_reason = cancel_reason
        self.cancelled_at = cancelled_at
        self.version = version
        self._items = []

        for uid in (self.id, self.clinic_id, self.patient_id, self.doctor_id):
            require_uuid(uid)

        if self.consultation_id is not None:
            require_uuid(self.consultation_id)

        if self.issued_at is not None:
            require_utc(self.issued_at)

        if self.cancelled_at is not None:
            require_utc(self.cancelled_at)

        if not isinstance(self.status, PrescriptionStatus):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.prescription.status.invalid",
            )

        for item in items:
            if not isinstance(item, PrescriptionItem):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="clinical.prescription.item.invalid",
                )
            self._items.append(item)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def items(self) -> tuple[PrescriptionItem, ...]:
        """Return a snapshot of the current prescription items.

        Returns:
            An immutable tuple of ``PrescriptionItem`` instances.
        """
        return tuple(self._items)

    def get_items(self) -> tuple[PrescriptionItem, ...]:
        """Return a snapshot of the current prescription items.

        Returns:
            An immutable tuple of ``PrescriptionItem`` instances.
        """
        return self.items()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def add_item(self, item: PrescriptionItem) -> None:
        """Append a line item to the prescription.

        Args:
            item: The prescription item to add.

        Raises:
            InvalidTransitionError: If the prescription is not in
                ``DRAFT`` status.
            ValidationError: If *item* is not a ``PrescriptionItem``.
        """
        self._require_draft("add_item")
        if not isinstance(item, PrescriptionItem):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.prescription.item.invalid",
            )
        self._items.append(item)

    def remove_item(self, index: int) -> None:
        """Remove a line item by its zero-based index.

        Args:
            index: Position of the item to remove.

        Raises:
            InvalidTransitionError: If the prescription is not in
                ``DRAFT`` status.
            ValidationError: If *index* is out of range.
        """
        self._require_draft("remove_item")
        if index < 0 or index >= len(self._items):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.prescription.item.index_out_of_range",
                safe_details={"index": str(index)},
            )
        del self._items[index]

    def issue(self, *, at: datetime) -> None:
        """Issue the prescription so that it may be dispensed.

        The prescription must be in ``DRAFT`` status and contain at
        least one item.

        Args:
            at: UTC instant of issuance.

        Raises:
            InvalidTransitionError: If the prescription is not in
                ``DRAFT`` status.
            ValidationError: If there are no items.
        """
        self._require_draft("issue")
        require_utc(at)
        if not self._items:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.prescription.issue.no_items",
            )
        self.status = PrescriptionStatus.ISSUED
        self.issued_at = at
        self.version += 1

    def cancel(self, reason: str, *, at: datetime) -> None:
        """Cancel the prescription with a mandatory reason.

        A prescription may be cancelled from either ``DRAFT`` or
        ``ISSUED`` status.

        Args:
            reason: Human-readable reason for cancellation.
            at: UTC instant of cancellation.

        Raises:
            InvalidTransitionError: If the prescription has already been
                cancelled.
            ValidationError: If *reason* is empty.
        """
        if self.status is PrescriptionStatus.CANCELLED:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="clinical.prescription.cancel.already_cancelled",
            )
        require_utc(at)
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.prescription.cancel_reason.empty",
                safe_details={"field": "cancel_reason"},
            )
        self.status = PrescriptionStatus.CANCELLED
        self.cancel_reason = reason.strip()
        self.cancelled_at = at
        self.version += 1

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_draft(self, operation: str) -> None:
        """Guard that the prescription is still in ``DRAFT`` status.

        Args:
            operation: Name of the attempted operation for the error key.

        Raises:
            InvalidTransitionError: If the status is not ``DRAFT``.
        """
        if self.status is not PrescriptionStatus.DRAFT:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key=f"clinical.prescription.{operation}.not_draft",
            )
