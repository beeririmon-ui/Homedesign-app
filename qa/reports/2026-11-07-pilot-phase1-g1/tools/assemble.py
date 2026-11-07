"""
qa-agent 2026-11-07: assembles qa/reports/2026-11-07-pilot-phase1-g1.json from the measurements in data/ (each tool's file named in it).
Usage: python3 -I assemble.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/data")
PIL = "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07"


def J(n):
    return json.load(open(os.path.join(D, n)))


lock2, lock3 = J("shell-lock.json"), J("shell-lock-v3.json")
wedge, furn = J("wedge-area.json"), J("furniture.json")
sf2, sf3, sf3b = J("shellfix-v2.json"), J("shellfix-v3.json"), J("shellfix-v3-graded-v3b.json")
bench, sd2, sd3 = J("bench-cap.json"), J("swapdiff.json"), J("swapdiff-v3.json")
gs3, gs3b = J("graded-split-v3.json"), J("graded-split-v3-graded-v3b.json")
sku3b, v3v2 = J("sku-colour-v3-graded-v3b.json"), J("v3-vs-v2.json")
worst = lambda d: max(v["p90_abs_px"] for v in d.values())  # noqa: E731
out = {
    "id": "2026-11-07-pilot-phase1-g1", "date": "2026-11-07", "by": "qa-agent",
    "scope": "warm-modern living-room tool pilot, phase 1 (shell, fixed furniture and shadow, the cushions slot A/B/C), before owner approval 3",
    "gate": "G1 + G2 (tool assets; G-ED does not apply), docs/ops/quality-gates-2026-11-02.md; brief briefs/render-warm-modern-pilot-phase1-2026-11-07.md; designer docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md §11, §13.1, §13.3",
    "versions": {
        "v2": "shell-v2.png, shell-furniture-v2.png, composite-set-*-v2.png; display grade 1 (corner to L* 90, gain 1.2295), files *-v2-graded.png re-written 18:12 with the same numbers",
        "v3": "shell-v3.png (back wall only; the bench from v2), shell-furniture-v3.png, composite-set-*-v3.png; display grade 2 (gain 1.2295 + the slab's b* cap 12) in *-v3-graded.png",
        "v3b": "grade v3b (designer §13.3: the centre to L* 89.5 on display, gain 1.0008): *-v3-graded-v3b.png. The approval-3 verdict is on v3 + v3b",
    },
    "approval_3": {
        "verdict": "conditional_yes",
        "summary": "v3 with grade v3b may go to the owner after one 0-token fix to the bench's front edge (the b*-only cap turned it mauve). The one-grade fix (the toe computed per file) is required before anything goes to the site; it does not change what the owner sees. The darker v3b (corner 82.6 against the ~86 the designer expected) goes to the designer's eye.",
        "conditions_before_owner": ["F1 bench front edge (render-agent)"],
        "conditions_before_site": ["F2 one display grade for every file (render-agent)", "F3 render-agent's lock record corrected (render-agent)"],
        "for_the_designer": ["D1 v3b reads 0.3 stop darker than v3: corner 82.6 (expected ~86), window wall flat 75-76"],
    },
    "lock_flag": {
        "verdict": "measurement artefact, not a lock failure",
        "qa_measure": {"v2": {k: v["p90_abs_px"] for k, v in lock2["shell-v2.png"].items()}, "v3": {k: v["p90_abs_px"] for k, v in lock3["shell-v3.png"].items()},
                       "v3_graded": {k: v["p90_abs_px"] for k, v in lock3["shell-v3-graded.png"].items()},
                       "worst_p90_px_1920": {"v2": worst(lock2["shell-v2.png"]), "v3": worst(lock3["shell-v3.png"])}, "limit_px_1920": 9.6,
                       "method": "render vs clay r4 shell layer (all named lines, the back-wall floor line WMC10 included), QA's projection (house plan 1.3.5), nearest-peak pairing, raw, no affine; 21-48 samples per line"},
        "render_agent_flag": {"mullion Y 1.45": "raw p90 11 with IQR [0, 11]: bimodal, pairs the profile's other face; after its affine 0. QA: p90 1 px, 48/48 paired",
                              "bench back-end top edge": "raw p90 0 (5 samples); after its affine 14.2 from one sample at 23 px. QA: p90 1 px raw on 48 samples",
                              "why_false": "its verdict needs every line to pass in one mode (all raw or all after the affine); each of the two lines fails in the other mode"},
        "v3_changes_only_the_back_wall": v3v2,
    },
    "checks": {
        "G1.4_lock": {"verdict": "pass", "v2_worst_p90": worst(lock2["shell-v2.png"]), "v3_worst_p90": worst(lock3["shell-v3.png"]), "file": "data/shell-lock.json, data/shell-lock-v3.json"},
        "furniture_on_clay": {"verdict": "pass", "iou": {k: v["iou"] for k, v in furn["objects"].items()},
                              "outline_p90_px_1920": {k: v["p90_px_1920"] for k, v in furn["objects"].items()}, "shadow_layer": furn["shadow_layer"], "file": "data/furniture.json"},
        "wedge_designer_13_1_1": {"verdict": "pass on v3 / v3b (fail on v2 ungraded)", "rule": "art and sconce area (frame u 0.45-0.85, v 0.15-0.45), max dL* over 120 px <= 2.5, both ends in the area",
                                  "values": {k: v["both_ends_in_area"]["max_dL_120"] for k, v in wedge.items()},
                                  "corner_falloff_note": "a 120 px span centred at the area's left edge reaches the corner's falloff (x 1090-1290 at 2720: the wall darkens toward the inside corner, architecture): " + json.dumps({k: v["centred_span_any_wall_max_dL_120"] for k, v in wedge.items()}),
                                  "file": "data/wedge-area.json"},
        "grading_points_qa_projection": {"v2_graded": {k: v["graded"] for k, v in sf2["grading_points"].items()}, "v3_ungraded": {k: v["ungraded"] for k, v in sf3["grading_points"].items()},
                                         "v3_graded": {k: v["graded"] for k, v in sf3["grading_points"].items()}, "v3b_display": {k: v["graded"] for k, v in sf3b["grading_points"].items()},
                                         "verdict": "v3b: the back-wall display targets met (centre 89.8, right 85.1); the corner 82.6 against the designer's expected ~86 (D1); the window wall Y 0.30 accepted by the designer (§13.1 (5), §13.3); the whole flat Y 0.30-0.65 now 72-76 (G1.8's 80-88 is a proposal): D1",
                                         "file": "data/shellfix-*.json"},
        "bench_slab": {"verdict": "fail (F1)", "lit_top_b": {k: bench[k]["lit_half_b"] for k in bench if k.endswith(".png")},
                       "front_face": {k: {"lab": bench[k]["front_face_lab"], "hsv_h": bench[k]["front_face_hsv_h"]} for k in bench if k.endswith(".png")},
                       "b_p95": {k: bench[k]["b_p95"] for k in bench if k.endswith(".png")},
                       "finding": "the lit top is no longer yellow (b* ~8); the cap clamps b* only and keeps a*, so the 8 cm front face went from ochre (h_ab 75) to mauve-taupe (Lab ~62.8/5.7/12.1, h_ab 65, HSV H 23.4 on the shell and 27.0 in the composites against G1.9's 'never H < 25 in white or beige'); at 100 % it reads lilac-grey next to the cream top. The mask also misses the front face's last ~40 px at the left end (303 px with b* > 20 in the 4 px ring)",
                       "fix": "0 tokens: cap the chroma along the slab's own hue (scale a* with b*, the face's a*:b* to the top's), and grow the mask to the left end; QA re-measures (no H < 25, b* <= 12, no yellow sliver)", "owner": "render-agent",
                       "file": "data/bench-cap.json, overlays/bench-v2-v3-v3b-100.jpg"},
        "swap_diff_ungraded": {"verdict": "pass", "v2": {k: v["outside_gt0"] for k, v in sd2.items() if "outside_gt0" in v}, "v3": {k: v["outside_gt0"] for k, v in sd3.items() if "outside_gt0" in v},
                               "file": "data/swapdiff.json, data/swapdiff-v3.json"},
        "swap_diff_display_graded": {"verdict": "fail (F2)", "v3": {k: [v["outside_px_gt2_levels"], v["dE76_max"]] for k, v in gs3.items()},
                                     "v3b": {k: [v["outside_px_gt2_levels"], v["dE76_max"]] for k, v in gs3b.items()},
                                     "finding": "outside the products and shadows the display files differ per set: up to 14,726 px over 2 levels (base->C, v3b), dE76 up to 2.7, all in the deep darks (L* 7-14). Cause: the black-point toe is computed per file (p0.5 after exposure: base 6.14, A 5.77, B 5.02, C 3.69 in v3b)",
                                     "fix": "0 tokens: one grade, its toe computed once (on the base) and applied unchanged to every file", "owner": "render-agent", "file": "data/graded-split-*.json"},
        "halo_G2.3": {"verdict": "pass", "finding": "the ring statistic flags lit fabric ribs, fringes and cushion edges; each hotspot at x4 (and x8 on B) is the product's own texture, no light or dark band", "file": "data/halo-hotspots-*.json, overlays/halo-hotspots-*-x4.jpg"},
        "cushions_G1.1": {"verdict": "pass", "finding": "all 12 items: the right silhouette, count, pattern and material against their SKU photos (overlays/cushions-set-*.jpg)"},
        "cushions_colour_G1.2": {"verdict": "pass with notes", "set_C_dark_coffee": {k: sku3b["C"]["items"]["45 corduroy patchwork Dark Coffee (left)"][k] for k in ("frame_norm_lab", "photo_norm_lab", "d_hue_deg", "dE2000")},
                                 "set_C_rule": "designer §13.1 (4): rotate only if dE > 5 or > 8 deg off the SKU photo; inside both, and yellower (+2.8 deg), not redder: left as it is (#603326 on the card is a label hex)",
                                 "light_items_note": "white-normalised medians run warmer than the SKU photos (b* +7 to +15 on White, Milk Tea, Oatmeal, the linen lumbars, Light Brown); on the lit faces the gap is b* +2 to +4: the shaded half carries the room's warm bounce (bone sofa, oak, walnut). Not a failure; the Milk Tea lumbar is the closest to the line (lit face 5 L* darker and +3.9 b*)",
                                 "file": "data/sku-colour-*.json, data/cushions.json"},
        "black_point_clipping": {"verdict": "pass", "black_point_final": 12.4, "clipped_254_pct": 0.0},
        "format": {"verdict": "pass for phase 1", "note": "2720 x 1530 test (G1.17: test 2K; the 6K masters come after approval 3)"},
        "combinations": {"verdict": "pass (ungraded)", "note": "one slot with three variants: the 6 pairs base/A/B/C are every combination there is"},
    },
    "fixes": [
        {"id": "F1", "what": "bench front edge: chroma cap along the slab's hue, and the mask's left end", "owner": "render-agent", "tokens": 0, "before": "owner approval 3"},
        {"id": "F2", "what": "one display grade: the toe computed once, applied to every file; then swap-diff on the display files", "owner": "render-agent", "tokens": 0, "before": "site"},
        {"id": "F3", "what": "the lock record in shell-fix-v3.json: nearest-peak pairing, >= 20 samples a line, one mode for the set; or carry QA's verdict", "owner": "render-agent", "tokens": 0, "before": "site"},
        {"id": "D1", "what": "v3b's darker room: corner 82.6, window wall 72-76: accept, or a gain between 1.0 and 1.23", "owner": "master-designer", "tokens": 0, "before": "owner approval 3 (eye)"},
    ],
    "tools": sorted(os.listdir(os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/tools"))),
    "overlays": sorted(os.listdir(os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/overlays"))),
    "pilot_folder": PIL,
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1.json"), "w"), ensure_ascii=False, indent=1)
print("ok", len(json.dumps(out)))
