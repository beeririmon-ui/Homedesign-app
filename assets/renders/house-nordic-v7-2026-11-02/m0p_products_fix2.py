#!/usr/bin/env python3
"""
m0p_products_fix2.py: M0p 1.2 for P0 (QA G1 2026-11-06, §2 and G1.14; render-agent, 0 tokens, new files only).
  rwh       the right-wall homography: lock_v2 left the local-warp composite (pose-m0p-1-2-shell-seedream-fix-warp.png) at tiles 5.5 / 4.6 on the
            back-right corner and the right wall (drawn in a slightly different perspective). One homography (ECC on gradient magnitude, render ->
            clay) for the right wall's plane, fitted on the right wall, its corner, cornice and skirting lines; applied to the right wall (clay
            index 7, its skirting and cornice) and faded out over 30 px -> pose-m0p-1-2-shell-seedream-fix-rwh.png (+ lock_v2, shell check)
  products  the M0 products of the fixed M0 frame (m0-1-2-products-fix2.png: the holder, the basket, the floor lamp and its light, the runner)
            carried into M0p: M0 and M0p share the camera's point (0.83, 4.64, 1.20) and differ only in yaw (25 / 0), so one rotation homography
            maps every M0 pixel to its M0p pixel at any depth (no parallax). The pouf is not carried: M0p sees its whole upper body, M0 only its
            top (the canvas edge cuts it at M0p v ~0.93). The M0p shell composite's short runner is taken off the table where the new one does
            not cover it. Tone: one linear gain per channel (M0's back wall against M0p's). -> pose-m0p-1-2-products-fix2.png (+ .json, lock_v2)
  grade     grading v6 (grade_v6_m0p.py) with the carried products in the product mask -> pose-m0p-1-2-products-fix2-graded-fix-v6.png,
            -frame-fix-v6.png (the M0p frame for P0), -measurements-fix-v6.json
  sheet     P0 pair sheet: M0p | M0, both graded v6
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m0_products_pass as PP  # noqa: E402
import m0p_seedream as MP  # noqa: E402

REPO, OD, OD_REL, DATE = PP.REPO, PP.OD, PP.OD_REL, PP.DATE
SRC = os.path.join(OD, MP.JID + "-fix-warp.png")
RWH_ID = MP.JID + "-fix-rwh"
RWH = os.path.join(OD, RWH_ID + ".png")
JP = "pose-m0p-1-2-products-fix2"
OUT = os.path.join(OD, JP + ".png")
M0_FIX2 = os.path.join(OD, "m0-1-2-products-fix2.png")
INDEX = os.path.join(OD, "m0p-clay-r5b-index.png")
SPD = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/m0p-fix2/"
LAYER = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fix2/layer-fix2.npz"
SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0p-m0-products-fix2-p0-sheet-2026-11-06.jpg")
FX, FY, U0, V0 = 0.6667, 1.1852, 0.47, 0.50
MOTION = cv2.MOTION_AFFINE


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((np.clip(x, 0, None) + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def load01(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def gradmag(img, sigma=1.5):
    g = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    g = cv2.GaussianBlur(g, (0, 0), sigma)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
    return m / max(float(np.percentile(m, 99.5)), 1e-6)


def rwh():
    import fix_m0_12 as M
    R = load01(SRC)
    H, W = R.shape[:2]
    C = np.asarray(Image.open(MP.CLAY).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    I = cv2.imread(INDEX, cv2.IMREAD_UNCHANGED)
    rw = (I == 7)
    xs_rw = np.nonzero(rw)[1]
    xc = int(xs_rw.min())                                                       # the back-right corner's column in the clay
    near = np.zeros((H, W), bool)
    near[:, max(0, xc - 40):] = True
    fit = cv2.dilate(rw.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & near
    fit &= np.isin(I, [5, 7, 8, 9, 11, 13])                                     # the shell only (no furniture edges)
    s = 2
    gC = cv2.resize(gradmag(C), (W // s, H // s), interpolation=cv2.INTER_AREA)
    gR = cv2.resize(gradmag(R), (W // s, H // s), interpolation=cv2.INTER_AREA)
    m2 = cv2.resize(fit.astype(np.uint8), (W // s, H // s), interpolation=cv2.INTER_NEAREST)
    # the motion model: a full homography slides along the wall's few lines (a plain wall gives it nothing to hold on to: 34 px median drift,
    # a step at the skirting's end); an affine keeps it to the lines' own offsets
    Hm = np.eye(2, 3, dtype=np.float32)
    cc, Hm = cv2.findTransformECC(gC, gR, Hm, MOTION, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 400, 1e-7), m2, 5)
    Hm = np.vstack([Hm, [0, 0, 1]])
    S = np.diag([s, s, 1]).astype(np.float64)
    Hf = S @ Hm.astype(np.float64) @ np.linalg.inv(S)                          # clay px -> render px (full size)
    Rw = cv2.warpPerspective(R, Hf, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    # where: the right wall, its skirting and cornice (right of the corner), faded over 30 px; the corner column itself fades in
    app = (rw | (np.isin(I, [11, 13, 9]) & near & (np.arange(W)[None, :] >= xc - 4))).astype(np.uint8)
    app = cv2.dilate(app, np.ones((9, 9), np.uint8))
    a = cv2.GaussianBlur(app.astype(np.float32), (0, 0), 10)
    a = np.clip(np.maximum(a, cv2.erode(app, np.ones((21, 21), np.uint8)).astype(np.float32)), 0, 1)
    out = R * (1 - a[..., None]) + Rw * a[..., None]
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(RWH)
    # displacement the homography makes on the right wall (render px)
    ys, xs = np.nonzero(rw[::8, ::8])
    pts = np.stack([xs * 8, ys * 8, np.ones_like(xs)], 0).astype(np.float64)
    q = Hf @ pts
    q = q[:2] / q[2]
    disp = np.hypot(q[0] - pts[0], q[1] - pts[1])
    PL = M._pipeline()
    MP.register(PL, RWH_ID)
    lk = MP.lock(PL, RWH_ID, RWH, "")
    sh = MP.shell(RWH, RWH_ID)
    rec = dict(asset_id=RWH_ID, date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0p_products_fix2.py rwh", source=OD_REL + MP.JID + "-fix-warp.png",
               homography=dict(model="affine (ECC, cv2.MOTION_AFFINE; the homography drifted 34 px along the lines)", ecc=round(float(cc), 4), clay_to_render=np.round(Hf, 6).tolist(), fitted_on="the right wall (clay index 7) +20 px, right of the corner - 40 px, shell classes only",
                               applied_to="the right wall, its skirting, cornice and ceiling edge right of the corner; feathered 10 px",
                               displacement_px_on_right_wall=dict(median=round(float(np.median(disp)), 2), max=round(float(disp.max()), 2))),
               lock_v2=lk, shell=dict(raw_max_px=sh["raw_max_px"], per_line=sh["per_line"], verdict=sh["verdict"]),
               before=json.load(open(os.path.join(OD, MP.JID + "-fix-warp.json")))["lock_v2"], output=OD_REL + RWH_ID + ".png")
    json.dump(rec, open(os.path.join(OD, RWH_ID + ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(h=rec["homography"]["displacement_px_on_right_wall"], ecc=rec["homography"]["ecc"], lock=lk, shell=sh["raw_max_px"]), indent=0))


def dense():
    """the second local warp: as m0p_warp.py (phase correlation of gradient magnitude, 160 px windows on a 48 px grid, robust smooth field),
    but only the code-placed art (the triptych, the round) protected: the shell lines are now aligned too (the corner, the cornice, the right
    wall's skirting and floor line, which the first warp kept as drawn). On the local-warp composite -> pose-m0p-1-2-shell-seedream-fix-rwh.png"""
    import fix_m0_12 as M
    import lock_v2 as LK
    import m0p_warp as MW
    import fix_v7 as F
    a = F.load(SRC)
    H, W = a.shape[:2]
    clay = LK.load_rgb(MP.CLAY)
    r16, c16 = MW.grad16(np.clip(a / 255.0, 0, 1).astype(np.float32)), MW.grad16(clay)
    n = json.load(open(os.path.join(OD, MP.JID + "-fix.json")))
    prot = np.zeros((H, W), np.uint8)
    for q in n["placement"]["targets_px"]:
        cv2.fillConvexPoly(prot, np.round(np.array(q)).astype(np.int32), 1)
    rr = json.load(open(os.path.join(OD, MP.JID + "-fix-base.json")))["wall_round"]["rendered"]
    cv2.ellipse(prot, ((rr["centre_px"][0], rr["centre_px"][1]), (rr["axes_px"][0] + 20, rr["axes_px"][1] + 20), 0), 1, -1)
    fy0, fy1 = int(round(65 / 2290 * H)), int(round(2225 / 2290 * H))
    fx0, fx1 = int(round(116 / 4072 * W)), int(round(3956 / 4072 * W))
    p16 = cv2.resize(prot[fy0:fy1, fx0:fx1].astype(np.float32), (1920, 1080), interpolation=cv2.INTER_NEAREST) > 0.5
    ys, xs, dx, dy = MW.field(r16, c16, p16)
    measured = int(np.isfinite(dx).sum())
    dxs, dys = MW.smooth(dx), MW.smooth(dy)
    fxg = cv2.resize(dxs, (len(xs) * MW.STEP, len(ys) * MW.STEP), interpolation=cv2.INTER_CUBIC)
    fyg = cv2.resize(dys, (len(xs) * MW.STEP, len(ys) * MW.STEP), interpolation=cv2.INTER_CUBIC)
    FXf = np.zeros((1080, 1920), np.float32)
    FYf = np.zeros_like(FXf)
    y0, x0 = ys[0] - MW.STEP // 2, xs[0] - MW.STEP // 2
    FXf[y0:y0 + fxg.shape[0], x0:x0 + fxg.shape[1]] = fxg[:1080 - y0, :1920 - x0]
    FYf[y0:y0 + fyg.shape[0], x0:x0 + fyg.shape[1]] = fyg[:1080 - y0, :1920 - x0]
    FXf = cv2.GaussianBlur(FXf, (0, 0), 24)
    FYf = cv2.GaussianBlur(FYf, (0, 0), 24)
    keep = 1 - cv2.GaussianBlur(cv2.dilate(p16.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 20)
    FXf, FYf = FXf * np.clip(keep, 0, 1), FYf * np.clip(keep, 0, 1)
    sc = (3840 / 4072 * W) / 1920.0
    FXc = np.zeros((H, W), np.float32)
    FYc = np.zeros((H, W), np.float32)
    bx = cv2.resize(FXf, (int(round(1920 * sc)), int(round(1080 * sc))), interpolation=cv2.INTER_LINEAR) * sc
    by = cv2.resize(FYf, (int(round(1920 * sc)), int(round(1080 * sc))), interpolation=cv2.INTER_LINEAR) * sc
    hh, ww = min(bx.shape[0], H - fy0), min(bx.shape[1], W - fx0)
    FXc[fy0:fy0 + hh, fx0:fx0 + ww] = bx[:hh, :ww]
    FYc[fy0:fy0 + hh, fx0:fx0 + ww] = by[:hh, :ww]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    out = cv2.remap(a.astype(np.float32), gx + FXc, gy + FYc, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    F.save(np.clip(out, 0, 255), RWH)
    PL = M._pipeline()
    MP.register(PL, RWH_ID)
    lk = MP.lock(PL, RWH_ID, RWH, "")
    sh = MP.shell(RWH, RWH_ID)
    rec = dict(asset_id=RWH_ID, date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0p_products_fix2.py dense", source=OD_REL + MP.JID + "-fix-warp.png",
               tried=dict(homography="ECC homography on the right wall's lines: it drifted along them (median 34 px, max 108) and left a step at the skirting's end; "
                                     "tiles 4.62 (top, u 0.5-0.75) / 1.56 (bottom-right)",
                          affine="ECC affine on the same: median 7 px; tiles 3.9 / 3.69"),
               method="a second dense local warp (m0p_warp.py's field) with only the code-placed art protected: the shell lines aligned too",
               grid=dict(measured_cells=measured, cells=int(dx.size)),
               field_px_1920=dict(dx_min=round(float(FXf.min()), 2), dx_max=round(float(FXf.max()), 2), dy_min=round(float(FYf.min()), 2), dy_max=round(float(FYf.max()), 2)),
               lock_v2=lk, shell=dict(raw_max_px=sh["raw_max_px"], per_line=sh["per_line"], verdict=sh["verdict"]),
               before=json.load(open(os.path.join(OD, MP.JID + "-fix-warp.json")))["lock_v2"], output=OD_REL + RWH_ID + ".png")
    json.dump(rec, open(os.path.join(OD, RWH_ID + ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(field=rec["field_px_1920"], lock=lk, shell=sh["raw_max_px"], per_line=sh["per_line"]), indent=0))


def ecc_field(r16, c16, prot16, win=240, step=80):
    """ECC translation (render gradient against clay gradient) in overlapping windows; kept where the clay has structure and ECC holds"""
    H, W = c16.shape
    ys = list(range(win // 2, H - win // 2 + 1, step))
    xs = list(range(win // 2, W - win // 2 + 1, step))
    dx = np.full((len(ys), len(xs)), np.nan, np.float32)
    dy = np.full_like(dx, np.nan)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            b = c16[y - win // 2:y + win // 2, x - win // 2:x + win // 2]
            a = r16[y - win // 2:y + win // 2, x - win // 2:x + win // 2]
            if prot16[y, x] or b.mean() < 2.0:
                continue
            Wm = np.eye(2, 3, dtype=np.float32)
            try:
                cc, Wm = cv2.findTransformECC(b / (b.max() + 1e-6), a / (a.max() + 1e-6), Wm, cv2.MOTION_TRANSLATION,
                                              (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), None, 5)
            except cv2.error:
                continue
            if cc > 0.6 and abs(Wm[0, 2]) < 10 and abs(Wm[1, 2]) < 10:
                dx[i, j], dy[i, j] = Wm[0, 2], Wm[1, 2]
    return ys, xs, dx, dy


def dense2(iters=2):
    """the shell's residual (the corner, the cornice, the right wall's lines) taken out by a smooth field of windowed ECC translations
    (render gradient against the clay's, 240 px windows every 80 px at 1920, ECC > 0.6), the code-placed art protected; twice"""
    import fix_m0_12 as M
    import lock_v2 as LK
    import m0p_warp as MW
    import fix_v7 as F
    a = F.load(SRC).astype(np.float32)
    H, W = a.shape[:2]
    clay = LK.load_rgb(MP.CLAY)
    c16 = MW.grad16(clay)
    n = json.load(open(os.path.join(OD, MP.JID + "-fix.json")))
    prot = np.zeros((H, W), np.uint8)
    for q in n["placement"]["targets_px"]:
        cv2.fillConvexPoly(prot, np.round(np.array(q)).astype(np.int32), 1)
    rr = json.load(open(os.path.join(OD, MP.JID + "-fix-base.json")))["wall_round"]["rendered"]
    cv2.ellipse(prot, ((rr["centre_px"][0], rr["centre_px"][1]), (rr["axes_px"][0] + 20, rr["axes_px"][1] + 20), 0), 1, -1)
    fy0, fy1 = int(round(65 / 2290 * H)), int(round(2225 / 2290 * H))
    fx0, fx1 = int(round(116 / 4072 * W)), int(round(3956 / 4072 * W))
    p16 = cv2.resize(prot[fy0:fy1, fx0:fx1].astype(np.float32), (1920, 1080), interpolation=cv2.INTER_NEAREST) > 0.5
    sc = (3840 / 4072 * W) / 1920.0
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    TX = np.zeros((H, W), np.float32)
    TY = np.zeros((H, W), np.float32)
    hist = []
    cur = a.copy()
    for it in range(iters):
        r16 = MW.grad16(np.clip(cur / 255.0, 0, 1).astype(np.float32))
        ys, xs, dx, dy = ecc_field(r16, c16, p16)
        dxs, dys = MW.smooth(dx), MW.smooth(dy)
        FXf = cv2.resize(dxs, (1920, 1080), interpolation=cv2.INTER_CUBIC) if False else None
        # the grid's centres -> a dense 1920 x 1080 field (bilinear between window centres, held at the borders)
        gxs, gys = np.array(xs, np.float32), np.array(ys, np.float32)
        X16, Y16 = np.meshgrid(np.arange(1920, dtype=np.float32), np.arange(1080, dtype=np.float32))
        fi = np.interp(X16[0], gxs, np.arange(len(xs), dtype=np.float32))
        fj = np.interp(Y16[:, 0], gys, np.arange(len(ys), dtype=np.float32))
        FI, FJ = np.meshgrid(fi, fj)
        FXf = cv2.remap(dxs.astype(np.float32), FI.astype(np.float32), FJ.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        FYf = cv2.remap(dys.astype(np.float32), FI.astype(np.float32), FJ.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        FXf = cv2.GaussianBlur(FXf, (0, 0), 30)
        FYf = cv2.GaussianBlur(FYf, (0, 0), 30)
        keep = 1 - cv2.GaussianBlur(cv2.dilate(p16.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 20)
        FXf, FYf = FXf * np.clip(keep, 0, 1), FYf * np.clip(keep, 0, 1)
        bx = cv2.resize(FXf, (int(round(1920 * sc)), int(round(1080 * sc))), interpolation=cv2.INTER_LINEAR) * sc
        by = cv2.resize(FYf, (int(round(1920 * sc)), int(round(1080 * sc))), interpolation=cv2.INTER_LINEAR) * sc
        FXc = np.zeros((H, W), np.float32)
        FYc = np.zeros((H, W), np.float32)
        hh, ww = min(bx.shape[0], H - fy0), min(bx.shape[1], W - fx0)
        FXc[fy0:fy0 + hh, fx0:fx0 + ww] = bx[:hh, :ww]
        FYc[fy0:fy0 + hh, fx0:fx0 + ww] = by[:hh, :ww]
        # outside the frame (the overscan) the field is held at the frame's edge value
        FXc = cv2.copyMakeBorder(FXc[fy0:fy0 + hh, fx0:fx0 + ww], fy0, H - fy0 - hh, fx0, W - fx0 - ww, cv2.BORDER_REPLICATE)
        FYc = cv2.copyMakeBorder(FYc[fy0:fy0 + hh, fx0:fx0 + ww], fy0, H - fy0 - hh, fx0, W - fx0 - ww, cv2.BORDER_REPLICATE)
        TX, TY = TX + FXc, TY + FYc
        cur = cv2.remap(a, gx + TX, gy + TY, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        hist.append(dict(it=it, windows=int(dx.size), measured=int(np.isfinite(dx).sum()), dx=[round(float(np.nanmin(dx)), 2), round(float(np.nanmax(dx)), 2)],
                         dy=[round(float(np.nanmin(dy)), 2), round(float(np.nanmax(dy)), 2)]))
        print(hist[-1], flush=True)
    F.save(np.clip(cur, 0, 255), RWH)
    PL = M._pipeline()
    MP.register(PL, RWH_ID)
    lk = MP.lock(PL, RWH_ID, RWH, "")
    sh = MP.shell(RWH, RWH_ID)
    rec = dict(asset_id=RWH_ID, date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0p_products_fix2.py dense2", source=OD_REL + MP.JID + "-fix-warp.png",
               tried=dict(homography="ECC homography on the right wall's lines: it drifted along them (median 34 px, max 108) and left a step at the skirting's end; "
                                     "tiles 4.62 (top, u 0.5-0.75) / 1.56 (bottom-right)",
                          affine="ECC affine on the same: median 7 px; tiles 3.9 / 3.69",
                          phase_field="m0p_warp's phase-correlation field with the shell unprotected: no change (the lines are too thin for 160 px windows)",
                          finding="the 5.5 tile is the back-right corner and the right wall's cornice (render 4.6 / 5.0 px left of the clay) and the cornice's "
                                  "dy (2 px), not the right wall's plane alone; the top-left tiles are the left corner / cornice (3-4 px right)"),
               method="windowed ECC translations (gradient magnitude, render against clay; 240 px every 80 px at 1920; ECC > 0.6), smoothed (median 3 x 3, "
                      "Gaussian 30 px), the triptych and the round protected; two passes",
               iterations=hist, field_canvas_px=dict(dx=[round(float(TX.min()), 2), round(float(TX.max()), 2)], dy=[round(float(TY.min()), 2), round(float(TY.max()), 2)]),
               lock_v2=lk, shell=dict(raw_max_px=sh["raw_max_px"], per_line=sh["per_line"], verdict=sh["verdict"]),
               before=json.load(open(os.path.join(OD, MP.JID + "-fix-warp.json")))["lock_v2"], output=OD_REL + RWH_ID + ".png")
    json.dump(rec, open(os.path.join(OD, RWH_ID + ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(lock=lk, shell=sh["raw_max_px"], per_line=sh["per_line"], field=rec["field_canvas_px"]), indent=0))


def m0_from_m0p(H, W):
    """for every M0p canvas pixel, its M0 canvas pixel (the same ray: the cameras share the point, yaw 0 vs 25)"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    u = ((xx / W) * 4072 - 116) / 3840
    v = ((yy / H) * 2290 - 65) / 2160
    rp = (u - U0) / FX                                            # M0p: right / forward, forward = -Y
    s, c = math.sin(math.radians(25)), math.cos(math.radians(25))
    d0 = -s * rp + c                                             # M0: forward (-s, -c), right (c, -s); the ray (rp, -1) in world XY
    r0 = c * rp + s
    u0 = U0 + FX * r0 / d0
    v0 = V0 + (v - V0) / d0
    mx = (u0 * 3840 + 116) / 4072 * W
    my = (v0 * 2160 + 65) / 2290 * H
    return mx.astype(np.float32), my.astype(np.float32), d0


def products():
    os.makedirs(SPD, exist_ok=True)
    B = load01(RWH)
    H, W = B.shape[:2]
    M0 = load01(M0_FIX2)
    Ly = np.load(LAYER)
    mx, my, d0 = m0_from_m0p(H, W)
    inside = (mx >= 0) & (mx <= W - 1) & (my >= 0) & (my <= H - 1)
    rm = lambda x, bv=0.0: cv2.remap(x.astype(np.float32), mx, my, cv2.INTER_LINEAR if x.ndim == 2 else cv2.INTER_LANCZOS4,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=bv)
    M0p_from_M0 = np.clip(rm(M0), 0, 1)
    I = cv2.imread(INDEX, cv2.IMREAD_UNCHANGED)
    # tone: M0's back wall against M0p's (both ungraded composites)
    bw = cv2.erode((I == 5).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & inside
    lam = rm(Ly["lamp_zone"]) > 0.01
    sel = bw & ~lam & (B.min(2) > 0.3) & (B.max(2) < 0.97)
    gains = np.array([float(np.median(s2l(B[..., c][sel]) / np.maximum(s2l(M0p_from_M0[..., c][sel]), 1e-4))) for c in range(3)], np.float32)
    col = np.clip(l2s(s2l(M0p_from_M0) * gains), 0, 1)
    rec = dict(asset_id=JP, date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0p_products_fix2.py products", base=OD_REL + RWH_ID + ".png",
               products_from=OD_REL + "m0-1-2-products-fix2.png", tone_gains_rgb=[round(float(g), 4) for g in gains],
               mapping="the rotation homography M0 (yaw 25) -> M0p (yaw 0) about the shared camera point; exact at every depth")
    # the lamp's light and the holder's shadow: their multipliers carried the same way (1 outside M0's canvas)
    mult = rm(Ly["mult"], 1.0)
    mult[~inside] = 1.0
    dark = rm(Ly["dark"], 1.0)
    dark[~inside] = 1.0
    out = np.clip(l2s(s2l(B) * mult * dark[..., None]), 0, 1)
    # the old runner: the shell composite's sage pixels on the table where the new runner does not lie -> the table (inpainted)
    a_run = rm(Ly["a_runner"])
    hls = cv2.cvtColor(B, cv2.COLOR_RGB2HLS)
    tbl = cv2.dilate(np.isin(I, [2, 43]).astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool)
    sage = tbl & (hls[..., 0] >= 55) & (hls[..., 0] <= 120) & (hls[..., 2] > 0.06) & (hls[..., 1] < 0.85)
    sage = cv2.morphologyEx(sage.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(sage)
    keep = np.zeros((H, W), np.uint8)
    for i in range(1, n_):
        if st_[i, cv2.CC_STAT_AREA] > 300:
            keep[lab_ == i] = 1
    old = cv2.dilate(keep, np.ones((9, 9), np.uint8)).astype(bool) & (a_run < 0.98)
    if old.any():
        o8 = (np.clip(out, 0, 1) * 255).astype(np.uint8)
        inp = cv2.inpaint(o8, old.astype(np.uint8), 7, cv2.INPAINT_TELEA).astype(np.float32) / 255
        # the oak's grain along the table: the high-pass of the table beside it, shifted along x
        hp = out - cv2.GaussianBlur(out, (0, 0), 3)
        ys, xs = np.nonzero(old)
        grain = np.roll(hp, int(xs.max() - xs.min() + 30), axis=1)
        ao = cv2.GaussianBlur(old.astype(np.float32), (0, 0), 2)[..., None]
        out = out * (1 - ao) + np.clip(inp + grain, 0, 1) * ao
    rec["old_runner_removed_px"] = int(old.sum())
    # the products (the pouf left out: M0 holds only its top)
    alphas = {}
    for k in ("holder", "basket", "lamp", "runner"):
        a = rm(Ly["a_" + k])
        a[~inside] = 0
        alphas[k] = np.clip(a, 0, 1)
        out = out * (1 - alphas[k][..., None]) + col * alphas[k][..., None]
    # is any carried product cut by M0's canvas edge inside M0p's frame?
    fr = np.zeros((H, W), bool)
    fr[int(round(65 / 2290 * H)):int(round(2225 / 2290 * H)), int(round(116 / 4072 * W)):int(round(3956 / 4072 * W))] = True
    edge = cv2.morphologyEx(inside.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(bool) & fr
    rec["cut_by_m0_canvas_px"] = {k: int((cv2.dilate((a > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & edge).sum()) for k, a in alphas.items()}
    pa = rm(Ly["a_pouf"])
    pin = pa > 0.5
    rec["pouf"] = dict(carried=False, why="M0p sees the pouf from v ~0.88 down to the frame's edge; M0's canvas ends at M0p v ~0.93 for its rays, so only its "
                                          "top third exists; carrying it would cut it straight across. It needs its own render (or is left out of P0)",
                       m0_top_part_in_m0p_frame_uv=None)
    if pin.any():
        ys, xs = np.nonzero(pin)
        rec["pouf"]["m0_top_part_in_m0p_frame_uv"] = [round(((xs.min() / W) * 4072 - 116) / 3840, 3), round(((xs.max() / W) * 4072 - 116) / 3840, 3),
                                                      round(((ys.min() / H) * 2290 - 65) / 2160, 3), round(((ys.max() / H) * 2290 - 65) / 2160, 3)]
    o8 = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(o8).save(OUT)
    np.savez_compressed(SPD + "carried.npz", **{k: (a > 0.5) for k, a in alphas.items()}, lamp_zone=lam)
    # nothing else moved: against the homography composite, outside the carried products (+12 px), the old runner, the lamp's light and the holder's shadow
    ch = np.zeros((H, W), bool)
    for a in alphas.values():
        ch |= a > 0.02
    ch |= old | (np.abs(mult - 1).max(2) > 0.003) | (np.abs(dark - 1) > 0.003)
    ch = cv2.dilate(ch.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    d = np.abs(out - B) * 255
    rec["nothing_else_moved"] = dict(rule="mean |delta| per channel <= 2 outside what was carried (+12 px), on the 16:9 frame",
                                     outside_mean_per_channel=[round(float(d[..., c][fr & ~ch].mean()), 3) for c in range(3)],
                                     outside_max=round(float(d.max(2)[fr & ~ch].max()), 2))
    rec["nothing_else_moved"]["pass"] = bool(max(rec["nothing_else_moved"]["outside_mean_per_channel"]) <= 2)
    def fuv(m):
        if not m.any():
            return None
        ys, xs = np.nonzero(m)
        return [round(((xs.min() / W) * 4072 - 116) / 3840, 3), round(((xs.max() / W) * 4072 - 116) / 3840, 3),
                round(((ys.min() / H) * 2290 - 65) / 2160, 3), round(((ys.max() / H) * 2290 - 65) / 2160, 3)]
    rec["products_frame_uv"] = {k: fuv(a > 0.5) for k, a in alphas.items()}
    # lock_v2 on the result
    import fix_m0_12 as M
    PL = M._pipeline()
    MP.register(PL, JP)
    rec["lock_v2"] = MP.lock(PL, JP, OUT, "")
    mf = json.load(open(os.path.join(OD, MP.JID + "-fix.json")))
    rec.update(placement=mf["placement"], prints=mf.get("prints"), output=OD_REL + JP + ".png")
    json.dump(rec, open(os.path.join(OD, JP + ".json"), "w"), indent=1, ensure_ascii=False)
    json.dump(dict(asset_id=JP + "-fix", note="alias record for grade_v6_m0p (it reads <JID>-fix.json): the composite is " + OD_REL + JP + ".png",
                   placement=mf["placement"], prints=mf.get("prints")), open(os.path.join(OD, JP + "-fix.json"), "w"), indent=1, ensure_ascii=False)
    fb = json.load(open(os.path.join(OD, MP.JID + "-fix-base.json")))
    json.dump(dict(asset_id=JP + "-fix-base", wall_round=fb["wall_round"]), open(os.path.join(OD, JP + "-fix-base.json"), "w"), indent=1)
    print(json.dumps({k: rec[k] for k in ("tone_gains_rgb", "old_runner_removed_px", "cut_by_m0_canvas_px", "pouf", "nothing_else_moved", "products_frame_uv", "lock_v2")}, indent=0))


def grade():
    import grade_v6_m0 as G
    import grade_v6_m0p as GP
    GP.JID = JP
    G.JID = JP
    G.SRC = OUT
    G.V5 = os.path.join(OD, MP.JID + "-graded-fix-v5.png")
    G.SP = SPD + "v6/"
    GP.SHEET = os.path.join(REPO, "assets/renders/house-nordic-m0p-products-fix2-v6-sheet-2026-11-06.jpg")
    os.makedirs(G.SP, exist_ok=True)
    a = G.load(G.SRC)
    Mk, mrec = G.masks(a)
    d = dict(np.load(G.SP + "masks.npz"))
    cm = dict(np.load(SPD + "carried.npz"))
    shell, I, ol = d["shell"].copy(), d["I"].copy(), d["obj_label"].copy()
    gray = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    La = G.Lmap(a)
    ids = {"holder": 601, "basket": 602, "lamp": 604, "runner": 43}
    cm["lamp shade"] = cm["lamp"] & (La > 65)
    ids["lamp shade"] = 605
    for k, i in ids.items():
        m = cm[k]
        I[m] = i
        ol[m] = i
        soft = np.clip(PP.guided1(gray, m.astype(np.float32), 2, 1e-4), 0, 1)
        shell = np.minimum(shell, 1 - soft)
    np.savez_compressed(G.SP + "masks.npz", shell=shell.astype(np.float32), art=d["art"], rnd=d["rnd"], cubes=d["cubes"], shell_kind=d["shell_kind"], obj_label=ol, I=I)
    shd = float(np.median(La[cm["lamp shade"]])) if cm["lamp shade"].any() else 90.0
    G.P0["obj_stops"] = {"605": float(np.clip(np.log2(float(s2l(np.float32(0.99))) / float(s2l(np.float32(shd / 100)))) + 0.2, 0.3, 1.5))}
    rec = json.load(open(G.SP + "masks.json"))
    rec["carried_products"] = dict(px={k: int(cm[k].sum()) for k in ids}, obj_stops=G.P0["obj_stops"])
    json.dump(rec, open(G.SP + "masks.json", "w"), indent=1)
    GP.run()
    # the products' QA values on the graded M0p
    g = G.load(os.path.join(OD, JP + "-graded-fix-v6.png"))
    L = G.Lmap(g)
    hls = cv2.cvtColor(g.astype(np.float32), cv2.COLOR_RGB2HLS)
    qa = {}
    felt = cm["holder"] & (L < 45) & (hls[..., 2] < 0.3)
    felt = cv2.erode(felt.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if felt.any():
        qa["holder felt L [25-35]"] = round(float(np.median(L[felt])), 1)
    h_, s_, l_ = G.hsl(g[cm["basket"]].mean(0)) if cm["basket"].any() else (None, None, None)
    qa["jute basket H [25-40] S [25-55]"] = dict(H=h_, S=s_, L=l_)
    if cm["lamp shade"].any():
        ys, xs = np.nonzero(cm["lamp shade"])
        H, W = L.shape
        wall = np.zeros((H, W), bool)
        wall[ys.min():ys.min() + int(0.6 * (ys.max() - ys.min())), max(0, xs.min() - 140):xs.min() - 40] = True
        wall &= (I == 5) & ~cm["lamp"]
        qa["lamp shade over the wall left of it [>= 6]"] = dict(shade=round(float(np.median(L[cm["lamp shade"]])), 1), wall=round(float(np.median(L[wall])), 1) if wall.any() else None)
    qa["whole frame: px at 255, black p0.1"] = [int((g.max(2) >= 254.5 / 255).sum()), round(float(np.percentile(L, 0.1)), 1)]
    n = json.load(open(os.path.join(OD, JP + "-measurements-fix-v6.json")))
    n["products_qa"] = qa
    n["input"] = OD_REL + JP + ".png"
    json.dump(n, open(os.path.join(OD, JP + "-measurements-fix-v6.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(qa, indent=1), n.get("not_met"))


def sheet():
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    a = Image.open(os.path.join(OD, JP + "-frame-fix-v6.png")).convert("RGB").resize((1280, 720), Image.LANCZOS)
    b = Image.open(os.path.join(OD, "m0-1-2-products-fix2-frame-fix-v6.png")).convert("RGB").resize((1280, 720), Image.LANCZOS)
    rec = json.load(open(os.path.join(OD, JP + ".json")))
    out = Image.new("RGB", (2 * 1280 + 30, 60 + 720 + 90), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.text((10, 16), f"P0 pair ({DATE}): M0p (yaw 0) | M0 (yaw 25), both with the four fixed products' layer, graded v6. Not QA'd.", fill=(0, 0, 0), font=fb)
    out.paste(a, (10, 60))
    out.paste(b, (1300, 60))
    lk = rec["lock_v2"]
    d.text((14, 790), f"M0p: lock_v2 band {lk['band_after']} / tile {lk['tile_after']} / edges {lk['fixed_edges_worst_px']} -> {'pass' if lk['verdict']['pass'] else 'FAIL'}; "
                      f"nothing else moved {rec['nothing_else_moved']['outside_mean_per_channel']}; the pouf not carried (M0 holds only its top).", fill=(0, 0, 0), font=f)
    d.text((1304, 790), "M0: m0-1-2-products-fix2 (holder, pouf, lamp light fixed).", fill=(0, 0, 0), font=f)
    out.save(SHEET, quality=88)
    print(SHEET)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "rwh":
        rwh()
    if w == "dense":
        dense()
    if w == "dense2":
        dense2()
    if w == "products":
        products()
    if w == "grade":
        grade()
    if w == "sheet":
        sheet()
