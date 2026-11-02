"""
G1.4 clay lock with the scale check (P6), and G1.3 edges of the fixed furniture, on every v7 frame and pose.
  check    pan_reproject.overlap_check(clay, cam, render, cam): the same camera -> identity reprojection; residual shift by
           phase correlation of Laplacian edges on the whole frame and in 4 vertical bands (px at 1920x1080).
  register pan_reproject.register(render, clay): one global affine (ECC on edges) -> shift and scale of the whole frame;
           then check again on the registered render (what remains is local redrawing).
  edges    for every fixed-furniture / architecture / window box of the clay selfcheck: the strongest vertical edge within
           +-0.035 of each clay box edge (rows 35-85 % of the box), in the clay and in the render; the same for the top and
           bottom edges (columns 35-85 %). Reported as the offset in px at 1920 and the width / height ratio render : clay.
Writes data/lock-<id>.json and overlays/lock-<id>.jpg (clay edges in red over the render, 1920 wide).
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W, H = 1920, 1080
os.makedirs(os.path.join(C.OUT, "data"), exist_ok=True)
os.makedirs(os.path.join(C.OUT, "overlays"), exist_ok=True)


def gray(img):
    return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def strongest_edge(prof, c, tol, w):
    x0, x1 = max(0, int((c - tol) * w)), min(len(prof), int((c + tol) * w))
    if x1 - x0 < 3:
        return None, 0.0
    i = x0 + int(np.argmax(prof[x0:x1]))
    return i, float(prof[i])


def edge_pairs(gc, gr, box, name):
    """Vertical (left/right) and horizontal (top/bottom) edge positions of one box in clay and render."""
    u0, u1, v0, v1 = box
    res = dict(box=[round(x, 4) for x in box])
    gxc, gxr = np.abs(np.diff(gc, axis=1)), np.abs(np.diff(gr, axis=1))
    gyc, gyr = np.abs(np.diff(gc, axis=0)), np.abs(np.diff(gr, axis=0))
    ry0, ry1 = int((v0 + 0.35 * (v1 - v0)) * H), int((v0 + 0.85 * (v1 - v0)) * H)
    cx0, cx1 = int((u0 + 0.35 * (u1 - u0)) * W), int((u0 + 0.85 * (u1 - u0)) * W)
    tol = 0.035
    out = {}
    if ry1 - ry0 >= 4:
        pc, pr_ = gxc[ry0:ry1].mean(0), gxr[ry0:ry1].mean(0)
        for side, c in (("left", u0), ("right", u1)):
            if c <= 0.01 or c >= 0.99:
                continue                          # the box is cut by the frame: no edge to find
            ic, sc = strongest_edge(pc, c, tol, W)
            ir, sr = strongest_edge(pr_, c, tol, W)
            if ic is None or ir is None or sc < 4.0 or sr < 4.0:
                continue                          # no clear edge on one side: not a measurement
            out[side] = dict(clay_px=ic, render_px=ir, d_px=ir - ic, clay_strength=round(sc, 1), render_strength=round(sr, 1))
    if cx1 - cx0 >= 4:
        pc, pr_ = gyc[:, cx0:cx1].mean(1), gyr[:, cx0:cx1].mean(1)
        for side, c in (("top", v0), ("bottom", v1)):
            if c <= 0.01 or c >= 0.99:
                continue
            ic, sc = strongest_edge(pc, c, tol, H)
            ir, sr = strongest_edge(pr_, c, tol, H)
            if ic is None or ir is None or sc < 4.0 or sr < 4.0:
                continue
            out[side] = dict(clay_px=ic, render_px=ir, d_px=ir - ic, clay_strength=round(sc, 1), render_strength=round(sr, 1))
    res["edges"] = out
    if "left" in out and "right" in out:
        wc = out["right"]["clay_px"] - out["left"]["clay_px"]
        wr = out["right"]["render_px"] - out["left"]["render_px"]
        res["width_ratio"] = round(wr / wc, 4) if wc > 0 else None
    if "top" in out and "bottom" in out:
        hc = out["bottom"]["clay_px"] - out["top"]["clay_px"]
        hr = out["bottom"]["render_px"] - out["top"]["render_px"]
        res["height_ratio"] = round(hr / hc, 4) if hc > 0 else None
    res["worst_edge_px"] = max([abs(e["d_px"]) for e in out.values()] or [None]) if out else None
    return res


def tiles_ecc(rend, clay, nx=4, ny=2, min_rho=0.12):
    """Local residual: ECC translation of the render's edge map onto the clay's, per tile (nx x ny), at 960 wide.
    rho is ECC's correlation after convergence; tiles under min_rho (no shared structure) are reported but not counted."""
    e_ref, e_img = C.pr._edges(clay, 960), C.pr._edges(rend, 960)
    h, w = e_ref.shape
    s = W / w
    out = []
    for j in range(ny):
        for i in range(nx):
            x0, x1, y0, y1 = int(i * w / nx), int((i + 1) * w / nx), int(j * h / ny), int((j + 1) * h / ny)
            a, b = e_ref[y0:y1, x0:x1], e_img[y0:y1, x0:x1]
            M = np.eye(2, 3, dtype=np.float32)
            crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5)
            try:
                rho, M = cv2.findTransformECC(a, b, M, cv2.MOTION_TRANSLATION, crit, None, 5)
                out.append(dict(u=[round(x0 / w, 2), round(x1 / w, 2)], v=[round(y0 / h, 2), round(y1 / h, 2)],
                                dx_px=round(float(M[0, 2]) * s, 2), dy_px=round(float(M[1, 2]) * s, 2), rho=round(float(rho), 3),
                                counted=bool(rho >= min_rho)))
            except cv2.error:
                out.append(dict(u=[round(x0 / w, 2), round(x1 / w, 2)], v=[round(y0 / h, 2), round(y1 / h, 2)], dx_px=None, dy_px=None,
                                rho=None, counted=False, note="ECC did not converge"))
    return out


def overlay(render, clay, path):
    g = gray(clay)
    e = cv2.Canny(g.astype(np.uint8), 60, 140)
    e = cv2.dilate(e, np.ones((2, 2), np.uint8))
    im = (render * 255).astype(np.uint8).copy()
    im[e > 0] = (255, 40, 40)
    cv2.imwrite(path, cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 82])


def run(fid):
    d = C.load(fid)
    cam = d["cam"]
    clay = C.at(d["clay"], W, H)
    rend = C.at(d["graded"], W, H)
    rep = dict(frame=fid, kind=d["kind"], overscan=d["ovs"], size=[W, H])
    # 1. check as rendered
    rep["check_raw"] = C.pr.overlap_check(clay, cam, rend, cam, W, H)
    # 2. register: one global affine
    reg, M = C.pr.register(rend, clay)
    rep["register"] = dict(affine=np.round(M, 5).tolist(), shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)],
                           scale=[round(float(M[0, 0]), 5), round(float(M[1, 1]), 5)],
                           note="affine maps render -> clay at 1920x1080 (register's own convention); shift = translation of the frame, scale = diagonal")
    rep["check_registered"] = C.pr.overlap_check(clay, cam, reg, cam, W, H)
    rep["check_note"] = ("phase correlation between a clay and a photo-real render is reliable only where response >= 0.05; "
                         "tiles_ecc below is QA's own local measure (ECC translation per tile on the same edge maps register uses)")
    rep["tiles_ecc"] = tiles_ecc(rend, clay)
    rep["tiles_ecc_registered"] = tiles_ecc(reg, clay)
    # 3. edges of the fixed furniture / architecture / windows, on the un-registered render (what the model drew)
    gc, gr = gray(clay), gray(rend)
    edges = {}
    for nm, (kind, box, area, vis) in C.boxes(d).items():
        if kind not in ("furniture", "architecture", "window", "door", "mirror"):
            continue
        if (box[1] - box[0]) * (box[3] - box[2]) < 0.002:
            continue
        edges[nm] = edge_pairs(gc, gr, box, nm)
        edges[nm]["kind"] = kind
        edges[nm]["visible_pct"] = vis
    rep["fixed_edges"] = edges
    worst = [e["worst_edge_px"] for e in edges.values() if e.get("worst_edge_px") is not None]
    rep["fixed_edges_worst_px"] = max(worst) if worst else None
    ratios = {nm: e.get("width_ratio") for nm, e in edges.items() if e.get("width_ratio")}
    rep["fixed_width_ratios"] = ratios
    bands = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_raw"]["bands"] if b["response"] >= 0.05]
    bands_reg = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_registered"]["bands"] if b["response"] >= 0.05]
    t = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc"] if x["counted"]]
    tr = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc_registered"] if x["counted"]]
    rep["summary"] = dict(global_shift_px=max(abs(rep["check_raw"]["shift_px"]["dx"]), abs(rep["check_raw"]["shift_px"]["dy"])),
                          global_shift_response=rep["check_raw"]["shift_px"]["response"],
                          worst_band_px=round(max(bands), 2) if bands else None, bands_reliable=len(bands),
                          worst_band_px_after_register=round(max(bands_reg), 2) if bands_reg else None,
                          worst_tile_ecc_px=round(max(t), 2) if t else None, tiles_counted=len(t),
                          worst_tile_ecc_px_after_register=round(max(tr), 2) if tr else None,
                          register_shift_px=rep["register"]["shift_px"], register_scale=rep["register"]["scale"],
                          fixed_edges_worst_px=rep["fixed_edges_worst_px"],
                          frame_file_matches_crop=d.get("frame_file_matches_crop"))
    json.dump(rep, open(os.path.join(C.OUT, "data", f"lock-{fid.replace(chr(39), 'prime')}.json"), "w"), indent=1)
    overlay(rend, clay, os.path.join(C.OUT, "overlays", f"lock-{fid.replace(chr(39), 'prime')}.jpg"))
    s = rep["summary"]
    print(f"{fid:9s} tiles {s['worst_tile_ecc_px']} ({s['tiles_counted']}/8) -> reg {s['worst_tile_ecc_px_after_register']}  bands(resp>=.05) {s['worst_band_px']} ({s['bands_reliable']})  "
          f"affine shift {s['register_shift_px']} scale {s['register_scale']}  edges worst {s['fixed_edges_worst_px']}  ratios {ratios}")
    return rep


if __name__ == "__main__":
    ids = sys.argv[1:] or (C.MASTERS + C.POSES)
    for f in ids:
        run(f)
