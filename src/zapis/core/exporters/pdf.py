# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""PDF exporter — schema → PDF bytes via weasyprint.
Requires native Pango/Cairo libraries (see CLAUDE.md Build Constraints).
pip install weasyprint alone is not sufficient.
Only ever imported lazily (export.py / bundle.py) so md/html never load weasyprint."""
from __future__ import annotations
import weasyprint
from zapis.core.exporters.html import export_html
from zapis.core.schema import WriteupSchema


def html_to_pdf(html_str: str) -> bytes:
    """One rendered HTML document → one PDF (one write_pdf call)."""
    return weasyprint.HTML(string=html_str).write_pdf()


def export_pdf(schema: WriteupSchema) -> bytes:
    return html_to_pdf(export_html(schema))
