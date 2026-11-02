"""Validation for explicit operation timing observations."""

from math import isfinite

from clinic_management.application.ports.metrics import MetricsRecorder
from clinic_management.domain.shared.errors import ValidationError
from clinic_management.infrastructure.observability.fields import OPERATIONS, OUTCOMES


def record_duration(
    recorder: MetricsRecorder, operation: str, seconds: float, *, outcome: str
) -> None:
    """Submit one finite measurement using registered low-cardinality labels.

    Args:
        recorder: Explicit metrics adapter, never a hidden global collector.
        operation: Registered use-case name.
        seconds: Elapsed monotonic duration, not a wall-clock timestamp.
        outcome: Registered operation outcome.

    Raises:
        ValidationError: If labels or duration violate the measurement contract.
    """
    if (
        operation not in OPERATIONS
        or outcome not in OUTCOMES
        or isinstance(seconds, bool)
        or not isfinite(seconds)
        or seconds < 0
    ):
        raise ValidationError(code="INVALID_VALUE", message_key="metrics.observation.invalid")
    recorder.observe(operation, seconds, outcome=outcome)
    recorder.increment(operation, outcome=outcome)
