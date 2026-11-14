#!/usr/bin/env python3
"""
proxy_house.py: a small analytic ray-caster of the part of the house the arrival sees (court, front door, hall,
the opening to the living room, the living room shell with three furniture boxes), from docs/house-plan.json and
docs/proposals/wm-front-door-2026-11-14.md. 0 var2 tokens.

It is a TEST FIXTURE, not a clay: axis-aligned boxes, world-fixed procedural textures, flat room lighting. It gives
exact colour and exact planar depth for any camera of the route in a second or two, so the transition tools can be
tested against ground truth before the real clay and the real stills exist (walk_test.py, turn_door.py,
assemble.py selftests). The clay of render-agent stays the ruler for the real work.

  python3 proxy_house.py --cam HD --canvas tall --out /tmp/x/hd.png        # one still (+ -depth.png, 16-bit, /5000)
  python3 proxy_house.py --walk clip1 --n 60 --w 960 --out /tmp/x/walk1    # an exact walk D0 -> HD, 0001.png ...
  python3 proxy_house.py --walk clip2 --n 60 --w 960 --out /tmp/x/walk2    # an exact walk HDx -> M0
"""
from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camgeo as cg  # noqa: E402

PLASTER = (0.925, 0.898, 0.855)     # #ECE5DA
WALNUT = (0.420, 0.290, 0.200)      # #6B4A33
OAK = (0.545, 0.435, 0.333)         # #8B6F55 smoked oak
STONE = (0.847, 0.784, 0.682)       # #D8C8AE
BRONZE = (0.227, 0.196, 0.173)      # #3A322C
GREIGE = (0.72, 0.68, 0.62)
SKY = (0.86, 0.88, 0.90)


def boxes(door: str = "open", seed_variant: int = 0):
    """name, (x0, x1, y0, y1, z0, z1), material. door: 'closed' | 'open' (leaf at 90 deg) | 'none' (D0o)."""
    B = []
    add = lambda n, x0, x1, y0, y1, z0, z1, m: B.append((n, (x0, x1, y0, y1, z0, z1), m))
    # floors and ceilings
    add("living floor", -2.65, 2.65, -0.35, 6.20, -0.2, 0.0, "oak_y")
    add("hall floor", 0.65, 3.66, 6.20, 9.95, -0.2, 0.0, "oak_y")
    add("corridor floor", 1.55, 3.25, 9.80, 17.7, -0.2, 0.0, "oak_y")
    add("court floor", 3.66, 9.5, 6.20, 9.95, -0.2, 0.0, "stone")
    add("living ceiling", -2.65, 2.65, -0.35, 6.35, 3.0, 3.3, "ceiling")
    add("hall ceiling", 0.65, 3.95, 6.20, 9.95, 3.0, 3.3, "ceiling")
    add("corridor ceiling", 1.55, 3.25, 9.80, 17.7, 2.7, 3.3, "ceiling")
    add("court soffit", 3.95, 7.60, 6.20, 9.95, 3.0, 3.3, "ceiling")
    # living shell
    add("living back wall", -2.65, 2.65, -0.35, 0.0, 0.0, 3.0, "plaster")
    add("living window wall", -2.65, -2.30, 0.0, 6.20, 0.0, 3.0, "window_wall")
    add("living right wall", 2.50, 2.65, 0.0, 6.20, 0.0, 3.0, "plaster")
    add("window bench", -2.30, -1.98, 0.75, 2.85, 0.0, 0.45, "stone")
    # the wall between the living room and the hall, with O-entry-living (X 0.95-2.15, to Z 2.40) lined in walnut
    add("front wall left", -2.65, 0.93, 6.20, 6.35, 0.0, 3.0, "plaster")
    add("front wall right", 2.17, 3.95, 6.20, 6.35, 0.0, 3.0, "plaster")
    add("front wall head", 0.93, 2.17, 6.20, 6.35, 2.42, 3.0, "plaster")
    add("lining left", 0.93, 0.95, 6.20, 6.35, 0.0, 2.42, "walnut")
    add("lining right", 2.15, 2.17, 6.20, 6.35, 0.0, 2.42, "walnut")
    add("lining soffit", 0.95, 2.15, 6.20, 6.35, 2.40, 2.42, "walnut")
    # hall
    add("hall left wall", 0.65, 0.80, 6.35, 9.95, 0.0, 3.0, "hall_left")
    add("hall back wall a", 0.80, 1.70, 9.80, 9.95, 0.0, 3.0, "plaster")
    add("hall back wall b", 3.10, 3.95, 9.80, 9.95, 0.0, 3.0, "plaster")
    add("hall back head", 1.70, 3.10, 9.80, 9.95, 2.62, 3.0, "plaster")
    add("corridor left", 1.55, 1.70, 9.95, 17.7, 0.0, 2.7, "plaster")
    add("corridor right", 3.10, 3.25, 9.95, 17.7, 0.0, 2.7, "plaster")
    add("corridor end", 1.55, 3.25, 17.51, 17.7, 0.0, 2.7, "plaster")
    # the exterior wall with the front door (O-front-door, Y 7.80-8.80, to Z 2.40), 0.35 thick
    add("door wall a", 3.60, 3.95, 6.35, 7.80, 0.0, 3.0, "plaster")
    add("door wall b", 3.60, 3.95, 8.80, 9.95, 0.0, 3.0, "plaster")
    add("door head", 3.60, 3.95, 7.80, 8.80, 2.40, 3.0, "plaster")
    if door == "closed":
        add("door leaf", 3.60, 3.66, 7.80, 8.80, 0.0, 2.40, "walnut_v")
        add("door pull", 3.66, 3.72, 7.885, 7.915, 0.75, 1.35, "bronze")
    elif door == "open":
        add("door leaf", 2.60, 3.60, 8.74, 8.80, 0.0, 2.40, "walnut_v")
        add("door pull", 2.685, 2.715, 8.68, 8.74, 0.75, 1.35, "bronze")
    # court
    add("court east wall", 3.95, 9.5, 6.20, 6.55, 0.0, 3.3, "plaster")
    add("court west wall", 3.95, 6.60, 9.60, 9.95, 0.0, 3.3, "plaster")
    add("bath window", 3.95, 4.25, 9.595, 9.60, 1.00, 2.15, "fluted")
    # living furniture (approximate boxes; only their presence and parallax matter here)
    add("sofa seat", -1.35, 1.05, 0.25, 1.20, 0.0, 0.42, "greige")
    add("sofa back", -1.35, 1.05, 0.25, 0.48, 0.42, 0.80, "greige")
    add("coffee table", -0.65, 0.35, 1.75, 2.35, 0.0, 0.36, "walnut")
    add("armchair seat", -1.60, -0.86, 2.36, 3.10, 0.0, 0.40, "greige")
    add("armchair back", -1.60, -1.42, 2.36, 3.10, 0.40, 0.75, "walnut")
    return B


def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFF).astype(np.float32) / 65535.0


def noise3(P, scale, seed=0):
    """World-fixed value noise in 0..1, trilinear."""
    q = P / scale
    i = np.floor(q).astype(np.int64)
    f = (q - i).astype(np.float32)
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        wx = f[..., 0] if dx else 1 - f[..., 0]
        for dy in (0, 1):
            wy = f[..., 1] if dy else 1 - f[..., 1]
            for dz in (0, 1):
                wz = f[..., 2] if dz else 1 - f[..., 2]
                out = out + wx * wy * wz * _hash3(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def _room_light(P):
    """Flat brightness per room: living 1.0, hall 2/3 stop below (0.63), corridor 0.8 stop (0.57), court 1.0."""
    x, y = P[..., 0], P[..., 1]
    L = np.full(x.shape, 1.0, np.float32)
    hall = (y > 6.27) & (y < 9.875) & (x < 3.66)
    corr = (y >= 9.875) & (x < 3.66)
    L[hall] = 0.63
    L[corr] = 0.57
    return L


def shade(P, axis, sign, mat_idx, mats, seed):
    """Colour per hit. P (n, 3) world, axis 0/1/2 of the hit face, sign of its normal, material index."""
    n = P.shape[0]
    col = np.zeros((n, 3), np.float32)
    L = _room_light(P)
    # face factor: tops brightest, then the two wall orientations; underside of ceilings a touch darker
    ff = np.where(axis == 2, np.where(sign > 0, 1.0, 0.94), np.where(axis == 0, 0.97, 0.90)).astype(np.float32)
    fine = noise3(P, 0.012, seed) - 0.5
    mid = noise3(P, 0.11, seed + 1) - 0.5
    low = noise3(P, 0.55, seed + 2) - 0.5
    for k, m in enumerate(mats):
        s = mat_idx == k
        if not s.any():
            continue
        Pk = P[s]
        if m in ("plaster", "ceiling", "hall_left", "window_wall"):
            c = np.array(PLASTER, np.float32)[None] * (1 + 0.05 * low[s] + 0.035 * mid[s] + 0.03 * fine[s])[:, None]
            if m == "hall_left":
                # washed from above by the roof light; the jib door of the work room as 4 mm shadow gaps
                c *= (0.86 + 0.16 * np.clip(Pk[:, 2] / 3.0, 0, 1))[:, None]
                gap = ((np.abs(Pk[:, 1] - 8.10) < 0.002) | (np.abs(Pk[:, 1] - 9.00) < 0.002)) & (Pk[:, 2] < 2.402)
                gap |= (np.abs(Pk[:, 2] - 2.40) < 0.002) & (Pk[:, 1] > 8.10) & (Pk[:, 1] < 9.00)
                c[gap] *= 0.35
            if m == "window_wall":
                glass = (Pk[:, 1] > 0.75) & (Pk[:, 1] < 2.85) & (Pk[:, 2] > 0.45) & (Pk[:, 2] < 2.70)
                bay = np.abs(((Pk[:, 1] - 0.75) % 0.70) - 0.0) < 0.022
                bay |= np.abs(((Pk[:, 1] - 0.75) % 0.70) - 0.70) < 0.022
                edge = (np.abs(Pk[:, 2] - 0.45) < 0.03) | (np.abs(Pk[:, 2] - 2.70) < 0.03)
                c[glass] = np.array(SKY, np.float32) * 1.08
                c[glass & (bay | edge)] = np.array(BRONZE, np.float32)
        elif m == "oak_y":
            # planks 22 cm wide running along Y, butt joints every ~1.9 m staggered per plank
            plank = np.floor(Pk[:, 0] / 0.22)
            tone = _hash3(plank.astype(np.int64), np.zeros_like(plank, np.int64), np.zeros_like(plank, np.int64), seed + 7) - 0.5
            joint = np.abs((Pk[:, 0] / 0.22) % 1.0 - 0.5) > 0.49
            butt = np.abs(((Pk[:, 1] + plank * 0.73) % 1.9) - 0.95) > 0.946
            grain = noise3(Pk * np.array([8.0, 0.6, 1.0]), 0.05, seed + 3) - 0.5
            c = np.array(OAK, np.float32)[None] * (1 + 0.16 * tone + 0.10 * grain + 0.04 * fine[s])[:, None]
            c[joint | butt] *= 0.62
        elif m == "stone":
            jx = np.abs(((Pk[:, 0] - 3.95) % 1.20) - 0.6) > 0.597
            jy = np.abs(((Pk[:, 1] - 8.00) % 0.60) - 0.3) > 0.297
            slab = np.floor((Pk[:, 0] - 3.95) / 1.20) * 31 + np.floor((Pk[:, 1] - 8.00) / 0.60)
            tone = _hash3(slab.astype(np.int64), np.zeros_like(slab, np.int64), np.zeros_like(slab, np.int64), seed + 9) - 0.5
            c = np.array(STONE, np.float32)[None] * (1 + 0.05 * tone + 0.04 * mid[s] + 0.03 * fine[s])[:, None]
            c[(jx | jy) & (axis[s] == 2)] *= 0.80
        elif m in ("walnut", "walnut_v"):
            g = noise3(Pk * np.array([6.0, 6.0, 0.35]), 0.03, seed + 4) - 0.5
            c = np.array(WALNUT, np.float32)[None] * (1 + 0.30 * g + 0.05 * fine[s])[:, None]
        elif m == "bronze":
            c = np.tile(np.array(BRONZE, np.float32), (Pk.shape[0], 1))
        elif m == "fluted":
            fl = 0.5 + 0.5 * np.cos(Pk[:, 0] / 0.02 * 2 * np.pi)
            c = np.array((0.74, 0.72, 0.68), np.float32)[None] * (0.9 + 0.1 * fl)[:, None]
        else:  # greige upholstery
            c = np.array(GREIGE, np.float32)[None] * (1 + 0.06 * mid[s] + 0.08 * fine[s])[:, None]
        col[s] = c
    col *= (L * ff)[:, None]
    return col


def render(cam: cg.Cam, cv: cg.Canvas, door: str = "open", seed: int = 0, exposure: float = 1.0, ss: int = 1, edges: bool = False):
    """Returns (rgb float32 0..1, planar depth float32 metres with inf = sky). ss: supersampling per axis.
    edges=True (ss 1 only): a third value, the structure edges as a bool mask (where the surface changes: another
    plane or another material, and the shadow gaps of the jib door), as the clay's edges pass gives them."""
    if ss > 1:
        big = cg.Canvas(cv.w * ss, cv.h * ss, tuple(b * ss for b in cv.box))
        rgb, dep = render(cam, big, door, seed, exposure, 1)
        rgb = cv2.resize(rgb, (cv.w, cv.h), interpolation=cv2.INTER_AREA)
        dep = dep.reshape(cv.h, ss, cv.w, ss).min(axis=(1, 3))
        return rgb, dep
    B = boxes(door)
    mats = sorted({b[2] for b in B})
    D = cg.rays(cam, cv).reshape(-1, 3)                 # d component = 1, so t is the planar depth
    O = np.asarray(cam.loc, np.float64)
    n = D.shape[0]
    tbest = np.full(n, np.inf)
    abest = np.zeros(n, np.int8)
    sbest = np.zeros(n, np.int8)
    mbest = np.full(n, -1, np.int16)
    pbest = np.zeros(n, np.float32)                     # the coordinate of the hit plane (to tell surfaces apart)
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / D
    for name, (x0, x1, y0, y1, z0, z1), m in B:
        lo = (np.array([x0, y0, z0]) - O) * inv
        hi = (np.array([x1, y1, z1]) - O) * inv
        t1 = np.minimum(lo, hi)
        t2 = np.maximum(lo, hi)
        ax = np.argmax(t1, axis=1)
        tn = t1[np.arange(n), ax]
        tf = t2.min(axis=1)
        hit = (tn < tf) & (tn > 1e-4) & (tn < tbest)
        tbest[hit] = tn[hit]
        abest[hit] = ax[hit]
        sbest[hit] = -np.sign(D[hit, ax[hit]])
        mbest[hit] = mats.index(m)
        bounds = np.array([[x0, x1], [y0, y1], [z0, z1]])
        pbest[hit] = bounds[ax[hit], (D[hit, ax[hit]] < 0).astype(int)]
    ok = np.isfinite(tbest)
    P = O[None] + D[ok] * tbest[ok, None]
    col = np.tile(np.array(SKY, np.float32), (n, 1))
    col[ok] = shade(P, abest[ok], sbest[ok], mbest[ok], mats, seed)
    rgb = np.clip(col * exposure, 0, 1).reshape(cv.h, cv.w, 3)
    dep = np.where(ok, tbest, np.inf).astype(np.float32).reshape(cv.h, cv.w)
    if not edges:
        return rgb, dep
    # one id per surface: material, face axis, side and plane; same plaster on the same plane is one surface
    sid = (mbest.astype(np.int64) * 8 + abest * 2 + (sbest > 0)) * 100000 + np.rint(pbest * 1000).astype(np.int64)
    sid[~ok] = -1
    Pall = O[None] + D * np.where(ok, tbest, 0.0)[:, None]
    hl = mats.index("hall_left") if "hall_left" in mats else -2
    gap = (mbest == hl) & (((np.abs(Pall[:, 1] - 8.10) < 0.002) | (np.abs(Pall[:, 1] - 9.00) < 0.002)) & (Pall[:, 2] < 2.402)
                           | ((np.abs(Pall[:, 2] - 2.40) < 0.002) & (Pall[:, 1] > 8.10) & (Pall[:, 1] < 9.00)))
    sid = sid.reshape(cv.h, cv.w)
    e = np.zeros((cv.h, cv.w), bool)
    e[:, :-1] |= sid[:, :-1] != sid[:, 1:]
    e[:-1, :] |= sid[:-1, :] != sid[1:, :]
    e |= gap.reshape(cv.h, cv.w)
    return rgb, dep, e


def save(path: str, rgb, dep=None, edges=None):
    """<name>.png, and in the clay's conventions <name>-depth.png (16-bit, metres = value / 5000, 65535 = sky) and
    <name>-edges.png (white, edges black)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    cv2.imwrite(path, cv2.cvtColor(np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    if dep is not None:
        d16 = np.where(np.isfinite(dep), np.clip(np.rint(dep * 5000.0), 0, 65534), 65535).astype(np.uint16)
        cv2.imwrite(os.path.splitext(path)[0] + "-depth.png", d16)
    if edges is not None:
        cv2.imwrite(os.path.splitext(path)[0] + "-edges.png", np.where(edges, 0, 255).astype(np.uint8))


CAMS = {"D0": cg.D0, "HD": cg.HD, "HDx": cg.HDX, "M0": cg.M0}
WALKS = {"clip1": (cg.D0, cg.HD, "open"), "clip2": (cg.HDX, cg.M0, "open")}


def canvas_of(name: str, w: int):
    if name == "frame":
        return cg.Canvas.frame(w)
    if name == "base":
        return cg.Canvas.base(w)
    if name == "tall":
        return cg.Canvas.tall(w, int(round(w * 2 / 3)), 0.0302)
    raise SystemExit("canvas: frame | base | tall")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cam", choices=sorted(CAMS))
    ap.add_argument("--walk", choices=sorted(WALKS))
    ap.add_argument("--canvas", default="frame")
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--door", default="open", choices=["open", "closed", "none"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cv = canvas_of(a.canvas, a.w)
    if a.cam:
        rgb, dep = render(CAMS[a.cam], cv, a.door)
        save(a.out, rgb, dep)
    elif a.walk:
        c0, c1, door = WALKS[a.walk]
        for i in range(a.n):
            rgb, _ = render(cg.lerp_cam(c0, c1, i / (a.n - 1)), cv, door)
            save(os.path.join(a.out, f"{i + 1:04d}.png"), rgb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
