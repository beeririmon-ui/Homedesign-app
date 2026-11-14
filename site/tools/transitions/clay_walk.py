#!/usr/bin/env python3
"""
clay_walk.py: a real clay walk along a straight move of the arrival, rendered with render-agent's entrance clay
(assets/blockout/house/framing_wm_entrance.py, imported, not changed), at any list of distances. 0 var2 tokens.

It is the test clip the transition tools are checked on before a model clip exists (the plan: "a correct walk from
the clay, and a plain dissolve between the two stills"), and the frames of the clay animatic. The camera of every
frame is the route's own (camgeo), so the frames sit exactly where the walk test and the assembly expect them.

  blender-python:  python3 clay_walk.py --route clip2 --s 0,0.06,0.15,... --res 960 --samples 4 --out DIR
                   python3 clay_walk.py --route clip2 --uneven 41 --res 960 --samples 4 --out DIR   # a model-like uneven walk
Writes DIR/W00.png ..., with -depth.png / -edges.png / -id.png passes (render-agent's conventions) and DIR/walk.json
(the distance of every frame). Routes with clay today: clip2 (HDx -> M0) and t-e0 (H0x -> M0); clip1 needs the door
clay (assets/blockout/house/framing/wm-door-2026-11-14/), which is not built yet.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CLAY = os.path.join(REPO, "assets", "blockout", "house")


def parse(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--route", default="clip2", choices=["clip2", "t-e0"])
    ap.add_argument("--s", help="comma list of distances (metres from the route's first camera)")
    ap.add_argument("--uneven", type=int, help="n frames at a model-like uneven speed over the whole route")
    ap.add_argument("--res", type=int, default=960)
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--out", required=True)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = parse(sys.argv[1:] if argv is None else argv)
    sys.path.insert(0, HERE)
    import camgeo as cg  # noqa: E402
    c0, c1 = {"clip2": (cg.HDX, cg.M0), "t-e0": (cg.H0X, cg.M0)}[a.route]
    L = math.dist(c0.loc, c1.loc)
    if a.uneven:
        import numpy as np
        ts = np.linspace(0, 1, a.uneven)
        prog = np.clip(np.maximum.accumulate(ts + 0.10 * np.sin(2 * np.pi * ts) * (1 - ts)), 0, 1)
        prog[-1] = 1.0
        svals = [float(p * L) for p in prog]
    else:
        svals = [float(x) for x in a.s.split(",")]
    os.environ.setdefault("WM_ENTRANCE_SCRATCH", os.path.join(os.path.abspath(a.out), "_scratch"))
    sys.path.insert(0, CLAY)
    import framing_wm_entrance as E  # noqa: E402  (imports bpy and builds nothing until main)

    orig = E.plan_frames

    def frames():
        F, alias, info = orig()
        for k, s in enumerate(svals):
            cam = cg.lerp_cam(c0, c1, s / L)
            F[f"W{k:02d}"] = dict(loc=[float(x) for x in cam.loc], yaw=cam.yaw, u0=cam.u0, v0=cam.v0, s=s,
                                  src=f"clay_walk.py {a.route} at {s:.4f} m (motion-agent test clip)")
        return F, {}, info

    E.plan_frames = frames
    ids = [f"W{k:02d}" for k in range(len(svals))]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "walk.json"), "w") as fh:
        json.dump(dict(route=a.route, length_m=L, s=svals, ids=ids, res=a.res, samples=a.samples,
                       clay="assets/blockout/house/framing_wm_entrance.py (render-agent), as imported on this date"), fh, indent=1)
    E.main(["--frames", ",".join(ids), "--res", str(a.res), "--samples", str(a.samples), "--out", a.out])
    return 0


if __name__ == "__main__":
    sys.exit(main())
