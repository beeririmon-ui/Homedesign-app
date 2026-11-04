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

  python3 lock_v2.py <render.png> <clay.png> <frame> <out.json> [--overscan] [--pan] [--overlay out.png] [--edges v3|v2] [--id <job id>]

v3 (render-agent, 2026-11-04; briefs/render-retakes-code-fixes-2026-11-04.md task 3, QA qa/reports/2026-11-03-retakes-g1.md §3), the default;
`--edges v2` (or edges_mode="v2") restores the 2026-11-03 behaviour exactly:
  - NAMED EDGES: QA's named lines per frame (tools/edges_direct.py, the same spans), each measured by normalised cross-correlation of
    the 1-D gradient profiles (+-90 px) and counted only when r >= 0.5; so lines that are no selfcheck box edge (W0-in's desk top and
    drawer, B2's vanity and mirror head) are measured;
  - BOX EDGES by cross-correlation (+-60 px, r >= 0.5) instead of the strongest single peak, so a peak on a leg or one of two parallel
    edges (B1's glazing frame vs glass, K-girl-0's desk legs) no longer becomes a furniture ratio;
  - BANDS / TILES counted only where the clay and the render share structure (band response >= 0.1, tile rho >= 0.3; v2: 0.05 / 0.12);
  - the verdict adds the named edges (worst |d| <= 0.01 of the width, 19 px) to the edge criterion.
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


BAND_MIN_RESPONSE_V3 = 0.10
TILE_MIN_RHO_V3 = 0.30
XCORR_MIN_R = 0.5
VIDEO_ENDPOINTS = {"W0-in", "MB-in"}
# QA's named lines (qa/reports/2026-11-03-retakes-g1/tools/edges_direct.py), keyed by the job id (a -fix still uses its retake's id):
# (name, 'h' = a horizontal line (offset in rows) | 'v', span (u0,u1) for h / (v0,v1) for v, search (lo,hi) on the other axis), 16:9 frame fractions
NAMED_EDGES = {
    "pose-w0-in-v7-r2": [("shelf top", "h", (0.30, 0.70), (0.05, 0.20)), ("shelf bottom (front face)", "h", (0.30, 0.70), (0.12, 0.26)),
                         ("desk top front edge", "h", (0.68, 0.80), (0.55, 0.85)),
                         ("desk top front edge (left of chair)", "h", (0.20, 0.33), (0.55, 0.85)), ("drawer bottom / apron", "h", (0.20, 0.33), (0.70, 0.95)),
                         ("chair back top", "h", (0.40, 0.60), (0.62, 0.90)), ("desk left outer edge", "v", (0.80, 0.95), (0.08, 0.26)),
                         ("desk right outer edge", "v", (0.80, 0.95), (0.75, 0.92)), ("chair back left edge", "v", (0.82, 0.98), (0.28, 0.44)),
                         ("chair back right edge", "v", (0.82, 0.98), (0.56, 0.72))],
    "pose-k-girl-0-v7-r2": [("desk top", "h", (0.25, 0.45), (0.50, 0.66)), ("band top (desk wall)", "h", (0.05, 0.20), (0.28, 0.44)),
                            ("bed foot top", "h", (0.02, 0.14), (0.55, 0.72)), ("skirting top (desk wall)", "h", (0.08, 0.20), (0.70, 0.90)),
                            ("room corner", "v", (0.08, 0.30), (0.52, 0.68)), ("desk left leg", "v", (0.72, 0.90), (0.15, 0.28)),
                            ("desk right leg", "v", (0.72, 0.90), (0.40, 0.52)), ("bed foot right edge", "v", (0.68, 0.90), (0.10, 0.24))],
    "b1-v7-r3": [("glazing top", "h", (0.24, 0.32), (0.08, 0.22)), ("glazing bottom / sill", "h", (0.24, 0.32), (0.42, 0.56)),
                 ("ledge top (WC block)", "h", (0.17, 0.30), (0.48, 0.62)), ("WC block bottom", "h", (0.17, 0.30), (0.90, 1.0)),
                 ("glazing left", "v", (0.20, 0.42), (0.14, 0.26)), ("glazing right", "v", (0.20, 0.42), (0.30, 0.42)),
                 ("WC block left", "v", (0.62, 0.90), (0.08, 0.20)), ("WC block right", "v", (0.62, 0.90), (0.36, 0.46)),
                 ("curtain track end / corner", "v", (0.05, 0.40), (0.68, 0.78)), ("vanity left edge", "v", (0.66, 0.95), (0.86, 0.96))],
    "b2-v7-r3": [("vanity top", "h", (0.52, 0.70), (0.44, 0.60)), ("mirror top", "h", (0.60, 0.76), (0.02, 0.14)), ("mirror bottom", "h", (0.60, 0.76), (0.40, 0.52)),
                 ("niche top", "h", (0.53, 0.63), (0.34, 0.46)), ("vanity left edge", "v", (0.58, 0.90), (0.42, 0.54)), ("vanity right edge", "v", (0.60, 0.90), (0.76, 0.88)),
                 ("mirror left", "v", (0.12, 0.40), (0.50, 0.62)), ("mirror right", "v", (0.12, 0.40), (0.74, 0.86)),
                 ("niche left", "v", (0.38, 0.48), (0.48, 0.58)), ("niche right", "v", (0.38, 0.48), (0.60, 0.70)), ("curtain outer edge", "v", (0.20, 0.70), (0.26, 0.36))],
}

# lines whose measured offset is another line, as judged by eye (each with who judged it and why): reported, not counted
EYE_OVERRIDES = {
    "pose-w0-in-v7-r2": {
        "named": {"shelf top": "QA §3 (2026-11-03): '+34' is another line (the shelf's front face against its top); by eye the shelf is within +-10",
                  "shelf bottom (front face)": "QA §3: the same clay peak as 'shelf top' (row 151); by eye the shelf is within +-10",
                  "desk right outer edge": "QA §3: '-33' is the inner edge of the thick side panel; the outer edge is in place by eye (render-agent 2026-11-04: outer edge ~1597 vs clay 1599)"},
        "box": {"built-in oak desk + shelf": {"top": "QA §3: the box top is the shelf line, '+34' is its front face against its top; by eye +-10"}}},
    "b2-v7-r3": {
        "named": {"mirror top": ("render-agent 2026-11-04, for QA to confirm: the head is sloped and the named line averages it over u 0.60-0.76, where the "
                                 "clay's strongest row (124) is the reflected ceiling line inside the glass, not the frame; measured per column (the first "
                                 "frame edge from the top, 6 px columns at x 1090 / 1150 / 1350 / 1450 / 1540) the raw head is -2 px from the clay at every "
                                 "column (fix_v8.MIRROR_HEAD_CHECK)")}},
    "pose-k-girl-0-v7-r2": {
        "named": {"skirting top (desk wall)": ("render-agent 2026-11-04, for QA to confirm: over the span u 0.08-0.20 the skirting is behind the bed foot and "
                                               "the muslin in the render, so the '+24' is the blanket's edge; QA's G1 list did not use this line")}},
}


def xcorr_offset(pc, pr_, ci, half=60):
    """Offset (px) of the render profile against the clay profile around index ci, by normalised cross-correlation within +-half
    (QA's tools/lock.py xcorr_offset). Returns (offset, r)."""
    n = len(pc)
    a0, a1 = max(0, ci - half), min(n - 1, ci + half)
    a = pc[a0:a1].astype(np.float64)
    if a1 - a0 < 20 or a.std() < 1e-6:
        return None, 0.0
    a = (a - a.mean()) / a.std()
    best, bo = -1.0, 0
    for o in range(-half, half + 1):
        b0, b1 = a0 + o, a1 + o
        if b0 < 0 or b1 > n - 1:
            continue
        b = pr_[b0:b1].astype(np.float64)
        if b.std() < 1e-6:
            continue
        b = (b - b.mean()) / b.std()
        r = float((a * b).mean())
        if r > best:
            best, bo = r, o
    return bo, round(best, 3)


def named_edges(gc, gr, frame_id):
    """QA's named lines for this job id: clay line = the strongest clay edge in the search window; offset = cross-correlation
    (+-90 px); counted when r >= 0.5. Rows of 1080 for horizontal lines, columns of 1920 for vertical ones."""
    out = {}
    for name, orient, span, search in NAMED_EDGES.get(frame_id, []):
        if orient == "h":
            c0, c1 = int(span[0] * W), int(span[1] * W)
            pc, prr = np.abs(np.diff(gc[:, c0:c1], axis=0)).mean(1), np.abs(np.diff(gr[:, c0:c1], axis=0)).mean(1)
            lo, hi = int(search[0] * H), int(search[1] * H)
        else:
            r0, r1 = int(span[0] * H), int(span[1] * H)
            pc, prr = np.abs(np.diff(gc[r0:r1], axis=1)).mean(0), np.abs(np.diff(gr[r0:r1], axis=1)).mean(0)
            lo, hi = int(search[0] * W), int(search[1] * W)
        ic = lo + int(np.argmax(pc[lo:hi]))
        o, r = xcorr_offset(pc, prr, ic, half=90)
        ov = EYE_OVERRIDES.get(frame_id, {}).get("named", {}).get(name)
        out[name] = dict(orientation=orient, clay_px=ic, d_xcorr_px=o, r=r, counted=bool(o is not None and r >= XCORR_MIN_R and not ov))
        if ov:
            out[name]["eye_override"] = ov
    return out


def edge_pairs_v3(gc, gr, box):
    """edge_pairs with the offsets by cross-correlation (+-60 px) of the same profiles; an edge counts when r >= 0.5 and the clay edge
    is strong; the ratios use the counted offsets, so a single peak on a leg or on one of two parallel edges cannot make a ratio."""
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
            if ic is None or sc < EDGE_MIN_STRENGTH:
                continue
            o, r = xcorr_offset(pc, prr, ic, half=60)
            if o is None or r < XCORR_MIN_R:
                out[side] = dict(clay_px=ic, d_px=None, r=r, counted=False)
                continue
            out[side] = dict(clay_px=ic, render_px=ic + o, d_px=o, r=r, clay_strength=round(sc, 1), counted=True)
    if cx1 - cx0 >= 4:
        pc, prr = gyc[:, cx0:cx1].mean(1), gyr[:, cx0:cx1].mean(1)
        for side, c in (("top", v0), ("bottom", v1)):
            if c <= 0.01 or c >= 0.99:
                continue
            ic, sc = _strongest(pc, c, 0.035, H)
            if ic is None or sc < EDGE_MIN_STRENGTH:
                continue
            o, r = xcorr_offset(pc, prr, ic, half=60)
            if o is None or r < XCORR_MIN_R:
                out[side] = dict(clay_px=ic, d_px=None, r=r, counted=False)
                continue
            out[side] = dict(clay_px=ic, render_px=ic + o, d_px=o, r=r, clay_strength=round(sc, 1), counted=True)
    res = dict(box=[round(x, 4) for x in box], edges=out, method="xcorr +-60 px, r >= 0.5")
    ok = {k: e for k, e in out.items() if e.get("counted")}
    if "left" in ok and "right" in ok:
        wc = ok["right"]["clay_px"] - ok["left"]["clay_px"]
        res["width_ratio"] = round((wc + ok["right"]["d_px"] - ok["left"]["d_px"]) / wc, 4) if wc > 0 else None
    if "top" in ok and "bottom" in ok:
        hc = ok["bottom"]["clay_px"] - ok["top"]["clay_px"]
        res["height_ratio"] = round((hc + ok["bottom"]["d_px"] - ok["top"]["d_px"]) / hc, 4) if hc > 0 else None
    res["worst_edge_px"] = max([abs(e["d_px"]) for e in ok.values()]) if ok else None
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


def lock_v2(render, clay, frame, boxes, pan, frame_id=None, overlay_path=None, edges_mode="v3"):
    """render, clay: float RGB arrays of the 16:9 frame (any size). boxes: {name: (kind, (u0,u1,v0,v1))}. edges_mode "v3" (default,
    2026-11-04) or "v2" (the 2026-11-03 behaviour)."""
    cam = pr.Cam(0.0, 0.5, 0.46)
    rend = pr.fit(render, W, H)
    cl = pr.fit(clay, W, H)
    rep = dict(frame=frame, id=frame_id, size=[W, H], pan_endpoint=bool(pan), edges_mode=edges_mode,
               method=("lock_v2 (register + bands + ECC tiles + fixed edges)" if edges_mode == "v2" else
                       "lock_v2 edges v3 (register + bands / tiles with shared structure + box edges by cross-correlation + QA's named edges)"))
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
    v3 = edges_mode != "v2"
    for nm, (kind, box) in boxes.items():
        e = edge_pairs_v3(gc, gr, box) if v3 else edge_pairs(gc, gr, box)
        e["kind"] = kind
        if v3:
            for side, why in EYE_OVERRIDES.get(frame_id, {}).get("box", {}).get(nm, {}).items():
                if side in e["edges"]:
                    e["edges"][side].update(counted=False, eye_override=why)
                    ok = {k: x for k, x in e["edges"].items() if x.get("counted")}
                    e["worst_edge_px"] = max([abs(x["d_px"]) for x in ok.values()]) if ok else None
                    if side in ("top", "bottom"):
                        e.pop("height_ratio", None)
                    else:
                        e.pop("width_ratio", None)
        edges[nm] = e
    rep["fixed_edges"] = edges
    bmin = BAND_MIN_RESPONSE_V3 if v3 else BAND_MIN_RESPONSE
    tcount = (lambda x: x.get("rho") is not None and x["rho"] >= TILE_MIN_RHO_V3) if v3 else (lambda x: x["counted"])
    bands_raw = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_raw"]["bands"] if b["response"] >= bmin]
    bands_reg = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_registered"]["bands"] if b["response"] >= bmin]
    t_raw = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc"] if tcount(x)]
    t_reg = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc_registered"] if tcount(x)]
    named = named_edges(gc, gr, frame_id) if v3 else {}
    rep["named_edges"] = named
    named_px = [abs(n["d_xcorr_px"]) for n in named.values() if n["counted"]]
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
    e_pass = (not edge_px or max(edge_px) <= EDGE_MAX_PX) and all(RATIO_LO <= r <= RATIO_HI for r in ratios.values()) and \
        (not named_px or max(named_px) <= EDGE_MAX_PX)
    rep["summary"] = dict(
        register_shift_px=shift, register_scale=scale, register_scale_pct=[round((scale[0] - 1) * 100, 2), round((scale[1] - 1) * 100, 2)],
        worst_band_px=_worst(bands_raw), bands_reliable=len(bands_raw),
        worst_band_px_after_register=_worst(bands_reg), bands_reliable_after_register=len(bands_reg),
        worst_tile_ecc_px=_worst(t_raw), tiles_counted=len(t_raw),
        worst_tile_ecc_px_after_register=_worst(t_reg), tiles_counted_after_register=len(t_reg),
        fixed_edges_worst_px=max(edge_px) if edge_px else None, fixed_edges_measured=len(edge_px), fixed_ratios=ratios)
    if v3:
        rep["summary"].update(named_edges_worst_px=max(named_px) if named_px else None, named_edges_counted=len(named_px), named_edges_total=len(named),
                              named_edges=({k: v["d_xcorr_px"] for k, v in named.items() if v["counted"]} if named else None))
    else:
        rep.pop("named_edges", None)
        rep.pop("edges_mode", None)
    rep["verdict"] = dict(
        thresholds=dict(shift_px=SHIFT_MAX_PX, scale_tol=SCALE_TOL, residual_px=resid_max,
                        residual_rule=("pan endpoint: <= 2 px per band / tile after register" if pan else "video endpoint: <= 0.5 % of the width after register"),
                        edge_px=EDGE_MAX_PX, ratio=[RATIO_LO, RATIO_HI],
                        **(dict(edges_mode=edges_mode, counted="bands response >= 0.10, tiles rho >= 0.30, box edges and named lines xcorr r >= 0.5") if v3 else {}),
                        source="docs/ops/quality-gates-2026-11-02.md G1.4 (+ G1.3 ratios, proposal); qa/reports/2026-11-02-v7-g1.md section 1"),
        global_pass=bool(g_pass), residual_pass=bool(r_pass), edges_pass=bool(e_pass),
        residual_measured=bool(resid_vals), **{"pass": bool(g_pass and r_pass and e_pass)})
    if overlay_path:
        g = gray8(cl)
        e = cv2.Canny(g.astype(np.uint8), 60, 140)
        e = cv2.dilate(e, np.ones((2, 2), np.uint8))
        im = (rend * 255).astype(np.uint8).copy()
        im[e > 0] = (255, 40, 40)
        for name, n in (rep.get("named_edges") or {}).items():  # v3: QA's named lines, red = clay, green = clay + xcorr offset (grey when not counted)
            sp = next(x[2] for x in NAMED_EDGES[frame_id] if x[0] == name)
            col = (40, 200, 40) if n["counted"] else (150, 150, 150)
            rp = n["clay_px"] + (n["d_xcorr_px"] or 0)
            lab = f"{name} {n['d_xcorr_px']:+d} r{n['r']}" if n["d_xcorr_px"] is not None else f"{name} -"
            if n["orientation"] == "h":
                x0, x1 = int(sp[0] * W), int(sp[1] * W)
                cv2.line(im, (x0, n["clay_px"]), (x1, n["clay_px"]), (255, 0, 0), 2)
                cv2.line(im, (x0, rp), (x1, rp), col, 1)
                cv2.putText(im, lab, (x0, max(12, n["clay_px"] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 0, 0), 1)
            else:
                y0, y1 = int(sp[0] * H), int(sp[1] * H)
                cv2.line(im, (n["clay_px"], y0), (n["clay_px"], y1), (255, 0, 0), 2)
                cv2.line(im, (rp, y0), (rp, y1), col, 1)
                cv2.putText(im, lab, (n["clay_px"] + 4, y0 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 0, 0), 1)
        Image.fromarray(im).save(overlay_path, quality=82)
    return rep


def run_frame(fid, render_path=None, out_path=None, overlay_path=None, edges_mode="v3", date="2026-11-03"):
    """The lock of one registry still (default: its normalised raw `<id>.png`) against its round-4 clay. In edges v3 the frames of
    VIDEO_ENDPOINTS (W0-in, MB-in: dolly endpoints, QA §3) take the video-endpoint residual (9.6 px), not the pan one."""
    frame, kind, clay_file, pan, overscan, room = VF.frame(fid)
    if edges_mode != "v2" and frame in VIDEO_ENDPOINTS:
        pan = False
    od = VF.out_dir(fid)
    render_path = render_path or os.path.join(od, fid + ".png")
    r = load_rgb(render_path)
    c = load_rgb(os.path.join(VF.R4, clay_file))
    if overscan:
        r, c = crop_frame(r), crop_frame(c)
    rep = lock_v2(r, c, frame, VF.fixed_boxes(frame, overscan, fid), pan, frame_id=fid, overlay_path=overlay_path, edges_mode=edges_mode)
    rep.update(render=os.path.relpath(render_path, VF.REPO), clay=os.path.relpath(os.path.join(VF.R4, clay_file), VF.REPO),
               overscan_cropped_to_frame=bool(overscan), date=date,
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
    ap.add_argument("--edges", default="v3", choices=["v3", "v2"])
    ap.add_argument("--id", help="job id for the named edges (NAMED_EDGES)")
    a = ap.parse_args()
    r, c = load_rgb(a.render), load_rgb(a.clay)
    if a.overscan:
        r, c = crop_frame(r), crop_frame(c)
    rep = lock_v2(r, c, a.frame, VF.fixed_boxes(a.frame, a.overscan), a.pan, frame_id=a.id, overlay_path=a.overlay, edges_mode=a.edges)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep["summary"]), json.dumps(rep["verdict"]))
