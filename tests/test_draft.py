# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""P2-2 — draft save/load (core/draft.py + /api/draft/*)."""
from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from zapis.core import draft, import_sarissa
from zapis.core.draft import DraftError, build_draft, normalise_entry, parse_draft
from zapis.core.schema import FIELD_NAMES
from zapis.main import create_app

SAVE, LOAD = "/api/draft/save", "/api/draft/load"

COMPLETE = {
    "challenge_name": "Lost USB", "ctf_name": "DFIR-Cup-2026", "category": "Forensics",
    "difficulty": 2, "tools_used": ["photorec"], "approach": "Carved it.", "flag": "flag{usb}",
    "notes": "n", "author": "R", "date": "2026-11-05", "time_spent_minutes": 49,
}
# Incomplete on purpose — drafts hold work in progress.
INCOMPLETE = {"challenge_name": "Phish Tank", "ctf_name": "DFIR-Cup-2026", "category": "",
              "difficulty": 0, "tools_used": [], "approach": "", "flag": ""}


@pytest.fixture
def client():
    return TestClient(create_app())


def saved(client, writeups, active_index=0):
    r = client.post(SAVE, json={"writeups": writeups, "active_index": active_index})
    assert r.status_code == 200, r.text
    return r


def a_draft(**overrides):
    return {"tool": "zapis", "draft_version": "1.0", "saved_at": "2026-11-05T00:00:00Z",
            "active_index": 0, "writeups": [COMPLETE], **overrides}


# --- save / load round trip --------------------------------------------------------

def test_save_load_round_trip(client):
    r = saved(client, [COMPLETE, INCOMPLETE], active_index=1)
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers["content-disposition"] == 'attachment; filename="dfir-cup-2026.zapis.json"'
    file = r.json()
    assert file["tool"] == "zapis" and file["draft_version"] == "1.0"
    assert file["saved_at"].endswith("Z") and "T" in file["saved_at"]
    loaded = client.post(LOAD, content=r.content, headers={"Content-Type": "application/json"})
    assert loaded.status_code == 200
    body = loaded.json()
    assert body["active_index"] == 1
    assert body["writeups"][0] == COMPLETE
    assert body["writeups"][1] == {**normalise_entry({}), **INCOMPLETE}


def test_incomplete_entries_accepted(client):
    file = saved(client, [INCOMPLETE, {}]).json()
    assert file["writeups"][0]["difficulty"] == 0 and file["writeups"][0]["flag"] == ""
    assert file["writeups"][1] == normalise_entry({})
    assert client.post(LOAD, json=file).status_code == 200


@pytest.mark.parametrize("writeups, expected", [
    ([{"ctf_name": "My CTF"}, {"ctf_name": " My CTF "}, {"ctf_name": ""}], "my-ctf.zapis.json"),
    ([{"ctf_name": "A"}, {"ctf_name": "B"}], "draft.zapis.json"),
    ([{}], "draft.zapis.json"),
    ([{"ctf_name": "!!!"}], "draft.zapis.json"),
])
def test_save_filename_slug(client, writeups, expected):
    r = saved(client, writeups)
    assert r.headers["content-disposition"] == f'attachment; filename="{expected}"'


def test_save_accepts_tool_zapis_any_case(client):
    assert client.post(SAVE, json={"tool": "Zapis", "writeups": []}).status_code == 200


# --- 422s ----------------------------------------------------------------------------

@pytest.mark.parametrize("url", [SAVE, LOAD])
@pytest.mark.parametrize("body", [
    {"writeups": "nope"},
    {"writeups": {"0": {}}},
    {"writeups": [{}, "entry"]},
    {"writeups": [None]},
    {"active_index": 0},
])
def test_bad_writeups_422(client, url, body):
    r = client.post(url, json={"tool": "zapis", **body})
    assert r.status_code == 422
    assert "writeups" in r.json()["detail"]


@pytest.mark.parametrize("url", [SAVE, LOAD])
def test_malformed_json_and_non_object_422(client, url):
    bad = client.post(url, content=b'{"tool": "zapis", "writeups": [', headers={"Content-Type": "application/json"})
    assert bad.status_code == 422
    assert client.post(url, json=[COMPLETE]).status_code == 422


@pytest.mark.parametrize("tool", ["sarissa", "", None, 1])
def test_wrong_tool_422(client, tool):
    load = client.post(LOAD, json=a_draft(tool=tool))
    assert load.status_code == 422 and "tool" in load.json()["detail"]
    save = client.post(SAVE, json={"tool": tool, "writeups": []})
    assert save.status_code == 422


def test_load_missing_tool_422(client):
    data = a_draft()
    del data["tool"]
    assert client.post(LOAD, json=data).status_code == 422


# --- lenient load ------------------------------------------------------------------------

def test_unknown_draft_version_warns_but_loads(client, caplog):
    with caplog.at_level(logging.WARNING, logger="zapis.draft"):
        r = client.post(LOAD, json=a_draft(draft_version="9.9"))
    assert r.status_code == 200
    assert r.json()["writeups"][0]["challenge_name"] == "Lost USB"
    assert "draft_version" in caplog.text


def test_known_draft_version_no_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="zapis.draft"):
        parse_draft(a_draft())
    assert caplog.text == ""


@pytest.mark.parametrize("index", [5, 1, -1, True, "0", None, 0.0])
def test_out_of_range_active_index_clamps_to_zero(client, index):
    r = client.post(LOAD, json=a_draft(active_index=index))
    assert r.status_code == 200 and r.json()["active_index"] == 0


def test_valid_active_index_kept():
    entries, index = parse_draft(a_draft(writeups=[COMPLETE, INCOMPLETE], active_index=1))
    assert index == 1 and len(entries) == 2


def test_empty_writeups_gives_one_blank_entry(client):
    r = client.post(LOAD, json=a_draft(writeups=[]))
    assert r.status_code == 200
    assert r.json() == {"writeups": [normalise_entry({})], "active_index": 0}
    assert build_draft([], 3)["writeups"] == [normalise_entry({})]


# --- normalise_entry (INV-P2-5) ----------------------------------------------------------------

def test_normalise_entry_blank_defaults_and_all_fields():
    blank = normalise_entry("not a dict")
    assert tuple(blank) == FIELD_NAMES
    assert blank == {"challenge_name": "", "ctf_name": "", "category": "", "difficulty": 0,
                     "tools_used": [], "approach": "", "flag": "", "notes": "", "author": "",
                     "date": "", "time_spent_minutes": 0}


def test_normalise_entry_wrong_types():
    entry = normalise_entry({"challenge_name": 5, "category": "web", "difficulty": True,
                             "tools_used": ["a", 1, None, "b"], "flag": ["x"],
                             "time_spent_minutes": -3, "unknown": "dropped"})
    assert entry["challenge_name"] == "" and entry["flag"] == ""
    assert entry["category"] == "Web"
    assert entry["difficulty"] == 0
    assert entry["tools_used"] == ["a", "b"]
    assert entry["time_spent_minutes"] == 0
    assert "unknown" not in entry
    assert normalise_entry({"difficulty": 4})["difficulty"] == 0


def test_normalise_entry_single_definition():
    # Import and draft-load share the one lenient-entry definition.
    assert import_sarissa.normalise_entry is draft.normalise_entry


def test_draft_never_builds_a_schema(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("draft-load must not validate for export")
    monkeypatch.setattr("zapis.core.schema.build_schema", boom)
    entries, _ = parse_draft(a_draft(writeups=[INCOMPLETE]))
    assert entries[0]["difficulty"] == 0


def test_parse_draft_errors_are_draft_errors():
    with pytest.raises(DraftError):
        parse_draft("text")
    with pytest.raises(DraftError):
        parse_draft({"tool": "zapis"})
    assert issubclass(DraftError, ValueError)


def test_saved_file_is_utf8_json(client):
    r = saved(client, [{**COMPLETE, "challenge_name": "Запис"}])
    assert "Запис" in r.content.decode("utf-8")
    assert json.loads(r.content)["writeups"][0]["challenge_name"] == "Запис"
