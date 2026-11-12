#!/usr/bin/env python3
"""qa-agent 2026-11-12 (R8): the verdict file qa/reports/2026-11-12-wm-phase2-r8.json, built from data/*.json (no image is read here)."""
import json
import os

OUT = "/home/user/homedesign-app/qa/reports/2026-11-12-wm-phase2-r8"
D = {k: json.load(open(os.path.join(OUT, "data", k + ".json"))) for k in
     ("scope", "holders", "curtains", "specks-detail", "integrity-r8", "grade", "lock", "shadow", "encode", "manifest", "wmt3", "designer-checks", "combos")}
sc, ho, cu, sd, it, gr, lk, sh, en, mf, wt, dc = (D[k] for k in ("scope", "holders", "curtains", "specks-detail", "integrity-r8", "grade", "lock", "shadow",
                                                                    "encode", "manifest", "wmt3", "designer-checks"))
c3 = cu["curtain3_colour"]
lock_files = {k: v for k, v in lk.items() if isinstance(v, dict) and "lines" in v}
fc = it["full_cross"]
res = {
    "id": "qa-2026-11-12-wm-phase2-r8",
    "date": "2026-11-12",
    "author": "qa-agent",
    "scope": "warm-modern living-room tool, phase 2, R8 (0-token code fixes on the R7 layers) + the WM-T3 clay + the designer's open R7 checks "
             "(3.2.1-3.2.3, 3.3.2, 3.4; the coordinator's addendum) + curtain 3 against the designer's lock (docs/proposals/wm-r8-eye-2026-11-12.md)",
    "cost": "0 tokens; no var2, no network, no commits; new files only",
    "verdict": "PASS",
    "bottom_line": "R8 passes: the four fixes do what fix-r8.json says, only the claimed products changed, and the phase-2 acceptance holds over "
                   "the full cross (2,592 compositions). No layer fails before the tool. WM-T3 passes in QA's own clay for the in-tool pieces. "
                   "Open items are records and rules, not pixels (findings).",
    "items": [
        dict(item="1 scope: files", result="PASS", numbers=f"{len(sc['changed'])} of {len(sc['files'])} tool files changed (candle-holders, curtains 180502, 554205, Linen: "
             f"layer + shadow each); {sc['unchanged_count']} byte-identical to R7"),
        dict(item="1 scope: composites", result="PASS", numbers=f"changed px outside the changed products' regions: {sc['composites_outside_total']} in all 13 scenes "
             "(3 defaults + 10 variant truths); 180502 / 554205 changed only in the bench zone x 130-240, y 1178-1213"),
        dict(item="2 holders: nothing outside the mark box", result="PASS", numbers=f"{ho['changes']['ungraded']['px']} px changed, box {ho['changes']['ungraded']['box']}, "
             f"outside R8's box {ho['changes']['ungraded']['outside_r8_mark_box']}"),
        dict(item="2 holders: nothing added", result="PASS", numbers=f"darker px: ungraded {ho['changes']['ungraded']['darker_px']}, graded {ho['changes']['graded']['darker_px']}"),
        dict(item="2 holders: <= 2/255 between the feet", result="PASS (with F4)", numbers=f"the gap (x >= 1718): max {ho['remaining']['rest_of_gap']['max']}/255, 0 px > 2; "
             f"scene dL* min {ho['scene_set_B_vs_base_on_marks']['r8']['gap_dL_min']}; A's own fan faded over x 1710-1717: max {ho['remaining']['a_fan_fade_10px']['max']}/255"),
        dict(item="2 holders: each foot's own shadow = the frozen recipe", result="PASS", numbers=f"B identical ({ho['own_fields']['B']['px']} px); A identical except "
             f"{ho['own_field_tolerance_sensitivity']['1.5']['changed_on_own_A']} px at its shoulder column x 1710 (<= 7/255 lighter); "
             f"recipe fingerprint min 0.616, direction [18.8, 55.8] vs [17.1, 54.3]"),
        dict(item="3 curtain 3: specks, literal rule", result="PASS in the scene / letter: 11 soft-edge px (F1)", numbers="ungraded 0, graded alpha 255 0, set-B truth 0; "
             f"graded alpha > 0: {sd['graded_literal_hits_alpha_range']} alpha, x {sd['graded_literal_hits_x_range']}, composite effect <= {sd['literal_hits_composite_effect_levels_max']} level"),
        dict(item="3 curtain 3: specks, R8's wide rule", result="PASS (0 in R8's Lab; 3 at the threshold in QA's)", numbers=json.dumps(sd["wide_rule_margins_r8_ungraded"])),
        dict(item="3 curtain 3: L* kept on the fixed px, nothing else changed", result="PASS (with F2)", numbers=f"dL vs the global factor on the specks max "
             f"{cu['curtain3_specks']['speck_step']['dL_on_specks_vs_global_factor_max']}; a*b* outside the specks p99.9 {cu['curtain3_specks']['speck_step']['dab_outside_specks_p999']} "
             f"except the final pass's {sd['outside_mask_file']['dab_gt3_px']} px (not in the mask file)"),
        dict(item="3 curtain 3: lit fabric L*", result="REPORTED", numbers=f"same mask {c3['measured']['r8']['curtains-v3']['same_mask']['L']} (OpenCV 72.99; R8 73.0); "
             f"lit (> p25) {c3['measured']['r8']['curtains-v3']['lit_fabric_L_above_p25']['L']}; card Linen L* {c3['cards']['linen']['L']}; card-ratio expectation "
             f"{c3['expected_L_by_card_ratio']}; in-room Y ratio to 180502 {c3['in_room_ratio_Y_v3_over_180502']} vs card {c3['card_ratio_Y_linen_over_180502']}"),
        dict(item="3 curtain 3 vs the designer's lock", result="L* PASS, h PASS, C* on the upper edge (F3)", numbers=json.dumps(c3["lock_check"])),
        dict(item="3 true length 12 / 22 cm", result="PASS", numbers={k: (v["hem_height_above_floor_cm"], v["max_abs_cm"]) for k, v in cu["true_length"].items()}),
        dict(item="4 bench break and contact", result="PASS", numbers={k: {t: (v[t]["m1_break_dL"], v[t]["m2_break_dL"], v[t]["m1_contact_multiply"], v[t]["hem_band_dL"]) for t in ("r7", "r8")}
                                                                       for k, v in cu["bench"].items() if k in ("default", "curtains-v2", "curtains-v3")}),
        dict(item="5 swap-diff over the full cross", result="PASS", numbers=f"{fc['n_combos']} x 3 sets x 2 paths = {fc['n_composites']}; worst {fc['worst']}; "
             f"swap-diff outside 0 ({it['swap_diff_defaults_outside_total']} over {len(it['swap_diff_defaults'])} toggles)"),
        dict(item="5 recomposite p99.9 <= 2, max <= 6", result="PASS", numbers={s: {p: (v["p999_region"], v["max"]) for p, v in it["recomposite_defaults"][s].items()} for s in "ABC"}),
        dict(item="5 shell lock", result="PASS", numbers=f"worst p90 {max(v['worst_p90_all'] for v in lock_files.values())} (<= 9.6) on {len(lock_files)} files; R8 = R7"),
        dict(item="5 one v3c grade", result="PASS", numbers={k: v["residual_median"] for k, v in gr["r8"].items()}),
        dict(item="5 encoding gate", result="PASS as a file proxy (F7)", numbers={k: {w: (m["scene_on_rect"]["p99"], m["scene_on_rect"]["p999"], m["scene_on_rect"]["over8"],
                                                                                   m["scene_on_rect"]["de00_p99"]) for w, m in v["widths"].items()} for k, v in en["layers"].items()}),
        dict(item="6 manifest integrity", result="PASS (with F8)", numbers=f"manifest-r8: {mf['manifest_r8']['paths']} paths, missing {len(mf['manifest_r8']['missing'])}, "
             f"recorded sha256 {mf['manifest_r8']['recorded_sha256_count']} (base, matches); assets/manifest.json: {mf['assets_manifest_r8']['entries']} R8 entries present and "
             f"identical, sha256 recorded {mf['assets_manifest_r8']['with_sha256']}"),
        dict(item="6 no supplier image", result="PASS", numbers=f"{mf['supplier_images']['repo_images_checked']} repo images vs {mf['supplier_images']['supplier_images_compared']} "
             f"supplier images, min dHash {mf['supplier_images']['min_hamming_256_overall']}/256 (only near-white full-canvas layers)"),
        dict(item="7 WM-T3 clay", result="PASS (with F5)", numbers=dict(qa_in_tool_min=wt["in_tool_min"], at=wt["in_tool_min_at"], moves=wt["moves_vs_1_9_4"],
                                                                        bowl=wt["bowl_point"], render_agent=wt["render_agent_in_tool_worst"])),
        dict(item="addendum 3.2.1 554205 bottom hue", result="PASS", numbers=dc["3.2.1_554205_bottom_hue"]["result"]["554205 (v2)"]),
        dict(item="addendum 3.2.2 Linen band under the hem", result="PASS (in base.png: the bench facet; outside the camera frame)",
             numbers={k: dc["3.2.2_linen_band_under_hem"][k] for k in ("v3_alpha_gt0_px", "v3_shadow_min", "truth_minus_base_L_max_abs", "band_in_base")}),
        dict(item="addendum 3.2.3 Linen weave vs SKU photo", result="PASS (the photo has the crosshatch too)", numbers=dc["3.2.3_linen_weave_vs_sku"]["result"]),
        dict(item="addendum 3.3.2 cup B soft edge", result="PASS (the cup's own lit edge; no dragged boucle)", numbers=dc["3.3.2_travertine_B_cup_left_edge"]),
        dict(item="addendum 3.4a bowl edge halo", result="PASS", numbers={k: v for k, v in dc["3.4a_black_bowl_right_edge"].items() if k != "rows"}),
        dict(item="addendum 3.4b table-edge dots", result="RECORDED (in base.png, the approved phase-1 cut; untouched)", numbers=dc["3.4b_table_edge_under_throw"]),
        dict(item="combinations (6, seed 812)", result="PASS", numbers="overlays/combos-r8-sheet.jpg; all natural"),
    ],
    "findings": [
        dict(id="F1", severity="low", owner="render-agent", title="curtain 3: 11 literal-rule pixels at the room-side soft edge (alpha 3-13, x 248-261) of the graded layer",
             fix="0 tokens: neutralise a*b* on alpha < 255 edge pixels too (or the designer limits the rule to alpha 255); invisible today (<= 0.77 level, 0 in the scene)"),
        dict(id="F2", severity="low", owner="render-agent", title="records: the speck mask file lacks the 44-px final pass; 'alpha_unchanged' holds for the ungraded sources only "
             "(graded alpha moved at 7 / 6 / 64 soft-edge px, <= 20 levels)", fix="save the final-pass mask; word the record"),
        dict(id="F3", severity="low", owner="master-designer", title="curtain 3 C* 12.52 (QA) / 12.503 (OpenCV) sits on the lock's upper edge 12.5",
             fix="state the method and precision of the lock, or 12.6; no pixel change"),
        dict(id="F4", severity="low", owner="master-designer", title="the WM-T3 between-the-feet rule as written reads 94/255 on R8 itself (A's own fan lies inside the box zone)",
             fix="define the zone (e.g. from 8 px past A's own field, or R8's x 1718-1752 moved with the pair) before the WM-T3 QA"),
        dict(id="F5", severity="medium", owner="master-designer + the coordinator", title="WM-T3 owner question: 'all clearances 0.023 and up' is not what the clay reads",
             fix="send the measured floor: A x B and candles x set C 0.0206-0.0207 (both clays); ceramic A x B 0.0195 (D17 cylinder) / 0.0211 (card shape); bowl x rug 0.015 "
                 "across the table's front edge (0.020-0.021 at 1.9.4), a 'hidden overlap' pair in the slots file: confirm in 1.9.5"),
        dict(id="F6", severity="info", owner="master-designer", title="180502 break: its top edge steps 2.8 L* per row against the cloth's 0.27 (a visible band at x4; 100% reads one line)",
             fix="taste: the designer's call; numbers only"),
        dict(id="F7", severity="info", owner="frontend-dev + qa-agent", title="the phase-2 layers have no site encodes yet (make-house builds the cushions only)",
             fix="when phase 2 is wired, run e2e/encoding.spec.ts on them; the file proxy passes with room (p99 2, p99.9 <= 3, 0 %, dE00 p99 <= 2.6)"),
        dict(id="F8", severity="info", owner="the coordinator / render-agent", title="no sha256 in assets/manifest.json (0 of 1,233) and only base's in manifest-r8",
             fix="QA recorded sha256 for every R8 file (data/manifest.json); add sha256 to the entries if hashes are to be checked against a record"),
    ],
    "closed_by_the_way": "the designer's wm-r8-eye 4.1 in_room note: both cards already carry in_room on the rendered SKU (CJYD218713946TG; 12000029601125492), commit 6737e3aa",
    "data": {k: f"qa/reports/2026-11-12-wm-phase2-r8/data/{k}.json" for k in D},
}
json.dump(res, open("/home/user/homedesign-app/qa/reports/2026-11-12-wm-phase2-r8.json", "w"), indent=1, ensure_ascii=False)
print("written", len(res["items"]), "items,", len(res["findings"]), "findings")
