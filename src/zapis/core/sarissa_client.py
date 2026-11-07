# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Live Sarissa manifest client (Ph6-Live).

The one authorized outbound call (INV-P6-2-EX1): GET http://SARISSA_HOST:SARISSA_PORT/api/manifest,
loopback only, timeout ≤ 2 s. Proxy env vars are ignored and redirects refused, so the
request can never leave the machine. Stdlib only.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("zapis.sarissa_client")

SARISSA_HOST = "127.0.0.1"
SARISSA_PORT = 7331  # single source of truth for Sarissa's port in Zapis
MANIFEST_PATH = "/api/manifest"
TIMEOUT = 2.0
MAX_BYTES = 1_000_000
STATUSES = ("in_progress", "solved")


class SarissaUnavailableError(Exception):
    """Sarissa could not be reached, or did not return a usable manifest."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a 3xx then surfaces as HTTPError — never followed off loopback


def _opener() -> urllib.request.OpenerDirector:
    # ProxyHandler({}) — ignore HTTP(S)_PROXY so a loopback call is never sent to a proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def fetch_sarissa_manifest(
    host: str = SARISSA_HOST, port: int = SARISSA_PORT, timeout: float = TIMEOUT
) -> dict:
    """GET Sarissa's manifest and return it as a dict, or raise SarissaUnavailableError."""
    if host != SARISSA_HOST:
        raise ValueError(f"Sarissa host must be {SARISSA_HOST!r}, got {host!r}")
    if not 0 < timeout <= TIMEOUT:
        raise ValueError(f"timeout must be in (0, {TIMEOUT}], got {timeout!r}")

    url = f"http://{host}:{port}{MANIFEST_PATH}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with _opener().open(request, timeout=timeout) as resp:
            if resp.status != 200:
                raise SarissaUnavailableError(f"Sarissa returned HTTP {resp.status}")
            raw = resp.read(MAX_BYTES + 1)
    except SarissaUnavailableError:
        raise
    except urllib.error.HTTPError as exc:
        raise SarissaUnavailableError(f"Sarissa returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SarissaUnavailableError(f"Sarissa not reachable at {url}: {exc.reason}") from exc
    except (OSError, ValueError) as exc:  # timeouts, resets, malformed HTTP
        raise SarissaUnavailableError(f"Sarissa not reachable at {url}: {exc}") from exc

    if len(raw) > MAX_BYTES:
        raise SarissaUnavailableError(f"Sarissa manifest larger than {MAX_BYTES} bytes")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SarissaUnavailableError(f"Sarissa manifest is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SarissaUnavailableError("Sarissa manifest must be a JSON object")
    return data


def parse_manifest(data: Any) -> list[dict[str, str]]:
    """Manifest dict → [{"id", "name", "status"}], or raise SarissaUnavailableError on bad shape."""
    if not isinstance(data, dict):
        raise SarissaUnavailableError("Sarissa manifest must be a JSON object")
    challenges = data.get("challenges")
    if not isinstance(challenges, list):
        raise SarissaUnavailableError("Sarissa manifest: challenges must be a list")
    out = []
    for i, ch in enumerate(challenges):
        if not isinstance(ch, dict):
            raise SarissaUnavailableError(f"Sarissa manifest: challenges[{i}] must be an object")
        for key in ("id", "name", "status"):
            if not isinstance(ch.get(key), str):
                raise SarissaUnavailableError(
                    f"Sarissa manifest: challenges[{i}].{key} must be a string"
                )
        if ch["status"] not in STATUSES:
            log.warning("Unknown Sarissa challenge status %r (known: %s) — kept as-is",
                        ch["status"], ", ".join(STATUSES))
        out.append({"id": ch["id"], "name": ch["name"], "status": ch["status"]})
    return out
