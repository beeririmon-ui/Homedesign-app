#!/usr/bin/env python3
"""
reserve_r12.py: the reserve passes R1 and R2 of the warm-modern living-room tool, phase 2 (briefs/render-wm-tool-phase2-reserve-2026-11-11.md,
continuing briefs/render-wm-tool-phase2-2026-11-10.md; the manager approved the reserve, 1,300, within PH2-WM). render-agent, 2026-11-11.

The lesson of steps 2-3: seedream with 6 products and 8 references did not hold the geometry, and pale clay the colour of the wall
let it move or re-size things (the white bowl disc went to the other end of the table; the single pale drum became a 66 cm pendant;
the pale box became a rack with its arches to the camera). So these passes give it FEWER products and ONE card crop each, and
TINTED clay: every placeholder is still the step-0 solid at the card's real size and the house plan 1.3.5 position (projected with
step 0's own M0 camera), but painted in the product's own base colour with its simple structure (folds, ribs, coils, arches and slings,
tiers, a rim), so the shape the model sees is already the product's outline.

  R1  curtains (WMC7 stack, never over glazing), planter + basket together (the basket IN FRONT of the pot), magazine holder (Orange)
  R2  bowl (step 0's (0.72, 1.94)) and pendant (50 cm, shade bottom 1.90)

Both passes are drawn on the CURRENT scene: phase 1's ungraded base + the six layered defaults of steps 1-3 + cushion set B.
Everything here writes new files only (inputs/r*-input.*, raw/r*-seedream.png, work-reserve/); steps 1-3 files are read, never written.

  python3 reserve_r12.py scene                         work-reserve/scene-B.png (the current ungraded scene)
  python3 reserve_r12.py input r1|r2                   inputs/<r>-input.png (+ .json), the placeholders in work-reserve/ph-<r>.npz
  python3 reserve_r12.py fetch r1|r2 <url> <pid> <tid> download into raw/, register, tone-match, cut every product into work-reserve/
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import phase2_wm as W  # noqa: E402
import stack  # noqa: E402
import extract as X  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR = os.path.join(HERE, "work-reserve")
PASSES = {"r1": ["curtains", "planter", "basket", "magazine-holder"], "r2": ["pendant", "bowl"]}
ACCEPTED = ["framed-art", "accent-sconces", "vase", "rug", "floor-lamp", "candle-holders"]
SIZE = W.SIZE
SS = 2                                       # supersampling of the drawn placeholders
NAMES = {"r1": "wm-ph2-reserve-r1-window-floor", "r2": "wm-ph2-reserve-r2-table-ceiling"}

# extraction spec for the reserve products (extract.SPEC, with the zones grown where the product has parts beyond the body:
# the basket's loop handles, the rack's slings; the rack's gaps are NOT filled: the rug shows through them and belongs to the rug)
SPEC = dict(X.SPEC)
SPEC.update({
    "basket": dict(margin=26, band=36, onto="floor_wall_planter", z=60),
    "magazine-holder": dict(margin=20, band=30, onto="floor", z=60, no_fill=True),
    "pendant": dict(margin=18, band=0, onto="none", z=80, thin=True),
    "bowl": dict(margin=14, band=22, onto="table", z=65, convex=True),
})


def rel(p):
    return os.path.relpath(p, W.REPO)


# ------------------------------------------------------------------------------------------------- projection (step 0's camera)
def proj(pts):
    """3D points -> work-size pixel coords (x, y) and depth"""
    out = []
    for X_, Y_, Z_ in pts:
        u, v, d = S0.P(X_, Y_, Z_)
        out.append(((S0.CX + u * S0.CW) / S0.GW * SIZE[0], (S0.CY + v * S0.CH) / S0.GH * SIZE[1], d))
    return np.array(out, np.float64)


def _canvas():
    return np.zeros((SIZE[1] * SS, SIZE[0] * SS), np.uint8)


def _down(m):
    return cv2.resize(m.astype(np.float32), SIZE, interpolation=cv2.INTER_AREA)


def hull_mask(pts):
    p = proj(pts)[:, :2] * SS
    m = _canvas()
    cv2.fillPoly(m, [np.round(cv2.convexHull(p.astype(np.float32)) * 4).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=2)
    return _down(m)


def poly_mask(pts):
    p = proj(pts)[:, :2] * SS
    m = _canvas()
    cv2.fillPoly(m, [np.round(p * 4).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=2)
    return _down(m)


def tube_mask(pts, r):
    """a tube of radius r (m) along a 3D polyline, its projected width taken at each segment's depth"""
    p = proj(pts)
    m = _canvas()
    for i in range(len(p) - 1):
        d = 0.5 * (p[i, 2] + p[i + 1, 2])
        w = max(1, int(round(2 * r * 0.6667 / d * S0.CW / S0.GW * SIZE[0] * SS)))
        a, b = tuple(np.round(p[i, :2] * SS).astype(int)), tuple(np.round(p[i + 1, :2] * SS).astype(int))
        cv2.line(m, a, b, 1, w, lineType=cv2.LINE_8)
        cv2.circle(m, a, w // 2, 1, -1)
    cv2.circle(m, tuple(np.round(p[-1, :2] * SS).astype(int)), max(1, w // 2), 1, -1)
    return _down(m)


def col_param(m):
    """per pixel of a soft mask: t in 0-1 across its own row (left edge 0, right edge 1)"""
    H_, W_ = m.shape
    xs = np.arange(W_, dtype=np.float32)[None, :].repeat(H_, 0)
    on = m > 0.5
    l_ = np.where(on.any(1), np.argmax(on, 1), 0).astype(np.float32)
    r_ = np.where(on.any(1), W_ - 1 - np.argmax(on[:, ::-1], 1), 1).astype(np.float32)
    return np.clip((xs - l_[:, None]) / np.maximum(r_ - l_, 1)[:, None], 0, 1)


def row_param(m):
    """per pixel of a soft mask: s in 0-1 down its own column (top 0, bottom 1)"""
    return col_param(m.T).T


# ------------------------------------------------------------------------------------------------- the products as tinted clay
D = S0.DEFAULTS


def parts_planter():
    cx, cy = -1.95, 0.42
    pot = hull_mask(S0.cyl(cx, cy, 0.21, 0.0, 0.355))
    soil = hull_mask(S0.circ(cx, cy, 0.19, 0.355))
    trunk = hull_mask(S0.cyl(cx, cy, 0.022, 0.355, 0.95, 12))
    crown = hull_mask(S0.ellip(cx, cy, 0.28, 0.70, 1.65))
    return dict(pot=pot, soil=soil, trunk=trunk, crown=crown)


def parts_basket():
    cx, cy = -1.62, 0.78
    body = hull_mask(S0.cyl(cx, cy, 0.175, 0.0, 0.39))
    inner = hull_mask(S0.circ(cx, cy, 0.160, 0.39))
    # two rope loops on the rim, opposite each other, the axis turned 30 deg off the camera's right so both read as loops
    cam = S0.CAM
    yaw = math.radians(cam["yaw_deg_left"])
    rgt, fwd = np.array([math.cos(yaw), -math.sin(yaw)]), np.array([-math.sin(yaw), -math.cos(yaw)])
    loops = np.zeros(body.shape, np.float32)
    for sgn in (1, -1):
        ax = sgn * (math.cos(math.radians(30)) * rgt - math.sin(math.radians(30)) * fwd)
        tg = np.array([-ax[1], ax[0]])
        c = np.array([cx, cy]) + 0.168 * ax
        pts = []
        for k in range(13):
            th = math.pi * k / 12
            q = c + tg * 0.035 * math.cos(th)
            pts.append((q[0], q[1], 0.385 + 0.075 * math.sin(th)))
        loops = np.maximum(loops, tube_mask(pts, 0.008))
    return dict(body=body, inner=inner, loops=loops)


def parts_rack():
    """the Orange magazine rack, small 35 x 19 x 27.5, long side to the camera, at (-0.47, 2.57) on the rug (Z 0.012): two arched black
    tubes at its ends (legs at the front and back, a round top), two thin rails along it, five cognac leather slings between them"""
    x0, x1, y0, y1, zb, zt = -0.645, -0.295, 2.475, 2.665, 0.012, 0.287
    r = 0.011
    ax = (x0 + r, x1 - r)
    yf, yb = y1 - r, y0 + r                      # front (camera side, larger Y) and back legs
    ym, rr = 0.5 * (yf + yb), 0.5 * (yf - yb)
    zs = zt - r - rr                             # the arch springs here
    arches = []
    for x in ax:
        pts = [(x, yb, zb + r), (x, yb, zs)] + [(x, ym - rr * math.cos(math.pi * k / 16), zs + rr * math.sin(math.pi * k / 16)) for k in range(17)] \
              + [(x, yf, zb + r)]
        arches.append(tube_mask(pts, r))
    zr = zs - 0.012
    rail_f = tube_mask([(ax[0], yf - 0.004, zr), (ax[1], yf - 0.004, zr)], 0.005)
    rail_b = tube_mask([(ax[0], yb + 0.004, zr), (ax[1], yb + 0.004, zr)], 0.005)
    sl_front, sl_back = np.zeros_like(rail_f), np.zeros_like(rail_f)
    for xc in np.linspace(x0 + 0.055, x1 - 0.055, 5):
        def edge(xe, t0, t1):
            out = []
            for k in range(9):
                t = t0 + (t1 - t0) * k / 8
                out.append((xe, yf - (yf - yb) * t, 0.06 + (zr - 0.06) * (2 * t - 1) ** 2))
            return out
        for t0, t1, dst in ((0.0, 0.5, sl_front), (0.5, 1.0, sl_back)):
            e0, e1 = edge(xc - 0.02, t0, t1), edge(xc + 0.02, t0, t1)
            dst[:] = np.maximum(dst, poly_mask(e0 + e1[::-1]))
    return dict(arches=arches, rail_f=rail_f, rail_b=rail_b, sl_front=sl_front, sl_back=sl_back)


def parts_curtains():
    return dict(stack=hull_mask(S0.box(-2.29, -2.15, 2.65, 2.95, 0.0, 2.86)))


def parts_bowl():
    """style 12, D20 x H8: a low foot ring, a rounded body to the rim, open top (seen from above the table)"""
    cx, cy, z0 = 0.72, 1.94, S0.TABLE_TOP
    pts = S0.cyl(cx, cy, 0.042, z0, z0 + 0.008, 48)
    for k in range(9):
        s = k / 8
        pts += S0.circ(cx, cy, 0.048 + 0.052 * math.sqrt(s), z0 + 0.008 + 0.072 * s, 48)
    body = hull_mask(pts)
    rim = hull_mask(S0.circ(cx, cy, 0.100, z0 + 0.08, 64))
    inside = hull_mask(S0.circ(cx, cy, 0.093, z0 + 0.079, 64))
    return dict(body=body, rim=rim, inside=inside)


TIERS = [(0.13, 2.13, 2.18), (0.19, 2.07, 2.145), (0.25, 2.00, 2.09), (0.20, 1.945, 2.02), (0.15, 1.90, 1.965)]


def parts_pendant():
    """tiered fabric drum, Beige 50: five stacked open rings, the widest 50 cm, shade 1.90-2.18 (step 0's 28 cm), cord to the ceiling"""
    cx, cy = 0.20, 1.72
    tiers = [(hull_mask(S0.cyl(cx, cy, r, z0, z1)), hull_mask(S0.circ(cx, cy, r * 0.97, z0, 96))) for r, z0, z1 in TIERS]
    cord = tube_mask([(cx, cy, 2.18), (cx, cy, 2.99)], 0.003)
    canopy = hull_mask(S0.cyl(cx, cy, 0.055, 2.975, 3.0, 48))
    return dict(tiers=tiers, cord=cord, canopy=canopy)


def shade(below, m, lo=0.6):
    sh = W.shade_of(below, m)
    return np.clip(lo + (1 - lo) * sh, lo, 1.1)


def lr(m, a=1.07, b=0.86):
    """a left-lit falloff across the shape (the window is on the left)"""
    return a + (b - a) * col_param(m)


def paint(out, m, rgb):
    m = np.clip(m, 0, 1)[..., None]
    return out * (1 - m) + np.clip(rgb, 0, 1) * m


def noise(shape, sig, seed):
    rng = np.random.default_rng(seed)
    n = cv2.GaussianBlur(rng.standard_normal(shape).astype(np.float32), (0, 0), sig)
    return n / max(1e-6, float(n.std()))


def draw(pass_, below):
    """the pass input: the scene with the tinted placeholders, far to near; returns the image and each product's full silhouette"""
    out = below.copy()
    sil = {}
    if pass_ == "r1":
        # curtains: a gathered sheer stack, 7 soft wave folds, the linen's pale beige, a little of the wall through it
        c = parts_curtains()["stack"]
        t = col_param(c)
        folds = 0.84 + 0.16 * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))
        lin = np.array([0.88, 0.84, 0.76], np.float32)
        clay = lin[None, None, :] * (folds * shade(below, c, 0.75))[..., None]
        clay = 0.82 * clay + 0.18 * below
        out = paint(out, c, clay)
        sil["curtains"] = c
        # planter: the pot (ribbed upper body, a smooth lower band), soil, the trunk, an olive-green crown (filler)
        p = parts_planter()
        crown = p["crown"]
        g = np.array([0.50, 0.53, 0.43], np.float32)
        out = paint(out, crown, g[None, None, :] * (shade(below, crown, 0.7) * lr(crown) * (1 + 0.10 * noise(crown.shape, 3.0, 4)))[..., None])
        out = paint(out, p["trunk"], np.array([0.40, 0.34, 0.27], np.float32)[None, None, :] * lr(p["trunk"])[..., None])
        pot = p["pot"]
        tt = col_param(pot)
        ang = np.arcsin(np.clip(2 * tt - 1, -1, 1))
        s_ = row_param(pot)
        ribs = np.where(s_ < 0.62, 0.92 + 0.08 * np.cos(44 * ang), 1.0)
        pc = np.array([0.72, 0.69, 0.64], np.float32)
        out = paint(out, pot, pc[None, None, :] * (ribs * shade(below, pot, 0.7) * lr(pot, 1.08, 0.80))[..., None])
        out = paint(out, p["soil"], np.array([0.30, 0.25, 0.20], np.float32))
        sil["planter"] = np.maximum.reduce([pot, p["trunk"], crown])
        # basket: jute tan, fine horizontal coils, a darker inside at the rim, two rope loops; IN FRONT of the pot
        b = parts_basket()
        body = b["body"]
        coils = 0.93 + 0.07 * np.sin(2 * np.pi * np.arange(SIZE[1], dtype=np.float32) / 5.0)[:, None]
        jc = np.array([0.73, 0.60, 0.44], np.float32)
        out = paint(out, body, jc[None, None, :] * (coils * shade(below, body, 0.7) * lr(body, 1.08, 0.80))[..., None])
        out = paint(out, b["inner"], np.array([0.42, 0.34, 0.25], np.float32))
        out = paint(out, b["loops"], jc * 0.95)
        sil["basket"] = np.maximum(body, b["loops"])
        # magazine rack (Orange): black tubes with a soft highlight, cognac slings
        r = parts_rack()
        cog = np.array([0.56, 0.33, 0.18], np.float32)
        blk = np.array([0.075, 0.075, 0.08], np.float32)
        out = paint(out, r["rail_b"], blk * 1.6)
        out = paint(out, r["sl_back"], cog * 0.72)
        for am in r["arches"]:
            out = paint(out, am, blk[None, None, :] * (1 + 1.6 * np.clip(1 - 2 * col_param(am), 0, 1))[..., None])
        out = paint(out, r["sl_front"], cog[None, None, :] * lr(r["sl_front"], 1.06, 0.88)[..., None])
        out = paint(out, r["rail_f"], blk * 1.8)
        sil["magazine-holder"] = np.maximum.reduce(r["arches"] + [r["rail_f"], r["rail_b"], r["sl_front"], r["sl_back"]])
    else:
        # pendant: five stacked off-white fabric rings, each a little darker on its underside (an open ring seen from below)
        p = parts_pendant()
        fab = np.array([0.90, 0.88, 0.83], np.float32)
        out = paint(out, p["canopy"], fab * 0.97)
        out = paint(out, p["cord"], fab)
        allm = np.zeros((SIZE[1], SIZE[0]), np.float32)
        for side, bot in p["tiers"]:
            out = paint(out, side, fab[None, None, :] * lr(side, 1.05, 0.86)[..., None])
            out = paint(out, side * bot, fab * 0.78)
            allm = np.maximum(allm, side)
        sil["pendant"] = np.maximum.reduce([allm, p["cord"], p["canopy"]])
        # bowl: matte black, a soft highlight toward the window, the dark inside under a thin rim
        b = parts_bowl()
        blk = np.array([0.16, 0.16, 0.155], np.float32)
        out = paint(out, b["body"], blk[None, None, :] * lr(b["body"], 1.15, 0.70)[..., None])
        out = paint(out, b["rim"], blk * 1.25)
        out = paint(out, b["inside"], blk * 0.55)
        sil["bowl"] = np.maximum(b["body"], b["rim"])
    return np.clip(out, 0, 1), sil


# ------------------------------------------------------------------------------------------------- the scene, the inputs
def scene():
    p = os.path.join(WR, "scene-B.png")
    if os.path.exists(p):
        return PW.load(p)
    os.makedirs(WR, exist_ok=True)
    U = stack.compose(set(ACCEPTED) | {"cushions"}, cushion_set="B")
    PW.save(p, U)
    return PW.load(p)


def existing_alpha():
    """the layered defaults' alpha (free alpha for items behind the furniture) and set B's, on the current scene; the rug excluded"""
    a = np.zeros((SIZE[1], SIZE[0]), np.float32)
    for k in ACCEPTED:
        if k == "rug":
            continue                                   # the rug lies UNDER the rack and the basket's edge: not in front of anything
        _, ak, _ = stack.product(k)
        a = np.maximum(a, ak)
    _, ac, _ = stack.product("cushions", "B")
    return np.maximum(a, ac)


def vis(pass_, sil):
    """visible parts: nearer placeholders of the pass cover farther ones, the fixed furniture covers the items behind it"""
    fa = W.furn_alpha()
    dep = {"curtains": 2.957, "planter": 4.999, "basket": 4.534, "magazine-holder": 2.425, "pendant": 2.913, "bowl": 2.494}
    out = {}
    for k in PASSES[pass_]:
        v = sil[k].copy()
        for j in PASSES[pass_]:
            if j != k and dep[j] < dep[k]:
                v = v * (1 - sil[j])
        if k in W.BEHIND_FURNITURE:
            v = v * (1 - fa)
        out[k] = np.clip(v, 0, 1)
    return out


def make_input(pass_):
    os.makedirs(W.INP, exist_ok=True)
    below = scene()
    img, sil = draw(pass_, below)
    V = vis(pass_, sil)
    # the visible placeholders must not cover a layered default (they would hide or replace it)
    ea = existing_alpha()
    clash = {k: int(((V[k] > 0.5) & (ea > 0.5)).sum()) for k in V}
    # in front of the fixed furniture only where the plan puts them: the curtains stand behind the armchair (removed above)
    fa = W.furn_alpha()
    img = np.where(((fa > 0.02) & (np.maximum.reduce(list(V.values())) < 0.02))[..., None], below, img)
    if "curtains" in V:
        cfree = sil["curtains"] * fa
        img = img * (1 - cfree[..., None]) + below * cfree[..., None]   # the armchair stays the armchair
    p = os.path.join(W.INP, f"{pass_}-input.png")
    PW.save(p, img)
    np.savez_compressed(os.path.join(WR, f"ph-{pass_}.npz"), **{f"sil_{k}": sil[k].astype(np.float16) for k in sil},
                        **{f"vis_{k}": V[k].astype(np.float16) for k in V})
    rep = {}
    for k in V:
        ys, xs = np.nonzero(V[k] > 0.5)
        rep[k] = dict(px=int((V[k] > 0.5).sum()), box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                      over_layered_defaults_px=clash[k])
    json.dump(dict(pass_=pass_, below=rel(os.path.join(WR, "scene-B.png")),
                   below_is="phase 1's ungraded base + the six layered defaults of steps 1-3 (work/layers) + cushion set B",
                   placeholders=rep, camera="house plan 1.3.5 M0 via step0_clay_checks.P", note="tinted clay placeholders at card size: "
                   "each product's base colour and simple structure, so the model sees its true outline; visible parts only"),
              open(os.path.join(W.INP, f"{pass_}-input.json"), "w"), indent=1)
    print(p, json.dumps(rep))


def load_ph(pass_):
    z = np.load(os.path.join(WR, f"ph-{pass_}.npz"))
    sil = {k[4:]: z[k].astype(np.float32) for k in z.files if k.startswith("sil_")}
    V = {k[4:]: z[k].astype(np.float32) for k in z.files if k.startswith("vis_")}
    return sil, V


# ------------------------------------------------------------------------------------------------- the result
def cut_product(k, regt, below, V, zone, front, dE):
    """extract.cut_one with the reserve SPEC (the rack's gaps stay open: the rug shows through them)"""
    saved = X.SPEC.get(k)
    X.SPEC[k] = SPEC[k]
    try:
        if SPEC[k].get("no_fill"):
            # cut_one fills enclosed holes < 4000 px for non-thin items; mark it thin-free but skip the fill by running it as "convex
            # off, thin off" and then re-opening the holes where the render shows the scene below (dE small)
            fill, a = X.cut_one(k, regt, below, V, zone, front, dE)
            holes = fill & (dE < 5.0) & (V < 0.5)
            ys, xs = np.nonzero(fill)
            inner = np.zeros_like(fill)
            inner[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = True
            reopen = holes & inner
            fill = fill & ~reopen
            g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
            a = np.clip(PW.guided(g, fill.astype(np.float32), 2, 1e-3), 0, 1)
            a = np.where(X.ero(fill, 1), 1.0, a)
            a = np.where(X.dil(fill, 2) & ~front, a, 0.0).astype(np.float32)
            return fill, a
        return X.cut_one(k, regt, below, V, zone, front, dE)
    finally:
        if saved is None:
            X.SPEC.pop(k, None)
        else:
            X.SPEC[k] = saved


def fetch(pass_, url, pid, tid):
    os.makedirs(os.path.join(WR, "layers"), exist_ok=True)
    os.makedirs(os.path.join(WR, "shadows"), exist_ok=True)
    slots = PASSES[pass_]
    p = os.path.join(W.RAW, f"{pass_}-seedream.png")
    if not os.path.exists(p):
        p = X.fetch_raw(url, f"{pass_}-seedream.png")
    out = PW.load(p)
    returned = list(Image.open(p).size)
    if out.shape[1::-1] != SIZE:
        out = cv2.resize(out, SIZE, interpolation=cv2.INTER_LANCZOS4)
    inp = PW.load(os.path.join(W.INP, f"{pass_}-input.png"))
    below = scene()
    reg, M = PW.register(out, inp)
    sil, V = load_ph(pass_)
    zones = {k: X.dil(V[k] > 0.02, SPEC[k]["margin"]) for k in slots}
    Z = np.zeros(SIZE[::-1], bool)
    for z in zones.values():
        Z |= z
    regt, G = X.tone_match(reg, below, Z)
    dE = X.lab_diff(regt, below)
    fa = W.furn_alpha()
    surf = X.surfaces()
    surf["front"] = fa > 0.02
    ea = existing_alpha()
    dep = {"curtains": 2.957, "planter": 4.999, "basket": 4.534, "magazine-holder": 2.425, "pendant": 2.913, "bowl": 2.494}
    order = sorted(slots, key=lambda k: dep[k])
    taken = np.zeros(Z.shape, bool)
    alphas, free = {}, {}
    for k in order:
        front = taken.copy() | (ea > 0.5)              # never take a layered default's pixels
        if k in W.BEHIND_FURNITURE:
            front |= fa > 0.5
        fill, a = cut_product(k, regt, below, V[k], zones[k], front, dE)
        free[k] = a
        if k in W.BEHIND_FURNITURE:
            a = a * (1 - fa)
        alphas[k] = a
        taken |= fill
    shadows = {}
    for k in slots:
        others = {j: alphas[j] for j in slots if j != k}
        others["_layered"] = ea
        saved = X.SPEC.get(k)
        X.SPEC[k] = SPEC[k]
        try:
            shadows[k] = X.shadow_one(k, alphas[k], regt, below, surf, others)
        finally:
            X.SPEC[k] = saved
    recs = {}
    for k in slots:
        a, sh = alphas[k], shadows[k]
        PW.save(os.path.join(WR, "layers", f"{k}.png"), regt, alpha=a)
        if k in W.BEHIND_FURNITURE:
            Image.fromarray((np.clip(free[k], 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(WR, "layers", f"{k}-free-alpha.png"))
        PW.save(os.path.join(WR, "shadows", f"{k}.png"), np.repeat(sh[..., None], 3, 2))
        ph = V[k] > 0.5
        ys, xs = np.nonzero(a > 0.5)
        recs[k] = dict(alpha_px=int((a > 0.5).sum()), soft_px=int(((a > 0.02) & (a < 0.98)).sum()),
                       box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                       placeholder_px=int(ph.sum()), placeholder_covered=round(float((ph & (a > 0.5)).sum() / max(1, ph.sum())), 3),
                       outside_placeholder_px=int(((a > 0.5) & ~X.dil(ph, 2)).sum()),
                       shadow_px_below_0_97=int((sh < 0.97).sum()), shadow_min=round(float(sh.min()), 3))
    far = ~X.dil(Z, 40)
    drift = np.abs(PW.Lstar(reg) - PW.Lstar(below))[far]
    drift_t = np.abs(PW.Lstar(regt) - PW.Lstar(below))[far]
    np.save(os.path.join(WR, f"{pass_}-regt.npy"), regt.astype(np.float16))
    rec = dict(id=NAMES[pass_], pass_=pass_, slots=slots, returned_px=returned, raw=rel(p), register_to_input=np.round(M, 4).tolist(),
               tone_gain_median=[round(float(np.median(G[..., c][Z])), 4) for c in range(3)],
               model_drift_outside_zones_L=dict(raw_median=round(float(np.median(drift)), 2), raw_p95=round(float(np.percentile(drift, 95)), 2),
                                                after_tone_match_median=round(float(np.median(drift_t)), 2),
                                                note="the model's redraw outside the products; discarded (the scene below is kept)"),
               products=recs, placeholder_id=pid, task_id=tid, url=url)
    json.dump(rec, open(os.path.join(WR, f"{pass_}-fetch.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k in ("register_to_input", "model_drift_outside_zones_L", "products", "tone_gain_median")}, indent=1))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "scene":
        scene()
    elif cmd == "input":
        make_input(args[0])
    elif cmd == "fetch":
        fetch(args[0], *args[1:4])
    else:
        raise SystemExit(__doc__)
