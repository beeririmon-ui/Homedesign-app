#!/usr/bin/env python3
"""
girl_plate.py: the K-girl empty plate, derived from the K-boy plate by code (ב.6 1א: "the boy's plate, the band recoloured to #E8D5CC in
code, in the band mask, including the L*; QA checks dE to the target and the light the band throws on the bed and the floor"),
render-agent, 2026-11-24; 0 tokens.
The two rooms are the same shell, camera and light (+3.63 in Y). Two clays were rendered with everything identical except the band's
albedo (K-boy-plate #A8A88E, K-girl-plate #E8D5CC): their ratio, in linear light, is what the change of band does to every other surface
(the bounce on the mattress, the floor, the walnut and the plaster near the corner). So:
  - off the band: girl = boy plate x the clays' ratio, smoothed (normalised convolution, sigma 10 px, the band itself excluded; the
    ratio is clamped 0.85-1.25 and set to 1 where the clays differ by less than 0.5 %);
  - on the band (ids 5, 8, 19): the boy plate's band, per channel in linear light, x (#E8D5CC / the boy band's implied albedo), where the
    implied albedo is the band over the plaster just above the line x #ECE5DA (compose_plate_kids.band_reading): the girl's band gets
    #E8D5CC against her plaster whatever the model did to the olive, and keeps its trowel texture;
  - the frame's black point is then read again (WM-G1).
  python3 girl_plate.py            (reads ../plate.png of the boy and the clay EXRs in the scratchpad)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
import compose_plate_kids as CP  # noqa: E402

C = K.C
H, W = K.H, K.W
EXR = os.path.join(K.SCR, "clay", "exr")


def load_exr(path):
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Linear Rec.709"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)


def main():
    boy = C.load(os.path.join(K.ST["boy"], "plate.png"))
    ids = K.ids("K-boy-plate")
    idg = K.ids("K-girl-plate")
    same_ids = float((ids == idg).mean())
    rb, rg = load_exr(os.path.join(EXR, "K-boy-plate.exr")), load_exr(os.path.join(EXR, "K-girl-plate.exr"))
    band = np.isin(ids, K.BAND)
    ratio = rg / np.maximum(rb, 1e-5)
    ratio = np.where(np.abs(ratio - 1) < 0.005, 1.0, ratio)
    ratio = np.clip(ratio, 0.85, 1.25)
    w = (~C.dil(band, 2) & (ids != 0) & (ids != 15)).astype(np.float64)
    rs = np.stack([C.blur(ratio[..., c] * w, 10) / np.maximum(C.blur(w, 10), 1e-4) for c in range(3)], -1)
    rs = np.where((C.blur(w, 10) > 0.05)[..., None], rs, 1.0)
    lin = C.lin(boy)
    # K-G1 / K-G2 (QA 2026-11-24): the band is no longer the boy's band times a constant (that clipped to white where the boy's band is
    # lit, and kept the olive's green in its shade and in the strips the clay's ids do not cover). Instead:
    #  1. the mask by what is drawn: the clay's band ids, plus the olive the boy's plate shows below the 1.25 line round them and in
    #     the furniture's clay regions (the legs, the chair and the foot board were drawn thinner than the clay), minus drawn walnut;
    #  2. the paint: #E8D5CC times a light, the light being the boy's band luminance (its trowel texture, its shade) scaled per column
    #     so that, just under the line, the band against the girl's plaster just over it is #E8D5CC against #ECE5DA (the implied
    #     albedo is the target in every column); one chromaticity, so the shade is the lit pink, darker, not khaki;
    #  3. a soft shoulder: never brighter than the plaster over it in its column (x 1.03), and no channel over 0.90 linear.
    lab_b = C.to_lab(C.blur(boy, 1.0))
    hue = np.degrees(np.arctan2(lab_b[..., 2], lab_b[..., 1]))
    chroma = np.hypot(lab_b[..., 1], lab_b[..., 2])
    yy = np.arange(H)[:, None]
    bid = np.isin(ids, (5, 8))
    line = np.where(bid.any(0), np.argmax(bid, 0), -1).astype(np.float64)
    okc = line > 0
    xs_ = np.arange(W)
    line = np.interp(xs_, xs_[okc], line[okc])
    below = yy >= (line[None, :] - 2)
    oliv = (hue > 85) & (hue < 140) & (chroma > 5) & (lab_b[..., 0] > 8)
    walnut = (hue > 35) & (hue < 78) & (chroma > 7) & (lab_b[..., 0] < 50)
    cand = (C.dil(np.isin(ids, (5, 8, 19)), 30) | np.isin(ids, (12, 14, 20, 23, 24, 25))) & ~np.isin(ids, (0, 13, 15, 16, 21, 22))
    band = (np.isin(ids, (5, 8, 19)) & ~walnut) | (cand & below & oliv)
    band = cv2.morphologyEx(band.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(1)).astype(bool) & ~np.isin(ids, (0, 13, 15, 16))
    out = lin * np.where(band[..., None], 1.0, rs)              # off the band: the boy's plate x the band's bounce
    lum = lambda v: v[..., 0] * 0.2126 + v[..., 1] * 0.7152 + v[..., 2] * 0.0722   # noqa: E731
    Yb = lum(lin)
    Yg = lum(out)
    alb_girl = C.lin(np.array([0xE8, 0xD5, 0xCC]) / 255.0)
    Ypl = float(lum(C.lin(np.array([0xEC, 0xE5, 0xDA]) / 255.0)))
    east = xs_[None, :] >= np.argmax(np.isin(ids, (5,)).any(0))
    wall_of = np.where(east, 1, 0) * np.ones((H, 1))
    Fmap = np.zeros((H, W, 3))                             # per channel: the light's own colour, read on the plaster over the line
    Smax = np.zeros((H, W, 3))
    pl_lin = C.lin(np.array([0xEC, 0xE5, 0xDA]) / 255.0)
    ks = {}
    for wi, (wall, wd) in enumerate((("north", CP.WALLS["north"]), ("east", CP.WALLS["east"]))):
        F = np.full((W, 3), np.nan)
        P = np.full((W, 3), np.nan)
        for x in range(W):
            col = ids[:, x]
            yb = np.nonzero(col == wd["band"])[0]
            yp = np.nonzero(col == wd["plaster"])[0]
            if len(yb) < 30 or len(yp) < 30 or abs(yp.max() - yb.min()) > 3:
                continue
            yl = yb.min()
            pg = np.median(out[yl - 26:yl - 6, x], 0)
            bt = float(np.median(Yb[yl + 6:yl + 26, x]))
            if bt > 1e-4:
                F[x] = (pg / pl_lin) / bt
                P[x] = pg / pl_lin
        ok = np.isfinite(F[:, 0])
        if ok.sum() < 10:
            continue
        xo = np.nonzero(ok)[0]
        sel = (wall_of == wi)[..., None]
        for c in range(3):
            Fm = np.array([np.median(F[xo, c][max(0, i - 4):i + 5]) for i in range(len(xo))])
            Pm = np.array([np.median(P[xo, c][max(0, i - 4):i + 5]) for i in range(len(xo))])
            Fx = cv2.GaussianBlur(np.interp(xs_, xo, Fm).astype(np.float32).reshape(1, -1), (0, 0), 7).ravel()     # no column streaks
            Px = cv2.GaussianBlur(np.interp(xs_, xo, Pm).astype(np.float32).reshape(1, -1), (0, 0), 7).ravel()
            Fmap[..., c] = np.where(sel[..., 0], Fx[None, :], Fmap[..., c])
            Smax[..., c] = np.where(sel[..., 0], Px[None, :], Smax[..., c])
        ks[wall] = dict(columns=int(ok.sum()), F_p5_p50_p95=[round(float(v), 4) for v in np.percentile(F[ok, 1], [5, 50, 95])])
    light = Fmap * Yb[..., None]
    knee, cap = Smax * 1.0, Smax * 1.06                     # above the plaster's own level in the column only, softly
    light = np.where(light > knee, knee + (cap - knee) * np.tanh((light - knee) / np.maximum(cap - knee, 1e-6)), light)
    paint = alb_girl[None, None, :] * light
    k_, c_ = 0.86, 0.915                                   # 0.915 linear = sRGB 245
    paint = np.where(paint > k_, k_ + (c_ - k_) * np.tanh((paint - k_) / (c_ - k_)), paint)
    soft = C.blur(band.astype(np.float64), 0.7)
    soft = np.where(band, 1.0, np.where(C.dil(band, 1), soft, 0.0))[..., None]     # the whole band painted; a 1 px ring outside it blends
    out = out * (1 - soft) + paint * soft
    k = dict(ks, method="per column: (girl plaster over the line / #ECE5DA) / (boy band under the line), times the boy band's luminance, "
                        "times #E8D5CC; soft shoulder from the plaster's level to x 1.06, and from 0.86 to 0.915 linear", band_px=int(band.sum()),
             band_by_colour_outside_ids=int((band & ~np.isin(ids, (5, 8, 19))).sum()))
    rgb = C.srgb(np.clip(out, 0, 1))
    labk = C.to_lab(rgb)
    k["skirting"] = CP.skirting_fix(labk, ids, "#E8D5CC")
    # K-G2 (QA 2026-11-24; its metric: no h 95-135 C* > 6 below the line): the corner lines of the reveal (id 12) and the skirting
    # (19) below the line kept the boy's olive (h 80-140, C* > 4); their a*, b* set to the reveal's own neutral below the line (the
    # median of its other pixels), scaled with L* (C*/L* kept), L* kept
    ytop = int(np.nonzero(np.isin(ids, (5, 8)).any(1))[0].min())
    below = np.zeros(ids.shape, bool)
    below[ytop:] = True
    hk = np.degrees(np.arctan2(labk[..., 2], labk[..., 1])) % 360
    ck = np.hypot(labk[..., 1], labk[..., 2])
    olive = below & np.isin(ids, (12, 19)) & (hk > 80) & (hk < 140) & (ck > 4)
    ref = below & (ids == 12) & ~olive
    if olive.any() and ref.sum() > 100:
        rL, ra, rb = (float(np.median(labk[..., c][ref])) for c in range(3))
        f = labk[..., 0][olive] / max(rL, 1)
        labk[..., 1][olive] = ra * f
        labk[..., 2][olive] = rb * f
    k["reveal_corner_olive"] = dict(px=int(olive.sum()), reference_Lab=[round(rL, 1), round(ra, 2), round(rb, 2)] if olive.any() and ref.sum() > 100 else None)
    rgb = np.clip(C.from_lab(labk), 0, 1)
    st = K.ST["girl"]
    K.save(os.path.join(st, "plate.png"), rgb)
    K.save_frame(rgb, os.path.join(st, "plate-frame.png"))
    lab = C.to_lab(rgb)
    fr = K.frame_mask()
    upper = C.ero(np.isin(ids, (1, 2)), 4) & fr
    labb = C.to_lab(boy)
    rec = dict(source="../../../boy/warm-modern/stage1-2026-11-24/plate.png (the boy's composed plate)", ids_identical_frac=round(same_ids, 5),
               method=__doc__.split("So:")[1].strip(), k_per_channel_per_wall=k,
               bounce=dict((nm, [round(float(v), 4) for v in np.median(rs[C.ero(np.isin(ids, g), 3) & fr], 0)]) for nm, g in
                           (("mattress", (22,)), ("floor", (10,)), ("walnut", (20, 21)), ("plaster above the band", (1, 2)))),
               
               plaster_above_band=dict(boy=[round(float(v), 1) for v in np.median(labb[upper], 0)], girl=[round(float(v), 1) for v in np.median(lab[upper], 0)],
                                       rule="ב.1: the wall above the band stays bone (H 32-40); no pink bleeds up"),
               black_point_p05=round(float(np.percentile(lab[..., 0][fr], 0.5)), 2))
    # the checks (the manager's 2026-11-24 list): WM-G1, one house against the boy and MB0, the band against #E8D5CC on both walls
    rows = {}
    ids0 = np.asarray(Image.open(CP.MB0_IDS))
    l0 = C.to_lab(C.load(CP.MB0))
    for name, (gg, g0) in CP.SURF.items():
        a_, _ = CP.rd(lab, ids, gg)
        b_, _ = CP.rd(labb, ids, gg)
        m0, _ = CP.rd(l0, ids0, g0)
        if a_ is None or m0 is None:
            continue
        La, _, _ = K.lch(a_)
        L0, C0, h0 = K.lch(K.lab_hex(CP.SPEC_HEX[name]) if name in CP.SPEC_HEX else m0)
        t_ = K.from_lch(La, C0 / max(L0, 1e-3) * La, h0)
        rows[name] = dict(girl=[round(float(v), 1) for v in a_], boy=[round(float(v), 1) for v in b_], dE00_vs_boy=round(float(C.de00(tuple(a_), tuple(b_))), 2),
                          dE00_material_vs_MB0=round(float(C.de00(tuple(a_), tuple(t_))), 2))
    rec["one_house"] = dict(rule="per surface: the girl's plate against the boy's, and the material (hue, C*/L* at its own L*) against MB0 as "
                                 "compose_plate_kids.py; off the band only the band's bounce differs", surfaces=rows)
    rec["band_girl"] = {w: CP.band_reading(rgb, ids, w, "#E8D5CC") for w in CP.WALLS}
    rec["band_boy"] = {w: CP.band_reading(boy, ids, w) for w in CP.WALLS}
    import colorsys
    hh, ll, ss = colorsys.rgb_to_hls(*np.median(rgb[upper], 0))
    rec["plaster_above_band"]["girl_HSL"] = [round(hh * 360, 1), round(ss * 100, 1), round(ll * 100, 1)]
    rec["WM_G1"] = dict(black_point_p05=rec["black_point_p05"], range=[11, 14], ok=bool(11 <= rec["black_point_p05"] <= 14))
    # K-G1 / K-G2 acceptance (QA 2026-11-24), on the plate
    r8 = np.rint(rgb * 255)
    hb = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    cb = np.hypot(lab[..., 1], lab[..., 2])
    bandf = band & fr
    cols = []
    pl = C.lin(np.array([0xEC, 0xE5, 0xDA]) / 255.0)
    for wall, wd in CP.WALLS.items():
        for x in range(*wd["xr"]):
            col = ids[:, x]
            yb = np.nonzero(col == wd["band"])[0]
            yp = np.nonzero(col == wd["plaster"])[0]
            if len(yb) < 30 or len(yp) < 30 or abs(yp.max() - yb.min()) > 3:
                continue
            yl = yb.min()
            bl, al = C.lin(rgb)[yl + 6:yl + 26, x].mean(0), C.lin(rgb)[yl - 26:yl - 6, x].mean(0)
            alb = np.clip(bl / al * pl, 0, 1)
            lab_a = C.to_lab(C.srgb(alb)[None, None])[0, 0]
            cols.append((float(C.de00(tuple(lab_a), tuple(K.lab_hex("#E8D5CC")))), float(lab[yl + 6:yl + 26, x, 0].mean() < lab[yl - 26:yl - 6, x, 0].mean())))
    cols = np.array(cols)
    lit = bandf & (lab[..., 0] > 55)
    dark = bandf & (lab[..., 0] < 50)
    hl, hd_ = float(np.median(hb[lit])), float(np.median(hb[dark])) if dark.any() else float("nan")
    up_l = C.ero(np.isin(ids, (1, 2)), 4) & fr
    rec["K-G1_K-G2"] = dict(
        band_px=int(bandf.sum()), band_px_all_three_over_245=int((bandf & (r8 > 245).all(-1)).sum()),
        band_px_any_over_252=int((bandf & (r8 > 252).any(-1)).sum()),
        implied_albedo_per_column_dE00_p5_p50_p95=[round(float(v), 2) for v in np.percentile(cols[:, 0], [5, 50, 95])], columns=len(cols),
        band_darker_than_plaster_columns_frac=round(float(cols[:, 1].mean()), 4),
        band_L_p99=round(float(np.percentile(lab[..., 0][bandf], 99)), 1), plaster_L_p99=round(float(np.percentile(lab[..., 0][up_l], 99)), 1),
        hue_lit_vs_shade=[round(hl, 1), round(hd_, 1)], band_px_hue_70_110=int((bandf & (hb > 70) & (hb < 110)).sum()),
        band_px_hue_70_110_C_over_3=int((bandf & (hb > 70) & (hb < 110) & (cb > 3)).sum()))
    json.dump(rec, open(os.path.join(st, "plate-compose.json"), "w"), indent=1)
    print(json.dumps(rec, indent=1)[:3000])


if __name__ == "__main__":
    main()
