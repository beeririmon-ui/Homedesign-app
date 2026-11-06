#!/usr/bin/env python3
"""
m0_clay_passes.py: the round-5b M0 clay's object-index / normal / depth passes, for the masks of grading v6 (grade_v6_m0.py;
docs/render-m0-1-2-review-2026-11-05.md section 4: "masks from the clay's object index"). render-agent, 2026-11-05, 0 var2 tokens.
Runs framing_r5b.main for M0 only (1920 px frame, 2036 x 1145 overscan canvas, 1 sample: the passes are not anti-aliased anyway)
with every output redirected to the scratchpad (round5b stays untouched), keeps the passes as .npy and the pass-index names, and
writes the index map onto the still's canvas (2736 x 1539, nearest) as a 16-bit PNG next to the v9 stills:
  assets/renders/living-room/nordic/v9/m0-clay-r5b-index.png + m0-clay-r5b-index.json (index -> name, kind, what it is)
  python3 m0_clay_passes.py render      (Blender's bpy module; ~40 s)
  python3 m0_clay_passes.py write       (the canvas PNG + json from the saved passes)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FRAME = os.environ.get("CLAY_FRAME", "M0")                           # M0 (default) or M0p (2026-11-06)
SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/" + ("m0-pass" if FRAME == "M0" else FRAME.lower() + "-pass")
OUT_PNG = os.path.join(REPO, "assets/renders/living-room/nordic/v9/" + FRAME.lower() + "-clay-r5b-index.png")
# the shell's pass indices are unnamed in the registry; identified by their normals and extents in the pass (2026-11-05)
SHELL = {0: ("glass / sky (no surface)", "glass"), 4: ("window frame and sashes", "window"), 5: ("back wall (normal +Y)", "back_wall"),
         6: ("window wall (normal +X)", "window_wall"), 7: ("right wall (normal -X; M0p)", "right_wall"), 8: ("floor (normal +Z)", "floor"), 9: ("ceiling (normal -Z)", "ceiling"),
         11: ("skirting", "skirting"), 12: ("window sill", "window"), 13: ("cornice", "cornice"), 14: ("window reveal", "window"),
         34: ("curtains", "product"), 41: ("throw (sofa-cover)", "product"), 42: ("cushions", "product"), 43: ("table runner", "product"),
         45: ("candle holders", "product")}


def render():
    os.makedirs(os.path.join(SP, "out", "poses"), exist_ok=True)
    os.environ["FRAMING_R2_OUT"] = os.path.join(SP, "out")
    sys.path.insert(0, os.path.join(REPO, "assets/blockout/house"))
    import framing_r5b as R5
    r3, fr, r2 = R5.r3, R5.fr, R5.r2
    r3.set_out(os.path.join(SP, "out"))
    for m_ in (r2, fr):
        if hasattr(m_, "OUT"):
            m_.OUT = os.path.join(SP, "out")
    _render, _run, state = fr.render, r3.run_frame, {}

    def render_w(path, tmp, res, samples, ao=0.30, passes=True, exposure=None):
        out = _render(path, tmp, res, samples, ao=ao, passes=passes, exposure=exposure)
        if out is not None:
            d, i, n = out
            np.save(os.path.join(SP, "depth.npy"), d.astype(np.float32))
            np.save(os.path.join(SP, "index.npy"), i.astype(np.int32))
            np.save(os.path.join(SP, "normal.npy"), n.astype(np.float32))
            if state.get("S") is not None:
                nm = r2.names_by_pidx(state["S"])
                json.dump({str(k): list(v) for k, v in nm.items()}, open(os.path.join(SP, "names.json"), "w"), indent=1)
        return out

    def run_w(fid, fplan, S, *a, **k):
        state["S"] = S
        return _run(fid, fplan, S, *a, **k)

    fr.render, r3.run_frame = render_w, run_w
    os.makedirs(SP, exist_ok=True)
    R5.main(["--frames", FRAME, "--res", "1920", "--samples", "1", "--pose-samples", "1", "--out", os.path.join(SP, "out"), "--exr", os.path.join(SP, "exr")])


def write():
    import cv2
    idx = np.load(os.path.join(SP, "index.npy"))
    nm = json.load(open(os.path.join(SP, "names.json")))
    I = cv2.resize(idx.astype(np.uint16), (2736, 1539), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(OUT_PNG, I)
    names = {}
    for k in np.unique(I):
        k = int(k)
        if str(k) in nm:
            names[k] = dict(name=nm[str(k)][0], kind="product" if nm[str(k)][1] in ("proxy", "furniture") else nm[str(k)][1], registry=nm[str(k)][1])
        elif k in SHELL:
            names[k] = dict(name=SHELL[k][0], kind=SHELL[k][1], registry="unnamed (identified by normal and extent)")
        else:
            names[k] = dict(name="unknown", kind="product", registry="unnamed")
    json.dump(dict(what=f"round-5b {FRAME} clay object index on the 2736 x 1539 canvas (nearest), from framing_r5b at 2036 x 1145, 1 sample; "
                        "m0_clay_passes.py, render-agent 2026-11-05", clay="assets/blockout/house/framing/round5b/" + ("M0.png" if FRAME == "M0" else f"poses/{FRAME}.png"), classes=names),
              open(OUT_PNG.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(OUT_PNG, sorted(names))


if __name__ == "__main__":
    {"render": render, "write": write}[sys.argv[1]]()
