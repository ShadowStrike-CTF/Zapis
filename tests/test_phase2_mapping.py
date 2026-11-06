# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""P2-1 — fuller Sarissa mapping (category, time spent) and time_spent_minutes everywhere."""
from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from zapis import cli
from zapis.core import build_schema
from zapis.core.exporters.html import export_html
from zapis.core.exporters.markdown import export_markdown
from zapis.core.import_sarissa import parse_sarissa_export
from zapis.core.schema import WriteupSchema
from zapis.main import create_app


def export_with(challenge: dict) -> dict:
    data = {"schema_version": "1.3", "tool": "Sarissa", "session": {"name": "Cup"},
            "challenges": [{"name": "C1", "notes": "n", **challenge}]}
    return parse_sarissa_export(data)[0]


VALID = dict(challenge_name="T", ctf_name="C", category="Web", difficulty=1,
             tools_used=[], approach="a", flag="f", date="2026-11-05")


# --- Sarissa category -----------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Forensics", "Forensics"),
    ("forensics", "Forensics"),
    ("OSINT", "OSINT"),
    ("osint", "OSINT"),
    ("rEvErSe", "Reverse"),
    ("Hardware", ""),
    ("", ""),
    (5, ""),
    (None, ""),
    (["Web"], ""),
])
def test_import_category_mapping(raw, expected):
    assert export_with({"category": raw})["category"] == expected


def test_import_category_missing():
    assert export_with({})["category"] == ""


# --- Sarissa challenge_time_seconds --------------------------------------------------

@pytest.mark.parametrize("seconds, minutes", [
    (2940, 49),
    (0, 0),
    (59, 1),
    (29, 0),
    (3600, 60),
    (-60, 0),
    (True, 0),
    ("120", 0),
    (120.0, 0),
    (None, 0),
])
def test_import_time_spent_mapping(seconds, minutes):
    assert export_with({"challenge_time_seconds": seconds})["time_spent_minutes"] == minutes


def test_import_time_spent_missing():
    assert export_with({})["time_spent_minutes"] == 0


def test_import_still_ignores_other_sarissa_fields():
    # Ph3: solved_at now maps to date ("x" is not a date → ""); points/status/id stay unmapped.
    entry = export_with({"points": 300, "status": "solved", "solved_at": "x", "id": "abc"})
    assert set(entry) == {"challenge_name", "ctf_name", "category", "difficulty", "tools_used",
                          "approach", "flag", "time_spent_minutes", "date"}
    assert entry["date"] == ""


# --- Schema ------------------------------------------------------------------------

def test_schema_time_spent_defaults_to_zero():
    assert WriteupSchema(**VALID).time_spent_minutes == 0


@pytest.mark.parametrize("bad", [-1, -100, 1.5, "30", True, None])
def test_schema_rejects_bad_time_spent(bad):
    with pytest.raises(ValueError, match="time_spent_minutes"):
        WriteupSchema(**VALID, time_spent_minutes=bad)


def test_build_schema_is_the_one_validator():
    assert build_schema(VALID).category == "Web"
    with pytest.raises(ValueError, match="tools_used"):
        build_schema({**VALID, "tools_used": "nmap"})
    with pytest.raises(ValueError, match="flag must be a string"):
        build_schema({**VALID, "flag": 123})
    with pytest.raises(ValueError, match="approach"):
        build_schema({k: v for k, v in VALID.items() if k != "approach"})
    with pytest.raises(ValueError):
        build_schema({**VALID, "bogus": 1})
    with pytest.raises(ValueError):
        build_schema(["not", "a", "dict"])
    assert build_schema({**VALID, "date": ""}).date  # blank date → today


# --- Templates ----------------------------------------------------------------------

def test_time_spent_row_present_when_positive():
    schema = WriteupSchema(**VALID, time_spent_minutes=49)
    assert "**Author:** ShadowStrike\n**Time spent:** 49 min\n\n---" in export_markdown(schema)
    assert "<tr><th>Time spent</th><td>49 min</td></tr>" in export_html(schema)


def test_time_spent_row_absent_when_zero():
    schema = WriteupSchema(**VALID)
    md, html = export_markdown(schema), export_html(schema)
    assert "Time spent" not in md and "Time spent" not in html
    assert "**Author:** ShadowStrike\n\n---" in md
    assert "<tr><th>Author</th><td>ShadowStrike</td></tr>\n  </table>" in html


# --- Web + CLI -----------------------------------------------------------------------

def test_web_export_time_spent():
    client = TestClient(create_app())
    ok = client.post("/api/export/md", json={**VALID, "time_spent_minutes": 30})
    assert ok.status_code == 200 and "**Time spent:** 30 min" in ok.text
    bad = client.post("/api/export/md", json={**VALID, "time_spent_minutes": -5})
    assert bad.status_code == 422 and "time_spent_minutes" in bad.json()["detail"]
    nonstr = client.post("/api/export/md", json={**VALID, "flag": 5})
    assert nonstr.status_code == 422 and "flag" in nonstr.json()["detail"]


CLI_BASE = ["create", "--challenge-name", "T", "--ctf-name", "C", "--category", "Web",
            "--difficulty", "1", "--approach", "a", "--flag", "f"]


def test_cli_time_spent(tmp_path):
    out = tmp_path / "w.md"
    assert cli.main(CLI_BASE + ["--time-spent", "45", "-o", str(out)]) == 0
    assert "**Time spent:** 45 min" in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["-5", "1.5", "abc"])
def test_cli_time_spent_rejects_bad_values(tmp_path, capsys, bad):
    with pytest.raises(SystemExit) as exc:
        cli.main(CLI_BASE + ["--time-spent", bad, "-o", str(tmp_path / "x.md")])
    assert exc.value.code == 2
    assert "--time-spent" in capsys.readouterr().err
    assert not (tmp_path / "x.md").exists()


def test_schema_field_order_keeps_time_spent_last():
    assert [f.name for f in dataclasses.fields(WriteupSchema)][-1] == "time_spent_minutes"
