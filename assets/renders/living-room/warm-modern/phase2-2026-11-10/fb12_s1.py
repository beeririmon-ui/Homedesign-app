#!/usr/bin/env python3
"""
fb12_s1.py: FB12 stage 1, the IDANA Olia coffee table as its own product layer in M0 (render-agent, 2026-11-25).
Brief: briefs/wm-fb12-stage1-olia-2026-11-25.md; spec: docs/proposals/wm-fb12-2026-11-25.md a.3, a.6 (stage 1), a.7, a.10.
Card: data/products/living-room/coffee-table/coffee-table-idana-javorina-olia-natural.json (J-OF120-N, 120 x 65 x 38, natural oak, oil).
NEW FILES ONLY: every stage-0 / R9 file is read, never written (stage 0's helpers are imported read-only from fb12_s0.py).

The fit (a.10): centre (0.30, 1.72), angle 0, top at Z 0.38, under the pendant group, on the M0 1.2 camera of docs/house-plan.json.
The table, measured on the supplier's photos (the scratchpad only; references, never pixels in a layer): a bent "waterfall" in solid
oak, one slab about 2 cm thick (2.2 in the clay) that rolls over at both ends (outer radius ~3.5 cm) into two slab legs the full depth
of the top (65), the legs' bottom corners rounded (~3 cm); open between the legs.

Commands (each writes new files only):
  clay      the table's clay at the real dimensions: a sphere-traced SDF on the M0 camera, 3 x 3 supersampled (alpha, parts, normals)
  input     the edit's input: the clean plate with the rug (base-fb12s0 + the rug's shadow + the rug, 8-bit stack) and the clay painted
  fetch URL download the render into raw/ (2720 x 1530 expected)
  cut       register + tone-match the render, cut the table (z 57) and its contact shadow (z 56, extract.shadow_one, frozen recipe)
  group     the bowl and the candle holders re-seated on the oak (code, 0 tokens): moved with their shadows, re-masked to the new top
  build     the new manifest's defaults A / B / C (8-bit stack where it changed, the stage-0 truths' bytes elsewhere), frames, sheet
"""
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")
LAY = os.path.join(P2, "layers")
OUT = os.environ.get("FB12_OUT", P2)                 # new files only; a scratch folder while developing
WORK = os.path.join(OUT, "work-fb12s1")
TAG = "fb12s1"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
CACHE = os.environ.get("FB12_CACHE", os.path.join(SCR, "fb12s1-cache"))   # big intermediates (the registered render, the edits' input):
                                                                          # rebuilt by `input` and `cut` when missing; never in the repo


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S0 = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))   # read-only: geometry (M0 1.2), io, compose8
S0.MASKS = os.path.join(P2, "work-fb12s0", "fb12s0-masks.npz")   # stage 0's split of the r4 clay (sofa / old table / armchair)
W, H = S0.W, S0.H
f8, u8, s2l, l2s, lum, sha, rel, save_png = S0.f8, S0.u8, S0.s2l, S0.l2s, S0.lum, S0.sha, S0.rel, S0.save_png
CAM = S0.CAM

# ------------------------------------------------------------------------------------------------- the table (plan metres)
T = dict(cx=0.30, cy=1.72, L=1.20, D=0.65, Hh=0.38, t=0.022, R=0.035, rb=0.03)
X0, X1 = T["cx"] - T["L"] / 2, T["cx"] + T["L"] / 2
Y0, Y1 = T["cy"] - T["D"] / 2, T["cy"] + T["D"] / 2
BBOX = (1280, 1120, 2200, 1530)                       # work px window that holds the table (x0, y0, x1, y1)


def _seg_d(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    h = np.clip(((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz), 0, 1)
    return np.hypot(px - ax - h * vx, pz - az - h * vz)


def _arc_d(px, pz, cx, cz, r, sx, sz):
    """distance to the quarter arc of radius r about (cx, cz) in the quadrant (sign sx of x, sign sz of z)"""
    vx, vz = px - cx, pz - cz
    inq = (vx * sx >= 0) & (vz * sz >= 0)
    d_in = np.abs(np.hypot(vx, vz) - r)
    e1 = np.hypot(vx - sx * r, vz)
    e2 = np.hypot(vx, vz - sz * r)
    return np.where(inq, d_in, np.minimum(e1, e2))


def sdf(P):
    """signed distance to the Olia table: the XZ profile (one slab of thickness t rolled over at both ends with outer radius R, the legs
    to the floor) extruded over the depth D, the legs' bottom corners rounded rb in YZ"""
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    t, R = T["t"], T["R"]
    rc = R - t / 2
    zt = T["Hh"] - t / 2
    cz = T["Hh"] - R
    xl, xr = X0 + t / 2, X1 - t / 2
    cxl, cxr = X0 + R, X1 - R
    d = np.minimum.reduce([
        _seg_d(X, Z, xl, -1.0, xl, cz),
        _arc_d(X, Z, cxl, cz, rc, -1, 1),
        _seg_d(X, Z, cxl, zt, cxr, zt),
        _arc_d(X, Z, cxr, cz, rc, 1, 1),
        _seg_d(X, Z, xr, cz, xr, -1.0)])
    s_xz = d - t / 2
    # YZ: a rounded box Y Y0..Y1, Z 0..1.0 (its top corners far above the table), radius rb
    qy = np.abs(Y - T["cy"]) - (T["D"] / 2 - T["rb"])
    qz = np.abs(Z - 0.5) - (0.5 - T["rb"])
    s_yz = np.hypot(np.maximum(qy, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qy, qz), 0) - T["rb"]
    return np.maximum(s_xz, s_yz)


def cam_basis():
    a = math.radians(CAM["yaw_deg_left"])
    fwd = np.array([-math.sin(a), -math.cos(a), 0.0])
    right = np.array([math.cos(a), -math.sin(a), 0.0])
    return np.array(CAM["loc"], np.float64), fwd, right


def rays(xs, ys):
    """work px -> unit ray directions (inverse of fb12_s0.project)"""
    C, fwd, right = cam_basis()
    fx = CAM.get("lens", 24) / 36.0
    fy = fx * 16 / 9
    u = (xs * S0.CANVAS[0] / W - 116) / 3840.0
    v = (ys * S0.CANVAS[1] / H - 65) / 2160.0
    a = (u - CAM["u0"]) / fx
    b = (CAM["v0"] - v) / fy
    D = fwd[None, :] + a[:, None] * right[None, :] + b[:, None] * np.array([0, 0, 1.0])[None, :]
    return C, D / np.linalg.norm(D, axis=1, keepdims=True)


def trace(xs, ys, iters=160):
    C, D = rays(xs.astype(np.float64), ys.astype(np.float64))
    t = np.full(len(xs), 1.5)
    hit = np.zeros(len(xs), bool)
    alive = np.ones(len(xs), bool)
    for _ in range(iters):
        idx = np.nonzero(alive)[0]
        if not len(idx):
            break
        P = C[None, :] + t[idx, None] * D[idx]
        s = sdf(P)
        h = s < 2e-5
        hit[idx[h]] = True
        alive[idx[h]] = False
        t[idx[~h]] += np.maximum(s[~h], 1e-5)
        far = t[idx] > 6.0
        alive[idx[far]] = False
    P = C[None, :] + t[:, None] * D
    return hit, P, t


def normals(P, e=2e-4):
    n = np.zeros_like(P)
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        n[:, k] = sdf(P + d) - sdf(P - d)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


def part_of(P, n):
    """0 none, 1 top surface, 2 front edge (Y face, any part), 3 left leg inner face, 4 right leg inner face, 5 bends, 6 other"""
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    p = np.full(len(P), 6, np.int8)
    p[(n[:, 2] > 0.9) & (Z > T["Hh"] - 0.004)] = 1
    p[n[:, 1] > 0.9] = 2
    p[(n[:, 0] > 0.9) & (X < T["cx"])] = 3
    p[(n[:, 0] < -0.9) & (X > T["cx"])] = 4
    bend = ((X < X0 + T["R"]) | (X > X1 - T["R"])) & (Z > T["Hh"] - T["R"]) & (np.abs(n[:, 1]) < 0.9)
    p[bend] = 5
    return p


def clay():
    """the clay at the work size, 3 x 3 supersampled inside BBOX: alpha (coverage), part (majority), shade, depth"""
    os.makedirs(WORK, exist_ok=True)
    x0, y0, x1, y1 = BBOX
    ss = 3
    gy, gx = np.mgrid[y0:y1, x0:x1]
    offs = [(i + 0.5) / ss - 0.5 for i in range(ss)]
    acc = np.zeros(gx.shape, np.float32)
    sh = np.zeros(gx.shape, np.float32)
    dep = np.full(gx.shape, np.inf, np.float32)
    parts = np.zeros(gx.shape + (7,), np.float32)
    Lk = np.array([-0.72, 0.10, 0.69])
    Lk /= np.linalg.norm(Lk)
    for oy in offs:
        for ox in offs:
            xs = (gx + 0.5 + ox).ravel().astype(np.float64)     # pixel centres at +0.5 (OpenCV / PIL convention)
            ys = (gy + 0.5 + oy).ravel().astype(np.float64)
            hit, P, tt = trace(xs - 0.5, ys - 0.5)                # project() maps to pixel-index coordinates
            n = normals(P)
            pr = np.where(hit, part_of(P, n), 0)
            lam = np.clip(n @ Lk, 0, 1)
            shade = 0.46 + 0.50 * lam + 0.10 * np.clip(n[:, 2], 0, 1)
            acc += hit.reshape(gx.shape)
            sh += np.where(hit, shade, 0).reshape(gx.shape)
            dep = np.minimum(dep, np.where(hit, tt, np.inf).reshape(gx.shape))
            for k in range(7):
                parts[..., k] += (pr == k).reshape(gx.shape)
    a = acc / ss ** 2
    full = lambda z, v=0: np.pad(z, ((y0, H - y1), (x0, W - x1)), constant_values=v)  # noqa: E731
    out = dict(alpha=full(a).astype(np.float32), shade=full(sh / np.maximum(acc, 1)).astype(np.float32),
               part=full(np.argmax(parts, -1).astype(np.int8)), depth=full(np.where(np.isfinite(dep), dep, 0).astype(np.float32)))
    np.savez_compressed(os.path.join(WORK, f"clay-{TAG}.npz"), **out)
    return out


def load_clay():
    z = np.load(os.path.join(WORK, f"clay-{TAG}.npz"))
    return {k: z[k] for k in z.files}


def clay_measures(c):
    """the clay's own numbers: the box, the corners, the air under the top"""
    a = c["alpha"]
    ys, xs = np.nonzero(a > 0.5)
    pr = {k: S0.project(*p) for k, p in dict(
        top_front_left=(X0, Y1, T["Hh"]), top_front_right=(X1, Y1, T["Hh"]), top_back_left=(X0, Y0, T["Hh"]),
        top_back_right=(X1, Y0, T["Hh"]), leg_left_front_bottom=(X0 + T["t"], Y1, 0.0), leg_right_front_bottom=(X1 - T["t"], Y1, 0.0),
        leg_left_back_bottom=(X0 + T["t"], Y0, 0.0), leg_right_back_bottom=(X1 - T["t"], Y0, 0.0)).items()}
    fb = S0.FRAME_BOX
    u = lambda x: (x - fb[0]) / (fb[2] - fb[0])   # noqa: E731
    v = lambda y: (y - fb[1]) / (fb[3] - fb[1])   # noqa: E731
    # the air: along the front plane (Y1) at mid height Z 0.19, the share of the table's length that is open (no leg)
    Xs = np.linspace(X0, X1, 1201)
    Zm = 0.19
    P = np.stack([Xs, np.full_like(Xs, T["cy"]), np.full_like(Xs, Zm)], -1)
    solid = sdf(P) <= 0
    return dict(bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                bbox_frame_uv=[round(u(xs.min()), 4), round(u(xs.max() + 1), 4), round(v(ys.min()), 4), round(v(ys.max() + 1), 4)],
                corners_px={k: [round(p[0], 1), round(p[1], 1)] for k, p in pr.items()},
                corners_frame_uv={k: [round(u(p[0]), 4), round(v(p[1]), 4)] for k, p in pr.items()},
                air_share_of_length=round(float(1 - solid.mean()), 3),
                alpha_px=int((a > 0.5).sum()), frame_bottom_y=round(fb[3], 2))


# ------------------------------------------------------------------------------------------------- the edit's input
def stage0_manifest():
    return json.load(open(os.path.join(LAY, "manifest-fb12s0.json")))


def plate_with_rug():
    man = stage0_manifest()
    base8 = np.asarray(Image.open(os.path.join(LAY, "base-fb12s0.png")).convert("RGB"))
    rug = next(l_ for l_ in man["layers"] if l_["id"] == "rug")
    rsh = next(l_ for l_ in man["layers"] if l_["id"] == "rug-shadow")
    return S0.compose8(base8, [("rug", os.path.join(LAY, rug["file"]), os.path.join(LAY, rsh["file"]))], {})


CLAY_RGB = np.array([0.80, 0.785, 0.76], np.float32)     # phase2_wm.CLAY


def make_input():
    os.makedirs(os.path.join(OUT, "inputs"), exist_ok=True)
    c = load_clay()
    below8 = plate_with_rug()
    below = below8.astype(np.float32) / 255
    a = c["alpha"][..., None]
    clay_img = CLAY_RGB[None, None, :] * np.clip(c["shade"], 0.35, 1.1)[..., None]
    out = below * (1 - a) + np.clip(clay_img, 0, 1) * a
    p = os.path.join(OUT, "inputs", f"{TAG}-input.png")
    save_png(p, u8(out))
    os.makedirs(CACHE, exist_ok=True)
    pb = os.path.join(CACHE, f"below-{TAG}.png")
    save_png(pb, below8)
    rec = dict(pass_=TAG, below="(scratch cache) below-fb12s1.png = plate_with_rug(); also the rug edit's input", below_is="layers/base-fb12s0.png + rug-shadow-fb12s0 + rug-fb12s0 (the manifest's 8-bit formula); "
               "no other layer (the brief: the clean plate with the rug, without the bowl and the candle holders)",
               below_sha256=sha(pb), clay=dict(T, centre=[T["cx"], T["cy"]], angle_deg=0, measures=clay_measures(c),
                                               how="sphere-traced SDF on docs/house-plan.json M0 (fb12_s0.project inverted), 3 x 3 "
                                                   "supersampled; plain clay (phase2_wm.CLAY) lit from the window side"),
               sha256=sha(p))
    json.dump(rec, open(os.path.join(OUT, "inputs", f"{TAG}-input.json"), "w"), indent=1)
    return p, rec


# ------------------------------------------------------------------------------------------------- the render -> the layer
def X_():
    """extract.py (read-only): the frozen recipe (tone_match, lab_diff, cut_one, shadow_one) with the table's SPEC row added in memory"""
    if P2 not in sys.path:
        sys.path.insert(0, P2)
    import extract as X  # noqa: E402
    X.SPEC.setdefault("coffee-table", dict(margin=30, band=SHADOW_BAND, onto="floor", z=57))
    return X


TONE_GROW = 150
SHADOW_BAND = 200         # px: extract.shadow_one's band for the table (the floor items' 36-40 are for objects 20-40 cm across). With 60
                          # the recipe's own ring (band + 12..60 px) sits in the table's shade under the top and cancels it (the table
                          # floats); at 200 the ring is the open rug beside the table and the shade under the top and the soft cast to the
                          # front-right (the window pool on the rug, light from the back-left) are kept, falling off as exp(-d / 100 px)
RAW = os.path.join(OUT, "raw", f"{TAG}-seedream.png")


def fetch(url):
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "240", "-o", RAW, "-w", "%{http_code}", url], capture_output=True, text=True)
    if r.stdout.strip() != "200":
        raise SystemExit(f"download failed {r.stdout} {r.stderr}")
    return RAW


def fixed_alpha():
    """fa' (stage 0): the sofa and the armchair only"""
    return f8(os.path.join(P2, "work-fb12s0", "fixed-furniture-fb12s0.png"))[..., 3]


def floor_surface():
    """the floor the table's shadow may fall on: the r4 clay's floor plus the old table's footprint (floor in the clean plate), minus fa'"""
    X = X_()
    surf = X.surfaces()
    T0 = S0.table_region(S0.masks())
    fa = fixed_alpha()
    return (surf["floor"] | T0) & ~(fa > 0.02), fa


def cut():
    X = X_()
    PW = X.PW
    raw = PW.load(RAW)
    returned = list(Image.open(RAW).size)
    if raw.shape[1::-1] != (W, H):
        raw = cv2.resize(raw, (W, H), interpolation=cv2.INTER_LANCZOS4)
    inp = PW.load(os.path.join(OUT, "inputs", f"{TAG}-input.png"))
    below = PW.load(os.path.join(CACHE, f"below-{TAG}.png"))
    c = load_clay()
    V = c["alpha"]
    reg, M = PW.register(raw, inp)
    zone = X.dil(V > 0.02, X.SPEC["coffee-table"]["margin"])
    # the exposure: the gain field from OUTSIDE the zone grown by TONE_GROW px. The model relit the rug round the table (the input's
    # window pool on the rug is dimmed in the render, out to ~250 px): a gain read next to the table would lift the oak by ~1.34 (top / rug
    # 0.90-1.11 against the SKU photos' 0.78-0.93); read beyond it, the gain is the render's global one (~1.08, top / rug 0.72-0.89)
    regt, G = X.tone_match(reg, below, X.dil(zone, TONE_GROW))
    dE = X.lab_diff(regt, below)
    floor, fa = floor_surface()
    front = np.zeros(V.shape, bool)                       # nothing stands in front of the table in M0 (fa' is behind it)
    fill, a = X.cut_one("coffee-table", regt, below, V, zone, front, dE)
    surf = dict(floor=floor, front=fa > 0.02)
    sh = X.shadow_one("coffee-table", a, regt, below, surf, {})
    drift = np.abs(PW.Lstar(regt) - PW.Lstar(below))[~X.dil(zone, 40)]
    rec = dict(returned_px=returned, register_to_input=np.round(M, 4).tolist(),
               tone_gain_median=[round(float(np.median(G[..., k][zone])), 4) for k in range(3)], tone_zone_grow_px=TONE_GROW,
               model_drift_outside_zone_L_after_tone=dict(median=round(float(np.median(drift)), 2), p95=round(float(np.percentile(drift, 95)), 2)),
               alpha_px=int((a > 0.5).sum()), soft_px=int(((a > 0.02) & (a < 0.98)).sum()),
               clay_covered=round(float(((V > 0.5) & (a > 0.5)).sum() / max(1, (V > 0.5).sum())), 4),
               outside_clay_px=int(((a > 0.5) & ~X.dil(V > 0.5, 2)).sum()),
               iou_cut_vs_clay=round(float(((V > 0.5) & (a > 0.5)).sum() / max(1, ((V > 0.5) | (a > 0.5)).sum())), 4),
               shadow_px_below_0_97=int((sh < 0.97).sum()), shadow_min=round(float(sh.min()), 3), shadow_band_px=SHADOW_BAND)
    os.makedirs(WORK, exist_ok=True)
    np.savez_compressed(os.path.join(CACHE, f"cut-{TAG}.npz"), regt=u8(regt), a=a.astype(np.float32), sh=sh.astype(np.float32))
    lp, sp = save_table(regt, a, sh)
    rec["files"] = dict(layer=rel(lp), shadow=rel(sp))
    json.dump(rec, open(os.path.join(WORK, f"cut-{TAG}.json"), "w"), indent=1)
    return rec


CARD = "coffee-table-idana-javorina-olia-natural"
TABLE_LAYER = os.path.join("coffee-table", f"{CARD}.png")
TABLE_SHADOW = os.path.join("coffee-table", f"{CARD}-shadow.png")


def decontaminate(rgb, a, solid=0.98):
    """the soft edge's colour: the nearest solid pixel of the product (the render's edge pixels carry what stood behind the table in
    the render: the bare sofa, the lit rug), so the edge never brings that colour over another background (a cushion set's throw)"""
    sol = (a >= solid).astype(np.uint8)
    _, lab_ = cv2.distanceTransformWithLabels(1 - sol, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(sol)
    lut = np.zeros((int(lab_.max()) + 1, 3), np.float32)
    lut[lab_[ys, xs]] = rgb[ys, xs]
    soft = (a > 0) & (a < solid)
    out = rgb.copy()
    out[soft] = lut[lab_[soft]]
    return out, int(soft.sum())


def save_table(regt, a, sh):
    """the layer: RGBA straight alpha (the tone-matched render inside the cut, 0 elsewhere; the soft edge decontaminated); the shadow:
    RGB multiply, 255 = none"""
    a8 = u8(a)
    rgb, _ = decontaminate(regt, a8.astype(np.float32) / 255)
    rgb8 = np.where((a8 > 0)[..., None], u8(rgb), 0).astype(np.uint8)
    lp = save_png(os.path.join(OUT, "layers", TABLE_LAYER), np.dstack([rgb8, a8]))
    s8 = u8(sh)
    s8[a8 == 255] = 255                                   # under the opaque table the shadow is never seen: none
    s8[fixed_alpha() > 0.5] = 255                         # never on the sofa or the armchair (the recipe's 2 px blur leaks ~1 px onto them)
    sp = save_png(os.path.join(OUT, "layers", TABLE_SHADOW), np.repeat(s8[..., None], 3, 2))
    return lp, sp


# ------------------------------------------------------------------------------------------------- the table's fidelity measures
def px_per_cm(P, axis):
    d = np.zeros(3)
    d[axis] = 0.01
    a, b = np.array(S0.project(*P)), np.array(S0.project(*(np.array(P) + d)))
    return float(np.hypot(*(b - a)))


def measures():
    """the cut against the clay at the real dimensions (edges in cm), the slab's thickness on the render, the air under the top, the tone"""
    c = load_clay()
    V = c["alpha"] > 0.5
    L8 = np.asarray(Image.open(os.path.join(OUT, "layers", TABLE_LAYER)))
    A = L8[..., 3] > 127
    rgb = L8[..., :3].astype(np.float32) / 255
    out = {}

    def first(m, axis, rev=False):
        idx = np.arange(m.shape[axis])
        big = m.shape[axis] + 1
        if rev:
            return np.where(m.any(axis), np.max(np.where(m, idx[:, None] if axis == 0 else idx[None, :], -1), axis=axis), -1)
        return np.where(m.any(axis), np.min(np.where(m, idx[:, None] if axis == 0 else idx[None, :], big), axis=axis), -1)
    # ends (length): leftmost / rightmost column per row, in rows where both have the end
    ends = {}
    for nm, rows, rev, P in (("left_end", (1290, 1440), False, (X0, Y1, 0.2)), ("right_end", (1260, 1360), True, (X1, Y1, 0.3))):
        y0, y1 = rows
        a_ = first(A[y0:y1], 1, rev)
        v_ = first(V[y0:y1], 1, rev)
        ok = (a_ >= 0) & (v_ >= 0)
        dpx = (a_[ok] - v_[ok]) * (1 if rev else -1)          # + = the render wider than the clay
        ends[nm] = dict(median_px=round(float(np.median(dpx)), 2), max_abs_px=int(np.abs(dpx).max()),
                        median_cm=round(float(np.median(dpx)) / px_per_cm(P, 0), 2), max_abs_cm=round(float(np.abs(dpx).max()) / px_per_cm(P, 0), 2))
    out["ends_vs_clay"] = ends
    out["length_cm"] = round(120 + ends["left_end"]["median_cm"] + ends["right_end"]["median_cm"], 1)
    # the top's back edge (depth) and the legs' bottoms (height): first / last row per column
    cols = np.arange(1500, 2080)
    a_ = first(A[:, cols], 0)
    v_ = first(V[:, cols], 0)
    ok = (a_ >= 0) & (v_ >= 0)
    dpx = (v_[ok] - a_[ok])                                   # + = the render's back edge higher (deeper) than the clay
    pc = px_per_cm((T["cx"], Y0, T["Hh"]), 1)
    out["back_edge_vs_clay"] = dict(median_px=round(float(np.median(dpx)), 2), max_abs_px=int(np.abs(dpx).max()),
                                    median_cm=round(float(np.median(dpx)) / pc, 2))
    legs = {}
    for nm, (c0, c1), P in (("left_leg_bottom", (1345, 1460), (X0 + 0.01, T["cy"], 0.0)),):
        cs = np.arange(c0, c1)
        a_ = first(A[:, cs], 0, True)
        v_ = first(V[:, cs], 0, True)
        ok = (a_ >= 0) & (v_ >= 0) & (v_ < 1486)
        dpx = a_[ok] - v_[ok]
        legs[nm] = dict(median_px=round(float(np.median(dpx)), 2), max_abs_px=int(np.abs(dpx).max()),
                        median_cm=round(float(np.median(dpx)) / px_per_cm(P, 2), 2))
    rows = np.arange(1400, 1525)
    a_ = first(A[rows][:, 2040:], 1) + 2040
    v_ = first(V[rows][:, 2040:], 1) + 2040
    dpx = v_ - a_                                             # + = the render's right leg reaches further left (thicker) than the clay
    legs["right_leg_inner_edge"] = dict(median_px=round(float(np.median(dpx)), 2), max_abs_px=int(np.abs(dpx).max()),
                                        median_cm=round(float(np.median(dpx)) / px_per_cm((X1 - T["t"], T["cy"], 0.1), 0), 2),
                                        note="the render shows the right leg's inner face a little wider than the clay near the floor")
    out["legs_vs_clay"] = legs
    # the slab's thickness: between the legs, the front edge face is the band from the last bright top row to the cut's bottom
    lum_ = lum(s2l(rgb))
    th = []
    for x in range(1470, 2060, 6):
        col = A[:, x]
        ys = np.nonzero(col)[0]
        if not len(ys):
            continue
        brk = np.nonzero(np.diff(ys) > 1)[0]
        yb = ys[brk[0] if len(brk) else len(ys) - 1] + 1     # the end of the first run (the top + its front edge)
        seg = cv2.GaussianBlur(lum_[:, x:x + 1], (1, 0), 0.8)[yb - 30:yb, 0] if yb > 30 else None
        if seg is None:
            continue
        g = np.diff(seg)
        k = int(np.argmin(g[:-2]))                           # the strongest fall: the lit top -> the edge face
        th.append(yb - (yb - 30 + k + 1))
    pcz = px_per_cm((T["cx"], Y1, T["Hh"]), 2)

    def run_bottom(col):
        ys = np.nonzero(col)[0]
        if not len(ys):
            return None
        brk = np.nonzero(np.diff(ys) > 1)[0]
        return ys[brk[0] if len(brk) else len(ys) - 1] + 1
    sb = [run_bottom(A[:, x]) - run_bottom(V[:, x]) for x in range(1480, 2050, 10) if run_bottom(A[:, x]) and run_bottom(V[:, x])]
    out["slab_thickness"] = dict(silhouette_bottom_vs_clay_px=dict(median=float(np.median(sb)), min=int(min(sb)), max=int(max(sb))),
                                 face_band_median_px=float(np.median(th)), face_band_p25_p75_px=[float(np.percentile(th, 25)), float(np.percentile(th, 75))],
                                 face_band_cm=round(float(np.median(th)) / pcz, 2), clay_cm=T["t"] * 100, px_per_cm=round(pcz, 2),
                                 note="the slab's silhouette (the top's surface + its edge) ends where the clay's 2.2 cm slab ends (median 0 px); "
                                      "the darker edge face itself reads ~1.4 cm, the rest is the hand-eased rounding that catches the light. "
                                      "The SKU photos read ~2 cm (1.7-2.5); the brief's 3-4 cm does not match the product")
    # the air under the top: along the front plane at mid height (Z 0.19), the share of the length where the cut is open
    Xs = np.linspace(X0, X1, 600)
    pts = np.array([S0.project(x, Y1, 0.19) for x in Xs])
    inside = (pts[:, 1] < H - 1)
    iy, ix = np.clip(np.round(pts[:, 1]).astype(int), 0, H - 1), np.clip(np.round(pts[:, 0]).astype(int), 0, W - 1)
    out["air_under_top"] = dict(plan_share_of_length=clay_measures(c)["air_share_of_length"],
                                image_share_cut=round(float((~A[iy, ix])[inside].mean()), 3), image_share_clay=round(float((~V[iy, ix])[inside].mean()), 3),
                                rule=">= 0.60", note="plan: the length between the slab legs (clay, Z 0.19); image: the front plane's mid-height line "
                                "through the picture (the left leg's inner face is seen behind it, so the image share is lower for the clay too)")
    out["iou_cut_vs_clay"] = round(float((A & V).sum() / max(1, (A | V).sum())), 4)
    # the tone: the top against the rug beside the table, the same ratio as on the SKU's own photos
    part = c["part"]
    top = cv2.erode(((part == 1) & (c["alpha"] > 0.99) & A).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    below = f8(os.path.join(CACHE, f"below-{TAG}.png"), "RGB")
    Mx = np.array([0.2126, 0.7152, 0.0722], np.float32)
    Yt = float(np.median(s2l(rgb[top]) @ Mx))
    rugs = dict(rug_left=(1000, 1250, 1250, 1340), rug_right=(2250, 1420, 2550, 1520))
    labt = cv2.cvtColor(np.ascontiguousarray(rgb[top][None]), cv2.COLOR_RGB2LAB)[0]
    out["tone"] = dict(top_Lab_median=[round(float(np.median(labt[:, k])), 1) for k in range(3)],
                       top_over_rug_Y={k: round(Yt / float(np.median(s2l(below[y0:y1, x0:x1].reshape(-1, 3)) @ Mx)), 3) for k, (x0, y0, x1, y1) in rugs.items()},
                       sku_top_over_rug_Y=dict(real_photo_2=0.775, real_photo_3_grazing=0.925),
                       sku_after_white_balance=dict(L_lit_top=[68.3, 69.3], hsl_S_lit=[25, 33], hue_deg=[29, 30],
                                                    method="the scratchpad script: white balance on the photo's own white cabinets, median of the lit top"),
                       note="L* of a photographed surface depends on its exposure: the check is relative, oak top / the cream rug beside it")
    json.dump(out, open(os.path.join(WORK, f"measures-{TAG}.json"), "w"), indent=1)
    return out


# ------------------------------------------------------------------------------------------------- stage 0's leftovers
def interior():
    """the rug seen through the table's open base: the region enclosed by the table's opaque cut, closed by the canvas bottom and by a
    line from the left leg's lowest point down to it (that short line lies in the overscan, below the camera frame's bottom 1486.6)"""
    A = np.asarray(Image.open(os.path.join(OUT, "layers", TABLE_LAYER)))[..., 3] > 127
    ys, xs = np.nonzero(A)
    m = A.astype(np.uint8).copy()
    yl = ys[xs < 1360].max()
    xl = int(xs[(xs < 1360) & (ys == yl)].mean())
    cv2.line(m, (xl, int(yl)), (xl, H - 1), 1, 2)
    cv2.line(m, (xl, H - 1), (int(xs.max()), H - 1), 1, 2)
    ff = m.copy()
    cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    return ff == 0, (xl, int(yl))


RUG_FILE = "rug/rug-cj-braided-wool-natural-fb12s0.png"
RUG_SIGMA = 12.0


def rug_fix():
    """The braid seam right of centre and the faint patch borders (stage 0) lie between the new legs. The paid fix (nano-banana-2 4K,
    450) re-styled the WHOLE rug (a regular chunky braid, peach): rejected, nothing of it is used. The table's own render (seedream) re-drew
    that rug continuously in the rug's own style, so the fix is in code from it: inside the open base only (stage 0's region), the rug =
    stage 0's own light and colour (a normalised blur, sigma 12 px, in linear light) x the render's braid detail as LUMINANCE only (the
    render's luminance over its own normalised blur, inside the open base only: its table shade and relight are low-frequency and drop
    out; its cool shade tint never enters). The patch is the whole open base (inside stage 0's changed rug region, which holds 99.9 % of
    it), so every visible border is a table edge: the patch runs on under the table's soft edge; under the opaque table stage 0 is kept."""
    rug8 = np.asarray(Image.open(os.path.join(LAY, RUG_FILE)))
    rug = rug8[..., :3].astype(np.float32) / 255
    ra = rug8[..., 3]
    I, low = interior()
    T0 = S0.table_region(S0.masks())
    a_t = np.asarray(Image.open(os.path.join(OUT, "layers", TABLE_LAYER)))[..., 3].astype(np.float32) / 255
    regt = np.load(os.path.join(CACHE, f"cut-{TAG}.npz"))["regt"].astype(np.float32) / 255
    Z0 = np.load(os.path.join(P2, "work-fb12s0", "regions-fb12s0.npz"))
    Z0 = Z0["rug"] | Z0["table"]                         # stage 0's changed rug and the old table's region
    R = I & Z0 & (ra > 0)
    edge = cv2.dilate(R.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & (a_t > 0) & (a_t < 1) & Z0 & (ra > 0)
    Rf = R | edge
    k_r = R.astype(np.float32)
    Yr = lum(s2l(regt))
    lh = np.log(np.clip(Yr / np.maximum(S0.nblur(Yr, k_r, RUG_SIGMA), 1e-4), 0.05, 5))
    # the rug's own texture, measured on stage 0's rug in the same region: its log-luminance contrast and how each channel follows it
    # (the grooves are warmer than the braid tops); the render's detail is brought to that contrast and given that tint
    k_s0 = (ra > 0).astype(np.float32)
    Ls = s2l(rug)
    Ys = lum(Ls)
    ls = np.log(np.clip(Ys / np.maximum(S0.nblur(Ys, k_s0, RUG_SIGMA), 1e-4), 0.05, 5))
    gain = float(np.std(ls[R]) / max(np.std(lh[R]), 1e-6))
    slopes = []
    for c_ in range(3):
        lc = np.log(np.clip(Ls[..., c_] / np.maximum(S0.nblur(Ls[..., c_], k_s0, RUG_SIGMA), 1e-4), 0.05, 5))
        slopes.append(float(np.polyfit(ls[R], lc[R], 1)[0]))
    hf = np.exp(np.dstack([gain * slopes[c_] * lh for c_ in range(3)])).astype(np.float32)
    # the soft-edge band holds table colour in the render: its detail is taken from the nearest interior pixel
    _, lab_ = cv2.distanceTransformWithLabels((~R).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(R)
    lut = np.zeros((int(lab_.max()) + 1, 3), np.float32)
    lut[lab_[ys, xs]] = hf[ys, xs]
    hf = np.where(edge[..., None], lut[lab_], hf)
    hf = np.clip(hf, 0.3, 2.0)
    k_s = (ra > 0).astype(np.float32)
    lf = S0.nblur(s2l(rug), k_s, RUG_SIGMA)
    new = l2s(np.clip(lf * hf, 0, 1))
    out = rug8.copy()
    out[Rf, :3] = u8(new)[Rf]
    p = save_png(os.path.join(OUT, "layers", "rug", f"rug-cj-braided-wool-natural-{TAG}.png"), out)
    chg = (out != rug8).any(2)
    lab_o = cv2.cvtColor(np.ascontiguousarray(cv2.GaussianBlur(rug, (0, 0), 6)), cv2.COLOR_RGB2LAB)
    lab_n = cv2.cvtColor(np.ascontiguousarray(cv2.GaussianBlur(out[..., :3].astype(np.float32) / 255, (0, 0), 6)), cv2.COLOR_RGB2LAB)
    dE = np.sqrt(((lab_o - lab_n) ** 2).sum(-1))[R]
    rec = dict(file=rel(p), region_px=int(Rf.sum()), changed_px=int(chg.sum()), changed_outside_stage0_regions_px=int((chg & ~Z0).sum()),
               open_base_px=int(I.sum()), open_base_outside_stage0_px=int((I & ~Z0).sum()),
               alpha_changed_px=int((out[..., 3] != ra).sum()), sigma_px=RUG_SIGMA, left_leg_low_point_px=list(low),
               detail_contrast_gain=round(gain, 3), channel_slopes=[round(v, 3) for v in slopes],
               low_freq_dE76_vs_stage0=dict(median=round(float(np.median(dE)), 2), p95=round(float(np.percentile(dE, 95)), 2)),
               nano_pass="rejected: re-styled the whole rug (raw/fb12s1-rug-nano.jpg); nothing of it is used")
    np.save(os.path.join(CACHE, f"interior-{TAG}.npy"), I)
    return rec


def throw_fix():
    """Sets A and C: the throw's lower-left corner, shaped by the old table's corner (stage 0), still pokes out left of the new right leg,
    under the top, in the open base (C: a dark tail, 236 px; A: 139 px). The throw now ends behind the leg: inside the open base the set's
    layer is cleared, and its shadow within 8 px of the cleared pixels (the tail's own shadow); every other pixel of the set is kept."""
    I = np.load(os.path.join(CACHE, f"interior-{TAG}.npy"))
    man = stage0_manifest()
    out = {}
    for st, v in man["slot_cushions"]["sets"].items():
        L8 = np.asarray(Image.open(os.path.join(LAY, v["layer"])))
        S8 = np.asarray(Image.open(os.path.join(LAY, v["shadow"])).convert("RGB"))
        q = I & (L8[..., 3] > 0)
        if not q.any():
            out[st] = dict(changed=False)
            continue
        L2 = L8.copy()
        L2[q] = 0
        qs = cv2.dilate(q.astype(np.uint8), np.ones((17, 17), np.uint8)).astype(bool) & I & (S8 < 255).any(2)
        S2 = S8.copy()
        S2[qs] = 255
        lp = save_png(os.path.join(OUT, "layers", "cushions", f"set-{st}-{TAG}.png"), L2)
        sp = save_png(os.path.join(OUT, "layers", "cushions", f"set-{st}-shadow-{TAG}.png"), S2)
        ys, xs = np.nonzero(q)
        out[st] = dict(changed=True, layer=rel(lp), shadow=rel(sp), layer_px_cleared=int(q.sum()), shadow_px_cleared=int(qs.sum()),
                       bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    return out


# ------------------------------------------------------------------------------------------------- the bowl and the candle holders
# each rendered piece moves about its own contact point on the top (Z 0.38, the old and the new top are both 38 high): the translation
# = the projection of the new contact point minus the old one, the scale = the depth ratio (perspective only); the shadow field moves with
# its piece and is re-masked by the frozen recipe's masks (extract.shadow_one / fix_r7.remask_shadow) on the NEW top
# the points: the brief (candle holders 18 cm left, the bowl at (0.46, 1.85)) with the proposal's own levers (a.10 section 2), taken
# because the moved layers measured under F3's 0.02 there: bowl x the throw of set C 0.0167 (black) / 0.0178 (white belly). Levers:
# B's right edge 0.19 (range 0.19-0.22; every holder 20 cm left instead of 18), the bowl 0.25 right of it and at Y 1.858 (range
# 1.83-1.858): bowl x set C 0.0209 / 0.0221. Ceramic trays (v2): A x B 0.0195 < 0.02 -> the pre-approved WM-T3 lever, A 1 cm further left.
LEVERS = dict(holders_dx=-0.20, bowl=(0.44, 1.858), trays_A_extra=-0.01,
              why="F3 < 0.02 at the brief's points on the moved layers: bowl x cushions C 0.0167 / 0.0178; trays A x B 0.0195 (a.10 section 2 "
                  "levers; WM-T3 lever for the trays)")
GROUP = {
    "bowl": dict(file="bowl/bowl-cj-matte-black-bowl-20-r7.png", shadow="bowl/bowl-cj-matte-black-bowl-20-r7-shadow.png",
                 pieces={"bowl": ((0.62, 1.94), LEVERS["bowl"])}),
    "candle-holders": dict(file="candle-holders/candle-holders-cj-travertine-pedestal-r8.png",
                           shadow="candle-holders/candle-holders-cj-travertine-pedestal-r8-shadow.png",
                           pieces={"A": ((0.195, 1.74), (0.195 + LEVERS["holders_dx"], 1.74)), "B": ((0.355, 1.68), (0.355 + LEVERS["holders_dx"], 1.68))}),
    "bowl-v2": dict(file="bowl/bowl-cj-glutinous-white-belly-bowl-21-r7.png", shadow="bowl/bowl-cj-glutinous-white-belly-bowl-21-r7-shadow.png",
                    pieces={"bowl": ((0.62, 1.94), LEVERS["bowl"])}),
    "candle-holders-v2": dict(file="candle-holders/candle-holders-cj-ceramic-pedestal-tray-r7.png",
                              shadow="candle-holders/candle-holders-cj-ceramic-pedestal-tray-r7-shadow.png",
                              pieces={"A": ((0.055, 1.74), (0.055 + LEVERS["holders_dx"] + LEVERS["trays_A_extra"], 1.74)),
                                      "B": ((0.305, 1.68), (0.305 + LEVERS["holders_dx"], 1.68))}),
}
SLOT_OF = {"bowl": "bowl", "bowl-v2": "bowl", "candle-holders": "candle-holders", "candle-holders-v2": "candle-holders"}
TOP_Z = 0.38


def depth_of(X, Y, Z):
    C, fwd, _ = cam_basis()
    return float((np.array([X, Y, Z]) - C) @ fwd)


def out_name(f):
    b, e = os.path.splitext(f)
    for t in ("-r7", "-r8"):
        if b.endswith(t) or b.endswith(t + "-shadow"):
            break
    if b.endswith("-shadow"):
        return b[:-len("-shadow")].rsplit("-r", 1)[0] + f"-{TAG}-shadow" + e
    return b.rsplit("-r", 1)[0] + f"-{TAG}" + e


def top_surface():
    """where a table item's shadow may fall: the new top's visible surface (the clay's top part, inside the table layer's opaque cut)"""
    c = load_clay()
    L = np.asarray(Image.open(os.path.join(OUT, "layers", TABLE_LAYER)))
    return (c["part"] == 1) & (L[..., 3] > 127)


def move_one(key):
    g = GROUP[key]
    L = f8(os.path.join(LAY, g["file"]))
    rgb, a = L[..., :3], L[..., 3]
    sh = f8(os.path.join(LAY, g["shadow"]), "L")
    n, lab_, st, _ = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8))
    ids = sorted([i for i in range(1, n) if st[i, 4] >= 200], key=lambda i: st[i, 0])
    names = list(g["pieces"])
    assert len(ids) == len(names), (key, len(ids))
    seeds = np.zeros(a.shape, np.uint8)
    for j, i in enumerate(ids):
        seeds[lab_ == i] = j + 1
    _, near = cv2.distanceTransformWithLabels((seeds == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys0, xs0 = np.nonzero(seeds > 0)
    lut = np.zeros(int(near.max()) + 1, np.uint8)
    lut[near[ys0, xs0]] = seeds[ys0, xs0]
    owner = lut[near]
    rgb_d, _ = decontaminate(rgb, a)                       # the walnut behind the old soft edge never comes onto the oak
    outA = np.zeros_like(a)
    outP = np.zeros_like(rgb)
    outD = np.zeros_like(sh)
    rec = {}
    for j, (i, nm) in enumerate(zip(ids, names)):
        (xo, yo), (xn, yn) = g["pieces"][nm]
        po, pn = np.array(S0.project(xo, yo, TOP_Z)), np.array(S0.project(xn, yn, TOP_Z))
        s = depth_of(xo, yo, TOP_Z) / depth_of(xn, yn, TOP_Z)
        ys, xs = np.nonzero(lab_ == i)
        ay = float(ys.max()) + 0.5
        ax = float(xs[ys >= ys.max() - 2].mean()) + 0.5
        tx, ty = pn - po
        M = np.float32([[s, 0, ax * (1 - s) + tx], [0, s, ay * (1 - s) + ty]])
        own = owner == j + 1
        ai = np.where(own, a, 0).astype(np.float32)
        di = np.where(own, 1 - sh, 0).astype(np.float32)
        outA += cv2.warpAffine(ai, M, (W, H), flags=cv2.INTER_AREA)
        outP += cv2.warpAffine(rgb_d * ai[..., None], M, (W, H), flags=cv2.INTER_AREA)
        outD = np.maximum(outD, cv2.warpAffine(di, M, (W, H), flags=cv2.INTER_AREA))
        rec[nm] = dict(plan_from=[xo, yo], plan_to=[xn, yn], anchor_px=[round(ax, 2), round(ay, 2)], translate_px=[round(float(tx), 2), round(float(ty), 2)],
                       scale=round(s, 4), new_anchor_px=[round(ax + float(tx), 2), round(ay + float(ty), 2)],
                       box_before=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    a2 = np.clip(outA, 0, 1).astype(np.float32)
    rgb2 = np.where((outA > 1e-4)[..., None], outP / np.maximum(outA, 1e-4)[..., None], 0).astype(np.float32)
    return rgb2, a2, np.clip(outD, 0, 1).astype(np.float32), rec


def remask(key, a, dfield, other_alpha, onto):
    """fix_r7.remask_shadow with the new top as the surface: the band (SPEC band + 4 px) round the item, on the top only, never on the other
    table item; floored at 0.45; 1 under the item"""
    X = X_()
    # the ring next to the item: on the walnut the field was cut to 0 under the old soft edge (1 under the product); moved onto the light
    # oak that ring reads as a light halo, so it takes the darkness found 4-8 px out (a max filter, 11 px), never more
    dist = cv2.distanceTransform((a <= 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    src = np.where((dist >= 4) & (dist <= 8), dfield, 0.0).astype(np.float32)
    fill = cv2.dilate(src, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    ring = (dist > 0) & (dist < 4)
    dfield = np.where(ring, np.maximum(dfield, fill), dfield)
    band = X.dil(a > 0.02, X.SPEC[SLOT_OF[key]]["band"] + 4) & ~(a > 0.02) & onto & ~(other_alpha > 0.02)
    d = np.where(band | (a > 0.02), dfield, 0.0)
    sh = np.clip((1 - d) * (1 - a) + a, 0.45, 1.0).astype(np.float32)
    return sh, int((dfield > 0.005).sum() - (d > 0.005).sum())


def group():
    onto = top_surface()
    moved = {k: move_one(k) for k in GROUP}
    pair = {"bowl": "candle-holders", "candle-holders": "bowl", "bowl-v2": "candle-holders-v2", "candle-holders-v2": "bowl-v2"}
    out = {}
    for k, (rgb2, a2, dfield, rec) in moved.items():
        other = np.maximum(moved[pair[k]][1], moved[{"bowl": "candle-holders-v2", "candle-holders": "bowl-v2", "bowl-v2": "candle-holders",
                                                       "candle-holders-v2": "bowl"}[k]][1])
        sh2, clipped = remask(k, a2, dfield, other, onto)
        g = GROUP[k]
        lp = save_png(os.path.join(OUT, "layers", out_name(g["file"])), np.dstack([np.where((a2 > 0)[..., None], u8(rgb2), 0).astype(np.uint8), u8(a2)]))
        sp = save_png(os.path.join(OUT, "layers", out_name(g["shadow"])), np.repeat(u8(sh2)[..., None], 3, 2))
        # the item stands on the top: its contact row on the opaque top, its soft shadow not past the top's edge
        a8 = u8(a2) > 127
        ys, xs = np.nonzero(a8)
        foot = a8 & (np.arange(H)[:, None] >= ys.max() - 1)
        out[k] = dict(pieces=rec, shadow_px_clipped_by_the_recipe_masks=clipped, files=dict(layer=rel(lp), shadow=rel(sp)),
                      source=dict(layer=rel(os.path.join(LAY, g["file"])), shadow=rel(os.path.join(LAY, g["shadow"]))),
                      foot_on_top_share=round(float(onto[foot].mean()) if foot.any() else 0.0, 3),
                      shadow_off_top_px=int(((u8(sh2) < 255) & ~onto & ~(a2 > 0.02)).sum()))
    json.dump(out, open(os.path.join(WORK, f"group-{TAG}.json"), "w"), indent=1)
    return out

# ------------------------------------------------------------------------------------------------- the stack, the defaults, the frames
FW_ = S0.FRAME_BOX[2] - S0.FRAME_BOX[0]               # the camera frame's width at 2720 (F3's frame-width unit)
RUG_NEW = os.path.join("rug", f"rug-cj-braided-wool-natural-{TAG}.png")


def new_files():
    """id (or (cushions, set)) -> the new file, relative to layers/ (the layer and shadow paths the new manifest names)"""
    f = {"rug": RUG_NEW, "coffee-table": TABLE_LAYER, "coffee-table-shadow": TABLE_SHADOW}
    for k in ("bowl", "candle-holders", "bowl-v2", "candle-holders-v2"):
        f[k] = out_name(GROUP[k]["file"])
        f[k + "-shadow"] = out_name(GROUP[k]["shadow"])
    for st in "ABC":
        lp = os.path.join(OUT, "layers", "cushions", f"set-{st}-{TAG}.png")
        if os.path.exists(lp):
            f[("cushions", st)] = os.path.relpath(lp, os.path.join(OUT, "layers"))
            f[("cushions-shadow", st)] = os.path.join("cushions", f"set-{st}-shadow-{TAG}.png")
    return f


def lay(path):
    """a layer path relative to layers/: this stage's new files live in OUT/layers, the rest in the repo's layers/"""
    q = os.path.join(OUT, "layers", path)
    return q if os.path.exists(q) else os.path.join(LAY, path)


def stack_stage0(man, st):
    out = []
    for l_ in man["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow") or l_.get("hidden_in_defaults"):
            continue
        if k == "cushions":
            v = man["slot_cushions"]["sets"][st]
            out.append((k, os.path.join(LAY, v["layer"]), os.path.join(LAY, v["shadow"])))
        else:
            sh = next(x for x in man["layers"] if x["id"] == k + "-shadow")
            out.append((k, os.path.join(LAY, l_["file"]), os.path.join(LAY, sh["file"])))
    return out


def stack_new(man, st, variant=None):
    """the new stack in the manifest's order: the table (shadow z 56, layer z 57) right after the cushions (54 / 55), the bowl and the
    candle holders shown again, on the new top; variant = (slot, key in GROUP) swaps that slot's moved layer"""
    f = new_files()
    out = []
    for l_ in man["layers"]:
        k = l_["id"]
        if k == "base" or k.endswith("-shadow"):
            continue
        if k == "cushions":
            v = man["slot_cushions"]["sets"][st]
            out.append((k, lay(f.get(("cushions", st), v["layer"])), lay(f.get(("cushions-shadow", st), v["shadow"]))))
            out.append(("coffee-table", lay(f["coffee-table"]), lay(f["coffee-table-shadow"])))
            continue
        sh = next(x for x in man["layers"] if x["id"] == k + "-shadow")
        key = variant[1] if variant and variant[0] == k else k
        out.append((k, lay(f.get(key, l_["file"])), lay(f.get(key + "-shadow", sh["file"]))))
    return out


def build():
    man = stage0_manifest()
    base8 = np.asarray(Image.open(os.path.join(LAY, "base-fb12s0.png")).convert("RGB"))
    cache, rec, R = {}, {}, {}
    for st in man["slot_cushions"]["order"]:
        s_old = S0.compose8(base8, stack_stage0(man, st), cache)
        s_new = S0.compose8(base8, stack_new(man, st), cache)
        Rg = (s_old != s_new).any(2)
        t0 = np.asarray(Image.open(os.path.normpath(os.path.join(LAY, man["truths"]["default"][st]))).convert("RGB"))
        truth = np.where(Rg[..., None], s_new, t0)
        fp = save_png(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png"), truth)
        R[st] = Rg
        rec[st] = dict(file=rel(fp), region_px=int(Rg.sum()), outside_region_vs_stage0_truth_px=int(((truth != t0).any(2) & ~Rg).sum()))
        if st == "B":
            for slot, key in (("bowl", "bowl-v2"), ("candle-holders", "candle-holders-v2")):
                s_v = S0.compose8(base8, stack_new(man, st, (slot, key)), cache)
                Rv = (s_v != s_new).any(2)
                tv = np.where(Rv[..., None], s_v, truth)
                fv = save_png(os.path.join(OUT, "graded", f"variant-{TAG}-{key}-set-B-graded-v3c.png"), tv)
                rec[f"variant-{key}"] = dict(file=rel(fv), region_px=int(Rv.sum()))
        cache = {k_: v_ for k_, v_ in cache.items() if "cushions" not in k_}
    np.savez_compressed(os.path.join(WORK, f"regions-{TAG}.npz"), **{f"default_{k}": v for k, v in R.items()})
    json.dump(rec, open(os.path.join(WORK, f"defaults-{TAG}.json"), "w"), indent=1)
    return rec


def frames():
    out = {}
    for st in "BAC":
        im = Image.open(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")).convert("RGB")
        p = os.path.join(OUT, f"default-frame-{TAG}-set-{st}.png")
        im.resize((1920, 1080), Image.LANCZOS, box=S0.FRAME_BOX).save(p)
        out[st] = p
    return out


def gaps():
    """F3 (frame-width units, >= 0.02) on the layers as they stand: the table group and the table against their neighbours"""
    al = lambda p: np.asarray(Image.open(p))[..., 3] > 127        # noqa: E731
    f = new_files()
    man = stage0_manifest()
    dmin = lambda a, b: round(float(cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)[a].min()) / FW_, 4) if a.any() and b.any() else None  # noqa: E731
    out = {}
    cs = {st: al(lay(f.get(("cushions", st), man["slot_cushions"]["sets"][st]["layer"]))) for st in "ABC"}
    for k in ("bowl", "candle-holders", "bowl-v2", "candle-holders-v2"):
        a = al(lay(f[k]))
        for st, c in cs.items():
            out[f"{k} x cushions {st}"] = dmin(a, c)
    for k in ("candle-holders", "candle-holders-v2"):
        a = al(lay(f[k]))
        n, lab_, stt, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8))
        ids = sorted([i for i in range(1, n) if stt[i, 4] >= 200], key=lambda i: stt[i, 0])
        out[f"{k} A x B"] = dmin(lab_ == ids[0], lab_ == ids[1])
        out[f"{k} B x {'bowl' if k == 'candle-holders' else 'bowl-v2'}"] = dmin(lab_ == ids[1], al(lay(f["bowl" if k == "candle-holders" else "bowl-v2"])))
    T_ = al(lay(f["coffee-table"]))
    mh = next(l_ for l_ in man["layers"] if l_["id"] == "magazine-holder")
    out["coffee-table x magazine-holder"] = dmin(T_, al(os.path.join(LAY, mh["file"])))
    ys, xs = np.nonzero(T_)
    out["coffee-table left edge u"] = round((xs.min() - S0.FRAME_BOX[0]) / FW_, 4)
    out["note"] = ("the sofa's left arm contour is u 0.466 (a.10): the table's front-left corner is clear of it by 'left edge u' - 0.466; "
                   "the table group is measured on the moved rendered layers (alpha > 127)")
    return out


# ------------------------------------------------------------------------------------------------- the QA sheet
def sheet():
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)

    def bar(w, label):
        b = Image.new("RGB", (w, 40), (24, 24, 24))
        ImageDraw.Draw(b).text((12, 6), label, fill=(240, 240, 240), font=font)
        return b

    def tile(im, box, k, label):
        t = im.crop(box)
        t = t.resize((t.width * k, t.height * k), Image.BILINEAR)    # bilinear, as a browser zooms (no Lanczos ringing at the edges)
        out = Image.new("RGB", (t.width, t.height + 40))
        out.paste(bar(t.width, label), (0, 0))
        out.paste(t, (0, 40))
        return out
    d = {st: Image.open(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")).convert("RGB") for st in "BAC"}
    d0 = Image.open(os.path.normpath(os.path.join(LAY, stage0_manifest()["truths"]["default"]["B"]))).convert("RGB")
    rows = [tile(d0, (1250, 1080, 2250, 1530), 2, "BEFORE  stage 0, set B (no table)  x2, px 1250-2250 x 1080-1530"),
            tile(d["B"], (1250, 1080, 2250, 1530), 2, f"AFTER  {TAG}, set B: Olia 120 x 65 x 38, natural oak; bowl and candle holders on it  x2")]
    small = [tile(d["B"], (1500, 1130, 1950, 1330), 2, "x2: the group on the oak (set B)"),
             tile(d["A"], (2000, 1200, 2250, 1450), 2, "x2: the throw, set A"),
             tile(d["C"], (2000, 1200, 2250, 1450), 2, "x2: the throw, set C")]
    w = rows[0].width
    r3 = Image.new("RGB", (w, max(t.height for t in small)), (24, 24, 24))
    x = 0
    for t in small:
        r3.paste(t, (x, 0))
        x += t.width + 10
    rows.append(r3)
    for st in "BAC":
        fr = d[st].resize((1920, 1080), Image.LANCZOS, box=S0.FRAME_BOX)
        t = Image.new("RGB", (w, 1120), (24, 24, 24))
        t.paste(bar(w, f"x1  the room, set {st} (the 1920 x 1080 camera frame)"), (0, 0))
        t.paste(fr, ((w - 1920) // 2, 40))
        rows.append(t)
    H_ = sum(r_.height for r_ in rows) + 6 * (len(rows) - 1)
    sh = Image.new("RGB", (w, H_), (255, 255, 255))
    y = 0
    for r_ in rows:
        sh.paste(r_, (0, y))
        y += r_.height + 6
    p = os.path.join(OUT, "qa-sheet-fb12-stage1.jpg")
    sh.save(p, quality=84)
    return p


# ------------------------------------------------------------------------------------------------- the records
JOBS = dict(
    table=dict(id="wm-fb12s1-table", model="seedream-5-pro", type="image-to-image", resolution="2K", aspect_ratio="auto", tokens=650,
               estimate=650, estimate_call=dict(tool="var2_estimate_cost", model_id="seedream-5-pro", type="image-to-image",
                                                params=dict(resolution="2K", aspect_ratio="auto", image_refs=3), total_tokens=650),
               idempotency_key="wm-fb12s1-table-20261125", placeholder_id="0b3888ee-e17e-408c-bc79-bfdb207b3287",
               task_id="77c8469bcc885bc337225fd489d6d6f6",
               url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/seedream5p-77c8469bcc885bc337225fd489d6d6f6-0-1795629230138-6da444c4.png",
               raw="raw/fb12s1-seedream.png", raw_sha256="93a7de9a3ea6e5936fb81208c5a870276b1a08542eebea319ab81d14c1c8550e", returned_px=[2720, 1530],
               image_url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/e36b007e-6aae-45bb-9a94-5cc229ea3872.png",
               image_url_local="inputs/fb12s1-input.png", image_sha256="1967753fbe87052ca2a57b32287a6f5cb41c726909b09bff5a7139ff237dd96e",
               image_upload_verified="GET of the public URL returned the same sha256", prompt="assets/prompts/warm-modern-phase2-2026-11-10/fb12s1-table.txt",
               seed=None, seed_note="seedream-5-pro takes no seed in var2: the prompt, the input, the references and the settings are kept",
               refs=[dict(n=1, url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/aef5bbea-09dc-4eb5-9aa3-7d5c4e0f9991.png",
                          card="coffee-table-idana-javorina-olia-natural", sku="J-OF120-N", what="the real unit in a home, natural finish (card image 2, cropped to the table)",
                          source_image="card images.urls[1]", crop_px=[170, 560, 830, 930], sha256="3437d70fac9fcd7c00f408c11afeb0f3933c9d7da5e313c8a5aaf4fc6c67c51d"),
                     dict(n=2, url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/6c8c4dd8-50d3-4b7b-bf0f-f57703b83067.png",
                          card="coffee-table-idana-javorina-olia-natural", sku="J-OF120-N", what="the real unit, close-up of the rolled waterfall edge and the grain (card image 3)",
                          source_image="card images.urls[2]", crop_px=[70, 430, 950, 1090], sha256="844014054616dad0a59ddff2cdf8518af09939411decdecc4556b8de949b6f98"),
                     dict(n=3, url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/89c27508-9cf3-4f15-bd05-53e262645ddb.png",
                          card="coffee-table-idana-javorina-olia-natural", sku="J-OF120-N", what="the supplier's studio shot, three-quarter view (card image 1), for the shape",
                          source_image="card images.urls[0]", crop_px=[20, 395, 920, 830], sha256="e078b4118bb2c6aab83c7c0c28dac8121614ce97e9dfbaaf707019b6db4efb44")],
               references_policy="supplier images are references only: downloaded and cropped in the scratchpad, uploaded to var2, never stored in the repo; no supplier pixel in a layer",
               result="used: the table layer (z 57) and its shadow (z 56); its rug detail under the table also feeds the rug's leftover fix"),
    rug=dict(id="wm-fb12s1-rug", model="nano-banana-2", type="image-to-image", resolution="4K", aspect_ratio="auto", tokens=450, estimate=450,
             estimate_call=dict(tool="var2_estimate_cost", model_id="nano-banana-2", type="image-to-image", params=dict(resolution="4K", aspect_ratio="auto"), total_tokens=450),
             idempotency_key="wm-fb12s1-rug-20261125", placeholder_id="ad683074-6301-4d2a-b1ef-6caa473f4437", task_id="0cd8b84dcbe68bd9132185703c5858c9",
             url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/nano2-0cd8b84dcbe68bd9132185703c5858c9-0-1795630533245-8b58be68.jpg",
             raw="raw/fb12s1-rug-nano.jpg", raw_sha256="872fd23c2ac0de083a7047a1a6b1c523f5dbf63f64bffc329a69b72070d4cdeb", returned_px=[2730, 1536],
             returned_note="asked 4K, returned 2730 x 1536 JPEG",
             image_url="https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/93dd5cb4-2531-4bce-a872-59b0f9bb7982.png",
             image_local="(scratch cache) below-fb12s1.png = base-fb12s0 + rug-fb12s0", image_sha256="4acabcc9ae482d3419aaa953491cf78baca41b900f8fb4094d58a236b47a7384",
             prompt="assets/prompts/warm-modern-phase2-2026-11-10/fb12s1-rug.txt", seed=None, refs=[],
             result="REJECTED, nothing used: the model re-styled the whole rug (a regular chunky braid, peach) instead of joining its rows; the "
                    "seam was fixed in code from the table's render (rug_fix)"))


def records():
    def J(n):
        p = os.path.join(WORK, n)
        return json.load(open(p)) if os.path.exists(p) else None
    rec = dict(id=f"wm-living-room-m0-{TAG}", date="2026-11-25", author="render-agent", brief="briefs/wm-fb12-stage1-olia-2026-11-25.md",
               spec="docs/proposals/wm-fb12-2026-11-25.md a.3, a.6 (stage 1), a.7, a.10", owner="FB12-T (2026-11-25): render Olia as a swappable layer; cap 2,650",
               card="data/products/living-room/coffee-table/coffee-table-idana-javorina-olia-natural.json",
               tokens=dict(spent=1100, table=650, rug_edit_rejected=450, cap=2650, expected=1100),
               tone_check=dict(method="the card's real photos (scratchpad only, python3.12 -I): white balance on each photo's own white cabinets; "
                                      "exposure-free ratio of the oak top to the cream rug beside it",
                               lit_top_L=[68.3, 69.3], lit_top_hsl_S=[25, 33], hue_deg=[29, 30], studio_shot_lit_leg_L=64.7,
                               top_over_rug_Y=dict(real_photo_2=0.775, real_photo_3_grazing=0.925),
                               verdict="L* ~64-69 (the top of a.3's 56-66, 67-68 borderline, never 'far outside'); S 25-33 after white balance "
                                       "(<= 36: not honey). Went ahead."),
               thickness_note="the SKU photos show one slab ~2 cm thick (1.7-2.5; legs the same), not the 3-4 cm the brief names: the clay "
                              "and the render follow the photos (fidelity first); the render's silhouette = the clay's 2.2 cm (median 0 px)",
               jobs=JOBS, input=J("../inputs/fb12s1-input.json") if False else json.load(open(os.path.join(OUT, "inputs", f"{TAG}-input.json"))),
               cut=J(f"cut-{TAG}.json"), measures=J(f"measures-{TAG}.json"), leftovers=J(f"leftovers-{TAG}.json"), group=J(f"group-{TAG}.json"),
               levers=LEVERS, gaps=J(f"gaps-{TAG}.json"), defaults=J(f"defaults-{TAG}.json"))
    files = dict(table=os.path.join(OUT, "layers", TABLE_LAYER), table_shadow=os.path.join(OUT, "layers", TABLE_SHADOW),
                 rug=os.path.join(OUT, "layers", RUG_NEW))
    for k, v in new_files().items():
        if isinstance(k, tuple):
            files[f"{k[0]}-{k[1]}"] = os.path.join(OUT, "layers", v)
        elif k not in ("rug", "coffee-table", "coffee-table-shadow"):
            files[k] = os.path.join(OUT, "layers", v)
    for st in "BAC":
        files[f"default-{st}"] = os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png")
        files[f"frame-{st}"] = os.path.join(OUT, f"default-frame-{TAG}-set-{st}.png")
    for key in ("bowl-v2", "candle-holders-v2"):
        files[f"variant-{key}"] = os.path.join(OUT, "graded", f"variant-{TAG}-{key}-set-B-graded-v3c.png")
    files["sheet"] = os.path.join(OUT, "qa-sheet-fb12-stage1.jpg")
    rec["files"] = {k: rel(v) for k, v in files.items()}
    rec["sha256"] = {k: sha(v) for k, v in files.items()}
    json.dump(rec, open(os.path.join(WORK, f"{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    plate = os.path.join(LAY, "base-fb12s0.png")
    note = dict(id=f"wm-m0-{TAG}-motion-note", date="2026-11-25", author="render-agent", to="motion-agent",
                line=f"FB12 stage 1: the landing plate (frame 702) is unchanged: layers/base-fb12s0.png, sha256 {sha(plate)}. The new table is a product layer "
                     "(z 57, shadow z 56) that enters with reveal B; nothing of it goes into HDx2, clip 2 or the hall station (path R, a.5).",
                landing_plate=dict(path=rel(plate), sha256=sha(plate)), stage0_note="work-fb12s0/motion-note-fb12s0.json (homographies, regions)")
    json.dump(note, open(os.path.join(WORK, f"motion-note-{TAG}.json"), "w"), indent=1)
    for k in ("table", "rug"):
        jb = dict(JOBS[k], date="2026-11-25", author="render-agent", brief="briefs/wm-fb12-stage1-olia-2026-11-25.md",
                  prompt_chars=len("".join(l_ for l_ in open(os.path.join(REPO, JOBS[k]["prompt"])) if not l_.startswith("#")).strip()))
        json.dump(jb, open(os.path.join(REPO, "assets/prompts/warm-modern-phase2-2026-11-10", f"{JOBS[k]['id']}.json"), "w"), indent=1)
    return rec, note


def region_rec(p):
    r = S0.layer_region(p)
    x0, y0, x1, y1 = r["bbox_px"]
    fb = S0.FRAME_BOX
    r["rect_canvas_uv"] = [round(x0 / W, 4), round(x1 / W, 4), round(y0 / H, 4), round(y1 / H, 4)]
    r["rect_camera_frame_uv"] = [round((x0 - fb[0]) / FW_, 4), round((x1 - fb[0]) / FW_, 4), round((y0 - fb[1]) / (fb[3] - fb[1]), 4),
                                 round((y1 - fb[1]) / (fb[3] - fb[1]), 4)]
    return r


def hotspot():
    """a point on the top, 6 cm in from the front edge, left of the candle holders' column: the frame uv (frontend may move it)"""
    x, y = S0.project(-0.17, T["cy"] + T["D"] / 2 - 0.06, T["Hh"])
    fb = S0.FRAME_BOX
    return dict(frame="M0", u=round((x - fb[0]) / FW_, 4), v=round((y - fb[1]) / (fb[3] - fb[1]), 4), plan=[-0.17, round(T["cy"] + T["D"] / 2 - 0.06, 3), T["Hh"]],
                provisional=True, note="a.6 named (0.615, 0.88) before the clay; that point now falls on the holders' column, so the dot sits on "
                "the free top left of them")


def manifest_out():
    import copy
    rec = json.load(open(os.path.join(WORK, f"{TAG}.json")))
    m0 = stage0_manifest()
    m = copy.deepcopy(m0)
    f = new_files()
    LO = os.path.join(OUT, "layers")
    m.update(id=f"wm-living-room-m0-tool-layers-phase2-{TAG}", version=f"{TAG} (FB12 stage 1: the Olia coffee table as a product layer; supersedes "
             "manifest-fb12s0.json for the tool; fb12s0 and r9 are kept for rollback)", date="2026-11-25", author="render-agent",
             brief="briefs/wm-fb12-stage1-olia-2026-11-25.md (FB12 stage 1); docs/proposals/wm-fb12-2026-11-25.md a.6 stage 1, a.10")
    m["approval"] = m0["approval"] + ("; FB12 stage 1: FB12-T (owner 2026-11-25), cap 2,650; spent 1,100 (the table 650; the rug edit 450, "
                                      "rejected); the rest in code")
    m["status"] = ("FB12 stage 1: the IDANA Olia coffee table (natural oak, 120 x 65 x 38, at (0.30, 1.72), angle 0) is a product layer "
                   "(z 57, its shadow z 56), never baked into the plate, so other tables can be swapped in; the bowl and the candle holders "
                   "stand on it again (moved in code with their shadows, re-masked on the oak; the a.10 levers); the stage-0 leftovers fixed in "
                   "code (the rug's braid seam under the table, the throw's corner in sets A and C). 13 defaults shown. Not for sale yet (no "
                   "written supplier approval). Not QA'd; for qa-agent. HD_PUBLIC=0 only.")
    T_ = os.path.join(LO, f["coffee-table"])
    meas = rec.get("measures") or {}
    out_layers = []
    for l_ in m["layers"]:
        k = l_["id"]
        if k in ("rug", "bowl", "candle-holders", "bowl-shadow", "candle-holders-shadow") or (k == "rug" and False):
            l_["previous_file"] = l_["file"]
            l_["file"] = f[k]
            l_.pop("hidden_in_defaults", None)
            l_.pop("hidden_note", None)
            if not k.endswith("-shadow"):
                l_["region"] = region_rec(os.path.join(LO, f[k]))
                l_["file_origin"] = dict(layer=f"new -{TAG} file", shadow=f"new -{TAG} file" if k != "rug" else "existing file, same bytes")
            if k in ("bowl", "candle-holders"):
                l_["fb12s1"] = dict(what="moved in code onto the oak top (Z 0.38, as the old top) with its shadow field; the shadow re-masked "
                                         "on the new top (the frozen recipe's masks), its ring next to the item filled from 4-8 px out; the soft "
                                         "edge decontaminated (no walnut on the oak)", pieces=(rec.get("group") or {}).get(k, {}).get("pieces"),
                                    levers=LEVERS)
            if k == "rug":
                l_["fb12s1"] = ("the open base under the new table (stage 0's region): stage 0's own light and colour x the braid detail of "
                                "the table's render (luminance, stage 0's own contrast and channel tint): the braid seam right of centre and "
                                "the patch borders are gone; under the opaque table stage 0 is kept; alpha unchanged")
        out_layers.append(l_)
        if k == "cushions":
            out_layers.append(dict(id="coffee-table-shadow", slot="coffee-table", blend="multiply", z=56, file=f["coffee-table-shadow"], opaque=True,
                                   white_is_none=True, format="RGB, no alpha",
                                   recipe=f"extract.shadow_one (frozen), band {SHADOW_BAND} px (the table is 120 cm: the floor items' 36-40 px "
                                          "leave the recipe's ring inside the shade under the top and cancel it); onto: the floor and the rug, "
                                          "never the sofa or the armchair; 255 under the opaque table"))
            out_layers.append(dict(id="coffee-table", slot="coffee-table", blend="normal", z=57, file=f["coffee-table"], format="RGBA, straight alpha",
                                   product=dict(card_id=CARD, card="data/products/living-room/coffee-table/coffee-table-idana-javorina-olia-natural.json",
                                                option=dict(finish="Solid Oak (natural oil)", size="120 x 65 x 38"), sku="J-OF120-N", default=True),
                                   sale_status="NOT FOR SALE YET: no written approval from IDANA (rule c.0); label 'עוד לא במכירה'",
                                   region=region_rec(T_), fit=dict(centre=[T["cx"], T["cy"]], angle_deg=0, top_Z=T["Hh"], slab_cm=T["t"] * 100,
                                                                   bend_outer_radius_cm=T["R"] * 100, leg_corner_radius_cm=T["rb"] * 100,
                                                                   camera="M0 1.2 (docs/house-plan.json)"),
                                   hotspot=hotspot(), reveal="B (with the rug and the accessories; the arrival's landing is the plate without it)",
                                   swaps_with="a future coffee-table layer at the same z (the slot's region: this layer's alpha + its shadow); "
                                              "the rug is whole under it",
                                   fidelity=dict(iou_cut_vs_clay=meas.get("iou_cut_vs_clay"), length_cm=meas.get("length_cm"),
                                                 ends_vs_clay=meas.get("ends_vs_clay"), back_edge_vs_clay=meas.get("back_edge_vs_clay"),
                                                 legs_vs_clay=meas.get("legs_vs_clay"), slab_thickness=meas.get("slab_thickness"),
                                                 air_under_top=meas.get("air_under_top"), tone=meas.get("tone")),
                                   pass_="fb12s1: seedream-5-pro i2i 2K (650) + code (register, tone match beyond the model's relit rug, cut, "
                                         "decontaminated soft edge)", record=f"../work-{TAG}/{TAG}.json"))
    m["layers"] = out_layers
    order = m["compose"]["order"]
    i = order.index("cushions")
    m["compose"]["order"] = order[:i + 1] + ["coffee-table-shadow", "coffee-table"] + order[i + 1:]
    for st, v in m["slot_cushions"]["sets"].items():
        if ("cushions", st) in f:
            v["previous_layer"], v["layer"] = v["layer"], f[("cushions", st)]
            v["previous_shadow"], v["shadow"] = v["shadow"], f[("cushions-shadow", st)]
            v["region"] = region_rec(os.path.join(LO, f[("cushions", st)]))
            v["fb12s1"] = ("the throw's lower-left corner, shaped by the old table's corner, no longer pokes out left of the new right leg: "
                           "the set is cleared inside the open base under the table, with its shadow within 8 px; every other pixel kept")
    for slot, key in (("bowl", "bowl-v2"), ("candle-holders", "candle-holders-v2")):
        for v in m["variants"].get(slot, []):
            if v["id"] == key:
                v["previous_file"], v["file"] = v["file"], f[key]
                v["previous_shadow"], v["shadow"] = v["shadow"], f[key + "-shadow"]
                v["region"] = region_rec(os.path.join(LO, f[key]))
                v["truth"] = os.path.relpath(os.path.join(OUT, "graded", f"variant-{TAG}-{key}-set-B-graded-v3c.png"), LO)
                v["fb12s1"] = "moved in code onto the oak with its shadow, as its slot's default"
    m.setdefault("history", {})["fb12s0_hidden"] = dict(defaults_hidden=m.pop("defaults_hidden", None), variants_hidden=m.pop("variants_hidden", None),
                                                        closed_by=f"{TAG}: the bowl and the candle holders stand on the new table again")
    m["truths"] = dict(default={st: os.path.relpath(os.path.join(OUT, "graded", f"default-scene-{TAG}-set-{st}-graded-v3c.png"), LO) for st in "BAC"},
                       variants_fb12s1={k: os.path.relpath(os.path.join(OUT, "graded", f"variant-{TAG}-{k}-set-B-graded-v3c.png"), LO) for k in ("bowl-v2", "candle-holders-v2")},
                       note=f"FB12 stage 1: each default = the 8-bit stack of this manifest where it differs from stage 0's stack, stage 0's "
                            "truth bytes elsewhere (RND2 0 outside); the other variants' truths are R9's (their regions do not touch the table)")
    m["table_group"] = dict(m0.get("table_group", {}), fb12s1=dict(points={k: {n: p_[1] for n, p_ in GROUP[k]["pieces"].items()} for k in GROUP},
                                                                     levers=LEVERS, gaps_frame=rec.get("gaps")))
    m["fb12s1"] = dict(record=f"../work-{TAG}/{TAG}.json", motion_note=f"../work-{TAG}/motion-note-{TAG}.json",
                       clay=f"../work-{TAG}/clay-{TAG}.npz", regions=f"../work-{TAG}/regions-{TAG}.npz",
                       site_note="frontend-dev: read manifest-fb12s1.json: coffee-table (z 57) and its shadow (z 56) are a product slot in M0, "
                                 "between the cushions and the basket / magazine holder; it enters with reveal B; the dot at 'hotspot'; label "
                                 "'עוד לא במכירה' until IDANA's written approval; the bowl and the candle holders are shown again; the landing "
                                 "frame 702 is still base-fb12s0.png")
    m["files"] = dict(build="../fb12_s1.py (clay, input, cut, measures, leftovers, group, gaps, build, records)", verify=f"verify_layers_{TAG}.py",
                      verification=f"verify-layers-{TAG}.json", sheet="../qa-sheet-fb12-stage1.jpg", record=f"../work-{TAG}/{TAG}.json",
                      asset_manifest_entries=f"asset-manifest-entries-{TAG}.json",
                      verify_usage=f"python3.12 -I verify_layers_{TAG}.py  (numpy + Pillow + OpenCV; exit 0 = pass)", previous_manifest="manifest-fb12s0.json")
    m["tokens"] = dict(m0["tokens"], fb12_stage1=1100, fb12_stage1_detail="the table 650 (seedream-5-pro 2K); the rug edit 450 (nano-banana-2 4K, rejected)")
    p = os.path.join(LO, f"manifest-{TAG}.json")
    json.dump(m, open(p, "w"), indent=1, ensure_ascii=False)
    return p


def asset_entries():
    rec = json.load(open(os.path.join(WORK, f"{TAG}.json")))
    P = rec["files"]

    def e(id_, path, kind, status, model="code (0 tokens)", tokens=0):
        fp = os.path.join(REPO, path)
        return dict(id=id_, path=path, kind=kind, room="living-room", style="warm-modern", created="2026-11-25", model=model, tokens=tokens,
                    status=status, sha256=sha(fp), bytes=os.path.getsize(fp))
    stl = "warm-modern tool, FB12 stage 1: not QA'd (qa-agent next); HD_PUBLIC=0 only"
    E = [e(f"wm-tool-{TAG}-coffee-table", P["table"], "layer: coffee-table (z 57), IDANA Olia natural oak 120 x 65 x 38 (J-OF120-N); not for sale yet", stl,
           "seedream-5-pro i2i 2K + code", 650),
         e(f"wm-tool-{TAG}-coffee-table-shadow", P["table_shadow"], "shadow: coffee-table (z 56, multiply; extract.shadow_one, band 200)", stl, "seedream-5-pro i2i 2K + code", 0),
         e(f"wm-tool-{TAG}-rug", P["rug"], "layer: the rug (z 20), the braid seam under the table fixed in code", stl)]
    kinds = {"bowl": "layer: bowl (z 65), black, moved onto the oak", "bowl-shadow": "shadow: bowl (z 64), re-masked on the oak",
             "candle-holders": "layer: candle holders (z 65), travertine, moved onto the oak", "candle-holders-shadow": "shadow: candle holders (z 64), re-masked",
             "bowl-v2": "variant layer: bowl v2 (white belly), moved onto the oak", "bowl-v2-shadow": "variant shadow: bowl v2",
             "candle-holders-v2": "variant layer: candle holders v2 (ceramic trays), moved onto the oak", "candle-holders-v2-shadow": "variant shadow: candle holders v2"}
    for k, kind in kinds.items():
        E.append(e(f"wm-tool-{TAG}-{k}", P[k], kind, stl))
    for st in "AC":
        if f"cushions-{st}" in P:
            E.append(e(f"wm-tool-{TAG}-cushions-{st}", P[f"cushions-{st}"], f"layer: cushion set {st} (z 55), the throw's corner cleared under the table", stl))
            E.append(e(f"wm-tool-{TAG}-cushions-shadow-{st}", P[f"cushions-shadow-{st}"], f"shadow: cushion set {st} (z 54)", stl))
    for st in "BAC":
        E.append(e(f"wm-tool-{TAG}-default-{st}", P[f"default-{st}"], f"truth: the default scene, set {st}, with the Olia table", "QA material, not for the site"))
        E.append(e(f"wm-tool-{TAG}-frame-{st}", P[f"frame-{st}"], f"frame 1920 x 1080 (the camera frame): the default scene, set {st}", "preview, not for the site before QA"))
    for k in ("bowl-v2", "candle-holders-v2"):
        E.append(e(f"wm-tool-{TAG}-variant-{k}", P[f"variant-{k}"], f"truth: variant {k}, set B", "QA material, not for the site"))
    for id_, path, kind, model, tok in [
            (f"wm-tool-{TAG}-input", rel(os.path.join(OUT, "inputs", f"{TAG}-input.png")), "input: the clean plate with the rug and the table's clay (the seedream edit's image)", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-raw-table", rel(os.path.join(OUT, "raw", f"{TAG}-seedream.png")), "raw: the seedream render (the table)", "seedream-5-pro i2i 2K", 0),
            (f"wm-tool-{TAG}-raw-rug-rejected", rel(os.path.join(OUT, "raw", f"{TAG}-rug-nano.jpg")), "raw: the nano rug edit, REJECTED (re-styled the whole rug), nothing used", "nano-banana-2 i2i 4K", 450),
            (f"wm-tool-{TAG}-manifest", rel(os.path.join(OUT, "layers", f"manifest-{TAG}.json")), "layers manifest (supersedes manifest-fb12s0 for the tool)", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-verify", rel(os.path.join(OUT, "layers", f"verify-layers-{TAG}.json")), "verification record", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-qa-sheet", P["sheet"], "QA sheet: the table at x2 (before / after), the group and the throws at x2, the room at x1 in sets B, A, C", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-motion-note", rel(os.path.join(WORK, f"motion-note-{TAG}.json")), "note for motion-agent: the landing plate (unchanged) and its sha", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-record", rel(os.path.join(WORK, f"{TAG}.json")), "build record (jobs, tone check, measures, levers, gaps)", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-clay", rel(os.path.join(WORK, f"clay-{TAG}.npz")), "source: the table's clay at the real dimensions (alpha, parts, shade, depth)", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-build-script", rel(os.path.join(OUT, "fb12_s1.py")), "tool: FB12 stage 1 build", "code (0 tokens)", 0),
            (f"wm-tool-{TAG}-verify-script", rel(os.path.join(OUT, "layers", f"verify_layers_{TAG}.py")), "tool: FB12 stage 1 checks", "code (0 tokens)", 0),
            (f"wm-fb12s1-table-prompt", "assets/prompts/warm-modern-phase2-2026-11-10/wm-fb12s1-table.json", "prompt record: the table edit", "seedream-5-pro i2i 2K", 0),
            (f"wm-fb12s1-rug-prompt", "assets/prompts/warm-modern-phase2-2026-11-10/wm-fb12s1-rug.json", "prompt record: the rug edit (rejected)", "nano-banana-2 i2i 4K", 0)]:
        E.append(e(id_, path, kind, "record / source, not for the site", model, tok))
    out = dict(note=f"merged into assets/manifest.json 'assets' (render-agent 2026-11-25, FB12 stage 1)", assets=E)
    json.dump(out, open(os.path.join(OUT, "layers", f"asset-manifest-entries-{TAG}.json"), "w"), indent=1, ensure_ascii=False)
    return E


def merge_assets(E):
    """re-read assets/manifest.json right before writing; replace entries with the same id, append the rest"""
    p = os.path.join(REPO, "assets/manifest.json")
    m = json.load(open(p))
    ids = {x["id"] for x in E}
    m["assets"] = [x for x in m["assets"] if x["id"] not in ids] + E
    with open(p, "w") as fh:
        fh.write(json.dumps(m, indent=1, ensure_ascii=False))     # the file's own format (indent 1, UTF-8, no trailing newline)
    return len(m["assets"])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "clay":
        c = clay()
        print(json.dumps(clay_measures(c), indent=1))
    elif cmd == "input":
        print(json.dumps(make_input()[1], indent=1)[:3000])
    elif cmd == "fetch":
        print(fetch(sys.argv[2]))
    elif cmd == "cut":
        print(json.dumps(cut(), indent=1))
    elif cmd == "measures":
        print(json.dumps(measures(), indent=1))
    elif cmd == "group":
        print(json.dumps(group(), indent=1))
    elif cmd == "build":
        print(json.dumps(build(), indent=1))
        print(frames())
        print(sheet())
    elif cmd == "records":
        records()
        print(manifest_out())
    elif cmd == "entries":
        E = asset_entries()
        print(len(E), "entries;", merge_assets(E) if "--merge" in sys.argv else "not merged (pass --merge)")
    elif cmd == "gaps":
        g = gaps()
        json.dump(g, open(os.path.join(WORK, f"gaps-{TAG}.json"), "w"), indent=1)
        print(json.dumps(g, indent=1))
    elif cmd == "leftovers":
        r = dict(rug=rug_fix(), throw=throw_fix())
        json.dump(r, open(os.path.join(WORK, f"leftovers-{TAG}.json"), "w"), indent=1)
        print(json.dumps(r, indent=1))
    else:
        raise SystemExit(__doc__)
