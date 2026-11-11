#!/usr/bin/env python3
"""
reserve_r3.py: fix pass R3 of the warm-modern living-room tool, phase 2 (briefs/render-wm-tool-phase2-fix-r3-2026-11-11.md, continuing the
reserve brief and the phase 2 brief; SPEND2, at most two passes at 650). render-agent, 2026-11-11.

  R3a  the planter and the basket together, at the card sizes and the plan's places, the basket IN FRONT of the pot
  R3b  the pendant alone, at the plan's X / Y, shade bottom 1.90 (V7Q7 b), 50 cm (the card)

The lesson of R1 / R2 (work-reserve/fidelity-r12.json): seedream keeps what already looks photographed (outside the products the room came
back within ~1 L* after the tone match) but re-imagines flat clay: given the tinted clay of the planter mostly hidden behind the basket (the
plan's 'basket hides ~75 % of the pot by design', slots 1.9.2), it enlarged the pot x1.36 and pushed the basket aside; given the clay pendant
it kept the shade's size and drew it ~60 px (~10 cm) lower. So the R3 placeholders are still the step-0 clay geometry (card size, house plan
1.3.5 place, step 0's M0 camera) but PHOTOGRAPHIC: each product's own earlier render, measured and fitted onto its clay box in code,
so the model sees the right size and place already looking real, and its job is to re-render it in place (materials to the card crop,
light, contact). What the model returns is measured again against the clay (fidelity-r3.json); nothing of the earlier renders goes into a
layer except through the new render.

  R3a placeholders: R1's pot (scaled x0.723 / y0.678 onto the clay pot box: rim 42, height 35.5, centre (-1.95, 0.42)), R1's olive tree
      (the filler, scaled x0.678 about its trunk foot, inside the crown envelope r <= 0.28, Z <= 1.65), R1's basket (scaled onto the clay
      basket box: 35 x 39 at (-1.62, 0.78), in front of the pot), each with its R1 contact shadow carried along
  R3b placeholder: R2's shade (50 cm) lifted onto the clay shade rows of Z 1.90-2.18 under the hang point (0.20, 1.72); the cord and
      canopy as R2 drew them, shortened by the shade

Everything is drawn on the CURRENT scene: phase 1's ungraded base + the 9 layered defaults (steps 1-3 and the reserve) + cushion set B.
New files only: work-r3/, inputs/r3*-input.*, raw/r3*-seedream.png.

  python3 reserve_r3.py scene
  python3 reserve_r3.py input r3a|r3b
  python3 reserve_r3.py fetch r3a|r3b <url> <placeholder_id> <task_id>
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import extract as X  # noqa: E402
import grade_cut_r12 as G12  # noqa: E402
import phase2_wm as W  # noqa: E402
import reserve_r12 as R  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR3 = os.path.join(HERE, "work-r3")
SIZE = W.SIZE
PASSES = {"r3a": ["planter", "basket"], "r3b": ["pendant"]}
NAMES = {"r3a": "wm-ph2-fix-r3a-planter-basket", "r3b": "wm-ph2-fix-r3b-pendant"}
LAYERED = G12.ACCEPTED                                  # the 9 defaults already layered (steps 1-3 + the reserve)
DEPTH = {"planter": 4.999, "basket": 4.534, "pendant": 2.913}
SPEC = dict(R.SPEC)
SPEC.update({
    "planter": dict(margin=26, band=40, onto="floor_wall", z=32, thin=True),
    "basket": dict(margin=22, band=36, onto="floor_wall_planter", z=60),
    "pendant": dict(margin=18, band=0, onto="none", z=80, thin=True),
})


def rel(p):
    return os.path.relpath(p, W.REPO)


# ------------------------------------------------------------------------------------------------- the current scene
def scene():
    p = os.path.join(WR3, "scene-B9.png")
    if os.path.exists(p):
        return PW.load(p)
    os.makedirs(WR3, exist_ok=True)
    U, _ = G12.compose(set(LAYERED) | {"cushions"}, W_parts(), cushion_set="B")
    PW.save(p, U)
    return PW.load(p)


_P = []


def W_parts():
    if not _P:
        import stack
        _P.append(stack.base_parts())
    return _P[0]


def layered_alpha():
    """the 9 layered defaults' alpha and set B's, on the current scene (the rug excluded: it lies under the floor items)"""
    a = np.zeros(SIZE[::-1], np.float32)
    for k in LAYERED:
        if k == "rug":
            continue
        _, ak, _ = G12.product(k)
        a = np.maximum(a, ak)
    _, ac, _ = G12._STACK_PRODUCT("cushions", "B")
    return np.maximum(a, ac)


# ------------------------------------------------------------------------------------------------- clay boxes (step 0's camera)
def clay_boxes():
    """the projected clay of the defaults at their card sizes and plan places (work px). The pot as its card draws it (notes: opening
    35.5, largest diameter (the belly) 42, height 35.5): x from the belly (r 0.21), the top from the opening's far rim (r 0.1775, Z 0.355),
    the bottom from the base's near edge (r ~0.17, Z 0). The basket: the clay of R1 (body r 0.175 x 0.39 + two loops), read as R1's
    basket is read (body_rows)"""
    P = R.proj
    belly, rim, base = P(S0.circ(-1.95, 0.42, 0.21, 0.24)), P(S0.circ(-1.95, 0.42, 0.1775, 0.355)), P(S0.circ(-1.95, 0.42, 0.17, 0.0))
    pb = R.parts_basket()
    return dict(
        pot=dict(left=float(belly[:, 0].min()), right=float(belly[:, 0].max()), top=float(rim[:, 1].min()), bottom=float(base[:, 1].max())),
        basket=body_rows(np.maximum(pb["body"], pb["loops"]) > 0.5))


# ------------------------------------------------------------------------------------------------- R1 as the donor of R3a
# R1's pot, measured on the registered, tone-matched R1 (work-reserve/r1-regt.npy): its left silhouette edge traced on L* (the strongest
# horizontal gradient left of the pot, rows 968-1064) and read on a 5x zoom below that, where the pot meets the white skirting and the
# edge is soft; the rim's top and the base's front on the axis column; the right edge (rows 965-992, then behind R1's basket) mirrored
# about the axis. Work px. Fitted by its BELLY (x 928 / 1145 at row ~1064, the card's 42) and its height (rim top 962, base front 1185).
R1_POT_LEFT = [(936, 968), (935, 990), (934, 1004), (933, 1016), (932, 1028), (930, 1040), (929, 1052), (928, 1064), (929, 1090),
               (930, 1110), (932, 1140), (937, 1160), (946, 1170), (960, 1178), (980, 1182), (1000, 1184), (1020, 1185)]
R1_POT = dict(left=928.0, right=1145.0, top=962.0, bottom=1185.0, axis=1036.5, trunk_foot=(1030.0, 968.0), rim=(936.0, 1137.0))


def poly_soft(pts, blur=0.8):
    m = np.zeros((SIZE[1] * 4, SIZE[0] * 4), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts, np.float64) * 16).astype(np.int32)], 1, lineType=cv2.LINE_AA, shift=2)
    m = cv2.resize(m.astype(np.float32), SIZE, interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(m, (0, 0), blur) if blur else m


def r1_pot_mask():
    ax = R1_POT["axis"]
    left = R1_POT_LEFT
    right = [(2 * ax - x, y) for x, y in reversed(left)]
    # the rim's top: a flat arc from the left corner over the axis (962) to the right corner
    top = [(x, 962 + 6 * ((x - ax) / (ax - 936)) ** 2) for x in np.linspace(2 * ax - 936, 936, 25)]
    return poly_soft(left + [(ax, 1185.0)] + right + top)


def r1_donor():
    """R1's planter (pot + tree), basket and their contact shadows, in R1's own place (work px)"""
    regt = np.load(os.path.join(HERE, "work-reserve/r1-regt.npy")).astype(np.float32)
    below = R.scene()                                   # R1's own scene below (the corner is the same in the current scene)
    dE = X.lab_diff(regt, below, 1.0)
    bm = np.load(os.path.join(HERE, "work-reserve/r1-basket-mask.npz"))["basket"]
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a_b = np.clip(PW.guided(g, bm.astype(np.float32), 2, 1e-3), 0, 1)
    a_b = np.where(X.ero(bm, 1), 1.0, np.where(X.dil(bm, 2), a_b, 0.0)).astype(np.float32)
    pot = r1_pot_mask()
    # the tree (filler): crown and trunk above the rim. Its matte is solved against R1's OWN wall (R1 relit the plaster round the tree by
    # up to ~15 dE, so a difference to the scene below would carry patches of R1's wall along): the leaves and the trunk are what is
    # textured or greener than a smooth wall; the wall behind them is the normalised blur of R1 over the rest (sigma 14); alpha from the
    # difference to that wall; the leaf colour un-mixed from it, so a thin leaf carries no R1 wall into the input
    lab = cv2.cvtColor(regt, cv2.COLOR_RGB2LAB)
    Ls = lab[..., 0]
    hp = np.abs(Ls - cv2.GaussianBlur(Ls, (0, 0), 2.0))
    hp = cv2.GaussianBlur(hp, (0, 0), 1.5)
    reg = np.zeros(dE.shape, bool)
    reg[440:972, 860:1240] = True
    leaf0 = reg & ((hp > 2.2) | (lab[..., 1] < -2.0)) & (pot < 0.5)
    n, lab_, st, _ = cv2.connectedComponentsWithStats(X.dil(leaf0, 2).astype(np.uint8), connectivity=8)
    seed = lab_[900, 1031] if lab_[900, 1031] else 1 + int(np.argmax(st[1:, 4]))
    tree0 = X.dil(lab_ == seed, 3) & reg
    bgw = (~X.dil(tree0, 2)).astype(np.float32)
    Bw = cv2.GaussianBlur(regt * bgw[..., None], (0, 0), 14) / np.maximum(cv2.GaussianBlur(bgw, (0, 0), 14), 1e-4)[..., None]
    dB = X.lab_diff(regt, Bw.astype(np.float32), 0.7)
    strong = tree0 & (dB > 14)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(strong.astype(np.uint8), connectivity=8)
    for i in range(1, n2):
        if st2[i, 4] < 25:
            strong[lab2 == i] = False
    a_t = np.clip((dB - 5.0) / 14.0, 0, 1) * (tree0 & X.dil(strong, 4))
    a_t = np.where(pot > 0.5, 0.0, a_t).astype(np.float32)
    n3, lab3, st3, _ = cv2.connectedComponentsWithStats(X.dil(a_t > 0.25, 2).astype(np.uint8), connectivity=8)
    main = 1 + int(np.argmax(st3[1:, 4]))
    a_t = np.where(X.dil(lab3 == main, 2), a_t, 0.0).astype(np.float32)   # specks apart from the tree are dropped
    leaf_rgb = np.where((a_t > 0.08)[..., None], (regt - (1 - a_t[..., None]) * Bw) / np.maximum(a_t, 0.08)[..., None], regt)
    leaf_rgb = np.clip(leaf_rgb, 0, 1).astype(np.float32)
    crown = tree0
    a_p = np.maximum(pot, a_t) * (1 - a_b)              # R1's basket stands in front of R1's pot
    ys, xs = np.nonzero(crown)
    surf = X.surfaces()
    surf["front"] = W.furn_alpha() > 0.02
    sv = X.SPEC.get("planter"), X.SPEC.get("basket")
    X.SPEC["planter"], X.SPEC["basket"] = SPEC["planter"], dict(SPEC["basket"], onto="floor_wall")
    try:
        # the pot's contact shadow only: round the crown R1's darkening of the plaster is the model's relighting, not a shadow (soft
        # north light), so the tree carries none
        sh_p = X.shadow_one("planter", pot * (1 - a_b), regt, below, surf, {"basket": a_b, "tree": a_t})
        sh_b = X.shadow_one("basket", a_b, regt, below, surf, {"planter": a_p})
    finally:
        X.SPEC["planter"], X.SPEC["basket"] = sv
    return dict(regt=regt, leaf_rgb=leaf_rgb, a_pot=pot * (1 - a_b), a_tree=a_t * (1 - a_b), a_b=a_b, sh_p=sh_p, sh_b=sh_b,
                crown_box=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], bm=bm)


def body_rows(m):
    """a basket mask's body: the rows whose width is >= 80 % of the median body width (the loops are narrow)"""
    w = m.sum(1)
    ys = np.nonzero(w)[0]
    h = ys.max() - ys.min()
    med = np.median(w[ys.min() + int(0.4 * h):ys.max() - int(0.1 * h)])
    body = np.nonzero(w >= 0.8 * med)[0]
    rows = m[body.min() + int(0.4 * (body.max() - body.min())):body.max() - int(0.1 * (body.max() - body.min()))]
    xs = [np.nonzero(r_)[0] for r_ in rows if r_.any()]
    return dict(top=int(body.min()), bottom=int(ys.max()), left=float(np.median([x.min() for x in xs])),
                right=float(np.median([x.max() + 1 for x in xs])), loop_top=int(ys.min()), width=float(med))


def affine(src, dst):
    """x / y scale + offset taking src's (left, right, top, bottom) onto dst's"""
    sx = (dst["right"] - dst["left"]) / (src["right"] - src["left"])
    sy = (dst["bottom"] - dst["top"]) / (src["bottom"] - src["top"])
    return np.float32([[sx, 0, dst["left"] - sx * src["left"]], [0, sy, dst["top"] - sy * src["top"]]]), sx, sy


def warp(img, M, border=0.0):
    return cv2.warpAffine(img.astype(np.float32), M, SIZE, flags=cv2.INTER_AREA if M[0, 0] < 1 else cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def warp_pm(rgb, a, M):
    """premultiplied warp: (colour, alpha)"""
    wa = warp(a, M)
    wp = warp(rgb * a[..., None], M)
    return np.where((wa > 1e-4)[..., None], wp / np.maximum(wa, 1e-4)[..., None], 0.0).astype(np.float32), np.clip(wa, 0, 1)


def fit_r3a(D):
    C = clay_boxes()
    Mp, sxp, syp = affine(R1_POT, C["pot"])
    # the tree: uniform x syp about its trunk foot, which moves with the pot
    fx, fy = R1_POT["trunk_foot"]
    fx2, fy2 = Mp[0, 0] * fx + Mp[0, 2], Mp[1, 1] * fy + Mp[1, 2]
    st = float(syp)
    Mt = np.float32([[st, 0, fx2 - st * fx], [0, st, fy2 - st * fy]])
    src_b = body_rows(D["bm"])
    Mb, sxb, syb = affine(src_b, C["basket"])
    return dict(Mp=Mp, Mt=Mt, Mb=Mb, scale=dict(pot=[round(float(sxp), 4), round(float(syp), 4)], tree=round(st, 4),
                                                 basket=[round(float(sxb), 4), round(float(syb), 4)]),
                src=dict(pot=R1_POT, basket=src_b), dst=C)


# ------------------------------------------------------------------------------------------------- R2 as the donor of R3b
def r2_donor():
    """R2's pendant lifted onto the clay: R2 drew the card's tiered shade at the clay's size (~51 cm) but ~60 px (~10 cm) low and ~22 px
    (~3.6 cm) left (work-reserve/fidelity-r12.json). Its shade is fitted onto the clay shade's box (Z 1.90-2.18, 50 cm, under the hang point
    (0.20, 1.72)); its canopy and cord move sideways with it (the canopy stays on the ceiling) and the cord ends in the shade's top.
    Matte: the shade against R2's OWN wall (the normalised blur of R2 outside it), filled, guided; colour un-mixed from that wall"""
    regt = np.load(os.path.join(HERE, "work-reserve/r2-regt.npy")).astype(np.float32)
    below = R.scene()
    dE = X.lab_diff(regt, below, 1.0)
    reg = np.zeros(dE.shape, bool)
    reg[150:470, 1460:1850] = True
    m = reg & (dE > 6)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    shade = lab == 1 + int(np.argmax(st[1:, 4]))
    shade = cv2.morphologyEx(shade.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))).astype(bool)
    inv = (~shade).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    for i in range(1, n2):
        if i not in border:
            shade |= lab2 == i
    # the cord and the canopy: what differs from R2's wall in a narrow column over the shade's axis and in the canopy's box
    ys, xs = np.nonzero(shade)
    rows = np.nonzero(shade.sum(1) > 40)[0]
    sbox = dict(left=float(np.nonzero(shade[rows.min():rows.max() + 1].any(0))[0].min()),
                right=float(np.nonzero(shade[rows.min():rows.max() + 1].any(0))[0].max() + 1), top=float(rows.min()), bottom=float(rows.max() + 1))
    cord_x = 1655.0                                      # R2's cord (the strongest difference on rows 40-200) and its canopy's centre
    hang = np.zeros(dE.shape, bool)
    hang[0:int(sbox["top"]) + 4, int(cord_x) - 5:int(cord_x) + 6] = True
    hang[0:40, 1622:1690] = True
    other = ~X.dil(shade | hang, 3)
    bg = other.astype(np.float32)
    Bw = cv2.GaussianBlur(regt * bg[..., None], (0, 0), 14) / np.maximum(cv2.GaussianBlur(bg, (0, 0), 14), 1e-4)[..., None]
    dB = X.lab_diff(regt, Bw.astype(np.float32), 0.7)
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a_s = np.clip(PW.guided(g, shade.astype(np.float32), 2, 1e-3), 0, 1)
    a_s = np.where(X.ero(shade, 1), 1.0, np.where(X.dil(shade, 2), a_s, 0.0)).astype(np.float32)
    canopy = np.zeros(dE.shape, np.uint8)
    cv2.ellipse(canopy, (1657, 22), (34, 19), 0, 0, 360, 1, -1)   # R2's canopy disc (read on a 3x zoom: x 1627-1687, y 7-38) + 3 px
    canopy = canopy.astype(bool)
    a_h = (np.clip((dB - 2.5) / 6.0, 0, 1) * canopy).astype(np.float32)   # the canopy only; the cord is redrawn (cord_profile)
    # the cord: a 1-2 px bright core with its shaded side 2-3 px right of it (rows 130-200, where it crosses plain wall); its profile
    # colours are un-mixed from R2's wall, and it is redrawn from the canopy to the lifted shade's top (R2's cord crossed the ceiling
    # line at another place, so its pixels there cannot move)
    prof_a = np.array([0.35, 0.95, 0.75, 0.55, 0.30], np.float32)
    xc = 1654
    C = np.median(regt[130:200, xc - 1:xc + 4], axis=0)
    Bc = np.median(Bw[130:200, xc - 1:xc + 4], axis=0)
    prof_rgb = np.clip((C - (1 - prof_a[:, None]) * Bc) / prof_a[:, None], 0, 1).astype(np.float32)
    def unmix(a):
        return np.clip(np.where((a > 0.08)[..., None], (regt - (1 - a[..., None]) * Bw) / np.maximum(a, 0.08)[..., None], regt), 0, 1)
    return dict(regt=regt, rgb_s=unmix(a_s).astype(np.float32), a_s=a_s, rgb_h=unmix(a_h).astype(np.float32), a_h=a_h, sbox=sbox,
                cord_x=cord_x, cord_profile=dict(dx=list(range(-1, 4)), alpha=prof_a, rgb=prof_rgb, x=xc, top=38))


def fit_r3b(D):
    sil = R.parts_pendant()
    tiers = np.maximum.reduce([t[0] for t in sil["tiers"]]) > 0.5
    rows = np.nonzero(tiers.sum(1) > 40)[0]
    cols = np.nonzero(tiers[rows.min():rows.max() + 1].any(0))[0]
    dst = dict(left=float(cols.min()), right=float(cols.max() + 1), top=float(rows.min()), bottom=float(rows.max() + 1))
    Ms, sx, sy = affine(D["sbox"], dst)
    # the cord keeps R2's relation to its shade (1.5 px left of the shade's centre); the canopy stays on the ceiling
    c_src = 0.5 * (D["sbox"]["left"] + D["sbox"]["right"])
    c_dst = Ms[0, 0] * c_src + Ms[0, 2]
    dx_h = (c_dst + (D["cord_x"] - c_src)) - D["cord_x"]
    Mh = np.float32([[1, 0, dx_h], [0, 1, 0]])
    return dict(Ms=Ms, Mh=Mh, scale=dict(shade=[round(float(sx), 4), round(float(sy), 4)], cord_canopy_dx_px=round(float(dx_h), 1)),
                src=dict(shade=D["sbox"], cord_x=D["cord_x"]), dst=dict(shade=dst))


# ------------------------------------------------------------------------------------------------- inputs
def make_input(pass_):
    os.makedirs(W.INP, exist_ok=True)
    os.makedirs(WR3, exist_ok=True)
    below = scene()
    rec = dict(pass_=pass_, below=rel(os.path.join(WR3, "scene-B9.png")),
               below_is="phase 1's ungraded base + the 9 layered defaults (steps 1-3 + reserve R1 / R2) + cushion set B")
    if pass_ == "r3a":
        D = r1_donor()
        F = fit_r3a(D)
        cp, ap = warp_pm(D["regt"], D["a_pot"], F["Mp"])
        ct, at = warp_pm(D["leaf_rgb"], D["a_tree"], F["Mt"])
        cb, ab = warp_pm(D["regt"], D["a_b"], F["Mb"])
        shp = 1 - np.maximum(warp(1 - D["sh_p"], F["Mp"]), 0)
        shb = 1 - np.maximum(warp(1 - D["sh_b"], F["Mb"]), 0)
        shp = np.where(np.maximum(ap, at) > 0.02, 1.0, shp)
        shb = np.where(ab > 0.02, 1.0, shb)
        img = below * shp[..., None]
        img = img * (1 - at[..., None]) + ct * at[..., None]
        img = img * (1 - ap[..., None]) + cp * ap[..., None]
        img = img * shb[..., None]
        img = img * (1 - ab[..., None]) + cb * ab[..., None]
        a_pl = np.maximum(ap, at)
        V = {"planter": np.clip(a_pl * (1 - ab), 0, 1), "basket": ab}
        sil = {"planter": a_pl, "basket": ab}
        # the clay silhouettes (full, for the outlines and the fidelity), as R1 drew them
        pp, pb = R.parts_planter(), R.parts_basket()
        clay = {"planter": np.maximum.reduce([pp["pot"], pp["trunk"], pp["crown"]]), "basket": np.maximum(pb["body"], pb["loops"]),
                "pot": pp["pot"], "basket_body": pb["body"]}
        rec["fit"] = dict(scale=F["scale"], src=F["src"], dst=F["dst"], M_pot=np.round(F["Mp"], 4).tolist(), M_tree=np.round(F["Mt"], 4).tolist(),
                          M_basket=np.round(F["Mb"], 4).tolist(), r1_crown_box=D["crown_box"])
    else:
        D = r2_donor()
        F = fit_r3b(D)
        cs, as_ = warp_pm(D["rgb_s"], D["a_s"], F["Ms"])
        ch, ah = warp_pm(D["rgb_h"], D["a_h"], F["Mh"])
        cp = D["cord_profile"]
        xc = int(round(cp["x"] + F["Mh"][0, 2]))
        top_s = int(np.nonzero((as_ > 0.5).any(1))[0].min())
        for k, dx in enumerate(cp["dx"]):
            ah[cp["top"]:top_s + 6, xc + dx] = np.maximum(ah[cp["top"]:top_s + 6, xc + dx], cp["alpha"][k])
            ch[cp["top"]:top_s + 6, xc + dx] = cp["rgb"][k]
        ah = np.where(as_ > 0.5, 0.0, ah)                  # the cord ends in the shade's top
        img = below * (1 - ah[..., None]) + ch * ah[..., None]
        img = img * (1 - as_[..., None]) + cs * as_[..., None]
        a_pd = np.maximum(as_, ah)
        V = {"pendant": a_pd}
        sil = {"pendant": a_pd}
        pp = R.parts_pendant()
        clay = {"pendant": np.maximum.reduce([t[0] for t in pp["tiers"]] + [pp["cord"], pp["canopy"]]),
                "shade": np.maximum.reduce([t[0] for t in pp["tiers"]])}
        rec["fit"] = dict(scale=F["scale"], src=F["src"], dst=F["dst"], M_shade=np.round(F["Ms"], 4).tolist(),
                          M_cord_canopy=np.round(F["Mh"], 4).tolist())
    ea = layered_alpha()
    clash = {k: int(((V[k] > 0.5) & (ea > 0.5)).sum()) for k in V}
    img = np.clip(img, 0, 1)
    p = os.path.join(W.INP, f"{pass_}-input.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, img)
    np.savez_compressed(os.path.join(WR3, f"ph-{pass_}.npz"), **{f"sil_{k}": sil[k].astype(np.float16) for k in sil},
                        **{f"vis_{k}": V[k].astype(np.float16) for k in V}, **{f"clay_{k}": clay[k].astype(np.float16) for k in clay})
    reps = {}
    for k in V:
        ys, xs = np.nonzero(V[k] > 0.5)
        reps[k] = dict(px=int((V[k] > 0.5).sum()), box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                       over_layered_defaults_px=clash[k])
    rec.update(placeholders=reps, camera="house plan 1.3.5 M0 via step0_clay_checks.P",
               note="PHOTOGRAPHIC placeholders: the product's own earlier render fitted in code onto its clay box (card size, plan place); "
                    "visible parts only; the earlier render reaches a layer only through the new render")
    json.dump(rec, open(os.path.join(W.INP, f"{pass_}-input.json"), "w"), indent=1)
    print(p, json.dumps(dict(placeholders=reps, fit=rec["fit"].get("scale")), indent=1))


def load_ph(pass_):
    z = np.load(os.path.join(WR3, f"ph-{pass_}.npz"))
    get = lambda pre: {k[len(pre):]: z[k].astype(np.float32) for k in z.files if k.startswith(pre)}  # noqa: E731
    return get("sil_"), get("vis_"), get("clay_")

# ------------------------------------------------------------------------------------------------- the result
def cut_product(k, regt, below, V, zone, front, dE):
    saved = X.SPEC.get(k)
    X.SPEC[k] = SPEC[k]
    try:
        return X.cut_one(k, regt, below, V, zone, front, dE)
    finally:
        if saved is None:
            X.SPEC.pop(k, None)
        else:
            X.SPEC[k] = saved


def pot_snap(a, regt, V, front):
    """the pot's rim lip and its opening are the plaster's colour and value, so GrabCut drops them. The render kept the placeholder's pot
    within ~1-2 px (fidelity-r3.json), so the pot (the placeholder below the crown, rows >= 1036) is taken as the placeholder's own
    silhouette snapped to the render's edges by a guided filter (r 4): 1 inside 4 px of it, 0 beyond 6 px; the tree keeps the general cut;
    never over the basket (front)"""
    pot = np.zeros(V.shape, np.float32)
    pot[1036:] = V[1036:]
    ph = pot > 0.5
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    ap = np.clip(PW.guided(g, pot, 4, 1e-3), 0, 1)
    ap = np.where(X.ero(ph, 4), 1.0, np.where(X.dil(ph, 6), ap, 0.0))
    ap = np.where(X.dil(front, 1), 0.0, ap)
    return np.maximum(a, ap).astype(np.float32)


def canopy_fix(a, regt, below, V):
    """the pendant's ceiling canopy is a white disc on the white ceiling: GrabCut leaves holes in it. It is cut as a rigid convex piece:
    the convex hull of what differs from the scene below (dE > 5) inside the placeholder's canopy grown by 6 px, its edge from a guided
    filter on the render (r 2); the cord and the shade keep the general cut"""
    ys, xs = np.nonzero(V[:60] > 0.5)
    box = np.zeros(a.shape, bool)
    box[:60] = X.dil(V > 0.5, 6)[:60]
    dEs = X.lab_diff(regt, below, 0.8)
    m = box & (dEs > 5)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n < 2:
        return a
    big = lab == 1 + int(np.argmax(st[1:, 4]))
    hull = np.zeros(a.shape, np.uint8)
    cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(big.astype(np.uint8))), 1)
    hull = hull.astype(bool)
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    ac = np.clip(PW.guided(g, hull.astype(np.float32), 2, 1e-3), 0, 1)
    ac = np.where(X.ero(hull, 1), 1.0, np.where(X.dil(hull, 2), ac, 0.0)).astype(np.float32)
    out = a.copy()
    out[:60] = np.maximum(np.where(X.dil(hull, 3)[:60], 0.0, a[:60]), ac[:60])
    return out.astype(np.float32)


def fetch(pass_, url, pid, tid):
    """download into raw/, register onto the pass's input, tone-match to the scene below outside the product zones, cut the products
    (nearest first) and their shadows into work-r3/, and record how much the model changed the placeholders"""
    os.makedirs(os.path.join(WR3, "layers"), exist_ok=True)
    os.makedirs(os.path.join(WR3, "shadows"), exist_ok=True)
    slots = PASSES[pass_]
    p = os.path.join(W.RAW, f"{pass_}-seedream.png")
    if not os.path.exists(p):
        p = X.fetch_raw(url, f"{pass_}-seedream.png")
    out = PW.load(p)
    returned = list(Image.open(p).size)
    if out.shape[1::-1] != SIZE:
        out = cv2.resize(out, SIZE, interpolation=cv2.INTER_LANCZOS4)
    inp = PW.load(os.path.join(W.INP, f"{pass_}-input.png"))
    below = scene()
    reg, M = PW.register(out, inp)
    sil, V, clay = load_ph(pass_)
    zones = {k: X.dil(np.maximum(V[k], clay.get(k, V[k])) > 0.02, SPEC[k]["margin"]) for k in slots}
    Z = np.zeros(SIZE[::-1], bool)
    for z in zones.values():
        Z |= z
    regt, G = X.tone_match(reg, below, Z)
    dE = X.lab_diff(regt, below)
    fa = W.furn_alpha()
    surf = X.surfaces()
    surf["front"] = fa > 0.02
    ea = layered_alpha()
    order = sorted(slots, key=lambda k: DEPTH[k])
    taken = np.zeros(Z.shape, bool)
    alphas = {}
    for k in order:
        front = taken.copy() | (ea > 0.5)
        fill, a = cut_product(k, regt, below, V[k], zones[k], front, dE)
        if k == "pendant":
            a = canopy_fix(a, regt, below, V[k])
            fill = a > 0.5
        if k == "planter":
            a = pot_snap(a, regt, V[k], front)
            fill = a > 0.5
        alphas[k] = a
        taken |= fill
    shadows = {}
    for k in slots:
        others = {j: alphas[j] for j in slots if j != k}
        others["_layered"] = ea
        saved = X.SPEC.get(k)
        X.SPEC[k] = SPEC[k]
        try:
            shadows[k] = X.shadow_one(k, alphas[k], regt, below, surf, others)
        finally:
            X.SPEC[k] = saved
    recs = {}
    dIn = X.lab_diff(regt, inp, 1.0)                   # the model's change against its own input (the placeholders)
    for k in slots:
        a, sh = alphas[k], shadows[k]
        PW.save(os.path.join(WR3, "layers", f"{k}.png"), regt, alpha=a)
        PW.save(os.path.join(WR3, "shadows", f"{k}.png"), np.repeat(sh[..., None], 3, 2))
        ph = V[k] > 0.5
        ys, xs = np.nonzero(a > 0.5)
        recs[k] = dict(alpha_px=int((a > 0.5).sum()), soft_px=int(((a > 0.02) & (a < 0.98)).sum()),
                       box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                       placeholder_px=int(ph.sum()), placeholder_covered=round(float((ph & (a > 0.5)).sum() / max(1, ph.sum())), 3),
                       outside_placeholder_px=int(((a > 0.5) & ~X.dil(ph, 2)).sum()),
                       shadow_px_below_0_97=int((sh < 0.97).sum()), shadow_min=round(float(sh.min()), 3),
                       model_change_vs_placeholder_dE=dict(median=round(float(np.median(dIn[ph])), 2), p90=round(float(np.percentile(dIn[ph], 90)), 2)))
    far = ~X.dil(Z, 40)
    drift = np.abs(PW.Lstar(reg) - PW.Lstar(below))[far]
    drift_t = np.abs(PW.Lstar(regt) - PW.Lstar(below))[far]
    np.save(os.path.join(WR3, f"{pass_}-regt.npy"), regt.astype(np.float16))
    rec = dict(id=NAMES[pass_], pass_=pass_, slots=slots, returned_px=returned, raw=rel(p), register_to_input=np.round(M, 4).tolist(),
               tone_gain_median=[round(float(np.median(G[..., c][Z])), 4) for c in range(3)],
               model_drift_outside_zones_L=dict(raw_median=round(float(np.median(drift)), 2), raw_p95=round(float(np.percentile(drift, 95)), 2),
                                                after_tone_match_median=round(float(np.median(drift_t)), 2),
                                                note="the model's redraw outside the products; discarded (the scene below is kept)"),
               products=recs, placeholder_id=pid, task_id=tid, url=url)
    json.dump(rec, open(os.path.join(WR3, f"{pass_}-fetch.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k in ("register_to_input", "model_drift_outside_zones_L", "products", "tone_gain_median")}, indent=1))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "scene":
        scene()
    elif cmd == "input":
        make_input(args[0])
    elif cmd == "fetch":
        fetch(args[0], *args[1:4])
    else:
        raise SystemExit(__doc__)
