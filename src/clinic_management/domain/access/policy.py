"""ResourceContext and AccessPolicy: server-side authorization enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from clinic_management.domain.access.enums import AccessScope, Permission
from clinic_management.domain.access.grants import RoleGrant
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.shared._invariants import require_uuid
from clinic_management.domain.shared.errors import (
    PermissionDeniedError,
    ValidationError,
)


@dataclass(frozen=True, kw_only=True)
class ResourceContext:
    """Trusted resource information loaded by the server for authorization.

    All facts in a ResourceContext are established by trusted server-side
    queries.  Clients must never be allowed to assert their own clinic
    membership, doctor assignment, patient identity, or available fields.

    Attributes:
        clinic_id: Clinic that owns the resource being accessed.
        patient_id: Identifier of the patient resource, or None.
        assigned_staff_ids: Staff identifiers assigned to the resource (e.g.
                            the doctors or nurses assigned to a patient).
        available_fields: Full set of field names the server has loaded for
                          this resource.  Only fields in this set can ever be
                          returned, regardless of grant permissions.
    """

    clinic_id: UUID
    patient_id: UUID | None
    assigned_staff_ids: frozenset[UUID]
    available_fields: frozenset[str]

    def __post_init__(self) -> None:
        """Validate clinic identifier and collection types.

        Raises:
            ValidationError: If any field has an incorrect type.
        """
        require_uuid(self.clinic_id)
        if self.patient_id is not None:
            require_uuid(self.patient_id)
        if not isinstance(self.assigned_staff_ids, frozenset):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="resource_context.assigned_staff_ids.invalid",
                safe_details={"field": "assigned_staff_ids"},
            )
        if not isinstance(self.available_fields, frozenset):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="resource_context.available_fields.invalid",
                safe_details={"field": "available_fields"},
            )


@dataclass(frozen=True, kw_only=True)
class AccessPolicy:
    """Evaluate authorization decisions using explicit grants.

    Authorization is deny-by-default.  A request is permitted only when at
    least one grant in ``grants`` matches the principal's roles, the requested
    action, the clinic boundary, and the access scope.

    The OWNER role does not receive an automatic bypass for clinical
    information; every access decision depends on a matching explicit grant.

    Attributes:
        grants: Ordered collection of RoleGrant rules for this policy.
    """

    grants: tuple[RoleGrant, ...]

    def __post_init__(self) -> None:
        """Validate that grants is a tuple of RoleGrant instances.

        Raises:
            ValidationError: If grants is not a tuple or contains non-RoleGrant items.
        """
        if not isinstance(self.grants, tuple):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="policy.grants.invalid",
                safe_details={"field": "grants"},
            )
        for g in self.grants:
            if not isinstance(g, RoleGrant):
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="policy.grants.item_invalid",
                    safe_details={"field": "grants"},
                )

    # ------------------------------------------------------------------
    # Public authorization API
    # ------------------------------------------------------------------

    def require(
        self,
        principal: Principal,
        action: Permission,
        resource: ResourceContext,
    ) -> None:
        """Assert that the principal is authorized for the requested action.

        Checks clinic boundary, role membership, permission, and scope.
        Raises ``PermissionDeniedError`` on any failure; never raises a more
        informative error that would leak resource or membership details.

        Args:
            principal: Verified, server-constructed authentication context.
            action: The Permission being requested.
            resource: Trusted server-loaded resource facts.

        Raises:
            PermissionDeniedError: If no grant authorises the request.
        """
        if not self._any_matching_grant(principal, action, resource):
            raise PermissionDeniedError(
                code="PERMISSION_DENIED",
                message_key="access.permission_denied",
            )

    def allowed_fields(
        self,
        principal: Principal,
        action: Permission,
        resource: ResourceContext,
    ) -> frozenset[str]:
        """Return the set of fields the principal may access for this action.

        Only returns fields that are both explicitly authorised by a matching
        grant **and** present in ``resource.available_fields``.  An empty
        result does not imply authorization for any action; callers must invoke
        ``require`` first to confirm the action itself is permitted.

        Args:
            principal: Verified, server-constructed authentication context.
            action: The Permission being evaluated for field-level access.
            resource: Trusted server-loaded resource facts.

        Returns:
            Intersection of grant-authorised fields and available resource fields.
        """
        authorised: set[str] = set()
        for grant in self.grants:
            if self._grant_matches(grant, principal, action, resource):
                authorised.update(grant.fields)
        return frozenset(authorised) & resource.available_fields

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _any_matching_grant(
        self,
        principal: Principal,
        action: Permission,
        resource: ResourceContext,
    ) -> bool:
        """Return True if at least one grant covers this request.

        Args:
            principal: Verified authentication context.
            action: Requested permission.
            resource: Trusted resource facts.

        Returns:
            True if a matching grant exists, False otherwise.
        """
        return any(
            self._grant_matches(grant, principal, action, resource)
            for grant in self.grants
        )

    def _grant_matches(
        self,
        grant: RoleGrant,
        principal: Principal,
        action: Permission,
        resource: ResourceContext,
    ) -> bool:
        """Return True if a single grant covers this principal/action/resource.

        Checks in order: clinic boundary, permission, role membership, scope.

        Args:
            grant: The RoleGrant rule to evaluate.
            principal: Verified authentication context.
            action: Requested permission.
            resource: Trusted resource facts.

        Returns:
            True only when all four conditions are satisfied.
        """
        if not self._clinic_matches(principal, resource):
            return False
        if grant.permission is not action:
            return False
        if grant.role not in principal.roles:
            return False
        return self._scope_matches(grant.scope, principal, resource)

    @staticmethod
    def _clinic_matches(principal: Principal, resource: ResourceContext) -> bool:
        """Return True when the principal and resource share the same clinic.

        Args:
            principal: Verified authentication context.
            resource: Trusted resource facts.

        Returns:
            True if clinic identifiers match.
        """
        return principal.clinic_id == resource.clinic_id

    @staticmethod
    def _scope_matches(
        scope: AccessScope,
        principal: Principal,
        resource: ResourceContext,
    ) -> bool:
        """Return True when the scope condition is satisfied.

        CLINIC: always satisfied within the same clinic (checked separately).
        ASSIGNED: satisfied when the principal's staff_id is in the resource's
                  assigned_staff_ids set.
        OWN: satisfied when the principal's patient_id matches the resource's
             patient_id, or when the principal's staff_id appears in assigned
             (for staff owning their own records).

        Args:
            scope: The AccessScope to evaluate.
            principal: Verified authentication context.
            resource: Trusted resource facts.

        Returns:
            True when the scope condition is met.
        """
        if scope is AccessScope.CLINIC:
            return True
        if scope is AccessScope.ASSIGNED:
            return (
                principal.staff_id is not None
                and principal.staff_id in resource.assigned_staff_ids
            )
        if scope is AccessScope.OWN:
            # Patient-facing own-access
            if (
                principal.patient_id is not None
                and resource.patient_id is not None
                and principal.patient_id == resource.patient_id
            ):
                return True
            # Staff-facing own-access (staff accessing their own assignment)
            return (
                principal.staff_id is not None
                and principal.staff_id in resource.assigned_staff_ids
            )
        return False  # Unknown scope: deny

