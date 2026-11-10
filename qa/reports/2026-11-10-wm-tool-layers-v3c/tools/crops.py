#!/usr/bin/env python3
"""
crops.py: qa-agent, 2026-11-10. Visual evidence for the residuals of the v3c tool layers.

For each set, around the worst shadow-band residual (the largest cluster of pixels >= 3 levels, browser path P4):
  set-X-worst-100.png    approved | recomposite (browser, premultiplied) | |diff| x 40 ; 240 x 240 px crop at 100 %
  set-X-worst-x4.png     the same, 64 x 64 px at x4 (nearest); a second row with both pictures stretched 0-48 -> 0-255
                         (a stress view that no screen shows: shadows lifted about 5x) and the diff map
  set-X-blink-x4.png     animated PNG: approved / recomposite / approved ..., 64 x 64 at x4, 700 ms each (blink comparator)
  set-X-maxpx-x4.png     as worst-x4, centred on the single worst pixel when it is away from the cluster
  set-X-residual-map.png the set's bounding box at 50 %: the picture dimmed, residual pixels marked
                         (1 level grey-blue, 2 yellow, >= 3 red), the region outline in thin green
  sets-recomposite-sheet.jpg  the three recomposites (browser path) side by side on the sofa, 100 % crop, for the eye
Usage: python3 crops.py <out_dir>
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_recomposite as q  # noqa: E402

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
B = np.asarray(Image.open(os.path.join(q.LAYERS, "base.png")))


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 16], fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 255, 255))
    return im


def panel(arr, scale, text):
    im = Image.fromarray(arr)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    canvas = Image.new("RGB", (im.width, im.height + 18), (0, 0, 0))
    canvas.paste(im, (0, 18))
    return label(canvas, text)


def hstack(ims, gap=6):
    w = sum(i.width for i in ims) + gap * (len(ims) - 1)
    h = max(i.height for i in ims)
    out = Image.new("RGB", (w, h), (40, 40, 40))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def vstack(ims, gap=6):
    w = max(i.width for i in ims)
    h = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (w, h), (40, 40, 40))
    y = 0
    for i in ims:
        out.paste(i, (0, y))
        y += i.height + gap
    return out


def crop(a, cx, cy, half):
    H, W = a.shape[:2]
    x0, y0 = max(0, cx - half), max(0, cy - half)
    x1, y1 = min(W, x0 + 2 * half), min(H, y0 + 2 * half)
    return a[y0:y1, x0:x1], (x0, y0, x1, y1)


def diffmap(d, gain=40):
    return np.clip(d * gain, 0, 255).astype(np.uint8)


def stretch(a, top=48):
    return np.clip(a.astype(np.float32) * 255.0 / top, 0, 255).astype(np.uint8)


sheet = []
log = {}
for s in q.SETS:
    LA = np.asarray(Image.open(os.path.join(q.LAYERS, f"cushions-set-{s}.png")))
    S = np.asarray(Image.open(os.path.join(q.LAYERS, f"cushions-set-{s}-shadow.png")))
    T = np.asarray(Image.open(os.path.join(q.PILOT, f"composite-set-{s}-v3-graded-v3c.png")))
    A = LA[..., 3]
    o = q.p4(B, S, LA[..., :3], A)
    d3 = np.abs(o.astype(np.int16) - T.astype(np.int16))
    d = d3.max(2)
    region = (A > 0) | (S < 255).any(2)
    n, lab, st, cen = cv2.connectedComponentsWithStats((d >= 3).astype(np.uint8), connectivity=8)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    cx, cy = int(round(cen[k][0])), int(round(cen[k][1]))
    log[s] = dict(worst_cluster_centre_xy=[cx, cy], worst_cluster_px=int(st[k, cv2.CC_STAT_AREA]),
                  max_in_crop=int(d[max(0, cy - 32):cy + 32, max(0, cx - 32):cx + 32].max()))
    # 100 %
    a1, box = crop(T, cx, cy, 120)
    b1, _ = crop(o, cx, cy, 120)
    dd, _ = crop(d3, cx, cy, 120)
    hstack([panel(a1, 1, f"set {s} approved v3c @100% x{box[0]} y{box[1]}"), panel(b1, 1, "recomposite (browser premult.)"),
            panel(diffmap(dd), 1, "|diff| x40")]).save(os.path.join(OUT, f"set-{s}-worst-100.png"))
    # x4
    a4, box4 = crop(T, cx, cy, 32)
    b4, _ = crop(o, cx, cy, 32)
    d4, _ = crop(d3, cx, cy, 32)
    row1 = hstack([panel(a4, 4, f"approved x4 ({box4[0]},{box4[1]})"), panel(b4, 4, "recomposite x4"), panel(diffmap(d4), 4, "|diff| x40")])
    row2 = hstack([panel(stretch(a4), 4, "approved, stretched 0-48"), panel(stretch(b4), 4, "recomposite, stretched 0-48"),
                   panel(diffmap(d4, 85), 4, "|diff| x85")])
    vstack([row1, row2]).save(os.path.join(OUT, f"set-{s}-worst-x4.png"))
    # blink
    fa = Image.fromarray(a4).resize((a4.shape[1] * 4, a4.shape[0] * 4), Image.NEAREST)
    fb = Image.fromarray(b4).resize((b4.shape[1] * 4, b4.shape[0] * 4), Image.NEAREST)
    fa.save(os.path.join(OUT, f"set-{s}-blink-x4.png"), save_all=True, append_images=[fb], duration=700, loop=0)
    # the single worst pixel, if it lies outside the cluster crop
    my, mx = np.unravel_index(int(np.argmax(d)), d.shape)
    log[s]["max_xy"] = [int(mx), int(my)]
    log[s]["max_level"] = int(d.max())
    if abs(int(mx) - cx) > 24 or abs(int(my) - cy) > 24:
        a4m, bm = crop(T, int(mx), int(my), 32)
        b4m, _ = crop(o, int(mx), int(my), 32)
        d4m, _ = crop(d3, int(mx), int(my), 32)
        r1 = hstack([panel(a4m, 4, f"approved x4 ({bm[0]},{bm[1]}) max px"), panel(b4m, 4, "recomposite x4"), panel(diffmap(d4m), 4, "|diff| x40")])
        r2 = hstack([panel(stretch(a4m), 4, "approved, stretched 0-48"), panel(stretch(b4m), 4, "recomposite, stretched 0-48"),
                     panel(diffmap(d4m, 85), 4, "|diff| x85")])
        vstack([r1, r2]).save(os.path.join(OUT, f"set-{s}-maxpx-x4.png"))
        log[s]["maxpx_crop"] = f"set-{s}-maxpx-x4.png"
    # residual map over the set's bbox
    ys, xs = np.nonzero(region)
    x0, x1, y0, y1 = xs.min() - 8, xs.max() + 9, ys.min() - 8, ys.max() + 9
    base = (T[y0:y1, x0:x1].astype(np.float32) * 0.45).astype(np.uint8)
    dm = d[y0:y1, x0:x1]
    # dilate the marks so single pixels stay visible at 50 %
    for lvl, col in ((1, (90, 140, 255)), (2, (255, 220, 0)), (3, (255, 30, 30))):
        m = (dm >= lvl) if lvl == 3 else (dm == lvl)
        m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        base[m] = col
    edge = cv2.morphologyEx(region[y0:y1, x0:x1].astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    base[edge & (dm == 0)] = (40, 160, 60)
    im = Image.fromarray(base)
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    label(im, f"set {s}: residual vs approved (browser path). blue 1 level, yellow 2, red >=3 (marks dilated 3x3). green = region edge").save(
        os.path.join(OUT, f"set-{s}-residual-map.png"))
    # sheet tile: 100 % of the sofa centre
    sheet.append(panel(o[880:1440, 1340:2460], 1, f"set {s} recomposite (browser path), 100%"))
vstack(sheet).convert("RGB").save(os.path.join(OUT, "sets-recomposite-sheet.jpg"), quality=92)
import json  # noqa: E402
json.dump(log, open(os.path.join(OUT, "crops.json"), "w"), indent=1)
print(log)
