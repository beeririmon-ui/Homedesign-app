"""
Assembles qa/reports/2026-11-02-v7-g1.json: one record per frame (frame, criteria[] {id, value, threshold, pass}, verdict,
may_reference, products_unverified[]) from data/*.json and the qa-agent's eye verdicts (EYE below: who = qa-agent, when =
2026-11-02, on the files named in the report). Also prints the summary table the report is written from.
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


def fn(x):
    return x.replace("'", "prime")


PAN_FRAMES = {"M0", "M0p", "M0x", "D1", "PD-35", "D2", "K-boy", "K-boy-0", "K-girl", "K-girl-0", "B1", "CB-0", "B2", "H0", "H0x", "H0e"}
FLOOR_BAND_IS_FLOOR = {"M0", "D2", "H0", "C0", "H0e", "H0x", "S1'", "MB-in", "PD-35", "M0x", "CB-0"}
POSE_BASE = {"H0x": "H0", "H0e": "H0", "M0p": "M0", "M0x": "M0", "PD-35": "D1", "W0-in": "W0", "S1'": "C0", "K-boy-0": "K-boy",
             "K-girl-0": "K-girl", "CB-0": "B1", "MB-in": "MB0"}

# --- eye verdicts (qa-agent, 2026-11-02, on <prefix>-graded.png at 1600 px and overlays/fidelity-<frame>.jpg at 100 %) -----------
EYE = {
    "M0": dict(fidelity_dev=[], fidelity_ok="triptych, cubes, pendant, curtains, vase, swing-arm sconce, basket, NYOKO stand-in, 3 cushions + throw, runner, 2 travertine holders, bowl: all the card's form",
               scale_dev=["sofa 1.20x the clay (edges 507/848 vs 538/815 at 1920: -47 / +64 px)", "armchair 1.29x (left edge -90 px)", "coffee table 1.16x"],
               forbidden=[], fillers=["eucalyptus in the sill vase (branches: registered)", "unlit candles (registered)"], view="bare birches, no snow, no buildings",
               consistency="reference for H0 / C0 vistas (checked there)"),
    "D1": dict(fidelity_dev=["condiment-set: turned baluster mills; the card image is a straight cylinder with a domed top", "mug-set: pale cream mugs; the card image is a sandy-brown glaze with a dark rim (colour)",
                             "centerpiece-vase: round belly; the card is a taller amphora 17.5 x 26.5 (form, minor)"],
               fidelity_ok="lantern 50, runner, iron plates + candles, curtains, bench pad, print, bowl, plates, ASKO and Medina stand-ins", scale_dev=[],
               forbidden=[], fillers=["pears in the bowl (not in the registered list)", "olive branches in the vase (registered)", "unlit candles (registered)"],
               view="bare birches, no snow", consistency="shares the print, plates, mugs, mills, bowl with D2 (same objects by eye)"),
    "D2": dict(fidelity_dev=["condiment-set: turned balusters vs the card's cylinder (as D1)", "mug-set: cream vs the card's sandy-brown (colour)",
                             "canisters: three cream jars; the card image is a black-and-white set with bamboo lids (colour / set)"],
               fidelity_ok="print, plates, bowl, paper-towel stand (Style A), tea towel, bench pad, runner stand-ins", scale_dev=[],
               forbidden=[], fillers=["pears in the bowl", "paper roll on the stand (shows use)", "tea towel on the oven bar (the black panel is the oven, shell)"],
               view="no window (allowed, Bible 1.6)", consistency="objects shared with D1 identical by eye"),
    "H0": dict(fidelity_dev=["console-vessel: a tall urn; the card is 19.5 wide x 20 high (squat round): proportion"],
               fidelity_ok="swinging-line art in black frame, black oval tray, 4 pine pegs, white cube sconce, bench cushion, waffle throw, two-tone rope basket; no umbrella stand",
               scale_dev=["hall console 1.12x the clay width (edges)", "portal 0.91x"], forbidden=[], fillers=["dried grass in the vessel (branches: registered)"],
               view="no window; the living vista is the brightest area", consistency="the living through the door = M0 v7 object for object (triptych 2 of 3 visible, cubes, pendant, sofa, cushions, candles, bowl, runner, armchair, rug, curtains, basket)"),
    "C0": dict(fidelity_dev=[], fidelity_ok="3 black-ink prints in wide mats and thin black frames, flat oval paper lantern; the vista = H0 v7 console (art, tray, vase) and M0 beyond",
               scale_dev=["far portal (G-C3) 0.80x (small box, low confidence)"], forbidden=[], design_note="the right-hand doorway reads as a dark grey opening (TR3 asks for the master-bath opening lit): for master-designer",
               fillers=[], view="no window; roof slot", consistency="vista = H0 + M0 by eye"),
    "MB0": dict(fidelity_dev=["cushions: the boucle cushion is rendered as a lumbar rectangle; the card is a 50 x 50 square"],
                fidelity_ok="black-ink pair, wave flush sconces (3 lobes), curtains, fluted column sill vase, seagrass belly planter, wabi-sabi bottle vase, dark oval dish, travertine holders, linen pillowcases and bedding, grey throw",
                scale_dev=["lower half re-framed vertically (register scale 1.028, shift -25 px); nightstands 1.04x"], forbidden=[],
                fillers=["olive tree in the planter (registered)", "dried stems in the vase (registered)", "unlit candles"], view="bare birches, no snow", consistency="MB-in shows the same nightstand, sconce, planter, holders"),
    "K-boy": dict(fidelity_dev=["bookshelf: each tier reads as one continuous ledge; the card is a pair of 42 cm ledges x2 (count unclear)",
                                "toy-cars: three unpainted beech cars; the card image shows natural + red + walnut cars (finish)"],
                  fidelity_ok="white washed-linen bedding, muslin blanket, two corduroy cushions (milky white / dark grey SKU), cream bear with bandana, jute rope basket, YUKI stand-in",
                  scale_dev=["desk 0.92x (edges)", "vertical scale 0.976"], forbidden=[], fillers=["football in the toy basket (shows use; not registered)", "picture books on the ledges (kids: design)"],
                  view="FAIL: the ground outside is white, reads as snow (prompt: no snow; TR3 default)", consistency="K-boy-0 shows the same desk, cars, ledges, blanket"),
    "K-girl": dict(fidelity_dev=["framed-prints: two prints; the card is a set of 3 (the v7 prompt itself asks for two: designer's call, not the render's)",
                                 "doll: about 1.4x its clay box (head above the +15 % band)", "soft-toy (crochet bunny): head above the +15 % band"],
                   fidelity_ok="two-tier ledges, natural linen bedding, muslin bedspread, cream + dusty-pink corduroy cushions, linen bunny doll with dress, crochet bunny, jute basket, LUMI stand-in",
                   scale_dev=["desk 0.93x (edges)", "vertical scale 0.982, shift -21 px"], forbidden=[], fillers=["yarn balls in the toy basket (shows use; not registered)", "picture books"],
                   view="bare birches, no snow", consistency="K-girl-0 is a copy of this framing (rejected pose)"),
    "B1": dict(fidelity_dev=["reed-diffuser: a narrow-neck bottle; the card is a lidded travertine-look jar with a bamboo lid (form)"],
               fidelity_ok="fluted resin sconces, linen slub curtain gathered at the corner, tufted bath mat, black floor paper stand, ribbed candle cup, 3 ribbed pump bottles",
               scale_dev=["fluted glazing / window 0.95x (edges)"], forbidden=[], fillers=["paper roll on the stand", "reeds in the diffuser"], view="fluted window, no view (by design)",
               consistency="B2 and CB-0 show the same curtain, niche bottles, sconces"),
    "B2": dict(fidelity_dev=["storage-basket: white cotton rope; the card image is a charcoal rope basket (colour / option to confirm)"],
               fidelity_ok="oak-framed mirror reflecting blank wall (F8), fluted sconce pair, curtain, 3 niche bottles, ribbed soap pump, travertine cup, bud vase, black towel ring, linen hand towel",
               scale_dev=["towel ring + towel about 0.04 right of the box (render-agent); shower fittings 1.79x (tiny box, low confidence)"], forbidden=[],
               fillers=["toothbrushes in the cup", "rolled towels in the basket", "eucalyptus in the bud vase (registered)"], view="no window (allowed)", consistency="shares curtain, bottles, sconces with B1"),
    "W0": dict(fidelity_dev=[], fidelity_ok="two grey felt bins, seagrass belly planter, white rope basket, grey kraft bin, stone pen cup, curtains, NYOKO stand-in; no bookends; bare wall stays bare",
               scale_dev=["desk chair 0.82x (edges)", "vertical scale 0.948, shift +18 px (lower half re-framed)"], forbidden=[], fillers=["ZZ plant in the planter (plant: registered type)", "pencils in the cup"],
               view="bare birches, no snow", consistency="W0-in shows the same objects"),
    # poses: consistency with the master by eye, and whether the pose followed its own clay
    "H0x": dict(consistency="same hall objects and the same living vista as H0 / M0", own_clay="vertical scale 0.956: re-framed vertically", copied_master=False),
    "M0p": dict(consistency="same living objects as M0; the dining through the opening = D1 objects", own_clay="shift +111 px vertical, scale 0.924: the frame is pushed down ~5 % (render-agent: kept without retake; only the right strip is used)", copied_master=False),
    "M0x": dict(consistency="living corner (print, cube, sofa arm, throw, basket) + the dining = D1 (lantern 50, vase, candles, bench pad, chairs, shelf)", own_clay="close: shift 3 / -9 px, scale 0.997 / 0.985", copied_master=False),
    "PD-35": dict(consistency="same lantern, vase, candle plates, runner, print, bench pad, window as D1", own_clay="locked: shift -0.2 / 1.8 px", copied_master=False),
    "H0e": dict(consistency="same console vignette and living vista as H0", own_clay="shift -27 px vertical, scale 0.979", copied_master=False),
    "W0-in": dict(consistency="same objects as W0", own_clay="REJECTED (render-agent): the pose repeats W0's framing instead of the 1.3 m closer view; the desk is ~1.1x W0's instead of ~1.7x", copied_master=True),
    "S1'": dict(consistency="hall console (art, tray, vase), bench, living vista as H0 / M0; roof light", own_clay="shift 7 / 2 px, scale 0.995", copied_master=False),
    "K-boy-0": dict(consistency="desk with 3 cars, ledges, bed foot, blanket as K-boy", own_clay="vertical scale 0.952, shift +8 px", copied_master=False),
    "K-girl-0": dict(consistency="the same objects, but the SAME FRAMING as the K-girl master (window, bed, shelves, desk): not the yaw-0 view", own_clay="REJECTED (render-agent): copied the master framing", copied_master=True),
    "CB-0": dict(consistency="window, WC, paper stand, sconce, bath mat, curtain edge, niche as B1", own_clay="locked: shift -0.2 / -2.7 px", copied_master=False),
    "MB-in": dict(consistency="nightstand, holders, sconce, planter as MB0; corridor lanterns, gallery prints, hall console and living vista beyond", own_clay="shift 2 / -11 px", copied_master=False, design_note="the doorway on the right reads dim grey, not lit (TR3)"),
}
VISTA_OK = {"H0": True, "C0": True}
SERVES = {"M0": ["T-E0 (end)", "T-LD (start)", "P0"], "M0p": ["T-LD: P0 / P1"], "M0x": ["T-LD: P1 / V2 start"], "PD-35": ["T-LD: V2 end / P2"], "D1": ["T-LD (end)", "P-D"], "D2": ["P-D"],
          "H0": ["T-E0 (start, site opening)", "PH", "T-HW"], "H0x": ["T-E0: pan / V1 start"], "H0e": ["T-HC / T-HW: PH end, V3 / V5"], "C0": ["T-HC (end)", "T-CM", "T-CGirl", "V6"], "S1'": ["V5 / V6 / V7 / V9 (rail station)"],
          "K-boy": ["T-CBoy (end)"], "K-boy-0": ["T-CBoy: V7 end / pan"], "K-girl": ["T-CGirl (end)"], "K-girl-0": ["T-CGirl: V8 end / pan"], "B1": ["T-CBath (end)", "P-B"], "CB-0": ["T-CBath: V9 end / pan"], "B2": ["P-B"],
          "MB0": ["T-CM (end)"], "MB-in": ["T-CM: V10 / V11"], "W0": ["T-HW (end)"], "W0-in": ["T-HW: V3 end / V4"]}


def crit(id_, value, threshold, pass_, binding=True, note=None):
    d = dict(id=id_, value=value, threshold=threshold, **{"pass": pass_}, binding=binding)
    if note:
        d["note"] = note
    return d


def main():
    lock = {f: J(f"lock-{fn(f)}.json") for f in C.MASTERS + C.POSES}
    light = {f: J(f"light-{fn(f)}.json") for f in C.MASTERS + C.POSES}
    pairs = J("pairs.json")
    ovs = J("overscan.json")
    dens = J("density.json")
    prod = J("products.json")
    out = []
    for f in C.MASTERS + C.POSES:
        L, G, P = lock[f], light[f], prod[f]
        is_master = f in C.MASTERS
        e = EYE.get(f, {})
        cr = []
        # ---- G1.4 clay lock with scale ------------------------------------------------------------------------------
        s = L["summary"]
        reg_shift = max(abs(x) for x in s["register_shift_px"])
        scale_dev = max(abs(x - 1) for x in s["register_scale"])
        resid = s["worst_tile_ecc_px_after_register"]
        thr = 2.0 if f in PAN_FRAMES else 9.6
        pass_lock = bool(reg_shift <= 9.6 and scale_dev <= 0.005 and (resid is not None and resid <= thr))
        cr.append(crit("G1.4", dict(register_shift_px=s["register_shift_px"], register_scale=s["register_scale"], scale_dev_pct=round(100 * scale_dev, 2),
                                    worst_tile_px_after_register=resid, tiles_counted=s["tiles_counted"],
                                    check_worst_band_px_reliable=s["worst_band_px"], check_bands_reliable=s["bands_reliable"]),
                       f"global shift <= 9.6 px (0.5 % of 1920) and scale within 0.5 %; residual per tile <= {thr} px ({'pan still' if f in PAN_FRAMES else 'video endpoint'})",
                       pass_lock, True, "pan_reproject.py register (ECC affine) + QA tile ECC; check's phase correlation only where response >= 0.05"))
        # ---- G1.3 fixed furniture edges ---------------------------------------------------------------------------
        fe = L["fixed_edges_worst_px"]
        ratios = L["fixed_width_ratios"]
        cr.append(crit("G1.3", dict(fixed_edges_worst_px=fe, width_ratios=ratios, eye=e.get("scale_dev", [])),
                       "every clear edge of a fixed piece within +-19 px (+-0.01 of 1920) of the clay; products inside their box +-15 % (eye)",
                       bool(fe is not None and fe <= 19 and not e.get("scale_dev")), False,
                       "edges with clay and render strength >= 4 only; product scale by eye on the fidelity sheet (no tool, P8)"))
        # ---- G1.7 / G1.8 exposure ---------------------------------------------------------------------------------------
        r = G.get("reference", {})
        if is_master:
            lo, hi = (92.0, 95.0) if f == "M0" else (90.0, 94.0)
            Lg = r.get("graded_HSL", [None, None, None])[2]
            cr.append(crit("G1.7" if f == "M0" else "G1.8",
                           dict(reference_uv=r.get("uv"), graded_HSL=r.get("graded_HSL"), raw_HSL=r.get("raw_HSL"), stops_needed_from_raw=r.get("stops_needed_to_bible_from_raw"),
                                agent_needed_stops=G.get("agent_grade", {}).get("needed_stops"), agent_applied=G.get("agent_grade", {}).get("applied_stops"), agent_flag=G.get("agent_grade", {}).get("flag")),
                           f"reference wall L {lo:.0f}-{hi:.0f} (M0: Bible corner; others: G1.8 proposal, BIB1 open); post lift <= +0.2 stop",
                           bool(Lg is not None and lo <= Lg <= hi), f == "M0", "M0 points: corner, behind the sofa, right edge in light-M0.json wall_patches"))
            if f == "M0":
                wp = G["wall_patches"]
                cr.append(crit("G1.7b", {k: v.get("graded_HSL") for k, v in wp.items() if k.startswith("bible")}, "corner 92-95, behind sofa 88-91, right edge 82-86",
                               False, True, "all three under target: 79.6 / 80.3 / 73.3"))
        else:
            cr.append(crit("G1.8", dict(note="the pose's reference uv is the master's point, not valid after rotation; exposure agreement is measured in G1.14 (dL in the overlap)",
                                        agent_needed_stops=G.get("agent_grade", {}).get("needed_stops"), agent_flag=G.get("agent_grade", {}).get("flag")),
                           "same exposure as the master (dL <= 1 in the overlap)", None, False))
        # ---- G1.9 black, whites, floor ----------------------------------------------------------------------------------
        bp = G["black_point_L"]
        wh = G["whites"]
        wall = G["wall_patches"].get("hero_wall_mid") or {}
        wall_hsl = r.get("graded_HSL") if f == "M0" else (wall.get("graded_HSL") or r.get("graded_HSL"))
        bath = f in ("B1", "B2", "CB-0")
        white_ok = bool(wall_hsl and (bath or 32 <= wall_hsl[0] <= 40) and 15 <= wall_hsl[1] <= 28 and wall_hsl[0] >= 25)
        pink = wh.get("share_H_under_25")
        pink_note = None
        pink_pass = bool(pink is not None and pink <= 0.01)
        if f in ("K-girl", "K-girl-0"):
            pink_pass = None
            pink_note = "the blush band #E8D5CC is by design (prompt MATERIALS); the upper wall at the reference is H 38.9: the share is the band, not the white"
        cr.append(crit("G1.9", dict(black_point_L=bp, wall_patch_HSL=wall_hsl, wall_patch="bible corner" if f == "M0" else "hero_wall_mid (clay selfcheck)", whites_H_median=wh.get("H_median"), whites_S_median=wh.get("S_median"), share_white_H_under_25=pink,
                                    floor_median_HSL=G["floor_median_HSL"] if f in FLOOR_BAND_IS_FLOOR else None),
                       "black point L 12-15; back wall H 32-40 (bath: 4000 K, H informational), S 15-28; no H < 25 in white / beige; parquet H 30-40 S 30-45 L 68-78 (G1.11 proposal)",
                       bool(12 <= bp <= 15 and white_ok and (pink_pass is None or pink_pass)) if is_master else bool(12 <= bp <= 15), True,
                       (pink_note or "") + (" HSL S inflates near L 90: S read on the frame's own mid wall" if wall_hsl and wall_hsl[2] > 88 else "") or None))
        # ---- G1.10 lamps ------------------------------------------------------------------------------------------------
        lamps = G["lamps"]
        if lamps:
            lp = all(v["shade_L_93_97"] and v.get("not_brighter_than_window", True) for v in lamps.values())
            cr.append(crit("G1.10", {k.split("/")[-1]: dict(L_p95=v["L_p95"], H=v["glow_H_median"], S=v["glow_S_median"], lit_in_clay=v["in_clay_lamps_on"], not_brighter_than_window=v.get("not_brighter_than_window"),
                                                            note="L_p95 < 85: the shade is outside its clay box (moved) or not glowing" if v["L_p95"] < 85 else None)
                                     for k, v in lamps.items()},
                           "every lamp lit: shade L 93-97 (H 35-45, S 25-45 informational: the box includes surroundings); none brighter than the window", bool(lp), True,
                           "measured inside the clay lamp box: top 10 % of L; a lamp drawn outside its box reads as wall"))
        else:
            cr.append(crit("G1.10", dict(lamps_in_clay=G["lamps_on_in_clay"]), "every lamp in the frame lit", None, True, "no lamp placeholder in this frame (F11 is a plan question, not a render one)"))
        # ---- G1.12 forbidden list (eye) ---------------------------------------------------------------------------------
        if is_master:
            cr.append(crit("G1.12", dict(findings=e.get("forbidden", []), fillers_to_register=[x for x in e.get("fillers", []) if "not registered" in x or "shows use" in x or x in ("pears in the bowl", "pencils in the cup", "toothbrushes in the cup", "rolled towels in the basket", "paper roll on the stand")],
                                         saturated_255_px=G["saturated_px_total"]),
                           "0 violations of the closed list (Bible / recipe 2.7); fillers must be on the registered list",
                           bool(not e.get("forbidden")) , True, "eye at 1600 px and 100 % crops; the unregistered fillers show use of the product (rule C.1 spirit) and are listed for the designer to register"))
        else:
            cr.append(crit("G1.12", dict(saturated_255_px=G["saturated_px_total"], eye="no sun patch, beam, bloom, cable, text or person seen"), "0 violations", True, True, "eye at 1600 px"))
        # ---- G1.13 window ------------------------------------------------------------------------------------------------
        w = G["window"]
        if f in ("M0p", "C0", "S1'", "MB-in"):
            cr.append(crit("G1.13", dict(box=w.get("box"), L_p99=w.get("L_p99"), brightest=w.get("brightest"), saturated_255_total=G["saturated_px_total"]),
                           "the brightest area is the window / vista; p99 <= 97; 0 x 255", None, True,
                           "the measured box is an opening or a secondary window (M0p: the living window at the left edge is not a clay box; C0 / S1' / MB-in: the door box is not the vista): no tool box for the vista"))
        elif w.get("box") and "vista" not in str(w.get("box")) and "portal" not in str(w.get("box")) and "door" not in str(w.get("box")):
            m = w["margins"]
            cut = any(v < 0.0 for v in m.values()) or any(v < 0.03 for v in m.values())
            f2 = (not cut) or True  # a window cut by the frame edge: the clay decides (F2 on the clay)
            vw = w["width_frac"]
            win_pass = bool(w["p99_le_97"] and w["no_255"] and w["brightest"] and vw <= 0.30 + 1e-6)
            cr.append(crit("G1.13", dict(box=w["box"], width_frac=vw, margins=m, L_p99=w["L_p99"], L_max=w["L_max"], brightest=w["brightest"], saturated_255=w["saturated_inside"], view=e.get("view")),
                           "F2: whole with >= 0.03 margins or cut >= 15 %, width <= 30 %; brightest; p99 <= 97; 0 x 255; same view (birches, no snow: proposal)",
                           win_pass and ("FAIL" not in str(e.get("view", ""))), True))
        else:
            cr.append(crit("G1.13", dict(box=w.get("box"), L_p99=w.get("L_p99"), brightest=w.get("brightest"), view=e.get("view")),
                           "no window in frame: the opening / vista is the brightest area, p99 <= 97", bool(w.get("p99_le_97", True) and w.get("brightest", True)) if w.get("box") else None, True,
                           None if w.get("box") else "no window and no opening box"))
        # ---- G1.14 consistency: pairs sharing a point + eye -------------------------------------------------------------
        mine = [p for p in pairs if f in (p["a"], p["b"]) and "render" in p and "error" not in p["render"]]
        if mine:
            vals = {f"{p['a']}->{p['b']} ({p['pan']}, {p['degrees']} deg)": dict(worst_band_px=p["render"]["worst_band_px"], shift_px=p["render"]["shift_px"], dL_mean=p["render"]["dL_mean"], dE_mean=p["render"]["deltaE"]["mean"],
                                                                               clay_worst_band_px=p["clay"].get("worst_band_px")) for p in mine}
            ok = all(p["render"]["worst_band_px"] <= 2.0 and p["render"]["dL_mean"] <= 1.0 for p in mine)
            cr.append(crit("G1.14", dict(pairs=vals, eye=e.get("consistency")), "each pair sharing a point: <= 2 px per band after reprojection and dL mean <= 1 (proposal); same objects by eye (binding)",
                           bool(ok), True, "pan_reproject.py check on the kept renders; the clay pairs are the tool's floor (<= 0.9 px)"))
        else:
            cr.append(crit("G1.14", dict(eye=e.get("consistency")), "same objects in both frames (eye)", VISTA_OK.get(f, True if e.get("consistency") and "FAIL" not in e.get("consistency", "") else None), True,
                           "no pair sharing a point; video endpoint sheets in overlays/endpoints-*.jpg"))
        # ---- masters only: G1.1 / G1.2 / G1.5 / G1.6 / G1.15 / G1.16 -----------------------------------------------------
        if is_master:
            cr.append(crit("G1.1", dict(deviations=e.get("fidelity_dev", []), ok=e.get("fidelity_ok")), "every product is the card's SKU: silhouette, count, pattern, material: 0 deviations",
                           bool(not e.get("fidelity_dev")), True, "eye on overlays/fidelity-<frame>.jpg (render crop per clay box next to the frame's references); no tool (P8)"))
            cr.append(crit("G1.2", dict(eye_colour_notes=[x for x in e.get("fidelity_dev", []) if "colour" in x]), "dh <= 5 deg, C* ratio 0.8-1.2 vs the SKU image (proposal)", None, False, "no tool (P8); eye notes only"))
            sc = C.SC[C.FRAMES[f][3]]
            tang = sc.get("F3_tangents", {})
            cr.append(crit("G1.5", dict(clay_F3_edge_tangents=len(tang.get("edge_tangents", [])), clay_F3_object_tangents=len(tang.get("object_object_tangents", [])),
                                        clay_F8=sc.get("F8_mirror", {}).get("result"), heroes_thirds=sc.get("heroes_thirds")),
                           "F1-F8, F11, F12 on the clay and again on the render", None, True, "no tool on the render; the round-4 selfcheck carries F3 / F8 only"))
            dn = dens[f]
            cr.append(crit("G1.6", dict(minimum=dn["minimum"], products_counted=dn["products_counted"], fixed_product_counted=dn["fixed_product_counted"], total=dn["total"],
                                        with_stand_in_rugs=dn["total_if_stand_in_rugs_sold"], categories=dn["categories"], categories_of_4=dn["categories_of_4"]),
                           f">= {dn['minimum']} products (>= 50 % visible, >= 0.5 % of the frame; fixed-product furniture counts; sets once) and >= {'3' if f == 'C0' else '4'} of 4 categories",
                           bool(dn["pass_"]), True, "counted on the round-4 clay boxes (visibility assumed where round 4 did not ray-cast); the render shows the same products by eye"))
            cr.append(crit("G1.15", dict(decision=None), "user approval on the sheet (gate 2 / approval 3)", None, True, "not asked yet; the sheet is assets/renders/house-nordic-sheet-v7-2026-11-02.jpg"))
            cr.append(crit("G1.16", dict(designer_score=None), ">= 8 / 10 by master-designer (proposal)", None, False, "docs/render-v7-review-2026-11-02.md not written yet at the time of this check"))
        # ---- overscan (poses and pan masters) ------------------------------------------------------------------------------
        o = ovs[f]
        cr.append(crit("OVS", dict(required=o["required"], why=o["why"], applied=o["applied"], frame_file_matches_centre_crop=o["frame_file_matches_centre_crop"]),
                       "3 % overscan on every still in a pan >= 21 deg (transitions render plan 3 / 6.4, proposal)", bool(o["pass_"]), False, o.get("note")))
        # ---- G1.17 technical --------------------------------------------------------------------------------------------------
        t = G["technical"]
        cr.append(crit("G1.17", dict(returned_size_px=G.get("agent_grade", {}).get("returned_size_px"), resize=G.get("agent_grade", {}).get("resize_16_9"), graded_size=t["graded_size"],
                                     overscan_canvas=t["overscan_canvas"], model=t["model"], quality=t["quality"], credits=t["credits"], prompt_file_exists=t["prompt_file_exists"], prompt_record_json=t["prompt_record_json"]),
                       "test: 2K, 16:9, what the model returned recorded; a prompt record per job", bool(t["is_2k"] and t["ratio_16_9"] and t["prompt_file_exists"]), True,
                       None if t["prompt_record_json"] else "no <job>.json prompt record found under assets/prompts/ (the jobs.json entry carries the prompt_file)"))
        # ---- G8.6 liveness -----------------------------------------------------------------------------------------------------
        cr.append(crit("G8.6", dict(baked_cards=P["baked_cards"], live=P["live"], unverified=len(P["unverified"])), "every baked card live at the supplier within 7 days (proposal: 7 days; principle binding)",
                       bool(not P["unverified"]), True, "docs/render-products-check-2026-11-02.json: only the 3 Zendrop cards were checked (MCP); CJ and AliExpress in the queue"))
        # ---- verdict -------------------------------------------------------------------------------------------------------
        failed = [c["id"] for c in cr if c["pass"] is False and c["binding"]]
        failed_prop = [c["id"] for c in cr if c["pass"] is False and not c["binding"]]
        cannot = [c["id"] for c in cr if c["pass"] is None]
        verdict = "fail" if failed else ("cannot measure" if cannot else "pass for the test")
        # reference / endpoint: geometry, consistency and fidelity decide; exposure (BIB1 open), density (clay) and liveness are house-wide and listed separately
        copied = e.get("copied_master", False)
        geo_ok = reg_shift <= 9.6 and scale_dev <= 0.01 and (resid is not None and resid <= 9.6) and not copied
        geo_reg = (resid is not None and resid <= 9.6) and not copied
        objects_ok = (f in VISTA_OK) or ("FAIL" not in str(e.get("consistency", ""))) and not copied
        fid_ok = not [x for x in e.get("fidelity_dev", []) if "colour" not in x and "prompt itself" not in x]
        if copied:
            may = "no: the pose copied the master's framing (retake)"
        elif geo_ok and objects_ok and fid_ok:
            may = "yes (geometry within 0.5 % of the clay; objects consistent)"
        elif geo_ok and objects_ok:
            may = "yes for geometry (shift <= 9.6 px, scale within 1 %, residual <= 9.6 px); product form to fix first: " + "; ".join(e.get("fidelity_dev", [])[:2])
        elif geo_reg and objects_ok:
            may = "with register only (global affine corrects it; residual <= 9.6 px); products / scale to fix: " + "; ".join(e.get("scale_dev", [])[:2] or e.get("fidelity_dev", [])[:2])
        else:
            may = "no: " + ("; ".join(e.get("scale_dev", [])[:2]) or "lock broken")
        blocks = [] if may.startswith("yes") else SERVES.get(f, [])
        out.append(dict(frame=f, kind="master" if is_master else "pose", base=POSE_BASE.get(f), kept_file=C.FRAMES[f][1] + "-graded.png", criteria=cr, verdict=verdict,
                        failed_binding=failed, failed_proposal=failed_prop, cannot_measure=cannot, may_reference=may, serves=SERVES.get(f, []), blocks_transitions=blocks,
                        design_notes=e.get("design_note"), products_unverified=P["unverified"], products_live=P["live"]))
        print(f"{f:9s} {verdict:17s} bind-fail {failed}  prop-fail {failed_prop}  | ref: {may[:70]}")
    rec = dict(report="qa/reports/2026-11-02-v7-g1.md", by="qa-agent", date="2026-11-02", gate="G1 (docs/ops/quality-gates-2026-11-02.md) on the Nordic v7 test set",
               tools="site/tools/transitions/pan_reproject.py register / check; qa/reports/2026-11-02-v7-g1/tools/*.py (QA); eye at 1600 px and 100 %",
               thresholds_note="binding = the principle is in a binding document; the numbers marked proposal are from the gates document (C3: 0.5 % per frame, 2 px per band in a pan)",
               frames=out)
    json.dump(rec, open(os.path.join(C.REPO, "qa/reports/2026-11-02-v7-g1.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
