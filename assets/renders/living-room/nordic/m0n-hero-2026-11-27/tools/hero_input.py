#!/usr/bin/env python3
"""hero_input.py: the H-N input = the P-N photograph with the clay's products pasted at their places (render-agent, 2026-11-27).
  python3 hero_input.py <plate_photo.png> <out.png>
Reads scratch clay/ (guide-hero.png, guide-plate.png, ids16.png). Steps:
 1. the plate photo is registered to the clay plate guide (ECC, affine, on edges) and the shift is reported (camera kept?);
 2. product + filler pixels (ids >= 800, the pendant cord included) of the clay hero guide, upscaled to the photo, are tone-matched to
    the photo by the low-pass ratio photo / clay-plate-guide (sigma 40 px) and pasted with a 1 px feather (warped back into the photo's
    frame by the inverse of step 1), so every pasted object sits where the photo's room has it.
Also writes <out>.json with the registration and the product boxes (fractions) for the prompt."""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

SCR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clay")   # the clay v2 outputs, kept in the repo
PROD = {801: "rug", 802: "curtains", 803: "vase", 804: "planter", 805: "basket", 806: "magazine-holder", 807: "floor-lamp", 808: "framed-art",
        809: "accent-sconces", 810: "pendant", 811: "bowl", 812: "candle-holders", 813: "coffee-table", 814: "cushions", 815: "sofa-cover",
        816: "wall-sconce", 817: "wall-decor", 818: "table-runner", 819: "pouf", 820: "tray"}


def edges(g):
    g = cv2.GaussianBlur(g, (0, 0), 1.5)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    e = np.sqrt(gx * gx + gy * gy)
    return e / (np.percentile(e, 99) + 1e-6)


def register(photo, guide):
    """affine that maps guide coords -> photo coords, on downscaled edge maps"""
    s = 0.25
    a = edges(cv2.resize(cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY), None, fx=s, fy=s, interpolation=cv2.INTER_AREA).astype(np.float32) / 255)
    b = edges(cv2.resize(cv2.cvtColor(photo, cv2.COLOR_RGB2GRAY), None, fx=s, fy=s, interpolation=cv2.INTER_AREA).astype(np.float32) / 255)
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        cc, warp = cv2.findTransformECC(a, b, warp, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    except cv2.error:
        cc = None
    warp[:, 2] /= s
    return warp, cc


def main(plate_path, out_path):
    P = np.asarray(Image.open(plate_path).convert("RGB"))
    H, W = P.shape[:2]
    up = lambda a, interp=cv2.INTER_CUBIC: cv2.resize(a, (W, H), interpolation=interp)
    gh = up(np.asarray(Image.open(os.path.join(SCR, "guide-hero.png")).convert("RGB")))
    gp = up(np.asarray(Image.open(os.path.join(SCR, "guide-plate.png")).convert("RGB")))
    ids = up(np.asarray(Image.open(os.path.join(SCR, "ids16.png"))).astype(np.float32), cv2.INTER_NEAREST).astype(np.int32)
    A, cc = register(P, gp)
    shift = dict(ecc=None if cc is None else round(float(cc), 4), matrix=[[round(float(x), 5) for x in r] for r in A],
                 centre_shift_px=[round(float(A[0, 0] * W / 2 + A[0, 1] * H / 2 + A[0, 2] - W / 2), 1), round(float(A[1, 0] * W / 2 + A[1, 1] * H / 2 + A[1, 2] - H / 2), 1)])
    wp = lambda a, interp=cv2.INTER_LINEAR: cv2.warpAffine(a, A, (W, H), flags=interp, borderMode=cv2.BORDER_REPLICATE)
    gh, gp = wp(gh), wp(gp)
    ids = wp(ids.astype(np.float32), cv2.INTER_NEAREST).astype(np.int32)
    m = (ids >= 800)
    yy, xx = np.mgrid[0:H, 0:W]
    m &= ~((ids == 801) & (xx < 0.27 * W) & (yy > 0.70 * H))   # the photo's armchair sits lower-left than the clay's: no rug over it
    m = m.astype(np.float32)
    # tone transfer clay -> photo: low-pass ratio on the room (the plate guide vs the plate photo)
    Pf, gpf, ghf = P.astype(np.float32) + 1, gp.astype(np.float32) + 1, gh.astype(np.float32)
    ratio = cv2.GaussianBlur(Pf, (0, 0), 40) / cv2.GaussianBlur(gpf, (0, 0), 40)
    prod = np.clip(ghf * ratio, 0, 255)
    a = cv2.GaussianBlur(m, (0, 0), 0.8)[..., None]
    out = P.astype(np.float32) * (1 - a) + prod * a
    Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8)).save(out_path)
    boxes = {}
    for k, name in PROD.items():
        ys, xs = np.nonzero(ids == k)
        if len(xs):
            boxes[name] = [round(xs.min() / W, 3), round((xs.max() + 1) / W, 3), round(ys.min() / H, 3), round((ys.max() + 1) / H, 3)]
    json.dump(dict(registration=shift, boxes_u0_u1_v0_v1=boxes, size=[W, H]), open(out_path[:-4] + ".json", "w"), indent=1)
    print(json.dumps(shift), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
