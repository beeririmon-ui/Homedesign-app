#!/usr/bin/env python3
"""
compose_plate_kids.py: the K-boy empty plate from the model's still (render-agent, 2026-11-24; 0 tokens). Global steps only, as the work
room's compose_plate_work.py:
1. Lock: an affine ECC fit of the still onto the plate's model input (the recoloured clay), masked to the architecture and the fixed
   furniture of the clay's id pass.
2. One house, read per material against MB0's plate.png (the same plaster, oak, walnut, bronze and limestone under the same north light):
   median Lab of the clay-id masks (the middle half of L*); a material whose chroma is off by more than dE00 3 gets an a* b* shift in its
   mask (L* is the light and stays the model's). The band is read against the plaster just above it (the same light): its implied albedo
   (band / plaster x #ECE5DA, per channel in linear light) against #A8A88E; a* b* moved toward the target when off by more than dE00 3.
   (2026-11-24, later: each wall's band read on its own wall, east and north; a band off by more than dE00 3 is multiplied per channel
   in linear light by #A8A88E / its implied albedo, the paint's hue and lightness, the light kept.)
3. WM-G1 / MP-I2: a toe on L* only, (0, 0) (p0.5, 11.5) (12, 16) (30, 30) (100, 100) when the 16:9 frame's p0.5 is under 11; above 14 the
   knots pull it to 12.5; a* b* kept; nothing above L* 30 changes. Recorded as 'mandatory_for_derived'.
  python3 compose_plate_kids.py raw/plate-K-boy-r1.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402

C = K.C
H, W = K.H, K.W
ST = K.ST["boy"]
MB0 = "/home/user/homedesign-app/assets/renders/master/warm-modern/stage1-2026-11-17/plate.png"
MB0_IDS = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/MB0-plate-id.png"
SURF = {"plaster": ((1, 2), (1, 2, 5)), "oak": ((10,), (10,)), "walnut, boards and frame": ((20, 21), (20, 21, 24, 25)),
        "walnut, desk and chair": ((23, 24, 25), (20, 21, 24, 25)), "bronze": ((13,), (13,)), "limestone slab": ((14,), (14,))}
FIX = {"plaster", "oak", "walnut, boards and frame", "walnut, desk and chair", "limestone slab"}
SPEC_HEX = {"limestone slab": "#D8C8AE"}     # the slab is read against the binding hex (MB0's slab reads washed out at L* 92)


def rd(lab, ids, g, ero=4, pct=(25, 75)):
    m = C.ero(np.isin(ids, g), ero) & K.frame_mask()
    if m.sum() < 50:
        return None, None
    v = lab[m]
    lo, hi = np.percentile(v[:, 0], pct)
    return np.median(v[(v[:, 0] >= lo) & (v[:, 0] <= hi)], 0), m


WALLS = {"east": dict(band=5, plaster=1, xr=(900, 2500, 4), ids=(5, 19)), "north": dict(band=8, plaster=2, xr=(100, 900, 3), ids=(8,))}


def band_reading(rgb, ids, wall="east", target="#A8A88E"):
    """the band's implied albedo: just below / just above the line Z 1.25 on one wall, column by column (the same light)"""
    wd = WALLS[wall]
    lin = C.lin(rgb)
    below, above = [], []
    for x in range(*wd["xr"]):
        col = ids[:, x]
        ys5 = np.nonzero(col == wd["band"])[0]
        ys1 = np.nonzero(col == wd["plaster"])[0]
        if len(ys5) < 30 or len(ys1) < 30:
            continue
        yl = ys5.min()
        if abs(ys1.max() - yl) > 3:
            continue
        below.append(lin[yl + 6:yl + 26, x].mean(0))
        above.append(lin[yl - 26:yl - 6, x].mean(0))
    if len(below) < (20 if wall == "east" else 12):
        return None
    b, a = np.median(below, 0), np.median(above, 0)
    pl = C.lin(np.array([0xEC, 0xE5, 0xDA]) / 255.0)
    alb = np.clip(b / a * pl, 0, 1)
    lab = C.to_lab(C.srgb(alb)[None, None])[0, 0]
    return dict(wall=wall, implied_albedo_srgb=[int(round(v)) for v in C.srgb(alb) * 255], implied_Lab=[round(float(v), 1) for v in lab],
                target=target, target_Lab=[round(float(v), 1) for v in K.lab_hex(target)],
                dE00=round(float(C.de00(tuple(lab), tuple(K.lab_hex(target)))), 2), columns=len(below))


def main(raw):
    ids = K.ids("K-boy-plate")
    stable = C.ero(np.isin(ids, K.ARCH), 3) & K.frame_mask()
    e, rl = K.ecc_lock(os.path.join(ST, raw), os.path.join(ST, "inputs", "plate-K-boy-input.png"), stable)
    steps = [dict(step=1, what="lock: ECC affine onto inputs/plate-K-boy-input.png, masked to the clay's architecture and fixed furniture", **rl)]
    lab = C.to_lab(e)
    ids0 = np.asarray(Image.open(MB0_IDS))
    lab0 = C.to_lab(C.load(MB0))
    before, fixes = {}, {}
    for name, (g, g0) in SURF.items():
        a, _ = rd(lab, ids, g)
        b, _ = rd(lab0, ids0, g0)
        if a is None or b is None:
            continue
        de = float(C.de00(tuple(a), tuple(b)))
        # the light differs (MB0's walnut faces the window; here the boards are in their own shade): the material is its hue and its
        # chroma relative to L*, so the target at this surface's own L* is MB0's hue at MB0's C*/L*
        La, Ca, ha = K.lch(a)
        Lb, Cb, hb = K.lch(K.lab_hex(SPEC_HEX[name]) if name in SPEC_HEX else b)
        t = K.from_lch(La, Cb / max(Lb, 1e-3) * La, hb)
        dc = float(C.de00(tuple(a), tuple(t)))
        before[name] = dict(k_boy=[round(float(v), 1) for v in a], mb0=[round(float(v), 1) for v in b], dE00_raw=round(de, 2),
                            target_at_own_L=[round(float(v), 1) for v in t], dE00_material=round(dc, 2),
                            C_over_L=[round(Ca / max(La, 1e-3), 3), round(Cb / max(Lb, 1e-3), 3)], hue=[round(ha, 1), round(hb, 1)])
        if name in FIX and dc > 3.0:
            sm = C.blur(C.dil(np.isin(ids, g), 1).astype(np.float64), 1.5)
            lab[..., 1] += sm * (t[1] - a[1])
            lab[..., 2] += sm * (t[2] - a[2])
            fixes[name] = dict(ab_shift=[round(float(t[1] - a[1]), 2), round(float(t[2] - a[2]), 2)],
                               why="the material (hue, C*/L*) off MB0 by more than dE00 3 at its own L*")
    e2 = np.clip(C.from_lab(lab), 0, 1)
    band0 = {}
    lin2 = C.lin(e2)
    for wall, wd in WALLS.items():          # each wall's band against the plaster above it on the same wall (the north wall is in its own light)
        b0 = band_reading(e2, ids, wall)
        band0[wall] = b0
        if b0 and b0["dE00"] > 3.0:
            # the paint, not the light: per channel in linear light, x (#A8A88E / the implied albedo); the trowel texture and the light stay
            k = C.lin(np.array([0xA8, 0xA8, 0x8E]) / 255.0) / np.maximum(C.lin(np.array(b0["implied_albedo_srgb"]) / 255.0), 1e-4)
            sm = C.blur(C.dil(np.isin(ids, wd["ids"]), 1).astype(np.float64), 1.5)
            lin2 = lin2 * (1 + (k - 1) * sm[..., None])
            fixes[f"band, {wall} wall"] = dict(k_linear=[round(float(v), 4) for v in k],
                                               why=f"the {wall} band's implied albedo off #A8A88E by more than dE00 3 (the paint: hue and lightness)")
    e2 = np.clip(C.srgb(np.clip(lin2, 0, 1)), 0, 1)
    lab = C.to_lab(e2)
    after = {}
    for name, (g, g0) in SURF.items():
        a, _ = rd(lab, ids, g)
        if a is not None:
            after[name] = [round(float(v), 1) for v in a]
    steps.append(dict(step=2, what="one house: per surface against MB0's plate.png; the band against the plaster above it", before=before,
                      band_before=band0, fixes=fixes, after=after, band_after={w: band_reading(e2, ids, w) for w in WALLS}))
    lab[..., 0] = np.clip(lab[..., 0], 0, 100)
    fr = K.frame_mask()
    p05 = float(np.percentile(lab[..., 0][fr], 0.5))
    if 0.5 < p05 < 11.0:
        xp, fp = [0, p05, 12, 30, 100], [0, 11.5, 16, 30, 100]
    elif p05 > 14.0:
        xp, fp = [0, p05, 30, 100], [0, 12.5, 30, 100]
    else:
        xp = None
    if xp:
        lab[..., 0] = np.interp(lab[..., 0], xp, fp)
        toe = dict(applied=True, p05_before=round(p05, 2), xp=[round(v, 3) for v in xp], fp=fp, why="WM-G1: the frame's p0.5 brought to 11-14")
    else:
        toe = dict(applied=False, p05=round(p05, 2), note="within WM-G1 (11-14) as it came")
    steps.append(dict(step=3, what="WM-G1 / MP-I2 toe on L*", **toe))
    rgb = np.clip(C.from_lab(lab), 0, 1)
    K.save(os.path.join(ST, "plate.png"), rgb)
    K.save_frame(rgb, os.path.join(ST, "plate-frame.png"))
    p05_after = float(np.percentile(C.to_lab(rgb)[..., 0][fr], 0.5))
    json.dump(dict(source=raw, out="plate.png", steps=steps, black_point_p05=round(p05_after, 2), camera_check=K.check_camera("boy"),
                   mandatory_for_derived="step 3's curve (MP-I2), when applied"), open(os.path.join(ST, "plate-compose.json"), "w"), indent=1)
    print(json.dumps(rl["ecc"]), json.dumps(before), json.dumps(fixes), json.dumps(band0), round(p05_after, 2))


if __name__ == "__main__":
    main(sys.argv[1])
