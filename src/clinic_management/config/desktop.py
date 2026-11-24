"""Desktop settings that cannot carry backend database or signing credentials."""

import re
from collections.abc import Mapping
from dataclasses import InitVar, dataclass
from urllib.parse import urlsplit

from clinic_management.config._validation import (
    invalid_setting,
    parse_timeout,
    positive_seconds,
    required,
)


@dataclass(frozen=True, kw_only=True)
class DesktopSettings:
    """Hold safe desktop settings, requiring HTTPS by default.

    A localhost-only HTTP exception is explicit, constructor-only and never
    inferred from the URL or a missing environment setting.
    """

    api_base_url: str
    request_timeout_seconds: float
    locale: str
    allow_insecure_localhost: InitVar[bool] = False

    def __post_init__(self, allow_insecure_localhost: bool) -> None:
        """Validate endpoint, timeout and locale without probing the network.

        Args:
            allow_insecure_localhost: Explicit local-development HTTP exception.

        Raises:
            ConfigurationError: If configuration is unsafe or malformed.
        """
        positive_seconds(self.request_timeout_seconds)
        try:
            parts = urlsplit(self.api_base_url)
            port = parts.port
        except ValueError:
            raise invalid_setting() from None
        local_http = (
            allow_insecure_localhost
            and parts.scheme == "http"
            and parts.hostname in {"localhost", "127.0.0.1", "::1"}
        )
        if (
            not parts.hostname
            or (parts.scheme != "https" and not local_http)
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or port == 0
            or not re.fullmatch(r"[a-z]{2,3}(?:[-_][A-Z]{2})?", self.locale)
        ):
            raise invalid_setting()


def load_desktop_settings(env: Mapping[str, str]) -> DesktopSettings:
    """Read only client configuration, rejecting an implicit HTTP downgrade.

    Args:
        env: Mapping supplied by the desktop composition root.

    Returns:
        Safe desktop settings without importing server configuration.

    Raises:
        ConfigurationError: If a required field or explicit exception is invalid.
    """
    exception = env.get("ALLOW_INSECURE_LOCALHOST", "false")
    if exception not in {"true", "false"}:
        raise invalid_setting()
    if exception == "true" and env.get("ENVIRONMENT") != "development":
        raise invalid_setting()
    return DesktopSettings(
        api_base_url=required(env, "API_BASE_URL"),
        request_timeout_seconds=parse_timeout(env, "REQUEST_TIMEOUT_SECONDS"),
        locale=required(env, "LOCALE"),
        allow_insecure_localhost=exception == "true",
    )
