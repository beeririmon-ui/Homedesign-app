#!/usr/bin/env python3
"""
lock_d0o.py: compose and check the D0o still (render-agent, 2026-11-17). 0 tokens.
  compose  <raw.png> <out.png> [gain]   D0 outside the mask (0 levels), the model's pixels inside it; optional linear gain
                                         inside the mask only (11.9.3: one multiplier, up to +-1/4 stop, D0o only)
  check    <d0o.png> <input.png> <out.json>
The lines (motion-agent section 2 item 2; master-designer 11.5.2 / 11.5.7) come from the clay's id pass D0-none-id.png and are
found in the image by registering across-line luminance profiles to the model input (the lit clay inside the mask).
"""
import json
import math
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hallkit as K  # noqa: E402
from prep_d0o import mask_d0o  # noqa: E402

CV = K.canvas("D0o")


def to_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def to_srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def compose(raw, out, gain=1.0):
    d0 = np.asarray(Image.open(K.D0).convert("RGB"))
    r = np.asarray(Image.open(raw).convert("RGB"))
    assert r.shape == d0.shape, (r.shape, d0.shape)
    m = mask_d0o()
    inside = r.astype(np.float64) / 255
    if abs(gain - 1.0) > 1e-9:
        inside = to_srgb(to_lin(inside) * gain)
        inside = np.clip(np.rint(inside * 255), 0, 255).astype(np.uint8)
    else:
        inside = r
    res = np.where(m[..., None], inside, d0)
    Image.fromarray(res.astype(np.uint8)).save(out)
    chk = np.asarray(Image.open(out).convert("RGB")).astype(int)
    return dict(outside_mask_max_diff_levels=int(np.abs(chk - d0.astype(int))[~m].max()), gain=gain,
                gain_stops=round(math.log2(gain), 3))


def lines():
    c = K.clay_id("D0o")
    x0, x1, y0, y1 = 704, 1162, 187, 1285
    row = lambda v: int(round(CV.box[1] + v * CV.fh))
    col = lambda u: int(round(CV.box[0] + u * CV.fw))
    V, Hh = {}, {}
    r = row(0.45)
    seams = [(a + b - 1) / 2 for a, b in K.runs_1d(c[r, x0:x1], (83,))]
    for i, s in enumerate(seams):
        V[f"jib door seam {'left' if i == 0 else 'right'}"] = (int(round(x0 + s)), row(0.30), row(0.66), 10, 6)
    # the stone panel's edge: first column of 94/86 left of the jamb, along a row
    rr = c[r, x0:x1]
    st = [k for k in range(len(rr) - 1) if rr[k] in (11, 64) and rr[k + 1] in (94, 86)]
    if st:
        V["stone panel edge"] = (x0 + st[-1] + 1, row(0.20), row(0.66), 10, 6)
    # the jib door head
    cc = col(0.32)
    hd = [(a + b - 1) / 2 for a, b in K.runs_1d(c[y0:y1, cc], (83,))]
    if hd:
        Hh["jib door head"] = (int(round(y0 + hd[0])), col(0.285), col(0.355), 6, 4)
    # ceiling / slot line / wall; skirting top; floor line (along the plaster left of the jib door, and between it and the stone)
    cl = c[y0:y1, col(0.32)]
    for a_, b_, name in (((15,), (95,), "ceiling to the line of light"), ((95,), (11, 82), "line of light to the wall")):
        k = [i for i in range(len(cl) - 1) if cl[i] in a_ and cl[i + 1] in b_]
        if k:
            Hh[name] = (y0 + k[0] + 1, x0 + 20, x1 - 70, 6, 4)
    for u0, u1, tag in ((0.248, 0.27, "left of the jib door"), (0.37, 0.395, "right of the jib door")):
        cx = col((u0 + u1) / 2)
        cl = c[y0:y1, cx]
        k = [i for i in range(len(cl) - 1) if cl[i] == 11 and cl[i + 1] == 14]
        f = [i for i in range(len(cl) - 1) if cl[i] == 14 and cl[i + 1] == 10]
        if k:
            Hh[f"skirting top, {tag}"] = (y0 + k[0] + 1, col(u0), col(u1), 8, 4)
        if f:
            Hh[f"floor line, {tag}"] = (y0 + f[0] + 1, col(u0), col(u1), 8, 4)
    # the panel's joints (id 86 runs along a column in the middle of the panel strip)
    pc = col(0.411)
    js = [(a + b - 1) / 2 for a, b in K.runs_1d(c[y0:y1, pc], (86,))]
    for j in js:
        Hh[f"panel joint v {(y0 + j + 0.5 - CV.box[1]) / CV.fh:.3f}"] = (int(round(y0 + j)), col(0.4015), col(0.4205), 8, 4)
    return V, Hh


def check(img, inp, outp):
    V, Hh = lines()
    meas = K.measure_lines(img, inp, V, Hh, seg=24)
    fin = [v for v in meas.values() if v["median_offset_px"] == v["median_offset_px"]]
    joints = {k: v["median_offset_px"] for k, v in meas.items() if "joint" in k}
    other = {k: v["median_offset_px"] for k, v in meas.items() if "joint" not in k}
    to_u = lambda px: (px + 0.5 - CV.box[0]) / CV.fw
    pos = {}
    for k, (x, *_r) in V.items():
        o = meas[k]["median_offset_px"]
        pos[k] = dict(clay_u=round(to_u(x), 4), still_u=round(to_u(x + (o if o == o else 0)), 4))
    lv = K.levels("D0o", img)
    a = K.d0_anchor(img)
    rep = dict(
        lines=meas,
        positions_u=pos,
        joints_worst_px=max(abs(x) for x in joints.values() if x == x) if joints else None,
        lines_worst_px=max(abs(x) for x in other.values() if x == x),
        lines_n=len(fin),
        rejection_11_5_7=dict(
            stone_edge_u_0400_0422=pos.get("stone panel edge"),
            jib_seams_0274_0365=[pos.get("jib door seam left"), pos.get("jib door seam right")],
            joints_within_3px=bool(joints and max(abs(x) for x in joints.values() if x == x) <= 3.0)),
        levels=lv,
        d0_stone_beside_door_stops=round(a[0], 3),
        jib_not_brighter_than_d0_stone=bool(lv["stops_vs_base"] <= a[0]),
    )
    json.dump(rep, open(outp, "w"), indent=1)
    return rep


if __name__ == "__main__":
    if sys.argv[1] == "compose":
        print(compose(sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 1.0))
    else:
        r = check(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps({k: v for k, v in r.items() if k != "lines"}, indent=1))
