"""Rotating allowlisted JSON logs that never render arbitrary log messages."""

from __future__ import annotations

import json
import logging
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from clinic_management.config._validation import LOG_LEVELS, invalid_setting
from clinic_management.infrastructure.observability.fields import redact_fields

MAX_LOG_BYTES = 2_000_000
LOG_BACKUPS = 3


class SafeJsonFormatter(logging.Formatter):
    """Render allowlisted fields and stack locations, never message/argument data."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize safe operational facts without exception text or locals.

        Args:
            record: Standard logging record from the clinic namespace.

        Returns:
            A JSON line excluding arbitrary messages, arguments and causes.
        """
        raw: object = getattr(record, "fields", {})
        candidate: dict[str, str] = {}
        if isinstance(raw, Mapping):
            candidate = {
                key: value
                for key, value in raw.items()
                if isinstance(key, str) and isinstance(value, str)
            }
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": logging.getLevelName(record.levelno),
            **redact_fields(candidate),
        }
        if record.exc_info and record.exc_info[2] is not None:
            payload["stack"] = [
                {"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_tb(record.exc_info[2])
            ]
        return json.dumps(payload, ensure_ascii=True, allow_nan=False)


def configure_logging(*, level: str, output: Path) -> None:
    """Configure only the clinic namespace with bounded rotating diagnostic logs.

    Args:
        level: Registered uppercase severity threshold.
        output: Caller-selected diagnostic log path, never a patient-data export.

    Raises:
        ConfigurationError: If the severity threshold is invalid.
        OSError: If the directory or file cannot be created or opened.
    """
    if level not in LOG_LEVELS:
        raise invalid_setting()
    output.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        output, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(SafeJsonFormatter())
    logger = logging.getLogger("clinic_management")
    for previous in logger.handlers[:]:
        logger.removeHandler(previous)
        previous.close()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
