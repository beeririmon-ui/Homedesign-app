#!/usr/bin/env python3
"""
Grading v3: the 22 kept v7 stills and the four accepted zero-token fixes (K-boy, K-girl, W0, K-boy-0 `-fix.png`) graded to the
Bible targets with process_v8.py --exposure bible (briefs/render-v7-retakes-2026-11-03.md task 1; V7Q4 = yes, BIB1 = all six).
New files only: <id>-graded-v3.png (+ -frame-v3.png / -graded-os6-v3.png on the overscan canvases), <id>-measurements-v3.json;
the fixes get -graded-fix-v3.png / -frame-fix-v3.png / -graded-os6-fix-v3.png / -measurements-fix-v3.json. No lock run (the
grade does not move edges; <id>-lock-v2.json / -lock-fix.json stay the record). Summary: regrade-v3-summary.json (the measured L
per target, the v3 stops, the v2 stops and the delta, black point, window p99, the B4 chroma delta, the B5 hall delta, and whether
the frame meets the Bible). render-agent, 2026-11-03, 0 var2 tokens.
  python3 regrade_v8.py [ids...]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import process_v8 as P  # noqa: E402

FIXES = ["k-boy-v7", "k-girl-v7", "w0-v7", "pose-k-boy-0-v7"]       # the accepted zero-token fixes of 2026-11-03 (fix_v7.py)
only = set(sys.argv[1:])
masters = [f for f in VF.FRAMES if VF.FRAMES[f][1] == "master"]
poses = [f for f in VF.FRAMES if VF.FRAMES[f][1] == "pose"]
rows, results = [], {}


def v2_stops(fid, fix):
    p = os.path.join(VF.out_dir(fid), fid + ("-measurements-fix.json" if fix else "-measurements-v2.json"))
    if os.path.exists(p):
        e = json.load(open(p)).get("grade", {}).get("exposure", {})
        return e.get("applied_stops"), e.get("needed_stops")
    return None, None


def hero_L(res):
    for k, v in res["measure_after"].items():
        if k.startswith("hero_wall_mid"):
            return v[2]
    return None


def run(fid, fix=False):
    frame = VF.FRAMES[fid][0]
    key = (fid, fix)
    if only and fid not in only:
        return
    render = os.path.join(VF.out_dir(fid), fid + "-fix.png") if fix else None
    suffix = "-fix-v3" if fix else "-v3"
    stops = target = None
    base = P.INHERIT_STOPS.get(frame)
    if base:
        bid = next(f for f in VF.FRAMES if VF.FRAMES[f][0] == base)
        src = results.get((bid, fix)) or results.get((bid, False))
        if src:
            stops = src["grade"]["exposure"]["applied_stops"]
    if frame == "CB-0":
        src = results.get(("b1-v7", False))
        if src:
            target = hero_L(src)
    r = P.process(fid, render, suffix, "v2", "auto", "none", None, "grading v3 (Bible targets, V7Q4)" + (" on the zero-token fix" if fix else ""),
                  exposure="bible", stops=stops, target=target)
    results[key] = r
    e, b = r["grade"]["exposure"], r["bible_v3"]
    s2, n2 = v2_stops(fid, fix)
    cg = r["grade"].get("near_white_chroma_guard_B4") or {}
    rows.append(dict(id=fid, frame=frame, fix=fix, suffix=suffix, target_L=b["target_L"], range=b["range"], measured_L=b["measured_L"], meets_target=b["meets_target"],
                     reference=b["reference_source"], target_source=b["target_source"], stops_v3=e["applied_stops"], needed_v3=e["needed_stops"], stops_v2=s2,
                     delta_stops_v3_minus_v2=(round(e["applied_stops"] - s2, 3) if s2 is not None else None), flag=e["flag"],
                     black=r["measure_after"]["darkest 0.5% patch L [12-15]"], black_point=r["grade"]["black_point"],
                     window_p99=r["measure_after"]["brightest area (window / door): L p50 / p99 / max"][1], frame_max=r["measure_after"]["frame L p99 / max"][1],
                     px255=r["measure_after"]["pixels with a 255 channel: inside / outside that area"], wall_HSL=b["reference_HSL"],
                     chroma_B4=dict(delta_C=cg.get("delta_C"), applied=cg.get("applied"), before=cg.get("before"), after=cg.get("after"), after_guard=cg.get("after_guard")),
                     window_wall=b.get("window_wall"), hall_B5=b.get("hall_under_living_stops"), checks=r["checks"], meets_bible=b["meets_bible"],
                     outputs=r["outputs"], measurements=os.path.relpath(os.path.join(VF.out_dir(fid), fid + "-measurements" + suffix + ".json"), VF.REPO)))


for fid in masters:
    run(fid)
for fid in FIXES:
    if VF.FRAMES[fid][1] == "master":
        run(fid, fix=True)
for fid in poses:
    run(fid)
for fid in FIXES:
    if VF.FRAMES[fid][1] == "pose":
        run(fid, fix=True)

for r in rows:                      # inherited frames are judged by their group reference (same stops, one camera point)
    if r["meets_target"] is None:
        ref = P.INHERIT_STOPS.get(r["frame"])
        src = next((x for x in rows if x["frame"] == ref and x["fix"] == r["fix"]), None) or next((x for x in rows if x["frame"] == ref), None)
        r["judged_by_reference"] = dict(frame=ref, meets_target=src["meets_target"] if src else None)
        r["meets_bible"] = bool(r["meets_bible"] and (src["meets_target"] if src else False))
n_ok = sum(1 for r in rows if r["meets_bible"])
n_t = sum(1 for r in rows if r["meets_target"] or (r["meets_target"] is None and r.get("judged_by_reference", {}).get("meets_target")))
summary = dict(date="2026-11-03", script="assets/renders/house-nordic-v7-2026-11-02/regrade_v8.py (process_v8.py --exposure bible)",
               rule="Bible targets (V7Q4 yes, BIB1 all six): reference wall to its target, black point 12-15 both ways, v2 roll-off last (L <= 97, zero 255), "
                    "B4 near-white chroma guard (+1.5 C max), B5 hall 2/3 stop under the living vista; B2 / M0x / K-boy-0 / K-girl-0 inherit the group stops; "
                    "C0 / S1' use the G1.8 proposal (hall rule), not a Bible number",
               targets={k: dict(target=v[0], lo=v[1], hi=v[2], source=v[3]) for k, v in P.BIBLE_TARGET.items()}, frames=len(rows),
               meet_target=n_t, meet_bible=n_ok, rows=rows)
json.dump(summary, open(os.path.join(HERE, "regrade-v3-summary.json"), "w"), indent=1, ensure_ascii=False)
print("\n== grading v3 (Bible targets) ==")
for r in rows:
    print(f"{r['id']:18s}{'(fix)' if r['fix'] else '     '} {r['frame']:9s} target {r['target_L']:5.1f} [{r['range'][0]}-{r['range'][1]}] -> L {r['measured_L']:5.1f} {'OK ' if r['meets_target'] else ('inh' if r['meets_target'] is None else 'off')} | "
          f"stops v3 {r['stops_v3']:+.3f} (v2 {r['stops_v2'] if r['stops_v2'] is not None else '-'}; d {r['delta_stops_v3_minus_v2']}) | black {r['black']} | win p99 {r['window_p99']} max {r['frame_max']} 255 {r['px255']} | "
          f"dC {r['chroma_B4']['delta_C']} | {'BIBLE' if r['meets_bible'] else 'fails: ' + ','.join(k for k, v in r['checks'].items() if k.startswith('bible_') and not v)}")
print(f"\n{n_t}/{len(rows)} on target, {n_ok}/{len(rows)} meet every Bible check")
