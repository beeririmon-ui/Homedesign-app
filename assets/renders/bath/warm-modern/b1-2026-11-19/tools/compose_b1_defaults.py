#!/usr/bin/env python3
"""
compose_b1_defaults.py: the B1 defaults render cut into layers (RND2), render-agent, 2026-11-19. 0 tokens. As B2's compose_defaults.py
and compose_fb10.py (the same helpers, imported):
  1. lock: the render against its own input (lock_b1.py: B2's lock_b2 on the B1 clay lines), one global warp;
  2. tone match: the render came back 1.2-1.75x darker than its input (the model undid part of the plate's relight), so it gets
     the plate's own two steps first (compose_b1_plate.relight against the clay B1-plate, then the plaster's a*/b*), then B2's
     smooth gain field (sigma 60 px, per channel, linear) of base / render, outside every product zone, the beam envelope and the
     fluted glass, clamped 0.75-1.35: the products sit in the plate's exposure;
  3. each product: GrabCut in its zone (the clay's mask, as placed in the input, grown), seeded where the render differs from the
     base; its shadow is the render's darkening round it (contact rim + a band bounded by the clay's own shadow); z and pid per slot;
  4. the light of the B1 sconce (screen, z 90): where the render is brighter than the plate, on the plaster round the drawn block
     (LIGHT_BOX), never on a product or the stone;
  3b. the refits: the model drew the sconce block 1.5x and the planter's pot about 1.4x their SKU size (as B2's lamps and vase):
     both are scaled to the clay (the block by its height about its centre, the pot by its belly about its foot), with their
     shadows and the sconce's light; the vacated pixels are the plate's;
  5. the WM-G1 grade on every file (plate-grade.json's curve, grade_plate.curve_apply); the light solved again on the graded stack;
     the composites recomposed from the files on plate.png (RND2: outside every alpha, shadow and light, plate.png byte for byte).

  python3 compose_b1_defaults.py raw/defaults-r1.png
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
B2T = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools"
sys.path.insert(0, B2T)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402
import prep_defaults as PD  # noqa: E402
import lock_b1 as LK  # noqa: E402

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-b1-2026-11-19/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath/b1/"
SHIFT = {59: (-8, -3), 57: (0, -3), 58: (0, -3)}
CARD = "data/products/bath/"
SLOTS = {
    "shower-dispensers": dict(ids=(41,), z=14, band=12, rim=4, margin=14, pid="shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle",
                              card=CARD + "shower-dispensers/shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle.json", sku="CJYD301460604DW"),
    "wall-sconce": dict(ids=(60,), z=14, band=10, rim=4, margin=60, pid="wall-sconce-aliexpress-wabi-sabi-yellow-marble-037853",
                        card=CARD + "wall-sconce/wall-sconce-aliexpress-wabi-sabi-yellow-marble-037853.json", sku="12000048654610384"),
    "bath-mat": dict(ids=(53,), z=18, band=24, rim=8, margin=30, pid="bath-mat-cj-tufted-cotton-frame-beige-40x60-khaki",
                     card=CARD + "bath-mat/bath-mat-cj-tufted-cotton-frame-beige-40x60.json", sku="CJYD289719807GT"),
    "shower-curtain": dict(ids=(40,), z=26, band=60, rim=8, margin=40, pid="shower-curtain-aliexpress-linen-blend-slub-panel-200x270",
                           card=CARD + "shower-curtain/shower-curtain-aliexpress-linen-blend-slub-panel-200x270.json", sku="12000059196236303"),
    "floor-planter": dict(ids=(51, 52), z=30, band=22, rim=10, margin=120, pid="planter-cj-cement-ribbed-belly-beige-medium",
                          card="data/products/planter/planter-cj-cement-ribbed-belly.json", sku="CJJT154204208HS"),
    "bin": dict(ids=(55,), z=42, band=30, rim=8, margin=24, pid="bin-cj-bent-walnut-round-swing-lid-walnut-swing-lid",
                card=CARD + "bin/bin-cj-bent-walnut-round-swing-lid.json", sku="CJJT102413505EV"),
    "toilet-paper-stand": dict(ids=(54, 61), z=44, band=24, rim=6, margin=8, pid="toilet-paper-stand-aliexpress-matte-black-freestanding-toilet-paper-stand-with-black",
                               card=CARD + "toilet-paper-stand/toilet-paper-stand-aliexpress-matte-black-freestanding-toilet-paper-stand-with.json", sku="12000053061878471"),
    "window-sill-vase": dict(ids=(59,), z=46, band=16, rim=6, margin=16, pid="vase-cj-black-matte-stoneware-jar-30-style4",
                             card="data/products/vase/vase-cj-black-matte-stoneware-jar-30.json", sku="CJJT198137605EV"),
    "candle": dict(ids=(57,), z=46, band=12, rim=5, margin=12, pid="candle-cj-ribbed-matte-ceramic-candle-cup-9-white",
                   card=CARD + "candle/candle-cj-ribbed-matte-ceramic-candle-cup-9.json", sku="CJJT120250201AZ"),
    "reed-diffuser": dict(ids=(58,), z=46, band=12, rim=5, margin=14, pid="reed-diffuser-cj-travertine-look-bamboo-lid-milktea",
                          card=CARD + "reed-diffuser/reed-diffuser-cj-travertine-look-bamboo-lid-milktea.json", sku="milk-tea"),
    "toilet-brush": dict(ids=(56,), z=48, band=16, rim=5, margin=14, pid="toilet-brush-cj-fluted-ceramic-holder-black-handle-light-color",
                         card=CARD + "toilet-brush/toilet-brush-cj-fluted-ceramic-holder-black-handle.json", sku="CJYD254508501AZ"),
}
LIGHT_SLOT = "wall-sconce"
PLASTER = (1, 2, 3, 4)


def masks(ids):
    H, W = ids.shape
    out = {}
    for k, s in SLOTS.items():
        m = np.zeros((H, W), bool)
        for g in s["ids"]:
            mg = ids == g
            dx, dy = SHIFT.get(g, (0, 0))
            if dx or dy:
                mg = cv2.warpAffine(mg.astype(np.uint8), np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), flags=cv2.INTER_NEAREST) > 0
            m |= mg
        out[k] = m
    return out


def gain_field(render, base, keep, lo=0.6, hi=2.4):
    """B2's gain_field (per channel, linear, normalised blur sigma 60) with a wider clamp: this render came back 1.2-1.75x darker
    than its input (the model undid part of the plate's relight), which B2's 0.8-1.25 cannot absorb"""
    w = keep.astype(np.float32)
    nb = cv2.GaussianBlur(w, (0, 0), 60) + 1e-6
    g = np.ones_like(render)
    for c in range(3):
        bb = cv2.GaussianBlur((C.lin(base[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        rr = cv2.GaussianBlur((C.lin(render[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        g[..., c] = np.clip(bb / np.maximum(rr, 1e-4), lo, hi)
    return g


RECT = {"floor-planter": dict(rect=(1290, 1005, 1612, 1346), core_ellipse=(1448, 1258, 108, 72)),
        "wall-sconce": dict(rect=(1174, 356, 1258, 498), core_ellipse=(1216, 427, 28, 50)),
        "shower-dispensers": dict(rect=(2066, 668, 2214, 766), core_ellipse=(2136, 735, 58, 22))}


def core_of(k, src, box):
    """sure seeds inside the drawn box: the product's body (an ellipse inside it) and, for the planter, the pothos's green"""
    H, W = box.shape
    cx, cy, rx, ry = RECT[k]["core_ellipse"]
    yy, xx = np.mgrid[0:H, 0:W]
    core = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    if k == "floor-planter":
        lab = C.lab_of(src)
        green = (lab[..., 1] < -8) & (lab[..., 2] > 5) & box
        core |= C.ero(green, 1)
    return core & box


REFIT = ("wall-sconce", "floor-planter")
# the brush as drawn (measured at 3x on the locked r1): about 10 px left of the clay (id 56), so its cut followed the clay and
# lost the cup's left side and the handle; the cup is a fluted cylinder and the handle a rod, so their outline is drawn here
CUP_TOP = (1260.0, 1279.5, 33.5, 5.5)               # the rim ellipse: cx, cy, rx, ry
CUP_BOT = (1260.5, 1362.0, 27.5, 5.0)               # the foot
CUP_BODY = [(1226.5, 1279.5), (1293.5, 1279.5), (1288.0, 1362.0), (1233.0, 1362.0)]
HANDLE = (1253.0, 1126.0, 1263.0, 1280.0)           # x0, y0, x1, y1


def brush_shape(H, W):
    yy, xx = np.mgrid[0:H, 0:W]
    m = np.zeros((H, W), bool)
    for cx, cy, rx, ry in (CUP_TOP, CUP_BOT):
        m |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    b = np.zeros((H, W), np.uint8)
    cv2.fillPoly(b, [np.int32(np.round(np.array(CUP_BODY) * 16))], 1, shift=4)
    m |= b.astype(bool)
    x0, y0, x1, y1 = HANDLE
    m |= (xx >= x0) & (xx <= x1) & (yy >= y0 + 3) & (yy <= y1)
    m |= ((xx - (x0 + x1) / 2) / ((x1 - x0) / 2 + 0.5)) ** 2 + ((yy - (y0 + 3)) / 3.0) ** 2 <= 1
    return m


def hull_of(f, min_px=200):
    """the convex hull of every piece of the cut bigger than min_px (the crack split the bin in two)"""
    n, lab, st, _ = cv2.connectedComponentsWithStats(f.astype(np.uint8), connectivity=8)
    keep = np.isin(lab, [i for i in range(1, n) if st[i, 4] >= min_px])
    pts = cv2.findNonZero(keep.astype(np.uint8))
    h = np.zeros(f.shape, np.uint8)
    cv2.fillPoly(h, [cv2.convexHull(pts)], 1)
    return h.astype(bool)
MAT_QUAD = [(1320.0, 1379.0), (1532.5, 1349.0), (1703.0, 1477.5), (1452.5, 1524.0)]   # far-left, far-right, near-right, near-left (r1)
MAT_CLAY = [(1315.0, 1368.0), (1522.0, 1334.0), (1697.0, 1476.0), (1453.0, 1526.0)]   # the clay's (id 53), the same order
MAT_KHAKI = (77.6, 4.2, 13.6)                       # house-20 photo check, mat-khaki (the SKU photo's floor crop)
MAT_BEIGE = (87.5, 0.0, 6.6)                        # mat-beige (the real photo on wood agrees: 88.6 / 7.7 / 86 LCh)
STONE = "#D8C8AE"                                   # the floor's limestone (WM bath)


def mat_quad(H, W):
    q = np.zeros((H, W), np.uint8)
    cv2.fillPoly(q, [np.int32(np.round(np.array(MAT_QUAD) * 16))], 1, lineType=cv2.LINE_8, shift=4)
    return q.astype(bool)


YW = np.array([0.2126, 0.7152, 0.0722])
PLASTER_HEX = "#ECE5DA"
LOWWALL_BOX = (1000, 1450, 1000, 1800)               # rows, cols: the plaster of the WC box and the wall behind the stand


def light_colour(plate, ids):
    """the light's colour at the floor, from the plate's plaster (which reads #ECE5DA's a/b) on the low walls beside the mat,
    normalised to unit luminance. The stone in the plate reads cooler than #D8C8AE (b* about 11 against 15; B2's 7.7), so the
    floor gives the light's intensity only"""
    y0, y1, x0, x1 = LOWWALL_BOX
    sel = np.zeros(ids.shape, bool)
    sel[y0:y1, x0:x1] = True
    sel &= np.isin(ids, PLASTER)
    c = np.median(C.lin(plate[sel]), 0) / C.hex_lin(PLASTER_HEX)
    return c / (c @ YW), int(sel.sum())


def mat_reading(rgb, a8, plate, ids):
    """R5 on the floor: the mat's mid-tone median (linear; L* 20-80th percentile of its solid body, eroded 3) over the light
    falling on it: its intensity from the plate's floor in a 10-40 px ring round the mat (floor ids 9, 10; luminance over the
    stone's), its colour from the plaster beside it (light_colour). rgb and plate graded, 0-1. Returns Lab, ring px"""
    m = C.ero(a8 == 255, 3)
    ring = C.dil(m, 40) & ~C.dil(a8 > 0, 10) & np.isin(ids, (9, 10))
    p = rgb[m]
    L = G.to_lab(p)[:, 0]
    lo, hi = np.percentile(L, [20, 80])
    med = np.median(C.lin(p[(L >= lo) & (L <= hi)]), 0)
    inten = (np.median(C.lin(plate[ring]), 0) @ YW) / (C.hex_lin(STONE) @ YW)
    c, _ = light_colour(plate, ids)
    lab = G.to_lab(C.srgb(np.clip(med / (inten * c), 0, 1))[None])[0]
    return lab, int(ring.sum())


def mat_relight(rgb, a, plate8, ids, sig=30.0, lo=0.3, hi=3.0):
    """the render lit the mat's right half far brighter than the floor beside it and washed it to a near-white (low chroma):
    the mat's large-scale colour and light (per channel, linear, sigma 30 px over its body eroded 8 px, carried out to the
    edges) become the photo's khaki in the plate's floor light under it (the plate has the bare floor there: its light colour
    is the floor's over the stone's albedo); only what is finer than that (the tufts, the band's grooves, the edges) is the
    render's. The level is then set by R5"""
    w = C.ero(a > 0.5, 8).astype(np.float64)
    nw = np.maximum(C.blur(w, sig), 1e-6)
    lr = C.lin(rgb)
    lp = C.lin(plate8.astype(np.float64) / 255)
    lowr = np.stack([C.blur(lr[..., i] * w, sig) / nw for i in range(3)], -1)
    lowp = np.stack([C.blur(lp[..., i] * w, sig) / nw for i in range(3)], -1)
    c, _ = light_colour(plate8.astype(np.float64) / 255, ids)
    E = (lowp @ YW / (C.hex_lin(STONE) @ YW))[..., None] * c
    want = E * C.lin(G.from_lab(np.array([MAT_KHAKI]))[0])
    g = np.clip(want / np.maximum(lowr, 1e-6), lo, hi)
    body = w > 0
    Y = np.array([0.2126, 0.7152, 0.0722])
    rb, rf = lowr @ Y, lowp @ Y
    out = C.srgb(np.clip(lr * g, 0, 1))
    lab_low = G.to_lab(C.srgb(np.clip(lowr[body] / E[body], 0, 1)))
    return out, dict(method="the mat's large-scale colour and light (per channel, linear, sigma 30 px over its body) set to the photo's khaki "
                            "in the light under it (intensity: the plate's bare floor there over the stone's luminance; colour: the plaster "
                            "beside it, light_colour); the tufts, grooves and edges kept "
                            "(finer than 30 px); level by R5 after", sigma_px=sig,
                     light_p95_over_p5_render=round(float(np.percentile(rb[body], 95) / np.percentile(rb[body], 5)), 3),
                     light_p95_over_p5_floor=round(float(np.percentile(rf[body], 95) / np.percentile(rf[body], 5)), 3),
                     render_albedo_chroma_p5_p50_p95=[round(float(v), 1) for v in np.percentile(np.hypot(lab_low[:, 1], lab_low[:, 2]), [5, 50, 95])],
                     gain_p1_p50_p99=[[round(float(v), 3) for v in np.percentile(g[a > 0][:, i], [1, 50, 99])] for i in range(3)])


def mat_recolour(rgb, a8, plate8, ids, target, n=4):
    """a per-channel linear gain on the whole mat (its shading and tufts kept) until its R5 reading is the photo's"""
    pl = plate8.astype(np.float64) / 255
    before, nring = mat_reading(rgb, a8, pl, ids)
    gain = np.ones(3)
    out = rgb
    for _ in range(n):
        lab, _ = mat_reading(out, a8, pl, ids)
        gain = gain * C.lin(G.from_lab(np.array([target]))[0]) / C.lin(G.from_lab(np.array([lab]))[0])
        out = C.srgb(np.clip(C.lin(rgb) * gain, 0, 1))
    after, _ = mat_reading(out, a8, pl, ids)
    clipped = int(((C.lin(rgb) * gain).max(-1)[a8 > 0] > 1).sum())
    de = lambda x: round(float(G.de00(np.array([x]), np.array([target]))[0]), 2)  # noqa: E731
    return out, dict(method="R5 after the grade: mid-tone median of the mat's solid body over the light on it (intensity from the plate's "
                            f"floor ring 10-40 px, ids 9-10, over the stone {STONE}'s luminance; colour from the plaster beside it); "
                            "a per-channel linear gain on the whole mat, the render's shading kept",
                     light_colour=[round(float(v), 4) for v in light_colour(pl, ids)[0]], plaster_px=light_colour(pl, ids)[1],
                     target_photo=list(target), ring_px=nring, before=[round(float(v), 1) for v in before], de00_before=de(before),
                     after=[round(float(v), 1) for v in after], de00_after=de(after), gain_linear=[round(float(v), 4) for v in gain],
                     clipped_px=clipped)


KNEE, TOP = 0.6, 0.95                               # the curtain's shoulder: linear luminance (L* 81.8), towards L* 98


SHOULDER = ("shower-curtain", "candle", "reed-diffuser")


def shoulder_src(locked, g0, g, M, cv):
    """the window light on the pale products that face it: the relight (about x1.5) and the tone match (about x1.25) on the
    raw clip the sunlit linen (about 40 % of the curtain to white; B2's same panel 13 %) and the white candle cup's lit side
    (its ribs lost). For these (SHOULDER) the luminance, unclipped, goes through a soft shoulder (above Y 0.6, tanh towards
    0.95, L* 98) instead of the clip, so the weave and the ribs stay; a*/b* are the raw's (as the relight). Only their own
    layers use it; the cuts and the shadows are measured on the common src"""
    yt = (C.lin(locked) * g0[..., None] * g) @ YW
    ys = np.where(yt <= KNEE, yt, KNEE + (TOP - KNEE) * np.tanh((yt - KNEE) / (TOP - KNEE)))
    lab = G.to_lab(locked)
    f = np.cbrt(np.clip(ys, 0, 1))
    lab[..., 0] = np.where(ys > 216 / 24389, 116 * f - 16, ys * 24389 / 27)
    out = G.from_lab(lab)
    rec = dict(method=f"luminance unclipped (raw x relight x tone gain) through a tanh shoulder above Y {KNEE} towards {TOP} instead of "
                      "the clip; a*/b* the raw's", knee_Y=KNEE, top_Y=TOP, products=list(SHOULDER))
    for k in SHOULDER:
        zone = C.ero(M[k], 3)
        q = cv(out)[zone]
        rec[k] = dict(L_p5_p50_p95=[round(float(v), 1) for v in np.percentile(G.to_lab(q)[:, 0], [5, 50, 95])],
                      over_1_unclipped_share=round(float((yt[zone] > 1).mean()), 3))
    return out, rec


LIGHT_BOX = (1020, 60, 1420, 900)                   # round the drawn block: its two V's


def refit_affine(k, f, ids, src):
    """the drawn product scaled to the clay's size: the sconce block by its height about its centre, onto the clay block's centre;
    the planter by the pot's widest row (its belly, the pothos above it excluded) about its foot's centre, onto the clay pot's"""
    ys, xs = np.nonzero(f)
    if k == "wall-sconce":
        cm = ids == 60
        cy_, cx_ = np.nonzero(cm)
        s = (cy_.max() - cy_.min() + 1) / (ys.max() - ys.min() + 1)
        a = ((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)
        A = ((cx_.min() + cx_.max()) / 2, (cy_.min() + cy_.max()) / 2)
    else:
        wd = POT["belly_px"]                                                    # the drawn belly, measured at 2x
        cm = ids == 51
        cy_, cx_ = np.nonzero(cm)
        # the clay pot is partly behind the brush and the bin from B1: its belly width is the projection of the SKU's 31 cm at the
        # slot (4.95, 10.20), not the visible clay pixels
        from b1proj import FW
        dep = (4.95 - 3.80) * 0.374607 + (10.20 - 13.20) * -0.927184
        wc = (24 / 36 * FW) * 0.31 / dep
        s = wc / wd
        a = POT["foot"]
        # scaled about its own foot, where the model stood it (about 14 cm right of the slot point): moved back onto (4.95, 10.20)
        # it would stand behind the bin and lose its drawn shadow; the designer is told
        A = a
    Mk = np.float32([[s, 0, A[0] - s * a[0]], [0, s, A[1] - s * a[1]]])
    return Mk, dict(scale=round(float(s), 4), drawn_anchor=[round(float(v), 1) for v in a], clay_anchor=[round(float(v), 1) for v in A],
                    drawn_bbox=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                    anchor="block centre, onto the clay block" if k == "wall-sconce" else "its own foot centre (kept where drawn)")


POT = dict(cx=1449.0, rows=[(1146, 97), (1150, 98.5), (1180, 104), (1210, 109), (1240, 113), (1265, 114), (1290, 108), (1310, 96),
                             (1325, 80), (1333, 62), (1336, 40)], belly_px=227.0, foot=(1449.0, 1334.0))


def pot_profile(H, W):
    """the pot as the model drew it (read off the render at 2x: rim y 1147-1160, belly 227 px at y 1250-1270, foot y 1333,
    centre x 1449): a solid of revolution's silhouette, half-width interpolated per row"""
    ys = np.array([r for r, _ in POT["rows"]], float)
    hw = np.array([w for _, w in POT["rows"]], float)
    m = np.zeros((H, W), bool)
    for y in range(int(ys[0]), int(ys[-1]) + 1):
        h = np.interp(y, ys, hw)
        m[y, int(round(POT["cx"] - h)):int(round(POT["cx"] + h)) + 1] = True
    return m


def keep_components(fg, seeds):
    n, lab = cv2.connectedComponents(fg.astype(np.uint8), connectivity=8)
    keep = set(np.unique(lab[seeds & fg])) - {0}
    return np.isin(lab, list(keep)) if keep else fg


def graded_shadow(s, below, cv):
    sg = np.ones(s.shape)
    m = s < 1
    if m.any():
        b = below[m]
        sg[m] = np.clip(cv(b * s[m][:, None]).mean(1) / np.maximum(cv(b).mean(1), 1e-4), 0, 1)
    return sg


def stack(plate, layers, order, light=None):
    out = plate.astype(np.float64) / 255
    for k in order:
        out = C.compose_one(out, *layers[k])
    if light is not None:
        out = C.light_one(out, light)
    return out


def main(rawp):
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    cv = lambda x: G.curve_apply(x, curve)[0]  # noqa: E731
    base = np.asarray(Image.open(os.path.join(ST, "raw", "plate-relit.png")).convert("RGB")).astype(np.float64) / 255
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    H, W = base.shape[:2]
    ids = np.asarray(Image.open(CLAY + "B1-id.png"))
    M = masks(ids)
    allm = np.zeros((H, W), bool)
    for m in M.values():
        allm |= m
    rec = {}
    # 1. lock against the input
    raw = C.load(os.path.join(ST, rawp), (H, W))
    tmp = SCR + "defaults-in.png"
    Image.fromarray(C.q(raw)).save(tmp)
    a_, b_, c_, used = LK.lock(tmp, os.path.join(ST, "inputs", "defaults-input.png"), SCR + "defaults-lock.json")
    src = LK.warp(raw, a_, b_, c_)
    rec["lock"] = dict(y_offset_px=round(a_, 3), y_scale_about_row_707=round(b_, 6), x_offset_px=round(c_, 3), used=used)
    # the clay's local light (beams, shadows) for the envelopes
    b1, pl = PD.load_exr(PD.EXR + "B1.exr"), PD.load_exr(PD.EXR + "B1-plate.exr")
    ra = cv2.GaussianBlur(((b1 + 1e-4) / (pl + 1e-4)).mean(2).astype(np.float32), (0, 0), 3).astype(np.float64)
    clay_shadow = ra < 0.97
    sc = M[LIGHT_SLOT]
    ys, xs = np.nonzero(sc)
    near = np.zeros((H, W), bool)
    near[max(0, ys.min() - 420):ys.max() + 420, max(0, xs.min() - 220):xs.max() + 220] = True
    beam = (ra > 1.05) & np.isin(ids, PLASTER + (5,)) & near
    light_env = C.dil(beam, 30) & ~C.dil(allm, 2) & near
    glass = C.dil(ids == 31, 12)
    # 2. tone match
    keep = ~C.dil(allm, 60) & ~C.dil(light_env, 20) & ~glass & ~C.dil(clay_shadow & C.dil(allm, 80), 10)
    import compose_b1_plate as CPL
    src_locked = src.copy()
    src, g0 = CPL.relight(src, C.load(CLAY + "B1-plate.png"), ids, gmax=2.4, gmin=0.6)
    rec["relight_p5_p50_p95"] = [round(float(v), 3) for v in np.percentile(g0, [5, 50, 95])]
    src = CPL.plaster_ab(src, ids)
    g = gain_field(src, base, keep, 0.75, 1.35)
    src = C.srgb(C.lin(src) * g)
    rec["gain_p1_p50_p99"] = [round(float(v), 3) for v in np.percentile(g, [1, 50, 99])]
    src_sh, rec["shoulder"] = shoulder_src(src_locked, g0, g, M, cv)
    # 3. the cuts
    d = np.linalg.norm(C.lab_of(src) - C.lab_of(base), axis=-1)
    fg = {}
    order = sorted(SLOTS, key=lambda k: (SLOTS[k]["z"], k))
    for k in order:
        s = SLOTS[k]
        m = M[k]
        zone = C.dil(m, s["margin"])
        hard = np.zeros((H, W), bool)
        for o in SLOTS:
            if o != k:
                hard |= C.ero(M[o], 2) & ~C.dil(m, 2)
        sure = C.ero(m, 3) & (d > 6)
        if sure.sum() < 30:
            sure = C.ero(m, 2)
        prob = C.dil(m, 3)
        if k == "floor-planter":                        # the pot reads like the stone behind it: its drawn profile, measured
            pot = pot_profile(H, W)
            lab_ = C.lab_of(src)
            leafbox = np.zeros((H, W), bool)
            leafbox[1010:1192, 1298:1608] = True
            leaves = leafbox & (lab_[..., 1] < -3) & (lab_[..., 2] > 2)
            leaves = cv2.morphologyEx(leaves.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
            sure = C.ero(pot, 6) | C.ero(leaves, 1)
            prob = C.dil(pot, 4) | (leafbox & C.dil(leaves, 10))
            zone = C.dil(prob, 10)
            hard = hard & ~zone
            f = C.gc_cut(src, sure, prob, zone, hard | ~zone)
            f = keep_components(f, sure)
            # among the leaves, the stone and plaster seen between them is not the plant: nothing lighter than L* 72 that is not green
            gap = leafbox & ~C.dil(pot, 4) & (lab_[..., 0] > 72) & ~((lab_[..., 1] < -3) & (lab_[..., 2] > 2))
            f &= ~gap
            # nor the render's wall in the drawn pot's shadow (grey-pink, under the leaves at the left rim, a ghost wedge on
            # the plate's wall once the pot is refitted): off the pot, only what is green (leaf and its sheen) or dark (the
            # foliage's depth) is the plant, closed by 3 px for the leaf edges
            offbox = np.zeros((H, W), bool)
            offbox[1010:1250, 1290:1610] = True          # the leaves' box and down to the pot's shoulder
            leafy = offbox & (((lab_[..., 1] < -1.5) & (lab_[..., 2] > 0)) | (lab_[..., 0] < 38))
            leafy = cv2.morphologyEx(leafy.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
            wedge = offbox & ~C.dil(pot, 3) & ~leafy & f
            f &= ~wedge
            rec["planter_wall_removed_px"] = int(wedge.sum())
            f = cv2.morphologyEx(f.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
            fg[k] = keep_components(f, sure & f) | C.ero(pot, 2)
            rec.setdefault("cut", {})[k] = dict(clay_px=int(m.sum()), alpha_px=int(fg[k].sum()), sure_px=int(sure.sum()), method="the drawn pot's profile + the pothos's green, GrabCut in a band")
            continue
        if k == "toilet-brush":                         # drawn beside the clay: its measured outline (no cut)
            fg[k] = brush_shape(H, W)
            rec.setdefault("cut", {})[k] = dict(clay_px=int(m.sum()), alpha_px=int(fg[k].sum()), method="the drawn cup and rod, measured at 3x")
            continue
        if k in RECT:                                   # drawn bigger than / beside the clay: the drawn box is the zone
            x0, y0, x1, y1 = RECT[k]["rect"]
            prob = np.zeros((H, W), bool)
            prob[y0:y1, x0:x1] = True
            zone = C.dil(prob, 14)
            sure = core_of(k, src, prob)
            hard = hard & ~prob
        if k == "bath-mat":                             # the stone round it is nearly the mat's own colour: the drawn quad, measured
            quad = mat_quad(H, W)
            prob, zone, sure = quad, C.dil(quad, 6), C.ero(quad, 6)
            hard = hard | ~zone
            rec["mat_quad"] = dict(corners=MAT_QUAD, px=int(quad.sum()), clay_px=int(m.sum()), area_vs_clay=round(float(quad.sum() / m.sum()), 3),
                                   method="the four corners of the drawn mat measured at 2x on r1; GrabCut only in a 6 px band round it (the tufts)")
        f = C.gc_cut(src, sure, prob, zone, hard)
        if k == "bath-mat":
            f &= C.dil(quad, 3)
        if k == "reed-diffuser":                        # the black reeds over the bright glass: dark thin lines joined to the lid
            lab_ = C.lab_of(src)
            rb = np.zeros((H, W), bool)
            rb[590:730, 860:940] = True
            frame = cv2.warpAffine((ids == 30).astype(np.uint8), np.float32([[1, 0, -8], [0, 1, 0]]), (W, H), flags=cv2.INTER_NEAREST) > 0
            reeds = rb & (lab_[..., 0] < 45) & ~C.dil(frame, 3) & (np.hypot(lab_[..., 1], lab_[..., 2]) < 8)   # black, not the bronze frame
            n_, l_ = cv2.connectedComponents((reeds | C.dil(f, 2)).astype(np.uint8), connectivity=8)
            reeds &= np.isin(l_, list(set(np.unique(l_[f])) - {0}))
            f |= reeds
        if k == "shower-curtain":                       # at the hem the floor is lit like the fabric: the clay's outline, grown 12
            low = np.zeros((H, W), bool)
            low[1440:] = True
            f &= ~(low & ~C.dil(m, 12))
            # below row 1260 the sunlit side hem reads like the floor and the cut broke (a 3 px sliver, steps of 12 and 10 px):
            # the side's own line (rows 600-1260, fitted) is carried down to the hem; right of it the curtain, left of it not
            yy = np.arange(600, 1260)
            xl = np.array([1650 + int(np.argmax(f[y, 1650:1900])) for y in yy])
            b_, a_ = np.polyfit(yy, xl, 1)
            for y in range(1260, H):
                x_line = int(round(a_ + b_ * y))
                body = np.nonzero(f[y, x_line + 3:1990])[0]
                if not len(body):
                    continue
                f[y, 1650:x_line] = False
                f[y, x_line:x_line + 3 + body[0]] = True
            rec["curtain_side"] = dict(fit_rows=[600, 1260], x_at_1260=round(float(a_ + b_ * 1260), 1), x_at_1486=round(float(a_ + b_ * 1486), 1),
                                       slope_px_per_row=round(float(b_), 4))
        fg[k] = keep_components(f, sure)
        if k == "bin":                                  # a cylinder: its outline is its cut's convex hull (the clay brush's rod,
            fg[k] = hull_of(fg[k])                      # 10 px right of the drawn one, had cracked it); behind the drawn brush
            behind = fg[k] & C.dil(brush_shape(H, W), 2)                 # the wood is filled in from round it
            box_ = np.nonzero(fg[k])
            y0_, y1_, x0_, x1_ = box_[0].min() - 8, box_[0].max() + 9, box_[1].min() - 8, box_[1].max() + 9
            src_bin = src.copy()
            src_bin[y0_:y1_, x0_:x1_] = cv2.inpaint(C.q(src[y0_:y1_, x0_:x1_]), (behind | ~fg[k])[y0_:y1_, x0_:x1_].astype(np.uint8), 6,
                                                    cv2.INPAINT_TELEA).astype(np.float64) / 255
            src_bin = np.where(behind[..., None], src_bin, src)
            rec["bin_behind_brush_px"] = int(behind.sum())
        rec.setdefault("cut", {})[k] = dict(clay_px=int(m.sum()), alpha_px=int(fg[k].sum()), sure_px=int(sure.sum()))
    np.savez_compressed(SCR + "b1-fg.npz", **{k.replace("-", "_"): v for k, v in fg.items()})
    allfg = np.zeros((H, W), bool)
    for k in order:
        allfg |= fg[k]
    AFF = {k: refit_affine(k, fg[k], ids, src) for k in REFIT}
    rec["refit"] = {k: v[1] for k, v in AFF.items()}
    # the others' shadows are blocked by where a refitted product ends up, not where it was drawn
    placed = {k: (cv2.warpAffine(fg[k].astype(np.uint8), AFF[k][0], (W, H), flags=cv2.INTER_NEAREST) > 0) if k in AFF else fg[k] for k in order}
    allplaced = np.zeros((H, W), bool)
    for k in order:
        allplaced |= placed[k]
    # 4. layers and shadows, graded
    layers, files = {}, {}
    os.makedirs(os.path.join(ST, "layers"), exist_ok=True)
    os.makedirs(os.path.join(ST, "shadows"), exist_ok=True)
    for k in order:
        s = SLOTS[k]
        oth = allplaced & ~placed[k] if k not in AFF else allfg & ~fg[k]
        if k in ("bin", "toilet-brush"):                # the drawn (oversize) pothos's leaves beside the bin's lid read as the
            oth = oth | fg["floor-planter"]             # bin's shadow (a grey blot above the lid): blocked where drawn too
        sh = C.shadow_of(src, base, fg[k], dict(band=s["band"], rim=s["rim"]), clay_shadow, C.dil(oth, 1))
        a = C.soft(fg[k])
        rgb = cv(C.defringe(src_sh if k in SHOULDER else src_bin if k == "bin" else src, fg[k]))
        sg = graded_shadow(sh, base, cv)
        if k in AFF:                                    # drawn oversize: scaled to the clay (the SKU's size), as B2's refits
            Mk = AFF[k][0]
            a = cv2.warpAffine(a.astype(np.float32), Mk, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
            rgb = cv2.warpAffine(rgb.astype(np.float32), Mk, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT).astype(np.float64)
            sg = 1 - cv2.warpAffine((1 - sg).astype(np.float32), Mk, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
            a[a < 0.02] = 0
        if k == "bath-mat":                             # drawn ~9 % short in depth (~54 of 60 cm): the drawn quad onto the clay's (the SKU's 40 x 60)
            PM = cv2.getPerspectiveTransform(np.float32(MAT_QUAD), np.float32(MAT_CLAY))
            a = cv2.warpPerspective(a.astype(np.float32), PM, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
            rgb = cv2.warpPerspective(rgb.astype(np.float32), PM, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float64)
            sg = 1 - cv2.warpPerspective((1 - sg).astype(np.float32), PM, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
            a[a < 0.02] = 0
            rec["mat_quad"].update(refit="homography, the drawn quad onto the clay's quad (layer, alpha and shadow)", clay_corners=MAT_CLAY,
                                   screen_h_ratio_drawn_vs_clay=round((1524.0 - 1349.0) / (1526.0 - 1334.0), 3))
        if k == "bath-mat":                             # the render's near-white pool on the right half: the floor's light instead
            rgb, rec["mat_light"] = mat_relight(rgb, a, plate8, ids)
        if k == "bath-mat":                             # R5 (as B2's M1 / T3): the render's own tuft shading, the photo's khaki
            rgb, rec["mat_recolour"] = mat_recolour(rgb, C.q(a), plate8, ids, MAT_KHAKI)
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        s8 = C.q(sg)
        lp = os.path.join("layers", k, s["pid"] + ".png")
        spth = os.path.join("shadows", k, s["pid"] + ".png")
        os.makedirs(os.path.join(ST, "layers", k), exist_ok=True)
        os.makedirs(os.path.join(ST, "shadows", k), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(os.path.join(ST, lp))
        Image.fromarray(s8).save(os.path.join(ST, spth))
        layers[k] = (rgba, s8)
        files[k] = (lp, spth)
    # 5. the light (screen), on the graded stack
    # the beams as drawn, round the drawn block, on the plaster only; measured against the plate (plate8, graded) and the other
    # products' layers as they stand unscaled at that place: none there but the block itself
    srcg = cv(src)
    pg = plate8.astype(np.float64) / 255
    Lg = 1 - (1 - srcg) / np.maximum(1 - pg, 1e-3)
    Lg = np.clip(np.stack([C.blur(Lg[..., i], 2.0) for i in range(3)], -1), 0, 1)
    x0, y0, x1, y1 = LIGHT_BOX
    env = np.zeros((H, W), bool)
    env[y0:y1, x0:x1] = True
    env &= np.isin(ids, PLASTER + (5,)) & ~C.dil(allfg & ~fg[LIGHT_SLOT], 6) & ~C.dil(fg[LIGHT_SLOT], 1)
    env &= ~C.dil(np.isin(ids, (12, 11, 13)), 6)
    # the plaster round the beams reads a little brighter in the render than in the plate (the tone match is smooth): that
    # baseline (the box's median outside the beams) is taken off, so only the beams are light
    lum = Lg.mean(2)
    basel = float(np.median(lum[env & (lum < np.percentile(lum[env], 60))])) if env.any() else 0.0
    Lg = np.clip(Lg - basel, 0, 1)
    fe = np.clip(C.blur(env.astype(np.float64), 8), 0, 1) * env
    # and the glow fades smoothly away from the drawn block (no box edge): an elliptical falloff round its centre
    bys, bxs = np.nonzero(fg[LIGHT_SLOT])
    yy_, xx_ = np.mgrid[0:H, 0:W]
    fall = np.exp(-(((xx_ - bxs.mean()) / 110.0) ** 2 + ((yy_ - bys.mean()) / 240.0) ** 2) / 2)
    Lg = Lg * (fe * fall)[..., None]
    Lg[Lg.max(2) < 0.02] = 0
    rec["light_baseline_removed"] = round(basel, 4)
    if LIGHT_SLOT in AFF:
        Lg = cv2.warpAffine(Lg.astype(np.float32), AFF[LIGHT_SLOT][0], (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
        Lg[Lg.max(2) < 0.015] = 0
        Lg *= (~(layers[LIGHT_SLOT][0][..., 3] == 255))[..., None]
    L8 = C.q(Lg)
    os.makedirs(os.path.join(ST, "light"), exist_ok=True)
    lpth = os.path.join("light", SLOTS[LIGHT_SLOT]["pid"] + ".png")
    Image.fromarray(L8).save(os.path.join(ST, lpth))
    # 6. the composite from the files, RND2
    o = stack(plate8, layers, order, L8)
    o8 = C.q(o)
    Image.fromarray(o8).save(os.path.join(ST, "b1-defaults.png"))
    C.frame_png(o8, os.path.join(ST, "b1-defaults-frame.png"))
    region = L8.max(2) > 0
    for k in order:
        region |= (layers[k][0][..., 3] > 0) | (layers[k][1] < 255)
    rnd2 = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    man = dict(frame="B1", room="bath", style="warm-modern", date="2026-11-19", canvas=[W, H], base="plate.png",
               frame_box=[round(v, 2) for v in G.FRAME], grade="plate-grade.json (B2's WM-G1 curve) on every file",
               compose=dict(order=["base"] + [f"{k}-shadow, {k}" for k in order] + ["light (screen)"],
                            formula="out = round((below * shadow / 255) * (1 - a) + rgb * a), straight alpha; then the light: "
                                    "out = 255 - round((255 - out) * (255 - L) / 255)"),
               layers=[dict(slot=k, product=SLOTS[k]["pid"], card=SLOTS[k]["card"], sku=SLOTS[k]["sku"], z=SLOTS[k]["z"], shadow_z=SLOTS[k]["z"] - 1,
                            default=True, layer=files[k][0], shadow=files[k][1], alpha_px=int((layers[k][0][..., 3] > 0).sum()),
                            shadow_px=int((layers[k][1] < 255).sum())) for k in order],
               light=dict(product=SLOTS[LIGHT_SLOT]["pid"], file=lpth, z=90, blend="screen", px=int((L8.max(2) > 0).sum())),
               variants=[], rnd2=dict(region_px=int(region.sum()), outside_differing_px=rnd2,
                                      rule="outside every alpha, shadow and light: plate.png, pixel for pixel"),
               gaps_left_empty=["shower-stool", "wall-art", "ledge-planter"], record=rec)
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(rnd2=rnd2, lock=rec["lock"], gain=rec["gain_p1_p50_p99"], cut=rec["cut"], light_px=man["light"]["px"])))


if __name__ == "__main__":
    main(sys.argv[1])
