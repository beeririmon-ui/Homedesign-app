#!/usr/bin/env python3
"""
repair_right_wall.py: clip 2 (HDx -> M0), take 1, warm modern: the right edge repaired in code. 0 var2 tokens.

The model drew, from ~1.0 to ~3.1 m, a column it invented on the back wall at the corner (X 2.11-2.50) and, in place
of the living room's right wall (X 2.50), a glass facade into another room. This repaints, frame by frame of the bank,
what the clay has there (docs/house-plan.json: living X -2.3..2.5, Y 0..6.2, h 3.0; O-living-dining in the right wall,
Y 2.97..4.57, Z 0..2.4, reveal X 2.50..2.65; the dining room behind it, painted as a quiet room: plaster, floor,
ceiling, no window, no furniture):

  geometry  every pixel's ray is traced through the analytic room for the bank frame's camera (the walk test's s,
            HDx -> M0, heading 25, registered per frame on the back wall's own floor, skirting and ceiling lines: an
            offset of 2-3 cm, up to 7 cm in the end lock): straight vertical edges, exact parallax. 3 x 3 rays per
            pixel (no edge shimmer).
  painted   the back wall from X 2.02 (ramp to 2.08) to the corner, the right wall with the opening, its far reveal
            and soffit, the dining room seen through it, the ceiling from X 2.05, and the floor under the free-standing
            pillar the model drew 1-1.6 m in front of the back wall, with the shadow it and the glass cast on the floor
            (the clay has that floor flat; the clip had it ~40 % darker): from just after the plank joint at X 1.876, Y <= 3.0,
            fading to 3.3. Everything else, and the clip's own near occluder (the entry reveal, which the
            model drew ~0.1 m off the clay and not rigid: found per frame from its motion), stays the
            clip's.
  light     clay shading at the point (linear luminance of the lit clay stations, per surface, view independent)
            x the clip's colour gain measured on the clean back wall right next to the column (X 1.85-2.02, per
            height; the ceiling per frame), smoothed over frames. The clay gives the right wall facing the windows
            ~13 % above the back wall.
  texture   the clip's own plaster (high-pass ratio, sigma 6 px) from the back wall 0.45 m to the left of the point
            (the right wall: mirrored tiles of that band, in wall coordinates, so the texture moves with the wall);
            the floor patch is the clip's own floor from the two clean planks left of it (one mirrored, so that no
            two neighbours repeat), joints on joints, under the clay's light (its own broad light, shadows
            included, divided out with a floor-only low-pass).

  python3 repair_right_wall.py --bank DIR --walk walk.json --stations DIR --out DIR [--report JSON] [--only 44,60,80]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as asm  # noqa: E402
import camgeo as cg  # noqa: E402

W, H = 1920, 1080
L2 = 3.872
XW, XR = 2.50, 2.65            # right wall: inner face, dining face
YN, YF, ZH = 4.57, 2.97, 2.40  # O-living-dining: near and far jambs, head
ZC = 3.00
XL, XD = -2.30, 7.25           # living left wall, dining far wall
YE0, YE1, XE0, XE1 = 6.20, 6.35, 0.95, 2.15   # O-entry-living (living face, hall face; jambs)
X_BAND, X_CEIL = 2.02, 2.05
X_FLOOR, Y_FLOOR, RAMP_FY, RAMP_FX = 1.892, 3.00, 0.30, 0.004    # the floor patch starts just after the plank joint at 1.876 (the clip's joint stays)
PLANK = 0.2235                  # the clip's planks (measured on the bank, floor coordinates): joints at 1.428 / 1.650 / 1.876 / 2.098
SOFA = ((-1.20, 1.45), (0.0, 1.05), (0.0, 0.85))   # a box around the sofa (M0: u 0.469-0.891): no texture is taken from behind it
RAMP = 0.06
SHIFT_BACK, BAND_TILE = 0.50, 0.40
SS = 3

# labels
KEEP, BACK, RIGHT, REVEAL, SOFFIT, DWALL, DFLOOR, DCEIL, CEIL, FLOOR, ENTRY, NONE, SOFA_L = range(13)
PAINT = (BACK, RIGHT, REVEAL, SOFFIT, DWALL, DFLOOR, DCEIL, CEIL, FLOOR)


def remap1d(img: np.ndarray, mx: np.ndarray, my: np.ndarray, interp=cv2.INTER_LINEAR) -> np.ndarray:
    """cv2.remap at arbitrary points (any shape): the maps go in rows of 1024 (remap needs 2-D maps under 32767)."""
    shp = np.shape(mx)
    mx, my = np.asarray(mx, np.float32).ravel(), np.asarray(my, np.float32).ravel()
    n = mx.size
    if n == 0:
        return np.zeros(shp + img.shape[2:], img.dtype)
    pad = (-n) % 1024
    mx, my = np.pad(mx, (0, pad)), np.pad(my, (0, pad))
    r = cv2.remap(img, mx.reshape(-1, 1024), my.reshape(-1, 1024), interp, borderMode=cv2.BORDER_REPLICATE)
    r = r.reshape((-1,) + img.shape[2:])[:n]
    return r.reshape(shp + img.shape[2:])


def lin(x8):
    x = x8.astype(np.float32) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def cam_at(s: float) -> cg.Cam:
    return cg.lerp_cam(cg.HDX, cg.M0, s / L2)


# ---------------------------------------------------------------------------------------------------------------
def trace(cam: cg.Cam, px: np.ndarray, py: np.ndarray):
    """px, py: pixel coordinates (float, centres at +0.5). Returns label, the hit point (..., 3) and the ramp weight."""
    u, v = px / W, py / H
    xr = (u - cam.u0) / cg.KU
    D = np.stack([cam.f[0] + xr * cam.r[0], cam.f[1] + xr * cam.r[1], -(v - cam.v0) / cg.KV], -1)
    C = np.asarray(cam.loc, np.float64)
    best = np.full(px.shape, np.inf)
    lab = np.full(px.shape, NONE, np.int16)

    def hit(t, ok, L):
        nonlocal best, lab
        m = ok & (t > 1e-3) & (t < best)
        best = np.where(m, t, best)
        lab = np.where(m, L if np.isscalar(L) else L, lab)

    def at(t):
        return C[None] + t[..., None] * D if False else np.stack([C[0] + t * D[..., 0], C[1] + t * D[..., 1], C[2] + t * D[..., 2]], -1)

    with np.errstate(divide="ignore", invalid="ignore"):
        # y = 0: back wall and dining wall
        t = (0.0 - C[1]) / D[..., 1]
        P = at(t)
        okz = (P[..., 2] >= 0) & (P[..., 2] <= ZC)
        hit(t, okz & (P[..., 0] >= XL) & (P[..., 0] <= XW), KEEP + 100)          # back wall, split later by X
        hit(t, okz & (P[..., 0] >= XR) & (P[..., 0] <= XD), DWALL)
        # x = 2.50: right wall with the opening
        t = (XW - C[0]) / D[..., 0]
        P = at(t)
        hole = (P[..., 1] > YF) & (P[..., 1] < YN) & (P[..., 2] < ZH)
        hit(t, (D[..., 0] > 0) & (P[..., 1] >= 0) & (P[..., 1] <= 6.2) & (P[..., 2] >= 0) & (P[..., 2] <= ZC) & ~hole, RIGHT)
        # far reveal face y = 2.97 and soffit z = 2.40
        t = (YF - C[1]) / D[..., 1]
        P = at(t)
        hit(t, (P[..., 0] >= XW) & (P[..., 0] <= XR) & (P[..., 2] >= 0) & (P[..., 2] <= ZH), REVEAL)
        t = (ZH - C[2]) / D[..., 2]
        P = at(t)
        hit(t, (D[..., 2] > 0) & (P[..., 0] >= XW) & (P[..., 0] <= XR) & (P[..., 1] >= YF) & (P[..., 1] <= YN), SOFFIT)
        # ceiling and floor
        for z, Ll, Ld in ((ZC, KEEP + 200, DCEIL), (0.0, KEEP + 300, DFLOOR)):
            t = (z - C[2]) / D[..., 2]
            P = at(t)
            ok = (t > 0) & (P[..., 1] >= 0) & (P[..., 1] <= 6.2)
            hit(t, ok & (P[..., 0] >= XL) & (P[..., 0] < XW), Ll)
            thr = (P[..., 0] >= XW) & (P[..., 0] < XR) & (P[..., 1] > YF) & (P[..., 1] < YN) if z == 0.0 else np.zeros_like(ok)
            hit(t, ok & (((P[..., 0] >= XR) & (P[..., 0] <= XD)) | thr), Ld)
        # the sofa (a box): only so that no texture is taken from behind it
        (sx0, sx1), (sy0, sy1), (sz0, sz1) = SOFA
        for axis, val, (o1, lo1, hi1), (o2, lo2, hi2) in ((1, sy1, (0, sx0, sx1), (2, sz0, sz1)), (0, sx1, (1, sy0, sy1), (2, sz0, sz1)),
                                                         (2, sz1, (0, sx0, sx1), (1, sy0, sy1))):
            t = (val - C[axis]) / D[..., axis]
            P = at(t)
            hit(t, (P[..., o1] >= lo1) & (P[..., o1] <= hi1) & (P[..., o2] >= lo2) & (P[..., o2] <= hi2), SOFA_L)
        # the entry wall, while the camera is in the hall
        if C[1] > YE0:
            for ye in (YE1, YE0):
                t = (ye - C[1]) / D[..., 1]
                P = at(t)
                out = ~((P[..., 0] >= XE0) & (P[..., 0] <= XE1) & (P[..., 2] >= 0) & (P[..., 2] <= ZH))
                hit(t, out, ENTRY)
    P = at(np.where(np.isfinite(best), best, 1.0))
    w = np.zeros(px.shape, np.float32)
    lab = lab.astype(np.int32)
    back = lab == KEEP + 100
    ceil = lab == KEEP + 200
    flo = lab == KEEP + 300
    rb = np.clip((P[..., 0] - X_BAND) / RAMP, 0, 1)
    rc = np.clip((P[..., 0] - X_CEIL) / RAMP, 0, 1)
    rf = np.clip((P[..., 0] - X_FLOOR) / RAMP_FX + 0.5, 0, 1) * np.clip((Y_FLOOR + RAMP_FY - P[..., 1]) / RAMP_FY, 0, 1)
    lab = np.where(back, np.where(rb > 0, BACK, KEEP), lab)
    lab = np.where(ceil, np.where(rc > 0, CEIL, KEEP), lab)
    lab = np.where(flo, np.where(rf > 0, FLOOR, KEEP), lab)
    w = np.where(lab == BACK, rb, np.where(lab == CEIL, rc, np.where(lab == FLOOR, rf, np.isin(lab, PAINT).astype(np.float32))))
    return lab, P, w.astype(np.float32)


# ---------------------------------------------------------------------------------------------------------------
class Shade:
    """Clay shading per surface (linear luminance of the lit clay), from the b stations of the entrance clay."""
    SURF = {
        "back": (lambda P: (np.abs(P[:, 1]) < 0.012) & (P[:, 0] < XW), lambda P: (P[:, 0], P[:, 2]), ((XL, XW), (0, ZC)), 0.05),
        "right": (lambda P: (np.abs(P[:, 0] - XW) < 0.012), lambda P: (P[:, 1], P[:, 2]), ((0, 6.2), (0, ZC)), 0.05),
        "ceil": (lambda P: (np.abs(P[:, 2] - ZC) < 0.012) & (P[:, 0] < XW), lambda P: (P[:, 0], P[:, 1]), ((XL, XW), (0, 6.2)), 0.05),
        "floor": (lambda P: (np.abs(P[:, 2]) < 0.012) & (P[:, 0] < XW), lambda P: (P[:, 0], P[:, 1]), ((XL, XW), (0, 6.2)), 0.05),
        "reveal": (lambda P: (np.abs(P[:, 1] - YF) < 0.012) & (P[:, 0] > XW - 0.01) & (P[:, 0] < XR + 0.01), lambda P: (P[:, 0], P[:, 2]),
                   ((XW, XR), (0, ZH)), 0.01),
    }

    def __init__(self, folder: str, stations=range(2, 12)):
        acc = {k: [] for k in self.SURF}
        for i in stations:
            cam = cg.lerp_cam(cg.H0X, cg.M0, i / 11)
            im = cv2.imread(os.path.join(folder, f"b/S{i:02d}.png"))[..., ::-1]
            depth, valid = cg.load_depth_png(os.path.join(folder, f"b/S{i:02d}-depth.png"))
            h, w = depth.shape
            x0, y0, x1, y1 = cg.Canvas.base(w).box
            gx, gy = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
            P = cam.unproject((gx - x0) / (x1 - x0), (gy - y0) / (y1 - y0), np.where(valid, depth, 1.0))[valid]
            Lm = (lin(im) @ np.array([0.2126, 0.7152, 0.0722], np.float32))[valid]
            for k, (test, co, _, _) in self.SURF.items():
                m = test(P)
                if m.any():
                    a, b = co(P[m])
                    acc[k].append(np.stack([a, b, Lm[m]], 1))
        self.maps = {}
        for k, lst in acc.items():
            A = np.concatenate(lst)
            (a0, a1), (b0, b1) = self.SURF[k][2]
            cell = self.SURF[k][3]
            na, nb = int(math.ceil((a1 - a0) / cell)), int(math.ceil((b1 - b0) / cell))
            ia = np.clip(((A[:, 0] - a0) / cell).astype(int), 0, na - 1)
            ib = np.clip(((A[:, 1] - b0) / cell).astype(int), 0, nb - 1)
            s = np.zeros((nb, na)); n = np.zeros((nb, na))
            np.add.at(s, (ib, ia), A[:, 2]); np.add.at(n, (ib, ia), 1)
            mean = np.where(n > 0, s / np.maximum(n, 1), 0.0)
            # fill the cells no station saw from the nearest seen ones, then smooth lightly
            g = mean.astype(np.float32)
            known = n > 0
            for sig in (1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
                ww = cv2.GaussianBlur(known.astype(np.float32), (0, 0), sig)
                vv = cv2.GaussianBlur(np.where(known, g, 0).astype(np.float32), (0, 0), sig)
                fill = (~known) & (ww > 1e-4)
                g = np.where(fill, vv / np.maximum(ww, 1e-6), g)
                known = known | fill
            ww = cv2.GaussianBlur(np.ones_like(g), (0, 0), 1.5)
            g = cv2.GaussianBlur(g, (0, 0), 1.5) / ww
            self.maps[k] = (g, a0, b0, cell)

    def __call__(self, k: str, a, b):
        g, a0, b0, cell = self.maps[k]
        mx = (np.asarray(a, np.float32) - a0) / cell - 0.5
        my = (np.asarray(b, np.float32) - b0) / cell - 0.5
        return remap1d(g, mx, my)


# ---------------------------------------------------------------------------------------------------------------
def occluder_track(frames: dict, ks: list[int]) -> dict:
    """The clip's near occluder at the right edge (the entry reveal as the model drew it, ~0.1 m off the clay and not
    rigid enough to fit as one line in space): per frame the leftmost column from which everything to the right moves
    faster than 8 px per bank frame; a running median of 5 removes single misses, and it may only move right.
    Returns {k: column} (inf once it has left the frame)."""
    raw = {}
    for k in ks:
        if k + 1 not in frames:
            continue
        f = asm.flow(frames[k][:, 1440:], frames[k + 1][:, 1440:], 1.0)[..., 0]
        col = np.median(f[100:1000], axis=0)
        fast = col > 8.0
        if not fast[-1]:
            raw[k] = float("inf")
            continue
        x = len(col) - 1
        while x > 0 and fast[x - 1]:
            x -= 1
        # the flow carries the jamb's motion into the textureless, overexposed glass left of it: step over any run of
        # mostly blown-out columns (the glass the model drew there) to where the jamb really starts
        lum = frames[k][150:950, 1440:].astype(np.float32).mean(axis=2) / 255.0
        frac = (lum > 0.93).mean(axis=0)
        xr = x
        while xr < len(frac) - 1 and xr < x + 60 and (frac[xr] > 0.3 or frac[min(len(frac) - 1, xr + 1)] > 0.3):
            xr += 1
        raw[k] = 1440.0 + xr
    kk = sorted(raw)
    v = np.array([raw[k] for k in kk])
    med = np.array([np.median(v[max(0, i - 2):i + 3]) for i in range(len(v))])
    med = np.maximum.accumulate(med)
    return dict(raw={k: raw[k] for k in kk}, x={k: float(x) for k, x in zip(kk, med)})


def occluder_x(track: dict, k: int, bias: float = 8.0) -> float:
    """Column from which the clip's own occluder is kept (inf: no occluder). The bias covers the thin wavy dark outline
    the model drew along the reveal's edge, so that the jamb meets the repaired wall on one straight vertical."""
    x = track["x"].get(k)
    if x is None:
        last = max(track["x"]) if track["x"] else None
        return float("inf") if last is None or k > last else track["x"][min(track["x"])] + bias
    return x + bias


# ---------------------------------------------------------------------------------------------------------------
def register(img8: np.ndarray, s: float) -> float:
    """The offset of s (metres) that puts the room's lines where the frame has them: the back wall's floor line, the top
    of its skirting and its ceiling line, left of the repaired band (X -0.5..1.9), scored on the vertical gradient. The
    walk test's s is the clay's best overall fit; at the right edge 2-3 cm matter (and up to 7 cm where the bank's end
    lock has warped the frame toward M0)."""
    g = cv2.cvtColor(img8, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = np.abs(cv2.Sobel(cv2.GaussianBlur(g, (0, 0), 1.0), cv2.CV_32F, 0, 1))
    Xs = np.linspace(-0.5, 1.9, 200)

    def score(c):
        tot = 0.0
        for z in (0.0, 0.15, ZC):
            u, v, d = c.project(np.stack([Xs, np.zeros_like(Xs), np.full_like(Xs, z)], -1))
            x, y = u * W, v * H
            ok = (d > 0) & (x > 2) & (x < W - 3) & (y > 2) & (y < H - 3)
            if ok.sum() > 10:
                tot += float(remap1d(g, x[ok], y[ok]).mean())
        return tot
    offs = np.arange(-0.06, 0.141, 0.004)
    sc = np.array([score(cam_at(s + o)) for o in offs])
    return float(offs[int(np.argmax(sc))])


def tri(x, p):
    m = np.mod(x, 2 * p)
    return np.where(m < p, m, 2 * p - m)


def source_points(lab, P):
    """For each painted surface point, the point of the clip whose plaster / floor / ceiling it takes its texture from."""
    S = P.copy()
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    zero = np.zeros_like(X)
    S = np.where((lab == BACK)[..., None], np.stack([X - SHIFT_BACK, zero, Z], -1), S)
    S = np.where((lab == RIGHT)[..., None], np.stack([X_BAND - 0.02 - tri(Y, BAND_TILE), zero, Z], -1), S)
    S = np.where((lab == REVEAL)[..., None], np.stack([X_BAND - 0.02 - (X - XW) * 2.0, zero, Z], -1), S)
    S = np.where((lab == DWALL)[..., None], np.stack([X_BAND - 0.02 - tri(X - XR, BAND_TILE), zero, Z], -1), S)
    S = np.where((lab == SOFFIT)[..., None], np.stack([X - 0.7, Y, zero + ZC], -1), S)
    S = np.where((lab == DCEIL)[..., None], np.stack([X - 1.4, Y, zero + ZC], -1), S)
    S = np.where((lab == CEIL)[..., None], np.stack([X - 0.5, Y, Z], -1), S)
    S = np.where((lab == DFLOOR)[..., None], np.stack([X - 1.0, Y, zero], -1), S)
    # per plank, from the clean planks 1.650-1.876 and 1.876-2.05 (the ones further left lie in the sofa's shadow): the
    # plank 1.876-2.098 is 1.650-1.876 mirrored (no joint at either end), from 2.092 on it is copied 0.448 to the right,
    # so its joint lands on 2.098 and the next on 2.324: one line per joint
    Xf = np.where(X < 2.092, 3.752 - X, X - 0.448)
    S = np.where((lab == FLOOR)[..., None], np.stack([Xf, np.maximum(Y, 0.03), zero], -1), S)
    return S


def gains(img_lin: np.ndarray, cam: cg.Cam, shade: Shade, xo: float) -> dict:
    """The clip's colour per unit of clay shading on clean surfaces right next to the painted ones: the back wall
    X 1.85-2.02 per 0.1 m of height, and the ceiling X 1.80-2.02."""
    zs = np.arange(0.05, ZC, 0.1)
    Xs = np.linspace(1.85, X_BAND, 6)
    Gw = np.full((len(zs), 3), np.nan)
    for i, z in enumerate(zs):
        P = np.stack([Xs, np.zeros_like(Xs), np.full_like(Xs, z)], -1)
        u, v, d = cam.project(P)
        x, y = u * W, v * H
        ok = (d > 0) & (x >= 3) & (x < min(W - 3, xo - 3)) & (y >= 3) & (y < H - 3)
        if ok.sum() < 3:
            continue
        lab, Ph, _ = trace(cam, x[ok], y[ok])
        good = (lab == KEEP) & (np.abs(Ph[:, 1]) < 0.02)
        if good.sum() < 3:
            continue
        cols = np.array([img_lin[int(yy) - 2:int(yy) + 3, int(xx) - 2:int(xx) + 3].reshape(-1, 3).mean(0) for xx, yy in zip(x[ok][good], y[ok][good])])
        sh = shade("back", Xs[ok][good], np.full(good.sum(), z, np.float32)).ravel()
        Gw[i] = np.median(cols / np.maximum(sh[:, None], 1e-4), axis=0)
    Ys = np.linspace(0.3, 3.0, 10)
    Xc = np.linspace(1.80, X_BAND, 4)
    XX, YY = np.meshgrid(Xc, Ys)
    P = np.stack([XX.ravel(), YY.ravel(), np.full(XX.size, ZC)], -1)
    u, v, d = cam.project(P)
    x, y = u * W, v * H
    ok = (d > 0) & (x >= 3) & (x < min(W - 3, xo - 3)) & (y >= 3) & (y < H - 3)
    Gc = np.full(3, np.nan)
    if ok.sum() >= 4:
        lab, Ph, _ = trace(cam, x[ok], y[ok])
        good = lab == KEEP
        if good.sum() >= 4:
            cols = np.array([img_lin[int(yy) - 2:int(yy) + 3, int(xx) - 2:int(xx) + 3].reshape(-1, 3).mean(0) for xx, yy in zip(x[ok][good], y[ok][good])])
            sh = shade("ceil", P[ok][good][:, 0], P[ok][good][:, 1]).ravel()
            Gc = np.median(cols / np.maximum(sh[:, None], 1e-4), axis=0)
    # the floor: its broad light (floor-only low-pass) per unit of clay shading, on unshadowed floor left of the patch
    blurL = floor_lowpass(img_lin, cam)
    XX, YY = np.meshgrid(np.linspace(1.55, 1.85, 4), np.linspace(1.3, 2.6, 6))
    P = np.stack([XX.ravel(), YY.ravel(), np.zeros(XX.size)], -1)
    u, v, d = cam.project(P)
    x, y = u * W, v * H
    ok = (d > 0) & (x >= 3) & (x < min(W - 3, xo - 3)) & (y >= 3) & (y < H - 3)
    Gf = np.full(3, np.nan)
    if ok.sum() >= 4:
        lab, Ph, _ = trace(cam, x[ok], y[ok])
        good = (lab == KEEP) & (np.abs(Ph[:, 2]) < 1e-6)
        if good.sum() >= 4:
            cols = blurL[y[ok][good].astype(int), x[ok][good].astype(int)]
            sh = shade("floor", P[ok][good][:, 0], P[ok][good][:, 1]).ravel()
            Gf = np.median(cols / np.maximum(sh[:, None], 1e-4), axis=0)
    return dict(zs=zs, wall=Gw, ceil=Gc, floor=Gf)


def floor_lowpass(img_lin: np.ndarray, cam: cg.Cam, sigma: float = 40.0) -> np.ndarray:
    """The broad light of the kept floor: a low-pass of the floor pixels only (no skirting, sofa or wall in it)."""
    step = 4
    gx, gy = np.meshgrid(np.arange(0, W, step) + step / 2, np.arange(0, H, step) + step / 2)
    lab, P, _ = trace(cam, gx, gy)
    m = ((lab == KEEP) & (np.abs(P[..., 2]) < 1e-6)).astype(np.float32)
    small = cv2.resize(img_lin, (gx.shape[1], gx.shape[0]), interpolation=cv2.INTER_AREA)
    s = sigma / step
    num = cv2.GaussianBlur(small * m[..., None], (0, 0), s)
    den = cv2.GaussianBlur(m, (0, 0), s)[..., None]
    lp = np.where(den > 0.05, num / np.maximum(den, 1e-6), small)
    return cv2.resize(lp.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)


def fill_rows(G):
    G = G.copy()
    ok = ~np.isnan(G[:, 0])
    if not ok.any():
        return None
    idx = np.arange(len(G))
    for c in range(G.shape[1]):
        G[:, c] = np.interp(idx, idx[ok], G[ok, c])
    return G


def paint_frame(img8: np.ndarray, cam: cg.Cam, shade: Shade, xo: float, Gw: np.ndarray, Gc: np.ndarray, zs: np.ndarray,
                fade: float = 1.0, Gf: np.ndarray | None = None):
    """Returns the repaired frame (uint8 RGB) and the coverage (float mask) of what was painted."""
    img_lin = lin(img8)
    blur = cv2.GaussianBlur(img_lin, (0, 0), 6.0)
    blurL = floor_lowpass(img_lin, cam)
    xs_probe = []
    for P in [(X_BAND, 0, z) for z in (0.0, 1.5, ZC)] + [(X_CEIL, y, ZC) for y in (0.0, 0.5, 2.0, 4.0)] + \
             [(X_FLOOR, y, 0.0) for y in (0.0, 1.0, Y_FLOOR + RAMP_FY)]:
        u, _, d = cam.project(np.array(P, float))
        if d > 0.05:
            xs_probe.append(u * W)
    x_lo = int(max(0, min(xs_probe) - 8)) if xs_probe else W
    x_hi = W if not math.isfinite(xo) else int(min(W, math.ceil(xo) + 2))
    alpha = np.zeros((H, W), np.float32)
    if x_lo >= x_hi:
        return img8.copy(), alpha
    zw = x_hi - x_lo
    gx = x_lo + (np.arange(zw * SS) + 0.5) / SS
    res = img_lin.copy()
    f32 = lambda q: q.astype(np.float32)
    band = 120                                        # output rows per band
    for r0 in range(0, H, band):
        r1 = min(H, r0 + band)
        gy = r0 + (np.arange((r1 - r0) * SS) + 0.5) / SS
        PX, PY = np.meshgrid(gx, gy)
        lab, P, w = trace(cam, PX, PY)
        w = np.where(PX >= xo, 0.0, w).astype(np.float32) * fade
        paint = np.isin(lab, PAINT) & (w > 0)
        if not paint.any():
            continue
        out = np.zeros(PX.shape + (3,), np.float32)
        Lp, Pp = lab[paint], P[paint]
        Sp = source_points(Lp, Pp)
        su, sv, sd = cam.project(Sp)
        sx, sy = su * W - 0.5, sv * H - 0.5
        lab_s, P_s, _ = trace(cam, sx + 0.5, sy + 0.5)
        valid = (sd > 0) & (sx >= 2) & (sx < min(W - 3, xo - 4)) & (sy >= 2) & (sy < H - 3) & (lab_s == KEEP) & \
                (np.linalg.norm(P_s - Sp, axis=-1) < 0.03)
        src = remap1d(img_lin, sx, sy)
        T = np.clip(src / np.maximum(remap1d(blur, sx, sy), 1e-4), 0.75, 1.3)
        T = np.where(valid[:, None], T, 1.0)
        X, Y, Z = Pp[:, 0], Pp[:, 1], Pp[:, 2]
        iz = np.interp(Z, zs, np.arange(len(zs)))
        Gz = np.stack([np.interp(iz, np.arange(len(zs)), Gw[:, c]) for c in range(3)], -1).astype(np.float32)
        col = np.zeros((len(Lp), 3), np.float32)
        m = Lp == BACK
        col[m] = shade("back", f32(X[m]), f32(Z[m])).reshape(-1, 1) * Gz[m] * T[m]
        m = Lp == RIGHT
        col[m] = shade("right", f32(Y[m]), f32(Z[m])).reshape(-1, 1) * Gz[m] * T[m]
        m = Lp == REVEAL
        col[m] = shade("reveal", f32(X[m]), f32(Z[m])).reshape(-1, 1) * Gz[m] * T[m]
        m = Lp == DWALL
        col[m] = 0.85 * shade("back", np.full(m.sum(), 2.3, np.float32), f32(Z[m])).reshape(-1, 1) * Gz[m] * T[m]
        m = Lp == CEIL
        col[m] = shade("ceil", f32(X[m]), f32(Y[m])).reshape(-1, 1) * Gc[None] * T[m]
        m = Lp == SOFFIT
        col[m] = 0.8 * shade("ceil", np.full(m.sum(), 2.45, np.float32), f32(Y[m])).reshape(-1, 1) * Gc[None] * T[m]
        m = Lp == DCEIL
        col[m] = 0.85 * shade("ceil", np.full(m.sum(), 2.45, np.float32), f32(Y[m])).reshape(-1, 1) * Gc[None] * T[m]
        m = Lp == DFLOOR
        if m.any():
            fb = np.median(src[m & valid], axis=0) if (m & valid).any() else np.array([0.1, 0.07, 0.05], np.float32)
            col[m] = 0.85 * np.where(valid[m][:, None], src[m], fb)
        m = Lp == FLOOR
        if m.any():
            # the source's wood (grain, joints, plank tone) under the light the clay gives the target: the broad light of
            # the source (its shadows: the sofa's, the pillar's) is divided out
            want = shade("floor", f32(X[m]), f32(Y[m])).reshape(-1, 1) * (Gf[None] if Gf is not None else 1.0)
            have = np.maximum(remap1d(blurL, sx[m], sy[m]), 1e-4)       # the floor-only low-pass at the source
            fb = np.median(src[m & valid] / have[valid[m]], axis=0) if (m & valid).any() else np.ones(3, np.float32)
            # the dark contact line where the floor meets the skirting of the back wall and of the right wall
            contact = 1.0 - 0.45 * np.clip(1 - Y[m] / 0.035, 0, 1) - 0.45 * np.clip(1 - (XW - X[m]) / 0.035, 0, 1)
            col[m] = np.where(valid[m][:, None], src[m] / have, fb[None]) * want * np.maximum(contact, 0.4).reshape(-1, 1).astype(np.float32)
        out[paint] = col
        wv = np.where(paint, w, 0.0).astype(np.float32)
        num = cv2.resize(out * wv[..., None], (zw, r1 - r0), interpolation=cv2.INTER_AREA)
        a = cv2.resize(wv, (zw, r1 - r0), interpolation=cv2.INTER_AREA)
        res[r0:r1, x_lo:x_hi] = res[r0:r1, x_lo:x_hi] * (1 - a[..., None]) + num
        alpha[r0:r1, x_lo:x_hi] = a
    return np.clip(np.rint(srgb(res) * 255), 0, 255).astype(np.uint8), alpha


# ---------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bank", required=True, help="assemble.py bank of clip 2 (0001.png ...)")
    ap.add_argument("--walk", required=True, help="the walk test report the bank was made from (its s range)")
    ap.add_argument("--stations", required=True, help="the entrance clay (b/Sxx.png and -depth.png)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--only", help="comma list of bank frames to paint (a test); the rest are not written")
    ap.add_argument("--fade", type=int, default=4, help="frames over which the repair fades out once the column has left the frame")
    a = ap.parse_args(argv)

    names = sorted(f for f in os.listdir(a.bank) if f.endswith(".png") and f[:4].isdigit())
    n = len(names)
    s_tab = asm.monotone(np.asarray(json.load(open(a.walk))["s_filled"], np.float64))
    s0, s1 = float(s_tab[0]), float(s_tab[-1])
    s_of = lambda k: s0 + (k - 1) * (s1 - s0) / (n - 1)
    rd = lambda k: cv2.cvtColor(cv2.imread(os.path.join(a.bank, f"{k:04d}.png")), cv2.COLOR_BGR2RGB)

    # the frames where anything of the repaired band can be in view: from the corner's first appearance to the band's exit
    def band_in_view(k):
        cam = cam_at(s_of(k))
        u, _, d = cam.project(np.array([X_BAND, 0.0, 1.5]))
        uc, _, dc = cam.project(np.array([X_CEIL, 0.3, ZC]))
        return (d > 0 and u < 1.0) or (dc > 0 and uc < 1.0)
    ks = [k for k in range(1, n + 1) if band_in_view(k) and s_of(k) > 0.6]
    # the column's top far corner (back wall X 2.11 at the ceiling) out past the right edge: then fade out
    k_gone = next((k for k in ks if cam_at(s_of(k)).project(np.array([2.11, 0.0, ZC]))[0] >= 1.0), max(ks))
    k_end = min(n - 4, k_gone + a.fade - 1)          # the last frames (M0 itself) stay the bank's own
    ks = [k for k in ks if k <= k_end]
    fade_of = lambda k: float(np.clip(1.0 - (k - k_gone) / a.fade, 0.0, 1.0))
    print(f"repair range: bank {ks[0]}-{ks[-1]} (s {s_of(ks[0]):.2f}-{s_of(ks[-1]):.2f} m)", flush=True)

    shade = Shade(a.stations)
    occ_ks = [k for k in ks if s_of(k) < 1.75]
    occ_frames = {k: rd(k) for k in occ_ks + [occ_ks[-1] + 1]}
    fit = occluder_track(occ_frames, occ_ks)
    del occ_frames
    print("occluder (raw / kept):", " ".join(f"b{k}:{fit['raw'][k]:.0f}/{fit['x'][k]:.0f}" for k in sorted(fit['x'])), flush=True)

    # registration: the offset of s per frame, smoothed over frames (a median of 5, then a gaussian of 3 frames)
    raw_off = np.array([register(rd(k), s_of(k)) for k in ks])
    med = np.array([np.median(raw_off[max(0, i - 2):i + 3]) for i in range(len(ks))])
    ker = np.exp(-0.5 * (np.arange(-6, 7) / 3.0) ** 2)
    off = np.convolve(np.pad(med, 6, mode="edge"), ker / ker.sum(), mode="valid")
    s_reg = {k: s_of(k) + float(o) for k, o in zip(ks, off)}
    print("registration offsets (m), every 8th:", " ".join(f"b{k}:{o:+.3f}" for k, o in list(zip(ks, off))[::8]), flush=True)

    # gains on every frame of the range, then smoothed over frames
    G = {}
    for k in ks:
        cam = cam_at(s_reg[k])
        G[k] = gains(lin(rd(k)), cam, shade, occluder_x(fit, k))
    zs = G[ks[0]]["zs"]
    Gw = np.stack([G[k]["wall"] for k in ks])
    Gc = np.stack([G[k]["ceil"] for k in ks])
    Gf = np.stack([G[k]["floor"] for k in ks])
    for arr in (Gw, Gc, Gf):
        flat = arr.reshape(len(ks), -1)
        for j in range(flat.shape[1]):
            col = flat[:, j]
            ok = ~np.isnan(col)
            if ok.any():
                flat[:, j] = np.interp(np.arange(len(ks)), np.nonzero(ok)[0], col[ok])
        sm = cv2.GaussianBlur(flat.astype(np.float32).reshape(len(ks), -1), (1, 0), sigmaX=0.1, sigmaY=3.0) if False else \
            np.stack([np.convolve(np.pad(flat[:, j], 6, mode="edge"), np.exp(-0.5 * (np.arange(-6, 7) / 3.0) ** 2) /
                                  np.exp(-0.5 * (np.arange(-6, 7) / 3.0) ** 2).sum(), mode="valid") for j in range(flat.shape[1])], 1)
        arr[...] = sm.reshape(arr.shape)

    only = [int(x) for x in a.only.split(",")] if a.only else None
    os.makedirs(a.out, exist_ok=True)
    if not only:
        for f in names:
            shutil.copyfile(os.path.join(a.bank, f), os.path.join(a.out, f))
    rep = dict(range=[ks[0], ks[-1]], s=[round(s_of(ks[0]), 3), round(s_of(ks[-1]), 3)], column_gone=k_gone,
               occluder={str(k): (v if math.isfinite(v) else None) for k, v in fit["x"].items()}, frames={})
    for j, k in enumerate(ks):
        if only and k not in only:
            continue
        cam = cam_at(s_reg[k])
        Gwk = fill_rows(Gw[j])
        if Gwk is None or np.isnan(Gc[j]).any():
            continue
        img = rd(k)
        res, alpha = paint_frame(img, cam, shade, occluder_x(fit, k), Gwk, Gc[j], zs, fade_of(k), None if np.isnan(Gf[j]).any() else Gf[j])
        cv2.imwrite(os.path.join(a.out, f"{k:04d}.png"), cv2.cvtColor(res, cv2.COLOR_RGB2BGR))
        ox = occluder_x(fit, k)
        rep["frames"][k] = dict(s=round(s_of(k), 3), s_registered=round(s_reg[k], 3), painted_px=int((alpha > 0.5).sum()),
                                occluder_x=round(ox, 1) if math.isfinite(ox) else None)
        print(f"b{k} s {s_of(k):.3f} painted {rep['frames'][k]['painted_px']} px", flush=True)
    if a.report:
        with open(a.report, "w") as fh:
            json.dump(rep, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
