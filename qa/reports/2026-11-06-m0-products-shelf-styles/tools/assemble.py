"""
qa-agent 2026-11-06: assembles qa/reports/2026-11-06-m0-products-shelf-styles.json (same record shape as before for the frames;
the shelf A/B as a size record; the style previews as reading notes, no pass / fail). Usage: python3.12 -I assemble.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-06-m0-products-shelf-styles")
D = lambda f: json.load(open(os.path.join(OUT, "data", f)))  # noqa: E731
LOCK = {k: D(f"lock-{k}.json") for k in ("M0_products_fix", "M0p_seedream_fix", "M0p_seedream_warp")}
PROD, LIGHT = D("products.json"), D("light-v6.json")
PREV = {f["frame"]: f for f in json.load(open(os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1.json")))["frames"]}
G14_4_T = ("register shift <= 9.6 px and scale within 0.5 %; residual after register <= 2.0 px per band / tile with shared structure for pan endpoints "
           "(M0 and M0p are the ends of P0); named lines within +-19 px (G1.4, proposal C3)")
G112_T = "0 seams, halos, fill artefacts at 100 % (Bible 'forbidden'; G1.12)"
LIGHT_T = "Bible 1.8.4 light and the grading chapter's fall-off: corner 90-94, centre 88-91, right edge 82-86, window wall 80-88, black 12-15, max <= 97, no 255"


def C(i, value, threshold, ok, binding=True):
    return dict(id=i, binding=binding, value=value, threshold=threshold, **{"pass": ok})


def lockv(k):
    L = LOCK[k]
    m = L["measure"]
    sc = m["register"]["scale"]
    return dict(register_shift_px=m["register"]["shift_px"], register_scale_pct=[round((sc[0] - 1) * 100, 2), round((sc[1] - 1) * 100, 2)],
                residual_gated=L["gated_residual"], tiles_registered=[[t.get("u"), t.get("v"), t.get("dx_px"), t.get("dy_px"), t.get("rho")] for t in m["tiles_ecc_registered"]],
                xcorr_box_ratios=m["summary"].get("xcorr_ratios"))


V9 = "assets/renders/living-room/nordic/v9/"
EX = PROD["changed_extents"]
lv6 = LIGHT["M0 products v6"]
products = {
    "magazine-holder (magazine-holder-cj-felt-log-basket, 45 x 32 x 40, dark grey felt #45474B, wood handles, cognac tabs)": dict(
        box=EX["magazine-holder"]["box_uv"], drawn_changed_extent=EX["magazine-holder"]["changed_extent_uv"], agent_grabcut=[0.281, 0.44, 0.856, 1.028],
        width_over_box=[1.85, 1.92], felt_L_median_graded=20.0, card_L=28.2,
        form="right: a charcoal felt tub with round wood handle bars and cognac leather tabs, newspapers inside",
        verdict="fail: about 1.85-1.9x its box's width (about 80 cm against the card's 45), its left edge (u 0.28-0.29) runs in front of the armchair's right "
                "front leg where the box keeps 0.020 clear; the felt reads L 20 (render-agent 22.6) against the card's 28: too dark", pass_=False),
    "basket (basket-cj-jute-rope-cylinder, 35 x 39 + handles)": dict(box=EX["basket"]["box_uv"], agent_grabcut=[0.343, 0.406, 0.681, 0.818],
        form="right: a jute rope cylinder with two loop handles, in the corner by the curtain stack; rope H 27, S 38, L 42", verdict="pass (in its box +-15 %; the handles above the box top by ~0.005)", pass_=True),
    "floor-lamp (floor-lamp-cj-black-drum-linen; test only, TR3 exception)": dict(box=EX["floor-lamp"]["box_uv"], agent_grabcut=[0.865, 0.975, 0.36, 0.92],
        form="right: a slim straight black pole on a round black disc base, a linen-look drum shade", shade_L=90.6, wall_left_L=82.5, wall_right_L=76.1,
        light_added_stops=dict((k.split(": ")[1], v) for k, v in PROD["lamp"].items() if k.startswith("light added")),
        verdict="shade and base within the box (the base ~0.013 lower); the glow is weak-to-moderate (shade +6..+8 over the wall left of it in QA's patches, +4.5 in "
                "render-agent's; +0.24 stop on the sofa's right end); its light on the wall is a G1.12 fail (below)", pass_=None),
    "pouf (pouf-cj-cotton-knit-ball-cover; test only)": dict(box=EX["pouf"]["box_uv"], agent_grabcut=[0.888, 0.998, 0.944, 1.028],
        form="right: a chunky cotton-knit ball, off-white (L 80, H 33, S 26)",
        verdict="fail (G1.3, proposal): its left edge at u ~0.86-0.89 against the box's 0.905 and its top at ~0.94 against 0.956: drawn larger and further left "
                "than the 45-48 x 36 envelope's projection", pass_=False),
    "table-runner (table-runner-cj-linen-look-sage-fringe, 33 x 183, tassel fringe at both ends)": dict(box=EX["table-runner"]["box_uv"], drawn_changed_extent=EX["table-runner"]["changed_extent_uv"],
        form="right now: a sage linen-look runner across the table's width in its left third, hanging over the front edge with a knotted fringe (11-05: a short cloth)",
        verdict="pass; the front drop (~25-30 cm by eye) is shorter than a 183 cm runner across a 70 cm table implies (~56 cm each side): a note, not a fail", pass_=True),
}
fr = []
fr.append(dict(frame="M0 products fix", kind="the products pass (seedream i2i, 650) laid in code over the locked seedream base (m0_products_pass.py), graded v6",
               fix_file=V9 + "m0-1-2-products-fix.png", graded=V9 + "m0-1-2-products-graded-fix-v6.png", frame_file=V9 + "m0-1-2-products-frame-fix-v6.png",
               criteria=[
    C("G1.4", dict(**lockv("M0_products_fix"), note="the shell and fixed furniture as the 11-05 base (shift 0.3 / 0.17 px, scale 0.00 / -0.01 %; sofa 0.999, table 0.995); "
                   "band 1 (u 0-0.25) reads 3.72 after register (1.48 unregistered): the new holder in front of the armchair; the 6.5 px tile is the curtain tile of 11-05"), G14_4_T, True),
    C("nothing else moved", dict(regions_mean_abs_delta=PROD["regions_mean_abs_delta"], outside=PROD["outside_product_zones"], outside_components=PROD["outside_changed_components_px_box"],
                                 note="walls, triptych, window, ceiling 0.00-0.02 levels; outside the product zones and the lamp's light zone 0.14 levels, p99 4; the changed "
                                      "components outside are the lamp's glow above the shade and the pouf / lamp light on the rug. The 'armchair' region's 2.5 is the holder "
                                      "in front of it, the 'rug left of the runner' the holder itself (QA's region choice). Confirmed: only the products moved"),
      "mean |delta| <= 2 levels outside the product boxes (+-15 %) and the runner area (the brief)", True),
    C("G1.1 / G1.3", products, "every product the card's SKU and inside its box +-15 % (G1.3 proposal)", False),
    C("G1.12", dict(violations=["the floor lamp's light on the wall: a bright trapezoid with hard straight edges behind the pole (a vertical edge right of the shade "
                                "from the shade down to the skirting, a horizontal edge and a cut corner by the shade's right; canvas ~x 2310-2595, y ~740-1310): "
                                "the light zone's boundary, visible at 100 % (overlays/g112-products-floor-lamp.jpg)"],
                    ok=["holder, basket, pouf, runner: no seam, halo or fringe of the lay at 100 % (overlays/g112-products-*.jpg)", "the old short runner gone, the oak under it clean"]),
      G112_T, False),
    C("G1.7-G1.9 (grading v6)", dict(fall_off={n: dict(L=v["L"], C=v["C"], ok=v["ok"]) for n, v in lv6["fall_off"].items()}, window_wall=lv6["window_wall"], black=lv6["black"],
                                     max_L=lv6["max_L"], px255=lv6["px255"], shape=lv6["shape"],
                                     note="the milky look of 11-05 is gone: the fall-off is in range at every Bible point (91.0 / 89.0 / 91.0 / 85.7), 35.7 % of the frame "
                                          "above L* 90 (was 68.7 %), local contrast 3.3 (was 1.3). render-agent's own v6 misses (glass margin 2.9 against 3, frame mean, the sofa's "
                                          "contact shadow, the cube washes, print 3's frame) are test-page numbers outside the Bible list QA checks; the v6 local fields are test-page "
                                          "grading only (B3)"), LIGHT_T, True),
    C("G1.14", "P0: the seedream M0p composite has none of the four products and the old short runner (overlays/g112-M0p-warp-max-100.jpg); it needs the same lay before P0 can be read", "pan pair <= 2 px, the same objects", False),
],
               verdict="fail", failed_in_the_frame=["G1.1 / G1.3 (the holder ~1.9x and too dark; the pouf off its box)", "G1.12 (the lamp light's hard edges)"],
               may_reference="yes for the shell, the furniture, the basket, the runner and the light (v6); not for the holder, the pouf or the lamp's light",
               may_pan_endpoint="not yet: P0 needs the M0p with the same products; the holder and the lamp light first",
               products_unverified=PREV["M0 seedream fix"]["products_unverified"] + ["magazine-holder-cj-felt-log-basket", "basket-cj-jute-rope-cylinder", "floor-lamp-cj-black-drum-linen", "pouf-cj-cotton-knit-ball-cover"]))
wl = LOCK["M0p_seedream_warp"]
fr.append(dict(frame="M0p seedream warp", kind="a local warp in code (m0p_warp.py, dx -8.4..+7.0 px) of the seedream M0p composite", fix_file=V9 + "pose-m0p-1-2-shell-seedream-fix-warp.png",
               graded=None, criteria=[
    C("G1.4", dict(**lockv("M0p_seedream_warp"), before_warp=lockv("M0p_seedream_fix"),
                   named_lines_1080="floor line 870 vs clay 871; cornice 74 / 108 vs 75 / 104 (+4 at x 600); back-right corner 1357-1360 vs 1362 (-2..-5); the left corner / jamb 42-45 vs 37-38 (+5..+7); "
                                    "sofa left arm 307 vs 305",
                   note="agrees with render-agent: bands <= 1.68 (was 6.78), tiles 5.5 and 4.63 over 2 px: tile u 0.5-0.75, v 0-0.5 (rho 0.75: the back-right corner) and u 0.75-1.0, v 0.5-1.0 "
                        "(rho 0.93: the right wall's skirting and floor): the right wall is drawn in a slightly different perspective; render-agent's next step (a homography for "
                        "the right wall) is the right one"), G14_4_T, False),
    C("G1.12", "no bend or seam where the warp moved most (the table and the runner, u ~0.29, v ~0.84; overlays/g112-M0p-warp-max-100.jpg)", G112_T, True),
], verdict="fail", failed_in_the_frame=["G1.4 (tiles 5.5 / 4.6 px on the corner and the right wall)"], may_reference="no", may_pan_endpoint="no: the right wall, then the products lay", products_unverified=[]))
shelf = dict(frame="M0 shelf A/B (B)", kind="SHF1 (a): the shelf pass (seedream i2i, 650) laid in code in the shelf zone of the graded v6 frame",
             file="assets/renders/living-room/nordic/v9/m0-1-2-products-shelf-graded-fix-v6.png", sheet="assets/renders/house-nordic-m0-shelf-ab-sheet-2026-11-06.jpg",
             spec="docs/proposals/living-room-shelf-2026-11-06.md: floating oak shelf 55 x 18, 3 thick, top at 1.00, X -1.65..-1.10 on the back wall; black matte jar 30 (30 x 15), cream fluted column, travertine tray with the reed diffuser",
             sizes=dict(how="QA's eye on 100 % crops with the position map's boxes (m0-shelf-ab-ref-clay.json) drawn on the clay and on B (overlays/shelf-*-boxes-100.jpg)",
                        shelf=dict(box_px_w=194, drawn_px_w=385, ratio=1.98, thickness="front face ~25 px against the box's ~14 (2-3x)", agent="x1.89 (~105 cm), ~9 cm thick"),
                        jar=dict(box_px_wh=[49, 100], drawn_px_wh=[90, 140], ratio=[1.84, 1.4], agent="~40 x 30 against 30 x 15"),
                        column=dict(ratio_height="~1.07", width="~1.5", position="~30 px right of its box"),
                        tray=dict(ratio_width=1.14, position="~80 px right of its box", material="reads as white marble with grey veins, not travertine (pool-cj-travertine-organic-tray-24)"),
                        diffuser=dict(vessel="~1.6x the box's width, on the tray, bamboo lid", agent_vessel_height=1.7),
                        group="the whole group spreads ~1.9x wider than planned, its right end under the right sconce ~40 px from the triptych"),
             outside_zone="identical to A outside the shelf zone: the changed pixels lie in canvas u 0.399-0.556, v 0.376-0.584 (render-agent: 0.003)",
             light="the laid zone was not re-graded: 1045 pixels at 255 (canvas u 0.426-0.527, v 0.385-0.542) and the black point 7.0 (the jar; Bible 12-15)",
             verdict="fail for sizes and for the grade of the laid zone; readable as a look only: what the owner sees is a shelf about twice as long and a jar about twice as wide as proposed",
             pass_=False)
styles_notes = {}
REP = json.load(open(os.path.join(REPO, "assets/renders/living-room/style-previews-2026-11-06/report.json")))["styles"]
for k, v in REP.items():
    styles_notes[k] = dict(shell_max_px=v["shell"]["raw_max_px"], vanishing_point=v["shell"]["vanishing_point"], lock_v2=v["lock_v2"]["verdict"], reference_cards=v.get("reference_cards"),
                           agent_visual_notes=v.get("visual_notes"))
out = dict(report="qa/reports/2026-11-06-m0-products-shelf-styles.md", by="qa-agent", date="2026-11-06",
           gate="G1 on the Nordic M0 products pass (M0S2), the M0p warp and the shelf A/B (SHF1 a); a reading of the five style previews (STY1 / STY2, test only, no pass / fail)",
           brief="the coordinator's task of 2026-11-06 (no brief file): board line 2026-11-06 'render-agent (מעבר המוצרים, חמש הדמיות סגנון, A/B מדף)'",
           tools="qa/reports/2026-11-06-m0-products-shelf-styles/tools/*.py (QA; the 11-03 .. 11-05 tools imported, not edited); eye at 100-200 %",
           inputs_sha256_16={"m0-1-2-products-fix.png": "812571b659d881c2", "m0-1-2-products-frame-fix-v6.png": "2598873b43d37d25", "m0-1-2-products-graded-fix-v6.png": "5760fcf2462a9bf2",
                             "m0-1-2-products-fix.json": "e020bb4051396e68", "m0-1-2-products-measurements-fix-v6.json": "a5e7a2909b4474fe", "pose-m0p-1-2-shell-seedream-fix-warp.png": "8ab53aaabb9c7a53",
                             "m0-1-2-products-shelf-graded-fix-v6.png": "661486569a75ca14", "m0-shelf-ab-pass.json": "05916cae1c00a74a", "m0-shelf-ab-ref-clay.json": "c83c7cab3efcd67a",
                             "house-nordic-m0-shelf-ab-sheet-2026-11-06.jpg": "f741fdb59468e5ca", "contact-sheet.png": "00085399c9e85ea1", "report.json": "57ad9bcb2633f048"},
           frames=fr, shelf_ab=shelf, style_previews=styles_notes, products_data=PROD, light_v6=LIGHT)
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-06-m0-products-shelf-styles.json"), "w"), indent=1, ensure_ascii=False)
print([(f["frame"], f["verdict"]) for f in fr], shelf["pass_"])
