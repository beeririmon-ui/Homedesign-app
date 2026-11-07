"""qa-agent 2026-11-07: register v5 (qa/reports/ged-register-2026-11-07-r5.json), superseding v4. Changes:
- warm-modern-A-ed7 (new; supersedes ed4-ed6): the milk-tea boucle's two-tone flattened (render-agent, ed7-milktea.json; QA data/ed7*.json)
  -> yes, dot on. The 21 Camel untouched, 'no', dot off until CAM1 -> not_yet.
- tool: the warm-modern pilot's F1-F3 verified on grade v3c (qa/reports/2026-11-07-pilot-phase1-v3c-verify.json): approval 3 yes after the
  sheet's step 2-3 tiles are the display files.
Usage: python3 -I build_register_v5.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
V4P = "qa/reports/ged-register-2026-11-07-r4.json"
R5 = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r5")
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V4P))))
E7, EE, EG = (json.load(open(os.path.join(R5, "data", n))) for n in ("ed7.json", "ed7-edge.json", "ed7-grey.json"))
VC = json.load(open(os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-v3c-verify.json")))
reg.update(version=5, supersedes=V4P, id="ged-register-2026-11-07-r5", date="2026-11-07", by="qa-agent")
reg.pop("changes_from_v3", None)
wm = copy.deepcopy(reg["frames"]["warm-modern-A-ed6"])
wm["file"] = "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed7.png"
reg["frames"]["warm-modern-A-ed7"] = wm
for r in wm["rows"]:
    if r["card_id"] == "cushions-cj-boucle-teddy" and r.get("option") == {"color": "milk-tea-color", "size": "50x50"}:
        r.update(verdict="yes", faithful="yes", dot="yes")
        r["note"] = r["why"] = (
            f"ed7 (render-agent's 0-token chroma flattening, {E7['changed_vs_ed6']} px, inside the cushion; 5 more at its 1 px edge): the two-tone is gone, "
            f"C* of the darkest fifth over the lightest {E7['ed7']['C_dark_minus_C_light']:+} (ed6 {E7['ed6']['C_dark_minus_C_light']:+}; the SKU photo "
            f"{E7['sku_photo']['C_dark_minus_C_light']:+}); against the White boucle of the same SKU here a* {E7['ed7_minus_white_ab'][0]:+}, b* {E7['ed7_minus_white_ab'][1]:+} "
            "(the photos +0.9, +1.6); L* and the loops kept. The greyish specks at x4: "
            f"{EG['ed7']['share_pct']} % of the cushion, scattered (largest group {EG['ed7']['largest_group_px']} px), fewer than ed5 ({EG['ed5']['share_pct']} %) and ed6 "
            f"({EG['ed6']['share_pct']} %), and the photo's own loops are grey-cream: accepted. Edge: no chroma ring (C* {EE['ed7']['ring_C']} at the edge vs {EE['ed7']['band_C']} inside, the same hue)")
    if r["card_id"] == "cushions-cj-knitted-chenille-bean-green":
        r["note"] = r["why"] = r["note"].replace(" ed6: untouched;", " ed6, ed7: untouched (0 px changed outside the milk-tea cushion since ed5);")
wm["state"] = "not_yet"
wm["state_source"] = ("QA: qa/reports/ged-register-2026-11-07-r5.md §1 (ed7 against ed6 and the SKU photo); G-ED.5: the 21 Camel (a product with a dot) is 'no' until the owner's "
                      "CAM1, so final_test is out. Eye: G-ED.10 / G-ED.13 pass (unchanged)")
wm["open"] = ["the 21 Camel chenille: the owner's CAM1 (proposals §13.2), then a verified caramel or the documented exception"]
sb = reg["superseded_by"]
for k, v in list(sb.items()):
    if v == "warm-modern-A-ed6":
        sb[k] = "warm-modern-A-ed7"
sb["warm-modern-A-ed6"] = "warm-modern-A-ed7"
t = reg["tool"]["living-room/warm-modern/pilot-phase1"]
t["record"] = ["qa/reports/2026-11-07-pilot-phase1-g1.json", "qa/reports/2026-11-07-pilot-phase1-v3c-verify.json"]
t["version_checked"] = "v3 with display grade v3c (one grade for every file)"
t["approval_3"] = {"verdict": "yes", "condition": VC["approval_3"]["condition"], "summary": "F1, F2, F3 verified on v3c; set C's black point 10.0 accepted (its own dark products, one grade); D1 closed by the designer (§13.4). The sheet's step 2-3 tiles are still the ungraded files (the bench's ochre edge): swap them to the v3c display files before it goes to the owner."}
for a in t["assets"]:
    if a["asset"].startswith("shell-v3-graded-v3b.png"):
        a.update(asset="shell-v3-graded-v3c.png (the bench slab)", checks="visible slab: 0 px under H 25, b* max 12.55; front face 59.8 / 2.0 / 12.0, HSV H 36.6; the left end in the mask", verdict="pass", fix="F1 done")
    elif "graded-v3b.png + shell-furniture" in a["asset"]:
        a.update(asset="composite-set-A/B/C-v3-graded-v3c.png + shell-furniture-v3-graded-v3c.png", checks="swap-diff on display: 0 px outside in all 6 pairs; set C p0.5 10.0 from its own products (accepted)", verdict="pass", fix="F2 done")
    elif a["asset"].startswith("shell-fix-v3.json"):
        a.update(checks="lock_F3: QA's method, worst p90 2 px, >= 21 samples a line; QA's re-run on v3c the same", verdict="pass", fix="F3 done")
    elif a["asset"].startswith("the back wall"):
        a.update(asset="the back wall on display (v3c = v3b gain)", verdict="pass; D1 closed (designer §13.4)")
t["assets"].append({"asset": "pilot-phase1-sheet.jpg", "checks": "step 2-3 tiles are the ungraded files (the bench's ochre edge, b* 27)", "verdict": "fix before sending", "owner": "render-agent"})
t["fixes"] = [{"id": "F1", "status": "done, verified"}, {"id": "F2", "status": "done, verified"}, {"id": "F3", "status": "done, verified"}, {"id": "D1", "status": "closed (designer §13.4)"},
              {"id": "S1", "what": "the sheet's step 2-3 tiles from the v3c display files", "owner": "render-agent", "tokens": 0, "before": "owner approval 3"}]
reg["changes_from_v4"] = [
    "warm-modern-A-ed7 added (supersedes ed4-ed6): the milk-tea boucle yes, dot on (the two-tone flattened); the 21 Camel no, dot off until CAM1; not_yet",
    "tool: the warm-modern pilot on grade v3c, F1-F3 verified; approval 3 yes once the sheet's step 2-3 tiles are the display files",
]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r5.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = []
if not isinstance(reg["version"], int):
    bad.append("version")
for part in ("frames", "closeups"):
    for k, f in (reg.get(part) or {}).items():
        if f.get("state") not in S:
            bad.append(f"{part}.{k}.state")
        if not isinstance(f.get("rows"), list) or (f["state"] != "not_yet" and not f["rows"]):
            bad.append(f"{part}.{k}.rows")
        for i, r in enumerate(f.get("rows") or []):
            if not isinstance(r.get("card_id"), str) or not isinstance(r.get("verdict"), str) or r.get("dot") not in Dt:
                bad.append(f"{part}.{k}.rows[{i}]")
for k, f in reg["frames"].items():
    print(k, f["state"], {v: sum(1 for r in f["rows"] if r["verdict"] == v) for v in ("yes", "partly", "no")})
print("version", reg["version"], "bad", bad, {k: v for k, v in sb.items() if "warm" in k})
