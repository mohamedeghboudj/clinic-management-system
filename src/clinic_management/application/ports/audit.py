"""Read-only audit contract compatible with M2's future immutable AuditEntry."""

from datetime import datetime
from typing import Protocol
from uuid import UUID


class AuditRecord(Protocol):
    """Describe audit facts structurally without implementing M2's entity.

    Every property is read-only at this boundary. Concrete records must also
    preserve their values after construction and contain no clinical narrative.
    """

    @property
    def id(self) -> UUID:
        """Return the unique audit entry identifier."""
        ...

    @property
    def clinic_id(self) -> UUID:
        """Return the clinic whose access boundary the action concerns."""
        ...

    @property
    def actor_id(self) -> UUID | None:
        """Return the verified actor ID, or none for an unknown login actor."""
        ...

    @property
    def action(self) -> str:
        """Return the registered action name, never a free-form message."""
        ...

    @property
    def resource_type(self) -> str:
        """Return the registered resource category."""
        ...

    @property
    def resource_id(self) -> UUID | None:
        """Return the affected resource ID when known."""
        ...

    @property
    def outcome(self) -> str:
        """Return the registered operation outcome."""
        ...

    @property
    def occurred_at(self) -> datetime:
        """Return the authoritative aware UTC instant."""
        ...

    @property
    def correlation_id(self) -> UUID:
        """Return the request correlation identifier."""
        ...

    @property
    def reason_code(self) -> str | None:
        """Return an optional registered reason code without private text."""
        ...


class AuditWriter(Protocol):
    """Stage an append-only record inside the active business transaction."""

    def append(self, entry: AuditRecord) -> None:
        """Stage a reviewed immutable audit fact in the current UoW.

        Args:
            entry: M2's AuditEntry or another structurally compatible record.

        Raises:
            PersistenceError: If mandatory audit persistence cannot complete.
        """
        ...
