"""qa-agent 2026-11-10: G-ED round 4 on MB1: render-agent's 0-token fixes (mb1-fix5.json: nordic fix5, warm-modern fix4) and the designer's
two conditions (mb1-fix6.json: nordic fix6, the candles out and DL1's exposure). From data/check.json, data/fix6.json, data/tone-check.json,
data/dl1.json, data/guardrails-fix6.json and the x3-x4 sheets. Writes qa/reports/2026-11-10-ged-master-fix6.json and register v11
(qa/reports/ged-register-2026-11-10-r11.json). Usage: python3 -I build.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix5/data")
CK, F6, TC, DL = (json.load(open(os.path.join(D, n))) for n in ("check.json", "fix6.json", "tone-check.json", "dl1.json"))
GR = json.load(open(os.path.join(D, "guardrails-fix6.json")))[0]
F4 = json.load(open(os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix4.json")))
nw, wg = CK["nordic-wedge"], CK["wm-gap"]
lr, m6 = DL["living-room nordic-A-fin2"], DL["nordic-MB-A-fix6.png"]
out = {
    "id": "2026-11-10-ged-master-fix6", "date": "2026-11-10", "by": "qa-agent", "follows": "qa/reports/2026-11-10-ged-master-fix4.json",
    "fix5": {
        "nordic-MB-A-fix5": {"G-ED.8": f"pass: {nw['changed_px']} px, all in the declared wedge (x {nw['bbox'][0]}-{nw['bbox'][1]}, y {nw['bbox'][2]}-{nw['bbox'][3]})",
                             "G-ED.9": f"pass: the pillowcase's linen runs down to a soft contact line; L* {nw['L_patch']} against {nw['L_ring']} around, grain {nw['grain_patch']} against {nw['grain_ring']} (present, a little smoother); no apex, no straight sides; natural at 100 % (overlays/nordic-wedge-x4.jpg, nordic-wedge-context-100.jpg)"},
        "warm-modern-MB-A-fix4": {"G-ED.8": f"pass: {wg['changed_px']} px, all in the declared box (x {wg['bbox'][0]}-{wg['bbox'][1]}, y {wg['bbox'][2]}-{wg['bbox'][3]})",
                                  "G-ED.9": f"pass: the blob is gone; the cream back pillow's edge and the gap continue down to the cushion; grain {wg['grain_patch']} (the clean gap rows above: 1.46) (overlays/wm-gap-x4.jpg)"}},
    "fix6": {
        "candles": f"pass: both flames and their glow gone, dark wicks kept, the wax's warm half toned down; the content change only inside the candle boxes ({TC['residual_gt3_inside_boxes']} px > 3 levels inside, 0 outside) (overlays/fix6-candles-x3.jpg)",
        "exposure": (f"pass: outside the candle boxes fix6 is fix5 through one tone curve of L* alone: residual after the curve 0 px > 3 levels (p99.9 {TC['residual_p999_outside']}), "
                     f"the same gain on R, G and B (spread p99 {TC['channel_gain_spread_p99']}); midtones x{F6['gain_median']} ({F6['gain_stops']} stop), easing to 1.0 in the sun stripes (their 2 % brightest x{F6['sun_2pct_ratio_median']}) and to about 0.88 in the deep shadow"),
        "DL1": (f"met: the wall above the panelling, lit side, L* {m6['wall_lit']['median']} against the living room's back wall {lr['wall_lit']['median']} (fix5: {DL['nordic-MB-A-fix5.png']['wall_lit']['median']}); "
                f"frame median {m6['frame_median']} against {lr['frame_median']}; render-agent's wider measure 60.5 against 60.5; the designer's cap (1/3 stop) used"),
        "guardrails": f"G-ED.11 pass (no split; shadow p1 {GR['shadow_floor_L_p1']} on QA's quarter-size copy, render-agent 8.2: both >= 8); G-ED.12 pass ({GR['clipped_254_pct']} % clipped, the window and the glazing behind the sill vase)",
    },
    "designer_eye": "docs/master-bedroom-comparison-2026-11-07.md §5: G-ED.10 pass; G-ED.13 pass after the candles; DL1 measured by QA; the frame a final test after the two code fixes",
    "states": {"nordic-MB-A-fix6": "final_test", "warm-modern-MB-A-fix4": "not_yet (the caramel pillowcases' flanges: P6b in SPEND1 week 3, prepared in mb1-fix5.json)"},
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix6.json"), "w"), ensure_ascii=False, indent=1)
V10P = "qa/reports/ged-register-2026-11-10-r10.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V10P))))
reg.update(version=11, supersedes=V10P, id="ged-register-2026-11-10-r11", date="2026-11-10", by="qa-agent")
reg.pop("changes_from_v9", None)
n_rows = copy.deepcopy(F4["frames"]["nordic-MB-A-fix4"]["rows"])
for r in n_rows:
    if r["card_id"] == "candle-holders-cj-travertine-pedestal":
        r["note"] = r["why"] = r["note"] + "; fix6: the pillar candles (generic fill) put out, the holders unchanged"
    if r["card_id"] == "cushions-cj-boucle-teddy":
        r["note"] = r["why"] = r["note"].replace("The fill left of it is a G-ED.9 item of the frame, not of the cushion", "fix5: the fill left of it is now the pillowcase's linen with its contact line (G-ED.9 pass)")
reg["master"]["nordic-MB-A-fix6"] = dict(file="assets/renders/master/editorial-2026-11-07/nordic/nordic-MB-A-fix6.png", state="final_test", rows=n_rows,
                                         record="qa/reports/2026-11-10-ged-master-fix6.json",
                                         state_source="QA: rounds 3-4 (qa/reports/2026-11-10-ged-master-fix4.md, -fix6.json): 11 of 11 yes, G-ED.8/9/11/12 pass, DL1 met. Eye: master-designer §5 (G-ED.10 pass, G-ED.13 pass after the candles)",
                                         designer_eye={"G-ED.10": "pass", "G-ED.13": "pass (candles out in fix6)", "DL1": "met (QA)"},
                                         note="TEST frame (MB1), not for the site; the site does not read this section")
w_rows = copy.deepcopy(F4["frames"]["warm-modern-MB-A-fix3"]["rows"])
reg["master"]["warm-modern-MB-A-fix4"] = dict(file="assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix4.png", state="not_yet", rows=w_rows,
                                              record="qa/reports/2026-11-10-ged-master-fix6.json",
                                              state_source="QA: the gap fixed (fix4, G-ED.8/9 pass); the caramel pillowcases still 'partly' (flanges): pass P6b in SPEND1 week 3 (from Sun 2026-11-15), prepared",
                                              note="TEST frame (MB1), not for the site; the site does not read this section")
reg["master_superseded_by"] = {"nordic-MB-A": "nordic-MB-A-fix6", "nordic-MB-A-fix1": "nordic-MB-A-fix6", "nordic-MB-A-fix4": "nordic-MB-A-fix6",
                               "warm-modern-MB-A": "warm-modern-MB-A-fix4", "warm-modern-MB-A-fix1": "warm-modern-MB-A-fix4", "warm-modern-MB-A-fix3": "warm-modern-MB-A-fix4"}
reg["changes_from_v10"] = ["master: nordic-MB-A-fix6 final_test (the wedge fixed in fix5; the candles out and DL1's -1/3 stop in fix6; the designer's eye §5)",
                           "master: warm-modern-MB-A-fix4 not_yet (the gap fixed; P6b for the caramel pillowcases in week 3)"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-10-r11.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = [f"{p}.{k}" for p in ("frames", "closeups", "master") for k, f in (reg.get(p) or {}).items()
       if f.get("state") not in S or any(not isinstance(r.get("card_id"), str) or r.get("dot") not in Dt or (r.get("units_in_frame") is not None and not 1 <= r["units_in_frame"] <= 12) for r in f.get("rows", []))]
print("v11 bad", bad, {k: (v["state"], sum(r["verdict"] == "yes" for r in v["rows"])) for k, v in reg["master"].items() if "fix6" in k or "fix4" in k})
