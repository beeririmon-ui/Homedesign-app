#!/usr/bin/env python3
"""
grade_cut_r7.py: the v3c layers of the warm-modern tool, phase 2, after R7 (render-agent, 2026-11-12).
Brief: briefs/render-wm-tool-r7-2026-11-12.md. NEW FILES ONLY: earlier files are read, never written; a layer or shadow whose
recomputed bytes equal an existing file keeps that file (each of the two on its own), anything else is written as <stem>-r7.png.

The same method as grade_cut_r6.py (ONE v3c grade, stack.Grade; every layer cut from the graded composites, never graded on its own;
the cushion sets kept byte for byte where the stack under them did not change), on the R7 sources (fix_r7.SRC7 / VSRC7):
  planter          section 8: k 0.78 in linear light on the pot's body
  curtains         section 6.3: 180502 at its sold 270 (hem Z 0.12; the stack rests on the bench top)
  candle-holders   section 1.5: the travertine pair moved in code to the 1.9.4 points (A with the pre-approved 9 cm lever), re-cut
  bowl             section 1.5: the black bowl moved in code to (0.62, 1.94) (POSITION PROVISIONAL: the clay's bowl x throw < 0.02)
and the variants, each cut on the SAME graded composite under its slot as the default:
  R6 (unchanged sources): framed-art-v2, accent-sconces-v2 / -v3, vase-v2, pendant-v2
  curtains-v2      554205 at its sold 270 (the same cut)
  6' (new)         bowl-v2 (white belly), candle-holders-v2 (ceramic trays), vase-v3 (white plum)
  7' (new)         curtains-v3 (Linen 200 x 260, its sold 260: hem Z 0.22)
  NOT layers       bowl-v3 and candle-holders-v3: the 7' render failed on size and place (work-r7/post-r7.json)
The shadow recipe is FROZEN (extract.shadow_one as every existing layer; the curtains' cut shadow is the designer's section 6.3 item 6).

Writes: layers/<slot>/...-r7.png (only where the bytes are new), layers/manifest-r7.json, graded/default-scene-r7-set-<X>-graded-v3c.png,
graded/variant-r7-<name>-set-B-graded-v3c.png (each variant's truth), layers/asset-manifest-entries-r7.json.
  python3 fix_r7.py all ; python3 pass_r7.py ... ; python3 post_r7.py p6|p7 ; python3 fix_r7.py curtains-v3 ;
  python3 grade_cut_r7.py ; python3 layers/verify_layers_r7.py ; python3 lock_r7.py ; python3 make_crops_r7.py
"""
import glob
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_r7 as F7  # noqa: E402
import pass_r7 as P7  # noqa: E402
import grade_cut as GC  # noqa: E402
import grade_cut_r3 as G3  # noqa: E402
import grade_cut_r12 as G12  # noqa: E402
import stack  # noqa: E402
from phase2_wm import P1  # noqa: E402

LAY, GRD, REPO = os.path.join(HERE, "layers"), os.path.join(HERE, "graded"), F7.W.REPO
F6 = F7.F6
ACCEPTED = list(F7.ACCEPTED)
FIX7 = ["planter", "curtains", "candle-holders", "bowl"]
CARDS = dict(F6.CARDS6)
VCARDS = dict(F6.VCARDS6)
VCARDS.update({"bowl-v2": P7.CARDS[("bowl", "v2")], "candle-holders-v2": P7.CARDS[("candle-holders", "v2")], "vase-v3": P7.CARDS[("vase", "v3")],
               "curtains-v3": P7.CARDS[("curtains", "v3")]})
VARIANTS = [("curtains", "curtains-v2"), ("curtains", "curtains-v3"), ("framed-art", "framed-art-v2"), ("accent-sconces", "accent-sconces-v2"),
            ("accent-sconces", "accent-sconces-v3"), ("vase", "vase-v2"), ("vase", "vase-v3"), ("pendant", "pendant-v2"),
            ("bowl", "bowl-v2"), ("candle-holders", "candle-holders-v2")]
NEW_IN_R7 = {"curtains-v2", "curtains-v3", "bowl-v2", "candle-holders-v2", "vase-v3"}
FIXREC = json.load(open(os.path.join(F7.WR7, "fix-r7.json")))
POSTREC = json.load(open(os.path.join(F7.WR7, "post-r7.json")))
FETCH = {p: json.load(open(os.path.join(F7.WR7, f"{p}-fetch.json"))) for p in ("p6", "p7")}
R6MAN = json.load(open(os.path.join(LAY, "manifest-r6.json")))
R6BY = {l_["id"]: l_ for l_ in R6MAN["layers"]}
R6VAR = {v["id"]: v for vs in R6MAN["variants"].values() for v in vs}
TG = json.load(open(os.path.join(HERE, "step0/r7-table-group/table-group-r7.json")))
LEV = json.load(open(os.path.join(HERE, "step0/r7-table-group/levers-r7.json")))
PASS7 = {"planter": "pass 5' + fix R7 (code: k 0.78 in linear light, section 8)",
         "curtains": "pass 4' (180502) + fix R7 (code: the sold 270, section 6.3)",
         "candle-holders": "steps 1-3 + fix R7 (code: re-cut, moved to the 1.9.4 points, section 1.5)",
         "bowl": "reserve R2 + fix R7 (code: moved to (0.62, 1.94), section 1.5)"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def same_file(d, arr, mode, stem=""):
    ps = sorted(glob.glob(os.path.join(d, "*.png")))
    for p in sorted(ps, key=lambda p_: (not os.path.basename(p_).startswith(stem), p_)):
        im = Image.open(p)
        if im.size != (arr.shape[1], arr.shape[0]) or im.mode != mode:
            continue
        a = np.asarray(im.convert(mode))
        if a.shape == arr.shape and np.array_equal(a, arr):
            return p
    return None


def write_or_reuse(d, stem, arr, mode):
    os.makedirs(d, exist_ok=True)
    found = same_file(d, arr, mode, stem)
    if found and "-r7" in os.path.basename(found):
        return found, "new -r7 file"
    if found:
        return found, "existing file, same bytes (" + os.path.basename(found) + ")"
    p = os.path.join(d, f"{stem}-r7{'-shadow' if mode == 'RGB' else ''}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    Image.fromarray(arr, mode).save(p, compress_level=9)
    return p, "new -r7 file"


def main():
    F7.use_r7_sources()
    G = stack.Grade()
    P = stack.base_parts()
    base8 = GC.u8(os.path.join(P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    assert sha(os.path.join(LAY, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
    results, regions, finals, cush_changed, pre = {}, {}, {}, {}, {}
    for s in "BAC":
        U, steps = F7.compose7(cushion_set=s)
        Aun = np.zeros(P["fa"].shape, np.float32)
        Cprev = base8.copy()
        appr = GC.u8(os.path.join(P1, f"composite-set-{s}-v3-graded-v3c.png"))
        for st in steps:
            k, reg = st["k"], st["region"]
            if s == "B":
                pre[k] = (Cprev.copy(), Aun.copy())
            Aun = np.maximum(Aun, st["a_eff"] if k != "cushions" else st["a"])
            Cg = G(st["U"], Aun).astype(np.float64)
            C = Cprev.copy()
            if k == "cushions":
                delta = reg & (np.abs(Cprev - base8).max(2) > 0)
                delta = cv2.dilate(delta.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & reg
                C[reg] = appr[reg]
                C[delta] = Cg[delta]
                cush_changed[s] = delta
            else:
                C[reg] = Cg[reg]
            a8 = np.clip(GC.rhu(st["a_eff"] * 255), 0, 255).astype(np.int32)
            r8 = np.clip(GC.rhu(st["Sh"] * 255), 0, 255).astype(np.float64)
            if k == "cushions":
                LA = np.asarray(Image.open(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png"))).copy()
                SA = np.asarray(Image.open(os.path.join(P1, f"layers-v3c/cushions-set-{s}-shadow.png")).convert("RGB")).copy()
                if delta.any():
                    a0 = np.where(delta, LA[..., 3].astype(np.int32), a8)
                    r = GC.cut(C, Cprev, a0, r8, reg)
                    LA[..., :3][delta] = r["L"][delta]
                    LA[..., 3][delta] = r["A"][delta]
                    SA[delta] = r["S"][delta]
                    st_ = dict(r["stats"], recut_px=int(delta.sum()), kept_approved_px=int((reg & ~delta).sum()))
                else:
                    st_ = dict(recut_px=0, kept_approved_px=int(reg.sum()))
                results[("cushions", s)] = dict(L=LA, S=SA, stats=st_)
            elif s == "B":
                r = GC.cut(C, Cprev, a8, r8, reg)
                if r["stats"]["stray_px"]:
                    raise SystemExit(f"{k}: {r['stats']['stray_px']} px change outside its region: stop")
                results[(k, None)] = dict(L=np.dstack([r["L"], r["A"]]), S=r["S"], stats=r["stats"])
            regions[(k, s)] = reg
            Cprev = C
        finals[s] = Cprev.astype(np.uint8)
        p = os.path.join(GRD, f"default-scene-r7-set-{s}-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(finals[s]).save(p, compress_level=6)
        print("scene", s, flush=True)
    vres, vreg = {}, {}
    for k, nm in VARIANTS:
        Uv, stv = F7.compose7(variants={k: nm})
        st = next(x for x in stv if x["k"] == k)
        Cprev, Aun0 = pre[k]
        Aun = np.maximum(Aun0, st["a_eff"])
        Cg = G(st["U"], Aun).astype(np.float64)
        reg = st["region"]
        C = Cprev.copy()
        C[reg] = Cg[reg]
        a8 = np.clip(GC.rhu(st["a_eff"] * 255), 0, 255).astype(np.int32)
        r8 = np.clip(GC.rhu(st["Sh"] * 255), 0, 255).astype(np.float64)
        r = GC.cut(C, Cprev, a8, r8, reg)
        if r["stats"]["stray_px"]:
            raise SystemExit(f"{nm}: {r['stats']['stray_px']} px change outside its region: stop")
        vres[nm] = dict(L=np.dstack([r["L"], r["A"]]), S=r["S"], stats=r["stats"], slot=k)
        vreg[nm] = reg
        T = finals["B"].astype(np.float64).copy()
        dreg = regions[(k, "B")]
        T[dreg] = Cprev[dreg]
        T[reg] = C[reg]
        p = os.path.join(GRD, f"variant-r7-{nm}-set-B-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(T.astype(np.uint8)).save(p, compress_level=6)
        print("variant", nm, flush=True)
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    cush_union = regions[("cushions", "A")] | regions[("cushions", "B")] | regions[("cushions", "C")]
    vabove = {nm: int((rg & cush_union).sum()) for nm, rg in vreg.items() if stack.ORDER.index(vres[nm]["slot"]) > stack.ORDER.index("cushions")}
    assert all(v == 0 for v in vabove.values()), f"a variant above the cushions overlaps a set: {vabove}"
    slot_union = {k: regions[(k, "B")].copy() for k in ACCEPTED}
    for nm, rg in vreg.items():
        slot_union[vres[nm]["slot"]] |= rg
    disjoint = {}
    for k in sorted({vres[nm]["slot"] for nm in vres}):
        for j in ACCEPTED:
            if j != k:
                n = int((slot_union[k] & slot_union[j]).sum())
                if n:
                    disjoint[f"{k} x {j}"] = n
        n = int((slot_union[k] & cush_union).sum())
        if n:
            disjoint[f"{k} x cushions"] = n
    files, origin = {}, {}
    for (k, s), r in results.items():
        d = os.path.join(LAY, "cushions" if k == "cushions" else k)
        stem = f"set-{s}" if k == "cushions" else CARDS[k][0]
        lp, lo = write_or_reuse(d, stem, r["L"], "RGBA")
        sp, so = write_or_reuse(d, stem, r["S"], "RGB")
        files[(k, s)] = (lp, sp)
        origin[f"{k}{'-' + s if s else ''}"] = dict(layer=lo, shadow=so)
    vfiles = {}
    for nm, r in vres.items():
        d = os.path.join(LAY, r["slot"])
        stem = VCARDS[nm][0]
        lp, lo = write_or_reuse(d, stem, r["L"], "RGBA")
        sp, so = write_or_reuse(d, stem, r["S"], "RGB")
        vfiles[nm] = (lp, sp)
        origin[nm] = dict(layer=lo, shadow=so)
    changed = sorted({k.split("-")[0] if k.startswith("cushions") else k for k, v in origin.items() if "new" in v["layer"] or "new" in v["shadow"]})
    unexpected = [k for k in changed if k not in FIX7 and k not in NEW_IN_R7]
    gaps = layer_gaps(vfiles, files)
    man = write_manifest(G, files, results, regions, cush_changed, overlap, origin, vres, vreg, vfiles, disjoint, unexpected, gaps)
    write_asset_entries(man, origin)
    print(json.dumps(dict(origin=origin, unexpected_changes=unexpected, disjoint_overlaps=disjoint, variant_vs_cushions=vabove, gaps=gaps,
                          variants={nm: dict(region_px=int(vreg[nm].sum()), stats=vres[nm]["stats"]) for nm in vres}), indent=1, default=str))
    return man


FW = 2565.02


def layer_gaps(vfiles, files):
    """F3 on the FINAL layers (alpha > 127, frame-width units): the table group's pieces against each other and the cushion sets"""
    def al(p):
        return np.asarray(Image.open(p))[..., 3] > 127
    sets = {s: al(files[("cushions", s)][0]) for s in "ABC"}

    def gap(a, b):
        if (a & b).any():
            return 0.0
        return round(float(cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)[a].min()) / FW, 4)

    def pair_pieces(m):
        n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)))
        ids = sorted([i for i in range(1, n) if st[i, 4] > 300], key=lambda i: st[i, 0])
        return [(lab == i) & m for i in ids]
    out = {}
    holders = {"travertine (default)": al(files[("candle-holders", None)][0]), "ceramic (v2)": al(vfiles["candle-holders-v2"][0])}
    bowls = {"black (default)": al(files[("bowl", None)][0]), "white belly (v2)": al(vfiles["bowl-v2"][0])}
    for hn, h in holders.items():
        ps = pair_pieces(h)
        out[f"{hn} A x B"] = gap(ps[0], ps[1]) if len(ps) == 2 else None
        out[f"{hn} x cushion sets (min)"] = min(gap(h, c) for c in sets.values())
        for bn, b in bowls.items():
            out[f"{hn} x {bn}"] = gap(h, b)
    for bn, b in bowls.items():
        out[f"{bn} x cushion sets (min)"] = min(gap(b, c) for c in sets.values())
    return out


def write_manifest(G, files, results, regions, cush_changed, overlap, origin, vres, vreg, vfiles, disjoint, unexpected, gaps):
    rel = F7.rel
    layers = [dict(R6BY["base"], sha256=sha(os.path.join(LAY, "base.png")))]
    for k in stack.ORDER:
        if k == "cushions":
            layers.append(R6BY["cushions-shadow"])
            layers.append(R6BY["cushions"])
            continue
        lp, sp = files[(k, None)]
        card, opt, sku = CARDS[k]
        cardp = next(p for p in sorted(glob.glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True)))
        layers.append(dict(id=f"{k}-shadow", slot=k, blend="multiply", z=stack.Z[k] - 1, file=os.path.relpath(sp, LAY), opaque=True,
                           white_is_none=True, format="RGB, no alpha"))
        rec = dict(id=k, slot=k, blend="normal", z=stack.Z[k], file=os.path.relpath(lp, LAY), format="RGBA, straight alpha",
                   product=dict(card_id=card, card=rel(cardp), option=opt, sku=sku, default=True),
                   region=GC.region_info(regions[(k, "B")]), build=results[(k, None)]["stats"], file_origin=origin[k],
                   behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in G3.LIGHTS)
        r6 = R6BY[k]
        for key in ("pass_", "note", "status_note", "fidelity", "render", "fix_r4", "position_status", "r5", "r6", "r5_as_variant",
                    "designer_conditions"):
            if key in r6:
                rec[key] = r6[key]
        if k in PASS7:
            rec["pass_"] = PASS7[k]
            rec["previous_file"] = r6["file"]
        if k == "planter":
            pr = FIXREC["planter"]
            rec["r7"] = dict(record="../work-r7/fix-r7.json#planter", k=pr["k"], targets=pr["targets"], all_met=pr["all_met"],
                             after={kk: pr["after"][kk] for kk in ("a1_dL_whole_minus_ring", "shoulder_1060_1107", "bottom_1180_1191", "b_dC_same_rows",
                                                                    "c_dh_same_rows", "highpass_L_std")})
            rec["status_note"] = ("R7 (section 8): darkened by ONE factor k 0.78 in linear light on the pot's body; (a') -8.0 against the wall, "
                                  "(a'') shoulder 77.2, every target met. The 0.8 % strip above the basket is the documented tangency (slots 1.9.4). "
                                  "'Partial' comes off after QA and the designer's eye")
        if k == "curtains":
            cr = FIXREC["curtains"]["curtains"]
            rec["r7"] = dict(record="../work-r7/fix-r7.json#curtains", hem_z=0.12, sold_length_cm=270, measured=cr["measured"],
                             geometry=cr["geometry"]["lines_3840"], hem_band_step_dL=cr["hem_band_step_dL"], band_natural_before=cr.get("band_natural_dL_before_cut"))
            rec["status_note"] = ("R7 (WM-C3 / SUP-C1, section 6.3): the sold 270 from the fabric top at 2.82: the hem 12 cm above the floor where "
                                  "the stack hangs free beyond the bench end (u 0-0.020), resting on the bench top beyond it; the floor contact "
                                  "line removed, the soft shade under the hem and the stone contact line added (the designer's shadow, item 6)")
        if k == "candle-holders":
            tr = FIXREC["table"]
            rec["r7"] = dict(record="../work-r7/fix-r7.json#table", pieces=tr["candle-holders"]["pieces"], lever=tr["candle-holders"]["lever"],
                             layer_gaps_frame=tr["layer_gaps_frame"])
            rec["status_note"] = ("R7 (WM-T2, section 1.5): moved in code to the 1.9.4 points with its shadow, about each foot: B (0.355, 1.68); A at "
                                  "(0.195, 1.74), the pre-approved 9 cm lever (the designer's 0.205 read A x B 0.0191 on the rendered pieces). "
                                  "Re-cut before the move: the step-3 convex hull had carried the old place's boucle beside the candle and the "
                                  "cone. The shadow is the frozen recipe's field carried with each piece, re-masked at the new place")
            rec["position_status"] = "1.9.4 points (owner WM-T2), clay F3 passes (step0/r7-table-group)"
        if k == "bowl":
            tr = FIXREC["table"]
            rec["r7"] = dict(record="../work-r7/fix-r7.json#table", pieces=tr["bowl"]["pieces"], layer_gaps_frame={kk: v for kk, v in tr["layer_gaps_frame"].items() if "bowl" in kk})
            rec["status_note"] = ("R7 (WM-T2, section 1.5): moved in code to (0.62, 1.94) with its shadow. POSITION PROVISIONAL: the clay reads the bowl "
                                  "x throw at 0.0095-0.016 for every bowl and every set (step0/r7-table-group): the throw's LOWER edge lies above the "
                                  "bowl, so moving left does not help and no pre-approved lever does: back to the designer (section 1.4)")
            rec["position_status"] = "PROVISIONAL: F3 bowl x throw < 0.02 at the 1.9.4 point (all bowls, all sets); the designer decides"
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(R6MAN["slot_cushions"]["sets"][s], layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       region=GC.region_info(regions[("cushions", s)]), recut_on_new_stack_px=int(cush_changed[s].sum()),
                       build=results[("cushions", s)]["stats"], file_origin=origin[f"cushions-{s}"])
    variants = {}
    for k, nm in VARIANTS:
        r = vres[nm]
        card, opt, sku = VCARDS[nm]
        cardp = next(p for p in sorted(glob.glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True)))
        lp, sp = vfiles[nm]
        v = dict(id=nm, slot=k, variant=nm.split("-")[-1], z=stack.Z[k], file=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                 blend="normal + its shadow multiply", product=dict(card_id=card, card=rel(cardp), option=opt, sku=sku, default=False),
                 region=GC.region_info(vreg[nm]), build=r["stats"], file_origin=origin[nm], truth=f"../graded/variant-r7-{nm}-set-B-graded-v3c.png",
                 behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in G3.LIGHTS,
                 swaps_with="its slot's default and every variant of the other slots (the slots' regions are disjoint: checked)")
        if nm in R6VAR and nm != "curtains-v2":
            for key in ("pass_", "cut", "post_fix", "r6", "in_wheel", "note"):
                if key in R6VAR[nm]:
                    v[key] = R6VAR[nm][key]
        if nm == "curtains-v2":
            v6 = R6VAR["curtains-v2"]
            cr = FIXREC["curtains"]["curtains-v2"]
            for key in ("cut", "r6", "note", "in_wheel"):
                if key in v6:
                    v[key] = v6[key]
            v.update(pass_="reserve R1 + fix R6 (L*, a*b*) + fix R7 (code: the sold 270, section 6.3)", previous_file=v6["file"],
                     r7=dict(record="../work-r7/fix-r7.json#curtains", hem_z=0.12, measured=cr["measured"], hem_band_step_dL=cr["hem_band_step_dL"]))
        if nm == "curtains-v3":
            cr = FIXREC["curtains-v3"]
            v.update(pass_="pass 7' (render) + post R7 (colour, R5 method) + fix R7 (code: the sold 260, section 6.3)",
                     cut=dict(record="../work-r7/p7-fetch.json#curtains-v3", **{kk: FETCH["p7"]["cut"]["curtains-v3"][kk]
                                                                                   for kk in ("placeholder_covered", "outside_placeholder_px", "model_change_vs_placeholder_dE")}),
                     colour=dict(record="../work-r7/post-r7.json#p7.curtains-v3", **{kk: POSTREC["p7"]["curtains-v3"][kk] for kk in ("photo", "after", "targets", "all_met")}),
                     r7=dict(record="../work-r7/fix-r7.json#curtains-v3", hem_z=0.22, sold_length_cm=260, measured=cr["measured"],
                             hem_band_step_dL=cr["hem_band_step_dL"]),
                     note="Linen 200 x 260, 4 hook (CJYD218713946TG; the card's in_room still names another SKU: sourcing moves it). How many "
                          "200 cm panels a 2.10 window takes, and the price, are the manager's")
        if nm in ("bowl-v2", "candle-holders-v2", "vase-v3"):
            fr = FETCH["p6"]["cut"][nm]
            v.update(pass_="pass 6' (render) + post R7 (code)", cut=dict(record=f"../work-r7/p6-fetch.json#{nm}",
                                                                         **{kk: fr[kk] for kk in ("placeholder_covered", "outside_placeholder_px", "model_change_vs_placeholder_dE")}),
                     post=dict(record=f"../work-r7/post-r7.json#p6.{nm}", **POSTREC["p6"][nm]),
                     colour_graded_set_B=POSTREC["p6"]["colour_graded_set_B"][nm])
            if nm == "bowl-v2":
                v["position_status"] = "PROVISIONAL with the default bowl (bowl x throw < 0.02 at (0.62, 1.94)); the designer decides"
            if nm == "candle-holders-v2":
                v["note"] = ("the two walnut ball handles of each tray added back to the cut from the render (GrabCut had left them out); both pieces "
                             "registered back onto their placeholders (the model warped the table region: B +13.5 px)")
        variants.setdefault(k, []).append(v)
    p7 = POSTREC["p7"]
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-r7", version="r7 (supersedes manifest-r6.json for the tool; the earlier manifests are kept)",
        room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-12", author="render-agent",
        brief="briefs/render-wm-tool-r7-2026-11-12.md (A: code, 0 tokens; B: passes 6' and 7', 650 each) from "
              "docs/proposals/owner-answers-applied-2026-11-12.md (sections 1, 6, 8)",
        approval=R6MAN["approval"] + "; R7: WM-T2 / WM-C3 / SUP-C1 (owner 2026-11-12) and the coordinator's planter addition; passes 6' and 7' "
                                     "under PH2-WM (phase 2: 5,850 + 1,300 = 7,150 of 9,740)",
        status="phase 2: 12 defaults + %d variants as layers, after R7. Not QA'd; for qa-agent and master-designer. HD_PUBLIC=0 only. "
               "FAILED in 7' (not layers): bowl-v3 and candle-holders-v3 (size and place). PROVISIONAL: the bowl's point (F3 bowl x throw)" % len(vres),
        grade=R6MAN["grade"], grade_params=G.record(), size=R6MAN["size"], color=R6MAN["color"],
        compose=dict(R6MAN["compose"], order=[l_["id"] for l_ in layers]),
        shadow_recipe=dict(R6MAN["shadow_recipe"], applies_to="every layer; R7's new cuts measure their contact shadow with extract.shadow_one "
                                                             "unchanged; the moved table defaults carry their recipe field, re-masked; the curtains' "
                                                             "cut shadow (under the hem, on the stone) is the designer's section 6.3 item 6"),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        variants=variants, disjoint_overlaps=disjoint, vase_point=R6MAN["vase_point"],
        table_group=dict(points="slots 1.9.4 by_style.warm-modern (WM-T2)", clay="../step0/r7-table-group/table-group-r7.json",
                         levers="../step0/r7-table-group/levers-r7.json", clay_fails=TG["fails"], iron_B16=LEV["iron_B16"]["per_bowl"],
                         final_layer_gaps_frame=gaps,
                         bowl_point="back to the designer: no bowl point on the table passes the throw and the holders together (levers-r7.json "
                                    "bowl_candidates: the throw needs the bowl left of X ~0.45, the holders need it right of ~0.58)"),
        failed_in_r7={"bowl-v3": p7["bowl-v3"], "candle-holders-v3": p7["candle-holders-v3"]},
        pending={"bowl point": "the designer (section 1.4)", "bowl-v3, candle-holders-v3": "a new pass, or a code salvage the designer approves (not done)"},
        changed_in_r7=dict(defaults=FIX7, variants=sorted(NEW_IN_R7), files=origin, unexpected_other_changes=unexpected),
        light_layers=R6MAN["light_layers"],
        files=dict(build="grade_cut_r7.py (fix_r7.py, pass_r7.py, post_r7.py)", fixes="../fix_r7.py -> ../work-r7/ (../work-r7/fix-r7.json)",
                   passes="../pass_r7.py -> ../work-r7/p6-fetch.json, p7-fetch.json; ../post_r7.py -> ../work-r7/post-r7.json; ../jobs-r7.json",
                   verify="verify_layers_r7.py", verification="verify-layers-r7.json", lock="../lock_r7.py -> ../lock-and-grade-check-r7.json",
                   crops="../crops-r7/ (../make_crops_r7.py)", sheet="../phase2-r7-sheet.jpg", asset_manifest_entries="asset-manifest-entries-r7.json",
                   verify_usage="python3 verify_layers_r7.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=dict(R6MAN["tokens"], fix_r7=0, passes_r7=1300, phase2_total=7150, phase2_cap=9740),
        held=G12.HELD,
    )
    p = os.path.join(LAY, "manifest-r7.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False, default=float)
    return man


def write_asset_entries(man, origin):
    status = ("warm-modern tool, phase 2 R7 (code A + passes 6' / 7', 2026-11-12); v3c layers cut from the graded composites; verified by "
              "layers/verify_layers_r7.py; awaiting qa-agent and master-designer; HD_PUBLIC=0")
    base = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
    out = []

    def add(eid, path, kind, model, extra=None):
        out.append(dict(id=eid, path=path, kind=kind, model=model, status=status, style="warm-modern", room="living-room", created="2026-11-12",
                        recipe=base + "grade_cut_r7.py (fix_r7.py, pass_r7.py, post_r7.py)", **(extra or {})))
    for l_ in man["layers"]:
        k = l_.get("slot")
        if "file" not in l_ or k in (None, "cushions"):
            continue
        is_sh = l_["id"].endswith("-shadow")
        o = origin[k]["shadow" if is_sh else "layer"]
        if not o.startswith("new"):
            continue
        prod = next(x for x in man["layers"] if x["id"] == k)
        add(f"wm-tool-ph2-r7-{l_['id']}", base + "layers/" + l_["file"],
            f"tool {'shadow layer, RGB multiply (white = none)' if is_sh else 'product layer, RGBA straight alpha'}, {k}, default, v3c",
            "code (R7, 0 tokens) on earlier seedream-5-pro renders", None if is_sh else dict(product_id=prod["product"]["card_id"], sku=prod["product"]["sku"]))
    for k, vs in man["variants"].items():
        for v in vs:
            mdl = ("seedream-5-pro i2i 2K (pass 6' / 7') + code" if v["id"] in ("bowl-v2", "candle-holders-v2", "vase-v3", "curtains-v3")
                   else "code (R7, 0 tokens) on an earlier render")
            for is_sh in (False, True):
                if not origin[v["id"]]["shadow" if is_sh else "layer"].startswith("new"):
                    continue
                add(f"wm-tool-ph2-r7-{v['id']}{'-shadow' if is_sh else ''}", base + "layers/" + (v["shadow"] if is_sh else v["file"]),
                    f"tool {'shadow layer, RGB multiply' if is_sh else 'product layer, RGBA straight alpha'}, {k}, variant {v['variant']}, v3c", mdl,
                    None if is_sh else dict(product_id=v["product"]["card_id"], sku=v["product"]["sku"]))
    for s in "BAC":
        add(f"wm-tool-ph2-r7-default-scene-{s}", base + f"graded/default-scene-r7-set-{s}-graded-v3c.png", f"graded default scene (12 defaults, R7), set {s}, v3c", "composite")
    for k, vs in man["variants"].items():
        for v in vs:
            add(f"wm-tool-ph2-r7-truth-{v['id']}", base + f"graded/variant-r7-{v['id']}-set-B-graded-v3c.png", f"graded truth of variant {v['id']}, set B, v3c", "composite")
    add("wm-tool-ph2-r7-layers-manifest", base + "layers/manifest-r7.json", "tool layers manifest r7 (12 defaults + variants)", "-")
    add("wm-tool-ph2-r7-sheet", base + "phase2-r7-sheet.jpg", "review sheet R7: every option of every slot, and the R7 changes", "-")
    add("wm-tool-ph2-r7-crops", base + "crops-r7/", "crops of the R7 changes at 100 % and x4", "-")
    for p in ("p6", "p7"):
        add(f"wm-tool-ph2-r7-raw-{p}", base + f"raw/{p}-r7-seedream.png", f"raw seedream render of pass {p[1]}' (not for the site)", "seedream-5-pro i2i 2K (650)")
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-12; R7: new files only, the entries in a separate JSON for "
                    "the manager); layers and shadows whose bytes did not change keep their earlier entries", assets=out)
    p = os.path.join(LAY, "asset-manifest-entries-r7.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
