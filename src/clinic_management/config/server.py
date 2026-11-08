"""Backend-only settings containing no implicit environment or network reads."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

from clinic_management.config._validation import (
    ENVIRONMENTS,
    LOG_LEVELS,
    invalid_setting,
    parse_timeout,
    positive_seconds,
    required,
)


@dataclass(frozen=True, kw_only=True)
class ServerSettings:
    """Hold backend secrets without exposing them through default repr output.

    No serializer or desktop response accepts this class. Signing algorithm,
    rotation and cryptographic key validation belong to M2's identity adapter.
    """

    database_url: str = field(repr=False)
    environment: str
    log_level: str
    connect_timeout_seconds: float
    token_issuer: str
    token_audience: str
    signing_key: str = field(repr=False)

    def __post_init__(self) -> None:
        """Reject missing values, unsupported environments and unsafe DB URLs.

        Raises:
            ConfigurationError: If any required configuration is invalid.
        """
        positive_seconds(self.connect_timeout_seconds)
        if self.environment not in ENVIRONMENTS or self.log_level not in LOG_LEVELS:
            raise invalid_setting()
        if any(
            not value.strip()
            for value in (self.token_issuer, self.token_audience, self.signing_key)
        ):
            raise invalid_setting()
        try:
            parts = urlsplit(self.database_url)
            port = parts.port
            query = parse_qs(parts.query)
        except ValueError:
            raise invalid_setting() from None
        if (
            parts.scheme not in {"postgresql", "postgresql+psycopg"}
            or not parts.hostname
            or parts.hostname in {"localhost", "127.0.0.1", "::1"}
            or not parts.username
            or not parts.password
            or not parts.path.strip("/")
            or parts.fragment
            or port == 0
            or query.get("sslmode") != ["verify-full"]
        ):
            raise invalid_setting()


def load_server_settings(env: Mapping[str, str]) -> ServerSettings:
    """Read required backend settings from an explicitly supplied mapping.

    Args:
        env: Backend environment, passed only by the server composition root.

    Returns:
        A validated secret-bearing server configuration.

    Raises:
        ConfigurationError: If any required field is absent or invalid.
    """
    return ServerSettings(
        database_url=required(env, "DATABASE_URL"),
        environment=required(env, "ENVIRONMENT"),
        log_level=required(env, "LOG_LEVEL"),
        connect_timeout_seconds=parse_timeout(env, "CONNECT_TIMEOUT_SECONDS"),
        token_issuer=required(env, "TOKEN_ISSUER"),
        token_audience=required(env, "TOKEN_AUDIENCE"),
        signing_key=required(env, "SIGNING_KEY"),
    )
