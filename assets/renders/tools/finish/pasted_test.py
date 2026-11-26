#!/usr/bin/env python3
"""
pasted_test.py: the "pasted" test of FB13 (render-agent, 2026-11-25; docs/proposals/wm-fb13-living-wow-2026-11-25.md 3.2 item 10).
0 var2 tokens. It EXTENDS assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/scan_edge_bleed.py (imported by path, not
edited: its EDGE and SHADOW checks run unchanged) with the checks of the proposal, for every product layer of a room's default stack:

  check      what                                                                          pass
  EDGE       carried background inside the alpha edge (scan_edge_bleed.edge_check)          no row visible at x1-x2
  SHADOW     a multiply shadow dark far from its product (scan_edge_bleed.shadow_check)     no row visible at x1-x2
  SHARP      edge spread of the layer's silhouette on the composite vs the plate's own     s_plate / s_layer in 0.85-1.15
             edges in a ring 15-120 px round it (sigma of a blurred step)                  (> 1.15: the layer is sharper, a cut-out)
  GRAIN      noise of the layer's flat interior vs the plate's flat ring (MAD of L - blur)  ratio 0.80-1.25
  LIGHT      the lit side: the plane fitted to the low-passed L* of the product's interior   <= 25 deg from the direction to the room's
             (standing objects only; prints, textiles and flat items carry albedo)           dominant light (its brightest 1.5 %)
  CONTACT    darkening within 2 cm under the contact line vs 6-12 cm away, same columns     >= 8 L* (standing objects; 2 cm from the
             (the central 60 % of the base; other products masked)                          card's height in px, else 3 % of the box)
  BLACK      the product's p0.5 L* vs the plate's p0.5 L* inside the frame                   not below it by more than 1.5
  LAMP       G1.10 for a lamp in frame: shade L* 93-97, H 35-45, S 25-45 (the brightest     lit, with a light layer near it
             quarter of its interior) and a light layer with energy round it
  EYE        the designer's squint at x1, phone size                                         by hand (not automated)
LIGHT and CONTACT are indicative (they read pixels, not geometry); EDGE, SHADOW, SHARP, GRAIN, BLACK and LAMP are measurements.
A score per layer (0 = clean) adds each check's excess over its bound; rows are reported worst first.

    python3.12 -I -B pasted_test.py <room> [--out file.json]       # a room of finish.ROOMS, its current default stack
    from pasted_test import run_test                                 # for a verify script: run_test(st, base, layers, lights)
"""
import glob
import importlib.util
import json
import math
import os
import sys

import cv2
import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finish as F  # noqa: E402

SEB_PATH = os.path.join(F.R, "living-room", "warm-modern", "phase2-2026-11-10", "layers", "scan_edge_bleed.py")
_spec = importlib.util.spec_from_file_location("scan_edge_bleed", SEB_PATH)
seb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seb)

HANGING = ("art", "print", "sconce", "pendant", "curtain", "blind", "hook", "towel", "wall-shelf", "ceiling", "wall-decor")
FLAT = ("rug", "mat", "runner", "bedding", "pillowcase", "bedspread", "cushion", "throw", "pad", "sofa-cover")
LAMPS = ("sconce", "pendant", "lamp", "ceiling-light")
_CARDS = {}


def card_dims(pid):
    if not _CARDS:
        for p in glob.glob(os.path.join(F.REPO, "data", "products", "**", "*.json"), recursive=True):
            _CARDS[os.path.splitext(os.path.basename(p))[0]] = p
    p = _CARDS.get(pid or "")
    if not p:
        return None
    try:
        return json.load(open(p)).get("dimensions_cm")
    except (OSError, ValueError):
        return None


def kind_of(slot):
    s = slot.lower()
    if any(k in s for k in FLAT):
        return "flat"
    if any(k in s for k in HANGING) and "floor" not in s:
        return "hanging"
    return "standing"


def is_lamp(slot):
    s = slot.lower()
    return any(k in s for k in LAMPS)


def light_dir(Lc, inside, offset, light_xy):
    din = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    m = din > 3
    n = int(m.sum())
    if n < 150 or light_xy is None:
        return None
    sig = max(2.0, 0.08 * math.sqrt(n))
    Lb = cv2.GaussianBlur(Lc, (0, 0), sig)
    ys, xs = np.nonzero(m)
    A = np.stack([np.ones(n), xs - xs.mean(), ys - ys.mean()], 1)
    coef, *_ = np.linalg.lstsq(A, Lb[ys, xs], rcond=None)
    g = coef[1:]
    ext = math.sqrt(n)
    span = float(np.hypot(*g) * ext)
    cx, cy = xs.mean() + offset[1], ys.mean() + offset[0]
    ref = np.array([light_xy[0] - cx, light_xy[1] - cy])
    if span < 4.0 or np.linalg.norm(ref) < 1:
        return dict(span_L=round(span, 2), verdict="n/a (flat shading)")
    ang = math.degrees(math.acos(float(np.clip(np.dot(g, ref) / (np.linalg.norm(g) * np.linalg.norm(ref)), -1, 1))))
    return dict(span_L=round(span, 2), angle_deg=round(ang, 1))


def contact(Lfull, a, others, px_per_cm, fmask):
    inside = a >= 0.5
    cols = np.nonzero(inside.any(0))[0]
    if len(cols) < 6:
        return None
    c0, c1 = cols.min(), cols.max()
    w = c1 - c0 + 1
    use = cols[(cols >= c0 + 0.2 * w) & (cols <= c1 - 0.2 * w)]
    b = int(max(2, round(2 * px_per_cm)))
    H = a.shape[0]
    band, far = [], []
    for c in use:
        yb = int(np.nonzero(inside[:, c])[0].max())
        if yb + 6 * b >= H:
            continue
        for y in range(yb + 1, yb + b + 1):
            if others[y, c] < 0.1 and not inside[y, c] and fmask[y, c]:
                band.append(Lfull[y, c])
        for y in range(yb + 3 * b, yb + 6 * b + 1):
            if others[y, c] < 0.1 and not inside[y, c] and fmask[y, c]:
                far.append(Lfull[y, c])
    if len(band) < 20 or len(far) < 20:
        return dict(verdict="n/a (no free floor under it in frame)", band_px=b)
    return dict(dark_L=round(float(np.median(far) - np.median(band)), 2), band_px=b)


def lamp_check(L, lights, a):
    inside = a >= 0.5
    din = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    m = din > 2
    if m.sum() < 30:
        return None
    rgb = L[..., :3][m].astype(np.float32)
    Lp = cv2.cvtColor((rgb[None] / 255.0).astype(np.float32), cv2.COLOR_RGB2LAB)[0][:, 0]
    top = Lp >= np.percentile(Lp, 75)
    shade_L = float(np.median(Lp[top]))
    mean = rgb[top].mean(0) / 255.0
    hsv = cv2.cvtColor(mean[None, None].astype(np.float32), cv2.COLOR_RGB2HSV)[0, 0]
    H_, S_ = float(hsv[0]), float(hsv[1] * 100)
    ys, xs = np.nonzero(inside)
    h, w = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    y0, y1 = max(0, ys.min() - h), min(a.shape[0], ys.max() + 2 * h)
    x0, x1 = max(0, xs.min() - w), min(a.shape[1], xs.max() + w)
    energy = max((float(Lt[y0:y1, x0:x1].astype(np.float32).mean()) for Lt in lights), default=0.0)
    ok = 93 <= shade_L <= 97 and 35 <= H_ <= 45 and 25 <= S_ <= 45
    lit = shade_L >= 90
    v = "lit (G1.10)" if ok and energy > 2 else ("looks lit, outside G1.10's H/S" if lit and energy > 2 else
                                                  ("lit, but no light layer round it" if lit else "NOT lit"))
    return dict(shade_L=round(shade_L, 1), H=round(H_, 1), S=round(S_, 1), light_layer_mean=round(energy, 2), verdict=v)


def score_of(r):
    s, why = 0.0, []
    sr = r.get("sharp_ratio")
    if sr:
        ex = max(0.0, abs(math.log(sr)) - math.log(1.15)) / math.log(1.15)
        if ex > 0:
            s += min(3.0, ex)
            why.append(f"SHARP {sr:.2f}" + (" (sharper than the plate)" if sr > 1 else " (softer)"))
    gr = r.get("grain_ratio")
    if gr:
        ex = (math.log(0.8) - math.log(gr)) / math.log(1.25) if gr < 0.8 else max(0.0, math.log(gr) - math.log(1.25)) / math.log(1.25)
        if ex > 0:
            s += min(2.0, ex)
            why.append(f"GRAIN {gr:.2f}" + (" (noisier than the plate)" if gr > 1 else " (smoother)"))
    ld = r.get("light") or {}
    if "angle_deg" in ld and ld["angle_deg"] > 25:                     # indicative: half weight, at most 1
        s += min(1.0, 0.5 * (ld["angle_deg"] - 25) / 25)
        why.append(f"LIGHT {ld['angle_deg']:.0f} deg (indicative)")
    ct = r.get("contact") or {}
    if "dark_L" in ct and ct["dark_L"] < 8:                             # indicative: half weight, at most 1
        s += min(1.0, 0.5 * (8 - ct["dark_L"]) / 8)
        why.append(f"CONTACT {ct['dark_L']:.1f} L* (indicative)")
    bl = r.get("black") or {}
    if bl.get("below_by", 0) > 1.5:
        s += bl["below_by"] / 5
        why.append(f"BLACK -{bl['below_by']:.1f}")
    ne, ns = r.get("edge_rows_x1", 0), r.get("shadow_rows_x1", 0)
    if ne:
        s += min(3, ne)
        why.append(f"EDGE x{ne}")
    if ns:
        s += min(3, ns)
        why.append(f"SHADOW x{ns}")
    lp = r.get("lamp") or {}
    if lp and not lp.get("verdict", "").startswith("lit (G1.10)"):
        s += 2 if lp["verdict"] == "NOT lit" else 1
        why.append(f"LAMP {lp['verdict']}")
    return round(s, 2), why


def run_test(st, base, layers, lights, label="before"):
    """the test on a stack (base RGB, [(RGBA, shadow RGB or None)], [light RGB]); rows per layer, worst first"""
    H, W = base.shape[:2]
    fmask = F.frame_mask((H, W), st["frame_box"])
    rng = np.random.default_rng(F.SEED)
    light_xy = F.light_centroid(base, fmask)
    alphas = [L[..., 3].astype(np.float32) / 255.0 for L, _ in layers]
    union = np.max(np.stack(alphas), 0) if alphas else np.zeros((H, W), np.float32)
    Lplate = F.Lstar(base)
    free = fmask & (union < 0.02)
    bp_plate = float(np.percentile(Lplate[free], 0.5)) if free.any() else 0.0
    pref = F.plate_reference(base, union, fmask, np.random.default_rng(F.SEED))
    comp_full = F.compose(base, layers, lights)
    Lfull = F.Lstar(comp_full)
    o = base.astype(np.float64)
    rows = []
    for i, ((L, S), e) in enumerate(zip(layers, st["entries"])):
        a = alphas[i]
        below_nos = o.astype(np.uint8)
        below = o if S is None else F.rhu(o * S.astype(np.float64) / 255.0)
        comp = F.rhu(F.rhu(L[..., :3].astype(np.float64) * a[..., None]) + below * (1 - a[..., None]))
        r = dict(room=st["key"], layer=e["name"], slot=e["slot"], product=e["product"], kind=kind_of(e["slot"]), test=label)
        vis = (a > 0.5) & fmask
        r["frame_px"] = int(vis.sum())
        if r["frame_px"] < 30:
            r["note"] = "not in frame"
            rows.append(r)
            o = comp
            continue
        S3 = S if S is not None else np.full((H, W, 3), 255, np.uint8)
        er = seb.edge_check(L, below_nos)
        sr = seb.shadow_check(L, S3)
        r["edge_rows_x1"] = sum(1 for x in er if seb.visible("EDGE", x) == "x1-x2")
        r["shadow_rows_x1"] = sum(1 for x in sr if seb.visible("SHADOW", x) == "x1-x2")
        r["edge_rows_low"] = len(er) - r["edge_rows_x1"]
        r["shadow_rows_low"] = len(sr) - r["shadow_rows_x1"]
        crop = F.bbox_of(a > 0.02, 24, (H, W))
        m = F.layer_edge_and_plate_sigma(comp.astype(np.uint8), below.astype(np.uint8), a, union, fmask, rng, crop, pref)
        if m:
            if m["s_layer"] and m["s_plate"]:
                r["sharp_ratio"] = round(m["s_plate"] / m["s_layer"], 3)
            if m["s_interior"] and m["s_plate"]:
                r["interior_ratio"] = round(m["s_plate"] / m["s_interior"], 3)
            if m["noise_layer"] and m["noise_plate"]:
                r["grain_ratio"] = round(m["noise_layer"] / m["noise_plate"], 3)
            r["sigma"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}
        Lc = F.Lstar(comp[crop].astype(np.uint8))
        inside = (a[crop] >= 0.9)
        if r["kind"] == "standing" and not is_lamp(e["slot"]):
            r["light"] = light_dir(Lc, inside, (crop[0].start, crop[1].start), light_xy)
            dims = card_dims(e["product"])
            ys = np.nonzero((a >= 0.5).any(1))[0]
            hpx = float(ys.max() - ys.min() + 1)
            if dims and dims.get("height"):
                ppc = hpx / float(dims["height"])
            else:
                ppc = 0.015 * hpx
            others = np.max(np.stack([alphas[j] for j in range(len(alphas)) if j != i]), 0) if len(alphas) > 1 else np.zeros((H, W), np.float32)
            r["contact"] = contact(Lfull, a, others, ppc, fmask)
            if r["contact"]:
                r["contact"]["px_per_cm"] = round(ppc, 2)
        din = cv2.distanceTransform((a >= 0.9).astype(np.uint8), cv2.DIST_L2, 5)
        core = (din > 2) & fmask
        if core.sum() > 50:
            p05 = float(np.percentile(F.Lstar(L[..., :3])[core], 0.5))
            r["black"] = dict(p05_L=round(p05, 2), plate_p05_L=round(bp_plate, 2), below_by=round(max(0.0, bp_plate - p05), 2))
        if is_lamp(e["slot"]):
            r["lamp"] = lamp_check(L, lights, a)
        r["score"], r["fails"] = score_of(r)
        rows.append(r)
        o = comp
    rows.sort(key=lambda x: -x.get("score", -1))
    return dict(room=st["key"], label=label, light_centroid=light_xy, plate_black_p05_L=round(bp_plate, 2), plate_reference=pref, rows=rows)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("room", choices=sorted(F.ROOMS))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    st = F.load_room(a.room)
    base, layers, lights = F.read_stack(st)
    res = run_test(st, base, layers, lights)
    for r in res["rows"]:
        print(f"{r.get('score', '-'):>6}  {r['layer']:28s} {', '.join(r.get('fails', [])) or r.get('note', 'clean')}")
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
