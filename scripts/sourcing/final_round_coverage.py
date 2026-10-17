"""Coverage of the final sourcing round (owner, 2026-10-13: at least 90% of slots before the site).

A slot counts for a style when it has 3 options for that style:
  existing picks (packs: `have`) + new cards from the round with a style fit guess >= 7 (CJ, Zendrop, AliExpress results)
  "ready"  = dropship cards only;  "any" = also Israeli-shop products with fit >= 7 (need a trade price before sale).
Eligible slots: every non-furniture slot in data/slots, minus Nordic on-hold slots (blocked by a decision).

  python3 scripts/sourcing/final_round_coverage.py              # writes coverage.json / coverage.md
  python3 scripts/sourcing/final_round_coverage.py --merge-index # also merges CJ/Zendrop queries into searched-index.json
"""
import glob, json, os, re, sys, collections, datetime

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
# Axes the options mapper could not name ("other", "finish", "set") still carry colours on 31 cards
# (e.g. "Dark German Gray", "Large Size Palegreen"). Count only the values that read as a colour.
COLOUR_AXES = {"other", "finish", "set"}
COLOUR_WORD = re.compile(r"(white|black|gr[ae]y|beige|khaki|cream|ivory|brown|green|blue|pink|red|yellow|orange|purple|natural|"
                         r"oat|sand|camel|caramel|coffee|olive|sage|navy|rust|terracotta|linen|jute|hemp|dune|mustard|ginger|lemon|"
                         r"wine|charcoal|taupe|\btan\b|walnut|\boak\b|teal|mint|lilac|apricot|peach|glaze|colou?r|turmeric|celadon|milk|"
                         r"\btea\b|primary|bleach)", re.I)


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
            vals = a.get("values") or []
            if a.get("id") in VARIANT_AXES:
                n = max(n, len(vals))
            elif a.get("id") in COLOUR_AXES:
                k = sum(1 for v in vals if COLOUR_WORD.search(str(v.get("label_src") or v.get("label_he") or v.get("id") or "")))
                if k >= 2:
                    n = max(n, k)
        out[cid] = min(3, n)
        out.setdefault(os.path.basename(f)[:-5], min(3, n))
    return out


def card_listing():
    """card id -> the supplier listing it was cut from ("aliexpress:<item>", "cj:<pid>"). Card copies made for another room
    ("-master", "-work", "-hall") and size twins of one listing are the same product: they count once per slot."""
    out = {}
    for f in glob.glob("data/products/**/*.json", recursive=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        cid = d.get("id") or os.path.basename(f)[:-5]
        u = (d.get("supplier") or {}).get("product_url") or ""
        m = re.findall(r"(\d{10,}|[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})", u)
        src = "aliexpress" if "aliexpress" in u else "cj" if "cjdropshipping" in u else "zendrop" if "zendrop" in u else "card"
        out[cid] = f"{src}:{m[-1]}" if m else f"card:{cid}"
        out.setdefault(os.path.basename(f)[:-5], out[cid])
    return out


def audits():
    """card id -> the master-designer's audit entry (round*/designer-audit*.json, 2026-10-17). Its verdict and scores
    override the team's guess: "reject" drops the card from the count; otherwise its fit and variants_fit replace the
    team's values for the styles it scored."""
    out = {}
    for f in sorted(glob.glob(f"{D}/round*/designer-audit*.json")):
        for c in json.load(open(f)).get("cards") or []:
            out[c["card_id"]] = c
    return out


def results():
    audit = audits()
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
                a = audit.get(c.get("card_id")) if not is_il else None
                if a:
                    if a.get("verdict") == "reject":
                        continue
                    fit = {**fit, **(a.get("fit") or {})}
                    c = {**c, "variants_fit": {**(c.get("variants_fit") or {}), **(a.get("variants_fit") or {})}}
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
                        if vf == 0:
                            vf = 1  # "no extra colour fits" means the card itself, not "unknown" (which falls back to every axis)
                        prev = cards[st][key].get(c["card_id"])
                        cards[st][key][c["card_id"]] = max(x for x in (vf, prev, 0) if x is not None) or None
    return cards, il, queries


def main():
    elig, hold = eligible(), on_hold()
    cards, il, queries = results()
    var = card_variants()
    lst = card_listing()

    def options(g, st, s):
        """Options for a gap slot: one per supplier listing (its colours, capped at 3), plus picks without a card."""
        have_ids = [p.get("card_id") for p in g.get("existing_picks") or [] if p.get("card_id")]
        groups, picks_in = collections.defaultdict(int), collections.Counter()
        for c in have_ids:
            L = lst.get(c, f"card:{c}")
            picks_in[L] += 1
            groups[L] = max(groups[L], var.get(c, 1))
        for c, n in cards[st].get(s, {}).items():
            if c not in have_ids:
                L = lst.get(c, f"card:{c}")
                groups[L] = max(groups[L], min(3, n) if n else var.get(c, 1))
        return sum(min(3, max(v, picks_in[L])) for L, v in groups.items()) + (g["have"] - len(have_ids))

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
            n_ready = options(g, st, s)
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
        if st == "nordic" and hold:
            # Report only: the Nordic on-hold slots (compositions 2026-10-11) as if they were open gaps with no picks.
            held = sorted(s for s in elig if s in hold)
            h_ready = sum(options({"have": 0, "existing_picks": []}, st, s) >= 3 for s in held)
            cov["styles"][st].update({"on_hold": len(held), "on_hold_already_covered": h_ready,
                                      "pct_ready_incl_on_hold": round(100 * (ready + h_ready) / (n + len(held)), 1)})
        cov["remaining"][st] = remaining
        tot["eligible"] += n; tot["ready"] += ready; tot["any"] += anyc; tot["one_ready"] += one_ready; tot["one_any"] += one_any
    cov["total"] = {"eligible": tot["eligible"], "covered_ready": tot["ready"], "covered_any": tot["any"],
                    "pct_ready": round(100 * tot["ready"] / tot["eligible"], 1), "pct_any": round(100 * tot["any"] / tot["eligible"], 1),
                    "pct_one_ready": round(100 * tot["one_ready"] / tot["eligible"], 1), "pct_one_any": round(100 * tot["one_any"] / tot["eligible"], 1),
                    "target_pct": 90, "target_metric": "pct_ready (3 options per slot, colours count)"}
    json.dump(cov, open(f"{D}/coverage.json", "w"), ensure_ascii=False, indent=1)
    lines = [f"# כיסוי הסבב האחרון ({cov['date']})", "",
             "עמדה מכוסה בסגנון = 3 אפשרויות: בחירות קיימות + כרטיסים חדשים בהתאמה 7+ (\"מוכן\"). צבע או הדפס של אותו מוצר נספר כאפשרות (ג.3, 2026-10-13), עד 3 לכרטיס. \"כולל ישראל\" = גם מוצרי חנויות ישראליות (דורש מחיר סוחר). היעד: 90% עם 3 אפשרויות (2026-10-14). כרטיס שעבר ביקורת מעצב (round*/designer-audit.json) נספר לפי הציון של המעצב, וכרטיס שנדחה לא נספר.", "",
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
