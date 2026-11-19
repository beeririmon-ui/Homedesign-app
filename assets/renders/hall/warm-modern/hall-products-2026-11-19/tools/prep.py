#!/usr/bin/env python3
"""
prep.py: the model input and the island masks of the HT2 product pass, render-agent 2026-11-19. 0 tokens.
  the input  = ht2.png (accepted, 12.7.2) outside the islands byte for byte; inside them a rough render of each product (geo.py,
               flat-shaded in its photo colour) and, for the wall light, two soft V beams on the stone (up and down from the
               cylinder's open ends, warm), so the model sees where and how big each product is ("the pasted areas are the masks",
               as in HT2 r1: var2 takes no mask)
  the islands = per product: its silhouette grown by `grow` px (its contact shadow), and for the wall light the beam zone; the
               compose takes the model's pixels only there (RND2: outside them ht2.png byte for byte)
  python3 prep.py   ->  SCR/ht2p-input.png, SCR/island-<slot>.png, SCR/beam.npy, OUT/prep.json
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo as G  # noqa: E402

K = G.K
GROW = {"wall-sconce": 28, "wall-hooks": 18, "bench-throw": 26, "basket": 24}
PAINT = ("wall-sconce", "wall-hooks", "basket", "bench-throw")
BEAM = dict(tan=0.40, w0=0.024, h0=0.16, gain=1.6, z_up=G.SCONCE["z"][1], z_dn=G.SCONCE["z"][0], y=G.SCONCE["axis"][1])


def beam_field(still="HT"):
    """The wall light's two V beams on the limestone plane (X 0.81) of a still: a relative irradiance 0-1 per canvas pixel."""
    P, ok = K.world(still)
    stone = ok & (np.abs(P[..., 0] - G.STONE_X) < 0.006)
    Y, Z = P[..., 1], P[..., 2]
    lat = np.abs(Y - BEAM["y"])
    out = np.zeros(Y.shape, np.float32)
    for sgn, z0 in ((1, BEAM["z_up"]), (-1, BEAM["z_dn"])):
        h = np.maximum(sgn * (Z - z0), 0)
        w = BEAM["w0"] + h * BEAM["tan"]
        edge = np.clip(1 - (lat - w * 0.55) / (w * 0.6 + 1e-3), 0, 1)
        edge = edge * edge * (3 - 2 * edge)
        fall = 1.0 / (1 + (h / BEAM["h0"]) ** 2)
        start = np.clip(h / 0.01, 0, 1)
        out = np.maximum(out, np.where(h > 0, edge * fall * start, 0))
    return np.where(stone, out, 0).astype(np.float32)


def main():
    os.makedirs(G.SCR, exist_ok=True)
    base = K.rgb(os.path.join(G.HALL18, "ht2.png"))
    inp = base.copy()
    rep = dict(base="hall-2026-11-18/ht2.png", islands={})
    # the beams first (on the stone), then the products over them
    bf = beam_field()
    tint = np.array([1.0, 0.86, 0.66])                     # 2700 K against the daylight of the still, roughly
    lin = K.to_lin(inp)
    lin = lin * (1 + BEAM["gain"] * bf[..., None] * tint)
    inp = K.to_srgb(np.clip(lin, 0, 1))
    beam_zone = bf > 0.0005                                 # the whole tail (1.6 x 0.0005 < 1 level): nothing leaks out of the island
    np.save(os.path.join(G.SCR, "beam.npy"), bf.astype(np.float16))
    for s in PAINT:                                       # far to near: the basket under the seat before the throw's hanging panel
        rgb, cover, dep = G.render(s)
        if s == "basket":
            cover &= ~G.bench_mask()
        inp[cover] = rgb[cover]
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * GROW[s] + 1,) * 2)
        isl = cv2.dilate(cover.astype(np.uint8), k) > 0
        if s == "wall-sconce":
            isl |= cv2.dilate(beam_zone.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        Image.fromarray((isl * 255).astype(np.uint8)).save(os.path.join(G.SCR, f"island-{s}.png"))
        Image.fromarray((cover * 255).astype(np.uint8)).save(os.path.join(G.SCR, f"proxy-{s}.png"))
        rep["islands"][s] = dict(grow_px=GROW[s], proxy_px=int(cover.sum()), island_px=int(isl.sum()), uv_box=G.uv_box(cover)[0],
                                 px_box=G.uv_box(cover)[1])
    crease, layers = G.throw_lines()
    ov = (inp * 255).astype(np.uint8).copy()
    cv2.polylines(ov, [np.int32(np.round(crease * 16))], False, (112, 104, 90), 3, cv2.LINE_AA, shift=4)
    for ln in layers:
        cv2.polylines(ov, [np.int32(np.round(ln * 16))], False, (150, 142, 126), 1, cv2.LINE_AA, shift=4)
    tm = np.asarray(Image.open(os.path.join(G.SCR, "island-bench-throw.png"))) > 0
    inp[tm] = ov[tm] / 255.0
    K.save(os.path.join(G.SCR, "ht2p-input.png"), inp)
    rep["beam"] = dict(BEAM, zone_px=int(beam_zone.sum()))
    rep["outside_islands_identical"] = True
    K.dump(os.path.join(G.OUT, "prep.json"), rep)
    print(rep)


if __name__ == "__main__":
    main()
