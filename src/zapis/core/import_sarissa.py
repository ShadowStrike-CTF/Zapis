# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Sarissa export JSON (schema v1.0) → pre-filled writeup dicts. File-based only — never calls Sarissa."""
from __future__ import annotations
from typing import Any

SCHEMA_VERSION = "1.0"
TOOL = "sarissa"


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
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SarissaImportError(
            f"schema_version must be {SCHEMA_VERSION!r}, got {data.get('schema_version')!r}"
        )
    if data.get("tool") != TOOL:
        raise SarissaImportError(f"tool must be {TOOL!r}, got {data.get('tool')!r}")
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
