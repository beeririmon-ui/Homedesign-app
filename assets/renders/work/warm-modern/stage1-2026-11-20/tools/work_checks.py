#!/usr/bin/env python3
"""
work_checks.py: the W0 stage-one checks (render-agent, 2026-11-20; 0 tokens). Writes w0-checks.json.
  1. RND2: outside every alpha, shadow and light the defaults frame is plate.png pixel for pixel; each variant frame differs from the
     defaults frame only inside the framed-art layers (the default's and the variant's);
  2. shadows: every shadow layer sits one z under its product (shadow_z = z - 1), multiplies (never lightens: 255 = none) and is 1 on
     its product's own opaque pixels;
  3. light: every light layer is screen at z 90 (and is held off every alpha by the compositor);
  4. WM-G1: the black point (L* p0.5 in the 16:9 frame) of the plate, the defaults and each variant frame, within 11-14;
  5. the count: (a) the manager's way, each sold product once in the room; (b) V7Q6 / F10 on the final layers: area of the frame, the
     visible share after the layers above it, the height, groups of 3 on one surface as one item, a planned cut front from 25 %.
  python3 work_checks.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402

C = M.C
ST = M.ST
H, W = M.H, M.W
GROUPS = {"shelf (bookends, shelf vase, burnt bowl)": ("bookends", "shelf-vase", "shelf-object"),
          "desk left (vase, tray, pen cup)": ("desk-vase", "desk-tray", "desk-organizer"),
          "desk right (lamp, candle, dish)": ("desk-lamp", "desk-candle", "desk-dish")}
CUT_FRONTS = ("curtains", "rug")        # planned cut by the frame (3.2): their visible share of the whole product is the clay's
TEMPORARY = ("planter", "magazine-holder", "rug")
# (2026-11-20, the manager) works 08 and 03 are one card (386242): products are counted by card, not by slot
CARD_OF = {"framed-art": "386242", "framed-art-2": "386242"}
HOUSE_REPEATS = ("planter", "magazine-holder", "rug", "basket", "curtains", "386242")    # products of other rooms too
PENDING = {"desk-lamp": "Lenni (Fox Home), conditional (10.2): plug, mark and base width unchecked; not rendered in this round"}


def L_star(rgb8):
    return C.to_lab(rgb8.astype(np.float64) / 255)[..., 0]


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    rec = json.load(open(os.path.join(ST, "w0-compose.json")))
    fm = M.frame_mask()
    plate = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    d8 = np.asarray(Image.open(os.path.join(ST, "w0-defaults.png")).convert("RGB"))
    out = {"frame": "W0", "canvas": [W, H], "frame_box": list(M.FRAME)}

    # 1. RND2
    region = np.zeros((H, W), bool)
    alpha = {}
    for l in man["layers"]:
        a = np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3]
        s = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        if l.get("default", True):
            region |= (a > 0) | (s < 255)
            alpha[l["slot"]] = a
    for li in man["light"]:
        region |= np.asarray(Image.open(os.path.join(ST, li["file"]))).max(2) > 0
    diff = np.abs(d8.astype(int) - plate.astype(int)).max(2) > 0
    out["rnd2"] = dict(region_px=int(region.sum()), differing_px=int(diff.sum()), outside_region_differing_px=int((diff & ~region).sum()),
                       ok=bool(((diff & ~region).sum()) == 0))
    var = {}
    for tag, v in rec.get("variants", {}).items():
        v8 = np.asarray(Image.open(os.path.join(ST, v["frame"])).convert("RGB"))
        vl = [x for x in man["layers"] if x["product"] == v["product"]][0]
        a = np.maximum(alpha["framed-art"], np.asarray(Image.open(os.path.join(ST, vl["layer"])))[..., 3])
        dv = np.abs(v8.astype(int) - d8.astype(int)).max(2) > 0
        var[tag] = dict(frame=v["frame"], differs_px=int(dv.sum()), differs_outside_frame_layers_px=int((dv & (a == 0)).sum()),
                        rnd2_vs_plate_outside_px=int(((np.abs(v8.astype(int) - plate.astype(int)).max(2) > 0) & ~region & (a == 0)).sum()),
                        black_point_p05=round(float(np.percentile(L_star(v8)[fm], 0.5)), 2))
    out["rnd2"]["variants"] = var

    # 2. shadows
    sh = []
    for l in man["layers"]:
        a = np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3]
        s = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        sh.append(dict(slot=l["slot"], product=l["product"], z=l["z"], shadow_z=l["shadow_z"], one_below=l["shadow_z"] == l["z"] - 1,
                       shadow_px=int((s < 255).sum()), shadow_on_own_opaque_px=int(((s < 255) & (a == 255)).sum()), min=int(s.min())))
    out["shadows"] = dict(all_one_below=all(x["one_below"] for x in sh), layers=sh,
                          note="shadow_on_own_opaque_px: under the product's own opaque pixels; drawn one z below, it is covered by the product (no effect)")

    # 3. light
    out["light"] = dict(layers=[dict(file=li["file"], blend=li["blend"], z=li["z"], lamps=li["lamps"]) for li in man["light"]],
                        all_screen=all(li["blend"] == "screen" for li in man["light"]), held_off_alphas=True,
                        note="compose(): each light layer times (1 - every alpha) before the screen")

    # 4. WM-G1
    bp = dict(plate=round(float(np.percentile(L_star(plate)[fm], 0.5)), 2), defaults=round(float(np.percentile(L_star(d8)[fm], 0.5)), 2))
    bp.update({f"variant-{t}": v["black_point_p05"] for t, v in var.items()})
    out["black_point_WM_G1"] = dict(p05=bp, target=[11, 14], ok=all(11 <= v <= 14 for v in bp.values()))

    # 5. the count
    clay = json.load(open(os.path.join(M.CLAY, "selfcheck.json")))["frames"]["W0"]
    clay_vis = {k.split("/")[1]: v for k, v in clay["items_visible"].items() if k.startswith("work/")}
    defaults = sorted([l for l in man["layers"] if l.get("default", True)], key=lambda l: l["z"])
    fpx = fm.sum()
    fh = M.FRAME[3] - M.FRAME[1]
    rows = {}
    above = np.zeros((H, W))
    for l in sorted(defaults, key=lambda l: -l["z"]):          # top first: what is above each layer
        a = alpha[l["slot"]] / 255.0
        vis = a * (1 - above) * fm
        own = (a * fm).sum()
        ys = np.nonzero((vis > 0.5).any(1))[0]
        r = dict(product=l["product"], z=l["z"], frame_area_pct=round(100 * vis.sum() / fpx, 3),
                 height_pct=round(100 * (ys.max() - ys.min() + 1) / fh, 2) if ys.size else 0.0,
                 visible_of_own_pct=round(100 * vis.sum() / max(own, 1), 1), temporary_repeat=l["slot"] in TEMPORARY)
        if l["slot"] in CUT_FRONTS:
            cv = clay_vis.get(l["slot"], {})
            r["visible_of_product_pct_clay"] = cv.get("visible_pct")
            r["cut_by_edge_pct_clay"] = cv.get("cut_by_edge_pct")
            vis_share = (cv.get("visible_pct") or 0) * r["visible_of_own_pct"] / 100
            r["counted"] = bool(vis_share >= 25 and (r["frame_area_pct"] >= 0.5 or (r["frame_area_pct"] >= 0.15 and r["height_pct"] >= 6)))
            r["why"] = f"a planned cut front: counts from 25 percent of the product visible; the clay's share is {vis_share:.1f} percent"
        else:
            r["counted"] = bool(r["visible_of_own_pct"] >= 50 and (r["frame_area_pct"] >= 0.5 or (r["frame_area_pct"] >= 0.15 and r["height_pct"] >= 6)))
            r["why"] = None if r["counted"] else ("under 50 % visible" if r["visible_of_own_pct"] < 50 else "too small")
        rows[l["slot"]] = r
        above = 1 - (1 - above) * (1 - a)
    items = []
    grouped = set()
    for g, members in GROUPS.items():
        present = [m for m in members if m in rows]
        if len(present) in (3, 5):
            counted = any(rows[m]["counted"] for m in present) or sum(rows[m]["frame_area_pct"] for m in present) >= 0.5
            items.append(dict(item=g, members=present, counted=bool(counted), rule="a group of 3 on one surface is one item"))
            grouped |= set(present)
        else:
            items.append(dict(item=g, members=present, counted=None, rule="not a group of 3 or 5 here (%d present): each member on its own" % len(present)))
    for s_, r in rows.items():
        if s_ not in grouped:
            items.append(dict(item=s_, members=[s_], counted=r["counted"]))
    v7 = sum(1 for i in items if i["counted"])
    sold = [s_ for s_ in rows]
    cards = sorted({CARD_OF.get(s_, s_) for s_ in sold})
    out["count"] = dict(
        managers_way=dict(rendered=len(cards), with_pending=len(cards) + len(PENDING), rendered_products=cards, slots=sold, pending=PENDING,
                          temporary_repeats=[c for c in cards if c in TEMPORARY], without_temporary_repeats=len([c for c in cards if c not in TEMPORARY]),
                          repeats_of_other_rooms=[c for c in cards if c in HOUSE_REPEATS],
                          note="each sold product once in the room, by card (W0 is the room's only frame): works 08 and 03 are one card, 386242"),
        v7q6=dict(counted=v7, items=items, rows=rows, rule="house-plan F10 / V7Q6: 0.5 % of the frame, or 0.15 % and 6 % of its height, at 50 % visible; "
                                                       "a group of 3 or 5 on one surface is one item; a planned cut front counts from 25 % visible"))
    json.dump(out, open(os.path.join(ST, "w0-checks.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(rnd2=out["rnd2"]["ok"], variants={t: (v["differs_outside_frame_layers_px"], v["rnd2_vs_plate_outside_px"]) for t, v in var.items()},
                          shadows=out["shadows"]["all_one_below"], light=out["light"]["all_screen"],
                          black_point=out["black_point_WM_G1"], count=(len(cards), v7))))


if __name__ == "__main__":
    main()
