#!/usr/bin/env python3
"""
verify_layers_r7.py: re-runnable check of the warm-modern tool's phase-2 layers after R7 (render-agent, 2026-11-12; for qa-agent).
Reads manifest-r7.json and the files it names (numpy + Pillow; the helpers of verify_layers_r4.py); writes verify-layers-r7.json; exit 0 =
every check passes. Read-only on everything else.

  python3 verify_layers_r7.py

Checks (as verify_layers_r6.py, on the R7 files)
  1. base.png is the approved layers-v3c/base.png (same bytes).
  2. Recomposite of the default stack with set B / A / C against graded/default-scene-r7-set-X: p99.9 <= 2 and max <= 6 over the union of
     the regions, float and browser-like 8-bit pipelines.
  3. Swap-diff per default layer (set B) and between the cushion sets: 0 px changed outside the product's region (the sets' union).
  4. Regions are tight (no alpha or shadow pixel > 60 px beyond the product's alpha box).
  5. Files: size and mode; every product card (defaults and variants) exists with its id and SKU; phase 1 unchanged in git; the curtains:
     default 180502, v2 554205, v3 the Japanese linen; the basket changed only in its soft edge (RGB at full alpha equal, alpha within 2).
  6. Each VARIANT in for its slot's default (set B): against its truth (graded/variant-r7-<name>-set-B) within the gate; default <-> variant
     changes 0 px outside the union of the two regions.
  7. THE FULL CROSS: every combination of the slots' options (curtains 3 x framed-art 2 x accent-sconces 3 x vase 3 x pendant 2 x bowl 2 x
     candle-holders 2 = 432) x the cushion sets B / A / C x the float and 8-bit pipelines (2,592 composites), each against the truth built
     from each option's own truth, within the gate; and independence: each composite equals, byte for byte, the default composite with
     every slot's region taken from that slot's option composed alone. Exact and fast: outside the union of the variant slots' regions
     every option is the identity (alpha 0, shadow 255), so each composite equals the default composite there; the walk composes only the
     pixels of that union (a depth-first walk sharing prefixes), and the gate's p99.9 over the regions' union merges the per-combination
     histogram inside with the constant one outside (numpy's linear percentile, reproduced from the integer histogram).
  8. ONE v3c grade on every layer changed in R7 (verify_layers_r4.py's method): the residual against its ungraded source, |median| <= 0.5
     and the toe within +-1.
"""
import importlib.util
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
spec6 = importlib.util.spec_from_file_location("v6", os.path.join(HERE, "verify_layers_r6.py"))
V6 = importlib.util.module_from_spec(spec6)
spec6.loader.exec_module(V6)
REPO, P2, P1 = V4.REPO, V4.P2, V4.P1
TOL_P999, TOL_MAX = V4.TOL_P999, V4.TOL_MAX
load, rhu, stats, compose, region_of, stack_layers, sha = V4.load, V4.rhu, V4.stats, V4.compose, V4.region_of, V4.stack_layers, V4.sha
MAN = os.path.join(HERE, "manifest-r7.json")
V6.MAN = MAN
arr = V6.arr


def pct_from_hist(h, q):
    """numpy's default (linear) percentile of the integer sample whose histogram is h"""
    n = int(h.sum())
    if n == 0:
        return 0.0
    pos = q / 100.0 * (n - 1)
    lo, hi = int(np.floor(pos)), int(np.ceil(pos))
    c = np.cumsum(h)
    vlo = int(np.searchsorted(c, lo + 1))
    vhi = int(np.searchsorted(c, hi + 1))
    return float(vlo + (pos - lo) * (vhi - vlo))


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
        _, _, T = load(os.path.join(P2, f"graded/default-scene-r7-set-{s}-graded-v3c.png"))
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
            io[f]["card_ok"] = c["id"] == prod["card_id"] and (prod["sku"] in skus or prod["sku"].split(" ")[0] in str(c.get("notes", "")))
            if not io[f]["card_ok"]:
                fails.append(f"card {i}")
    rep["checks"]["files"] = io
    g = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", os.path.relpath(P1, REPO)], capture_output=True, text=True)
    rep["checks"]["phase1_unchanged_in_git"] = dict(porcelain=g.stdout.strip().splitlines(), ok=g.returncode == 0 and not g.stdout.strip())
    if not rep["checks"]["phase1_unchanged_in_git"]["ok"]:
        fails.append("phase 1 changed")
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    cv = {v["id"]: v["product"]["card_id"] for v in man["variants"]["curtains"]}
    cur_ok = (byid["curtains"]["product"]["card_id"] == "curtains-aliexpress-linen-blend-s-fold-180502"
              and cv.get("curtains-v2") == "curtains-aliexpress-beige-linen-sheer-curtains-554205"
              and cv.get("curtains-v3") == "curtains-cj-japanese-linen-half-shade")
    rep["checks"]["curtains_options"] = dict(default=byid["curtains"]["product"]["card_id"], variants=cv, ok=cur_ok)
    if not cur_ok:
        fails.append("curtains options")
    m6 = json.load(open(os.path.join(HERE, "manifest-r6.json")))
    b6 = next(l_ for l_ in m6["layers"] if l_["id"] == "basket")["file"]
    A6, A7 = arr(b6).astype(int), arr(byid["basket"]["file"]).astype(int)
    dd = np.abs(A6 - A7).max(2) > 0
    bse = dict(r6=b6, r7=byid["basket"]["file"], px_changed=int(dd.sum()),
               rgb_changed_at_full_alpha=int((dd & (A6[..., 3] == 255) & (A7[..., 3] == 255)).sum()),
               alpha_changed_px=int((A6[..., 3] != A7[..., 3]).sum()), alpha_max_diff=int(np.abs(A6[..., 3] - A7[..., 3]).max()))
    bse["ok"] = bse["rgb_changed_at_full_alpha"] == 0 and bse["alpha_max_diff"] <= 2
    rep["checks"]["basket_soft_edge"] = bse
    if not bse["ok"]:
        fails.append("basket changed beyond its soft edge")
    # 6 the variants, one at a time (set B)
    vr, vregs, vtruth = {}, {}, {}
    for k, vs in man["variants"].items():
        dreg = region_of(byid[k]["file"], byid[k + "-shadow"]["file"])[0]
        for v in vs:
            _, _, T = load(os.path.join(P2, f"graded/variant-r7-{v['id']}-set-B-graded-v3c.png"))
            vtruth[v["id"]] = T
            lay = V6.swap_in(layersB, {k: (v["file"], v["shadow"])})
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
    # 7 disjoint slots, and the full cross on the union of the variant slots' regions
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
    VM = np.zeros(base.shape[:2], bool)
    for k in vslots:
        VM |= slot_union[k]
    idx = np.nonzero(VM.ravel())[0]
    slot_of_px = np.full(idx.shape, -1, np.int16)
    for i, k in enumerate(vslots):
        slot_of_px[slot_union[k].ravel()[idx]] = i
    sub_cache = {}

    def sub(f):
        if f not in sub_cache:
            a = arr(f).astype(np.float32)
            a = a.reshape(-1, a.shape[2]) if a.ndim == 3 else a.reshape(-1, 1)
            sub_cache[f] = a[idx]
        return sub_cache[f]

    def step(o, lf, sf, pipe):
        L = sub(lf)
        S = sub(sf)
        a = L[:, 3:4] / 255.0
        if pipe == "float":
            return (o * S[:, :3] / 255.0) * (1 - a) + L[:, :3] * a
        m = np.floor(o * S[:, :3] / 255.0 + 0.5)
        pre = np.floor(L[:, :3] * a + 0.5)
        return np.floor(pre + m * (1 - a) + 0.5)

    options = {k: [("default", byid[k]["file"], byid[k + "-shadow"]["file"])] + [(v["id"], v["file"], v["shadow"]) for v in man["variants"][k]]
               for k in vslots}
    n_opts = {k: len(v) for k, v in options.items()}
    ua_in = union_all.ravel()[idx]
    out_mask = union_all & ~VM
    base_sub = base.reshape(-1, 3)[idx]
    worst = dict(p999=0.0, max=0.0, indep_max=0.0)
    per = {}
    fails_cross = []
    for s in "BAC":
        layers = stack_layers(man, s)
        Tsub_def = Tdef[s].reshape(-1, 3)[idx]
        vt_sub = {vid: T.reshape(-1, 3)[idx] for vid, T in vtruth.items()}
        vreg_sub = {vid: (vregs[vid][1].ravel()[idx], vregs[vid][2].ravel()[idx]) for vid in vregs}
        for pipe in ("float", "8bit"):
            # the constant part outside the variant slots: the default composite against the default truth
            Dfull = compose(base, layers, "float" if pipe == "float" else "8bit")
            dout = np.abs(rhu(Dfull) - Tdef[s]).max(2)
            h_out = np.bincount(dout[out_mask].astype(np.int64), minlength=256).astype(np.int64)
            max_out = float(dout[~VM].max()) if (~VM).any() else 0.0
            singles = {}
            count = [0]

            def walk(visit, only_singles):
                def rec(i, o, combo):
                    while i < len(layers) and layers[i][0] not in options:
                        k, lf, sf = layers[i]
                        o = step(o, lf, sf, pipe)
                        i += 1
                    if i == len(layers):
                        visit(combo, rhu(o).astype(np.uint8))
                        return
                    k = layers[i][0]
                    for name, lf, sf in options[k]:
                        c2 = dict(combo, **{k: name})
                        if only_singles and sum(v != "default" for v in c2.values()) > 1:
                            continue
                        rec(i + 1, step(o, lf, sf, pipe), c2)
                rec(0, base_sub.astype(np.float32), {})

            def keep_single(combo, o8):
                singles[tuple(sorted(combo.items()))] = o8
            walk(keep_single, True)
            dflt = singles[tuple(sorted({k: "default" for k in vslots}.items()))]

            def visit(combo, o8):
                count[0] += 1
                T = Tsub_def.copy()
                P = dflt.copy()
                for i, k in enumerate(vslots):
                    if combo[k] != "default":
                        reg, dreg = vreg_sub[combo[k]]
                        T[dreg] = vt_sub[combo[k]][dreg]
                        T[reg] = vt_sub[combo[k]][reg]
                        one = singles[tuple(sorted(dict({j: "default" for j in vslots}, **{k: combo[k]}).items()))]
                        msk = slot_of_px == i
                        P[msk] = one[msk]
                d = np.abs(o8.astype(np.float64) - T).max(1)
                h = h_out + np.bincount(d[ua_in].astype(np.int64), minlength=256)
                p999 = pct_from_hist(h, 99.9)
                mx = max(max_out, float(d.max()))
                indep = int(np.abs(P.astype(np.int16) - o8.astype(np.int16)).max())
                key = f"set {s} / {pipe} / " + ", ".join(f"{k}={combo[k]}" for k in vslots)
                per[key] = dict(p99_9=p999, max=mx, independence_max=indep)
                worst["p999"] = max(worst["p999"], p999)
                worst["max"] = max(worst["max"], mx)
                worst["indep_max"] = max(worst["indep_max"], indep)
                if p999 > TOL_P999 or mx > TOL_MAX or indep:
                    fails_cross.append(key)
            walk(visit, False)
            print("cross", s, pipe, count[0], worst, flush=True)
    n_combo = int(np.prod(list(n_opts.values())))
    rep["checks"]["full_cross"] = dict(slots=vslots, options=n_opts, n_combos=n_combo, n_composites=len(per), worst=worst,
                                       pixels_walked=int(len(idx)), all_pass=not fails_cross, failing=fails_cross[:20], disjoint_overlaps=disj,
                                       method="the walk composes only the union of the variant slots' regions (elsewhere every option is the "
                                              "identity); p99.9 merges that part's histogram with the constant one outside",
                                       composites=per)
    if fails_cross:
        fails.append(f"full cross ({len(fails_cross)})")
    # 8 one grade on the R7 changes
    W7 = os.path.join(P2, "work-r7", "layers")
    names = {k: (byid[k]["file"], os.path.join(W7, f"{k}.png"), byid[k]["z"]) for k in ("curtains", "planter", "candle-holders", "bowl")}
    for vid in ("curtains-v2", "curtains-v3", "bowl-v2", "candle-holders-v2", "vase-v3"):
        v = next(x for vs in man["variants"].values() for x in vs if x["id"] == vid)
        names[vid] = (v["file"], os.path.join(W7, f"{vid}.png"), v["z"])
    rep["checks"]["one_v3c_grade"] = gr = V6.grade_check(names)
    for k, v in gr.items():
        if not v["pass_"]:
            fails.append(f"grade {k}")
    rep["fails"] = fails
    rep["pass"] = not fails
    json.dump(rep, open(os.path.join(HERE, "verify-layers-r7.json"), "w"), indent=1)
    print(json.dumps(dict(recomposite={s: {p: (v[p]["p99_9_region"], v[p]["max"]) for p in ("float", "bit8")} for s, v in rec.items()},
                          swap_outside=sum(v.get("changed_outside_region", v.get("changed_outside_union", 0)) for v in sw.values()),
                          variants={k: dict(f=(v["float"]["p99_9_region"], v["float"]["max"]), b=(v["bit8"]["p99_9_region"], v["bit8"]["max"]),
                                            out=v["swap_vs_default"]["changed_outside_the_two_regions"]) for k, v in vr.items()},
                          full_cross=dict(n=len(per), worst=worst), disjoint=disj, basket=bse,
                          grade={k: (v["residual_median"], v.get("toe_residual_median")) for k, v in gr.items()}, fails=fails), indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
