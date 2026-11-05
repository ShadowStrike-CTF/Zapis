# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""WriteupSchema — single source of truth for Zapis writeup fields."""
from __future__ import annotations
import dataclasses
import datetime
from dataclasses import dataclass, field
from typing import Any

CATEGORIES = ("Forensics", "OSINT", "Crypto", "Pwn", "Web", "Reverse", "Misc")

@dataclass
class WriteupSchema:
    challenge_name: str
    ctf_name: str
    category: str                        # must be in CATEGORIES
    difficulty: int                      # 1–3
    tools_used: list[str]
    approach: str                        # free text — solution walkthrough
    flag: str
    notes: str = ""
    author: str = "ShadowStrike"
    date: str = field(
        default_factory=lambda: datetime.date.today().isoformat()
    )
    time_spent_minutes: int = 0          # optional; 0 = not recorded (renders nothing)

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(
                f"category must be one of {CATEGORIES}, got {self.category!r}"
            )
        if self.difficulty not in (1, 2, 3):
            raise ValueError(f"difficulty must be 1, 2 or 3, got {self.difficulty!r}")
        if not self.flag.strip():
            raise ValueError("flag must not be empty")
        minutes = self.time_spent_minutes
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
            raise ValueError(
                f"time_spent_minutes must be a whole number >= 0, got {minutes!r}"
            )


FIELD_NAMES = tuple(f.name for f in dataclasses.fields(WriteupSchema))
_TEXT_FIELDS = ("challenge_name", "ctf_name", "category", "approach", "flag", "notes", "author", "date")


def build_schema(fields: dict[str, Any]) -> WriteupSchema:
    """The one validator (INV-P2-4): raw field dict → WriteupSchema, or ValueError.

    Every export path — single web export, bundle, CLI — goes through here. Import and
    draft-load never call it (their entries may be incomplete on purpose).
    """
    if not isinstance(fields, dict):
        raise ValueError("writeup must be an object")
    fields = dict(fields)
    if not fields.get("date"):
        fields.pop("date", None)  # blank date → today
    tools = fields.get("tools_used")
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        raise ValueError("tools_used must be a list of strings")
    for name in _TEXT_FIELDS:
        if name in fields and not isinstance(fields[name], str):
            raise ValueError(f"{name} must be a string")
    try:
        return WriteupSchema(**fields)
    except TypeError as exc:  # missing or unknown field
        raise ValueError(str(exc).replace("WriteupSchema.__init__() ", "")) from exc
