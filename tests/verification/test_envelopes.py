"""M1 author verification of bounded paging and content-free envelopes."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from typing import cast

import pytest

from clinic_management.application.contracts.health import (
    ComponentHealth,
    HealthStatus,
    RuntimeState,
)
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.domain.shared.errors import ValidationError
from tests.support.fault_injection import assign_unchecked, replace_unchecked
from tests.support.fixtures import FIXED_TIME, event_fixture


@pytest.mark.parametrize("limit", [0, -1, 101, True])
def test_page_size_is_bounded_and_rejects_boolean(limit: int) -> None:
    """An unbounded or boolean limit never reaches a repository query."""
    with pytest.raises(ValidationError):
        PageRequest(limit=limit)


@pytest.mark.parametrize("cursor", ["", "has spaces", "\n", "é", "x" * 2049])
def test_cursor_container_rejects_ambiguous_or_oversized_text(cursor: str) -> None:
    """Opaque cursor meaning stays in the repository; its container is bounded."""
    with pytest.raises(ValidationError):
        PageRequest(cursor=cursor)


def test_page_boundaries_and_continuation() -> None:
    """Sizes at both boundaries and explicit continuation results are supported."""
    assert PageRequest(limit=1).limit == 1
    assert PageRequest(limit=100, cursor="cursor-1").cursor == "cursor-1"
    assert Page(items=(), next_cursor=None).has_next() is False
    assert Page(items=(1, 2), next_cursor="cursor-2").has_next() is True
    with pytest.raises(ValidationError):
        Page(items=tuple(range(101)), next_cursor=None)
    with pytest.raises(ValidationError):
        Page(items=cast("tuple[int, ...]", [1]), next_cursor=None)
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(PageRequest(), "limit", 50)


@pytest.mark.parametrize(
    "field,value",
    [
        ("event_type", "PRIVATE CLINICAL CONTENT"),
        ("entity_version", -1),
        ("entity_version", True),
        ("actor_id", "unparsed-identifier"),
        ("occurred_at", datetime(2026, 11, 1)),
        ("occurred_at", datetime(2026, 11, 1, tzinfo=timezone(timedelta(hours=1)))),
    ],
)
def test_event_metadata_is_validated(field: str, value: object) -> None:
    """Malformed event metadata fails before staging or publication."""
    with pytest.raises(ValidationError):
        replace_unchecked(event_fixture(), {field: value})


def test_event_is_immutable_and_contains_no_arbitrary_payload() -> None:
    """The committed hint contract carries IDs and time rather than clinical data."""
    event = event_fixture()
    assert event.occurred_at.tzinfo is UTC
    assert not hasattr(event, "payload")
    with pytest.raises(FrozenInstanceError):
        assign_unchecked(event, "event_type", "ACCESS_CHANGED")


def test_runtime_and_health_values_are_explicit() -> None:
    """Health checks return safe registered facts and no raw failure message."""
    result = ComponentHealth(
        component="database",
        status=HealthStatus.UNAVAILABLE,
        checked_at=FIXED_TIME,
        code="DEPENDENCY_UNAVAILABLE",
    )
    assert result.status is HealthStatus.UNAVAILABLE
    assert RuntimeState.DISCONNECTED.value == "DISCONNECTED"
    assert replace(result, status=HealthStatus.OK, code=None).code is None
    for change in (
        {"component": "private-clinic-name"},
        {"status": "OK"},
        {"code": "raw database credentials"},
        {"checked_at": FIXED_TIME.replace(tzinfo=None)},
    ):
        with pytest.raises(ValidationError):
            replace_unchecked(result, change)
