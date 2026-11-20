#!/usr/bin/env python3
"""
compose_edits.py: the layers of stage one from the mask-edit passes, their projection D1 <-> D2, and the two frames (render-agent,
2026-11-20; 0 tokens beyond the passes). MB1's compositor (master/warm-modern/mb1-2026-11-19/tools/mb1_compose.py), on two frames:
Per pass (passes.json: the raw edit, its input, the base the input was made from):
  1. lock: ECC affine of the edit onto its input, masked to the clay's architecture / kitchen / fixed furniture outside the pass's zone;
  2. MP-I1: the gain field (sigma 60, the MB0 compositor's) against the base, outside the zone and the lamps' glow;
  3. cut, per product: in a zone round its clay region, GrabCut seeded by what the edit changed on the base (dE76 on a 1 px blur; a
     lower threshold for the pale products on pale grounds) and by the clay region's core; only pieces touching the core; holes filled;
     a pixel claimed by two products goes to the nearer clay region; fillers (candles, olive, eucalyptus, pears, the paper roll, the
     blank canvas) belong to their product;
  4. shadow: the edit's darkening of the base in a band round each product, never on a product (multiply, z - 1);
  5. light: for a lit lamp, the edit's brightening of the base outside every product, smoothed (screen, z 90);
  6. MP-I2 / WM-G1: the frame's toe (plate-<frame>-compose.json, step 3) on the new layers' L*, once.
Then the projection: a layer cut in one frame goes to the other by the rotation homography about PD (the same rays: exact), with its
shadow and light, where the other frame's clay sees the product (a depth test against that frame's defaults clay: nearer objects cover).
Then the frames: plate-<frame>.png, the layers in z order (each shadow, then the layer), the lights times (1 - every alpha); outside
every alpha, shadow and light nothing differs from the plate (RND2).
  python3 compose_edits.py cut <pass> ...      python3 compose_edits.py project      python3 compose_edits.py compose
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kd_common as K  # noqa: E402
from kd_passes import PASSES, PRODUCTS, FILLERS, VARIANTS, owner  # noqa: E402
import kd_fixes as FX  # noqa: E402

C = K.C
H, W = K.H, K.W
ST = K.ST
ARCH = (1, 2, 3, 4, 5, 9, 10, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33, 36, 37, 38, 40, 41, 42, 43)
PALE = {53, 57, 58, 62, 63, 65, 76, 50, 70}          # bone / cream / white products on pale grounds: a lower change threshold
PAD = {50: 30, 52: 14, 53: 26, 55: 14, 57: 40, 58: 40, 60: 24, 61: 10, 62: 10, 63: 14, 65: 12, 66: 10, 67: 12, 69: 14, 70: 16,
       71: 8, 72: 10, 73: 12, 74: 12, 76: 12, 77: 14}
FILLER_PAD = {54: 40, 56: 10, 59: 70, 64: 8, 68: 4, 51: 6, 75: 8}
OUT_LAYERS = os.path.join(ST, "layers")


def toe(fr):
    s = json.load(open(os.path.join(ST, f"plate-{fr}-compose.json")))["steps"][2]
    return (s["xp"], s["fp"]) if s.get("applied") else None


def fill_holes(m, max_area):
    inv = (~m).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lb[0], lb[-1], lb[:, 0], lb[:, -1]])))
    return m | np.isin(lb, [i for i in range(1, n) if i not in border and st[i, cv2.CC_STAT_AREA] < max_area])


def keep_touching(m, core):
    n, lb, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    good = set(np.unique(lb[core & m])) - {0}
    return np.isin(lb, list(good))


def product_ids(k):
    return [k] + [f for f, o in FILLERS.items() if o == k]


def light_env(ids, lamps):
    env = np.zeros((H, W), bool)
    for k in lamps:
        env |= C.dil(ids == k, 230 if k == 50 else 150)
    return env


def cut_pass(p, rec, J):
    P = PASSES[p]
    fr = P["frame"]
    ids = K.ids(fr)
    pl_ids = K.ids(f"{fr}-plate")
    base = C.load(os.path.join(ST, J["base"]))
    variant = P.get("variant", False)
    prods = sorted({owner(k) for k in P["ids"]})
    zones = {}
    for k in prods:
        z = np.zeros((H, W), bool)
        for j in product_ids(k):
            z |= C.dil(ids == j, FILLER_PAD.get(j, PAD.get(k, 14)))
        if k == 50:                                   # the pendant: its whole box (the variants' shapes differ from the clay's)
            z |= C.box_mask([J.get("pendant_box", (640, 0, 1190, 480))])
        zones[k] = z
    zone = np.zeros((H, W), bool)
    for z in zones.values():
        zone |= z
    stable = C.ero(np.isin(pl_ids, ARCH), 3) & ~C.dil(zone, 40) & K.frame_mask()
    e, rl = K.ecc_lock(os.path.join(ST, J["raw"]), os.path.join(ST, J["input"]), stable)
    lampenv = light_env(ids, P["lamps"])
    keep = ~C.dil(zone, 40) & ~lampenv
    g = C.gain_field(e, base, keep)
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    lab_e, lab_b = C.to_lab(e), C.to_lab(base)
    d = np.linalg.norm(C.blur(lab_e, 1.0) - C.blur(lab_b, 1.0), axis=-1)
    out_d = d[keep & K.frame_mask()]
    rp = dict(lock=rl, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
              dE_outside_zone_p50_p95=[round(float(v), 2) for v in np.percentile(out_d, [50, 95])], products={})
    # light vs object: a change of brightness only (hue kept) on the plate's surfaces round a lit lamp is light, not object
    lab_e0, lab_b0 = C.blur(lab_e, 1.5), C.blur(lab_b, 1.5)
    ce_, cb_ = np.hypot(lab_e0[..., 1], lab_e0[..., 2]), np.hypot(lab_b0[..., 1], lab_b0[..., 2])
    he_, hb_ = np.degrees(np.arctan2(lab_e0[..., 2], lab_e0[..., 1])), np.degrees(np.arctan2(lab_b0[..., 2], lab_b0[..., 1]))
    dh_ = np.abs((he_ - hb_ + 180) % 360 - 180)
    same = ((np.abs(lab_e0[..., 1] - lab_b0[..., 1]) < 4) & (np.abs(lab_e0[..., 2] - lab_b0[..., 2]) < 5)) | ((dh_ < 12) & (np.abs(ce_ - cb_) < 8))
    layers = {}
    for k in prods:
        z = zones[k]
        core_src = np.isin(ids, product_ids(k))
        core = C.ero(core_src, 3 if core_src.sum() > 600 else 1)
        thr = 5.0 if k in PALE else 7.0
        cand = (d > thr) & z
        if k not in PALE:
            cand &= ~(same & ~C.dil(core_src, 4))     # shading on the ground beside a product is not the product
        else:
            cand &= ~(same & ~C.dil(core_src, 10) & (lab_e0[..., 0] < lab_b0[..., 0]))   # a shadow beside a pale product
        if P["lamps"]:
            glow = (lab_e[..., 0] - lab_b[..., 0] > 2) & same & ~C.dil(core_src, 6)
            cand &= ~glow
        cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        sure = (core & (d > 2.5)) | C.ero((d > 16) & z & C.dil(core_src, 6), 2)
        hard = z & ~C.ero(z, 2)
        try:
            m = C.gc_cut(e, sure, C.dil(cand, 2) & z, z, hard, iters=6) if sure.sum() > 20 else cand
        except Exception:                             # noqa: BLE001
            m = cand
        m = (m | (cand & C.dil(m, 1))) & z
        m = keep_touching(m, sure | core)
        m = fill_holes(m, 1500) & z
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        layers[k] = m
    # a pixel claimed by two products goes to the nearer clay region
    if len(prods) > 1:
        dist = np.stack([cv2.distanceTransform((~np.isin(ids, product_ids(k))).astype(np.uint8), cv2.DIST_L2, 5) for k in prods])
        near = np.argmin(dist, 0)
        for i, k in enumerate(prods):
            layers[k] &= (near == i) | ~np.any([layers[j] for j in prods if j != k], axis=0)
    pre_fix = np.zeros((H, W), bool)
    for k in prods:
        pre_fix |= layers[k]
    # the code fixes (kd_fixes.py)
    if 50 in prods:
        e, layers[50] = FX.fix_pendant(e, layers[50], ids, rp)
    if 52 in prods:
        layers[52] = FX.fix_runner(layers[52], pl_ids)
    if 53 in prods:
        layers[53] = FX.sharp_filter(e, layers[53], ids, 54, rp)
    for k in prods:
        rp["products"][str(k)] = dict(slot=PRODUCTS[k][0], px=int(layers[k].sum()), clay_px=int(np.isin(ids, product_ids(k)).sum()))
    # shadows: darkening round each product (band 45), the nearest product, never on any product, never through the window
    allfg = np.zeros((H, W), bool)
    for k in prods:
        allfg |= layers[k]
    rat = np.clip(C.blur(C.luma(C.lin(e)), 2) / np.maximum(C.blur(C.luma(C.lin(base)), 2), 1e-4), 0, 1.5)
    dark = np.clip(1 - rat - 0.02, 0, 0.75)
    dk = np.stack([cv2.distanceTransform((~layers[k]).astype(np.uint8), cv2.DIST_L2, 5) for k in prods])
    near = np.argmin(dk, 0)
    du = dk.min(0)
    band = 45
    taper = np.clip(1 - du / band, 0, 1) ** 1.1
    shade_w = np.clip(C.blur(((dh_ < 15) & (np.abs(ce_ - cb_) < 10)).astype(np.float64), 4) * 1.4 - 0.2, 0, 1)
    edge_in = allfg & ~C.ero(allfg, 2)
    shadows = {}
    for i, k in enumerate(prods):
        sup, bk = FX.support_env(k, pl_ids, band)
        env = (du <= bk) & (near == i) & ~allfg & (pl_ids != 0) & (pl_ids != 15)
        if sup is not None:
            env &= sup                                # shadows only on the product's support surfaces (kd_fixes.SUPPORT)
        if k == 50 or variant:
            env &= False                              # the pendant casts no shadow (1.4)
        tk = np.clip(1 - du / max(bk, 1), 0, 1) ** 1.1
        s = 1 - C.blur(dark * tk * env * shade_w, 1.0)
        s[~C.dil(env, 1) | allfg] = 1
        s_min = cv2.erode(s.astype(np.float32), C.disk(2).astype(np.uint8)).astype(np.float64)
        s = np.where(edge_in, np.minimum(s, s_min), s)
        shadows[k] = np.where(s > 0.996, 1.0, np.clip(s, 0, 1))
    light = None
    if P["lamps"] and not variant:
        env = light_env(ids, P["lamps"])
        L8 = np.clip(1 - (1 - e) / np.maximum(1 - base, 1e-3), 0, 0.5)
        glow_ok = np.clip(C.blur(((dh_ < 30) & (ce_ - cb_ < 22)).astype(np.float64), 3) * 1.4 - 0.2, 0, 1)
        wgt = (env & ~C.dil(allfg | pre_fix, 3) & (pl_ids != 0) & (pl_ids != 15)).astype(np.float64) * glow_ok   # never the edit's own product pixels
        Ls = np.stack([C.blur(L8[..., c] * wgt, 8) / np.maximum(C.blur(wgt, 8), 1e-3) for c in range(3)], -1)
        Ls[C.blur(wgt, 8) < 0.02] = 0
        soft_env = C.blur(env.astype(np.float64), 25)
        light = Ls * soft_env[..., None]               # under the products too (filled from round them): the variants differ in size
        rp["light_px"] = int((light.max(2) > 0.003).sum())
    rec[p] = rp
    return e, layers, shadows, light, prods


def write_pass(p, e, layers, shadows, light, prods, man, rec):
    P = PASSES[p]
    fr = P["frame"]
    tc = toe(fr)
    variant = P.get("variant", False)
    man["layers"] = [l for l in man["layers"] if not (l.get("pass") == p and l["frame"] == fr)]
    for k in prods:
        slot, pid, z = PRODUCTS[k]
        if variant:
            slot, pid = VARIANTS[p]
        a = C.soft(layers[k])
        rgb = C.defringe(e, layers[k])
        if tc:
            lab = C.to_lab(rgb)
            lab[..., 0] = np.interp(lab[..., 0], tc[0], tc[1])
            rgb = np.clip(C.from_lab(lab), 0, 1)
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        lp = os.path.join(ST, "layers", fr, slot, pid + ".png")
        sp = os.path.join(ST, "shadows", fr, slot, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
        s8 = C.q(shadows[k])
        Image.fromarray(s8).save(sp, optimize=True)
        ys, xs = np.nonzero(a8 > 0)
        man["layers"].append(dict(frame=fr, slot=slot, product=pid, clay_id=k, z=z, shadow_z=z - 1, default=not variant, layer=os.path.relpath(lp, ST),
                                  shadow=os.path.relpath(sp, ST), alpha_px=int((a8 > 0).sum()), shadow_px=int((s8 < 255).sum()),
                                  bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if xs.size else None,
                                  sold=True, source=f"{fr} pass {p} (nano-banana-2 mask edit), cut in code (tools/compose_edits.py)", pass_=p))
    if light is not None:
        lp = os.path.join(ST, "light", fr, f"{p}-lamps.png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        Image.fromarray(C.q(light)).save(lp, optimize=True)
        man["light"] = [li for li in man["light"] if not (li.get("pass_") == p and li["frame"] == fr)]
        man["light"].append(dict(frame=fr, file=os.path.relpath(lp, ST), z=90, blend="screen", lamps=[PRODUCTS[k][0] for k in P["lamps"]], pass_=p))
    man["layers"].sort(key=lambda l: (l["frame"], l["z"], l["slot"]))


# ---------------------------------------------------------------------------------------------------------------- projection
def project(man, rec):
    """every default layer cut in one frame, into the other frame where that frame's clay sees the product (depth test)"""
    man["layers"] = [l for l in man["layers"] if not l.get("projected_from")]
    man["light"] = [li for li in man["light"] if not li.get("projected_from")]
    rp = {}
    for src, dst in (("D1", "D2"), ("D2", "D1")):
        maps = K.map_between(src, dst)
        mx, my, ok = maps
        ids_dst = K.ids(dst)
        dep_src = K.depth(src)
        dep_dst = K.depth(dst)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        f_src, _, _ = K.axes(src)
        rb = K.rays(dst, xx + 0.5, yy + 0.5)
        k_ = rb @ f_src                                  # dst ray . src forward
        ds = cv2.remap(np.where(np.isfinite(dep_src), dep_src, 50).astype(np.float32), mx, my, cv2.INTER_NEAREST)
        d_in_dst = ds / np.maximum(k_, 1e-6)
        dd = np.where(np.isfinite(dep_dst), dep_dst, 50)
        for l in [l for l in man["layers"] if l["frame"] == src and l["default"]]:
            k = l["clay_id"]
            if not np.isin(ids_dst, product_ids(k)).any():
                continue
            rgba = np.asarray(Image.open(os.path.join(ST, l["layer"]))).astype(np.float32)
            s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"]))).astype(np.float32)
            wr = cv2.remap(rgba, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            ws = cv2.remap(s8, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
            wr[~ok] = 0
            ws[~ok] = 255
            vis = d_in_dst <= dd + 0.03 + 0.01 * d_in_dst
            vis = C.dil(vis, 1) | np.isin(ids_dst, product_ids(k))
            wr[..., 3] *= vis
            ws = np.where(vis, ws, 255)
            # the straight-alpha colour under a resampled alpha: premultiplied resample
            prem = cv2.remap(rgba[..., :3] * (rgba[..., 3:4] / 255), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            al = cv2.remap(rgba[..., 3], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            col = prem / np.maximum(al[..., None] / 255, 1e-3)
            a8 = np.clip(np.rint(wr[..., 3]), 0, 255).astype(np.uint8)
            out = np.dstack([np.clip(np.rint(col), 0, 255).astype(np.uint8), a8])
            out[..., :3][a8 == 0] = 0
            if (a8 > 0).sum() < 20:
                continue
            lp = os.path.join(ST, "layers", dst, l["slot"], os.path.basename(l["layer"]))
            sp = os.path.join(ST, "shadows", dst, l["slot"], os.path.basename(l["shadow"]))
            os.makedirs(os.path.dirname(lp), exist_ok=True)
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            Image.fromarray(out, "RGBA").save(lp, optimize=True)
            s8o = np.clip(np.rint(ws), 0, 255).astype(np.uint8)
            Image.fromarray(s8o).save(sp, optimize=True)
            ys, xs = np.nonzero(a8 > 0)
            nl = dict(l, frame=dst, layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sp, ST), alpha_px=int((a8 > 0).sum()),
                      shadow_px=int((s8o < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                      projected_from=src, source=l["source"] + f"; projected {src} -> {dst} by the rotation homography about PD (depth test on the {dst} clay)")
            man["layers"].append(nl)
            rp[f"{l['product']} {src}->{dst}"] = dict(alpha_px=nl["alpha_px"], shadow_px=nl["shadow_px"])
        for li in [li for li in man["light"] if li["frame"] == src]:
            L8 = np.asarray(Image.open(os.path.join(ST, li["file"]))).astype(np.float32)
            wl = cv2.remap(L8, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            wl[~ok] = 0
            if wl.max() < 2:
                continue
            lp = os.path.join(ST, "light", dst, os.path.basename(li["file"]).replace(".png", f"-from-{src}.png"))
            os.makedirs(os.path.dirname(lp), exist_ok=True)
            Image.fromarray(np.clip(np.rint(wl), 0, 255).astype(np.uint8)).save(lp, optimize=True)
            man["light"].append(dict(li, frame=dst, file=os.path.relpath(lp, ST), projected_from=src))
            rp[f"light {li['file']} {src}->{dst}"] = dict(px=int((wl.max(2) > 1).sum()))
    man["layers"].sort(key=lambda l: (l["frame"], l["z"], l["slot"]))
    rec["projection"] = rp


# ---------------------------------------------------------------------------------------------------------------- frames
def compose(man, rec, fr, swap=None, out_name=None):
    """swap: {slot: layer entry} to show a variant instead of the default"""
    plate8 = np.asarray(Image.open(os.path.join(ST, f"plate-{fr}.png")).convert("RGB"))
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    a_all = np.zeros((H, W))
    ls = [l for l in man["layers"] if l["frame"] == fr and l["default"]]
    if swap:
        ls = [l for l in ls if l["slot"] not in swap] + list(swap.values())
    ls.sort(key=lambda l: (l["z"], l["slot"]))
    for l in ls:
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
        s8 = np.asarray(Image.open(os.path.join(ST, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
        region |= (rgba[..., 3] > 0) | (s8 < 255)
        a_all = 1 - (1 - a_all) * (1 - rgba[..., 3] / 255)
    for li in [li for li in man["light"] if li["frame"] == fr]:
        L8 = np.asarray(Image.open(os.path.join(ST, li["file"]))).astype(np.float64)
        L8 = np.clip(np.rint(L8 * (1 - a_all)[..., None]), 0, 255).astype(np.uint8)
        out = C.light_one(out, L8)
        region |= L8.max(2) > 0
    o8 = C.q(out)
    name = out_name or f"{fr}-defaults"
    Image.fromarray(o8).save(os.path.join(ST, f"{name}.png"))
    K.frame_crop(o8).save(os.path.join(ST, f"{name}-frame.png"))
    lab = C.to_lab(o8.astype(np.float64) / 255)
    r = dict(region_px=int(region.sum()), outside_differing_px=int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum()),
             rule="outside every alpha, shadow and light: plate-<frame>.png, pixel for pixel",
             black_point_p05=round(float(np.percentile(lab[..., 0][K.frame_mask()], 0.5)), 2))
    rec.setdefault("frames", {})[name] = r
    return o8


def load_man():
    mp = os.path.join(ST, "manifest.json")
    if os.path.exists(mp):
        return json.load(open(mp))
    return dict(id="wm-kitchen-dining-stage1-2026-11-20", room="dining-room", house_room="kitchen-dining", style="warm-modern", frames=["D1", "D2"],
                canvas=[W, H], frame_box=list(K.FRAME), bases={"D1": "plate-D1.png", "D2": "plate-D2.png"},
                cameras={fr: dict(loc=list(K.LOC), yaw=K.YAW[fr], lens_mm=24, u0=K.U0, v0=K.V0) for fr in ("D1", "D2")},
                compose="plate-<frame>.png; per layer of that frame in z order: shadow (multiply), then the layer (straight alpha); lights (screen, z 90) "
                        "times (1 - every alpha)", layers=[], light=[])


def main(args):
    man = load_man()
    rp = os.path.join(ST, "compose.json")
    rec = json.load(open(rp)) if os.path.exists(rp) else {}
    J = json.load(open(os.path.join(ST, "passes.json")))
    cmd = args[0]
    if cmd == "cut":
        for p in args[1:]:
            e, layers, shadows, light, prods = cut_pass(p, rec, J[p])
            write_pass(p, e, layers, shadows, light, prods, man, rec)
            np.save(os.path.join(K.SCR, f"{p}-locked.npy"), e.astype(np.float16))
            print(p, json.dumps({k: v for k, v in rec[p].items() if k != "lock"})[:1200], json.dumps(rec[p]["lock"]["ecc"]))
    if cmd == "project":
        project(man, rec)
        print(json.dumps(rec["projection"])[:2000])
    if cmd in ("compose", "project", "cut"):
        for fr in ("D1", "D2"):
            if os.path.exists(os.path.join(ST, f"plate-{fr}.png")):
                compose(man, rec, fr)
        print(json.dumps(rec.get("frames")))
    json.dump(man, open(os.path.join(ST, "manifest.json"), "w"), indent=1)
    json.dump(rec, open(rp, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1:])
