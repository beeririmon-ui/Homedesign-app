#!/usr/bin/env python3
"""
fin7_planter.py: QA register v3 (qa/reports/ged-register-2026-11-07-r3.md section 2) on boho fin6, render-agent, 2026-11-07. 0 tokens.
The planter's card option is "natural" (sizes only); the frame shows a black-dipped base (from a reference crop of a dipped basket in
the listing). The dark base is recoloured to the natural seagrass of the planter's own body and its shading rebuilt:
  mask    render-agent's outline of the base (full-size px, read off a 10 px grid) intersected with the dark pixels (L* < 33), grown 1 px,
          holes filled; the coffee table and the bowl in front stay out (they are light)
  colour  the body's seagrass: per column, the median L* / a* / b* of the body's lowest 40 px band above the seam (the sun spots on the
          body's right excluded: L* above the band's 85th percentile), smoothed along x
  shading the base turns under: L* falls from 0.97 of the body value at the seam to 0.72 at the bottom; the base's own low-frequency
          shading (its left / right modelling) kept as a ratio; the weave: the body's own high-frequency L* texture copied down
          (the 40 px band repeated, its diagonal weave continued), scaled to the base's light; the seam line kept as a 2 px darker band; the belly darker toward its left / right outline (16 px), the weave texture clipped to +-6 L* (no sun glints)
fin6 -> boho-A-fin7.png; record fin7-planter.json; crops fin7-planter-before-after/ (100 %, x4).
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

SRC = os.path.join(HERE, "boho-A-fin6.png")
OUT = os.path.join(HERE, "boho-A-fin7.png")
REC = os.path.join(HERE, "fin7-planter.json")
CROPS = os.path.join(HERE, "fin7-planter-before-after")
OUTLINE = [(1816, 924), (1860, 931), (1900, 935), (1950, 935), (2000, 931), (2020, 926), (2022, 960), (2016, 1000), (2005, 1030),
           (1990, 1040), (1900, 1042), (1850, 1040), (1838, 1015), (1826, 975), (1818, 945)]


def main():
    A = np.asarray(Image.open(SRC).convert("RGB"))
    H, W = A.shape[:2]
    f = A.astype(np.float32) / 255
    lab = cv2.cvtColor(f, cv2.COLOR_RGB2LAB)
    L = lab[..., 0]
    pm = np.zeros((H, W), np.uint8)
    cv2.fillPoly(pm, [np.array(OUTLINE, np.int32)], 1)
    pm = cv2.dilate(pm, np.ones((9, 9), np.uint8))
    dark = (pm > 0) & (L < 33)
    dark = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, labm, st, _ = cv2.connectedComponentsWithStats(dark)
    big = 1 + int(np.argmax(st[1:, 4]))
    dark = (labm == big).astype(np.uint8)
    cnts, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    m = np.zeros_like(dark)
    cv2.drawContours(m, cnts, -1, 1, -1)
    m = (cv2.dilate(m, np.ones((3, 3), np.uint8)) > 0) & (pm > 0) & (L < 40)
    ys, xs = np.nonzero(m)
    x0, x1 = xs.min(), xs.max()
    seam = np.full(W, -1)
    bottom = np.full(W, -1)
    for x in range(x0, x1 + 1):
        col = np.nonzero(m[:, x])[0]
        if col.size:
            seam[x], bottom[x] = col.min(), col.max()
    # the body's band above the seam
    BAND = 40
    bodyL, bodyA, bodyB = np.zeros(W, np.float32), np.zeros(W, np.float32), np.zeros(W, np.float32)
    for x in range(x0, x1 + 1):
        if seam[x] < 0:
            continue
        b = lab[max(0, seam[x] - 4 - BAND):seam[x] - 4, x]
        hi = np.percentile(b[:, 0], 85)
        b = b[b[:, 0] <= hi]
        bodyL[x], bodyA[x], bodyB[x] = np.median(b, 0)
    sm = lambda v: cv2.GaussianBlur(v.reshape(1, -1), (0, 0), 12).ravel()
    valid = np.zeros(W, np.float32)
    valid[x0:x1 + 1] = (seam[x0:x1 + 1] >= 0)
    nrm = np.maximum(sm(valid), 1e-4)
    bodyL, bodyA, bodyB = sm(bodyL * valid) / nrm, sm(bodyA * valid) / nrm, sm(bodyB * valid) / nrm
    # texture: the body's high frequencies of L*, the band copied down, column by column (the weave continues)
    hpL = np.clip(L - cv2.GaussianBlur(L, (0, 0), 3.0), -6, 6)             # the weave, without the sun glints of the body's right side
    out_lab = lab.copy()
    LFbase = cv2.GaussianBlur(np.where(m, L, 0).astype(np.float32), (0, 0), 14) / np.maximum(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 14), 1e-4)
    base_mean = float(np.median(LFbase[m]))
    for x in range(x0, x1 + 1):
        if seam[x] < 0:
            continue
        rows = np.nonzero(m[:, x])[0]
        t = (rows - seam[x]) / max(1, bottom[x] - seam[x])
        fall = 0.97 - 0.25 * t
        model = np.clip(LFbase[rows, x] / max(base_mean, 1e-3), 0.85, 1.15)          # the base's own left / right modelling, as a ratio
        src = seam[x] - 4 - BAND + ((rows - seam[x]) % BAND)
        tex = hpL[np.clip(src, 0, H - 1), x] * (0.9 - 0.3 * t)
        newL = bodyL[x] * fall * model + tex
        newL = np.where(rows - seam[x] < 2, newL * 0.82, newL)                       # the seam stays a fine darker line
        out_lab[rows, x, 0] = newL
        out_lab[rows, x, 1] = bodyA[x]
        out_lab[rows, x, 2] = bodyB[x] * (0.95 - 0.15 * t)
    # the belly turns away at its left and right silhouette: darker toward the outline (horizontal distance to the mask's side, 16 px)
    for y in np.unique(ys):
        row = np.nonzero(m[y])[0]
        if row.size < 3:
            continue
        xl, xr = row.min(), row.max()
        d = np.minimum(row - xl, xr - row).astype(np.float32)
        out_lab[y, row, 0] *= 0.72 + 0.28 * np.clip(d / 16.0, 0, 1) ** 0.8
    rgb = np.clip(cv2.cvtColor(out_lab, cv2.COLOR_LAB2RGB), 0, 1)
    # feather the outline 1 px (mixes only inside the grown mask)
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8) * m
    a = np.maximum(a, cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32))
    o = f * (1 - a[..., None]) + rgb * a[..., None]
    o8 = np.where(m[..., None], (o * 255 + 0.5).astype(np.uint8), A)
    Image.fromarray(o8).save(OUT)
    lo = cv2.cvtColor(o8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    body_band = np.zeros((H, W), bool)
    for x in range(x0, x1 + 1):
        if seam[x] >= 0:
            body_band[max(0, seam[x] - 4 - BAND):seam[x] - 4, x] = True
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="boho-A-fin6.png", out="boho-A-fin7.png",
               source="qa/reports/ged-register-2026-11-07-r3.md section 2 (QA register v3); coordinator 2026-11-07",
               product="the boho planter (seagrass belly basket), card option 'natural' (sizes only)",
               mask_px=int(m.sum()), base_Lab_median=dict(before=[round(float(v), 2) for v in np.median(lab[m], 0)],
                                                          after=[round(float(v), 2) for v in np.median(lo[m], 0)]),
               body_band_Lab_median=[round(float(v), 2) for v in np.median(lab[body_band], 0)],
               shading="L* 0.97 -> 0.72 of the body's band from the seam to the bottom, the base's own left / right modelling kept as a ratio, the body's weave texture copied down",
               note="TEST, not for the site; new files only")
    rec.update(check(o8, A, m, "boho-A-fin7.png"))
    os.makedirs(CROPS, exist_ok=True)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    Ai, Bi = Image.fromarray(A), Image.fromarray(o8)
    outl = []
    for name, bx, sc in (("planter-100", (1760, 780, 2080, 1080), 1), ("base-x4", (1850, 915, 1950, 1015), 4),
                         ("seam-x4", (1930, 900, 2030, 960), 4), ("context-50", (1500, 600, 2300, 1150), 0.5)):
        w_, h_ = bx[2] - bx[0], bx[3] - bx[1]
        size = (int(w_ * sc), int(h_ * sc))
        rs = Image.NEAREST if sc > 1 else Image.LANCZOS
        pa, pb = Ai.crop(bx).resize(size, rs), Bi.crop(bx).resize(size, rs)
        im = Image.new("RGB", (size[0] * 2 + 30, size[1] + 40), (250, 249, 247))
        d = ImageDraw.Draw(im)
        d.text((10, 5), f"{name}: fin6 | fin7", fill=(0, 0, 0), font=fnt)
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
