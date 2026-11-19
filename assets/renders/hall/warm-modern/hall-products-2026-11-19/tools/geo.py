#!/usr/bin/env python3
"""
geo.py: the hall's first four products in world coordinates, and their projection into HT2 and HDx2, render-agent 2026-11-19.
0 tokens. Positions from docs/proposals/wm-house-20-2026-11-19.md 4.4 (with 1.3.9) and 8.1-8.2; the clay of 2026-11-18 wins on the
planes (the limestone face is at X 0.81 in wm-hall-2026-11-18/HT: a 1 cm cladding on the plaster at 0.80).

  wall-sconce  332886 A 28 (12000051976080270): a smooth travertine cylinder D 6.5 x H 28 on a walnut block (card depth 11 = block
               4.5 + cylinder 6.5); the plate's centre (0.81, 6.95, 1.70) (1.3.9), so the cylinder is Z 1.56-1.84, its axis X 0.8875.
               The block from the SKU photo A: about 14 cm, from 26 % to 76 % of the cylinder's height measured from its top.
  wall-hooks   CJJJJTJT09286-Black, four walnut blocks 4 x 8 x 2 with a 1.7 dowel angled up; on the stone at Y 7.25-7.65, Z 1.59-1.67
               (1.3.9: Y 7.25-7.65, Z 1.60-1.66), the outer edges at 7.25 and 7.65, so the centres are 12 cm apart.
  bench-throw  the Khaki waffle 150x200 folded 4 x 5 (8.1): a stack 37 x 40 x 7.5 on the full depth of the seat (X 0.81-1.21) at its
               left end, Y 7.09-7.46 (about 39 cm of walnut left bare on the right), the last panel hanging 15 cm over the front edge.
  basket       CJYD195774302BY, cream cotton rope D 30 x H 30, under the seat, centred at (1.01, 7.10) (1.3.9), with two rope loops
               at the rim on the Y sides (6 cm). Hidden wherever the clay's bench (id 100) is in front.
"""
from __future__ import annotations

import math
import os
import sys

import cv2
import numpy as np

REPO = "/home/user/homedesign-app"
T18 = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-18/tools")
sys.path.insert(0, T18)
import kit as K  # noqa: E402

HALL18 = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-2026-11-18")
OUT = os.path.join(REPO, "assets/renders/hall/warm-modern/hall-products-2026-11-19")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/hallp"
STONE_X = 0.81
LIGHT = np.array([0.45, 0.0, 1.0]) / math.hypot(0.45, 1.0)       # the roof-light slot from above, the door's fill from +X

# ---- the products ----------------------------------------------------------------------------------------------------------------
SCONCE = dict(axis=(0.8875, 6.95), r=0.0325, z=(1.56, 1.84), block=((STONE_X, 6.935, 1.627), (0.855, 6.965, 1.767)))
HOOK_Y = (7.27, 7.39, 7.51, 7.63)
HOOK = dict(w=0.04, h=0.08, t=0.02, z0=1.59, peg_r=0.0085, peg_len=0.045, peg_z=1.607, peg_tilt_deg=15.0)
THROW = dict(x=(STONE_X, 1.21), y=(7.09, 7.46), z=(0.45, 0.525), flap_z=0.30, flap_t=0.012)
BASKET = dict(c=(1.01, 7.10), r=0.15, z=(0.0, 0.30), loop=0.06)

PIDS = {
    "wall-sconce": dict(pid="wall-sconce-aliexpress-travertine-walnut-cylinder-332886-hall", sku="12000051976080270",
                        card="data/products/entrance/wall-sconce/wall-sconce-aliexpress-travertine-walnut-cylinder-332886-hall.json"),
    "wall-hooks": dict(pid="wall-hooks-cj-walnut-block-peg-set-of-4", sku="CJJJJTJT09286-Black",
                       card="data/products/entrance/wall-hooks/wall-hooks-cj-walnut-block-peg-set-of-4.json"),
    "bench-throw": dict(pid="bench-throw-cj-cotton-waffle-blanket-150x200", sku="CJZW275832213MN",
                        card="data/products/entrance/bench-throw/bench-throw-cj-cotton-waffle-blanket-150x200.json"),
    "basket": dict(pid="basket-cj-jute-cotton-rope-cylinder-30-hall", sku="CJYD195774302BY",
                   card="data/products/entrance/basket/basket-cj-jute-cotton-rope-cylinder-30-hall.json"),
}
ORDER = ("wall-sconce", "wall-hooks", "bench-throw", "basket")


# ---- faces -----------------------------------------------------------------------------------------------------------------------
def box(lo, hi, tag):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    return [
        ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0), tag),
        ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), tag),
        ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1), tag),
        ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0), tag),
        ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), tag),
    ]


def cylinder(p0, p1, r, tag, n=48, caps=True):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a = (p1 - p0) / np.linalg.norm(p1 - p0)
    e1 = np.cross(a, [0, 0, 1.0]) if abs(a[2]) < 0.9 else np.cross(a, [1.0, 0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    out = []
    ring = [math.cos(2 * math.pi * k / n) * e1 + math.sin(2 * math.pi * k / n) * e2 for k in range(n)]
    for k in range(n):
        q0, q1 = ring[k], ring[(k + 1) % n]
        nm = (q0 + q1) / np.linalg.norm(q0 + q1)
        out.append(([p0 + r * q0, p0 + r * q1, p1 + r * q1, p1 + r * q0], tuple(nm), tag))
    if caps:
        out.append(([p1 + r * q for q in ring], tuple(a), tag))
        out.append(([p0 + r * q for q in ring[::-1]], tuple(-a), tag))
    return out


def faces(slot):
    if slot == "wall-sconce":
        (bx0, by0, bz0), (bx1, by1, bz1) = SCONCE["block"]
        X, Y = SCONCE["axis"]
        return box((bx0, by0, bz0), (bx1, by1, bz1), "walnut") + \
            cylinder((X, Y, SCONCE["z"][0]), (X, Y, SCONCE["z"][1]), SCONCE["r"], "travertine")
    if slot == "wall-hooks":
        f = []
        t = math.radians(HOOK["peg_tilt_deg"])
        for y in HOOK_Y:
            f += box((STONE_X, y - HOOK["w"] / 2, HOOK["z0"]), (STONE_X + HOOK["t"], y + HOOK["w"] / 2, HOOK["z0"] + HOOK["h"]), "walnut")
            p0 = (STONE_X + HOOK["t"] - 0.003, y, HOOK["peg_z"])
            p1 = (p0[0] + HOOK["peg_len"] * math.cos(t), y, p0[2] + HOOK["peg_len"] * math.sin(t))
            f += cylinder(p0, p1, HOOK["peg_r"], "walnut", n=24)
        return f
    if slot == "bench-throw":
        x0, x1 = THROW["x"]
        y0, y1 = THROW["y"]
        z0, z1 = THROW["z"]
        f = box((x0 + 0.005, y0, z0), (x1, y1, z1), "khaki")
        f += box((x1, y0, THROW["flap_z"]), (x1 + THROW["flap_t"], y1, z0), "khaki_flap")
        return f
    if slot == "basket":
        cx, cy = BASKET["c"]
        r = BASKET["r"]
        z0, z1 = BASKET["z"]
        f = cylinder((cx, cy, z0), (cx, cy, z1), r, "cream", n=64, caps=False)
        f.append(([(cx + r * 0.97 * math.cos(2 * math.pi * k / 64), cy + r * 0.97 * math.sin(2 * math.pi * k / 64), z1 - 0.004)
                   for k in range(64)], (0, 0, 1), "inside"))
        for sy in (-1, 1):                                   # the two loops, as short arcs of rope
            yc = cy + sy * (r - 0.01)
            pts = [(cx + 0.045 * math.cos(math.pi * k / 12), yc, z1 + BASKET["loop"] * math.sin(math.pi * k / 12)) for k in range(13)]
            for a, b in zip(pts[:-1], pts[1:]):
                f += cylinder(a, b, 0.006, "cream", n=8, caps=False)
        return f
    raise KeyError(slot)


COLOURS = {  # sRGB 0-255 of the proxy materials, near their photo readings (house20-photo-check.json), before shading
    "walnut": (107, 74, 51), "travertine": (226, 207, 172), "khaki": (183, 174, 156), "khaki_flap": (168, 159, 142), "cream": (219, 210, 190),
    "inside": (120, 110, 92)}


def render(slot, still="HT", shade=True):
    """Rasterise one product's faces (painter's order) on a still's canvas: (rgb float 0-1, coverage mask, depth)."""
    cam, cv = K.CAMS[still], K.canvas(still)
    rgb = np.zeros((cv.h, cv.w, 3), np.float32)
    dep = np.full((cv.h, cv.w), np.inf, np.float32)
    cover = np.zeros((cv.h, cv.w), np.uint8)
    loc = np.asarray(cam.loc)
    items = []
    for quad, nrm, tag in faces(slot):
        Q = np.asarray(quad, float)
        c = Q.mean(0)
        nm = np.asarray(nrm, float)
        if nm @ (loc - c) <= 0:
            continue
        u, v, d = cam.project(Q)
        if np.any(d <= 0.05):
            continue
        x, y = cv.px(u, v)
        items.append((float(np.mean(d)), np.stack([x, y], -1), nm, tag))
    items.sort(key=lambda t: -t[0])
    for d, xy, nm, tag in items:
        s = (0.42 + 0.58 * max(0.0, float(nm @ LIGHT))) if shade else 1.0
        col = np.array(COLOURS[tag], np.float32) / 255.0
        lin = K.to_lin(col) * s
        m = np.zeros((cv.h, cv.w), np.uint8)
        cv2.fillPoly(m, [np.int32(np.round(xy * 16))], 1, lineType=cv2.LINE_AA, shift=4)
        sel = m > 0
        rgb[sel] = K.to_srgb(lin)
        dep[sel] = d
        cover |= m
    return rgb, cover.astype(bool), dep


def polyline(P, still="HT"):
    """World points -> canvas pixel coordinates (n, 2)."""
    u, v, _ = K.CAMS[still].project(np.asarray(P, float))
    x, y = K.canvas(still).px(u, v)
    return np.stack([x, y], -1)


def throw_lines(still="HT"):
    """The fold lines the input draws on the throw's front: the crease where the hanging panel leaves the stack (at the seat's
    front edge) and three faint layer lines across the stack's front face."""
    y0, y1 = THROW["y"]
    z0, z1 = THROW["z"]
    x1 = THROW["x"][1]
    crease = polyline([(x1 + THROW["flap_t"], y0, z0), (x1 + THROW["flap_t"], y1, z0)], still)
    layers = [polyline([(x1, y0, z), (x1, y1, z)], still) for z in np.linspace(z0, z1, 5)[1:-1]]
    return crease, layers


def bench_mask(still="HT"):
    return K.clay_id(still) == K.BENCH_ID


def product_mask(slot, still="HT"):
    _, m, _ = render(slot, still, shade=False)
    if slot == "basket":
        m &= ~bench_mask(still)
    return m


def uv_box(m, still="HT"):
    ys, xs = np.nonzero(m)
    u0, v0 = K.uv_of_px(still, xs.min() - 0.5, ys.min() - 0.5)
    u1, v1 = K.uv_of_px(still, xs.max() + 0.5, ys.max() + 0.5)
    return [round(u0, 4), round(u1, 4), round(v0, 4), round(v1, 4)], [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


if __name__ == "__main__":
    for s in ORDER:
        m = product_mask(s)
        print(s, int(m.sum()), uv_box(m))


def cylinder_alpha(still="HT", ss=4, pad=4):
    """the wall light's travertine cylinder as an exact anti-aliased silhouette (ray cast, ss x ss samples per pixel): the side
    (X, Y axis, r, Z 1.56-1.84) and the bottom opening's rim (seen from below). Returns (alpha float32 on the canvas, bbox)."""
    cam, cv = K.CAMS[still], K.canvas(still)
    _, cov, _ = render("wall-sconce", still, shade=False)
    ys, xs = np.nonzero(cov)
    x0, y0, x1, y1 = xs.min() - pad, ys.min() - pad, xs.max() + 1 + pad, ys.max() + 1 + pad
    off = (np.arange(ss) + 0.5) / ss - 0.5
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    X = (xx[..., None, None] + off[None, None, None, :])
    Y = (yy[..., None, None] + off[None, None, :, None])
    X, Y = np.broadcast_arrays(X, Y)
    u = (X + 0.5 - cv.box[0]) / cv.fw
    v = (Y + 0.5 - cv.box[1]) / cv.fh
    P = cam.unproject(u, v, np.ones_like(u))
    C = np.asarray(cam.loc, float)
    d = P - C
    ax, ay = SCONCE["axis"]
    r = SCONCE["r"]
    z0, z1 = SCONCE["z"]
    ox, oy = C[0] - ax, C[1] - ay
    a = d[..., 0] ** 2 + d[..., 1] ** 2
    b = 2 * (ox * d[..., 0] + oy * d[..., 1])
    c = ox * ox + oy * oy - r * r
    disc = b * b - 4 * a * c
    t = (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a)
    z = C[2] + t * d[..., 2]
    hit = (disc >= 0) & (t > 0) & (z >= z0) & (z <= z1)
    tc = (z0 - C[2]) / d[..., 2]                                  # the bottom cap (the camera is below it)
    qx, qy = ox + tc * d[..., 0], oy + tc * d[..., 1]
    hit |= (tc > 0) & (qx * qx + qy * qy <= r * r)
    al = np.zeros((cv.h, cv.w), np.float32)
    al[y0:y1, x0:x1] = hit.mean((-1, -2))
    return al, (int(x0), int(y0), int(x1), int(y1))


def face_alpha(slot, tag, still="HT", ss=4):
    """anti-aliased alpha of a slot's visible faces with one tag (fillPoly on a ss x canvas, area-averaged down)"""
    cam, cv = K.CAMS[still], K.canvas(still)
    loc = np.asarray(cam.loc)
    big = np.zeros((cv.h * ss, cv.w * ss), np.uint8)
    for quad, nrm, tg in faces(slot):
        if tg != tag:
            continue
        Q = np.asarray(quad, float)
        if np.asarray(nrm, float) @ (loc - Q.mean(0)) <= 0:
            continue
        u, v, d = cam.project(Q)
        x, y = cv.px(u, v)
        pts = np.stack([(x + 0.5) * ss - 0.5, (y + 0.5) * ss - 0.5], -1)
        cv2.fillPoly(big, [np.int32(np.round(pts * 16))], 255, shift=4)
    return cv2.resize(big, (cv.w, cv.h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
