#!/usr/bin/env python3
"""
compose_defaults.py: B2 with the defaults (output 2), its layers, and the mask-edit variants (render-agent, 2026-11-18). 0 tokens.
Version 2 (2026-11-18): the cut by plain difference (v1) failed on this render: the model re-lit the whole room (window patches on
the left wall, a darker wall by the ring), so "the render differs from the plate" was not "product". v2 segments the products:
  1. lock: the render's lines against the input's (tools/lock_b2.py, the clay's named lines), one global warp (y about the horizon,
     x constant), as the plate. An edit (the sprig fix, a towel variant) is locked the same way on its own.
  2. tone match: a smooth gain field (normalised blur, sigma 60 px, per channel, linear light) of base / render, measured outside
     every product zone, shadow band and light envelope, applied to the render: the products sit in the plate's exposure.
  3. per slot, the alpha: GrabCut (OpenCV, 6 iterations) on the matched render, inside the slot's zone (the clay mask grown by its
     margin). Sure product: the clay core (eroded 4 px) where the render changed (dE76 over 9), plus the slot's colour prior (the
     pothos green, the caramel, the black of the ring, the vase and the pumps); probable product: the clay grown 2 px; sure
     background: outside the zone and the other slots' clay. Only components touching the sure product; holes under 150 px filled;
     a 0.8 px soft edge.
  4. per slot, the shadow (grey multiply on the sRGB values, as the engine does): the render's darkening of the plate (luma ratio,
     blurred 3 px, under 3 % ignored) inside an envelope: a contact rim round the product, plus the clay's own shadow (Cycles,
     B2 / B2-plate local ratio under 0.97) grown 8 px, within the slot's band; feathered 4 px; never on a product.
  5. the light of the sconce pair (screen, z 90): where the render is brighter than the stack (L = 1 - (1 - render) / (1 - stack),
     blurred 2 px, a floor of 0.01), only inside the clay's beam envelope (local ratio over 1.05, on the plaster and the stone top,
     grown 20 px, feathered 10 px), never on a product or the mirror. The light that falls on a product is in its own layer.
  6. the composite: ungraded, then the WM-G1 curve (plate-grade.json) pointwise: product RGB = curve(render); the grey shadow in
     the graded files = mean(curve(below x s)) / mean(curve(below)); the light solved again on the graded stack. The files are
     8-bit, the graded stack starts from plate.png's bytes, and the defaults are recomposed from the files (what the engine does).
     Outside every alpha, shadow and light: plate.png, pixel for pixel (RND2).
Recolour mode (a colour variant of the same card): the default's alpha and shadow are kept byte for byte; the RGB is the default's
fabric recoloured (lightness by the two SKU photos' luminance ratio, a* and b* as the edit render drew the new colour in this
place). The edit render is a colour reference only: the model changed the drape, and rejection 11 wants the folds and the hem
identical in every variant. The other layers and the light are read from the defaults run's files, untouched.

  python3 compose_defaults.py raw/defaults-r1.png [slot=<edit.png> ...]
  python3 compose_defaults.py raw/defaults-r1.png --recolour hand-towel=raw/towel-linen-r1.jpg --colours caramel,linen \
          --pid hand-towel-aliexpress-pure-linen-towel-38x55-linen --name b2-variant-linen
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import grade_plate as G  # noqa: E402

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-2026-11-17/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath/"
HORIZON = 707.0
FRAME = G.FRAME
PLASTER, TOP, MIRROR = (1, 2, 3, 4), (23,), (17, 18)
# slot: clay ids, zone margin px, extra downward reach px, shadow band px, contact rim px, z, product id, colour prior
SLOTS = {
    "shower-dispensers": dict(ids=(41,), margin=16, trust=True, band=14, rim=6, z=14, pid="shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle", prior="pump"),
    "vanity-sconces": dict(ids=(42, 43), margin=90, trust=True, band=20, rim=12, z=14, pid="vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853", prior=None),
    "shower-curtain": dict(ids=(40,), margin=100, band=90, rim=8, z=26, pid="shower-curtain-aliexpress-linen-blend-slub-panel-200x270", prior=None),
    "floor-planter": dict(ids=(51, 52), margin=40, band=70, rim=14, z=30, pid="planter-cj-cement-ribbed-belly-beige-medium", prior="pothos"),
    "soap-dispenser": dict(ids=(44,), margin=20, trust=True, band=16, rim=8, z=46, pid="soap-dispenser-cj-sand-ribbed-ceramic-pump-bottle", prior="pump"),
    "toothbrush-cup": dict(ids=(45, 46), margin=30, trust=True, band=16, rim=8, z=46, pid="toothbrush-cup-cj-silver-travertine-cup", prior="brush"),
    "vanity-vase": dict(ids=(47, 48), margin=30, trust=True, box=(2030, 640, 2380, 950), band=16, rim=8, z=46, pid="vanity-vase-cj-matte-black-pottery-bud-vase-10", prior="vase"),
    "towel-ring": dict(ids=(49,), margin=45, band=14, rim=6, z=50, pid="towel-ring-aliexpress-1-2pcs-bathroom-towel-842335-a3", prior="black"),
    "hand-towel": dict(ids=(50,), margin=40, down=260, band=40, rim=12, z=52, pid="hand-towel-aliexpress-pure-linen-towel-38x55-caramel", prior="caramel"),
}
LIGHT_PID = "vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853"
# the model drew both travertine blocks 1.34x the SKU's 8 x 16 cm and 3-6 cm low (measured on the render: the front edges, the top
# edge and the end of the lit slot). Each block is scaled down uniformly to the clay's height (Style B, Z 1.65) about the clay
# box's centre; its beams are moved with it: the upper V by the top edge's shift, the lower V by the bottom edge's.
SCONCE_RENDER_BOX = {42: (1355, 365, 1437, 506), 43: (2272, 257, 2388, 453)}
# the bud vase (card 7 x 9.8 cm) came out 1.43x (its body 85 x 120 px against the clay's 61 x 84): scaled back about its base,
# with its sprig (from the sprig-fix edit)
VASE_RENDER_BOX = {47: (2082, 813, 2167, 933)}
# the soap dispenser and the three niche bottles (card 7.5 x 16.5 cm) came out 1.17-1.19x tall: scaled back about their base too
SOAP_RENDER_BOX = {44: (1908, 771, 1991, 924)}
BOTTLES_RENDER_BOX = {41: (949, 666, 1084, 762)}
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


def lab_of(img):
    k = id(img)
    if k not in _LAB:
        _LAB[k] = (img, G.to_lab(img))
    return _LAB[k][1]


def load(p, size=None):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64) / 255
    if size is not None and a.shape[:2] != size:
        a = cv2.resize(a.astype(np.float32), (size[1], size[0]), interpolation=cv2.INTER_LANCZOS4).astype(np.float64)
    return np.clip(a, 0, 1)


def q(x):
    return np.clip(np.rint(x * 255), 0, 255).astype(np.uint8)


def prior_mask(kind, img):
    if kind is None:
        return np.zeros(img.shape[:2], bool)
    lab = lab_of(img)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C, h = np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360
    if kind == "pothos":
        return (a < -6) & (b > 2) & (L < 70)
    if kind == "caramel":
        return (C > 12) & (a > 6) & (h > 30) & (h < 75) & (L < 60)
    if kind in ("black", "pump"):
        return (L < 22) & (C < 12)
    if kind == "brush":                                  # the bamboo handles above the cup's rim
        yy = np.arange(img.shape[0])[:, None]
        xx = np.arange(img.shape[1])[None, :]
        return (C > 14) & (h > 55) & (h < 85) & (L > 40) & (L < 80) & (yy < 835) & (xx > 1995) & (xx < 2075)
    if kind == "vase":
        return ((L < 22) & (C < 12)) | ((a < -4) & (L < 70) & (C > 5))
    raise ValueError(kind)


def lock_and_warp(path, size):
    """lock the still against the input (lock_b2.py) and warp it; returns the warped still and the warp record"""
    import compose_plate as CP
    img = load(path, size)
    stem = os.path.basename(path).rsplit(".", 1)[0]
    tmp = os.path.join(SCR, "lock-in-" + stem + ".png")
    Image.fromarray(q(img)).save(tmp)                       # the lock reads the still at the canvas size
    lp = os.path.join(SCR, "lock-" + stem + ".json")
    subprocess.run([sys.executable, os.path.join(HERE, "lock_b2.py"), tmp, os.path.join(ST, "inputs/defaults-input.png"), lp],
                   check=True, capture_output=True)
    a, b, c, used = CP.fit(json.load(open(lp)))
    H, W = size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    out = cv2.remap(img.astype(np.float32), xx + c, yy + a + b * (yy - HORIZON), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out, 0, 1).astype(np.float64), dict(file=path, y_offset_px=round(a, 3), y_scale_about_row_707=round(b, 6),
                                                       x_offset_px=round(c, 3), used=used)


def clay_local_ratio():
    """B2 / B2-plate (the clay's Cycles EXRs), blurred 3 px, divided by its own sigma-150 blur: the products' local light and shadow"""
    import prep_defaults as P
    b2, pl = P.load_exr(P.EXR + "B2.exr"), P.load_exr(P.EXR + "B2-plate.exr")
    r = blur(((b2 + 1e-4) / (pl + 1e-4)).mean(2), 3)
    return r / np.maximum(blur(r, 150), 1e-3), r


def gain_field(render, base, keep):
    """per channel, linear: blur(base * keep) / blur(render * keep), sigma 60 px (normalised convolution), clamped 0.8-1.25"""
    w = keep.astype(np.float32)
    nb = cv2.GaussianBlur(w, (0, 0), 60) + 1e-6
    g = np.ones_like(render)
    for c in range(3):
        bb = cv2.GaussianBlur((lin(base[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        rr = cv2.GaussianBlur((lin(render[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        g[..., c] = np.clip(bb / np.maximum(rr, 1e-4), 0.8, 1.25)
    return g


def gc_cut(img, sure, prob, zone, hard_bg):
    """GrabCut in the zone's box: sure = GC_FGD, prob = GC_PR_FGD, the rest of the zone GC_PR_BGD, outside and hard_bg GC_BGD"""
    H, W = zone.shape
    ys, xs = np.nonzero(zone)
    y0, y1, x0, x1 = max(0, ys.min() - 12), min(H, ys.max() + 13), max(0, xs.min() - 12), min(W, xs.max() + 13)
    sl = (slice(y0, y1), slice(x0, x1))
    z = zone[sl]
    seeds = sure[sl] & z
    m = np.full(z.shape, cv2.GC_BGD, np.uint8)
    m[z] = cv2.GC_PR_BGD
    m[z & prob[sl]] = cv2.GC_PR_FGD
    m[hard_bg[sl]] = cv2.GC_BGD
    seeds &= ~hard_bg[sl]
    m[seeds] = cv2.GC_FGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(q(img[sl])[..., ::-1].copy(), m, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg = (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)
    n, lab = cv2.connectedComponents(fg.astype(np.uint8), connectivity=8)
    keep = set(np.unique(lab[seeds & fg])) - {0}
    fg = np.isin(lab, list(keep))
    inv = (~fg).astype(np.uint8)
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    small = [i for i in range(1, n2) if stats[i, cv2.CC_STAT_AREA] < 150 and i not in border]
    fg |= np.isin(lab2, small)
    out = np.zeros((H, W), bool)
    out[sl] = fg
    return out


def defringe(rgb, fg):
    """the edge pixels take the colour of the product's own interior (normalised blur of the pixels 2 px inside), so no wall
    colour of the render rides on the cut"""
    inner = ero(fg, 2).astype(np.float64)
    w = blur(inner, 2.0)
    out = rgb.copy()
    edge = dil(fg, 2) & (inner == 0) & (w > 0.02)       # the soft edge outside the cut too
    for c in range(3):
        v = blur(rgb[..., c] * inner, 2.0) / np.maximum(w, 1e-6)
        out[..., c][edge] = v[edge]
    return out


def soft(fg):
    a = blur(fg.astype(np.float64), 0.8)
    a = np.where(ero(fg, 1), 1.0, a)
    a[~dil(fg, 2)] = 0
    return np.clip(a, 0, 1)


def shadow_of(src, base, fg, sp, clay_shadow, block):
    """block: the other products (their cut grown 1 px). Under the product's own soft edge the shadow is carried on from the
    plaster next to it (normalised blur), so no pale rim is left between a product and its shadow"""
    rat = np.clip(blur(luma(src), 3) / np.maximum(blur(luma(base), 3), 1e-4), 0, 1)
    support = dil(fg, 2)
    env = dil(fg, sp["rim"]) | (dil(fg, sp["band"]) & dil(clay_shadow, 8))
    env = cv2.morphologyEx(env.astype(np.uint8), cv2.MORPH_CLOSE, disk(4)).astype(bool) & ~block
    dist = cv2.distanceTransform((~fg).astype(np.uint8), cv2.DIST_L2, 5)
    # darker than 35 % of the plate is an object, not a shadow, except in the contact rim, where the shadow is capped at 70 %
    valid = env & ~support & ((rat > 0.35) | (dist <= sp["rim"]))
    taper = np.clip(1 - dist / max(sp["band"], 1), 0, 1) ** 1.5      # a shadow fades with the distance from the product
    dark = np.clip((1 - rat) - 0.03, 0, 0.7) * valid * taper
    w = blur(valid.astype(np.float64), 3)
    fill = blur(dark, 3) / np.maximum(w, 1e-6)
    edge = support & ~ero(fg, 3) & ~block & (w > 0.05)
    dark = np.where(edge, fill, dark)
    soft_env = np.clip(blur((env | edge).astype(np.float64), 6) * 1.6, 0, 1) * (env | edge)
    s = 1 - blur(dark * soft_env, 1.5)
    s[~dil(env | edge, 2)] = 1
    s = np.where(s > 0.996, 1.0, s)
    return np.clip(s, 0, 1)


def setup(rawp, overrides):
    base = load(os.path.join(ST, "raw/plate-ungraded-bpl1.png"))
    H, W = base.shape[:2]
    render, wr = lock_and_warp(rawp, (H, W))
    ids = np.asarray(Image.open(CLAY + "B2-id.png"))
    clay = {k: np.isin(ids, v["ids"]) for k, v in SLOTS.items()}
    zones = {}
    for k, sp in SLOTS.items():
        z = dil(clay[k], sp["margin"])
        if sp.get("down"):                               # the render's towel hangs longer than the clay's: the zone runs down
            ys, xs = np.nonzero(z)
            ext = np.zeros_like(z)
            ext[ys.min():min(H, ys.max() + sp["down"]), xs.min():xs.max() + 1] = True
            z |= ext
        if sp.get("box"):                                # the sprig fix arches further than the clay's sprig: a box round it
            x0, y0, x1, y1 = sp["box"]
            z[y0:y1, x0:x1] = True
        zones[k] = z
    cr, ra = clay_local_ratio()
    clay_prod = np.isin(ids, list(range(40, 53)))
    clay_shadow = (cr < 0.97) & ~clay_prod
    near = np.zeros((H, W), bool)                        # the beams of the pair only: a window round each lamp
    for i in (42, 43):
        ys, xs = np.nonzero(ids == i)
        near[max(0, ys.min() - 360):ys.max() + 320, max(0, xs.min() - 230):xs.max() + 230] = True
    beam = (ra > 2.4) & np.isin(ids, PLASTER + TOP) & near
    light_env = dil(beam, 50) & ~np.isin(ids, MIRROR) & near
    anyzone = np.zeros((H, W), bool)
    for k in SLOTS:
        anyzone |= dil(zones[k], SLOTS[k]["band"])
    keep = ~(anyzone | dil(light_env, 20))
    g = gain_field(render, base, keep)
    render = srgb(lin(render) * g)
    rec = dict(render=wr, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])], overrides={})
    srcs = {k: render for k in SLOTS}
    for k, op in (overrides or {}).items():
        o, wo = lock_and_warp(op, (H, W))
        go = gain_field(o, base, keep)
        srcs[k] = srgb(lin(o) * go)
        rec["overrides"][k] = dict(warp=wo, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(go, [1, 50, 99])])
    return base, ids, clay, zones, clay_shadow, light_env, srcs, rec


def curtain_span(src, clay_m):
    """the curtain panel row by row: its left and right edges are the strongest luma steps near the clay's (stone darker than
    the cream fabric), fitted with a robust line x = a + b y and a local correction of at most 5 px"""
    Y = blur(luma(src), 1.2)
    dx = np.zeros_like(Y)
    dx[:, 3:-3] = Y[:, 6:] - Y[:, :-6]
    H, W = Y.shape
    xs = np.nonzero(clay_m.any(0))[0]
    cl, cr = xs.min(), xs.max()
    rows = np.arange(H)
    det_l = cl - 92 + np.argmax(dx[:, cl - 92:cl + 23], 1)
    det_r = cr - 35 + np.argmin(dx[:, cr - 35:cr + 45], 1)
    out = []
    for det in (det_l, det_r):
        use = rows < 1400
        for _ in range(4):
            b, a = np.polyfit(rows[use], det[use], 1)
            res = det - (a + b * rows)
            use = (rows < 1400) & (np.abs(res) < 6)
        corr = np.clip(cv2.medianBlur(np.clip(res + 128, 0, 255).astype(np.uint8).reshape(-1, 1), 41).ravel().astype(float) - 128, -5, 5)
        out.append(a + b * rows + np.where(np.abs(res) < 6, corr, 0))
    left, right = out
    span = (np.arange(W)[None, :] >= np.rint(left)[:, None]) & (np.arange(W)[None, :] <= np.rint(right)[:, None])
    return span, dict(left_top=round(float(left[0]), 1), left_bottom=round(float(left[-1]), 1), right_top=round(float(right[0]), 1),
                      right_bottom=round(float(right[-1]), 1))


HEM = 1460


CUP_BODY = (2003, 845, 2051, 921)                         # the cup's body as drawn (18 px left of the clay's): its sure seeds


def alpha_for(k, src, base, clay, zones, prior_kind, info=None, extra_bg=None):
    d = np.linalg.norm(lab_of(src) - lab_of(base), axis=-1)
    hard = np.zeros(d.shape, bool) if extra_bg is None else extra_bg.copy()
    for o in SLOTS:
        if o != k and not (k == "towel-ring" and o == "hand-towel"):
            hard |= ero(clay[o], 1) & ~dil(clay[k], 3)
    if k == "towel-ring":                                # the towel hangs over the ring: its caramel is never ring
        hard |= prior_mask("caramel", src)
    if k in ("vanity-vase", "soap-dispenser", "toothbrush-cup", "vanity-sconces"):
        hard |= dil(np.isin(np.asarray(Image.open(CLAY + "B2-plate-id.png")), MIRROR), 2)   # the mirror's bronze is not the vase's black
    cm, zone = clay[k], zones[k]
    if k == "shower-curtain":
        span, rec = curtain_span(src, cm)
        if info is not None:
            info["curtain_edges"] = rec
        H = span.shape[0]
        above = np.zeros_like(span)
        above[:HEM] = True
        sure = ero(span, 8) & above
        fg = gc_cut(src, sure, span, zone & dil(span, 6), hard)
        return (span & above) | (fg & span & ~above)
    pr = prior_mask(prior_kind, src) & zone
    pr = cv2.morphologyEx(pr.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
    if k == "floor-planter":
        pot = np.isin(np.asarray(Image.open(CLAY + "B2-id.png")), (51,))
        pr |= ero(pot, 45)                                # the pot's heart: the render's pot sits up to 40 px off the clay's
    if k == "toothbrush-cup":
        body = np.zeros_like(cm)
        x0, y0, x1, y1 = CUP_BODY
        body[y0:y1, x0:x1] = True
        sure, prob = body | pr, dil(body, 8) | dil(pr, 4)
    elif SLOTS[k].get("trust"):                          # small products the model kept in their placeholder: the clay core counts
        sure, prob = (ero(cm, 3) & (d > 9)) | pr, dil(cm, 3) | dil(pr, 4)
    else:                                                # the curtain, the planter, the ring and the towel moved: their colour counts
        sure, prob = pr, dil(pr, 4)
    fg = gc_cut(src, sure, prob, zone, hard)
    if k == "hand-towel":                                # one towel: its largest piece
        n, lab, st, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
        if n > 2:
            fg = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    if k == "vanity-vase":                               # the sprig's thin stems: darker than the plaster round them, joined to a leaf
        L = lab_of(src)[..., 0]
        bg = cv2.medianBlur(np.clip(L * 2.55, 0, 255).astype(np.uint8), 15).astype(np.float64) / 2.55
        cand = (bg - L > 7) & zone & dil(fg, 25) & ~hard
        n, lab = cv2.connectedComponents((fg | cand).astype(np.uint8), connectivity=8)
        fg = np.isin(lab, list(set(np.unique(lab[fg])) - {0}))
    if k == "floor-planter":                             # the pot's lit left side is as pale as the wall: per row, the first step
        Y = blur(luma(src), 1.0)                         # darker than the wall at the canvas edge, to the cut
        lefts = {}
        for y in range(1295, 1497):
            xs = np.nonzero(fg[y, :140])[0]
            if xs.size == 0 or xs.min() <= 6:
                continue
            bgv = np.median(Y[y, 0:4])
            c = np.nonzero(Y[y, :xs.min() + 1] < bgv - 0.05)[0]
            if c.size:
                lefts[y] = (int(c.min()), int(xs.min()))
        if lefts:
            ys_ = np.array(sorted(lefts))
            l0 = np.array([lefts[y][0] for y in ys_], float)
            l0 = np.array([np.median(l0[max(0, i - 7):i + 8]) for i in range(len(l0))])
            for y, lx in zip(ys_, l0):
                fg[y, int(round(lx)):lefts[y][1]] = True
            if info is not None:
                info["planter_left_fill_rows"] = int(len(ys_))
        # the pot's own floor shadow is as dark as its shaded side: below row 1440 the cut keeps to the clay pot's outline,
        # slid onto the render's pot (the best overlap over rows 1300-1440), grown 6 px
        pot = np.isin(np.asarray(Image.open(CLAY + "B2-id.png")), (51,))
        best = (0, 0, -1)
        band = np.zeros_like(fg)
        band[1300:1440] = True
        for dx in range(-60, 21, 2):
            for dy in range(-20, 21, 2):
                sh = np.roll(np.roll(pot, dy, 0), dx, 1)
                if dx < 0:
                    sh[:, dx:] = False
                a_, b_ = sh & band, fg & band
                iou = (a_ & b_).sum() / max((a_ | b_).sum(), 1)
                if iou > best[2]:
                    best = (dx, dy, iou)
        sh = np.roll(np.roll(pot, best[1], 0), best[0], 1)
        if best[0] < 0:
            sh[:, best[0]:] = False
        low = np.zeros_like(fg)
        low[1440:] = True
        fg &= ~low | dil(sh, 6)
        if info is not None:
            info["planter_pot_slide"] = dict(dx=best[0], dy=best[1], iou=round(float(best[2]), 3))
    return fg


def compose_one(stack, rgba, s8):
    a = rgba[..., 3:4].astype(np.float64) / 255
    return np.rint((stack * 255 * s8[..., None] / 255) * (1 - a) + rgba[..., :3].astype(np.float64) * a) / 255


def light_one(stack, L8):
    return (255 - np.rint((255 - stack * 255) * (255 - L8.astype(np.float64)) / 255)) / 255


def frame_png(o8, path):
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    Image.fromarray(o8).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(path)


def main(rawp, overrides):
    base, ids, clay, zones, clay_shadow, light_env, srcs, rec = setup(rawp, overrides)
    H, W = base.shape[:2]
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    cv = lambda x: G.curve_apply(x, curve)[0]  # noqa: E731
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    rec["plate_png_vs_curve_of_base"] = dict(max=int(np.abs(q(cv(base)).astype(int) - plate8.astype(int)).max()),
                                             px=int((np.abs(q(cv(base)).astype(int) - plate8.astype(int)).max(2) > 0).sum()))
    order = sorted(SLOTS, key=lambda k: SLOTS[k]["z"])
    # the vase first: the cup and the soap keep off it, and off the long sprig the defaults render drew (replaced by the edit)
    lab_d = lab_of(srcs["shower-curtain"])
    green = (lab_d[..., 1] < -3) & (np.hypot(lab_d[..., 1], lab_d[..., 2]) > 5) & (lab_d[..., 0] < 70)
    cupbox = np.zeros((H, W), bool)
    cupbox[CUP_BODY[1] - 6:CUP_BODY[3] + 12, CUP_BODY[0] - 8:CUP_BODY[2] + 10] = True   # the cup's grey-green specks are not sprig
    old_sprig = dil(green & zones["vanity-vase"] & ~ero(clay["vanity-vase"], 2) & ~cupbox, 3)
    fg = {"vanity-vase": alpha_for("vanity-vase", srcs["vanity-vase"], base, clay, zones, "vase", rec)}
    for k in order:
        if k != "vanity-vase":
            xb = dil(fg["vanity-vase"], 2) | old_sprig if k in ("toothbrush-cup", "soap-dispenser") else None
            fg[k] = alpha_for(k, srcs[k], base, clay, zones, SLOTS[k]["prior"], rec, xb)
    render = srcs["shower-curtain"]                      # the defaults render, matched (the light is read from it)
    fg_old = fg["vanity-sconces"].copy()
    srcs["vanity-sconces"], fg["vanity-sconces"], sc_part, moves = refit(render, fg_old, ids, SCONCE_RENDER_BOX, "centre", True)
    vsrc, vfg = srcs["vanity-vase"], fg["vanity-vase"].copy()
    srcs["vanity-vase"], fg["vanity-vase"], v_part, vmoves = refit(vsrc, vfg, ids, VASE_RENDER_BOX, "bottom", False)
    ssrc, sfg = srcs["soap-dispenser"], fg["soap-dispenser"].copy()
    srcs["soap-dispenser"], fg["soap-dispenser"], s_part, smoves = refit(ssrc, sfg, ids, SOAP_RENDER_BOX, "bottom", False, 0.15)
    bsrc, bfg = srcs["shower-dispensers"], fg["shower-dispensers"].copy()
    srcs["shower-dispensers"], fg["shower-dispensers"], b_part, bmoves = refit(bsrc, bfg, ids, BOTTLES_RENDER_BOX, "bottom", False, 0.15)
    rec["sconce_fix"], rec["vase_fix"], rec["soap_fix"], rec["bottles_fix"] = moves, vmoves, smoves, bmoves
    allfg0 = np.zeros((H, W), bool)
    for k in order:
        allfg0 |= fg[k]
    srcs["hand-towel"], rec["towel_match"] = match_towel(srcs["hand-towel"], fg["hand-towel"], base, allfg0, "caramel")
    refits = {"vanity-sconces": (render, sc_part, moves), "vanity-vase": (vsrc, v_part, vmoves),
              "soap-dispenser": (ssrc, s_part, smoves), "shower-dispensers": (bsrc, b_part, bmoves)}
    alpha = {k: soft(fg[k]) for k in order}
    prod = np.zeros((H, W), bool)
    for k in order:
        prod |= alpha[k] > 0
    fgall = np.zeros((H, W), bool)
    for k in order:
        fgall |= fg[k]
    shadow = {}
    for k in order:
        oth = np.zeros((H, W), bool)
        for o in order:
            if o != k:
                oth |= fg[o]
                if o in refits:                          # where a refitted product was drawn is not a shadow of its neighbours
                    oth |= dil(refits[o][1], 3)
        if k != "vanity-vase":
            oth |= old_sprig
        if k in refits:
            so, fo, mv = refits[k]
            s0 = shadow_of(so, base, fo, SLOTS[k], clay_shadow, dil(oth, 1))
            sk = warp_dark(s0, mv, H, W)
            sk[dil(oth, 1)] = 1
            shadow[k] = np.where(sk > 0.996, 1.0, sk)
        else:
            shadow[k] = shadow_of(srcs[k], base, fg[k], SLOTS[k], clay_shadow, dil(oth, 1))
    stack_u, stack_g = base.copy(), plate8.astype(np.float64) / 255
    s_g, rgb_g = {}, {}
    for k in order:
        s = shadow[k]
        m = s < 1
        sg = np.ones((H, W))
        if m.any():
            below = stack_u[m]
            sg[m] = np.clip(cv(below * s[m][:, None]).mean(1) / np.maximum(cv(below).mean(1), 1e-4), 0, 1)
        s_g[k] = sg
        src_k = defringe(srcs[k], fg[k])
        rgb_g[k] = cv(src_k)
        a = alpha[k][..., None]
        stack_u = stack_u * s[..., None]
        stack_u = stack_u * (1 - a) + src_k * a
        stack_g = stack_g * sg[..., None]
        stack_g = stack_g * (1 - a) + rgb_g[k] * a
    oldbox = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in SCONCE_RENDER_BOX.values():
        oldbox[y0 - 2:y1 + 3, x0 - 3:x1 + 4] = True
    old = dil((fg_old & oldbox) | (prod & ~dil(fg["vanity-sconces"], 3)), 1)
    lenv0 = light_env & ~old
    Lu = np.where(lenv0[..., None] & (render > base), 1 - (1 - render) / np.maximum(1 - base, 1e-3), 0.0)
    Lu = np.clip(blur(np.clip(Lu, 0, 1), 2) - 0.01, 0, 1)
    Lu = move_beams(Lu, moves)
    lenv = light_env & ~dil(prod, 1)
    Lu = Lu * lenv[..., None]
    fe = np.clip(blur(lenv.astype(np.float64), 25) * 2, 0, 1) * lenv
    Lu = Lu * fe[..., None]
    tgt = cv(1 - (1 - stack_u) * (1 - Lu))
    Lg = np.clip(np.where(lenv[..., None], 1 - (1 - tgt) / np.maximum(1 - stack_g, 1e-3), 0.0), 0, 1)
    write_set(order, alpha, s_g, rgb_g, Lg, plate8, rec, rawp, overrides, H, W, fg)


def refit(render, fg, ids, boxes, anchor, restrict, min_frac=0.0):
    """scale a product the model drew too big back to the clay's size (uniform scale, the clay box's height): about the box
    centre onto the clay box's centre (anchor "centre": the lamps), or about the base onto the clay's centre line at the render's
    own base row (anchor "bottom": the vase stands where the model stood it, on the stone top)"""
    H, W = fg.shape
    src = render.copy()
    new = np.zeros_like(fg)
    parts = np.zeros_like(fg)
    moves = {}
    for i, (x0, y0, x1, y1) in boxes.items():
        ys, xs = np.nonzero(ids == i)
        X0, Y0, X1, Y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        s = (Y1 - Y0) / (y1 - y0)
        if anchor == "centre":
            ax, ay, AX, AY = (x0 + x1) / 2, (y0 + y1) / 2, (X0 + X1) / 2, (Y0 + Y1) / 2
        else:
            ax, ay, AX, AY = (x0 + x1) / 2, y1, (X0 + X1) / 2, y1
        M = np.float32([[s, 0, AX - s * ax], [0, s, AY - s * ay]])
        part = fg.copy()
        if restrict:                                     # the block only: no plaster of its beams
            box = np.zeros_like(fg)
            box[y0 - 2:y1 + 3, x0 - 3:x1 + 4] = True
            part &= box
        else:                                            # the vase and its sprig: the component(s) round the box
            n, lab = cv2.connectedComponents(part.astype(np.uint8), connectivity=8)
            near = np.zeros_like(fg)
            near[y0:y1, x0:x1] = True
            part = np.isin(lab, list(set(np.unique(lab[near & part])) - {0}))
            if min_frac > 0:                             # no floating crumbs (a spout tip cut off from its pump)
                n2, lab2, st2, _ = cv2.connectedComponentsWithStats(part.astype(np.uint8), connectivity=8)
                big = st2[1:, cv2.CC_STAT_AREA].max() if n2 > 1 else 0
                part = np.isin(lab2, [i for i in range(1, n2) if st2[i, cv2.CC_STAT_AREA] >= min_frac * big])
            foot = np.zeros_like(fg)                     # its contact line on the stone stays the vase's width
            foot[y1 - 18:, :x0 - 2] = True
            foot[y1 - 18:, x1 + 2:] = True
            foot[y1 + 1:, :] = True
            part &= ~foot
        parts |= part
        w = cv2.warpAffine(render.astype(np.float32), M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT).astype(np.float64)
        pm = cv2.warpAffine(part.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR) > 0.5
        ys2, xs2 = np.nonzero(pm)
        win = np.zeros_like(fg)
        win[max(0, ys2.min() - 60):ys2.max() + 60, max(0, xs2.min() - 60):xs2.max() + 60] = True
        src[win] = w[win]
        new |= pm
        nb = [int(v) for v in np.round([AX - s * (ax - x0), AY - s * (ay - y0), AX + s * (x1 - ax), AY + s * (y1 - ay)])]
        moves[i] = dict(render_box=[x0, y0, x1, y1], clay_box=[int(X0), int(Y0), int(X1), int(Y1)], scale=round(float(s), 4),
                        new_box=nb, anchor=anchor, affine=[[round(float(v), 4) for v in row] for row in M.tolist()],
                        window=[int(max(0, xs2.min() - 60)), int(max(0, ys2.min() - 60)), int(xs2.max() + 60), int(ys2.max() + 60)])
    return src, new, parts, moves


def warp_dark(s, moves, H, W):
    """a refitted product's shadow: computed round the drawn product, then moved with it"""
    dk = np.zeros((H, W))
    for m in moves.values():
        x0, y0, x1, y1 = m["render_box"]
        piece = np.zeros((H, W))
        pad = 120
        sl = (slice(max(0, y0 - pad), y1 + pad), slice(max(0, x0 - pad), x1 + pad)) if m["anchor"] == "centre" else (slice(None), slice(None))
        piece[sl] = (1 - s)[sl]
        dk = np.maximum(dk, cv2.warpAffine(piece.astype(np.float32), np.float32(m["affine"]), (W, H), flags=cv2.INTER_LINEAR))
    return 1 - dk


def move_beams(L, moves):
    """each lamp's light moves with its block: the same uniform scale about the block's centre and the same shift, so the two
    V's keep their origins on the block's top and bottom edges (the model's 1.34x lamp drew 1.34x beams)"""
    H, W = L.shape[:2]
    out = L.copy()
    for i, m in moves.items():
        x0, y0, x1, y1 = m["render_box"]
        win = (slice(max(0, y0 - 380), min(H, y1 + 340)), slice(max(0, x0 - 250), min(W, x1 + 250)))
        piece = np.zeros_like(L)
        piece[win] = L[win]
        out[win] = 0
        M = np.float32(m["affine"])
        moved = cv2.warpAffine(piece.astype(np.float32), M, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
        out = np.maximum(out, moved)
    return out


def write_set(order, alpha, s_g, rgb_g, Lg, plate8, rec, rawp, overrides, H, W, fg):
    man = dict(id="wm-bath-b2-layers-2026-11-18", room="bath", style="warm-modern", frame="B2", canvas=[W, H],
               frame_box=[round(v, 2) for v in FRAME], base="plate.png (graded, WM-G1 round 3), byte for byte",
               color="8-bit sRGB, no ICC profile; blending on the sRGB-encoded values",
               compose=dict(order=["base"] + [f"{k}-shadow, {k}" for k in order] + ["light (screen)"],
                            formula="for each product in z order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, "
                                    "straight alpha; then the light: out = 255 - round((255 - out) * (255 - L) / 255)",
                            swap_region="per product: alpha > 0 or shadow < 255; a product changes nothing outside its region"),
               grade="every layer is cut from the graded composite (plate-grade.json, round 3); the site applies no further grade",
               cut="tools/compose_defaults.py v2 (GrabCut in the slot zone, clay-bounded shadows, clay-bounded light)", layers=[])
    rec_stack = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    for k in order:
        sp = SLOTS[k]
        a8 = q(alpha[k])
        rgba = np.dstack([q(rgb_g[k]), a8])
        rgba[..., :3][a8 == 0] = 0
        s8 = q(s_g[k])
        lp = os.path.join(ST, "layers", k, sp["pid"] + ".png")
        sh = os.path.join(ST, "shadows", k, sp["pid"] + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sh), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp)
        Image.fromarray(s8).save(sh)
        rec_stack = compose_one(rec_stack, rgba, s8)
        r = (a8 > 0) | (s8 < 255)
        region |= r
        ys, xs = np.nonzero(r)
        man["layers"].append(dict(slot=k, product=sp["pid"], z=sp["z"], default=True, layer=os.path.relpath(lp, ST),
                                  shadow=os.path.relpath(sh, ST), shadow_z=sp["z"] - 1, alpha_px=int((a8 > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
        if k == "hand-towel" and "towel_match" in rec:
            man["layers"][-1]["colour_match"] = rec["towel_match"]
        if k == "vanity-sconces" and "sconce_fix" in rec:
            man["layers"][-1]["refit"] = {str(i): {x: m[x] for x in ("render_box", "clay_box", "scale", "new_box")} for i, m in rec["sconce_fix"].items()}
        for kk, rk in (("vanity-vase", "vase_fix"), ("soap-dispenser", "soap_fix"), ("shower-dispensers", "bottles_fix")):
            if k == kk and rk in rec:
                man["layers"][-1]["refit"] = {str(i): {x: m[x] for x in ("render_box", "clay_box", "scale", "new_box")} for i, m in rec[rk].items()}
    L8 = q(Lg)
    lpth = os.path.join(ST, "light", LIGHT_PID + ".png")
    os.makedirs(os.path.dirname(lpth), exist_ok=True)
    Image.fromarray(L8).save(lpth)
    out = light_one(rec_stack, L8)
    region |= L8.max(2) > 0
    man["light"] = dict(product=LIGHT_PID, file=os.path.relpath(lpth, ST), z=90, blend="screen", px=int((L8.max(2) > 0).sum()),
                        note="the beams on the plaster and the stone top only; the light that falls on a product is in that product's own layer")
    o8 = q(out)
    Image.fromarray(o8).save(os.path.join(ST, "b2-defaults.png"))
    frame_png(o8, os.path.join(ST, "b2-defaults-frame.png"))
    diff_out = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=diff_out,
                       rule="outside every alpha, shadow and light: plate.png, pixel for pixel")
    man["variants"] = []
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    rec.update(raw=rawp, edits=overrides, alpha_px={k: int((alpha[k] > 0).sum()) for k in order}, light_px=man["light"]["px"],
               rnd2=man["rnd2"])
    json.dump(rec, open(os.path.join(ST, "b2-defaults-compose.json"), "w"), indent=1)
    os.makedirs(os.path.join(SCR, "npz"), exist_ok=True)
    np.savez_compressed(os.path.join(SCR, "npz", "defaults-fg.npz"), **{k: fg[k] for k in order})
    print(json.dumps(man["rnd2"]), json.dumps(rec["gain_p1_p50_p99"]), json.dumps(rec["plate_png_vs_curve_of_base"]),
          {k: (v["warp"]["y_offset_px"], v["warp"]["x_offset_px"]) for k, v in rec["overrides"].items()})


# the two SKU photographs' mid-tone fabric (25-75 % of L* over the fabric only; the colour step of the hand-towel card, same
# fabric and size): sRGB-linear medians, measured on the reference crops (scratchpad skuref, never in the repo)
SKU_MID = {"caramel": dict(lin=[0.25415, 0.07036, 0.02519], lab=[38.71, 23.86, 28.96]),
           "linen": dict(lin=[0.52712, 0.47353, 0.43415], lab=[74.98, 2.14, 5.04])}


PLASTER_REF = (1150, 150, 1300, 300)                      # lit plaster left of the mirror (the plate's L* 85-91 field)


def albedo_lab(src, mask, plate, allfg):
    """the product's colour as if in the light of the plate's lit plaster (where the plaster reads L* 85-91, about the light of the
    SKU photographs, daylight on white): its median linear RGB over `mask` divided by the plate's light there (the plate's wall
    in a ring 45-90 px round it, over the lit plaster reference, per channel). A check for rejections 2 and 11"""
    ring = dil(mask, 90) & ~dil(mask, 45) & ~dil(allfg, 45)
    x0, y0, x1, y1 = PLASTER_REF
    ref = np.median(lin(plate[y0:y1, x0:x1]).reshape(-1, 3), 0)
    illum = np.median(lin(plate[ring]), 0) / ref
    alb = np.median(lin(src[mask]), 0) / np.maximum(illum, 1e-4)
    return G.to_lab(srgb(np.clip(alb, 0, 1))), illum


def match_towel(src, fg_t, base, allfg, colour):
    """the drawn towel's light level against the plate's light round it and its SKU: one gain on its pixels (linear), so that
    its lower half, put back under the lit plaster, has the SKU photo's mid-tone luminance"""
    ys, xs = np.nonzero(fg_t)
    lowm = fg_t.copy()
    lowm[:(ys.min() + ys.max()) // 2] = False
    lowm &= ero(fg_t, 4)
    lab0, illum = albedo_lab(src, lowm, base, allfg)
    target = SKU_MID[colour]["lab"][0]
    y_now = ((lab0[0] + 16) / 116) ** 3
    y_tgt = ((target + 16) / 116) ** 3
    g = y_tgt / y_now
    out = src.copy()
    reg = dil(fg_t, 3)
    out[reg] = srgb(lin(src[reg]) * g)
    lab1, _ = albedo_lab(out, lowm, base, allfg)
    return out, dict(gain_linear=round(float(g), 4), albedo_lab_before=[round(float(v), 2) for v in lab0],
                     albedo_lab_after=[round(float(v), 2) for v in lab1], sku_mid_lab=SKU_MID[colour]["lab"],
                     de00_after_vs_sku=round(float(G.de00(lab1[None], np.array([SKU_MID[colour]["lab"]]))[0]), 2),
                     plate_light_rgb=[round(float(v), 4) for v in illum])


def albedo_rec(src, mask, base, allfg, colour):
    lab, _ = albedo_lab(src, mask, base, allfg)
    return dict(albedo_lab=[round(float(v), 2) for v in lab], sku_mid_lab=SKU_MID[colour]["lab"],
                de00_vs_sku=round(float(G.de00(lab[None], np.array([SKU_MID[colour]["lab"]]))[0]), 2))


def recolour_variant(rawp, slot, vpath, pid, name, frm, to):
    """a colour variant of the same product: the default's own geometry (alpha, folds, hem, shadow) recoloured: its shading x the
    new SKU photo's mid-tone x the plate's light round the towel. The edit render is the in-room reference only (its drape moved)"""
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    base, ids, clay, zones, clay_shadow, light_env, srcs, rec = setup(rawp, {slot: vpath})
    H, W = base.shape[:2]
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    lay = {l["slot"]: l for l in man["layers"]}[slot]
    rgba_d = np.asarray(Image.open(os.path.join(ST, lay["layer"])))
    sh_d = np.asarray(Image.open(os.path.join(ST, lay["shadow"])))
    fg = np.load(os.path.join(SCR, "npz", "defaults-fg.npz"))[slot]
    allfg = np.zeros((H, W), bool)
    for l in man["layers"]:
        allfg |= np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0
    src0, _ = match_towel(srcs["shower-curtain"], fg, base, allfg, frm)   # the default as it went into its layer
    src = defringe(src0, fg)
    # the default's shading (its luminance over its lower half's median) x the new SKU's mid-tone x the plate's light round the
    # towel (per channel): the folds, the weave and the hem stay the default's, the colour is the new SKU's in this light
    ys, xs = np.nonzero(fg)
    lower = np.zeros_like(fg)
    lower[(ys.min() + ys.max()) // 2:, :] = True
    lowm = fg & lower & ero(fg, 4)
    Y = lin(src) @ np.array([0.2126, 0.7152, 0.0722])
    shade = Y / np.median(Y[lowm])
    inner = ero(fg, 2)
    shade = np.minimum(shade, np.percentile(shade[inner], 99.5))
    w = blur(inner.astype(np.float64), 2.0)                   # the soft edge carries the shading of the fabric next to it
    edge = dil(fg, 2) & ~inner
    shade[edge] = (blur(shade * inner, 2.0) / np.maximum(w, 1e-6))[edge]
    ring = dil(lowm, 90) & ~dil(lowm, 45) & ~dil(allfg, 45)
    x0, y0, x1, y1 = PLASTER_REF
    illum = np.median(lin(base[ring]), 0) / np.median(lin(base[y0:y1, x0:x1]).reshape(-1, 3), 0)
    app = np.array(SKU_MID[to]["lin"]) * illum
    new = srgb(np.clip(shade[..., None] * app[None, None, :], 0, 1))
    kY = float(np.dot(SKU_MID[to]["lin"], [0.2126, 0.7152, 0.0722]) / np.dot(SKU_MID[frm]["lin"], [0.2126, 0.7152, 0.0722]))
    labv, labd = lab_of(srcs[slot]), lab_of(src0)
    pick = dil(fg, 30) & zones[slot] & (np.linalg.norm(labv - lab_of(srcs["shower-curtain"]), axis=-1) > 8) & (labv[..., 1] < 8) & (labv[..., 0] > 15)
    rgb = G.curve_apply(new, curve)[0]
    a8 = rgba_d[..., 3]
    rgba = np.dstack([q(rgb), a8])
    rgba[..., :3][a8 == 0] = 0
    lp = os.path.join(ST, "layers", slot, pid + ".png")
    sh = os.path.join(ST, "shadows", slot, pid + ".png")
    Image.fromarray(rgba, "RGBA").save(lp)
    Image.fromarray(sh_d).save(sh)                            # the same geometry casts the same shadow
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    files = {l["slot"]: (np.asarray(Image.open(os.path.join(ST, l["layer"]))), np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
             for l in man["layers"]}
    files[slot] = (rgba, sh_d)
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        out = compose_one(out, *files[l["slot"]])
        region |= (files[l["slot"]][0][..., 3] > 0) | (files[l["slot"]][1] < 255)
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    out = light_one(out, L8)
    region |= L8.max(2) > 0
    o8 = q(out)
    Image.fromarray(o8).save(os.path.join(ST, name + ".png"))
    frame_png(o8, os.path.join(ST, name + "-frame.png"))
    dflt = np.asarray(Image.open(os.path.join(ST, "b2-defaults.png")).convert("RGB"))
    diff = np.abs(o8.astype(int) - dflt.astype(int)).max(2) > 0
    # checks: the in-room colour against the edit's own towel (lower half, median Lab), and an albedo estimate against the SKU
    labn = G.to_lab(new)
    lowm = fg & lower & ero(fg, 4)
    edit_low = pick & lower
    med = lambda lab, m: [round(float(np.median(lab[..., i][m])), 2) for i in range(3)]  # noqa: E731
    v = dict(slot=slot, product=pid, z=SLOTS[slot]["z"], default=False, method="recolour of the default's geometry (colour variant of "
             "the same card)", layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sh, ST), composite=name + ".png",
             alpha_identical_to_default=True, shadow_identical_to_default=True,
             kY_sku=round(kY, 4),
             kY_scene=round(float(np.median((lin(srcs[slot]) @ [0.2126, 0.7152, 0.0722])[edit_low]) / np.median(Y[lowm])), 4),
             lab_lower_half=dict(recoloured=med(labn, lowm), edit_render=med(labv, edit_low), default=med(labd, lowm)),
             de00_recoloured_vs_edit_lower_half=round(float(G.de00(np.array([med(labn, lowm)]), np.array([med(labv, edit_low)]))[0]), 2),
             albedo_check=albedo_rec(new, lowm, base, allfg, to),
             differing_px_vs_defaults=int(diff.sum()), differing_px_vs_defaults_outside_alpha=int((diff & (a8 == 0)).sum()),
             outside_differing_px_vs_plate=int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum()),
             edit_render=rec["overrides"][slot])
    man["variants"] = [x for x in man.get("variants", []) if x["product"] != pid] + [v]
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    print(json.dumps({k: v[k] for k in v if k != "edit_render"}))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--recolour" in args:
        i = args.index("--recolour")
        slot, vpath = args[i + 1].split("=", 1)
        frm, to = args[args.index("--colours") + 1].split(",")
        recolour_variant(args[0], slot, vpath, args[args.index("--pid") + 1], args[args.index("--name") + 1], frm, to)
    else:
        main(args[0], dict(a.split("=", 1) for a in args[1:]))
