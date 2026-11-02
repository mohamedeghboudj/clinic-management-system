"""Bounded operational labels and safe structured field filtering."""

from collections.abc import Mapping
from math import isfinite
from uuid import UUID

OPERATIONS = frozenset(
    {
        "foundation_demo",
        "register_patient",
        "search_patients",
        "authenticate",
        "book_appointment",
        "reschedule_appointment",
        "check_in_patient",
        "finalize_consultation",
        "issue_prescription",
        "issue_invoice",
        "record_payment",
        "reverse_payment",
        "health_check",
        "dispatch_events",
    }
)
OUTCOMES = frozenset({"success", "failure", "denied", "conflict", "unavailable"})
ERROR_CODES = frozenset(
    {
        "INVALID_VALUE",
        "INVALID_CONFIGURATION",
        "STALE_VERSION",
        "APPOINTMENT_OVERLAP",
        "INVALID_TRANSITION",
        "ACCESS_DENIED",
        "PAYMENT_EXCEEDS_BALANCE",
        "IDEMPOTENCY_KEY_REUSED",
        "DEPENDENCY_UNAVAILABLE",
        "PERSISTENCE_FAILURE",
        "UNEXPECTED_FAILURE",
    }
)


def _valid_duration(value: str) -> bool:
    """Check a bounded machine-number string without reflecting invalid input.

    Args:
        value: Candidate elapsed-seconds representation.

    Returns:
        Whether the string represents a finite nonnegative duration.
    """
    try:
        seconds = float(value)
    except ValueError:
        return False
    return len(value) <= 24 and isfinite(seconds) and seconds >= 0


def _valid_correlation(value: str) -> bool:
    """Accept only canonical UUID correlation strings.

    Args:
        value: Candidate correlation identifier.

    Returns:
        Whether the supplied value is a canonical UUID string.
    """
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def redact_fields(fields: Mapping[str, str]) -> dict[str, str]:
    """Drop unknown keys and invalid values instead of inspecting clinical text.

    Args:
        fields: Operational values from a deliberate structured logging call.

    Returns:
        Only registered operations, outcomes, codes, durations and correlation IDs.
    """
    safe: dict[str, str] = {}
    choices = {"operation": OPERATIONS, "outcome": OUTCOMES, "code": ERROR_CODES}
    for name, value in fields.items():
        raw_value: object = value
        if not isinstance(raw_value, str):
            continue
        if name in choices and value in choices[name]:
            safe[name] = value
        elif name == "duration_seconds" and _valid_duration(value):
            safe[name] = value
        elif name == "correlation_id" and _valid_correlation(value):
            safe[name] = value
    return safe
