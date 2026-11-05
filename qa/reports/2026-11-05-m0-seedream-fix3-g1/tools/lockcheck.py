"""
qa-agent 2026-11-05: G1.4 / G1.3 on the seedream M0 1.2 (raw + composite) and the fix3 frames. The same measures as on 11-04
(register, gated residual: bands response >= 0.10, tiles rho >= 0.30; masked register; box edges by cross-correlation; named lines
by cross-correlation AND nearest peak), the 11-04 named-line lists, plus the register on sub-regions for K-girl-0.
Writes data/lock-<id>.json and overlays/lock-<id>.jpg. Usage: ~/.venvs/motion/bin/python -I lockcheck.py [ids]
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
PAN = {"M0 seedream raw": True, "M0 seedream fix": True, "M0p 1.2 fix3": True, "B1 r3 fix3": True, "CB-0 b1r3f3": True, "W0-in r2 fix3": False, "K-girl-0 r2 fix3": True}
_txt = open(os.path.join(C.REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1/tools/lockcheck.py")).read()
_ns = {}
exec(compile("NAMED = " + _txt.split("NAMED = ")[1].split("\n\n\ndef named")[0], "lockcheck-1104", "exec"), _ns)
NAMED = {"W0-in r2 fix3": _ns["NAMED"]["W0-in r2 fix2"], "K-girl-0 r2 fix3": _ns["NAMED"]["K-girl-0 r2 fix2"], "B1 r3 fix3": _ns["NAMED"]["B1 r3 fix2"]}


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
    tu = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["tiles_ecc"] if x.get("rho") is not None and x["rho"] >= 0.30]
    bu = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in rep["check_raw"]["bands"] if x["response"] >= 0.10]
    return dict(bands=[round(x, 2) for x in b], tiles=[round(x, 2) for x in t], worst=round(max(b + t), 2) if (b or t) else None,
                unregistered=dict(bands=[round(x, 2) for x in bu], tiles=[round(x, 2) for x in tu], worst=round(max(bu + tu), 2) if (bu or tu) else None))


def run(sid):
    d = C.load(sid)
    pan = PAN[sid]
    clay, rend = C.at(d["clay"], W, H), C.at(d["raw"], W, H)
    rep = dict(frame=sid, raw=d["raw_file"], clay=d["clay_file"], pan_endpoint=pan)
    m = L3.measure(rend, clay, d, pan)
    rep["measure"] = m
    rep["gated_residual"] = gated(m)
    try:
        rep["masked_register"] = LK.masked_register(rend, clay, LK.product_mask(d))
    except Exception as e:  # noqa: BLE001
        rep["masked_register"] = dict(error=str(e)[:120])
    gc, gr = L3.gray(clay), L3.gray(rend)
    rep["named"] = named(gc, gr, sid)
    if sid.startswith("K-girl-0"):
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
    nl = [abs(v["d_nearest_peak"]) for v in rep["named"].values()]
    rep["verdict"] = dict(global_ok=bool(g_ok), residual_ok=bool(g["worst"] is not None and g["worst"] <= lim), residual_limit=lim,
                          named_worst_nearest_peak=max(nl) if nl else None)
    json.dump(rep, open(os.path.join(C.OUT, "data", f"lock-{C.fn(sid)}.json"), "w"), indent=1)
    L3.overlay(rend, clay, os.path.join(C.OUT, "overlays", f"lock-{C.fn(sid)}.jpg"), f"{sid}: clay edges (red) | shift {s['register_shift_px']} scale% {s['register_scale_pct']}")
    print(f"{sid:18s} shift {s['register_shift_px']} scale% {s['register_scale_pct']} | gated {g} | masked {rep['masked_register'].get('shift_px')} {rep['masked_register'].get('scale_pct')} "
          f"| xcorr box ratios {s['xcorr_ratios']} | named {{{', '.join(f'{k}: {v['d_xcorr']} (r {v['r']}) / {v['d_nearest_peak']}' for k, v in rep['named'].items())}}}")
    if "register_by_region" in rep:
        print("   register by region:", rep["register_by_region"])
    return rep


if __name__ == "__main__":
    for f in (sys.argv[1:] or (C.M0S + C.FIX3)):
        run(f)
