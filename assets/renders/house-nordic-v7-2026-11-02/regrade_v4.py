#!/usr/bin/env python3
"""
Grading v4 (briefs/render-retakes-code-fixes-2026-11-04.md task 2; QA qa/reports/2026-11-03-retakes-g1.md §4 and §11.2): the
22 kept v7 stills, the four accepted fixes of 2026-11-03 (K-boy, K-girl, W0, K-boy-0) and the four code fixes of 2026-11-04
(B1 r3, B2 r3, K-girl-0 r2, W0-in r2) graded with process_v8.py --grade v4 (the v3 Bible grade + the masked wall-hue
correction when H > 40, C* <= 7 absolute, the window-wall points, C0 on S1''s stops, CB-0 on the white wall).
New files only: <id>-graded-v4.png (+ -frame-v4.png / -graded-os6-v4.png on the overscan canvases), <id>-measurements-v4.json;
the fixes get -graded-fix-v4.png / -frame-fix-v4.png / -graded-os6-fix-v4.png / -measurements-fix-v4.json. No lock run (the
grade does not move edges; <id>-lock-v2.json / -lock-fix.json stay the record). Summary: regrade-v4-summary.json.
render-agent, 2026-11-04, 0 var2 tokens.
  python3 regrade_v4.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import process_v8 as P  # noqa: E402

OLD_FIXES = ["k-boy-v7", "k-girl-v7", "w0-v7", "pose-k-boy-0-v7"]                    # fix_v7.py, 2026-11-03
NEW_FIXES = ["b1-v7-r3", "b2-v7-r3", "pose-k-girl-0-v7-r2", "pose-w0-in-v7-r2"]       # fix_v8.py, 2026-11-04
FIX_BASE = {"b2-v7-r3": "b1-v7-r3", "pose-k-boy-0-v7": "k-boy-v7"}                   # a fix inherits its group reference's fix
BIBLE_NOTE = {"C0": "corridor: no Bible number; G1.8 proposal (hall rule), stops of S1' (QA §4)", "S1prime": "corridor: G1.8 proposal (hall rule), not a Bible number",
              "H0x": "hall wall 2/3 stop under the living (Bible B5)", "H0e": "hall wall 2/3 stop under the living (Bible B5)"}
results, rows = {}, []


def fid_of(frame):
    return next(f for f in VF.FRAMES if VF.FRAMES[f][0] == frame)


def run(fid, fix=False):
    frame = VF.frame(fid)[0]
    render = os.path.join(VF.out_dir(fid), fid + "-fix.png") if fix else None
    suffix = "-fix-v4" if fix else "-v4"
    stops = hue_force = base_id = None
    base_frame = P.INHERIT_STOPS_V4.get(frame)
    if fix and fid in FIX_BASE:
        base_id = FIX_BASE[fid]
        src = results.get((base_id, True))
    elif base_frame:
        base_id = fid_of(base_frame)
        src = results.get((base_id, False))
    else:
        src = None
    if src is not None:
        stops = src["grade"]["exposure"]["applied_stops"]
        hue_force = True if src["grade"].get("wall_hue_v4", {}).get("applied") else None   # corrected reference -> corrected here; else this frame's own H > 40 trigger
    label = "grading v4 (Bible targets + wall hue / C* / window wall, QA §11.2)" + (" on the code fix" if fix else "")
    r = P.process(fid, render, suffix, "v2", "auto", "none", None, label, exposure="bible", stops=stops, grade_mode="v4", hue_force=hue_force)
    results[(fid, fix)] = r
    e, b, m = r["grade"]["exposure"], r["bible_v3"], r["measure_after"]
    wv, wh = b.get("wall_v4", {}), r["grade"].get("wall_hue_v4", {})
    fails = [k for k, v in r["checks"].items() if k.startswith("bible_") and v is False]
    rows.append(dict(
        id=fid, frame=frame, fix=fix, suffix=suffix, inherits=(dict(from_id=base_id, stops=stops, hue_correction=hue_force) if src is not None else None),
        target_L=b["target_L"], range=b["range"], reference=b["reference_source"], reference_uv=b["reference_point"],
        L_reference=b["measured_L"], meets_target=b["meets_target"], target_note=BIBLE_NOTE.get(frame),
        H=wv.get("reading", {}).get("H"), C_star=wv.get("reading", {}).get("C_star"), wall_judged=wv.get("judged"),
        H_after_lift_before_correction=r["grade"].get("wall_after_lift_v4", {}).get("H"), C_after_lift_before_correction=r["grade"].get("wall_after_lift_v4", {}).get("C_star"),
        hue_correction=dict(applied=wh.get("applied"), pixels_touched_pct=wh.get("pixels_touched_pct"), why_not=wh.get("why_not")),
        window_wall=b.get("window_wall"), hall_B5=b.get("hall_under_living_stops"),
        black=m["darkest 0.5% patch L [12-15]"], window_p99=m["brightest area (window / door): L p50 / p99 / max"][1], frame_max=m["frame L p99 / max"][1],
        px255=m["pixels with a 255 channel: inside / outside that area"], stops=e["applied_stops"], needed=e["needed_stops"],
        checks={k: v for k, v in r["checks"].items() if k.startswith("bible_")}, fails=fails, meets_bible_1_8_2=b["meets_bible"],
        outputs=r["outputs"], measurements=os.path.relpath(os.path.join(VF.out_dir(fid), fid + "-measurements" + suffix + ".json"), VF.REPO)))


masters = [f for f in VF.FRAMES if VF.FRAMES[f][1] == "master" and VF.FRAMES[f][0] != "C0"]
poses = [f for f in VF.FRAMES if VF.FRAMES[f][1] == "pose"]
for f in masters:
    run(f)
for f in OLD_FIXES:
    if VF.FRAMES[f][1] == "master":
        run(f, fix=True)
for f in poses:
    run(f)
run(fid_of("C0"))
for f in OLD_FIXES:
    if VF.FRAMES[f][1] == "pose":
        run(f, fix=True)
for f in NEW_FIXES:
    run(f, fix=True)

for r in rows:                      # inherited stops: the target is judged by the group reference (one exposure per camera point)
    if r["meets_target"] is None and r["inherits"]:
        src = next((x for x in rows if x["id"] == r["inherits"]["from_id"] and (x["fix"] == r["fix"] or not x["fix"])), None)
        r["judged_by_reference"] = dict(id=r["inherits"]["from_id"], meets_target=src["meets_target"] if src else None)
        r["meets_bible_1_8_2"] = bool(r["meets_bible_1_8_2"] and (src["meets_target"] if src else False))
        if src and not src["meets_target"]:
            r["fails"].append("bible_target_met (group reference)")
        lo, hi = r["range"]
        if not (lo - 0.5 <= r["L_reference"] <= hi + 0.5):
            r["own_reading_note"] = (f"its own reference point reads L {r['L_reference']} at the inherited stops, outside {lo}-{hi}; the frame is judged by "
                                     f"{r['inherits']['from_id']} (one exposure per group); for C0 the corridor has no Bible number (G1.8 proposal only)")
    if r["wall_judged"] is False:
        r["fails"].append("wall hue / C* not judged (no wall at the reference point)")
        r["meets_bible_1_8_2"] = False
n_ok = sum(1 for r in rows if r["meets_bible_1_8_2"])
from collections import Counter  # noqa: E402
fail_count = Counter(k for r in rows for k in r["fails"])
summary = dict(
    date="2026-11-04", tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/regrade_v4.py (process_v8.py --grade v4)",
    rule=("Bible 1.8.2 light rules (V7Q4 test page; BIB1): reference wall to its target, wall H 32-40 and CIELAB C* <= 7 (B4, absolute) on the "
          "reference wall, the window wall L 80-88 (B1 (2)) where QA reads it (M0, K-boy, K-girl, W0, MB0 and their fixes), black point 12-15, roll-off "
          "last (L <= 97, zero 255), the v3 relative near-white guard (B4), H0's hall 2/3 stop under the vista (B5). The masked wall-hue correction runs "
          "when the wall reads H > 40 after the lift; frames that inherit stops inherit the correction. C0 on S1''s stops; CB-0 on the white wall "
          "beside the window (B1's wall, L 86-90)."),
    frames=len(rows), meet_bible_1_8_2=n_ok, failing_checks=dict(fail_count), rows=rows)
json.dump(summary, open(os.path.join(HERE, "regrade-v4-summary.json"), "w"), indent=1, ensure_ascii=False)
print("\n== grading v4 ==")
for r in rows:
    ww = r["window_wall"]["L"] if r["window_wall"] else "-"
    print(f"{r['id']:20s}{'(fix)' if r['fix'] else '     '} L {r['L_reference']:5.1f} [{r['range'][0]:.1f}-{r['range'][1]:.1f}] H {r['H']} C* {r['C_star']} "
          f"(lift: H {r['H_after_lift_before_correction']} C* {r['C_after_lift_before_correction']}; corr {r['hue_correction']['applied']}) win-wall {ww} | black {r['black']} | "
          f"p99 {r['window_p99']} | {'BIBLE 1.8.2' if r['meets_bible_1_8_2'] else 'fails: ' + ', '.join(r['fails'])}")
print(f"\n{n_ok}/{len(rows)} meet Bible 1.8.2 in full; failing checks: {dict(fail_count)}")
