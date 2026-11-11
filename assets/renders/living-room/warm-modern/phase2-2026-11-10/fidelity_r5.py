#!/usr/bin/env python3
"""
fidelity_r5.py: the fidelity numbers of R5 (render-agent, 2026-11-11), on the graded r5 files (the default scene set B, each variant's truth):
colour (median Lab of the product's interior: its final layer's alpha 255 eroded 2 px), against the card hex and, where measured, the SKU
photo; size and place against the card's clay at the plan point (step 0's camera). Writes work-r5/fidelity-r5.json. 0 tokens.
  python3 fidelity_r5.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import fix_r4 as F4  # noqa: E402
import fix_r5 as F5  # noqa: E402
import reserve_r3 as R3  # noqa: E402
import step0_clay_checks as S0  # noqa: E402

LAY, GRD = os.path.join(HERE, "layers"), os.path.join(HERE, "graded")
MAN = json.load(open(os.path.join(LAY, "manifest-r5.json")))
BY = {l_["id"]: l_ for l_ in MAN["layers"]}
VAR = {v["id"]: v for vs in MAN["variants"].values() for v in vs}


def lab8(p):
    return cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def alpha(f):
    return np.asarray(Image.open(os.path.join(LAY, f)))[..., 3]


def summ(LAB, m):
    L, a, b = (float(np.median(LAB[..., i][m])) for i in range(3))
    C = np.hypot(LAB[..., 1], LAB[..., 2])
    return dict(L=round(L, 1), a=round(a, 2), b=round(b, 2), C=round(math.hypot(a, b), 2), h=round(math.degrees(math.atan2(b, a)) % 360, 1),
                C_px_p95=round(float(np.percentile(C[m], 95)), 2), px=int(m.sum()))


def hexlab(h):
    h = h.lstrip("#")
    c = np.array([[[int(h[i:i + 2], 16) for i in (0, 2, 4)]]], np.float32) / 255
    L, a, b = cv2.cvtColor(c, cv2.COLOR_RGB2LAB)[0, 0]
    return dict(L=round(float(L), 1), C=round(float(math.hypot(a, b)), 2), h=round(math.degrees(math.atan2(b, a)) % 360, 1))


def interior(a8, er=2):
    return cv2.erode((a8 == 255).astype(np.uint8), np.ones((2 * er + 1, 2 * er + 1), np.uint8)) > 0


def ring(m, r0=15, r1=40, excl=None):
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    rg = (d >= r0) & (d <= r1)
    return rg & ~excl if excl is not None else rg


def main():
    out = {}
    LB = lab8(os.path.join(GRD, "default-scene-r5-set-B-graded-v3c.png"))
    allp = np.zeros(LB.shape[:2], bool)
    for l_ in MAN["layers"]:
        if "product" in l_:
            allp |= alpha(l_["file"]) > 0
    # the default vase at the clay point
    a = alpha(BY["vase"]["file"])
    m = interior(a)
    ys, xs = np.nonzero(m)
    xc = (xs.min() + xs.max()) / 2
    lit = m & (np.arange(m.shape[1])[None, :] < xc)
    rg = ring(a > 0, excl=allp | (LB[..., 0] > 95) | (LB[..., 0] < 50))
    v = summ(LB, lit)
    pl = summ(LB, rg)
    out["vase"] = dict(card="#EEECE8", card_lab=hexlab("#EEECE8"), lit_half=v, beside_ring_off_glass_and_bronze=pl,
                       targets={"C* median 4-7 on the lit half": dict(value=v["C"], pass_=4 <= v["C"] <= 7),
                                "hue within +-10 deg of the surface beside": dict(value=round((v["h"] - pl["h"] + 180) % 360 - 180, 1),
                                                                                 pass_=abs((v["h"] - pl["h"] + 180) % 360 - 180) <= 10),
                                "not above C 7 (QA's plaster)": dict(value=v["C"], pass_=v["C"] <= 7)},
                       size_place="15.9 x ~31.5 cm; seat on the clay point within 1 px (jobs-r5.json vase_landing_check)")
    # the curtains (default) and the magazine rods, the lamp's wisp: re-measured on the r5 scene
    G8 = np.asarray(Image.open(os.path.join(GRD, "default-scene-r5-set-B-graded-v3c.png")).convert("RGB"))
    mc, rc = F5.qa_curtain_masks()
    out["curtains"] = dict(r5_scene=F5.curtain_measure(G8, mc, rc), photo=dict(L=86.9, C=6.5, h=93.0))
    rods = json.load(open(os.path.join(HERE, "work-r5/fix-r5.json")))["magazine-holder"]
    out["magazine-holder rods"] = dict(fix_record=rods["measured_graded_rod_core"], photo=rods["target"])
    a8l = alpha(BY["floor-lamp"]["file"])
    out["floor-lamp wisp (QA's measure)"] = F5.lamp_wisp_measure(G8, a8l)
    # the planter, whole
    a = alpha(BY["planter"]["file"])
    pot = interior(a)
    pot[:1050] = False
    rgp = ring(a > 0, excl=allp | (LB[..., 0] < 50))
    rgp[:900] = False
    p_ = summ(LB, pot)
    pr = summ(LB, rgp)
    cb = R3.clay_boxes()["pot"]
    w = {y: int((a[y, 930:1130] > 127).sum()) for y in range(990, 1200)}
    rim = next(y for y in range(990, 1200) if w[y] >= 60)
    bot = max(y for y in range(990, 1200) if w[y] > 0)
    out["planter"] = dict(card="#BDB6A8", card_lab=hexlab("#BDB6A8"), pot=p_, wall_and_floor_beside=pr,
                          targets={"C* median <= 6": dict(value=p_["C"], pass_=p_["C"] <= 6),
                                   "darker than the plaster beside (not cream)": dict(value=round(p_["L"] - pr["L"], 1), pass_=p_["L"] < pr["L"])},
                          size_cm=dict(belly=round(42 * max(w.values()) / (cb["right"] - cb["left"]), 1), height=round(35.5 * (bot + 1 - rim) / (cb["bottom"] - cb["top"]), 1)),
                          shape="the card's opening narrower than the belly with a rounded shoulder, vertical ribs on the upper half, a smooth "
                                "speckled band below with a curved boundary (the render); size fixed in code (post-r5.json)")
    # the variants, each on its truth
    for vid, vv in VAR.items():
        LV = lab8(os.path.join(GRD, f"variant-r5-{vid}-set-B-graded-v3c.png"))
        a = alpha(vv["file"])
        m = interior(a)
        rec = dict(card=vv["product"]["card_id"], all=summ(LV, m))
        if vid == "framed-art-v2":
            dark = m & (LV[..., 0] < 35)
            rec["black_shapes"] = dict(summ(LV, dark), target="espresso-black L* 12-22 (scene brief)",
                                       pass_=12 <= float(np.median(LV[..., 0][dark])) <= 22)
            rec["frames"] = "the default's walnut frames (post-r5.json): the same frame in every variant"
        if vid == "vase-v2":
            rec["card_lab"] = hexlab("#3B3A38")
            rec["size_place"] = "W ~23.3 x H 32 cm (card: about 22 x 32); foot centre 672.5 against the point's 672.4; seat row ~1064 against its clay foot edge 1063.8"
        if vid.startswith("accent-sconces"):
            hexc = "#DCC3A2" if vid.endswith("v2") else "#E3D5BE"
            light = m & (LV[..., 0] > 55)
            rec["stone"] = summ(LV, light)
            rec["card_lab"] = hexlab(hexc)
            rec["size"] = ("8 x 16 (+ the side face seen); the right block x0.95 to the card in code" if vid.endswith("v2")
                           else "the card has NO dimensions: scaled x0.82-0.83 in code to the clay from the SKU photo's proportions inside the slot envelope")
        if vid == "curtains-v2":
            mm = cv2.erode((a == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            mm[:100], mm[1400:] = False, False
            G8v = np.asarray(Image.open(os.path.join(GRD, f"variant-r5-{vid}-set-B-graded-v3c.png")).convert("RGB"))
            rec["qa_mask"] = F5.curtain_measure(G8v, mm, ring(mm))
            rec["photo"] = dict(L=87.2, C=6.48, h=92.8)
        if vid == "pendant-v2":
            rec["card_lab"] = hexlab("#F1ECE3")
            ys, xs = np.nonzero(a > 127)
            body = (a > 127).copy()
            body[:198] = False
            bys, bxs = np.nonzero(body)
            _, vb, _ = S0.P(0.20, 1.72, 1.90)
            u0, _, _ = S0.P(0.0, 1.72, 2.02)
            u1, _, _ = S0.P(0.40, 1.72, 2.02)
            wpx = (u1 - u0) * S0.CW / S0.GW * 2720
            rec["size_place"] = dict(lantern_width_px=int(bxs.max() + 1 - bxs.min()), card_40cm_px=round(wpx, 1),
                                     width_cm=round(40 * (bxs.max() + 1 - bxs.min()) / wpx, 1), bottom_row=int(bys.max()),
                                     Z190_row=round((S0.CY + vb * S0.CH) / S0.GH * 1530, 1))
            rec["notes"] = "faint horizontal banding on the paper (partial against the card's smooth pleats); the model's wood sleeve on the cord replaced by the cord in code"
        out[vid] = rec
    json.dump(out, open(os.path.join(HERE, "work-r5/fidelity-r5.json"), "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
