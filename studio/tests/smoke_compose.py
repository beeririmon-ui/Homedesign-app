#!/usr/bin/env python3
"""Smoke test for the Studio's room compositions ("הרכבה" in the rooms screen) and the next sourcing round ("ליקוט הבא").

1. Python checks on studio/build.py (no browser):
   - the eight real compositions (data/compositions): every room is read, the status counts agree with each file's own
     summary, the whole-look total is the file's, on-hold slots name their blocking decision (LK1 in the bath),
     and every product reference is a card, an AliExpress record, a set or a model (none lost);
   - the fixture compositions (studio/tests/fixtures/compositions): slots as a list, odd status spellings, a card id with a
     suffix, a card that does not exist, an AliExpress record, a set, a furniture model, a slot not in the slots file,
     a broken file, an unknown room, a list instead of an object, the newer of two files for the same room;
   - the real round-3 list: tiers and sources add up to its query count, the slots are sorted by priority, every slot has
     its price ceiling, the needs-card and already-searched lists; the searched index goes into data.json as counts only;
   - the round's results: absent = "not yet"; the fixture results (studio/tests/fixtures/round-3-results) in every shape
     (the round's own per-source report like round-3-results/cj.json, one file per slot, {records}, {slots: {...}},
     an unknown slot, a broken file) land in their slots; the real results files read cleanly when they exist.
2. Browser, built offline into temp folders (studio/dist is not touched), 390px and 1280px, light and dark:
   - A: the real compositions and round-3 list with the fixture results. Rooms: the composition view is the default, the
     status chips count the slots and filter them, the whole look and the room check show, a card tile opens the product
     drawer, LK1 on a bath slot on hold goes to the decisions screen, the old "frames and slots" view is still there.
     Sourcing: totals per tier and per source, the rules, the slots by priority (30 at a time, "more" and "all"), the
     room / priority / source / "only with results" filters
     (focus stays), needs-card and dropped lists, the fixture results in their slots, the unmatched record and the broken
     file reported, and the links between a sourcing slot and its composition slot both ways.
   - B: the fixture compositions: "צריך כרטיס" on an AliExpress tile, "הכרטיס לא נמצא", a set, a model, the file's
     differing counts, a slot outside the slots file; the sourcing screen says the results have not arrived.
   - every case: no horizontal scroll, axe-core finds no WCAG 2.0/2.1 A or AA violation, no JavaScript error.
3. --shots: builds the real data into studio/dist and saves assets/qa/studio-2026-10-12/
   rooms-composition-{390,1280}-{light,dark}.png (living room), rooms-composition-bath-390-light.png and
   sourcing-{390,1280}-{light,dark}.png.

Usage:  python3 studio/tests/smoke_compose.py [--shots] [--keep]
Needs:  Python Playwright and Chromium (PW_CHROMIUM, default /opt/pw-browsers/chromium); axe-core from site/node_modules.
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import functools
import http.server
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / "studio"
FIX = STUDIO / "tests" / "fixtures"
FIX_COMP = FIX / "compositions"
FIX_RES = FIX / "round-3-results"
AXE = ROOT / "site" / "node_modules" / "axe-core" / "axe.min.js"
CHROMIUM = os.environ.get("PW_CHROMIUM", "/opt/pw-browsers/chromium")
SHOTS = ROOT / "assets" / "qa" / "studio-2026-10-12"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
STATUSES = ("ready-to-lock", "partial", "empty", "on-hold")

failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(("  ok    " if ok else "  FAIL  ") + what, flush=True)
    if not ok:
        failures.append(what)


def load_build():
    spec = importlib.util.spec_from_file_location("studio_build_compose", STUDIO / "build.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def raw_slots(d: dict) -> list[dict]:
    s = d.get("slots")
    if isinstance(s, dict):
        return [v for v in s.values() if isinstance(v, dict)]
    return [v for v in s or [] if isinstance(v, dict)]


def refs(x):
    """every product reference in a normalized composition"""
    if isinstance(x, dict):
        if x.get("k") in ("card", "ae", "set", "model", "missing"):
            yield x
        for v in x.values():
            yield from refs(v)
    elif isinstance(x, list):
        for v in x:
            yield from refs(v)


# --------------------------------------------------------------------------- 1. python checks

def python_checks():
    print("- build.py: compositions, round 3, results, searched index")
    B = load_build()
    plan = B.read_json(ROOT / "docs" / "house-plan.json")
    order, rooms = B.load_rooms(plan)
    sl = B.load_slots(order, rooms)
    products = B.load_products(set(order))
    B.attach_candidates(sl, products)
    sbk = {s["key"]: s for rows in sl.values() for s in rows}
    dec = {d["id"] for d in B.load_decisions(order)["items"]}
    ctx = B.CompCtx(products, dec, order, sbk)
    by_id = {p["id"] for p in products}

    # the real compositions
    comps = B.load_compositions(B.COMPOSITIONS_DIR, ctx)
    files = sorted(B.COMPOSITIONS_DIR.glob("*.json"))
    check(not comps["warnings"], f"real compositions read without warnings ({comps['warnings'][:2]})")
    rooms_in_files = set()
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        room = B.room_key(d.get("room"), set(order))
        rooms_in_files.add(room)
        c = (comps["rooms"].get(room) or {}).get("nordic")
        if not c:
            check(False, f"{f.name}: composition missing in the output")
            continue
        fc = d.get("counts") or d.get("status_counts") or {}
        want = {k: fc.get(k, 0) for k in STATUSES}
        check(c["counts"] == want and c["file_counts"] is None, f"{room}: status counts from the slots = the file's summary {want}")
        check(len(c["slots"]) == len(raw_slots(d)), f"{room}: {len(c['slots'])} slots, as in the file")
        w = d.get("whole_look") or {}
        total = w.get("total_price_ils", (w.get("both_rooms") or {}).get("total_price_ils"))
        check((c["whole"] or {}).get("main", {}).get("price") == total, f"{room}: whole-look total ₪{total}")
        check(bool(c["check"]), f"{room}: room check text")
        rs = list(refs(c["slots"]))
        n_raw = sum(1 for s in raw_slots(d) for x in [s.get("default")] + list(s.get("variations") or []) if isinstance(x, dict))
        n_raw += sum(1 for s in raw_slots(d) for b in (s.get("by_room") or {}).values() if isinstance(b, dict)
                     for x in [b.get("default")] + list(b.get("variations") or []) if isinstance(x, dict))
        top = sum(1 for s in c["slots"] for x in [s.get("default")] + (s.get("variations") or []) if x) \
            + sum(1 for s in c["slots"] for b in s.get("by_room") or [] for x in [b.get("default")] + (b.get("variations") or []) if x)
        check(top == n_raw, f"{room}: every default and variation kept ({top} of {n_raw})")
        check(all(r["k"] != "card" or r["id"] in by_id for r in rs), f"{room}: card tiles point at existing cards")
    check(rooms_in_files == set(comps["rooms"]), f"one composition per room ({len(comps['rooms'])} rooms)")
    bath = (comps["rooms"].get("bath") or {}).get("nordic") or {"slots": []}
    lk1 = [s for s in bath["slots"] if s["status"] == "on-hold" and any("LK1" in b["ids"] for b in s.get("blocked") or [])]
    check(len(lk1) >= 5, f"bath: on-hold slots name LK1 as their blocking decision ({len(lk1)})")
    kids = (comps["rooms"].get("kids") or {}).get("nordic") or {"slots": []}
    check(any(s.get("by_room") for s in kids["slots"]), "kids: per-room sub-slots (boy / girl) kept")

    # the fixture compositions
    fx = B.load_compositions(FIX_COMP, ctx)
    w = " | ".join(fx["warnings"])
    check("attic" in w and "bath-nordic" in w and "kids-nordic" in w, "fixture: unknown room, broken file and a list are reported, not fatal")
    hall = (fx["rooms"].get("hall") or {}).get("nordic")
    check(bool(hall) and hall["author"] == "FIXTURE newer" and hall["slots"] == [], "fixture: 'entrance' / 'scandinavian' map to hall / nordic; the newer file wins")
    lr = fx["rooms"]["living-room"]["nordic"]
    st = {s["id"]: s for s in lr["slots"]}
    check(st["curtains"]["status"] == "partial" and st["rug"]["status"] == "on-hold", "fixture: status spellings normalized ('Partial', 'ON HOLD')")
    check(st["curtains"]["default"]["k"] == "card" and st["curtains"]["default"]["id"] == "curtains-aliexpress-linen-blend-s-fold-180502",
          "fixture: a card id with a suffix ' (pair)' resolves")
    check(st["curtains"]["variations"][0]["k"] == "missing", "fixture: a card that does not exist is marked missing")
    lamp = st["floor-lamp"]["default"]
    has_card = ctx.card_for_ae("1005009294740268", "living-room/floor-lamp")
    check(lamp["k"] == ("card" if has_card else "ae") and lamp["ae"] == "1005009294740268", f"fixture: AliExpress record {'(a card exists now)' if has_card else 'without a card'}")
    check(st["cushions"]["default"]["k"] == "set" and len(st["cushions"]["default"]["items"]) == 2, "fixture: a set with two items")
    check(st["sofa"]["default"]["k"] == "model" and st["sofa"]["default"].get("price_from"), "fixture: a furniture model with 'from' price")
    check(st["no-such-slot"].get("unknown_slot") is True, "fixture: a slot outside the slots file is flagged")
    check("not a slot" not in json.dumps(lr["slots"], ensure_ascii=False), "fixture: a non-object slot is skipped")
    check(st["vase"].get("lock_ids") == ["VL1"], "fixture: the lock decision VL1 is linked")
    check(st["framed-art"]["blocked"][0]["ids"] == ["PR1"] and st["framed-art"]["blocked"][1]["ids"] == [], "fixture: PR1 found in 'PR1: ...', none in plain text")
    check(lr["file_counts"] is not None and lr["counts"]["ready-to-lock"] == 2, "fixture: the file's differing counts are kept next to the real ones")
    check([x["label"] for x in lr["whole"]["subs"]] == ["חדר הילד", "חדר הילדה"] and lr["whole"]["subs"][1]["margin"] < 0, "fixture: whole-look parts, margin computed")
    check(lr["check"][:3] == ["FIXTURE בדיקה", "(1) נקודה ראשונה", "(2) נקודה שנייה"], "fixture: the room check splits at its numbered points")

    # the real round 3
    ns = B.load_next_sourcing(B.NEXT_SOURCING_DIR, None, ctx, comps)
    rf, rnd = B.latest_round(B.NEXT_SOURCING_DIR)
    r3 = json.loads(rf.read_text(encoding="utf-8"))
    check(ns["present"] and ns["round"] == r3.get("round", rnd), f"round {ns.get('round')} read from {rf.name}")
    check(len(ns["slots"]) == len(r3["slots"]), f"all {len(r3['slots'])} slots")
    n_plan = sum(len(v) for v in r3["search_plan"].values())
    check(sum(t["n"] for t in ns["tiers"]) == n_plan == ns["n_queries"] == sum(ns["by_source"].values()),
          f"tiers and sources add up to the query count ({ns['n_queries']})")
    check(all(sum(t["by_source"].values()) == t["n"] for t in ns["tiers"]), "each tier's sources add up to the tier")
    pr = {"high": 0, "medium": 1, "low": 2}
    seq = [pr.get(s["priority"], 3) for s in ns["slots"]]
    check(seq == sorted(seq), "slots sorted by priority")
    raw_ceil = {s["slot"]: s.get("price_ceiling") or {} for s in r3["slots"]}
    kept = [s["key"] for s in ns["slots"] if all(s["ceiling"].get(k) == raw_ceil.get(s["key"], {}).get(k) for k in ("breakeven_landed_ils", "landed_for_40_ils"))]
    n_num = sum(1 for c in raw_ceil.values() if isinstance(c.get("landed_for_40_ils"), (int, float)))
    check(len(kept) == len(ns["slots"]), f"every slot keeps its break-even and 40% landed ceiling ({n_num} with numbers in the file)")
    check(len(ns["needs_card"]) == len(r3["needs_card"]) and len(ns["dropped"]) == len(r3["dropped_as_already_searched"]), "needs-card and dropped lists")
    check(sum(len(s["queries"]) for s in ns["slots"]) == sum(len(s["queries"]) for s in r3["slots"]), "every slot's new queries kept")
    blocked_onhold = [s for s in ns["slots"] if s["status"] == "on-hold" and s["blocked"]]
    check(len(blocked_onhold) >= 10, f"on-hold slots carry their blocking decisions from the composition ({len(blocked_onhold)})")
    sx = ns["searched"]
    si = json.loads((B.NEXT_SOURCING_DIR / "searched-index.json").read_text(encoding="utf-8"))
    check(sx["ae_queries"] == sum(len(v) for v in si["aliexpress_queries_by_slot"].values()) and sx["ae_slots"] == len(si["aliexpress_queries_by_slot"]),
          f"searched index as counts: {sx['ae_queries']} AliExpress queries in {sx['ae_slots']} slots")
    sample = next(iter(next(iter(si["aliexpress_queries_by_slot"].values()))))
    check(sample not in json.dumps(sx, ensure_ascii=False), "the searched index's query lists are not copied into data.json")
    res_dir = B.NEXT_SOURCING_DIR / f"round-{ns['round']}-results"
    check(ns["results"]["present"] == res_dir.exists(), f"results {'present' if res_dir.exists() else 'absent: not yet'} ({ns['results']['dir']})")
    empty = Path(tempfile.mkdtemp(prefix="studio-src-empty-"))
    try:
        e = B.load_next_sourcing(empty, None, ctx, comps)
        check(e["present"] is False and e["searched"] is None, "a folder without a round file: 'not present', no error")
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    # the fixture results
    r = B.load_round_results(FIX_RES, ctx)
    bs = r["by_slot"]
    check([x["title"] for x in bs.get("living-room/floor-lamp", [])] == ["FIXTURE result linen drum floor lamp", "FIXTURE result paper floor lamp"],
          "results: one file per slot (room--slot.json), best first")
    check("hall/basket" in bs and "bath/shower-curtain" in bs, "results: {records} with room/slot and 'entrance' as the hall")
    check("work/desk-lamp" in bs, "results: {slots: {room/slot: [...]}}")
    check(len(r["unmatched"]) == 2 and "broken.json" in " ".join(r["warnings"]), "results: the unknown slot (a record and a report) and the broken file are reported")
    # the sourcing round's own report shape (the first real file, round-3-results/cj.json)
    rep = r["reports"].get("dining-room/floor-vase") or [{}]
    check(rep[0].get("found") is False and rep[0].get("summary") == "FIXTURE no pass on CJ" and rep[0].get("notable") and rep[0].get("opened") == {"rejected": 1},
          "results: a slot report (found, summary, next, opened, not opened)")
    cus = bs.get("living-room/cushions") or []
    known = next((x for x in cus if x.get("card") == "cushions-cj-boucle-teddy"), {})
    pend = next((x for x in cus if x.get("card_pending")), {})
    check(len(cus) == 2 and abs(known.get("margin", 0) - 0.314) < 1e-9 and known.get("ship_usd") == 6.5 and known.get("ship_days") == [9, 23],
          "results: the report's cards with their numbers (margin, freight) and a link to the card")
    check(pend.get("card_pending") == "fixture-new-card-not-built-yet" and pend.get("passes_40") is True, "results: a card id this build does not see yet is kept as pending")
    fi = next((x for x in r["files"] if x["file"] == "cj-report.json"), {})
    check(fi.get("source") == "cj" and fi.get("points") == 120 and fi.get("queries_run") == 2 and fi.get("queries_not_run") == 1, "results: the file's source, queries and CJ points")
    real = B.NEXT_SOURCING_DIR / f"round-{ns['round']}-results"
    if real.exists():
        rr = B.load_round_results(real, ctx)
        check(not rr["warnings"] and not rr["unmatched"] and rr["n_slots"] > 0, f"results: the real files read cleanly ({rr['n']} products, {rr['n_slots']} slots, {len(rr['files'])} files)")


# --------------------------------------------------------------------------- 2. browser

def build(dist: Path, *extra: str) -> None:
    cmd = [sys.executable, str(STUDIO / "build.py"), "--offline", "--dist", str(dist), *extra]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print("\n".join("    " + l for l in r.stdout.splitlines() if "compositions" in l or "next sourcing" in l or "dist:" in l))
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


def open_page(browser, base, width, scheme, screen, ready, room=None, block_net=True):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, locale="he-IL")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "Failed to load resource" not in m.text else None)
    if block_net:  # fonts, marked and AliExpress images come from other hosts; the page has fallbacks
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    page.add_init_script("try{localStorage.clear()" + (f";localStorage.setItem('studio.room', {json.dumps(json.dumps(room))})" if room else "") + "}catch(e){}")
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


def no_hscroll(page, width, label):
    sw = page.evaluate("document.documentElement.scrollWidth")
    check(sw <= width + 1, f"{label}: no horizontal scroll (scrollWidth {sw})")


def active_id(page):
    return page.evaluate("document.activeElement && document.activeElement.id")


def rooms_checks(browser, base, data):
    comps = data["compositions"]["rooms"]
    lr = comps["living-room"]["nordic"]
    for width in (390, 1280):
        for scheme in ("light", "dark"):
            label = f"rooms {width}px {scheme}"
            print(f"- A, {label}")
            ctx, page, errors = open_page(browser, base, width, scheme, "rooms", ".comp-slot", room="living-room")
            check(page.get_attribute("#rv-compose", "aria-pressed") == "true", f"{label}: the composition is the default view")
            check(page.locator("#room-body .comp-slot").count() == len(lr["slots"]), f"{label}: {len(lr['slots'])} slots")
            chips = page.eval_on_selector_all("#room-body [data-comp-status]", "bs => bs.map(b => [b.dataset.compStatus, +b.querySelector('.n').textContent])")
            want = [["", len(lr["slots"])]] + [[k, lr["counts"][k]] for k in STATUSES]
            check(chips == want, f"{label}: status chips count the slots {chips}")
            check(page.locator("#room-body .comp-whole .tile").count() >= 3 and "2,212" in page.locator("#room-body .comp-whole").inner_text(), f"{label}: whole look with its total")
            check(page.locator("#room-body .comp-check p").count() >= 1, f"{label}: room check")
            cur = page.locator("#comp-living-room--curtains")
            check(cur.locator("button.ptile.is-default[data-product]").count() == 1 and cur.locator(".ptile.is-gap").count() >= 1,
                  f"{label}: curtains: the default card tile, its variation and the missing one")
            check("מרווח" in cur.inner_text() and "ציון" in cur.inner_text() and "₪" in cur.inner_text(), f"{label}: score, price and margin chips")
            no_hscroll(page, width, label)
            axe(page, label, "#screen-rooms")
            # status filter keeps focus and shows only that status
            page.click("#room-body [data-comp-status='on-hold']")
            sts = page.eval_on_selector_all("#room-body .comp-slot", "ls => ls.map(l => l.dataset.status)")
            check(bool(sts) and set(sts) == {"on-hold"} and len(sts) == lr["counts"]["on-hold"], f"{label}: 'on hold' filter ({len(sts)} slots)")
            check(page.evaluate("document.activeElement && document.activeElement.dataset.compStatus") == "on-hold", f"{label}: focus stays on the status chip")
            page.click("#room-body [data-comp-status='']")
            # a card tile opens the product drawer
            page.locator("#room-body button.ptile[data-product]").first.click()
            check(page.locator("#drawer[open]").count() == 1, f"{label}: a card tile opens the product drawer")
            page.keyboard.press("Escape")
            # the old view is kept
            page.click("#rv-plan")
            check(page.locator("#room-body .slots-table").is_visible() and active_id(page) == "rv-plan", f"{label}: 'frames and slots' view still there")
            page.click("#rv-compose")
            # bath: LK1 on an on-hold slot goes to the decisions screen
            page.click("#room-pick [data-room='bath']")
            btn = page.locator("#room-body .comp-slot[data-status='on-hold'] [data-goto-dec='LK1']").first
            check(btn.count() == 1, f"{label}: bath: an on-hold slot shows LK1")
            btn.click()
            page.wait_for_selector("#screen-decisions:not([hidden])")
            page.wait_for_timeout(100)
            check(page.evaluate("(() => { const c = document.activeElement && document.activeElement.closest('.dcard'); return c ? c.dataset.id : null; })()") == "LK1",
                  f"{label}: LK1 opens the decisions screen on its card")
            # from a composition slot to its sourcing slot
            page.goto(base + "#rooms")
            page.wait_for_selector("#screen-rooms:not([hidden]) .comp-slot")
            link = page.locator("#room-body [data-goto-src]").first
            key = link.get_attribute("data-goto-src")
            link.click()
            page.wait_for_selector("#screen-sourcing:not([hidden]) .src-slot")
            page.wait_for_timeout(100)
            check(active_id(page) == "src-" + re.sub(r"[^\w-]+", "--", key) + "-h", f"{label}: 'בליקוט הבא' focuses the slot in the sourcing screen ({key})")
            check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()


def sourcing_checks(browser, base, data):
    ns = data["next_sourcing"]
    for width in (390, 1280):
        for scheme in ("light", "dark"):
            label = f"sourcing {width}px {scheme}"
            print(f"- A, {label}")
            ctx, page, errors = open_page(browser, base, width, scheme, "sourcing", ".src-slot")
            rows = page.eval_on_selector_all("#src-body .src-matrix tbody tr", "rs => rs.map(r => r.dataset.tier)")
            check(rows == [t["id"] for t in ns["tiers"]], f"{label}: a row per tier {rows}")
            tot = page.locator("#src-body .src-matrix tfoot td").last.inner_text().strip()
            check(tot == str(ns["n_queries"]), f"{label}: total {tot} queries")
            check(page.locator("#src-body .src-rules li").count() == len(ns["rules"]), f"{label}: the round's rules")
            n0 = page.locator("#src-body .src-slot").count()
            check(n0 == min(30, len(ns["slots"])) and f"מתוך {len(ns['slots'])} עמדות" in page.locator("#src-body .result-line").inner_text(), f"{label}: the first 30 of {len(ns['slots'])} slots")
            page.click("#sf-more")
            check(page.locator("#src-body .src-slot").count() == min(60, len(ns["slots"])) and active_id(page) == page.locator("#src-body .src-slot").nth(30).locator("h3").get_attribute("id"),
                  f"{label}: 'more' shows 30 more and focuses the first new one")
            page.click("#sf-all")
            check(page.locator("#src-body .src-slot").count() == len(ns["slots"]), f"{label}: 'all' shows all {len(ns['slots'])} slots")
            pr = page.eval_on_selector_all("#src-body .src-slot", "ls => ls.map(l => ({high: 0, medium: 1, low: 2})[l.dataset.priority] ?? 3)")
            check(pr == sorted(pr), f"{label}: sorted by priority")
            first = page.locator("#src-body .src-slot").first
            check("נחיתה לאיזון" in first.inner_text() and "נחיתה למרווח 40%" in first.inner_text() and first.locator(".qlist li").count() >= 1,
                  f"{label}: a slot shows its ceiling and new queries")
            check(page.locator("#src-body .nc-item").count() == len(ns["needs_card"]), f"{label}: needs-card list ({len(ns['needs_card'])})")
            check(page.locator("#src-body .drop-table tbody tr").count() == len(ns["dropped"]), f"{label}: already searched, dropped ({len(ns['dropped'])})")
            lamp = page.locator("#src-living-room--floor-lamp")
            titles = lamp.locator(".res-item .rt").all_inner_texts()
            check(titles[:2] == ["FIXTURE result linen drum floor lamp", "FIXTURE result paper floor lamp"], f"{label}: fixture results in their slot, best first")
            check(page.locator("#src-hall--basket .res-item").count() == 1 and page.locator("#src-work--desk-lamp .res-item").count() == 1, f"{label}: results from every file shape")
            vase = page.locator("#src-dining-room--floor-vase .res-report")
            check(vase.count() == 1 and "FIXTURE no pass on CJ" in vase.inner_text() and "לא נמצא" in vase.inner_text() and "FIXTURE try Israeli stock" in vase.inner_text(),
                  f"{label}: a slot report: not found, summary and next step")
            cush = page.locator("#src-living-room--cushions")
            check(cush.locator(".res-item button[data-product='cushions-cj-boucle-teddy']").count() == 1 and "כרטיס חדש, עוד לא בבנייה" in cush.inner_text(),
                  f"{label}: the report's cards: linked, and a pending one marked")
            check("120 נקודות CJ" in page.locator("#src-body .cmp-src").inner_text(), f"{label}: the results file's CJ points")
            page.check("#sf-res")
            keys = page.eval_on_selector_all("#src-body .src-slot", "ls => ls.map(l => l.dataset.key)")
            check(active_id(page) == "sf-res" and sorted(keys) == sorted(set(data["next_sourcing"]["results"]["by_slot"]) | set(data["next_sourcing"]["results"]["reports"]) & set(s["key"] for s in ns["slots"])),
                  f"{label}: 'only slots with results' ({len(keys)})")
            page.uncheck("#sf-res")
            body = page.locator("#src-body").inner_text()
            check("לא שויכו" in body and "broken.json" in body, f"{label}: unmatched record and broken file reported")
            no_hscroll(page, width, label)
            axe(page, label, "#screen-sourcing")
            # filters keep focus
            page.select_option("#sf-room", "bath")
            rs = page.eval_on_selector_all("#src-body .src-slot", "ls => ls.map(l => l.dataset.room)")
            check(active_id(page) == "sf-room" and bool(rs) and set(rs) == {"bath"}, f"{label}: room filter ({len(rs)} bath slots), focus kept")
            page.select_option("#sf-prio", "high")
            ps = page.eval_on_selector_all("#src-body .src-slot", "ls => ls.map(l => l.dataset.room + '/' + l.dataset.priority)")
            check(active_id(page) == "sf-prio" and bool(ps) and set(ps) == {"bath/high"}, f"{label}: priority filter ({len(ps)})")
            page.click("#sf-reset")
            page.select_option("#sf-src", "cj")
            ss = page.eval_on_selector_all("#src-body .src-slot", "ls => ls.map(l => l.dataset.source)")
            check(active_id(page) == "sf-src" and bool(ss) and set(ss) == {"cj"}, f"{label}: source filter ({len(ss)} CJ slots)")
            page.select_option("#sf-src", "")
            # from a sourcing slot to its composition slot
            link = page.locator("#src-body .src-slot [data-goto-comp]").first
            key = link.get_attribute("data-goto-comp")
            link.click()
            page.wait_for_selector("#screen-rooms:not([hidden]) .comp-slot")
            page.wait_for_timeout(100)
            check(active_id(page) == "comp-" + re.sub(r"[^\w-]+", "--", key) + "-h", f"{label}: 'להרכבה' focuses the slot in the room's composition ({key})")
            check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()


def fixture_comp_checks(browser, base):
    for width in (390, 1280):
        for scheme in ("light", "dark"):
            label = f"fixture compositions {width}px {scheme}"
            print(f"- B, {label}")
            ctx, page, errors = open_page(browser, base, width, scheme, "rooms", ".comp-slot", room="living-room")
            body = page.locator("#room-body")
            lamp = page.locator("#comp-living-room--floor-lamp")
            ae_tile = lamp.locator(".ptile").first
            check(("צריך כרטיס" in ae_tile.inner_text() and ae_tile.locator("a[href*='aliexpress.com/item/1005009294740268']").count() == 1)
                  or ae_tile.evaluate("e => e.matches('button[data-product]')"), f"{label}: an AliExpress record without a card says 'צריך כרטיס' and links to AliExpress")
            check("הכרטיס לא נמצא" in page.locator("#comp-living-room--curtains").inner_text(), f"{label}: a card that does not exist is marked")
            check(page.locator("#comp-living-room--cushions .set-items li").count() == 2, f"{label}: a set lists its items")
            check("רהיט קבוע" in page.locator("#comp-living-room--sofa").inner_text(), f"{label}: a furniture model")
            check("לא בקובץ העמדות" in page.locator("#comp-living-room--no-such-slot").inner_text(), f"{label}: a slot outside the slots file is flagged")
            check("בסיכום של הקובץ" in body.inner_text(), f"{label}: the file's differing counts are shown")
            check(page.locator("#comp-living-room--rug [data-goto-dec='LK1']").count() == 1 and page.locator("#comp-living-room--framed-art [data-goto-dec='PR1']").count() == 1,
                  f"{label}: blocked slots link LK1 and PR1")
            check(page.locator("#comp-living-room--vase [data-goto-dec='VL1']").count() == 1, f"{label}: the lock decision VL1 links")
            no_hscroll(page, width, label)
            axe(page, label, "#screen-rooms")
            page.click("#room-pick [data-room='hall']")
            check("אין עמדות" in body.inner_text() or page.locator("#room-body .comp-slot").count() == 0, f"{label}: a composition without slots renders")
            page.click("#room-pick [data-room='bath']")
            check("אין עדיין הרכבה" in body.inner_text() and page.locator("#room-body .slots-table").count() == 1, f"{label}: a room without a readable composition keeps the old view")
            page.goto(base + "#sourcing")
            page.wait_for_selector("#screen-sourcing:not([hidden]) .src-slot")
            check("תוצאות הסבב עוד לא הגיעו" in page.locator("#src-body").inner_text(), f"{label}: results not here yet")
            check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()


def scroll_all(page):
    """load the lazy images before a full-page screenshot"""
    h = page.evaluate("document.documentElement.scrollHeight")
    for y in range(0, h, 700):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(40)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)


def shots(browser):
    print("- screenshots from the real data (studio/dist)")
    r = subprocess.run([sys.executable, str(STUDIO / "build.py")], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("real build failed")
    srv, base = serve(STUDIO / "dist")
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        jobs = [("rooms", ".comp-slot", "living-room", "rooms-composition", w, s) for w in (390, 1280) for s in ("light", "dark")]
        jobs += [("rooms", ".comp-slot", "bath", "rooms-composition-bath", 390, "light")]
        jobs += [("sourcing", ".src-slot", None, "sourcing", w, s) for w in (390, 1280) for s in ("light", "dark")]
        for screen, ready, room, name, width, scheme in jobs:
            ctx, page, errors = open_page(browser, base, width, scheme, screen, ready, room=room, block_net=False)
            page.wait_for_timeout(600)  # web fonts
            scroll_all(page)
            h = page.evaluate("document.documentElement.scrollHeight")
            max_h = 3200 if width < 600 else 2600
            p = SHOTS / f"{name}-{width}-{scheme}.png"
            page.screenshot(path=str(p), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": min(h, max_h)})
            print(f"    {p.relative_to(ROOT)} ({width}×{min(h, max_h)} of {h})")
            no_hscroll(page, width, f"real data {name} {width}px {scheme}")
            check(not errors, f"real data {name} {width}px {scheme}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()
    finally:
        srv.shutdown()


def main() -> int:
    python_checks()
    tmp = Path(tempfile.mkdtemp(prefix="studio-compose-"))
    dist_a, dist_b = tmp / "a", tmp / "b"
    print("- build A: real compositions and round 3, fixture results")
    build(dist_a, "--round-results-dir", str(FIX_RES))
    print("- build B: fixture compositions, no results")
    build(dist_b, "--compositions-dir", str(FIX_COMP), "--round-results-dir", str(tmp / "no-results"))
    data_a = json.loads((dist_a / "data.json").read_text(encoding="utf-8"))
    srv_a, base_a = serve(dist_a)
    srv_b, base_b = serve(dist_b)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None)
            rooms_checks(browser, base_a, data_a)
            sourcing_checks(browser, base_a, data_a)
            fixture_comp_checks(browser, base_b)
            if "--shots" in sys.argv:
                shots(browser)
            browser.close()
    finally:
        srv_a.shutdown()
        srv_b.shutdown()
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {tmp}")
    print(f"\n{'FAILED' if failures else 'PASSED'}: {len(failures)} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
