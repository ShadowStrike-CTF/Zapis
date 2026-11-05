# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Markdown exporter — schema → .md string via Jinja2 template."""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from zapis.core.schema import WriteupSchema
from zapis.core.text import md_inline_code, md_line

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


def markdown_env() -> Environment:
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=False)
    env.filters["md_line"] = md_line
    env.filters["md_inline_code"] = md_inline_code
    return env


def export_markdown(schema: WriteupSchema) -> str:
    return markdown_env().get_template("writeup.md").render(w=schema)
