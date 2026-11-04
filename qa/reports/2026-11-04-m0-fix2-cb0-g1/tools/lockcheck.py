"""
G1.4 / G1.3 on the M0 1.2 composites, the four fix2 frames and CB-0 recomposed from B1 r3: QA's measures (register, gated
residual: bands response >= 0.10, tiles rho >= 0.30, box edges by cross-correlation), the masked register (product boxes out),
and named lines (the 11-03 / 11-04 lists, W0-in's chair top on the clay's 835 line). For K-girl-0 fix2 also the register on
sub-regions, to see whether its global scale is a property of the frame or of the estimator.
Writes data/lock-<id>.json and overlays/lock-<id>.jpg.
"""
import importlib.util
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

_s = importlib.util.spec_from_file_location("qa1104_lock", os.path.join(C.REPO, "qa/reports/2026-11-04-retakes-fixes-g1/tools/lock.py"))
LK = importlib.util.module_from_spec(_s)
_s.loader.exec_module(LK)
L3 = LK.L3
W, H = 1920, 1080
PAN = {"M0 1.2 fix": True, "M0 1.2 r2": True, "M0p 1.2 fix": True, "M0x 1.2 fix": True, "B1 r3 fix2": True, "B2 r3 fix2": True,
       "K-girl-0 r2 fix2": True, "W0-in r2 fix2": False, "CB-0 b1r3": True}
NAMED = {  # (name, orient, span, search) in 16:9 frame fractions (edges_direct.py of 11-03; W0-in chair top on the clay's 835 line)
    "W0-in r2 fix2": [("desk top front edge", "h", (0.68, 0.80), (0.70, 0.76)), ("desk front face bottom left of chair", "h", (0.20, 0.33), (0.70, 0.76)),
                      ("drawer bottom / apron", "h", (0.20, 0.33), (0.80, 0.90)), ("chair back top (clay 835)", "h", (0.42, 0.58), (0.755, 0.80)),
                      ("desk left outer edge", "v", (0.80, 0.95), (0.08, 0.26)), ("chair back left edge", "v", (0.82, 0.98), (0.28, 0.44)),
                      ("chair back right edge", "v", (0.82, 0.98), (0.56, 0.72)), ("shelf top", "h", (0.30, 0.70), (0.08, 0.15))],
    "K-girl-0 r2 fix2": [("upper ledge", "h", (0.03, 0.10), (0.19, 0.23)), ("lower ledge", "h", (0.03, 0.10), (0.34, 0.37)), ("band top (desk wall)", "h", (0.05, 0.20), (0.33, 0.37)),
                         ("desk top", "h", (0.25, 0.45), (0.60, 0.66)), ("skirting top (desk wall)", "h", (0.30, 0.36), (0.87, 0.92)), ("room corner", "v", (0.08, 0.30), (0.58, 0.64)),
                         ("desk left leg", "v", (0.72, 0.90), (0.25, 0.29)), ("desk right leg", "v", (0.72, 0.90), (0.44, 0.48)), ("bed foot right edge", "v", (0.68, 0.90), (0.19, 0.23))],
    "B1 r3 fix2": [("glazing top", "h", (0.24, 0.32), (0.08, 0.22)), ("glazing bottom / sill", "h", (0.24, 0.32), (0.42, 0.56)), ("ledge top", "h", (0.17, 0.30), (0.46, 0.52)),
                   ("glazing left", "v", (0.20, 0.42), (0.14, 0.26)), ("glazing right", "v", (0.20, 0.42), (0.30, 0.42)), ("WC block left", "v", (0.62, 0.90), (0.08, 0.20)),
                   ("WC block right", "v", (0.62, 0.90), (0.36, 0.46)), ("corner / track end", "v", (0.05, 0.40), (0.68, 0.78)), ("vanity left edge", "v", (0.66, 0.95), (0.86, 0.96))],
    "B2 r3 fix2": [("vanity top", "h", (0.52, 0.70), (0.44, 0.50)), ("mirror bottom", "h", (0.60, 0.76), (0.43, 0.48)), ("niche top", "h", (0.53, 0.63), (0.43, 0.48)),
                   ("vanity left edge", "v", (0.58, 0.90), (0.47, 0.50)), ("vanity right outer edge", "v", (0.60, 0.90), (0.815, 0.835)), ("mirror left", "v", (0.12, 0.40), (0.54, 0.57)),
                   ("mirror right", "v", (0.12, 0.40), (0.79, 0.82)), ("curtain outer edge", "v", (0.20, 0.70), (0.29, 0.32))],
}


def named(gc, gr, sid):
    out = {}
    for name, o, span, search in NAMED.get(sid, []):
        if o == "h":
            c0, c1 = int(span[0] * W), int(span[1] * W)
            pc, prr = (np.abs(np.diff(g[:, c0:c1], axis=0)).mean(1) for g in (gc, gr))
            n, lo, hi = H, int(search[0] * H), int(search[1] * H)
        else:
            r0, r1 = int(span[0] * H), int(span[1] * H)
            pc, prr = (np.abs(np.diff(g[r0:r1], axis=1)).mean(0) for g in (gc, gr))
            n, lo, hi = W, int(search[0] * W), int(search[1] * W)
        ic = lo + int(np.argmax(pc[lo:hi]))
        o_, r = L3.xcorr_offset(pc, prr, ic / n, n, half=60)
        lo2, hi2 = max(0, ic - 40), min(n - 1, ic + 40)
        near = lo2 + int(np.argmax(prr[lo2:hi2]))
        out[name] = dict(clay_px=ic, d_xcorr=o_, r=r, d_nearest_peak=near - ic)
    return out


def gated(rep):
    b = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["check_registered"]["bands"] if x["response"] >= 0.10]
    t = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc_registered"] if x.get("rho") is not None and x["rho"] >= 0.30]
    return dict(bands=[round(x, 2) for x in b], tiles=[round(x, 2) for x in t], worst=round(max(b + t), 2) if (b or t) else None)


def run(sid):
    d = C.load(sid)
    pan = PAN[sid]
    clay, rend = C.at(d["clay"], W, H), C.at(d["raw"], W, H)
    rep = dict(frame=sid, raw=d["raw_file"], clay=d["clay_file"], pan_endpoint=pan)
    m = L3.measure(rend, clay, d, pan)
    rep["measure"] = m
    rep["gated_residual"] = gated(m)
    rep["masked_register"] = LK.masked_register(rend, clay, LK.product_mask(d))
    gc, gr = L3.gray(clay), L3.gray(rend)
    rep["named"] = named(gc, gr, sid)
    if sid == "K-girl-0 r2 fix2":
        sub = {}
        for nm, (x0, x1) in {"left 60 % (desk wall)": (0, 0.6), "right 40 % (near wall)": (0.6, 1.0), "middle 80 %": (0.1, 0.9)}.items():
            mk = np.zeros((H, W), np.uint8)
            mk[:, int(x0 * W):int(x1 * W)] = 1
            try:
                _, M = C.pr.register(rend, clay, mask=mk)
                sub[nm] = dict(shift_px=[round(float(M[0, 2]), 2), round(float(M[1, 2]), 2)], scale_pct=[round((float(M[0, 0]) - 1) * 100, 2), round((float(M[1, 1]) - 1) * 100, 2)])
            except cv2.error as e:
                sub[nm] = dict(error=str(e)[:80])
        rep["register_by_region"] = sub
    s = m["summary"]
    g = rep["gated_residual"]
    lim = 2.0 if pan else 9.6
    g_ok = max(abs(x) for x in s["register_shift_px"]) <= 9.6 and max(abs(x) for x in s["register_scale_pct"]) <= 0.5
    nl = [abs(v["d_xcorr"]) for v in rep["named"].values() if v["d_xcorr"] is not None and v["r"] >= 0.5]
    rep["verdict"] = dict(global_ok=bool(g_ok), residual_ok=bool(g["worst"] is not None and g["worst"] <= lim), residual_limit=lim,
                          named_worst=max(nl) if nl else None, named_ok=bool(not nl or max(nl) <= 19))
    json.dump(rep, open(os.path.join(C.OUT, "data", f"lock-{C.fn(sid)}.json"), "w"), indent=1)
    L3.overlay(rend, clay, os.path.join(C.OUT, "overlays", f"lock-{C.fn(sid)}.jpg"), f"{sid}: clay edges (red) | shift {s['register_shift_px']} scale% {s['register_scale_pct']}")
    print(f"{sid:18s} shift {s['register_shift_px']} scale% {s['register_scale_pct']} | gated {g} | masked {rep['masked_register']['shift_px']} {rep['masked_register']['scale_pct']} "
          f"| xcorr box ratios {s['xcorr_ratios']} | named {{{', '.join(f'{k}: {v['d_xcorr']} (r {v['r']}) / {v['d_nearest_peak']}' for k, v in rep['named'].items())}}}")
    if "register_by_region" in rep:
        print("   register by region:", rep["register_by_region"])
    return rep


if __name__ == "__main__":
    for f in (sys.argv[1:] or (C.FIX2 + C.M012 + ["M0 1.2 r2", "CB-0 b1r3"])):
        run(f)
