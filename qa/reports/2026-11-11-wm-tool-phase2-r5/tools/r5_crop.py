#!/usr/bin/env python3
"""
qa-agent 2026-11-11 (R5): crop helper. Usage:
  python3 r5_crop.py OUT.png SCALE x0 y0 x1 y1 IMG [IMG ...]
Crops the same box (canvas px, 2720 x 1530) from each image, scales it by SCALE with nearest neighbour (no smoothing, so halos and
posterisation stay visible), and lays them side by side with a 6 px grey gap. An IMG may be 'scene:B' (graded/default-scene-r5-set-B),
'scene4:B' (r4), 'var:<id>' (graded/variant-r5-<id>-set-B), 'base', or a path; 'alpha:<layer path>' shows a layer's alpha as grey.
"""
import os
import sys

import numpy as np
from PIL import Image

REPO = "/home/user/homedesign-app"
P2 = os.path.join(REPO, "assets/renders/living-room/warm-modern/phase2-2026-11-10")


def load(spec):
    if spec.startswith("scene:"):
        p = os.path.join(P2, f"graded/default-scene-r5-set-{spec[6:]}-graded-v3c.png")
    elif spec.startswith("scene4:"):
        p = os.path.join(P2, f"graded/default-scene-r4-set-{spec[7:]}-graded-v3c.png")
    elif spec.startswith("var:"):
        p = os.path.join(P2, f"graded/variant-r5-{spec[4:]}-set-B-graded-v3c.png")
    elif spec == "base":
        p = os.path.join(P2, "layers/base.png")
    elif spec.startswith("alpha:"):
        a = np.asarray(Image.open(os.path.join(P2, "layers", spec[6:])))[..., 3]
        return np.dstack([a, a, a])
    elif spec.startswith("layerrgb:"):
        a = np.asarray(Image.open(os.path.join(P2, "layers", spec[9:])))
        return a[..., :3]
    else:
        p = spec
    return np.asarray(Image.open(p).convert("RGB"))


def main():
    out, sc = sys.argv[1], int(sys.argv[2])
    x0, y0, x1, y1 = map(int, sys.argv[3:7])
    tiles = []
    for spec in sys.argv[7:]:
        im = load(spec)[y0:y1, x0:x1]
        tiles.append(np.repeat(np.repeat(im, sc, 0), sc, 1))
    gap = np.full((tiles[0].shape[0], 6, 3), 90, np.uint8)
    row = tiles[0]
    for t in tiles[1:]:
        row = np.concatenate([row, gap, t], 1)
    Image.fromarray(row.astype(np.uint8)).save(out)
    print(out, row.shape)


if __name__ == "__main__":
    main()
