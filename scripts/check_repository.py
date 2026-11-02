"""Reject tracked local environments, secret files and operational data artifacts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path, PurePosixPath


def forbidden(path: PurePosixPath) -> bool:
    """Recognize private/generated artifacts without reading any file contents.

    Args:
        path: Repository-relative tracked path from Git's index.

    Returns:
        Whether this path violates the no-local-secrets/data repository rule.
    """
    excluded = {".conda-env", ".venv", "__pycache__"}
    return (
        bool(excluded.intersection(path.parts))
        or path.parts[0] in {"logs", "exports", "backups"}
        or (path.name.startswith(".env") and path.name != ".env.example")
        or path.suffix in {".db", ".dump", ".key", ".pem"}
        or path.name.endswith((".sqlite", ".sqlite3"))
    )


def main() -> int:
    """Inspect tracked paths, including accidentally force-added ignored files.

    Returns:
        Zero when no forbidden artifact is tracked, otherwise one.
    """
    git = shutil.which("git")
    if git is None:
        print("Git is required to verify tracked artifact paths")
        return 1
    root = Path.cwd().resolve()
    result = subprocess.run(  # noqa: S603 -- fixed read-only command and repository root
        [git, "-c", f"safe.directory={root.as_posix()}", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if result.returncode:
        print("Cannot inspect repository index")
        return 1
    paths = [PurePosixPath(value.decode("utf-8")) for value in result.stdout.split(b"\0") if value]
    rejected = sum(forbidden(path) for path in paths)
    print(f"Forbidden tracked artifacts: {rejected}")
    return int(bool(rejected))


if __name__ == "__main__":
    raise SystemExit(main())
