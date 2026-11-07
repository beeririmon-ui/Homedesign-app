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
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix5-clay-r3/overlays")
ITEMS = [
    ("mc-edges-100", "modern-country-A-mc1.png", "modern-country-A-fix3.png", (1060, 1180, 1700, 1536), 1),
    ("mc-edge-left-x4", "modern-country-A-mc1.png", "modern-country-A-fix3.png", (1090, 1200, 1150, 1360), 4),
    ("mc-edge-right-x4", "modern-country-A-mc1.png", "modern-country-A-fix3.png", (1596, 1200, 1656, 1360), 4),
    ("mc-bowl-x2", "modern-country-A-mc1.png", "modern-country-A-fix3.png", (1010, 1080, 1280, 1210), 2),
    ("mc-vase-x2", "modern-country-A-mc1.png", "modern-country-A-fix3.png", (1860, 500, 2060, 780), 2),
    ("mc-vase-shoulder-x4", "modern-country-A-mc1.png", "modern-country-A-fix3.png", (1975, 530, 2035, 620), 4),
    ("mc-table-100", "modern-country-A.png", "modern-country-A-fix3.png", (960, 1030, 1860, 1300), 1),
    ("mc-sill-100", "modern-country-A.png", "modern-country-A-fix3.png", (1760, 450, 2240, 810), 1),
    ("boho-door-100", "boho-A-fin4.png", "boho-A-fin5.png", (1940, 700, 2340, 1110), 1),
    ("boho-door-x3", "boho-A-fin4.png", "boho-A-fin5.png", (2000, 740, 2320, 1000), 3),
    ("boho-grade-wall", "boho-A-fin5.png", "boho-A-fin6.png", (700, 150, 1500, 600), 1),
    ("boho-grade-sofa", "boho-A-fin5.png", "boho-A-fin6.png", (200, 650, 1500, 1100), 1),
    ("boho-grade-edges-x3", "boho-A-fin5.png", "boho-A-fin6.png", (1040, 160, 1180, 300), 3),
    ("boho-grade-plant-x3", "boho-A-fin5.png", "boho-A-fin6.png", (1700, 420, 1900, 620), 3),
    ("med-bench-100", "mediterranean-A-ed5.png", "mediterranean-A-ed6.png", (150, 620, 1900, 1150), 1),
    ("med-left-x3", "mediterranean-A-ed5.png", "mediterranean-A-ed6.png", (180, 680, 420, 860), 3),
    ("med-fringe-x4", "mediterranean-A-ed5.png", "mediterranean-A-ed6.png", (300, 700, 460, 780), 4),
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
