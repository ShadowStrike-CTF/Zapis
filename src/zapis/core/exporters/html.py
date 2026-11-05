# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""HTML exporter — schema → styled self-contained HTML string."""
from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from zapis.core.schema import WriteupSchema
from zapis.core.text import has_code, split_fences

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


def html_env() -> Environment:
    """Jinja2 environment for HTML templates. Autoescape stays on (INV-P2-3)."""
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)
    env.globals["split_fences"] = split_fences
    return env


def export_html(schema: WriteupSchema) -> str:
    tmpl = html_env().get_template("writeup.html")
    # Code-block CSS is only emitted when there is code, so plain writeups stay byte-identical (INV-P2-2).
    return tmpl.render(w=schema, has_code=has_code(schema.approach, schema.notes))
