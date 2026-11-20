#!/usr/bin/env python3
"""
kd_plate.py: a D1 / D2 empty plate from the model's still (render-agent, 2026-11-20; 0 tokens). Global steps, nothing local:
1. Lock: an affine ECC fit of the still onto the plate's model input (the recoloured clay), masked to the architecture, the kitchen run
   and the fixed furniture of the clay's id pass. Residuals on the analytic lock lines are reported (canvas px).
2. One house: the materials read against the approved stills of the house (the living room base.png: plaster, oak, walnut; the hall
   ht2.png: the honed limestone). Reported per material (median Lab, dE00); corrected only where a material's chroma is off by more than
   dE00 3 (a* b* shift in that material's clay mask, feathered 3 px; L* is the light and stays the model's).
3. WM-G1 / MP-I2: a toe on L* only, (0, 0) (p0.5, 11.5) (12, 16) (30, 30) (100, 100) when the 16:9 frame's p0.5 is under 11 (MB1's
   curve); nothing above L* 30 changes. The curve is recorded (mandatory for every layer cut from this plate).
  python3 kd_plate.py D1 raw/plate-D1-r1.png
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
TARGET_L = {"D1": 84.0}
PLASTER_ALL = (1, 2, 3, 4, 5, 6, 7, 9, 12, 16, 37)
PLASTER_WALLS = (1, 2, 3, 4, 5, 6, 7, 9, 12, 16)


def Y_of(L):
    return ((L + 16) / 116) ** 3 if L > 8 else L / 903.3


CURVE = {"xp": [0, 30, 45, 52, 61, 68, 81, 96, 100], "fp": [0, 40, 62, 72, 82, 90.5, 91.5, 97, 100]}
BONE = (40, 41)
CURVES = {"D1": None, "D2": json.loads(os.environ.get("KD_D2_CURVE", "null"))}


def plaster_light(e, lab, ids, fr, curve=None):
    curve = curve or CURVE
    pm = np.isin(ids, PLASTER_ALL)
    bm = np.isin(ids, BONE)
    out = {}
    lab = lab.copy()
    for name, m, off in (("plaster", pm, 0.0), ("bone talls", bm, -3.0)):
        if m.sum() < 100:
            continue
        core = C.ero(m, 2)
        w = C.blur(core.astype(np.float64), 25)
        Ls = C.blur(lab[..., 0] * core, 25) / np.maximum(w, 1e-6)
        abs_ = [C.blur(lab[..., c] * core, 25) / np.maximum(w, 1e-6) for c in (1, 2)]
        Lt = np.interp(Ls, curve["xp"], curve["fp"]) + off
        g = np.vectorize(Y_of)(np.clip(Lt, 9, 100)) / np.vectorize(Y_of)(np.clip(Ls, 9, 100)) if False else \
            (((np.clip(Lt, 9, 100) + 16) / 116) ** 3) / (((np.clip(Ls, 9, 100) + 16) / 116) ** 3)
        sim = np.sqrt((lab[..., 0] - Ls) ** 2 + (lab[..., 1] - abs_[0]) ** 2 + (lab[..., 2] - abs_[1]) ** 2) < 12
        wt = C.blur((C.dil(m, 4) & sim & (w > 0.02)).astype(np.float64), 1.2)
        wt = np.where(C.ero(m, 1), 1.0, wt)
        Y = ((np.clip(lab[..., 0], 0, 100) + 16) / 116) ** 3
        Ynew = Y * (1 + (g - 1) * wt)
        Lnew = np.where(Ynew > 216 / 24389, 116 * np.cbrt(Ynew) - 16, 903.3 * Ynew)
        before = float(np.median(lab[..., 0][core & K.frame_mask()]))
        lab[..., 0] = np.where(wt > 0, Lnew, lab[..., 0])
        out[name] = dict(median_L_before=round(before, 1), median_L_after=round(float(np.median(lab[..., 0][core & K.frame_mask()])), 1),
                         gain_p5_p50_p95=[round(float(v), 3) for v in np.percentile(g[core], [5, 50, 95])])
    out["curve"] = curve
    out["regions_after"] = {}
    for nm, g_, box in (("east wall by the window", (1,), (500, 0, 800, 1100)), ("east wall at the corner", (1,), (1100, 0, 1180, 1100)),
                        ("rounded corner", (5,), None), ("south wall above the shelves", (2,), None), ("hood", (37,), None)):
        m = C.ero(np.isin(ids, g_), 4) & K.frame_mask()
        if box:
            bb = np.zeros_like(m)
            bb[box[1]:box[3], box[0]:box[2]] = True
            m &= bb
        if m.sum() > 50:
            out["regions_after"][nm] = round(float(np.median(lab[..., 0][m])), 1)
    return lab, out


def shift_surface(lab, ids, g, dL=0.0, ab=None):
    m = np.isin(ids, g)
    core = C.ero(m, 2)
    w = C.blur(core.astype(np.float64), 15)
    Ls = C.blur(lab[..., 0] * core, 15) / np.maximum(w, 1e-6)
    abs_ = [C.blur(lab[..., c] * core, 15) / np.maximum(w, 1e-6) for c in (1, 2)]
    sim = np.sqrt((lab[..., 0] - Ls) ** 2 + (lab[..., 1] - abs_[0]) ** 2 + (lab[..., 2] - abs_[1]) ** 2) < 14
    wt = C.blur((C.dil(m, 3) & sim & (w > 0.02)).astype(np.float64), 1.0)
    wt = np.where(C.ero(m, 1), 1.0, wt)
    Y = ((np.clip(lab[..., 0], 0, 100) + 16) / 116) ** 3
    L0 = float(np.median(lab[..., 0][core]))
    gain = (((L0 + dL + 16) / 116) ** 3) / (((L0 + 16) / 116) ** 3)
    Yn = Y * (1 + (gain - 1) * wt)
    lab = lab.copy()
    lab[..., 0] = np.where(wt > 0, np.where(Yn > 216 / 24389, 116 * np.cbrt(Yn) - 16, 903.3 * Yn), lab[..., 0])
    if ab is not None:
        a0, b0 = float(np.median(lab[..., 1][core])), float(np.median(lab[..., 2][core]))
        lab[..., 1] += wt * (ab[0] - a0)
        lab[..., 2] += wt * (ab[1] - b0)
    return lab, dict(ids=list(g), L_before=round(L0, 1), L_after=round(float(np.median(lab[..., 0][core])), 1), gain=round(float(gain), 3),
                     ab_after=[round(float(np.median(lab[..., c][core])), 1) for c in (1, 2)])


def d2_surfaces(lab, ids):
    out = {}
    p1 = C.load(os.path.join(K.ST, "plate-D1.png"))
    maps = K.map_between("D1", "D2")
    w1 = C.to_lab(np.clip(K.warp(p1, "D1", "D2", maps=maps), 0, 1))
    ov = C.ero(K.warp(K.frame_mask(), "D1", "D2", maps=maps) & K.frame_mask(), 8)
    m = C.ero(ids == 38, 2) & ov
    dL = float(np.median(w1[..., 0][m]) - np.median(lab[..., 0][m]))
    lab, out["walnut shelves"] = shift_surface(lab, ids, (38,), dL=dL)
    out["walnut shelves"]["dL_to_D1"] = round(dL, 2)
    esp = K.lab_hex("#2E2824")
    L0 = float(np.median(lab[..., 0][C.ero(ids == 43, 2)]))
    lab, out["oven front"] = shift_surface(lab, ids, (43,), dL=max(0.0, 17.0 - L0), ab=(float(esp[1]), float(esp[2])))
    return lab, out


MAT = {"plaster (walls)": (1, 2, 3, 5), "hood (plaster)": (37,), "oak floor": (10,), "walnut (table top)": (20,), "walnut (chairs, bench, shelves)": (21, 22, 24, 38),
       "limestone (worktop, splash, sill)": (14, 32, 33), "taupe lowers": (30,), "bone talls": (40, 41), "bronze frame": (13,),
       "espresso oven": (43,), "walnut niche": (42,)}
HOUSE = "/home/user/homedesign-app/assets/renders/"
REF_BOXES = {   # (file, box x0 y0 x1 y1, what): the approved stills' materials (canvas px of the file)
    "hood (plaster)": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (1300, 300, 2200, 800)),
    "plaster (walls)": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (1300, 300, 2200, 800)),
    "oak floor": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (2350, 1390, 2700, 1500)),
    "walnut (table top)": ("living-room/warm-modern/phase2-2026-11-10/layers/base.png", (1400, 1215, 1900, 1290)),
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


def main(fr, raw, patch=None):
    ids = K.ids(f"{fr}-plate")
    stable = C.ero(np.isin(ids, ARCH), 3)
    stable &= K.frame_mask()
    e, rl = K.ecc_lock(os.path.join(K.ST, raw), os.path.join(K.ST, "inputs", f"plate-{fr}-input.png"), stable)
    steps = [dict(step=1, what="lock: ECC affine onto inputs/plate-<fr>-input.png, masked to the clay's architecture, kitchen and fixed furniture", **rl)]
    if patch:
        # 1b. a mask edit of the still (the splashback continued to the shelves, KD-8): locked onto the locked still, its light matched
        #     outside the band (MP-I1's gain field), and used only inside the clay's splash mask (id 33, +4 px), never on the tap (id 35)
        band = C.dil(ids == 33, 4) & ~C.dil(ids == 35, 3)
        st2 = C.ero(np.isin(ids, ARCH), 3) & ~C.dil(band, 40) & K.frame_mask()
        pe, prl = K.ecc_lock(os.path.join(K.ST, patch), e, st2)
        g = C.gain_field(pe, e, st2)
        pe = C.srgb(np.clip(C.lin(pe) * g, 0, 1))
        w = C.blur(band.astype(np.float64), 1.5)[..., None]
        e = pe * w + e * (1 - w)
        steps.append(dict(step="1b", what="KD-8: the splashback continued to the shelves from the mask edit, inside the clay's splash mask only", source=patch,
                          mask_px=int(band.sum()), gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])], **prl))
    lab = C.to_lab(e)
    refs = ref_lab()
    # 2a. one house, the light of the plaster: the model drew the walls grey (L* 61-68) where 1.1 / 1.5 want them bright (the east wall
    #     90-94 by the window, 80-85 at the rounded corner; 1.1: plaster about 91, stone 81, taupe 58, oak 49), while its stone, taupe,
    #     oak and walnut already read the house (MEASURED in the json). A smooth luminance field on the plaster only (walls, corner,
    #     ceiling, hood, reveals, skirting; the bone talls 3 L* below it): the plaster's local L* (normalised blur, sigma 25 px) mapped by
    #     one monotonic curve (CURVE), applied as a gain in linear light, so the trowel texture stays. Applied where a pixel reads as the
    #     local plaster (dE76 under 12 from its smoothed colour) within 4 px of the clay's plaster mask: no halo where the still and the
    #     clay differ by a few pixels. D2 takes the curve that matches it to the finished D1 on the overlap (one camera point).
    lab, rec2a = plaster_light(e, lab, ids, fr, curve=CURVES.get(fr))
    e = np.clip(C.from_lab(lab), 0, 1)
    steps.append(dict(step="2a", what="one house: the plaster's light (a luminance field on the plaster only)", **rec2a))
    # 2c. D2 only, two surfaces against the finished D1 / the spec: the walnut shelves' L* to D1's on the overlap (dE00 4.1 before);
    #     the oven front to matte espresso #2E2824 (KD-11: the model drew it near-black and neutral, L* 10.5 a* 0 b* 2.6)
    if fr == "D2":
        lab, rec2c = d2_surfaces(lab, ids)
        steps.append(dict(step="2c", what="D2: the walnut shelves matched to D1 on the overlap; the oven front to espresso", **rec2c))
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
                m = C.blur(C.dil(np.isin(ids, PLASTER_WALLS if k.startswith("plaster") else MAT[k]), 2).astype(np.float64), 3.0)
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
    main(*sys.argv[1:4])
