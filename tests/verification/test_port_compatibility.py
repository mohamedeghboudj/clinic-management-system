"""Exercise structural adapters and committed-only delivery at shared boundaries."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from clinic_management.application.contracts.health import ComponentHealth, HealthStatus
from clinic_management.application.ports.audit import AuditRecord, AuditWriter
from clinic_management.application.ports.events import EventPublisher
from clinic_management.application.ports.health import HealthCheck
from clinic_management.application.ports.unit_of_work import UnitOfWork
from clinic_management.domain.shared.events import DomainEvent
from tests.support.fixtures import FIXED_TIME, audit_fixture, event_fixture
from tests.support.store import MemoryStore
from tests.support.unit_of_work import MemoryUnitOfWork


@dataclass
class RecordingPublisher:
    """Capture published batches independently of the transaction's pending list."""

    delivered: list[DomainEvent] = field(default_factory=list)

    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Copy the committed batch supplied by the explicit dispatcher boundary.

        Args:
            events: Committed event hints from the unit of work.
        """
        self.delivered.extend(tuple(events))


@dataclass
class TransactionAuditWriter:
    """Stage audit through the same transaction used for business changes."""

    unit: UnitOfWork

    def append(self, entry: AuditRecord) -> None:
        """Accept structural immutable records without importing M2's class.

        Args:
            entry: Readonly audit fact matching the shared protocol.
        """
        self.unit.stage_audit(entry)


class SyntheticHealthCheck:
    """Implement the health boundary without a database or network dependency."""

    def check(self) -> ComponentHealth:
        """Return a safe readiness fixture rather than a driver exception.

        Returns:
            A validated unavailable-database health result.
        """
        return ComponentHealth(
            component="database",
            status=HealthStatus.UNAVAILABLE,
            checked_at=FIXED_TIME,
            code="DEPENDENCY_UNAVAILABLE",
        )


def test_structural_adapters_preserve_transaction_and_delivery_boundaries() -> None:
    """Audit can use M2's shape while event delivery consumes committed facts only."""
    store = MemoryStore()
    unit = MemoryUnitOfWork(store)
    concrete = RecordingPublisher()
    publisher: EventPublisher = concrete
    writer: AuditWriter = TransactionAuditWriter(unit=unit)
    with unit:
        writer.append(audit_fixture())
        unit.stage_event(event_fixture())
        assert concrete.delivered == []
        unit.commit()
    publisher.publish(unit.committed_events)
    assert concrete.delivered == [event_fixture()]
    assert len(store.snapshot().audit_entries) == 1
    with unit:
        unit.stage_event(event_fixture())
    publisher.publish(unit.committed_events)
    assert concrete.delivered == [event_fixture()]


def test_health_protocol_returns_safe_typed_readiness() -> None:
    """Consumers can depend on the protocol without importing a concrete adapter."""
    check: HealthCheck = SyntheticHealthCheck()
    result = check.check()
    assert result.status is HealthStatus.UNAVAILABLE
    assert result.code == "DEPENDENCY_UNAVAILABLE"
