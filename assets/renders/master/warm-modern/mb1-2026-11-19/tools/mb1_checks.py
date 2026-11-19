#!/usr/bin/env python3
"""
mb1_checks.py: the MB1 checks (render-agent, 2026-11-19; 0 tokens): RND2 against plate.png, shadows one z under their layer, the
black point (WM-G1, p0.5 L* 11-14 in the 16:9 frame), each product's lit tone (L* p60-p90 of its opaque alpha, nothing of a higher z
over it) against the same product in MB0's approved composite, the planter by R5 (its median against the plaster ring 20-60 px out,
rows of the pot), and the room count (V7Q6 on MB1's frame). Writes mb1-checks.json.
  python3 mb1_checks.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST


def lit_lab(lab, m, pct=(60, 90)):
    v = lab[m]
    if len(v) < 30:
        return None
    lo, hi = np.percentile(v[:, 0], pct)
    return np.median(v[(v[:, 0] >= lo) & (v[:, 0] <= hi)], 0)


def clean_masks(man, root):
    al = {}
    for l in man["layers"]:
        key = l["slot"] + ("-" + l["side"] if l.get("side") else "")
        al[key] = (np.asarray(Image.open(os.path.join(root, l["layer"])))[..., 3], l["z"])
    out = {}
    for k, (a, z) in al.items():
        m = C.ero(a == 255, 3)
        for k2, (a2, z2) in al.items():
            if z2 > z:
                m &= a2 == 0
        out[k] = (m, a)
    return out


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    rep = {}
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB")).astype(int)
    o8 = np.asarray(Image.open(os.path.join(ST, "mb1-defaults.png")).convert("RGB")).astype(int)
    rep["rnd2"] = man["rnd2"]
    rep["shadow_z"] = all(l["shadow_z"] == l["z"] - 1 for l in man["layers"])
    fr = M.frame_mask()
    lab = C.to_lab(o8 / 255.0)
    rep["black_point_p05"] = round(float(np.percentile(lab[..., 0][fr], 0.5)), 2)
    # against MB0
    man0 = json.load(open(os.path.join(M.MB0, "layers", "manifest.json")))
    lab0 = C.to_lab(C.load(os.path.join(M.MB0, "mb0-defaults.png")))
    m1, m0 = clean_masks(man, ST), clean_masks(man0, M.MB0)
    vs = {}
    for k, (m, a) in m1.items():
        k0 = k.split("-east")[0].split("-west")[0]
        if k0 not in m0:
            continue
        a1, b0 = lit_lab(lab, m & fr), lit_lab(lab0, m0[k0][0])
        if a1 is None or b0 is None:
            vs[k] = "too little clean area to read"
            continue
        c1, c0 = float(np.hypot(a1[1], a1[2])), float(np.hypot(b0[1], b0[2]))
        h1, h0 = float(np.degrees(np.arctan2(a1[2], a1[1]))), float(np.degrees(np.arctan2(b0[2], b0[1])))
        vs[k] = dict(mb1=[round(float(v), 1) for v in a1], mb0=[round(float(v), 1) for v in b0], dE00=round(float(C.de00(tuple(a1), tuple(b0))), 1),
                     dL=round(float(a1[0] - b0[0]), 1), dC=round(c1 - c0, 1), dh=round(h1 - h0, 1))
    rep["vs_mb0_lit_tone"] = vs
    # planter R5
    ids_pl = M.ids("MB1-plate")
    anyA = np.zeros((H, W), bool)
    anyS = np.zeros((H, W), bool)
    for l in man["layers"]:
        anyA |= np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0
        anyS |= np.asarray(Image.open(os.path.join(ST, l["shadow"]))) < 250
    pm, pa = m1["planter"]
    rows = np.zeros((H, W), bool)
    ys = np.nonzero((pa > 0).any(1))[0]
    pot_rows = (1040, 1330)
    rows[pot_rows[0]:pot_rows[1]] = True
    ring = C.dil(pa > 0, 60) & ~C.dil(pa > 0, 20) & np.isin(ids_pl, (1, 2, 5)) & ~anyA & ~anyS & rows
    potm = pm & rows & (np.arange(W)[None, :] < 2642)
    mp, mw = np.median(lab[potm], 0), np.median(lab[ring], 0)
    rep["planter_R5"] = dict(pot_Lab=[round(float(v), 1) for v in mp], wall_ring_Lab=[round(float(v), 1) for v in mw], dL=round(float(mp[0] - mw[0]), 1),
                             pot_C=round(float(np.hypot(mp[1], mp[2])), 1), C_limit=round(float(np.hypot(mw[1], mw[2]) + 1.5), 1),
                             dh=round(float(np.degrees(np.arctan2(mp[2], mp[1])) - np.degrees(np.arctan2(mw[2], mw[1]))), 1),
                             ring_px=int(ring.sum()), pot_px=int(potm.sum()), rows=list(pot_rows), target="dL -6..-10 (aim -8), C <= wall + 1.5, h within 10")
    # the room count on MB1 (V7Q6: 0.5 % of the frame, or 0.15 % and 6 % of its height, and 50 % visible)
    fa = fr.sum()
    count = {}
    for l in man["layers"]:
        a = np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 127
        a &= fr
        if not a.any():
            continue
        ys_ = np.nonzero(a.any(1))[0]
        area, hgt = a.sum() / fa, (ys_.max() - ys_.min() + 1) / (M.FRAME[3] - M.FRAME[1])
        k = l["slot"] + ("-" + l["side"] if l.get("side") else "")
        count[k] = dict(frame_pct=round(100 * float(area), 3), height_pct=round(100 * float(hgt), 1),
                        passes=bool(area >= 0.005 or (area >= 0.0015 and hgt >= 0.06)))
    rep["v7q6_on_mb1"] = count
    json.dump(rep, open(os.path.join(ST, "mb1-checks.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("v7q6_on_mb1",)}, indent=0)[:4000])
    print({k: (v["frame_pct"], v["passes"]) for k, v in count.items()})


if __name__ == "__main__":
    main()
