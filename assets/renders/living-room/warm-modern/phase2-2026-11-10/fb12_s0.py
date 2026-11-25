#!/usr/bin/env python3
"""
fb12_s0.py: FB12 stage 0, the clean M0 plate without the old coffee table (render-agent, 2026-11-25).
Brief: briefs/wm-fb12-stage0-clean-plate-2026-11-25.md; spec: docs/proposals/wm-fb12-2026-11-25.md sections a.5-a.7 (path R).
Code only: 0 tokens, no var2, no network. NEW FILES ONLY: every phase-1 / phase-2 file is read, never written.

The plate is rebuilt in phase 1's own ungraded model and graded with the ONE v3c grade (stack.Grade, base.png byte for byte):
    U = shell_v3 x S x (1 - fa) + F x fa                     (pilot-phase1/shell_fix_v3.py: shell-furniture-v3.png)
  * fa / F: the old table leaves the fixed-furniture layer. fa' = the sofa and the armchair only. Where the table hid the sofa
    (the lower strip of the sofa front: the deck rail's lower part, the upholstered base band, the recessed walnut plinth, the left
    arm's foot) the sofa is synthesised in the sofa-front plane (Y 0.95, the M0 1.2 camera of docs/house-plan.json), from its own
    visible sides: the band profile from the strip right of the table, the light along X from the rail visible above the table,
    the boucle grain in row-aligned strips of that same band (random offsets, min-cut seams), its contrast per column matched to the
    boucle visible above the table (the window side is brighter and flatter).
  * shell: the shell v3 is the empty-room render; under the table it is the real parquet in the same light (board lines are the
    render's own, so they run straight through: checked against the floor homography).
  * S: the code furniture shadow loses the table's part: S' = M inside the table's footprint, and S + w max(0, M - S) around it
    (w = 1 over the table's zone, feathered out at X -0.75..-0.65 and X 1.15..1.35), M = the sofa's own contact / AO model fitted to
    S right of the table (its front, k(X) ramp: S has no AO at the window end).
  * outside the changed region the plate is base.png's own bytes (RND2 0).
Then (same run):
  * the rug layer: whole under the old table. In the rug plane (Z 0.012, 900 px/m): where the table hid the rug, or its shadow sat on
    the rug (gain > 1.15), the grain is hole-filled by quilting from the visible rug (blocks of the same depth band and, where there
    are enough, the same side within 0.6 m, since the rendered braid size drifts; 1 - NCC choice; min-cut seams); its colour and
    level: the room's light (the shell, board scale out) x S' x the rug's own ratio carried in from around the zone; faint shadow is
    relit (x LFt / LF); the back edge left of the sofa copied along X; alpha = the rug's footprint (back edge Y 0.777, left X -1.45)
    x (1 - fa'); the rug's edge shadow extended along that edge.
  * the cushion sets: inside the old table's region only, the throw's darkening of the sofa is carried in (fades over 40 px) and the
    set's shadow on the old table top becomes its own continuation; every R9 pixel outside the region is kept.
  * the defaults (sets B / A / C): the 8-bit stack of the new manifest (bowl and candle holders hidden) where the stack changed, the
    R8 truths' own bytes elsewhere; the QA sheet; the records (manifest-fb12s0.json, the motion note, the asset entries).
"""
import hashlib
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/homedesign-app"
LR = os.path.join(REPO, "assets/renders/living-room/warm-modern")
P1 = os.path.join(LR, "pilot-phase1-2026-11-07")
P2 = os.path.join(LR, "phase2-2026-11-10")
LAY = os.path.join(P2, "layers")
OUT = os.environ.get("FB12_OUT", P2)                 # the phase-2 folder (new files only); a scratch folder while developing
WORK = os.path.join(OUT, "work-fb12s0")
LAY_OUT = os.path.join(OUT, "layers")                # new layer files and records go here (= LAY in the repo run)
MASKS = os.path.join(WORK, "fb12s0-masks.npz")      # the r4 clay index split (sofa / table / armchair) at the work size
W, H = 2720, 1530
CANVAS = (4072, 2290)
RNG = np.random.default_rng(20261125)
TAG = "fb12s0"


# ------------------------------------------------------------------------------------------------- io
def f8(p, mode=None):
    im = Image.open(p)
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(np.float32) / 255.0


def u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def l2s(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055).astype(np.float32)


def lum(lin):
    return (lin * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, REPO)


# ------------------------------------------------------------------------------------------------- geometry (M0 1.2)
PLAN = json.load(open(os.path.join(REPO, "docs/house-plan.json")))
CAM = next(c for c in PLAN["cameras"] if c["id"] == "M0")


def project(X, Y, Z):
    """docs/house-plan.json camera M0 (QA's clay_wm_r1.project), to work px on the 2720 x 1530 overscan canvas"""
    a = math.radians(CAM["yaw_deg_left"])
    fwd = np.array([-math.sin(a), -math.cos(a), 0.0])
    right = np.array([math.cos(a), -math.sin(a), 0.0])
    p = np.array([X, Y, Z], np.float64) - np.array(CAM["loc"], np.float64)
    d = float(p @ fwd)
    fx = CAM.get("lens", 24) / 36.0
    fy = fx * 16 / 9
    u = CAM["u0"] + fx * float(p @ right) / d
    v = CAM["v0"] - fy * float(p[2]) / d
    return (116 + u * 3840) * W / CANVAS[0], (65 + v * 2160) * H / CANVAS[1]


def plane_H(kind, c):
    """homography plane coords -> work px. kind 'z': the horizontal plane Z = c, coords (X, Y); kind 'y': the vertical plane
    Y = c, coords (X, Z)"""
    src = np.array([[-2, 0.0], [2, 0.0], [2, 3.5], [-2, 3.5]]) if kind == "z" else np.array([[-2, 0.0], [2, 0.0], [2, 1.0], [-2, 1.0]])
    pts = [(x, y, c) if kind == "z" else (x, c, y) for x, y in src]
    dst = np.array([project(*p) for p in pts])
    return cv2.findHomography(src, dst)[0]


def rect_A(ppm, x0, y0, flip=False):
    """rect px -> plane coords (y down unless flip: then row 0 = y0 and coordinates decrease)"""
    return np.array([[1 / ppm, 0, x0], [0, (-1 if flip else 1) / ppm, y0], [0, 0, 1]], np.float64)


def img_to_plane(Hm):
    Hi = np.linalg.inv(Hm)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    P = np.stack([xx, yy, np.ones_like(xx)], -1) @ Hi.T
    return (P[..., 0] / P[..., 2]).astype(np.float32), (P[..., 1] / P[..., 2]).astype(np.float32)


H_FLOOR = plane_H("z", 0.0)
SOFA_Y = 0.95                         # the sofa front plane (sofa 220 x 92 x 78, Y 0.03-0.95, house plan / clay r4)
H_SOFA = plane_H("y", SOFA_Y)
# the sofa-front rect: 560 px/m, X -1.0..1.4 (cols), Z 0.6..0.0 (rows)
SR_PPM, SR_X0, SR_Z1, SR_W, SR_H = 560, -1.0, 0.6, 1344, 336
SR_M = H_SOFA @ rect_A(SR_PPM, SR_X0, SR_Z1, flip=True)


def sr_warp(a, interp=cv2.INTER_CUBIC):
    return cv2.warpPerspective(a, SR_M, (SR_W, SR_H), flags=cv2.WARP_INVERSE_MAP | interp, borderMode=cv2.BORDER_REPLICATE)


def sr_back(a, interp=cv2.INTER_CUBIC):
    return cv2.warpPerspective(a, SR_M, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


# measured on the render (rect rows / cols of the sofa-front rect; see plate() record): the band rows and the ends
SOFA = dict(seat_crease=165.0, rail_crease=249.0, base_bottom=302.0, plinth_bottom=329.5, arm_left_edge=62.0, base_left_end=54.5,
            plinth_left_end=79.5, corner_rows=(246.0, 253.0), junction_left=142, ref_cols=(1088, 1200), base_ref_cols=(1088, 1280), plinth_ref_cols=(1088, 1255),
            plinth_Y=0.911)


# ------------------------------------------------------------------------------------------------- the masks
def masks():
    z = np.load(MASKS)
    return {k: z[k].astype(np.float32) / 255.0 for k in ("sofa", "table", "armchair")}


def table_region(m):
    """the old table's region in the picture: the clay table, dilated 4 px (covers the furniture alpha's +-3 px snap ring)"""
    return cv2.dilate((m["table"] > 0.005).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)


# ------------------------------------------------------------------------------------------------- the shadow S'
G_CONTACT = np.array([(0.0, 0.50), (0.01, 0.505), (0.02, 0.52), (0.03, 0.55), (0.04, 0.585), (0.05, 0.63), (0.06, 0.69), (0.07, 0.75),
                      (0.08, 0.80), (0.09, 0.845), (0.10, 0.875), (0.11, 0.895), (0.12, 0.92), (0.13, 0.93), (0.14, 0.945), (0.16, 0.96),
                      (0.18, 0.975), (0.20, 0.985), (0.25, 1.0)], np.float32)
PLINTH_RECT = (-0.855, 1.255, 0.03, SOFA["plinth_Y"])


def sofa_model(X, Y):
    """M: the sofa's own floor shadow in front (the plateau right of the table, 0.91, is the table's penumbra and is divided out).
    Two parts: the contact under the base band's 4 cm overhang (always), and the AO tail, ramped along X (S has none at the
    window end: S = 1.000 at X -1.10..-0.86, Y 0.75..1.10)."""
    x0, x1, y0, y1 = PLINTH_RECT
    d = np.hypot(np.maximum(np.maximum(x0 - X, X - x1), 0), np.maximum(np.maximum(y0 - Y, Y - y1), 0))
    g = np.interp(d, G_CONTACT[:, 0], G_CONTACT[:, 1]).astype(np.float32)
    gc = (1 - 0.40 * np.exp(-d / 0.012)).astype(np.float32)              # the overhang contact (d < ~3 cm)
    gt = np.clip(g / np.maximum(gc, 1e-3), 0, 1)                         # the tail
    k = np.clip((X + 0.90) / 1.85, 0, 1) ** 1.0                          # 0 at the window end, 1 from X 0.95 (fitted there)
    return (gc * (1 - k * (1 - gt))).astype(np.float32)


def shadow_prime(S, T, X, Y):
    M = sofa_model(X, Y)
    wl = np.clip((X + 0.75) / 0.10, 0, 1)
    wr = np.clip((1.35 - X) / 0.20, 0, 1)
    wy = np.clip((Y - (SOFA["plinth_Y"] - 0.02)) / 0.02, 0, 1) * np.clip((2.45 - Y) / 0.10, 0, 1)
    w = (wl * wr * wy).astype(np.float32)
    Sp = S + w * np.maximum(0, M - S)
    Sp = np.where(T, M, Sp)
    return Sp.astype(np.float32), M, w


# ------------------------------------------------------------------------------------------------- texture helpers
def nblur(x, k, sig):
    """normalised Gaussian blur of x over the weight k"""
    if x.ndim == 3:
        return np.dstack([nblur(x[..., c], k, sig) for c in range(x.shape[2])])
    return cv2.GaussianBlur(x * k, (0, 0), sig) / np.maximum(cv2.GaussianBlur(k, (0, 0), sig), 1e-6)


def mincut_v(err):
    """min-cost vertical path through err (h x w): returns per row the column where the new patch starts"""
    h, w = err.shape
    E = err.copy()
    for i in range(1, h):
        prev = E[i - 1]
        left = np.r_[np.inf, prev[:-1]]
        right = np.r_[prev[1:], np.inf]
        E[i] += np.minimum(np.minimum(left, prev), right)
    path = np.zeros(h, int)
    path[-1] = int(np.argmin(E[-1]))
    for i in range(h - 2, -1, -1):
        j = path[i + 1]
        lo, hi = max(0, j - 1), min(w, j + 2)
        path[i] = lo + int(np.argmin(E[i, lo:hi]))
    return path


# ------------------------------------------------------------------------------------------------- the plate
def sofa_silhouette_rect(xr, yr):
    """the sofa's full silhouette in the sofa-front rect (left part; the right part is never hidden): 1 inside"""
    s = SOFA
    c0, c1 = s["corner_rows"]                                         # the base band's rounded top-left corner (measured, 50 % alpha)
    t = np.clip((yr - c0) / (c1 - c0), 0, 1)
    xl = np.where(yr < c0, s["arm_left_edge"], np.where(yr < s["base_bottom"], s["arm_left_edge"] + (s["base_left_end"] - s["arm_left_edge"]) * t,
                                                         s["plinth_left_end"]))
    return ((yr <= s["plinth_bottom"]) & (xr >= xl)).astype(np.float32)


def sil_image(T):
    """the sofa silhouette at work px, 4 x 4 supersampled, then softened to the furniture alpha's own edge (sigma 1.1 px)"""
    Hi = np.linalg.inv(SR_M)
    ys, xs = np.nonzero(cv2.dilate(T.astype(np.uint8), np.ones((15, 15), np.uint8)))
    cov = np.zeros((H, W), np.float32)
    acc = np.zeros(len(xs), np.float32)
    for oy in (0.125, 0.375, 0.625, 0.875):
        for ox in (0.125, 0.375, 0.625, 0.875):
            P = np.stack([xs - 0.5 + ox, ys - 0.5 + oy, np.ones(len(xs))], -1) @ Hi.T
            acc += sofa_silhouette_rect(P[:, 0] / P[:, 2], P[:, 1] / P[:, 2])
    cov[ys, xs] = acc / 16
    return cv2.GaussianBlur(cov, (0, 0), 1.1)


def plate():
    os.makedirs(WORK, exist_ok=True)
    m = masks()
    T = table_region(m)
    shell = f8(os.path.join(P1, "shell-v3.png"), "RGB")
    Fl = f8(os.path.join(P1, "fixed-furniture.png"))
    F, fa = Fl[..., :3], Fl[..., 3]
    S = f8(os.path.join(P1, "fixed-furniture-shadow.png"), "L")
    U8 = np.asarray(Image.open(os.path.join(P1, "shell-furniture-v3.png")).convert("RGB"))
    X, Y = img_to_plane(H_FLOOR)
    rec = dict()

    # --- S'
    Sp, M, w = shadow_prime(S, T, X, Y)
    rec["shadow"] = dict(model="sofa_model(): contact under the overhang + AO tail ramped along X; S' = M in the table region, "
                               "S + w max(0, M - S) around it", px_changed=int((np.abs(Sp - S) > 0.5 / 255).sum()))

    # --- the sofa strip, in the sofa-front rect (linear light)
    s = SOFA
    Fr = s2l(sr_warp(F))
    Tr = sr_warp(T.astype(np.float32), cv2.INTER_LINEAR) > 0.01
    rows = np.arange(SR_H)
    r0 = np.array([int(np.argmax(Tr[:, x])) if Tr[:, x].any() else SR_H for x in range(SR_W)])
    rc0, rc1 = s["ref_cols"]
    P = Fr[:, rc0:rc1].mean(1)                                        # the band profile (RGB per row), right of the table
    bc0, bc1 = s["base_ref_cols"]
    P[int(s["rail_crease"]) - 1:int(s["base_bottom"]) + 1] = Fr[int(s["rail_crease"]) - 1:int(s["base_bottom"]) + 1, bc0:bc1].mean(1)
    pc0, pc1 = s["plinth_ref_cols"]
    P[int(s["base_bottom"]) + 1:] = Fr[int(s["base_bottom"]) + 1:, pc0:pc1].mean(1)
    Lr = lum(Fr)
    Lp = lum(P)
    # the light along X: the rail rows visible above the table (169 .. the table's own edge - 2)
    Tt = sr_warp(m["table"], cv2.INTER_LINEAR) > 0.5
    rt = np.array([int(np.argmax(Tt[:, x])) if Tt[:, x].any() else SR_H for x in range(SR_W)])
    g = np.full(SR_W, np.nan, np.float32)
    for x in range(SR_W):
        y1 = min(rt[x] - 2, int(s["rail_crease"]) - 4)
        if y1 - 169 >= 5 and x >= s["junction_left"] - 4:
            g[x] = Lr[169:y1, x].mean() / Lp[169:y1].mean()
    valid = np.isfinite(g) & (np.arange(SR_W) < rc1)
    gx = np.where(valid, g, 0).astype(np.float32)
    vf = valid.astype(np.float32)
    gs = cv2.GaussianBlur(gx[None], (0, 0), 14)[0] / np.maximum(cv2.GaussianBlur(vf[None], (0, 0), 14)[0], 1e-6)
    gs3 = cv2.GaussianBlur(gx[None], (0, 0), 2.5)[0] / np.maximum(cv2.GaussianBlur(vf[None], (0, 0), 2.5)[0], 1e-6)
    xs_ = np.arange(SR_W)
    t = np.clip((xs_ - 170) / 40.0, 0, 1)                            # the rail's lit left end keeps its own per-column light
    gs = np.where(valid, gs3 * (1 - t) + gs * t, gs)
    xv = np.nonzero(valid)[0]
    lo = xv.min()
    gs[:lo] = gs[lo]                                                  # left of the rail (the arm's foot): the rail's end value
    gs[rc1:] = 1.0
    # the colour and level right at the seam: RGB over the 6 rows just above the table's edge / the band profile there, per column
    grgb = np.full((SR_W, 3), np.nan, np.float32)
    for x in range(SR_W):
        y1 = min(rt[x] - 2, int(s["rail_crease"]) - 4)
        if y1 - 169 >= 5 and x >= s["junction_left"] - 4 and x < rc1:
            ya = max(169, y1 - 6)
            grgb[x] = Fr[ya:y1, x].mean(0) / np.maximum(P[ya:y1].mean(0), 1e-4)
    okg = np.isfinite(grgb[:, 0])
    gz = np.where(okg[:, None], grgb, 0)
    den = cv2.GaussianBlur(okg.astype(np.float32)[None], (0, 0), 10)[0]
    for c in range(3):
        grgb[:, c] = cv2.GaussianBlur(gz[:, c][None].astype(np.float32), (0, 0), 10)[0] / np.maximum(den, 1e-6)
    xg = np.nonzero(okg)[0]
    grgb[:xg.min()] = grgb[xg.min()]
    grgb[rc1:] = 1.0
    t_r = np.clip((rc0 - np.arange(SR_W)) / 60.0, 0, 1)[:, None]          # to 1 at the reference (the visible right part)
    grgb = grgb * t_r + 1.0 * (1 - t_r)
    rec["light_along_x"] = dict(gain_at={str(x): round(float(gs[x]), 3) for x in (60, 100, 150, 300, 500, 700, 900, 1050, 1100)},
                                 note="gs: the contrast measure's light; the colour and level of the fill: grgb (the 6 rows above the table's edge)",
                                 method="rail rows 169..r0-5 / the band profile, Gaussian 14 px; left of the rail: linear trend of its first 80 cols")

    # --- the boucle grain: row-aligned strips of the band itself (right of the table), min-cut seams, random offsets and mirrors;
    #     its contrast scaled per column to the boucle visible above the table there (the window side is brighter and flatter)
    qw = rc0 + 24
    HFs = np.ones((SR_H, SR_W), np.float32)
    rt_ = np.minimum(rt, int(s["rail_crease"]) - 4)
    sig_v = np.full(SR_W, np.nan, np.float32)
    for x in range(s["junction_left"], qw):
        y1 = rt_[x] - 2
        if y1 - 169 >= 5:
            blk = Lr[169:y1, max(0, x - 12):x + 13] / (Lp[169:y1, None] * gs[max(0, x - 12):x + 13][None])
            sig_v[x] = float(blk.std())
    okv = np.isfinite(sig_v)
    sv = np.where(okv, sig_v, 0)
    sig_s = cv2.GaussianBlur(sv[None], (0, 0), 20)[0] / np.maximum(cv2.GaussianBlur(okv.astype(np.float32)[None], (0, 0), 20)[0], 1e-6)
    xs_ok = np.nonzero(okv)[0]
    sig_s[:xs_ok.min()] = sig_s[xs_ok.min()]
    sig_s[xs_ok.max() + 1:] = sig_s[xs_ok.max()]
    bands = [("rail", 166, int(s["rail_crease"]) - 1, (rc0, 1196)), ("base", int(s["rail_crease"]) - 1, int(s["base_bottom"]) + 2, (bc0, 1282))]
    rec_bands = {}
    for name, ya, yb, (ca, cb) in bands:
        ref = Lr[ya:yb, ca:cb] / np.maximum(Lp[ya:yb, None], 1e-4)
        cprof = cv2.GaussianBlur(ref.mean(0)[None].astype(np.float32), (0, 0), 10)[0]
        hf_ref = ref / cprof[None]
        sig_ref = float(hf_ref[3:-3].std())
        out = np.ones((yb - ya, qw), np.float32)
        xw, o = 0, 8
        n_strips = 0
        while xw < qw:
            bw = int(RNG.integers(26, 41))
            best = None
            for _ in range(60):
                sx = int(RNG.integers(0, hf_ref.shape[1] - bw))
                blk = hf_ref[:, sx:sx + bw]
                e = 0.0 if xw == 0 else float(((blk[:, :o] - out[:, xw - o:xw]) ** 2).sum())
                if best is None or e < best[0]:
                    best = (e, blk)
            blk = best[1]
            n = min(bw, qw - xw + (o if xw else 0))
            if xw == 0:
                out[:, :bw] = blk[:, :min(bw, qw)]
                xw = bw
            else:
                x0 = xw - o
                e = (blk[:, :o] - out[:, x0:xw]) ** 2
                path = mincut_v(e)
                for i in range(out.shape[0]):
                    c0 = x0 + path[i]
                    c1 = min(qw, x0 + bw)
                    out[i, c0:c1] = blk[i, path[i]:path[i] + (c1 - c0)]
                xw = x0 + bw
            n_strips += 1
        k = (sig_s[:qw] / sig_ref)[None]
        HFs[ya:yb, :qw] = 1 + (out - 1) * k
        rec_bands[name] = dict(rows=[ya, yb], ref_cols=[ca, cb], strips=n_strips, sigma_ref=round(sig_ref, 3))
    rec_bands["contrast_target"] = {str(x): round(float(sig_s[x]), 3) for x in (150, 300, 500, 700, 900, 1050)}
    # the walnut plinth: full-height column blocks of the plinth itself (rows aligned), its own grain
    pr0 = int(s["base_bottom"]) - 2
    plin = Lr[pr0:, pc0:pc1] / np.maximum(Lp[pr0:, None], 1e-4)
    pq = np.ones((SR_H - pr0, qw), np.float32)
    xw, bw, o = 0, 36, 6
    ramp = np.linspace(0, 1, o, dtype=np.float32)[None]
    while xw < qw:
        sx = int(RNG.integers(0, plin.shape[1] - bw))
        blk = plin[:, sx:sx + bw]
        n = min(bw, qw - xw)
        if xw == 0:
            pq[:, :n] = blk[:, :n]
        else:
            pq[:, xw:xw + o] = pq[:, xw:xw + o] * (1 - ramp[:, :min(o, qw - xw)]) + blk[:, :min(o, qw - xw)] * ramp[:, :min(o, qw - xw)]
            pq[:, xw + o:xw + n] = blk[:, o:n]
        xw += bw - o
    HFs[pr0:, :qw] = np.where(rows[pr0:, None] >= int(s["base_bottom"]) + 1, pq, HFs[pr0:, :qw])
    # the target: P(y) x gain(x) x grain
    synth = P[:, None, :] * grgb[None, :, :] * HFs[..., None]
    # the left arm and the arm / rail junction (cols < junction_left + 6): extended down from their own visible part
    Pa = Fr[:, 1222:1275].mean(1)                                     # the right arm's own profile to its foot
    La = lum(Pa)
    jl = s["junction_left"] + 6
    for x in range(int(s["arm_left_edge"]) - 6, jl):
        ytop = r0[x] - 4
        if ytop >= int(s["rail_crease"]):
            continue
        src0 = 172 if x >= s["junction_left"] - 20 else max(100, ytop - 50)
        src1 = ytop - 2
        if src1 - src0 < 10:
            src0 = src1 - 10
        colv = Fr[src0:src1, x]
        lf = colv.mean(0)
        ref = La[src0:src1].mean()
        for y in range(ytop, int(s["rail_crease"])):
            sy = src0 + (y - ytop) % (src1 - src0)
            hf = lum(Fr[sy, x][None])[0] / max(lum(lf[None])[0], 1e-4)
            synth[y, x] = lf * (La[y] / ref) * hf
    synth = np.clip(synth, 0, 1)
    # where the fill meets the visible sofa: 3 px cross-fades (top: below the table's top edge; right: the table's right end)
    fill = Tr.copy()
    wfill = cv2.GaussianBlur(fill.astype(np.float32), (0, 0), 1.0)
    wfill = np.where(fill, np.maximum(wfill, 0.0), 0.0)
    Fr_new = Fr * (1 - wfill[..., None]) + synth * wfill[..., None]
    if os.environ.get("FB12_DEBUG"):
        np.save(os.path.join(WORK, "sofa-rect-debug.npy"), np.clip(l2s(Fr_new), 0, 1).astype(np.float16))
        np.savez(os.path.join(WORK, "hf-debug.npz"), HFs=HFs.astype(np.float16))
    # back to the picture
    synth_img = l2s(np.clip(sr_back(Fr_new), 0, 1))
    sil = sil_image(T)
    fa_new = np.where(T, sil, fa).astype(np.float32)
    F_new = np.where(T[..., None], synth_img, F).astype(np.float32)
    Un = shell * Sp[..., None] * (1 - fa_new[..., None]) + F_new * fa_new[..., None]
    Un8 = u8(Un)
    region = T | (np.abs(Sp - S) > 0.5 / 255)
    U8n = np.where(region[..., None], Un8, U8)
    rec["region_px"] = int(region.sum())
    rec["rows_r0"] = {str(x): int(r0[x]) for x in (60, 100, 150, 300, 600, 900, 1040, 1080)}
    rec["grain"] = rec_bands
    return dict(U8=U8n, U8_old=U8, region=region, fa_new=fa_new, fa_old=fa, F_new=F_new, Sp=Sp, S=S, T=T, rec=rec, M=M, w=w)


def graded_plate(pl):
    sys.path.insert(0, P2)
    sys.path.insert(0, P1)
    import stack as ST  # noqa: E402  (read-only: the ONE v3c grade, base.png byte for byte)
    G = ST.Grade()
    base = np.asarray(Image.open(os.path.join(LAY, "base.png")))
    new = G(pl["U8"].astype(np.float32) / 255)
    new = np.where(pl["region"][..., None], new, base)               # identical outside the region in any case (checked)
    pl["plate8"] = new
    pl["grade"] = G
    return new


# ------------------------------------------------------------------------------------------------- the cushion sets at the old table
def cushions(pl):
    """The cushion sets were cut with the table mask subtracted (pilot_wm.py). Next to the old table a set's layer holds the sofa
    itself, darkened by the throw (the cushion pass re-rendered it); with the table gone that darkening stopped at the old table's
    outline. Fix (new pixels only inside the old table's region, every R9 pixel of the set kept): the darkening ratio of the
    sofa-like pixels within 12 px outside the region (layer / plate, per channel; sofa-like = Lab a*, b* within 4 / 5 of the plate,
    Y ratio < 1.02, the classification blurred) is carried in by a normalised blur (10 px) and fades over 40 px; the set's layer gets
    those pixels as plate x ratio on the sofa (fa' > 0.5). The set's shadow inside the region (cast on the old table top) is replaced
    by its own continuation from outside, fading over 20 px."""
    T = pl["T"]
    plate = pl["plate8"].astype(np.float32) / 255
    pl_lin = s2l(plate)
    din = cv2.distanceTransform(T.astype(np.uint8), cv2.DIST_L2, 5)
    dout = cv2.distanceTransform((~T).astype(np.uint8), cv2.DIST_L2, 5)
    sofa = pl["fa_new"] > 0.5
    labp = cv2.cvtColor(plate, cv2.COLOR_RGB2LAB)
    out, rec = {}, {}
    man = json.load(open(os.path.join(LAY, "manifest-r9.json")))
    for st, v in man["slot_cushions"]["sets"].items():
        L8 = np.asarray(Image.open(os.path.join(LAY, v["layer"])))
        Sh8 = np.asarray(Image.open(os.path.join(LAY, v["shadow"])).convert("RGB"))
        L = L8.astype(np.float32) / 255
        lin = s2l(L[..., :3])
        labl = cv2.cvtColor(np.ascontiguousarray(L[..., :3]), cv2.COLOR_RGB2LAB)
        da = cv2.GaussianBlur(np.abs(labl[..., 1] - labp[..., 1]), (0, 0), 2.0)
        db = cv2.GaussianBlur(np.abs(labl[..., 2] - labp[..., 2]), (0, 0), 2.0)
        ratio = lin / np.maximum(pl_lin, 1e-4)
        yr = lum(lin) / np.maximum(lum(pl_lin), 1e-4)
        src = (~T) & (dout < 12) & (L8[..., 3] > 250) & (da < 4) & (db < 5) & (yr < 1.02) & sofa
        k = src.astype(np.float32)
        den = cv2.GaussianBlur(k, (0, 0), 10.0)
        rat = np.dstack([cv2.GaussianBlur(np.clip(ratio[..., c], 0.1, 1.0) * k, (0, 0), 10.0) for c in range(3)]) / np.maximum(den, 1e-6)[..., None]
        wk = np.clip(den / 0.15, 0, 1)
        fade = np.clip(1 - din / 40.0, 0, 1) ** 1.5
        add = T & sofa & (L8[..., 3] == 0) & (wk * fade > 0.02) & (lum(rat) < 0.97)
        a_add = np.where(add, wk * fade, 0.0)
        rgb_add = l2s(np.clip(pl_lin * rat, 0, 1))
        L2 = L8.copy()
        L2[add, :3] = u8(rgb_add)[add]
        L2[add, 3] = u8(a_add)[add]
        # the set's shadow inside the region: its continuation from the 8 px outside, fading over 20 px
        ks = ((~T) & (dout < 8)).astype(np.float32)
        dens = cv2.GaussianBlur(ks, (0, 0), 6.0)
        Sf = Sh8.astype(np.float32) / 255
        ext = np.dstack([cv2.GaussianBlur((1 - Sf[..., c]) * ks, (0, 0), 6.0) for c in range(3)]) / np.maximum(dens, 1e-6)[..., None]
        fs = np.clip(1 - din / 20.0, 0, 1)[..., None] * np.clip(dens / 0.1, 0, 1)[..., None]
        Sh2 = Sh8.copy()
        Sin = u8(1 - ext * fs)
        Sh2[T] = Sin[T]
        out[st] = (L2, Sh2)
        rec[st] = dict(added_px=int((L2[..., 3] != L8[..., 3]).sum()), shadow_px_changed=int((Sh2 != Sh8).any(2).sum()),
                       source_px=int(src.sum()))
    return out, rec


# ------------------------------------------------------------------------------------------------- prep
IDX_FURN = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r4-furn-idx/M0.npz"


def prep():
    """the r4 clay's furniture index pass (pilot_wm.py IDX_FURN: sofa 1, table 2, armchair 3), area-resampled to the work size as
    pilot_wm.idx_masks does, kept with this stage (8-bit) so the stage re-runs without the session scratchpad"""
    os.makedirs(WORK, exist_ok=True)
    if os.path.exists(MASKS):
        return
    idx = np.load(IDX_FURN)["idx"]
    out = {}
    for k, v in {"sofa": 1, "table": 2, "armchair": 3}.items():
        out[k] = u8(cv2.resize((idx == v).astype(np.float32), (W, H), interpolation=cv2.INTER_AREA))
    np.savez_compressed(MASKS, **out)


# ------------------------------------------------------------------------------------------------- the rug under the table
RUG_Z = 0.012
RUG_SHARP = 0.22      # unsharp amount on the synthesised rug: its fine grain measured 0.83-0.92 of the original's at the same depth
RR_PPM, RR_X0, RR_Y0, RR_W, RR_H = 900, -1.3, 0.70, 2970, 1710          # X -1.3..2.0, Y 0.70..2.60
RUG_EDGE = dict(back_Y=0.777, left_X=-1.45)          # measured on the R9 rug layer's 50 % alpha (plan: 230 x 330 at (0.20, 1.92))
EDGE_SHIFT = 0.15                                    # m: the back edge revealed left of the sofa is copied along X from the visible edge
RR_M = plane_H("z", RUG_Z) @ rect_A(RR_PPM, RR_X0, RR_Y0)


def rr_warp(a, interp=cv2.INTER_CUBIC):
    return cv2.warpPerspective(a, RR_M, (RR_W, RR_H), flags=cv2.WARP_INVERSE_MAP | interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def rr_back(a, interp=cv2.INTER_CUBIC):
    return cv2.warpPerspective(a, RR_M, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def box_lf(x, k, bw=45, bh=39):
    """anisotropic box LF over the weight k: two rib periods across (2.4 cm each) and two braid periods along (2.1 cm each)"""
    num = cv2.boxFilter(x * k, -1, (bw, bh), normalize=False)
    den = cv2.boxFilter(k.astype(np.float32), -1, (bw, bh), normalize=False)
    return num / np.maximum(den, 1e-6), den / (bw * bh)


def fill_quilt(tex, known, todo, bs=(96, 48), ov=(20, 14), n_cand=600, top=4, depth=None, dlocal=0.15, xm=None, xlocal=0.6, rng=RNG):
    """hole filling by quilting: blocks (h, w) in raster order over the bbox of todo; each block's error is the SSD against every
    known (original or already filled) pixel in its window; the patch goes into the unknown pixels, with min-cut seams in the left /
    top overlaps where those overlaps were themselves filled; candidates: fully-known source windows within ylocal rows (the same
    depth band, so the same sharpness), one of the `top` best at random"""
    bh, bw = bs
    oh, ow = ov
    out = tex.copy()
    kn = known.copy()
    filled = np.zeros_like(known)
    okc = cv2.erode(known.astype(np.uint8), np.ones((bh, bw), np.uint8), anchor=(0, 0))
    okc[-bh + 1:, :] = 0
    okc[:, -bw + 1:] = 0
    cy, cx = np.nonzero(okc)
    cdep = depth[np.minimum(cy + bh // 2, depth.shape[0] - 1), np.minimum(cx + bw // 2, depth.shape[1] - 1)] if depth is not None else None
    ys, xs = np.nonzero(todo)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    nblocks = 0
    for by in range(y0, y1, bh - oh):
        for bx in range(x0, x1, bw - ow):
            win = (slice(by, by + bh), slice(bx, bx + bw))
            t = todo[win] & ~filled[win]
            if not t.any():
                continue
            hh, ww = t.shape
            if depth is not None:
                dt = depth[min(by + bh // 2, depth.shape[0] - 1), min(bx + bw // 2, depth.shape[1] - 1)]
                sel = np.abs(cdep - dt) <= dlocal
                if xm is not None:
                    # the rug's braid size drifts across the render: prefer donors from the same side (within xlocal m)
                    sx_ = sel & (np.abs(xm[np.minimum(cx + bw // 2, len(xm) - 1)] - xm[min(bx + bw // 2, len(xm) - 1)]) <= xlocal)
                    if sx_.sum() >= 80:
                        sel = sx_
            else:
                sel = np.ones(len(cy), bool)
            idx = np.nonzero(sel)[0]
            if len(idx) < 50:
                idx = np.argsort(np.abs(cdep - dt))[:400] if depth is not None else np.arange(len(cy))
            pick = idx[rng.integers(0, len(idx), min(n_cand, len(idx)))]
            m = (kn[win] & ~(todo[win] & ~filled[win])).astype(np.float32)
            if tex.ndim == 3:
                m = m[..., None]
            cur = out[win]
            errs = np.empty(len(pick), np.float32)
            msum = max(float(m.sum()), 1.0)
            cm = float((cur * m).sum()) / msum
            cs = math.sqrt(max(float((((cur - cm) ** 2) * m).sum()) / msum, 1e-8))
            for i, j in enumerate(pick):
                p = tex[cy[j]:cy[j] + hh, cx[j]:cx[j] + ww]
                pm = float((p * m).sum()) / msum
                ps = math.sqrt(max(float((((p - pm) ** 2) * m).sum()) / msum, 1e-8))
                # 1 - NCC over the known pixels, plus the contrast mismatch (no bias toward flat, blurred donors)
                ncc = float((((p - pm) * (cur - cm)) * m).sum()) / msum / (ps * cs)
                errs[i] = (1 - ncc) + 0.5 * abs(math.log(ps / cs))
            order = np.argsort(errs)[:top]
            j = pick[order[rng.integers(0, len(order))]]
            p = tex[cy[j]:cy[j] + hh, cx[j]:cx[j] + ww].copy()
            put = t.copy()
            # min-cut in the left overlap and the top overlap, where the overlap holds filled pixels
            if bx > x0 and ww > ow:
                e = (p[:, :ow] - cur[:, :ow]) ** 2
                path = mincut_v(e.sum(-1) if e.ndim == 3 else e)
                fl = filled[win][:, :ow]
                for i in range(hh):
                    keep = np.arange(ow) < path[i]
                    put[i, :ow] &= ~(keep & fl[i])
                    put[i, :ow] |= (~keep) & fl[i] & todo[win][i, :ow]
            if by > y0 and hh > oh:
                e = (p[:oh, :] - cur[:oh, :]) ** 2
                e = (e.sum(-1) if e.ndim == 3 else e).T
                path = mincut_v(e)
                fl = filled[win][:oh, :]
                for jx in range(ww):
                    keep = np.arange(oh) < path[jx]
                    put[:oh, jx] &= ~(keep & fl[:, jx])
                    put[:oh, jx] |= (~keep) & fl[:, jx] & todo[win][:oh, jx]
            cur[put] = p[put]
            out[win] = cur
            filled[win] |= put
            kn[win] |= put
            nblocks += 1
    return out, nblocks


def rug(pl):
    """pl: the plate() result (S', T, fa') and the graded new plate"""
    R8 = np.asarray(Image.open(os.path.join(LAY, "rug/rug-cj-braided-wool-natural.png")))
    R = R8.astype(np.float32) / 255
    T, Sp, S, fa_new = pl["T"], pl["Sp"], pl["S"], pl["fa_new"]
    plate8 = pl["plate8"]
    shell_g = f8(os.path.join(P1, "shell-v3-graded-v3c.png"), "RGB")
    rec = {}
    # the light on the floor without the table: the graded shell's luminance at the board scale out (anisotropic, in the plane) x S'
    Xr, Yr = img_to_plane(plane_H("z", RUG_Z))
    Lsh = lum(s2l(shell_g))
    Lsh_r = rr_warp(Lsh)
    okf = rr_warp((1 - pl["fa_old"]).astype(np.float32), cv2.INTER_LINEAR) > 0.99
    num = cv2.GaussianBlur(Lsh_r * okf, (0, 0), sigmaX=0.25 * RR_PPM, sigmaY=0.10 * RR_PPM)
    den = cv2.GaussianBlur(okf.astype(np.float32), (0, 0), sigmaX=0.25 * RR_PPM, sigmaY=0.10 * RR_PPM)
    light_r = num / np.maximum(den, 1e-6) * rr_warp(Sp, cv2.INTER_LINEAR)
    # the rug in the plane
    Rr = rr_warp(R)
    ar = Rr[..., 3]
    lin = s2l(np.clip(Rr[..., :3], 0, 1))
    Lr = lum(lin)
    Tr = rr_warp(T.astype(np.float32), cv2.INTER_LINEAR) > 0.01
    dS = rr_warp(np.abs(Sp - S), cv2.INTER_LINEAR)
    clean = (ar > 0.995) & ~cv2.dilate(Tr.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    LF, cover = box_lf(Lr, clean.astype(np.float32))
    rho = np.where(clean & (cover > 0.6), LF / np.maximum(light_r, 1e-5), np.nan)
    # the zone: the table's region, where S lost the table's shadow, and where the rug's own LF says shadow (rho well under the fit)
    Xg, Yg = np.meshgrid(RR_X0 + np.arange(RR_W) / RR_PPM, RR_Y0 + np.arange(RR_H) / RR_PPM)
    zone = Tr | (dS > 0.003)
    zone = cv2.morphologyEx(zone.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)).astype(bool)
    zone = cv2.dilate(zone.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))).astype(bool)
    in_rug = (ar > 0.0) | Tr
    zone &= in_rug
    # the rug's own level relative to the light, carried in from around the zone (normalised blur, 0.15 m), so the fill continues
    # the rug's look at its edge; inside, the light (shell x S') shapes it
    kr = (clean & ~zone & (cover > 0.9) & np.isfinite(rho)).astype(np.float32)
    rr = np.where(kr > 0, rho, 0).astype(np.float32)
    d1 = cv2.GaussianBlur(kr, (0, 0), 0.15 * RR_PPM)
    c1 = cv2.GaussianBlur(rr * kr, (0, 0), 0.15 * RR_PPM) / np.maximum(d1, 1e-6)
    d2 = cv2.GaussianBlur(kr, (0, 0), 0.60 * RR_PPM)
    c2 = cv2.GaussianBlur(rr * kr, (0, 0), 0.60 * RR_PPM) / np.maximum(d2, 1e-6)
    c2 = np.where(d2 > 1e-4, c2, float(np.median(rho[kr > 0])))
    w1 = np.clip(d1 / 0.15, 0, 1)
    c_loc = c1 * w1 + c2 * (1 - w1)
    LFt = (c_loc * light_r).astype(np.float32)
    ring = (kr > 0) & cv2.dilate(zone.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    res = np.where(ring, LF / np.maximum(LFt, 1e-5), np.nan)
    rec["light_fit"] = dict(model="rug LF = c x the shell's light (anisotropic blur 0.25 / 0.10 m) x S'; c = the rug's own LF / light "
                                  "around the zone, normalised blur 0.15 m", ring_px=int(ring.sum()),
                            ring_residual_p05_p50_p95=[round(float(np.nanpercentile(res, q)), 3) for q in (5, 50, 95)])
    shade = np.where(clean & (cover > 0.6), LF / np.maximum(LFt, 1e-5), 1.0)
    # visible rug in the zone: relit (its own grain kept): x LFt / LF where the table's shadow was faint (gain <= 1.15); hidden,
    # shadowed (gain > 1.15) or without an LF: synthesised
    LFz, coverz = box_lf(Lr, (ar > 0.995).astype(np.float32))
    gain = np.where(coverz > 0.6, LFt / np.maximum(LFz, 1e-5), 9.0)
    synth = zone & (Tr | (gain > 1.15))
    synth = cv2.morphologyEx(synth.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8)).astype(bool)
    synth = cv2.dilate(synth.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))).astype(bool) & zone
    gz = np.clip(np.where(zone & ~synth, gain, 1.0), 0.85, 1.2).astype(np.float32)
    gz = np.where(synth, 1.0, gz)
    relit = np.clip(lin * gz[..., None], 0, 1)
    # the grain: the clean rug's own RGB over its per-channel LF (colour and grain kept together), hole-filled by quilting
    LFc = np.dstack([box_lf(lin[..., c], clean.astype(np.float32))[0] for c in range(3)])
    tex = np.where(clean[..., None], lin / np.maximum(LFc, 1e-5), 1.0).astype(np.float32)
    known = clean & ~synth & (cover > 0.95)
    todo = synth & (rr_warp(np.ones((H, W), np.float32), cv2.INTER_LINEAR) > 0.5)
    Dr = (0.4226 * (0.83 - Xg) + 0.9063 * (4.64 - Yg)).astype(np.float32)      # depth along M0's axis (m)
    texq, nb = fill_quilt(tex, known, todo, depth=Dr, xm=(RR_X0 + np.arange(RR_W) / RR_PPM).astype(np.float32))
    # the rug's back edge left of the sofa (revealed between the old table's left end and the sofa's end): whole columns copied
    # from the visible edge EDGE_SHIFT to the left (the edge runs along X, the ribs along Y: both stay continuous); 6 px cross-fade
    dsh = int(round(EDGE_SHIFT * RR_PPM))
    cols = np.nonzero((RR_X0 + np.arange(RR_W) / RR_PPM >= -1.06) & (RR_X0 + np.arange(RR_W) / RR_PPM <= -0.86))[0]
    n_edge = 0
    for c in cols:
        rows_t = np.nonzero(todo[:, c] & known[:, c - dsh])[0]
        if len(rows_t):
            xr_ = RR_X0 + c / RR_PPM
            wcol = float(np.clip((-0.86 - xr_) / 0.03, 0, 1))
            texq[rows_t, c] = tex[rows_t, c - dsh] * wcol + texq[rows_t, c] * (1 - wcol)
            n_edge += len(rows_t)
    rec["edge_copy_px_rect"] = n_edge
    # the colour of the LF: the clean rug's, smoothed and carried into the zone
    chrom = LFc / np.maximum(LF[..., None], 1e-5)
    kc = (clean & ~zone).astype(np.float32)
    med = np.median(chrom[kc > 0], axis=0)
    den = cv2.GaussianBlur(kc, (0, 0), 0.15 * RR_PPM)
    Cn = np.dstack([cv2.GaussianBlur(chrom[..., c] * kc, (0, 0), 0.15 * RR_PPM) for c in range(3)]) / np.maximum(den, 1e-6)[..., None]
    den2 = cv2.GaussianBlur(kc, (0, 0), 0.6 * RR_PPM)
    Cn2 = np.dstack([cv2.GaussianBlur(chrom[..., c] * kc, (0, 0), 0.6 * RR_PPM) for c in range(3)]) / np.maximum(den2, 1e-6)[..., None]
    Cn2 = np.where(den2[..., None] > 1e-4, Cn2, med[None, None])
    wC = np.clip(den / 0.15, 0, 1)[..., None]
    C = Cn * wC + Cn2 * (1 - wC)
    syn_lin = np.clip(texq * (LFt[..., None] * C), 0, 1)
    ws = cv2.GaussianBlur(synth.astype(np.float32), (0, 0), 2.0)
    ws = np.where(synth, ws, 0)[..., None]
    new_lin = syn_lin * ws + relit * (1 - ws)
    new_g = l2s(new_lin)
    rec["synth_px_rect"] = int(synth.sum())
    rec["relit_px_rect"] = int((zone & ~synth).sum())
    # back to the picture; the zone in the picture, its edge feathered 2 px
    zimg = rr_back(zone.astype(np.float32), cv2.INTER_LINEAR) > 0.5
    zimg &= (R[..., 3] > 0) | T
    wz = cv2.GaussianBlur(zimg.astype(np.float32), (0, 0), 1.2)
    wz = np.where(zimg, wz, 0)
    newimg = np.clip(rr_back(new_g), 0, 1)
    wsi = np.clip(rr_back(ws[..., 0].astype(np.float32), cv2.INTER_LINEAR), 0, 1)[..., None]
    sharp = np.clip(newimg + RUG_SHARP * (newimg - cv2.GaussianBlur(newimg, (0, 0), 1.2)), 0, 1)
    newimg = newimg * (1 - wsi) + sharp * wsi
    rgb = R[..., :3] * (1 - wz[..., None]) + newimg * wz[..., None]
    # alpha: in the table's region the rug is whole, under the sofa's new strip (1 - fa'); elsewhere the old alpha
    a_full = cv2.GaussianBlur(((Yr >= RUG_EDGE["back_Y"]) & (Xr >= RUG_EDGE["left_X"])).astype(np.float32), (0, 0), 1.2)
    a_new = np.where(T, a_full * (1 - fa_new), R[..., 3]).astype(np.float32)
    # soft edge at the sofa's foot: solve rgb so that the stack formula gives the physical mix (target = rug (1-fa') + sofa fa')
    soft = T & (a_new > 0.02) & (a_new < 0.98)
    base_g = plate8.astype(np.float32) / 255
    sofa_g = base_g                                                     # where fa' ~ 1 the plate is the sofa
    target = rgb * a_new[..., None] + sofa_g * (1 - a_new[..., None])
    solved = (target - base_g * (1 - a_new[..., None])) / np.maximum(a_new[..., None], 1e-3)
    rgb = np.where(soft[..., None], np.clip(solved, 0, 1), rgb)
    a8 = u8(a_new)
    a8 = np.where(a8 == 0, 0, a8)
    out = np.dstack([u8(rgb), a8])
    out[a8 == 0, :3] = R8[a8 == 0, :3]                                 # no colour under alpha 0 change (keeps the old bytes)
    changed = (out != R8).any(2)
    # the rug's own contact shadow along the revealed back edge: the R9 shadow layer sampled EDGE_SHIFT to the left along X
    Sh8 = np.asarray(Image.open(os.path.join(LAY, "rug/rug-cj-braided-wool-natural-shadow.png")).convert("RGB"))
    Hr0 = plane_H("z", RUG_Z)
    band = T & (Yr > RUG_EDGE["back_Y"] - 0.08) & (Yr < RUG_EDGE["back_Y"] + 0.05) & (Xr > -1.10) & (Xr < -0.85)
    ys_, xs_ = np.nonzero(band)
    P_ = np.stack([Xr[ys_, xs_] - EDGE_SHIFT, Yr[ys_, xs_], np.ones(len(xs_))], -1) @ Hr0.T
    mx = (P_[:, 0] / P_[:, 2]).astype(np.float32)
    my = (P_[:, 1] / P_[:, 2]).astype(np.float32)
    smp = cv2.remap(Sh8, mx[None], my[None], cv2.INTER_LINEAR)[0]
    Sh_new = Sh8.copy()
    Sh_new[ys_, xs_] = np.minimum(Sh8[ys_, xs_], smp)
    rec["rug_shadow_px_changed"] = int((Sh_new != Sh8).any(2).sum())
    rec["zone_px"] = int(zimg.sum())
    rec["changed_px"] = int(changed.sum())
    rec["quilt_blocks"] = nb
    rec["alpha_px_new"] = int((a8 > 0).sum())
    rec["alpha_px_old"] = int((R8[..., 3] > 0).sum())
    return dict(rug8=out, rug_shadow8=Sh_new, rec=rec, zimg=zimg, changed=changed | (Sh_new != Sh8).any(2), rho_debug=(shade, zone, LFt, LF) if os.environ.get("FB12_DEBUG") else None)


# ------------------------------------------------------------------------------------------------- the defaults
HIDDEN = ("bowl", "candle-holders")          # on the old table: hidden in the defaults until the new table is in (layers kept)


def rhu(x):
    return np.floor(x + 0.5)


def stack_list(man, st, files):
    """(id, layer path, shadow path) in the manifest's order, the hidden slots out; files: id -> replacement layer path"""
    out = []
    for l_ in man["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow") or k in HIDDEN:
            continue
        if k == "cushions":
            v = man["slot_cushions"]["sets"][st]
            out.append((k, files.get(("cushions", st), os.path.join(LAY, v["layer"])), files.get(("cushions-shadow", st), os.path.join(LAY, v["shadow"]))))
        else:
            sh = next(x for x in man["layers"] if x["id"] == k + "-shadow")
            out.append((k, files.get(k, os.path.join(LAY, l_["file"])), files.get(k + "-shadow", os.path.join(LAY, sh["file"]))))
    return out


def compose8(base8, layers, cache):
    """the manifest's formula, 8-bit pipe (verify_layers_r4.compose 'int'): m = rhu(o S / 255); o = rhu(rhu(rgb a) + m (1 - a))"""
    o = base8.astype(np.float64)
    for k, lf, sf in layers:
        if lf not in cache:
            cache[lf] = np.asarray(Image.open(lf))
        if sf not in cache:
            cache[sf] = np.asarray(Image.open(sf).convert("RGB"))
        L, S = cache[lf].astype(np.float64), cache[sf].astype(np.float64)
        a = L[..., 3:4] / 255.0
        o = rhu(rhu(L[..., :3] * a) + rhu(o * S / 255.0) * (1 - a))
    return o.astype(np.uint8)


def region_layer(lf, sf):
    L = np.asarray(Image.open(lf))
    S = np.asarray(Image.open(sf).convert("RGB"))
    return (L[..., 3] > 0) | (S < 255).any(2)


# ------------------------------------------------------------------------------------------------- build
def save_png(p, a):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Image.fromarray(a).save(p, optimize=False, compress_level=6)
    return p


def build_all():
    prep()
    rec = dict(id="wm-living-room-m0-fb12-stage0", date="2026-11-25", author="render-agent", tokens=0, model="code (0 tokens, no var2)",
               brief="briefs/wm-fb12-stage0-clean-plate-2026-11-25.md", spec="docs/proposals/wm-fb12-2026-11-25.md a.5-a.7 (path R)")
    pl = plate()
    plate8 = graded_plate(pl)
    base = np.asarray(Image.open(os.path.join(LAY, "base.png")))
    diff = (plate8 != base).any(2)
    assert not (diff & ~pl["region"]).any(), "the plate changed outside its region"
    P = dict(plate=os.path.join(OUT, "layers", f"base-{TAG}.png"),
             U=os.path.join(WORK, f"shell-furniture-{TAG}.png"),
             F=os.path.join(WORK, f"fixed-furniture-{TAG}.png"),
             S=os.path.join(WORK, f"fixed-furniture-shadow-{TAG}.png"),
             regions=os.path.join(WORK, f"regions-{TAG}.npz"),
             rug=os.path.join(OUT, "layers", "rug", f"rug-cj-braided-wool-natural-{TAG}.png"))
    save_png(P["plate"], plate8)
    save_png(P["U"], pl["U8"])
    save_png(P["F"], np.dstack([u8(pl["F_new"]), u8(pl["fa_new"])]))
    save_png(P["S"], np.repeat(u8(pl["Sp"])[..., None], 3, 2))
    rec["plate"] = dict(pl["rec"], px_changed_vs_base=int(diff.sum()))
    r = rug(pl)
    save_png(P["rug"], r["rug8"])
    if r["rec"]["rug_shadow_px_changed"]:
        P["rug_shadow"] = os.path.join(OUT, "layers", "rug", f"rug-cj-braided-wool-natural-shadow-{TAG}.png")
        save_png(P["rug_shadow"], r["rug_shadow8"])
    rec["rug"] = r["rec"]
    cush, crec = cushions(pl)
    files = {"rug": P["rug"]}
    if "rug_shadow" in P:
        files["rug-shadow"] = P["rug_shadow"]
    for st, (L2, Sh2) in cush.items():
        if crec[st]["added_px"]:
            fp = os.path.join(OUT, "layers", "cushions", f"set-{st}-{TAG}.png")
            save_png(fp, L2)
            files[("cushions", st)] = fp
            P[f"cushions-{st}"] = fp
        if crec[st]["shadow_px_changed"]:
            fp = os.path.join(OUT, "layers", "cushions", f"set-{st}-shadow-{TAG}.png")
            save_png(fp, Sh2)
            files[("cushions-shadow", st)] = fp
            P[f"cushions-{st}-shadow"] = fp
    rec["cushions"] = crec
    # the defaults: the new 8-bit stack where anything changed (new stack != old stack), the old truths' own bytes elsewhere
    man = json.load(open(os.path.join(LAY, "manifest-r9.json")))
    cache = {}
    R_def = {}
    rec["defaults"] = {}
    for st in man["slot_cushions"]["order"]:
        old_layers = []
        for l_ in man["layers"]:
            k = l_["id"]
            if k == "base" or k.endswith("-shadow"):
                continue
            if k == "cushions":
                v = man["slot_cushions"]["sets"][st]
                old_layers.append((k, os.path.join(LAY, v["layer"]), os.path.join(LAY, v["shadow"])))
            else:
                sh = next(x for x in man["layers"] if x["id"] == k + "-shadow")
                old_layers.append((k, os.path.join(LAY, l_["file"]), os.path.join(LAY, sh["file"])))
        s_old = compose8(base, old_layers, cache)
        s_new = compose8(plate8, stack_list(man, st, files), cache)
        Rg = (s_old != s_new).any(2)
        truth_old = np.asarray(Image.open(os.path.normpath(os.path.join(LAY, man["truths"]["default"][st]))).convert("RGB"))
        truth = np.where(Rg[..., None], s_new, truth_old)
        fp = os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")
        save_png(fp, truth)
        P[f"default-{st}"] = fp
        R_def[st] = Rg
        rec["defaults"][st] = dict(file=rel(fp), region_px=int(Rg.sum()), outside_region_vs_old_truth_px=int(((truth != truth_old).any(2) & ~Rg).sum()))
        cache = {k_: v_ for k_, v_ in cache.items() if "cushions" not in k_}
    np.savez_compressed(P["regions"], table=pl["T"], plate=pl["region"], rug=r["changed"], **{f"default_{k}": v for k, v in R_def.items()})
    rec["files"] = {k: rel(v) for k, v in P.items()}
    rec["sha256"] = {k: sha(v) for k, v in P.items() if v.endswith(".png")}
    json.dump(rec, open(os.path.join(WORK, f"{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    return rec, pl, r


# ------------------------------------------------------------------------------------------------- the QA sheet
def sheet():
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    man = json.load(open(os.path.join(LAY, "manifest-r9.json")))
    box = (1200, 1120, 2400, 1530)                                   # the old table's region (x0, y0, x1, y1) at x2
    tb = (1850, 1100, 2450, 1450)                                    # the throw's side, at x2
    def tile(p, b, label, k=2):
        im = Image.open(p).convert("RGB").crop(b)
        im = im.resize((im.width * k, im.height * k), Image.LANCZOS)
        bar = Image.new("RGB", (im.width, 40), (24, 24, 24))
        ImageDraw.Draw(bar).text((12, 6), label, fill=(240, 240, 240), font=font)
        out = Image.new("RGB", (im.width, im.height + 40))
        out.paste(bar, (0, 0))
        out.paste(im, (0, 40))
        return out
    t_old = lambda st: os.path.normpath(os.path.join(LAY, man["truths"]["default"][st]))
    t_new = lambda st: os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")
    rows = [tile(os.path.join(LAY, "base.png"), box, "BEFORE  base.png (r9 plate, the old table)  x2, px 1200-2400 x 1120-1530"),
            tile(os.path.join(OUT, "layers", f"base-{TAG}.png"), box, f"AFTER  base-{TAG}.png (clean plate: parquet, sofa strip, shadow)  x2"),
            tile(t_old("B"), box, "BEFORE  default set B (r8 truth)  x2"),
            tile(t_new("B"), box, f"AFTER  default set B ({TAG}: rug fill, bowl + candle holders hidden)  x2")]
    pair = [tile(t_new(st), tb, f"AFTER set {st}: the throw's side  x2") for st in ("A", "C")]
    w = rows[0].width
    pr = Image.new("RGB", (w, pair[0].height), (24, 24, 24))
    pr.paste(pair[0], (0, 0))
    pr.paste(pair[1], (w - pair[1].width, 0))
    rows.append(pr)
    H_ = sum(r_.height for r_ in rows) + 6 * (len(rows) - 1)
    sh = Image.new("RGB", (w, H_), (255, 255, 255))
    y = 0
    for r_ in rows:
        sh.paste(r_, (0, y))
        y += r_.height + 6
    p = os.path.join(OUT, "qa-sheet-fb12-stage0.jpg")
    sh.save(p, quality=86)
    return p


# ------------------------------------------------------------------------------------------------- the frames
FRAME_BOX = (77.49, 43.43, 2642.51, 1486.57)        # the 3840 x 2160 camera frame inside the 2720 x 1530 canvas (manifest size)


def frames():
    """1920 x 1080 frames of the camera frame (as the hall's *-frame.png): the clean plate (the arrival's landing, 702) and the
    default scene (set B, the tool's resting frame)"""
    out = {}
    for name, src in (("plate", os.path.join(OUT, "layers", f"base-{TAG}.png")),
                      ("default", os.path.join(OUT, "graded", f"default-scene-{TAG}-set-B-graded-v3c.png"))):
        im = Image.open(src).convert("RGB")
        fr = im.resize((1920, 1080), Image.LANCZOS, box=FRAME_BOX)
        p = os.path.join(OUT, f"{name}-frame-{TAG}.png")
        fr.save(p)
        out[name] = p
    return out


# ------------------------------------------------------------------------------------------------- the records
def homog(Hm):
    Hm = Hm / Hm[2, 2]
    return [[round(float(v), 9) for v in r_] for r_ in Hm]


def records():
    rec = json.load(open(os.path.join(WORK, f"{TAG}.json")))
    S_c = np.diag([CANVAS[0] / W, CANVAS[1] / H, 1.0])
    plate_p = os.path.join(OUT, "layers", f"base-{TAG}.png")
    note = dict(
        id=f"wm-m0-{TAG}-motion-note", date="2026-11-25", author="render-agent", to="motion-agent",
        what="FB12 stage 0: the clean M0 plate without the old coffee table (path R). Erase the old table from HDx2, from clip 2 (529-701) "
             "and from the hall's station frame (hdx2-products) by projecting the floor and the sofa front from this plate.",
        clean_plate=dict(path=rel(plate_p), sha256=sha(plate_p), size=[W, H], canvas="the M0 1.2 overscan canvas at 2720 x 1530 "
                         "(4072 x 2290 x 2720 / 4072); the 3840 x 2160 camera frame inside it at [77.49, 43.43, 2642.51, 1486.57]",
                         grade="v3c, the same bytes as base.png outside the changed region; frame 702 = this file"),
        previous_plate=dict(path=rel(os.path.join(LAY, "base.png")), sha256=sha(os.path.join(LAY, "base.png")), note="kept for rollback"),
        camera=dict(source="docs/house-plan.json cameras M0 (1.2)", loc=CAM["loc"], yaw_deg_left=CAM["yaw_deg_left"], lens_mm=CAM["lens"],
                    u0=CAM["u0"], v0=CAM["v0"], projection="clay_wm_r1.project: u = u0 + (24/36) (p.right)/d, v = v0 - (24/36)(16/9) p.z / d; "
                    "canvas px = (116 + 3840 u, 65 + 2160 v) on 4072 x 2290"),
        homography_floor=dict(plane="Z 0 (the parquet), plan axes: X right, Y toward the viewer (back wall Y 0), metres",
                              H_plan_to_px_2720=homog(H_FLOOR), H_plan_to_px_4072=homog(S_c @ H_FLOOR),
                              H_px_2720_to_plan=homog(np.linalg.inv(H_FLOOR)),
                              check="the shell's board joints run along Y: in this plane they are vertical lines (verify check 2)"),
        homography_sofa_front=dict(plane=f"Y {SOFA_Y} (the sofa's front: the deck rail, the base band; the plinth is recessed to Y {SOFA['plinth_Y']})",
                                   coords="(X, Z) metres", H_plan_to_px_2720=homog(H_SOFA), H_plan_to_px_4072=homog(S_c @ H_SOFA)),
        homography_rug=dict(plane=f"Z {RUG_Z} (the rug's top; the tool only: the arrival has no rug)", H_plan_to_px_2720=homog(plane_H("z", RUG_Z))),
        regions=dict(file=rel(os.path.join(WORK, f"regions-{TAG}.npz")),
                     table="the old table: the r4 clay's table index, dilated 4 px (covers the furniture alpha's snap ring)",
                     plate="where the plate changed: the table region and the floor where the table's contact / cast shadow was lifted"),
        how="HDx2 / clip 2: the floor through H_floor and the sofa front through H_sofa_front, from this plate into each frame's own "
            "camera (the clay's geometry), with the exposure ratio measured in the wall / floor ring as in arrival-v2's pastes; holes that "
            "neither still sees from the clip's own floor (proposal a.6).",
        not_changed="the sofa, the armchair, the walls, the window: the same pixels; only the table, its shadow and the sofa's hidden foot")
    json.dump(note, open(os.path.join(WORK, f"motion-note-{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    return note


def layer_region(p):
    L = np.asarray(Image.open(p))
    a = L[..., 3]
    ys, xs = np.nonzero(a > 0)
    return dict(px=int((a > 0).sum()), alpha_255_px=int((a == 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])


def manifest_out():
    import copy
    rec = json.load(open(os.path.join(WORK, f"{TAG}.json")))
    r9 = json.load(open(os.path.join(LAY, "manifest-r9.json")))
    m = copy.deepcopy(r9)
    m.update(id=f"wm-living-room-m0-tool-layers-phase2-{TAG}", version=f"{TAG} (FB12 stage 0; supersedes manifest-r9.json for the tool; "
             "manifest-r9.json is kept for rollback)", date="2026-11-25", author="render-agent",
             brief="briefs/wm-fb12-stage0-clean-plate-2026-11-25.md (FB12 stage 0, code only, 0 tokens); "
                   "docs/proposals/wm-fb12-2026-11-25.md a.5-a.7 (path R)")
    m["approval"] = r9["approval"] + "; FB12 stage 0: code only, 0 tokens (FB12, owner 2026-11-25; the paid steps wait for FB12-T, SPEND2)"
    m["status"] = ("FB12 stage 0: the old coffee table (fixed-product walnut) is out of the plate. base = the clean plate; the rug layer "
                   "is whole under the old table; the cushion sets' sofa-shading at the old table's outline fades out; the bowl and the "
                   "candle holders (they stood on the old table) are hidden in the defaults, their layers kept. 11 defaults shown "
                   "(12 minus 2 hidden, the new table not yet in) + 10 variants. Not QA'd; for qa-agent. HD_PUBLIC=0 only.")
    P = rec["files"]
    relL = lambda k: os.path.relpath(os.path.join(REPO, P[k]), LAY_OUT)
    for l_ in m["layers"]:
        if l_["id"] == "base":
            l_.update(file=relL("plate"), how="FB12 stage 0: base.png without the old coffee table and its shadow (fb12_s0.py): phase 1's "
                      "model U = shell_v3 x S' x (1 - fa') + F' x fa', graded by the one v3c grade; base.png's own bytes outside the "
                      "changed region", sha256=rec["sha256"]["plate"], previous_file="base.png",
                      replaces_base_layers=["shell (z 0)", "fixed-furniture-shadow (z 34, multiply) without the table's part",
                                            "fixed-furniture (z 40): the sofa and the armchair only (the coffee table left the plate)"],
                      source=rel(os.path.join(WORK, f"shell-furniture-{TAG}.png")))
            l_.pop("source_v3c", None)
        elif l_["id"] == "rug":
            l_.update(file=relL("rug"), previous_file=l_["file"], region=layer_region(os.path.join(REPO, P["rug"])),
                      file_origin=dict(layer=f"new -{TAG} file: the old table's area filled (the rug plane, quilted from the visible rug, "
                                             "the room's light x S'), the table's baked shadow lifted", shadow="existing file, same bytes"))
        elif l_["id"] == "rug-shadow" and "rug_shadow" in P:
            l_.update(file=relL("rug_shadow"), previous_file=l_["file"],
                      fb12s0="the rug's contact shadow along its back edge, revealed left of the sofa (X -1.0..-0.89), sampled from the "
                             f"visible edge {EDGE_SHIFT} m to the left; R9's bytes elsewhere")
        elif l_["id"] in HIDDEN or l_["id"] in [h + "-shadow" for h in HIDDEN]:
            l_["hidden_in_defaults"] = True
            l_["hidden_note"] = ("FB12 stage 0: it stood on the old coffee table, which left the plate; hidden in the defaults and the "
                                 "preview until the new table is in (stage 1 re-seats it on the new top, proposal a.6). Layer kept, not deleted")
    for st, v in m["slot_cushions"]["sets"].items():
        k = f"cushions-{st}"
        if k in P:
            v["previous_layer"] = v["layer"]
            v["layer"] = relL(k)
            v["region"] = layer_region(os.path.join(REPO, P[k]))
        if k + "-shadow" in P:
            v["previous_shadow"] = v["shadow"]
            v["shadow"] = relL(k + "-shadow")
        v["fb12s0"] = ("inside the old table's region only: the throw's darkening of the sofa carried in from outside and faded over 40 px "
                       f"({rec['cushions'][st]['added_px']} new px), the set's shadow on the old table top replaced by its own continuation "
                       f"({rec['cushions'][st]['shadow_px_changed']} px); every R9 pixel outside the region kept")
    m["truths"] = dict(default={st: os.path.relpath(os.path.join(REPO, P[f"default-{st}"]), LAY_OUT) for st in r9["truths"]["default"]},
                       note="FB12 stage 0: each default = the 8-bit stack of this manifest (the hidden slots out) where the stack changed, "
                            "the R8 truth's own bytes elsewhere (RND2 0 outside); variant truths are R9's (no variant touches the old table)")
    m["defaults_hidden"] = list(HIDDEN)
    m["fb12s0"] = dict(record=rel(os.path.join(WORK, f"{TAG}.json")), motion_note=rel(os.path.join(WORK, f"motion-note-{TAG}.json")),
                       regions=os.path.relpath(os.path.join(WORK, f"regions-{TAG}.npz"), OUT),
                       files={k: os.path.relpath(os.path.join(REPO, v), OUT) for k, v in P.items()},
                       fixed_furniture=dict(layer=rel(os.path.join(WORK, f"fixed-furniture-{TAG}.png")),
                                            shadow=rel(os.path.join(WORK, f"fixed-furniture-shadow-{TAG}.png")),
                                            note="fa' = the sofa and the armchair only; the sofa's hidden foot synthesised (fb12_s0.py)"),
                       site_note="frontend-dev: read manifest-fb12s0.json; a layer with hidden_in_defaults is not drawn in the defaults "
                                 "(and not in the reveal) until the new table's manifest; the landing frame 702 = the new base")
    m["files"] = dict(build="../fb12_s0.py (all: plate, rug, cushions, defaults, sheet, records)", verify=f"verify_layers_{TAG}.py",
                      verification=f"verify-layers-{TAG}.json", sheet="../qa-sheet-fb12-stage0.jpg", record=f"../work-{TAG}/{TAG}.json",
                      asset_manifest_entries=f"asset-manifest-entries-{TAG}.json",
                      verify_usage=f"python3.12 -I verify_layers_{TAG}.py  (numpy + Pillow + OpenCV; exit 0 = pass)", previous_manifest="manifest-r9.json")
    m["tokens"] = dict(r9["tokens"], fb12_stage0=0)
    for k in ("changed_in_r7", "changed_in_r8", "changed_in_r9", "failed_in_r7", "pending"):
        if k in m:
            m.setdefault("history", {})[k] = m.pop(k)
    os.makedirs(LAY_OUT, exist_ok=True)
    p = os.path.join(LAY_OUT, f"manifest-{TAG}.json")
    json.dump(m, open(p, "w"), indent=1, ensure_ascii=False)
    return m


def asset_entries():
    rec = json.load(open(os.path.join(WORK, f"{TAG}.json")))
    P = rec["files"]
    base = dict(room="living-room", style="warm-modern", created="2026-11-25", model="code (0 tokens)", tokens=0)
    def e(id_, path, kind, status):
        fp = os.path.join(REPO, path)
        return dict(id=id_, path=path, kind=kind, **base, status=status, sha256=sha(fp), bytes=os.path.getsize(fp))
    st_layer = "warm-modern tool, FB12 stage 0: not QA'd (qa-agent next); HD_PUBLIC=0 only"
    E = [e(f"wm-tool-{TAG}-base", P["plate"], "layer: the clean M0 plate without the old coffee table (base, z 0); the arrival's landing frame 702", st_layer),
         e(f"wm-tool-{TAG}-rug", P["rug"], "layer: the rug (z 20), whole under the old table (filled in code)", st_layer)]
    if "rug_shadow" in P:
        E.append(e(f"wm-tool-{TAG}-rug-shadow", P["rug_shadow"], "shadow: the rug's (z 19), its revealed back edge left of the sofa", st_layer))
    for st in "BAC":
        if f"cushions-{st}" in P:
            E.append(e(f"wm-tool-{TAG}-cushions-{st}", P[f"cushions-{st}"], f"layer: cushion set {st} (z 55), the throw's darkening carried into the old table's region", st_layer))
        if f"cushions-{st}-shadow" in P:
            E.append(e(f"wm-tool-{TAG}-cushions-{st}-shadow", P[f"cushions-{st}-shadow"], f"shadow: cushion set {st} (z 54), the part on the old table top replaced", st_layer))
    for nm, kind in (("plate", "frame 1920 x 1080 (the camera frame): the clean plate, the arrival's landing (702)"),
                     ("default", "frame 1920 x 1080 (the camera frame): the rebuilt default scene, set B")):
        fp = os.path.join(OUT, f"{nm}-frame-{TAG}.png")
        if os.path.exists(fp):
            E.append(e(f"wm-tool-{TAG}-{nm}-frame", rel(fp), kind, "preview, not for the site before QA"))
    for st in "BAC":
        E.append(e(f"wm-tool-{TAG}-default-{st}", P[f"default-{st}"], f"truth: the rebuilt default scene, set {st} (bowl and candle holders hidden)", "QA material, not for the site"))
    for id_, path, kind in [(f"wm-tool-{TAG}-manifest", rel(os.path.join(LAY_OUT, f"manifest-{TAG}.json")), "layers manifest (supersedes manifest-r9 for the tool)"),
                            (f"wm-tool-{TAG}-verify", rel(os.path.join(LAY_OUT, f"verify-layers-{TAG}.json")), "verification record"),
                            (f"wm-tool-{TAG}-qa-sheet", rel(os.path.join(OUT, "qa-sheet-fb12-stage0.jpg")), "QA sheet: the old table's region at x2, before and after"),
                            (f"wm-tool-{TAG}-motion-note", rel(os.path.join(WORK, f"motion-note-{TAG}.json")), "note for motion-agent: the clean plate's path, sha and homographies"),
                            (f"wm-tool-{TAG}-record", rel(os.path.join(WORK, f"{TAG}.json")), "build record"),
                            (f"wm-tool-{TAG}-fixed-furniture", P["F"], "source: fixed furniture without the table (ungraded RGBA: the sofa and the armchair, the sofa's foot synthesised)"),
                            (f"wm-tool-{TAG}-fixed-furniture-shadow", P["S"], "source: the code furniture shadow without the table's part (multiply)"),
                            (f"wm-tool-{TAG}-shell-furniture", P["U"], "source: the ungraded clean plate (graded -> base-fb12s0.png)")]:
        E.append(e(id_, path, kind, "record / source, not for the site"))
    out = dict(note=f"to merge into assets/manifest.json 'assets' (render-agent 2026-11-25, FB12 stage 0)", assets=E)
    json.dump(out, open(os.path.join(LAY_OUT, f"asset-manifest-entries-{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    return E


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        rec, _, _ = build_all()
        print(json.dumps(rec, indent=1, ensure_ascii=False)[:4000])
    if cmd in ("all", "sheet"):
        print(sheet())
    if cmd in ("all", "frames"):
        print(frames())
    if cmd in ("all", "records"):
        print(json.dumps(records(), indent=1)[:600])
        manifest_out()
    if cmd == "entries":
        print(len(asset_entries()))
