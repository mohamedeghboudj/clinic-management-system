"""Validate new workflow safety and preserve the original Telegram Git blob."""

import hashlib
import re
from pathlib import Path
from typing import cast

import yaml  # deptry: ignore[DEP004] -- development-only workflow verification

LEGACY_PATH = Path(".github/workflows/telegram-notif.yml")
LEGACY_BLOB = "b81663a6e5b4611129f05367b7da406867fb4c06"  # pragma: allowlist secret


def workflow_issues(path: Path) -> list[str]:
    """Check declared workflow permissions, pinning and execution bounds.

    Args:
        path: New maintained workflow, excluding the preserved legacy exception.

    Returns:
        Safe diagnostics for missing guardrails or unpinned action references.
    """
    config = cast("dict[str, object]", yaml.safe_load(path.read_text(encoding="utf-8")))
    permissions = cast("dict[str, str]", config.get("permissions", {}))
    events = cast("dict[str, object]", config.get("on", {}))
    issues: list[str] = []
    if permissions.get("contents") != "read" or "pull_request_target" in events:
        issues.append(f"{path}: invalid default permission or untrusted-code trigger")
    jobs = cast("dict[str, dict[str, object]]", config.get("jobs", {}))
    for name, job in jobs.items():
        if "timeout-minutes" not in job:
            issues.append(f"{path}: {name} lacks a timeout")
        for step in cast("list[dict[str, object]]", job.get("steps", [])):
            action = step.get("uses")
            if isinstance(action, str) and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action):
                issues.append(f"{path}: action is not pinned to a full commit")
    return issues


def main() -> int:
    """Check every new workflow and the preserved notification blob identity.

    Returns:
        Zero when the original workflow and new workflow guardrails are intact.
    """
    content = LEGACY_PATH.read_bytes().replace(b"\r\n", b"\n")
    blob = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    digest = hashlib.sha1(blob, usedforsecurity=False).hexdigest()
    issues = [] if digest == LEGACY_BLOB else ["Original Telegram workflow blob changed"]
    for path in sorted(Path(".github/workflows").glob("*.yml")):
        if path != LEGACY_PATH:
            issues.extend(workflow_issues(path))
    for issue in issues:
        print(issue)
    print(f"Workflow contracts: {len(issues)} violation(s)")
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
