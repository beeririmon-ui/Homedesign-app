#!/usr/bin/env python3
"""
throw_variants.py: the two throw variants in code (12.8, 1b; render-agent, 2026-11-18; 0 tokens). The same muslin in another dye: in
linear light every channel of the Pecan layer is multiplied by one ratio per channel, measured the R5 way on the SKU photos (the
fabric's mid-tones, 25-75 % of L*; scratchpad comp/throw-ratios.json, photos not in the repo). The photos' exposures differ (Pecan's
fabric reads L* 26, Flax 52, Clay 19), so the ratio is set through a target for the layer's mid-tone: L* = Pecan's in the frame plus
the difference of (fabric - the photo's white) between the two photos; a* b* = the new photo's fabric (its hue and C*). The ratio is
lin(target) / lin(Pecan's mid-tone in the frame).
The alpha, the folds, the fringes and the shadow are Pecan's, byte for byte. Each variant frame is recomposed from the layer files.
  python3 throw_variants.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402

RATIOS = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master/comp/throw-ratios.json"
VARIANTS = {"flax": dict(pid="sofa-cover-cj-cotton-muslin-fringe-flax-brown-150x200", sku="CJYD205807538LO"),
            "clay": dict(pid="sofa-cover-cj-cotton-muslin-fringe-clay-150x200", sku="CJYD205807510JQ")}


def recompose(man, swap=None):
    out = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB")).astype(np.float64) / 255
    for l in man["layers"]:
        lp = swap if (swap and l["slot"] == "throw") else os.path.join(ST, l["layer"])
        rgba = np.asarray(Image.open(lp))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
    for li in man["light"]:
        out = C.light_one(out, np.asarray(Image.open(os.path.join(ST, li["file"]))))
    return out


def hc(lab):
    return float(np.degrees(np.arctan2(lab[2], lab[1])) % 360), float(np.hypot(lab[1], lab[2]))


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    rt = json.load(open(RATIOS))
    tl = [l for l in man["layers"] if l["slot"] == "throw"][0]
    rgba = np.asarray(Image.open(os.path.join(ST, tl["layer"])))
    a = rgba[..., 3]
    rgb = rgba[..., :3].astype(np.float64) / 255
    inner = C.ero(a == 255, 3)
    lab_p = C.to_lab(rgb[inner])
    sel = (lab_p[:, 0] > np.percentile(lab_p[:, 0], 25)) & (lab_p[:, 0] < np.percentile(lab_p[:, 0], 75))
    duvet = C.to_lab(np.asarray(Image.open(os.path.join(ST, "mb0-defaults.png")))[1150:1300, 1300:1900].reshape(-1, 3).astype(float) / 255)
    duv = np.median(duvet, 0)
    head = np.median(C.to_lab(np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))[680:740, 1000:1700].reshape(-1, 3).astype(float) / 255), 0)
    rec = dict(method=__doc__.strip().splitlines()[1], pecan_mid_Lab=np.median(lab_p[sel], 0).round(1).tolist(), variants={})
    man["variants"] = [dict(slot="throw", product=tl["product"], default=True, layer=tl["layer"], shadow=tl["shadow"])]
    for k, v in VARIANTS.items():
        pm = np.median(lab_p[sel], 0)
        dl = (rt[k]["fab_lab"][0] - rt[k]["white_lab"][0]) - (rt["pecan"]["fab_lab"][0] - rt["pecan"]["white_lab"][0])
        tgt = np.array([pm[0] + dl, rt[k]["fab_lab"][1], rt[k]["fab_lab"][2]])
        r = C.lin(C.from_lab(tgt[None, None])[0, 0]) / np.maximum(C.lin(C.from_lab(pm[None, None])[0, 0]), 1e-6)
        new = C.srgb(np.clip(C.lin(rgb) * r, 0, 1))
        out = np.dstack([C.q(new), a])
        out[..., :3][a == 0] = 0
        lp = os.path.join(ST, "layers", "throw", v["pid"] + ".png")
        Image.fromarray(out, "RGBA").save(lp)
        sp = os.path.join(ST, "shadows", "throw", v["pid"] + ".png")
        Image.fromarray(np.asarray(Image.open(os.path.join(ST, tl["shadow"])))).save(sp)
        fr = recompose(man, lp)
        o8 = C.q(fr)
        Image.fromarray(o8).save(os.path.join(ST, f"mb0-variant-throw-{k}.png"))
        x0, y0, x1, y1 = (int(round(t)) for t in C.FRAME)
        Image.fromarray(o8).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, f"mb0-variant-throw-{k}-frame.png"))
        lab_v = C.to_lab(new[inner])
        mid = np.median(lab_v[sel], 0)
        h_v, c_v = hc(mid)
        h_s, c_s = hc(rt[k]["fab_lab"])
        diff = np.abs(o8.astype(int) - C.q(recompose(man)).astype(int)).max(2) > 0
        rec["variants"][k] = dict(product=v["pid"], sku=v["sku"], ratio_lin_rgb=r.round(3).tolist(), target_mid_Lab=tgt.round(1).tolist(), dL_vs_pecan_from_photos=round(float(dl), 1), mid_Lab=mid.round(1).tolist(),
                                  hue_deg=round(h_v, 1), C=round(c_v, 1), sku_hue_deg=round(h_s, 1), sku_C=round(c_s, 1),
                                  d_hue=round(h_v - h_s, 1), d_C=round(c_v - c_s, 1), dE00_vs_duvet=round(C.de00(mid, duv), 1),
                                  dE00_vs_headboard=round(C.de00(mid, head), 1), alpha_identical=True,
                                  changed_px_outside_throw_alpha=int((diff & (a == 0)).sum()))
        man["variants"].append(dict(slot="throw", product=v["pid"], default=False, layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sp, ST),
                                    alpha="identical to the default's", frame=f"mb0-variant-throw-{k}.png"))
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    json.dump(rec, open(os.path.join(ST, "mb0-throw-variants.json"), "w"), indent=1)
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
