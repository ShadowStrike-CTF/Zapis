# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Ph3 — browser end-to-end test of the Sarissa import into the working set.

The additive merge lives in index.html (the server keeps no working set, INV-P2-1 / INV-P3-3),
so only a real browser can test it. Needs the `[e2e]` extra (playwright) and a Chromium:
- ZAPIS_E2E_CHROMIUM — optional path to a Chromium binary (else Playwright's own install).
- ZAPIS_E2E_REQUIRED=1 — fail instead of skip when the browser cannot start (set in CI).
"""
from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

import uvicorn  # noqa: E402

from zapis.main import HOST, create_app  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sarissa_1_3_export.json"
START_DATE = "2026-01-15"  # set on the page first, so "kept the current date" is visible


@pytest.fixture(scope="module")
def base_url():
    with socket.socket() as s:
        s.bind((HOST, 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), host=HOST, port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            pytest.fail("Zapis test server did not start")
        time.sleep(0.05)
    yield f"http://{HOST}:{port}"
    server.should_exit = True
    thread.join(5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=os.environ.get("ZAPIS_E2E_CHROMIUM") or None)
        except Exception as exc:  # browser binary missing / cannot start
            if os.environ.get("ZAPIS_E2E_REQUIRED") == "1":
                raise
            pytest.skip(f"Chromium not available for e2e tests: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser, base_url):
    pg = browser.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda exc: errors.append(str(exc)))
    pg.goto(base_url + "/")
    # Categories load asynchronously; an import before that could not select "Forensics".
    pg.wait_for_function("document.querySelectorAll('#category option').length > 1")
    pg.fill("#date", START_DATE)
    yield pg
    assert errors == [], errors
    pg.close()


def picker_labels(pg) -> list[str]:
    return pg.eval_on_selector_all("#import_pick option", "opts => opts.map(o => o.textContent)")


def import_fixture(pg, expected_total: int) -> None:
    pg.set_input_files("#import_file", str(FIXTURE))
    pg.wait_for_function(
        "n => document.querySelectorAll('#import_pick option').length === n", arg=expected_total)
    assert "Imported 2 challenges" in pg.text_content("#import_status")


def switch_to(pg, index: int) -> None:
    pg.select_option("#import_pick", str(index))


def test_import_replaces_single_blank_entry(page):
    import_fixture(page, 2)
    assert picker_labels(page) == ["1. Lost USB", "2. Phish Tank"]
    assert page.is_visible("#import_pick")
    # Active entry = first imported: every mapped field reaches the form.
    assert page.input_value("#challenge_name") == "Lost USB"
    assert page.input_value("#ctf_name") == "DFIR-Cup-2026"
    assert page.input_value("#category") == "Forensics"
    assert page.input_value("#difficulty") == ""  # unchosen — user picks before export
    assert page.input_value("#approach") == "Carved the FAT partition with photorec."
    assert page.input_value("#time_spent_minutes") == "49"
    assert page.input_value("#date") == "2026-10-24"  # solved_at
    assert page.input_value("#flag") == ""
    assert page.input_value("#tools_used") == ""

    switch_to(page, 1)
    assert page.input_value("#challenge_name") == "Phish Tank"
    assert page.input_value("#category") == ""
    assert page.input_value("#time_spent_minutes") == ""
    assert page.input_value("#date") == START_DATE  # unsolved → keeps the current date, not blank


def test_import_into_non_empty_set_is_additive(page):
    page.fill("#challenge_name", "Hand Typed")
    page.fill("#approach", "Typed before the import.")
    page.fill("#flag", "flag{kept}")
    import_fixture(page, 3)
    assert picker_labels(page) == ["1. Hand Typed", "2. Lost USB", "3. Phish Tank"]
    assert page.input_value("#import_pick") == "1"  # active = first imported
    assert page.input_value("#challenge_name") == "Lost USB"

    switch_to(page, 0)
    assert page.input_value("#challenge_name") == "Hand Typed"
    assert page.input_value("#approach") == "Typed before the import."
    assert page.input_value("#flag") == "flag{kept}"
    assert page.input_value("#date") == START_DATE


def test_two_sequential_imports_both_additive(page):
    import_fixture(page, 2)
    page.fill("#flag", "flag{edited}")  # edit an imported entry before the second import
    import_fixture(page, 4)
    assert picker_labels(page) == ["1. Lost USB", "2. Phish Tank", "3. Lost USB", "4. Phish Tank"]
    assert page.input_value("#import_pick") == "2"
    assert page.is_visible("#bundle_controls")

    switch_to(page, 0)
    assert page.input_value("#flag") == "flag{edited}"  # first import's edits survive the second
    switch_to(page, 2)
    assert page.input_value("#flag") == ""
    assert page.input_value("#date") == "2026-10-24"
