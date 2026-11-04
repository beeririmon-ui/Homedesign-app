"""
Grading v4 against Bible 1.8.3 (light chapters unchanged since 1.8: B1 two targets, B2 black, B3 roll-off, B4 C* absolute, B5),
measured by QA on the 30 graded-v4 stills, independently of regrade-v4-summary.json, with the same points as on 11-03 (the
agent's point re-read, the clay wall patches, the Bible points of M0, QA's window-wall points) plus:
  halo check   for every frame the masked wall-hue correction ran on: the wall pixels (L* > 80, C* < 18) in a 14 px ring just
               inside each protected box (product boxes and the upholstered furniture: left uncorrected, feathered) against a
               14 px ring 30-44 px outside it (corrected): median CIELAB hue h_ab and C*; the same rings on the v3 still as the
               baseline. A visible halo = a hue step >= 5 deg or a C* step >= 1.5 that the v3 still does not have.
  C0 / S1'     frame statistics and the living vista through the portal (G1.14: the same rooms at the two ends of the V6 rail).
Writes data/light-<id>.json, data/halos.json, data/c0-s1.json and overlays/halo-<id>.jpg.
"""
import importlib.util
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

_s = importlib.util.spec_from_file_location("qa1103_light_src", os.path.join(C.REPO, "qa/reports/2026-11-03-retakes-g1/tools/light.py"))
_src = open(_s.origin).read()
# re-use the 11-03 helpers (Lmap, hsl, lab_C, Y, patch, box_px, reading, TARGET, WW_POINT, M0_PTS, H0 points) without running its main
_ns = {"__name__": "qa1103_light", "__file__": _s.origin}
_sys_path0 = list(sys.path)
exec(compile(_src.split("\nSUMMARY = json.load")[0], _s.origin, "exec"), _ns)          # imports + docstring
exec(compile("\nTARGET =" + _src.split("\nTARGET =")[1].split("\ndef run(")[0], _s.origin, "exec"), _ns)
L1 = type("L1", (), _ns)
SUMMARY = json.load(open(os.path.join(C.REPO, "assets/renders/house-nordic-v7-2026-11-02/regrade-v4-summary.json")))
AGENT_ROWS = {(r["id"], bool(r["fix"])): r for r in SUMMARY["rows"]}
WW_POINT = dict(L1.WW_POINT)
CORRECTED = {"M0", "D1", "H0", "MB0", "M0p", "M0x", "MB-in", "C0"}
NEW_FIX_KIND = {"B1 r3 fix", "B2 r3 fix", "K-girl-0 r2 fix", "W0-in r2 fix"}


def lab_img(a):
    return cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2LAB)


def ring_stats(lab, mask):
    Ls, a_, b_ = lab[..., 0][mask], lab[..., 1][mask], lab[..., 2][mask]
    Cc = np.hypot(a_, b_)
    sel = (Ls > 80) & (Cc < 18)
    if sel.sum() < 150:
        return None
    return dict(n=int(sel.sum()), h_ab=round(float(np.degrees(np.arctan2(np.median(b_[sel]), np.median(a_[sel])))), 1), C=round(float(np.median(Cc[sel])), 2),
                L=round(float(np.median(Ls[sel])), 1))


def halos(sid, d):
    """hue / chroma step at the protected boxes, v4 against v3."""
    g4 = d["graded"]
    v3 = C.C3.STILLS.get(sid)
    f3 = C.rgb(os.path.join(C.REPO, d["graded_file"].replace("-graded-v4.png", "-graded-v3.png")))
    g3 = C.crop_canvas(f3) if d["ovs"] else f3
    H, W = g4.shape[:2]
    l4, l3 = lab_img(g4), lab_img(g3)
    boxes = [(nm, b) for nm, (kind, b, area, vis) in C.boxes(d).items() if kind in ("proxy", "proxy-transit") or any(w in nm.lower() for w in ("sofa", "armchair", "bed"))]
    out, worst = [], None
    for nm, (u0, u1, v0, v1) in boxes:
        x0, x1, y0, y1 = int(u0 * W), int(u1 * W), int(v0 * H), int(v1 * H)
        if x1 - x0 < 30 or y1 - y0 < 30:
            continue
        box = np.zeros((H, W), bool)
        box[max(0, y0):y1, max(0, x0):x1] = True
        er = cv2.erode(box.astype(np.uint8), np.ones((29, 29), np.uint8)).astype(bool)
        inner = box & ~er
        o1 = cv2.dilate(box.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
        o2 = cv2.dilate(box.astype(np.uint8), np.ones((89, 89), np.uint8)).astype(bool)
        outer = o2 & ~o1
        si4, so4, si3, so3 = ring_stats(l4, inner), ring_stats(l4, outer), ring_stats(l3, inner), ring_stats(l3, outer)
        if not (si4 and so4 and si3 and so3):
            continue
        dh4, dC4 = abs(si4["h_ab"] - so4["h_ab"]), abs(si4["C"] - so4["C"])
        dh3, dC3 = abs(si3["h_ab"] - so3["h_ab"]), abs(si3["C"] - so3["C"])
        rec = dict(box=nm, inside_v4=si4, outside_v4=so4, step_v4=dict(dh=round(dh4, 1), dC=round(dC4, 2)), step_v3=dict(dh=round(dh3, 1), dC=round(dC3, 2)),
                   halo=bool((dh4 >= 5 and dh4 - dh3 >= 3) or (dC4 >= 1.5 and dC4 - dC3 >= 1.0)))
        out.append(rec)
        if worst is None or dh4 + 3 * dC4 > worst[0]:
            worst = (dh4 + 3 * dC4, nm, (x0, x1, y0, y1))
    if worst:
        x0, x1, y0, y1 = worst[2]
        X0, X1, Y0, Y1 = max(0, x0 - 120), min(W, x1 + 120), max(0, y0 - 120), min(H, y1 + 120)
        im = np.concatenate([(g3[Y0:Y1, X0:X1] * 255).astype(np.uint8), np.full((Y1 - Y0, 8, 3), 255, np.uint8), (g4[Y0:Y1, X0:X1] * 255).astype(np.uint8)], axis=1)
        im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        cv2.putText(im, f"{sid}: v3 (left) / v4 (right) around '{worst[1]}'", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        cv2.imwrite(os.path.join(C.OUT, "overlays", f"halo-{C.fn(sid)}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return out


def run(sid):
    d = C.load(sid, raw=False)
    canvas = d.get("graded_canvas") if d["ovs"] else d["graded"]
    frame = d["graded"]
    sc = d["sc"]
    room, base = d["room"], d["base"]
    lo, hi, src, binding = L1.TARGET[room]
    rep = dict(frame=sid, room=room, graded=d["graded_file"])
    pts = []
    am = C.agent_measurements_v4(sid)
    agent = None
    if am and am.get("bible_v3"):
        b = am["bible_v3"]
        u, v = b["reference_point"]
        agent = dict(point=[u, v], source=b.get("reference_source"), target_L=b.get("target_L"), range=b.get("range"), measured_L=b.get("measured_L"), judged_by=b.get("judged_by"),
                     meets_target=b.get("meets_target"), meets_bible=b.get("meets_bible"), wall_v4=b.get("wall_v4"), window_wall=b.get("window_wall"),
                     applied_stops=am["grade"]["exposure"].get("applied_stops"), hue_correction=(am["grade"].get("wall_hue_v4") or {}).get("applied"))
        pts.append(L1.reading(canvas, None, u, v, "agent reference point", lo, hi))
        pts[-1]["qa_minus_agent_L"] = round(pts[-1]["graded_HSL"][2] - b["measured_L"], 1) if b.get("measured_L") is not None else None
    rep["agent"] = agent
    wp = sc.get("wall_patches", {})
    refkey = "reference_" + {"living": "M0", "kitchen-dining": "PD", "hall": "H0", "corridor": "C0", "master": "MB0", "boy": "Kb", "girl": "Kg", "bath": "CB", "work": "W0"}[room]
    for k in (refkey, "hero_wall_mid", "wall_beside_window"):
        v_ = wp.get(k)
        if v_ and "u" in v_ and "L_hsl" in v_ and 0 <= v_["u"] <= 1 and 0 <= v_["v"] <= 1:
            pts.append(L1.reading(canvas, None, v_["u"], v_["v"], f"clay {k} (clay L {v_['L_hsl']})", lo, hi))
    if d["frame"] == "M0":
        for k, (u, v) in L1.M0_PTS.items():
            r = L1.reading(canvas, None, u, v, "Bible M0 " + k)
            r["range"] = [90.0, 94.0] if "corner" in k else ([88.0, 91.0] if "sofa" in k else [82.0, 86.0])
            r["in_range"] = bool(r["range"][0] <= r["graded_HSL"][2] <= r["range"][1])
            pts.append(r)
    if sid in WW_POINT:
        u, v = WW_POINT[sid]
        rep["window_wall"] = L1.reading(canvas, None, u, v, "QA window wall (Bible 1.8 B1 (2): 80-88)", 80.0, 88.0)
        pts.append(rep["window_wall"])
    if d["frame"] == "H0":
        vis = L1.reading(canvas, None, *L1.H0_VISTA, "living vista through the door")
        hall = L1.reading(canvas, None, *L1.H0_HALL, "hall wall over the console")
        st = round(float(np.log2(max(L1.Y(L1.patch(canvas, *L1.H0_VISTA)), 1e-6) / max(L1.Y(L1.patch(canvas, *L1.H0_HALL)), 1e-6))), 3)
        rep["B5"] = dict(vista=vis, hall=hall, stops_hall_under_vista=st, ok=bool(0.47 <= st <= 0.87))
        pts += [vis, hall]
    rep["points"] = pts
    # the verdict point: the agent's own wall when it judged its own wall; else the clay reference patch
    ref = None
    if agent and (agent.get("judged_by") or "").startswith("own"):
        ref = pts[0]
    if ref is None:
        ref = next((p for p in pts if p["label"].startswith("clay reference_")), None)
    if d["frame"] == "CB-0":
        ref = pts[0]          # v4 moved CB-0's point to the white wall beside the window (B1's wall): re-read and judged
    rep["reference"] = ref
    rep["target"] = dict(lo=lo, hi=hi, source=src, binding=binding)
    # judgeability: no wall at the point (M0x, K-boy-0: default (0.5, 0.3)); B2 / B2 r3 fix: inherited stops, no Bible number at the mirror wall
    judge = not (d["frame"] in ("M0x", "K-boy-0") or sid in ("B2", "B2 r3 fix"))
    if d["frame"] == "C0":
        judge = True       # judged on its wall hue / C* only; its L target is the G1.8 proposal
    rep["judgeable"] = judge
    if ref is not None and judge:
        rep["lit_wall_ok"] = (None if lo is None or d["frame"] == "C0" else bool(lo <= ref["graded_HSL"][2] <= hi))
        rep["hue_ok"] = bool(32 <= ref["graded_HSL"][0] <= 40)
        rep["C_ok"] = bool(ref["lab_C"] <= 7.0)
    Lm = L1.Lmap(frame)
    Hh, Ww = frame.shape[:2]
    sat = frame.max(2) >= 254.5 / 255
    from numpy.lib.stride_tricks import sliding_window_view
    kk = max(4, int(0.005 * canvas.shape[1]))                     # render-agent's window: 0.5 % of the saved file's width
    Lc = L1.Lmap(canvas)
    pm = sliding_window_view(Lc, (kk, kk))[::4, ::4].mean((2, 3))
    rep["black_point_L"] = round(float(pm.min()), 1)
    rep["black_ok"] = bool(12.0 <= pm.min() <= 15.0)
    rep["frame_L_p99"], rep["frame_L_max"], rep["px_255"] = round(float(np.percentile(Lm, 99)), 1), round(float(Lm.max()), 1), int(sat.sum())
    rep["frame_L_mean"] = round(float(Lm.mean()), 1)
    rep["rolloff_ok"] = bool(rep["frame_L_max"] <= 97.0 and rep["px_255"] == 0)
    a = AGENT_ROWS.get((C.AGENT_ID[sid], d["kind"] in ("fix", "fix8")))
    if a:
        rep["agent_row"] = dict(L=a["L_reference"], H=a["H"], C=a["C_star"], judged=a["wall_judged"], window_wall=a.get("window_wall"), meets=a["meets_bible_1_8_2"], fails=a["fails"],
                                corrected=a["hue_correction"]["applied"], touched_pct=a["hue_correction"]["pixels_touched_pct"], stops=a["stops"])
    if d["frame"] in CORRECTED and d["kind"] in ("master", "pose"):
        rep["halos"] = halos(sid, d)
    json.dump(rep, open(os.path.join(C.OUT, "data", f"light-{C.fn(sid)}.json"), "w"), indent=1, ensure_ascii=False)
    r = ref or {}
    hl = rep.get("halos")
    print(f"{sid:16s} ref L {r.get('graded_HSL', [None]*3)[2]} H {r.get('graded_HSL', [None])[0]} C* {r.get('lab_C')} [{lo}-{hi}] judge {judge} lit {rep.get('lit_wall_ok')} hue {rep.get('hue_ok')} C {rep.get('C_ok')} "
          f"| agent L {agent and agent['measured_L']} (QA-agent {pts[0].get('qa_minus_agent_L') if agent else None}) | ww {rep.get('window_wall', {}).get('graded_HSL', [None]*3)[2]} | black {rep['black_point_L']} | max {rep['frame_L_max']} 255 {rep['px_255']}"
          + (f" | B5 {rep['B5']['stops_hall_under_vista']} {rep['B5']['ok']}" if "B5" in rep else "")
          + (f" | halos {sum(h['halo'] for h in hl)}/{len(hl)} worst dh {max((h['step_v4']['dh'] for h in hl), default=None)} dC {max((h['step_v4']['dC'] for h in hl), default=None)}" if hl is not None else ""))
    return rep


def c0_s1():
    out = {}
    for sid in ("C0", "S1'", "H0"):
        d = C.load(sid, raw=False)
        Lm = L1.Lmap(d["graded"])
        rec = dict(mean=round(float(Lm.mean()), 1), p99=round(float(np.percentile(Lm, 99)), 1), max=round(float(Lm.max()), 1))
        for nm, (kind, b, area, vis) in C.boxes(d).items():
            if kind in ("door", "architecture") and ("portal" in nm or "door" in nm or "opening" in nm):
                bl = L1.box_px(Lm, b)
                if bl.size > 1000:
                    rec.setdefault("openings", {})[nm] = dict(box=[round(x, 3) for x in b], mean=round(float(bl.mean()), 1), p99=round(float(np.percentile(bl, 99)), 1))
        out[sid] = rec
    v3 = {}
    for sid in ("C0", "S1'"):
        f = os.path.join(C.REPO, C.C3.STILLS[sid][2].replace("-graded-v4.png", "-graded-v3.png"))
        Lm = L1.Lmap(C.rgb(f))
        v3[sid] = dict(mean=round(float(Lm.mean()), 1), p99=round(float(np.percentile(Lm, 99)), 1), max=round(float(Lm.max()), 1))
    out["v3_for_comparison"] = v3
    json.dump(out, open(os.path.join(C.OUT, "data", "c0-s1.json"), "w"), indent=1)
    print("C0 / S1' / H0:", json.dumps(out))


if __name__ == "__main__":
    ids = sys.argv[1:] or C.V4_ROWS
    for f in ids:
        run(f)
    if not sys.argv[1:]:
        c0_s1()
