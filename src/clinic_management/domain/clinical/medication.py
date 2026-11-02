"""Medication value object used within prescription items."""

from __future__ import annotations

from dataclasses import dataclass

from clinic_management.domain.shared.errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class Medication:
    """Immutable value object describing a pharmaceutical product.

    Attributes:
        name: Non-empty medication name (e.g. ``"Amoxicillin"``).
        strength: Optional dosage strength (e.g. ``"500 mg"``).
        form: Optional pharmaceutical form (e.g. ``"tablet"``).
    """

    name: str
    strength: str | None = None
    form: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalise medication fields.

        Raises:
            ValidationError: If the name is empty or optional fields
                contain only whitespace.
        """
        # --- name ---
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="clinical.medication.name.empty",
                safe_details={"field": "name"},
            )
        object.__setattr__(self, "name", self.name.strip())

        # --- strength ---
        if self.strength is not None:
            if not isinstance(self.strength, str) or not self.strength.strip():
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="clinical.medication.strength.empty",
                    safe_details={"field": "strength"},
                )
            object.__setattr__(self, "strength", self.strength.strip())

        # --- form ---
        if self.form is not None:
            if not isinstance(self.form, str) or not self.form.strip():
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="clinical.medication.form.empty",
                    safe_details={"field": "form"},
                )
            object.__setattr__(self, "form", self.form.strip())
