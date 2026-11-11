#!/usr/bin/env python3
"""
grade_cut_r3.py: the v3c display files and layers of the warm-modern tool, phase 2, after the fix passes R3a / R3b (render-agent,
2026-11-11). Brief: briefs/render-wm-tool-phase2-fix-r3-2026-11-11.md. Code only, 0 tokens. NEW FILES ONLY: steps 1-3 and r12 files are
read, never written.

The same method as grade_cut.py / grade_cut_r12.py (one v3c grade, stack.Grade; every layer cut from the graded composites, never graded
on its own; the cushion sets kept byte for byte where the stack under them did not change), on the stack of ALL 12 defaults:
  steps 1-3 (work/layers):     rug, vase, floor-lamp, framed-art, accent-sconces, candle-holders
  reserve (work-reserve/):     curtains (R1), magazine-holder Orange (R1), bowl (R2, position PROVISIONAL pending WM-T2)
  fix R3 (work-r3/):           planter + basket (R3a), pendant (R3b, rendered off; its light layer is made in code later)
A layer whose recomputed bytes equal an existing file (steps 1-3 or r12) keeps that file (the manifest points to it); one that differs is
written as <name>-r3.png. The three new products get their own new folders.

Writes: layers/<slot>/... (new files), layers/manifest-r3.json, graded/default-scene-r3-set-<X>-graded-v3c.png,
layers/asset-manifest-entries-r3.json.
  python3 grade_cut_r3.py        then   python3 layers/verify_layers_r3.py
"""
import glob
import json
import os

import cv2
import numpy as np
from PIL import Image

import grade_cut as GC
import grade_cut_r12 as G12
import phase2_wm as W
import reserve_r3 as R3
import stack
from phase2_wm import P1

HERE = W.HERE
LAY = os.path.join(HERE, "layers")
GRD = os.path.join(HERE, "graded")
REPO = W.REPO
FID12 = G12.FID
FID3 = json.load(open(os.path.join(R3.WR3, "fidelity-r3.json")))["products"]
FETCH3 = {p: json.load(open(os.path.join(R3.WR3, f"{p}-fetch.json"))) for p in ("r3a", "r3b")}

STEP13 = G12.STEP13
RESERVE = G12.RESERVE
FIX = ["planter", "basket", "pendant"]
ACCEPTED = STEP13 + RESERVE + FIX
CARDS = dict(G12.CARDS)
CARDS.update({
    "planter": ("planter-cj-cement-ribbed-belly", {"color": "beige", "size": "large"}, "CJJT154204209IR"),
    "basket": ("basket-cj-jute-rope-cylinder", {"other": "large"}, "CJYD186026903CX"),
    "pendant": ("pendant-cj-tiered-fabric-drum", {}, "CJYD247032902BY"),
})
NOTES = dict(G12.NOTES)
NOTES.update({
    "planter": "R3a. Size and place pass on the clay (belly 42 / height 35.5 at (-1.95, 0.42)); SHAPE PARTIAL: the opening reads ~42 cm "
               "against the card's 35.5, so the shoulder under the rim is straighter than the card's belly (it shows only on the pot's "
               "visible left side; the basket hides ~75 % of the pot by design, slots 1.9.2). The olive tree is a filler (not sold), inside "
               "its envelope (crown ~51 cm, top Z ~1.24). The pot's hidden part is NOT in this layer: a basket variant that hides less of "
               "it needs the pot drawn whole (variant stage)",
    "basket": "R3a. In front of the pot as planned; body 35 cm, floor centre within 0.5 cm of the clay read the same way (2.7 cm from the "
              "plan's point by that method's own bias)",
    "pendant": "R3b. Rendered OFF; its light layer is made in code later (plan section 2, step 8). Shade bottom fits Z 1.885 (owner's 1.90, "
               "V7Q7 b; R2 was 1.80), width 50.7 cm, centre +0.2 cm. No shadow layer in the slot (has_shadow_layer false): its shadow "
               "file is all white",
})
LIGHTS = set(GC.LIGHTS) | {"pendant"}
PASS = {k: "steps 1-3" for k in STEP13}
PASS.update({"curtains": "reserve R1", "magazine-holder": "reserve R1", "bowl": "reserve R2", "planter": "fix R3a", "basket": "fix R3a",
             "pendant": "fix R3b"})
G12.SRC.update({k: (os.path.join(R3.WR3, "layers"), os.path.join(R3.WR3, "shadows")) for k in FIX})


def sha(p):
    return GC.sha(p)


def main():
    os.makedirs(LAY, exist_ok=True)
    G = stack.Grade()
    P = stack.base_parts()
    base8 = GC.u8(os.path.join(P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    assert sha(os.path.join(LAY, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
    items = set(ACCEPTED) | {"cushions"}
    results, regions, finals, cush_changed = {}, {}, {}, {}
    for s in "BAC":
        U, steps = G12.compose(items, P, cushion_set=s)
        Aun = np.zeros(P["fa"].shape, np.float32)
        Cprev = base8.copy()
        appr = GC.u8(os.path.join(P1, f"composite-set-{s}-v3-graded-v3c.png"))
        for st in steps:
            k, reg = st["k"], st["region"]
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
        p = os.path.join(GRD, f"default-scene-r3-set-{s}-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(finals[s]).save(p, compress_level=6)
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    # write the layers: reuse an existing file (steps 1-3 or r12) when the bytes are the same, else a new -r3 file
    files, reused = {}, {}
    for (k, s), r in results.items():
        if k == "cushions":
            d = os.path.join(LAY, "cushions")
            stem = f"set-{s}"
        else:
            d = os.path.join(LAY, k)
            stem = CARDS[k][0]
        os.makedirs(d, exist_ok=True)
        key = f"{k}{'-' + s if s else ''}"
        found = None
        for suf in ("", "-r12"):
            lp_old, sp_old = os.path.join(d, f"{stem}{suf}.png"), os.path.join(d, f"{stem}{suf}-shadow.png")
            if os.path.exists(lp_old) and os.path.exists(sp_old):
                if (np.array_equal(np.asarray(Image.open(lp_old)), r["L"]) and
                        np.array_equal(np.asarray(Image.open(sp_old).convert("RGB")), r["S"])):
                    found = (lp_old, sp_old, "existing file, same bytes (" + ("steps 1-3 / r12 base name" if not suf else "r12") + ")")
                    break
        if found:
            files[(k, s)] = found[:2]
            reused[key] = found[2]
            continue
        if os.path.exists(os.path.join(d, f"{stem}.png")):
            lp, sp = os.path.join(d, f"{stem}-r3.png"), os.path.join(d, f"{stem}-r3-shadow.png")
            reused[key] = "recomputed bytes differ: new -r3 file"
        else:
            lp, sp = os.path.join(d, f"{stem}.png"), os.path.join(d, f"{stem}-shadow.png")
            reused[key] = "new product: new file"
        assert not os.path.exists(lp) and not os.path.exists(sp), f"would overwrite {lp}"
        Image.fromarray(r["L"], "RGBA").save(lp, compress_level=9)
        Image.fromarray(r["S"], "RGB").save(sp, compress_level=9)
        files[(k, s)] = (lp, sp)
    man = write_manifest(G, files, results, regions, cush_changed, overlap, reused)
    write_asset_entries(man)
    print(json.dumps(dict(reuse=reused, build={f"{k}{'-' + s if s else ''}": v["stats"] for (k, s), v in results.items()}), indent=1))
    return man


def write_manifest(G, files, results, regions, cush_changed, overlap, reused):
    rel = W.rel
    layers = [dict(id="base", file="base.png", blend="normal", z=0, opaque=True,
                   replaces_base_layers=["shell (z 0)", "fixed-furniture-shadow (z 34, multiply)", "fixed-furniture (z 40)"],
                   source=rel(os.path.join(P1, "layers-v3c/base.png")), how="byte copy of the approved v3c base (= shell-furniture-v3-graded-v3c.png)",
                   sha256=sha(os.path.join(LAY, "base.png")))]
    for k in stack.ORDER:
        if k == "cushions":
            layers.append(dict(id="cushions-shadow", slot="cushions", blend="multiply", z=54, per_set="sets.<X>.shadow", white_is_none=True, format="RGB, no alpha"))
            layers.append(dict(id="cushions", slot="cushions", blend="normal", z=55, per_set="sets.<X>.layer", format="RGBA, straight alpha",
                               how="the approved v3c set where the stack under it did not change; re-cut on the new stack where it did (rug, floor lamp)"))
            continue
        lp, sp = files[(k, None)]
        card, opt, sku = CARDS[k]
        st = results[(k, None)]["stats"]
        reg = regions[(k, "B")]
        cardp = next(p for p in sorted(glob.glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True)))
        layers.append(dict(id=f"{k}-shadow", slot=k, blend="multiply", z=stack.Z[k] - 1, file=os.path.relpath(sp, LAY), opaque=True, white_is_none=True,
                           format="RGB, no alpha"))
        rec = dict(id=k, slot=k, blend="normal", z=stack.Z[k], file=os.path.relpath(lp, LAY), format="RGBA, straight alpha",
                   product=dict(card_id=card, card=rel(cardp), option=opt, sku=sku, default=True),
                   region=GC.region_info(reg), build=st, pass_=PASS[k], file_origin=reused[k],
                   behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in LIGHTS)
        if k in stack.BEHIND:
            rec["note"] = ("stands behind the fixed furniture, which the base already holds: its alpha leaves the furniture whole and its soft edge is "
                           "solved against it (composed physically in stack.py: (behind x shadow + product) x (1 - fa) + furniture x fa)")
        if k in NOTES:
            rec["status_note"] = NOTES[k]
        if k == "bowl":
            rec["position_status"] = "provisional, pending WM-T2"
        if k in FIX:
            rec["fidelity"] = {kk: vv for kk, vv in FID3[k].items() if kk not in ("card", "option", "sku")}
            pid = "r3a" if k != "pendant" else "r3b"
            rec["render"] = dict(job=FETCH3[pid]["id"], raw=FETCH3[pid]["raw"], model_change_vs_placeholder_dE=FETCH3[pid]["products"][k]["model_change_vs_placeholder_dE"])
        elif k in FID12:
            rec["fidelity"] = {kk: vv for kk, vv in FID12[k].items() if kk not in ("card", "option", "sku")}
            if k == "curtains":
                rec["fidelity"]["curtains_vs_armchair"] = FID12["curtains_vs_armchair"]
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       products="as layers-v3c/manifest.json sets." + s, region=GC.region_info(regions[("cushions", s)]),
                       recut_on_new_stack_px=int(cush_changed[s].sum()), build=results[("cushions", s)]["stats"], file_origin=reused[f"cushions-{s}"],
                       approved_source=rel(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png")))
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-r3", version="r3 (supersedes manifest-r12.json for the tool; manifest.json and manifest-r12.json are kept)",
        room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-11", author="render-agent",
        brief="briefs/render-wm-tool-phase2-fix-r3-2026-11-11.md (continuing the reserve brief and briefs/render-wm-tool-phase2-2026-11-10.md)",
        approval="PH2-WM (owner, 2026-11-10); the reserve 1,300 by the manager; R3 under SPEND2 (owner, 2026-11-10), two passes at 650 by "
                 "the manager; base and cushions: AP3-WM + QA qa/reports/2026-11-10-wm-tool-layers-v3c.md",
        status="phase 2 defaults COMPLETE as layers: 12 of 12 (6 from steps 1-3, 3 from the reserve, 3 from fix R3). The bowl's position is "
               "provisional (WM-T2); the planter's shape is partial (its opening); the curtains' colour is partial. Not QA'd; for qa-agent "
               "and master-designer. HD_PUBLIC=0 only",
        grade="v3c, ONE display grade (stack.Grade = phase 1 grade_v3c; base.png reproduced byte for byte). Every layer is cut from the graded "
              "composites; no layer is graded on its own; the site applies no further grade",
        grade_params=G.record(),
        size=json.load(open(os.path.join(P1, "layers-v3c/manifest.json")))["size"],
        color="8-bit sRGB, no ICC profile. Blending on the sRGB-encoded values (CSS mix-blend-mode, canvas 2D, the engine's GL path)",
        compose=dict(order=[l_["id"] for l_ in layers],
                     formula="for each product in order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, straight alpha; "
                             "the cushions: one set at a time, its shadow and its layer together",
                     swap_region="per product: alpha > 0 or any shadow channel < 255; a product (or a set) changes nothing outside its region"),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        pending={},
        light_layers="the floor lamp, the wall lamps and the pendant are rendered OFF as products; their light layers are made in code later "
                     "(plan section 2, step 8)",
        files=dict(build="grade_cut_r3.py (with grade_cut_r12.py, reserve_r3.py, stack.py, extract.py, phase2_wm.py)", verify="verify_layers_r3.py",
                   verification="verify-layers-r3.json", fidelity="../work-r3/fidelity-r3.json (planter, basket, pendant); "
                   "../work-reserve/fidelity-r12.json (curtains, magazine holder, bowl)",
                   asset_manifest_entries="asset-manifest-entries-r3.json", verify_usage="python3 verify_layers_r3.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=dict(this_build=0, fix_passes=1300, reserve_passes=1300, steps_1_3=1950),
        held=G12.HELD,
    )
    p = os.path.join(LAY, "manifest-r3.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False)
    return man


def write_asset_entries(man):
    status = ("warm-modern tool, phase 2 after the fix passes R3a / R3b (briefs/render-wm-tool-phase2-fix-r3-2026-11-11.md, SPEND2, the "
              "manager's two passes); all 12 defaults layered; v3c layers cut from the graded composites; verified by "
              "layers/verify_layers_r3.py (exit 0); awaiting qa-agent and master-designer")
    base = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
    out = []
    for l_ in man["layers"]:
        k = l_.get("slot")
        if "file" not in l_ or k in (None, "cushions"):
            continue
        prod = next(x for x in man["layers"] if x["id"] == k)
        if k not in FIX and not prod.get("file_origin", "").startswith("recomputed"):
            continue
        is_sh = l_["id"].endswith("-shadow")
        e = dict(id=f"wm-tool-ph2-{l_['id']}", path=base + "layers/" + l_["file"],
                 kind=(f"tool shadow layer, RGB multiply (white = none), {k}, default, v3c" if is_sh
                       else f"tool product layer, RGBA straight alpha, normal, {k}, default, v3c"),
                 model="seedream-5-pro i2i 2K + code", status=status + ("; " + NOTES[k] if (k in NOTES and not is_sh and k in FIX) else ""),
                 style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r3.py")
        if not is_sh:
            e.update(product_id=prod["product"]["card_id"], sku=prod["product"]["sku"])
        out.append(e)
    for s in "BAC":
        out.append(dict(id=f"wm-tool-ph2-r3-default-scene-{s}", path=base + f"graded/default-scene-r3-set-{s}-graded-v3c.png",
                        kind=f"graded default scene (12 of 12 defaults), set {s}, v3c", model="code", status=status
                        + ("; the full default scene (cushion set B is the default, CAM1)" if s == "B" else ""),
                        style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r3.py"))
    out.append(dict(id="wm-tool-ph2-r3-layers-manifest", path=base + "layers/manifest-r3.json", kind="tool layers manifest r3 (12 defaults)",
                    model="code", status=status, style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r3.py"))
    out.append(dict(id="wm-tool-ph2-r3-sheet", path=base + "phase2-r3-default-scene-sheet.jpg", kind="review sheet: the full default scene "
                    "with set B (12 defaults), sets A / C, the three new layers, R3a / R3b inputs and renders", model="code", status=status,
                    style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "make_sheet_r3.py"))
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-11; the R3 brief: new files only, the entries in a "
                    "separate JSON for the manager). Layers whose bytes did not change keep their entries in asset-manifest-entries.json "
                    "(steps 1-3) and asset-manifest-entries-r12.json (reserve)", assets=out)
    p = os.path.join(LAY, "asset-manifest-entries-r3.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
