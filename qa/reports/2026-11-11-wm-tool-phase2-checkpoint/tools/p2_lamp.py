#!/usr/bin/env python3
"""
qa-agent 2026-11-11: the floor lamp, two conditions of docs/proposals/wm-phase2-f3-decisions-2026-11-11.md.
  §1 F3: on the real layers, sets A and B (and C): where the lamp's base meets the sofa (fixed furniture alpha, not covered by a cushion set),
     is there a line of dL* > 10 along >= 8 px?
  §5 the shade "looks lit": the designer's five targets, measured on the shade fabric (lamp alpha 255, rows of the cone) against a wall ring
     15-40 px around the shade at the same rows: (1) left third median >= right third median + 5; (2) bottom 15 % of the shade height
     <= right-third median - 5; (3) left third <= ring median + 4 and right third <= ring median; (4) median b* <= ring b* + 4 and no px
     >= ring b* p95 + 8; (5) folds kept (high-pass std, only reported). Also: is the layer file the steps-1-3 one (no toning applied)?
Writes data/floor-lamp.json.   ~/.venvs/motion/bin/python -I p2_lamp.py
"""
import hashlib
import json
import os

import cv2
import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
OUT = os.path.join(REPO, "qa/reports/2026-11-11-wm-tool-phase2-checkpoint")
man = json.load(open(os.path.join(P2, "layers/manifest-r3.json")))
byid = {l_["id"]: l_ for l_ in man["layers"]}
f = os.path.join(P2, "layers", byid["floor-lamp"]["file"])
lamp = np.asarray(Image.open(f)).astype(np.float32)
a = lamp[..., 3]
res = {"layer_file": byid["floor-lamp"]["file"], "layer_mtime": os.path.getmtime(f),
       "layer_sha256": hashlib.sha256(open(f, "rb").read()).hexdigest(),
       "manifest_pass": byid["floor-lamp"].get("pass_"), "manifest_file_origin": byid["floor-lamp"].get("file_origin")}
other = [p for p in os.listdir(os.path.dirname(f)) if p.endswith(".png")]
res["files_in_folder"] = sorted(other)


def labimg(rgb):
    return cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


# --- §5 shade
rows = np.nonzero((a > 0).sum(1))[0]
width = (a >= 255).sum(1)
# the cone: from the top of the layer down to where the width collapses to the stem (< 40 px)
top = int(rows.min())
y = top
while y < a.shape[0] and (width[y] >= 40 or y < top + 10):
    y += 1
bot = y
res["shade_rows"] = [top, bot]
S = np.asarray(Image.open(os.path.join(P2, "graded/default-scene-r3-set-B-graded-v3c.png")).convert("RGB")).astype(np.float32)
LAB = labimg(S)
shade = np.zeros(a.shape, bool)
shade[top:bot] = a[top:bot] >= 255
shade = cv2.erode(shade.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
xs = np.nonzero(shade.any(0))[0]
x0, x1 = int(xs.min()), int(xs.max())
w3 = (x1 - x0) / 3
cols = np.arange(a.shape[1])[None, :].repeat(a.shape[0], 0)
left = shade & (cols < x0 + w3)
right = shade & (cols > x1 - w3)
h = bot - top
bottom = shade & (np.arange(a.shape[0])[:, None] >= bot - 0.15 * h)
d = cv2.distanceTransform((a == 0).astype(np.uint8), cv2.DIST_L2, 5)
ring = (d >= 15) & (d <= 40)
ring[:top] = False
ring[bot:] = False
# keep the ring on the wall: drop anything under another product or the fixed furniture
for l_ in man["layers"]:
    if "product" in l_ and l_["id"] != "floor-lamp":
        ring &= np.asarray(Image.open(os.path.join(P2, "layers", l_["file"])))[..., 3] == 0
L, bb = LAB[..., 0], LAB[..., 2]
med = lambda m, ch=L: float(np.median(ch[m]))
ringL, ringb = med(ring), med(ring, bb)
leftL, rightL, botL = med(left), med(right), med(bottom)
shade_b = med(shade, bb)
ring_b95 = float(np.percentile(bb[ring], 95))
hp = L - cv2.GaussianBlur(L, (0, 0), 3)
res["shade"] = dict(px=int(shade.sum()), ring_px=int(ring.sum()), ring_L=round(ringL, 2), ring_b=round(ringb, 2), ring_b_p95=round(ring_b95, 2),
                    left_third_L=round(leftL, 2), right_third_L=round(rightL, 2), bottom15_L=round(botL, 2), shade_b=round(shade_b, 2),
                    shade_L_p50_p95_max=[round(float(np.percentile(L[shade], q)), 2) for q in (50, 95, 100)],
                    px_b_ge_ring_p95_plus8=int((bb[shade] >= ring_b95 + 8).sum()), highpass_std=round(float(hp[shade].std()), 3))
t = {
    "1 window gradient: left >= right + 5": dict(value=round(leftL - rightL, 2), pass_=leftL - rightL >= 5),
    "2 bottom/inside <= right - 5": dict(value=round(botL - rightL, 2), pass_=botL <= rightL - 5),
    "3a left third <= ring + 4": dict(value=round(leftL - ringL, 2), pass_=leftL <= ringL + 4),
    "3b right third <= ring": dict(value=round(rightL - ringL, 2), pass_=rightL <= ringL),
    "4a median b* <= ring b* + 4": dict(value=round(shade_b - ringb, 2), pass_=shade_b <= ringb + 4),
    "4b no px b* >= ring p95 + 8": dict(value=int((bb[shade] >= ring_b95 + 8).sum()), pass_=int((bb[shade] >= ring_b95 + 8).sum()) == 0),
}
res["designer_targets"] = t
res["all_targets_met"] = all(v["pass_"] for v in t.values())

# --- §1 F3: base vs sofa arm
fur = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3]
f3 = {}
for s in "ABC":
    Sx = np.asarray(Image.open(os.path.join(P2, f"graded/default-scene-r3-set-{s}-graded-v3c.png")).convert("RGB")).astype(np.float32)
    Lx = labimg(Sx)[..., 0]
    cs = np.asarray(Image.open(os.path.join(P2, "layers", man["slot_cushions"]["sets"][s]["layer"])))[..., 3]
    lampm = (a > 127) & (cs < 128)
    lampm[: int(np.nonzero(width > 0)[0].max()) - 90] = False   # the base only (lowest ~90 rows)
    sofa = (fur > 127) & (cs < 128) & (a < 128)
    edge_l = cv2.dilate(sofa.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    contact = lampm & edge_l
    n = int(contact.sum())
    rec = dict(contact_px=n)
    if n:
        ys_, xs_ = np.nonzero(contact)
        dl = []
        for yy, xx in zip(ys_, xs_):
            win = sofa[max(0, yy - 2):yy + 3, max(0, xx - 2):xx + 3]
            sw = Lx[max(0, yy - 2):yy + 3, max(0, xx - 2):xx + 3][win]
            if sw.size:
                dl.append(abs(float(Lx[yy, xx]) - float(np.median(sw))))
        dl = np.array(dl)
        rows_hi = len(set(int(v) for v in ys_[np.array([d_ > 10 for d_ in dl])])) if len(dl) else 0
        rec.update(dL_median=round(float(np.median(dl)), 2), dL_max=round(float(dl.max()), 2), px_dL_gt10=int((dl > 10).sum()),
                   rows_with_dL_gt10=rows_hi, contact_box=[int(xs_.min()), int(ys_.min()), int(xs_.max()), int(ys_.max())],
                   sofa_L_near=round(float(np.median(Lx[edge_l & sofa])), 1) if (edge_l & sofa).any() else None)
    rec["line_rule_hit"] = bool(n and rec.get("rows_with_dL_gt10", 0) >= 8)
    f3[s] = rec
res["f3_base_vs_sofa"] = f3
json.dump(res, open(os.path.join(OUT, "data/floor-lamp.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
