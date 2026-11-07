"""
qa-agent 2026-11-07: MB1 G-ED.3 colour (Lab medians on lit, representative patches; boxes by eye on the full frame, x0 y0 x1 y1) against
the reference crops (view only, scratchpad master-refs/: the product's centre third, and the crop's lightest 10 % as the photo's white),
and G-ED.4 scale (extents read on overlays/grid-*.jpg, in frame px) against the card sizes.
Usage: ~/.venvs/motion/bin/python -I measure.py. Writes data/measure.json.
"""
import json
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1")
REF = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/master-refs/"


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lch(m):
    return [round(float(m[0]), 1), round(float(m[1]), 1), round(float(m[2]), 1), round(float(np.hypot(m[1], m[2])), 1), round(float(np.degrees(np.arctan2(m[2], m[1]))), 1)]


def patch(arr, box):
    x0, y0, x1, y1 = box
    return lch(np.median(lab(arr[y0:y1, x0:x1].reshape(-1, 3).astype(float)), 0))


def ref(name, frac=(1 / 3, 2 / 3, 1 / 3, 2 / 3)):
    a = np.asarray(Image.open(REF + name).convert("RGB")).astype(float)
    H, W = a.shape[:2]
    c = a[int(frac[2] * H):int(frac[3] * H), int(frac[0] * W):int(frac[1] * W)].reshape(-1, 3)
    L = lab(a.reshape(-1, 3))
    white = np.median(L[L[:, 0] >= np.percentile(L[:, 0], 90)], 0)
    return dict(product=lch(np.median(lab(c), 0)), photo_white=lch(white))


P = {
    "nordic-MB-A": {
        "neutral: white panelling (shade side)": (1800, 340, 2000, 560),
        "bedding: duvet": (800, 1200, 1200, 1320),
        "pillowcase (right)": (2000, 650, 2350, 850),
        "lumbar": (1640, 740, 1990, 860),
        "throw": (1400, 1280, 2200, 1440),
        "bottle": (2555, 800, 2610, 930),
        "candle holder (tall)": (2665, 860, 2712, 950),
        "sconce (right, lit)": (2470, 330, 2650, 490),
        "sill vase": (330, 600, 410, 720),
        "planter": (800, 770, 920, 900),
        "jute basket": (670, 830, 800, 960),
        "generic: cloth on the chair": (40, 800, 280, 1120),
    },
    "warm-modern-MB-A": {
        "neutral: plaster wall by the bed": (1600, 580, 1800, 640),
        "bedding: duvet": (1200, 960, 1800, 1080),
        "bedding: back pillow (cream)": (2100, 655, 2400, 690),
        "pillowcase (caramel, left)": (1520, 720, 1780, 900),
        "lumbar (milk tea)": (1830, 810, 2250, 920),
        "throw (pecan)": (1400, 1200, 2200, 1400),
        "bottle": (1250, 800, 1310, 920),
        "candle holder (tall)": (1100, 830, 1150, 920),
        "sconce cone (left)": (1215, 500, 1300, 560),
        "planter": (640, 860, 880, 1080),
        "sill vase": (125, 740, 195, 900),
        "jute basket": (760, 1000, 930, 1200),
    },
}
REFS = {"bedding": "crop_bedding_natural.png", "pillow natural": "crop_pillow_natural.png", "pillow caramel": "crop_pillow_caramel.png",
        "lumbar white": "crop_cushion_white.png", "lumbar milk tea": "crop_cushion_milktea.png", "throw light grey": "crop_throw_lightgray.png",
        "throw pecan": "crop_muslin_pecan.png", "bottle D": "crop_vaseD.png", "candle holders": "crop_candles.png", "sconce wave": "crop_sconce_wave.png",
        "sconce cone": "crop_sconce_cone.png", "clay vase": "crop_claysvase.png", "planter seagrass": "crop_planter_seagrass.png",
        "planter cement": "crop_planter_cement.png", "sill vase fluted": "crop_sillvase.png", "jute basket": "crop_basket.png"}
out = {"frames": {}, "refs": {k: ref(v) for k, v in REFS.items()}}
for f, d in P.items():
    arr = np.asarray(Image.open(os.path.join(B, "nordic" if f.startswith("nordic") else "warm-modern", f + ".png")).convert("RGB"))
    out["frames"][f] = {k: patch(arr, b) for k, b in d.items()}
# G-ED.4: extents read on the grids (frame px); scale = px per cm from the pillowcase's 74 cm width in the headboard plane
S = {
    "nordic-MB-A": {"px_per_cm": round(450 / 74, 2), "basis": "the right pillowcase, 1940-2390 = 450 px for 74 cm, headboard plane",
                    "items": {"sconce (right) width": (210, 24), "sconce (right) height": (183, 20), "bottle height": (230, 24.5),
                              "candle holder (tall) height": (170, 11), "candle holder (tall) cup width": (75, 7), "lumbar width": (450, 50),
                              "mug body width (generic)": (60, 9)},
                    "ratios": {"bottle H/W": (230 / 75, 24.5 / 11), "sill vase H/W": (160 / 98, 1.85), "sconce W/H": (210 / 183, 24 / 20),
                               "candle holder (tall) H/W": (170 / 75, 11 / 7), "lumbar / pillowcase width": (450 / 450, 50 / 74)}},
    "warm-modern-MB-A": {"px_per_cm": round(530 / 74, 2), "basis": "the left caramel pillowcase, 1480-2010 = 530 px for 74 cm, headboard plane",
                         "items": {"sconce cone rim width": (133, 15), "bottle height": (192, 24.5), "candle holder (tall) height": (173, 11),
                                   "candle holder (short) height": (127, 11), "candle holder cup width": (65, 7), "lumbar width": (483, 50)},
                         "ratios": {"bottle H/W": (192 / 78, 24.5 / 11), "candle holder (tall) H/W": (173 / 65, 11 / 7), "lumbar / pillowcase width": (483 / 530, 50 / 74)}},
}
for f, s in S.items():
    k = s["px_per_cm"]
    s["scale_vs_card"] = {n: round(px / k / cm, 2) for n, (px, cm) in s["items"].items()}
    s["ratio_vs_card"] = {n: [round(a, 2), round(b, 2), round(a / b, 2)] for n, (a, b) in s["ratios"].items()}
out["scale"] = S
json.dump(out, open(os.path.join(OUT, "data", "measure.json"), "w"), indent=1, ensure_ascii=False)
for f, d in out["frames"].items():
    print("==", f)
    for k, v in d.items():
        print("  ", k.ljust(40), v)
print("== refs")
for k, v in out["refs"].items():
    print("  ", k.ljust(20), v)
for f, s in S.items():
    print("==", f, s["scale_vs_card"], s["ratio_vs_card"])
