#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): framed-art v2, the seam where render-agent's code pasted the default's walnut frames back over the variant
(post-r5: 'the default's walnut frames in the moulding band', 'seam px refilled from the print') and the specks in the blacks.

  1. The inner edge of each frame (top and bottom rails of the three frames): per column, the sub-pixel row of the dark inner line
     (darkness-weighted centroid in a 9-row window around the darkest row), a straight-line fit along the rail, and the residual. An
     anti-aliased straight edge drifts smoothly (residual well under 0.5 px, no jumps); a stair-stepped seam jumps by ~1 px every few
     dozen columns. Reported: residual RMS, the count of column-to-column jumps >= 0.6 px, for the variant and the default.
  2. Specks: isolated light pixels in the prints' black shapes (L* > black median + 25 with all 8 neighbours dark), in the layer.
  3. The black lift (post-r5 'blacks'): the dark tones' 8-bit histogram in the layer (gaps = posterisation) and the high-pass texture
     against the same model's untouched cut (work-r5/layers/framed-art-v2-cut.png, if present).
Writes data/framed-art-v2.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r5")


def lab(rgb8):
    return cv2.cvtColor(rgb8.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32) * [100 / 255, 1, 1] - [0, 128, 128]


V = np.asarray(Image.open(os.path.join(P2, "graded/variant-r5-framed-art-v2-set-B-graded-v3c.png")).convert("RGB"))
D = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r5-set-B-graded-v3c.png")).convert("RGB"))
LV, LD_ = lab(V)[..., 0], lab(D)[..., 0]
# rails: (name, x0, x1, y_lo, y_hi) - a window that holds the rail's inner dark line (from the x3 crops)
RAILS = [("print 1 top", 1525, 1690, 528, 552), ("print 2 top", 1735, 1910, 512, 540), ("print 3 top", 1965, 2160, 500, 530),
         ("print 1 bottom", 1525, 1690, 772, 796), ("print 2 bottom", 1735, 1910, 772, 796), ("print 3 bottom", 1965, 2160, 776, 802)]


def rail_profile(L, x0, x1, y0, y1, top):
    """the inner edge: the strongest vertical step from frame (dark) to print (light), per column, refined to sub-pixel"""
    ys = []
    for x in range(x0, x1):
        col = L[y0:y1, x].astype(np.float64)
        g = np.diff(col) if top else -np.diff(col)          # frame above (top rail) or below (bottom rail): dark -> light into the print
        i = int(np.argmax(g))
        if 0 < i < len(g) - 1:
            a, b, c = g[i - 1], g[i], g[i + 1]
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if abs(den) > 1e-6 else 0.0
        else:
            off = 0.0
        ys.append(y0 + i + 0.5 + float(np.clip(off, -0.5, 0.5)))
    ys = np.array(ys)
    xs = np.arange(x0, x1)
    k, b = np.polyfit(xs, ys, 1)
    r = ys - (k * xs + b)
    j = np.abs(np.diff(ys))
    return dict(slope=round(float(k), 4), residual_rms=round(float(np.sqrt((r ** 2).mean())), 3), residual_max=round(float(np.abs(r).max()), 2),
                jumps_ge_0_6=int((j >= 0.6).sum()), jumps_ge_1_0=int((j >= 1.0).sum()), columns=int(len(xs)))


res = {"rails": {}}
for name, x0, x1, y0, y1 in RAILS:
    top = "top" in name
    res["rails"][name] = dict(variant=rail_profile(LV, x0, x1, y0, y1, top), default=rail_profile(LD_, x0, x1, y0, y1, top))
    print(name, res["rails"][name])

# 2. specks in the blacks (layer)
lay = np.asarray(Image.open(os.path.join(P2, "layers/framed-art/framed-art-aliexpress-modern-minimalist-neutral-gallery-802995-r5.png")))
La = lab(lay[..., :3])[..., 0]
a = lay[..., 3]
black = (La < 25) & (a == 255)
blk = cv2.morphologyEx(black.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)   # the black shapes, holes closed
med = float(np.median(La[black]))
nb_dark = cv2.erode(black.astype(np.uint8), np.ones((3, 3), np.uint8), borderType=cv2.BORDER_CONSTANT)  # unused, kept for clarity
spk = blk & ~black & (La > med + 25)
# isolated: the 8-neighbourhood (without the pixel) all black
k8 = np.ones((3, 3), np.float32)
k8[1, 1] = 0
nblack = cv2.filter2D(black.astype(np.float32), -1, k8, borderType=cv2.BORDER_CONSTANT)
iso = spk & (nblack >= 7)
ys, xs = np.nonzero(spk)
res["specks"] = dict(black_shape_px=int(blk.sum()), black_median_L=round(med, 2), light_px_inside_black=int(spk.sum()),
                     isolated_px=int(iso.sum()), coords=[[int(x), int(y), round(float(La[y, x]), 1)] for y, x in zip(ys, xs)][:40])
print("specks", res["specks"]["light_px_inside_black"], res["specks"]["isolated_px"], res["specks"]["coords"][:12])

# 3. the black lift: histogram gaps and texture
vals = lay[..., :3][black].reshape(-1)
h = np.bincount(vals, minlength=256)
lo, hi = int(np.percentile(vals, 1)), int(np.percentile(vals, 99))
gaps = [int(v) for v in range(lo, hi + 1) if h[v] == 0]
hp = lambda L_: L_ - cv2.GaussianBlur(L_, (0, 0), 2.0)  # noqa: E731
inner = cv2.erode(black.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
res["black_lift"] = dict(rgb_p1_p99=[lo, hi], empty_levels_between=gaps, n_levels_used=int((h[lo:hi + 1] > 0).sum()),
                         highpass_std_layer=round(float(hp(La)[inner].std()), 3))
cutp = os.path.join(P2, "work-r5/layers/framed-art-v2-cut.png")
if os.path.exists(cutp):
    cut = np.asarray(Image.open(cutp))
    Lc = lab(np.clip(cut[..., :3], 0, 255))[..., 0]
    res["black_lift"]["highpass_std_ungraded_cut_same_px"] = round(float(hp(Lc)[inner].std()), 3)
    res["black_lift"]["cut_black_median_L_ungraded"] = round(float(np.median(Lc[inner])), 2)
res["black_lift"]["layer_black_median_L"] = round(float(np.median(La[inner])), 2)
# the default's darkest print tone for reference (its espresso band)
dl = np.asarray(Image.open(os.path.join(P2, "layers/framed-art/framed-art-aliexpress-frameless-minimalist-wall-art-631735.png")))
Ld = lab(dl[..., :3])[..., 0]
dd = (Ld < 30) & (dl[..., 3] == 255)
res["black_lift"]["default_print_darkest_tone_median_L"] = round(float(np.median(Ld[dd])), 2) if dd.any() else None
print("lift", res["black_lift"])
json.dump(res, open(os.path.join(OUT, "data/framed-art-v2.json"), "w"), indent=1)
