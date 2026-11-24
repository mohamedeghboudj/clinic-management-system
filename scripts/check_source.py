"""Enforce physical file, annotation, documentation and architecture contracts."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from scripts.project_files import project_files

MAX_SOURCE_LINES = 500
PACKAGE = "clinic_management"


def function_issues(path: Path, tree: ast.AST) -> list[str]:
    """Find undocumented or incompletely annotated function definitions.

    Args:
        path: Maintained Python source path for diagnostic locations.
        tree: Parsed syntax tree of the maintained source file.

    Returns:
        Safe file/line diagnostics, never function argument values.
    """
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        location = f"{path}:{node.lineno}: {node.name}"
        if not ast.get_docstring(node):
            issues.append(f"{location}: missing function docstring")
        if node.returns is None:
            issues.append(f"{location}: missing return annotation")
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        arguments += [arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None]
        for argument in arguments:
            if argument.arg not in {"self", "cls"} and argument.annotation is None:
                issues.append(f"{location}: missing annotation for {argument.arg}")
    return issues


def allowed_import(module: str, imported: str) -> bool:
    """Apply inward-only production dependency rules to an absolute import.

    Args:
        module: Importing module's dotted production package name.
        imported: Absolute dotted dependency name.

    Returns:
        Whether the declared import satisfies the layer's dependency boundary.
    """
    root = imported.split(".")[0]
    if module.startswith(f"{PACKAGE}.domain"):
        return root in sys.stdlib_module_names or imported.startswith(f"{PACKAGE}.domain")
    if module.startswith(f"{PACKAGE}.application"):
        return root in sys.stdlib_module_names or imported.startswith(
            (f"{PACKAGE}.domain", f"{PACKAGE}.application")
        )
    if module.startswith(f"{PACKAGE}.desktop"):
        return not imported.startswith(
            (f"{PACKAGE}.infrastructure", f"{PACKAGE}.config.server", f"{PACKAGE}.api", "tests")
        )
    return root != "tests"


def architecture_issues(path: Path, tree: ast.AST, root: Path) -> list[str]:
    """Reject prohibited direct imports, including relative production imports.

    Args:
        path: Maintained Python file to inspect.
        tree: Parsed source syntax tree.
        root: Repository root containing the ``src`` directory.

    Returns:
        Dependency-rule violations with file/line/module identifiers.
    """
    source = root / "src"
    if not path.is_relative_to(source):
        return []
    parts = list(path.relative_to(source).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    module = ".".join(parts)
    package = parts if path.name == "__init__.py" else parts[:-1]
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        dependencies: list[str] = []
        if isinstance(node, ast.Import):
            dependencies = [alias.name for alias in node.names]
        else:
            base = node.module or ""
            if node.level:
                base = ".".join([*package[: len(package) - node.level + 1], base]).strip(".")
            dependencies = [base, *(f"{base}.{alias.name}" for alias in node.names)]
        for dependency in dependencies:
            if not allowed_import(module, dependency):
                issues.append(f"{path}:{node.lineno}: prohibited import {dependency}")
    return issues


def main() -> int:
    """Check all maintained Python files using standard-library static analysis.

    Returns:
        Zero if all structural source rules pass, otherwise one.
    """
    root = Path.cwd().resolve()
    issues: list[str] = []
    for path in project_files(root):
        if path.suffix != ".py":
            continue
        text = path.read_text(encoding="utf-8")
        if len(text.splitlines()) > MAX_SOURCE_LINES:
            issues.append(f"{path}: exceeds {MAX_SOURCE_LINES} physical lines")
        tree = ast.parse(text, filename=str(path))
        issues.extend(function_issues(path, tree))
        issues.extend(architecture_issues(path, tree, root))
    for issue in issues:
        print(issue)
    print(f"Source contracts: {len(issues)} violation(s)")
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
