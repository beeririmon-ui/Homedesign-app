#!/usr/bin/env python3
"""
verify_layers_r6.py: re-runnable check of the warm-modern tool's phase-2 layers after R6 (render-agent, 2026-11-12; for qa-agent).
Reads manifest-r6.json and the files it names (numpy + Pillow; the helpers of verify_layers_r4.py); writes verify-layers-r6.json; exit 0 =
every check passes. Read-only on everything else.

  python3 verify_layers_r6.py

Checks
  1. base.png is the approved layers-v3c/base.png (same bytes).
  2. Recomposite of the default stack with set B / A / C against graded/default-scene-r6-set-X: p99.9 <= 2 and max <= 6 over the union of
     the regions, float and browser-like 8-bit pipelines.
  3. Swap-diff per default layer (set B) and between the cushion sets: 0 px changed outside the product's region (the sets' union).
  4. Regions are tight (no alpha or shadow pixel > 60 px beyond the product's alpha box).
  5. Files: size and mode; every product card (defaults and variants) exists with its id and SKU; phase 1 unchanged in git; the curtains'
     default is 180502 and curtains-v2 is 554205.
  6. Each VARIANT in for its slot's default (set B): against its truth (graded/variant-r6-<name>-set-B) within the gate; default <-> variant
     changes 0 px outside the union of the two regions.
  7. THE FULL CROSS: every combination of the slots' options (curtains 2 x framed-art 2 x accent-sconces 3 x vase 2 x pendant 2 = 48)
     x the cushion sets B / A / C x the float and 8-bit pipelines (288 composites), each against the truth built from each option's own
     truth, within the gate; and independence: each composite equals, byte for byte, the default composite with every slot's region taken
     from that slot's option composed alone (the slots' regions are disjoint: re-checked). The composites share their common prefixes
     (a depth-first walk of the stack), the same operations as composing each one from the base.
  8. ONE v3c grade on every layer changed in R6 (verify_layers_r4.py's method): the residual against its ungraded source, |median| <= 0.5
     and the toe within +-1.
"""
import importlib.util
import itertools
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("v4", os.path.join(HERE, "verify_layers_r4.py"))
V4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V4)
REPO, P2, P1 = V4.REPO, V4.P2, V4.P1
TOL_P999, TOL_MAX = V4.TOL_P999, V4.TOL_MAX
load, rhu, stats, compose, region_of, stack_layers, sha = V4.load, V4.rhu, V4.stats, V4.compose, V4.region_of, V4.stack_layers, V4.sha
MAN = os.path.join(HERE, "manifest-r6.json")
CACHE = {}


def arr(f):
    if f not in CACHE:
        CACHE[f] = np.asarray(Image.open(os.path.join(HERE, f)))
    return CACHE[f]


def step(o, lf, sf, pipe):
    L = arr(lf).astype(np.float32)
    S = arr(sf).astype(np.float32)
    if S.ndim == 2:
        S = S[..., None]
    a = L[..., 3:4] / 255.0
    if pipe == "float":
        return (o * S[..., :3] / 255.0) * (1 - a) + L[..., :3] * a
    m = np.floor(o * S[..., :3] / 255.0 + 0.5)
    pre = np.floor(L[..., :3] * a + 0.5)
    return np.floor(pre + m * (1 - a) + 0.5)


def swap_in(layers, repl):
    return [(k, *repl[k]) if k in repl else (k, lf, sf) for k, lf, sf in layers]


def dfs(base, layers, options, pipe, visit):
    """compose every combination: layers = [(slot, lf, sf)]; options = {slot: [(name, lf, sf), ...]} (the first = the default); visit(
    combo, out) for each leaf; the prefix up to each branching slot is shared"""
    def rec(i, o, combo):
        while i < len(layers) and layers[i][0] not in options:
            k, lf, sf = layers[i]
            o = step(o, lf, sf, pipe)
            i += 1
        if i == len(layers):
            visit(combo, o)
            return
        k = layers[i][0]
        for name, lf, sf in options[k]:
            rec(i + 1, step(o, lf, sf, pipe), dict(combo, **{k: name}))
    rec(0, base.astype(np.float32), {})


def grade_check(names):
    """verify_layers_r4.grade_check's method on (id -> (layer file, ungraded source path, z)); interiors under no later layer"""
    man = json.load(open(MAN))
    u = np.asarray(Image.open(os.path.join(P1, "shell-furniture-v3.png")).convert("RGB")).astype(np.float64) / 255
    g = np.asarray(Image.open(os.path.join(HERE, "base.png")).convert("RGB")).astype(np.float64) / 255
    stone = np.asarray(Image.open(os.path.join(P1, "masks/stone-wide.png")).convert("L")) > 127
    Lu, Lg = V4.lab_L(u)[~stone], V4.lab_L(g)[~stone]
    bins = np.arange(0, 100.25, 0.25)
    idx = np.clip(np.digitize(Lu, bins) - 1, 0, len(bins) - 2)
    dL = Lg - Lu
    cnt = np.bincount(idx, minlength=len(bins) - 1)
    curve = np.full(len(bins) - 1, np.nan)
    order = np.argsort(idx, kind="stable")
    for i, sv in enumerate(np.split(dL[order], np.cumsum(cnt)[:-1])):
        if sv.size >= 20:
            curve[i] = np.median(sv)
    xc = (bins[:-1] + bins[1:]) / 2
    ok = ~np.isnan(curve)
    cf = np.interp(xc, xc[ok], curve[ok])
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    alph = {k: arr(l_["file"])[..., 3] for k, l_ in byid.items() if "product" in l_}
    sets = [arr(man["slot_cushions"]["sets"][s]["layer"])[..., 3] for s in "ABC"]
    out = {}
    for name, (lf, src, z) in names.items():
        s_ = np.asarray(Image.open(src)).astype(np.float64) / 255
        lay = arr(lf).astype(np.float64) / 255
        inner = V4.erode(lay[..., 3] == 1.0, 2) & (s_[..., 3] >= 1.0)
        for o, a in alph.items():
            if byid[o]["z"] > z:
                inner &= a == 0
        for a in sets:
            inner &= a == 0
        Ls, Ll = V4.lab_L(s_[..., :3])[inner], V4.lab_L(lay[..., :3])[inner]
        r = (Ll - Ls) - np.interp(Ls, xc, cf)
        rec = dict(px=int(inner.sum()), residual_median=round(float(np.median(r)), 3) if inner.any() else None, source=os.path.relpath(src, REPO))
        toe = Ls < 25
        if toe.sum() >= 20:
            rec.update(toe_px=int(toe.sum()), toe_residual_median=round(float(np.median(r[toe])), 3))
        rec["pass_"] = bool(inner.any() and abs(rec["residual_median"]) <= 0.5 and abs(rec.get("toe_residual_median", 0.0)) <= 1.0)
        out[name] = rec
    return out


def main():
    man = json.load(open(MAN))
    rep = dict(manifest=os.path.relpath(MAN, REPO), tolerance=dict(p99_9=TOL_P999, max=TOL_MAX), checks={})
    fails = []
    rep["checks"]["base_same_bytes_as_v3c"] = b_ok = sha(os.path.join(HERE, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
    if not b_ok:
        fails.append("base")
    base = arr("base.png").astype(np.float32)[..., :3]
    size = (base.shape[1], base.shape[0])
    # 2
    rec, union_all, Tdef = {}, np.zeros(base.shape[:2], bool), {}
    for s in "BAC":
        layers = stack_layers(man, s)
        _, _, T = load(os.path.join(P2, f"graded/default-scene-r6-set-{s}-graded-v3c.png"))
        Tdef[s] = T
        union = np.zeros(base.shape[:2], bool)
        for k, lf, sf in layers:
            union |= region_of(lf, sf)[0]
        union_all |= union
        r = dict(float=stats(compose(base, layers, "float"), T, union), bit8=stats(compose(base, layers, "8bit"), T, union))
        for p in ("float", "bit8"):
            if r[p]["p99_9_region"] > TOL_P999 or r[p]["max"] > TOL_MAX:
                fails.append(f"recomposite set {s} {p}")
        rec[s] = r
    rep["checks"]["recomposite_defaults"] = rec
    # 3 + 4
    layersB = stack_layers(man, "B")
    full = compose(base, layersB, "float")
    sw = {}
    for k, lf, sf in layersB:
        reg, alpha = region_of(lf, sf)
        wo = compose(base, layersB, "float", skip=k)
        d = np.abs(rhu(full) - rhu(wo)).max(2) > 0
        sw[k] = dict(changed_px=int(d.sum()), changed_outside_region=int((d & ~reg).sum()), region_px=int(reg.sum()))
        if sw[k]["changed_outside_region"]:
            fails.append(f"swap {k}")
        if alpha.any():
            ys, xs = np.nonzero(alpha)
            ry, rx = np.nonzero(reg)
            far = int(((ry < ys.min() - 60) | (ry > ys.max() + 60) | (rx < xs.min() - 60) | (rx > xs.max() + 60)).sum())
            sw[k]["region_px_beyond_60px_of_its_alpha_box"] = far
            if far:
                fails.append(f"region {k}")
    regs = {s: region_of(man["slot_cushions"]["sets"][s]["layer"], man["slot_cushions"]["sets"][s]["shadow"])[0] for s in "BAC"}
    comps = {s: compose(base, stack_layers(man, s), "float") for s in "BAC"}
    for a_, b_ in (("A", "B"), ("A", "C"), ("B", "C")):
        d = np.abs(rhu(comps[a_]) - rhu(comps[b_])).max(2) > 0
        sw[f"cushions {a_}<->{b_}"] = dict(changed_px=int(d.sum()), changed_outside_union=int((d & ~(regs[a_] | regs[b_])).sum()))
        if sw[f"cushions {a_}<->{b_}"]["changed_outside_union"]:
            fails.append(f"swap cushions {a_}{b_}")
    rep["checks"]["swap_diff_defaults"] = sw
    # 5
    io = {}
    allfiles = [(l_["file"], l_.get("product"), l_["id"]) for l_ in man["layers"] if "file" in l_]
    for k, vs in man["variants"].items():
        for v in vs:
            allfiles += [(v["file"], v["product"], v["id"]), (v["shadow"], None, v["id"] + "-shadow")]
    for f, prod, i in allfiles:
        mode, sz, _ = load(os.path.join(HERE, f))
        io[f] = dict(mode=mode, size=list(sz), ok=list(sz) == list(size) and mode in ("RGB", "RGBA"))
        if not io[f]["ok"]:
            fails.append(f"file {f}")
        if prod:
            c = json.load(open(os.path.join(REPO, prod["card"])))
            skus = [x["id"] for x in ((c.get("options") or {}).get("skus") or [])]
            io[f]["card_ok"] = c["id"] == prod["card_id"] and (prod["sku"] in skus or prod["sku"] in str(c.get("notes", "")))
            if not io[f]["card_ok"]:
                fails.append(f"card {i}")
    rep["checks"]["files"] = io
    g = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", os.path.relpath(P1, REPO)], capture_output=True, text=True)
    rep["checks"]["phase1_unchanged_in_git"] = dict(porcelain=g.stdout.strip().splitlines(), ok=g.returncode == 0 and not g.stdout.strip())
    if not rep["checks"]["phase1_unchanged_in_git"]["ok"]:
        fails.append("phase 1 changed")
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    cur_ok = (byid["curtains"]["product"]["card_id"] == "curtains-aliexpress-linen-blend-s-fold-180502" and
              next(v for v in man["variants"]["curtains"] if v["id"] == "curtains-v2")["product"]["card_id"] == "curtains-aliexpress-beige-linen-sheer-curtains-554205")
    rep["checks"]["curtains_flip"] = dict(default=byid["curtains"]["product"]["card_id"], v2=man["variants"]["curtains"][0]["product"]["card_id"], ok=cur_ok)
    if not cur_ok:
        fails.append("curtains flip")
    # 6 the variants, one at a time (set B)
    vr, vregs, vtruth = {}, {}, {}
    for k, vs in man["variants"].items():
        dreg = region_of(byid[k]["file"], byid[k + "-shadow"]["file"])[0]
        for v in vs:
            _, _, T = load(os.path.join(P2, f"graded/variant-r6-{v['id']}-set-B-graded-v3c.png"))
            vtruth[v["id"]] = T
            lay = swap_in(layersB, {k: (v["file"], v["shadow"])})
            o = compose(base, lay, "float")
            reg = region_of(v["file"], v["shadow"])[0]
            vregs[v["id"]] = (k, reg, dreg)
            r = dict(float=stats(o, T, union_all | reg), bit8=stats(compose(base, lay, "8bit"), T, union_all | reg))
            d = np.abs(rhu(o) - rhu(full)).max(2) > 0
            r["swap_vs_default"] = dict(changed_px=int(d.sum()), changed_outside_the_two_regions=int((d & ~(reg | dreg)).sum()))
            for p in ("float", "bit8"):
                if r[p]["p99_9_region"] > TOL_P999 or r[p]["max"] > TOL_MAX:
                    fails.append(f"variant {v['id']} {p}")
            if r["swap_vs_default"]["changed_outside_the_two_regions"]:
                fails.append(f"variant swap {v['id']}")
            vr[v["id"]] = r
    rep["checks"]["variants"] = vr
    # 7 disjoint slots, and the full cross
    slot_union = {k: region_of(lf, sf)[0] for k, lf, sf in layersB}
    for vid, (k, reg, _) in vregs.items():
        slot_union[k] = slot_union[k] | reg
    vslots = sorted({k for k, _, _ in vregs.values()})
    disj = {}
    for k in vslots:
        for j in slot_union:
            if j != k and j != "cushions":
                n = int((slot_union[k] & slot_union[j]).sum())
                if n:
                    disj[f"{k} x {j}"] = n
        n = int((slot_union[k] & (regs["A"] | regs["B"] | regs["C"])).sum())
        if n:
            disj[f"{k} x cushion sets"] = n
    if disj or man.get("disjoint_overlaps"):
        fails.append("regions not disjoint")
    options = {k: [("default", byid[k]["file"], byid[k + "-shadow"]["file"])] + [(v["id"], v["file"], v["shadow"]) for v in man["variants"][k]]
               for k in vslots}
    n_opts = {k: len(v) for k, v in options.items()}
    worst = dict(p999=0.0, max=0.0, indep_max=0.0)
    per = {}
    fails_cross = []
    for s in "BAC":
        layers = stack_layers(man, s)
        for pipe in ("float", "8bit"):
            single = {}

            def keep_single(combo, out):
                nd = [k for k in vslots if combo[k] != "default"]
                if len(nd) <= 1:
                    single[tuple(sorted(combo.items()))] = out

            leaves = []

            def visit(combo, out):
                keep_single(combo, out)
                T = Tdef[s].copy()
                for k in vslots:
                    if combo[k] != "default":
                        _, reg, dreg = vregs[combo[k]]
                        T[dreg] = vtruth[combo[k]][dreg]
                        T[reg] = vtruth[combo[k]][reg]
                st = stats(out, T, union_all)
                leaves.append((combo, rhu(out).astype(np.uint8), st))
            dfs(base, layers, options, pipe, visit)
            # independence: the default composite, each slot's region from its option alone
            dflt = single[tuple(sorted({k: "default" for k in vslots}.items()))]
            for combo, out8, st in leaves:
                P = rhu(dflt).astype(np.uint8).copy()
                for k in vslots:
                    if combo[k] != "default":
                        one = single[tuple(sorted(dict({j: "default" for j in vslots}, **{k: combo[k]}).items()))]
                        m = slot_union[k]
                        P[m] = rhu(one).astype(np.uint8)[m]
                indep = int(np.abs(P.astype(np.int16) - out8.astype(np.int16)).max())
                key = f"set {s} / {pipe} / " + ", ".join(f"{k}={combo[k]}" for k in vslots)
                per[key] = dict(p99_9=st["p99_9_region"], max=st["max"], independence_max=indep)
                worst["p999"] = max(worst["p999"], st["p99_9_region"])
                worst["max"] = max(worst["max"], st["max"])
                worst["indep_max"] = max(worst["indep_max"], indep)
                if st["p99_9_region"] > TOL_P999 or st["max"] > TOL_MAX or indep:
                    fails_cross.append(key)
            print("cross", s, pipe, len(leaves), worst, flush=True)
    n_combo = int(np.prod(list(n_opts.values())))
    rep["checks"]["full_cross"] = dict(slots=vslots, options=n_opts, n_combos=n_combo, n_composites=len(per), worst=worst,
                                       all_pass=not fails_cross, failing=fails_cross[:20], disjoint_overlaps=disj, composites=per)
    if fails_cross:
        fails.append(f"full cross ({len(fails_cross)})")
    # 8 one grade on the R6 changes
    W6 = os.path.join(P2, "work-r6", "layers")
    W5 = os.path.join(P2, "work-r5", "layers")
    names = {"curtains": (byid["curtains"]["file"], os.path.join(W6, "curtains.png"), byid["curtains"]["z"]),
             "vase": (byid["vase"]["file"], os.path.join(W6, "vase.png"), byid["vase"]["z"]),
             "magazine-holder": (byid["magazine-holder"]["file"], os.path.join(W6, "magazine-holder.png"), byid["magazine-holder"]["z"])}
    for k, vs in man["variants"].items():
        for v in vs:
            src = os.path.join(W6, f"{v['id']}.png")
            names[v["id"]] = (v["file"], src if os.path.exists(src) else os.path.join(W5, f"{v['id']}.png"), v["z"])
    rep["checks"]["one_v3c_grade"] = gr = grade_check(names)
    for k, v in gr.items():
        if not v["pass_"]:
            fails.append(f"grade {k}")
    rep["fails"] = fails
    rep["pass"] = not fails
    json.dump(rep, open(os.path.join(HERE, "verify-layers-r6.json"), "w"), indent=1)
    print(json.dumps(dict(recomposite={s: {p: (v[p]["p99_9_region"], v[p]["max"]) for p in ("float", "bit8")} for s, v in rec.items()},
                          swap_outside=sum(v.get("changed_outside_region", v.get("changed_outside_union", 0)) for v in sw.values()),
                          variants={k: dict(f=(v["float"]["p99_9_region"], v["float"]["max"]), b=(v["bit8"]["p99_9_region"], v["bit8"]["max"]),
                                            out=v["swap_vs_default"]["changed_outside_the_two_regions"]) for k, v in vr.items()},
                          full_cross=dict(n=len(per), worst=worst), disjoint=disj,
                          grade={k: (v["residual_median"], v.get("toe_residual_median")) for k, v in gr.items()}, fails=fails), indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
