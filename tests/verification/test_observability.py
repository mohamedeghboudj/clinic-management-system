"""M1 author verification of private-data exclusion and bounded measurements."""

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from clinic_management.domain.shared.errors import ConfigurationError, ValidationError
from clinic_management.infrastructure.observability.fields import redact_fields
from clinic_management.infrastructure.observability.logging import configure_logging
from clinic_management.infrastructure.observability.timing import record_duration


@dataclass
class RecordingMetrics:
    """Capture explicit measurements for assertions without global collectors."""

    counts: list[tuple[str, str]] = field(default_factory=list)
    durations: list[tuple[str, float, str]] = field(default_factory=list)

    def increment(self, name: str, *, outcome: str) -> None:
        """Capture one registered count with its outcome.

        Args:
            name: Registered operation name.
            outcome: Registered operation outcome.
        """
        self.counts.append((name, outcome))

    def observe(self, name: str, seconds: float, *, outcome: str) -> None:
        """Capture one duration without identifying a patient or user.

        Args:
            name: Registered operation name.
            seconds: Measured elapsed seconds.
            outcome: Registered operation outcome.
        """
        self.durations.append((name, seconds, outcome))


@pytest.fixture
def clinic_logger() -> Iterator[logging.Logger]:
    """Isolate the clinic logger so tests leave global logging unchanged.

    Yields:
        A logger whose original handlers/level/propagation are restored afterward.
    """
    logger = logging.getLogger("clinic_management")
    previous = logger.handlers[:], logger.level, logger.propagate
    logger.handlers = []
    try:
        yield logger
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers, logger.level, logger.propagate = previous


def test_logging_drops_messages_arguments_exception_values_and_unknown_fields(
    tmp_path: Path, clinic_logger: logging.Logger
) -> None:
    """Even an unsafe logging call cannot put its private values in clinic output."""
    output = tmp_path / "logs" / "clinic.jsonl"
    configure_logging(level="INFO", output=output)
    try:
        raise ValueError("synthetic-private-exception")
    except ValueError:
        clinic_logger.exception(
            "synthetic-private-message %s",
            "synthetic-private-argument",
            extra={
                "fields": {
                    "operation": "record_payment",
                    "outcome": "failure",
                    "diagnosis": "synthetic-private-note",
                }
            },
        )
    for handler in clinic_logger.handlers:
        handler.flush()
    text = output.read_text(encoding="utf-8")
    assert "synthetic-private" not in text
    value = json.loads(text)
    assert value["operation"] == "record_payment"
    assert value["outcome"] == "failure"
    assert value["stack"][0]["file"] == "test_observability.py"
    assert "source" not in value["stack"][0]
    configure_logging(level="WARNING", output=output)
    assert len(clinic_logger.handlers) == 1


def test_redactor_validates_values_and_omits_unknown_keys() -> None:
    """Free-form private labels cannot inflate metrics or enter structured logs."""
    correlation = str(UUID(int=1))
    safe = redact_fields(
        {
            "operation": "record_payment",
            "outcome": "success",
            "code": "ACCESS_DENIED",
            "duration_seconds": "0.25",
            "correlation_id": correlation,
            "patient_name": "synthetic",
        }
    )
    assert len(safe) == 5
    for fields in (
        {"operation": "private-name"},
        {"outcome": "private-content"},
        {"code": "raw SQL"},
        {"duration_seconds": "nan"},
        {"duration_seconds": "-1"},
        {"duration_seconds": "not numeric"},
        {"correlation_id": "not-a-uuid"},
        {"correlation_id": "A" * 32},
    ):
        assert redact_fields(fields) == {}


def test_invalid_log_configuration_fails(tmp_path: Path) -> None:
    """An unknown severity or unwritable directory cannot silently disable logging."""
    with pytest.raises(ConfigurationError):
        configure_logging(level="invented", output=tmp_path / "log")
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("fixture", encoding="utf-8")
    with pytest.raises(OSError):
        configure_logging(level="INFO", output=blocker / "log")


def test_duration_records_exactly_one_observation_and_count() -> None:
    """Successful measurement uses operation/outcome labels and no identifiers."""
    recorder = RecordingMetrics()
    record_duration(recorder, "record_payment", 0.5, outcome="success")
    assert recorder.counts == [("record_payment", "success")]
    assert recorder.durations == [("record_payment", 0.5, "success")]


@pytest.mark.parametrize("seconds", [-1.0, float("nan"), float("inf"), True])
def test_invalid_durations_never_reach_adapter(seconds: float) -> None:
    """Finite nonnegative numeric durations are required at the measurement boundary."""
    recorder = RecordingMetrics()
    with pytest.raises(ValidationError):
        record_duration(recorder, "record_payment", seconds, outcome="success")
    assert recorder.counts == []


def test_unknown_metric_labels_are_rejected() -> None:
    """Labels are registered technical names rather than arbitrary user content."""
    for operation, outcome in (("private-name", "success"), ("record_payment", "private-text")):
        with pytest.raises(ValidationError):
            record_duration(RecordingMetrics(), operation, 0.1, outcome=outcome)


def test_unstructured_or_wrongly_typed_logging_fields_are_dropped(
    tmp_path: Path, clinic_logger: logging.Logger
) -> None:
    """Malformed logging extras cannot expose a free-form message or field value."""
    output = tmp_path / "operational.jsonl"
    configure_logging(level="INFO", output=output)
    clinic_logger.info("synthetic-private", extra={"fields": "synthetic-private"})
    clinic_logger.info("synthetic-private", extra={"fields": {"operation": 123}})
    for handler in clinic_logger.handlers:
        handler.flush()
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all("synthetic-private" not in line for line in lines)
    assert redact_fields(cast("dict[str, str]", {"operation": 123})) == {}
