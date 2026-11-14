#!/usr/bin/env python3
"""
camgeo.py: the house-plan camera model with a position, canvases with overscan, and the two reprojections the
transition tools are built on. 0 var2 tokens. (pan_reproject.py keeps its own rotation-only Cam; this module adds
the camera location, non-16:9 canvases and depth.)

Conventions (docs/house-plan.json -> conventions):
  world     metres; X right as the living master camera sees it, Y from the living back wall toward the entrance, Z up
  yaw       degrees, heading from -Y, positive toward -X (a larger yaw is a turn to the LEFT)
            f = (-sin yaw, -cos yaw, 0), r = (cos yaw, -sin yaw, 0); the camera is level (tilt 0, roll 0)
  project   d = f.(P-C), x = r.(P-C);  u = u0 + KU x/d;  v = v0 + KV (Hc - Z)/d   (24 mm, 16:9)
  u, v      fractions of the 16:9 CAMERA FRAME (0 = left / top edge). The shift (u0, v0) is the principal point.
  depth     planar depth d (metres along the optical axis), as the clay depth passes store it

A Canvas is an image that holds the 16:9 camera frame at `box` (x0, y0, x1, y1 in canvas pixels, pixel edges):
  Canvas.frame(1920, 1080)        the frame itself
  Canvas.base()                   the canvas of base.png: 2720 x 1530, frame at [77.49, 43.43, 2642.51, 1486.57]
  Canvas.tall(2496, 1664, 0.0302) a 3:2 still with the frame centred: 3.02 % overscan left and right, 12.84 % above
                                  and below (what the 65 degree turn needs; see turn_door.py)

Reprojections
  rot_map   same centre of projection (a pan, a shift change): exact, no depth needed
  dibr      a different camera position, from one still and its depth: forward splat of the depth with a z-buffer,
            hole filling, then a backward map (cv2.remap) and a disocclusion mask
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import cv2
import numpy as np

KU = 24.0 / 36.0                 # focal / frame width  (house plan: 0.6667)
KV = KU * 16.0 / 9.0             # focal / frame height (1.1852)
BASE_BOX = (77.49, 43.43, 2642.51, 1486.57)   # the 16:9 frame inside the 2720 x 1530 canvas of base.png


# ----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cam:
    loc: tuple          # (X, Y, Z) of the lens; Z = Hc
    yaw: float          # degrees, positive = left
    u0: float
    v0: float

    @property
    def f(self):
        a = math.radians(self.yaw)
        return np.array([-math.sin(a), -math.cos(a), 0.0])

    @property
    def r(self):
        a = math.radians(self.yaw)
        return np.array([math.cos(a), -math.sin(a), 0.0])

    def project(self, P):
        """World points (..., 3) -> u, v, d."""
        P = np.asarray(P, np.float64)
        q = P - np.asarray(self.loc, np.float64)
        d = q @ self.f
        x = q @ self.r
        with np.errstate(divide="ignore", invalid="ignore"):
            u = self.u0 + KU * x / d
            v = self.v0 + KV * (self.loc[2] - P[..., 2]) / d
        return u, v, d

    def unproject(self, u, v, d):
        """Frame coordinates and planar depth -> world points (..., 3)."""
        u, v, d = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64), np.asarray(d, np.float64))
        x = (u - self.u0) / KU * d
        z = self.loc[2] - (v - self.v0) / KV * d
        P = np.asarray(self.loc, np.float64)[None] + d[..., None] * self.f + x[..., None] * self.r
        P = P.reshape(d.shape + (3,))
        P[..., 2] = z
        return P

    def edges_yaw(self, ovs_l: float = 0.0, ovs_r: float = 0.0):
        """World yaw of the left and right edges (of the frame, or of a canvas with that horizontal overscan)."""
        return (self.yaw + math.degrees(math.atan((self.u0 + ovs_l) / KU)),
                self.yaw - math.degrees(math.atan((1 - self.u0 + ovs_r) / KU)))

    def moved(self, loc=None, yaw=None, u0=None, v0=None):
        return replace(self, loc=self.loc if loc is None else tuple(loc), yaw=self.yaw if yaw is None else yaw,
                       u0=self.u0 if u0 is None else u0, v0=self.v0 if v0 is None else v0)


def lerp_cam(a: Cam, b: Cam, s: float) -> Cam:
    la, lb = np.asarray(a.loc, float), np.asarray(b.loc, float)
    return Cam(tuple(la + (lb - la) * s), a.yaw + (b.yaw - a.yaw) * s, a.u0 + (b.u0 - a.u0) * s, a.v0 + (b.v0 - a.v0) * s)


# the cameras of the arrival from the door (docs/proposals/wm-front-door-2026-11-14.md, sections 3.1 and 4.2;
# M0 from docs/house-plan.json). Proposed values (plan entry 1.3.9 pending); the clay wins.
D0 = Cam((7.40, 8.15, 1.20), 90.0, 0.36, 0.48)
HD = Cam((2.462, 8.15, 1.20), 90.0, 0.36, 0.48)
HDX = Cam((2.462, 8.15, 1.20), 25.0, 0.47, 0.50)
M0 = Cam((0.83, 4.64, 1.20), 25.0, 0.47, 0.50)
H0X = Cam((2.877, 9.039, 1.20), 25.0, 0.47, 0.50)


# ----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Canvas:
    w: int
    h: int
    box: tuple          # x0, y0, x1, y1 of the 16:9 camera frame, canvas pixels (edges, may be fractional)

    @staticmethod
    def frame(w: int, h: int | None = None) -> "Canvas":
        h = int(round(w * 9 / 16)) if h is None else h
        return Canvas(w, h, (0.0, 0.0, float(w), float(h)))

    @staticmethod
    def base(w: int = 2720) -> "Canvas":
        k = w / 2720.0
        return Canvas(w, int(round(1530 * k)), tuple(b * k for b in BASE_BOX))

    @staticmethod
    def tall(w: int, h: int, ovs_x: float) -> "Canvas":
        """The frame centred, `ovs_x` of its width outside it on the left and on the right; the rest of the height
        is vertical overscan."""
        fw = w / (1 + 2 * ovs_x)
        fh = fw * 9 / 16
        x0, y0 = (w - fw) / 2, (h - fh) / 2
        return Canvas(w, h, (x0, y0, x0 + fw, y0 + fh))

    @staticmethod
    def overscan(w: int, l: float, r: float, t: float, b: float) -> "Canvas":
        """A canvas `w` wide with overscan given as fractions of the frame (left, right, top, bottom)."""
        fw = w / (1 + l + r)
        fh = fw * 9 / 16
        return Canvas(w, int(round(fh * (1 + t + b))), (l * fw, t * fh, l * fw + fw, t * fh + fh))

    @property
    def fw(self):
        return self.box[2] - self.box[0]

    @property
    def fh(self):
        return self.box[3] - self.box[1]

    @property
    def ovs(self):
        """Overscan as fractions of the frame: left, right, top, bottom."""
        return (self.box[0] / self.fw, (self.w - self.box[2]) / self.fw, self.box[1] / self.fh, (self.h - self.box[3]) / self.fh)

    def scaled(self, w: int) -> "Canvas":
        k = w / self.w
        return Canvas(w, int(round(self.h * k)), tuple(b * k for b in self.box))

    def uv(self):
        """u, v (frame fractions) of every pixel centre: two (h, w) float64 arrays."""
        u = (np.arange(self.w) + 0.5 - self.box[0]) / self.fw
        v = (np.arange(self.h) + 0.5 - self.box[1]) / self.fh
        return np.meshgrid(u, v)

    def px(self, u, v):
        """Frame fractions -> pixel coordinates (for cv2.remap: pixel centres at integers)."""
        return np.asarray(u) * self.fw + self.box[0] - 0.5, np.asarray(v) * self.fh + self.box[1] - 0.5

    def crop_frame(self, img: np.ndarray, w: int | None = None, h: int | None = None) -> np.ndarray:
        """The 16:9 camera frame cut from an image on this canvas, resampled to w x h (area filter when shrinking)."""
        w = int(round(self.fw)) if w is None else w
        h = int(round(w * 9 / 16)) if h is None else h
        M = np.array([[self.fw / w, 0, self.box[0] + 0.5 * self.fw / w - 0.5], [0, self.fh / h, self.box[1] + 0.5 * self.fh / h - 0.5]])
        interp = cv2.INTER_AREA if self.fw > w * 1.05 else cv2.INTER_CUBIC
        return cv2.warpAffine(img, M, (w, h), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)


def rays(cam: Cam, cv: Canvas):
    """Unit-free ray directions of every canvas pixel in world axes: (h, w, 3), with d (the f component) = 1."""
    u, v = cv.uv()
    x = (u - cam.u0) / KU
    z = (cam.v0 - v) / KV
    return x[..., None] * cam.r + z[..., None] * np.array([0.0, 0.0, 1.0]) + cam.f


# ----------------------------------------------------------------------------------------------------------------
# rotation / shift only (same centre of projection)
# ----------------------------------------------------------------------------------------------------------------
def rot_map(src: Cam, scv: Canvas, dst: Cam, dcv: Canvas):
    """For every pixel of the destination canvas, the pixel of the source canvas that shows the same ray.
    Returns map_x, map_y (float32, for cv2.remap) and `front` (the ray points into the source's half space)."""
    D = rays(dst, dcv)
    d = D @ src.f
    x = D @ src.r
    z = D[..., 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        us = src.u0 + KU * x / d
        vs = src.v0 - KV * z / d
    mx, my = scv.px(us, vs)
    front = d > 1e-6
    return mx.astype(np.float32), my.astype(np.float32), front


def inside(mx, my, w, h, margin: float = 0.0):
    return (mx >= margin - 0.5) & (mx <= w - 0.5 - margin) & (my >= margin - 0.5) & (my <= h - 0.5 - margin)


def rot_warp(img, src: Cam, scv: Canvas, dst: Cam, dcv: Canvas, interp=cv2.INTER_CUBIC, margin: float = 1.0):
    """Reproject a still into another view from the same point. Returns (image, coverage bool)."""
    mx, my, front = rot_map(src, scv, dst, dcv)
    out = cv2.remap(img, mx, my, interp, borderMode=cv2.BORDER_REPLICATE)
    return out, front & inside(mx, my, scv.w, scv.h, margin)


# ----------------------------------------------------------------------------------------------------------------
# depth-image-based rendering (a different camera position)
# ----------------------------------------------------------------------------------------------------------------
def _splat_depth(P, dst: Cam, dcv: Canvas, ss: int = 1):
    """Forward-splat world points into the destination view: a z-buffer of planar depth (inf where nothing lands)."""
    u, v, d = dst.project(P.reshape(-1, 3))
    ok = d > 0.02
    px, py = dcv.px(u[ok], v[ok])
    d = d[ok]
    W, H = dcv.w * ss, dcv.h * ss
    ix = np.rint((px + 0.5) * ss - 0.5).astype(np.int64)
    iy = np.rint((py + 0.5) * ss - 0.5).astype(np.int64)
    m = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    idx = iy[m] * W + ix[m]
    z = np.full(W * H, np.inf, np.float64)
    np.minimum.at(z, idx, d[m])
    return z.reshape(H, W)


def _fill_holes(z: np.ndarray, iters: int = 6) -> np.ndarray:
    """Fill the pin-holes of a splatted z-buffer. A hole takes the FARTHEST of its filled neighbours (a hole opens
    where a near surface has moved off a far one, so the background is the right guess), then one min-filter pass
    removes far values that leak through the gaps of a magnified near surface."""
    z = z.copy()
    hole = ~np.isfinite(z)
    k = np.ones((3, 3), np.uint8)
    for _ in range(iters):
        if not hole.any():
            break
        zz = np.where(hole, -np.inf, z).astype(np.float32)
        far = cv2.dilate(zz, k)
        fill = hole & np.isfinite(far) & (far > -1e30)
        z[fill] = far[fill]
        hole = ~np.isfinite(z)
    return z


def dibr(img, depth, src: Cam, scv: Canvas, dst: Cam, dcv: Canvas, interp=cv2.INTER_LINEAR, tol: float = 0.04,
         depth_valid=None):
    """Render the destination view from one still and its planar depth (both on the source canvas).
    Returns (image, valid, depth_dst): `valid` is False where the destination sees something the source does not
    (outside its canvas, or behind a nearer surface: a disocclusion), `depth_dst` is the destination planar depth.
    tol: relative depth disagreement that counts as a disocclusion."""
    us, vs = scv.uv()
    dv = np.isfinite(depth) & (depth > 0)
    if depth_valid is not None:
        dv &= depth_valid
    P = src.unproject(us, vs, np.where(dv, depth, 1.0))
    P = P[dv]
    # splat at 2x the destination density when the source is sparser than the destination, then reduce by min
    z = _splat_depth(P, dst, dcv, ss=1)
    # magnification leaves pin-holes: close them; a near surface magnified over a far one leaks far depth
    # through its gaps: a 3x3 min removes the leaks where the splat was sparse
    filled = np.isfinite(z)
    zmin = cv2.erode(np.where(filled, z, 1e9).astype(np.float32), np.ones((3, 3), np.uint8))
    leak = filled & (z > zmin * (1 + 2 * tol))
    z = np.where(leak, zmin, z)
    z = _fill_holes(z, iters=8)
    zd = z.astype(np.float64)
    ud, vd = dcv.uv()
    known = np.isfinite(zd)
    Pd = dst.unproject(ud, vd, np.where(known, zd, 1.0))
    u2, v2, d2 = src.project(Pd)
    mx, my = scv.px(u2, v2)
    mx = mx.astype(np.float32)
    my = my.astype(np.float32)
    out = cv2.remap(img, mx, my, interp, borderMode=cv2.BORDER_REPLICATE)
    dsrc = cv2.remap(np.where(dv, depth, 1e9).astype(np.float32), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=1e9)
    agree = np.abs(dsrc - d2) <= tol * np.maximum(d2, 0.05) + 0.01
    valid = known & (d2 > 0.02) & inside(mx, my, scv.w, scv.h, 1.0) & agree
    return out, valid, np.where(known, zd, np.nan)


def load_depth_png(path: str, units_per_m: float = 5000.0, sky: int = 65535):
    """A 16-bit clay depth pass (metres = value / units_per_m, `sky` = nothing / beyond range) -> float32 metres, valid."""
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is None or raw.dtype != np.uint16:
        raise SystemExit(f"{path}: expected a 16-bit PNG depth pass")
    if raw.ndim == 3:
        raw = raw[..., 0]
    valid = raw < sky
    return raw.astype(np.float32) / units_per_m, valid


# ----------------------------------------------------------------------------------------------------------------
# the room depth map of the site (assets/renders/<room>/<style>/depth.png): near = bright
# ----------------------------------------------------------------------------------------------------------------
def save_room_depth(path: str, depth: np.ndarray, valid: np.ndarray, meta: dict) -> dict:
    """16-bit grey PNG, near = bright, linear in 1 / depth (what parallax needs):
    value = 1 + 65534 * (1/d - 1/d_far) / (1/d_near - 1/d_far); 0 = no surface (the view out through the glazing).
    A JSON next to it records the mapping and the camera, so that metres can be read back."""
    import json
    import os
    d = depth[valid]
    d_near, d_far = float(d.min()), float(d.max())
    inv = (1.0 / np.maximum(depth, 1e-6) - 1.0 / d_far) / (1.0 / d_near - 1.0 / d_far)
    v = np.where(valid, 1 + np.rint(np.clip(inv, 0, 1) * 65534), 0).astype(np.uint16)
    cv2.imwrite(path, v)
    info = dict(file=os.path.basename(path), size=[int(depth.shape[1]), int(depth.shape[0])],
                encoding="uint16 grey, near = bright, linear in 1/depth: value = 1 + 65534 * (1/d - 1/d_far) / (1/d_near - 1/d_far); "
                         "0 = no surface (the view out through the glazing). d = planar depth along the optical axis, metres.",
                d_near_m=d_near, d_far_m=d_far, **meta)
    with open(os.path.splitext(path)[0] + ".json", "w") as fh:
        json.dump(info, fh, indent=1, ensure_ascii=False)
    return info


def load_room_depth(path: str):
    """depth.png + depth.json -> (planar depth in metres float32, valid bool)."""
    import json
    import os
    info = json.load(open(os.path.splitext(path)[0] + ".json"))
    v = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if v is None or v.dtype != np.uint16:
        raise SystemExit(f"{path}: expected the 16-bit room depth map")
    valid = v > 0
    inv = (v.astype(np.float64) - 1) / 65534.0 * (1.0 / info["d_near_m"] - 1.0 / info["d_far_m"]) + 1.0 / info["d_far_m"]
    return np.where(valid, 1.0 / np.maximum(inv, 1e-9), np.inf).astype(np.float32), valid
