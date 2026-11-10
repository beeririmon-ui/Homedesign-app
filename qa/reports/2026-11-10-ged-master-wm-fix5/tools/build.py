"""qa-agent 2026-11-10: G-ED round 5 on the warm-modern master bedroom: warm-modern-MB-A-fix5 (P6b, mb1-fix7.json) against fix4, the frame
QA checked last (qa/reports/2026-11-10-ged-master-fix6.json, register v11). From data/*.json (diff, lumbar, duvet, ring, gap, cast-shadow,
fidelity, guardrails, shadow-floor, dl1-wm) and the overlays. Writes qa/reports/2026-11-10-ged-master-wm-fix5.json and register v12
(qa/reports/ged-register-2026-11-10-r12.json): r11 with only the warm-modern master entry changed (a new key for fix5, its
master_superseded_by targets, the change note). Usage: ~/.venvs/motion/bin/python -I build.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5/data")
J = {n: json.load(open(os.path.join(D, n + ".json"))) for n in
     ("diff", "lumbar", "duvet", "ring", "gap", "cast-shadow", "fidelity", "guardrails", "shadow-floor", "dl1-wm")}
REC = json.load(open(os.path.join(REPO, "assets/renders/master/editorial-2026-11-07/mb1-fix7.json")))
df, lu, du, ri, gp, cs, fi = J["diff"], J["lumbar"], J["duvet"], J["ring"], J["gap"], J["cast-shadow"], J["fidelity"]
GR = {os.path.basename(g["file"]): g for g in J["guardrails"]}
SF, DL = J["shadow-floor"], J["dl1-wm"]
FL, FR = fi["left (QA's patch)"], fi["right (lamp's shadow)"]
G4 = fi["G-ED.4"]
RR, RL = ri["right pillowcase top"], ri["left pillowcase top"]
b2 = du["below_contact_plus_2px"]
g4, g5 = gp["fix4"], gp["fix5"]
c4, c5 = cs["fix4"], cs["fix5"]

pillow_note = (f"P6b (seedream-5-pro, fix5): both caramel pillowcases plain envelopes, no flange, flat strip, stitch line or piping; the "
               f"seam on the edge and soft pointed corners, as in the card photo. QA's patch Lab {FL['fix5']['Lab']}, dE00 {FL['fix5']['dE00_vs_swatch']} "
               f"against the card swatch {fi['swatch']} (brief: <= 5; fix4 {FL['fix4']['dE00_vs_swatch']}), h {FL['fix5']['hue']} against {fi['swatch_hue']}; "
               f"L* against the lit wall {fi['L_left_minus_wall']['fix5']} (the card's {fi['card_L_minus_photo_white']}). Washed linen: crinkles kept "
               f"(x{FL['grain_ratio_fix5_over_fix4'][1]} at sigma 4), the fine weave softer (x{FL['grain_ratio_fix5_over_fix4'][0]}). "
               f"{G4['left_pillowcase_corner_to_corner_px']} px corner to corner = the 530 px scale basis x{G4['left_vs_basis']}")
lumbar_add = (f"; fix5 (P6b): its outer 1-6 px (the top-left corner, x 1851-1862, and the shaded right edge) lay inside the comp mask and were "
              f"rewritten ({lu['changed_gt0_inside']} px of QA's lumbar mask changed, max {lu['max_change_inside']} levels; the right edge within 1.7 px); "
              f"no seam at x4, the bouclé face untouched; {int(sorted(G4['lumbar_width_px_rows_840_910'])[4])} px against the {G4['left_pillowcase_corner_to_corner_px']} px pillowcase "
              f"({G4['lumbar_over_pillowcase']} = x{G4['lumbar_ratio_vs_card']} of 50/74)")

out = {
    "id": "2026-11-10-ged-master-wm-fix5", "date": "2026-11-10", "by": "qa-agent",
    "follows": "qa/reports/2026-11-10-ged-master-fix6.json (round 4: warm-modern fix4 not_yet, the flanges only; the gap's spot was closed there)",
    "inputs": {"frame": "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix5.png",
               "compared_with": "warm-modern-MB-A-fix4.png (the frame QA checked last)",
               "record": "assets/renders/master/editorial-2026-11-07/mb1-fix7.json", "script": "mb1_fix7.py",
               "masks": ["warm-modern/raw/P6b-comp-mask.png", "P6b-seg-mask.png", "P6b-protect-v2.png", "P6b-protect.png", "P6b-mask.png"],
               "brief": "briefs/render-master-P6b-2026-11-10.md", "gate": "docs/ops/quality-gate-g-ed-2026-11-07.md"},
    "G-ED.8": {
        "verdict": "pass",
        "numbers": {"changed_px_gt0": df["changed_px_gt0"], "changed_px_gt2": df["changed_px_gt2"], "changed_box": df["changed_box_gt0"],
                    "outside_comp_mask": df["changed_gt0_outside_comp_mask"], "outside_crop": df["changed_gt0_outside_crop"],
                    "in_20px_band_outside_mask": df["changed_gt0_in_20px_band_outside_mask"], "components_gt2_15px": len(df["components_gt2_15px"]),
                    "comp_mask_px": df["comp_mask_px"], "comp_mask_beyond_hand_mask": df["comp_mask_outside_hand_mask"],
                    "in_protect_v2": df["changed_in_protect_v2"], "in_prepared_protect": df["changed_in_prepared_protect"],
                    "prepared_protect_split": df["prepared_protect_split"], "beyond_segments_max_px": df["changed_outside_segments_distance_px"]["max"],
                    "P6b_input_is_fix4_crop": df["input_is_fix4_crop"]},
        "read": "QA's own diff (8-bit, any channel > 0) reproduces render-agent's numbers exactly: 224,508 px, all in x 1474-2647, y 673-956, 0 outside the comp mask, 0 in a 20 px band round it, 0 outside the crop; one area at > 2 levels on a 15 px dilation. The region (the comp mask) is declared in mb1-fix7.json, so G-ED.8 is measured against it. The changes beyond the pillowcase segments reach 12.6 px at most: the declared 12 px ring.",
    },
    "claims_check": {
        "lumbar_0px": f"true only in render-agent's colour mask (protect-v2: 0). With QA's own lumbar mask (lumbar.py): {lu['changed_gt0_inside']} px changed ({lu['ring_1px']['changed_gt2']} in its outermost px ring at > 2 levels; max {lu['max_change_inside']} levels): the top-left corner left of x 1863 (the protect polygon starts at x 1866) and the shaded right edge (L* < 45, outside the colour mask). The right edge moved out by up to 1.7 px at y 824-848; the left edge within 0.2 px. Not visible at 100 % or x4 (overlays/seam-lumbar-top-left.jpg, seam-lumbar-right.jpg).",
        "duvet_0px": f"true in render-agent's colour mask. More than 2 px below the pillows' contact line: {b2['changed_gt0']} px changed, {b2['changed_gt2']} above 2 levels, max {b2['max_level']}; the comp mask has {du['mask_islands_on_duvet']['count']} small islands on the duvet ({du['mask_islands_on_duvet']['px']} px, mean change {du['mask_islands_on_duvet']['mean_abs_level_change']} levels). Invisible at x6 (seam-duvet-specks-*.jpg).",
        "colour": f"confirmed with QA's own CIEDE2000 (checked on Sharma 2005 pairs): left {FL['fix5']['dE00_vs_swatch']} (fix4 {FL['fix4']['dE00_vs_swatch']}), fix5 against fix4 {FL['dE00_fix5_vs_fix4']}; right (in the lamp's shadow) {FR['fix5']['dE00_vs_swatch']}, {FR['dE00_fix5_vs_fix4']} against fix4",
        "envelopes": "confirmed: no flange, flat strip, stitch line or piping on either pillowcase at 100 %, x2 and x4 (seam-left-end, seam-right-end, bed-head-100)",
        "record_wording": "render-agent's 'kept: lumbar 0 px, duvet 0 px' should read 'in the colour protect masks'; for the next pass, protect a product with its segment (segment-map 10-12 'cream boucle pillow'), not a polygon plus a colour threshold",
    },
    "G-ED.9": [
        {"where": "the gap between the pillowcases (deviation 1)", "verdict": "pass",
         "finding": f"one dark slit, the cream back pillow's band (lit at the top, shaded lower) and the right pillowcase's plain edge, continuous from the pillows' tops down to the lumbar's top; no blob, no doubled or stepped edge at x4. The old spot box: L* median {g5['spot_box_L_median']} (fix4 {g4['spot_box_L_median']}), grain {g5['spot_box_grain']} (fix4 {g4['spot_box_grain']}, fix3 0.85), range p10-p90 {g5['spot_box_L_p10_p90']}: structure, not a flat fill (overlays/seam-gap.jpg)"},
        {"where": "the 12 px ring on the cream back pillows (deviation 2)", "verdict": "pass, with a note",
         "finding": f"no dark dashes or contact lines of the old flange left. Above the right pillowcase (x 2080-2440) the ring is a lighter, smoother band: L* {RR['ring_L']} against {RR['back_pillow_above_L']} on the pillow just above (p50 {RR['ring_minus_above_L_p10_p50_p90'][1]:+}, p90 {RR['ring_minus_above_L_p10_p50_p90'][2]:+}), a step of {RR['step_across_edge_L_p50_p90'][0]}-{RR['step_across_edge_L_p50_p90'][1]} L* across the mask edge, grain {RR['grain_ring']} against {RR['grain_above']}. At 100 % it reads as the back pillow's own lower edge (ring-tops-right-100.png); the straight edge 12 px above the pillowcase shows only at x4-x5 (seam-ring-top-right-a/b.jpg). Above the left pillowcase: L* {RL['ring_minus_above_L_p10_p50_p90'][1]:+} (median), grain {RL['grain_ring']} against {RL['grain_above']}: fine",
         "fix": "optional, code, 0 tokens (render-agent; the designer decides in the eye check): in the ring above the right pillowcase, match L* to the 3-12 px of back pillow above with a vertical gain ramp, keep a 2-3 px darker contact line on the pillowcase's top edge, and add the grain back (L* high-pass from the pillow 12-24 px higher, as mb1_fix5's gap method); QA re-checks G-ED.8/9 in that box only"},
        {"where": "the pillowcase ends against the walnut headboard and the cream back pillows", "verdict": "pass",
         "finding": "right end: the second back pillow now shows down the pillowcase's end, as on the left; the headboard's groove runs straight through the mask edge; left end: the flange and its stitch line are gone, the back pillow continues; the revealed cream is a touch smoother than the original at x4 only (seam-right-end.jpg, seam-left-end.jpg, seam-back-pillow-left-end.jpg)"},
        {"where": "the lumbar's edges", "verdict": "pass",
         "finding": "no seam along the mask edge inside the corner, the bouclé bumps continue; see claims_check.lumbar_0px"},
        {"where": "the pillows' bottom edge on the duvet, the mask islands", "verdict": "pass",
         "finding": "clean contact line; the islands are invisible at x6 (seam-duvet-edge-*.jpg, seam-duvet-specks-*.jpg, seam-duvet-left-corner.jpg)"},
    ],
    "deviations": {
        "1 the gap strip is seedream's": "accept. The protected band's right side was the old flange itself (v1's doubled, stepped edge); seedream's gap is clean and continuous at x4, and the spot does not come back.",
        "2 the 12 px ring on the back pillows": "accept, with the note above (G-ED.9). The optional 0-token tone-and-grain match on the right pillowcase's top is the designer's call.",
        "3 the cushion's cast shadow": (f"accept seedream's; do NOT restore the old one. The core is darker and wider low down (L* < 14 at y 880: {c5['rows']['880']['px_lt14']} px against {c4['rows']['880']['px_lt14']}; box median L* {c5['box_median_L']} against {c4['box_median_L']}, mean {c5['box_mean_L_2210_2330_y820_925']} against {c4['box_mean_L_2210_2330_y820_925']}), "
                                         "and that is the right geometry: the lumbar leans back, touching the pillowcase at its top and standing off it at its base, so the shadow widens downward, away from the light on the left (the same direction as the olive's shadow on the wall). "
                                         "Restoring it in code would paste fix4's pixels (the old linen folds) into seedream's new linen on the product, a texture seam. If the designer finds it heavy: a 0-token lift of the core only (L* < 14 in x 2215-2330, y 840-925, feathered, toward fix4's median), no paste."),
        "4 the new linen is softer at x2": f"accept. Fine weave x{FL['grain_ratio_fix5_over_fix4'][0]} (left) and x{FR['grain_ratio_fix5_over_fix4'][0]} (right), the crinkle scale x{FL['grain_ratio_fix5_over_fix4'][1]} / x{FR['grain_ratio_fix5_over_fix4'][1]}: it reads as washed linen, like the card photo.",
    },
    "fidelity": {
        "pillowcases-cj-pure-linen-envelope-pair-48x74 (caramel-pairs)": {"G-ED.2": "yes: plain envelope, pointed corners", "G-ED.3": "yes", "G-ED.4": "yes", "verdict": "yes (was partly)", "dot": "yes", "note": pillow_note},
        "cushions-cj-boucle-teddy (milk-tea-color, 30x50)": {"verdict": "yes (unchanged)", "note": lumbar_add.lstrip("; ")},
        "G-ED.6-7": "pass: no new items; the cream strips now seen at both ends are the bedding set's own back pillows, already in the bedding row",
        "G-ED.14-16": "pass: unchanged; no text or mark on the linen; caramel linen is in the palette",
    },
    "guardrails": {
        "G-ED.11": (f"no split flag (shadows b* {GR['warm-modern-MB-A-fix5.png']['shadows_10pct_Lab'][2]}, highlights {GR['warm-modern-MB-A-fix5.png']['highlights_10pct_Lab'][2]}, one amber light). "
                    f"Deep shadow p1 {GR['warm-modern-MB-A-fix5.png']['shadow_floor_L_p1']} (fix4 {GR['warm-modern-MB-A-fix4.png']['shadow_floor_L_p1']}, MB-A {GR['warm-modern-MB-A.png']['shadow_floor_L_p1']}): information under the gate's Q-ED7 ruling, as in MB1 and for the living room's final_test ed8 (p1 {SF['warm-modern-A-ed8']['p1']}). "
                    "OPEN QUESTION: the warm-modern Bible 1.0 (approved, WMB1), 'the story and the detail', says 'black point a bit deeper (L* 8 at least)'. If that floor applies to the warm-modern story frames, both this frame and ed8 fail it today; the fix is code, 0 tokens (a toe on L* < 10, about +2-3 L* at p1, highlights untouched). The deepest 1 % sits in crevices: the throw's folds, under the nightstand, the sandals, the window's bronze frame (overlays/shadow-floor-map.jpg). Owner of the ruling: master-designer (Q-ED7) and the manager"),
        "G-ED.12": f"pass: finished {GR['warm-modern-MB-A-fix5.png']['clipped_254_pct']} %, raw P6b-seedream {GR['P6b-seedream.png']['clipped_254_pct']} % (the lit floor-lamp shade and the window)",
    },
    "eye_inputs": {
        "for": "master-designer: G-ED.10 and G-ED.13 have never been written for the warm-modern master; QA's half of G-ED.10: no halos round the new pillowcases at 100 %",
        "look_at": ["warm-modern-MB-A-fix5.png at full size", "overlays/bed-head-100.jpg", "overlays/ring-tops-right-100.png (the ring band, deviation 2)",
                    "overlays/seam-lumbar-shadow-right.jpg (deviation 3)", "docs/master-bedroom-comparison-2026-11-07.md §2 ('Siesta of August, 18:30')"],
        "DL1": (f"met: the master is darker than the living room ed8: the plaster above the niche L* {DL['warm-modern-MB-A-fix5']['wall']['median']} against {DL['warm-modern-A-ed8']['wall']['median']} above the triptych; "
                f"frame median {DL['warm-modern-MB-A-fix5']['frame_median']} against {DL['warm-modern-A-ed8']['frame_median']}, p90 {DL['warm-modern-MB-A-fix5']['frame_p90']} against {DL['warm-modern-A-ed8']['frame_p90']}"),
        "G-ED.11/12": "above",
    },
    "rows": {"yes": 12, "partly": 0, "no": 0},
    "state": {"warm-modern-MB-A-fix5": "almost",
              "why": "every QA check passes and 12 of 12 rows are yes; the designer's eye (G-ED.10, G-ED.13) is still to be written, and the register keeps a frame with a pending eye at 'almost'. It goes to final_test on the designer's pass, with no further QA round unless a code fix is applied (then G-ED.8/9 on that box only). If the warm-modern floor (L* 8) is ruled to apply, it is not_yet until the 0-token toe lift."},
    "open": [
        "master-designer: G-ED.10 and G-ED.13 on fix5; decide the two optional code touches (the ring band, the shadow's core)",
        "master-designer + manager: Q-ED7 for warm modern (the Bible's L* 8 against the gate's 'information'), for this frame and ed8",
        "render-agent (record only): reword 'lumbar 0 px / duvet 0 px' as 'in the colour protect masks'",
    ],
    "register": "qa/reports/ged-register-2026-11-10-r12.json",
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-10-ged-master-wm-fix5.json"), "w"), ensure_ascii=False, indent=1)

# register v12: r11 with only the warm-modern master entry changed
V11P = "qa/reports/ged-register-2026-11-10-r11.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V11P))))
reg.update(version=12, supersedes=V11P, id="ged-register-2026-11-10-r12", date="2026-11-10", by="qa-agent")
reg.pop("changes_from_v10", None)
w_rows = copy.deepcopy(reg["master"]["warm-modern-MB-A-fix4"]["rows"])
for r in w_rows:
    if r["card_id"] == "pillowcases-cj-pure-linen-envelope-pair-48x74":
        r.update(verdict="yes", dot="yes", note=pillow_note, why=pillow_note, faithful="yes")
        r.pop("fix", None)
    if r["card_id"] == "cushions-cj-boucle-teddy":
        r["note"] = r["why"] = r["note"] + lumbar_add
reg["master"]["warm-modern-MB-A-fix5"] = dict(
    file="assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix5.png", state="almost", rows=w_rows,
    record="qa/reports/2026-11-10-ged-master-wm-fix5.json",
    state_source="QA round 5 (qa/reports/2026-11-10-ged-master-wm-fix5.md): P6b made the caramel pillowcases plain envelopes; 12 of 12 yes; G-ED.8 pass (0 px outside the comp mask), G-ED.9 pass with a note (the ring band), G-ED.11/12 pass under Q-ED7. Eye pending: master-designer G-ED.10 and G-ED.13",
    designer_eye={"G-ED.10": "pending", "G-ED.13": "pending", "DL1": "met (QA: darker than the living room ed8)"},
    note="TEST frame (MB1), not for the site; the site does not read this section")
sup = reg["master_superseded_by"]
for k in ("warm-modern-MB-A", "warm-modern-MB-A-fix1", "warm-modern-MB-A-fix3", "warm-modern-MB-A-fix4"):
    sup[k] = "warm-modern-MB-A-fix5"
reg["changes_from_v11"] = ["master: warm-modern-MB-A-fix5 almost (P6b: the caramel pillowcases plain envelopes, 12/12 yes; the designer's eye G-ED.10/13 pending)"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-10-r12.json"), "w"), ensure_ascii=False, indent=1)

# the same validation as build.py v11 (site/tools/lib/qa-frames.ts rules), and nothing but the warm-modern master entry changed
r11 = json.load(open(os.path.join(REPO, V11P)))
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = [f"{p}.{k}" for p in ("frames", "closeups", "master") for k, f in (reg.get(p) or {}).items()
       if f.get("state") not in S or any(not isinstance(r.get("card_id"), str) or r.get("dot") not in Dt or (r.get("units_in_frame") is not None and not 1 <= r["units_in_frame"] <= 12) for r in f.get("rows", []))]
same = [k for k in r11 if k in reg and k not in ("id", "version", "supersedes", "master", "master_superseded_by") and r11[k] != reg[k]]
m_changed = [k for k in reg["master"] if r11["master"].get(k) != reg["master"][k]]
print("v12 bad", bad, "| other top keys changed:", same, "| master keys changed:", m_changed,
      "| superseded:", reg["master_superseded_by"], "| wm fix5:", reg["master"]["warm-modern-MB-A-fix5"]["state"], sum(r["verdict"] == "yes" for r in w_rows), len(w_rows))
