"""MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md): the pixel gate of a frame of FB16's house light
(render-agent, assets/renders/tools/fb16/README.md): the frame's layers, shadows and lights composed on its fb16 base
exactly as tools/tour/gate_finish.py composes them (the render tools' finish.compose), then the house grade of the
frame (`fb16.frames.<id>.grade`, Lab, the fb16 tool's own apply_grade), then each glow over the whole graded frame
(screen, or multiply: B1's glass), against the folder's fb16 frame (through the finish's frame view). Read only:
nothing is written.

The fb16 frame is the grade of the render's FINISHED frame (fb15's finish: its grain and light wrap, which the
site's stack never carried: MOCK7's gate was against the composite before the finish). So the stack graded is the
fb16 frame up to that finish, and the gate is a measure: the mean and the 99th percentile of the channel differences,
and how much of the frame differs by more than 8 values. Prints
{"max", "mean", "p99", "over8", "differing", "values", "size"}.

usage: python3.12 -I tools/tour/gate_fb16.py <folder> <manifest> <truth> <finish tools> <fb16 tools>
         [--frame <id>] [--plate <file>] [--box <json with frame_box>]
"""
import json
import os
import sys

import numpy as np

folder, manifest_rel, truth_rel, finish_dir, fb16_dir = sys.argv[1:6]
opt = dict(zip(sys.argv[6::2], sys.argv[7::2]))
sys.path.insert(0, finish_dir)
sys.path.insert(0, fb16_dir)
import finish as F  # noqa: E402
from fb16 import apply_grade, screen  # noqa: E402

man_path = os.path.join(folder, manifest_rel)
mdir = os.path.dirname(man_path)
m = json.load(open(man_path))
frames = m["fb16"]["frames"]
fid = opt.get("--frame") or (next(iter(frames)) if len(frames) == 1 else None)
if fid not in frames:
    sys.exit(f"gate_fb16: no fb16 frame {fid} in {manifest_rel} ({', '.join(frames)})")
fr = frames[fid]
frame = opt.get("--frame") if any("frame" in x for x in m["layers"]) else None


def here(x):
    return (not frame or x.get("frame", frame) == frame) and not x.get("retired")


def path(f):
    for p in (os.path.join(folder, f), os.path.join(mdir, f)):
        if os.path.exists(p):
            return p
    rest = f.split("/", 1)[1] if f.startswith(m.get("style", "warm-modern") + "/") else f
    return os.path.join(folder, rest.split("/", 1)[1] if rest.startswith(os.path.basename(os.path.normpath(folder)) + "/") else rest)


rows = [(i, x) for i, x in enumerate(m["layers"]) if here(x) and x.get("default", True) is not False]
rows.sort(key=lambda r: (r[1]["z"], r[1].get("sub", 0), r[0]))
layers = [(F.rd(path(x["layer"]), "RGBA"), F.rd(path(x["shadow"]), "RGB")) for _, x in rows]
lights = [F.rd(path(x["file"]), "RGB") for x in (m["light"] if isinstance(m["light"], list) else [m["light"]]) if here(x)]
base = F.rd(os.path.join(folder, opt["--plate"]), "RGB")
comp = apply_grade(F.compose(base, layers, lights), fr["grade"])
for g in fr["glows"]:
    q = F.rd(os.path.join(mdir, g["file"]), "RGB").astype(np.float64) / 255.0
    comp = np.clip(np.rint(comp.astype(np.float64) * q), 0, 255).astype(np.uint8) if g["blend"] == "multiply" else screen(comp, q)
truth = F.rd(os.path.join(folder, truth_rel), "RGB")
if truth.shape != comp.shape:
    box = json.load(open(os.path.join(folder, opt["--box"])))["frame_box"] if "--box" in opt else m["frame_box"]
    comp = F.frame_view(comp, {"frame_box": box}, (truth.shape[1], truth.shape[0]))
d = np.abs(comp.astype(np.int16) - truth.astype(np.int16))
print(json.dumps({"frame": fid, "max": int(d.max()), "mean": round(float(d.mean()), 3), "p99": float(np.percentile(d, 99)),
                  "over8": round(float((d.max(2) > 8).mean()), 5), "differing": int((d > 0).sum()), "values": int(d.size),
                  "size": [int(truth.shape[1]), int(truth.shape[0])]}))
