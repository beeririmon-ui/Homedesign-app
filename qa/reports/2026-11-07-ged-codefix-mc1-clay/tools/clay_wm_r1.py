"""
qa-agent 2026-11-07: G1 (short, per the coordinator's update) on the warm-modern living-room clay r1.
(1) QA's own projection from the plan's camera record (docs/house-plan.json cameras M0 / M0p: loc, yaw_deg_left, lens 24 on a
    36 mm-wide 16:9 frame, shift u0 / v0), built from a rotation, not from render-agent's P(); compared with the uv render-agent
    wrote in clay-checks-2026-11-07.json (named_lines).
(2) Named edges on the clay itself: every named plan line of 1.3.1 section 0א as built in r1 is projected, sampled at 40 points,
    and at each point the clay's gradient profile across the line (+-20 px of the 3840 frame, gray blurred sigma 1) gives the
    nearest strong peak; the median offset is the line's fit (px at 1920 = px at 3840 / 2).
(3) render-agent's r1 findings, re-measured on his index passes (session scratchpad wm-r1-idx/, first-hit object ids):
    pot vs back stack, armchair / basket vs magazine holder, vase vs armchair back; the crown and the M0p corner by plan arithmetic.
Writes data/clay-wm-r1.json and overlays/clay-M0-named-edges.jpg. Usage: ~/.venvs/motion/bin/python -I clay_wm_r1.py
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
CL = os.path.join(REPO, "assets/blockout/house/framing/warm-modern-r1")
OUT = os.path.join(REPO, "qa/reports/2026-11-07-ged-codefix-mc1-clay")
IDX = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-r1-idx"
plan = json.load(open(os.path.join(REPO, "docs/house-plan.json")))
CAM = {c["id"]: c for c in plan["cameras"] if c["id"] in ("M0", "M0p", "M0x")}
CX, CY, FW, FH = 116, 65, 3840, 2160   # overscan canvas 4072 x 2290 -> the 16:9 frame


def project(cam, X, Y, Z):
    """plan axes: X right, Y toward the viewer (back wall at Y 0), Z up; yaw 0 looks along -Y, yaw_deg_left turns left."""
    a = math.radians(cam["yaw_deg_left"])
    fwd = np.array([-math.sin(a), -math.cos(a), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    right = np.array([math.cos(a), -math.sin(a), 0.0])   # X right in this (left-handed) plan
    p = np.array([X, Y, Z]) - np.array(cam["loc"])
    d = float(p @ fwd)
    lens = cam.get("lens", 24)
    fx = lens / 36.0                 # focal in frame widths
    fy = fx * 16 / 9                 # square pixels on 16:9
    return cam["u0"] + fx * float(p @ right) / d, cam["v0"] - fy * float(p @ up) / d, d


def to_px(u, v):
    return CX + u * FW, CY + v * FH


# named lines of plan 1.3.1 section 0א as built in r1 (1.3.2 moves the bench edge to X -1.98, the corner radius to 0.30 and the
# track into the band's slot; r1 is the 1.3.1 build)
LINES = {
    "glazing back jamb (X -2.30, Y 0.75)": ((-2.30, 0.75, 0.50), (-2.30, 0.75, 2.65)),
    "glazing head (Z 2.70)": ((-2.30, 0.80, 2.70), (-2.30, 2.80, 2.70)),
    "bench top meets the window wall (Z 0.45)": ((-2.30, 0.80, 0.45), (-2.30, 2.80, 0.45)),
    "bench front top edge (X -1.90, Z 0.45)": ((-1.90, 0.80, 0.45), (-1.90, 2.80, 0.45)),
    "bench back-end front corner (X -1.90, Y 0.75)": ((-1.90, 0.75, 0.03), (-1.90, 0.75, 0.42)),
    "back wall floor line (Y 0, Z 0)": ((-1.80, 0.0, 0.0), (1.90, 0.0, 0.0)),
    "back wall ceiling line (Y 0, Z 3.00)": ((-1.80, 0.0, 3.0), (1.90, 0.0, 3.0)),
    "track band bottom edge (X -2.05, Z 2.82)": ((-2.05, 0.40, 2.82), (-2.05, 3.60, 2.82)),
}


def gray(path):
    a = np.asarray(Image.open(path).convert("L")).astype(np.float32)
    return cv2.GaussianBlur(a, (0, 0), 1.0)


def measure_line(g, cam, A, B, n=40, half=20):
    rows = []
    for k in range(n):
        t = (k + 0.5) / n
        P0 = [A[i] + (B[i] - A[i]) * t for i in range(3)]
        P1 = [A[i] + (B[i] - A[i]) * min(1, t + 0.01) for i in range(3)]
        u0, v0, d0 = project(cam, *P0)
        u1, v1, _ = project(cam, *P1)
        if d0 <= 0.1 or not (0.01 < u0 < 0.99 and 0.01 < v0 < 0.99):
            continue
        x0, y0 = to_px(u0, v0)
        x1, y1 = to_px(u1, v1)
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / L, tx / L
        s = np.arange(-half, half + 1, dtype=np.float32)
        xs, ys = (x0 + nx * s).astype(np.float32), (y0 + ny * s).astype(np.float32)
        prof = cv2.remap(g, xs.reshape(1, -1), ys.reshape(1, -1), cv2.INTER_LINEAR)[0]
        grad = np.abs(np.gradient(prof))
        i = int(np.argmax(grad))
        rows.append(dict(u=round(u0, 4), v=round(v0, 4), offset_px_3840=float(s[i]), peak=round(float(grad[i]), 2), median_grad=round(float(np.median(grad)), 2)))
    if not rows:
        return dict(in_frame=False)
    offs = np.array([r["offset_px_3840"] for r in rows])
    strong = np.array([r["peak"] > 3 * max(r["median_grad"], 0.2) for r in rows])
    o = offs[strong] if strong.any() else offs
    return dict(in_frame=True, samples=len(rows), strong_samples=int(strong.sum()), median_offset_px_1920=round(float(np.median(o)) / 2, 1),
                iqr_px_1920=[round(float(np.percentile(o, 25)) / 2, 1), round(float(np.percentile(o, 75)) / 2, 1)],
                start_uv=[rows[0]["u"], rows[0]["v"]], end_uv=[rows[-1]["u"], rows[-1]["v"]])


def load_idx(fid):
    z = np.load(os.path.join(IDX, f"{fid}.npz"))
    nm = json.load(open(os.path.join(IDX, f"{fid}-names.json")))["names"]
    return z["idx"][CY:CY + FH, CX:CX + FW], {int(k): v[0] for k, v in nm.items()}


def mask(idx, names, key):
    if key == "planter-pot":
        return idx == 35
    if key == "planter-crown":
        return idx == 60
    ids = [k for k, v in names.items() if v == key]
    return np.isin(idx, ids)


def min_dist(a, b):
    if not a.any() or not b.any():
        return None
    if (a & b).any():
        return 0.0
    dt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[a].min())


if __name__ == "__main__":
    out = {}
    ag = json.load(open(os.path.join(CL, "clay-checks-2026-11-07.json")))
    # (1) projection vs render-agent's
    agl = ag["named_lines"]["M0"]
    comp = {}
    ends = {"glazing_jamb_back_Y0.75": [(-2.30, 0.75, 0.45), (-2.30, 0.75, 2.70)], "glazing_head": [(-2.30, 0.75, 2.70), (-2.30, 2.85, 2.70)],
            "glazing_sill_line": [(-2.30, 0.75, 0.45), (-2.30, 2.85, 0.45)], "bench_front_top_edge_X-1.90": [(-1.90, 0.75, 0.45), (-1.90, 2.85, 0.45)],
            "rounded_corner_tangent_left_wall_Y0.15": [(-2.30, 0.15, 0.0), (-2.30, 0.15, 3.0)], "rounded_corner_tangent_back_wall_X-2.15": [(-2.15, 0.0, 0.0), (-2.15, 0.0, 3.0)]}
    for k, (A, B) in ends.items():
        qa = [round(project(CAM["M0"], *A)[0], 4), round(project(CAM["M0"], *A)[1], 4)]
        ra = agl.get(k, {}).get("start_uv")
        comp[k] = dict(qa_start_uv=qa, render_agent_start_uv=ra, d_u=None if ra is None else round(qa[0] - ra[0], 4), d_v=None if ra is None else round(qa[1] - ra[1], 4))
    out["projection_vs_render_agent"] = comp
    # M0p corner tangents: r 0.15 (r1) and 0.30 (1.3.2 WMC3); bench back edge X -2.30+0.40 / +0.32 (WMC4)
    out["M0p_plan_arithmetic"] = {
        "corner_tangent_window_wall_r0.15_u": round(project(CAM["M0p"], -2.30, 0.15, 1.5)[0], 4),
        "corner_tangent_window_wall_r0.30_u": round(project(CAM["M0p"], -2.30, 0.30, 1.5)[0], 4),
        "bench_back_end_front_corner_X-1.90_u": round(project(CAM["M0p"], -1.90, 0.75, 0.45)[0], 4),
        "bench_back_end_front_corner_X-1.98_u": round(project(CAM["M0p"], -1.98, 0.75, 0.45)[0], 4),
    }
    # (2) named edges on the clay
    g = gray(os.path.join(CL, "M0.png"))
    ne = {name: measure_line(g, CAM["M0"], A, B) for name, (A, B) in LINES.items()}
    out["named_edges_M0"] = ne
    # overlay
    im = cv2.cvtColor(np.asarray(Image.open(os.path.join(CL, "M0.png")).convert("RGB")), cv2.COLOR_RGB2BGR)
    for name, (A, B) in LINES.items():
        pts = []
        for k in range(60):
            t = k / 59
            P = [A[i] + (B[i] - A[i]) * t for i in range(3)]
            u, v, d = project(CAM["M0"], *P)
            if d > 0.1:
                pts.append(tuple(int(c) for c in to_px(u, v)))
        for p, q in zip(pts[:-1], pts[1:]):
            cv2.line(im, p, q, (0, 0, 255), 3)
    cv2.imwrite(os.path.join(OUT, "overlays", "clay-M0-named-edges.jpg"), cv2.resize(im, (2036, 1145)), [cv2.IMWRITE_JPEG_QUALITY, 85])
    # (3) render-agent's findings on his index passes
    idx, names = load_idx("M0")
    cur = mask(idx, names, "living/curtains")
    n, lab, st, _ = cv2.connectedComponentsWithStats(cur.astype(np.uint8))
    comps = sorted([(int(st[i, 4]), i, st[i, 0] / FW) for i in range(1, n)], reverse=True)
    back = np.zeros_like(cur)
    for px, i, u in comps:
        if 0.28 < u < 0.36:
            back |= lab == i
    pot, crown = mask(idx, names, "planter-pot"), mask(idx, names, "planter-crown")
    arm, mag = idx == 3, mask(idx, names, "living/magazine-holder")
    bas, vase = mask(idx, names, "living/basket"), mask(idx, names, "living/vase")
    f = {}
    for nm_, a, b in (("pot vs back stack", pot, back), ("crown vs back stack", crown, back), ("armchair vs magazine holder", arm, mag),
                      ("basket vs magazine holder", bas, mag), ("vase vs armchair", vase, arm)):
        dpx = min_dist(a, b)
        f[nm_] = dict(min_gap_px_3840=dpx, gap_frame_width=None if dpx is None else round(dpx / FW, 4), a_px=int(a.sum()), b_px=int(b.sum()))
    out["findings_M0_index"] = f
    out["crown_plan_arithmetic_r0.40"] = dict(x_min=round(-2.00 - 0.40, 3), through_wall_m=round(-2.30 - (-2.40), 3) * -1,
                                             y_max=round(0.47 + 0.40, 3), past_back_jamb_m=round(0.47 + 0.40 - 0.75, 3),
                                             x_min_at_y_0_75=round(-2.00 - math.sqrt(0.40 ** 2 - (0.75 - 0.47) ** 2), 4),
                                             to_glass_plane_at_y_0_75_cm=round(100 * (-2.00 - math.sqrt(0.40 ** 2 - 0.28 ** 2) + 2.30), 1))
    json.dump(out, open(os.path.join(OUT, "data", "clay-wm-r1.json"), "w"), indent=1)
    print(json.dumps(out["projection_vs_render_agent"], indent=0))
    print(json.dumps(out["M0p_plan_arithmetic"]))
    for k, v in ne.items():
        print(k, {kk: v[kk] for kk in v if kk in ("samples", "strong_samples", "median_offset_px_1920", "iqr_px_1920", "start_uv")})
    for k, v in f.items():
        print(k, v)
    print(out["crown_plan_arithmetic_r0.40"])
