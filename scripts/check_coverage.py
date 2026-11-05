"""Enforce the branch threshold per measured implementation module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast


class Summary(TypedDict):
    """Describe the coverage.py summary fields consumed by this checker."""

    num_branches: int
    covered_branches: int
    num_statements: int
    covered_lines: int


class FileResult(TypedDict):
    """Describe one measured module in the coverage JSON report."""

    summary: Summary


class CoverageReport(TypedDict):
    """Describe the file mapping emitted by coverage.py JSON output."""

    files: dict[str, FileResult]


def main() -> int:
    """Check branch coverage, or statement coverage for branch-free modules.

    Returns:
        Zero if each implemented measured module reaches 80 percent.
    """
    report = cast("CoverageReport", json.loads(Path("coverage.json").read_text(encoding="utf-8")))
    failures = 0
    for path, result in report["files"].items():
        summary = result["summary"]
        branches = summary["num_branches"]
        total = branches or summary["num_statements"]
        covered = summary["covered_branches"] if branches else summary["covered_lines"]
        if total and covered / total < 0.8:
            print(f"{path}: {covered}/{total} {'branches' if branches else 'statements'} < 80%")
            failures += 1
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
