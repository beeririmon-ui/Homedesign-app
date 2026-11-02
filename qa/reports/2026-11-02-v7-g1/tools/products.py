"""
G8.6: the products baked into every v7 frame and pose, with their liveness state.
Sources: docs/render-products-check-2026-11-02.json (rows per master frame, replacements, liveness), the v7 prompt headers
(assets/prompts/recipe-v5.nordic/<frame>-v7.txt: the swaps applied), framing/round4/plan.json poses (placeholders + also_visible).
Writes data/products.json.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

PC = json.load(open(os.path.join(C.REPO, "docs/render-products-check-2026-11-02.json")))
cards = PC["cards"] if isinstance(PC["cards"], dict) else {}
repl = PC["replacement_candidates_checked"]
PROMPT = {"M0": "m0", "D1": "d1", "D2": "d2", "H0": "h0", "C0": "c0", "MB0": "mb0", "K-boy": "k-boy", "K-girl": "k-girl", "B1": "b1", "B2": "b2", "W0": "w0"}
POSE_BASE = {"H0x": "H0", "H0e": "H0", "M0p": "M0", "M0x": "M0", "PD-35": "D1", "W0-in": "W0", "S1'": "C0", "K-boy-0": "K-boy", "K-girl-0": "K-girl", "CB-0": "B1", "MB-in": "MB0"}
POSE_KEY = {"S1'": "S1prime"}
ROOM_OF = {"living": "M0", "kitchen-dining": "D1", "hall": "H0", "corridor": "C0", "master": "MB0", "boy": "K-boy", "girl": "K-girl", "bath": "B1", "work": "W0"}


LIVE = set(PC["checks_summary"].get("liveness_live", []))


def liveness(card_id):
    c = cards.get(card_id) or repl.get(card_id) or {}
    lv = c.get("liveness") if isinstance(c, dict) else None
    lv = lv if isinstance(lv, dict) else {}
    state = lv.get("state") or ("live" if card_id in LIVE else "not-checked")
    return state, lv.get("how") or lv.get("why_he") or ("docs/render-products-check-2026-11-02.json checks_summary.liveness_live" if card_id in LIVE else "in the liveness queue (no CJ_API_KEY; AliExpress in another session)")


def master_rows(f):
    fr = next(x for x in PC["frames"] if x["frame"] == f)
    rows = []
    for r in fr["rows"]:
        rep = r.get("replacement")
        slot = r["slot"]
        if r["verdict"] == "stand-in" or r["card_id"] is None:
            rows.append(dict(slot=slot, card=None, state="stand-in (not for sale)", vista_only=bool(r.get("vista_only")), liveness="n/a"))
            continue
        if r["verdict"] == "replace" and isinstance(rep, dict):
            if rep.get("kind") == "card":
                rows.append(dict(slot=slot, card=rep["card_id"], state="replacement of " + r["card_id"], vista_only=bool(r.get("vista_only")),
                                 liveness=liveness(rep["card_id"])[0], liveness_how=liveness(rep["card_id"])[1], sku=rep.get("sku")))
            elif rep.get("kind") == "leave-empty":
                rows.append(dict(slot=slot, card=None, state="explicitly empty (" + r["card_id"] + " out)", vista_only=bool(r.get("vista_only")), liveness="n/a"))
            elif rep.get("kind") == "stand-in":
                rows.append(dict(slot=slot, card=None, state="stand-in rug (" + r["card_id"] + " out)", vista_only=bool(r.get("vista_only")), liveness="n/a"))
            continue
        rows.append(dict(slot=slot, card=r["card_id"], state=r["verdict"], vista_only=bool(r.get("vista_only")), liveness=liveness(r["card_id"])[0],
                         liveness_how=liveness(r["card_id"])[1], render_sku=r.get("render_sku")))
    # the prompt header may name a different SKU (M0 line i-l: the charcoal cushion 30x50, not the card's 50x50)
    pf = os.path.join(C.REPO, f"assets/prompts/recipe-v5.nordic/{PROMPT[f]}-v7.txt")
    head = [l for l in open(pf).read().splitlines() if l.startswith("#")]
    notes = [l for l in head if re.search(r"SKU|not the card|STAND-IN|replac", l)]
    return rows, notes


out = {}
for f in C.MASTERS:
    rows, notes = master_rows(f)
    baked = [r for r in rows if r["card"]]
    out[f] = dict(kind="master", products=rows, baked_cards=len(baked), live=[r["card"] for r in baked if r["liveness"] == "live"],
                  unverified=[r["card"] for r in baked if r["liveness"] != "live"], prompt_notes=notes[:6])
for p in C.POSES:
    base = POSE_BASE[p]
    key = POSE_KEY.get(p, p)
    pl = C.PLAN["poses"][key]
    own = out[base]["products"]
    also = pl.get("also_visible", [])
    extra = []
    for s in also:
        room, slot = s.split("/", 1)
        mf = ROOM_OF[room]
        for r in out[mf]["products"]:
            if r["slot"] == slot and r not in extra:
                extra.append(dict(r, from_frame=mf))
    allp = own + extra
    baked = [r for r in allp if r["card"]]
    out[p] = dict(kind="pose", base=base, products_of_base=len(own), also_visible=also, products=allp, baked_cards=len(baked),
                  live=sorted({r["card"] for r in baked if r["liveness"] == "live"}), unverified=sorted({r["card"] for r in baked if r["liveness"] != "live"}),
                  note="a pose bakes the base frame's products plus the neighbouring-room products the plan lists as visible; which of them the pose really shows is read on the sheet")
json.dump(out, open(os.path.join(C.OUT, "data", "products.json"), "w"), indent=1, ensure_ascii=False)
allcards = sorted({r["card"] for v in out.values() for r in v["products"] if r["card"]})
live = sorted({c for c in allcards if liveness(c)[0] == "live"})
print("unique baked cards", len(allcards), "live", live)
for f, v in out.items():
    print(f"{f:9s} baked {v['baked_cards']:2d} live {len(v['live'])} unverified {len(v['unverified'])}")
