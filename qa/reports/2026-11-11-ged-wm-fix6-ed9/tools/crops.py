"""
qa-agent 2026-11-11: G-ED.9 crops, before | after, for the eye. 100 % (pixels as stored), x4 NEAREST, and a x4 contrast stretch
(the gate's: percentiles 1-60 of the two crops together mapped to 0-255, the same mapping on both sides).
Master (fix5 | fix6): (b)'s region with the mask outline in cyan; its left end at the cushion, its right end and base, its top; the
(b)-only lift as a heat map; the muslin's deep folds; the void under the nightstand and the walnut drawer fronts; the dark sheet at 100 %.
Living room (ed8 | ed9): the black bowl; under the table and the walnut drum bases; the bronze window frame; the dark sheet at 100 %.
Usage: ~/.venvs/motion/bin/python -I crops.py (after master_diff.py). Writes overlays/*.png / *.jpg.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LR, MB, OUT, load  # noqa: E402

OV = os.path.join(OUT, "overlays")
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
except OSError:
    FONT = ImageFont.load_default()


def sheet(tiles, title, sub, path):
    pad, top = 10, 50
    w = sum(t.shape[1] for t in tiles) + pad * (len(tiles) + 1)
    h = max(t.shape[0] for t in tiles) + top + pad
    s = Image.new("RGB", (max(w, 600), h), (245, 244, 240))
    x = pad
    for t in tiles:
        s.paste(Image.fromarray(t), (x, top))
        x += t.shape[1] + pad
    d = ImageDraw.Draw(s)
    d.text((pad, 6), title, fill=(30, 30, 30), font=FONT)
    d.text((pad, 26), sub, fill=(90, 90, 90), font=FONT)
    if path.endswith(".jpg"):
        s.save(path, quality=93)
    else:
        s.save(path)


def crop(a, box):
    x0, y0, x1, y1 = box
    return a[y0:y1, x0:x1]


def up(t, k):
    return np.asarray(Image.fromarray(t).resize((t.shape[1] * k, t.shape[0] * k), Image.NEAREST))


def stretch(a, b):
    both = np.concatenate([a.reshape(-1, 3), b.reshape(-1, 3)]).astype(float)
    lo, hi = np.percentile(both, 1), np.percentile(both, 60)
    f = lambda t: np.clip((t.astype(float) - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    return f(a), f(b), lo, hi


def outline(t, m, col=(0, 230, 255)):
    t = t.copy()
    e = m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    t[e] = col
    return t


def trio(before, after, box, name, title, k=4, mask=None):
    a, b = crop(before, box), crop(after, box)
    x0, y0, x1, y1 = box
    sheet([a, b] + ([outline(b, crop(mask, box))] if mask is not None else []), title,
          f"x {x0}-{x1}, y {y0}-{y1} · 100 % · before | after" + (" | after with (b)'s mask (cyan)" if mask is not None else ""),
          os.path.join(OV, f"{name}-100.png"))
    if k:
        sheet([up(a, k), up(b, k)], title, f"x {x0}-{x1}, y {y0}-{y1} · x{k} NEAREST · before | after", os.path.join(OV, f"{name}-x{k}.png"))
        sa, sb, lo, hi = stretch(a, b)
        tiles = [up(sa, k), up(sb, k)]
        if mask is not None:
            tiles = [up(sa, k), up(sb, k), up(outline(sb, crop(mask, box)), k)]
        sheet(tiles, title + " · stretch", f"x {x0}-{x1}, y {y0}-{y1} · x{k} NEAREST · stretch: 8-bit {lo:.0f}-{hi:.0f} -> 0-255 on both · before | after" + (" | after with the mask" if mask is not None else ""),
              os.path.join(OV, f"{name}-x{k}-stretch.png"))


f5 = load(os.path.join(MB, "warm-modern-MB-A-fix5.png"))
f6 = load(os.path.join(MB, "warm-modern-MB-A-fix6.png"))
reg = np.asarray(Image.open(os.path.join(MB, "raw/fix6-b-region.png"))) > 0
# (b)
trio(f5, f6, (2150, 780, 2560, 950), "mb-b-region", "master fix5 | fix6: polish (b), the cushion's cast shadow on the right pillowcase", k=0, mask=reg)
trio(f5, f6, (2190, 805, 2290, 930), "mb-b-left-end", "master: (b)'s left end at the cushion (contact line)", k=4, mask=reg)
trio(f5, f6, (2380, 850, 2520, 935), "mb-b-right-end", "master: (b)'s right end and base on the duvet", k=4, mask=reg)
trio(f5, f6, (2240, 795, 2400, 860), "mb-b-top", "master: (b)'s top edge in the half-shadow (L* >= 20 changes)", k=4, mask=reg)
bres = np.load(os.path.join(OUT, "data/b-only-dL.npy"))
bx = (2150, 780, 2560, 950)
hm = cv2.applyColorMap(np.clip(crop(bres, bx) / 4.0 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)[..., ::-1]
mix = (crop(f6, bx) * 0.3 + hm * 0.7).astype(np.uint8)
sheet([outline(mix, crop(reg, bx)), crop(f6, bx)], "master: (b) alone (QA's empirical toe taken off), 0-4 L* as inferno; mask in cyan",
      "x 2150-2560, y 780-950 · 100 %", os.path.join(OV, "mb-b-only-lift-map.png"))
# products in deep shadow
trio(f5, f6, (1820, 1230, 2300, 1470), "mb-muslin-folds", "master: the pecan muslin throw, deep folds at the foot of the bed", k=0)
trio(f5, f6, (1960, 1300, 2160, 1420), "mb-muslin-folds-zoom", "master: muslin folds", k=4)
trio(f5, f6, (990, 960, 1320, 1290), "mb-nightstand", "master: walnut nightstand and the void under it", k=0)
trio(f5, f6, (1000, 1200, 1300, 1290), "mb-under-nightstand", "master: the void under the nightstand (render-agent's purple / red specks, first version)", k=4)
trio(f5, f6, (1020, 1010, 1180, 1110), "mb-walnut-drawer", "master: walnut drawer front in shadow", k=4)
# the dark sheet at 100 %: the darkest 1 % of fix5 (quarter size) as boxes
e8 = load(os.path.join(LR, "warm-modern-A-ed8.png"))
e9 = load(os.path.join(LR, "warm-modern-A-ed9.png"))
trio(e8, e9, (1340, 960, 1680, 1150), "lr-black-bowl", "living room ed8 | ed9: the matte black bowl (bowl-cj-matte-black-bowl-20)", k=0)
trio(e8, e9, (1400, 1000, 1600, 1120), "lr-black-bowl-zoom", "living room: the black bowl's shadow side", k=4)
trio(e8, e9, (1080, 1230, 2200, 1460), "lr-under-table", "living room: under the walnut table, the drum bases", k=0)
trio(e8, e9, (1860, 1260, 2010, 1360), "lr-walnut-drum", "living room: the right walnut drum base in deep shadow", k=4)
trio(e8, e9, (100, 0, 200, 200), "lr-window-frame", "living room: the bronze window frame (darkest px, greenish before and after)", k=4)
for nm, a, b in (("mb", f5, f6), ("lr", e8, e9)):
    h, w = a.shape[:2]
    sheet([np.asarray(Image.fromarray(a).resize((w // 2, h // 2), Image.LANCZOS)), np.asarray(Image.fromarray(b).resize((w // 2, h // 2), Image.LANCZOS))],
          f"{nm}: the whole frame, before | after (half size)", "the toe lifts only L* < 20; DL1 (plaster, median) does not move", os.path.join(OV, f"{nm}-whole-half.jpg"))
print("ok")


# own stretch per side (each side by its own percentiles 1-60): the structure (grain, folds, specks) at equal contrast
def own(before, after, box, name, title, k=4):
    a, b = crop(before, box), crop(after, box)
    f = lambda t: np.clip((t.astype(float) - np.percentile(t, 1)) / max(np.percentile(t, 60) - np.percentile(t, 1), 1) * 255, 0, 255).astype(np.uint8)
    x0, y0, x1, y1 = box
    sheet([up(f(a), k), up(f(b), k)], title + " · own stretch", f"x {x0}-{x1}, y {y0}-{y1} · x{k} NEAREST · each side by its own p1-p60 · before | after",
          os.path.join(OV, f"{name}-x{k}-own-stretch.png"))


own(e8, e9, (1860, 1260, 2010, 1360), "lr-walnut-drum", "living room: the right walnut drum base")
own(e8, e9, (1400, 1000, 1600, 1120), "lr-black-bowl-zoom", "living room: the black bowl's shadow side")
own(f5, f6, (1000, 1200, 1300, 1290), "mb-under-nightstand", "master: the void under the nightstand")
own(f5, f6, (1960, 1300, 2160, 1420), "mb-muslin-folds-zoom", "master: muslin folds")
print("own ok")
