"""
qa-agent 2026-11-04 (second round): assembles qa/reports/2026-11-04-m0-fix2-cb0-g1.json from data/*.json and the eye verdicts
(G1.12 at 100 / 200 %: overlays/g112-*.jpg). Same record shape as 11-03 / 11-04: per frame criteria[] (id, value, threshold, pass,
binding), verdict, may_reference, may_pan_endpoint, products_unverified[]. Usage: python3.12 -I assemble.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1")
D = lambda f: json.load(open(os.path.join(OUT, "data", f)))  # noqa: E731
LOCK = {k: D(f"lock-{k}.json") for k in ("M0_1.2_fix", "M0_1.2_r2", "M0p_1.2_fix", "M0x_1.2_fix", "B1_r3_fix2", "B2_r3_fix2", "K-girl-0_r2_fix2", "W0-in_r2_fix2", "CB-0_b1r3")}
SHELL = D("m0-shell.json")
LIGHT = D("light-v5.json")
PAIRS = D("pairs.json")
SEAM = D("cb0-seam.json")
PREV = json.load(open(os.path.join(REPO, "qa/reports/2026-11-04-retakes-fixes-g1.json")))
V7 = {(f.get("frame") or f.get("id")): f for f in json.load(open(os.path.join(REPO, "qa/reports/2026-11-02-v7-g1.json")))["frames"] if isinstance(f, dict)}
PU = {f["frame"]: f for f in PREV["frames"]}
G14_T = "pan_reproject.check in the overlap: <= 2 px per band with response >= 0.05 and dL <= 1 (gates doc 7.1, proposal; the principle binding)"
G14_4_T = ("register shift <= 9.6 px and scale within 0.5 %; residual after register <= 2.0 px per band / tile with shared structure (response >= 0.10, "
           "rho >= 0.30) for pan endpoints, <= 9.6 px for video endpoints; named lines within +-19 px (G1.4, proposal C3)")
G112_T = "0 seams, halos, fill artefacts at 100 % (Bible 'forbidden'; G1.12)"
LIGHT_T = ("Bible 1.8.4: the reference wall in range (living 90-94, bath 86-90 HSL L; corridor L* 72-75 at the BIB2 points), H 32-40, C* <= 7 (B4), "
           "window wall 80-88, black 12-15, max <= 97 and no 255; hall walls L* 75-78; the corridor-end vista the brightest")


def lrow(rid, fix):
    return next(r for r in LIGHT["rows"] if r["id"] == rid and (r["fix"] or None) == fix)


def pair(a, b):
    p = next(x for x in PAIRS if x["a"] == a and x["b"] == b)
    return dict(pan=p["pan"], degrees=p["degrees"], bands=[[round(x["dx_px"], 2), round(x["dy_px"], 2), x["response"]] for x in p["render"]["bands"]],
                worst_reliable_px=p["render"]["worst_band_px_reliable"], dL=p["render"]["dL_mean"], dE_mean=p["render"]["deltaE"]["mean"],
                clay_floor_px=p["clay"]["worst_band_px_reliable"])


def lockv(k):
    L = LOCK[k]
    m = L["measure"]
    sc = m["register"]["scale"]
    return dict(register_shift_px=m["register"]["shift_px"], register_scale_pct=[round((sc[0] - 1) * 100, 2), round((sc[1] - 1) * 100, 2)],
                residual_gated=L["gated_residual"], masked_register=L["masked_register"], named_lines_px={n: v.get("d_nearest_peak") for n, v in L["named"].items()} or None)


def rec(frame, kind, fix_file, graded, criteria, verdict, may_ref, may_pan, products, live=()):
    fb = [c["id"] for c in criteria if c["binding"] and c["pass"] is False]
    return dict(frame=frame, kind=kind, fix_file=fix_file, graded=graded, criteria=criteria, verdict=verdict, failed_binding=fb,
                failed_proposal=[c["id"] for c in criteria if not c["binding"] and c["pass"] is False],
                cannot_measure=["G1.2", "G1.5", "G1.11", "G1.15", "G1.16"], may_reference=may_ref, may_pan_endpoint=may_pan,
                products_unverified=list(products), products_live=list(live))


def C(i, value, threshold, ok, binding=True):
    return dict(id=i, binding=binding, value=value, threshold=threshold, **{"pass": ok})


R = "assets/renders/"
frames = []
# ---------------------------------------------------------------- M0 1.2 fix
m0 = lrow("m0-v8b-r2", "fix")
frames.append(rec("M0 1.2 fix", "code composite 2026-11-04 (fix_m0_12.py) on the paid reserve render m0-v8b-r2", R + "living-room/nordic/v8/m0-v8b-r2-fix.png",
                  R + "living-room/nordic/v8/m0-v8b-r2-graded-fix-v5.png", [
    C("G1.4", dict(**lockv("M0_1.2_fix"), raw_before=lockv("M0_1.2_r2"), shell=dict(
        offsets_px_1080=SHELL["offsets_px"], slopes=SHELL["slopes"], back_wall_vanishing_point_px=SHELL["back_wall_vanishing_point"],
        homography_all_planes_residual_px=SHELL["homography_all_planes"]["residual_px"],
        homography_back_wall_residual_px=SHELL["homography_back_wall"]["residual_px"],
        back_wall_homography_on_the_window_wall_px=SHELL["homography_back_wall"]["applied_to_window_wall"],
        affine_all_planes_max_residual_px=SHELL["affine_all_planes"]["residual_px_max"],
        verdict="confirmed: the room shell is drawn in another perspective (not a shift or scale): back-wall floor line -16 -> -46 px, skirting -10 -> -36, "
                "cornice -16 -> -5 (the opposite trend), sill -28..-31, corner +5 (1920 frame; x 1.425 on the canvas = render-agent's 20-66 / ~45). "
                "The back-wall vanishing point moved from x -1844 to -2421. One homography for all planes leaves 5-18 px; the back wall's own homography "
                "fits to 2-10 px but misses the window wall by 27-32 px: the planes need different homographies = parallax = a different camera position. "
                "A per-region warp cannot reach the 2 px of a pan endpoint (P0) at the plane joints, tears the window / curtains / pendant at the plane "
                "borders and re-cuts the furniture just composited: not realistic. Only a new render fixes M0's shell.")),
      G14_4_T, False),
    C("G1.3", dict(by_cross_correlation=dict(sofa_width=1.051, sofa_left_edge_px=-41, table_width=0.939, table_right_edge_px=-31),
                   note="the furniture edges the code moved; not decisive while the shell is off (proposal)"), "fixed edges +-19 px, width 0.95-1.05 (proposal)", None, False),
    C("G1.1", "not judged this round: the products are those of the paid render m0-v8b-r2 (sofa / table groups scaled uniformly with their decor); "
              "the card check waits for the frame that passes G1.4", "every product the card's SKU", None),
    C("G1.12", dict(violations=["right strip (fill copied 114 px): the skirting's top profile breaks at canvas x ~2435 and ~2545 (y ~1190); "
                                "rectangular plank blocks on the floor (x ~2425-2500, y ~1260-1335); the rug's border stair-stepped (x ~2435-2590, y ~1330-1350)",
                                "soft fill patches in the floor and rug around the old sofa / table footprint (render-agent reports them too)"],
                    overlays=["overlays/g112-M0-right-strip-200.jpg", "overlays/g112-M0-floor-rug.jpg", "overlays/g112-M0-sofa-wall.jpg"]), G112_T, False),
    C("G1.7-G1.9 (grading v5)", dict(back_wall=m0["bible_points"]["back wall by the corner (0.427,0.416)"], window_wall_bible_point=m0["bible_points"]["window wall (0.352,0.415)"],
                                     window_wall_note="the Bible point (0.352, 0.415) lands on the curtain's edge in this render (the shell is off); on the bare strip "
                                                      "u 0.364-0.368: L 84.1-86.3, in 80-88", black=m0["black"], max_L=m0["max_L"], px255=m0["px255"],
                                     fails=["C* 7.78 > 7 (B4) at the back-wall point"]), LIGHT_T, False),
    C("G1.14", dict(P0=pair("M0 1.2 fix", "M0p 1.2 fix")), G14_T, False),
], "fail", "no: the shell is in another perspective (G1.4); fill artefacts on the right (G1.12); C* 7.8 (B4)",
    "no: P0 22.5 px, dL 4.0 against M0p 1.2 fix; T-E0 ends on M0", V7["M0"]["products_unverified"] if "M0" in V7 else [], ["basket-zendrop-seagrass-belly-38x34"]))
# ---------------------------------------------------------------- M0p 1.2 fix
m0p = lrow("pose-m0p-v8b", "fix")
frames.append(rec("M0p 1.2 fix", "code composite 2026-11-04 on pose-m0p-v8b", R + "poses/nordic/v8/pose-m0p-v8b-fix.png", R + "poses/nordic/v8/pose-m0p-v8b-graded-fix-v5.png", [
    C("G1.4", dict(**lockv("M0p_1.2_fix"), shell="shell lines off by a uniform vertical error (floor line -14/-15, skirting -7/-8, cornice -4, corner 0, side wall "
                                                   "-10..-19 px): about -1.3 % vertical, the same at every column: one vertical affine of the raw (0 tokens) before the "
                                                   "furniture is re-composited is realistic here (unlike M0)"), G14_4_T, False),
    C("G1.3", dict(sofa_width_by_edges=1.0015, sofa_width_by_xcorr=1.125, table_width_by_xcorr=1.049), "fixed edges +-19 px, width 0.95-1.05 (proposal)", None, False),
    C("G1.1", dict(deviations=["the bowl on the table reads as two nested rims: the old bowl's rim stays visible behind the scaled one (bowl-cj-glutinous-white-belly-bowl-21: "
                               "one bowl)"], overlay="overlays/g112-M0p-bowl-200.jpg"), "every product the card's SKU: silhouette, count", False),
    C("G1.12", dict(violations=["the doubled bowl rim (canvas ~x 1100-1300, y ~1190-1260)",
                                "right of the sofa's right leg: rectangular blocks on the rug border and a vertical seam through the floor and the rug (canvas ~x 1500-1650, y ~1180-1300)"],
                    overlays=["overlays/g112-M0p-bowl-200.jpg", "overlays/g112-M0p-floor-right-leg-200.jpg", "overlays/g112-M0p-sofa.jpg"]), G112_T, False),
    C("G1.7-G1.9 (grading v5)", dict(reference=m0p["ref"], black=m0p["black"], max_L=m0p["max_L"], px255=m0p["px255"]), LIGHT_T, True),
    C("G1.14", dict(P0=pair("M0 1.2 fix", "M0p 1.2 fix"), P1=pair("M0p 1.2 fix", "M0x 1.2 fix")), G14_T, False),
], "fail", "no: shell -1.3 % vertical (G1.4), the doubled bowl (G1.1 / G1.12), rug / floor blocks", "no: P0 22.5 px, P1 36.4 px",
    V7["M0p"]["products_unverified"] if "M0p" in V7 else [], ["basket-zendrop-seagrass-belly-38x34"]))
# ---------------------------------------------------------------- M0x 1.2 fix
m0x = lrow("pose-m0x-v8b", "fix")
frames.append(rec("M0x 1.2 fix", "one vertical affine 2026-11-04 on pose-m0x-v8b", R + "poses/nordic/v8/pose-m0x-v8b-fix.png", R + "poses/nordic/v8/pose-m0x-v8b-graded-fix-v5.png", [
    C("G1.4", dict(**lockv("M0x_1.2_fix"), shell="cornice / ceiling lines within +-5 px after the vertical affine; fails the pan rule: bands 2.17 / 2.08 and tiles up to 17.1 px "
                                                   "(u 0-0.25, v 0-0.5, rho 0.70)"), G14_4_T, False),
    C("G1.3", "door leaves 0.944 (render-agent's lock; proposal 0.95-1.05)", "width / height 0.95-1.05 (proposal)", False, False),
    C("G1.12", "no local edit (one global affine); by eye clean at 100 % (overlays/g112-M0x-door.jpg)", G112_T, True),
    C("G1.7-G1.9 (grading v5)", dict(reference=m0x["ref"], note="not judgeable: the agent's point (0.5, 0.3) is window glare (L 96.5, H 0); inherits M0 1.2 fix's stops (0.907)"), LIGHT_T, None),
    C("G1.14", dict(P1=pair("M0p 1.2 fix", "M0x 1.2 fix")), G14_T, False),
], "fail", "no: residual over 2 px (pan endpoint) and P1 36.4 px", "no: P1 36.4 px, dL 7.8",
    V7["M0x"]["products_unverified"] if "M0x" in V7 else [], ["basket-zendrop-seagrass-belly-38x34"]))
# ---------------------------------------------------------------- B1 r3 fix2
b1 = lrow("b1-v7-r3", "fix2")
frames.append(rec("B1 r3 fix2", "code cleanup 2026-11-04 (fix_v9.py)", R + "bath/nordic/v7/b1-v7-r3-fix2.png", R + "bath/nordic/v7/b1-v7-r3-graded-fix2-v5.png", [
    C("G1.4", lockv("B1_r3_fix2"), G14_4_T, True),
    C("G1.1", dict(ok=["toilet brush: holder 88 of 231 px = 38 % of the height (card: 14.5 cm holder, 38 %), height 1.00 of its box; the silhouette now the card's",
                       "the seagrass basket on the floor (unchanged since fix)"]), "every product the card's SKU", True),
    C("G1.12", dict(violations=["two pale rectangular lumps with hard edges on the linen right of the fern (canvas ~x 1570-1605, y ~1050-1185): visible at 100 %",
                                "the refilled linen above the fern keeps horizontal steps across the folds (x ~1500-1600 at y ~690, ~830, ~940) and the curtain's left "
                                "edge is a straight synthetic diagonal (x 1455 -> 1521 over y 615 -> 1292): visible at 200 %, soft at 100 %"],
                    better="the big light / dark blocks of fix (11-04) are gone", overlays=["overlays/g112-B1-lumps-200.jpg", "overlays/g112-B1-curtain-left-200.jpg", "overlays/g112-B1-fern-curtain.jpg"]),
      G112_T, False),
    C("G1.7-G1.9 (grading v5)", dict(reference=b1["ref"], black=b1["black"], max_L=b1["max_L"], px255=b1["px255"]), LIGHT_T, True),
    C("G1.14", dict(P_B=pair("B1 r3 fix2", "B2 r3 fix2"), T_CBath=pair("B1 r3 fix2", "CB-0 b1r3")), G14_T, False),
    PU["B1 r3 fix"]["criteria"][[c["id"] for c in PU["B1 r3 fix"]["criteria"]].index("G1.6")],
    PU["B1 r3 fix"]["criteria"][[c["id"] for c in PU["B1 r3 fix"]["criteria"]].index("G8.6")],
], "fail", "yes for geometry and grading (G1.4 in full: named lines 0 / +-1, residual <= 1.63 px; v5 89.2 / H 35.9 / C* 5.4); as an image after the two lumps right of the fern",
    "T-CBath: yes for geometry (CB-0 is built from it, 0.06 px); the lumps travel into CB-0 and must go first. P-B: no (9.0 px against B2 r3 fix2)",
    PU["B1 r3 fix"]["products_unverified"]))
# ---------------------------------------------------------------- B2 r3 fix2
b2 = lrow("b2-v7-r3", "fix2")
frames.append(rec("B2 r3 fix2", "global affine + cleanup 2026-11-04 (fix_v9.py)", R + "bath/nordic/v7/b2-v7-r3-fix2.png", R + "bath/nordic/v7/b2-v7-r3-graded-fix2-v5.png", [
    C("G1.4", dict(**lockv("B2_r3_fix2"), note="global fixed (scale 0.00 / +0.01 %); a local vertical offset stays: vanity top / mirror bottom / niche top -7 / -8 / -7 px; tile 2.69 px (u 0.5-0.75, v 0-0.5, rho 0.50)"),
      G14_4_T, False),
    C("G1.1", dict(ok=["planter: basket 1.00 of the clay pot's height (x0.85, unchanged since fix)", "storage basket within +-15 % (11-04), unchanged"]), "every product the card's SKU", True),
    C("G1.12", dict(violations=["the limestone panel behind the fern refilled pale: a block with a horizontal top edge at y ~870 and a vertical edge at x ~440 (canvas x ~273-443, y ~870-1340)",
                                "a white strip with a hard edge left of the fronds (x ~0-50, y ~780-1150)",
                                "floor right of the basket: a grey smeared patch with stepped edges at the curtain's foot and the panel's base (x ~300-450, y ~1250-1400)",
                                "the basket's right outline stair-stepped at 200 %"],
                    overlays=["overlays/g112-B2-planter-floor.jpg", "overlays/g112-B2-floor-right-of-basket.jpg", "overlays/g112-B2-wall-panel.jpg"]), G112_T, False),
    C("G1.7-G1.9 (grading v5)", dict(reference=b2["ref"], fails=["C* 9.30 > 7 (B4)", "L 82.1 under 86-90 at the inherited point (the agent judges it by B1's stops)"]), LIGHT_T, False),
    C("G1.14", dict(P_B=pair("B1 r3 fix2", "B2 r3 fix2")), G14_T, False),
    PU["B2 r3 fix"]["criteria"][[c["id"] for c in PU["B2 r3 fix"]["criteria"]].index("G1.6")],
    PU["B2 r3 fix"]["criteria"][[c["id"] for c in PU["B2 r3 fix"]["criteria"]].index("G8.6")],
], "fail", "no: fill artefacts round the planter (G1.12), C* 9.3 (B4), vanity line -7/-8 px", "no: P-B 9.0 px (was 14.2)", PU["B2 r3 fix"]["products_unverified"]))
# ---------------------------------------------------------------- K-girl-0 r2 fix2
kg = lrow("pose-k-girl-0-v7-r2", "fix2")
kl = LOCK["K-girl-0_r2_fix2"]
frames.append(rec("K-girl-0 r2 fix2", "one vertical affine 2026-11-04 (fix_v9.py)", R + "poses/nordic/v7/pose-k-girl-0-v7-r2-fix2.png", R + "poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix2-v5.png", [
    C("G1.4", dict(**lockv("K-girl-0_r2_fix2"), register_by_region=kl.get("by_region") or kl.get("register_by_region"),
                   register_question="the register is not identifiable here, so +0.89 % is not a stretch: plain ECC +0.89 % (y), masked +0.13 %, and three regions give "
                                     "-1.59 .. +1.57 % and shifts to 27 px (the frame is plain wall and floor). The named lines settle it: the six horizontal lines are "
                                     "0 / +-1 (render-agent +-0.6): the vertical stretch is fixed",
                   still_off="x was not touched: the vertical lines of the left quarter are -4 .. -8 px (clay 69/73/80 -> 64/69/75 and 211 -> 203 at row 300; "
                             "437/446 -> 434/443 at row 700), the corner +2, the bed foot -3; unregistered residual 5.3 px (tile u 0-0.25, v 0-0.5, rho 0.90), band 4.7",
                   unregistered_tiles=[[t.get("dx_px"), t.get("dy_px"), t.get("rho")] for t in kl["measure"]["tiles_ecc"]]), G14_4_T, False),
    C("G1.1", "prints 0.98 x 1.00 and the doll as on 11-04 (only the 0.84 % vertical affine since)", "every product the card's SKU", True),
    C("G1.12", "no new edit besides the affine; the replicated border rows lie in the overscan margin; by eye clean (overlays/g112-K-girl-0-*.jpg)", G112_T, True),
    C("G1.7-G1.9 (grading v5)", dict(reference=kg["ref"]), LIGHT_T, True),
    C("G1.14", dict(T_CGirl=pair("K-girl fix", "K-girl-0 r2 fix2")), G14_T, False),
    PU["K-girl-0 r2 fix"]["criteria"][[c["id"] for c in PU["K-girl-0 r2 fix"]["criteria"]].index("G8.6")],
], "fail", "yes for the vertical geometry (named lines 0 / +-1); a horizontal fix of the left quarter (about -5 px, 0 tokens) first for a pan",
    "no: T-CGirl 30.8 px (the K-girl master) and the left quarter -4..-8 px", PU["K-girl-0 r2 fix"]["products_unverified"]))
# ---------------------------------------------------------------- W0-in r2 fix2
w0 = lrow("pose-w0-in-v7-r2", "fix2")
frames.append(rec("W0-in r2 fix2", "basket cleanup 2026-11-04 (fix_v9.py)", R + "poses/nordic/v7/pose-w0-in-v7-r2-fix2.png", R + "poses/nordic/v7/pose-w0-in-v7-r2-graded-fix2-v5.png", [
    C("G1.4", dict(**lockv("W0-in_r2_fix2"), note="video endpoint: residual 8.8 <= 9.6. Named lines by peak lists: desk top -3, face bottom -2, drawer -2/-3, chair top -3 "
                                                  "(the +32 cross-correlation is a mis-pair), desk left -2, chair 0 / -8, shelf front 0/+1 (the +36 is a mis-pair: peaks 151 / 151-152), shelf bottom -5..-7"),
      G14_4_T, True),
    C("G1.1", "pencil cup as on 11-04 (8.8 x 11 cm, the card); the desk: see G1.12", "every product the card's SKU", True),
    C("G1.12", dict(violations=["NEW in fix2: the desk's front-left corner is broken: the drawer front's left end is copied into the leg (three extra vertical edges at x 351 / 361 / 384 "
                                "of 1920 at row 780, where the clay and fix have one edge at 318-319) and the slab's mitred corner became a square notch (canvas ~x 430-560, y ~1080-1330)",
                                "beside the basket's base a smaller darker floor block with a straight top edge remains (canvas ~x 400-450, y ~1465-1539)"],
                    fixed="the green / dark blocks in the basket's weave are gone", overlays=["overlays/g112-W0-in-desk-corner.jpg", "overlays/g112-W0-in-desk-corner-raw-clay.jpg",
                                                                                            "overlays/g112-W0-in-basket.jpg", "overlays/g112-W0-in-basket-base-200.jpg"]), G112_T, False),
    C("G1.7-G1.9 (grading v5)", dict(reference=w0["ref"]), LIGHT_T, True),
    C("G1.14", "dolly W0 fix -> W0-in r2 fix2: same objects by eye (overlays/endpoints-W0_fix-W0-in_r2_fix2.jpg); no pan rule", G14_T, None),
    PU["W0-in r2 fix"]["criteria"][[c["id"] for c in PU["W0-in r2 fix"]["criteria"]].index("G8.6")],
], "fail", "yes for geometry (video endpoint); as an image after the desk corner is restored (take it from W0-in r2 fix, 0 tokens)",
    "V4 / T-HW after the desk corner (the basket is clean now)", PU["W0-in r2 fix"]["products_unverified"], PU["W0-in r2 fix"]["products_live"]))
# ---------------------------------------------------------------- CB-0 b1r3
cb = LIGHT["cb0_b1r3"]
frames.append(rec("CB-0 b1r3", "recomposed 2026-11-04 from B1 r3 fix2 by a 22 deg reprojection (recompose_cb0.py)", R + "poses/nordic/v7/pose-cb-0-v7-b1r3.png",
                  R + "poses/nordic/v7/pose-cb-0-v7-graded-b1r3-v5.png", [
    C("G1.4", dict(**lockv("CB-0_b1r3"), named_lines_px_1080="on the round-4 CB-0 clay (no r3 clay of CB-0): window sides 822/832/862 = clay, WC block 729/750 and 1241 = clay "
                   "(+-1), block top 575/581 = clay, ledge 643/685 = clay, left jamb 89 vs 90, skirting -4..0",
                   note="the ECC register (+3.66 / -7.37 px, a 0.5 % shear) and the tiles <= 3.73 px are biased by the plain walls; the named lines are exact. "
                        "As the slide's end (video) it passes; as the pan's start the pair check is the binding one (G1.14)"), G14_4_T, True),
    C("G1.14", dict(T_CBath=pair("B1 r3 fix2", "CB-0 b1r3"), agent="0.06 px, dL 0.8: confirmed"), G14_T, True),
    C("G1.12", dict(violations=["the old CB-0 is not only u < 0.30: two wedges B1's canvas does not reach are old pixels too: the top (frame rows 44-160, from the seam to u ~0.52 at the "
                                "frame's top edge) and the bottom (rows ~1380-1495, u 0.31-0.58) (overlays/cb0-source-map.jpg)",
                                "at 100 % the top wedge shows as a warmer, lighter band (L* +2.2, b* +3.3, dE ~4 against the B1 wall below) whose corner sits on the seam "
                                "(overlays/g112-CB-0-seam-top-100.jpg)",
                                "the vertical seam on the plain left wall: a soft tonal step dL* 1.0-1.9, dE 1.2-2.0 beyond the wall's own gradient over the 60 px blend "
                                "(data/cb0-seam.json; overlays/g112-CB-0-seam-stretch.jpg)",
                                "the two lumps right of the fern come with B1 r3 fix2"],
                    ok="lines cross the wedge borders continuously (wall corner 1074 -> 1076, floor joints continuous); the left part's door jamb on the clay (89/90)"),
      G112_T, False),
    C("G1.1", "the products are B1 r3 fix2's pixels (brush 38 %, basket on the floor)", "every product the card's SKU", True),
    C("G1.7-G1.9 (grading v5)", dict(**cb, note="judged by B1 (the same pixels and stops): at B1's point carried into CB-0 (0.645, 0.170) L 88.6, C* 6.25 (B1 89.2 / 5.42 at "
                                                "its own point; H 41.0 there next to the sconce glow, B1 35.9). The record's 'reading 79.3, meets_bible true' is inconsistent: "
                                                "79.3 is the darker wall left of the window at the old point (0.419, 0.174), outside 86-90"), LIGHT_T, True),
], "fail", "yes for geometry (named lines on the clay, 0.06 px against B1); as an image after the wedges and the seam are matched",
    "T-CBath: the geometry and the overlap pass; two 0-token items first: match the top / bottom wedges to B1 (or widen and colour-match the blend) and clear the lumps in B1 r3 fix2, then re-export CB-0",
    PU["B1 r3 fix"]["products_unverified"]))

out = dict(
    report="qa/reports/2026-11-04-m0-fix2-cb0-g1.md", by="qa-agent", date="2026-11-04",
    gate="G1 (docs/ops/quality-gates-2026-11-02.md) on the M0 1.2 code composites, the four fix2 frames, CB-0 recomposed from B1 r3 fix2, and grading v5 against Bible 1.8.4",
    brief="briefs/qa-m0-composite-fix2-cb0-2026-11-04.md",
    tools="site/tools/transitions/pan_reproject.py register / check; qa/reports/2026-11-04-m0-fix2-cb0-g1/tools/*.py (QA; the 11-03 / 11-04 tools imported, not edited); eye at 100-200 %",
    inputs_sha256_16={
        "m0-v8b-r2-fix.png": "d48e072d39ad087a", "m0-v8b-r2-graded-fix-v5.png": "29b47a2d17baa585", "pose-m0p-v8b-fix.png": "595cf8450b043c0c",
        "pose-m0p-v8b-graded-fix-v5.png": "5c48a6e2c1ee11d1", "pose-m0x-v8b-fix.png": "08ea42bf16125047", "pose-m0x-v8b-graded-fix-v5.png": "4634d13831299d96",
        "b1-v7-r3-fix2.png": "0e63a76919b73719", "b1-v7-r3-graded-fix2-v5.png": "baf7bbf14d2202be", "b2-v7-r3-fix2.png": "872d740cfb02e708",
        "b2-v7-r3-graded-fix2-v5.png": "5ab9a5c8770d19e9", "pose-k-girl-0-v7-r2-fix2.png": "693df84c5389b73d", "pose-k-girl-0-v7-r2-graded-fix2-v5.png": "662511616448cc19",
        "pose-w0-in-v7-r2-fix2.png": "22c22a1c53ba0d3a", "pose-w0-in-v7-r2-graded-fix2-v5.png": "2ee638baa684ab6d", "pose-cb-0-v7-b1r3.png": "8fcca55ac9e0dc18",
        "pose-cb-0-v7-graded-b1r3-v5.png": "24256db1d01cde7f", "regrade-v5-summary.json": "5999099291a6d612"},
    products_note="M0 / M0p / M0x lists are the v7 frames' (2026-11-02 report); M0 1.2's card set (Bible 1.8.3: pouf, armchair, rug) is not re-verified this round",
    out_of_scope="m0-v8b-r2-fix2.png / .json appeared at 22:47 during this run (render-agent's wall-art round, RND3): not checked here",
    frames=frames,
    m0_shell=dict(answer="confirmed: another perspective; a code correction of the shell is not realistic for M0 (parallax between the planes; >= 2-10 px at the joints "
                         "against the 2 px of a pan endpoint); only a new render. M0p: a uniform -1.3 % vertical, correctable by one affine of the raw (0 tokens). "
                         "M0x: within +-5 after its affine.", data="data/m0-shell.json"),
    grading_v5=LIGHT["rows"], grading_v5_cb0_b1r3=cb,
    grading_v5_counts=dict(qa_pass_on_the_agent_rules=LIGHT["counts"]["qa_pass"], agent_pass=LIGHT["counts"]["agent_pass"], disagree=LIGHT["counts"]["disagree"],
                           qa_pass_on_the_bible_text=LIGHT["counts"]["qa_pass"] - 1,
                           bible_text_note="Bible 1.8.4 asks the living back wall in the corridor's vista at target (1); the agent tests only 'vista p95 above every other "
                                           "surface's p99.5'. S1' passes that test (80.8 > 78.4) but its living back wall in the vista reads L 67-78 / L* 71-81, the same as "
                                           "its corridor wall (L* 73.5), not 90-94 (H0's vista 92.5). On the Bible's text S1' fails too: 11 of 33"),
    corridor_points=dict(C0=dict(point=[0.8578, 0.3695], render=lrow("c0-v7", None)["ref"], clay=lrow("c0-v7", None)["clay_at_point"], clean_wall=True,
                                 vista=lrow("c0-v7", None)["vista"], vista_back_wall_L=[77.0, 85.4]),
                         S1prime=dict(point=[0.755, 0.3612], render=lrow("pose-s1prime-v7", None)["ref"], clay=lrow("pose-s1prime-v7", None)["clay_at_point"], clean_wall=True,
                                      vista=lrow("pose-s1prime-v7", None)["vista"], vista_back_wall_L=[66.7, 77.8])),
    h0_hall=dict(qa_point=lrow("h0-v7-r2", None)["hall"]["qa_point"], left_of_the_art=dict(uv=[0.57, 0.30], L=81.8, Lstar=84.59), agent_Lstar=80.09,
                 B5=lrow("h0-v7-r2", None)["B5"], verdict="fails 75-78 (L* 80.0 at QA's point, 82.6-84.6 left of the art); B5 0.61 stop passes: the two rules overlap only "
                                                          "below about L* 78.6 with the vista at 94.5"),
    pairs=PAIRS, cb0_seam=SEAM,
    transitions={"T-CBath": "closest: geometry and overlap pass (0.06 px, dL 0.8); open after two 0-token items (B1 lumps; CB-0 wedges / seam) and a G1 re-check of those crops",
                 "V4 / T-HW": "W0-in r2 fix2 locked (video); blocked by the desk corner fix2 broke (0 tokens: restore it from fix)",
                 "P-B": "blocked: 9.0 px (was 14.2), B2's fill artefacts and C* 9.3",
                 "T-E0 / T-LD": "blocked: M0 1.2's shell needs a new render; P0 22.5 px, P1 36.4 px",
                 "T-CGirl": "blocked: the K-girl master (30.8 px) and K-girl-0's left quarter (-5 px)"},
)
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1.json"), "w"), indent=1, ensure_ascii=False)
for f in frames:
    print(f["frame"], f["verdict"], [(c["id"], c["pass"]) for c in f["criteria"]])
