# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""WriteupSchema — single source of truth for Zapis writeup fields."""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field

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

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(
                f"category must be one of {CATEGORIES}, got {self.category!r}"
            )
        if self.difficulty not in (1, 2, 3):
            raise ValueError(f"difficulty must be 1, 2 or 3, got {self.difficulty!r}")
        if not self.flag.strip():
            raise ValueError("flag must not be empty")
