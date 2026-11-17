#!/usr/bin/env python3
"""
walk_test.py: "מבחן ההליכה". Is a raw clip from a video model a WALK along the planned straight line, or a blend of
its two end frames (a dissolve, or a zoom on a flat picture)? Runs on the raw clip in a minute or two, 0 var2 tokens.
Nothing else is sent to var2 before the clip passes (docs/proposals/wm-arrival-entrance-to-living-2026-11-13.md, 3).

THE CLAY IS THE RULER. render-agent writes, for every clay station along the line, a depth pass and a structure-edges
pass. An edge pixel with its depth is a point in the house: the stations together are a cloud of the house's
structure lines (jambs, corners, the floor line, furniture outlines) as 3D points. For a clip frame and a guessed
distance s along the line, the cloud is projected through the plan's camera at s and compared with the edges that
are really in the frame (chamfer distance). The s that fits best is where that frame stands. This needs no texture
(the house is bare plaster) and does not drift: every frame is measured on its own.

The four checks
 1 parallax   s is solved three times per frame: from all the structure, from its NEAR half and from its FAR half.
              In a walk the three agree. In a zoom on a flat picture everything grows by one factor, so the far
              structure says "walked far" and the near structure says "hardly moved". Reported as the brief words it:
              the size of the near structure and the size of the far structure, each against the size the plan gives
              it at the frame's position; more than 5 % off fails.
 2 dissolve   Each middle frame is fitted as a mix of the first and the last frame (on gradients, so that plaster
              that is the same colour everywhere does not count as agreement). In a walk the middle frames are not a
              mix of the ends (R2 low); in a dissolve they are (R2 near 1). The same fit with the first frame
              enlarged and the last frame reduced as flat pictures (the best scale of each) catches the flat zoom
              even where the structure is too shallow for check 1 (flat_zoom_r2).
 3 progress   s must rise all the time. A stretch where the picture changes but s does not is a morph. Uneven speed
              does not fail (the assembly resamples to constant speed); s per frame is written out for that.
 4 verticals  A level camera keeps every vertical edge vertical in every frame: long segments within 10 degrees of
              vertical must stay within +-0.5 degrees (median per frame).
Also reported: how far the house's structure lines are from the frame's edges at the best s (% of the frame width;
QA limit 1 %). Shapes of furniture and "nothing is born or vanishes" stay an eye check at 100 %.

Options added 2026-11-17 (the final entrance, ENT2; docs/proposals/wm-arrival-from-door-2026-11-14.md section 13):
  --exclude ID:A-B   the clay id ID (the station's -id.png palette index) does not take part in the fit while the
                     candidate position is between A and B metres from the route's first camera. For a part of the
                     house the model may simplify or leave out without failing the clip (id 50, the dining glimpse
                     of clip 2, 1.0-1.8 m: wm-front-door-2026-11-14.md 10.4). Repeatable.
  --events FILE[:JOB] the clip's event table (jobs.json "walk_events" of job JOB, or a JSON list): for every event
                     ("at_m", or a "window_m" [a, b]), the clip frames where the solved position reaches it, so the
                     eye check at 100 % looks at the right frames (e.g. the herbs must be gone by 2.40 m in clip 1a).

  python3 walk_test.py test --frames DIR|clip.mp4 --route clip2 --stations DIR --ids b/S02,...,b/S11 --line t-e0 --out report.json
  python3 walk_test.py fakes --first A.png --last B.png --out DIR [--n 121]     # a dissolve and a flat zoom
  python3 walk_test.py selftest --out DIR      # an exact proxy walk (uneven speed) must pass; dissolve and zoom must fail
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402

ROUTES = {"clip1": (cg.D0, cg.HD), "clip1a": (cg.D0, cg.HT), "clip1b": (cg.HT, cg.HD), "clip2": (cg.HDX, cg.M0),
          "t-e0": (cg.H0X, cg.M0)}
LIMITS = dict(parallax_dev=0.05, dissolve_r2=0.55, vertical_deg=0.5, structure_w=0.01, stall_frac=0.12, back_m=0.04,
              jump_frac=0.25)
TRUNC = 0.008          # chamfer truncation, fraction of the frame width (7.7 px at 960)


# ----------------------------------------------------------------------------------------------------------------
def read_frames(src: str, w: int = 960) -> list[np.ndarray]:
    """Frames of a clip (a directory of images, or a video file) as RGB uint8 at width w."""
    out = []
    if os.path.isdir(src):
        for n in sorted(f for f in os.listdir(src) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))):
            im = cv2.imread(os.path.join(src, n), cv2.IMREAD_COLOR)
            h = int(round(im.shape[0] * w / im.shape[1]))
            out.append(cv2.cvtColor(cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA) if im.shape[1] != w else im, cv2.COLOR_BGR2RGB))
    else:
        cap = cv2.VideoCapture(src)
        while True:
            ok, im = cap.read()
            if not ok:
                break
            h = int(round(im.shape[0] * w / im.shape[1]))
            out.append(cv2.cvtColor(cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA) if im.shape[1] != w else im, cv2.COLOR_BGR2RGB))
        cap.release()
    if not out:
        raise SystemExit(f"no frames in {src}")
    return out


# ----------------------------------------------------------------------------------------------------------------
# the ruler: structure points of the clay stations
# ----------------------------------------------------------------------------------------------------------------
def cloud(depth: np.ndarray, edges: np.ndarray, cam: cg.Cam, cv: cg.Canvas, max_pts: int = 30000, seed: int = 0,
          labels: np.ndarray | None = None):
    """World points of the structure edges of one station. An edge between a near and a far surface belongs to the
    near one: each edge pixel takes the nearest depth of its 3 x 3 neighbourhood. With `labels` (the id pass), also
    the id of every point: (points, ids)."""
    d = np.where(np.isfinite(depth) & (depth > 0), depth, 1e6).astype(np.float32)
    dn = cv2.erode(d, np.ones((3, 3), np.uint8))
    ys, xs = np.nonzero(edges & (dn < 1e5))
    if len(xs) > max_pts:
        sel = np.random.default_rng(seed).choice(len(xs), max_pts, replace=False)
        ys, xs = ys[sel], xs[sel]
    u = (xs + 0.5 - cv.box[0]) / cv.fw
    v = (ys + 0.5 - cv.box[1]) / cv.fh
    P = cam.unproject(u, v, dn[ys, xs].astype(np.float64))
    if labels is None:
        return P
    # the id of an edge pixel: the id of the nearest surface around it (the one whose depth the point took)
    near = (d[ys, xs] <= dn[ys, xs] + 1e-4)
    lab = labels[ys, xs].copy()
    if (~near).any():
        H, W = d.shape
        for j in np.nonzero(~near)[0]:
            y0, y1, x0, x1 = max(0, ys[j] - 1), min(H, ys[j] + 2), max(0, xs[j] - 1), min(W, xs[j] + 2)
            win = d[y0:y1, x0:x1]
            iy, ix = np.unravel_index(int(np.argmin(win)), win.shape)
            lab[j] = labels[y0 + iy, x0 + ix]
    return P, lab.astype(np.int32)


def canvas_of(name: str, W: int, H: int) -> cg.Canvas:
    return {"frame": cg.Canvas.frame(W, H), "base": cg.Canvas(W, H, cg.Canvas.base(W).box),
            "tall": cg.Canvas.tall(W, H, cg.BASE_BOX[0] / (cg.BASE_BOX[2] - cg.BASE_BOX[0]))}[name]


def load_station(folder: str, fid: str, cam: cg.Cam, canvas: str = "base", with_ids: bool = False):
    """A clay frame of render-agent: <id>-depth.png (16-bit, metres = value / 5000, 65535 = sky) and <id>-edges.png
    (white with black edges, 1 px). with_ids: also <id>-id.png (a palette PNG whose index is the clay id) -> (points,
    ids)."""
    depth, valid = cg.load_depth_png(os.path.join(folder, fid + "-depth.png"))
    e = cv2.imread(os.path.join(folder, fid + "-edges.png"), cv2.IMREAD_GRAYSCALE)
    if e is None:
        raise SystemExit(f"{fid}-edges.png is missing")
    H, W = depth.shape
    labels = None
    if with_ids:
        from PIL import Image
        im = Image.open(os.path.join(folder, fid + "-id.png"))
        if im.mode != "P":
            raise SystemExit(f"{fid}-id.png is not a palette PNG (mode {im.mode}): the index is the clay id")
        labels = np.asarray(im)
    return cloud(np.where(valid, depth, np.inf), e < 128, cam, canvas_of(canvas, W, H), labels=labels)


class Ruler:
    """Stations along a straight route. clouds[k] is the structure seen from the station at distance at[k] (metres
    from the route's first camera, along the route)."""

    def __init__(self, cam0: cg.Cam, cam1: cg.Cam, clouds: list[np.ndarray], at: list[float],
                 ids: list[np.ndarray] | None = None, exclude: list[tuple[int, float, float]] | None = None):
        """ids: the clay id of every point of every cloud (needed for `exclude`). exclude: (id, a, b): that id does not
        take part in the fit while the candidate position s is within [a, b] (metres from cam0)."""
        self.cam0, self.cam1 = cam0, cam1
        self.exclude = list(exclude or [])
        if self.exclude and ids is None:
            raise ValueError("exclude needs the ids of the clouds")
        vec = np.asarray(cam1.loc) - np.asarray(cam0.loc)
        self.L = float(np.linalg.norm(vec))
        self.dir = vec / self.L
        order = np.argsort(at)
        self.at = np.array([at[i] for i in order], np.float64)
        self.clouds = [clouds[i] for i in order]
        self.ids = [ids[i] for i in order] if ids is not None else None
        # coordinates of every cloud in the route camera's axes (the camera only moves along `dir`, never turns)
        self.rel = []
        for P in self.clouds:
            q = P - np.asarray(cam0.loc)[None]
            self.rel.append(np.stack([q @ cam0.r, q[:, 2], q @ cam0.f], axis=1))       # x (right), z (up, from the lens), d (forward)
        self.fd = float(self.dir @ cam0.f)        # forward, sideways and upward components of one metre of travel
        self.fx = float(self.dir @ cam0.r)
        self.fz = float(self.dir[2])

    def station_for(self, s: float) -> int:
        return int(np.argmin(np.abs(self.at - s)))

    def project(self, k: int, s: float, w: int, h: int):
        """Pixels (x, y) and depth of station k's structure as the route camera at distance s sees it."""
        R = self.rel[k]
        d = R[:, 2] - s * self.fd
        x = R[:, 0] - s * self.fx
        with np.errstate(divide="ignore", invalid="ignore"):
            u = self.cam0.u0 + cg.KU * x / d
            v = self.cam0.v0 - cg.KV * (R[:, 1] - s * self.fz) / d
        px, py = u * w - 0.5, v * h - 0.5
        ok = (d > 0.08) & (px >= 1) & (px <= w - 2) & (py >= 1) & (py <= h - 2)
        return px, py, d, ok & self.keep(k, s)

    def keep(self, k: int, s: float) -> np.ndarray:
        """Points of station k that take part in the fit at position s (all, unless an `exclude` applies)."""
        m = np.ones(len(self.rel[k]), bool)
        for cid, a, b in self.exclude:
            if a <= s <= b:
                m &= self.ids[k] != cid
        return m


def frame_dt(gray: np.ndarray) -> np.ndarray:
    """Distance (pixels) from every pixel to the nearest edge of the frame; edges by Canny with thresholds set from
    the frame's own gradient statistics, so that a pale render and a contrasty one are treated alike."""
    g = cv2.GaussianBlur(gray, (0, 0), 1.0)
    mag = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    hi = float(max(12.0, np.percentile(mag, 93)))
    e = cv2.Canny(g, 0.4 * hi, hi, L2gradient=True)
    return cv2.distanceTransform(255 - e, cv2.DIST_L2, 3)


def _sample(dt: np.ndarray, px: np.ndarray, py: np.ndarray) -> np.ndarray:
    x0 = np.floor(px).astype(np.int32)
    y0 = np.floor(py).astype(np.int32)
    fx, fy = px - x0, py - y0
    return (dt[y0, x0] * (1 - fx) * (1 - fy) + dt[y0, x0 + 1] * fx * (1 - fy) + dt[y0 + 1, x0] * (1 - fx) * fy + dt[y0 + 1, x0 + 1] * fx * fy)


def solve_frame(R: Ruler, dt: np.ndarray, lo: float | None = None, hi: float | None = None, step: float = 0.03) -> dict:
    """The distance s that best puts the house's structure on the frame's edges: from all points, from the near half
    and from the far half. Costs are mean truncated distances, in fractions of the frame width. A structure point that
    falls outside the frame costs the truncation value (it cannot be checked), so that a position is never preferred
    because it pushes the structure out of sight."""
    h, w = dt.shape
    T = TRUNC * w
    lo = -0.05 if lo is None else lo
    hi = R.L + 0.05 if hi is None else hi

    def cost(s: float, k: int, sel: np.ndarray | None) -> float:
        px, py, d, ok = R.project(k, float(s), w, h)
        kp = R.keep(k, float(s))                       # an excluded point is left out of the mean (no truncation cost)
        sel = kp if sel is None else (sel & kp)
        px, py, ok = px[sel], py[sel], ok[sel]
        if len(ok) == 0:
            return np.inf
        c = np.full(len(ok), T, np.float32)
        if ok.any():
            c[ok] = np.minimum(_sample(dt, px[ok], py[ok]), T)
        return float(c.mean()) / w

    def search(svals, k, sel):
        c = np.array([cost(s, R.station_for(float(np.clip(s, 0, R.L))) if k is None else k, sel) for s in svals])
        i = int(np.argmin(c))
        fine = np.linspace(svals[max(0, i - 1)], svals[min(len(svals) - 1, i + 1)], 31)
        c2 = np.array([cost(s, R.station_for(float(np.clip(s, 0, R.L))) if k is None else k, sel) for s in fine])
        j = int(np.argmin(c2))
        return dict(s=float(fine[j]), cost_w=float(c2[j]), contrast=float(np.median(c) / max(1e-9, c2[j])))

    res = {"all": search(np.arange(lo, hi + 1e-9, step), None, None), "near": None, "far": None}
    # the near and the far half: the SAME points for every candidate (the station nearest the solved position,
    # split at the median depth of what is in frame there), searched within a metre of the solved position
    s0 = res["all"]["s"]
    k = R.station_for(float(np.clip(s0, 0, R.L)))
    px, py, d, ok = R.project(k, s0, w, h)
    res["n"] = int(ok.sum())
    if ok.sum() >= 80:
        med = float(np.median(d[ok]))
        near, far = ok & (d <= med), ok & (d > med)
        win = np.arange(max(lo, s0 - 1.0), min(hi, s0 + 1.0) + 1e-9, step)
        if near.sum() >= 40 and far.sum() >= 40:
            res["d_near"], res["d_far"] = float(np.median(d[near])), float(np.median(d[far]))
            res["near"] = search(win, k, near)
            res["far"] = search(win, k, far)
    return res


# ----------------------------------------------------------------------------------------------------------------
def dissolve_r2(frames: list[np.ndarray]) -> list[float]:
    """R2 of each frame's gradients as a mix of the first and the last frame's gradients."""
    def grad(im):
        g = cv2.cvtColor(cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 1.0)
        return np.concatenate([cv2.Sobel(g, cv2.CV_32F, 1, 0).ravel(), cv2.Sobel(g, cv2.CV_32F, 0, 1).ravel()])
    A, B = grad(frames[0]), grad(frames[-1])
    X = np.stack([A, B], axis=1)
    XtX = X.T @ X + 1e-6 * np.eye(2)
    out = []
    for f in frames:
        y = grad(f)
        coef = np.linalg.solve(XtX, X.T @ y)
        r = y - X @ coef
        out.append(float(1 - (r @ r) / max(1e-9, y @ y)))
    return out


def flat_zoom_r2(frames: list[np.ndarray], cam0: cg.Cam, step: int = 2) -> list[float]:
    """For each middle frame (25-75 % of the clip): the best FLAT zoom of the first frame (scale 1-6 about the
    vanishing point) and the best flat zoom-out of the last frame (scale 1/6-1), and the R2 of the frame's gradients
    as a mix of the two. A flat picture that grows (with or without a melt into the last frame) is explained well
    (R2 near 1). A real walk is not: near and far structure grow at different rates, so no one scale aligns them."""
    W, H = 480, 270
    cx, cy = cam0.u0 * W, cam0.v0 * H

    def gray(im):
        g = cv2.cvtColor(cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32)
        return cv2.GaussianBlur(g, (0, 0), 1.0)

    def grad(g):
        return np.concatenate([cv2.Sobel(g, cv2.CV_32F, 1, 0).ravel(), cv2.Sobel(g, cv2.CV_32F, 0, 1).ravel()])

    def zoomed(g, k):
        M = np.array([[k, 0, cx * (1 - k)], [0, k, cy * (1 - k)]], np.float32)
        return grad(cv2.warpAffine(g, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))

    gA, gB = gray(frames[0]), gray(frames[-1])
    sA, sB = np.geomspace(1.0, 6.0, 31), np.geomspace(1 / 6.0, 1.0, 31)
    KA = [zoomed(gA, k) for k in sA]
    KB = [zoomed(gB, k) for k in sB]
    nA = [float(x @ x) + 1e-9 for x in KA]
    nB = [float(x @ x) + 1e-9 for x in KB]

    def best(g, scales, K, nK, y):
        i = int(np.argmax([(x @ y) / np.sqrt(n) for x, n in zip(K, nK)]))
        lo, hi = scales[max(0, i - 1)], scales[min(len(scales) - 1, i + 1)]
        cand = [(K[i], (K[i] @ y) / np.sqrt(nK[i]))]
        for k in np.geomspace(lo, hi, 13):                      # refine to about 0.5 % of scale
            x = zoomed(g, float(k))
            cand.append((x, (x @ y) / np.sqrt(float(x @ x) + 1e-9)))
        return max(cand, key=lambda c: c[1])[0]

    T = len(frames)
    out = []
    for t in range(int(T * 0.25), max(int(T * 0.25) + 1, int(T * 0.75)), step):
        y = grad(gray(frames[t]))
        X = np.stack([best(gA, sA, KA, nA, y), best(gB, sB, KB, nB, y)], axis=1)
        coef = np.linalg.solve(X.T @ X + 1e-6 * np.eye(2), X.T @ y)
        r = y - X @ coef
        out.append(float(1 - (r @ r) / max(1e-9, y @ y)))
    return out


def verticals(frames: list[np.ndarray], step: int = 4) -> dict:
    """Tilt (degrees from vertical) of long near-vertical segments: the length-weighted median per sampled frame."""
    try:
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    except Exception:
        lsd = None
    per = []
    for i in range(0, len(frames), step):
        g = cv2.cvtColor(frames[i], cv2.COLOR_RGB2GRAY)
        if lsd is not None:
            lines = lsd.detect(g)[0]
            lines = np.zeros((0, 4)) if lines is None else lines.reshape(-1, 4)
        else:
            e = cv2.Canny(g, 40, 120)
            lines = cv2.HoughLinesP(e, 1, np.pi / 720, 60, minLineLength=g.shape[0] // 6, maxLineGap=4)
            lines = np.zeros((0, 4)) if lines is None else lines.reshape(-1, 4).astype(np.float32)
        if len(lines) == 0:
            continue
        dx, dy = lines[:, 2] - lines[:, 0], lines[:, 3] - lines[:, 1]
        ln = np.hypot(dx, dy)
        ang = np.degrees(np.arctan2(dx, np.abs(dy) + 1e-9)) * np.sign(dy + 1e-9)
        m = (ln > g.shape[0] * 0.18) & (np.abs(ang) < 10)
        if m.sum() < 2:
            continue
        a, wgt = ang[m], ln[m]
        order = np.argsort(a)
        cw = np.cumsum(wgt[order]) / wgt.sum()
        per.append(dict(frame=i, n=int(m.sum()), median_deg=round(float(a[order][np.searchsorted(cw, 0.5)]), 3),
                        worst_deg=round(float(np.abs(a).max()), 3)))
    if not per:
        return dict(frames=0, max_abs_median_deg=None, note="no long vertical segments found")
    return dict(frames=len(per), max_abs_median_deg=max(abs(p["median_deg"]) for p in per),
                p90_worst_deg=float(np.percentile([p["worst_deg"] for p in per], 90)))


# ----------------------------------------------------------------------------------------------------------------
def walk_test(frames: list[np.ndarray], R: Ruler, limits: dict = LIMITS) -> dict:
    T = len(frames)
    grays = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in frames]
    h, w = grays[0].shape
    L = R.L
    sol = [solve_frame(R, frame_dt(g)) for g in grays]
    def best(x):
        """The frame's position: the middle one of the three solutions when both halves pin it down, else the one
        from all the structure."""
        if x["all"] is None:
            return np.nan
        if x.get("near") and x.get("far") and min(x["near"]["contrast"], x["far"]["contrast"]) >= 2.0:
            return float(np.median([x["all"]["s"], x["near"]["s"], x["far"]["s"]]))
        return x["all"]["s"]
    s = np.array([best(x) for x in sol])
    known = np.isfinite(s)
    idx = np.arange(T)
    s_filled = np.interp(idx, idx[known], s[known]) if known.any() else np.zeros(T)
    # a single wild frame (edges that fit two places) is replaced by its neighbours' median for the tables
    med = np.array([np.median(s_filled[max(0, i - 2):i + 3]) for i in range(T)])
    typical_step = float(np.median(np.abs(np.diff(s_filled)))) if T > 1 else 0.0
    wild = np.abs(s_filled - med) > max(0.12, 2.0 * typical_step)
    s_table = np.where(wild, med, s_filled)

    # 1 parallax: sizes of the near and of the far structure against the plan at the frame's position
    dev_near, dev_far = [], []
    for x in sol:
        if x["all"] is None or x.get("near") is None or x.get("far") is None:
            dev_near.append(None)
            dev_far.append(None)
            continue
        sa, sn, sf, dn, df = x["all"]["s"], x["near"]["s"], x["far"]["s"], x["d_near"], x["d_far"]
        # d_near / d_far are depths from the camera at sa; a structure at depth d seen from s' has size ~ 1 / (d + sa - s')
        if dn < 0.5 or (df - dn) < 0.2 * dn or min(x["near"]["contrast"], x["far"]["contrast"]) < 2.0:
            # too close to the near structure, no depth difference to speak of, or a half whose edges do not pin the
            # position down (its best fit is hardly better than its typical fit)
            dev_near.append(None)
            dev_far.append(None)
            continue
        dev_near.append(float(dn / max(0.05, dn + sa - sn) - 1.0))
        dev_far.append(float(df / max(0.05, df + sa - sf) - 1.0))
    both = [max(abs(a), abs(b)) for a, b in zip(dev_near, dev_far) if a is not None]
    par = dict(frames_measured=len(both), p90_abs=float(np.percentile(both, 90)) if both else None,
               median_abs=float(np.median(both)) if both else None, max_abs=float(max(both)) if both else None)

    # 2 dissolve
    r2 = dissolve_r2(frames)
    mid = r2[int(T * 0.25):max(int(T * 0.25) + 1, int(T * 0.75))]
    dis = dict(r2_mid_median=float(np.median(mid)), r2_mid_max=float(np.max(mid)))
    zr = flat_zoom_r2(frames, R.cam0)
    dis["flat_zoom_r2_mid_median"] = float(np.median(zr)) if zr else None

    # 3 progress
    ds = np.diff(s_table)
    img_change = np.array([float(np.abs(grays[t].astype(np.int16) - grays[t - 1].astype(np.int16)).mean()) for t in range(1, T)])
    typical = float(np.median(img_change)) + 1e-6
    stall = (np.abs(ds) < 0.002 * L) & (img_change > 0.5 * typical)
    stall[:2] = False
    stall[-2:] = False
    jump = float(np.max(np.abs(ds))) / L if len(ds) else 0.0
    prog = dict(start_m=float(s_table[0]), end_m=float(s_table[-1]), length_m=L, back_steps=int((ds < -limits["back_m"]).sum()),
                worst_back_m=float(min(0.0, ds.min())) if len(ds) else 0.0, stall_frac=float(stall.mean()) if len(ds) else 0.0,
                largest_step_frac=jump, wild_frames=int(wild.sum()), unknown_frames=int((~known).sum()),
                speed_max_over_median=float(np.max(ds) / max(1e-6, np.median(ds))) if len(ds) else None)

    # structure residual at the best s
    cst = [x["all"]["cost_w"] for x in sol if x["all"] is not None]
    res = dict(median_w=float(np.median(cst)) if cst else None, p90_w=float(np.percentile(cst, 90)) if cst else None)
    ver = verticals(frames)

    fails, defects = [], []
    if dis["r2_mid_median"] > limits["dissolve_r2"]:
        fails.append(f"dissolve: the middle frames are a mix of the end frames (R2 {dis['r2_mid_median']:.2f} > {limits['dissolve_r2']})")
    if dis["flat_zoom_r2_mid_median"] is not None and dis["flat_zoom_r2_mid_median"] > limits["dissolve_r2"] and dis["r2_mid_median"] <= limits["dissolve_r2"]:
        fails.append(f"flat zoom: the middle frames are the first frame enlarged as one flat picture (R2 {dis['flat_zoom_r2_mid_median']:.2f} > "
                     f"{limits['dissolve_r2']}): no parallax, not a walk")
    if par["p90_abs"] is not None and par["p90_abs"] > limits["parallax_dev"]:
        fails.append(f"parallax: near and far structure are up to {par['p90_abs']:.0%} off the sizes the plan gives them (limit 5 %): a zoom, not a walk")
    if prog["stall_frac"] > limits["stall_frac"]:
        fails.append(f"the picture changes on {prog['stall_frac']:.0%} of the frames while the camera does not advance: a morph")
    if jump > limits["jump_frac"]:
        fails.append(f"the camera jumps {jump:.0%} of the line between two frames: not a continuous move")
    if par["frames_measured"] < max(6, T // 10):
        defects.append("parallax could be measured on few frames (near and far structure too close in depth): judge by eye too")
    if prog["back_steps"] > 0:
        defects.append(f"the camera steps back {prog['back_steps']} times (worst {prog['worst_back_m']:.2f} m)")
    if abs(prog["end_m"] - L) > 0.05 * L or abs(prog["start_m"]) > 0.05 * L:
        defects.append(f"the clip runs from {prog['start_m']:.2f} m to {prog['end_m']:.2f} m of a {L:.2f} m line")
    if ver.get("max_abs_median_deg") is not None and ver["max_abs_median_deg"] > limits["vertical_deg"]:
        defects.append(f"verticals lean up to {ver['max_abs_median_deg']:.2f} deg (limit 0.5)")
    if res["p90_w"] is not None and res["p90_w"] > limits["structure_w"] * 0.5:
        defects.append(f"structure lines sit up to {res['p90_w']:.2%} of the width from the frame's edges (the chamfer truncates at {TRUNC:.1%}; QA limit 1 %)")
    verdict = "NOT A WALK" if fails else ("WALK, WITH DEFECTS" if defects else "WALK")
    return dict(verdict=verdict, fails=fails, defects=defects, frames=T, size=[w, h], length_m=L, parallax=par, dissolve=dis,
                progress=prog, structure_residual=res, verticals=ver,
                s_per_frame=[None if not np.isfinite(x) else round(float(x), 4) for x in s],
                s_filled=[round(float(x), 4) for x in s_table],
                detail=dict(dev_near=[None if x is None else round(x, 4) for x in dev_near],
                            dev_far=[None if x is None else round(x, 4) for x in dev_far],
                            s_near=[None if x.get("near") is None else round(x["near"]["s"], 4) for x in sol],
                            s_far=[None if x.get("far") is None else round(x["far"]["s"], 4) for x in sol],
                            cost_w=[None if x["all"] is None else round(x["all"]["cost_w"], 5) for x in sol],
                            structure_points_in_frame=[x.get("n") for x in sol]),
                limits=limits, stations_at_m=[round(float(x), 3) for x in R.at])


# ----------------------------------------------------------------------------------------------------------------
# the two known failures, built from the end frames (to test the test)
# ----------------------------------------------------------------------------------------------------------------
def parse_exclude(x: str) -> tuple[int, float, float]:
    """'50:1.0-1.8' -> (50, 1.0, 1.8)."""
    cid, rng = x.split(":")
    a, b = rng.split("-")
    return int(cid), float(a), float(b)


def load_events(spec: str) -> list[dict]:
    """jobs.json:clip1a (that job's walk_events) or a JSON file holding a list of events."""
    path, _, job = spec.partition(":")
    data = json.load(open(path))
    if isinstance(data, dict):
        jobs = {j["id"]: j for j in data.get("jobs", [])}
        if job not in jobs:
            raise SystemExit(f"no job {job!r} in {path}")
        return jobs[job].get("walk_events", [])
    return data


def events_report(events: list[dict], s_table: list[float]) -> list[dict]:
    """For each event, the clip frames (1-based) where the solved position reaches it: `at_m` -> the first frame at
    or past it; `window_m` [a, b] -> the frames inside the window. The eye check at 100 % looks there."""
    s = np.asarray(s_table, np.float64)
    out = []
    for e in events:
        r = dict(what=e.get("what"))
        if "window_m" in e:
            a, b = e["window_m"]
            idx = np.nonzero((s >= a) & (s <= b))[0]
            r.update(window_m=[a, b], frames=[int(idx[0]) + 1, int(idx[-1]) + 1] if len(idx) else None)
        else:
            idx = np.nonzero(s >= e["at_m"])[0]
            r.update(at_m=e["at_m"], frame=int(idx[0]) + 1 if len(idx) else None)
        if "check" in e:
            r["check"] = e["check"]
        out.append(r)
    return out


def fake_dissolve(first: np.ndarray, last: np.ndarray, n: int) -> list[np.ndarray]:
    a, b = first.astype(np.float32), last.astype(np.float32)
    out = []
    for i in range(n):
        t = i / (n - 1)
        t = t * t * (3 - 2 * t)
        out.append(np.clip(a * (1 - t) + b * t + 0.5, 0, 255).astype(np.uint8))
    return out


def fake_zoom(first: np.ndarray, last: np.ndarray, n: int, cam0: cg.Cam, k_end: float = 3.2) -> list[np.ndarray]:
    """The picture grows as one flat sheet about the vanishing point (door frame and room at the same rate), and the
    last third melts into the last frame."""
    h, w = first.shape[:2]
    cx, cy = cam0.u0 * w, cam0.v0 * h
    b = last.astype(np.float32)
    out = []
    for i in range(n):
        t = i / (n - 1)
        k = k_end ** t
        M = np.array([[k, 0, cx * (1 - k)], [0, k, cy * (1 - k)]], np.float32)
        z = cv2.warpAffine(first, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        m = float(np.clip((t - 0.67) / 0.33, 0, 1))
        m = m * m * (3 - 2 * m)
        out.append(np.clip(z * (1 - m) + b * m + 0.5, 0, 255).astype(np.uint8))
    return out


def write_frames(frames: list[np.ndarray], out_dir: str, ext: str = "jpg") -> None:
    os.makedirs(out_dir, exist_ok=True)
    for i, f in enumerate(frames):
        cv2.imwrite(os.path.join(out_dir, f"{i + 1:04d}.{ext}"), cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])


def proxy_ruler(route: str, n_stations: int = 12, w: int = 960) -> Ruler:
    """The ruler of a route from the proxy house (stations with exact depth and structure edges), for the selftests."""
    import proxy_house as ph
    c0, c1 = ROUTES[route]
    fr = cg.Canvas.frame(w)
    clouds, at = [], []
    L = float(np.linalg.norm(np.asarray(c1.loc) - np.asarray(c0.loc)))
    for k in range(n_stations):
        cam = cg.lerp_cam(c0, c1, k / (n_stations - 1))
        _, dep, e = ph.render(cam, fr, "open", edges=True)
        clouds.append(cloud(dep, e, cam, fr))
        at.append(L * k / (n_stations - 1))
    return Ruler(c0, c1, clouds, at)


def model_like_walk(route: str, n: int, w: int = 960, seed: int = 3):
    """An exact proxy walk as a model would return it: uneven speed, a little flicker and grain. Returns (frames, s)."""
    import proxy_house as ph
    c0, c1 = ROUTES[route]
    fr = cg.Canvas.frame(w)
    rng = np.random.default_rng(seed)
    ts = np.linspace(0, 1, n)
    prog = ts + 0.11 * np.sin(2 * np.pi * ts) * (1 - ts) - 0.05 * np.sin(3 * np.pi * ts) * ts * (1 - ts)
    prog = np.clip(np.maximum.accumulate(prog), 0, 1)
    prog[-1] = 1.0
    frames = []
    for p in prog:
        rgb, _ = ph.render(cg.lerp_cam(c0, c1, float(p)), fr, "open")
        rgb = rgb * (1 + rng.normal(0, 0.006)) + rng.normal(0, 0.004, rgb.shape).astype(np.float32)
        frames.append(np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8))
    L = float(np.linalg.norm(np.asarray(c1.loc) - np.asarray(c0.loc)))
    return frames, prog * L


def selftest(out_dir: str, w: int = 960, n: int = 61, keep_frames: bool = False) -> dict:
    """An exact walk from the proxy house at an UNEVEN speed, with model-like flicker, must come out WALK. A dissolve
    and a flat zoom between the same two end frames must come out NOT A WALK. For both clips of the arrival."""
    os.makedirs(out_dir, exist_ok=True)
    rep = {}
    for route in ("clip2", "clip1"):
        R = proxy_ruler(route, 12, w)
        walk, s_true = model_like_walk(route, n, w)
        clips = dict(walk=walk, dissolve=fake_dissolve(walk[0], walk[-1], n), zoom=fake_zoom(walk[0], walk[-1], n, ROUTES[route][0]))
        rep[route] = {}
        for name, fs in clips.items():
            r = walk_test(fs, R)
            if name == "walk":
                err = np.abs(np.array(r["s_filled"]) - s_true)
                r["progress_error_m"] = dict(mean=float(err.mean()), p90=float(np.percentile(err, 90)), max=float(err.max()))
            rep[route][name] = {k: v for k, v in r.items() if k not in ("detail", "s_per_frame", "s_filled", "limits")}
            if keep_frames:
                write_frames(fs[::4], os.path.join(out_dir, f"{route}-{name}-every4"))
        rep[route]["as_expected"] = bool(rep[route]["walk"]["verdict"].startswith("WALK") and
                                         rep[route]["dissolve"]["verdict"] == "NOT A WALK" and rep[route]["zoom"]["verdict"] == "NOT A WALK")
    rep["limits"] = LIMITS
    with open(os.path.join(out_dir, "walk-test-selftest.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("test")
    t.add_argument("--frames", required=True)
    t.add_argument("--route", required=True, choices=sorted(ROUTES), help="the straight move of the clip")
    t.add_argument("--stations", required=True, help="folder of clay frames with -depth.png and -edges.png passes")
    t.add_argument("--ids", required=True, help="comma list of station ids, in path order")
    t.add_argument("--line", default=None, choices=sorted(ROUTES), help="the line the stations sit on at even distance (default: the route)")
    t.add_argument("--line-count", type=int, default=None, help="how many stations the line has in all (default: the number of ids)")
    t.add_argument("--line-first", type=int, default=0, help="the index on the line of the first id (b/S02 of 12 stations: 2)")
    t.add_argument("--canvas", default="base", choices=["base", "tall", "frame"], help="the canvas of the station passes")
    t.add_argument("--w", type=int, default=960)
    t.add_argument("--exclude", action="append", default=[], metavar="ID:A-B",
                   help="clay id ID takes no part in the fit while the position is A-B metres from the route start (repeatable)")
    t.add_argument("--events", default=None, metavar="FILE[:JOB]",
                   help="event table: jobs.json with the job id (its walk_events), or a JSON list of events")
    t.add_argument("--out", required=True)
    f = sub.add_parser("fakes")
    f.add_argument("--first", required=True)
    f.add_argument("--last", required=True)
    f.add_argument("--route", default="clip2", choices=sorted(ROUTES))
    f.add_argument("--n", type=int, default=121)
    f.add_argument("--out", required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=61)
    s.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "test":
        frames = read_frames(a.frames, a.w)
        c0, c1 = ROUTES[a.route]
        l0, l1 = ROUTES[a.line or a.route]
        ids = a.ids.split(",")
        vec = np.asarray(c1.loc) - np.asarray(c0.loc)
        L = float(np.linalg.norm(vec))
        clouds, at, labs = [], [], []
        excl = [parse_exclude(x) for x in a.exclude]
        n_line = a.line_count or len(ids)
        for k, fid in enumerate(ids):
            cam = cg.lerp_cam(l0, l1, (a.line_first + k) / (n_line - 1))
            if excl:
                P, lab = load_station(a.stations, fid, cam, a.canvas, with_ids=True)
                clouds.append(P)
                labs.append(lab)
            else:
                clouds.append(load_station(a.stations, fid, cam, a.canvas))
            at.append(float((np.asarray(cam.loc) - np.asarray(c0.loc)) @ (vec / L)))
        rep = walk_test(frames, Ruler(c0, c1, clouds, at, labs if excl else None, excl))
        if excl:
            rep["excluded"] = [dict(id=i, from_m=x, to_m=y) for i, x, y in excl]
        if a.events:
            rep["events"] = events_report(load_events(a.events), rep["s_filled"])
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump(rep, fh, indent=1)
        print(json.dumps({k: v for k, v in rep.items() if k not in ("detail", "s_per_frame", "s_filled")}, indent=1))
        return 0 if rep["verdict"].startswith("WALK") else 3
    if a.cmd == "fakes":
        A = cv2.cvtColor(cv2.imread(a.first), cv2.COLOR_BGR2RGB)
        B = cv2.cvtColor(cv2.imread(a.last), cv2.COLOR_BGR2RGB)
        B = cv2.resize(B, (A.shape[1], A.shape[0]), interpolation=cv2.INTER_AREA)
        write_frames(fake_dissolve(A, B, a.n), os.path.join(a.out, "dissolve"))
        write_frames(fake_zoom(A, B, a.n, ROUTES[a.route][0]), os.path.join(a.out, "zoom"))
        return 0
    if a.cmd == "selftest":
        rep = selftest(a.out, n=a.n, keep_frames=a.keep_frames)
        print(json.dumps(rep, indent=1))
        return 0 if all(rep[r]["as_expected"] for r in ("clip1", "clip2")) else 4
    return 1


if __name__ == "__main__":
    sys.exit(main())
