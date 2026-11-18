#!/usr/bin/env python3
"""
prep_hc.py: the model input of HC (route 12.3: the corridor from the junction, a new view from the clay), render-agent 2026-11-18. 0 tokens.
The clay HC (wm-hall-2026-11-18, the walnut portal flush with the plaster, the bath window out of the hall corner) in linear light, its
surfaces found from the clay's world points and normals (the corridor is outside the entrance clay's id scope: id 99), then:
  - materials: plaster bone (a* 1, b* 5), the oak floor to #8B6F55's chroma at the corridor's light, the walnut (the portal's linings and
    soffit, the door reveals, the bedroom door's lining) to the walnut lining's chroma of hdx.png; lightness kept
  - levels (route 12.3, 12.5; display stops against base.png's back wall), one gain per surface group, real edges between groups:
      the hall plaster around the portal -0.60; the corridor's right wall at mid height, Y 11-13, -0.8; its left wall 0.5 under it;
      the bedroom seen through the door 0; the floor, the ceiling and the far wall of the corridor take the right wall's gain
  - the slot: kept as the clay draws it (a soft line), capped under 255
  python3 prep_hc.py <work_dir> -> hc-input.png, hc-groups.png, prep-hc.json
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
from prep_ht2 import normals  # noqa: E402

N = "HC"
TARGETS = dict(hall=-0.60, right=-0.80, left=-1.30, bedroom=0.15)
# the hall plaster around the portal: its two sides set apart (the right side stands under the hall's slot and is brighter in the clay by
# ~0.8 stop: left of the portal -0.75, right of it -0.35, so that their union sits at -0.60 and the bedroom door stays the brightest
# point after the slot line, route 12.3 rejection item 1)
HALL_SIDES = dict(hall_l=-0.75, hall_r=-0.35)


def groups(name=N):
    P, ok = K.world(name)
    n = normals(name)
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    nx, ny, nz = n[..., 0], n[..., 1], n[..., 2]
    G = {}
    G["floor"] = ok & (Z < 0.02) & (nz > 0.7)
    G["ceiling"] = ok & (nz < -0.7)
    G["slot"] = ok & (Z > 2.69) & ~G["ceiling"] & (Y > 9.9) & (X < 1.75)          # the corridor slot's well along the right wall's top
    walnut = ok & (((np.abs(X - 1.72) < 0.025) | (np.abs(X - 3.08) < 0.025)) & (Y > 9.795) & (Y < 9.955) & (Z < 2.71))   # the portal's linings
    walnut |= ok & (Z > 2.61) & (Z < 2.71) & (Y > 9.795) & (Y < 9.955) & (X > 1.70) & (X < 3.10)                         # its soffit
    side_rev = ok & (Y > 9.96) & (Y < 17.50) & (np.abs(ny) > 0.7) & ((X < 1.69) | (X > 3.11))                           # side doors' reveals
    bed_rev = ok & (Y > 17.50) & (Y < 17.70) & (np.abs(nx) > 0.7) & (X > 1.95) & (X < 2.95)                              # the bedroom door's
    G["walnut"] = walnut | side_rev | bed_rev
    G["walnut_plaster"] = side_rev | bed_rev
    G["hall"] = ok & (Y < 9.805) & ~G["walnut"] & ~G["floor"] & ~G["ceiling"]
    corr = ok & (Y >= 9.805) & (Y < 17.505) & ~G["walnut"] & ~G["floor"] & ~G["ceiling"] & ~G["slot"]
    G["right"] = corr & (nx > 0.7) & (X < 2.4)
    G["left"] = corr & (nx < -0.7) & (X > 2.4)
    G["end"] = corr & (ny < -0.7) & (Y > 17.4)
    U, V = K.canvas(name).uv()
    far = ~ok & (U > 0.45) & (U < 0.55) & (V > 0.25) & (V < 0.75)      # past 13.1 m the depth pass saturates: the bedroom's far wall
    G["bedroom"] = (ok & (Y >= 17.70) & ~G["floor"] & ~G["ceiling"]) | far
    G["through_side_doors"] = ok & (((X < 1.55) | (X > 3.25)) & (Y > 9.96)) & ~G["walnut"]
    G["leaf"] = ok & (X > 2.89) & (X < 2.95) & (Y > 17.65) & (Y < 18.6)
    for k in ("bedroom", "through_side_doors", "end", "right", "left", "hall"):
        G[k] &= ~G["leaf"]
    G["right"] &= ~G["through_side_doors"]
    G["left"] &= ~G["through_side_doors"]
    G["other"] = ok & ~np.any(np.stack([v for k, v in G.items() if k != "walnut_plaster"]), 0)
    return G, P, ok


def main(work):
    clay = K.to_lin(K.rgb(K.clay_png(N)))
    G, P, ok = groups()
    Y = clay @ K.W709
    Z = P[..., 2]
    U, V = K.canvas(N).uv()
    mid = (Z >= 0.80) & (Z <= 1.65)
    meas = dict(hall=G["hall"] & (((U >= 0.05) & (U < 0.20)) | ((U >= 0.85) & (U < 0.95))) & (V >= 0.40) & (V < 0.60),
                right=G["right"] & mid & (P[..., 1] >= 11) & (P[..., 1] <= 13),
                left=G["left"] & mid & (P[..., 1] >= 11) & (P[..., 1] <= 13),
                bedroom=G["bedroom"] & (V >= 0.40) & (V < 0.60))
    rep = dict(groups_px={k: int(v.sum()) for k, v in G.items()}, clay_levels={}, gains={})
    for k, m in meas.items():
        rep["clay_levels"][k] = round(K.stops_of(np.median(Y[m])), 3) if m.any() else None
    for k, (a, b) in (("hall_l", (0.05, 0.20)), ("hall_r", (0.85, 0.95))):
        meas[k] = G["hall"] & (U >= a) & (U < b) & (V >= 0.40) & (V < 0.60)
        rep["clay_levels"][k] = round(K.stops_of(np.median(Y[meas[k]])), 3)
    gain = {k: 2 ** (TARGETS[k] - rep["clay_levels"][k]) for k in TARGETS}
    gain.update({k: 2 ** (HALL_SIDES[k] - rep["clay_levels"][k]) for k in HALL_SIDES})
    gmap = np.ones(Y.shape)
    for k in ("right", "left", "bedroom"):
        gmap[G[k]] = gain[k]
    gmap[G["hall"] & (U < 0.5)] = gain["hall_l"]
    gmap[G["hall"] & (U >= 0.5)] = gain["hall_r"]
    for k in ("floor", "ceiling", "end", "walnut", "slot", "through_side_doors", "leaf", "other"):
        gmap[G[k]] = gain["right"]
    gmap[G["floor"] & (P[..., 1] < 9.80)] = gain["hall_l"]
    gmap[G["ceiling"] & (P[..., 1] < 9.80)] = gain["hall_l"]
    gmap[G["floor"] & (P[..., 1] > 17.66)] = gain["bedroom"]
    gmap[G["walnut"] & (P[..., 1] < 9.96)] = gain["hall_l"]
    gmap[G["leaf"]] = gain["bedroom"]
    rep["gains"] = {k: round(v, 3) for k, v in gain.items()}
    res = clay * gmap[..., None]
    # the door reveals of the corridor and of the bedroom are plaster in the clay: walnut albedo instead (Y 0.083 for the plaster's 0.78)
    rv = G["walnut_plaster"]
    res[rv] *= 0.083 / 0.78
    lab = K.lab_from_lin(res)

    def tint(m, a, b, keep=0.3):
        if m.any():
            lab[m, 1] = a + (lab[m, 1] - lab[m, 1].mean()) * keep
            lab[m, 2] = b + (lab[m, 2] - lab[m, 2].mean()) * keep
    plaster = G["hall"] | G["right"] | G["left"] | G["end"] | G["bedroom"] | G["ceiling"] | G["through_side_doors"] | G["leaf"] | G["other"]
    tint(plaster, 1.0, 5.0)
    tint(G["walnut"], 12.6, 18.8)
    tint(G["floor"], 6.0, 15.0)
    # the oak: #8B6F55 is L* ~49 in albedo; the clay's floor is pale: its lightness scaled to the plaster beside it, times 0.55
    fl = G["floor"]
    if fl.any():
        lab[fl, 0] = lab[fl, 0] * 0.62
    wl = G["walnut"]
    if wl.any():
        lab[wl, 0] = np.maximum(lab[wl, 0], 22.0)
    # the hall plaster right of the portal sits under the hall's slot: brighter (real), but kept off white with a soft shoulder over L* 90
    hl = G["hall"] | G["other"]
    L = lab[hl, 0]
    lab[hl, 0] = np.where(L > 90, 90 + 4 * np.tanh((L - 90) / 4), L)
    res = K.lin_from_lab(lab)
    res = np.minimum(res, 0.985)
    out = K.to_srgb(res)
    K.save(os.path.join(work, "hc-input.png"), out)
    pal = {"floor": (139, 111, 85), "ceiling": (245, 240, 230), "slot": (255, 255, 160), "walnut": (107, 74, 51), "hall": (236, 229, 218),
           "right": (200, 220, 240), "left": (170, 160, 200), "end": (220, 200, 160), "bedroom": (255, 220, 200), "through_side_doors": (255, 0, 0),
           "leaf": (0, 200, 200), "other": (255, 0, 255)}
    gi = np.zeros(Y.shape + (3,), np.uint8)
    for k, c in pal.items():
        if k not in G:
            continue
        gi[G[k]] = c
    K.save(os.path.join(work, "hc-groups.png"), gi)
    o8 = K.rgb8(os.path.join(work, "hc-input.png"))
    Yo = K.to_lin(o8 / 255.0) @ K.W709
    rep["input_levels"] = {k: round(K.stops_of(np.median(Yo[m])), 3) for k, m in meas.items() if m.any()}
    rep["note"] = "hall = route 12.3's region (both sides), target -0.60 +-1/6; hall_l / hall_r its two sides; right / left: the corridor walls, Y 11-13, Z 0.80-1.65"
    rep["input_clipped_px"] = int((o8.max(-1) >= 255).sum())
    K.dump(os.path.join(work, "prep-hc.json"), rep)
    print(rep)


if __name__ == "__main__":
    main(sys.argv[1])
