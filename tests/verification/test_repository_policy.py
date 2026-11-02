"""Verify safe ruleset updates and fail-closed enforcement readback."""

from copy import deepcopy

import pytest

from scripts import configure_github as admin


def test_ruleset_apply_creates_then_updates_without_touching_other_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated application updates its named policy and preserves unrelated rules."""
    existing: list[dict[str, object]] = [{"id": 9, "name": "Unrelated"}]
    writes: list[tuple[str, str]] = []
    payload: dict[str, object] = {"name": "Main policy", "enforcement": "active"}

    def read(method: str, path: str, token: str) -> object:
        """Return an isolated synthetic listing for the requested repository.

        Args:
            method: Expected GET method.
            path: Requested listing path.
            token: Unused synthetic credential.

        Returns:
            Copied public ruleset summaries.
        """
        assert method == "GET" and path.startswith("/repos/example/rulesets?")
        return deepcopy(existing)

    def write(
        method: str, path: str, token: str, body: dict[str, object] | None = None
    ) -> dict[str, object]:
        """Record only the synthetic policy creation or update.

        Args:
            method: Expected POST or PUT method.
            path: Ruleset mutation path.
            token: Unused synthetic credential.
            body: Public policy payload.

        Returns:
            A synthetic API response.
        """
        assert body == payload
        writes.append((method, path))
        if method == "POST":
            existing.append({"id": 10, "name": body["name"]})
        return {"id": 10}

    monkeypatch.setattr(admin, "request_json", read)
    monkeypatch.setattr(admin, "request", write)
    admin.apply_rulesets("/repos/example", "", [payload])
    admin.apply_rulesets("/repos/example", "", [payload])
    assert writes == [("POST", "/repos/example/rulesets"), ("PUT", "/repos/example/rulesets/10")]
    assert existing[0] == {"id": 9, "name": "Unrelated"}
    assert len(existing) == 2


def test_duplicate_ruleset_names_fail_before_a_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    """An ambiguous same-name ruleset never selects an arbitrary target to update."""

    def read(method: str, path: str, token: str) -> object:
        """Return two conflicting policy summaries.

        Args:
            method: Unused GET method.
            path: Unused synthetic API path.
            token: Unused synthetic credential.

        Returns:
            An intentionally ambiguous listing.
        """
        return [{"id": 1, "name": "Duplicate"}, {"id": 2, "name": "Duplicate"}]

    monkeypatch.setattr(admin, "request_json", read)
    with pytest.raises(RuntimeError, match="Ambiguous duplicate"):
        admin.apply_rulesets("/repos/example", "", [{"name": "Duplicate"}])


def test_check_readback_rejects_wrong_app_even_when_context_names_match() -> None:
    """A similarly named status from another integration cannot satisfy readback."""
    expected = [{"context": "quality", "integration_id": 15368}]
    admin.require_status_checks(deepcopy(expected), expected, "main.checks")
    with pytest.raises(RuntimeError, match="integration_id"):
        admin.require_status_checks(
            [{"context": "quality", "integration_id": 1}], expected, "main.checks"
        )
    with pytest.raises(RuntimeError, match="contexts differ"):
        admin.require_status_checks(expected * 2, expected, "main.checks")


def test_ruleset_readback_rejects_admin_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    """An active ruleset with an unexpected bypass must fail verification."""
    payload = admin.configured_rulesets({"ruleset_files": [".github/rulesets/main.json"]})[0]
    observed = deepcopy(payload)
    observed["bypass_actors"] = [
        {"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"}
    ]

    def read(method: str, path: str, token: str) -> object:
        """Return the configured policy's synthetic summary.

        Args:
            method: Unused GET method.
            path: Unused synthetic API path.
            token: Unused synthetic credential.

        Returns:
            One policy summary.
        """
        return [{"id": 10, "name": payload["name"]}]

    def detail(
        method: str, path: str, token: str, body: dict[str, object] | None = None
    ) -> dict[str, object]:
        """Return a synthetic ruleset with an unexpected administrative bypass.

        Args:
            method: Unused GET method.
            path: Unused synthetic API path.
            token: Unused synthetic credential.
            body: Unused request body.

        Returns:
            The unsafe readback.
        """
        return observed

    monkeypatch.setattr(admin, "request_json", read)
    monkeypatch.setattr(admin, "request", detail)
    with pytest.raises(RuntimeError, match="bypass_actors"):
        admin.check_rulesets("/repos/example", "", [payload])
