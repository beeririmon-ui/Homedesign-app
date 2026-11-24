#!/usr/bin/env python3
"""
kids_variants.py: the sample slot's variants, colour only, in code (ד.4: "all six SKU photos of the waffle gauze are one scene
recoloured: the geometry and the fold are identical in the three variants, so V2 and V3 come out by recolouring in code in the throw's
mask (0 tokens), by the measured Lab values"), render-agent, 2026-11-24.
The readings of the photo check (picks/new-rooms-photo-check.json, the lit side; ד.4): Deep Chestnut L*46.2 C*8.8 h51; Coffee L*56.3
C*19.7 h74; Green L*35.9 C*18.5 h110; Linen Brown L*57.4 C*12.6 h73; Pink L*67.8 C*13.2 h48.
Per pixel of the throw's layer, in Lab:
  - L*: in linear light, Y x (Y_photo(Vn) / Y_photo(V1)): the same shading and texture, the photo's step in lightness;
  - a* b*: the rendered V1's own a* b* minus its median, plus the photo's a* b* of Vn scaled by s = (rendered V1 median L*) / (photo V1
    L*): the hue is the photo's, the chroma follows the light the throw is in.
V1 itself is checked the same way against its photo (hue and chroma at the scale s) and moved when it is off by more than dE00 3.
The shadow of every variant is V1's (the same geometry). Writes layers/bedspread/<variant>.png and K-<kid>-V2 / -V3 frames.
  python3 kids_variants.py <kid>
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import kids_cut as KC  # noqa: E402
from kids_passes import PRODUCTS, VARIANTS, VARIANT_SKU  # noqa: E402

C = K.C
PHOTO = {"spread-chestnut": (46.2, 8.8, 51), "spread-coffee": (56.3, 19.7, 74), "spread-green": (35.9, 18.5, 110),
         "spread-linen": (57.4, 12.6, 73), "spread-pink": (67.8, 13.2, 48)}


def Y(L):
    return np.where(L > 8, ((L + 16) / 116) ** 3, L / 903.3)


def Lof(y):
    return np.where(y > 216 / 24389, 116 * np.cbrt(y) - 16, 903.3 * y)


def main(kid):
    st = K.ST[kid]
    man = KC.load_man(kid)
    v1 = [l for l in man["layers"] if l["key"] == "bedspread" and l.get("default", True)][0]
    rgba = np.asarray(Image.open(os.path.join(st, v1["layer"]))).astype(np.float64) / 255
    a = rgba[..., 3]
    lab = C.to_lab(rgba[..., :3])
    # the duvet seen between the fringe's strands sits inside the throw's layer (the fringe is one piece there): it keeps its colour.
    # Weight w: 1 on the throw's side of the cut's hue line (6 degrees in), 0 six degrees past it; below C* 5, by L*
    tr = man.get("cut_records", {}).get("PB1-bed" if kid == "boy" else "GB1-bed", {}).get("mask_edit", {}).get("throw", {})
    hh, cc = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])), np.hypot(lab[..., 1], lab[..., 2])
    if tr.get("hue_thr") is not None:
        u = (hh - tr["hue_thr"]) * tr["hue_sign"]
        w = np.where(cc > 5, np.clip((u + 6) / 12, 0, 1), np.clip((60 - lab[..., 0]) / 15, 0, 1))
    else:
        w = np.ones(a.shape)
    # the hue test only where duvet can show between strands: the bottom 30 px of the throw (the fringe); elsewhere the layer is throw
    m_ = a > 0
    below = np.zeros_like(m_)
    below[:-30] = m_[30:]
    fringe_band = m_ & ~below
    w = np.where(fringe_band, w, 1.0)
    w = C.blur(w, 0.7) * (a > 0)
    core = (a > 0.6) & (w > 0.9)
    med = np.median(lab[core], 0)
    p1 = VARIANTS[kid]["V1"][1]
    L1p, C1p, h1p = PHOTO[p1]
    s = med[0] / L1p
    rec = dict(rule=__doc__.split("Per pixel")[1].split("Writes")[0].strip(), duvet_between_strands_kept_px=int(((a > 0) & (w < 0.1)).sum()),
               v1_rendered_Lab=[round(float(v), 1) for v in med],
               v1_rendered_LCh=[round(v, 1) for v in K.lch(med)], chroma_scale_s=round(float(s), 3), variants={})
    tgt1 = K.from_lch(med[0], C1p * s, h1p)
    de1 = float(C.de00(tuple(med), (med[0], tgt1[1], tgt1[2])))
    rec["v1_vs_photo_dE00_hue_chroma"] = round(de1, 2)
    if de1 > 3.0:
        lab[..., 1] += w * (tgt1[1] - med[1])
        lab[..., 2] += w * (tgt1[2] - med[2])
        rgb1 = KC.floor_lab(np.clip(C.from_lab(lab), 0, 1), a > 0)
        out = np.dstack([C.q(rgb1), C.q(a)])
        out[..., :3][out[..., 3] == 0] = 0
        Image.fromarray(out, "RGBA").save(os.path.join(st, v1["layer"]), optimize=True)
        rec["v1_fix"] = dict(ab_shift=[round(float(tgt1[1] - med[1]), 2), round(float(tgt1[2] - med[2]), 2)],
                             why="the rendered V1's hue / chroma off its SKU photo by more than dE00 3 (EFF1.3: a mismatch with the product)")
        lab = C.to_lab(np.clip(C.from_lab(lab), 0, 1))
        med = np.median(lab[core], 0)
    for vn in ("V2", "V3"):
        pid, pk = VARIANTS[kid][vn]
        Lp, Cp, hp = PHOTO[pk]
        tgt = K.from_lch(0, Cp * s, hp)
        if kid == "girl" and vn == "V3":
            # ב.4: the girl's pink at HSL S <= 40 (read on the layer's median, as kids_checks.py): the chroma eased until it is
            import colorsys
            f_ = 1.0
            for _ in range(8):
                y_ = Y(lab[..., 0]) * (Y(np.array(Lp)) / Y(np.array(L1p)))
                mk_ = (a > 200 / 255) & K.frame_mask()           # the set kids_checks.py reads
                Ln_ = lab[..., 0] + w * (Lof(y_) - lab[..., 0])
                an_ = lab[..., 1] + w * (tgt[1] * f_ - med[1])
                bn_ = lab[..., 2] + w * (tgt[2] * f_ - med[2])
                med_n = np.median(np.stack([Ln_[mk_], an_[mk_], bn_[mk_]], -1), 0)
                hh_, ll_, ss_ = colorsys.rgb_to_hls(*np.clip(C.from_lab(med_n[None, None])[0, 0], 0, 1))
                if ss_ * 100 <= 39.5:
                    break
                f_ *= 0.96
            tgt = (tgt[0], tgt[1] * f_, tgt[2] * f_)
            rec.setdefault("v3_pink_chroma_eased", round(float(f_), 3))
        lab_n = lab.copy()
        y = Y(lab[..., 0]) * (Y(np.array(Lp)) / Y(np.array(L1p)))
        lab_n[..., 0] = lab[..., 0] + w * (Lof(y) - lab[..., 0])
        lab_n[..., 1] = lab[..., 1] + w * (tgt[1] - med[1])
        lab_n[..., 2] = lab[..., 2] + w * (tgt[2] - med[2])
        rgb = KC.floor_lab(np.clip(C.from_lab(lab_n), 0, 1), a > 0)
        out = np.dstack([C.q(rgb), C.q(a)])
        out[..., :3][out[..., 3] == 0] = 0
        lp = os.path.join(st, "layers", v1["slot"], pid + ".png")
        Image.fromarray(out, "RGBA").save(lp, optimize=True)
        mn = np.median(C.to_lab(rgb)[core], 0)
        man["layers"] = [l for l in man["layers"] if not (l["product"] == pid and not l.get("default", True))]
        entry = dict(v1, product=pid, default=False, variant=vn, layer=os.path.relpath(lp, st), sku=VARIANT_SKU[pk],
                     source=f"code variant of V1 (tools/kids_variants.py): colour only, the photo's Lab of {pk}", pass_="variants")
        entry.pop("passes", None)
        man["layers"].append(entry)
        rec["variants"][vn] = dict(product=pid, sku=VARIANT_SKU[pk], photo_LCh=[Lp, Cp, hp], rendered_Lab=[round(float(v), 1) for v in mn],
                                   rendered_LCh=[round(v, 1) for v in K.lch(mn)])
    man.setdefault("code_fixes", {})["sample slot variants"] = rec
    KC.save_man(kid, man)
    for vn in ("V2", "V3"):
        e = [l for l in man["layers"] if l.get("variant") == vn and l["key"] == "bedspread"][0]
        o8, r = KC.compose(kid, f"K-{kid}-{vn}", swap={e["slot"]: e})
        rec["variants"][vn]["frame"] = r
    man = KC.load_man(kid)
    man["code_fixes"]["sample slot variants"] = rec
    KC.save_man(kid, man)
    print(json.dumps(rec, indent=1)[:2500])


if __name__ == "__main__":
    main(sys.argv[1])
