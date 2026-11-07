"""
qa-agent 2026-11-07: G-ED.9 views. For each item: before | after at the given scale (NEAREST for >1, so seams are not
smoothed), and a x4 contrast stretch of the after (percentiles 1-60 per crop, as in the 11-07 report).
Writes overlays/<tag>.jpg and overlays/<tag>-stretch.jpg. Usage: ~/.venvs/motion/bin/python -I crops.py
"""
import os

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
R = os.path.join(REPO, "assets/renders/editorial-phase-b-2026-11-06")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/overlays")
ITEMS = [
    ("boho-seam", "boho-A-fin2.png", "boho-A-fin4.png", (330, 190, 470, 530), 2),
    ("boho-basket", "boho-A-fin3.png", "boho-A-fin4.png", (1940, 700, 2340, 1110), 1),
    ("boho-door-x3", "boho-A-fin3.png", "boho-A-fin4.png", (2000, 740, 2300, 1000), 3),
    ("med-cush-left", "mediterranean-A-ed4.png", "mediterranean-A-ed5.png", (180, 680, 640, 1040), 1),
    ("med-cush-mid", "mediterranean-A-ed4.png", "mediterranean-A-ed5.png", (890, 700, 1250, 990), 1),
    ("med-fringe-x4", "mediterranean-A-ed4.png", "mediterranean-A-ed5.png", (300, 700, 460, 780), 4),
    ("med-rim-x4", "mediterranean-A-ed4.png", "mediterranean-A-ed5.png", (1370, 1120, 1510, 1215), 4),
    ("jp-jar-x3", "japandi-A-ed4.png", "japandi-A-ed5.png", (570, 890, 770, 1160), 3),
    ("jp-base-x4", "japandi-A-ed4.png", "japandi-A-ed5.png", (600, 1080, 760, 1160), 4),
    ("wm-pendant", "warm-modern-A-ed4.png", "warm-modern-A-ed5.png", (1280, 0, 1640, 290), 1),
    ("wm-ring4-x4", "warm-modern-A-ed4.png", "warm-modern-A-ed5.png", (1320, 160, 1600, 250), 4),
    ("mc-table", "modern-country-A.png", "modern-country-A-mc1.png", (960, 1030, 1860, 1300), 1),
    ("mc-cups-x3", "modern-country-A.png", "modern-country-A-mc1.png", (1550, 1080, 1830, 1215), 3),
    ("mc-runner-front", "modern-country-A.png", "modern-country-A-mc1.png", (1060, 1180, 1700, 1536), 1),
    ("mc-sill", "modern-country-A.png", "modern-country-A-mc1.png", (1760, 450, 2240, 810), 1),
    ("mc-fly-x4", "modern-country-A.png", "modern-country-A-mc1.png", (1560, 835, 1645, 905), 4),
    ("mc-curtain-left", "modern-country-A.png", "modern-country-A-mc1.png", (1560, 40, 1820, 780), 1),
    ("mc-curtain-right", "modern-country-A.png", "modern-country-A-mc1.png", (2320, 40, 2600, 990), 1),
    ("mc-rug", "modern-country-A.png", "modern-country-A-mc1.png", (280, 1370, 2736, 1536), 1),
    ("mc-rug-legs-x2", "modern-country-A-fix1.png", "modern-country-A-mc1.png", (780, 1380, 1000, 1536), 2),
    ("mc-rug-legs2-x2", "modern-country-A-fix1.png", "modern-country-A-mc1.png", (1760, 1360, 1960, 1536), 2),
    ("mc-rug-legs3-x2", "modern-country-A-fix1.png", "modern-country-A-mc1.png", (2340, 1340, 2520, 1480), 2),
]


def img(p):
    return Image.open(os.path.join(R, p)).convert("RGB")


cache = {}
if __name__ == "__main__":
    for tag, a, b, box, s in ITEMS:
        A = cache.setdefault(a, img(a))
        B = cache.setdefault(b, img(b))
        ca, cb = A.crop(box), B.crop(box)
        w, h = ca.width * s, ca.height * s
        rs = Image.NEAREST if s > 1 else Image.BICUBIC
        vertical = ca.width > 1.6 * ca.height
        if vertical:
            out = Image.new("RGB", (w, 2 * h + 8), (40, 40, 40))
            out.paste(ca.resize((w, h), rs), (0, 0))
            out.paste(cb.resize((w, h), rs), (0, h + 8))
        else:
            out = Image.new("RGB", (2 * w + 8, h), (40, 40, 40))
            out.paste(ca.resize((w, h), rs), (0, 0))
            out.paste(cb.resize((w, h), rs), (w + 8, 0))
        if out.width > 2000:
            out = out.resize((2000, int(out.height * 2000 / out.width)), Image.BICUBIC)
        out.save(os.path.join(OUT, f"{tag}.jpg"), quality=92)
        arr = np.asarray(cb).astype(float)
        lo, hi = np.percentile(arr, 1), np.percentile(arr, 60)
        st = np.clip((arr - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
        si = Image.fromarray(st).resize((cb.width * 4, cb.height * 4), Image.NEAREST) if cb.width * 4 <= 1600 else Image.fromarray(st)
        si.save(os.path.join(OUT, f"{tag}-stretch.jpg"), quality=88)
    print("ok", len(ITEMS))
