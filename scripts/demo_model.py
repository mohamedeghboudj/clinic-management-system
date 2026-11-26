"""Demonstrate the Week 1 clinic workflow and its in-memory transaction contracts."""

from __future__ import annotations

import argparse
from uuid import UUID

from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.ports.clock import Clock
from scripts.clinic_visit_demo import clinic_demo
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


def main() -> int:
    """Run the foundation checks and, by default, the connected clinic visit.

    Returns:
        Zero after the requested demonstrations succeed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation-only", action="store_true")
    args = parser.parse_args()
    foundation_demo()
    if not args.foundation_only:
        clinic_demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
