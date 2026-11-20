#!/usr/bin/env python3
"""
work_common.py: shared pieces for the W0 tools (render-agent, 2026-11-20; 0 tokens): the camera, the clay passes, the lock of a model
still onto the clay or onto its input, and the colour helpers of the MB0 compositor (master stage1-2026-11-17/tools/compose_defaults.py,
imported as C, nothing changed there), the way the MB1 tools did.
Camera W0: (-0.825, 9.85, 1.10), yaw 0, 24 mm (F 1710 px on the 2565 px frame), tilt 0, u0 0.50, v0 0.46; the base.png canvas
2720 x 1530 with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57].
"""
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
REPO = "/home/user/homedesign-app"
CLAY = os.path.join(REPO, "assets/blockout/house/framing/wm-work-2026-11-20")
sys.path.insert(0, os.path.join(REPO, "assets/renders/master/warm-modern/stage1-2026-11-17/tools"))
import compose_defaults as C  # noqa: E402

H, W = 1530, 2720
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
CAM = dict(loc=(-0.825, 9.85, 1.10), yaw=0.0, u0=0.50, v0=0.46)
F_ = 1710.0
CX_ = 1360.0
HZ_ = 765.0 + (CAM["v0"] - 0.5) * 9 / 16 * 2565.0
PICKS = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-work/"
ARCH = (1, 2, 4, 5, 9, 10, 12, 13, 14, 17, 18, 20, 21, 22, 24, 25)      # walls, floor, window, the fixed walnut (the chair's legs: 25)


def proj(X, Y, Z):
    d = CAM["loc"][1] - Y
    return CX_ + F_ * (X - CAM["loc"][0]) / d, HZ_ - F_ * (Z - CAM["loc"][2]) / d


def ids(frame="W0"):
    return np.asarray(Image.open(os.path.join(CLAY, f"{frame}-id.png")))


def depth(frame="W0"):
    d = np.asarray(Image.open(os.path.join(CLAY, f"{frame}-depth.png"))).astype(np.float64)
    return np.where(d >= 65535, np.inf, d / 5000.0)


def frame_mask():
    m = np.zeros((H, W), bool)
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    m[y0:y1, x0:x1] = True
    return m


def ecc_lock(raw, ref, stable, motion=cv2.MOTION_AFFINE):
    """a still at the canvas size, warped onto ref by an ECC fit on the gradient magnitude, masked to stable (as MB1)"""
    r = np.asarray(Image.open(raw).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    pl = (np.asarray(Image.open(ref).convert("RGB")) if isinstance(ref, str) else C.q(ref)).astype(np.float32)

    def g(a):
        y = cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.5)
        gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
        m = np.sqrt(gx * gx + gy * gy)
        return m / (np.percentile(m, 99) + 1e-6)
    a_, b_ = g(r), g(pl)
    warp = np.eye(2, 3, dtype=np.float32)
    cc = {}
    for s in (4, 2, 1):
        a = cv2.resize(a_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        b = cv2.resize(b_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        m = cv2.resize(stable.astype(np.uint8), (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST)
        w = warp.copy()
        w[:, 2] /= s
        c, w = cv2.findTransformECC(b, a, w, motion, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), m, 5)
        w[:, 2] *= s
        warp, cc[s] = w, round(float(c), 4)
    out = cv2.warpAffine(r, warp, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out / 255, 0, 1).astype(np.float64), dict(method="ECC affine on the gradient magnitude, masked", ecc=cc,
                                                              warp=[[round(float(v), 6) for v in row] for row in warp])


def save(path, rgb):
    Image.fromarray(C.q(rgb)).save(path)


def save_frame(rgb, path):
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    Image.fromarray(C.q(rgb)).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(path)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def rel(p):
    return os.path.relpath(p, REPO)
