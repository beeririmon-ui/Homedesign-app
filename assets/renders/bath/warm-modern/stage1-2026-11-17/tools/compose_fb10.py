#!/usr/bin/env python3
"""
compose_fb10.py: the FB10 passes on B2 (proposal 12.6, HOUSE2B) cut into layers, render-agent 2026-11-18. 0 tokens.
Runs after compose_defaults.py, --recolour and post_b2.py (the QA-passed defaults); writes only new layers and moves two:
  pass A (raw/fb10-a-r1): the rope basket and the waffle stack on the open shelf, the travertine tray under the soap dispenser
         and the cup; the dispenser and the cup (layers and shadows) rise onto the tray's well as the render drew it
  pass T3 (raw/fb10-t3-r1): the khaki waffle tea towel, a third hand-towel variant with its own alpha and shadow
Each render is locked (lock_b2.py) and tone-matched (gain field) to its own input's base (the defaults with the WM-G1 curve
inverted); each product is cut with GrabCut seeded from its placeholder where the render changed; its shadow is the render's
darkening round it (contact rim + band, tapered); everything is graded with plate-grade.json's curve (grade_plate.curve_apply)
and the composites are recomposed from the files (RND2: outside every alpha, shadow and light, plate.png byte for byte).

  python3 compose_fb10.py
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
import grade_plate as G  # noqa: E402
import prep_fb10 as P  # noqa: E402

NEW = {
    "bath-towels": dict(pid="bath-towels-cj-waffle-cotton-milky-white-70x140-brown", z=36, box="towels", band=24, rim=8,
                        card="data/products/bath/bath-towels/bath-towels-cj-waffle-cotton-milky-white-70x140.json", sku="CJYD178122205EV"),
    "storage-basket": dict(pid="storage-basket-cj-two-tone-cotton-rope-basket-38x25x23-tan-white", z=38, box="basket", band=28, rim=10,
                           card="data/products/bath/storage-basket/storage-basket-cj-two-tone-cotton-rope-basket-38x25x23.json", sku="CJYD180710801AZ"),
    "vanity-tray": dict(pid="pool-cj-travertine-organic-tray-24", z=44, box="tray", band=10, rim=5,
                        card="data/products/pool/tray/pool-cj-travertine-organic-tray-24.json", sku="CJYD238979001AZ"),
}
T3 = dict(slot="hand-towel", pid="tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki", sku="CJYD223761707GT",
          card="data/products/dining/tea-towel/tea-towel-cj-waffle-cotton-beige-45x65-pair.json", band=40, rim=12)
SCR = C.SCR
KHAKI_LCH = (42.8, 17.2, 70.2)     # CJYD223761707GT's photo by QA's photo method (L*, C*, h)
KHAKI_SHEET = (44.0, 16.0, 70.0)   # the designer's sheet (12.6 a)
BAND_LAB = (57.3, 9.1, 19.4)       # the basket's tan band, CJYD180710801AZ's photo by QA's photo method (L*, a*, b*)
TOWELS_LCH = (72.0, 5.0, 47.0)     # Brown CJYD178122205EV, the designer's photo reading (12.6 a): to the photo, not the card's HEX


def files(man):
    return {l["slot"]: (np.asarray(Image.open(os.path.join(ST, l["layer"]))), np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
            for l in man["layers"]}


def stack(man, plate, F, skip=(), swap=None, light=True):
    out = plate.astype(np.float64) / 255
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        if l["slot"] in skip:
            continue
        out = C.compose_one(out, *(swap or {}).get(l["slot"], F[l["slot"]]))
    if light:
        out = C.light_one(out, np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB")))
    return out


def locked(path, base, keep):
    r, wr = C.lock_and_warp(path, base.shape[:2])
    g = C.gain_field(r, base, keep)
    return C.srgb(C.lin(r) * g), dict(warp=wr, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])])


def cut(src, base, ph, zone, hard, prior=None):
    d = np.linalg.norm(C.lab_of(src) - C.lab_of(base), axis=-1)
    sure = C.ero(ph, 4) & (d > 9)
    if prior is not None:
        sure |= prior & zone
    fg = C.gc_cut(src, sure, C.dil(ph, 3), zone, hard)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
    if n > 2:
        fg = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return fg


def shadow(src, base, fg, band, rim, block):
    sp = dict(band=band, rim=rim)
    return C.shadow_of(src, base, fg, sp, np.zeros_like(fg), block)


def graded_shadow(s, below_u, cv):
    sg = np.ones(s.shape)
    m = s < 1
    if m.any():
        b = below_u[m]
        sg[m] = np.clip(cv(b * s[m][:, None]).mean(1) / np.maximum(cv(b).mean(1), 1e-4), 0, 1)
    return sg


def write_layer(slot, pid, a, rgb_g, s_g):
    a8 = C.q(a)
    rgba = np.dstack([C.q(rgb_g), a8])
    rgba[..., :3][a8 == 0] = 0
    lp, sh = os.path.join("layers", slot, pid + ".png"), os.path.join("shadows", slot, pid + ".png")
    os.makedirs(os.path.join(ST, "layers", slot), exist_ok=True)
    os.makedirs(os.path.join(ST, "shadows", slot), exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(os.path.join(ST, lp))
    Image.fromarray(C.q(s_g)).save(os.path.join(ST, sh))
    return lp, sh, rgba, C.q(s_g)


def main():
    man_p = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(man_p))
    if man.get("fb10"):
        sys.exit("fb10 already applied: re-run the chain (compose_defaults, --recolour, post_b2) first")
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    cv = lambda x: G.curve_apply(x, curve)[0]  # noqa: E731
    plate = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    H, W = plate.shape[:2]
    F = files(man)
    rec = {}
    # ---------- pass A ----------
    base_a = P.inv_curve(stack(man, plate, F), curve)
    allfg = np.zeros((H, W), bool)
    for k, (rgba, _) in F.items():
        allfg |= rgba[..., 3] > 0
    ph = {}
    dummy = base_a.copy()
    ids = np.asarray(Image.open(C.CLAY + "B2-plate-id.png"))
    # the same occluders as the input (prep_fb10): the plate's drawer rail edge
    Y = C.blur(C.luma(base_a), 1.0)
    above = np.zeros((H, W), bool)
    above_t = np.zeros((H, W), bool)      # the towels' top face reaches up under the rail: only the rail's own edge occludes it
    for x in range(1340, 2180):
        c = np.nonzero(ids[1000:1450, x] == 21)[0]
        if not len(c):
            continue
        e0 = 1000 + c.max()
        prof = Y[e0 - 5:e0 + 60, x]
        cand = [i for i in range(len(prof) - 14) if prof[i] - prof[i + 4] > 0.06 and prof[i + 4:i + 14].mean() < 0.22]
        if cand:
            above[:e0 - 5 + max(cand) + 2 + 2, x] = True
            above_t[:e0 - 5 + min(cand) + 2 + 2, x] = True
    onvan = (F["soap-dispenser"][0][..., 3] > 0) | (F["toothbrush-cup"][0][..., 3] > 0) | (F["vanity-vase"][0][..., 3] > 0)
    col = lambda idx, b: np.array([0.5, 0.5, 0.5])  # noqa: E731
    ph["towels"] = P.paint(dummy, P.BOXES["towels"], col, keep_off=above)
    ph["basket"] = P.paint(dummy, P.BOXES["basket"], col, keep_off=above)
    ph["tray"] = P.paint(dummy, P.BOXES["tray"], col, keep_off=onvan)
    zones = {k: C.dil(ph[NEW[k]["box"]], 30 if k != "vanity-tray" else 14) for k in NEW}
    zones["bath-towels"] &= ~above
    zones["storage-basket"] &= ~above
    keep = ~(C.dil(zones["bath-towels"] | zones["storage-basket"] | zones["vanity-tray"], 40))
    src_a, rec["a_render"] = locked(os.path.join(ST, "raw", "fb10-a-r1.png"), base_a, keep)
    fg = {}
    # the tray first needs the dispenser and the cup where they now stand (raised by the tray's thickness)
    # the tray is a dish (1.8 cm at its rim, a shallow well inside): the render stands the dispenser and the cup in the well,
    # their bases at rows 913-914 and 916 where the defaults have them at 920 and 925, so they rise by 7 and 9 px (about
    # 0.9 and 1.2 cm; the rim's full 1.8 cm is 14 px and would leave them standing in the air over the drawn well)
    rim_px = int(round(P.px(6.06, 12.62, 0.88)[1] - P.px(6.06, 12.62, 0.898)[1]))
    RISE = {"soap-dispenser": 7, "toothbrush-cup": 9}
    lay = {l["slot"]: l for l in man["layers"]}
    raised = np.zeros((H, W), bool)
    for k in ("soap-dispenser", "toothbrush-cup"):
        a_ = F[k][0][..., 3] > 0
        raised[:-RISE[k]] |= a_[RISE[k]:]
    for k in NEW:
        if k == "vanity-tray":
            # the tray as the render drew it: an oval slab (top ellipse swept down by its front face), read off the render
            # (left and right ends x 1872 / 2087, top surface y 897-927, front face to 937), refined by GrabCut on its colour
            yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float64)
            def oval(cx, cy, a, b, t):
                m = np.zeros((H, W), bool)
                for dy in range(0, t + 1):
                    m |= ((xx_ - cx) / a) ** 2 + ((yy_ - cy - dy) / b) ** 2 <= 1
                return m
            guess = oval(1979.5, 912, 107.5, 15, 10)
            zone_t = C.dil(guess, 10)
            hard_t = ~zone_t | C.dil(F["vanity-vase"][0][..., 3] > 0, 1)
            fg[k] = C.gc_cut(src_a, C.ero(guess, 5) & ~C.dil(raised, 3), C.dil(guess, 3), zone_t, hard_t)
            # the cut stops a few rows short of the raised dispenser's and cup's bases (their dark contact): the tray's top is
            # filled up to 2 px under each base, column by column, so no vanity top shows between a product and the tray
            filled = 0
            for x in np.nonzero(raised.any(0) & fg[k].any(0))[0]:
                yb_ = int(np.nonzero(raised[:, x])[0].max())
                yt_ = int(np.nonzero(fg[k][:, x])[0].min())
                if yt_ > yb_ - 2:
                    add = np.zeros(H, bool)
                    add[yb_ - 2:yt_] = True
                    add &= C.dil(guess, 2)[:, x]
                    filled += int((add & ~fg[k][:, x]).sum())
                    fg[k][:, x] |= add
            rec["tray_fill_under_bases_px"] = filled
            continue
        hard = allfg & ~C.dil(ph[NEW[k]["box"]], 2)
        for o in NEW:
            if o != k:
                hard |= C.ero(ph[NEW[o]["box"]], 2)
        fg[k] = cut(src_a, base_a, ph[NEW[k]["box"]], zones[k], hard)
        if k == "bath-towels":
            # the model drew the stack bigger than the box (328 x 208 px against 293 x 163: puffy folds, a deeper top), so the
            # zone cut its top face and the ends of its folds off; the whole stack is taken (everything lighter than the shelf's
            # black back, L* over 7.5, off the lit walnut floor, joined to the cut) and refitted below, as the lamps and the vase
            labt = G.to_lab(src_a[1240:1500, 1370:1745])
            Ct = np.hypot(labt[..., 1], labt[..., 2])
            cand = np.zeros((H, W), bool)
            cand[1240:1500, 1370:1745] = (labt[..., 0] > 7.5) & ~((Ct > 18) & (labt[..., 0] > 22))
            zt_ = np.zeros((H, W), bool)
            zt_[1250:1490, 1380:1736] = True
            cand &= zt_
            cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
            n_, lab_ = cv2.connectedComponents(cand.astype(np.uint8), connectivity=8)
            full = np.isin(lab_, list(set(np.unique(lab_[C.ero(fg[k], 4) & cand])) - {0}))
            full = cv2.morphologyEx(full.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(4)).astype(bool)
            inv_ = (~full).astype(np.uint8)
            n2_, l2_, st2_, _ = cv2.connectedComponentsWithStats(inv_, connectivity=4)
            full |= np.isin(l2_, [i for i in range(1, n2_) if st2_[i, cv2.CC_STAT_AREA] < 600])
            fg[k] = full
            ys_, xs_ = np.nonzero(full)
            bx = [float(v) for v in np.array([P.px(x_, y_, z_)[:2] for x_ in P.BOXES["towels"][0:2] for y_ in P.BOXES["towels"][2:4]
                                               for z_ in P.BOXES["towels"][4:6]]).T.reshape(2, -1).min(1)] + \
                 [float(v) for v in np.array([P.px(x_, y_, z_)[:2] for x_ in P.BOXES["towels"][0:2] for y_ in P.BOXES["towels"][2:4]
                                               for z_ in P.BOXES["towels"][4:6]]).T.reshape(2, -1).max(1)]
            d0 = [int(xs_.min()), int(ys_.min()), int(xs_.max()) + 1, int(ys_.max()) + 1]
            sc = (bx[3] - bx[1]) / (d0[3] - d0[1])                     # the box's height, as the refits of the defaults
            ax_, ay_, AX_, AY_ = (d0[0] + d0[2]) / 2, d0[3], (bx[0] + bx[2]) / 2, bx[3]   # bottom centre onto bottom centre
            TOWEL_M = np.float32([[sc, 0, AX_ - sc * ax_], [0, sc, AY_ - sc * ay_]])
            rec["towels_refit"] = dict(drawn_bbox=d0, box_bbox=[round(v, 1) for v in bx], scale=round(float(sc), 4), anchor="bottom centre",
                                       affine=[[round(float(v), 4) for v in row] for row in TOWEL_M.tolist()],
                                       new_bbox=[round(AX_ - sc * (ax_ - d0[0]), 1), round(AY_ - sc * (ay_ - d0[1]), 1),
                                                 round(AX_ + sc * (d0[2] - ax_), 1), round(AY_, 1)])
        if k == "bath-towels":
            fg[k] &= ~above_t
        if k == "storage-basket":
            fg[k] &= ~above
        if k == "storage-basket":
            # the cut took the shadowed gap between the basket's right end and the vanity's upright (L* under 13.5, against
            # 16 and up on the basket's shaded end): it comes out where it joins the outside of the cut, right of x 2060
            Lk = np.full((H, W), 100.0)
            Lk[1200:, 2000:2200] = G.to_lab(cv(src_a[1200:, 2000:2200]))[..., 0]
            dk = fg[k] & (Lk < 13.5)
            dk[:, :2060] = False
            n_, lab_ = cv2.connectedComponents(dk.astype(np.uint8), connectivity=8)
            drop = np.isin(lab_, list(set(np.unique(lab_[C.dil(~fg[k], 1) & dk])) - {0}))
            rec["basket_gap_trim_px"] = int(drop.sum())
            fg[k] &= ~drop
            fg[k] = cv2.morphologyEx(fg[k].astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
            n_, lab_, st_, _ = cv2.connectedComponentsWithStats(fg[k].astype(np.uint8), connectivity=8)
            fg[k] = lab_ == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))
    newfg = np.zeros((H, W), bool)
    for k in NEW:
        newfg |= fg[k]
    rec["tray_rise_px"] = dict(RISE, rim_1_8cm_px=rim_px)
    for k in ("soap-dispenser", "toothbrush-cup"):
        rgba, s8 = F[k]
        rgba2 = np.zeros_like(rgba)
        rgba2[:-RISE[k]] = rgba[RISE[k]:]
        s2 = np.full_like(s8, 255)
        s2[:-RISE[k]] = s8[RISE[k]:]
        Image.fromarray(rgba2, "RGBA").save(os.path.join(ST, lay[k]["layer"]))
        Image.fromarray(s2).save(os.path.join(ST, lay[k]["shadow"]))
        F[k] = (rgba2, s2)
        lay[k]["raised_on_tray_px"] = RISE[k]
    # the waffle stack: the render drew it darker and yellower than the photo's taupe-mushroom (against the basket's white body,
    # the shelf's only neutral, L* 66.9 / C* 9.1 / h 52 where the sheet has 72 / 5 / 47): recoloured as M1 to the designer's
    # sheet, in the light of the basket's body (its photo's white by QA's photo method, L* 90.9 / 0.7 / 3.5 = #E9E4DE)
    C.WHITE["basket-body"] = "#E9E4DE"
    ga = cv(src_a)
    gl = G.to_lab(ga)
    bk = fg["storage-basket"]
    ysb = np.nonzero(bk)[0]
    bb = C.ero(bk, 3) & (np.arange(H)[:, None] > ysb.min() + 0.65 * (ysb.max() - ysb.min())) & (np.hypot(gl[..., 1], gl[..., 2]) < 12)
    Lb = gl[..., 0][bb]
    lo, hi = np.percentile(Lb, [20, 80])
    ref_bb = np.median(C.lin(ga[bb][(Lb >= lo) & (Lb <= hi)]), 0)
    # read on the stack's lit front faces (its lower 70 %, facing the room like the basket's body), not on its top face, which
    # lies in the shade under the drawer and would pull the median down (and the solved colour up)
    yt0 = np.nonzero(fg["bath-towels"])[0]
    mt = C.ero(fg["bath-towels"], 3) & (np.arange(H)[:, None] >= yt0.min() + 0.3 * (yt0.max() - yt0.min()))
    before = C.r5_lab(ga, mt, ref_bb, "basket-body")
    src_tw, tm = C.recolour_r5(src_a, fg["bath-towels"], mt, ref_bb, "basket-body", TOWELS_LCH, cv)
    tm.update(method="R5 after the grade: the stack's front faces (its lower 70 %), mid-tone, against the basket's white body beside it (its lower third, "
                     "C* under 12), whose albedo is its photo's (#E9E4DE)", reference_px=int(bb.sum()),
              r5_lab_before=[round(float(v), 2) for v in before], de00_before=round(C.de(before, TOWELS_LCH), 2),
              de00_after_vs_qa_photo_abs=round(float(G.de00(np.array([tm["r5_lab_after"]]), np.array([[69.2, 4.1, 4.7]]))[0]), 2))
    rec["towels_match"] = tm
    # the basket's jute band: drawn 3-6 L* lighter and yellower than the photo's tan (dE00 4.3-5.9 depending on the mask);
    # brought to the photo's tan in the light of the basket's own body (the photo's body/band pair), per channel, solved on the
    # graded result; weighted by chroma (C* 8 -> 14), so the cream body and the fill towels keep their colour
    yb = np.arange(H)[:, None]
    bandm = C.ero(bk, 3) & (yb > ysb.min() + 0.1 * (ysb.max() - ysb.min())) & (yb < ysb.min() + 0.6 * (ysb.max() - ysb.min())) & \
        (np.hypot(gl[..., 1], gl[..., 2]) > 10)
    wgt = np.clip((np.hypot(gl[..., 1], gl[..., 2]) - 8) / 6, 0, 1) * C.dil(bk, 2) * (yb < ysb.min() + 0.7 * (ysb.max() - ysb.min()))
    tan_lin = C.lin(G.from_lab(np.array([BAND_LAB]))[0])
    t_band = tan_lin / C.hex_lin(C.WHITE["basket-body"]) * ref_bb
    def band_read(img):
        Lx = G.to_lab(img[bandm])[:, 0]
        lo_, hi_ = np.percentile(Lx, [20, 80])
        return np.median(C.lin(img[bandm][(Lx >= lo_) & (Lx <= hi_)]), 0)
    f = np.ones(3)
    lin_a = C.lin(src_a)
    for _ in range(16):
        src_bk = C.srgb(np.clip(lin_a * (1 + wgt[..., None] * (f - 1)), 0, 1))
        f = f * (t_band / np.maximum(band_read(cv(src_bk)), 1e-6)) ** 0.85
    src_bk = C.srgb(np.clip(lin_a * (1 + wgt[..., None] * (f - 1)), 0, 1))
    def rd(img):
        return G.to_lab(C.srgb(np.clip(band_read(img) / ref_bb * C.hex_lin(C.WHITE["basket-body"]), 0, 1))[None])[0]
    b0, b1 = rd(ga), rd(cv(src_bk))
    rec["basket_band_match"] = dict(method="the jute band (rows 10-60 % of the basket, C* over 10), mid-tone, against the basket's white body; "
                                           "target the photo's tan by QA's photo method", target_lab=list(BAND_LAB), gain_rgb=[round(float(v), 4) for v in f],
                                    band_px=int(bandm.sum()), lab_before=[round(float(v), 2) for v in b0], lab_after=[round(float(v), 2) for v in b1],
                                    de00_before=round(float(G.de00(b0[None], np.array([BAND_LAB]))[0]), 2),
                                    de00_after=round(float(G.de00(b1[None], np.array([BAND_LAB]))[0]), 2))
    for k in NEW:
        oth = (allfg | newfg) & ~fg[k]
        s = shadow(src_a, base_a, fg[k], NEW[k]["band"], NEW[k]["rim"], C.dil(oth, 1))
        a = C.soft(fg[k])
        rgb = cv(C.defringe({"bath-towels": src_tw, "storage-basket": src_bk}.get(k, src_a), fg[k]))
        if k == "bath-towels":
            # the whole stack (layer and shadow) scaled to the box about its bottom centre; the render's darkening moves with it
            a = cv2.warpAffine(a.astype(np.float32), TOWEL_M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
            rgb = cv2.warpAffine(rgb.astype(np.float32), TOWEL_M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT).astype(np.float64)
            dk = np.zeros((H, W))
            dk[1150:, 1250:1800] = (1 - s)[1150:, 1250:1800]
            s = 1 - cv2.warpAffine(dk.astype(np.float32), TOWEL_M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float64)
            s[C.dil(oth, 1)] = 1
            a[a < 0.02] = 0
        sg = graded_shadow(s, base_a, cv)
        if k == "vanity-tray":
            # the render's tray already carries the dispenser's and the cup's contact; their own shadow layers (z above the tray)
            # darken it again: the tray's pixels under those shadows are divided by them, so the composite there is the render's
            shp = np.ones((H, W))
            for o in ("soap-dispenser", "toothbrush-cup"):
                shp *= F[o][1].astype(np.float64) / 255
            under = (a > 0) & (shp < 1)
            cap = np.percentile(rgb[C.ero(fg[k], 3) & ~C.dil(shp < 1, 4)], 98, axis=0)
            rgb[under] = np.minimum(rgb[under] / shp[under][:, None], cap)
            rec["tray_unshadowed_px"] = int(under.sum())
        lp, sh, rgba, s8 = write_layer(k, NEW[k]["pid"], a, rgb, sg)
        ys, xs = np.nonzero((rgba[..., 3] > 0) | (s8 < 255))
        man["layers"].append(dict(slot=k, product=NEW[k]["pid"], card=NEW[k]["card"], sku=NEW[k]["sku"], z=NEW[k]["z"], default=True,
                                  layer=lp, shadow=sh, shadow_z=NEW[k]["z"] - 1, pass_="fb10-a", alpha_px=int((rgba[..., 3] > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
        F[k] = (rgba, s8)
    for l in man["layers"]:
        l["pass"] = l.pop("pass_", l.get("pass", "defaults"))
    # ---------- pass T3 ----------
    base_t = P.inv_curve(stack(man, plate, F, skip=("hand-towel",)), curve)
    pht = np.asarray(Image.open(os.path.join(ST, "inputs", "fb10-t3-mask.png"))) > 0
    zt = C.dil(pht, 40)
    keep_t = ~C.dil(zt, 40)
    src_t, rec["t3_render"] = locked(os.path.join(ST, "raw", "fb10-t3-r1.png"), base_t, keep_t)
    ring = F["towel-ring"][0][..., 3] > 0
    lab = C.lab_of(src_t)
    khaki = (lab[..., 0] > 8) & (lab[..., 0] < 60) & (np.hypot(lab[..., 1], lab[..., 2]) > 8) & (lab[..., 2] > 6) & ~C.dil(ring, 2)
    hard_t = (allfg & ~ring & ~(F["hand-towel"][0][..., 3] > 0)) & ~C.dil(pht, 2)
    ft = cut(src_t, base_t, pht, zt, hard_t, prior=C.ero(pht, 10) & khaki)
    # (no wall trim here: the khaki reads like the shadowed plaster in a*/C*, and the T3 base has no towel to confuse the cut)
    # the render drew the khaki as light as the linen (R5 albedo L* about 80 against the plaster rings) where the photo is a dark
    # khaki (L* 43): a product mismatch, recoloured like the caramel (M1): its own waffle shading, the photo's colour in the light
    # of the plaster round it, solved on the graded result
    oth0 = (allfg | newfg) & ~(F["hand-towel"][0][..., 3] > 0)
    lowm_k, rings_k = C.towel_rings(ft, oth0 | ft)
    plate_g = plate.astype(np.float64) / 255
    refs_k = [np.median(C.lin(plate_g[r]), 0) for r in rings_k]
    ref_k = np.exp(np.mean(np.log(np.array(refs_k)), 0))
    src_t0 = src_t                    # the shadow is read off the render as drawn (the recolour would darken its rim's blur)
    src_t, km = C.recolour_r5(src_t, ft, lowm_k, ref_k, "plaster", KHAKI_LCH, cv)
    gk = cv(src_t)
    labs_k = [C.r5_lab(gk, lowm_k, rf, "plaster") for rf in refs_k]
    km.update(method="R5 after the grade, as the caramel (M1): lower half, mid-tone, against the plaster round the towel (#ECE5DA); "
                     "target the supplier photo read by QA's photo method (b2_colour.photo)",
              rings_lab=[[round(float(v), 2) for v in l] for l in labs_k], de00_rings=[round(C.de(l, KHAKI_LCH), 2) for l in labs_k],
              de00_rings_vs_designer_sheet=[round(C.de(l, KHAKI_SHEET), 2) for l in labs_k])
    rec["t3_khaki_match"] = km
    oth = (allfg | newfg) & ~F["hand-towel"][0][..., 3].astype(bool) & ~ft
    s = shadow(src_t0, base_t, ft, T3["band"], T3["rim"], C.dil(oth & ~ring, 1))
    a = C.soft(ft)
    rgb = cv(C.defringe(src_t, ft))
    sg = graded_shadow(s, base_t, cv)
    lp, sh, rgba_t, s8_t = write_layer("hand-towel", T3["pid"], a, rgb, sg)
    np.save(os.path.join(SCR, "npz", "fb10-t3-fg.npy"), ft)
    np.save(os.path.join(SCR, "npz", "fb10-new-fg.npy"), np.stack([fg[k] for k in NEW]))
    # ---------- composites from the files ----------
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    def region_of(pairs):
        r = L8.max(2) > 0
        for rgba, s8 in pairs:
            r |= (rgba[..., 3] > 0) | (s8 < 255)
        return r
    out = {}
    o8 = C.q(stack(man, plate, F))
    Image.fromarray(o8).save(os.path.join(ST, "b2-defaults.png"))
    C.frame_png(o8, os.path.join(ST, "b2-defaults-frame.png"))
    reg = region_of(F.values())
    out["defaults"] = int((np.abs(o8.astype(int) - plate.astype(int)).max(2)[~reg] > 0).sum())
    for v in man.get("variants", []):
        sw = {v["slot"]: (np.asarray(Image.open(os.path.join(ST, v["layer"]))), np.asarray(Image.open(os.path.join(ST, v["shadow"]))))}
        ov = C.q(stack(man, plate, F, swap=sw))
        name = v["composite"].rsplit(".", 1)[0]
        Image.fromarray(ov).save(os.path.join(ST, name + ".png"))
        C.frame_png(ov, os.path.join(ST, name + "-frame.png"))
        rv = region_of(list(F.values()) + list(sw.values()))
        out[name] = int((np.abs(ov.astype(int) - plate.astype(int)).max(2)[~rv] > 0).sum())
        d = np.abs(ov.astype(int) - o8.astype(int)).max(2) > 0
        v["differing_px_vs_defaults_outside_alpha"] = int((d & (sw[v["slot"]][0][..., 3] == 0)).sum())
        v["outside_differing_px_vs_plate"] = out[name]
    sw = {"hand-towel": (rgba_t, s8_t)}
    ok = C.q(stack(man, plate, F, swap=sw))
    Image.fromarray(ok).save(os.path.join(ST, "b2-variant-khaki.png"))
    C.frame_png(ok, os.path.join(ST, "b2-variant-khaki-frame.png"))
    rk = region_of(list(F.values()) + [(rgba_t, s8_t)])
    out["b2-variant-khaki"] = int((np.abs(ok.astype(int) - plate.astype(int)).max(2)[~rk] > 0).sum())
    dk = np.abs(ok.astype(int) - o8.astype(int)).max(2) > 0
    swap_reg = (rgba_t[..., 3] > 0) | (s8_t < 255) | (F["hand-towel"][0][..., 3] > 0) | (F["hand-towel"][1] < 255)
    man["variants"] = [x for x in man.get("variants", []) if x["product"] != T3["pid"]] + [dict(
        slot="hand-towel", product=T3["pid"], card=T3["card"], sku=T3["sku"], z=52, default=False, method="its own render (pass T3), own alpha and shadow",
        layer=lp, shadow=sh, composite="b2-variant-khaki.png", alpha_px=int((rgba_t[..., 3] > 0).sum()), shadow_px=int((s8_t < 255).sum()),
        outside_differing_px_vs_plate=out["b2-variant-khaki"], differing_px_vs_defaults_outside_the_swap_region=int((dk & ~swap_reg).sum()))]
    man["rnd2"] = dict(region_px=int(reg.sum()), outside_differing_px=out["defaults"], rule=man["rnd2"]["rule"])
    man["compose"]["order"] = ["base"] + [f"{l['slot']}-shadow, {l['slot']}" for l in sorted(man["layers"], key=lambda l: l["z"])] + ["light (screen)"]
    man["fb10"] = dict(date="2026-11-18", tool="tools/compose_fb10.py", source="docs/proposals/wm-bath-render-2026-11-17.md 12.6 (HOUSE2B)",
                       passes=["fb10-a (nano-banana-2, 400)", "fb10-t3 (nano-banana-2, 400)"], rnd2_outside_differing_px=out, **rec)
    json.dump(man, open(man_p, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(rnd2=out, **rec), default=float))


if __name__ == "__main__":
    main()
