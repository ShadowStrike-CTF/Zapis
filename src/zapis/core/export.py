# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Format dispatch shared by the web and CLI layers — schema → (bytes, media type, filename)."""
from __future__ import annotations
import re
from zapis.core.exporters.html import export_html
from zapis.core.exporters.markdown import export_markdown
from zapis.core.schema import WriteupSchema

FORMATS = ("md", "html", "pdf")

_MEDIA_TYPES = {
    "md": "text/markdown; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "pdf": "application/pdf",
}


def _check(fmt: str) -> None:
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}, got {fmt!r}")


def export(schema: WriteupSchema, fmt: str) -> bytes:
    _check(fmt)
    if fmt == "md":
        return export_markdown(schema).encode("utf-8")
    if fmt == "html":
        return export_html(schema).encode("utf-8")
    # Lazy import — weasyprint needs native Pango/Cairo; md/html must not depend on it.
    from zapis.core.exporters.pdf import export_pdf
    return export_pdf(schema)


def media_type(fmt: str) -> str:
    _check(fmt)
    return _MEDIA_TYPES[fmt]


def filename_for(schema: WriteupSchema, fmt: str) -> str:
    _check(fmt)
    slug = re.sub(r"[^a-z0-9]+", "-", schema.challenge_name.lower()).strip("-")
    return f"{slug or 'writeup'}.{fmt}"
