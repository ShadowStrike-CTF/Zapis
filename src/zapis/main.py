# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Zapis launcher — FastAPI app factory, uvicorn thread, browser open."""
from __future__ import annotations
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI

PORT = 7334
HOST = "127.0.0.1"


def static_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "zapis" / "static"
    return Path(__file__).parent / "static"


def create_app() -> FastAPI:
    from zapis.web.routes import router

    app = FastAPI(title="Zapis", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.port = PORT
    app.include_router(router)
    return app


def main() -> None:
    config = uvicorn.Config(create_app(), host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    webbrowser.open(f"http://{HOST}:{PORT}/")
    try:
        while thread.is_alive():
            thread.join(0.5)
    except KeyboardInterrupt:
        server.should_exit = True
        thread.join()
