"""
qa-agent 2026-11-10: G-ED.2-G-ED.4 on the caramel pillowcases of warm-modern-MB-A-fix5 (P6b), with QA's own code:
  colour  median Lab (sRGB D65, the same formula as measure.py) on QA's patch (left: x 1520-1780, y 720-900, the lit side, clear of the
          lumbar and its shadow) and a right patch (x 2300-2560, y 720-900), fix4 and fix5; CIEDE2000 (QA's own implementation, Sharma 2005)
          against the card swatch (qa/reports/2026-11-07-ged-master-mb1/data/measure.json refs['pillow caramel'].product) and fix4;
          hue and chroma; L* against the cream back pillow and the plaster wall in the same light (G-ED.3's neighbour relation)
  grain   linen texture: SD of the L* high-pass (sigma 1.6 and 4) in the same patches, fix4 and fix5, and the ratio
  size    G-ED.4: the left pillowcase's corner-to-corner width (the room's scale basis, 530 px = 74 cm) and the lumbar's width
Usage: ~/.venvs/motion/bin/python -I fidelity.py. Writes data/fidelity.json.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")
REF = json.load(open(os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1/data/measure.json")))
SW = REF["refs"]["pillow caramel"]["product"][:3]
PL, PR = (1520, 720, 1780, 900), (2300, 720, 2560, 900)
BACK = (1600, 682, 1760, 700)      # the cream back pillow above the left pillowcase, outside the comp mask (fix4 = fix5 there)
WALL = (2680, 560, 2730, 640)      # the plaster wall right of the headboard, same side light


def lab(x8):
    c = x8 / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def ciede2000(p, q):
    L1, a1, b1 = p
    L2, a2, b2 = q
    Cab = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    G = 0.5 * (1 - np.sqrt(Cab ** 7 / (Cab ** 7 + 25.0 ** 7)))
    ap1, ap2 = a1 * (1 + G), a2 * (1 + G)
    Cp1, Cp2 = np.hypot(ap1, b1), np.hypot(ap2, b2)
    hp1 = np.degrees(np.arctan2(b1, ap1)) % 360 if Cp1 else 0.0
    hp2 = np.degrees(np.arctan2(b2, ap2)) % 360 if Cp2 else 0.0
    dL, dC = L2 - L1, Cp2 - Cp1
    if Cp1 * Cp2 == 0:
        dh = 0.0
    else:
        dh = hp2 - hp1
        dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dH = 2 * np.sqrt(Cp1 * Cp2) * np.sin(np.radians(dh / 2))
    Lm, Cm = (L1 + L2) / 2, (Cp1 + Cp2) / 2
    if Cp1 * Cp2 == 0:
        hm = hp1 + hp2
    elif abs(hp1 - hp2) <= 180:
        hm = (hp1 + hp2) / 2
    else:
        hm = (hp1 + hp2 + 360) / 2 if hp1 + hp2 < 360 else (hp1 + hp2 - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.20 * np.cos(np.radians(4 * hm - 63))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cm, 1 + 0.015 * Cm * T
    RT = -2 * np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)) * np.sin(np.radians(60 * np.exp(-(((hm - 275) / 25) ** 2))))
    return float(np.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH)))


# self-test on Sharma, Wu & Dalal (2005) table pairs 1, 7 and 17
for p, q, e in (((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425), ((50, 0, 0), (50, -1, 2), 2.3669), ((50, 2.5, 0), (73, 25, -18), 27.1492)):
    assert abs(ciede2000(p, q) - e) < 1e-3, (p, q, ciede2000(p, q), e)

f = {k: np.asarray(Image.open(os.path.join(B, f"warm-modern-MB-A-{k}.png")).convert("RGB")).astype(np.float64) for k in ("fix4", "fix5")}
Lab = {k: lab(v) for k, v in f.items()}


def med(k, box):
    x0, y0, x1, y1 = box
    return [round(float(v), 1) for v in np.median(Lab[k][y0:y1, x0:x1].reshape(-1, 3), 0)]


def grain(k, box, s):
    x0, y0, x1, y1 = box
    L = Lab[k][..., 0]
    hp = L - cv2.GaussianBlur(L, (0, 0), s)
    return round(float(hp[y0:y1, x0:x1].std()), 2)


out = {"swatch": SW, "swatch_hue": round(float(np.degrees(np.arctan2(SW[2], SW[1]))), 1), "swatch_chroma": round(float(np.hypot(SW[1], SW[2])), 1)}
for nm, box in (("left (QA's patch)", PL), ("right (lamp's shadow)", PR)):
    r = {}
    for k in ("fix4", "fix5"):
        v = med(k, box)
        r[k] = dict(Lab=v, hue=round(float(np.degrees(np.arctan2(v[2], v[1]))), 1), chroma=round(float(np.hypot(v[1], v[2])), 1),
                    dE00_vs_swatch=round(ciede2000(SW, v), 2), grain_s1_6=grain(k, box, 1.6), grain_s4=grain(k, box, 4.0))
    r["dE00_fix5_vs_fix4"] = round(ciede2000(r["fix4"]["Lab"], r["fix5"]["Lab"]), 2)
    r["grain_ratio_fix5_over_fix4"] = [round(r["fix5"]["grain_s1_6"] / r["fix4"]["grain_s1_6"], 2), round(r["fix5"]["grain_s4"] / r["fix4"]["grain_s4"], 2)]
    out[nm] = r
out["neighbours_fix5"] = {"cream back pillow above the left pillowcase": med("fix5", BACK), "plaster wall": med("fix5", WALL)}
out["L_left_minus_back_pillow"] = {k: round(med(k, PL)[0] - med(k, BACK)[0], 1) for k in ("fix4", "fix5")}
out["L_left_minus_wall"] = {k: round(med(k, PL)[0] - med(k, WALL)[0], 1) for k in ("fix4", "fix5")}
out["card_L_minus_photo_white"] = round(SW[0] - REF["refs"]["pillow caramel"]["photo_white"][0], 1)
# G-ED.4: the left pillowcase corner to corner (caramel: red well above green, not the dark walnut), and the lumbar (lumbar.py's mask)
im = f["fix5"]
r_, g_ = im[..., 0], im[..., 1]
Y = im.mean(2)
car = (((r_ - g_) > 0.28 * Y + 8) & (Y > 33) & (Y < 170)).astype(np.uint8)
car[:690], car[962:], car[:, 2025:] = 0, 0, 0
car = cv2.morphologyEx(car, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
n, lbl, st, _ = cv2.connectedComponentsWithStats(car, 8)
i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
lw = int(st[i, cv2.CC_STAT_WIDTH])
lum = np.asarray(Image.open(os.path.join(OUT, "data/qa-lumbar-mask.png"))) > 127
mid = [int(np.nonzero(lum[y])[0].max() - np.nonzero(lum[y])[0].min() + 1) for y in range(840, 920, 10)]
out["G-ED.4"] = dict(left_pillowcase_corner_to_corner_px=lw, left_box=[int(st[i, 0]), int(st[i, 1]), int(st[i, 0] + lw - 1), int(st[i, 1] + st[i, 3] - 1)],
                     scale_basis_px=530, left_vs_basis=round(lw / 530, 3), lumbar_width_px_rows_840_910=mid,
                     lumbar_over_pillowcase=round(float(np.median(mid)) / lw, 3), card_ratio=round(50 / 74, 3),
                     lumbar_ratio_vs_card=round(float(np.median(mid)) / lw / (50 / 74), 3))
json.dump(out, open(os.path.join(OUT, "data", "fidelity.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
