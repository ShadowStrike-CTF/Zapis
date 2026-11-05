# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""P2-4 — fenced code blocks and safe Markdown output (core/text.py + exporters)."""
from __future__ import annotations

import pytest

from zapis.core.exporters.html import export_html
from zapis.core.exporters.markdown import export_markdown
from zapis.core.schema import WriteupSchema
from zapis.core.text import Segment, md_inline_code, md_line, split_fences

FENCED = "Ran the script:\n\n```python\nprint('hi')\n```\nThen read the output."


def make(**overrides) -> WriteupSchema:
    fields = dict(
        challenge_name="Fence Test", ctf_name="TestCTF", category="Pwn", difficulty=1,
        tools_used=["gdb"], approach="plain", flag="flag{x}", date="2026-11-05",
    )
    fields.update(overrides)
    return WriteupSchema(**fields)


# --- split_fences --------------------------------------------------------------

def test_fenced_block_splits_into_prose_and_code():
    assert split_fences(FENCED) == [
        Segment("prose", "", "Ran the script:"),
        Segment("code", "python", "print('hi')"),
        Segment("prose", "", "Then read the output."),
    ]


@pytest.mark.parametrize("text", ["", "one line", "a\n\nb\n", "  indented\n\ttabbed"])
def test_no_fence_is_one_untouched_prose_segment(text):
    assert split_fences(text) == [Segment("prose", "", text)]


def test_unclosed_fence_runs_to_end():
    segs = split_fences("intro\n~~~\nline 1\nline 2")
    assert segs == [Segment("prose", "", "intro"), Segment("code", "", "line 1\nline 2")]


def test_tilde_fence_and_closer_must_match():
    # A ``` line inside a ~~~ block is content, not a closer.
    segs = split_fences("~~~sh\necho a\n```\necho b\n~~~")
    assert segs == [Segment("code", "sh", "echo a\n```\necho b")]


def test_backtick_info_string_with_backtick_is_not_a_fence():
    assert split_fences("```a`b\nx") == [Segment("prose", "", "```a`b\nx")]


# --- HTML rendering --------------------------------------------------------------

def test_html_fenced_block_renders_pre_code_with_language():
    html = export_html(make(approach=FENCED))
    assert '<pre><code class="python">print(&#39;hi&#39;)</code></pre>' in html
    assert '<p class="prose">Ran the script:</p>' in html
    assert '<p class="prose">Then read the output.</p>' in html


def test_html_script_inside_fence_is_escaped():
    html = export_html(make(approach="```html\n<script>alert(1)</script>\n```"))
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


def test_html_notes_also_render_fences():
    html = export_html(make(notes="```\nnotes code\n```"))
    assert "<pre><code>notes code</code></pre>" in html


def test_html_code_css_only_when_code_present():
    plain = export_html(make())
    fenced = export_html(make(approach=FENCED))
    assert "white-space: pre-wrap;\n    word-break: break-all;" not in plain
    assert "white-space: pre-wrap;\n    word-break: break-all;" in fenced
    assert "page-break-inside: auto;\n  }\n  pre code" in fenced


def test_html_no_fence_text_matches_v132_markup():
    html = export_html(make(approach="line one\n\nline <two>"))
    assert '<p class="prose">line one\n\nline &lt;two&gt;</p>' in html
    assert "<pre>" not in html


# --- Markdown helpers --------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("flag{plain}", "`flag{plain}`"),
    ("fl`ag", "``fl`ag``"),
    ("a``b`c", "```a``b`c```"),
    ("`edge`", "`` `edge` ``"),
])
def test_md_inline_code(raw, expected):
    assert md_inline_code(raw) == expected


def test_md_line_collapses_all_line_breaks():
    assert md_line("a\nb\r\nc\rd") == "a b c d"


def test_markdown_flag_with_backtick_is_valid_inline_code():
    md = export_markdown(make(flag="flag{b`tick}"))
    assert "## Flag\n``flag{b`tick}``\n" in md


def test_markdown_newline_in_challenge_name_cannot_break_heading():
    md = export_markdown(make(challenge_name="Line one\n# injected", ctf_name="C\nD",
                              author="A\nB", tools_used=["t1\n- t2"]))
    lines = md.split("\n")
    assert lines[0] == "# Line one # injected"
    assert "**CTF:** C D" in lines
    assert "**Author:** A B" in lines
    assert "- t1 - t2" in lines
    assert "# injected" not in lines


def test_markdown_approach_and_notes_verbatim():
    md = export_markdown(make(approach=FENCED, notes="*keep* `me`"))
    assert FENCED in md
    assert "*keep* `me`" in md


def test_markdown_empty_tools_renders_none_recorded():
    # Deliberate exception to INV-P2-2 (decided by R): matches the HTML "None recorded."
    md = export_markdown(make(tools_used=[]))
    assert "## Tools Used\n_None recorded._\n" in md
