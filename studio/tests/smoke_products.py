#!/usr/bin/env python3
"""Smoke test for the Studio's products, product drawer and profit screens (2026-10-11): prices, shipping, sell quantity.

1. Python checks on studio/build.py (no browser):
   - sell quantity: the room SKU's own label decides ("1 PC" = per piece, "2PC" / "pair" = already the pair), so a pair
     is never sold twice; the three AliExpress curtain cards are one panel each and sell as a pair (2).
   - market categories priced per pair ("וילונות בד, זוג") get pieces 2; "זוגי" (double size) does not.
   - economics from the fixture folder (studio/tests/fixtures/economics): CJ no_route, Zendrop and AliExpress freight files,
     the quote for 4 pieces of a set, the pricing team's starting price (retail_src, il_value with https links only,
     customer_total_ils, price_note, flag, slot_alternative_ok), and the storefront fees from site/shared economics.ts.
2. Browser, the Studio built with the fixture economics (a mock db stands in for the published page's db):
   - "CJ לא שולח לישראל (נבדק 11.10)" instead of "חסר משלוח", also with the under-20-days method;
   - Zendrop / AliExpress labels; an AliExpress card without data stays "חסר משלוח";
   - starting price: "מחיר התחלתי" chip, flag and margin from it, the basis in the drawer ("שווי בישראל", comparables,
     customer total with ₪29 shipping under ₪299, free shipping from ₪299);
   - floor chips (VR1, 40%): "חריג: אין חלופה בעמדה" (no alternative) and "מתחת לרף 40%" (an alternative exists);
   - default target 40%;
   - quick price edit on a card and inline edit in the profit table write product_edits/<id> (fields.economics.retail_ils)
     and the chip goes away; a pair of curtains gets the pair's market price (₪179), not twice it;
   - slot filter "בלי עמדה", shared slots on pool cards, design-first order in a slot;
   - 390px and 1280px: no horizontal scroll, axe-core finds no WCAG A/AA violation in the cards and the drawer, no JS errors.
3. Real data (built offline into a temp folder): no CJ card shows "חסר משלוח" while it has a cost; the counts are printed.
4. --shots: screenshots into assets/qa/studio-2026-10-11/ (products, drawer, profit at 1280 and 390). The real data is used;
   when data/economics/products.json does not exist yet, the fixture pricing file is laid over a copy of data/economics
   (temp folder; studio/dist is never built with fixture prices).

Usage:  python3 studio/tests/smoke_products.py [--shots] [--keep]
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import functools
import http.server
import importlib.util
import json
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
FIX_ECON = STUDIO / "tests" / "fixtures" / "economics"
AXE = ROOT / "site" / "node_modules" / "axe-core" / "axe.min.js"
CHROMIUM = os.environ.get("PW_CHROMIUM", "/opt/pw-browsers/chromium")
SHOTS = ROOT / "assets" / "qa" / "studio-2026-10-11"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

WALL_HOOKS = "wall-hooks-cj-raw-wood-cylinder-peg-set-of-4"     # CJ, quote for 4 pieces, starting price ₪99
NO_ROUTE = "paper-towel-holder-cj-beech-upright-31"              # CJ, no shipping method to Israel
NO_FAST = "wall-hooks-cj-light-wood-rail-5-brass-pegs-58"         # CJ, only a 9-23 day option; ₪49 = loses money
TEA_TOWEL = "tea-towel-zendrop-cotton-linen-washed-60x45"         # Zendrop, ₪39, under the floor, no alternative, add-on only
CURTAIN_PAIR = "curtains-aliexpress-cotton-linen-curtain-look-902882"  # AliExpress, one panel, sold as a pair, ₪349
CURTAIN_2 = "curtains-aliexpress-cotton-linen-texture-translucent"     # AliExpress, one panel, no price (pair band)
CURTAIN_CJ = "curtains-cj-japanese-linen-half-shade"                   # CJ, price set in the studio, under the floor
AE_NO_DATA = "floor-vase-aliexpress-capiron-zen-ceramic"               # AliExpress, no freight data

failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(("  ok    " if ok else "  FAIL  ") + what, flush=True)
    if not ok:
        failures.append(what)


def load_build():
    spec = importlib.util.spec_from_file_location("studio_build_test", STUDIO / "build.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --------------------------------------------------------------------------- 1. python checks

def python_checks():
    print("- build.py: sell quantity, market pieces, economics, storefront")
    B = load_build()
    slots = {"r/pair": {"key": "r/pair", "set_of": 2}, "r/six": {"key": "r/six", "set_of": 6}, "r/one": {"key": "r/one"},
             "r/fam": {"key": "r/fam", "set_of": 2}}

    def card(label, notes="", slot="r/pair", shared=()):
        return {"name": "FIXTURE curtain", "notes": notes, "_slot_key": slot, "_shared_in": list(shared),
                "options": {"default_sku": "s1", "axes": [{"id": "size", "values": [{"id": "v", "label_src": label}]}],
                            "skus": [{"id": "s1", "values": {"size": "v"}}]}}

    q = B.sell_qty_default(card("1 PC W100cmxH275cm", notes="price per piece"), slots)
    check(q["qty"] == 2 and q["sure"], f"one-panel SKU + 'per piece' in a pair slot sells 2 ({q['qty']}, {q['reason']})")
    q = B.sell_qty_default(card("1 PC W100cmxH275cm"), slots)
    check(q["qty"] == 1 and not q["sure"] and "יחידה אחת" in (q["reason"] or ""),
          f"a one-panel SKU label alone never raises the quantity (1, not sure: {q['reason']})")
    q = B.sell_qty_default(card("2PC W225cmxH250cm", notes="price is per piece"), slots)
    check(q["qty"] == 1 and q["sure"], f"a SKU that is already the pair is never doubled, even when the notes say 'per piece' ({q['qty']})")
    q = B.sell_qty_default(card("Pair (2 panels)"), slots)
    check(q["qty"] == 1, f"'pair' in the SKU label = the pair ({q['qty']})")
    q = B.sell_qty_default(card("2pcs", slot="r/six"), slots)
    check(q["qty"] == 1 and not q["sure"], f"a 2-piece SKU in a set-of-6 slot is not multiplied by guess (qty {q['qty']}, not sure)")
    q = B.sell_qty_default(card("1PC (price is per piece)", notes="price per piece", slot="r/one", shared=["r/fam"]), slots)
    check(q["qty"] == 2 and "המשותפת" in (q["reason"] or ""), f"per piece + the shared family slot's pair = 2, and the reason says so ({q['reason']})")
    q = B.sell_qty_default({"name": "x", "notes": "price per piece", "_slot_key": "r/pair", "_shared_in": []}, slots)
    check(q["qty"] == 2 and q["sure"], "without options the notes rule still works (per piece + pair slot = 2)")
    q = B.sell_qty_default({"name": "x", "notes": "", "_slot_key": "r/pair", "_shared_in": []}, slots)
    check(q["qty"] == 1 and not q["sure"], "without options and without a hint: 1, not sure")

    # the three AliExpress curtain cards of the repo
    plan = B.read_json(ROOT / "docs" / "house-plan.json")
    order, rooms = B.load_rooms(plan)
    sl = B.load_slots(order, rooms)
    products = B.load_products(set(order))
    B.mark_duplicates(products)
    B.attach_candidates(sl, products)
    sbk = {s["key"]: s for rows in sl.values() for s in rows}
    for pid in ("curtains-aliexpress-cotton-linen-curtain-look-902882", "curtains-aliexpress-cotton-linen-texture-translucent-091154",
                "curtains-aliexpress-cotton-linen-texture-translucent"):
        p = next((x for x in products if x["id"] == pid and x.get("_slot_key") == "living-room/curtains"), None)
        if p is None:
            print(f"  skip  {pid}: not in the living room any more")
            continue
        q = B.sell_qty_default(p, sbk)
        check(q["qty"] == 2 and q.get("sku_pieces") == 1, f"{pid}: the room SKU is one panel, sold as a pair (qty {q['qty']}, SKU pieces {q.get('sku_pieces')})")

    m = B.load_market(ROOT / "data" / "economics")
    cats = (m or {}).get("categories") or {}
    check(cats.get("curtains", {}).get("pieces") == 2, "market: curtains are priced per pair (pieces 2)")
    check(cats.get("pillowcases", {}).get("pieces") == 2, "market: pillowcases are priced per pair (pieces 2)")
    check(cats.get("bedding-set", {}).get("pieces") == 1, "market: 'זוגי' (double size) is not a pair (pieces 1)")

    ids = [WALL_HOOKS, NO_ROUTE, NO_FAST, TEA_TOWEL, CURTAIN_PAIR, CURTAIN_2, CURTAIN_CJ, AE_NO_DATA]
    cards = [x for x in products if x["id"] in ids]
    eco = B.load_economics(FIX_ECON, cards)
    E = eco["products"]
    check(E.get(NO_ROUTE, {}).get("freight", {}).get("status") == "no_route", "no_route reaches data.json")
    check(E.get(TEA_TOWEL, {}).get("freight", {}).get("src") == "zendrop", "Zendrop freight file is read (src zendrop)")
    check(E.get(CURTAIN_PAIR, {}).get("freight", {}).get("src") == "aliexpress", "AliExpress freight file is read (src aliexpress)")
    check(E.get(WALL_HOOKS, {}).get("freight", {}).get("quoted_qty") == 4, "the quote for the 4 pieces of the set is kept (quoted_qty 4)")
    check(E.get(NO_FAST, {}).get("freight", {}).get("under20") is None, "no option within 20 days: under20 empty")
    check("freight" not in E.get(AE_NO_DATA, {}), "an AliExpress card without data gets no invented shipping")
    w = E.get(WALL_HOOKS, {})
    check(w.get("retail_ils") == 99 and w.get("retail_src") == "initial-2026-10-11", "starting price and retail_src pass through")
    comps = (w.get("il_value") or {}).get("comps") or []
    check(len(comps) == 3 and all(c["url"] is None or c["url"].startswith("https://") for c in comps) and comps[2]["url"] is None,
          "il_value comparables pass through, http links dropped")
    check(w.get("customer_total_ils") == 128 and bool(w.get("price_note")), "customer_total_ils and price_note pass through")
    check(E.get(TEA_TOWEL, {}).get("price_flag") == "below-floor" and E.get(TEA_TOWEL, {}).get("slot_alternative_ok") is False,
          "flag and slot_alternative_ok pass through")
    check(E.get(TEA_TOWEL, {}).get("addon_only") is True and E.get(NO_FAST, {}).get("action_he", "").startswith("FIXTURE"), "addon_only and action_he pass through")
    sf = eco.get("storefront") or {}
    check(sf.get("shipping_fee_economy_ils") == 29 and sf.get("free_shipping_threshold_ils") == 299,
          f"storefront fees from {sf.get('src')}: ₪{sf.get('shipping_fee_economy_ils')} under ₪{sf.get('free_shipping_threshold_ils')}")


# --------------------------------------------------------------------------- browser

def build(dist: Path, eco: Path | None) -> None:
    cmd = [sys.executable, str(STUDIO / "build.py"), "--offline", "--dist", str(dist)]
    if eco:
        cmd += ["--economics-dir", str(eco)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print("\n".join("    " + l for l in r.stdout.splitlines() if "economics" in l or "dist:" in l or "sell quantity" in l))
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


# an in-memory stand-in for the published page's db (window.claude.use('db') / use('user')); window.__db holds the docs
MOCK_DB = """
window.__db = Object.assign({product_edits:{}, product_new:{}, settings:{}, decisions:{}}, %s);
(() => {
  const subs = {};
  const clone = v => JSON.parse(JSON.stringify(v));
  const snap = n => ({docs: Object.entries(window.__db[n] || {}).map(([id, v]) => ({id, exists: true, data: () => clone(v)}))});
  const notify = n => (subs[n] || []).forEach(cb => setTimeout(() => cb(snap(n)), 0));
  const coll = n => ({
    onSnapshot(cb){ (subs[n] = subs[n] || []).push(cb); setTimeout(() => cb(snap(n)), 0); return () => {}; },
    doc(id){ return {
      async set(v){ (window.__db[n] = window.__db[n] || {})[id] = clone(v); notify(n); },
      async update(v){ window.__db[n][id] = Object.assign(window.__db[n][id] || {}, clone(v)); notify(n); },
      async delete(){ delete window.__db[n][id]; notify(n); } }; },
    async add(v){ const id = 'n' + Math.random().toString(36).slice(2, 8); (window.__db[n] = window.__db[n] || {})[id] = clone(v); notify(n); return {id}; }
  });
  const db = {collection: coll};
  const user = {async id(){ return 'smoke-user'; }, async can(){ return true; }};
  window.claude = {async use(name){ return name === 'db' ? db : name === 'user' ? user : null; }};
})();
"""


def open_page(browser, base, width, scheme="light", screen="products", ready=".pcard", db=True, seed=None, block_net=True, height=900):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme, locale="he-IL")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "Failed to load resource" not in m.text else None)
    if block_net:
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    page.add_init_script("try{localStorage.clear()}catch(e){}" + (MOCK_DB % json.dumps(seed or {}) if db else ""))
    page.goto(base + "#" + screen)
    page.wait_for_selector(f"#screen-{screen}:not([hidden]) {ready}", timeout=15000)
    page.wait_for_timeout(150)
    return ctx, page, errors


def axe(page, label, root):
    if not AXE.exists():
        print(f"  skip  axe ({label}): {AXE.relative_to(ROOT)} not found")
        return
    if not page.evaluate("typeof axe !== 'undefined'"):
        page.add_script_tag(path=str(AXE))
    res = page.evaluate("""([tags, root]) => axe.run(document.querySelector(root), {runOnly: {type: 'tag', values: tags}})
        .then(r => r.violations.map(v => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0].target.join(' ')} — ${v.help}`))""", [AXE_TAGS, root])
    check(not res, f"axe {label}: no violations" + ("" if not res else "\n        " + "\n        ".join(res[:8])))


WIDE_JS = """() => [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > innerWidth + 1 || r.left < -1) && getComputedStyle(e).position !== 'fixed'; })
    .filter(e => !e.closest('.pcard-w') || e.matches('.pcard-w')).slice(0, 4)
    .map(e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}.${String(e.className).split(' ').join('.')} ${Math.round(e.getBoundingClientRect().left)}..${Math.round(e.getBoundingClientRect().right)}`)"""


def no_hscroll(page, width, what):
    sw = page.evaluate("document.documentElement.scrollWidth")
    check(sw <= width + 1, f"{what}: no horizontal scroll ({sw})" + ("" if sw <= width + 1 else " " + "; ".join(page.evaluate(WIDE_JS))))


def card(page, pid):
    return page.locator(f".pcard-w[data-pid='{pid}']").first


def open_drawer(page, pid):
    card(page, pid).locator("button.pcard").click()
    page.wait_for_selector("#drawer[open] #h-econ")
    page.wait_for_function("() => document.activeElement && document.activeElement.matches('#drawer [data-close]')", timeout=5000)


def close_drawer(page):
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.getElementById('drawer').open", timeout=5000)


def fixture_checks(browser, base):
    for width in (390, 1280):
        label = f"{width}px"
        print(f"- fixture economics, products screen, {label}")
        ctx, page, errors = open_page(browser, base, width)
        page.wait_for_selector(".pquick [data-qprice]")
        # shipping
        c = card(page, NO_ROUTE)
        ft = c.locator(".flag").inner_text()
        check("CJ לא שולח לישראל (נבדק 11.10)" in ft and "חסר משלוח" not in ft and c.get_attribute("data-miss").startswith("no_route"),
              f"{label}: no_route card says 'CJ לא שולח לישראל (נבדק 11.10)' ({ft})")
        check(card(page, TEA_TOWEL).get_attribute("data-ship-src") == "zendrop" and "$6.73" in card(page, TEA_TOWEL).locator(".prow").first.inner_text(),
              f"{label}: Zendrop card shows its shipping in the price row")
        check(card(page, CURTAIN_PAIR).get_attribute("data-ship-src") == "aliexpress", f"{label}: AliExpress card has shipping from the AliExpress file")
        ae = card(page, AE_NO_DATA)
        check("חסר משלוח" in ae.locator(".flag").inner_text() and ae.get_attribute("data-ship-src") == "", f"{label}: AliExpress card without data stays 'חסר משלוח'")
        # starting price
        w = card(page, WALL_HOOKS)
        wt = w.inner_text()
        check("₪ 99" in wt and w.locator(".chip-initial").count() == 1 and w.get_attribute("data-retail-src") == "initial",
              f"{label}: starting price ₪99 with the 'מחיר התחלתי' chip")
        check(w.get_attribute("data-flag") in ("green", "red") and "חסר" not in w.locator(".flag").inner_text(), f"{label}: flag and margin from the starting price")
        check(card(page, CURTAIN_CJ).locator(".chip-initial").count() == 0 and card(page, CURTAIN_CJ).get_attribute("data-retail-src") == "file",
              f"{label}: a price the studio set (retail_src studio) has no chip")
        # floor chips (VR1)
        check(card(page, TEA_TOWEL).locator(".chip-exception").inner_text() == "חריג: אין חלופה בעמדה", f"{label}: under the floor, no alternative: amber exception chip")
        check(card(page, CURTAIN_CJ).locator(".chip-floor").inner_text() == "מתחת לרף 40%", f"{label}: under the floor, alternative exists: 'מתחת לרף 40%'")
        check(w.locator(".chip-floor, .chip-exception, .chip-loss").count() == 0, f"{label}: above the floor: no floor chip")
        # ה.13: losing money
        nf = card(page, NO_FAST)
        check(nf.locator(".chip-loss").inner_text() == "מפסיד, לא למכירה" and nf.locator(".chip-floor, .chip-exception").count() == 0,
              f"{label}: negative contribution: 'מפסיד, לא למכירה' (instead of the floor chip)")
        check(card(page, TEA_TOWEL).locator(".chip-addon").inner_text() == "רק כתוספת לסל", f"{label}: addon_only: 'רק כתוספת לסל'")
        page.select_option("#f-flag", "loss")
        lz = page.eval_on_selector_all(".pcard-w", "e => e.map(x => [x.dataset.pid, !!x.querySelector('.chip-loss')])")
        check(bool(lz) and all(x[1] for x in lz) and NO_FAST in [x[0] for x in lz], f"{label}: flag filter 'מפסיד' shows only losing products ({len(lz)})")
        page.select_option("#f-flag", "")
        page.select_option("#f-slot", "hall/wall-hooks")
        hz = page.eval_on_selector_all(".pcard-w", "e => e.map(x => !!x.querySelector('.chip-loss'))")
        check(NO_FAST in page.eval_on_selector_all(".pcard-w", "e => e.map(x => x.dataset.pid)") and hz == sorted(hz),
              f"{label}: in a slot the losing products are kept, and last ({hz})")
        page.select_option("#f-slot", "")
        # pool cards and the 'no slot' filter
        shared = page.locator(".pcard-w .pslot", has_text="משותף:")
        check(shared.count() >= 1, f"{label}: pool cards with shared slots show 'משותף: …' ({shared.count()})")
        page.focus("#f-slot")
        page.select_option("#f-slot", "__none")
        slots_txt = page.eval_on_selector_all(".pcard-w .pname + .pslot", "e => e.map(x => x.textContent)")
        check(bool(slots_txt) and all(not t.startswith("משותף:") and "·" not in t for t in slots_txt), f"{label}: 'בלי עמדה' shows only unplaced cards ({len(slots_txt)}: {slots_txt[:2]})")
        check(page.evaluate("document.activeElement && document.activeElement.id") == "f-slot", f"{label}: focus stays on the slot filter")
        page.select_option("#f-slot", "living-room/curtains")
        ids = page.eval_on_selector_all(".pcard-w", "e => e.map(x => x.dataset.pid)")
        check({CURTAIN_PAIR, CURTAIN_2, CURTAIN_CJ} <= set(ids), f"{label}: every curtain candidate is in the slot's basket, below-floor included ({len(ids)})")
        sc = page.eval_on_selector_all(".pcard-w:not(:has(.chip-loss))", "e => e.map(x => { const b = x.querySelector('.chip-design b'); return b ? +b.textContent : null; })")
        scored = [x for x in sc if x is not None]
        check(scored == sorted(scored, reverse=True) and (None not in sc or sc.index(None) >= len(scored)),
              f"{label}: in a slot, design score first, high to low ({sc[:6]})")
        page.select_option("#f-slot", "")
        sw = page.evaluate("document.documentElement.scrollWidth")
        check(sw <= width + 1, f"{label}: products: no horizontal scroll ({sw})")
        axe(page, f"{label} products grid", "#pgrid")
        # quick price edit on a card
        page.locator(f".pcard-w[data-pid='{WALL_HOOKS}'] [data-qprice]").click()
        inp = page.locator(f"#qp-{WALL_HOOKS}")
        check(inp.is_visible() and page.evaluate("document.activeElement && document.activeElement.id") == f"qp-{WALL_HOOKS}", f"{label}: quick edit opens with focus in the field")
        sw = page.evaluate("document.documentElement.scrollWidth")
        check(sw <= width + 1, f"{label}: quick edit fits the card ({sw})")
        inp.fill("109")
        inp.press("Enter")
        page.wait_for_function(f"() => {{ const d = window.__db.product_edits['{WALL_HOOKS}']; return d && d.fields && d.fields.economics && d.fields.economics.retail_ils === 109; }}", timeout=5000)
        page.wait_for_function(f"() => {{ const c = document.querySelector(\".pcard-w[data-pid='{WALL_HOOKS}']\"); return c && c.dataset.retailSrc === 'studio'; }}", timeout=5000)
        w = card(page, WALL_HOOKS)
        check("₪ 109" in w.inner_text() and w.locator(".chip-initial").count() == 0, f"{label}: saved ₪109 through product_edits; the starting-price chip is gone")
        check(page.evaluate("document.activeElement && document.activeElement.dataset.qprice") == WALL_HOOKS, f"{label}: focus returns to the card's price button")
        # drawer: starting price basis, customer total, shipping label
        open_drawer(page, TEA_TOWEL)
        dt = page.locator("#drawer-body").inner_text()
        check("Zendrop, 11.10" in dt, f"{label}: drawer shipping label 'Zendrop, 11.10'")
        check("ללקוח עם משלוח" in dt and "₪ 68" in dt, f"{label}: customer total ₪39 + ₪29 = ₪68")
        check("חריג: אין חלופה בעמדה" in dt, f"{label}: drawer shows the exception chip")
        close_drawer(page)
        open_drawer(page, CURTAIN_PAIR)
        dt = page.locator("#drawer-body").inner_text()
        check("משלוח חינם" in dt and "AliExpress, 11.10" in dt, f"{label}: ₪349: free shipping; label 'AliExpress, 11.10'")
        check("שווי בישראל" in dt and page.locator("#drawer-body .chip-initial").count() >= 1, f"{label}: drawer shows the price basis and the chip")
        close_drawer(page)
        open_drawer(page, NO_ROUTE)
        dt = page.locator("#drawer-body").inner_text()
        check("CJ לא שולח לישראל (נבדק 11.10)" in dt and "חסר משלוח" not in dt, f"{label}: drawer of the no_route card names the reason")
        close_drawer(page)
        open_drawer(page, NO_FAST)
        dt = page.locator("#drawer-body").inner_text()
        check("מפסיד, לא למכירה" in dt and "מה לעשות:" in dt and "FIXTURE: shipping is more than the price" in dt, f"{label}: drawer of a losing product shows what to do (action_he)")
        close_drawer(page)
        open_drawer(page, CURTAIN_CJ)
        dt = page.locator("#drawer-body").inner_text()
        check("מחיר מומלץ ליעד 40%" in dt and "מתחת לרף 40%" in dt, f"{label}: drawer: target 40% and the floor chip")
        page.locator("#econ-price-edit").click()
        check(page.evaluate("document.activeElement && document.activeElement.id") == "e-retail_ils", f"{label}: 'עריכת המחיר לצרכן' moves focus to the price field")
        no_hscroll(page, width, f"{label}: drawer")
        axe(page, f"{label} drawer", "#drawer")
        close_drawer(page)
        # profit: target 40%, inline price edit
        page.goto(base + "#profit")
        page.wait_for_selector("#screen-profit:not([hidden]) .ptable")
        check("יעד 40%" in page.locator("#profit-body .assume").inner_text(), f"{label}: profit: default target 40%")
        tile = page.locator("#profit-body .tile", has_text="מחיר לצרכן").inner_text()
        check("מחיר התחלתי" in tile, f"{label}: profit: price tile counts starting prices")
        pin = page.locator(f"#pi-retail-{TEA_TOWEL}")
        pin.fill("59")
        pin.press("Enter")
        page.wait_for_function(f"() => {{ const d = window.__db.product_edits['{TEA_TOWEL}']; return d && d.fields.economics && d.fields.economics.retail_ils === 59; }}", timeout=5000)
        page.wait_for_timeout(200)
        row = page.locator("#profit-body tr", has=page.locator(f"#pi-retail-{TEA_TOWEL}"))
        check(row.locator(".chip-initial").count() == 0, f"{label}: profit inline edit saves ₪59 and drops the chip")
        sw = page.evaluate("document.documentElement.scrollWidth")
        check(sw <= width + 1, f"{label}: profit: no horizontal scroll ({sw})")
        # comparison: a pair of curtains is one market price
        page.goto(base + "#compare")
        page.wait_for_selector("#screen-compare:not([hidden]) .cmp-table")
        page.select_option("#cf-room", "living-room")
        if not page.is_checked("#cf-unr"):
            page.check("#cf-unr")
        r = page.locator(f"#cmp-living-room--curtains tr[data-key='card:{CURTAIN_2}']")
        check(r.count() == 1 and r.get_attribute("data-qty") == "2" and r.get_attribute("data-retail") == "179",
              f"{label}: a pair of panels gets the pair's market price ₪179, not ₪349 ({r.get_attribute('data-retail') if r.count() else None})")
        check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
        ctx.close()

    print("- fixture economics, under-20-days shipping method (settings in the db)")
    ctx, page, errors = open_page(browser, base, 1280, seed={"settings": {"economics": {"shipping_method": "under20"}}})
    page.wait_for_function(f"() => {{ const c = document.querySelector(\".pcard-w[data-pid='{NO_FAST}']\"); return c && c.dataset.shipSrc === 'nofast'; }}", timeout=5000)
    check("משלוח מהיר" in card(page, NO_FAST).locator(".flag").inner_text(), "under20: a card with only a 9-23 day option is 'חסר משלוח מהיר'")
    ft = card(page, NO_ROUTE).locator(".flag").inner_text()
    check("CJ לא שולח לישראל" in ft and "20 יום" not in ft, f"under20: the no_route card still says 'CJ לא שולח לישראל' ({ft})")
    check(not errors, "under20: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()

    print("- without a db (local preview): read only, no quick edit")
    ctx, page, errors = open_page(browser, base, 1280, db=False)
    check(page.locator("[data-qprice]").count() == 0 and "₪ 99" in card(page, WALL_HOOKS).inner_text(), "no db: prices shown, no edit buttons")
    check(not errors, "no db: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()


def real_checks(browser, base):
    print("- real data: shipping and price state of every card")
    ctx, page, errors = open_page(browser, base, 1280, db=False)
    cards = page.eval_on_selector_all(".pcard-w", """cs => cs.map(c => ({id: c.dataset.pid, sup: c.dataset.sup, miss: c.dataset.miss,
        ship: c.dataset.shipSrc, rsrc: c.dataset.retailSrc, flag: c.querySelector('.flag').textContent,
        floor: (c.querySelector('.chip-loss, .chip-floor, .chip-exception') || {}).textContent || '',
        addon: !!c.querySelector('.chip-addon'), initial: !!c.querySelector('.chip-initial'), qmis: !!c.querySelector('.pecon .chip-warn')}))""")
    # the acceptance rule: a CJ card that has a cost and a freight entry never shows "חסר משלוח"; a card that is not in
    # freight-cj.json yet (added after the last freight run) shows "חסר משלוח: CJ עוד לא נבדק", which is its real reason
    fr = json.loads((ROOT / "data" / "economics" / "freight-cj.json").read_text(encoding="utf-8")).get("products") or {}
    cj_bad = [c["id"] for c in cards if c["sup"] == "cj" and c["id"] in fr and "shipping" in c["miss"].split(",") and "cost" not in c["miss"]]
    check(not cj_bad, f"real data: no CJ card with a cost and freight data shows 'חסר משלוח' ({len(cj_bad)}: {cj_bad[:4]})")
    unchecked = [c["id"] for c in cards if c["sup"] == "cj" and c["id"] not in fr and "shipping" in c["miss"].split(",")]
    if unchecked:
        print(f"    note: {len(unchecked)} CJ cards are not in freight-cj.json yet: {unchecked[:4]}")
    check(not any("חסר משלוח" in c["flag"] for c in cards if c["ship"] == "no_route"), "real data: no_route cards show the reason, not 'חסר משלוח'")
    from collections import Counter
    print("    cards:", len(cards), "· shipping source:", dict(Counter(c["ship"] or "none" for c in cards)))
    print("    price source:", dict(Counter(c["rsrc"] or "none" for c in cards)), "· missing:", dict(Counter(c["miss"] or "-" for c in cards)))
    print("    price chips:", dict(Counter(c["floor"] for c in cards if c["floor"])), "· add-on only:", sum(c["addon"] for c in cards),
          "· 'מחיר התחלתי' chips:", sum(c["initial"] for c in cards))
    miss_ship = [(c["sup"], c["id"]) for c in cards if "shipping" in c["miss"].split(",")]
    print("    still without shipping:", len(miss_ship), dict(Counter(s for s, _ in miss_ship)))
    check(not errors, "real data: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()
    # accessibility and layout with the real prices: products, a drawer with a starting price, profit (light 1280, dark 390)
    for width, scheme in ((1280, "light"), (390, "dark")):
        label = f"real data {width}px {scheme}"
        ctx, page, errors = open_page(browser, base, width, scheme=scheme)
        axe(page, f"{label} products", "#pgrid")
        no_hscroll(page, width, f"{label} products")
        pid = page.evaluate("() => (document.querySelector(\".pcard-w[data-retail-src='initial']\") || document.querySelector('.pcard-w')).dataset.pid")
        open_drawer(page, pid)
        axe(page, f"{label} drawer", "#drawer")
        no_hscroll(page, width, f"{label} drawer")
        close_drawer(page)
        page.goto(base + "#profit")
        page.wait_for_selector("#screen-profit:not([hidden]) .ptable")
        axe(page, f"{label} profit", "#profit-body")
        no_hscroll(page, width, f"{label} profit")
        check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
        ctx.close()


def shots(browser, tmp: Path):
    print("- screenshots (real data) into " + str(SHOTS.relative_to(ROOT)))
    eco = None
    if not (ROOT / "data" / "economics" / "products.json").exists():
        # the merged file is not there yet: merge the pricing team's data/economics/pricing/*.json into a temp copy
        # (the same fields the merged file will have); without them, the fixture's 4 test prices
        eco = tmp / "eco-shots"
        shutil.copytree(ROOT / "data" / "economics", eco)
        merged = {}
        for f in sorted((ROOT / "data" / "economics" / "pricing").glob("*.json")):
            merged.update((json.loads(f.read_text(encoding="utf-8")).get("products") or {}))
        if merged:
            (eco / "products.json").write_text(json.dumps({"version": 1, "products": merged}, ensure_ascii=False), encoding="utf-8")
            print(f"    note: data/economics/products.json does not exist yet; {len(merged)} prices merged from data/economics/pricing/*.json into a temp copy")
        else:
            shutil.copy(FIX_ECON / "products.json", eco / "products.json")
            print("    note: no pricing files yet; the fixture pricing file (4 test prices) is laid over a temp copy")
    dist = tmp / "dist-shots"
    build(dist, eco)
    srv, base = serve(dist)
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        for width in (1280, 390):
            ctx, page, errors = open_page(browser, base, width, block_net=False, height=900 if width > 400 else 844)
            page.wait_for_timeout(700)  # web fonts
            page.wait_for_selector(".pquick [data-qprice]")
            h = page.evaluate("document.documentElement.scrollHeight")
            page.screenshot(path=str(SHOTS / f"products-{width}.png"), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": min(h, 2600)})
            # a slot list: the living-room curtains, design first
            page.select_option("#f-slot", "living-room/curtains")
            page.wait_for_timeout(200)
            h = page.evaluate("document.documentElement.scrollHeight")
            page.screenshot(path=str(SHOTS / f"products-slot-{width}.png"), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": min(h, 2400)})
            page.select_option("#f-slot", "")
            # the drawer of a product with a starting price (the first one that has a basis)
            pid = page.evaluate("""() => { const c = [...document.querySelectorAll(".pcard-w[data-retail-src='initial']")];
                return (c.find(x => x.dataset.pid === '%s') || c[0] || document.querySelector('.pcard-w')).dataset.pid; }""" % WALL_HOOKS)
            open_drawer(page, pid)
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHOTS / f"drawer-{width}.png"))
            page.evaluate("document.getElementById('h-econ').scrollIntoView({block: 'start'})")
            page.wait_for_timeout(200)
            page.screenshot(path=str(SHOTS / f"drawer-price-{width}.png"))
            close_drawer(page)
            page.goto(base + "#profit")
            page.wait_for_selector("#screen-profit:not([hidden]) .ptable")
            page.wait_for_timeout(300)
            h = page.evaluate("document.documentElement.scrollHeight")
            page.screenshot(path=str(SHOTS / f"profit-{width}.png"), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": min(h, 2600)})
            check(not errors, f"shots {width}px: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()
        for p in sorted(SHOTS.glob("*.png")):
            print(f"    {p.relative_to(ROOT)}")
    finally:
        srv.shutdown()


def main() -> int:
    python_checks()
    tmp = Path(tempfile.mkdtemp(prefix="studio-products-"))
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None)
            print("- build with the fixture economics (studio/tests/fixtures/economics)")
            build(tmp / "dist-fixture", FIX_ECON)
            srv, base = serve(tmp / "dist-fixture")
            try:
                fixture_checks(browser, base)
            finally:
                srv.shutdown()
            print("- build with the real data")
            build(tmp / "dist-real", None)
            srv, base = serve(tmp / "dist-real")
            try:
                real_checks(browser, base)
            finally:
                srv.shutdown()
            if "--shots" in sys.argv:
                shots(browser, tmp)
            browser.close()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {tmp}")
    print(f"\n{'FAILED' if failures else 'PASSED'}: {len(failures)} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
