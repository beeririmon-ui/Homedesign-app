"""
Assembles qa/reports/2026-11-04-retakes-fixes-g1.json (the 11-03 record shape: one record per fix with frame, criteria[] (id, value,
threshold, pass, binding), verdict, may_reference, may_pan_endpoint, products_unverified[]; plus grading_v4[] for the 30 rows,
disputes, pairs, c0_s1, halos) from data/, and prints the grading table. Eye verdicts (G1.12 at 100 %, G1.1) by qa-agent, 2026-11-04,
on the graded-fix-v4 stills at 100-200 % (overlays/box-*.jpg and the crops listed in the report).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

D = os.path.join(C.OUT, "data")
J = lambda n: json.load(open(os.path.join(D, n)))  # noqa: E731
P3 = json.load(open(os.path.join(C.REPO, "qa/reports/2026-11-03-retakes-g1/data/products.json")))
DENS3 = json.load(open(os.path.join(C.REPO, "qa/reports/2026-11-03-retakes-g1/data/density.json")))
disp, pairs, fid, c0s1 = J("disputes.json"), J("pairs.json"), J("fidelity.json"), J("c0-s1.json")
light = {s: J(f"light-{C.fn(s)}.json") for s in C.V4_ROWS}
lock = {s: J(f"lock-{C.fn(s)}.json") for s in C.FIX_IDS}

NAMED = {  # QA's named lines on the -fix.png, paired by position (tools/disputes.py, edges peaks; px at 1920 x 1080)
    "B1 r3 fix": {"all 10 named lines (glazing 4, ledge, WC block 3, corner, vanity)": "0 / +-1 (cross-correlation, r 0.65-0.99)"},
    "B2 r3 fix": {"vanity top": -7, "mirror bottom": -8, "niche top": -7, "mirror left / right": "+6 / +4", "mirror head per column (x 1090-1540)": "-1 to -3",
                  "vanity right outer edge (clay 1584/1591, fix 1595)": "+4", "vanity left": 0, "curtain outer edge": -2},
    "K-girl-0 r2 fix": {"ledges (3 lines)": "-1 to -3", "band top": -1, "desk top": "+2", "desk-wall skirting": "+4", "room corner": "+2", "desk legs": "-3 / -1",
                        "bed foot top": "+11", "bed foot right edge": -3},
    "W0-in r2 fix": {"desk front face bottom (right / left of the chair)": "-4 / -2", "drawer bottom": -3, "chair back top (clay 835)": -3,
                     "chair back left / right": "0 / -8", "desk outer left / right": "-2 / -4", "slab top-front": "-3"},
}
EYE = {
    "B1 r3 fix": dict(
        fidelity=dict(deviations=["toilet brush: height now 0.99 of its box and the holder 0.90 of its width, but the silhouette is still not the card's: holder 64 % of the height and handle 36 %, the card a short 14.5 cm holder and a 25 cm handle (holder 38 %)"],
                      ok=["the seagrass basket on the floor: 0.90 x 1.10 of the clay pot, its bottom 3 px above the pot box's bottom; the plinth gone", "the fern sage (H 56, S 13); its top about 0.65 m (the clay's about 1.2 m; filler, inside the slot's max 120)"]),
        forbidden=dict(violations=["fill artefact on the linen curtain above and beside the fern: blocky rectangular light / dark patches from the column copy (canvas about x 1440-1640, y 660-940; u 0.53-0.60, v 0.43-0.61), visible at 100 % and at 200 %"],
                       ok=["the wall, skirting and floor where the plinth and the old brush were: clean at 100 %", "the brush's contact shadow and the basket's floor shadow read naturally"])),
    "B2 r3 fix": dict(
        fidelity=dict(deviations=[],
                      ok=["the planter basket 0.98 x 1.03 of the clay pot (was 1.18)", "the storage basket inside its box +-15 % (about 1.02 x 1.05, shifted right about 12 % of the box): QA's 11-03 'about 1.25x' was the extent estimate catching the towels and the shelf; do not shrink it x0.80 in the paid pass",
                            "towel ring about 1.25x the box width (G1.3 proposal, borderline; unchanged)", "vanity 1.006 and mirror 0.996-1.02 wide: on the clay (the 11-03 vanity / mirror-head findings withdrawn, section 4)"]),
        forbidden=dict(violations=["fill artefacts round the planter: a pale rectangle with hard edges on the white wall above-left of the fronds; blocky pale patches on the limestone panel's base right of the fronds; a pale sliver along the basket's floor contact (render-agent lists two of them as residual seams)"],
                       ok=["the reflected curtain hook in the mirror's top-left corner removed; the mirror shows wall only at 100 %"])),
    "K-girl-0 r2 fix": dict(
        fidelity=dict(deviations=[],
                      ok=["the two framed prints 0.98 x 1.00 of their clay box (were 1.5 x 1.55)", "the bunny doll 1.06-1.11 of its box height with the ears (the K-girl master's 1.12; the proxy is a thin cylinder, so the width is not the measure)"]),
        forbidden=dict(violations=[], ok=["the wall behind the old prints and the doll: no seam, line or rim at 100 % (the band line continues)"])),
    "W0-in r2 fix": dict(
        fidelity=dict(deviations=[],
                      ok=["the pen cup body about 1.10 x 0.84 of its box = about 8.8 x 11 cm, the card's 8 x 11 (the clay proxy is 13 cm tall); G1.3 height at the -15 % edge", "desk, drawer, chair and the floor objects on the clay lines (section 3)"]),
        forbidden=dict(violations=["fill artefacts where the plant layer was put back over the warped desk area: a band of dark / green pixel blocks in the seagrass basket's upper weave (the stems showing through), and a dark rectangle with a hard edge on the skirting / floor right of the basket's base (u 0.12-0.16, v 0.92-1.00)"],
                       ok=["the cup, the desk, the wall above row 640 and the right corner: clean at 100 %"])),
}
MAY = {
    "B1 r3 fix": ("yes, for geometry: the first still of the v7/v8 set that passes G1.4 in full on QA's numbers (named lines 0/+-1, bands <= 0.8 px); as an image, after the curtain fill is redone",
                  "T-CBath (as the source of a re-composed CB-0) and P-B: after the curtain fill is redone (the patch lies in both overlaps)"),
    "B2 r3 fix": ("no: global scale +0.64 / +0.74 % and fill artefacts round the planter", "no: P-B 14.2 px against B1 r3 fix (the relative scale of the two)"),
    "K-girl-0 r2 fix": ("after a global vertical affine (about -0.9 %, 0 tokens): every named line is within +-11 px", "not yet: T-CGirl also needs the K-girl master on its clay (-20.5 px, -1.9 % vertical)"),
    "W0-in r2 fix": ("yes for geometry (video endpoint: shift 0.1 / -0.4 px, scale 0.0 %, residual <= 7.7 px, named lines <= 8 px); as an image after the basket / floor patch is cleaned",
                     "V4 / T-HW video endpoint after the basket / floor patch is cleaned (no pan rule applies)"),
}
PAN = {"W0-in r2 fix": False, "K-girl-0 r2 fix": True, "B1 r3 fix": True, "B2 r3 fix": True}

records = []
for sid in C.FIX_IDS:
    k = lock[sid]
    s, v = k["after"]["summary"], k["after"]["verdict"]
    pan = PAN[sid]
    bands_g = [max(abs(b["dx_px"]), abs(b["dy_px"])) for b in k["after"]["check_registered"]["bands"] if b["response"] >= 0.10]
    tiles_g = [max(abs(t["dx_px"]), abs(t["dy_px"])) for t in k["after"]["tiles_ecc_registered"] if t.get("rho") is not None and t["rho"] >= 0.30]
    resid_g = max(bands_g + tiles_g) if (bands_g or tiles_g) else None
    g_ok = max(abs(x) for x in s["register_shift_px"]) <= 9.6 and max(abs(x) for x in s["register_scale_pct"]) <= 0.5
    lim = 2.0 if pan else 9.6
    crit = []
    crit.append(dict(id="G1.4", binding=True,
                     value=dict(register_shift_px=s["register_shift_px"], register_scale_pct=s["register_scale_pct"], masked_register=k["after_masked_register"],
                                residual_gated=dict(bands_response_ge_0_10=[round(x, 2) for x in bands_g], tiles_rho_ge_0_30=[round(x, 2) for x in tiles_g], worst=round(resid_g, 2) if resid_g is not None else None),
                                residual_ungated=dict(band=s["worst_band_px_after_register"], tile=s["worst_tile_ecc_px_after_register"]),
                                named_lines_px=NAMED[sid], agent_lock_fix=k.get("agent_lock_fix"), before_fix=dict(shift=k["before"]["summary"]["register_shift_px"], scale_pct=k["before"]["summary"]["register_scale_pct"])),
                     threshold=f"register shift <= 9.6 px and scale within 0.5 %; residual after register <= {lim} px per band / tile with shared structure (response >= 0.10, rho >= 0.30: QA's 11-03 recommendation, adopted by lock_v2 v3); named lines within +-19 px",
                     **{"pass": bool(g_ok and resid_g is not None and resid_g <= lim)}))
    crit.append(dict(id="G1.3", binding=False, value=dict(xcorr_ratios=s["xcorr_ratios"], named_lines_px=NAMED[sid]), threshold="fixed edges +-19 px, width / height 0.95-1.05; products in their box +-15 %",
                     **{"pass": bool(all(0.95 <= r <= 1.05 for kk, r in s["xcorr_ratios"].items() if "shower fittings" not in kk and "built-in oak desk" not in kk))}))
    crit.append(dict(id="G1.1", binding=True, value=EYE[sid]["fidelity"], threshold="every product the card's SKU: silhouette, count, pattern, material; 0 deviations", **{"pass": not EYE[sid]["fidelity"]["deviations"]}))
    crit.append(dict(id="G1.12", binding=True, value=EYE[sid]["forbidden"], threshold="0 violations at 100 % (Bible 'אסור'; seams, halos, fill artefacts of the code edits)", **{"pass": not EYE[sid]["forbidden"]["violations"]}))
    L = light[sid]
    ref = L.get("reference") or {}
    lit = L.get("lit_wall_ok")
    crit.append(dict(id="G1.7-G1.9 (grading v4)", binding=True,
                     value=dict(point=ref.get("label"), graded_HSL=ref.get("graded_HSL"), lab_C=ref.get("lab_C"), black=L["black_point_L"], frame_max=L["frame_L_max"], px_255=L["px_255"],
                                agent=(L.get("agent") or {}).get("measured_L"), judgeable=L["judgeable"]),
                     threshold="lit wall in its Bible range, wall H 32-40, C* <= 7, black 12-15, max <= 97, no 255",
                     **{"pass": (None if not L["judgeable"] else bool(lit is not False and L.get("hue_ok") and L.get("C_ok") and L["black_ok"] and L["rolloff_ok"]))}))
    pp = [p for p in pairs if sid in (p["a"], p["b"])]
    crit.append(dict(id="G1.14", binding=True, value=[dict(pair=f"{p['a']} -> {p['b']}", degrees=p["degrees"], worst_band_px_reliable=p["render"]["worst_band_px_reliable"],
                                                           bands_reliable=p["render"]["bands_reliable"], dL=p["render"]["dL_mean"], clay_floor=p["clay"]["worst_band_px"]) for p in pp]
                     or "W0 -> W0-in is a dolly: sheet by eye (overlays/endpoints-W0_fix-W0-in_r2_fix.jpg): the same objects",
                     threshold="<= 2 px per band and mean dL <= 1 in a pan pair's overlap; the same objects", **{"pass": (None if not pp else bool(all((p["render"]["worst_band_px_reliable"] or 99) <= 2 and p["render"]["dL_mean"] <= 1 for p in pp)))}))
    base = C.FIXES[sid][10]
    if base in DENS3 and "test_rule" in DENS3[base]:
        crit.append(dict(id="G1.6", binding=True, value=dict(test_rule=DENS3[base]["test_rule"]["passed"], sourcing_tasks=DENS3[base]["test_rule"]["sourcing_tasks"]),
                         threshold="studio rules 2.11: every slot with an approved product filled (unchanged by the fix)", **{"pass": DENS3[base]["test_rule"]["passed"]}))
    pr_ = P3[base]
    crit.append(dict(id="G8.6", binding=True, value=dict(baked=pr_["baked_cards"], live=pr_["live"], unverified=len(pr_["unverified"])), threshold="every baked card live at the supplier", **{"pass": pr_["baked_cards"] == len(pr_["live"])}))
    fb = [c["id"] for c in crit if c["binding"] and c["pass"] is False]
    frame_fb = [x for x in fb if x != "G8.6"]
    records.append(dict(frame=sid, kind="code fix 2026-11-04", fix_file=C.FIXES[sid][3], graded=C.FIXES[sid][2], criteria=crit, verdict="fail" if fb else "pass",
                        failed_binding=fb, failed_in_the_frame=frame_fb, failed_proposal=[c["id"] for c in crit if not c["binding"] and c["pass"] is False],
                        cannot_measure=["G1.2", "G1.5", "G1.11", "G1.15", "G1.16"], may_reference=MAY[sid][0], may_pan_endpoint=MAY[sid][1],
                        products_unverified=pr_["unverified"], products_live=pr_["live"]))

# grading v4: QA's checks per row
grading = []
for sid in C.V4_ROWS:
    L = light[sid]
    ref = L.get("reference") or {}
    a = L.get("agent_row") or {}
    judge = L["judgeable"]
    hue_ok, c_ok, lit = L.get("hue_ok"), L.get("C_ok"), L.get("lit_wall_ok")
    if sid in ("B2", "B2 r3 fix"):          # L not judged (inherited stops, no Bible number); H and C* at the agent's white-wall point (beside the mirror)
        p0 = L["points"][0]
        hue_ok, c_ok, judge = bool(32 <= p0["graded_HSL"][0] <= 40), bool(p0["lab_C"] <= 7.0), True
        ref = p0
    ww = L.get("window_wall")
    ww_ok = None if (not ww or sid == "D1") else ww["in_range"]
    b5 = L.get("B5", {}).get("ok") if "B5" in L else None
    checks = dict(lit_wall=lit, hue_32_40=hue_ok, C_le_7=c_ok, window_wall=ww_ok, black=L["black_ok"], rolloff=L["rolloff_ok"], B5=b5)
    vals = [x for x in checks.values() if x is not None]
    halo_n = sum(h["halo"] for h in L.get("halos", [])) if "halos" in L else None
    grading.append(dict(still=sid, agent=dict(L=a.get("L"), H=a.get("H"), C=a.get("C"), meets=a.get("meets"), fails=a.get("fails"), corrected=a.get("corrected"), stops=a.get("stops")),
                        qa=dict(point=ref.get("label"), L=ref.get("graded_HSL", [None] * 3)[2], H=ref.get("graded_HSL", [None])[0], C=ref.get("lab_C"),
                                window_wall=(ww or {}).get("graded_HSL", [None] * 3)[2] if ww_ok is not None else None, black=L["black_point_L"], frame_max=L["frame_L_max"], px255=L["px_255"]),
                        target=L["target"], checks=checks, halo_boxes=halo_n,
                        verdict=("cannot judge" if not judge else ("pass" if all(vals) else "fail")), failed=[k for k, x in checks.items() if x is False]))

# the fixes' light criterion = their grading row (B2 r3 fix: H and C* judged at the agent's white-wall point, L not judged)
gv = {g["still"]: g for g in grading}
for r in records:
    for c in r["criteria"]:
        if c["id"].startswith("G1.7"):
            g = gv[r["frame"]]
            c["pass"] = None if g["verdict"] == "cannot judge" else g["verdict"] == "pass"
            c["value"]["qa_checks"] = g["checks"]
    r["failed_binding"] = [c["id"] for c in r["criteria"] if c["binding"] and c["pass"] is False]
    r["failed_in_the_frame"] = [x for x in r["failed_binding"] if x != "G8.6"]
    r["verdict"] = "fail" if r["failed_binding"] else "pass"

out = dict(report="qa/reports/2026-11-04-retakes-fixes-g1.md", by="qa-agent", date="2026-11-04",
           gate="G1 (docs/ops/quality-gates-2026-11-02.md) on the four code fixes of 2026-11-04 and the grading v4 (30 rows), against Bible 1.8.3",
           tools="site/tools/transitions/pan_reproject.py register / check; qa/reports/2026-11-04-retakes-fixes-g1/tools/*.py (QA; the 11-03 tools imported, not edited); eye at 100-200 %",
           frames=records, grading_v4=grading,
           grading_v4_counts=dict(qa_pass=sum(g["verdict"] == "pass" for g in grading), qa_fail=sum(g["verdict"] == "fail" for g in grading), qa_cannot_judge=sum(g["verdict"] == "cannot judge" for g in grading),
                                  agent_pass=sum(1 for g in grading if g["agent"]["meets"])),
           disputes=disp, pairs=pairs, c0_s1=c0s1, fidelity=fid, objects=J("objects.json"),
           lock_vs_agent={s: lock[s].get("qa_vs_agent") for s in C.FIX_IDS})
json.dump(out, open(os.path.join(C.REPO, "qa/reports/2026-11-04-retakes-fixes-g1.json"), "w"), indent=1, ensure_ascii=False, default=float)
print(json.dumps(out["grading_v4_counts"]))
for g in grading:
    print(f"{g['still']:16s} agent {g['agent']['L']} H {g['agent']['H']} C {g['agent']['C']} meets {g['agent']['meets']} | QA L {g['qa']['L']} H {g['qa']['H']} C {g['qa']['C']} ww {g['qa']['window_wall']} black {g['qa']['black']} max {g['qa']['frame_max']} halos {g['halo_boxes']} -> {g['verdict']} {g['failed']}")
for r in records:
    print(r["frame"], r["verdict"], r["failed_binding"], r["failed_proposal"], [ (c["id"], c["pass"]) for c in r["criteria"]])
