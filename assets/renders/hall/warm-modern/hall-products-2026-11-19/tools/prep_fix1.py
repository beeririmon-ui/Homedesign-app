#!/usr/bin/env python3
"""
prep_fix1.py: the input of fix1 (the throw and the basket again), render-agent 2026-11-19. 0 tokens.
Why: r1 drew the throw's stack about 14 cm thick at the front (8.1: 7-8, QA 7-9) and its last panel about 25 cm down (8.1: about
15), and the basket 12 % wider than D 30 and about 5 cm right of Y 7.10. The wall light and the pegs of r1 stay (refit in code).
  the input = ht2.png, with r1's refit wall light and pegs (compose.py r1 stage, as a preview) for context, and the clay's throw
              and basket proxies (geo.py) at their exact size, textured with r1's own waffle (a flat patch of its hanging panel)
              and rope (a patch of its basket), so the model reads the scale from the cells and the rope rows:
                - the stack 37 x 40 x 7.5 with five fold edges on its front, the waffle on its top foreshortened (x 0.28)
                - the hanging panel to Z 0.30 (15 cm below the seat's front edge), a hem at its bottom
                - the basket D 30 x H 30 at (1.01, 7.10), its rope rows, a lighter rim and two loops
  the island = the throw's and the basket's islands of prep.py
  python3 prep_fix1.py <r1 canvas png> <r1 preview png>   ->  SCR/fix1-input.png, SCR/island-fix1.png
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo as G  # noqa: E402

K = G.K
WAFFLE_BOX = (1520, 1300, 1700, 1420)      # r1 canvas: a flat part of the hanging panel (x0, y0, x1, y1)
ROPE_BOX = (1772, 1420, 1828, 1515)        # r1 canvas: the basket's rope rows, right of the panel
TOP_BOX = (1500, 1125, 1640, 1160)         # r1 canvas: the lit top of its stack


def face_masks(slot):
    """per visible face of a slot (painter's order): (mask, normal, tag)"""
    cam, cv = K.CAMS["HT"], K.canvas("HT")
    loc = np.asarray(cam.loc)
    items = []
    for quad, nrm, tag in G.faces(slot):
        Q = np.asarray(quad, float)
        nm = np.asarray(nrm, float)
        if nm @ (loc - Q.mean(0)) <= 0:
            continue
        u, v, d = cam.project(Q)
        x, y = cv.px(u, v)
        m = np.zeros((cv.h, cv.w), np.uint8)
        cv2.fillPoly(m, [np.int32(np.round(np.stack([x, y], -1) * 16))], 1, shift=4)
        items.append((float(np.mean(d)), m > 0, nm, tag))
    items.sort(key=lambda t: -t[0])
    return items


def tile(patch, h, w, ox=0, oy=0, mirror=True):
    """tiling, mirrored for the waffle (no hard seams for the model to copy), straight for the rope (mirrored rows make chevrons)"""
    if mirror:
        patch = np.concatenate([patch, patch[::-1]], 0)
        patch = np.concatenate([patch, patch[:, ::-1]], 1)
    reps = (h // patch.shape[0] + 2, w // patch.shape[1] + 2, 1)
    t = np.tile(patch, reps)
    return t[oy:oy + h, ox:ox + w]


def main(r1c, prev):
    base = K.rgb(os.path.join(G.HALL18, "ht2.png"))
    r1 = K.rgb(r1c)
    pv = K.rgb(prev)
    inp = base.copy()
    st = np.load(os.path.join(G.SCR, "stage-r1.npz"))
    for s in ("wall-sconce", "wall-hooks"):
        isl = st[f"{s}__island"]                                  # the compose's islands (the light's restricted, compose.py)
        inp[isl] = pv[isl]
    H, W = base.shape[:2]
    x0, y0, x1, y1 = WAFFLE_BOX
    waf = r1[y0:y1, x0:x1]
    waf_rel = waf / waf.mean((0, 1))                             # the cells' light and shade only
    khaki = 0.5 * (r1[TOP_BOX[1]:TOP_BOX[3], TOP_BOX[0]:TOP_BOX[2]].reshape(-1, 3).mean(0) + waf.mean((0, 1)))   # r1's own khaki:
    # the mean of its lit stack top and its panel in the seat's shade (either alone reads too light or too brown)
    x0, y0, x1, y1 = ROPE_BOX
    rope = r1[y0:y1, x0:x1]
    rope_rel = rope / rope.mean((0, 1))
    rope_rel = rope_rel / rope_rel.mean(1, keepdims=True).mean(0, keepdims=True)
    cream = rope.mean((0, 1)) * 1.05                             # r1's own cream
    out = inp.copy()
    # the basket (behind), then the throw
    for d, m, nm, tag in face_masks("basket"):
        s = 0.55 + 0.45 * max(0.0, float(nm @ G.LIGHT))
        if tag == "inside":
            out[m] = np.array([0.36, 0.33, 0.28])
            continue
        tex = tile(rope_rel, H, W, mirror=False)
        out[m] = np.clip(cream * s * tex[m], 0, 1)
    bm = G.bench_mask()
    out[bm] = inp[bm]                                            # the seat and the panels stay in front of the basket
    for d, m, nm, tag in face_masks("bench-throw"):
        s = 0.62 + 0.38 * max(0.0, float(nm @ G.LIGHT))
        if nm[2] > 0.5:                                          # the top: foreshortened cells
            t = cv2.resize(waf_rel, (waf_rel.shape[1], max(4, int(waf_rel.shape[0] * 0.28))), interpolation=cv2.INTER_AREA)
            tex = tile(t, H, W)
        elif tag == "khaki_flap":
            tex = tile(waf_rel, H, W)
        else:
            tex = np.ones((H, W, 3))
        out[m] = np.clip(khaki * s * tex[m], 0, 1)
    # five fold edges on the stack's front, the crease, and the hem at the bottom of the panel
    y0t, y1t = G.THROW["y"]
    z0, z1 = G.THROW["z"]
    xf = G.THROW["x"][1]
    o8 = (out * 255).astype(np.uint8)
    for z in np.linspace(z0, z1, 6)[1:-1]:
        ln = G.polyline([(xf, y0t, z), (xf, y1t, z)])
        cv2.polylines(o8, [np.int32(np.round(ln * 16))], False, (120, 112, 98), 1, cv2.LINE_AA, shift=4)
    ln = G.polyline([(xf + G.THROW["flap_t"], y0t, z0), (xf + G.THROW["flap_t"], y1t, z0)])
    cv2.polylines(o8, [np.int32(np.round(ln * 16))], False, (100, 93, 80), 3, cv2.LINE_AA, shift=4)
    for zz, col in ((G.THROW["flap_z"] + 0.012, (128, 120, 104)), (G.THROW["flap_z"] + 0.004, (110, 102, 88))):
        ln = G.polyline([(xf + G.THROW["flap_t"], y0t, zz), (xf + G.THROW["flap_t"], y1t, zz)])
        cv2.polylines(o8, [np.int32(np.round(ln * 16))], False, col, 2, cv2.LINE_AA, shift=4)
    out = o8 / 255.0
    isl = np.zeros((H, W), bool)
    for s in ("bench-throw", "basket"):
        isl |= np.asarray(Image.open(os.path.join(G.SCR, f"island-{s}.png"))) > 0
    res = inp.copy()
    res[isl] = out[isl]
    K.save(os.path.join(G.SCR, "fix1-input.png"), res)
    Image.fromarray((isl * 255).astype(np.uint8)).save(os.path.join(G.SCR, "island-fix1.png"))
    b8 = (base * 255 + 0.5).astype(np.uint8)
    r8 = K.rgb8(os.path.join(G.SCR, "fix1-input.png"))
    allisl = isl | st["wall-sconce__island"] | st["wall-hooks__island"]
    print("outside islands max diff vs ht2:", int(np.abs(r8.astype(int) - b8.astype(int))[~allisl].max()), "island px", int(isl.sum()))


if __name__ == "__main__":
    main(*sys.argv[1:3])
