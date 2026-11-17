#!/usr/bin/env python3
"""check_hdx.py: HDx lines (11.5.2 / 11.5.7) and levels (11.9.3) against the clay; render-agent 2026-11-17. 0 tokens.
  python3 check_hdx.py <img.png> <input.png> [out.json]"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K, lock_tall as T
CV = K.canvas("HDx")
def run(img, inp, outp=None):
    cls = K.clay_id("HDx")
    row = lambda v: int(round(CV.box[1] + v * CV.fh)); col = lambda u: int(round(CV.box[0] + u * CV.fw))
    to_u = lambda px: (px + 0.5 - CV.box[0]) / CV.fw
    r = row(0.45)
    corner = T.vstep_col(cls, r, (94, 86), (12,))
    walnut_l = T.vstep_col(cls, r, (12, 14, 24), (23, 20), lo=corner)
    walnut_r = T.vstep_col(cls, r, (20, 23), (24,) + tuple(range(30, 44)), lo=walnut_l)
    open_r = T.vstep_col(cls, r, tuple(range(30, 44)) + (0,), (12,), lo=walnut_r)
    V = {"inside corner (u 0.259)": (corner, row(0.05), row(0.95), 12, 8),
         "return / walnut lining (u 0.291)": (walnut_l, row(0.05), row(0.95), 10, 6),
         "walnut / living room (u 0.318)": (walnut_r, row(0.55), row(0.95), 10, 6),
         "opening, right arris (u 0.651)": (open_r, row(0.05), row(0.95), 12, 8)}
    # vertical joints near the left edge (u ~0.063)
    vj = [x for x in range(0, corner - 1) if cls[row(0.62), x] == 86 and cls[row(0.62), x - 1] != 86]
    Hh = {}
    meas = K.measure_lines(img, inp, V, Hh, seg=40)
    L, R = K.lum(img), K.lum(inp)
    curves = T.joint_curves(cls, (86,), (94,), 0, corner - 3, 0, CV.h, min_len=150)
    for i, pts in enumerate(sorted(curves, key=lambda p: p[len(p) // 2][1])):
        meas[f"stone joint {i + 1} (clay row {pts[len(pts) // 2][1]:.0f} mid)"] = T.measure_curve(L, R, pts)
    joints = [v["median_offset_px"] for k, v in meas.items() if "joint" in k and v["median_offset_px"] == v["median_offset_px"]]
    lines = {k: v["median_offset_px"] for k, v in meas.items() if "joint" not in k}
    pos = {k: dict(clay_u=round(to_u(x), 4), still_u=round(to_u(x + meas[k]["median_offset_px"]), 4)) for k, (x, *_r) in V.items()}
    rep = dict(lines=meas, positions_u=pos, joints_n=len(joints), joints_worst_px=max(abs(j) for j in joints) if joints else None,
               architecture_worst_px=max(abs(v) for v in lines.values()),
               rejection_11_5_7=dict(corner_0259=pos["inside corner (u 0.259)"], opening_0291_0651=[pos["return / walnut lining (u 0.291)"], pos["opening, right arris (u 0.651)"]],
                                     joints_within_3px=bool(joints and max(abs(j) for j in joints) <= 3)),
               levels=K.levels("HDx", img))
    if outp:
        json.dump(rep, open(outp, "w"), indent=1)
    return rep
if __name__ == "__main__":
    r = run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    for k, v in r["lines"].items():
        print(k, v["median_offset_px"], v["p90_abs_px"], v["n"], v["mean_corr"])
    print(json.dumps({k: v for k, v in r.items() if k != "lines"}, indent=1))
