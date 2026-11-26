#!/usr/bin/env python3
"""hwlib.py: shared helpers of the FB13 stage-A hero run (the M0-W canvas 2720 x 1530, the frame box, the clay's masks, the light
measures of the gate, the one display grade)."""
import json
import os

import cv2
import numpy as np
from PIL import Image

SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13-hero"
OUT = os.path.join(SP, "out")
REPO = "/home/user/homedesign-app"
FB13 = os.path.join(REPO, "assets/renders/living-room/warm-modern/fb13-2026-11-25")
FB = (77.4852652259332, 43.427947598253276, 2642.5147347740667, 1486.5720524017468)
W, H = 2720, 1530
PI = {"rug": 801, "vase": 803, "planter": 804, "basket": 805, "magazine-holder": 806, "floor-lamp": 807, "framed-art": 808,
      "accent-sconces": 809, "pendant": 810, "bowl": 811, "candle-holders": 812, "coffee-table": 813, "cushion-left": 814,
      "cushion-right": 815, "cushion-lumbar": 816, "throw": 817, "olive": 830, "candles": 831, "cord": 833}

srgb2lin = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
lin2srgb = lambda a: np.where(a <= 0.0031308, a * 12.92, 1.055 * np.clip(a, 0, None) ** (1 / 2.4) - 0.055)


def to_lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def from_lab(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def rd(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def wr(p, rgb, **kw):
    Image.fromarray(np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(p, **kw)


def shifted_map(name, scale):
    a = np.asarray(Image.open(os.path.join(FB13, name))).astype(np.float32) / scale
    a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
    dy = 0.035 * (FB[3] - FB[1])
    return cv2.warpAffine(a, np.float32([[1, 0, 0], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


_C = {}


def maps():
    if not _C:
        _C["idx"] = np.load(os.path.join(OUT, "passes-full.npz"))["idx"]
        _C["idx_p"] = np.load(os.path.join(OUT, "passes-plate.npz"))["idx"]
        _C["depth"] = np.load(os.path.join(OUT, "passes-full.npz"))["depth"]
        _C["depth_p"] = np.load(os.path.join(OUT, "passes-plate.npz"))["depth"]
        _C["sun"] = shifted_map("m0w-sun.png", 255.0)
        for k in ("accent-sconces", "floor-lamp", "pendant", "wall-sconce"):
            _C["light-" + k] = shifted_map(f"m0w-light-{k}.png", 65535.0)
    return _C


def frame_mask():
    m = np.zeros((H, W), bool)
    m[int(np.ceil(FB[1])):int(np.floor(FB[3])), int(np.ceil(FB[0])):int(np.floor(FB[2]))] = True
    return m


def frame_view(img, size=(1920, 1080)):
    x0, y0, x1, y1 = FB
    sx, sy = (x1 - x0) / size[0], (y1 - y0) / size[1]
    M = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    return cv2.warpAffine(img, M, size, flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)


def light_masks(hero=False):
    """the plaster of the back wall in open shade and in the sun (the clay's maps), away from every product and lamp pool"""
    m = maps()
    idx = m["idx"] if hero else m["idx_p"]
    back = (idx == 5) & frame_mask()
    back = cv2.erode(back.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    quiet = (m["light-accent-sconces"] < 0.10) & (m["light-floor-lamp"] < 0.10) & (m["light-pendant"] < 0.15)
    sun_d = cv2.dilate((m["sun"] > 0.04).astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    shade = back & ~sun_d & (quiet if hero else True)
    sunny = back & (cv2.erode((m["sun"] > 0.55).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0)
    return shade, sunny


def measure(rgb, hero=False):
    lab = to_lab(rgb)
    shade, sunny = light_masks(hero)
    fm = frame_mask()
    r = dict(shade_px=int(shade.sum()), sun_px=int(sunny.sum()))
    r["plaster_shade_Lab"] = [round(float(v), 2) for v in np.median(lab[shade], axis=0)]
    r["plaster_shade_L_p10_p90"] = [round(float(np.percentile(lab[..., 0][shade], q)), 2) for q in (10, 90)]
    if sunny.any():
        r["plaster_sun_Lab"] = [round(float(v), 2) for v in np.median(lab[sunny], axis=0)]
        r["plaster_sun_L_p10_p90"] = [round(float(np.percentile(lab[..., 0][sunny], q)), 2) for q in (10, 90)]
    r["black_point_L_p0.5"] = round(float(np.percentile(lab[..., 0][fm], 0.5)), 2)
    r["L_p50"] = round(float(np.percentile(lab[..., 0][fm], 50)), 2)
    r["L_p99.5"] = round(float(np.percentile(lab[..., 0][fm], 99.5)), 2)
    return r


def tone_curve(xs, ys):
    """a monotone curve on L* through the control points (PCHIP-like by np.interp on a dense, smoothed table)"""
    t = np.linspace(0, 100, 1001)
    y = np.interp(t, xs, ys)
    k = np.ones(41) / 41.0
    ypad = np.concatenate([np.full(20, y[0]) - (np.arange(20, 0, -1) * (y[1] - y[0])), y, np.full(20, y[-1]) + np.arange(1, 21) * (y[-1] - y[-2])])
    return t, np.convolve(ypad, k, mode="valid")


GRADE = dict(
    name="m0w-g2",
    xs=[0.0, 3.6, 26.7, 50.0, 65.5, 77.5, 93.0, 96.0, 100.0],
    ys=[4.8, 10.6, 36.0, 62.5, 76.5, 83.6, 89.6, 93.2, 98.8],
    a_shift=1.0, b_shift=2.5,                    # the shade: bone (a 1.5, b 7.5), never grey
    warm=dict(L0=80.0, L1=92.0, a=0.8, b=3.5),   # the sun and the lit plaster: warm white-gold (a about 3, b about 12), not orange
    note="ONE display grade for P-W, H-W and every edit of H-W (pointwise in Lab: commutes with the layers' compositing). The owner's "
         "note of 2026-11-26 on concept B ('a little too dramatic') and the house light spec (docs/proposals/wm-fb16-house-light-2026-11-26.md): "
         "shade plaster L about 76 (74-80), sunlit plaster about 89-90 (88-92), black point 10-11",
)


def apply_grade(rgb, gr=None):
    """ONE display grade, pointwise: L* through a monotone curve; a*, b* shifted (the shade's bone), a little more in the highlights
    (the sun's warm white-gold). The same for the plate, the hero and every edit."""
    gr = gr or GRADE
    lab = to_lab(rgb)
    t, y = tone_curve(gr["xs"], gr["ys"])
    L_in = lab[..., 0]
    Lo = np.interp(L_in, t, y)
    w = gr.get("warm")
    hi = np.clip((Lo - w["L0"]) / (w["L1"] - w["L0"]), 0, 1) if w else 0.0
    hi = hi * hi * (3 - 2 * hi) if w else 0.0
    # the shift fades in the darkest tones (a black stays neutral)
    lo = np.clip(Lo / 25.0, 0, 1)
    a_ = lab[..., 1] + (gr.get("a_shift", 0.0) + (w["a"] * hi if w else 0.0)) * lo
    b_ = lab[..., 2] + (gr.get("b_shift", 0.0) + (w["b"] * hi if w else 0.0)) * lo
    return from_lab(np.dstack([Lo, a_, b_]))


if __name__ == "__main__":
    import sys
    im = rd(sys.argv[1])
    if im.shape[:2] != (H, W):
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA)
    print(json.dumps(measure(im, hero=len(sys.argv) > 2), indent=1))
