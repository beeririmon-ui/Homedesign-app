#!/usr/bin/env python3
"""
work_variants.py: the sample slot's variant frames (render-agent, 2026-11-20; 0 tokens). The W0 frame composed exactly as the defaults
(work_compose.compose: plate, layers in z order with their shadows, the lights), with the framed-art layer swapped for each variant
layer (386242-01, -02; the same frame and shadow, another print, tools/work_prints.py). Outside the frame layer each variant frame is
the defaults frame, pixel for pixel.
  python3 work_variants.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work_common as M  # noqa: E402
import work_compose as WC  # noqa: E402

ST = M.ST


def main():
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    rec = json.load(open(os.path.join(ST, "w0-compose.json")))
    d8 = np.asarray(Image.open(os.path.join(ST, "w0-defaults.png")).convert("RGB"))
    out = {}
    for l in man["layers"]:
        if l["slot"] != "framed-art" or l.get("default"):
            continue
        tag = l["product"].split("-")[-2]
        name = f"w0-variant-art-{tag}"
        o8, rnd2, bp = WC.compose(man, rec, out_name=name, swap={"framed-art": l["layer"]})
        dl = [x for x in man["layers"] if x["slot"] == "framed-art" and x.get("default")][0]
        a = np.maximum(np.asarray(Image.open(os.path.join(ST, dl["layer"])))[..., 3], np.asarray(Image.open(os.path.join(ST, l["layer"])))[..., 3])
        diff = np.abs(o8.astype(int) - d8.astype(int)).max(2) > 0
        out[tag] = dict(frame=f"{name}.png", frame_1920=f"{name}-frame.png", product=l["product"], rnd2_vs_plate=rnd2, black_point_p05=bp,
                        differs_from_defaults_px=int(diff.sum()), differs_outside_the_frame_layer_px=int((diff & (a == 0)).sum()))
    rec["variants"] = out
    json.dump(rec, open(os.path.join(ST, "w0-compose.json"), "w"), indent=1, default=str)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
