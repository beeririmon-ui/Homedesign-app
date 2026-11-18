#!/usr/bin/env python3
"""
fb10_compose.py: the FB9/FB10 products on MB0 as new layers over the approved round-9 set (render-agent, 2026-11-18; 0 tokens beyond
the three nano edits). Per pass the nano edit is locked onto its input (ECC affine, masked to the stable ids outside the pass's zone)
and matched to the approved composite outside the zone (the gain field, sigma 60: MP-I1; the MP-I2 toe is in the base it was made
from). Each product is cut on its own (GrabCut / its own geometry), its colour unmixed at the edge, and set on the canvas as an RGBA
layer; its shadow is the edit's darkening of the composite round it (multiply, one z below). Where the edit missed the product card
(size, outline, pattern), the layer is corrected in code from the SKU photo and the card, and its shadow follows (see the README,
FB10). The prints go into the frames in code from the flat files. The lights are taken off the new products (x 1 - alpha); then the
frame is recomposed from the layer files (plate.png, layers in z order, lights): outside every alpha, shadow and light nothing
differs from plate.png (RND2).
  python3 fb10_compose.py            (run after compose_defaults.py all, which rewrites the manifest without these layers)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402

PICKS = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/"
H, W = C.H, C.W
F_, CX_, HZ_ = 1710.0, 1360.0, 707.3
PH = json.load(open(os.path.join(ST, "fb10", "placeholders.json")))
LAYERS = {   # slot: pass, z, product id, sold
    "wall-shelf": ("p1-wall", 11, "wall-shelf-walnut-180x24-fixed-not-sold", False),
    "framed-art": ("p1-wall", 12, "framed-art-aliexpress-japandi-bare-branch-70x100-776445-50x70-walnut-float", True),
    "framed-art-2": ("p1-wall", 13, "framed-art-aliexpress-misty-landscape-386242-work-05-30x40", True),
    "shelf-vase-left": ("p1-wall", 18, "vase-cj-charcoal-carved-style-b", True),
    "shelf-vase-right": ("p1-wall", 18, "vase-cj-white-plum-hand-thrown-m", True),
    "planter": ("p2-corner", 30, "planter-cj-cement-ribbed-belly-beige-large-ficus-audrey", True),
    "magazine-holder": ("p2-corner", 38, "magazine-holder-cj-gunmetal-leather-strap-orange", True),
    "bedside-carafe": ("p3-islands", 46, "open-shelf-ceramics-cj-patina-clay-pitcher-c03d140", True),
    "trinket-dish": ("p3-islands", 46, "trinket-dish-cj-travertine-rough-edge-10x10", True),
}
ZONES = {"p1-wall": [(847, 60, 1873, 530)], "p2-corner": [(2200, 150, 2720, 1530)], "p3-islands": [(1780, 760, 2060, 1000), (700, 930, 830, 990)]}


def proj(X, Y, Z):
    d = 21.05 - Y
    return CX_ + F_ * (X + 0.70) / d, HZ_ + F_ * (1.05 - Z) / d


def zone_mask(p, pad=0):
    return C.box_mask(ZONES[p], pad)


def lock2(ids, raw, ref_path, p):
    """C.lock with the pass's zone (grown 60 px) out of the ECC mask: the placeholders there are not in the edit"""
    r = np.asarray(Image.open(raw).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
    pl = np.asarray(Image.open(ref_path).convert("RGB")).astype(np.float32)
    prod = C.dil((ids >= 40) & (ids < 90), 30)
    stable = np.isin(ids, [20, 24, 25, 26, 1, 2, 5, 9, 10, 12, 13, 14]) & ~prod & ~zone_mask(p, 60)
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
    return np.clip(out / 255, 0, 1).astype(np.float64), dict(method="ECC affine on the gradient magnitude, masked to the stable ids outside the pass's zone",
                                                              ecc=cc, warp=[[round(float(v), 6) for v in row] for row in warp])


def edit_of(p, ids, ref, rec):
    j = JOBS[p]
    cache = os.environ.get("FB10_CACHE")
    if cache and os.path.exists(os.path.join(cache, p + ".npz")):
        z = np.load(os.path.join(cache, p + ".npz"), allow_pickle=True)
        e, rl = z["e"].astype(np.float64), z["rl"].item()
    else:
        e, rl = lock2(ids, os.path.join(ST, j["raw"]), os.path.join(ST, j["input"]), p)
        if cache:
            np.savez(os.path.join(cache, p + ".npz"), e=e.astype(np.float32), rl=np.array(rl, dtype=object))
    keep = ~zone_mask(p, 40)
    keep[1450:] = False
    g = C.gain_field(e, ref, keep)
    eg = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    d = np.linalg.norm(C.to_lab(C.blur(eg, 1.0)) - C.to_lab(C.blur(ref, 1.0)), axis=-1)
    rec.setdefault("passes", {})[p] = dict(lock=rl, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
                                           dE_outside_zone_p50_p95=[round(float(v), 2) for v in np.percentile(d[keep], [50, 95])])
    return eg


def largest(m):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    return lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])) if n > 1 else m


def fill_holes(m, max_area=10 ** 9):
    inv = (~m).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    return m | np.isin(lab, [i for i in range(1, n) if i not in border and st[i, cv2.CC_STAT_AREA] < max_area])


def warp_layer(rgb, a, M, size=(W, H)):
    """an RGBA (premultiplied for the resampling) through a 2x3 affine (dst = M @ src)"""
    pm = np.dstack([rgb * a[..., None], a])
    out = cv2.warpAffine(pm.astype(np.float32), M.astype(np.float32), size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    a2 = np.clip(out[..., 3], 0, 1).astype(np.float64)
    rgb2 = out[..., :3] / np.maximum(a2[..., None], 1e-6)
    return np.clip(rgb2, 0, 1), a2


def scale_about(s_x, s_y, cx, cy, tx=0.0, ty=0.0):
    return np.array([[s_x, 0, cx - s_x * cx + tx], [0, s_y, cy - s_y * cy + ty]])


def darkening(e, ref):
    """the edit's darkening of the approved composite (luma ratio, 2 px blur, under 3 % ignored)"""
    rat = np.clip(C.blur(C.luma(C.lin(e)), 2) / np.maximum(C.blur(C.luma(C.lin(ref)), 2), 1e-4), 0, 1.2)
    return np.clip(1 - rat - 0.03, 0, 0.7)


def fill_from(dark, have, region, s=4):
    """dark inside region from the pixels in have (normalised blur, widening until filled)"""
    out = dark.copy()
    need = region & ~have
    for sig in (s, 2 * s, 4 * s, 8 * s):
        if not need.any():
            break
        num = C.blur(dark * have, sig)
        den = C.blur(have.astype(np.float64), sig)
        ok = need & (den > 0.05)
        out[ok] = num[ok] / den[ok]
        need &= ~ok
    return out


def shadows_for(dark, objs, band, block):
    """each object's shadow: the darkening in a band round its new outline (not on any new object, nor on block), the pixel going to
    the nearest object; tapered over the band; returned as multiply maps (1 = none)"""
    names = list(objs)
    dist = np.stack([cv2.distanceTransform((~objs[n]).astype(np.uint8), cv2.DIST_L2, 5) for n in names])
    near = np.argmin(dist, 0)
    allfg = np.zeros((H, W), bool)
    for n in names:
        allfg |= objs[n] > 0.5
    out = {}
    for i, n in enumerate(names):
        bw = band[n]
        env = (dist[i] <= bw) & (near == i) & ~allfg & ~block
        taper = np.clip(1 - dist[i] / max(bw, 1), 0, 1) ** 1.2
        d = dark * env * taper
        s = 1 - C.blur(d, 1.2)
        s[~C.dil(env, 2) | allfg] = 1
        out[n] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
    return out


# ---------------------------------------------------------------------------------------------------------------- p1: the wall group
SHELF = dict(X=(-1.60, 0.20), Y=(17.66, 17.90), Z=(1.46, 1.50))     # 180 x 24 x 4, under the art; the camera (Z 1.05) sees its front and underside
FRAME_EDGES = {   # measured on the locked edit (row / column means of L*, the strongest steps): outer left, top, inner left/top/right/bottom
    "framed-art": dict(outer=(1082.5, 94.5), inner=(1096.5, 108.5, 1348.5, 459.0)),
    "framed-art-2": dict(outer=(1391.5, 302.5), inner=(1406.5, 315.0, 1606.5, 461.0))}
VASE_R_EDIT = [   # the edit's white vase, per row: (y, left, right), from the L* / b* steps (the lit side is weak: b* settles it)
    (299, 1716, 1738), (308, 1714, 1740), (312, 1690, 1765), (316, 1676.5, 1779), (324, 1668.5, 1786), (332, 1664.5, 1789), (340, 1662.5, 1790),
    (348, 1661.5, 1791), (356, 1662.5, 1789), (364, 1663.5, 1787), (372, 1666.5, 1785), (380, 1668.5, 1780.5), (388, 1673.5, 1777),
    (396, 1677, 1773), (404, 1681, 1769), (412, 1684.5, 1765.5), (420, 1688.5, 1763), (428, 1692, 1760), (436, 1694.5, 1757),
    (444, 1696.5, 1755), (452, 1698, 1753), (460, 1700, 1751), (464, 1700.5, 1750.5)]
PLUM_SKU = [   # white plum M (22.6 x 33): the SKU photo's outline, width per row of 418 (lip to foot), GrabCut on the listing photo
    (0, 2), (2, 7), (4, 48), (8, 54), (14, 56), (18, 60), (20, 68), (22, 82), (24, 92), (26, 125), (28, 150), (30, 168), (32, 191), (34, 206),
    (36, 220), (38, 229), (40, 237), (44, 248), (48, 258), (63, 274), (84, 285), (105, 291), (125, 290), (146, 282), (167, 266), (188, 247),
    (209, 225), (230, 202), (251, 183), (272, 163), (293, 145), (314, 131), (334, 120), (355, 110), (376, 101), (397, 96), (418, 89)]
SHELF_Y = 463.0                                           # the shelf's front top edge: every object on it ends here (the shelf hides its foot)


def poly_alpha(pts, ss=4):
    """an anti-aliased polygon (4x supersampled)"""
    m = np.zeros((H * ss, W * ss), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts) * ss).astype(np.int32)], 255)
    return cv2.resize(m.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_AREA).astype(np.float64)


def rect_alpha(x0, y0, x1, y1):
    xs, ys = np.arange(W) + 0.5, np.arange(H) + 0.5
    ax = np.clip(np.minimum(xs - x0, x1 - xs) + 0.5, 0, 1)
    ay = np.clip(np.minimum(ys - y0, y1 - ys) + 0.5, 0, 1)
    return ay[:, None] * ax[None, :]


def above_shelf():
    ys = np.arange(H) + 0.5
    return np.clip(SHELF_Y - ys + 0.5, 0, 1)[:, None] * np.ones((1, W))


def shelf_alpha():
    (X0, X1), (Yb, Yf), (Z0, Z1) = SHELF["X"], SHELF["Y"], SHELF["Z"]
    front = [proj(X0, Yf, Z1), proj(X1, Yf, Z1), proj(X1, Yf, Z0), proj(X0, Yf, Z0)]
    under = [proj(X0, Yf, Z0), proj(X1, Yf, Z0), proj(X1, Yb, Z0), proj(X0, Yb, Z0)]
    return np.maximum(poly_alpha(front), poly_alpha(under)), dict(front=[[round(a, 1) for a in p] for p in front], underside=[[round(a, 1) for a in p] for p in under])


def p1(e, ref, rec):
    out, old = {}, {}
    r = {}
    # the shelf: its own box, projected
    a, geo = shelf_alpha()
    out["wall-shelf"] = (e, a)
    old["wall-shelf"] = a > 0.5
    r["wall-shelf"] = dict(geometry=geo, note="the box from the slot (X -1.60..0.20, Y 17.66..17.90, Z 1.46..1.50); the edit's shelf sits on it within 1 px")
    # the frames: rectangles from the edit's own edges; the moulding's lower part hides behind the shelf (the camera is below it)
    for s, fe in FRAME_EDGES.items():
        ox, oy = fe["outer"]
        ix0, iy0, ix1, iy1 = fe["inner"]
        mw = ix0 - ox
        a = rect_alpha(ox, oy, ix1 + mw, H) * above_shelf()
        out[s] = (e, a)
        old[s] = a > 0.5
        r[s] = dict(outer=[ox, oy, ix1 + mw, SHELF_Y], canvas=[ix0, iy0, ix1, iy1], moulding_px=mw)
    # the charcoal vase and its dry branch: the edit's, 1.08 x about the foot (the card: 22 x 32 is 115 x 167 px here; the edit drew 102 x 152)
    lab = C.to_lab(e)
    L = lab[..., 0]
    zone = C.box_mask([(934, 300, 1056, 466)])
    d = np.linalg.norm(C.blur(lab, 1.0) - C.blur(C.to_lab(ref), 1.0), axis=-1)
    gc = C.gc_cut(e, C.ero((d > 22) & zone, 2), (d > 9) & zone, zone, zone & ~C.ero(zone, 3), iters=8)
    dark = largest((C.blur(L, 0.7) < 50) & zone)
    xs = np.nonzero(dark)[1]
    axis = 0.5 * (np.percentile(xs, 0.5) + np.percentile(xs, 99.5))
    right = np.zeros((H, W), bool)
    for y in range(300, 466):
        row = np.nonzero(dark[y])[0]
        if row.size:
            right[y, :row.max() + 2] = True
    vl = fill_holes(gc & right) & zone
    vl &= np.arange(H)[:, None] < SHELF_Y
    br = C.box_mask([(866, 88, 1125, 318)])
    bg = cv2.medianBlur(np.clip(L * 2.55, 0, 255).astype(np.uint8), 21).astype(np.float64) / 2.55
    depth = bg - C.blur(L, 0.6)
    thin = largest(C.dil((depth > 9) & br, 1) | C.dil(vl, 1)) & (br | vl)
    a_br = np.clip((depth - 3) / 22, 0, 1) * C.dil(thin, 1) * br * ~vl
    core = C.ero(thin & br, 0) & (depth > 18)
    col_br = np.median(e[core], 0) if core.any() else np.array([0.25, 0.2, 0.17])
    a_vl = C.soft(vl)
    rgb_vl = C.defringe(e, vl)
    rgb = np.where((a_br > a_vl)[..., None], col_br, rgb_vl)
    a = np.maximum(a_vl, a_br)
    M = scale_about(1.08, 1.08, axis, SHELF_Y)
    rgb2, a2 = warp_layer(rgb, a, M)
    a2 *= above_shelf()
    out["shelf-vase-left"] = (rgb2, a2)
    old["shelf-vase-left"] = (a > 0.5)
    r["shelf-vase-left"] = dict(scale=1.08, about=[round(float(axis), 1), SHELF_Y], edit_px=[int(np.ptp(np.nonzero(vl)[1])) + 1, int(SHELF_Y - np.nonzero(vl)[0].min())],
                                branch="the edit's branch: alpha from its depth under the local median L* (median 21 px), its core colour")
    # the white plum vase: the SKU outline (card 22.6 x 33 = 118 x 173 px at Y 17.78), the edit's surface mapped across each row
    yt = proj(0, 17.78, 1.83)[1]
    hpx = proj(0, 17.78, 1.50)[1] - yt
    wmax = 0.226 * F_ / (21.05 - 17.78)
    sk = np.array(PLUM_SKU, float)
    ax_t = 1726.25
    ev = np.array(VASE_R_EDIT, float)
    ys = np.arange(H)
    f = (ys + 0.5 - yt) / hpx
    hw_t = np.interp(f * 418, sk[:, 0], sk[:, 1]) / sk[:, 1].max() * wmax / 2
    valid = (f >= 0) & (ys + 0.5 < SHELF_Y + 0.5)
    le, ri = np.interp(ys + 0.5, ev[:, 0], ev[:, 1]), np.interp(ys + 0.5, ev[:, 0], ev[:, 2])
    ce, hw_e = (le + ri) / 2, (ri - le) / 2
    xx = np.arange(W) + 0.5
    mapx = np.zeros((H, W), np.float32)
    mapy = np.repeat((ys.astype(np.float32))[:, None], W, 1)
    u = (xx[None, :] - ax_t) / np.maximum(hw_t[:, None], 1e-3)
    mapx[:] = (ce[:, None] + np.clip(u, -1, 1) * hw_e[:, None] * 0.955 - 0.5).astype(np.float32)
    rgb_r = cv2.remap(e.astype(np.float32), mapx, mapy, cv2.INTER_LINEAR).astype(np.float64)
    a_r = np.clip(hw_t[:, None] - np.abs(xx[None, :] - ax_t) + 0.5, 0, 1) * valid[:, None]
    a_r *= np.clip((ys + 0.5 - yt) + 0.5, 0, 1)[:, None]
    a_r *= above_shelf()
    sl = C.box_mask([(1600, 280, 1850, 470)])
    a_r *= sl
    out["shelf-vase-right"] = (rgb_r, a_r)
    old_r = np.zeros((H, W), bool)
    for y in range(299, 464):
        old_r[y, int(round(le[y])):int(round(ri[y]))] = True
    old["shelf-vase-right"] = old_r
    r["shelf-vase-right"] = dict(outline="SKU (GrabCut of the listing photo, 37 rows), scaled to 118 x 173 px; the edit's surface remapped across each row",
                                 top_y=round(yt, 1), height_px=round(hpx, 1), max_width_px=round(wmax, 1),
                                 edit_vs_card_width_at_f=dict((str(t), round(float(np.interp(yt + t * hpx, ev[:, 0], ev[:, 2] - ev[:, 1]) /
                                                                                  (np.interp(t * 418, sk[:, 0], sk[:, 1]) / sk[:, 1].max() * wmax)), 2)) for t in (0.25, 0.5, 0.7, 0.9)))
    return out, old, r


# ---------------------------------------------------------------------------------------------------------------- p2: the right corner
POT = dict(X=1.45, Y=17.88, H=0.355, R=0.21, R_IN=0.1775, SOIL=0.325, sku="6bde6ef7_564d83ce-d066-4da9-ab34-952570829362.jpg",
           sku_rect=(90, 130, 565, 520), lab=(64.0, 2.5, 9.5))
CROWN = dict(s=0.70, about=(2455.0, 600.0), split_y=770)      # the ficus crown scaled about a point inside the lamp shade
LAMP_BULB = (0.95, 18.25, 1.42)


def sku_pot():
    img = cv2.imread(PICKS + POT["sku"])
    m = np.zeros(img.shape[:2], np.uint8)
    b, g = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, m, POT["sku_rect"], b, g, 8, cv2.GC_INIT_WITH_RECT)
    fg = largest((m == 1) | (m == 3))
    ys = np.nonzero(fg.any(1))[0]
    rows = np.array([(np.nonzero(fg[y])[0].min(), np.nonzero(fg[y])[0].max() + 1) for y in ys], float)
    rgb = img[..., ::-1].astype(np.float64) / 255
    Ly = C.luma(C.lin(rgb))
    det = Ly / np.maximum(C.blur(Ly, 9), 1e-4)                      # the relief and the speckles; the studio's broad light out
    return dict(y0=int(ys[0]), rows=rows, det=np.clip(det, 0.25, 2.2))


def pot_profile(sk):
    """r(z) from the listing photo: f 0.05 (the rim's front, where the full width starts) to 1 (the base) is z 0.355 to 0; the width
    scaled to the card's 42 cm at the belly; under f 0.95 the base rounds in to r 12 cm"""
    w = sk["rows"][:, 1] - sk["rows"][:, 0]
    n = len(w)
    f = (np.arange(n) + 0.5) / n
    k = 2 * POT["R"] / w.max()
    zz = np.linspace(0, POT["H"], 900)
    ff = 0.05 + (1 - zz / POT["H"]) * 0.95
    r = np.interp(ff, f, w) * k / 2
    base = ff > 0.95
    r[base] = np.interp(ff[base], [0.95, 1.0], [np.interp(0.95, f, w) * k / 2, 0.12])
    return zz, r, ff


def render_pot(sk, rec):
    """the pot by forward splatting (3x supersampled, nearest surface wins): the outer wall with the listing photo's relief and
    speckles mapped by angle and height, matte shading (the floor lamp's bulb, the window from the left, ambient), the rim, the
    inner back wall and the soil"""
    ss = 3
    zz, r, ff = pot_profile(sk)
    Xc, Yc = POT["X"], POT["Y"]
    cam = np.array([-0.70, 21.05, 1.05])
    th_view = np.arctan2(cam[1] - Yc, cam[0] - Xc)
    det, y0s, rows = sk["det"], sk["y0"], sk["rows"]
    n_rows = len(rows)
    lam = np.array(LAMP_BULB)
    win = np.array([-1.0, 0.15, 0.35]) / np.linalg.norm([-1.0, 0.15, 0.35])
    pts, cols = [], []
    th = np.linspace(-np.pi, np.pi, 2400, endpoint=False) + th_view
    dr = np.gradient(r, zz)
    for i in range(len(zz)):
        z = zz[i]
        if i % 1:
            continue
        P = np.stack([Xc + r[i] * np.cos(th), Yc + r[i] * np.sin(th), np.full_like(th, z)], -1)
        nrm = np.stack([np.cos(th), np.sin(th), np.full_like(th, -dr[i])], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        v = cam - P
        vis = (nrm * v).sum(-1) > 0
        P, nrm = P[vis], nrm[vis]
        phi = th[vis] - th_view
        u = np.sin(phi)
        fr = (ff[i] * n_rows)
        ri = int(np.clip(fr, 0, n_rows - 1))
        xl, xr = rows[ri]
        xs_ = (xl + xr) / 2 + u * (xr - xl) / 2 * 0.98
        ys_ = y0s + ri
        D = det[np.clip(int(ys_), 0, det.shape[0] - 1), np.clip(xs_.astype(int), 0, det.shape[1] - 1)]
        ll = lam - P
        dist = np.linalg.norm(ll, axis=-1)
        sh = 0.42 + 0.62 * np.clip((nrm * (ll / dist[:, None])).sum(-1), 0, 1) * (1.0 / (1 + (dist / 1.2) ** 2)) * 1.8 + 0.28 * np.clip(nrm @ win, 0, 1)
        sh *= 1 - 0.30 * np.clip((0.06 - z) / 0.06, 0, 1)                  # the floor's occlusion near the base
        pts.append(P)
        cols.append(np.stack([sh * D, np.zeros_like(sh)], -1))
    # the rim top (annulus), the inner back wall, the soil
    tt = np.linspace(-np.pi, np.pi, 3000, endpoint=False)
    for rr in np.linspace(POT["R_IN"], r[-1], 4):
        P = np.stack([Xc + rr * np.cos(tt), Yc + rr * np.sin(tt), np.full_like(tt, POT["H"])], -1)
        pts.append(P)
        cols.append(np.stack([np.full_like(tt, 1.08), np.full_like(tt, 1.0)], -1))
    for z in np.linspace(POT["SOIL"], POT["H"], 70):
        P = np.stack([Xc + POT["R_IN"] * np.cos(tt), Yc + POT["R_IN"] * np.sin(tt), np.full_like(tt, z)], -1)
        nrm = np.stack([-np.cos(tt), -np.sin(tt), np.zeros_like(tt)], -1)
        vis = (nrm * (cam - P)).sum(-1) > 0
        pts.append(P[vis])
        cols.append(np.stack([np.full(vis.sum(), 0.45 + 0.15 * (z - POT["SOIL"]) / (POT["H"] - POT["SOIL"])), np.full(vis.sum(), 2.0)], -1))
    rng = np.random.default_rng(7)
    for rr in np.linspace(0, POT["R_IN"], 60):
        P = np.stack([Xc + rr * np.cos(tt), Yc + rr * np.sin(tt), np.full_like(tt, POT["SOIL"])], -1)
        pts.append(P)
        cols.append(np.stack([0.75 + 0.35 * rng.random(len(tt)), np.full_like(tt, 3.0)], -1))
    P = np.concatenate(pts)
    V = np.concatenate(cols)
    d = 21.05 - P[:, 1]
    x = (CX_ + F_ * (P[:, 0] + 0.70) / d) * ss
    y = (HZ_ + F_ * (1.05 - P[:, 2]) / d) * ss
    depth = np.linalg.norm(P - cam, axis=1)
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    x0, y0 = xi.min() - 2, yi.min() - 2
    w, h = xi.max() - x0 + 3, yi.max() - y0 + 3
    idx = (yi - y0) * w + (xi - x0)
    order = np.lexsort((depth, idx))
    first = np.ones(len(order), bool)
    first[1:] = idx[order][1:] != idx[order][:-1]
    sel = order[first]
    val = np.zeros((h * w, 2))
    cov = np.zeros(h * w, bool)
    val[idx[sel]] = V[sel]
    cov[idx[sel]] = True
    val = val.reshape(h, w, 2)
    cov = cov.reshape(h, w)
    holes = ~cov & C.ero(cv2.morphologyEx(cov.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2)).astype(bool), 0)
    if holes.any():
        for c in range(2):
            num = cv2.blur((val[..., c] * cov).astype(np.float32), (5, 5))
            den = cv2.blur(cov.astype(np.float32), (5, 5))
            val[..., c][holes] = (num / np.maximum(den, 1e-6))[holes]
        val[..., 1][holes] = np.round(val[..., 1][holes])
        cov |= holes
    # colours: the outer wall in the card's colour (lightness set by the shading x relief), the rim a touch lighter, the inner wall in
    # its own shade, the soil a dark peat
    base = np.array(POT["lab"])
    sh = val[..., 0]
    kind = np.round(val[..., 1]).astype(int)
    lin_base = C.lin(C.from_lab(base[None, None, :]))[0, 0]
    Lw = C.luma(lin_base[None, :])[0]
    rgb_lin = np.zeros((h, w, 3))
    outer = kind == 0
    med = np.median(sh[outer & cov])
    rgb_lin[outer] = lin_base * (sh[outer] / med)[:, None]
    rgb_lin[kind == 1] = lin_base * 1.10
    rgb_lin[kind == 2] = lin_base * sh[kind == 2][:, None]
    soil = C.lin(C.from_lab(np.array([[[30.0, 4.0, 8.0]]])))[0, 0]
    rgb_lin[kind == 3] = soil * sh[kind == 3][:, None]
    rgb_lin *= cov[..., None]
    a_hi = cov.astype(np.float32)
    pm = cv2.resize((rgb_lin * a_hi[..., None]).astype(np.float32), None, fx=1 / ss, fy=1 / ss, interpolation=cv2.INTER_AREA)
    a_lo = cv2.resize(a_hi, None, fx=1 / ss, fy=1 / ss, interpolation=cv2.INTER_AREA)
    rgb_lo = C.srgb(np.clip(pm / np.maximum(a_lo[..., None], 1e-6), 0, 1))
    ox, oy = x0 // ss, y0 // ss
    rgb_full = np.zeros((H, W, 3))
    a_full = np.zeros((H, W))
    hh, ww = a_lo.shape
    ys_, xs_ = slice(oy, min(H, oy + hh)), slice(ox, min(W, ox + ww))
    rgb_full[ys_, xs_] = rgb_lo[:ys_.stop - oy, :xs_.stop - ox]
    a_full[ys_, xs_] = a_lo[:ys_.stop - oy, :xs_.stop - ox]
    yy, xx = np.nonzero(a_full > 0.5)
    rec["planter_pot"] = dict(method="lathe from the listing photo's outline (GrabCut), the card's 42 x 35.5 cm, splatted 3x; relief and speckles from the photo",
                              centre_XY=[Xc, Yc], bbox=[int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1],
                              colour_lab=list(POT["lab"]), median_L=round(float(np.median(C.to_lab(rgb_full[a_full > 0.9])[:, 0])), 1))
    return rgb_full, a_full


def layer_alpha(slot, man):
    l = [x for x in man["layers"] if x["slot"] == slot][0]
    return np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3].astype(np.float64) / 255


def p2(e, ref, man, rec):
    out, old, r = {}, {}, {}
    lab = C.to_lab(e)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    lamp = layer_alpha("floor-lamp", man) > 0.02
    bed = layer_alpha("bedding", man) > 0.5
    # the magazine holder: GrabCut, seeded by its black tube, its cognac straps and the white magazines
    hz = C.box_mask([(2372, 1168, 2676, 1478)])
    chroma, hue = np.hypot(A, B), np.degrees(np.arctan2(B, A)) % 360
    tube = (L < 24) & hz
    strap = (chroma > 30) & (hue > 40) & (hue < 75) & (L > 30) & (L < 70) & hz
    mags = (L > 82) & (chroma < 10) & C.box_mask([(2470, 1205, 2640, 1420)])
    sure = C.ero(tube, 1) | C.ero(strap, 2) | C.ero(mags, 2)
    hard = (hz & ~C.ero(hz, 3)) | (lamp & hz) | bed
    holder = C.gc_cut(e, sure, C.dil(sure, 6) & hz, hz, hard, iters=10)
    holder = fill_holes(holder, 400) & hz & ~bed
    out["magazine-holder"] = (C.defringe(e, holder), C.soft(holder))
    old["magazine-holder"] = holder
    ys, xs = np.nonzero(holder)
    r["magazine-holder"] = dict(source="the edit's holder as drawn (its 3/4 view: 265 px wide at the floor 1440-1465; the card's 35 x 19 x 27.5 cm in this view is about 267 x 262 px)",
                                bbox=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    # the ficus: leaves (green) and the pale trunk, never the lamp
    cz = C.box_mask([(2200, 150, 2720, 1075)])
    green = (A < -4) & (L < 72) & cz & ~lamp
    wall = (L > 74) & (A > 0) & (B > 6) & cz
    sure = C.ero(green, 2)
    trunk_zone = C.box_mask([(2480, 640, 2580, 1072)])
    trunk = trunk_zone & (B < 7.5) & (L > 55) & (L < 86) & ~green
    trunk = largest(cv2.morphologyEx(trunk.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)) if trunk.any() else trunk
    crown = C.gc_cut(e, sure | C.ero(trunk, 1), (C.dil(green, 4) | C.dil(trunk, 2)) & cz, cz, (cz & ~C.ero(cz, 3)) | lamp | C.ero(wall, 1), iters=8)
    crown &= ~lamp
    old_plant = crown.copy()
    # leaves that cross behind the pole: carried across it, row by row
    pole = C.box_mask([(2320, 612, 2345, 780)])
    rgb_p = e.copy()
    a_p = crown.astype(np.float64)
    for y in range(612, 780):
        l_, r_ = 2318, 2347
        if crown[y, l_] and crown[y, r_]:
            t = np.linspace(0, 1, r_ - l_ + 1)[1:-1]
            a_p[y, l_ + 1:r_] = 1
            rgb_p[y, l_ + 1:r_] = (1 - t)[:, None] * e[y, l_] + t[:, None] * e[y, r_]
    a_p *= ~(lamp & ~pole)
    rgb_p = C.defringe(rgb_p, a_p > 0.5)
    a_soft = C.soft(a_p > 0.5)
    ys_t = np.nonzero(crown[CROWN["split_y"]:1075].any(1))[0]
    y_soil_e = CROWN["split_y"] + int(ys_t.max()) if ys_t.size else 1050
    crown_top = int(np.nonzero(crown.any(1))[0].min())
    s, (ax, ay) = CROWN["s"], CROWN["about"]
    Mc = scale_about(s, s, ax, ay)
    upper = np.zeros((H, W))
    upper[:CROWN["split_y"]] = 1
    upper = C.blur(upper, 1.0)
    pm = np.dstack([rgb_p * (a_soft * upper)[..., None], a_soft * upper])
    wc = cv2.warpAffine(pm.astype(np.float32), Mc.astype(np.float32), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # the bare trunk below the crown, stretched from the scaled crown down to the new pot's soil
    xs_soil, ys_soil = proj(POT["X"], POT["Y"], POT["SOIL"])
    y_top_new = ay + s * (CROWN["split_y"] - ay)
    rows_new = np.arange(int(np.floor(y_top_new)), int(np.ceil(ys_soil)) + 1)
    mapx = np.full((H, W), -10, np.float32)
    mapy = np.full((H, W), -10, np.float32)
    cols_e = {}
    for y in range(CROWN["split_y"], y_soil_e + 1):
        xx = np.nonzero(crown[y, 2440:2620])[0]
        cols_e[y] = (2440 + xx.mean()) if xx.size else None
    yk = np.array([k for k, v in cols_e.items() if v is not None], float)
    xk = np.array([cols_e[int(k)] for k in yk])
    for yn in rows_new:
        t = (yn - y_top_new) / max(ys_soil - y_top_new, 1)
        ye = CROWN["split_y"] + t * (y_soil_e - CROWN["split_y"])
        xc_e = np.interp(ye, yk, xk)
        xc_new = (ax + s * (xc_e - ax)) * (1 - t) + xs_soil * t
        xn = np.arange(int(xc_new) - 30, int(xc_new) + 31)
        mapx[yn, xn] = (xc_e + (xn - xc_new) / s).astype(np.float32)
        mapy[yn, xn] = ye
    pm2 = np.dstack([rgb_p * a_soft[..., None] * (1 - upper)[..., None], a_soft * (1 - upper)]).astype(np.float32)
    wt = cv2.remap(pm2, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    tot = wc + wt
    a_pl = np.clip(tot[..., 3], 0, 1).astype(np.float64)
    rgb_pl = np.clip(tot[..., :3] / np.maximum(tot[..., 3:4], 1e-6), 0, 1).astype(np.float64)
    # the pot, in code; the plant's trunk goes into its soil (the pot's rim in front of the trunk's foot)
    sk = sku_pot()
    rgb_pot, a_pot = render_pot(sk, r)
    yy = np.arange(H)[:, None]
    front_rim = (a_pot > 0) & (yy > ys_soil - 2)
    a_pl = np.where(front_rim & (a_pot > 0.5), 0, a_pl)
    a_out = a_pl + a_pot * (1 - a_pl)
    rgb_out = (rgb_pl * a_pl[..., None] + rgb_pot * (a_pot * (1 - a_pl))[..., None]) / np.maximum(a_out[..., None], 1e-6)
    out["planter"] = (np.clip(rgb_out, 0, 1), np.clip(a_out, 0, 1))
    old["planter"] = old_plant | (C.box_mask([(2390, 1030, 2672, 1250)]) & ~holder)
    top_new = ay + s * (crown_top - ay)
    r["planter"] = dict(plant="the edit's ficus 'Audrey': crown x %.2f about (%.0f, %.0f) (a point inside the lamp shade, so what the shade hid stays hidden); the bare trunk stretched to the new pot's soil" % (s, ax, ay),
                        crown_top_edit=crown_top, crown_top_new=round(top_new, 1), crown_top_limit_y=round(proj(POT["X"], POT["Y"], 1.75)[1], 1),
                        soil=[round(xs_soil, 1), round(ys_soil, 1)], trunk_rows_edit=[CROWN["split_y"], y_soil_e])
    return out, old, r


# ---------------------------------------------------------------------------------------------------------------- p3: the nightstand islands
PITCHER_EDIT = [(1887.5, 791.25), (1890, 788.75), (1967.5, 788.75), (1980, 791), (1988.75, 797.5), (1991, 807.5), (1990, 820), (1986, 840),
                (1982.5, 862.5), (1976.25, 880), (1972.5, 905), (1967.5, 930), (1962.5, 955), (1957.5, 972.5), (1952.5, 977.5), (1942.5, 978.75),
                (1907, 978.75), (1897, 977.5), (1892, 972.5), (1887, 955), (1886.25, 925), (1878.75, 905), (1873.75, 885), (1872.5, 862.5),
                (1875, 847.5), (1883.75, 832.5), (1897.5, 822.5), (1910, 807.5), (1901, 795)]
PITCHER_EDIT_HOLE = [(1945, 798.75), (1978.75, 798.75), (1979.5, 801), (1979.5, 852.5), (1977, 852.5), (1970, 835), (1960, 820), (1946, 807.5)]
PITCHER_SKU = [(285, 277), (290, 272), (480, 272), (510, 280), (535, 295), (540, 320), (535, 380), (525, 420), (515, 450), (510, 470), (505, 500),
               (495, 560), (480, 620), (465, 680), (445, 735), (298, 737), (295, 700), (285, 660), (270, 600), (258, 540), (252, 480), (253, 440),
               (260, 400), (275, 365), (300, 345), (330, 320), (315, 295)]
PITCHER_SKU_HOLE = [(500, 292), (515, 310), (515, 410), (502, 445), (495, 370), (470, 340), (440, 320), (430, 300)]
PITCHER = dict(sku="024df36f_bf476452-1265-4a56-97cd-190f98e87005.jpg", slot=(0.33, 17.84), top_Z=0.78, foot_Z=0.54, foot_front_Y=17.88)
DISH = dict(X=(-1.84, -1.74), Y=(17.85, 17.95), Z=(0.550, 0.568), rim_y=975.0, sku="33039093_d2de0c80-3921-4551-80a8-5817ef6af558.jpg",
            sku_face=(345, 500, 455, 640))


def poly_mask(pts, shape):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts) * 4).astype(np.int32)], 1, shift=2)
    return m.astype(bool)


def band_stats(lab, m, n=6):
    ys = np.nonzero(m.any(1))[0]
    y0, y1 = ys.min(), ys.max()
    out = []
    for i in range(n):
        a, b = y0 + (y1 - y0) * i / n, y0 + (y1 - y0) * (i + 1) / n
        mm = m.copy()
        mm[:int(a)] = False
        mm[int(np.ceil(b)):] = False
        out.append(((a + b) / 2 - y0) / (y1 - y0))
        out[-1] = (out[-1], np.median(lab[mm], 0))
    return y0, y1, out


def p3(e, ref, man, rec):
    out, old, r = {}, {}, {}
    bed = (layer_alpha("bedding", man) > 0.02) | (layer_alpha("pillowcases", man) > 0.02)
    # the pitcher: the edit's (its outline traced on the locked edit), its patina tone set to the listing photo's, band by band
    # (lightness, a*, b* medians over six height bands; the edit's own light and speckle kept, its spread x 1.25); then 0.689 x about
    # its foot: 24 cm tall is 131 px here (lip 851, foot 982), the edit drew it 190 px tall
    pm = poly_mask(PITCHER_EDIT, (H, W)) & ~poly_mask(PITCHER_EDIT_HOLE, (H, W))
    vis = pm & ~bed
    lab = C.to_lab(e)
    sk = C.load(PICKS + PITCHER["sku"])
    skm = poly_mask(PITCHER_SKU, sk.shape[:2]) & ~poly_mask(PITCHER_SKU_HOLE, sk.shape[:2])
    slab = C.to_lab(sk)
    ey0, ey1, eb = band_stats(lab, C.ero(vis, 2))
    _, _, sb = band_stats(slab, C.ero(skm, 3))
    fe = np.array([b[0] for b in eb])
    ys = np.arange(H)
    f = np.clip((ys - ey0) / (ey1 - ey0), 0, 1)
    new = lab.copy()
    for c, k in ((0, 1.25), (1, 1.0), (2, 1.0)):
        me = np.interp(f, fe, [b[1][c] for b in eb])[:, None]
        ms = np.interp(f, [b[0] for b in sb], [b[1][c] for b in sb])[:, None]
        new[..., c] = ms + (lab[..., c] - me) * k
    rgb = np.clip(C.from_lab(new), 0, 1)
    rgb = C.defringe(rgb, vis)
    a = C.soft(vis) * (~bed)
    x_axis_e = 1924.75
    tgt_top = proj(PITCHER["slot"][0], PITCHER["slot"][1], PITCHER["top_Z"])[1]
    tgt_bot = proj(PITCHER["slot"][0], PITCHER["foot_front_Y"], PITCHER["foot_Z"])[1]
    s = (tgt_bot - tgt_top) / (978.75 - 788.75)
    x_c = proj(*PITCHER["slot"], PITCHER["foot_Z"])[0] - s * ((1872.5 + 1991) / 2 - x_axis_e)
    Mp = np.array([[s, 0, x_c - s * x_axis_e], [0, s, tgt_bot - s * 978.75]])
    rgb2, a2 = warp_layer(rgb, a, Mp)
    out["bedside-carafe"] = (rgb2, a2)
    old["bedside-carafe"] = pm
    r["bedside-carafe"] = dict(scale=round(s, 3), lip_y=round(tgt_top, 1), foot_y=round(tgt_bot, 1), body_axis_x=round(x_c, 1),
                               tone=dict(edit_bands_Lab=[[round(float(v), 1) for v in b[1]] for b in eb], sku_bands_Lab=[[round(float(v), 1) for v in b[1]] for b in sb]),
                               note="the edit's outline traced (its foot behind the pillow mirrored from the right); the patina: the listing photo's band tones, the edit's speckle and light")
    r["_pitcher_M"] = Mp.tolist()
    # the dish: a rough-edged travertine slab, 10 x 10 x 1.8 cm, in code (the edit drew a book): its top face from the camera and the
    # card, the listing photo's stone face as its texture, lit like the tray under the sconce; the tray's front rim hides its foot
    (X0, X1), (Yb, Yf), (Z0, Z1) = DISH["X"], DISH["Y"], DISH["Z"]
    top = [proj(X0, Yb, Z1), proj(X1, Yb, Z1), proj(X1, Yf, Z1), proj(X0, Yf, Z1)]
    front = [proj(X0, Yf, Z1), proj(X1, Yf, Z1), proj(X1, Yf, Z0), proj(X0, Yf, Z0)]
    rng = np.random.default_rng(11)

    def rough(pts, amp=0.6):
        pts = np.array(pts, float)
        out_ = []
        for i in range(len(pts)):
            p0, p1 = pts[i], pts[(i + 1) % len(pts)]
            for t in np.linspace(0, 1, 9, endpoint=False):
                q_ = p0 + (p1 - p0) * t
                nrm = np.array([-(p1 - p0)[1], (p1 - p0)[0]])
                nrm /= max(np.linalg.norm(nrm), 1e-6)
                out_.append(q_ + nrm * rng.normal(0, amp))
        return out_
    a_top = poly_alpha(rough(top))
    a_front = poly_alpha(rough(front)) * (1 - a_top)
    rim = np.clip(DISH["rim_y"] - (np.arange(H) + 0.5) + 0.5, 0, 1)[:, None]
    a_top *= rim
    a_front *= rim
    skd = C.load(PICKS + DISH["sku"])
    x0s, y0s, x1s, y1s = DISH["sku_face"]
    face = skd[y0s:y1s, x0s:x1s]
    fl = C.lin(face)
    det = C.luma(fl) / np.maximum(C.blur(C.luma(fl), 6), 1e-4)
    alb = np.median(C.to_lab(face).reshape(-1, 3), 0)
    ys_, xs_ = np.nonzero((a_top + a_front) > 0)
    bx0, by0, bx1, by1 = xs_.min(), ys_.min(), xs_.max() + 1, ys_.max() + 1
    tex = cv2.resize(det.astype(np.float32), (bx1 - bx0, max(2, int((by1 - by0)))), interpolation=cv2.INTER_AREA).astype(np.float64)
    tex = 1 + (tex - 1) * 1.6
    lit = np.zeros((H, W))
    lit[by0:by1, bx0:bx1] = 1.0
    alb_lin = C.lin(C.from_lab(np.array([[[alb[0], alb[1], alb[2]]]])))[0, 0]
    k_top, k_front = 1.00, 0.70
    rgb_d = np.zeros((H, W, 3))
    t_full = np.ones((H, W))
    t_full[by0:by1, bx0:bx1] = tex
    for kk, aa in ((k_top, a_top), (k_front, a_front)):
        rgb_d += (alb_lin * kk)[None, None, :] * (t_full * (aa > 0))[..., None]
    a_d = np.clip(a_top + a_front, 0, 1)
    out["trinket-dish"] = (C.srgb(np.clip(rgb_d, 0, 1)), a_d)
    old["trinket-dish"] = C.box_mask([(705, 945, 815, 982)]) & (C.blur(lab[..., 0], 1) > 0)
    r["trinket-dish"] = dict(method="code: a 10 x 10 x 1.8 cm slab (the card gives no height; the photo shows about 1.5-2), its outline roughened 0.6 px, the photo's stone face (its relief over a 6 px blur) as texture",
                             top_face=[[round(a_, 1) for a_ in p] for p in top], hidden_below_y=DISH["rim_y"], sku_face_Lab=[round(float(v), 1) for v in alb],
                             edit="the edit drew a book here: not used")
    return out, old, r


# ---------------------------------------------------------------------------------------------------------------- prints, shadows, set
PRINTS = {"framed-art": "c2511450_S0a720a638a594c2c825b3e25ece41352o.jpg", "framed-art-2": "5aff04c0_Sffd2120da3974d409909687f874b51d0k.jpg"}
CANVAS_ALBEDO = np.array([216, 200, 174]) / 255                   # the blank canvas the edit was asked for (#D8C8AE)


def set_print(rgb, e, slot, rec):
    """the flat print into the frame's canvas, cover-fit (no stretch), lit by the canvas's own light in the edit: the edit's canvas
    over the colour it was asked to be (#D8C8AE), per channel, 1.5 px blur, so the moulding's edge shadow and the wall light carry"""
    x0, y0, x1, y1 = FRAME_EDGES[slot]["inner"]
    xi0, yi0, xi1, yi1 = int(np.floor(x0)), int(np.floor(y0)), int(np.ceil(x1)), int(np.ceil(y1))
    pr = C.load(PICKS + PRINTS[slot])
    if slot == "framed-art-2":                                   # the listing shows the print on white with a margin and a drop shadow
        nonw = pr.min(2) < 0.86
        ys, xs = np.nonzero(nonw)
        pr = pr[ys.min() + 4:ys.max() - 3, xs.min() + 4:xs.max() - 3]
    cw, ch = x1 - x0, y1 - y0
    k = max(cw / pr.shape[1], ch / pr.shape[0])
    sw, sh = pr.shape[1] * k, pr.shape[0] * k
    M = np.array([[k, 0, x0 - (sw - cw) / 2], [0, k, y0 - (sh - ch) / 2]])
    pl_ = cv2.warpAffine(C.lin(pr).astype(np.float32), M.astype(np.float32), (W, H), flags=cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR)
    light = C.blur(C.lin(e), 1.5) / C.lin(CANVAS_ALBEDO)[None, None, :]
    canvas = rect_alpha(x0, y0, x1, y1)
    out = rgb.copy()
    sl = (slice(yi0, yi1), slice(xi0, xi1))
    lit = C.srgb(np.clip(pl_[sl] * light[sl], 0, 1))
    out[sl] = lit * canvas[sl][..., None] + rgb[sl] * (1 - canvas[sl][..., None])
    li = light[sl][canvas[sl] > 0.99]
    rec[slot]["print"] = dict(file=PRINTS[slot].split("_")[0] + " (listing file, scratchpad only)", file_px=list(pr.shape[1::-1]), canvas_px=[round(cw, 1), round(ch, 1)],
                              cover_scale=round(k, 4), cropped_px=[round(sw - cw, 1), round(sh - ch, 1)],
                              canvas_light_p5_p50_p95=[round(float(v), 3) for v in np.percentile(C.luma(li), [5, 50, 95])])
    return out


def shadow_maps(dark_by, objs, band, block):
    names = list(objs)
    dist = np.stack([cv2.distanceTransform((~objs[n]).astype(np.uint8), cv2.DIST_L2, 5) for n in names])
    near = np.argmin(dist, 0)
    allfg = np.zeros((H, W), bool)
    for n in names:
        allfg |= objs[n]
    out = {}
    for i, n in enumerate(names):
        bw = band[n]
        env = (dist[i] <= bw) & (near == i) & ~allfg & ~block.get(n, np.zeros((H, W), bool))
        taper = np.clip(1 - dist[i] / max(bw, 1), 0, 1) ** 1.2
        d = dark_by[n] * env * taper
        s = 1 - C.blur(d, 1.2)
        s[~C.dil(env, 2) | allfg] = 1
        out[n] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
    return out


def main():
    global JOBS
    JOBS = json.load(open(os.path.join(ST, "fb10", "jobs-fb10.json")))
    ids = np.asarray(Image.open(C.CLAY + "MB0-id.png"))
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    man["layers"] = [l for l in man["layers"] if l["slot"] not in LAYERS]
    pre = os.path.join(ST, "fb10", "lights-pre")
    os.makedirs(pre, exist_ok=True)
    for li in man["light"]:                                      # the lights as compose_defaults wrote them (FB10 takes its products off them)
        src = os.path.join(ST, li["file"])
        keep = os.path.join(pre, os.path.basename(li["file"]))
        if not os.path.exists(keep) or man.get("fb10") is None:
            Image.open(src).save(keep)
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    base = plate8.astype(np.float64) / 255                        # the approved set, recomposed from its layers (no FB10)
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        base = C.compose_one(base, np.asarray(Image.open(os.path.join(ST, l["layer"]))), np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
    for li in man["light"]:
        base = C.light_one(base, np.asarray(Image.open(os.path.join(pre, os.path.basename(li["file"])))))
    ref = base
    rec = {}
    outs, olds, edits = {}, {}, {}
    for p, fn in (("p1-wall", p1), ("p2-corner", p2), ("p3-islands", p3)):
        e = edit_of(p, ids, ref, rec)
        edits[p] = e
        o, od, r = fn(e, ref, rec) if p == "p1-wall" else fn(e, ref, man, rec)
        outs.update(o)
        olds.update(od)
        rec.update(r)
    for s in PRINTS:
        rgb, a = outs[s]
        outs[s] = (set_print(rgb, edits["p1-wall"], s, rec), a)
    # shadows: the edit's darkening round each product (filled under where the edit drew it), following the corrections
    new = {s: outs[s][1] > 0.5 for s in outs}
    dark_by, band, block = {}, {}, {}
    lamp = layer_alpha("floor-lamp", man) > 0.02
    for p, e in edits.items():
        dk = darkening(e, ref)
        olds_p = np.zeros((H, W), bool)
        for s in LAYERS:
            if LAYERS[s][0] == p:
                olds_p |= olds[s] | new[s]
        dk = fill_from(dk, ~C.dil(olds_p, 1), C.dil(olds_p, 1))
        for s in LAYERS:
            if LAYERS[s][0] == p:
                dark_by[s] = dk
    dark_by["bedside-carafe"] = cv2.warpAffine(dark_by["bedside-carafe"].astype(np.float32), np.array(rec.pop("_pitcher_M"), np.float32), (W, H)).astype(np.float64)
    cr = np.zeros((H, W))
    sx, (ax, ay) = CROWN["s"], CROWN["about"]
    crw = cv2.warpAffine(dark_by["planter"].astype(np.float32), scale_about(sx, sx, ax, ay).astype(np.float32), (W, H), borderMode=cv2.BORDER_REFLECT).astype(np.float64)
    yy = np.arange(H)[:, None] * np.ones((1, W))
    dark_by["planter"] = np.where(yy < ay + sx * (CROWN["split_y"] - ay), crw, dark_by["planter"])
    xd, yd = proj(-1.79, 17.95, 0.55)
    dish_dark = np.zeros((H, W))
    dd = C.dil(new["trinket-dish"], 3) & ~new["trinket-dish"]
    dish_dark[dd] = 0.22
    dark_by["trinket-dish"] = C.blur(dish_dark, 1.0)
    for s in LAYERS:
        band[s] = {"wall-shelf": 45, "planter": 40, "magazine-holder": 30}.get(s, 22)
    block["magazine-holder"] = lamp
    block["bedside-carafe"] = layer_alpha("candle-holders", man) > 0.02
    shadows = shadow_maps(dark_by, new, band, block)
    # write the layers
    a_new = np.zeros((H, W))
    for s, (rgb, a) in outs.items():
        p, z, pid, sold = LAYERS[s]
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        lp = os.path.join(ST, "layers", s, pid + ".png")
        sp = os.path.join(ST, "shadows", s, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp)
        s8 = C.q(shadows[s])
        Image.fromarray(s8).save(sp)
        ys, xs = np.nonzero(a8 > 0)
        man["layers"].append(dict(slot=s, product=pid, z=z, default=True, layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sp, ST), shadow_z=z - 1,
                                  alpha_px=int((a8 > 0).sum()), shadow_px=int((s8 < 255).sum()),
                                  bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], sold=sold, fixed=not sold,
                                  source="FB10 %s: nano-banana-2 edit, cut and corrected in code (fb10_compose.py)" % p if s != "trinket-dish" else "FB10 p3: in code (fb10_compose.py)"))
        a_new = 1 - (1 - a_new) * (1 - a8 / 255)
    order = {s: i for i, s in enumerate(["nightstand-vase", "candle-holders", "bedside-carafe", "trinket-dish"])}
    man["layers"].sort(key=lambda l: (l["z"], order.get(l["slot"], -1)))
    for li in man["light"]:
        L0 = np.asarray(Image.open(os.path.join(pre, os.path.basename(li["file"])))).astype(np.float64)
        Image.fromarray(np.clip(np.rint(L0 * (1 - a_new)[..., None]), 0, 255).astype(np.uint8)).save(os.path.join(ST, li["file"]))
    man["fb10"] = dict(date="2026-11-18", slots=list(LAYERS), lights_pre="fb10/lights-pre/", tool="tools/fb10_compose.py")
    # recompose from the layer files
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    for l in man["layers"]:
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
        region |= (rgba[..., 3] > 0) | (s8 < 255)
    for li in man["light"]:
        L8 = np.asarray(Image.open(os.path.join(ST, li["file"])))
        out = C.light_one(out, L8)
        region |= L8.max(2) > 0
    o8 = C.q(out)
    Image.fromarray(o8).save(os.path.join(ST, "mb0-defaults.png"))
    x0, y0, x1, y1 = C.FRAME
    Image.fromarray(o8).crop((int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, "mb0-defaults-frame.png"))
    diff = np.abs(o8.astype(int) - plate8.astype(int)).max(2)
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=int((diff[~region] > 0).sum()),
                       rule="outside every alpha, shadow and light: plate.png, pixel for pixel")
    newreg = np.zeros((H, W), bool)
    for s in LAYERS:
        l = [x for x in man["layers"] if x["slot"] == s][0]
        newreg |= (np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0) | (np.asarray(Image.open(os.path.join(ST, l["shadow"]))) < 255)
    ch = np.abs(o8.astype(int) - C.q(ref).astype(int)).max(2) > 0
    rec["changed_vs_round9_outside_new_layers_px"] = int((ch & ~newreg).sum())
    rec["changed_vs_round9_px"] = int(ch.sum())
    lab = C.to_lab(o8.astype(np.float64) / 255)
    fr = np.zeros((H, W), bool)
    fr[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = True
    rec["black_point_p0_5_L"] = round(float(np.percentile(lab[..., 0][fr], 0.5)), 2)
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    json.dump(rec, open(os.path.join(ST, "fb10", "fb10-compose.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps(man["rnd2"]), rec["changed_vs_round9_outside_new_layers_px"], rec["black_point_p0_5_L"])


if __name__ == "__main__":
    main()
