#!/usr/bin/env python3
"""
mb1_throw_end_prep.py: the input of the M1 mask edit (render-agent, 2026-11-19; manager's ruling after QA): the Pecan's near-right end
drops about 40 cm down the bed's side in the p1 edit (MB0: about 10 cm) with 6.5-8 cm twisted fringes (12.9: 2-3 cm loose threads).
The input is the p1 edit itself (locked onto the canvas, before MB1's toe), so the new edit lands in p1's own space; the throw's drop
below the new hem line is a flat placeholder: each row interpolated between the duvet beside the drop (left and right), so the model
draws the duvet's side drop there and ends the throw at the line.
The hem line: 60 px (about 10 cm at 5.8-6.6 px/cm, the QA's scale here) down the drop's two side edges from where they leave the bed's
top: left (1301, 1005) -> (1319, 1062), right (1460, 945) -> (1479, 1002).
  python3 mb1_throw_end_prep.py <p1-locked.npy>      (writes inputs/p5-throw-end-input.png and its prep json)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mb1_common as M  # noqa: E402

C = M.C
H, W = M.H, M.W
ST = M.ST
HEM = ((1319, 1062), (1479, 1002))
BOX = (1270, 950, 1580, 1275)


def below_hem():
    (x0, y0), (x1, y1) = HEM
    yy, xx = np.mgrid[0:H, 0:W]
    yline = y0 + (xx - x0) * (y1 - y0) / (x1 - x0)
    return yy > yline


def placeholder_mask():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    l = [x for x in man["layers"] if x["slot"] == "throw"][0]
    a = np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3] > 0
    bx = C.box_mask([BOX])
    return C.dil(a & bx, 4) & below_hem() & bx


def main(npy):
    e = np.load(npy).astype(np.float64)
    P = placeholder_mask()
    out = e.copy()
    for y in np.nonzero(P.any(1))[0]:
        xs = np.nonzero(P[y])[0]
        # runs of the placeholder in this row: interpolate each between the 5 px of duvet on either side
        runs = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
        for r in runs:
            a, b = r[0], r[-1]
            L = np.median(e[y, max(0, a - 7):a - 2], 0) if a > 7 else e[y, b + 3]
            R = np.median(e[y, b + 3:b + 8], 0)
            t = (np.arange(a, b + 1) - a + 0.5) / (b - a + 1)
            out[y, a:b + 1] = L[None, :] * (1 - t[:, None]) + R[None, :] * t[:, None]
    # a light vertical blur inside the patch only, so its rows read as one smooth area
    sm = cv2.GaussianBlur(out.astype(np.float32), (0, 0), 3).astype(np.float64)
    out[P] = sm[P]
    ip = os.path.join(ST, "inputs", "p5-throw-end-input.png")
    M.save(ip, np.clip(out, 0, 1))
    rec = dict(pass_="p5-throw-end", source="the p1 edit, locked (tools/mb1_compose.py p1-bed's e)", hem_line=HEM, box=BOX, placeholder_px=int(P.sum()),
               fill="row-wise interpolation between the duvet beside the drop, 3 px blur inside", input=os.path.relpath(ip, ST), input_sha256=M.sha(ip))
    json.dump(rec, open(os.path.join(ST, "inputs", "p5-throw-end-prep.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main(sys.argv[1])
