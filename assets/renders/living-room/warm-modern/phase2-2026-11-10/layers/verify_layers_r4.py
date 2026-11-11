#!/usr/bin/env python3
"""
verify_layers_r4.py: re-runnable check of the warm-modern tool's phase-2 layers after the code fixes R4, all 12 defaults (render-agent, 2026-11-11;
for qa-agent; verify_layers_r3.py with the r4 manifest and composites, plus checks 6-8). Reads manifest-r4.json and the files it names
(numpy + Pillow only); writes verify-layers-r4.json next to it; exit 0 = every check passes. Read-only on everything else.

  python3 verify_layers_r4.py

Checks
  1. base.png is the approved layers-v3c/base.png (same bytes).
  2. Recomposite: base, then for each product in the manifest's order its shadow (multiply) and its layer (source-over, straight alpha),
     with cushion set X, against graded/default-scene-r4-set-X-graded-v3c.png, for X = B (the default), A, C. Per pixel the largest
     channel difference in 8-bit levels; gate p99.9 <= 2 and max <= 6 over the union of the regions, for two pipelines:
       float  one rounding at the end;   8bit  browser-like: multiply rounded to 8 bits, the layer premultiplied and rounded, then over.
  3. Swap-diff per layer (rule ו.5): composing the stack with and without each product changes 0 px outside that product's region
     (alpha > 0 or any shadow channel < 255); set B <-> A <-> C changes 0 px outside the union of the two sets' regions.
  4. Regions are tight: no alpha and no shadow pixel farther than 60 px from the product's own alpha (a product never darkens or covers
     another part of the room).
  5. The cushion sets keep the approved v3c pixels wherever the stack under them did not change (counted), files have the manifest's
     size and mode, every product card exists with its id, and the approved phase-1 files are unchanged in git.
  6. R4 changed only its five products: every other layer, shadow and cushion set is the same file (same bytes) as in manifest-r3.json;
     and outside the five products' r3 + r4 regions the r4 scenes equal the r3 scenes byte for byte (sets B, A, C).
  7. ONE v3c grade on the five changed layers (QA's method, qa/reports/2026-11-11-wm-tool-phase2-checkpoint/tools/p2_grade.py, in numpy):
     the curve dL*(L*_ungraded) learned on the approved pair (phase 1 shell-furniture-v3.png -> base.png, off the bench slab), then on
     each layer's interior (alpha 255 eroded 2 px, under no later layer) the residual (L_layer - L_source) - curve(L_source) against its
     ungraded source in ../work-r4/layers; gate |median| <= 0.5 and, where >= 20 px sit in the toe (L < 25), |toe median| <= 1.
  8. The vase layer carries the flag fix_status "size fixed; placement pending the designer" (and no "status" key, which marks a pending,
     unused layer for this script and for the engine).
"""
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
P2 = os.path.dirname(HERE)
P1 = os.path.join(REPO, "assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07")
TOL_P999, TOL_MAX = 2.0, 6.0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load(p):
    im = Image.open(p)
    return im.mode, im.size, np.asarray(im).astype(np.float64)


def rhu(x):
    return np.floor(x + 0.5)


def stack_layers(man, s):
    out = []
    for l_ in man["layers"]:
        if l_.get("status") or l_["id"] == "base" or l_["id"].endswith("-shadow"):
            continue
        if l_["id"] == "cushions":
            st = man["slot_cushions"]["sets"][s]
            out.append(("cushions", st["layer"], st["shadow"]))
        else:
            sh = next(x for x in man["layers"] if x["id"] == l_["id"] + "-shadow")
            out.append((l_["id"], l_["file"], sh["file"]))
    return out


def compose(base, layers, pipe, skip=None):
    o = base.copy()
    for k, lf, sf in layers:
        if k == skip:
            continue
        _, _, L = load(os.path.join(HERE, lf))
        _, _, S = load(os.path.join(HERE, sf))
        a = L[..., 3:4] / 255.0
        if pipe == "float":
            o = (o * S / 255.0) * (1 - a) + L[..., :3] * a
        else:
            m = rhu(o * S / 255.0)
            pre = rhu(L[..., :3] * a)
            o = rhu(pre + m * (1 - a))
    return o


def region_of(lf, sf):
    _, _, L = load(os.path.join(HERE, lf))
    _, _, S = load(os.path.join(HERE, sf))
    return (L[..., 3] > 0) | (S < 255).any(2), L[..., 3] > 0


def stats(o, T, region):
    d = np.abs(rhu(o) - T).max(2)
    yx = np.unravel_index(int(np.argmax(d)), d.shape)
    return dict(max=float(d.max()), max_at_px=[int(yx[1]), int(yx[0])], p99_9_region=float(np.percentile(d[region], 99.9)) if region.any() else 0.0,
                p99_9_canvas=float(np.percentile(d, 99.9)), px_gt0=int((d > 0).sum()), px_gt2=int((d > 2).sum()), px_gt6=int((d > 6).sum()))


def lab_L(rgb01):
    """L* of sRGB values 0-1 (D65), as OpenCV's float RGB2LAB"""
    c = np.where(rgb01 <= 0.04045, rgb01 / 12.92, ((rgb01 + 0.055) / 1.055) ** 2.4)
    Y = c[..., 0] * 0.212671 + c[..., 1] * 0.715160 + c[..., 2] * 0.072169
    return np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)


def erode(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out &= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def grade_check(man):
    u = np.asarray(Image.open(os.path.join(P1, "shell-furniture-v3.png")).convert("RGB")).astype(np.float64) / 255
    g = np.asarray(Image.open(os.path.join(HERE, "base.png")).convert("RGB")).astype(np.float64) / 255
    stone = np.asarray(Image.open(os.path.join(P1, "masks/stone-wide.png")).convert("L")) > 127
    Lu, Lg = lab_L(u)[~stone], lab_L(g)[~stone]
    bins = np.arange(0, 100.25, 0.25)
    idx = np.clip(np.digitize(Lu, bins) - 1, 0, len(bins) - 2)
    dL = Lg - Lu
    cnt = np.bincount(idx, minlength=len(bins) - 1)
    curve = np.full(len(bins) - 1, np.nan)
    order = np.argsort(idx, kind="stable")
    splits = np.split(dL[order], np.cumsum(cnt)[:-1])
    for i, sv in enumerate(splits):
        if sv.size >= 20:
            curve[i] = np.median(sv)
    xc = (bins[:-1] + bins[1:]) / 2
    ok = ~np.isnan(curve)
    cf = np.interp(xc, xc[ok], curve[ok])
    byid = {l_["id"]: l_ for l_ in man["layers"]}
    alph = {k: np.asarray(Image.open(os.path.join(HERE, l_["file"])))[..., 3] for k, l_ in byid.items() if "product" in l_}
    out = {}
    for k in man["changed_in_r4"]["products"]:
        src = np.asarray(Image.open(os.path.join(P2, "work-r4/layers", f"{k}.png"))).astype(np.float64) / 255
        lay = np.asarray(Image.open(os.path.join(HERE, byid[k]["file"]))).astype(np.float64) / 255
        inner = erode(alph[k] == 255, 2) & (src[..., 3] >= 1.0)
        for o, a in alph.items():
            if o != k and byid[o]["z"] > byid[k]["z"]:
                inner &= a == 0
        for s in "ABC":
            inner &= np.asarray(Image.open(os.path.join(HERE, man["slot_cushions"]["sets"][s]["layer"])))[..., 3] == 0
        Ls, Ll = lab_L(src[..., :3])[inner], lab_L(lay[..., :3])[inner]
        r = (Ll - Ls) - np.interp(Ls, xc, cf)
        rec = dict(px=int(inner.sum()), residual_median=round(float(np.median(r)), 3), residual_p95_abs=round(float(np.percentile(np.abs(r), 95)), 3))
        toe = Ls < 25
        if toe.sum() >= 20:
            rec.update(toe_px=int(toe.sum()), toe_expected_lift_median=round(float(np.median(np.interp(Ls[toe], xc, cf))), 2),
                       toe_observed_lift_median=round(float(np.median((Ll - Ls)[toe])), 2), toe_residual_median=round(float(np.median(r[toe])), 3))
        rec["pass_"] = bool(abs(rec["residual_median"]) <= 0.5 and abs(rec.get("toe_residual_median", 0.0)) <= 1.0)
        out[k] = rec
    return dict(curve_samples={f"{x:.0f}": round(float(np.interp(x, xc, cf)), 3) for x in (8, 12, 20, 25, 50, 88, 92, 95, 98)}, products=out,
                rule="one grade if |residual median| <= 0.5 and the toe residual within +-1 (a second toe adds ~+3 to +6 at L 8-12; a missing one -3 to -6)")


def main():
    man = json.load(open(os.path.join(HERE, "manifest-r4.json")))
    rep = dict(manifest=os.path.relpath(os.path.join(HERE, "manifest-r4.json"), REPO), tolerance=dict(p99_9=TOL_P999, max=TOL_MAX), checks={})
    fails = []
    # 1
    b_ok = sha(os.path.join(HERE, "base.png")) == sha(os.path.join(P1, "layers-v3c/base.png"))
    rep["checks"]["base_same_bytes_as_v3c"] = b_ok
    if not b_ok:
        fails.append("base")
    _, size, base = load(os.path.join(HERE, "base.png"))
    # 2 + 3
    rec = {}
    for s in "BAC":
        layers = stack_layers(man, s)
        _, _, T = load(os.path.join(P2, f"graded/default-scene-r4-set-{s}-graded-v3c.png"))
        union = np.zeros(base.shape[:2], bool)
        for k, lf, sf in layers:
            union |= region_of(lf, sf)[0]
        r = dict(float=stats(compose(base, layers, "float"), T, union), bit8=stats(compose(base, layers, "8bit"), T, union))
        for p in ("float", "bit8"):
            if r[p]["p99_9_region"] > TOL_P999 or r[p]["max"] > TOL_MAX:
                fails.append(f"recomposite set {s} {p}")
        rec[s] = r
    rep["checks"]["recomposite"] = rec
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
        # 4 tightness
        if alpha.any():
            ys, xs = np.nonzero(alpha)
            ry, rx = np.nonzero(reg)
            far = int(((ry < ys.min() - 60) | (ry > ys.max() + 60) | (rx < xs.min() - 60) | (rx > xs.max() + 60)).sum())
            sw[k]["region_px_beyond_60px_of_its_alpha_box"] = far
            if far:
                fails.append(f"region {k}")
    comps = {s: compose(base, stack_layers(man, s), "float") for s in "BAC"}
    regs = {s: region_of(man["slot_cushions"]["sets"][s]["layer"], man["slot_cushions"]["sets"][s]["shadow"])[0] for s in "BAC"}
    for a_, b_ in (("A", "B"), ("A", "C"), ("B", "C")):
        d = np.abs(rhu(comps[a_]) - rhu(comps[b_])).max(2) > 0
        sw[f"cushions {a_}<->{b_}"] = dict(changed_px=int(d.sum()), changed_outside_union=int((d & ~(regs[a_] | regs[b_])).sum()))
        if sw[f"cushions {a_}<->{b_}"]["changed_outside_union"]:
            fails.append(f"swap cushions {a_}{b_}")
    rep["checks"]["swap_diff"] = sw
    # 5
    kept = {}
    for s in "BAC":
        st = man["slot_cushions"]["sets"][s]
        _, _, Ln = load(os.path.join(HERE, st["layer"]))
        _, _, La = load(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png"))
        _, _, Sn = load(os.path.join(HERE, st["shadow"]))
        _, _, Sa = load(os.path.join(P1, f"layers-v3c/cushions-set-{s}-shadow.png"))
        same = (Ln == La).all(2) & (Sn == Sa).all(2)
        reg = regs[s]
        kept[s] = dict(region_px=int(reg.sum()), same_as_approved_px=int((same & reg).sum()), recut_px=int((~same & reg).sum()),
                       manifest_recut_px=st["recut_on_new_stack_px"])
    rep["checks"]["cushions_kept_from_v3c"] = kept
    io = {}
    for l_ in man["layers"]:
        if "file" not in l_:
            continue
        mode, sz, _ = load(os.path.join(HERE, l_["file"]))
        io[l_["file"]] = dict(mode=mode, size=list(sz), ok=list(sz) == list(size) and mode in ("RGB", "RGBA"))
        if not io[l_["file"]]["ok"]:
            fails.append(f"file {l_['file']}")
        if "product" in l_:
            c = json.load(open(os.path.join(REPO, l_["product"]["card"])))
            skus = [k["id"] for k in ((c.get("options") or {}).get("skus") or [])]
            # a single-variant card without options.skus names its SKU in the notes (e.g. the pendant)
            io[l_["file"]]["card_ok"] = c["id"] == l_["product"]["card_id"] and (l_["product"]["sku"] in skus or l_["product"]["sku"] in str(c.get("notes", "")))
            if not io[l_["file"]]["card_ok"]:
                fails.append(f"card {l_['id']}")
    rep["checks"]["files"] = io
    g = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", os.path.relpath(P1, REPO)], capture_output=True, text=True)
    rep["checks"]["phase1_unchanged_in_git"] = dict(porcelain=g.stdout.strip().splitlines(), ok=g.returncode == 0 and not g.stdout.strip())
    if not rep["checks"]["phase1_unchanged_in_git"]["ok"]:
        fails.append("phase 1 changed")
    # 6 only the five products changed
    r3 = json.load(open(os.path.join(HERE, "manifest-r3.json")))
    r3f = {l_["id"]: l_["file"] for l_ in r3["layers"] if "file" in l_}
    fix = man["changed_in_r4"]["products"]
    same = {}
    for l_ in man["layers"]:
        if "file" not in l_ or l_.get("slot") in fix:
            continue
        same[l_["id"]] = sha(os.path.join(HERE, l_["file"])) == sha(os.path.join(HERE, r3f[l_["id"]]))
    for s in "BAC":
        for kind in ("layer", "shadow"):
            same[f"cushions {s} {kind}"] = sha(os.path.join(HERE, man["slot_cushions"]["sets"][s][kind])) == sha(os.path.join(HERE, r3["slot_cushions"]["sets"][s][kind]))
    for k, v in same.items():
        if not v:
            fails.append(f"r4 changed {k}")
    union = np.zeros(base.shape[:2], bool)
    for k in fix:
        l4 = next(x for x in man["layers"] if x["id"] == k)
        s4 = next(x for x in man["layers"] if x["id"] == k + "-shadow")
        l3 = next(x for x in r3["layers"] if x["id"] == k)
        s3 = next(x for x in r3["layers"] if x["id"] == k + "-shadow")
        union |= region_of(l4["file"], s4["file"])[0] | region_of(l3["file"], s3["file"])[0]
    outside = {}
    for s in "BAC":
        _, _, T4 = load(os.path.join(P2, f"graded/default-scene-r4-set-{s}-graded-v3c.png"))
        _, _, T3 = load(os.path.join(P2, f"graded/default-scene-r3-set-{s}-graded-v3c.png"))
        d = np.abs(T4 - T3).max(2) > 0
        outside[s] = dict(changed_px=int(d.sum()), changed_outside_the_five_regions=int((d & ~union).sum()), five_regions_px=int(union.sum()))
        if outside[s]["changed_outside_the_five_regions"]:
            fails.append(f"r4 scene {s} changed outside the five products")
    rep["checks"]["r4_only_five_products"] = dict(same_file_as_r3=same, scenes_vs_r3=outside)
    # 7 one grade
    rep["checks"]["one_v3c_grade"] = gr = grade_check(man)
    for k, v in gr["products"].items():
        if not v["pass_"]:
            fails.append(f"grade {k}")
    # 8 the vase's flag
    vl = next(x for x in man["layers"] if x["id"] == "vase")
    rep["checks"]["vase_flag"] = dict(fix_status=vl.get("fix_status"), no_pending_status_key="status" not in vl,
                                      ok=vl.get("fix_status") == "size fixed; placement pending the designer" and "status" not in vl)
    if not rep["checks"]["vase_flag"]["ok"]:
        fails.append("vase flag")
    rep["fails"] = fails
    rep["pass"] = not fails
    json.dump(rep, open(os.path.join(HERE, "verify-layers-r4.json"), "w"), indent=1)
    print(json.dumps(dict(recomposite={s: {p: (v[p]["p99_9_region"], v[p]["max"]) for p in v} for s, v in rec.items()},
                          swap={k: v.get("changed_outside_region", v.get("changed_outside_union")) for k, v in sw.items()},
                          cushions_kept=kept, r4_scenes_vs_r3=outside, unchanged_files=all(same.values()),
                          grade={k: (v["residual_median"], v.get("toe_residual_median")) for k, v in gr["products"].items()},
                          vase_flag=rep["checks"]["vase_flag"]["ok"], fails=fails), indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
