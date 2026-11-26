#!/usr/bin/env python3
"""masks.py: the hard mask of every default product in the hero (scratch -> out/prep/masks.npz).
Sources: the free segment map of the hero as returned (grok-imagine-image-2 segment-map, 0 tokens; pixel-exact crops located in the
hero), the segment map of the table edit (the new Olia, the bowl, the candle holders; mapped by the edit's registration), the rug's
right end after its edit (the ivory rug against the dark oak), the three frames from the canvases found by prints.py, and the
magazine holder by colour against the rug (the segment map does not name it)."""
import json
import os

import cv2
import numpy as np
from PIL import Image

import hwlib as L
import guide_hw_geom as GG

SP = L.SP
OUTP = os.path.join(L.OUT, "prep")
H_, W_ = L.H, L.W
dil = lambda m, r: cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
ero = lambda m, r: cv2.erode(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def main():
    seg = {k: v > 127 for k, v in np.load(os.path.join(SP, "seg", "groups.npz")).items()}
    e1 = {k: v > 127 for k, v in np.load(os.path.join(SP, "seg", "e1-groups.npz")).items()}
    pm = np.load(os.path.join(OUTP, "paste-masks.npz"))
    a1, a3 = pm["a1"] > 127, pm["a3"] > 127
    cv = np.load(os.path.join(OUTP, "canvas.npz"))
    Hg = L.rd(os.path.join(OUTP, "hero.png"))
    Hb = L.rd(os.path.join(OUTP, "hero-blank-canvases.png"))
    lab = L.to_lab(Hg)
    Ls = cv2.GaussianBlur(lab[..., 0], (0, 0), 1.2)
    M = {}
    for k in ("vase", "planter", "basket", "floor-lamp", "pendant", "accent-sconces"):
        M[k] = seg[k]
    M["coffee-table"], M["bowl"], M["candle-holders"] = e1["coffee-table"], e1["bowl"], e1["candle-holders"]
    M["coffee-table"] = M["coffee-table"] & ~M["bowl"] & ~M["candle-holders"]
    throw = np.where(a1, e1["throw-e1"], seg["throw"])
    cush = seg["cushion-left"] | seg["cushion-right"] | seg["cushion-lumbar"] | throw
    M["cushions"] = cush & ~M["coffee-table"] & ~M["bowl"] & ~M["candle-holders"]
    # the rug: as segmented; inside the table paste as the edit's map says; at its right end by lightness against the oak floor
    rug = np.where(a1, e1["rug-e1"], seg["rug"])
    zone3 = dil(a3, 6)
    light = (Ls > 50) & (lab[..., 2] < 22) & zone3 & ~seg["sofa"] & ~throw & ~seg["floor-lamp"]
    rug = np.where(zone3, light, rug)
    rug = cv2.morphologyEx(rug.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(rug.astype(np.uint8), connectivity=8)
    big = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 1500]
    rug = np.isin(lb, big)
    # the magazine holder: on the rug, between the armchair and the table: what is not rug-coloured there (black tube, cognac leather,
    # newsprint darker or more coloured than the wool), closed and filled
    m = L.maps()
    box = dil(np.load(os.path.join(OUTP, "maps.npz"))["idx"] == L.PI["magazine-holder"], 45)
    box &= ~seg["armchair"] & ~M["coffee-table"]
    hull = np.zeros((H_, W_), np.uint8)
    cnts, _ = cv2.findContours(rug.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.fillConvexPoly(hull, cv2.convexHull(np.vstack(cnts)), 1)
    box &= dil(hull.astype(bool), 4)
    # its own materials: the black tube (L* under 24) and the cognac leather (a* over 10, b* over 15), closed into one body
    cand = box & ((Ls < 24) | ((lab[..., 1] > 10) & (lab[..., 2] > 15) & (Ls < 62)))
    cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    notrug = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (23, 23)))
    n, lb, st, _ = cv2.connectedComponentsWithStats(notrug, connectivity=8)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    hold = lb == k
    # fill the holes the frame closes (the rug seen through a closed loop of tube stays part of the holder's layer)
    ff = hold.astype(np.uint8).copy()
    pad = np.pad(ff, 1)
    cv2.floodFill(pad, None, (0, 0), 2)
    hold = pad[1:-1, 1:-1] != 2
    M["magazine-holder"] = hold & box
    np.save(os.path.join(OUTP, "rug-hull.npy"), hull)
    rug = rug & ~M["magazine-holder"]
    M["rug"] = rug
    # the frames: each found canvas, grown by its moulding (the dark ring round the canvas in the hero with blank canvases)
    art = np.zeros((H_, W_), bool)
    Lb = cv2.GaussianBlur(L.to_lab(Hb)[..., 0], (0, 0), 0.8)
    rings = []
    for q in cv["quads"]:
        inner = GG.quad_mask(q, (H_, W_)) > 0.5
        ring = dil(inner, 16) & ~inner
        wall_L = float(np.median(Lb[dil(inner, 40) & ~dil(inner, 22)]))
        can_L = float(np.median(Lb[ero(inner, 12)]))
        dark = ring & (Lb < min(wall_L, can_L) - 10)
        dark = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        dt = cv2.distanceTransform((~inner).astype(np.uint8), cv2.DIST_L2, 5)
        th = float(np.percentile(dt[dark], 90)) if dark.sum() > 200 else 8.0
        rings.append(round(th, 1))
        art |= dil(inner, int(round(th)) + 1)
    M["framed-art"] = art
    json.dump(dict(moulding_px=rings, px={k: int(v.sum()) for k, v in M.items()}), open(os.path.join(OUTP, "masks.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(OUTP, "masks.npz"), sofa=seg["sofa"].astype(np.uint8) * 255, armchair=seg["armchair"].astype(np.uint8) * 255,
                        throw=throw.astype(np.uint8) * 255, **{k: v.astype(np.uint8) * 255 for k, v in M.items()})
    ov = Hg * 0.45
    rs = np.random.RandomState(7)
    for k, v in M.items():
        col = rs.uniform(0.3, 1.0, 3).astype(np.float32)
        e = v & ~ero(v, 1)
        ov[v] = ov[v] * 0.55 + col * 0.45
        ov[e] = col
    Image.fromarray((ov * 255).astype(np.uint8)).resize((1360, 765), Image.LANCZOS).save(os.path.join(OUTP, "masks-overview.jpg"), quality=88)
    Image.fromarray((ov[1250:1530, 560:1160] * 255).astype(np.uint8)).save(os.path.join(OUTP, "masks-holder.jpg"), quality=90)
    print(json.dumps(dict(moulding_px=rings, px={k: int(v.sum()) for k, v in M.items()})))


if __name__ == "__main__":
    main()
