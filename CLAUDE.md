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
