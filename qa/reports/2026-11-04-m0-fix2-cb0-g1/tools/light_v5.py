"""
qa-agent 2026-11-04: grading v5 (regrade-v5-summary.json, 33 rows, + CB-0 b1r3) against Bible 1.8.4, measured by QA on the
graded files independently of the summary. Same reading as 11-03 / 11-04 (patch 1 % of the width, mean RGB -> HSL L / H,
CIELAB L* / C*), at the agent's reference point; plus the window wall at the agent's point, black point (0.5 % window
means), roll-off (max L, RGB 255), and the 1.8.4 additions:
  corridor  CIELAB L* 72-75 at C0 (0.8578, 0.3695) and S1' (0.755, 0.3612), the points render-agent verified on the clay
            (QA re-reads the clay and checks the render point is clean wall: gradient within 64 px)
  hall      H0's hall walls CIELAB L* 75-78 at QA's hall point (0.681, 0.12) and a second hall-wall point
  vista     the view at the corridor's end the brightest surface: p95 of the vista box vs p99.5 of the rest (the agent's rule:
            the ceiling band v < 0.12 and emitters L* >= 97 left out), and the living back wall in the vista at target (1)
  CB-0 b1r3 at the v5 point (0.419, 0.174) and at B1's reference point carried into CB-0 by the 22 deg rotation
Writes data/light-v5.json and overlays/points-<frame>.jpg. Usage: ~/.venvs/motion/bin/python -I light_v5.py
"""
import colorsys
import json
import math
import os

import cv2
import numpy as np

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1")
SUM = json.load(open(os.path.join(REPO, "assets/renders/house-nordic-v7-2026-11-02/regrade-v5-summary.json")))
CLAY4 = os.path.join(REPO, "assets/blockout/house/framing/round4")
BATH = (86.0, 90.0)
LIT = (90.0, 94.0)


def rgb(p):
    a = cv2.imread(os.path.join(REPO, p), cv2.IMREAD_UNCHANGED)
    if a.dtype == np.uint16:
        a = a.astype(np.float32) / 65535.0
    else:
        a = a.astype(np.float32) / 255.0
    return cv2.cvtColor(a[..., :3], cv2.COLOR_BGR2RGB)


def patch(a, u, v, w=0.01):
    H, W = a.shape[:2]
    hw = max(2, int(w * W / 2))
    x, y = int(u * W), int(v * H)
    return a[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


def read(a, u, v):
    p = patch(a, u, v)
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in p])
    lab = cv2.cvtColor(p.reshape(1, 1, 3).astype(np.float32), cv2.COLOR_RGB2LAB)[0, 0]
    return dict(uv=[round(u, 4), round(v, 4)], L=round(l * 100, 1), H=round(h * 360, 1), S=round(s * 100, 1), Lstar=round(float(lab[0]), 2),
                C=round(float(np.hypot(lab[1], lab[2])), 2))


def Lmap(a):
    return (a.max(2) + a.min(2)) / 2 * 100


def Lstar_map(a):
    return cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2LAB)[..., 0]


def black_point(a):
    from numpy.lib.stride_tricks import sliding_window_view
    k = max(4, int(0.005 * a.shape[1]))
    pm = sliding_window_view(Lmap(a), (k, k))[::4, ::4].mean((2, 3))
    return round(float(pm.min()), 1)


def edge_near(a, u, v, r=64):
    g = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    H, W = g.shape
    x, y = int(u * W), int(v * H)
    sub = g[max(0, y - r):y + r, max(0, x - r):x + r]
    gm = np.hypot(cv2.Sobel(sub, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(sub, cv2.CV_32F, 0, 1, ksize=3))
    return round(float(np.percentile(gm, 99.5)), 1)


def vista(a, box):
    Ls = Lstar_map(a)
    H, W = Ls.shape
    u0, u1, v0, v1 = box
    m = np.zeros_like(Ls, bool)
    m[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)] = True
    rest = (~m)
    rest[:int(0.12 * H)] = False
    vals = Ls[rest]
    vals = vals[vals < 97]
    vb = Ls[m]
    Lh = Lmap(a)[m]
    return dict(box=box, vista_Lstar_p95=round(float(np.percentile(vb, 95)), 2), vista_L_HSL_p50=round(float(np.percentile(Lh, 50)), 1),
                vista_L_HSL_p95=round(float(np.percentile(Lh, 95)), 1), rest_Lstar_p99_5=round(float(np.percentile(vals, 99.5)), 2),
                brightest=bool(np.percentile(vb, 95) > np.percentile(vals, 99.5)))


def mark(a, pts, path):
    im = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    H, W = im.shape[:2]
    for lab_, (u, v) in pts:
        x, y = int(u * W), int(v * H)
        cv2.circle(im, (x, y), int(0.005 * W) + 2, (0, 0, 255), 3)
        cv2.putText(im, lab_, (x + 18, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
    im = cv2.resize(im, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(path, im, [cv2.IMWRITE_JPEG_QUALITY, 85])


def b1_to_cb0(u, v, W=2736, H=1539):
    s = W / 4072
    fx = 0.6667 * 3840 * s
    cx_b, cx_c, cy = 116 * s + 0.52 * 3840 * s, 116 * s + 0.50 * 3840 * s, 65 * s + 0.46 * 2160 * s
    X, Y = (u * W - cx_b) / fx, (v * H - cy) / fx
    t = math.radians(22)
    Xc, Zc = X * math.cos(t) + math.sin(t), -X * math.sin(t) + math.cos(t)
    return round((cx_c + Xc / Zc * fx) / W, 4), round((cy + Y / Zc * fx) / H, 4)


if __name__ == "__main__":
    rows = []
    for r in SUM["rows"]:
        a = rgb(r["outputs"]["graded"])
        u, v = r["reference_uv"]
        ref = read(a, u, v)
        rec = dict(id=r["id"], frame=r["frame"], fix=r["fix"], graded=r["outputs"]["graded"], inherits=r["inherits"], agent=dict(
            measured=r["measured"], scale=r["scale"], range=r["range"], H=r["H"], C=r["C_star"], judged=r["wall_judged"], ww=(r["window_wall"] or {}).get("L"),
            black=r["black"], max=r["frame_max"], px255=r["px255"], fails=r["fails"], meets=r["meets_bible_1_8_4"]), ref=ref)
        corridor = r["scale"].startswith("CIELAB")
        val = ref["Lstar"] if corridor else ref["L"]
        rec["qa_minus_agent"] = round(val - r["measured"], 2)
        lo, hi = r["range"]
        rec["checks"] = dict(target=bool(lo <= val <= hi))
        if r["wall_judged"]:
            rec["checks"]["hue_32_40"] = bool(32 <= ref["H"] <= 40)
            rec["checks"]["C_le_7"] = bool(ref["C"] <= 7.0)
        if r["window_wall"]:
            pt = r["window_wall"]["point"]
            import re
            m = re.search(r"\(([\d.]+),\s*([\d.]+)\)", pt)
            wu, wv = float(m.group(1)), float(m.group(2))
            rec["window_wall"] = read(a, wu, wv)
            rec["checks"]["window_wall_80_88"] = bool(80 <= rec["window_wall"]["L"] <= 88)
        Lm = Lmap(a)
        rec["black"] = black_point(a)
        rec["max_L"] = round(float(Lm.max()), 1)
        rec["px255"] = int((a.max(2) >= 254.5 / 255).sum())
        rec["checks"]["black_12_15"] = bool(12 <= rec["black"] <= 15)
        rec["checks"]["rolloff"] = bool(rec["max_L"] <= 97.0 and rec["px255"] == 0)
        if corridor:
            rec["edge_p99_5_within_64px"] = edge_near(a, u, v)
            key = "C0" if r["frame"] == "C0" else "S1prime"
            cp = os.path.join(CLAY4, "C0.png" if key == "C0" else "poses/S1prime.png")
            ca = rgb(os.path.relpath(cp, REPO))
            rec["clay_at_point"] = read(ca, u, v)
            rec["clay_edge_p99_5_within_64px"] = edge_near(ca, u, v)
            box = r["v5"]["vista"]["box_uv"]
            rec["vista"] = vista(a, box)
            rec["checks"]["vista_brightest"] = rec["vista"]["brightest"]
            mark(a, [("wall pt", (u, v)), ("vista", ((box[0] + box[1]) / 2, (box[2] + box[3]) / 2))], os.path.join(OUT, "overlays", f"points-{r['frame']}.jpg"))
        if r["frame"] == "H0":
            hall = read(a, 0.681, 0.12)
            hall2 = read(a, 0.62, 0.30)
            rec["hall"] = dict(qa_point=hall, second_point=hall2, agent_Lstar=r["v5"]["hall_wall_Lstar"]["L_star"])
            rec["checks"]["hall_Lstar_75_78"] = bool(75 <= hall["Lstar"] <= 78)
            vis = read(a, 0.35, 0.40)
            Yv = float(np.mean(np.where(patch(a, 0.35, 0.40) <= 0.04045, patch(a, 0.35, 0.40) / 12.92, ((patch(a, 0.35, 0.40) + 0.055) / 1.055) ** 2.4) @ [0.2126, 0.7152, 0.0722]))
            ph = patch(a, 0.681, 0.12)
            Yh = float(np.mean(np.where(ph <= 0.04045, ph / 12.92, ((ph + 0.055) / 1.055) ** 2.4) @ [0.2126, 0.7152, 0.0722]))
            rec["B5"] = dict(vista=vis, stops_hall_under_vista=round(math.log2(Yv / Yh), 3), ok=bool(0.47 <= math.log2(Yv / Yh) <= 0.87))
            rec["checks"]["B5"] = rec["B5"]["ok"]
            box = r["v5"]["vista"]["box_uv"]
            rec["vista"] = vista(a, box)
            rec["checks"]["vista_brightest"] = rec["vista"]["brightest"]
            mark(a, [("hall", (0.681, 0.12)), ("hall2", (0.62, 0.30)), ("vista", (0.35, 0.40))], os.path.join(OUT, "overlays", "points-H0.jpg"))
        if r["id"] == "m0-v8b-r2":
            rec["bible_points"] = {"back wall by the corner (0.427,0.416)": read(a, 0.4269, 0.4156), "window wall (0.352,0.415)": read(a, 0.352, 0.415)}
            mark(a, [("back", (0.4269, 0.4156)), ("ww", (0.352, 0.415))], os.path.join(OUT, "overlays", "points-M0_1.2_fix.jpg"))
        fails = [k for k, ok in rec["checks"].items() if ok is False]
        if not r["wall_judged"]:
            fails.append("not judged (no wall at the point)")
        rec["qa_fails"] = fails
        rec["qa_pass"] = (not fails)
        rows.append(rec)
    # CB-0 b1r3 (not in the 33)
    a = rgb("assets/renders/poses/nordic/v7/pose-cb-0-v7-graded-b1r3-v5.png")
    mp = b1_to_cb0(0.419, 0.174)
    cb = dict(id="pose-cb-0-v7-b1r3", frame="CB-0", fix="b1r3", graded="assets/renders/poses/nordic/v7/pose-cb-0-v7-graded-b1r3-v5.png",
              agent=dict(reading=79.3, meets=True, stops_from="b1-v7-r3 fix2 (0.163)"),
              v5_point=read(a, 0.419, 0.174), b1_point_carried=dict(uv=mp, **{k: v for k, v in read(a, *mp).items() if k != "uv"}),
              b1_fix2_at_its_point=read(rgb("assets/renders/bath/nordic/v7/b1-v7-r3-graded-fix2-v5.png"), 0.419, 0.174),
              old_cb0_v5_at_v5_point=read(rgb("assets/renders/poses/nordic/v7/pose-cb-0-v7-graded-v5.png"), 0.419, 0.174),
              black=black_point(a), max_L=round(float(Lmap(a).max()), 1), px255=int((a.max(2) >= 254.5 / 255).sum()))
    ref = cb["b1_point_carried"]
    cb["checks"] = dict(target=bool(BATH[0] <= ref["L"] <= BATH[1]), hue_32_40=bool(32 <= ref["H"] <= 40), C_le_7=bool(ref["C"] <= 7), black_12_15=bool(12 <= cb["black"] <= 15),
                        rolloff=bool(cb["max_L"] <= 97 and cb["px255"] == 0), v5_point_in_86_90=bool(BATH[0] <= cb["v5_point"]["L"] <= BATH[1]))
    mark(a, [("v5 pt", (0.419, 0.174)), ("B1 pt", mp)], os.path.join(OUT, "overlays", "points-CB-0_b1r3.jpg"))
    out = dict(rows=rows, cb0_b1r3=cb, counts=dict(qa_pass=sum(r["qa_pass"] for r in rows), agent_pass=sum(bool(r["agent"]["meets"]) for r in rows),
                                                   disagree=[r["id"] + (" " + r["fix"] if r["fix"] else "") for r in rows if r["qa_pass"] != bool(r["agent"]["meets"])]))
    json.dump(out, open(os.path.join(OUT, "data", "light-v5.json"), "w"), indent=1)
    for r in rows:
        ref = r["ref"]
        print(f"{r['id'][:22]:22s} {str(r['fix'] or ''):5s} ref L {ref['L']:5.1f} L* {ref['Lstar']:5.1f} H {ref['H']:5.1f} C* {ref['C']:5.2f} (agent {r['agent']['measured']}, d {r['qa_minus_agent']:+.2f}) "
              f"ww {r.get('window_wall', {}).get('L')} black {r['black']} max {r['max_L']} 255 {r['px255']} | QA {'PASS' if r['qa_pass'] else 'fail ' + ','.join(r['qa_fails'])} | agent {'PASS' if r['agent']['meets'] else 'fail ' + ','.join(r['agent']['fails'])}")
        for k in ("vista", "hall", "B5", "clay_at_point", "bible_points"):
            if k in r:
                print("     ", k, json.dumps(r[k])[:400])
        if "edge_p99_5_within_64px" in r:
            print("      edges render / clay", r["edge_p99_5_within_64px"], r["clay_edge_p99_5_within_64px"])
    print("CB-0 b1r3", json.dumps(cb)[:1500])
    print(out["counts"])
