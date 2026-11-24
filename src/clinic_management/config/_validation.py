"""Private configuration parsing that never includes input values in failures."""

from collections.abc import Mapping
from math import isfinite

from clinic_management.domain.shared.errors import ConfigurationError

ENVIRONMENTS = frozenset({"development", "test", "staging", "production"})
LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def invalid_setting() -> ConfigurationError:
    """Create a generic startup error without rendering configuration contents.

    Returns:
        An error safe even when the rejected input contains credentials.
    """
    return ConfigurationError(code="INVALID_CONFIGURATION", message_key="config.invalid")


def required(env: Mapping[str, str], key: str) -> str:
    """Read an explicitly required nonempty setting without logging it.

    Args:
        env: Supplied environment mapping, usually provided at bootstrap.
        key: Public setting name whose value must exist.

    Returns:
        The supplied value without altering significant secret whitespace.

    Raises:
        ConfigurationError: If the value is missing or blank.
    """
    value = env.get(key, "")
    if not isinstance(value, str) or not value.strip():
        raise invalid_setting()
    return value


def positive_seconds(value: float) -> None:
    """Validate a bounded positive timeout without choosing deployment defaults.

    Args:
        value: Configured timeout in seconds.

    Raises:
        ConfigurationError: If the value is nonnumeric, nonfinite or nonpositive.
    """
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise invalid_setting()
    if not isfinite(value) or value <= 0:
        raise invalid_setting()


def parse_timeout(env: Mapping[str, str], key: str) -> float:
    """Parse an explicit finite positive timeout without leaking its input.

    Args:
        env: Supplied environment mapping.
        key: Name of the required timeout setting.

    Returns:
        The parsed positive duration.

    Raises:
        ConfigurationError: If parsing or validation fails.
    """
    try:
        value = float(required(env, key))
    except ValueError:
        raise invalid_setting() from None
    positive_seconds(value)
    return value
