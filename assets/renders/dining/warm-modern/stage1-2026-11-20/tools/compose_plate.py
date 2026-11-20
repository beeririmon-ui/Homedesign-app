#!/usr/bin/env python3
"""
compose_plate.py: a D1 / D2 empty plate from the model's still (render-agent, 2026-11-20; 0 tokens). Global steps, nothing local:
1. Lock: an affine ECC fit of the still onto the plate's model input (the recoloured clay), masked to the architecture, the kitchen run
   and the fixed furniture of the clay's id pass. Residuals on the analytic lock lines are reported (canvas px).
2. One house: the materials read against the approved stills of the house (the living room base.png: plaster, oak, walnut; the hall
   ht2.png: the honed limestone). Reported per material (median Lab, dE00); corrected only where a material's chroma is off by more than
   dE00 3 (a* b* shift in that material's clay mask, feathered 3 px; L* is the light and stays the model's).
3. WM-G1 / MP-I2: a toe on L* only, (0, 0) (p0.5, 11.5) (12, 16) (30, 30) (100, 100) when the 16:9 frame's p0.5 is under 11 (MB1's
   curve); nothing above L* 30 changes. The curve is recorded (mandatory for every layer cut from this plate).
  python3 compose_plate.py D1 raw/plate-D1-r1.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

C = K.C
H, W = K.H, K.W
ARCH = (1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33, 36, 37, 38, 40, 41, 42, 43)
MAT = {"plaster (walls)": (1, 2, 3, 5), "hood (plaster)": (37,), "oak floor": (10,), "walnut (table, chairs, bench, shelves)": (20, 21, 22, 24, 38),
       "limestone (worktop, splash, sill)": (14, 32, 33), "taupe lowers": (30,), "bone talls": (40, 41), "bronze frame": (13,),
       "espresso oven": (43,), "walnut niche": (42,)}
HOUSE = "/home/user/homedesign-app/assets/renders/"
REF_BOXES = {   # (file, box x0 y0 x1 y1, what): the approved stills' materials (canvas px of the file)
    "plaster (walls)": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (1300, 300, 2200, 800)),
    "oak floor": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (2350, 1390, 2700, 1500)),
    "walnut (table, chairs, bench, shelves)": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (1400, 1215, 1900, 1290)),
    "limestone (worktop, splash, sill)": ("hall/warm-modern/hall-2026-11-18/ht2.png", (1700, 300, 2300, 900)),
}


def med(lab, m):
    v = lab[m]
    lo, hi = np.percentile(v[:, 0], (20, 80))
    return np.median(v[(v[:, 0] >= lo) & (v[:, 0] <= hi)], 0)


def ref_lab():
    out = {}
    for k, (f, b) in REF_BOXES.items():
        a = C.load(HOUSE + f)
        out[k] = med(C.to_lab(a[b[1]:b[3], b[0]:b[2]]), np.ones((b[3] - b[1], b[2] - b[0]), bool))
    return out


def readings(lab, ids):
    out = {}
    fm = K.frame_mask()
    for k, g in MAT.items():
        m = C.ero(np.isin(ids, g), 5) & fm
        if m.sum() > 300:
            out[k] = med(lab, m)
    return out


def lock_residuals(rgb, fr):
    """per lock line: the strongest gradient across the line near its analytic position (+-12 px), its median offset"""
    import cv2
    J = json.load(open(os.path.join(K.CLAY, f"{fr}-lock-target.json")))
    y = cv2.GaussianBlur(C.luma(rgb).astype(np.float32), (0, 0), 1.0)
    gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
    out = {}
    for name, L in J["lines"].items():
        (x0, y0), (x1, y1) = L["px_ends"]
        d = np.array([x1 - x0, y1 - y0], float)
        n = np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-6)
        offs = []
        for x, yy, seen in L["samples"]:
            if not seen:
                continue
            best, bo = 0, None
            for o in np.arange(-12, 12.5, 0.5):
                px, py = x + n[0] * o, yy + n[1] * o
                if 1 <= px < W - 1 and 1 <= py < H - 1:
                    g = abs(gx[int(py), int(px)] * n[0] + gy[int(py), int(px)] * n[1])
                    if g > best:
                        best, bo = g, o
            if bo is not None and best > 4:
                offs.append(bo)
        if len(offs) >= 5:
            out[name] = dict(median_px=round(float(np.median(offs)), 1), n=len(offs))
    return out


def main(fr, raw):
    ids = K.ids(f"{fr}-plate")
    stable = C.ero(np.isin(ids, ARCH), 3)
    stable &= K.frame_mask()
    e, rl = K.ecc_lock(os.path.join(K.ST, raw), os.path.join(K.ST, "inputs", f"plate-{fr}-input.png"), stable)
    steps = [dict(step=1, what="lock: ECC affine onto inputs/plate-<fr>-input.png, masked to the clay's architecture, kitchen and fixed furniture", **rl)]
    lab = C.to_lab(e)
    refs = ref_lab()
    rb = readings(lab, ids)
    fixes = {}
    table = {}
    for k, v in rb.items():
        row = dict(plate=[round(float(x), 1) for x in v])
        if k in refs:
            r = refs[k]
            row["house"] = [round(float(x), 1) for x in r]
            row["dE00"] = round(float(C.de00(tuple(v), tuple(r))), 2)
            row["dE00_chroma_only"] = round(float(C.de00((r[0], v[1], v[2]), tuple(r))), 2)
            if row["dE00_chroma_only"] > 3.0:
                m = C.blur(C.dil(np.isin(ids, MAT[k]), 2).astype(np.float64), 3.0)
                lab[..., 1] += m * (r[1] - v[1])
                lab[..., 2] += m * (r[2] - v[2])
                fixes[k] = dict(shift_ab=[round(float(r[1] - v[1]), 2), round(float(r[2] - v[2]), 2)], why="chroma off the house by more than dE00 3")
        table[k] = row
    after = {k: [round(float(x), 1) for x in v] for k, v in readings(lab, ids).items()}
    steps.append(dict(step=2, what="one house: per material against the living room's base.png and the hall's ht2.png", readings=table, fixes=fixes,
                      after=after))
    lab[..., 0] = np.clip(lab[..., 0], 0, 100)
    fm = K.frame_mask()
    p05 = float(np.percentile(lab[..., 0][fm], 0.5))
    if 0.5 < p05 < 11.0:
        xp, fp = [0, p05, 12, 30, 100], [0, 11.5, 16, 30, 100]
        lab[..., 0] = np.interp(lab[..., 0], xp, fp)
        toe = dict(applied=True, p05_before=round(p05, 2), xp=[round(v, 3) for v in xp], fp=fp, curve=f"(0, 0) ({p05:.2f}, 11.5) (12, 16) (30, 30) (100, 100)")
    else:
        toe = dict(applied=False, p05=round(p05, 2), note="within WM-G1 (11-14) as it came")
    steps.append(dict(step=3, what="WM-G1 / MP-I2 toe on L*", **toe))
    rgb = np.clip(C.from_lab(lab), 0, 1)
    out = os.path.join(K.ST, f"plate-{fr}.png")
    K.save(out, rgb)
    q = C.q(rgb)
    K.frame_crop(q).save(os.path.join(K.ST, f"plate-{fr}-frame.png"))
    p05_after = float(np.percentile(C.to_lab(rgb)[..., 0][fm], 0.5))
    res = lock_residuals(rgb, fr)
    rec = dict(frame=fr, source=raw, out=os.path.relpath(out, K.ST), steps=steps, black_point_p05=round(p05_after, 2),
               lock_lines_after=res, mandatory_for_derived="step 3's curve (MP-I2) on every layer cut from this plate")
    json.dump(rec, open(os.path.join(K.ST, f"plate-{fr}-compose.json"), "w"), indent=1)
    print(json.dumps(rl["ecc"]), json.dumps(table), json.dumps(fixes), round(p05_after, 2))
    print(json.dumps(res))


if __name__ == "__main__":
    main(*sys.argv[1:3])
