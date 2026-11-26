#!/usr/bin/env python3
"""
finish.py: the shared finishing code of FB13 (render-agent, 2026-11-25; docs/proposals/wm-fb13-living-wow-2026-11-25.md 3.2 item 9).
0 var2 tokens. Room-agnostic: it reads a room's layer manifest (the living-room tool format or the v2 format of the other rooms) and never
writes into a room's files unless asked to write new files with the -fb13prep suffix.

ONE FINISH, THE SAME FOR EVERY COMBINATION. Every operation is either a property of one product layer (baked into that layer, so it travels
with it into any combination) or a function of the canvas position only (the same at a pixel whatever stands there):
  1. sharpness   each layer's silhouette edge spread (sigma of a blurred step, measured on the composite across its alpha edge) is matched to
                 the plate's edge spread measured on the plate's own edges in a ring round the product: a layer sharper than the plate by
                 more than 10 % is blurred (premultiplied RGBA, sigma_add = sqrt(s_plate^2 - s_layer^2), at most 1.6 px); a softer matte
                 gets its alpha ramp steepened round 0.5 (at most x1.4, RGB untouched: an unsharp mask on RGB leaves a soft matte soft and
                 adds crunch; tried on W0 and dropped). Target: the ratio s_plate / s_layer inside 0.90-1.10.
  2. depth of    only where the room has a depth map (the living room's depth.png; M0-W's clay depth): the circle of confusion of
     field       lens / f-number / focus distance per pixel for the plate and at the product's contact depth for a layer (f/5.6 by default).
  3. light wrap  at most 2 px and 15 %: in the layer's edge band, the blurred plate under it is mixed in where the plate is brighter than the
                 layer, weighted by how much the edge faces the room's dominant light (the centroid of the plate's brightest 1.5 % inside the
                 frame: the glazing or the sun patch). Not a halo: never brighter than the background it borrows from.
  4. bounce      a separate multiplicative tint around a coloured product (C* >= 12 and >= 0.3 % of the frame): its own colour, relative to
                 grey, at most 6 %, spread over the surfaces next to it and fading with distance (sigma 0.04 sqrt(area)); outside the alpha.
  5. grain       ONE grain field by canvas position (seed 1540, monochrome, sigma 0.6 px grain, midtone weighted, 1.2-2.0 levels) on the plate and
                 every layer alike, so a pixel shows the same grain whatever product covers it; plus a per-layer top-up for a layer smoother
                 than the plate (sqrt(s_plate^2 - s_layer^2) of a second positional field), so its noise matches the plate's.
  6. grade and   one grade is already in every room; the vignette is off for the existing rooms (their grade has one where it has one);
     vignette    for M0-W it is part of the finish, at most 0.25 stop (G1.9).
The finished stack is composed with the manifests' own formula. The pasted test (pasted_test.py) measures the stack before and after.

    python3.12 -I -B finish.py <room> [--write-layers DIR]          # one room: the finished frame (-fb13prep), a record
Rooms: see ROOMS (the current default frame of every warm-modern room, 2026-11-25).
"""
import glob
import json
import math
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
R = os.path.join(REPO, "assets", "renders")
SEED = 1540

# the current default frame of every warm-modern room with product layers (2026-11-25)
ROOMS = {
    "M0": dict(room="living-room", manifest="living-room/warm-modern/phase2-2026-11-10/layers/manifest-basket.json", kind="tool", set="B",
               frame="living-room/warm-modern/phase2-2026-11-10/default-frame-basket-set-B.png", frame_kind="frame1920",
               depth="living-room/warm-modern/depth.png", depth_json="living-room/warm-modern/depth.json", out_dir="living-room/warm-modern/phase2-2026-11-10",
               out_name="default-frame-basket-set-B"),
    "D1": dict(room="kitchen-dining", manifest="dining/warm-modern/stage1-2026-11-20/manifest.json", kind="v2", frame_id="D1",
               frame="dining/warm-modern/stage1-2026-11-20/D1-defaults.png", out_dir="dining/warm-modern/stage1-2026-11-20", out_name="D1-defaults"),
    "D2": dict(room="kitchen-dining", manifest="dining/warm-modern/stage1-2026-11-20/manifest.json", kind="v2", frame_id="D2",
               frame="dining/warm-modern/stage1-2026-11-20/D2-defaults.png", out_dir="dining/warm-modern/stage1-2026-11-20", out_name="D2-defaults"),
    "W0": dict(room="work", manifest="work/warm-modern/stage1-2026-11-20/layers/manifest.json", kind="v2",
               frame="work/warm-modern/stage1-2026-11-20/w0-defaults.png", out_dir="work/warm-modern/stage1-2026-11-20", out_name="w0-defaults"),
    "MB0": dict(room="master", manifest="master/warm-modern/stage1-2026-11-17/layers/manifest.json", kind="v2",
                frame="master/warm-modern/stage1-2026-11-17/mb0-defaults.png", out_dir="master/warm-modern/stage1-2026-11-17", out_name="mb0-defaults"),
    "MB1": dict(room="master", manifest="master/warm-modern/mb1-2026-11-19/layers/manifest.json", kind="v2",
                frame="master/warm-modern/mb1-2026-11-19/mb1-defaults.png", out_dir="master/warm-modern/mb1-2026-11-19", out_name="mb1-defaults"),
    "B1": dict(room="bath", manifest="bath/warm-modern/b1-2026-11-19/layers/manifest.json", kind="v2",
               frame="bath/warm-modern/b1-2026-11-19/b1-defaults.png", out_dir="bath/warm-modern/b1-2026-11-19", out_name="b1-defaults"),
    "B2": dict(room="bath", manifest="bath/warm-modern/stage1-2026-11-17/layers/manifest.json", kind="v2",
               frame="bath/warm-modern/stage1-2026-11-17/b2-defaults.png", out_dir="bath/warm-modern/stage1-2026-11-17", out_name="b2-defaults"),
    "K-boy": dict(room="boy", manifest="boy/warm-modern/stage1-2026-11-24/manifest.json", kind="v2",
                  frame="boy/warm-modern/stage1-2026-11-24/K-boy-defaults.png", out_dir="boy/warm-modern/stage1-2026-11-24", out_name="K-boy-defaults"),
    "K-girl": dict(room="girl", manifest="girl/warm-modern/stage1-2026-11-24/manifest-g1.json", kind="v2",
                   frame="girl/warm-modern/stage1-2026-11-24/K-girl-defaults-g1.png", out_dir="girl/warm-modern/stage1-2026-11-24",
                   out_name="K-girl-defaults-g1"),
    "HT2": dict(room="hall", manifest="hall/warm-modern/hall-products-2026-11-19/layers/manifest.json", kind="v2",
                frame="hall/warm-modern/hall-products-2026-11-19/ht2-products.png", out_dir="hall/warm-modern/hall-products-2026-11-19",
                out_name="ht2-products"),
    "HDx2": dict(room="hall", manifest="hall/warm-modern/hall-products-2026-11-19/hdx2/manifest.json", kind="v2",
                 frame="hall/warm-modern/hall-products-2026-11-19/hdx2-products.png", out_dir="hall/warm-modern/hall-products-2026-11-19",
                 out_name="hdx2-products"),
}
NOT_LAYERED = {"D0": "hall/warm-modern/door-2026-11-16/d0.png: one approved render, no product layers (the porch light and the doormat are "
                     "baked); the pasted test needs layers"}


# ---------------------------------------------------------------------------------------------------------------
# reading a room
# ---------------------------------------------------------------------------------------------------------------
def rd(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def _png_of(s):
    m = re.search(r"[^\s()]+\.png", s or "")
    return m.group(0) if m else None


def _resolve(mdir, rel):
    for base in (mdir, os.path.dirname(mdir), os.path.dirname(os.path.dirname(mdir))):
        p = os.path.normpath(os.path.join(base, rel))
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"{rel} (from {mdir})")


def load_room(key):
    """-> dict(base, entries=[dict(name, slot, product, layer, shadow, z)], lights=[path], frame, canvas, frame_box, ...)"""
    cfg = dict(ROOMS[key])
    mp = os.path.join(R, cfg["manifest"])
    mdir = os.path.dirname(mp)
    man = json.load(open(mp))
    st = dict(key=key, cfg=cfg, manifest=mp, entries=[], lights=[])
    st["frame_box"] = man.get("frame_box") or [77.4882, 43.4301, 2642.5118, 1486.5699]
    if cfg["kind"] == "tool":
        by = {l_["id"]: l_ for l_ in man["layers"]}
        st["base"] = _resolve(mdir, by["base"]["file"])
        order = man["compose"]["order"]
        cs = man["slot_cushions"]["sets"][cfg["set"]]
        for k in order:
            if k == "base" or k.endswith("-shadow"):
                continue
            if k == "cushions":
                lf, sf, prod = _resolve(mdir, cs["layer"]), _resolve(mdir, cs["shadow"]), f"cushion set {cfg['set']}"
            else:
                sh = by.get(k + "-shadow")
                lf = _resolve(mdir, by[k]["file"])
                sf = _resolve(mdir, sh["file"]) if sh and sh.get("file") else None
                p = by[k].get("product") or {}
                prod = p.get("card_id") if isinstance(p, dict) else str(p)
            st["entries"].append(dict(name=k, slot=k, product=prod, layer=lf, shadow=sf, z=by[k]["z"]))
        for L in man.get("light_layers", []) if isinstance(man.get("light_layers"), list) else []:
            if isinstance(L, dict) and L.get("file"):
                st["lights"].append(_resolve(mdir, L["file"]))
    else:
        fid = cfg.get("frame_id")
        if fid:
            st["base"] = _resolve(mdir, _png_of(man["bases"][fid]))
        else:
            st["base"] = _resolve(mdir, _png_of(man["base"]))
        rows = []
        for l_ in man["layers"]:
            if not l_.get("default") or l_.get("retired"):
                continue
            if fid and l_.get("frame") != fid:
                continue
            rows.append(l_)
        rows.sort(key=lambda l_: (l_["z"], l_.get("sub", 0)))
        for l_ in rows:
            nm = l_["slot"] + (f"-{l_['side']}" if l_.get("side") else "")
            if any(e["name"] == nm for e in st["entries"]):
                nm = f"{nm}-{len(st['entries'])}"
            st["entries"].append(dict(name=nm, slot=l_["slot"], product=l_.get("product"), layer=_resolve(mdir, l_["layer"]),
                                      shadow=_resolve(mdir, l_["shadow"]) if l_.get("shadow") else None, z=l_["z"]))
        lights = man.get("light") or []
        if isinstance(lights, dict):
            lights = [lights]
        for L in lights:
            if fid and L.get("frame") not in (None, fid):
                continue
            st["lights"].append(_resolve(mdir, L["file"]))
    st["frame"] = os.path.join(R, cfg["frame"])
    return st


# ---------------------------------------------------------------------------------------------------------------
# composing (the manifests' formula: o = round(round(rgb a) + round(o S / 255) (1 - a)); lights screen x (1 - every alpha))
# ---------------------------------------------------------------------------------------------------------------
def rhu(x):
    return np.floor(x + 0.5)


def compose(base, layers, lights=(), extra=None, grain=None):
    """base: HxWx3 float (0-255); layers: list of (rgba uint8/float, shadow HxWx3 or None); extra: list of HxWx3 multiplicative fields
    applied after the layers (the bounce tints); grain: HxW field added last (8-bit units)"""
    o = base.astype(np.float64)
    keep = np.ones(o.shape[:2], np.float64)
    for L, S in layers:
        Lf = L.astype(np.float64)
        a = Lf[..., 3:4] / 255.0
        if S is not None:
            o = rhu(o * S.astype(np.float64) / 255.0)
        o = rhu(rhu(Lf[..., :3] * a) + o * (1 - a))
        keep *= (1 - a[..., 0])
    for Lt in lights:
        Lm = Lt.astype(np.float64) / 255.0 * keep[..., None]
        o = rhu(255.0 - (255.0 - o) * (1.0 - Lm))
    if extra:
        for t in extra:
            o = o * t
    if grain is not None:
        o = o + grain[..., None]
    return np.clip(rhu(o), 0, 255).astype(np.uint8)


def read_stack(st):
    base = rd(st["base"], "RGB")
    L = []
    for e in st["entries"]:
        a = rd(e["layer"], "RGBA")
        s = rd(e["shadow"], "RGB") if e.get("shadow") else None
        L.append((a, s))
    lights = [rd(p, "RGB") for p in st["lights"]]
    return base, L, lights


def frame_view(img, st, size=(1920, 1080)):
    """the 16:9 camera frame at its sub-pixel frame box, resampled (bicubic) to size: how the room's 1920 frames are made"""
    x0, y0, x1, y1 = st["frame_box"]
    sx, sy = (x1 - x0) / size[0], (y1 - y0) / size[1]
    M = np.float32([[sx, 0, x0 + 0.5 * sx - 0.5], [0, sy, y0 + 0.5 * sy - 0.5]])
    return cv2.warpAffine(img, M, size, flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)


def reproduce_check(st, comp):
    ref = rd(st["frame"], "RGB")
    if st["cfg"].get("frame_kind") == "frame1920":
        mine = frame_view(comp, st, (ref.shape[1], ref.shape[0]))
    else:
        mine = comp
    if mine.shape != ref.shape:
        return dict(error=f"shape {mine.shape} vs {ref.shape}")
    d = np.abs(mine.astype(int) - ref.astype(int)).max(2)
    return dict(max=int(d.max()), mean=round(float(d.mean()), 4), px_over_2=int((d > 2).sum()), compared_to=os.path.relpath(st["frame"], REPO))


# ---------------------------------------------------------------------------------------------------------------
# measurements shared by the finish and the pasted test
# ---------------------------------------------------------------------------------------------------------------
def Lstar(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[..., 0]


def bbox_of(a, pad, shape):
    ys, xs = np.nonzero(a)
    if not len(xs):
        return None
    H, W = shape
    return (slice(max(0, ys.min() - pad), min(H, ys.max() + pad + 1)), slice(max(0, xs.min() - pad), min(W, xs.max() + pad + 1)))


def edge_sigma(L, pts, nrm, half=6.0, min_contrast=8.0):
    """sigma of a blurred step from profiles across the edges (contrast / (max gradient * sqrt(2 pi))), median over the usable points"""
    if len(pts) == 0:
        return None, 0
    t = np.arange(-half, half + 0.01, 0.5, dtype=np.float32)
    mx = (pts[:, 0:1] + nrm[:, 0:1] * t[None, :]).astype(np.float32)
    my = (pts[:, 1:2] + nrm[:, 1:2] * t[None, :]).astype(np.float32)
    prof = cv2.remap(L.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    lo = prof[:, t <= -3.5].mean(1)
    hi = prof[:, t >= 3.5].mean(1)
    con = np.abs(hi - lo)
    g = np.abs(np.diff(prof, axis=1)).max(1) / 0.5
    ok = (con >= min_contrast) & (g > 1e-3)
    if ok.sum() < 12:
        return None, int(ok.sum())
    sg = con[ok] / (g[ok] * math.sqrt(2 * math.pi))
    sg = sg[(sg > 0.15) & (sg < 6.0)]
    if len(sg) < 12:
        return None, len(sg)
    return float(np.median(sg)), int(len(sg))


def sample(m, n, rng):
    ys, xs = np.nonzero(m)
    if len(xs) > n:
        k = rng.choice(len(xs), n, replace=False)
        ys, xs = ys[k], xs[k]
    return np.stack([xs, ys], 1).astype(np.float32)


_NK = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], np.float32)


def noise_sigma(L, m, min_px=200):
    """robust pixel noise of L (L* units) in the flat part of mask m: Immerkaer's kernel (blind to linear shading), its response to white
    noise of sigma s has a standard deviation 6 s; median absolute response x 1.4826 / 6, where the local gradient is low"""
    if m.sum() < min_px:
        return None
    r = cv2.filter2D(L.astype(np.float32), -1, _NK, borderType=cv2.BORDER_REFLECT)
    gb = cv2.GaussianBlur(L, (0, 0), 2.0)
    gm = np.hypot(cv2.Sobel(gb, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gb, cv2.CV_32F, 0, 1, ksize=3)) / 8.0
    flat = m & (gm < 1.2)
    if flat.sum() < min_px:
        flat = m & (gm < np.percentile(gm[m], 30))
    v = r[flat]
    return float(1.4826 * np.median(np.abs(v)) / 6.0) if len(v) >= min_px else None


def plate_reference(base, union, fmask, rng):
    """the plate's edge spread and noise over the whole frame outside every product (the fallback when a product's ring is blank)"""
    L = Lstar(base)
    free = fmask & (cv2.dilate((union > 0.02).astype(np.uint8), np.ones((13, 13), np.uint8)) == 0)
    can = cv2.Canny(np.clip(L * 2.55, 0, 255).astype(np.uint8), 40, 90) > 0
    pp = sample(can & free, 1500, rng)
    s, n = None, 0
    if len(pp):
        Lb = cv2.GaussianBlur(L, (0, 0), 1.0)
        gx, gy = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3)
        ix, iy = pp[:, 0].astype(int), pp[:, 1].astype(int)
        nv = np.stack([gx[iy, ix], gy[iy, ix]], 1)
        nn = np.linalg.norm(nv, axis=1, keepdims=True)
        k = nn[:, 0] > 1e-4
        s, n = edge_sigma(L, pp[k], nv[k] / nn[k])
    return dict(s_plate=s, n_plate_pts=n, noise_plate=noise_sigma(L, free, 2000))


def frame_mask(shape, fb):
    m = np.zeros(shape, bool)
    x0, y0, x1, y1 = [int(round(v)) for v in fb]
    m[y0:y1, x0:x1] = True
    return m


def light_centroid(plate, fmask):
    L = Lstar(plate)
    thr = np.percentile(L[fmask], 98.5)
    ys, xs = np.nonzero(fmask & (L >= thr))
    return (float(xs.mean()), float(ys.mean())) if len(xs) else None


def layer_edge_and_plate_sigma(comp, below_plate, a, union_alpha, fmask, rng, crop, ref=None):
    """edge spread of the layer (composite across its alpha edge) and of the plate (its own edges in a ring 15-120 px round the product)"""
    sl = crop
    A = a[sl]
    Lc = Lstar(comp[sl])
    Lp = Lstar(below_plate[sl])
    inside = A >= 0.5
    if inside.sum() < 60:
        return None
    bnd = inside & ~cv2.erode(inside.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ab = cv2.GaussianBlur(A.astype(np.float32), (0, 0), 1.5)
    gx, gy = cv2.Sobel(ab, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(ab, cv2.CV_32F, 0, 1, ksize=3)
    pts = sample(bnd & fmask[sl], 500, rng)
    if len(pts):
        ix, iy = pts[:, 0].astype(int), pts[:, 1].astype(int)
        nv = np.stack([-gx[iy, ix], -gy[iy, ix]], 1)
        nn = np.linalg.norm(nv, axis=1, keepdims=True)
        keep = nn[:, 0] > 1e-4
        s_layer, n_layer = edge_sigma(Lc, pts[keep], nv[keep] / nn[keep])
    else:
        s_layer, n_layer = None, 0
    # interior texture of the layer
    din = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    can = cv2.Canny(np.clip(Lc * 2.55, 0, 255).astype(np.uint8), 40, 90) > 0
    ip = sample(can & (din > 4) & fmask[sl], 400, rng)
    s_int, n_int = (None, 0)
    if len(ip):
        Lb = cv2.GaussianBlur(Lc, (0, 0), 1.0)
        gx2, gy2 = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3)
        ix, iy = ip[:, 0].astype(int), ip[:, 1].astype(int)
        nv = np.stack([gx2[iy, ix], gy2[iy, ix]], 1)
        nn = np.linalg.norm(nv, axis=1, keepdims=True)
        keep = nn[:, 0] > 1e-4
        s_int, n_int = edge_sigma(Lc, ip[keep], nv[keep] / nn[keep], half=4.0)
    # the plate's edges round the product (no product of the room on them)
    dout = cv2.distanceTransform((~inside).astype(np.uint8), cv2.DIST_L2, 5)
    U = union_alpha[sl] > 0.02
    U = cv2.dilate(U.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
    ring = (dout >= 15) & (dout <= 120) & ~U & fmask[sl]
    canp = cv2.Canny(np.clip(Lp * 2.55, 0, 255).astype(np.uint8), 40, 90) > 0
    pp = sample(canp & ring, 500, rng)
    s_plate, n_plate = (None, 0)
    if len(pp):
        Lb = cv2.GaussianBlur(Lp, (0, 0), 1.0)
        gx3, gy3 = cv2.Sobel(Lb, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(Lb, cv2.CV_32F, 0, 1, ksize=3)
        ix, iy = pp[:, 0].astype(int), pp[:, 1].astype(int)
        nv = np.stack([gx3[iy, ix], gy3[iy, ix]], 1)
        nn = np.linalg.norm(nv, axis=1, keepdims=True)
        keep = nn[:, 0] > 1e-4
        s_plate, n_plate = edge_sigma(Lp, pp[keep], nv[keep] / nn[keep])
    # noise
    n_l = noise_sigma(Lc, (din > 3) & fmask[sl])
    ring_n = (dout >= 8) & (dout <= 150) & ~U & fmask[sl]
    n_p = noise_sigma(Lp, ring_n, 2000)
    src = dict(edge="ring", noise="ring")
    if ref is not None:
        if (s_plate is None or n_plate < 40) and ref.get("s_plate"):
            s_plate, src["edge"] = ref["s_plate"], "frame (the ring has too few plate edges)"
        if n_p is None and ref.get("noise_plate"):
            n_p, src["noise"] = ref["noise_plate"], "frame (the ring is too small)"
    return dict(s_layer=s_layer, n_layer_pts=n_layer, s_interior=s_int, n_interior_pts=n_int, s_plate=s_plate, n_plate_pts=n_plate,
                noise_layer=n_l, noise_plate=n_p, reference=src)


# ---------------------------------------------------------------------------------------------------------------
# the finish
# ---------------------------------------------------------------------------------------------------------------
def grain_field(shape, seed=SEED, sigma_px=0.6):
    rng = np.random.default_rng(seed)
    g = rng.standard_normal(shape).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), sigma_px)
    return g / max(float(g.std()), 1e-6)


def blur_premult(L, sigma, crop):
    out = L.astype(np.float32).copy()
    sl = crop
    c = out[sl]
    a = c[..., 3:4] / 255.0
    pm = np.concatenate([c[..., :3] * a, c[..., 3:4]], -1)
    pm = np.stack([cv2.GaussianBlur(pm[..., i], (0, 0), sigma) for i in range(4)], -1)
    a2 = pm[..., 3:4] / 255.0
    rgb = np.where(a2 > 1e-4, pm[..., :3] / np.maximum(a2, 1e-4), c[..., :3])
    out[sl] = np.concatenate([rgb, pm[..., 3:4]], -1)
    return out


def steepen_alpha(L, k, crop):
    """the alpha ramp of a soft matte made k times steeper round 0.5 (a' = (a - 0.5) k + 0.5), RGB untouched; opaque and empty pixels stay"""
    out = L.astype(np.float32).copy()
    c = out[crop]
    a = c[..., 3] / 255.0
    edge = (a > 0.0) & (a < 1.0)
    a2 = np.where(edge, np.clip((a - 0.5) * k + 0.5, 0, 1), a)
    c[..., 3] = a2 * 255.0
    out[crop] = c
    return out


def unsharp_rgb(L, amount, radius, crop):
    out = L.astype(np.float32).copy()
    c = out[crop]
    for i in range(3):
        b = cv2.GaussianBlur(c[..., i], (0, 0), radius)
        c[..., i] = np.clip(c[..., i] + amount * (c[..., i] - b), 0, 255)
    out[crop] = c
    return out


def light_wrap(L, below, light_xy, crop, max_mix=0.15, width=2.0):
    out = L.astype(np.float32).copy()
    c = out[crop]
    A = c[..., 3] / 255.0
    inside = A >= 0.5
    din = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    w = np.clip(1.0 - (din - 0.5) / width, 0, 1) * inside
    bg = cv2.GaussianBlur(below[crop].astype(np.float32), (0, 0), 2.5)
    Lb, Ll = Lstar(np.clip(bg, 0, 255)), Lstar(np.clip(c[..., :3], 0, 255))
    k = np.clip((Lb - Ll) / 40.0, 0, 1)
    if light_xy is not None:
        ab = cv2.GaussianBlur(A.astype(np.float32), (0, 0), 1.5)
        gx, gy = -cv2.Sobel(ab, cv2.CV_32F, 1, 0, ksize=3), -cv2.Sobel(ab, cv2.CV_32F, 0, 1, ksize=3)     # outward normal
        nn = np.maximum(np.hypot(gx, gy), 1e-6)
        H, W = A.shape
        yy, xx = np.mgrid[0:H, 0:W]
        lx, ly = light_xy[0] - (xx + crop[1].start), light_xy[1] - (yy + crop[0].start)
        ln = np.maximum(np.hypot(lx, ly), 1e-6)
        dot = (gx * lx + gy * ly) / (nn * ln)
        k = k * np.clip(0.25 + 0.75 * dot, 0, 1)
    s = (max_mix * w * k)[..., None]
    c[..., :3] = c[..., :3] * (1 - s) + bg * s
    out[crop] = c
    return out, float(s.max()), int((s[..., 0] > 0.01).sum())


def bounce_tint(L, shape, fmask, max_tint=0.06):
    a = L[..., 3].astype(np.float32) / 255.0
    area = float((a > 0.5).sum())
    if area < 0.003 * fmask.sum():
        return None, None
    crop = bbox_of(a > 0.5, 1, shape)
    rgb = L[..., :3][a > 0.9].astype(np.float32)
    if len(rgb) < 100:
        return None, None
    lab = cv2.cvtColor((rgb[None] / 255.0).astype(np.float32), cv2.COLOR_RGB2LAB)[0]
    C = float(np.median(np.hypot(lab[:, 1], lab[:, 2])))
    if C < 12:
        return None, dict(chroma=round(C, 1), note="grey enough: no bounce")
    col = np.median(rgb, 0)
    tint = col / max(float(col.mean()), 1e-3) - 1.0
    sig = float(np.clip(0.04 * math.sqrt(area), 4, 25))
    pad = int(3 * sig)
    H, W = shape
    sl = (slice(max(0, crop[0].start - pad), min(H, crop[0].stop + pad)), slice(max(0, crop[1].start - pad), min(W, crop[1].stop + pad)))
    m = cv2.GaussianBlur((a[sl] > 0.5).astype(np.float32), (0, 0), sig)
    m = m / max(float(m.max()), 1e-6) * (1 - np.clip(cv2.dilate(a[sl], np.ones((3, 3), np.uint8)) * 1.0, 0, 1))
    field = np.ones((H, W, 3), np.float32)
    field[sl] = 1.0 + max_tint * m[..., None] * np.clip(tint, -1, 1)[None, None, :]
    return field, dict(chroma=round(C, 1), tint=[round(float(v), 3) for v in tint], sigma_px=round(sig, 1))


def dof_sigma_px(depth_m, focus_m, lens_mm, N, px_per_mm):
    A = lens_mm / N
    c_mm = A * np.abs(depth_m - focus_m) / np.maximum(depth_m, 1e-3) * lens_mm / max(focus_m * 1000 - lens_mm, 1e-3)
    return c_mm * px_per_mm / 2.355                       # blur circle diameter as a Gaussian's FWHM


def finish_room(st, base, layers, lights, opts=None):
    """-> (finished layers, finished base, bounce fields, grain field, record). Every finished quantity is per layer or per position."""
    o = dict(dict(grain=1.2, grain_max=2.0, sharp_band=0.10, max_blur=1.6, max_steepen=1.4, wrap=0.15, wrap_px=2.0, bounce=0.06, dof=None),
             **(opts or {}))
    H, W = base.shape[:2]
    fmask = frame_mask((H, W), st["frame_box"])
    rng = np.random.default_rng(SEED)
    light_xy = light_centroid(base, fmask)
    union = np.zeros((H, W), np.float32)
    for L, _ in layers:
        union = np.maximum(union, L[..., 3].astype(np.float32) / 255.0)
    # 0. the stack before, to measure each layer over what is below it
    comp_below = base.astype(np.float64)
    rec = dict(light_centroid=light_xy, layers={})
    out_layers = []
    noises = []
    # the plate's own noise (outside every product) sets the grain
    pref = plate_reference(base, union, fmask, np.random.default_rng(SEED))
    n_plate = pref["noise_plate"]
    rec["plate_reference"] = pref
    depth = o.get("dof")
    for (L, S), e in zip(layers, st["entries"]):
        a = L[..., 3].astype(np.float32) / 255.0
        crop = bbox_of(a > 0.02, 24, (H, W))
        r = dict(slot=e["slot"], product=e["product"])
        if crop is None:
            out_layers.append((L, S))
            r["skipped"] = "empty layer"
            rec["layers"][e["name"]] = r
            continue
        below = comp_below.copy()
        if S is not None:
            below = rhu(below * S.astype(np.float64) / 255.0)
        comp = rhu(rhu(L[..., :3].astype(np.float64) * a[..., None]) + below * (1 - a[..., None]))
        m = layer_edge_and_plate_sigma(comp.astype(np.uint8), below.astype(np.uint8), a, union, fmask, rng, crop, pref)
        Lf = L.astype(np.float32)
        if m:
            r["measured"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}
            sl_, sp = m.get("s_layer"), m.get("s_plate")
            if sl_ and sp:
                ratio = sp / sl_
                r["sharp_ratio_before"] = round(ratio, 3)
                if ratio > 1 + o["sharp_band"]:                  # the plate is softer: the layer is blurred
                    sb = float(min(o["max_blur"], math.sqrt(max(sp ** 2 - sl_ ** 2, 0.0))))
                    Lf = blur_premult(Lf, sb, crop)
                    r["sharpness"] = f"blurred sigma {sb:.2f}"
                elif ratio < 1 - o["sharp_band"]:                # the layer's matte is softer: its alpha ramp is steepened round 0.5
                    k = float(min(o["max_steepen"], 1.0 / ratio))  # (an unsharp mask on RGB leaves a soft matte soft and adds crunch)
                    Lf = steepen_alpha(Lf, k, crop)
                    r["sharpness"] = f"alpha ramp steepened x{k:.2f}"
                else:
                    r["sharpness"] = "inside the band: unchanged"
            if m.get("noise_layer") is not None:
                noises.append((e["name"], m["noise_layer"], m.get("noise_plate") or n_plate))
        if depth is not None:
            ys, xs = np.nonzero(a > 0.5)
            yb, xc = min(H - 1, int(ys.max()) + 2), int(np.median(xs))
            dz = float(depth["m"][yb, xc]) if depth["m"][yb, xc] > 0 else float(np.median(depth["m"][a > 0.5][depth["m"][a > 0.5] > 0]))
            sg = float(dof_sigma_px(np.array([dz]), depth["focus"], depth["lens"], depth["N"], depth["px_per_mm"])[0])
            r["dof"] = dict(depth_m=round(dz, 3), sigma_px=round(sg, 3))
            if sg >= 0.35:
                Lf = blur_premult(Lf, sg, crop)
        # light wrap (over the stack below the layer, after its own shadow)
        Lf, smax, spx = light_wrap(Lf, below.astype(np.float32), light_xy, crop, o["wrap"], o["wrap_px"])
        r["light_wrap"] = dict(max_mix=round(smax, 3), px=spx)
        Lu = np.clip(rhu(Lf), 0, 255).astype(np.uint8)
        out_layers.append((Lu, S))
        comp_below = rhu(rhu(Lu[..., :3].astype(np.float64) * (Lu[..., 3:4] / 255.0)) + below * (1 - Lu[..., 3:4] / 255.0))
        rec["layers"][e["name"]] = r
    # grain: one field by position; its strength from the plate and the noisiest layer
    g_amp = o["grain"]
    if n_plate:
        worst = max([n for _, n, _ in noises] or [n_plate])
        if worst > 1.25 * n_plate:
            need = math.sqrt(max(worst ** 2 - (1.25 * n_plate) ** 2, 0) / (1.25 ** 2 - 1))
            g_amp = float(np.clip(need, o["grain"], o["grain_max"]))
    G = grain_field((H, W))
    Lb = Lstar(base) / 100.0
    wmid = np.clip(4 * Lb * (1 - Lb), 0.25, 1.0)
    grain = G * g_amp * wmid
    rec["grain"] = dict(amplitude_8bit=round(g_amp, 3), seed=SEED, grain_px=0.6, midtone_weight="4 l (1 - l), floor 0.25, from the plate's L*")
    # per-layer top-up for a layer smoother than the plate (a second positional field, inside that layer's alpha only)
    G2 = grain_field((H, W), seed=SEED + 1)
    topped = []
    final_layers = []
    for (L, S), e in zip(out_layers, st["entries"]):
        nl = next((n for nm, n, _ in noises if nm == e["name"]), None)
        npl = next((p for nm, _, p in noises if nm == e["name"]), None) or n_plate
        if nl is not None and npl and nl < 0.8 * npl:
            amt = math.sqrt(max(npl ** 2 - nl ** 2, 0.0))
            Lf = L.astype(np.float32)
            Lf[..., :3] = Lf[..., :3] + (G2 * amt * wmid)[..., None]
            L = np.clip(rhu(Lf), 0, 255).astype(np.uint8)
            topped.append((e["name"], round(amt, 3)))
        final_layers.append((L, S))
    rec["grain"]["top_up"] = topped
    # bounce tints (one field per coloured product)
    bounces = []
    for (L, _), e in zip(final_layers, st["entries"]):
        f, info = bounce_tint(L, (H, W), fmask, o["bounce"])
        if info:
            rec["layers"][e["name"]]["bounce"] = info
        if f is not None:
            bounces.append(f)
    # the plate: depth of field by position
    fbase = base.astype(np.float32)
    if depth is not None:
        sgm = dof_sigma_px(depth["m"], depth["focus"], depth["lens"], depth["N"], depth["px_per_mm"])
        sgm[depth["m"] <= 0] = 0
        lv = [0.0, 0.5, 1.0, 1.5]
        stack = [fbase] + [np.stack([cv2.GaussianBlur(fbase[..., i], (0, 0), s) for i in range(3)], -1) for s in lv[1:]]
        idx = np.clip(np.interp(sgm, lv, np.arange(len(lv))), 0, len(lv) - 1)
        i0 = np.floor(idx).astype(int)
        i1 = np.minimum(i0 + 1, len(lv) - 1)
        t = (idx - i0)[..., None]
        out = np.zeros_like(fbase)
        for k in range(len(lv)):
            out += stack[k] * ((i0 == k)[..., None] * (1 - t) + (i1 == k)[..., None] * t)
        fbase = out
        rec["dof_plate"] = dict(sigma_px_p50=round(float(np.median(sgm[depth['m'] > 0])), 3), sigma_px_max=round(float(sgm.max()), 3),
                                focus_m=depth["focus"], N=depth["N"], lens_mm=depth["lens"])
    return final_layers, fbase, bounces, grain, rec


def load_depth(cfg, N=5.6, focus=None):
    if not cfg.get("depth"):
        return None
    dj = json.load(open(os.path.join(R, cfg["depth_json"])))
    enc = rd(os.path.join(R, cfg["depth"])).astype(np.float64)
    dn, df = dj["d_near_m"], dj["d_far_m"]
    inv = (enc - 1) / 65534.0 * (1 / dn - 1 / df) + 1 / df
    m = np.where(enc > 0, 1.0 / np.maximum(inv, 1e-6), 0.0)
    fb = dj.get("frame_box") or [77.49, 43.43, 2642.51, 1486.57]
    px_per_mm = (fb[2] - fb[0]) / 36.0
    lens = dj["camera"].get("lens_mm") or dj["camera"].get("lens")
    if focus is None:
        focus = float(np.median(m[m > 0]))
    return dict(m=m, focus=focus, lens=lens, N=N, px_per_mm=px_per_mm, source=os.path.relpath(os.path.join(R, cfg["depth"]), REPO))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("room", choices=sorted(ROOMS))
    ap.add_argument("--out", default=None, help="the finished frame's path (default: <room dir>/<frame>-fb13prep.png)")
    a = ap.parse_args()
    st = load_room(a.room)
    base, layers, lights = read_stack(st)
    dep = load_depth(st["cfg"])
    fl, fb_, bounces, grain, rec = finish_room(st, base, layers, lights, dict(dof=dep))
    img = compose(fb_, fl, lights, bounces, grain)
    out = a.out or os.path.join(R, st["cfg"]["out_dir"], st["cfg"]["out_name"] + "-fb13prep.png")
    Image.fromarray(img).save(out, optimize=True)
    print(json.dumps(dict(out=out, grain=rec["grain"]), indent=1))


if __name__ == "__main__":
    main()
