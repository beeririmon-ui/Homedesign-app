"""
qa-agent 2026-11-05: the light of M0 1.2 (seedream) graded v5 against Bible 1.8.4, and what "milky" is in numbers.
Bible points (back wall by the corner (0.427, 0.416) L 90-94; window wall (0.352, 0.415) L 80-88), H, C*, black point (0.5 %
windows), max L / 255; then the tonal shape against two references: m0-v7-r2 graded v5 (the old M0 grade) and the 11-04 gpt
composite graded v5: CIELAB L* percentiles, the share of the frame above L* 90, mean chroma, the median local contrast
(std of L* in 32 px windows), the darkest product (the charcoal cushion) and the floor / rug, the shadow under the sofa.
Also the fix3 frames at their agents' points (measurements-*-v5.json). Writes data/light-m0s.json, data/light-fix3.json.
Usage: ~/.venvs/motion/bin/python -I light_m0s.py
"""
import importlib.util
import json
import os

import cv2
import numpy as np

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1")
_s = importlib.util.spec_from_file_location("lv5", os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1/tools/light_v5.py"))
LV = importlib.util.module_from_spec(_s)
_s.loader.exec_module(LV)
R = "assets/renders/"
FILES = {"M0 seedream fix (v5)": R + "living-room/nordic/v9/m0-1-2-shell-seedream-graded-fix-v5.png",
         "M0 seedream raw": R + "living-room/nordic/v9/m0-1-2-shell-seedream-fix.png",
         "M0 v7 r2 (v5)": R + "living-room/nordic/v7/m0-v7-r2-graded-v5.png",
         "M0 1.2 gpt fix (v5, 11-04)": R + "living-room/nordic/v8/m0-v8b-r2-graded-fix-v5.png"}
# regions in canvas fractions (u0, u1, v0, v1): judged by eye on the seedream frame
REG = {"charcoal cushion": (0.70, 0.78, 0.66, 0.70), "rug / floor right of the sofa": (0.90, 0.98, 0.93, 0.97), "under the sofa right of the table (shadow)": (0.80, 0.84, 0.865, 0.885),
       "wood floor by the window": (0.33, 0.40, 0.765, 0.79)}
# Bible "light fall-off on the back wall" (grading chapter): by the corner 90-94, centre behind the picture 88-91, the right edge of the back wall 82-86 (HSL L)
FALL = {"by the corner (0.427, 0.416) [90-94]": (0.4269, 0.4156, 90, 94), "centre, above the triptych (0.62, 0.30) [88-91]": (0.62, 0.30, 88, 91),
        "centre, between triptych and sofa (0.62, 0.55) [88-91]": (0.62, 0.55, 88, 91), "right edge of the back wall (0.97, 0.31) [82-86]": (0.97, 0.31, 82, 86)}


def shape(a):
    Ls = LV.Lstar_map(a)
    lab = cv2.cvtColor(a.astype(np.float32), cv2.COLOR_RGB2LAB)
    C = np.hypot(lab[..., 1], lab[..., 2])
    k = 32
    m = cv2.blur(Ls, (k, k))
    sd = np.sqrt(np.maximum(cv2.blur(Ls * Ls, (k, k)) - m * m, 0))
    H, W = Ls.shape
    reg = {}
    for n, (u0, u1, v0, v1) in REG.items():
        p = Ls[int(v0 * H):int(v1 * H), int(u0 * W):int(u1 * W)]
        reg[n] = round(float(np.median(p)), 1)
    return dict(Lstar_p1=round(float(np.percentile(Ls, 1)), 1), Lstar_p5=round(float(np.percentile(Ls, 5)), 1), Lstar_p50=round(float(np.percentile(Ls, 50)), 1),
                Lstar_p95=round(float(np.percentile(Ls, 95)), 1), share_Lstar_over_90=round(float((Ls > 90).mean()), 3), mean_C=round(float(C.mean()), 2),
                local_contrast_median=round(float(np.median(sd)), 2), regions_Lstar=reg)


if __name__ == "__main__":
    out = {}
    for k, f in FILES.items():
        a = LV.rgb(f)
        fall = {n: dict(LV.read(a, u, v), range=[lo, hi], ok=bool(lo <= LV.read(a, u, v)["L"] <= hi)) for n, (u, v, lo, hi) in FALL.items()}
        rec = dict(file=f, back_wall=LV.read(a, 0.4269, 0.4156), window_wall=LV.read(a, 0.352, 0.415), fall_off=fall, black=LV.black_point(a),
                   max_L=round(float(LV.Lmap(a).max()), 1), px255=int((a.max(2) >= 254.5 / 255).sum()), shape=shape(a))
        out[k] = rec
        print(k, json.dumps(rec)[:900])
    LV.mark(LV.rgb(FILES["M0 seedream fix (v5)"]), [("back", (0.4269, 0.4156)), ("ww", (0.352, 0.415))] + [(n[:8], ((v[0] + v[1]) / 2, (v[2] + v[3]) / 2)) for n, v in REG.items()] + [(n[:6], (v[0], v[1])) for n, v in FALL.items()],
            os.path.join(OUT, "overlays", "points-M0s.jpg"))
    json.dump(out, open(os.path.join(OUT, "data", "light-m0s.json"), "w"), indent=1)
    # fix3 frames at the agents' points
    fx = {}
    for k, (g, meas) in {"B1 r3 fix3": (R + "bath/nordic/v7/b1-v7-r3-graded-fix3-v5.png", R + "bath/nordic/v7/b1-v7-r3-measurements-fix3-v5.json"),
                         "CB-0 b1r3f3": (R + "poses/nordic/v7/pose-cb-0-v7-graded-b1r3f3-v5.png", R + "poses/nordic/v7/pose-cb-0-v7-measurements-b1r3f3-v5.json"),
                         "W0-in r2 fix3": (R + "poses/nordic/v7/pose-w0-in-v7-r2-graded-fix3-v5.png", R + "poses/nordic/v7/pose-w0-in-v7-r2-measurements-fix3-v5.json"),
                         "M0p 1.2 fix3": (R + "poses/nordic/v8/pose-m0p-v8b-graded-fix3-v5.png", R + "poses/nordic/v8/pose-m0p-v8b-measurements-fix3-v5.json"),
                         "K-girl-0 r2 fix3": (R + "poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix3-v5.png", R + "poses/nordic/v7/pose-k-girl-0-v7-r2-measurements-fix3-v5.json")}.items():
        a = LV.rgb(g)
        m = json.load(open(os.path.join(REPO, meas)))
        b = m.get("bible_v3") or m.get("bible_v5") or m.get("bible") or {}
        pt = b.get("reference_point") or b.get("reference_uv")
        if k == "CB-0 b1r3f3":
            pt = [0.6449, 0.1701]
        rec = dict(file=g, agent_point=pt, agent_L=b.get("measured_L"), black=LV.black_point(a), max_L=round(float(LV.Lmap(a).max()), 1), px255=int((a.max(2) >= 254.5 / 255).sum()))
        if pt:
            rec["qa"] = LV.read(a, *pt)
        fx[k] = rec
        print(k, json.dumps(rec)[:400])
    json.dump(fx, open(os.path.join(OUT, "data", "light-fix3.json"), "w"), indent=1)
