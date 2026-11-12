#!/usr/bin/env python3
"""
pass_r7.py: variant passes 6' and 7' of the warm-modern living-room tool, phase 2, R7 (render-agent, 2026-11-12).
Brief: briefs/render-wm-tool-r7-2026-11-12.md (B); the designer: docs/proposals/owner-answers-applied-2026-11-12.md (sections 1, 6);
slots 1.9.4. Approval PH2-WM (owner, up to 9,740; phase 2 so far 5,850); 650 per pass, var2_estimate_cost before each; no third pass.

  6'  bowl-v2 (white belly D21.2 x 6.4), candle-holders-v2 (ceramic trays on walnut feet), vase-v3 (white plum, M 33 x 22.4)
  7'  bowl-v3 (speckled ivory wide D21.3 x 5.2), candle-holders-v3 (iron plates D10.5, candles 15 / 16), curtains-v3 (Linen 200 x 260, 4 hook)

The R3 method: PHOTOGRAPHIC placeholders fitted in code at the card size and the plan place (slots 1.9.4; the table group's clay check
step0/r7-table-group/): the card's clay in the room's own window light (revolve() of pass_r5, step 0's camera), the slot's own form where the
slot fixes it (the curtain stack: the default's form; the dry olive branch: the default vase's). The model re-renders material, light and
contact; nothing of a placeholder reaches a layer except through the new render. Each pass is drawn on the CURRENT R7 scene (fix_r7.py:
planter, curtains at 270, the table defaults moved; cushion set B) with the pass's slots taken out; the cut is against that scene.
Cuts by extract.cut_one (GrabCut seeded by the placeholder); the contact shadow by the FROZEN recipe (extract.shadow_one as is).
Files: work-r7/layers/<name>.png, work-r7/shadows/<name>.png, work-r7/<pass>-fetch.json. New files only.

  python3 pass_r7.py input p6|p7
  python3 pass_r7.py fetch p6|p7 <url> <placeholder_id> <task_id>
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
import fix_r7 as F7  # noqa: E402
import grade_cut_r12 as G12  # noqa: E402
import pass_r5 as R5  # noqa: E402
import phase2_wm as W  # noqa: E402
import stack  # noqa: E402
import step0_clay_checks as S0  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR7 = F7.WR7
SIZE = W.SIZE
T_TOP = S0.TABLE_TOP
POINT = R5.POINT
BOWL_XY = (0.62, 1.94)
PASSES = {
    "p6": dict(products=[("bowl", "v2"), ("candle-holders", "v2"), ("vase", "v3")], remove=["bowl", "candle-holders", "vase"], name="wm-ph2-variants-p6"),
    "p7": dict(products=[("bowl", "v3"), ("candle-holders", "v3"), ("curtains", "v3")], remove=["bowl", "candle-holders", "curtains"],
               name="wm-ph2-variants-p7"),
}
CARDS = {
    ("bowl", "v2"): ("bowl-cj-glutinous-white-belly-bowl-21", {}, "2505301100271623400 (single vid; the card lists no SKU id)"),
    ("bowl", "v3"): ("bowl-cj-speckled-ivory-wide-bowl-21", {"other": "large-white"}, "CJCJ241334805EV"),
    ("candle-holders", "v2"): ("candle-holders-cj-ceramic-pedestal-tray", {"color": "white"}, "CJYD234800201AZ"),
    ("candle-holders", "v3"): ("candle-holders-aliexpress-matte-black-iron-pillar-set2", {"set": "2pc"}, "12000057351444960"),
    ("vase", "v3"): ("vase-cj-white-plum-hand-thrown", {"size": "m"}, "CJJT281811802BY"),
    ("curtains", "v3"): ("curtains-cj-japanese-linen-half-shade", {"color": "linen", "size": "200x260-4-hook"}, "CJYD218713946TG"),
}
SPEC = dict(X.SPEC)
SPEC["candle-holders"] = dict(margin=12, band=22, onto="table", z=65)        # NOT convex: a tray on a foot, a dish under a candle
SPEC["bowl"] = dict(margin=12, band=22, onto="table", z=65, convex=True)
SPEC["vase"] = dict(margin=18, band=22, onto="bench", z=16, thin=True)
DEPTH = {"bowl": 2.62, "candle-holders": 2.89, "vase": 4.355, "curtains": 2.9}
HOLDERS = {"v2": dict(A=(0.055, 1.74), B=(0.305, 1.68), candles=(0.075, 0.06)), "v3": dict(A=(0.15, 1.74), B=(0.34, 1.68), candles=(0.15, 0.16))}


def rel(p):
    return os.path.relpath(p, W.REPO)


def fname(slot, var):
    return f"{slot}-{var}"


f32, lab, rgb_of = F7.f32, F7.lab, F7.rgb_of
revolve, over, hex_rgb, to_work = R5.revolve, R5.over, R5.hex_rgb, R5.to_work


def scene(pass_):
    """the pass's 'below': the R7 stack (fix_r7), set B, without the pass's slots"""
    p = os.path.join(WR7, f"scene-{pass_}.png")
    if os.path.exists(p):
        return PW.load(p)
    os.makedirs(WR7, exist_ok=True)
    U, _ = F7.compose7(items=[k for k in F7.ACCEPTED if k not in PASSES[pass_]["remove"]])
    PW.save(p, U)
    return PW.load(p)


def ellipse_fill(cx, cy, r, z):
    return to_work(S0.raster([S0.circ(cx, cy, r, z)]))


def soft_contact(cx, cy, r, z=T_TOP, strength=0.30):
    """a hint of contact under a placeholder on the table: the foot's ellipse, blurred (the model draws the real one)"""
    m = ellipse_fill(cx, cy, r * 1.08, z)
    return 1 - strength * np.clip(cv2.GaussianBlur(m, (0, 0), 3.0) * 1.3, 0, 1)


# ------------------------------------------------------------------------------------------------- placeholders
PROF_BOWL2 = [(0.0, 0.040), (0.004, 0.046), (0.010, 0.062), (0.020, 0.080), (0.032, 0.094), (0.045, 0.102), (0.056, 0.105), (0.064, 0.106)]
PROF_BOWL3 = [(0.0, 0.030), (0.006, 0.034), (0.010, 0.048), (0.022, 0.070), (0.034, 0.088), (0.046, 0.102), (0.052, 0.1065)]
PROF_VASE3 = [(0.0, 0.050), (0.04, 0.056), (0.09, 0.068), (0.14, 0.083), (0.19, 0.098), (0.23, 0.108), (0.255, 0.112), (0.275, 0.110),
              (0.295, 0.098), (0.31, 0.075), (0.32, 0.045), (0.325, 0.022), (0.327, 0.018), (0.33, 0.0175)]   # card M: H 33, W 22.4, mouth 3.3


def ph_bowl(prof, body_hex, inner_hex, rim_hex=None, wall=0.005):
    """a card-sized bowl at (0.62, 1.94) on the table top: its outer wall (revolve) and its open top (the rim's ellipse filled with the
    inside, a touch darker toward the front where the far inner wall faces away from the window); the moved default's shadow"""
    cx, cy = BOWL_XY
    H = prof[-1][0]
    rgb, a = revolve(cx, cy, T_TOP, prof, hex_rgb(body_hex), amb=0.6)
    rtop = prof[-1][1]
    inner = ellipse_fill(cx, cy, rtop - wall, T_TOP + H)
    rim = ellipse_fill(cx, cy, rtop, T_TOP + H)
    ys = np.nonzero(inner.any(1))[0] if inner.any() else np.array([0])
    yy = np.arange(SIZE[1], dtype=np.float32)[:, None]
    t = np.clip((yy - ys.min()) / max(1, ys.max() - ys.min()), 0, 1)
    shade = 0.82 + 0.16 * t                                  # the far inner wall (top of the ellipse) is lit by the window, the near one less
    inside = hex_rgb(inner_hex)[None, None, :] * shade[..., None]
    rimc = hex_rgb(rim_hex or body_hex)
    rgb = np.where((rim > 0.5)[..., None], rimc[None, None, :], rgb)
    rgb = np.where((inner > 0.5)[..., None], inside, rgb)
    a = np.maximum(a, rim)
    sh = f32(os.path.join(WR7, "shadows/bowl.png"), "L")
    sh = np.where(a > 0.98, 1.0, sh)
    return rgb.astype(np.float32), a.astype(np.float32), sh.astype(np.float32)


def ph_bowl_v2(below):
    rgb, a, sh = ph_bowl(PROF_BOWL2, "#ECE7DC", "#E2DCCF")
    return dict(rgb=rgb, a=a, sh=sh, rec=dict(source="the card's clay (revolve(): D 21.2 x H 6.4, rounded belly, flared lip, #ECE7DC) at (0.62, 1.94); "
                                                     "the moved default bowl's shadow"))


def ph_bowl_v3(below):
    rgb, a, sh = ph_bowl(PROF_BOWL3, "#EDE6DA", "#EAE3D6", rim_hex="#B98A66", wall=0.004)
    return dict(rgb=rgb, a=a, sh=sh, rec=dict(source="the card's clay (revolve(): D 21.3 x H 5.2, wide cone on a small foot ring, ivory #EDE6DA, the "
                                                     "clay rim #B98A66) at (0.62, 1.94); the moved default bowl's shadow"))


def candle(cx, cy, z0, h, r=0.03):
    return revolve(cx, cy, z0, [(0.0, r), (h - 0.004, r), (h, r - 0.003)], hex_rgb("#EFE7D4"), amb=0.62)


def ph_holders_v2(below):
    """the ceramic trays (card: tray D13.3, 7.2 tall, 17 with the ball handles, handles along X): a walnut foot (cone D5 -> D7, H5), the
    white tray (D13.3, raised rim, top 7.2), two walnut balls D2.1 at the ends of the 17 cm span; a cream pillar candle D6 on each, A 7.5 /
    B 6. Far piece first (B, Y 1.68), then the near one (A, Y 1.74)"""
    d = HOLDERS["v2"]
    rgb = np.zeros(SIZE[::-1] + (3,), np.float32)
    a = np.zeros(SIZE[::-1], np.float32)
    sh = np.ones(SIZE[::-1], np.float32)
    walnut, white = hex_rgb("#7A5236"), hex_rgb("#F1EEE8")
    for w, h in (("B", d["candles"][1]), ("A", d["candles"][0])):
        cx, cy = d[w]
        parts = [revolve(cx, cy, T_TOP, [(0.0, 0.035), (0.05, 0.025)], walnut, amb=0.5),
                 revolve(cx, cy, T_TOP + 0.05, [(0.0, 0.060), (0.004, 0.0665), (0.022, 0.0665)], white, amb=0.62)]
        top = ellipse_fill(cx, cy, 0.0615, T_TOP + 0.072)
        for sx in (-0.0745, 0.0745):
            ball = [(0.0, 0.0), (0.003, 0.0065), (0.0105, 0.0105), (0.018, 0.0065), (0.021, 0.0)]
            parts.append(revolve(cx + sx, cy, T_TOP + 0.0505, ball, walnut, amb=0.55, nz=60, nt=180))
        for prgb, pa in parts:
            rgb, a = over(rgb, a, prgb, pa)
        rgb = np.where((top > 0.5)[..., None], (white * 0.9)[None, None, :], rgb)
        a = np.maximum(a, top)
        crgb, ca = candle(cx, cy, T_TOP + 0.065, h)
        rgb, a = over(rgb, a, crgb, ca)
        sh = np.minimum(sh, soft_contact(cx, cy, 0.035))
    sh = np.where(a > 0.98, 1.0, sh)
    return dict(rgb=rgb, a=a, sh=sh, rec=dict(source="card-sized clay (revolve()): walnut foot D5->7 x 5, white tray D13.3 to 7.2, walnut balls D2.1 "
                                                     "on the 17 cm span along X, cream candles D6 A 7.5 / B 6; A (0.055, 1.74), B (0.305, 1.68)"))


def ph_holders_v3(below):
    """the matte black iron plates (card estimate: D10.5 x H3 with a rolled rim and three ball feet); a cream pillar candle D7 standing
    in each, A 15 / B 16 (the pre-approved lever of section 1.4: 18 -> 16, the clay read 0.0184 against the throw at 18)"""
    d = HOLDERS["v3"]
    rgb = np.zeros(SIZE[::-1] + (3,), np.float32)
    a = np.zeros(SIZE[::-1], np.float32)
    sh = np.ones(SIZE[::-1], np.float32)
    iron = hex_rgb("#2A2A2A")
    for w, h in (("B", d["candles"][1]), ("A", d["candles"][0])):
        cx, cy = d[w]
        drgb, da = revolve(cx, cy, T_TOP + 0.004, [(0.0, 0.040), (0.006, 0.046), (0.018, 0.0505), (0.024, 0.0525), (0.026, 0.0525),
                                                   (0.028, 0.051)], iron, amb=0.45)
        rgb, a = over(rgb, a, drgb, da)
        dtop = ellipse_fill(cx, cy, 0.049, T_TOP + 0.032)
        rgb = np.where((dtop > 0.5)[..., None], (iron * 0.8)[None, None, :], rgb)
        a = np.maximum(a, dtop)
        crgb, ca = candle(cx, cy, T_TOP + 0.012, h, r=0.035)
        rgb, a = over(rgb, a, crgb, ca)
        sh = np.minimum(sh, soft_contact(cx, cy, 0.05))
    sh = np.where(a > 0.98, 1.0, sh)
    return dict(rgb=rgb, a=a, sh=sh, rec=dict(source="card-sized clay (revolve()): black iron dish D10.5 x 3 with a rolled rim, cream candles D7 A 15 / "
                                                     "B 16 (lever); A (0.15, 1.74), B (0.34, 1.68)"))


def ph_vase_v3(below):
    """vase 3 (white plum, M: H 33, W 22.4, mouth 3.3) at the clay point in the card's white (#EFEDE8), with the SAME dry olive branch as
    the default (the R6 default layer's pixels above its mouth); the default's shadow"""
    rgb, a = revolve(POINT[0], POINT[1], 0.45, PROF_VASE3, hex_rgb("#F6F4EF"), amb=0.74,
                     ripple=lambda T, Zr: 0.03 * np.sin(Zr * 380))
    Lv = f32(os.path.join(F7.WR6, "layers/vase.png"))
    mv = F4.vase_measure(Lv[..., 3], Lv[..., :3])
    _, vm, _ = S0.P(POINT[0], POINT[1], 0.45 + 0.33)
    mouth_row = int(round((S0.CY + vm * S0.CH) / S0.GH * SIZE[1]))
    br_rgb, br_a = R5.branch_from(Lv[..., :3], Lv[..., 3], min(mouth_row, mv["mouth_top_y"]) + 2)
    rgb, a = over(rgb, a, br_rgb, br_a)
    sh = f32(os.path.join(F7.WR6, "shadows/vase.png"), "L")
    sh = np.where(a > 0.98, 1.0, sh)
    return dict(rgb=rgb, a=a, sh=sh, rec=dict(source="the card's clay (revolve(): H 33, W 22.4, mouth 3.3, #EFEDE8, faint throwing rings) at the clay "
                                                     f"point {POINT}; the same branch from work-r6/layers/vase.png above row {mouth_row}"))


def ph_curtains_v3(below):
    """the slot's form: the default's stack BEFORE the length cut (work-r6: the same free alpha, inner edge, folds), its folds' light
    (L* smoothed sigma 1.5) as a linen clay: L* -7.5, a* 1.3, b* 9.5 (the card's Linen #D9CDB8 against the default's cream); the default's
    R6 shadow. The sold length is cut in code after the pass (fix_r7.curtains_v3: hem Z 0.22)"""
    L = f32(os.path.join(F7.WR6, "layers/curtains.png"))
    af = f32(os.path.join(F7.WR6, "layers/curtains-free-alpha.png"), "L")
    Lw = lab(L[..., :3])
    Ls = cv2.GaussianBlur(Lw[..., 0], (0, 0), 1.5)
    rgb = rgb_of(np.clip(Ls - 7.5, 0, 100), np.full_like(Ls, 1.3), np.full_like(Ls, 9.5))
    sh = f32(os.path.join(F7.WR6, "shadows/curtains.png"), "L")
    return dict(rgb=rgb.astype(np.float32), a=L[..., 3], a_free=af, sh=sh,
                rec=dict(source="work-r6/layers/curtains.png (the default's uncut form) -> linen clay: L* smoothed sigma 1.5, -7.5, a* 1.3, b* 9.5"))


PH = {("bowl", "v2"): ph_bowl_v2, ("candle-holders", "v2"): ph_holders_v2, ("vase", "v3"): ph_vase_v3,
      ("bowl", "v3"): ph_bowl_v3, ("candle-holders", "v3"): ph_holders_v3, ("curtains", "v3"): ph_curtains_v3}


# ------------------------------------------------------------------------------------------------- the input
def make_input(pass_):
    os.makedirs(W.INP, exist_ok=True)
    below = scene(pass_)
    phd = os.path.join(WR7, f"ph-{pass_}")
    recs, override = {}, {}
    for slot, var in PASSES[pass_]["products"]:
        ph = PH[(slot, var)](below)
        os.makedirs(os.path.join(phd, "layers"), exist_ok=True)
        os.makedirs(os.path.join(phd, "shadows"), exist_ok=True)
        PW.save(os.path.join(phd, "layers", f"{slot}.png"), ph["rgb"], alpha=ph["a"])
        PW.save(os.path.join(phd, "shadows", f"{slot}.png"), np.repeat(ph["sh"][..., None], 3, 2))
        override[slot] = (ph["rgb"], ph["a"], ph.get("a_free"), ph["sh"])
        recs[slot] = dict(variant=var, card=CARDS[(slot, var)][0], sku=CARDS[(slot, var)][2], **ph["rec"])
    slots = [s for s, _ in PASSES[pass_]["products"]]
    keep = [k for k in F7.ACCEPTED if k not in PASSES[pass_]["remove"]]
    U, steps = F7.compose7(items=keep + slots, override=override)
    V = {}
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
    np.savez_compressed(os.path.join(WR7, f"ph-{pass_}.npz"), **{f"vis_{k}": V[k].astype(np.float16) for k in V},
                        **{f"sil_{k}": sil[k].astype(np.float16) for k in sil})
    rep = {}
    for k in V:
        ys, xs = np.nonzero(V[k] > 0.5)
        rep[k] = dict(recs[k], visible_px=int((V[k] > 0.5).sum()), box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
    J = dict(pass_=pass_, below=rel(os.path.join(WR7, f"scene-{pass_}.png")),
             below_is="the R7 stack (fix_r7: the planter at k 0.78, the curtains at 270, the table defaults moved), cushion set B, without "
                      + ", ".join(PASSES[pass_]["remove"]),
             points=dict(bowl=BOWL_XY, holders=HOLDERS, vase=POINT), placeholders=rep,
             note="PHOTOGRAPHIC placeholders (R3 method): the card-sized clay in the room's light at the slots 1.9.4 points, the slot's own form "
                  "where the slot fixes it; visible parts only; a placeholder reaches a layer only through the new render")
    json.dump(J, open(os.path.join(W.INP, f"{pass_}-input.json"), "w"), indent=1, default=float)
    print(p, json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("visible_px", "box_px")} for k, v in rep.items()}, indent=1))


def load_ph(pass_):
    z = np.load(os.path.join(WR7, f"ph-{pass_}.npz"))
    get = lambda pre: {k[len(pre):]: z[k].astype(np.float32) for k in z.files if k.startswith(pre)}  # noqa: E731
    return get("sil_"), get("vis_")


# ------------------------------------------------------------------------------------------------- the result
def shadow_new(k, a, regt, below, surf, others):
    """THE FROZEN RECIPE: extract.shadow_one exactly as every existing layer has it (pass_r5.shadow_new), with this pass's SPEC"""
    saved = X.SPEC.get(k)
    X.SPEC[k] = SPEC[k]
    try:
        sh = X.shadow_one(k, a, regt, below, surf, others)
    finally:
        X.SPEC[k] = saved
    return sh, dict(recipe="extract.shadow_one as is (frozen)")


def cut(k, regt, below, V, zone, front, dE):
    saved = X.SPEC.get(k)
    X.SPEC[k] = SPEC[k]
    try:
        return X.cut_one(k, regt, below, V, zone, front, dE)
    finally:
        X.SPEC[k] = saved


def fetch(pass_, url, pid, tid):
    os.makedirs(os.path.join(WR7, "layers"), exist_ok=True)
    os.makedirs(os.path.join(WR7, "shadows"), exist_ok=True)
    prods = PASSES[pass_]["products"]
    slots = [s for s, _ in prods]
    p = os.path.join(W.RAW, f"{pass_}-r7-seedream.png")
    if not os.path.exists(p):
        p = X.fetch_raw(url, f"{pass_}-r7-seedream.png")
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
    keep = [k for k in F7.ACCEPTED if k not in PASSES[pass_]["remove"]]
    F7.use_r7_sources()
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
        stem = "curtains-v3-render" if nm == "curtains-v3" else nm
        PW.save(os.path.join(WR7, "layers", f"{stem}.png"), regt, alpha=alphas[k])
        if k in stack.BEHIND:
            Image.fromarray((np.clip(free[k], 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(WR7, "layers", f"{stem}-free-alpha.png"))
        PW.save(os.path.join(WR7, "shadows", f"{stem}.png"), np.repeat(sh[..., None], 3, 2))
        a = alphas[k]
        ph = V[k] > 0.5
        ys, xs = np.nonzero(a > 0.5)
        recs[nm] = dict(slot=k, variant=var, card=CARDS[(k, var)][0], sku=CARDS[(k, var)][2], file=stem, alpha_px=int((a > 0.5).sum()),
                        soft_px=int(((a > 0.02) & (a < 0.98)).sum()),
                        box_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None,
                        placeholder_px=int(ph.sum()), placeholder_covered=round(float((ph & (a > 0.5)).sum() / max(1, ph.sum())), 3),
                        outside_placeholder_px=int(((a > 0.5) & ~X.dil(ph, 2)).sum()),
                        shadow_px_below_0_97=int((sh < 0.97).sum()), shadow_min=round(float(sh.min()), 3), shadow_edge=sinfo,
                        model_change_vs_placeholder_dE=dict(median=round(float(np.median(dIn[ph])), 2), p90=round(float(np.percentile(dIn[ph], 90)), 2)))
    far = ~X.dil(Z, 40)
    drift = np.abs(PW.Lstar(reg) - PW.Lstar(below))[far]
    drift_t = np.abs(PW.Lstar(regt) - PW.Lstar(below))[far]
    np.save(os.path.join(WR7, f"{pass_}-regt.npy"), regt.astype(np.float16))
    rec = dict(id=PASSES[pass_]["name"], pass_=pass_, products=[fname(k, v) for k, v in prods], returned_px=returned, raw=rel(p),
               register_to_input=np.round(M, 4).tolist(), tone_gain_median=[round(float(np.median(G[..., c][Z])), 4) for c in range(3)],
               model_drift_outside_zones_L=dict(raw_median=round(float(np.median(drift)), 2), raw_p95=round(float(np.percentile(drift, 95)), 2),
                                                after_tone_match_median=round(float(np.median(drift_t)), 2),
                                                note="the model's redraw outside the products; discarded (the scene below is kept)"),
               cut=recs, placeholder_id=pid, task_id=tid, url=url)
    json.dump(rec, open(os.path.join(WR7, f"{pass_}-fetch.json"), "w"), indent=1, default=float)
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
