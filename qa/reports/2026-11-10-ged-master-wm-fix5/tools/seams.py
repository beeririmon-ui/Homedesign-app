"""
qa-agent 2026-11-10: G-ED.9 sheets on fix4 -> fix5 (P6b): for each zone, before | after at 100 % (context), x4 NEAREST, and the x4 contrast
stretch (percentiles 1-60, G-ED.9's stretch) of the after; plus an 'after with the comp mask outline' panel.
Usage: ~/.venvs/motion/bin/python -I seams.py. Writes overlays/seam-*.jpg.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/warm-modern")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5/overlays")
f4 = np.asarray(Image.open(os.path.join(B, "warm-modern-MB-A-fix4.png")).convert("RGB"))
f5 = np.asarray(Image.open(os.path.join(B, "warm-modern-MB-A-fix5.png")).convert("RGB"))
comp = np.asarray(Image.open(os.path.join(B, "raw/P6b-comp-mask.png"))) > 127
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
ZONES = {
    "gap": (1975, 690, 2085, 830),
    "lumbar-top-left": (1835, 790, 1905, 880),
    "lumbar-right": (2185, 800, 2275, 940),
    "left-end": (1465, 670, 1560, 965),
    "right-end": (2560, 670, 2665, 965),
    "top-edge-left": (1560, 660, 1800, 740),
    "top-edge-right": (2050, 655, 2330, 735),
    "top-edge-right2": (2330, 660, 2600, 740),
    "back-pillow-left-end": (1400, 660, 1520, 780),
    "duvet-edge-left": (1470, 900, 1700, 975),
    "duvet-edge-right": (2280, 900, 2660, 975),
    "lumbar-shadow-right": (2200, 800, 2420, 950),
    # x5-x6 follow-ups: the 12 px ring on the back pillows (deviation 2) and the comp mask's islands on the duvet
    "ring-top-left-a": (1560, 672, 1680, 742),
    "ring-top-right-a": (2045, 668, 2165, 728),
    "ring-top-right-b": (2240, 672, 2360, 732),
    "ring-top-right-c": (2440, 670, 2560, 730),
    "duvet-specks-a": (2380, 915, 2480, 962),
    "duvet-specks-b": (2480, 915, 2580, 962),
    "duvet-specks-c": (2300, 915, 2380, 962),
    "duvet-left-corner": (1470, 905, 1560, 975),
}
SCALE = {"ring-top-left-a": 5, "ring-top-right-a": 5, "ring-top-right-b": 5, "ring-top-right-c": 5,
         "duvet-specks-a": 6, "duvet-specks-b": 6, "duvet-specks-c": 6, "duvet-left-corner": 6}


def stretch(a):
    lo, hi = np.percentile(a, 1), np.percentile(a, 60)
    return np.clip((a.astype(np.float32) - lo) * 255.0 / max(hi - lo, 1) * 0.6, 0, 255).astype(np.uint8)


def sheet(name, box, sc=4):
    x0, y0, x1, y1 = box
    a, b = f4[y0:y1, x0:x1], f5[y0:y1, x0:x1]
    cm = comp[y0:y1, x0:x1]
    e = cm & ~cv2.erode(cm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    bm = b.copy()
    bm[e] = (0, 220, 255)
    tiles = [("fix4", a), ("fix5", b), ("fix5 + mask edge", bm), ("fix5 stretch x4", stretch(b))]
    w, h = (x1 - x0) * sc, (y1 - y0) * sc
    W = len(tiles) * (w + 10) + 10
    im = Image.new("RGB", (W, h + 40), (246, 244, 240))
    dr = ImageDraw.Draw(im)
    dr.text((10, 2), f"{name}  x {x0}-{x1}, y {y0}-{y1}  (x{sc}, NEAREST)", fill=(0, 0, 0), font=FONT)
    for i, (t, arr) in enumerate(tiles):
        dr.text((10 + i * (w + 10), 20), t, fill=(0, 0, 0), font=FONT)
        im.paste(Image.fromarray(arr).resize((w, h), Image.NEAREST), (10 + i * (w + 10), 38))
    im.save(os.path.join(OUT, f"seam-{name}.jpg"), quality=92)


def context100():
    """the bed head at 100 %: fix4 over fix5"""
    x0, y0, x1, y1 = 1380, 620, 2700, 1000
    a, b = Image.fromarray(f4[y0:y1, x0:x1]), Image.fromarray(f5[y0:y1, x0:x1])
    im = Image.new("RGB", (a.width + 20, a.height * 2 + 70), (246, 244, 240))
    dr = ImageDraw.Draw(im)
    dr.text((10, 4), "bed head 100 %: fix4 (top), fix5 (bottom)", fill=(0, 0, 0), font=FONT)
    im.paste(a, (10, 26))
    im.paste(b, (10, 50 + a.height))
    im.save(os.path.join(OUT, "bed-head-100.jpg"), quality=92)


if __name__ == "__main__":
    names = sys.argv[1:] or list(ZONES)
    for n in names:
        sheet(n, ZONES[n], SCALE.get(n, 4 if (ZONES[n][2] - ZONES[n][0]) <= 130 else 2))
    context100()
    # the pillow tops at 100 %, native size (fix4 above, fix5 below): the ring as the eye sees it
    for nm, box in (("tops-right", (1990, 630, 2690, 800)), ("tops-left", (1440, 640, 2040, 800))):
        x0, y0, x1, y1 = box
        im = Image.new("RGB", (x1 - x0, (y1 - y0) * 2 + 30), (246, 244, 240))
        ImageDraw.Draw(im).text((5, y1 - y0 + 8), "fix4 above, fix5 below, 100 %", fill=(0, 0, 0), font=FONT)
        im.paste(Image.fromarray(f4[y0:y1, x0:x1]), (0, 0))
        im.paste(Image.fromarray(f5[y0:y1, x0:x1]), (0, y1 - y0 + 30))
        im.save(os.path.join(OUT, f"ring-{nm}-100.png"))
