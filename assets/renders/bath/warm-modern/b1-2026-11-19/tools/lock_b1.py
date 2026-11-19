#!/usr/bin/env python3
"""
lock_b1.py: a B1 still against its clay (render-agent, 2026-11-19; 0 tokens). B2's lock_b2.py and compose_plate.fit as they are,
pointed at the B1 clay's named lines (assets/blockout/house/framing/wm-bath-b1-2026-11-19/lock-target.json). One global warp: y about
the horizon (row 707, the same camera intrinsics as B2) by the fitted scale and offset, x by the fitted constant; nothing local.

  python3 lock_b1.py <still.png> <clay.png> <lock.json> <warped.png>
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

B2T = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools"
CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-b1-2026-11-19/"
sys.path.insert(0, B2T)
import compose_plate as CP  # noqa: E402
import lock_b2 as LB  # noqa: E402

CP.CLAY = CLAY
LB.LT = CLAY + "lock-target.json"
HORIZON = 707.0


def lock(still, clay, lock_json):
    LB.main(still, clay, lock_json)
    return CP.fit(json.load(open(lock_json)))


def warp(img, a, b, c):
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    out = cv2.remap(img.astype(np.float32), xx + c, yy + a + b * (yy - HORIZON), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out, 0, 1).astype(np.float64)


def main(still, clay, lock_json, out):
    a, b, c, used = lock(still, clay, lock_json)
    img = np.asarray(Image.open(still).convert("RGB")).astype(np.float64) / 255
    w = warp(img, a, b, c)
    Image.fromarray(np.clip(np.rint(w * 255), 0, 255).astype(np.uint8)).save(out)
    rec = json.load(open(lock_json))
    rec["fit"] = dict(y_offset_px=round(a, 3), y_scale_about_row_707=round(b, 6), x_offset_px=round(c, 3), used=used)
    json.dump(rec, open(lock_json, "w"), indent=1)
    print(json.dumps(rec["fit"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
