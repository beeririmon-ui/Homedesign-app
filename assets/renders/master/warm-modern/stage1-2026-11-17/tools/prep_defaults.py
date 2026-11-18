#!/usr/bin/env python3
"""
prep_defaults.py: the model input of MB0 with the defaults (render-agent, 2026-11-18; 0 tokens).
The accepted plate (plate.png) everywhere, and inside the product and filler masks of the defaults clay (MB0-id.png, ids 40-55,
feathered 1 px) the clay MB0.png itself, recoloured toward each product's SKU photo: a* b* from the photo's median (inputs/defaults-refs),
L* to a room value with the clay's own shading (x0.8 around its median). The lamps (sconces 43 / 44, floor lamp 55) keep the clay's
materials (walnut plate, black arm, travertine cone; brass, walnut stem, cream shade) and their glow.

  python3 prep_defaults.py plate.png <clay MB0.png> <clay MB0-id.png> inputs/defaults-input.png inputs/defaults-input-prep.json
"""
import json
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from prep_plate import lab, rgb_from_lab  # noqa: E402

TARGET = {  # id: (name, L*, a*, b*)  a*/b* from the SKU photos (inputs/defaults-refs), L* a room value
    52: ("bedding Natural Linen", 74.0, 2.5, 9.0), 51: ("pillowcases Caramel Pairs", 46.0, 24.2, 33.2), 53: ("cushion Milk Tea", 82.0, 2.5, 8.0),
    54: ("throw Pecan", 40.0, 12.1, 16.5), 40: ("curtain linen-blend", 86.0, -0.4, 6.5), 41: ("sill vase cream fluted", 88.0, -1.7, 8.5),
    46: ("bottle Color D", 68.0, 4.5, 19.4), 48: ("dish travertine", 76.0, 2.0, 5.7), 45: ("tray walnut", 28.0, 17.5, 12.1),
    49: ("candle holders travertine", 76.0, 2.0, 10.1), 50: ("candles cream (filler)", 88.0, 1.0, 8.0), 47: ("oat stems (filler)", 70.0, 4.0, 24.0),
    42: ("sage stem (filler)", 55.0, -8.0, 12.0)}
KEEP = {43, 44, 55}


def main(plate, clay, clay_id, out, rec):
    P = np.asarray(Image.open(plate).convert("RGB")).astype(np.float64) / 255
    C = np.asarray(Image.open(clay).convert("RGB")).astype(np.float64) / 255
    ids = np.asarray(Image.open(clay_id))
    L = lab(C)
    rep = {}
    for g, (name, lt, at, bt) in TARGET.items():
        m = ids == g
        if not m.any():
            continue
        med = float(np.median(L[m, 0]))
        L[m, 0] = np.clip(lt + (L[m, 0] - med) * 0.8, 0, 100)
        L[m, 1], L[m, 2] = at, bt
        rep[name] = dict(id=g, px=int(m.sum()), clay_median_L=round(med, 1), target=[lt, at, bt])
    Cr = rgb_from_lab(L)
    m = np.isin(ids, list(TARGET) + list(KEEP)).astype(np.float32)
    w = cv2.GaussianBlur(m, (0, 0), 0.7)
    w = np.where(m > 0, np.maximum(w, 0.5), w)[..., None]
    w = np.clip(w * 1.0, 0, 1)
    outp = P * (1 - w) + Cr * w
    Image.fromarray(np.clip(np.rint(outp * 255), 0, 255).astype(np.uint8)).save(out)
    rep["kept_clay_materials"] = sorted(KEEP)
    rep["mask_px"] = int(m.sum())
    json.dump(rep, open(rec, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:6])
