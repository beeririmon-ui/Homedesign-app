"""
qa-agent 2026-11-07: G1 on the warm-modern living-room clay r3 (house plan 1.3.3 section 0א, WMC1-WMC8). Same method as
qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py (imported for its projection, its named-edge reader and the index helpers):
(1) QA's projection vs render-agent's r3 named lines; (2) the named plan lines of 1.3.3 on the r3 clay (median offset of the gradient peak
across each line, px at 1920); (3) the WMC6-WMC8 findings and the accepted tangents re-measured on render-agent's r3 index passes
(session scratchpad wm-r3-idx/, first-hit ids). Writes data/clay-wm-r3.json and overlays/clay-r3-M0-named-edges.jpg.
Usage: ~/.venvs/motion/bin/python -I clay_wm_r3.py
"""
import importlib.util
import json
import math
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
spec = importlib.util.spec_from_file_location("r1", os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay/tools/clay_wm_r1.py"))
r1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1)
CL = os.path.join(REPO, "assets/blockout/house/framing/warm-modern-r3")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix5-clay-r3")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r3-idx"
CAM = r1.CAM
FW, FH, CX, CY = r1.FW, r1.FH, r1.CX, r1.CY

LINES = {
    "glazing back jamb (X -2.30, Y 0.75)": ((-2.30, 0.75, 0.50), (-2.30, 0.75, 2.65)),
    "glazing head (Z 2.70)": ((-2.30, 0.80, 2.70), (-2.30, 2.60, 2.70)),
    "bench front top edge (X -1.98, Z 0.45; WMC4, WMC6)": ((-1.98, 1.05, 0.45), (-1.98, 2.60, 0.45)),
    "bench back-end front corner (X -1.98, Y 1.00; WMC6)": ((-1.98, 1.00, 0.03), (-1.98, 1.00, 0.42)),
    "bench back-end top edge (Y 1.00, Z 0.45)": ((-2.28, 1.00, 0.45), (-2.00, 1.00, 0.45)),
    "back wall ceiling line (Y 0, Z 3.00)": ((-1.80, 0.0, 3.0), (1.90, 0.0, 3.0)),
    "back wall floor line (Y 0, Z 0)": ((-1.60, 0.0, 0.0), (1.90, 0.0, 0.0)),
    "ceiling band bottom edge (X -2.05, Z 2.82; WMC5)": ((-2.05, 0.40, 2.82), (-2.05, 3.60, 2.82)),
    "curtain stack back edge (Y 2.65; WMC7)": ((-2.16, 2.65, 0.10), (-2.16, 2.65, 2.70)),
}


def load_idx(fid):
    z = np.load(os.path.join(IDX, f"{fid}.npz"))
    nm = json.load(open(os.path.join(IDX, f"{fid}-names.json")))["names"]
    return z["idx"][CY:CY + FH, CX:CX + FW], {int(k): v[0] for k, v in nm.items()}


if __name__ == "__main__":
    out = {}
    ag = json.load(open(os.path.join(CL, "clay-checks-2026-11-07.json")))
    agl = ag["named_lines"]["M0"]
    ends = {"bench_front_top_edge_X-1.98": (-1.98, 1.00, 0.45), "bench_end_back_Y1.00": (-1.98, 1.00, 0.0),
            "rounded_corner_tangent_left_wall_Y0.30": (-2.30, 0.30, 0.0), "rounded_corner_tangent_back_wall_X-2.00": (-2.00, 0.0, 0.0),
            "curtain_track_X-2.22_Z2.86": (-2.22, 0.30, 2.86), "curtain_stack_back_edge_Y2.65": (-2.16, 2.65, 0.0)}
    comp = {}
    for k, P in ends.items():
        u, v, _ = r1.project(CAM["M0"], *P)
        ra = agl.get(k, {}).get("start_uv")
        comp[k] = dict(qa_uv=[round(u, 4), round(v, 4)], render_agent_start_uv=ra,
                       d_u=None if not ra else round(u - ra[0], 4), d_v=None if not ra else round(v - ra[1], 4))
    out["projection_vs_render_agent_r3"] = comp
    g = r1.gray(os.path.join(CL, "M0.png"))
    out["named_edges_M0_r3"] = {name: r1.measure_line(g, CAM["M0"], A, B) for name, (A, B) in LINES.items()}
    im = cv2.cvtColor(np.asarray(Image.open(os.path.join(CL, "M0.png")).convert("RGB")), cv2.COLOR_RGB2BGR)
    for name, (A, B) in LINES.items():
        pts = []
        for k in range(60):
            t = k / 59
            P = [A[i] + (B[i] - A[i]) * t for i in range(3)]
            u, v, d = r1.project(CAM["M0"], *P)
            if d > 0.1:
                pts.append(tuple(int(c) for c in r1.to_px(u, v)))
        for p, q in zip(pts[:-1], pts[1:]):
            cv2.line(im, p, q, (0, 0, 255), 3)
    cv2.imwrite(os.path.join(OUT, "overlays", "clay-r3-M0-named-edges.jpg"), cv2.resize(im, (2036, 1145)), [cv2.IMWRITE_JPEG_QUALITY, 85])
    idx, names = load_idx("M0")
    m = lambda key: np.isin(idx, [k for k, v in names.items() if v == key])  # noqa: E731
    pot_all, crown, arm = idx == 35, idx == 60, idx == 3
    bench, cur, mag = m("living/window-bench"), m("living/curtains"), m("living/magazine-holder")
    bas, vase, table = m("living/basket"), m("living/vase"), idx == 2
    f = {}
    for nm_, a, b in (("WMC6 pot (incl. trunk) vs bench", pot_all, bench), ("WMC8 holder vs armchair", mag, arm), ("WMC8 holder vs basket", mag, bas),
                      ("WMC8 holder vs coffee table", mag, table), ("vase vs armchair", vase, arm), ("crown vs curtains", crown, cur)):
        d = r1.min_dist(a, b)
        f[nm_] = dict(min_gap_px_3840=d, gap_frame_width=None if d is None else round(d / FW, 4))
    # WMC7: the armchair in front of the stack: per row, the stack's visible right edge minus the armchair's left edge
    rows = []
    for y in range(FH):
        cs, ca = np.where(cur[y])[0], np.where(arm[y])[0]
        if len(cs) and len(ca):
            rows.append((cs.max() - ca.min()) / FW)
    f["WMC7 armchair over the stack (u overlap: stack's visible right edge minus the armchair's left edge, rows where both show)"] = dict(
        rows=len(rows), median=round(float(np.median(rows)), 4) if rows else None, min=round(float(np.min(rows)), 4) if rows else None)
    # the stack against the frame's left edge (16:9 frame) and against the overscan canvas
    full = np.load(os.path.join(IDX, "M0.npz"))["idx"]
    curf = np.isin(full, [k for k, v in names.items() if v == "living/curtains"])
    f["curtain stack vs left edge"] = dict(rows_cut_by_frame_edge=int(cur[:, 0].sum()), frame_rows=FH,
                                           leftmost_canvas_col=int(np.where(curf.any(0))[0].min()), canvas_margin_frame_u=round(float(np.where(curf.any(0))[0].min()) / FW, 4))
    # basket top vs pot rim (accepted at 1.30 %)
    bt = np.where(bas.any(1))[0].min()
    pot_cols = np.where(pot_all.any(0))[0]
    f["basket top v"] = round(float(bt) / FH, 4)
    out["findings_M0_r3_index"] = f
    out["M0p"] = {"corner_arc_tangent_u_R0.30": round(r1.project(CAM["M0p"], -2.30, 0.30, 1.5)[0], 4),
                  "bench_back_corner_u_Y1.00": round(r1.project(CAM["M0p"], -1.98, 1.00, 0.45)[0], 4)}
    json.dump(out, open(os.path.join(OUT, "data", "clay-wm-r3.json"), "w"), indent=1)
    print(json.dumps(comp))
    for k, v in out["named_edges_M0_r3"].items():
        print(k, {kk: v.get(kk) for kk in ("samples", "strong_samples", "median_offset_px_1920", "iqr_px_1920")})
    for k, v in f.items():
        print(k, v)
    print(out["M0p"])
