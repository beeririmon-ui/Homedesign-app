#!/usr/bin/env python3
"""
art_m0_12.py: the geometric triptych (RND3 = a; framed-art-aliexpress-minimal-geometric-triptych-prints, three different prints as in
the listing) put on the wall above the sofa in M0 1.2 and M0p 1.2, in code (render-agent, 2026-11-04, 0 var2 tokens; the coordinator's
message after the owner's RND3 answer). New files only: <id>-fix2.png / -fix2.json, lock_v2 -> <id>-fix2-lock-v2.json / .jpg, grading
v5 -> <id>-graded-fix2-v5.png etc. The QA'd -fix stills are read, never written.

Source: the old M0 r2 (house plan 1.1 camera: (1.25, 5.55, 1.20), yaw 25, u0 0.52, v0 0.46) has the triptych rendered on the same back wall
(the plane Y = 0), lit by the same sconce pair; but its three frames all carry print 1 (the RND2 "one print duplicated" fault).
  1. the three oak frames found in the old still (outer edges: per-row / per-column gradient maxima, robust line fits, corners);
  2. prints 2 and 3 of the listing (SKU colour 2 / 3, 50 x 70) put into frames 2 and 3: the rendered print-1 marks filled from the
     oatmeal around them, the listing's charcoal shapes (circle; three bars) drawn in, mapped by the listing's own frame -> the rendered
     frame (the listing print 1 mapped the same way lands on the rendered print-1 marks: IoU checked), in the rendered charcoal colour,
     shaded by the rendered oatmeal's light;
  3. each frame warped by the homography old frame -> its place on the wall of the new camera: three 50 x 70 frames, 6 cm apart (162 x 70),
     centred at (0.20, 0, 1.475) = the centre of the framed-art slot box of living-room.json 1.6 m0_1_2 (that box is the projection of a
     154 x 95 envelope at that centre with the 1.2.3 camera (0.83, 4.64, 1.20), yaw 25, u0 0.47, v0 0.50, to 0.0004); the round-5b clay
     has no framed-art placeholder (empty per the designer, RND2), so the box is projected from the plan with the same camera;
  4. the frames' soft shadow on the old wall carried as a ratio map (old / the membrane-cleaned old wall) by the triptych's homography;
     light: a per-channel gain, low-pass new wall / low-pass cleaned old wall (sigma 40 px); grain: the new wall's high-pass std added.
The camera-only wall-plane homography (old camera -> new camera) is measured too (where it would have put the old triptych).
  python3 art_m0_12.py [m0 | m0p | all] [--no-lock]
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
import fix_v7 as F  # noqa: E402
import fix_m0_12 as M  # noqa: E402

REPO = M.REPO
DATE = "2026-11-04"
OLD = os.path.join(REPO, "assets/renders/living-room/nordic/v7/m0-v7-r2.png")
REF1 = os.path.join(REPO, "assets/renders/house-nordic-2026-10-25/refs/ae01-alicdn-com-kf-Sf7d0432bcab14eba8f32b9c6f2232d36B-jpg.jpg")
DL = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-triptych/"
REF2 = DL + "S210e02a3b02f4ed5b97114be268d1ddaW.png"      # listing image of SKU colour 2 (50x70: 12000039454944614 family), viewed only
REF3 = DL + "S26d83984104f47f1a00c7d5adaa4e2ceR.png"      # colour 3
REF_URLS = {1: "https://ae01.alicdn.com/kf/Sf7d0432bcab14eba8f32b9c6f2232d36B.jpg", 2: "https://ae01.alicdn.com/kf/S210e02a3b02f4ed5b97114be268d1ddaW.jpg",
            3: "https://ae01.alicdn.com/kf/S26d83984104f47f1a00c7d5adaa4e2ceR.jpg"}
CAM_OLD = dict(loc=(1.25, 5.55, 1.20), yaw=25, u0=0.52, v0=0.46)
CAMS = {"m0-v8b-r2": dict(loc=(0.83, 4.64, 1.20), yaw=25, u0=0.47, v0=0.50), "pose-m0p-v8b": dict(loc=(0.83, 4.64, 1.20), yaw=0, u0=0.47, v0=0.50)}
ART_C = (0.20, 1.475)                    # wall X, Z of the art centre (slot box centre)
FRAME_W, FRAME_H, GAP = 0.50, 0.70, 0.06
FRAMES_OLD_APPROX = [(1592, 1778, 425, 693), (1802, 2001, 415, 695), (2024, 2233, 403, 696)]


def H_wall(cam, fx=0.6667, fy=1.1852):
    """Wall plane Y = 0: (X, Z, 1) -> frame uv (homogeneous), the projection of tone_r4.project / pan_reproject."""
    s, c = math.sin(math.radians(cam["yaw"])), math.cos(math.radians(cam["yaw"]))
    cx, cy, cz = cam["loc"]
    d = np.array([-s, 0, s * cx + c * cy])
    x = np.array([c, 0, -c * cx + s * cy])
    return np.vstack([cam["u0"] * d + fx * x, cam["v0"] * d + fy * np.array([0, -1, cz]), d])


def C_canvas(W, H):
    """frame uv -> canvas px of the overscan still (4072 x 2290 canvas, the 3840 x 2160 frame at (116, 65))."""
    return np.array([[3840.0 / 4072 * W, 0, 116.0 / 4072 * W], [0, 2160.0 / 2290 * H, 65.0 / 2290 * H], [0, 0, 1]])


def apply_h(Hm, pts):
    p = np.c_[np.asarray(pts, float), np.ones(len(pts))] @ Hm.T
    return p[:, :2] / p[:, 2:3]


INSET_PX = 1.2


def inset_quad(q, d):
    """q (TL TR BR BL) with each side moved inward by d px (lines offset along their normals, corners re-intersected)."""
    c = q.mean(0)
    lines = []
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        pa, pb = q[a], q[b]
        t = (pb - pa) / np.linalg.norm(pb - pa)
        n = np.array([-t[1], t[0]])
        if np.dot(n, c - pa) < 0:
            n = -n
        lines.append((pa + n * d, t))
    out = []
    for i in range(4):                       # corner i = side (i-1) x side i
        (p1, t1), (p2, t2) = lines[i - 1], lines[i]
        A = np.array([t1, -t2]).T
        s_ = np.linalg.solve(A, p2 - p1)
        out.append(p1 + s_[0] * t1)
    return np.array(out)


def frame_rects():
    """The three frames on the wall: (X0, X1, Z0, Z1), left to right."""
    xc, zc = ART_C
    x0 = xc - (3 * FRAME_W + 2 * GAP) / 2
    return [(x0 + k * (FRAME_W + GAP), x0 + k * (FRAME_W + GAP) + FRAME_W, zc - FRAME_H / 2, zc + FRAME_H / 2) for k in range(3)]


def quad_of_rect(Hc, r):
    X0, X1, Z0, Z1 = r
    return apply_h(Hc, [(X0, Z1), (X1, Z1), (X1, Z0), (X0, Z0)])          # TL, TR, BR, BL in the image


def fit_line(ts, ps):
    """p = a t + b, least squares, refit without points > 1.5 px off."""
    ts, ps = np.asarray(ts, float), np.asarray(ps, float)
    for _ in range(3):
        A = np.c_[ts, np.ones_like(ts)]
        (a, b), *_ = np.linalg.lstsq(A, ps, rcond=None)
        r = np.abs(ps - (a * ts + b))
        keep = r <= max(1.5, np.percentile(r, 80))
        if keep.all():
            break
        ts, ps = ts[keep], ps[keep]
    return a, b, float(np.sqrt(np.mean((ps - (a * ts + b)) ** 2)))


def frame_quad(img, box, win=14, band_L=None):
    """The outer edge of one frame (TL TR BR BL). The inner edge (mat -> oak) is crisp on all four sides; the outer edge is crisp only
    on the lit left and top sides (on the right and the bottom the frame's side face runs into its cast shadow), so: inner edges on all
    sides, the oak band's width measured on the left / top (inner -> outer crossing), outer = inner + that width on every side."""
    _, Lm, _ = M.hls(img)
    Lm = cv2.GaussianBlur(Lm, (0, 0), 0.7)
    x0, x1, y0, y1 = box
    ys = np.arange(int(y0 + 0.2 * (y1 - y0)), int(y1 - 0.2 * (y1 - y0)), 2)
    xs = np.arange(int(x0 + 0.2 * (x1 - x0)), int(x1 - 0.2 * (x1 - x0)), 2)

    def cross(prof, i_from, thr, below):
        """first fractional index >= i_from where prof goes below (below=True) / back above thr."""
        for i in range(i_from, len(prof) - 1):
            a_, b_ = prof[i], prof[i + 1]
            if (below and a_ >= thr > b_) or ((not below) and a_ < thr <= b_):
                return i + (thr - a_) / (b_ - a_)
        return None

    def scan(prof):
        """prof from inside (mat) outward: (inner edge, outer edge or None)."""
        mat = float(np.median(prof[:4]))
        lo = float(prof.min())
        thr = (mat + lo) / 2
        a_ = cross(prof, 0, thr, True)
        if a_ is None:
            return None, None
        j = int(np.argmin(prof[int(a_):int(a_) + 10])) + int(a_)
        b_ = cross(prof, j, thr, False)
        return a_, b_
    Li, Ri, Ti, Bi, wid = [], [], [], [], []
    for y in ys:
        a_, b_ = scan(Lm[y, x0 + win:x0 - win - 1:-1])
        if a_ is not None:
            Li.append((y, x0 + win - a_))
            if b_ is not None:
                wid.append(b_ - a_)
        a_, _ = scan(Lm[y, x1 - win:x1 + win + 1])
        if a_ is not None:
            Ri.append((y, x1 - win + a_))
    for x in xs:
        a_, b_ = scan(Lm[y0 + win:y0 - win - 1:-1, x])
        if a_ is not None:
            Ti.append((x, y0 + win - a_))
            if b_ is not None:
                wid.append(b_ - a_)
        a_, _ = scan(Lm[y1 - win:y1 + win + 1, x])
        if a_ is not None:
            Bi.append((x, y1 - win + a_))
    w = float(np.median(wid)) if wid else 6.0
    L = [(t, p - w) for t, p in Li]
    R = [(t, p + w) for t, p in Ri]
    T = [(t, p - w) for t, p in Ti]
    B = [(t, p + w) for t, p in Bi]
    la, lb, le = fit_line(*zip(*L))        # x = la y + lb
    ra, rb, re_ = fit_line(*zip(*R))
    ta, tb, te = fit_line(*zip(*T))        # y = ta x + tb
    ba, bb, be = fit_line(*zip(*B))

    def cross(va, vb, ha, hb):             # x = va y + vb, y = ha x + hb
        y = (ha * vb + hb) / (1 - ha * va)
        return (va * y + vb, y)
    q = np.array([cross(la, lb, ta, tb), cross(ra, rb, ta, tb), cross(ra, rb, ba, bb), cross(la, lb, ba, bb)])
    return q, dict(rms_px=[round(le, 2), round(re_, 2), round(te, 2), round(be, 2)], oak_band_px=round(w, 2))


def listing(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    h = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2HLS).astype(np.float32)
    L, S = h[..., 1] / 2.55, h[..., 2] / 2.55
    oak = (S > 25) & (L < 75) & (L > 30)
    ys, xs = np.nonzero(oak)
    fx0, fx1, fy0, fy1 = xs.min(), xs.max(), ys.min(), ys.max()
    inner = np.zeros(L.shape, bool)
    inner[fy0 + int(0.03 * (fy1 - fy0)):fy1 - int(0.03 * (fy1 - fy0)), fx0 + int(0.04 * (fx1 - fx0)):fx1 - int(0.04 * (fx1 - fx0))] = True
    mark = np.clip((45.0 - L) / 20.0, 0, 1) * inner          # the charcoal, anti-aliased
    quad = np.array([(fx0, fy0), (fx1 + 1, fy0), (fx1 + 1, fy1 + 1), (fx0, fy1 + 1)], float)
    return dict(mark=mark.astype(np.float32), quad=quad, size=a.shape[:2])


def build_layer(old):
    """The old still with prints 2 / 3 in frames 2 / 3; returns (image, the three frame quads, records)."""
    H, W = old.shape[:2]
    quads, fits = [], []
    for b in FRAMES_OLD_APPROX:
        q, r = frame_quad(old, b)
        quads.append(q)
        fits.append(r)
    _, Lo, So = M.hls(old)
    refs = {k: listing(p) for k, p in ((1, REF1), (2, REF2), (3, REF3))}
    out = old.copy()
    recs = []
    for k, q in enumerate(quads):
        G = cv2.getPerspectiveTransform(refs[1]["quad"].astype(np.float32), q.astype(np.float32))
        m1 = cv2.warpPerspective(refs[1]["mark"], G, (W, H), flags=cv2.INTER_AREA)
        fmask = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(fmask, np.round(q).astype(np.int32), 1)
        inner = cv2.erode(fmask, np.ones((15, 15), np.uint8)) > 0
        rmark = ((Lo < 42) & inner).astype(np.uint8)
        rmark = cv2.morphologyEx(rmark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        # the rendered marks vs the listing's print-1 marks mapped by the frame: offset of their centroids and IoU
        ys, xs = np.nonzero(rmark)
        ys1, xs1 = np.nonzero(m1 > 0.5)
        d = (float(xs.mean() - xs1.mean()), float(ys.mean() - ys1.mean()))
        G2 = np.array([[1, 0, d[0]], [0, 1, d[1]], [0, 0, 1]]) @ G           # the listing layout as the render drew it
        m1b = cv2.warpPerspective(refs[1]["mark"], G2, (W, H), flags=cv2.INTER_AREA) > 0.5
        iou = float((m1b & (rmark > 0)).sum() / max(1, (m1b | (rmark > 0)).sum()))
        rec = dict(frame=k + 1, quad_px=np.round(q, 1).tolist(), edge_fit=fits[k], print=k + 1, marks_centroid_offset_px=[round(d[0], 2), round(d[1], 2)],
                   print1_marks_iou_after_offset=round(iou, 3))
        if k > 0:
            charcoal = np.median(old[rmark > 0], 0)
            hole = cv2.dilate(rmark, np.ones((5, 5), np.uint8)).astype(np.float32)
            valid = (inner & (hole < 0.5)).astype(np.float32)
            import fix_v8 as F8
            filled = F8.nc_fill(out, hole, valid, scales=((4, 4), (10, 10), (25, 25)))
            out = np.where((hole > 0.5)[..., None], filled, out)
            # light: the oatmeal around, relative to its median, carries the gradient onto the new charcoal
            oat = cv2.GaussianBlur(F.gray(out), (0, 0), 12.0)
            oat_med = float(np.median(F.gray(out)[inner & (hole < 0.5)]))
            shade = np.clip(oat / max(oat_med, 1.0), 0.8, 1.2)[..., None]
            Gk = cv2.getPerspectiveTransform(refs[k + 1]["quad"].astype(np.float32), q.astype(np.float32))
            Gk2 = np.array([[1, 0, d[0]], [0, 1, d[1]], [0, 0, 1]]) @ Gk
            mk = cv2.warpPerspective(refs[k + 1]["mark"], Gk2, (W, H), flags=cv2.INTER_AREA)
            mk = np.clip(mk, 0, 1) * inner
            out = out * (1 - mk[..., None]) + (charcoal[None, None, :] * shade) * mk[..., None]
            rec.update(marks_removed_px=int(rmark.sum()), marks_added_px=int((mk > 0.5).sum()), charcoal_rgb=[round(float(c), 1) for c in charcoal],
                       listing_image=REF_URLS[k + 1])
        recs.append(rec)
    return out, quads, recs


def place(jid, old_mod, old, quads_old, recs_layer, preview=False):
    new = M.still(jid) if False else F.load(M.out_fix(jid))
    H, W = new.shape[:2]
    Hn = C_canvas(W, H) @ H_wall(CAMS[jid])
    Ho = C_canvas(old.shape[1], old.shape[0]) @ H_wall(CAM_OLD)
    targets = [quad_of_rect(Hn, r) for r in frame_rects()]
    # --- the camera-only homography (old image -> wall -> new image) and where it puts the old triptych
    Hcam = Hn @ np.linalg.inv(Ho)
    allo = np.vstack(quads_old)
    via_cam = apply_h(Hcam, allo)
    allt = np.vstack(targets)
    wall_old = apply_h(np.linalg.inv(Ho), allo)
    size_old_cm = dict(width=round(float((wall_old[[1, 2, 5, 6, 9, 10], 0].max() - wall_old[[0, 3, 4, 7, 8, 11], 0].min()) * 100), 1),
                       height=round(float((wall_old[:, 1].max() - wall_old[:, 1].min()) * 100), 1),
                       centre=[round(float(wall_old[:, 0].mean()), 3), round(float(wall_old[:, 1].mean()), 3)])

    def bbox(p):
        return p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()
    bt, bc = bbox(allt), bbox(via_cam)
    s1920 = 1920.0 / (3840.0 / 4072 * W)
    cam_only = dict(width_ratio=round((bc[1] - bc[0]) / (bt[1] - bt[0]), 4), height_ratio=round((bc[3] - bc[2]) / (bt[3] - bt[2]), 4),
                    corner_error_px_1920=round(float(np.abs(via_cam - allt).max() * s1920), 1),
                    centre_offset_px_1920=[round(float((via_cam[:, 0].mean() - allt[:, 0].mean()) * s1920), 1), round(float((via_cam[:, 1].mean() - allt[:, 1].mean()) * s1920), 1)])
    # --- the old wall cleaned (membrane through the ring around the frames) and the frames' shadow ratio
    Ho_, Wo_ = old.shape[:2]
    fm = np.zeros((Ho_, Wo_), np.uint8)
    for q in quads_old:
        cv2.fillConvexPoly(fm, np.round(q).astype(np.int32), 1)
    hole = cv2.dilate(fm, np.ones((9, 9), np.uint8)).astype(np.float32)
    region = cv2.dilate(fm, np.ones((121, 121), np.uint8)).astype(np.float32)
    dom = region.copy()
    clean = M.laplace_fill(old, hole, dom, pad=70)
    band = np.clip(cv2.dilate(fm, np.ones((81, 81), np.uint8)).astype(np.float32) - hole, 0, 1)
    ratio = np.where((band > 0.5)[..., None], np.clip(old / np.maximum(clean, 1.0), 0.55, 1.02), 1.0).astype(np.float32)
    ratio = cv2.GaussianBlur(ratio, (0, 0), 1.5)
    # the triptych's homography (outer corners) for the shadow; each frame its own for the frames
    outer_o = np.array([quads_old[0][0], quads_old[2][1], quads_old[2][2], quads_old[0][3]], np.float32)
    outer_t = np.array([targets[0][0], targets[2][1], targets[2][2], targets[0][3]], np.float32)
    Ht = cv2.getPerspectiveTransform(outer_o, outer_t)
    rat_n = cv2.warpPerspective(ratio, Ht, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(1, 1, 1))
    clean_n = cv2.warpPerspective(cv2.GaussianBlur(clean, (0, 0), 40.0), Ht, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    tm = np.zeros((H, W), np.uint8)
    for q in targets:
        cv2.fillConvexPoly(tm, np.round(q).astype(np.int32), 1)
    near = cv2.dilate(tm, np.ones((161, 161), np.uint8)) > 0
    gain = cv2.GaussianBlur(new, (0, 0), 40.0) / np.maximum(clean_n, 1.0)
    gain = np.clip(gain, 0.6, 1.8)
    out = new * np.clip(rat_n, 0.55, 1.02)
    layer = np.zeros_like(new)
    alpha = np.zeros((H, W), np.float32)
    for q_o, q_t in zip(quads_old, targets):
        # the source quad inset by INSET_PX (old pixels) along each side's normal and mapped onto the full target quad: the frame's
        # anti-aliased outer pixel row (half wall, a staircase on the sloped top) stays behind; the frame is ~0.6 % wider than drawn
        q_s = inset_quad(q_o, INSET_PX)
        Hk = cv2.getPerspectiveTransform(q_s.astype(np.float32), q_t.astype(np.float32))
        l_ = cv2.warpPerspective(old_mod, Hk, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        a_ = np.zeros((H * 4, W * 4), np.uint8)
        cv2.fillConvexPoly(a_, np.round(q_t * 4).astype(np.int32), 255, lineType=cv2.LINE_AA)
        a_ = cv2.resize(a_, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        layer = layer * (1 - a_[..., None]) + l_ * a_[..., None]
        alpha = np.maximum(alpha, a_)
    layer = layer * gain
    # grain: the new wall's high-pass std around the art vs the warped frames' (their mats)
    hp = lambda img: F.gray(img) - cv2.GaussianBlur(F.gray(img), (0, 0), 1.5)  # noqa: E731
    wall_ring = near & (tm == 0) & (cv2.dilate(tm, np.ones((41, 41), np.uint8)) == 0)
    s_new = float(np.std(hp(new)[wall_ring]))
    inner_t = cv2.erode(tm, np.ones((9, 9), np.uint8)) > 0
    s_lay = float(np.std(hp(layer)[inner_t & (F.gray(layer) > np.percentile(F.gray(layer)[inner_t], 60))]))
    add = math.sqrt(max(0.0, s_new ** 2 - s_lay ** 2))
    rng = np.random.default_rng(7)
    noise = rng.normal(0, add, (H, W)).astype(np.float32)[..., None]
    layer = layer + noise
    out = out * (1 - alpha[..., None]) + layer * alpha[..., None]
    out = np.clip(out, 0, 255)
    rec = dict(targets_px=[np.round(t, 1).tolist() for t in targets], camera_only_homography=dict(matrix=np.round(Hcam / Hcam[2, 2], 6).tolist(), **cam_only),
               old_triptych_on_the_wall=size_old_cm, light_gain_median_rgb=[round(float(x), 3) for x in np.median(gain[tm > 0], 0)],
               grain=dict(new_wall_hp_std=round(s_new, 2), layer_hp_std=round(s_lay, 2), added_std=round(add, 2)))
    return out, rec, targets, tm


def measure_placed(img, targets, s1920):
    """An independent check of the placed frames: along each side of each target quad, profiles across the side (inside -> outside,
    +-10 px) of the output's lightness; the outer edge = where the profile, past its darkest (oak) point, rises back through the midpoint
    of the oak and the wall 8-10 px outside; its signed offset from the target side (+ = outside), median per side."""
    _, Lm, _ = M.hls(img)
    Lm = cv2.GaussianBlur(Lm, (0, 0), 0.6)
    H, W = Lm.shape
    sides_all, worst = [], 0.0
    for t in targets:
        cen = t.mean(0)
        offs = []
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
            pa, pb = t[a], t[b]
            d = pb - pa
            n = np.array([d[1], -d[0]]) / np.linalg.norm(d)
            if np.dot(n, (pa + pb) / 2 - cen) < 0:
                n = -n                              # outward
            vals = []
            for f in np.linspace(0.15, 0.85, 25):
                p0 = pa + f * d
                ts = np.arange(-10, 10.01, 0.25)
                xs, ys = p0[0] + ts * n[0], p0[1] + ts * n[1]
                prof = cv2.remap(Lm, xs.astype(np.float32).reshape(1, -1), ys.astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR).ravel()
                i_min = int(np.argmin(prof[:48]))           # the oak, inside the side (t <= +2)
                outside = float(np.median(prof[-8:]))
                thr = (prof[i_min] + outside) / 2
                j = next((j for j in range(i_min, len(prof) - 1) if prof[j] < thr <= prof[j + 1]), None)
                if j is not None:
                    vals.append(ts[j] + (thr - prof[j]) / max(prof[j + 1] - prof[j], 1e-3) * 0.25)
            offs.append(round(float(np.median(vals)), 2) if vals else None)
        sides_all.append(offs)
        worst = max(worst, max(abs(o) for o in offs if o is not None))
    return dict(side_offsets_px_canvas=sides_all, side_order="top, right, bottom, left (+ = outside the target)",
                worst_side_offset_px_canvas=round(worst, 2), worst_side_offset_px_1920=round(worst * s1920, 2),
                box_ratio_w=1.0, box_ratio_h=1.0, box_ratio_note="by construction: the frames' alpha is the projected target quad (3 x 50 x 70, 6 cm gaps)")


def run(jid, do_lock=True):
    old = F.load(OLD)
    old_mod, quads_old, recs_layer = build_layer(old)
    out, rec, targets, tm = place(jid, old_mod, old, quads_old, recs_layer)
    od = os.path.join(REPO, M.OUT[jid])
    p = os.path.join(od, jid + "-fix2.png")
    F.save(out, p)
    W = out.shape[1]
    s1920 = 1920.0 / (3840.0 / 4072 * W)
    placed = measure_placed(out, targets, s1920)
    note = dict(asset_id=jid + "-fix2", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/art_m0_12.py",
                what=("RND3 (a): the geometric triptych (framed-art-aliexpress-minimal-geometric-triptych-prints, prints 1 / 2 / 3 of the listing, left to right) "
                      "on the wall above the sofa, in code from the old M0 r2's rendered triptych"),
                source=dict(base=os.path.relpath(M.out_fix(jid), REPO), art_from=os.path.relpath(OLD, REPO), cameras=dict(old=CAM_OLD, new=CAMS[jid]),
                            listing_images={str(k): v for k, v in REF_URLS.items()}),
                wall_target=dict(centre_XZ=list(ART_C), frames_cm="3 x 50 x 70, 6 cm apart (162 x 70)", why="the slot box of living-room.json 1.6 m0_1_2 = the projection of a 154 x 95 envelope centred at (0.20, 0, 1.475) with the 1.2.3 camera; the round-5b clay has no framed-art placeholder (empty per RND2)"),
                prints=recs_layer, placement=rec, placed_measured=placed,
                how=("old frames: outer oak edges by gradient maxima, robust line fits; prints 2 / 3: the rendered print-1 marks filled (normalised convolution of the oatmeal), "
                     "the listing's charcoal mapped by the listing frame -> rendered frame homography (+ the centroid offset that puts the listing's print-1 marks on the "
                     "rendered ones), in the rendered charcoal colour x the oatmeal's light; each frame warped by its homography (Lanczos, 4x anti-aliased alpha) onto "
                     "its 50 x 70 place on the wall; the shadow as a ratio map (old / membrane-cleaned old wall) by the triptych's homography; light gain = low-pass new "
                     "wall / low-pass cleaned old wall (sigma 40); grain added to the new wall's high-pass std"))
    json.dump(note, open(os.path.join(od, jid + "-fix2.json"), "w"), indent=1, ensure_ascii=False)
    print(jid, json.dumps(dict(camera_only=rec["camera_only_homography"], old_cm=rec["old_triptych_on_the_wall"], placed=placed,
                               prints=[(r["frame"], r["marks_centroid_offset_px"], r["print1_marks_iou_after_offset"]) for r in recs_layer]), indent=0))
    if do_lock:
        lock_grade(jid)
    return note


def lock_grade(jid):
    PL = M._pipeline()
    od = os.path.join(REPO, M.OUT[jid])
    p = os.path.join(od, jid + "-fix2.png")
    lock = PL.LK.run_frame(jid, render_path=p, out_path=os.path.join(od, jid + "-fix2-lock-v2.json"), overlay_path=os.path.join(od, jid + "-fix2-lock-v2.jpg"), date=DATE)
    r = PL.P.process(jid, p, "-fix2-v5", "v2", "auto", "none", od, f"{jid}-fix2: M0 1.2 composite + the triptych, grading v5", exposure="bible",
                     grade_mode="v5")
    s, v = lock["summary"], lock["verdict"]
    note_p = os.path.join(od, jid + "-fix2.json")
    note = json.load(open(note_p))
    note["checks"] = dict(lock_v2=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                                       tile_after=s["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"],
                                       verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")}),
                          grade_v5=dict(stops=r["grade"]["exposure"]["applied_stops"], target=r["bible_v3"]["target_L"], range=r["bible_v3"]["range"],
                                        measured=r["bible_v3"]["measured_L"], meets_bible=r["bible_v3"]["meets_bible"],
                                        fails=[k for k, x in r["checks"].items() if k.startswith("bible_") and x is False], outputs=r["outputs"]))
    json.dump(note, open(note_p, "w"), indent=1, ensure_ascii=False)
    print(jid, "lock", note["checks"]["lock_v2"], "grade", {k: note["checks"]["grade_v5"][k] for k in ("measured", "range", "meets_bible", "fails")})


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    dl = "--no-lock" not in sys.argv
    if w in ("m0", "all"):
        run("m0-v8b-r2", dl)
    if w in ("m0p", "all"):
        run("pose-m0p-v8b", dl)
