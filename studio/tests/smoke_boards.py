#!/usr/bin/env python3
"""Smoke test for the Studio's room boards screen (#boards, "לוחות חדרים", 2026-10-17).

1. Python checks (no browser):
   - scripts/boards/room_boards.py is the single source: boards() gives the 48 boards (6 styles x 8 rooms, the labels of
     the script), each board's slots in the slot file's order (no fixed furniture), statuses chosen / candidate / missing /
     on-hold, the counts and the default total; importing it does not change the working directory;
   - its CLI renderer (board()) draws exactly that data: the header line, one tile per slot, the "נבחר" / "מועמד" tags;
   - supplier, status with the supplier and margin on known cards: the Jellycat look-alike teddy is "בהמתנה" (and has no
     EN71), a CJ sconce without CE is "חסר תקן", a shade-only pendant needs the E27 set, the margin comes from the pick,
     then data/economics/products.json, then the final round, and its tone follows 40% / 25%; an Israeli supplier gets
     the outreach state of data/suppliers/directory.json; a broken card never stops the boards;
   - nothing rejected on a board (QA 2026-10-17, B3): no card whose status is "rejected", no card the designer rejected
     for that slot (designer-audit*.json through final_round_coverage.audit_for, slot-aware), no candidate the designer
     scored below 7 for the style; a candidate the designer kept is "המעצב בדק", the rest "מועמד, לא נבדק"; every pick
     left out is listed in the board's `dropped` with a known reason;
   - studio/build.py load_boards(): every card on a board is a product with a picture (a cell of a sheet in
     dist/img/s/), nothing redacted, no unknown id; a missing module leaves an empty, explained screen instead of a
     failed build. The boards are a chunk (data-boards.json) that the page loads when the screen opens.
2. Browser, the real data built offline into a temp folder (studio/dist is not touched):
   - the screen renders from the nav; the coverage map has 48 cells; all 48 boards open from the map (1280px, light) and
     from the selects (400px, dark, table view): heading, the counts line, one tile or row per slot, the tags, the
     empty tiles; no horizontal scroll at 400px; no JavaScript errors;
   - a tile opens the product drawer for its card, an alternate opens its own card, Escape returns focus to the tile;
   - the margins agree with the profitability screen (QA 2026-10-17, M4): a pick with a live margin shows the margin
     #profit shows for that card, its tone follows 40% / 25%; the others show the board's margin;
   - the official coverage (coverage.json) is on the screen, and the map says it is another measure;
   - the table view: the columns, the chips and the margins of the known cards;
   - the last style, room and view are remembered (localStorage), and the page still works when localStorage throws;
   - axe-core finds no WCAG 2.0/2.1 A or AA violation in the screen (tiles and table, light and dark).
   - on a phone the table view is a stacked list with the same items and chips.
3. --shots: builds the real data into studio/dist and saves studio/screens/boards-{1280,400}.png (light),
   boards-{1280,400}-dark.png and boards-table-{1280,400}.png.

Usage:  python3 studio/tests/smoke_boards.py [--shots] [--keep]
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_products as T  # noqa: E402  (shared helpers: build, serve, axe, no_hscroll)

ROOT = T.ROOT
STUDIO = T.STUDIO
SCREENS = STUDIO / "screens"
BOARDS_PY = ROOT / "scripts" / "boards" / "room_boards.py"
check = T.check

TEDDY = "soft-toy-aliexpress-30cm-lovely-curly-teddy-548628"   # ART DIRECTOR on hold (replica rule), no EN71
SCONCE = "accent-sconces-cj-travertine-block-updown-8x16"       # CJ, no CE declared, the designer's 43.7%
CUSHION = "cushions-cj-boucle-teddy"                            # a candidate in the Nordic living room: margin from economics


def load_rb():
    spec = importlib.util.spec_from_file_location("room_boards_test", BOARDS_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def find(B, style, room):
    return next(b for b in B["boards"] if b["style"] == style and b["room"] == room)


def picks_of(B, cid):
    """[(board, slot, index, pick)] wherever the card is on a board."""
    return [(b, s, i, p) for b in B["boards"] for s in b["slots"] for i, p in enumerate(s.get("picks") or []) if p["card_id"] == cid]


def shade_pick(B):
    return next(((b, s, i, p) for b in B["boards"] for s in b["slots"] for i, p in enumerate(s.get("picks") or [])
                 if any(x["code"] == "shade-set" for x in p["supplier_status"])), None)


def sub_line(b):
    c = b["counts"]
    return (f"{c['slots']} עמדות: {c['chosen']} עם בחירת מעצב, {c['candidate']} עם מועמד מהליקוט האחרון, {c['missing']} חסרות."
            f" סכום ברירות המחדל: ₪{b['total']:,.0f}")


# --------------------------------------------------------------------------- 1. python checks

def python_checks():
    print("- scripts/boards/room_boards.py: the boards as data")
    cwd = os.getcwd()
    R = load_rb()
    check(os.getcwd() == cwd, "importing room_boards does not change the working directory")
    B = R.boards()
    check(len(B["boards"]) == 48 and [x["id"] for x in B["styles"]] == R.STYLES and [x["id"] for x in B["rooms"]] == R.ROOMS,
          f"48 boards in STYLES x ROOMS order ({len(B['boards'])})")
    check([x["he"] for x in B["styles"]] == [R.ST_HE[s] for s in R.STYLES] and [x["he"] for x in B["rooms"]] == [R.ROOM_HE[r] for r in R.ROOMS],
          "the Hebrew labels are the script's")
    bad_order, bad_counts, bad_status, bad_total = [], [], [], []
    for b in B["boards"]:
        want = [s["id"] for s in json.loads((ROOT / "data" / "slots" / f"{b['room']}.json").read_text(encoding="utf-8"))["slots"]
                if s.get("kind") != "fixed-product"]
        if [s["id"] for s in b["slots"]] != want:
            bad_order.append(f"{b['style']}/{b['room']}")
        n = {k: sum(1 for s in b["slots"] if s["status"] == k) for k in ("chosen", "candidate", "missing", "on-hold")}
        c = b["counts"]
        if (c["slots"], c["chosen"], c["candidate"], c["missing"], c["on_hold"]) != (len(b["slots"]), n["chosen"], n["candidate"], n["missing"] + n["on-hold"], n["on-hold"]):
            bad_counts.append(f"{b['style']}/{b['room']}")
        for s in b["slots"]:
            ok = s["status"] in ("chosen", "candidate", "missing", "on-hold") and (bool(s.get("picks")) == (s["status"] in ("chosen", "candidate")))
            if s.get("picks"):
                ok = ok and s["main_role"] == s["picks"][0]["role"] and all(p.get("card_id") for p in s["picks"])
                ok = ok and (s["status"] != "candidate" or all(p["role"] == "candidate" for p in s["picks"]))
            if not ok:
                bad_status.append(f"{b['style']}/{b['room']}/{s['id']}")
        if b["total"] != sum(s["picks"][0]["price"] or 0 for s in b["slots"] if s.get("picks")):
            bad_total.append(f"{b['style']}/{b['room']}")
    check(not bad_order, f"every board lists the slots in the slot file's order, without fixed furniture {bad_order[:3]}")
    check(not bad_counts, f"counts agree with the slots (missing includes on-hold) {bad_counts[:3]}")
    check(not bad_status, f"status, picks and main role agree in every slot {bad_status[:3]}")
    check(not bad_total, f"the default total is the sum of the main picks' prices {bad_total[:3]}")
    nl = find(B, "nordic", "living-room")
    check(nl["counts"]["slots"] == len(nl["slots"]) and any(s["status"] == "on-hold" for s in nl["slots"]),
          f"Nordic living room: {sub_line(nl)} (an on-hold slot among the missing)")

    print("- the CLI renderer draws the same data")
    R.image = lambda cid, cat, cache: f"/img/{cid}.webp"  # no downloads in the test
    ctx = R.Context()
    bad = []
    for b in B["boards"]:
        doc, a, c, n = R.board(b["style"], b["room"], ctx.cat, "/nowhere", ctx)
        ok = (a, c, n) == (b["counts"]["chosen"], b["counts"]["candidate"], b["counts"]["slots"])
        ok = ok and f"<h1>{R.ROOM_HE[b['room']]} · {R.ST_HE[b['style']]}</h1>" in doc and sub_line(b) in doc
        ok = ok and doc.count("<div class='t") == n and doc.count("<span class='tag'>נבחר</span>") == a and doc.count("<span class='tag c'>מועמד</span>") == c
        ok = ok and doc.count("<b>בהמתנה</b>") == b["counts"]["on_hold"]
        if not ok:
            bad.append(f"{b['style']}/{b['room']}")
    check(not bad, f"board() html = boards() data for all 48 (header, counts, tiles, tags) {bad[:3]}")

    print("- supplier, status with the supplier, margin")
    labels = B["status_labels"]
    ted = picks_of(B, TEDDY)
    if ted:
        b, s, i, p = ted[0]
        codes = [x["code"] for x in p["supplier_status"]]
        check(codes[0] == "on-hold" and "Jellycat" in (p["supplier_status"][0].get("why") or "") and labels["on-hold"]["he"] == "בהמתנה",
              f"the teddy is 'בהמתנה' first, with the art director's note ({b['style']}/{b['room']}/{s['id']}: {codes})")
        check("no-standard" in codes and ("unreviewed" in codes or "reviewed" in codes),
              f"the teddy: no EN71 ('חסר תקן'), a candidate with its review state ({codes})")
        check(p["supplier"] == {"key": "aliexpress", "name": "AliExpress"} and p["margin"]["src"] == "leads" and p["margin"]["tone"] == "good",
              f"the teddy: AliExpress, margin from the final round's repricing ({p['margin']})")
    else:
        print(f"  skip  {TEDDY}: not on a board any more")
    sc = [x for x in picks_of(B, SCONCE) if x[0]["style"] == "nordic"]
    if sc:
        p = sc[0][3]
        check(p["supplier"]["name"] == "CJ" and p["supplier_status"][0]["code"] == "no-standard" and "CE" in p["supplier_status"][0].get("why", ""),
              f"a CJ sconce without a declared CE is 'חסר תקן' ({p['supplier_status']})")
        check(p["margin"]["src"] == "pick" and p["margin"]["pct"] >= 40 and p["margin"]["tone"] == "good", f"its margin is the designer's, green ({p['margin']})")
    sh = shade_pick(B)
    if sh:
        b, s, i, p = sh
        card = json.loads(next((ROOT / "data" / "products").rglob(f"{p['card_id']}.json")).read_text(encoding="utf-8"))
        codes = [x["code"] for x in p["supplier_status"]]
        check("no-standard" not in codes and labels["shade-set"]["he"] == "אהיל + סט תלייה" and "shade only" in ((card.get("safety") or {}).get("source") or "").lower(),
              f"a shade-only card (wave 4) needs the E27 set, not a CE of its own ({p['card_id']}: {codes})")
    else:
        print("  skip  no shade-only card on a board")
    cu = [x for x in picks_of(B, CUSHION) if x[1]["status"] == "candidate"]
    if cu:
        m = cu[0][3]["margin"]
        check(m and m["src"] == "economics", f"a candidate's margin comes from data/economics/products.json ({m})")
    tones = {(p["margin"] or {}).get("tone"): 0 for b in B["boards"] for s in b["slots"] for p in s.get("picks") or []}
    bad_tone = [(p["card_id"], p["margin"]) for b in B["boards"] for s in b["slots"] for p in s.get("picks") or [] if p["margin"] and
                p["margin"]["tone"] != ("bad" if p["margin"]["flag"] == "loss" or p["margin"]["pct"] < 25 else "good" if p["margin"]["pct"] >= 40 else "warn")]
    check(not bad_tone and {"good", "warn", "bad"} <= set(tones), f"margin tones: >= 40 green, 25-40 amber, below 25 or a loss red {bad_tone[:2]}")
    ready = [p for b in B["boards"] for s in b["slots"] for p in s.get("picks") or [] if any(x["code"] == "ready" for x in p["supplier_status"])]
    check(ready and all(p["supplier"]["key"] in ("cj", "aliexpress", "zendrop") and p["role"] != "candidate" and len(p["supplier_status"]) == 1 for p in ready),
          f"'מוכן לדרופשיפינג' only on a chosen dropshipping card without another status ({len(ready)})")
    cands = [(b, s, p) for b in B["boards"] for s in b["slots"] if s["status"] == "candidate" for p in s["picks"]]
    ctx = R.Context()
    wrong = []
    for b, s, p in cands:
        a = R.audit_for(ctx.audit, p["card_id"], f"{b['room']}/{s['id']}")
        want = "reviewed" if a and a.get("verdict") != "reject" else "unreviewed"
        if sum(1 for x in p["supplier_status"] if x["code"] in ("reviewed", "unreviewed")) != 1 or not any(x["code"] == want for x in p["supplier_status"]):
            wrong.append(f"{b['style']}/{b['room']}/{s['id']}/{p['card_id']}")
    check(not wrong and cands, f"every candidate is 'המעצב בדק' when the designer audited it there, else 'מועמד, לא נבדק' "
          f"({len(cands)}; {sum(1 for b, s, p in cands if any(x['code'] == 'reviewed' for x in p['supplier_status']))} reviewed) {wrong[:3]}")

    print("- nothing rejected on a board (B3)")
    check(not ctx.audit_error and ctx.audit, f"the designer audits load through final_round_coverage.py ({len(ctx.audit)} entries, error {ctx.audit_error})")
    on = [(b, s, p) for b in B["boards"] for s in b["slots"] for p in s.get("picks") or []]
    rejected = [f"{b['style']}/{b['room']}/{s['id']}/{p['card_id']}" for b, s, p in on if (ctx.cat.get(p["card_id"]) or {}).get("status") == "rejected"]
    check(not rejected, f"no card whose status is 'rejected' is on a board {rejected[:3]}")
    vetoed = [f"{b['style']}/{b['room']}/{s['id']}/{p['card_id']}" for b, s, p in on
              if (R.audit_for(ctx.audit, p["card_id"], f"{b['room']}/{s['id']}") or {}).get("verdict") == "reject"]
    check(not vetoed, f"no card the designer rejected for that slot is on a board {vetoed[:3]}")
    low = [f"{b['style']}/{b['room']}/{s['id']}/{p['card_id']}" for b, s, p in on
           if (lambda f: f is not None and f < 7)(R.designer_fit(R.audit_for(ctx.audit, p["card_id"], f"{b['room']}/{s['id']}"), b["style"]))]
    check(not low, f"no pick the designer scored below 7 for the style is on a board {low[:3]}")
    # the audit is slot-aware: a reject in one slot leaves the card in its other slots
    sl = [(k, a) for k, a in ctx.audit.items() if k[1] != "*" and a.get("verdict") == "reject" and (k[0], "*") not in ctx.audit]
    if sl:
        (cid, key), a = sl[0]
        check(R.audit_for(ctx.audit, cid, key) is a and R.audit_for(ctx.audit, cid, "living-room/no-such-slot") is None,
              f"a reject for one slot applies in that slot only ({cid} in {key})")
    reasons = {d["why"] for b in B["boards"] for d in b.get("dropped") or []}
    check(reasons <= set(B["dropped_he"]), f"every pick left out has a known reason ({sorted(reasons)})")
    gone = {d["card_id"] for b in B["boards"] for d in b.get("dropped") or []}
    check(not any(p["card_id"] in gone and (ctx.cat.get(p["card_id"]) or {}).get("status") == "rejected" for b, s, p in on),
          f"a pick left out because it was rejected is not on any board ({len(gone)} cards left out)")
    allc = {x["code"] for b in B["boards"] for s in b["slots"] for p in s.get("picks") or [] for x in p["supplier_status"]}
    check(allc <= set(labels), f"every status code has a label ({sorted(allc - set(labels))})")
    ctx = R.Context()
    il = {"id": "x", "name": "x", "supplier": {"name": "KADO HOME", "product_url": "https://example.co.il/x"}, "safety": {}, "notes": "", "currency": "ILS"}
    st = R.statuses_of(ctx, "living-room", "vase", il, R.supplier_of(il), None, "chosen", 199)
    check(R.supplier_of(il)["key"] == "il" and st and st[0]["code"] in ("coop-sent", "coop-replied", "coop-none"),
          f"an Israeli supplier gets its outreach state from directory.json ({st})")
    broken = dict(ctx.cat)
    cid = next(p["card_id"] for b in B["boards"] for s in b["slots"] for p in s.get("picks") or [])
    broken[cid] = dict(broken[cid], supplier="not an object", safety=["nope"], notes=None)
    try:
        bd = R.board_data("nordic", "living-room", ctx=type("C", (), dict(vars(ctx), cat=broken))())
        check(True, f"a broken card does not stop the boards ({sum(1 for s in bd['slots'] if s.get('picks'))} filled slots)")
    except Exception as e:
        check(False, f"a broken card does not stop the boards ({type(e).__name__}: {e})")

    print("- studio/build.py load_boards")
    Bd = T.load_build()
    plan = Bd.read_json(ROOT / "docs" / "house-plan.json")
    order, rooms = Bd.load_rooms(plan)
    products = Bd.load_products(set(order))
    ids = {p["id"] for p in products}
    board_ids = {p["card_id"] for b in B["boards"] for s in b["slots"] for p in s.get("picks") or []}
    check(board_ids <= ids, f"every card on a board is a product card ({len(board_ids)} cards, not cards: {sorted(board_ids - ids)[:3]})")
    Bd.BOARDS_SRC = ROOT / "scripts" / "boards" / "no-such-file.py"
    d = Bd.load_boards(products, True)
    check(d["present"] is False and d["boards"] == [] and d.get("error"), "a missing boards module leaves an explained empty screen, not a failed build")
    return B


# --------------------------------------------------------------------------- 2. browser

def open_boards(browser, base, width, scheme="light", keep_storage=False, block_storage=False, seed=None):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 860}, color_scheme=scheme, locale="he-IL")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "Failed to load resource" not in m.text else None)
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    if block_storage:
        init = "Object.defineProperty(window, 'localStorage', {configurable: true, get(){ throw new DOMException('blocked', 'SecurityError'); }});"
    elif keep_storage:  # clear once per context, so a reload keeps what the page saved
        init = "try{ if(!sessionStorage.getItem('smoke')){ localStorage.clear(); sessionStorage.setItem('smoke', '1'); } }catch(e){}"
    else:
        init = "try{localStorage.clear()}catch(e){}"
    if seed:
        init += f"try{{localStorage.setItem('studio.boards', {json.dumps(json.dumps(seed))})}}catch(e){{}}"
    page.add_init_script(init + (T.MOCK_DB % "{}"))
    page.goto(base + "#boards")
    page.wait_for_selector("#screen-boards:not([hidden]) #h-bd-board", timeout=15000)
    page.wait_for_timeout(150)
    return ctx, page, errors


def board_state(page):
    return page.evaluate("""() => ({
        h: document.getElementById('h-bd-board').textContent.trim(),
        sub: document.getElementById('bd-sub').textContent.replace(/\\s+/g, ' ').trim(),
        tiles: document.querySelectorAll('#bd-body .bd-grid > li.bt').length,
        chosen: document.querySelectorAll('#bd-body .bt-tag:not(.c)').length,
        cand: document.querySelectorAll('#bd-body .bt-tag.c').length,
        empty: document.querySelectorAll('#bd-body .bt-empty').length,
        hold: [...document.querySelectorAll('#bd-body .bt-empty[data-status="on-hold"] b')].filter(b => b.textContent === 'בהמתנה').length,
        rows: (document.querySelector('#bd-body .bd-tbl-wrap') || {}).offsetParent ? document.querySelectorAll('#bd-body .bd-tbl tbody tr').length
            : document.querySelectorAll('#bd-body .bd-list li.bl-pick, #bd-body .bd-list li.bl-slot.is-empty').length,
        list: !!(document.querySelector('#bd-body .bd-list') || {}).offsetParent,
        current: [...document.querySelectorAll('.bd-cell[aria-current="true"]')].filter(e => e.offsetParent).map(e => e.dataset.bdCell)
    })""")


def expect_board(st, b, view):
    c = b["counts"]
    ok = st["h"] == f"{b['room_he']} · {b['style_he']}" and st["sub"] == sub_line(b)
    if view == "tiles":
        ok = ok and st["tiles"] == c["slots"] and st["chosen"] == c["chosen"] and st["cand"] == c["candidate"] and st["empty"] == c["missing"] and st["hold"] == c["on_hold"]
    else:
        ok = ok and st["rows"] == sum(max(1, len(s.get("picks") or [])) for s in b["slots"])
    return ok


def margin_shown_ok(chip, pk) -> bool:
    """A margin chip on a board: the live one (data-src "live", checked against #profit separately) has the tone of its
    number; any other is the board's margin, with its tone."""
    src, pct, tone = chip.get_attribute("data-src"), chip.get_attribute("data-pct"), chip.get_attribute("data-tone")
    if src == "live":
        x = float(pct)
        return tone == ("bad" if x < 25 else "good" if x >= 40 else "warn") or tone == "bad"
    m = pk["margin"]
    return (not m and tone == "none") or bool(m and pct == f"{m['pct']:.1f}" and tone == m["tone"])


def agree_checks(page, B):
    """The boards and the profitability screen show the same margin for the same card (live margins)."""
    print("- the boards' margins agree with the profitability screen")
    seen = {}
    for style, room in (("nordic", "living-room"), ("warm-modern", "work"), ("boho", "bath"), ("japandi", "kids")):
        page.click(f".bd-mx-wide .bd-cell[data-bd-cell='{style}|{room}']")
        page.click("[data-bd-view='table']")
        for row in page.locator("#bd-body .bd-tbl tr[data-card]").all():
            chip = row.locator(".bd-margin")
            if chip.get_attribute("data-src") == "live":
                seen.setdefault(row.get_attribute("data-card"), chip.get_attribute("data-pct"))
    page.click("[data-bd-view='tiles']")
    page.goto(page.url.split("#")[0] + "#profit")
    page.wait_for_selector("#screen-profit:not([hidden]) tr[data-pid]", timeout=15000)
    prof = page.evaluate("Object.fromEntries([...document.querySelectorAll('#screen-profit tr[data-pid]')].map(r => [r.dataset.pid, r.dataset.margin]))")
    bad = [(cid, pct, prof.get(cid)) for cid, pct in seen.items() if prof.get(cid) != pct]
    check(seen and not bad, f"{len(seen)} picks with a live margin show the margin of #profit {bad[:3]}")
    page.goto(page.url.split("#")[0] + "#boards")
    page.wait_for_selector("#screen-boards:not([hidden]) #h-bd-board", timeout=15000)


def browser_checks(browser, base, D):
    B = D["boards"]
    names = {p["id"]: p["name"] for p in D["products"]}

    print("- 1280px light: nav, the coverage map, all 48 boards from the map")
    ctx, page, errors = open_boards(browser, base, 1280)
    check(page.locator(".tabs a[data-screen='boards']").inner_text().strip() == "לוחות חדרים" and
          page.get_attribute(".tabs a[data-screen='boards']", "aria-current") == "page", "the nav has 'לוחות חדרים', current")
    check(page.locator("#h-boards").inner_text() == "לוחות חדרים", "the screen's heading")
    cells = page.locator(".bd-mx-wide .bd-cell")
    check(cells.count() == 48 and page.locator(".bd-mx-wide tbody tr").count() == 6 and page.locator(".bd-mx-wide thead th").count() == 8,
          f"the map: 6 styles x 8 rooms ({cells.count()} cells)")
    shares = page.eval_on_selector_all(".bd-mx-wide .bd-cell", "e => e.map(x => [x.dataset.bdCell, x.dataset.share, x.querySelector('.p').textContent])")
    # Math.round in the page (62.5 -> 63), not Python's round half to even
    want = {f"{b['style']}|{b['room']}": int(100 * (b["counts"]["chosen"] + b["counts"]["candidate"]) / b["counts"]["slots"] + 0.5) for b in B["boards"]}
    check(all(int(s) == want[k] and p == f"{want[k]}%" for k, s, p in shares), "every cell shows the share of filled slots (chosen + candidate)")
    check(page.locator(".bd-segs [data-bd-style]").count() == 6 and page.locator(".bd-segs [data-bd-room]").count() == 8, "6 style and 8 room buttons")
    st = board_state(page)
    check(expect_board(st, find(B, "nordic", "living-room"), "tiles") and st["current"] == ["nordic|living-room"],
          f"the default board is the Nordic living room: {st['sub']}")
    legend = page.locator(".bd-legend").inner_text()
    check('"נבחר": בחירת המעצב' in legend and '"מועמד": מוצר מהליקוט האחרון בהתאמה 7 ומעלה (לפי ציון המעצב כשהוא בדק אותו)' in legend
          and "המעצב דחה בעמדה" in legend and "בלי ריהוט קבוע" in legend,
          "the legend line, as in the board images")
    cols = page.evaluate("getComputedStyle(document.querySelector('#bd-body .bd-grid')).gridTemplateColumns.split(' ').length")
    gap = page.evaluate("getComputedStyle(document.querySelector('#bd-body .bd-grid')).columnGap")
    check(cols == 5 and gap == "16px", f"5 columns with a 16px gutter on desktop ({cols}, {gap})")
    bad = []
    for b in B["boards"]:
        key = f"{b['style']}|{b['room']}"
        page.click(f".bd-mx-wide .bd-cell[data-bd-cell='{key}']")
        st = board_state(page)
        foc = page.evaluate("document.activeElement && document.activeElement.id")
        if not (expect_board(st, b, "tiles") and st["current"] == [key] and foc == "h-bd-board"):
            bad.append(f"{key}: {st['h']} · {st['sub']} · tiles {st['tiles']}")
    check(not bad, "all 48 boards open from the map: heading, counts line, one tile per slot, tags, empty tiles, focus on the heading" + ("" if not bad else f" {bad[:2]}"))
    T.no_hscroll(page, 1280, "1280px")
    check(not errors, "1280px: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))

    print("- tiles: chips, margin, the product drawer")
    page.click(".bd-mx-wide .bd-cell[data-bd-cell='nordic|living-room']")
    nl = find(B, "nordic", "living-room")
    sl = next(s for s in nl["slots"] if s["status"] == "chosen" and len(s["picks"]) > 1)
    tile = page.locator(f"#bd-body li.bt[data-slot='{sl['id']}']")
    main = sl["picks"][0]
    txt = tile.inner_text()
    lab = B["status_labels"][main["supplier_status"][0]["code"]]["he"] if main["supplier_status"] else None
    chip = tile.locator(".bd-margin")
    live = chip.get_attribute("data-src") == "live"
    first = tile.locator(".bd-chip[data-code]").first
    lab_shown = first.inner_text() if tile.locator(".bd-chip[data-code]").count() else None
    check(main["supplier"]["name"] in txt and (live or lab is None or lab == lab_shown) and (lab_shown is None or lab_shown in [x["he"] for x in B["status_labels"].values()]),
          f"tile '{sl['name_he']}': supplier {main['supplier']['name']}, status '{lab_shown}' (board: '{lab}'), margin {chip.get_attribute('data-pct')} ({chip.get_attribute('data-src')})")
    check(margin_shown_ok(chip, main), f"the margin chip: the board's or the live one, and its colour follows its tone ({chip.get_attribute('data-tone')})")
    tile.locator(".bt-main").click()
    page.wait_for_selector("#drawer[open]")
    check(page.locator("#drawer-title").inner_text().strip() == names[main["card_id"]].strip(), f"the tile opens the drawer of {main['card_id']}")
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.getElementById('drawer').open", timeout=5000)
    check(page.evaluate(f"document.activeElement && document.activeElement.matches(\"li.bt[data-slot='{sl['id']}'] .bt-main\")"), "Escape closes it, focus back on the tile")
    alt = sl["picks"][1]
    tile.locator(f".bt-alt[data-product='{alt['card_id']}']").click()
    page.wait_for_selector("#drawer[open]")
    check(page.locator("#drawer-title").inner_text().strip() == names[alt["card_id"]].strip(), f"an alternate opens its own card ({alt['card_id']})")
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.getElementById('drawer').open", timeout=5000)
    sc = next(((b, s) for b, s, i, p in picks_of(B, SCONCE) if b["style"] == "nordic" and i == 0), None)
    if sc:
        page.click(f".bd-mx-wide .bd-cell[data-bd-cell='{sc[0]['style']}|{sc[0]['room']}']")
        t = page.locator(f"#bd-body li.bt[data-card='{SCONCE}']").first
        check(t.locator(".bd-chip[data-code='no-standard']").count() == 1 and "CJ" in t.inner_text() and t.locator(".bd-margin").get_attribute("data-tone") == "good",
              "the CJ sconce tile: 'חסר תקן', CJ, a green margin")
    ready = next(((b, s) for b in B["boards"] for s in b["slots"] if s.get("picks") and s["picks"][0]["supplier_status"] and
                  s["picks"][0]["supplier_status"][0]["code"] == "ready"), None)
    if ready:
        page.click(f".bd-mx-wide .bd-cell[data-bd-cell='{ready[0]['style']}|{ready[0]['room']}']")
        t = page.locator(f"#bd-body li.bt[data-slot='{ready[1]['id']}']")
        check("מוכן לדרופשיפינג" in t.inner_text(), f"'מוכן לדרופשיפינג' on {ready[0]['style']}/{ready[0]['room']}/{ready[1]['id']}")
    T.axe(page, "1280px light tiles", "#screen-boards")

    print("- the official coverage and the map's own measure (M7)")
    cov = D.get("coverage") or {}
    if cov.get("present"):
        sec = page.locator("#bd-body [data-cov='boards']")
        tot = f"{cov['total']['pct_ready']:g}%"
        check(sec.count() == 1 and tot in sec.inner_text() and sec.locator("tbody tr").count() == len(cov["styles"]),
              f"the boards screen shows the official coverage ({tot}, {len(cov['styles'])} styles)")
        check("לא הכיסוי הרשמי" in page.locator("#bd-count").inner_text() and "זה לא הכיסוי הרשמי" in page.locator("#bd-body").inner_text(),
              "the map's share of slots with a product says it is not the official coverage")
    agree_checks(page, B)

    print("- the table view")
    page.click(".bd-mx-wide .bd-cell[data-bd-cell='nordic|living-room']")
    page.click("[data-bd-view='table']")
    page.wait_for_selector("#bd-body .bd-tbl")
    heads = page.eval_on_selector_all("#bd-body .bd-tbl thead th", "e => e.map(x => x.textContent.trim())")
    check(heads == ["עמדה", "מוצר", "ספק", "סטטוס מול הספק", "מחיר", "רווח %"], f"the table's columns ({heads})")
    check(expect_board(board_state(page), nl, "table"), "one row per slot and pick, in the slot order")
    empty = nl["slots"][[s["status"] for s in nl["slots"]].index("missing")]
    check("חסר" in page.locator(f"#bd-body tr.is-empty[data-slot='{empty['id']}']").inner_text(), f"an empty slot says 'חסר' ({empty['id']})")
    row = page.locator(f"#bd-body tr.is-main[data-slot='{sl['id']}']")
    check(main["supplier"]["name"] in row.locator(".c-sup").inner_text() and row.locator(".c-st .bd-chip").count() == len(main["supplier_status"]),
          f"the row of '{sl['name_he']}': supplier and every status chip")
    ted = picks_of(B, TEDDY)
    if ted:
        b, s, i, p = ted[0]
        page.click(f".bd-mx-wide .bd-cell[data-bd-cell='{b['style']}|{b['room']}']")
        r = page.locator(f"#bd-body .bd-tbl tr[data-card='{TEDDY}']")
        check(r.count() == 1 and r.locator(".c-st .bd-chip").first.inner_text() == "בהמתנה" and "AliExpress" in r.inner_text()
              and margin_shown_ok(r.locator(".bd-margin"), p),
              f"the teddy's row: 'בהמתנה' first, AliExpress, margin {r.locator('.bd-margin').get_attribute('data-pct')} ({r.locator('.bd-margin').get_attribute('data-src')}) ({b['style']}/{b['room']}, alternate {i})")
        r.locator("button.tp").click()
        page.wait_for_selector("#drawer[open]")
        check(page.locator("#drawer-title").inner_text().strip() == names[TEDDY].strip(), "a table row opens the drawer of its card")
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.getElementById('drawer').open", timeout=5000)
    sh = shade_pick(B)
    if sh:
        b, s, i, p = sh
        page.click(f".bd-mx-wide .bd-cell[data-bd-cell='{b['style']}|{b['room']}']")
        check("אהיל + סט תלייה" in page.locator(f"#bd-body .bd-tbl tr[data-slot='{s['id']}'][data-card='{p['card_id']}'] .c-st").first.inner_text(),
              f"a shade-only card's row: 'אהיל + סט תלייה' ({b['style']}/{b['room']}/{s['id']})")
    T.axe(page, "1280px light table", "#screen-boards")
    check(not errors, "1280px tiles and table: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()

    print("- 400px dark: selects, all 48 boards in the table and as tiles, no horizontal scroll")
    ctx, page, errors = open_boards(browser, base, 400, "dark")
    check(page.locator(".bd-mx-narrow").is_visible() and not page.locator(".bd-mx-wide").is_visible() and page.locator(".bd-mx-narrow tbody tr").count() == 8,
          "the map turns: rooms in rows, styles in columns")
    check(page.locator("#bd-style").is_visible() and page.locator("#bd-room").is_visible() and not page.locator(".bd-segs").is_visible(), "selects instead of buttons")
    cols = page.evaluate("getComputedStyle(document.querySelector('#bd-body .bd-grid')).gridTemplateColumns.split(' ').length")
    check(cols == 2, f"2 columns on a phone ({cols})")
    T.no_hscroll(page, 400, "400px tiles")
    T.axe(page, "400px dark tiles", "#screen-boards")
    sl0 = next(s for s in nl["slots"] if s.get("picks"))
    page.locator(f"#bd-body li.bt[data-slot='{sl0['id']}'] .bt-main").click()
    page.wait_for_selector("#drawer[open]")
    check(page.locator("#drawer-title").inner_text().strip() == names[sl0["picks"][0]["card_id"]].strip(), "400px: a tile opens the drawer")
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.getElementById('drawer').open", timeout=5000)
    # a cell of the map: the board comes under the sticky masthead, not behind it
    page.click(".bd-mx-narrow .bd-cell[data-bd-cell='boho|bath']")
    top = page.evaluate("document.getElementById('h-bd-board').getBoundingClientRect().top - document.querySelector('.mast').getBoundingClientRect().bottom")
    check(0 <= top < 60 and board_state(page)["h"] == "חדר רחצה · בוהו", f"a map cell opens the board right under the masthead ({top:.0f}px)")
    page.click("[data-bd-view='table']")
    check(board_state(page)["list"] and not page.locator("#bd-body .bd-tbl-wrap").is_visible(),
          "400px: the table view is a stacked list (supplier, status and margin without a sideways swipe)")
    ted = picks_of(B, TEDDY)
    if ted:
        b, s, i, p = ted[0]
        page.select_option("#bd-style", b["style"])
        page.select_option("#bd-room", b["room"])
        li = page.locator(f"#bd-body .bd-list li.bl-pick[data-card='{TEDDY}']")
        check(li.count() == 1 and li.locator(".bd-chip[data-code]").first.inner_text() == "בהמתנה" and "AliExpress" in li.inner_text()
              and margin_shown_ok(li.locator(".bd-margin"), p), "400px list: the teddy is 'בהמתנה', AliExpress, with its margin")
        li.locator("button.bl-main").click()
        page.wait_for_selector("#drawer[open]")
        check(page.locator("#drawer-title").inner_text().strip() == names[TEDDY].strip(), "400px list: a product opens its drawer")
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.getElementById('drawer').open", timeout=5000)
    bad, wide = [], []
    for b in B["boards"]:
        page.select_option("#bd-style", b["style"])
        page.select_option("#bd-room", b["room"])
        st = board_state(page)
        if not expect_board(st, b, "table"):
            bad.append(f"{b['style']}/{b['room']}: {st['h']} rows {st['rows']}")
        sw = page.evaluate("document.documentElement.scrollWidth")
        if sw > 401:
            wide.append(f"{b['style']}/{b['room']} {sw}")
    check(not bad, "all 48 boards from the selects, in the table view (the phone list): heading, counts, one item per slot and pick" + ("" if not bad else f" {bad[:2]}"))
    check(not wide, "400px: no horizontal scroll on any board (the table scrolls inside its own box)" + ("" if not wide else f" {wide[:3]}"))
    T.axe(page, "400px dark table", "#screen-boards")
    page.click("[data-bd-view='tiles']")
    wide = []
    for b in B["boards"]:
        page.select_option("#bd-style", b["style"])
        page.select_option("#bd-room", b["room"])
        if not expect_board(board_state(page), b, "tiles") or page.evaluate("document.documentElement.scrollWidth") > 401:
            wide.append(f"{b['style']}/{b['room']}")
    check(not wide, "all 48 boards as tiles at 400px, without horizontal scroll" + ("" if not wide else f" {wide[:3]}"))
    check(not errors, "400px: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()

    print("- 1280px dark and 400px light")
    for width, scheme in ((1280, "dark"), (400, "light")):
        ctx, page, errors = open_boards(browser, base, width, scheme)
        T.no_hscroll(page, width, f"{width}px {scheme}")
        T.axe(page, f"{width}px {scheme} tiles", "#screen-boards")
        check(not errors, f"{width}px {scheme}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
        ctx.close()

    print("- remembered per viewer (localStorage), and without it")
    ctx, page, errors = open_boards(browser, base, 1280, keep_storage=True)
    page.click(".bd-segs [data-bd-style='japandi']")
    check(page.evaluate("document.activeElement && document.activeElement.dataset.bdStyle") == "japandi", "focus stays on the style button")
    page.click(".bd-segs [data-bd-room='work']")
    page.click("[data-bd-view='table']")
    page.reload()
    page.wait_for_selector("#screen-boards:not([hidden]) #h-bd-board")
    st = board_state(page)
    check(st["h"] == "חדר עבודה · ג'פנדי" and st["rows"] > 0 and page.get_attribute("[data-bd-view='table']", "aria-pressed") == "true",
          f"after a reload: the same style, room and view ({st['h']})")
    check(page.evaluate("JSON.parse(localStorage.getItem('studio.boards'))") == {"style": "japandi", "room": "work", "view": "table"},
          "saved under studio.boards with the Studio's store")
    ctx.close()
    ctx, page, errors = open_boards(browser, base, 1280, seed={"style": "no-such-style", "room": "attic", "view": "x"})
    check(board_state(page)["h"] == "סלון · נורדי", "an unknown saved choice falls back to the first board")
    ctx.close()
    ctx, page, errors = open_boards(browser, base, 1280, block_storage=True)
    page.click(".bd-segs [data-bd-style='boho']")
    check(board_state(page)["h"] == "סלון · בוהו" and not errors, "localStorage that throws: the screen still renders and switches" + ("" if not errors else ": " + "; ".join(errors[:2])))
    ctx.close()


def empty_checks(browser, dist: Path, tmp: Path):
    print("- data.json without boards")
    d2 = tmp / "no-boards"
    d2.mkdir(parents=True, exist_ok=True)
    data = json.loads((dist / "data.json").read_text(encoding="utf-8"))
    data["boards"] = {"present": False, "error": "FIXTURE: module failed", "boards": []}
    (data.get("chunks") or {}).pop("boards", None)  # the boards are in data.json itself here, not a chunk
    (d2 / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(dist / "index.html", d2 / "index.html")
    srv, base = T.serve(d2)
    try:
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="he-IL")
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
        page.goto(base + "#boards")
        page.wait_for_selector("#screen-boards:not([hidden]) #bd-body .empty", timeout=15000)
        check("FIXTURE: module failed" in page.locator("#bd-body").inner_text() and not errors, "no boards: the screen says why, without errors")
        ctx.close()
    finally:
        srv.shutdown()


def shots(browser):
    print("- screenshots from the real data (studio/dist) into studio/screens/")
    r = subprocess.run([sys.executable, str(STUDIO / "build.py")], cwd=ROOT, capture_output=True, text=True)
    print("\n".join("    " + l for l in r.stdout.splitlines() if "boards" in l or "dist:" in l))
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("real build failed")
    srv, base = T.serve(STUDIO / "dist")
    SCREENS.mkdir(parents=True, exist_ok=True)
    try:
        for width, scheme, view, name in ((1280, "light", "tiles", "boards-1280"), (1280, "dark", "tiles", "boards-1280-dark"),
                                          (400, "light", "tiles", "boards-400"), (400, "dark", "tiles", "boards-400-dark"),
                                          (1280, "light", "table", "boards-table-1280"), (400, "light", "table", "boards-table-400")):
            ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, locale="he-IL")
            page = ctx.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.add_init_script("try{localStorage.clear();localStorage.setItem('studio.boards', " + json.dumps(json.dumps({"style": "nordic", "room": "living-room", "view": view})) + ")}catch(e){}")
            page.goto(base + "#boards")
            page.wait_for_selector("#screen-boards:not([hidden]) #h-bd-board", timeout=15000)
            page.evaluate("window.__studioPictures.all()")
            page.wait_for_function("() => window.__studioPictures.ready().then(() => true)", timeout=30000)
            page.wait_for_timeout(700)  # web fonts
            p = SCREENS / f"{name}.png"
            page.screenshot(path=str(p), full_page=True)
            h = page.evaluate("document.documentElement.scrollHeight")
            print(f"    {p.relative_to(ROOT)} ({width}×{h})")
            T.no_hscroll(page, width, f"real data {name}")
            check(not errors, f"real data {name}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()
    finally:
        srv.shutdown()


def main() -> int:
    python_checks()
    tmp = Path(tempfile.mkdtemp(prefix="studio-boards-"))
    try:
        print("- build with the real data (offline)")
        T.build(tmp / "dist", None)
        D = T.load_build().read_dist_data(tmp / "dist")
        check("boards" not in json.loads((tmp / "dist" / "data.json").read_text(encoding="utf-8")) and (tmp / "dist" / "data-boards.json").exists(),
              "the boards are a chunk (data-boards.json), not in the first load")
        bi = D["boards"]["images"]
        imgs = {p["id"]: p.get("img") or {} for p in D["products"]}
        missing = [i for i in {p["card_id"] for b in D["boards"]["boards"] for s in b["slots"] for p in s.get("picks") or []}
                   if not (imgs.get(i, {}).get("sheet") and (tmp / "dist" / imgs[i]["sheet"]).exists())]
        check(not missing and bi["with_file"] == bi["cards"] and not bi["not_cards"],
              f"every card on a board has its picture in a sheet ({bi['with_file']} of {bi['cards']}; placeholders offline: {len(bi['placeholders'])})")
        check(D["boards"]["redacted"] == 0 and D["boards"]["bad_ids"] == [], "the boards pass the secret check, every id known")
        srv, base = T.serve(tmp / "dist")
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=T.CHROMIUM if Path(T.CHROMIUM).exists() else None)
                browser_checks(browser, base, D)
                empty_checks(browser, tmp / "dist", tmp)
                if "--shots" in sys.argv:
                    shots(browser)
                browser.close()
        finally:
            srv.shutdown()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {tmp}")
    print(f"\n{'FAILED' if T.failures else 'PASSED'}: {len(T.failures)} failed checks")
    return 1 if T.failures else 0


if __name__ == "__main__":
    sys.exit(main())
