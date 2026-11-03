"""
G1.4 clay lock with scale, and G1.3 edges of the fixed furniture, on the four v8 retakes, measured by QA on the raw normalised
still (geometry) and confirmed on the graded-v3 file. Independent of render-agent's lock_v2.py (which is a port of QA's
2026-11-02 method): the same three measures are re-run here by QA's own code, and a fourth, differently built estimator is added:

  xcorr edges   for every clay box edge of a fixed piece: the 1-D gradient profile across the edge (averaged along 35-85 % of
                the edge's span) in the clay and in the render, cross-correlated within +-60 px at 1920 -> the offset of the
                whole edge (not the strongest single peak), with the correlation peak as its confidence. A line the model moved
                shows as an offset; a line it redrew at a different size shows as different offsets on the two sides.

Writes data/lock-<id>.json and overlays/lock-<id>.jpg (clay Canny edges in red over the render, 1920 wide), and a comparison
row against the render-agent's <id>-lock-v2.json.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

W, H = 1920, 1080
SHIFT_MAX = 0.005 * W
SCALE_TOL = 0.005
RESID_PAN = 2.0
RESID_VIDEO = SHIFT_MAX
EDGE_MAX = 0.01 * W
RATIO = (0.95, 1.05)
# which retake is a pan endpoint (2 px) and which only a video endpoint (0.5 %), per docs/transitions-render-plan-2026-11-02.md
# section 5 and the round-4 plan: W0-in ends the V4 pull-back / T-HW slide (no pan); K-girl-0 is the T-CGirl pan start (33 deg);
# B1 is the T-CBath pan end (22 deg) and the P-B start (35 deg); B2 is the P-B end
PAN_ENDPOINT = {"W0-in r2": False, "K-girl-0 r2": True, "B1 r3": True, "B2 r3": True}


def gray(img):
    return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)


def strongest_edge(prof, c, tol, n):
    x0, x1 = max(0, int((c - tol) * n)), min(len(prof), int((c + tol) * n))
    if x1 - x0 < 3:
        return None, 0.0
    i = x0 + int(np.argmax(prof[x0:x1]))
    return i, float(prof[i])


def xcorr_offset(pc, pr_, c, n, half=60):
    """Offset (px) of the render profile against the clay profile around c, by normalised cross-correlation within +-half."""
    ci = int(c * n)
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


def edge_pairs(gc, gr, box):
    u0, u1, v0, v1 = box
    gxc, gxr = np.abs(np.diff(gc, axis=1)), np.abs(np.diff(gr, axis=1))
    gyc, gyr = np.abs(np.diff(gc, axis=0)), np.abs(np.diff(gr, axis=0))
    ry0, ry1 = int((v0 + 0.35 * (v1 - v0)) * H), int((v0 + 0.85 * (v1 - v0)) * H)
    cx0, cx1 = int((u0 + 0.35 * (u1 - u0)) * W), int((u0 + 0.85 * (u1 - u0)) * W)
    out, xc = {}, {}
    if ry1 - ry0 >= 4:
        pc, prr = gxc[ry0:ry1].mean(0), gxr[ry0:ry1].mean(0)
        for side, c in (("left", u0), ("right", u1)):
            if c <= 0.01 or c >= 0.99:
                continue
            ic, sc = strongest_edge(pc, c, 0.035, W)
            ir, sr = strongest_edge(prr, c, 0.035, W)
            if ic is not None and ir is not None and sc >= 4.0 and sr >= 4.0:
                out[side] = dict(clay_px=ic, render_px=ir, d_px=ir - ic, clay_strength=round(sc, 1), render_strength=round(sr, 1))
            o, r = xcorr_offset(pc, prr, c, W)
            if o is not None and r >= 0.35:
                xc[side] = dict(d_px=o, corr=r)
    if cx1 - cx0 >= 4:
        pc, prr = gyc[:, cx0:cx1].mean(1), gyr[:, cx0:cx1].mean(1)
        for side, c in (("top", v0), ("bottom", v1)):
            if c <= 0.01 or c >= 0.99:
                continue
            ic, sc = strongest_edge(pc, c, 0.035, H)
            ir, sr = strongest_edge(prr, c, 0.035, H)
            if ic is not None and ir is not None and sc >= 4.0 and sr >= 4.0:
                out[side] = dict(clay_px=ic, render_px=ir, d_px=ir - ic, clay_strength=round(sc, 1), render_strength=round(sr, 1))
            o, r = xcorr_offset(pc, prr, c, H)
            if o is not None and r >= 0.35:
                xc[side] = dict(d_px=o, corr=r)
    res = dict(box=[round(x, 4) for x in box], edges=out, xcorr=xc)
    if "left" in out and "right" in out:
        wc = out["right"]["clay_px"] - out["left"]["clay_px"]
        wr = out["right"]["render_px"] - out["left"]["render_px"]
        res["width_ratio"] = round(wr / wc, 4) if wc > 0 else None
    if "top" in out and "bottom" in out:
        hc = out["bottom"]["clay_px"] - out["top"]["clay_px"]
        hr = out["bottom"]["render_px"] - out["top"]["render_px"]
        res["height_ratio"] = round(hr / hc, 4) if hc > 0 else None
    if "left" in xc and "right" in xc:
        wc = (u1 - u0) * W
        res["width_ratio_xcorr"] = round((wc + xc["right"]["d_px"] - xc["left"]["d_px"]) / wc, 4)
    if "top" in xc and "bottom" in xc:
        hc = (v1 - v0) * H
        res["height_ratio_xcorr"] = round((hc + xc["bottom"]["d_px"] - xc["top"]["d_px"]) / hc, 4)
    res["worst_edge_px"] = max([abs(e["d_px"]) for e in out.values()]) if out else None
    res["worst_xcorr_px"] = max([abs(e["d_px"]) for e in xc.values()]) if xc else None
    return res


def tiles_ecc(rend, clay, nx=4, ny=2, min_rho=0.12):
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
            rec = dict(u=[round(x0 / w, 2), round(x1 / w, 2)], v=[round(y0 / h, 2), round(y1 / h, 2)])
            try:
                rho, M = cv2.findTransformECC(a, b, M, cv2.MOTION_TRANSLATION, crit, None, 5)
                rec.update(dx_px=round(float(M[0, 2]) * s, 2), dy_px=round(float(M[1, 2]) * s, 2), rho=round(float(rho), 3), counted=bool(rho >= min_rho))
            except cv2.error:
                rec.update(dx_px=None, dy_px=None, rho=None, counted=False, note="ECC did not converge")
            out.append(rec)
    return out


def overlay(render, clay, path, note=""):
    g = gray(clay)
    e = cv2.Canny(g.astype(np.uint8), 60, 140)
    e = cv2.dilate(e, np.ones((2, 2), np.uint8))
    im = (render * 255).astype(np.uint8).copy()
    im[e > 0] = (255, 40, 40)
    im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
    cv2.putText(im, note, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(path, im, [cv2.IMWRITE_JPEG_QUALITY, 82])


def measure(rend, clay, d, pan):
    cam = d["cam"]
    rep = {}
    rep["check_raw"] = C.pr.overlap_check(clay, cam, rend, cam, W, H)
    reg, M = C.pr.register(rend, clay)
    rep["register"] = dict(affine=np.round(M, 5).tolist(), shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)],
                           scale=[round(float(M[0, 0]), 5), round(float(M[1, 1]), 5)])
    rep["check_registered"] = C.pr.overlap_check(clay, cam, reg, cam, W, H)
    rep["tiles_ecc"] = tiles_ecc(rend, clay)
    rep["tiles_ecc_registered"] = tiles_ecc(reg, clay)
    gc, gr = gray(clay), gray(rend)
    edges = {}
    for nm, (kind, box, area, vis) in C.boxes(d).items():
        if kind not in ("furniture", "architecture", "window", "door", "mirror"):
            continue
        if (box[1] - box[0]) * (box[3] - box[2]) < 0.002:
            continue
        edges[nm] = edge_pairs(gc, gr, box)
        edges[nm]["kind"] = kind
        edges[nm]["visible_pct"] = vis
    rep["fixed_edges"] = edges
    bands = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_raw"]["bands"] if b["response"] >= 0.05]
    bands_reg = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in rep["check_registered"]["bands"] if b["response"] >= 0.05]
    t = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc"] if x["counted"]]
    tr = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc_registered"] if x["counted"]]
    worst = [e["worst_edge_px"] for e in edges.values() if e.get("worst_edge_px") is not None]
    worstx = [e["worst_xcorr_px"] for e in edges.values() if e.get("worst_xcorr_px") is not None]
    ratios = {nm + " w": e["width_ratio"] for nm, e in edges.items() if e.get("width_ratio")}
    ratios.update({nm + " h": e["height_ratio"] for nm, e in edges.items() if e.get("height_ratio")})
    ratios_x = {nm + " w": e["width_ratio_xcorr"] for nm, e in edges.items() if e.get("width_ratio_xcorr")}
    ratios_x.update({nm + " h": e["height_ratio_xcorr"] for nm, e in edges.items() if e.get("height_ratio_xcorr")})
    shift, scale = rep["register"]["shift_px"], rep["register"]["scale"]
    resid_max = RESID_PAN if pan else RESID_VIDEO
    resid_vals = [v for v in ((round(max(bands_reg), 2) if bands_reg else None), (round(max(tr), 2) if tr else None)) if v is not None]
    g_pass = max(abs(shift[0]), abs(shift[1])) <= SHIFT_MAX and max(abs(scale[0] - 1), abs(scale[1] - 1)) <= SCALE_TOL
    r_pass = bool(resid_vals) and max(resid_vals) <= resid_max
    e_pass = (not worst or max(worst) <= EDGE_MAX) and all(RATIO[0] <= r <= RATIO[1] for r in ratios.values())
    rep["summary"] = dict(register_shift_px=shift, register_scale=scale, register_scale_pct=[round((scale[0] - 1) * 100, 2), round((scale[1] - 1) * 100, 2)],
                          global_shift_px_phase=max(abs(rep["check_raw"]["shift_px"]["dx"]), abs(rep["check_raw"]["shift_px"]["dy"])),
                          global_shift_response=rep["check_raw"]["shift_px"]["response"],
                          worst_band_px=round(max(bands), 2) if bands else None, bands_reliable=len(bands),
                          worst_band_px_after_register=round(max(bands_reg), 2) if bands_reg else None, bands_reliable_after_register=len(bands_reg),
                          worst_tile_ecc_px=round(max(t), 2) if t else None, tiles_counted=len(t),
                          worst_tile_ecc_px_after_register=round(max(tr), 2) if tr else None, tiles_counted_after_register=len(tr),
                          fixed_edges_worst_px=max(worst) if worst else None, fixed_edges_measured=len(worst), fixed_ratios=ratios,
                          xcorr_edges_worst_px=max(worstx) if worstx else None, xcorr_ratios=ratios_x)
    rep["verdict"] = dict(residual_rule=("pan endpoint: <= 2 px per band / tile after register" if pan else "video endpoint only: <= 0.5 % (9.6 px) after register"),
                          global_pass=bool(g_pass), residual_pass=bool(r_pass), edges_pass=bool(e_pass), passed=bool(g_pass and r_pass and e_pass))
    return rep


def run(sid):
    d = C.load(sid)
    pan = PAN_ENDPOINT[sid]
    clay = C.at(d["clay"], W, H)
    rep = dict(frame=sid, clay=d["clay_file"], pan_endpoint=pan, size=[W, H])
    rep["raw"] = measure(C.at(d["raw"], W, H), clay, d, pan)
    rep["raw"]["file"] = d["raw_file"]
    rep["graded_v3"] = measure(C.at(d["graded"], W, H), clay, d, pan)
    rep["graded_v3"]["file"] = d["graded_file"]
    a = C.agent_lock(sid)
    if a:
        s, v = a["summary"], a["verdict"]
        rep["agent_lock_v2"] = dict(file=d["raw_file"].replace(".png", "-lock-v2.json"), register_shift_px=s["register_shift_px"], register_scale_pct=s["register_scale_pct"],
                                    worst_band_px_after_register=s["worst_band_px_after_register"], worst_tile_ecc_px_after_register=s["worst_tile_ecc_px_after_register"],
                                    fixed_edges_worst_px=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"], pan_endpoint=a.get("pan_endpoint"),
                                    passed=v["pass"], global_pass=v["global_pass"], residual_pass=v["residual_pass"], edges_pass=v["edges_pass"])
        q = rep["raw"]["summary"]
        rep["qa_vs_agent"] = dict(shift_diff_px=[round(q["register_shift_px"][i] - s["register_shift_px"][i], 2) for i in range(2)],
                                  scale_pct_diff=[round(q["register_scale_pct"][i] - s["register_scale_pct"][i], 2) for i in range(2)],
                                  band_after_diff=(None if q["worst_band_px_after_register"] is None or s["worst_band_px_after_register"] is None
                                                   else round(q["worst_band_px_after_register"] - s["worst_band_px_after_register"], 2)),
                                  tile_after_diff=(None if q["worst_tile_ecc_px_after_register"] is None or s["worst_tile_ecc_px_after_register"] is None
                                                   else round(q["worst_tile_ecc_px_after_register"] - s["worst_tile_ecc_px_after_register"], 2)),
                                  edges_diff=(None if q["fixed_edges_worst_px"] is None or s["fixed_edges_worst_px"] is None else q["fixed_edges_worst_px"] - s["fixed_edges_worst_px"]),
                                  pan_rule_agent=a.get("pan_endpoint"), pan_rule_qa=pan)
    json.dump(rep, open(os.path.join(C.OUT, "data", f"lock-{C.fn(sid)}.json"), "w"), indent=1)
    s = rep["raw"]["summary"]
    overlay(C.at(d["raw"], W, H), clay, os.path.join(C.OUT, "overlays", f"lock-{C.fn(sid)}.jpg"),
            f"{sid}: clay edges (red) over the raw still | shift {s['register_shift_px']} scale% {s['register_scale_pct']} | edges worst {s['fixed_edges_worst_px']} xcorr {s['xcorr_edges_worst_px']}")
    print(f"{sid:12s} shift {s['register_shift_px']} scale% {s['register_scale_pct']} | resid band {s['worst_band_px_after_register']} ({s['bands_reliable_after_register']}) "
          f"tile {s['worst_tile_ecc_px_after_register']} ({s['tiles_counted_after_register']}/8) | edges worst {s['fixed_edges_worst_px']} ratios {s['fixed_ratios']} "
          f"| xcorr worst {s['xcorr_edges_worst_px']} ratios {s['xcorr_ratios']} | {'PASS' if rep['raw']['verdict']['passed'] else 'FAIL'} "
          f"(g {int(rep['raw']['verdict']['global_pass'])} r {int(rep['raw']['verdict']['residual_pass'])} e {int(rep['raw']['verdict']['edges_pass'])})")
    if "qa_vs_agent" in rep:
        print(f"{'':12s} vs agent: shift diff {rep['qa_vs_agent']['shift_diff_px']} scale diff {rep['qa_vs_agent']['scale_pct_diff']} band diff {rep['qa_vs_agent']['band_after_diff']} "
              f"tile diff {rep['qa_vs_agent']['tile_after_diff']} edges diff {rep['qa_vs_agent']['edges_diff']} | agent pan rule {rep['qa_vs_agent']['pan_rule_agent']} QA {pan}")
    for nm, e in rep["raw"]["fixed_edges"].items():
        print(f"{'':12s}   {nm}: peaks {{{', '.join(f'{k} {v['d_px']:+d}' for k, v in e['edges'].items())}}} xcorr {{{', '.join(f'{k} {v['d_px']:+d} (r {v['corr']})' for k, v in e['xcorr'].items())}}} "
              f"w {e.get('width_ratio')} / {e.get('width_ratio_xcorr')} h {e.get('height_ratio')} / {e.get('height_ratio_xcorr')}")
    return rep


if __name__ == "__main__":
    for f in (sys.argv[1:] or C.RETAKES):
        run(f)
