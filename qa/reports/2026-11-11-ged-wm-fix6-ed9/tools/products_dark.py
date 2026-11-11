"""
qa-agent 2026-11-11: G-ED.3 spot reads the designer asked for (§6: the black bowl still black-espresso, the muslin caramel, the walnut
rich), and how much of the grain / folds in deep shadow the toe keeps.
  colour: mean Lab of the product's px in deep shadow (L* < 25 on the before frame, the same px after), and its chromaticity
          (linear RGB / G) against neutral neighbours in the same light (the white bouclé behind the bowl, the white mug; in the
          master the cream bouclé cushion), and against the Bible's espresso #2E2824 and the card's #2F2F2E;
  grain:  L* high-pass SD (sigma 1.5) on the same px before / after, the ratio, and the correlation of the two high-pass maps
          (1 = the same pattern); and the same for log-luminance (the ratio of contrasts, which a pure exposure lift keeps at 1);
  the bowl's lower contour band (its 8 px above the foot and table) for a red / fig bleed: hue and C*.
Usage: ~/.venvs/motion/bin/python -I products_dark.py. Writes data/products-dark.json.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LR, MB, OUT, lab, load, mean_lab, r  # noqa: E402


def lin(x):
    c = np.asarray(x, np.float64) / 255.0
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def chrom(im, m):
    v = lin(im)[m].mean(0)
    return [r(v[0] / v[1], 3), 1.0, r(v[2] / v[1], 3)]


def grain(Lb, La, Yb, Ya, m):
    hb = Lb - cv2.GaussianBlur(Lb, (0, 0), 1.5)
    ha = La - cv2.GaussianBlur(La, (0, 0), 1.5)
    lb_, la_ = np.log(np.maximum(Yb, 1e-4)), np.log(np.maximum(Ya, 1e-4))
    gb = lb_ - cv2.GaussianBlur(lb_, (0, 0), 1.5)
    ga = la_ - cv2.GaussianBlur(la_, (0, 0), 1.5)
    return dict(hpL_sd_before=r(hb[m].std(), 3), hpL_sd_after=r(ha[m].std(), 3), hpL_ratio=r(ha[m].std() / hb[m].std(), 3),
                hpL_corr=r(np.corrcoef(hb[m], ha[m])[0, 1], 3),
                hp_logY_ratio=r(ga[m].std() / gb[m].std(), 3), hp_logY_corr=r(np.corrcoef(gb[m], ga[m])[0, 1], 3))


def boxm(shape, b):
    m = np.zeros(shape, bool)
    m[b[1]:b[3], b[0]:b[2]] = True
    return m


def Ylum(im):
    return lin(im) @ np.array([0.2126, 0.7152, 0.0722])


out = {"refs": {"bible_espresso_2E2824": mean_lab(lab(np.array([[[0x2E, 0x28, 0x24]]])), np.ones((1, 1), bool)),
                "card_bowl_2F2F2E": mean_lab(lab(np.array([[[0x2F, 0x2F, 0x2E]]])), np.ones((1, 1), bool)),
                "espresso_chromaticity": chrom(np.array([[[0x2E, 0x28, 0x24]]]), np.ones((1, 1), bool))}}
for name, (pb, pa), items in (
        ("ed9", (os.path.join(LR, "warm-modern-A-ed8.png"), os.path.join(LR, "warm-modern-A-ed9.png")), {
            "black bowl body (bowl-cj-matte-black-bowl-20)": (1380, 1000, 1630, 1110),
            "walnut table, left drum base": (1110, 1250, 1410, 1440),
            "walnut table, right drum base": (1870, 1250, 2170, 1450),
            "walnut table, top edge": (900, 1160, 2380, 1240),
            "neutral: white boucle seat behind the bowl": (1660, 960, 1760, 1010),
            "neutral: white mug, lit": (1610, 1080, 1700, 1140)}),
        ("fix6", (os.path.join(MB, "warm-modern-MB-A-fix5.png"), os.path.join(MB, "warm-modern-MB-A-fix6.png")), {
            "pecan muslin throw, deep folds": (1820, 1230, 2300, 1470),
            "pecan muslin throw, the whole foot of the bed": (940, 1140, 2736, 1536),
            "walnut nightstand, drawer fronts": (1000, 960, 1320, 1200),
            "walnut bed head (in shadow)": (1380, 640, 1460, 940),
            "void under the nightstand": (990, 1230, 1300, 1280),
            "neutral: cream boucle cushion": (1880, 820, 2180, 900)})):
    b, a = load(pb), load(pa)
    lb, la = lab(b), lab(a)
    Yb, Ya = Ylum(b), Ylum(a)
    e = {}
    for k, bx in items.items():
        m = boxm(lb.shape[:2], bx)
        if not k.startswith("neutral"):
            m &= lb[..., 0] < 25
        e[k] = dict(box=list(bx), before=mean_lab(lb, m), after=mean_lab(la, m), chromaticity_before=chrom(b, m), chromaticity_after=chrom(a, m))
        if not k.startswith("neutral"):
            e[k]["grain"] = grain(lb[..., 0], la[..., 0], Yb, Ya, m)
    out[name] = e
# the bowl's lower contour band: bowl px (L* < 25 in ed8) within 8 px of the bowl's outline below y 1060
e8, e9 = load(os.path.join(LR, "warm-modern-A-ed8.png")), load(os.path.join(LR, "warm-modern-A-ed9.png"))
l8, l9 = lab(e8), lab(e9)
bowl = boxm(l8.shape[:2], (1380, 1000, 1630, 1110)) & (l8[..., 0] < 25)
bowl = cv2.morphologyEx(bowl.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
n, lbl, st, _ = cv2.connectedComponentsWithStats(bowl.astype(np.uint8))
bowl = lbl == (1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])))
edge = bowl & ~cv2.erode(bowl.astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool)
low = edge.copy()
low[:1060] = False
inner = cv2.erode(bowl.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
out["ed9_bowl_contour"] = dict(lower_band_before=mean_lab(l8, low), lower_band_after=mean_lab(l9, low),
                               inner_before=mean_lab(l8, inner), inner_after=mean_lab(l9, inner),
                               lower_band_chromaticity_after=chrom(e9, low), inner_chromaticity_after=chrom(e9, inner))
json.dump(out, open(os.path.join(OUT, "data", "products-dark.json"), "w"), indent=1)
for name in ("ed9", "fix6"):
    for k, v in out[name].items():
        g = v.get("grain", {})
        print(name, k, "| L", v["before"]["L"], "->", v["after"]["L"], "C", v["before"]["C"], "->", v["after"]["C"], "h", v["before"]["h"], "->", v["after"]["h"],
              "| chrom", v["chromaticity_before"], "->", v["chromaticity_after"], "| grain", g.get("hpL_ratio"), g.get("hpL_corr"), g.get("hp_logY_ratio"), g.get("hp_logY_corr"))
print(json.dumps(out["refs"]))
print(json.dumps(out["ed9_bowl_contour"]))
