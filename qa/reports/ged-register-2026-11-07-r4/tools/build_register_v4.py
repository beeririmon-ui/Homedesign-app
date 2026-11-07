"""qa-agent 2026-11-07: register v4 (qa/reports/ged-register-2026-11-07-r4.json), superseding v3. Changes:
- warm-modern-A-ed6 (new; supersedes ed5): the milk-tea boucle recoloured (render-agent, ed6-milktea.json; QA data/ed6*.json): its colour now
  sits on the SKU photos' relation to White; its texture reads two-tone (C* of the shadows +14 over the peaks, the photo +1.6) -> partly.
  The 21 Camel stays 'no' with its dot off until the owner's CAM1 -> not_yet.
- boho-A-fin7 (new; supersedes fin6): the planter's base natural (fin7-planter.json; QA data/fin7.json) -> yes. G-ED.6 on the second
  rust cushion (left, no story point): the same product and option as the pointed one (dE76 1.5, 0.5 deg), and the brief asks for
  'Rust Orange x2': a second unit of our product, not an imitation -> the row says 2 units -> final_test.
- tool (new section, read by no site code): the warm-modern pilot phase 1 (qa/reports/2026-11-07-pilot-phase1-g1.json).
Usage: python3 -I build_register_v4.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
V3P = "qa/reports/ged-register-2026-11-07-r3.json"
R4 = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r4")
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V3P))))
E6, E6R = json.load(open(os.path.join(R4, "data/ed6.json"))), json.load(open(os.path.join(R4, "data/ed6-relation.json")))
F7, RU = json.load(open(os.path.join(R4, "data/fin7.json"))), json.load(open(os.path.join(R4, "data/boho-rust.json")))
PIL = json.load(open(os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1.json")))
reg["version"] = 4
reg["supersedes"] = V3P
reg["id"] = "ged-register-2026-11-07-r4"
reg.pop("changes_from_v2", None)


def row(frame, card_id, option="any"):
    for r in reg["frames"][frame]["rows"]:
        if r["card_id"] == card_id and (option == "any" or r.get("option") == option):
            return r
    raise KeyError((frame, card_id, option))


def setrow(r, **kw):
    r.update(kw)
    if "verdict" in kw:
        r["faithful"] = kw["verdict"]
    if "note" in kw:
        r["why"] = kw["note"]


# ---- warm-modern-A-ed6
wm = copy.deepcopy(reg["frames"]["warm-modern-A-ed5"])
wm["file"] = "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed6.png"
reg["frames"]["warm-modern-A-ed6"] = wm
mt = row("warm-modern-A-ed6", "cushions-cj-boucle-teddy", {"color": "milk-tea-color", "size": "50x50"})
d6 = E6R["milk_tea_ed6_minus_white_boucle"]
setrow(mt, verdict="partly", dot="no",
       note=(f"ed6 (render-agent's 0-token recolour, {E6['changed_px']} px, all inside the cushion): the colour now sits on the SKU photos' relation to White "
             f"(against the White boucle of the same SKU in this frame a* {d6[1]:+}, b* {d6[2]:+}; the photos a* +0.9, b* +1.6), no clipped pixel, the olive leaves intact. "
             f"But the boucle reads two-tone, cream peaks and tan valleys: C* of its darkest fifth over its lightest {E6R['milk_tea_ed6']['C_dark_minus_C_light']:+} "
             f"(the SKU photo {E6R['sku_milk-tea-color']['C_dark_minus_C_light']:+}, the White boucle here {E6R['white_boucle']['C_dark_minus_C_light']:+}); inherited from ed5 "
             f"({E6R['milk_tea_ed5']['C_dark_minus_C_light']:+}), more visible now that it is light. Fix, 0 tokens: inside the mask, bring each pixel's a*, b* to the cushion's "
             "median hue and a chroma that follows L* (the photo's flat cream), L* and the loops kept; then QA"))
cam = row("warm-modern-A-ed6", "cushions-cj-knitted-chenille-bean-green")
setrow(cam, note=cam["note"] + " ed6: untouched; the dot stays off until the owner's CAM1 (proposals §13.2)")
wm["state"] = "not_yet"
wm["state_source"] = ("QA: qa/reports/ged-register-2026-11-07-r4.md §1 (ed6 against ed5 and the SKU photos); G-ED.5: the 21 Camel (a product with a dot) is 'no', "
                      "so final_test is out until CAM1. Eye: G-ED.10 / G-ED.13 pass (unchanged from ed5)")
wm["open"] = ["the 21 Camel chenille: the owner's CAM1 (proposals §13.2), then a verified caramel or the documented exception",
              "the milk-tea boucle: a 0-token flattening of its two-tone chroma, then QA"]
# ---- boho-A-fin7
bo = copy.deepcopy(reg["frames"]["boho-A-fin6"])
bo["file"] = "assets/renders/editorial-phase-b-2026-11-06/boho-A-fin7.png"
reg["frames"]["boho-A-fin7"] = bo
pl = row("boho-A-fin7", "planter-zendrop-seagrass-belly-basket-45")
setrow(pl, verdict="yes", dot="yes",
       note=(f"fin7 (render-agent's 0-token recolour, {F7['changed_px']} px, all inside the base): the black-dipped base is natural seagrass now, as the card's 'natural' "
             f"and the natural baskets in its cached gallery photo. Base Lab {F7['base_fin7']} against the body band above {F7['body_band_fin7']} "
             f"(L ratio {F7['base_over_body_L']}, the belly turning from the light; hue {F7['hue_ab_base']} vs {F7['hue_ab_body']} deg); the weave carried down "
             f"(texture sd {F7['texture_hf_sd_base']} in the shade vs {F7['texture_hf_sd_body']} in the sun above); the old dip line reads as the belly's fold "
             f"(median L* step {F7['seam_step_L_median']}), the base's bottom edge clean at x4. The shipping colour: natural, per the coordinator (no sourcing file seen by QA)"))
for fr in ("boho-A-fin6", "boho-A-fin7"):
    ru = row(fr, "cushions-cj-washed-cotton-frayed")
    setrow(ru, note=(ru["note"] + f". Two units in the frame (G-ED.6, register v4): the left one, without a story point, is the same product and option as the pointed one "
                     f"(face dE76 {RU['dE76_left_vs_right']}, hue {RU['d_hue_deg']:+} deg, the same washed weave and frayed edge at x3), and the brief asks for 'Rust Orange x2' "
                     "(briefs/render-editorial-phase-b-2026-11-06.md, the products table and the boho prompt): a second unit of our product, not an imitation"),
           units_in_frame=2, ged6="second unit of our product (brief: x2), not an imitation")
    if fr == "boho-A-fin6":
        ru["card"] = "cushions-cj-washed-cotton-frayed (Rust Orange) x2"
row("boho-A-fin7", "cushions-cj-washed-cotton-frayed")["card"] = "cushions-cj-washed-cotton-frayed (Rust Orange) x2"
bo["state"] = "final_test"
bo["state_source"] = ("QA: qa/reports/ged-register-2026-11-07-r4.md §2 (the planter's base; G-ED.6 on the second rust cushion). Eye: proposals §5, §7 (G-ED.10, G-ED.13 pass), "
                      "carried over: fin7 changes only the planter's base (21,034 px, 0 outside it)")
bo.pop("open", None)
bo["before_site"] = ["the story point of the rust cushion says 'in the frame: two units' (as the sconces' does), and 'buy the look' adds 2",
                     "data/story/story.json moves to boho-A-fin7.png (qa_key boho-A-fin7)"]
# ---- the chains
sb = reg["superseded_by"]
for k, v in list(sb.items()):
    if v == "warm-modern-A-ed5":
        sb[k] = "warm-modern-A-ed6"
    if v == "boho-A-fin6":
        sb[k] = "boho-A-fin7"
sb["warm-modern-A-ed5"] = "warm-modern-A-ed6"
sb["boho-A-fin6"] = "boho-A-fin7"
# ---- the tool section (G1 / G2, not G-ED; no site code reads it)
reg["tool"] = {
    "note": "tool assets (the 'design it yourself' layers): G1 and G2 from docs/ops/quality-gates-2026-11-02.md, not G-ED; not read by site/tools/lib/qa-frames.ts",
    "living-room/warm-modern/pilot-phase1": {
        "record": "qa/reports/2026-11-07-pilot-phase1-g1.json",
        "folder": PIL["pilot_folder"],
        "version_checked": "v3 with display grade v3b",
        "approval_3": PIL["approval_3"],
        "assets": [
            {"asset": "shell-v3.png", "checks": "G1.4 lock vs clay r4 (all named lines, WMC10 in): worst p90 2 px at 1920; the wedge in the art/sconce area 2.36 (v3) / 1.86 (v3b)", "verdict": "pass"},
            {"asset": "shell-v3-graded-v3b.png (the bench slab)", "checks": "the lit top b* 8.2 (no longer yellow); the front face mauve (HSV H 23.4 / 27.0 in the composites), a yellow sliver at the left end", "verdict": "fail", "fix": "F1", "owner": "render-agent"},
            {"asset": "the back wall on display (v3b)", "checks": "centre 89.8, right 85.1 (targets met); corner 82.6 against the expected ~86; window wall 72-76", "verdict": "pass; D1 to the designer"},
            {"asset": "fixed-furniture.png + fixed-furniture-shadow.png", "checks": "IoU 0.996 / 0.994 / 0.987; outline p90 <= 1 px at 1920; soft shadow", "verdict": "pass"},
            {"asset": "layers/cushions/set-A, set-B, set-C (+ shadows)", "checks": "G1.1 all 12 items; set C Dark Coffee dE00 1.4, +2.8 deg against its SKU photo (left as is); no halo at x4", "verdict": "pass"},
            {"asset": "composite-set-A/B/C-v3.png (ungraded)", "checks": "swap-diff: 0 px outside the products and shadows, all 6 pairs", "verdict": "pass"},
            {"asset": "composite-set-A/B/C-v3-graded-v3b.png + shell-furniture-v3-graded-v3b.png", "checks": "swap-diff on display: up to 14,726 px over 2 levels outside (deep darks), the toe computed per file", "verdict": "fail", "fix": "F2", "owner": "render-agent"},
            {"asset": "shell-fix-v3.json lock record (pass:false)", "checks": "a measurement artefact: the mullion's other face, and one outlier of 5 samples after an affine", "verdict": "record to correct", "fix": "F3", "owner": "render-agent"},
        ],
        "fixes": PIL["fixes"],
    },
}
reg["changes_from_v3"] = [
    "warm-modern-A-ed6 added (supersedes ed5): the milk-tea boucle partly (colour right, the boucle two-tone); the 21 Camel no, its dot off until CAM1; not_yet",
    "boho-A-fin7 added (supersedes fin6): the planter yes (natural base); the rust cushion x2 = a second unit of our product (G-ED.6), not an imitation; final_test",
    "boho-A-fin6: the rust cushion's row notes the two units (the same decision)",
    "tool: a new section, the warm-modern pilot phase 1 (G1/G2): conditional yes for approval 3 after F1",
]
reg["schema"]["units_in_frame"] = ("optional on a row: how many units of that product and option the frame shows, when more than one "
                                   "(G-ED.6: a second unit the brief asks for is our product, not an imitation; the story point says it and 'buy the look' adds that many)")
reg["schema"]["tool"] = "tool.<room/style/phase>: G1/G2 results of tool assets, kept apart from the editorial frames; the site does not read it"
reg["date"] = "2026-11-07"
reg["by"] = "qa-agent"
out = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r4.json")
json.dump(reg, open(out, "w"), ensure_ascii=False, indent=1)
# the site's checkRegister (site/tools/lib/qa-frames.ts), mirrored
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
print("version", reg["version"], "bad", bad, "superseded_by", {k: v for k, v in reg["superseded_by"].items() if "ed" in k or "fin" in k})
