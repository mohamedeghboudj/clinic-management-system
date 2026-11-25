"""M1 author verification of identities, safe errors and deterministic adapters."""

from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from clinic_management.application.ports.clock import Clock
from clinic_management.application.ports.identity import IdGenerator
from clinic_management.domain.shared.errors import ClinicError, ValidationError
from clinic_management.infrastructure.clock import SystemClock
from clinic_management.infrastructure.identity_ids import UuidGenerator
from tests.support.clock import FrozenClock
from tests.support.fixtures import FIXED_TIME, ProbeEntity
from tests.support.ids import SequenceIdGenerator


@dataclass(eq=False, kw_only=True)
class AlternativeProbe(ProbeEntity):
    """Represent a distinct concrete entity sharing the same fixture ID."""


def test_entity_equality_uses_identity_and_concrete_type() -> None:
    """Changing mutable fields does not change identity; another type is unequal."""
    original = ProbeEntity(id=UUID(int=1), value=1)
    assert original == ProbeEntity(id=original.id, value=999)
    assert original != ProbeEntity(id=UUID(int=2), value=1)
    assert original != AlternativeProbe(id=original.id, value=1)
    assert original != object()
    with pytest.raises(TypeError):
        hash(original)


def test_error_contract_copies_details_and_omits_them_from_representations() -> None:
    """Changing caller data cannot alter a failure or leak detail values by repr."""
    source = {"field": "synthetic-private-context"}
    error = ClinicError(code="INVALID_VALUE", message_key="shared.invalid", safe_details=source)
    source["field"] = "changed"
    assert error.safe_details["field"] == "synthetic-private-context"
    assert str(error) == "INVALID_VALUE"
    assert "synthetic-private-context" not in repr(error)
    assert "synthetic-private-context" not in str(error)
    with pytest.raises(TypeError):
        cast("MutableMapping[str, str]", error.safe_details)["field"] = "changed"
    assert dict(ClinicError(code="EMPTY", message_key="empty").safe_details) == {}


@pytest.mark.parametrize("code,key", [("bad code", "valid.key"), ("VALID", "private text")])
def test_error_identifiers_reject_free_form_text(code: str, key: str) -> None:
    """Failure codes and translation keys cannot be arbitrary human messages."""
    with pytest.raises(ValueError):
        ClinicError(code=code, message_key=key)


def test_error_details_reject_non_string_structures() -> None:
    """An incorrectly typed external caller cannot attach arbitrary detail objects."""
    invalid = cast("dict[str, str]", {"field": 123})
    with pytest.raises(ValueError):
        ClinicError(code="INVALID_VALUE", message_key="shared.invalid", safe_details=invalid)


def test_real_adapters_satisfy_ports() -> None:
    """The clock returns UTC and UUID generation supplies version-four identities."""
    clock: Clock = SystemClock()
    generator: IdGenerator = UuidGenerator()
    instant = clock.now()
    assert instant.tzinfo is UTC
    assert generator.new_id().version == 4
    assert generator.new_id() != generator.new_id()


def test_frozen_clock_is_explicit_and_monotonic() -> None:
    """Reading does not advance time and negative simulated elapsed time fails."""
    clock = FrozenClock(current=FIXED_TIME)
    assert clock.now() == FIXED_TIME
    clock.advance(timedelta(seconds=5))
    assert clock.now() == FIXED_TIME + timedelta(seconds=5)
    with pytest.raises(ValidationError):
        clock.advance(timedelta(seconds=-1))
    with pytest.raises(ValidationError):
        FrozenClock(current=datetime(2026, 11, 1))


def test_sequence_ids_copy_inputs_and_fail_on_exhaustion() -> None:
    """A fixture never unexpectedly falls back to randomness or reused IDs."""
    values = [UUID(int=1), UUID(int=2)]
    generator: IdGenerator = SequenceIdGenerator(values)
    values.clear()
    assert generator.new_id() == UUID(int=1)
    assert generator.new_id() == UUID(int=2)
    with pytest.raises(RuntimeError, match="exhausted"):
        generator.new_id()
    with pytest.raises(ValueError, match="unique"):
        SequenceIdGenerator([UUID(int=1), UUID(int=1)])
    with pytest.raises(ValidationError):
        SequenceIdGenerator(cast("list[UUID]", ["not-a-uuid"]))
