#!/usr/bin/env python3
"""
compose.py: the HT2 product pass cut into layers on the approved ht2.png (RND2), render-agent 2026-11-19. 0 tokens.

Sources: r1 (nano-banana-2 4K, the wall light and the pegs) and fix1 (nano-banana-2 4K, the throw and the basket). Each model
picture is read at 4K (5504 x 3072, 2.02x the canvas) and resampled onto the canvas of base.png (2720 x 1530) with an area filter
or, where a product is refit, with a matched Gaussian prefilter and a remap.

  1. exposure: per island, the model's per-channel linear ratio to ht2.png on a ring outside every island (joints excluded); the
     island's model pixels are divided by it, so the products sit in HT2's exposure.
  2. the refits (the model drew the small wall products larger than the clay, as the bath's B1 lamp and planter):
     - wall light: r1's cylinder 63.5 x 207 px for the clay's 45 x 185 (9.2 x 31 cm for 6.5 x 28): remapped about its centre
       (sx 0.709, sy 0.894) onto the clay; above and below the cylinder, its beams follow the moved ends, and their width scale
       relaxes from sx to 1 over 120 px (the opening is narrower; the fan's spread is the model's).
     - pegs: each block, measured on r1 (walnut, L* < 52, C* > 6), mapped box to box onto the clay's block (4 x 8 x 2 at
       Y 7.27 / 7.39 / 7.51 / 7.63, Z 1.59-1.67).
     - basket and throw (fix1): drawn on their clay proxies; no refit if within 3 px (checked, reported).
  3. alpha: the wall light's = the clay silhouette (the refit lands the drawn edges on it); the pegs' = the drawn walnut,
     1 px luminance matte at the edge; the throw's and the basket's = GrabCut on the model in the island, seeded by the clay.
  4. shadows (multiply, grey, z one under the product) and light (screen, RGB, z 90): the model's smooth luminance gain over
     ht2.png's own pixels (normalised blur, the joints of both pictures and every alpha excluded), feathered to 1 at the island
     edge. The model's redrawn stone is never used: its joints moved up to ~7 px. Gains < 1 are the shadow, > 1 the light.
  5. the composite is rebuilt from the files with the manifest's formula; outside every alpha, shadow and light it is ht2.png
     byte for byte (checked).

  python3 compose.py r1 <r1.jpg>        -> SCR/stage-r1.npz (wall light and pegs)
  python3 compose.py fix1 <fix1.jpg>    -> SCR/stage-fix1.npz (throw and basket)
  python3 compose.py write              -> OUT/ht2-products.png, -frame.png, layers/, shadows/, light/, compose.json
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo as G  # noqa: E402

K = G.K
W, H = 2720, 1530
SCR = G.SCR
BASE = os.path.join(G.HALL18, "ht2.png")
Z = {"wall-sconce": 14, "wall-hooks": 16, "basket": 20, "bench-throw": 22}     # shadow at z - 1; light at 90
SC_MODEL = dict(x=(1725.0, 1788.5), y=(315.8, 523.2))     # r1's travertine cylinder, edges measured on the canvas (gradient peaks)
SC_CLAY = dict(x=(1734.5, 1779.5), y=(326.5, 511.5))      # the clay's (geo.render: travertine faces, pixel edges)
BEAM_RELAX = 120.0


def walnut(lab):
    """the drawn walnut of the pegs: the block L* 32-38 C* 23-27, the dowel's shade side L* 15-28; not the soft shadow under them
    (L* 44-64, C* 15-18), the stone (L* 73-79, C* 11-12) or its joints (thin, removed by the opening)"""
    L, C = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    return (L < 33) | ((L < 50) & (C > 20))


# ---- io --------------------------------------------------------------------------------------------------------------------------
def rgb8(p):
    return np.asarray(Image.open(p).convert("RGB"))


def island(slot):
    return np.asarray(Image.open(os.path.join(SCR, f"island-{slot}.png"))) > 0


def sconce_island():
    """the wall light's island for the compose: prep.py's (lamp + beam zone), but only above y 1000 (Z about 0.95: r1's beams are
    gone well before) and 40 px clear of every other island. prep.py's beam tail (> 0.0005) reached the bench, so without this
    r1's oversized throw would enter the light's gain as dark smudges on the stone"""
    m = island("wall-sconce")
    m[1000:] = False
    others = island("wall-hooks") | island("bench-throw") | island("basket")
    return m & ~(cv2.dilate(others.astype(np.uint8), np.ones((81, 81), np.uint8)) > 0)


def all_islands():
    m = np.zeros((H, W), bool)
    for s in G.ORDER:
        m |= island(s)
    return m


def to_canvas(m4):
    return cv2.resize(m4, (W, H), interpolation=cv2.INTER_AREA)


def k4(m4):
    return m4.shape[1] / W, m4.shape[0] / H


def lum(lin):
    return lin @ K.W709


def joints(srgb01, thr=0.018):
    """the dark thin lines of the stone (joints, pits): a black-hat of the luminance, grown 1 px"""
    y = (srgb01 @ K.W709).astype(np.float32)
    bh = cv2.morphologyEx(y, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    return cv2.dilate((bh > thr).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0


def nblur(x, w, s):
    w = w.astype(np.float32)
    nb = cv2.GaussianBlur(w, (0, 0), s) + 1e-6
    if x.ndim == 2:
        return cv2.GaussianBlur((x * w).astype(np.float32), (0, 0), s) / nb
    return np.stack([cv2.GaussianBlur((x[..., c] * w).astype(np.float32), (0, 0), s) / nb for c in range(x.shape[-1])], -1)


def exposure(model01, base01, isl, others):
    """per-channel linear ratio model / base on a ring 20-100 px outside the island, off every island and the joints"""
    ring = (cv2.dilate(isl.astype(np.uint8), np.ones((201, 201), np.uint8)) > 0) & ~(cv2.dilate(others.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0)
    ring &= ~joints(model01) & ~joints(base01)
    r = K.to_lin(model01[ring]) / np.maximum(K.to_lin(base01[ring]), 1e-4)
    return np.median(r, 0), int(ring.sum())


def remap4(m4, xs, ys, sig=(1.1, 0.95)):
    """sample the 4K model at canvas coordinates (xs, ys) with a Gaussian prefilter (anti-alias for a 2-3x reduction)"""
    kx, ky = k4(m4)
    X = (xs + 0.5) * kx - 0.5
    Y = (ys + 0.5) * ky - 0.5
    x0, x1 = int(max(0, np.floor(X.min()) - 8)), int(min(m4.shape[1], np.ceil(X.max()) + 9))
    y0, y1 = int(max(0, np.floor(Y.min()) - 8)), int(min(m4.shape[0], np.ceil(Y.max()) + 9))
    crop = cv2.GaussianBlur(m4[y0:y1, x0:x1].astype(np.float32), (0, 0), sigmaX=sig[0], sigmaY=sig[1])
    return cv2.remap(crop, (X - x0).astype(np.float32), (Y - y0).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) / 255.0


def bbox(m, pad=0):
    ys, xs = np.nonzero(m)
    return max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + 1 + pad), min(H, ys.max() + 1 + pad)


# ---- the wall light ----------------------------------------------------------------------------------------------------------
def sconce_map(xt, yt):
    cxm, cym = np.mean(SC_MODEL["x"]), np.mean(SC_MODEL["y"])
    cxc, cyc = np.mean(SC_CLAY["x"]), np.mean(SC_CLAY["y"])
    sx = (SC_CLAY["x"][1] - SC_CLAY["x"][0]) / (SC_MODEL["x"][1] - SC_MODEL["x"][0])
    sy = (SC_CLAY["y"][1] - SC_CLAY["y"][0]) / (SC_MODEL["y"][1] - SC_MODEL["y"][0])
    xs = cxm + (xt - cxc) / sx
    ys = cym + (yt - cyc) / sy
    for side in ("up", "dn"):
        if side == "up":
            h = SC_CLAY["y"][0] - yt
            sel = h > 0
            ys = np.where(sel, SC_MODEL["y"][0] - h, ys)
        else:
            h = yt - SC_CLAY["y"][1]
            sel = h > 0
            ys = np.where(sel, SC_MODEL["y"][1] + h, ys)
        s = sx + (1 - sx) * np.clip(h / BEAM_RELAX, 0, 1)
        xs = np.where(sel, cxm + (xt - cxc) / s, xs)
    return xs, ys, dict(sx=round(float(sx), 4), sy=round(float(sy), 4))


def stage_r1(path):
    m4 = rgb8(path)
    base = rgb8(BASE) / 255.0
    mc = to_canvas(m4) / 255.0
    rep = dict(source=os.path.basename(path), model_px=[int(m4.shape[1]), int(m4.shape[0])])
    allisl = all_islands()
    out = {}
    # -- the wall light
    isl = sconce_island()
    x0, y0, x1, y1 = bbox(isl)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    xs, ys, sc = sconce_map(xx, yy)
    ref = mc.copy()
    ref[y0:y1, x0:x1] = remap4(m4, xs, ys)
    e, nring = exposure(mc, base, isl, allisl & ~isl)
    ref_lin = K.to_lin(ref) / e
    a_cyl, _ = G.cylinder_alpha()
    a_blk = drawn_alpha(K.to_srgb(np.clip(ref_lin, 0, 1)), BLOCK_BOX, lambda L, C: (L < 52) & (C > 20))
    a = np.maximum(a_cyl, a_blk)
    cov_s = a > 0
    gf = gains(ref_lin, base, isl, cov_s, sigma=4.0, feather=30, grow=4)      # near the lamp: the block's soft shadow
    gs = gains(ref_lin, base, isl, cov_s, sigma=12.0, feather=30, grow=4)     # the beams: light is smooth
    dl = cv2.distanceTransform((~cov_s).astype(np.uint8), cv2.DIST_L2, 5)
    tw = np.clip((dl - 15) / 25.0, 0, 1)
    tw = (tw * tw * (3 - 2 * tw))[..., None]
    gl = gf * (1 - tw) + gs * tw
    out["wall-sconce"] = dict(rgb=K.to_srgb(np.clip(ref_lin, 0, 1)), alpha=a, gain=gl, island=isl)
    rep["wall-sconce"] = dict(refit=dict(model_edges=SC_MODEL, clay_edges=SC_CLAY, **sc, beam_relax_px=BEAM_RELAX),
                              exposure=[round(float(v), 4) for v in e], ring_px=nring, alpha_px=int((a > 0).sum()))
    # -- the pegs
    isl = island("wall-hooks")
    e, nring = exposure(mc, base, isl, allisl & ~isl)
    lab = K.lab_from_lin(K.to_lin(mc))
    rgbp = mc.copy()
    alpha = np.zeros((H, W), np.float32)
    pegs = []
    for i, y in enumerate(G.HOOK_Y):
        lo = (G.STONE_X, y - G.HOOK["w"] / 2, G.HOOK["z0"])
        hi = (G.STONE_X + G.HOOK["t"], y + G.HOOK["w"] / 2, G.HOOK["z0"] + G.HOOK["h"])
        P = np.array([[x, yy_, z] for x in (lo[0], hi[0]) for yy_ in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        px = G.polyline(P)
        cb = (float(px[:, 0].min()), float(px[:, 1].min()), float(px[:, 0].max()), float(px[:, 1].max()))
        sx0, sy0 = int(cb[0] - 30), int(cb[1] - 30)
        sx1, sy1 = int(cb[2] + 30), int(cb[3] + 40)
        wal = walnut(lab[sy0:sy1, sx0:sx1])
        wal = cv2.morphologyEx(wal.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))   # no joints (2-3 px lines)
        n, cc, st, _ = cv2.connectedComponentsWithStats(wal, 8)
        j = 1 + int(np.argmax(st[1:, 4]))
        mb = (sx0 + st[j, 0] - 0.5, sy0 + st[j, 1] - 0.5, sx0 + st[j, 0] + st[j, 2] - 0.5, sy0 + st[j, 1] + st[j, 3] - 0.5)
        cbe = (cb[0] - 0.5, cb[1] - 0.5, cb[2] + 0.5, cb[3] + 0.5)
        fx = (mb[2] - mb[0]) / (cbe[2] - cbe[0])
        fy = (mb[3] - mb[1]) / (cbe[3] - cbe[1])
        bx0, by0, bx1, by1 = int(cbe[0] - 26), int(cbe[1] - 20), int(cbe[2] + 26), int(cbe[3] + 34)
        yy, xx = np.mgrid[by0:by1, bx0:bx1].astype(np.float64)
        xs = mb[0] + (xx - cbe[0]) * fx
        ys = mb[1] + (yy - cbe[1]) * fy
        patch = remap4(m4, xs, ys, sig=(0.5 * k4(m4)[0] * fx, 0.5 * k4(m4)[1] * fy))
        rgbp[by0:by1, bx0:bx1] = patch
        pl = K.lab_from_lin(K.to_lin(patch))
        core = walnut(pl)
        core = cv2.morphologyEx(core.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n2, cc2, st2, _ = cv2.connectedComponentsWithStats(core, 8)
        j2 = 1 + int(np.argmax(st2[1:, 4]))
        core = cc2 == j2
        core = cv2.morphologyEx(core.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
        hole = cv2.floodFill((~core).astype(np.uint8).copy(), None, (0, 0), 0)[1] > 0
        core |= hole
        ls = float(np.median(pl[..., 0][~cv2.dilate(core.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)]))
        lw = float(np.percentile(pl[..., 0][core], 60))
        matte = np.clip((ls - pl[..., 0]) / max(ls - lw, 1.0), 0, 1)
        inner = cv2.erode(core.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        band = (cv2.dilate(core.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & ~inner
        matte = np.where(joints(patch), 0.0, matte)                   # the model's moved joint touching the block: not the peg
        ap = np.where(inner, 1.0, np.where(band, matte, 0.0))
        alpha[by0:by1, bx0:bx1] = np.maximum(alpha[by0:by1, bx0:bx1], ap)
        pegs.append(dict(i=i, Y=y, clay_block_px=[round(v, 1) for v in cbe], model_block_px=[round(v, 1) for v in mb],
                         scale_drawn_over_clay=[round(fx, 3), round(fy, 3)], stone_L=round(ls, 1), walnut_L60=round(lw, 1),
                         alpha_px=int((ap > 0).sum())))
    cov_h = alpha > 0
    rl = K.to_lin(rgbp) / e
    gm = gains(rl, base, isl, cov_h, sigma=2.5, feather=14)           # the model's own shading: only to calibrate the drop shadow
    gl, cal = peg_shadow(alpha, gm, pegs)
    rep_cal = cal
    out["wall-hooks"] = dict(rgb=K.to_srgb(np.clip(rl, 0, 1)), alpha=alpha, gain=gl, island=isl)
    rep["wall-hooks"] = dict(exposure=[round(float(v), 4) for v in e], ring_px=nring, pegs=pegs, alpha_px=int(cov_h.sum()),
                             shadow=rep_cal)
    save_stage("r1", out, rep)


BLOCK_BOX = (1722, 372, 1736, 484)        # x0, y0, x1, y1: the lamp's walnut block as drawn (r1 refit: x 1730-1734, y 383-470)
PEG_SHADOW = dict(dy=3.0, sigma=3.0, band=(2, 9))


def drawn_alpha(rgb01, box, test):
    """a drawn object's alpha in a box: the test's pixels (closed, holes filled) at 1, and a 1 px luminance matte at their edge"""
    x0, y0, x1, y1 = box
    lab = K.lab_from_lin(K.to_lin(rgb01[y0:y1, x0:x1]))
    L, C = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    core = cv2.morphologyEx(test(L, C).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(core, 8)
    core = cc == (1 + int(np.argmax(st[1:, 4]))) if n > 1 else core > 0
    near = cv2.dilate(core.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    far = ~(cv2.dilate(core.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0)
    ls = float(np.median(L[far])) if far.any() else 75.0
    lw = float(np.median(L[core])) if core.any() else 40.0
    matte = np.clip((ls - L) / max(ls - lw, 1.0), 0, 1)
    a = np.where(core, 1.0, np.where(near, matte, 0.0)).astype(np.float32)
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = a
    return out


def peg_shadow(alpha, gm, pegs):
    """each peg's shadow on the stone, drawn from its own alpha (shifted down dy, blurred sigma: the slot light from above), its
    depth calibrated to the model: the median of the model's luminance gain in a band 2-9 px under each block, over its width.
    (The model's gain itself carries its moved joint as dark ticks beside the blocks, so it is not used directly.)"""
    sh = cv2.GaussianBlur(np.roll(alpha, int(round(PEG_SHADOW["dy"])), 0), (0, 0), PEG_SHADOW["sigma"])
    wv = np.ones((H, W), np.float32)                              # the slot light is above: no shadow over a block's upper half
    for p in pegs:
        x0, y0, x1, y1 = p["clay_block_px"]
        cols = slice(int(x0) - 12, int(x1) + 13)
        yy = np.arange(H, dtype=np.float32)[:, None]
        t = np.clip((yy - (y0 + y1) / 2) / max((y1 - (y0 + y1) / 2), 1), 0, 1)
        wv[:, cols] = np.minimum(wv[:, cols], np.where(yy < y0 - 12, 1.0, t * t * (3 - 2 * t)))
    sh = sh * wv
    glum = gm @ K.W709.astype(np.float32)
    ratios, levels = [], []
    for p in pegs:
        x0, y0, x1, y1 = p["clay_block_px"]
        b0, b1 = PEG_SHADOW["band"]
        xs, ys = slice(int(x0) + 2, int(x1) - 1), slice(int(y1) + b0, int(y1) + b1)
        ratios.append(float(np.median(glum[ys, xs])))
        levels.append(float(np.median(sh[ys, xs])))
    g_band, s_band = float(np.median(ratios)), float(np.median(levels))
    k = (1 - g_band) / max(s_band, 1e-3)
    g = 1 - k * sh * (alpha < 0.999)
    g = np.clip(g, 0.3, 1.0)
    return np.repeat(g[..., None], 3, -1).astype(np.float32), dict(model_gain_under_blocks=[round(r, 3) for r in ratios],
                                                                   band_px=PEG_SHADOW["band"], k=round(k, 3), **{k_: v for k_, v in PEG_SHADOW.items() if k_ != "band"})


# ---- gains (shadow < 1 < light) ----------------------------------------------------------------------------------------------
def gains(model_lin, base01, isl, alpha_mask, sigma, feather, grow=1):
    """the model's smooth per-channel linear gain over ht2.png inside the island: normalised blur of both, excluding the joints
    of either picture, every alpha (grown 1 px) and the outside of the island; (g - 1) feathered to 0 at the island's edge"""
    base_lin = K.to_lin(base01)
    kk = np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)
    valid = isl & ~joints(K.to_srgb(np.clip(model_lin, 0, 1))) & ~joints(base01) & ~(cv2.dilate(alpha_mask.astype(np.uint8), kk) > 0)
    x0, y0, x1, y1 = bbox(isl, pad=int(3 * sigma) + 2)
    g = np.ones((H, W, 3), np.float32)
    mb = nblur(model_lin[y0:y1, x0:x1], valid[y0:y1, x0:x1], sigma)
    bb = nblur(base_lin[y0:y1, x0:x1], valid[y0:y1, x0:x1], sigma)
    wsum = cv2.GaussianBlur(valid[y0:y1, x0:x1].astype(np.float32), (0, 0), sigma)
    gg = mb / np.maximum(bb, 1e-4)
    # few valid pixels near (an alpha, or the limestone's pits, which the joint test also flags): the coarser (3 sigma) estimate
    mb3 = nblur(model_lin[y0:y1, x0:x1], valid[y0:y1, x0:x1], 3 * sigma)
    bb3 = nblur(base_lin[y0:y1, x0:x1], valid[y0:y1, x0:x1], 3 * sigma)
    w3 = cv2.GaussianBlur(valid[y0:y1, x0:x1].astype(np.float32), (0, 0), 3 * sigma)
    g3 = 1 + (mb3 / np.maximum(bb3, 1e-4) - 1) * np.clip((w3 - 0.02) / 0.1, 0, 1)[..., None]
    wt = np.clip((wsum - 0.05) / 0.25, 0, 1)[..., None]
    g[y0:y1, x0:x1] = g3 + (gg - g3) * wt
    d = cv2.distanceTransform(isl.astype(np.uint8), cv2.DIST_L2, 5)
    t = np.clip(d / float(feather), 0, 1)
    f = (t * t * (3 - 2 * t))[..., None]
    g = 1 + (g - 1) * f
    g[~isl] = 1
    return g.astype(np.float32)


def save_stage(name, out, rep):
    np.savez_compressed(os.path.join(SCR, f"stage-{name}.npz"), **{f"{k}__{f}": (v[f].astype(np.float16) if f != "island" else v[f])
                                                                   for k, v in out.items() for f in v})
    K.dump(os.path.join(SCR, f"stage-{name}.json"), rep)
    print(json.dumps(rep, indent=1, default=str)[:3000])


def load_stage(name):
    z = np.load(os.path.join(SCR, f"stage-{name}.npz"))
    out = {}
    for key in z.files:
        k, f = key.split("__")
        out.setdefault(k, {})[f] = z[key].astype(np.float32) if f != "island" else z[key]
    return out, json.load(open(os.path.join(SCR, f"stage-{name}.json")))


if __name__ == "__main__":
    if sys.argv[1] == "r1":
        stage_r1(sys.argv[2])


# ---- the throw (r1, remapped onto the clay) and the basket (fix1, registered onto the clay) ----------------------------------
# r1's throw, column-averaged landmarks (x 1560-1700): top surface 1121-1163, three fold edges with creases at 1190 / 1220 / 1247,
# the hanging panel from 1250, its hem 1440-1451; the waffle period 11.4 px (autocorrelation). The clay: top face 1150-1219,
# front 1219-1273 (7.5 cm at the front), panel to 1384 (Z 0.30, 15 cm). The panel is cut by 8 whole periods (91.2 px) above its
# hem, so its cells stay square; the folds are compressed (0.62), the top spread (1.64: the clay's lower stack shows more of it).
PERIOD = 11.4
R1_PANEL_RIGHT = 1772                       # r1's panel ends at x ~1765 (right edge and its hem)
R1_PANEL_EDGE_R = 1757.5                    # r1's front panel, right edge (rows 1290-1362: 1756-1758)
THROW_KNOTS = [(1150.0, 1121.0), (1219.0, 1163.0), (1273.0, 1250.0), (1372.2, 1349.2), (1372.21, 1349.2 + 8 * PERIOD),
               (1383.2, 1451.4)]


def throw_src_y(ty):
    t = np.array([k[0] for k in THROW_KNOTS])
    s = np.array([k[1] for k in THROW_KNOTS])
    out = np.interp(ty, t, s)
    out = np.where(ty < t[0], ty - (t[0] - s[0]), out)
    return np.where(ty > t[-1], ty + (s[-1] - t[-1]), out)


def texture_energy(L, s=2.5):
    m = cv2.GaussianBlur(L, (0, 0), s)
    return np.sqrt(np.maximum(cv2.GaussianBlur(L * L, (0, 0), s) - m * m, 0))


def throw_alpha_r1(r1c, base):
    """r1's throw: waffle texture energy or a clear difference from ht2.png, in the throw's island; GrabCut in its box with the clay
    proxy (grown to r1's thicker stack and longer panel) as the prior"""
    isl = island("bench-throw")
    labr = K.lab_from_lin(K.to_lin(r1c)).astype(np.float32)
    labb = K.lab_from_lin(K.to_lin(base)).astype(np.float32)
    dE = np.sqrt(((labr - labb) ** 2).sum(-1))
    te = texture_energy(labr[..., 0])
    teb = texture_energy(labb[..., 0])
    x0, y0, x1, y1 = 1400, 1095, 1800, 1475
    roi = np.zeros((H, W), bool)
    roi[y0:y1, x0:x1] = True
    fg = roi & (((te > 4.0) & (te > teb + 2.0)) | (dE > 14))
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(fg, 8)
    fg = cc == (1 + int(np.argmax(st[1:, 4])))
    mask = np.full((y1 - y0, x1 - x0), cv2.GC_BGD, np.uint8)
    sub = fg[y0:y1, x0:x1]
    mask[cv2.dilate(sub.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0] = cv2.GC_PR_BGD
    mask[sub] = cv2.GC_PR_FGD
    mask[cv2.erode(sub.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0] = cv2.GC_FGD
    lr, cr = labr[y0:y1, x0:x1, 0], np.hypot(labr[y0:y1, x0:x1, 1], labr[y0:y1, x0:x1, 2])
    yy = np.arange(y0, y1)[:, None] + np.zeros((1, x1 - x0))
    mask[(lr > 62) & (cr < 16) & (yy > 1300)] = cv2.GC_BGD           # r1's cream basket
    mask[:, R1_PANEL_RIGHT - x0:] = cv2.GC_BGD                       # right of r1's panel: the seat and the basket
    img = (np.clip(r1c[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, None, bgd, fgd, 4, cv2.GC_INIT_WITH_MASK)
    a = np.zeros((H, W), bool)
    a[y0:y1, x0:x1] = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    a = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(a, 8)
    a = cc == (1 + int(np.argmax(st[1:, 4])))
    hole = cv2.floodFill((~a).astype(np.uint8).copy(), None, (0, 0), 0)[1] > 0
    return a | hole


BASKET_FIX1 = dict(x=(1567.5, 1844.5), rim_y=1332.0)       # fix1's basket: side edges (gradient peaks, rows 1400-1500), rim (right)
BASKET_CLAY = dict(x=(1586.5, 1804.5), rim_y=1330.4)       # the clay's (geo.render: D 30 at (1.01, 7.10); rim at Y 6.95, v 0.8918)
THROW_BOX = (1415, 1125, 1785, 1400)                       # the throw's target box
THROW_SHADOW_K = 0.35
SEAT_EDGE_Y = 1273                                         # the seat's front edge (v 0.8519)
SEAT_UNDER_Y, SEAT_SHADE = 1309.0, 0.72                    # the seat's front face bottom (v 0.8767); its shade on the basket
PLASTER_HEX = "#ECE5DA"                                    # the hall plaster (the jib door): the scene's cast against its design
BASKET_PHOTO_H = 85.0                                      # house20-photo-check basket-cream-b: L* 82.8, C* 11.5, h 85
BASKET_PHOTO_C_OVER_L = 0.16                               # the photo's 0.14 (11.5 / 82.8) + the still's cast (the plaster: 0.06 -> 0.08)
THROW_PHOTO = dict(L=70.0, C_over_L=0.16)                  # khaki: L* 64-75 (SKU 74.8, close-up 63.6, bed 71.5), C*/L* 0.11-0.18 (8.1)
WALNUT_HEX = "#6B4A33"                                     # the bench's walnut (route 2.2): its vertical faces in ht2.png give the light
BASKET_BOX = (1560, 1240, 1832, 1530)


def basket_map(tx, ty, period):
    s = (BASKET_CLAY["x"][1] - BASKET_CLAY["x"][0]) / (BASKET_FIX1["x"][1] - BASKET_FIX1["x"][0])
    cxf, cxc = np.mean(BASKET_FIX1["x"]), np.mean(BASKET_CLAY["x"])
    sx = cxf + (tx - cxc) / s
    sy = BASKET_FIX1["rim_y"] + (ty - BASKET_CLAY["rim_y"]) / s
    last = H - 2.0                                            # fix1 ends at the canvas bottom: the rope's last period repeats
    sy = np.where(sy > last, last - period + np.mod(sy - last, period), sy)
    return sx, sy, s


def rope_period(f01):
    L = K.lab_from_lin(K.to_lin(f01))[1420:1520, 1780:1830, 0].mean(1)
    L = L - L.mean()
    ac = np.array([np.sum(L[:-k] * L[k:]) / len(L[k:]) for k in range(3, 20)])
    k = 3 + int(np.argmax(ac))
    return float(k)


def basket_alpha_fix1(f01, period):
    """fix1's basket: GrabCut in its box, seeded by the clay silhouette carried back into fix1 (eroded: basket, outside grown: not)"""
    _, cov, _ = G.render("basket", shade=False)
    x0, y0, x1, y1 = 1530, 1230, 1880, H
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    s = (BASKET_CLAY["x"][1] - BASKET_CLAY["x"][0]) / (BASKET_FIX1["x"][1] - BASKET_FIX1["x"][0])
    cx = np.mean(BASKET_CLAY["x"]) + (xx - np.mean(BASKET_FIX1["x"])) * s     # fix1 px -> clay px (forward map)
    cy = BASKET_CLAY["rim_y"] + (yy - BASKET_FIX1["rim_y"]) * s
    prior = cv2.remap(cov.astype(np.float32), cx.astype(np.float32), cy.astype(np.float32), cv2.INTER_LINEAR) > 0.5
    lab = K.lab_from_lin(K.to_lin(f01[y0:y1, x0:x1]))
    khaki = (np.hypot(lab[..., 1], lab[..., 2]) > 15.5) & (lab[..., 0] < 62)
    mask = np.full(prior.shape, cv2.GC_PR_BGD, np.uint8)
    mask[prior] = cv2.GC_PR_FGD
    mask[cv2.erode(prior.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0] = cv2.GC_FGD
    mask[~(cv2.dilate(prior.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0)] = cv2.GC_BGD
    mask[khaki & (yy < 1400)] = cv2.GC_BGD                                     # fix1's own hanging panel
    img = (np.clip(f01[y0:y1, x0:x1], 0, 1) * 255).astype(np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, None, bgd, fgd, 4, cv2.GC_INIT_WITH_MASK)
    a = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    a = cv2.morphologyEx(a.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(a, 8)
    a = cc == (1 + int(np.argmax(st[1:, 4])))
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = a
    return out


def rolling_median(v, k):
    p = np.pad(v, (k // 2, k // 2), mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(p, k), -1)


def stone_exposure(m01, base01):
    """one luminance factor, model / ht2 on the limestone above the bench (x 1300-2000, y 900-1100, joints excluded): the per-channel
    ratio on the ring round an island is skewed by the redrawn bench and would tint the product (r1: 1.16 / 1.04 / 1.19)"""
    stone = np.zeros((H, W), bool)
    stone[900:1100, 1300:2000] = True
    stone &= ~joints(m01) & ~joints(base01)
    r = float(np.median((K.to_lin(m01[stone]) @ K.W709) / np.maximum(K.to_lin(base01[stone]) @ K.W709, 1e-4)))
    return np.array([r, r, r]), int(stone.sum())


def hex_lab(h):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    return K.lab_from_lin(K.to_lin(c[None]))[0]


def scene_cast(base01):
    """hue rotation of the still's light: ht2.png's jib-door plaster (x 500-900, y 300-900) against #ECE5DA (h about 80 -> 72)"""
    lab = K.lab_from_lin(K.to_lin(base01[300:900, 500:900])).reshape(-1, 3)
    hm = np.degrees(np.arctan2(np.median(lab[:, 2]), np.median(lab[:, 1])))
    d = hex_lab(PLASTER_HEX)
    return float(hm - np.degrees(np.arctan2(d[2], d[1])))


def hue_to(rgb01, m, target_h):
    """rotate a*/b* inside m so the median hue is target_h; L* and C* kept (the product's colour against its SKU photo)"""
    lab = K.lab_from_lin(K.to_lin(rgb01))
    h0 = float(np.degrees(np.arctan2(np.median(lab[..., 2][m]), np.median(lab[..., 1][m]))))
    dh = np.radians(target_h - h0)
    a, b = lab[..., 1], lab[..., 2]
    lab2 = lab.copy()
    lab2[..., 1] = np.where(m, a * np.cos(dh) - b * np.sin(dh), a)
    lab2[..., 2] = np.where(m, a * np.sin(dh) + b * np.cos(dh), b)
    out = K.to_srgb(K.lin_from_lab(lab2)).astype(np.float32)
    return out, dict(h_drawn=round(h0, 1), h_target=round(float(target_h), 1), rotation_deg=round(float(target_h - h0), 1))


def to_photo(rgb01, m, base01, panel_rows=None, albedo_L=None, c_over_l=None):
    """the product's colour against its photo (8.1: "the hue by the real photo"; as B1's mat): optionally its reflectance, from the
    light on its vertical panel measured on the bench's own vertical walnut (the left end panel's front face in ht2.png against
    #6B4A33), then its chroma (C*/L* median), hue and the model's shading kept"""
    rep = {}
    lin = K.to_lin(rgb01)
    if albedo_L is not None:
        lpanel = np.zeros(m.shape, bool)
        lpanel[1330:1480, 1468:1488] = True                        # the left panel's front face (lock: u 0.5413-0.5553), below the seat
        lpanel &= G.bench_mask()
        y_w = float(np.median(K.to_lin(base01[lpanel]) @ K.W709))
        w = hex_lab(WALNUT_HEX)
        y_walb = float(K.lin_from_lab(w[None])[0] @ K.W709)
        light = y_w / y_walb                                       # what a vertical face receives, against its albedo
        pm = m.copy()
        pm[:panel_rows[0]] = False
        pm[panel_rows[1]:] = False
        y_p = float(np.median(lin[pm] @ K.W709))
        alb_model = y_p / light
        alb_target = float(K.lin_from_lab(np.array([[albedo_L, 0, 0]]))[0] @ K.W709)
        gy = alb_target / alb_model
        lin = np.where(m[..., None], lin * gy, lin)
        rep.update(walnut_vertical_light=round(light, 3), model_albedo_L=round(float(K.lstar(alb_model)), 1), target_albedo_L=albedo_L,
                   luminance_gain=round(gy, 3), panel_px=int(pm.sum()))
    lab = K.lab_from_lin(np.clip(lin, 0, 1))
    if c_over_l is not None:
        L, a, b = lab[..., 0][m], lab[..., 1][m], lab[..., 2][m]
        cl0 = float(np.median(np.hypot(a, b)) / max(np.median(L), 1e-3))
        f = c_over_l / max(cl0, 1e-3)
        lab[..., 1] = np.where(m, lab[..., 1] * f, lab[..., 1])
        lab[..., 2] = np.where(m, lab[..., 2] * f, lab[..., 2])
        rep.update(c_over_l_drawn=round(cl0, 3), c_over_l_target=c_over_l, chroma_scale=round(f, 3))
    out = K.to_srgb(K.lin_from_lab(lab)).astype(np.float32)
    return np.where(m[..., None], out, rgb01).astype(np.float32), rep


def synth_shadow(alpha, where, k, sigma, dy=0.0):
    sh = cv2.GaussianBlur(np.roll(alpha, int(round(dy)), 0), (0, 0), sigma)
    g = 1 - k * sh * (alpha < 0.999) * where
    return np.repeat(np.clip(g, 0.3, 1.0)[..., None], 3, -1).astype(np.float32)


def stage_bench(r1p, f1p):
    base = rgb8(BASE) / 255.0
    r4, f4 = rgb8(r1p), rgb8(f1p)
    r1c, f1c = to_canvas(r4) / 255.0, to_canvas(f4) / 255.0
    allisl = all_islands()
    rep = dict(throw=dict(source="r1 " + os.path.basename(r1p), knots=THROW_KNOTS, period_px=PERIOD),
               basket=dict(source="fix1 " + os.path.basename(f1p), fix1=BASKET_FIX1, clay=BASKET_CLAY))
    # -- the throw
    a_src = throw_alpha_r1(r1c, base).astype(np.float32)
    a_src[int(np.ceil(THROW_KNOTS[-1][1])) + 2:] = 0
    a_src = cv2.GaussianBlur(a_src, (0, 0), 0.7)
    x0, y0, x1, y1 = THROW_BOX
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    sy = throw_src_y(yy)
    sx = xx.copy()
    # the hanging panel, row by row: r1's light-fabric edges (L* > 30 in its alpha) onto the clay's straight edges
    a_flap = G.face_alpha("bench-throw", "khaki_flap")
    fl_cols = np.nonzero(a_flap[SEAT_EDGE_Y + 40] > 0.5)[0]
    cl, cr = fl_cols.min() - 0.5, fl_cols.max() + 0.5
    Lr = K.lab_from_lin(K.to_lin(r1c))[..., 0]
    rows = np.arange(1250, int(THROW_KNOTS[-1][1]) + 1)
    xl, xr = [], []
    for r in rows:
        c = np.nonzero((a_src[r] > 0.5) & (Lr[r] > 30) & (np.arange(W) > 1470) & (np.arange(W) < R1_PANEL_RIGHT))[0]
        xl.append(c.min() - 0.5 if len(c) else np.nan)
        xr.append(c.max() + 0.5 if len(c) else np.nan)
    xl = np.array(xl)
    fit = np.isfinite(xl) & (rows >= 1290)                      # below the stack: r1's panel edge slants 1494 -> 1517
    pl = np.polyfit(rows[fit], xl[fit], 1)
    xl = np.polyval(pl, rows)
    xr = np.full(rows.shape, R1_PANEL_EDGE_R)                   # the front panel's right edge (a second layer hangs 13 px beyond it)
    fl = yy >= SEAT_EDGE_Y
    l_s, r_s = np.interp(sy, rows, xl), np.interp(sy, rows, xr)
    sx = np.where(fl, l_s + (xx - cl) / (cr - cl) * (r_s - l_s), sx)
    rgb_t = np.zeros((H, W, 3), np.float32)
    rgb_t[y0:y1, x0:x1] = remap4(r4, sx, sy, sig=(0.85, 1.25))
    rep["throw"]["panel_rectified"] = dict(clay_edges=[round(float(cl), 1), round(float(cr), 1)], r1_left_fit=[round(float(v), 4) for v in pl],
                                           r1_left=[round(float(xl[0]), 1), round(float(xl[-1]), 1)], r1_right=R1_PANEL_EDGE_R)
    a_t = np.zeros((H, W), np.float32)
    a_t[y0:y1, x0:x1] = cv2.remap(a_src, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR)
    _, cov_t, _ = G.render("bench-throw", shade=False)
    near = cv2.dilate(cov_t.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))) > 0
    near_flap = cv2.dilate(cov_t.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
    near[SEAT_EDGE_Y:] = near_flap[SEAT_EDGE_Y:]                  # the panel: r1's dark side edges stay out (3 px, not 8)
    lab_t = K.lab_from_lin(K.to_lin(rgb_t))
    hue = np.degrees(np.arctan2(lab_t[..., 2], lab_t[..., 1]))
    walnut_px = (hue < 66) & (np.hypot(lab_t[..., 1], lab_t[..., 2]) > 21)      # r1's seat edge carried along: not the throw
    a_t = a_t * near * ~walnut_px
    a_t = cv2.GaussianBlur(cv2.morphologyEx((a_t > 0.5).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.7) * (a_t > 0.02)
    a_t[SEAT_EDGE_Y:] = a_flap[SEAT_EDGE_Y:]                    # the hanging panel: the clay's outline (r1's rectified onto it)
    e_t, n_t = stone_exposure(r1c, base)
    rgb_t = K.to_srgb(np.clip(K.to_lin(rgb_t) / e_t, 0, 1)).astype(np.float32)
    rgb_t, col_t = to_photo(rgb_t, a_t > 0.5, base, panel_rows=(1290, 1370), albedo_L=THROW_PHOTO["L"], c_over_l=THROW_PHOTO["C_over_L"])
    # its shadow: on the bench (seat top right of the stack, the front face beside the panel) and on the stone behind the stack,
    # calibrated on r1's own seat just right of its stack (r1 kept the bench: shift 0)
    gl_r1 = (K.to_lin(r1c) @ K.W709) / np.maximum(K.to_lin(base) @ K.W709, 1e-4)
    cal = float(np.median(gl_r1[1210:1262, 1768:1778]))
    sh_t = cv2.GaussianBlur(a_t, (0, 0), 4.0)
    ref = float(np.median(sh_t[1210:1262, 1768:1778])) if sh_t[1210:1262, 1768:1778].max() > 0 else 0.3
    k_t = (1 - cal) / max(ref, 0.05)
    k_used = k_t if 0.1 <= k_t <= 1.2 else THROW_SHADOW_K       # r1's seat beside its stack reads brighter than ht2's: no calibration
    under = np.zeros((H, W), np.float32)
    under[1300:] = 1.0                                           # under the seat (the basket, the stone in the seat's shade)
    where = np.clip(G.bench_mask().astype(np.float32) + under, 0, 1)
    g_t = synth_shadow(a_t, where, k_used, 3.0, dy=2)
    rep["throw"].update(exposure=[round(float(v), 4) for v in e_t], ring_px=n_t, alpha_px=int((a_t > 0.01).sum()),
                        colour_to_photo=col_t,
                        shadow=dict(r1_seat_gain=round(cal, 3), k_from_r1=round(k_t, 3), k=round(k_used, 3), sigma=3.0, dy=2,
                                    where="the bench (clay id 100) and below y 1300; never the stone above the seat (light from above)"))
    # -- the basket
    per = rope_period(f1c)
    a_bs = basket_alpha_fix1(f1c, per)
    x0, y0, x1, y1 = BASKET_BOX
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    sx, sy, s = basket_map(xx, yy, per)
    rgb_b = np.zeros((H, W, 3), np.float32)
    rgb_b[y0:y1, x0:x1] = remap4(f4, sx, sy, sig=(1.3, 1.3))
    a_b = np.zeros((H, W), np.float32)
    a_b[y0:y1, x0:x1] = cv2.remap(cv2.GaussianBlur(a_bs, (0, 0), 0.8), sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR)
    a_b *= ~G.bench_mask()                                     # behind the seat's front edge and the panels (the clay's bench)
    e_b, _ = stone_exposure(f1c, base)
    rgb_b = K.to_srgb(np.clip(K.to_lin(rgb_b) / e_b, 0, 1)).astype(np.float32)
    cast = scene_cast(base)
    rgb_b, hue_rep = hue_to(rgb_b, a_b > 0.5, BASKET_PHOTO_H + cast)
    # the seat's shade on the basket (fix1 lit it under its own, higher seat): linear 0.72 at the seat's underside -> 1 by y 1440
    yv = np.arange(H, dtype=np.float32)[:, None]
    t = np.clip((yv - SEAT_UNDER_Y) / (1440.0 - SEAT_UNDER_Y), 0, 1)
    ramp = SEAT_SHADE + (1 - SEAT_SHADE) * t * t * (3 - 2 * t)
    rgb_b = K.to_srgb(np.clip(K.to_lin(rgb_b) * ramp[..., None], 0, 1)).astype(np.float32)
    rgb_b, col_b = to_photo(rgb_b, a_b > 0.5, base, c_over_l=BASKET_PHOTO_C_OVER_L)
    g_b = synth_shadow(a_b, 1.0, 0.25, 7.0, dy=2)
    rep["basket"].update(scale=round(float(s), 4), rope_period_px=per, exposure=[round(float(v), 4) for v in e_b],
                         alpha_px=int((a_b > 0.01).sum()), hue=dict(scene_cast_deg=round(cast, 1), **hue_rep),
                         seat_shade=dict(at_y=SEAT_UNDER_Y, gain=SEAT_SHADE, to_y=1440), colour_to_photo=col_b, bottom_rows_repeated="target y > %.0f (overscan; the frame ends at 1486.6)" %
                         (BASKET_CLAY["rim_y"] + (H - 2 - BASKET_FIX1["rim_y"]) * s), shadow=dict(k=0.25, sigma=7.0, dy=2, note="synthetic, subtle: fix1's own is on its moved bench"))
    out = {"bench-throw": dict(rgb=rgb_t, alpha=a_t, gain=g_t, island=island("bench-throw")),
           "basket": dict(rgb=rgb_b, alpha=a_b, gain=g_b, island=island("basket"))}
    save_stage("bench", out, rep)


if __name__ == "__main__" and sys.argv[1] == "bench":
    stage_bench(sys.argv[2], sys.argv[3])


# ---- write: the files, the composite from the files, RND2 -------------------------------------------------------------------
ORDER_Z = ("wall-sconce", "wall-hooks", "basket", "bench-throw")
BLACK_POINT = 12.7                                        # ht2-lock.json bench_levels.black_point_L_p01 (the 16:9 frame)
WALNUT_FLOOR = BLACK_POINT + 8                            # 12.7 rule: a walnut face >= 8 L* over the black point


def q8(x):
    return np.clip(np.rint(x), 0, 255).astype(np.uint8)


def grey_shadow(below8, g):
    """grey multiply factor (0-255) that darkens below8 by the luminance part of the gain g where it is < 1"""
    gy = np.minimum(g @ K.W709.astype(np.float32), 1.0)
    b = below8.astype(np.float32) / 255.0
    t = K.to_srgb(np.clip(K.to_lin(b) * gy[..., None], 0, 1))
    s = np.where(b > 0.02, t / np.maximum(b, 1e-3), 1.0).mean(-1)
    s = np.where(gy >= 0.999, 1.0, s)
    return q8(np.clip(s, 0, 1) * 255)


def walnut_tone(rgb01, a, name):
    """tone.py's WM-G1 toe inside a walnut alpha, A set so the alpha's p2 L* reaches the walnut floor (if it is under it)"""
    sys.path.insert(0, os.path.join(G.HALL18, "tools"))
    import tone as TN  # noqa: E402
    m = a > 0.5
    L = TN.lab(rgb01)[..., 0]
    p2 = float(np.percentile(L[m], 2))
    rep = dict(p2_before=round(p2, 2), floor=WALNUT_FLOOR)
    if p2 >= WALNUT_FLOOR:
        rep["A"] = 0.0
        return rgb01, rep
    lo, hi = 0.0, 14.9
    for _ in range(40):
        A = (lo + hi) / 2
        if float(np.percentile(TN.f(L[m], A), 2)) < WALNUT_FLOOR:
            lo = A
        else:
            hi = A
    out, _ = TN.apply(rgb01.astype(np.float64), hi, m)
    rep.update(A=round(hi, 3), p2_after=round(float(np.percentile(TN.lab(out)[..., 0][m], 2)), 2), name=name)
    return out.astype(np.float32), rep


def write():
    o1, r1rep = load_stage("r1")
    o2, b_rep = load_stage("bench")
    out = {**o1, **o2}
    base8 = rgb8(BASE)
    reps = {}
    # the walnut floor (12.7): the pegs and the lamp's block
    rgb_h, reps["wall-hooks_tone"] = walnut_tone(out["wall-hooks"]["rgb"], out["wall-hooks"]["alpha"], "pegs")
    out["wall-hooks"]["rgb"] = rgb_h
    blk = out["wall-sconce"]["alpha"] * (G.cylinder_alpha()[0] < 0.5)
    rgb_s, reps["wall-sconce_block_tone"] = walnut_tone(out["wall-sconce"]["rgb"], blk, "lamp block")
    out["wall-sconce"]["rgb"] = np.where((blk > 0)[..., None], rgb_s, out["wall-sconce"]["rgb"])
    files, cur = {}, base8.copy()
    for s in ORDER_Z:
        meta = G.PIDS[s]
        S8 = grey_shadow(cur, out[s]["gain"])
        A8 = q8(out[s]["alpha"] * 255)
        RGB8 = q8(np.clip(out[s]["rgb"], 0, 1) * 255)
        RGB8[A8 == 0] = 0
        files[s] = (S8, A8, RGB8)
        cur = compose_step(cur, S8, A8, RGB8)
    pre = cur
    # the light (the wall light only), screen, never on a product
    g = out["wall-sconce"]["gain"]
    lightm = (g @ K.W709.astype(np.float32)) > 1.0005
    anyA = np.zeros(pre.shape[:2], bool)
    for s in ORDER_Z:
        anyA |= files[s][1] > 0
    tgt = K.to_srgb(np.clip(K.to_lin(pre / 255.0) * np.maximum(g, 1.0), 0, 1)) * 255
    Lt = 255 - 255 * (255 - tgt) / np.maximum(255 - pre.astype(np.float32), 1e-3)
    Lt = np.where((lightm & ~anyA)[..., None], Lt, 0)
    L8 = q8(np.clip(Lt, 0, 255))
    final = screen(pre, L8)
    # files
    lay = os.path.join(G.OUT, "layers")
    entries = []
    for s in ORDER_Z:
        S8, A8, RGB8 = files[s]
        pid = G.PIDS[s]["pid"]
        lp = os.path.join(lay, s, pid + ".png")
        sp = os.path.join(G.OUT, "shadows", s, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        Image.fromarray(np.dstack([RGB8, A8]), "RGBA").save(lp, optimize=True)
        Image.fromarray(S8, "L").save(sp, optimize=True)
        entries.append(dict(slot=s, product=pid, card=G.PIDS[s]["card"], sku=G.PIDS[s]["sku"], z=Z[s], shadow_z=Z[s] - 1, default=True,
                            layer=os.path.relpath(lp, G.OUT), shadow=os.path.relpath(sp, G.OUT), alpha_px=int((A8 > 0).sum()),
                            shadow_px=int((S8 < 255).sum())))
    lpth = os.path.join(G.OUT, "light", G.PIDS["wall-sconce"]["pid"] + ".png")
    os.makedirs(os.path.dirname(lpth), exist_ok=True)
    Image.fromarray(L8, "RGB").save(lpth, optimize=True)
    # recompose from the files (as a page would), and RND2
    chk = base8.copy()
    for s in ORDER_Z:
        e = [x for x in entries if x["slot"] == s][0]
        S8 = np.asarray(Image.open(os.path.join(G.OUT, e["shadow"])))
        LA = np.asarray(Image.open(os.path.join(G.OUT, e["layer"])))
        chk = compose_step(chk, S8, LA[..., 3], LA[..., :3])
    chk = screen(chk, np.asarray(Image.open(lpth)))
    assert np.array_equal(chk, final)
    touched = (L8.max(-1) > 0)
    for s in ORDER_Z:
        touched |= (files[s][0] < 255) | (files[s][1] > 0)
    rnd2 = int(np.abs(chk.astype(int) - base8.astype(int))[~touched].max())
    K.save(os.path.join(G.OUT, "ht2-products.png"), chk)
    cv = K.canvas("HT")
    K.save(os.path.join(G.OUT, "ht2-products-frame.png"), cv.crop_frame(chk, 1920, 1080))
    man = dict(frame="HT2", room="hall", style="warm-modern", date="2026-11-19", canvas=[W, H],
               base="../hall-2026-11-18/ht2.png (accepted 12.7.2; not edited)", frame_box=list(cv.box),
               grade="ht2.png's own (no grade on the products beyond tone.py's WM-G1 toe in the walnut alphas, if needed: see tone)",
               compose=dict(order=["base"] + [f"{s}-shadow (z {Z[s] - 1}), {s} (z {Z[s]})" for s in ORDER_Z] + ["light (screen, z 90)"],
                            formula="per slot: out = round((below * shadow / 255) * (1 - a) + rgb * a), straight alpha, a = A / 255; then the "
                                    "light: out = 255 - round((255 - out) * (255 - L) / 255)"),
               layers=entries, light=[dict(slot="wall-sconce", product=G.PIDS["wall-sconce"]["pid"], z=90, blend="screen",
                                           file=os.path.relpath(lpth, G.OUT), px=int(touched.sum() and (L8.max(-1) > 0).sum()))],
               rnd2=dict(outside_every_alpha_shadow_light_max_diff_vs_ht2=rnd2, recomposed_equals_written=True),
               tone=reps, at_rest_only="the layers appear only at rest on HT2 (focus mode, 6.6a.4) and lift before any move; the clips are unchanged")
    K.dump(os.path.join(lay, "manifest.json"), man)
    print(json.dumps(dict(rnd2=rnd2, tone=reps, layers=[(e["slot"], e["alpha_px"], e["shadow_px"]) for e in entries],
                          light_px=int((L8.max(-1) > 0).sum())), indent=1))


def compose_step(below8, S8, A8, RGB8):
    b = below8.astype(np.float32) * (S8.astype(np.float32)[..., None] / 255.0)
    a = A8.astype(np.float32)[..., None] / 255.0
    return q8(b * (1 - a) + RGB8.astype(np.float32) * a)


def screen(below8, L8):
    return (255 - q8((255 - below8.astype(np.float32)) * (255 - L8.astype(np.float32)) / 255.0)).astype(np.uint8)


if __name__ == "__main__" and sys.argv[1] == "write":
    write()
