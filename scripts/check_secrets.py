"""Scan maintained text and report only a candidate count to CI.
"""

import json
from pathlib import Path

from detect_secrets.core.secrets_collection import SecretsCollection  # deptry: ignore[DEP004]
from detect_secrets.settings import default_settings  # deptry: ignore[DEP004]

# Development‑only maintenance tooling.
from scripts.project_files import project_files


def main() -> int:
    """Detect candidate secrets while excluding generated hashes and binaries.

    Returns:
        Zero if no candidate secrets are found, otherwise one.
    """
    # Load baseline – required for CI correctness.
    # Locate baseline relative to repository root (the directory containing this script)
repo_root = Path(__file__).resolve().parent
baseline_path = repo_root / ".secrets.baseline"
    if not baseline_path.is_file():
        print(f"Error: baseline file not found at {baseline_path}")
        raise SystemExit(1)
    from detect_secrets.core.baseline import load, load_from_file
    try:
        baseline_dict = load_from_file(str(baseline_path))
        baseline_collection = load(baseline_dict)
    except (OSError, json.JSONDecodeError) as exc:
        # Critical error: malformed or unreadable baseline → abort.
        print(f"Error: could not load baseline ({baseline_path}): {exc}")
        raise SystemExit(1)
    # Scan maintained project files.
    secrets = SecretsCollection()
    with default_settings():
        for path in project_files(Path.cwd().resolve()):
            if path.name == "requirements-dev.txt" or path.suffix in {".png", ".pdf", ".ico"}:
                continue
            if path.name.startswith((".coverage", "coverage.")):
                continue
            secrets.scan_file(str(path))
    # Apply baseline subtraction.
    secrets = secrets - baseline_collection
    findings = list(secrets)
    print(f"Secret scan: {len(findings)} candidate(s)")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
