#!/usr/bin/env python3
"""
grade_med.py: the Mediterranean regional grade in code (master-designer, docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 6,
G-ED.13: 13:00, a hard sun blade, cool shade), render-agent, 2026-11-07. 0 tokens, no var2.
mediterranean-A-ed6.png -> mediterranean-A-ed7.png (ed6 and the raw kept as they are). Per-pixel curves on a soft shade mask:
  sun mask    the direct sun patches only (L* > 78 and b* > 18, the window box out), softened ~20 px: inside, nothing changes
  shade       everything else but the window: white balance ~500 K cooler (linear gains W(5000 K) / W(4500 K), luminance kept);
              L* 30-70 down by up to 4 (a soft bump); chroma -10 % (the terracotta floor held at HSV S >= 0.40);
              the limewash (low-chroma warm whites on the architecture, the products' boxes out) pulled to b* 6-9 and a* <= 3
  the blade   the sun patch on the floor and the sill stays exactly as it is and stands out as the shade round it goes down
Guardrails measured: G-ED.11 (b* of the darkest 10 % >= -4; target >= +3), G-ED.12 (clipped >= 254, raw / ed6 / ed7), and the mask edge
(the shade weight's gradient zone) checked for halos in the crops. grade-med.json, grade-med-sheet.jpg, grade-med-before-after/.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01  # noqa: E402
from grade_boho import white_rgb, lab_f, rgb_f, hsv_s, measure_clip  # noqa: E402

SRC = os.path.join(HERE, "mediterranean-A-ed6.png")
RAW = os.path.join(HERE, "raw", "mediterranean-A-gpt-image-2-5.png")
OUT = os.path.join(HERE, "mediterranean-A-ed7.png")
REC = os.path.join(HERE, "grade-med.json")
WINDOW = (2392, 170, 2730, 915)                         # the glass and the view (the shutter outside it)
PRODUCT_BOXES = [(288, 136, 692, 664), (732, 182, 1102, 672), (1138, 226, 1462, 678),    # the three framed prints
                 (1172, 0, 1694, 252),                                                    # the pendant
                 (200, 700, 1772, 1240), (428, 980, 1004, 1446),                          # the back cushions, the seat pad, the throw
                 (708, 1000, 2132, 1536),                                                 # the table, the bowl, the candle holders
                 (1728, 838, 2002, 1232), (1948, 918, 2272, 1272),                       # the magazine holder, the planter
                 (2088, 378, 2652, 930), (276, 1356, 2684, 1536)]                         # the sill vase with its olive, the rug


def box_mask(shape, boxes):
    m = np.zeros(shape[:2], bool)
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = True
    return m


def main():
    a = load01(SRC)
    H, W = a.shape[:2]
    lab0 = lab_f(a)
    L0, A0, B0 = lab0[..., 0], lab0[..., 1], lab0[..., 2]
    win = box_mask(a.shape, [WINDOW])
    # the sun mask (hard patches) softened ~20 px; the window kept too
    sun = (L0 > 78) & (B0 > 18) & ~win
    sun = cv2.morphologyEx(sun.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    sun = cv2.morphologyEx(sun, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(np.float32)
    sun_s = np.maximum(sun, np.clip(cv2.GaussianBlur(sun, (0, 0), 6.5) * 1.6, 0, 1))      # the patches whole; the ~20 px soft edge in the shade
    win_s = np.clip(cv2.GaussianBlur(win.astype(np.float32), (0, 0), 4.0) * 1.3, 0, 1)
    shade = (1 - sun_s) * (1 - win_s)
    # 1. white balance ~500 K cooler, in the shade only
    lin = s2l(a)
    g = white_rgb(5000) / white_rgb(4500)
    g = g / (g @ np.array([0.2126, 0.7152, 0.0722]))
    hl = np.clip((L0 - 80.0) / 12.0, 0, 1)                                 # the highlights (L* 80-92) keep their white: no clipping
    wb_w = shade * (1 - hl)
    lin1 = lin * (1 + (g[None, None, :] - 1) * wb_w[..., None])
    s1 = l2s(np.clip(lin1, 0, 1))
    lab = lab_f(s1)
    L, A_, B_ = lab[..., 0], lab[..., 1], lab[..., 2]
    # 2. chroma -10 % in the shade; the terracotta floor held at S >= 0.40
    C = np.hypot(A_, B_)
    h = np.degrees(np.arctan2(B_, A_)) % 360
    cf = 1 - 0.10 * shade
    A2, B2 = A_ * cf, B_ * cf
    # 3. the limewash in the shade: b* to 6-9, a* <= 3 (the architecture's low-chroma warm whites; the products' boxes out)
    prod = box_mask(a.shape, PRODUCT_BOXES)
    lime = (C < 24) & (h > 45) & (h < 105) & (L > 35) & (L < 95) & ~prod & ~win
    lm = cv2.GaussianBlur(lime.astype(np.float32), (0, 0), 2.0) * (1 - cv2.GaussianBlur(prod.astype(np.float32), (0, 0), 2.0)) * shade
    b_now = float(np.median(B2[lime & (shade > 0.9)])) if (lime & (shade > 0.9)).any() else 10.0
    b_t = float(np.clip(b_now, 6.0, 9.0))
    if b_now > 9.0:
        b_t = 8.0
    elif b_now < 6.0:
        b_t = 6.5
    B3 = B2 + (np.clip(B2, 6.0, 9.0) - B2) * lm                              # each limewash pixel into b* 6-9
    A3 = np.where(A2 > 3.0, A2 - (A2 - 3.0) * 0.7 * lm, A2)
    # 4. L* 30-70 down by up to 4 (a soft bump), shade only, the chroma kept in proportion
    bump = np.where((L > 30) & (L < 70), 4.0 * np.sin(np.pi * (L - 30) / 40.0), 0.0)
    L3 = L - bump * shade
    ratio = np.clip(L3 / np.maximum(L, 1e-3), 0.9, 1.0)
    lab3 = np.stack([L3, A3 * ratio, B3 * ratio], -1)
    s3 = rgb_f(lab3)
    # the terracotta floor (hue 25-60, C > 15, low in the frame) held at S >= 0.40 where it was
    S_in, S_out = hsv_s(a), hsv_s(s3)
    terr = (h > 25) & (h < 60) & (C > 15) & (S_in >= 0.40) & (S_out < 0.40) & (shade > 0.05) & ~prod
    if terr.any():
        k_ = np.clip((0.40 - S_out) / np.maximum(S_in - S_out, 1e-3), 0, 1)
        s3 = np.where(terr[..., None], s3 * (1 - k_[..., None]) + a * k_[..., None], s3)
    o8 = (np.clip(s3, 0, 1) * 255 + 0.5).astype(np.uint8)
    # inside the sun mask (weight < 0.002 shade) and the window: the original pixels exactly
    keep = shade < 0.002
    o8 = np.where(keep[..., None], (a * 255 + 0.5).astype(np.uint8), o8)
    Image.fromarray(o8).save(OUT)
    # --- measures
    labo = lab_f(o8.astype(np.float32) / 255)

    def dark10_b(lb):
        Lq = cv2.resize(lb[..., 0], (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        Bq = cv2.resize(lb[..., 2], (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        thr = np.percentile(Lq, 10)
        return round(float(Bq[Lq <= thr].mean()), 2)

    def patch(lb, bx):
        x0, y0, x1, y1 = bx
        s_ = lb[y0:y1, x0:x1].reshape(-1, 3)
        return [round(float(np.median(s_[:, i])), 1) for i in range(3)]
    patches = {"limewash back wall (shade)": (1520, 320, 1700, 520), "limewash arch left (shade)": (20, 400, 120, 900),
               "limewash right wall (shade)": (1800, 300, 2000, 600), "bench front (shade)": (260, 1240, 600, 1340),
               "terracotta floor (shade)": (2300, 1320, 2600, 1400), "the blade: floor sun patch": None, "the blade: sill sun patch": None}
    pat = {}
    for k, bx in patches.items():
        if bx is None:
            continue
        pat[k] = dict(before=patch(lab0, bx), after=patch(labo, bx))
    # the blade: the sun pixels on the floor (y > 1250) and the sill (x > 2300, y 880-960): unchanged, and their contrast to the shade
    floor_sun = (sun > 0) & (np.mgrid[0:H, 0:W][0] > 1250)
    sill_sun = (sun > 0) & box_mask(a.shape, [(2250, 860, 2736, 980)])

    def contrast(lb, m):
        if not m.any():
            return None
        ring = cv2.dilate(m.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & ~cv2.dilate(m.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
        return round(float(np.median(lb[..., 0][m]) - np.median(lb[..., 0][ring])), 1)
    blade = dict(floor=dict(px=int(floor_sun.sum()), L_contrast_to_shade_before=contrast(lab0, floor_sun), after=contrast(labo, floor_sun)),
                 sill=dict(px=int(sill_sun.sum()), L_contrast_to_shade_before=contrast(lab0, sill_sun), after=contrast(labo, sill_sun)))
    moved_in_sun = int((np.abs(o8.astype(int) - (a * 255 + 0.5).astype(int)).max(2) > 0)[sun > 0].sum())
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="mediterranean-A-ed6.png", out="mediterranean-A-ed7.png",
               raw_kept="raw/mediterranean-A-gpt-image-2-5.png", spec="docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 6 + the manager's brief",
               masks=dict(sun_px=int((sun > 0).sum()), sun_soft_px=int(((sun_s > 0.002) & (sun_s < 0.998)).sum()), shade_mean=round(float(shade.mean()), 3),
                          window_box=list(WINDOW), limewash_px=int(lime.sum()), product_boxes=PRODUCT_BOXES),
               steps=dict(white_balance=dict(from_K=5000, to_K=4500, linear_gains=np.round(g, 4).tolist(), note="cooler by ~500 K, shade only"),
                          chroma_factor_shade=0.90, terracotta_floor_floor_S=0.40, terracotta_held_px=int(terr.sum()),
                          limewash=dict(b_median_before=round(b_now, 2), b_target=round(b_t, 2), a_cap=3.0),
                          L_bump="L* 30-70 down by up to 4 (sin), shade only"),
               patches_Lab=pat, blade=blade, sun_px_changed=moved_in_sun,
               guardrails=dict(G_ED_11_dark10_b=dict(ed6=dark10_b(lab0), ed7=dark10_b(labo), rule=">= -4 (target >= +3)"),
                               G_ED_12=dict(raw=measure_clip(RAW) if os.path.exists(RAW) else None, ed6=measure_clip(SRC), ed7=measure_clip(OUT))),
               note="TEST, not for the site; new files only")
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    # the sheet and crops
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    A = Image.open(SRC).convert("RGB")
    B = Image.open(OUT).convert("RGB")
    w = 1200
    A2_, B2_ = A.resize((w, int(A.height * w / A.width)), Image.LANCZOS), B.resize((w, int(B.height * w / B.width)), Image.LANCZOS)
    sh = Image.new("RGB", (2 * w + 60, A2_.height + 90), (250, 249, 247))
    d = ImageDraw.Draw(sh)
    d.text((20, 18), "Mediterranean: ed6 (left) -> ed7, regional grade: the sun kept, the shade cooler and lower (13:00). TEST", fill=(0, 0, 0), font=f)
    sh.paste(A2_, (20, 70))
    sh.paste(B2_, (40 + w, 70))
    sh.save(os.path.join(HERE, "grade-med-sheet.jpg"), quality=90)
    os.makedirs(os.path.join(HERE, "grade-med-before-after"), exist_ok=True)
    for name, bx in {"floor-blade": (1900, 1150, 2736, 1536), "sill-blade": (2150, 700, 2736, 1000), "wall-shade": (1400, 200, 2100, 900),
                     "arch-bench": (0, 600, 900, 1400)}.items():
        pa, pb = A.crop(bx), B.crop(bx)
        im = Image.new("RGB", (pa.width * 2 + 20, pa.height), (250, 249, 247))
        im.paste(pa, (0, 0))
        im.paste(pb, (pa.width + 20, 0))
        im.save(os.path.join(HERE, "grade-med-before-after", name + ".jpg"), quality=92)
    return rec


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: v for k, v in r.items() if k in ("masks", "steps", "patches_Lab", "blade", "sun_px_changed", "guardrails")}, indent=1, ensure_ascii=False)[:5000])
