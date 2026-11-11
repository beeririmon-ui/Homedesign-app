"""
qa-agent 2026-11-11: builds qa/reports/2026-11-11-ged-wm-fix6-ed9.json from data/*.json, and register v13
(qa/reports/ged-register-2026-11-11-r13.json): r12 with only the two frames of this round changed - the master's
warm-modern-MB-A-fix6 (new key, replaces fix5) and the living room's warm-modern-A-ed9 (new key, replaces ed8) - plus the two
superseded_by maps that point the older keys of those two frames at the new ones. Then the same validation as build.py v12 (the rules
of site/tools/lib/qa-frames.ts), and a diff against r12 that lists every key that changed. The site's own reader is run on the
result by check_register.ts.
Run order: master_diff.py, b_edges.py, toe_numbers.py, blotch.py, products_dark.py, floor_all_styles.py, crops.py, build.py,
then site/node_modules/.bin/tsx check_register.ts.
Usage: ~/.venvs/motion/bin/python -I build.py.
"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-11-ged-wm-fix6-ed9")
D = lambda n: json.load(open(os.path.join(OUT, "data", n)))
MD, BN, ED, GR, BL, PD, FL = (D("master-diff.json"), D("b-numbers.json"), D("ed9-diff.json"), D("guardrails.json"), D("blotch.json"),
                              D("products-dark.json"), D("floor-all-styles.json"))
gm, ge = GR["warm-modern-MB-A-fix6.png vs warm-modern-MB-A-fix5.png"], GR["warm-modern-A-ed9.png vs warm-modern-A-ed8.png"]
R12P = "qa/reports/ged-register-2026-11-10-r12.json"
R13P = "qa/reports/ged-register-2026-11-11-r13.json"

bowl = PD["ed9"]["black bowl body (bowl-cj-matte-black-bowl-20)"]
muslin = PD["fix6"]["pecan muslin throw, deep folds"]
rep = {
    "id": "2026-11-11-ged-wm-fix6-ed9",
    "date": "2026-11-11",
    "by": "qa-agent",
    "follows": "qa/reports/2026-11-10-ged-master-wm-fix5.json (round 5: fix5 almost, eye pending); docs/master-bedroom-comparison-2026-11-07.md §6 (eye pass on fix5; polish (b); Q-ED7 (a))",
    "scope": "box check only (the designer: no further eye round if the numbers are inside the limits): G-ED.8 and G-ED.9 on what changed, G-ED.11's p1 / p5 / split flag, (b)'s box median and hue, G-ED.3 spot reads (black bowl, muslin, walnut), G-ED.12 as a control",
    "inputs": {
        "master": {"frame": "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix6.png", "against": "warm-modern-MB-A-fix5.png (QA round 5)",
                   "record": "assets/renders/master/editorial-2026-11-07/mb1-fix8.json", "script": "mb1_fix8.py", "toe": "q_ed7_toe.py",
                   "mask": "warm-modern/raw/fix6-b-region.png", "crops": "fix8-before-after/"},
        "living_room": {"frame": "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed9.png", "against": "warm-modern-A-ed8.png (final_test, register r8-r12)",
                        "record": "assets/renders/editorial-phase-b-2026-11-06/codefix-ed9.json", "script": "codefix_ed9.py", "crops": "codefix-ed9-before-after/"},
        "base_frames_untouched": "fix5 and ed8 are byte-identical to the commits QA checked (git: one commit each)",
        "gate": "docs/ops/quality-gate-g-ed-2026-11-07.md (1.1 from this round: G-ED.11 in warm modern; Q-ED7 closed)"},
    "master_fix6": {
        "G-ED.8": {"verdict": "pass", "numbers": {"changed": MD["changed"], "outside_b_mask": MD["outside_b_mask"], "inside_b_mask": MD["inside_b_mask"],
                                                  "b_mask": MD["b_mask"], "b_only": MD["b_only"], "cushion": {k: v for k, v in MD["cushion"].items() if k != "right_edge_vs_mask_left_edge_per_row"},
                                                  "cushion_to_mask_gap_px_per_row": MD["cushion"]["right_edge_vs_mask_left_edge_per_row"],
                                                  "duvet": MD["duvet_below_contact_plus_2px"], "ring_band_a": MD["ring_band"],
                                                  "areas_gt2_at_L_ge_20": MD["areas_gt2_at_L5_ge_20"], "toe": MD["toe_read_outside_mask"]},
                   "read": "QA's own diff reproduces render-agent's totals exactly (288,321 px; 2,910 at L* >= 20, 786 of them > 2 levels, all inside the (b) mask). Outside the mask every changed px had L* < 20 (max 16.5), 0 at L* >= 20: the toe only. The toe as it landed is one monotone curve (0 drops), +2.2 at L* 8, +1.2 at 12, +0.6 at 14, 0 from 18; hue within +-2.3 deg (p1-p99), chroma never down. The cushion: 0 px changed in QA's mask (round 5's and the same recipe on fix5), and (b)'s mask stays 2-8 px off its edge (the contact line). The duvet: 0 from (b); the 1,021 toe px in the zone below the contact line are the open book's dark photo and the mug's shadow (y 1019-1085, L* < 16.1, max 7 levels). The ring band of polish (a): 0 overlap, 0 changes."},
        "G-ED.9": {"verdict": "pass", "read": "At 100 % and x4 (also stretched): no step, halo or ghost on (b)'s edge. (b) alone (QA's empirical toe taken off both sides) adds at most 0.41 L* across the mask's edge (p99 0.26) and its own lift is ~0 on the mask's inner 2 px (p99 0.42, max 1.0): it fades out inside the mask. The wedge keeps its shape and the creases inside it (high-pass SD x0.95, correlation 0.994). Contact lines kept: along the cushion's right edge 7.1 against 8.9 in the shadow beside it (fix5: 3.5 against 3.2, no separate line); along the base on the duvet darker than the shadow above in every sampled column. No colour blotch: 0 off-family px (hue outside 20-110 deg with C* >= 3) among the 288,321 changed px; the void under the nightstand reads a smooth warm dark (h 55.4, C* 8.1), no purple or red speck at x4 stretched. The muslin folds open and stay pecan (h 53.2 -> 52.9, C* 22.7 -> 23.6, grain x0.94, corr 0.98); the walnut nightstand keeps its grain (x0.93, corr 0.99).",
                   "data": {"b": BN, "blotch": BL["fix6"], "products": PD["fix6"]}},
        "numbers": {"G-ED.11": gm | {"p5_before_after": [GR["warm-modern-MB-A-fix5.png"]["qa_quarter_size_percentiles"]["p5"], GR["warm-modern-MB-A-fix6.png"]["qa_quarter_size_percentiles"]["p5"]],
                                    "full_size_p1_info": GR["warm-modern-MB-A-fix6.png"]["full_size_percentiles_info"]["p1"],
                                    "shadows_10pct_Lab": GR["warm-modern-MB-A-fix6.png"]["shadows_10pct_Lab"], "highlights_10pct_Lab": GR["warm-modern-MB-A-fix6.png"]["highlights_10pct_Lab"]},
                    "b_box_median": {"fix5": BN["fix5"]["designer_box_median"], "fix6": BN["fix6"]["designer_box_median"], "target": [14, 15], "pass": 14 <= BN["fix6"]["designer_box_median"] <= 15},
                    "slit_median": {"fix5": BN["fix5"]["slit_median"], "fix6": BN["fix6"]["slit_median"], "shadow_brighter_than_slit": BN["fix6"]["designer_box_median"] > BN["fix6"]["slit_median"]},
                    "hue": {"core_L_lt_20_fix6": BN["fix6"]["core_L5_lt_20"], "lit_caramel_left_patch": BN["fix6"]["caramel_left_patch_lit"],
                            "caramel_right_patch_off_shadow": BN["fix6"]["caramel_right_patch_off_shadow"],
                            "delta_deg": round(BN["fix6"]["core_L5_lt_20"]["h"] - BN["fix6"]["caramel_left_patch_lit"]["h"], 1), "window_deg": 3, "pass": True},
                    "G-ED.12": {"clipped_254_pct": GR["warm-modern-MB-A-fix6.png"]["clipped_254_pct"], "unchanged": gm["clipped_254_same"]},
                    "DL1": {"median_p90_full_size": GR["warm-modern-MB-A-fix6.png"]["full_size_median_p90"], "living_room_ed9": GR["warm-modern-A-ed9.png"]["full_size_median_p90"], "met": True}},
        "deviation": {"verdict": "accepted",
                      "what": "(b)'s region follows the shadow (mask bbox x 2212-2509, y 808-922, 4 parts; the change x 2217-2489, y 819-919), not QA's box x 2215-2330, y 840-925",
                      "why": "QA measured fix5: the core (L* < 14) runs to x 2357 at y 880, 2394 at y 900 and 2483 at y 918, and starts at y ~822 (557 px of L* < 14 above y 840 inside the box's columns). A cut at the box would leave the step render-agent describes. The 2,910 half-shadow px at L* >= 20 move by +0.6 L* (median), +1.2 (p90), +2.05 at most, all on the right caramel pillowcase inside the mask, fading to 0 at its edge. Nothing on the cushion, the duvet or the ring band. The designer's box median (the number the eye ruled on) is measured in the designer's box."},
        "state": "final_test",
        "state_why": "the designer passed G-ED.10 / G-ED.13 on fix5 and ruled 'no further eye round if the numbers are inside the limits' (§6); every number is inside: p1 8.99 (8.5-9.5), p5 +0.59 (<= 3), split flag off, box median 14.46 (14-15), hue -1.5 deg (+-3); G-ED.8 / G-ED.9 pass"},
    "living_room_ed9": {
        "G-ED.8": {"verdict": "pass", "numbers": ED,
                   "read": "359,782 px changed, every one with L*(ed8) < 20 (max 17.0); 0 at L* >= 20 (> 0 and > 2 levels). One monotone curve (0 drops): +3.4 at L* 8, +1.7 at 12, +1.0 at 14, 0 from 18; hue within +-2.8 deg (p1-p99), chroma never down. The frame's median (46.23) and p90 (78.82) do not move."},
        "G-ED.9": {"verdict": "pass", "read": "At 100 % and x4: no seam, halo or blotch. The toe is one global curve, so it draws no edge. Off-family colour (hue outside 20-110 deg, C* >= 3) among the changed px: 5,615 after against 6,656 at the same px before, and every listed group keeps its hue (the figs' red-purple, the olive leaves' and the bronze frame's green-grey): object colours, not new blotches. The bowl's shadow side is smooth and even; its lower rim keeps the walnut's bounce it had in ed8 (h 53.2 -> 51.9, C*/L* 0.85 -> 0.79), no red bleed from the figs.",
                   "data": {"blotch": BL["ed9"], "products": PD["ed9"], "bowl_contour": PD["ed9_bowl_contour"]}},
        "G-ED.3_spot": {"black_bowl": {"verdict": "pass (black-espresso)", "before": bowl["before"], "after": bowl["after"],
                                       "chromaticity_after": bowl["chromaticity_after"], "neutral_white_boucle": PD["ed9"]["neutral: white boucle seat behind the bowl"]["chromaticity_after"],
                                       "espresso": PD["refs"]["espresso_chromaticity"], "card_hex": "#2F2F2E (neutral)",
                                       "read": "the body lifts from L* 5.4 to 10.2 and stays 6 L* under the Bible's espresso (16.6); its chromaticity (linear R/G 1.59, B/G 0.69) sits on the white bouclé's in the same light (1.49, 0.70), nearer than in ed8 (1.70, 0.63) and far from the walnut (2.1-2.5, 0.38-0.51): a neutral black under amber light, not brown. The core away from the contours is near-neutral (1.34, 0.78), between the light's cast and the espresso"},
                        "walnut": {"verdict": "pass (rich)", "left_drum": PD["ed9"]["walnut table, left drum base"], "right_drum": PD["ed9"]["walnut table, right drum base"],
                                   "top_edge": PD["ed9"]["walnut table, top edge"],
                                   "read": "hue kept (56.0-56.2), chroma up (C* 7.6 -> 11.7 and 10.8 -> 13.9). The grain keeps its pattern (correlation 0.97) at x0.69-0.83 of its L* amplitude: softer only in the stretch; at 100 % the drum bases read walnut with grain"}},
        "numbers": {"G-ED.11": ge | {"p5_before_after": [GR["warm-modern-A-ed8.png"]["qa_quarter_size_percentiles"]["p5"], GR["warm-modern-A-ed9.png"]["qa_quarter_size_percentiles"]["p5"]],
                                    "full_size_p1_info": GR["warm-modern-A-ed9.png"]["full_size_percentiles_info"]["p1"],
                                    "shadows_10pct_Lab": GR["warm-modern-A-ed9.png"]["shadows_10pct_Lab"], "highlights_10pct_Lab": GR["warm-modern-A-ed9.png"]["highlights_10pct_Lab"]},
                    "G-ED.12": {"clipped_254_pct": GR["warm-modern-A-ed9.png"]["clipped_254_pct"], "unchanged": ge["clipped_254_same"]},
                    "DL1": "the median and p90 do not move (46.23, 78.82); the master stays darker (44.13, 70.48)"},
        "state": "final_test (replaces ed8)",
        "state_why": "ed8's rows and the eye verdicts carry over (the toe changes no product's lit side, no outline, no count); G-ED.11 now meets the Bible floor; p5 +2.55 is inside the designer's <= 3, so no eye round (§6)",
        "owner_note": "ed8 was shown to the owner; the manager notes the toe when ed9 is shown (§6)"},
    "claims_check": {
        "totals": "render-agent's counts reproduced exactly on both frames (288,321 / 2,910 / 786; 359,782 / 0 at L* >= 20), and the percentiles to 0.01 with the gate's own guardrails.py",
        "mb1-fix8.json region_bbox": "the record gives [2213, 819, 2491, 923]; the mask file is [2212, 808, 2509, 922] in 4 parts (3 small islands up to y 808 and x 2509, unchanged). The record's box is the changed px, not the mask. Precision only",
        "mb1-fix8.json px_changed_in_duvet_below_the_base: 0": "true for (b). The whole pass also changes 1,021 dark px (toe, L* < 16.1) in the zone below the bed's contact line: the book's photo and the mug's shadow, not the duvet's linen",
        "hue 55.4": "QA 55.2 (core L* < 20, off the cushion), 55.0 (L* < 14); lit caramel 56.7 (round 5's left patch), 56.2 (the right pillowcase off the shadow)",
        "full_size_p1": "information: full-size p1 is 8.38 (master) and 8.53 (ed9). The gate's p1 is the quarter-size copy (G-ED.11), 8.99 and 9.01; both are >= 8 at either scale"},
    "gate_update": {"file": "docs/ops/quality-gate-g-ed-2026-11-07.md", "version": "1.1 (2026-11-11)",
                    "what": "G-ED.11: the L* 8 floor applies to warm-modern story frames (Bible 1.0.1 'מעקות גריידינג'); Q-ED7 closed: the Bible floor applies to story frames (the tool keeps its own black point, WM-G1). Other styles: information until their Bible is written and approved",
                    "not_updated": "docs/ops/quality-gate-g-ed-2026-11-07.json (the machine counterpart): the brief allowed only the .md version note; it now lags 1.1 on G-ED.11 and Q-ED7"},
    "floor_all_styles": FL,
    "register": R13P,
}

# ---------------------------------------------------------------- register v13
reg = copy.deepcopy(json.load(open(os.path.join(REPO, R12P))))
reg.update(version=13, supersedes=R12P, id="ged-register-2026-11-11-r13", date="2026-11-11", by="qa-agent")
reg.pop("changes_from_v11", None)
# master: fix6
m_rows = copy.deepcopy(reg["master"]["warm-modern-MB-A-fix5"]["rows"])
for r in m_rows:
    if r["card_id"] == "pillowcases-cj-pure-linen-envelope-pair-48x74":
        add = (f" fix6 (code, polish (b) and the Q-ED7 toe): the cushion's cast shadow on the right pillowcase lifted in its core, box median "
               f"{BN['fix5']['designer_box_median']} -> {BN['fix6']['designer_box_median']} (target 14-15), brighter than the slit "
               f"({BN['fix6']['slit_median']}); hue {BN['fix6']['core_L5_lt_20']['h']} against the lit caramel {BN['fix6']['caramel_left_patch_lit']['h']}; "
               f"wedge, contact lines and creases kept; the lit face untouched")
        r["note"] = r["why"] = r["note"] + "." + add
    if r["card_id"] == "sofa-cover-cj-cotton-muslin-fringe":
        add = (f". fix6 (the Q-ED7 toe): the deep folds open (L* < 25: L* {muslin['before']['L']} -> {muslin['after']['L']}, p5 lifted), "
               f"pecan kept (h {muslin['before']['h']} -> {muslin['after']['h']}, C* {muslin['before']['C']} -> {muslin['after']['C']})")
        r["note"] = r["why"] = r["note"] + add
reg["master"]["warm-modern-MB-A-fix6"] = dict(
    file="assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix6.png", state="final_test", rows=m_rows,
    record="qa/reports/2026-11-11-ged-wm-fix6-ed9.json",
    state_source=("QA round 6, box check (qa/reports/2026-11-11-ged-wm-fix6-ed9.md): fix6 = fix5 + polish (b) + the Q-ED7 toe, in code. G-ED.8 pass "
                  "(outside (b)'s mask only L* < 20 moved; 0 on the cushion and the ring band; (b) 0 on the duvet), G-ED.9 pass, G-ED.11 p1 8.99 / p5 +0.59 / "
                  "no split flag (the Bible's L* 8 floor met), box median 14.46, hue within 3 deg; the declared wider region accepted. Eye: G-ED.10 / G-ED.13 "
                  "pass on fix5 (docs/master-bedroom-comparison-2026-11-07.md §6), carried over by the designer's own rule (no eye round if the numbers are inside)"),
    designer_eye={"G-ED.10": "pass", "G-ED.13": "pass", "DL1": "met (QA: darker than the living room ed9)",
                  "source": "docs/master-bedroom-comparison-2026-11-07.md §6, on fix5; carried to fix6 (§6: no further eye round when the box numbers are inside the limits)"},
    note="TEST frame (MB1), not for the site; the site does not read this section")
for k in ("warm-modern-MB-A", "warm-modern-MB-A-fix1", "warm-modern-MB-A-fix3", "warm-modern-MB-A-fix4", "warm-modern-MB-A-fix5"):
    reg["master_superseded_by"][k] = "warm-modern-MB-A-fix6"
# living room: ed9
f8 = reg["frames"]["warm-modern-A-ed8"]
e_rows = copy.deepcopy(f8["rows"])
for r in e_rows:
    if r["card_id"] == "bowl-cj-matte-black-bowl-20":
        add = (f". ed9 (the Q-ED7 toe): still black-espresso - body L* {bowl['before']['L']} -> {bowl['after']['L']} (the Bible's espresso 16.6), "
               f"chromaticity on the white boucle's in the same light (R/G {bowl['chromaticity_after'][0]}, B/G {bowl['chromaticity_after'][2]} against 1.487, 0.695), "
               f"not brown; no fig bleed on its rim")
        r["note"] = r["why"] = r["note"] + add
    if r["card_id"] == "sofa-cover-cj-cotton-muslin-fringe":
        r["note"] = r["why"] = r["note"] + ". ed9: the toe only (L* < 20), its lit side untouched"
reg["frames"]["warm-modern-A-ed9"] = dict(
    file="assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed9.png", state="final_test",
    state_source=("QA round 6, box check (qa/reports/2026-11-11-ged-wm-fix6-ed9.md): ed9 = ed8 + the Q-ED7 toe, in code (codefix-ed9). G-ED.8 pass "
                  "(359,782 px, all L* < 20; 0 at L* >= 20), G-ED.9 pass, G-ED.11 p1 9.01 / p5 +2.55 / no split flag (the Bible's L* 8 floor met; ed8 was 3.65), "
                  "G-ED.3 spot: the black bowl black-espresso, the walnut rich; median and p90 unchanged (DL1). Rows and eye carried over from ed8 "
                  "(qa/reports/ged-register-2026-11-07-r8.md §1; eye from ed5, §6 of the master comparison: no eye round for the toe)"),
    designer_eye={"G-ED.10": "pass", "G-ED.13": "pass"},
    rows=e_rows, fixed_furniture=copy.deepcopy(f8.get("fixed_furniture", [])),
    before_site=["data/story/story.json: the warm-modern living-room frame's src becomes warm-modern-A-ed9.png and its qa_key warm-modern-A-ed9 "
                 "(until then make-story warns that ed8 is superseded and keeps the frame out)",
                 "the camel point becomes cushions-cj-wide-stripe-corduroy-light-green {color: camel} (carried from ed8)",
                 "the triptych's point names the option tl2356-3pcs (the set of three), then QA keys its row (carried from ed8)",
                 "the manager notes the toe when ed9 is shown to the owner (ed8 was shown)"],
    replaces="warm-modern-A-ed8")
for k in ("warm-modern-A-ed4", "warm-modern-A-ed5", "warm-modern-A-ed6", "warm-modern-A-ed7", "warm-modern-A-ed8"):
    reg["superseded_by"][k] = "warm-modern-A-ed9"
reg["changes_from_v12"] = [
    "frames: warm-modern-A-ed9 final_test, replaces ed8 (the Q-ED7 toe only: p1 3.65 -> 9.01, p5 +2.55, nothing at L* >= 20); superseded_by ed4-ed8 -> ed9",
    "master: warm-modern-MB-A-fix6 final_test (polish (b): box median 14.46; the Q-ED7 toe: p1 5.96 -> 8.99, p5 +0.59; the eye's pass on fix5 carried over); master_superseded_by fix5 and older -> fix6",
    "gate 1.1: G-ED.11's L* 8 floor applies to warm-modern story frames; Q-ED7 closed"]
json.dump(reg, open(os.path.join(REPO, R13P), "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- validation (the site's rules, as build.py v12) and the diff to r12
r12 = json.load(open(os.path.join(REPO, R12P)))
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = []
if not isinstance(reg["version"], int):
    bad.append("version")
for p in ("frames", "closeups", "master"):
    for k, f in (reg.get(p) or {}).items():
        if f.get("state") not in S:
            bad.append(f"{p}.{k}.state")
        if not isinstance(f.get("rows"), list) or (f["state"] != "not_yet" and not f["rows"]):
            bad.append(f"{p}.{k}.rows")
        for i, r in enumerate(f.get("rows", [])):
            if not isinstance(r.get("card_id"), str) or not isinstance(r.get("verdict"), str) or r.get("dot") not in Dt or \
                    (r.get("units_in_frame") is not None and not (isinstance(r["units_in_frame"], int) and 1 <= r["units_in_frame"] <= 12)):
                bad.append(f"{p}.{k}.rows[{i}]")
            for c in ("card", "present", "faithful", "why"):
                if c not in r:
                    bad.append(f"{p}.{k}.rows[{i}].{c} (compat)")
top_changed = sorted(k for k in set(r12) | set(reg) if r12.get(k) != reg.get(k))
fr_changed = sorted(k for k in set(r12["frames"]) | set(reg["frames"]) if r12["frames"].get(k) != reg["frames"].get(k))
ms_changed = sorted(k for k in set(r12["master"]) | set(reg["master"]) if r12["master"].get(k) != reg["master"].get(k))
sup_changed = {k: (r12["superseded_by"].get(k), v) for k, v in reg["superseded_by"].items() if r12["superseded_by"].get(k) != v}
msup_changed = {k: (r12["master_superseded_by"].get(k), v) for k, v in reg["master_superseded_by"].items() if r12["master_superseded_by"].get(k) != v}
rows_vs = {"ed9 vs ed8": [(a["card_id"], a["verdict"], a["dot"]) == (b["card_id"], b["verdict"], b["dot"]) for a, b in zip(e_rows, f8["rows"])],
           "fix6 vs fix5": [(a["card_id"], a["verdict"], a["dot"]) == (b["card_id"], b["verdict"], b["dot"]) for a, b in zip(m_rows, r12["master"]["warm-modern-MB-A-fix5"]["rows"])]}
check = dict(bad=bad, top_keys_changed=top_changed, frames_changed=fr_changed, master_changed=ms_changed, superseded_by_changed=sup_changed,
             master_superseded_by_changed=msup_changed, rows_same_card_verdict_dot={k: all(v) and len(v) > 0 for k, v in rows_vs.items()},
             counts={"ed9": [len(e_rows), sum(r["verdict"] == "yes" for r in e_rows)], "fix6": [len(m_rows), sum(r["verdict"] == "yes" for r in m_rows)]})
rep["register_check_py"] = check
sr = os.path.join(OUT, "data", "register-check-site-reader.json")
if os.path.exists(sr):
    rep["register_check_site_reader"] = dict(tool="tools/check_register.ts (site/tools/lib/qa-frames.ts registerReader and rowOf, unchanged)",
                                             result=json.load(open(sr)))
json.dump(rep, open(os.path.join(REPO, "qa/reports/2026-11-11-ged-wm-fix6-ed9.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(check, indent=1, ensure_ascii=False))
