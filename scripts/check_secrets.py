"""Scan maintained text and report only a candidate count to CI."""

from __future__ import annotations

import json
from pathlib import Path

from detect_secrets.core.secrets_collection import SecretsCollection  # deptry: ignore[DEP004]
from detect_secrets.settings import default_settings  # deptry: ignore[DEP004]

# Development-only maintenance tooling.
from scripts.project_files import project_files


def main() -> int:
    """Detect candidate secrets while excluding generated hashes and binaries.

    Returns:
        Zero if no candidate secrets are found, otherwise one.
    """
    baseline_path = Path(__file__).resolve().parents[1] / ".secrets.baseline"
    try:
        baseline = SecretsCollection.load_from_baseline(
            json.loads(baseline_path.read_text(encoding="utf-8"))
        )
    except OSError, ValueError, TypeError, KeyError:
        print("Secret scan failed: unreadable baseline")
        return 1

    root = Path.cwd()
    secrets = SecretsCollection()
    with default_settings():
        for path in project_files(root):
            if path.name in {"requirements-dev.txt", ".secrets.baseline"} or path.suffix in {
                ".png",
                ".pdf",
                ".ico",
            }:
                continue
            if path.name.startswith((".coverage", "coverage.")):
                continue
            secrets.scan_file(str(path.relative_to(root)))

    findings = list(secrets - baseline)
    print(f"Secret scan: {len(findings)} candidate(s)")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
