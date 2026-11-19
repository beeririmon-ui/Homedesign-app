#!/usr/bin/env python3
"""
variant_b1_mat.py: the sample slot's variant 2, the bath mat in Return Frame Beige (CJYD289719801AZ), in code (0 tokens), render-agent,
2026-11-19. Khaki (the default) and Beige are one card, one weave and one frame design: only the colour changes, and the two SKU
photographs are one studio set shot once per colour (house-20 photo check: same tub, same tray). So the Beige is the Khaki layer
recoloured by the photographs' own ratio, per channel, in linear light, in the same space as the Khaki's R5 recolour (after the
grade): beige = khaki x lin(Beige photo) / lin(Khaki photo), the photos read by the photo check on the same floor crop
(Khaki 77.6 / 4.2 / 13.6, Beige 87.5 / 0.0 / 6.6). The Khaki layer already reads the Khaki photo (R5 in compose_b1_defaults.py), so
the Beige reads the Beige photo. The alpha and the shadow are the default's, byte for byte (the geometry is one).
Then the composite is recomposed from the files (RND2) and the two mats are read again with the same R5 reading.

  python3 variant_b1_mat.py
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
B2T = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools"
sys.path.insert(0, B2T)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402
import compose_b1_defaults as D  # noqa: E402

KHAKI, BEIGE = D.MAT_KHAKI, D.MAT_BEIGE
PID = "bath-mat-cj-tufted-cotton-frame-beige-40x60-beige"
PHOTO_KHAKI_P05_P95 = (58.3, 85.9)                  # house-20 photo check, mat-khaki L_p05 / L_p95
PHOTO_BEIGE_P05_P95 = (78.9, 91.4)                  # mat-beige


def main():
    man_p = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(man_p))
    lay = {l["slot"]: l for l in man["layers"]}
    l = lay["bath-mat"]
    rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
    s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
    a = rgba[..., 3]
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    rgb = rgba[..., :3].astype(np.float64) / 255
    ratio = C.lin(G.from_lab(np.array([BEIGE]))[0]) / C.lin(G.from_lab(np.array([KHAKI]))[0])
    # the pile's own contrast: in the two SKU photos (one set, one exposure: background L* 62.0 / 62.6) the light Beige shows far
    # less shading in its pile than the Khaki (light fibres fill their own crevices). Its p05-p95 spread in log luminance is 0.39
    # of the Khaki's, so the Khaki layer's detail (its luminance over its own large-scale light, sigma 30 px) is raised to 0.39;
    # without it the Beige's tuft highlights clip to white (about 10,000 px) where the photo's p95 is L* 91.4
    sp = lambda l05, l95: np.log(((l95 + 16) / 116) ** 3 / ((l05 + 16) / 116) ** 3)  # noqa: E731
    gam = float(sp(*PHOTO_BEIGE_P05_P95) / sp(*PHOTO_KHAKI_P05_P95))
    lr = C.lin(rgb)
    w = C.ero(a > 127, 8).astype(np.float64)
    nw = np.maximum(C.blur(w, 30.0), 1e-6)
    low = np.stack([C.blur(lr[..., i] * w, 30.0) / nw for i in range(3)], -1)
    Yw = np.array([0.2126, 0.7152, 0.0722])
    det = np.clip((lr @ Yw) / np.maximum(low @ Yw, 1e-6), 0.02, 50)
    base_b = low * ratio * (det ** gam)[..., None]
    pl = plate8.astype(np.float64) / 255
    ids = np.asarray(Image.open(D.CLAY + "B1-id.png"))
    kb = np.ones(3)
    for _ in range(4):                                  # then R5, a uniform per-channel gain, to the Beige photo's reading
        cur = C.srgb(np.clip(base_b * kb, 0, 1))
        lab, _ = D.mat_reading(cur, a, pl, ids)
        kb = kb * C.lin(G.from_lab(np.array([BEIGE]))[0]) / C.lin(G.from_lab(np.array([lab]))[0])
    lin_new = base_b * kb
    clipped = int((lin_new.max(-1)[a > 0] > 1).sum())
    new = C.srgb(np.clip(lin_new, 0, 1))
    out = rgba.copy()
    out[..., :3] = np.where((a > 0)[..., None], C.q(new), 0)
    lp = os.path.join("layers", "bath-mat", PID + ".png")
    sp = os.path.join("shadows", "bath-mat", PID + ".png")
    Image.fromarray(out, "RGBA").save(os.path.join(ST, lp))
    shutil.copyfile(os.path.join(ST, l["shadow"]), os.path.join(ST, sp))
    order = [x["slot"] for x in sorted(man["layers"], key=lambda x: (x["z"], x["slot"]))]
    files = {x["slot"]: (np.asarray(Image.open(os.path.join(ST, x["layer"]))), np.asarray(Image.open(os.path.join(ST, x["shadow"])))) for x in man["layers"]}
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    dflt = np.asarray(Image.open(os.path.join(ST, "b1-defaults.png")).convert("RGB"))
    files["bath-mat"] = (out, s8)
    o8 = C.q(D.stack(plate8, files, order, L8))
    Image.fromarray(o8).save(os.path.join(ST, "b1-variant-mat-beige.png"))
    C.frame_png(o8, os.path.join(ST, "b1-variant-mat-beige-frame.png"))
    region = L8.max(2) > 0
    for k in order:
        region |= (files[k][0][..., 3] > 0) | (files[k][1] < 255)
    rnd2 = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    diff_out = int(((np.abs(o8.astype(int) - dflt.astype(int)).max(2) > 0) & (a == 0)).sum())
    pg = plate8.astype(np.float64) / 255
    rk, nring = D.mat_reading(dflt.astype(np.float64) / 255, a, pg, ids)
    rb, _ = D.mat_reading(o8.astype(np.float64) / 255, a, pg, ids)
    rk, rb = [round(float(x), 1) for x in rk], [round(float(x), 1) for x in rb]
    de = lambda x, y: round(float(G.de00(np.array([x]), np.array([y]))[0]), 2)  # noqa: E731
    v = dict(slot="bath-mat", product=PID, card=l["card"], sku="CJYD289719801AZ", z=l["z"], default=False,
             method="colour-only, in code: the Khaki layer's large-scale colour x the two SKU photographs' ratio (linear, per channel, after the grade), its pile detail at the Beige photo's lower contrast (gamma), then R5 to the Beige photo; alpha and shadow the default's",
             ratio_linear=[round(float(x), 4) for x in ratio], clipped_px=clipped, pile_detail_gamma=round(gam, 3),
             r5_gain_after=[round(float(x), 4) for x in kb],
             layer=lp, shadow=sp, composite="b1-variant-mat-beige.png", alpha_identical_to_default=True, shadow_identical_to_default=True,
             outside_differing_px_vs_plate=rnd2, differing_px_vs_defaults_outside_alpha=diff_out,
             readings_vs_floor=dict(reference=f"R5 on the floor (compose_b1_defaults.mat_reading): intensity from the plate floor ring 10-40 px over the stone {D.STONE} luminance, light colour from the plaster beside it", ring_px=nring,
                                    khaki=rk, khaki_photo=list(KHAKI), de00_khaki=de(rk, KHAKI), beige=rb, beige_photo=list(BEIGE), de00_beige=de(rb, BEIGE)))
    man["variants"] = [x for x in man.get("variants", []) if x["product"] != PID] + [v]
    man["variants_note"] = ("the sample slot has 2 variants (house-20 8.1): Khaki and Beige. The third (row 14, 8.6) is open: no other mat card "
                            "has passed a photo check (Line Camel failed), so none is rendered")
    json.dump(man, open(man_p, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(v["readings_vs_floor"]), rnd2, diff_out)


if __name__ == "__main__":
    main()
