# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""FastAPI route handlers — call core exporters, never export directly (INV-4).

Handlers only translate: request → core call → response, and core ValueErrors → 422.
No validation or mapping lives here (INV-1).
"""
from __future__ import annotations
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, Response

from zapis.core import build_schema
from zapis.core.bundle import BundleError, bundle_filename, bundle_media_type, export_bundle
from zapis.core.draft import DraftError, draft_filename, draft_from_request, dump_draft, parse_draft
from zapis.core.export import export, filename_for, media_type
from zapis.core.import_sarissa import SarissaImportError, parse_sarissa_export
from zapis.core.schema import CATEGORIES

router = APIRouter()


def _attachment(content: bytes, media: str, filename: str) -> Response:
    return Response(
        content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    from zapis.main import static_dir
    return FileResponse(static_dir() / "index.html", media_type="text/html")


@router.get("/api/health")
def health(request: Request) -> dict:
    return {"status": "ok", "port": request.app.state.port}


@router.get("/api/categories")
def categories() -> list[str]:
    return list(CATEGORIES)


@router.post("/api/export/{fmt}")
def export_writeup(
    fmt: Literal["md", "html", "pdf"], body: dict[str, Any] = Body(...)
) -> Response:
    try:
        schema = build_schema(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _attachment(export(schema, fmt), media_type(fmt), filename_for(schema, fmt))


@router.post("/api/export/bundle/{fmt}")
def export_bundle_route(
    fmt: Literal["md", "html", "pdf", "zip"], body: dict[str, Any] = Body(...)
) -> Response:
    entries = body.get("writeups")
    try:
        content = export_bundle(entries, fmt, body.get("inner", "md"))
    except BundleError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _attachment(content, bundle_media_type(fmt), bundle_filename(entries, fmt))


@router.post("/api/draft/save")
def draft_save(body: dict[str, Any] = Body(...)) -> Response:
    try:
        draft = draft_from_request(body)
    except DraftError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _attachment(dump_draft(draft), "application/json", draft_filename(draft))


@router.post("/api/draft/load")
def draft_load(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        entries, active_index = parse_draft(body)
    except DraftError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"writeups": entries, "active_index": active_index}


@router.post("/api/import/sarissa")
def import_sarissa(body: dict[str, Any] = Body(...)) -> list[dict[str, Any]]:
    try:
        return parse_sarissa_export(body)
    except SarissaImportError as exc:
        raise HTTPException(422, str(exc)) from exc
