"""qa-agent 2026-11-07: register v3 (qa/reports/ged-register-2026-11-07-r3.json), superseding v2. Changes:
- warm-modern-A-ed5: the "21 Camel" chenille against its SKU photo (data/camel.json) -> no; the milk-tea boucle against its SKU photo
  (data/setA.json) -> partly; the frame -> not_yet (G-ED.5: a starring product at "no").
- boho-A-fin6: the planter's dark base against the card's cached gallery photo -> partly (the listing shows natural and black-dipped
  baskets; the card is "natural" and its SKUs are size-only) -> almost.
- mediterranean-A-ed7: master-designer's eye (proposals §10) -> final_test.
Usage: python3.12 -I build_register_v3.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
V2P = "qa/reports/ged-register-2026-11-07-r2.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V2P))))
CAM = json.load(open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r3/data/camel.json")))
SA = json.load(open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r3/data/setA.json")))
reg["version"] = 3
reg["supersedes"] = V2P
reg["changes_from_v2"] = [
    "warm-modern-A-ed5: final_test -> not_yet. The 21 Camel chenille is 'no' against its SKU photo (taupe-grey woven chenille; the frame shows a caramel crinkle cushion); the milk-tea boucle is 'partly' (the photo is a pale cream, the frame a light tan). Both dots off",
    "boho-A-fin6: final_test -> almost. The planter is 'partly': its black-dipped base comes from the listing's gallery photo, but the card is 'natural' with size-only SKUs; dot off until sourcing confirms the colour",
    "mediterranean-A-ed7: almost -> final_test (master-designer, proposals §10: G-ED.10 and G-ED.13 pass)",
]
reg.pop("changes_from_v1", None)


def setrow(frame, card_id, option, **kw):
    for r in reg["frames"][frame]["rows"]:
        if r["card_id"] == card_id and (option is None or r.get("option") == option):
            r.update(kw)
            if "note" in kw:
                r["why"] = kw["note"]
            if "verdict" in kw:
                r["faithful"] = kw["verdict"]
            return r
    raise KeyError((frame, card_id, option))


fc, ph = CAM["frame"], CAM["sku_photo"]
setrow("warm-modern-A-ed5", "cushions-cj-knitted-chenille-bean-green", {"color": "21-camel-color"}, verdict="no", dot="no",
       note=("against the SKU photo (CJYD282217003CX, '21 Camel Color', view only), not the card's HEX: the photo is a taupe-grey heathered chenille "
             f"with a woven grid (relative to its white throw a* {ph['cushion_minus_neutral'][1]:+}, b* {ph['cushion_minus_neutral'][2]:+}); the frame shows a caramel crinkled "
             f"cushion (relative to the white boucle in its light a* {fc['cushion_minus_neutral'][1]:+}, b* {fc['cushion_minus_neutral'][2]:+}), neither the colour nor the grid. "
             "The earlier 'yes' (phase B) was read against the card's name and HEX, with no SKU photo. Fix: a verified option of this card (proposals §12.4) and a local pass, not a recolour"))
d = SA["frame_milk_tea_minus_white"]
setrow("warm-modern-A-ed5", "cushions-cj-boucle-teddy", {"color": "milk-tea-color", "size": "50x50"}, verdict="partly", dot="no",
       note=("against the SKU photo ('milk tea color', view only): a pale cream boucle, barely off its White SKU in the same photo setup (L* +1.1, a* +0.9, b* +1.6); "
             "in the frame it is a light tan, against the white stoneware vase in the same sun L* -7.9, a* +4.4, b* +8.5. Boucle and size right. "
             "Fix, 0 tokens: shift it in code toward the photo's relation to white (a G-ED.3 fix of the same SKU), then QA"))
setrow("warm-modern-A-ed5", "sofa-cover-cj-cotton-muslin-fringe", {"other": "flax-brown"},
       note="against the SKU photo (flax brown, view only): a greige crinkled muslin with a short fringe; the frame's is warmer in the golden light, same family: yes")
wm = reg["frames"]["warm-modern-A-ed5"]
wm["state"] = "not_yet"
wm["state_source"] = ("QA: qa/reports/ged-register-2026-11-07-r3.md (set A against the SKU photos); G-ED.5: a starring product at 'no' blocks final_test. "
                      "Eye: G-ED.10 / G-ED.13 pass (unchanged). Note: proposals §12 reads 'stays final test with one dot fewer'; that conflicts with G-ED.5 ('no' never) and needs the manager / owner")
wm["open"] = ["the camel chenille: sourcing verifies a caramel option of this card by photo (6 Brown, 7 Earthy Yellow), then a local pass of the cushion (~650, owner's choice, proposals §12.4)",
              "the milk-tea boucle: a 0-token recolour toward its SKU photo, then QA"]
pl = setrow("boho-A-fin6", "planter-zendrop-seagrass-belly-basket-45", None, verdict="partly", dot="no",
            note=("the frame's planter has a black-dipped base. The card's cached gallery photo (urls[0], assets/renders/house-nordic-2026-10-25/refs/...a75cb5e9...jpg) shows "
                  "natural and black-dipped two-tone baskets side by side, and render-agent's reference crop (ed2-crops/bo-planter) picked a dipped one. "
                  "But the card is 'natural' and its SKUs are size-only (the card's own note: 'confirm the natural colour before ordering'): the base exists in the listing, "
                  "not as a chosen option. Fix: sourcing confirms which colour the 45 x 36 SKU ships; if natural, a 0-token recolour of the base"))
bo = reg["frames"]["boho-A-fin6"]
bo["state"] = "almost"
bo["state_source"] = "QA: qa/reports/ged-register-2026-11-07-r3.md (the planter's base against the card's photos); eye: proposals §5, §7 (pass)"
bo["open"] = ["sourcing-agent: the colour the planter's 45 x 36 SKU ships (natural or black-dipped); then 'yes' as is, or a 0-token recolour of the base"]
me = reg["frames"]["mediterranean-A-ed7"]
me["state"] = "final_test"
me["state_source"] = "QA: qa/reports/ged-register-2026-11-07-r2.md (G-ED.8-G-ED.12); eye: docs/proposals/clay-r2-and-ged-verdicts-2026-11-07.md §10 (G-ED.10, G-ED.13 pass)"
me["designer_eye"] = {"G-ED.10": "pass", "G-ED.13": "pass", "G-ED.16": "pass"}
me.pop("open", None)
me["before_site"] = ["the White SKU's stock (B22)", "the bench-back-cushions slot", "dots for the three bench cushions"]
out = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r3.json")
json.dump(reg, open(out, "w"), ensure_ascii=False, indent=1)
S, D = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = [k for part in ("frames", "closeups") for k, f in reg[part].items() if f["state"] not in S or (f["state"] != "not_yet" and not f["rows"])
       or any(not isinstance(r["card_id"], str) or not isinstance(r["verdict"], str) or r["dot"] not in D for r in f["rows"])]
for k, f in reg["frames"].items():
    print(k, f["state"], {v: sum(1 for r in f["rows"] if r["verdict"] == v) for v in ("yes", "partly", "no")})
print("version", reg["version"], "bad", bad)
