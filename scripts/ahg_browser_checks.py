#!/usr/bin/env python
"""Browser checks from the ahg.md test plan that need no Copilot sign-in.

Runs against GLOW started locally from this branch (ahg.md section 1.7):
Setup-01, Setup-11 to Setup-14, Deck-01 to Deck-03, Deck-06, Share-01,
Share-02, Share-05 to Share-08, A11y-01 on the share page, A11y-02 and
Load-01, plus an axe scan of each page and a 320px reflow sweep of the
main GLOW pages.

    python scripts/ahg_browser_checks.py --base http://127.0.0.1:5000         --axe web/node_modules/axe-core/axe.min.js

Needs Playwright and Chrome. Exit code 0 when every check passes.
"""
import argparse
import sys

_parser = argparse.ArgumentParser()
_parser.add_argument("--base", default="http://127.0.0.1:5000")
_parser.add_argument("--axe", default="web/node_modules/axe-core/axe.min.js")
_args = _parser.parse_args()
import concurrent.futures
import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = _args.base.rstrip("/")
KIT = Path(__file__).resolve().parents[1] / "docs" / "ahg-2026" / "kit"
AXE = Path(_args.axe).read_text(encoding="utf-8")
results = {}


def record(case, ok, note=""):
    results[case] = ("Pass" if ok else "Fail", note)
    print(f"{case:10} {'Pass' if ok else 'FAIL'}  {note}")


def axe(page):
    page.add_script_tag(content=AXE)
    r = page.evaluate("async () => await axe.run(document, {resultTypes:['violations']})")
    return [(v["id"], v["impact"], len(v["nodes"])) for v in r["violations"]]


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    ctx = browser.new_context(bypass_csp=True)
    page = ctx.new_page()

    # Setup-13: the landing and share pages open with no consent form.
    page.goto(BASE + "/ahg")
    share_first = ctx.new_page()
    share_first.goto(BASE + "/workshop/ahg-2026/share")
    record("Setup-13", page.url.rstrip("/").endswith("/ahg") and "/consent" not in share_first.url,
           f"{page.url.replace(BASE, '')} and {share_first.url.replace(BASE, '')}")
    share_first.close()

    # Setup-14: every way of typing the address arrives at /ahg.
    arrived = {}
    for path in ("/AHG", "/ahg2026", "/ahg-2026", "/ahg/", "/workshop/ahg-2026"):
        page.goto(BASE + path)
        arrived[path] = page.url.replace(BASE, "").rstrip("/")
    record("Setup-14", all(v == "/ahg" for v in arrived.values()), str(arrived))
    page.goto(BASE + "/ahg")

    # Accept GLOW's consent once, for the tool pages in the reflow sweep.
    tool = ctx.new_page()
    tool.goto(BASE + "/audit/")
    if "/consent" in tool.url:
        tool.check("#consent-agree-checkbox")
        tool.click("#consent-continue-btn")
        tool.wait_for_load_state("networkidle")
    tool.close()

    # Setup-01
    body = page.inner_text("main") if page.locator("main").count() else page.inner_text("body")
    h1 = page.locator("h1").all_inner_texts()
    links = {a: page.locator(f'a[href*="{a}"]').count() for a in ("kit.zip", "code-profile", "/share", "deck", "step-cards/")}
    ok = "Accessibility Agents at AHG 2026" in " ".join(h1) and all(links.values()) and links["step-cards/"] == 8 \
        and "Never paste anything private" in body
    record("Setup-01", ok, f"h1={h1} links={links}")

    # Setup-11: structure, plus axe
    h2 = page.locator("main h2").all_inner_texts()
    vio = axe(page)
    record("Setup-11", len(h1) == 1 and len(h2) >= 4 and not vio, f"h2={h2} axe={vio}")

    # Setup-12: no consent needed for tool downloads
    fresh = browser.new_context()
    for path in ("/workshop/ahg-2026/kit.zip", "/workshop/ahg-2026/ahg-2026.code-profile"):
        resp = fresh.request.get(BASE + path, max_redirects=0)
        results.setdefault("Setup-12", ("Pass", ""))
        if resp.status != 200:
            record("Setup-12", False, f"{path} -> {resp.status}")
    if results.get("Setup-12", ("Pass",))[0] == "Pass":
        record("Setup-12", True, "kit.zip and profile download with no consent cookie")
    fresh.close()

    # Share page cases against a test fork
    share = BASE + "/workshop/ahg-2026/share"
    agent = KIT / "examples" / "agents" / "faculty-coach" / "SKILL.md"

    def fresh_share(query=""):
        page.goto(share + query)
        page.evaluate("window.__opened = null; window.open = (u) => { window.__opened = u; return null; }")

    fresh_share("?repo=testfork/accessibility-agents")
    page.set_input_files("#agent-file", str(agent))
    page.wait_for_function("document.getElementById('agent-name').value !== ''")
    status = page.inner_text("#result")
    record("Share-01", page.input_value("#agent-name") == "faculty-coach" and "loaded" in status, status)
    page.click("button[type=submit]")
    url = page.evaluate("window.__opened") or ""
    record("Share-02", url.startswith("https://github.com/testfork/accessibility-agents/issues/new?template=submit-agent.yml") and "kind=My+real+agent" in url and "workshop-code=AHG2026" in url, url[:140])

    fresh_share()
    page.click("button[type=submit]")
    record("Share-05", "empty" in page.inner_text("#result") and page.evaluate("document.activeElement.id") == "agent-text")

    fresh_share()
    page.fill("#agent-text", (KIT / "my-agent" / "SKILL.md").read_text(encoding="utf-8"))
    page.click("button[type=submit]")
    record("Share-06", "name of its own" in page.inner_text("#result") and page.evaluate("document.activeElement.id") == "agent-name")

    fresh_share()
    page.fill("#agent-text", agent.read_text(encoding="utf-8") + "\n" + ("Long guidance line. " * 600))
    page.fill("#agent-name", "long-agent")
    page.click("button[type=submit]")
    msg = page.inner_text("#result")
    record("Share-07", "longer than GitHub accepts" in msg and "share form on GitHub" in msg and not page.evaluate("window.__opened"))

    page.goto((KIT / "share-my-agent.html").resolve().as_uri() + "?repo=testfork/accessibility-agents")
    page.evaluate("window.__opened = null; window.open = (u) => { window.__opened = u; return null; }")
    page.set_input_files("#agent-file", str(agent))
    page.wait_for_function("document.getElementById('agent-name').value !== ''")
    page.click("button[type=submit]")
    record("Share-08", (page.evaluate("window.__opened") or "").startswith("https://github.com/testfork/"))

    page.goto(share)
    vio = axe(page)
    record("Share-axe", not vio, f"axe={vio}")

    # Deck
    page.goto(BASE + "/workshop/deck")
    titles = page.locator("section h2, .slide h2").all_inner_texts()
    sub = "Building Human-Centered AI Workflows for Trusted Accessibility Automation at Scale"
    record("Deck-01", len(titles) == 26 and titles[0].strip() == "Accessibility Agents" and sub in page.content(), f"{len(titles)} slides, first={titles[:1]}")
    page.keyboard.press("End")
    page.wait_for_timeout(300)
    focused_end = page.evaluate("document.activeElement && document.activeElement.textContent")
    page.keyboard.press("Home")
    page.wait_for_timeout(300)
    focused_home = page.evaluate("document.activeElement && document.activeElement.textContent")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(300)
    focused_next = page.evaluate("document.activeElement && document.activeElement.textContent")
    live = page.locator("[aria-live]").count()
    record("Deck-02", "Go make one more champion" in (focused_end or "") and "Accessibility Agents" in (focused_home or "")
           and "Forty thousand" in (focused_next or "") and live > 0,
           f"end={focused_end!r} home={focused_home!r} next={focused_next!r}")
    notes_before = page.evaluate("document.body.dataset.notes")
    page.keyboard.press("n")
    page.wait_for_timeout(200)
    notes_after = page.evaluate("document.body.dataset.notes")
    record("Deck-03", notes_before != notes_after, f"{notes_before} -> {notes_after}")
    vio = axe(page)
    record("Deck-axe", not vio, f"axe={vio}")

    resp = ctx.request.get(BASE + "/workshop/deck?download=1")
    txt = resp.text()
    record("Deck-06", resp.status == 200 and "<script src=" not in txt and '<link rel="stylesheet"' not in txt and "http://" not in txt)

    # Zoom: setup and share pages at 400 percent equivalent (320 CSS pixels wide)
    small = browser.new_context(viewport={"width": 320, "height": 640}, bypass_csp=True)
    sp = small.new_page()
    sp.goto(BASE + "/ahg")
    if "/consent" in sp.url:
        sp.check("#consent-agree-checkbox"); sp.click("#consent-continue-btn"); sp.wait_for_load_state("networkidle")
    overflow = {}
    for path in ("/ahg", "/workshop/ahg-2026/share"):
        sp.goto(BASE + path)
        overflow[path] = sp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    record("A11y-02", all(v <= 1 for v in overflow.values()), f"horizontal overflow px at 320 wide: {overflow}")
    small.close()

    # Keyboard: every interactive element on the share page reachable by Tab
    page.goto(share)
    seen = []
    for _ in range(60):
        page.keyboard.press("Tab")
        el = page.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.tagName)")
        seen.append(el)
    need = {"agent-file", "agent-text", "agent-name"}
    record("A11y-01-share", need <= set(seen) and "BUTTON" in seen, f"reached {sorted(set(s for s in seen if s))[:12]}")
    browser.close()


# Load-01: 40 kit downloads at once
def fetch(_):
    with urllib.request.urlopen(BASE + "/workshop/ahg-2026/kit.zip", timeout=60) as r:
        return r.status


with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
    codes = list(pool.map(fetch, range(40)))
record("Load-01", all(c == 200 for c in codes), f"{codes.count(200)} of 40 returned 200")



# Reflow sweep: no sideways scrolling at 320px, no axe violations at 1280px
PAGES = ["/", "/privacy", "/workshop/", "/ahg", "/workshop/ahg-2026/share",
         "/ahg/site", "/ahg/kit", "/ahg/kit/step-cards/4-ground-it.md",
         "/ahg/kit/office-team/word-documents/SKILL.md", "/ahg/kit/README.md",
         "/ahg/kit/ahg-2026.code-profile", "/ahg/kit/examples/maria-alternate-format-planner.md",
         "/workshop/deck", "/audit/", "/convert/"]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for width in (320, 1280):
        c = b.new_context(viewport={"width": width, "height": 800}, bypass_csp=True)
        pg = c.new_page()
        pg.goto(BASE + "/audit/")
        if "/consent" in pg.url:
            pg.check("#consent-agree-checkbox"); pg.click("#consent-continue-btn"); pg.wait_for_load_state("networkidle")
        for path in PAGES:
            resp = pg.goto(BASE + path)
            over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            line = f"{width:5} {path:28} status={resp.status} overflow={over}"
            if width == 1280:
                pg.add_script_tag(content=AXE)
                v = pg.evaluate("async () => (await axe.run(document, {resultTypes:['violations']})).violations.map(x => x.id + ':' + x.nodes.length)")
                line += f" axe={v}"
            print(line)
            ok = over <= 1 and (width != 1280 or not v)
            results[f"Reflow {width} {path}"] = ("Pass" if ok else "Fail", line)
        c.close()
    b.close()

failed = [k for k, (status, _) in results.items() if status != "Pass"]
print(f"{len(results) - len(failed)} of {len(results)} checks pass")
sys.exit(1 if failed else 0)
