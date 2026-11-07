#!/usr/bin/env python3
"""
ed6_milktea.py: QA register v3 (qa/reports/ged-register-2026-11-07-r3.md section 1) on warm-modern ed5, render-agent, 2026-11-07. 0 tokens.
The milk-tea boucle cushion (cushions-cj-boucle-teddy, Milk Tea 30 x 50 on the card; in this frame the square at the right end) reads light
brown: against the white stoneware vase in the same sun L* -7.9, a* +4.4, b* +8.5 (QA). In the SKU photo the same SKU is a pale cream,
milk tea minus White = L* +1.1, a* +0.9, b* +1.6 (QA's setA.json). So the cushion is moved, inside its own mask only, by the median shift
that puts it at the photo's relation to white: L* +9.0, a* -3.5, b* -6.9 (vase = white). Texture and shading kept (additive in Lab:
every pixel's offset from the cushion's median stays); highlights rolled off from L* 80 and the lift shrunk wherever a channel would pass 250, so nothing clips; the olive leaves in front of
it excluded (green or dark). The "21 Camel" cushion is not touched (owner, CAM1).
warm-modern-A-ed5.png -> warm-modern-A-ed6.png; record ed6-milktea.json; crops ed6-milktea-before-after/.
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

SRC = os.path.join(HERE, "warm-modern-A-ed5.png")
OUT = os.path.join(HERE, "warm-modern-A-ed6.png")
REC = os.path.join(HERE, "ed6-milktea.json")
CROPS = os.path.join(HERE, "ed6-milktea-before-after")
# render-agent's outline of the cushion (full-size px), read off a 25 px grid; GrabCut refines a +-10 px band
OUTLINE = [(2016, 685), (2060, 705), (2110, 720), (2190, 705), (2272, 692), (2270, 710), (2250, 765), (2240, 840), (2230, 920), (2227, 932),
           (2160, 925), (2100, 920), (2030, 910), (1960, 902), (1957, 900), (1980, 830), (2000, 765), (2007, 715)]
SHIFT = dict(L=9.0, a=-3.5, b=-6.9)
VASE_BOX = (0.66, 0.58, 0.70, 0.68)          # the white stoneware vase's sunlit body (frame fractions), for the after-check


def lab_of(a8):
    return cv2.cvtColor(a8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


def main():
    A = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = A.shape[:2]
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
    cv2.grabCut(A[cy0:cy1, cx0:cx1].copy(), sub, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    m = np.zeros((H, W), bool)
    m[cy0:cy1, cx0:cx1] = np.isin(sub, (cv2.GC_FGD, cv2.GC_PR_FGD))
    lab = lab_of(A)
    leaves = (lab[..., 1] < 0.5) | (lab[..., 0] < 38)                    # olive leaves and stems in front: green or dark
    leaves = cv2.dilate(leaves.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m &= ~leaves
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2) * cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8))
    soft = np.where(leaves, 0.0, soft).astype(np.float32)
    before = np.median(lab[m], 0)
    L = lab[..., 0]
    roll = 1.0 - np.clip((L - 80.0) / 16.0, 0, 1) ** 1.5                  # highlights keep their headroom
    lab2 = lab.copy()
    lab2[..., 1] = lab[..., 1] + SHIFT["a"] * soft
    lab2[..., 2] = lab[..., 2] + SHIFT["b"] * soft
    k = np.ones((H, W), np.float32)
    for _ in range(8):                                                   # no channel above 250: the L lift shrinks where it would clip
        lab2[..., 0] = L + SHIFT["L"] * roll * soft * k
        rgb = np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1)
        hot = (rgb.max(2) > 250 / 255) & (soft > 0)
        if not hot.any():
            break
        k = np.where(hot, k * 0.7, k).astype(np.float32)
    k = np.minimum(k, cv2.erode(k, np.ones((5, 5), np.uint8)))
    k = cv2.GaussianBlur(k, (0, 0), 2.0)
    lab2[..., 0] = L + SHIFT["L"] * roll * soft * k
    rgb = np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1)
    hot = (rgb.max(2) > 250 / 255) & (soft > 0)                          # the last few: no lift at all there
    lab2[..., 0] = np.where(hot, L, lab2[..., 0])
    rgb = np.clip(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB), 0, 1)
    hot2 = (rgb.max(2) * 255 + 0.5 >= 254) & (soft > 0)                  # still at the ceiling (the b* cut lifts blue): left as they were
    zone = (soft > 0) & ~hot2
    o8 = np.where(zone[..., None], (rgb * 255 + 0.5).astype(np.uint8), A)
    Image.fromarray(o8).save(OUT)
    lab_o = lab_of(o8)
    after = np.median(lab_o[m], 0)
    vb = VASE_BOX
    vase_before = np.median(lab[int(vb[1] * H):int(vb[3] * H), int(vb[0] * W):int(vb[2] * W)].reshape(-1, 3), 0)
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="warm-modern-A-ed5.png", out="warm-modern-A-ed6.png",
               source="qa/reports/ged-register-2026-11-07-r3.md section 1 (QA register v3); coordinator 2026-11-07",
               product="cushions-cj-boucle-teddy, Milk Tea (same SKU as White)", shift_Lab=SHIFT,
               mask_px=int(m.sum()), leaves_excluded_px=int((leaves & (pm > 0)).sum()),
               cushion_Lab_median=dict(before=[round(float(v), 2) for v in before], after=[round(float(v), 2) for v in after]),
               vase_Lab_median=[round(float(v), 2) for v in vase_before],
               cushion_minus_vase=dict(before=[round(float(before[i] - vase_before[i]), 2) for i in range(3)],
                                       after=[round(float(after[i] - vase_before[i]), 2) for i in range(3)],
                                       sku_photo_milk_tea_minus_white=[1.1, 0.9, 1.6]),
               clipped_254_in_mask=int(((o8 >= 254).any(2) & zone).sum()),
               note="TEST, not for the site; the 21 Camel cushion untouched (owner, CAM1); new files only")
    rec.update(check(o8, A, zone, "warm-modern-A-ed6.png"))
    os.makedirs(CROPS, exist_ok=True)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    Bi, Ai = Image.fromarray(o8), Image.fromarray(A)
    outl = []
    for name, bx, sc in (("cushion-100", (1880, 620, 2380, 1000), 1), ("cushion-edge-x4", (1990, 760, 2090, 860), 4),
                         ("leaves-x4", (1960, 690, 2060, 790), 4), ("context-50", (1500, 560, 2560, 1200), 0.5)):
        w_, h_ = bx[2] - bx[0], bx[3] - bx[1]
        size = (int(w_ * sc), int(h_ * sc))
        rs = Image.NEAREST if sc > 1 else Image.LANCZOS
        pa, pb = Ai.crop(bx).resize(size, rs), Bi.crop(bx).resize(size, rs)
        im = Image.new("RGB", (size[0] * 2 + 30, size[1] + 40), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: ed5 | ed6", fill=(0, 0, 0), font=fnt)
        im.paste(pa, (10, 30))
        im.paste(pb, (20 + size[0], 30))
        p = os.path.join(CROPS, name + ".jpg")
        im.save(p, quality=92)
        outl.append(os.path.relpath(p, HERE))
    rec["crops"] = outl
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in rec.items() if k not in ("crops",)}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
