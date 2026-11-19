#!/usr/bin/env python3
"""
mb1_tone_fix.py: product-colour fixes on MB1's layers in code (render-agent, 2026-11-19; 0 tokens), only where MB1 read off the product
against MB0 / the SKU (mb1_checks.py), and only in the product's own pixels (each layer's alpha; nothing else changes):
  - the planter's pot (Beige Large; MB0's pot is the 13.11 / R5 one): its lit tone (L* p60-p90 of its own pixels, no soil, no plant)
    and chroma set to MB0's pot's, read the same way; in linear light, the texture kept. The ficus is not touched. (R5 against the
    plaster ring is reported by mb1_checks.py; in MB1 the ring is lit by the floor lamp's glow, so it is a reading, not the target);
  - the patina pitcher: the model drew it grey-blue (C* 3.5, h -15 off MB0's); a* b* moved to MB0's lit tone (2.4, 11.0), L* kept;
  - the travertine candle holders: grey (C* 5) against MB0's warm travertine (2.4, 11.7): a* b* moved the same way, L* kept.
  - the rug: to the living room's rug (the same listing and photo) relative to the oak beside it, and its chroma.
Run after the passes and the prints, then mb1_compose.py compose.
  python3 mb1_tone_fix.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402
import mb1_checks as K  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
AB_TO_MB0 = {"bedside-carafe": (2.4, 11.0), "candle-holders": (2.4, 11.7)}


def Y_of(L):
    return np.where(L > 8, ((L + 16) / 116) ** 3, L / 903.3)


def L_of(Y):
    return np.where(Y > 216 / 24389, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def load_layer(man, slot):
    l = [x for x in man["layers"] if x["slot"] == slot][0]
    p = os.path.join(ST, l["layer"])
    return p, np.asarray(Image.open(p)).astype(np.float64) / 255


def save_layer(p, rgb, a):
    rgba = np.dstack([C.q(rgb), C.q(a)])
    rgba[..., :3][rgba[..., 3] == 0] = 0
    Image.fromarray(rgba, "RGBA").save(p)


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    comp = C.to_lab(C.load(os.path.join(ST, "mb1-defaults.png")))
    rec = {}
    # the pot: its lit tone (L* p60-p90 of the pot's own pixels, not the soil, not the plant) to MB0's pot's, read the same way
    # (the same SKU in the same room light; MB0's pot is the 13.11 / R5 one); in linear light, the texture kept
    p, im = load_layer(man, "planter")
    rgb, a = im[..., :3], im[..., 3]
    lab = C.to_lab(rgb)
    def pot_mask(lab, a, rows):
        hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
        ch = np.hypot(lab[..., 1], lab[..., 2])
        m = (a > 0.99) & ~((hh > 85) & (ch > 4)) & (lab[..., 0] > 32)
        rr = np.zeros(a.shape, bool)
        rr[rows[0]:rows[1]] = True
        return m & rr
    l0 = [x for x in json.load(open(os.path.join(M.MB0, "layers", "manifest.json")))["layers"] if x["slot"] == "planter"][0]
    im0 = np.asarray(Image.open(os.path.join(M.MB0, l0["layer"]))).astype(np.float64) / 255
    lab0 = C.to_lab(im0[..., :3])
    m0 = pot_mask(lab0, im0[..., 3], (1075, 1296))
    m1 = pot_mask(lab, a, (1060, 1330))
    t0, c1 = K.lit_lab(lab0, m0), K.lit_lab(lab, m1)
    g = float(Y_of(np.array(t0[0])) / Y_of(np.array(c1[0])))
    kc = float(np.hypot(t0[1], t0[2]) / max(np.hypot(c1[1], c1[2]), 1e-3))
    hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    ch = np.hypot(lab[..., 1], lab[..., 2])
    rows = np.zeros((H, W), bool)
    rows[1040:1340] = True
    pot = (a > 0) & rows & ~((hh > 85) & (ch > 4)) & ~((ch < 5) & (lab[..., 0] > 60) & (np.arange(H)[:, None] < 1075))
    w = C.blur(pot.astype(np.float64), 1.0) * (a > 0)
    lab2 = lab.copy()
    lab2[..., 0] = L_of(Y_of(lab[..., 0]) * (1 + (g - 1) * w))
    lab2[..., 1] = lab[..., 1] * (1 + (kc - 1) * w)
    lab2[..., 2] = lab[..., 2] * (1 + (kc - 1) * w)
    save_layer(p, np.clip(C.from_lab(lab2), 0, 1), a)
    rec["planter"] = dict(rule="the pot's lit tone (L* p60-p90, pot pixels) to MB0's pot's (the 13.11 / R5 pot), read the same way",
                          mb0_pot_lit=[round(float(v), 1) for v in t0], mb1_pot_lit_before=[round(float(v), 1) for v in c1],
                          luminance_gain=round(g, 3), chroma_scale=round(kc, 3))
    # pitcher, candle holders: a* b* to MB0's
    for slot, (ta, tb) in AB_TO_MB0.items():
        p, im = load_layer(man, slot)
        rgb, a = im[..., :3], im[..., 3]
        lab = C.to_lab(rgb)
        m = a > 0.99
        cur = np.median(lab[m], 0)
        lab[..., 1] += (ta - cur[1]) * (a > 0)
        lab[..., 2] += (tb - cur[2]) * (a > 0)
        save_layer(p, np.clip(C.from_lab(lab), 0, 1), a)
        rec[slot] = dict(rule="a* b* to MB0's lit tone, L* kept", before_ab=[round(float(cur[1]), 1), round(float(cur[2]), 1)], to=[ta, tb])
    # the rug: the same listing and photo as the living room's rug; there it reads 3.95 x the oak floor beside it (luminance, medians:
    # rug L* 77.1 against oak 42.9, the r12 set-B graded frame) at C* 11.9; the edit drew it barely lighter than the oak (43 against 40)
    # and more saturated. Its median set to 3.95 x the oak beside it (the plate's floor within 200 px, under no layer), C* to 11.9, hue
    # kept; in linear light, so its braid and the bed's and bench's shade on it stay
    p, im = load_layer(man, "rug")
    rgb, a = im[..., :3], im[..., 3]
    lab = C.to_lab(rgb)
    rug = a > 0.99
    anyA = np.zeros((H, W), bool)
    for l in man["layers"]:
        anyA |= np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0
    oak = np.isin(M.ids("MB1-plate"), (10,)) & ~anyA & M.frame_mask() & ~C.dil(rug, 10) & C.dil(rug, 200)
    oakL = float(np.median(comp[oak][:, 0]))
    tY = 3.95 * float(Y_of(np.array(oakL)))
    tL = float(L_of(np.array(tY)))
    cur = np.median(lab[rug], 0)
    g = tY / float(Y_of(np.array(cur[0])))
    kc = 11.9 / max(float(np.hypot(cur[1], cur[2])), 1e-3)
    w = (a > 0).astype(np.float64)
    lab2 = lab.copy()
    lab2[..., 0] = L_of(Y_of(lab[..., 0]) * (1 + (g - 1) * w))
    lab2[..., 1] = lab[..., 1] * (1 + (kc - 1) * w)
    lab2[..., 2] = lab[..., 2] * (1 + (kc - 1) * w)
    save_layer(p, np.clip(C.from_lab(lab2), 0, 1), a)
    rec["rug"] = dict(rule="the living room's rug-to-oak ratio (3.95, luminance of the medians) and its C* (11.9), hue kept",
                      oak_beside_L=round(oakL, 1), rug_before=[round(float(v), 1) for v in cur], target_median_L=round(tL, 1),
                      luminance_gain=round(g, 3), chroma_scale=round(kc, 3))
    r = json.load(open(os.path.join(ST, "mb1-compose.json")))
    r["tone_fix"] = rec
    json.dump(r, open(os.path.join(ST, "mb1-compose.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
