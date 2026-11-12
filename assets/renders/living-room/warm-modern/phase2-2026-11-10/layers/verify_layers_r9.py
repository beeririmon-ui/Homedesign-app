#!/usr/bin/env python3
"""
verify_layers_r9.py: re-runnable check of the warm-modern tool's phase-2 layers after R9 (render-agent, 2026-11-12; for qa-agent).
Reads manifest-r9.json and the files it names (numpy + Pillow + OpenCV; the helpers of verify_layers_r4.py / _r6.py / _r8.py, loaded
read-only); writes verify-layers-r9.json; exit 0 = every check passes. Read-only on everything else.

  python3.12 -I verify_layers_r9.py

Checks 1-8: verify_layers_r8.py's, unchanged, on the R9 files and truths (the default truths are R8's: neither default changed):
  1 base.png is the approved v3c base; 2 recomposite of the default stack (sets B / A / C) p99.9 <= 2, max <= 6, float and 8-bit;
  3 swap-diff per default layer: 0 px outside its region; 4 regions tight; 5 files, cards, phase 1 unchanged in git, the curtains' options;
  6 each variant against its truth, and 0 px outside the two regions; 7 THE FULL CROSS (432 combinations x B / A / C x float / 8-bit =
  2,592 composites) within the gate and independent; the slots' regions disjoint; 8 ONE v3c grade on every layer changed in R7-R9
  (pendant 2 against its ungraded R6 source, curtain 3 against its ungraded R8 source).
Check 9, R9:
  (scope)    against manifest-r8.json: only the pendant-2 and curtain-3 LAYERS are new files; every shadow, every other layer, the cushion sets,
             the default truths and the other 8 variant truths are the R8 files; every file in QA's R8 sha256 list
             (qa/reports/2026-11-12-wm-phase2-r8/data/manifest.json) still has QA's hash; no tracked file under phase 2 is modified in git.
  (pendant2) P2-1, the designer's (a)-(f) (docs/proposals/wm-pendant2-eye-2026-11-12.md section 4), measured on the files:
             (a) the refined 50 % line against the fit (work-r9/pendant2-outline-r9.npy) <= 1 px where fitted, one turn sign at 4-px chords;
             (b) the right edge: no 4-px chord turns more than 2 x its neighbours; (c) the 10-90 % ramp on both flanks within 0.5 px of the
             reference (the default pendant against the wall, fix-r9.json); (d) the widest row within 2 px; (e) QA's halo metric
             (r67_halo.analyse, loaded read-only) on the R9 truth: <= 10 bright px on the lantern, no dark fringe outside the cord beyond R8's;
             (f) the variant alone in sets B / A / C (from the full cross); + RGB at alpha 255 unchanged, RGB changed only where the alpha
             rose, the canopy / cord / collar unchanged, the shadow the R8 file; the stop numbers (fix-r9.json).
  (curtain3) the designer's literal rule 0 at alpha > 0 (R8's and QA's Lab); the wide rule 0 at alpha >= 128 (R8's Lab); exactly the 11
             mask pixels changed, alpha the same bytes; L* kept on them (<= 0.05); the truth changed only there; the colour in QA's same mask
             against the designer's lock (L* 71.5-74.5, h 81-87, C* 10.5-12.5) and unchanged from R8.
  (records)  QA R8 F2: the final-pass mask beside the speck mask (44 px, disjoint), the alpha_unchanged correction in fix-r9.json.
  (lock)     the shell lock (QA's shell_lock.py reader, lock_r7.py's rule: every named line p90 <= 9.6 px, >= 20 paired) on the default
             set-B scene and the two new truths.
"""
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V4 = _load("v4", "verify_layers_r4.py")
V6 = _load("v6", "verify_layers_r6.py")
V8 = _load("v8", "verify_layers_r8.py")
REPO, P2, P1 = V4.REPO, V4.P2, V4.P1
TOL_P999, TOL_MAX = V4.TOL_P999, V4.TOL_MAX
load, rhu, stats, compose, region_of, stack_layers = V4.load, V4.rhu, V4.stats, V4.compose, V4.region_of, V4.stack_layers
MAN = os.path.join(HERE, "manifest-r9.json")
V6.MAN = MAN
arr = V6.arr
QA8 = os.path.join(REPO, "qa/reports/2026-11-12-wm-phase2-r8/data/manifest.json")
sys.path.insert(0, P2)
import fix_r9 as F9  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def truth_of(v):
    return os.path.normpath(os.path.join(HERE, v["truth"]))


def main():
    man = json.load(open(MAN))
    m8 = json.load(open(os.path.join(HERE, "manifest-r8.json")))
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
        _, _, T = load(os.path.normpath(os.path.join(HERE, man["truths"]["default"][s])))
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
    # 6 the variants, one at a time (set B)
    vr, vregs, vtruth = {}, {}, {}
    for k, vs in man["variants"].items():
        dreg = region_of(byid[k]["file"], byid[k + "-shadow"]["file"])[0]
        for v in vs:
            _, _, T = load(truth_of(v))
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
    # 7 the full cross (verify_layers_r8.py's walk, unchanged)
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
            Dfull = compose(base, layers, "float" if pipe == "float" else "8bit")
            dout = np.abs(rhu(Dfull) - Tdef[s]).max(2)
            h_out = np.bincount(dout[out_mask].astype(np.int64), minlength=256).astype(np.int64)
            max_out = float(dout[~VM].max()) if (~VM).any() else 0.0
            singles = {}
            count = [0]

            def walk(visit, only_singles):
                def rec_(i, o, combo):
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
                        rec_(i + 1, step(o, lf, sf, pipe), c2)
                rec_(0, base_sub.astype(np.float32), {})

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
                p999 = V8.pct_from_hist(h, 99.9)
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
                                       method="verify_layers_r8.py's walk, unchanged", composites=per)
    if fails_cross:
        fails.append(f"full cross ({len(fails_cross)})")
    # 8 one grade on the layers changed in R7-R9
    W6, W7, W8 = (os.path.join(P2, f"work-r{i}", "layers") for i in (6, 7, 8))
    src8 = {"candle-holders", "curtains", "curtains-v2", "curtains-v3"}
    names = {k: (byid[k]["file"], os.path.join(W8 if k in src8 else W7, f"{k}.png"), byid[k]["z"]) for k in ("curtains", "planter", "candle-holders", "bowl")}
    vv = {x["id"]: x for vs in man["variants"].values() for x in vs}
    for vid in ("curtains-v2", "curtains-v3", "bowl-v2", "candle-holders-v2", "vase-v3"):
        names[vid] = (vv[vid]["file"], os.path.join(W8 if vid in src8 else W7, f"{vid}.png"), vv[vid]["z"])
    names["pendant-v2"] = (vv["pendant-v2"]["file"], os.path.join(W6, "pendant-v2.png"), vv["pendant-v2"]["z"])
    rep["checks"]["one_v3c_grade"] = gr = V6.grade_check(names)
    for k, v in gr.items():
        if not v["pass_"]:
            fails.append(f"grade {k}")
    # 9 R9
    rep["checks"]["r9"] = r9 = r9_checks(man, m8, per)
    for k, v in r9.items():
        if isinstance(v, dict) and v.get("pass_") is False:
            fails.append(f"r9 {k}")
    rep["fails"] = fails
    rep["pass"] = not fails
    json.dump(rep, open(os.path.join(HERE, "verify-layers-r9.json"), "w"), indent=1, default=float)
    print(json.dumps(dict(recomposite={s: {p: (v[p]["p99_9_region"], v[p]["max"]) for p in ("float", "bit8")} for s, v in rec.items()},
                          swap_outside=sum(v.get("changed_outside_region", v.get("changed_outside_union", 0)) for v in sw.values()),
                          variants={k: dict(f=(v["float"]["p99_9_region"], v["float"]["max"]), b=(v["bit8"]["p99_9_region"], v["bit8"]["max"]),
                                            out=v["swap_vs_default"]["changed_outside_the_two_regions"]) for k, v in vr.items()},
                          full_cross=dict(n=len(per), worst=worst), disjoint=disj,
                          grade={k: (v["residual_median"], v.get("toe_residual_median")) for k, v in gr.items()},
                          r9={k: (v.get("pass_"), v.get("summary")) for k, v in r9.items() if isinstance(v, dict)}, fails=fails), indent=1, default=float))
    sys.exit(0 if not fails else 1)


# ------------------------------------------------------------------------------------------------- 9 R9
def _files(man):
    f = {l_["id"]: l_["file"] for l_ in man["layers"] if "file" in l_}
    for vs in man["variants"].values():
        for v in vs:
            f[v["id"]], f[v["id"] + "-shadow"], f[v["id"] + "-truth"] = v["file"], v["shadow"], os.path.basename(v["truth"])
    for s in "BAC":
        f[f"cushions-{s}"], f[f"cushions-{s}-shadow"] = man["slot_cushions"]["sets"][s]["layer"], man["slot_cushions"]["sets"][s]["shadow"]
    return f


def scope(man, m8):
    f8, f9 = _files(m8), _files(man)
    f8.update({f"default-truth-{s}": f"default-scene-r8-set-{s}-graded-v3c.png" for s in "BAC"})
    f9.update({f"default-truth-{s}": os.path.basename(man["truths"]["default"][s]) for s in "BAC"})
    changed = sorted(k for k in f9 if f9[k] != f8.get(k))
    expected = ["curtains-v3", "curtains-v3-truth", "pendant-v2", "pendant-v2-truth"]
    qa = json.load(open(QA8))["manifest_r8"]["rows"]
    bad, n = [], 0
    for r in qa:
        p = os.path.join(REPO, r["path"])
        if "sha256_qa" in r and os.path.isfile(p):
            n += 1
            if sha(p) != r["sha256_qa"]:
                bad.append(r["path"])
    g = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=no", "--", os.path.relpath(P2, REPO)], capture_output=True, text=True)
    mod = g.stdout.strip().splitlines()
    out = dict(changed_vs_r8=changed, expected=expected, qa_r8_sha256_files_checked=n, qa_r8_sha256_mismatch=bad, git_modified_tracked_under_phase2=mod)
    out["pass_"] = changed == expected and not bad and n > 0 and g.returncode == 0 and not mod
    out["summary"] = dict(changed=changed, qa_hash_files=n, mismatches=len(bad), git_modified=len(mod))
    return out


def pendant2(man, m8, per):
    fx = json.load(open(os.path.join(P2, "work-r9", "fix-r9.json")))["pendant2"]
    v8 = next(v for v in m8["variants"]["pendant"] if v["id"] == "pendant-v2")
    v9 = next(v for v in man["variants"]["pendant"] if v["id"] == "pendant-v2")
    L8, L9 = arr(v8["file"]).astype(int), arr(v9["file"]).astype(int)
    A8, A9 = L8[..., 3], L9[..., 3]
    cx, cy = fx["geometry"]["centre_px"]
    thR, thL = fx["geometry"]["bottom_arc"]["theta_deg"]
    thTL = fx["geometry"]["left_flank"]["theta_deg"][1]
    poly = np.load(os.path.join(P2, "work-r9", "pendant2-outline-r9.npy"))
    g9 = F9.pendant_geometry(A9.astype(np.uint8), cx, cy, poly, thR, thL, thTL)
    g8 = F9.pendant_geometry(A8.astype(np.uint8), cx, cy, None, thR, thL, thTL)
    rr9, rr8 = F9.flank_ramps(A9.astype(np.uint8), cx), F9.flank_ramps(A8.astype(np.uint8), cx)
    ref = F9.default_pendant_ramp()["flanks"]
    # (e) QA's halo metric on the truths (the pendant is the top layer: nothing above it)
    halo = V8._qa_halo()
    out_e = {}
    for tag, L_, tp in (("r8", L8, os.path.join(P2, "graded", "variant-r8-pendant-v2-set-B-graded-v3c.png")), ("r9", L9, os.path.normpath(os.path.join(HERE, v9["truth"])))):
        T = np.asarray(Image.open(tp).convert("RGB"))
        A = L_[..., 3].astype(np.uint8)
        cordzone = np.zeros(A.shape, bool)
        cordzone[:F9.TOP + 6] = True                                   # the cord and the canopy (above the lantern's collar)
        out_e[tag] = dict(lantern=halo["analyse"](halo["Lof"](T), A, f"r9check-p2-{tag}", T, cordzone, save=False),
                          cord_and_canopy=halo["analyse"](halo["Lof"](T), A, f"r9check-p2c-{tag}", T, ~cordzone, save=False))
    S8, S9 = arr(v8["shadow"]), arr(v9["shadow"])
    up = A9 > A8
    rgbch = (L8[..., :3] != L9[..., :3]).any(2)
    yy, xx = np.mgrid[0:A8.shape[0], 0:A8.shape[1]]
    zone = (np.abs(xx - F9.CORD_X) <= F9.COLLAR_DX) & (yy <= F9.COLLAR_Y)        # fix_r9's kept collar, exactly
    alone = {f"set {s} {p}": per[k] for s in "BAC" for p in ("float", "8bit")
             for k in per if k.startswith(f"set {s} / {p} /") and "pendant=pendant-v2" in k
             and all(f"{sl}=default" in k for sl in ("curtains", "framed-art", "accent-sconces", "vase", "bowl", "candle-holders"))}
    st = fx["stop_rule"]
    a_ok = g9["line_vs_fit_px"]["right_side_max_abs"] <= 1 and g9["line_vs_fit_px"]["left_flank_max_abs"] <= 1 \
        and g9["turns_4px"]["right_side_opposite"] == 0 and g9["turns_4px"]["left_flank_opposite"] == 0
    b_ok = g9["right_edge_corner"]["chords_over_2x"] == 0
    c_ok = abs(rr9["left"] - ref) <= 0.5 and abs(rr9["right"] - ref) <= 0.5
    d_ok = abs(g9["widest_row"]["width_px"] - g8["widest_row"]["width_px"]) <= 2
    e_ok = out_e["r9"]["lantern"]["bright_halo_px"] <= 10 and out_e["r9"]["lantern"]["dark_fringe_px"] <= out_e["r8"]["lantern"]["dark_fringe_px"]
    f_ok = all(v["p99_9"] <= TOL_P999 and v["max"] <= TOL_MAX and v["independence_max"] == 0 for v in alone.values()) and len(alone) == 6
    colour = dict(rgb_changed_at_alpha_255_both=int((rgbch & (A8 == 255) & (A9 == 255)).sum()), rgb_changed_where_alpha_did_not_rise=int((rgbch & ~up).sum()),
                  collar_cord_canopy_changed=int((((A8 != A9) | rgbch) & zone).sum() + (((A8 != A9) | rgbch)[:190]).sum()),
                  shadow_same_file=v8["shadow"] == v9["shadow"], shadow_same_bytes=bool(np.array_equal(S8, S9)))
    col_ok = colour["rgb_changed_at_alpha_255_both"] == 0 and colour["rgb_changed_where_alpha_did_not_rise"] == 0 \
        and colour["collar_cord_canopy_changed"] == 0 and colour["shadow_same_bytes"]
    stop_ok = all(v["cut"] <= 3 and v["fill"] <= 2 for k, v in st["applied"].items() if k in ("right_side", "left_flank"))
    out = dict(a_line=dict(r8_turns=g8["turns_4px"], r9=g9["line_vs_fit_px"], r9_turns=g9["turns_4px"], pass_=a_ok),
               b_right_edge=dict(r8=g8["right_edge_corner"], r9=g9["right_edge_corner"], pass_=b_ok),
               c_ramp=dict(reference=ref, r8=rr8, r9=rr9, rule="both flanks within +-0.5 px of the reference", pass_=c_ok),
               d_width=dict(r8_px=g8["widest_row"], r9_px=g9["widest_row"], change_px=round(g9["widest_row"]["width_px"] - g8["widest_row"]["width_px"], 3),
                            cm_at_41=round((g9["widest_row"]["width_px"] - g8["widest_row"]["width_px"]) * 41 / g8["widest_row"]["width_px"], 3), pass_=d_ok),
               e_halo=dict(r8=out_e["r8"], r9=out_e["r9"], rule="<= 10 bright px on the lantern; no dark fringe on the lantern beyond R8's (the cord apart)",
                           pass_=e_ok),
               f_alone_in_three_sets=dict(composites=alone, pass_=f_ok),
               colour_and_scope=dict(colour, pass_=col_ok),
               stop_rule=dict(applied=st["applied"], top_left_arc=st["top_left_arc"]["whole_left_side_least_squares"],
                              top_left_decision=st["top_left_arc"]["decision"], pass_=stop_ok))
    out["pass_"] = all(v["pass_"] for v in out.values() if isinstance(v, dict) and "pass_" in v)
    out["summary"] = dict(a=(g9["line_vs_fit_px"], g9["turns_4px"]["right_side_opposite"], g9["turns_4px"]["left_flank_opposite"]),
                          b=g9["right_edge_corner"]["max_turn_over_neighbours"], c=(ref, rr9["left"], rr9["right"]), d=out["d_width"]["change_px"],
                          e=(out_e["r9"]["lantern"]["bright_halo_px"], out_e["r9"]["lantern"]["dark_fringe_px"], out_e["r8"]["lantern"]["dark_fringe_px"]),
                          stop=st["applied"])
    return out


def curtain3(man, m8):
    fx = json.load(open(os.path.join(P2, "work-r9", "fix-r9.json")))["curtain3"]
    v8 = next(v for v in m8["variants"]["curtains"] if v["id"] == "curtains-v3")
    v9 = next(v for v in man["variants"]["curtains"] if v["id"] == "curtains-v3")
    C8, C9 = arr(v8["file"]), arr(v9["file"])
    m = np.load(os.path.join(P2, "work-r9", "curtain3-soft-edge-mask-r9.npy"))
    cnt9, _ = F9.counts(C9[..., :3], C9[..., 3])
    cnt8, _ = F9.counts(C8[..., :3], C8[..., 3])
    ch = (C8 != C9).any(2)
    L8_, L9_ = F9.lab_cv(C8[..., :3])[..., 0], F9.lab_cv(C9[..., :3])[..., 0]
    T8 = np.asarray(Image.open(os.path.join(P2, "graded", "variant-r8-curtains-v3-set-B-graded-v3c.png")).convert("RGB"))
    T9 = np.asarray(Image.open(os.path.normpath(os.path.join(HERE, v9["truth"]))).convert("RGB"))
    tch = (T8 != T9).any(2)
    import cv2
    same = np.ones(C9.shape[:2], bool)
    f9 = {l_["id"]: l_["file"] for l_ in man["layers"] if "file" in l_}
    for f in (f9["curtains"], next(v["file"] for v in man["variants"]["curtains"] if v["id"] == "curtains-v2"), v9["file"]):
        A = arr(f)[..., 3]
        mm = cv2.erode((A == 255).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        mm[:100] = False
        mm[1150:] = False
        same &= mm

    def summ(T, lab):
        lb = lab(T)[same].astype(np.float64)
        L_, a_, b_ = np.median(lb, 0)
        return dict(L=round(float(L_), 3), C=round(float(math.hypot(a_, b_)), 3), h=round(float(math.degrees(math.atan2(b_, a_)) % 360), 2))
    lock = dict(qa_lab=summ(T9, F9.lab_qa), r8_lab=summ(T9, F9.lab_cv), r8_truth_qa_lab=summ(T8, F9.lab_qa), mask_px=int(same.sum()),
                truth_changed_in_mask=int((tch & same).sum()), designer_lock=dict(L=[71.5, 74.5], h=[81, 87], C=[10.5, 12.5]))
    inlock = {lab_: dict(L=71.5 <= v["L"] <= 74.5, h=81 <= v["h"] <= 87, C=10.5 <= v["C"] <= 12.5) for lab_, v in (("qa_lab", lock["qa_lab"]), ("r8_lab", lock["r8_lab"]))}
    lock["in_lock"] = inlock
    lock["note"] = ("R9 changes no pixel in this mask (the 11 are soft-edge pixels), so the colour is R8's: L* and h inside the lock; C* sits on the "
                    "top edge 12.5 (QA R8 F3: the lock's measurement and precision are the designer's to write)")
    out = dict(before=cnt8, after=cnt9, px_changed=int(ch.sum()), changed_equals_mask=bool(np.array_equal(ch, m)), mask_px=int(m.sum()),
               alpha_same_bytes=bool(np.array_equal(C8[..., 3], C9[..., 3])), dL_max_on_changed=round(float(np.abs(L9_ - L8_)[ch].max()), 4),
               truth_px_changed=int(tch.sum()), truth_changed_only_on_mask=bool(not (tch & ~m).any()), truth_max_level_change=int(np.abs(T8.astype(int) - T9.astype(int)).max()),
               shadow_same_file=v8["shadow"] == v9["shadow"], colour_lock=lock, record_dL_max=fx["dL_max_abs"])
    out["pass_"] = (cnt9["literal_alpha_gt0"]["r8_lab"] == 0 and cnt9["literal_alpha_gt0"]["qa_lab"] == 0 and cnt9["wide_visible_alpha_ge128"]["r8_lab"] == 0
                    and out["changed_equals_mask"] and out["mask_px"] == 11 and out["alpha_same_bytes"] and out["dL_max_on_changed"] <= 0.05
                    and out["truth_changed_only_on_mask"] and out["shadow_same_file"] and lock["truth_changed_in_mask"] == 0
                    and inlock["qa_lab"]["L"] and inlock["qa_lab"]["h"])
    out["summary"] = dict(literal=(cnt8["literal_alpha_gt0"], cnt9["literal_alpha_gt0"]), wide_visible=cnt9["wide_visible_alpha_ge128"],
                          wide_soft=(cnt8["wide_soft_edge_alpha_lt128"], cnt9["wide_soft_edge_alpha_lt128"]), dL=out["dL_max_on_changed"],
                          lock=(lock["qa_lab"], lock["r8_lab"]))
    return out


def records():
    fx = json.load(open(os.path.join(P2, "work-r9", "fix-r9.json")))["r8_record_corrections"]
    fin = np.load(os.path.join(P2, "work-r8", "curtain3-speck-mask-final-pass.npy"))
    spk = np.load(os.path.join(P2, "work-r8", "curtain3-speck-mask.npy"))
    r8 = json.load(open(os.path.join(P2, "work-r8", "fix-r8.json")))["curtain3"]["specks"]["final_pass"]["px"]
    out = dict(final_pass_px=int(fin.sum()), r8_record_final_pass_px=r8, overlap_with_speck_mask=int((fin & spk).sum()),
               alpha_unchanged_correction=fx["alpha_unchanged"]["correct"],
               graded_alpha_px_changed={k: v["graded_alpha_px_changed"] for k, v in fx["alpha_unchanged"]["per_curtain"].items()})
    out["pass_"] = out["final_pass_px"] == r8 == 44 and out["overlap_with_speck_mask"] == 0
    out["summary"] = dict(final_pass=out["final_pass_px"], graded_alpha=out["graded_alpha_px_changed"])
    return out


def lock(man):
    spec = importlib.util.spec_from_file_location("sl", os.path.join(REPO, "qa/reports/2026-11-07-pilot-phase1-g1/tools/shell_lock.py"))
    sl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sl)
    gc = sl.gray(Image.open(sl.CLAY).convert("RGB").resize((1920, 1080), Image.LANCZOS))
    vv = {v["id"]: v for vs in man["variants"].values() for v in vs}
    files = {"default-scene set B (R8 = R9)": os.path.normpath(os.path.join(HERE, man["truths"]["default"]["B"]))}
    files.update({f"variant {k} (R9)": truth_of(vv[k]) for k in ("pendant-v2", "curtains-v3")})
    out = {}
    for name, f in files.items():
        gr = sl.gray(Image.open(f).convert("RGB").resize((1920, 1080), Image.LANCZOS))
        lines = {ln: sl.nearest_peak_line(gc, gr, A, B) for ln, (A, B) in sl.LINES.items()}
        out[name] = dict(pass_=bool(all(v["p90_abs_px"] <= 9.6 and v["paired"] >= 20 for v in lines.values())),
                         worst_p90=max(v["p90_abs_px"] for v in lines.values()), min_paired=min(v["paired"] for v in lines.values()))
    res = dict(per_file=out, rule="every named line p90 <= 9.6 px with >= 20 paired samples (lock_r7.py)")
    res["pass_"] = all(v["pass_"] for v in out.values())
    res["summary"] = {k: (v["pass_"], v["worst_p90"]) for k, v in out.items()}
    return res


def r9_checks(man, m8, per):
    return dict(scope=scope(man, m8), pendant2=pendant2(man, m8, per), curtain3=curtain3(man, m8), records=records(), shell_lock=lock(man))


if __name__ == "__main__":
    main()
