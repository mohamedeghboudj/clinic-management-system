"""RoleGrant value object: one explicit policy rule binding role, permission, scope, and fields."""

from __future__ import annotations

from dataclasses import dataclass

from clinic_management.domain.access.enums import AccessScope, Permission, Role
from clinic_management.domain.shared.errors import ValidationError


@dataclass(frozen=True, kw_only=True)
class RoleGrant:
    """Immutable policy rule that associates a role with a permission and scope.

    A grant represents a single authorisation rule.  The ``fields`` set limits
    which data fields are accessible under this grant.  An empty ``fields`` set
    is **not** a wildcard; it means no fields are authorised for field-level
    access.  Permissions that do not operate on individual data fields must use
    an explicit action-only rule with an empty ``fields`` set.

    Attributes:
        role: The Role to which this grant applies.
        permission: The Permission being granted.
        scope: The AccessScope that restricts which resources are covered.
        fields: Frozen set of field names authorised under this grant.
    """

    role: Role
    permission: Permission
    scope: AccessScope
    fields: frozenset[str]

    def __post_init__(self) -> None:
        """Validate that all grant components are the expected types.

        Raises:
            ValidationError: If role, permission, scope, or fields have wrong types.
        """
        if not isinstance(self.role, Role):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="grant.role.invalid",
                safe_details={"field": "role"},
            )
        if not isinstance(self.permission, Permission):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="grant.permission.invalid",
                safe_details={"field": "permission"},
            )
        if not isinstance(self.scope, AccessScope):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="grant.scope.invalid",
                safe_details={"field": "scope"},
            )
        if not isinstance(self.fields, frozenset):
            raise ValidationError(
                code="INVALID_VALUE",
                message_key="grant.fields.invalid",
                safe_details={"field": "fields"},
            )
        for item in self.fields:
            if not isinstance(item, str) or not item.strip():
                raise ValidationError(
                    code="INVALID_VALUE",
                    message_key="grant.fields.item_invalid",
                    safe_details={"field": "fields"},
                )

