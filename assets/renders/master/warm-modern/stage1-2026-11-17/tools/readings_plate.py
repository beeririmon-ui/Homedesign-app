#!/usr/bin/env python3
"""readings_plate.py: material tones of the MB0 plate against base.png (render-agent, 2026-11-17; 0 tokens). Median Lab per clay id
(the plate is locked to the clay), the bed wall by thirds, the black point, the window's brightness, and dE00 to base.png's patches.
  python3 readings_plate.py plate.png plate-readings.json"""
import json
import sys

import numpy as np
from PIL import Image

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/MB0-plate-id.png"
BASE = "/home/user/homedesign-app/assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png"
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])
FRAME = (77, 43, 2643, 1487)


def lab(path):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    l = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    f = l @ M.T / WP
    f = np.where(f > 216 / 24389, np.cbrt(f), (24389 / 27 * f + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de00(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    G = 0.5 * (1 - np.sqrt(((C1 + C2) / 2) ** 7 / (((C1 + C2) / 2) ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1, h2 = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dh = h2 - h1
    dh = dh - 360 * np.sign(dh) if abs(dh) > 180 else dh
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lb, Cb = (L1 + L2) / 2, (C1p + C2p) / 2
    hb = (h1 + h2 + 360) / 2 if abs(h1 - h2) > 180 else (h1 + h2) / 2
    T = 1 - 0.17 * np.cos(np.radians(hb - 30)) + 0.24 * np.cos(np.radians(2 * hb)) + 0.32 * np.cos(np.radians(3 * hb + 6)) - 0.20 * np.cos(np.radians(4 * hb - 63))
    Rt = -np.sin(np.radians(60 * np.exp(-(((hb - 275) / 25) ** 2)))) * 2 * np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))
    Sl, Sc, Sh = 1 + 0.015 * (Lb - 50) ** 2 / np.sqrt(20 + (Lb - 50) ** 2), 1 + 0.045 * Cb, 1 + 0.015 * Cb * T
    return float(np.sqrt(((L2 - L1) / Sl) ** 2 + ((C2p - C1p) / Sc) ** 2 + (dH / Sh) ** 2 + Rt * ((C2p - C1p) / Sc) * (dH / Sh)))


def main(plate, out):
    L, B = lab(plate), lab(BASE)
    ids = np.asarray(Image.open(CLAY))
    med = lambda A, m: [round(float(x), 1) for x in np.median(A[m], 0)]
    r = {}
    for g, n in ((1, "plaster, bed wall"), (2, "plaster, window wall"), (5, "plaster, rounded corner"), (9, "skirting"), (10, "floor, oak"),
                 (12, "window reveals"), (13, "window frame, bronze"), (14, "sill slab, limestone"), (20, "headboard, walnut"),
                 (23, "mattress"), (24, "nightstand fronts / sides, walnut"), (25, "nightstand tops, walnut")):
        r[n] = med(L, ids == g)
    for nm, (x0, x1) in (("left", (450, 950)), ("centre", (1100, 1620)), ("right", (1900, 2500))):
        for rn, (y0, y1) in (("upper", (80, 500)), ("lower", (500, 850))):
            m = np.zeros(ids.shape, bool)
            m[y0:y1, x0:x1] = True
            r[f"bed wall {nm} {rn}"] = med(L, m & (ids == 1))
    m = np.zeros(ids.shape, bool)
    m[1230:1530, 2250:2720] = True
    r["floor, right of the bed (x 2250-2720, y 1230-1530)"] = med(L, m & (ids == 10))
    base = {"back wall (x 1150-2650, y 200-1000)": [round(float(x), 1) for x in np.median(B[200:1000, 1150:2650].reshape(-1, 3), 0)],
            "floor right (x 2400-2650, y 1380-1480)": [round(float(x), 1) for x in np.median(B[1380:1480, 2400:2650].reshape(-1, 3), 0)],
            "floor far right (x 2500-2700, y 1300-1350)": [round(float(x), 1) for x in np.median(B[1300:1350, 2500:2700].reshape(-1, 3), 0)],
            "floor mid-left (x 950-1200, y 1180-1300)": [round(float(x), 1) for x in np.median(B[1180:1300, 950:1200].reshape(-1, 3), 0)],
            "window frames (bath README)": [22.5, 4.2, 6.8]}
    fl = r["floor, right of the bed (x 2250-2720, y 1230-1530)"]
    cmp = {"plaster bed wall vs base back wall": dict(dL=round(r["plaster, bed wall"][0] - base["back wall (x 1150-2650, y 200-1000)"][0], 1),
                                                       dE00=round(de00(r["plaster, bed wall"], base["back wall (x 1150-2650, y 200-1000)"]), 2), rule="+-3 L*"),
           "bronze vs base window frames (id median)": dict(dE00=round(de00(r["window frame, bronze"], base["window frames (bath README)"]), 2),
                                                           note="the frame is 8-12 px wide here; the id median takes in glass and reveal edges")}
    pc, bc = L[100:850, 215:265], B[200:900, 300:330]
    pcore, bcore = np.median(pc[pc[..., 0] < 30], 0), np.median(bc[bc[..., 0] < 30], 0)
    cmp["bronze core vs base.png frame core (L* < 30; plate x 215-265, y 100-850; base x 300-330, y 200-900)"] = dict(
        plate=[round(float(x), 1) for x in pcore], base=[round(float(x), 1) for x in bcore], dE00=round(de00(pcore, bcore), 2), rule="dE00 <= 3")
    for k in ("floor right (x 2400-2650, y 1380-1480)", "floor far right (x 2500-2700, y 1300-1350)", "floor mid-left (x 950-1200, y 1180-1300)"):
        cmp[f"floor right vs base {k}"] = dict(dE00=round(de00(fl, base[k]), 2), dE00_chroma_only=round(de00([base[k][0]] + fl[1:], base[k]), 2), rule="dE00 <= 3")
    x0, y0, x1, y1 = FRAME
    f = L[y0:y1, x0:x1, 0]
    win = (ids == 0) | (ids == 15)
    rgb = np.asarray(Image.open(plate).convert("RGB")).astype(float)
    rep = dict(plate=plate, by_material=r, base_png=base, compare=cmp,
               black_point=dict(p0_5=round(float(np.percentile(f, 0.5)), 2), p1=round(float(np.percentile(f, 1)), 2), p5=round(float(np.percentile(f, 5)), 2), rule="WM-G1: 11-14"),
               window_brightest=dict(window_p99=round(float(np.percentile(L[win][:, 0], 99)), 1), frame_p99=round(float(np.percentile(f, 99)), 1),
                                     non_window_p99=round(float(np.percentile(L[y0:y1, x0:x1][~win[y0:y1, x0:x1]][:, 0], 99)), 1)),
               frame_mean_L_8bit=round(float((rgb[y0:y1, x0:x1] * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1))
    json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
