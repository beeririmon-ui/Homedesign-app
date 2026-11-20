#!/usr/bin/env python3
"""
work_compose.py: the W0 layers from the nano passes, and the W0 frame (render-agent, 2026-11-20; 0 tokens beyond the passes).
MB1's compositor (master mb1-2026-11-19/tools/mb1_compose.py), made generic for the work room. Per pass (passes.json: the raw edit, its
input, and the base the input was made from):
  1. lock: ECC affine of the edit onto its input, masked to the clay's architecture and fixed furniture outside the pass's zone;
  2. MP-I1: the gain field (sigma 60, the MB0 compositor's) against the base outside the zone and the lamps' glow;
  3. cut: what the edit changed on the base inside the zone (dE76 > 7 on a 1 px blur), GrabCut-refined, holes filled; a change of
     brightness only on the walls, the floor or the fixed walnut is light or shadow, not object; each pixel goes to one product of the
     pass by the nearest clay region; per product the cut is bounded to its clay region (BOUND px round it);
  4. shadow: the edit's darkening of the base in a band round each product, never on a product, never on the view (multiply, z - 1);
  5. light: for the lit lamps, the edit's brightening of the base outside every product, as a screen layer (z 90);
  6. MP-I2 / WM-G1: the plate's toe (plate-compose.json, step 3) on the new layers' L*, once, if the plate applied one.
Then the frame: plate.png, the layers in z order (each shadow, then the layer), the lights times (1 - every alpha): outside every alpha,
shadow and light nothing differs from plate.png (RND2).
  python3 work_compose.py <pass> ...     (each pass replaces its layers in layers/manifest.json and recomposes)
  python3 work_compose.py compose        (recompose only)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
CARD = "framed-art-aliexpress-misty-landscape-386242-work"
P = {   # clay id: (slot, product id (card + option), z, pass)
    41: ("framed-art", f"{CARD}-08-30x40", 12, "pA-wall"),
    53: ("bookends", "bookends-aliexpress-solid-beech-arch-bookends-with-black-steel-9-black-walnut", 44, "pA-wall"),
    55: ("shelf-vase", "vase-cj-coarse-sand-white-tall", 44, "pA-wall"),
    56: ("shelf-object", "bowl-cj-burnt-paulownia-footed-bowl-23-fire-color", 44, "pA-wall"),
    63: ("pendant", "pendant-cj-silk-ribbed-pumpkin-40-30cm-warm", 80, "pA-wall"),
    47: ("basket", "basket-cj-two-tone-rope-jute-white-30", 30, "pB-desk"),
    48: ("waste-basket", "waste-basket-aliexpress-washable-kraft-paper-bin-25x40-brown-xl", 30, "pB-desk"),
    57: ("desk-tray", "pool-cj-travertine-organic-tray-24", 44, "pB-desk"),
    58: ("desk-organizer", "desk-organizer-cj-cave-stone-pen-cup-8x11-cream-yellow", 46, "pB-desk"),
    60: ("desk-vase", "vase-cj-faceted-cream-large", 44, "pB-desk"),
    61: ("desk-candle", "nightstand-objects-foxhome-hiba-ceramic-candle-500g-cream", 46, "pB-desk"),
    62: ("desk-dish", "trinket-dish-aliexpress-retro-raw-rim-dish-8-5-style-a", 46, "pB-desk"),
    40: ("curtains", "curtains-aliexpress-linen-blend-s-fold-180502", 10, "pC-sides"),
    43: ("framed-art-2", f"{CARD}-03-30x40", 13, "pC-sides"),
    45: ("wall-sconce", "wall-sconce-cj-travertine-cube-updown-12-type-a-indoor", 14, "pC-sides"),
    49: ("planter", "planter-cj-cement-ribbed-belly-beige-large-rhapis", 32, "pC-sides"),
    51: ("magazine-holder", "magazine-holder-cj-gunmetal-leather-strap-orange", 36, "pC-sides"),
    46: ("rug", "rug-cj-braided-wool-natural-160x230", 20, "pD-front"),
    64: ("chair-throw", "throw-cj-cotton-linen-light-gray-200x230-brown", 60, "pD-front"),
}
FILLERS = {42: 41, 44: 43, 50: 49, 52: 51, 54: 53, 59: 58}
LAMPS = {"pA-wall": [63], "pC-sides": [45]}
ZONE_PAD = {63: 40, 41: 20, 49: 60, 50: 70, 40: 40, 64: 50, 46: 40, 47: 25, 48: 25, 51: 30, 53: 20, 55: 20, 56: 20}
BOUND = {57: 20, 58: 24, 59: 24, 60: 20, 61: 20, 62: 16, 45: 18, 53: 18, 55: 18, 56: 18, 63: 26, 41: 14, 43: 14, 47: 24, 48: 24, 51: 26}
LIGHT_COLOURED = (41, 42, 43, 44, 45, 55, 57, 58, 60, 61, 63, 40, 46)      # cream / white / pale products on the plaster or the oak: exempt
SURF = (1, 2, 4, 5, 9, 10, 11, 17, 18)                                      # walls and floor
WAL = (20, 21, 22, 23, 24, 25, 26)                                          # the fixed walnut and the seat
SPECIAL = {}                                                                # per-pass hooks (filled below after the edits were seen)
# the clay-seeded cut (after pA: the model drew each product on its placeholder, so its own clay region is the prior):
# clay id: (outer band px, convex hull)
CLAYCUT = {41: (6, True), 43: (20, True), 53: (40, False), 55: (10, True), 56: (16, False), 63: (5, False),
           57: (8, True), 58: (8, False), 60: (8, True), 61: (45, True), 62: (6, True), 47: (10, True), 48: (10, False),
           40: (14, False), 45: (6, True), 49: (60, False), 51: (60, False), 46: (20, False), 64: (16, False)}
SHADOW_ON = {"pA-wall": (17, 24), "pB-desk": (17, 20, 21, 9, 10, 11), "pC-sides": (1, 2, 4, 5, 9, 10, 11), "pD-front": (10, 11), "pD-throw": (25, 26)}
SHADOW_BAND = 30
# sizes fixed in code against the card (as B1 / MB1): (pass, clay id) -> how. 'whole': the layer scaled (sx, sy) about its foot (bottom
# centre); 'parts': each connected piece of the given colour class scaled about its own foot
SIZEFIX = {("pA-wall", 56): dict(mode="whole", sx=118 / 126, sy=46 / 57,
                                 why="the bowl came 126 x 57 px against the clay's 118 x 46 (the card's 23 x 9): 24 % too tall"),
           ("pC-sides", 51): dict(mode="rack", why="the rack came about 48 cm wide (the card's 35): scaled uniformly to the card's front (191 px at "
                                                      "Y 6.71) about its foot; the foot set at X 0.32 (0.095 right of 3.2's place) for a 0.022 gap to the desk panel"),
           ("pC-sides", 43): dict(mode="frame2", why="frame 2 came about 23 % too tall"),
           ("pA-wall", 53): dict(mode="parts", cls="walnut", sx=1.13, sy=1.13,
                                 why="the two arch bookends came about 15 cm tall against the card's 17 (75 px against 86): scaled 1.13 about their feet")}


def pass_ids(p):
    J = json.load(open(os.path.join(ST, "passes.json"))).get(p, {})
    ids = list(J["ids"]) if "ids" in J else [k for k, v in P.items() if v[3] == p]     # (after the restart) a pass may cut only some ids
    return ids + [f for f, k in FILLERS.items() if k in ids]


def own(k):
    return [k] + [f for f, o in FILLERS.items() if o == k]


def toe_curve():
    s = json.load(open(os.path.join(ST, "plate-compose.json")))["steps"][2]
    return (s["xp"], s["fp"]) if s.get("applied") else None


def fill_holes(m, max_area):
    inv = (~m).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lb[0], lb[-1], lb[:, 0], lb[:, -1]])))
    return m | np.isin(lb, [i for i in range(1, n) if i not in border and st[i, cv2.CC_STAT_AREA] < max_area])


def light_env(ids, p):
    env = np.zeros((H, W), bool)
    for k in LAMPS.get(p, []):
        env |= C.dil(ids == k, 150 if k == 63 else 130)
    return env


def poly_mask(poly):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32(np.round(np.array(poly, np.float64)))], 1)
    return m.astype(bool)


def gc_poly(e, poly, band):
    dm = poly_mask(poly)
    gc = C.gc_cut(e, C.ero(dm, band), dm, C.dil(dm, band), np.zeros((H, W), bool), iters=8)
    return gc | C.ero(dm, max(2, band // 2 + 1))


def hull_of(m):
    ys, xs = np.nonzero(m)
    if len(xs) < 3:
        return m
    hpts = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32))
    out = np.zeros((H, W), np.uint8)
    cv2.fillPoly(out, [hpts], 1)
    return out.astype(bool)


def gc_clay(e, ids, k, fg):
    """GrabCut seeded by the product's own clay region: sure = the region 3 px in, probable = the region and what the edit changed
    within the band, background beyond the band; holes filled; the convex hull for the convex products (frames, vases, bowls, tray)"""
    outer, hull = CLAYCUT[k]
    km = np.isin(ids, own(k))
    zone = C.dil(km, outer)
    sure = C.ero(km, 3)
    prob = km | (fg & zone)
    hard = zone & ~C.ero(zone, 2)
    m = C.gc_cut(e, sure, prob, zone, hard, iters=6)
    m = fill_holes(m | sure, 20000) & zone
    if hull:
        m = hull_of(m) & zone
    return m


def scale_piece(e, base, piece, sx, sy):
    """scale the edit's pixels of `piece` about its foot (bottom centre); what the piece no longer covers takes the base (so it casts
    no false shadow); returns the new edit and the new piece mask"""
    ys, xs = np.nonzero(piece)
    ax, ay = (xs.min() + xs.max() + 1) / 2.0, float(ys.max() + 1)
    A = np.float32([[sx, 0, ax * (1 - sx)], [0, sy, ay * (1 - sy)]])
    rgb = cv2.warpAffine(e.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    a = cv2.warpAffine(piece.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) > 0.5
    e2 = e.copy()
    gone = piece & ~a
    e2[gone] = base[gone]
    e2[a] = rgb[a]
    return e2, a, dict(anchor=[round(ax, 1), round(ay, 1)], scale=[round(sx, 3), round(sy, 3)], px_before=int(piece.sum()), px_after=int(a.sum()))


def apply_sizefix(p, e, base, layers, lab_e, rp, ids_now=None):
    for (pp, k), F in SIZEFIX.items():
        if pp != p or k not in layers:
            continue
        m = layers[k]
        recs = []
        if F["mode"] == "frame2":
            e, layers[k] = frame2_fit(e, base, m, rp)
            continue
        if F["mode"] == "rack":
            ys, xs = np.nonzero(m)
            arch = np.nonzero(m[RACK_ARCH_ROWS[0]:RACK_ARCH_ROWS[1]].any(0))[0]      # the two arches above the straps: the rack's width
            sc = RACK_FRONT_PX / (arch.max() + 1 - arch.min())
            cx_clay = M.proj(RACK_X, 6.71, 0.0)[0]
            ax, ay = (arch.min() + arch.max() + 1) / 2.0, float(ys.max() + 1)
            A = np.float32([[sc, 0, cx_clay - sc * ax], [0, sc, ay * (1 - sc)]])
            RACK_T.update(A=A, e_pre=e.copy(), m_old=m.copy())                # for the rack's shadow (shadow_overrides)
            rgb = cv2.warpAffine(e.astype(np.float32), A, (W, H), flags=cv2.INTER_AREA).astype(np.float64)
            nm = cv2.warpAffine(m.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) > 0.5
            gone = m & ~nm
            e = e.copy()
            e[gone] = base[gone]
            e[nm] = rgb[nm]
            layers[k] = nm
            rp.setdefault("sizefix", {})[P[k][0]] = dict(why=F["why"], scale=round(float(sc), 3), foot_from=[round(ax, 1), round(ay, 1)],
                                                        foot_to=[round(float(cx_clay), 1), round(ay, 1)], px_before=int(m.sum()), px_after=int(nm.sum()))
            continue
        if F["mode"] == "whole":
            e, nm, r = scale_piece(e, base, m, F["sx"], F["sy"])
            layers[k] = nm
            recs.append(r)
        else:
            L, a_, b_ = lab_e[..., 0], lab_e[..., 1], lab_e[..., 2]
            cls = m & (L < 50) & (np.hypot(a_, b_) > 6)                 # the walnut pieces (the books are pale)
            cls = cv2.morphologyEx(cls.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
            n, lb, st, _ = cv2.connectedComponentsWithStats(cls.astype(np.uint8), 8)
            rest = m.copy()
            for j in [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] > 300 and st[j, cv2.CC_STAT_WIDTH] > 0.4 * st[j, cv2.CC_STAT_HEIGHT]]:
                piece = fill_holes(lb == j, 400)
                e, nm, r = scale_piece(e, base, piece, F["sx"], F["sy"])
                rest = (rest & ~piece) | nm
                recs.append(r)
            layers[k] = rest
        rp.setdefault("sizefix", {})[P[k][0]] = dict(why=F["why"], pieces=recs)
    return e


RACK_T = {}
LAYER_SRC = {}          # clay id -> the RGB a layer is cut from, when it is not the shared edit (the tray, inpainted)
LAYER_RGB = {}          # clay id -> the layer's own RGB after a FIT (the shared edit is never overwritten by a FIT)
FIT_T = {}              # clay id -> dict(A, m_old, foot, w): the FIT transforms, for the shadows
CUP_ROWS = {}
# (2026-11-20, after the restart) FIT: the edit drew four small desk objects 1.2-1.6 times the card; each is scaled uniformly about its
# foot (bottom centre) to the clay's width (the card's, in the camera) and set with its foot on the clay's (centre x, bottom y + 1).
# The cup is measured on its body (not the pencils) and the pencils scale with it. Order: the cup before the tray it stands on
FIT = {("pB-desk", 58): dict(w=43, foot=(1126.0, 882.0), why="the pen cup came 53 px wide against the clay's 43 (the card's 8 cm): x0.81, with its pencils"),
       ("pB-desk", 61): dict(w=95, foot=(1704.0, 888.0), why="the Hiba bowl came 136 px wide against the clay's 95 (the card's 18 cm) and 20 px left: x0.70, onto the clay"),
       ("pB-desk", 62): dict(w=48, foot=(1568.5, 899.0), why="the dish came 77 px wide against the clay's 48 (the card's 8.5 cm): x0.62, onto the clay"),
       ("pB-desk", 57): dict(w=133, foot=(1127.0, 895.0), why="the tray came 207 px long against the clay's 133 (the card's 24 cm): x0.64, onto the clay")}


def apply_fit(p, e, layers, rp):
    for (pp, k), F in FIT.items():
        if pp != p or k not in layers:
            continue
        m = layers[k]
        ys, xs = np.nonzero(m)
        if k == 58 and CUP_ROWS:                                             # the cup's own width, not the pencils'
            bx = np.arange(CUP_ROWS["x0"], CUP_ROWS["x1"] + 1)
        else:
            bx = xs
        w0 = float(bx.max() + 1 - bx.min())
        sc = F["w"] / w0
        ax, ay = (bx.min() + bx.max() + 1) / 2.0, float(ys.max() + 1)
        tx, ty = F["foot"]
        A = np.float32([[sc, 0, tx - sc * ax], [0, sc, ty - sc * ay]])
        src = LAYER_SRC.get(k, e)
        src = C.blur(src, max(0.45 * (1 / sc - 1), 0.01))                       # anti-alias the downscale
        rgb = cv2.warpAffine(src.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
        nm = cv2.warpAffine(m.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR) > 0.5
        LAYER_RGB[k] = rgb
        FIT_T[k] = dict(A=A, m_old=m.copy(), foot=(tx, ty), w=F["w"])
        layers[k] = nm
        rp.setdefault("sizefix", {})[P[k][0]] = dict(why=F["why"], scale=round(float(sc), 3), measured_w=round(w0, 1), target_w=F["w"],
                                                    foot_from=[round(ax, 1), round(ay, 1)], foot_to=[tx, ty], px_before=int(m.sum()), px_after=int(nm.sum()))


def fit_shadows(p, e, base, layers, shadows, pl_ids, rp):
    """the shadows of the FIT objects: the edit's darkening round each as drawn (sigma 3), relative to a ring 30-55 px out, moved and
    scaled with it (full to 10 px, gone at 28), and a contact shadow under its foot (an ellipse 1.1 times its width, at most x0.62);
    the old, larger objects' own shading is never used where they no longer are"""
    if not FIT_T:
        return
    view = np.isin(pl_ids, (0, 15))
    on = np.isin(pl_ids, SHADOW_ON[p]) & ~view
    old = np.zeros((H, W), bool)
    for T in FIT_T.values():
        old |= T["m_old"]
    allfg = np.zeros((H, W), bool)
    for m in layers.values():
        allfg |= m
    valid = on & ~C.dil(old | allfg, 2)
    r = soft_ratio(e, base, valid, 3)
    out = {}
    for k, T in FIT_T.items():
        d_old = cv2.distanceTransform((~T["m_old"]).astype(np.uint8), cv2.DIST_L2, 5)
        ring = valid & (d_old > 30) & (d_old < 55)
        ref = float(np.median(r[ring])) if ring.any() else 1.0
        rr = np.clip(r / max(ref, 1e-3), 0, 1).astype(np.float32)
        rw = cv2.warpAffine(rr, T["A"], (W, H), flags=cv2.INTER_LINEAR, borderValue=1.0).astype(np.float64)
        dk = cv2.distanceTransform((~layers[k]).astype(np.uint8), cv2.DIST_L2, 5)
        s_field = 1 - (1 - np.maximum(rw, 0.55)) * ramp(dk, 10, 28) * C.blur(on.astype(np.float64), 1.0)
        tx, ty = T["foot"]
        el = np.zeros((H, W), np.uint8)
        cv2.ellipse(el, (int(round(tx)), int(round(ty - 2))), (int(round(0.55 * T["w"])), max(3, int(round(0.07 * T["w"])))), 0, 0, 360, 1, -1)
        s_contact = 1 - 0.38 * C.blur(el.astype(np.float64), 2.0)
        sh = np.minimum(s_field, s_contact)
        sh[layers[k]] = 1
        shadows[k] = np.where(sh > 0.996, 1.0, np.clip(sh, 0, 1))
        out[P[k][0]] = dict(ref=round(ref, 3), min=round(float(shadows[k].min()), 3), px=int((shadows[k] < 0.996).sum()))
    rp["fit_shadows"] = out




def soft_ratio(e, base, valid, sig):
    """the edit's darkening of the plate (linear luminance ratio, at most 1), as a smooth field: a normalised blur over the valid pixels
    (plaster, skirting, floor), so the field runs on, unbroken, behind fronds, tubes and the stack (1 where no valid pixel is near)"""
    r = np.clip(C.luma(C.lin(e)) / np.maximum(C.luma(C.lin(base)), 1e-4), 0, 1.0)
    w = valid.astype(np.float64)
    num, den = C.blur(r * w, sig), C.blur(w, sig)
    return np.where(den > 0.02, num / np.maximum(den, 1e-6), 1.0)


def ramp(dist, d0, d1):
    """1 up to d0, a cosine fall to 0 at d1"""
    t = np.clip((dist - d0) / float(d1 - d0), 0, 1)
    return 0.5 + 0.5 * np.cos(np.pi * t)


def shadow_overrides(p, e, base, layers, shadows, pl_ids, rp):
    """(2026-11-20, after the restart) two shadows taken as smooth fields, not as the 30 px band split by nearest product:
      planter: the band (and its split with the curtain and the cube) left hard steps and grey blotches on the corner plaster. The
        edit's darkening round the plant (the palm's soft shadow from the window, to the right and down) as a smooth field (sigma 6),
        full to 60 px from the plant and gone at 180, never on the curtain, the cube or the plant;
      magazine-holder: the edit's darkening round the rack as drawn (sigma 3), moved and scaled with the rack (RACK_T), full to 22 px
        from the rack and gone at 46."""
    view = np.isin(pl_ids, (0, 15))
    allfg = np.zeros((H, W), bool)
    for m in layers.values():
        allfg |= m
    on = np.isin(pl_ids, SHADOW_ON[p]) & ~view
    out = {}
    if p == "pC-sides" and 49 in layers:
        leafish = green_or_dark(C.to_lab(e), C.to_lab(base))                                             # fronds the cut left out
        leafish[int(np.nonzero(M.ids('W0') == 49)[0].min()):] = False       # below the rim only canes: the corner's dark shade is shadow
        valid = on & ~C.dil(allfg, 3) & ~C.dil(leafish & C.dil(layers[49], 40), 3)                       # are not shadow
        r = soft_ratio(e, base, valid, 6)
        dk = cv2.distanceTransform((~layers[49]).astype(np.uint8), cv2.DIST_L2, 5)
        others = np.zeros((H, W))
        for k in (40, 45):
            if k in layers:
                others = np.maximum(others, C.blur(layers[k].astype(np.float64), 1.0))
        s = 1 - (1 - np.maximum(r, 0.65)) * ramp(dk, 60, 180) * (1 - others) * C.blur(on.astype(np.float64), 1.0)
        s[layers[49]] = 1
        shadows[49] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
        out["planter"] = dict(rule="smooth field, sigma 6, at most x0.65, full to 60 px, gone at 180; leaf-coloured pixels are not shadow", min=round(float(shadows[49].min()), 3),
                              px=int((shadows[49] < 0.996).sum()))
    if p == "pC-sides" and 51 in layers and RACK_T:
        valid = on & ~C.dil(RACK_T["m_old"], 2)
        r = soft_ratio(RACK_T["e_pre"], base, valid, 3)
        d_old = cv2.distanceTransform((~RACK_T["m_old"]).astype(np.uint8), cv2.DIST_L2, 5)
        ring = valid & (d_old > 50) & (d_old < 80)                     # the edit's own exposure there, not the rack's shadow
        ref = float(np.median(r[ring])) if ring.any() else 1.0
        r = np.clip(r / max(ref, 1e-3), 0, 1).astype(np.float32)
        rw = cv2.warpAffine(r, RACK_T["A"], (W, H), flags=cv2.INTER_LINEAR, borderValue=1.0).astype(np.float64)
        dk = cv2.distanceTransform((~layers[51]).astype(np.uint8), cv2.DIST_L2, 5)
        s = 1 - (1 - np.maximum(rw, 0.5)) * ramp(dk, 22, 46) * C.blur(on.astype(np.float64), 1.0)
        s[layers[51]] = 1
        shadows[51] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
        out["magazine-holder"] = dict(rule="the edit's darkening round the rack as drawn, relative to a ring 50-80 px out (ref), moved and scaled with it; full to 22 px, gone at 46", ref=round(ref, 3),
                                      min=round(float(shadows[51].min()), 3), px=int((shadows[51] < 0.996).sum()))
    if out:
        rp["shadow_overrides"] = out


CURTAIN_LEAD_X = 380            # a fold crest at u 0.12 (3.2: the stack u 0.12-0.18); the edit drew the sheer wider, over the glass


def curtain_stack(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """the edit drew the sheer as a wide panel over the window (to x ~212); the spec's stack is u 0.12-0.18. The stack is kept from the
    fold crest at x 380 (its leading edge) to the panel's right edge and its hem, found by GrabCut in that strip; left of it the plate's
    window shows"""
    sure = np.zeros((H, W), bool)
    sure[40:1400, 392:488] = True
    zone = np.zeros((H, W), bool)
    zone[0:1500, CURTAIN_LEAD_X:545] = True
    hard = np.zeros((H, W), bool)
    hard[:, 540:545] = True
    hard[1490:1500, CURTAIN_LEAD_X:545] = True
    g = C.gc_cut(e, sure, zone & (d > 2), zone, hard, iters=6)
    n, lb, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), 8)
    g = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    g = fill_holes(g, 50000) & zone
    rp["curtain_stack"] = dict(lead_x=CURTAIN_LEAD_X, px=int(g.sum()), note="the stack cut at its leading fold crest (u 0.12): the edit's panel "
                               "over the glass (x 212-380) is not kept")
    return g


SPECIAL[("pC-sides", 40)] = curtain_stack


def green_or_dark(lab_e, lab_b):
    """leaf colour in the edit: green (h 95-200, C* > 7; the fronds read h 102-124, C* 10-22), or dark (L* < 40) and green, off the
    plate's hue by more than 25 (canes, frond shade), or near black (L* < 22). Dark warm plaster in the corner's shade is not leaf"""
    L, cc = lab_e[..., 0], np.hypot(lab_e[..., 1], lab_e[..., 2])
    hh = np.degrees(np.arctan2(lab_e[..., 2], lab_e[..., 1])) % 360
    hb = np.degrees(np.arctan2(lab_b[..., 2], lab_b[..., 1])) % 360
    dh = np.abs((hh - hb + 180) % 360 - 180)
    green = (hh > 95) & (hh < 200) & (cc > 7)
    dark = (L < 40) & (((hh > 95) & (cc > 3)) | ((dh > 25) & (cc > 5)) | (L < 22))
    return green | dark


def palm(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """the pot by its own clay region (GrabCut, 16 px band, hull); the Rhapis as leaf: what the edit changed (dE76 > 6) that is green
    (h 85-200, C* > 4) or dark (L* < 40: canes, leaf shade), in a box round the clay crown; pieces of 60 px and more, small holes filled.
    The wall between the fronds (brightened by the cube's down-light in the edit) is light, not plant: it goes to the light layer"""
    pot_k = ids == 49
    zone = C.dil(pot_k, 16)
    pot = C.gc_cut(e, C.ero(pot_k, 3), pot_k | (fg & zone), zone, zone & ~C.ero(zone, 2), iters=6)
    pot = hull_of(fill_holes(pot, 20000) & zone) & zone
    hh = np.degrees(np.arctan2(lab_e[..., 2], lab_e[..., 1])) % 360
    cc = np.hypot(lab_e[..., 1], lab_e[..., 2])
    # (2026-11-20, after the restart) green_or_dark: the edit's corner plaster is warm yellow (h 84-93, C* 12-17) and in its deep corner
    # shade L* < 40; both passed the old rule (h > 85, C* > 4, or L* < 40), so whole patches of wall went into the layer (a hard-edged
    # panel left of the plant)
    leaf = (green_or_dark(lab_e, C.to_lab(base))) & (d > 6)
    box = C.dil(ids == 50, 110) & ~pot
    box[C.ero(pot_k, 1).nonzero()[0].min():] &= C.dil(ids == 50, 3)[C.ero(pot_k, 1).nonzero()[0].min():]   # below the rim: the canes only
    crown = leaf & box
    crown = cv2.morphologyEx(crown.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(crown.astype(np.uint8), 8)
    crown = np.isin(lb, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 60])
    crown = fill_holes(crown, 80)
    # (2026-11-20, after the restart) only the pieces that reach the plant: a piece is kept when, grown by 12 px, it joins the largest
    # piece or the pot. A loose piece 60 px above the crown (the cube's down-light on the plaster, read as leaf) went into the layer
    n, lb, st, _ = cv2.connectedComponentsWithStats(C.dil(crown, 12).astype(np.uint8), 8)
    if n > 1:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        touch = set(np.unique(lb[C.dil(pot, 14)])) - {0}
        crown &= np.isin(lb, list(touch | {big}))
    rp["palm"] = dict(pot_px=int(pot.sum()), crown_px=int(crown.sum()), rule="pot: clay-seeded GrabCut + hull; crown: changed leaf pixels "
                      "(green or dark), only the pieces joined to the plant (12 px)")
    return pot | crown


SPECIAL[("pC-sides", 49)] = palm

RACK_BOX = (1830, 1060, 2165, 1335)
RACK_FRONT_PX = 0.35 * 1710 / (9.85 - 6.71)        # the card's 35 cm front at the clay's front face (Y 6.71): 191 px
RACK_ARCH_ROWS = (1095, 1160)                       # the rows where only the arches are (above the straps and the rod)
RACK_X = 0.32         # the foot's centre: at the clay's 0.225 (X 0.05-0.40) the left arch kisses the desk panel's front edge in frame
                      # (0.002); at 0.32 (X 0.145-0.495) the gap is 0.022 (W-HC3) and the back right corner clears the rounded corner


# the magazines as the edit drew them (traced on the locked, gain-matched edit at x3; canvas px): two pale sheets standing in the sling,
# the back one's top at y 1103, the front one's at 1131, down to the straps' bottom. Pale on pale plaster, so no colour rule finds them
RACK_MAGS = [(1885, 1103), (2047, 1103), (2047, 1128), (2060, 1133), (2060, 1298), (1888, 1302), (1883, 1131), (1885, 1128)]
RACK_FLOOR_Y = 1342                                  # the front legs' foot
RACK_RIGHT_X = 2132
RACK_FLOOR_LINE = 1290                               # where the skirting meets the floor behind the rack


def rack(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """the edit drew the rack about 45 % over the card (about 50 cm wide) and 0.10 m right of its place (the size and the place are fixed
    in apply_sizefix). (2026-11-20, after the restart) Cut as its parts, never as a filled box: the box kept the plaster, skirting and
    floor seen through the rack, which the scaling then moved (a grey box with the skirting at the wrong height round the rack).
      straps: cognac (C* > 22, h 35-85); magazines: RACK_MAGS (pale on pale plaster: no colour rule finds them);
      tubes and rod: dark and neutral (L* < 30, C* < 6) above the floor line (RACK_FLOOR_LINE); below it the floor under the rack is as
      dark and as neutral (L* 12-15, C* 3-5), so there only the legs' columns (as found just above the line) run down to the foot.
    The plaster, skirting and floor seen through the rack are not in the layer; the rack's shadow on them is in its shadow layer"""
    x0, y0, x1, y1 = RACK_BOX
    zone = np.zeros((H, W), bool)
    zone[y0:RACK_FLOOR_Y, max(x0, 1834):RACK_RIGHT_X] = True   # the desk panel's edge is at 1832; the right arch's outer edge at 2128
    L, a_, b_ = lab_e[..., 0], lab_e[..., 1], lab_e[..., 2]
    cc = np.hypot(a_, b_)
    hh = np.degrees(np.arctan2(b_, a_)) % 360
    straps = zone & (cc > 22) & (hh > 35) & (hh < 85) & (L > 25)
    mags = poly_mask(RACK_MAGS) & zone
    tubes = zone & (L < 30) & (cc < 6)
    tubes[RACK_FLOOR_LINE:] = False
    tubes = cv2.morphologyEx(tubes.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(tubes.astype(np.uint8), 8)
    tubes = np.isin(lb, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 40])
    legs_x = np.nonzero(tubes[RACK_FLOOR_LINE - 14:RACK_FLOOR_LINE].sum(0) >= 10)[0]
    legs = np.zeros((H, W), bool)
    legs[RACK_FLOOR_LINE:RACK_FLOOR_Y, legs_x] = True
    g = (tubes | legs | straps | mags) & zone
    g = cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(1)).astype(bool) & zone
    g = fill_holes(g, 60)
    n, lb, st, _ = cv2.connectedComponentsWithStats(C.dil(g, 3).astype(np.uint8), 8)     # only what joins the rack
    if n > 1:
        g &= lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    rp["rack_cut"] = dict(box=list(RACK_BOX), floor_line=RACK_FLOOR_LINE, foot_y=RACK_FLOOR_Y, px=int(g.sum()), straps_px=int(straps.sum()),
                          magazines_px=int(mags.sum()), legs_columns=int(legs_x.size),
                          rule="parts, not a box: straps by colour, magazines traced, tubes dark-neutral above the floor line, legs below it")
    return g


SPECIAL[("pC-sides", 51)] = rack


def frame2_cut(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """(2026-11-20, after the restart) the edit drew frame 2 about 23 % too tall, its bottom 70-90 px under the clay's: the clay-seeded
    cut (a 20 px band) stopped above its bottom mat and moulding, and frame2_fit then stretched a frame with no bottom. The whole frame:
    GrabCut in the clay's band grown 100 px downward, seeded by the clay, hull (a quad); frame2_fit then sets its span onto the clay's"""
    km = np.isin(ids, own(43))
    zone = C.dil(km, 20)
    ys, xs = np.nonzero(km)
    down = np.zeros((H, W), bool)
    down[ys.min():ys.max() + 100, xs.min() - 6:xs.max() + 7] = True
    zone |= down
    sure = C.ero(km, 3)
    hard = zone & ~C.ero(zone, 2)
    g = C.gc_cut(e, sure, km | (fg & zone), zone, hard, iters=6)
    n, lb, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), 8)
    g = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])) if n > 1 else g
    g = hull_of(fill_holes(g | sure, 20000)) & zone
    yy, xx = np.nonzero(g)
    rp["frame2_cut"] = dict(px=int(g.sum()), bottom_row=int(yy.max()), clay_bottom_row=int(ys.max()))
    return g


SPECIAL[("pC-sides", 43)] = frame2_cut


def frame2_fit(e, base, m, rp):
    """the edit drew frame 2 about 23 % too tall (its bottom 70-90 px under the clay's): per column the frame's span (top to bottom of the
    layer) is remapped onto the clay's (the projected 44 x 54 at the frame face, X 0.619, the side face to the wall): the top edge and the
    sides stay, the verticals stay vertical"""
    xr = 0.649
    cols = np.nonzero(m.any(0))[0]
    map_y = np.tile(np.arange(H, dtype=np.float32)[:, None], (1, W))
    new = np.zeros((H, W), bool)
    rows = np.arange(H, dtype=np.float32)
    for x in cols:
        c = np.nonzero(m[:, x])[0]
        te, be = c.min(), c.max() + 1
        Yw = 7.03 + (7.47 - 7.03) * np.clip((x - M.proj(0.619, 7.03, 1.4)[0]) / (M.proj(0.619, 7.47, 1.4)[0] - M.proj(0.619, 7.03, 1.4)[0]), 0, 1)
        Xf = 0.619 if x <= M.proj(0.619, 7.47, 1.4)[0] else 0.619 + (xr - 0.619) * np.clip((x - M.proj(0.619, 7.47, 1.4)[0]) /
                                                                                              (M.proj(xr, 7.47, 1.4)[0] - M.proj(0.619, 7.47, 1.4)[0]), 0, 1)
        tc, bc = M.proj(Xf, Yw, 1.69)[1], M.proj(Xf, Yw, 1.15)[1]
        tc = te                                                           # the top as drawn (it sits on the clay's within 2 px)
        k = (be - te) / max(bc - tc, 1.0)
        map_y[:, x] = te + (rows - tc) * k
        new[int(np.ceil(tc)):int(np.floor(bc)), x] = True
    rgb = np.stack([cv2.remap(e[..., i].astype(np.float32), np.tile(np.arange(W, dtype=np.float32)[None, :], (H, 1)), map_y, cv2.INTER_LINEAR)
                    for i in range(3)], -1).astype(np.float64)
    nm = cv2.remap(m.astype(np.float32), np.tile(np.arange(W, dtype=np.float32)[None, :], (H, 1)), map_y, cv2.INTER_LINEAR) > 0.5
    e2 = e.copy()
    gone = m & ~nm
    e2[gone] = base[gone]
    e2[nm] = rgb[nm]
    rp.setdefault("sizefix", {})["framed-art-2"] = dict(why="the edit's frame 2 came about 23 % taller than 44 x 54 (bottom 70-90 px low)",
                                                       method="per-column remap of the frame's span onto the clay's projected span", px_before=int(m.sum()),
                                                       px_after=int(nm.sum()))
    return e2, nm


DESK_TOP_Y = 873            # the desk top's back edge in W0 (the clay's id 20): above it the niche wall
TRAY_BOX = (990, 1222, 910)                         # x0, x1, y1 of the tray's search box (on the desk top)
PENCIL_BOX = (1080, 1212, 715)                      # x0, x1, top of the pencils' search box (down to the cup's top); right of the vase


def tray(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """(2026-11-20, after the restart) the edit drew the tray 1.56 times the card (from under the vase, x ~990, to 1196: about 38 cm for
    24) and the cut gave its left end to the vase (a dark line of desk under the vase). The tray: the pale pixels the edit changed on the
    desk top (below the wall line, so no wall and no shadow on it), less the vase and the cup and their contact shadows; its outline
    is their hull (an organic slab, convex), and what the vase and the cup hid of it is inpainted from its own stone (LAYER_SRC), so the
    whole slab can be scaled to the card in apply_sizefix (FIT)"""
    x0, x1, y1 = TRAY_BOX
    zone = np.zeros((H, W), bool)
    zone[DESK_TOP_Y + 2:y1, x0:x1] = True
    vase = gc_clay(e, ids, 60, fg)
    km = ids == 58
    cz = C.dil(km, 10)
    cup = hull_of(C.gc_cut(e, C.ero(km, 3), km | (fg & cz), cz, cz & ~C.ero(cz, 2), iters=6) & cz) & cz
    excl = C.dil(vase, 5) | C.dil(cup, 5)
    t = zone & (lab_e[..., 0] > 50) & (d > 6) & ~excl
    t = cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(t.astype(np.uint8), 8)
    t = np.isin(lb, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 30])     # the slab shows either side of the cup
    t = fill_holes(t, 400)
    hull = hull_of(t) & zone
    hidden = hull & ~t
    ys, xs = np.nonzero(hull)
    by0, by1, bx0, bx1 = max(ys.min() - 12, 0), ys.max() + 12, max(xs.min() - 12, 0), xs.max() + 12
    crop = C.q(e[by0:by1, bx0:bx1])
    known_bad = (~hull[by0:by1, bx0:bx1]) | hidden[by0:by1, bx0:bx1]          # inpaint from the visible slab only
    fill = cv2.inpaint(np.where(known_bad[..., None], 0, crop).astype(np.uint8), known_bad.astype(np.uint8), 6, cv2.INPAINT_TELEA)
    src = e.copy()
    hb = hidden[by0:by1, bx0:bx1]
    sub = src[by0:by1, bx0:bx1]
    sub[hb] = fill[hb] / 255.0
    LAYER_SRC[57] = src
    rp["tray_cut"] = dict(px=int(hull.sum()), visible_px=int(t.sum()), inpainted_px=int(hidden.sum()),
                          rule="pale changed pixels on the desk top (y > %d), less the vase and the cup; the hull, its hidden part inpainted" % (DESK_TOP_Y + 2))
    return hull


def pencup(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """(2026-11-20, after the restart) the edit fanned the three pencils wider than the clay's two sticks, so the clay-bounded cut kept
    the cup only and the pencils came out as grey ghosts in the shadow layer. The cup: its clay (58) GrabCut-cut in a 10 px band, hull;
    the pencils: what the edit changed above the cup (dE > 10) that is wood (C* > 14) or graphite (L* < 45), pieces of 15 px and more"""
    km = ids == 58
    zone = C.dil(km, 10)
    cup = C.gc_cut(e, C.ero(km, 3), km | (fg & zone), zone, zone & ~C.ero(zone, 2), iters=6)
    cup = hull_of(fill_holes(cup, 2000) & zone) & zone
    top = int(np.nonzero(cup)[0].min())
    cx = np.nonzero(cup.any(0))[0]
    CUP_ROWS.update(top=top, bottom=int(np.nonzero(cup)[0].max()), x0=int(cx.min()), x1=int(cx.max()))
    x0, x1, y0 = PENCIL_BOX
    box = np.zeros((H, W), bool)
    box[y0:top + 8, x0:x1] = True
    cc = np.hypot(lab_e[..., 1], lab_e[..., 2])
    pen = box & (d > 10) & ((cc > 14) | (lab_e[..., 0] < 45)) & ~C.dil(gc_clay(e, ids, 60, fg), 4)
    pen = cv2.morphologyEx(pen.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(1)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(pen.astype(np.uint8), 8)
    pen = np.isin(lb, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 15])
    rp["pencup_cut"] = dict(cup_px=int(cup.sum()), pencils_px=int(pen.sum()), rule="cup: clay GrabCut + hull; pencils: wood or graphite changed above the cup")
    return cup | pen


def boxed_object(e, box, cores, band=3):
    """GrabCut in a box round an object the edit drew off its clay: sure = the given core ellipses, background = the box's border;
    the hull (the object's silhouette is convex)"""
    x0, y0, x1, y1 = box
    zone = np.zeros((H, W), bool)
    zone[y0:y1, x0:x1] = True
    sure = np.zeros((H, W), np.uint8)
    for (cx, cy, ax, ay) in cores:
        cv2.ellipse(sure, (int(cx), int(cy)), (int(ax), int(ay)), 0, 0, 360, 1, -1)
    sure = sure.astype(bool) & zone
    hard = zone & ~C.ero(zone, band)
    g = C.gc_cut(e, sure, zone & ~hard, zone, hard, iters=8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), 8)
    g = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])) if n > 1 else g
    return hull_of(fill_holes(g, 3000)) & zone


def candle(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """(2026-11-20, after the restart) the edit drew the Hiba bowl 136 px wide (the card's 18 cm is the clay's 95) and 20 px left of the
    clay, its rim and wax as pale as the wall: the clay-bounded cut kept its middle and its rim became a grey ring in the shadow layer.
    The whole bowl: GrabCut in a box round it, seeded by its body and its wax, hull (then FIT)"""
    g = boxed_object(e, CANDLE_BOX, [(1684, 864, 46, 16), (1685, 834, 40, 5)])
    rp["candle_cut"] = dict(px=int(g.sum()), box=list(CANDLE_BOX))
    return g


def dish(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """(2026-11-20, after the restart) the edit drew the dish 77 px wide (the card's 8.5 cm is the clay's 48): the clay-bounded cut kept
    a crescent of it. The whole dish: GrabCut in a box round it, hull (then FIT)"""
    g = boxed_object(e, DISH_BOX, [(1583, 887, 30, 7)])
    rp["dish_cut"] = dict(px=int(g.sum()), box=list(DISH_BOX))
    return g


def vase_base(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """(2026-11-20, after the restart) in its base rows (y >= 870) the vase is held to its clay footprint (3 px): the edit's oversized tray
    ran under it, and the hull took that end of the tray into the vase's layer (a pale slab under the vase once the tray was set to size)"""
    keep = np.ones((H, W), bool)
    keep[870:] = C.dil(ids == 60, 3)[870:]
    rp["vase_base"] = dict(removed_px=int((m & ~keep).sum()))
    return m & keep


CANDLE_BOX = (1608, 812, 1764, 895)
DISH_BOX = (1536, 864, 1632, 906)
SPECIAL[("pB-desk", 61)] = candle
SPECIAL[("pB-desk", 62)] = dish
SPECIAL[("pB-desk", 60)] = vase_base
SPECIAL[("pB-desk", 57)] = tray
SPECIAL[("pB-desk", 58)] = pencup


def cut_pass(p, rec):
    J = json.load(open(os.path.join(ST, "passes.json")))[p]
    ids = M.ids("W0")
    pl_ids = M.ids("W0-plate")
    base = C.load(os.path.join(ST, J["base"]))
    pids = pass_ids(p)
    zone = np.zeros((H, W), bool)
    for k in pids:
        zone |= C.dil(ids == k, ZONE_PAD.get(k, 22))
    for k, v in P.items():                               # never another pass's product that is already in the base
        if v[3] != p:
            zone &= ~(C.ero(np.isin(ids, own(k)), 2) & ~C.dil(np.isin(ids, pids), 6))
    ign = C.dil(np.isin(ids, [i for k in J.get("ignore", []) for i in own(k)]), 40)   # placeholders the raw edited but this pass does not cut
    stable = C.ero(np.isin(pl_ids, M.ARCH), 3) & ~C.dil(zone, 40) & ~ign
    stable[1460:] = False
    e, rl = M.ecc_lock(os.path.join(ST, J["raw"]), os.path.join(ST, J["input"]), stable)
    keep = ~C.dil(zone, 40) & ~light_env(ids, p) & M.frame_mask() & ~ign
    g = C.gain_field(e, base, keep)
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    d = np.linalg.norm(C.blur(C.to_lab(e), 1.0) - C.blur(C.to_lab(base), 1.0), axis=-1)
    out_d = d[keep]
    rp = dict(lock=rl, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
              dE_outside_zone_p50_p95=[round(float(v), 2) for v in np.percentile(out_d, [50, 95])])
    fg = (d > 7) & zone
    lc = np.isin(ids, [k for k in pids if k in LIGHT_COLOURED])
    fg |= (d > 4) & C.ero(lc, 2) & zone                  # pale products on pale ground: a lower threshold inside their own clay region
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    sure = C.ero(((d > 16) | ((d > 6) & C.ero(lc, 3))) & zone, 2)
    hard = zone & ~C.ero(zone, 2)
    fg2 = C.gc_cut(e, sure, C.dil(fg, 2) & zone, zone, hard, iters=6) if sure.any() else fg
    fg = fill_holes(fg2 | C.ero(fg, 1), 900) & zone
    # a change of brightness only, on the walls, the floor or the fixed walnut, away from the products' own places: light or shadow
    lab_e0, lab_b0 = C.blur(C.to_lab(e), 1.5), C.blur(C.to_lab(base), 1.5)
    ce_, cb_ = np.hypot(lab_e0[..., 1], lab_e0[..., 2]), np.hypot(lab_b0[..., 1], lab_b0[..., 2])
    he_, hb_ = np.degrees(np.arctan2(lab_e0[..., 2], lab_e0[..., 1])), np.degrees(np.arctan2(lab_b0[..., 2], lab_b0[..., 1]))
    dh_ = np.abs((he_ - hb_ + 180) % 360 - 180)
    same = ((np.abs(lab_e0[..., 1] - lab_b0[..., 1]) < 4) & (np.abs(lab_e0[..., 2] - lab_b0[..., 2]) < 5)) | ((dh_ < 12) & (np.abs(ce_ - cb_) < 8))
    same |= light_env(ids, p) & (dh_ < 25) & (np.abs(ce_ - cb_) < 14) & (lab_e0[..., 0] >= lab_b0[..., 0] - 3)
    surf = np.isin(pl_ids, SURF + WAL) & ~np.isin(ids, pids)
    fg &= ~(same & surf)
    fg &= ~(same & np.isin(pl_ids, SURF + WAL) & ~C.dil(np.isin(ids, pids), 3) )
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    lab_e, lab_b = C.to_lab(e), C.to_lab(base)
    if LAMPS.get(p):
        glow = (lab_e[..., 0] - lab_b[..., 0] > 2) & (np.abs(lab_e[..., 1] - lab_b[..., 1]) < 5) & ~np.isin(ids, pids)
        lampm = np.zeros((H, W), bool)
        for k in LAMPS[p]:
            lampm |= C.dil(ids == k, 4)
        fg &= ~(glow & ~lampm)
    prods = sorted({FILLERS.get(k, k) for k in pids})
    dist = np.stack([cv2.distanceTransform((~np.isin(ids, own(k))).astype(np.uint8), cv2.DIST_L2, 5) for k in prods])
    lab_i = np.argmin(dist, 0)
    layers = {}
    for i, k in enumerate(prods):
        if k in CLAYCUT:
            m = gc_clay(e, ids, k, fg) & ((lab_i == i) | np.isin(ids, own(k)))
            if k == 46:
                m &= ~np.isin(pl_ids, WAL)
            if (p, k) in SPECIAL:
                m = SPECIAL[(p, k)](e, m, fg, lab_e, d, ids, pl_ids, base, rp)
            layers[k] = m
            rp[P[k][0]] = dict(px=int(m.sum()), clay_px=int(np.isin(ids, own(k)).sum()), cut="clay-seeded GrabCut")
            continue
        m = fg & (lab_i == i)
        if k in BOUND:
            m &= C.dil(np.isin(ids, own(k)), BOUND[k])
        if k == 46:                                      # the rug: never over the chair or the desk (the plate's fixed walnut)
            m &= ~np.isin(pl_ids, WAL)
        if (p, k) in SPECIAL:
            m = SPECIAL[(p, k)](e, m, fg, lab_e, d, ids, pl_ids, base, rp)
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        n, lb, stt, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        m = np.isin(lb, [j for j in range(1, n) if stt[j, cv2.CC_STAT_AREA] >= 40])
        layers[k] = m
        rp[P[k][0]] = dict(px=int(m.sum()), clay_px=int(np.isin(ids, own(k)).sum()))
    e = apply_sizefix(p, e, base, layers, lab_e, rp, ids_now=ids)
    apply_fit(p, e, layers, rp)
    if 49 in layers and 40 in layers:                    # the stack (Y 7.03-7.25) is nearer the camera than the plant (Y 6.72): the
        occl = layers[49] & layers[40]                   # fronds that reach it go behind it (2026-11-20, after the restart)
        layers[49] = layers[49] & ~layers[40]
        rp["planter_behind_curtain_px"] = int(occl.sum())
    allfg = np.zeros((H, W), bool)
    for k in prods:
        allfg |= layers[k]
    rat = np.clip(C.blur(C.luma(C.lin(e)), 2) / np.maximum(C.blur(C.luma(C.lin(base)), 2), 1e-4), 0, 1.5)
    dark = np.clip(1 - rat - 0.02, 0, 0.75)
    dk = np.stack([cv2.distanceTransform((~layers[k]).astype(np.uint8), cv2.DIST_L2, 5) for k in prods])
    near = np.argmin(dk, 0)
    du = dk.min(0)
    band = SHADOW_BAND
    taper = np.clip(1 - du / band, 0, 1) ** 1.1
    shadows = {}
    edge_in = allfg & ~C.ero(allfg, 2)
    shade_w = np.clip(C.blur(((dh_ < 15) & (np.abs(ce_ - cb_) < 10)).astype(np.float64), 4) * 1.4 - 0.2, 0, 1)
    view = np.isin(pl_ids, (0, 15))
    for i, k in enumerate(prods):
        env = (du <= band) & (near == i) & ~allfg & ~view & np.isin(pl_ids, SHADOW_ON[p])
        s = 1 - C.blur(np.minimum(dark, 0.45) * taper * env * shade_w, 1.0)
        s[~C.dil(env, 1) | allfg] = 1
        s_min = cv2.erode(s.astype(np.float32), C.disk(2).astype(np.uint8)).astype(np.float64)
        s = np.where(edge_in, np.minimum(s, s_min), s)
        shadows[k] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
    shadow_overrides(p, e, base, layers, shadows, pl_ids, rp)
    fit_shadows(p, e, base, layers, shadows, pl_ids, rp)
    light = None
    if LAMPS.get(p):
        env = light_env(ids, p)
        L8 = np.clip(1 - (1 - e) / np.maximum(1 - base, 1e-3), 0, 0.45)
        glow_ok = np.clip(C.blur(((dh_ < 30) & (ce_ - cb_ < 22)).astype(np.float64), 3) * 1.4 - 0.2, 0, 1)
        wgt = (env & ~C.dil(allfg, 2) & ~view).astype(np.float64) * glow_ok
        Ls = np.stack([C.blur(L8[..., c] * wgt, 10) / np.maximum(C.blur(wgt, 10), 1e-3) for c in range(3)], -1)
        Ls[C.blur(wgt, 10) < 0.02] = 0
        soft_env = C.blur(env.astype(np.float64), 25)
        light = Ls * (soft_env * ~allfg)[..., None]
        rp["light_px"] = int((light.max(2) > 0.003).sum())
    rec[p] = rp
    return e, layers, shadows, light, prods


def y_of_L(L):
    f = (np.asarray(L, np.float64) + 16) / 116
    return np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29))


def L_of_y(Y):
    Y = np.asarray(Y, np.float64)
    return np.where(Y > (6 / 29) ** 3, 116 * np.cbrt(Y) - 16, Y * (29 / 3) ** 3)


SHADOW_KNEE = (14.0, 11.5)     # WM-G1 for the shadows (2026-11-20, after the restart): below L* 14 a shadow's result is eased onto 11.5-14


def shadow_toe(s):
    """the shadow's own MP-I2: where a shadow would take the plate under L* 14, the result is eased onto 11.5-14 (L' = 11.5 + 2.5 L / 14),
    never darker than that and never lighter than the plate; the planter's and the rack's shadows on the dark corner floor otherwise
    took the frame's p0.5 to 10.4"""
    plate = C.load(os.path.join(ST, "plate.png"))
    Yp = np.maximum(C.luma(C.lin(plate)), 1e-6)
    Lp = L_of_y(Yp)
    Ls = L_of_y(s * Yp)
    k, lo = SHADOW_KNEE
    Lt = np.where(Ls < k, lo + (k - lo) * Ls / k, Ls)
    Lt = np.minimum(Lt, Lp)
    out = np.where(s < 1, np.clip(y_of_L(np.maximum(Lt, Ls)) / Yp, 0, 1), 1.0)
    return np.maximum(out, s)


# (2026-11-20, after the restart) colour fixed in code against the photo check (new-rooms-photo-check.json): the layer's a* b* scaled so
# its median C* is the photo's, L* and hue kept (the edit warmed both well past the SKU photo)
COLOURFIX = {62: dict(C=21.0, photo="w-dish: the wall L*48, C*21, h58", why="the dish came C* 35.5 (h 58.6): a saturated orange, not the muted caramel of the photo"),
             48: dict(C=19.3, photo="w-bin-brown: L*58, C*19.3, h66", why="the bin came C* 29.6 (h 67): orange kraft, the photo's is taupe-kraft")}


def colour_fix(k, rgb, a, rec_p):
    F = COLOURFIX.get(k)
    if not F:
        return rgb
    m = C.ero(a > 0.98, 2)
    lab = C.to_lab(rgb)
    c0 = float(np.median(np.hypot(lab[..., 1], lab[..., 2])[m]))
    f = F["C"] / max(c0, 1e-3)
    lab[..., 1:] *= f
    out = np.clip(C.from_lab(lab), 0, 1)
    c1 = float(np.median(np.hypot(*(C.to_lab(out)[..., i] for i in (1, 2)))[m]))
    rec_p.setdefault("colourfix", {})[P[k][0]] = dict(why=F["why"], photo=F["photo"], C_before=round(c0, 1), C_after=round(c1, 1), ab_scale=round(f, 3))
    return out


def write_pass(p, e, layers, shadows, light, prods, man, rec):
    tc = toe_curve()
    man["layers"] = [l for l in man["layers"] if l.get("pass") != p]
    for k in prods:
        slot, pid, z, _ = P[k]
        a = C.soft(layers[k])
        rgb = C.defringe(LAYER_RGB.get(k, e), layers[k])
        if tc:
            lab = C.to_lab(rgb)
            lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
            rgb = np.clip(C.from_lab(lab), 0, 1)
        rgb = colour_fix(k, rgb, a, rec.setdefault(p, {}))
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        lp, sp = os.path.join(ST, "layers", slot, pid + ".png"), os.path.join(ST, "shadows", slot, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp)
        if slot in ("framed-art", "framed-art-2"):                 # the blank-canvas layer, kept for tools/work_prints.py
            os.makedirs(os.path.join(M.SCR, "blank-frames"), exist_ok=True)
            Image.fromarray(rgba, "RGBA").save(os.path.join(M.SCR, "blank-frames", pid + ".png"))
        s8 = C.q(shadow_toe(shadows[k]))
        Image.fromarray(s8).save(sp)
        ys, xs = np.nonzero(a8 > 0)
        man["layers"].append(dict(slot=slot, product=pid, z=z, shadow_z=z - 1, default=True, layer=os.path.relpath(lp, ST),
                                  shadow=os.path.relpath(sp, ST), alpha_px=int((a8 > 0).sum()), shadow_px=int((s8 < 255).sum()),
                                  bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if xs.size else None,
                                  sold=True, temporary_repeat=slot in ("planter", "magazine-holder", "rug"),
                                  source=f"W0 {p} (nano-banana-2 edit), cut in code (tools/work_compose.py)", **{"pass": p}))
    man["light"] = [li for li in man["light"] if li.get("pass") != p]
    if light is not None:
        lp = os.path.join(ST, "light", f"{p}-lamps.png")
        Image.fromarray(C.q(light)).save(lp)
        man["light"].append(dict(file=os.path.relpath(lp, ST), z=90, blend="screen", lamps=[P[k][0] for k in LAMPS[p]], **{"pass": p}))
    man["layers"].sort(key=lambda l: (l["z"], l["slot"]))


def compose(man, rec, out_name="w0-defaults", swap=None):
    """swap: {slot: layer path} to compose a variant in place of the default layer"""
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    a_all = np.zeros((H, W))
    for l in [x for x in man["layers"] if x.get("default", True)]:
        lpath = (swap or {}).get(l["slot"], l["layer"])
        rgba = np.asarray(Image.open(os.path.join(ST, lpath)))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
        region |= (rgba[..., 3] > 0) | (s8 < 255)
        a_all = 1 - (1 - a_all) * (1 - rgba[..., 3] / 255)
    for li in man["light"]:
        L8 = np.asarray(Image.open(os.path.join(ST, li["file"]))).astype(np.float64)
        L8 = np.clip(np.rint(L8 * (1 - a_all)[..., None]), 0, 255).astype(np.uint8)
        out = C.light_one(out, L8)
        region |= L8.max(2) > 0
    o8 = C.q(out)
    Image.fromarray(o8).save(os.path.join(ST, f"{out_name}.png"))
    M.save_frame(o8.astype(np.float64) / 255, os.path.join(ST, f"{out_name}-frame.png"))
    rnd2 = dict(region_px=int(region.sum()), outside_differing_px=int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum()),
                rule="outside every alpha, shadow and light: plate.png, pixel for pixel")
    lab = C.to_lab(o8.astype(np.float64) / 255)
    bp = round(float(np.percentile(lab[..., 0][M.frame_mask()], 0.5)), 2)
    if swap is None:
        man["rnd2"] = rnd2
        rec["black_point_p05"] = bp
    return o8, rnd2, bp


def main(args):
    mp = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(mp)) if os.path.exists(mp) else dict(
        id="wm-work-w0-stage1-2026-11-20", room="work", style="warm-modern", frame="W0", canvas=[W, H], frame_box=list(M.FRAME),
        base="plate.png", camera=dict(M.CAM), compose="plate.png; per layer in z order: shadow (multiply), then the layer (straight alpha); "
                                                    "lights (screen, z 90) times (1 - every alpha)", layers=[], light=[])
    rp = os.path.join(ST, "w0-compose.json")
    rec = json.load(open(rp)) if os.path.exists(rp) else {}
    for p in args:
        if p == "compose":
            continue
        e, layers, shadows, light, prods = cut_pass(p, rec)
        write_pass(p, e, layers, shadows, light, prods, man, rec)
        M.save(os.path.join(M.SCR, f"{p}-locked.png"), e)
    compose(man, rec)
    json.dump(man, open(mp, "w"), indent=1)
    json.dump(rec, open(rp, "w"), indent=1, default=str)
    print(json.dumps(man.get("rnd2")), rec.get("black_point_p05"),
          json.dumps({p: {k: v for k, v in rec[p].items() if k not in ("lock",)} for p in args if p in rec})[:2000])


if __name__ == "__main__":
    main(sys.argv[1:])
