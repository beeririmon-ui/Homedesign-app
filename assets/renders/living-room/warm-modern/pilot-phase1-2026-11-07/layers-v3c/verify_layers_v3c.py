#!/usr/bin/env python3
"""
verify_layers_v3c.py: re-runnable check of the warm-modern tool's v3c layers (render-agent, 2026-11-10; for qa-agent).
Brief: briefs/render-wm-tool-layers-v3c-2026-11-10.md. Reads manifest.json and the files it names; numpy + Pillow only; writes
verify-layers-v3c.json next to it and exits 0 when everything passes, 1 otherwise. Read-only on the approved files.

  python3 verify_layers_v3c.py

Checks:
  1. base.png is the approved shell-furniture-v3-graded-v3c.png: the same bytes (sha256) and the same pixels.
  2. Recompositing: base, then shadow X (multiply), then layer X (source-over, straight alpha), in the manifest's order, against the
     approved composite-set-X-v3-graded-v3c.png. Per pixel, the largest channel difference in 8-bit levels.
       gate: p99.9 <= 2 and max <= 6, for every set and for both pipelines:
         float  one rounding at the end (round half up);
         8bit   browser-like: the multiply rounded to 8 bits, the layer premultiplied and rounded on upload (as the engine's GL path does),
                then source-over rounded.
       p99.9 is taken over the set's region (alpha > 0 or any shadow channel < 255), the strict reading; over the whole canvas it is
       reported too.
  3. Swap-diff (the gate): for every pair of sets, the recomposites differ in 0 pixels outside the union of the two sets' regions, and
     base -> X in 0 pixels outside X's region. Reported too, on the approved composites with these regions: the few pixels that differ
     there must lie inside the approved cut and differ by at most 1 level (bright shadow-band pixels where the grade's shoulder put one
     channel 1 level above the base; a multiply cannot brighten, so they are not in the shadow layer).
  4. The regions stay inside the approved cut (approved layer alpha > 0 or approved shadow < 255), the files have the manifest's size and
     mode, the default set is B, and every product's card exists with its id.
"""
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
TOL_P999, TOL_MAX = 2.0, 6.0


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def img(p):
    im = Image.open(p)
    return im.mode, im.size, np.asarray(im).astype(np.float64)


def rhu(x):
    return np.floor(x + 0.5)


def stats(out, T, region):
    d = np.abs(out - T)
    dp = d.max(2)
    yx = np.unravel_index(int(np.argmax(dp)), dp.shape)
    return dict(max=float(dp.max()), max_at_px=[int(yx[1]), int(yx[0])],
                p99_9_region=round(float(np.percentile(dp[region], 99.9)), 3),
                p99_region=round(float(np.percentile(dp[region], 99)), 3),
                p99_9_canvas=round(float(np.percentile(dp, 99.9)), 3),
                p99_9_canvas_per_channel=round(float(np.percentile(d, 99.9)), 3),
                px_gt0=int((dp > 0).sum()), px_gt1=int((dp > 1).sum()), px_gt2=int((dp > 2).sum()), px_gt6=int((dp > 6).sum()),
                region_px=int(region.sum()))


def main():
    man = json.load(open(os.path.join(HERE, "manifest.json")))
    W, H = man["size"]["width"], man["size"]["height"]
    res = dict(manifest=os.path.relpath(os.path.join(HERE, "manifest.json"), REPO), tolerance=dict(p99_9=TOL_P999, max=TOL_MAX), checks={})
    fails = []

    # 1. the base
    bl = next(x for x in man["layers"] if x["id"] == "base")
    bp, ap = os.path.join(HERE, bl["file"]), os.path.join(REPO, bl["source"])
    mb, sb, B = img(bp)
    _, _, BA = img(ap)
    B, BA = B[..., :3], BA[..., :3]
    base = dict(file=bl["file"], source=bl["source"], same_bytes=sha256(bp) == sha256(ap), sha256=sha256(bp),
                sha256_matches_manifest=sha256(bp) == bl.get("sha256"), same_pixels=bool(np.array_equal(B, BA)), mode=mb, size=list(sb))
    res["checks"]["base"] = base
    if not (base["same_bytes"] and base["same_pixels"] and list(sb) == [W, H]):
        fails.append("base")

    # 2. recompositing
    order = man["compose"]["order"]
    if order != ["base", "cushions-shadow", "cushions"]:
        fails.append("order")
    blends = {x["id"]: x["blend"] for x in man["layers"]}
    if blends != {"base": "normal", "cushions-shadow": "multiply", "cushions": "normal"}:
        fails.append("blends")
    R, REG, T, CUT = {}, {}, {}, {}
    rec = {}
    for s, st in man["sets"].items():
        ml, sl, L = img(os.path.join(HERE, st["layer"]))
        ms, ss, S = img(os.path.join(HERE, st["shadow"]))
        tp = os.path.join(REPO, st["source"]["approved_composite"])
        _, _, Tc = img(tp)
        Tc = Tc[..., :3]
        a = L[..., 3:4] / 255.0
        region = (L[..., 3] > 0) | (S < 255).any(2)
        # float: one rounding at the end
        out_f = rhu((B * S / 255.0) * (1 - a) + L[..., :3] * a)
        # 8bit: the multiply rounded, the layer premultiplied on upload, source-over rounded
        Bm = rhu(B * S / 255.0)
        Lp = rhu(L[..., :3] * a)
        out_8 = rhu(Lp + Bm * (1 - a))
        sf, s8 = stats(out_f, Tc, region), stats(out_8, Tc, region)
        # 4. the region inside the approved cut
        a0 = np.asarray(Image.open(os.path.join(REPO, st["source"]["alpha_from"])))[..., 3] > 0
        s0 = np.asarray(Image.open(os.path.join(REPO, st["source"]["shadow_band_from"])).convert("RGB")).min(2) < 255
        cards = []
        for p in st["products"]:
            cp = os.path.join(REPO, p["card"])
            cards.append(bool(os.path.exists(cp) and json.load(open(cp)).get("id") == p["card_id"]))
        r = dict(layer=dict(file=st["layer"], mode=ml, size=list(sl)), shadow=dict(file=st["shadow"], mode=ms, size=list(ss)),
                 approved_composite=st["source"]["approved_composite"],
                 approved_composite_sha256_matches_manifest=sha256(tp) == st["source"].get("approved_composite_sha256"),
                 recomposite_float=sf, recomposite_8bit=s8,
                 region_px=int(region.sum()), region_outside_approved_cut_px=int((region & ~(a0 | s0)).sum()),
                 cards_ok=all(cards), n_products=len(cards))
        ok = (ml == "RGBA" and ms == "RGB" and list(sl) == [W, H] and list(ss) == [W, H]
              and all(x["p99_9_region"] <= TOL_P999 and x["max"] <= TOL_MAX for x in (sf, s8))
              and r["region_outside_approved_cut_px"] == 0 and r["cards_ok"] and r["approved_composite_sha256_matches_manifest"])
        r["pass"] = bool(ok)
        if not ok:
            fails.append(f"set {s}")
        rec[s] = r
        R[s], REG[s], T[s], CUT[s] = out_f, region, Tc, a0 | s0
    res["checks"]["recomposite"] = rec

    # 3. swap-diff
    sw = {}
    sets = list(man["sets"])

    def approved(X, Y, u, cut):
        d = np.abs(X - Y).max(2)
        o = (d > 0) & ~u
        return dict(approved_outside=int(o.sum()), approved_outside_max_level=float(d[o].max()) if o.any() else 0.0,
                    approved_outside_not_in_approved_cut=int((o & ~cut).sum()))

    for s in sets:
        sw[f"base->{s}"] = dict(recomposite_outside=int(((R[s] != B).any(2) & ~REG[s]).sum()), **approved(T[s], B, REG[s], CUT[s]))
    for i, s in enumerate(sets):
        for t in sets[i + 1:]:
            u = REG[s] | REG[t]
            dr = (R[s] != R[t]).any(2)
            sw[f"{s}<->{t}"] = dict(recomposite_changed_px=int(dr.sum()), recomposite_outside=int((dr & ~u).sum()), union_px=int(u.sum()),
                                    approved_changed_px=int((T[s] != T[t]).any(2).sum()), **approved(T[s], T[t], u, CUT[s] | CUT[t]))
    res["checks"]["swap_diff"] = sw
    if any(v["recomposite_outside"] for v in sw.values()):
        fails.append("swap-diff")
    if any(v["approved_outside_max_level"] > 1 or v["approved_outside_not_in_approved_cut"] for v in sw.values()):
        fails.append("approved composites outside the regions")

    # default
    res["checks"]["default"] = man["slot"]["default"]
    sel = json.load(open(os.path.join(REPO, "data/selections/living-room.warm-modern.json")))["slots"]["cushions"]["picks"]
    if man["slot"]["default"] != "B" or sel[0]["set_id"] != "B":
        fails.append("default")

    res["pass"] = not fails
    res["fails"] = fails
    json.dump(res, open(os.path.join(HERE, "verify-layers-v3c.json"), "w"), indent=1)
    for s, r in rec.items():
        f, e = r["recomposite_float"], r["recomposite_8bit"]
        print(f"set {s}: float p99.9 {f['p99_9_region']} max {f['max']:.0f} (>2: {f['px_gt2']} px) | 8bit p99.9 {e['p99_9_region']} "
              f"max {e['max']:.0f} (>2: {e['px_gt2']} px) | region {r['region_px']} px | {'pass' if r['pass'] else 'FAIL'}")
    print("swap-diff outside the regions (recomposite px | approved px, max level):",
          {k: (v["recomposite_outside"], v["approved_outside"], v["approved_outside_max_level"]) for k, v in sw.items()})
    print("base identical:", base["same_bytes"] and base["same_pixels"], "| default:", man["slot"]["default"], "|", "PASS" if not fails else f"FAIL {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
