#!/usr/bin/env python3
"""
mb1_prints.py: the two prints set into the MB1 frames in code (render-agent, 2026-11-19; 0 tokens), as in MB0 (FB10): the model drew the
frames with blank canvases (#D8C8AE, never the art). Per frame: the canvas is the blank in the frame layer (Lab within 10 of its median,
alpha 1); the flat print (A: 776445, 801 x 1101; B: 386242 work 05, its listing margins cropped) is cover-fitted to the canvas's
projected quad (the frame's plane at Y 17.734, the moulding 2.5 cm in; the camera's homography, so the print sits in perspective) and
lit by the canvas's own light in the edit (its linear colour over #D8C8AE's, 1.5 px blur), so the shelf's light, the frame's inner
shadow and the room's warmth carry onto it. Only the canvas pixels of the two frame layers change; nothing else. Art A is x1 only
(rights unclear): no close-up, no zoom frame.
  python3 mb1_prints.py            (after mb1_compose.py p3-wall; then mb1_compose.py compose)
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
CANVAS_ALBEDO = np.array([216, 200, 174]) / 255
PRINTS = {"framed-art": dict(file="c2511450_S0a720a638a594c2c825b3e25ece41352o.jpg", x=(-1.244, -0.695), z=(1.50, 2.243), crop_white=False),
          "framed-art-2": dict(file="5aff04c0_Sffd2120da3974d409909687f874b51d0k.jpg", x=(-0.639, -0.191), z=(1.50, 1.838), crop_white=True)}
Y_FACE, MOULD = 17.734, 0.025


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    rec = {}
    for slot, P in PRINTS.items():
        l = [x for x in man["layers"] if x["slot"] == slot][0]
        lp = os.path.join(ST, l["layer"])
        rgba = np.asarray(Image.open(lp)).astype(np.float64) / 255
        rgb, a = rgba[..., :3], rgba[..., 3]
        lab = C.to_lab(rgb)
        opaque = a > 0.99
        med = np.median(lab[opaque & (np.linalg.norm(lab - np.array([79.0, 2.0, 16.5]), axis=-1) < 14)], 0)
        cv = opaque & (np.linalg.norm(lab - med[None, None, :], axis=-1) < 10)
        cv = cv2.morphologyEx(cv.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
        n, lb, st, _ = cv2.connectedComponentsWithStats(cv.astype(np.uint8), connectivity=8)
        cv = lb == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        cv = C.ero(cv, 1)
        (x0, x1), (z0, z1) = P["x"], P["z"]
        quad = np.float32([M.proj(x0 + MOULD, Y_FACE, z1 - MOULD), M.proj(x1 - MOULD, Y_FACE, z1 - MOULD),
                           M.proj(x1 - MOULD, Y_FACE, z0 + MOULD), M.proj(x0 + MOULD, Y_FACE, z0 + MOULD)])
        pr = C.load(M.PICKS + P["file"])
        if P["crop_white"]:
            nonw = pr.min(2) < 0.86
            ys, xs = np.nonzero(nonw)
            pr = pr[ys.min() + 4:ys.max() - 3, xs.min() + 4:xs.max() - 3]
        ph, pw = pr.shape[:2]
        cw, chh = (x1 - x0 - 2 * MOULD), (z1 - z0 - 2 * MOULD)                 # the canvas in metres: cover-fit the print to it
        k = max(cw / pw, chh / ph)
        sw, sh = cw / k, chh / k                                                   # the print's window, in print pixels
        ox, oy = (pw - sw) / 2, (ph - sh) / 2
        src = np.float32([[ox, oy], [ox + sw, oy], [ox + sw, oy + sh], [ox, oy + sh]])
        Hm = cv2.getPerspectiveTransform(src, quad)
        warped = cv2.warpPerspective(C.lin(pr).astype(np.float32), Hm, (W, H), flags=cv2.INTER_AREA if k * 1710 / 3.3 < 1 else cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
        light = C.blur(C.lin(rgb), 1.5) / C.lin(CANVAS_ALBEDO)[None, None, :]
        lit = C.srgb(np.clip(warped * light, 0, 1))
        w = C.blur(cv.astype(np.float64), 0.7) * cv
        out = rgb * (1 - w[..., None]) + lit * w[..., None]
        rgba8 = np.dstack([C.q(out), C.q(a)])
        rgba8[..., :3][rgba8[..., 3] == 0] = 0
        Image.fromarray(rgba8, "RGBA").save(lp)
        li = light[cv]
        rec[slot] = dict(file=P["file"].split("_")[0] + " (listing file, scratchpad only)", print_px=[pw, ph], canvas_px=int(cv.sum()),
                         quad=[[round(float(v), 1) for v in q] for q in quad], cover_window_px=[round(sw, 1), round(sh, 1)],
                         canvas_light_p5_p50_p95=[round(float(v), 3) for v in np.percentile(C.luma(li), [5, 50, 95])],
                         canvas_Lab_in_edit=[round(float(v), 1) for v in med])
        if slot == "framed-art":
            rec[slot]["closeup"] = "none: 776445's rights are unclear (x1 only)"
    rp = os.path.join(ST, "mb1-compose.json")
    r = json.load(open(rp))
    r["prints"] = rec
    json.dump(r, open(rp, "w"), indent=1)
    for l in man["layers"]:
        if l["slot"] == "framed-art":
            l["closeup"] = False
            l["closeup_note"] = "776445: usage rights unclear; no close-up or zoom frame"
        if l["slot"] in PRINTS:
            l["print"] = "set in code (tools/mb1_prints.py) from the flat file"
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
