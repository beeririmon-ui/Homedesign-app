#!/usr/bin/env python3
"""
grade_cut_r6.py: the v3c layers of the warm-modern tool, phase 2, after R6 (render-agent, 2026-11-12; 0 tokens, code only).
Brief: briefs/render-wm-tool-r6-codefix-2026-11-12.md. NEW FILES ONLY: earlier files are read, never written; a layer or shadow whose
recomputed bytes equal an existing file keeps that file (each of the two on its own), anything else is written as <stem>-r6.png.

The same method as grade_cut_r5.py (ONE v3c grade, stack.Grade; every layer cut from the graded composites, never graded on its own;
the cushion sets kept byte for byte where the stack under them did not change), on the R6 sources (fix_r6.SRC6 / VSRC6):
  curtains          the DEFAULT is 180502 now (the designer, eye section 1): R5's curtains-v2 work files, unchanged
  vase              re-cut from the raw 4' render, straightened and sized to the card about the foot, R5's colour fix re-solved
  magazine-holder   the rods' soft edge
and the variants, each cut on the SAME graded composite under its slot as the default:
  curtains-v2 = 554205 (L* and a*b* relative to 180502), framed-art-v2 (the seams, the specks), accent-sconces-v2 / -v3 (R5, unchanged),
  vase-v2 (re-cut, neutral charcoal), pendant-v2 (canopy, outline, cord black, rings out)
The shadow recipe is FROZEN (extract.shadow_one as every existing layer).

Writes: layers/<slot>/...-r6.png (only where the bytes are new), layers/manifest-r6.json, graded/default-scene-r6-set-<X>-graded-v3c.png,
graded/variant-r6-<name>-set-B-graded-v3c.png (each variant's truth), layers/asset-manifest-entries-r6.json.
  python3 fix_r6.py all ; python3 grade_cut_r6.py ; python3 layers/verify_layers_r6.py ; python3 lock_r6.py ; python3 make_crops_r6.py
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
import fix_r6 as F6  # noqa: E402  (imports grade_cut_r5 / r4 / r12 / r3 and sets the R6 sources)
import grade_cut as GC  # noqa: E402
import grade_cut_r3 as G3  # noqa: E402
import grade_cut_r12 as G12  # noqa: E402
import stack  # noqa: E402
from phase2_wm import P1  # noqa: E402

LAY, GRD, REPO = os.path.join(HERE, "layers"), os.path.join(HERE, "graded"), F6.W.REPO
G5 = F6.G5
ACCEPTED = list(F6.ACCEPTED)
FIX6 = ["curtains", "vase", "magazine-holder"]
CARDS = dict(F6.CARDS6)
VARIANTS = [("curtains", "curtains-v2"), ("framed-art", "framed-art-v2"), ("accent-sconces", "accent-sconces-v2"), ("vase", "vase-v2"),
            ("accent-sconces", "accent-sconces-v3"), ("pendant", "pendant-v2")]
FIXREC = json.load(open(os.path.join(F6.WR6, "fix-r6.json")))
R5MAN = json.load(open(os.path.join(LAY, "manifest-r5.json")))
R5BY = {l_["id"]: l_ for l_ in R5MAN["layers"]}
R5VAR = {v["id"]: v for vs in R5MAN["variants"].values() for v in vs}
NEW_IN_R6 = {"vase-v2", "pendant-v2", "framed-art-v2", "curtains-v2"}
PASS6 = {"curtains": "pass 4' (180502, the R5 variant) as the default from R6", "vase": "pass 4' + fix R6 (code: re-cut, straightened, sized, colour)",
         "magazine-holder": "reserve R1 + fix R5 + fix R6 (code: the rods' soft edge)"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def same_file(d, arr, mode, stem=""):
    """an existing file in d with exactly these pixels (mode RGBA or RGB), or None; the files of the product's own stem first"""
    ps = sorted(glob.glob(os.path.join(d, "*.png")))
    for p in sorted(ps, key=lambda p_: (not os.path.basename(p_).startswith(stem), p_)):
        im = Image.open(p)
        if im.size != (arr.shape[1], arr.shape[0]):
            continue
        if im.mode != mode:
            continue
        a = np.asarray(im.convert(mode))
        if a.shape == arr.shape and np.array_equal(a, arr):
            return p
    return None


def write_or_reuse(d, stem, arr, mode, cache):
    """the same bytes already in the folder -> that file; else <stem>-r6(.png | -shadow.png)"""
    os.makedirs(d, exist_ok=True)
    key = (d, mode)
    if key not in cache:
        cache[key] = None
    found = same_file(d, arr, mode, stem)
    if found:
        return found, "existing file, same bytes (" + os.path.basename(found) + ")"
    p = os.path.join(d, f"{stem}-r6{'-shadow' if mode == 'RGB' else ''}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    Image.fromarray(arr, mode).save(p, compress_level=9)
    return p, "new -r6 file"


def main():
    F6.use_r6_sources()
    G = stack.Grade()
    P = stack.base_parts()
    base8 = GC.u8(os.path.join(P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    assert sha(os.path.join(LAY, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
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
        p = os.path.join(GRD, f"default-scene-r6-set-{s}-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(finals[s]).save(p, compress_level=6)
        print("scene", s, flush=True)
    # ------------------------------------------------------------------ the variants, each on its slot's own Cprev (set B)
    vres, vreg = {}, {}
    for k, nm in VARIANTS:
        Uv, stv = F6.compose6(variants={k: nm})
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
        p = os.path.join(GRD, f"variant-r6-{nm}-set-B-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(T.astype(np.uint8)).save(p, compress_level=6)
        print("variant", nm, flush=True)
    # ------------------------------------------------------------------ disjointness
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    slot_union = {k: regions[(k, "B")].copy() for k in ACCEPTED}
    for nm, rg in vreg.items():
        slot_union[vres[nm]["slot"]] |= rg
    cush_union = regions[("cushions", "A")] | regions[("cushions", "B")] | regions[("cushions", "C")]
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
    # ------------------------------------------------------------------ files
    files, origin, cache = {}, {}, {}
    for (k, s), r in results.items():
        d = os.path.join(LAY, "cushions" if k == "cushions" else k)
        stem = f"set-{s}" if k == "cushions" else CARDS[k][0]
        lp, lo = write_or_reuse(d, stem, r["L"], "RGBA", cache)
        sp, so = write_or_reuse(d, stem, r["S"], "RGB", cache)
        files[(k, s)] = (lp, sp)
        origin[f"{k}{'-' + s if s else ''}"] = dict(layer=lo, shadow=so)
    vfiles = {}
    for nm, r in vres.items():
        k = r["slot"]
        d = os.path.join(LAY, k)
        stem = F6.VCARDS6[nm][0]
        lp, lo = write_or_reuse(d, stem, r["L"], "RGBA", cache)
        sp, so = write_or_reuse(d, stem, r["S"], "RGB", cache)
        vfiles[nm] = (lp, sp)
        origin[nm] = dict(layer=lo, shadow=so)
    changed = sorted({k.split("-")[0] if k.startswith("cushions") else k for k, v in origin.items() if "new" in v["layer"] or "new" in v["shadow"]})
    unexpected = [k for k in changed if k not in FIX6 and k not in NEW_IN_R6]
    man = write_manifest(G, files, results, regions, cush_changed, overlap, origin, vres, vreg, vfiles, disjoint, unexpected)
    write_asset_entries(man, origin)
    print(json.dumps(dict(origin=origin, unexpected_changes=unexpected, disjoint_overlaps=disjoint,
                          variants={nm: dict(region_px=int(vreg[nm].sum()), stats=vres[nm]["stats"]) for nm in vres}), indent=1, default=str))
    return man


def write_manifest(G, files, results, regions, cush_changed, overlap, origin, vres, vreg, vfiles, disjoint, unexpected):
    rel = F6.rel
    layers = [dict(R5BY["base"], sha256=sha(os.path.join(LAY, "base.png")))]
    for k in stack.ORDER:
        if k == "cushions":
            layers.append(R5BY["cushions-shadow"])
            layers.append(R5BY["cushions"])
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
        r5 = R5BY[k]
        if k == "curtains":
            v5 = R5VAR["curtains-v2"]
            rec.update(pass_=PASS6[k], note=r5.get("note"),
                       status_note="R6: the slot's default is 180502 (the designer, wm-phase2-r5-eye section 1; FR-F): its R5 layer, the same bytes "
                                   "as R5's variant file. 554205 is variant 2 (curtains-v2). The true lengths (270 / 260) wait for the designer",
                       r5_as_variant=dict(cut=v5.get("cut"), post_fix=v5.get("post_fix")),
                       designer_conditions=dict(inner_edge="QA R5: within +-0.003 u in 94 of 101 rows (7 rows to 0.0039, 2.3 px, in two folds); "
                                                           "QA recommends accepting", armchair_overlap="QA R5: >= R1's 0.0343 (+2 px): passes 0.028"))
        else:
            for key in ("pass_", "note", "status_note", "fidelity", "render", "fix_r4", "position_status", "r5"):
                if key in r5:
                    rec[key] = r5[key]
            if k in PASS6:
                rec["pass_"] = PASS6[k]
        if k in ("vase", "magazine-holder"):
            rec["r6"] = dict(record="../work-r6/fix-r6.json#" + k, previous_file=r5["file"],
                             summary={kk: FIXREC[k][kk] for kk in ("size", "colour", "axis_check_in_layer", "rods", "dark_line_px") if kk in FIXREC[k]})
            if k == "vase":
                rec["status_note"] = ("R6: re-cut from the raw 4' render (the lit flank back: QA R5 3.1), straightened (the model's lean 3.9 deg; the "
                                      "camera is level), its width to the card (D16: the render drew ~18.3) about the foot; R5's a*b* fix re-solved on "
                                      "the whole body (lit half C* 4.5); the contact shadow by the frozen recipe on the final cut")
            else:
                rec["status_note"] = (r5.get("status_note", "") + ". R6: the rods' satin silver carried into their soft edge (the dark line under the "
                                      "front rod at x 2)")
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(R5MAN["slot_cushions"]["sets"][s], layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       region=GC.region_info(regions[("cushions", s)]), recut_on_new_stack_px=int(cush_changed[s].sum()),
                       build=results[("cushions", s)]["stats"], file_origin=origin[f"cushions-{s}"])
    variants = {}
    for k, nm in VARIANTS:
        r = vres[nm]
        card, opt, sku = F6.VCARDS6[nm]
        cardp = next(p for p in sorted(glob.glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True)))
        lp, sp = vfiles[nm]
        v = dict(id=nm, slot=k, variant=nm.split("-")[-1], z=stack.Z[k], file=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                 blend="normal + its shadow multiply", product=dict(card_id=card, card=rel(cardp), option=opt, sku=sku, default=False),
                 region=GC.region_info(vreg[nm]), build=r["stats"], file_origin=origin[nm], truth=f"../graded/variant-r6-{nm}-set-B-graded-v3c.png",
                 behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in G3.LIGHTS,
                 swaps_with="its slot's default and every variant of the other slots: the slots' regions (all their variants) are disjoint "
                            "(checked: disjoint_overlaps)")
        if nm == "curtains-v2":
            d5 = R5BY["curtains"]
            v.update(pass_="reserve R1 + fix R6 (code: L* and a*b* relative to 180502)", cut=dict(record="../work-reserve (R1)", r5_default_file=d5["file"]),
                     r6=dict(record="../work-r6/fix-r6.json#curtains-v2", targets=FIXREC["curtains-v2"]["targets"], all_met=FIXREC["curtains-v2"]["all_met"]),
                     note="in R5 this id was 180502; from R6 it is 554205 (the slot's default flipped)", in_wheel="the designer: after QA confirms targets 1-6")
        else:
            v5 = R5VAR[nm]
            for key in ("pass_", "cut", "post_fix"):
                if key in v5:
                    v[key] = v5[key]
            if nm in FIXREC:
                fr = FIXREC[nm]
                v["r6"] = dict(record=f"../work-r6/fix-r6.json#{nm}", **{kk: fr[kk] for kk in ("targets", "all_met", "size", "measured") if kk in fr})
                if "colour" in fr:
                    v["r6"]["colour"] = {kk: fr["colour"][kk] for kk in ("targets", "all_met", "after") if kk in fr["colour"]}
        variants.setdefault(k, []).append(v)
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-r6", version="r6 (supersedes manifest-r5.json for the tool; the earlier manifests are kept)",
        room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-12", author="render-agent",
        brief="briefs/render-wm-tool-r6-codefix-2026-11-12.md (code only, 0 tokens) from qa/reports/2026-11-11-wm-tool-phase2-r5.md and "
              "docs/proposals/wm-phase2-r5-eye-2026-11-11.md",
        approval=R5MAN["approval"] + "; R6: code only, 0 tokens (studio rules: 0-token code fixes are decided at once); the curtains' default "
                                     "order: the designer under FR-F (the coordinator: within the designer's authority, the owner informed)",
        status="phase 2: 12 defaults + %d variants as layers, after R6. Not QA'd; for qa-agent and master-designer. HD_PUBLIC=0 only. Not in "
               "R6 (waiting): the planter's colour (the designer), the curtains' true lengths (the designer), the table group (WM-T2 coordinates)" % len(vres),
        grade=R5MAN["grade"], grade_params=G.record(), size=R5MAN["size"], color=R5MAN["color"],
        compose=dict(R5MAN["compose"], order=[l_["id"] for l_ in layers]),
        shadow_recipe=dict(R5MAN["shadow_recipe"], applies_to="every layer; R6's new cuts (the vases) measure their contact shadow with "
                                                             "extract.shadow_one unchanged; the other R6 changes keep their shadow files"),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        variants=variants, disjoint_overlaps=disjoint, vase_point=R5MAN["vase_point"], pending={},
        changed_in_r6=dict(defaults=FIX6, variants=sorted(NEW_IN_R6), files=origin, unexpected_other_changes=unexpected,
                           curtains_flip="default 554205 -> 180502; curtains-v2 180502 -> 554205"),
        not_in_r6=dict(planter_colour="waiting on the designer (the pre-approved darkening would be 25-29 L* on the lit shoulder)",
                       curtain_lengths="waiting on the designer's instruction (owner: SUP-C1 / WM-C3, the real 270 / 260)",
                       table_group="waiting on the WM-T2 coordinates in data/slots"),
        light_layers=R5MAN["light_layers"],
        files=dict(build="grade_cut_r6.py (fix_r6.py, grade_cut_r5.py, ...)", fixes="../fix_r6.py -> ../work-r6/ (../work-r6/fix-r6.json)",
                   verify="verify_layers_r6.py", verification="verify-layers-r6.json", lock="../lock_r6.py -> ../lock-and-grade-check-r6.json",
                   crops="../crops-r6/ (../make_crops_r6.py)", sheet="../phase2-r6-sheet.jpg", asset_manifest_entries="asset-manifest-entries-r6.json",
                   verify_usage="python3 verify_layers_r6.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=dict(R5MAN["tokens"], this_build=0, fix_r6=0),
        held=G12.HELD,
    )
    p = os.path.join(LAY, "manifest-r6.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False, default=float)
    return man


def write_asset_entries(man, origin):
    status = ("warm-modern tool, phase 2 R6 (0-token code fixes after QA R5 and the designer's eye, 2026-11-12); v3c layers cut from the graded "
              "composites; verified by layers/verify_layers_r6.py; awaiting qa-agent and master-designer; HD_PUBLIC=0")
    base = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
    out = []

    def add(eid, path, kind, extra=None):
        out.append(dict(id=eid, path=path, kind=kind, model="seedream-5-pro i2i 2K + code (R6: code only)", status=status, style="warm-modern",
                        room="living-room", created="2026-11-12", recipe=base + "grade_cut_r6.py (fix_r6.py)", **(extra or {})))
    for l_ in man["layers"]:
        k = l_.get("slot")
        if "file" not in l_ or k in (None, "cushions"):
            continue
        is_sh = l_["id"].endswith("-shadow")
        o = origin[k]["shadow" if is_sh else "layer"]
        if not o.startswith("new"):
            continue
        prod = next(x for x in man["layers"] if x["id"] == k)
        add(f"wm-tool-ph2-r6-{l_['id']}", base + "layers/" + l_["file"],
            f"tool {'shadow layer, RGB multiply (white = none)' if is_sh else 'product layer, RGBA straight alpha'}, {k}, default, v3c",
            None if is_sh else dict(product_id=prod["product"]["card_id"], sku=prod["product"]["sku"]))
    for k, vs in man["variants"].items():
        for v in vs:
            for is_sh in (False, True):
                if not origin[v["id"]]["shadow" if is_sh else "layer"].startswith("new"):
                    continue
                add(f"wm-tool-ph2-r6-{v['id']}{'-shadow' if is_sh else ''}", base + "layers/" + (v["shadow"] if is_sh else v["file"]),
                    f"tool {'shadow layer, RGB multiply' if is_sh else 'product layer, RGBA straight alpha'}, {k}, variant {v['variant']}, v3c",
                    None if is_sh else dict(product_id=v["product"]["card_id"], sku=v["product"]["sku"]))
    for s in "BAC":
        add(f"wm-tool-ph2-r6-default-scene-{s}", base + f"graded/default-scene-r6-set-{s}-graded-v3c.png",
            f"graded default scene (12 defaults, R6: curtains 180502), set {s}, v3c")
    for k, vs in man["variants"].items():
        for v in vs:
            add(f"wm-tool-ph2-r6-truth-{v['id']}", base + f"graded/variant-r6-{v['id']}-set-B-graded-v3c.png", f"graded truth of variant {v['id']}, set B, v3c")
    add("wm-tool-ph2-r6-layers-manifest", base + "layers/manifest-r6.json", "tool layers manifest r6 (12 defaults + variants)")
    add("wm-tool-ph2-r6-sheet", base + "phase2-r6-sheet.jpg", "review sheet R6: the default scene and each slot's options, before / after")
    add("wm-tool-ph2-r6-crops", base + "crops-r6/", "crops of the R6 fixes, before / after, at 100 % and x4")
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-12; R6: new files only, the entries in a separate JSON for "
                    "the manager); layers and shadows whose bytes did not change keep their earlier entries", assets=out)
    p = os.path.join(LAY, "asset-manifest-entries-r6.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
