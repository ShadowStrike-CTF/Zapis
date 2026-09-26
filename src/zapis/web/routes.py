# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""FastAPI route handlers — call core exporters, never export directly (INV-4)."""
from __future__ import annotations
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, Response

from zapis.core.export import export, filename_for, media_type
from zapis.core.schema import CATEGORIES, WriteupSchema

router = APIRouter()


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


def _build_schema(body: dict[str, Any]) -> WriteupSchema:
    fields = dict(body)
    if not fields.get("date"):
        fields.pop("date", None)
    tools = fields.get("tools_used")
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        raise HTTPException(422, "tools_used must be a list of strings")
    try:
        return WriteupSchema(**fields)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/export/{fmt}")
def export_writeup(
    fmt: Literal["md", "html", "pdf"], body: dict[str, Any] = Body(...)
) -> Response:
    schema = _build_schema(body)
    return Response(
        export(schema, fmt),
        media_type=media_type(fmt),
        headers={"Content-Disposition": f'attachment; filename="{filename_for(schema, fmt)}"'},
    )
