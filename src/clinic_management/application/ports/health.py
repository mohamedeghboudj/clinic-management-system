"""Readiness-check boundary; concrete external checks arrive with adapters."""

from typing import Protocol

from clinic_management.application.contracts.health import ComponentHealth


class HealthCheck(Protocol):
    """Check one dependency within its configured timeout."""

    def check(self) -> ComponentHealth:
        """Return a safe result for both healthy and unavailable dependencies.

        Returns:
            Component status without secrets or raw exception messages.
        """
        ...
