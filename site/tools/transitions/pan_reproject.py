#!/usr/bin/env python3
"""
pan_reproject.py: a camera pan between two stills taken from the same centre of projection, built in code by
homography reprojection (route R of docs/transitions-plan-2026-11-02.md). 0 var2 tokens.

A pure rotation about the lens centre has no parallax, so every in-between frame of a pan is an exact
reprojection of the two stills:  x_dst = K_dst . R_dst^T . R_src . K_src^-1 . x_src.

Conventions (docs/house-plan.json -> conventions):
  yaw_deg_left: heading from -Y, positive toward -X (left);  f = (-sin yaw, -cos yaw, 0),  r = (cos yaw, -sin yaw, 0)
  projection:   u = u0 + 0.6667 x/d ;  v = v0 + 1.1852 (Hc - Z)/d   (24 mm, 16:9; the same focal in square pixels)
  u, v are fractions of the frame (0 = left / top edge). A level camera (tilt 0, roll 0) everywhere.
The clay pipeline (assets/blockout/house/build_house.py set_view, mirrored camera) uses the same model; the
`check` command measures it against two clay renders.

Commands
  pan       the pan as frames: a constant-speed "render" clip (24 fps, the Bible pan speed, like a video segment)
            and/or playback frames sampled uniformly in progress (for the site export), optional motion blur
  compose   a rotation pose still: the master reprojected wherever it covers, the raw pose render only in the
            revealed strip, with a soft world-fixed seam (3-5 % of the width) next to the master's edge
  check     reproject A into B's camera and measure the overlap: residual shift (phase correlation) and difference
  selftest  synthetic test on one still: two virtual cameras cut from it, the tool's pan against the exact
            reprojection, endpoint identity, seam behaviour; writes a JSON report and a short clip

Seams. Endpoints are exact by construction: the first frame is A, the last frame is B (or the composite pose).
In between, a seam that moves across the frame decides which still is used where the two overlap: it starts
just outside the edge where new content enters and ends just outside the opposite edge, crossing the frame
fastest in the middle of the pan (where playback is fastest too). Where only one still covers, that still is
used. With a composite pose the two stills are identical outside the strip, so the moving seam is invisible
there; with two masters (P-D, P-B) it is a soft wipe across the overlap, visible only where the masters differ.

Requires: Python 3.10+, numpy, opencv-python-headless, Pillow (pip install numpy opencv-python-headless pillow).
ffmpeg for the mp4.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace

import cv2
import numpy as np
from PIL import Image

FX_REL = 0.6667      # focal / frame width  (24 mm on 16:9, house-plan conventions.projection)
FY_REL = 1.1852      # focal / frame height (the same focal: 0.6667 * 16/9)


# ----------------------------------------------------------------------------------------------------------------
# cameras
# ----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cam:
    yaw: float                 # degrees, positive = left (house-plan yaw_deg_left)
    u0: float = 0.52           # principal point, fraction of the width
    v0: float = 0.46           # principal point, fraction of the height
    fx_rel: float = FX_REL     # focal / width   (a crop of the frame = a longer relative focal)
    fy_rel: float = FY_REL     # focal / height

    def K(self, w: int, h: int) -> np.ndarray:
        # pixel centres at integer indices: u (fraction) = (i + 0.5) / w
        return np.array([[self.fx_rel * w, 0.0, self.u0 * w - 0.5],
                         [0.0, self.fy_rel * h, self.v0 * h - 0.5],
                         [0.0, 0.0, 1.0]])

    def R(self) -> np.ndarray:
        """Camera-to-world rotation; camera axes (x right, y down, z forward)."""
        a = math.radians(self.yaw)
        r = np.array([math.cos(a), -math.sin(a), 0.0])
        f = np.array([-math.sin(a), -math.cos(a), 0.0])
        down = np.array([0.0, 0.0, -1.0])
        return np.stack([r, down, f], axis=1)

    def hfov_edges(self) -> tuple[float, float]:
        """World azimuths (yaw convention) of the left and right frame edges."""
        left = self.yaw + math.degrees(math.atan(self.u0 / self.fx_rel))
        right = self.yaw - math.degrees(math.atan((1.0 - self.u0) / self.fx_rel))
        return left, right


def parse_cam(s: str) -> Cam:
    """'yaw,u0,v0' (u0, v0 optional)."""
    p = [float(x) for x in s.split(",")]
    return Cam(p[0], *(p[1:3]))


def overscan_cam(c: Cam, ovs: float) -> Cam:
    """The camera of a still rendered with `ovs` extra height above and below its 16:9 frame (same focal, same
    principal point): its K in its own pixels."""
    if ovs <= 0:
        return c
    k = 1 + 2 * ovs
    return replace(c, v0=(c.v0 + ovs) / k, fy_rel=c.fy_rel / k)


def crop16(img: np.ndarray, ovs: float) -> np.ndarray:
    """The 16:9 frame inside an overscan still."""
    if ovs <= 0:
        return img
    h16 = int(round(img.shape[0] / (1 + 2 * ovs)))
    top = int(round(ovs * h16))
    return img[top:top + h16]


def lerp_cam(a: Cam, b: Cam, s: float) -> Cam:
    return Cam(a.yaw + (b.yaw - a.yaw) * s, a.u0 + (b.u0 - a.u0) * s, a.v0 + (b.v0 - a.v0) * s,
               a.fx_rel + (b.fx_rel - a.fx_rel) * s, a.fy_rel + (b.fy_rel - a.fy_rel) * s)


def homography(src: Cam, sw: int, sh: int, dst: Cam, dw: int, dh: int) -> np.ndarray:
    """Pixel in src -> pixel in dst (same centre of projection)."""
    H = dst.K(dw, dh) @ dst.R().T @ src.R() @ np.linalg.inv(src.K(sw, sh))
    return H / H[2, 2]


# ----------------------------------------------------------------------------------------------------------------
# easing (Design Bible, "גריידינג ותנועה": ease-in-out cubic, 15 % acceleration, 30 % landing)
# Velocity rises from 0 over the first 15 % of the play time and falls to 0 over the last 30 %, each ramp a cubic
# smoothstep, constant in between: position, velocity and acceleration are continuous (a gimbal walk, no kick).
# ----------------------------------------------------------------------------------------------------------------
def ease(t: float, a: float = 0.15, d: float = 0.30) -> float:
    vmax = 1.0 / (1.0 - a / 2 - d / 2)
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    if t < a:
        x = t / a
        return vmax * a * (x ** 3 - x ** 4 / 2)
    if t <= 1 - d:
        return vmax * a / 2 + vmax * (t - a)
    x = (1 - t) / d
    return 1.0 - vmax * d * (x ** 3 - x ** 4 / 2)


def ease_speed(t: float, a: float = 0.15, d: float = 0.30) -> float:
    """d(progress)/d(t), both normalised to 0..1."""
    vmax = 1.0 / (1.0 - a / 2 - d / 2)
    sm = lambda x: 3 * x * x - 2 * x ** 3
    if t <= 0 or t >= 1:
        return 0.0
    if t < a:
        return vmax * sm(t / a)
    if t <= 1 - d:
        return vmax
    return vmax * sm((1 - t) / d)


def ease_inv(p: float, a: float = 0.15, d: float = 0.30) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if ease(mid, a, d) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def smootherstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


# ----------------------------------------------------------------------------------------------------------------
# images
# ----------------------------------------------------------------------------------------------------------------
def load(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


def save(path: str, img: np.ndarray) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(to8(img)).save(path)


def to8(img: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(img * 255.0), 0, 255).astype(np.uint8)


def fit(img: np.ndarray, w: int, h: int) -> np.ndarray:
    """Resize a 16:9 still to the working size (area filter when shrinking). The same call is used for the
    endpoints and for the warp sources, so frame 0 and the master at that size are identical."""
    if img.shape[1] == w and img.shape[0] == h:
        return img
    interp = cv2.INTER_AREA if img.shape[1] > w else cv2.INTER_CUBIC
    return cv2.resize(img, (w, h), interpolation=interp)


def warp(img: np.ndarray, src: Cam, dst: Cam, w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Reproject img (taken with src) into dst at w x h. Returns (image, soft coverage 0..1)."""
    sh, sw = img.shape[:2]
    H = homography(src, sw, sh, dst, w, h)
    if np.allclose(H, np.eye(3), atol=1e-10) and (sw, sh) == (w, h):
        return img.copy(), np.ones((h, w), np.float32)
    out = cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    cov = cv2.warpPerspective(np.ones((sh, sw), np.float32), H, (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # keep the Lanczos ringing of the source border out: 2 px inset, then a 2 px soft edge
    hard = (cov > 0.999).astype(np.uint8)
    hard = cv2.erode(hard, np.ones((3, 3), np.uint8), iterations=2).astype(np.float32)
    soft = cv2.GaussianBlur(hard, (0, 0), 1.0) * hard
    return np.clip(out, 0, 1), soft


def azimuth_map(cam: Cam, w: int, h: int) -> np.ndarray:
    """World azimuth (degrees, yaw convention) of every pixel column (a level camera: columns are vertical planes)."""
    K = cam.K(w, h)
    x = (np.arange(w, dtype=np.float64) - K[0, 2]) / K[0, 0]
    return (cam.yaw - np.degrees(np.arctan(x))).astype(np.float32)


# ----------------------------------------------------------------------------------------------------------------
# the pan
# ----------------------------------------------------------------------------------------------------------------
@dataclass
class Pan:
    A: np.ndarray            # first still (a master), full resolution
    cam_a: Cam
    B: np.ndarray            # last still: a master, or a raw pose render (kind="pose")
    cam_b: Cam
    kind: str = "master"     # "master": B is final;  "pose": B is a raw render, the strip-only composite is final
    seam_frac: float = 0.04  # soft seam width, fraction of the frame width (designer: 3-5 %)
    seam_inset: float = 0.004  # the composite seam starts this far inside the master's edge (fraction of width)
    ovs_a: float = 0.0       # vertical overscan of A: extra rows above and below the 16:9 frame, fraction of its height
    ovs_b: float = 0.0       # (a still rendered taller than 16:9 with the same camera; its 16:9 centre is the frame)

    def __post_init__(self):
        self._cache: dict = {}
        self.src_a = overscan_cam(self.cam_a, self.ovs_a)
        self.src_b = overscan_cam(self.cam_b, self.ovs_b)
        self.dyaw = self.cam_b.yaw - self.cam_a.yaw
        self.direction = "right" if self.dyaw < 0 else "left"   # where new content enters

    def sources(self, w: int, h: int):
        key = (w, h)
        if key not in self._cache:
            # sources at about the output scale, so the warp is close to 1:1 (no aliasing when shrinking)
            aw, bw = self.A.shape[1], self.B.shape[1]
            sa = fit(self.A, w, int(round(h * (1 + 2 * self.ovs_a)))) if aw >= w else self.A
            sb = fit(self.B, w, int(round(h * (1 + 2 * self.ovs_b)))) if bw >= w else self.B
            self._cache[key] = (sa, sb)
        return self._cache[key]

    # the master's edge on the strip side, as a world azimuth
    def _edge_az(self) -> float:
        left, right = self.cam_a.hfov_edges()
        return right if self.direction == "right" else left

    def pose_formula(self, cam: Cam, w: int, h: int, wa=None, ca=None, wb=None, cb=None) -> np.ndarray:
        """The composite pose seen from `cam`: master wherever it covers (world-fixed soft seam next to its edge),
        the raw pose render elsewhere."""
        sa, sb = self.sources(w, h)
        if wa is None:
            wa, ca = warp(sa, self.src_a, cam, w, h)
            wb, cb = warp(sb, self.src_b, cam, w, h)
        az = azimuth_map(cam, w, h)
        edge = self._edge_az()
        inside = (az - edge) if self.direction == "right" else (edge - az)          # degrees inside the master
        hfov = sum(abs(math.degrees(math.atan(x / cam.fx_rel))) for x in (cam.u0, 1 - cam.u0))
        band = self.seam_frac * hfov
        inset = self.seam_inset * hfov
        wm = smootherstep((inside - inset) / band)[None, :] * ca                    # master weight
        wm = np.where(cb > 0.01, wm, np.maximum(wm, ca))
        return wm[..., None] * wa + (1 - wm[..., None]) * wb

    def frame(self, s: float, w: int, h: int) -> tuple[np.ndarray, float]:
        """The pan at progress s (0..1 of the angle). Returns (image, hole fraction)."""
        sa, sb = self.sources(w, h)
        if s <= 0.0:
            return fit(crop16(self.A, self.ovs_a), w, h), 0.0
        cam = lerp_cam(self.cam_a, self.cam_b, s)
        wa, ca = warp(sa, self.src_a, cam, w, h)
        wb, cb = warp(sb, self.src_b, cam, w, h)
        if self.kind == "pose":
            tb = self.pose_formula(cam, w, h, wa, ca, wb, cb)
            cbm = np.maximum(cb, ca)
        else:
            if s >= 1.0:
                return fit(crop16(self.B, self.ovs_b), w, h), 0.0
            tb, cbm = wb, cb
        if s >= 1.0:
            return np.clip(tb, 0, 1), 0.0
        # the moving seam: from just outside the entering edge (s=0) to just outside the opposite edge (s=1)
        band = self.seam_frac
        m = float(smootherstep(s))
        u = (np.arange(w, dtype=np.float32) + 0.5) / w
        if self.direction == "right":
            us = (1 + band) - (1 + 2 * band) * m
            wseam = smootherstep((u - us) / band + 0.5)
        else:
            us = -band + (1 + 2 * band) * m
            wseam = smootherstep((us - u) / band + 0.5)
        wB = np.broadcast_to(wseam[None, :], (h, w)).astype(np.float32)
        # coverage: a still that does not cover a pixel cannot be used there
        wB = np.where(ca < 1.0, np.maximum(wB, 1 - ca), wB)
        wB = np.where(cbm < 1.0, np.minimum(wB, cbm), wB)
        hole = (ca < 0.01) & (cbm < 0.01)
        out = np.clip((1 - wB[..., None]) * wa + wB[..., None] * tb, 0, 1)
        if hole.any():
            # The pan gap: between the two axes the intermediate view sees a sliver above the top edge and below
            # the bottom edge that neither still covers ((sec(dyaw/2) - 1) of the distance from the horizon to the
            # edge: ~1 % of the height at 22-25 deg, ~2-3 % at 33-35 deg). Filled here by inpainting; the plan
            # removes it at the source with vertical overscan (README, "פער ה-pan").
            m = cv2.dilate(hole.astype(np.uint8), np.ones((5, 5), np.uint8))
            out = cv2.inpaint(to8(out), m, 6, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
        return out, float(hole.mean())

    def frame_blur(self, s: float, w: int, h: int, blur_deg: float, max_sub: int = 16) -> tuple[np.ndarray, float]:
        """Rotational motion blur: the average of sub-frames over `blur_deg` of yaw centred on s (180 deg shutter
        is half the angle per frame). No blur at the endpoints, so they stay exact."""
        span_s = abs(blur_deg / self.dyaw) if self.dyaw else 0.0
        fx_px = self.cam_a.fx_rel * w
        span_px = abs(math.radians(blur_deg)) * fx_px
        n = int(min(max_sub, max(1, math.ceil(span_px / 1.25))))
        if n <= 1 or s <= 0 or s >= 1:
            return self.frame(s, w, h)
        acc = np.zeros((h, w, 3), np.float32)
        holes = 0.0
        for k in range(n):
            sk = min(1.0, max(0.0, s + span_s * ((k + 0.5) / n - 0.5)))
            f, hfrac = self.frame(sk, w, h)
            acc += f
            holes = max(holes, hfrac)
        return acc / n, holes


# ----------------------------------------------------------------------------------------------------------------
# outputs
# ----------------------------------------------------------------------------------------------------------------
def write_mp4(frames_dir: str, fps: float, out: str, crf: int = 16) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{fps}", "-i", os.path.join(frames_dir, "%04d.png"),
           "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-an", out]
    subprocess.run(cmd, check=True)


def render_constant_clip(pan: Pan, out_dir: str, w: int, h: int, fps: float = 24.0, deg_per_s: float = 8.0,
                         blur: bool = True, shutter: float = 0.5) -> dict:
    """The pan as a constant-speed clip, like a video segment rendered at the Bible pan speed (<= 8 deg/s)."""
    deg = abs(pan.dyaw)
    n = max(2, int(round(deg / deg_per_s * fps)) + 1)
    os.makedirs(out_dir, exist_ok=True)
    step = deg / (n - 1)
    holes = 0.0
    for i in range(n):
        s = i / (n - 1)
        img, hfrac = pan.frame_blur(s, w, h, step * shutter) if blur else pan.frame(s, w, h)
        holes = max(holes, hfrac)
        Image.fromarray(to8(img)).save(os.path.join(out_dir, f"{i + 1:04d}.png"), compress_level=1)
    return dict(frames=n, fps=fps, deg=deg, deg_per_s=deg / ((n - 1) / fps), max_hole_fraction=holes)


MOBILE_FRAC = 0.3375   # skeleton-spec "מצלמות", mobile: a full-height 3:5 window = 0.3375 of a 16:9 frame's width


def mobile_crop(img: np.ndarray, centre_u: float, frac: float = MOBILE_FRAC) -> np.ndarray:
    """The full-height 3:5 window centred at centre_u (fraction of the width), clamped inside the frame, with a
    sub-pixel position so a moving window does not step."""
    h, w = img.shape[:2]
    cw = int(round(frac * w))
    left = min(max(centre_u * w - cw / 2.0, 0.0), w - cw)
    if abs(left - round(left)) < 1e-6:
        k = int(round(left))
        return img[:, k:k + cw].copy()
    M = np.array([[1.0, 0.0, -left], [0.0, 1.0, 0.0]])
    return cv2.warpAffine(img, M, (cw, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)


def render_playback(pan: Pan, out_dir: str, w: int, h: int, play_s: float, fps: float = 60.0, blur: bool = True,
                    shutter: float = 0.5, p_range=(0.0, 1.0), frames_total: int | None = None,
                    mobile_dir: str | None = None, mobile_window: tuple[float, float] | None = None) -> dict:
    """Frames uniform in path progress (the site applies the easing when it plays them). The motion blur of each
    frame matches the speed at which the eased playback shows it. With mobile_dir, also the phone sequence: the
    3:5 window moves from the first still's mobile window to the last one's, linearly in progress, so on screen it
    follows the same easing as the camera."""
    n = frames_total or max(2, int(round(play_s * fps)))
    os.makedirs(out_dir, exist_ok=True)
    if mobile_dir:
        os.makedirs(mobile_dir, exist_ok=True)
    p0, p1 = p_range
    holes = 0.0
    for i in range(n):
        p = i / (n - 1)
        s = (p - p0) / (p1 - p0)
        t = ease_inv(p)
        dp_dt = ease_speed(t) / play_s                            # progress per second
        deg_per_s = dp_dt / (p1 - p0) * abs(pan.dyaw)
        bdeg = deg_per_s * shutter / fps
        img, hfrac = pan.frame_blur(s, w, h, bdeg) if blur else pan.frame(s, w, h)
        holes = max(holes, hfrac)
        Image.fromarray(to8(img)).save(os.path.join(out_dir, f"{i + 1:04d}.png"), compress_level=1)
        if mobile_dir and mobile_window:
            c = mobile_window[0] + (mobile_window[1] - mobile_window[0]) * p
            Image.fromarray(to8(mobile_crop(img, c))).save(os.path.join(mobile_dir, f"{i + 1:04d}.png"), compress_level=1)
    return dict(frames=n, fps=fps, play_s=play_s, max_hole_fraction=holes,
                mobile=(dict(window=list(mobile_window), size=[int(round(MOBILE_FRAC * w)), h]) if mobile_dir else None))


# ----------------------------------------------------------------------------------------------------------------
# check: reproject A into B and measure the overlap
# ----------------------------------------------------------------------------------------------------------------
def overlap_check(A: np.ndarray, cam_a: Cam, B: np.ndarray, cam_b: Cam, w: int = 1920, h: int = 1080,
                  diff_out: str | None = None) -> dict:
    a = fit(A, w, h)
    b = fit(B, w, h)
    wa, ca = warp(a, cam_a, cam_b, w, h)
    m = ca > 0.999
    cols = np.where(m.any(axis=0))[0]
    rows = np.where(m.any(axis=1))[0]
    x0, x1, y0, y1 = cols.min(), cols.max(), rows.min(), rows.max()
    # largest rectangle inside the overlap (columns fully covered)
    full = np.where(m[y0 + 40:y1 - 40].all(axis=0))[0]
    x0, x1 = full.min(), full.max()
    ga = cv2.cvtColor(to8(wa[y0:y1, x0:x1]), cv2.COLOR_RGB2GRAY).astype(np.float32)
    gb = cv2.cvtColor(to8(b[y0:y1, x0:x1]), cv2.COLOR_RGB2GRAY).astype(np.float32)
    # edges carry the geometry; lighting differences between the two stills do not matter to the shift
    ea = cv2.Laplacian(cv2.GaussianBlur(ga, (0, 0), 1.5), cv2.CV_32F)
    eb = cv2.Laplacian(cv2.GaussianBlur(gb, (0, 0), 1.5), cv2.CV_32F)
    win = cv2.createHanningWindow((ea.shape[1], ea.shape[0]), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(ea, eb, win)
    # local shifts in vertical bands (a model that redrew a line shows up as a local shift)
    bands = []
    nb = 4
    for k in range(nb):
        xa, xb = int(k * ea.shape[1] / nb), int((k + 1) * ea.shape[1] / nb)
        wb_ = cv2.createHanningWindow((xb - xa, ea.shape[0]), cv2.CV_32F)
        (bx, by), br = cv2.phaseCorrelate(ea[:, xa:xb].copy(), eb[:, xa:xb].copy(), wb_)
        bands.append(dict(u=[round((x0 + xa) / w, 3), round((x0 + xb) / w, 3)], dx_px=round(bx, 2), dy_px=round(by, 2),
                          response=round(br, 3)))
    lab_a = cv2.cvtColor(wa[y0:y1, x0:x1].astype(np.float32), cv2.COLOR_RGB2LAB)
    lab_b = cv2.cvtColor(b[y0:y1, x0:x1].astype(np.float32), cv2.COLOR_RGB2LAB)
    de = np.sqrt(((lab_a - lab_b) ** 2).sum(axis=2))
    res = dict(size=[w, h], overlap_u=[round(x0 / w, 3), round(x1 / w, 3)], overlap_v=[round(y0 / h, 3), round(y1 / h, 3)],
               shift_px=dict(dx=round(dx, 2), dy=round(dy, 2), response=round(resp, 3)), bands=bands,
               deltaE=dict(mean=round(float(de.mean()), 2), p95=round(float(np.percentile(de, 95)), 2),
                           share_over_5=round(float((de > 5).mean()), 3)),
               L_mean=dict(a=round(float(lab_a[..., 0].mean()), 1), b=round(float(lab_b[..., 0].mean()), 1)))
    if diff_out:
        vis = np.concatenate([wa[y0:y1, x0:x1], b[y0:y1, x0:x1]], axis=1)
        d = np.clip(de / 20.0, 0, 1)
        dv = np.stack([d, d * 0.3, d * 0.0], axis=2)
        blend = 0.5 * wa[y0:y1, x0:x1] + 0.5 * b[y0:y1, x0:x1]
        sheet = np.concatenate([vis, np.concatenate([blend, dv], axis=1)], axis=0)
        sheet = cv2.resize(sheet, (sheet.shape[1] // 2, sheet.shape[0] // 2), interpolation=cv2.INTER_AREA)
        save(diff_out, sheet)
        res["sheet"] = diff_out
    return res


# ----------------------------------------------------------------------------------------------------------------
# register: lock a render onto its clay (or onto a neighbour reprojected), one global affine by ECC on edges
# ----------------------------------------------------------------------------------------------------------------
def _edges(img: np.ndarray, w: int) -> np.ndarray:
    h = int(round(w * img.shape[0] / img.shape[1]))
    g = cv2.cvtColor(cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    m = np.sqrt(gx * gx + gy * gy)
    return (m / (np.percentile(m, 99) + 1e-6)).clip(0, 1).astype(np.float32)


def register(img: np.ndarray, ref: np.ndarray, work_w: int = 960, mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Affine that maps `img` onto `ref` (both 16:9, any size). Returns (registered img at img's size, 2x3 matrix
    in img pixels). A global correction only: a render whose lines are redrawn locally keeps a residual, which
    `check` reports per band; then the frame goes back to the render agent instead."""
    e_ref = _edges(ref, work_w)
    e_img = _edges(img, work_w)
    M = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    m8 = None if mask is None else cv2.resize(mask.astype(np.uint8), (e_ref.shape[1], e_ref.shape[0]), interpolation=cv2.INTER_NEAREST)
    _, M = cv2.findTransformECC(e_ref, e_img, M, cv2.MOTION_AFFINE, crit, m8, 5)
    s = img.shape[1] / work_w
    Mf = M.copy().astype(np.float64)
    Mf[:, 2] *= s
    out = cv2.warpAffine(img, Mf, (img.shape[1], img.shape[0]), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_REPLICATE)
    return np.clip(out, 0, 1), Mf


# ----------------------------------------------------------------------------------------------------------------
# selftest: two virtual cameras cut from one still
# ----------------------------------------------------------------------------------------------------------------
def selftest(src_path: str, cam: Cam, out_dir: str, half_deg: float = 7.0, crop: float = 0.6, w: int = 1152,
             clip_fps: float = 24.0) -> dict:
    """Virtual cameras A (yaw + half_deg) and B (yaw - half_deg), each a `crop`-wide window with the source focal,
    so both lie inside the source. The ground truth at every step is the source reprojected directly."""
    os.makedirs(out_dir, exist_ok=True)
    S = load(src_path)
    h = int(round(w * 9 / 16))
    ca_ = Cam(cam.yaw + half_deg, 0.5, cam.v0, cam.fx_rel / crop, cam.fy_rel / crop)
    cb_ = Cam(cam.yaw - half_deg, 0.5, cam.v0, cam.fx_rel / crop, cam.fy_rel / crop)
    big = fit(S, 2 * w, 2 * h)
    A, _ = warp(big, cam, ca_, w, h)
    B, _ = warp(big, cam, cb_, w, h)
    rep: dict = dict(source=src_path, source_cam=cam.__dict__, cam_a=ca_.__dict__, cam_b=cb_.__dict__, size=[w, h])

    # 1. masters mode, B untouched: every frame must equal the direct reprojection (up to one extra resampling)
    pan = Pan(A, ca_, B, cb_, kind="master")
    errs, shifts = [], []
    for s in np.linspace(0, 1, 9):
        f, _ = pan.frame(float(s), w, h)
        g, cg = warp(big, cam, lerp_cam(ca_, cb_, float(s)), w, h)
        m = cg > 0.999
        e = np.abs(f - g)[m] * 255
        errs.append(dict(s=round(float(s), 3), mean_abs=round(float(e.mean()), 3), p99=round(float(np.percentile(e, 99)), 2)))
        g8 = cv2.cvtColor(to8(g), cv2.COLOR_RGB2GRAY).astype(np.float32)
        f8 = cv2.cvtColor(to8(f), cv2.COLOR_RGB2GRAY).astype(np.float32)
        (dx, dy), _ = cv2.phaseCorrelate(g8, f8, cv2.createHanningWindow((w, h), cv2.CV_32F))
        shifts.append(round(math.hypot(dx, dy), 3))
    f0, _ = pan.frame(0.0, w, h)
    f1, _ = pan.frame(1.0, w, h)
    rep["masters_mode"] = dict(per_step=errs, max_shift_px=max(shifts),
                               first_equals_A=bool(np.array_equal(to8(f0), to8(A))),
                               last_equals_B=bool(np.array_equal(to8(f1), to8(B))))

    # 2. the sign test: a pan in the wrong direction would leave a large shift
    wrong = Pan(A, ca_, B, Cam(cam.yaw + 3 * half_deg, 0.5, cam.v0, ca_.fx_rel, ca_.fy_rel), kind="master")
    fm, _ = wrong.frame(0.5, w, h)
    g, _ = warp(big, cam, lerp_cam(ca_, cb_, 0.5), w, h)
    rep["wrong_direction_mean_abs"] = round(float(np.abs(fm - g).mean() * 255), 2)

    # 3. pose mode: B is a "raw render" that differs from A (+6 % warmer) everywhere; the composite must keep the
    #    master's pixels outside the strip, put the raw render only in the strip, and land exactly on the composite
    Braw = np.clip(B * np.array([1.06, 1.0, 0.94], np.float32), 0, 1)
    pp = Pan(A, ca_, Braw, cb_, kind="pose")
    P, _ = pp.frame(1.0, w, h)
    Aw, caw = warp(A, ca_, cb_, w, h)
    inner = caw > 0.999
    left, right = ca_.hfov_edges()
    az = azimuth_map(cb_, w, h)
    deep = inner & ((az - right) > (pp.seam_frac + pp.seam_inset) * 50 + 0.5)[None, :]
    strip = (caw < 0.01)
    rep["pose_mode"] = dict(
        composite_equals_master_outside_strip_mean_abs=round(float(np.abs(P - Aw)[deep].mean() * 255), 3),
        composite_equals_raw_in_strip_mean_abs=round(float(np.abs(P - Braw)[strip].mean() * 255), 3),
        strip_share_of_frame=round(float(strip.mean()), 3),
        first_equals_A=bool(np.array_equal(to8(pp.frame(0.0, w, h)[0]), to8(A))))
    save(os.path.join(out_dir, "selftest-A.png"), A)
    save(os.path.join(out_dir, "selftest-B-raw.png"), Braw)
    save(os.path.join(out_dir, "selftest-pose-composite.png"), P)

    # 4. a short clip of the pose-mode pan (constant speed, 8 deg/s, 24 fps) for the eye
    tmp = tempfile.mkdtemp(prefix="pan-selftest-")
    try:
        info = render_constant_clip(pp, tmp, w, h, fps=clip_fps, deg_per_s=8.0)
        write_mp4(tmp, clip_fps, os.path.join(out_dir, "selftest-pose-pan.mp4"))
        rep["clip"] = dict(info, file=os.path.join(out_dir, "selftest-pose-pan.mp4"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # 5. vertical overscan removes the pan gap: a 25 deg pan between two virtual stills, plain 16:9 vs 6 % overscan
    big_a = Cam(cam.yaw + 12.5, 0.5, cam.v0, ca_.fx_rel, ca_.fy_rel)
    big_b = Cam(cam.yaw - 12.5, 0.5, cam.v0, ca_.fx_rel, ca_.fy_rel)
    o = 0.03
    ho = int(round(h * (1 + 2 * o)))
    Ao, _ = warp(big, cam, overscan_cam(big_a, o), w, ho)
    Bo, _ = warp(big, cam, overscan_cam(big_b, o), w, ho)
    plain = Pan(crop16(Ao, o), big_a, crop16(Bo, o), big_b)
    over = Pan(Ao, big_a, Bo, big_b, ovs_a=o, ovs_b=o)
    hp = max(plain.frame(x, w, h)[1] for x in (0.25, 0.5, 0.75))
    ho_ = max(over.frame(x, w, h)[1] for x in (0.25, 0.5, 0.75))
    rep["overscan"] = dict(pan_deg=25, overscan_each_side=o, gap_share_plain=round(hp, 5), gap_share_overscan=round(ho_, 5),
                           first_equals_crop=bool(np.array_equal(to8(over.frame(0.0, w, h)[0]), to8(crop16(Ao, o)))))
    rep["ease"] = dict(vmax=round(1 / (1 - 0.15 / 2 - 0.30 / 2), 3), p_at_15=round(ease(0.15), 4), p_at_70=round(ease(0.70), 4),
                       monotonic=bool(all(ease(i / 999) <= ease((i + 1) / 999) for i in range(999))))
    ok = (rep["masters_mode"]["first_equals_A"] and rep["masters_mode"]["last_equals_B"]
          and rep["masters_mode"]["max_shift_px"] < 0.25 and max(e["mean_abs"] for e in errs) < 1.5
          and rep["wrong_direction_mean_abs"] > 5 * max(e["mean_abs"] for e in errs)
          and rep["pose_mode"]["composite_equals_master_outside_strip_mean_abs"] < 0.05
          and rep["pose_mode"]["composite_equals_raw_in_strip_mean_abs"] < 0.05 and rep["pose_mode"]["first_equals_A"]
          and rep["overscan"]["gap_share_plain"] > 0 and rep["overscan"]["gap_share_overscan"] == 0
          and rep["overscan"]["first_equals_crop"])
    rep["pass"] = bool(ok)
    with open(os.path.join(out_dir, "selftest.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    return rep


# ----------------------------------------------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--a", required=True, help="first still (a master)")
        p.add_argument("--a-cam", required=True, help="yaw,u0,v0 of the first still")
        p.add_argument("--b", required=True, help="last still: a master, or a raw pose render with --kind pose")
        p.add_argument("--b-cam", required=True, help="yaw,u0,v0 of the last still")
        p.add_argument("--size", default="1920x1080")
        p.add_argument("--a-overscan", type=float, default=0.0, help="A rendered taller than 16:9: extra height above and below, fraction of the 16:9 height")
        p.add_argument("--b-overscan", type=float, default=0.0)

    p = sub.add_parser("pan", help="render the pan")
    common(p)
    p.add_argument("--kind", choices=["master", "pose"], default="master")
    p.add_argument("--seam-frac", type=float, default=0.04)
    p.add_argument("--clip-dir", help="constant-speed clip frames (0001.png ...)")
    p.add_argument("--clip-fps", type=float, default=24.0)
    p.add_argument("--deg-per-s", type=float, default=8.0, help="render speed of the clip (Bible: up to 8)")
    p.add_argument("--mp4", help="master mp4 of the constant-speed clip (H.264, no audio)")
    p.add_argument("--play-dir", help="playback frames, uniform in progress, for the site export")
    p.add_argument("--play-s", type=float, help="play time of the pan (house-plan / transitions plan)")
    p.add_argument("--play-fps", type=float, default=60.0, help="60 on screen (brief 8.1)")
    p.add_argument("--mobile-dir", help="phone sequence: the moving 3:5 window (648x1080 from a 1920x1080 frame)")
    p.add_argument("--mobile-window", help="c0,c1: centre u of the first and last still's mobile window")
    p.add_argument("--no-blur", action="store_true")
    p.add_argument("--pose-out", help="write the final pose still (the composite with --kind pose) at --size")

    p = sub.add_parser("compose", help="composite pose still: master where it covers, raw render in the strip")
    common(p)
    p.add_argument("--seam-frac", type=float, default=0.04)
    p.add_argument("--out", required=True)

    p = sub.add_parser("check", help="reproject A into B's camera and measure the overlap")
    common(p)
    p.add_argument("--json", help="write the measurements here")
    p.add_argument("--sheet", help="write a visual sheet (A reprojected | B / 50-50 blend | delta E)")

    p = sub.add_parser("register", help="lock a render onto its clay: one global affine (ECC on edges)")
    p.add_argument("--img", required=True, help="the render")
    p.add_argument("--ref", required=True, help="its clay (same camera)")
    p.add_argument("--out", required=True)

    p = sub.add_parser("selftest", help="synthetic test on one still")
    p.add_argument("--src", required=True)
    p.add_argument("--cam", required=True, help="yaw,u0,v0 of the still")
    p.add_argument("--out", required=True)

    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        rep = selftest(a.src, parse_cam(a.cam), a.out)
        print(json.dumps({k: rep[k] for k in ("masters_mode", "wrong_direction_mean_abs", "pose_mode", "overscan", "pass")}, indent=1))
        return 0 if rep["pass"] else 1

    if a.cmd == "register":
        img, M = register(load(a.img), load(a.ref))
        save(a.out, img)
        print(json.dumps(dict(out=a.out, affine=np.round(M, 5).tolist(),
                              shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)],
                              scale=[round(float(M[0, 0]), 5), round(float(M[1, 1]), 5)]), indent=1))
        return 0

    w, h = (int(x) for x in a.size.lower().split("x"))
    A, B = load(a.a), load(a.b)
    ca, cb = parse_cam(a.a_cam), parse_cam(a.b_cam)
    if a.cmd == "check":
        res = overlap_check(A, ca, B, cb, w, h, a.sheet)
        if a.json:
            with open(a.json, "w") as fh:
                json.dump(res, fh, indent=1)
        print(json.dumps(res, indent=1))
        return 0
    if a.cmd == "compose":
        pan = Pan(A, ca, B, cb, kind="pose", seam_frac=a.seam_frac, ovs_a=a.a_overscan, ovs_b=a.b_overscan)
        img, _ = pan.frame(1.0, w, h)
        save(a.out, img)
        return 0

    pan = Pan(A, ca, B, cb, kind=a.kind, seam_frac=a.seam_frac, ovs_a=a.a_overscan, ovs_b=a.b_overscan)
    out = {}
    if a.pose_out:
        img, _ = pan.frame(1.0, w, h)
        save(a.pose_out, img)
    if a.clip_dir:
        out["clip"] = render_constant_clip(pan, a.clip_dir, w, h, a.clip_fps, a.deg_per_s, blur=not a.no_blur)
        if a.mp4:
            write_mp4(a.clip_dir, a.clip_fps, a.mp4)
            out["clip"]["mp4"] = a.mp4
    if a.play_dir:
        if not a.play_s:
            ap.error("--play-dir needs --play-s")
        mw = tuple(float(x) for x in a.mobile_window.split(",")) if a.mobile_window else None
        if a.mobile_dir and not mw:
            ap.error("--mobile-dir needs --mobile-window c0,c1")
        out["playback"] = render_playback(pan, a.play_dir, w, h, a.play_s, a.play_fps, blur=not a.no_blur,
                                          mobile_dir=a.mobile_dir, mobile_window=mw)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
