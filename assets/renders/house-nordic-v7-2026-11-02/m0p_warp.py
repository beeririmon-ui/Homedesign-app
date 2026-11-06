#!/usr/bin/env python3
"""
m0p_warp.py: a local warp of M0p 1.2's furniture onto the clay (the P0 pan endpoint: lock_v2 residual <= 2 px; the composite read band 6.8 /
tile 4.7 with the shell and the global register already on the clay). render-agent, 2026-11-06, 0 tokens. New files:
v9/pose-m0p-1-2-shell-seedream-fix-warp.png (+ .json, -lock-v2.json / .jpg).
How: on the 16:9 frame at 1920, local phase correlation of the gradient magnitude (render against the clay) in 160 px windows on a 48 px grid,
kept where the response is strong and the clay has edges; a robust smooth field (median 3x3 of the grid, then Gaussian), zero on the shell's
named lines, the triptych and the round (code-placed on the geometry already), faded to zero over 60 px; the render remapped by it (Lanczos).
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_m0_12 as M  # noqa: E402
import fix_v7 as F  # noqa: E402
import m0p_seedream as MP  # noqa: E402

REPO, OD, OD_REL = MP.REPO, MP.OD, MP.OD_REL
JID = MP.JID
SRC = os.path.join(OD, JID + "-fix.png")
OUT = os.path.join(OD, JID + "-fix-warp.png")
WIN, STEP = 160, 48


def grad16(img01):
    import lock_v2 as LK
    f = LK.pr.fit(LK.crop_frame(img01), 1920, 1080)
    g = cv2.cvtColor((np.clip(f, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    return np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))


def field(r16, c16, protect16):
    H, W = r16.shape
    hann = cv2.createHanningWindow((WIN, WIN), cv2.CV_32F)
    ys = list(range(WIN // 2, H - WIN // 2, STEP))
    xs = list(range(WIN // 2, W - WIN // 2, STEP))
    dx = np.full((len(ys), len(xs)), np.nan, np.float32)
    dy = np.full_like(dx, np.nan)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            a = r16[y - WIN // 2:y + WIN // 2, x - WIN // 2:x + WIN // 2]
            b = c16[y - WIN // 2:y + WIN // 2, x - WIN // 2:x + WIN // 2]
            if b.mean() < 6 or protect16[y, x]:
                continue
            (sx, sy), resp = cv2.phaseCorrelate(b.astype(np.float32), a.astype(np.float32), hann)
            if resp > 0.12 and abs(sx) < 14 and abs(sy) < 14:
                dx[i, j], dy[i, j] = sx, sy
    return ys, xs, dx, dy


def smooth(grid, n_iter=3):
    g = grid.copy()
    for _ in range(n_iter):
        pad = np.pad(g, 1, mode="edge")
        st = np.stack([pad[i:i + g.shape[0], j:j + g.shape[1]] for i in range(3) for j in range(3)], 0)
        med = np.nanmedian(st, 0)
        g = np.where(np.isnan(g), med, np.where(np.abs(g - med) > 2.5, med, g))
    return np.nan_to_num(g, nan=0.0)


def run():
    import lock_v2 as LK
    PL = M._pipeline()
    MP.register(PL, JID)
    a = F.load(SRC)
    H, W = a.shape[:2]
    clay = LK.load_rgb(MP.CLAY)
    r16, c16 = grad16(np.clip(a / 255.0, 0, 1).astype(np.float32)), grad16(clay)
    # protected: the triptych and the round (code-placed on the geometry), the shell lines (a band round the clay's shell edges of the walls)
    n = json.load(open(os.path.join(OD, JID + "-fix.json")))
    prot = np.zeros((H, W), np.uint8)
    for q in n["placement"]["targets_px"]:
        cv2.fillConvexPoly(prot, np.round(np.array(q)).astype(np.int32), 1)
    rr = json.load(open(os.path.join(OD, JID + "-fix-base.json")))["wall_round"]["rendered"]
    cv2.ellipse(prot, ((rr["centre_px"][0], rr["centre_px"][1]), (rr["axes_px"][0] + 20, rr["axes_px"][1] + 20), 0), 1, -1)
    I = cv2.imread(os.path.join(OD, "m0p-clay-r5b-index.png"), cv2.IMREAD_UNCHANGED)
    shellk = np.isin(I, [5, 6, 7, 8, 9, 11, 13]).astype(np.uint8)
    edge = cv2.morphologyEx(shellk, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    objs = (~np.isin(I, [5, 6, 7, 8, 9, 11, 13])).astype(np.uint8)
    shell_lines = edge & (cv2.dilate(objs, np.ones((25, 25), np.uint8)) == 0)          # shell-shell edges (corners, floor line, cornice), not object outlines
    prot = np.maximum(prot, cv2.dilate(shell_lines, np.ones((9, 9), np.uint8)))
    p16 = cv2.resize(LK.crop_frame(prot.astype(np.float32)) if False else prot[int(round(65 / 2290 * H)):int(round(2225 / 2290 * H)), int(round(116 / 4072 * W)):int(round(3956 / 4072 * W))].astype(np.float32),
                     (1920, 1080), interpolation=cv2.INTER_NEAREST) > 0.5
    ys, xs, dx, dy = field(r16, c16, p16)
    measured = int(np.isfinite(dx).sum())
    dxs, dys = smooth(dx), smooth(dy)
    # dense field at 1920 x 1080, zero (faded over 60 px) on the protected parts
    fx = cv2.resize(dxs, (len(xs) * STEP, len(ys) * STEP), interpolation=cv2.INTER_CUBIC)
    fy = cv2.resize(dys, (len(xs) * STEP, len(ys) * STEP), interpolation=cv2.INTER_CUBIC)
    FX = np.zeros((1080, 1920), np.float32)
    FY = np.zeros_like(FX)
    y0, x0 = ys[0] - STEP // 2, xs[0] - STEP // 2
    FX[y0:y0 + fx.shape[0], x0:x0 + fx.shape[1]] = fx[:1080 - y0, :1920 - x0]
    FY[y0:y0 + fy.shape[0], x0:x0 + fy.shape[1]] = fy[:1080 - y0, :1920 - x0]
    FX = cv2.GaussianBlur(FX, (0, 0), 24)
    FY = cv2.GaussianBlur(FY, (0, 0), 24)
    keep = 1 - cv2.GaussianBlur(cv2.dilate(p16.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 20)
    FX, FY = FX * np.clip(keep, 0, 1), FY * np.clip(keep, 0, 1)
    # to the canvas: frame px at 1920 -> canvas px (scale s), the render's feature at (clay + d): sample the render at x + d
    fx0, fy0 = int(round(116 / 4072 * W)), int(round(65 / 2290 * H))
    s = (3840 / 4072 * W) / 1920.0
    FXc = np.zeros((H, W), np.float32)
    FYc = np.zeros((H, W), np.float32)
    big_x = cv2.resize(FX, (int(round(1920 * s)), int(round(1080 * s))), interpolation=cv2.INTER_LINEAR) * s
    big_y = cv2.resize(FY, (int(round(1920 * s)), int(round(1080 * s))), interpolation=cv2.INTER_LINEAR) * s
    hh, ww = min(big_x.shape[0], H - fy0), min(big_x.shape[1], W - fx0)
    FXc[fy0:fy0 + hh, fx0:fx0 + ww] = big_x[:hh, :ww]
    FYc[fy0:fy0 + hh, fx0:fx0 + ww] = big_y[:hh, :ww]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    out = cv2.remap(a.astype(np.float32), gx + FXc, gy + FYc, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    F.save(np.clip(out, 0, 255), OUT)
    wid = JID + "-warp"
    PL.VF.RETAKES[wid] = PL.JOBS["pose-m0p-v8b"]
    J = MP.T.jr()
    if not any(j["id"] == wid for j in J["jobs"]):
        J["jobs"].append(dict(id=wid, out_dir=OD_REL, model="code", tokens=0, status="stub"))
        MP.T.save_jr(J)
    lk = PL.LK.run_frame(wid, render_path=OUT, out_path=os.path.join(OD, JID + "-fix-warp-lock-v2.json"),
                         overlay_path=os.path.join(OD, JID + "-fix-warp-lock-v2.jpg"), date=MP.DATE)
    sm, v = lk["summary"], lk["verdict"]
    rep = MP.shell(OUT, JID + "-fix-warp")
    rec = dict(asset_id=JID + "-fix-warp", date=MP.DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/m0p_warp.py", source=OD_REL + JID + "-fix.png",
               grid=dict(window_px_1920=WIN, step_px_1920=STEP, measured_cells=measured, cells=int(dx.size)),
               field_px_1920=dict(dx_min=round(float(FX.min()), 2), dx_max=round(float(FX.max()), 2), dy_min=round(float(FY.min()), 2), dy_max=round(float(FY.max()), 2)),
               lock_v2=dict(shift_px=sm["register_shift_px"], scale_pct=sm["register_scale_pct"], band_after=sm["worst_band_px_after_register"],
                            tile_after=sm["worst_tile_ecc_px_after_register"], fixed_edges_worst_px=sm["fixed_edges_worst_px"], fixed_ratios=sm["fixed_ratios"],
                            verdict={k: v[k] for k in ("global_pass", "residual_pass", "edges_pass", "pass")}),
               shell=dict(raw_max_px=rep["raw_max_px"], per_line=rep["per_line"], verdict=rep["verdict"]),
               before=json.load(open(os.path.join(OD, JID + "-fix.json")))["checks"]["lock_v2"], output=OD_REL + JID + "-fix-warp.png")
    json.dump(rec, open(OUT.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(field=rec["field_px_1920"], cells=rec["grid"], lock=rec["lock_v2"], shell=rec["shell"]["raw_max_px"]), indent=0))


if __name__ == "__main__":
    run()
