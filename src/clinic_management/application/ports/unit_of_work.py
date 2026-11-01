"""Explicit transaction boundary shared by feature repositories and outbox."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from clinic_management.application.ports.audit import AuditRecord
from clinic_management.domain.shared.events import DomainEvent


class UnitOfWork(Protocol):
    """Make business changes, audit facts and outbox entries one transaction.

    Each concrete feature UoW exposes its typed repositories. A context that
    exits without commit rolls back; exceptions are never suppressed.
    Once commit succeeds, later exceptions cannot undo the committed data.
    """

    def __enter__(self) -> UnitOfWork:
        """Start a new transaction and acquire transaction-scoped resources.

        Returns:
            This transaction's unit of work.
        """
        ...

    def commit(self) -> None:
        """Commit business writes, staged audit and outbox records together.

        Raises:
            PersistenceError: If the transaction cannot commit.
        """
        ...

    def rollback(self) -> None:
        """Discard the active uncommitted transaction and staged side effects."""
        ...

    def stage_event(self, event: DomainEvent) -> None:
        """Stage an event for the transaction's durable outbox.

        Args:
            event: Metadata-only event that must not be published yet.
        """
        ...

    def stage_audit(self, entry: AuditRecord) -> None:
        """Stage a mandatory audit record in the same transaction.

        Args:
            entry: Structurally compatible immutable audit fact.
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back uncommitted work, release resources and propagate errors.

        Args:
            exc_type: Exception category raised inside the context, if any.
            exc: Exception being propagated, without rendering its contents.
            traceback: Active traceback supplied by context-manager machinery.
        """
        ...
