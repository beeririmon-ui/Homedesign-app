#!/usr/bin/env python3
"""
pass_r5.py: variant passes 4' and 5' of the warm-modern living-room tool, phase 2 (render-agent, 2026-11-11).
Brief: briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md; the designer: docs/proposals/wm-phase2-checkpoint-eye-2026-11-11.md
(section 2: the vases' point, section 6: the planter whole, section 7: the passes). Approval PH2-WM (owner); 650 per pass, var2_estimate_cost
before each; no third pass.

  4'  vase (the default, re-rendered at the clay point; step0/vase-point-r5.json), curtains v2, framed-art v2, accent-sconces v2
  5'  planter (the default, WHOLE, the basket out of the input), vase v2 (the same point), accent-sconces v3, pendant v2

The R3 method (the manager accepted it): PHOTOGRAPHIC placeholders fitted in code to the clay box at the card size and the plan place:
the product's own earlier render where there is one (the vase: R4's code-sized layer, carried to the clay point; the planter: R3a's pot,
completed to the card's clay), otherwise the card-sized clay in the room's own light (the variants have no earlier render): the default's
own form where the slot fixes the form (the curtain stack, the walnut frames), the card's solid elsewhere. The model re-renders material,
light and contact; nothing of a placeholder reaches a layer except through the new render. Each pass is drawn on the CURRENT scene (the r4
stack with the R5 colour fixes, cushion set B) with the pass's slots taken out; the cut is against that scene (the 'below').

Each product is cut, after the ECC registration and the local tone match of extract.py, by extract.cut_one (GrabCut seeded by its
placeholder), its contact shadow by extract.shadow_one with the luminance taken on the ENCODED values (the multiply works on sRGB-encoded
pixels; the brief: the shadow recipe bug) and R4's edge treatment (fix_r4.shadow_ext). Files: work-r5/layers/<slot>[-v2|-v3].png,
work-r5/shadows/..., work-r5/<pass>-fetch.json. New files only.

  python3 pass_r5.py input p4|p5
  python3 pass_r5.py fetch p4|p5 <url> <placeholder_id> <task_id>
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import extract as X  # noqa: E402
import fix_r4 as F4  # noqa: E402
import grade_cut_r4 as G4  # noqa: E402  (sets the r4 sources in grade_cut_r12.SRC)
import grade_cut_r12 as G12  # noqa: E402
import phase2_wm as W  # noqa: E402
import stack  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR5 = os.path.join(HERE, "work-r5")
SIZE = W.SIZE
POINT = tuple(json.load(open(os.path.join(HERE, "step0/vase-point-r5.json")))["chosen_point"]["xy"])
# the R5 code fixes join the stack (fix_r5.py): the curtains' colour, the magazine holder's rods
G12.SRC.update({k: (os.path.join(WR5, "layers"), os.path.join(WR5, "shadows")) for k in ("curtains", "magazine-holder")})
ACCEPTED = list(G4.ACCEPTED)
PASSES = {
    "p4": dict(products=[("vase", "default"), ("curtains", "v2"), ("framed-art", "v2"), ("accent-sconces", "v2")],
               remove=["vase", "curtains", "framed-art", "accent-sconces"], name="wm-ph2-variants-p4"),
    "p5": dict(products=[("planter", "default"), ("vase", "v2"), ("accent-sconces", "v3"), ("pendant", "v2")],
               remove=["planter", "basket", "vase", "accent-sconces", "pendant"], name="wm-ph2-variants-p5"),
}
CARDS = {
    ("vase", "default"): ("vase-cj-textured-white-stoneware", {"size": "large"}, "CJJT312391803CX"),
    ("vase", "v2"): ("vase-cj-charcoal-carved", {"style": "style-b"}, "CJJT276474102BY"),
    ("curtains", "v2"): ("curtains-aliexpress-linen-blend-s-fold-180502", {"style": "s-fold", "size": "132x270"}, "12000059196236244"),
    ("framed-art", "v2"): ("framed-art-aliexpress-modern-minimalist-neutral-gallery-802995", {"color": "01 / 02 / 03", "size": "see note"}, "12000038165012545"),
    ("accent-sconces", "v2"): ("accent-sconces-cj-travertine-block-updown-8x16", {"style": "type-b", "other": "indoor"}, "CJYD254545505EV"),
    ("accent-sconces", "v3"): ("accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket", {"other": "type-b"}, "CJYD320857702BY"),
    ("pendant", "v2"): ("pendant-cj-pleated-pumpkin-lantern-40", {"size": "40"}, "CJYD272646801AZ"),
    ("planter", "default"): ("planter-cj-cement-ribbed-belly", {"color": "beige", "size": "large"}, "CJJT154204209IR"),
}
SPEC = dict(X.SPEC)
SPEC.update({"planter": dict(margin=26, band=40, onto="floor", z=32, thin=True)})   # R3a: the pot's shadow on the floor only
DEPTH = {"vase": 4.355, "curtains": 2.9, "framed-art": 4.47, "accent-sconces": 4.6, "planter": 4.999, "pendant": 2.913}


def rel(p):
    return os.path.relpath(p, W.REPO)


def fname(slot, var):
    return slot if var == "default" else f"{slot}-{var}"


def f32(p, mode=None):
    im = Image.open(p)
    if mode:
        im = im.convert(mode)
    return np.asarray(im).astype(np.float32) / 255.0


def lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def rgb_of(L, A, B):
    return np.clip(cv2.cvtColor(np.dstack([L, A, B]).astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


_P = []


def parts():
    if not _P:
        _P.append(stack.base_parts())
    return _P[0]


def compose(items, src=None):
    saved = dict(G12.SRC)
    if src:
        G12.SRC.update(src)
    try:
        return G12.compose(set(items) | {"cushions"}, parts(), cushion_set="B")
    finally:
        G12.SRC.clear()
        G12.SRC.update(saved)


def scene(pass_):
    """the pass's 'below': the r4 stack + the R5 fixes, set B, without the pass's slots"""
    p = os.path.join(WR5, f"scene-{pass_}.png")
    if os.path.exists(p):
        return PW.load(p)
    os.makedirs(WR5, exist_ok=True)
    U, _ = compose([k for k in ACCEPTED if k not in PASSES[pass_]["remove"]])
    PW.save(p, U)
    return PW.load(p)


# ------------------------------------------------------------------------------------------------- canvas helpers
def to_work(m_canvas):
    return cv2.resize(m_canvas.astype(np.float32), SIZE, interpolation=cv2.INTER_AREA)


def quad(pts):
    return to_work(S0.raster([pts]))


def wall_light(below, m, sig=20):
    """the scene's own light round a wall piece (normalised blur of L* from outside it), relative to its median"""
    Lb = PW.Lstar(below).astype(np.float32)
    w = (m < 0.02).astype(np.float32)
    d1 = cv2.GaussianBlur(w, (0, 0), sig)
    n1 = cv2.GaussianBlur(Lb * w, (0, 0), sig) / np.maximum(d1, 1e-4)
    d2 = cv2.GaussianBlur(w, (0, 0), 6 * sig)                 # inside a large piece (a 200 px frame) the near ring has no support
    n2 = cv2.GaussianBlur(Lb * w, (0, 0), 6 * sig) / np.maximum(d2, 1e-4)
    t = np.clip((d1 - 0.02) / 0.10, 0, 1)
    nb = n1 * t + n2 * (1 - t)
    ref = float(np.median(nb[m > 0.5])) if (m > 0.5).any() else 70.0
    return nb, ref


# ------------------------------------------------------------------------------------------------- placeholders, pass 4'
def ph_vase_default(below):
    """R4's code-sized vase (Large D16 x H32 + the dry branch) carried to the clay point at its card size there: x and y scale to the
    card's cylinder projected at the point, the foot's contact onto the projected foot; its contact shadow at the foot's scale"""
    Lv = f32(os.path.join(HERE, "work-r4/layers/vase.png"))
    rgb, a = Lv[..., :3], Lv[..., 3]
    Sh = f32(os.path.join(HERE, "work-r4/shadows/vase.png"), "L")
    m = F4.vase_measure(a, rgb)
    card = F4.card_vase_box(*POINT)
    sx, sy = card["width"] / m["width_px"], card["height"] / m["height_px"]
    tx, ty = card["centre_x"] - sx * m["foot_centre_x"], card["bottom"] - sy * m["foot_contact_y"]
    Ml = np.float32([[sx, 0, tx], [0, sy, ty]])
    Ms = np.float32([[sx, 0, tx], [0, sx, card["bottom"] - sx * m["foot_contact_y"]]])
    wa = cv2.warpAffine(a, Ml, SIZE, flags=cv2.INTER_AREA)
    wp = cv2.warpAffine(rgb * a[..., None], Ml, SIZE, flags=cv2.INTER_AREA)
    rgb2 = np.where((wa > 1e-4)[..., None], wp / np.maximum(wa, 1e-4)[..., None], 0.0)
    sh2 = 1 - cv2.warpAffine(1 - Sh, Ms, SIZE, flags=cv2.INTER_AREA)
    sh2 = np.where(wa >= 0.999, 1.0, sh2)
    m2 = F4.vase_measure(np.clip(wa, 0, 1), rgb2)
    _, vbr, _ = S0.P(POINT[0], POINT[1], 1.05)
    rec = dict(source="work-r4/layers/vase.png (R4: the R3 render scaled in code to the card) and its shadow", measured_source=m,
               card_at_point_px={k: round(v, 2) for k, v in card.items()}, matrix_layer=np.round(Ml, 4).tolist(), matrix_shadow=np.round(Ms, 4).tolist(),
               scale=[round(float(sx), 4), round(float(sy), 4)], measured_placeholder=m2,
               branch_top_px=int(np.nonzero((wa > 0.5).any(1))[0].min()), branch_Z105_row_px=round((S0.CY + vbr * S0.CH) / S0.GH * SIZE[1], 1))
    return dict(rgb=rgb2.astype(np.float32), a=np.clip(wa, 0, 1).astype(np.float32), sh=np.clip(sh2, 0, 1).astype(np.float32), rec=rec)


def ph_curtains_v2(below):
    """the slot's form: the default's stack (its free alpha, the same drop, the same inner edge +-0.003 u) and its folds' light (L*,
    smoothed sigma 1.5 so the default's slub does not carry), as an undyed clay (a* 0, b* 2), +3 L* (the card's lighter natural); the
    default's floor shadow"""
    L = f32(os.path.join(WR5, "layers/curtains.png"))
    af = f32(os.path.join(WR5, "layers/curtains-free-alpha.png"), "L")
    Lw = lab(L[..., :3])
    Ls = cv2.GaussianBlur(Lw[..., 0], (0, 0), 1.5)
    rgb = rgb_of(np.clip(Ls + 3.0, 0, 100), np.zeros_like(Ls), np.full_like(Ls, 2.0))
    sh = f32(os.path.join(WR5, "shadows/curtains.png"), "L")
    return dict(rgb=rgb.astype(np.float32), a=L[..., 3], a_free=af, sh=sh,
                rec=dict(source="work-r5/layers/curtains.png (the default's form, R5 colour) -> undyed clay: L* smoothed sigma 1.5, +3, a* 0, b* 2"))


def ph_framed_art_v2(below):
    """the slot's form: the default's three walnut frames and their wall shadows (the variants keep the same frame, scene brief section
    3); inside each frame (the frame's piece eroded 6 px: the walnut moulding is ~4-5 px) a blank canvas in the wall's own light"""
    L = f32(os.path.join(W.WORK, "layers/framed-art.png"))
    rgb, a = L[..., :3].copy(), L[..., 3]
    sh = f32(os.path.join(W.WORK, "shadows/framed-art.png"), "L")
    n, lb, st, _ = cv2.connectedComponentsWithStats((a > 0.5).astype(np.uint8))
    nb, ref = wall_light(below, a)
    inner_all = np.zeros(a.shape, bool)
    boxes = []
    Lw = lab(rgb)
    walnut = (Lw[..., 0] < 62) & (Lw[..., 1] > 7) & (Lw[..., 2] > 9)
    mould = {}
    for i in range(1, n):
        if st[i, 4] < 500:
            continue
        piece = (lb == i) & (a > 0.5)
        x0, y0, w_, h_ = st[i, :4]
        # per side: the walnut moulding's inner edge, as an offset from the piece's alpha edge (the median over the lines whose walnut run
        # starts within 8 px of the edge and is 2-10 px long; a run that merges into a brown print is longer and is skipped)
        off, starts, lens = {}, {}, {}
        for side in ("left", "right", "top", "bottom"):
            st_l, ln_l = [], []
            lines = range(y0 + int(0.1 * h_), y0 + int(0.9 * h_)) if side in ("left", "right") else range(x0 + int(0.1 * w_), x0 + int(0.9 * w_))
            for q in lines:
                line = piece[q] if side in ("left", "right") else piece[:, q]
                wl = walnut[q] if side in ("left", "right") else walnut[:, q]
                idx = np.nonzero(line)[0]
                if not len(idx):
                    continue
                seq = list(range(idx.min(), idx.max() + 1) if side in ("left", "top") else range(idx.max(), idx.min() - 1, -1))
                st_ = next((j for j, p in enumerate(seq[:20]) if wl[p]), None)
                if st_ is None:
                    continue
                ln = 0
                while st_ + ln < len(seq) and wl[seq[st_ + ln]]:
                    ln += 1
                st_l.append(st_)
                if 2 <= ln <= 10:
                    ln_l.append(ln)
            starts[side] = int(np.median(st_l)) if st_l else 6
            lens[side] = int(np.median(ln_l)) if ln_l else None
        known = [v for v in lens.values() if v]
        for side in starts:
            off[side] = starts[side] + (lens[side] or int(np.median(known)) if known else 5) + 1
        mould[i] = off
        inner = np.zeros(a.shape, bool)
        for y in range(y0, y0 + h_):
            xs_ = np.nonzero(piece[y])[0]
            if len(xs_):
                inner[y, xs_.min() + off["left"]:xs_.max() + 1 - off["right"]] = True
        for x in range(x0, x0 + w_):
            ys_ = np.nonzero(piece[:, x])[0]
            if len(ys_):
                colm = np.zeros(a.shape[0], bool)
                colm[ys_.min() + off["top"]:ys_.max() + 1 - off["bottom"]] = True
                inner[:, x] &= colm
        inner &= piece
        inner_all |= inner
        ys, xs = np.nonzero(inner)
        boxes.append(dict(box=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], moulding_offset_px=off))
    Lc = np.clip(nb * 0.97, 0, 96)
    canvas = rgb_of(Lc, np.full_like(Lc, 0.6), np.full_like(Lc, 4.5))
    rgb = np.where(inner_all[..., None], canvas, rgb)
    return dict(rgb=rgb.astype(np.float32), a=a, sh=sh, rec=dict(source="work/layers/framed-art.png (the default's frames) with the print "
                                                                        "areas blanked to canvas", print_areas_px=boxes))


def clay_box_sconce(below, x, w, d, h, zc=1.75, tone=(0.86, 0.80, 0.72)):
    """a card-sized block on the back wall (Y 0 .. d) centred at (x, zc): front, the side the camera sees and the underside, shaded for
    the soft light from the left window and the wall's own light"""
    x0, x1, z0, z1 = x - w / 2, x + w / 2, zc - h / 2, zc + h / 2
    front = quad([(x0, d, z0), (x1, d, z0), (x1, d, z1), (x0, d, z1)])
    sx = x1 if x < S0.CAM["loc"][0] else x0
    side = quad([(sx, 0.0, z0), (sx, d, z0), (sx, d, z1), (sx, 0.0, z1)])
    under = quad([(x0, 0.0, z0), (x1, 0.0, z0), (x1, d, z0), (x0, d, z0)])
    side_f = 0.74 if sx == x1 else 1.02                       # the +X side faces away from the window; the -X side faces it
    a = np.clip(np.maximum.reduce([front, side, under]), 0, 1)
    nb, ref = wall_light(below, a)
    lightf = np.clip(nb / max(ref, 1e-3), 0.85, 1.15)
    shade = np.where(front >= np.maximum(side, under), 0.92, np.where(side >= under, side_f, 0.62))
    rgb = np.array(tone, np.float32)[None, None, :] * (shade * lightf)[..., None]
    return np.clip(rgb, 0, 1).astype(np.float32), a.astype(np.float32)


def ph_sconces_v2(below):
    """the card's block (W8 x D8 x H16, 'Rectangle - Indoor Model') at the two plates (-0.85, 0, 1.75) and (1.25, 0, 1.75), in the
    travertine's light clay; no shadow (the model draws the contact)"""
    rgb = np.zeros(SIZE[::-1] + (3,), np.float32)
    a = np.zeros(SIZE[::-1], np.float32)
    for x in (-0.85, 1.25):
        c, ai = clay_box_sconce(below, x, 0.08, 0.08, 0.16)
        rgb = np.where((ai > a)[..., None], c, rgb)
        a = np.maximum(a, ai)
    return dict(rgb=rgb, a=a, sh=np.ones_like(a), rec=dict(source="card-sized clay blocks W8 x D8 x H16 at the plates (step 0's camera)"))


PH = {("vase", "default"): ph_vase_default, ("curtains", "v2"): ph_curtains_v2, ("framed-art", "v2"): ph_framed_art_v2,
      ("accent-sconces", "v2"): ph_sconces_v2}


# ------------------------------------------------------------------------------------------------- the input
def make_input(pass_):
    os.makedirs(W.INP, exist_ok=True)
    below = scene(pass_)
    phd = os.path.join(WR5, f"ph-{pass_}")
    os.makedirs(os.path.join(phd, "layers"), exist_ok=True)
    os.makedirs(os.path.join(phd, "shadows"), exist_ok=True)
    recs, src = {}, {}
    for slot, var in PASSES[pass_]["products"]:
        ph = PH[(slot, var)](below)
        PW.save(os.path.join(phd, "layers", f"{slot}.png"), ph["rgb"], alpha=ph["a"])
        if "a_free" in ph:
            Image.fromarray((np.clip(ph["a_free"], 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(phd, "layers", f"{slot}-free-alpha.png"))
        PW.save(os.path.join(phd, "shadows", f"{slot}.png"), np.repeat(ph["sh"][..., None], 3, 2))
        src[slot] = (os.path.join(phd, "layers"), os.path.join(phd, "shadows"))
        recs[slot] = dict(variant=var, card=CARDS[(slot, var)][0], **ph["rec"])
    slots = [s for s, _ in PASSES[pass_]["products"]]
    keep = [k for k in ACCEPTED if k not in PASSES[pass_]["remove"]]
    U, steps = compose(keep + slots, src)
    # the visible part of each placeholder: its effective alpha, under every later layer of the stack
    V = {}
    order = [st["k"] for st in steps]
    for i, st in enumerate(steps):
        if st["k"] not in slots:
            continue
        v = st["a_eff"].copy()
        for st2 in steps[i + 1:]:
            v = v * (1 - (st2["a_eff"] if st2["k"] != "cushions" else st2["a"]))
        V[st["k"]] = np.clip(v, 0, 1).astype(np.float32)
    sil = {st["k"]: st["a"].astype(np.float32) for st in steps if st["k"] in slots}
    p = os.path.join(W.INP, f"{pass_}-input.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    PW.save(p, U)
    np.savez_compressed(os.path.join(WR5, f"ph-{pass_}.npz"), **{f"vis_{k}": V[k].astype(np.float16) for k in V},
                        **{f"sil_{k}": sil[k].astype(np.float16) for k in sil})
    rep = {}
    for k in V:
        ys, xs = np.nonzero(V[k] > 0.5)
        rep[k] = dict(recs[k], visible_px=int((V[k] > 0.5).sum()), box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    J = dict(pass_=pass_, below=rel(os.path.join(WR5, f"scene-{pass_}.png")),
             below_is="the r4 stack with the R5 colour fixes (curtains, magazine holder rods), cushion set B, without " + ", ".join(PASSES[pass_]["remove"]),
             vase_point=dict(xy=POINT, record="step0/vase-point-r5.json"), stack_order=order, placeholders=rep,
             note="PHOTOGRAPHIC placeholders (R3 method): the product's own earlier render fitted to the clay at card size and plan place, or the "
                  "card-sized clay in the room's light; visible parts only; a placeholder reaches a layer only through the new render")
    json.dump(J, open(os.path.join(W.INP, f"{pass_}-input.json"), "w"), indent=1, default=float)
    print(p, json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("visible_px", "box_px", "scale", "measured_placeholder", "branch_top_px",
                                                                         "branch_Z105_row_px", "print_areas_px")} for k, v in rep.items()}, indent=1, default=float))


def load_ph(pass_):
    z = np.load(os.path.join(WR5, f"ph-{pass_}.npz"))
    get = lambda pre: {k[len(pre):]: z[k].astype(np.float32) for k in z.files if k.startswith(pre)}  # noqa: E731
    return get("sil_"), get("vis_")


# ------------------------------------------------------------------------------------------------- the result
def enc_lum(x):
    return (np.clip(x, 0, 1) * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2)


def shadow_new(k, a, regt, below, surf, others):
    """extract.shadow_one with the luminance on the encoded values (the multiply acts on sRGB-encoded pixels), and R4's edge treatment
    (fix_r4.shadow_ext); the SPEC of extract (+ R3a's planter)"""
    saved_lum, saved_spec = PW.lum, F4.SPEC.get(k)
    PW.lum = enc_lum
    F4.SPEC[k] = SPEC[k]
    try:
        sh, sh0, info = F4.shadow_ext(k, a, regt, below, surf, others)
    finally:
        PW.lum = saved_lum
        if saved_spec is None:
            F4.SPEC.pop(k, None)
        else:
            F4.SPEC[k] = saved_spec
    return sh, info


def cut_snap_ph(V, regt, r=5):
    """the frames: the placeholder's frames snapped to the render's own edges (extract.cut_snap with the pass's placeholder)"""
    ph = V > 0.5
    g = cv2.cvtColor((regt * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    a = np.clip(PW.guided(g, V.astype(np.float32), r, 1e-3), 0, 1)
    a = np.where(X.ero(ph, r), 1.0, np.where(X.dil(ph, r), a, 0.0)).astype(np.float32)
    return a > 0.5, a


def cut(k, regt, below, V, zone, front, dE):
    saved = X.SPEC.get(k)
    X.SPEC[k] = SPEC[k]
    try:
        if k == "framed-art":
            return cut_snap_ph(V, regt)
        return X.cut_one(k, regt, below, V, zone, front, dE)
    finally:
        X.SPEC[k] = saved


def fetch(pass_, url, pid, tid):
    os.makedirs(os.path.join(WR5, "layers"), exist_ok=True)
    os.makedirs(os.path.join(WR5, "shadows"), exist_ok=True)
    prods = PASSES[pass_]["products"]
    slots = [s for s, _ in prods]
    p = os.path.join(W.RAW, f"{pass_}-r5-seedream.png")
    if not os.path.exists(p):
        p = X.fetch_raw(url, f"{pass_}-r5-seedream.png")
    out = PW.load(p)
    returned = list(Image.open(p).size)
    if out.shape[1::-1] != SIZE:
        out = cv2.resize(out, SIZE, interpolation=cv2.INTER_LANCZOS4)
    inp = PW.load(os.path.join(W.INP, f"{pass_}-input.png"))
    below = scene(pass_)
    reg, M = PW.register(out, inp)
    sil, V = load_ph(pass_)
    zones = {k: X.dil(np.maximum(V[k], sil[k]) > 0.02, SPEC[k]["margin"]) for k in slots}
    Z = np.zeros(SIZE[::-1], bool)
    for z in zones.values():
        Z |= z
    regt, G = X.tone_match(reg, below, Z)
    dE = X.lab_diff(regt, below)
    fa = W.furn_alpha()
    surf = X.surfaces()
    surf["front"] = fa > 0.02
    # what stands in front of each product in the scene (the layers above it in the stack, set B): never the product's
    keep = [k for k in ACCEPTED if k not in PASSES[pass_]["remove"]]
    above = {}
    for k in slots:
        m = np.zeros(SIZE[::-1], np.float32)
        for j in keep:
            if stack.ORDER.index(j) > stack.ORDER.index(k) and j != "rug":
                _, aj, _ = G12.product(j)
                m = np.maximum(m, aj)
        if stack.ORDER.index("cushions") > stack.ORDER.index(k):
            _, ac, _ = G12._STACK_PRODUCT("cushions", "B")
            m = np.maximum(m, ac)
        above[k] = m
    order = sorted(slots, key=lambda k: DEPTH[k])
    taken = np.zeros(Z.shape, bool)
    alphas, free = {}, {}
    for k in order:
        front = taken.copy() | (above[k] > 0.5)
        if k in stack.BEHIND:
            front |= fa > 0.5
        fill, a = cut(k, regt, below, V[k], zones[k], front, dE)
        if k == "pendant":
            a, _, cinfo = F4.canopy_cut(regt, below, a)
            fill = a > 0.5
        free[k] = a
        if k in stack.BEHIND:
            a = a * (1 - fa)
        alphas[k] = a
        taken |= fill
    recs = {}
    dIn = X.lab_diff(regt, inp, 1.0)
    for k, var in prods:
        others = {j: alphas[j] for j in slots if j != k}
        others["_above"] = above[k]
        sh, sinfo = shadow_new(k, alphas[k], regt, below, surf, others)
        nm = fname(k, var)
        PW.save(os.path.join(WR5, "layers", f"{nm}.png"), regt, alpha=alphas[k])
        if k in stack.BEHIND:
            Image.fromarray((np.clip(free[k], 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(WR5, "layers", f"{nm}-free-alpha.png"))
        PW.save(os.path.join(WR5, "shadows", f"{nm}.png"), np.repeat(sh[..., None], 3, 2))
        a = alphas[k]
        ph = V[k] > 0.5
        ys, xs = np.nonzero(a > 0.5)
        recs[nm] = dict(slot=k, variant=var, card=CARDS[(k, var)][0], alpha_px=int((a > 0.5).sum()), soft_px=int(((a > 0.02) & (a < 0.98)).sum()),
                        box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                        placeholder_px=int(ph.sum()), placeholder_covered=round(float((ph & (a > 0.5)).sum() / max(1, ph.sum())), 3),
                        outside_placeholder_px=int(((a > 0.5) & ~X.dil(ph, 2)).sum()),
                        shadow_px_below_0_97=int((sh < 0.97).sum()), shadow_min=round(float(sh.min()), 3), shadow_edge=sinfo,
                        model_change_vs_placeholder_dE=dict(median=round(float(np.median(dIn[ph])), 2), p90=round(float(np.percentile(dIn[ph], 90)), 2)))
    far = ~X.dil(Z, 40)
    drift = np.abs(PW.Lstar(reg) - PW.Lstar(below))[far]
    drift_t = np.abs(PW.Lstar(regt) - PW.Lstar(below))[far]
    np.save(os.path.join(WR5, f"{pass_}-regt.npy"), regt.astype(np.float16))
    rec = dict(id=PASSES[pass_]["name"], pass_=pass_, products=[fname(k, v) for k, v in prods], returned_px=returned, raw=rel(p),
               register_to_input=np.round(M, 4).tolist(), tone_gain_median=[round(float(np.median(G[..., c][Z])), 4) for c in range(3)],
               model_drift_outside_zones_L=dict(raw_median=round(float(np.median(drift)), 2), raw_p95=round(float(np.percentile(drift, 95)), 2),
                                                after_tone_match_median=round(float(np.median(drift_t)), 2),
                                                note="the model's redraw outside the products; discarded (the scene below is kept)"),
               cut=recs, placeholder_id=pid, task_id=tid, url=url)
    json.dump(rec, open(os.path.join(WR5, f"{pass_}-fetch.json"), "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in rec.items() if k in ("register_to_input", "model_drift_outside_zones_L", "cut", "tone_gain_median")}, indent=1, default=float))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "scene":
        scene(args[0])
    elif cmd == "input":
        make_input(args[0])
    elif cmd == "fetch":
        fetch(args[0], *args[1:4])
    else:
        raise SystemExit(__doc__)
