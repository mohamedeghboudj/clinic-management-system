"""Lifecycle status enumerations for clinical-care aggregates."""

from __future__ import annotations

from enum import Enum, unique


@unique
class ConsultationStatus(Enum):
    """Lifecycle state of a doctor–patient consultation.

    Attributes:
        DRAFT: The consultation is being composed and may still be edited.
        FINAL: The consultation has been finalized and is read-only.
    """

    DRAFT = "DRAFT"
    FINAL = "FINAL"


@unique
class PrescriptionStatus(Enum):
    """Lifecycle state of a medication prescription.

    Attributes:
        DRAFT: The prescription is being prepared and may be modified.
        ISSUED: The prescription has been signed/issued to the patient.
        CANCELLED: The prescription has been voided with a recorded reason.
    """

    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"
