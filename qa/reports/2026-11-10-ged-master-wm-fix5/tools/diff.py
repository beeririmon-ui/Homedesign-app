"""
qa-agent 2026-11-10: G-ED.8 on warm-modern-MB-A-fix5 (P6b), independent of render-agent's numbers.
fix5 against fix4 (the last frame QA checked, qa/reports/2026-11-10-ged-master-fix6.json), in 8-bit RGB as stored:
  - changed px at > 0 and > 2 levels (any channel), their box, and connected areas on a 15 px dilation;
  - the same counts outside render-agent's composite mask (raw/P6b-comp-mask.png), outside the crop, and in bands just outside the mask;
  - P6b-input.png against the fix4 crop (the job ran on the frame QA had passed);
  - the changed px in render-agent's protect-v2 and in the original protect mask (raw/P6b-protect.png), split into the gap band and the
    rest; QA's own lumbar and duvet checks are in lumbar.py and duvet.py.
Run order: diff.py, lumbar.py, duvet.py, ring.py, gap.py, cast_shadow.py, fidelity.py, shadow_floor.py, dl1_wm.py, seams.py, build.py;
before build.py, G-ED.11/12: qa/reports/2026-11-07-gate-g-ed/tools/guardrails.py on fix5, fix4, MB-A and raw/P6b-seedream.png --out data/guardrails.json.
Usage: ~/.venvs/motion/bin/python -I diff.py. Writes data/diff.json and overlays/diff-map.jpg (the change x3 as a heat map, the comp mask outline in cyan).
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
B = os.path.join(REPO, "assets/renders/master/editorial-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5")
CROP = (1380, 520, 2700, 1086)


def rgb(p):
    return np.asarray(Image.open(os.path.join(B, p)).convert("RGB")).astype(np.int16)


def m(p):
    return np.asarray(Image.open(os.path.join(B, p))) > 127


def lab(x8):
    c = x8 / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


f3, f4, f5 = rgb("warm-modern/warm-modern-MB-A-fix3.png"), rgb("warm-modern/warm-modern-MB-A-fix4.png"), rgb("warm-modern/warm-modern-MB-A-fix5.png")
H, W = f4.shape[:2]
x0, y0, x1, y1 = CROP
inp = rgb("warm-modern/raw/P6b-input.png")
comp = m("warm-modern/raw/P6b-comp-mask.png")
prot_c = m("warm-modern/raw/P6b-protect.png")          # crop px
protv2_c = m("warm-modern/raw/P6b-protect-v2.png")     # crop px
hand_c = m("warm-modern/raw/P6b-mask.png")             # crop px
seg_c = m("warm-modern/raw/P6b-seg-mask.png")          # crop px


def to_frame(mc):
    z = np.zeros((H, W), bool)
    z[y0:y1, x0:x1] = mc
    return z


prot, protv2, hand, segm = (to_frame(a) for a in (prot_c, protv2_c, hand_c, seg_c))
d = np.abs(f5 - f4).max(2)
ch0, ch2 = d > 0, d > 2
ys, xs = np.nonzero(ch0)
out = {"pair": "warm-modern-MB-A-fix4.png -> warm-modern-MB-A-fix5.png",
       "input_is_fix4_crop": bool((inp == f4[y0:y1, x0:x1]).all()),
       "fix4_vs_fix3_gt2_px": int((np.abs(f4 - f3).max(2) > 2).sum()),
       "changed_px_gt0": int(ch0.sum()), "changed_px_gt2": int(ch2.sum()),
       "changed_box_gt0": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
       "max_abs_change": int(d.max()),
       "comp_mask_px": int(comp.sum()),
       "changed_gt0_outside_comp_mask": int((ch0 & ~comp).sum()),
       "changed_gt0_outside_crop": int(ch0.sum() - ch0[y0:y1, x0:x1].sum()),
       "comp_mask_px_unchanged": int((comp & ~ch0).sum()),
       "comp_mask_outside_hand_mask": int((comp & ~hand).sum()),
       "changed_in_protect_v2": int((ch0 & protv2).sum()),
       "changed_in_prepared_protect": int((ch0 & prot).sum())}
# bands just outside the mask: anything there would be a leak the mask file does not show
for r in (1, 3, 8, 20):
    ring = cv2.dilate(comp.astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)).astype(bool) & ~comp
    out[f"changed_gt0_in_{r}px_band_outside_mask"] = int((ch0 & ring).sum())
# connected areas (G-ED.8 tool: > 2 levels, 15 px dilation)
n, lbl, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(ch2.astype(np.uint8), np.ones((15, 15), np.uint8)), connectivity=8)
comps = []
for i in range(1, n):
    a, b, w, h, _ = st[i]
    px = int((ch2 & (lbl == i)).sum())
    comps.append(dict(bbox=[int(a), int(b), int(a + w), int(b + h)], changed_px=px,
                      inside_crop=bool(a >= x0 and b >= y0 and a + w <= x1 and b + h <= y1)))
out["components_gt2_15px"] = sorted(comps, key=lambda c: -c["changed_px"])

# the lumbar and the duvet with QA's own masks: lumbar.py and duvet.py (run after this file)
# the prepared protect, split: the gap band and the rest (the back pillows' ring)
GAP_BAND = np.array([(1998, 696), (2022, 696), (2062, 818), (1998, 818)], np.int32)
gap = np.zeros((H, W), np.uint8)
cv2.fillPoly(gap, [GAP_BAND], 1)
gap = gap.astype(bool)
pc = ch0 & prot
out["prepared_protect_split"] = {"gap_band": int((pc & gap).sum()), "rest (the back pillows' ring round the old pillowcases)": int((pc & ~gap).sum())}
# the ring render-agent declared (12 px beyond the segments) on the back pillows: how far the changes reach from the segments
dist = cv2.distanceTransform((~segm).astype(np.uint8), cv2.DIST_L2, 5)
far = ch0 & ~segm & ~gap
out["changed_outside_segments_distance_px"] = dict(px=int(far.sum()), p50=round(float(np.percentile(dist[far], 50)), 1),
                                                   p99=round(float(np.percentile(dist[far], 99)), 1), max=round(float(dist[far].max()), 1))
json.dump(out, open(os.path.join(OUT, "data", "diff.json"), "w"), indent=1)

# overlays: the diff map (the bed head, 100 %) and the mask with its 3 px outside band
bx = (1380, 620, 2700, 1000)
crop = f5[bx[1]:bx[3], bx[0]:bx[2]].astype(np.uint8).copy()
heat = np.clip(d[bx[1]:bx[3], bx[0]:bx[2]] * 3, 0, 255).astype(np.uint8)
hm = cv2.applyColorMap(heat, cv2.COLORMAP_INFERNO)[..., ::-1]
mix = (crop * 0.35 + hm * 0.65).astype(np.uint8)
cm = comp[bx[1]:bx[3], bx[0]:bx[2]]
edge = cm & ~cv2.erode(cm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
mix[edge] = (0, 220, 255)
Image.fromarray(mix).save(os.path.join(OUT, "overlays", "diff-map.jpg"), quality=92)
print(json.dumps({k_: v for k_, v in out.items() if k_ != "components_gt2_15px"}, indent=1))
print(out["components_gt2_15px"][:10])
