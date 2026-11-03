#!/usr/bin/env python3
"""
tone_r4 with FIXED post values (render-agent, 2026-11-03; 0 var2 tokens): the bath r3 clays (framing_r4_bath_r3.py) get the
exposure, white-balance gains and shoulder that round 4 recorded for group CB (framing/round4/selfcheck.json frames.B1.post:
exposure 0.885, wb_gains [0.7135, 1.0179, 1.6659]), instead of re-solving them on the new render, so the new B1 / B2 clays match
the round-4 ones everywhere except the two added placeholders. tone_r4.py is imported, not changed; round4/selfcheck.json is not
touched: the readings go to <out>/selfcheck.json.

  python3 tone_r4_fixed.py --frames B1,B2 --exr <dir with B1.exr, B2.exr> --out framing/round4/r3-2026-11-03
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tone_r4 as T  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--frames", default="B1,B2")
ap.add_argument("--exr", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--group", default="CB")
a = ap.parse_args()

sc4 = json.load(open(os.path.join(T.R4, "selfcheck.json")))
ref = T.GROUPS[a.group]["ref"]
post = sc4["frames"][ref]["post"]
e, gains = post["exposure"], tuple(post["wb_gains"]) if post.get("wb_gains") else None
rsc = json.load(open(os.path.join(a.out, "selfcheck-render-A.json"))).get("frames", {})
outp = os.path.join(a.out, "selfcheck.json")
out = json.load(open(outp)) if os.path.exists(outp) else {"frames": {}}
toner = T.Toner()
for fid in a.frames.split(","):
    img, lin = toner.load(os.path.join(a.exr, f"{fid}.exr"))
    t = toner.tone(img, lin, e, gains)
    final = T.shoulder(t)
    import bpy
    bpy.data.images.remove(img)
    dst = os.path.join(a.out, f"{fid}.png")
    T.save_png(final, dst)
    wp = {}
    for k, q in (rsc.get(fid, {}).get("wall_patches") or {}).items():
        if isinstance(q, dict) and "u" in q and "L_hsl" in q:
            wp[k] = dict(u=q["u"], v=q["v"], xyz=q.get("xyz"), L_final=round(T.L_hsl(T.patch(final, q["u"], q["v"])), 1))
    u, v = post["reference_uv"]
    wp[f"reference_{a.group}"] = dict(u=u, v=v, L_final=round(T.L_hsl(T.patch(final, u, v)), 1), target=post["target_L"],
                                      round4_L_final=sc4["frames"][fid]["wall_patches"].get(f"reference_{a.group}", {}).get("L_hsl"))
    Lmap = (final.max(2) + final.min(2)) / 2 * 100
    R = dict(group=a.group, source="tone_r4_fixed.py: the round-4 post of group CB applied as recorded (no re-solve)", exposure=e,
             wb_gains=list(gains) if gains else None, shoulder=post["shoulder"], render_exposure=1.35, image=os.path.relpath(dst, HERE),
             wall_patches=wp, p99_L_frame=round(float(np.percentile(Lmap, 99)), 1), max_L_frame=round(float(Lmap.max()), 1),
             mean_L_hsl=round(float(Lmap.mean()), 1), round4_mean_L_hsl=sc4["frames"][fid]["post"].get("mean_L_hsl"))
    out["frames"][fid] = {**{k: v for k, v in rsc.get(fid, {}).items() if k not in ("image",)}, "image": R["image"], "post": R}
    print(fid, "exp", e, "gains", gains, "ref L", wp[f"reference_{a.group}"], "p99", R["p99_L_frame"], "mean", R["mean_L_hsl"], "(round 4", R["round4_mean_L_hsl"], ")")
out["stage"] = "bath r3 clays (B1 + floor planter + toilet brush; B2 + floor planter), 2026-11-03, round-4 post applied as recorded"
json.dump(out, open(outp, "w"), indent=1, ensure_ascii=False)
