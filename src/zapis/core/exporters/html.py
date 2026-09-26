# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""HTML exporter — schema → styled self-contained HTML string."""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from zapis.core.schema import WriteupSchema

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

def export_html(schema: WriteupSchema) -> str:
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)
    tmpl = env.get_template("writeup.html")
    return tmpl.render(**schema.__dict__)
