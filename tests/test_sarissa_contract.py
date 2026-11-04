# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""F01 contract test — Zapis accepts what Sarissa actually emits (schema 1.3, tool "Sarissa").

The fixture mirrors Sarissa's ``build_export()`` (src/sarissa/main.py): schema_version "1.3",
tool "Sarissa" (capital S), challenges as stored minus ``challenge_timer_started_at``.
"""
from __future__ import annotations

import copy
import logging

import pytest
from fastapi.testclient import TestClient

from zapis.core.import_sarissa import SarissaImportError, parse_sarissa_export
from zapis.main import create_app

SARISSA_1_3_EXPORT = {
    "schema_version": "1.3",
    "tool": "Sarissa",
    "session": {
        "name": "DFIR-Cup-2026",
        "created_at": "2026-10-24T01:00:00Z",
        "updated_at": "2026-10-24T03:00:00Z",
        "exported_at": "2026-10-24T03:05:00Z",
        "timer": {"mode": "countdown", "duration_seconds": 10800, "started_at": "2026-10-24T01:00:00Z"},
    },
    "challenges": [
        {
            "id": "a1b2c3d4e5f6",
            "name": "Lost USB",
            "category": "Forensics",
            "points": 300,
            "notes": "Carved the FAT partition with photorec.",
            "status": "solved",
            "created_at": "2026-10-24T01:10:00Z",
            "solved_at": "2026-10-24T02:00:00Z",
            "challenge_time_seconds": 2940,
        },
        {
            "id": "0f9e8d7c6b5a",
            "name": "Phish Tank",
            "category": "",
            "points": 0,
            "notes": "",
            "status": "in_progress",
            "created_at": "2026-10-24T01:12:00Z",
            "solved_at": None,
            "challenge_time_seconds": 0,
        },
    ],
}


def test_accepts_sarissa_1_3_export(caplog):
    with caplog.at_level(logging.WARNING, logger="zapis.import_sarissa"):
        result = parse_sarissa_export(copy.deepcopy(SARISSA_1_3_EXPORT))
    assert result
    assert [e["challenge_name"] for e in result] == ["Lost USB", "Phish Tank"]
    assert {e["ctf_name"] for e in result} == {"DFIR-Cup-2026"}
    assert result[0]["approach"] == "Carved the FAT partition with photorec."
    assert caplog.text == ""  # 1.3 is a known version — no warning


def test_accepts_sarissa_1_3_export_via_route():
    r = TestClient(create_app()).post("/api/import/sarissa", json=SARISSA_1_3_EXPORT)
    assert r.status_code == 200
    assert len(r.json()) == 2


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
