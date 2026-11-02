"""ClinicMembership domain entity connecting an account to a clinic with roles."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from clinic_management.domain.access.enums import Role
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    ValidationError,
)


@dataclass(eq=False, kw_only=True)
class ClinicMembership(Entity):
    """Domain entity connecting a user account to a specific clinic with roles.

    Membership is the authoritative source of a user's roles within a clinic.
    A patient membership is reserved for future patient-facing access and does
    not carry staff roles.

    Attributes:
        id: Unique identifier for this membership record.
        version: Aggregate root version for optimistic concurrency (defaults to 0).
        account_id: Identifier of the associated UserAccount.
        clinic_id: Identifier of the clinic this membership belongs to.
        staff_id: Optional staff-profile identifier (for staff memberships).
        patient_id: Optional patient identifier (for patient memberships).
        roles: Frozen set of roles held by this membership within the clinic.
        active: Whether the membership is currently active.
    """

    id: UUID
    version: int = 0
    account_id: UUID
    clinic_id: UUID
    staff_id: UUID | None = None
    patient_id: UUID | None = None
    roles: frozenset[Role] = field(default_factory=frozenset)
    active: bool = True

    def __post_init__(self) -> None:
        """Validate all identifiers, version, and structural constraints.

        Raises:
            ValidationError: If any identifier, version, roles, or active flag is invalid.
        """
        require_uuid(self.id)
        require_uuid(self.account_id)
        require_uuid(self.clinic_id)

        if self.staff_id is not None:
            require_uuid(self.staff_id)
        if self.patient_id is not None:
            require_uuid(self.patient_id)

        if type(self.version) is not int or self.version < 0:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="membership.version.invalid",
                safe_details={"field": "version"},
            )

        if not isinstance(self.roles, frozenset):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="membership.roles.invalid",
                safe_details={"field": "roles"},
            )
        for r in self.roles:
            if not isinstance(r, Role):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="membership.roles.item_invalid",
                    safe_details={"field": "roles"},
                )

        if type(self.active) is not bool:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="membership.active.invalid",
                safe_details={"field": "active"},
            )

    def grant_role(self, role: Role) -> None:
        """Add a role to this membership.

        Role changes must be authorised by an application use case; the domain
        model only enforces structural validity.

        Args:
            role: The Role to add to this membership.

        Raises:
            ValidationError: If the supplied value is not a Role instance.
        """
        if not isinstance(role, Role):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="membership.roles.item_invalid",
                safe_details={"field": "role"},
            )
        self.roles = self.roles | frozenset([role])

    def revoke_role(self, role: Role) -> None:
        """Remove a role from this membership.

        Args:
            role: The Role to remove from this membership.

        Raises:
            ValidationError: If the supplied value is not a Role instance.
        """
        if not isinstance(role, Role):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="membership.roles.item_invalid",
                safe_details={"field": "role"},
            )
        self.roles = self.roles - frozenset([role])

    def deactivate(self) -> None:
        """Deactivate this membership.

        Raises:
            InvalidTransitionError: If the membership is already inactive.
        """
        if not self.active:
            raise InvalidTransitionError(
                code="INVALID_TRANSITION",
                message_key="membership.already_inactive",
                safe_details={"membership_id": str(self.id)},
            )
        self.active = False

