"""Demonstrate M1 rollback/outbox contracts without inventing M2-M5 features."""

from __future__ import annotations

import argparse
from uuid import UUID

from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.ports.clock import Clock
from tests.support.clock import FrozenClock
from tests.support.fixtures import FIXED_TIME, ProbeEntity, audit_fixture, event_fixture
from tests.support.ids import SequenceIdGenerator
from tests.support.store import MemoryStore
from tests.support.unit_of_work import MemoryUnitOfWork


def foundation_demo() -> None:
    """Exercise copied writes, rollback and atomic audit/outbox staging offline.

    Raises:
        RuntimeError: If a foundation contract fails its demonstration check.
    """
    clock: Clock = FrozenClock(current=FIXED_TIME)
    ids = SequenceIdGenerator([UUID(int=1), UUID(int=2)])
    first = ProbeEntity(id=ids.new_id(), value=10)
    second = ProbeEntity(id=ids.new_id(), value=20)
    store = MemoryStore()
    with MemoryUnitOfWork(store) as transaction:
        store.replace_collection("first", {first.id: first})
        store.replace_collection("second", {second.id: second})
        transaction.stage_audit(audit_fixture())
        transaction.stage_event(event_fixture())
        transaction.commit()
    try:
        with MemoryUnitOfWork(store) as transaction:
            store.replace_collection("first", {})
            store.replace_collection("second", {})
            transaction.stage_event(event_fixture(event_id=UUID(int=101)))
            raise ValueError("Synthetic rollback probe")
    except ValueError:
        if not store.read_collection("first") or not store.read_collection("second"):
            raise RuntimeError("Rollback did not restore both collections") from None
    snapshot = store.snapshot()
    if len(snapshot.audit_entries) != 1 or len(snapshot.outbox_events) != 1:
        raise RuntimeError("Rolled-back side effects became committed")
    page = Page(items=(first.id,), next_cursor=None)
    if page.has_next() or PageRequest().limit != 25 or clock.now() != FIXED_TIME:
        raise RuntimeError("A deterministic foundation contract failed")
    print("Foundation demo passed: two copied collections, rollback, one audit/outbox commit.")
    print("This is infrastructure verification, not the complete clinic workflow.")


def main() -> int:
    """Run explicitly available foundation behavior or report missing integration.

    Returns:
        Zero for the available foundation demo; two for pending clinic integration.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation-only", action="store_true")
    args = parser.parse_args()
    if args.foundation_only:
        foundation_demo()
        return 0
    print("Full clinic demo pending: M2 people/access, M3 scheduling, M4 clinical, M5 billing.")
    print("Run --foundation-only for implemented M1 transaction contracts.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
