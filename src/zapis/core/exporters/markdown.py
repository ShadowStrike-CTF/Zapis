# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Markdown exporter — schema → .md string via Jinja2 template."""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from zapis.core.schema import WriteupSchema

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

def export_markdown(schema: WriteupSchema) -> str:
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=False)
    tmpl = env.get_template("writeup.md")
    return tmpl.render(**schema.__dict__)
