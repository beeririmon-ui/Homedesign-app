"""qa-agent 2026-11-07: G-ED on the master-bedroom base frames MB1 (assets/renders/master/editorial-2026-11-07/), from data/measure.json,
data/lumbar.json, data/guardrails-whole.json and QA's eye on overlays/*.jpg. Writes qa/reports/2026-11-07-ged-master-mb1.json and the
register v7 (qa/reports/ged-register-2026-11-07-r7.json: v6 plus a 'master' section, which the site does not read).
Usage: python3 -I build.py"""
import copy
import json
import os

REPO = "/home/user/homedesign-app"
D = os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1/data")
M = json.load(open(os.path.join(D, "measure.json")))
LU = json.load(open(os.path.join(D, "lumbar.json")))
GR = {os.path.basename(g["file"]).replace(".png", ""): g for g in json.load(open(os.path.join(D, "guardrails-whole.json")))}
fN, fW = M["frames"]["nordic-MB-A"], M["frames"]["warm-modern-MB-A"]
sN, sW = M["scale"]["nordic-MB-A"]["scale_vs_card"], M["scale"]["warm-modern-MB-A"]["scale_vs_card"]
rN, rW = M["scale"]["nordic-MB-A"]["ratio_vs_card"], M["scale"]["warm-modern-MB-A"]["ratio_vs_card"]
R = M["refs"]


def row(card, option, verdict, dot, why, fix=None, units=None, sale_unit=None):
    r = dict(card_id=card, option=option, verdict=verdict, dot=dot, note=why, card=card + (f" ({option if isinstance(option, str) else ', '.join(option.values())})" if option else ""),
             present=True, faithful=verdict, why=why)
    if fix:
        r["fix"] = fix
    if units:
        r["units_in_frame"], r["sale_unit"] = units, sale_unit
    return r


PASS = lambda name: f"targeted pass {name} (seedream-5-pro masked crop, ~650, SPEND1)"  # noqa: E731
CODE = "code, 0 tokens"
nordic = [
    row("bedding-cj-washed-linen-natural-set", {"color": "natural-linen"}, "yes", "yes",
        f"washed natural linen, rumpled, the sun's window stripes across it (the hero moment); duvet {fN['bedding: duvet'][:3]} against the white panelling {fN['neutral: white panelling (shade side)'][:3]} in the same warm morning light"),
    row("pillowcases-cj-pure-linen-envelope-pair-48x74", {"other": "a-pair-of-rain-and-dew-hemp"}, "partly", "no",
        "two, natural linen in the card's tone, but drawn with a flange (oxford) border all round; the product is a plain envelope (G-ED.2)",
        PASS("P5 'bed head' (with the lumbar)"), 1, "a pair in one SKU ('A Pair')"),
    row("cushions-cj-boucle-teddy", {"color": "white", "size": "30x50"}, "partly", "no",
        f"warm-white bouclé lumbar, lit face {LU['nordic-MB-A']['lumbar']} (white in the warm sun), but as wide as a 74 cm pillowcase: x{rN['lumbar / pillowcase width'][2]} against the card's 50/74 (G-ED.4)",
        PASS("P5 'bed head'")),
    row("throw-cj-cotton-linen-light-gray-200x230", None, "no", "no",
        f"a fuzzy plush taupe-grey blanket (Lab {fN['throw'][:3]}, h {fN['throw'][4]}) against the flat light-grey cotton-linen of the SKU photo (L* {R['throw light grey']['product'][0]}, h {R['throw light grey']['product'][4]}): material and tone wrong (G-ED.3)",
        PASS("P1 'foot of the bed'")),
    row("nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862", {"color": "D"}, "no", "no",
        f"a tall taupe bottle with a long neck, but a straight conical taper, not option D's bell; H/W {rN['bottle H/W'][0]} against {rN['bottle H/W'][1]} (x{rN['bottle H/W'][2]}); height x{sN['bottle height']} against the pillowcase (G-ED.2, G-ED.4)",
        PASS("P2 'nightstand' (with the candle holders)")),
    row("candle-holders-cj-travertine-pedestal", None, "no", "no",
        f"travertine, two, but a thin flat plate on a waisted cone instead of the thick cup; the tall one x{sN['candle holder (tall) height']} high against the card's 11 cm (x1.64 against the bottle), H/W {rN['candle holder (tall) H/W'][0]} against 1.57; two heights as in the listing photo, while the set is 2 x Small (G-ED.2, G-ED.4)",
        PASS("P2 'nightstand'"), 1, "a set of 2 (the site's pack)"),
    row("bedside-sconces-cj-linen-wave-flush", {"size": "beige-fabric"}, "partly", "no",
        f"three linen cylinders with rims, W/H {rN['sconce W/H'][0]} against 1.2, the lit linen as the photo; but x{sN['sconce (right) width']}-{sN['sconce (right) height']} against the pillowcase (about 35 cm wide against 24) (G-ED.4). Both lit; the brief has one, faintly (G-ED.13). No dot until CE is verified (designer's table)",
        "code, 0 tokens: scale both x0.68 on the panelling (the boards continue), dim the left one", 2, "single lamps (a pair is 2 units)"),
    row("curtains-aliexpress-linen-blend-s-fold-180502", {"style": "s-fold"}, "yes", "yes",
        "natural linen S-fold, two panels, a touch beige in the sun", None, 2, "single panels ('1PC')"),
    row("vase-aliexpress-vintage-distressed-clay-vase-589009", None, "no", "no",
        f"a round-shouldered ovoid, H/W {rN['sill vase H/W'][0]} against the line 1.85 (modern-country fix4 passed at 2.05; the photo is a slender tapered column with fine horizontal texture); the colour right ({fN['sill vase'][:3]}) (G-ED.2, G-ED.4)",
        PASS("P3 'sill'")),
    row("planter-zendrop-seagrass-belly-38x34", None, "partly", "no",
        f"a belly basket with two handles, but golden-brown (Lab {fN['planter'][:3]}, h {fN['planter'][4]}), the jute basket's colour beside it ({fN['jute basket'][:3]}), against the SKU photo's pale yellow-green seagrass (h {R['planter seagrass']['product'][4]}, about 17 L* lighter than jute) (G-ED.3); the same miss as boho fin6",
        "code, 0 tokens: recolour the basket as boho fin7 (hue toward 90, L* up about 15, the weave kept)"),
    row("basket-cj-jute-rope-cylinder", None, "yes", "yes",
        f"jute rope cylinder with loop handles (a little low), h {fN['jute basket'][4]} against the photo's {R['jute basket']['product'][4]}"),
]
wm = [
    row("bedding-cj-washed-linen-natural-set", {"color": "natural-linen"}, "yes", "yes",
        "washed natural linen, softly rumpled; the two cream pillows behind are the set's own pillowcases (duvet cover + flat sheet + pillowcases), not an extra product"),
    row("pillowcases-cj-pure-linen-envelope-pair-48x74", {"other": "caramel-pairs"}, "partly", "no",
        f"two, caramel in the card's tone (Lab {fW['pillowcase (caramel, left)'][:3]}, h {fW['pillowcase (caramel, left)'][4]} against the photo's h {R['pillow caramel']['product'][4]}), but with a flange border; the product is a plain envelope (G-ED.2)",
        PASS("P6 'bed head' (with the lumbar)"), 1, "a pair in one SKU ('Caramel Pairs')"),
    row("cushions-cj-boucle-teddy", {"color": "milk-tea-color", "size": "30x50"}, "partly", "no",
        f"bouclé lumbar, but it reads oatmeal: its lit face {LU['warm-modern-MB-A']['lumbar']} is {LU['warm-modern-MB-A']['lumbar_minus_duvet'][0]} L* and b* {LU['warm-modern-MB-A']['lumbar_minus_duvet'][2]:+} against the natural-linen duvet in the same light, while milk tea is a near-white cream well above natural linen (the SKU photo; register ed7); and x{rW['lumbar / pillowcase width'][2]} wide against the pillowcase (G-ED.3, G-ED.4)",
        PASS("P6 'bed head' (size and colour together)")),
    row("sofa-cover-cj-cotton-muslin-fringe", {"other": "pecan"}, "yes", "yes",
        f"pecan crinkled muslin with the short fringe, h {fW['throw (pecan)'][4]} against the photo's {R['throw pecan']['product'][4]}, folded across the foot"),
    row("wall-sconce-cj-travertine-cone-walnut", None, "partly", "no",
        f"travertine cone on a round walnut plate with the black arm, lit; x{sW['sconce cone rim width']} against the card's D15 (G-ED.4). CE to check before a dot (designer's table)",
        "code, 0 tokens: scale both x0.8 on the plaster", 2, "single lamps (a pair is 2 units)"),
    row("candle-holders-cj-travertine-pedestal", None, "partly", "no",
        f"travertine, cup on a cone (the shape), but stretched and big: the tall one x{sW['candle holder (tall) height']} and the short one x{sW['candle holder (short) height']} high against 11 cm, H/W {rW['candle holder (tall) H/W'][0]} against 1.57; two heights, while the set is 2 x Small (G-ED.2, G-ED.4)",
        PASS("P4 'nightstand' (with the bottle)"), 1, "a set of 2 (the site's pack)"),
    row("nightstand-vase-aliexpress-handmade-wabi-sabi-vase-665862", {"color": "D"}, "no", "no",
        f"a shouldered milk bottle with a short neck, not option D's bell with a long thin neck (G-ED.2); darker and more orange than the sand bottle (Lab {fW['bottle'][:3]}, h {fW['bottle'][4]} against the photo's h {R['bottle D']['product'][4]}); the height right (x{sW['bottle height']})",
        PASS("P4 'nightstand'")),
    row("floor-lamp-cj-pleated-walnut-stem-158", None, "yes", "yes",
        "walnut stem, brass base and details, cream pleated cone shade, pull chain, lit; shade width to height about 0.26 against the card's 37/158 = 0.23 (x1.12)"),
    row("planter-cj-cement-ribbed-belly", {"color": "beige", "size": "large"}, "yes", "yes",
        f"ribbed upper half and smooth lower band on the diagonal, as the photo; warm grey-beige in the amber light (Lab {fW['planter'][:3]} against the wall {fW['neutral: plaster wall by the bed'][:3]})"),
    row("curtains-aliexpress-beige-linen-sheer-curtains-554205", None, "yes", "yes", "sheer beige linen, two panels", None, 2, "single panels (the slot sells a pair = 2)"),
    row("sill-vase-cj-cream-fluted-column-25", None, "yes", "yes", "cream fluted column on a turned foot, as the photo"),
    row("basket-cj-jute-rope-cylinder", None, "yes", "yes", "jute rope cylinder with loop handles"),
]


def ged(frame, rows, extra):
    c = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("yes", "partly", "no")}
    g = GR[frame]
    return dict(rows=rows, counts=c, guardrails=dict(clipped_254_pct=g["clipped_254_pct"], shadows_10pct_Lab=g["shadows_10pct_Lab"], highlights_10pct_Lab=g["highlights_10pct_Lab"],
                                                      split_flag=g["split_flag"], shadow_floor_L_p1=g["shadow_floor_L_p1"]), **extra)


out = {
    "id": "2026-11-07-ged-master-mb1", "date": "2026-11-07", "by": "qa-agent",
    "inputs": {"frames": ["assets/renders/master/editorial-2026-11-07/nordic/nordic-MB-A.png", "assets/renders/master/editorial-2026-11-07/warm-modern/warm-modern-MB-A.png"],
               "raw_equals_final": True, "brief": "briefs/render-master-editorial-2026-11-07.md", "products": "docs/master-bedroom-comparison-2026-11-07.md §3",
               "refs": "render-agent's reference crops (scratchpad master-refs/, view only)", "render_agent_read": "jobs.json render_agent_read (compared, not taken over)"},
    "scale_basis": {k: M["scale"][k]["basis"] for k in M["scale"]},
    "frames": {
        "nordic-MB-A": ged("nordic-MB-A", nordic, dict(state="not_yet", checks={
            "G-ED.1": "pass: 11 of 11 products present",
            "G-ED.2": "fail: pillowcase flanges; candle-holder plate; the bottle without its bell; the sill vase an ovoid",
            "G-ED.3": "fail: the throw (plush taupe against flat light grey); the planter (jute brown against seagrass)",
            "G-ED.4": "fail: sconces x1.44-1.5, bottle x1.54, candle holders x2.5, lumbar x1.48 (against the 74 cm pillowcase); the sill vase H/W 1.63 against 1.85",
            "G-ED.5": "3 yes, 4 partly, 4 no: not_yet",
            "G-ED.6": "fail: the cloth over the generic chair is a fringed taupe linen throw (Lab 38.5 / 6.4 / 15.9), a second throw in our palette beside ours; the brief asked for a robe. Fix: code, 0 tokens, a clearly different colour (the designer picks), or the robe in P1",
            "G-ED.7": "pass",
            "G-ED.8": "n/a (no fix yet)", "G-ED.9": "n/a (no fix yet)",
            "G-ED.10": "QA's eye: no HDR halos; master-designer's verdict pending",
            "G-ED.11": "pass: no split (shadows b* 15.2, highlights 5.9); deepest shadow L* p1 10.9 (Nordic >= 8)",
            "G-ED.12": "pass: 0.05 % clipped (raw = final)",
            "G-ED.13": "master-designer; note: both sconces lit, the brief says one, faintly; the book and glasses are missing",
            "G-ED.14": "pass", "G-ED.15": "pass (no logo; the generic chair to the designer's eye)", "G-ED.16": "pass",
            "G-ED.17": "not yet (no point map)", "G-ED.18": "not yet (the room's other frames and close-ups)",
            "generic": "the chair: dark-stained ash with a natural linen seat, unlike the living-room armchair (MB-Q2); the white sheet at the head: generic white against our natural linen (distinct); the mug: dark stoneware (distinct)"})),
        "warm-modern-MB-A": ged("warm-modern-MB-A", wm, dict(state="not_yet", checks={
            "G-ED.1": "pass: 12 of 12 products present",
            "G-ED.2": "fail: pillowcase flanges; the bottle a milk bottle, not the bell; two candle-holder heights",
            "G-ED.3": "partly: the milk-tea lumbar reads oatmeal; the bottle darker and more orange",
            "G-ED.4": "fail: candle holders x2.2 / x1.6 high, lumbar x1.35, sconces x1.24",
            "G-ED.5": "7 yes, 4 partly, 1 no: not_yet",
            "G-ED.6": "pass: the cream back pillows are the bedding set's own pillowcases; the mug grey-green stoneware; the book, sandals, bed and nightstands generic and distinct",
            "G-ED.7": "pass",
            "G-ED.8": "n/a", "G-ED.9": "n/a",
            "G-ED.10": "QA's eye: no HDR halos; warm overall from the amber story; master-designer pending",
            "G-ED.11": "no split flag (shadows b* 15.0, highlights 19.8, one warm light); deepest shadow L* p1 6.4 (the Nordic floor does not apply; information)",
            "G-ED.12": "pass: 0.056 % clipped (raw = final)",
            "G-ED.13": "master-designer (the amber slice on the plaster and the cone reads)",
            "G-ED.14": "pass: the open book shows photographs, no text (overlays/wm-book-100.jpg)", "G-ED.15": "pass", "G-ED.16": "pass",
            "G-ED.17": "not yet", "G-ED.18": "not yet"})),
    },
    "fix_plan": {
        "rule": "SPEND1 (owner): QA-requested targeted passes up to 2,600 a week, 650 at most each, without asking",
        "this_week_2600": [
            {"id": "P1", "frame": "nordic-MB-A", "what": "the throw at the foot of the bed: flat light-grey cotton-linen (the SKU photo); optionally the chair cloth as a robe", "tokens": 650, "fixes": ["throw (no)"]},
            {"id": "P2", "frame": "nordic-MB-A", "what": "the nightstand: option D's bell bottle at 24.5 cm and the candle holders as the thick-cup Small pair (7 x 11, the same height)", "tokens": 650, "fixes": ["bottle (no)", "candle holders (no)"]},
            {"id": "P3", "frame": "nordic-MB-A", "what": "the sill: the clay vase as the slender tapered column (H/W >= 1.85)", "tokens": 650, "fixes": ["sill vase (no)"]},
            {"id": "P4", "frame": "warm-modern-MB-A", "what": "the nightstand: option D's bell bottle and the candle holders at 7 x 11, the same height", "tokens": 650, "fixes": ["bottle (no)", "candle holders (partly)"]},
        ],
        "next_week_1300": [
            {"id": "P5", "frame": "nordic-MB-A", "what": "the bed head: plain envelope pillowcases (no flange), the lumbar at 50/74 of their width", "tokens": 650},
            {"id": "P6", "frame": "warm-modern-MB-A", "what": "the bed head: plain envelope pillowcases, the lumbar at 50/74 of their width and in milk tea (near-white cream above the natural linen)", "tokens": 650},
        ],
        "code_0_tokens": [
            {"frame": "nordic-MB-A", "what": "sconces x0.68 and the left one dimmed; the planter recoloured to seagrass; the chair cloth recoloured (G-ED.6)"},
            {"frame": "warm-modern-MB-A", "what": "sconces x0.8"},
        ],
        "order": "the passes first, then the code fixes, then QA round 2 (G-ED.8 / G-ED.9 on every changed area), then the designer's eye (G-ED.10, G-ED.13)",
    },
    "open": ["the candle-holder set is 2 x Small (the same height); the listing photo shows two heights, and so do the living-room frames: sourcing and the designer confirm the set before the frames are asked for equal heights",
             "the scale basis is the 74 cm pillowcase in the headboard plane; the pillowcase itself is not checked against a third size (±10 %)"],
}
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-07-ged-master-mb1.json"), "w"), ensure_ascii=False, indent=1)
# ---- register v7
V6P = "qa/reports/ged-register-2026-11-07-r6.json"
reg = copy.deepcopy(json.load(open(os.path.join(REPO, V6P))))
reg.update(version=7, supersedes=V6P, id="ged-register-2026-11-07-r7", date="2026-11-07", by="qa-agent")
reg.pop("changes_from_v5", None)
reg["master"] = {k: dict(file=v, state=out["frames"][k]["state"], rows=out["frames"][k]["rows"], record="qa/reports/2026-11-07-ged-master-mb1.json",
                         note="TEST base frame (MB1), not for the site; the site does not read this section")
                 for k, v in (("nordic-MB-A", out["inputs"]["frames"][0]), ("warm-modern-MB-A", out["inputs"]["frames"][1]))}
reg["schema"]["master"] = "master.<qa_key>: the master bedroom's story frames (G-ED), the same shape as frames; kept apart until the room's story goes to the site"
reg["changes_from_v6"] = ["master: nordic-MB-A and warm-modern-MB-A (MB1), both not_yet (qa/reports/2026-11-07-ged-master-mb1.json)"]
json.dump(reg, open(os.path.join(REPO, "qa/reports/ged-register-2026-11-07-r7.json"), "w"), ensure_ascii=False, indent=1)
S, Dt = {"not_yet", "almost", "final_test", "approved_for_site"}, {"yes", "no", "closeup_only"}
bad = []
for part in ("frames", "closeups", "master"):
    for k, f in (reg.get(part) or {}).items():
        if f.get("state") not in S:
            bad.append(f"{part}.{k}.state")
        for i, r in enumerate(f.get("rows") or []):
            u = r.get("units_in_frame")
            if not isinstance(r.get("card_id"), str) or not isinstance(r.get("verdict"), str) or r.get("dot") not in Dt or (u is not None and not (isinstance(u, int) and 1 <= u <= 12)):
                bad.append(f"{part}.{k}.rows[{i}]")
print("v7 bad", bad)
for k, f in out["frames"].items():
    print(k, f["state"], f["counts"])
