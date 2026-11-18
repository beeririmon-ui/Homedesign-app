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
    "bedding": [(520, 1110, 2200, 1380), (1000, 940, 1700, 975), (1700, 950, 1900, 985)],
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
def lock(ids, raw=RAW, ref=None):
    """a still at the canvas size, warped onto its reference (plate.png for r4; the edit's input for an edit): an affine fit (ECC,
    masked to the walls, headboard and nightstands)"""
    r = Image.open(raw).convert("RGB")
    r = np.asarray(r.resize((W, H), Image.LANCZOS)).astype(np.float32)
    pl = np.asarray(Image.open(ref or os.path.join(ST, "plate.png")).convert("RGB")).astype(np.float32)
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

    def gb(a, s):                                         # a Gaussian blur at 1/8 size (the field is smooth), back to the canvas
        sm = cv2.resize(a.astype(np.float32), (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = cv2.GaussianBlur(sm, (0, 0), s / 8.0, borderType=cv2.BORDER_REFLECT)
        return cv2.resize(sm, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float64)
    for s in sigmas:
        nb = gb(w, s)
        val = gb(v * w, s) / np.maximum(nb, 1e-9)
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
    return dict(caramel=(C > 27) & (h > 50) & (h < 76) & (L > 38) & (L < 78),
                walnut=(C < 27) & (L < 48) & (h > 35) & (h < 62),
                pecan=(C > 14) & (h > 28) & (h < 72) & (L < 62),
                cream=(L > 62) & (C < 14), L=L, C=C)


# the throw as r4 drew it: the band's top edge and its drapes (outer), and its lower edge (inner), traced on the locked r4
THROW_OUTER = [(388, 1264), (398, 1230), (428, 1187), (478, 1136), (546, 1092), (628, 1049), (743, 993), (880, 982), (1840, 982),
               (2092, 1021), (2162, 1061), (2205, 1091), (2247, 1116), (2280, 1154), (2314, 1195), (2339, 1233), (2356, 1264)]
THROW_INNER = [(2332, 1270), (2324, 1250), (2295, 1210), (2262, 1172), (2230, 1133), (2192, 1115), (1800, 1114), (880, 1114),
               (610, 1114), (553, 1117), (501, 1153), (451, 1203), (416, 1241), (400, 1270)]
CHAINS = [(2300, 558, 2310, 633), (2295, 627, 2314, 656), (2354, 558, 2364, 668), (2347, 662, 2369, 696)]
BASE_ELL = dict(c=(2332.0, 1259.5), a=85.0, b=18.5, side=12)       # the lamp's disc base as r4 drew it (top face + its side band)


def poly(pts):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return m.astype(bool)


def thin_dark(src, zone, k=15, t=7.0):
    """stems: darker than the local median by t L*, inside the zone"""
    L = lab_of(src)[..., 0]
    bg = cv2.medianBlur(np.clip(L * 2.55, 0, 255).astype(np.uint8), k).astype(np.float64) / 2.55
    return (bg - L > t) & zone


CURTAIN_X = (369, 547)                                     # the panel's edges on r4, vertical (it hangs at one X)


def curtain_cut(src):
    """the sheer panel between its two vertical edges; the hem per column: the strongest light-to-dark step in rows 1160-1212,
    a running median over 41 columns"""
    Y = blur(luma(src), 1.2)
    dy = np.zeros_like(Y)
    dy[3:-3] = Y[6:] - Y[:-6]
    xs = np.arange(CURTAIN_X[0], CURTAIN_X[1] + 1)
    hem = 1160 + np.argmin(dy[1160:1212, xs], 0)
    hem = np.array([np.median(hem[max(0, i - 20):i + 21]) for i in range(hem.size)])
    m = np.zeros((H, W), bool)
    for i, x in enumerate(xs):
        m[:int(round(hem[i])) + 1, x] = True
    return m, dict(edges_x=list(CURTAIN_X), hem_rows={int(x): float(hem[i]) for i, x in enumerate(xs) if (x - xs[0]) % 30 == 0})


def lamp_cut(src, same):
    """the shade (GrabCut above row 590), the collar and the stem (the dark run round x 2332, row by row), the disc base (r4's
    ellipse); the two pull chains are left out"""
    clay_shade = np.asarray(Image.open(CLAY + "MB0-id.png")) == 55
    clay_shade &= box_mask([(0, 0, W, 592)])
    zone = dil(clay_shade, 14) & box_mask([(2165, 345, 2515, 592)])
    core = ero(clay_shade, 12)
    shade = gc_cut(src, core, zone, zone, same & ~dil(core, 3))
    L = blur(lab_of(src)[..., 0], 0.8)
    stem = np.zeros((H, W), bool)
    for y in range(560, 1262):
        row = L[y, 2300:2365]
        wall = np.median(np.r_[L[y, 2270:2295], L[y, 2370:2395]])
        dark = np.nonzero(np.abs(row - wall) > 10)[0]
        dark = dark[(dark > 15) & (dark < 50)]
        if dark.size:
            stem[y, 2300 + dark.min():2300 + dark.max() + 1] = True
    stem = cv2.morphologyEx(stem.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 3), np.uint8)).astype(bool)
    stem &= box_mask([(2316, 560, 2350, 1262)])
    yy, xx = np.mgrid[0:H, 0:W]
    e = BASE_ELL
    base = np.zeros((H, W), bool)
    for dz in range(0, e["side"] + 1):                    # the disc swept down its thickness: top face, side band, bottom edge
        base |= ((xx - e["c"][0]) / e["a"]) ** 2 + ((yy - e["c"][1] - dz) / e["b"]) ** 2 <= 1
    chains = box_mask(CHAINS)
    return (shade | stem | base) & ~(chains & ~dil(shade, 0) & (yy > 575)), dict(base=base, chains=chains, shade=shade, stem=stem)


def cut_all(src, base, ids):
    lab_s, lab_b = blur(lab_of(src), 1.5), blur(lab_of(base), 1.5)
    dE = np.linalg.norm(lab_s - lab_b, axis=-1)
    same = dE < 3
    pr = priors(src)
    zones = {k: box_mask([sp["box"]] + ([sp["box2"]] if sp.get("box2") else [])) for k, sp in SLOTS.items()}
    seeds = {k: box_mask(v) for k, v in CORES.items()}
    info = {}
    fg = {}
    # the textiles first: the throw in its traced band, the pillows by their caramel, the cushion in its box, the duvet the rest
    tz = dil(poly(THROW_OUTER + THROW_INNER), 8)
    seeds["throw"] = ero(poly(THROW_OUTER + THROW_INNER), 5) & pr["pecan"]
    fg["throw"] = gc_cut(src, seeds["throw"], tz, tz, (same | pr["cream"]) & ~dil(seeds["throw"], 2))
    pz = zones["pillowcases"]
    seeds["pillowcases"] = cv2.morphologyEx((pr["caramel"] & pz).astype(np.uint8), cv2.MORPH_OPEN, disk(2)).astype(bool)
    seeds["pillowcases"] &= ~box_mask([(0, 960, W, H)])
    hard = (pr["walnut"] & ~dil(seeds["pillowcases"], 6)) | (same & ~dil(seeds["pillowcases"], 2)) | dil(seeds["cushions"], 2)
    fg["pillowcases"] = gc_cut(src, seeds["pillowcases"], pz & ~same, pz, hard)
    cz = box_mask([(1185, 762, 1540, 936)])
    fg["cushions"] = gc_cut(src, seeds["cushions"], cz, cz, ero(fg["pillowcases"], 2) | (same & ~dil(seeds["cushions"], 2)))
    fg["pillowcases"] &= ~fg["cushions"]
    bz = zones["bedding"]
    pid = np.asarray(Image.open(CLAY + "MB0-plate-id.png"))
    mat = pid == 23                                      # over the plate's mattress, "like the plate" is the duvet, not background
    hard = (same & ~mat & ~dil(seeds["bedding"], 2)) | ero(fg["pillowcases"], 3) | ero(fg["cushions"], 3)
    hard |= box_mask([(0, 880, W, 1530)]) & ~bz
    fg["bedding"] = gc_cut(src, (seeds["bedding"] | (mat & ero(bz, 1) & pr["cream"] & box_mask([(560, 1000, 2160, 1390)]))) & ~fg["throw"],
                           bz & (~same | mat), bz, hard)
    fg["bedding"] |= dil(fg["throw"], 3) & bz          # the duvet runs on under the throw (its hidden part is filled later)
    # the hard products
    fg["curtains"], info["curtain"] = curtain_cut(src)
    fg["floor-lamp"], lp = lamp_cut(src, same)
    info["lamp"] = lp
    for k in ("bedside-sconces", "sill-vase", "nightstand-tray", "nightstand-vase", "candle-holders"):
        hard = same & ~dil(seeds[k], 2)
        for o in ("bedding", "throw", "pillowcases"):
            hard |= fg[o]
        fg[k] = gc_cut(src, seeds[k], zones[k] & ~same, zones[k], hard)
    new_dark = lambda z: thin_dark(src, z) & ~thin_dark(base, dil(z, 0), t=4.0)  # noqa: E731  (dark here, not dark in the plate)
    stems_s = new_dark(box_mask([(185, 540, 340, 770)]))
    stems_n = new_dark(box_mask([(605, 685, 750, 840)]))
    for nm, st in (("s", stems_s), ("n", stems_n)):
        n_, lab_, stt, _ = cv2.connectedComponentsWithStats(dil(st, 1).astype(np.uint8), connectivity=8)
        keep_ = [i for i in range(1, n_) if stt[i, cv2.CC_STAT_AREA] >= 40]
        st &= np.isin(lab_, keep_)
        if nm == "s":
            stems_s = st
        else:
            stems_n = st
    fg["sill-vase"] |= stems_s
    # the bottle is a lathe form: its outline as r4 drew it (neck 18 px, shoulder rows 850-880, body 60 px), symmetric about x 680.5
    sym = np.zeros((H, W), bool)
    for y in range(820, 980):
        t = np.clip((y - 850) / 30.0, 0, 1)
        hw = 9 + 21 * (3 * t * t - 2 * t ** 3)
        sym[y, int(np.ceil(680.5 - hw)):int(np.floor(680.5 + hw)) + 1] = True
    sym &= fg["nightstand-vase"] | box_mask([(645, 820, 716, 980)])
    fg["nightstand-vase"] = (fg["nightstand-vase"] & ~box_mask([(640, 818, 722, 980)])) | sym
    stalks = thin_dark(src, box_mask([(630, 760, 732, 826)]), k=11, t=3.5) & ~thin_dark(base, box_mask([(630, 760, 732, 826)]), t=3.0)
    allst = stems_n | stalks
    n_, lab_ = cv2.connectedComponents(dil(allst | sym, 1).astype(np.uint8), connectivity=8)
    keep_ = set(np.unique(lab_[sym])) - {0}
    fg["nightstand-vase"] |= stems_n | (allst & np.isin(lab_, list(keep_)))
    fg["bedding"] &= ~(fg["floor-lamp"] & ~lp["base"])
    return fg, dict(dE=dE, same=same, seeds=seeds, zones=zones, info=info)


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
    env = light_envelopes()
    cache = SCR + "tone.npz"
    if os.path.exists(cache) and "retone" not in sys.argv:
        d = np.load(cache)
        return (ids, base, d["render"].astype(np.float64), d["matched"].astype(np.float64), d["gain"].astype(np.float64), env,
                json.load(open(SCR + "tone-rec.json")))
    render, rec_lock = lock(ids)
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
    np.savez(cache, render=render.astype(np.float32), matched=matched.astype(np.float32), gain=g.astype(np.float32))
    json.dump(rec, open(SCR + "tone-rec.json", "w"), indent=1)
    return ids, base, render, matched, g, env, rec


def main_cut():
    ids, base, render, matched, g, env, rec = setup()
    fg, aux = cut_all(matched, base, ids)
    np.savez_compressed(SCR + "cut.npz", matched=q(matched), gain=g.astype(np.float32), **{"fg_" + k: v for k, v in fg.items()})
    overlay(matched, fg, SCR + "cut-overlay.png")
    rec["curtain"] = aux["info"]["curtain"]
    json.dump(rec, open(SCR + "cut-rec.json", "w"), indent=1)
    print(json.dumps(rec), {k: int(v.sum()) for k, v in fg.items()})



# ---------------------------------------------------------------------------------------------------------------- 4. the 12.7 fixes
HEM_X = (455, 2285)                                       # where r4 drew the upholstered base under the duvet's hem (between the drapes)


def bedding_fix(src, fg_b, base, rec):
    """1. the hem: per column the strongest light-to-dark step in rows 1370-1470 (the duvet over the base's shade), a running median;
    below it the plate (the mattress's edge and front face). 2. the foot corners: where the plate's mattress shows beside the duvet's
    corner drape, the drape is drawn out over it (a horizontal remap of the layer, fading over 220 px), 8 px past the mattress"""
    Y = blur(luma(src), 1.0)
    dy = np.zeros_like(Y)
    dy[2:-2] = Y[4:] - Y[:-4]
    xs = np.arange(HEM_X[0], HEM_X[1] + 1)
    det = 1385 + np.argmin(dy[1385:1420, xs], 0)
    use = np.ones(xs.size, bool)
    for _ in range(5):
        cf = np.polyfit(xs[use], det[use], 2)
        res = det - np.polyval(cf, xs)
        use = np.abs(res) < max(2.5, 2.5 * np.median(np.abs(res[use])))
    hem = np.polyval(cf, xs)
    a = fg_b.copy()
    Lr = blur(to_lab(src)[..., 0], 1.0)
    for i, x in enumerate(xs):
        a[1250:int(round(hem[i])) + 1, x] = True
        a[int(round(hem[i])) + 1:, x] = False
    for x0_, x1_ in ((HEM_X[0] - 30, HEM_X[0]), (HEM_X[1] + 1, HEM_X[1] + 31)):   # next to the base: the fabric, not r4's dark base
        sub = a[1395:, x0_:x1_] & (Lr[1395:, x0_:x1_] > 40)
        sub = cv2.morphologyEx(sub.astype(np.uint8), cv2.MORPH_OPEN, disk(2)).astype(bool)
        a[1395:, x0_:x1_] = sub
    rec["hem_fit"] = dict(coef=[float(v) for v in cf], inliers=int(use.sum()), of=int(xs.size))
    # drop what is not the duvet below the hem band at the sides (r4's floor and base outside the drapes)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8), connectivity=4)
    a = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    pid = np.asarray(Image.open(CLAY + "MB0-plate-id.png"))
    mat = pid == 23
    rgb = src.copy()
    moves = {}
    for side in ("left", "right"):
        need = np.zeros(H)
        for y in range(1250, H):
            row_b, row_m = np.nonzero(a[y])[0], np.nonzero(mat[y])[0]
            if row_b.size == 0 or row_m.size == 0:
                continue
            if side == "left":
                need[y] = max(0.0, row_b.min() - row_m.min() + 8)
            else:
                need[y] = max(0.0, row_m.max() - row_b.max() + 8)
        need = np.array([need[max(0, y - 25):y + 26].max() for y in range(H)])
        need = blur(need[:, None], 12)[:, 0]
        if need.max() < 1:
            continue
        mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        sx = mx.copy()
        for y in range(1150, H):
            if need[y] < 0.5:
                continue
            row_b = np.nonzero(a[y])[0]
            if side == "left":
                x0, x1 = row_b.min() - need[y], row_b.min() + 220
                w = np.clip((x1 - mx[y]) / (x1 - x0), 0, 1)
                sx[y] = mx[y] + need[y] * w
            else:
                x0, x1 = row_b.max() - 220, row_b.max() + need[y]
                w = np.clip((mx[y] - x0) / (x1 - x0), 0, 1)
                sx[y] = mx[y] - need[y] * w
        a = cv2.remap(a.astype(np.float32), sx, my, cv2.INTER_LINEAR) > 0.5
        rgb = np.stack([cv2.remap(rgb[..., c].astype(np.float32), sx, my, cv2.INTER_CUBIC) for c in range(3)], -1).astype(np.float64)
        moves[side] = dict(max_px=round(float(need.max()), 1), rows=[int(np.nonzero(need > 0.5)[0].min()), int(np.nonzero(need > 0.5)[0].max())])
    rec["bedding_hem"] = dict(x=list(HEM_X), rows={int(x): float(hem[i]) for i, x in enumerate(xs) if (x - xs[0]) % 150 == 0})
    rec["bedding_corners"] = moves
    exposed = mat & ~dil(a, 1) & box_mask([(0, 1250, W, H)])
    rec["plate_mattress_front_face_beside_the_drapes_px"] = int((exposed & ~box_mask([(HEM_X[0], 0, HEM_X[1] + 1, H)])).sum())
    hem_line = np.full(W, -1.0)
    hem_line[xs] = hem
    return a, rgb, hem_line


def contact_shadow_hem(hem_line, a_bed, base):
    """the duvet's hem on the mattress's edge below it: 1 - 0.38 exp(-dy / 10), 34 px, on the plate's mattress only"""
    pid = np.asarray(Image.open(CLAY + "MB0-plate-id.png"))
    s = np.ones((H, W))
    yy = np.arange(H)[:, None]
    for x in np.nonzero(hem_line > 0)[0]:
        h0 = hem_line[x]
        dy = yy[:, 0] - h0
        band = (dy > 0) & (dy < 34)
        s[band, x] = 1 - 0.38 * np.exp(-dy[band] / 10.0)
    s = 1 - blur(1 - s, 2.0)
    s[(pid != 23) | a_bed] = 1
    return s


HOLDER_SRC = dict(box=(1918, 843, 2003, 980), axis=1961.5)          # r4's left holder (cup and cone), the candle above it
CANDLE_SRC = dict(box=(1938, 798, 1988, 850))
SKU_HOLDER = [0.46, 0.482, 0.474, 0.224, 0.257, 0.292, 0.326, 0.359, 0.393, 0.427, 0.462, 0.121]   # width / height, 12 levels
HOLDERS = [dict(X=0.50, Y=17.88, candle=0.10), dict(X=0.61, Y=17.82, candle=0.15)]                 # the slot points (master.json)


def profile_of(m):
    ys = np.nonzero(m.any(1))[0]
    out = {}
    for y in range(ys.min(), ys.max() + 1):
        xs_ = np.nonzero(m[y])[0]
        if xs_.size:
            out[y] = (xs_.min(), xs_.max())
    return out


def holder_sprites(src, fg_h):
    """one holder: r4's left holder, its right half mirrored (the duvet touches its left foot), resampled row by row to the SKU
    photo's outline (the Small 70 x 110: rim and foot about 0.47 of the height, waist 0.22) and to the card's 11 cm; one candle:
    r4's left candle, its top face kept and its body stretched to the filler's height, 0.8 of the rim wide. Returns RGBA sprites"""
    x0, y0, x1, y1 = HOLDER_SRC["box"]
    m = fg_h[y0:y1, x0:x1].copy()
    m[:850 - y0] = False
    ax = HOLDER_SRC["axis"] - x0
    img = src[y0:y1, x0:x1].copy()
    prof = profile_of(m)
    for yk, (l, r) in list(prof.items()):               # the duvet touches the left foot: the left edge mirrored from the right
        if yk + y0 > 955:
            prof[yk] = (max(l, int(round(2 * ax - r))), r)
        l, r = prof[yk]
        prof[yk] = (l + 1.5, r - 1.5)
    ys = sorted(prof)
    hs = ys[-1] - ys[0] + 1
    lv = np.linspace(0, 1, len(SKU_HOLDER))
    # 12.8 4d: matte, opaque travertine: the colour and the pores of the sconces' cones in this frame, a matte cylinder's shading
    # (light from the upper left, the sconce and the window), no gloss. r4's holder gives only the outline's rows now
    cone = to_lab(src[610:628, 746:776])                # inside the west cone (its lower part), no wall, no rim
    cmed = np.median(cone.reshape(-1, 3), 0)
    tex = cone - np.stack([blur(cone[..., c], 2.0) for c in range(3)], -1)

    def make(h_px):
        h_px = int(round(h_px))
        wmax = int(np.ceil(max(SKU_HOLDER) * h_px)) + 4
        out = np.zeros((h_px, wmax, 4))
        cx = (wmax - 1) / 2
        for r in range(h_px):
            f = (r + 0.5) / h_px
            sy = ys[0] + f * hs
            yi = int(np.clip(round(sy), ys[0], ys[-1]))
            l, rr = prof.get(yi, (None, None))
            if l is None:
                continue
            tw = np.interp(f, lv, SKU_HOLDER) * h_px
            xs_t = np.arange(wmax)
            u = (xs_t - (cx - tw / 2)) / max(tw, 1e-3)
            inside = (u >= 0) & (u <= 1)
            uu = np.clip((xs_t - cx) / max(tw / 2, 1e-3), -1, 1)
            shade = np.maximum(0, np.cos(np.arcsin(uu) + 0.5))
            Lm = cmed[0] - 18 + 26 * shade + (4 if f < 0.10 else 0) - 6 * max(0.0, (f - 0.88) / 0.12)
            tr_, tc_ = tex[r % tex.shape[0]], tex[r % tex.shape[0], (xs_t % tex.shape[1])]
            lab_px = np.stack([Lm + tc_[:, 0], np.full(xs_t.size, cmed[1]) + 0.5 * tc_[:, 1], np.full(xs_t.size, cmed[2]) + 0.5 * tc_[:, 2]], -1)
            out[r, :, :3] = np.clip(from_lab(lab_px), 0, 1)
            out[r, :, 3] = np.clip(np.minimum(xs_t - (cx - tw / 2) + 0.5, (cx + tw / 2) - xs_t + 0.5), 0, 1)
        return out

    cx0, cy0, cx1, cy1 = CANDLE_SRC["box"]
    cm = fg_h[cy0:cy1, cx0:cx1]
    cimg = src[cy0:cy1, cx0:cx1]
    cprof = profile_of(cm)
    cys = sorted(cprof)

    def candle(w_px, h_px):
        w_px, h_px = int(round(w_px)), int(round(h_px))
        top = 10                                           # the top face and the wick, as drawn (source rows), scaled with the width
        src_rows = cys[-1] - cys[0] + 1
        out = np.zeros((h_px, w_px + 2, 4))
        ks = w_px / max(cprof[cys[0] + top][1] - cprof[cys[0] + top][0], 1)
        tr = max(2, int(round(top * ks)))
        for r in range(h_px):
            if r < tr:
                yi = int(round(cys[0] + r / ks))
            else:
                f = (r - tr) / max(h_px - tr - 1, 1)
                yi = int(round(cys[0] + top + f * (src_rows - top - 1)))
            yi = int(np.clip(yi, cys[0], cys[-1]))
            l, rr = cprof[yi]
            l, rr = l + 1.5, rr - 1.5
            xs_t = np.arange(w_px + 2)
            u = (xs_t - 1) / max(w_px - 1, 1)
            sxs = l + u * (rr - l)
            for c in range(3):
                out[r, :, c] = np.interp(sxs, np.arange(cimg.shape[1]), cimg[yi, :, c])
            out[r, :, 3] = ((xs_t >= 1) & (xs_t <= w_px)).astype(float)
        return out
    return make, candle


def paste(dst_rgb, dst_a, spr, x_c, y_bottom):
    """sprite (RGBA) with its bottom centre at (x_c, y_bottom), sub-pixel placement by a shift of the sprite"""
    h, w = spr.shape[:2]
    X0, Y0 = x_c - (w - 1) / 2, y_bottom - h + 1
    ix, iy = int(np.floor(X0)), int(np.floor(Y0))
    fx, fy = X0 - ix, Y0 - iy
    Mt = np.float32([[1, 0, fx], [0, 1, fy]])
    pad = np.zeros((h + 2, w + 2, 4))
    pad[:h, :w] = spr
    pad[..., :3] *= pad[..., 3:4]
    sh = cv2.warpAffine(pad.astype(np.float32), Mt, (w + 2, h + 2), flags=cv2.INTER_LINEAR).astype(np.float64)
    a = sh[..., 3:4]
    rgb = np.where(a > 1e-4, sh[..., :3] / np.maximum(a, 1e-4), 0)
    sl = (slice(iy, iy + h + 2), slice(ix, ix + w + 2))
    da = dst_a[sl][..., None]
    dst_rgb[sl] = rgb * a + dst_rgb[sl] * (1 - a)
    dst_a[sl] = (a + da * (1 - a))[..., 0]


def holders_fix(src, fg_h, rec):
    make, candle = holder_sprites(src, fg_h)
    rgb = np.zeros((H, W, 3))
    a = np.zeros((H, W))
    sh = np.ones((H, W))
    out = []
    for hd in HOLDERS:
        x, y = proj(hd["X"], hd["Y"], 0.55)
        d = CAM[1] - hd["Y"]
        hp = F * 0.11 / d
        spr = make(hp)
        rim = SKU_HOLDER[1] * hp
        vis = hd["candle"] - 0.02                           # the candle stands 2 cm deep in the cup
        cs = candle(0.8 * rim, F * vis / d)
        paste(rgb, a, cs, x, y - hp + 1 + F * 0.02 / d)    # the candle first, its foot 2 cm down in the cup
        paste(rgb, a, spr, x, y)
        # the contact shadow on the stone of the nightstand's top: a soft ellipse under the foot
        yy, xx = np.mgrid[0:H, 0:W]
        e = ((xx - x) / (rim * 0.75)) ** 2 + ((yy - y - 1) / 3.2) ** 2
        sh *= 1 - 0.42 * np.exp(-e)
        out.append(dict(point=[hd["X"], hd["Y"]], foot_px=[round(x, 1), round(y, 1)], height_px=round(hp, 1), rim_px=round(rim, 1),
                        candle_cm=hd["candle"] * 100, candle_visible_px=round(F * vis / d, 1), candle_w_px=round(0.8 * rim, 1)))
    rec["candle_holders_rebuilt"] = dict(pair=out, outline="the SKU photo's Small (70 x 110): rim 0.48 h, waist 0.22 h, foot 0.46 h",
                                         texture="12.8 4d: opaque matte travertine; colour and pores from the sconces' cones in this frame, a matte cylinder's shading; r4's left holder gives only the outline rows",
                                         removed="r4's three holders (about 2x the card: 130 px tall and 73 px wide at 3.17 m)")
    sh[a > 0.02] = 1
    return rgb, a, sh


DISH_BOX = (716, 946, 798, 976)                          # r4's white block on the tray


def dish_fix(src, fg_tray, rec):
    """the white block out: below the tray's back rim (row 957) the tray runs on (OpenCV Telea inpainting from the tray beside it,
    rows 957-976); above it, the plate (not in any alpha)"""
    x0, y0, x1, y1 = DISH_BOX
    a = fg_tray.copy()
    a[y0:y1 + 1, x0:x1] = False
    out = src.copy()
    smp = src[y0:y1 + 1, 614:646]
    tile = np.concatenate([smp, smp[:, ::-1]], 1)
    seq = np.resize(np.arange(tile.shape[1]), x1 - x0)
    for y in range(y0, y1 + 1):                          # the tray's row where the tray is right of the bottle (x 711-715)
        if not fg_tray[y, 711:716].any():
            continue
        own = fg_tray[y, 614:646]
        col = np.median(src[y, 614:646][own], 0) if own.any() else np.median(src[y, 711:716], 0)
        tex = tile[y - y0, seq] - tile[y - y0].mean(0)
        out[y, x0:x1] = np.clip(col + 0.5 * tex, 0, 1)
        a[y, x0:x1] = True
    rec["dish"] = dict(removed_box=list(DISH_BOX), fill="per row where the tray shows right of the bottle: the row colour of the tray left of the bottle (x 614-645) with half its texture; above: the plate",
                       slot="trinket-dish empty this round (12.7, 3)")
    return out, a


BOTTLE_FOOT = 975                                         # r4's bottle stands on the tray at row 975


def bottle_fix(src, fg_v, rec):
    """the bottle (and its stems) back to the card's 24.5 cm: r4 drew it 155 px tall where the card is 133 px at 3.15 m; the layer
    is scaled vertically about the foot by 133 / 155 (the width, 60 px, is the card's 11 cm already)"""
    k = 133.0 / 155.0
    mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    sy = BOTTLE_FOOT - (BOTTLE_FOOT - my) / k
    a = cv2.remap(fg_v.astype(np.float32), mx, sy, cv2.INTER_LINEAR)
    rgb = np.stack([cv2.remap(src[..., c].astype(np.float32), mx, sy, cv2.INTER_CUBIC) for c in range(3)], -1).astype(np.float64)
    a = a > 0.5
    a &= box_mask([(560, 600, 780, BOTTLE_FOOT + 3)])
    keep_low = fg_v & box_mask([(0, BOTTLE_FOOT + 1, W, H)])
    rec["bottle"] = dict(scale_y=round(k, 4), foot_row=BOTTLE_FOOT, card_cm=[11, 24.5], r4_px=[60, 155], new_px=[60, 133],
                         stem_top_Z=round(CAM[2] + (HZ - (BOTTLE_FOOT - (BOTTLE_FOOT - 695) * k)) * (CAM[1] - 17.90) / F, 3))
    return np.where(keep_low[..., None], src, rgb), a | keep_low


def lamp_fix(src, fg_l, parts, rec):
    """the chains out (the shade's rim under them is inpainted from the rim beside them); the disc base in the card's brass: L* x 1.6,
    a* b* from r4's own brass collar, chroma scaled with the lightness"""
    out = src.copy()
    rim = parts["chains"] & parts["shade"]
    if rim.any():
        q8 = q(out)
        q8 = cv2.inpaint(q8, dil(rim, 1).astype(np.uint8), 3, cv2.INPAINT_TELEA)
        out = np.where(dil(rim, 1)[..., None], q8.astype(np.float64) / 255, out)
    lab = to_lab(out)
    col = lab[578:598, 2322:2343].reshape(-1, 3)
    cL, ca, cb = np.median(col, 0)
    b = parts["base"] & fg_l
    L = lab[..., 0][b]
    Ln = np.clip(L * 1.9, 0, 82)
    k = np.sqrt(Ln / max(cL, 1e-3))                      # a metal keeps its tint in the shade: chroma with the square root
    new = np.stack([Ln, ca * k * 0.9, cb * k * 0.9], -1)
    lab[b] = new
    out = np.where(b[..., None], np.clip(from_lab(lab), 0, 1), out)
    rec["floor_lamp"] = dict(chains_removed=2, sku_photo="A1 (in room, Sd30f6c7...): no pull chain; the card's text says one",
                             base_recolour=dict(L_x=1.9, chroma="collar a* b* x 0.9 sqrt(L / L_collar)", collar_Lab=[round(float(v), 1) for v in (cL, ca, cb)]),
                             base_ellipse_px=dict(BASE_ELL), base_floor_row=round(BASE_ELL["c"][1] + BASE_ELL["side"], 1),
                             base_depth_m=round(F * CAM[2] / (BASE_ELL["c"][1] + BASE_ELL["side"] - HZ), 2))
    return out


def cover_corners(a, rgb):
    """where the plate's mattress shows beside the duvet's corner drapes (rows 1150 down), the drape is drawn out over it: a
    horizontal remap of the layer fading over 220 px, 8 px past the mattress"""
    pid = np.asarray(Image.open(CLAY + "MB0-plate-id.png"))
    mat = pid == 23
    moves = {}
    for side in ("left", "right"):
        need = np.zeros(H)
        for y in range(1150, H):
            row_b, row_m = np.nonzero(a[y])[0], np.nonzero(mat[y])[0]
            if row_b.size == 0 or row_m.size == 0:
                continue
            need[y] = max(0.0, (row_b.min() - row_m.min() + 8) if side == "left" else (row_m.max() - row_b.max() + 8))
        need = np.array([need[max(0, y - 25):y + 26].max() for y in range(H)])
        need = blur(need[:, None], 12)[:, 0]
        if need.max() < 1:
            continue
        mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        sx = mx.copy()
        for y in range(1100, H):
            if need[y] < 0.5 or not a[y].any():
                continue
            row_b = np.nonzero(a[y])[0]
            if side == "left":
                x0, x1 = row_b.min() - need[y], row_b.min() + 220
                sx[y] = mx[y] + need[y] * np.clip((x1 - mx[y]) / (x1 - x0), 0, 1)
            else:
                x0, x1 = row_b.max() - 220, row_b.max() + need[y]
                sx[y] = mx[y] - need[y] * np.clip((mx[y] - x0) / (x1 - x0), 0, 1)
        a = cv2.remap(a.astype(np.float32), sx, my, cv2.INTER_LINEAR) > 0.5
        rgb = np.stack([cv2.remap(rgb[..., c].astype(np.float32), sx, my, cv2.INTER_CUBIC) for c in range(3)], -1).astype(np.float64)
        moves[side] = round(float(need.max()), 1)
    return a, rgb, moves


EDIT_RAW = os.path.join(ST, "raw/defaults-r5-edit.jpg")          # nano-banana-2 edit of the composed frame (12.8, 1a + 4a-b)
EDIT_IN = os.path.join(ST, "inputs/defaults-edit-r5-input.png")   # its input: the composed frame as sent
FOOT_Y0 = 1292                                            # the duvet's foot from the edit below this row (blended over 30 rows)


def compose_edit(ids, src, fg, srcs, rec):
    """the edit, locked onto its input and matched to it (the field, sigma 60, outside its two regions), used only in them:
    the foot: the duvet's front drop and corners from the edit below row FOOT_Y0 (no mattress side, no band), its straight crease
    softened into a fold (a vertical wave, 6 + 3 px); the throw: the edit's Pecan with its fringes, below r4's top edge of the band
    (the duvet's fold strip stays r4's), the fringes' gaps open onto the duvet"""
    e_raw, rl = lock(ids, EDIT_RAW, EDIT_IN)
    ref = load(EDIT_IN)
    foot = box_mask([(150, FOOT_Y0 - 40, 2570, H), (150, 1160, 560, H), (2230, 1160, 2570, H)])
    tpoly = poly(THROW_OUTER + [(2420, 1330), (330, 1330)])
    tzone = dil(tpoly, 45) & box_mask([(0, 0, W, 1335)])
    xs_top = np.arange(W)
    top_pts = [p for p in THROW_OUTER if 546 <= p[0] <= 2205]
    topline = np.interp(xs_top, [p[0] for p in top_pts], [p[1] for p in top_pts], left=-1, right=-1)
    above = np.zeros((H, W), bool)
    for x in range(546, 2206):
        above[:int(round(topline[x])), x] = True
    tzone &= ~above
    keep = ~(dil(foot, 30) | dil(tzone, 30))
    g = gain_field(e_raw, ref, keep)
    e = srgb(lin(e_raw) * g)
    same = np.linalg.norm(blur(to_lab(e), 1.5) - blur(to_lab(ref), 1.5), axis=-1) < 4
    pr = priors(e)
    # the throw: r4's Pecan stays above its own middle fold (its top fold, drapes and contour). Below that fold, across the band
    # (x 560-2160), the edit's hem and fringe strands, in place (the edit hung them where r4's lower layer was: tips at r4's lower
    # edge, no shift); the alpha below the fold is a chroma matte of the edit, so the duvet shows between the strands
    Le = lab_of(e)
    Ce = np.hypot(Le[..., 1], Le[..., 2])
    he = np.degrees(np.arctan2(Le[..., 2], Le[..., 1])) % 360
    pec = (Ce > 14) & (he > 25) & (he < 75) & (Le[..., 0] < 66) & tzone & ~same
    t_old = fg["throw"]
    xs_b = np.arange(560, 2161)
    tips = np.array([1000 + (np.nonzero(pec[1000:1140, x])[0].max() if pec[1000:1140, x].any() else 95) for x in xs_b], float)
    tips = np.array([np.median(tips[max(0, i - 30):i + 31]) for i in range(tips.size)])
    fold = tips - 52
    strand_a = np.zeros((H, W))
    rgb_t = srcs["throw"].copy()
    am_all = np.clip((Ce - 10.0) / 10.0, 0, 1) * ((he > 25) & (he < 75))
    for i, x in enumerate(xs_b):
        f0, t0 = int(round(fold[i])), int(round(tips[i])) + 3
        strand_a[f0:t0, x] = am_all[f0:t0, x]
        strand_a[f0:int(round(tips[i])) - 40, x] = 1.0          # the hem itself is solid; the strands below it a matte
        rgb_t[f0:t0, x] = e[f0:t0, x]
    below_fold = np.zeros((H, W), bool)
    for i, x in enumerate(xs_b):
        below_fold[int(round(fold[i])):, x] = True
    t_new = (t_old & ~below_fold) | (strand_a > 0.5)
    fg["throw"] = t_new
    fg["throw_fringe_alpha"] = np.where(below_fold, strand_a, 0.0)
    srcs["throw"] = np.where(below_fold[..., None], rgb_t, srcs["throw"])
    rec["fringe_transfer"] = dict(span_x=[560, 2160], fold_rows_p10_p50_p90=[int(v) for v in np.percentile(fold, [10, 50, 90])],
                                  tip_rows_p10_p50_p90=[int(v) for v in np.percentile(tips, [10, 50, 90])],
                                  note="the edit's hem and strands in place below r4's middle fold; the drapes stay r4's (no strands there)")
    # the foot
    L = lab_of(e)
    C_ = np.hypot(L[..., 1], L[..., 2])
    duv = foot & (C_ < 14) & (L[..., 0] > 30) & ~fg["throw"]
    duv = cv2.morphologyEx(duv.astype(np.uint8), cv2.MORPH_OPEN, disk(2)).astype(bool)
    n_, lab_ = cv2.connectedComponents(duv.astype(np.uint8), connectivity=8)
    core = box_mask([(700, FOOT_Y0, 2000, H)])
    duv = np.isin(lab_, list(set(np.unique(lab_[core & duv])) - {0}))
    inv = (~duv).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    duv |= np.isin(lab2, [i for i in range(1, n2) if i not in border])
    yy = np.arange(H)[:, None].astype(np.float64)
    xx_ = np.arange(W)[None, :]
    y0c = np.where((xx_ < 560) | (xx_ > 2230), 1200, FOOT_Y0)     # the corners' drapes from the edit from row 1200
    wgt = np.clip((yy - (y0c - 30)) / 30.0, 0, 1)
    a_old = fg["bedding"].astype(np.float64)
    foot = foot | box_mask([(150, 1160, 560, H), (2230, 1160, 2570, H)])
    below = yy >= y0c
    a_new = np.where(below, duv, fg["bedding"] | (duv & (wgt > 0)))
    rgb = srcs["bedding"] * (1 - wgt[..., None]) + e * wgt[..., None]
    rgb = np.where((fg["bedding"] & ~duv)[..., None] & (wgt[..., None] > 0), srcs["bedding"], rgb)
    # the crease: the strongest light-to-dark step in rows 1380-1425 between the corners, a soft fold instead of a ruler line
    Yl = blur(luma(e), 1.0)
    dy = np.zeros_like(Yl)
    dy[2:-2] = Yl[4:] - Yl[:-4]
    cx_ = np.arange(700, 2000)
    crease = float(np.median(1380 + np.argmax(np.abs(dy[1380:1425, cx_]), 0)))
    mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    wave = 6 * np.sin(2 * np.pi * mx / 420 + 0.7) + 3 * np.sin(2 * np.pi * mx / 170 + 2.1)
    env = np.exp(-((my - crease) / 34.0) ** 2) * (my > crease - 90)
    sy = (my + wave * env).astype(np.float32)
    rgb = np.stack([cv2.remap(rgb[..., c].astype(np.float32), mx, sy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE) for c in range(3)], -1)
    a_new = cv2.remap(a_new.astype(np.float32), mx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) > 0.5
    a_new, rgb, cmoves = cover_corners(a_new, rgb.astype(np.float64))
    fg["bedding"] = a_new
    srcs["bedding"] = np.clip(rgb, 0, 1)
    rec["edit_r5_corners_drawn_out_px"] = cmoves
    fg["floor-lamp"] &= ~ero(a_new, 3)
    rec["edit_r5"] = dict(raw="raw/defaults-r5-edit.jpg", input="inputs/defaults-edit-r5-input.png", lock=rl,
                          gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g[keep], [1, 50, 99])],
                          used=["the throw's fringe strands only, hung under r4's Pecan (its fold, drop and contour kept)",
                                f"the duvet's foot below row {FOOT_Y0} (blend 30 rows), crease at row {crease:.0f} waved 6 + 3 px"],
                          throw_px=int(fg["throw"].sum()), foot_px=int((a_new & below).sum()))
    return fg, srcs, crease


LAMP_CONTACT = (2332.0, 1271.5)                           # the disc base's floor contact as r4 drew it (its centre, bottom)


def pole_band(fg_l, parts, rec):
    """the pole below the collar as one clean band: its two edges fitted with robust lines over rows 610-1235 (the cut had a step)"""
    st = parts["stem"]
    rows = np.arange(610, 1236)
    L_, R_ = [], []
    for y in rows:
        xs_ = np.nonzero(st[y, 2300:2365])[0]
        L_.append(2300 + xs_.min() if xs_.size else np.nan)
        R_.append(2300 + xs_.max() if xs_.size else np.nan)
    out = {}
    for nm, v in (("left", np.array(L_)), ("right", np.array(R_))):
        ok = ~np.isnan(v)
        use = ok.copy()
        for _ in range(4):
            b, a = np.polyfit(rows[use], v[use], 1)
            use = ok & (np.abs(v - (a + b * rows)) < 2.5)
        out[nm] = (a, b)
    band = np.zeros((H, W), bool)
    for y in range(596, 1262):
        l = out["left"][0] + out["left"][1] * y
        r = out["right"][0] + out["right"][1] * y
        band[y, int(round(l)):int(round(r)) + 1] = True
    zone = box_mask([(2306, 596, 2360, 1262)]) & ~parts["base"] & ~parts["shade"]
    rec["pole_band"] = dict(left=[round(out["left"][0] + out["left"][1] * 610, 1), round(out["left"][0] + out["left"][1] * 1235, 1)],
                            right=[round(out["right"][0] + out["right"][1] * 610, 1), round(out["right"][0] + out["right"][1] * 1235, 1)])
    return (fg_l & ~zone) | (band & zone) | (fg_l & parts["shade"])


def lamp_scale(parts, rec):
    """12.8, 3: uniform about the base's floor contact so the lamp reads 158 at the base's depth; then, if the shade still reads over
    43 +-2, the shade alone horizontally about the pole (the off-axis widening of a circle at the lamp's place taken out)"""
    cx, cy = LAMP_CONTACT
    d = F * CAM[2] / (cy - HZ)
    ys = np.nonzero(parts["shade"].any(1))[0]
    xs = np.nonzero(parts["shade"].any(0))[0]
    top, rim = ys.min(), ys.max()
    h_m = (cy - top) * d / F
    s = 1.58 / h_m
    X = CAM[0] + (cx - CX) * d / F
    th = np.linspace(0, 2 * np.pi, 1441)

    def width(r):
        u = CX + F * (X + r * np.cos(th) - CAM[0]) / (d - r * np.sin(th))
        return u.max() - u.min()
    wf = width(0.215) / (2 * 0.215 * F / d)
    w_m = (xs.max() - xs.min() + 1) * s * d / F / wf
    k = 1.0 if w_m <= 0.45 else 0.43 / w_m
    rim_dest = cy + (rim - cy) * s
    new_l = cx - (cx - xs.min()) * s * k
    new_r = cx + (xs.max() + 1 - cx) * s * k
    u = lambda x: (x - FRAME[0]) / (FRAME[2] - FRAME[0])  # noqa: E731
    rec["floor_lamp_scale"] = dict(depth_m=round(d, 3), drawn_height_m=round(h_m, 3), uniform=round(s, 4), shade_drawn_m=round(w_m / s, 3),
                                   shade_after_uniform_m=round(w_m, 3), shade_x=round(k, 4), shade_final_m=round(w_m * k, 3),
                                   offaxis_widening=round(wf, 3), base_final_cm=round(27.5 * s, 1),
                                   shade_u=[round(u(new_l), 4), round(u(new_r), 4)], right_margin_u=round(1 - u(new_r), 4),
                                   gap_to_right_cone_u=round(u(new_l) - u(2015), 4))
    return dict(s=s, k=k, cx=cx, cy=cy, rim_dest=rim_dest)


def lamp_remap(arr, lm, interp):
    mx, my = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    t = np.clip((lm["rim_dest"] + 4 - my) / 6.0, 0, 1)
    kk = 1 * (1 - t) + lm["k"] * t
    sx = (lm["cx"] + (mx - lm["cx"]) / (lm["s"] * kk)).astype(np.float32)
    sy = (lm["cy"] + (my - lm["cy"]) / lm["s"]).astype(np.float32)
    if arr.ndim == 2:
        return cv2.remap(arr.astype(np.float32), sx, sy, interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float64)
    return np.stack([cv2.remap(arr[..., c].astype(np.float32), sx, sy, interp, borderMode=cv2.BORDER_REPLICATE) for c in range(arr.shape[2])], -1).astype(np.float64)


def curtain_fix(src, fg_c, rec):
    """the hem level at 12 cm (WM-C3): at the panel's X (-2.255) the hem row is HZ + F (1.05 - 0.12) / d(x); r4's hem is about level
    in the picture, so the near folds hang short. Per column, rows 300 .. r4's hem are stretched to 300 .. the target"""
    xs = np.arange(CURTAIN_X[0], CURTAIN_X[1] + 1)
    Y = blur(luma(src), 1.2)
    dy = np.zeros_like(Y)
    dy[3:-3] = Y[6:] - Y[:-6]
    hem = 1160 + np.argmin(dy[1160:1212, xs], 0)
    hem = np.array([np.median(hem[max(0, i - 20):i + 21]) for i in range(hem.size)])
    out = src.copy()
    a = fg_c.copy()
    tgt = {}
    for i, x in enumerate(xs):
        d = F * (CAM[0] - (-2.255)) / (CX - x)
        t = HZ + F * (CAM[2] - 0.12) / d
        h0 = hem[i]
        tgt[int(x)] = round(float(t), 1)
        if t <= h0 + 0.5:
            a[int(round(t)) + 1:, x] = False
            continue
        ys = np.arange(300, int(round(t)) + 1)
        sy = 300 + (ys - 300) * (h0 - 300) / (t - 300)
        for c in range(3):
            out[ys, x, c] = np.interp(sy, np.arange(H), src[:, x, c])
        a[300:int(round(t)) + 1, x] = True
        a[int(round(t)) + 1:, x] = False
    rec["curtain_hem"] = dict(rule="12 cm over the floor at X -2.255", r4_rows={int(k): float(hem[i]) for i, k in enumerate(xs) if (k - xs[0]) % 44 == 0},
                              target_rows={k: v for k, v in tgt.items() if (k - xs[0]) % 44 == 0})
    return out, a



# ---------------------------------------------------------------------------------------------------------------- 5. shadows, light
def soft(fg):
    a = blur(fg.astype(np.float64), 0.8)
    a = np.where(ero(fg, 1), 1.0, a)
    a[~dil(fg, 2)] = 0
    return np.clip(a, 0, 1)


def defringe(rgb, fg, r=2):
    inner = ero(fg, r).astype(np.float64)
    w = blur(inner, 2.0)
    out = rgb.copy()
    edge = dil(fg, 2) & (inner == 0) & (w > 0.02)
    for c in range(3):
        v = blur(rgb[..., c] * inner, 2.0) / np.maximum(w, 1e-6)
        out[..., c][edge] = v[edge]
    return out


def shadow_of(src, base, fg, sp, block, extra_block=None, cap=0.7):
    """the bath's: the render's darkening of the plate (luma ratio, 3 px blur, under 3 % ignored) in a contact rim and a band round
    the product, fading with the distance; never on another product"""
    rat = np.clip(blur(luma(src), 3) / np.maximum(blur(luma(base), 3), 1e-4), 0, 1)
    support = dil(fg, 2)
    env = dil(fg, sp["band"])
    env &= ~block
    if extra_block is not None:
        env &= ~extra_block
    dist = cv2.distanceTransform((~fg).astype(np.uint8), cv2.DIST_L2, 5)
    valid = env & ~support & ((rat > 0.35) | (dist <= sp["rim"]))
    taper = np.clip(1 - dist / max(sp["band"], 1), 0, 1) ** 1.5
    dark = np.clip((1 - rat) - 0.03, 0, cap) * valid * taper
    w = blur(valid.astype(np.float64), 3)
    fill = blur(dark, 3) / np.maximum(w, 1e-6)
    edge = support & ~ero(fg, 3) & ~block & (w > 0.05)
    dark = np.where(edge, fill, dark)
    soft_env = np.clip(blur((env | edge).astype(np.float64), 6) * 1.6, 0, 1) * (env | edge)
    s = 1 - blur(dark * soft_env, 1.5)
    s[~dil(env | edge, 2)] = 1
    s = np.where(s > 0.996, 1.0, s)
    return np.clip(s, 0, 1)


def fill_under(rgb, have, region, axis):
    """the hidden part of a layer under the one above it: per row (axis 1) or column (axis 0), linear between the nearest own pixels"""
    out = rgb.copy()
    rr = region & ~have
    lines = np.nonzero(rr.any(axis))[0]
    for i in lines:
        own = have[:, i] if axis == 0 else have[i]
        need = rr[:, i] if axis == 0 else rr[i]
        idx = np.nonzero(own)[0]
        if idx.size < 2:
            continue
        tgt = np.nonzero(need)[0]
        for c in range(3):
            line = out[:, i, c] if axis == 0 else out[i, :, c]
            vals = np.interp(tgt, idx, line[idx])
            if axis == 0:
                out[tgt, i, c] = vals
            else:
                out[i, tgt, c] = vals
    return out


def compose_one(stack, rgba, s8):
    a = rgba[..., 3:4].astype(np.float64) / 255
    return np.rint((stack * 255 * s8[..., None] / 255) * (1 - a) + rgba[..., :3].astype(np.float64) * a) / 255


def light_one(stack, L8):
    return (255 - np.rint((255 - stack * 255) * (255 - L8.astype(np.float64)) / 255)) / 255


def albedo_lab(src, mask, plate, allfg):
    """4d, the R5 way: the product's median colour divided by the plate's light round it relative to the lit plaster (x 1250-1450,
    y 150-300, L* 88-89), i.e. as if in the lit plaster's light"""
    ring = dil(mask, 90) & ~dil(mask, 45) & ~dil(allfg, 45)
    ref = np.median(lin(plate[150:300, 1250:1450]).reshape(-1, 3), 0)
    illum = np.median(lin(plate[ring]), 0) / ref
    alb = np.median(lin(src[mask]), 0) / np.maximum(illum, 1e-4)
    return to_lab(srgb(np.clip(alb, 0, 1))[None, None])[0, 0], illum


SKU_MID = {"bedding": [86.4, 0.4, -2.1], "cushions": [80.3, 1.9, 4.4], "cones": [86.5, 3.8, 14.1]}    # the SKU photos' mid-tones


def de00(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = dh - 360 * np.sign(dh) if abs(dh) > 180 else dh
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hbp = (h1p + h2p + (360 if abs(h1p - h2p) > 180 else 0)) / 2
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.2 * np.cos(np.radians(4 * hbp - 63))
    SL = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    RT = -2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hbp - 275) / 25) ** 2)))
    return float(np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH)))


def main_all():
    ids, base, render, matched, g, env, rec = setup()
    src = matched
    fg, aux = cut_all(src, base, ids)
    lamp_parts = aux["info"]["lamp"]
    rec["curtain_cut"] = aux["info"]["curtain"]
    srcs = {k: src for k in SLOTS}
    old = {k: fg[k].copy() for k in SLOTS}
    a_bed, srcs["bedding"], hem_line = bedding_fix(src, fg["bedding"], base, rec)
    fg["bedding"] = a_bed
    rgb_h, a_h, sh_h = holders_fix(src, fg["candle-holders"], rec)
    srcs["nightstand-tray"], fg["nightstand-tray"] = dish_fix(src, fg["nightstand-tray"], rec)
    srcs["nightstand-vase"], fg["nightstand-vase"] = bottle_fix(src, fg["nightstand-vase"], rec)
    srcs["floor-lamp"] = lamp_fix(src, fg["floor-lamp"], lamp_parts, rec)
    fg["floor-lamp"] = pole_band(fg["floor-lamp"], lamp_parts, rec)
    old["floor-lamp"] = fg["floor-lamp"].copy()
    lm = lamp_scale(lamp_parts, rec)
    srcs["floor-lamp"] = np.clip(lamp_remap(srcs["floor-lamp"], lm, cv2.INTER_CUBIC), 0, 1)
    fg["floor-lamp"] = lamp_remap(fg["floor-lamp"], lm, cv2.INTER_LINEAR) > 0.5
    fg["floor-lamp"] &= ~ero(a_bed, 3)
    srcs["curtains"], fg["curtains"] = curtain_fix(src, fg["curtains"], rec)
    edited = os.path.exists(EDIT_RAW) and "noedit" not in sys.argv
    if edited:                                            # 12.8: the one model edit, used only inside its two regions
        fg, srcs, foot_line = compose_edit(ids, src, fg, srcs, rec)
        fringe_a = fg.pop("throw_fringe_alpha")
        a_bed = fg["bedding"]
    # the duvet closes up to the throw's lower edge (GrabCut left a seam there: the throw's shadow line), 12.8 4c
    comb = cv2.morphologyEx((fg["bedding"] | fg["throw"]).astype(np.uint8), cv2.MORPH_CLOSE, disk(6)).astype(bool)
    fg["bedding"] |= comb & dil(fg["throw"], 6) & box_mask([(0, 900, W, H)])
    # the hidden parts under the layer above: the duvet under the throw, the pillows under the cushion
    t_any = fg["throw"] | old["throw"]                    # the old throw's lower layer too: the duvet shows between the new strands
    under_t = dil(t_any, 3) & fg["bedding"]
    srcs["bedding"] = fill_under(srcs["bedding"], fg["bedding"] & ~dil(t_any, 2), under_t, 0)
    pill_under = dil(fg["cushions"], 3) & box_mask([(1185, 762, 1540, 960)]) & ~fg["bedding"]
    srcs["pillowcases"] = fill_under(srcs["pillowcases"], fg["pillowcases"] & ~dil(fg["cushions"], 2), pill_under, 1)
    fg["pillowcases"] = fg["pillowcases"] | pill_under
    # 4d, the cushion: it read as light as the plaster beside it (L* 89 against 90); Milk Tea is a greige about 18 L* under its
    # photo's white. Linear x 0.758 (median L* 89.3 to 80), a* + 1.5 (the photo's 1.9 against 0.3)
    cm = fg["cushions"]
    labc = to_lab(np.clip(srgb(lin(srcs["cushions"]) * 0.758), 0, 1))
    labc[..., 1] += 1.5
    labc[..., 2] += 1.5
    srcs["cushions"] = np.where(dil(cm, 2)[..., None], np.clip(from_lab(labc), 0, 1), srcs["cushions"])
    rec["cushion_tone"] = dict(before_Lab=[89.3, 0.3, 7.6], linear_x=0.758, da=1.5, db=1.5, sku_Lab=SKU_MID["cushions"],
                               note="the wall above the headboard reads L* 90.1 a* 0.3 b* 4.5")
    order = sorted(SLOTS, key=lambda k: SLOTS[k]["z"])
    alpha = {k: soft(fg[k]) for k in order}
    if edited:                                            # the fringe strands keep their own soft (chroma) matte
        alpha["throw"] = np.maximum(soft(fg["throw"] & ~(fringe_a > 0)), fringe_a)
    alpha["candle-holders"] = a_h
    srcs["candle-holders"] = np.where(a_h[..., None] > 0, rgb_h, src)
    fgb = {k: alpha[k] > 0.5 for k in order}
    # 4d: the tones against the SKU photos
    allfg = np.zeros((H, W), bool)
    for k in order:
        allfg |= fgb[k]
    t4d = {}
    lab_cone = np.zeros((H, W), bool)
    for bx in ((745, 575, 790, 630), (1955, 575, 2000, 630)):
        lab_cone |= box_mask([bx]) & fgb["bedside-sconces"]
    plaster = to_lab(np.median(base[150:300, 1250:1450].reshape(-1, 3), 0)[None, None])[0, 0]
    for nm, msk, src_ in (("bedding", ero(fgb["bedding"], 6) & box_mask([(520, 1130, 2200, 1380)]) & ~dil(fgb["throw"], 8), srcs["bedding"]),
                          ("cushions", ero(fgb["cushions"], 6), srcs["cushions"]), ("cones", lab_cone, src)):
        if nm == "cones":                                 # small, on the plaster: in the light of the plaster round them
            al, il = albedo_lab(src_, msk, base, allfg)
        else:                                             # the textiles have no plaster round them: as they read in the frame
            al, il = to_lab(np.median(src_[msk], 0)[None, None])[0, 0], np.ones(3)
        t4d[nm] = dict(albedo_Lab=[round(float(v), 1) for v in al], sku_Lab=SKU_MID[nm], illum_rgb=[round(float(v), 3) for v in il],
                       dE00=round(de00(al, SKU_MID[nm]), 2), dL=round(float(al[0] - SKU_MID[nm][0]), 1),
                       dab=[round(float(al[1] - SKU_MID[nm][1]), 1), round(float(al[2] - SKU_MID[nm][2]), 1)])
    t4d["plaster_ref_Lab"] = [round(float(v), 1) for v in plaster]
    t4d["method"] = ("cones: median linear colour over the plate's light round them relative to the lit plaster (x 1250-1450, y 150-300); "
                     "duvet and cushion: their median in the frame (no plaster round them), next to the lit plaster's reading")
    rec["tones_4d"] = t4d
    # shadows
    shadow = {}
    below_hem = np.zeros((H, W), bool)
    for x in np.nonzero(hem_line > 0)[0]:
        below_hem[int(round(hem_line[x])) + 1:, x] = True
    for k in order:
        oth = np.zeros((H, W), bool)
        for o in order:
            if o != k:
                oth |= fgb[o]
        sp = SLOTS[k]
        if k == "candle-holders":
            shadow[k] = sh_h
            continue
        extra = None
        cap = 0.7
        if k == "bedding" and not edited:
            extra = below_hem
        if k == "curtains":
            cap = 0.25
        sk = shadow_of(srcs[k] if k not in ("bedding",) else src, base, old[k] if k not in ("bedding", "curtains") else fgb[k],
                       sp, dil(oth, 1), extra, cap)
        if k == "bedding":
            if not edited:
                sk = sk * contact_shadow_hem(hem_line, fgb["bedding"], base)
        if k == "floor-lamp":                             # the lamp's own shadow goes with it
            sk = 1 - lamp_remap(1 - sk, lm, cv2.INTER_LINEAR)
        if k == "candle-holders" or k == "nightstand-tray":
            sk[dil(old["candle-holders"], 2)] = 1
        sk[dil(oth, 1)] = 1
        shadow[k] = np.where(sk > 0.996, 1.0, sk)
    # removed things are not shadows of anything
    gone = (old["candle-holders"] & ~fgb["candle-holders"]) | box_mask([DISH_BOX]) & ~fgb["nightstand-tray"]
    gone |= old["nightstand-vase"] & ~fgb["nightstand-vase"]
    gone |= lamp_parts["chains"] & ~fgb["floor-lamp"]
    gone |= old["floor-lamp"] & ~fgb["floor-lamp"]
    hole = dil(gone, 6)                                   # under what was removed: each shadow carried on from round it, softly
    t = np.clip(blur(hole.astype(np.float64), 4) * 1.5, 0, 1)
    for k in order:
        if k == "candle-holders":
            continue
        d_ = 1 - shadow[k]
        w = (~hole).astype(np.float64)
        v = blur(d_ * w, 10) / np.maximum(blur(w, 10), 1e-6)
        sk = 1 - (d_ * (1 - t) + v * t)
        for o in order:
            if o != k:
                sk[fgb[o]] = 1
        shadow[k] = np.where(sk > 0.996, 1.0, np.clip(sk, 0, 1))
    # the stack, then the light (screen) solved on it
    stack = base.copy()
    rgb_out = {}
    for k in order:
        a = alpha[k][..., None]
        if k == "throw":                                  # over the duvet r4's own edge pixels are right (the duvet is under them);
            rgb_out[k] = np.where(dil(fgb["bedding"], 1)[..., None], srcs[k], defringe(srcs[k], fgb[k], 3))   # only the outer edge defringed
        elif k == "candle-holders":
            rgb_out[k] = srcs[k]
        else:
            rgb_out[k] = defringe(srcs[k], fgb[k])
        stack = stack * shadow[k][..., None]
        stack = stack * (1 - a) + rgb_out[k] * a
    prod = np.zeros((H, W), bool)
    for k in order:
        prod |= alpha[k] > 0
    # the render with what was removed inpainted: the light is read from the wall, not from the old objects
    gone_px = dil(gone, 3)
    src_c = cv2.inpaint(q(src), gone_px.astype(np.uint8), 6, cv2.INPAINT_TELEA).astype(np.float64) / 255
    lights = {}
    a_all = 1 - np.prod(np.stack([1 - alpha[k] for k in order]), axis=0)
    prod_l = prod | dil(old["floor-lamp"], 2)
    for nm, e in env.items():
        e2 = dil(e, 60) & ~dil(prod_l, 1)
        Lr = np.where(e2[..., None] & (src_c > stack), 1 - (1 - src_c) / np.maximum(1 - stack, 1e-3), 0.0)
        Lr = np.clip(blur(np.clip(Lr, 0, 1), 4) - 0.012, 0, 1) * e2[..., None]
        hole = (dil(gone, 8) | dil(prod_l, 1)) & dil(e, 60)   # removed things and the products: carried on from round them
        w = (e2 & ~hole).astype(np.float64)
        t = np.clip(blur(hole.astype(np.float64), 4) * 1.5, 0, 1)
        bw = blur(w, 12)
        for c in range(3):
            v = np.where(bw > 1e-3, blur(Lr[..., c] * w, 12) / np.maximum(bw, 1e-3), 0)
            Lr[..., c] = Lr[..., c] * (1 - t) + v * t
        Lr *= (e2 | hole)[..., None]
        fe = np.clip(blur(e.astype(np.float64), 30) * 1.25, 0, 1)
        Lx = np.clip(Lr * fe[..., None], 0, 1)
        if nm == "floor-lamp":
            Lx = np.clip(lamp_remap(Lx, lm, cv2.INTER_LINEAR), 0, 1)
        lights[nm] = Lx * (1 - a_all)[..., None]       # never on a product; at a soft edge, as much as the plate shows
    rec["light_solve"] = "screen solved on the stack (plate, shadows, products), from r4 with the removed objects inpainted; blur 4 px, " \
                         "minus 0.012; the lamps' windows feathered 30 px (no hard edge); continuous under the products, then x (1 - their alpha); " \
                         "the floor lamp's moved with the lamp's scaling"
    write_set(order, alpha, shadow, rgb_out, lights, base, rec)


LIGHTS = {"sconce": ("bedside-sconces", ["sconce-w", "sconce-e"]), "floor-lamp": ("floor-lamp", ["floor-lamp"])}


def write_set(order, alpha, shadow, rgb_out, lights, base, rec):
    plate8 = (np.clip(base, 0, 1) * 255 + 0.5).astype(np.uint8)
    man = dict(id="wm-master-mb0-layers-2026-11-18", room="master", style="warm-modern", frame="MB0", canvas=[W, H],
               frame_box=[round(v, 2) for v in FRAME], base="plate.png (steps 1-4), byte for byte",
               color="8-bit sRGB, no ICC profile; blending on the sRGB-encoded values",
               compose=dict(order=["base"] + [f"{k}-shadow, {k}" for k in order] + ["light (screen)"],
                            formula="for each product in z order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, "
                                    "straight alpha; then each light: out = 255 - round((255 - out) * (255 - L) / 255)",
                            swap_region="per product: alpha > 0 or shadow < 255; a product changes nothing outside its region"),
               grade="every layer is cut from r4 matched to plate.png (MP-I1 field); MP-I2's toe is in plate.png and r4 already",
               cut="tools/compose_defaults.py (GrabCut in the slot's box, traced throw, analytic lamp base, rebuilt candle holders)", layers=[])
    stack = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    for k in order:
        sp = SLOTS[k]
        a8 = q(alpha[k])
        rgba = np.dstack([q(rgb_out[k]), a8])
        rgba[..., :3][a8 == 0] = 0
        s8 = q(shadow[k])
        lp = os.path.join(ST, "layers", k, sp["pid"] + ".png")
        sh = os.path.join(ST, "shadows", k, sp["pid"] + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sh), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp)
        Image.fromarray(s8).save(sh)
        stack = compose_one(stack, rgba, s8)
        r = (a8 > 0) | (s8 < 255)
        region |= r
        ys, xs = np.nonzero(r)
        man["layers"].append(dict(slot=k, product=sp["pid"], z=sp["z"], default=True, layer=os.path.relpath(lp, ST),
                                  shadow=os.path.relpath(sh, ST), shadow_z=sp["z"] - 1, alpha_px=int((a8 > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
    man["light"] = []
    out = stack
    for nm, (slot, parts) in LIGHTS.items():
        L = np.zeros((H, W, 3))
        for p_ in parts:
            L = 1 - (1 - L) * (1 - lights[p_])
        L8 = q(L)
        pid = SLOTS[slot]["pid"]
        lpth = os.path.join(ST, "light", pid + ".png")
        os.makedirs(os.path.dirname(lpth), exist_ok=True)
        Image.fromarray(L8).save(lpth)
        out = light_one(out, L8)
        region |= L8.max(2) > 0
        man["light"].append(dict(product=pid, slot=slot, file=os.path.relpath(lpth, ST), z=90, blend="screen", px=int((L8.max(2) > 0).sum()),
                                 note="the light on the plate only; the light that falls on a product is in that product's own layer"))
    o8 = q(out)
    Image.fromarray(o8).save(os.path.join(ST, "mb0-defaults.png"))
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    Image.fromarray(o8).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, "mb0-defaults-frame.png"))
    diff_out = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=diff_out,
                       rule="outside every alpha, shadow and light: plate.png, pixel for pixel")
    man["variants"] = []
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    rec["rnd2"] = man["rnd2"]
    lab = to_lab(o8.astype(np.float64) / 255)[int(FRAME[1]):int(FRAME[3]), int(FRAME[0]):int(FRAME[2]), 0]
    rec["black_point_L_p01_p001"] = [round(float(np.percentile(lab, 1)), 2), round(float(np.percentile(lab, 0.1)), 2)]
    json.dump(rec, open(os.path.join(ST, "mb0-defaults-compose.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps(man["rnd2"]), json.dumps(rec.get("tones_4d")), rec["black_point_L_p01_p001"])


if __name__ == "__main__":
    if sys.argv[1] == "cut":
        main_cut()
    elif sys.argv[1] == "all":
        main_all()
