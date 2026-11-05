# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Code-review assertions — UI and template rules that a reviewer would otherwise check by eye."""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PKG = ROOT / "src" / "zapis"
INDEX = (PKG / "static" / "index.html").read_text(encoding="utf-8")
TEMPLATES = sorted((PKG / "templates").glob("*"))
COLOURED = [PKG / "static" / "index.html"] + [p for p in TEMPLATES if p.suffix == ".html"]


def test_no_html_injection_sinks_in_ui():
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert sink not in INDEX, sink


def test_no_browser_dialogs():
    assert not re.search(r"\b(alert|confirm|prompt)\s*\(", INDEX)


@pytest.mark.parametrize("path", COLOURED, ids=lambda p: p.name)
def test_no_green(path):
    text = path.read_text(encoding="utf-8").lower()
    assert not re.search(r"\b(green|lime|olive|teal|chartreuse)\b", text)
    for hexcol in re.findall(r"#([0-9a-f]{6}|[0-9a-f]{3})\b", text):
        full = "".join(c * 2 for c in hexcol) if len(hexcol) == 3 else hexcol
        r, g, b = (int(full[i:i + 2], 16) for i in (0, 2, 4))
        assert not (g > r + 16 and g > b + 16), f"green-ish colour #{hexcol} in {path.name}"


def test_ui_has_phase2_controls():
    for control in ('id="new_btn"', 'id="remove_btn"', 'id="remove_confirm"', 'id="draft_save_btn"',
                    'id="draft_open_btn"', 'id="bundle_btn"', 'id="bundle_fmt"', 'id="import_btn"'):
        assert control in INDEX, control
    assert re.search(r'<input id="time_spent_minutes"[^>]*type="number"[^>]*min="0"[^>]*step="1"', INDEX)
    for path in ("/api/draft/save", "/api/draft/load", "/api/export/bundle/", "/api/import/sarissa"):
        assert path in INDEX


def test_picker_switch_writes_back_before_loading():
    # P2-2 bug fix: the picker must commit the form to the working set before switching.
    switch = re.search(r"function switchTo\(i\) \{(.*?)\n  \}", INDEX, re.S).group(1)
    assert switch.index("commit();") < switch.index("fillForm(")
    assert "picker.addEventListener(\"change\", function () { switchTo(" in INDEX


def test_no_server_side_or_browser_storage():
    # INV-P2-1: drafts are user-owned files; nothing persisted by Zapis.
    for api in ("localStorage", "sessionStorage", "indexedDB"):
        assert api not in INDEX


def test_templates_never_mark_user_text_safe():
    # INV-P2-3: autoescape on, no |safe, no Markup().
    for path in TEMPLATES:
        code = re.sub(r"\{#.*?#\}", "", path.read_text(encoding="utf-8"), flags=re.S)  # drop comments
        assert "|safe" not in code.replace(" ", ""), path.name
    for path in (PKG / "core").rglob("*.py"):
        assert "Markup" not in path.read_text(encoding="utf-8"), path.name
    # Only the Markdown environment (plain text output) turns autoescape off.
    html_py = (PKG / "core" / "exporters" / "html.py").read_text(encoding="utf-8")
    assert "autoescape=True" in html_py


def test_no_new_runtime_dependencies():
    # INV-P2-6
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    assert sorted(re.split(r"[<>=]", d)[0] for d in deps) == ["fastapi", "jinja2", "uvicorn", "weasyprint"]
