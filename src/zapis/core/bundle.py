# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Bundle export — a working set of writeups → one md / html / pdf document, or a zip.

Every entry is validated through build_schema() before anything is rendered (INV-P2-4): one bad
entry fails the whole bundle and nothing is half-exported. WeasyPrint is imported only for
fmt == "pdf" or a zip with inner == "pdf".
"""
from __future__ import annotations

import io
import zipfile
from typing import Any

from zapis.core import export as single
from zapis.core.draft import common_ctf_name
from zapis.core.exporters.html import html_env
from zapis.core.exporters.markdown import markdown_env
from zapis.core.schema import WriteupSchema, build_schema
from zapis.core.text import slugify

FORMATS = ("md", "html", "pdf", "zip")
INNER_FORMATS = single.FORMATS
DEFAULT_TITLE = "CTF Writeups"
INDEX_NAME = "index.md"


class BundleError(ValueError):
    """One or more entries cannot be exported. `messages` names every failing entry."""

    def __init__(self, messages: list[str]):
        self.messages = list(messages)
        super().__init__("; ".join(self.messages))


def _label(i: int, raw: Any) -> str:
    name = raw.get("challenge_name") if isinstance(raw, dict) else None
    name = name.strip() if isinstance(name, str) and name.strip() else "(unnamed)"
    return f"Writeup {i + 1} ({name})"


def validate_entries(entries: Any) -> list[WriteupSchema]:
    """Every entry through build_schema(); collect every failure before raising."""
    if not isinstance(entries, list):
        raise BundleError(["writeups must be a list"])
    if not entries:
        raise BundleError(["writeups must not be empty"])
    schemas: list[WriteupSchema] = []
    errors: list[str] = []
    for i, raw in enumerate(entries):
        try:
            schemas.append(build_schema(raw))
        except ValueError as exc:
            errors.append(f"{_label(i, raw)}: {exc}")
    if errors:
        raise BundleError(errors)
    return schemas


def _title(schemas: list[WriteupSchema]) -> str:
    return common_ctf_name(s.ctf_name for s in schemas) or DEFAULT_TITLE


def _unique_slugs(schemas: list[WriteupSchema]) -> list[str]:
    seen: set[str] = set()
    slugs = []
    for s in schemas:
        base = slug = slugify(s.challenge_name, "writeup")
        n = 2
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        seen.add(slug)
        slugs.append(slug)
    return slugs


def _render_md(schemas: list[WriteupSchema], **extra: Any) -> str:
    return markdown_env().get_template("bundle.md").render(
        writeups=schemas, title=_title(schemas), **extra)


def _render_html(schemas: list[WriteupSchema]) -> str:
    return html_env().get_template("bundle.html").render(
        writeups=schemas, title=_title(schemas), has_code=True)


def export_bundle(entries: Any, fmt: str, inner: str = "md") -> bytes:
    if fmt not in FORMATS:
        raise BundleError([f"format must be one of {FORMATS}, got {fmt!r}"])
    if fmt == "zip" and inner not in INNER_FORMATS:
        raise BundleError([f"inner must be one of {INNER_FORMATS}, got {inner!r}"])
    schemas = validate_entries(entries)  # before anything is rendered

    if fmt == "md":
        return _render_md(schemas).encode("utf-8")
    if fmt == "html":
        return _render_html(schemas).encode("utf-8")
    if fmt == "pdf":
        from zapis.core.exporters.pdf import html_to_pdf  # lazy — native libs
        return html_to_pdf(_render_html(schemas))  # one write_pdf() for the whole bundle

    files = [f"{slug}.{inner}" for slug in _unique_slugs(schemas)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for schema, name in zip(schemas, files):
            zf.writestr(name, single.export(schema, inner))  # pdf imported lazily there
        zf.writestr(INDEX_NAME, _render_md(schemas, files=files, contents_only=True))
    return buf.getvalue()


def bundle_filename(entries: Any, fmt: str) -> str:
    names = (e["ctf_name"] for e in entries if isinstance(e, dict) and isinstance(e.get("ctf_name"), str)) \
        if isinstance(entries, list) else ()
    slug = slugify(common_ctf_name(names), "")
    return f"{slug}-writeups.{fmt}" if slug else f"writeups.{fmt}"


def bundle_media_type(fmt: str) -> str:
    return "application/zip" if fmt == "zip" else single.media_type(fmt)
