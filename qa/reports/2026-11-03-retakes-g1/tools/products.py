"""
G8.6: the products baked into the four retakes, with their liveness state. Sources: docs/render-products-check-2026-11-02.json
(rows per master, replacements, liveness), the two new bath cards (V7Q3), the retake prompts, and framing/round4/plan.json
poses (placeholders). Writes data/products.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

PC = json.load(open(os.path.join(C.REPO, "docs/render-products-check-2026-11-02.json")))
cards = PC["cards"] if isinstance(PC["cards"], dict) else {}
repl = PC["replacement_candidates_checked"]
LIVE = set(PC["checks_summary"].get("liveness_live", []))
NEW = {"floor-planter": ("floor-planter-aliexpress-seagrass-straight-planter-basket-30", "data/products/bath/floor-planter/floor-planter-aliexpress-seagrass-straight-planter-basket-30.json"),
       "toilet-brush": ("toilet-brush-aliexpress-matte-black-steel-cylinder-245996", "data/products/bath/toilet-brush/toilet-brush-aliexpress-matte-black-steel-cylinder-245996.json")}


def liveness(card_id):
    c = cards.get(card_id) or repl.get(card_id) or {}
    lv = c.get("liveness") if isinstance(c, dict) else None
    lv = lv if isinstance(lv, dict) else {}
    state = lv.get("state") or ("live" if card_id in LIVE else "not-checked")
    return state


def master_rows(frame):
    fr = next(x for x in PC["frames"] if x["frame"] == frame)
    rows = []
    for r in fr["rows"]:
        rep = r.get("replacement")
        slot = r["slot"].split(" ")[0]
        if r["verdict"] == "stand-in" or r["card_id"] is None:
            rows.append(dict(slot=slot, card=None, state="stand-in (not for sale)", liveness="n/a"))
            continue
        if r["verdict"] == "replace" and isinstance(rep, dict):
            if rep.get("kind") == "card":
                rows.append(dict(slot=slot, card=rep["card_id"], state="replacement of " + r["card_id"], liveness=liveness(rep["card_id"])))
            else:
                rows.append(dict(slot=slot, card=None, state=f"{rep.get('kind')} ({r['card_id']} out)", liveness="n/a"))
            continue
        rows.append(dict(slot=slot, card=r["card_id"], state=r["verdict"], liveness=liveness(r["card_id"])))
    return rows


def new_card_row(slot):
    cid, path = NEW[slot]
    c = json.load(open(os.path.join(C.REPO, path)))
    sku = next((s for s in c["options"]["skus"] if s.get("in_room")), None)
    return dict(slot=slot, card=cid, state="designer 6.5, test only (V7Q3)", liveness="not-checked",
                note=f"card stock field (seller claim, not a liveness check): {sku.get('stock') if sku else None}; usage_rights {c['images'].get('usage_rights')}; "
                     f"status {c.get('status')}; in_room SKU {sku.get('id') if sku else None}")


out = {}
for sid in C.RETAKES:
    frame, base = C.STILLS[sid][0], C.STILLS[sid][9]
    if sid == "B1 r3":
        rows = master_rows("B1") + [new_card_row("floor-planter"), new_card_row("toilet-brush")]
    elif sid == "B2 r3":
        rows = master_rows("B2") + [new_card_row("floor-planter")]
    else:
        # the pose plan lists the base frame's placeholders; the v8 prompt renders only these (its product lines; the rest "NOT IN FRAME")
        own = master_rows(base)
        ph = {"W0-in": {"basket", "waste-basket", "planter", "shelf-boxes", "desk-organizer"}, "K-girl-0": {"framed-prints", "bookshelf", "bedspread", "doll"}}[frame]
        rows = [r for r in own if r["slot"] in ph]
    baked = [r for r in rows if r["card"]]
    out[sid] = dict(products=rows, baked_cards=len(baked), live=sorted({r["card"] for r in baked if r["liveness"] == "live"}),
                    unverified=sorted({r["card"] for r in baked if r["liveness"] != "live"}))
    print(f"{sid:12s} baked {out[sid]['baked_cards']:2d} live {out[sid]['live']} unverified {len(out[sid]['unverified'])}")
json.dump(out, open(os.path.join(C.OUT, "data", "products.json"), "w"), indent=1, ensure_ascii=False)
