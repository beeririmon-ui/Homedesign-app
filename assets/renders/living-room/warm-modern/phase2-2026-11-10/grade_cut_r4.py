#!/usr/bin/env python3
"""
grade_cut_r4.py: the v3c display files and layers of the warm-modern tool, phase 2, after the code fixes R4 (render-agent, 2026-11-11).
Task: the manager's code-only fixes from QA's phase-2 checkpoint (qa/reports/2026-11-11-wm-tool-phase2-checkpoint.md) and the designer's shade
targets (docs/proposals/wm-phase2-f3-decisions-2026-11-11.md section 5). 0 tokens, no var2, no network. NEW FILES ONLY: earlier files are
read, never written.

The same method as grade_cut.py / grade_cut_r12.py / grade_cut_r3.py (one v3c grade, stack.Grade; every layer cut from the graded composites,
never graded on its own; the cushion sets kept byte for byte where the stack under them did not change), on the stack of all 12 defaults,
with five products read from work-r4/ (fix_r4.py):
  floor-lamp   the shade fabric toned off (section 5)                         work-r4/layers/floor-lamp.png (+ free alpha, shadow as before)
  vase         scaled to the card at its own base; placement pending          work-r4/layers/vase.png, work-r4/shadows/vase.png
  planter      left side and bottom re-cut, contact shadow to the edge         work-r4/...
  basket       right edge re-cut, contact shadow to the edge                   work-r4/...
  pendant      ceiling canopy re-cut whole                                     work-r4/layers/pendant.png
A layer whose recomputed bytes equal an existing file (steps 1-3, r12 or r3) keeps that file; one that differs is written as <name>-r4.png.

Writes: layers/<slot>/...-r4.png (new files), layers/manifest-r4.json, graded/default-scene-r4-set-<X>-graded-v3c.png,
layers/asset-manifest-entries-r4.json.
  python3 fix_r4.py all   then   python3 grade_cut_r4.py   then   python3 layers/verify_layers_r4.py   and   python3 lock_r4.py
"""
import glob
import json
import os

import cv2
import numpy as np
from PIL import Image

import fix_r4 as F
import grade_cut as GC
import grade_cut_r12 as G12
import grade_cut_r3 as G3
import phase2_wm as W
import stack
from phase2_wm import P1

HERE = W.HERE
LAY = os.path.join(HERE, "layers")
GRD = os.path.join(HERE, "graded")
REPO = W.REPO
WR4 = F.WR4
FIX4 = ["floor-lamp", "vase", "planter", "basket", "pendant"]
ACCEPTED = G3.ACCEPTED
CARDS = G3.CARDS
FIXREC = json.load(open(F.REC))
G12.SRC.update({k: (os.path.join(WR4, "layers"), os.path.join(WR4, "shadows")) for k in FIX4})
NOTES = dict(G3.NOTES)
NOTES.update({
    "floor-lamp": "R4: the shade fabric toned OFF to the designer's targets (docs/proposals/wm-phase2-f3-decisions-2026-11-11.md section 5): "
                  "the window side lighter, the inside and the lower edge in shade, no warmer than the wall; the folds from the step-2 "
                  "raw render; the collar, stem, base and chain unchanged. Rendered off; its light layer is made in code later",
    "vase": "R4: SIZE FIXED; PLACEMENT PENDING THE DESIGNER. Scaled in code to the card (Large D16 x H32) about its own base (the foot's "
            "contact point), x and y separately; its contact shadow redone about the same anchor. Not moved: it stands ~0.29 m nearer the "
            "camera than the plan point (-2.42, 1.35) (on the bench, about (-2.19, 1.57)); the plan point would be a re-render (~650)",
    "planter": G3.NOTES["planter"] + ". R4: the left side and the bottom re-cut from the R3a render (alpha from the render, outline "
               "smoothed, edge colour un-mixed) and the contact shadow carried to the edge (QA: the dark rim and the ghost)",
    "basket": G3.NOTES["basket"] + ". R4: the right edge re-cut from the R3a render and the contact shadow carried to the edge (QA: the "
              "light line)",
    "pendant": G3.NOTES["pendant"] + ". R4: the ceiling canopy re-cut whole from the R3b render (QA: a half disc and a separate crescent)",
})
PASS = dict(G3.PASS)
PASS.update({"floor-lamp": "steps 1-3 + fix R4 (code)", "vase": "steps 1-3 + fix R4 (code)", "planter": "fix R3a + fix R4 (code re-cut)",
             "basket": "fix R3a + fix R4 (code re-cut)", "pendant": "fix R3b + fix R4 (code re-cut)"})


def sha(p):
    return GC.sha(p)


def remeasure(files):
    """the numbers QA reads on the layers that changed: the shade's five targets (QA's p2_lamp.py masks, on the r4 set-B scene), the
    vase as fix_r4 measured it, the basket's body width and the planter's left edge (QA's p2_geometry.py reading), the canopy's pieces"""
    out = {}
    G8 = np.asarray(Image.open(os.path.join(GRD, "default-scene-r4-set-B-graded-v3c.png")).convert("RGB"))
    A8 = np.asarray(Image.open(files[("floor-lamp", None)][0]))[..., 3]
    M = F.qa_lamp_masks(A8)
    Lw = F.f32(os.path.join(WR4, "layers", "floor-lamp.png"))
    core, ring = F.collar_mask(F.f32(F.LAMP_W)[..., :3], Lw[..., 3], M)
    out["floor-lamp"] = F.lamp_measure(G8, M, M["shade"] & ~core & ~ring)
    out["floor-lamp"]["masks"] = dict(qa_shade_px=int(M["shade"].sum()), collar_in_qa_shade_px=int((M["shade"] & (core | ring)).sum()),
                                      note="QA's shade mask (alpha 255 in the cone's rows, eroded) includes the brass collar's top, which "
                                           "section 5 leaves unchanged; 'fabric_only' leaves the collar and its 1 px ring out")
    G0 = np.asarray(Image.open(os.path.join(GRD, "default-scene-r3-set-B-graded-v3c.png")).convert("RGB"))
    out["floor-lamp"]["r3_for_comparison"] = F.lamp_measure(G0, M, M["shade"] & ~core & ~ring)
    out["vase"] = {k: FIXREC["vase"][k] for k in ("measured_before", "before_cm", "measured_after", "after_cm", "base_kept", "card_at_its_place_px",
                                                  "stands_at", "scale", "status")}
    a = np.asarray(Image.open(files[("basket", None)][0]))[..., 3] >= 128
    w = a.sum(1)
    a3 = np.asarray(Image.open(os.path.join(LAY, "basket/basket-cj-jute-rope-cylinder.png")))[..., 3] >= 128
    out["basket"] = dict(body_width_px_qa_method=int(w.max()), r3=int(a3.sum(1).max()), card_px_D35=133.2,
                         right_edge_rows_1080_1230_median_px={"r3": float(np.median([np.nonzero(a3[y])[0].max() for y in range(1080, 1231)])),
                                                              "r4": float(np.median([np.nonzero(a[y])[0].max() for y in range(1080, 1231)]))})
    a = np.asarray(Image.open(files[("planter", None)][0]))[..., 3] >= 128
    a3 = np.asarray(Image.open(os.path.join(LAY, "planter/planter-cj-cement-ribbed-belly.png")))[..., 3] >= 128
    out["planter"] = dict(left_edge_min_rows_1040_1195={"r3": int(min(np.nonzero(a3[y])[0].min() for y in range(1040, 1195) if a3[y].any())),
                                                         "r4": int(min(np.nonzero(a[y])[0].min() for y in range(1040, 1195) if a[y].any()))},
                          expected_belly_left_px=958.2, bottom_row_at_x975={"r3": int(np.nonzero(a3[:, 975])[0].max()), "r4": int(np.nonzero(a[:, 975])[0].max())})
    a = np.asarray(Image.open(files[("pendant", None)][0]))[..., 3]
    n, _, st, _ = cv2.connectedComponentsWithStats((a[:62] >= 128).astype(np.uint8), connectivity=8)
    out["pendant"] = dict(canopy_pieces_above_row_62_px=[int(s) for s in st[1:, 4] if s >= 5], canopy=FIXREC["pendant"]["canopy"],
                          note="one piece: the disc, joined to the cord (r3: a half disc with the cord, and a separate crescent)")
    return out


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
        p = os.path.join(GRD, f"default-scene-r4-set-{s}-graded-v3c.png")
        assert not os.path.exists(p) or os.environ.get("REDO"), p
        Image.fromarray(finals[s]).save(p, compress_level=6)
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    files, reused = {}, {}
    for (k, s), r in results.items():
        if k == "cushions":
            d, stem = os.path.join(LAY, "cushions"), f"set-{s}"
        else:
            d, stem = os.path.join(LAY, k), CARDS[k][0]
        os.makedirs(d, exist_ok=True)
        key = f"{k}{'-' + s if s else ''}"
        found = None
        for suf in ("", "-r12", "-r3"):
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
        lp, sp = os.path.join(d, f"{stem}-r4.png"), os.path.join(d, f"{stem}-r4-shadow.png")
        reused[key] = "recomputed bytes differ: new -r4 file" + (" (fix R4)" if k in FIX4 else " (the stack under it changed)")
        assert not os.path.exists(lp) and not os.path.exists(sp), f"would overwrite {lp}"
        Image.fromarray(r["L"], "RGBA").save(lp, compress_level=9)
        Image.fromarray(r["S"], "RGB").save(sp, compress_level=9)
        files[(k, s)] = (lp, sp)
    unexpected = [k for k, v in reused.items() if v.startswith("recomputed") and k not in FIX4]
    meas = remeasure(files)
    man = write_manifest(G, files, results, regions, cush_changed, overlap, reused, meas, unexpected)
    write_asset_entries(man)
    print(json.dumps(dict(reuse=reused, unexpected_changes=unexpected,
                          lamp_targets=meas["floor-lamp"]["fabric_only"]["targets"], lamp_targets_qa_mask=meas["floor-lamp"]["qa_shade_mask"]["targets"],
                          vase=meas["vase"]["after_cm"], basket=meas["basket"], planter=meas["planter"], pendant=meas["pendant"]["canopy_pieces_above_row_62_px"]),
                     indent=1, default=str))
    return man


def write_manifest(G, files, results, regions, cush_changed, overlap, reused, meas, unexpected):
    rel = W.rel
    r3 = json.load(open(os.path.join(LAY, "manifest-r3.json")))
    r3by = {l_["id"]: l_ for l_ in r3["layers"]}
    layers = [dict(r3by["base"], sha256=sha(os.path.join(LAY, "base.png")))]
    for k in stack.ORDER:
        if k == "cushions":
            layers.append(r3by["cushions-shadow"])
            layers.append(r3by["cushions"])
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
                   behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in G3.LIGHTS)
        for key in ("note", "status_note", "position_status", "fidelity", "render"):
            if key in r3by[k]:
                rec[key] = r3by[k][key]
        if k in NOTES:
            rec["status_note"] = NOTES[k]
        if k in FIX4:
            rec["fix_r4"] = dict(record="../work-r4/fix-r4.json#" + {"planter": "edges", "basket": "edges"}.get(k, k), remeasured=meas[k],
                                 previous_file=r3by[k]["file"])
        if k == "vase":
            rec["status"] = "size fixed; placement pending the designer"
            rec["position_status"] = "pending the designer: accept its place on the bench (~0.29 m nearer the camera than the plan point) or re-render at the plan point (~650)"
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(r3["slot_cushions"]["sets"][s], layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       region=GC.region_info(regions[("cushions", s)]), recut_on_new_stack_px=int(cush_changed[s].sum()),
                       build=results[("cushions", s)]["stats"], file_origin=reused[f"cushions-{s}"])
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-r4", version="r4 (supersedes manifest-r3.json for the tool; manifest.json, manifest-r12.json and "
        "manifest-r3.json are kept)", room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-11", author="render-agent",
        brief="the manager's code-only task (2026-11-11): QA's phase-2 checkpoint fixes (qa/reports/2026-11-11-wm-tool-phase2-checkpoint.md) and the "
              "designer's shade targets (docs/proposals/wm-phase2-f3-decisions-2026-11-11.md section 5)",
        approval=r3["approval"] + "; R4: code only, 0 tokens (studio rules: 0-token code fixes are decided at once)",
        status="phase 2 defaults: 12 of 12 as layers, after the R4 code fixes (the shade toned off; the pendant canopy, the basket's right edge and "
               "the planter's left side and bottom re-cut; the vase's SIZE fixed, its PLACEMENT pending the designer). The bowl's position is "
               "provisional (WM-T2); the planter's shape is partial (its opening); the curtains' colour is partial. Not QA'd; for qa-agent "
               "(the changed regions) and master-designer. HD_PUBLIC=0 only",
        grade=r3["grade"], grade_params=G.record(), size=r3["size"], color=r3["color"],
        compose=dict(r3["compose"], order=[l_["id"] for l_ in layers]),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        pending={},
        changed_in_r4=dict(products=FIX4, files={k: reused[k] for k in FIX4}, unexpected_other_changes=unexpected,
                           unchanged_products=[k for k in ACCEPTED if k not in FIX4], cushion_sets={s: reused[f"cushions-{s}"] for s in "BAC"}),
        light_layers=r3["light_layers"] + ". The floor lamp's shade is toned off in R4 (section 5), so the light layer alone carries the glow",
        files=dict(build="grade_cut_r4.py (with fix_r4.py, grade_cut_r3.py, grade_cut_r12.py, reserve_r3.py, stack.py, extract.py, phase2_wm.py)",
                   fixes="fix_r4.py -> ../work-r4/ (record: ../work-r4/fix-r4.json)", verify="verify_layers_r4.py", verification="verify-layers-r4.json",
                   lock="../lock_r4.py -> ../lock-and-grade-check-r4.json", crops="../crops-r4/ (make_crops_r4.py)", sheet="../phase2-r4-default-scene-sheet.jpg",
                   asset_manifest_entries="asset-manifest-entries-r4.json", verify_usage="python3 verify_layers_r4.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=dict(r3["tokens"], this_build=0, fix_r4=0),
        held=G12.HELD,
    )
    p = os.path.join(LAY, "manifest-r4.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False, default=float)
    return man


def write_asset_entries(man):
    status = ("warm-modern tool, phase 2 after the code fixes R4 (the manager's code-only task from QA's phase-2 checkpoint, 2026-11-11; 0 tokens); "
              "v3c layers cut from the graded composites; verified by layers/verify_layers_r4.py; awaiting qa-agent (the changed regions)")
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
        e = dict(id=f"wm-tool-ph2-r4-{l_['id']}", path=base + "layers/" + l_["file"],
                 kind=(f"tool shadow layer, RGB multiply (white = none), {k}, default, v3c" if is_sh
                       else f"tool product layer, RGBA straight alpha, normal, {k}, default, v3c"),
                 model="seedream-5-pro i2i 2K + code (R4: code only)", status=status + ("; " + NOTES[k] if (k in NOTES and not is_sh) else ""),
                 style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r4.py (fix_r4.py)",
                 supersedes=base + "layers/" + (prod["fix_r4"]["previous_file"] if not is_sh else
                                                 prod["fix_r4"]["previous_file"].replace(".png", "-shadow.png")))
        if not is_sh:
            e.update(product_id=prod["product"]["card_id"], sku=prod["product"]["sku"])
            if k == "vase":
                e["flag"] = "size fixed; placement pending the designer"
        out.append(e)
    for s in "BAC":
        out.append(dict(id=f"wm-tool-ph2-r4-default-scene-{s}", path=base + f"graded/default-scene-r4-set-{s}-graded-v3c.png",
                        kind=f"graded default scene (12 of 12 defaults, R4), set {s}, v3c", model="code", status=status
                        + ("; the full default scene (cushion set B is the default, CAM1)" if s == "B" else ""),
                        style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r4.py"))
    out.append(dict(id="wm-tool-ph2-r4-layers-manifest", path=base + "layers/manifest-r4.json", kind="tool layers manifest r4 (12 defaults)",
                    model="code", status=status, style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "grade_cut_r4.py"))
    out.append(dict(id="wm-tool-ph2-r4-sheet", path=base + "phase2-r4-default-scene-sheet.jpg", kind="review sheet: the full default scene "
                    "with set B after R4, sets A / C, and the five fixes before / after", model="code", status=status,
                    style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "make_sheet_r4.py"))
    out.append(dict(id="wm-tool-ph2-r4-crops", path=base + "crops-r4/", kind="before / after crops of the five R4 fixes at 100 % and x4",
                    model="code", status=status, style="warm-modern", room="living-room", created="2026-11-11", recipe=base + "make_crops_r4.py"))
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-11; the R4 task: new files only, the entries in a "
                    "separate JSON for the manager). Each r4 layer entry names the r3 / steps-1-3 file it supersedes for the tool; layers "
                    "whose bytes did not change keep their earlier entries (asset-manifest-entries.json, -r12.json, -r3.json)", assets=out)
    p = os.path.join(LAY, "asset-manifest-entries-r4.json")
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
