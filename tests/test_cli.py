# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Tests for the Zapis CLI — `zapis create` and the no-subcommand launcher."""
from __future__ import annotations

import pytest

import zapis.main
from zapis import cli

BASE = [
    "create",
    "--challenge-name", "Test Challenge",
    "--ctf-name", "TestCTF 2026",
    "--category", "Forensics",
    "--difficulty", "2",
    "--tool", "Autopsy",
    "--tool", "FTK Imager",
    "--approach", "Mounted the image and found the flag in EXIF metadata.",
    "--flag", "FLAG{test_flag_123}",
]


def _with(**overrides) -> list[str]:
    args = list(BASE)
    for key, val in overrides.items():
        opt = "--" + key.replace("_", "-")
        args[args.index(opt) + 1] = val
    return args


def test_create_md(tmp_path, capsys):
    out = tmp_path / "w.md"
    assert cli.main(BASE + ["-o", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "FLAG{test_flag_123}" in text
    assert "Autopsy" in text and "FTK Imager" in text
    assert str(out) in capsys.readouterr().out


def test_create_html(tmp_path):
    out = tmp_path / "w.html"
    assert cli.main(BASE + ["--format", "html", "-o", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "<html" in text and "FLAG{test_flag_123}" in text


def test_create_pdf(tmp_path):
    out = tmp_path / "w.pdf"
    assert cli.main(BASE + ["--format", "pdf", "-o", str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")


def test_create_default_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(BASE) == 0
    assert (tmp_path / "test-challenge.md").is_file()


def test_create_invalid_category(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(_with(category="Hardware") + ["-o", str(tmp_path / "x.md")])
    assert exc.value.code == 2
    assert "category" in capsys.readouterr().err
    assert not (tmp_path / "x.md").exists()


def test_create_blank_flag(tmp_path, capsys):
    out = tmp_path / "x.md"
    assert cli.main(_with(flag="   ") + ["-o", str(out)]) == 1
    assert "error: flag" in capsys.readouterr().err
    assert not out.exists()


def test_no_subcommand_launches_web(monkeypatch):
    calls = []
    monkeypatch.setattr(zapis.main, "main", lambda: calls.append(True))
    assert cli.main([]) == 0
    assert calls == [True]
