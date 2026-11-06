# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""F01 / Ph3 contract test — Zapis accepts what Sarissa actually emits (schema 1.3, tool "Sarissa").

The fixture (tests/fixtures/sarissa_1_3_export.json — the single reference export, INV-P3-5)
mirrors Sarissa's ``build_export()`` (src/sarissa/main.py): schema_version "1.3", tool "Sarissa"
(capital S), challenges as stored minus ``challenge_timer_started_at``.
"""
from __future__ import annotations

import copy
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zapis.core.import_sarissa import IMPORT_KEYS, SarissaImportError, parse_sarissa_export
from zapis.main import create_app

FIXTURE = Path(__file__).parent / "fixtures" / "sarissa_1_3_export.json"
SARISSA_1_3_EXPORT = json.loads(FIXTURE.read_text(encoding="utf-8"))

# Every mapped field, for both fixture challenges (Ph3: solved_at → date).
EXPECTED = [
    {
        "challenge_name": "Lost USB",
        "ctf_name": "DFIR-Cup-2026",
        "category": "Forensics",
        "difficulty": 0,
        "tools_used": [],
        "approach": "Carved the FAT partition with photorec.",
        "flag": "",
        "time_spent_minutes": 49,  # 2940 s
        "date": "2026-10-24",      # solved_at 2026-10-24T02:00:00Z
    },
    {
        "challenge_name": "Phish Tank",
        "ctf_name": "DFIR-Cup-2026",
        "category": "",
        "difficulty": 0,
        "tools_used": [],
        "approach": "",
        "flag": "",
        "time_spent_minutes": 0,
        "date": "",                # solved_at null
    },
]
UNMAPPED = ("id", "points", "status", "created_at", "solved_at", "challenge_time_seconds", "name", "notes")


def test_fixture_has_every_sarissa_1_3_field():
    for challenge in SARISSA_1_3_EXPORT["challenges"]:
        for key in ("id", "name", "category", "points", "notes", "status", "created_at",
                    "solved_at", "challenge_time_seconds"):
            assert key in challenge, key


def test_accepts_sarissa_1_3_export(caplog):
    with caplog.at_level(logging.WARNING, logger="zapis.import_sarissa"):
        result = parse_sarissa_export(copy.deepcopy(SARISSA_1_3_EXPORT))
    assert result == EXPECTED
    assert caplog.text == ""  # 1.3 is a known version — no warning


def test_contract_entry_keys_are_exactly_import_keys():
    for entry in parse_sarissa_export(copy.deepcopy(SARISSA_1_3_EXPORT)):
        assert list(entry) == list(IMPORT_KEYS)
        for key in UNMAPPED:
            assert key not in entry, key


def test_solved_challenge_gets_date_unsolved_leaves_blank():
    solved, unsolved = parse_sarissa_export(copy.deepcopy(SARISSA_1_3_EXPORT))
    assert solved["date"] == "2026-10-24"
    assert unsolved["date"] == ""


_MISSING = object()


@pytest.mark.parametrize("solved_at, date", [
    ("2026-10-24T02:00:00Z", "2026-10-24"),
    ("2026-10-24T23:59:59+00:00", "2026-10-24"),
    ("2026-10-24", "2026-10-24"),
    (None, ""),
    ("", ""),
    ("garbage", ""),
    ("2026-13-01T00:00:00Z", ""),
    ("2026-02-30T00:00:00Z", ""),
    ("2026-W43-6", ""),
    ("20261024T020000Z", ""),
    (123, ""),
    (True, ""),
    (_MISSING, ""),
])
def test_solved_at_date_mapping(solved_at, date):
    challenge = {"name": "C1"}
    if solved_at is not _MISSING:
        challenge["solved_at"] = solved_at
    data = {"schema_version": "1.3", "tool": "Sarissa", "challenges": [challenge]}
    assert parse_sarissa_export(data)[0]["date"] == date


def test_accepts_sarissa_1_3_export_via_route():
    r = TestClient(create_app()).post("/api/import/sarissa", json=SARISSA_1_3_EXPORT)
    assert r.status_code == 200
    assert r.json() == EXPECTED


def test_route_is_stateless_between_imports():
    # Ph3 / INV-P3-3: the server keeps no working set — the additive merge is the browser's job
    # (tests/test_e2e_import.py). A second import returns only its own challenges.
    client = TestClient(create_app())
    first = client.post("/api/import/sarissa", json=SARISSA_1_3_EXPORT)
    other = copy.deepcopy(SARISSA_1_3_EXPORT)
    other["challenges"] = [{"name": "Cookie Jar", "category": "web", "solved_at": "2026-10-25T00:10:00Z"}]
    second = client.post("/api/import/sarissa", json=other)
    assert first.status_code == second.status_code == 200
    assert [e["challenge_name"] for e in first.json()] == ["Lost USB", "Phish Tank"]
    assert second.json() == [{
        "challenge_name": "Cookie Jar", "ctf_name": "DFIR-Cup-2026", "category": "Web",
        "difficulty": 0, "tools_used": [], "approach": "", "flag": "",
        "time_spent_minutes": 0, "date": "2026-10-25",
    }]


@pytest.mark.parametrize("version", ["1.0", "1.3"])
def test_known_schema_versions_no_warning(version, caplog):
    data = copy.deepcopy(SARISSA_1_3_EXPORT) | {"schema_version": version}
    with caplog.at_level(logging.WARNING, logger="zapis.import_sarissa"):
        assert parse_sarissa_export(data)
    assert caplog.text == ""


@pytest.mark.parametrize("version", ["2.0", "1.1", None, 13])
def test_unknown_schema_version_warns_not_rejected(version, caplog):
    data = copy.deepcopy(SARISSA_1_3_EXPORT) | {"schema_version": version}
    with caplog.at_level(logging.WARNING, logger="zapis.import_sarissa"):
        assert parse_sarissa_export(data)
    assert "schema_version" in caplog.text


@pytest.mark.parametrize("tool", ["Sarissa", "sarissa", "SARISSA", "sArIsSa"])
def test_tool_case_insensitive(tool):
    assert parse_sarissa_export(copy.deepcopy(SARISSA_1_3_EXPORT) | {"tool": tool})


@pytest.mark.parametrize("tool", ["Treska", "", None, 1, " sarissa"])
def test_tool_still_rejected_when_not_sarissa(tool):
    data = copy.deepcopy(SARISSA_1_3_EXPORT) | {"tool": tool}
    if tool is None:
        del data["tool"]
    with pytest.raises(SarissaImportError):
        parse_sarissa_export(data)
