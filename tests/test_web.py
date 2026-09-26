# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Tests for the Zapis web layer — FastAPI routes via TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from zapis.core.schema import CATEGORIES
from zapis.main import PORT, create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def payload():
    return {
        "challenge_name": "Test Challenge",
        "ctf_name": "TestCTF 2026",
        "category": "Forensics",
        "difficulty": 2,
        "tools_used": ["Autopsy", "FTK Imager"],
        "approach": "Mounted the image & found <the> flag in EXIF metadata.",
        "flag": "FLAG{test_flag_123}",
        "notes": "Good challenge.",
        "author": "ShadowStrike",
        "date": "2026-09-26",
    }


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "port": PORT}


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "#a93226" in r.text


def test_categories(client):
    r = client.get("/api/categories")
    assert r.status_code == 200
    assert r.json() == list(CATEGORIES)


def test_export_md(client, payload):
    r = client.post("/api/export/md", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.headers["content-disposition"] == 'attachment; filename="test-challenge.md"'
    assert "FLAG{test_flag_123}" in r.text
    assert "Test Challenge" in r.text


def test_export_html(client, payload):
    r = client.post("/api/export/html", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers["content-disposition"] == 'attachment; filename="test-challenge.html"'
    assert "FLAG{test_flag_123}" in r.text
    assert "&lt;the&gt;" in r.text
    assert "<the>" not in r.text


def test_export_pdf(client, payload):
    r = client.post("/api/export/pdf", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'attachment; filename="test-challenge.pdf"'
    assert r.content.startswith(b"%PDF")


def test_export_invalid_category(client, payload):
    r = client.post("/api/export/md", json={**payload, "category": "Hardware"})
    assert r.status_code == 422
    assert "category" in r.json()["detail"]


def test_export_invalid_difficulty(client, payload):
    for bad in (0, 4):
        r = client.post("/api/export/md", json={**payload, "difficulty": bad})
        assert r.status_code == 422
        assert "difficulty" in r.json()["detail"]


def test_export_empty_flag_and_missing_field(client, payload):
    assert client.post("/api/export/md", json={**payload, "flag": "  "}).status_code == 422
    partial = {k: v for k, v in payload.items() if k != "approach"}
    assert client.post("/api/export/md", json=partial).status_code == 422


def test_unknown_format_and_no_docs(client, payload):
    assert client.post("/api/export/docx", json=payload).status_code == 422
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
