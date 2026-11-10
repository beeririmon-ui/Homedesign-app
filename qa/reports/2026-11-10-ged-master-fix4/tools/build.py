"""qa-agent 2026-11-10: G-ED round 3 on MB1 (nordic-MB-A-fix4.png, warm-modern-MB-A-fix3.png; mb1-fix2/3/4.json), from data/diff.json,
data/measure.json and QA's grids and seam sheets (overlays/), with the wall-plane scale of qa/reports/2026-11-08-ged-master-fix1 (boards2 /
the niche). Writes qa/reports/2026-11-10-ged-master-fix4.json and register v10 (qa/reports/ged-register-2026-11-10-r10.json).
Usage: python3 -I build.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix4/data")
DF, MS = json.load(open(os.path.join(D, "diff.json"))), json.load(open(os.path.join(D, "measure.json")))
F1 = json.load(open(os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1.json")))
prev = {k: {r["card_id"]: r for r in v["rows"]} for k, v in F1["frames"].items()}


def row(card, option, verdict, dot, why, fix=None, units=None, sale_unit=None):
    r = dict(card_id=card, option=option, verdict=verdict, dot=dot, note=why, why=why, faithful=verdict, present=True,
             card=card + (f" ({', '.join(option.values())})" if isinstance(option, dict) else ""))
    if fix:
        r["fix"] = fix
    if units:
        r["units_in_frame"], r["sale_unit"] = units, sale_unit
    return r


N, W = MS["nordic"], MS["warm-modern"]
nordic = [
    prev["nordic-MB-A-fix1"]["bedding-cj-washed-linen-natural-set"],
    row("pillowcases-cj-pure-linen-envelope-pair-48x74", {"other": "a-pair-of-rain-and-dew-hemp"}, "yes", "yes",
        "P5: plain envelopes now, no flange (the open end shows on the right one), natural linen in the card's tone", None, 1, "a pair in one SKU ('A Pair')"),
    row("cushions-cj-boucle-teddy", {"color": "white", "size": "30x50"}, "yes", "yes",
        f"P5 + code: about 325 px wide against the 450 px pillowcase (0.72 against 50/74 = 0.68: inside +-15 %); white bouclé, its lit face {N['lumbar']} against the duvet {N['duvet']} (less yellow than the linen). The fill left of it is a G-ED.9 item of the frame, not of the cushion"),
    prev["nordic-MB-A-fix1"]["throw-cj-cotton-linen-light-gray-200x230"],
    row("nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862", {"color": "D"}, "yes", "yes",
        "P7: option D's bell, 183 px high, H/W 2.15 against 2.23; on the wall's own scale at its x (6.86 px/cm, about 7.2 with its place in front of the wall) about 25 cm against 24.5 (x1.04)"),
    row("candle-holders-cj-travertine-pedestal", None, "yes", "yes",
        "P7: thick cups on cones, 85 and 84 px high on 52 / 53 px cups (H/W 1.63 / 1.58 against 1.57), about 11.3 cm and 6.9 cm against 11 and 7 on the wall's scale at their x; the same height, as the set of 2 x Small; the generic mug now about 9.4 cm",
        None, 1, "a set of 2 (the site's pack)"),
    row("bedside-sconces-cj-linen-wave-flush", {"size": "beige-fabric"}, "yes", "no",
        "code from the source: x0.80 (right) and x0.82 (left); on the wall's own scale both about 24 cm wide; boards continuous behind, shadows the originals' scaled, no ghost (x2-x4). Dot off until CE is verified",
        None, 2, "single lamps (a pair is 2 units)"),
    prev["nordic-MB-A-fix1"]["curtains-aliexpress-linen-blend-s-fold-180502"],
    prev["nordic-MB-A-fix1"]["vase-aliexpress-vintage-distressed-clay-vase-589009"],
    prev["nordic-MB-A-fix1"]["planter-zendrop-seagrass-belly-38x34"],
    prev["nordic-MB-A-fix1"]["basket-cj-jute-rope-cylinder"],
]
wm = [
    prev["warm-modern-MB-A-fix1"]["bedding-cj-washed-linen-natural-set"],
    row("pillowcases-cj-pure-linen-envelope-pair-48x74", {"other": "caramel-pairs"}, "partly", "no",
        "P6 composited only the cushion area (seedream returned its own aspect): both caramel pillowcases still carry the flange border; the product is a plain envelope (G-ED.2)",
        "targeted pass P6b (week 3), the crop cut at one of seedream's aspects", 1, "a pair in one SKU ('Caramel Pairs')"),
    row("cushions-cj-boucle-teddy", {"color": "milk-tea-color", "size": "30x50"}, "yes", "yes",
        f"P6 + code: 360 px against the 530 px pillowcase (0.68 = 50/74); now a cream above the natural-linen duvet: lit face {W['lumbar']} against {W['duvet']}, i.e. L* {W['lumbar_minus_duvet'][0]:+}, b* {W['lumbar_minus_duvet'][2]:+} (MB-A: -3.2 / +2.1; the photos' milk tea over the bedding +7.3 / +5.6)"),
    prev["warm-modern-MB-A-fix1"]["sofa-cover-cj-cotton-muslin-fringe"],
    prev["warm-modern-MB-A-fix1"]["wall-sconce-cj-travertine-cone-walnut"],
    row("candle-holders-cj-travertine-pedestal", None, "yes", "yes",
        "P8: cups on cones, 82 and 80 px high on 53 / 52 px cups (H/W 1.55 / 1.54 against 1.57), about 11.2 cm on 7.2 cm at 7.3 px/cm (the frontal wall)", None, 1, "a set of 2 (the site's pack)"),
    row("nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862", {"color": "D"}, "yes", "yes",
        "P8: the bell in light sand with the olive sprig, 182 px high (about 24.9 cm, x1.02); H/W 1.92 against 2.23 (a broad bell, -14 %, inside +-15 %); the leaf ghosts gone (code)"),
    prev["warm-modern-MB-A-fix1"]["floor-lamp-cj-pleated-walnut-stem-158"],
    prev["warm-modern-MB-A-fix1"]["planter-cj-cement-ribbed-belly"],
    prev["warm-modern-MB-A-fix1"]["curtains-aliexpress-beige-linen-sheer-curtains-554205"],
    prev["warm-modern-MB-A-fix1"]["sill-vase-cj-cream-fluted-column-25"],
    prev["warm-modern-MB-A-fix1"]["basket-cj-jute-rope-cylinder"],
]
cnt = lambda rows: {v: sum(1 for r in rows if r["verdict"] == v) for v in ("yes", "partly", "no")}  # noqa: E731
out = {
    "id": "2026-11-10-ged-master-fix4", "date": "2026-11-10", "by": "qa-agent", "follows": "qa/reports/2026-11-08-ged-master-fix1.json",
    "inputs": {"frames": ["assets/renders/master/editorial-2026-11-07/nordic/nordic-MB-A-fix4.png", "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix3.png"],
               "records": ["mb1-fix2.json", "mb1-fix3.json", "mb1-fix4.json"], "compared_with": "fix1 (the frames QA last checked)"},
    "G-ED.8": {"nordic": {"areas": [c["bbox"] for c in DF["nordic"]["components"]], "verdict": "pass: the bed head with the nightstand (P5 + P7), the chair cloth (fix2, fix3), both sconces (fix3)"},
               "warm-modern": {"areas": [c["bbox"] for c in DF["warm-modern"]["components"]], "verdict": "pass: the cushion area (P6), the nightstand with the old ghost (P8, fix2)"}},
    "G-ED.9": {
        "nordic": [
            {"where": "left of the lumbar, x 1585-1640, y 780-850", "verdict": "fail (small, code)", "finding": "a pale sheet-coloured triangle with a sharp apex and straight sides, where the old wider lumbar was; visible at 100 %, reads as a fill, not as sheet between pillows (overlays/seam-n-wedge.jpg)",
             "fix": "code, 0 tokens: continue the left pillowcase's linen (its folds and grain) down to the lumbar, with the soft contact shadow under the pillow's edge; QA re-checks at x4"},
            {"where": "the right pillowcase, the shadow's top edge (x 2010-2100, y about 745)", "verdict": "pass, with a note", "finding": "the lumbar's shadow under the low sun, its top at the lumbar's own top (755) and soft (a penumbra of about 6 px); straight over about 90 px like the lumbar's top edge; reads plausible at 100 % and x2"},
            {"where": "the chair cloth's lower edge (343 px above C* 8)", "verdict": "pass", "finding": "the warm pixels between the folds by the chair leg are the floor seen through the gap, as in fix1, not the old colour on the cloth"},
            {"where": "sconces, nightstand", "verdict": "pass", "finding": "boards continuous, no ghost, candles whole"}],
        "warm-modern": [
            {"where": "the pillowcase gap at the cushion's top, x about 2000-2060, y 760-812", "verdict": "fail (small, code)", "finding": "a blurred dark blob with no grain where the gap between the caramel pillowcases meets the new, lower cushion top (overlays/seam-w-spot.jpg)",
             "fix": "code, 0 tokens: carry the gap's lines (the cream back pillow's edge, the caramel folds) down to the cushion's top, with the frame's grain; or inside P6b's mask"},
            {"where": "nightstand", "verdict": "pass", "finding": "plaster continuous, no ghost of the old sprig, the new sprig whole"}]},
    "G-ED.6": {"nordic": f"pass: the chair cloth is now the designer's charcoal (Lab {N['chair cloth'][:3]}, C* {N['chair cloth'][3]}), far from our light-grey throw ({N['throw'][:3]}) and from any throw we sell", "warm-modern": "pass"},
    "frames": {"nordic-MB-A-fix4": dict(state="almost", rows=nordic, counts=cnt(nordic),
                                        why_state="every product yes; one small code fix (the wedge, G-ED.9) and the designer's eye (G-ED.10, G-ED.13) still open"),
               "warm-modern-MB-A-fix3": dict(state="not_yet", rows=wm, counts=cnt(wm),
                                             why_state="the caramel pillowcases are 'partly' and need a pass (P6b); one small code fix (the gap spot)")},
    "left": {
        "code_0_tokens": ["Nordic: fill the wedge left of the lumbar with the pillowcase's linen and its contact shadow",
                          "warm modern: rebuild the pillowcase gap down to the cushion's top (or within P6b)"],
        "week_3_pass": [{"id": "P6b", "frame": "warm-modern-MB-A-fix3", "what": "the two caramel pillowcases as plain envelopes (no flange); the cushion, the cream back pillows and the bedding kept",
                         "tokens": 650, "input": "a crop cut at one of seedream's returned aspects (the lesson in mb1-fix4.json), e.g. x 1380-2700, y 520-1086 (1320 x 566, 2.33:1, as 3122 x 1338); the mask over the two caramel pillowcases only; the cushion protected"}],
        "then": "QA round 4 on the changed areas (G-ED.8, G-ED.9), then master-designer's eye (G-ED.10, G-ED.13) on both frames",
    },
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-10-ged-master-fix4.json"), "w"), ensure_ascii=False, indent=1)
V9P = "qa/reports/ged-register-2026-11-08-r9.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V9P))))
reg.update(version=10, supersedes=V9P, id="ged-register-2026-11-10-r10", date="2026-11-10", by="qa-agent")
reg.pop("changes_from_v8", None)
for k, f in out["frames"].items():
    reg["master"][k] = dict(file=out["inputs"]["frames"][0 if k.startswith("nordic") else 1], state=f["state"], rows=f["rows"],
                            record="qa/reports/2026-11-10-ged-master-fix4.json", note="TEST frame (MB1 fix round 3), not for the site; the site does not read this section")
reg["master_superseded_by"] = {"nordic-MB-A": "nordic-MB-A-fix4", "nordic-MB-A-fix1": "nordic-MB-A-fix4",
                               "warm-modern-MB-A": "warm-modern-MB-A-fix3", "warm-modern-MB-A-fix1": "warm-modern-MB-A-fix3"}
reg["changes_from_v9"] = ["master: nordic-MB-A-fix4 (almost: all yes; the wedge to fix in code; the designer's eye) and warm-modern-MB-A-fix3 (not_yet: the caramel pillowcases' flanges, pass P6b in week 3) added; the fix1 entries superseded"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-10-r10.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = [f"{p}.{k}" for p in ("frames", "closeups", "master") for k, f in (reg.get(p) or {}).items()
       if f.get("state") not in S or any(not isinstance(r.get("card_id"), str) or r.get("dot") not in Dt or (r.get("units_in_frame") is not None and not 1 <= r["units_in_frame"] <= 12) for r in f.get("rows", []))]
print("v10 bad", bad)
for k, f in out["frames"].items():
    print(k, f["state"], f["counts"])
