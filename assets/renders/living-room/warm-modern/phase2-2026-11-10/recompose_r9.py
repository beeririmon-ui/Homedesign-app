#!/usr/bin/env python3
"""
recompose_r9.py: the R9 truths and manifest of the warm-modern tool, phase 2 (render-agent, 2026-11-12; 0 tokens, code only). NO GRADE in
R9: fix_r9.py changed two graded layers after the one v3c grade (pendant 2's alpha, curtain 3's soft edge). A variant's truth is the R8
truth with every pixel the layer change touches recomposed over the graded scene under that layer, as the tool composes it:
    T = round(C_under x S / 255 x (1 - a) + L x a)
C_under is grade_cut_r8.py's own set-B composite before the slot's step, rebuilt here in memory (the R8 pipeline re-run; the run must
reproduce R8's default scene and both R8 truths byte for byte, and the formula with the R8 layer must give the R8 truth exactly on every
pixel it recomposes). NEW FILES ONLY.

  python3.12 -I recompose_r9.py            graded/variant-r9-{pendant-v2,curtains-v3}-set-B-graded-v3c.png, layers/manifest-r9.json
  python3.12 -I recompose_r9.py entries    layers/asset-manifest-entries-r9.json (after verify_layers_r9.py and make_crops_r9.py):
                                           a sha256 for every new file, and for every file of the tool's set as of R9 (QA R8 F8)
"""
import copy
import glob
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join
LAY, GRD, WR9 = D(HERE, "layers"), D(HERE, "graded"), D(HERE, "work-r9")
REPO = os.path.abspath(D(HERE, *[".."] * 5))
BASE = "assets/renders/living-room/warm-modern/phase2-2026-11-10/"
MAN8 = json.load(open(D(LAY, "manifest-r8.json")))
FIX9 = json.load(open(D(WR9, "fix-r9.json")))
V8 = {v["id"]: v for vs in MAN8["variants"].values() for v in vs}
CHANGED = {"pendant-v2": ("pendant", FIX9["pendant2"]["files"]["layer"]), "curtains-v3": ("curtains", FIX9["curtain3"]["files"]["layer"])}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _new(p):
    assert not os.path.exists(p) or os.environ.get("REDO"), f"would overwrite {p}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def rhu(x):
    return np.floor(x + 0.5)


def scene_under():
    """grade_cut_r8.main()'s set-B loop, in memory: the graded composite before each step; checks that R8 is reproduced"""
    sys.path.insert(0, HERE)
    import grade_cut_r8 as G8
    F7, GC, stack = G8.F7, G8.GC, G8.stack
    F7.use_r7_sources()
    G = stack.Grade()
    P = stack.base_parts()
    base8 = GC.u8(D(G8.P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    _, steps = F7.compose7(cushion_set="B")
    Aun = np.zeros(P["fa"].shape, np.float32)
    Cprev = base8.copy()
    appr = GC.u8(D(G8.P1, "composite-set-B-v3-graded-v3c.png"))
    pre = {}
    import cv2
    for st in steps:
        k, reg = st["k"], st["region"]
        pre[k] = (Cprev.copy(), Aun.copy())
        Aun = np.maximum(Aun, st["a_eff"] if k != "cushions" else st["a"])
        Cg = G(st["U"], Aun).astype(np.float64)
        C = Cprev.copy()
        if k == "cushions":
            delta = reg & (np.abs(Cprev - base8).max(2) > 0)
            delta = cv2.dilate(delta.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & reg
            C[reg] = appr[reg]
            C[delta] = Cg[delta]
        else:
            C[reg] = Cg[reg]
        Cprev = C
    final = Cprev.astype(np.uint8)
    checks = {"default-scene-r8-set-B": bool(np.array_equal(final, np.asarray(Image.open(D(GRD, "default-scene-r8-set-B-graded-v3c.png")).convert("RGB"))))}
    for nm, (k, _) in CHANGED.items():
        _, stv = F7.compose7(variants={k: nm})
        st = next(x for x in stv if x["k"] == k)
        Cp, A0 = pre[k]
        Cg = G(st["U"], np.maximum(A0, st["a_eff"])).astype(np.float64)
        C = Cp.copy()
        C[st["region"]] = Cg[st["region"]]
        T = final.astype(np.float64).copy()
        dreg = next(s for s in steps if s["k"] == k)["region"]
        T[dreg] = Cp[dreg]
        T[st["region"]] = C[st["region"]]
        checks[f"variant-r8-{nm}"] = bool(np.array_equal(T.astype(np.uint8), np.asarray(Image.open(D(GRD, f"variant-r8-{nm}-set-B-graded-v3c.png")).convert("RGB"))))
        above = np.zeros(dreg.shape, bool)
        i = [x["k"] for x in stv].index(k)
        for s_ in stv[i + 1:]:
            above |= (s_["a_eff"] > 0) if s_["k"] != "cushions" else (s_["a"] > 0)
            if s_.get("Sh") is not None:
                above |= s_["Sh"] < 1
        checks[f"{nm}: layers above its region (px)"] = int((above & st["region"]).sum())
    assert all(v is True or v == 0 for v in checks.values()), checks
    return {k: pre[k][0] for k, _ in CHANGED.values()}, checks, GC


def main():
    Cu, repro, GC = scene_under()
    truths, region = {}, {}
    for nm, (k, newrel) in CHANGED.items():
        v8 = V8[nm]
        L8 = np.asarray(Image.open(D(LAY, v8["file"]))).astype(np.float64)
        L9 = np.asarray(Image.open(D(REPO, newrel))).astype(np.float64)
        S = np.asarray(Image.open(D(LAY, v8["shadow"])).convert("RGB")).astype(np.float64)
        T8 = np.asarray(Image.open(D(GRD, f"variant-r8-{nm}-set-B-graded-v3c.png")).convert("RGB")).astype(np.float64)
        Cp = Cu[k].astype(np.float64)
        chg = (L8 != L9).any(2)

        def comp(L):
            a = L[..., 3:4] / 255.0
            return rhu(Cp * S / 255.0 * (1 - a) + L[..., :3] * a)
        exact = int((comp(L8)[chg] != T8[chg]).any(1).sum())
        assert exact == 0, f"{nm}: the formula with the R8 layer misses the R8 truth on {exact} px"
        T9 = T8.copy()
        T9[chg] = comp(L9)[chg]
        p = _new(D(GRD, f"variant-r9-{nm}-set-B-graded-v3c.png"))
        Image.fromarray(T9.astype(np.uint8)).save(p, compress_level=6)
        reg9 = (L9[..., 3] > 0) | (S < 255).any(2)
        reg8 = (L8[..., 3] > 0) | (S < 255).any(2)
        d = np.abs(T9 - T8).max(2)
        truths[nm] = dict(file=os.path.relpath(p, LAY), sha256=sha(p), layer_px_changed=int(chg.sum()), truth_px_changed=int((d > 0).sum()),
                          truth_max_level_change=int(d.max()), truth_changed_outside_the_layers_regions=int(((d > 0) & ~(reg8 | reg9)).sum()),
                          r8_formula_check="the formula with the R8 layer gives the R8 truth exactly on all %d recomposed px" % int(chg.sum()))
        region[nm] = (reg9, reg8)
        print(nm, json.dumps(truths[nm]))
    write_manifest(truths, region, repro, GC)


def write_manifest(truths, region, repro, GC):
    man = copy.deepcopy(MAN8)
    f9 = FIX9
    p2, c3, rc = f9["pendant2"], f9["curtain3"], f9["r8_record_corrections"]
    for k, vs in man["variants"].items():
        for v in vs:
            nm = v["id"]
            if nm not in CHANGED:
                continue
            v["previous_file"] = V8[nm]["file"]
            v["file"] = os.path.relpath(D(REPO, CHANGED[nm][1]), LAY)
            v["truth"] = "../graded/" + os.path.basename(truths[nm]["file"])
            v["file_origin"] = dict(layer="new -r9 file (fix_r9.py on the graded R8 layer)", shadow="existing file, same bytes (" + os.path.basename(v["shadow"]) + ")")
            v["region"] = GC.region_info(region[nm][0])
            L9 = np.asarray(Image.open(D(LAY, v["file"])))[..., 3]
            v["build_r9"] = dict(alpha_px=int((L9 > 0).sum()), alpha_255_px=int((L9 == 255).sum()), soft_px=int(((L9 > 0) & (L9 < 255)).sum()),
                                 note="R9 changes the graded layer after the cut; 'build' is R8's cut record")
            if nm == "pendant-v2":
                v["pass_"] = v["pass_"] + " + fix R9 (code: P2-1, the outline and the ramp, alpha only)"
                v["r9"] = dict(record="../work-r9/fix-r9.json#pendant2", what=p2["what"], stop_rule=dict(applied=p2["stop_rule"]["applied"],
                               top_left_arc=p2["stop_rule"]["top_left_arc"]["decision"]),
                               ramp_10_90_px=dict(reference_default_pendant_flanks=p2["ramp"]["reference"]["flanks"], before=p2["ramp"]["before"],
                                                  after=p2["ramp"]["after"]),
                               geometry_after=p2["geometry_after"], width_change_px=p2["width_change_px"], alpha_and_colour=p2["alpha_and_colour"],
                               shadow=p2["shadow"], designer_eye="docs/proposals/wm-pendant2-eye-2026-11-12.md: 'partial' can go; before 'approved for "
                                                                  "site': P2-1 (this fix) and QA's (a)-(g)")
            else:
                v["pass_"] = v["pass_"] + " + fix R9 (code: the 11 soft-edge pixels the literal speck rule flagged, QA R8 F1)"
                v["fidelity_status"] = ("designer's eye 2026-11-12 (docs/proposals/wm-r8-eye-2026-11-12.md): L* 73.0 is faithful to the Linen SKU; lock "
                                        "L* 71.5-74.5, h 81-87, C* 10.5-12.5 (C* 12.52 on the top edge: QA R8 F3, the designer's)")
                v["r9"] = dict(record="../work-r9/fix-r9.json#curtain3", what=c3["what"], before=c3["before"], after=c3["after"],
                               dL_max_abs=c3["dL_max_abs"], px_changed=c3["px_changed"], px_changed_outside_flagged=c3["px_changed_outside_flagged"],
                               alpha=c3["alpha"], shadow=c3["shadow"], wide_rule_soft_edge_note=c3["wide_rule_soft_edge_note"])
    man.update(
        id="wm-living-room-m0-tool-layers-phase2-r9", version="r9 (supersedes manifest-r8.json for the tool; the earlier manifests are kept)",
        date="2026-11-12", author="render-agent",
        brief="the coordinator's R9 task (2026-11-12, 0 tokens): P2-1 (docs/proposals/wm-pendant2-eye-2026-11-12.md section 4) on pendant 2; QA R8 "
              "F1 (curtain 3's soft edge), F2 (the records) and F8 (sha256); WM-T3 waits for the owner: nothing moved",
        approval=MAN8["approval"] + "; R9: code fixes, 0 tokens: P2-1 (the designer) and QA R8 F1 / F2 / F8 (the coordinator)",
        status=MAN8["status"].replace("after R8 (R7 + code fixes: the marks between the travertine feet; the curtains' break and stone contact; "
                                      "curtain 3's specks, L* (pending the designer's eye) and corner fringe)",
                                      "after R9 (R8, which QA passed, + code fixes on two graded layers: pendant 2's outline and ramp (P2-1, alpha "
                                      "only; its top-left arc kept under the stop rule) and curtain 3's soft-edge specks (QA R8 F1))"),
        truths=dict(default={s: f"../graded/default-scene-r8-set-{s}-graded-v3c.png" for s in "BAC"},
                    note="the default scenes do not change in R9 (neither default changed): the R8 files; variant truths: each variant's 'truth'"),
        changed_in_r9=dict(allowed={"pendant-v2": ["layer"], "curtains-v3": ["layer"]}, layers={k: dict(r8=V8[k]["file"], r9=os.path.relpath(D(REPO, CHANGED[k][1]), LAY))
                                                                                             for k in CHANGED},
                           truths=truths, scene_under_reproduced=repro, shadows="none changed", every_other_file="the R8 file (verify_layers_r9.py check 9)",
                           r8_record_corrections=dict(record="../work-r9/fix-r9.json#r8_record_corrections",
                                                      final_pass_mask=rc["final_pass_mask"]["file"].replace(BASE, "../"),
                                                      alpha_unchanged=rc["alpha_unchanged"]["correct"])),
        files=dict(MAN8["files"], build="no grade in R9: ../fix_r9.py (the two graded layers) -> ../recompose_r9.py (the two truths, this manifest)",
                   fixes="../fix_r9.py -> ../work-r9/ (../work-r9/fix-r9.json)", verify="verify_layers_r9.py", verification="verify-layers-r9.json",
                   crops="../crops-r9/ (../make_crops_r9.py)", asset_manifest_entries="asset-manifest-entries-r9.json",
                   verify_usage="python3.12 -I verify_layers_r9.py  (numpy + Pillow + OpenCV; exit 0 = pass)", previous_manifest="manifest-r8.json"),
        tokens=dict(MAN8["tokens"], fix_r9=0),
    )
    p = _new(D(LAY, "manifest-r9.json"))
    json.dump(man, open(p, "w"), indent=1, ensure_ascii=False, default=float)
    print("manifest", p)


def entries():
    man = json.load(open(D(LAY, "manifest-r9.json")))
    status = ("warm-modern tool, phase 2 R9 (code, 0 tokens, 2026-11-12): two graded layers fixed after the one v3c grade (no re-grade); "
              "verified by layers/verify_layers_r9.py; awaiting qa-agent and master-designer; HD_PUBLIC=0")
    out = []

    def add(eid, rel_, kind, model, extra=None):
        p = D(HERE, rel_)
        out.append(dict(id=eid, path=BASE + rel_, kind=kind, model=model, status=status, style="warm-modern", room="living-room", created="2026-11-12",
                        recipe=BASE + "fix_r9.py, recompose_r9.py", sha256=sha(p), bytes=os.path.getsize(p), **(extra or {})))
    vv = {v["id"]: v for vs in man["variants"].values() for v in vs}
    for nm in CHANGED:
        v = vv[nm]
        add(f"wm-tool-ph2-r9-{nm}", "layers/" + v["file"], f"tool product layer, RGBA straight alpha, {v['slot']}, variant {v['variant']}, v3c",
            "code (R9, 0 tokens) on earlier seedream-5-pro renders", dict(product_id=v["product"]["card_id"], sku=v["product"]["sku"]))
        add(f"wm-tool-ph2-r9-truth-{nm}", "graded/" + os.path.basename(v["truth"]), f"truth of variant {nm} on the default, set B, v3c (recomposed, no grade)", "composite")
    add("wm-tool-ph2-r9-layers-manifest", "layers/manifest-r9.json", "tool layers manifest r9 (12 defaults + variants)", "-")
    add("wm-tool-ph2-r9-verify", "layers/verify-layers-r9.json", "verification of the r9 layers (verify_layers_r9.py)", "-")
    add("wm-tool-ph2-r9-fix-record", "work-r9/fix-r9.json", "R9 fix record (P2-1, F1, F2)", "-")
    add("wm-tool-ph2-r9-pendant2-outline", "work-r9/pendant2-outline-r9.npy", "pendant 2's new 50 % outline (canvas px, numpy)", "code (0 tokens)")
    add("wm-tool-ph2-r9-curtain3-mask", "work-r9/curtain3-soft-edge-mask-r9.npy", "curtain 3: the 11 soft-edge pixels fixed in R9 (numpy bool)", "code (0 tokens)")
    add("wm-tool-ph2-r8-curtain3-final-pass-mask", "work-r8/curtain3-speck-mask-final-pass.npy",
        "curtain 3: R8's final speck pass (44 px), rebuilt in R9 (QA R8 F2; numpy bool)", "code (0 tokens)")
    for p in sorted(glob.glob(D(HERE, "crops-r9", "*.png"))):
        add("wm-tool-ph2-r9-crop-" + os.path.splitext(os.path.basename(p))[0], os.path.relpath(p, HERE), "R9 before / after crop", "-")
    scripts = {BASE + s: sha(D(HERE, s)) for s in ("fix_r9.py", "recompose_r9.py", "make_crops_r9.py", "layers/verify_layers_r9.py")}
    # the tool's whole set as of R9: every file the manifest names, with its sha256 (QA R8 F8)
    tool = {}
    for l_ in man["layers"]:
        if "file" in l_:
            tool[BASE + "layers/" + l_["file"]] = None
    for s in "BAC":
        tool[BASE + "layers/" + man["slot_cushions"]["sets"][s]["layer"]] = None
        tool[BASE + "layers/" + man["slot_cushions"]["sets"][s]["shadow"]] = None
        tool[BASE + "graded/" + os.path.basename(man["truths"]["default"][s])] = None
    for v in vv.values():
        for f in (v["file"], v["shadow"]):
            tool[BASE + "layers/" + f] = None
        tool[BASE + "graded/" + os.path.basename(v["truth"])] = None
    tool = {k: sha(D(REPO, k)) for k in sorted(tool)}
    rec = dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-12; R9: new files only, the entries in a separate JSON for "
                    "the manager). Every entry carries its sha256 (QA R8 F8); 'tool_set_sha256' lists every file of the tool as of R9 (layers, "
                    "shadows, cushion sets, default and variant truths) so any of them can be checked against a record; files whose bytes did "
                    "not change keep their earlier entries",
               assets=out, scripts_sha256=scripts, tool_set_sha256=tool)
    json.dump(rec, open(_new(D(LAY, "asset-manifest-entries-r9.json")), "w"), indent=1, ensure_ascii=False)
    print("entries", len(out), "tool files", len(tool))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "entries":
        entries()
    else:
        main()
