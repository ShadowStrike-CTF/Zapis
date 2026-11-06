# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Sarissa export JSON (schema v1.0 / v1.3) → pre-filled writeup dicts. File-based only — never calls Sarissa."""
from __future__ import annotations

import datetime
import logging
import re
from typing import Any

from zapis.core.draft import normalise_entry

log = logging.getLogger("zapis.import_sarissa")

# Sarissa export schema versions Zapis knows. Any other version is imported with a warning, not rejected.
SCHEMA_VERSIONS = ("1.0", "1.3")
TOOL = "sarissa"  # compared case-insensitively — Sarissa emits "Sarissa"

# The keys an imported entry carries. notes/author are not part of an import — the UI keeps its own.
# date comes from solved_at (Ph3); "" when unsolved, and the UI then keeps its current date.
IMPORT_KEYS = ("challenge_name", "ctf_name", "category", "difficulty", "tools_used",
               "approach", "flag", "time_spent_minutes", "date")

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class SarissaImportError(ValueError):
    """The supplied data is not a usable Sarissa export."""


def _minutes(seconds: Any) -> int:
    # Sarissa 1.3 `challenge_time_seconds`: non-negative whole seconds → whole minutes, else 0.
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        return 0
    return round(seconds / 60)


def _solved_date(solved_at: Any) -> str:
    # Sarissa `solved_at` (ISO 8601, or null while unsolved) → its YYYY-MM-DD date part, else "".
    # The regex comes first: fromisoformat alone would also accept week dates like "2026-W43-6".
    if not isinstance(solved_at, str) or not _ISO_DATE.match(solved_at):
        return ""
    try:
        return datetime.date.fromisoformat(solved_at[:10]).isoformat()
    except ValueError:
        return ""


def _entry(challenge: dict[str, Any], ctf_name: str) -> dict[str, Any]:
    # difficulty/tools_used/flag are left blank — the user fills them before export.
    entry = normalise_entry({
        "challenge_name": challenge.get("name"),
        "ctf_name": ctf_name,
        "category": challenge.get("category"),  # case-insensitive → canonical, else ""
        "approach": challenge.get("notes"),
        "time_spent_minutes": _minutes(challenge.get("challenge_time_seconds")),
        "date": _solved_date(challenge.get("solved_at")),
    })
    return {key: entry[key] for key in IMPORT_KEYS}


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
    ctf_name = session.get("name") if isinstance(session, dict) else ""

    if not challenges:
        return [_entry({}, ctf_name)]
    entries = []
    for i, challenge in enumerate(challenges):
        if not isinstance(challenge, dict):
            raise SarissaImportError(f"challenges[{i}] must be an object")
        entries.append(_entry(challenge, ctf_name))
    return entries
