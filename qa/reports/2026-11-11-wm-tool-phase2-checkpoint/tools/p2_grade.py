#!/usr/bin/env python3
"""
qa-agent 2026-11-11: is every product layer under ONE v3c grade (not ungraded, not graded twice)?
The v3c grade is a per-pixel function of colour outside the bench slab (gain, toe under L* 25, shoulder). Learn it on the approved pair
(phase-1 ungraded shell-furniture-v3.png -> layers/base.png, outside masks/stone-wide.png) as dL*(L*_ungraded) in 0.25 bins, then for each
product's interior (alpha 255, eroded 2 px, no other layer's alpha) compare its ungraded source (the registered render or the ungraded step
composite) to its layer: residual = (L_layer - L_src) - curve(L_src). A missing grade shows as -lift in the toe, a double grade as +lift.
Writes data/grade.json.   ~/.venvs/motion/bin/python -I p2_grade.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}


def L_of(rgb01):
    return cv2.cvtColor(rgb01.astype(np.float32), cv2.COLOR_RGB2LAB)


u = np.asarray(Image.open(os.path.join(P1, "shell-furniture-v3.png")).convert("RGB")).astype(np.float32) / 255
g = np.asarray(Image.open(os.path.join(P2, "layers/base.png")).convert("RGB")).astype(np.float32) / 255
stone = np.asarray(Image.open(os.path.join(P1, "masks/stone-wide.png")).convert("L")) > 127
Lu, Lg = L_of(u), L_of(g)
m = ~stone
bins = np.arange(0, 100.25, 0.25)
idx = np.clip(np.digitize(Lu[..., 0][m], bins) - 1, 0, len(bins) - 2)
dL = (Lg[..., 0] - Lu[..., 0])[m]
curve = np.full(len(bins) - 1, np.nan)
spread = np.full(len(bins) - 1, np.nan)
for i in range(len(bins) - 1):
    s = dL[idx == i]
    if s.size >= 20:
        curve[i] = np.median(s)
        spread[i] = np.percentile(np.abs(s - curve[i]), 95)
ok = ~np.isnan(curve)
xc = (bins[:-1] + bins[1:]) / 2
curve_f = np.interp(xc, xc[ok], curve[ok])
res = dict(curve_samples={f"{x:.1f}": round(float(np.interp(x, xc, curve_f)), 3) for x in (5, 8, 10, 12, 15, 20, 25, 30, 50, 80, 88, 92, 95, 98)},
           base_pair_p95_abs_dev_in_bins_median=round(float(np.nanmedian(spread)), 3))

src = {
    "rug": ("png", "work/layers/rug.png"), "vase": ("png", "work/layers/vase.png"),
    "floor-lamp": ("png", "work/layers/floor-lamp.png"), "framed-art": ("png", "work/layers/framed-art.png"),
    "accent-sconces": ("png", "work/layers/accent-sconces.png"), "candle-holders": ("png", "work/layers/candle-holders.png"),
    "curtains": ("npy", "work-reserve/r1-regt.npy"), "magazine-holder": ("npy", "work-reserve/r1-regt.npy"),
    "bowl": ("npy", "work-reserve/r2-regt.npy"), "planter": ("npy", "work-r3/r3a-regt.npy"),
    "basket": ("npy", "work-r3/r3a-regt.npy"), "pendant": ("npy", "work-r3/r3b-regt.npy")}
alphas = {k: np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"])))[..., 3] for k in src}
for s in "ABC":
    alphas["set-" + s] = np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["layer"])))[..., 3]
out = {}
for k, (kind, f) in src.items():
    p = os.path.join(P2, f)
    S = np.load(p).astype(np.float32) if kind == "npy" else np.asarray(Image.open(p))[..., :3].astype(np.float32) / 255
    lay = np.asarray(Image.open(os.path.join(P2, "layers", byid[k]["file"]))).astype(np.float32)
    inner = cv2.erode((alphas[k] == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    for o, a in alphas.items():
        if o != k and byid.get(o, {}).get("z", 999) > byid[k]["z"] or o.startswith("set-"):
            inner &= a == 0
    if kind == "png":
        inner &= np.asarray(Image.open(p))[..., 3] == 255
    Ls = L_of(S)[..., 0][inner]
    Ll = L_of(lay[..., :3] / 255)[..., 0][inner]
    r = (Ll - Ls) - np.interp(Ls, xc, curve_f)
    rec = dict(source=f, px=int(inner.sum()), L_src_p1_p50_p99=[round(float(np.percentile(Ls, q)), 1) for q in (1, 50, 99)],
               residual_median=round(float(np.median(r)), 3), residual_p95_abs=round(float(np.percentile(np.abs(r), 95)), 3))
    toe = Ls < 25
    if toe.sum() > 20:
        lift = np.interp(Ls[toe], xc, curve_f)
        rec["toe_px"] = int(toe.sum())
        rec["toe_expected_lift_median"] = round(float(np.median(lift)), 2)
        rec["toe_observed_lift_median"] = round(float(np.median((Ll - Ls)[toe])), 2)
        rec["toe_residual_median"] = round(float(np.median(r[toe])), 3)
    sh = Ls > 88
    if sh.sum() > 20:
        rec["shoulder_px"] = int(sh.sum())
        rec["shoulder_residual_median"] = round(float(np.median(r[sh])), 3)
    out[k] = rec
res["products"] = out
res["verdict_rule"] = "one grade if |residual median| <= 0.5 and toe residual within +-1 (a second toe would add ~+3 to +6 at L 8-12; a missing one -3 to -6)"
json.dump(res, open(os.path.join(OUT, "data/grade.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
