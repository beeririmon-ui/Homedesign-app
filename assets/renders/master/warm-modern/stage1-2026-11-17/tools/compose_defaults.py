#!/usr/bin/env python3
"""
compose_defaults.py: MB0 with the defaults (12.7: r4 is the base), its layers and the throw variants (render-agent, 2026-11-18). 0 tokens.
The bath's method (assets/renders/bath/warm-modern/stage1-2026-11-17/tools/compose_defaults.py v2), on this frame:
  1. lock: raw/defaults-r4.png resampled to the canvas (2720 x 1530, Lanczos) and warped onto plate.png by one affine fit (OpenCV ECC on
     the gradient magnitude, masked to the walls, the headboard and the nightstands away from every product; pyramid 4-2-1).
  2. tone match (MP-I1): a smooth gain field (normalised blur, sigma 60 px, per channel, linear light) of plate / render, measured
     outside every product zone, shadow band and light envelope, applied to the render. r4 descends from plate.png (steps 1-4 already
     in), so the field is 1 where the model kept the plate's light and lifts only where it put the fall-off back (the right third).
     MP-I2: MB0's toe is in plate.png already and r4 inherits it; it is not applied again (the black point is checked instead).
  3. per slot, the alpha: GrabCut (6 iterations) in the slot's box on the matched render. Sure product: the slot's colour prior or core
     boxes measured on r4; sure background: the box where the matched render is the plate (dE76 under 3 on a 1.5 px blur), and the
     other slots' seeds. Only components touching a seed; small holes filled; a 0.8 px soft edge.
  4. the 12.7 fixes, in code: the duvet's hem (the upholstered base out, the plate's mattress edge under it, a contact shadow), the duvet's
     foot corners drawn over the plate's mattress corners; the third candle holder out and the pair rebuilt at the card's 7 x 11 at the
     slot points with the filler candles 7 x 10 and 7 x 15; the dish (a white block) out, the tray refilled; the bottle back to the
     card's 24.5 cm; the floor lamp's two pull chains out (the in-room SKU's photo, A1, has none) and its disc base in the card's brass;
     the curtain's hem level at 12 cm (a per-column stretch of the panel's lower part); the tones of 4d.
  5. shadows (multiply on the sRGB values) and lights (screen, z 90) as in the bath; outside every alpha, shadow and light: plate.png.
  python3 compose_defaults.py cut        (steps 1-3, writes the scratchpad npz and an overlay)
  python3 compose_defaults.py all        (everything, writes the layers, the frame and the manifest)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-master-2026-11-17/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master/comp/"
RAW = os.path.join(ST, "raw/defaults-r4.png")
H, W = 1530, 2720
F, CX, HZ = 1710.0, 1360.0, 707.3                         # canvas px focal length (24 mm on the 16:9 frame), u0, the horizon row
CAM = (-0.70, 21.05, 1.05)
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])

# slot: clay ids, the box on r4 (x0, y0, x1, y1), z, product id (card + option), shadow band and contact rim (px)
SLOTS = {
    "curtains": dict(ids=(40,), box=(330, 0, 600, 1300), z=10, band=150, rim=8,
                     pid="curtains-aliexpress-linen-blend-s-fold-180502"),
    "bedside-sconces": dict(ids=(43, 44), box=(690, 505, 830, 655), box2=(1900, 505, 2040, 655), z=14, band=30, rim=10,
                            pid="wall-sconce-cj-travertine-cone-walnut"),
    "sill-vase": dict(ids=(41, 42), box=(210, 555, 335, 905), z=16, band=20, rim=8, pid="sill-vase-cj-cream-fluted-column-25"),
    "floor-lamp": dict(ids=(55,), box=(2165, 345, 2515, 1312), z=36, band=40, rim=12,
                       pid="floor-lamp-aliexpress-pleated-walnut-43x158-177278-master-a1-warm-light"),
    "nightstand-tray": dict(ids=(45,), box=(585, 940, 845, 996), z=44, band=16, rim=8, pid="nightstand-tray-cj-black-walnut-rect-tray"),
    "nightstand-vase": dict(ids=(46, 47), box=(598, 680, 752, 982), z=46, band=16, rim=8,
                            pid="nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862-d"),
    "candle-holders": dict(ids=(49, 50), box=(1912, 780, 2098, 988), z=46, band=16, rim=8,
                           pid="candle-holders-cj-travertine-pedestal-70x110"),
    "pillowcases": dict(ids=(51,), box=(880, 728, 1862, 1002), z=50, band=30, rim=10,
                        pid="pillowcases-cj-pure-linen-envelope-pair-48x74-caramel-pairs"),
    "bedding": dict(ids=(52,), box=(200, 880, 2535, 1530), z=52, band=60, rim=14,
                    pid="bedding-cj-washed-linen-natural-set-natural-linen-1-8m"),
    "cushions": dict(ids=(53,), box=(1178, 758, 1548, 968), z=55, band=20, rim=8, pid="cushions-cj-boucle-teddy-milk-tea-30x50"),
    "throw": dict(ids=(54,), box=(370, 955, 2350, 1265), z=58, band=24, rim=8, pid="sofa-cover-cj-cotton-muslin-fringe-pecan-150x200"),
}
# core seeds measured on the locked r4 (sure product)
CORES = {
    "curtains": [(395, 40, 485, 1150)],
    "bedside-sconces": [(735, 530, 795, 600), (745, 600, 780, 630), (1940, 530, 2000, 600), (1955, 600, 1990, 630)],
    "sill-vase": [(250, 760, 290, 880)],
    "floor-lamp": [(2215, 390, 2465, 560), (2325, 600, 2338, 1240), (2345, 1258, 2405, 1286)],
    "nightstand-tray": [(600, 977, 700, 985), (712, 976, 800, 984)],
    "nightstand-vase": [(662, 845, 700, 965), (674, 822, 690, 845)],
    "candle-holders": [(1945, 880, 1977, 965), (1948, 808, 1978, 840), (2004, 925, 2030, 972), (2047, 900, 2070, 960),
                       (2042, 840, 2068, 864)],
    "cushions": [(1235, 795, 1495, 905)],
    "bedding": [(520, 1110, 2200, 1380), (1000, 940, 1700, 975)],
}
_LAB = {}


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def dil(m, r):
    return m.astype(bool) if r <= 0 else cv2.dilate(m.astype(np.uint8), disk(r)).astype(bool)


def ero(m, r):
    return m.astype(bool) if r <= 0 else cv2.erode(m.astype(np.uint8), disk(r)).astype(bool)


def blur(a, s):
    return cv2.GaussianBlur(a.astype(np.float32), (0, 0), s).astype(np.float64)


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def luma(a):
    return a @ np.array([0.2126, 0.7152, 0.0722])


def to_lab(rgb):
    xyz = lin(rgb) @ M.T / WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def from_lab(L):
    fy = (L[..., 0] + 16) / 116
    fx, fz = fy + L[..., 1] / 500, fy - L[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    return srgb(xyz @ np.linalg.inv(M).T)


def lab_of(img):
    k = id(img)
    if k not in _LAB:
        _LAB[k] = (img, to_lab(img))
    return _LAB[k][1]


def load(p):
    return np.clip(np.asarray(Image.open(p).convert("RGB")).astype(np.float64) / 255, 0, 1)


def q(x):
    return np.clip(np.rint(x * 255), 0, 255).astype(np.uint8)


def box_mask(boxes, pad=0):
    m = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in boxes:
        m[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] = True
    return m


def proj(X, Y, Z):
    d = CAM[1] - Y
    return CX + F * (X - CAM[0]) / d, HZ + F * (CAM[2] - Z) / d


# ---------------------------------------------------------------------------------------------------------------- 1. lock
def lock(ids):
    """r4 at the canvas size, warped onto plate.png: an affine fit (ECC, masked to the walls, headboard and nightstands)"""
    r = Image.open(RAW).convert("RGB")
    r = np.asarray(r.resize((W, H), Image.LANCZOS)).astype(np.float32)
    pl = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB")).astype(np.float32)
    prod = dil((ids >= 40) & (ids < 90), 30)
    stable = np.isin(ids, [20, 24, 25, 26, 1, 2, 5, 9, 10, 12, 13, 14]) & ~prod
    stable[1450:] = False

    def g(a):
        y = cv2.GaussianBlur(a @ np.array([0.2126, 0.7152, 0.0722], np.float32), (0, 0), 1.5)
        gx, gy = cv2.Sobel(y, cv2.CV_32F, 1, 0), cv2.Sobel(y, cv2.CV_32F, 0, 1)
        m = np.sqrt(gx * gx + gy * gy)
        return m / (np.percentile(m, 99) + 1e-6)
    a_, b_ = g(r), g(pl)
    warp = np.eye(2, 3, dtype=np.float32)
    cc = {}
    for s in (4, 2, 1):
        a = cv2.resize(a_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        b = cv2.resize(b_, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
        m = cv2.resize(stable.astype(np.uint8), (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST)
        w = warp.copy()
        w[:, 2] /= s
        c, w = cv2.findTransformECC(b, a, w, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), m, 5)
        w[:, 2] *= s
        warp, cc[s] = w, round(float(c), 4)
    out = cv2.warpAffine(r, warp, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out / 255, 0, 1).astype(np.float64), dict(method="ECC affine on the gradient magnitude, masked", ecc=cc,
                                                              warp=[[round(float(v), 6) for v in row] for row in warp])


# ---------------------------------------------------------------------------------------------------------------- 2. tone
def light_envelopes():
    """the lamps' light on the plate, by lamp: windows round each source (the sconces' cones down to the nightstand tops; the floor
    lamp below its shade's rim and its floor pool). Above and right of the shade is not lamp light: there the field is MP-I1's"""
    env = {}
    e = np.zeros((H, W), bool)
    e[500:1000, 600:905] = True
    env["sconce-w"] = e
    e = np.zeros((H, W), bool)
    e[500:1000, 1815:2125] = True
    env["sconce-e"] = e
    e = np.zeros((H, W), bool)
    e[575:1240, 2080:2560] = True
    e[1225:H, 2150:W] = True
    env["floor-lamp"] = e
    return env


def nconv(v, w, sigmas=(60, 240, 900)):
    """normalised convolution at sigma 60; where the measured support is thin (the bed's middle), the wider scales fill in"""
    out, have = None, None
    for s in sigmas:
        nb = cv2.GaussianBlur(w, (0, 0), s)
        val = cv2.GaussianBlur((v * w).astype(np.float32), (0, 0), s) / np.maximum(nb, 1e-9)
        a = np.clip(nb / 0.15, 0, 1)
        if out is None:
            out, have = val * a, a
        else:
            out, have = out + val * a * (1 - have), have + a * (1 - have)
    return out / np.maximum(have, 1e-9)


def gain_field(render, base, keep):
    w = keep.astype(np.float32)
    g = np.ones_like(render)
    for c in range(3):
        g[..., c] = np.clip(nconv(lin(base[..., c]), w) / np.maximum(nconv(lin(render[..., c]), w), 1e-4), 0.5, 2.5)
    return g


# ---------------------------------------------------------------------------------------------------------------- 3. cut
def gc_cut(img, sure, prob, zone, hard_bg, iters=6):
    ys, xs = np.nonzero(zone)
    y0, y1, x0, x1 = max(0, ys.min() - 12), min(H, ys.max() + 13), max(0, xs.min() - 12), min(W, xs.max() + 13)
    sl = (slice(y0, y1), slice(x0, x1))
    z = zone[sl]
    seeds = sure[sl] & z & ~hard_bg[sl]
    m = np.full(z.shape, cv2.GC_BGD, np.uint8)
    m[z] = cv2.GC_PR_BGD
    m[z & prob[sl]] = cv2.GC_PR_FGD
    m[hard_bg[sl]] = cv2.GC_BGD
    m[seeds] = cv2.GC_FGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(q(img[sl])[..., ::-1].copy(), m, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    fg = (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)
    n, lab = cv2.connectedComponents(fg.astype(np.uint8), connectivity=8)
    fg = np.isin(lab, list(set(np.unique(lab[seeds & fg])) - {0}))
    inv = (~fg).astype(np.uint8)
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    fg |= np.isin(lab2, [i for i in range(1, n2) if stats[i, cv2.CC_STAT_AREA] < 150 and i not in border])
    out = np.zeros((H, W), bool)
    out[sl] = fg
    return out


def priors(src):
    lab = lab_of(src)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C, h = np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360
    return dict(caramel=(C > 18) & (h > 35) & (h < 75) & (L > 28) & (L < 72),
                pecan=(C > 14) & (h > 28) & (h < 72) & (L < 62),
                dark=(L < 30))


def cut_all(src, base, ids):
    lab_s, lab_b = blur(lab_of(src), 1.5), blur(lab_of(base), 1.5)
    dE = np.linalg.norm(lab_s - lab_b, axis=-1)
    same = dE < 3
    pr = priors(src)
    cores = {k: box_mask(v) for k, v in CORES.items()}
    zones = {}
    for k, sp in SLOTS.items():
        z = box_mask([sp["box"]] + ([sp["box2"]] if sp.get("box2") else []))
        zones[k] = z
    seeds = dict(cores)
    seeds["pillowcases"] = pr["caramel"] & zones["pillowcases"] & ~box_mask([(0, 975, W, H)])
    seeds["throw"] = pr["pecan"] & zones["throw"] & ~box_mask([(0, 0, W, 985)])
    seeds["throw"] = cv2.morphologyEx(seeds["throw"].astype(np.uint8), cv2.MORPH_OPEN, disk(2)).astype(bool)
    seeds["pillowcases"] = cv2.morphologyEx(seeds["pillowcases"].astype(np.uint8), cv2.MORPH_OPEN, disk(2)).astype(bool)
    seeds["bedding"] = seeds["bedding"] & ~dil(seeds["throw"], 6)
    fg = {}
    for k in SLOTS:
        hard = same & ~dil(seeds[k], 2)
        for o in SLOTS:
            if o != k and SLOTS[o]["z"] != SLOTS[k]["z"]:
                hard |= ero(seeds[o], 2)
        prob = zones[k] & (~same | dil(seeds[k], 3))
        fg[k] = gc_cut(src, seeds[k], prob, zones[k], hard)
    return fg, dict(dE=dE, same=same, seeds=seeds, zones=zones)


def overlay(src, fg, path):
    cols = {"curtains": (255, 0, 0), "bedside-sconces": (0, 255, 0), "sill-vase": (0, 0, 255), "floor-lamp": (255, 255, 0),
            "nightstand-tray": (255, 0, 255), "nightstand-vase": (0, 255, 255), "candle-holders": (255, 128, 0),
            "pillowcases": (128, 0, 255), "bedding": (0, 128, 255), "cushions": (255, 0, 128), "throw": (0, 255, 128)}
    o = (src * 255).astype(np.float64)
    for k, m in fg.items():
        e = m & ~ero(m, 2)
        o[e] = cols[k]
        o[m & ~e] = o[m & ~e] * 0.75 + np.array(cols[k]) * 0.25
    Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(path)


def setup():
    ids = np.asarray(Image.open(CLAY + "MB0-id.png"))
    base = load(os.path.join(ST, "plate.png"))
    render, rec_lock = lock(ids)
    env = light_envelopes()
    anyz = np.zeros((H, W), bool)
    for k, sp in SLOTS.items():
        anyz |= dil(box_mask([sp["box"]] + ([sp["box2"]] if sp.get("box2") else [])), 20)
    anyl = np.zeros((H, W), bool)
    for e in env.values():
        anyl |= e
    curtain_strip = box_mask([(300, 0, 760, 1300)])          # the curtain's shade on the bed wall by the corner (the clay has it too)
    keep = ~(anyz | dil(anyl, 20) | curtain_strip)
    g = gain_field(render, base, keep)
    matched = srgb(lin(render) * g)
    rec = dict(lock=rec_lock, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
               gain_keep_px=int(keep.sum()))
    return ids, base, render, matched, g, env, rec


def main_cut():
    ids, base, render, matched, g, env, rec = setup()
    fg, aux = cut_all(matched, base, ids)
    np.savez_compressed(SCR + "cut.npz", matched=q(matched), gain=g.astype(np.float32), **{"fg_" + k: v for k, v in fg.items()})
    overlay(matched, fg, SCR + "cut-overlay.png")
    json.dump(rec, open(SCR + "cut-rec.json", "w"), indent=1)
    print(json.dumps(rec), {k: int(v.sum()) for k, v in fg.items()})


if __name__ == "__main__":
    if sys.argv[1] == "cut":
        main_cut()
