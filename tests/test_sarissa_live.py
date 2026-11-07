# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Tests for Ph6-Live — GET /api/import/sarissa/live and core/sarissa_client.py.

Sarissa is never needed: route tests monkeypatch the client, client tests run against a
stub stdlib http.server on 127.0.0.1 with an ephemeral port.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zapis.core import sarissa_client
from zapis.core.sarissa_client import (
    SarissaUnavailableError,
    fetch_sarissa_manifest,
    parse_manifest,
)
from zapis.main import create_app

URL = "/api/import/sarissa/live"
ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "sarissa_1_3_export.json"

MANIFEST = {
    "challenges": [
        {"id": "a1b2c3d4e5f6", "name": "Lost USB", "status": "solved"},
        {"id": "0f9e8d7c6b5a", "name": "Phish Tank", "status": "in_progress"},
    ],
    "total": 2,
    "manifest_hash": "sha256:" + "ab" * 32,
}


@pytest.fixture
def client():
    return TestClient(create_app())


def patch_fetch(monkeypatch, result):
    def fake(*args, **kwargs):
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr("zapis.web.routes.fetch_sarissa_manifest", fake)


def assert_unreachable(resp):
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "sarissa_unreachable"
    assert isinstance(body["detail"], str) and body["detail"]


# ---------------------------------------------------------------- route ----

def test_live_success_returns_challenge_list(client, monkeypatch):
    patch_fetch(monkeypatch, MANIFEST)
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.json() == MANIFEST["challenges"]


def test_live_drops_extra_keys(client, monkeypatch):
    manifest = {"challenges": [{"id": "x", "name": "N", "status": "solved", "flag_hash": "h"}]}
    patch_fetch(monkeypatch, manifest)
    assert client.get(URL).json() == [{"id": "x", "name": "N", "status": "solved"}]


def test_live_empty_manifest(client, monkeypatch):
    patch_fetch(monkeypatch, {"challenges": [], "total": 0, "manifest_hash": "sha256:00"})
    resp = client.get(URL)
    assert resp.status_code == 200 and resp.json() == []


def test_live_unreachable_is_503(client, monkeypatch):
    patch_fetch(monkeypatch, SarissaUnavailableError("Sarissa not reachable: connection refused"))
    resp = client.get(URL)
    assert_unreachable(resp)
    assert "connection refused" in resp.json()["detail"]


def test_live_non_200_is_503(client, monkeypatch, stub):
    stub.respond(500, b'{"detail": "boom"}')
    _point_route_at(monkeypatch, stub)
    assert_unreachable(client.get(URL))


def test_live_malformed_json_is_503(client, monkeypatch, stub):
    stub.respond(200, b"{not json")
    _point_route_at(monkeypatch, stub)
    assert_unreachable(client.get(URL))


@pytest.mark.parametrize("manifest", [
    {"challenges": "nope"},
    {"total": 0},
    {"challenges": ["not-an-object"]},
    {"challenges": [{"id": 1, "name": "N", "status": "solved"}]},
    {"challenges": [{"id": "x", "status": "solved"}]},
])
def test_live_bad_shape_is_503(client, monkeypatch, manifest):
    patch_fetch(monkeypatch, manifest)
    assert_unreachable(client.get(URL))


def test_live_with_sarissa_down_is_503(client, monkeypatch):
    # Real client, real closed port — no mock of the failure itself.
    port = _closed_port()
    monkeypatch.setattr("zapis.web.routes.fetch_sarissa_manifest",
                        lambda: fetch_sarissa_manifest(port=port))
    assert_unreachable(client.get(URL))


def test_file_import_unchanged(client):
    data = json.loads(FIXTURE.read_text())
    resp = client.post("/api/import/sarissa", json=data)
    assert resp.status_code == 200
    names = [e["challenge_name"] for e in resp.json()]
    assert names == ["Lost USB", "Phish Tank"]


# ---------------------------------------------------------- stub server ----

class _Stub:
    def __init__(self):
        self.status, self.body, self.headers, self.delay = 200, b"{}", {}, 0.0
        self.hits = 0
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                stub.hits += 1
                stub.path = self.path
                if stub.delay:
                    time.sleep(stub.delay)
                self.send_response(stub.status)
                for k, v in stub.headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(stub.body)))
                self.end_headers()
                self.wfile.write(stub.body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def respond(self, status, body, headers=None, delay=0.0):
        self.status, self.body, self.headers, self.delay = status, body, headers or {}, delay


@pytest.fixture
def stub():
    s = _Stub()
    yield s
    s.server.shutdown()
    s.server.server_close()


def _point_route_at(monkeypatch, stub):
    # Route → real client → stub server: exercises the whole path, Sarissa replaced by the stub.
    monkeypatch.setattr("zapis.web.routes.fetch_sarissa_manifest",
                        lambda: fetch_sarissa_manifest(port=stub.port))


def _closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --------------------------------------------------------------- client ----

def test_client_success(stub):
    stub.respond(200, json.dumps(MANIFEST).encode(), {"Content-Type": "application/json"})
    assert fetch_sarissa_manifest(port=stub.port) == MANIFEST
    assert stub.path == "/api/manifest"


def test_client_non_200(stub):
    stub.respond(404, b"{}")
    with pytest.raises(SarissaUnavailableError, match="HTTP 404"):
        fetch_sarissa_manifest(port=stub.port)


def test_client_malformed_json(stub):
    stub.respond(200, b"<html>")
    with pytest.raises(SarissaUnavailableError, match="not valid JSON"):
        fetch_sarissa_manifest(port=stub.port)


def test_client_non_object_json(stub):
    stub.respond(200, b"[1, 2]")
    with pytest.raises(SarissaUnavailableError, match="JSON object"):
        fetch_sarissa_manifest(port=stub.port)


def test_client_oversized_body(stub, monkeypatch):
    monkeypatch.setattr(sarissa_client, "MAX_BYTES", 10)
    stub.respond(200, json.dumps(MANIFEST).encode())
    with pytest.raises(SarissaUnavailableError, match="larger than"):
        fetch_sarissa_manifest(port=stub.port)


def test_client_redirect_not_followed(stub):
    stub.respond(302, b"", {"Location": "http://example.com/api/manifest"})
    with pytest.raises(SarissaUnavailableError, match="HTTP 302"):
        fetch_sarissa_manifest(port=stub.port)
    assert stub.hits == 1


def test_client_connection_refused():
    with pytest.raises(SarissaUnavailableError, match="not reachable"):
        fetch_sarissa_manifest(port=_closed_port())


def test_client_timeout(stub):
    stub.respond(200, b"{}", delay=1.0)
    start = time.monotonic()
    with pytest.raises(SarissaUnavailableError):
        fetch_sarissa_manifest(port=stub.port, timeout=0.2)
    assert time.monotonic() - start < 1.0


def test_client_ignores_proxy_env(stub, monkeypatch):
    dead = f"http://127.0.0.1:{_closed_port()}"
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY"):
        monkeypatch.setenv(var, dead)
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")
    stub.respond(200, json.dumps(MANIFEST).encode())
    assert fetch_sarissa_manifest(port=stub.port) == MANIFEST


@pytest.mark.parametrize("host", ["localhost", "0.0.0.0", "10.0.0.1", "sarissa.example.com"])
def test_client_rejects_non_loopback_host(host):
    with pytest.raises(ValueError, match="127.0.0.1"):
        fetch_sarissa_manifest(host=host)


@pytest.mark.parametrize("timeout", [0, -1, 2.01, 10])
def test_client_rejects_timeout_over_2s(timeout):
    with pytest.raises(ValueError, match="timeout"):
        fetch_sarissa_manifest(timeout=timeout)


def test_client_defaults():
    assert sarissa_client.SARISSA_HOST == "127.0.0.1"
    assert sarissa_client.SARISSA_PORT == 7331
    assert 0 < sarissa_client.TIMEOUT <= 2


def test_unknown_status_warns_and_is_kept(caplog):
    with caplog.at_level("WARNING", logger="zapis.sarissa_client"):
        out = parse_manifest({"challenges": [{"id": "x", "name": "N", "status": "abandoned"}]})
    assert out == [{"id": "x", "name": "N", "status": "abandoned"}]
    assert "abandoned" in caplog.text


def test_port_7331_defined_once_in_src():
    hits = [
        (p.relative_to(ROOT), line)
        for p in (ROOT / "src").rglob("*")
        if p.is_file() and p.suffix in {".py", ".html", ".md", ".js", ".json"}
        for line in p.read_text(encoding="utf-8").splitlines()
        if "7331" in line
    ]
    assert len(hits) == 1, hits
    assert hits[0][0].name == "sarissa_client.py"
