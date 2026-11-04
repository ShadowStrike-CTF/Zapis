# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Sarissa export JSON (schema v1.0 / v1.3) → pre-filled writeup dicts. File-based only — never calls Sarissa."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("zapis.import_sarissa")

# Sarissa export schema versions Zapis knows. Any other version is imported with a warning, not rejected.
SCHEMA_VERSIONS = ("1.0", "1.3")
TOOL = "sarissa"  # compared case-insensitively — Sarissa emits "Sarissa"


class SarissaImportError(ValueError):
    """The supplied data is not a usable Sarissa export."""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _entry(challenge_name: str, ctf_name: str, approach: str) -> dict[str, Any]:
    # category/difficulty/tools_used/flag are left blank — the user fills them before export.
    return {
        "challenge_name": challenge_name,
        "ctf_name": ctf_name,
        "category": "",
        "difficulty": 0,
        "tools_used": [],
        "approach": approach,
        "flag": "",
    }


def parse_sarissa_export(data: dict) -> list[dict]:
    if not isinstance(data, dict):
        raise SarissaImportError("Sarissa export must be a JSON object")
    if data.get("schema_version") not in SCHEMA_VERSIONS:
        log.warning(
            "Unknown Sarissa schema_version %r (known: %s) — importing anyway",
            data.get("schema_version"), ", ".join(SCHEMA_VERSIONS),
        )
    tool = data.get("tool")
    if not isinstance(tool, str) or tool.lower() != TOOL:
        raise SarissaImportError(f"tool must be {TOOL!r} (any case), got {tool!r}")
    challenges = data.get("challenges")
    if not isinstance(challenges, list):
        raise SarissaImportError("challenges must be a list")

    session = data.get("session")
    ctf_name = _text(session.get("name")) if isinstance(session, dict) else ""

    if not challenges:
        return [_entry("", ctf_name, "")]
    entries = []
    for i, challenge in enumerate(challenges):
        if not isinstance(challenge, dict):
            raise SarissaImportError(f"challenges[{i}] must be an object")
        entries.append(_entry(_text(challenge.get("name")), ctf_name, _text(challenge.get("notes"))))
    return entries
