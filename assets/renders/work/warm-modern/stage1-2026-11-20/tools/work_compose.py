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
           57: (8, True), 58: (8, False), 60: (8, True), 61: (8, True), 62: (6, True), 47: (10, True), 48: (10, False),
           40: (14, False), 45: (6, True), 49: (60, False), 51: (60, False), 46: (20, False), 64: (16, False)}
SHADOW_ON = {"pA-wall": (17, 24), "pB-desk": (17, 20, 21, 9, 10, 11), "pC-sides": (1, 2, 4, 5, 9, 10, 11), "pD-front": (10, 11)}
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
    ids = [k for k, v in P.items() if v[3] == p]
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
    leaf = (((hh > 85) & (hh < 200) & (cc > 4)) | (lab_e[..., 0] < 40)) & (d > 6)
    box = C.dil(ids == 50, 110) & ~pot
    box[C.ero(pot_k, 1).nonzero()[0].min():] &= C.dil(ids == 50, 3)[C.ero(pot_k, 1).nonzero()[0].min():]   # below the rim: the canes only
    crown = leaf & box
    crown = cv2.morphologyEx(crown.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(crown.astype(np.uint8), 8)
    crown = np.isin(lb, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 60])
    crown = fill_holes(crown, 80)
    rp["palm"] = dict(pot_px=int(pot.sum()), crown_px=int(crown.sum()), rule="pot: clay-seeded GrabCut + hull; crown: changed leaf pixels (green or dark)")
    return pot | crown


SPECIAL[("pC-sides", 49)] = palm

RACK_BOX = (1830, 1060, 2165, 1335)
RACK_FRONT_PX = 0.35 * 1710 / (9.85 - 6.71)        # the card's 35 cm front at the clay's front face (Y 6.71): 191 px
RACK_ARCH_ROWS = (1095, 1160)                       # the rows where only the arches are (above the straps and the rod)
RACK_X = 0.32         # the foot's centre: at the clay's 0.225 (X 0.05-0.40) the left arch kisses the desk panel's front edge in frame
                      # (0.002); at 0.32 (X 0.145-0.495) the gap is 0.022 (W-HC3) and the back right corner clears the rounded corner


def rack(e, m, fg, lab_e, d, ids, pl_ids, base, rp):
    """the edit drew the rack about 45 % over the card (about 50 cm wide) and 0.10 m right of its place: cut from a box round it, seeded
    by the cognac straps and the black tubes (the size and the place are fixed in apply_sizefix)"""
    x0, y0, x1, y1 = RACK_BOX
    zone = np.zeros((H, W), bool)
    zone[y0:y1, x0:x1] = True
    L, a_, b_ = lab_e[..., 0], lab_e[..., 1], lab_e[..., 2]
    seeds = zone & C.ero(((np.hypot(a_, b_) > 30) & (L > 30)) | (L < 26), 1)
    hard = zone & ~C.ero(zone, 3)
    g = C.gc_cut(e, seeds, zone & (d > 7), zone, hard, iters=8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), 8)
    g = np.isin(lb, [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 150])
    g = fill_holes(g, 3000)
    rp["rack_cut"] = dict(box=list(RACK_BOX), px=int(g.sum()))
    return g


SPECIAL[("pC-sides", 51)] = rack


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
    stable = C.ero(np.isin(pl_ids, M.ARCH), 3) & ~C.dil(zone, 40)
    stable[1460:] = False
    e, rl = M.ecc_lock(os.path.join(ST, J["raw"]), os.path.join(ST, J["input"]), stable)
    keep = ~C.dil(zone, 40) & ~light_env(ids, p) & M.frame_mask()
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


def write_pass(p, e, layers, shadows, light, prods, man, rec):
    tc = toe_curve()
    man["layers"] = [l for l in man["layers"] if l.get("pass") != p]
    for k in prods:
        slot, pid, z, _ = P[k]
        a = C.soft(layers[k])
        rgb = C.defringe(e, layers[k])
        if tc:
            lab = C.to_lab(rgb)
            lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
            rgb = np.clip(C.from_lab(lab), 0, 1)
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
        s8 = C.q(shadows[k])
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
