#!/usr/bin/env python3
"""
hallkit.py: shared helpers for the four hall stills (D0o, HDx, HD, HT), render-agent 2026-11-17. 0 tokens.
- canvases and cameras of each still (site/tools/transitions/camgeo.py conventions)
- the clay passes (id, depth) of each still
- levels in display terms against base.png's back wall (ch. 11.9.1 / 11.9.3 of the designer's proposal)
- line locks: the clay's lines from its id pass, found in an image by registering across-line luminance profiles
  against a reference (the lit input sent to the model), as lock_d0.py of 2026-11-16 does.
"""
from __future__ import annotations

import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
sys.path.insert(0, os.path.join(REPO, "site/tools/transitions"))
import camgeo as cg  # noqa: E402

CLAY = os.path.join(REPO, "assets/blockout/house/framing/wm-door-2026-11-16")
BASE = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png")
D0 = os.path.join(REPO, "assets/renders/hall/warm-modern/door-2026-11-16/d0.png")
BASE_BACK_WALL = 0.751      # base.png back wall, display-decoded linear median (checks_wm_door_final.py)
OVS_X = cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0])

HT_CAM = cg.Cam((3.60, 8.15, 1.20), 90.0, 0.36, 0.48)
CAMS = {"D0o": cg.D0, "HT": HT_CAM, "HD": cg.HD, "HDx": cg.HDX}
CLAY_FRAME = {"D0o": "D0-none", "HT": "HT", "HD": "HD", "HDx": "HDx"}


def canvas(name):
    if name in ("HD", "HDx"):
        return cg.Canvas.tall(2496, 1664, OVS_X)
    return cg.Canvas.base(2720)


def clay_id(name):
    return np.asarray(Image.open(os.path.join(CLAY, CLAY_FRAME[name] + "-id.png")))


def clay_depth(name):
    d, ok = cg.load_depth_png(os.path.join(CLAY, CLAY_FRAME[name] + "-depth.png"))
    return d, ok


def lin_Y(img):
    """img: path or uint8/float RGB array -> display-decoded linear luminance (Rec.709)."""
    if isinstance(img, str):
        a = np.asarray(Image.open(img).convert("RGB")).astype(np.float64) / 255
    else:
        a = np.asarray(img).astype(np.float64)
        if a.max() > 1.5:
            a = a / 255
    l = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return l @ np.array([0.2126, 0.7152, 0.0722])


def lstar(Y):
    f = np.where(Y > 216 / 24389, np.cbrt(Y), (24389 / 27 * Y + 16) / 116)
    return 116 * f - 16


def uvz(name):
    cv = canvas(name)
    U, V = cv.uv()
    d, ok = clay_depth(name)
    P = CAMS[name].unproject(U, V, np.where(ok, d, 1.0))
    return U, V, P[..., 2], ok


def region(name, ids, u0, u1, v0, v1, zband=True, cls=None):
    cls = clay_id(name) if cls is None else cls
    U, V, Z, ok = uvz(name)
    m = np.isin(cls, ids) & (U >= u0) & (U < u1) & (V >= v0) & (V < v1)
    if zband:
        m &= ok & (Z >= 0.80) & (Z <= 1.65)
    return m


# the measurable targets of 11.9.3 (display stops vs base.png back wall)
TARGETS = {
    "D0o": dict(ref=("jib door", (82,), (0.28, 0.36, 0.40, 0.55)), target=-0.60, tol=1 / 6),
    "HT": dict(ref=("jib door", (82,), (0.18, 0.35, 0.29, 0.65)), target=-0.60, tol=1 / 6,
               rel=("stone panel", (94,), (0.48, 0.77, 0.0, 1.0), (-0.6, -0.25))),
    "HD": dict(ref=("jib door", (82,), (0.05, 0.35, 0.16, 0.77)), target=-0.60, tol=1 / 6,
               rel=("stone panel", (94,), (0.55, 0.70, 0.0, 1.0), (-0.6, -0.25))),
    "HDx": dict(ref=("stone panel, left wall", (94,), (0.08, 0.24, 0.0, 1.0)), target=-1.0, tol=1 / 6,
                rel=("living back wall in the opening", (31,), (0.0, 1.0, 0.0, 1.0), None)),
}


def stops(Y, m):
    return math.log2(float(np.median(Y[m])) / BASE_BACK_WALL), int(m.sum())


def levels(name, img, cls=None):
    """Levels of a still (path or array on its canvas) against 11.9.3."""
    Y = lin_Y(img)
    t = TARGETS[name]
    lab, ids, box = t["ref"]
    m = region(name, ids, *box, cls=cls)
    s, n = stops(Y, m)
    out = dict(reference=lab, stops_vs_base=round(s, 3), L_star=round(float(lstar(np.median(Y[m]))), 1), px=n,
               target=t["target"], tol=round(t["tol"], 3), within=bool(abs(s - t["target"]) <= t["tol"] + 1e-9),
               off_by=round(s - t["target"], 3))
    if "rel" in t:
        lab2, ids2, box2, band = t["rel"]
        m2 = region(name, ids2, *box2, zband=(name != "HDx"), cls=cls)
        if m2.sum():
            s2, n2 = stops(Y, m2)
            out["second"] = dict(surface=lab2, stops_vs_base=round(s2, 3), px=n2,
                                 vs_reference=round(s2 - s, 3), band=band,
                                 within=(None if band is None else bool(band[0] <= s2 - s <= band[1])))
    if name == "HDx":
        out["second"]["target"] = "0 +-1/12"
        out["second"]["within"] = bool(abs(out["second"]["stops_vs_base"]) <= 1 / 12)
    return out


def d0_anchor(img):
    """D0's anchor: the door-wall stone in shade (id 84, u 0.45-0.56, v 0.52-0.75), target -0.42 +-1/4."""
    Y = lin_Y(img)
    cls = np.asarray(Image.open(os.path.join(CLAY, "D0-closed-id.png")))
    cv = canvas("D0o")
    U, V = cv.uv()
    m = (cls == 84) & (U >= 0.45) & (U < 0.56) & (V >= 0.52) & (V < 0.75)
    return stops(Y, m)


# ---------------------------------------------------------------------------------------------------------------
# line locks
# ---------------------------------------------------------------------------------------------------------------
def lum(img):
    if isinstance(img, str):
        a = np.asarray(Image.open(img).convert("RGB")).astype(np.float32)
    else:
        a = np.asarray(img).astype(np.float32)
        if a.max() <= 1.5:
            a = a * 255
    return cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.0)


def _shift(pa, pb, maxs):
    da, db = np.abs(np.diff(pa)), np.abs(np.diff(pb))
    n = len(da)
    best, bs_ = -2, 0
    sc = {}
    for s in range(-maxs, maxs + 1):
        a = da[maxs:n - maxs]
        b = db[maxs + s:n - maxs + s]
        a0, b0 = a - a.mean(), b - b.mean()
        den = np.sqrt((a0 * a0).sum() * (b0 * b0).sum()) + 1e-9
        c = float((a0 * b0).sum() / den)
        sc[s] = c
        if c > best:
            best, bs_ = c, s
    if -maxs < bs_ < maxs:
        c0, c1, c2 = sc[bs_ - 1], sc[bs_], sc[bs_ + 1]
        den = c0 - 2 * c1 + c2
        sub = 0.0 if abs(den) < 1e-9 else 0.5 * (c0 - c2) / den
    else:
        sub = 0.0
    return bs_ + max(-0.5, min(0.5, sub)), best


def measure_lines(img, ref, V, Hh, seg=40, box=None):
    """V: name -> (x, y0, y1, half, maxshift); Hh: name -> (y, x0, x1, half, maxshift). Offsets image - ref, px."""
    L, R = lum(img), lum(ref)
    out = {}
    for name, (x, y0, y1, h_, m_) in V.items():
        offs, cs, yc = [], [], []
        for y in range(int(y0), int(y1) - seg + 1, seg):
            pa = R[y:y + seg, x - h_:x + h_ + 1].mean(0)
            pb = L[y:y + seg, x - h_:x + h_ + 1].mean(0)
            if len(pa) < 2 * m_ + 4:
                continue
            s_, c = _shift(pa, pb, m_)
            if c > 0.5:
                offs.append(s_)
                cs.append(c)
                yc.append(y + seg / 2)
        a = np.array(offs) if offs else np.array([np.nan])
        tilt = None
        if len(offs) >= 3:
            k = np.polyfit(np.array(yc), a, 1)[0]
            tilt = round(math.degrees(math.atan(k)), 3)
        out[name] = dict(kind="vertical", clay_px=int(x), median_offset_px=round(float(np.nanmedian(a)), 2),
                         p90_abs_px=round(float(np.nanpercentile(np.abs(a), 90)), 2) if offs else None, n=len(offs),
                         mean_corr=round(float(np.mean(cs)), 3) if cs else None, tilt_deg_vs_clay=tilt)
    for name, (y, x0, x1, h_, m_) in Hh.items():
        offs, cs = [], []
        for x in range(int(x0), int(x1) - seg + 1, seg):
            pa = R[y - h_:y + h_ + 1, x:x + seg].mean(1)
            pb = L[y - h_:y + h_ + 1, x:x + seg].mean(1)
            if len(pa) < 2 * m_ + 4:
                continue
            s_, c = _shift(pa, pb, m_)
            if c > 0.5:
                offs.append(s_)
                cs.append(c)
        a = np.array(offs) if offs else np.array([np.nan])
        out[name] = dict(kind="horizontal", clay_px=int(y), median_offset_px=round(float(np.nanmedian(a)), 2),
                         p90_abs_px=round(float(np.nanpercentile(np.abs(a), 90)), 2) if offs else None, n=len(offs),
                         mean_corr=round(float(np.mean(cs)), 3) if cs else None)
    return out


def runs_1d(arr, target_set):
    """[(start, end_exclusive)] of runs where arr is in target_set."""
    m = np.isin(arr, list(target_set)).astype(np.int8)
    d = np.diff(np.concatenate([[0], m, [0]]))
    s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    return list(zip(s.tolist(), e.tolist()))


def save_rgb(path, arr):
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = np.clip(np.rint(a * 255 if a.max() <= 1.5 else a), 0, 255).astype(np.uint8)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(a).save(path)
