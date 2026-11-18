#!/usr/bin/env python3
"""
prep_defaults.py: the model input of output 2, B2 with the defaults of section 0א (render-agent, 2026-11-18). 0 tokens.
  the base:        the plate as it went to QA, with BP-L1 (raw/plate-ungraded.png through grade_plate.bp_l1), UNGRADED: the model works
                   in the plate's own exposure; the WM-G1 curve is applied once, on the final composite (grade_plate.py apply)
  the light hint:  outside the products, the base times the clay's LOCAL light ratio B2 / B2-plate (scene-linear, from the clay
                   EXRs, blurred 3 px, divided by its own wide blur so the room level does not move, clamped 0.55-3): the two V beams
                   of each sconce, the pools, the products' shadows
  the products:    inside the clay's product masks (ids 40-52, fillers included), the lit clay B2 itself as a placeholder at the
                   exact size and place (the planter, the towel and the curtain as clay shapes, the sconce blocks as travertine)
Writes inputs/defaults-input.png, raw/plate-ungraded-bpl1.png (the base for the composite) and inputs/defaults-products-mask.png.

  python3 prep_defaults.py
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import grade_plate as G  # noqa: E402

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-2026-11-17/"
EXR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath/exr/"
PRODUCTS = list(range(40, 53))


def load_exr(path):
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Linear Rec.709"
    W, H = img.size
    px = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(H, W, 4)[::-1, :, :3].astype(np.float64)


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def main():
    import cv2
    raw = np.asarray(Image.open(os.path.join(ST, "raw/plate-ungraded.png")).convert("RGB")).astype(np.float64) / 255
    base, n = G.bp_l1(raw)
    Image.fromarray(np.clip(np.rint(base * 255), 0, 255).astype(np.uint8)).save(os.path.join(ST, "raw/plate-ungraded-bpl1.png"))
    b2, pl = load_exr(EXR + "B2.exr"), load_exr(EXR + "B2-plate.exr")
    ratio = (b2 + 1e-4) / (pl + 1e-4)
    ratio = cv2.GaussianBlur(ratio.astype(np.float32), (0, 0), 3).astype(np.float64)
    # only the local light: the clay's lamps also lift the whole room by about 0.6 stop, which would push the plaster past L* 91;
    # the ratio is divided by its own wide blur (sigma 150 px), so the beams, pools and shadows stay and the room level does not move
    lum = ratio.mean(2)
    wide = cv2.GaussianBlur(lum.astype(np.float32), (0, 0), 150).astype(np.float64)
    ratio = ratio / np.maximum(wide, 1e-3)[..., None]
    ratio = np.clip(ratio, 0.55, 3.0)
    ids = np.asarray(Image.open(CLAY + "B2-id.png"))
    prod = np.isin(ids, PRODUCTS)
    clay = np.asarray(Image.open(CLAY + "B2.png").convert("RGB")).astype(np.float64) / 255
    lit = srgb(lin(base) * ratio)
    out = np.where(prod[..., None], clay, lit)
    Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)).save(os.path.join(ST, "inputs/defaults-input.png"))
    Image.fromarray((prod * 255).astype(np.uint8)).save(os.path.join(ST, "inputs/defaults-products-mask.png"))
    print("BP-L1 px", n, "products px", int(prod.sum()), "ratio p1/p50/p99", np.round(np.percentile(ratio.mean(2), [1, 50, 99]), 3))


if __name__ == "__main__":
    main()
