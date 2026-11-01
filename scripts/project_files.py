"""Enumerate maintained project files without walking environments or secrets."""

from __future__ import annotations

import os
from pathlib import Path

IGNORED_DIRS = frozenset(
    {
        ".git",
        ".conda-env",
        ".venv",
        ".tools",
        ".cache",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "build",
        "dist",
        "htmlcov",
    }
)


def project_files(root: Path) -> tuple[Path, ...]:
    """Return maintained files while pruning generated directory trees.

    Args:
        root: Repository root explicitly selected by the caller.

    Returns:
        Sorted file paths, without symlink traversal or environment files.
    """
    files: list[Path] = []
    for directory, children, names in os.walk(root, followlinks=False):
        children[:] = [
            name
            for name in children
            if name not in IGNORED_DIRS
            and not (Path(directory) == root and name in {"logs", "exports", "backups"})
            and not (Path(directory) / name).is_symlink()
            and not name.endswith(".egg-info")
        ]
        for name in names:
            path = Path(directory) / name
            if not path.is_symlink() and (not name.startswith(".env") or name == ".env.example"):
                files.append(path)
    return tuple(sorted(files))
