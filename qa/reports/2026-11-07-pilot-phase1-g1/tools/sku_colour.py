"""
qa-agent 2026-11-07: the cushion colours against their SKU photos, white-normalised on both sides (G1.2's method; the designer's set-C rule in
docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md section 13.1 (4): rotate the hue only if the render is off the SKU photo by > dE 5 or > 8 deg).
- Photo: linear RGB of the centre third (median), divided by the photo's own white (the lightest 10 %, median), i.e. its background is white.
- Frame: linear RGB of the item (cushion-polys.json, eroded 13 px, median), divided by the frame's white, taken as the back wall at the
  plan point (0.20, 0, 1.95) (41 x 41 median) over the Bible's plaster #ECE5DA, i.e. the wall reads as its own colour under white light.
- Both scaled to the photo item's Y (exposure out), then Lab D65: hue difference, chroma ratio (frame / photo) and dE2000.
Usage: ~/.venvs/motion/bin/python -I sku_colour.py <suffix, e.g. v2-graded | v3-graded>. Writes data/sku-colour-<suffix>.json.
"""
import importlib.util
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
spec2 = importlib.util.spec_from_file_location("cu", os.path.join(HERE, "cushions.py"))
src = open(os.path.join(HERE, "cushions.py")).read()
head = src.split("\nout = {}")[0]            # the constants (REFS, REF, POLYS, P, OUT) without running the measure
ns = {}
exec(compile(head, "cushions_head", "exec"), ns)
REFS, REF, POLYS, P, OUT = ns["REFS"], ns["REF"], ns["POLYS"], ns["P"], ns["OUT"]
SUF = sys.argv[1] if len(sys.argv) > 1 else "v2-graded"
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WN = np.array([0.9505, 1.0, 1.089])


def lin(rgb8):
    c = np.asarray(rgb8, float) / 255.0
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def lab_lin(c):
    xyz = (M @ c) / WN
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de2000(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hbp = (h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.2 * np.cos(np.radians(4 * hbp - 63))
    SL = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    RT = -2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hbp - 275) / 25) ** 2)))
    return float(np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH)))


u, v, _ = r1.project(r1.CAM["M0"], 0.20, 0, 1.95)
WX, WY = int((116 + u * 3840) / 4072 * 2720), int((65 + v * 2160) / 2290 * 1530)
PLASTER = lin([0xEC, 0xE5, 0xDA])
out = {"suffix": SUF, "wall_px": [WX, WY]}
for S in ("A", "B", "C"):
    arr = np.asarray(Image.open(os.path.join(P, f"composite-set-{S}-{SUF}.png")).convert("RGB"))
    wall = np.median(lin(arr[WY - 20:WY + 21, WX - 20:WX + 21].reshape(-1, 3)), 0)
    fw = wall / PLASTER                                  # the frame's light colour (and exposure)
    ox, oy = POLYS[S]["origin"]
    res = {}
    for item, poly in POLYS[S].items():
        if item == "origin" or not isinstance(poly, list):
            continue
        ks = [k for k in REFS[S] if k.lower() in item.lower()]
        if not ks:
            continue
        key = max(ks, key=len)
        pts = np.array([[ox + x, oy + y] for x, y in poly], np.int32)
        m = np.zeros(arr.shape[:2], np.uint8)
        cv2.fillPoly(m, [pts], 1)
        mi = cv2.erode(m, np.ones((13, 13), np.uint8)) > 0
        f_lin = np.median(lin(arr[mi]), 0) / fw
        ra = np.asarray(Image.open(REF + REFS[S][key]).convert("RGB"))
        cy, cx = ra.shape[0] // 2, ra.shape[1] // 2
        centre = ra[cy - ra.shape[0] // 6:cy + ra.shape[0] // 6, cx - ra.shape[1] // 6:cx + ra.shape[1] // 6].reshape(-1, 3)
        allp = ra.reshape(-1, 3)
        Yp = lin(allp) @ M[1]
        pw = np.median(lin(allp[Yp >= np.percentile(Yp, 90)]), 0)
        p_lin = np.median(lin(centre), 0) / pw
        f_lin = f_lin * ((M[1] @ p_lin) / max(M[1] @ f_lin, 1e-6))          # exposure matched to the photo
        lf, lp = lab_lin(f_lin), lab_lin(p_lin)
        hf, hp = np.degrees(np.arctan2(lf[2], lf[1])), np.degrees(np.arctan2(lp[2], lp[1]))
        Cf, Cp = np.hypot(lf[1], lf[2]), np.hypot(lp[1], lp[2])
        res[item] = dict(sku_photo=REFS[S][key], frame_norm_lab=[round(float(x), 1) for x in lf], photo_norm_lab=[round(float(x), 1) for x in lp],
                         hue_frame=round(float(hf), 1), hue_photo=round(float(hp), 1), d_hue_deg=round(float(hf - hp), 1),
                         chroma_ratio=round(float(Cf / max(Cp, 1e-6)), 2), dE2000=round(de2000(lp, lf), 1),
                         rule_C="dE <= 5 and |dh| <= 8 (designer 13.1 (4))", within=bool(de2000(lp, lf) <= 5 and abs(hf - hp) <= 8) if Cp > 4 else bool(de2000(lp, lf) <= 5))
    out[S] = dict(frame_light_vs_plaster=[round(float(x), 3) for x in fw], items=res)
json.dump(out, open(os.path.join(OUT, "data", f"sku-colour-{SUF}.json"), "w"), indent=1)
for S in "ABC":
    for it, r in out[S]["items"].items():
        print(SUF, S, it[:42].ljust(42), "frame", r["frame_norm_lab"], "photo", r["photo_norm_lab"], "dh", r["d_hue_deg"], "Cr", r["chroma_ratio"], "dE00", r["dE2000"], r["within"])
