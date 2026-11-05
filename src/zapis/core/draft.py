# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Draft files — the user-owned JSON that holds a working set of (possibly incomplete) writeups.

Zapis keeps no writeup content of its own (INV-P2-1): the browser holds the working set, and a
draft is a file the user saves and re-opens. `normalise_entry` is the single lenient-entry
definition (INV-P2-5), shared with the Sarissa import. Nothing here builds a WriteupSchema.
"""
from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Iterable

from zapis.core.schema import CATEGORIES, FIELD_NAMES
from zapis.core.text import slugify

log = logging.getLogger("zapis.draft")

TOOL = "zapis"
DRAFT_VERSION = "1.0"
DRAFT_VERSIONS = (DRAFT_VERSION,)
DRAFT_SUFFIX = ".zapis.json"

_TEXT_FIELDS = ("challenge_name", "ctf_name", "approach", "flag", "notes", "author", "date")
_CATEGORY_BY_LOWER = {c.lower(): c for c in CATEGORIES}


class DraftError(ValueError):
    """The supplied data is not a usable Zapis draft."""


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def match_category(value: Any) -> str:
    """Case-insensitive match against CATEGORIES → canonical casing, else ""."""
    return _CATEGORY_BY_LOWER.get(value.lower(), "") if isinstance(value, str) else ""


def normalise_entry(raw: Any) -> dict[str, Any]:
    """Any value → a dict with every WriteupSchema field. Wrong type or missing → blank default.

    Blank defaults are deliberately not export-valid (category "", difficulty 0, flag ""):
    the user fills them in before export.
    """
    raw = raw if isinstance(raw, dict) else {}
    entry: dict[str, Any] = {name: (raw.get(name) if isinstance(raw.get(name), str) else "")
                             for name in _TEXT_FIELDS}
    entry["category"] = match_category(raw.get("category"))
    difficulty = raw.get("difficulty")
    entry["difficulty"] = difficulty if _whole(difficulty) and 1 <= difficulty <= 3 else 0
    tools = raw.get("tools_used")
    entry["tools_used"] = [t for t in tools if isinstance(t, str)] if isinstance(tools, list) else []
    minutes = raw.get("time_spent_minutes")
    entry["time_spent_minutes"] = minutes if _whole(minutes) and minutes >= 0 else 0
    return {name: entry[name] for name in FIELD_NAMES}


def _check_writeups(writeups: Any) -> list[dict]:
    if not isinstance(writeups, list):
        raise DraftError("writeups must be a list")
    for i, entry in enumerate(writeups):
        if not isinstance(entry, dict):
            raise DraftError(f"writeups[{i}] must be an object")
    return writeups


def _check_tool(tool: Any) -> None:
    if not isinstance(tool, str) or tool.lower() != TOOL:
        raise DraftError(f"tool must be {TOOL!r} (any case), got {tool!r}")


def _index(value: Any, count: int) -> int:
    return value if _whole(value) and 0 <= value < count else 0


def build_draft(entries: list[dict], active_index: Any = 0) -> dict[str, Any]:
    """Working set → the draft file structure. Entries are normalised; index clamped to 0."""
    writeups = [normalise_entry(e) for e in _check_writeups(entries)] or [normalise_entry({})]
    return {
        "tool": TOOL,
        "draft_version": DRAFT_VERSION,
        "saved_at": datetime.datetime.now(datetime.timezone.utc)
                    .isoformat(timespec="seconds").replace("+00:00", "Z"),
        "active_index": _index(active_index, len(writeups)),
        "writeups": writeups,
    }


def draft_from_request(body: Any) -> dict[str, Any]:
    """Save request `{"writeups": [...], "active_index": n}` → draft. `tool` optional, but if
    present it must be "zapis" (so a draft file can be POSTed back as-is)."""
    if not isinstance(body, dict):
        raise DraftError("request body must be a JSON object")
    if "tool" in body:
        _check_tool(body["tool"])
    if "writeups" not in body:
        raise DraftError("writeups is required")
    return build_draft(body["writeups"], body.get("active_index", 0))


def parse_draft(data: Any) -> tuple[list[dict], int]:
    """Draft file content → (normalised entries, active index). Lenient about entry contents,
    strict about the envelope. Unknown draft_version → warning, loaded anyway."""
    if not isinstance(data, dict):
        raise DraftError("draft must be a JSON object")
    _check_tool(data.get("tool"))
    if "writeups" not in data:
        raise DraftError("writeups is required")
    writeups = _check_writeups(data["writeups"])
    if data.get("draft_version") not in DRAFT_VERSIONS:
        log.warning("Unknown draft_version %r (known: %s) — loading anyway",
                    data.get("draft_version"), ", ".join(DRAFT_VERSIONS))
    entries = [normalise_entry(e) for e in writeups] or [normalise_entry({})]
    return entries, _index(data.get("active_index"), len(entries))


def common_ctf_name(names: Iterable[str]) -> str:
    """The CTF name shared by every entry that has one; "" when they differ or none is set."""
    distinct = {n.strip() for n in names if n.strip()}
    return distinct.pop() if len(distinct) == 1 else ""


def draft_filename(draft: dict[str, Any]) -> str:
    names = (e["ctf_name"] for e in draft["writeups"])
    return slugify(common_ctf_name(names), "draft") + DRAFT_SUFFIX


def dump_draft(draft: dict[str, Any]) -> bytes:
    return (json.dumps(draft, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
