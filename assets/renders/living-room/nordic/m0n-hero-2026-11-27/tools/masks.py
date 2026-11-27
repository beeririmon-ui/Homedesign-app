#!/usr/bin/env python3
"""masks.py: the product masks of H-N (render-agent, 2026-11-27). 0 tokens.
  python3 masks.py <hero_final.png> <seg_dir> <out.npz>
The free grok segment map of the final hero (segment-map b34afc43, 35 segments) returns each segment as a bbox crop (RGBA, the hero's
pixels + the mask). Each crop is placed by template matching (1/4 scale coarse, full-scale refine, SQDIFF_NORMED); the segments are
grouped into slots (fillers go with their product: the olive with the planter, the stems with the vase, the candles with the holders).
Not segmented by grok: the magazine holder and the pouf: cut by colour and shape inside their clay boxes (felt L* < 38 + the paper and
the handles of the E2 edit region; the pouf = the clay pouf silhouette warped like the hero input (the model kept it in place)). The tray is split from the 'candle
holders' segments as the wide flat one."""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

CLAY_IDS = os.path.join(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clay"), "ids16.png")
GROUPS = {"curtains": [1], "vase": [2, 4, 6], "planter": [3, 5, 8], "wall-decor": [9], "accent-sconces": [10, 11], "framed-art": [12, 13, 14],
          "pendant": [15], "cushions": [17, 18, 19, 20], "sofa-cover": [21], "floor-lamp": [22], "basket": [7, 23, 24], "coffee-table": [25],
          "table-runner": [26], "candle-holders": [27, 28, 29, 30], "tray": [31], "bowl": [32], "rug": [33], "_papers": [34]}


def place(H, crop):
    rgb, a = crop[..., :3], crop[..., 3] > 127
    s = 4
    Hs = cv2.resize(H, (H.shape[1] // s, H.shape[0] // s), interpolation=cv2.INTER_AREA)
    ts = cv2.resize(rgb, (max(rgb.shape[1] // s, 4), max(rgb.shape[0] // s, 4)), interpolation=cv2.INTER_AREA)
    r = cv2.matchTemplate(Hs, ts, cv2.TM_SQDIFF_NORMED)
    _, _, mn, _ = cv2.minMaxLoc(r)
    x0, y0 = mn[0] * s, mn[1] * s
    best = None
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            x, y = x0 + dx, y0 + dy
            if x < 0 or y < 0 or x + rgb.shape[1] > H.shape[1] or y + rgb.shape[0] > H.shape[0]:
                continue
            d = float(np.mean((H[y:y + rgb.shape[0], x:x + rgb.shape[1]].astype(np.float32) - rgb.astype(np.float32)) ** 2))
            if best is None or d < best[0]:
                best = (d, x, y)
    return best[1], best[2], a, best[0]


def main(hero_p, seg_dir, out_p):
    H = np.asarray(Image.open(hero_p).convert("RGB"))
    h, w = H.shape[:2]
    full = {}
    rec = {}
    for i in range(35):
        crop = np.asarray(Image.open(os.path.join(seg_dir, f"{i}.png")).convert("RGBA"))
        x, y, a, err = place(H, crop)
        m = np.zeros((h, w), bool)
        m[y:y + a.shape[0], x:x + a.shape[1]] = a
        full[i] = m
        rec[i] = dict(xy=[x, y], size=[a.shape[1], a.shape[0]], mse=round(err, 2))
    M = {k: np.any([full[i] for i in v], 0) for k, v in GROUPS.items()}
    lab = cv2.cvtColor(H.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)
    L = lab[..., 0]
    # magazine holder: the charcoal felt (L* < 38, low chroma) + the papers (segment 34 and the E2 paste) + the wooden handles,
    # inside its box; the largest component, holes filled
    bx = np.zeros((h, w), bool)
    bx[1150:1530, 700:1030] = True                     # x from 700: the armchair's front leg stays out
    C = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    felt = bx & (L < 38) & (C < 12)
    e2 = np.asarray(Image.open(os.path.join(os.path.dirname(hero_p), "hn-e2-mask.png"))) if os.path.exists(os.path.join(os.path.dirname(hero_p), "hn-e2-mask.png")) else None
    paper = M.pop("_papers")
    if e2 is not None:
        r = np.load(os.path.join(os.path.dirname(hero_p), "hn-e2-region.npy"))
        pm = np.zeros((h, w), bool)
        pm[r[1]:r[3], r[0]:r[2]] = e2 > 127
        paper |= pm & bx & (L > 60)
    wood = bx & (lab[..., 2] > 18) & (L > 35) & (L < 75)
    hold = felt | paper
    hold = cv2.morphologyEx(hold.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(hold)
    k = 1 + int(np.argmax(st[1:, 4])) if n > 1 else 0
    hold = lb == k
    hb = cv2.dilate(hold.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    hold |= wood & hb & (np.arange(h)[:, None] < 1330)
    cs, _ = cv2.findContours(hold.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    fill = np.zeros((h, w), np.uint8)
    cv2.drawContours(fill, [c for c in cs if cv2.contourArea(c) > 400], -1, 1, -1)
    M["magazine-holder"] = fill.astype(bool) & ~M["rug"] | (fill.astype(bool) & felt)
    # pouf: the cream knit dome cut by the bottom-right corner: an ellipse fitted to the bright knit pixels in its box, minus the rug seg
    # the pouf: the clay's pouf silhouette (id 819), warped like the hero input (hn-input.json registration): the model kept it in place
    ids = np.asarray(Image.open(CLAY_IDS)).astype(np.float32)
    ids = cv2.resize(ids, (w, h), interpolation=cv2.INTER_NEAREST)
    A = np.float32(json.load(open(os.path.join(os.path.dirname(hero_p), "hn-input.json")))["registration"]["matrix"])
    ids = cv2.warpAffine(ids, A, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    pf2 = cv2.dilate((np.rint(ids) == 819).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))).astype(bool)   # +6 px: the hull runs a little wide of the clay
    M["pouf"] = pf2.astype(bool)
    # exclusivity in z order (a higher product wins its pixels)
    Z = ["curtains", "framed-art", "wall-decor", "accent-sconces", "vase", "rug", "floor-lamp", "planter", "sofa-cover", "cushions", "coffee-table",
         "basket", "magazine-holder", "table-runner", "tray", "bowl", "candle-holders", "pouf", "pendant"]
    taken = np.zeros((h, w), bool)
    for k in reversed(Z):
        M[k] = M[k] & ~taken
        taken |= M[k]
    np.savez_compressed(out_p, **{k: M[k] for k in Z})
    json.dump(dict(segments=rec, px={k: int(M[k].sum()) for k in Z}), open(out_p[:-4] + ".json", "w"), indent=1)
    vis = H.astype(np.float32) * 0.35
    rng = np.random.default_rng(4)
    for k in Z:
        vis[M[k]] = vis[M[k]] * 0.3 + rng.uniform(80, 255, 3) * 0.7
    Image.fromarray(vis.astype(np.uint8)).resize((1360, 765)).save(out_p[:-4] + "-vis.jpg", quality=85)
    print({k: int(M[k].sum()) for k in Z})


if __name__ == "__main__":
    main(*sys.argv[1:4])
