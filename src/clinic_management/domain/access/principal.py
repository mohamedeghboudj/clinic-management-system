"""Principal: immutable, server-verified authenticated request context."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.access.enums import Role
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class Principal:
    """Immutable authenticated request context constructed by the server.

    A Principal is only constructed after the server has verified the account,
    session validity, authentication version, and clinic membership.  It must
    never be accepted as trusted data from client-supplied JSON or any other
    untrusted source.

    Attributes:
        account_id: Identifier of the authenticated UserAccount.
        clinic_id: Identifier of the clinic the user is operating within.
        membership_id: Identifier of the active ClinicMembership.
        staff_id: Staff-profile identifier, or None for patient memberships.
        patient_id: Patient identifier, or None for staff memberships.
        roles: Frozen set of roles held by the membership in the clinic.
        auth_version: Authentication version matched against the account at
                      token issuance time.
    """

    account_id: UUID
    clinic_id: UUID
    membership_id: UUID
    staff_id: UUID | None
    patient_id: UUID | None
    roles: frozenset[Role]
    auth_version: int

    def __post_init__(self) -> None:
        """Validate all identifiers, roles, and auth version.

        Raises:
            ValidationError: If any field has an incorrect type or value.
        """
        require_uuid(self.account_id)
        require_uuid(self.clinic_id)
        require_uuid(self.membership_id)

        if self.staff_id is not None:
            require_uuid(self.staff_id)
        if self.patient_id is not None:
            require_uuid(self.patient_id)

        if not isinstance(self.roles, frozenset):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="principal.roles.invalid",
                safe_details={"field": "roles"},
            )
        for r in self.roles:
            if not isinstance(r, Role):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="principal.roles.item_invalid",
                    safe_details={"field": "roles"},
                )

        if type(self.auth_version) is not int or self.auth_version < 1:
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="principal.auth_version.invalid",
                safe_details={"field": "auth_version"},
            )

    def has_role(self, role: Role) -> bool:
        """Return whether this principal holds the given role.

        Args:
            role: The Role to test for.

        Returns:
            True if the role is present in this principal's role set.
        """
        return role in self.roles

