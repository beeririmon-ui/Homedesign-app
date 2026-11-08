"""qa-agent 2026-11-07: register v8 (qa/reports/ged-register-2026-11-07-r8.json), superseding v7:
- warm-modern-A-ed8 (new; supersedes ed4-ed7): CAM1 (owner) - set B's camel corduroy in place of the '21 Camel' chenille (render-agent,
  cam1.json; QA data/ed8*.json) -> yes, dot on; the frame -> final_test; units_in_frame on its multi-unit products (as v6 did for the others).
- tool: the pilot's set B corduroy against the card's 50 x 50 (render-agent: prompted at 45 x 45).
Usage: python3 -I build_register_v8.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
V7P = "qa/reports/ged-register-2026-11-07-r7.json"
R8 = os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r8")
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V7P))))
E8, EC = json.load(open(os.path.join(R8, "data/ed8.json"))), json.load(open(os.path.join(R8, "data/ed8-colour.json")))
reg.update(version=8, supersedes=V7P, id="ged-register-2026-11-07-r8", date="2026-11-07", by="qa-agent")
reg.pop("changes_from_v6", None)
wm = copy.deepcopy(reg["frames"]["warm-modern-A-ed7"])
wm["file"] = "assets/renders/editorial-phase-b-2026-11-06/warm-modern-A-ed8.png"
rows = [r for r in wm["rows"] if r["card_id"] != "cushions-cj-knitted-chenille-bean-green"]
note = (f"CAM1 (owner): set B's camel corduroy in place of the '21 Camel' chenille (render-agent's targeted pass, 650; ed8). G-ED.8: {E8['changed_px']} px, one area, "
        f"0 outside the old cushion's outline grown 3 px, 0 on the White bouclé's own surface, the candles untouched. G-ED.3: the hue of the SKU photo's camel "
        f"(QA {EC['d_hue']:+} deg with the frame light neutralised on the White bouclé; render-agent +0.7 deg, dE76 2.9 with its gain); the sunlit ribs carry the golden "
        "light's extra chroma, as the white and milk-tea bouclé beside it do. G-ED.2: 20-21 ribs against about 19 in the photo (inside +-1 per 10); the wheat-grain "
        "blocks show on the lit ribs at x4 and only as a hint in the shade (a note). G-ED.4: against the milk-tea bouclé (50 x 50) at the same lean, width x1.02, "
        "height x0.93: about 10 % small in height, inside +-15 %. G-ED.9: the edges clean at x4 (the white cushion, the wall, the shade), no ghost of the old outline")
rows.insert(6, dict(card_id="cushions-cj-wide-stripe-corduroy-light-green", option={"color": "camel"}, verdict="yes", dot="yes", note=note,
                    card="cushions-cj-wide-stripe-corduroy-light-green (Camel)", present=True, faithful="yes", why=note))
for r in rows:
    if r["card_id"] == "cushions-cj-boucle-teddy" and not r.get("option"):
        r["note"] = r["why"] = "white bouclé, one in the frame (the other became Milk Tea in ED2)"
    if r["card_id"] == "accent-sconces-aliexpress-travertine-cylinder-walnut-choice":
        r.update(units_in_frame=2, sale_unit="single lamps (the card: '₪299 per unit', 'pair (2 units, ₪598)')",
                 units_note="register v8: two travertine cylinders, either side of the triptych; sold as single lamps, so the look adds 2")
    if r["card_id"] == "candle-holders-cj-travertine-pedestal":
        r.update(units_in_frame=1, sale_unit="a set of 2 (the site's pack set_qty 2)", units_note="register v8: the pedestal pair, one set")
    if r["card_id"] == "framed-art-aliexpress-frameless-minimalist-wall-art-631735":
        r["units_note"] = ("register v8: three prints; the card sells them one at a time (TL2356-1/-2/-3, the default is -1) or as the option 'tl2356-3pcs'. "
                           "No units_in_frame: the story point has no option, so the look would add one print. Open: the point names {color: tl2356-3pcs} "
                           "(frontend-dev), then QA keys this row to that option")
wm["rows"] = rows
reg["frames"]["warm-modern-A-ed8"] = wm
wm["state"] = "final_test"
wm["state_source"] = ("QA: qa/reports/ged-register-2026-11-07-r8.md §1 (ed8: CAM1's corduroy, G-ED.2-G-ED.4, G-ED.8, G-ED.9). Eye: G-ED.10 / G-ED.13 pass from ed5, "
                      "carried over: ed6-ed8 change only two cushions (inside their masks)")
wm.pop("open", None)
wm["before_site"] = ["data/story/story.json: the camel point becomes cushions-cj-wide-stripe-corduroy-light-green {color: camel}, the frame src warm-modern-A-ed8.png (qa_key warm-modern-A-ed8)",
                     "the triptych's point names the option tl2356-3pcs (the set of three), then QA keys its row"]
sb = reg["superseded_by"]
for k, v in list(sb.items()):
    if v == "warm-modern-A-ed7":
        sb[k] = "warm-modern-A-ed8"
sb["warm-modern-A-ed7"] = "warm-modern-A-ed8"
t = reg["tool"]["living-room/warm-modern/pilot-phase1"]
t["set_B_corduroy_size"] = {
    "file": "composite-set-B-v3-graded-v3c.png", "card": "cushions-cj-wide-stripe-corduroy-light-green, 50 x 50 (its only size)",
    "measured": "outline 232 x 196 px (cushion-polys.json) against the Oatmeal bouclé (50 x 50) at the sofa's other end, 255 x 245 px; the depth along the sofa back from the house plan's back-top line (v 0.60 left, 0.63 right): the left end about 1.16x farther at the cushions' places",
    "result": "about 53 x 46.5 cm (width x1.06, height x0.93); even read as the 45 x 45 it was prompted at, it is -10 %: inside +-15 % (G2.7)",
    "verdict": "pass (G2.7), with a note: the prompt's 45 x 45 should read 50 x 50 in the next pass (the same in set A's chenille and set C's corduroy patchwork outlines, all about 232 x 200 px)"}
reg["changes_from_v7"] = ["warm-modern-A-ed8 added (supersedes ed4-ed7): CAM1's camel corduroy yes, dot on; final_test; units on its sconces (2) and candle holders (1); the triptych needs its 3-piece option",
                          "tool: set B's corduroy inside +-15 % of 50 x 50"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r8.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = []
for part in ("frames", "closeups", "master"):
    for k, f in (reg.get(part) or {}).items():
        if f.get("state") not in S:
            bad.append(f"{part}.{k}.state")
        if part != "master" and (not isinstance(f.get("rows"), list) or (f["state"] != "not_yet" and not f["rows"])):
            bad.append(f"{part}.{k}.rows")
        for i, r in enumerate(f.get("rows") or []):
            u = r.get("units_in_frame")
            if not isinstance(r.get("card_id"), str) or not isinstance(r.get("verdict"), str) or r.get("dot") not in Dt or (u is not None and not (isinstance(u, int) and 1 <= u <= 12)):
                bad.append(f"{part}.{k}.rows[{i}]")
f = reg["frames"]["warm-modern-A-ed8"]
print("v8 bad", bad, f["state"], {v: sum(1 for r in f["rows"] if r["verdict"] == v) for v in ("yes", "partly", "no")})
