#!/usr/bin/env python3
"""
post_r5.py: the 0-token code fixes on the cuts of passes 4' / 5' (render-agent, 2026-11-11). Each raw cut is kept as <name>-cut.png; the
fixed file takes the name grade_cut_r5.py reads (<name>.png). Record: work-r5/post-r5.json.

  frames    framed-art-v2: the model drew the reference's light-oak frames; the scene brief (section 3: every variant keeps the same walnut
            frame) and the PR1 framing (the art is sold unframed; the frame is the room's) want the default's walnut frames. The moulding
            band (the piece outside the print area, pass_r5's measured moulding offsets) takes the default's own frame pixels and alpha
            at the same place (the same frames, so only the prints change when the variant swaps); the prints are the render's
  sconces   accent-sconces-v2: the right block came out 79 px tall against the clay box's 75 (16.8 cm against the card's 16): shrunk x0.95
            about its centre (the left block is within 2 %); a size fix, as extract.scale_fix
  curtains  curtains-v2: the model warmed it (C* 8.9, h 82 against its photo's C 6.5, h 93): the designer's pre-approved fix (section 3,
            'on the variants'): a* and b* only, one hue rotation and one chroma factor, to median h 85-95, C* 5.5-7.5, p95 <= 11, >= the
            plaster beside it + 0.5, L* unchanged; and the armchair post's light line closed as on the default (fix_r5.post_line_fix)
  vase-v2   (5') reported only

  python3 post_r5.py p4|p5
"""
import json
import math
import os
import shutil
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_r5 as F5  # noqa: E402
import grade_cut_r12 as G12  # noqa: E402
import pass_r5 as R  # noqa: E402
import stack  # noqa: E402
from phase2_wm import PW  # noqa: E402

WR5 = R.WR5
REC = os.path.join(WR5, "post-r5.json")


def record(key, val):
    r = json.load(open(REC)) if os.path.exists(REC) else dict(date="2026-11-11", author="render-agent", tokens=0,
                                                              note="0-token code fixes on the pass cuts; the raw cuts are kept as <name>-cut.png")
    r[key] = val
    json.dump(r, open(REC, "w"), indent=1, ensure_ascii=False, default=float)


def keep_cut(nm, shadow=False):
    """the raw cut kept once as <name>-cut.png; returns the path of the raw cut to read"""
    d = os.path.join(WR5, "shadows" if shadow else "layers")
    src, raw = os.path.join(d, f"{nm}.png"), os.path.join(d, f"{nm}-cut.png")
    if not os.path.exists(raw):
        shutil.copyfile(src, raw)
    return raw


# ------------------------------------------------------------------------------------------------- variant-aware composition
def compose_with(variants, items=None, cushion_set="B"):
    """the r5 stack (pass_r5.ACCEPTED, the R5 sources) with some slots read from a variant file: variants = {slot: name}"""
    orig = G12.product

    def prod(k, s=None):
        if k in variants:
            ld, sd = os.path.join(WR5, "layers"), os.path.join(WR5, "shadows")
            nm = variants[k]
            L = stack.f8(os.path.join(ld, f"{nm}.png"))
            a = L[..., 3]
            fp = os.path.join(ld, f"{nm}-free-alpha.png")
            if not os.path.exists(fp):
                fp = os.path.join(ld, f"{nm[:-4] if nm.endswith('-cut') else nm}-free-alpha.png")
            if k in stack.BEHIND and os.path.exists(fp):
                a = stack.f8(fp, "L")
            sp = os.path.join(sd, f"{nm}.png")
            if not os.path.exists(sp):
                sp = os.path.join(sd, f"{nm[:-4] if nm.endswith('-cut') else nm}.png")
            return L[..., :3], a, stack.f8(sp, "L")
        return orig(k, s)
    G12.product = prod
    stack_prod = stack.product
    stack.product = prod
    try:
        return stack.compose(set(items or R.ACCEPTED) | {"cushions"}, R.parts(), cushion_set=cushion_set, keep_steps=True)
    finally:
        G12.product = orig
        stack.product = stack_prod


# ------------------------------------------------------------------------------------------------- the fixes
def frames():
    nm = "framed-art-v2"
    raw = keep_cut(nm)
    L = R.f32(raw)
    D = R.f32(os.path.join(R.W.WORK, "layers/framed-art.png"))
    ph = R.f32(os.path.join(WR5, "ph-p4/layers/framed-art.png"))
    inner = (np.abs(ph[..., :3] - D[..., :3]).max(2) > 1e-6) & (D[..., 3] > 0.5)     # the placeholder's blanked print areas
    band = (D[..., 3] > 0) & ~inner
    # the print's 2 px ring next to the moulding: the render's light-oak frame was wider than the walnut band there; the ring takes the
    # print's own colour from just inside it (a normalised blur over the print core, sigma 1.5)
    core = R.X.ero(inner, 2)
    seam = inner & ~core
    nb, den = F5.X_nblur(L[..., :3], core.astype(np.float32), 1.5)
    prt = np.where((seam & (den > 1e-3))[..., None], nb, L[..., :3])
    rgb = np.where(band[..., None], D[..., :3], prt)
    a = np.where(band, D[..., 3], L[..., 3])
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), rgb, alpha=a)
    lab = R.lab(L[..., :3])
    ring = band & (D[..., 3] > 0.98)
    record("framed-art-v2", dict(fix="the default's walnut frames in the moulding band (scene brief section 3; PR1)",
                                 band_px=int(band.sum()), print_px=int(inner.sum()), seam_px_refilled_from_the_print=int(seam.sum()),
                                 render_frame_colour_lab=[round(float(np.median(lab[..., i][ring])), 1) for i in range(3)],
                                 default_frame_colour_lab=[round(float(np.median(R.lab(D[..., :3])[..., i][ring])), 1) for i in range(3)]))
    print("frames", int(band.sum()), int(inner.sum()), "seam", int(seam.sum()))


def sconces(nm="accent-sconces-v2", ph_pass="p4"):
    raw, raws = keep_cut(nm), keep_cut(nm, shadow=True)
    L = R.f32(raw)
    sh = R.f32(raws, "L")
    a = L[..., 3]
    clay = R.f32(os.path.join(WR5, f"ph-{ph_pass}/layers/accent-sconces.png"))[..., 3]
    out_rgb, out_a, out_sh = L[..., :3].copy(), a.copy(), sh.copy()
    rec = {}
    for side, (x0, x1) in (("left", (1380, 1480)), ("right", (2220, 2340))):
        win = np.zeros(a.shape, bool)
        win[:, x0:x1] = True
        m, c = (a > 0.5) & win, (clay > 0.5) & win
        ys, xs = np.nonzero(m)
        cy_, cx_ = np.nonzero(c)
        h_cut, h_clay = ys.max() + 1 - ys.min(), cy_.max() + 1 - cy_.min()
        f = h_clay / h_cut
        rec[side] = dict(cut_box=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                         clay_box=[int(cx_.min()), int(cy_.min()), int(cx_.max()) + 1, int(cy_.max()) + 1], height_ratio=round(float(1 / f), 4))
        f = min(f, (cx_.max() + 1 - cx_.min()) / (xs.max() + 1 - xs.min())) if ph_pass == "p5" else f   # v3: the larger miss of the two axes
        if f > 0.97:
            rec[side]["scaled"] = False
            continue
        ax, ay = (xs.min() + xs.max() + 1) / 2.0, (ys.min() + ys.max() + 1) / 2.0
        M = np.float32([[f, 0, ax * (1 - f)], [0, f, ay * (1 - f)]])
        roi = R.X.dil(m, 40) & win
        ai = np.where(R.X.dil(m, 4) & win, a, 0).astype(np.float32)
        wa = cv2.warpAffine(ai, M, R.SIZE, flags=cv2.INTER_AREA)
        wp = cv2.warpAffine(L[..., :3] * ai[..., None], M, R.SIZE, flags=cv2.INTER_AREA)
        ws = cv2.warpAffine(np.where(roi, 1 - sh, 0).astype(np.float32), M, R.SIZE, flags=cv2.INTER_AREA)
        out_a = np.where(roi, wa, out_a)
        out_rgb = np.where((roi & (wa > 1e-4))[..., None], wp / np.maximum(wa, 1e-4)[..., None], out_rgb)
        out_sh = np.where(roi, np.clip(1 - ws, 0, 1), out_sh)
        out_sh = np.where(out_a >= 0.999, 1.0, out_sh)
        rec[side].update(scaled=True, factor=round(float(f), 4), anchor_px=[round(float(ax), 1), round(float(ay), 1)])
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), np.clip(out_rgb, 0, 1), alpha=np.clip(out_a, 0, 1))
    PW.save(os.path.join(WR5, "shadows", f"{nm}.png"), np.repeat(np.clip(out_sh, 0, 1)[..., None], 3, 2))
    record(nm, dict(fix="size: a piece over 3 % larger than its clay box shrunk about its centre (extract.scale_fix's way)" +
                    ("; v3: the card has no dimensions, the clay box is the SKU photo's proportions inside the slot envelope" if ph_pass == "p5" else ""),
                    pieces=rec))
    print("sconces", json.dumps(rec))


def curtains():
    nm = "curtains-v2"
    raw = keep_cut(nm)
    L = R.f32(raw)
    rgb_w, a_in = L[..., :3], L[..., 3]
    a_free = R.f32(os.path.join(WR5, "layers", f"{nm}-free-alpha.png"), "L")
    P = R.parts()
    fa, F = P["fa"], P["F"]
    U, steps = compose_with({"curtains": f"{nm}-cut"})
    A_all = np.zeros(fa.shape, np.float32)
    for st in steps:
        A_all = np.maximum(A_all, st["a_eff"] if st["k"] != "cushions" else st["a"])
    Gr0 = stack.Grade()
    G0 = Gr0(U, A_all)
    reg = (a_free > 0) | R.X.dil((fa > 0.02) & (a_free > 0.02), 2)
    Gr = lambda U_: np.where(reg[..., None], Gr0(U_, A_all), G0)  # noqa: E731
    m = cv2.erode((a_in >= 0.999).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m[:100], m[1400:] = False, False
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    ring = (d >= 15) & (d <= 40)
    vis = (a_free * (1 - fa))[..., None]
    before = F5.curtain_measure(G0, m, ring)
    want_h, want_C = 90.0, 6.5
    dh, k = want_h - before["h"], want_C / before["C"]
    hist = []
    for it in range(8):
        rgb_n = F5.recolour_ab(rgb_w, dh, k)
        mm = F5.curtain_measure(Gr(U + (rgb_n - rgb_w) * vis), m, ring)
        hist.append(dict(it=it, dh=round(dh, 3), k=round(k, 4), h=mm["h"], C=mm["C"], C_p95=mm["C_px_p95"], L=mm["L"]))
        if abs(want_h - mm["h"]) < 0.3 and abs(want_C - mm["C"]) < 0.05:
            break
        dh += want_h - mm["h"]
        k *= want_C / max(mm["C"], 1e-3)
    # the p95 bound: one factor for every pixel, so where the slub's spread is wide the median goes lower (still >= 5.5 and >= the
    # plaster + 0.5)
    for it in range(6):
        if hist[-1]["C_p95"] <= 10.9:
            break
        k *= 10.8 / hist[-1]["C_p95"]
        mm = F5.curtain_measure(Gr(U + (F5.recolour_ab(rgb_w, dh, k) - rgb_w) * vis), m, ring)
        hist.append(dict(it=f"p95-{it}", dh=round(dh, 3), k=round(k, 4), h=mm["h"], C=mm["C"], C_p95=mm["C_px_p95"], L=mm["L"]))
    rgb_n = F5.recolour_ab(rgb_w, dh, k)
    rgb_f, fringe = F5.post_line_fix(rgb_n, a_free, fa, F)
    after = F5.curtain_measure(Gr(U + (rgb_f - rgb_w) * vis), m, ring)
    tg = {"L* median within +-0.5": after["L"] - before["L"], "high-pass within +-5 %": after["highpass_std"] / before["highpass_std"] - 1,
          "median h 85-95": after["h"], "median C* 5.5-7.5": after["C"], "p95 C* <= 11": after["C_px_p95"],
          ">= plaster + 0.5": after["C"] - after["plaster_ring"]["C"]}
    ok = {"L* median within +-0.5": abs(tg["L* median within +-0.5"]) <= 0.5, "high-pass within +-5 %": abs(tg["high-pass within +-5 %"]) <= 0.05,
          "median h 85-95": 85 <= after["h"] <= 95, "median C* 5.5-7.5": 5.5 <= after["C"] <= 7.5, "p95 C* <= 11": after["C_px_p95"] <= 11,
          ">= plaster + 0.5": tg[">= plaster + 0.5"] >= 0.5}
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), rgb_f, alpha=a_in)
    record("curtains-v2", dict(fix="the designer's pre-approved colour fix (section 3, 'on the variants') + the post line, as on the default",
                               photo=dict(files="curtains2/img4.jpg, img1.jpg (scratchpad)", L=87.2, C=6.48, h=92.8),
                               dh_deg=round(dh, 3), k=round(k, 4), iterations=hist, before=before, after=after,
                               targets={kk: dict(value=round(float(v), 3), pass_=bool(ok[kk])) for kk, v in tg.items()}, all_met=all(ok.values()),
                               post_line_fringe_px=int(fringe.sum())))
    print("curtains", json.dumps(dict(before={x: before[x] for x in ("L", "C", "h", "C_px_p95")}, after={x: after[x] for x in ("L", "C", "h", "C_px_p95", "plaster_ring")},
                                      ok=ok, k=k, dh=dh), default=float))


def pendant():
    """pendant-v2: a pleated white lantern on the white wall: GrabCut kept ~78 % of it. The render followed the placeholder's outline within
    ~2 px (checked on the overlay), so the lantern is the placeholder's silhouette snapped to the render's edges by a guided filter (r 4;
    1 inside 4 px of it, 0 beyond 6 px; as R3a's pot_snap); the cord and the canopy keep the cut (canopy_cut()). No shadow layer (slot)"""
    nm = "pendant-v2"
    raw = keep_cut(nm)
    L = R.f32(raw)
    a_cut = L[..., 3]
    ph = R.f32(os.path.join(WR5, "ph-p5/layers/pendant.png"))[..., 3]
    regt = np.load(os.path.join(WR5, "p5-regt.npy")).astype(np.float32)
    lr, la = R.revolve(0.20, 1.72, 1.90, R.PROF_PUMPKIN, R.hex_rgb("#F1ECE3"), nz=200, nt=360)
    top = int(np.nonzero((la > 0.5).any(1))[0].min())
    lant = np.zeros_like(ph)
    lant[top:] = ph[top:]
    m = lant > 0.5
    g = cv2.cvtColor((np.clip(regt, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    al = np.clip(PW.guided(g, lant.astype(np.float32), 4, 1e-3), 0, 1)
    al = np.where(R.X.ero(m, 4), 1.0, np.where(R.X.dil(m, 6), al, 0.0)).astype(np.float32)
    a_new = a_cut.copy()
    a_new[top:] = np.maximum(a_cut[top:] * R.X.dil(m, 6)[top:], al[top:])
    # the model added a light-wood sleeve on the cord above the lantern (not in the card): the cord's own profile (its colour and alpha
    # across its column, the median of the rows where it hangs alone under the canopy) replaces it down to the lantern's top
    rgb = regt.copy()
    cx_ = float(np.median([(np.nonzero(a_new[y] > 0.5)[0].min() + np.nonzero(a_new[y] > 0.5)[0].max()) / 2.0 for y in range(62, 91)]))
    c0, c1 = int(np.floor(cx_ - 6)), int(np.ceil(cx_ + 7))
    labc = R.lab(regt)
    band = np.zeros(a_new.shape, bool)
    band[90:top + 4, c0:c1] = True
    sleeve = band & (a_new > 0.3) & (labc[..., 2] > 12)
    if sleeve.any():
        y0s, y1s = int(np.nonzero(sleeve.any(1))[0].min()) - 2, top + 3
        prof_a = np.median(a_new[62:91, c0:c1], axis=0)
        prof_rgb = np.median(regt[62:91, c0:c1], axis=0)
        a_new[y0s:y1s, c0:c1] = np.where(lant[y0s:y1s, c0:c1] > 0.5, a_new[y0s:y1s, c0:c1], prof_a[None, :])
        rgb[y0s:y1s, c0:c1] = np.where((lant[y0s:y1s, c0:c1] > 0.5)[..., None], regt[y0s:y1s, c0:c1], prof_rgb[None, :, :])
        sleeve_rec = dict(rows=[y0s, y1s], cols=[c0, c1], px=int(sleeve.sum()))
    else:
        sleeve_rec = None
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), rgb, alpha=a_new)
    covered = float(((a_new > 0.5) & m).sum() / max(1, m.sum()))
    record(nm, dict(fix="the lantern's alpha snapped from the placeholder's silhouette (GrabCut lost ~22 % of the white lantern on the white wall)",
                    lantern_top_row=top, placeholder_covered_before=round(float(((a_cut > 0.5) & m).sum() / max(1, m.sum())), 3),
                    placeholder_covered_after=round(covered, 3), alpha_px=int((a_new > 0.5).sum()),
                    cord_sleeve_replaced_by_the_cord=sleeve_rec))
    print("pendant", top, round(covered, 3))


def planter_size():
    """planter (5'): the model drew the pot ~12 % taller (rim top row ~1030 against the clay's 1044) and ~9 % wider (belly 158 px against
    145.3) than the card's clay (R3's clay_boxes: belly 42, height 35.5). A size miss: the pot is scaled to the clay box about ITS OWN base
    (its bottom row and axis, not moved), x and y separately; the olive tree (a filler) is not scaled, only carried down with the rim (its
    trunk stays in the soil); the floor shadow scaled about the same anchor at the x factor (it lies on the floor)"""
    import reserve_r3 as R3
    nm = "planter"
    raw, raws = keep_cut(nm), keep_cut(nm, shadow=True)
    L = R.f32(raw)
    rgb, a = L[..., :3], L[..., 3]
    sh = R.f32(raws, "L")
    clay = R3.clay_boxes()["pot"]
    widths = {y: int((a[y, 930:1130] > 0.5).sum()) for y in range(990, 1200)}
    rim = next(y for y in range(990, 1200) if widths[y] >= 60)               # the rim: where the row widens from the trunk to the pot
    bottom = max(y for y in range(990, 1200) if widths[y] > 0)
    belly = max(widths.values())
    rows = [y for y in range(rim, bottom) if widths[y] >= belly - 1]
    yb = int(np.median(rows))
    xs = np.nonzero(a[yb, 930:1130] > 0.5)[0] + 930
    axis = (xs.min() + xs.max() + 1) / 2.0
    sx = (clay["right"] - clay["left"]) / belly
    sy = (clay["bottom"] - clay["top"]) / (bottom + 1 - rim)
    ax, ay = axis, bottom + 1.0
    M = np.float32([[sx, 0, ax * (1 - sx)], [0, sy, ay * (1 - sy)]])
    Ms = np.float32([[sx, 0, ax * (1 - sx)], [0, sx, ay * (1 - sx)]])
    cut_row = rim - 4
    pot_a = a.copy()
    pot_a[:cut_row] = 0
    tree_a = a.copy()
    tree_a[cut_row:] = 0
    dy = int(round((ay - sy * (ay - cut_row)) - cut_row))
    wa = cv2.warpAffine(pot_a, M, R.SIZE, flags=cv2.INTER_AREA)
    wp = cv2.warpAffine(rgb * pot_a[..., None], M, R.SIZE, flags=cv2.INTER_AREA)
    Mt = np.float32([[1, 0, 0], [0, 1, dy]])
    ta = cv2.warpAffine(tree_a, Mt, R.SIZE, flags=cv2.INTER_NEAREST)
    tp = cv2.warpAffine(rgb * tree_a[..., None], Mt, R.SIZE, flags=cv2.INTER_NEAREST)
    a2 = np.clip(wa + ta * (1 - wa), 0, 1)
    pm = wp + tp * (1 - wa)[..., None]
    rgb2 = np.where((a2 > 1e-4)[..., None], pm / np.maximum(a2, 1e-4)[..., None], rgb)
    sh2 = 1 - cv2.warpAffine(1 - sh, Ms, R.SIZE, flags=cv2.INTER_AREA)
    sh2 = np.where(a2 >= 0.999, 1.0, sh2)
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), np.clip(rgb2, 0, 1), alpha=a2)
    PW.save(os.path.join(WR5, "shadows", f"{nm}.png"), np.repeat(np.clip(sh2, 0, 1)[..., None], 3, 2))
    w2 = {y: int((a2[y, 930:1130] > 0.5).sum()) for y in range(990, 1200)}
    rim2 = next(y for y in range(990, 1200) if w2[y] >= 60)
    bot2 = max(y for y in range(990, 1200) if w2[y] > 0)
    rec = dict(fix="size: the pot scaled to the card's clay box about its own base (not moved); the tree carried down with the rim, not scaled",
               before=dict(rim_row=rim, bottom_row=bottom, belly_px=belly, belly_row=yb, axis_x=round(axis, 1),
                           cm=dict(belly=round(42 * belly / (clay["right"] - clay["left"]), 1), height=round(35.5 * (bottom + 1 - rim) / (clay["bottom"] - clay["top"]), 1))),
               clay_box=clay, scale=[round(float(sx), 4), round(float(sy), 4)], anchor_px=[round(ax, 1), ay], tree_shift_px=dy,
               after=dict(rim_row=rim2, bottom_row=bot2, belly_px=max(w2.values()),
                          cm=dict(belly=round(42 * max(w2.values()) / (clay["right"] - clay["left"]), 1),
                                  height=round(35.5 * (bot2 + 1 - rim2) / (clay["bottom"] - clay["top"]), 1))))
    record(nm, rec)
    print("planter", json.dumps(rec, default=float))


def _graded_region(variants, reg):
    U, steps = compose_with(variants)
    A_all = np.zeros(R.SIZE[::-1], np.float32)
    for st in steps:
        A_all = np.maximum(A_all, st["a_eff"] if st["k"] != "cushions" else st["a"])
    Gr0 = stack.Grade()
    G0 = Gr0(U, A_all)
    return U, (lambda U_: np.where(reg[..., None], Gr0(U_, A_all), G0)), G0


def vase_colour():
    """the default vase (4'): the model drew it cream (lit half C* 13.7, h 80, against the surfaces beside it C 4.2, h 85), against the
    designer's targets (section 2: off-white like the card #EEECE8, C* median 4-7 on the lit half, hue within 10 deg of the surface beside,
    not above C 7): a*b* only, one hue rotation and one chroma factor for every pixel, L* unchanged (fix_r5's method); the branch (a filler)
    keeps its colour"""
    import fix_r4 as F4
    nm = "vase"
    raw = keep_cut(nm)
    L = R.f32(raw)
    rgb_w, a = L[..., :3], L[..., 3]
    mv = F4.vase_measure(a, rgb_w)
    body = (a > 0).copy()
    body[:935] = False                                      # the body from the rim down (the rim row ~935-937); the branch above is a filler
    reg = (a > 0) | R.X.dil(a > 0, 2)
    U, Gr, G0 = _graded_region({"vase": f"{nm}-cut"}, reg)
    m = cv2.erode((a >= 0.999).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    m &= body
    ys, xs = np.nonzero(m)
    lit = m & (np.arange(m.shape[1])[None, :] < (xs.min() + xs.max()) / 2)
    LB = R.lab(G0.astype(np.float32) / 255)
    d = cv2.distanceTransform((~(a > 0)).astype(np.uint8), cv2.DIST_L2, 5)
    beside = (d >= 15) & (d <= 40) & (LB[..., 0] <= 95) & (LB[..., 0] >= 50)

    def meas(G):
        LL = R.lab(G.astype(np.float32) / 255)
        aa, bb = float(np.median(LL[..., 1][lit])), float(np.median(LL[..., 2][lit]))
        return dict(L=round(float(np.median(LL[..., 0][lit])), 2), C=round(math.hypot(aa, bb), 2), h=round(math.degrees(math.atan2(bb, aa)) % 360, 2))
    ab, bb_ = float(np.median(LB[..., 1][beside])), float(np.median(LB[..., 2][beside]))
    h_b = math.degrees(math.atan2(bb_, ab)) % 360
    before = meas(G0)
    want_C, want_h = 5.5, h_b
    dh, k = want_h - before["h"], want_C / before["C"]
    hist = []
    sel = body[..., None]
    for it in range(8):
        rgb_n = np.where(sel, F5.recolour_ab(rgb_w, dh, k), rgb_w)
        mm = meas(Gr(U + (rgb_n - rgb_w) * a[..., None]))
        hist.append(dict(it=it, dh=round(dh, 2), k=round(k, 4), **mm))
        if abs(mm["C"] - want_C) < 0.1 and abs(mm["h"] - want_h) < 0.5:
            break
        dh += want_h - mm["h"]
        k *= want_C / max(mm["C"], 1e-3)
    rgb_n = np.where(sel, F5.recolour_ab(rgb_w, dh, k), rgb_w)
    after = meas(Gr(U + (rgb_n - rgb_w) * a[..., None]))
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), rgb_n, alpha=a)
    tg = {"C* median 4-7 on the lit half": 4 <= after["C"] <= 7, "hue within 10 deg of the surface beside": abs((after["h"] - h_b + 180) % 360 - 180) <= 10,
          "not above C 7": after["C"] <= 7, "L* unchanged (+-0.5)": abs(after["L"] - before["L"]) <= 0.5}
    record(nm, dict(fix=vase_colour.__doc__.replace("\n", " "), beside=dict(C=round(math.hypot(ab, bb_), 2), h=round(h_b, 2)), before=before, after=after,
                    dh_deg=round(dh, 3), k=round(k, 4), iterations=hist, targets=tg, all_met=all(tg.values()), card="#EEECE8"))
    print("vase", before, after, tg)


def art_blacks():
    """framed-art-v2: the prints' black reads L* 11 in the room; the scene brief (section 3) measures it as espresso-black, L* 12-22. The
    print's dark tones (L* < 35 in the layer) are lifted by a smooth toe (full at L* 5, none at 35), L* only, to a graded median of 15"""
    nm = "framed-art-v2"
    L = R.f32(os.path.join(WR5, "layers", f"{nm}.png"))      # the frame-fixed file (frames() ran first)
    rgb_w, a = L[..., :3], L[..., 3]
    Lw = R.lab(rgb_w)
    D = R.f32(os.path.join(R.W.WORK, "layers/framed-art.png"))
    ph = R.f32(os.path.join(WR5, "ph-p4/layers/framed-art.png"))
    prints = (np.abs(ph[..., :3] - D[..., :3]).max(2) > 1e-6) & (D[..., 3] > 0.5)
    reg = a > 0
    U, Gr, G0 = _graded_region({"framed-art": nm}, reg)
    dark = prints & (a >= 0.999)

    def meas(G):
        LL = R.lab(G.astype(np.float32) / 255)[..., 0]
        m = dark & (LL < 35)
        return round(float(np.median(LL[m])), 2), int(m.sum())
    before = meas(G0)
    w = np.clip((35.0 - Lw[..., 0]) / 30.0, 0, 1)
    lift = 4.0
    hist = []
    for it in range(8):
        Ln = Lw[..., 0] + lift * w
        rgb_n = np.where(prints[..., None], R.rgb_of(Ln, Lw[..., 1], Lw[..., 2]), rgb_w)
        mm = meas(Gr(U + (rgb_n - rgb_w) * a[..., None]))
        hist.append(dict(it=it, lift=round(lift, 3), black_L=mm[0]))
        if abs(mm[0] - 15.0) < 0.2:
            break
        lift += (15.0 - mm[0]) * 1.2
    PW.save(os.path.join(WR5, "layers", f"{nm}.png"), rgb_n, alpha=a)
    rec = json.load(open(REC)).get(nm, {})
    rec["blacks"] = dict(fix=art_blacks.__doc__.replace("\n", " "), before_black_L=before, after_black_L=mm, lift_at_L5=round(lift, 3), iterations=hist)
    record(nm, rec)
    print("art blacks", before, mm, lift)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "p4":
        frames()
        sconces()
        curtains()
    elif what == "curtains":
        curtains()
    elif what == "frames":
        frames()
    elif what == "colour":
        vase_colour()
        frames()
        art_blacks()
    elif what == "p5":
        pendant()
        planter_size()
        sconces("accent-sconces-v3", "p5")
