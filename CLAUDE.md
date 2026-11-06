# Zapis — CLAUDE.md

## Identity
**Tool:** Zapis
**One-liner:** CTF writeup templating and export tool. Proprietary. by ShadowStrike.
**PyPI slug:** zapis
**GitHub:** ShadowStrike-CTF/zapis
**Port:** 7334
**Colour:** #a93226 (Macedonian brick red)
**Licence:** Proprietary (all rights reserved)
**Copyright:** © 2026 ShadowStrike. All rights reserved.

## What Zapis Does
Zapis is a local browser tool for producing structured CTF competition writeups.
A competitor fills in a form covering challenge name, category, difficulty, tools used,
solution approach, flag, and notes. Zapis exports the writeup in three formats:
- Markdown (.md) — for GitHub or personal knowledge base
- HTML — styled, self-contained, readable in any browser
- PDF — for submission or archiving

## Architecture
- **Backend:** FastAPI at port 7334
- **Frontend:** Single-page HTML form served by FastAPI
- **Export pipeline:** form data → Jinja2 template → Markdown / HTML / PDF
- **PDF generation:** weasyprint (headless, no browser dependency)
- **Launcher:** `src/zapis/__main__.py` — thin wrapper calling `zapis.main.main()`
  (same devnull guard pattern as Sarissa for windowed exe compatibility)
- **Port constant:** `PORT = 7334` in `src/zapis/main.py` — single source of truth

## Delivery
- Local browser only — no server, no auth, no external calls
- `python -m zapis` launches the server and opens the browser

## Architecture Invariants (INVs)
- INV-1: All export logic lives in `src/zapis/core/` — never in the web or CLI layer
- INV-2: The form schema is defined once in `src/zapis/core/schema.py` — used by all exporters
- INV-3: Each exporter (md, html, pdf) is a separate module in `src/zapis/core/exporters/`
- INV-4: No export logic in `main.py`, `__main__.py`, or any web handler
- INV-5: Templates live in `src/zapis/templates/` — never inline strings in exporter code
- INV-6: PORT = 7334 defined once in `main.py` — never duplicated

## Module Structure (target)
```
src/zapis/
  __init__.py
  __main__.py          # thin launcher — calls main.main()
  main.py              # FastAPI app, PORT=7334, uvicorn thread, browser open
  cli.py               # `zapis` launches the web UI, `zapis create` exports a writeup
  core/
    __init__.py
    export.py          # format dispatch shared by web + CLI: schema → (bytes, media type, filename)
    schema.py          # WriteupSchema dataclass — single source of truth for form fields
    import_sarissa.py  # Sarissa export JSON → pre-filled writeup dicts (Phase 6)
    text.py            # fence parser (split_fences) + Markdown escape helpers (Phase 2)
    draft.py           # draft file build/parse + normalise_entry (Phase 2)
    bundle.py          # multi-writeup bundle export: md / html / pdf / zip (Phase 2)
    exporters/
      __init__.py
      markdown.py      # schema → .md string
      html.py          # schema → styled HTML string (uses templates/writeup.html)
      pdf.py           # schema → PDF bytes (via weasyprint)
  web/
    __init__.py
    routes.py          # FastAPI route handlers — call core exporters, never export directly
  templates/
    writeup.html       # Jinja2 template for HTML export (wrapper around the partials)
    writeup.md         # Jinja2 template for Markdown export (wrapper around the partial)
    _writeup_style.html  # shared <style> block for writeup.html + bundle.html (Phase 2)
    _writeup_body.html # one writeup's header…sections — shared by single + bundle (Phase 2)
    _writeup_body.md   # one writeup's body — shared by single + bundle (Phase 2)
    bundle.html        # multi-writeup bundle: title page, contents, one writeup per page (Phase 2)
    bundle.md          # multi-writeup bundle in Markdown (Phase 2)
  static/
    index.html         # single-page form UI
```

## Writeup Schema (core fields)
- `challenge_name` — str
- `ctf_name` — str
- `category` — str, one of Forensics, OSINT, Crypto, Pwn, Web, Reverse, Misc
  (source of truth: `CATEGORIES` in `src/zapis/core/schema.py` — this list is a copy)
- `difficulty` — int 1–3
- `tools_used` — list[str]
- `approach` — str (free text — solution walkthrough)
- `flag` — str
- `notes` — str (optional)
- `author` — str (defaults to "ShadowStrike")
- `date` — str (ISO date, defaults to today)
- `time_spent_minutes` — int ≥ 0 (optional, defaults to 0; 0 means "not recorded" and renders nothing)

## UI Design
- Brick red theme: `--brick: #a93226`, dark background matching Megdan line style
- Single-page form — all fields visible, no pagination
- Three export buttons: Download MD | Download HTML | Download PDF
- No `window.alert`, `window.prompt`, `window.confirm`
- No green in UI
- No external CSS/JS dependencies — all inline

## Build Constraints
- Python 3.11 minimum
- Dependencies: fastapi, uvicorn, jinja2, weasyprint
- **WeasyPrint native dependencies:** weasyprint is not pure Python — it requires the
  native Pango/Cairo libraries at runtime.
  - CI: `apt install` them before pytest (e.g. `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2`)
  - PyInstaller (later phase): the GTK/Pango runtime must be bundled for Windows builds
- src/ layout — all code under src/zapis/
- Proprietary licence — © 2026 ShadowStrike. All rights reserved.
- Every source file header: `# © 2026 ShadowStrike. All rights reserved.`
- Commit trailer: `Co-Authored-By: Digger (Claude Opus 5.5) <noreply@anthropic.com>`

## PACKAGING (PyInstaller)
Spec: zapis.spec (onefile, console=False, pathex=['src'])
Datas: src/zapis/static/index.html → zapis/static/
       src/zapis/templates/ → zapis/templates/ (exporters load via Path(__file__)/../../../templates)
Static dir: main.py static_dir() returns sys._MEIPASS/zapis/static when frozen.
Devnull guard: __main__.py redirects sys.stdout/stderr to devnull when None.
Build: pyinstaller zapis.spec
Output: dist/zapis (Linux ELF, ~38 MB)
WeasyPrint: pyinstaller-hooks-contrib's hook-weasyprint collects weasyprint data files
  (css/html5_ua.css etc.) and bundles the build host's libpango-1.0, libpangoft2-1.0,
  libharfbuzz, libharfbuzz-subset, libgobject-2.0 and libfontconfig (+ their deps) and
  /etc/fonts config. Cairo is not used by WeasyPrint >= 53 and is not bundled.
  The build host MUST have the native libs installed (libpango-1.0-0, libpangoft2-1.0-0,
  libharfbuzz0b, libharfbuzz-subset0, libgdk-pixbuf-2.0-0) or the hook bundles nothing and
  PDF export fails. Font files themselves are not bundled — target needs system fonts.
  Treat the exe as tied to the build host's glibc; install the same libs on targets to be safe.
Hiddenimports: none. Probe (--collect-submodules weasyprint) showed no weasyprint misses;
  fontTools.ttLib.* and pycparser.lextab/yacctab warnings are benign false positives.

## Phase 6 — Sarissa Export JSON Import
Load a Sarissa session export (Sarissa `GET /api/export`, schema v1.0 or v1.3) into Zapis as
pre-filled writeups. File-based only — the user picks the `.json` file Sarissa saved.

### Endpoint: `POST /api/import/sarissa`
- Body: the full Sarissa export JSON object, unmodified.
- Validation — each of these is a 422 with a string `detail`:
  - malformed JSON, or a body that is not a JSON object
  - `tool` missing, not a string, or not `"sarissa"` compared case-insensitively
    (`tool.lower() == "sarissa"` — Sarissa emits `"Sarissa"`)
  - `challenges` missing or not a list (an empty list is valid)
  - a `challenges[]` entry that is not an object
- Schema version (F01, Zapis 1.3.0) — never an error:
  - Known versions: `"1.0"` and `"1.3"` (`SCHEMA_VERSIONS` in `core/import_sarissa.py`) → imported silently.
    Sarissa emits `"1.3"` since its Phase 13 (v1.3 adds `challenge_time_seconds`; additive — mapped
    to `time_spent_minutes` since Zapis Phase 2 / P2-1).
  - Any other value (incl. missing) → `logging` warning on `zapis.import_sarissa`, then imported anyway.
- Lenient fields — never an error:
  - `name` / `notes` missing (or not a string) on a challenge → `""`
  - `category` missing, not a string, or not in `CATEGORIES` (case-insensitive) → `""`
  - `challenge_time_seconds` missing, not an int, or negative → `time_spent_minutes: 0`
  - `session` missing, null or not an object → `ctf_name` is `""`. No 409: Zapis holds no
    session state of its own; the 409 NoActiveSession convention is Sarissa's, and Sarissa
    already refuses to export without an active session.
- Returns: a JSON list of pre-filled writeup dicts, one per challenge, in file order:
  `{"challenge_name": str, "ctf_name": str, "category": str, "difficulty": 0,
    "tools_used": [], "approach": str, "flag": "", "time_spent_minutes": int}`
  (`category` and `time_spent_minutes` added by P2-1 — see Field mapping.)
- `challenges` empty → a list with one blank entry (`ctf_name` still filled from the session).
- Unknown extra keys anywhere in the export are ignored.

### Field mapping
| Sarissa export        | Zapis writeup    |
|-----------------------|------------------|
| `challenges[].name`   | `challenge_name` |
| `session.name`        | `ctf_name` (same value on every entry) |
| `challenges[].notes`  | `approach` (pre-fill — user edits before export) |
| `challenges[].category` | `category` — case-insensitive match against `CATEGORIES`, stored with canonical casing; no match → `""` (P2-1) |
| `challenges[].challenge_time_seconds` | `time_spent_minutes` = `round(seconds / 60)`; bad/missing/negative → `0` (P2-1) |
| —                     | `difficulty`, `tools_used`, `flag` left blank |

`difficulty: 0` and `category: ""` are deliberately invalid for `WriteupSchema` — the user
must choose them before export. The import never builds a `WriteupSchema`.
Other Sarissa fields (`points`, `status`, `solved_at`, …) are ignored.

### Core module: `src/zapis/core/import_sarissa.py`
- Pure function `parse_sarissa_export(data: dict) -> list[dict]` — no FastAPI import.
- Raises `SarissaImportError(ValueError)` on invalid input; the route maps it to 422.
- `routes.py` only calls it — no validation or mapping in the web layer (INV-1, INV-4).

### Frontend (`src/zapis/static/index.html`)
- "Import from Sarissa" button in the header → hidden `<input type="file" accept=".json">`.
- File read client-side (`file.text()`), raw text POSTed to `/api/import/sarissa`; the
  server is the single validator (malformed JSON → 422 → shown inline).
- On success (Phase 2): imported challenges are added to the working set — they replace it only
  when it holds a single blank entry. Each fills `challenge_name`, `ctf_name`, `approach`,
  `category` (blank if unmatched), `time_spent_minutes`; `tools_used`, `flag` empty, difficulty
  unchosen; `author`/`date` copied from the current entry, `notes` blank.
- 2+ entries → a "Challenge" picker appears; switching writes the form back to the working set
  first (P2-2 fix — edits are never lost). Export buttons export whatever the form currently shows.
- All user data via `textContent` / `value` — never `innerHTML`. Errors shown inline in the
  header status (no browser dialogs). No green.
- Client-side required check also covers category and difficulty (an imported form must
  have them chosen before export).

### Phase 6 INVs
- INV-P6-1: Zapis NEVER calls Sarissa's API directly — import is file-based only
- INV-P6-2: Port 7331 NEVER hardcoded in Zapis
- INV-P6-3: No `results` key expected in Sarissa JSON (ignored if present)
- INV-P6-4: Manual form entry unchanged — import is additive
- INV-P6-5: No new runtime dependencies — stdlib `json` only
- INV-P6-6: Existing export pipeline (MD/HTML/PDF) unchanged

### Tests (`tests/test_import_sarissa.py`, TestClient)
- `test_import_sarissa_valid_single_challenge`
- `test_import_sarissa_valid_multi_challenge`
- `test_import_sarissa_empty_challenges`
- `test_import_sarissa_missing_notes`
- `test_import_sarissa_unknown_schema_version_warns` → 200 + warning (was `_wrong_schema_version` → 422 before F01)
- `test_import_sarissa_wrong_tool` → 422
- `test_import_sarissa_malformed_json` → 422

Minimum 7 new tests for Phase 6. The existing suite stays green; see phase sections for minimum
new test counts (absolute totals are not tracked here — they go stale).

F01 contract tests (`tests/test_sarissa_contract.py`): `SARISSA_1_3_EXPORT` fixture mirrors
Sarissa's `build_export()` (schema "1.3", tool "Sarissa"). `test_accepts_sarissa_1_3_export` plus
known/unknown version, tool-case and still-rejected-tool cases. When Sarissa bumps its export schema,
add the version to `SCHEMA_VERSIONS` and the fixture together.

## Phase 2 — Working set, drafts, bundle export, code blocks (v1.4.0)
P2-1 Sarissa mapping · P2-2 working set + drafts · P2-3 bundle export · P2-4 code blocks + safe MD.
(P2-5 Windows onedir build is a separate task — needs a Windows host.)

### Endpoints (handlers only call core; every core ValueError → 422 with a string `detail`)
- `POST /api/draft/save` — body `{"writeups": [...], "active_index": n}` (`tool` optional; if present
  it must be "zapis", any case). Returns the draft file as an attachment:
  `<ctf-slug>.zapis.json` (common CTF name) or `draft.zapis.json`.
- `POST /api/draft/load` — body: the draft file as-is. Returns `{"writeups": [...], "active_index": n}`,
  every entry normalised. Unknown `draft_version` → warning on `zapis.draft`, loaded anyway.
  `active_index` out of range → 0. Empty `writeups` → one blank entry.
- Draft 422s: malformed JSON, body not an object, `tool` ≠ "zapis" (load: required), `writeups`
  missing / not a list, any `writeups[]` entry not an object.
- `POST /api/export/bundle/{fmt}` — fmt ∈ md, html, pdf, zip. Body `{"writeups": [...], "inner": "md"}`
  (`inner` ∈ md/html/pdf, zip only). 422 detail names every failing entry:
  `Writeup 2 (Phish Tank): difficulty must be 1, 2 or 3, got 0; Writeup 3 (...): ...`.
  Download name `<ctf-slug>-writeups.<ext>` (or `writeups.<ext>` when CTF names differ).

### Draft file
`{"tool": "zapis", "draft_version": "1.0", "saved_at": "<ISO 8601 UTC, Z>", "active_index": 0,
  "writeups": [{...every WriteupSchema field, all optional...}]}` — `DRAFT_VERSIONS` in `core/draft.py`.

### Core modules
- `core/schema.py` — `build_schema(fields) -> WriteupSchema`: the one validator (also re-exported
  as `zapis.core.build_schema`). Blank date → today; `tools_used` must be list[str]; text fields must be str.
- `core/draft.py` — `normalise_entry` (the one lenient entry: wrong type/missing → blank default,
  category matched case-insensitively), `build_draft`, `draft_from_request`, `parse_draft`,
  `DraftError(ValueError)`, `common_ctf_name`.
- `core/bundle.py` — `export_bundle(entries, fmt, inner="md") -> bytes`, `bundle_filename`,
  `BundleError(ValueError)` with `.messages`. Validates every entry before rendering anything.
  Zip: one file per writeup (slug collisions → `-2`, `-3`) + `index.md`, built in `BytesIO`.
  PDF: one `write_pdf()` per bundle (`exporters/pdf.py:html_to_pdf`).
- `core/text.py` — `split_fences` (``` / ~~~, optional language tag, unclosed runs to end),
  `md_inline_code` (CommonMark backtick-run rule), `md_line`, `slugify`.

### Rendering
- Templates: `writeup.{html,md}` are wrappers around `_writeup_body.{html,md}`; `_writeup_style.html`
  is the shared `<style>`. `bundle.{html,md}`: title (common CTF name, else "CTF Writeups"),
  contents, then each writeup via the partial (HTML/PDF: `break-before: page`).
- `approach`/`notes` in HTML: prose → `<p class="prose">`, fences → `<pre><code class="lang">`,
  autoescaped. Code-block CSS (`white-space: pre-wrap; word-break: break-all;
  page-break-inside: auto`) is emitted only when there is code (keeps INV-P2-2).
- Markdown: `md_line` on challenge_name, ctf_name, author, each tool; flag via
  `md_inline_code(md_line(flag))`; approach/notes verbatim; no tools → `_None recorded._`.
- "Time spent: N min" row only when `time_spent_minutes > 0`.

### Frontend
- Working set (`workingSet`, `activeIndex`) in memory only. New challenge / Remove challenge
  (inline confirm, no dialog). Save draft / Open draft (`file.text()` → POST, same as import).
- "Export all" (format select + zip inner select + button) appears with ≥ 2 entries; 422 detail
  shown inline in the header status. "Time spent (min)" number input (min 0, step 1).

### CLI
- `zapis create ... --time-spent MINUTES` (int ≥ 0).
- `zapis bundle DRAFT.zapis.json --format {md,html,pdf,zip} [--inner FMT] [-o PATH]` — reuses
  `parse_draft()` + `export_bundle()`. Errors → stderr, exit 1, nothing written.

### Phase 2 INVs
- INV-P2-1: Stateless server — Zapis never stores writeup content (no server files, DB, localStorage).
- INV-P2-2: Single-writeup MD/HTML for v1.3.2-valid input (no time spent, no fences, no backtick in
  flag) is byte-identical to v1.3.2 — `tests/test_golden.py` + `tests/golden/`.
  One decided exception: MD with an empty tools list renders `_None recorded._`.
- INV-P2-3: User text is never trusted markup — autoescape on, no `|safe`, no `Markup()`.
- INV-P2-4: One validator — `build_schema()` for every export path (single, bundle, CLI).
  Import and draft-load never call it.
- INV-P2-5: One `normalise_entry()` (core/draft.py), shared by import and draft-load.
- INV-P2-6: No new runtime deps — stdlib `json`, `zipfile`, `io`, `re` only. WeasyPrint stays lazy:
  imported only for pdf output (`bundle.py` only for fmt pdf or zip with inner pdf).

### Tests (Phase 2: 148 new)
`test_golden.py` (INV-P2-2), `test_text.py` (P2-4), `test_phase2_mapping.py` (P2-1),
`test_draft.py` (P2-2), `test_bundle.py` (P2-3), `test_ui_static.py` (no HTML sinks, no dialogs,
no green, no |safe, no new deps). Two pre-existing tests changed on purpose: the Phase 6 `blank()`
helper gained `time_spent_minutes`; the F01 contract test now expects `"Lost USB"` → `Forensics`, 49 min.

## Phase 3 — Sarissa import integration (v1.5.0)
End-to-end test of the Sarissa → Zapis pipeline, plus the `solved_at` → `date` mapping.
Status: planned (M/1.1.14). Build lands on branch `claude/zapis-phase-3-sarissa-xyb8kq`.

### Decisions (locked by R)
- `solved_at` → `date`: **adopted (Option A).** A string that starts `YYYY-MM-DD` and parses as a real
  date (`re` + `datetime.date.fromisoformat`) → that date. Null, missing, non-string or unparsable → `""`.
  A bare `[:10]` slice is not enough: Python 3.11 `fromisoformat` also accepts week dates (`2026-W43-6`).
  It is the UTC date part, so a late-night local solve can show the next day.
- The UI keeps the current entry's date when an imported `date` is blank
  (`entry.date = e.date || base.date || todayISO()`). Solved challenges get their solve date.
- Additive merge testing: a Playwright browser test. `playwright` is a test-only `[e2e]` extra.

### Mapping as of Ph3
| Sarissa export | Zapis writeup |
|---|---|
| `challenges[].name` | `challenge_name` |
| `session.name` | `ctf_name` |
| `challenges[].notes` | `approach` (unchanged) |
| `challenges[].category` | `category` (case-insensitive, else `""`) |
| `challenges[].challenge_time_seconds` | `time_spent_minutes` (`round(s/60)`, bad → 0) |
| `challenges[].solved_at` | `date` (`YYYY-MM-DD`, else `""`) — **new in Ph3** |
| `id`, `points`, `status`, `created_at` | not mapped |

`IMPORT_KEYS` (Ph3): `challenge_name, ctf_name, category, difficulty, tools_used, approach, flag,
time_spent_minutes, date`. `notes` and `author` still come from the UI's current entry.

### Reference fixture
`tests/fixtures/sarissa_1_3_export.json` is the single Sarissa 1.3 reference export, used by the
contract tests, the e2e tests and the G.0 smoke curl.

### Phase 3 INVs
- INV-P3-1: `normalise_entry()` stays the only lenient-entry path; import adds inputs, not a normaliser.
- INV-P3-2: `points`, `status`, `id`, `created_at` stay unmapped. `notes` → `approach` unchanged.
- INV-P3-3: The additive merge stays client-side. The server never sees or stores the working set.
- INV-P3-4: `playwright` is test-only (`[e2e]`); runtime deps unchanged.
- INV-P3-5: `tests/fixtures/sarissa_1_3_export.json` is the single reference fixture. A Sarissa schema
  bump updates it together with `SCHEMA_VERSIONS`.

## Testing Standard
- All tests in `tests/`
- pytest with `[test]` extras in pyproject.toml
- Test exporters against known schema inputs — assert output contains expected field values
- Test routes with FastAPI TestClient
- No test touches the filesystem for export — use BytesIO / StringIO

## WHAT NOT TO DO
- Never put export logic outside `src/zapis/core/`
- Never duplicate PORT = 7334
- Never use `window.alert`, `window.prompt`, `window.confirm`
- Never use green in UI
- Never inline template strings in exporter code — use `src/zapis/templates/`
- Never make external network calls
- Never assume `pip install weasyprint` alone gives working PDF export — Pango/Cairo native libs are required (CI + PyInstaller)
- Never use `git add -A` — path-scoped commits only
- Never bundle unrelated work: one PR per capability on a `claude/…` branch (R reviews and merges);
  chore commits (docs, CLAUDE.md, metadata) go direct to main

## F04 — licence: MIT → Proprietary
- LICENSE: all rights reserved, no reproduction/distribution without ShadowStrike's written permission
- pyproject: `license = {text = "Proprietary"}`, classifier `License :: Other/Proprietary License`
- Every package .py carries `# © 2026 ShadowStrike. All rights reserved.` in its header
  (vendored `_vendor/megdan_schema/` excluded — hash-pinned, never edited)
- README footer: `© 2026 ShadowStrike. All rights reserved. Aut Viam Inveniam Aut Faciam`
- MIT releases already on PyPI stay MIT; the proprietary licence applies from this version on
- Version 1.1.2 → 1.2.0. No tag pushed

## Security Middleware — TrustedHostMiddleware (F02 — M/1.1.12)

TrustedHostMiddleware is active on this tool. It restricts accepted Host headers
to 127.0.0.1 and localhost only (allowed_hosts=["127.0.0.1", "localhost"]).
This is a deliberate security control — not a bug.

WHAT NOT TO DO:
- Do not remove TrustedHostMiddleware
- Do not widen allowed_hosts (no "*", no "testserver", no other hosts)
- Do not remove the tests/conftest.py TestClient patch or revert its default
  base_url to Starlette's "http://testserver"

Test suite: tests/conftest.py patches TestClient's default base_url to
"http://127.0.0.1" to match the middleware. If tests fail with 400 Invalid host
header, check base_url first.
