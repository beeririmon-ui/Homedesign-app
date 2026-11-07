#!/usr/bin/env python3
"""
ed7_milktea.py: QA register v4 (qa/reports/ged-register-2026-11-07-r4.md) on warm-modern ed6, render-agent, 2026-11-07. 0 tokens.
The milk-tea boucle now sits on its SKU photo's relation to White, but reads two-tone (cream peaks, tan valleys): C* of its darkest fifth
over its lightest fifth +14.2 (inherited from ed5), in the SKU photo +1.6. The chroma contrast is flattened inside the cushion only,
L* kept (texture and value untouched): C* loses its dependence on L* around the cushion's median (valleys down, peaks up,
the median colour kept, never below 0.45 of the median chroma), every pixel on the cushion's median hue (one fabric; its stray blue-grey
hues out), sized so the dark-fifth minus light-fifth C* lands on the photo's +1.6; peaks that would clip keep their own. The 21 Camel cushion is not touched (CAM1).
warm-modern-A-ed6.png -> warm-modern-A-ed7.png; record ed7-milktea.json; crops ed7-milktea-before-after/ (100 %, x4).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from codefix3 import check  # noqa: E402
from ed6_milktea import OUTLINE  # noqa: E402

SRC = os.path.join(HERE, "warm-modern-A-ed6.png")
OUT = os.path.join(HERE, "warm-modern-A-ed7.png")
REC = os.path.join(HERE, "ed7-milktea.json")
CROPS = os.path.join(HERE, "ed7-milktea-before-after")
TARGET = 1.6                       # the SKU photo's C*(darkest fifth) - C*(lightest fifth), QA register v4


def fifths(Lv, Cv):
    lo, hi = np.percentile(Lv, 20), np.percentile(Lv, 80)
    d, l = Lv <= lo, Lv >= hi
    return float(np.median(Cv[d]) - np.median(Cv[l])), float(np.median(Lv[d])), float(np.median(Lv[l]))


def main():
    A = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = A.shape[:2]
    lab = cv2.cvtColor(A.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    # the cushion: the same outline and GrabCut as ed6, run on ed5 (the same geometry; on ed6 the pale cushion is too close to the wall
    # for GrabCut), the olive leaves out
    A5 = np.asarray(Image.open(os.path.join(HERE, "warm-modern-A-ed5.png")).convert("RGB"))
    lab5 = cv2.cvtColor(A5.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    pm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(pm, [np.array(OUTLINE, np.int32)], 1)
    gm = np.full((H, W), cv2.GC_BGD, np.uint8)
    gm[cv2.dilate(pm, np.ones((21, 21), np.uint8)) > 0] = cv2.GC_PR_BGD
    gm[pm > 0] = cv2.GC_PR_FGD
    gm[cv2.erode(pm, np.ones((21, 21), np.uint8)) > 0] = cv2.GC_FGD
    x0, y0, w, h = cv2.boundingRect(np.array(OUTLINE, np.int32))
    cx0, cy0, cx1, cy1 = x0 - 60, y0 - 60, x0 + w + 60, y0 + h + 60
    sub = gm[cy0:cy1, cx0:cx1].copy()
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(A5[cy0:cy1, cx0:cx1].copy(), sub, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    m = np.zeros((H, W), bool)
    m[cy0:cy1, cx0:cx1] = np.isin(sub, (cv2.GC_FGD, cv2.GC_PR_FGD))
    leaves = cv2.dilate(((lab5[..., 1] < 0.5) | (lab5[..., 0] < 38)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m &= ~leaves
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2) * cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8))
    soft = np.where(leaves, 0.0, soft).astype(np.float32)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    hue = np.arctan2(b, a)
    dC, Ld, Ll = fifths(L[m], C[m])
    # both ends move toward the cushion's median chroma (anchored at its median L*): the valleys lose chroma, the peaks gain it; a
    # one-sided cut would turn the valleys neutral, which reads blue-grey in this warm light
    Lref = float(np.median(L[m]))
    hmed = float(np.arctan2(np.median(b[m]), np.median(a[m])))
    Cfloor = 0.45 * float(np.median(C[m]))
    s = (dC - TARGET) / max(Ll - Ld, 1e-3)
    for _ in range(8):                                   # refined on the written 8-bit result (the soft edge and the round trip move it)
        Cn = np.maximum(C + s * (L - Lref), Cfloor)     # never toward neutral (a grey valley reads blue in this warm light)
        # one fabric, one hue: every pixel along the cushion's median hue (its stray blue-grey hues out), blended by the soft mask
        a_n, b_n = Cn * np.cos(hmed), Cn * np.sin(hmed)
        lab2 = lab.copy()
        lab2[..., 1] = a + (a_n - a) * soft
        lab2[..., 2] = b + (b_n - b) * soft
        Cr = C
        rgb = np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1)
        hot = (rgb.max(2) * 255 + 0.5 >= 251) & (soft > 0)          # never a clipped peak: those keep their own chroma
        if hot.any():
            lab2[..., 1] = np.where(hot, Cr * np.cos(hue), lab2[..., 1])
            lab2[..., 2] = np.where(hot, Cr * np.sin(hue), lab2[..., 2])
            rgb = np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1)
        zone = soft > 0
        o8 = np.where(zone[..., None], (rgb * 255 + 0.5).astype(np.uint8), A)
        lo = cv2.cvtColor(o8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
        Co = np.hypot(lo[..., 1], lo[..., 2])
        dC_after, _, _ = fifths(lo[..., 0][m], Co[m])
        if abs(dC_after - TARGET) < 0.3:
            break
        s += (dC_after - TARGET) / max(Ll - Ld, 1e-3)
    rec_extra = dict(hue_median_deg=round(float(np.degrees(hmed)), 1), chroma_floor=round(Cfloor, 2),
                     px_b_below_3=dict(before=int((m & (b < 3)).sum()), after=int((m & (lo[..., 2] < 3)).sum())))
    Image.fromarray(o8).save(OUT)
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="warm-modern-A-ed6.png", out="warm-modern-A-ed7.png",
               source="qa/reports/ged-register-2026-11-07-r4.md (QA register v4): the milk-tea boucle two-tone; coordinator 2026-11-07",
               product="cushions-cj-boucle-teddy, Milk Tea", mask_px=int(m.sum()),
               C_dark_fifth_minus_light_fifth=dict(before=round(dC, 2), after=round(dC_after, 2), sku_photo=TARGET),
               L_fifths_medians=dict(dark=round(Ld, 1), light=round(Ll, 1)), slope_C_per_L=round(float(s), 4), L_ref=round(Lref, 2),
               Lab_median=dict(before=[round(float(v), 2) for v in np.median(lab[m], 0)], after=[round(float(v), 2) for v in np.median(lo[m], 0)]),
               L_max_change=round(float(np.abs(lo[..., 0] - L)[zone].max()), 2), **rec_extra, clipped_254_in_mask=int(((o8 >= 254).any(2) & zone).sum()),
               method="C* made (nearly) independent of L* around the cushion median (valleys down, peaks up); L* and hue kept; inside the cushion only; clip guard",
               note="TEST, not for the site; the 21 Camel cushion untouched (CAM1); new files only")
    rec.update(check(o8, A, zone, "warm-modern-A-ed7.png"))
    os.makedirs(CROPS, exist_ok=True)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    Ai, Bi = Image.fromarray(A), Image.fromarray(o8)
    outl = []
    for name, bx, sc in (("cushion-100", (1880, 620, 2380, 1000), 1), ("boucle-x4", (2090, 760, 2190, 860), 4), ("edge-x4", (1990, 760, 2090, 860), 4)):
        w_, h_ = bx[2] - bx[0], bx[3] - bx[1]
        size = (int(w_ * sc), int(h_ * sc))
        rs = Image.NEAREST if sc > 1 else Image.LANCZOS
        pa, pb = Ai.crop(bx).resize(size, rs), Bi.crop(bx).resize(size, rs)
        im = Image.new("RGB", (size[0] * 2 + 30, size[1] + 40), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: ed6 | ed7", fill=(0, 0, 0), font=fnt)
        im.paste(pa, (10, 30))
        im.paste(pb, (20 + size[0], 30))
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        outl.append(os.path.relpath(p, HERE))
    rec["crops"] = outl
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in rec.items() if k != "crops"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
