"""MOCK7 (2026-11-26): the pixel gate of a frame whose default frame the render tools' finish composed (FB15's rooms,
M0-W): its layers, shadows (RGB, multiply) and lights (screen, times 1 − every alpha), composed exactly as
assets/renders/tools/finish/finish.py composes them, against the folder's own default frame (at the canvas; or, for a
1920 frame, through the finish's frame view: the 16:9 camera frame, bicubic). Read only: nothing is written. Prints
{"max": .., "differing": .., "values": .., "size": [w, h]} in channel values.

usage: python3.12 -I tools/tour/gate_finish.py <folder> <manifest> <truth> <finish tools folder>
         [--frame <id>] [--plate <file>] [--box <json with frame_box>]

--frame: a manifest of several frames (the kitchen's D1 / D2): that frame's layers and lights only.
--box: the manifest writes its frame box to 4 decimals; the finish resampled at the box's full precision, which a file
of the folder holds (M0-W: m0w-depth.json).
"""
import json
import os
import sys

import numpy as np

folder, manifest_rel, truth_rel, finish_dir = sys.argv[1:5]
opt = dict(zip(sys.argv[5::2], sys.argv[6::2]))
sys.path.insert(0, finish_dir)
import finish as F  # noqa: E402  (the render folder's own compose and frame view)

man_path = os.path.join(folder, manifest_rel)
m = json.load(open(man_path))
frame = opt.get("--frame")
base_rel = opt.get("--plate") or os.path.relpath(os.path.normpath(os.path.join(os.path.dirname(man_path), m["base"])), folder)


def here(x):
    return (not frame or x.get("frame", frame) == frame) and not x.get("retired")


def path(f):
    # FB15's code lights name their file from the style folder or the room's (warm-modern/<folder>/light/..., <folder>/light/...)
    p = os.path.join(folder, f)
    if os.path.exists(p):
        return p
    rest = f.split("/", 1)[1] if f.startswith(m.get("style", "warm-modern") + "/") else f
    return os.path.join(folder, rest.split("/", 1)[1] if rest.startswith(os.path.basename(os.path.normpath(folder)) + "/") else rest)


rows = [(i, x) for i, x in enumerate(m["layers"]) if here(x) and x.get("default", True) is not False]
rows.sort(key=lambda r: (r[1]["z"], r[1].get("sub", 0), r[0]))
layers = [(F.rd(path(x["layer"]), "RGBA"), F.rd(path(x["shadow"]), "RGB")) for _, x in rows]
lights = [F.rd(path(x["file"]), "RGB") for x in (m["light"] if isinstance(m["light"], list) else [m["light"]]) if here(x)]
comp = F.compose(F.rd(os.path.join(folder, base_rel), "RGB"), layers, lights)
truth = F.rd(os.path.join(folder, truth_rel), "RGB")
if truth.shape != comp.shape:
    box = json.load(open(os.path.join(folder, opt["--box"])))["frame_box"] if "--box" in opt else m["frame_box"]
    comp = F.frame_view(comp, {"frame_box": box}, (truth.shape[1], truth.shape[0]))
d = np.abs(comp.astype(np.int16) - truth.astype(np.int16))
print(json.dumps({"max": int(d.max()), "differing": int((d > 0).sum()), "values": int(d.size), "size": [int(truth.shape[1]), int(truth.shape[0])]}))
