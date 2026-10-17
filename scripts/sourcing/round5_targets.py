"""Targets for the massive sourcing round to 80% per style (owner, 2026-10-17; studio-rules ז).

Reads coverage.json (run final_round_coverage.py first), the per-style gap packs, and every results file.
For each slot that is still short in some style, writes one target with:
  - the styles that need it and how many options each still needs;
  - the slot spec, the designer's spec, queries and price ceiling per style (from the packs);
  - the unused candidates already found for it: fit >= 7 for a needing style but no card, with the blocker
    (loss at the slot price / outside the envelope / unpriced / thin margin), so they are re-priced, not re-searched;
  - the team (group) that owns it.
Also writes, per style, how many more covered slots it needs to reach 80%.

  python3 scripts/sourcing/round5_targets.py      # -> data/leads/final-2026-10-13/round5/targets.json
"""
import collections, glob, json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
D = "data/leads/final-2026-10-13"
STYLES = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
TARGET = 0.80
STORAGE_A = {"bath", "hall", "corridor"}


def group(slot, category):
    room = slot.split("/")[0]
    if category == "storage-function":
        return "storage-bath-hall-corridor" if room in STORAGE_A else "storage-rooms"
    return category or "other"


def blocker(c, st):
    m = c.get("margin_pct")
    if isinstance(m, dict):
        m = m.get(st)
    if m is None:
        m = c.get("margin_at_slot_price_pct")
        if isinstance(m, dict):
            m = m.get(st)
    if c.get("type_ok") is False:
        return "type"
    if c.get("fits_envelope") in (False, "no"):
        return "envelope"
    if c.get("decision") == "loss" or (isinstance(m, (int, float)) and m < 0):
        return "loss_at_slot_price"
    if m is None:
        return "unpriced"
    if m < 40:
        return "below_40"
    return "not_chosen"


def main():
    cov = json.load(open(f"{D}/coverage.json"))
    packs = {st: {g["slot"]: g for g in json.load(open(f"{D}/{st}.json"))["gaps"]} for st in STYLES}
    unused = collections.defaultdict(list)
    for f in sorted(glob.glob(f"{D}/results/*.json")):
        if os.path.basename(f).startswith("il-"):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for key, s in (d.get("slots") or {}).items():
            for c in s.get("candidates") or []:
                if not isinstance(c, dict) or c.get("card_id"):
                    continue
                unused[key].append((os.path.basename(f), c))
    targets = {}
    for st in STYLES:
        for g in cov["remaining"][st]:
            t = targets.setdefault(g["slot"], {"slot": g["slot"], "category": g["category"], "priority": g["priority"],
                                               "group": group(g["slot"], g["category"]), "styles": {}, "spec": None,
                                               "per_style": {}, "already_searched_aliexpress": set(), "unused_candidates": []})
            t["styles"][st] = {"have_ready": g["have_ready"], "need": g["need"]}
            p = packs[st].get(g["slot"]) or {}
            if p and not t["spec"]:
                t["spec"] = {k: p.get(k) for k in ("name_he", "placement", "envelope_cm", "set_of", "electrical", "safety")}
            t["per_style"][st] = {"designer_spec_he": p.get("designer_spec_he"), "designer_queries": p.get("designer_queries"),
                                  "price_ceiling": p.get("price_ceiling"),
                                  "existing_picks": [{k: e.get(k) for k in ("card_id", "name", "title", "url") if e.get(k)}
                                                     for e in p.get("existing_picks") or []]}
            t["already_searched_aliexpress"] |= set(p.get("already_searched_aliexpress") or [])
            if g["priority"] == "high" or t["priority"] not in ("high",):
                t["priority"] = g["priority"] if g["priority"] == "high" else t["priority"]
    for key, t in targets.items():
        seen = set()
        for fname, c in unused.get(key, []):
            fit = c.get("style_fit_guess") or {}
            needing = [st for st in t["styles"] if isinstance(fit.get(st), (int, float)) and fit[st] >= 7]
            if not needing or (c.get("source"), c.get("id")) in seen:
                continue
            seen.add((c.get("source"), c.get("id")))
            t["unused_candidates"].append({
                "file": f"{D}/results/{fname}", "source": c.get("source"), "id": c.get("id"), "url": c.get("url"),
                "title": c.get("title"), "image": c.get("image"), "styles": needing,
                "blocker": blocker(c, needing[0]), "margin_pct": c.get("margin_pct"), "landed_ils": c.get("landed_ils"),
                "slot_price_ils": c.get("slot_price_ils"), "fits_envelope": c.get("fits_envelope"), "dims_cm": c.get("dims_cm"),
                "why_he": c.get("why_he")})
        t["already_searched_aliexpress"] = sorted(t["already_searched_aliexpress"])
        t["closes_styles"] = len(t["styles"])
        t["partial"] = sum(1 for v in t["styles"].values() if v["have_ready"] > 0)
    short = {}
    for st, c in cov["styles"].items():
        goal = math.ceil(TARGET * c["eligible"])
        short[st] = {"eligible": c["eligible"], "covered_ready": c["covered_ready"], "goal_80": goal,
                     "more_needed": max(0, goal - c["covered_ready"])}
    rank = {"high": 0, "medium": 1, "low": 2}
    order = sorted(targets.values(), key=lambda t: (rank.get(t["priority"], 3), -t["closes_styles"], -t["partial"], t["slot"]))
    groups = collections.Counter(t["group"] for t in order)
    os.makedirs(f"{D}/round5", exist_ok=True)
    out = {"date": cov["date"], "target_pct_per_style": int(TARGET * 100), "metric": "pct_ready, 3 options per slot",
           "shortfall": short, "groups": dict(groups), "targets": order}
    json.dump(out, open(f"{D}/round5/targets.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(short, ensure_ascii=False))
    print(dict(groups), "targets", len(order), "unused candidates",
          sum(len(t["unused_candidates"]) for t in order))


if __name__ == "__main__":
    main()
