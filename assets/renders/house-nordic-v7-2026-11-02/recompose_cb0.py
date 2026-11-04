#!/usr/bin/env python3
"""
CB-0 recomposed from the B1 r3 cleanup (briefs/render-m0-composite-and-cleanup-2026-11-04.md task 4; QA 2026-11-04 §§ 1, 6: today's
CB-0 is the v7 composite, 19.4 px / dL 14.2 against B1 r3 fix). render-agent, 2026-11-04, 0 var2 tokens. New files only.

CB-0 and B1 share the camera point CB (house plan: (3.80, 13.20, 1.15), 24 mm): B1 yaw -22 u0 0.52 v0 0.46, CB-0 yaw 0 u0 0.50 v0 0.46
(round-4 plan poses.CB-0). A pure rotation, so pan_reproject.warp (the homography of the same centre of projection) carries the B1
still into CB-0 exactly; the part of CB-0 that B1 does not see (its left, toward the door) keeps the current CB-0 (pose-cb-0-v7.png),
blended over a 60 px band inside B1's coverage. Both canvases are the overscan canvas (4072 x 2290 at 2736 x 1539: the 16:9 frame
plus 116 / 65 px each side), so the cameras get the overscan in u and v (same focal, same principal point).
  build   -> assets/renders/poses/nordic/v7/pose-cb-0-v7-b1r3.png (+ .json), the raw composite
  grade   -> process_v8 --grade v5 on it with B1 r3 fix2's stops (one exposure per camera point, as B2 / CB-0 group CB):
             pose-cb-0-v7-graded-b1r3-v5.png, -frame-b1r3-v5.png, -measurements-b1r3-v5.json
  check   -> pan_reproject.overlap_check B1 r3 fix2 (graded-fix2-v5) -> CB-0 (graded-b1r3-v5), QA's G1.14 rule: bands with response
             >= 0.05 <= 2 px, dL (mean L of the overlap) <= 1; also the old CB-0 for comparison -> pose-cb-0-v7-b1r3-overlap.json / .jpg
  python3 recompose_cb0.py build | grade | check | all
"""
import json
import os
import sys
from dataclasses import replace

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "site", "tools", "transitions"))
import pan_reproject as pr  # noqa: E402
import v7_frames as VF  # noqa: E402
import fix_v7 as F  # noqa: E402

DATE = "2026-11-04"
B1_ID, CB_ID = "b1-v7-r3", "pose-cb-0-v7"
B1_FIX = os.path.join(VF.out_dir(B1_ID), B1_ID + "-fix2.png")
CB_OLD = os.path.join(VF.out_dir(CB_ID), CB_ID + ".png")
CB_NEW = os.path.join(VF.out_dir(CB_ID), CB_ID + "-b1r3.png")
CAM_B1 = pr.Cam(-22.0, 0.52, 0.46)
CAM_CB0 = pr.Cam(0.0, 0.50, 0.46)
OX, OY = 116 / 3840.0, 65 / 2160.0
SEAM_PX = 60


def canvas_cam(c):
    kx, ky = 1 + 2 * OX, 1 + 2 * OY
    return replace(c, u0=(c.u0 + OX) / kx, v0=(c.v0 + OY) / ky, fx_rel=c.fx_rel / kx, fy_rel=c.fy_rel / ky)


def build():
    b1 = F.load(B1_FIX) / 255.0
    old = F.load(CB_OLD) / 255.0
    H, W = old.shape[:2]
    wa, ca = pr.warp(b1.astype(np.float32), canvas_cam(CAM_B1), canvas_cam(CAM_CB0), W, H)
    full = (ca > 0.999).astype(np.uint8)
    dist = cv2.distanceTransform(full, cv2.DIST_L2, 5)
    t = np.clip(dist / SEAM_PX, 0, 1)
    w = t * t * t * (t * (t * 6 - 15) + 10)                 # smootherstep
    # the old CB-0 (a v7 render) is warmer and darker than B1 r3 on the same left wall: its part is matched to B1 by a per-row, per-channel
    # gain read on the wall just inside B1's coverage (40-160 px from its edge, the left wall in both stills), smoothed along v
    band = (dist >= 40) & (dist <= 160)
    cols = np.nonzero(full.any(0))[0]
    band[:, cols.min() + 200:] = False
    ratio = np.ones((H, 3), np.float32)
    for y in range(H):
        sel = band[y]
        if sel.sum() >= 20:
            ratio[y] = np.median(wa[y, sel], 0) / np.maximum(np.median(old[y, sel], 0), 1e-3)
    ratio = cv2.GaussianBlur(ratio.reshape(H, 1, 3), (1, 0), sigmaX=0.1, sigmaY=40).reshape(H, 3)
    ratio = np.clip(ratio, 0.7, 1.4)
    old_m = np.clip(old * ratio[:, None, :], 0, 1)
    out = w[..., None] * wa + (1 - w[..., None]) * old_m
    F.save(out * 255.0, CB_NEW)
    cols = np.nonzero(full.any(0))[0]
    rec = dict(asset_id=CB_ID + "-b1r3", date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/recompose_cb0.py",
               what="CB-0 recomposed from the B1 r3 cleanup (b1-v7-r3-fix2.png) by reprojection (same centre of projection: a pure 22 deg pan)",
               sources=dict(b1=os.path.relpath(B1_FIX, REPO), cb0_left=os.path.relpath(CB_OLD, REPO)),
               cameras=dict(B1=dict(yaw=-22, u0=0.52, v0=0.46), CB0=dict(yaw=0, u0=0.50, v0=0.46), lens="24 mm (fx_rel 0.6667)", canvas_overscan_px=[116, 65]),
               coverage=dict(b1_covers_canvas_u=[round(cols.min() / W, 4), round(cols.max() / W, 4)], share=round(float(full.mean()), 4),
                             seam=f"smootherstep over {SEAM_PX} px inside B1's coverage; outside it the current CB-0 (v7 composite), "
                                  "matched to B1 by a per-row, per-channel gain read on the left wall 40-160 px inside the coverage (median, smoothed 40 rows)",
                             gain_median_rgb=[round(float(x), 4) for x in np.median(ratio, 0)]),
               output=os.path.relpath(CB_NEW, REPO))
    json.dump(rec, open(CB_NEW.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(rec["coverage"]))
    return rec


def grade():
    import process_v8 as P
    m = json.load(open(os.path.join(VF.out_dir(B1_ID), B1_ID + "-measurements-fix2-v5.json")))
    stops = m["grade"]["exposure"]["applied_stops"]
    hue_force = True if m["grade"].get("wall_hue_v4", {}).get("applied") else None
    r = P.process(CB_ID, CB_NEW, "-b1r3-v5", "v2", "auto", "none", None, "CB-0 recomposed from B1 r3 fix2, grading v5 on B1's stops",
                  exposure="bible", stops=stops, grade_mode="v5", hue_force=hue_force)
    rec = json.load(open(CB_NEW.replace(".png", ".json")))
    rec["grade_v5"] = dict(stops_from=os.path.relpath(os.path.join(VF.out_dir(B1_ID), B1_ID + "-measurements-fix2-v5.json"), REPO), stops=stops,
                           hue_force=hue_force, outputs=r["outputs"], reading=r["bible_v3"].get("measured_L"), meets_bible=r["bible_v3"].get("meets_bible"))
    json.dump(rec, open(CB_NEW.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    return r


def check():
    def frame_of(p):
        a = F.load(p) / 255.0
        H, W = a.shape[:2]
        x0, y0, x1, y1 = VF.frame_box_px(W, H)
        return a[y0:y1, x0:x1].astype(np.float32)
    od_b, od_c = VF.out_dir(B1_ID), VF.out_dir(CB_ID)
    B = frame_of(os.path.join(od_b, B1_ID + "-graded-fix2-v5.png"))
    res = {}
    for nm, p in (("new", os.path.join(od_c, CB_ID + "-graded-b1r3-v5.png")), ("old_v4", os.path.join(od_c, CB_ID + "-graded-v4.png"))):
        C = frame_of(p)
        sheet = os.path.join(od_c, CB_ID + "-b1r3-overlap.jpg") if nm == "new" else None
        r = pr.overlap_check(B, CAM_B1, C, CAM_CB0, 1920, 1080, sheet)
        bands = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"]]
        rel = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"] if x["response"] >= 0.05]
        r.update(worst_band_px=round(max(bands), 2), worst_band_px_reliable=(round(max(rel), 2) if rel else None), bands_reliable=len(rel),
                 dL_mean=round(abs(r["L_mean"]["a"] - r["L_mean"]["b"]), 2),
                 passes=bool(rel and max(rel) <= 2.0 and abs(r["L_mean"]["a"] - r["L_mean"]["b"]) <= 1.0))
        res[nm] = r
        print(nm, "bands", [(x["dx_px"], x["dy_px"], x["response"]) for x in r["bands"]], "reliable worst", r["worst_band_px_reliable"], "dL", r["dL_mean"], "pass", r["passes"])
    out = dict(date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/recompose_cb0.py",
               rule="QA G1.14: pan_reproject.overlap_check in the overlap (B1 -> CB-0, 22 deg), bands with response >= 0.05 <= 2 px, dL <= 1",
               b1=os.path.relpath(os.path.join(od_b, B1_ID + "-graded-fix2-v5.png"), REPO),
               cb0_new=os.path.relpath(os.path.join(od_c, CB_ID + "-graded-b1r3-v5.png"), REPO), results=res)
    json.dump(out, open(os.path.join(od_c, CB_ID + "-b1r3-overlap.json"), "w"), indent=1, ensure_ascii=False)
    return out


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w in ("build", "all"):
        build()
    if w in ("grade", "all"):
        grade()
    if w in ("check", "all"):
        check()
