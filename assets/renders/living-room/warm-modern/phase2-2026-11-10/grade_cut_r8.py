#!/usr/bin/env python3
"""
grade_cut_r8.py: the v3c layers of the warm-modern tool, phase 2, after R8 (render-agent, 2026-11-12; 0 tokens, code only).
Source: docs/proposals/wm-r7-table-decisions-2026-11-12.md section 3 (3.3.1 the marks between the travertine feet, 3.2.4 the specks in
curtain 3). NEW FILES ONLY: the R7 files (and every earlier one) are read, never written; a layer or shadow whose recomputed bytes equal
an existing file keeps that file (each of the two on its own), anything else is written as <stem>-r8.png.

The same method as grade_cut_r7.py, unchanged (ONE v3c grade, stack.Grade; every layer cut from the graded composites, never graded on
its own; the cushion sets kept byte for byte where the stack under them did not change; the frozen shadow recipe), on the R7 sources with
two R8 sources (fix_r8.py -> work-r8/):
  candle-holders (default)   the shadow without the marks between the feet (the layer: the R7 source, byte copy)
  curtains-v3 (variant)      the specks neutralised (a*, b* only; alpha, free alpha and shadow: the R7 sources, byte copies)
Every other slot and variant reads its R7 source; the run checks that each of them reproduces its R7 file byte for byte.

Writes: layers/<slot>/...-r8.png (only where the bytes are new), layers/manifest-r8.json, layers/asset-manifest-entries-r8.json,
graded/default-scene-r8-set-<X>-graded-v3c.png, graded/variant-r8-<name>-set-B-graded-v3c.png (each variant's truth on the R8 default).
  python3 fix_r8.py all ; python3 grade_cut_r8.py ; python3 layers/verify_layers_r8.py ; python3 make_crops_r8.py
"""
import copy
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade_cut_r7 as G7  # noqa: E402

F7, GC, G12, stack, P1 = G7.F7, G7.GC, G7.G12, G7.stack, G7.P1
LAY, GRD, REPO = G7.LAY, G7.GRD, G7.REPO
D = os.path.join
WR8 = D(HERE, "work-r8")
F7.SRC7["candle-holders"] = (D(WR8, "layers"), D(WR8, "shadows"))
F7.VSRC7["curtains-v3"] = (D(WR8, "layers"), D(WR8, "shadows"))
FIX8 = {"candle-holders": "shadow", "curtains-v3": "layer"}       # what R8 is allowed to change
FIXREC8 = json.load(open(D(WR8, "fix-r8.json")))
MAN7 = json.load(open(D(LAY, "manifest-r7.json")))
ACCEPTED, VARIANTS, CARDS, VCARDS = G7.ACCEPTED, G7.VARIANTS, G7.CARDS, G7.VCARDS
sha = G7.sha


def write_or_reuse(d, stem, arr, mode):
    os.makedirs(d, exist_ok=True)
    found = G7.same_file(d, arr, mode, stem)
    if found and "-r8" in os.path.basename(found):
        return found, "new -r8 file"
    if found:
        return found, "existing file, same bytes (" + os.path.basename(found) + ")"
    p = D(d, f"{stem}-r8{'-shadow' if mode == 'RGB' else ''}.png")
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    Image.fromarray(arr, mode).save(p, compress_level=9)
    return p, "new -r8 file"


def _new(p):
    assert not os.path.exists(p) or os.environ.get("REDO"), p
    return p


def main():
    F7.use_r7_sources()
    G = stack.Grade()
    P = stack.base_parts()
    base8 = GC.u8(D(P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    assert sha(D(LAY, "base.png")) == sha(D(P1, "layers-v3c/base.png"))
    results, regions, finals, cush_changed, pre = {}, {}, {}, {}, {}
    for s in "BAC":
        U, steps = F7.compose7(cushion_set=s)
        Aun = np.zeros(P["fa"].shape, np.float32)
        Cprev = base8.copy()
        appr = GC.u8(D(P1, f"composite-set-{s}-v3-graded-v3c.png"))
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
                LA = np.asarray(Image.open(D(P1, f"layers-v3c/cushions-set-{s}.png"))).copy()
                SA = np.asarray(Image.open(D(P1, f"layers-v3c/cushions-set-{s}-shadow.png")).convert("RGB")).copy()
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
        Image.fromarray(finals[s]).save(_new(D(GRD, f"default-scene-r8-set-{s}-graded-v3c.png")), compress_level=6)
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
        Image.fromarray(T.astype(np.uint8)).save(_new(D(GRD, f"variant-r8-{nm}-set-B-graded-v3c.png")), compress_level=6)
        print("variant", nm, flush=True)
    files, origin = {}, {}
    for (k, s), r in results.items():
        d = D(LAY, "cushions" if k == "cushions" else k)
        stem = f"set-{s}" if k == "cushions" else CARDS[k][0]
        lp, lo = write_or_reuse(d, stem, r["L"], "RGBA")
        sp, so = write_or_reuse(d, stem, r["S"], "RGB")
        files[(k, s)] = (lp, sp)
        origin[f"{k}{'-' + s if s else ''}"] = dict(layer=lo, shadow=so)
    vfiles = {}
    for nm, r in vres.items():
        d = D(LAY, r["slot"])
        lp, lo = write_or_reuse(d, VCARDS[nm][0], r["L"], "RGBA")
        sp, so = write_or_reuse(d, VCARDS[nm][0], r["S"], "RGB")
        vfiles[nm] = (lp, sp)
        origin[nm] = dict(layer=lo, shadow=so)
    # every file must be its R7 file, except what R8 fixes
    r7file = {l_["id"]: l_["file"] for l_ in MAN7["layers"] if "file" in l_}
    r7var = {v["id"]: (v["file"], v["shadow"]) for vs in MAN7["variants"].values() for v in vs}
    unexpected, same_as_r7 = [], {}
    for (k, s), (lp, sp) in files.items():
        if k == "cushions":
            r7l, r7s = MAN7["slot_cushions"]["sets"][s]["layer"], MAN7["slot_cushions"]["sets"][s]["shadow"]
            key = f"cushions-{s}"
        else:
            r7l, r7s = r7file[k], r7file[k + "-shadow"]
            key = k
        same_as_r7[key] = dict(layer=os.path.relpath(lp, LAY) == r7l, shadow=os.path.relpath(sp, LAY) == r7s)
    for nm, (lp, sp) in vfiles.items():
        same_as_r7[nm] = dict(layer=os.path.relpath(lp, LAY) == r7var[nm][0], shadow=os.path.relpath(sp, LAY) == r7var[nm][1])
    for key, v in same_as_r7.items():
        for part in ("layer", "shadow"):
            if not v[part] and FIX8.get(key) != part:
                unexpected.append(f"{key} {part}")
    gaps = G7.layer_gaps(vfiles, files)
    man = write_manifest(G, files, results, regions, origin, vres, vreg, vfiles, unexpected, gaps, same_as_r7)
    write_asset_entries(man, origin)
    print(json.dumps(dict(origin=origin, unexpected_changes=unexpected, gaps=gaps), indent=1, default=str))
    if unexpected:
        raise SystemExit(f"unexpected changes: {unexpected}")
    return man


def write_manifest(G, files, results, regions, origin, vres, vreg, vfiles, unexpected, gaps, same_as_r7):
    man = copy.deepcopy(MAN7)
    fx = FIXREC8
    for l_ in man["layers"]:
        k = l_.get("slot")
        if k is None or k == "cushions" or "file" not in l_:
            continue
        lp, sp = files[(k, None)]
        if l_["id"].endswith("-shadow"):
            l_["file"] = os.path.relpath(sp, LAY)
            continue
        l_["file"] = os.path.relpath(lp, LAY)
        l_["region"] = GC.region_info(regions[(k, "B")])
        l_["build"] = results[(k, None)]["stats"]
        l_["file_origin"] = origin[k]
        if k == "candle-holders":
            h = fx["holders"]
            l_["previous_shadow_file"] = next(x["file"] for x in MAN7["layers"] if x["id"] == "candle-holders-shadow")
            l_["pass_"] = l_["pass_"] + " + fix R8 (code: the marks between the feet out of the shadow, designer 3.3.1)"
            l_["r8"] = dict(record="../work-r8/fix-r8.json#holders", what="the shadow only: the frozen recipe's field kept on each foot, "
                            "whatever lay between the feet taken out (one soft ellipse under each foot)", px_changed_ungraded=h["px_changed"],
                            darkening_removed_255_max=h["darkening_removed_255"]["max"], between_feet_after=h["between_feet_after"],
                            nothing_added=h["nothing_added"], layer_rgba="unchanged (the R7 file)")
            l_["status_note"] = l_["status_note"] + (" R8: the three short dark marks between A and B (they came from R6 inside the shadow file) "
                                                     "taken out; the WM-T3 move, if the owner approves it, starts from these files")
    sets = man["slot_cushions"]["sets"]
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s]["layer"], sets[s]["shadow"] = os.path.relpath(lp, LAY), os.path.relpath(sp, LAY)
        sets[s]["file_origin"] = origin[f"cushions-{s}"]
    for k, vs in man["variants"].items():
        for v in vs:
            nm = v["id"]
            lp, sp = vfiles[nm]
            v["file"], v["shadow"] = os.path.relpath(lp, LAY), os.path.relpath(sp, LAY)
            v["file_origin"] = origin[nm]
            v["region"] = GC.region_info(vreg[nm])
            v["build"] = vres[nm]["stats"]
            v["truth"] = f"../graded/variant-r8-{nm}-set-B-graded-v3c.png"
            if nm == "curtains-v3":
                c = fx["curtain3"]
                v["previous_file"] = next(x["file"] for x in MAN7["variants"]["curtains"] if x["id"] == "curtains-v3")
                v["pass_"] = v["pass_"] + " + fix R8 (code: the green specks neutralised, designer 3.2.4)"
                v["r8"] = dict(record="../work-r8/fix-r8.json#curtain3", rules=c["rules"], before=c["before"], fixed_px=c["fixed_px"],
                               after_ungraded=c["after_ungraded"], changed_outside_specks=c["changed_outside_specks"],
                               dL_max_on_specks=c["dL_max_on_specks"], dab_on_specks=c["dab_on_specks"],
                               body_median_lab=dict(before=c["body_median_lab_before"], after=c["body_median_lab_after"]),
                               alpha="unchanged (layer alpha, free alpha and shadow: the R7 sources)")
    tg = dict(man["table_group"])
    tg["wm_t3_clay"] = dict(record="../step0/wm-t3/table-group-wm-t3.json", overlay="../step0/wm-t3/table-group-wm-t3-overlay.jpg",
                            note="WM-T3 (designer 2026-11-12 section 1.4) checked in clay only; NO layer moved: the owner answers WM-T3 first")
    tg["final_layer_gaps_frame"] = gaps
    man.update(
        id="wm-living-room-m0-tool-layers-phase2-r8", version="r8 (supersedes manifest-r7.json for the tool; the earlier manifests are kept)",
        date="2026-11-12", author="render-agent",
        brief="the coordinator's R8 task (2026-11-12, 0 tokens): docs/proposals/wm-r7-table-decisions-2026-11-12.md section 3 (3.3.1, 3.2.4); "
              "the WM-T3 clay of section 1.6 (no layer moved)",
        approval=MAN7["approval"] + "; R8: code fixes in the designer's authority (section 3), 0 tokens",
        status=MAN7["status"].replace("after R7", "after R8 (R7 + two code fixes: the marks between the travertine feet, the specks in curtain 3)"),
        grade_params=G.record(),
        table_group=tg,
        changed_in_r8=dict(allowed=FIX8, unexpected_other_changes=unexpected, files={k: v for k, v in origin.items() if "new" in v["layer"] + v["shadow"]},
                           same_as_r7=same_as_r7),
        files=dict(MAN7["files"], build="grade_cut_r8.py (fix_r8.py; on grade_cut_r7.py's method and the R7 sources)",
                   fixes="../fix_r8.py -> ../work-r8/ (../work-r8/fix-r8.json)", verify="verify_layers_r8.py", verification="verify-layers-r8.json",
                   crops="../crops-r8/ (../make_crops_r8.py)", asset_manifest_entries="asset-manifest-entries-r8.json",
                   verify_usage="python3 verify_layers_r8.py  (numpy + Pillow + OpenCV; exit 0 = pass)", previous_manifest="manifest-r7.json"),
        tokens=dict(MAN7["tokens"], fix_r8=0),
    )
    p = _new(D(LAY, "manifest-r8.json"))
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False, default=float)
    return man


def write_asset_entries(man, origin):
    status = ("warm-modern tool, phase 2 R8 (code, 0 tokens, 2026-11-12): v3c layers cut from the graded composites; verified by "
              "layers/verify_layers_r8.py; awaiting qa-agent and master-designer; HD_PUBLIC=0")
    base = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
    out = []

    def add(eid, path, kind, model, extra=None):
        out.append(dict(id=eid, path=path, kind=kind, model=model, status=status, style="warm-modern", room="living-room", created="2026-11-12",
                        recipe=base + "grade_cut_r8.py (fix_r8.py)", **(extra or {})))
    for l_ in man["layers"]:
        k = l_.get("slot")
        if "file" not in l_ or k in (None, "cushions"):
            continue
        is_sh = l_["id"].endswith("-shadow")
        if not origin[k]["shadow" if is_sh else "layer"].startswith("new"):
            continue
        prod = next(x for x in man["layers"] if x["id"] == k)
        add(f"wm-tool-ph2-r8-{l_['id']}", base + "layers/" + l_["file"],
            f"tool {'shadow layer, RGB multiply (white = none)' if is_sh else 'product layer, RGBA straight alpha'}, {k}, default, v3c",
            "code (R8, 0 tokens) on earlier seedream-5-pro renders", None if is_sh else dict(product_id=prod["product"]["card_id"], sku=prod["product"]["sku"]))
    for k, vs in man["variants"].items():
        for v in vs:
            for is_sh in (False, True):
                if not origin[v["id"]]["shadow" if is_sh else "layer"].startswith("new"):
                    continue
                add(f"wm-tool-ph2-r8-{v['id']}{'-shadow' if is_sh else ''}", base + "layers/" + (v["shadow"] if is_sh else v["file"]),
                    f"tool {'shadow layer, RGB multiply' if is_sh else 'product layer, RGBA straight alpha'}, {k}, variant {v['variant']}, v3c",
                    "code (R8, 0 tokens) on the 7' seedream-5-pro render", None if is_sh else dict(product_id=v["product"]["card_id"], sku=v["product"]["sku"]))
    for s in "BAC":
        add(f"wm-tool-ph2-r8-default-scene-{s}", base + f"graded/default-scene-r8-set-{s}-graded-v3c.png", f"graded default scene (12 defaults, R8), set {s}, v3c", "composite")
    for k, vs in man["variants"].items():
        for v in vs:
            add(f"wm-tool-ph2-r8-truth-{v['id']}", base + f"graded/variant-r8-{v['id']}-set-B-graded-v3c.png", f"graded truth of variant {v['id']} on the R8 default, set B, v3c", "composite")
    add("wm-tool-ph2-r8-layers-manifest", base + "layers/manifest-r8.json", "tool layers manifest r8 (12 defaults + variants)", "-")
    add("wm-tool-ph2-r8-crops", base + "crops-r8/", "before / after crops of the R8 fixes at 100 % and x4", "-")
    add("wm-tool-ph2-wm-t3-clay", base + "step0/wm-t3/table-group-wm-t3.json", "clay check of the WM-T3 table-group proposal (no layer moved)", "code (0 tokens)")
    add("wm-tool-ph2-wm-t3-clay-overlay", base + "step0/wm-t3/table-group-wm-t3-overlay.jpg", "overlay of the WM-T3 clay check on the R7 default scene", "code (0 tokens)")
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-12; R8: new files only, the entries in a separate JSON for "
                    "the manager); layers and shadows whose bytes did not change keep their earlier entries", assets=out)
    json.dump(rec, open(_new(D(LAY, "asset-manifest-entries-r8.json")), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
