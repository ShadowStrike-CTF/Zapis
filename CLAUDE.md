# Zapis — CLAUDE.md

## Identity
**Tool:** Zapis
**One-liner:** CTF writeup templating and export tool. MIT licensed community tool. by ShadowStrike.
**PyPI slug:** zapis
**GitHub:** ShadowStrike-CTF/zapis
**Port:** 7334
**Colour:** #a93226 (Macedonian brick red)
**Licence:** MIT
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
  core/
    __init__.py
    schema.py          # WriteupSchema dataclass — single source of truth for form fields
    import_sarissa.py  # Sarissa export JSON → pre-filled writeup dicts (Phase 6)
    exporters/
      __init__.py
      markdown.py      # schema → .md string
      html.py          # schema → styled HTML string (uses templates/writeup.html)
      pdf.py           # schema → PDF bytes (via weasyprint)
  web/
    __init__.py
    routes.py          # FastAPI route handlers — call core exporters, never export directly
  templates/
    writeup.html       # Jinja2 template for HTML export
    writeup.md         # Jinja2 template for Markdown export
  static/
    index.html         # single-page form UI
```

## Writeup Schema (core fields)
- `challenge_name` — str
- `ctf_name` — str
- `category` — str (e.g. Forensics, OSINT, Crypto, Pwn, Web, Misc)
- `difficulty` — int 1–3
- `tools_used` — list[str]
- `approach` — str (free text — solution walkthrough)
- `flag` — str
- `notes` — str (optional)
- `author` — str (defaults to "ShadowStrike")
- `date` — str (ISO date, defaults to today)

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
- MIT licence — © 2026 ShadowStrike. All rights reserved.
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
Load a Sarissa session export (Sarissa `GET /api/export`, schema v1.0) into Zapis as
pre-filled writeups. File-based only — the user picks the `.json` file Sarissa saved.

### Endpoint: `POST /api/import/sarissa`
- Body: the full Sarissa export JSON object, unmodified.
- Validation — each of these is a 422 with a string `detail`:
  - malformed JSON, or a body that is not a JSON object
  - `schema_version != "1.0"`
  - `tool != "sarissa"`
  - `challenges` missing or not a list (an empty list is valid)
  - a `challenges[]` entry that is not an object
- Lenient fields — never an error:
  - `name` / `notes` missing (or not a string) on a challenge → `""`
  - `session` missing, null or not an object → `ctf_name` is `""`. No 409: Zapis holds no
    session state of its own; the 409 NoActiveSession convention is Sarissa's, and Sarissa
    already refuses to export without an active session.
- Returns: a JSON list of pre-filled writeup dicts, one per challenge, in file order:
  `{"challenge_name": str, "ctf_name": str, "category": "", "difficulty": 0,
    "tools_used": [], "approach": str, "flag": ""}`
- `challenges` empty → a list with one blank entry (`ctf_name` still filled from the session).
- Unknown extra keys anywhere in the export are ignored.

### Field mapping
| Sarissa export        | Zapis writeup    |
|-----------------------|------------------|
| `challenges[].name`   | `challenge_name` |
| `session.name`        | `ctf_name` (same value on every entry) |
| `challenges[].notes`  | `approach` (pre-fill — user edits before export) |
| —                     | `category`, `difficulty`, `tools_used`, `flag` left blank |

`difficulty: 0` and `category: ""` are deliberately invalid for `WriteupSchema` — the user
must choose them before export. The import never builds a `WriteupSchema`.

### Core module: `src/zapis/core/import_sarissa.py`
- Pure function `parse_sarissa_export(data: dict) -> list[dict]` — no FastAPI import.
- Raises `SarissaImportError(ValueError)` on invalid input; the route maps it to 422.
- `routes.py` only calls it — no validation or mapping in the web layer (INV-1, INV-4).

### Frontend (`src/zapis/static/index.html`)
- "Import from Sarissa" button in the header → hidden `<input type="file" accept=".json">`.
- File read client-side (`file.text()`), raw text POSTed to `/api/import/sarissa`; the
  server is the single validator (malformed JSON → 422 → shown inline).
- On success: fills `challenge_name`, `ctf_name`, `approach`; clears `tools_used`, `flag`;
  blanks the category and difficulty selects. `notes`, `author`, `date` are left as-is.
- 2+ entries → a "Challenge" picker appears beside the button; choosing one refills the form
  from that entry. Export buttons export whatever the form currently shows.
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
- `test_import_sarissa_wrong_schema_version` → 422
- `test_import_sarissa_wrong_tool` → 422
- `test_import_sarissa_malformed_json` → 422

Minimum 7 new tests; the existing 32 stay green (39 total).

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
- Never open PRs for Phase 1 — commit directly to main
