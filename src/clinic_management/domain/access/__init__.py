"""M2 accounts, grants and immutable audit records.

The AuditEntry entity satisfies the M1 AuditRecord protocol structurally.
"""

from clinic_management.domain.access.audit import AuditEntry
from clinic_management.domain.access.enums import AccessScope, Permission, Role
from clinic_management.domain.access.grants import RoleGrant

__all__ = [
    "AccessScope",
    "AuditEntry",
    "Permission",
    "Role",
    "RoleGrant",
]
