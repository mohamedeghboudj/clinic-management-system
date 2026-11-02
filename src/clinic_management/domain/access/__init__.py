"""Access domain package: roles, permissions, scopes, and grants."""

from clinic_management.domain.access.enums import AccessScope, Permission, Role
from clinic_management.domain.access.grants import RoleGrant

__all__ = [
    "AccessScope",
    "Permission",
    "Role",
    "RoleGrant",
]
