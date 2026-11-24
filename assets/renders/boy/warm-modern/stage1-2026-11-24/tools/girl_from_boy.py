#!/usr/bin/env python3
"""
girl_from_boy.py: the girl's family layers made by code from the boy's (ב.6 2: "the family slots above 1.25 (the pendant, the blind,
prints A and B) are moved by code from the boy, because the background is the same; the Type A art goes into the frames by code"),
render-agent, 2026-11-24; 0 tokens. The same camera and shell (+3.63 in Y), so a layer, its shadow and the lamp's light carry over pixel
for pixel; what changes:
  - the prints: the boy's frames with their blank canvases (kept by kids_art.py), the girl's Type A panels placed by kids_art.py;
  - the pen cup: the same listing in Beech (ד.2 row 7). The SKU photos of Walnut and Beech are one drawing in two woods, so the cup's
    pixels (the clay's cup region, not the pencils) are recoloured as the sample slot's variants: Y x (Y(78.2) / Y(41.9)), the hue and
    chroma of the Beech photo (L*78.2 C*31.8 h68) at the light's scale;
  - the toy cars are the boy's only and are not carried over.
Also carried, unchanged: the bookshelf (two ledge pairs, the face-out books, frame C on the top ledge), the bookends and their books.
  python3 girl_from_boy.py
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import kids_cut as KC  # noqa: E402
import kids_art as KA  # noqa: E402
from kids_passes import PRODUCTS, GIRL_FROM_BOY  # noqa: E402

C = K.C


def recolour_cup(rgba, ids):
    """K-G3 (QA 2026-11-24): the Beech cup built from the walnut cup's light, not its grain. The walnut's shading on a 4 px normalised
    blur (no grain, no gloss), its contrast compressed to 0.6 round the lit half, and 15 % of the fine grain kept; the lit half's median
    set to the Beech photo (L*78.2 C*31.8 h68), the chroma following L* (C*/L* of the photo), one hue: matte, even, light wood"""
    a = rgba[..., 3].astype(np.float64) / 255
    lab = C.to_lab(rgba[..., :3].astype(np.float64) / 255)
    L = lab[..., 0]
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))
    cc = np.hypot(lab[..., 1], lab[..., 2])
    # the boy's olive band seen between the pencils was cut into the layer: it goes (the girl's band shows through)
    bg = (a > 0) & (hh > 90) & (hh < 140) & (cc > 4)
    a = np.where(bg, 0.0, a)
    # the cup: the clay's cup, and the dark walnut inside its opening (under the pencils), which is the cup's inside, not a pencil
    inside = C.dil(ids == 49, 1) & (L < 45) & (hh > 35) & (hh < 75) & (a > 0)
    cup = ((C.dil(ids == 48, 3) & ~C.dil(ids == 49, 1)) | inside) & (a > 0)
    w = cup.astype(np.float64)
    Ls = C.blur(L * w, 4) / np.maximum(C.blur(w, 4), 1e-4)
    core = cup & (a > 0.98)
    lit = core & (Ls >= np.median(Ls[core]))
    m_lit = float(np.median(Ls[lit]))
    Lt, Ct, ht = 78.2, 31.8, 68.0
    Ln = np.clip(Lt + 0.6 * (Ls - m_lit) + 0.15 * (L - Ls), 30, 92)
    t = K.from_lch(100.0, Ct / Lt * 100.0, ht)
    an, bn = t[1] * Ln / 100.0, t[2] * Ln / 100.0
    lab[..., 0] = np.where(cup, Ln, lab[..., 0])
    lab[..., 1] = np.where(cup, an, lab[..., 1])
    lab[..., 2] = np.where(cup, bn, lab[..., 2])
    rgb = KC.floor_lab(np.clip(C.from_lab(lab), 0, 1), a > 0)
    # the walnut's soft edge was unmixed against the olive band: as light beech it reads as a pale rim, so the cup's edge is pulled in 1 px
    rim = cup & ~C.ero(cup & (a > 0.98), 1)
    a = np.where(rim, a * 0.45, a)
    out = np.dstack([C.q(rgb), C.q(a)])
    out[..., :3][out[..., 3] == 0] = 0
    lab2 = C.to_lab(rgb)
    lit2 = core & (lab2[..., 0] >= np.median(lab2[..., 0][core]))
    med = np.median(lab2[lit2], 0)
    return out, dict(cup_px=int(cup.sum()), olive_background_removed_px=int(bg.sum()), inside_px=int(inside.sum()), lit_half_Lab=[round(float(v), 1) for v in med],
                     photo_Lab=[round(float(v), 1) for v in K.from_lch(Lt, Ct, ht)],
                     dE00_lit_half=round(float(C.de00(tuple(med), tuple(K.from_lch(Lt, Ct, ht)))), 2),
                     method=recolour_cup.__doc__.split("K-G3 (QA 2026-11-24): ")[1].strip())


def recolour_cup2(rgba, ids, boy_plate):
    """K-G3 recheck (QA 2026-11-24, after c4b811c0): the colour held (dE00 0.10) but the cup read flat, a glowing peach block: no grain
    (0.62 against the photo's 3.28), no shade between its faces (75.1 / 75.4), a light ring round it, ragged pencil bottoms. Now:
    - the pencils keyed against the boy's plate (the band each walnut pixel was drawn on): dE76 over 20 the pencil, its dark sides
      too; under 6 the band (alpha 0); between, a ramp (under 0.2: none) with the pencil's colour spread from its sure pixels; the
      dark walnut above the front lip (9 rows, L* < 32: the opening and the back rim) is the cup's; the cup's
      outline keeps the cut's alpha (its left edge is a real highlight) and takes the model's colour; where the boy's layer carried
      his band in the cup's shade (olive, darker than his plate), alpha 0 and that shade (his layer's luminance over his plate's)
      goes into the cup's shadow layer (median 5 px, then a 2.5 px normalised blur, at most 0.45, the pencils' edges not sampled);
    - the shading as the walnut's light in linear Y, not its figure: per column, the front face's walnut profile fitted by a line
      (the gradient from the window; flat if it would brighten towards the corner: that is the walnut's satin), the right side face at its own walnut ratio (power 0.75: a matte wood keeps less of the walnut's
      satin contrast), a 1.5 px corner, the left rounded edge's highlight held to 1.12; per row, the walnut's profile (smoothed, power
      0.7, the lip's highlight held to 1.12); the inside at the walnut's own ratio (power 0.75);
    - the grain: the walnut's fine structure (L* minus its 3 px blur, clipped to +-8, 2 px inside the outline) scaled to the photo's
      about 3.3 on the result (QA's measure; the photo 3.28);
    - the lit half (R5) set to the Beech photo (L*78.2), the chroma following L* (C*/L* of the photo), hue 68"""
    a0 = rgba[..., 3].astype(np.float64) / 255
    I = rgba[..., :3].astype(np.float64) / 255
    lab = C.to_lab(I)
    L = lab[..., 0]
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    cc = np.hypot(lab[..., 1], lab[..., 2])
    B = boy_plate
    Hh, Ww = a0.shape
    yy = np.arange(Hh)[:, None] + np.zeros((1, Ww), int)
    xx = np.zeros((Hh, 1), int) + np.arange(Ww)[None, :]
    front = ids == 48
    fr_rows = np.nonzero((front & (yy > 805)).sum(1) >= 10)[0]
    lip = int(fr_rows.min())                                           # the front lip's first row (816)
    cx = np.nonzero(front[lip + 4])[0]
    x0c, x1c = int(cx.min()), int(cx.max())
    body = (C.dil(front | (ids == 49), 3) & (yy >= lip - 1) & (a0 > 0))    # the clay's pencils run down behind the front face
    # the pencils (above the lip) and the opening's inside (dark, the 6 rows above the lip, between the pencils)
    above = (a0 > 0) & (yy < lip - 1)
    olive = (hh > 90) & (hh < 140) & (cc > 4)
    dB = np.linalg.norm(lab - C.to_lab(B), axis=-1)
    # the pencils by difference against the band they were drawn on (the boy's plate): dE76 over 20 the pencil (its dark sides too),
    # under 6 the band (alpha 0), between a ramp with the pencil's own colour spread from its sure pixels
    inside = above & (yy >= lip - 9) & (L < 32) & ~olive                      # the opening and the back rim (walnut, not band)
    band_like = (hh > 75) & (hh < 140) & (cc < 20) & (L < 70)                # the band in the cup's shade: olive, darker than the plate
    sure = above & ~inside & (dB > 20) & ~band_like
    ramp = np.clip((dB - 6) / 14, 0, 1) * ~band_like
    a_p = np.where(above & ~inside, np.minimum(a0, np.where(sure, 1.0, ramp)), 0.0)
    a_p = np.where(a_p < 0.2, 0.0, a_p)
    P = KC.KC.spread(I, sure.astype(np.float64), (1.0, 2.0, 4.0))
    F_p = np.where(sure[..., None], I, P)
    walnut_sure = C.ero(body & (a0 > 0.98), 2)
    # the cup's outline keeps the cut's alpha (its left edge is a real highlight, not band); its colour comes from the model below
    a_b = a0
    F_b = np.where(walnut_sure[..., None], I, KC.KC.spread(I, walnut_sure.astype(np.float64), (1.5, 3.0, 6.0)))
    # the walnut's light, in Y
    Lw = C.to_lab(np.where(body[..., None], F_b, I))[..., 0]
    Yw = ((np.maximum(Lw, 0) + 16) / 116) ** 3
    core = walnut_sure & (yy > lip + 6) & (yy < fr_rows.max() - 4)
    cols = np.arange(x0c - 6, x1c + 7)                                # the outline too (the cut runs 3-4 px past the clay)
    prof = np.array([np.median(Yw[:, x][core[:, x]]) if core[:, x].sum() > 8 else np.nan for x in cols])
    ok = ~np.isnan(prof)
    sm = np.convolve(np.nan_to_num(prof, nan=np.nanmedian(prof)), np.ones(3) / 3, "same")
    rr = np.nonzero(ok)[0]
    lo, hi = rr.min(), rr.max()
    span = hi - lo + 1
    seg = sm[lo + int(0.6 * span):hi - 1]
    corner = lo + int(0.6 * span) + int(np.argmin(np.diff(seg))) + 1      # the steepest fall in the right part: the corner
    fx = np.arange(lo + 4, corner - 1)
    q = np.polyfit(fx, prof[fx], 1)
    if q[0] > 0:                        # brighter towards the corner is the walnut's satin catching the window, not light: flat
        q = np.array([0.0, float(np.median(prof[fx]))])
    ref = float(np.polyval(q, fx).max())
    Fcol = np.ones(len(cols))
    for i in range(len(cols)):
        if i < lo + 4:
            Fcol[i] = min(float(np.nanmax([prof[i] if ok[i] else ref, ref])) / ref, 1.12) if ok[i] else 1.0
        elif i < corner:
            Fcol[i] = float(np.polyval(q, i)) / ref
        else:
            Fcol[i] = 1.0
    side = np.nanmedian(prof[corner + 1:hi - 1]) / float(np.polyval(q, corner - 2))
    side_r = float(side ** 0.75)
    t = np.clip((np.arange(len(cols)) - (corner - 0.75)) / 1.5, 0, 1)
    Fcol = Fcol * (1 - t) + (Fcol[corner - 2] if corner >= 2 else 1.0) * side_r * t
    Fx = np.ones((Hh, Ww))
    Fx[:, cols] = Fcol[None, :]
    rows = np.arange(lip - 1, fr_rows.max() + 4)
    rp = np.array([np.median(Yw[y][walnut_sure[y]]) if walnut_sure[y].sum() > 10 else np.nan for y in rows])
    rp = np.where(np.isnan(rp), np.nanmedian(rp), rp)
    rp = np.convolve(rp, np.ones(3) / 3, "same")
    rref = float(np.median(rp[6:-6]))
    Frow = np.clip((rp / rref) ** 0.7, 0.4, 1.12)
    Fy = np.ones((Hh, Ww))
    Fy[rows] = Frow[:, None]
    F = Fx * Fy
    Ywb = C.blur(Yw * inside, 1.0) / np.maximum(C.blur(inside.astype(np.float64), 1.0), 1e-4)
    F = np.where(inside, np.clip((Ywb / ref) ** 0.75, 0.15, 1.0), F)
    hp = Lw - C.blur(Lw * body, 3) / np.maximum(C.blur(body.astype(np.float64), 3), 1e-4)
    hp = np.clip(hp, -8, 8) * C.ero(body, 2)                  # the grain, not the outline's highlights (clipped, 2 px in)
    g = 2.4 / max(float(np.std(hp[core])), 1e-3)                  # 2.4 here reads about 3.3 on the result (its shading edges add)
    Lt, Ct, ht = 78.2, 31.8, 68.0
    cupm = body | inside
    Ys = 1.0
    for _ in range(6):
        Ln = 116 * np.cbrt(np.clip(Ys * ((Lt + 16) / 116) ** 3 * F, 1e-6, 1)) - 16 + g * hp * (~inside)
        Ln = np.clip(Ln, 10, 94)
        m = core & (Ln >= np.median(Ln[core]))
        r5 = float(np.median(Ln[m]))
        Ys *= (((Lt + 16) / 116) ** 3) / (((r5 + 16) / 116) ** 3)
    tt = K.from_lch(100.0, Ct / Lt * 100.0, ht)
    labn = np.stack([Ln, tt[1] * Ln / 100.0, tt[2] * Ln / 100.0], -1)
    beech = np.clip(C.from_lab(labn), 0, 1)
    rgb = np.where(cupm[..., None], beech, F_p)
    alpha = np.where(cupm, np.where(inside, 1.0, a_b), a_p)
    alpha = np.where(alpha < 2 / 255, 0.0, alpha)
    rgb = KC.floor_lab(rgb, alpha > 0)
    out = np.dstack([C.q(rgb), C.q(alpha)])
    out[..., :3][out[..., 3] == 0] = 0
    labo = C.to_lab(rgb)
    lit2 = core & (labo[..., 0] >= np.median(labo[..., 0][core]))
    med = np.median(labo[lit2], 0)
    thirds = np.array_split(np.arange(x0c, x1c + 1), 3)
    th = [round(float(np.median(labo[..., 0][core & np.isin(xx, t3)])), 1) for t3 in thirds]
    hp2 = labo[..., 0] - C.blur(labo[..., 0] * body, 3) / np.maximum(C.blur(body.astype(np.float64), 3), 1e-4)
    rec = dict(lip_row=lip, corner_col=int(cols[corner]), side_face_ratio_Y=round(side_r, 3), grain_gain=round(g, 3),
               grain_std_L_minus_blur3=round(float(np.std(hp2[core])), 2), thirds_L=th, lit_half_Lab=[round(float(v), 1) for v in med],
               photo_Lab=[round(float(v), 1) for v in K.from_lch(Lt, Ct, ht)],
               dE00_lit_half=round(float(C.de00(tuple(med), tuple(K.from_lch(Lt, Ct, ht)))), 2),
               pencils_edge_px=int(((a_p > 0) & (a_p < 1)).sum()), band_between_pencils_px=int((above & ~inside & (a_p == 0)).sum()),
               inside_px=int(inside.sum()), method=recolour_cup2.__doc__.split("Now:")[1].strip())
    # the band the boy's layer carried (between the pencils, in the cup's shade): its shade, as the layer's luminance over the plate's
    lum = lambda v: (C.lin(v) * np.array([0.2126, 0.7152, 0.0722])).sum(-1)   # noqa: E731
    band_px = (a0 > 0) & (alpha == 0)
    import cv2
    ratio = np.clip(lum(I) / np.maximum(lum(B), 1e-4), 0.4, 1.0)
    samp = band_px & ~C.dil(alpha > 0, 1) & C.ero(a0 > 0.98, 2)             # not the pencils' edges, not the layer's own outline
    rmed = cv2.medianBlur(C.q(ratio), 5).astype(np.float64) / 255
    dk = C.blur((1 - rmed) * samp, 2.5) / np.maximum(C.blur(samp.astype(np.float64), 2.5), 1e-4)
    shade = np.where(band_px, 1 - np.clip(dk, 0, 0.45), 1.0)
    rec["band_shade_px"] = int((band_px & (shade < 0.98)).sum())
    return out, rec, (a0 > 0) & (yy >= lip - 2), shade


def fill_cup_shadow(sh, boy_alpha_body, girl_alpha):
    """the boy's cup shadow is 1 under his cup; where the girl's matted cup is thinner (its outline) the band showed unshaded, a light
    ring: there the shade is filled from just outside (a normalised blur, 3 px)"""
    hole = C.dil(boy_alpha_body & (girl_alpha < 0.98), 1)
    known = ~C.dil(boy_alpha_body, 1) & C.dil(hole, 10)
    dark = 1 - sh
    fillv = C.blur(dark * known, 3) / np.maximum(C.blur(known.astype(np.float64), 3), 1e-4)
    return np.where(hole, 1 - fillv, sh), int(hole.sum())


def clean_olive_edge(rgba):
    """K-G2 (QA 2026-11-24): the boy's layers were cut on his olive band; at their edge (alpha under 1, and 2 px inside it) an olive
    tint (h 90-140, C* over 4) takes the product's own colour spread from inside"""
    a = rgba[..., 3] > 0
    solid = rgba[..., 3] >= 250
    edge = a & ~C.ero(solid, 2)
    rgb = rgba[..., :3].astype(np.float64) / 255
    lab = C.to_lab(rgb)
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))
    cc = np.hypot(lab[..., 1], lab[..., 2])
    ol = edge & (h > 90) & (h < 140) & (cc > 4)
    if ol.any():
        fill = KC.KC.spread(rgb, (C.ero(solid, 2) & ~ol).astype(np.float64), (2.0, 5.0, 12.0))
        rgb = np.where(ol[..., None], fill, rgb)
    out = rgba.copy()
    out[..., :3] = C.q(rgb)
    out[..., :3][out[..., 3] == 0] = 0
    return out, int(ol.sum())


def main_cup():
    """K-G3 recheck: only the pen cup, its layer and its shadow (python3 girl_from_boy.py pen-cup)"""
    sb, sg = K.ST["boy"], K.ST["girl"]
    mb, mg = KC.load_man("boy"), KC.load_man("girl")
    ids = K.ids("K-girl")
    lb = [l for l in mb["layers"] if l["key"] == "pen-cup" and l.get("default", True)][0]
    lg = [l for l in mg["layers"] if l["key"] == "pen-cup" and l.get("default", True)][0]
    src = np.asarray(Image.open(os.path.join(sb, lb["layer"]))).copy()
    out, rec, boy_body, shade = recolour_cup2(src, ids, C.load(os.path.join(sb, "plate.png")))
    Image.fromarray(out, "RGBA").save(os.path.join(sg, lg["layer"]), optimize=True)
    sh = np.asarray(Image.open(os.path.join(sb, lb["shadow"]))).astype(np.float64) / 255
    sh2, nh = fill_cup_shadow(sh, boy_body, out[..., 3] / 255)
    sh2 = np.minimum(sh2, shade)
    Image.fromarray(C.q(np.clip(sh2, 0, 1))).save(os.path.join(sg, lg["shadow"]), optimize=True)
    rec["shadow_ring_filled_px"] = nh
    mg = KC.load_man("girl")
    mg.setdefault("code_fixes", {}).setdefault("from the boy", {})["pen-cup"] = rec
    KC.save_man("girl", mg)
    print(json.dumps({k: v for k, v in rec.items() if k != "method"}))


def main():
    sb, sg = K.ST["boy"], K.ST["girl"]
    mb = KC.load_man("boy")
    mg = KC.load_man("girl")
    ids = K.ids("K-girl")
    rec = {}
    for key in GIRL_FROM_BOY:
        lb = [l for l in mb["layers"] if l["key"] == key and l.get("default", True)][0]
        slot, pid, z, cids, sku = PRODUCTS["girl"][key]
        lp = os.path.join(sg, "layers", slot, pid + ".png")
        sp = os.path.join(sg, "shadows", slot, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        src = os.path.join(sb, lb["layer"])
        if key == "framed-prints":
            src = os.path.join(K.SCR, "boy-framed-prints-blank.png")
        rgba = np.asarray(Image.open(src)).copy()
        if key == "pen-cup":
            rgba, rec["pen-cup"] = recolour_cup(rgba, ids)
        if key in ("pen-cup", "bookends"):
            rgba, n_ = clean_olive_edge(rgba)
            rec.setdefault("olive edge cleaned px", {})[key] = n_
        Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
        shutil.copy(os.path.join(sb, lb["shadow"]), sp)
        mg["layers"] = [l for l in mg["layers"] if not (l["key"] == key and l.get("default", True))]
        e = dict(lb, product=pid, sku=sku, layer=os.path.relpath(lp, sg), shadow=os.path.relpath(sp, sg),
                 source=f"the boy's layer by code (tools/girl_from_boy.py, ב.6): {lb['source']}", pass_="from-boy", passes=["from-boy"] + lb.get("passes", []))
        mg["layers"].append(e)
    for li in mb["light"]:
        dst = os.path.join(sg, li["file"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(os.path.join(sb, li["file"]), dst)
        mg["light"] = [x for x in mg["light"] if x["file"] != li["file"]]
        mg["light"].append(dict(li, pass_="from-boy", note="the boy's pendant light, the same lamp at the same place"))
    mg.setdefault("code_fixes", {})["from the boy"] = dict(rec, carried=GIRL_FROM_BOY, not_carried=["toy-cars (the boy's only)"])
    KC.save_man("girl", mg)
    if os.path.exists(os.path.join(K.SCR, "wm-kids", "art", "girl-0.png")) or True:
        KA.place("girl")
    print(json.dumps(rec))


if __name__ == "__main__":
    if sys.argv[1:] == ["pen-cup"]:
        main_cup()
    else:
        main()
