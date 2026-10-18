#!/usr/bin/env python3
"""The Studio's db contract and the data the db documents point at (qa-agent, 2026-10-17).

Written for the QA of 2026-10-17 (assets/qa/studio-qa-2026-10-17.md). Each check below is a finding of that report;
the test fails until frontend-dev (and the card owners) fix them, and then keeps them fixed.

1. Python, no browser:
   - every card id under data/products/** is unique: product_edits/<id> must point at exactly one card (DB-2);
   - apply_edits.py finds every card by its id (its Run.index, the one it writes through): a card whose file name is not
     its id (zendrop-2883892.json, furniture-express-*.json) must still be found, and an id two cards claim is refused (DB-3);
   - every answered decision in status/decisions.json stores `answer` as the page reads it, {option, note, at, by},
     not a bare option string next to answer_text (DB-1);
   - every answer whose option is not one of the decision's options carries a note or answer_text, so the page has
     something to show instead of a raw id.
   With --db DIR (an export of the published page's db: DIR/decisions/<id>.json, then DIR/out/<id>.json written over
   it and DIR/out/<id>-<suffix>.json (-ans, -fix) applied as an update, with {"__delete__": true} removing a field, the
   way the art director syncs):
   - no decision is open in the db while the repo has it answered or applied;
   - no db document stores `answer` as a bare string;
   - WARNING, never a failure (read-only, 2026-10-18): decisions the db has "applied" while the repo still has them
     "answered" (16 on 17.10). No tool syncs a decision's status between the two; the art director aligns
     status/decisions.json. The other drift is printed as info.
2. Browser (the real data built offline into a temp folder, the mock db of smoke_products.py):
   - a decision answered in the repo whose db document is still open (LK1 before the 17.10 sync) is not shown as open,
     and is not in "לאשר את כל ההמלצות הפתוחות" (the bulk approve would overwrite the owner's answer) (DB-4);
   - a db document with a string answer (as VR1 was in the db before the 17.10 sync; when no such answer is left, one is
     made from an answered decision) shows the answer text, never "function at()";
   - read-only (no db): the same decision from data.json shows its answer text, and so does a data.json whose answer is
     a bare string next to answer_text (the old repo shape);
   - a product_edits document marked synced (QA 2026-10-17, M8): synced before the build, its fields no longer override
     the repo (the card shows the repo's price and "סונכרן", not "ממתין לסנכרון"); synced after the build, the db's value
     stays until the next build (also "סונכרן"); not synced, the db's value and "ממתין לסנכרון";
   - no JavaScript errors.

Usage:  python3 studio/tests/smoke_db_contract.py [--db DIR] [--keep]
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import types
import tempfile
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_products as T  # noqa: E402  (shared helpers: build, serve, open_page, the mock db)

ROOT = T.ROOT
check = T.check
UI_FIELDS = ("_src", "_rooms", "_order")
warnings: list[str] = []


def warn(ok: bool, what: str) -> None:
    """A finding that is reported, never a failure (the test stays read-only and green)."""
    print(("  ok    " if ok else "  WARN  ") + what, flush=True)
    if not ok:
        warnings.append(what)


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else None


def apply_edits_run():
    """studio/apply_edits.py's Run on the repo, read-only: its index is the one an edit is written through."""
    spec = importlib.util.spec_from_file_location("apply_edits_test", ROOT / "studio" / "apply_edits.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    args = types.SimpleNamespace(dry_run=True, no_move=True, all=False, force=False)
    return m.Run(ROOT, args)


def repo_decisions() -> dict:
    return {d["id"]: d for d in json.loads((ROOT / "status" / "decisions.json").read_text(encoding="utf-8"))["decisions"]}


def option_of(a):
    return a.get("option") if isinstance(a, dict) else a


# --------------------------------------------------------------------------- 1. python

def python_checks():
    print("- cards: ids and the sync index")
    by_id = defaultdict(list)
    for f in sorted((ROOT / "data" / "products").rglob("*.json")):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # a broken card is a finding of its own
            check(False, f"{f.relative_to(ROOT)} parses ({e})")
            continue
        by_id[c.get("id") or f.stem].append(f)
    dups = {k: v for k, v in by_id.items() if len(v) > 1}
    check(not dups, f"every card id is unique ({len(by_id)} ids)" + "".join(
        f"\n        {k}: " + ", ".join(str(p.relative_to(ROOT)) for p in v) for k, v in sorted(dups.items())))
    run = apply_edits_run()
    lost = sorted(k for k, v in by_id.items() if len(v) == 1 and run.index.get(k) != v[0])
    check(not lost, f"apply_edits.py finds every card by its id ({len(lost)} cannot be synced; "
          f"{sum(1 for k, v in by_id.items() if v[0].stem != k)} file names are not the id)" + "".join(
        f"\n        {k} ({by_id[k][0].relative_to(ROOT)})" for k in lost))
    check(set(run.dup_ids) == set(dups), f"apply_edits.py knows the duplicate ids and refuses them ({sorted(run.dup_ids)})")

    print("- status/decisions.json: the answer as the page reads it")
    dec = repo_decisions()
    strings = sorted(i for i, d in dec.items() if isinstance(d.get("answer"), str))
    check(not strings, f"every answer is {{option, note, at, by}}, not a bare string ({len(strings)}: {', '.join(strings)})")
    bare = []
    for i, d in sorted(dec.items()):
        a = d.get("answer")
        if a is None:
            continue
        ids = {o.get("id") for o in d.get("options") or []}
        if option_of(a) not in ids and not ((isinstance(a, dict) and str(a.get("note") or "").strip()) or str(d.get("answer_text") or "").strip()):
            bare.append(i)
    check(not bare, f"an answer outside the options carries a note or answer_text ({', '.join(bare) or 'none'})")


def _update(doc: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if isinstance(v, dict) and v.get("__delete__") is True:
            doc.pop(k, None)
        else:
            doc[k] = v
    return doc


def load_db(folder: Path) -> dict:
    """The db as the art director left it: the export, then out/<id>.json (whole documents), then out/<id>-<suffix>.json
    (updates: -ans, -fix, ...) in name order. A decision id may contain a dash (FR-A): an update is a file whose name
    minus its last "-word" is a known document."""
    db = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((folder / "decisions").glob("*.json"))}
    out = folder / "out"
    if out.is_dir():
        files = sorted(out.glob("*.json"))
        whole, updates = [], []
        for f in files:
            base, _, suffix = f.stem.rpartition("-")
            (updates if base and suffix.isalpha() and suffix.islower() and (base in db or (out / f"{base}.json").exists()) else whole).append((base, f))
        for _, f in whole:
            db[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        for base, f in updates:
            _update(db.setdefault(base, {}), json.loads(f.read_text(encoding="utf-8")))
    return db


def db_checks(folder: Path):
    print(f"- the db export in {folder}")
    db, dec = load_db(folder), repo_decisions()
    check(set(db) >= set(dec), f"every repo decision is in the db ({len(dec)} repo, {len(db)} db; missing: {sorted(set(dec) - set(db))})")
    stale = sorted(i for i, d in dec.items() if i in db and (d.get("status") or "open") != "open" and (db[i].get("status") or "open") == "open")
    check(not stale, f"no decision is open in the db while the repo has it answered ({', '.join(stale) or 'none'})")
    strings = sorted(i for i, d in db.items() if isinstance(d.get("answer"), str))
    check(not strings, f"no db document stores the answer as a bare string ({', '.join(strings) or 'none'})")
    # the db ahead of the repo: applied there, answered here (QA 2026-10-17 §3, 16 decisions). A warning, not a failure
    ahead = sorted(i for i in dec if i in db and (dec[i].get("status") or "open") == "answered" and db[i].get("status") == "applied")
    warn(not ahead, f"no decision is 'applied' in the db and 'answered' in the repo ({len(ahead)} pairs"
         + (f": {', '.join(ahead)}; align status/decisions.json" if ahead else "") + ")")
    drift = sorted(f"{i} repo {dec[i].get('status')} / db {db[i].get('status')}" for i in dec
                   if i in db and (dec[i].get("status") or "open") != (db[i].get("status") or "open") and i not in ahead)
    print(f"  info  other status drift between the repo and the db: {len(drift)}" + "".join(f"\n        {x}" for x in drift))


# --------------------------------------------------------------------------- 2. browser

def answered_with_string(dec: dict) -> dict | None:
    """A decision whose answer is a bare option string next to answer_text; when none is left (the 17.10 sync), one is
    made from an answered decision with a note, in the old shape, so the page is still tested against it."""
    found = next((d for d in dec.values() if isinstance(d.get("answer"), str) and str(d.get("answer_text") or "").strip()), None)
    if found:
        return found
    src = next((d for d in dec.values() if isinstance(d.get("answer"), dict) and str(d["answer"].get("note") or "").strip()
                and d["answer"].get("option") not in {o.get("id") for o in d.get("options") or []}), None) \
        or next((d for d in dec.values() if isinstance(d.get("answer"), dict) and str(d["answer"].get("note") or "").strip()), None)
    if not src:
        return None
    a = src["answer"]
    old = {k: v for k, v in src.items() if k != "answer"}
    old.update({"answer": a.get("option") or "", "answer_text": a["note"], "answered": str(a.get("at") or "")[:10] or None})
    return old


def answered_in_repo(dec: dict) -> dict | None:
    return next((d for d in dec.values() if d.get("status") == "answered" and isinstance(d.get("answer"), dict)
                 and any(o.get("recommended") for o in d.get("options") or [])
                 and option_of(d["answer"]) not in {o["id"] for o in d["options"] if o.get("recommended")}), None) \
        or next((d for d in dec.values() if d.get("status") == "answered"), None)


def browser_checks(browser, base):
    dec = repo_decisions()
    s_dec, r_dec = answered_with_string(dec), answered_in_repo(dec)
    if not s_dec or not r_dec:
        print("  skip  no decision with a string answer / answered in the repo")
        return
    sid, rid = s_dec["id"], r_dec["id"]
    seed = {"decisions": {
        sid: {k: v for k, v in s_dec.items() if k not in UI_FIELDS},                       # as the art director seeded it
        rid: dict({k: v for k, v in r_dec.items() if k not in UI_FIELDS + ("answer", "answer_text", "answered")}, status="open"),
    }}
    print(f"- live db: {rid} answered in the repo but open in the db; {sid} with a string answer")
    ctx, page, errors = T.open_page(browser, base, 1280, screen="decisions", ready=".dcard", seed=seed)
    page.wait_for_selector("#dec-status .db-dot.live", timeout=10000)
    st = page.evaluate(f"""() => {{ const c = document.querySelector('.dcard[data-id={json.dumps(rid)}]');
        return c ? [...c.classList].find(x => x.startsWith('is-')) : null; }}""")
    check(st != "is-open", f"{rid}: answered in the repo, not shown as open because the db doc is still open ({st})")
    page.evaluate("() => { const b = document.getElementById('bulk-open'); if(b) b.click(); }")
    bulk = page.evaluate("() => [...document.querySelectorAll('#dec-confirm li code')].map(e => e.textContent)")
    check(rid not in bulk, f"{rid}: not in the bulk approve list ({len(bulk)} in the list)")
    text = s_dec.get("answer_text", "")
    shown = answer_text(page, sid)
    check(text[:20] in shown and "function" not in shown, f"{sid}: the db's string answer shows its text ('{shown[:80]}')")
    check(not page.evaluate("document.getElementById('dec-list').textContent.includes('function at')"), "live db: no decision card says 'function at()'")
    check(not errors, "live db: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()

    print(f"- read-only (no db): {sid} from data.json")
    ctx, page, errors = T.open_page(browser, base, 390, screen="decisions", ready=".dcard", db=False)
    shown = answer_text(page, sid)
    check(text[:20] in shown, f"{sid}: the answer text is shown read-only ('{shown[:80]}')")
    check(not page.evaluate("document.getElementById('dec-list').textContent.includes('function at')"), "read-only: no decision card says 'function at()'")
    check(not errors, "read-only: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()


def old_shape_checks(browser, dist: Path, tmp: Path):
    """data.json from a repo that still stores answers as a bare string next to answer_text (before the 17.10 sync)."""
    dec = repo_decisions()
    s_dec = answered_with_string(dec)
    if not s_dec:
        print("  skip  no answered decision with a note")
        return
    sid = s_dec["id"]
    print(f"- read-only, the old repo shape in data.json: {sid} with answer '{s_dec['answer']}' and answer_text")
    d2 = tmp / "old-shape"
    shutil.copytree(dist, d2)
    data = json.loads((d2 / "data.json").read_text(encoding="utf-8"))
    for it in data["decisions"]["items"]:
        if it["id"] == sid:
            it.update({k: s_dec[k] for k in ("answer", "answer_text", "answered")})
    (d2 / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    srv, base = T.serve(d2)
    try:
        ctx, page, errors = T.open_page(browser, base, 1280, screen="decisions", ready=".dcard", db=False)
        shown = answer_text(page, sid)
        check(s_dec["answer_text"][:20] in shown and "function" not in shown, f"{sid}: a bare string answer shows answer_text ('{shown[:80]}')")
        check(not errors, "old shape: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
        ctx.close()
    finally:
        srv.shutdown()


def synced_checks(browser, base, dist: Path):
    """QA 2026-10-17, M8: a product_edits document marked synced stops overriding the repo once the build is newer."""
    data = T.load_build().read_dist_data(dist)
    built = data["build"]["built_at"]
    econ = (data.get("economics") or {}).get("products") or {}
    shown = {p["id"] for p in data["products"] if p.get("slot_key")}
    ids = [k for k, v in sorted(econ.items()) if k in shown and isinstance(v.get("retail_ils"), (int, float)) and v["retail_ils"] > 20][:3]
    if len(ids) < 3:
        print("  skip  fewer than 3 cards with a price in the build")
        return
    old, new, pend = ids
    seed = {"product_edits": {
        old: {"fields": {"economics": {"retail_ils": econ[old]["retail_ils"] + 11}}, "history": [], "synced": True,
              "synced_at": "2026-10-01", "updated_at": "2026-09-30T10:00:00Z"},
        new: {"fields": {"economics": {"retail_ils": econ[new]["retail_ils"] + 13}}, "history": [], "synced": True,
              "synced_at": "2999-01-01T00:00:00Z", "updated_at": "2999-01-01T00:00:00Z"},
        pend: {"fields": {"economics": {"retail_ils": econ[pend]["retail_ils"] + 17}}, "history": [], "synced": False,
               "updated_at": "2026-10-18T05:00:00Z"},
    }}
    print(f"- synced product edits (M8), build {built}: {old} synced 1.10, {new} synced after the build, {pend} not synced")
    ctx, page, errors = T.open_page(browser, base, 1280, screen="products", ready=".pcard", seed=seed)
    page.wait_for_function(f"() => !!document.querySelector('.pcard-w[data-pid={json.dumps(pend)}] .chip-pending')", timeout=10000)

    def state(pid):
        return page.evaluate(f"""() => {{ const c = document.querySelector('.pcard-w[data-pid={json.dumps(pid)}]'); if(!c) return null;
            const pr = c.querySelector('.pprice .num');
            return {{price: pr ? pr.textContent.replace(/[^0-9.]/g, '') : '', src: c.dataset.retailSrc, synced: c.dataset.synced || '',
                     chip: !!c.querySelector('.chip-synced'), pending: !!c.querySelector('.chip-pending')}}; }}""")
    a, b, c = state(old), state(new), state(pend)
    want = lambda pid, d: str(round(econ[pid]["retail_ils"] + d))
    check(a and a["price"] == want(old, 0) and a["src"] != "studio" and a["chip"] and not a["pending"] and a["synced"] == "stale",
          f"{old}: synced before the build, the repo's price shows (₪{want(old, 0)}, not ₪{want(old, 11)}) with 'סונכרן' ({a})")
    check(b and b["price"] == want(new, 13) and b["src"] == "studio" and b["chip"] and not b["pending"] and b["synced"] == "live",
          f"{new}: synced after the build, the db's price stays until the next build, with 'סונכרן' ({b})")
    check(c and c["price"] == want(pend, 17) and c["src"] == "studio" and c["pending"] and not c["chip"],
          f"{pend}: not synced, the db's price and 'ממתין לסנכרון' ({c})")
    exp = json.loads(page.evaluate("exportJson()"))
    check(sorted(x["id"] for x in exp["product_edits"]) == [pend], f"the sync file holds only the edit that is not synced ({[x['id'] for x in exp['product_edits']]})")
    check(not errors, "synced edits: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()


def answer_text(page, did) -> str:
    return page.evaluate(f"""() => {{ const b = document.querySelector('.dcard[data-id={json.dumps(did)}] .answer-box');
        return b ? b.textContent.replace(/\\s+/g, ' ').trim() : ''; }}""")


def main() -> int:
    python_checks()
    db = arg("--db")
    if db:
        db_checks(Path(db))
    tmp = Path(tempfile.mkdtemp(prefix="studio-dbc-"))
    try:
        print("- build with the real data")
        try:
            T.build(tmp / "dist", None)
            built = True
        except SystemExit as e:
            check(False, f"the real data builds ({e})")
            built = False
        if built:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=T.CHROMIUM if Path(T.CHROMIUM).exists() else None)
                srv, base = T.serve(tmp / "dist")
                try:
                    browser_checks(browser, base)
                    synced_checks(browser, base, tmp / "dist")
                finally:
                    srv.shutdown()
                old_shape_checks(browser, tmp / "dist", tmp)
                browser.close()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {tmp}")
    print(f"\n{'FAILED' if T.failures else 'PASSED'}: {len(T.failures)} failed checks"
          + (f", {len(warnings)} warning{'s' if len(warnings) > 1 else ''} (reported, not a failure)" if warnings else ""))
    return 1 if T.failures else 0


if __name__ == "__main__":
    sys.exit(main())
