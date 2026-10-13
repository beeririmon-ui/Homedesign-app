"""The final comprehensive sourcing round (owner, 2026-10-13): one work pack per style.

For every style (nordic + the five catalog styles) and every non-furniture slot in data/slots/<room>.json,
the slot is a gap when it has fewer than 3 picks for that style:
  - nordic: data/compositions/<room>-nordic-2026-10-11.json (skips ready-to-lock and on-hold)
  - others: data/catalog/<style>-2026-10-12.json picks
Each gap carries the slot spec, the slot's Israeli-value price and price ceilings (Studio formula), the
style spec and queries the designers wrote (round 3 for nordic, round 4 for the styles), the existing picks,
and every query already run for that slot (searched-index.json), so no search runs twice.
Writes data/leads/final-2026-10-13/<style>.json and data/leads/final-2026-10-13/index.json.
"""
import glob, json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "data/leads/final-2026-10-13"
STYLES = ["nordic", "warm-modern", "japandi", "mediterranean", "modern-country", "boho"]
IDX = json.load(open("data/leads/next-sourcing/searched-index.json"))
R3 = {s["slot"]: s for s in json.load(open("data/leads/next-sourcing/round-3-2026-10-11.json"))["slots"]}
R4 = {(s["style"], s["slot"]): s for s in json.load(open("data/leads/next-sourcing/round-4-styles-2026-10-12.json"))["slots"]}
PRICE = {}
for f in glob.glob("/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/compose/*.json"):
    try:
        for s in json.load(open(f)).get("slots") or []:
            PRICE[s["key"]] = s.get("slot_price_ils_median")
    except Exception:
        pass


def ceilings(p):
    if not p:
        return None
    net = p / 1.18
    fee = 0.02 * p + 1.2
    return {"slot_price_ils": p, "breakeven_landed_ils": round(0.92 * net - fee, 1), "landed_for_40_ils": round(0.52 * net - fee, 1)}


def slots_of(room):
    d = json.load(open(f"data/slots/{room}.json"))
    sl = d["slots"] if isinstance(d["slots"], list) else list(d["slots"].values())
    return [s for s in sl if s.get("kind") != "fixed-product"]


ROOMS = sorted(os.path.basename(f)[:-5] for f in glob.glob("data/slots/*.json") if "filler" not in f)
nordic = {}
for f in glob.glob("data/compositions/*-nordic-2026-10-11.json"):
    d = json.load(open(f))
    for sid, s in d["slots"].items():
        nordic[f"{d['room']}/{sid}"] = s
cat = {st: json.load(open(f"data/catalog/{st}-2026-10-12.json")) for st in STYLES[1:]}
index = {"round": "final", "date": "2026-10-13", "styles": {}}
for st in STYLES:
    gaps = []
    for room in ROOMS:
        for s in slots_of(room):
            key = f"{room}/{s['id']}"
            if st == "nordic":
                c = nordic.get(key) or {}
                if c.get("status") in ("ready-to-lock", "on-hold"):
                    continue
                picks = ([c["default"]] if c.get("default") else []) + list(c.get("variations") or [])
                design = R3.get(key) or {}
            else:
                cs = ((cat[st]["rooms"].get(room) or {}).get("slots") or {}).get(s["id"]) or {}
                picks = cs.get("picks") or []
                design = R4.get((st, key)) or {}
            if len(picks) >= 3:
                continue
            p = (design.get("price_ceiling") or {}).get("slot_price_ils") or PRICE.get(key)
            gaps.append({
                "slot": key, "name_he": s.get("name_he"), "category": s.get("category"), "placement": s.get("placement"),
                "envelope_cm": s.get("envelope_cm") or design.get("envelope_cm"), "set_of": s.get("set_of"),
                "electrical": s.get("electrical"), "safety": s.get("safety"),
                "have": len(picks), "need": 3 - len(picks),
                "existing_picks": [{k: x.get(k) for k in ("card_id", "ae_item_id", "style_score", "score", "price_ils") if x.get(k) is not None} for x in picks],
                "priority": design.get("priority") or "medium",
                "designer_spec_he": design.get("spec_he"), "designer_source_type": design.get("source_type"),
                "designer_queries": design.get("queries") or [],
                "price_ceiling": design.get("price_ceiling") or ceilings(p),
                "already_searched_aliexpress": IDX["aliexpress_queries_by_slot"].get(key, []),
            })
    pri = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: (pri.get(str(g["priority"]).lower(), 1), g["slot"]))
    pack = {"round": "final", "style": st, "date": "2026-10-13",
            "brief": f"docs/design-bible/{'nordic.md' if st == 'nordic' else st + '-brief-draft.md'}",
            "catalog": "data/compositions/<room>-nordic-2026-10-11.json" if st == "nordic" else f"data/catalog/{st}-2026-10-12.json",
            "already_searched_cj_global": IDX["cj_queries"], "gaps": gaps}
    json.dump(pack, open(f"{OUT}/{st}.json", "w"), ensure_ascii=False, indent=1)
    c = collections.Counter(g["priority"] for g in gaps)
    index["styles"][st] = {"gaps": len(gaps), "need_total": sum(g["need"] for g in gaps), "by_priority": dict(c),
                           "with_designer_queries": sum(1 for g in gaps if g["designer_queries"])}
json.dump(index, open(f"{OUT}/index.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(index["styles"], ensure_ascii=False, indent=1))
