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


def request(
    method: str, path: str, token: str, body: dict[str, object] | None = None
) -> dict[str, object]:
    """Call a fixed-host repository administration endpoint over HTTPS.

    Args:
        method: Explicit HTTP method selected by the reviewed policy operation.
        path: Repository-relative GitHub REST API path.
        token: Existing administration credential, never included in output.
        body: Public policy settings to serialize, when required.

    Returns:
        A decoded response object, or an empty object for no-content responses.

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
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected GitHub response type")
    return cast("dict[str, object]", value)


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
