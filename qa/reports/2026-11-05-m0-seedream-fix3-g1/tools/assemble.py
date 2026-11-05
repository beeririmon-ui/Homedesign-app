"""
qa-agent 2026-11-05: assembles qa/reports/2026-11-05-m0-seedream-fix3-g1.json from data/*.json and the eye verdicts (overlays/g112-*.jpg).
Same record shape as 11-03 / 11-04. Usage: python3.12 -I assemble.py
"""
import json
import os

REPO = "/home/user/homedesign-app"
OUT = os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1")
D = lambda f: json.load(open(os.path.join(OUT, "data", f)))  # noqa: E731
LOCK = {k: D(f"lock-{k}.json") for k in ("M0_seedream_raw", "M0_seedream_fix", "M0p_1.2_fix3", "B1_r3_fix3", "CB-0_b1r3f3", "W0-in_r2_fix3", "K-girl-0_r2_fix3")}
SHELL = D("m0s-shell.json")
LM = D("light-m0s.json")
LF = D("light-fix3.json")
PAIRS = D("pairs.json")
SEAM = D("cb0-seam.json")
PREV = {f["frame"]: f for f in json.load(open(os.path.join(REPO, "qa/reports/2026-11-04-m0-fix2-cb0-g1.json")))["frames"]}
G14_T = "pan_reproject.check in the overlap: <= 2 px per band with response >= 0.05 and dL <= 1 (gates doc 7.1, proposal; the principle binding)"
G14_4_T = ("register shift <= 9.6 px and scale within 0.5 %; residual after register <= 2.0 px per band (gate text) / tile with shared structure (QA: response >= 0.10, "
           "rho >= 0.30) for pan endpoints, <= 9.6 px for video endpoints; named lines within +-19 px (G1.4, proposal C3). Where the ECC register contradicts the "
           "named lines (it is not identifiable on plain walls), QA reads the residual unregistered and says so")
G112_T = "0 seams, halos, fill artefacts at 100 % (Bible 'forbidden'; G1.12)"
LIGHT_T = ("Bible 1.8.4: the reference wall in range (living 90-94, bath 86-90 HSL L), H 32-40, C* <= 7 (B4), window wall 80-88, black 12-15, max <= 97 and no 255; "
           "the grading chapter's light fall-off on the back wall: by the corner 90-94, centre behind the picture 88-91, the right edge 82-86, continuous")


def pair(a, b):
    p = next(x for x in PAIRS if x["a"] == a and x["b"] == b)
    return dict(pan=p["pan"], degrees=p["degrees"], bands=[[round(x["dx_px"], 2), round(x["dy_px"], 2), x["response"]] for x in p["render"]["bands"]],
                worst_reliable_px=p["render"]["worst_band_px_reliable"], dL=p["render"]["dL_mean"], dE_mean=p["render"]["deltaE"]["mean"], clay_floor_px=p["clay"]["worst_band_px_reliable"])


def lockv(k):
    L = LOCK[k]
    m = L["measure"]
    sc = m["register"]["scale"]
    return dict(register_shift_px=m["register"]["shift_px"], register_scale_pct=[round((sc[0] - 1) * 100, 2), round((sc[1] - 1) * 100, 2)],
                residual_gated=L["gated_residual"], masked_register=L["masked_register"],
                named_lines_px={n: dict(xcorr=v["d_xcorr"], r=v["r"], nearest_peak=v["d_nearest_peak"]) for n, v in L["named"].items()} or None,
                xcorr_box_ratios=m["summary"].get("xcorr_ratios"))


def C(i, value, threshold, ok, binding=True):
    return dict(id=i, binding=binding, value=value, threshold=threshold, **{"pass": ok})


def prevc(frame, cid):
    f = PREV[frame]
    return next(c for c in f["criteria"] if c["id"] == cid)


def rec(frame, kind, fix_file, graded, criteria, verdict, in_frame, may_ref, may_pan, products, live=()):
    fb = [c["id"] for c in criteria if c["binding"] and c["pass"] is False]
    return dict(frame=frame, kind=kind, fix_file=fix_file, graded=graded, criteria=criteria, verdict=verdict, failed_binding=fb, failed_in_the_frame=in_frame,
                failed_proposal=[c["id"] for c in criteria if not c["binding"] and c["pass"] is False], cannot_measure=["G1.2", "G1.5", "G1.11", "G1.15", "G1.16"],
                may_reference=may_ref, may_pan_endpoint=may_pan, products_unverified=list(products), products_live=list(live))


R = "assets/renders/"
V9 = R + "living-room/nordic/v9/"
M0_PRODUCTS = list(PREV["M0 1.2 fix"]["products_unverified"]) + ["wall-decor-cj-corn-husk-round-38"]
frames = []
sr, sf = SHELL["M0 seedream raw"], SHELL["M0 seedream fix"]
frames.append(rec("M0 seedream raw", "paid render 2026-11-05, seedream-5-pro on the round-5b clay (M0S1)", V9 + "m0-shell-seedream.png", V9 + "m0-shell-seedream-graded-v5.png", [
    C("G1.4", dict(**lockv("M0_seedream_raw"), shell=dict(per_line_px=sr["per_line_d"], max_abs_px=sr["max_abs_px"], fits=sr["fits"],
        note="QA's peak lists (data/m0s-shell.json): every shell line within +-3 px; the skirting top is a double edge in the render (a bead 5 px above): "
             "paired with the nearest it is +0.7..+1.3, with the upper bead -4.1..-5.6 (render-agent's -4.2..-5.5). One homography fits every plane "
             "to 2.7 px and the back wall's homography meets the window wall to 3.1 px: the same camera, no parallax (gpt: 27-32 px on 11-04)")),
      G14_4_T + "; global scale -0.51 % is 0.01 % over", False),
    C("G1.3", dict(xcorr=dict(sofa=1.0, table=0.995, armchair=1.0), wall_round="x1.86 of the 38 cm card (corrected in the composite)"), "+-15 % (proposal)", False, False),
], "fail", ["G1.4 (scale -0.51 %, 0.01 % over)", "G1.3 (the wall round x1.86)"], "superseded by the composite (one affine, the round, the triptych)", "no (the composite is the candidate)", M0_PRODUCTS))
lmf = LM["M0 seedream fix (v5)"]
frames.append(rec("M0 seedream fix", "code composite 2026-11-05 on the seedream render: one global affine, the wall round x0.537, the RND3 triptych (art_m0_12.py)",
                  V9 + "m0-1-2-shell-seedream-fix.png", V9 + "m0-1-2-shell-seedream-graded-fix-v5.png", [
    C("G1.4", dict(**lockv("M0_seedream_fix"), shell=dict(per_line_px=sf["per_line_d"], max_abs_px=sf["max_abs_px"], fits=sf["fits"]),
                   tile_note="the one tile over 2 px (u 0.25-0.5, v 0-0.5: 6.4 px horizontal, rho 0.58) holds the right curtain stack: the window's inner reveal, "
                             "the rod, the cornice and the corner lie on the clay lines there (overlays/m0s-tile-upper-left-clay-edges.jpg); the residual is the "
                             "curtain, a soft product drawn wider than the clay proxy (frame x ~555-635 against ~560-615). Carried to G1.3 and to P0",
                   masked_register_note="the masked register (products out) is not identifiable here (+7 % scale): not used"),
      G14_4_T, True),
    C("G1.3", dict(sofa_xcorr=1.0, table_xcorr=0.995, armchair_by_edges=1.0, armchair_xcorr_note="0.935 is a mis-pair (left edge +36 at r 0.65); the direct edges are 0 / 0 / 0",
                   wall_round_px=[117.5, 125], wall_round_target_px=[118.3, 129.1], right_curtain_stack="about 1.4x the clay proxy's width (soft product)"),
      "+-15 % (proposal)", None, False),
    C("G1.1", dict(ok=["triptych: prints 2 and 3 as in the listing images (the circle on the fold line between two light bands; three bars between two light bands); "
                       "framed in oak with a white mat, as PR1 allows (sold unframed)", "wall round: corn-husk coil with a braided hyacinth rim, 38 cm by projection"],
                   deviations=["table runner: a short sage cloth lying on the table, no fringe and no overhang; the card is 33 x 183 with a tassel fringe at both ends, "
                               "crossing the table (living-room.json: across its width in the left third). The 11-04 gpt render had it right"],
                   notes=["print 1's listing image is not on disk (no network): it comes from the old M0 r2's rendered print 1, not checked against the listing",
                          "print 3's oatmeal panel reads warmer and darker than prints 1-2 at 100 % (the listing: one oatmeal for the set)",
                          "the other products (bowl, candle holders, cushions, throw, rug, pendant, sconces, curtains, vase, armchair, sofa) are not checked against "
                          "their card images this round (none on disk); the bowl reads beige-speckled against the card's warm white"]),
      "every product the card's SKU: silhouette, count, pattern, material", False),
    C("G1.12", dict(ok=["triptych crisp at 100 % (a faint light outline round print 1's black squares at 200 %)", "the wall behind the old, larger round: clean membrane fill",
                        "no other code edit"], overlays=["overlays/g112-M0s-triptych-100.jpg", "overlays/g112-M0s-triptych-left-200.jpg", "overlays/g112-M0s-wall-round-raw-200.jpg"]),
      G112_T, True),
    C("G1.7-G1.9 (grading v5)", dict(bible_point=lmf["back_wall"], window_wall=lmf["window_wall"], fall_off=lmf["fall_off"], black=lmf["black"], max_L=lmf["max_L"], px255=lmf["px255"],
                                     tonal_shape=lmf["shape"], references={k: dict(fall_off={n: v["L"] for n, v in LM[k]["fall_off"].items()}, shape=LM[k]["shape"]) for k in LM if k != "M0 seedream fix (v5)"},
                                     milky="the centre of the back wall sits in the roll-off: L 96.5 with S 0 and C* 0.02 at (0.62, 0.30) and (0.62, 0.55), against 88-91; "
                                           "the right edge 90.9 against 82-86. 68.7 % of the frame is above L* 90, the median local contrast 1.3 L*, mean C* 6.5 "
                                           "(m0-v7-r2: 62.5 %, 1.6, 9.9). In the raw the corner is the darker part of the back wall (72.8; centre 82-85, right edge 70.6): "
                                           "the +0.77 stop that puts the corner at 92 pushes the centre into the roll-off. One global grade cannot meet both; a light or "
                                           "Bible decision"),
      LIGHT_T, False),
    C("G1.14", dict(P0_against_M0p_fix3=pair("M0 seedream fix", "M0p 1.2 fix3"), note="not a valid pair: M0p fix3 is the gpt render; P0 waits for the seedream M0p (paid, not pulled)"),
      G14_T, None),
], "fail", ["G1.1 (table runner)", "G1.7-G1.9 (the back wall's fall-off: milky)"],
    "yes for geometry: the first M0 1.2 whose shell and fixed furniture sit on the round-5b clay (19 shell lines within 2.8 px, the same perspective); as an image after the light decision and the runner",
    "not yet: P0 needs the seedream M0p (paid, not pulled) and the curtain tile settled in that pair; T-E0 ends on M0: after the light", M0_PRODUCTS))
# ------------------------------------------------ M0p fix3
lp = LF["M0p 1.2 fix3"]
frames.append(rec("M0p 1.2 fix3", "code 2026-11-05 on the gpt pose (m0p_fix3.py): +1.337 % vertical on the raw, re-composite, the doubled bowl removed, the triptych",
                  R + "poses/nordic/v8/pose-m0p-v8b-fix3.png", R + "poses/nordic/v8/pose-m0p-v8b-graded-fix3-v5.png", [
    C("G1.4", dict(**lockv("M0p_1.2_fix3"), shell_by_peaks_1080="floor line 871 = clay; cornice 75 = clay (+-2 at x 600); corner 1362 = clay; side wall 933 / 1011 / 1042 against 934 / 1014 / 1043; "
                   "skirting top +6 (a shorter skirting than the clay's); sofa arms 305 = 305 and 1016-1018 against 1011-1026: the shell and the sofa on the clay",
                   register_note="the ECC register (-5.5 / +13.6 px, +0.93 / -1.04 %) contradicts the lines: not identifiable; read unregistered: tile 17.9 px (u 0.25-0.5, "
                                 "v 0.5-1.0, rho 0.37: the table / runner / rug), band 7.6 (u 0-0.25): over 2 px"), G14_4_T, False),
    C("G1.1", "the bowl is single now; the triptych as in M0", "every product the card's SKU", True),
    C("G1.12", dict(violations=["a pale rectangle with hard edges on the oak table top round the bowl and the holders (the decor clean-up; canvas ~x 1085-1230, y ~1195-1285): visible at 100 %",
                                "right of the sofa's right leg: the rectangular blocks on the rug border and the vertical seam through the floor and the rug, unchanged"],
                    overlays=["overlays/g112-M0p-bowl-200.jpg", "overlays/g112-M0p-floor-right-leg-200.jpg", "overlays/g112-M0p-sofa.jpg"]), G112_T, False),
    C("G1.7-G1.9 (grading v5)", lp, LIGHT_T, True),
    C("G1.14", dict(P0=pair("M0 seedream fix", "M0p 1.2 fix3")), G14_T, False),
], "fail", ["G1.4 (residual)", "G1.12"], "no: superseded by the seedream M0p once pulled", "no: P0 7.3 px, dL 4.2 against the seedream M0 (different renders)", PREV["M0p 1.2 fix"]["products_unverified"]))
# ------------------------------------------------ B1 r3 fix3
lb = LF["B1 r3 fix3"]
frames.append(rec("B1 r3 fix3", "code 2026-11-05 (fix_v10.py): the two lumps right of the fern cleared", R + "bath/nordic/v7/b1-v7-r3-fix3.png", R + "bath/nordic/v7/b1-v7-r3-graded-fix3-v5.png", [
    C("G1.4", dict(**lockv("B1_r3_fix3"), note="as fix2: named lines 0 / +-1 by cross-correlation (r 0.65-0.99); the +14 / -11 / -17 nearest peaks are neighbours (glazing mullion, track end, vanity front)"), G14_4_T, True),
    C("G1.1", "brush 38 % holder (card), the basket on the floor: unchanged since fix2", "every product the card's SKU", True),
    C("G1.12", dict(fixed="the two pale lumps right of the fern are gone; the folds continue (overlays/g112-B1-lumps-200.jpg)",
                    minor=["the leftmost linen fold above the fern keeps faint blocky steps (canvas ~x 1455-1530, y ~620-900) and the curtain's left edge is a straight diagonal: "
                           "plain at 200 %, faint at 100 % only on close inspection (overlays/g112-B1-around-fern-100.jpg); not blocking, for the final polish",
                           "soft green-grey smudges on the wall left of the fern (its old shadow): read as the plant's soft shadow"]), G112_T, True),
    C("G1.7-G1.9 (grading v5)", lb, LIGHT_T, True),
    C("G1.14", dict(T_CBath=pair("B1 r3 fix3", "CB-0 b1r3f3"), P_B=pair("B1 r3 fix3", "B2 r3 fix2")), G14_T + " (P-B fails on B2's side)", False),
    prevc("B1 r3 fix2", "G1.6"), prevc("B1 r3 fix2", "G8.6"),
], "pass in the frame (G1.14 P-B fails on B2's side; G8.6 is the cards' liveness, not the image)", [],
    "yes: geometry, products, light; the faint fold steps above the fern for the final polish", "T-CBath: yes (the pan's end). P-B: no (9.0 px, B2 r3 fix2)", PREV["B1 r3 fix2"]["products_unverified"]))
# ------------------------------------------------ CB-0 b1r3f3
lc = LF["CB-0 b1r3f3"]
frames.append(rec("CB-0 b1r3f3", "recomposed 2026-11-05 from B1 r3 fix3 (recompose_cb0_v3.py): the kept part matched by a gain field, a 150 px blend",
                  R + "poses/nordic/v7/pose-cb-0-v7-b1r3f3.png", R + "poses/nordic/v7/pose-cb-0-v7-graded-b1r3f3-v5.png", [
    C("G1.4", dict(**lockv("CB-0_b1r3f3"), named_lines_px_1080="on the round-4 CB-0 clay: window sides 822/832/862 and head 102/132/163-167 against 103/133/166, WC block 729/750/1241, "
                   "block top 575-581, ledge 643/685, left jamb 89/90: 0 / +-1 (the head +-3)", register_note="the ECC register (+3.4 / -7.5 px, a 0.5 % shear) is biased by the plain walls; "
                   "unregistered: bands 0.10 / 0.15, tiles <= 0.65 px"), G14_4_T, True),
    C("G1.14", dict(T_CBath=pair("B1 r3 fix3", "CB-0 b1r3f3"), agent="0.06 px, dL 0.8: confirmed (dE 1.0)"), G14_T, True),
    C("G1.12", dict(fixed=["the upper wedge now matches the B1 wall: dE 1.36 (was 4.21); no light band, no rectangle at 100 % and none at x4 contrast (overlays/g112-CB-0-seam-stretch.jpg)",
                           "the vertical seam: the bump over the wall's own smooth gradient is 0.36-0.53 L* (was 0.80-0.89), rms 0.2", "the lumps of B1 are gone here too"],
                    data=SEAM, overlays=["overlays/g112-CB-0-seam-top-100.jpg", "overlays/g112-CB-0-top-wedge-100.jpg", "overlays/g112-CB-0-bottom-wedge-100.jpg", "overlays/cb0-source-map.jpg"]),
      G112_T, True),
    C("G1.1", "B1 r3 fix3's pixels (brush 38 %, basket on the floor)", "every product the card's SKU", True),
    C("G1.7-G1.9 (grading v5)", dict(**lc, note="judged by B1 (the same pixels and stops) at B1's point carried into CB-0; the record is corrected (79.3 explained)"), LIGHT_T, True),
], "pass in the frame (G8.6: the cards' liveness, not the image)", [],
    "yes", "T-CBath: yes (the slide's end and the pan's start, with B1 r3 fix3)", PREV["CB-0 b1r3"]["products_unverified"]))
# ------------------------------------------------ W0-in fix3
lw = LF["W0-in r2 fix3"]
wl = LOCK["W0-in_r2_fix3"]
frames.append(rec("W0-in r2 fix3", "code 2026-11-05: fix2 with the desk's front-left corner taken back from fix", R + "poses/nordic/v7/pose-w0-in-v7-r2-fix3.png", R + "poses/nordic/v7/pose-w0-in-v7-r2-graded-fix3-v5.png", [
    C("G1.4", dict(**lockv("W0-in_r2_fix3"), note="video endpoint: after register the worst band is 9.64 px (9.6, a proposal) because the 0.58 px / 0.05 % register moves it the wrong way; "
                   "unregistered the same band is 7.27 and the worst tile 7.58. Named lines <= 8 (chair right -8; the +32 / +36 cross-correlations are mis-pairs: chair top -3, shelf front 0/+1 "
                   "by the peak lists). QA rules it within the measurement's precision: pass"), G14_4_T, True),
    C("G1.1", "pencil cup as on 11-04; the desk corner restored", "every product the card's SKU", True),
    C("G1.12", dict(fixed=["the desk's front-left corner is fix's again: one outer edge, the mitred slab corner (overlays/g112-W0-in-desk-corner-vs-fix.jpg)", "the basket's weave clean"],
                    ok="the 'dark block' beside the basket's base is the floor under the skirting in the gap between basket and leg; the skirting continues above it: not a fill artefact"), G112_T, True),
    C("G1.7-G1.9 (grading v5)", lw, LIGHT_T, True),
    C("G1.14", "dolly W0 fix -> W0-in r2 fix3: the same objects by eye (overlays/endpoints-W0_fix-W0-in_r2_fix3.jpg); no pan rule", G14_T, None),
    prevc("W0-in r2 fix2", "G8.6"),
], "pass in the frame (G8.6: the cards' liveness)", [], "yes (video endpoint)", "V4 / T-HW: yes from W0-in's side; the W0 master end is outside this brief",
    PREV["W0-in r2 fix2"]["products_unverified"], PREV["W0-in r2 fix2"]["products_live"]))
# ------------------------------------------------ K-girl-0 fix3
lk = LF["K-girl-0 r2 fix3"]
kl = LOCK["K-girl-0_r2_fix3"]
frames.append(rec("K-girl-0 r2 fix3", "code 2026-11-05: fix2 + a local horizontal warp of the left quarter (x < 600 at 1920)", R + "poses/nordic/v7/pose-k-girl-0-v7-r2-fix3.png",
                  R + "poses/nordic/v7/pose-k-girl-0-v7-r2-graded-fix3-v5.png", [
    C("G1.4", dict(**lockv("K-girl-0_r2_fix3"), register_by_region=kl.get("register_by_region"),
                   lines_by_peaks_1080="left quarter: row 200 clay 8 / 26 / 72 -> 12 / 22 / 73 (a pair of edges drawn 8 px closer), row 330 69 / 76 / 207 -> 71 / 77 / 203, "
                                       "row 650 542 -> 539 / 545, row 900 414 / 446 / 496 / 515 / 521 -> 415 / 446 / 495 / 516 / 521; horizontal lines 0 / +-1",
                   note="the register is still not identifiable (regions -0.85 .. +1.54 %, shifts to 27 px; plain ECC +0.90 %); unregistered: tiles <= 1.32 px (rho >= 0.30), bands <= 1.24: within 2 px"),
      G14_4_T, True),
    C("G1.1", "prints and doll unchanged (the warp stops at x 600, the prints start at ~630)", "every product the card's SKU", True),
    C("G1.12", "the local warp leaves no bend or seam at 200 % (overlays/g112-K-girl-0-left-200.jpg)", G112_T, True),
    C("G1.7-G1.9 (grading v5)", lk, LIGHT_T, True),
    C("G1.14", dict(T_CGirl=pair("K-girl fix", "K-girl-0 r2 fix3")), G14_T + " (fails on the K-girl master's side)", False),
    prevc("K-girl-0 r2 fix2", "G8.6"),
], "pass in the frame (T-CGirl fails on the master's side; G8.6 the cards' liveness)", [], "yes", "no: T-CGirl 28.8 px from the K-girl master (-20.5 px, -1.86 % vertical)",
    PREV["K-girl-0 r2 fix2"]["products_unverified"]))

out = dict(
    report="qa/reports/2026-11-05-m0-seedream-fix3-g1.md", by="qa-agent", date="2026-11-05",
    gate="G1 (docs/ops/quality-gates-2026-11-02.md) on M0 1.2 from the three-model test (seedream-5-pro, M0S1: raw and code composite) and on the fix3 round",
    brief="the coordinator's task of 2026-11-05 (no brief file): board lines 2026-11-05 'render-agent (fix3, 0 טוקנים)' and 'render-agent (ניסוי שלושה מודלים ...)'",
    tools="site/tools/transitions/pan_reproject.py register / check; qa/reports/2026-11-05-m0-seedream-fix3-g1/tools/*.py (QA; the 11-03 / 11-04 tools imported, not edited); eye at 100-200 %",
    inputs_sha256_16={"m0-shell-seedream.png": "ca2b720b7db32211", "m0-1-2-shell-seedream-fix.png": "aca9366f5eca7219", "m0-1-2-shell-seedream-graded-fix-v5.png": "7bade8ca8cdc0b55",
                      "m0-1-2-shell-seedream-fix.json": "4f412fe15efd91ed", "m0-1-2-shell-seedream-fix-base.json": "f074797c9a4ec90a", "b1-v7-r3-fix3.png": "f6068555192c473c",
                      "b1-v7-r3-graded-fix3-v5.png": "b8767fd2fa9c8823", "pose-cb-0-v7-b1r3f3.png": "ac60b39f1a32afc1", "pose-cb-0-v7-graded-b1r3f3-v5.png": "ba2bce0ece7f0962",
                      "pose-cb-0-v7-b1r3f3-overlap.json": "ea3cb2a0df89131a", "pose-w0-in-v7-r2-fix3.png": "cc4e840fe8aa5cc0", "pose-w0-in-v7-r2-graded-fix3-v5.png": "c3e5ae367d2ccaa2",
                      "pose-m0p-v8b-fix3.png": "8db8f7dac49b8536", "pose-m0p-v8b-graded-fix3-v5.png": "3059628ccb841910", "pose-k-girl-0-v7-r2-fix3.png": "df41b8f591685ca9",
                      "pose-k-girl-0-v7-r2-graded-fix3-v5.png": "a456831514848973"},
    reference_images="the listing images of prints 2 and 3 from the session scratchpad (downloaded by render-agent on 11-04; QA did not use the network): overlays/ref-triptych-listing-prints-2-3.jpg",
    frames=frames, m0_shell=SHELL, light_m0=LM, light_fix3=LF, pairs=PAIRS, cb0_seam=SEAM,
    t_cbath=dict(answer="yes: CB-0 b1r3f3 and B1 r3 fix3 may serve as the bath ends of T-CBath (the slide's end / the pan's start and the pan's end)",
                 why=["both pass G1 in the frame (geometry on the clay, products, light, no visible seam)", "the pair: 0.06 px in four bands, dL 0.8, dE 1.0"],
                 still_open=["the rest of T-CBath runs through S1' (the R2 dolly and the slide S1' -> CB-0): S1' is outside this brief and has open items (11-02 lock, 11-04 vista)",
                             "the white-balance ramp 4600 -> 4000 K in post at the door frame (transitions plan)", "the faint fold steps above the fern: final polish, not blocking"]),
    transitions={"T-CBath": "unblocked at the bath ends (CB-0 b1r3f3 + B1 r3 fix3); the corridor side through S1' still open",
                 "V4 / T-HW": "unblocked from W0-in's side (W0-in r2 fix3); the W0 master end not re-checked here",
                 "P-B": "blocked: 9.0 px, B2 r3 fix2 unchanged (its fill artefacts, C* 9.3, vanity -7/-8)",
                 "T-CGirl": "blocked: the K-girl master (28.8 px); K-girl-0 itself passes",
                 "P0 / T-E0 / T-LD": "blocked: the seedream M0 is on the clay (geometry solved) but its light is milky (fall-off) and P0 needs the seedream M0p (paid, not pulled)"},
)
json.dump(out, open(os.path.join(REPO, "qa/reports/2026-11-05-m0-seedream-fix3-g1.json"), "w"), indent=1, ensure_ascii=False)
for f in frames:
    print(f["frame"], "|", f["verdict"][:40], "|", [(c["id"], c["pass"]) for c in f["criteria"]])
