# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""PDF exporter — schema → PDF bytes via weasyprint.
Requires native Pango/Cairo libraries (see CLAUDE.md Build Constraints).
pip install weasyprint alone is not sufficient."""
from __future__ import annotations
import weasyprint
from zapis.core.exporters.html import export_html
from zapis.core.schema import WriteupSchema

def export_pdf(schema: WriteupSchema) -> bytes:
    html_str = export_html(schema)
    return weasyprint.HTML(string=html_str).write_pdf()
