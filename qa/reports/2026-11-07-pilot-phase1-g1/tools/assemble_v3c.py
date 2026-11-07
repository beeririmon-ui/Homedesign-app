"""
qa-agent 2026-11-07: assembles qa/reports/2026-11-07-pilot-phase1-v3c-verify.json (QA's check of render-agent's F1-F3 on grade v3c, set C's
black point, the sheet, and the final approval-3 verdict) from data/verify-v3c*.json, graded-split-v3-graded-v3c.json,
swapdiff-v3-graded-v3c.json, lock-v3c.json, dark-c.json, sku-colour-v3-graded-v3c.json. Usage: python3 -I assemble_v3c.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/data")
J = lambda n: json.load(open(os.path.join(D, n)))  # noqa: E731
slab, ver, gs = J("verify-v3c-slab.json"), J("verify-v3c.json"), J("graded-split-v3-graded-v3c.json")
sd, lk, dk, sku = J("swapdiff-v3-graded-v3c.json"), J("lock-v3c.json"), J("dark-c.json"), J("sku-colour-v3-graded-v3c.json")
c = "composite-set-C-v3-graded-v3c.png"
out = {
    "id": "2026-11-07-pilot-phase1-v3c-verify", "date": "2026-11-07", "by": "qa-agent",
    "follows": "qa/reports/2026-11-07-pilot-phase1-g1.json (F1-F3, D1)",
    "checked": "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/*-v3-graded-v3c.png, masks/stone-wide.png, shell-fix-v3.json (grade_v3c, lock_F3), pilot-phase1-sheet.jpg",
    "F1_bench": {"verdict": "pass", "visible_slab": slab[c]["visible_slab"], "armchair_edge_over_slab": slab[c]["armchair_edge_over_slab"],
                 "front_face_lab": ver[c]["front_lab"], "front_face_hsv_h": ver[c]["front_hsv_h"], "top_lab": ver[c]["top_lab"],
                 "note": "on the visible slab no pixel under H 25 and b* max 12.55; the b* > 15 / H < 25 pixels in the wide mask are the armchair's walnut and its antialiased edge (alpha > 0), not stone; no ochre line along the armchair at x4; the left end's strip is in the mask now (overlays/bench-v3c-100.jpg, bench-v3c-x4.jpg)"},
    "F2_one_grade": {"verdict": "pass", "graded_split": {k: [v["outside_px_gt0"], v["outside_px_gt2_levels"], v["dE76_max"]] for k, v in gs.items()},
                     "swap_diff_display": {k: v.get("outside_gt0") for k, v in sd.items() if "outside_gt0" in v}},
    "F3_lock": {"verdict": "pass", "qa_worst_p90_px_1920": lk["qa_worst_p90"], "qa_min_paired": lk["qa_min_paired"], "render_agent_lock_F3_matches": True},
    "black_point_set_C": {"verdict": "acceptable", "values": dk,
                          "why": "one grade for every file (F2) fixes the toe on the base (p0.5 12.4, WM-G1 11-14); the deep crevice is the same pixels and level in every set; set C's p0.5 10.0 comes from its own products (12.7 % of the layer under L* 11: the Dark Coffee corduroy and the Clay throw's folds), which keep their texture (9 px sd median 2.1, 1.7 % flat, min L* 6.3, nothing crushed); lifting set C alone would split the grade again (F2). Their colour against the SKU photos holds on v3c: Dark Coffee dE00 2.4 / +6.3 deg, Clay dE00 1.4",
                          "dark_coffee_v3c": sku["C"]["items"]["45 corduroy patchwork Dark Coffee (left)"], "clay_v3c": sku["C"]["items"]["throw Clay (seat, front and arm top)"]},
    "D1": {"verdict": "closed by master-designer (proposals §13.4: v3b accepted for the approval-3 sheet); v3c keeps the v3b gain (1.0008)"},
    "sheet": {"verdict": "fix before sending (0 tokens, minutes)",
              "finding": "pilot-phase1-sheet.jpg: the step 2 'shell v3' and step 3 'shell v3 + furniture' tiles are the ungraded files: the bench's front face reads ochre there (sampled on the sheet: Lab 60.8 / 6.7 / 27.0; shell-v3.png 55.2 / 7.2 / 27.3; v3c display 55.1 / 0.5 / 12.0), the yellow the designer rejected (§13.1 (3)), while the step 4 tiles are v3c",
              "fix": "the step 2 and 3 tiles from shell-v3-graded-v3c.png and shell-furniture-v3-graded-v3c.png (or labelled 'before the display grade')", "owner": "render-agent"},
    "approval_3": {"verdict": "yes", "condition": "after the sheet's step 2-3 tiles are swapped to the v3c display files", "before_site": "6K masters and the remaining G1/G2 on them (G1.17), not part of phase 1"},
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-v3c-verify.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
