#!/usr/bin/env python3
"""
tone_r4 with FIXED post values for the round-5 living clays (render-agent, 2026-11-03; 0 var2 tokens): M0, M0p, M0x and the M0-pouf
measurement clay get the exposure and shoulder that round 4 recorded for group M0 (framing/round4/selfcheck.json frames.M0.post:
exposure solved on the back wall by the corner, the "+1 stop" of the brief), instead of re-solving them on the new camera, so the
new clays match the round-4 light everywhere (same scene, same light; only the camera moved). tone_r4.py is imported, not changed;
round4/selfcheck.json is not touched: the readings go to framing/round5/selfcheck.json (merged with selfcheck-render-A.json).
The readings include the Bible 1.8 (BIB1 B1) points that framing_r5.py adds to the wall patches: back wall by the corner
(-1.75, 0, 1.60) [L 90-94] and the window wall (-2.30, 0.30, 1.60) [L 80-88].

  python3 tone_r5_fixed.py --frames M0,M0p,M0x,M0-pouf --exr <scratch>/r5-exr --out framing/round5
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
ap.add_argument("--frames", default="M0,M0p,M0x,M0-pouf")
ap.add_argument("--exr", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--group", default="M0")
a = ap.parse_args()

sc4 = json.load(open(os.path.join(T.R4, "selfcheck.json")))
ref = T.GROUPS[a.group]["ref"]
post = sc4["frames"][ref]["post"]
e, gains = post["exposure"], tuple(post["wb_gains"]) if post.get("wb_gains") else None
plan = json.load(open(os.path.join(a.out, "plan.json")))
rsc = json.load(open(os.path.join(a.out, "selfcheck-render-A.json"))).get("frames", {})
outp = os.path.join(a.out, "selfcheck.json")
out = json.load(open(outp)) if os.path.exists(outp) else {"frames": {}}
toner = T.Toner()
for fid in a.frames.split(","):
    img, lin = toner.load(os.path.join(a.exr, f"{fid}.exr"))
    raw = toner.tone(img, lin, 1.35)
    t = toner.tone(img, lin, e, gains)
    final = T.shoulder(t)
    import bpy
    bpy.data.images.remove(img)
    is_pose = fid in plan["poses"]
    dst = os.path.join(a.out, "poses" if is_pose else "", f"{fid}.png")
    T.save_png(final, dst)
    wp = {}
    for k, q in (rsc.get(fid, {}).get("wall_patches") or {}).items():
        if isinstance(q, dict) and "u" in q and "L_hsl" in q:
            lf = round(T.L_hsl(T.patch(final, q["u"], q["v"])), 1)
            wp[k] = dict(u=q["u"], v=q["v"], xyz=q.get("xyz"), L_render=round(T.L_hsl(T.patch(raw, q["u"], q["v"])), 1), L_final=lf, L_hsl=lf)
    Lmap = (final.max(2) + final.min(2)) / 2 * 100
    wins = {}
    for k, b in (rsc.get(fid, {}).get("boxes") or {}).items():
        if k.lower().startswith("window") or "glass" in k.lower():
            H, W = Lmap.shape
            bb = b["box"]
            sub = Lmap[int(bb[2] * H):int(bb[3] * H), int(bb[0] * W):int(bb[1] * W)]
            if sub.size > 100:
                wins[k] = dict(p99=round(float(np.percentile(sub, 99)), 1), mean=round(float(sub.mean()), 1))
    R = dict(group=a.group, exposure_group_ref=ref, source="tone_r5_fixed.py: the round-4 post of group M0 applied as recorded (no re-solve)",
             exposure=e, exposure_vs_round3_stops=round(e - 0.35, 3), wb_gains=list(gains) if gains else None, shoulder=post["shoulder"],
             render_exposure=1.35, image=os.path.relpath(dst, HERE), pose=is_pose, camera=rsc.get(fid, {}).get("camera"),
             wall_patches=wp, window_p99=wins, p99_L_frame=round(float(np.percentile(Lmap, 99)), 1), max_L_frame=round(float(Lmap.max()), 1),
             mean_L_hsl=round(float(Lmap.mean()), 1), round4_M0_mean_L_hsl=sc4["frames"]["M0"]["post"].get("mean_L_hsl"),
             round4_M0_reference_L_final=sc4["frames"]["M0"]["post"].get("reference_L_final"))
    R["glass_rolloff_pass"] = bool(all(w["p99"] <= 97 for w in wins.values()) and R["p99_L_frame"] <= 97.5)
    out["frames"][fid] = {**{k: v for k, v in rsc.get(fid, {}).items() if k not in ("wall_patches", "image")}, "image": R["image"],
                          "wall_patches_render": rsc.get(fid, {}).get("wall_patches"), "wall_patches": wp, "post": R}
    print(fid, "exp", e, "p99", R["p99_L_frame"], "mean", R["mean_L_hsl"], "(round 4 M0", R["round4_M0_mean_L_hsl"], ") windows", {k: v["p99"] for k, v in wins.items()},
          "bible18", {k: v["L_final"] for k, v in wp.items() if k.startswith("bible18")}, flush=True)
out["stage"] = ("round 5 clays (M0 1.2.1: M0, M0p, M0x + M0-pouf measurement), 2026-11-03, round-4 M0 group post applied as recorded; "
                "briefs/render-m0-new-camera-2026-11-03.md task 2")
out["tone"] = "tone_r5_fixed.py: round-4 group M0 exposure (+1 stop trim) -> AgX MHC -> tanh shoulder; no white balance"
out["round5"] = json.load(open(os.path.join(a.out, "selfcheck-render-A.json"))).get("round5")
json.dump(out, open(outp, "w"), indent=1, ensure_ascii=False)
