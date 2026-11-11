"""
qa-agent 2026-11-11: polish (b) on warm-modern-MB-A-fix6, the numbers and the edges.
  - the designer's box (x 2210-2330, y 820-925; round 5's cast_shadow.py slicing, L[820:925, 2210:2330]): median and mean L*;
    the slit (round 5's gap.py spot box, L[770:812, 2030:2060]); QA's area (x 2215-2330, y 840-925);
  - the hue: the core (box, L* < 20, off the cushion) against the lit caramel of the same right pillowcase (L* 30-45, x 2340-2560,
    y 760-900, outside the mask) and round 5's left-pillowcase patch value (h 56.5); mean a*, b* of the set, then its angle;
  - the contact line: per row y 830-915, the darkest L* within 1-4 px right of the cushion's edge (QA's fix5 cushion mask) against
    the shadow 8-20 px further right, fix5 and fix6;
  - the creases inside the shadow: L* high-pass (sigma 3) SD in the core, fix5 and fix6, and their correlation (a curve keeps them;
    a fill would drop both);
  - the mask's edge: for every pair of 4-neighbours across the edge (one in, one out), the step it adds,
    (L6_in - L6_out) - (L5_in - L5_out), split by side; and (b)'s own residual (data/b-only-dL.npz) on the mask's inner 1-2 px.
Usage: ~/.venvs/motion/bin/python -I b_edges.py (after master_diff.py). Writes data/b-numbers.json.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MB, OUT, lab, load, mean_lab, r  # noqa: E402

f5 = load(os.path.join(MB, "warm-modern-MB-A-fix5.png"))
f6 = load(os.path.join(MB, "warm-modern-MB-A-fix6.png"))
reg = np.asarray(Image.open(os.path.join(MB, "raw/fix6-b-region.png"))) > 0
lum = np.asarray(Image.open(os.path.join(OUT, "data/qa-lumbar-mask-fix5.png"))) > 127
bres = np.load(os.path.join(OUT, "data/b-only-dL.npz"))["dL"]
l5, l6 = lab(f5), lab(f6)
L5, L6 = l5[..., 0], l6[..., 0]
H, W = L5.shape
out = {}
for k, L in (("fix5", L5), ("fix6", L6)):
    out[k] = dict(designer_box_median=r(np.median(L[820:925, 2210:2330])), designer_box_mean=r(L[820:925, 2210:2330].mean()),
                  designer_box_inclusive_median=r(np.median(L[820:926, 2210:2331])),
                  qa_area_median=r(np.median(L[840:926, 2215:2331])),
                  slit_median=r(np.median(L[770:812, 2030:2060])),
                  core_lt14_px_in_box=int((L[820:925, 2210:2330] < 14).sum()))
# hue: the core and the lit caramel
box = np.zeros((H, W), bool)
box[820:925, 2210:2330] = True
for k, lb, L in (("fix5", l5, L5), ("fix6", l6, L6)):
    core = box & ~lum & (L5 < 20)                       # the same px in both frames (selected on fix5)
    core14 = box & ~lum & (L5 < 14)
    lit = np.zeros((H, W), bool)
    lit[720:900, 2300:2560] = True                      # round 5's right patch, off the mask and off the shadow
    lit &= ~reg & (L5 >= 20)
    out[k]["core_L5_lt_20"] = mean_lab(lb, core)
    out[k]["core_L5_lt_14"] = mean_lab(lb, core14)
    out[k]["caramel_right_patch_off_shadow"] = mean_lab(lb, lit)
    pl = np.zeros((H, W), bool)
    pl[720:900, 1520:1780] = True                       # round 5's left patch (the lit side): the "lit caramel"
    out[k]["caramel_left_patch_lit"] = mean_lab(lb, pl)
out["hue_window_designer"] = "+-3 deg of the lit caramel's hue"
out["lit_caramel_left_patch_round5_h"] = 56.5

# contact line
rows = []
for y in range(830, 916, 5):
    xe = int(np.nonzero(lum[y])[0].max())
    a5, a6 = L5[y, xe + 1:xe + 5].min(), L6[y, xe + 1:xe + 5].min()
    s5, s6 = np.median(L5[y, xe + 8:xe + 20]), np.median(L6[y, xe + 8:xe + 20])
    rows.append(dict(y=y, edge=xe, line_fix5=r(a5, 1), shadow_fix5=r(s5, 1), line_fix6=r(a6, 1), shadow_fix6=r(s6, 1)))
out["contact_line_rows"] = rows
out["contact_line_summary"] = dict(line_fix5_median=r(np.median([q["line_fix5"] for q in rows]), 1),
                                   line_fix6_median=r(np.median([q["line_fix6"] for q in rows]), 1),
                                   shadow_minus_line_fix5_median=r(np.median([q["shadow_fix5"] - q["line_fix5"] for q in rows]), 1),
                                   shadow_minus_line_fix6_median=r(np.median([q["shadow_fix6"] - q["line_fix6"] for q in rows]), 1))
# the base against the duvet: per column x 2230-2480, the darkest L* in the 4 px above the contact line, against the shadow 8-20 px above
base = []
for x in range(2230, 2481, 25):
    col = np.nonzero(reg[:, x])[0]
    if not col.size:
        continue
    yb = int(col.max())
    base.append(dict(x=x, y=yb, line_fix5=r(L5[yb - 3:yb + 3, x].min(), 1), line_fix6=r(L6[yb - 3:yb + 3, x].min(), 1),
                     above_fix5=r(np.median(L5[yb - 20:yb - 8, x]), 1), above_fix6=r(np.median(L6[yb - 20:yb - 8, x]), 1)))
out["base_line_cols"] = base
# creases
core = box & ~lum & (L5 < 20)
hp5 = L5 - cv2.GaussianBlur(L5, (0, 0), 3)
hp6 = L6 - cv2.GaussianBlur(L6, (0, 0), 3)
out["creases_core"] = dict(hp_sd_fix5=r(hp5[core].std(), 3), hp_sd_fix6=r(hp6[core].std(), 3),
                           ratio=r(hp6[core].std() / hp5[core].std(), 3), corr=r(np.corrcoef(hp5[core], hp6[core])[0, 1], 3))
lit = np.zeros((H, W), bool)
lit[720:900, 2300:2560] = True
lit &= ~reg & (L5 >= 20)
out["creases_lit_pillowcase_ref"] = dict(hp_sd=r(hp6[lit].std(), 3), hp_sd_over_L=r(hp6[lit].std() / L6[lit].mean(), 4),
                                         core_hp_sd_over_L_fix5=r(hp5[core].std() / L5[core].mean(), 4),
                                         core_hp_sd_over_L_fix6=r(hp6[core].std() / L6[core].mean(), 4))

# mask edge: pairs across the edge (4-neighbours)
steps = {"left (cushion side, x < 2232)": [], "bottom (duvet side, y >= 912)": [], "top/right (lit pillowcase)": []}
res_in = []
inner = reg & ~cv2.erode(reg.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    yy, xx = np.nonzero(inner)
    y2, x2 = yy + dy, xx + dx
    ok = (y2 >= 0) & (y2 < H) & (x2 >= 0) & (x2 < W)
    yy, xx, y2, x2 = yy[ok], xx[ok], y2[ok], x2[ok]
    o = ~reg[y2, x2]
    yy, xx, y2, x2 = yy[o], xx[o], y2[o], x2[o]
    st = (L6[yy, xx] - L6[y2, x2]) - (L5[yy, xx] - L5[y2, x2])
    for a, b, s in zip(yy, xx, st):
        side = "left (cushion side, x < 2232)" if b < 2232 else ("bottom (duvet side, y >= 912)" if a >= 912 else "top/right (lit pillowcase)")
        steps[side].append(s)
for k, v in steps.items():
    v = np.abs(np.array(v))
    steps[k] = dict(pairs=int(v.size), abs_step_p50=r(np.percentile(v, 50)), p90=r(np.percentile(v, 90)), p99=r(np.percentile(v, 99)),
                    max=r(v.max()), share_gt_1=r((v > 1).mean(), 3), share_gt_2=r((v > 2).mean(), 3))
out["mask_edge_added_step_L"] = steps
tab = np.array(json.load(open(os.path.join(OUT, "data", "master-toe-curve.json")))["table"])
toeL = np.where(L5 < 20, np.interp(L5, tab[:, 0], tab[:, 1]), L5)
resid = L6 - toeL                                       # (b) plus 8-bit rounding; the toe itself is taken off on both sides
bsteps = {"left (cushion side, x < 2232)": [], "bottom (duvet side, y >= 912)": [], "top/right (lit pillowcase)": []}
for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    yy, xx = np.nonzero(inner)
    y2, x2 = yy + dy, xx + dx
    ok = (y2 >= 0) & (y2 < H) & (x2 >= 0) & (x2 < W)
    yy, xx, y2, x2 = yy[ok], xx[ok], y2[ok], x2[ok]
    o = ~reg[y2, x2]
    yy, xx, y2, x2 = yy[o], xx[o], y2[o], x2[o]
    st = resid[yy, xx] - resid[y2, x2]
    for a, b, s_ in zip(yy, xx, st):
        side = "left (cushion side, x < 2232)" if b < 2232 else ("bottom (duvet side, y >= 912)" if a >= 912 else "top/right (lit pillowcase)")
        bsteps[side].append(s_)
for k, v in bsteps.items():
    v = np.abs(np.array(v))
    bsteps[k] = dict(pairs=int(v.size), abs_step_p50=r(np.percentile(v, 50)), p90=r(np.percentile(v, 90)), p99=r(np.percentile(v, 99)),
                     max=r(v.max()), share_gt_1=r((v > 1).mean(), 3))
out["mask_edge_step_from_b_only_L"] = bsteps
out["mask_edge_added_step_note"] = ("mask_edge_added_step_L mixes in the toe (a dark px inside next to a brighter one outside gets the "
                                    "larger toe lift); mask_edge_step_from_b_only_L takes QA's empirical toe off both sides")
ring2 = reg & ~cv2.erode(reg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
out["b_residual_on_inner_2px"] = dict(px=int(ring2.sum()), p50=r(np.percentile(bres[ring2], 50)), p90=r(np.percentile(bres[ring2], 90)),
                                      p99=r(np.percentile(bres[ring2], 99)), max=r(bres[ring2].max()))
json.dump(out, open(os.path.join(OUT, "data", "b-numbers.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
