#!/usr/bin/env python3
"""Smoke test for answering decisions in the Studio (2026-10-13): writeAnswer() and the decisions/<id> docs.

The Studio is built from the real data (offline) and opened with the mock db of smoke_products.py, which behaves like the
real db: update() rejects invalid_argument when the document does not exist, set() creates or replaces it.

1. A decision that is in the db (seeded by the art director): picking an option, writing a note and saving in the card
   writes update() with {status:"answered", answer:{option, note, at, by}} only; the other fields of the doc are kept,
   and no UI field (_src, _rooms, _order) gets into the db.
2. A decision that is only in data.json (status/decisions.json, not seeded): its card can be answered, and saving writes
   set(), which creates the doc with the decision's own fields (id, title, question, options, ...) plus the answer,
   without _src, _rooms and _order, and no error is shown. After the snapshot the card shows the answer from the db.
3. The mock itself: update() on a missing doc rejects invalid_argument, as the real db does (so the old bug would show).
4. No JavaScript errors.

Usage:  python3 studio/tests/smoke_decisions.py [--keep]
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_products as T  # noqa: E402  (shared helpers: build, serve, open_page, the mock db)

check = T.check
UI_FIELDS = ("_src", "_rooms", "_order")


def pick_decisions(dist: Path) -> tuple[dict, dict]:
    """Two open decisions with at least two options from the built data.json: one to seed, one left static-only."""
    items = json.loads((dist / "data.json").read_text(encoding="utf-8"))["decisions"]["items"]
    usable = [d for d in items if (d.get("status") or "open") == "open" and len(d.get("options") or []) >= 2]
    if len(usable) < 2:
        raise SystemExit(f"need two open decisions with options in data.json ({len(usable)})")
    return usable[0], usable[1]


def answer_in_card(page, did, option, note):
    card = page.locator(f".dcard[data-id='{did}']")
    card.locator(f"input[type=radio][value='{option}']").check()
    card.locator("textarea").fill(note)
    card.locator("[data-save]").click()
    # done = saved and the card is idle again, or the card shows an error (then the checks below fail with its text)
    page.wait_for_function(f"""() => {{ const c = document.querySelector('.dcard[data-id={json.dumps(did)}]');
        if(c && c.querySelector('.save-state.err')) return true;
        const b = c && c.querySelector('[data-save]');
        return (window.__db.decisions[{json.dumps(did)}] || {{}}).status === 'answered' && b && !b.disabled; }}""", timeout=8000)
    err = card.locator(".save-state.err")
    check(err.count() == 0, f"{did}: saved without an error in the card" + ("" if not err.count() else f" ({err.inner_text()})"))
    return page.evaluate(f"window.__db.decisions[{json.dumps(did)}] || {{}}")


def writes(page, did):
    return [w["op"] for w in page.evaluate("window.__dbLog") if w["path"] == f"decisions/{did}"]


def answer_ok(ans, option, note):
    return (ans.get("option") == option and ans.get("note") == note and ans.get("by") == "smoke-user"
            and str(ans.get("at") or "").endswith("Z") and set(ans) == {"option", "note", "at", "by"})


def browser_checks(browser, base, seeded: dict, static: dict):
    sid, tid = seeded["id"], static["id"]
    seed_doc = {k: v for k, v in seeded.items() if k not in UI_FIELDS}
    seed_doc.update({"status": "open", "FIXTURE_db_only": "kept"})   # a field only the db doc has: update must keep it
    ctx, page, errors = T.open_page(browser, base, 1280, screen="decisions", ready=".dcard", seed={"decisions": {sid: seed_doc}})
    page.wait_for_selector(f".dcard[data-id='{sid}'] [data-save]", timeout=10000)
    check(page.locator("#dec-status .db-dot.live").count() == 1 and page.evaluate(f"!({json.dumps(tid)} in window.__db.decisions)"),
          f"db is live with {sid} seeded and {tid} only in data.json")
    check(page.locator(f".dcard[data-id='{tid}'] [data-save]").count() == 1, f"{tid}: the static-only card can be answered")

    # 1. a doc that exists: update() with the answer only, as before
    print(f"- {sid}: a decision that is in the db")
    s_opt = seeded["options"][1]["id"]
    doc = answer_in_card(page, sid, s_opt, "  FIXTURE note on the seeded one  ")
    check(writes(page, sid) == ["update"], f"{sid}: one update(), no set() ({writes(page, sid)})")
    check(answer_ok(doc.get("answer") or {}, s_opt, "FIXTURE note on the seeded one"),
          f"{sid}: answer = {{option, note (trimmed), at, by}} ({doc.get('answer')})")
    check(doc.get("FIXTURE_db_only") == "kept" and doc.get("title") == seeded.get("title") and doc.get("options") == seeded.get("options"),
          f"{sid}: the doc's other fields are kept")
    check(not any(k in doc for k in UI_FIELDS), f"{sid}: no UI field in the db doc ({[k for k in UI_FIELDS if k in doc]})")

    # 2. a decision only in data.json: set() creates the doc from its own fields plus the answer
    print(f"- {tid}: a decision that is only in data.json")
    t_opt = static["options"][0]["id"]
    doc = answer_in_card(page, tid, t_opt, " FIXTURE note on the static one ")
    check(writes(page, tid) == ["set"], f"{tid}: one set(), no update() ({writes(page, tid)})")
    check(doc.get("status") == "answered", f"{tid}: status answered ({doc.get('status')})")
    check(answer_ok(doc.get("answer") or {}, t_opt, "FIXTURE note on the static one"),
          f"{tid}: answer = {{option, note (trimmed), at, by}} ({doc.get('answer')})")
    own = {k: v for k, v in static.items() if k not in UI_FIELDS and k not in ("status", "answer")}
    differ = [k for k, v in own.items() if doc.get(k) != v]
    check(not differ and doc.get("id") == tid and "title" in own and "question" in own and "options" in own,
          f"{tid}: the decision's own fields are in the doc ({len(own)}: {', '.join(sorted(own))}{'; differ: ' + str(differ) if differ else ''})")
    check(not any(k in doc for k in UI_FIELDS), f"{tid}: no UI field in the db doc ({[k for k in UI_FIELDS if k in doc]})")
    card = page.locator(f".dcard[data-id='{tid}']")
    label = next(o["label"] for o in static["options"] if o["id"] == t_opt)
    shown = page.evaluate(f"() => {{ const b = document.querySelector('.dcard[data-id={json.dumps(tid)}] .answer-box'); return !!b && b.textContent.includes({json.dumps(label)}); }}")
    check(shown and card.locator(".chip.st-answered").count() >= 1, f"{tid}: the card shows the answer from the db ({label})")
    check((page.evaluate(f"window.__db.decisions[{json.dumps(sid)}].answer") or {}).get("option") == s_opt, f"{sid}: untouched by the second answer")

    # 3. the mock behaves like the real db, so the old update-only code fails here
    code = page.evaluate("""async () => (await window.claude.use('db')).collection('decisions').doc('FIXTURE-missing')
        .update({status: 'answered'}).then(() => 'resolved', e => e && e.code)""")
    check(code == "invalid_argument", f"mock db: update() on a missing doc rejects invalid_argument ({code})")

    check(not errors, "no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="studio-decisions-"))
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=T.CHROMIUM if Path(T.CHROMIUM).exists() else None)
            print("- build with the real data")
            T.build(tmp / "dist", None)
            seeded, static = pick_decisions(tmp / "dist")
            srv, base = T.serve(tmp / "dist")
            try:
                browser_checks(browser, base, seeded, static)
            finally:
                srv.shutdown()
            browser.close()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {tmp}")
    print(f"\n{'FAILED' if T.failures else 'PASSED'}: {len(T.failures)} failed checks")
    return 1 if T.failures else 0


if __name__ == "__main__":
    sys.exit(main())
