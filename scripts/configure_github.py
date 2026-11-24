"""Apply or inspect the reviewed repository policy without exposing credentials."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast


def load_token() -> str:
    """Read an existing administration credential without logging or persisting it.

    Returns:
        An environment token or the authenticated GitHub CLI credential.

    Raises:
        RuntimeError: If no noninteractive authenticated route exists.
    """
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    cli = shutil.which("gh")
    if cli is None:
        windows_cli = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "GitHub CLI/gh.exe"
        if windows_cli.is_file():
            cli = str(windows_cli)
    if cli is not None:
        result = subprocess.run(  # noqa: S603 -- fixed auth command, resolved executable
            [cli, "auth", "token"], capture_output=True, text=True, check=False, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise RuntimeError(
        "Authenticate GitHub CLI or supply GH_TOKEN privately; never paste tokens in chat"
    )


def request_json(
    method: str, path: str, token: str, body: dict[str, object] | None = None
) -> object:
    """Call a fixed-host repository administration endpoint over HTTPS.

    Args:
        method: Explicit HTTP method selected by the reviewed policy operation.
        path: Repository-relative GitHub REST API path.
        token: Existing administration credential, never included in output.
        body: Public policy settings to serialize, when required.

    Returns:
        Decoded JSON, or an empty object for no-content responses.

    Raises:
        RuntimeError: If the API rejects the request or returns an unexpected body.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clinic-management-repository-policy",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310 -- fixed HTTPS host
            raw = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub rejected {method} {path}: HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("GitHub administration endpoint is unreachable") from None
    value: object = json.loads(raw) if raw else {}
    return value


def request(
    method: str, path: str, token: str, body: dict[str, object] | None = None
) -> dict[str, object]:
    """Request a repository administration response with an object shape.

    Args:
        method: Explicit HTTP method.
        path: GitHub repository API path.
        token: Private existing administration credential.
        body: Optional public policy fields.

    Returns:
        The decoded JSON object.

    Raises:
        RuntimeError: If the API response is not an object.
    """
    value = request_json(method, path, token, body)
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected GitHub response type")
    return cast("dict[str, object]", value)


def ruleset_index(base: str, token: str) -> dict[str, dict[str, object]]:
    """List repository-owned rulesets without changing unrelated policies.

    Args:
        base: Authorized repository API base path.
        token: Private existing administration credential.

    Returns:
        Repository rulesets indexed by unique name.

    Raises:
        RuntimeError: If response shapes or duplicate names are ambiguous.
    """
    value = request_json("GET", base + "/rulesets?includes_parents=false&per_page=100", token)
    if not isinstance(value, list) or len(value) >= 100:
        raise RuntimeError("Unexpected or incomplete repository ruleset listing")
    result: dict[str, dict[str, object]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise RuntimeError("Unexpected ruleset summary")
        row = cast("dict[str, object]", item)
        name = str(row["name"])
        if name in result:
            raise RuntimeError("Ambiguous duplicate ruleset name: " + name)
        result[name] = row
    return result


def configured_rulesets(policy: dict[str, object]) -> list[dict[str, object]]:
    """Load the explicit ruleset documents beside the reviewed repository policy.

    Args:
        policy: Parsed public repository policy.

    Returns:
        The reviewed ruleset payloads.
    """
    return [
        cast("dict[str, object]", json.loads(Path(path).read_text(encoding="utf-8")))
        for path in cast("list[str]", policy["ruleset_files"])
    ]


def apply_rulesets(base: str, token: str, payloads: list[dict[str, object]]) -> None:
    """Create or update named rulesets while preserving other administrators' rules.

    Args:
        base: Authorized repository API base path.
        token: Private existing administration credential.
        payloads: Reviewed ruleset definitions.
    """
    existing = ruleset_index(base, token)
    for payload in payloads:
        name = str(payload["name"])
        current = existing.get(name)
        path = base + "/rulesets"
        if current is not None:
            path += "/" + str(current["id"])
        request("PUT" if current else "POST", path, token, payload)
        print("Applied ruleset: " + name)


def check_rulesets(base: str, token: str, payloads: list[dict[str, object]]) -> list[int]:
    """Read back active rules, conditions and bypasses without mutating GitHub.

    Args:
        base: Authorized repository API base path.
        token: Private existing administration credential.
        payloads: Reviewed ruleset definitions.

    Returns:
        Verified ruleset identifiers.

    Raises:
        RuntimeError: If any configured ruleset is absent or differs.
    """
    existing = ruleset_index(base, token)
    identifiers: list[int] = []
    for payload in payloads:
        name = str(payload["name"])
        current = existing.get(name)
        if current is None:
            raise RuntimeError("Required ruleset missing: " + name)
        identifier = cast("int", current["id"])
        observed = request("GET", base + "/rulesets/" + str(identifier), token)
        expected_header = {key: value for key, value in payload.items() if key != "rules"}
        require_values(observed, expected_header, name)
        rules = cast("list[dict[str, object]]", observed.get("rules", []))
        expected_rules = cast("list[dict[str, object]]", payload["rules"])
        indexed = {str(rule["type"]): rule for rule in rules}
        if set(indexed) != {rule["type"] for rule in expected_rules}:
            raise RuntimeError("Ruleset rule types differ: " + name)
        for rule in expected_rules:
            require_values(indexed[str(rule["type"])], rule, name + "." + str(rule["type"]))
        identifiers.append(identifier)
    return identifiers


def apply_policy(policy: dict[str, object], token: str) -> None:
    """Apply only the specific reviewed settings for the configured repository.

    Args:
        policy: Parsed public repository-policy document.
        token: Existing credential with repository administration rights.

    Raises:
        RuntimeError: If administration is unavailable or any mutation fails.
    """
    repo = str(policy["repository"])
    if repo != "mohamedeghboudj/clinic-management-system":
        raise RuntimeError("Policy repository does not match the authorized target")
    base = "/repos/" + repo
    metadata = request("GET", base, token)
    permissions = cast("dict[str, object]", metadata.get("permissions", {}))
    if permissions.get("admin") is not True:
        raise RuntimeError("The credential lacks administration access to this repository")
    operations = (
        ("PATCH", base, "repository_settings"),
        ("PUT", base + "/actions/permissions", "actions_permissions"),
        ("PUT", base + "/actions/permissions/selected-actions", "selected_actions"),
        ("PUT", base + "/actions/permissions/workflow", "workflow_permissions"),
        ("PUT", base + "/branches/main/protection", "branch_protection"),
    )
    for method, path, key in operations:
        request(method, path, token, cast("dict[str, object]", policy[key]))
        print(f"Applied {key}")
    request("PUT", base + "/vulnerability-alerts", token)
    print("Enabled dependency vulnerability alerts")
    request("PUT", base + "/automated-security-fixes", token)
    print("Enabled automated dependency security fixes")
    request("PATCH", base, token, {"security_and_analysis": policy["security_and_analysis"]})
    print("Applied secret scanning and push protection")
    apply_rulesets(base, token, configured_rulesets(policy))


def require_status_checks(observed: object, expected: list[dict[str, object]], prefix: str) -> None:
    """Compare check names and originating apps independently of API ordering.

    Args:
        observed: Current required-status-check list.
        expected: Reviewed context/app bindings.
        prefix: Public policy location used in safe diagnostics.

    Raises:
        RuntimeError: If contexts, list shape or originating apps differ.
    """
    if not isinstance(observed, list):
        raise RuntimeError(f"Policy setting missing: {prefix}")
    rows = cast("list[dict[str, object]]", observed)
    indexed = {row["context"]: row for row in rows}
    if len(indexed) != len(rows) or set(indexed) != {row["context"] for row in expected}:
        raise RuntimeError(f"Required check contexts differ: {prefix}")
    for row in expected:
        require_values(indexed[row["context"]], row, prefix)


def require_values(observed: dict[str, object], expected: dict[str, object], prefix: str) -> None:
    """Verify the configured subset, normalizing GitHub enabled-flag wrappers.

    Args:
        observed: Current safe repository administration response.
        expected: Reviewed subset that must be actively enforced.
        prefix: Technical setting location for mismatch diagnostics.

    Raises:
        RuntimeError: If an observed setting differs from the reviewed policy.
    """
    for key, wanted in expected.items():
        actual = observed.get(key)
        location = f"{prefix}.{key}"
        if key == "required_status_checks" and isinstance(wanted, list):
            require_status_checks(actual, cast("list[dict[str, object]]", wanted), location)
            continue
        if isinstance(wanted, dict):
            if not isinstance(actual, dict):
                raise RuntimeError(f"Policy setting missing: {location}")
            require_values(cast("dict[str, object]", actual), wanted, location)
            continue
        if isinstance(wanted, bool) and isinstance(actual, dict):
            actual = actual.get("enabled")
        if key in {"contexts", "patterns_allowed"} and isinstance(actual, list):
            actual = sorted(cast("list[str]", actual))
            wanted = sorted(cast("list[str]", wanted))
        if actual != wanted:
            raise RuntimeError(f"Policy setting does not match: {location}")


def check_policy(policy: dict[str, object], token: str) -> None:
    """Inspect enforcement without printing credentials or security alert contents.

    Args:
        policy: Reviewed public repository policy.
        token: Existing credential authorized to read administration settings.
    """
    base = "/repos/" + str(policy["repository"])
    metadata = request("GET", base, token)
    require_values(metadata, cast("dict[str, object]", policy["repository_settings"]), "repository")
    require_values(
        cast("dict[str, object]", metadata.get("security_and_analysis", {})),
        cast("dict[str, object]", policy["security_and_analysis"]),
        "security",
    )
    protection = request("GET", base + "/branches/main/protection", token)
    require_values(protection, cast("dict[str, object]", policy["branch_protection"]), "main")
    routes = (
        ("actions_permissions", "/actions/permissions"),
        ("selected_actions", "/actions/permissions/selected-actions"),
        ("workflow_permissions", "/actions/permissions/workflow"),
    )
    for key, suffix in routes:
        require_values(
            request("GET", base + suffix, token), cast("dict[str, object]", policy[key]), key
        )
    request("GET", base + "/vulnerability-alerts", token)
    require_values(
        request("GET", base + "/automated-security-fixes", token),
        {"enabled": True},
        "security_fixes",
    )
    reviews = cast("dict[str, object]", protection.get("required_pull_request_reviews", {}))
    checks = cast("dict[str, object]", protection.get("required_status_checks", {}))
    result = {
        "required_approvals": reviews.get("required_approving_review_count"),
        "dismiss_stale_reviews": reviews.get("dismiss_stale_reviews"),
        "code_owner_review": reviews.get("require_code_owner_reviews"),
        "required_checks": checks.get("contexts"),
        "actions": request("GET", base + "/actions/permissions/workflow", token),
        "verified_ruleset_ids": check_rulesets(base, token, configured_rulesets(policy)),
        "policy_verified": True,
    }
    print(json.dumps(result, indent=2))


def main() -> int:
    """Inspect the prepared policy, or explicitly apply/check it with credentials.

    Returns:
        Zero for successful policy inspection/application, otherwise one.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    policy = cast(
        "dict[str, object]",
        json.loads(Path(".github/repository-policy.json").read_text(encoding="utf-8")),
    )
    if not args.apply and not args.check:
        print(json.dumps(policy, indent=2))
        return 0
    try:
        token = load_token()
        if args.apply:
            apply_policy(policy, token)
        check_policy(policy, token)
    except RuntimeError as error:
        print(str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
