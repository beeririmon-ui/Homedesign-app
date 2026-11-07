"""qa-agent 2026-11-07: register v2 (qa/reports/ged-register-2026-11-07-r2.json), superseding v1 (qa/reports/ged-register-2026-11-07.json).
Changes: modern-country-A-fix4 -> final_test (QA's fix4 check + master-designer's eye, proposals §9); mediterranean-A-ed7 replaces ed6
(QA's G-ED.8-G-ED.12 on the regional shade grade, data/ed7.json and data/guardrails-med.json; the designer's G-ED.13 on ed7 has not
landed, so 'almost' at most); a closeups section (empty). Everything else carried over from v1. Usage: python3.12 -I build_register_v2.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
V1P = "qa/reports/ged-register-2026-11-07.json"
V1 = json.load(open(os.path.join(REPO, V1P)))
ED7 = json.load(open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r2/data/ed7.json")))
GM = {r["file"].split("/")[-1]: r for r in json.load(open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r2/data/guardrails-med.json")))}
R = "assets/renders/editorial-phase-b-2026-11-06/"

reg = copy.deepcopy(V1)
reg["version"] = 2
reg["supersedes"] = V1P
reg["schema"]["closeups"] = ("closeups.<qa_key>: layer 2's close-ups, keyed by their qa_key, in the same shape as frames.<key> (file, state of the four, "
                             "rows with card_id, option, verdict, note, dot); site/tools/lib/qa-frames.ts reads frames.<key> ?? closeups.<key>")
reg["changes_from_v1"] = [
    "modern-country-A-fix4: almost -> final_test (QA: the sofa spot gone, the mullion has grain, the line left of the vase stays a note; eye: proposals §9, G-ED.10 and G-ED.13 pass)",
    "mediterranean-A-ed7 replaces mediterranean-A-ed6: not_yet -> almost (QA: G-ED.8-G-ED.12 pass on the regional shade grade; the designer's G-ED.13 on ed7 is pending)",
    "closeups: added, empty",
]

f = reg["frames"]["modern-country-A-fix4"]
f["state"] = "final_test"
f["state_source"] = "QA: qa/reports/ged-register-2026-11-07-r2.md (fix3 -> fix4, codefix6); eye: docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md §9 (G-ED.10, G-ED.13 pass)"
f["designer_eye"] = {"G-ED.10": "pass", "G-ED.13": "pass", "note": "optional: a cooler window (b* -4 to -6 inside the glass box), a note for the owner, not a condition"}
f["fix4_check"]["g_ed_8"] = "three components only, at the sofa spot, the strip left of the vase (rows 585-700) and the mullion (840 px); 0 px elsewhere (render-agent's 0 outside the masks confirmed)"
f.pop("open", None)

med = copy.deepcopy(reg["frames"].pop("mediterranean-A-ed6"))
med["file"] = R + "mediterranean-A-ed7.png"
med["state"] = "almost"
med["state_source"] = ("QA: qa/reports/ged-register-2026-11-07-r2.md (ed6 -> ed7, grade-med.json): G-ED.8-G-ED.12 pass, every product row yes; "
                       "eye: G-ED.13 failed on ed6 (proposals §6), the verdict on ed7 has not landed: 'almost' until it does")
med["designer_eye"] = {"G-ED.10": "pass (ed6)", "G-ED.13": "pending on ed7 (failed on ed6)", "G-ED.16": "pass"}
med["ed7_check"] = dict(
    sun_patches=f"untouched: QA's own sun mask from ed6 (L* > 78, b* > 18, window out) {ED7['sun_px']} px; its core (eroded 2 px) changed in 1 px; the changes sit on the threshold edge, inside the grade's soft edge. The floor blade's core: 0 px changed",
    shade=f"{ED7['changed_pct']} % of the frame changed (the grade); far shade L* {ED7['delta_L_far_shade']}, the ring 4-24 px round the sun {ED7['delta_L_ring_4_24px']}: no bright halo",
    products="every product keeps its colour family under the cooler shade (b* -5 to -7, L* -2 to -4): our White cushion (53.1, 4.0, 9.9), terracotta (31.9, 14.6, 19.6), moss (35.1, 2.4, 14.0); data/ed7.json",
    g_ed_9="pass: no halo at the sun mask's edge; at the floor blade's fringe the terracotta reads a little mottled where warm flecks meet the cooler shade, but its fine chroma variation fell (hf sd b* 3.93 -> 3.05): the tile's own texture. The window box changed only along its edges (max 14 levels)",
    g_ed_11=f"pass: no split (darkest 10 % b* {GM['mediterranean-A-ed7.png']['shadows_10pct_Lab'][2]}, rule >= -4, target >= +3); deepest shadow L* p1 {GM['mediterranean-A-ed7.png']['shadow_floor_L_p1']}",
    g_ed_12=f"pass: raw {GM['mediterranean-A-gpt-image-2-5.png']['clipped_254_pct']} % clipped outside the window box; ed7 {GM['mediterranean-A-ed7.png']['clipped_254_pct']} %",
    data=["qa/reports/ged-register-2026-11-07-r2/data/ed7.json", "qa/reports/ged-register-2026-11-07-r2/data/guardrails-med.json"])
med["open"] = ["master-designer's G-ED.13 on ed7 (proposals file); if it fails, the frame returns to not_yet and the next step is the owner's (a paid local pass ~600, or the story line's hour)"]
for r_ in med["rows"]:
    if r_["card_id"] == "cushions-cj-washed-cotton-frayed" and r_.get("option") == {"other": "white"}:
        r_["note"] = r_["why"] = "ed6: the three bench back cushions are this card's White 50 x 50 (x3); ed7: still white under the cooler shade"
reg["frames"]["mediterranean-A-ed7"] = med
reg["superseded_by"]["mediterranean-A-ed6"] = "mediterranean-A-ed7"
reg["superseded_by"]["mediterranean-A-ed5"] = "mediterranean-A-ed7"
reg["pending_qa"] = []
reg["closeups"] = {}
out = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r2.json")
json.dump(reg, open(out, "w"), ensure_ascii=False, indent=1)
for k, v in reg["frames"].items():
    print(k, v["state"], len(v["rows"]))
