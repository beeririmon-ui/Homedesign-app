#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8; copied from r67_grade.py, inputs changed): one v3c grade on every layer R8 made or changed (not ungraded, not graded twice). The method of
qa/reports/2026-11-11-wm-tool-phase2-r5/tools/r5_grade.py (copied; only the inputs changed): the v3c curve learned on the approved pair
(phase-1 ungraded shell-furniture-v3.png -> layers/base.png, outside the bench slab) as dL*(L*_ungraded); for each layer's interior
(alpha 255 eroded 2 px, under no higher layer) its ungraded source (work-r6|r7/layers/<k>.png) against the graded layer file:
residual = (L_layer - L_src) - curve(L_src); in the toe (L_src < 25) the observed lift against the expected one.
Also the black point (L* p0.5) and the clipped share (any channel >= 254) of the r5 / r6 / r7 default scenes.
Writes data/grade.json.   python3 r67_grade.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8")
JOBS = {"r8": ["curtains", "candle-holders", "curtains-v2", "curtains-v3"]}


def lab(rgb01):
    return cv2.cvtColor(rgb01.astype(np.float32), cv2.COLOR_RGB2LAB)


u = np.asarray(Image.open(os.path.join(P1, "shell-furniture-v3.png")).convert("RGB")).astype(np.float32) / 255
g = np.asarray(Image.open(os.path.join(P2, "layers/base.png")).convert("RGB")).astype(np.float32) / 255
stone = np.asarray(Image.open(os.path.join(P1, "masks/stone-wide.png")).convert("L")) > 127
Lu, Lg = lab(u)[..., 0], lab(g)[..., 0]
m = ~stone
bins = np.arange(0, 100.25, 0.25)
idx = np.clip(np.digitize(Lu[m], bins) - 1, 0, len(bins) - 2)
dL = (Lg - Lu)[m]
curve = np.full(len(bins) - 1, np.nan)
for i in range(len(bins) - 1):
    s = dL[idx == i]
    if s.size >= 20:
        curve[i] = np.median(s)
ok = ~np.isnan(curve)
xc = (bins[:-1] + bins[1:]) / 2
curve_f = np.interp(xc, xc[ok], curve[ok])
res = dict(curve_samples={f"{x:.0f}": round(float(np.interp(x, xc, curve_f)), 3) for x in (5, 10, 12, 15, 20, 25, 50, 80, 90, 95)})
for tag, ks in JOBS.items():
    man = json.load(open(os.path.join(P2, f"layers/manifest-{tag}.json")))
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    alphas = {l_["id"]: np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] for l_ in man["layers"] if "product" in l_}
    for s in "ABC":
        alphas["set-" + s] = np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["layer"])))[..., 3]
    VAR = {v["id"]: (v["file"], v["slot"]) for vs in man["variants"].values() for v in vs}
    out = {}
    for k in ks:
        src = np.asarray(Image.open(os.path.join(P2, f"work-{tag}/layers", f"{k}.png"))).astype(np.float32)
        lf, slot = (byid[k]["file"], k) if k in byid else VAR[k]
        lay = np.asarray(Image.open(os.path.join(P2, "layers", lf))).astype(np.float32)
        a = lay[..., 3]
        inner = (cv2.erode((a == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & (src[..., 3] == 255)
        for o, ao in alphas.items():
            if o in (k, slot) or o in VAR:
                continue
            if o.startswith("set-") or byid[o]["z"] > byid[slot]["z"]:
                inner &= ao == 0
        Ls = lab(src[..., :3] / 255)[..., 0][inner]
        Ll = lab(lay[..., :3] / 255)[..., 0][inner]
        r = (Ll - Ls) - np.interp(Ls, xc, curve_f)
        rec = dict(file=lf, px=int(inner.sum()), L_src_p1_p50_p99=[round(float(np.percentile(Ls, q)), 1) for q in (1, 50, 99)],
                   residual_median=round(float(np.median(r)), 3), residual_p95_abs=round(float(np.percentile(np.abs(r), 95)), 3))
        toe = Ls < 25
        if toe.sum() > 20:
            rec.update(toe_px=int(toe.sum()), toe_expected_lift=round(float(np.median(np.interp(Ls[toe], xc, curve_f))), 2),
                       toe_observed_lift=round(float(np.median((Ll - Ls)[toe])), 2))
        out[k] = rec
        print(tag, k, rec, flush=True)
    res[tag] = out
res["rule"] = "one grade if |residual median| <= 0.5 and, in the toe, observed lift within +-1 of the expected (a second toe adds ~+3..+6, a missing one -3..-6)"
res["one_grade_pass"] = all(abs(v["residual_median"]) <= 0.5 and (("toe_px" not in v) or abs(v["toe_observed_lift"] - v["toe_expected_lift"]) <= 1)
                            for t in JOBS for v in res[t].values())
bp = {}
for t in ("r7", "r8"):
    for s in "ABC":
        S = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-{t}-set-{s}-graded-v3c.png")).convert("RGB"))
        L = lab(S.astype(np.float32) / 255)[..., 0]
        bp[f"{t} {s}"] = dict(L_p0_5=round(float(np.percentile(L, 0.5)), 2), clipped_254_pct=round(100 * float((S >= 254).any(2).mean()), 4))
res["black_point_and_clip"] = bp
print(bp, res["one_grade_pass"])
json.dump(res, open(os.path.join(OUT, "data/grade.json"), "w"), indent=1)
