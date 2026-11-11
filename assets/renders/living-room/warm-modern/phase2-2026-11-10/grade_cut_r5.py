#!/usr/bin/env python3
"""
grade_cut_r5.py: the v3c layers of the warm-modern tool, phase 2, after the R5 code fixes and the variant passes 4' / 5' (render-agent,
2026-11-11). Brief: briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md. Code only (the passes are pass_r5.py). NEW FILES ONLY: earlier
files are read, never written.

The same method as grade_cut_r4.py (ONE v3c grade, stack.Grade; every layer cut from the graded composites, never graded on its own; the
cushion sets kept byte for byte where the stack under them did not change), on the stack of the 12 defaults with, from work-r5/:
  curtains          R5 colour fix (a*b* to the card's cream) + the armchair post's light line         fix_r5.py
  magazine-holder   R5: the two thin rods to the SKU photo's satin silver                              fix_r5.py
  floor-lamp        R5: the step-2 wisp under the shade out of the layer (QA R4 2.1)                   fix_r5.py
  vase              4': the default re-rendered at the clay point (-2.42, 1.35)                        pass_r5.py p4
  planter           5': the default re-rendered WHOLE (if 5' passed; else R4's)                        pass_r5.py p5
and the VARIANTS, each cut on the SAME graded composite under its slot as the default (the default's Cprev and slab alpha), so a variant
swaps with its default changing nothing outside the union of the two regions:
  curtains-v2, framed-art-v2, accent-sconces-v2 (4'), vase-v2, accent-sconces-v3, pendant-v2 (5')
The shadow recipe is FROZEN (extract.shadow_one as every existing layer; the coordinator after QA's R4 check).

Writes: layers/<slot>/...-r5.png and the variants' layer files, layers/manifest-r5.json, graded/default-scene-r5-set-<X>-graded-v3c.png,
graded/variant-r5-<name>-set-B-graded-v3c.png (the truth for each variant), layers/asset-manifest-entries-r5.json.
  python3 grade_cut_r5.py     then   python3 layers/verify_layers_r5.py   and   python3 lock_r5.py
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade_cut as GC  # noqa: E402
import grade_cut_r4 as G4  # noqa: E402  (the r4 sources)
import grade_cut_r12 as G12  # noqa: E402
import grade_cut_r3 as G3  # noqa: E402
import pass_r5 as R  # noqa: E402  (the R5 sources: curtains, magazine-holder)
import post_r5 as PO  # noqa: E402
import stack  # noqa: E402
from phase2_wm import P1  # noqa: E402

LAY, GRD, REPO = G4.LAY, G4.GRD, G4.REPO
WR5 = R.WR5
P5_OK = os.path.exists(os.path.join(WR5, "p5-fetch.json")) and os.path.exists(os.path.join(WR5, "layers/planter.png"))
FIX5 = ["curtains", "magazine-holder", "floor-lamp", "vase"] + (["planter"] if P5_OK else [])
G12.SRC.update({k: (os.path.join(WR5, "layers"), os.path.join(WR5, "shadows")) for k in FIX5})
ACCEPTED = G4.ACCEPTED
CARDS = dict(G4.CARDS)
VARIANTS = [("curtains", "v2", "p4"), ("framed-art", "v2", "p4"), ("accent-sconces", "v2", "p4")]
if P5_OK:
    VARIANTS += [("vase", "v2", "p5"), ("accent-sconces", "v3", "p5"), ("pendant", "v2", "p5")]
FIXREC = json.load(open(os.path.join(WR5, "fix-r5.json")))
POSTREC = json.load(open(os.path.join(WR5, "post-r5.json"))) if os.path.exists(os.path.join(WR5, "post-r5.json")) else {}
FETCH = {p: json.load(open(os.path.join(WR5, f"{p}-fetch.json"))) for p in ("p4", "p5") if os.path.exists(os.path.join(WR5, f"{p}-fetch.json"))}
NOTES = dict(G4.NOTES)
NOTES.update({
    "curtains": "R5: colour fixed in code toward the card's cream (designer section 3): a*b* only, one hue rotation and one chroma factor; "
                "median h 89.7, C* 6.5, p95 9.5, L* -0.1, >= the plaster + 0.5; and the armchair post's 1 px light line closed in the same cut",
    "magazine-holder": G4.NOTES.get("magazine-holder", "") + ". R5: the two thin rods to the SKU photo's satin silver (L* median 56, C* 2.5); "
                       "the glossy black tubes are the designer's documented exception (pending WM-M1)",
    "floor-lamp": G4.NOTES["floor-lamp"] + ". R5: the step-2 wisp under the shade removed from the layer (QA R4 2.1)",
    "vase": "4': re-rendered at the clay point (-2.42, 1.35) (step0/vase-point-r5.json: the first of the designer's three points where all "
            "three vases pass), from R4's code-sized render as the placeholder; seat on the point within 1 px; 15.9 x ~31.5 cm. The model drew it "
            "cream (lit half C* 16): a*b* fixed in code to the designer's targets (C* 5.5, hue of the surface beside, L* unchanged; post-r5.json)",
    "planter": "5': re-rendered WHOLE (designer section 6) from the card's clay pot (opening 35.5, belly 42, height 35.5) and R3a's olive "
               "tree; the basket that passed stays on top" if P5_OK else G4.NOTES["planter"],
})
PASS = dict(G4.PASS)
PASS.update({"curtains": "reserve R1 + fix R5 (code)", "magazine-holder": "reserve R1 + fix R5 (code)", "floor-lamp": "steps 1-3 + fix R4 + fix R5 (code)",
             "vase": "pass 4' (re-render at the clay point)"})
if P5_OK:
    PASS["planter"] = "pass 5' (re-render, whole)"
VCARDS = {(k, v): R.CARDS[(k, v)] for k, v, _ in VARIANTS}


def vname(k, v):
    return R.fname(k, v)


def main():
    os.makedirs(LAY, exist_ok=True)
    G = stack.Grade()
    P = stack.base_parts()
    base8 = GC.u8(os.path.join(P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    items = set(ACCEPTED) | {"cushions"}
    results, regions, finals, cush_changed, pre = {}, {}, {}, {}, {}
    for s in "BAC":
        U, steps = G12.compose(items, P, cushion_set=s)
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
        p = os.path.join(GRD, f"default-scene-r5-set-{s}-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(finals[s]).save(p, compress_level=6)
    # ------------------------------------------------------------------ the variants, each on its slot's own Cprev (set B)
    vres, vreg, vtruth = {}, {}, {}
    for k, v, ps in VARIANTS:
        nm = vname(k, v)
        Uv, stv = PO.compose_with({k: nm})
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
        vres[nm] = dict(L=np.dstack([r["L"], r["A"]]), S=r["S"], stats=r["stats"], slot=k, variant=v, pass_=ps)
        vreg[nm] = reg
        # the truth with the variant: the default scene B, the slot's default taken out (Cprev there), the variant in
        T = finals["B"].astype(np.float64).copy()
        dreg = regions[(k, "B")]
        T[dreg] = Cprev[dreg]
        T[reg] = C[reg]
        vtruth[nm] = T.astype(np.uint8)
        p = os.path.join(GRD, f"variant-r5-{nm}-set-B-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(vtruth[nm]).save(p, compress_level=6)
    # ------------------------------------------------------------------ disjointness: every slot with variants against every other slot
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    slot_union = {}
    for k in ACCEPTED:
        u = regions[(k, "B")].copy()
        for nm, rg in vreg.items():
            if vres[nm]["slot"] == k:
                u |= rg
        slot_union[k] = u
    cush_union = regions[("cushions", "A")] | regions[("cushions", "B")] | regions[("cushions", "C")]
    vslots = sorted({vres[nm]["slot"] for nm in vres})
    disjoint = {}
    for k in vslots:
        for j in ACCEPTED:
            if j == k:
                continue
            n = int((slot_union[k] & slot_union[j]).sum())
            if n:
                disjoint[f"{k} x {j}"] = n
        n = int((slot_union[k] & cush_union).sum())
        if n:
            disjoint[f"{k} x cushions"] = n
    # ------------------------------------------------------------------ files
    files, reused = {}, {}
    for (k, s), r in results.items():
        d, stem = (os.path.join(LAY, "cushions"), f"set-{s}") if k == "cushions" else (os.path.join(LAY, k), CARDS[k][0])
        os.makedirs(d, exist_ok=True)
        key = f"{k}{'-' + s if s else ''}"
        found = None
        for suf in ("", "-r12", "-r3", "-r4", "-r5"):
            lp_old, sp_old = os.path.join(d, f"{stem}{suf}.png"), os.path.join(d, f"{stem}{suf}-shadow.png")
            if os.path.exists(lp_old) and os.path.exists(sp_old):
                if (np.array_equal(np.asarray(Image.open(lp_old)), r["L"]) and
                        np.array_equal(np.asarray(Image.open(sp_old).convert("RGB")), r["S"])):
                    found = (lp_old, sp_old, "existing file, same bytes (" + (suf.strip("-") or "base name") + ")")
                    break
        if found:
            files[(k, s)] = found[:2]
            reused[key] = found[2]
            continue
        lp, sp = os.path.join(d, f"{stem}-r5.png"), os.path.join(d, f"{stem}-r5-shadow.png")
        reused[key] = "recomputed bytes differ: new -r5 file" + (" (R5)" if k in FIX5 else " (the stack under it changed)")
        assert not os.path.exists(lp) and not os.path.exists(sp), f"would overwrite {lp}"
        Image.fromarray(r["L"], "RGBA").save(lp, compress_level=9)
        Image.fromarray(r["S"], "RGB").save(sp, compress_level=9)
        files[(k, s)] = (lp, sp)
    vfiles = {}
    for nm, r in vres.items():
        k = r["slot"]
        d = os.path.join(LAY, k)
        stem = VCARDS[(k, r["variant"])][0]
        lp, sp = os.path.join(d, f"{stem}-r5.png"), os.path.join(d, f"{stem}-r5-shadow.png")
        assert not os.path.exists(lp) or os.environ.get("REDO"), lp
        Image.fromarray(r["L"], "RGBA").save(lp, compress_level=9)
        Image.fromarray(r["S"], "RGB").save(sp, compress_level=9)
        vfiles[nm] = (lp, sp)
    unexpected = [k for k, v in reused.items() if v.startswith("recomputed") and k not in FIX5]
    man = write_manifest(G, files, results, regions, cush_changed, overlap, reused, unexpected, vres, vreg, vfiles, disjoint)
    write_asset_entries(man)
    print(json.dumps(dict(reuse=reused, unexpected_changes=unexpected, variants={nm: dict(region_px=int(vreg[nm].sum()), stats=vres[nm]["stats"])
                                                                                   for nm in vres}, disjoint_overlaps=disjoint), indent=1, default=str))
    return man


def write_manifest(G, files, results, regions, cush_changed, overlap, reused, unexpected, vres, vreg, vfiles, disjoint):
    rel = R.rel
    r4 = json.load(open(os.path.join(LAY, "manifest-r4.json")))
    r4by = {l_["id"]: l_ for l_ in r4["layers"]}
    layers = [dict(r4by["base"], sha256=GC.sha(os.path.join(LAY, "base.png")))]
    for k in stack.ORDER:
        if k == "cushions":
            layers.append(r4by["cushions-shadow"])
            layers.append(r4by["cushions"])
            continue
        lp, sp = files[(k, None)]
        card, opt, sku = CARDS[k]
        st = results[(k, None)]["stats"]
        cardp = next(p for p in sorted(glob.glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True)))
        layers.append(dict(id=f"{k}-shadow", slot=k, blend="multiply", z=stack.Z[k] - 1, file=os.path.relpath(sp, LAY), opaque=True, white_is_none=True,
                           format="RGB, no alpha"))
        rec = dict(id=k, slot=k, blend="normal", z=stack.Z[k], file=os.path.relpath(lp, LAY), format="RGBA, straight alpha",
                   product=dict(card_id=card, card=rel(cardp), option=opt, sku=sku, default=True),
                   region=GC.region_info(regions[(k, "B")]), build=st, pass_=PASS[k], file_origin=reused[k],
                   behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in G3.LIGHTS)
        for key in ("note", "status_note", "fidelity", "render", "fix_r4"):
            if key in r4by[k]:
                rec[key] = r4by[k][key]
        if k in NOTES:
            rec["status_note"] = NOTES[k]
        if k in FIX5:
            src = {"curtains": "fix-r5.json#curtains", "magazine-holder": "fix-r5.json#magazine-holder", "floor-lamp": "fix-r5.json#floor-lamp",
                   "vase": "p4-fetch.json + ../jobs-r5.json (vase_landing_check)", "planter": "p5-fetch.json"}[k]
            rec["r5"] = dict(record="../work-r5/" + src, previous_file=r4by[k]["file"])
            if k in ("curtains", "magazine-holder", "floor-lamp"):
                rec["r5"]["measured"] = {kk: FIXREC[k][kk] for kk in ("after", "targets", "post_line", "measured_graded_rod_core", "qa_measure")
                                         if kk in FIXREC[k]}
        if k in POSTREC:
            rec.setdefault("r5", {})["post_fix"] = POSTREC[k]
        if k == "vase":
            rec.pop("fix_status", None)
            rec["position_status"] = "at the clay point (-2.42, 1.35), the slot's own point (step0/vase-point-r5.json)"
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(r4["slot_cushions"]["sets"][s], layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       region=GC.region_info(regions[("cushions", s)]), recut_on_new_stack_px=int(cush_changed[s].sum()),
                       build=results[("cushions", s)]["stats"], file_origin=reused[f"cushions-{s}"])
    variants = {}
    for nm, r in vres.items():
        k, v = r["slot"], r["variant"]
        card, opt, sku = VCARDS[(k, v)]
        cardp = next(p for p in sorted(glob.glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True)))
        lp, sp = vfiles[nm]
        cutrec = FETCH[r["pass_"]]["cut"][nm]
        variants.setdefault(k, []).append(dict(
            id=nm, slot=k, variant=v, z=stack.Z[k], file=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY), blend="normal + its shadow multiply",
            product=dict(card_id=card, card=rel(cardp), option=opt, sku=sku, default=False), region=GC.region_info(vreg[nm]), build=r["stats"],
            pass_=f"pass {r['pass_'][1]}'", cut=dict(record=f"../work-r5/{r['pass_']}-fetch.json#{nm}", **{x: cutrec[x] for x in
                                                     ("placeholder_covered", "outside_placeholder_px", "model_change_vs_placeholder_dE")}),
            post_fix=POSTREC.get(nm), truth=f"../graded/variant-r5-{nm}-set-B-graded-v3c.png",
            behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in G3.LIGHTS,
            swaps_with="its slot's default and every variant of the other slots: the slots' regions (all their variants) are disjoint "
                       "(checked: disjoint_overlaps)"))
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-r5", version="r5 (supersedes manifest-r4.json for the tool; the earlier manifests are kept)",
        room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-11", author="render-agent",
        brief="briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md (0-token colour fixes, the vases' clay point, passes 4' and 5'); the "
              "coordinator's corrections: the frozen shadow recipe, the floor lamp's wisp",
        approval=r4["approval"] + "; R5: PH2-WM, passes 4' and 5' at 650 each (jobs-r5.json)",
        status="phase 2: 12 defaults + %d variants as layers, after R5. Not QA'd; for qa-agent and master-designer. HD_PUBLIC=0 only" % len(vres),
        grade=r4["grade"], grade_params=G.record(), size=r4["size"], color=r4["color"],
        compose=dict(r4["compose"], order=[l_["id"] for l_ in layers],
                     variants="a variant replaces its slot's default layer and shadow at the same z; nothing else changes"),
        shadow_recipe=dict(frozen=True, recipe="extract.shadow_one as every existing layer (luminance in linear light; the units bug's rendered "
                                               "effect is mixed, -3.5 to +16 L*, compensated by the rest of the recipe)",
                           decision="the coordinator, 2026-11-11, after QA's R4 check (qa/reports/2026-11-11-wm-tool-phase2-r4.md); a units fix, "
                                    "if any, is ONE calibration of every layer with the 6K masters and the owner's re-approval of the base",
                           applies_to="every variant layer of passes 4' and 5'"),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        variants=variants, disjoint_overlaps=disjoint,
        vase_point=json.load(open(os.path.join(R.HERE, "step0/vase-point-r5.json")))["chosen_point"],
        pending={},
        changed_in_r5=dict(products=FIX5, files={k: reused[k] for k in FIX5}, unexpected_other_changes=unexpected,
                           unchanged_products=[k for k in ACCEPTED if k not in FIX5], cushion_sets={s: reused[f"cushions-{s}"] for s in "BAC"}),
        light_layers=r4["light_layers"],
        files=dict(build="grade_cut_r5.py (fix_r5.py, pass_r5.py, post_r5.py, grade_cut_r4.py, ...)", fixes="../fix_r5.py, ../post_r5.py -> ../work-r5/",
                   passes="../pass_r5.py -> ../work-r5/ (../jobs-r5.json)", clay="../clay_vase_point_r5.py -> ../step0/vase-point-r5.json",
                   verify="verify_layers_r5.py", verification="verify-layers-r5.json", lock="../lock_r5.py -> ../lock-and-grade-check-r5.json",
                   crops="../crops-r5/ (make_crops_r5.py)", sheet="../phase2-r5-variants-sheet.jpg", asset_manifest_entries="asset-manifest-entries-r5.json"),
        tokens=dict(r4["tokens"], this_build=0, passes_r5=sum(j.get("tokens", 0) for j in json.load(open(os.path.join(R.HERE, "jobs-r5.json")))["jobs"])),
        held=G12.HELD,
    )
    p = os.path.join(LAY, "manifest-r5.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False, default=float)
    return man


def write_asset_entries(man):
    status = ("warm-modern tool, phase 2 R5 (0-token code fixes + variant passes 4' / 5', 2026-11-11); v3c layers cut from the graded "
              "composites; verified by layers/verify_layers_r5.py; awaiting qa-agent and master-designer")
    base = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
    out = []
    for l_ in man["layers"]:
        k = l_.get("slot")
        if "file" not in l_ or k in (None, "cushions"):
            continue
        prod = next(x for x in man["layers"] if x["id"] == k)
        if not prod.get("file_origin", "").startswith("recomputed"):
            continue
        is_sh = l_["id"].endswith("-shadow")
        e = dict(id=f"wm-tool-ph2-r5-{l_['id']}", path=base + "layers/" + l_["file"],
                 kind=(f"tool shadow layer, RGB multiply (white = none), {k}, default, v3c" if is_sh else f"tool product layer, RGBA straight alpha, normal, {k}, default, v3c"),
                 model=("seedream-5-pro i2i 2K + code" if k in ("vase", "planter") else "seedream-5-pro i2i 2K + code (R5: code only)"),
                 status=status, style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r5.py")
        if not is_sh:
            e.update(product_id=prod["product"]["card_id"], sku=prod["product"]["sku"])
        out.append(e)
    for k, vs in man["variants"].items():
        for v in vs:
            for is_sh in (False, True):
                out.append(dict(id=f"wm-tool-ph2-r5-{v['id']}{'-shadow' if is_sh else ''}", path=base + "layers/" + (v["shadow"] if is_sh else v["file"]),
                                kind=f"tool {'shadow layer, RGB multiply' if is_sh else 'product layer, RGBA straight alpha'}, {k}, variant {v['variant']}, v3c",
                                model="seedream-5-pro i2i 2K" + (" + code" if v.get("post_fix") else ""), status=status, style="warm-modern",
                                room="living-room", created="2026-11-11", recipe=base + "grade_cut_r5.py (pass_r5.py, post_r5.py)",
                                **({} if is_sh else dict(product_id=v["product"]["card_id"], sku=v["product"]["sku"]))))
    for s in "BAC":
        out.append(dict(id=f"wm-tool-ph2-r5-default-scene-{s}", path=base + f"graded/default-scene-r5-set-{s}-graded-v3c.png",
                        kind=f"graded default scene (12 defaults, R5), set {s}, v3c", model="code", status=status, style="warm-modern",
                        room="living-room", created="2026-11-11", recipe=base + "grade_cut_r5.py"))
    out.append(dict(id="wm-tool-ph2-r5-layers-manifest", path=base + "layers/manifest-r5.json", kind="tool layers manifest r5 (12 defaults + variants)",
                    model="code", status=status, style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r5.py"))
    out.append(dict(id="wm-tool-ph2-r5-sheet", path=base + "phase2-r5-variants-sheet.jpg", kind="review sheet: each slot's variants on the default "
                    "scene with set B", model="code", status=status, style="warm-modern", room="living-room", created="2026-11-11",
                    recipe=base + "make_sheet_r5.py"))
    out.append(dict(id="wm-tool-ph2-r5-crops", path=base + "crops-r5/", kind="crops of the R5 fixes and the variants at 100 % and x3", model="code",
                    status=status, style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "make_crops_r5.py"))
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-11; R5: new files only, the entries in a separate JSON "
                    "for the manager); layers whose bytes did not change keep their earlier entries", assets=out)
    p = os.path.join(LAY, "asset-manifest-entries-r5.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
