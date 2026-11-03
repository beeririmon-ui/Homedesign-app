#!/usr/bin/env python3
"""
Re-grade and re-lock the 22 kept v7 stills with process_v8.py (grade order v2, wall sample point auto, lock_v2), as new
files next to the v7 ones: <id>-graded-v2.png (+ -frame-v2.png / -graded-os6-v2.png for the overscan canvases),
<id>-measurements-v2.json, <id>-lock-v2.json. Nothing of v7 is overwritten. render-agent, 2026-11-03, 0 var2 tokens.
Writes a summary table to regrade-v2-summary.json and prints it.
  python3 regrade_v7.py [ids...]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import process_v8 as P  # noqa: E402

ids = sys.argv[1:] or list(VF.FRAMES)
rows = []
for fid in ids:
    r = P.process(fid)
    s, v = r["lock_v2_summary"], r["lock_v2_verdict"]
    rows.append(dict(id=fid, frame=r["frame"], pan=VF.FRAMES[fid][3],
                     sample_point=r["sample_point"], exposure=r["grade"]["exposure"], window_after=r["measure_after"]["brightest area (window / door): L p50 / p99 / max"],
                     window_v7=r["v7_for_comparison"].get("measure_after_v1_window"), frame_max_after=r["measure_after"]["frame L p99 / max"][1],
                     black=r["measure_after"]["darkest 0.5% patch L [12-15]"], checks=r["checks"],
                     lock=dict(shift_px=s["register_shift_px"], scale_pct=s["register_scale_pct"], band_after=s["worst_band_px_after_register"],
                               tile_after=s["worst_tile_ecc_px_after_register"], edges_worst_px=s["fixed_edges_worst_px"], ratios=s["fixed_ratios"],
                               residual_limit=v["thresholds"]["residual_px"], global_pass=v["global_pass"], residual_pass=v["residual_pass"], edges_pass=v["edges_pass"],
                               **{"pass": v["pass"]})))
json.dump(dict(date="2026-11-03", script="process_v8.py", rows=rows), open(os.path.join(HERE, "regrade-v2-summary.json"), "w"), indent=1, ensure_ascii=False)
print("\n== lock v2 (px at 1920) ==")
for r in rows:
    L = r["lock"]
    print(f"{r['frame']:9s} {'pan ' if r['pan'] else 'end '} shift {L['shift_px']} scale% {L['scale_pct']} resid band {L['band_after']} tile {L['tile_after']} (<= {L['residual_limit']}) edges {L['edges_worst_px']} -> {'PASS' if L['pass'] else 'FAIL'}")
print("\n== grade v2 ==")
for r in rows:
    e = r["exposure"]
    print(f"{r['frame']:9s} point {r['sample_point']['source'][:32]:32s} need {e['needed_stops']:+.3f} applied {e['applied_stops']:+.2f} | window p99 v7 {r['window_v7'][1] if r['window_v7'] else '-'} -> v2 {r['window_after'][1]} | frame max {r['frame_max_after']} | black {r['black']} | ok {all(r['checks'].values())}")
