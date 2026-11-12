#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R8): curtain 3's specks, the detail behind data/curtains.json section D (runs r8_curtains.py for its functions).
  1. every pixel either rule flags in R8 (graded layer at alpha > 0, ungraded source, set-B truth): x, y, alpha, Lab, C*, h;
  2. the wide rule's margin (a* - median7 a*, threshold -8) on the opaque hits, in QA's numpy Lab and in OpenCV's Lab (R8's);
  3. the pixels outside R8's mask file (work-r8/curtain3-speck-mask.npy, passes 1-2) whose a*b* changed by > 3 between the ungraded R7
     and R8 sources: alpha, R7 / R8 hue, L* kept or not (against the global Y factor), and how many the wide rule flags once the L*
     factor alone is applied to R7 (simulated in QA's Lab) - fix-r8.json's "final_pass" (44 px) is not in the mask file;
  4. the literal hits' effect on the composite: alpha x the RGB distance to a neutral of the same L*, in 8-bit levels.
Writes data/specks-detail.json.     ~/.venvs/motion/bin/python3.12 -I r8_specks_detail.py
"""
import contextlib
import io
import json
import os
import runpy

import cv2
import numpy as np

HERE = "/home/user/homedesign-app/qa/reports/2026-11-12-wm-phase2-r8/tools"
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(os.path.join(HERE, "r8_curtains.py"))
u8, P2, lab, specks, layer, truth, Yof = g["u8"], g["P2"], g["lab"], g["specks"], g["layer"], g["truth"], g["Yof"]
OUT = "/home/user/homedesign-app/qa/reports/2026-11-12-wm-phase2-r8"
BOX = (0, 0, 300, 1460)
res = {}
Lg = layer("r8", "curtains-v3")
U7 = u8(os.path.join(P2, "work-r7/layers/curtains-v3.png"))
U8 = u8(os.path.join(P2, "work-r8/layers/curtains-v3.png"))
T = truth("r8", "curtains-v3")


def hits(rgb, al):
    lit, wide, Lb = specks(rgb, al, BOX)
    out = []
    for y, x in zip(*np.nonzero(lit | wide)):
        L, a, b = Lb[y, x]
        out.append(dict(x=int(x), y=int(y), alpha=int(al[y, x]), L=round(float(L), 1), a=round(float(a), 1), b=round(float(b), 1),
                        C=round(float(np.hypot(a, b)), 1), h=round(float(np.degrees(np.arctan2(b, a)) % 360), 1), literal=bool(lit[y, x]), wide=bool(wide[y, x]),
                        in_camera_frame=bool(77.49 <= x <= 2642.51 and 43.43 <= y <= 1486.57)))
    return out


res["r8_hits"] = {"graded_layer_alpha_gt0": hits(Lg[..., :3], Lg[..., 3]), "ungraded_source": hits(U8[..., :3], U8[..., 3]),
                  "set_B_truth_in_alpha": hits(T, Lg[..., 3])}
gl = res["r8_hits"]["graded_layer_alpha_gt0"]
res["graded_literal_hits_alpha_range"] = [min(h["alpha"] for h in gl if h["literal"]), max(h["alpha"] for h in gl if h["literal"])]
res["graded_literal_hits_x_range"] = [min(h["x"] for h in gl if h["literal"]), max(h["x"] for h in gl if h["literal"])]
# composite effect of the literal (soft-edge) hits: alpha/255 x RGB distance to a neutral grey of the same L*
eff = []
for h in gl:
    if not h["literal"]:
        continue
    rgb = Lg[h["y"], h["x"], :3].astype(float)
    grey = np.full(3, float(np.dot(rgb, [0.2126, 0.7152, 0.0722])))
    eff.append(round(float(h["alpha"] / 255 * np.abs(rgb - grey).max()), 2))
res["literal_hits_composite_effect_levels_max"] = max(eff) if eff else 0


def margins(U, pts):
    rgb = U[:1460, :300, :3]
    Lb = lab(rgb)
    md = cv2.medianBlur(np.clip(np.round(Lb[..., 1] + 128), 0, 255).astype(np.uint8), 7).astype(float) - 128
    lc = cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    mdc = cv2.medianBlur(np.clip(np.round(lc[..., 1] + 128), 0, 255).astype(np.uint8), 7).astype(float) - 128
    return {f"{x},{y}": dict(qa_lab_a_minus_med=round(float(Lb[y, x, 1] - md[y, x]), 3), opencv_lab_a_minus_med=round(float(lc[y, x, 1] - mdc[y, x]), 3),
                             threshold=-8.0) for (x, y) in pts}


opaque = [(h["x"], h["y"]) for h in res["r8_hits"]["ungraded_source"]]
res["wide_rule_margins_r8_ungraded"] = margins(U8, opaque)
res["wide_rule_margins_r7_ungraded_same_px"] = margins(U7, opaque)

# 3. outside the mask file
rmask = np.load(os.path.join(P2, "work-r8/curtain3-speck-mask.npy"), allow_pickle=False)
l7, l8 = lab(U7[..., :3]), lab(U8[..., :3])
dab = np.hypot(l8[..., 1] - l7[..., 1], l8[..., 2] - l7[..., 2])
outside = (U7[..., 3] > 0) & ~cv2.dilate(rmask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
ys, xs = np.nonzero(outside & (dab > 3))
Y7, Y8 = Yof(U7[..., :3]), Yof(U8[..., :3])
body = (U7[..., 3] == 255) & ~rmask
body[1150:] = False
f = float(np.median((Y8 / np.maximum(Y7, 1e-6))[body]))
Lpred = 116 * np.cbrt(Y7 * f) - 16
fin = [dict(x=int(x), y=int(y), alpha=int(U7[y, x, 3]), h_r7=round(float(np.degrees(np.arctan2(l7[y, x, 2], l7[y, x, 1])) % 360), 1),
            h_r8=round(float(np.degrees(np.arctan2(l8[y, x, 2], l8[y, x, 1])) % 360), 1), C_r7=round(float(np.hypot(l7[y, x, 1], l7[y, x, 2])), 1),
            L_r7=round(float(l7[y, x, 0]), 1), dL_vs_global_factor=round(float(l8[y, x, 0] - Lpred[y, x]), 2), dab=round(float(dab[y, x]), 1))
       for y, x in zip(ys, xs)]
# simulate the L* step alone on R7 (Y x f, a*b* kept) and ask the wide rule
fy = (np.clip(Lpred, 0, 100) + 16) / 116
fx, fz = fy + l7[..., 1] / 500, fy - l7[..., 2] / 200


def finv(t):
    return np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))


xyz = np.stack([finv(fx) * 0.95047, finv(fy), finv(fz) * 1.08883], -1)
Minv = np.linalg.inv(np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]]))
rgb = np.clip(xyz @ Minv.T, 0, 1)
S = np.clip(np.round(np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055) * 255), 0, 255).astype(np.uint8)
_, wide_sim, _ = specks(S, U7[..., 3], BOX)
res["outside_mask_file"] = dict(mask_file_px=int(rmask.sum()), r8_record_final_pass_px=44, dab_gt3_px=len(fin),
                                flagged_by_wide_rule_after_Lstar_step_sim=int(wide_sim[ys, xs].sum()),
                                h_r7_range=[min(p["h_r7"] for p in fin), max(p["h_r7"] for p in fin)] if fin else None,
                                h_r8_range=[min(p["h_r8"] for p in fin), max(p["h_r8"] for p in fin)] if fin else None,
                                dL_vs_global_factor_max_abs=max(abs(p["dL_vs_global_factor"]) for p in fin) if fin else None,
                                alpha_range=[min(p["alpha"] for p in fin), max(p["alpha"] for p in fin)] if fin else None, pixels=fin, global_Y_factor=round(f, 4))
json.dump(res, open(os.path.join(OUT, "data/specks-detail.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("r8_hits",)}, indent=1)[:3500])
print({k: len(v) for k, v in res["r8_hits"].items()})
