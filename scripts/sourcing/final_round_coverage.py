"""Coverage of the final sourcing round (owner, 2026-10-13: at least 90% of slots before the site).

A slot counts for a style when it has 3 options for that style:
  existing picks (packs: `have`) + new cards from the round with a style fit guess >= 7 (CJ, Zendrop, AliExpress results)
  "ready"  = dropship cards only;  "any" = also Israeli-shop products with fit >= 7 (need a trade price before sale).
Eligible slots: every non-furniture slot in data/slots, minus Nordic on-hold slots (blocked by a decision).

  python3 scripts/sourcing/final_round_coverage.py              # writes coverage.json / coverage.md
  python3 scripts/sourcing/final_round_coverage.py --merge-index # also merges CJ/Zendrop queries into searched-index.json
"""
import glob, json, os, sys, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
D = "data/leads/final-2026-10-13"
STYLES = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
FIT = 7.0
NAMES = {"nordic": "נורדי", "warm-modern": "מודרני חם", "japandi": "ג'פנדי", "mediterranean": "ים-תיכוני",
         "modern-country": "כפרי מודרני", "boho": "בוהו"}


def eligible():
    out = set()
    for f in glob.glob("data/slots/*.json"):
        if "filler" in f:
            continue
        d = json.load(open(f))
        room = os.path.basename(f)[:-5]
        sl = d["slots"] if isinstance(d["slots"], list) else list(d["slots"].values())
        out |= {f"{room}/{s['id']}" for s in sl if s.get("kind") != "fixed-product"}
    return out


def on_hold():
    out = set()
    for f in glob.glob("data/compositions/*-nordic-2026-10-11.json"):
        d = json.load(open(f))
        out |= {f"{d['room']}/{k}" for k, v in d["slots"].items() if v.get("status") == "on-hold"}
    return out


VARIANT_AXES = {"color", "style", "pattern", "print"}


def card_variants():
    """card id -> how many look variants it offers (colour / print / style values), capped at 3 (rule ג.3, 2026-10-13)."""
    out = {}
    for f in glob.glob("data/products/**/*.json", recursive=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        cid = d.get("id") or os.path.basename(f)[:-5]
        n = 1
        for a in ((d.get("options") or {}).get("axes") or []):
            if a.get("id") in VARIANT_AXES:
                n = max(n, len(a.get("values") or []))
        out[cid] = min(3, n)
        out.setdefault(os.path.basename(f)[:-5], min(3, n))
    return out


def results():
    cards = collections.defaultdict(lambda: collections.defaultdict(dict))  # style -> slot -> {card id: fitting colour variants or None}
    il = collections.defaultdict(lambda: collections.defaultdict(set))      # style -> slot -> product urls
    queries = {"cj": set(), "zendrop": set()}
    for f in glob.glob(f"{D}/results/*.json"):
        try:
            d = json.load(open(f))
        except Exception as e:
            print("skip (invalid JSON):", f, e, file=sys.stderr)
            continue
        is_il = os.path.basename(f).startswith("il-")
        for key, s in (d.get("slots") or {}).items():
            queries["cj"] |= set(s.get("queries_cj") or [])
            queries["zendrop"] |= set(s.get("queries_zendrop") or [])
            for c in (s.get("products") if is_il else s.get("candidates")) or []:
                fit = c.get("style_fit_guess") or {}
                for st in STYLES:
                    try:
                        ok = float(fit.get(st) or 0) >= FIT
                    except (TypeError, ValueError):
                        ok = False
                    if not ok:
                        continue
                    if is_il:
                        il[st][key].add(c.get("url") or c.get("title"))
                    elif c.get("card_id"):
                        vf = (c.get("variants_fit") or {}).get(st)
                        prev = cards[st][key].get(c["card_id"])
                        cards[st][key][c["card_id"]] = max(x for x in (vf, prev, 0) if x is not None) or None
    return cards, il, queries


def main():
    elig, hold = eligible(), on_hold()
    cards, il, queries = results()
    var = card_variants()
    cov = {"date": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "fit_threshold": FIT, "styles": {}, "remaining": {}}
    tot = collections.Counter()
    for st in STYLES:
        pack = json.load(open(f"{D}/{st}.json"))
        gaps = {g["slot"]: g for g in pack["gaps"]}
        slots = sorted(s for s in elig if not (st == "nordic" and s in hold))
        ready = anyc = partial = one_ready = one_any = 0
        remaining = []
        for s in slots:
            g = gaps.get(s)
            if not g:
                ready += 1; anyc += 1; one_ready += 1; one_any += 1
                continue
            have_ids = [p.get("card_id") for p in g.get("existing_picks") or [] if p.get("card_id")]
            have_var = sum(var.get(c, 1) for c in have_ids) + (g["have"] - len(have_ids))
            n_ready = max(g["have"], have_var) + sum(min(3, n) if n else var.get(c, 1) for c, n in cards[st].get(s, {}).items() if c not in have_ids)
            n_any = n_ready + len(il[st].get(s, ()))
            ready += n_ready >= 3
            anyc += n_any >= 3
            one_ready += n_ready >= 1
            one_any += n_any >= 1
            if n_ready < 3:
                partial += n_ready > 0
                remaining.append({"slot": s, "have_ready": n_ready, "have_with_il": n_any, "need": 3 - n_ready,
                                  "priority": g.get("priority"), "category": g.get("category")})
        n = len(slots)
        cov["styles"][st] = {"eligible": n, "covered_ready": ready, "covered_any": anyc, "partial_ready": partial,
                             "pct_ready": round(100 * ready / n, 1), "pct_any": round(100 * anyc / n, 1),
                             "one_ready": one_ready, "one_any": one_any,
                             "pct_one_ready": round(100 * one_ready / n, 1), "pct_one_any": round(100 * one_any / n, 1)}
        cov["remaining"][st] = remaining
        tot["eligible"] += n; tot["ready"] += ready; tot["any"] += anyc; tot["one_ready"] += one_ready; tot["one_any"] += one_any
    cov["total"] = {"eligible": tot["eligible"], "covered_ready": tot["ready"], "covered_any": tot["any"],
                    "pct_ready": round(100 * tot["ready"] / tot["eligible"], 1), "pct_any": round(100 * tot["any"] / tot["eligible"], 1),
                    "pct_one_ready": round(100 * tot["one_ready"] / tot["eligible"], 1), "pct_one_any": round(100 * tot["one_any"] / tot["eligible"], 1),
                    "target_pct": 90, "target_metric": "pct_ready (3 options per slot, colours count)"}
    json.dump(cov, open(f"{D}/coverage.json", "w"), ensure_ascii=False, indent=1)
    lines = [f"# כיסוי הסבב האחרון ({cov['date']})", "",
             "עמדה מכוסה בסגנון = 3 אפשרויות: בחירות קיימות + כרטיסים חדשים בהתאמה 7+ (\"מוכן\"). צבע או הדפס של אותו מוצר נספר כאפשרות (ג.3, 2026-10-13), עד 3 לכרטיס. \"כולל ישראל\" = גם מוצרי חנויות ישראליות (דורש מחיר סוחר). היעד: 90% עם 3 אפשרויות (2026-10-14).", "",
             "| סגנון | עמדות | 3 אפשרויות, מוכן | 3 אפשרויות, כולל ישראל | לפחות אחת, מוכן | לפחות אחת, כולל ישראל |", "| --- | --- | --- | --- | --- | --- |"]
    for st, c in cov["styles"].items():
        lines.append(f"| {NAMES[st]} | {c['eligible']} | {c['pct_ready']}% | {c['pct_any']}% | {c['pct_one_ready']}% | {c['pct_one_any']}% |")
    t = cov["total"]
    lines.append(f"| **סה\"כ** | {t['eligible']} | **{t['pct_ready']}%** | **{t['pct_any']}%** | **{t['pct_one_ready']}%** | **{t['pct_one_any']}%** |")
    open(f"{D}/coverage.md", "w").write("\n".join(lines) + "\n")
    if "--merge-index" in sys.argv:
        p = "data/leads/next-sourcing/searched-index.json"
        idx = json.load(open(p))
        before = len(idx["cj_queries"])
        idx["cj_queries"] = sorted(set(idx["cj_queries"]) | queries["cj"])
        idx["zendrop_queries"] = sorted(set(idx.get("zendrop_queries") or []) | queries["zendrop"])
        idx["updated"] = cov["date"]
        json.dump(idx, open(p, "w"), ensure_ascii=False, indent=1)
        print(f"searched-index: cj {before} -> {len(idx['cj_queries'])}, zendrop {len(idx['zendrop_queries'])}")
    print(json.dumps({k: (v["pct_ready"], v["pct_any"], v["pct_one_ready"], v["pct_one_any"]) for k, v in cov["styles"].items()}, ensure_ascii=False))
    print("total", t)


if __name__ == "__main__":
    main()
