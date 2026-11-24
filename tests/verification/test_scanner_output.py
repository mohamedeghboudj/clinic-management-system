"""Exercise the real scanner's fail-closed behavior and count-only CI output."""

from pathlib import Path

import pytest

from scripts.check_secrets import main


def test_detected_candidate_fails_without_printing_value_or_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A synthetic keyword finding fails the gate without exposing finding data.

    Args:
        tmp_path: Isolated temporary workspace.
        monkeypatch: Restores the working directory after scanning.
        capsys: Captures both output streams without publishing fixture content.
    """
    marker = "".join(("krypton", "marigold", "silver", "cedar"))
    target = tmp_path / "private_finding_metadata.py"
    target.write_text("password" + " = " + repr(marker) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main() == 1
    output = capsys.readouterr()
    assert output.out == "Secret scan: 1 candidate(s)\n"
    assert output.err == ""
    assert marker not in output.out + output.err
    assert str(target) not in output.out + output.err
    assert "Secret Keyword" not in output.out + output.err


def test_clean_workspace_passes_with_only_a_zero_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clean workspace succeeds while keeping the same minimal output contract.

    Args:
        tmp_path: Isolated temporary workspace.
        monkeypatch: Restores the working directory after scanning.
        capsys: Captures scanner output.
    """
    (tmp_path / "safe.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main() == 0
    output = capsys.readouterr()
    assert output.out == "Secret scan: 0 candidate(s)\n"
    assert output.err == ""
