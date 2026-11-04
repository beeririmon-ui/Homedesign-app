#!/usr/bin/env python3
"""
Grading v5 (briefs/render-m0-composite-and-cleanup-2026-11-04.md task 3; Bible 1.8.4): process_v8.py --grade v5 = v4 plus
  - the living back wall L 90-94 (Bible 1.8 B1 (1)) for M0 / M0p / M0x and H0's vista (v3 / v4 judged them against 1.0's 92-95);
  - the corridor (BIB2): C0 and S1' each to CIELAB L* 73.5 (72-75) on its own right-wall point, projected with the plan cameras and
    verified on the clay (C0 frame (0.8578, 0.3695), S1' (0.7550, 0.3612)); C0 no longer on S1''s stops; the view at the corridor's
    end must stay the brightest surface (checked);
  - H0: the hall walls L* 75-78 (checked, beside B5's 2/3 stop);
  - D1: the wall-hue correction protects the objects' silhouettes, not their boxes (QA §4: 1.5-2.5 dE steps at the box edges).
Rows: the 22 kept v7 stills, the four 2026-11-03 fixes, the four 2026-11-04 fixes as cleaned today (<id>-fix2.png, fix_v9.py),
and the M0 1.2 composites (m0-v8b-r2-fix, pose-m0p-v8b-fix, pose-m0x-v8b-fix; graded in a second process by fix_m0_12.py grade5,
since they need the round-5b clay registration). New files only: <id>-graded-v5.png, -fix-v5, -fix2-v5 (+ -frame / -os6 on the
overscan canvases), -measurements-*-v5.json. Summary: regrade-v5-summary.json (pass / fail against Bible 1.8.4 per frame).
render-agent, 2026-11-04, 0 var2 tokens.
  python3 regrade_v5.py
"""
import json
import os
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import process_v8 as P  # noqa: E402

OLD_FIXES = ["k-boy-v7", "k-girl-v7", "w0-v7", "pose-k-boy-0-v7"]                    # fix_v7.py, 2026-11-03: <id>-fix.png
NEW_FIXES = ["b1-v7-r3", "b2-v7-r3", "pose-k-girl-0-v7-r2", "pose-w0-in-v7-r2"]       # fix_v9.py, 2026-11-04 cleanup: <id>-fix2.png
FIX_BASE = {"b2-v7-r3": "b1-v7-r3", "pose-k-boy-0-v7": "k-boy-v7"}
INHERIT_V5 = {k: v for k, v in P.INHERIT_STOPS_V4.items() if k != "C0"}            # C0 has its own BIB2 point now
NOTE = {"C0": "corridor (BIB2): own right-wall point, L* 72-75", "S1prime": "corridor (BIB2): own right-wall point, L* 72-75",
        "H0": "the vista at the living target (1) 90-94; hall walls L* 75-78 (1.8.4) and 2/3 stop (B5)",
        "M0": "Bible 1.8 B1 (1): 90-94", "M0p": "M0's target, 90-94", "M0x": "inherits M0's stops"}
results, rows = {}, []


def fid_of(frame):
    return next(f for f in VF.FRAMES if VF.FRAMES[f][0] == frame)


def row_of(r, fid, frame, fix, suffix, inherits):
    e, b, m = r["grade"]["exposure"], r["bible_v3"], r["measure_after"]
    wv, wh = b.get("wall_v4", {}), r["grade"].get("wall_hue_v4", {})
    fails = [k for k, v in r["checks"].items() if k.startswith("bible_") and v is False]
    return dict(
        id=fid, frame=frame, fix=fix, suffix=suffix, inherits=inherits,
        target=b["target_L"], range=b["range"], scale=r["settings"].get("target_scale", "HSL L"), reference=b["reference_source"], reference_uv=b["reference_point"],
        measured=b["measured_L"], meets_target=b["meets_target"], note=NOTE.get(frame),
        H=wv.get("reading", {}).get("H"), C_star=wv.get("reading", {}).get("C_star"), L_star=wv.get("reading", {}).get("L_star"), wall_judged=wv.get("judged"),
        hue_correction=dict(applied=wh.get("applied"), pixels_touched_pct=wh.get("pixels_touched_pct"), mask=wh.get("mask"), why_not=wh.get("why_not")),
        window_wall=b.get("window_wall"), hall_B5=b.get("hall_under_living_stops"), v5=b.get("v5"),
        black=m["darkest 0.5% patch L [12-15]"], window_p99=m["brightest area (window / door): L p50 / p99 / max"][1], frame_max=m["frame L p99 / max"][1],
        px255=m["pixels with a 255 channel: inside / outside that area"], stops=e["applied_stops"], needed=e["needed_stops"],
        checks={k: v for k, v in r["checks"].items() if k.startswith("bible_")}, fails=fails, meets_bible_1_8_4=b["meets_bible"],
        outputs=r["outputs"])


def run(fid, fix=None):
    """fix None: the still; "fix": <id>-fix.png; "fix2": <id>-fix2.png."""
    frame = VF.frame(fid)[0]
    render = os.path.join(VF.out_dir(fid), fid + "-" + fix + ".png") if fix else None
    suffix = ("-" + fix + "-v5") if fix else "-v5"
    stops = hue_force = base_id = src = None
    base_frame = INHERIT_V5.get(frame)
    if fix and fid in FIX_BASE:
        base_id = FIX_BASE[fid]
        src = results.get((base_id, fix))
    elif base_frame:
        base_id = fid_of(base_frame)
        src = results.get((base_id, None))
    if src is not None:
        stops = src["grade"]["exposure"]["applied_stops"]
        hue_force = True if src["grade"].get("wall_hue_v4", {}).get("applied") else None
    label = "grading v5 (Bible 1.8.4: living 90-94, corridor L* 72-75, hall L* 75-78, D1 silhouettes)" + (f" on the {fix}" if fix else "")
    r = P.process(fid, render, suffix, "v2", "auto", "none", None, label, exposure="bible", stops=stops, grade_mode="v5", hue_force=hue_force)
    results[(fid, fix)] = r
    rows.append(row_of(r, fid, frame, fix, suffix, dict(from_id=base_id, stops=stops, hue_correction=hue_force) if src is not None else None))


# --only id[:fix],...  re-runs those rows and merges them into the existing regrade-v5-summary.json (a row's inheritance source must be
# re-run with it when it changes; the M0 1.2 rows come from regrade-v5-m0-1-2.json as written)
ONLY = None
if "--only" in sys.argv:
    ONLY = [tuple((x.split(":") + [None])[:2]) for x in sys.argv[sys.argv.index("--only") + 1].split(",")]
if ONLY is None:
    masters = [f for f in VF.FRAMES if VF.FRAMES[f][1] == "master"]
    poses = [f for f in VF.FRAMES if VF.FRAMES[f][1] == "pose"]
    for f in masters:
        run(f)
    for f in OLD_FIXES:
        if VF.FRAMES[f][1] == "master":
            run(f, "fix")
    for f in poses:
        run(f)
    for f in OLD_FIXES:
        if VF.FRAMES[f][1] == "pose":
            run(f, "fix")
    for f in NEW_FIXES:
        run(f, "fix2")
    # the M0 1.2 composites: a second process (the round-5b clay registration of m0_1_2_pipeline.py changes v7_frames' globals)
    sub = subprocess.run([sys.executable, os.path.join(HERE, "fix_m0_12.py"), "grade5"], capture_output=True, text=True, cwd=HERE)
    print(sub.stdout[-2000:], sub.stderr[-2000:])
    m12 = json.load(open(os.path.join(HERE, "regrade-v5-m0-1-2.json")))
    for x in m12["rows"]:
        rows.append(x)
else:
    old_rows = json.load(open(os.path.join(HERE, "regrade-v5-summary.json")))["rows"]
    for fid, fx in ONLY:
        run(fid, fx)
    new = {(r["id"], r["fix"]): r for r in rows}
    rows = [new.get((r["id"], r["fix"]), r) for r in old_rows]
    for r in rows:                  # the merged rows are judged afresh below
        r["fails"] = [k for k, v in r["checks"].items() if v is False]
        r["meets_bible_1_8_4"] = bool(all(r["checks"].values()))
        r.pop("judged_by_reference", None)

for r in rows:                      # inherited stops: the target is judged by the group reference (one exposure per camera point)
    if r["meets_target"] is None and r["inherits"]:
        src = next((x for x in rows if x["id"] == r["inherits"]["from_id"] and (x["fix"] == r["fix"] or not x["fix"])), None)
        r["judged_by_reference"] = dict(id=r["inherits"]["from_id"], meets_target=src["meets_target"] if src else None)
        r["meets_bible_1_8_4"] = bool(r["meets_bible_1_8_4"] and (src["meets_target"] if src else False))
        if src and not src["meets_target"]:
            r["fails"].append("bible_target_met (group reference)")
    if r["wall_judged"] is False:
        r["fails"].append("wall hue / C* not judged (no wall at the reference point)")
        r["meets_bible_1_8_4"] = False
n_ok = sum(1 for r in rows if r["meets_bible_1_8_4"])
fail_count = Counter(k for r in rows for k in r["fails"])
summary = dict(
    date="2026-11-04", tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/regrade_v5.py (process_v8.py --grade v5; fix_m0_12.py grade5)",
    rule=("Bible 1.8.4 light rules (V7Q4 test page): the reference wall to its target - the living back wall L 90-94 (M0 group; H0's vista), "
          "the corridor CIELAB L* 72-75 on the right wall at the BIB2 points (C0, S1'), bath 86-90, the rest 90-94; the view at the corridor's end "
          "the brightest surface; the hall walls L* 75-78 (and B5's 2/3 stop); wall H 32-40 and C* <= 7 (B4) on the reference wall; the window wall "
          "L 80-88 where QA reads it; black point 12-15; no 255, window p99 <= 97; the near-white chroma guard (B4). The wall-hue correction as v4; in D1 "
          "it protects the objects' silhouettes instead of their boxes. Frames that inherit stops are judged by their group reference."),
    corridor_points=dict(C0=dict(plan=[3.10, 15.80, 1.30], camera=dict(loc=[2.397, 17.11, 1.20], yaw=0, u0=0.50, v0=0.46, lens=24), frame_uv=[0.8578, 0.3695],
                                 designer_estimate=[0.86, 0.37], clay="clean wall, L* 79.35 +- 0.03 (round-4 C0.png), no edge within 64 px"),
                         S1prime=dict(plan=[3.10, 11.80, 1.30], camera=dict(loc=[2.641, 13.00, 1.20], yaw=0, u0=0.50, v0=0.46, lens=24), frame_uv=[0.7550, 0.3612],
                                      designer_estimate=[0.76, 0.36], clay="clean wall, L* 84.89 +- 0.03 (round-4 poses/S1prime.png), no edge within 64 px",
                                      note="S1''s u0 0.50 is the plan's (round-4/5/5b plan.json poses.S1prime), the value the designer assumed")),
    frames=len(rows), meet_bible_1_8_4=n_ok, failing_checks=dict(fail_count), rows=rows)
json.dump(summary, open(os.path.join(HERE, "regrade-v5-summary.json"), "w"), indent=1, ensure_ascii=False)
print("\n== grading v5 ==")
for r in rows:
    ww = r["window_wall"]["L"] if r["window_wall"] else "-"
    vv = (r.get("v5") or {}).get("vista")
    print(f"{r['id']:20s}{('(' + r['fix'] + ')') if r['fix'] else '      '} {r['scale'][:6]} {r['measured']} [{r['range'][0]}-{r['range'][1]}] H {r['H']} C* {r['C_star']} "
          f"win-wall {ww} vista {vv['vista_Lstar_p95'] if vv else '-'}/{vv['surfaces_Lstar_p99_5'] if vv else '-'} | black {r['black']} | "
          f"{'BIBLE 1.8.4' if r['meets_bible_1_8_4'] else 'fails: ' + ', '.join(r['fails'])}")
print(f"\n{n_ok}/{len(rows)} meet Bible 1.8.4 in full; failing checks: {dict(fail_count)}")
