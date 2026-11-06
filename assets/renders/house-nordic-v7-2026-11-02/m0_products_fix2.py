#!/usr/bin/env python3
"""
m0_products_fix2.py: QA G1 2026-11-06 (qa/reports/2026-11-06-m0-products-shelf-styles.md) fixes on the M0 1.2 products frame, 0 tokens, new files
only (render-agent, 2026-11-06):
  1. the magazine holder: the pass drew it ~1.9x its box (about 80 cm for the card's 45); its sprite scaled to the projected 45 x 32 x 40 holder
     (house plan 1.2.5, slots 1.8) with the rim at the box's top, the body below the scaled sprite continued in felt to the canvas edge (the pass's
     front pocket is not on the card and is left out), clear of the armchair; the felt lifted towards the card's charcoal (#45474B, L ~28)
  2. the pouf: moved and scaled onto the projected 45 / 36 ball at (1.45, 2.00) (box [0.905, 1.0, 0.956, 1.0]), leaving through the right and bottom edges
  3. the floor lamp's light: the pass's low-pass ratio (whose zone edge made a hard trapezoid on the wall) replaced by a smooth analytic light
     from the shade (an up and a down lobe on the wall, a pool on the sofa's right end and the throw), 2700 K, no straight edge anywhere
Everything else as m0-1-2-products-fix.png: the base m0-1-2-shell-seedream-fix.png, the basket, the lamp and the runner from the registered pass
(same tone gains, same alpha). Then lock_v2, "nothing else moved", grading v6 (grade_v6_m0.py) and the products' QA values.
  python3 m0_products_fix2.py build | check | grade | qa
Outputs (v9/): m0-1-2-products-fix2.png (+ .json), m0-1-2-products-fix2-lock-v2.json / .jpg, m0-1-2-products-fix2-graded-fix-v6.png,
m0-1-2-products-fix2-frame-fix-v6.png (the fixed M0 frame), -graded-os6-fix-v6.png, -masks-fix-v6.jpg, -measurements-fix-v6.json.
grade_v6_m0 reads <JID>-fix.json / -fix-base.json for the triptych and the round: m0-1-2-products-fix2-fix.json / -fix-base.json carry them.
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m0_products_pass as PP  # noqa: E402

REPO, OD, OD_REL, DATE = PP.REPO, PP.OD, PP.OD_REL, PP.DATE
JID2 = "m0-1-2-products-fix2"
OUT = os.path.join(OD, JID2 + ".png")
SPD = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix2/"
FELT_TARGET_L = 28.0           # the composite's felt (L*); grading v6 (+0.2 stop products, the toe) takes it to about 28 (the card's #45474B is L 30)
FELT_RGB = np.array([0x45, 0x47, 0x4B], np.float32) / 255.0
LAMP = dict(down=0.32, up=0.14, pool=0.26, wash=0.45, warm=(1.08, 1.0, 0.80))   # stops at the lobes' peaks; the added light's tint (2700 K against the wall)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def Lstar(img):
    return cv2.cvtColor(np.clip(img, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)[..., 0]


def frame_to_canvas(u, v, W=2736, H=1539):
    return (u * 3840 + 116) / 4072 * W, (v * 2160 + 65) / 2290 * H


def projected_mask(points, H=1539, W=2736, cam=None):
    """convex hull of the projected 3D points (all in front of the camera) on the canvas"""
    cam = cam or PP.CAM
    pts = []
    for P in points:
        u, v, d = PP.proj(P, cam)
        pts.append(frame_to_canvas(u, v, W, H))
    pts = np.array(pts, np.float32)
    hull = cv2.convexHull(pts)
    m = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(m, np.round(hull * 4).astype(np.int32), 1, shift=2)
    return m.astype(bool)


def holder_points():
    s, c = math.sin(math.radians(PP.CAM["yaw"])), math.cos(math.radians(PP.CAM["yaw"]))
    F = PP.box_faces(PP.HOLDER_XY, (-s, -c), 0.45, 0.32, 0.40, 0.0, 0.3)
    return [p for f, _ in F for p in f]


def pouf_points():
    out = []
    for i in range(72):
        for j in range(37):
            t, p = 2 * math.pi * i / 72, -math.pi / 2 + math.pi * j / 36
            out.append(np.array([1.45 + 0.225 * math.cos(p) * math.cos(t), 2.00 + 0.225 * math.cos(p) * math.sin(t), 0.18 + 0.18 * math.sin(p)]))
    return out


def row_extent(m, y):
    xs = np.nonzero(m[int(y)])[0]
    return (int(xs.min()), int(xs.max())) if len(xs) else None


def warp_sprite(img, alpha, s, src_anchor, dst_anchor, H, W):
    """uniform scale s about src_anchor, src_anchor -> dst_anchor (Lanczos, premultiplied)"""
    A = np.array([[s, 0, dst_anchor[0] - s * src_anchor[0]], [0, s, dst_anchor[1] - s * src_anchor[1]]], np.float32)
    pm = cv2.warpAffine(img * alpha[..., None], A, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = np.clip(cv2.warpAffine(alpha, A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0), 0, 1)
    col = pm / np.maximum(a[..., None], 1e-4)
    return np.clip(col, 0, 1), a, A


def felt_lift(img, alpha, rec):
    """the holder's felt (dark, unsaturated) to FELT_TARGET_L with the card's charcoal ratio; wood, tabs and magazines kept"""
    L = Lstar(img)
    hls = cv2.cvtColor(np.clip(img, 0, 1).astype(np.float32), cv2.COLOR_RGB2HLS)
    S = hls[..., 2]
    w = np.clip((38.0 - L) / 10.0, 0, 1) * np.clip((0.32 - S) / 0.14, 0, 1) * (alpha > 0.5)
    core = (w > 0.95)
    lin = s2l(img)
    Yraw = float(np.median((lin * PP_Y).sum(2)[core]))
    Ytgt = ((FELT_TARGET_L + 16) / 116) ** 3
    gain = Ytgt / max(Yraw, 1e-5)
    med = np.median(lin[core], 0)
    card = s2l(FELT_RGB)
    tint = (card / (card * PP_Y).sum()) / (med / max((med * PP_Y).sum(), 1e-6))
    tint = 1 + 0.5 * (tint - 1)          # half way to the card's cool grey: grading v6 neutralises the warm room a little more
    Ypix = np.maximum((lin * PP_Y).sum(2), 1e-5)
    gp = np.maximum(gain * (Ypix / Yraw) ** (FELT_GAMMA - 1.0), 1.0)          # the pass's felt contrast compressed (gamma 0.6): its lit edge was L 30 at a median of 8
    g = 1 + (gp[..., None] * tint[None, None, :] - 1) * w[..., None]
    out = l2s(lin * g)
    rec.update(felt_px=int(core.sum()), felt_L_before=round(float(np.median(L[core])), 1), felt_gain_linear=round(gain, 3),
               tint_rgb=[round(float(t), 3) for t in tint], felt_gamma=FELT_GAMMA, felt_L_after=round(float(np.median(Lstar(out)[core])), 1))
    return np.clip(out, 0, 1).astype(np.float32)


PP_Y = np.array([0.2126, 0.7152, 0.0722], np.float32)
KEEP_FRAC, BAND = 0.62, 12
FELT_GAMMA = 0.6
RIGHT_TARGET = 84.0
POCKET_X = (990, 1100)          # the pass's front pocket (canvas x, unscaled), not on the card


def holder_sprite(pt, sil, H, W, rec):
    """the scaled holder (RGB, alpha) on the canvas, the body continued below the scaled sprite in felt"""
    true = projected_mask(holder_points(), H, W)
    ys, xs = np.nonzero(sil)
    top_s = int(ys.min())
    # the rim row of the sprite (the widest body row near the top, below the tabs): 70 px under its top; the true holder's width there
    r_s = row_extent(sil, top_s + 70)
    tys = np.nonzero(true)[0]
    top_t = max(int(tys.min()), int(round(frame_to_canvas(0, 0.848, W, H)[1])))
    # scale: the sprite's body width (rows 60-160 below its top, median) onto the true holder's width at its visible rim rows
    wsp = np.median([np.ptp(np.nonzero(sil[y])[0]) for y in range(top_s + 60, min(H, top_s + 160))])
    wtr = np.median([np.ptp(np.nonzero(true[y])[0]) for y in range(top_t + 30, min(H, top_t + 90)) if true[y].any()])
    s = float(wtr / wsp)
    cxs = 0.5 * (r_s[0] + r_s[1])
    rows_t = [row_extent(true, y) for y in range(top_t + 30, min(H, top_t + 90)) if true[y].any()]
    cxt = float(np.median([0.5 * (a + b) for a, b in rows_t]))
    alpha = cv2.GaussianBlur(cv2.erode(sil.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)
    img = felt_lift(pt, alpha, rec)
    col, a, A = warp_sprite(img, alpha, s, (cxs, top_s), (cxt, top_t), H, W)
    # the body: below the front rim the sprite holds felt and the pass's pocket; keep the sprite down to keep_y, felt below it
    bottom_scaled = int(top_t + s * (H - 1 - top_s))
    keep_y = int(top_t + s * KEEP_FRAC * (H - 1 - top_s))     # under the front rim's lowest point (0.51 of the visible height), above the pocket (0.71)
    bottom_scaled = min(H, bottom_scaled)
    # the body's side edges: the scaled sprite's edges from keep_y down to its bottom, continued as straight lines
    left, right = [], []
    for y in range(keep_y, bottom_scaled - 2):
        e = row_extent(a > 0.5, y)
        if e:
            left.append((y, e[0]))
            right.append((y, e[1]))
    ly, lx = np.array(left).T
    ry, rx = np.array(right).T
    pl, pr_ = np.polyfit(ly, lx, 1), np.polyfit(ry, rx, 1)
    body = np.zeros((H, W), np.float32)
    for y in range(keep_y - 12, H):
        x0, x1 = np.polyval(pl, y), np.polyval(pr_, y)
        body[y, int(round(x0)):int(round(x1)) + 1] = 1
    body = cv2.GaussianBlur(body, (0, 0), 0.8)
    # the felt's shading per column: the scaled sprite's clean felt rows (keep_y to its bottom), the pass's front pocket columns bridged
    pk0, pk1 = [int(round(cxt + s * (x - cxs))) for x in POCKET_X]
    rows = col[keep_y:bottom_scaled - 2]
    rm = cv2.erode((a[keep_y:bottom_scaled - 2] > 0.98).astype(np.uint8), np.ones((1, 5), np.uint8)).astype(bool)
    prof = np.full((W, 3), np.nan, np.float32)
    for x in range(W):
        if pk0 - 4 <= x <= pk1 + 4:
            continue
        sel = rm[:, x]
        if sel.sum() > 6:
            prof[x] = np.median(rows[sel, x], 0)
    ok = np.nonzero(np.isfinite(prof[:, 0]))[0]
    for c in range(3):
        prof[:, c] = np.interp(np.arange(W), ok, prof[ok, c])
    prof = cv2.GaussianBlur(prof.reshape(1, W, 3), (0, 0), 3).reshape(W, 3)
    # the felt's grain: the high-pass of the clean felt (luminance), its std; synthesized as fine isotropic noise of the same std
    Lr = Lstar(rows)
    hp = (Lr - cv2.GaussianBlur(Lr, (0, 0), 2.5))
    colmask = np.ones(rm.shape, bool)
    colmask[:, max(0, pk0 - 4):pk1 + 5] = False
    sd = float(np.std(hp[rm & colmask]))
    rng = np.random.default_rng(7)
    nz = cv2.GaussianBlur(rng.standard_normal((H - keep_y, W)).astype(np.float32), (0, 0), 0.7)
    nz *= sd / max(float(nz.std()), 1e-6) / 100.0
    yy = np.arange(keep_y, H, dtype=np.float32)
    shade = (1.0 - 0.10 * np.clip((yy - keep_y) / max(1, H - keep_y), 0, 1))[:, None, None]      # a little darker towards the floor
    fill = np.clip(l2s(s2l(prof[None, :, :]) * shade) * (1 + nz[..., None] * 1.6), 0, 1)
    col2 = col.copy()
    a2 = a.copy()
    blend = np.clip((yy - keep_y) / 8.0, 0, 1)[:, None]                                          # an 8 px blend under keep_y
    a2[keep_y:] = (1 - blend) * a[keep_y:] + blend * body[keep_y:]
    col2[keep_y:] = (1 - blend[..., None]) * col[keep_y:] + blend[..., None] * fill
    rec.update(scale=round(s, 4), sprite_top_px=top_s, true_top_px=top_t, sprite_rim_centre_x=round(cxs, 1), true_centre_x=round(cxt, 1),
               width_sprite_px=float(wsp), width_true_px=float(wtr), scaled_sprite_bottom_px=bottom_scaled, body_from_px=keep_y, felt_grain_std_L=round(sd, 2), pocket_columns_scaled=[pk0, pk1],
               body_edges_slope_px_per_row=[round(float(pl[0]), 3), round(float(pr_[0]), 3)],
               how=("the pass's holder (grabCut core) scaled uniformly onto the projected 45 x 32 x 40 holder (width at its rim rows), the rim at "
                    "the box's top; below KEEP_FRAC of the scaled sprite (under the front rim) the body is felt: the sprite's clean felt per column (the pass's "
                    "front pocket bridged: not on the card), fine felt grain of the measured std, the side edges continued, 10 % darker to the canvas edge"))
    return col2, np.clip(a2, 0, 1), true


def pouf_sprite(pt, sil, region_alpha, H, W, rec):
    true = projected_mask(pouf_points(), H, W)
    ty = np.nonzero(true)[0].min()
    # the pass's pouf: the grabCut core misses its rims; the sprite is the lay region's alpha round the core (rug excluded by colour)
    ys, xs = np.nonzero(sil)
    top_s = int(ys.min())
    zone = np.zeros((H, W), bool)
    zone[top_s - 6:, max(0, xs.min() - 40):min(W, xs.max() + 40)] = True
    Lp = Lstar(pt)
    cand = (region_alpha > 0.5) & zone & (Lp > 60)
    cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand)
    kk = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == kk).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    m2 = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(m2, hull, 1)
    m2 = (m2 & ((region_alpha > 0.5) | sil)).astype(np.uint8)
    ys, xs = np.nonzero(m2)
    top_s = int(ys.min())
    cx_s = float(xs[ys <= top_s + 3].mean())
    # the scale: the sprite's width 60 px under its top onto the true ball's width 60 px under its top (in the canvas, before the right edge cuts it)
    def width_at(mask, y):
        e = row_extent(mask, y)
        return e[1] - e[0] if e else 0
    tys, txs = np.nonzero(true)
    cx_t = float(txs[tys <= ty + 3].mean())
    true_full = true.copy()
    wt = None
    # the projected silhouette runs past the canvas's right edge: its width at a row from its own left edge to its centre, doubled
    e = row_extent(true_full, ty + 60)
    wt = 2 * (cx_t - e[0])
    es = row_extent(m2.astype(bool), top_s + 60)
    ws = 2 * (cx_s - es[0])
    s = float(wt / ws)
    alpha = cv2.GaussianBlur(cv2.erode(m2, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.0)
    col, a, A = warp_sprite(pt, alpha, s, (cx_s, top_s), (cx_t, ty), H, W)
    rec.update(scale=round(s, 4), sprite_top_px=top_s, sprite_crown_x=round(cx_s, 1), true_top_px=int(ty), true_crown_x=round(cx_t, 1),
               width_60px_below_top=dict(sprite=round(float(ws), 1), true=round(float(wt), 1)),
               visible_frame_uv=None,
               how="the pass's pouf (its lay region round the grabCut core, rug left out by L < 60, convex) scaled and moved onto the projected 45 / 36 ball "
                   "(crown onto crown, the width 60 px under the crown matched); it leaves through the right and bottom edges")
    return col, a, true


def lamp_light(H, W, shade_mask, rec):
    """a smooth light from the shade: an up and a down lobe on the wall round the shade, a pool on the sofa's right end and the throw; a
    multiplier in linear light (>= 1), warm"""
    ys, xs = np.nonzero(shade_mask)
    sx0, sx1, sy0, sy1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, w, h = 0.5 * (sx0 + sx1), sx1 - sx0, sy1 - sy0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    down = np.exp(-0.5 * (((xx - cx) / (0.9 * w)) ** 2 + ((yy - (sy1 + 0.6 * h)) / (2.0 * h)) ** 2))
    down *= np.clip((yy - sy1) / (0.6 * h), 0, 1) ** 1.5                                       # the lobe opens under the shade's rim (none beside it)
    up = np.exp(-0.5 * (((xx - (cx + 0.2 * w)) / (0.9 * w)) ** 2 + ((yy - (sy0 - 0.3 * h)) / (1.0 * h)) ** 2))
    up *= np.clip((sy0 - yy) / (0.5 * h), 0, 1) ** 1.5                                         # and above its top
    # the pool: the sofa's right end and the throw (frame uv 0.80-0.87 x 0.60-0.76), ~70 cm radius at ~4.3 m
    px, py = frame_to_canvas(0.845, 0.66, W, H)
    pool = np.exp(-0.5 * (((xx - px) / 150.0) ** 2 + ((yy - py) / 120.0) ** 2))
    # the wash on the back wall's right end, right of the shade (towards the corner: the review's right-end points 0.952 / 0.97): the old pass lit
    # it (+9 L there, nothing left of the shade) and the Bible's right end (82-86) counts on it; a smooth lobe that fades out across the shade
    wash = np.exp(-0.5 * (((xx - (sx1 + 0.3 * w)) / (0.6 * w)) ** 2 + ((yy - (sy0 + 0.3 * h)) / (1.6 * h)) ** 2))
    wash *= 1.0 / (1.0 + np.exp(-(xx - cx) / (0.18 * w)))
    stops = LAMP["down"] * down + LAMP["up"] * up + LAMP["pool"] * pool + LAMP["wash"] * wash
    f = 2.0 ** stops - 1.0
    warm = np.array(LAMP["warm"], np.float32)
    mult = 1.0 + f[..., None] * warm[None, None, :]
    rec["lamp_light"] = dict(shade_canvas_px=[int(sx0), int(sx1), int(sy0), int(sy1)], peak_stops=dict(down=LAMP["down"], up=LAMP["up"], pool=LAMP["pool"], wash=LAMP["wash"]),
                             tint_rgb=list(LAMP["warm"]), pool_centre_frame_uv=[0.845, 0.66], pool_sigma_px=[150, 120],
                             how=("multiplier in linear light on the base: two Gaussian lobes on the wall (down: 0.9 x shade width, 2.0 x shade height, "
                                  "opening under the rim; up: 0.9 x / 1.0 x, 0.2 w to the right (the corner), opening above the top; a wash on the wall's right end, right of the "
                                  "shade (0.6 w x 1.6 h, fading out across the shade by a logistic of 0.18 w); nothing left of the shade, so it stays 6-8 over the wall) and a Gaussian pool on the sofa's right end and the throw; 2700 K tint; "
                                  "no zone, no edge (it replaces the pass's low-pass ratio, whose zone edge drew the trapezoid of G1.12)"))
    return mult.astype(np.float32)


def build():
    os.makedirs(SPD, exist_ok=True)
    b = PP.load01(PP.BASE)
    H, W = b.shape[:2]
    pr = PP.load01(os.path.join(OD, PP.PASS_ID + "-reg.png"))
    fixrec = json.load(open(os.path.join(OD, PP.JID + "-fix.json")))
    gains = np.array(fixrec["tone"]["gains_rgb"], np.float32)
    pt = np.clip(l2s(s2l(pr) * gains), 0, 1).astype(np.float32)
    LM = np.load(PP.DL + "lay-masks.npz")
    a_soft = LM["alpha"].astype(np.float32)
    sils = {k: LM[k] for k in ("magazine-holder", "basket", "pouf", "floor-lamp", "runner")}
    # each pixel of the old lay's alpha to its nearest product (distance to each grabCut core)
    keys = list(sils)
    dist = np.stack([cv2.distanceTransform((~sils[k]).astype(np.uint8), cv2.DIST_L2, 5) for k in keys], 0)
    lab = np.argmin(dist, 0)
    alpha_of = {k: a_soft * (lab == i) for i, k in enumerate(keys)}
    rec = dict(asset_id=JID2, date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0_products_fix2.py", qa="qa/reports/2026-11-06-m0-products-shelf-styles.md (G1)",
               base=OD_REL + "m0-1-2-shell-seedream-fix.png", products_from=OD_REL + PP.PASS_ID + "-reg.png", tone_gains_rgb=fixrec["tone"]["gains_rgb"])
    # 3. the lamp light on the base (linear light)
    La = Lstar(pt)
    shade = np.load(PP.DL + "new-products.npz")["floor-lamp"] & (La > 65)      # the lay's lamp region (shade hull + pole), not grabCut's core (it took the glow)
    shade[int(frame_to_canvas(0, 0.53, W, H)[1]):] = False                      # the shade's box is v 0.389-0.484 (the glow below it is not the shade)
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(shade.astype(np.uint8))
    shade = lab_ == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))
    mult = lamp_light(H, W, shade, rec)
    out = np.clip(l2s(s2l(b) * mult), 0, 1).astype(np.float32)
    # the basket, the lamp and the runner as laid before (same pass, same tone, same alpha)
    for k in ("basket", "floor-lamp", "runner"):
        a = alpha_of[k][..., None]
        out = out * (1 - a) + pt * a
    # 2. the pouf
    prec = {}
    pc, pa, ptrue = pouf_sprite(pt, sils["pouf"], alpha_of["pouf"], H, W, prec)
    out = out * (1 - pa[..., None]) + pc * pa[..., None]
    # 1. the holder: its soft shadow on the rug (window light from the left: a little to the right), then the sprite
    hrec = {}
    # the holder's mask: grabCut's core (it left out the wood bars and part of the tabs) and, in the lay's region round it, what is not rug
    # (felt L < 40, or wood / cognac S > 0.22): the rug, lit or in the pass's shadow, is pale and unsaturated
    hls = cv2.cvtColor(pt, cv2.COLOR_RGB2HLS)
    core = sils["magazine-holder"]
    near = cv2.dilate(core.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    extra = (alpha_of["magazine-holder"] > 0.5) & ((hls[..., 2] > 0.22) | ((La < 40) & near))      # dark only next to the core (not the pass's shadow)
    hm = cv2.morphologyEx((core | extra).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(hm)
    hm = (lab_ == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    inv = 1 - hm
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n_):
        if st_[i, cv2.CC_STAT_AREA] < 3000:
            hm[lab_ == i] = 1
    hc, ha, htrue = holder_sprite(pt, hm.astype(bool), H, W, hrec)
    sh = cv2.GaussianBlur(np.roll(ha, 18, axis=1), (0, 0), 14) * (1 - ha)
    occ = cv2.GaussianBlur(ha, (0, 0), 5) * (1 - ha)
    dark = 1 - 0.22 * np.clip(sh, 0, 1) - 0.12 * np.clip(occ, 0, 1)
    out = np.clip(l2s(s2l(out) * dark[..., None]), 0, 1)
    out = out * (1 - ha[..., None]) + hc * ha[..., None]
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT)
    lz = np.zeros((H, W), np.float32)
    lz[int(PP.LAMP_LIGHT_ZONE[2] * H):int(PP.LAMP_LIGHT_ZONE[3] * H), int(PP.LAMP_LIGHT_ZONE[0] * W):int(PP.LAMP_LIGHT_ZONE[1] * W)] = 1
    np.savez_compressed(SPD + "layer-fix2.npz", mult=mult.astype(np.float16), dark=dark.astype(np.float16), a_holder=ha.astype(np.float16),
                        a_pouf=pa.astype(np.float16), a_basket=alpha_of["basket"].astype(np.float16), a_lamp=alpha_of["floor-lamp"].astype(np.float16),
                        a_runner=alpha_of["runner"].astype(np.float16), lamp_zone=np.maximum(lz, (np.abs(mult - 1).max(2) > 0.01).astype(np.float32)).astype(np.float16))
    # masks for grading (the new product pixels) and the records
    npd = dict(np.load(PP.DL + "new-products.npz"))
    npd["magazine-holder"] = ha > 0.5
    npd["pouf"] = pa > 0.5
    np.savez_compressed(SPD + "new-products-fix2.npz", **npd)
    def fuv(m):
        ys, xs = np.nonzero(m)
        return [round(((xs.min() / W) * 4072 - 116) / 3840, 3), round(((xs.max() / W) * 4072 - 116) / 3840, 3),
                round(((ys.min() / H) * 2290 - 65) / 2160, 3), round(((ys.max() / H) * 2290 - 65) / 2160, 3)]
    hrec.update(rendered_frame_uv=fuv(ha > 0.5), projected_frame_uv=fuv(htrue), brief_box=list(PP.BOX_FRAME["magazine-holder"]))
    prec.update(rendered_frame_uv=fuv(pa > 0.5), projected_frame_uv=fuv(ptrue), brief_box=list(PP.BOX_FRAME["pouf"]))
    # clear of the armchair: the clay's armchair (id 3) against the holder
    I = cv2.imread(os.path.join(OD, "m0-clay-r5b-index.png"), cv2.IMREAD_UNCHANGED)
    arm = I == 3
    xs_arm = np.nonzero(arm[int(frame_to_canvas(0, 0.85, W, H)[1]):, :])[1]
    hx0 = np.nonzero(ha > 0.5)[1].min()
    hrec["armchair_clay_right_px_below_v0_85"] = int(xs_arm.max()) if len(xs_arm) else None
    hrec["gap_to_armchair_frame_u"] = round((hx0 - xs_arm.max()) / W * 4072 / 3840, 3) if len(xs_arm) else None
    rec["magazine_holder"], rec["pouf"] = hrec, prec
    nem = PP.nothing_else_moved(out.astype(np.float32), b)
    rec["nothing_else_moved_after_lay"] = nem
    fx = json.load(open(os.path.join(OD, PP.JID + "-fix.json")))
    rec.update(placement=fx["placement"], prints=fx.get("prints"), output=OD_REL + JID2 + ".png")
    json.dump(rec, open(os.path.join(OD, JID2 + ".json"), "w"), indent=1, ensure_ascii=False)
    # grade_v6_m0's inputs (the triptych and the round of the base)
    json.dump(dict(asset_id=JID2 + "-fix", note="alias record for grade_v6_m0 (it reads <JID>-fix.json): the composite is " + OD_REL + JID2 + ".png",
                   placement=fx["placement"], prints=fx.get("prints")), open(os.path.join(OD, JID2 + "-fix.json"), "w"), indent=1, ensure_ascii=False)
    fb = json.load(open(os.path.join(OD, PP.JID + "-fix-base.json")))
    json.dump(dict(asset_id=JID2 + "-fix-base", note=fb.get("note"), wall_round=fb["wall_round"]), open(os.path.join(OD, JID2 + "-fix-base.json"), "w"), indent=1)
    print(json.dumps(dict(holder=hrec, pouf=prec, lamp=rec["lamp_light"]["shade_canvas_px"], nem=nem), indent=0)[:3500])


def check():
    import fix_m0_12 as M
    import m0_model_test as T
    PL = M._pipeline()
    PL.VF.RETAKES[JID2] = PL.JOBS["m0-v8b"]
    J = T.jr()
    if not any(j["id"] == JID2 for j in J["jobs"]):
        J["jobs"].append(dict(id=JID2, out_dir=OD_REL, model="code", tokens=0, status="QA G1 fixes on the products frame (holder, pouf, lamp light)"))
        T.save_jr(J)
    PL.VF.RETAKES_JOBS = T.JR
    lk = PL.LK.run_frame(JID2, render_path=OUT, out_path=os.path.join(OD, JID2 + "-lock-v2.json"), overlay_path=os.path.join(OD, JID2 + "-lock-v2.jpg"), date=DATE)
    s, v = lk["summary"], lk["verdict"]
    rec = json.load(open(os.path.join(OD, JID2 + ".json")))
    rec["lock_v2"] = dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                          tile_after=s["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"],
                          verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")})
    # against the earlier laid frame too: only the holder, the pouf and the lamp light changed
    a = PP.load01(OUT)
    f1 = PP.load01(os.path.join(OD, PP.JID + "-fix.png"))
    H, W = a.shape[:2]
    d = np.abs(a - f1).max(2) * 255
    zones = {"holder (frame u 0.25-0.47, v 0.78-1)": (0.25, 0.47, 0.78, 1.04), "pouf (u 0.84-1.03, v 0.90-1.03)": (0.84, 1.04, 0.90, 1.04),
             "lamp light (u 0.75-1.03, v 0.15-0.95)": (0.75, 1.04, 0.15, 0.95)}
    other = np.ones((H, W), bool)
    for k, (u0, u1, v0, v1) in zones.items():
        x0, y0 = frame_to_canvas(u0, v0, W, H)
        x1, y1 = frame_to_canvas(u1, v1, W, H)
        other[int(y0):int(y1), int(x0):int(x1)] = False
    rec["against_products_fix"] = dict(rule="the fix2 frame against m0-1-2-products-fix.png: max |delta| outside the three fix areas",
                                       mean_outside=round(float(d[other].mean()), 3), p999_outside=round(float(np.percentile(d[other], 99.9)), 2))
    json.dump(rec, open(os.path.join(OD, JID2 + ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(lock=rec["lock_v2"], nem=rec["nothing_else_moved_after_lay"], vs_fix=rec["against_products_fix"]), indent=0))


def grade():
    import grade_v6_m0 as G
    G.JID = JID2
    G.SRC = OUT
    G.V5 = os.path.join(OD, "m0-1-2-shell-seedream-graded-fix-v5.png")
    G.SP = SPD + "v6/"
    G.SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0-products-fix2-v6-sheet-2026-11-06.jpg")
    os.makedirs(G.SP, exist_ok=True)
    a = G.load(G.SRC)
    Mk, mrec = G.masks(a)
    d = dict(np.load(G.SP + "masks.npz"))
    npd = dict(np.load(SPD + "new-products-fix2.npz"))
    shell, I, ol = d["shell"].copy(), d["I"].copy(), d["obj_label"].copy()
    ids = {"magazine-holder": 601, "basket": 602, "pouf": 603, "floor-lamp": 604}
    gray = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    La = G.Lmap(a)
    npd["floor-lamp shade"] = npd["floor-lamp"] & (La > 65)
    ids["floor-lamp shade"] = 605
    for k, i in ids.items():
        m = npd[k]
        I[m] = i
        ol[m] = i
        soft = np.clip(PP.guided1(gray, m.astype(np.float32), 2, 1e-4), 0, 1)
        shell = np.minimum(shell, 1 - soft)
    np.savez_compressed(G.SP + "masks.npz", shell=shell.astype(np.float32), art=d["art"], rnd=d["rnd"], cubes=d["cubes"], shell_kind=d["shell_kind"], obj_label=ol, I=I)
    rec = json.load(open(G.SP + "masks.json"))
    shd = float(np.median(La[npd["floor-lamp shade"]]))
    G.P0["obj_stops"] = {"605": float(np.clip(np.log2(PP_s2l(0.99) / PP_s2l(shd / 100)) + 0.2, 0.3, 1.5))}
    G.TGT["right"] = RIGHT_TARGET          # the Bible's right end (82-86); the lamp's wash lights it now (the pass's light did), so the solver need not lift
                                           # the whole right end (+0.43 stop without the wash, which also lit the wall beside the shade)
    rec["new_products"] = dict(how="the four products set to product (+0.2 stop; the holder's felt lifted in the composite instead, see " + JID2 + ".json), "
                                   "ids 601-604; 605 the floor-lamp shade as an emitter", px={k: int(npd[k].sum()) for k in ids}, obj_stops=G.P0["obj_stops"])
    json.dump(rec, open(G.SP + "masks.json", "w"), indent=1)
    G.run()
    qa()


def PP_s2l(x):
    return float(s2l(np.float32(x)))


def qa():
    import grade_v6_m0 as G
    G.SP = SPD + "v6/"
    d = dict(np.load(G.SP + "masks.npz"))
    npd = dict(np.load(SPD + "new-products-fix2.npz"))
    g = G.load(os.path.join(OD, JID2 + "-graded-fix-v6.png"))
    H, W = g.shape[:2]
    L = G.Lmap(g)
    qa_ = {}
    hm = npd["magazine-holder"]
    hls = cv2.cvtColor(g.astype(np.float32), cv2.COLOR_RGB2HLS)
    felt = hm & (L < 45) & (hls[..., 2] < 0.3)
    felt = cv2.erode(felt.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    h_, s_, l_ = G.hsl(g[felt].mean(0))
    qa_["charcoal holder felt (L < 45, S < 0.3, eroded): L [25-35], card #45474B L 30"] = dict(H=h_, S=s_, L=l_, L_median=round(float(np.median(L[felt])), 1), ok=bool(25 <= l_ <= 35))
    h_, s_, l_ = G.hsl(g[npd["basket"]].mean(0))
    qa_["jute basket: H [25-40], S [25-55]"] = dict(H=h_, S=s_, L=l_, ok=bool(25 <= h_ <= 40 and 25 <= s_ <= 55))
    shade = npd["floor-lamp"] & (L > 70)
    ys, xs = np.nonzero(shade)
    shade_L = float(np.median(L[shade]))
    wall = np.zeros((H, W), bool)
    wall[int(0.36 * H):int(0.42 * H), max(0, xs.min() - 140):xs.min() - 40] = True
    wall &= ~npd["floor-lamp"]
    wL = float(np.median(L[wall]))
    qa_["floor-lamp shade over the wall left of it [>= 6; QA: 6-8 is fine]"] = dict(shade=round(shade_L, 1), wall=round(wL, 1), diff=round(shade_L - wL, 1), ok=bool(shade_L - wL >= 6))
    b0 = G.load(os.path.join(OD, "m0-1-2-shell-seedream-graded-fix-v6.png"))
    sofa_end = np.zeros((H, W), bool)
    sofa_end[int(0.62 * H):int(0.80 * H), int(0.80 * W):int(0.88 * W)] = True
    sofa_end &= (d["I"] == 1) | (d["I"] == 41)
    dL = float(np.median(L[sofa_end]) - np.median(G.Lmap(b0)[sofa_end]))
    qa_["pool on the sofa's right end and the throw: L over the Nordic v6 without the lamp [>= 2]"] = dict(delta_L=round(dL, 1), ok=bool(dL >= 2))
    qa_["whole frame: pixels at 255, black point"] = dict(at_255=int((g.max(2) >= 254.5 / 255).sum()), black_p01=round(float(np.percentile(L, 0.1)), 1))
    n = json.load(open(os.path.join(OD, JID2 + "-measurements-fix-v6.json")))
    n["products_qa"] = qa_
    n["input"] = OD_REL + JID2 + ".png"
    json.dump(n, open(os.path.join(OD, JID2 + "-measurements-fix-v6.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(qa_, indent=1))
    print("not_met", n.get("not_met"))


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "build":
        build()
    if w == "check":
        check()
    if w == "grade":
        grade()
    if w == "qa":
        qa()
