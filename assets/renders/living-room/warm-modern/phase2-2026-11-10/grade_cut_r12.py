#!/usr/bin/env python3
"""
grade_cut_r12.py: the v3c display files and layers of the warm-modern tool, phase 2, after the reserve passes R1 and R2 (render-agent,
2026-11-11). Brief: briefs/render-wm-tool-phase2-reserve-2026-11-11.md. Code only, 0 tokens. NEW FILES ONLY: steps 1-3 files are read,
never written.

The same method as grade_cut.py (one v3c grade, stack.Grade; every layer cut from the graded composites, never graded on its own; the
cushion sets kept byte for byte where the stack under them did not change), on the stack of every default that now passes:
  steps 1-3 (work/layers):     rug, vase, floor-lamp, framed-art, accent-sconces, candle-holders
  reserve (work-reserve/):     curtains (R1), magazine-holder Orange (R1), bowl (R2, position PROVISIONAL pending WM-T2)
  still pending:               planter, basket (R1 failed), pendant (R2 failed)
A layer whose recomputed bytes equal its steps 1-3 file keeps that file (the manifest points to it); one that differs is written as
<name>-r12.png. New products get their own new folders.

Writes: layers/<slot>/... (new files), layers/manifest-r12.json, graded/default-scene-r12-set-<X>-graded-v3c.png,
graded/reserve-r12-crops-set-B.png (unused by the site; the sheet's source), jobs-reserve.json (grade record).
  python3 grade_cut_r12.py        then   python3 layers/verify_layers_r12.py
"""
import glob
import hashlib
import json
import os

import cv2
import numpy as np
from PIL import Image

import grade_cut as GC
import phase2_wm as W
import reserve_r12 as R
import stack
from phase2_wm import P1

HERE = W.HERE
LAY = os.path.join(HERE, "layers")
GRD = os.path.join(HERE, "graded")
REPO = W.REPO
FID = json.load(open(os.path.join(R.WR, "fidelity-r12.json")))["products"]

STEP13 = ["framed-art", "accent-sconces", "vase", "rug", "floor-lamp", "candle-holders"]
RESERVE = ["curtains", "magazine-holder", "bowl"]
ACCEPTED = STEP13 + RESERVE
CARDS = dict(GC.CARDS)
CARDS.update({
    "curtains": ("curtains-aliexpress-beige-linen-sheer-curtains-554205", {"style": "hooks-top", "size": "150x270"}, "12000029601125492"),
    "magazine-holder": ("magazine-holder-cj-gunmetal-leather-strap", {"color": "orange", "size": "small"}, "CJYD201631004DW"),
    "bowl": ("bowl-cj-matte-black-bowl-20", {"other": "12style"}, "CJJT131449012LO"),
})
PENDING = {
    "planter": "R1 (reserve) failed: the pot drawn ~1.37x the card (rim ~57.5 cm, card 42) and its lower right hidden by the rendered basket, "
               "which is itself off the plan; it cannot be cut whole (work-reserve/fidelity-r12.json)",
    "basket": "R1 (reserve) failed on placement: in front of the pot this time, but its floor centre ~30 cm off the plan's (-1.62, 0.78) "
              "(pushed back toward the wall) and ~40 cm wide (card 35)",
    "pendant": "R2 (reserve) failed on placement: the card's 50 cm tiered shade at the plan's X / Y, but hung ~10 cm low (shade bottom "
               "~1.80 against the owner's 1.90, V7Q7 b); not moved in code (the R2 render can be cut at 0 tokens if 1.80 is accepted)",
}
NOTES = {
    "bowl": "POSITION PROVISIONAL, pending WM-T2 (the coordinator, 2026-11-11, from docs/proposals/wm-phase2-f3-decisions-2026-11-11.md: "
            "(0.72, 1.94) sits 0.009 from the throw, no place in the slot envelope solves it; the designer proposes moving the warm-modern "
            "table group left under the pendant). Measured in this layer: 0.0083-0.0086 of the frame from sets A / B / C",
    "magazine-holder": "the ORANGE SKU (cognac straps) as the selection and the designer's decision 4 (2026-11-11) describe it, not the "
                       "card's default black; QA: the strap colour",
    "curtains": "the designer's condition (2026-11-11, 2.5): the armchair's overlap of the stack, measured on this layer: see "
                "fidelity.curtains_vs_armchair; the stack's inner edge is the reference for the variants (+-0.003 u)",
}
LIGHTS = GC.LIGHTS
SRC = {k: (os.path.join(W.WORK, "layers"), os.path.join(W.WORK, "shadows")) for k in STEP13}
SRC.update({k: (os.path.join(R.WR, "layers"), os.path.join(R.WR, "shadows")) for k in RESERVE})
_STACK_PRODUCT = stack.product                       # the original (steps 1-3 folders; phase 1's cushion sets)


def f8(p, mode=None):
    return stack.f8(p, mode)


def product(k, s=None):
    """stack.product with each product read from its own pass's folder"""
    if k == "cushions":
        return _STACK_PRODUCT(k, s)
    ld, sd = SRC[k]
    L = f8(os.path.join(ld, f"{k}.png"))
    a = L[..., 3]
    fp = os.path.join(ld, f"{k}-free-alpha.png")
    if k in stack.BEHIND and os.path.exists(fp):
        a = f8(fp, "L")
    Sh = f8(os.path.join(sd, f"{k}.png"), "L")
    if k == "bowl":
        # the bowl stands 0.008 of the frame from the throw (WM-T2): the far edge of its faint shadow reached the throw's soft edge and the
        # throw's own shadow on the table (34 / 176 / 71 px with sets A / B / C). It is held off the union of the three sets' regions
        # (+1 px), so the one bowl layer stays valid with every set (a layer above the cushions must not touch any set's region)
        Sh = np.where(cushion_union(), 1.0, Sh).astype(np.float32)
        HELD["bowl_shadow_px_held_off_the_sets"] = int(((Sh == 1.0) & (f8(os.path.join(sd, f"{k}.png"), "L") < 1.0)).sum())
    return L[..., :3], a, Sh


HELD = {}
_UNION = []


def cushion_union():
    if not _UNION:
        u = None
        for s_ in "ABC":
            _, ca, cs = _STACK_PRODUCT("cushions", s_)
            r_ = (ca > 0) | (cs < 1)
            u = r_ if u is None else (u | r_)
        _UNION.append(cv2.dilate(u.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool))
    return _UNION[0]


def compose(items, P, cushion_set="B"):
    stack.product = product
    try:
        return stack.compose(items, P, cushion_set=cushion_set, keep_steps=True)
    finally:
        stack.product = _STACK_PRODUCT


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
        U, steps = compose(items, P, cushion_set=s)
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
        Image.fromarray(finals[s]).save(os.path.join(GRD, f"default-scene-r12-set-{s}-graded-v3c.png"), compress_level=6)
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    # write the layers: reuse a steps 1-3 file when the bytes are the same, else a new -r12 file
    files, reused = {}, {}
    for (k, s), r in results.items():
        if k == "cushions":
            d = os.path.join(LAY, "cushions")
            stem = f"set-{s}"
        else:
            d = os.path.join(LAY, k)
            stem = CARDS[k][0]
        os.makedirs(d, exist_ok=True)
        lp_old, sp_old = os.path.join(d, f"{stem}.png"), os.path.join(d, f"{stem}-shadow.png")
        if os.path.exists(lp_old) and os.path.exists(sp_old):
            same = (np.array_equal(np.asarray(Image.open(lp_old)), r["L"]) and
                    np.array_equal(np.asarray(Image.open(sp_old).convert("RGB")), r["S"]))
            if same:
                files[(k, s)] = (lp_old, sp_old)
                reused[f"{k}{'-' + s if s else ''}"] = "steps 1-3 file, same bytes"
                continue
            lp, sp = os.path.join(d, f"{stem}-r12.png"), os.path.join(d, f"{stem}-r12-shadow.png")
            reused[f"{k}{'-' + s if s else ''}"] = "recomputed bytes differ: new -r12 file"
        else:
            lp, sp = lp_old, sp_old
            reused[f"{k}{'-' + s if s else ''}"] = "new product: new file"
        assert not os.path.exists(lp) and not os.path.exists(sp), f"would overwrite {lp}"
        Image.fromarray(r["L"], "RGBA").save(lp, compress_level=9)
        Image.fromarray(r["S"], "RGB").save(sp, compress_level=9)
        files[(k, s)] = (lp, sp)
    man = write_manifest(G, files, results, regions, cush_changed, overlap, reused)
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
        if k in PENDING:
            layers.append(dict(id=k, slot=k, z=stack.Z[k], status="pending: both paid passes failed fidelity (steps 2-3 and the reserve); "
                               "no third pass (the reserve brief)", reason=PENDING[k]))
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
                   region=GC.region_info(reg), build=st, pass_=("reserve " + ("R1" if k in ("curtains", "magazine-holder") else "R2")) if k in RESERVE
                   else "steps 1-3", file_origin=reused[k],
                   behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in LIGHTS)
        if k in stack.BEHIND:
            rec["note"] = ("stands behind the fixed furniture, which the base already holds: its alpha leaves the furniture whole and its soft edge is "
                           "solved against it (composed physically in stack.py: (behind x shadow + product) x (1 - fa) + furniture x fa)")
        if k in NOTES:
            rec["status_note"] = NOTES[k]
        if k == "bowl":
            rec["position_status"] = "provisional, pending WM-T2"
        if k in FID:
            rec["fidelity"] = {kk: vv for kk, vv in FID[k].items() if kk not in ("card", "option", "sku")}
            if k == "curtains":
                rec["fidelity"]["curtains_vs_armchair"] = FID["curtains_vs_armchair"]
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       products="as layers-v3c/manifest.json sets." + s, region=GC.region_info(regions[("cushions", s)]),
                       recut_on_new_stack_px=int(cush_changed[s].sum()), build=results[("cushions", s)]["stats"], file_origin=reused[f"cushions-{s}"],
                       approved_source=rel(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png")))
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-r12", version="r12 (supersedes manifest.json of steps 1-3 for the tool; that file is kept)",
        room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-11", author="render-agent",
        brief="briefs/render-wm-tool-phase2-reserve-2026-11-11.md (continuing briefs/render-wm-tool-phase2-2026-11-10.md)",
        approval="PH2-WM (owner, 2026-11-10); the reserve 1,300 by the manager; base and cushions: AP3-WM + QA qa/reports/2026-11-10-wm-tool-layers-v3c.md",
        status="phase 2 defaults after the reserve, PARTIAL: 9 of 12 defaults layered (6 from steps 1-3, 3 from the reserve), 3 pending "
               "(planter, basket, pendant: both paid passes failed fidelity). The bowl's position is provisional (WM-T2). Not QA'd; for "
               "qa-agent and master-designer. HD_PUBLIC=0 only",
        grade="v3c, ONE display grade (stack.Grade = phase 1 grade_v3c; base.png reproduced byte for byte). Every layer is cut from the graded "
              "composites; no layer is graded on its own; the site applies no further grade",
        grade_params=G.record(),
        size=json.load(open(os.path.join(P1, "layers-v3c/manifest.json")))["size"],
        color="8-bit sRGB, no ICC profile. Blending on the sRGB-encoded values (CSS mix-blend-mode, canvas 2D, the engine's GL path)",
        compose=dict(order=[l_["id"] for l_ in layers if "status" not in l_],
                     formula="for each product in order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, straight alpha; "
                             "the cushions: one set at a time, its shadow and its layer together",
                     swap_region="per product: alpha > 0 or any shadow channel < 255; a product (or a set) changes nothing outside its region"),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        pending=PENDING,
        light_layers="the floor lamp and the wall lamps are rendered OFF as products; their light layers are made in code later (plan section 2, step 8)",
        files=dict(build="grade_cut_r12.py (with stack.py, reserve_r12.py, extract.py, phase2_wm.py)", verify="verify_layers_r12.py",
                   verification="verify-layers-r12.json", fidelity="../work-reserve/fidelity-r12.json",
                   asset_manifest_entries="asset-manifest-entries-r12.json", verify_usage="python3 verify_layers_r12.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=dict(this_build=0, reserve_passes=1300),
        held=HELD,
    )
    json.dump(man, open(os.path.join(LAY, "manifest-r12.json"), "w"), indent=1, ensure_ascii=False)
    return man


if __name__ == "__main__":
    main()
