#!/usr/bin/env python3
"""
scan_edge_bleed.py: a room-agnostic scan for carried background and false shadows in a layer manifest (render-agent, 2026-11-25,
brief briefs/wm-living-fix-cushion-basket-2026-11-25.md, task 4; for qa-agent: run it on every room's manifest).

    python3.12 -I -B scan_edge_bleed.py [manifest.json] [--sets B,A,C] [--no-variants] [--out scan.json]

The manifest is the tool's layer manifest (layers[] with id / file / blend / z, compose.order, optional slot_cushions.sets and variants);
the 8-bit stack is the manifest's own formula: o = round(round(rgb a) + round(o S / 255) (1 - a)), base first.

Two checks per product layer (each default; each cushion set; each variant at its slot's z, on the same stack below):
  EDGE    carried background: a band 1-8 px just inside the alpha edge is compared with the plate under it (the stack below the
          layer, before its own shadow). A pixel is "carried" when it is opaque (alpha >= 0.9: soft edge pixels are mixed by design),
          looks like background and not like the product (its Lab distance to the plate just outside the edge, 3-10 px out, is under
          half its distance to the product's own colour 10-20 px in), and differs from the plate under it by a visible step
          (dE76 >= 6). Each connected patch (8-connected, >= 20 px) is one row: px, bbox, the mean dL* and dhue (degrees,
          chroma-weighted) of the step, and a score = the sum of dE over its px.
  SHADOW  false shadow: a multiply shadow that stays dark far from its product. Darkening (1 - S) >= 0.15 farther than
          max(12, 0.06 sqrt(area)) px from the product's alpha and outside the convex hull of each of its parts (the shadow under a
          table top, between its legs, is the table's own), or >= 0.45 anywhere outside the product. A contact shadow in this soft
          light fades within that distance; a flat dark field far out is a carried relighting. One row per patch (>= 40 px): px,
          bbox, the mean and max darkening, and a score = the sum of the darkening x 100.

Visibility (EFF1.3): a patch is "x1-x2" when it has >= 80 canvas px and a mean step >= 8 dE (EDGE) or a mean darkening >= 0.18
(SHADOW); otherwise "low" (to status/backlog-low.md). Rows are sorted worst first by score.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def arr(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def rhu(x):
    return np.floor(x + 0.5)


def lab(rgb8):
    return cv2.cvtColor(rgb8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


def nblur(x, w, s):
    """normalised Gaussian blur of x over the weight w"""
    if x.ndim == 3:
        num = np.stack([cv2.GaussianBlur((x[..., i] * w).astype(np.float32), (0, 0), s) for i in range(x.shape[2])], -1)
    else:
        num = cv2.GaussianBlur((x * w).astype(np.float32), (0, 0), s)
    den = cv2.GaussianBlur(w.astype(np.float32), (0, 0), s)
    return num / np.maximum(den[..., None] if x.ndim == 3 else den, 1e-6), den


def patches(m, min_px):
    """the 8-connected patches of m with >= min_px px: (mask, px, bbox)"""
    if not m.any():
        return []
    n, lab_, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a >= min_px:
            out.append((lab_ == i, int(a), [int(x), int(y), int(x + w - 1), int(y + h - 1)]))
    return out


def edge_check(L, below):
    a = L[..., 3].astype(np.float32) / 255.0
    inside = a >= 0.5
    if inside.sum() < 50:
        return []
    din = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    dout = cv2.distanceTransform((~inside).astype(np.uint8), cv2.DIST_L2, 5)
    band = inside & (din <= 8)
    core = inside & (din >= 10) & (din <= 20)
    if not core.any():
        core = inside & (din >= 3)
    ring = (~inside) & (dout >= 3) & (dout <= 10)
    x0, y0 = np.min(np.nonzero(inside.any(0))), np.min(np.nonzero(inside.any(1)))
    x1, y1 = np.max(np.nonzero(inside.any(0))), np.max(np.nonzero(inside.any(1)))
    pad = 40
    sl = (slice(max(0, y0 - pad), y1 + pad + 1), slice(max(0, x0 - pad), x1 + pad + 1))
    Ll, Lb = lab(L[..., :3][sl]), lab(below[sl])
    F, wF = nblur(Ll, core[sl].astype(np.float32), 6.0)
    B, wB = nblur(Lb, ring[sl].astype(np.float32), 6.0)
    dF = np.linalg.norm(Ll - F, axis=2)
    dB = np.linalg.norm(Ll - B, axis=2)
    step = np.linalg.norm(Ll - Lb, axis=2)
    carried = band[sl] & (a[sl] >= 0.9) & (wF > 1e-3) & (wB > 1e-3) & (dB < 0.5 * dF) & (step >= 6.0)
    C1, C2 = np.hypot(Ll[..., 1], Ll[..., 2]), np.hypot(Lb[..., 1], Lb[..., 2])
    h1, h2 = np.degrees(np.arctan2(Ll[..., 2], Ll[..., 1])), np.degrees(np.arctan2(Lb[..., 2], Lb[..., 1]))
    dh = np.abs((h1 - h2 + 180) % 360 - 180)
    wC = np.minimum(C1, C2)
    rows = []
    for m, px, bb in patches(carried, 20):
        bb = [int(bb[0] + sl[1].start), int(bb[1] + sl[0].start), int(bb[2] + sl[1].start), int(bb[3] + sl[0].start)]
        rows.append(dict(px=px, bbox=bb, dL_mean=round(float((Ll[..., 0] - Lb[..., 0])[m].mean()), 2),
                         dhue_mean_deg=round(float((dh * wC)[m].sum() / max(wC[m].sum(), 1e-6)), 1),
                         dE_mean=round(float(step[m].mean()), 2), score=round(float(step[m].sum()), 1)))
    return rows


def shadow_check(L, S):
    a = L[..., 3].astype(np.float32) / 255.0
    d = 1.0 - S.astype(np.float32).mean(2) / 255.0
    prod = a > 0.02
    if not prod.any():
        return []
    dist = cv2.distanceTransform((~prod).astype(np.uint8), cv2.DIST_L2, 5)
    hull = np.zeros(prod.shape, np.uint8)
    for m, px, bb in patches(prod, 30):
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.fillPoly(hull, [cv2.convexHull(np.concatenate(cnts))], 1)
    far = max(12.0, 0.06 * float(np.sqrt(prod.sum())))
    bad = ((d >= 0.15) & (dist > far) & (hull == 0)) | ((d >= 0.45) & ~prod)
    return [dict(px=px, bbox=bb, dark_mean=round(float(d[m].mean()), 3), dark_max=round(float(d[m].max()), 3),
                 score=round(float(d[m].sum() * 100), 1)) for m, px, bb in patches(bad, 40)]


def visible(kind, r):
    if kind == "EDGE":
        return "x1-x2" if r["px"] >= 80 and r["dE_mean"] >= 8 else "low"
    return "x1-x2" if r["px"] >= 80 and r["dark_mean"] >= 0.18 else "low"


def scan(man_path, sets=None, variants=True):
    mdir = os.path.dirname(os.path.abspath(man_path))
    man = json.load(open(man_path))
    by = {l_["id"]: l_ for l_ in man["layers"]}
    order = man.get("compose", {}).get("order") or [l_["id"] for l_ in sorted(man["layers"], key=lambda l_: l_["z"])]
    P = lambda f: os.path.normpath(os.path.join(mdir, f))  # noqa: E731
    cs = man.get("slot_cushions", {}).get("sets", {})
    sets = sets or (man.get("slot_cushions", {}).get("order") or ["-"])
    rows = []
    for si, st in enumerate(sets):
        o = arr(P(by["base"]["file"]), "RGB").astype(np.float64)
        for k in order:
            if k == "base" or k.endswith("-shadow"):
                continue
            if k == "cushions":
                if st not in cs:
                    continue
                lf, sf = P(cs[st]["layer"]), P(cs[st]["shadow"])
            else:
                sh = by.get(k + "-shadow")
                lf, sf = P(by[k]["file"]), P(sh["file"]) if sh else None
            only_cushions = si > 0 and k != "cushions"
            L = arr(lf)
            S = arr(sf, "RGB") if sf else np.full(L.shape[:2] + (3,), 255, np.uint8)
            below = o.astype(np.uint8)
            cand = [(k if k != "cushions" else f"cushions set {st}", L, S, os.path.relpath(lf, mdir))]
            if variants and not only_cushions and k != "cushions":
                for v in man.get("variants", {}).get(k, []):
                    if v.get("file") and v.get("shadow"):
                        cand.append((v["id"], arr(P(v["file"])), arr(P(v["shadow"]), "RGB"), v["file"]))
            if not only_cushions or k == "cushions":
                for name, Lx, Sx, f in cand:
                    for kind, rs in (("EDGE", edge_check(Lx, below)), ("SHADOW", shadow_check(Lx, Sx))):
                        for r in rs:
                            rows.append(dict(layer=name, file=f, check=kind, visibility=visible(kind, r), **r))
            Lf, Sf = L.astype(np.float64), S.astype(np.float64)
            a = Lf[..., 3:4] / 255.0
            o = rhu(rhu(Lf[..., :3] * a) + rhu(o * Sf / 255.0) * (1 - a))
    rows.sort(key=lambda r: -r["score"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", nargs="?", default=os.path.join(HERE, "manifest-fb12s1.json"))
    ap.add_argument("--sets", default=None)
    ap.add_argument("--no-variants", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = scan(a.manifest, a.sets.split(",") if a.sets else None, not a.no_variants)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.manifest)),
                                "scan-edge-bleed-" + os.path.basename(a.manifest).replace("manifest-", "").replace(".json", "") + ".json")
    json.dump(dict(manifest=os.path.basename(a.manifest), method=__doc__.strip().split("\n\n")[2], rows=rows), open(out, "w"), indent=1)
    for r in rows:
        print(f"{r['score']:9.1f}  {r['visibility']:6s} {r['check']:6s} {r['layer']:28s} px {r['px']:6d} {r['bbox']} "
              f"{'dE %.1f dL %.1f dh %.0f' % (r['dE_mean'], r['dL_mean'], r['dhue_mean_deg']) if r['check'] == 'EDGE' else 'dark %.2f max %.2f' % (r['dark_mean'], r['dark_max'])}")
    print("->", out)


if __name__ == "__main__":
    main()
