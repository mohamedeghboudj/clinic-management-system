"""Generate or verify the pip-tools input from the canonical dev dependency group."""

import argparse
import tomllib
from pathlib import Path
from typing import cast


def main() -> int:
    """Keep declared developer packages and lock input from drifting apart.

    Returns:
        Zero when synchronized or regenerated, otherwise one.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = cast("list[str]", metadata["dependency-groups"]["dev"])
    expected = (
        "# Generated from [dependency-groups].dev by scripts.requirements_input.\n"
        "# Edit pyproject.toml, regenerate this input, then compile the hash lock.\n"
        + "\n".join(dependencies)
        + "\n"
    )
    target = Path("requirements-dev.in")
    if args.write:
        target.write_text(expected, encoding="utf-8")
    elif target.read_text(encoding="utf-8") != expected:
        print("Developer dependency input drift: run python -m scripts.requirements_input --write")
        return 1
    print("Developer dependency declaration/input match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
