"""
Lock check of the four 2026-11-04 code fixes (briefs/render-retakes-code-fixes-2026-11-04.md, tasks 1 and 3), 0 var2 tokens.

For each retake: lock_v2 with the v3 edges (QA's named edges + cross-correlated box edges + structure-gated bands / tiles, W0-in
as a video endpoint) on the raw retake ("before") and on its `-fix.png` ("after"), and the v2 numbers of the fix for continuity.
Writes `<id>-lock-fix.json` and two overlays next to the stills: `<id>-lock-fix.jpg` (after) and `<id>-lock-v3.jpg` (before);
red = the clay's edges and named lines, green = the render's line at the measured offset (grey = not counted).

  python3 lock_fixes_v8.py [id ...]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import lock_v2 as L  # noqa: E402

IDS = ["b1-v7-r3", "pose-k-girl-0-v7-r2", "pose-w0-in-v7-r2", "b2-v7-r3"]
DATE = "2026-11-04"
# QA's numbers on the raw retakes (qa/reports/2026-11-03-retakes-g1.md §2-3, data/edges-direct.json): d_strongest / xcorr at 1920 x 1080
QA_BEFORE = {
    "pose-w0-in-v7-r2": "desk top front -39 (r 0.63), drawer bottom -45 (0.85), chair back top -6, chair +1 / -5, desk left -3; desk right -33 = the side panel's inner edge (eye); shelf +34 = another line (eye)",
    "pose-k-girl-0-v7-r2": "desk top 0 / xc 2, band +3, bed foot +11, room corner +2, legs -3 / -1",
    "b1-v7-r3": "all named lines within +-5: glazing 0 / +1 / -3 / -1, ledge +1, WC block -3 / -1 / 0, corner +2, vanity +5",
    "b2-v7-r3": "vanity right -43 (strongest; xcorr +4 at r 0.435), vanity top -7, mirror -6 / +4 / -8, mirror head ~-30 (sloped), niche -6 / -7",
}


def brief(rep):
    s, v = rep["summary"], rep["verdict"]
    return dict(register_shift_px=s["register_shift_px"], register_scale_pct=s["register_scale_pct"],
                worst_band_px_after_register=s["worst_band_px_after_register"], bands_counted=s["bands_reliable_after_register"],
                worst_tile_px_after_register=s["worst_tile_ecc_px_after_register"], tiles_counted=s["tiles_counted_after_register"],
                box_edges_worst_px=s["fixed_edges_worst_px"], box_ratios=s["fixed_ratios"],
                named_edges_worst_px=s.get("named_edges_worst_px"), named_edges_counted=f"{s.get('named_edges_counted')}/{s.get('named_edges_total')}",
                named_edges=s.get("named_edges"), residual_limit_px=v["thresholds"]["residual_px"],
                global_pass=v["global_pass"], residual_pass=v["residual_pass"], edges_pass=v["edges_pass"], **{"pass": v["pass"]})


def run(fid):
    od = VF.out_dir(fid)
    raw, fix = os.path.join(od, fid + ".png"), os.path.join(od, fid + "-fix.png")
    tmp = os.path.join(od, fid + "-lock-fix.tmp.json")
    before = L.run_frame(fid, render_path=raw, out_path=tmp, overlay_path=os.path.join(od, fid + "-lock-v3.jpg"), edges_mode="v3", date=DATE)
    after = L.run_frame(fid, render_path=fix, out_path=tmp, overlay_path=os.path.join(od, fid + "-lock-fix.jpg"), edges_mode="v3", date=DATE)
    after_v2 = L.run_frame(fid, render_path=fix, out_path=tmp, edges_mode="v2", date=DATE)
    os.remove(tmp)
    named = {}
    for nm, b in before["named_edges"].items():
        a = after["named_edges"][nm]
        named[nm] = dict(clay_px=b["clay_px"], before=b["d_xcorr_px"], before_r=b["r"], after=a["d_xcorr_px"], after_r=a["r"],
                         counted_after=a["counted"], **({"eye_override": a["eye_override"]} if "eye_override" in a else {}))
    rec = dict(asset_id=fid, date=DATE, tokens=0, script="assets/renders/house-nordic-v7-2026-11-02/lock_fixes_v8.py",
               method="lock_v2.py edges v3 (2026-11-04): " + after["method"],
               counting=after["verdict"]["thresholds"].get("counted"), endpoint=("video endpoint (9.6 px)" if not after["pan_endpoint"] else "pan endpoint (2 px)"),
               before=dict(still=os.path.relpath(raw, VF.REPO), **brief(before)), after=dict(still=os.path.relpath(fix, VF.REPO), **brief(after)),
               after_lock_v2_edges_v2=dict(worst_band=after_v2["summary"]["worst_band_px_after_register"], worst_tile=after_v2["summary"]["worst_tile_ecc_px_after_register"],
                                           box_edges_worst_px=after_v2["summary"]["fixed_edges_worst_px"], box_ratios=after_v2["summary"]["fixed_ratios"],
                                           **{"pass": after_v2["verdict"]["pass"]}),
               named_edges_before_after=named, qa_before=QA_BEFORE.get(fid),
               full_before=before, full_after=after,
               overlays=dict(before=os.path.relpath(os.path.join(od, fid + "-lock-v3.jpg"), VF.REPO), after=os.path.relpath(os.path.join(od, fid + "-lock-fix.jpg"), VF.REPO)))
    json.dump(rec, open(os.path.join(od, fid + "-lock-fix.json"), "w"), indent=1, ensure_ascii=False)
    print(f"--- {fid}")
    for nm, n in named.items():
        print(f"    {nm:38s} clay {n['clay_px']:5d}  before {str(n['before']):>4s} (r {n['before_r']})  after {str(n['after']):>4s} (r {n['after_r']}){'' if n['counted_after'] else '  [not counted' + (': eye' if 'eye_override' in n else ': r < 0.5') + ']'}")
    return rec


if __name__ == "__main__":
    for i in (sys.argv[1:] or IDS):
        run(i)
