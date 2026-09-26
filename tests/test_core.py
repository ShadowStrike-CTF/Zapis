# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Tests for the Zapis core library — schema and MD/HTML/PDF exporters."""
from __future__ import annotations

import dataclasses
import datetime

import pytest

from zapis.core.exporters.html import export_html
from zapis.core.exporters.markdown import export_markdown
from zapis.core.exporters.pdf import export_pdf
from zapis.core.schema import WriteupSchema


@pytest.fixture
def sample_schema():
    return WriteupSchema(
        challenge_name="Test Challenge",
        ctf_name="TestCTF 2026",
        category="Forensics",
        difficulty=2,
        tools_used=["Autopsy", "FTK Imager"],
        approach="Mounted the image and found the flag in EXIF metadata.",
        flag="FLAG{test_flag_123}",
        notes="Good challenge.",
    )


def _fields(schema: WriteupSchema) -> dict:
    return {f.name: getattr(schema, f.name) for f in dataclasses.fields(schema)}


# --- Schema -----------------------------------------------------------------

def test_schema_valid(sample_schema):
    assert sample_schema.challenge_name == "Test Challenge"
    assert sample_schema.category == "Forensics"
    assert sample_schema.difficulty == 2


def test_schema_invalid_category(sample_schema):
    with pytest.raises(ValueError):
        WriteupSchema(**{**_fields(sample_schema), "category": "Hardware"})


def test_schema_invalid_difficulty(sample_schema):
    for bad in (0, 4):
        with pytest.raises(ValueError):
            WriteupSchema(**{**_fields(sample_schema), "difficulty": bad})


def test_schema_empty_flag(sample_schema):
    for bad in ("", "   "):
        with pytest.raises(ValueError):
            WriteupSchema(**{**_fields(sample_schema), "flag": bad})


def test_schema_defaults(sample_schema):
    assert sample_schema.author == "ShadowStrike"
    assert sample_schema.date == datetime.date.today().isoformat()


# --- Markdown ---------------------------------------------------------------

def test_markdown_contains_challenge_name(sample_schema):
    assert "# Test Challenge" in export_markdown(sample_schema)


def test_markdown_contains_flag(sample_schema):
    assert "`FLAG{test_flag_123}`" in export_markdown(sample_schema)


def test_markdown_contains_all_tools(sample_schema):
    md = export_markdown(sample_schema)
    for tool in sample_schema.tools_used:
        assert f"- {tool}" in md


# --- HTML -------------------------------------------------------------------

def test_html_is_string(sample_schema):
    assert isinstance(export_html(sample_schema), str)


def test_html_contains_challenge_name(sample_schema):
    assert "Test Challenge" in export_html(sample_schema)


def test_html_contains_flag(sample_schema):
    assert "FLAG{test_flag_123}" in export_html(sample_schema)


def test_html_autoescaped(sample_schema):
    schema = WriteupSchema(
        **{**_fields(sample_schema), "approach": "<script>alert(1)</script>"}
    )
    html = export_html(schema)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


# --- PDF --------------------------------------------------------------------

def test_pdf_returns_bytes(sample_schema):
    assert isinstance(export_pdf(sample_schema), bytes)


def test_pdf_starts_with_pdf_header(sample_schema):
    assert export_pdf(sample_schema).startswith(b"%PDF")


def test_pdf_nonempty(sample_schema):
    assert len(export_pdf(sample_schema)) > 1000
