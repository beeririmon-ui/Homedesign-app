#!/usr/bin/env python3
"""
compose_plate_work.py: the W0 empty plate from the model's still (render-agent, 2026-11-20; 0 tokens). Global steps only, as MB1:
1. Lock: an affine ECC fit of the still onto the plate's model input (the recoloured clay, inputs/plate-input.png), masked to the
   architecture and the fixed furniture of the clay's id pass (walls, niche, window frame and sill, desk, shelf, chair).
2. One house (MB0's plate.png, the same materials under the same window light), read per material (median Lab of the clay-id masks,
   the middle half of L*); corrected where off by more than dE00 3 (the 13.10 QA gate):
   - the desk-wall plaster came 9 L* under MB0's bed wall, evenly: a smooth light field on the desk-wall plaster only (wall_field;
     plate-gain-field.png, gain = value / 40000), the MB0 step-2 method (MP-I1);
   - the window wall: a* b* only (backlit; its L* is the light);
   - the walnut desk top against MB0's nightstand tops: one luminance gain and half the a* b* shift (the grain kept);
   - the oak within 3: as it came. Bronze and limestone: reported.
3. WM-G1 / MP-I2: a toe on L* only, (0, 0) (p0.5, 11.5) (12, 16) (30, 30) (100, 100) on the 16:9 frame's p0.5 when it is under 11 (MB1's);
   above 14 the same knots pull it down to 12.5; a* b* kept; nothing above L* 30 changes. Recorded as 'mandatory_for_derived'.

  python3 compose_plate_work.py raw/plate-r1.png plate.png plate-compose.json [--no-house]
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
MB0 = "/home/user/homedesign-app/assets/renders/master/warm-modern/stage1-2026-11-17/plate.png"
MB0_IDS = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/MB0-plate-id.png"
# (W0 ids, MB0 ids, kind)
SURF = {"plaster, desk wall": ((1,), (1,), "plaster"), "plaster, window wall": ((2, 5), (2, 5), "plaster"),
        "oak": ((10,), (10,), "wood"), "walnut, vertical fronts (desk panels, drawer / nightstand fronts)": ((21, 22), (24,), "wood"),
        "walnut, tops (desk / nightstands)": ((20,), (25,), "wood"), "bronze": ((13,), (13,), "report"), "limestone slab": ((14,), (14,), "report")}


def rd(lab, ids, g, ero=4, pct=(25, 75)):
    m = C.ero(np.isin(ids, g), ero) & M.frame_mask()
    if m.sum() < 50:
        return None, None
    v = lab[m]
    lo, hi = np.percentile(v[:, 0], pct)
    return np.median(v[(v[:, 0] >= lo) & (v[:, 0] <= hi)], 0), m


def Y_of(L):
    return np.where(L > 8, ((L + 16) / 116) ** 3, L / 903.3)


def L_of(Y):
    return np.where(Y > 216 / 24389, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def readings(lab, ids, lab0, ids0):
    out = {}
    for name, (g, g0, kind) in SURF.items():
        a, _ = rd(lab, ids, g)
        b, _ = rd(lab0, ids0, g0)
        if a is not None and b is not None:
            out[name] = dict(w0=[round(float(v), 1) for v in a], mb0=[round(float(v), 1) for v in b], dE00=round(float(C.de00(tuple(a), tuple(b))), 2),
                             dL=round(float(a[0] - b[0]), 1))
    for name, g in (("desk side panels", (21,)), ("shelf", (24,)), ("chair", (25,)), ("niche back wall", (17,)), ("niche jambs and soffit", (18,))):
        a, _ = rd(lab, ids, g)
        if a is not None:
            out[name] = dict(w0=[round(float(v), 1) for v in a])
    return out


DESK_WALL = (1, 17, 18)
TARGET_L = 85.5            # MB0's bed wall after its step 2 (85.6), inside base.png's back wall (85.5-91.4)
KEEP = 0.25                # the share of the model's own fall-off kept (MB0 kept half; here the wall came 9 L* low and flat)
MAX_GAIN = 2 ** 0.6
GAIN_SCALE = 40000.0
RAMP_PX = 160.0
KNEE, CEIL = 88.0, 95.0    # the lifted plaster's shoulder: unchanged below L* 88, towards 95 above (the window stays the brightest)


def shoulder(L):
    return np.where(L <= KNEE, L, KNEE + (CEIL - KNEE) * (1 - np.exp(-(L - KNEE) / (CEIL - KNEE))))


def wall_field(lab, ids):
    """the desk-wall plaster's light: log luminance fitted (quadratic in x and y) on the face, the niche and the soffit above the desk
    (rows above 1000: the shade under the desk stays as it is); gain = (Y_t / fit) ** (1 - KEEP), lift only, at most +0.6 stop; Y_t solved
    so the face's median reads TARGET_L. Applied to the desk-wall plaster and the skirting under it, ramped to none across each rounded
    corner (RAMP_PX): the right wall (which faces the window, L* 90) and the window wall keep their light."""
    m = C.ero(np.isin(ids, DESK_WALL), 4) & M.frame_mask()
    m[1000:] = False
    ys, xs = np.nonzero(m)
    sub = np.random.default_rng(1).choice(len(xs), min(60000, len(xs)), replace=False)
    xs, ys = xs[sub], ys[sub]
    X, Yy = xs / W, ys / H
    A = np.stack([np.ones_like(X), X, X * X, Yy, Yy * Yy, X * Yy], 1)
    lY = np.log(np.maximum(Y_of(lab[..., 0][ys, xs]), 1e-4))
    coef, *_ = np.linalg.lstsq(A, lY, rcond=None)
    gx, gy = np.meshgrid(np.arange(W) / W, np.arange(H) / H)
    fit = coef[0] + coef[1] * gx + coef[2] * gx * gx + coef[3] * gy + coef[4] * gy * gy + coef[5] * gx * gy
    import cv2
    dw = np.isin(ids, DESK_WALL)
    sk = (ids == 9) & C.dil(dw, 25)
    core = dw | sk
    # across each rounded corner (and its skirting) the lift ramps from the desk wall's to none at the side wall (about 150 px)
    corner = (ids == 5) | ((ids == 9) & C.dil(ids == 5, 25))
    dist = cv2.distanceTransform((~core).astype(np.uint8), cv2.DIST_L2, 5)
    ramp = np.clip(1 - dist / RAMP_PX, 0, 1) * corner
    region = np.maximum(core.astype(np.float64), ramp)
    region = np.maximum(C.blur(region, 3.0) * (core | corner), core.astype(np.float64))
    face = C.ero(ids == 1, 4) & M.frame_mask()
    lo, hi = -1.0, 2.0
    for _ in range(30):
        t = (lo + hi) / 2
        g = np.clip(np.exp((1 - KEEP) * (t - fit)), 1.0, MAX_GAIN)
        g = 1 + (g - 1) * np.clip(region, 0, 1)
        Lm = float(np.median(shoulder(L_of(Y_of(lab[..., 0][face]) * g[face]))))
        if Lm < TARGET_L:
            lo = t
        else:
            hi = t
    return g, np.clip(region, 0, 1), dict(shoulder=f"L* above {KNEE} eased toward {CEIL}", fit_coef=[round(float(c), 4) for c in coef], log_target=round(t, 4), keep=KEEP, max_gain=round(MAX_GAIN, 3),
                   gain_p50_p99_on_face=[round(float(v), 3) for v in np.percentile(g[face], [50, 99])], face_median_after=round(Lm, 1))


def one_house(lab, ids, lab0, ids0):
    fixes = {}
    lab = lab.copy()
    g, region, frec = wall_field(lab, ids)
    L1 = L_of(Y_of(lab[..., 0]) * g)
    lab[..., 0] = L1 + (shoulder(L1) - L1) * region
    fixes["plaster, desk wall"] = dict(applied=True, method="smooth light field on the desk-wall plaster (wall_field)", **frec)
    for name in ("plaster, window wall",):
        gids, g0, _ = SURF[name]
        a, _ = rd(lab, ids, gids)
        b, _ = rd(lab0, ids0, g0)
        d = b[1:] - a[1:]
        sm = C.blur(C.dil(np.isin(ids, gids), 1).astype(np.float64), 1.5)
        lab[..., 1] += sm * d[0]
        lab[..., 2] += sm * d[1]
        fixes[name] = dict(applied=True, ab_shift=[round(float(v), 2) for v in d], note="a* b* only: it is the backlit wall, its L* is the light")
    name = "walnut, tops (desk / nightstands)"
    gids, g0, _ = SURF[name]
    a, _ = rd(lab, ids, gids)
    b, _ = rd(lab0, ids0, g0)
    de = float(C.de00(tuple(a), tuple(b)))
    if de > 3.0:
        sm = C.blur(C.dil(np.isin(ids, gids), 1).astype(np.float64), 1.5)
        gy = float(Y_of(np.array(b[0])) / Y_of(np.array(a[0])))
        lab[..., 0] = L_of(Y_of(lab[..., 0]) * (1 + (gy - 1) * sm))
        a2, _ = rd(lab, ids, gids)
        dab = (b[1:] - a2[1:]) * 0.5
        lab[..., 1] += sm * dab[0]
        lab[..., 2] += sm * dab[1]
        fixes[name] = dict(dE00_before=round(de, 2), applied=True, luminance_gain=round(gy, 3), ab_shift=[round(float(v), 2) for v in dab])
    fixes["walnut, vertical fronts"] = dict(applied=False, note="not comparable: the reading is mostly the side panels' inner faces in the "
                                                                 "desk's own shade; MB0's are lit nightstand fronts")
    fixes["oak"] = dict(applied=False, note="within dE00 3 as it came")
    return lab, fixes, g


def main(raw, out, rec, *flags):
    ST = M.ST
    ids = M.ids("W0-plate")
    stable = C.ero(np.isin(ids, M.ARCH), 3)
    e, rl = M.ecc_lock(os.path.join(ST, raw), os.path.join(ST, "inputs", "plate-input.png"), stable)
    steps = [dict(step=1, what="lock: ECC affine onto inputs/plate-input.png, masked to the clay's architecture and fixed furniture", **rl)]
    lab = C.to_lab(e)
    ids0 = np.asarray(Image.open(MB0_IDS))
    lab0 = C.to_lab(C.load(MB0))
    before = readings(lab, ids, lab0, ids0)
    gfield = None
    if "--no-house" in flags:
        fixes = dict(note="step 2 skipped (--no-house)")
    else:
        lab, fixes, gfield = one_house(lab, ids, lab0, ids0)
        Image.fromarray(np.clip(np.rint(gfield * GAIN_SCALE), 0, 65535).astype(np.uint16)).save(os.path.join(ST, "plate-gain-field.png"))
    after = readings(lab, ids, lab0, ids0)
    steps.append(dict(step=2, what="one house: per surface against MB0's plate.png (the same material under the same window light)",
                      before=before, fixes=fixes, after=after))
    lab[..., 0] = np.clip(lab[..., 0], 0, 100)
    fr = M.frame_mask()
    p05 = float(np.percentile(lab[..., 0][fr], 0.5))
    if 0.5 < p05 < 11.0:
        xp, fp = [0, p05, 12, 30, 100], [0, 11.5, 16, 30, 100]
    elif p05 > 14.0:
        xp, fp = [0, p05, 30, 100], [0, 12.5, 30, 100]
    else:
        xp = None
    if xp:
        lab[..., 0] = np.interp(lab[..., 0], xp, fp)
        toe = dict(applied=True, p05_before=round(p05, 2), xp=[round(v, 3) for v in xp], fp=fp,
                   curve=" ".join(f"({a:.2f}, {b})" for a, b in zip(xp, fp)), why="WM-G1: the frame's p0.5 brought to 11-14")
    else:
        toe = dict(applied=False, p05=round(p05, 2), note="within WM-G1 (11-14) as it came")
    steps.append(dict(step=3, what="WM-G1 / MP-I2 toe on L*", **toe))
    rgb = np.clip(C.from_lab(lab), 0, 1)
    M.save(os.path.join(ST, out), rgb)
    M.save_frame(rgb, os.path.join(ST, out.replace(".png", "-frame.png")))
    p05_after = float(np.percentile(C.to_lab(rgb)[..., 0][fr], 0.5))
    lab_f = C.to_lab(rgb)
    win = np.isin(ids, (0, 15)) & fr
    json.dump(dict(source=raw, out=out, steps=steps, black_point_p05=round(p05_after, 2),
                   window_p99=round(float(np.percentile(lab_f[..., 0][win], 99)), 1) if win.any() else None,
                   rest_p99=round(float(np.percentile(lab_f[..., 0][fr & ~win], 99)), 1),
                   mandatory_for_derived="step 3's curve (MP-I2), when applied; MP-I1: each pass's gain field against this plate outside its zone"),
              open(os.path.join(ST, rec), "w"), indent=1)
    print(json.dumps(steps[0]["ecc"]), json.dumps(before), json.dumps(fixes), round(p05_after, 2))


if __name__ == "__main__":
    main(*sys.argv[1:])
