"""S8 — Playwright browser path for Goal Graph §12 (docs/GOAL_GRAPH.md).

Opt-in: set AEGIS_PLAYWRIGHT=1 (requires playwright + chromium).
Starts a local uvicorn on an ephemeral port with an isolated DATA_DIR.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

BEEF_RICE_RUN = "Ate beef and rice, run was good, averaged 10:30 for 3 miles."

pytestmark = pytest.mark.skipif(
    os.environ.get("AEGIS_PLAYWRIGHT") != "1",
    reason="Set AEGIS_PLAYWRIGHT=1 after `pip install playwright && playwright install chromium`",
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    data = tmp_path_factory.mktemp("s8-data")
    port = _free_port()
    env = os.environ.copy()
    env["DATA_DIR"] = str(data)
    env["AEGIS_BACKGROUND_SYNC"] = "0"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    import urllib.request

    last_err = None
    while time.time() < deadline:
        if proc.poll() is not None:
            err = (proc.stderr.read() or b"").decode()[:800]
            raise RuntimeError(f"uvicorn exited early: {err}")
        try:
            with urllib.request.urlopen(base + "/health", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception as exc:  # noqa: BLE001 — retry until ready
            last_err = exc
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError(f"server not ready: {last_err}")

    yield base
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_s8_goal_graph_section12_browser_path(live_server):
    """Full §12 browser story: goal → journal → suggestion edit/approve → chat."""
    playwright = pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept("Log Sunday long run"))

        page.goto(live_server + "/", wait_until="networkidle")

        # 1) Create goal from UI (conversation stand-in)
        page.click('a[href="#goals"]')
        page.wait_for_selector("#goal-tree")
        page.fill("#goal-new-title", "Improve running conditioning")
        page.fill("#goal-new-metric", "running_pace")
        page.click("#goal-create-form button[type=submit]")
        page.wait_for_timeout(600)
        assert "running" in page.locator("#goal-tree").inner_text().lower()

        # 2) Submit journal entry via composer → directive
        page.click('a[href="#composer"]')
        page.fill("#compose-text", BEEF_RICE_RUN)
        page.click("#directive-btn")
        page.wait_for_selector("#result:not([hidden])", timeout=20000)
        assert "training planning" in page.locator("#directive-mode").inner_text().lower()

        # 3–5) Contributions / suggestions appear for HITL review
        page.click('a[href="#goals"]')
        page.click("#suggestion-refresh-btn")
        page.wait_for_function(
            """() => {
              const t = document.getElementById('suggestion-list')?.innerText || '';
              return t.includes('Approve') || t.toLowerCase().includes('pace')
                || t.toLowerCase().includes('protein') || t.toLowerCase().includes('run');
            }""",
            timeout=10000,
        )
        sug_text = page.locator("#suggestion-list").inner_text().lower()
        assert "approve" in sug_text

        # 6) Edit + approve suggestion (dialog handler supplies edited title)
        edit_btn = page.locator(
            '#suggestion-list button.sug-decide[data-decision="edited"]'
        ).first
        edit_btn.click()
        page.wait_for_timeout(800)

        # 7) Dashboard / task list updated
        page.click('button.task-view[data-view="inbox"]')
        page.wait_for_timeout(400)
        tasks = page.locator("#task-list").inner_text().lower()
        assert "sunday" in tasks or "run" in tasks or "log" in tasks

        # 8) Screen-aware chat about goals dashboard
        page.click('a[href="#composer"]')
        page.fill("#compose-text", "What am I looking at on my goals dashboard?")
        page.click("#ask-btn")
        page.wait_for_selector("#thread:not([hidden])", timeout=20000)
        page.wait_for_function(
            """() => {
              const t = document.getElementById('thread-log')?.innerText || '';
              return t.toLowerCase().includes('goal')
                || t.toLowerCase().includes('looking')
                || t.toLowerCase().includes('context')
                || t.toLowerCase().includes('dashboard')
                || t.length > 40;
            }""",
            timeout=20000,
        )
        assert len(page.locator("#thread-log").inner_text()) > 10

        browser.close()
