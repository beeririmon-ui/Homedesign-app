#!/usr/bin/env python3
"""
kit.py: shared helpers for the four arrival stills of 2026-11-18 (HT2, HDx2, HC, HC130) and HD's bottom strip, render-agent. 0 tokens.
Builds on hall-2026-11-17/tools/hallkit.py (levels against base.png's back wall, line locks) and site/tools/transitions/camgeo.py.
  - cameras and canvases of each still; the new junction clay (assets/blockout/house/framing/wm-hall-2026-11-18, with the bench and the
    console) and the clay of 2026-11-16 (without them)
  - colour helpers (sRGB / linear / Lab)
  - `reproject`: a still's pixels carried to another camera through the clay depth of both (exact for the bench's planes), with a
    visibility test against the source depth
"""
from __future__ import annotations

import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-17/tools"))
sys.path.insert(0, os.path.join(REPO, "site/tools/transitions"))
import camgeo as cg  # noqa: E402
import hallkit as HK  # noqa: E402

OUT = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-18")
PREV = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-17")
CLAY = os.path.join(REPO, "assets/blockout/house/framing/wm-hall-2026-11-18")
CLAY_OLD = HK.CLAY
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-arrival"
BASE_BACK_WALL = HK.BASE_BACK_WALL
W709 = np.array([0.2126, 0.7152, 0.0722])
HX = (2.462, 8.15, 1.20)

CAMS = dict(HT=HK.HT_CAM, HD=cg.HD, HDx=cg.HDX, HC=cg.Cam(HX, 180.0, 0.50, 0.50), HC130=cg.Cam(HX, 130.0, 0.50, 0.50))
BENCH_ID, CONSOLE_ID = 100, 101


def canvas(name):
    return cg.Canvas.base(2720) if name == "HT" else cg.Canvas.tall(2496, 1664, HK.OVS_X)


# ---- io and colour ------------------------------------------------------------------------------------------------------------------
def rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float64) / 255.0


def rgb8(path):
    return np.asarray(Image.open(path).convert("RGB"))


def save(path, a):
    a = np.asarray(a)
    if a.dtype != np.uint8:
        a = np.clip(np.rint(a * 255.0), 0, 255).astype(np.uint8)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(a).save(path)


def to_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def to_srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_WP = np.array([0.95047, 1.0, 1.08883])


def lab_from_lin(l):
    xyz = l @ _M.T / _WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lin_from_lab(lab):
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * _WP
    return np.clip(xyz @ np.linalg.inv(_M).T, 0, 1)


def lstar(Y):
    return HK.lstar(np.asarray(Y, np.float64))


def stops_of(Y):
    return math.log2(float(Y) / BASE_BACK_WALL)


# ---- clay ---------------------------------------------------------------------------------------------------------------------------
def clay_png(name, kind="", old=False):
    d = CLAY_OLD if old else CLAY
    return os.path.join(d, name + (("-" + kind) if kind else "") + ".png")


def clay_id(name, old=False):
    return np.asarray(Image.open(clay_png(name, "id", old)))


def clay_depth(name, old=False):
    return cg.load_depth_png(clay_png(name, "depth", old))


def world(name, old=False):
    """World points of every canvas pixel of a still, from its clay depth: (h, w, 3) and the valid mask."""
    cv = canvas(name)
    U, V = cv.uv()
    d, ok = clay_depth(name, old)
    P = CAMS[name].unproject(U, V, np.where(ok, d, 1.0))
    return P, ok


def reproject(src_img, src, dst, dst_ids=None, tol=0.02, src_old=False):
    """For every pixel of the destination canvas (optionally only where its clay id is in dst_ids): the source still's pixel that shows the
    same world point, through both clay depths, and whether the source really sees it (its depth agrees within tol x depth).
    Returns (image on the destination canvas, float32 in the source's units; valid mask)."""
    scv, dcv = canvas(src), canvas(dst)
    P, ok = world(dst)
    if dst_ids is not None:
        ok &= np.isin(clay_id(dst), dst_ids)
    us, vs, ds = CAMS[src].project(P)
    mx, my = scv.px(us, vs)
    mx, my = mx.astype(np.float32), my.astype(np.float32)
    sd, sok = clay_depth(src, src_old)
    sdep = cv2.remap(np.where(sok, sd, 1e4).astype(np.float32), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=1e4)
    vis = ok & (ds > 0.05) & HK.cg.inside(mx, my, scv.w, scv.h, 1.0) & (np.abs(sdep - ds) < tol * np.maximum(ds, 0.1))
    img = cv2.remap(np.asarray(src_img, np.float32), mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return img, vis


def rot(src_img, src, dst):
    """Pure rotation (same lens centre): the source still on the destination canvas, and where it is defined."""
    mx, my, front = cg.rot_map(CAMS[src], canvas(src), CAMS[dst], canvas(dst))
    scv = canvas(src)
    ins = front & cg.inside(mx, my, scv.w, scv.h, 1.0)
    img = cv2.remap(np.asarray(src_img, np.float32), mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return img, ins


def u_px(name, u):
    cv = canvas(name)
    return cv.box[0] + u * cv.fw - 0.5


def v_px(name, v):
    cv = canvas(name)
    return cv.box[1] + v * cv.fh - 0.5


def uv_of_px(name, x, y):
    cv = canvas(name)
    return (x + 0.5 - cv.box[0]) / cv.fw, (y + 0.5 - cv.box[1]) / cv.fh


def region_stops(img, m):
    Y = to_lin(img if img.max() <= 1.0 else img / 255.0) @ W709
    med = float(np.median(Y[m]))
    return dict(stops_vs_base=round(stops_of(med), 3), L_star=round(float(lstar(med)), 1), px=int(m.sum()))


def zband(name, lo=0.80, hi=1.65):
    P, ok = world(name)
    return ok & (P[..., 2] >= lo) & (P[..., 2] <= hi)


def uvbox(name, u0, u1, v0, v1):
    U, V = canvas(name).uv()
    return (U >= u0) & (U < u1) & (V >= v0) & (V < v1)


def dump(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    json.dump(obj, open(path, "w"), indent=1, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def feather_alpha(core, band):
    """Alpha 1 on `core`, falling to 0 over `band` px outside it (smoothstep of the distance), 0 beyond: stays inside dilate(core, band)."""
    dist = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
    t = np.clip(1.0 - dist / float(band), 0, 1)
    return t * t * (3 - 2 * t)


def resample_to(img8, w, h):
    if img8.shape[1] == w and img8.shape[0] == h:
        return img8
    interp = cv2.INTER_AREA if img8.shape[1] > w else cv2.INTER_CUBIC
    return cv2.resize(img8, (w, h), interpolation=interp)


def shift_vs(a, b, m=None):
    """Global translation of image b against image a (luminance phase correlation, optionally on a mask): (dx, dy, response)."""
    la = cv2.GaussianBlur((np.asarray(a, np.float32) @ W709.astype(np.float32)), (0, 0), 1.0)
    lb = cv2.GaussianBlur((np.asarray(b, np.float32) @ W709.astype(np.float32)), (0, 0), 1.0)
    if m is not None:
        la, lb = la * m, lb * m
    win = cv2.createHanningWindow(la.shape[::-1], cv2.CV_32F)
    (dx, dy), r = cv2.phaseCorrelate(la, lb, win)
    return float(dx), float(dy), float(r)
