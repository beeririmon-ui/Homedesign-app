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
    out = lin * np.where(band[..., None], 1.0, rs)
    alb_girl = C.lin(np.array([0xE8, 0xD5, 0xCC]) / 255.0)
    ks = {}
    for wall, wd in CP.WALLS.items():              # each wall's band from its own reading (the north wall is in its own light)
        br = CP.band_reading(boy, ids, wall)
        alb_boy = C.lin(np.array(br["implied_albedo_srgb"]) / 255.0)
        k = alb_girl / np.maximum(alb_boy, 1e-4)
        ks[wall] = [round(float(v), 4) for v in k]
        bw = np.isin(ids, wd["ids"])
        soft = C.blur(bw.astype(np.float64), 0.8)
        soft = np.where(C.ero(bw, 1), 1.0, np.where(C.dil(bw, 1), soft, 0.0))
        out = out * (1 + (k - 1) * soft[..., None])
    k = ks
    # the plaster above each band takes the band's new bounce, the band does not (the clays' ratio on the band is its albedo change): one
    # more pass per wall, the band against the plaster above it on the girl's own plate, to #E8D5CC
    for wall, wd in CP.WALLS.items():
        br2 = CP.band_reading(C.srgb(np.clip(out, 0, 1)), ids, wall, "#E8D5CC")
        if br2 and br2["dE00"] > 1.0:
            k2 = alb_girl / np.maximum(C.lin(np.array(br2["implied_albedo_srgb"]) / 255.0), 1e-4)
            bw = np.isin(ids, wd["ids"])
            soft = C.blur(bw.astype(np.float64), 0.8)
            soft = np.where(C.ero(bw, 1), 1.0, np.where(C.dil(bw, 1), soft, 0.0))
            out = out * (1 + (k2 - 1) * soft[..., None])
            ks[wall + "_second_pass"] = [round(float(v), 4) for v in k2]
    rgb = C.srgb(np.clip(out, 0, 1))
    labk = C.to_lab(rgb)
    ks["skirting"] = CP.skirting_fix(labk, ids, "#E8D5CC")
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
    json.dump(rec, open(os.path.join(st, "plate-compose.json"), "w"), indent=1)
    print(json.dumps(rec, indent=1)[:3000])


if __name__ == "__main__":
    main()
