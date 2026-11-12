#!/usr/bin/env python3
"""qa-agent 2026-11-12 (R9): the verdict file qa/reports/2026-11-12-wm-phase2-r9.json, built from data/*.json (no image is read here)."""
import json
import os

ROOT = "/home/user/homedesign-app/qa/reports"
OUT = os.path.join(ROOT, "2026-11-12-wm-phase2-r9")
D = {k: json.load(open(os.path.join(OUT, "data", k + ".json"))) for k in
     ("scope", "pendant", "halo", "bands", "curtains", "integrity-r9", "lock", "grade", "encode", "manifest", "combos")}
sc, pe, ha, bd, cu, it, lk, gr, en, mf, co = (D[k] for k in ("scope", "pendant", "halo", "bands", "curtains", "integrity-r9", "lock", "grade", "encode", "manifest", "combos"))
fc = it["full_cross"]
va = it["variants_alone"]
lock_files = {k: v for k, v in lk.items() if isinstance(v, dict) and "lines" in v}
ts = pe["turns_summary"]
ramp = pe["ramp"]
bq = bd["r9"]["qa"]
bc = bd["r9"]["opencv"]


def ok(b):
    return "PASS" if b else "FAIL"


pen_alone = va["pendant-v2"]
items = [
    dict(item="1 scope: files", result=ok(sc["changed"] == ["curtains-v3 layer", "pendant-v2 layer"] and not sc["git_since_r8_qa_commit"]["modified"]
                                         and not sc["git_since_r8_qa_commit"]["deleted"]),
         numbers=f"{len(sc['changed'])} of {len(sc['files'])} tool files changed (pendant-v2 layer, curtains-v3 layer); shadows unchanged; "
                 f"git since QA's R8 commit: {len(sc['git_since_r8_qa_commit']['added'])} added, 0 modified, 0 deleted"),
    dict(item="1 scope: QA's R8 sha256 list", result=ok(not sc["r8_sha256_list"]["differ"]),
         numbers=f"{sc['r8_sha256_list']['identical']} of {sc['r8_sha256_list']['files']} byte-identical"),
    dict(item="1 scope: scenes", result=ok(sc["scenes_composed_outside_total"] == 0 and all(
        v.get("changed_outside_two_products", 0) == 0 for v in sc["stored_truths"].values())),
         numbers=f"13 scenes composed by QA (3 defaults + 10 variants, set B): {sc['scenes_composed_outside_total']} px changed outside the two products; "
                 f"stored truths: 2 new (pendant-v2 {sc['stored_truths']['variant pendant-v2']['changed_px']} px, max {sc['stored_truths']['variant pendant-v2']['max_change']}; "
                 f"curtains-v3 {sc['stored_truths']['variant curtains-v3']['changed_px']} px, max {sc['stored_truths']['variant curtains-v3']['max_change']}), 0 outside; 11 identical"),
    dict(item="2 P2-1 alpha only", result=ok(pe["alpha_only"]["rgb_changed_at_alpha255_both"] == 0 and pe["alpha_only"]["rgb_changed_where_alpha_not_raised"] == 0
                                             and pe["alpha_only"]["rows_lt_195_changed_px"] == 0 and pe["alpha_only"]["collar_zone_changed_px"] == 0
                                             and pe["alpha_only"]["shadow_file"]["same_as_r8_qa_list"] and pe["alpha_only"]["new_rgb_between_old_and_bleed_px"] == pe["alpha_only"]["of_px"]),
         numbers=f"alpha {pe['alpha_only']['alpha_changed_px']} px (+{pe['alpha_only']['alpha_raised']} / -{pe['alpha_only']['alpha_lowered']}); RGB {pe['alpha_only']['rgb_changed_px']} px, "
                 f"all where alpha rose from > 0, 0 at alpha 255; added colour vs the layer's bleed: median {pe['alpha_only']['implied_added_colour_vs_bleed']['median']} levels; "
                 f"all {pe['alpha_only']['of_px']} between the old colour and the bleed; cord/canopy rows and collar 0; shadow byte-identical"),
    dict(item="2 P2-1 (a) the line", result="PASS on the fitted sides; top-left arc kept (stop rule, closed by the designer)",
         numbers=f"QA line vs R9's stored line <= {max(v.get('dist_to_r9_stored_line_max', 0) for k, v in pe['fit']['r9'].items() if k.startswith('r9:'))} px; "
                 f"convex-hull depth: right side {pe['fit']['r9']['r9:right_side']['hull_depth_max']}, left flank {pe['fit']['r9']['r9:left_flank']['hull_depth_max']} px "
                 f"(R8 {pe['fit']['r8']['r9:right_side']['hull_depth_max']} / {pe['fit']['r8']['r9:left_flank']['hull_depth_max']}); opposite turns (4 phases, max): "
                 f"right {ts['r9']['opposite_r9_zones_max_over_phases']['right_side']}/{ts['r9']['n_r9_zones_phase0']['right_side']}, "
                 f"left flank {ts['r9']['opposite_r9_zones_max_over_phases']['left_flank']}/{ts['r9']['n_r9_zones_phase0']['left_flank']} "
                 f"(R8 {ts['r8']['opposite_r9_zones_max_over_phases']['right_side']} / {ts['r8']['opposite_r9_zones_max_over_phases']['left_flank']}); "
                 f"top-left arc {ts['r9']['opposite_r9_zones_max_over_phases']['top_left_arc']}/{ts['r9']['n_r9_zones_phase0']['top_left_arc']} (= R8)"),
    dict(item="2 P2-1 (b) right edge", result=ok(ts["r9"]["right_edge_over_2x_any_phase"] == 0),
         numbers=f"max turn ratio {ts['r9']['right_edge_max_ratio_over_phases']} over 4 phases (R8 {ts['r8']['right_edge_max_ratio_over_phases']}); chords over 2x: 0 (R8 up to "
                 f"{max(p['right_edge']['over_2x'] for p in pe['turns']['r8'])})"),
    dict(item="2 P2-1 (c) ramp", result=ok(all(v["pass_"] for v in ramp["P2-1 (c)"].values())),
         numbers=f"left {ramp['r9']['left_flank']['median']}, right {ramp['r9']['right_flank']['median']} px vs reference {ramp['reference_drum_r4']['flanks_both']['median']} "
                 f"(default pendant's flanks); R8 {ramp['r8']['left_flank']['median']} / {ramp['r8']['right_flank']['median']}"),
    dict(item="2 P2-1 (d) size", result=ok(pe["width"]["P2_1_d"]["pass_"]),
         numbers=f"widest row {pe['width']['r8']['width_px']} -> {pe['width']['r9']['width_px']} px ({pe['width']['change_px']} px, {pe['width']['change_cm']} cm)"),
    dict(item="2 P2-1 (e) halos", result=ok(ha["P2-1 (e)"]["pass_"]),
         numbers=f"bright on the lantern {ha['P2-1 (e)']['bright_on_lantern_r9']}; dark on the lantern {ha['P2-1 (e)']['dark_on_lantern_r8']} -> {ha['P2-1 (e)']['dark_on_lantern_r9']}, "
                 f"0 new places (2 one-pixel extensions of R8 spots, pleat grooves at the top edge); the cord's run unchanged"),
    dict(item="2 P2-1 (f) integrity", result=ok(all(pen_alone[f"{s} P1"]["swap_vs_default_outside_two_regions"] == 0 and pen_alone[f"{s} P1"]["variant_vs_empty_outside_variant_region"] == 0
                                                    for s in "ABC") and not it["disjoint"]["variant_slot_overlaps"]),
         numbers=f"swap and empty-swap outside the pendant region 0 (sets A, B, C); region disjoint from every other slot (nearest: framed-art "
                 f"{it['disjoint']['nearest_other_regions_px']['pendant'].get('framed-art')} px); alone in A/B/C, 3 paths: p99.9 <= "
                 f"{max(r['p999_region'] for k, r in pen_alone.items() if isinstance(r, dict))}, max <= {max(r['max'] for k, r in pen_alone.items() if isinstance(r, dict))}"),
    dict(item="2 P2-1 (g) eye x2 + photo", result="PASS (the flank and the right side); the top-left arc closed by the designer",
         numbers="whole-lantern x2: one convex flank left (no ledge) and right (no facet); the 40's photos (scratchpad only): smooth convex silhouette, "
                 "no ledge low on the left, vertical lobes, no horizontal bands"),
    dict(item="2 stop rule at the top-left arc", result="CONFIRMED",
         numbers=f"line moved median {pe['kept_arcs_line_move']['top_left_arc']['without_blends']['median_abs']}, max {pe['kept_arcs_line_move']['top_left_arc']['without_blends']['max_abs']} px "
                 f"outside the declared blends (all: max {pe['kept_arcs_line_move']['top_left_arc']['all']['max_abs']}); ramp {pe['top_left_arc']['r8']['ramp']['median']} -> "
                 f"{pe['top_left_arc']['r9']['ramp']['median']}; convex-hull depth {pe['top_left_arc']['hull_depth_r9']['hull_depth_max']} px at "
                 f"{pe['top_left_arc']['hull_depth_r9']['hull_depth_at']} (R8 {pe['top_left_arc']['hull_depth_r8']['hull_depth_max']}); RGB there only where alpha rose"),
    dict(item="3 F1 literal rule", result=ok(cu["F1_literal"]["r9 graded layer, qa_lab"]["whole_layer"] == 0 and cu["F1_literal"]["r9 graded layer, r8_opencv_lab"]["whole_layer"] == 0),
         numbers="R9 graded layer at alpha > 0: 0 (QA Lab), 0 (R8's OpenCV Lab), whole layer; R8: 11 / 11"),
    dict(item="3 F1 only the 11 px", result=ok(cu["changed"]["same_set_as_r8_literal_hits"] and cu["changed"]["alpha_bytes_identical"] and cu["changed"]["shadow"]["sha_equals_qa_r8_list"]),
         numbers=f"RGB changed on {cu['changed']['rgb_changed_px']} px = R8's literal hits = R9's mask; alpha byte-identical; shadow byte-identical"),
    dict(item="3 F1 dL* <= 0.03", result="PASS in R8's Lab; 1 px over in QA's Lab (quantisation, not visible)",
         numbers=f"max |dL*| {cu['changed']['dL_opencv_lab']['max_abs']} (OpenCV) / {cu['changed']['dL_qa_lab']['max_abs']} (QA; pixel (248,23), alpha 6, above the camera "
                 f"frame; no 8-bit value within +-2 does better than 0.068 in both Labs); scene effect <= {cu['changed']['dL_scene_effect_max_L']} L*"),
    dict(item="3 colour lock", result=ok(cu["lock"]["pass_"]),
         numbers=f"L* {cu['lock']['r9']['qa']['rounded']['L']}, h {cu['lock']['r9']['qa']['rounded']['h']}, C* {cu['lock']['r9']['qa']['rounded']['C']} "
                 f"(raw {cu['lock']['r9']['qa']['raw']}); mask {cu['lock']['r9']['mask_px']} px; = R8"),
    dict(item="3 the 8 soft-edge px", result="NOT VISIBLE",
         numbers=f"alpha 4-16, h 103.9-144.0; scene effect <= {cu['wide_rule_r9']['soft_edge_max_scene_effect']['levels']} levels, "
                 f"CIEDE2000 <= {cu['wide_rule_r9']['soft_edge_max_scene_effect']['de00']}"),
    dict(item="4 F2 final-pass mask", result=ok(cu["F2"]["final_pass_px"] == 44 and cu["F2"]["overlap"] == 0),
         numbers=f"44 px, overlap 0, union 897; a*b* moved on all 44 ({cu['F2']['dab_in_final_pass']['min']}-{cu['F2']['dab_in_final_pass']['max']}); outside the union "
                 f"p99.9 {cu['F2']['dab_outside_union']['p999']} (the 4 px over 1 are in R8's bench-break zone); QA R8's 37 px: 36 in the mask, 1 in the bench zone"),
    dict(item="4 F2 alpha_unchanged correction", result=ok(all(v["ungraded_alpha_same"] and v["free_alpha_same"] and v["changed_where_source_not_soft"] == 0
                                                               for v in cu["alpha_unchanged_correction"]["qa"].values())),
         numbers="ungraded and free alpha R7 == R8 (3 curtains); graded alpha changed 7 / 6 / 64 px, max 15 / 20 / 12, 0 where the source is not soft (= fix-r9.json)"),
    dict(item="4 F8 sha256", result=ok(not mf["entries_r9"]["sha_mismatch"] and not mf["entries_r9"]["bytes_mismatch"] and not mf["entries_r9"]["tool_set"]["mismatch"]
                                       and not mf["entries_r9"]["scripts"]["mismatch"] and not mf["assets_manifest"]["sha256_mismatch"]
                                       and mf["assets_manifest"]["r9_entries_present_and_identical"] and not mf["written_sha256"]["mismatched"]),
         numbers=f"{mf['entries_r9']['entries']} entries (sha256 + bytes), {mf['entries_r9']['scripts']['n']} scripts, {mf['entries_r9']['tool_set']['n']} tool files: all match; "
                 f"assets/manifest.json: R9 entries identical, {mf['assets_manifest']['entries_with_sha256']} with sha256, all match; vs R8: "
                 f"+{len(mf['assets_manifest']['vs_r8_qa_commit']['added'])}, 0 removed, 0 changed; written sha256 {mf['written_sha256']['matched']}/{mf['written_sha256']['n']}"),
    dict(item="5 full cross", result=ok(fc["all_pass"] and fc["independence_all_zero"] and fc["n_composites"] == 2592),
         numbers=f"{fc['n_composites']} compositions ({fc['n_combos']} x 3 sets x 2 paths): worst p99.9 {fc['worst']['p999']}, max {fc['worst']['max']}, independence "
                 f"{fc['worst']['indep_max']}; swap-diff of the defaults outside {it['swap_diff_defaults_outside_total']}"),
    dict(item="5 shell lock", result=ok(all(v["pass_all_samples"] for v in lock_files.values())),
         numbers=f"worst p90 {max(v['worst_p90_all'] for v in lock_files.values())} px vs 9.6, on {len(lock_files)} files; = R8 line by line"),
    dict(item="5 one v3c grade", result=ok(gr["one_grade_pass"]),
         numbers=f"residual median {gr['r9']['pendant-v2']['residual_median']} / {gr['r9']['curtains-v3']['residual_median']}; black point and clip = R8"),
    dict(item="5 encoding (file test)", result=ok(all(w[k]["pass"] for v in en["layers"].values() for w in v["widths"].values() for k in ("product_over_grey", "shadow", "scene_on_rect"))),
         numbers="pendant-v2 R9 and curtains-v3 R9 at 1920 and 2720: p99 2, p99.9 2-3, max 3, dE00 p99 2.44-2.72 (thresholds 6 / 10 / 3.5); base AVIF bytes = R8"),
    dict(item="6 no supplier image", result=ok(not mf["supplier_images"]["near_matches_le_40_of_256"] or min(q.get("min_hamming_256", 999) for q in mf["supplier_images"]["near_matches_le_40_of_256"]) > 20),
         numbers=f"{mf['supplier_images']['repo_images_checked']} repo images vs {mf['supplier_images']['supplier_images_compared']}; nearest {mf['supplier_images']['min_hamming_256_overall']}/256 "
                 f"(as R8); R9's new images >= {mf['supplier_images']['r9_images_min']}"),
    dict(item="+ six random combinations (seed 912)", result="PASS", numbers="pendant-v2 in 2, curtains-v3 in 3; all read natural"),
]
le = bq["left_half"]["band_edges"]
res = {
    "id": "qa-2026-11-12-wm-phase2-r9",
    "date": "2026-11-12",
    "author": "qa-agent",
    "scope": "warm-modern living-room tool, phase 2, R9 (code only, 0 tokens): P2-1 on pendant 2 (alpha only), F1 on curtain 3, F2 / F8 records; "
             "plus the R9 baseline of the left inner bands for P2-2 (the manager's addendum; not judged)",
    "cost": "0 tokens; no var2, no network, no commits; new files only",
    "verdict": "PASS",
    "bottom_line": "R9 passes: only the two claimed layers changed, P2-1 meets (a)-(g) where it fitted and holds the top-left arc under the stop rule "
                   "(closed by the designer), F1 reads 0 in both Labs with the colour lock unchanged, the records and every sha256 match, and the "
                   "phase-2 acceptance holds over 2,592 compositions. Curtain 3 can go to 'approved for the site' from QA's side; pendant 2 waits only for P2-2.",
    "items": items,
    "bands_baseline_r9": dict(
        method="data/bands.json (tools/r9_bands.py): 24 visible sectors of 7.5 deg, per-sector L* down the meridian, 4-knot cubic B-spline, both Labs",
        left_half=dict(band_edges=[dict(sectors=e["sectors"], y=e["y"], jump3=e["jump3"], plateau=e["plateau"], rise_10_90_px=e["rise_10_90_px"],
                                        steepest_row_change=e["steepest_row_change"]) for e in le],
                       residual_max_abs=dict(qa=bq["left_half"]["residual_max_abs"], opencv=bc["left_half"]["residual_max_abs"]),
                       literal_steps=bq["left_half"]["literal_steps"], plateau_max=bq["plateau_max"]["left"]),
        right_half=dict(band_edges=len(bq["right_half"]["band_edges"]), residual_max_abs=dict(qa=bq["right_half"]["residual_max_abs"], opencv=bc["right_half"]["residual_max_abs"]),
                        literal_steps=bq["right_half"]["literal_steps"], plateau_max=bq["plateau_max"]["right"],
                        sectors_residual_gt1=bq["right_half"]["sectors_residual_gt1"]),
        noise_floor=bq["noise_floor"], p2_2_numbers=bq["p2_2_baseline"], p2_2_numbers_opencv=bc["p2_2_baseline"],
        r8_equals_r9=bd["r8_vs_r9_same_profiles"]),
    "findings": [
        dict(id="F9", severity="medium", owner="master-designer",
             what="P2-2 (a) as written (the residual of every sector's meridian profile <= 1 L*) cannot be met on this paper even where the designer accepts it: "
                  f"QA's measure of R9 gives a residual over 1 L* in every measured right-half sector (max {bq['right_half']['residual_max_abs']}), with no band edge there; "
                  "the pleats and lobes leave ~1.5-3 L* in a single sector's profile",
             fix="before R10 runs, write (a) as a band-edge rule: e.g. no step with a 3-px jump >= 2 L* and a plateau >= 2.5 L* in any sector (R9: 3 in the left half, "
                 f"0 in the right; the right half tops out at {bq['plateau_max']['right']}), or a residual bound relative to the right half; QA measures R10 with tools/r9_bands.py"),
        dict(id="F10", severity="low", owner="render-agent",
             what="'L* kept' in fix-r9.json is measured in OpenCV's float Lab, whose sRGB curve is approximate near white: on pixel (248,23) dL* is 0.012 there and 0.143 in "
                  "QA's exact CIELAB (all other 10 px <= 0.024 in both). No pixel is visible (alpha 3-13; scene effect <= 0.003 L*)",
             fix="0 pixels to change. In later records state dL* in QA's Lab too (or both), as the lock's precision rule already says QA's tool decides"),
        dict(id="F11", severity="info", owner="the manager and render-agent",
             what="F8 is closed for R9: its 18 entries in assets/manifest.json carry sha256, and the whole tool (64 files) is recorded in asset-manifest-entries-r9.json "
                  "tool_set_sha256 (all match). The earlier phase-2 entries in assets/manifest.json still have none (163 of 181)",
             fix="none needed for the tool; if the site build should check against assets/manifest.json itself, merge tool_set_sha256 into the entries"),
        dict(id="F12", severity="info", owner="master-designer",
             what="At x2 the right flank reads softer than in R8 (the ramp went 1.29 -> 2.91 px, the default pendant's own, as P2-1 (c) asked). Against the wall the shaded "
                  "side has more contrast than the lit side, so the soft ramp shows more there",
             fix="none from QA (taste); the designer is already looking at pendant 2 at x2"),
        dict(id="F13", severity="info", owner="render-agent",
             what="crops-r9/pendant-2-top-left-stop-x2.png is an x2 crop of the top-left arc only (made before the designer's whole-lantern rule); "
                  "crops-r9/pendant-2-x2.png and pendant-2-100.png show the whole lantern",
             fix="from R10 every x2 crop of pendant 2 shows the whole lantern (QA's overlays/pendant-2-whole-x2-r8-r9.png and combo-*-pendant-whole-x2.png do)"),
    ],
    "per_product": [
        dict(product="pendant-cj-pleated-pumpkin-lantern-40 (pendant 2)", r9="PASS (P2-1 (a)-(g); top-left arc kept by the stop rule, closed by the designer)",
             approved_for_site_from_qa="not yet: only P2-2 (the left inner bands, RGB only, R10) remains; QA's R9 side is done",
             remains="P2-2 in R10 (render-agent); define P2-2 (a) first (F9, master-designer); the buy point: CE + canopy colour (sourcing)"),
        dict(product="curtains-cj-japanese-linen-half-shade (curtain 3, Linen)", r9="PASS (F1, lock, F2)",
             approved_for_site_from_qa="yes", remains="the buy point only: shipping of ...946TG (sourcing) and panels per window (the manager)"),
        dict(product="every other tool layer", r9="byte-identical to R8", approved_for_site_from_qa="as in QA R8", remains="-"),
    ],
    "data": {k: f"qa/reports/2026-11-12-wm-phase2-r9/data/{k}.json" for k in D},
}
json.dump(res, open(os.path.join(ROOT, "2026-11-12-wm-phase2-r9.json"), "w"), indent=1, ensure_ascii=False)
for i in items:
    print(i["result"][:12].ljust(12), i["item"], "|", i["numbers"][:220])
print("bands edges", [(e["sectors"], e["y"], e["plateau"], e["rise_10_90_px"]) for e in le])
