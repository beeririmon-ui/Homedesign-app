"""
Exposure and light against Bible 1.8 on every graded-v3 still (the 26 rows of regrade-v3-summary.json and the 4 retakes),
measured by QA independently of process_v8.py / regrade-v3-summary.json:
  B1  two targets: the lit wall by the window (back wall by the corner) L 90-94 (bath 1.6: 86-90; hall B5: 2/3 stop under the
      living vista; corridor: G1.8 proposal, no Bible number), and the window wall L 80-88 where it is in frame.
  B2  black point: the darkest 0.5 %-wide patch L 12-15.
  B3  roll-off from L 94: window / frame p99 <= 97, no 255 channel; the highlight ceiling.
  B4  near-white chroma: CIELAB C* of the reference wall patch (warm white: working value <= 7) and of the near-white
      population (HSL L > 80): median and p95; HSL hue 32-40 on the wall.
  B5  H0: the living vista through the door is the brightest; the hall wall 2/3 stop under it (0.47-0.87).
Patches are sampled where the render-agent sampled (its `bible_v3.reference_point` from the measurements-v3 record, in the
coordinates of the graded file = the canvas for overscan stills) so its number can be confirmed, and at QA's own points: the
clay selfcheck wall patches (post.reference_uv, hero_wall_mid, wall_beside_window), the Bible points of M0, and a window-wall
point per frame where a window wall is in frame. HSL as the Bible defines it (L = (max+min)/2).
Writes data/light-<id>.json and overlays/points-<id>.jpg (the sampled points drawn on the still).
"""
import colorsys
import json
import os
import sys

import cv2
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SUMMARY = json.load(open(os.path.join(C.REPO, "assets/renders/house-nordic-v7-2026-11-02/regrade-v3-summary.json")))
AGENT_ROWS = {}
for r in SUMMARY["rows"]:
    AGENT_ROWS[(r["id"], bool(r["fix"]))] = r

# QA's Bible 1.8 targets per frame: (lo, hi, source, binding)
TARGET = {
    "living":  (90.0, 94.0, "Bible 1.8 B1 (1): back wall by the corner L 90-94 (1.4; 92-95 was 1.0)", True),
    "kitchen-dining": (90.0, 94.0, "Bible 'אור' 1.4 / 1.8 B1 (1): the lit wall by the window L 90-94", True),
    "master":  (90.0, 94.0, "Bible 1.8 B1 (1)", True),
    "boy":     (90.0, 94.0, "Bible 1.8 B1 (1)", True),
    "girl":    (90.0, 94.0, "Bible 1.8 B1 (1)", True),
    "work":    (90.0, 94.0, "Bible 1.8 B1 (1)", True),
    "bath":    (86.0, 90.0, "Bible 1.6 bath: the wall beside the fluted window L 86-90 (4000 K); 1.8 keeps the room exception", True),
    "hall":    (None, None, "Bible 1.8 B5: the hall walls 2/3 stop under the living back wall; the vista the brightest", True),
    "corridor": (71.2, 80.6, "G1.8 PROPOSAL (gates doc): corridor walls 2/3 stop under the living; no Bible number", False),
}
WINDOW_WALL = (80.0, 88.0)
# QA window-wall points (coordinates of the graded file): the wall that holds the window, beside it
WW_POINT = {"M0": (0.10, 0.30), "K-boy": (0.275, 0.30), "K-girl": (0.275, 0.30), "K-boy fix": (0.275, 0.30), "K-girl fix": (0.275, 0.30),
            "W0": (0.21, 0.30), "W0 fix": (0.21, 0.30), "MB0": (0.17, 0.30), "D1": (0.20, 0.33)}
M0_PTS = {"bible corner (0.467,0.385) [90-94]": (0.467, 0.385), "behind the sofa (0.69,0.22) [88-91]": (0.69, 0.22), "right edge (0.97,0.31) [82-86]": (0.97, 0.31)}
H0_VISTA, H0_HALL = (0.35, 0.40), (0.681, 0.12)


def Lmap(a):
    return (a.max(2) + a.min(2)) / 2 * 100


def hsl(rgb):
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in rgb])
    return [round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)]


def lab_C(rgb):
    px = np.array(rgb, np.float32).reshape(1, 1, 3)
    lab = cv2.cvtColor(px, cv2.COLOR_RGB2LAB)[0, 0]
    return round(float(np.hypot(lab[1], lab[2])), 2), round(float(lab[0]), 1)


def s2l(x):
    x = np.asarray(x, float)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def Y(rgb):
    return float(s2l(rgb).dot(np.array([0.2126, 0.7152, 0.0722])))


def patch(a, u, v, w=0.01):
    Hh, Ww = a.shape[:2]
    hw = max(2, int(w * Ww / 2))
    x, y = int(u * Ww), int(v * Hh)
    return a[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


def box_px(a, b):
    Hh, Ww = a.shape[:2]
    u0, u1, v0, v1 = b
    return a[max(0, int(v0 * Hh)):min(Hh, int(v1 * Hh)), max(0, int(u0 * Ww)):min(Ww, int(u1 * Ww))]


def reading(a, raw, u, v, label, lo=None, hi=None):
    p = patch(a, u, v)
    out = dict(label=label, uv=[round(u, 4), round(v, 4)], graded_HSL=hsl(p))
    out["lab_C"], out["lab_L"] = lab_C(p)
    if raw is not None:
        pr_ = patch(raw, u, v)
        out["raw_HSL"] = hsl(pr_)
        out["stops_raw_to_graded"] = round(float(np.log2(max(Y(p), 1e-6) / max(Y(pr_), 1e-6))), 3)
    if lo is not None:
        out["range"] = [lo, hi]
        out["in_range"] = bool(lo <= out["graded_HSL"][2] <= hi)
    return out


def run(sid):
    d = C.load(sid)
    canvas = d.get("graded_canvas") if d["ovs"] else d["graded"]      # the file the agent graded and sampled
    frame = d["graded"]
    raw_canvas = None
    if d["raw"] is not None:
        raw_canvas = C.rgb(os.path.join(C.REPO, d["raw_file"])) if d["ovs"] else d["raw"]
    sc = d["sc"]
    room, base = d["room"], d["base"]
    lo, hi, src, binding = TARGET[room]
    rep = dict(frame=sid, kind=d["kind"], room=room, graded=d["graded_file"], sampled_on="canvas (overscan)" if d["ovs"] else "frame")
    pts = []
    # 1. the agent's point, re-read by QA
    am = C.agent_measurements(sid)
    agent = None
    if am and am.get("bible_v3"):
        b = am["bible_v3"]
        u, v = b["reference_point"]
        agent = dict(point=[u, v], source=b.get("reference_source"), target_L=b.get("target_L"), range=b.get("range"), measured_L=b.get("measured_L"),
                     meets_target=b.get("meets_target"), meets_bible=b.get("meets_bible"), judged_by=b.get("judged_by"),
                     applied_stops=am.get("grade", {}).get("exposure", {}).get("applied_stops"), needed_stops=am.get("grade", {}).get("exposure", {}).get("needed_stops"))
        pts.append(reading(canvas, raw_canvas, u, v, "agent reference point", lo, hi))
        pts[-1]["agent_measured_L"] = b.get("measured_L")
        pts[-1]["qa_minus_agent_L"] = round(pts[-1]["graded_HSL"][2] - b["measured_L"], 1) if b.get("measured_L") is not None else None
    rep["agent"] = agent
    # 2. QA's own points: the clay wall patches
    wp = sc.get("wall_patches", {})
    for k in ("reference_" + {"living": "M0", "kitchen-dining": "PD", "hall": "H0", "corridor": "C0", "master": "MB0", "boy": "Kb", "girl": "Kg", "bath": "CB", "work": "W0"}[room],
              "hero_wall_mid", "wall_beside_window"):
        v_ = wp.get(k)
        if v_ and "u" in v_ and "L_hsl" in v_ and 0 <= v_["u"] <= 1 and 0 <= v_["v"] <= 1:
            r = reading(canvas, raw_canvas, v_["u"], v_["v"], f"clay {k} (clay L {v_['L_hsl']})", lo, hi)
            pts.append(r)
    ref_uv = sc.get("post", {}).get("reference_uv")
    if ref_uv and not any(p["uv"] == [round(ref_uv[0], 4), round(ref_uv[1], 4)] for p in pts):
        pts.append(reading(canvas, raw_canvas, ref_uv[0], ref_uv[1], "clay post.reference_uv", lo, hi))
    if base == "M0" and d["frame"] == "M0":
        for k, (u, v) in M0_PTS.items():
            pts.append(reading(canvas, raw_canvas, u, v, "Bible M0 " + k))
        pts[-3]["range"], pts[-3]["in_range"] = [90.0, 94.0], bool(90 <= pts[-3]["graded_HSL"][2] <= 94)
        pts[-2]["range"], pts[-2]["in_range"] = [88.0, 91.0], bool(88 <= pts[-2]["graded_HSL"][2] <= 91)
        pts[-1]["range"], pts[-1]["in_range"] = [82.0, 86.0], bool(82 <= pts[-1]["graded_HSL"][2] <= 86)
    if sid in WW_POINT:
        u, v = WW_POINT[sid]
        r = reading(canvas, raw_canvas, u, v, "QA window wall (Bible 1.8 B1 (2): 80-88)", *WINDOW_WALL)
        pts.append(r)
        rep["window_wall"] = r
    if d["frame"] == "H0":
        vis = reading(canvas, raw_canvas, *H0_VISTA, "living vista through the door (B5: the brightest; living back wall 90-94)")
        hall = reading(canvas, raw_canvas, *H0_HALL, "hall wall over the console (B5: 2/3 stop under the vista)")
        st = round(float(np.log2(max(Y(patch(canvas, *H0_VISTA)), 1e-6) / max(Y(patch(canvas, *H0_HALL)), 1e-6))), 3)
        rep["B5"] = dict(vista=vis, hall=hall, stops_hall_under_vista=st, ok=bool(0.47 <= st <= 0.87), vista_L_in_90_94=bool(90 <= vis["graded_HSL"][2] <= 94))
        pts += [vis, hall]
    rep["points"] = pts
    # the verdict point for B1 (1): the agent's point when it is a wall reading with its own target; else the clay reference patch
    ref = None
    for p in pts:
        if p["label"].startswith("agent") and agent and agent.get("judged_by", "").startswith("own"):
            ref = p
            break
    if ref is None:
        for p in pts:
            if p["label"].startswith("clay reference_") or p["label"].startswith("clay post"):
                ref = p
                break
    rep["reference"] = ref
    rep["target"] = dict(lo=lo, hi=hi, source=src, binding=binding)
    if ref is not None and lo is not None:
        rep["B1_lit_wall_ok"] = bool(lo <= ref["graded_HSL"][2] <= hi)
        rep["wall_H_32_40"] = bool(32 <= ref["graded_HSL"][0] <= 40)
        rep["wall_labC_le_7"] = bool(ref["lab_C"] <= 7.0)
    # 3. frame statistics (what the viewer sees: the 16:9 frame)
    L = Lmap(frame)
    Hh, Ww = frame.shape[:2]
    sat = frame.max(2) >= 254.5 / 255
    k = max(4, int(0.005 * Ww))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    rep["black_point_L"] = round(float(pm.min()), 1)
    rep["black_point_ok_12_15"] = bool(12.0 <= pm.min() <= 15.0)
    rep["frame_L_p99"] = round(float(np.percentile(L, 99)), 1)
    rep["frame_L_max"] = round(float(L.max()), 1)
    rep["px_255"] = int(sat.sum())
    rep["share_L_over_94"] = round(float((L > 94).mean()), 4)
    # canvas statistics too (the agent's numbers are on the canvas)
    if d["ovs"]:
        Lc = Lmap(canvas)
        rep["canvas_L_p99"], rep["canvas_L_max"], rep["canvas_px_255"] = round(float(np.percentile(Lc, 99)), 1), round(float(Lc.max()), 1), int((canvas.max(2) >= 254.5 / 255).sum())
        pmc = sliding_window_view(Lc, (k, k))[::4, ::4].mean((2, 3))
        rep["canvas_black_point_L"] = round(float(pmc.min()), 1)
    # window / brightest area
    win = None
    for nm, (kind, b, area, vis) in C.boxes(d).items():
        if kind == "window":
            win = (nm, b)
            break
    if d["frame"] == "M0":
        win = ("window (pilot box)", (0.19, 0.375, 0.025, 0.553))
    if d["frame"] == "H0":
        win = ("living vista through the door (process box)", (0.26, 0.44, 0.05, 0.95))
    if win:
        wl = box_px(L, win[1])
        mask = np.zeros_like(L, bool)
        u0, u1, v0, v1 = win[1]
        mask[max(0, int(v0 * Hh)):min(Hh, int(v1 * Hh)), max(0, int(u0 * Ww)):min(Ww, int(u1 * Ww))] = True
        rep["window"] = dict(box=win[0], L_p50=round(float(np.median(wl)), 1), L_p99=round(float(np.percentile(wl, 99)), 1), L_max=round(float(wl.max()), 1),
                             outside_L_p999=round(float(np.percentile(L[~mask], 99.9)), 1), brightest=bool(np.percentile(wl, 99) >= np.percentile(L[~mask], 99.9)),
                             p99_le_97=bool(np.percentile(wl, 99) <= 97.0))
    else:
        rep["window"] = dict(box=None, note="no window box in this frame (allowed in a room's second frame / inner poses)")
    rep["rolloff_ok"] = bool(rep["frame_L_p99"] <= 97.0 and rep["frame_L_max"] <= 97.0 and rep["px_255"] == 0)
    # B4: near-white population chroma (Lab) on the frame
    sub = frame[::5, ::5].reshape(-1, 3)
    Ls = (sub.max(1) + sub.min(1)) / 2 * 100
    nw = sub[Ls > 80]
    if len(nw):
        lab = cv2.cvtColor(nw.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2LAB).reshape(-1, 3)
        Cc = np.hypot(lab[:, 1], lab[:, 2])
        rep["near_white_B4"] = dict(share_of_frame=round(float(len(nw) / len(sub)), 3), C_median=round(float(np.median(Cc)), 2), C_p95=round(float(np.percentile(Cc, 95)), 2),
                                    share_C_over_7=round(float((Cc > 7).mean()), 3), share_C_over_14=round(float((Cc > 14).mean()), 3))
    # the agent's summary row for this still
    aid = C.AGENT_ID[sid]
    arow = AGENT_ROWS.get((aid, d["kind"] == "fix"))
    if arow:
        rep["agent_row"] = dict(target_L=arow["target_L"], range=arow["range"], measured_L=arow["measured_L"], meets_target=arow["meets_target"], meets_bible=arow["meets_bible"],
                                stops_v3=arow["stops_v3"], black=arow["black"], window_p99=arow["window_p99"], frame_max=arow["frame_max"], px255=arow["px255"],
                                window_wall=arow.get("window_wall"), hall_B5=arow.get("hall_B5"), reference=arow["reference"])
    # overlay with the points
    im = (C.pr.to8(C.pr.fit(canvas, 1920, int(round(1920 * canvas.shape[0] / canvas.shape[1]))))).copy()
    im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
    for i, p in enumerate(pts):
        x, y = int(p["uv"][0] * im.shape[1]), int(p["uv"][1] * im.shape[0])
        col = (0, 0, 255) if p["label"].startswith("agent") else ((255, 0, 0) if "window wall" in p["label"] else (0, 160, 0))
        cv2.rectangle(im, (x - 10, y - 10), (x + 10, y + 10), col, 2)
        cv2.putText(im, f"{i}: L {p['graded_HSL'][2]}", (x + 14, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
    cv2.putText(im, f"{sid}  (red = agent point, green = clay / QA points, blue = window wall)", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(C.OUT, "overlays", f"points-{C.fn(sid)}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 80])
    json.dump(rep, open(os.path.join(C.OUT, "data", f"light-{C.fn(sid)}.json"), "w"), indent=1, ensure_ascii=False)
    r = rep.get("reference") or {}
    ww = rep.get("window_wall")
    print(f"{sid:12s} ref L {r.get('graded_HSL', [None, None, None])[2]} H {r.get('graded_HSL', [None])[0]} C* {r.get('lab_C')} [{lo}-{hi}] ok {rep.get('B1_lit_wall_ok')} "
          f"| agent {agent['measured_L'] if agent else None} (QA-agent {pts[0].get('qa_minus_agent_L') if agent else None}) | ww {ww['graded_HSL'][2] if ww else '-'} "
          f"| black {rep['black_point_L']} | p99 {rep['frame_L_p99']} max {rep['frame_L_max']} 255 {rep['px_255']} | win p99 {rep['window'].get('L_p99')} brightest {rep['window'].get('brightest')} "
          f"| B4 C med {rep.get('near_white_B4', {}).get('C_median')} p95 {rep.get('near_white_B4', {}).get('C_p95')}" + (f" | B5 {rep['B5']['stops_hall_under_vista']} ok {rep['B5']['ok']}" if 'B5' in rep else ""))
    return rep


if __name__ == "__main__":
    for f in (sys.argv[1:] or (C.RETAKES + C.V3_ROWS)):
        run(f)
