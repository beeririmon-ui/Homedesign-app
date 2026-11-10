#!/usr/bin/env python3
"""
resample_check.py: qa-agent, 2026-11-10. Informational, not an acceptance gate of the brief (the brief measures at 2720).

The engine (site/web/src/engine/engine.ts, gl.ts) composes the layers into an RGBA8 target at compWidth (1920 by default,
the 'lo' width on phones), from web files resized per width, each texture sampled LINEAR and premultiplied. So every layer
is resized on its own before the blend. This compares, per set and width:
  layered = each file resized on its own, then: base -> RGBA8 ; x shadow -> RGBA8 ; source-over premultiplied layer -> RGBA8
  single  = the approved composite resized as one picture
Two resizers:
  gl_bilinear   cv2 INTER_LINEAR on the 2720 files (the GL sampler on full-size textures)
  encoder_area  cv2 INTER_AREA, premultiplied resize, the layer stored back as 8-bit straight alpha (an offline web encoder)
Reported: p99.9 over the set's region and max of the per-pixel largest channel difference, counts >= 3 / >= 5 / > 6, and the
max outside the region grown by 1 px (must stay 0).
Writes <out_dir>/resample-check.json and two x4 crops for set B at 1920 into <crops_dir>.
Usage: python3 resample_check.py <out_json> <crops_dir>
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_recomposite as q  # noqa: E402

WIDTHS = [2720, 1920, 1440, 1280, 960, 800]
B = np.asarray(Image.open(os.path.join(q.LAYERS, "base.png"))).astype(np.float64)


def r8(x):
    return np.clip(np.floor(x + 0.5), 0, 255)


def run(mode, LA, S, T, w):
    h = round(w / (2720 / 1530))
    interp = cv2.INTER_LINEAR if mode == "gl_bilinear" else cv2.INTER_AREA

    def rs(a):
        return np.clip(cv2.resize(a.astype(np.float32), (w, h), interpolation=interp).astype(np.float64), 0, 255)

    a = LA[..., 3]
    if mode == "gl_bilinear":
        Lp8 = r8(LA[..., :3] * a[..., None] / 255.0)
        Lpt, at = rs(Lp8), rs(a)[..., None]
        Bt, St = r8(rs(B)), rs(S)
    else:
        at = r8(rs(a))[..., None]
        Lpt = rs(LA[..., :3] * a[..., None] / 255.0)
        Ls = np.where(at > 0, r8(Lpt * 255.0 / np.maximum(at, 1)), 0)
        Lpt = r8(Ls * at / 255.0)
        Bt, St = r8(rs(B)), r8(rs(S))
    m = r8(Bt * St / 255.0)
    out = r8(Lpt + m * (1 - at / 255.0))
    single = r8(rs(T))
    return out, single


def main():
    out_json, crops = sys.argv[1], sys.argv[2]
    res = {}
    keep = None
    for s in q.SETS:
        LA = np.asarray(Image.open(os.path.join(q.LAYERS, f"cushions-set-{s}.png"))).astype(np.float64)
        S = np.asarray(Image.open(os.path.join(q.LAYERS, f"cushions-set-{s}-shadow.png"))).astype(np.float64)
        T = np.asarray(Image.open(os.path.join(q.PILOT, f"composite-set-{s}-v3-graded-v3c.png"))).astype(np.float64)
        region = ((LA[..., 3] > 0) | (S < 255).any(2)).astype(np.uint8)
        res[s] = {}
        for mode in ("gl_bilinear", "encoder_area"):
            res[s][mode] = {}
            for w in WIDTHS:
                out, single = run(mode, LA, S, T, w)
                d = np.abs(out - single).max(2)
                h = out.shape[0]
                reg = cv2.resize(region, (w, h), interpolation=cv2.INTER_LINEAR) > 0
                reg_d = cv2.dilate(reg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
                res[s][mode][str(w)] = dict(p99_9_region=round(float(np.percentile(d[reg], 99.9)), 2), max=int(d.max()),
                                            px_ge3=int((d >= 3).sum()), px_ge5=int((d >= 5).sum()), px_gt6=int((d > 6).sum()),
                                            max_outside_region_plus_1px=int(d[~reg_d].max()))
                if s == "B" and mode == "encoder_area" and w == 1920:
                    keep = (out.astype(np.uint8), single.astype(np.uint8), d)
            print(s, mode, {w: (v["p99_9_region"], v["max"], v["px_gt6"]) for w, v in res[s][mode].items()})
    json.dump(res, open(out_json, "w"), indent=1)
    out, single, d = keep
    ys, xs = np.nonzero(d == d.max())
    spots = [(int(xs[0]), int(ys[0]))]
    d2 = d.copy()
    d2[max(0, spots[0][1] - 40):spots[0][1] + 40, max(0, spots[0][0] - 40):spots[0][0] + 40] = 0
    ys, xs = np.nonzero(d2 == d2.max())
    spots.append((int(xs[0]), int(ys[0])))
    for i, (cx, cy) in enumerate(spots):
        tiles = []
        for arr, txt in ((single[cy - 24:cy + 24, cx - 24:cx + 24], "approved composite resized (1920)"),
                         (out[cy - 24:cy + 24, cx - 24:cx + 24], "layers resized, then blended (1920)"),
                         (np.clip(np.abs(single[cy - 24:cy + 24, cx - 24:cx + 24].astype(int) - out[cy - 24:cy + 24, cx - 24:cx + 24].astype(int)) * 12, 0, 255).astype(np.uint8), "|diff| x12")):
            im = Image.fromarray(arr).resize((192, 192), Image.NEAREST)
            c = Image.new("RGB", (192, 210), (0, 0, 0))
            c.paste(im, (0, 18))
            ImageDraw.Draw(c).text((3, 3), txt, fill=(255, 255, 255))
            tiles.append(c)
        sheet = Image.new("RGB", (192 * 3 + 12, 210), (40, 40, 40))
        for k, t in enumerate(tiles):
            sheet.paste(t, (k * 198, 0))
        sheet.save(os.path.join(crops, f"resample-1920-set-B-spot{i + 1}-x4.png"))
        print("crop", i + 1, (cx, cy), "max", int(d[cy - 24:cy + 24, cx - 24:cx + 24].max()))


if __name__ == "__main__":
    main()
