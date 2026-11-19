#!/usr/bin/env python3
"""
prep_b1_defaults.py: the model input of the B1 defaults, render-agent, 2026-11-19. 0 tokens. As B2's prep_defaults.py:
  the base:        the B1 plate UNGRADED (raw/plate-relit.png: the model's plate with the clay-relative light and the plaster colour of
                   compose_b1_plate.py, before the WM-G1 curve): the model works in the plate's own exposure; the curve is applied
                   once, on the layers and the composite
  the light hint:  outside the products, the base times the clay's LOCAL light ratio B1 / B1-plate (the clay EXRs, blurred 3 px,
                   divided by its own sigma-150 blur so the room level does not move, clamped 0.55-3): the B1 sconce's V beams, the
                   products' shadows
  the products:    inside the clay's product masks (ids 40-61, fillers included), the lit clay B1 itself, at the exact size and place;
                   the jar on the sill, the candle and the diffuser follow the plate's own window and slab (the model drew the
                   window 8 px left of the clay and the slab's top edge 3 px higher: those three placeholders move with them)
Writes inputs/defaults-input.png and inputs/defaults-products-mask.png.

  python3 prep_b1_defaults.py
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools")
import prep_defaults as P  # noqa: E402

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-b1-2026-11-19/"
PRODUCTS = list(range(40, 62))
SHIFT = {59: (-8, -3), 57: (0, -3), 58: (0, -3)}          # id: (dx, dy) px


def main():
    base = np.asarray(Image.open(os.path.join(ST, "raw/plate-relit.png")).convert("RGB")).astype(np.float64) / 255
    b1, pl = P.load_exr(P.EXR + "B1.exr"), P.load_exr(P.EXR + "B1-plate.exr")
    ratio = cv2.GaussianBlur(((b1 + 1e-4) / (pl + 1e-4)).astype(np.float32), (0, 0), 3).astype(np.float64)
    wide = cv2.GaussianBlur(ratio.mean(2).astype(np.float32), (0, 0), 150).astype(np.float64)
    ratio = np.clip(ratio / np.maximum(wide, 1e-3)[..., None], 0.55, 3.0)
    ids = np.asarray(Image.open(CLAY + "B1-id.png"))
    clay = np.asarray(Image.open(CLAY + "B1.png").convert("RGB")).astype(np.float64) / 255
    H, W = ids.shape
    prod = np.zeros((H, W), bool)
    out = P.srgb(P.lin(base) * ratio)
    for g in PRODUCTS:
        m = ids == g
        if not m.any():
            continue
        dx, dy = SHIFT.get(g, (0, 0))
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        m2 = cv2.warpAffine(m.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST) > 0
        c2 = cv2.warpAffine(clay.astype(np.float32), M, (W, H), flags=cv2.INTER_NEAREST).astype(np.float64)
        out[m2] = c2[m2]
        prod |= m2
    Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)).save(os.path.join(ST, "inputs/defaults-input.png"))
    Image.fromarray((prod * 255).astype(np.uint8)).save(os.path.join(ST, "inputs/defaults-products-mask.png"))
    print("products px", int(prod.sum()), "ratio p1/p50/p99", np.round(np.percentile(ratio.mean(2), [1, 50, 99]), 3))


if __name__ == "__main__":
    main()
