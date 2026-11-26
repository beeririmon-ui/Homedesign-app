"""MOCK7 (2026-11-26): the pixel gate of a room whose default frame the render tools' finish made (M0-W, the living
room): its layers, shadows and lights, composed exactly as assets/renders/tools/finish/finish.py composes them (compose,
then frame_view: the 16:9 camera frame, bicubic, at the truth's size), against the folder's own default frame. Read
only: nothing is written. Prints {"max": .., "differing": .., "values": ..} (channel values).

usage: python3.12 -I tools/tour/gate_finish.py <folder> <manifest> <truth> <finish tools folder> [<json with frame_box>]

The manifest writes its frame box to 4 decimals; the finish resampled at the box's full precision, which a file of the
folder holds (M0-W: m0w-depth.json): given, it is used, and the frame is reproduced to the value.
"""
import json
import os
import sys

import numpy as np

folder, manifest_rel, truth_rel, finish_dir = sys.argv[1:5]
box_file = sys.argv[5] if len(sys.argv) > 5 else None
sys.path.insert(0, finish_dir)
import finish as F  # noqa: E402  (the render folder's own compose and frame view)

man_path = os.path.join(folder, manifest_rel)
m = json.load(open(man_path))
base = F.rd(os.path.normpath(os.path.join(os.path.dirname(man_path), m["base"])), "RGB")
rows = [(i, x) for i, x in enumerate(m["layers"]) if x.get("default", True) and not x.get("retired")]
# the manifest's own order (the finish composes its layers in the order it wrote them)
layers = [(F.rd(os.path.join(folder, x["layer"]), "RGBA"), F.rd(os.path.join(folder, x["shadow"]), "RGB")) for _, x in rows]
lights = [F.rd(os.path.join(folder, x["file"]), "RGB") for x in (m["light"] if isinstance(m["light"], list) else [m["light"]])]
comp = F.compose(base, layers, lights)
truth = F.rd(os.path.join(folder, truth_rel), "RGB")
if truth.shape != comp.shape:
    box = json.load(open(os.path.join(folder, box_file)))["frame_box"] if box_file else m["frame_box"]
    comp = F.frame_view(comp, {"frame_box": box}, (truth.shape[1], truth.shape[0]))
d = np.abs(comp.astype(np.int16) - truth.astype(np.int16))
print(json.dumps({"max": int(d.max()), "differing": int((d > 0).sum()), "values": int(d.size), "size": [int(truth.shape[1]), int(truth.shape[0])]}))
