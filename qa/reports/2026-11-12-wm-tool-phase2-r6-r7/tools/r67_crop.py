#!/usr/bin/env python3
"""
qa-agent 2026-11-12 (R6/R7): crop helper. Usage:
  python3 r67_crop.py OUT.png SCALE x0 y0 x1 y1 IMG [IMG ...]
Crops the same box (canvas px, 2720 x 1530) from each image, scales it by SCALE with nearest neighbour (halos and posterisation stay
visible) and lays them side by side with a 6 px grey gap. IMG:
  scene<N>:<set>      graded/default-scene-r<N>-set-<set>-graded-v3c.png   (N = 4..7)
  var<N>:<id>         graded/variant-r<N>-<id>-set-B-graded-v3c.png
  base                layers/base.png
  alpha:<layer path>  the layer's alpha as grey;  rgb:<layer path> the layer's RGB;  shadow:<file> a shadow file
  raw:<path>          a raw render (any size, resized to the canvas) - only for side-by-side reading
  or a path.
"""
import os
import sys

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")


def load(spec):
    if spec.startswith("scene"):
        n, s = spec[5:].split(":")
        p = os.path.join(P2, f"graded/default-scene-r{n}-set-{s}-graded-v3c.png")
    elif spec.startswith("var"):
        n, v = spec[3:].split(":")
        p = os.path.join(P2, f"graded/variant-r{n}-{v}-set-B-graded-v3c.png")
    elif spec == "base":
        p = os.path.join(P2, "layers/base.png")
    elif spec.startswith("alpha:"):
        a = np.asarray(Image.open(os.path.join(P2, "layers", spec[6:])))[..., 3]
        return np.dstack([a, a, a])
    elif spec.startswith("rgb:"):
        return np.asarray(Image.open(os.path.join(P2, "layers", spec[4:])))[..., :3]
    elif spec.startswith("shadow:"):
        return np.asarray(Image.open(os.path.join(P2, "layers", spec[7:])).convert("RGB"))
    elif spec.startswith("raw:"):
        return np.asarray(Image.open(spec[4:]).convert("RGB").resize((2720, 1530), Image.LANCZOS))
    else:
        p = spec
    return np.asarray(Image.open(p).convert("RGB"))


def crop(out, sc, x0, y0, x1, y1, specs):
    tiles = []
    for spec in specs:
        im = load(spec)[y0:y1, x0:x1]
        tiles.append(np.repeat(np.repeat(im, sc, 0), sc, 1))
    gap = np.full((tiles[0].shape[0], 6, 3), 90, np.uint8)
    row = tiles[0]
    for t in tiles[1:]:
        row = np.concatenate([row, gap, t], 1)
    Image.fromarray(row.astype(np.uint8)).save(out)
    return row.shape


if __name__ == "__main__":
    o, s = sys.argv[1], int(sys.argv[2])
    print(o, crop(o, s, *map(int, sys.argv[3:7]), sys.argv[7:]))
