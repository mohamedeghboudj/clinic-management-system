"""Deliberately invalid test inputs without weakening production annotations."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import cast


def replace_unchecked[T](value: T, changes: Mapping[str, object]) -> T:
    """Inject invalid constructor values across a deliberate test-only boundary.

    Args:
        value: Dataclass fixture whose constructor validation is under test.
        changes: Potentially invalid field values supplied by the test case.

    Returns:
        The replaced dataclass if its runtime validation accepts the input.
    """
    factory = cast("Callable[..., T]", replace)
    return factory(value, **changes)


def assign_unchecked(value: object, field_name: str, new_value: object) -> None:
    """Invoke the real setter to test readonly guards or malformed caller state.

    Args:
        value: Fixture whose real mutation behavior is being exercised.
        field_name: Explicit field selected by the test, never production input.
        new_value: Potentially invalid value for the runtime boundary.
    """
    setter = cast("Callable[[str, object], None]", value.__setattr__)
    setter(field_name, new_value)
