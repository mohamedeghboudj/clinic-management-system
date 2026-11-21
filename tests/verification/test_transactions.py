"""M1 author verification of copied state, rollback and explicit transaction state."""

from dataclasses import dataclass
from uuid import UUID

import pytest

from clinic_management.application.ports.audit import AuditRecord
from clinic_management.application.ports.unit_of_work import UnitOfWork
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import ConcurrencyError, ConflictError
from tests.support.fault_injection import assign_unchecked
from tests.support.fixtures import ProbeEntity, audit_fixture, event_fixture
from tests.support.store import MemoryStore
from tests.support.unit_of_work import MemoryUnitOfWork


def read_probe(store: MemoryStore, collection: str, identifier: UUID) -> ProbeEntity:
    """Read a typed synthetic root through the copied store boundary.

    Args:
        store: Current fake store.
        collection: Explicit fixture collection name.
        identifier: Synthetic identifier to read.

    Returns:
        The detached fixture root for assertions about values and versions.
    """
    entity = store.read_collection(collection)[identifier]
    assert isinstance(entity, ProbeEntity)
    return entity


def seeded_store() -> MemoryStore:
    """Create two synthetic collections for cross-repository rollback tests.

    Returns:
        A fresh store with known numeric fixture values.
    """
    store = MemoryStore()
    store.replace_collection("first", {UUID(int=1): ProbeEntity(id=UUID(int=1), value=10)})
    store.replace_collection("second", {UUID(int=2): ProbeEntity(id=UUID(int=2), value=20)})
    return store


def test_store_copies_inputs_reads_and_snapshots() -> None:
    """No external object, returned mapping or snapshot can mutate stored values."""
    store = MemoryStore()
    probe = ProbeEntity(id=UUID(int=1), value=10)
    store.replace_collection("first", {probe.id: probe})
    probe.value = 999
    detached = read_probe(store, "first", probe.id)
    assert detached.value == 10
    detached.value = 888
    assert read_probe(store, "first", probe.id).value == 10
    snapshot = store.snapshot()
    assert isinstance(snapshot.collections["first"][probe.id], ProbeEntity)
    snapshot.collections["first"].clear()
    assert read_probe(store, "first", probe.id).value == 10
    store.restore(snapshot)
    assert store.read_collection("first") == {}
    snapshot.collections["first"][probe.id] = probe
    assert store.read_collection("first") == {}
    assert store.read_collection("missing") == {}


def test_collection_identity_mapping_is_checked() -> None:
    """Invalid collection names and key/entity identity mismatches fail."""
    store = MemoryStore()
    with pytest.raises(ValueError):
        store.replace_collection("", {})
    with pytest.raises(ValueError):
        store.replace_collection("first", {UUID(int=1): ProbeEntity(id=UUID(int=2))})


def test_successful_commit_retains_both_writes_and_staged_effects() -> None:
    """Audit protocol compatibility and atomic fake outbox persistence are real."""
    store = seeded_store()
    concrete = MemoryUnitOfWork(store)
    contract: UnitOfWork = concrete
    audit: AuditRecord = audit_fixture()
    with contract as transaction:
        store.replace_collection("first", {})
        store.replace_collection("second", {})
        transaction.stage_audit(audit)
        transaction.stage_event(event_fixture())
        assert store.snapshot().audit_entries == ()
        assert store.snapshot().outbox_events == ()
        transaction.commit()
    assert store.read_collection("first") == {}
    assert store.read_collection("second") == {}
    snapshot = store.snapshot()
    assert len(snapshot.audit_entries) == 1
    assert len(snapshot.outbox_events) == 1
    assert concrete.committed_events == (event_fixture(),)


@pytest.mark.parametrize("raise_error", [True, False])
def test_uncommitted_context_restores_both_collections_and_discards_effects(
    raise_error: bool,
) -> None:
    """Both ordinary uncommitted exit and exception exit discard partial work."""
    store = seeded_store()
    unit = MemoryUnitOfWork(store)
    try:
        with unit:
            store.replace_collection("first", {})
            store.replace_collection("second", {})
            unit.stage_audit(audit_fixture())
            unit.stage_event(event_fixture())
            if raise_error:
                raise LookupError("synthetic failure")
    except LookupError:
        assert raise_error
    assert read_probe(store, "first", UUID(int=1)).value == 10
    assert read_probe(store, "second", UUID(int=2)).value == 20
    assert store.snapshot().outbox_events == ()
    assert store.snapshot().audit_entries == ()
    assert unit.committed_events == ()


def test_post_commit_exception_does_not_undo_committed_data() -> None:
    """Successful commit stays durable within fake semantics despite later errors."""
    store = seeded_store()
    with pytest.raises(LookupError), MemoryUnitOfWork(store) as transaction:
        store.replace_collection("first", {})
        transaction.commit()
        raise LookupError("after commit")
    assert store.read_collection("first") == {}


def test_nested_and_inactive_transactions_are_rejected() -> None:
    """A test double never silently pretends to support nested transactions."""
    store = seeded_store()
    unit = MemoryUnitOfWork(store)
    with pytest.raises(RuntimeError):
        unit.commit()
    with pytest.raises(RuntimeError):
        unit.rollback()
    with pytest.raises(RuntimeError):
        unit.stage_event(event_fixture())
    with pytest.raises(RuntimeError):
        unit.stage_audit(audit_fixture())
    with unit:
        with pytest.raises(RuntimeError):
            unit.__enter__()
        with pytest.raises(RuntimeError), MemoryUnitOfWork(store):
            pytest.fail("Nested transaction unexpectedly entered")
        unit.commit()
        with pytest.raises(RuntimeError):
            unit.commit()
    with unit:
        unit.rollback()
    with unit:
        unit.commit()
    assert unit.committed_events == ()


@pytest.mark.parametrize("duplicate_audit", [True, False])
def test_duplicate_effect_failure_rolls_back_business_changes(duplicate_audit: bool) -> None:
    """A failed outbox/audit append cannot leave the preceding writes committed."""
    store = seeded_store()
    with MemoryUnitOfWork(store) as first:
        first.stage_audit(audit_fixture())
        first.stage_event(event_fixture())
        first.commit()
    with pytest.raises(ConflictError), MemoryUnitOfWork(store) as second:
        store.replace_collection("first", {})
        if duplicate_audit:
            second.stage_audit(audit_fixture())
        else:
            second.stage_event(event_fixture())
        second.commit()
    assert read_probe(store, "first", UUID(int=1)).value == 10
    assert len(store.snapshot().audit_entries) == 1
    assert len(store.snapshot().outbox_events) == 1


def test_stale_save_does_not_overwrite_a_newer_root() -> None:
    """Two detached reads cannot silently overwrite each other's saved state."""
    store = seeded_store()
    first = read_probe(store, "first", UUID(int=1))
    stale = read_probe(store, "first", UUID(int=1))
    first.value = 30
    store.save_versioned("first", first, expected_version=0)
    assert first.version == 0
    assert read_probe(store, "first", first.id).version == 1
    stale.value = 99
    with pytest.raises(ConcurrencyError):
        store.save_versioned("first", stale, expected_version=0)
    assert read_probe(store, "first", first.id).value == 30
    with pytest.raises(ConcurrencyError):
        store.save_versioned("first", stale, expected_version=1)


@dataclass(eq=False, frozen=True, slots=True, kw_only=True)
class FrozenVersionedProbe(Entity):
    """Verify fake version replacement also supports frozen or slotted roots."""

    id: UUID
    version: int = 0


def test_versioned_save_supports_frozen_slotted_dataclasses() -> None:
    """Version replacement creates a new instance rather than mutating slots."""
    store = MemoryStore()
    probe = FrozenVersionedProbe(id=UUID(int=3))
    store.replace_collection("frozen", {probe.id: probe})
    store.save_versioned("frozen", probe, expected_version=0)
    result = store.read_collection("frozen")[probe.id]
    assert isinstance(result, FrozenVersionedProbe)
    assert result.version == 1
    assert probe.version == 0


@pytest.mark.parametrize("version", [-1, True, "bad", None])
def test_malformed_versions_and_missing_fixtures_fail(version: object) -> None:
    """The helper cannot treat booleans, strings or missing roots as valid versions."""
    store = seeded_store()
    probe = read_probe(store, "first", UUID(int=1))
    assign_unchecked(probe, "version", version)
    with pytest.raises(ValueError):
        store.save_versioned("first", probe, expected_version=0)
    with pytest.raises(ValueError):
        store.save_versioned("first", ProbeEntity(id=UUID(int=99)), expected_version=0)
    with pytest.raises(ValueError):
        store.save_versioned("first", ProbeEntity(id=UUID(int=1)), expected_version=-1)
