#!/usr/bin/env python3
"""
kd_print.py: print 05 into the frame's blank canvas, in code (render-agent, resumed session, 2026-11-20; 0 tokens). 10.7: the print of
framed-art-aliexpress-misty-landscape-386242-work, design 05 (landscape, 40 x 30), goes in from the listing's flat file, as in the
bedroom (master stage1 tools/fb10_compose.py set_print): the listing shows the print on white with a margin, so the non-white part is
taken; it is cover-fit into the canvas (no stretch) and lit by the canvas's own light in the edit (the edit's canvas over the colour it
was asked to be, #D8C8AE, 1.5 px blur), so the moulding's edge shadow and the LED's wash carry over.
The canvas is found in the D2 layer of the frame: the largest flat region of the asked colour inside the layer, its bounding box less
1 px. Run after kd_cut2.py (E-left) and before compose_edits.py project (D1 gets the print by the projection).
  python3 kd_print.py        (the supplier file is read from the scratchpad only; it never enters the repo)
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402

C = K.C
ST = K.ST
H, W = K.H, K.W
PRINT = os.path.join(K.PICKS, "img", "5aff04c0_Sffd2120da3974d409909687f874b51d0k.jpg")   # design 05, the bedroom's framed-art-2 file
CANVAS_ALBEDO = np.array([216, 200, 174]) / 255
PID = "framed-art-aliexpress-misty-landscape-386242-work-05-30x40"


def main():
    man = json.load(open(os.path.join(ST, "manifest.json")))
    l = [x for x in man["layers"] if x["frame"] == "D2" and x["product"] == PID and not x.get("projected_from")][0]
    lp = os.path.join(ST, l["layer"])
    rgba = np.asarray(Image.open(lp)).copy()
    a = rgba[..., 3] > 250
    rgb = rgba[..., :3].astype(np.float64) / 255
    lab = C.to_lab(rgb)
    med = np.median(lab[C.ero(a, 6)], 0)
    flat = a & (np.linalg.norm(lab - med, axis=-1) < 9)
    flat = cv2.morphologyEx(flat.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
    n, lb, st, _ = cv2.connectedComponentsWithStats(flat.astype(np.uint8), connectivity=4)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.nonzero(lb == i)
    x0, y0, x1, y1 = xs.min() + 1, ys.min() + 1, xs.max(), ys.max()
    pr = C.load(PRINT)
    nonw = pr.min(2) < 0.86
    py, px = np.nonzero(nonw)
    pr = pr[py.min() + 4:py.max() - 3, px.min() + 4:px.max() - 3]
    cw, ch = x1 - x0, y1 - y0
    k = max(cw / pr.shape[1], ch / pr.shape[0])
    sw, sh = pr.shape[1] * k, pr.shape[0] * k
    M = np.array([[k, 0, x0 - (sw - cw) / 2], [0, k, y0 - (sh - ch) / 2]], np.float32)
    pl_ = cv2.warpAffine(C.lin(pr).astype(np.float32), M, (W, H), flags=cv2.INTER_AREA if k < 1 else cv2.INTER_LINEAR).astype(np.float64)
    light = C.blur(C.lin(rgb), 1.5) / C.lin(CANVAS_ALBEDO)[None, None, :]
    box = np.zeros((H, W), bool)
    box[y0:y1, x0:x1] = True
    lit = C.srgb(np.clip(pl_ * light, 0, 1))
    rgb2 = np.where(box[..., None], lit, rgb)
    rgba[..., :3] = C.q(rgb2)
    Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
    rp = os.path.join(ST, "compose.json")
    rec = json.load(open(rp))
    li = C.luma(light[box])
    rec["print-05"] = dict(file=os.path.basename(PRINT).split("_")[0] + " (listing file, scratchpad only)", file_px=list(pr.shape[1::-1]),
                           canvas_box_px=[int(x0), int(y0), int(x1), int(y1)], canvas_px=[int(cw), int(ch)], cover_scale=round(float(k), 4),
                           cropped_px=[round(float(sw - cw), 1), round(float(sh - ch), 1)],
                           canvas_light_p5_p50_p95=[round(float(v), 3) for v in np.percentile(li, [5, 50, 95])],
                           rule="10.7: print 05 into the blank canvas in code, cover-fit, lit by the edit's canvas light; D1 gets it by the projection")
    l["print"] = "05, in code (tools/kd_print.py)"
    json.dump(rec, open(rp, "w"), indent=1, default=str)
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    print(json.dumps(rec["print-05"]))


if __name__ == "__main__":
    main()
