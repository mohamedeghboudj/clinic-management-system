"""Copy-isolated single-threaded storage for repository contract verification."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, is_dataclass, replace
from typing import cast
from uuid import UUID

from clinic_management.application.ports.audit import AuditRecord
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ConcurrencyError, ConflictError
from clinic_management.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MemorySnapshot:
    """Hold detached test-store state, including audit and outbox history."""

    collections: dict[str, dict[UUID, Entity]]
    audit_entries: tuple[AuditRecord, ...]
    outbox_events: tuple[DomainEvent, ...]


class MemoryStore:
    """Support deterministic transaction tests without claiming DB isolation."""

    def __init__(self) -> None:
        """Create empty copied entity collections, audit and outbox histories."""
        self._collections: dict[str, dict[UUID, Entity]] = {}
        self._audit_entries: list[AuditRecord] = []
        self._outbox_events: list[DomainEvent] = []
        self._transaction_open = False

    def snapshot(self) -> MemorySnapshot:
        """Copy the entire fake store, including committed side effects.

        Returns:
            A detached snapshot safe for rollback or test inspection.
        """
        return MemorySnapshot(
            collections=deepcopy(self._collections),
            audit_entries=deepcopy(tuple(self._audit_entries)),
            outbox_events=deepcopy(tuple(self._outbox_events)),
        )

    def restore(self, snapshot: MemorySnapshot) -> None:
        """Restore copies without retaining references into a caller's snapshot.

        Args:
            snapshot: Earlier complete state to restore.
        """
        self._collections = deepcopy(snapshot.collections)
        self._audit_entries = list(deepcopy(snapshot.audit_entries))
        self._outbox_events = list(deepcopy(snapshot.outbox_events))

    def read_collection(self, name: str) -> dict[UUID, Entity]:
        """Read copies; mutating a returned object never changes stored data.

        Args:
            name: Internal test collection name, not a user-submitted query.

        Returns:
            A detached mapping of entity IDs to copied entities.
        """
        return deepcopy(self._collections.get(name, {}))

    def replace_collection(self, name: str, rows: Mapping[UUID, Entity]) -> None:
        """Replace an internal collection using validated detached values.

        Args:
            name: Internal test collection name.
            rows: Entity IDs mapped to entities carrying the same IDs.

        Raises:
            ValueError: If a collection name or key/identity mapping is invalid.
        """
        if not name or any(key != entity.id for key, entity in rows.items()):
            raise ValueError("Invalid test collection identity mapping")
        self._collections[name] = deepcopy(dict(rows))

    def save_versioned(self, name: str, entity: Entity, *, expected_version: int) -> None:
        """Exercise stale-save rejection for copied mutable aggregate fixtures.

        Args:
            name: Collection whose existing entity is being replaced.
            entity: Candidate root exposing an integer ``version`` attribute.
            expected_version: Version returned by the earlier read.

        Raises:
            ConcurrencyError: If the stored or candidate version is stale.
            ValueError: If the fixture is missing or version is malformed.
        """
        rows = self.read_collection(name)
        current = rows.get(entity.id)
        if current is None or type(expected_version) is not int or expected_version < 0:
            raise ValueError("A versioned save requires an existing valid fixture")
        if (
            self._version_of(current) != expected_version
            or self._version_of(entity) != expected_version
        ):
            raise ConcurrencyError(code="STALE_VERSION", message_key="entity.version.stale")
        candidate: object = deepcopy(entity)
        if isinstance(candidate, type) or not is_dataclass(candidate):
            raise ValueError("Versioned fixtures must be dataclass entities")
        # Runtime dataclass validation above guards this test-adapter boundary.
        factory = cast("Callable[..., Entity]", replace)
        rows[entity.id] = factory(candidate, version=expected_version + 1)
        self.replace_collection(name, rows)

    def _version_of(self, entity: Entity) -> int:
        """Read an explicitly valid version from a versioned aggregate fixture.

        Args:
            entity: Fixture whose persisted version is being checked.

        Returns:
            A nonnegative integer version, never a boolean or missing attribute.

        Raises:
            ValueError: If the fixture does not expose a valid version.
        """
        value: object = getattr(entity, "version", None)
        if type(value) is not int or value < 0:
            raise ValueError("A versioned fixture requires a nonnegative integer version")
        return value

    def begin(self) -> MemorySnapshot:
        """Reserve the store for one fake transaction; nested contexts fail.

        Returns:
            The complete state before the new transaction.

        Raises:
            RuntimeError: If a transaction is already open on this fake store.
        """
        if self._transaction_open:
            raise RuntimeError("MemoryStore does not support nested transactions")
        snapshot = self.snapshot()
        self._transaction_open = True
        return snapshot

    def finish(self) -> None:
        """Release the fake transaction reservation after commit or rollback."""
        self._transaction_open = False

    def append_effects(self, audit: Sequence[AuditRecord], events: Sequence[DomainEvent]) -> None:
        """Append copied audit and outbox records, rejecting duplicate IDs.

        Args:
            audit: Staged immutable audit facts.
            events: Staged metadata-only outbox events.

        Raises:
            ConflictError: If audit or event identifiers are duplicated.
        """
        audit_copy, event_copy = deepcopy(tuple(audit)), deepcopy(tuple(events))
        audit_ids = [entry.id for entry in (*self._audit_entries, *audit_copy)]
        event_ids = [entry.event_id for entry in (*self._outbox_events, *event_copy)]
        if len(set(audit_ids)) != len(audit_ids) or len(set(event_ids)) != len(event_ids):
            raise ConflictError(code="DUPLICATE_EFFECT", message_key="transaction.effect.duplicate")
        self._audit_entries.extend(audit_copy)
        self._outbox_events.extend(event_copy)
