#!/usr/bin/env python3
"""
kids_common.py: shared pieces for the warm-modern kids' rooms stage-one tools (render-agent, 2026-11-24; 0 tokens): the two cameras
(K-boy, K-girl = K-boy + 3.63 in Y: the same view of a sibling room), the clay passes, the lock of a model still onto a reference, and
the colour helpers of the MB0 compositor (master/warm-modern/stage1-2026-11-17/tools/compose_defaults.py, imported as C, nothing changed
there), the way the work room and the kitchen tools did.
Cameras: (1.10, 13.00 | 16.63, 1.00), yaw 33 (from -Y, positive to -X), 24 mm (F 1710 px on the 2565 px frame), tilt 0, u0 0.52,
v0 0.44; the base.png canvas 2720 x 1530 with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57].
The tools serve both rooms; their outputs go to assets/renders/<kid>/warm-modern/stage1-2026-11-24/ (ST[kid]).
"""
import hashlib
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/homedesign-app"
ST = {k: os.path.join(REPO, f"assets/renders/{k}/warm-modern/stage1-2026-11-24") for k in ("boy", "girl")}
CLAY = os.path.join(REPO, "assets/blockout/house/framing/wm-kids-2026-11-24")
PROMPTS = os.path.join(REPO, "assets/prompts/warm-modern-kids-2026-11-24")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-kids/"
PICKS = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/"
sys.path.insert(0, os.path.join(REPO, "assets/renders/master/warm-modern/stage1-2026-11-17/tools"))
import compose_defaults as C  # noqa: E402

H, W = 1530, 2720
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
FW = FRAME[2] - FRAME[0]
FH = FRAME[3] - FRAME[1]
DY = {"boy": 0.0, "girl": 3.63}
LOC = {"boy": (1.10, 13.00, 1.00), "girl": (1.10, 16.63, 1.00)}
YAW = 33.0
U0, V0 = 0.52, 0.44
F_ = FW * 24.0 / 36.0
CX_ = FRAME[0] + U0 * FW
HZ_ = FRAME[1] + V0 * FH
# clay ids (framing_wm_kids.py)
ARCH = (1, 2, 3, 4, 5, 8, 9, 10, 12, 13, 14, 19, 20, 21, 22, 23, 24, 25)
PLASTER = (1, 2, 3, 4, 9, 12)
BAND = (5, 8, 19)
FIXED = (20, 21, 22, 23, 24, 25)


def axes():
    th = math.radians(YAW)
    return np.array([-math.sin(th), -math.cos(th), 0.0]), np.array([math.cos(th), -math.sin(th), 0.0]), np.array([0.0, 0.0, 1.0])


def proj(kid, X, Y, Z):
    f, r, u = axes()
    L = LOC[kid]
    d = np.array([X - L[0], Y - L[1], Z - L[2]])
    z = d @ f
    return CX_ + F_ * (d @ r) / z, HZ_ - F_ * (d @ u) / z


def ids(frame):
    return np.asarray(Image.open(os.path.join(CLAY, f"{frame}-id.png")))


def depth(frame):
    d = np.asarray(Image.open(os.path.join(CLAY, f"{frame}-depth.png"))).astype(np.float64)
    return np.where(d >= 65535, np.inf, d / 5000.0)


def frame_mask():
    m = np.zeros((H, W), bool)
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    m[y0:y1, x0:x1] = True
    return m


def check_camera(kid):
    J = json.load(open(os.path.join(CLAY, f"{kid}-lock-target.json")))
    errs = []
    for name, L in J["lines"].items():
        for a, b in zip(L["xyz"], L["px_ends"]):
            x, y = proj(kid, *a)
            errs.append(math.hypot(x - b[0], y - b[1]))
    return dict(n=len(errs), max_px=round(max(errs), 3), mean_px=round(float(np.mean(errs)), 3))


def grad(a):
    y = cv2.GaussianBlur(a.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.5)
    gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
    m = np.sqrt(gx * gx + gy * gy)
    return m / (np.percentile(m, 99) + 1e-6)


def ecc_lock(raw, ref, stable, size=(W, H), motion=cv2.MOTION_AFFINE):
    """a still at `size`, warped onto ref (path or float image) by an ECC fit on the gradient magnitude, masked to stable"""
    r = np.asarray(Image.open(raw).convert("RGB").resize(size, Image.LANCZOS)).astype(np.float32) if isinstance(raw, str) else \
        np.asarray(raw, np.float32) * (255 if raw.max() <= 1.0 else 1)
    pl = (np.asarray(Image.open(ref).convert("RGB")) if isinstance(ref, str) else C.q(ref)).astype(np.float32)
    a_, b_ = grad(r), grad(pl)
    warp = np.eye(2, 3, dtype=np.float32)
    cc = {}
    for s in (4, 2, 1):
        a = cv2.resize(a_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        b = cv2.resize(b_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        m = cv2.resize(stable.astype(np.uint8), (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST)
        w = warp.copy()
        w[:, 2] /= s
        try:
            c, w = cv2.findTransformECC(b, a, w, motion, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), m, 5)
        except cv2.error:
            c = None
        w[:, 2] *= s
        warp, cc[s] = w, None if c is None else round(float(c), 4)
    out = cv2.warpAffine(r, warp, (size[0], size[1]), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out / 255, 0, 1).astype(np.float64), dict(method="ECC affine on the gradient magnitude, masked", ecc=cc,
                                                              warp=[[round(float(v), 6) for v in row] for row in warp])


def save(path, rgb):
    Image.fromarray(C.q(rgb)).save(path)


def save_frame(rgb, path):
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    a = C.q(rgb) if np.asarray(rgb).dtype != np.uint8 else np.asarray(rgb)
    Image.fromarray(a).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(path)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def rel(p):
    return os.path.relpath(p, REPO)


def lab_hex(h):
    h = h.lstrip("#")
    rgb = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64) / 255
    return C.to_lab(rgb[None, None])[0, 0]


def lch(lab):
    return float(lab[0]), float(math.hypot(lab[1], lab[2])), float(math.degrees(math.atan2(lab[2], lab[1])) % 360)


def from_lch(L, Cc, h):
    return np.array([L, Cc * math.cos(math.radians(h)), Cc * math.sin(math.radians(h))])
