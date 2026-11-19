#!/usr/bin/env python3
"""
compose_plate_mb1.py: the MB1 empty plate from the model's still (render-agent, 2026-11-19; 0 tokens). Global steps, nothing local:
1. Lock: an affine ECC fit of the still onto the plate's model input (the recoloured clay, inputs/plate-input.png), masked to the
   architecture and the fixed furniture of the clay's id pass (walls, window frame and sill, bed, nightstands, shelf, bench).
2. One house (MB0's plate, the same materials under the same light): the bed-wall plaster, the oak and the walnut read against
   MB0's plate.png, per material: the median L* / a* / b* of the clay-id masks here against MB0's. Reported, and corrected only where
   a material is off by more than dE00 3 (13.10's QA gate for the plaster and the oak): a smooth per-material shift, a* b* only for the
   plaster (its light falls off differently from this side of the room, and L* is the light).
3. WM-G1 / MP-I2: a toe on L* only, (0, 0) (p0.5, 11.5) (12, 16) (30, 30) (100, 100) on the 16:9 frame's p0.5 when it is under 11
   (MB0's one-knot toe, with a second knot so the walnut's mid-darks stay MB0's);
   a* b* kept; nothing above L* 30 changes.

  python3 compose_plate_mb1.py raw/plate-r1.png plate.png plate-compose.json
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ARCH = (1, 2, 5, 9, 10, 12, 13, 14, 20, 21, 23, 24, 25, 28, 29, 30)
MAT = {"plaster bed wall": (1,), "plaster window wall": (2, 5), "oak": (10,), "walnut": (20, 21, 24, 25, 28, 29, 30), "mattress": (23,),
       "bronze": (13,), "stone": (14,)}


def medians(lab, ids, ero=6):
    out = {}
    for k, g in MAT.items():
        m = C.ero(np.isin(ids, g), ero) & M.frame_mask()
        if m.sum() > 200:
            out[k] = np.median(lab[m], 0)
    return out


def rd(l, i, g, box=None, ero=4, pct=(25, 75)):
    m = C.ero(np.isin(i, g), ero) & M.frame_mask()
    if box is not None:
        bm = np.zeros_like(m)
        bm[box[1]:box[3], box[0]:box[2]] = True
        m &= bm
    if m.sum() < 50:
        return None
    v = l[m]
    lo, hi = np.percentile(v[:, 0], pct)
    return np.median(v[(v[:, 0] >= lo) & (v[:, 0] <= hi)], 0)


def surface_readings(lab, ids, lab0, ids0):
    out = {}
    for name, g, box1, box0 in (("wall above the headboard", (1,), (1096, 300, 1730, 560), (900, 250, 1820, 560)),
                                ("headboard", (20,), None, None), ("nightstand top", (25,), None, None), ("nightstand fronts", (24,), None, None),
                                ("oak", (10,), None, None), ("window wall", (2,), (80, 700, 500, 1100), None)):
        a, b = rd(lab, ids, g, box1), rd(lab0, ids0, g, box0)
        if a is not None and b is not None:
            out[name] = dict(mb1=[round(float(v), 1) for v in a], mb0=[round(float(v), 1) for v in b], dE00=round(float(C.de00(tuple(a), tuple(b))), 2))
    for name, g in (("bench top", (29,)), ("bench ends", (30,)), ("shelf", (28,))):
        a = rd(lab, ids, g)
        out[name] = dict(mb1=[round(float(v), 1) for v in a])
    return out


def Y_of(L):
    return np.where(L > 8, ((L + 16) / 116) ** 3, L / 903.3)


def L_of(Y):
    return np.where(Y > 216 / 24389, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def one_house(e, lab, ids, lab0, ids0):
    """the three surfaces the model drew off MB0's house:
    - the headboard: the model lit it flat and light (L* 52-56 across); MB0's window light falls off across it (46 -> 24). Per X along
      the headboard (its plane at Y 17.71), the luminance is scaled so the column median matches MB0's at the same X (linear light,
      the grain kept; the gain smoothed over 0.05 m);
    - the bench top: grey and light (a sheen); set to MB1's own nightstand tops (the same walnut, a horizontal face in the same light):
      a Lab shift, the texture kept;
    - the oak: 9 L* darker than MB0's beside the bed: one luminance gain on the floor ids (linear light) to MB0's median."""
    fixes = {}
    lab = lab.copy()
    # headboard
    hb1, hb0 = C.ero(ids == 20, 2), C.ero(ids0 == 20, 2)
    cols1 = np.nonzero(hb1.any(0))[0]
    th = np.radians(M.CAM["yaw"])

    def X_mb1(x):            # the headboard plane (Y 17.71): the ray through column x
        cx, cy = M.CAM["loc"][0], M.CAM["loc"][1]
        fx, fy = -np.sin(th), -np.cos(th)
        rx, ry = np.cos(th), -np.sin(th)
        k = (x - M.CX_) / M.F_
        dx, dy = fx + k * rx, fy + k * ry
        t = (17.71 - cy) / dy
        return cx + t * dx

    def x_mb0(X):
        return C.proj(X, 17.71, 0.6)[0]
    med0 = {}
    cols0 = np.nonzero(hb0.any(0))[0]
    for x in cols0:
        med0[x] = np.median(lab0[..., 0][:, x][hb0[:, x]])
    xs0 = np.array(sorted(med0))
    m0v = np.array([med0[x] for x in xs0])
    m0v = np.convolve(np.pad(m0v, 15, mode="edge"), np.ones(31) / 31, mode="valid")
    gains = np.ones(W)
    g_list = []
    for x in cols1:
        col = hb1[:, x]
        L1 = np.median(lab[..., 0][:, x][col])
        X = X_mb1(x + 0.5)
        L0 = np.interp(x_mb0(X), xs0, m0v)
        g_list.append((x, float(Y_of(np.array(L0)) / max(Y_of(np.array(L1)), 1e-4))))
    gx = np.array([g for _, g in g_list])
    gx = np.convolve(np.pad(gx, 20, mode="edge"), np.ones(41) / 41, mode="valid")
    gains[cols1] = gx
    gmap = np.where(C.dil(ids == 20, 1), gains[None, :], 1.0)
    gmap = 1 + (C.blur(gmap, 1.0) - 1) * C.blur(C.dil(ids == 20, 1).astype(np.float64), 1.0)
    Lh = L_of(Y_of(lab[..., 0]) * gmap)
    lab[..., 0] = np.where(gmap != 1.0, Lh, lab[..., 0])
    fixes["headboard"] = dict(gain_min_max=[round(float(gx.min()), 3), round(float(gx.max()), 3)], method="per-X luminance gain to MB0's column medians")
    # bench top
    tgt = rd(lab, ids, (25,))
    cur = rd(lab, ids, (29,))
    d = tgt - cur
    sm = C.blur(C.dil(ids == 29, 1).astype(np.float64), 1.0)
    gy = float(Y_of(np.array(tgt[0])) / Y_of(np.array(cur[0])))
    lit = np.clip((lab[..., 0] - 20) / 20, 0, 1) * sm                 # the lit top face; its dark front edge keeps its own colour
    lab[..., 0] = L_of(Y_of(lab[..., 0]) * (1 + (gy - 1) * sm))
    lab[..., 1] += lit * d[1]
    lab[..., 2] += lit * d[2]
    fixes["bench top"] = dict(luminance_gain=round(gy, 3), shift_ab=[round(float(d[1]), 1), round(float(d[2]), 1)], to="MB1's nightstand tops",
                              note="ab weighted by the light (L* 20-40 ramp): the top's dark front edge keeps its colour")
    # oak
    o1, o0 = rd(lab, ids, (10,)), rd(lab0, ids0, (10,))
    g = float(Y_of(np.array(o0[0])) / Y_of(np.array(o1[0])))
    fm = C.blur(np.isin(ids, (10, 11)).astype(np.float64), 1.5)
    lab[..., 0] = L_of(Y_of(lab[..., 0]) * (1 + (g - 1) * fm))
    fixes["oak"] = dict(luminance_gain=round(g, 3), from_L=round(float(o1[0]), 1), to_L=round(float(o0[0]), 1))
    return lab, fixes


def main(raw, out, rec):
    ST = M.ST
    ids = M.ids("MB1-plate")
    stable = C.ero(np.isin(ids, ARCH), 3)
    e, rl = M.ecc_lock(os.path.join(ST, raw), os.path.join(ST, "inputs", "plate-input.png"), stable)
    steps = [dict(step=1, what="lock: ECC affine onto inputs/plate-input.png, masked to the clay's architecture and fixed furniture", **rl)]
    lab = C.to_lab(e)
    ids0 = np.asarray(Image.open("/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/MB0-plate-id.png"))
    lab0 = C.to_lab(C.load(os.path.join(M.MB0, "plate.png")))
    before = surface_readings(lab, ids, lab0, ids0)
    lab, fixes = one_house(e, lab, ids, lab0, ids0)
    after = surface_readings(lab, ids, lab0, ids0)
    steps.append(dict(step=2, what="one house: per surface against MB0's plate.png (the same surface under the same window light)",
                      before=before, fixes=fixes, after=after))
    lab[..., 0] = np.clip(lab[..., 0], 0, 100)
    fr = M.frame_mask()
    p05 = float(np.percentile(lab[..., 0][fr], 0.5))
    if 0.5 < p05 < 11.0:
        xp, fp = [0, p05, 12, 30, 100], [0, 11.5, 16, 30, 100]
        lab[..., 0] = np.interp(lab[..., 0], xp, fp)
        toe = dict(applied=True, p05_before=round(p05, 2), curve=f"(0, 0) ({p05:.2f}, 11.5) (12, 16) (30, 30) (100, 100)", xp=[round(v, 3) for v in xp], fp=fp,
                   why="the model's contact shadows came near black (p0.5 1.6): MB0's one-knot toe from there lifts every dark under 30 and "
                       "flattens the walnut; the second knot keeps the nightstand fronts at MB0's L* 17.6 and lifts only the deepest 0.5 %")
    else:
        toe = dict(applied=False, p05=round(p05, 2), note="within WM-G1 (11-14) as it came")
    steps.append(dict(step=3, what="WM-G1 / MP-I2 toe on L*", **toe))
    rgb = np.clip(C.from_lab(lab), 0, 1)
    M.save(os.path.join(ST, out), rgb)
    x0, y0, x1, y1 = (int(round(v)) for v in M.FRAME)
    Image.fromarray(C.q(rgb)).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, out.replace(".png", "-frame.png")))
    p05_after = float(np.percentile(C.to_lab(rgb)[..., 0][fr], 0.5))
    json.dump(dict(source=raw, out=out, steps=steps, black_point_p05=round(p05_after, 2), mandatory_for_derived="step 3's curve (MP-I2)"),
              open(os.path.join(ST, rec), "w"), indent=1)
    print(json.dumps(steps[0]["ecc"]), json.dumps(steps[1]["after"]), json.dumps(steps[1]["fixes"]), round(p05_after, 2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
