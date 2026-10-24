# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Tests for Phase 6 — Sarissa export JSON import via POST /api/import/sarissa."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from zapis.main import create_app

URL = "/api/import/sarissa"


@pytest.fixture
def client():
    return TestClient(create_app())


def sarissa_export(**overrides):
    data = {
        "schema_version": "1.0",
        "tool": "sarissa",
        "session": {
            "name": "DFIR-Cup-2026",
            "created_at": "2026-10-24T01:00:00Z",
            "updated_at": "2026-10-24T03:00:00Z",
            "exported_at": "2026-10-24T03:05:00Z",
            "timer": {"duration_seconds": 10800, "started_at": "2026-10-24T01:00:00Z"},
        },
        "challenges": [
            {"name": "Lost USB", "notes": "Carved the FAT partition with <photorec>."},
        ],
    }
    data.update(overrides)
    return data


def blank(challenge_name, ctf_name, approach):
    return {
        "challenge_name": challenge_name,
        "ctf_name": ctf_name,
        "category": "",
        "difficulty": 0,
        "tools_used": [],
        "approach": approach,
        "flag": "",
    }


def test_import_sarissa_valid_single_challenge(client):
    r = client.post(URL, json=sarissa_export())
    assert r.status_code == 200
    assert r.json() == [
        blank("Lost USB", "DFIR-Cup-2026", "Carved the FAT partition with <photorec>.")
    ]


def test_import_sarissa_valid_multi_challenge(client):
    challenges = [
        {"name": "Lost USB", "notes": "photorec"},
        {"name": "Phish Tank", "notes": "Header analysis."},
        {"name": "Registry Run", "notes": ""},
    ]
    r = client.post(URL, json=sarissa_export(challenges=challenges))
    assert r.status_code == 200
    entries = r.json()
    assert [e["challenge_name"] for e in entries] == ["Lost USB", "Phish Tank", "Registry Run"]
    assert [e["approach"] for e in entries] == ["photorec", "Header analysis.", ""]
    assert {e["ctf_name"] for e in entries} == {"DFIR-Cup-2026"}


def test_import_sarissa_empty_challenges(client):
    r = client.post(URL, json=sarissa_export(challenges=[]))
    assert r.status_code == 200
    assert r.json() == [blank("", "DFIR-Cup-2026", "")]


def test_import_sarissa_missing_notes(client):
    data = sarissa_export(challenges=[{"name": "No Notes"}, {"notes": "No name."}])
    del data["session"]
    r = client.post(URL, json=data)
    assert r.status_code == 200
    assert r.json() == [blank("No Notes", "", ""), blank("", "", "No name.")]


def test_import_sarissa_wrong_schema_version(client):
    r = client.post(URL, json=sarissa_export(schema_version="2.0"))
    assert r.status_code == 422
    assert "schema_version" in r.json()["detail"]


def test_import_sarissa_wrong_tool(client):
    r = client.post(URL, json=sarissa_export(tool="treska"))
    assert r.status_code == 422
    assert "tool" in r.json()["detail"]


def test_import_sarissa_malformed_json(client):
    r = client.post(URL, content=b'{"schema_version": "1.0", ', headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    for bad in ([], sarissa_export(challenges={"name": "x"}), sarissa_export(challenges=["x"])):
        assert client.post(URL, json=bad).status_code == 422
