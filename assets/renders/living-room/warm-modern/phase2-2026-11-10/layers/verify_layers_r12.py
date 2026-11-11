#!/usr/bin/env python3
"""
verify_layers_r12.py: re-runnable check of the warm-modern tool's phase-2 layers after the reserve passes R1 / R2 (render-agent, 2026-11-11;
for qa-agent; verify_layers.py of steps 1-3 with the r12 manifest and composites). Reads manifest-r12.json and the files it names (numpy + Pillow only); writes verify-layers-r12.json next to it; exit 0 = every check passes.
Read-only on everything else.

  python3 verify_layers_r12.py

Checks
  1. base.png is the approved layers-v3c/base.png (same bytes).
  2. Recomposite: base, then for each product in the manifest's order its shadow (multiply) and its layer (source-over, straight alpha),
     with cushion set X, against graded/default-scene-r12-set-X-graded-v3c.png, for X = B (the default), A, C. Per pixel the largest
     channel difference in 8-bit levels; gate p99.9 <= 2 and max <= 6 over the union of the regions, for two pipelines:
       float  one rounding at the end;   8bit  browser-like: multiply rounded to 8 bits, the layer premultiplied and rounded, then over.
  3. Swap-diff per layer (rule ו.5): composing the stack with and without each product changes 0 px outside that product's region
     (alpha > 0 or any shadow channel < 255); set B <-> A <-> C changes 0 px outside the union of the two sets' regions.
  4. Regions are tight: no alpha and no shadow pixel farther than 60 px from the product's own alpha (a product never darkens or covers
     another part of the room).
  5. The cushion sets keep the approved v3c pixels wherever the stack under them did not change (counted), files have the manifest's
     size and mode, every product card exists with its id, and the approved phase-1 files are unchanged in git.
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


def main():
    man = json.load(open(os.path.join(HERE, "manifest-r12.json")))
    rep = dict(manifest=os.path.relpath(os.path.join(HERE, "manifest-r12.json"), REPO), tolerance=dict(p99_9=TOL_P999, max=TOL_MAX), checks={})
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
        _, _, T = load(os.path.join(P2, f"graded/default-scene-r12-set-{s}-graded-v3c.png"))
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
    rep["fails"] = fails
    rep["pass"] = not fails
    json.dump(rep, open(os.path.join(HERE, "verify-layers-r12.json"), "w"), indent=1)
    print(json.dumps(dict(recomposite={s: {p: (v[p]["p99_9_region"], v[p]["max"]) for p in v} for s, v in rec.items()},
                          swap={k: v.get("changed_outside_region", v.get("changed_outside_union")) for k, v in sw.items()},
                          cushions_kept=kept, fails=fails), indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
