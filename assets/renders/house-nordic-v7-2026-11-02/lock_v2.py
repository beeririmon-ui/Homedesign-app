#!/usr/bin/env python3
"""
lock_v2: the scale-aware clay lock of gate G1.4 (docs/ops/quality-gates-2026-11-02.md), adopted from QA's measure on
the v7 set (qa/reports/2026-11-02-v7-g1.md section 5, tools/lock.py) in place of process_v7.py's `clay_lock`, which
measured a phase-correlation shift only and reported M0 r2 as locked (0.024) while the sofa was 1.20-1.23x the clay.
render-agent, 2026-11-03. 0 var2 tokens.

Three measures on the 16:9 frame at 1920x1080 (the overscan canvas is cropped to its frame first):
  1. register   site/tools/transitions/pan_reproject.register(render, clay): one global affine by ECC on Sobel edge
                maps at 960 wide -> the shift (px) and the scale (x, y) of the whole frame. ECC's convention: the
                matrix maps clay (template) coordinates to render coordinates, so scale > 1 means the render drew the
                scene larger than the clay.
  2. residual   after that affine is undone: pan_reproject.overlap_check (phase correlation of Laplacian edges, whole
                frame and 4 vertical bands; a band counts only when its response >= 0.05, because against a clay the
                correlation slides on texture below that) and ECC translation per tile (4 x 2) on the same edge maps
                (a tile counts when its correlation rho >= 0.12). What remains after register is local redrawing.
  3. edges      for every fixed-furniture / architecture / window / door / mirror box of the clay selfcheck: the
                strongest vertical edge within +-0.035 of each clay box edge (rows 35-85 % of the box) in the clay and
                in the render, and the same for the top / bottom edges (columns 35-85 %); only edges strong in both
                (>= 4 grey levels mean gradient) count. Reported as px offsets at 1920 and width / height ratios.

Thresholds (G1.4, with QA's reading of the gate): register shift <= 0.5 % of the width (9.6 px) and scale within
0.5 %; residual per band and per tile after register <= 2 px for a still that is a pan endpoint, <= 9.6 px for a video
endpoint; every measured fixed edge within +-0.01 of the width (19 px) and width / height ratios 0.95-1.05 (G1.3,
proposal). `pass` needs all three.

  python3 lock_v2.py <render.png> <clay.png> <frame> <out.json> [--overscan] [--pan] [--overlay out.png]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402

sys.path.insert(0, os.path.join(VF.REPO, "site", "tools", "transitions"))
import pan_reproject as pr  # noqa: E402

W, H = 1920, 1080
SHIFT_MAX_PX = 0.005 * W          # 9.6
SCALE_TOL = 0.005
RESID_PAN_PX = 2.0
RESID_ENDPOINT_PX = SHIFT_MAX_PX
EDGE_MAX_PX = 0.01 * W            # 19.2
RATIO_LO, RATIO_HI = 0.95, 1.05
BAND_MIN_RESPONSE = 0.05
TILE_MIN_RHO = 0.12
EDGE_MIN_STRENGTH = 4.0


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


def crop_frame(img):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = VF.frame_box_px(w, h)
    return img[y0:y1, x0:x1]


def gray8(img):
    return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def _strongest(prof, c, tol, n):
    x0, x1 = max(0, int((c - tol) * n)), min(len(prof), int((c + tol) * n))
    if x1 - x0 < 3:
        return None, 0.0
    i = x0 + int(np.argmax(prof[x0:x1]))
    return i, float(prof[i])


def edge_pairs(gc, gr, box):
    u0, u1, v0, v1 = box
    gxc, gxr = np.abs(np.diff(gc, axis=1)), np.abs(np.diff(gr, axis=1))
    gyc, gyr = np.abs(np.diff(gc, axis=0)), np.abs(np.diff(gr, axis=0))
    ry0, ry1 = int((v0 + 0.35 * (v1 - v0)) * H), int((v0 + 0.85 * (v1 - v0)) * H)
    cx0, cx1 = int((u0 + 0.35 * (u1 - u0)) * W), int((u0 + 0.85 * (u1 - u0)) * W)
    out = {}
    if ry1 - ry0 >= 4:
        pc, prr = gxc[ry0:ry1].mean(0), gxr[ry0:ry1].mean(0)
        for side, c in (("left", u0), ("right", u1)):
            if c <= 0.01 or c >= 0.99:
                continue
            ic, sc = _strongest(pc, c, 0.035, W)
            ir, sr = _strongest(prr, c, 0.035, W)
            if ic is None or ir is None or sc < EDGE_MIN_STRENGTH or sr < EDGE_MIN_STRENGTH:
                continue
            out[side] = dict(clay_px=ic, render_px=ir, d_px=ir - ic, clay_strength=round(sc, 1), render_strength=round(sr, 1))
    if cx1 - cx0 >= 4:
        pc, prr = gyc[:, cx0:cx1].mean(1), gyr[:, cx0:cx1].mean(1)
        for side, c in (("top", v0), ("bottom", v1)):
            if c <= 0.01 or c >= 0.99:
                continue
            ic, sc = _strongest(pc, c, 0.035, H)
            ir, sr = _strongest(prr, c, 0.035, H)
            if ic is None or ir is None or sc < EDGE_MIN_STRENGTH or sr < EDGE_MIN_STRENGTH:
                continue
            out[side] = dict(clay_px=ic, render_px=ir, d_px=ir - ic, clay_strength=round(sc, 1), render_strength=round(sr, 1))
    res = dict(box=[round(x, 4) for x in box], edges=out)
    if "left" in out and "right" in out:
        wc = out["right"]["clay_px"] - out["left"]["clay_px"]
        wr = out["right"]["render_px"] - out["left"]["render_px"]
        res["width_ratio"] = round(wr / wc, 4) if wc > 0 else None
    if "top" in out and "bottom" in out:
        hc = out["bottom"]["clay_px"] - out["top"]["clay_px"]
        hr = out["bottom"]["render_px"] - out["top"]["render_px"]
        res["height_ratio"] = round(hr / hc, 4) if hc > 0 else None
    res["worst_edge_px"] = max([abs(e["d_px"]) for e in out.values()]) if out else None
    return res


def tiles_ecc(rend, clay, nx=4, ny=2):
    e_ref, e_img = pr._edges(clay, 960), pr._edges(rend, 960)
    h, w = e_ref.shape
    s = W / w
    out = []
    for j in range(ny):
        for i in range(nx):
            x0, x1, y0, y1 = int(i * w / nx), int((i + 1) * w / nx), int(j * h / ny), int((j + 1) * h / ny)
            a, b = e_ref[y0:y1, x0:x1], e_img[y0:y1, x0:x1]
            M = np.eye(2, 3, dtype=np.float32)
            crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5)
            rec = dict(u=[round(x0 / w, 2), round(x1 / w, 2)], v=[round(y0 / h, 2), round(y1 / h, 2)])
            try:
                rho, M = cv2.findTransformECC(a, b, M, cv2.MOTION_TRANSLATION, crit, None, 5)
                rec.update(dx_px=round(float(M[0, 2]) * s, 2), dy_px=round(float(M[1, 2]) * s, 2), rho=round(float(rho), 3),
                           counted=bool(rho >= TILE_MIN_RHO))
            except cv2.error:
                rec.update(dx_px=None, dy_px=None, rho=None, counted=False, note="ECC did not converge")
            out.append(rec)
    return out


def _worst(vals):
    return round(max(vals), 2) if vals else None


def lock_v2(render, clay, frame, boxes, pan, frame_id=None, overlay_path=None):
    """render, clay: float RGB arrays of the 16:9 frame (any size). boxes: {name: (kind, (u0,u1,v0,v1))}."""
    cam = pr.Cam(0.0, 0.5, 0.46)
    rend = pr.fit(render, W, H)
    cl = pr.fit(clay, W, H)
    rep = dict(frame=frame, id=frame_id, size=[W, H], pan_endpoint=bool(pan), method="lock_v2 (register + bands + ECC tiles + fixed edges)")
    rep["check_raw"] = pr.overlap_check(cl, cam, rend, cam, W, H)
    reg, M = pr.register(rend, cl)
    rep["register"] = dict(affine=np.round(M, 5).tolist(), shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)],
                           scale=[round(float(M[0, 0]), 5), round(float(M[1, 1]), 5)],
                           note="ECC affine, clay (template) -> render coordinates at 1920x1080; scale > 1 = the render drew it larger")
    rep["check_registered"] = pr.overlap_check(cl, cam, reg, cam, W, H)
    rep["tiles_ecc"] = tiles_ecc(rend, cl)
    rep["tiles_ecc_registered"] = tiles_ecc(reg, cl)
    gc, gr = gray8(cl), gray8(rend)
    edges = {}
    for nm, (kind, box) in boxes.items():
        e = edge_pairs(gc, gr, box)
        e["kind"] = kind
        edges[nm] = e
    rep["fixed_edges"] = edges
    bands_raw = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_raw"]["bands"] if b["response"] >= BAND_MIN_RESPONSE]
    bands_reg = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_registered"]["bands"] if b["response"] >= BAND_MIN_RESPONSE]
    t_raw = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc"] if x["counted"]]
    t_reg = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc_registered"] if x["counted"]]
    edge_px = [e["worst_edge_px"] for e in edges.values() if e.get("worst_edge_px") is not None]
    ratios = {}
    for nm, e in edges.items():
        if e.get("width_ratio"):
            ratios[nm + " w"] = e["width_ratio"]
        if e.get("height_ratio"):
            ratios[nm + " h"] = e["height_ratio"]
    shift = rep["register"]["shift_px"]
    scale = rep["register"]["scale"]
    resid_max = RESID_PAN_PX if pan else RESID_ENDPOINT_PX
    resid_vals = [v for v in (_worst(bands_reg), _worst(t_reg)) if v is not None]
    g_pass = max(abs(shift[0]), abs(shift[1])) <= SHIFT_MAX_PX and max(abs(scale[0] - 1), abs(scale[1] - 1)) <= SCALE_TOL
    r_pass = bool(resid_vals) and max(resid_vals) <= resid_max
    e_pass = (not edge_px or max(edge_px) <= EDGE_MAX_PX) and all(RATIO_LO <= r <= RATIO_HI for r in ratios.values())
    rep["summary"] = dict(
        register_shift_px=shift, register_scale=scale, register_scale_pct=[round((scale[0] - 1) * 100, 2), round((scale[1] - 1) * 100, 2)],
        worst_band_px=_worst(bands_raw), bands_reliable=len(bands_raw),
        worst_band_px_after_register=_worst(bands_reg), bands_reliable_after_register=len(bands_reg),
        worst_tile_ecc_px=_worst(t_raw), tiles_counted=len(t_raw),
        worst_tile_ecc_px_after_register=_worst(t_reg), tiles_counted_after_register=len(t_reg),
        fixed_edges_worst_px=max(edge_px) if edge_px else None, fixed_edges_measured=len(edge_px), fixed_ratios=ratios)
    rep["verdict"] = dict(
        thresholds=dict(shift_px=SHIFT_MAX_PX, scale_tol=SCALE_TOL, residual_px=resid_max,
                        residual_rule=("pan endpoint: <= 2 px per band / tile after register" if pan else "video endpoint: <= 0.5 % of the width after register"),
                        edge_px=EDGE_MAX_PX, ratio=[RATIO_LO, RATIO_HI], source="docs/ops/quality-gates-2026-11-02.md G1.4 (+ G1.3 ratios, proposal); qa/reports/2026-11-02-v7-g1.md section 1"),
        global_pass=bool(g_pass), residual_pass=bool(r_pass), edges_pass=bool(e_pass),
        residual_measured=bool(resid_vals), **{"pass": bool(g_pass and r_pass and e_pass)})
    if overlay_path:
        g = gray8(cl)
        e = cv2.Canny(g.astype(np.uint8), 60, 140)
        e = cv2.dilate(e, np.ones((2, 2), np.uint8))
        im = (rend * 255).astype(np.uint8).copy()
        im[e > 0] = (255, 40, 40)
        Image.fromarray(im).save(overlay_path, quality=82)
    return rep


def run_frame(fid, render_path=None, out_path=None, overlay_path=None):
    """The lock of one registry still (default: its normalised raw `<id>.png`) against its round-4 clay."""
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    od = VF.out_dir(fid)
    render_path = render_path or os.path.join(od, fid + ".png")
    r = load_rgb(render_path)
    c = load_rgb(os.path.join(VF.R4, clay_file))
    if overscan:
        r, c = crop_frame(r), crop_frame(c)
    rep = lock_v2(r, c, frame, VF.fixed_boxes(frame, overscan, fid), pan, frame_id=fid, overlay_path=overlay_path)
    rep.update(render=os.path.relpath(render_path, VF.REPO), clay=os.path.relpath(os.path.join(VF.R4, clay_file), VF.REPO),
               overscan_cropped_to_frame=bool(overscan), date="2026-11-03",
               note="geometry only: measured on the normalised raw still (the grade does not move edges); the old clay_lock stays in <id>-measurements.json")
    out_path = out_path or os.path.join(od, fid + "-lock-v2.json")
    json.dump(rep, open(out_path, "w"), indent=1)
    s, v = rep["summary"], rep["verdict"]
    print(f"{fid:18s} shift {s['register_shift_px']} scale% {s['register_scale_pct']} | resid band {s['worst_band_px_after_register']} tile {s['worst_tile_ecc_px_after_register']} "
          f"(limit {v['thresholds']['residual_px']}) | edges worst {s['fixed_edges_worst_px']} ratios {s['fixed_ratios']} | "
          f"{'PASS' if v['pass'] else 'FAIL'} (g {int(v['global_pass'])} r {int(v['residual_pass'])} e {int(v['edges_pass'])})")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("clay")
    ap.add_argument("frame")
    ap.add_argument("out")
    ap.add_argument("--overscan", action="store_true")
    ap.add_argument("--pan", action="store_true")
    ap.add_argument("--overlay")
    a = ap.parse_args()
    r, c = load_rgb(a.render), load_rgb(a.clay)
    if a.overscan:
        r, c = crop_frame(r), crop_frame(c)
    rep = lock_v2(r, c, a.frame, VF.fixed_boxes(a.frame, a.overscan), a.pan, overlay_path=a.overlay)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep["summary"]), json.dumps(rep["verdict"]))
