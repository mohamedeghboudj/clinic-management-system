"""M1 author verification of explicit settings and credential-safe failures."""

from dataclasses import replace
from typing import cast

import pytest

from clinic_management.config.desktop import DesktopSettings, load_desktop_settings
from clinic_management.config.server import ServerSettings, load_server_settings
from clinic_management.domain.shared.errors import ConfigurationError


def server_env() -> dict[str, str]:
    """Supply synthetic backend settings without any actual credentials.

    Returns:
        A complete test-only configuration using reserved invalid hostnames.
    """
    return {
        "DATABASE_URL": (
            "postgresql://fixture:placeholder@"  # pragma: allowlist secret
            "database.example.invalid/clinic?sslmode=verify-full"
        ),
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "CONNECT_TIMEOUT_SECONDS": "5",
        "TOKEN_ISSUER": "fixture-issuer",
        "TOKEN_AUDIENCE": "fixture-audience",
        "SIGNING_KEY": "fixture-" + "x" * 40,
    }


def desktop_env() -> dict[str, str]:
    """Supply only harmless synthetic desktop configuration.

    Returns:
        Required client settings without server credentials.
    """
    return {
        "API_BASE_URL": "https://api.example.invalid/api/v1",
        "REQUEST_TIMEOUT_SECONDS": "5",
        "LOCALE": "en",
    }


def test_server_settings_are_explicit_and_hide_secrets() -> None:
    """Valid values load without network access and secrets are absent from repr."""
    env = server_env()
    settings = load_server_settings(env)
    assert settings.environment == "test"
    assert settings.connect_timeout_seconds == 5
    assert env["SIGNING_KEY"] not in repr(settings)
    assert env["DATABASE_URL"] not in repr(settings)
    assert env["DATABASE_URL"] == settings.database_url


@pytest.mark.parametrize(
    "key,value",
    [
        ("ENVIRONMENT", "invented"),
        ("LOG_LEVEL", "anything"),
        ("TOKEN_ISSUER", ""),
        ("TOKEN_AUDIENCE", " "),
        ("SIGNING_KEY", ""),
        ("CONNECT_TIMEOUT_SECONDS", "0"),
        ("CONNECT_TIMEOUT_SECONDS", "nan"),
        ("CONNECT_TIMEOUT_SECONDS", "inf"),
        ("CONNECT_TIMEOUT_SECONDS", "not-a-number"),
        (
            "DATABASE_URL",
            "postgresql://fixture:placeholder@"  # pragma: allowlist secret
            "localhost/clinic?sslmode=verify-full",
        ),
        (
            "DATABASE_URL",
            "postgresql://fixture:placeholder@"  # pragma: allowlist secret
            "database.example.invalid/clinic",
        ),
        (
            "DATABASE_URL",
            "postgresql://fixture:placeholder@"  # pragma: allowlist secret
            "database.example.invalid:broken/clinic",
        ),
        (
            "DATABASE_URL",
            "mysql://fixture:placeholder@"  # pragma: allowlist secret
            "database.example.invalid/clinic",
        ),
    ],
)
def test_server_invalid_values_fail_without_rendering_inputs(key: str, value: str) -> None:
    """Startup failure never reflects a rejected connection string or secret."""
    env = server_env()
    env[key] = value
    with pytest.raises(ConfigurationError) as caught:
        load_server_settings(env)
    assert str(caught.value) == "INVALID_CONFIGURATION"
    assert "placeholder" not in repr(caught.value)


def test_missing_and_wrongly_typed_settings_fail() -> None:
    """Missing requirements and numeric-type bypasses are rejected explicitly."""
    with pytest.raises(ConfigurationError):
        load_server_settings({})
    settings: ServerSettings = load_server_settings(server_env())
    for timeout in (True, 0, -1, float("nan"), cast("float", "5")):
        with pytest.raises(ConfigurationError):
            replace(settings, connect_timeout_seconds=timeout)


def test_desktop_never_loads_backend_secrets() -> None:
    """Extra server keys do not become properties of desktop configuration."""
    env = {**server_env(), **desktop_env()}
    settings = load_desktop_settings(env)
    assert not hasattr(settings, "database_url")
    assert not hasattr(settings, "signing_key")
    assert settings.locale == "en"


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.invalid",
        "http://localhost:8000",
        "file:///private",
        "https://fixture:placeholder@api.example.invalid",  # pragma: allowlist secret
        "https://api.example.invalid?token=x",
        "https://api.example.invalid#fragment",
        "https://api.example.invalid:0",
        "https://api.example.invalid:broken",
    ],
)
def test_desktop_rejects_unsafe_endpoints(url: str) -> None:
    """Default client configuration cannot downgrade TLS or hide URL credentials."""
    env = desktop_env()
    env["API_BASE_URL"] = url
    with pytest.raises(ConfigurationError):
        load_desktop_settings(env)


def test_local_http_requires_explicit_development_exception() -> None:
    """A development exception is loopback-only and never inferred automatically."""
    env = {
        **desktop_env(),
        "API_BASE_URL": "http://localhost:8000",
        "ALLOW_INSECURE_LOCALHOST": "true",
    }
    with pytest.raises(ConfigurationError):
        load_desktop_settings(env)
    env["ENVIRONMENT"] = "development"
    assert load_desktop_settings(env).api_base_url == "http://localhost:8000"
    env["API_BASE_URL"] = "http://public.example.invalid"
    with pytest.raises(ConfigurationError):
        load_desktop_settings(env)
    env["ALLOW_INSECURE_LOCALHOST"] = "yes"
    with pytest.raises(ConfigurationError):
        load_desktop_settings(env)


def test_locale_and_timeout_are_required_client_values() -> None:
    """Invalid locale and nonfinite client deadlines fail before startup."""
    with pytest.raises(ConfigurationError):
        DesktopSettings(
            api_base_url="https://api.example.invalid",
            request_timeout_seconds=1,
            locale="bad locale",
        )
    with pytest.raises(ConfigurationError):
        DesktopSettings(
            api_base_url="https://api.example.invalid",
            request_timeout_seconds=float("inf"),
            locale="en",
        )
