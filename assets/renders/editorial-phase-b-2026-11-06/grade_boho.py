#!/usr/bin/env python3
"""
grade_boho.py: the boho grade in code (master-designer's G-ED.10 fix, docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 2),
render-agent, 2026-11-07. 0 tokens, no var2. boho-A-fin5.png -> boho-A-fin6.png (fin5 and the raw kept as they are).
Every step is a per-pixel curve (no local tone mapping), so the reed curtain's light stripes keep their contrast:
  1. white balance ~ -300 K: linear-light gains W(4600 K) / W(4300 K) (Planckian white points, CIE 1931 / sRGB), luminance kept
  2. saturation -15 %: Lab chroma x0.85; terracotta and rust (hue 25-58 deg) held at HSV S >= 0.45 where they were at or above it
  3. shadows: black point L* 9-11 (p0.5 kept there) and a gentle toe that deepens L* 10-45 by up to 2.5 (the shadows read less lifted)
  4. highlights: a soft roll-off from L* 90
  5. the plaster toward sand-cream (#D9C4A1 .. #F0E7D8): in the wall zone only (the art, the sconces, the macrame disc, the pendant and the
     plants kept out), plaster pixels (hue 50-80 deg, C > 8) rotated toward hue 82 and their chroma x0.78; a soft mask
  6. (optional, kept only if clean) the stripes on the rug lifted slightly: +15 % of the rug's own light detail (sigma 14), edges damped
Measures G-ED.12 (clipped >= 254) on the raw and on fin6 with qa's guardrails rules; grade-boho.json.
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finish_phaseb import s2l, l2s, load01  # noqa: E402

SRC = os.path.join(HERE, "boho-A-fin5.png")
RAW = os.path.join(HERE, "raw", "boho-A-gpt-image-2-5.png")
OUT = os.path.join(HERE, "boho-A-fin6.png")
REC = os.path.join(HERE, "grade-boho.json")
M_XYZ2RGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])


def planck_xy(T):
    if T <= 4000:
        x = -0.2661239e9 / T ** 3 - 0.2343589e6 / T ** 2 + 0.8776956e3 / T + 0.179910
    else:
        x = -3.0258469e9 / T ** 3 + 2.1070379e6 / T ** 2 + 0.2226347e3 / T + 0.240390
    if T <= 2222:
        y = -1.1063814 * x ** 3 - 1.34811020 * x ** 2 + 2.18555832 * x - 0.20219683
    elif T <= 4000:
        y = -0.9549476 * x ** 3 - 1.37418593 * x ** 2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x ** 3 - 5.87338670 * x ** 2 + 3.75112997 * x - 0.37001483
    return x, y


def white_rgb(T):
    x, y = planck_xy(T)
    XYZ = np.array([x / y, 1.0, (1 - x - y) / y])
    rgb = M_XYZ2RGB @ XYZ
    return rgb / rgb[1]


def lab_f(srgb):
    return cv2.cvtColor(np.clip(srgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def rgb_f(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def hsv_s(srgb):
    mx, mn = srgb.max(2), srgb.min(2)
    return np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)


def box_mask(shape, boxes):
    m = np.zeros(shape[:2], bool)
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = True
    return m


# products and objects on the wall (full-size boxes, read on the frame): kept out of the plaster step
WALL_OBJECTS = [(800, 170, 1050, 590), (1064, 204, 1278, 590), (1288, 230, 1472, 592),     # the three framed prints
                (210, 230, 402, 470), (1524, 334, 1686, 510),                               # the two rattan sconces
                (500, 276, 672, 462),                                                       # the macrame disc
                (1580, 0, 1990, 262),                                                       # the pendant
                (1730, 380, 2160, 850)]                                                     # the plant on the right
WALL_ZONE = (0, 0, 2160, 690)
RUG_ZONE = [(60, 1180), (2060, 1180), (2060, 1536), (60, 1536)]
RUG_OUT = [(780, 1020, 2045, 1450), (2080, 1090, 2690, 1510)]                               # the coffee table + runner, the pouf


def measure_clip(path, windows=()):
    im = np.asarray(Image.open(path).convert("RGB"))
    keep = np.ones(im.shape[:2], bool)
    for x0, y0, x1, y1 in windows:
        keep[y0:y1, x0:x1] = False
    mx = im.max(2)
    return dict(file=os.path.relpath(path, os.path.join(HERE, "..", "..", "..")), clipped_254_pct=round(float(((mx >= 254) & keep).sum() / keep.sum() * 100), 3),
                near_clip_250_pct=round(float(((mx >= 250) & keep).sum() / keep.sum() * 100), 3))


def main(stripes=True):
    a = load01(SRC)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    lin = s2l(a)
    Y0 = lin @ np.array([0.2126, 0.7152, 0.0722])
    # 1. white balance -300 K (the image's white treated as 4600 K, re-balanced as if at 4300 K: cooler)
    g = white_rgb(4600) / white_rgb(4300)
    g = g / (g @ np.array([0.2126, 0.7152, 0.0722]))
    lin1 = lin * g[None, None, :]
    s1 = l2s(np.clip(lin1, 0, 1))
    lab0 = lab_f(a)
    lab = lab_f(s1)
    L, A_, B_ = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(A_, B_)
    h = np.degrees(np.arctan2(B_, A_)) % 360
    # 5. the plaster (before the global desaturation, so its two factors combine): wall zone, plaster hue and chroma, soft mask
    wz = box_mask(a.shape, [WALL_ZONE]) & ~box_mask(a.shape, WALL_OBJECTS)
    plaster = wz & (h > 50) & (h < 80) & (C > 8) & (L > 25) & (L < 88)
    pm = cv2.GaussianBlur(plaster.astype(np.float32), (0, 0), 2.0) * cv2.GaussianBlur(wz.astype(np.float32), (0, 0), 6.0)
    h_t = h + (82.0 - h) * 0.6 * pm
    C_t = C * (1 - 0.22 * pm)
    # 2. saturation -15 % (chroma), terracotta / rust held at S >= 0.45
    C2 = C_t * 0.85
    lab2 = np.stack([L, C2 * np.cos(np.radians(h_t)), C2 * np.sin(np.radians(h_t))], -1)
    s2 = rgb_f(lab2)
    S_in = hsv_s(a)
    S_out = hsv_s(s2)
    terr = (h > 25) & (h < 58) & (C > 20) & (S_in >= 0.45) & (S_out < 0.45) & (pm < 0.5)
    if terr.any():
        need = np.clip((0.45 - S_out) / np.maximum(S_in - S_out, 1e-3), 0, 1)
        Cf = np.where(terr, C_t * (0.85 + 0.15 * need), C2)
        lab2 = np.stack([L, Cf * np.cos(np.radians(h_t)), Cf * np.sin(np.radians(h_t))], -1)
        s2 = rgb_f(lab2)
    # 3 + 4. the tone curve on L*: the black point kept at L* 9-11, a toe deepening L* 10-45 by up to 2.5, a roll-off from 90
    Lr = lab2[..., 0]
    p05 = float(np.percentile(cv2.resize(Lr, (W // 4, H // 4), interpolation=cv2.INTER_AREA), 0.5))
    toe = np.where((Lr > 10) & (Lr < 45), 2.5 * np.sin(np.pi * (Lr - 10) / 35.0), 0.0)
    Lc = Lr - toe
    Lc = np.where(Lc > 90, 90 + 10 * np.tanh((Lc - 90) / 10.0), Lc)
    lab3 = lab2.copy()
    lab3[..., 0] = Lc
    # the chroma kept in proportion where L* moved (so the toe does not desaturate or over-saturate the shadows)
    ratio = np.clip(Lc / np.maximum(Lr, 1e-3), 0.85, 1.05)
    lab3[..., 1] *= ratio
    lab3[..., 2] *= ratio
    s3 = rgb_f(lab3)
    info_stripes = None
    # 6. the stripes on the rug, slightly (only the rug's own light detail; product edges damped)
    if stripes:
        rug = np.zeros((H, W), np.uint8)
        cv2.fillPoly(rug, [np.array(RUG_ZONE, np.int32)], 1)
        rug = rug.astype(bool) & ~box_mask(a.shape, RUG_OUT)
        rm = cv2.GaussianBlur(rug.astype(np.float32), (0, 0), 10.0) * rug
        Ls = lab3[..., 0]
        base = cv2.GaussianBlur(Ls, (0, 0), 14.0)
        fine = cv2.GaussianBlur(Ls, (0, 0), 2.0)
        D = np.clip(fine - base, -8, 8)                      # the light bands (14 px scale), not the weave (2 px detail kept as is)
        gm = np.hypot(cv2.Sobel(fine, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(fine, cv2.CV_32F, 0, 1, ksize=3))
        damp = np.clip(1 - (gm - 6) / 10.0, 0, 1)            # strong edges (the table legs, the fringe) not pushed
        add = 0.15 * D * rm * damp
        lab4 = lab3.copy()
        lab4[..., 0] = Ls + add
        s3 = rgb_f(lab4)
        info_stripes = dict(amount=0.15, sigma=14, px=int((np.abs(add) > 0.2).sum()), max_L_added=round(float(np.abs(add).max()), 2))
    o8 = (np.clip(s3, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(OUT)
    # --- measures
    labo = lab_f(o8.astype(np.float32) / 255)

    def patch(lb, box):
        x0, y0, x1, y1 = box
        s = lb[y0:y1, x0:x1].reshape(-1, 3)
        return [round(float(np.median(s[:, i])), 1) for i in range(3)]
    patches = {"plaster left of the art": (600, 300, 760, 520), "plaster between the art": (1500, 120, 1560, 260),
               "plaster right": (1700, 500, 1800, 640), "plaster, a lit stripe": (1560, 420, 1640, 560), "plaster top left": (200, 60, 400, 160),
               "ceiling": (1300, 0, 1500, 20), "floor right": (2000, 1100, 2200, 1180), "rug": (900, 1350, 1100, 1450),
               "terracotta cushion": (560, 800, 720, 880), "green cushion": (1040, 760, 1180, 860), "sofa linen": (900, 900, 1050, 960)}
    pat = {k: dict(before=patch(lab0, b), after=patch(labo, b)) for k, b in patches.items()}
    targets = {"#D9C4A1": [round(float(v), 1) for v in lab_f(np.array([[[217, 196, 161]]], np.float32) / 255)[0, 0]],
               "#F0E7D8": [round(float(v), 1) for v in lab_f(np.array([[[240, 231, 216]]], np.float32) / 255)[0, 0]]}
    # stripe contrast on the wall (kept): the light detail's spread in a striped wall patch, before / after
    def stripe_sd(lb, box):
        x0, y0, x1, y1 = box
        Lb = lb[..., 0]
        d = cv2.GaussianBlur(Lb, (0, 0), 2) - cv2.GaussianBlur(Lb, (0, 0), 14)
        return round(float(d[y0:y1, x0:x1].std()), 2)
    stripes_wall = {k: dict(before=stripe_sd(lab0, b), after=stripe_sd(labo, b)) for k, b in
                    {"wall stripes right of the art": (1480, 380, 1740, 690), "wall stripes left": (420, 480, 780, 690),
                     "rug stripes": (300, 1300, 760, 1520), "rug stripes 2": (1100, 1450, 1600, 1530)}.items()}
    Lq = cv2.resize(labo[..., 0], (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    Lq0 = cv2.resize(lab0[..., 0], (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    s_terr = hsv_s(o8.astype(np.float32) / 255)[800:880, 560:720]
    rec = dict(date="2026-11-07", by="render-agent", tokens=0, base="boho-A-fin5.png", out="boho-A-fin6.png", raw_kept="raw/boho-A-gpt-image-2-5.png",
               spec="docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 2 (G-ED.10 fix) + the manager's brief",
               steps=dict(white_balance=dict(from_K=4600, to_K=4300, linear_gains=np.round(g, 4).tolist()),
                          saturation=dict(chroma_factor=0.85, terracotta_rust_floor_S=0.45, held_px=int(terr.sum())),
                          shadows=dict(black_point_L_p05_before=round(float(np.percentile(Lq0, 0.5)), 1), black_point_L_p05_after=round(float(np.percentile(Lq, 0.5)), 1),
                                       p1_after=round(float(np.percentile(Lq, 1)), 1), toe="L* 10-45 down by up to 2.5 (sin)"),
                          highlights=dict(rolloff_from_L=90),
                          plaster=dict(hue_target_deg=82, hue_pull=0.6, chroma_factor=0.78, mask_px=int((pm > 0.5).sum()), targets_Lab=targets),
                          rug_stripes=info_stripes),
               patches_Lab=pat, light_detail_sd=stripes_wall,
               terracotta_cushion_S_median=round(float(np.median(s_terr)), 3),
               clipped_G_ED_12=dict(raw=measure_clip(RAW), fin5=measure_clip(SRC), fin6=measure_clip(OUT)),
               note="TEST, not for the site; new files only")
    json.dump(rec, open(REC, "w"), indent=1, ensure_ascii=False)
    return rec


def sheet():
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    A = Image.open(SRC).convert("RGB")
    B = Image.open(OUT).convert("RGB")
    w = 1200
    A2 = A.resize((w, int(A.height * w / A.width)), Image.LANCZOS)
    B2 = B.resize((w, int(B.height * w / B.width)), Image.LANCZOS)
    out = Image.new("RGB", (2 * w + 60, A2.height + 90), (250, 249, 247))
    d = ImageDraw.Draw(out)
    d.text((20, 18), "boho: fin5 (left) -> fin6, the grade in code (WB -300 K, chroma -15 %, toe, roll-off, plaster to sand). TEST", fill=(0, 0, 0), font=f)
    out.paste(A2, (20, 70))
    out.paste(B2, (40 + w, 70))
    out.save(os.path.join(HERE, "grade-boho-sheet.jpg"), quality=90)
    # crops: the plaster with its stripes, the rug, the cushions (100 %)
    os.makedirs(os.path.join(HERE, "grade-boho-before-after"), exist_ok=True)
    for name, box in {"wall-stripes": (1380, 300, 1900, 700), "rug": (200, 1250, 900, 1536), "cushions": (400, 680, 1500, 960),
                      "door-light": (2100, 50, 2736, 700)}.items():
        a_, b_ = A.crop(box), B.crop(box)
        im = Image.new("RGB", (a_.width * 2 + 20, a_.height), (250, 249, 247))
        im.paste(a_, (0, 0))
        im.paste(b_, (a_.width + 20, 0))
        im.save(os.path.join(HERE, "grade-boho-before-after", name + ".jpg"), quality=92)


if __name__ == "__main__":
    r = main(stripes="--no-stripes" not in sys.argv)
    sheet()
    print(json.dumps({k: v for k, v in r.items() if k in ("steps", "patches_Lab", "light_detail_sd", "terracotta_cushion_S_median", "clipped_G_ED_12")},
                     indent=1, ensure_ascii=False)[:6000])
