#!/usr/bin/env python3
"""
recompose_cb0_v3.py: CB-0 recomposed from B1 r3 fix3 (QA qa/reports/2026-11-04-m0-fix2-cb0-g1.md §5 / §8; the coordinator's message of
2026-11-05). render-agent, 0 var2 tokens. New files only (pose-cb-0-v7-b1r3f3*); recompose_cb0.py and its b1r3 files are kept.

Changes against the b1r3 recompose:
  - the source is b1-v7-r3-fix3.png (the two lumps right of the fern gone);
  - the part of CB-0 that B1 does not see is larger than the left strip: B1's canvas, turned 22 deg, misses an upper and a lower wedge
    too (QA's source map). The whole kept part (left strip + both wedges) is matched to B1 by a smooth per-channel gain FIELD: the
    log-ratio low-pass(B1) / low-pass(old CB-0) read on the plain surfaces 20-260 px inside B1's coverage (both stills smooth there,
    the ratio within 0.12 of its median), extended over the kept part as a membrane (harmonic: no step at the coverage edge, smooth
    beyond it); the fix2 recompose matched by rows only, read on the left wall, which left the upper wedge warm and light;
  - the seam: smootherstep over 150 px (was 60);
  - grading v5 on B1 fix3's stops, the reference read where B1's own reference point (canvas uv 0.419, 0.174 of B1) lands in CB-0 (the
    b1r3 record read the dark wall left of the window at CB-0's (0.419, 0.174): 79.3, and called it a pass; that was wrong).
  python3 recompose_cb0_v3.py build | grade | check | seam | all
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import recompose_cb0 as RC  # noqa: E402
import fix_v7 as F  # noqa: E402
import fix_m0_12 as M  # noqa: E402

pr, VF, REPO = RC.pr, RC.VF, RC.REPO
DATE = "2026-11-05"
SCRIPT = "assets/renders/house-nordic-v7-2026-11-02/recompose_cb0_v3.py"
B1_ID, CB_ID = RC.B1_ID, RC.CB_ID
B1_FIX = os.path.join(VF.out_dir(B1_ID), B1_ID + "-fix3.png")
CB_OLD = RC.CB_OLD
TAG = "-b1r3f3"
CB_NEW = os.path.join(VF.out_dir(CB_ID), CB_ID + TAG + ".png")
SEAM_PX = 150
B1_REF_CANVAS_UV = (0.419, 0.174)


def b1_point_in_cb0(W, H):
    Hm = pr.homography(RC.canvas_cam(RC.CAM_B1), W, H, RC.canvas_cam(RC.CAM_CB0), W, H)
    p = Hm @ np.array([B1_REF_CANVAS_UV[0] * W - 0.5, B1_REF_CANVAS_UV[1] * H - 0.5, 1.0])
    return (float((p[0] / p[2] + 0.5) / W), float((p[1] / p[2] + 0.5) / H))


def energy(img, s=2.0):
    g = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), 1.5)
    return np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), s))


def build():
    b1 = F.load(B1_FIX) / 255.0
    old = F.load(CB_OLD) / 255.0
    H, W = old.shape[:2]
    wa, ca = pr.warp(b1.astype(np.float32), RC.canvas_cam(RC.CAM_B1), RC.canvas_cam(RC.CAM_CB0), W, H)
    full = (ca > 0.999).astype(np.uint8)
    dist = cv2.distanceTransform(full, cv2.DIST_L2, 5)
    # the gain field
    lw = cv2.GaussianBlur(wa, (0, 0), 6.0)
    lo = cv2.GaussianBlur(old.astype(np.float32), (0, 0), 6.0)
    logr = np.log(np.maximum(lw, 1e-3)) - np.log(np.maximum(lo, 1e-3))
    band = (dist >= 20) & (dist <= 260)
    smooth = (energy(wa) < 2.0) & (energy(old) < 2.0)
    known = band & smooth
    med = np.median(logr[known], 0)
    known &= (np.abs(logr - med).max(2) < 0.12)
    kept = dist < 20
    hole = (~known).astype(np.float32)
    # (rows / columns far from the band are as unknown as the kept part: one membrane over the whole canvas, fixed on the known band)
    field = M.laplace_fill(logr.astype(np.float32), hole, np.ones((H, W), np.float32), pad=0)
    field = cv2.GaussianBlur(field, (0, 0), 3.0)
    gain = np.exp(np.clip(field, np.log(0.7), np.log(1.4)))
    old_m = np.clip(old * gain, 0, 1)
    t = np.clip(dist / SEAM_PX, 0, 1)
    w = t * t * t * (t * (t * 6 - 15) + 10)
    out = w[..., None] * wa + (1 - w[..., None]) * old_m
    F.save(out * 255.0, CB_NEW)
    # the kept part's extent (rows / columns), for the record
    keptA = (full == 0)
    rows_top = [int(y) for y in range(H) if keptA[y].sum() > 0.6 * W]
    rec = dict(asset_id=CB_ID + TAG, date=DATE, tokens=0, script=SCRIPT,
               what="CB-0 recomposed from B1 r3 fix3 (reprojection, a pure 22 deg pan about the camera point CB), the part B1 does not see matched by a gain field",
               sources=dict(b1=os.path.relpath(B1_FIX, REPO), cb0_kept=os.path.relpath(CB_OLD, REPO)),
               cameras=dict(B1=dict(yaw=-22, u0=0.52, v0=0.46), CB0=dict(yaw=0, u0=0.50, v0=0.46), lens="24 mm", canvas_overscan_px=[116, 65]),
               kept_part=dict(share_of_canvas=round(float(keptA.mean()), 4),
                              note="the left strip (canvas u < ~0.30 at mid height) and an upper and a lower wedge (B1's canvas turned 22 deg misses the corners)"),
               gain_field=dict(known_px=int(known.sum()), median_log_ratio_rgb=[round(float(x), 4) for x in med],
                               gain_median_in_kept_rgb=[round(float(x), 4) for x in np.median(gain[kept], 0)],
                               gain_range_in_kept=[round(float(gain[kept].min()), 3), round(float(gain[kept].max()), 3)],
                               how="log(low-pass B1 / low-pass old CB-0), sigma 6, on plain surfaces (high-pass energy < 2 in both) 20-260 px inside B1's coverage, "
                                   "within 0.12 of the median; extended over the rest by a membrane (fix_m0_12.laplace_fill), blurred 3 px, clipped 0.7-1.4"),
               seam=f"smootherstep over {SEAM_PX} px inside B1's coverage", output=os.path.relpath(CB_NEW, REPO))
    json.dump(rec, open(CB_NEW.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(rec["gain_field"]))
    return rec


def grade():
    import process_v8 as P
    m = json.load(open(os.path.join(VF.out_dir(B1_ID), B1_ID + "-measurements-fix3-v5.json")))
    stops = m["grade"]["exposure"]["applied_stops"]
    hue_force = True if m["grade"].get("wall_hue_v4", {}).get("applied") else None
    a = F.load(CB_NEW)
    pt = b1_point_in_cb0(a.shape[1], a.shape[0])
    P.CB0_WALL_V4 = pt                       # this call only: the reference where B1's own point lands (process_v8 is not edited)
    r = P.process(CB_ID, CB_NEW, TAG + "-v5", "v2", "auto", "none", None, "CB-0 recomposed from B1 r3 fix3, grading v5 on B1 fix3's stops",
                  exposure="bible", stops=stops, grade_mode="v5", hue_force=hue_force)
    b = r["bible_v3"]
    lo, hi = b["range"]
    wr = b.get("wall_v4", {}).get("reading", {})
    own_ok = bool(lo - 0.5 <= b["measured_L"] <= hi + 0.5)
    b1_ok = bool(m["bible_v3"]["meets_target"])
    others = [k for k, v in r["checks"].items() if k.startswith("bible_") and v is False]
    verdict = dict(reference_point_canvas_uv=[round(pt[0], 4), round(pt[1], 4)],
                   reference_note="B1's reference point (B1 canvas uv 0.419, 0.174 = the wall beside the fluted window) projected into CB-0",
                   L=b["measured_L"], range=[lo, hi], H=wr.get("H"), C_star=wr.get("C_star"), stops=stops, stops_from="b1-v7-r3 fix3 (v5)",
                   target_by_group_reference=b1_ok, target_at_own_point=own_ok, other_bible_checks_failed=others,
                   meets_bible_1_8_4=bool(b1_ok and own_ok and not others),
                   correction_of_the_b1r3_record=("pose-cb-0-v7-b1r3.json said 'reading 79.3, meets_bible true': 79.3 was the dark wall left of the window "
                                                  "at CB-0's own (0.419, 0.174), outside 86-90, and the pass came from the inherited stops only (meets_target None)"))
    rec = json.load(open(CB_NEW.replace(".png", ".json")))
    rec["grade_v5"] = dict(verdict, outputs=r["outputs"])
    json.dump(rec, open(CB_NEW.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(verdict))
    return r


def frame_of(p):
    a = F.load(p) / 255.0
    H, W = a.shape[:2]
    x0, y0, x1, y1 = VF.frame_box_px(W, H)
    return a[y0:y1, x0:x1].astype(np.float32)


def check():
    od_b, od_c = VF.out_dir(B1_ID), VF.out_dir(CB_ID)
    B = frame_of(os.path.join(od_b, B1_ID + "-graded-fix3-v5.png"))
    C = frame_of(os.path.join(od_c, CB_ID + "-graded" + TAG + "-v5.png"))
    r = pr.overlap_check(B, RC.CAM_B1, C, RC.CAM_CB0, 1920, 1080, os.path.join(od_c, CB_ID + TAG + "-overlap.jpg"))
    bands = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"]]
    rel = [max(abs(x["dx_px"]), abs(x["dy_px"])) for x in r["bands"] if x["response"] >= 0.05]
    r.update(worst_band_px=round(max(bands), 2), worst_band_px_reliable=(round(max(rel), 2) if rel else None), bands_reliable=len(rel),
             dL_mean=round(abs(r["L_mean"]["a"] - r["L_mean"]["b"]), 2),
             passes=bool(rel and max(rel) <= 2.0 and abs(r["L_mean"]["a"] - r["L_mean"]["b"]) <= 1.0))
    out = dict(date=DATE, tokens=0, script=SCRIPT, rule="QA G1.14: overlap_check B1 -> CB-0 (22 deg), bands with response >= 0.05 <= 2 px, dL <= 1",
               b1=os.path.relpath(os.path.join(od_b, B1_ID + "-graded-fix3-v5.png"), REPO), cb0=os.path.relpath(os.path.join(od_c, CB_ID + "-graded" + TAG + "-v5.png"), REPO),
               result=r)
    json.dump(out, open(os.path.join(od_c, CB_ID + TAG + "-overlap.json"), "w"), indent=1, ensure_ascii=False)
    print("bands", [(x["dx_px"], x["dy_px"], x["response"]) for x in r["bands"]], "worst", r["worst_band_px_reliable"], "dL", r["dL_mean"], "pass", r["passes"])
    return out


def seam():
    """The seam on the graded stills: CIELAB of the kept part's upper wedge vs the B1 wall right under it, and the vertical seam on the
    plain left wall (the L* residual from a smooth wall gradient across the transition)."""
    import process_v8 as P
    od_c = VF.out_dir(CB_ID)
    res = {}
    for nm, tag in (("b1r3 (fix2 recompose)", "-b1r3"), ("b1r3f3 (this)", TAG)):
        g = F.load(os.path.join(od_c, CB_ID + "-graded" + tag + "-v5.png")) / 255.0
        H, W = g.shape[:2]
        lab = P.lab_arr(g)
        ca = pr.warp(np.ones((H, W, 3), np.float32), RC.canvas_cam(RC.CAM_B1), RC.canvas_cam(RC.CAM_CB0), W, H)[1]
        full = (ca > 0.999).astype(np.uint8)
        din = cv2.distanceTransform(full, cv2.DIST_L2, 5)
        dout = cv2.distanceTransform(1 - full, cv2.DIST_L2, 5)
        en = energy(g) < 2.5
        steps = []
        sd = din - dout                       # signed distance to the coverage edge (+ inside B1's part)
        Ls = cv2.GaussianBlur(lab[..., 0].astype(np.float32), (0, 0), 2.0)
        for y in range(int(0.20 * H), int(0.85 * H), 10):
            xs = np.nonzero((sd[y] >= -40) & (sd[y] <= 190))[0]
            if len(xs) < 200 or not en[y, xs].all():
                continue                      # only rows where the whole span is plain wall
            t = sd[y, xs]
            a0 = Ls[y, xs][t <= -30].mean()
            a1 = Ls[y, xs][t >= 180].mean()
            lin = a0 + (a1 - a0) * (t + 35) / 220.0
            res_ = Ls[y, xs] - lin
            steps.append((y, round(float(np.abs(res_).max()), 2), round(float(a1 - a0), 2)))
        wedge = (full == 0) & (np.arange(H)[:, None] < int(0.10 * H)) & (np.arange(W)[None, :] > int(0.32 * W)) & en
        under = (din >= 40) & (din <= 120) & (np.arange(H)[:, None] < int(0.16 * H)) & (np.arange(W)[None, :] > int(0.32 * W)) & en
        wd = (lab[wedge].mean(0) - lab[under].mean(0)) if wedge.sum() > 100 and under.sum() > 100 else None
        res[nm] = dict(vertical_seam_dL_star_max=(max(s_[1] for s_ in steps) if steps else None),
                       vertical_seam_dL_star_median=(round(float(np.median([s_[1] for s_ in steps])), 2) if steps else None),
                       vertical_seam_dL_star_p75=(round(float(np.percentile([s_[1] for s_ in steps], 75)), 2) if steps else None),
                       note_max="the max comes from rows whose span crosses an edge the energy gate misses (door jamb, WC block); median / p75 are the wall",
                       wall_gradient_across_dL_star=(round(float(np.median([s_[2] for s_ in steps])), 2) if steps else None), rows=len(steps),
                       vertical_seam_how="rows where the span -40..+190 px across the coverage edge is plain wall: L* (blurred 2 px) minus the straight line "
                                         "between its ends (the wall's own gradient); the max |residual| = the step the seam adds",
                       upper_wedge_vs_B1_wall=(dict(dL=round(float(wd[0]), 2), da=round(float(wd[1]), 2), db=round(float(wd[2]), 2),
                                                    dE=round(float(np.sqrt((wd ** 2).sum())), 2)) if wd is not None else None))
    rec = json.load(open(CB_NEW.replace(".png", ".json")))
    rec["seam_check"] = res
    json.dump(rec, open(CB_NEW.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    if w in ("build", "all"):
        build()
    if w in ("grade", "all"):
        grade()
    if w in ("check", "all"):
        check()
    if w in ("seam", "all"):
        seam()


def lock():
    import lock_v2 as L
    import lock_fixes_v8 as LF
    od = VF.out_dir(CB_ID)
    rep = L.run_frame(CB_ID, render_path=CB_NEW, out_path=os.path.join(od, CB_ID + TAG + "-lock-v2.json"),
                      overlay_path=os.path.join(od, CB_ID + TAG + "-lock-v2.jpg"), edges_mode="v3", date=DATE)
    rec = json.load(open(CB_NEW.replace(".png", ".json")))
    rec["lock_v2"] = dict(LF.brief(rep), record=os.path.relpath(os.path.join(od, CB_ID + TAG + "-lock-v2.json"), REPO),
                          note="the round-4 CB-0 clay has no planter / brush / curtain-hem proxies (QA: no r3 clay of CB-0 exists)")
    json.dump(rec, open(CB_NEW.replace(".png", ".json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: rec["lock_v2"][k] for k in ("register_shift_px", "register_scale_pct", "worst_band_px_after_register", "worst_tile_px_after_register",
                                                     "named_edges_worst_px", "named_edges_counted", "pass")}))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "lock":
    lock()
