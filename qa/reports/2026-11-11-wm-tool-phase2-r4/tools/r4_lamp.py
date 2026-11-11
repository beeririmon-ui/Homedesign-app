#!/usr/bin/env python3
"""
qa-agent 2026-11-11: the floor lamp's shade after R4, against the designer's targets (docs/proposals/wm-phase2-f3-decisions-2026-11-11.md
section 5). QA's own masks (the same rules as the checkpoint's p2_lamp.py, rebuilt here on the r4 layer's alpha):
  QA mask      = the cone's rows (layer top down to where the alpha-255 width falls under 40 px), alpha 255, eroded 3x3; thirds by column,
                 the bottom 15 % by row; the wall ring 15-40 px from the lamp's alpha in the same rows, off every other product's alpha.
  fabric (QA)  = the QA mask minus the brass, found two independent ways:
                 (a) "kept": the pixels of the QA mask whose RGB is byte-identical in the r3 and r4 layer files (what render-agent kept),
                     plus a 1 px ring;
                 (b) "colour": pixels of the QA mask, in its lowest 14 rows, whose r3 graded colour is brass (b* > 30, or L* < 75 and
                     b* > 20; hue 55-100 deg), grown 1 px. The two are compared.
  Targets 1-4 on the r4 graded scene (A, B, C); target 5 (folds) = graded high-pass std (L* minus a sigma-3 blur) on the fabric, r4 against
  r3, within +-10 %; also the fold registration: the correlation of the r3 and r4 high-pass on the fabric and the phase-correlation shift.
  The 4b pixels on the QA mask: how many, where, and their colour (brass or fabric?). Clipping: fabric pixels with a channel at 255 in the
  layer file (r3 vs r4). The collar / stem / base / chain: changed pixels of the layer outside the fabric.
Writes data/floor-lamp.json.   ~/.venvs/motion/bin/python -I r4_lamp.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-r4")
m3 = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
m4 = json.load(open(os.path.join(P2, "layers/manifest-r4.json")))
b3 = {l_["id"]: l_ for l_ in m3["layers"]}
b4 = {l_["id"]: l_ for l_ in m4["layers"]}
L3f = np.asarray(Image.open(os.path.join(P2, "layers", b3["floor-lamp"]["file"])))
L4f = np.asarray(Image.open(os.path.join(P2, "layers", b4["floor-lamp"]["file"])))
a = L4f[..., 3].astype(np.float32)


def lab8(img8):
    return cv2.cvtColor(img8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


rows = np.nonzero((a > 0).sum(1))[0]
width = (a >= 255).sum(1)
top = int(rows.min())
y = top
while y < a.shape[0] and (width[y] >= 40 or y < top + 10):
    y += 1
bot = y
shade = np.zeros(a.shape, bool)
shade[top:bot] = a[top:bot] >= 255
shade = cv2.erode(shade.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
xs = np.nonzero(shade.any(0))[0]
x0, x1 = int(xs.min()), int(xs.max())
w3 = (x1 - x0) / 3
cols = np.arange(a.shape[1])[None, :].repeat(a.shape[0], 0)
rr = np.arange(a.shape[0])[:, None].repeat(a.shape[1], 1)
left, right = shade & (cols < x0 + w3), shade & (cols > x1 - w3)
h = bot - top
bottom = shade & (rr >= bot - 0.15 * h)
d = cv2.distanceTransform((a == 0).astype(np.uint8), cv2.DIST_L2, 5)
ring = (d >= 15) & (d <= 40)
ring[:top] = False
ring[bot:] = False
for l_ in m4["layers"]:
    if "product" in l_ and l_["id"] != "floor-lamp":
        ring &= np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] == 0
res = dict(shade_rows=[top, bot], shade_cols=[x0, x1], qa_mask_px=int(shade.sum()), ring_px=int(ring.sum()))

# the brass, two ways
kept = (np.abs(L4f[..., :3].astype(int) - L3f[..., :3].astype(int)).max(2) == 0) & shade
kept_g = cv2.dilate(kept.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
G3B = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB"))
LAB3 = lab8(G3B)
hue3 = np.degrees(np.arctan2(LAB3[..., 2], LAB3[..., 1])) % 360
brass = shade & (rr >= bot - 14) & ((LAB3[..., 2] > 30) | ((LAB3[..., 0] < 75) & (LAB3[..., 2] > 20))) & (hue3 > 55) & (hue3 < 100)
brass_g = cv2.dilate(brass.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
ys_k, xs_k = np.nonzero(kept)
res["brass"] = dict(kept_px=int(kept.sum()), kept_box=[int(xs_k.min()), int(ys_k.min()), int(xs_k.max()) + 1, int(ys_k.max()) + 1] if kept.any() else None,
                    colour_px=int(brass.sum()), overlap_px=int((kept & brass).sum()),
                    kept_rows_from_bottom=[int(bot - ys_k.max()), int(bot - ys_k.min())] if kept.any() else None,
                    kept_r3_colour_Lab_median=[round(float(np.median(LAB3[..., c][kept])), 1) for c in range(3)] if kept.any() else None)
fabric = {"kept": shade & ~kept_g, "colour": shade & ~brass_g}
dk = cv2.distanceTransform((~kept).astype(np.uint8), cv2.DIST_L2, 5)

# the changed pixels of the layer outside the fabric (the collar, stem, base and chain must keep their pixels)
ch = (np.abs(L4f[..., :3].astype(int) - L3f[..., :3].astype(int)).max(2) > 0) & ((L4f[..., 3] > 0) | (L3f[..., 3] > 0))
ch_a = L4f[..., 3] != L3f[..., 3]
res["layer_changes"] = dict(rgb_changed_under_alpha_px=int(ch.sum()), rgb_changed_on_brass_colour_px=int((ch & brass).sum()),
                            rgb_changed_below_shade_rows_px=int(ch[bot + 3:].sum()), alpha_changed_px=int(ch_a.sum()),
                            alpha_changed_max_levels=int(np.abs(L4f[..., 3].astype(int) - L3f[..., 3].astype(int)).max()))


def measure(G8, masks):
    LAB = lab8(G8)
    L, bb = LAB[..., 0], LAB[..., 2]
    med = lambda m, ch_=L: float(np.median(ch_[m]))  # noqa: E731
    ringL, ringb, ringb95 = med(ring), med(ring, bb), float(np.percentile(bb[ring], 95))
    hp = L - cv2.GaussianBlur(L, (0, 0), 3)
    out = dict(ring=dict(L=round(ringL, 2), b=round(ringb, 2), b_p95=round(ringb95, 2)))
    for name, sel in masks.items():
        sh, le, ri, bo = shade & sel, left & sel, right & sel, bottom & sel
        lL, rL, bL, sb = med(le), med(ri), med(bo), med(sh, bb)
        hot = sh & (bb >= ringb95 + 8)
        t = {"1 left >= right + 5": [round(lL - rL, 2), bool(lL - rL >= 5)],
             "2 bottom15 <= right - 5": [round(bL - rL, 2), bool(bL <= rL - 5)],
             "3a left <= ring + 4": [round(lL - ringL, 2), bool(lL <= ringL + 4)],
             "3b right <= ring": [round(rL - ringL, 2), bool(rL <= ringL)],
             "4a b* median <= ring b* + 4": [round(sb - ringb, 2), bool(sb <= ringb + 4)],
             "4b no px b* >= ring p95 + 8": [int(hot.sum()), int(hot.sum()) == 0]}
        rec = dict(px=int(sh.sum()), left_L=round(lL, 2), right_L=round(rL, 2), bottom15_L=round(bL, 2), b_median=round(sb, 2),
                   L_p5_p50_p95_max=[round(float(np.percentile(L[sh], q)), 2) for q in (5, 50, 95, 100)],
                   hp_std=round(float(hp[sh].std()), 3), targets=t, all_1_to_4=all(v[1] for v in t.values()))
        if hot.any():
            yh, xh = np.nonzero(hot)
            rec["4b_px_box"] = [int(xh.min()), int(yh.min()), int(xh.max()) + 1, int(yh.max()) + 1]
            rec["4b_px_rows_from_shade_bottom"] = [int(bot - yh.max()), int(bot - yh.min())]
            rec["4b_px_on_kept"] = int((hot & kept_g).sum())
            rec["4b_px_on_brass_colour"] = int((hot & brass_g).sum())
            rec["4b_px_Lab_median"] = [round(float(np.median(LAB[..., c][hot])), 1) for c in range(3)]
            if hot.sum() <= 3:
                rec["4b_px_detail"] = [dict(xy=[int(x_), int(y_)], Lab_r4=[round(float(LAB[y_, x_, c]), 1) for c in range(3)],
                                            Lab_r3=[round(float(LAB3[y_, x_, c]), 1) for c in range(3)],
                                            layer_rgb_r3=L3f[y_, x_, :3].tolist(), layer_rgb_r4=L4f[y_, x_, :3].tolist(),
                                            dist_to_kept_px=round(float(dk[y_, x_]), 2)) for y_, x_ in zip(*np.nonzero(hot))]
        out[name] = rec
    return out, hp, L


res["scenes"] = {}
G4 = {}
for s in "BAC":
    G4[s] = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-r4-set-{s}-graded-v3c.png")).convert("RGB"))
    res["scenes"][f"r4 set {s}"], hp4, L4 = measure(G4[s], {"qa_mask": shade, "fabric_kept": fabric["kept"], "fabric_colour": fabric["colour"]})
    if s == "B":
        hp4B, L4B = hp4, L4
res["scenes"]["r3 set B (before)"], hp3B, L3B = measure(G3B, {"qa_mask": shade, "fabric_kept": fabric["kept"], "fabric_colour": fabric["colour"]})

# target 5, the folds
fab = fabric["kept"]
r = res["scenes"]
for name in ("qa_mask", "fabric_kept", "fabric_colour"):
    s4, s3 = r["r4 set B"][name]["hp_std"], r["r3 set B (before)"][name]["hp_std"]
    r["r4 set B"][name]["target5_hp_ratio_vs_r3"] = [round(s4 / s3, 3), bool(abs(s4 / s3 - 1) <= 0.10)]
cc = float(np.corrcoef(hp4B[fab], hp3B[fab])[0, 1])
ys_, xs_ = np.nonzero(fab)
y0, y1, xa, xb = ys_.min(), ys_.max() + 1, xs_.min(), xs_.max() + 1
win = cv2.createHanningWindow((int(xb - xa), int(y1 - y0)), cv2.CV_32F)
(dx, dy), resp = cv2.phaseCorrelate((hp3B * fab)[y0:y1, xa:xb].astype(np.float32), (hp4B * fab)[y0:y1, xa:xb].astype(np.float32), win)
# the fine folds only (sigma 1.5 band): does the r4 shade carry a doubled / ghosted fold pattern?
hpf4 = L4B - cv2.GaussianBlur(L4B, (0, 0), 1.5)
hpf3 = L3B - cv2.GaussianBlur(L3B, (0, 0), 1.5)
res["folds"] = dict(corr_hp3_r3_vs_r4_on_fabric=round(cc, 3), phase_shift_px=[round(dx, 3), round(dy, 3)], phase_response=round(float(resp), 3),
                    fine_hp_std_r3=round(float(hpf3[fab].std()), 3), fine_hp_std_r4=round(float(hpf4[fab].std()), 3),
                    corr_fine=round(float(np.corrcoef(hpf4[fab], hpf3[fab])[0, 1]), 3))
# vertical profile: the lower-edge band (is there a hard horizontal step in the shading?)
prof = []
for yy in range(top, bot):
    m = fab[yy]
    if m.sum() >= 10:
        prof.append([yy, round(float(np.median(L4B[yy][m])), 2), round(float(np.median(L3B[yy][m])), 2)])
res["row_profile_L_r4_r3"] = prof
steps = [abs(prof[i + 1][1] - prof[i][1]) for i in range(len(prof) - 1)]
res["row_profile_max_step_r4"] = round(max(steps), 2)
res["row_profile_max_step_r3"] = round(max(abs(prof[i + 1][2] - prof[i][2]) for i in range(len(prof) - 1)), 2)
# clipping in the layer files
for nm, Lf in (("r3", L3f), ("r4", L4f)):
    res[f"fabric_px_with_a_channel_at_255_{nm}"] = int(((Lf[..., :3] == 255).any(2) & fab).sum())
# the shade's soft rim: is any rim pixel lighter than both the fabric just inside and the wall just outside (a light halo)?
rim = (a > 0) & (a < 255)
rim[:top - 2], rim[bot + 2:] = False, False
Lb = L4B
inner = cv2.erode((a >= 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
den_i = cv2.GaussianBlur(inner.astype(np.float32), (0, 0), 2.5)
Li = cv2.GaussianBlur(Lb * inner, (0, 0), 2.5) / np.maximum(den_i, 1e-4)
outer = (d >= 3) & (d <= 8)
den_o = cv2.GaussianBlur(outer.astype(np.float32), (0, 0), 2.5)
Lo = cv2.GaussianBlur(Lb * outer, (0, 0), 2.5) / np.maximum(den_o, 1e-4)
ok = rim & (den_i > 0.02) & (den_o > 0.02)
exc = Lb - np.maximum(Li, Lo)
res["rim"] = dict(rim_px=int(ok.sum()), lighter_than_both_by_3=int((ok & (exc > 3)).sum()), lighter_than_both_by_6=int((ok & (exc > 6)).sum()),
                  max_excess=round(float(exc[ok].max()), 2))
L3rim = L3B
Li3 = cv2.GaussianBlur(L3rim * inner, (0, 0), 2.5) / np.maximum(den_i, 1e-4)
Lo3 = cv2.GaussianBlur(L3rim * outer, (0, 0), 2.5) / np.maximum(den_o, 1e-4)
exc3 = L3rim - np.maximum(Li3, Lo3)
res["rim_r3"] = dict(lighter_than_both_by_3=int((ok & (exc3 > 3)).sum()), lighter_than_both_by_6=int((ok & (exc3 > 6)).sum()))
json.dump(res, open(os.path.join(OUT, "data/floor-lamp.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "row_profile_L_r4_r3"}, indent=1))
