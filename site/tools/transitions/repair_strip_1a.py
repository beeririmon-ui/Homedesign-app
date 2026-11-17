#!/usr/bin/env python3
"""
repair_strip_1a.py: clip 1a (D0o + leaf -> HT, kling-3-omni take 1), the living room seen past the walnut edge, repainted
from the real stills through their clay depth, and the door's right jamb replaced by one consistent jamb. 0 var2 tokens.
Briefs: briefs/wm-clip1a-strip-repair-2026-11-17.md (round 1), briefs/wm-clip1a-strip-repair-r2-2026-11-17.md (round 2,
QA C1A-M1, M2, M3), briefs/wm-clip1a-strip-repair-r3-2026-11-17.md (round 3, QA C1A-M4: the bench at the end lock; C1A-L4).

The model drew a plain wall where the living room shows through O-entry-living (right of the walnut lining), its right door
jamb changes look in every frame from 120 to 125 (and carries a black contour line), and the end lock melted the wall into
HT's north window with the birches (bank frames 130-141). From bank frame 122 (the first frame in which the clay sees the
living room past the walnut lining, Y < 6.20) every frame gets:

  the stills   every pixel of the living room is looked up from the stills BACKWARD, through the clay depth of that very
               frame (the clay depth pass at the bank camera): the world point of the pixel is projected into each still,
               and the still is used only where its own clay depth sees that point (no splat, so nothing is stretched across
               a depth jump: round 2, C1A-M2). Order: HT (its 16:9 frame only, HT-L2), HDx, base.png; 6 px feathers where
               a later still meets an earlier one.
  the window   the glass is carried on the plane of the window frame of W-living (X = -2.65, the clay's frame face), the
               same plane in every view; the glass takes HT, then base.png, never HDx. HT's right frame edge lies on the
               mullion, so HT gives the left pane and base.png the right pane, and the seam sits on the mullion, outside
               the glass (round 2, C1A-M3).
  the armchair the clay has no living-room furniture; base.png's room depth has the walnut armchair (CHAIR_BOX): its points are
               splatted forward (direct hits only, no hole filling) where they lie in front of the clay, and HDx gives nothing
               it sees through that box (it would show the armchair as a decal on the floor). HT is not cut by the box: its
               16:9 frame has no armchair, and everything frame 143 shows comes from HT (round 3, C1A-M4).
  the plate    what no still sees outside HT's frame (the top right ceiling corner, bits of floor by the armchair) is
               painted ONCE, at bank frame 130: first the same clay plane further along the window wall (+Y: the ceiling,
               the soffit and the boards do not change along it, so the soffit's edge runs on), then an inpaint that stays
               inside each clay plane; every other frame looks that plate up through the clay depth like a still: it moves
               with the room and cannot flicker (round 2, C1A-M2). HDx gives no ceiling (its render of it is darker).
  behind the lining  a pixel HT cannot see because the walnut lining hides it from HT (within 120 px of the lining) keeps
               the clip (24 px ramp); past the paint's coverage the clip, never black.
  the jamb     the clip's jamb as it drew it at bank frame 125 (its contour line cut off), one texture for every frame from
               122, mapped as the plane of the reveal under the forward walk (a 1-D homography about the focus of
               expansion), its edge moving at a constant acceleration from the clip's own edge and speed at 122 to out of
               the frame at 131 (the clay's jamb is out at ~130), with an edge blur of 0.15 of its speed (round 2,
               C1A-M1: the clip's black line at 123-124 lies under it, and no frame has the model's changing jamb); it starts at
               the tone of the model's jamb in the frame before and reaches its own over five frames (round 3, C1A-L4). What the
               clay's jamb still covers left of the new edge (122-127) is HT splatted forward (it is past the jamb).
  register     the paint moves with the clip's own walnut edge (dark-to-bright step, sub-pixel, per frame, lightly smoothed),
               so the border is the clip's line.
  the end      frame 143 is HT itself (the end lock) and is not touched.

  python3 repair_strip_1a.py --bank DIR --clay DIR --out DIR --report repair.json
  python3 repair_strip_1a.py check --bank DIR --before DIR --repair repair.json --clay DIR --out selfcheck.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
HALL = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-17")
CLAY_DOOR = os.path.join(REPO, "assets/blockout/house/framing/wm-door-2026-11-16")
LIV = os.path.join(REPO, "assets/renders/living-room/warm-modern")
W, H = 1920, 1080
L1A, N = 3.80, 143
Y_CUT = 6.20            # HT shows the whole reveal of O-entry-living (Y 6.20-6.35) in walnut: past it, the living room
XG = -2.65              # the frame face of W-living's glazing (clay: X -2.650 +- 0.003 on the panes it fits cleanly)
TOL = 0.04
FEATHER = 1.5
SEAM = 6.0
OVS = cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0])
CX, CY = 0.36 * W, 0.48 * H     # the bank cameras' principal point = the focus of expansion of the walk (-X along f)
JAMB_SRC = 125          # the clip's jamb as drawn at this bank frame (lit face + shaded face, a straight contour line)
JAMB_NEAR = 1.5         # clay depth (m) below which a pixel right of the walnut is the door jamb
PLATE_K = 130           # the first frame in which the clay's jamb is out of the frame


def cam_at(k: int) -> cg.Cam:
    s = L1A * (k - 1) / (N - 1)
    return cg.D0.moved(loc=(cg.D0.loc[0] - s, cg.D0.loc[1], cg.D0.loc[2]))


def rgb(p):
    return cv2.cvtColor(cv2.imread(p, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def to8(a):
    return np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)


def lstar_bgr(bgr8):
    return cv2.cvtColor(bgr8, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * (100.0 / 255.0)


def shift_x(a: np.ndarray, dx: float) -> np.ndarray:
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    return cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def left_border(mask: np.ndarray) -> np.ndarray:
    """Per row, the first mask column (nan where the row has none)."""
    has = mask.any(axis=1)
    x = np.argmax(mask, axis=1).astype(np.float64)
    return np.where(has, x, np.nan)


def walnut_edge(img8_gray: np.ndarray) -> float:
    """The clip's walnut band (the darkest 30 px band in x 1300-1720, rows 200-800) and its right edge (the largest rise),
    sub-pixel (a parabola through the rise and its neighbours). Returns the index j of the step between columns j and j+1."""
    g = cv2.GaussianBlur(img8_gray.astype(np.float32), (0, 0), 1.2)
    prof = g[200:800, :].mean(axis=0)
    band = np.convolve(prof, np.ones(30) / 30, mode="same")
    wl = 1300 + int(np.argmin(band[1300:1720]))
    d = np.diff(prof[wl:wl + 80])
    j = int(np.argmax(d))
    dl = d[j - 1] if j > 0 else d[j]
    dr = d[j + 1] if j + 1 < len(d) else d[j]
    den = dl - 2 * d[j] + dr
    off = 0.5 * (dl - dr) / den if abs(den) > 1e-6 else 0.0
    return wl + j + float(np.clip(off, -0.5, 0.5))


def reveal_edge(img8_gray: np.ndarray, wr: float) -> int:
    """The clip's right door jamb (a near face entering from the right): its left edge, the largest fall of the column
    profile right of the walnut edge + 40 px."""
    g = cv2.GaussianBlur(img8_gray.astype(np.float32), (0, 0), 1.2)
    prof = g[200:800, :].mean(axis=0)
    a = int(wr) + 40
    p2 = cv2.GaussianBlur(prof[a:1916].reshape(1, -1), (0, 0), 2).ravel()
    return a + int(np.argmin(np.diff(p2)))


def dark_lines(L: np.ndarray, lo: int, hi: int, rows=(40, 1040), drop: float = 15.0, half: int = 4):
    """Narrow dark vertical lines, measured on the frame itself: per column, the rows in which L* lies `drop` below BOTH
    columns `half` px to the left and to the right. Returns (x of the column with most such rows, its row count, the per-
    column counts over [lo, hi))."""
    Lr = L[rows[0]:rows[1]]
    r = np.minimum(np.roll(Lr, half, axis=1), np.roll(Lr, -half, axis=1)) - Lr
    cnt = (r > drop).sum(axis=0)
    cnt[:lo] = 0
    cnt[hi:] = 0
    x = int(np.argmax(cnt))
    return x, int(cnt[x]), cnt


# ----------------------------------------------------------------------------------------------------------------
# geometry
# ----------------------------------------------------------------------------------------------------------------
def glass_hit(cam: cg.Cam, cv: cg.Canvas):
    """Planar depth of every pixel's ray on the glazing plane X = XG, and where that hit lies in the living room's window
    wall (Y 0-6.2, Z 0.3-2.9, in front of the camera)."""
    us, vs = cv.uv()
    f, r = cam.f, cam.r
    den = f[0] + (us - cam.u0) / cg.KU * r[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        d = (XG - cam.loc[0]) / den
    good = np.isfinite(d) & (d > 0.05)
    P = cam.unproject(us, vs, np.where(good, d, 1.0))
    ok = good & (P[..., 1] > 0.0) & (P[..., 1] < 6.2) & (P[..., 2] > 0.3) & (P[..., 2] < 2.9)
    return np.where(ok, d, 0).astype(np.float32), ok


def sources():
    """The stills, each with its clay depth; the clay has nothing behind the glass: there, the glazing plane."""
    out = []
    ht = rgb(os.path.join(HALL, "ht.png"))
    cvb = cg.Canvas(ht.shape[1], ht.shape[0], cg.Canvas.base(ht.shape[1]).box)
    d, v = cg.load_depth_png(os.path.join(CLAY_DOOR, "HT-depth.png"))
    gd, gok = glass_hit(cg.HT, cvb)
    g = ~v & gok
    d = np.where(g, gd, d).astype(np.float32)
    v = v | g
    x0, y0, x1, y1 = cvb.box
    v[:, :int(np.ceil(x0))] = False                     # HT-L2: only the 16:9 frame of HT is read
    v[:, int(np.floor(x1)):] = False
    out.append(dict(name="HT", cam=cg.HT, cv=cvb, img=ht, depth=d, valid=v))
    hdx = rgb(os.path.join(HALL, "hdx.png"))
    cvt = cg.Canvas.tall(hdx.shape[1], hdx.shape[0], OVS)
    d, v = cg.load_depth_png(os.path.join(CLAY_DOOR, "HDx-depth.png"))
    out.append(dict(name="HDx", cam=cg.HDX, cv=cvt, img=hdx, depth=d, valid=v))      # no glass from HDx
    base = rgb(os.path.join(LIV, "phase2-2026-11-10/layers/base.png"))
    cvm = cg.Canvas(base.shape[1], base.shape[0], cg.Canvas.base(base.shape[1]).box)
    d, v = cg.load_room_depth(os.path.join(LIV, "depth.png"))
    if d.shape != base.shape[:2]:
        d = cv2.resize(d, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST)
        v = cv2.resize(v.astype(np.uint8), (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    gd, gok = glass_hit(cg.M0, cvm)
    g = ~v & gok
    d = np.where(v, d, np.where(g, gd, 0)).astype(np.float32)
    v = v | g
    out.append(dict(name="base.png", cam=cg.M0, cv=cvm, img=base, depth=d, valid=v))
    return out


def target(clay_dir: str, k: int) -> dict:
    """The clay at bank camera k: planar depth (glass on the glazing plane), world points, the living room mask."""
    cam = cam_at(k)
    fr = cg.Canvas.frame(W, H)
    d, v = cg.load_depth_png(os.path.join(clay_dir, f"k{k:03d}-depth.png"))
    gd, gok = glass_hit(cam, fr)
    g = ~v & gok
    d = np.where(v, d, np.where(g, gd, 0)).astype(np.float32)
    v = v | g
    us, vs = fr.uv()
    P = cam.unproject(us, vs, np.where(v, d, 1.0))
    m = v & (P[..., 1] < Y_CUT)
    return dict(k=k, cam=cam, fr=fr, d=d, v=v, glass=g, P=P, m=m)


def clay_mask(clay_dir: str, k: int, cam: cg.Cam | None = None) -> np.ndarray:
    return target(clay_dir, k)["m"]


def backward(st: dict, P: np.ndarray, sel: np.ndarray, tol: float = TOL):
    """Look a still up at world points P. Returns (image, ok, occluded): ok where the still's own clay depth sees that
    very point and no nearer surface lies within 2 px of it in the still (so no colour of an occluding edge is sampled:
    nothing across a depth jump); occluded where the still sees something nearer there."""
    u2, v2, d2 = st["cam"].project(P)
    mx, my = st["cv"].px(u2, v2)
    mx = np.nan_to_num(mx, nan=-1e4).astype(np.float32)
    my = np.nan_to_num(my, nan=-1e4).astype(np.float32)
    im = cv2.remap(st["img"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    dsv = np.where(st["valid"], st["depth"], 0).astype(np.float32)
    ds = cv2.remap(dsv, mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if "dmin" not in st:
        st["dmin"] = cv2.erode(np.where(st["valid"], st["depth"], 1e4).astype(np.float32), np.ones((5, 5), np.uint8))
    dm = cv2.remap(st["dmin"], mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=1e4)
    inside = cg.inside(mx, my, st["cv"].w, st["cv"].h, 1.0) & (d2 > 0.05)
    agree = np.abs(ds - d2) <= tol * d2 + 0.01
    occ = inside & (ds > 0) & ((ds < d2 * (1 - tol) - 0.01) | (dm < d2 * 0.9 - 0.01))
    ok = sel & inside & agree & ~occ
    return im, ok, occ & sel


def in_frame_of(st: dict, P: np.ndarray, margin_px: float = 0.0) -> np.ndarray:
    """Whether world points fall inside a still's 16:9 frame (seen or hidden), `margin_px` inside its edges."""
    u2, v2, d2 = st["cam"].project(P)
    mu, mv = margin_px / st["cv"].fw, margin_px / st["cv"].fh
    return (d2 > 0.05) & (u2 >= mu) & (u2 < 1 - mu) & (v2 >= mv) & (v2 < 1 - mv)


# the walnut armchair by W-living (base.png's room depth: X -1.78..-0.76, Y 2.26..3.24, Z to 0.68), with a margin. The clay has
# no living-room furniture: a still whose ray to a clay point crosses this box may show the armchair there, not the point.
CHAIR_BOX = (np.array([-1.85, 2.20, 0.0]), np.array([-0.70, 3.30, 0.75]))


def ray_crosses_box(C, P: np.ndarray, box=CHAIR_BOX) -> np.ndarray:
    """Whether the segment from C to each world point P passes through the box before reaching P."""
    C = np.asarray(C, np.float64)
    D = P - C
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (box[0] - C) / D
        t2 = (box[1] - C) / D
    t1 = np.where(np.abs(D) < 1e-12, np.where((C >= box[0]) & (C <= box[1]), -np.inf, np.inf), t1)
    t2 = np.where(np.abs(D) < 1e-12, np.where((C >= box[0]) & (C <= box[1]), np.inf, -np.inf), t2)
    tmin = np.max(np.minimum(t1, t2), axis=-1)
    tmax = np.min(np.maximum(t1, t2), axis=-1)
    return (tmax >= np.maximum(tmin, 0)) & (tmin < 0.995)


def forward_direct(st: dict, cam: cg.Cam, fr: cg.Canvas):
    """A still splatted forward (cg.dibr), kept only where a source point landed (a 1 px closing for pin-holes): no hole
    filling, so nothing stretched. Returns (image, ok, planar depth)."""
    us, vs = st["cv"].uv()
    dv = np.isfinite(st["depth"]) & (st["depth"] > 0) & st["valid"]
    Pw = st["cam"].unproject(us, vs, np.where(dv, st["depth"], 1.0))[dv]
    z = cg._splat_depth(Pw, cam, fr, ss=1)
    hit = cv2.morphologyEx(np.isfinite(z).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    im, ok, dd = cg.dibr(st["img"], st["depth"], st["cam"], st["cv"], cam, fr, depth_valid=st["valid"])
    return im, ok & hit, dd


def segments(P: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The clay's planes: pixels grouped by the dominant axis and sign of their normal and their offset along it (a step of
    > 3 cm or a change of axis is a border). 0 = border / no surface."""
    gx = np.gradient(P, axis=1)
    gy = np.gradient(P, axis=0)
    n = np.cross(gx, gy)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    ax = np.argmax(np.abs(n), axis=-1)
    sg = np.take_along_axis(n, ax[..., None], -1)[..., 0] > 0
    cls = (ax * 2 + sg).astype(np.int32)
    off = np.take_along_axis(P, ax[..., None], -1)[..., 0]
    edge = ~v.copy()
    for sh in ((0, 1), (1, 0)):
        c2 = np.roll(cls, sh, axis=(0, 1))
        o2 = np.roll(off, sh, axis=(0, 1))
        e = (c2 != cls) | (np.abs(o2 - off) > 0.03)
        edge |= e
        edge |= np.roll(e, (-sh[0], -sh[1]), axis=(0, 1))
    n_, lab = cv2.connectedComponents((~edge).astype(np.uint8), connectivity=4)
    return lab.astype(np.int32)


def extrude_fill(paint: np.ndarray, cov: np.ndarray, hole: np.ndarray, tg: dict, lab: np.ndarray, step: float = 0.02,
                 max_dy: float = 2.5):
    """Fill holes from the same clay plane further along +Y (the room's surfaces by W-living - the ceiling, the soffit along
    the window wall, the wall above the window, the floor boards - do not change along the window wall): for each hole
    point, the nearest point P + (0, dY, 0) that this frame paints on the same plane gives its colour. Returns (image,
    filled)."""
    ys, xs = np.nonzero(hole)
    out = paint.copy()
    filled = np.zeros_like(hole)
    if not len(ys):
        return out, filled
    Ph = tg["P"][ys, xs]
    lh = lab[ys, xs]
    cove = cv2.erode(cov.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    done = lh == 0
    got = np.zeros(len(ys), bool)
    for dy in np.arange(step, max_dy, step):
        idx = np.nonzero(~done)[0]
        if not len(idx):
            break
        Q = Ph[idx] + np.array([0.0, dy, 0.0])
        u, v, d = tg["cam"].project(Q)
        mx, my = tg["fr"].px(u, v)
        ix = np.clip(np.rint(mx).astype(np.int64), 0, W - 1)
        iy = np.clip(np.rint(my).astype(np.int64), 0, H - 1)
        ok = (mx >= 1) & (mx <= W - 2) & (my >= 1) & (my <= H - 2) & (d > 0.05)
        ok &= cove[iy, ix] & (lab[iy, ix] == lh[idx]) & (np.abs(tg["d"][iy, ix] - d) <= 0.03 * d + 0.01)
        sel = idx[ok]
        if len(sel):
            col = cv2.remap(paint, mx[ok].astype(np.float32).reshape(-1, 1), my[ok].astype(np.float32).reshape(-1, 1), cv2.INTER_LINEAR)
            out[ys[sel], xs[sel]] = col.reshape(-1, 3)
            done[sel] = True
            got[sel] = True
    filled[ys[got], xs[got]] = True
    return out, filled


def seg_inpaint(img: np.ndarray, known: np.ndarray, hole: np.ndarray, lab: np.ndarray) -> tuple[np.ndarray, int]:
    """Fill `hole` plane by plane: each clay plane only from its own known pixels (so the borders between planes stay the
    clay's); what is left (plane borders, planes with nothing known) from all known pixels. Returns (image, px filled by
    the general pass)."""
    out = img.copy()
    o8 = to8(out)
    todo = hole.copy()
    for s in np.unique(lab[hole]):
        if s == 0:
            continue
        seg = lab == s
        h_ = hole & seg
        k_ = known & seg
        if k_.sum() < 20:
            continue
        ys, xs = np.nonzero(h_)
        y0, y1, x0, x1 = max(ys.min() - 80, 0), min(ys.max() + 81, H), max(xs.min() - 80, 0), min(xs.max() + 81, W)
        if k_[y0:y1, x0:x1].sum() < 20:
            continue
        sub = o8[y0:y1, x0:x1].copy()
        msk = (~k_[y0:y1, x0:x1]).astype(np.uint8) * 255
        f = cv2.inpaint(sub, msk, 6, cv2.INPAINT_TELEA)
        hh = h_[y0:y1, x0:x1]
        sub[hh] = f[hh]
        o8[y0:y1, x0:x1] = sub
        todo &= ~h_
    rest = int(todo.sum())
    if rest:
        f = cv2.inpaint(o8, (todo | ~(known | hole)).astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA)
        o8[todo] = f[todo]
    out = o8.astype(np.float32) / 255.0
    sm = cv2.GaussianBlur(out, (0, 0), 1.5)                  # the inpaint's own texture (dots, streaks) smoothed: these are plain planes
    out[hole] = sm[hole]
    return out, rest


# ----------------------------------------------------------------------------------------------------------------
# the jamb
# ----------------------------------------------------------------------------------------------------------------
class Jamb:
    """The clip's jamb at JAMB_SRC, its face from `e_src` (right of the contour line), placed with its edge at x_j: the
    plane of the reveal seen from a camera walking along its optical axis maps by 1/(x - CX) -> 1/(x - CX) + c (and y about
    CY by the same local scale). Past the source frame's right edge the shaded face goes on: its last 80 columns mirrored
    back and forth (round 3, C1A-L4: a plain mirror at the frame edge brought the lit face back as a bright band at 122)."""

    def __init__(self, img: np.ndarray, e_src: float, tail: int = 80, ext: int = 640):
        t = img[:, W - tail:W]
        reps = [t[:, ::-1] if i % 2 == 0 else t for i in range(int(np.ceil(ext / tail)))]
        self.img = np.ascontiguousarray(np.concatenate([img[:, :W]] + reps, axis=1))
        self.e = float(e_src)
        X, Y = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
        self.X, self.Y = X, Y

    def render(self, xj: float, w: float):
        c = 1.0 / (self.e - CX) - 1.0 / (xj - CX)
        Xs = np.maximum(self.X, xj)
        inv = 1.0 / (Xs - CX) + c
        xs = CX + 1.0 / inv
        lam = (Xs - CX) / (xs - CX)
        ys = CY + (self.Y - CY) / lam
        out = cv2.remap(self.img, xs.astype(np.float32), ys.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        assert float(xs.max()) < self.img.shape[1] - 2, "the jamb's face is extended too little"
        a = np.clip((self.X - xj) / max(w, 1.0) + 0.5, 0, 1).astype(np.float32)
        return out, a


def jamb_path(x0: float, v0: float, k0: int, k1: int, x_out: float = W + 40.0) -> dict:
    """Edge positions: x0 at k0 with speed v0, a constant acceleration to x_out at k1."""
    T = k1 - k0
    acc = 2 * (x_out - x0 - v0 * T) / (T * T)
    return {k: x0 + v0 * (k - k0) + 0.5 * acc * (k - k0) ** 2 for k in range(k0, k1 + 1)}, acc


# ----------------------------------------------------------------------------------------------------------------
def paint_stills(tg: dict, src: list, sel: np.ndarray):
    """The stills looked up backward over `sel`, in order, SEAM px feathers inside the earlier coverage. HDx gives neither
    the glass nor the ceiling (its ceiling is a darker, textured render of the same plaster: a seam against HT's), nor anything it
    sees through the armchair's box. HT is not cut by the box: its 16:9 frame has no armchair (QA HT-M2), and cutting it took
    the bench and the bottom of the window from base.png until the end lock (round 3, C1A-M4). Returns (image, covered,
    who 1..n, HT occluded)."""
    out = np.zeros((H, W, 3), np.float32)
    cov = np.zeros((H, W), bool)
    who = np.zeros((H, W), np.uint8)
    occ_ht = np.zeros((H, W), bool)
    for i, st in enumerate(src):
        s = sel
        if st["name"] == "HDx":
            s = s & ~tg["glass"] & (tg["P"][..., 2] < 2.55)
        if st["name"] == "HDx":
            s = s & ~ray_crosses_box(st["cam"].loc, tg["P"])       # HDx shows the armchair; HT's 16:9 frame has none (HT-M2)
        im, ok, occ = backward(st, tg["P"], s)
        if st["name"] == "HT":
            occ_ht = occ
        if not ok.any():
            continue
        new = ok & ~cov
        if cov.any():
            inside = cv2.distanceTransform(cov.astype(np.uint8), cv2.DIST_L2, 3)
            wa = np.clip(inside / SEAM, 0, 1)[..., None]
            both = (ok & cov)[..., None]
            out = np.where(both, wa * out + (1 - wa) * im, out)
        out[new] = im[new]
        who[new] = i + 1
        cov |= ok
    return out, cov, who, occ_ht


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bank", required=True)
    ap.add_argument("--clay", required=True, help="clay depth passes at the bank cameras, k%%03d-depth.png (1920 x 1080 frame)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--debug", help="a scratch folder for the plate image")
    ap.add_argument("--jamb", default="122,131", help="the new jamb from this frame (the clip's edge and speed there) until out of the frame at the second")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    names = sorted(f for f in os.listdir(a.bank) if f.endswith(".png") and f[:4].isdigit())
    assert len(names) == N, f"{a.bank}: {len(names)} frames, expected {N}"
    src = sources()
    ht = src[0]
    base_st = src[2]
    us_, vs_ = base_st["cv"].uv()
    Pb = base_st["cam"].unproject(us_, vs_, np.where(base_st["valid"], base_st["depth"], 1.0))
    inbox = np.all((Pb >= CHAIR_BOX[0]) & (Pb <= CHAIR_BOX[1]), axis=-1) & (Pb[..., 2] > 0.03)
    chair_st = dict(base_st, valid=base_st["valid"] & inbox)
    chair_st.pop("dmin", None)
    kj0, kj1 = (int(x) for x in a.jamb.split(","))

    # the frames with living room past the walnut, and the registration to the clip's walnut edge
    tgs = {}
    for k in range(100, N):
        tg = target(a.clay, k)
        if tg["m"].sum() > 50:
            tgs[k] = tg
    ks = sorted(tgs)
    k0 = ks[0]
    gray = {k: cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[k - 1])), cv2.COLOR_BGR2GRAY) for k in range(k0 - 3, N + 1)}
    wr = {k: walnut_edge(gray[k]) for k in ks}
    border = {k: float(np.nanmean(left_border(tgs[k]["m"])[200:800])) for k in ks}
    dx_raw = {k: wr[k] + 0.5 - border[k] for k in ks}
    dx = {}
    for k in ks:
        if k in (ks[0], ks[-1]):
            dx[k] = dx_raw[k]
        else:
            dx[k] = 0.25 * dx_raw[k - 1] + 0.5 * dx_raw[k] + 0.25 * dx_raw[k + 1]
    # the clip's jamb: its edge (largest fall) and its black contour line (measured on the frame), per frame
    rv = {k: reveal_edge(gray[k], wr.get(k, walnut_edge(gray[k]))) for k in range(k0 - 2, kj1 + 1)}
    Lb = {k: lstar_bgr(cv2.imread(os.path.join(a.bank, names[k - 1]))) for k in range(k0 - 2, N)}
    line = {}
    for k in Lb:
        x, n_, _ = dark_lines(Lb[k], int(walnut_edge(gray[k])) + 60, W - 6)
        line[k] = dict(x=x, rows=n_)
    # the new jamb: from the clip's edge at kj0 (8 px left of it, so the clip's edge is under it) and the clip's speed there
    x0 = rv[kj0] - 8.0
    v0 = 0.5 * (rv[kj0 + 2] - rv[kj0])
    xj, acc = jamb_path(x0, v0, kj0, kj1)
    vj = {k: (xj[k] - xj[k - 1]) if k > kj0 else v0 for k in xj}
    wj = {k: max(1.0, 0.15 * vj[k]) for k in xj}
    e_src = line[JAMB_SRC]["x"] + 4.0
    jamb = Jamb(rgb(os.path.join(a.bank, names[JAMB_SRC - 1])), e_src)
    # the handover from the model's jamb (C1A-L4): the new jamb starts at the tone the model's jamb had in the frame before (its
    # mean colour over the columns the new jamb takes), and reaches its own tone over five frames, like an eye adapting
    x_a = int(np.ceil(xj[kj0] + wj[kj0]))
    prev = rgb(os.path.join(a.bank, names[kj0 - 2]))[:, x_a:W].reshape(-1, 3).mean(0)
    ours = jamb.render(xj[kj0], wj[kj0])[0][:, x_a:W].reshape(-1, 3).mean(0)
    ratio = np.clip(prev / np.maximum(ours, 1e-3), 0.6, 1.4)
    jgain = {k: ratio ** (max(0, kj0 + 5 - k) / 5.0) for k in xj}

    rep = dict(tool="repair_strip_1a.py", round=3, date="2026-11-17", first_frame=k0, y_cut=Y_CUT, glazing_plane_x=XG,
               sources_order=[s_["name"] for s_ in src],
               registration=dict(dx_measured={k: round(dx_raw[k], 2) for k in ks}, dx_used={k: round(dx[k], 2) for k in ks},
                                 note="dx: the clip's walnut edge (sub-pixel) minus the clay's (px), smoothed 1-2-1 over the frames (the first "
                                      "and last as measured)"),
               jamb=dict(source_frame=JAMB_SRC, source_edge_x=e_src, frames=[kj0, kj1], start_x=round(x0, 1), start_speed=round(v0, 1),
                         accel_px_per_frame2=round(acc, 2), edge_x={k: round(v, 1) for k, v in xj.items()},
                         speed_px_per_frame={k: round(v, 1) for k, v in vj.items()}, edge_blur_px={k: round(v, 1) for k, v in wj.items()},
                         handover_gain_rgb={k: [round(float(g), 3) for g in v] for k, v in jgain.items() if k < kj0 + 5},
                         clip_edge_measured={k: rv[k] for k in sorted(rv)},
                         clip_line_measured={k: line[k] for k in sorted(line) if k <= kj1 + 2},
                         note=f"one jamb from {kj0}: the clip's face at {JAMB_SRC} (right of its contour line), on the plane of the reveal; "
                              f"the edge leaves the frame by {kj1} (last visible step {xj[kj1 - 1] - xj[kj1 - 2]:.1f} px, out of the frame "
                              f"{xj[kj1] - xj[kj1 - 1]:.1f} px); the clay's jamb is out at ~130"),
               frames={})

    # the plate: what no still sees outside HT's frame, painted once at PLATE_K
    def compose(k, plate=None):
        tg = tgs[k]
        m = tg["m"]
        X = np.arange(W, dtype=np.float32)[None, :]
        paint, cov, who, occ_ht = paint_stills(tg, src, m)
        # the armchair (base.png's room depth has it, the clay has not): base.png's points in its box, splatted forward, where
        # they lie in front of the clay
        imc, okc, ddc = forward_direct(chair_st, tg["cam"], tg["fr"])
        okc = okc & np.isfinite(ddc) & tg["v"] & (ddc < tg["d"] * 0.995 - 0.005) & (m | (X > border[k] + 40))
        if okc.any():
            paint[okc] = imc[okc]
            who[okc] = 4
            cov |= okc
        nf = int(okc.sum())
        region = m | okc
        # behind the clay's jamb, left of the new jamb: HT forward (HT is past the jamb)
        nB = 0
        Bsel = np.zeros((H, W), bool)
        if k < kj1:
            xju = xj[k] - dx[k] if k >= kj0 else -1
            wl = border[k] + 40
            Bsel = tg["v"] & (tg["d"] < JAMB_NEAR) & (tg["P"][..., 2] > 0.03) & ~m & (X > wl) & (X < xju + wj.get(k, 1.0) + 2)
            if Bsel.any():
                imh, okh, ddh = forward_direct(ht, tg["cam"], tg["fr"])
                okB = Bsel & okh & np.isfinite(ddh) & (ddh > 2.0)
                paint[okB] = imh[okB]
                who[okB] = 5
                cov |= okB
                nB = int(okB.sum())
                region |= Bsel
        hole = region & ~cov
        # hidden from HT by the walnut lining (HT sees something nearer there, inside its frame), or behind the clay jamb where
        # HT forward has nothing: the clip keeps these (its own wall, 24 px ramp). Every other hole: the plate.
        u2, v2, d2 = ht["cam"].project(tg["P"])
        mx_, my_ = ht["cv"].px(u2, v2)
        dsh = cv2.remap(np.where(ht["valid"], ht["depth"], 0).astype(np.float32), np.nan_to_num(mx_, nan=-1e4).astype(np.float32),
                        np.nan_to_num(my_, nan=-1e4).astype(np.float32), cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        lining = occ_ht & (dsh > 0) & (dsh < 0.9 * d2) & (X < border[k] + 120)      # the band by the lining: not a window reveal corner
        hole_keep = hole & ((lining & in_frame_of(ht, tg["P"], 3.0)) | (Bsel & (X < border[k] + 120)))
        hole_out = hole & ~hole_keep
        xju_ = (xj[k] - dx[k]) if (kj0 <= k < kj1) else W + 100
        n_out_visible = int((hole_out & (X < xju_)).sum())
        n_keep_B = int((hole & Bsel).sum())
        n_plate = n_inp = 0
        if hole_out.any() and plate is not None:
            st = dict(name="plate", cam=plate["cam"], cv=plate["fr"], img=plate["img"], depth=plate["d"], valid=plate["ok"])
            imp, okp, _ = backward(st, tg["P"], hole_out)
            paint[okp] = imp[okp]
            who[okp] = 6
            cov |= okp
            hole_out &= ~okp
            n_plate = int(okp.sum())
        n_ext = 0
        if hole_out.any():
            lab = segments(tg["P"], tg["v"])
            paint, ext = extrude_fill(paint, cov, hole_out, tg, lab)
            n_ext = int(ext.sum())
            cov |= ext
            hole_out &= ~ext
        if hole_out.any():
            paint, rest = seg_inpaint(paint, cov, hole_out, lab)
            n_inp = int(hole_out.sum())
            cov |= hole_out
            if a.debug:
                cv2.imwrite(os.path.join(a.debug, f"inpainted-k{k}.png"), hole_out.astype(np.uint8) * 255)
        return dict(tg=tg, paint=paint, cov=cov, who=who, region=region, hole_keep=hole_keep, Bsel=Bsel,
                    n=dict(armchair_base_forward=nf, behind_jamb_HT=nB, behind_jamb_kept_clip=n_keep_B, plate=n_plate, extruded=n_ext, inpainted=n_inp,
                           holes_left_of_jamb=n_out_visible))

    cp = compose(PLATE_K)
    pok = cp["cov"] & tgs[PLATE_K]["m"]
    pimg = cp["paint"].copy()                                 # padded past its edges, so a look-up never blends in black
    if (~pok).any():
        p8 = cv2.inpaint(to8(pimg), (~pok).astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
        pimg = np.where(pok[..., None], pimg, p8.astype(np.float32) / 255)
    plate = dict(cam=tgs[PLATE_K]["cam"], fr=tgs[PLATE_K]["fr"], img=pimg, d=tgs[PLATE_K]["d"], ok=pok)
    rep["plate"] = dict(frame=PLATE_K, inpainted_px=cp["n"]["inpainted"],
                        note="painted once, inside each clay plane, where no still sees outside HT's frame; every frame looks it up through its clay depth")
    if a.debug:
        os.makedirs(a.debug, exist_ok=True)
        cv2.imwrite(os.path.join(a.debug, f"plate-k{PLATE_K}.png"), cv2.cvtColor(to8(cp["paint"]), cv2.COLOR_RGB2BGR))

    for k in range(1, N + 1):
        srcp = os.path.join(a.bank, names[k - 1])
        dst = os.path.join(a.out, names[k - 1])
        if k not in tgs or k == N:
            shutil.copyfile(srcp, dst)
            continue
        img = rgb(srcp)
        c = cp if k == PLATE_K else compose(k, plate)
        X = np.arange(W, dtype=np.float32)[None, :]
        paint = shift_x(c["paint"], dx[k])
        cov = shift_x(c["cov"].astype(np.float32), dx[k]) > 0.5
        region = shift_x(c["region"].astype(np.float32), dx[k]) > 0.5
        hole_keep = shift_x(c["hole_keep"].astype(np.float32), dx[k]) > 0.5
        region &= cov | hole_keep
        lay = (region & ~hole_keep).astype(np.float32)
        alpha = cv2.GaussianBlur(lay, (0, 0), FEATHER)
        if hole_keep.any():                                # the clip's own wall and floor meet the paint over 24 px, not on a line
            alpha *= np.clip(cv2.distanceTransform((~hole_keep).astype(np.uint8), cv2.DIST_L2, 3) / 24.0, 0, 1)
        # the floor line (where the living room's floor meets the hall's, the paint's lower border): a 40 px vertical blend
        col_has = region.any(axis=0)
        bottom = np.where(col_has, H - 1 - np.argmax(region[::-1, :], axis=0), -1)
        rr = np.arange(H, dtype=np.float32)[:, None]
        xjk = xj.get(k, -1e9)
        floorcols = (bottom > 0) & (bottom < H - 5) & ((X[0] < xjk - 20) if k < kj1 else True)
        ramp = np.clip((bottom[None, :] - rr) / 40.0, 0, 1)          # 0 on the clay's threshold line, the paint 40 px above it
        zone = floorcols[None, :] & (rr > bottom[None, :] - 40) & (rr <= bottom[None, :] + 10) & cov
        alpha = np.where(zone, ramp, alpha)
        # the paint comes in over the first three frames (the clip's own wall before it)
        if k < k0 + 3:
            t_ = float(np.clip((k - k0 + 2) / 5.0, 0, 1))
            alpha *= t_ * t_ * (3 - 2 * t_)
        paint = np.where(cov[..., None], paint, img)          # past the paint's edge (its feather) the clip, never black
        res = img * (1 - alpha[..., None]) + paint * alpha[..., None]
        if kj0 <= k < kj1:
            jim, ja = jamb.render(xj[k], wj[k])
            jim = np.clip(jim * jgain[k][None, None, :].astype(np.float32), 0, 1)
            res = res * (1 - ja[..., None]) + jim * ja[..., None]
        tot = float((region | hole_keep).sum()) or 1.0
        whoi = cv2.warpAffine(c["who"], np.float32([[1, 0, dx[k]], [0, 1, 0]]), (W, H), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
        if a.debug:
            cv2.imwrite(os.path.join(a.debug, f"who-k{k}.png"), whoi)
        rep["frames"][k] = dict(region_px=int(region.sum()), holes_kept_clip_frac=round(float(hole_keep.sum()) / tot, 4),
                                dx=round(dx[k], 2), jamb_edge=round(xj[k], 1) if k in xj and k < kj1 else None,
                                sources={nm: round(float(((whoi == i + 1) & region).sum()) / tot, 4)
                                         for i, nm in enumerate(["HT", "HDx", "base.png", "base.png forward (armchair)", "HT forward (behind the clay jamb)", "plate"])},
                                px=c["n"])
        cv2.imwrite(dst, cv2.cvtColor(to8(res), cv2.COLOR_RGB2BGR))
    for fn in os.listdir(a.bank):
        if not (fn.endswith(".png") and fn[:4].isdigit()):
            shutil.copyfile(os.path.join(a.bank, fn), os.path.join(a.out, fn))
    fr = rep["frames"]
    rep["summary"] = dict(frames_painted=len(fr), first=k0, last=max(fr), method="backward look-up of the real stills (HT, HDx, base.png) through the "
                          "clay depth of each frame; the glass on the glazing plane; one plate for what no still sees; one jamb from 122",
                          holes_kept_clip_max=max(v["holes_kept_clip_frac"] for v in fr.values()),
                          inpainted_px_outside_plate_frame={k: v["px"]["inpainted"] for k, v in fr.items() if v["px"]["inpainted"] and k != PLATE_K},
                          dx_range=[round(min(v["dx"] for v in fr.values()), 2), round(max(v["dx"] for v in fr.values()), 2)])
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep["summary"], indent=1))
    return 0


# ----------------------------------------------------------------------------------------------------------------
def check_main(argv=None) -> int:
    """The self-check, measured on the frames (round 2): each measure on the repaired bank and, at the same place, on the
    bank before the repair, per frame:
      lines    narrow dark vertical lines anywhere right of the walnut edge + 60 px (L* 15 below both columns 4 px away): the
               column with most such rows, and its row count (QA counted 1,065 of 1,080 rows at x 1634 in 123); also the
               count at the clip's own line x (found on the bank before) and at the new jamb's edge
      shards   the dark pixels (L* < 70) in QA's ceiling zone (x 1786-1919, y 0-140) and the floor zone under the armchair
               (x 1840-1900, y 760-860), their sharp edges (Sobel > 40 on L*), and the even/odd flicker: per zone, the mean
               |L*(k) - (L*(k-1) + L*(k+1))/2| per pixel
      birch    HT's birch (frame 143, the left pane) scaled to each frame's glazing distance, the best NCC in a 60 px window
      tab, jamb vs border, floor, flash   as in round 1
    """
    ap = argparse.ArgumentParser(description="repair_strip_1a.py check")
    ap.add_argument("--bank", required=True, help="the repaired bank")
    ap.add_argument("--before", required=True, help="the bank before the repair")
    ap.add_argument("--repair", required=True)
    ap.add_argument("--clay", required=True)
    ap.add_argument("--out")
    ap.add_argument("--who", help="the repair's --debug folder (who-k%%d.png: 4 = the armchair), to leave the armchair out of the bench steps")
    a = ap.parse_args(argv)
    rep = json.load(open(a.repair))
    fr = {int(k): v for k, v in rep["frames"].items()}
    jline = {int(k): v for k, v in rep["jamb"]["clip_line_measured"].items()}
    names = sorted(f for f in os.listdir(a.bank) if f.endswith(".png") and f[:4].isdigit())
    LA = {k: lstar_bgr(cv2.imread(os.path.join(a.bank, names[k - 1]))) for k in range(118, N + 1)}
    LB = {k: lstar_bgr(cv2.imread(os.path.join(a.before, names[k - 1]))) for k in range(118, N + 1)}

    def outline(g, cx, rows):
        dips = []
        for r0 in rows:
            if cx < 14 or cx > W - 15:
                continue
            prof = g[r0:r0 + 30, cx - 12:cx + 13].mean(axis=0)
            for c0 in range(9, 16):
                ln = prof[c0 - 1:c0 + 2]
                left, right = prof[c0 - 8:c0 - 3].mean(), prof[c0 + 4:c0 + 9].mean()
                dips.append(float(max(min(left, right) - ln.min(), ln.max() - max(left, right))))
        return round(max(dips), 1) if dips else None

    def edge_line(g, cx):
        xs, ys = [], []
        for r0 in range(150, 950, 30):
            prof = cv2.GaussianBlur(g[r0:r0 + 30, cx - 25:cx + 26].mean(axis=0).reshape(1, -1), (0, 0), 1.0).ravel()
            gr = np.diff(prof)
            j = int(np.argmax(gr))
            if gr[j] > 6:
                xs.append(cx - 25 + j + 0.5)
                ys.append(r0 + 15)
        if len(xs) < 6:
            return None, None
        c = np.polyfit(ys, xs, 1)
        return round(float(np.max(np.abs(np.array(xs) - np.polyval(c, ys)))), 1), float(np.median(xs))

    # birch template: HT's frame (bank 143), the left pane
    tg143 = target(a.clay, N)
    g143 = cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[N - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gl = tg143["glass"]
    ys, xs = np.nonzero(gl)
    # the left pane: the glass component containing the most pixels left of the mullion
    n_, lab = cv2.connectedComponents(gl.astype(np.uint8))
    best = max(range(1, n_), key=lambda i: (lab == i).sum())
    ys, xs = np.nonzero(lab == best)
    bx0, bx1, by0, by1 = xs.min() + 8, xs.max() - 6, 220, 600
    tmpl = g143[by0:by1, bx0:bx1]
    zg = 3.60 - XG

    def ncc_birch(g, k):
        s = zg / (zg + L1A * (N - k) / (N - 1))
        t = cv2.resize(tmpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cxm = CX + ((bx0 + bx1) / 2 - CX) * s
        cym = CY + ((by0 + by1) / 2 - CY) * s
        x0 = int(cxm - t.shape[1] / 2 - 30)
        y0 = int(cym - t.shape[0] / 2 - 30)
        win = g[max(y0, 0):y0 + t.shape[0] + 60, max(x0, 0):min(x0 + t.shape[1] + 60, W)]
        if win.shape[0] < t.shape[0] or win.shape[1] < t.shape[1]:
            return None
        r = cv2.matchTemplate(win, t, cv2.TM_CCOEFF_NORMED)
        return round(float(r.max()), 3)

    # the bench under the window (C1A-M4), step to step after motion alignment through the clay: each pixel of frame k (paint
    # coordinates: x - dx) is carried to frame k+1 by its clay world point; |dL*| and signed dL*, the armchair and the jamb left out
    def bench_steps(lo=128, hi=N, box=(620, 820, 1780, 1915), lab="after", L=LA):
        y0, y1, x0, x1 = box
        res = {}
        jx = {int(k): v for k, v in rep["jamb"]["edge_x"].items()}
        for k in range(lo, hi):
            tgk = target(a.clay, k)
            dxk = fr[k]["dx"] if k in fr else 0.0
            dxn = fr[k + 1]["dx"] if (k + 1) in fr else 0.0
            ys_, xs_ = np.mgrid[y0:y1, x0:x1]
            xc = (xs_ - dxk).astype(np.float32)
            P = np.stack([cv2.remap(tgk["P"][..., i].astype(np.float32), xc, ys_.astype(np.float32), cv2.INTER_LINEAR) for i in range(3)], -1)
            vv = cv2.remap(tgk["v"].astype(np.uint8), xc, ys_.astype(np.float32), cv2.INTER_NEAREST) > 0
            u2, v2, d2 = cam_at(k + 1).project(P)
            mx, my = cg.Canvas.frame(W, H).px(u2, v2)
            mx = (mx + dxn).astype(np.float32)
            my = my.astype(np.float32)
            Ln = cv2.remap(L[k + 1], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
            Lk = L[k][y0:y1, x0:x1]
            ok = vv & (Ln >= 0) & (mx > 2) & (mx < W - 3)
            if k in jx and k < 131:
                ok &= xs_ < jx[k] - 12
            if (k + 1) in jx and k + 1 < 131:
                ok &= mx < jx[k + 1] - 12
            if a.who:
                for kk, xx, yy in ((k, xs_.astype(np.float32), ys_.astype(np.float32)), (k + 1, mx, my)):
                    pw = os.path.join(a.who, f"who-k{kk}.png")
                    if os.path.exists(pw):
                        wch = cv2.dilate((cv2.imread(pw, 0) == 4).astype(np.uint8), np.ones((13, 13), np.uint8))
                        ok &= cv2.remap(wch, xx, yy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) == 0
            d = (Ln - Lk)[ok]
            res[k] = dict(step=f"{k}->{k + 1}", px=int(ok.sum()), mean_abs=round(float(np.abs(d).mean()), 2) if ok.any() else None,
                          mean_signed=round(float(d.mean()), 2) if ok.any() else None, px_over_8=int((np.abs(d) > 8).sum()))
        return res

    zones = dict(ceiling=(0, 140, 1786, 1920), floor=(760, 860, 1840, 1900))
    out = dict(frames=[])
    out["bench_steps_after"] = bench_steps()
    out["bench_steps_before"] = bench_steps(L=LB)
    la, lb = [], []
    for k in sorted(set(fr) | set(range(118, N))):
        A, B = LA[k], LB[k]
        rec = dict(frame=k)
        wr = int(walnut_edge(cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[k - 1])), cv2.COLOR_BGR2GRAY)))
        for tag, L in (("after", A), ("before", B)):
            x, n_, cnt = dark_lines(L, wr + 60, W - 6)
            rec[f"line_max_{tag}"] = dict(x=x, rows=n_)
            if tag == "after":
                cntA = cnt
            else:
                cntB = cnt
        if k in jline and jline[k]["rows"] > 100:
            x = jline[k]["x"]
            rec["at_clip_line"] = dict(x=x, rows_before=int(cntB[max(x - 3, 0):x + 4].max()), rows_after=int(cntA[max(x - 3, 0):x + 4].max()))
        if k in fr and fr[k].get("jamb_edge") is not None:
            x = int(round(fr[k]["jamb_edge"]))
            if 4 < x < W - 4:
                rec["at_new_jamb_edge"] = dict(x=x, rows_after=int(cntA[max(x - 6, 0):min(x + 7, W)].max()))
        for zn, (y0, y1, x0, x1) in zones.items():
            for tag, L in (("after", A), ("before", B)):
                z = L[y0:y1, x0:x1]
                sob = np.hypot(cv2.Sobel(z, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(z, cv2.CV_32F, 0, 1, ksize=3))
                rec[f"{zn}_dark_{tag}"] = int((z < 70).sum())
                rec[f"{zn}_sharp_dark_{tag}"] = int(((z < 70) & (cv2.dilate((sob > 40).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)).sum())
                if 118 < k < N:
                    zp, zn_ = (LA if tag == "after" else LB)[k - 1][y0:y1, x0:x1], (LA if tag == "after" else LB)[k + 1][y0:y1, x0:x1]
                    rec[f"{zn}_flicker_{tag}"] = round(float(np.abs(z - 0.5 * (zp + zn_)).mean()), 2)
        if 130 <= k <= N:
            rec["birch_ncc_after"] = ncc_birch(cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[k - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32), k)
            rec["birch_ncc_before"] = ncc_birch(cv2.cvtColor(cv2.imread(os.path.join(a.before, names[k - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32), k)
        if k in fr:
            gA = cv2.cvtColor(cv2.imread(os.path.join(a.bank, names[k - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
            gB = cv2.cvtColor(cv2.imread(os.path.join(a.before, names[k - 1])), cv2.COLOR_BGR2GRAY).astype(np.float32)
            m = shift_x(clay_mask(a.clay, k).astype(np.float32), fr[k]["dx"]) > 0.5
            cx = int(round(float(np.nanmedian(left_border(m)[200:800]))))
            for tag, g in (("after", gA), ("before", gB)):
                rec[f"outline_walnut_{tag}"] = outline(g, cx, range(150, 920, 30))
                tab, xe = edge_line(g, cx)
                rec[f"tab_px_{tag}"] = tab
                if tag == "after":
                    rec["jamb_vs_border_px"] = None if xe is None else round(abs(xe - cx), 1)
            bottom = np.array([np.max(np.nonzero(m[:, c])[0]) if m[:, c].any() else -1 for c in range(W)])
            cols = np.nonzero((bottom > 20) & (bottom < H - 20))[0]
            if len(cols) > 10:
                for tag, g in (("after", gA), ("before", gB)):
                    above = np.mean([g[bottom[c] - 12:bottom[c] - 3, c].mean() for c in cols])
                    below = np.mean([g[bottom[c] + 3:bottom[c] + 12, c].mean() for c in cols])
                    rec[f"floor_step_{tag}"] = round(float(above - below), 1)
            la.append(float(gA[m].mean()) if m.any() else np.nan)
            lb.append(float(gB[m].mean()) if m.any() else np.nan)
        out["frames"].append(rec)

    def flash(x):
        x = np.array(x)
        x = x[np.isfinite(x)]
        return round(float(np.max(np.abs(np.diff(x, 2)))), 2) if len(x) > 3 else None
    F = out["frames"]
    mx = lambda key: max((f[key] for f in F if f.get(key) is not None), default=None, key=abs)
    r130 = [f for f in F if 130 <= f["frame"] <= 141]
    ba = out["bench_steps_after"]
    out["summary"] = dict(
        frames=[F[0]["frame"], F[-1]["frame"]],
        bench_steps_after={v["step"]: [v["mean_abs"], v["mean_signed"]] for v in ba.values()},
        bench_steps_before={v["step"]: [v["mean_abs"], v["mean_signed"]] for v in out["bench_steps_before"].values()},
        bench_step_max_after=max(v["mean_abs"] for v in ba.values() if v["mean_abs"] is not None),
        lines_after={f["frame"]: f["line_max_after"] for f in F if 118 <= f["frame"] <= 135},
        lines_before={f["frame"]: f["line_max_before"] for f in F if 118 <= f["frame"] <= 135},
        at_clip_line={f["frame"]: f["at_clip_line"] for f in F if "at_clip_line" in f},
        at_new_jamb_edge={f["frame"]: f["at_new_jamb_edge"]["rows_after"] for f in F if "at_new_jamb_edge" in f},
        ceiling_dark_after_130_141={f["frame"]: f["ceiling_dark_after"] for f in r130},
        ceiling_dark_before_130_141={f["frame"]: f["ceiling_dark_before"] for f in r130},
        floor_sharp_dark_after_130_141={f["frame"]: f["floor_sharp_dark_after"] for f in r130},
        floor_sharp_dark_before_130_141={f["frame"]: f["floor_sharp_dark_before"] for f in r130},
        ceiling_flicker_after_max=max(f.get("ceiling_flicker_after", 0) for f in r130),
        floor_flicker_after_max=max(f.get("floor_flicker_after", 0) for f in r130),
        birch_ncc_after={f["frame"]: f.get("birch_ncc_after") for f in F if 130 <= f["frame"] <= N},
        birch_ncc_before={f["frame"]: f.get("birch_ncc_before") for f in F if 130 <= f["frame"] <= N},
        outline_walnut_after_max=mx("outline_walnut_after"), outline_walnut_before_max=mx("outline_walnut_before"),
        tab_px_after_max=mx("tab_px_after"), tab_px_before_max=mx("tab_px_before"),
        jamb_vs_border_px_max=mx("jamb_vs_border_px"),
        floor_step_after_max=mx("floor_step_after"), floor_step_before_max=mx("floor_step_before"),
        strip_flash_after=flash(la), strip_flash_before=flash(lb))
    print(json.dumps(out["summary"], indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(check_main(sys.argv[2:]))
    sys.exit(main())
