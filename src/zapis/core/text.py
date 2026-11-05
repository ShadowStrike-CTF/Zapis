# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Text helpers shared by the exporters — fenced-code parsing and safe Markdown output.

Pure stdlib (`re`). No Markdown library: Zapis only needs to recognise fenced code blocks
in free text and keep single-line Markdown fields single-line.
"""
from __future__ import annotations

import re
from typing import NamedTuple

# CommonMark fence: up to 3 spaces of indent, then 3+ backticks or 3+ tildes, then an info string.
_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
# Closing fence: same character, at least as long as the opener, nothing after but whitespace.
_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_NEWLINE = re.compile(r"\r\n|\r|\n")
_BACKTICKS = re.compile(r"`+")


class Segment(NamedTuple):
    kind: str   # "prose" or "code"
    lang: str   # language tag from the fence info string ("" if none, always "" for prose)
    body: str


def split_fences(text: str) -> list[Segment]:
    """Split free text into prose and fenced-code segments.

    Text without fences comes back as exactly one prose segment holding the text unchanged
    (also for ""), so templates render it the way v1.3.2 did. An unclosed fence runs to the
    end of the text (CommonMark).
    """
    lines = text.split("\n")
    segments: list[Segment] = []
    prose: list[str] = []
    i = 0
    while i < len(lines):
        m = _OPEN.match(lines[i])
        # A backtick fence's info string may not contain backticks (CommonMark) — then it is prose.
        if not m or (m.group(2)[0] == "`" and "`" in m.group(3)):
            prose.append(lines[i])
            i += 1
            continue
        if prose:
            segments.append(Segment("prose", "", "\n".join(prose)))
            prose = []
        indent, fence, info = len(m.group(1)), m.group(2), m.group(3).strip()
        lang = info.split()[0] if info else ""
        body: list[str] = []
        i += 1
        while i < len(lines):
            c = _CLOSE.match(lines[i])
            if c and c.group(1)[0] == fence[0] and len(c.group(1)) >= len(fence):
                i += 1
                break
            line = lines[i]
            # Content lines lose up to the opener's indent (CommonMark).
            strip = len(line) - len(line.lstrip(" "))
            body.append(line[min(indent, strip):])
            i += 1
        segments.append(Segment("code", lang, "\n".join(body)))
    if prose:
        segments.append(Segment("prose", "", "\n".join(prose)))

    if not any(s.kind == "code" for s in segments):
        return segments  # one prose segment, byte-for-byte the input
    # With fences present, the newlines around a fence are layout, not content.
    return [
        s if s.kind == "code" else s._replace(body=s.body.strip("\n"))
        for s in segments
        if s.kind == "code" or s.body.strip()
    ]


def has_code(*texts: str) -> bool:
    """True if any of the texts contains a fenced code block."""
    return any(seg.kind == "code" for t in texts for seg in split_fences(t))


def md_inline_code(s: str) -> str:
    """Wrap `s` as a CommonMark inline code span that survives backticks inside it.

    The delimiter is one backtick longer than the longest backtick run in `s`; a space pads
    each side when `s` starts or ends with a backtick. Plain text gives `s` in single backticks.
    """
    longest = max((len(run) for run in _BACKTICKS.findall(s)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if s.startswith("`") or s.endswith("`") else ""
    return f"{fence}{pad}{s}{pad}{fence}"


def md_line(s: str) -> str:
    """Collapse embedded line breaks to spaces — keeps a single-line Markdown field on one line."""
    return _NEWLINE.sub(" ", s)


def slugify(s: str, fallback: str) -> str:
    """Lower-case ASCII slug for filenames; `fallback` when nothing usable is left."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or fallback
