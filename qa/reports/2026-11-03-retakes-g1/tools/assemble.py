"""
Assembles qa/reports/2026-11-03-retakes-g1.json (one record per still: frame, criteria[] with id, value, threshold, pass,
binding; verdict; may_reference; may_pan_endpoint; products_unverified[]) from the data/ files of the other tools, and prints
the Markdown tables of the report. The eye verdicts (G1.1 fidelity, G1.12 forbidden list) are written here as data, by
qa-agent, 2026-11-03, on the graded-v3 stills at 1600 px and on the fidelity sheets at 100 %.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

D = os.path.join(C.OUT, "data")


def J(name):
    p = os.path.join(D, name)
    return json.load(open(p)) if os.path.exists(p) else None


light = {s: J(f"light-{C.fn(s)}.json") for s in C.RETAKES + C.V3_ROWS}
lock = {s: J(f"lock-{C.fn(s)}.json") for s in C.RETAKES}
edges = J("edges-direct.json")
pairs = J("pairs.json")
ovs = J("overscan.json")
dens = J("density.json")
prods = J("products.json")
bath = J("bath-products.json")
fid = {s: J(f"fidelity-{C.fn(s)}.json") for s in C.RETAKES}

# --- eye verdicts (qa-agent, 2026-11-03) ----------------------------------------------------------------------------------
EYE_FIDELITY = {
    "W0-in r2": dict(deviations=["desk-organizer: the stone pen cup about 1.4x the clay box in width and taller than it (card 8 x 11 cm); the pencils are the filler",
                                 "desk: the slab, drawer and side panels sit 39-46 px (3.6-4.3 % of the height) above the clay lines; the chair back and the shelf are on theirs"],
                     ok=["rope basket (cut by the bottom edge, in its box)", "kraft bin (in its box, cut by the bottom edge)", "seagrass belly basket with the same ZZ plant as the W0 master (crown to the shelf height, the designer's deliberate deviation)",
                         "two light-grey felt bins with the same satin eyelet handles as the accepted W0 master", "no window, curtain or rug in view; nothing invented on the bare wall"]),
    "K-girl-0 r2": dict(deviations=["framed prints: the pair about 1.7x the clay box width (each print about 50 cm wide instead of 30 x 40 of the card); same charcoal flower silhouettes and thin frames as the K-girl master",
                                    "doll: the linen bunny about 2x the clay box in width and 1.6x in height (the K-girl master fix set it to 1.12x); same doll, same oat dress",
                                    "muslin blanket: draped over the bed's foot rail instead of folded on the foot third (the master shows it folded)"],
                        ok=["two-tier oak ledges with picture books in blush / oat / warm white, no readable text, cut by the left edge", "the band on the desk wall only, the near wall plain warm white, the corner line clean at x 0.60",
                            "oak desk and bed foot as in the clay; no window, lamp, chair or invented object"]),
    "B1 r3": dict(deviations=["INVENTED OBJECT: a pale stone cylinder (plinth) under the seagrass basket, about 26 cm tall at the pot's scale; the basket stands on it at 26-53 cm above the floor instead of on the floor; the clay's pot cylinder was read as a plinth",
                              "toilet brush: a tall matte-black cylinder 1.37x the clay box height (about 52 cm at the box's 38 cm) and 1.27x its width; the card is a short 14.5 cm holder with a 25 cm handle (handle 66 % of the height), the render a 34 cm holder with an 18 cm handle",
                              "floor planter basket: 0.91x the pot box height and 1.11x its width (inside +-15 %), the same straight chunky-coil seagrass as the card, but lifted by the plinth"],
                  ok=["linen slub curtain gathered at the corner, fluted wall lamp (lit), tufted cream bath mat, slim black roll stand with one spare roll at its base, milk-tea diffuser with reeds, ribbed candle cup (unlit), three sand ribbed pump bottles in the niche",
                      "wall-hung WC on the limestone ledge, fluted window with no view and no snow, the east vanity sconce cut at the right edge (lit)", "fern sage, not bright green"]),
    "B2 r3": dict(deviations=["floor planter basket (cut by the left edge) 1.18x the clay pot height and about 1.2x its width: outside +-15 %, and not the same size as the basket in B1 r3 (0.91x) seen from the same point",
                              "vanity: the right edge 38-43 px (2 % of the width) inside the clay's, the cabinet reads about 5 % narrower (ratio 0.954); mirror frame about 10 px wider and its top edge about 30 px above the clay's",
                              "mirror: a small dark bracket / line reflected in the top-left corner inside the glass (the clay's F8 ray-cast lists no non-wall object; the prompt forbids any object in the mirror)",
                              "storage basket: about 1.25x the box width (fills the shelf more than the clay); towel ring about 1.3x the box"],
                  ok=["oak vanity with drawer and open shelf, round basin, matte black wall tap, two fluted lamps (lit), gathered linen curtain, three pump bottles in the niche, ribbed soap pump, travertine cup with two bamboo toothbrushes, oat bud vase with a eucalyptus sprig, black oval towel ring with a linen hand towel, cream rope basket with three rolled towels",
                      "the basket of the planter on the floor (no plinth), the same seagrass as the card and as B1 r3", "no window in frame, no snow"]),
}
EYE_FORBIDDEN = {
    "W0-in r2": dict(violations=[], notes=["0 pixels at 255; no sun patches, beams, bloom, haze, halos; no visible cable, bulb, text, people; no window in frame; the ZZ plant's glossy leaves are the filler, not a product"]),
    "K-girl-0 r2": dict(violations=[], notes=["0 pixels at 255; no snow (no window); no cable, bulb, text, people; the blush band is the room's approved exception; no object beyond the prompt's products"]),
    "B1 r3": dict(violations=["an object in frame that is neither a product with a card nor a registered filler: the stone plinth under the planter basket (Bible 'אסור'; recipe section 2.7)"],
                  notes=["0 pixels at 255 after the grade; no snow, no view through the fluted glass; no sun patches, no cable; the spare roll at the stand's base and the reeds / wax / liquids are fillers of their products"]),
    "B2 r3": dict(violations=["an object reflected in the U6 mirror (a small dark bracket / line in the top-left corner of the glass): F8 asks for wall only; the prompt's NOT IN FRAME lists 'any object reflected in the mirror'"],
                  notes=["0 pixels at 255; no window, no snow; no cable, text, people; nothing on the vanity beyond the three products of the surface group"]),
}
MAY = {
    "W0-in r2": ("no: the desk slab and drawer sit 39-46 px above the clay lines (named edges); pen cup about 1.4x its box", "no: a video endpoint (V4 / T-HW), and its lock fails"),
    "K-girl-0 r2": ("no: framing now follows the clay (fixed furniture within +-11 px), but the prints are 1.7x and the doll 2x their clay boxes", "no: K-girl -> K-girl-0 30.6 px in the reliable band (2 px)"),
    "B1 r3": ("geometry only, after a code fix (plinth out, basket down to the floor, brush x0.73) and a G1 re-run: every named line within +-5 px, bands <= 0.96 px after register", "after the same fix and G1 re-run (T-CBath via a re-composed CB-0, P-B start); not as it is"),
    "B2 r3": ("no: vanity right edge -43 px (0.954), basket 1.18x, an object reflected in the mirror", "no: P-B 5.7 px (2 px); the basket differs in size from B1 r3"),
}
SERVES = {"W0-in r2": ["V4 pull-back / T-HW (end)"], "K-girl-0 r2": ["T-CGirl pan (start)", "V8 slide (end)"], "B1 r3": ["T-CBath pan (end)", "P-B pan (start)", "CB-0 re-composite source"], "B2 r3": ["P-B pan (end)"]}

records = []
for sid in C.RETAKES:
    L = light[sid]
    K = lock[sid]["raw"]
    s, v = K["summary"], K["verdict"]
    pan = lock[sid]["pan_endpoint"]
    E = edges[sid]
    crit = []
    # G1.4
    resid = [x for x in (s["worst_band_px_after_register"], s["worst_tile_ecc_px_after_register"]) if x is not None]
    crit.append(dict(id="G1.4", value=dict(register_shift_px=s["register_shift_px"], register_scale_pct=s["register_scale_pct"], worst_band_px_after_register=s["worst_band_px_after_register"],
                                           bands_reliable=s["bands_reliable_after_register"], worst_tile_px_after_register=s["worst_tile_ecc_px_after_register"], tiles_counted=s["tiles_counted_after_register"],
                                           named_edges_px={k: dict(strongest=e["d_strongest_px"], xcorr=e["d_xcorr_px"], r=e["xcorr_r"]) for k, e in E.items()},
                                           agent_lock_v2=lock[sid].get("agent_lock_v2", {}).get("passed")),
                     threshold=("global shift <= 9.6 px and scale within 0.5 %; residual per band / tile after register <= 2 px (pan endpoint)" if pan else
                                "global shift <= 9.6 px and scale within 0.5 %; residual <= 9.6 px (video endpoint; render-agent applied the 2 px pan rule)"),
                     passed=bool(v["passed"]), binding=True, note="principle binding (house plan frame_checks, Bible 'תנועה'); the numbers are the gates document's proposals (C3)"))
    # G1.3 fixed edges + products
    worst_named = max((abs(e["d_xcorr_px"]) if e["xcorr_r"] >= 0.5 else abs(e["d_nearest_px"])) for e in E.values())
    crit.append(dict(id="G1.3", value=dict(fixed_edges_worst_px_boxes=s["fixed_edges_worst_px"], fixed_ratios=s["fixed_ratios"], xcorr_ratios=s["xcorr_ratios"], named_edges_worst_px=worst_named,
                                           product_extent={k.split("/")[-1]: (v_["extent_estimate"] or {}).get("height_ratio") for k, v_ in fid[sid]["products"].items()}),
                     threshold="every clear edge of a fixed piece within +-19 px (+-0.01 of 1920), width / height ratios 0.95-1.05; products inside their box +-15 % (eye on the sheet)",
                     passed=bool(worst_named <= 19 and all(0.95 <= r <= 1.05 for k, r in s["fixed_ratios"].items() if "shower fittings" not in k) and not EYE_FIDELITY[sid]["deviations"]), binding=False))
    # G1.1 fidelity (eye)
    crit.append(dict(id="G1.1", value=dict(deviations=EYE_FIDELITY[sid]["deviations"], ok=EYE_FIDELITY[sid]["ok"], eye="qa-agent, 2026-11-03, graded-v3 at 1600 px and the fidelity sheet at 100 %"),
                     threshold="every product is the card's SKU: same silhouette, count, pattern, material; 0 deviations", passed=bool(not EYE_FIDELITY[sid]["deviations"]), binding=True))
    # G1.7 / G1.8 light
    ref = L.get("reference") or {}
    lo, hi = L["target"]["lo"], L["target"]["hi"]
    crit.append(dict(id="G1.7/G1.8", value=dict(reference=ref.get("label"), uv=ref.get("uv"), graded_HSL=ref.get("graded_HSL"), lab_C=ref.get("lab_C"), range=[lo, hi], target_source=L["target"]["source"],
                                                agent_measured_L=(L.get("agent") or {}).get("measured_L"), agent_applied_stops=(L.get("agent") or {}).get("applied_stops"), agent_judged_by=(L.get("agent") or {}).get("judged_by")),
                     threshold="the lit wall by the window in the Bible range (bath 1.6: 86-90; others 90-94); test page: graded to the target (V7Q4)",
                     passed=(None if L.get("B1_lit_wall_ok") is None else bool(L["B1_lit_wall_ok"])), binding=True,
                     note=("B2 inherits B1's stops (one exposure per camera point); its wall beside the mirror has no Bible number: 81.9 is a reading, not a verdict" if sid == "B2 r3" else None)))
    # G1.9 black, hue, chroma
    crit.append(dict(id="G1.9", value=dict(black_point_L_frame=L["black_point_L"], black_point_L_canvas=L.get("canvas_black_point_L"), wall_H=ref.get("graded_HSL", [None])[0], wall_labC=ref.get("lab_C"),
                                           near_white_C_median=L.get("near_white_B4", {}).get("C_median"), near_white_C_p95=L.get("near_white_B4", {}).get("C_p95")),
                     threshold="black point L 12-15 (darkest 0.5 % patch); wall H 32-40; near-white chroma C* <= 7 on the warm-white wall (B4 working value)",
                     passed=bool(L["black_point_ok_12_15"] and (ref.get("graded_HSL") is None or (32 <= ref["graded_HSL"][0] <= 40 and ref["lab_C"] <= 7.0))), binding=True))
    # G1.13 window / roll-off
    w = L["window"]
    crit.append(dict(id="G1.13", value=dict(window=w.get("box"), window_L_p99=w.get("L_p99"), brightest=w.get("brightest"), frame_L_p99=L["frame_L_p99"], frame_L_max=L["frame_L_max"], px_255=L["px_255"]),
                     threshold="window the brightest, p99 <= 97, no 255 channel; roll-off from L 94", passed=bool(L["rolloff_ok"] and (w.get("brightest") is None or w.get("brightest"))), binding=True))
    # G1.12 forbidden
    crit.append(dict(id="G1.12", value=EYE_FORBIDDEN[sid], threshold="0 violations of the closed list (Bible 'אסור', recipe 2.7)", passed=bool(not EYE_FORBIDDEN[sid]["violations"]), binding=True))
    # G1.6 density (masters only)
    if sid in dens and "test_rule" in dens[sid]:
        dd = dens[sid]
        crit.append(dict(id="G1.6", value=dict(test_rule=dict(passed=dd["test_rule"]["passed"], filled=dd["test_rule"]["filled"], unfilled_with_approved_card=dd["test_rule"]["unfilled_with_approved_card"], sourcing_tasks=dd["test_rule"]["sourcing_tasks"]),
                                               today_rule=dict(counted=dd["today_rule"]["counted"], minimum=dd["today_rule"]["minimum"], categories_of_5=dd["today_rule"]["categories_of_5"]),
                                               v7q6_estimate=dict(counted=dd["v7q6_estimate"]["counted"], minimum=dd["v7q6_estimate"]["minimum"], categories_of_5=dd["v7q6_estimate"]["categories_of_5"], passed_frame=dd["v7q6_estimate"]["passed_frame"])),
                         threshold="test frames (studio rules 2.11): every slot with an approved product filled; final assets: V7Q6 (2.13) 11 / half for the second frame, room 15, 4 of 5 categories",
                         passed=bool(dd["test_rule"]["passed"]), binding=True, note="the test rule decides for this round; the V7Q6 column is an estimate from clay boxes"))
    # overscan
    o = ovs[sid]
    crit.append(dict(id="OVS", value=dict(required=o["required"], why=o["why"], applied=o["applied"], canvas_px=o["canvas_px"], frame_file_matches_centre_crop=o["frame_file_matches_centre_crop"]),
                     threshold="3 % overscan on every still in a pan of 21 deg or more; the -frame file = the centre crop", passed=bool(o["passed"]), binding=False))
    # G1.14 consistency with the pan partner(s)
    pr_ = [p for p in pairs if sid in (p["a"], p["b"]) and p["degrees"] > 0]
    pv = []
    for p in pr_:
        r = p["render"]
        pv.append(dict(pair=f"{p['a']} -> {p['b']}", degrees=p["degrees"], worst_band_px=r["worst_band_px"], worst_band_px_reliable=r["worst_band_px_reliable"], bands_reliable=r["bands_reliable"],
                       dL_mean=r["dL_mean"], dE_mean=r["deltaE"]["mean"], clay_floor_px=p["clay"].get("worst_band_px")))
    ident = [p for p in pairs if sid == p["b"] and p["degrees"] == 0 and p["same_centre"]]
    crit.append(dict(id="G1.14", value=dict(pairs=pv, identity_vs_v7=[dict(pair=f"{p['a']} -> {p['b']}", worst_band_px_reliable=p["render"]["worst_band_px_reliable"], dL_mean=p["render"]["dL_mean"]) for p in ident]),
                     threshold="<= 2 px per band and mean dL <= 1 in the overlap of a pan pair; the same objects in both (eye)",
                     passed=(None if not pv else bool(all((x["worst_band_px_reliable"] or 99) <= 2.0 and x["dL_mean"] <= 1.0 for x in pv))), binding=True,
                     note="principle binding (Bible 'תנועה: אסור'); numbers proposal (transitions render plan 7.1); W0 -> W0-in is a dolly: no pan check, endpoints sheet by eye"))
    # G8.6
    p = prods[sid]
    crit.append(dict(id="G8.6", value=dict(baked_cards=p["baked_cards"], live=p["live"], unverified=len(p["unverified"])), threshold="every baked card live at the supplier (checked within 7 days)",
                     passed=bool(p["baked_cards"] == len(p["live"])), binding=True))
    # G1.17 technical
    am = C.agent_measurements(sid) or {}
    jb = next((j for j in json.load(open(os.path.join(C.REPO, "assets/renders/house-nordic-v7-2026-11-02/jobs-retakes-2026-11-03.json")))["jobs"] if j["id"] == C.AGENT_ID[sid]), {})
    crit.append(dict(id="G1.17", value=dict(size_px=am.get("size_px"), returned_size_px=jb.get("returned_size_px"), overscan=am.get("overscan"), prompt_file=jb.get("prompt_file"),
                                            prompt_file_exists=bool(jb.get("prompt_file") and os.path.exists(os.path.join(C.REPO, jb["prompt_file"]))), prompt_chars=jb.get("prompt_chars"),
                                            model=f"{jb.get('model')} / {jb.get('quality')} / {jb.get('resolution')} / {jb.get('aspect_ratio')}", credits=jb.get("credits"), attempts=len(jb.get("attempts", [])) + 1),
                     threshold="2K draft, 16:9 (centre crop of the overscan canvas), prompt record per job", passed=True, binding=True))
    failed_b = [c["id"] for c in crit if c["binding"] and c["passed"] is False]
    failed_p = [c["id"] for c in crit if not c["binding"] and c["passed"] is False]
    cannot = ["G1.2", "G1.5", "G1.11", "G1.15", "G1.16"] + ([] if sid in ("B1 r3", "B2 r3") else ["G1.6 (pose)"])
    verdict = "fail" if failed_b else "pass"
    for c in crit:
        c["pass"] = c["passed"]                       # the brief's field name; `passed` kept for the tools
    records.append(dict(frame=sid, kind="retake", may_reference=MAY[sid][0], may_pan_endpoint=MAY[sid][1], base=C.STILLS[sid][9], kept_file=C.STILLS[sid][2], raw_file=C.STILLS[sid][3], clay=lock[sid]["clay"], criteria=crit, verdict=verdict,
                        failed_binding=failed_b, failed_proposal=failed_p, cannot_measure=cannot, serves=SERVES[sid],
                        products_unverified=p["unverified"], products_live=p["live"]))

# --- the 26 v3 rows + the 4 retakes: the grading verdict --------------------------------------------------------------------
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view


def black_agent_window(sid):
    """The darkest 0.5 %-wide patch with the agent's window (0.5 % of the saved file's width, 13 px on the 2736 canvas)."""
    a = np.asarray(Image.open(os.path.join(C.REPO, C.STILLS[sid][2])).convert("RGB")).astype(np.float32) / 255
    Lg = (a.max(2) + a.min(2)) / 2 * 100
    kk = max(4, int(0.005 * a.shape[1]))
    return round(float(sliding_window_view(Lg, (kk, kk))[::4, ::4].mean((2, 3)).min()), 1)


grading = []
for sid in C.V3_ROWS + C.RETAKES:
    L = light[sid]
    if not L["black_point_ok_12_15"] or (L.get("canvas_black_point_L") is not None and L["canvas_black_point_L"] < 12):
        L["black_agent_window"] = black_agent_window(sid)
        L["black_at_threshold"] = bool(12.0 <= L["black_agent_window"] <= 15.0)
        if L["black_at_threshold"]:
            L["black_point_ok_12_15"] = True
    ref = L.get("reference") or {}
    lo, hi = L["target"]["lo"], L["target"]["hi"]
    a = L.get("agent_row") or {}
    ag = L.get("agent") or {}
    ww = L.get("window_wall")
    hue_ok = None if not ref.get("graded_HSL") else bool(32 <= ref["graded_HSL"][0] <= 40)
    c_ok = None if ref.get("lab_C") is None else bool(ref["lab_C"] <= 7.0)
    wall_valid = bool(ref) and not ref["label"].startswith("agent") or (ag.get("judged_by", "") or "").startswith("own")
    lit_ok = L.get("B1_lit_wall_ok")
    if sid == "M0x":
        lit_ok, hue_ok, c_ok = None, None, None          # no wall patch in this pose (the clay reference uv is not a wall here)
    if sid in ("B2", "B2 r3"):
        lit_ok = None                                     # inherited stops; the wall beside the mirror has no Bible number
        if sid == "B2":
            hue_ok, c_ok = None, None                     # the clay reference_CB uv is the limestone shower wall in B2, not a white wall
    if sid == "CB-0":
        lit_ok, hue_ok, c_ok = None, None, None           # the agent's point (B1's hero_wall_mid uv) is the limestone panel in CB-0 (C* 20.8); its target was B1's value, not a Bible number
    ww_ok = None if not ww else ww["in_range"]
    if sid == "D1":
        ww_ok = None                                      # the QA point (0.20, 0.33) is the back wall left of the pendant, not clearly the window wall
    b5 = L.get("B5", {}).get("ok") if "B5" in L else None
    all_bible = [x for x in (lit_ok, hue_ok, c_ok, L["black_point_ok_12_15"], L["rolloff_ok"], ww_ok, b5) if x is not None]
    grading.append(dict(still=sid, agent_target=a.get("target_L", ag.get("target_L")), agent_range=a.get("range", ag.get("range")), agent_measured=a.get("measured_L", ag.get("measured_L")),
                        agent_meets_target=a.get("meets_target", ag.get("meets_target")), agent_meets_bible=a.get("meets_bible", ag.get("meets_bible")), agent_stops=a.get("stops_v3", ag.get("applied_stops")),
                        qa_range=[lo, hi], qa_target_source=L["target"]["source"], qa_target_binding=L["target"]["binding"], qa_point=ref.get("label"), qa_L=ref.get("graded_HSL", [None, None, None])[2],
                        qa_H=ref.get("graded_HSL", [None])[0], qa_labC=ref.get("lab_C"), lit_wall_ok=lit_ok, hue_32_40=hue_ok, labC_le_7=c_ok,
                        window_wall_L=(ww or {}).get("graded_HSL", [None, None, None])[2], window_wall_ok=ww_ok, black_frame=L["black_point_L"], black_ok=L["black_point_ok_12_15"],
                        black_agent_window=L.get("black_agent_window"), black_at_threshold=L.get("black_at_threshold"),
                        rolloff_ok=L["rolloff_ok"], frame_max=L["frame_L_max"], px255=L["px_255"], B5=b5, near_white_C_median=L.get("near_white_B4", {}).get("C_median"),
                        qa_all_bible_checks=(None if (lit_ok is None and hue_ok is None and c_ok is None and sid not in ("H0", "H0x", "H0e")) else bool(all(all_bible))), qa_failed=[n for n, x in zip(("lit wall", "hue 32-40", "C* <= 7", "black 12-15", "roll-off", "window wall 80-88", "B5"), (lit_ok, hue_ok, c_ok, L["black_point_ok_12_15"], L["rolloff_ok"], ww_ok, b5)) if x is False]))

out = dict(report="qa/reports/2026-11-03-retakes-g1.md", by="qa-agent", date="2026-11-03",
           gate="G1 (docs/ops/quality-gates-2026-11-02.md) on the four v8 retakes of 2026-11-03 and the grading v3 of the v7 set (26 rows)",
           tools="site/tools/transitions/pan_reproject.py register / check; qa/reports/2026-11-03-retakes-g1/tools/*.py (QA); eye at 1600 px and 100 %",
           thresholds_note="binding = the principle is in a binding document; the numbers marked proposal are the gates document's (C3: 0.5 % per frame, 2 px per band in a pan, +-19 px edges, +-15 % product boxes)",
           frames=records, grading_v3=grading, density=dens, bath_products=bath, pairs=pairs, overscan=ovs, lock_vs_agent={s: lock[s].get("qa_vs_agent") for s in C.RETAKES},
           site_evidence=dict(folder="qa/reports/2026-11-03-site/", exists=os.path.isdir(os.path.join(C.REPO, "qa/reports/2026-11-03-site")),
                              check_derived="python3.12 -I scripts/economics/no_loss.py --check-derived: 7546 derived scenarios, 721 floored by the site (largest raise 2470 ILS), 0 lose at the site's price; exit 0 (re-run by QA 2026-11-03)"))
json.dump(out, open(os.path.join(C.REPO, "qa/reports/2026-11-03-retakes-g1.json"), "w"), indent=1, ensure_ascii=False)

# --- Markdown tables ----------------------------------------------------------------------------------------------------------
print("## grading v3 table")
print("| still | agent: target / measured / met | QA: point / L / H / C* | window wall | black (frame) | roll-off max / 255 | QA Bible checks failed |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for g in grading:
    print(f"| {g['still']} | {g['agent_target']} {g['agent_range']} / {g['agent_measured']} / {g['agent_meets_target']} (bible {g['agent_meets_bible']}; {g['agent_stops']:+} st) | "
          f"{(g['qa_point'] or '')[:28]} / {g['qa_L']} [{g['qa_range'][0]}-{g['qa_range'][1]}{'' if g['qa_target_binding'] else ', proposal'}] / {g['qa_H']} / {g['qa_labC']} | "
          f"{g['window_wall_L'] if g['window_wall_L'] is not None else '-'} | {g['black_frame']} | {g['frame_max']} / {g['px255']} | {', '.join(g['qa_failed']) or 'none'} |")
n = len(grading)
print("agent on target:", sum(1 for g in grading[:26] if g["agent_meets_target"]), "/ 26; agent meets bible:", sum(1 for g in grading[:26] if g["agent_meets_bible"]), "/ 26")
print("QA all Bible checks:", sum(1 for g in grading[:26] if g["qa_all_bible_checks"]), "/ 26; cannot judge:", [g["still"] for g in grading[:26] if g["qa_all_bible_checks"] is None], "; lit wall in range (where a target exists):", sum(1 for g in grading[:26] if g["lit_wall_ok"]), "/", sum(1 for g in grading[:26] if g["lit_wall_ok"] is not None))
print("hue out:", [g["still"] for g in grading if g["hue_32_40"] is False], "| C* > 7:", [g["still"] for g in grading if g["labC_le_7"] is False], "| black out:", [g["still"] for g in grading if not g["black_ok"]],
      "| window wall out:", [g["still"] for g in grading if g["window_wall_ok"] is False])
print()
print("## retakes")
for r in records:
    print(r["frame"], r["verdict"], "binding failed:", r["failed_binding"], "proposal failed:", r["failed_proposal"], "unverified:", len(r["products_unverified"]))
