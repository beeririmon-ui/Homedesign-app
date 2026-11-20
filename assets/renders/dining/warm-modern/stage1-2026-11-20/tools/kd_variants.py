#!/usr/bin/env python3
"""
kd_variants.py: the sample slot's variants (the pendant over the table) and their frames (render-agent, resumed session, 2026-11-20).
  v2       : V2 in code, 0 tokens. pendant-cj-silk-pumpkin-lantern, 50: its SKU drawing is the same 50 cm flat ribbed silk pumpkin with
             a dark bottom ring as V1's (the same shade from another listing); what differs is the suspension: a thin white wire, no
             rod. So V2 is V1's rendered shade with V1's rod and line taken off and the white wire drawn to the top of the frame.
  register : V3's layer (cut by kd_cut2.py from the crop edit) into the manifest as a variant
  frames   : D1-V2.png and D1-V3.png (+ 1920 frames): the defaults with only the pendant swapped; RND2 against D1-defaults outside
             the two pendants' alphas
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
import compose_edits as CE  # noqa: E402

C = K.C
ST = K.ST
H, W = K.H, K.W
V1 = "pendant-cj-silk-ribbed-pumpkin-40-50cm-warm-light"
V2 = "pendant-cj-silk-pumpkin-lantern-50cm-warm-light"
V3 = "pendant-cj-scalloped-pleated-bell-45"


def v2(man, rec):
    l1 = [l for l in man["layers"] if l["frame"] == "D1" and l["product"] == V1 and l["default"]][0]
    rgba = np.asarray(Image.open(os.path.join(ST, l1["layer"]))).copy()
    top = rec["A-table"]["pendant"]["new_shade_top_row"]
    cx = rec["A-table"]["pendant"]["centre_x"]
    rgba[: top - 1] = 0                                           # V1's rod and line off
    wire = np.array([228, 224, 216], np.uint8)                    # a thin white wire (the drawing), in the room's warm light
    x0 = int(np.floor(cx - 1))
    for y in range(0, top + 3):
        for x, a in ((x0 - 1, 70), (x0, 235), (x0 + 1, 235), (x0 + 2, 70)):
            if rgba[y, x, 3] < a:
                rgba[y, x, :3] = wire
                rgba[y, x, 3] = a
    lp = os.path.join(ST, "layers", "D1", "dining-pendant", V2 + ".png")
    sp = os.path.join(ST, "shadows", "D1", "dining-pendant", V2 + ".png")
    Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
    Image.fromarray(np.full((H, W), 255, np.uint8)).save(sp, optimize=True)
    ys, xs = np.nonzero(rgba[..., 3] > 0)
    man["layers"] = [l for l in man["layers"] if not (l["frame"] == "D1" and l["product"] == V2)]
    man["layers"].append(dict(frame="D1", slot="dining-pendant", product=V2, clay_id=50, z=80, sub=0, shadow_z=79, default=False, variant="V2",
                              layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sp, ST), alpha_px=int((rgba[..., 3] > 0).sum()), shadow_px=0,
                              bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], sold=True,
                              source="code variant (tools/kd_variants.py v2), 0 tokens: V1's rendered shade (the two SKU drawings show the same 50 cm "
                                     "flat ribbed silk pumpkin with a bottom ring), V2's suspension: a thin white wire, no rod", pass_="V2-code"))
    rec["V2-code"] = dict(shade_top_row=int(top), wire_px=4, wire_rgb=wire.tolist(), rule="V1's shade, V2's white wire (SKU drawing)")


def register_v3(man):
    for l in man["layers"]:
        if l["frame"] == "D1" and l["product"] == V3:
            l["variant"] = "V3"
            l["default"] = False


def frames(man, rec):
    base = np.asarray(Image.open(os.path.join(ST, "D1-defaults.png")).convert("RGB")).astype(int)
    a1 = np.asarray(Image.open(os.path.join(ST, [l for l in man["layers"] if l["frame"] == "D1" and l["product"] == V1][0]["layer"])))[..., 3]
    for v, pid in (("V2", V2), ("V3", V3)):
        ls = [l for l in man["layers"] if l["frame"] == "D1" and l["product"] == pid]
        if not ls:
            continue
        o8 = CE.compose(man, rec, "D1", swap={"dining-pendant": ls[0]}, out_name=f"D1-{v}")
        av = np.asarray(Image.open(os.path.join(ST, ls[0]["layer"])))[..., 3]
        region = (a1 > 0) | (av > 0)
        diff = np.abs(o8.astype(int) - base).max(2) > 0
        rec["frames"][f"D1-{v}"]["vs_defaults_outside_pendants_px"] = int((diff & ~region).sum())
        rec["frames"][f"D1-{v}"]["rule_variant"] = "only the pendant changes: outside V1's and this variant's alphas the frame is D1-defaults"


def main(cmd):
    man = CE.load_man()
    rp = os.path.join(ST, "compose.json")
    rec = json.load(open(rp))
    if cmd == "v2":
        v2(man, rec)
    if cmd == "register":
        register_v3(man)
    if cmd == "frames":
        frames(man, rec)
        print(json.dumps({k: v for k, v in rec["frames"].items() if k.startswith("D1-V")}))
    man["layers"].sort(key=lambda l: (l["frame"], l["z"], l.get("sub", 0), l["slot"]))
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    json.dump(rec, open(rp, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1])
