#!/usr/bin/env python3
"""Smoke test for the Studio, focused on the supplier comparison screen (#compare).

1. Builds the Studio with the fixture of the deep AliExpress pass (studio/tests/fixtures/deep-2026-10/) into a
   temporary folder (studio/dist is not touched), serves it locally and opens it in Chromium.
2. At 400px and 1280px, light and dark: every screen renders without a JavaScript error; the comparison screen shows
   the summary, the slot tables and the fixture's winners; the filters work and keep focus; there is no horizontal
   scroll at 400px; and axe-core finds no WCAG 2.0/2.1 A or AA violation on the screen.
3. With --shots: builds the real data into studio/dist and saves studio/screens/compare-400.png and compare-1280.png.

Usage:  python3 studio/tests/smoke_compare.py [--shots] [--keep]
Needs:  Python Playwright and Chromium (PW_CHROMIUM, default /opt/pw-browsers/chromium); axe-core from
        site/node_modules/axe-core (the accessibility check is skipped, with a note, when it is missing).
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import functools
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / "studio"
FIXTURE = STUDIO / "tests" / "fixtures" / "deep-2026-10"
AXE = ROOT / "site" / "node_modules" / "axe-core" / "axe.min.js"
CHROMIUM = os.environ.get("PW_CHROMIUM", "/opt/pw-browsers/chromium")
SCREENS = ["overview", "todo", "decisions", "rooms", "products", "profit", "compare", "suppliers", "budget", "quality", "log"]
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(("  ok    " if ok else "  FAIL  ") + what, flush=True)
    if not ok:
        failures.append(what)


def build(dist: Path | None, deep: Path | None) -> None:
    cmd = [sys.executable, str(STUDIO / "build.py"), "--offline"]
    if deep:
        cmd += ["--deep-dir", str(deep)]
    if dist:
        cmd += ["--dist", str(dist)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print("\n".join("    " + l for l in r.stdout.splitlines() if "comparison" in l or "dist:" in l))
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"build failed ({r.returncode})")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(folder: Path):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(folder)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


def open_page(browser, base, width, scheme, block_net=True, state=None):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, locale="he-IL")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "Failed to load resource" not in m.text else None)
    if block_net:  # fonts and marked come from CDNs; the page has fallbacks
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    page.add_init_script("try{localStorage.clear()}catch(e){}" + (f"localStorage.setItem('studio.cmp', {state!r});" if state else ""))
    page.goto(base + "#compare")
    page.wait_for_selector("#screen-compare:not([hidden]) .cmp-table", timeout=15000)
    return ctx, page, errors


def axe(page, label):
    if not AXE.exists():
        print(f"  skip  axe ({label}): {AXE.relative_to(ROOT)} not found")
        return
    page.add_script_tag(path=str(AXE))
    res = page.evaluate("""(tags) => axe.run(document.querySelector('#screen-compare'), {runOnly: {type: 'tag', values: tags}})
        .then(r => r.violations.map(v => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0].target.join(' ')} — ${v.help}`))""", AXE_TAGS)
    check(not res, f"axe {label}: no violations" + ("" if not res else "\n        " + "\n        ".join(res[:8])))


def winner_title(page, slot_key):
    sid = "cmp-" + slot_key.replace("/", "--")
    loc = page.locator(f"#{sid} tr.is-win .cand-title")
    return loc.first.inner_text() if loc.count() else None


def fixture_checks(browser, base):
    for width in (400, 1280):
        for scheme in ("light", "dark"):
            label = f"{width}px {scheme}"
            print(f"- fixture, {label}")
            ctx, page, errors = open_page(browser, base, width, scheme)
            # summary and slot tables (living room, Nordic by default)
            check(page.locator("#h-cmp-sum").inner_text().startswith("מי מנצח"), f"{label}: summary heading")
            check(page.locator("#cmp-body .tile").count() >= 3, f"{label}: summary tiles")
            check(page.locator("#cmp-body .cmp-slot").count() >= 5, f"{label}: slot tables rendered")
            check((winner_title(page, "living-room/cushions") or "").startswith("FIXTURE Washed linen"), f"{label}: cushions winner is the fixture AliExpress item (more profit per unit)")
            check((winner_title(page, "living-room/vase") or "").startswith("FIXTURE Matte stoneware"), f"{label}: vase winner is the fixture AliExpress item")
            check(page.locator("#cmp-body .db-line").first.inner_text().find("רשומות") >= 0, f"{label}: deep-pass source line")
            check("לא שויכו" in page.locator("#cmp-body").inner_text(), f"{label}: unmatched record reported")
            sw = page.evaluate("document.documentElement.scrollWidth")
            check(sw <= width + 1, f"{label}: no horizontal scroll (scrollWidth {sw})")
            if width == 400:
                check(page.locator("#living-room-cushions, #cmp-living-room--cushions .cmp-narrow").first.is_visible(), f"{label}: narrow summary line visible")
                check(not page.locator("#cmp-living-room--cushions th.w").first.is_visible(), f"{label}: wide-only columns hidden")
            axe(page, f"{label} nordic")
            # supplier filter keeps focus and shows AliExpress rows only
            page.select_option("#cf-sup", "aliexpress")
            check(page.evaluate("document.activeElement && document.activeElement.id") == "cf-sup", f"{label}: focus stays on the supplier filter")
            sups = page.eval_on_selector_all("#cmp-body .cmp-table tbody tr", "rs => rs.map(r => r.dataset.sup)")
            check(bool(sups) and all(s == "aliexpress" for s in sups), f"{label}: supplier filter shows AliExpress only ({len(sups)} rows)")
            page.select_option("#cf-sup", "")
            # only profitable
            page.check("#cf-profit")
            ms = page.eval_on_selector_all("#cmp-body .cmp-table tbody tr", "rs => rs.map(r => r.dataset.margin == null ? null : +r.dataset.margin)")
            check(bool(ms) and all(m is not None and m >= 0.35 - 1e-9 for m in ms), f"{label}: 'only profitable' shows margins of 35% and up ({len(ms)} rows)")
            page.uncheck("#cf-profit")
            # the warm-modern record rejects the vase: hidden unless 'include rejected'
            page.select_option("#cf-style", "warm-modern")
            check(page.locator("#cmp-living-room--vase .cand-title", has_text="FIXTURE Matte stoneware").count() == 0, f"{label}: rejected for warm-modern is hidden")
            page.check("#cf-rej")
            check(page.locator("#cmp-living-room--vase tr.is-rej .cand-title", has_text="FIXTURE Matte stoneware").count() == 1, f"{label}: 'include rejected' shows it, marked rejected")
            page.uncheck("#cf-rej")
            # japandi: the fixture rug; boho: the fixture cushion
            page.select_option("#cf-style", "japandi")
            check((winner_title(page, "living-room/rug") or "").startswith("FIXTURE Flat-weave jute"), f"{label}: japandi rug winner")
            page.select_option("#cf-style", "boho")
            check(page.locator("#cmp-living-room--cushions .cand-title", has_text="FIXTURE Washed linen").count() == 1, f"{label}: boho shows the fixture cushion")
            # all styles: the matrix, then a click on a style row switches to it
            page.select_option("#cf-style", "all")
            check(page.locator("#cmp-body .cmp-matrix tbody tr").count() == 6, f"{label}: all styles matrix has six styles")
            check(page.locator("#cmp-living-room--cushions .cmp-wins li").count() == 6, f"{label}: winners by style line")
            page.click("[data-cmp-style='nordic']")
            check(page.input_value("#cf-style") == "nordic", f"{label}: matrix row switches the style")
            # kids room (records filed as kids-boy) and the whole house
            page.select_option("#cf-room", "kids")
            check(page.locator("#cmp-kids--toy-cars .cand-title", has_text="FIXTURE Wooden toy cars").count() == 1, f"{label}: kids-boy record lands in the kids room")
            page.select_option("#cf-room", "")
            check(page.locator("#cmp-body .cmp-room").count() >= 8, f"{label}: whole house renders every room")
            # jump from the summary list to a slot moves focus to its heading
            page.select_option("#cf-room", "living-room")
            page.locator("#cmp-body .tile details").first.locator("summary").click()
            btn = page.locator("#cmp-body .tile details [data-cmp-jump]").first
            key = btn.get_attribute("data-cmp-jump")
            btn.click()
            check(page.evaluate("document.activeElement && (document.activeElement.id || '')") in ("cmp-" + key.replace("/", "--") + "-h", "cmp-" + key.replace("/", "--")), f"{label}: summary link focuses the slot ({key})")
            # a card opens the product drawer
            page.locator("#cmp-body .cmp-table button[data-product]").first.click()
            check(page.locator("#drawer[open]").count() == 1, f"{label}: a card opens the product drawer")
            page.keyboard.press("Escape")
            check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()


def screens_check(browser, base):
    print("- every screen renders (1280px light)")
    ctx, page, errors = open_page(browser, base, 1280, "light")
    for s in SCREENS:
        page.goto(base + "#" + s)
        page.wait_for_selector(f"#screen-{s}:not([hidden])", timeout=10000)
        page.wait_for_timeout(120)
        check(page.locator(f"#h-{s}").is_visible() and not page.locator(f"#screen-{s} .toast-err").count(), f"screen {s}")
    check(not errors, "no JavaScript errors on any screen" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()


def shots(browser):
    print("- screenshots from the real data (studio/dist)")
    build(None, None)
    srv, base = serve(STUDIO / "dist")
    out = STUDIO / "screens"
    out.mkdir(exist_ok=True)
    try:
        for width, max_h in ((400, 2600), (1280, 2200)):
            ctx, page, errors = open_page(browser, base, width, "light", block_net=False)
            page.wait_for_timeout(600)  # web fonts
            h = page.evaluate("document.documentElement.scrollHeight")
            p = out / f"compare-{width}.png"
            page.screenshot(path=str(p), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": min(h, max_h)})
            print(f"    {p.relative_to(ROOT)} ({width}×{min(h, max_h)} of {h})")
            check(not errors, f"real data {width}px: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()
    finally:
        srv.shutdown()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="studio-smoke-"))
    dist = tmp / "dist"
    print("- build with the fixture of the deep AliExpress pass")
    build(dist, FIXTURE)
    srv, base = serve(dist)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None)
            fixture_checks(browser, base)
            screens_check(browser, base)
            if "--shots" in sys.argv:
                shots(browser)
            browser.close()
    finally:
        srv.shutdown()
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {dist}")
    print(f"\n{'FAILED' if failures else 'PASSED'}: {len(failures)} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
