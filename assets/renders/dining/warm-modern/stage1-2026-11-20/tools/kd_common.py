#!/usr/bin/env python3
"""
kd_common.py: shared pieces for the warm-modern kitchen-dining stage-one tools (render-agent, 2026-11-20; 0 tokens): the two cameras of
PD, the clay passes, the rotation homography D1 <-> D2 (one centre of projection, a pure pan), the lock of a model still onto the clay or
onto its input, and the colour helpers of the MB0 compositor (master/warm-modern/stage1-2026-11-17/tools/compose_defaults.py, imported
as C, nothing changed there).
Cameras: PD (2.80, 3.80, 1.10), D1 yaw -56, D2 yaw -91 (from -Y, positive to -X), 24 mm (F 1710 px on the 2565 px frame), tilt 0,
u0 0.52, v0 0.43; the base.png canvas 2720 x 1530 with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57]. The principal point and the
horizon were checked against the clay's analytic lock lines (lock-target.json): see check_camera().
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-dining-2026-11-20"
sys.path.insert(0, "/home/user/homedesign-app/assets/renders/master/warm-modern/stage1-2026-11-17/tools")
import compose_defaults as C  # noqa: E402

H, W = 1530, 2720
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
FW = FRAME[2] - FRAME[0]
FH = FRAME[3] - FRAME[1]
LOC = (2.80, 3.80, 1.10)
# 10.9 [KD-15] (2026-11-24): D2 is now yaw -86. The stage-one D2 (yaw -91) is kept as "D2o": its plate and the layers cut in it are the
# sources the new D2 is composed from (a pure rotation about PD). The clay of the new D2 is CLAY2 (the 10.9 niche and products).
YAW = {"D1": -56.0, "D2o": -91.0, "D2": -86.0}
CLAY2 = "/home/user/homedesign-app/assets/blockout/house/framing/wm-dining-2026-11-24"


def clay_file(frame, kind):
    """frame: D1, D1-plate, D1-shell, D2o(-plate), D2(-plate); kind: '.png', '-id.png', '-depth.png', '-lock-target.json'"""
    if frame.startswith("D2o"):
        return os.path.join(CLAY, frame.replace("D2o", "D2") + kind)
    if frame.startswith("D2"):
        return os.path.join(CLAY2, frame + kind)
    return os.path.join(CLAY, frame + kind)
U0, V0 = 0.52, 0.43
F_ = FW * 24.0 / 36.0
CX_ = FRAME[0] + U0 * FW
HZ_ = FRAME[1] + V0 * FH
PICKS = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-dining/"


def axes(fr):
    th = math.radians(YAW[fr])
    f = np.array([-math.sin(th), -math.cos(th), 0.0])
    r = np.array([math.cos(th), -math.sin(th), 0.0])
    u = np.array([0.0, 0.0, 1.0])
    return f, r, u


def proj(fr, X, Y, Z):
    f, r, u = axes(fr)
    d = np.array([X - LOC[0], Y - LOC[1], Z - LOC[2]])
    z = d @ f
    return CX_ + F_ * (d @ r) / z, HZ_ - F_ * (d @ u) / z


def depth_of(fr, X, Y):
    f, _, _ = axes(fr)
    return (X - LOC[0]) * f[0] + (Y - LOC[1]) * f[1]


def rays(fr, xs, ys):
    """world directions of canvas pixels (arrays), shape (..., 3)"""
    f, r, u = axes(fr)
    a = (np.asarray(xs, np.float64) - CX_) / F_
    b = -(np.asarray(ys, np.float64) - HZ_) / F_
    return f[None] * 1.0 + a[..., None] * r[None] + b[..., None] * u[None] if np.ndim(a) else f + a * r + b * u


def map_between(src, dst):
    """for every canvas pixel of dst, its (x, y) in src (a pure rotation about PD); also where it lies in front of src's camera"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    d = rays(dst, xx + 0.5, yy + 0.5)
    f, r, u = axes(src)
    z = d @ f
    mx = CX_ + F_ * (d @ r) / np.where(z > 1e-6, z, 1e-6) - 0.5
    my = HZ_ - F_ * (d @ u) / np.where(z > 1e-6, z, 1e-6) - 0.5
    ok = (z > 1e-6) & (mx >= 0) & (mx <= W - 1) & (my >= 0) & (my <= H - 1)
    return mx.astype(np.float32), my.astype(np.float32), ok


def warp(img, src, dst, interp=cv2.INTER_LANCZOS4, maps=None):
    mx, my, ok = maps or map_between(src, dst)
    a = np.asarray(img)
    if a.dtype == bool:
        out = cv2.remap(a.astype(np.uint8), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
        return out & ok
    out = cv2.remap(a.astype(np.float32), mx, my, interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if out.ndim == 3:
        out[~ok] = 0
    else:
        out[~ok] = 0
    return out


def _new(frame, kind, new):
    """new=True: D1 from the clay of 2026-11-24 (10.9's products) when it exists; for the depth test of the projection into D1"""
    p = os.path.join(CLAY2, frame + kind)
    return p if (new and frame.startswith("D1") and os.path.exists(p)) else clay_file(frame, kind)


def ids(frame, new=False):
    return np.asarray(Image.open(_new(frame, "-id.png", new)))


def depth(frame, new=False):
    d = np.asarray(Image.open(_new(frame, "-depth.png", new))).astype(np.float64)
    return np.where(d >= 65535, np.inf, d / 5000.0)


def frame_mask():
    m = np.zeros((H, W), bool)
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    m[y0:y1, x0:x1] = True
    return m


def frame_crop(rgb8):
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    return Image.fromarray(rgb8).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS)


def check_camera():
    """the analytic projection here against the clay's lock lines (Blender's own projection), in canvas px"""
    out = {}
    for fr in ("D1", "D2o", "D2"):
        if not os.path.exists(clay_file(fr, "-lock-target.json")):
            continue
        J = json.load(open(clay_file(fr, "-lock-target.json")))
        errs = []
        for name, L in J["lines"].items():
            for (a, b) in zip(L["xyz"], L["px_ends"]):
                x, y = proj(fr, *a)
                errs.append(math.hypot(x - b[0], y - b[1]))
        out[fr] = dict(n=len(errs), max_px=round(max(errs), 3), mean_px=round(float(np.mean(errs)), 3))
    return out


def ecc_lock(raw, ref, stable, motion=cv2.MOTION_AFFINE):
    """a still at the canvas size, warped onto ref by an ECC fit on the gradient magnitude, masked to stable"""
    r = np.asarray(Image.open(raw).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32) if isinstance(raw, str) else (raw * 255).astype(np.float32)
    pl = (np.asarray(Image.open(ref).convert("RGB")) if isinstance(ref, str) else C.q(ref)).astype(np.float32)

    def g(a):
        y = cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.5)
        gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
        m = np.sqrt(gx * gx + gy * gy)
        return m / (np.percentile(m, 99) + 1e-6)
    a_, b_ = g(r), g(pl)
    warp_ = np.eye(3, 3, dtype=np.float32) if motion == cv2.MOTION_HOMOGRAPHY else np.eye(2, 3, dtype=np.float32)
    cc = {}
    for s in (4, 2, 1):
        a = cv2.resize(a_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        b = cv2.resize(b_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        m = cv2.resize(stable.astype(np.uint8), (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST)
        w = warp_.copy()
        if motion == cv2.MOTION_HOMOGRAPHY:
            S = np.diag([1 / s, 1 / s, 1]).astype(np.float32)
            w = S @ w @ np.linalg.inv(S)
        else:
            w[:, 2] /= s
        c, w = cv2.findTransformECC(b, a, w, motion, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), m, 5)
        if motion == cv2.MOTION_HOMOGRAPHY:
            S = np.diag([1 / s, 1 / s, 1]).astype(np.float32)
            w = np.linalg.inv(S) @ w @ S
        else:
            w[:, 2] *= s
        warp_, cc[s] = w, round(float(c), 4)
    if motion == cv2.MOTION_HOMOGRAPHY:
        out = cv2.warpPerspective(r, warp_, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    else:
        out = cv2.warpAffine(r, warp_, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out / 255, 0, 1).astype(np.float64), dict(method="ECC on the gradient magnitude, masked", motion=int(motion), ecc=cc,
                                                              warp=[[round(float(v), 6) for v in row] for row in warp_])


def save(path, rgb):
    Image.fromarray(C.q(rgb)).save(path)


def sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def lab_hex(h):
    h = h.lstrip("#")
    rgb = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64) / 255
    return C.to_lab(rgb[None, None])[0, 0]
