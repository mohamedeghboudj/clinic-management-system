"""Explicit transaction test double with rollback and staged-side-effect safety."""

from __future__ import annotations

from copy import deepcopy
from types import TracebackType

from clinic_management.application.ports.audit import AuditRecord
from clinic_management.domain.shared.events import DomainEvent
from tests.support.store import MemorySnapshot, MemoryStore


class MemoryUnitOfWork:
    """Provide rollback in a single-threaded fake, never concurrency guarantees."""

    def __init__(self, store: MemoryStore) -> None:
        """Bind one reusable unit of work to an explicit fake store.

        Args:
            store: Store shared by the transaction's feature repository fakes.
        """
        self.store = store
        self._events: list[DomainEvent] = []
        self._audit: list[AuditRecord] = []
        self._snapshot: MemorySnapshot | None = None
        self._committed = False
        self._active = False
        self.committed_events: tuple[DomainEvent, ...] = ()

    def __enter__(self) -> MemoryUnitOfWork:
        """Open a fresh context and clear observations from the earlier context.

        Returns:
            This unit of work with a detached rollback snapshot.

        Raises:
            RuntimeError: If this context or the store already has a transaction.
        """
        if self._active:
            raise RuntimeError("Unit of work context is already active")
        self._snapshot = self.store.begin()
        self._active, self._committed = True, False
        self._events, self._audit = [], []
        self.committed_events = ()
        return self

    def _require_active(self) -> None:
        """Reject operations outside an unfinished transaction context.

        Raises:
            RuntimeError: If the transaction is inactive or already committed.
        """
        if not self._active or self._committed:
            raise RuntimeError("No active uncommitted transaction")

    def stage_event(self, event: DomainEvent) -> None:
        """Copy an event into the current uncommitted outbox batch.

        Args:
            event: Validated metadata-only domain event.

        Raises:
            RuntimeError: If no uncommitted transaction is open.
        """
        self._require_active()
        self._events.append(deepcopy(event))

    def stage_audit(self, entry: AuditRecord) -> None:
        """Copy a structurally compatible audit record into the active batch.

        Args:
            entry: M2's future immutable audit fact or a synthetic test record.

        Raises:
            RuntimeError: If no uncommitted transaction is open.
        """
        self._require_active()
        self._audit.append(deepcopy(entry))

    def commit(self) -> None:
        """Retain writes and append audit/outbox together without delivering them.

        Raises:
            ConflictError: If a staged effect duplicates a persisted identifier.
            RuntimeError: If no unfinished context exists.
        """
        self._require_active()
        self.store.append_effects(self._audit, self._events)
        self.committed_events = tuple(self._events)
        self._committed = True

    def rollback(self) -> None:
        """Restore uncommitted writes and discard staged side effects.

        Raises:
            RuntimeError: If there is no active uncommitted transaction.
        """
        self._require_active()
        if self._snapshot is None:
            raise RuntimeError("Missing rollback snapshot")
        self.store.restore(self._snapshot)
        self._events, self._audit = [], []
        self.committed_events = ()
        self._active = False
        self.store.finish()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back unfinished work while never suppressing the original error.

        Args:
            exc_type: Error category raised inside the context, if any.
            exc: Propagated exception, whose contents must not be logged here.
            traceback: Context-manager traceback, without rendering private data.
        """
        try:
            if self._active and not self._committed:
                self.rollback()
        finally:
            if self._active:
                self.store.finish()
            self._active = False
            self._snapshot = None
