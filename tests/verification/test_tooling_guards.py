"""Protect real source packages from operational artifact exclusion mistakes."""

from pathlib import Path, PurePosixPath

from scripts.check_repository import forbidden
from scripts.check_source import allowed_import
from scripts.project_files import project_files


def test_export_adapter_source_is_not_mistaken_for_private_exports(tmp_path: Path) -> None:
    """Root exports are private artifacts; a nested source adapter remains checked."""
    source = tmp_path / "src" / "clinic_management" / "infrastructure" / "exports" / "worker.py"
    private = tmp_path / "exports" / "private.txt"
    environment = tmp_path / ".conda-env" / "generated.py"
    for path in (source, private, environment):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture", encoding="utf-8")
    found = project_files(tmp_path)
    assert source in found
    assert private not in found
    assert environment not in found
    assert (
        forbidden(PurePosixPath("src/clinic_management/infrastructure/exports/worker.py")) is False
    )
    assert forbidden(PurePosixPath("exports/private.txt")) is True
    assert forbidden(PurePosixPath(".env")) is True
    assert forbidden(PurePosixPath(".env.example")) is False


def test_domain_and_application_cannot_import_adapters() -> None:
    """Layer checks reject actual outward dependencies while permitting pure values."""
    assert allowed_import("clinic_management.domain.people", "decimal")
    assert not allowed_import("clinic_management.domain.people", "sqlalchemy")
    assert not allowed_import("clinic_management.domain.people", "clinic_management.infrastructure")
    assert allowed_import("clinic_management.application.people", "clinic_management.domain.people")
    assert not allowed_import("clinic_management.application.people", "clinic_management.desktop")
    assert not allowed_import(
        "clinic_management.desktop.clients", "clinic_management.config.server"
    )
