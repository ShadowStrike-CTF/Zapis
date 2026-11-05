# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""INV-P2-2 golden test — single-writeup MD/HTML output stays byte-identical to v1.3.2.

The files in tests/golden/ were rendered by Zapis v1.3.2 (tag v1.3.2, before any Phase 2
change). They must pass before and after the template partial extraction.
Exception (decided by R): MD with an empty tools list now renders "_None recorded._" —
not covered here because sample_schema has tools.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from zapis.core.exporters.html import export_html
from zapis.core.exporters.markdown import export_markdown
from zapis.core.schema import WriteupSchema

GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def golden_schema():
    # The test_core sample_schema with the date pinned.
    return WriteupSchema(
        challenge_name="Test Challenge",
        ctf_name="TestCTF 2026",
        category="Forensics",
        difficulty=2,
        tools_used=["Autopsy", "FTK Imager"],
        approach="Mounted the image and found the flag in EXIF metadata.",
        flag="FLAG{test_flag_123}",
        notes="Good challenge.",
        date="2026-09-26",
    )


def _golden(name: str) -> str:
    return (GOLDEN / name).read_bytes().decode("utf-8")


def test_golden_markdown_byte_identical(golden_schema):
    assert export_markdown(golden_schema) == _golden("sample.md")


def test_golden_html_byte_identical(golden_schema):
    assert export_html(golden_schema) == _golden("sample.html")


def test_golden_html_no_notes_no_tools_byte_identical(golden_schema):
    golden_schema.notes = ""
    golden_schema.tools_used = []
    assert export_html(golden_schema) == _golden("no_notes_no_tools.html")
