"""Browser smoke test: every view of the web UI on a fresh home, in headless Chromium.

The test accepts the responsible-use terms on its own throwaway instance, then opens each view. It fails on a
JavaScript error, a failed request, or "undefined" / "NaN" / "[object Object]" on screen, at desktop and phone
width, and checks that the Settings attack-host row (with its Test and Del buttons) fits inside its card.
Skipped unless Playwright for Python and a Chromium are installed (the CI browser job installs both). A local
Chromium can be used with ONIOPS_UI_CHROMIUM=/path/to/chrome.
"""

import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

VIEWS = ["dashboard", "targets", "workbench", "agent", "graph", "aisec", "arsenal", "intel", "reports", "settings"]
BAD_TEXT = ("undefined", "NaN", "[object Object]")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    home = tmp_path_factory.mktemp("ui-home")
    env = {k: v for k, v in os.environ.items() if k not in ("ONIOPS_CONFIG",)}
    env["ONIOPS_HOME"] = str(home)
    subprocess.run([sys.executable, "-m", "oniops", "init"], check=True, env=env, capture_output=True, timeout=120)
    port = _free_port()
    cfg = home / "config.yaml"
    cfg.write_text(re.sub(r"bind_port: \d+", f"bind_port: {port}", cfg.read_text()))
    env["ONIOPS_CONFIG"] = str(cfg)            # a source checkout would otherwise prefer its own config.yaml
    proc = subprocess.Popen([sys.executable, "-m", "oniops", "serve"], env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(150):
        try:
            urllib.request.urlopen(base + "/healthz", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("the server did not start: " + (proc.stdout.read() or b"").decode()[-2000:])
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def _browser(p):
    exe = os.getenv("ONIOPS_UI_CHROMIUM")
    try:
        return p.chromium.launch(**({"executable_path": exe} if exe else {}), args=["--no-sandbox"])
    except sync_api.Error as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("no Chromium for Playwright: run `python -m playwright install chromium`")
        raise


def _open(page, base):
    page.goto(base + "/", wait_until="networkidle")
    if page.is_visible("#termsConfirm"):             # only on first use; afterwards the box is hidden
        page.check("#termsConfirm")
        page.click("#termsAcceptBtn")
        page.wait_for_timeout(800)


def test_every_view_loads_cleanly(server):
    issues: list[str] = []
    with sync_api.sync_playwright() as p:
        b = _browser(p)
        page = b.new_page(viewport={"width": 1400, "height": 900})
        cur = {"view": "load"}
        page.on("pageerror", lambda e: issues.append(f"[{cur['view']}] JS error: {e}"))
        page.on("console", lambda m: m.type == "error" and issues.append(f"[{cur['view']}] console: {m.text}"))
        page.on("response", lambda r: r.status >= 400 and issues.append(
            f"[{cur['view']}] HTTP {r.status} {r.url.replace(server, '')}"))
        _open(page, server)
        for v in VIEWS:
            cur["view"] = v
            page.evaluate("(v) => switchView(v)", v)
            page.wait_for_timeout(800)
            text = page.inner_text("body")
            solid = page.evaluate("""() => [...document.querySelectorAll('.view-section.active .btn:not(.btn-primary)')]
                .filter(b => b.checkVisibility() && getComputedStyle(b).backgroundColor !== 'rgba(0, 0, 0, 0)').length""")
            if solid:
                issues.append(f"[{v}] {solid} secondary buttons are drawn as primary")
            issues += [f"[{v}] shows {bad!r}" for bad in BAD_TEXT if bad in text]
        b.close()
    assert issues == []


def test_attack_host_row_fits_its_card(server):
    with sync_api.sync_playwright() as p:
        b = _browser(p)
        for width in (1400, 412):
            page = b.new_page(viewport={"width": width, "height": 900})
            _open(page, server)
            page.evaluate("() => switchView('settings')")
            page.wait_for_selector(".set-host-row", timeout=10000)
            r = page.evaluate("""() => { const row = document.querySelector('.set-host-row');
                const card = row.parentElement.parentElement;
                return { card: card.getBoundingClientRect().right,
                         buttons: [...row.querySelectorAll('button')].map(x => x.getBoundingClientRect().right) }; }""")
            assert r["buttons"] and max(r["buttons"]) <= r["card"] + 1, (width, r)
            page.close()
        b.close()


def test_views_fit_a_phone(server):
    wide: list[str] = []
    with sync_api.sync_playwright() as p:
        b = _browser(p)
        page = b.new_page(viewport={"width": 412, "height": 915})
        _open(page, server)
        for v in VIEWS:
            page.evaluate("(v) => switchView(v)", v)
            page.wait_for_timeout(500)
            w = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            if w[0] > w[1] + 2:
                wide.append(f"{v}: {w[0]}px wide on a {w[1]}px screen")
        b.close()
    assert wide == []


def test_tool_and_host_text_is_escaped(server):
    """Text from tools and hostnames must not become markup."""
    bad = "<img src=x onerror=window.__x=1>"
    with sync_api.sync_playwright() as p:
        b = _browser(p)
        page = b.new_page(viewport={"width": 1400, "height": 900})
        page.route("**/api/intel?*", lambda r: r.fulfill(json={"exploits": [
            {"id": "1", "title": bad, "type": bad, "platform": "x", "codes": bad}]}))
        page.route("**/api/targets", lambda r: r.fulfill(json={"targets": [
            {"hostname": bad, "ip": "192.0.2.1", "type": "host", "node": bad, "role": bad, "open_ports": "-",
             "services": [{"port": 1, "service": bad}], "vulns": {"critical": 1, "high": 0, "medium": 0, "total": 1}}]}))
        _open(page, server)
        page.evaluate("() => { switchView('intel'); document.getElementById('exploitQueryInput').value = 'a'; searchExploitDb(); }")
        page.wait_for_timeout(800)
        assert page.locator("main img").count() == 0
        assert page.evaluate("window.__x") is None
        b.close()
