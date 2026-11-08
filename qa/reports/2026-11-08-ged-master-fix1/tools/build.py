"""qa-agent 2026-11-08: G-ED round 2 on the MB1 fix round (assets/renders/master/editorial-2026-11-07/*-fix1.png, mb1-fix.json), from
data/diff.json, data/boards2.json, data/measure.json and QA's grids and seam sheets (overlays/). Writes
qa/reports/2026-11-08-ged-master-fix1.json and register v9 (qa/reports/ged-register-2026-11-08-r9.json: v8 with the master section moved
to the fix1 frames). Usage: python3 -I build.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1/data")
DF, BD, MS = (json.load(open(os.path.join(D, n))) for n in ("diff.json", "boards2.json", "measure.json"))
MB1 = json.load(open(os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1.json")))
PXN = 6.08                                              # the pillowcase basis at x 2165 (MB1)
rB, rH, rS = BD["ratio_vs_pillowcase"]["bottle"], BD["ratio_vs_pillowcase"]["holders"], BD["ratio_vs_pillowcase"]["sconce_right"]
left_ratio = round((BD["theil_sen"][0] * 1447 + BD["theil_sen"][1]) / BD["pitch_at"]["pillowcase_2165"], 3)
N = dict(  # Nordic, nightstand plane (px/cm on the wall at each x; objects about 20-30 cm in front read about 5-10 % larger again)
    px_cm_bottle=round(PXN * rB, 2), px_cm_holders=round(PXN * rH, 2), px_cm_sconce_right=round(PXN * rS, 2), px_cm_sconce_left=round(PXN * left_ratio, 2),
    bottle_px=257, holder_left_px=123, holder_right_px=108, cup_left_px=72, cup_right_px=69, mug_h_px=85, sconce_right_w_px=145, sconce_right_h_px=123,
    sconce_left_w_px=80, sconce_left_h_px=75)
N["bottle_x"] = round(N["bottle_px"] / N["px_cm_bottle"] / 24.5, 2)
N["holder_left_x"] = round(N["holder_left_px"] / (PXN * (BD["theil_sen"][0] * 2595 + BD["theil_sen"][1]) / BD["pitch_at"]["pillowcase_2165"]) / 11, 2)
N["holder_right_x"] = round(N["holder_right_px"] / (PXN * (BD["theil_sen"][0] * 2678 + BD["theil_sen"][1]) / BD["pitch_at"]["pillowcase_2165"]) / 11, 2)
N["cup_x"] = round(N["cup_left_px"] / N["px_cm_holders"] / 7, 2)
N["mug_height_cm"] = round(N["mug_h_px"] / N["px_cm_bottle"], 1)
N["sconce_right_x"] = [round(N["sconce_right_w_px"] / N["px_cm_sconce_right"] / 24, 2), round(N["sconce_right_h_px"] / N["px_cm_sconce_right"] / 20, 2)]
N["sconce_left_x"] = [round(N["sconce_left_w_px"] / N["px_cm_sconce_left"] / 24, 2), round(N["sconce_left_h_px"] / N["px_cm_sconce_left"] / 20, 2)]
W = dict(px_cm=7.16, niche_ratio_right_left=MS["warm-modern"]["niche_scale"]["ratio_right_left"], bottle_px=215, bottle_w_px=105, holder_left_px=100, holder_right_px=92,
         cup_px=50, sconce_rim_px=106)
W["bottle_x"] = round(W["bottle_px"] / W["px_cm"] / 24.5, 2)
W["holder_x"] = [round(W["holder_left_px"] / W["px_cm"] / 11, 2), round(W["holder_right_px"] / W["px_cm"] / 11, 2)]
W["holder_HW"] = [round(W["holder_left_px"] / W["cup_px"], 2), round(W["holder_right_px"] / W["cup_px"], 2)]
W["cup_x"] = round(W["cup_px"] / W["px_cm"] / 7, 2)
W["sconce_x"] = round(W["sconce_rim_px"] / W["px_cm"] / 15, 2)
mN, mW = MS["nordic"], MS["warm-modern"]


def row(card, option, verdict, dot, why, fix=None, units=None, sale_unit=None):
    r = dict(card_id=card, option=option, verdict=verdict, dot=dot, note=why, why=why, faithful=verdict, present=True,
             card=card + (f" ({', '.join(option.values())})" if isinstance(option, dict) else ""))
    if fix:
        r["fix"] = fix
    if units:
        r["units_in_frame"], r["sale_unit"] = units, sale_unit
    return r


prev = {k: {r["card_id"]: r for r in v["rows"]} for k, v in MB1["frames"].items()}
nordic = [
    prev["nordic-MB-A"]["bedding-cj-washed-linen-natural-set"],
    prev["nordic-MB-A"]["pillowcases-cj-pure-linen-envelope-pair-48x74"],
    prev["nordic-MB-A"]["cushions-cj-boucle-teddy"],
    row("throw-cj-cotton-linen-light-gray-200x230", None, "yes", "yes",
        f"P1: a flat light-grey cotton-linen throw with a plain hem, no pile; its lit face {mN['throw (P1)']['lit'][:3]} sits at the white panelling's level in shade ({mN['neutral: white panelling (shade)']['lit'][:3]}) and less yellow, as the photo's light grey sits under its white"),
    row("nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862", {"color": "D"}, "partly", "no",
        f"P2: option D's bell with the long thin neck, H/W {round(257 / 108, 2)} against 2.23; but still x{N['bottle_x']} high in the nightstand's own plane (the wall's board pitch, {N['px_cm_bottle']} px/cm at its x), about x1.4 allowing for its place in front of the wall (G-ED.4); the colour a warm tan in the sun (lit {mN['bottle (P2)']['lit'][:3]}), L* -17 against the panelling, inside the card's relation",
        "targeted pass P7 (scale; the input with the objects already shrunk)"),
    row("candle-holders-cj-travertine-pedestal", None, "partly", "no",
        f"P2: thick cups on cones, H/W {round(123 / 72, 2)} and {round(108 / 69, 2)} against 1.57, two pillar candles; but x{N['holder_left_x']} and x{N['holder_right_x']} high, cups x{N['cup_x']} wide, in the nightstand's plane (G-ED.4)",
        "targeted pass P7", 1, "a set of 2 (the site's pack)"),
    row("bedside-sconces-cj-linen-wave-flush", {"size": "beige-fabric"}, "partly", "no",
        f"code x0.68 on both from the pillowcase basis; on the wall's own scale the right one is now x{N['sconce_right_x'][0]} wide / x{N['sconce_right_x'][1]} high (inside +-15 %), the left one x{N['sconce_left_x'][0]} / x{N['sconce_left_x'][1]} (too small: the wall is farther there); no ghost of the old shapes, boards continuous, the left one dimmed. No dot until CE is verified",
        "code, 0 tokens: both rescaled from the originals, x0.80 (right) and x0.82 (left)", 2, "single lamps (a pair is 2 units)"),
    prev["nordic-MB-A"]["curtains-aliexpress-linen-blend-s-fold-180502"],
    row("vase-aliexpress-vintage-distressed-clay-vase-589009", None, "yes", "yes",
        f"P3: a slim cream column with fine horizontal ribbing, H/W about 2.1 (line 1.85), the colour as the photo ({mN['sill vase (P3)']['median'][:3]} against {MS['refs']['clay vase']['median'][:3]}); clean against the glazing at x4"),
    row("planter-zendrop-seagrass-belly-38x34", None, "yes", "yes",
        f"code: pale yellow-green seagrass now (lit {mN['planter (code)']['lit'][:3]}, h {mN['planter (code)']['lit'][4]} against the photo's {MS['refs']['planter seagrass']['lit'][4]}), clearly apart from the jute basket (h {mN['jute basket']['lit'][4]}); the weave kept"),
    prev["nordic-MB-A"]["basket-cj-jute-rope-cylinder"],
]
wm = [
    prev["warm-modern-MB-A"]["bedding-cj-washed-linen-natural-set"],
    prev["warm-modern-MB-A"]["pillowcases-cj-pure-linen-envelope-pair-48x74"],
    prev["warm-modern-MB-A"]["cushions-cj-boucle-teddy"],
    prev["warm-modern-MB-A"]["sofa-cover-cj-cotton-muslin-fringe"],
    row("wall-sconce-cj-travertine-cone-walnut", None, "yes", "no",
        f"code x0.8: rim about {W['sconce_rim_px']} px = x{W['sconce_x']} of D15 on the wall's scale (the pill niche is the same height at both ends: right/left {W['niche_ratio_right_left']}, so the wall is frontal and the pillowcase basis holds there); no ghost. Dot off until CE is checked (the designer's table)",
        None, 2, "single lamps (a pair is 2 units)"),
    row("candle-holders-cj-travertine-pedestal", None, "partly", "no",
        f"P4: two of about the same height, cup on cone, cups x{W['cup_x']} of 7 cm wide; but the bodies too tall: x{W['holder_x'][0]} / x{W['holder_x'][1]} high, H/W {W['holder_HW'][0]} / {W['holder_HW'][1]} against 1.57 (G-ED.4)",
        "targeted pass P8 (shorter bodies, the input already corrected)", 1, "a set of 2 (the site's pack)"),
    row("nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862", {"color": "D"}, "partly", "no",
        f"P4: option D's bell with a long neck in light sand (lit {mW['bottle (P4)']['lit'][:3]}, above the plaster as the photo's sand), H/W {round(215 / 105, 2)} against 2.23; but x{W['bottle_x']} high (G-ED.4). The old sprig left two leaf fragments floating right of the new sprig (x 1332-1350, y 651-685): a ghost (G-ED.9)",
        "targeted pass P8 (scale); code, 0 tokens: remove the two leaf fragments"),
    prev["warm-modern-MB-A"]["floor-lamp-cj-pleated-walnut-stem-158"],
    prev["warm-modern-MB-A"]["planter-cj-cement-ribbed-belly"],
    prev["warm-modern-MB-A"]["curtains-aliexpress-beige-linen-sheer-curtains-554205"],
    prev["warm-modern-MB-A"]["sill-vase-cj-cream-fluted-column-25"],
    prev["warm-modern-MB-A"]["basket-cj-jute-rope-cylinder"],
]
cnt = lambda rows: {v: sum(1 for r in rows if r["verdict"] == v) for v in ("yes", "partly", "no")}  # noqa: E731
cc = mN["chair_cloth_vs_throw"]
out = {
    "id": "2026-11-08-ged-master-fix1", "date": "2026-11-08", "by": "qa-agent", "follows": "qa/reports/2026-11-07-ged-master-mb1.json",
    "inputs": {"frames": ["assets/renders/master/editorial-2026-11-07/nordic/nordic-MB-A-fix1.png", "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A-fix1.png"],
               "record": "assets/renders/master/editorial-2026-11-07/mb1-fix.json"},
    "G-ED.8": {"nordic": {"changed_px": DF["nordic"]["changed_px_gt2"], "areas": [c["bbox"] for c in DF["nordic"]["components"]],
                          "verdict": "pass: every changed area is a declared one (the throw, the right sconce with the nightstand, the chair cloth and its fringe at the frame's left edge, the left sconce, the planter, the sill)"},
               "warm-modern": {"changed_px": DF["warm-modern"]["changed_px_gt2"], "areas": [c["bbox"] for c in DF["warm-modern"]["components"]],
                               "verdict": "pass: the left sconce with the nightstand, the right sconce"}},
    "G-ED.9": {"nordic": "pass, with two notes: the chair cloth's fringe tips at its lower right keep a warm pink-orange (the old colour in the feather; extend the mask 2 px); the left sconce's shadow is the original's, scaled, and reads plausible",
               "warm-modern": "fail: two leaf fragments of the old sprig float to the right of the new one (overlays/w-sprig-ghost-x4.jpg); code fix, 0 tokens"},
    "G-ED.6": {"nordic": f"pass, provisional: the chair cloth (sage-grey linen) now differs from our throw (dE76 {cc['dE76']}, L* {cc['dL']}, hue {cc['dh']:+} deg) and has a fringe where the throw has a plain hem. For the designer's final pick: not this sage, which is the colour family of our Nordic sage linen-look runner with its fringe",
               "warm-modern": "pass"},
    "scale": {
        "method": "Nordic: the headboard wall's board pitch (equal boards) on MB-A's clean boards, Theil-Sen fit of pitch against x (data/boards2.json): the px/cm at each object's x relative to QA's pillowcase basis (6.08 px/cm at x 2165) on the same wall. Warm modern: the pill niche's height at both ends (data/measure.json): equal, so the wall is frontal and the pillowcase basis (7.16 px/cm) holds at the nightstand. Objects stand about 20-30 cm in front of the wall: about 5-10 % larger again; tolerance +-15 %",
        "nordic": N, "warm_modern": W,
        "answer_a": "yes, a scale pass for each nightstand: Nordic, the bottle and holders read x1.4-1.6 even in the nightstand's own plane (x1.35-1.45 allowing for their depth), and the generic mug about 12 cm tall reads the same way; warm modern, the bottle x1.2 and the holders' bodies x1.15-1.25 too tall (H/W 1.84-2.0 against 1.57)",
        "answer_b": ("the input crop must already carry the right sizes: render-agent shrinks the objects in code about their base points to the targets (Nordic at about 7.3 px/cm on the table: bottle 24.5 cm = ~180 px, "
                     "holders 11 cm = ~80 px with cups ~51 px, candles 10 / 15 cm, the mug x0.8 so the still life stays coherent; warm modern at about 7.5 px/cm: bottle ~184 px, holders ~83 px tall on the same ~50 px cups, i.e. "
                     "shorter cones), fills the wall behind roughly (boards / plaster; streaks are fine), and the pass gets a mask over the old footprint plus the new objects, the two reference crops, and the prompt "
                     "'keep every object's size and place exactly as in the input; repair the wall behind; re-light'. The model is not asked to choose a size")},
    "frames": {
        "nordic-MB-A-fix1": dict(state="not_yet", rows=nordic, counts=cnt(nordic)),
        "warm-modern-MB-A-fix1": dict(state="not_yet", rows=wm, counts=cnt(wm)),
    },
    "this_week_2600": {
        "rule": "SPEND1, the week from Sunday 2026-11-08: up to 2,600, 650 at most each; in this order",
        "passes": [
            {"n": 1, "id": "P5", "frame": "nordic-MB-A-fix1", "what": "the bed head: plain envelope pillowcases (no flange), the lumbar at 50/74 of their width", "tokens": 650},
            {"n": 2, "id": "P7", "frame": "nordic-MB-A-fix1", "what": "the nightstand at scale: the input with the bottle, holders and mug already shrunk (answer_b)", "tokens": 650},
            {"n": 3, "id": "P6", "frame": "warm-modern-MB-A-fix1", "what": "the bed head: plain envelope pillowcases, the lumbar at 50/74 of their width, in milk tea above the natural linen", "tokens": 650},
            {"n": 4, "id": "P8", "frame": "warm-modern-MB-A-fix1", "what": "the nightstand at scale: the bottle x0.83, the holders' cones shortened to H/W 1.57 in the input; the sprig ghost gone", "tokens": 650},
        ],
        "total": 2600,
        "why_this_order": "Nordic first (more open products); in each frame the bed head first (two starring products on the hero bed), then the nightstand",
        "code_0_tokens_first": ["Nordic: both sconces rescaled from the originals (x0.80 right, x0.82 left); the chair cloth's fringe tips; its final colour once the designer picks", "warm modern: the two floating leaf fragments"],
    },
    "not_a_defect": "the two houses' tool shells differ in geometry: expected under ARC1 (owner, 2026-11-07: each style may change openings in the tool; the house switch is a cross-fade between different houses); not logged",
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-08-ged-master-fix1.json"), "w"), ensure_ascii=False, indent=1)
V8P = "qa/reports/ged-register-2026-11-07-r8.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V8P))))
reg.update(version=9, supersedes=V8P, id="ged-register-2026-11-08-r9", date="2026-11-08", by="qa-agent")
reg.pop("changes_from_v7", None)
for k, f in out["frames"].items():
    reg["master"][k] = dict(file=out["inputs"]["frames"][0 if k.startswith("nordic") else 1], state=f["state"], rows=f["rows"],
                            record="qa/reports/2026-11-08-ged-master-fix1.json", note="TEST frame (MB1 fix round 1), not for the site; the site does not read this section")
reg.setdefault("superseded_by", {})
reg["master_superseded_by"] = {"nordic-MB-A": "nordic-MB-A-fix1", "warm-modern-MB-A": "warm-modern-MB-A-fix1"}
reg["changes_from_v8"] = ["master: nordic-MB-A-fix1 and warm-modern-MB-A-fix1 added (MB1 fix round 1), both not_yet; the MB-A entries kept as they were, superseded (master_superseded_by)"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-08-r9.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = [f"{p}.{k}" for p in ("frames", "closeups", "master") for k, f in (reg.get(p) or {}).items()
       if f.get("state") not in S or any(not isinstance(r.get("card_id"), str) or r.get("dot") not in Dt or (r.get("units_in_frame") is not None and not 1 <= r["units_in_frame"] <= 12) for r in f.get("rows", []))]
print("v9 bad", bad)
for k, f in out["frames"].items():
    print(k, f["state"], f["counts"])
print(json.dumps(N), json.dumps(W))
