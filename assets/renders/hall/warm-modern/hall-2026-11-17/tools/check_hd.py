#!/usr/bin/env python3
"""check_hd.py: HD lines (11.5.2 / 11.5.7), levels (11.9.3) and the seam to the HDx seed; render-agent 2026-11-17. 0 tokens.
  python3 check_hd.py <img.png> <input.png> <keep_mask.png> [out.json]"""
import json, sys
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K, lock_tall as T
CV = K.canvas("HD")
def run(img, inp, keepp, outp=None):
    cls = K.clay_id("HD")
    keep = np.asarray(Image.open(keepp)) > 127
    row = lambda v: int(round(CV.box[1] + v * CV.fh))
    to_u = lambda px: (px + 0.5 - CV.box[0]) / CV.fw
    r = row(0.62)
    rr = cls[r]
    seams = [(a + b - 1) / 2 for a, b in K.runs_1d(rr, (83,))]
    edge = T.vstep_col(cls, r, (11, 82, 83), (94, 86))
    V = {"jib door seam left (u 0.019)": (int(round(seams[0])), 0, CV.h, 10, 6),
         "jib door seam right (u 0.380)": (int(round(seams[1])), 0, CV.h, 10, 6),
         "stone edge (u 0.521)": (edge, 0, CV.h, 12, 8)}
    # vertical joints in the stone (u ~0.804), measured on the courses where they exist
    vj = [x for x in range(edge + 5, CV.w - 1) if cls[r, x] == 86 and cls[r, x - 1] != 86]
    meas = K.measure_lines(img, inp, V, {}, seg=40)
    L, R = K.lum(img), K.lum(inp)
    curves = T.joint_curves(cls, (86,), (94,), edge + 4, CV.w, 0, CV.h, min_len=150)
    for i, pts in enumerate(sorted(curves, key=lambda p: p[len(p) // 2][1])):
        side = "in the seed (u >= 0.717)" if keep[int(pts[0][1]), int(pts[0][0])] and keep[int(pts[-1][1]), int(pts[-1][0])] else "rendered / across the seam"
        meas[f"stone joint {i + 1} (clay row {pts[len(pts) // 2][1]:.0f}), {side}"] = T.measure_curve(L, R, pts)
    joints = [v["median_offset_px"] for k, v in meas.items() if "joint" in k and v["median_offset_px"] == v["median_offset_px"]]
    pos = {k: dict(clay_u=round(to_u(x), 4), still_u=round(to_u(x + meas[k]["median_offset_px"]), 4)) for k, (x, *_r) in V.items()}
    # the seam to the seed: stone just left / right of the seed's boundary, per band of rows, ratio of medians
    Y = K.lin_Y(img)
    xb = np.array([np.argmax(keep[y]) if keep[y].any() else CV.w for y in range(CV.h)])
    rat = []
    for y0 in range(0, CV.h - 80, 80):
        a, b = [], []
        for y in range(y0, y0 + 80):
            x = xb[y]
            if 20 < x < CV.w - 20:
                st = cls[y] == 94
                a += list(Y[y, x - 18:x - 6][st[x - 18:x - 6]]); b += list(Y[y, x + 6:x + 18][st[x + 6:x + 18]])
        if len(a) > 200 and len(b) > 200:
            rat.append(float(np.median(b) / np.median(a)))
    seam = dict(bands=len(rat), median_pct=round(100 * (np.median(rat) - 1), 2), worst_pct=round(100 * max(abs(x - 1) for x in rat), 2),
                rule="11.5.7 / motion-agent: the tone at the seam within 3 %")
    rep = dict(lines=meas, positions_u=pos, joints_n=len(joints), joints_worst_px=max(abs(j) for j in joints) if joints else None,
               architecture_worst_px=max(abs(meas[k]["median_offset_px"]) for k in V), seam_to_hdx_seed=seam,
               rejection_11_5_7=dict(stone_edge_0521=pos["stone edge (u 0.521)"], seams_0019_0380=[pos["jib door seam left (u 0.019)"], pos["jib door seam right (u 0.380)"]],
                                     joints_within_3px=bool(joints and max(abs(j) for j in joints) <= 3)),
               levels=K.levels("HD", img))
    if outp:
        json.dump(rep, open(outp, "w"), indent=1)
    return rep
if __name__ == "__main__":
    r = run(*sys.argv[1:4], sys.argv[4] if len(sys.argv) > 4 else None)
    for k, v in r["lines"].items():
        print(k, v["median_offset_px"], v["p90_abs_px"], v["n"], v["mean_corr"])
    print(json.dumps({k: v for k, v in r.items() if k != "lines"}, indent=1))
