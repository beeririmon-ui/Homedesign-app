"""
G1.4 / G1.3 on the four 2026-11-04 code fixes, by QA's own code (qa/reports/2026-11-03-retakes-g1/tools/lock.py `measure`, imported):
register + bands + ECC tiles + box edges with cross-correlation, on the raw retake (before) and on its -fix.png (after), plus two
views that lock_v2 does not have:
  masked register   pan_reproject.register with the product boxes (dilated 2 % of the width) masked out of the ECC: the global
                    affine of the shell and fixed furniture only. A code edit that rescales products (prints, doll, planter) changes
                    the content the plain register fits; the masked one shows whether the room itself moved.
  graded = raw      the graded-fix-v4 file against the -fix.png (register): the grade must not move edges.
Writes data/lock-<id>.json and overlays/lock-<id>.jpg (clay edges in red over the -fix.png).
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

import importlib.util  # noqa: E402
_s = importlib.util.spec_from_file_location("qa1103_lock", os.path.join(C.REPO, "qa/reports/2026-11-03-retakes-g1/tools/lock.py"))
L3 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(L3)

W, H = 1920, 1080
PAN_ENDPOINT = {"W0-in r2 fix": False, "K-girl-0 r2 fix": True, "B1 r3 fix": True, "B2 r3 fix": True}


def product_mask(d):
    m = np.ones((H, W), np.uint8)
    for nm, (kind, b, area, vis) in C.boxes(d).items():
        if kind in ("proxy", "proxy-transit"):
            u0, u1, v0, v1 = b
            p = 0.02
            m[max(0, int((v0 - p) * H)):min(H, int((v1 + p) * H)), max(0, int((u0 - p) * W)):min(W, int((u1 + p) * W))] = 0
    return m


def masked_register(rend, clay, mask):
    reg, M = C.pr.register(rend, clay, mask=mask)
    out = C.pr.overlap_check(clay, C.pr.Cam(0, .5, .46), reg, C.pr.Cam(0, .5, .46), W, H)
    bands = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in out["bands"] if b["response"] >= 0.05]
    t = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in L3.tiles_ecc(reg, clay) if x["counted"]]
    return dict(shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)], scale_pct=[round((float(M[0, 0]) - 1) * 100, 2), round((float(M[1, 1]) - 1) * 100, 2)],
                masked_share=round(float(1 - mask.mean()), 3), worst_band_px_after=round(max(bands), 2) if bands else None, worst_tile_px_after=round(max(t), 2) if t else None)


def run(sid):
    t = C.FIXES[sid]
    d = C.load(sid)
    before = C.load(t[10])
    pan = PAN_ENDPOINT[sid]
    clay = C.at(d["clay"], W, H)
    fixr = C.at(d["raw"], W, H)
    bef = C.at(before["raw"], W, H)
    rep = dict(frame=sid, fix_file=t[3], before_file=before["raw_file"], clay=d["clay_file"], pan_endpoint=pan)
    rep["after"] = L3.measure(fixr, clay, d, pan)
    rep["before"] = L3.measure(bef, clay, before, pan)
    m = product_mask(d)
    rep["after_masked_register"] = masked_register(fixr, clay, m)
    rep["before_masked_register"] = masked_register(bef, clay, m)
    g = C.at(d["graded"], W, H)
    _, Mg = C.pr.register(g, fixr)
    rep["graded_vs_fix"] = dict(shift_px=[round(float(Mg[0, 2]), 2), round(float(Mg[1, 2]), 2)], scale_pct=[round((float(Mg[0, 0]) - 1) * 100, 3), round((float(Mg[1, 1]) - 1) * 100, 3)])
    a = C.agent_lock_fix(sid)
    if a:
        aa = a["after"]
        rep["agent_lock_fix"] = {k: aa.get(k) for k in ("register_shift_px", "register_scale_pct", "worst_band_px_after_register", "bands_counted", "worst_tile_px_after_register",
                                                        "tiles_counted", "box_edges_worst_px", "named_edges_worst_px", "named_edges_counted", "global_pass", "residual_pass", "edges_pass", "pass")}
        s = rep["after"]["summary"]
        rep["qa_vs_agent"] = dict(shift_diff_px=[round(s["register_shift_px"][i] - aa["register_shift_px"][i], 2) for i in range(2)],
                                  scale_pct_diff=[round(s["register_scale_pct"][i] - aa["register_scale_pct"][i], 2) for i in range(2)])
    json.dump(rep, open(os.path.join(C.OUT, "data", f"lock-{C.fn(sid)}.json"), "w"), indent=1)
    s, v = rep["after"]["summary"], rep["after"]["verdict"]
    L3.overlay(fixr, clay, os.path.join(C.OUT, "overlays", f"lock-{C.fn(sid)}.jpg"),
               f"{sid}: clay edges (red) over the -fix.png | shift {s['register_shift_px']} scale% {s['register_scale_pct']} | masked {rep['after_masked_register']['scale_pct']}")
    b = rep["before"]["summary"]
    mr, mb = rep["after_masked_register"], rep["before_masked_register"]
    print(f"{sid:16s} AFTER shift {s['register_shift_px']} scale% {s['register_scale_pct']} | band {s['worst_band_px_after_register']} ({s['bands_reliable_after_register']}) tile {s['worst_tile_ecc_px_after_register']} ({s['tiles_counted_after_register']}) "
          f"| box edges {s['fixed_edges_worst_px']} xcorr {s['xcorr_edges_worst_px']} ratios {s['xcorr_ratios']} | {'PASS' if v['passed'] else 'FAIL'} (g{int(v['global_pass'])} r{int(v['residual_pass'])} e{int(v['edges_pass'])})")
    print(f"{'':16s} BEFORE shift {b['register_shift_px']} scale% {b['register_scale_pct']} band {b['worst_band_px_after_register']} tile {b['worst_tile_ecc_px_after_register']}")
    print(f"{'':16s} MASKED register after: shift {mr['shift_px']} scale% {mr['scale_pct']} band {mr['worst_band_px_after']} tile {mr['worst_tile_px_after']} (masked {mr['masked_share']}) | before: shift {mb['shift_px']} scale% {mb['scale_pct']}")
    print(f"{'':16s} graded-v4 vs fix: {rep['graded_vs_fix']} | agent: {rep.get('agent_lock_fix', {}).get('register_shift_px')} {rep.get('agent_lock_fix', {}).get('register_scale_pct')} pass {rep.get('agent_lock_fix', {}).get('pass')}")
    return rep


if __name__ == "__main__":
    for f in (sys.argv[1:] or C.FIX_IDS):
        run(f)
