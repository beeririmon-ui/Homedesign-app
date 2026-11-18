#!/usr/bin/env python3
"""
lock_hc.py: the lock of HC (and HC130) against the clay, render-agent 2026-11-18. 0 tokens.
The clay's vertical edges (from the surface groups of prep_hc.py / the clay's world points) are found in the still by registering
across-line luminance profiles against the model input (the lit clay), as hallkit.measure_lines (2026-11-17). Offsets are still - clay, px.
  python3 lock_hc.py HC <still.png> <input.png> <report.json>
  python3 lock_hc.py HC130 <still.png> <input.png> <report.json>
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
import hallkit as HK  # noqa: E402

LINES = {
    "HC": {   # name: (u of the clay edge at v 0.50, v0, v1)
        "portal left reveal, hall side (u 0.240)": (0.2400, 0.10, 0.90),
        "portal left reveal, corridor side (u 0.279)": (0.2787, 0.15, 0.85),
        "bath door reveal near (u 0.400)": (0.3997, 0.38, 0.62),
        "bath door reveal far (u 0.418)": (0.4176, 0.40, 0.60),
        "laundry jib seam (u 0.431)": (0.4307, 0.42, 0.58),
        "bedroom door left jamb (u 0.469)": (0.4690, 0.40, 0.62),
        "bedroom door right jamb (u 0.533)": (0.5325, 0.40, 0.62),
        "girl's door reveal (u 0.557-0.563)": (0.5569, 0.40, 0.60),
        "boy's door reveal far (u 0.596)": (0.5956, 0.38, 0.62),
        "boy's door reveal near (u 0.613)": (0.6134, 0.36, 0.64),
        "portal right reveal, corridor side (u 0.767)": (0.7672, 0.15, 0.85),
        "portal right reveal, hall side (u 0.810)": (0.8097, 0.10, 0.90),
    },
    "HC130": {
        "portal north reveal, corridor side (u 0.144)": (0.1438, 0.10, 0.90),
        "portal north reveal, hall side (u 0.189)": (0.1888, 0.10, 0.90),
        "inside corner (u 0.444)": (0.4441, 0.10, 0.90),
        "jib door seam (u 0.653)": (0.6523, 0.10, 0.90),
    },
}


def main(name, still, inp, outp):
    cv = K.canvas(name)
    V, Hh = {}, {}
    for k, (u, v0, v1) in LINES[name].items():
        V[k] = (int(round(K.u_px(name, u))), int(round(K.v_px(name, v0))), int(round(K.v_px(name, v1))), 28, 22)
    res = HK.measure_lines(K.rgb8(still), K.rgb8(inp), V, Hh, seg=40)
    worst = max(abs(r["median_offset_px"]) for r in res.values() if r["n"])
    rep = dict(still=name, lines=res, worst_median_offset_px=round(worst, 2), px_per_u=round(cv.fw, 1))
    if name == "HC":
        l, r = res["bedroom door left jamb (u 0.469)"], res["bedroom door right jamb (u 0.533)"]
        ul = (K.u_px(name, 0.4690) + l["median_offset_px"] + 0.5 - cv.box[0]) / cv.fw
        ur = (K.u_px(name, 0.5325) + r["median_offset_px"] + 0.5 - cv.box[0]) / cv.fw
        rep["bedroom_door_u"] = [round(ul, 4), round(ur, 4)]
        rep["bedroom_door_centre_u"] = round((ul + ur) / 2, 4)
    K.dump(outp, rep)
    for k, r in res.items():
        print(f"{k:50s} {r['median_offset_px']:7.2f} px  n={r['n']}  corr={r['mean_corr']}")
    print({k: v for k, v in rep.items() if k != "lines"})


if __name__ == "__main__":
    main(*sys.argv[1:5])
