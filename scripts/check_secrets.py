"""Scan maintained text without printing candidate secret values."""

from pathlib import Path

from detect_secrets.core.secrets_collection import SecretsCollection  # deptry: ignore[DEP004]
from detect_secrets.settings import default_settings  # deptry: ignore[DEP004]

# These imports are intentionally development-only maintenance tooling.
from scripts.project_files import project_files


def main() -> int:
    """Detect candidate secrets while excluding generated hashes and binaries.

    Returns:
        Zero if no candidate secrets are found, otherwise one.
    """
    secrets = SecretsCollection()
    with default_settings():
        for path in project_files(Path.cwd().resolve()):
            if path.name == "requirements-dev.txt" or path.suffix in {".png", ".pdf", ".ico"}:
                continue
            if path.name.startswith((".coverage", "coverage.")):
                continue
            secrets.scan_file(str(path))
    findings = list(secrets)
    for filename, finding in findings:
        finding_kind = str(finding.type)
        print(f"{filename}:{finding.line_number}: {finding_kind}; inspect locally")
    print(f"Secret scan: {len(findings)} candidate(s)")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
