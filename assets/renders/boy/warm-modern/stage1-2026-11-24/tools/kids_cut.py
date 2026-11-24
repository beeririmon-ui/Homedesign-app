#!/usr/bin/env python3
"""
kids_cut.py: the cut of the crop edits into layers, shadows and light, and the compose (render-agent, 2026-11-24; 0 tokens).
The kitchen's second cut (dining stage1-2026-11-20/tools/kd_cut2.py; its matte and inpaint are imported, nothing changed there), made
simpler for one camera per room:
  1. lock and light: the assembled canvas (kids_crop.py) is matched to the canvas it was made on outside the products (MP-I1's gain field);
  2. what changed: dE76 of the blurred Lab against the base, in each product's zone (the clay region of its ids, padded); a pixel that only
     got darker at the same chroma is shade, not product (it goes to the shadow); components that touch no clay region are dropped;
  3. who owns a pixel: the clay's own id pass decides (the product whose clay region holds it, else the nearest clay region): so the
     occlusion order of the clay (the cushions over the standing pillow, the toy over the lying one, the basket over the duvet) holds;
  4. edges: against the background a known-background matte (kd_cut2.matte, the edit's own background inpainted under the products);
     between two products of the pass the lower one is filled 8 px under the upper one, so the upper's soft edge sits on product, not plate;
  5. shadows: the edit's darkening of the base round each product (compose_defaults.shadow_of), each pixel to the nearest product; never on
     a product of the pass;
  6. light (a lit lamp in the pass): screen, 1 - (1 - e) / (1 - base) outside every product, inside the lamp's envelope, smoothed;
  7. WM-G1: no product pixel under L* 11 (the kitchen's floor), no shadow taking the base under sRGB 0.12.
  python3 kids_cut.py cut <pass>            -> layers/, shadows/, light/, manifest.json of the pass's room
  python3 kids_cut.py compose <kid> [name] -> the room's frame from plate.png + the default layers (z order) + lights
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kids_common as K  # noqa: E402
from kids_passes import PASSES, PRODUCTS, pass_ids  # noqa: E402

sys.path.insert(0, os.path.join(K.REPO, "assets/renders/dining/warm-modern/stage1-2026-11-20/tools"))
import kd_cut2 as KC  # noqa: E402

C = K.C
H, W = K.H, K.W
PAD = {"roman-blind": 30, "pendant": 26, "framed-prints": 12, "bookshelf": 14, "pen-cup": 10, "bookends": 12, "toy-cars": 10,
       "bedding": 50, "pillowcase": 30, "bedspread": 60, "cushions-pair": 30, "soft-toy": 20, "toy-basket": 40}
PALE = {"roman-blind", "pendant", "bedding", "pillowcase", "soft-toy", "framed-prints", "toy-basket"}
SHADOW = {"roman-blind": None, "pendant": None, "framed-prints": dict(band=22, rim=6), "bookshelf": dict(band=26, rim=6),
          "pen-cup": dict(band=24, rim=5), "bookends": dict(band=24, rim=5), "toy-cars": dict(band=14, rim=4),
          "bedding": dict(band=40, rim=8), "pillowcase": dict(band=26, rim=6), "bedspread": dict(band=26, rim=6),
          "cushions-pair": dict(band=30, rim=6), "soft-toy": dict(band=22, rim=5), "toy-basket": dict(band=46, rim=8)}
# rigid products the edits put where their clay is: the mask may grow only this far past the clay region (the kitchen's NO_GROW)
GROW_LIMIT = {"framed-prints": 5, "bookshelf": 7, "pen-cup": 6, "bookends": 6, "toy-cars": 10}
BP_FLOOR = ([0.0, 11.0, 16.0, 100.0], [11.0, 12.5, 16.0, 100.0])
SHADOW_FLOOR_SRGB = 0.12


def man_path(kid):
    return os.path.join(K.ST[kid], "manifest.json")


def load_man(kid):
    p = man_path(kid)
    if os.path.exists(p):
        return json.load(open(p))
    return dict(id=f"wm-kids-{kid}-stage1-2026-11-24", room=kid, house_room=kid, style="warm-modern", frame=f"K-{kid}",
                canvas=[W, H], frame_box=list(K.FRAME), base="plate.png",
                camera=dict(loc=list(K.LOC[kid]), yaw=K.YAW, lens_mm=24, u0=K.U0, v0=K.V0),
                compose="plate.png; per layer in z order: shadow (multiply), then the layer (straight alpha); lights (screen, z 90) times "
                        "(1 - every alpha)", layers=[], light=[], status="for QA (stage one, before the owner's approval 3). Not for the "
                        "site before QA.")


def save_man(kid, man):
    man["layers"].sort(key=lambda l: (l["z"], l.get("sub", 0), l["slot"], not l.get("default", True)))
    json.dump(man, open(man_path(kid), "w"), indent=1, ensure_ascii=False)


def floor_lab(rgb, m=None):
    lab = C.to_lab(rgb)
    L = np.interp(lab[..., 0], *BP_FLOOR)
    if m is not None:
        L = np.where(m, L, lab[..., 0])
    lab[..., 0] = L
    return np.clip(C.from_lab(lab), 0, 1)


def fill_holes(m, max_area):
    inv = (~m).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    small = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] <= max_area and i not in border]
    return m | np.isin(lab, small)


def keep_touching(m, core):
    n, lab = cv2.connectedComponents(m.astype(np.uint8), connectivity=8)
    keep = set(np.unique(lab[m & core])) - {0}
    return np.isin(lab, list(keep))


def lamp_env(ids, kid, lamps):
    env = np.zeros((H, W), bool)
    for pr in lamps:
        cid = PRODUCTS[kid][pr][3]
        env |= C.dil(np.isin(ids, cid), 360)
    return env & (ids != 0) & (ids != 15) & K.frame_mask() | (env & K.frame_mask() & (ids == 90))


def edit_canvas(p, opts=None):
    """the assembled edit, matched to its base outside the products (MP-I1's gain field); the zones of the pass's products"""
    opts = opts or {}
    P = PASSES[p]
    kid = P["kid"]
    st = K.ST[kid]
    rec = json.load(open(os.path.join(st, "inputs", f"{p}-prep.json")))
    x0, y0, x1, y1 = rec["crop_box"]
    base = C.load(os.path.join(K.REPO, rec["base"]))
    e = C.load(os.path.join(K.SCR, f"{p}-canvas.png"))
    ids = K.ids(P.get("clay", f"K-{kid}"))          # the clay the pass was prepared from (the bed passes: the bed-only clay)
    pid = set(pass_ids(p))
    box = np.zeros((H, W), bool)
    box[y0:y1, x0:x1] = True
    region, zone = {}, {}
    for pr in P["products"]:
        cid = [c for c in PRODUCTS[kid][pr][3] if c in pid]
        region[pr] = np.isin(ids, cid)
        zone[pr] = C.dil(region[pr], PAD[pr] + opts.get("pad_extra", {}).get(pr, 0)) & box
    allz = np.zeros((H, W), bool)
    for z in zone.values():
        allz |= z
    env = lamp_env(ids, kid, P["lamps"]) if P["lamps"] else np.zeros((H, W), bool)
    keep = box & ~C.dil(allz, 40) & ~env & K.frame_mask()
    g = C.gain_field(e, base, keep)
    g[~box] = 1.0
    e = C.srgb(np.clip(C.lin(e) * g, 0, 1))
    e[~box] = base[~box]
    return dict(P=P, kid=kid, st=st, rec=rec, base=base, e=e, ids=ids, box=box, region=region, zone=zone, env=env, keep=keep, g=g)


def shadow_soft(e, base, fg, sp, block, cap=0.65):
    """the edit's darkening of the base round a product, as a multiply: the luma ratio on a 5 px blur (the edit's own trowel texture is
    not shade), 4 % ignored, tapered with the distance, the contact band next to the product filled from the shade just beyond it (no
    bright gap at the edge), never on another product, softened 2.5 px"""
    rat = np.clip(C.blur(C.luma(e), 5) / np.maximum(C.blur(C.luma(base), 5), 1e-4), 0, 1.5)
    env = C.dil(fg, sp["band"]) & ~fg & ~block
    dist = cv2.distanceTransform((~fg).astype(np.uint8), cv2.DIST_L2, 5)
    taper = np.clip(1 - dist / max(sp["band"], 1), 0, 1) ** 1.2
    dark = np.clip(1 - rat - 0.04, 0, cap) * env * taper
    contact = env & (dist <= sp["rim"] + 2)
    beyond = env & (dist > sp["rim"] + 2) & (dist <= sp["rim"] + 10)
    w = C.blur(beyond.astype(np.float64), 4)
    fillv = C.blur(dark * beyond, 4) / np.maximum(w, 1e-6)
    dark = np.where(contact & (w > 0.02), np.maximum(dark, fillv), dark)
    sh = 1 - C.blur(dark, 2.5)
    sh[~C.dil(env, 3)] = 1
    sh = np.where(block & ~env, 1.0, sh)
    return np.clip(np.where(sh > 0.995, 1.0, sh), 0, 1)


def cut(p, opts=None):
    opts = opts or {}
    S = edit_canvas(p, opts)
    P, kid, st, rec, base, e, ids, box = S["P"], S["kid"], S["st"], S["rec"], S["base"], S["e"], S["ids"], S["box"]
    region, zone, env, keep, g = S["region"], S["zone"], S["env"], S["keep"], S["g"]
    prods = P["products"]
    lab_e, lab_b = C.to_lab(e), C.to_lab(base)
    d = np.linalg.norm(C.blur(lab_e, 2.0) - C.blur(lab_b, 2.0), axis=-1)       # sigma 2: the edit's own trowel texture is not a change
    le, lb = C.blur(lab_e, 1.5), C.blur(lab_b, 1.5)
    ce, cb = np.hypot(le[..., 1], le[..., 2]), np.hypot(lb[..., 1], lb[..., 2])
    dh = np.abs((np.degrees(np.arctan2(le[..., 2], le[..., 1])) - np.degrees(np.arctan2(lb[..., 2], lb[..., 1])) + 180) % 360 - 180)
    same = ((np.abs(le[..., 1] - lb[..., 1]) < 3.5) & (np.abs(le[..., 2] - lb[..., 2]) < 4.5)) | ((dh < 10) & (np.abs(ce - cb) < 6))
    shade = same & (le[..., 0] < lb[..., 0] - 1.0)
    glow = same & (le[..., 0] > lb[..., 0] + 1.5) if P["lamps"] else np.zeros((H, W), bool)
    rp = dict(pass_=p, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g[box], [1, 50, 99])],
              dE_outside_zone_p50_p95=[round(float(v), 2) for v in np.percentile(d[keep], [50, 95])] if keep.any() else None, products={})
    # 2. what changed, per product zone
    U = np.zeros((H, W), bool)
    core_all = np.zeros((H, W), bool)
    claim = {}
    for pr in prods:
        thr = opts.get("thr", {}).get(pr, 4.0 if pr in PALE else 6.0)
        c = (d > thr) & zone[pr]
        c &= ~(same & ~C.dil(region[pr], 3))          # the wall re-lit or re-textured by the edit (darker or brighter): not product
        c &= ~(glow & ~C.dil(region[pr], 4))
        c = cv2.morphologyEx(c.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        core = C.ero(region[pr], 2 if region[pr].sum() > 400 else 0)
        c |= core & (d > 1.5)
        c = keep_touching(c, C.dil(region[pr], 2))
        # GrabCut on the edit's colours (the kitchen's step): the product's own colours against the wall and its painted shadow
        if pr not in opts.get("no_gc", ()):
            z = zone[pr]
            sure = (core & (d > 2.5)) | C.ero((d > 16) & z & C.dil(region[pr], 6), 2)
            hard = z & ~C.ero(z, 2)
            try:
                if sure.sum() > 20:
                    gm = C.gc_cut(e, sure, C.dil(c, 2) & z, z, hard, iters=6)
                    c = (gm | (c & C.dil(gm, 1) & ~same)) & z
            except Exception:                                   # noqa: BLE001
                pass
        claim[pr] = c
        U |= c
        core_all |= region[pr]
    U = fill_holes(U, 1500)
    U = cv2.morphologyEx(U.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(1)).astype(bool)
    # 3. owner: the clay's own region, else the nearest clay region (the clay id pass holds the occlusion order)
    dist = np.stack([cv2.distanceTransform((~region[pr]).astype(np.uint8), cv2.DIST_L2, 5) for pr in prods], 0)
    # among the products whose own colour cut claims the pixel, the clay's owner if it is one of them, else the nearest claimant
    cl = np.stack([C.dil(claim[pr], 1) for pr in prods], 0)
    big = np.where(cl, dist, 1e9)
    own = np.where(cl.any(0), np.argmin(big, 0), np.argmin(dist, 0))
    masks = {}
    for i, pr in enumerate(prods):
        m = U & (own == i) & zone[pr]
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2)).astype(bool) & zone[pr]   # no 1 px cracks inside a product
        m = fill_holes(m, 2500)
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
        m = keep_touching(m, C.dil(region[pr], 2))
        if pr in GROW_LIMIT:
            m &= C.dil(region[pr], GROW_LIMIT[pr])
        masks[pr] = m
    # slivers: a changed pixel no product kept (the clean-up opened a 1 px line where the clay's owner and the edit's colours
    # disagree) goes to the nearest product mask within 4 px, so no line of the base shows between two products
    anym = np.zeros((H, W), bool)
    for m in masks.values():
        anym |= m
    left = U & ~anym
    if left.any() and len(prods) > 0:
        dm = np.stack([cv2.distanceTransform((~masks[pr]).astype(np.uint8), cv2.DIST_L2, 5) for pr in prods], 0)
        near_i = np.argmin(dm, 0)
        close = np.min(dm, 0) <= 4
        for i, pr in enumerate(prods):
            masks[pr] |= left & close & (near_i == i)
        rp["slivers_px"] = int((left & close).sum())
    if opts.get("mask_edit"):
        masks = opts["mask_edit"](masks, dict(e=e, base=base, ids=ids, d=d, region=region, zone=zone, lab_e=lab_e, lab_b=lab_b))
    allfg = np.zeros((H, W), bool)
    for m in masks.values():
        allfg |= m
    # 4. edges: matte against the edit's own background; lower products filled under the upper ones
    Bk = KC.inpaint(e, C.dil(allfg, 3) & box, radius=6)
    zs = {pr: PRODUCTS[kid][pr][2] for pr in prods}
    out = {}
    for pr in prods:
        m = masks[pr]
        if m.sum() < 10:
            out[pr] = None
            continue
        upper = np.zeros((H, W), bool)
        for q in prods:
            if q != pr and zs[q] > zs[pr]:
                upper |= masks[q]
        lower_touch = np.zeros((H, W), bool)
        for q in prods:
            if q != pr and zs[q] < zs[pr]:
                lower_touch |= C.dil(masks[q], 2)
        a, col = KC.matte(e, m, Bk)
        col = np.where((a < 0.5)[..., None], C.defringe(e, m), col)      # no over-bright unmixing at a weak edge
        # the edge against a lower product of the pass: soft binary alpha, the colour from the product itself
        sb = C.soft(m)
        near_lower = lower_touch & ~C.ero(m, 2)
        a = np.where(near_lower, sb, a)
        col = np.where(near_lower[..., None], C.defringe(e, m), col)
        # filled under the upper products by 8 px, from its own pixels
        under = C.dil(m, 8) & upper & ~m
        if under.any():
            fill = KC.spread(e, C.ero(m, 1).astype(np.float64), (2.0, 5.0, 12.0))
            col = np.where(under[..., None], fill, col)
            a = np.where(under, 1.0, a)
        a = np.where(a < 0.04, 0.0, a)
        col = floor_lab(col, a > 0)
        out[pr] = (a, col)
        rp["products"][pr] = dict(px=int((a > 0).sum()), clay_px=int(region[pr].sum()), ratio_to_clay=round(float((m.sum() + 1) / (region[pr].sum() + 1)), 3))
    # 5. shadows, each pixel to the nearest product
    prev_alpha = np.zeros((H, W), bool)
    man = load_man(kid)
    for l in man["layers"]:
        if l.get("default", True) and l.get("pass_") != p:
            al = np.asarray(Image.open(os.path.join(st, l["layer"])))[..., 3] > 0
            if l["key"] in prods:                        # a product this pass re-cuts: its other pass's pixels only, never its own stale ones
                al &= ~box
            prev_alpha |= al
    block = allfg | prev_alpha
    sh = {}
    for pr in prods:
        if out[pr] is None or SHADOW.get(pr) is None:
            sh[pr] = np.ones((H, W))
            continue
        sh[pr] = shadow_soft(e, base, masks[pr], SHADOW[pr], block & ~masks[pr], cap=0.65)
    valid = [pr for pr in prods if out[pr] is not None]
    if valid:
        dd = np.stack([cv2.distanceTransform((~masks[pr]).astype(np.uint8), cv2.DIST_L2, 5) for pr in valid], 0)
        near = np.argmin(dd, 0)
        for i, pr in enumerate(valid):
            sh[pr] = np.where(near == i, sh[pr], 1.0)
            sh[pr] = np.where(block, 1.0, sh[pr])
            sh[pr] = np.maximum(sh[pr], SHADOW_FLOOR_SRGB / np.maximum(C.luma(base), SHADOW_FLOOR_SRGB))
            sh[pr][~box] = 1.0
    # 6. light
    light = None
    if P["lamps"]:
        L8 = np.clip(1 - (1 - e) / np.maximum(1 - base, 1e-3), 0, 0.6)
        ok = np.clip(C.blur(((dh < 30) & (ce - cb < 22)).astype(np.float64), 3) * 1.4 - 0.2, 0, 1)
        wgt = (env & ~C.dil(allfg | prev_alpha, 3)).astype(np.float64) * ok
        Ls = np.stack([C.blur(L8[..., c] * wgt, 8) / np.maximum(C.blur(wgt, 8), 1e-3) for c in range(3)], -1)
        Ls[C.blur(wgt, 8) < 0.02] = 0
        light = Ls * C.blur(env.astype(np.float64), 25)[..., None]
        light[~box] = 0
        rp["light_max"] = round(float(light.max()), 3)
    write(p, kid, prods, out, sh, light, man, rp)
    return rp


def write(p, kid, prods, out, sh, light, man, rp):
    st = K.ST[kid]
    man["layers"] = [l for l in man["layers"] if not (l.get("pass_") == p and l.get("default", True))]
    for pr in prods:
        if out[pr] is None:
            continue
        slot, pid, z, cids, sku = PRODUCTS[kid][pr]
        a, col = out[pr]
        a8 = C.q(a)
        rgba = np.dstack([C.q(col), a8])
        rgba[..., :3][a8 == 0] = 0
        lp = os.path.join(st, "layers", slot, pid + ".png")
        sp = os.path.join(st, "shadows", slot, pid + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        # a product cut in two passes (the prints: C on the shelf, A + B on the desk) is one layer: merge with the other pass's pixels
        prev = [l for l in man["layers"] if l["product"] == pid and l.get("default", True)]
        bx0, by0, bx1, by1 = PASSES[p]["box"]
        inbox = np.zeros((H, W), bool)
        inbox[by0:by1, bx0:bx1] = True
        if prev and os.path.exists(lp):
            # the other pass's pixels of the same product, outside this pass's crop only (a re-cut never keeps its own stale pixels)
            old = np.asarray(Image.open(lp)).copy()
            take = (old[..., 3] > 0) & (a8 == 0) & ~inbox
            rgba[take] = old[take]
            olds = np.asarray(Image.open(sp))
            s8 = np.where(inbox, C.q(sh[pr]), np.minimum(C.q(sh[pr]), olds))
        else:
            s8 = C.q(sh[pr])
        man["layers"] = [l for l in man["layers"] if not (l["product"] == pid and l.get("default", True))]
        Image.fromarray(rgba, "RGBA").save(lp, optimize=True)
        Image.fromarray(s8).save(sp, optimize=True)
        ys, xs = np.nonzero(rgba[..., 3] > 0)
        passes = sorted(set([p] + [x for l in prev for x in l.get("passes", [l.get("pass_")])]))
        man["layers"].append(dict(slot=slot, product=pid, key=pr, clay_ids=list(cids), z=z, sub=0, shadow_z=z - 1, default=True,
                                  layer=os.path.relpath(lp, st), shadow=os.path.relpath(sp, st), alpha_px=int((rgba[..., 3] > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                                  sold=True, sku=sku, source=f"pass {p} (nano-banana-2 crop edit), cut in code (tools/kids_cut.py)", pass_=p,
                                  passes=passes))
    if light is not None:
        lp = os.path.join(st, "light", f"{p}-lamps.png")
        Image.fromarray(C.q(light)).save(lp, optimize=True)
        man["light"] = [li for li in man["light"] if li.get("pass_") != p]
        man["light"].append(dict(file=os.path.relpath(lp, st), z=90, blend="screen", lamps=[PRODUCTS[kid][x][1] for x in PASSES[p]["lamps"]], pass_=p))
    man.setdefault("cut_records", {})[p] = rp
    save_man(kid, man)


def compose(kid, name=None, swap=None, base_file="plate.png", write_files=True, only=None):
    """swap: {slot: layer entry} to show a variant instead of the default; only: a set of product keys (a partial canvas)"""
    st = K.ST[kid]
    man = load_man(kid)
    plate8 = np.asarray(Image.open(os.path.join(st, base_file)).convert("RGB"))
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    a_all = np.zeros((H, W))
    ls = [l for l in man["layers"] if l.get("default", True)]
    if only is not None:
        ls = [l for l in ls if l["key"] in only]
    if swap:
        ls = [l for l in ls if l["slot"] not in swap] + list(swap.values())
    ls.sort(key=lambda l: (l["z"], l.get("sub", 0), l["slot"]))
    for l in ls:
        rgba = np.asarray(Image.open(os.path.join(st, l["layer"])))
        s8 = np.asarray(Image.open(os.path.join(st, l["shadow"])))
        out = C.compose_one(out, rgba, s8)
        region |= (rgba[..., 3] > 0) | (s8 < 255)
        a_all = 1 - (1 - a_all) * (1 - rgba[..., 3] / 255)
    for li in man["light"]:
        if only is not None and li.get("pass_") and not any(l.get("pass_") == li["pass_"] for l in ls):
            continue
        L8 = np.asarray(Image.open(os.path.join(st, li["file"]))).astype(np.float64)
        L8 = np.clip(np.rint(L8 * (1 - a_all)[..., None]), 0, 255).astype(np.uint8)
        out = C.light_one(out, L8)
        region |= L8.max(2) > 0
    o8 = C.q(out)
    r = dict(region_px=int(region.sum()), outside_differing_px=int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum()),
             rule="outside every alpha, shadow and light: plate.png, pixel for pixel",
             black_point_p05=round(float(np.percentile(C.to_lab(o8.astype(np.float64) / 255)[..., 0][K.frame_mask()], 0.5)), 2))
    if write_files and name:
        Image.fromarray(o8).save(os.path.join(st, f"{name}.png"))
        K.save_frame(o8, os.path.join(st, f"{name}-frame.png"))
    return o8, r


def _clean_blind(masks, ctx):
    """PB3: the blind is pale fabric; the edit redrew the mullion's top under it (dark bronze): only fabric-light pixels, one piece"""
    if "roman-blind" in masks:
        m0 = masks["roman-blind"]
        ys, xs = np.nonzero(m0)
        bottom = np.full(W, -1)
        for x in range(xs.min(), xs.max() + 1):
            c = np.nonzero(m0[:, x])[0]
            if c.size:
                bottom[x] = c.max()
        ok = bottom >= 0
        v = bottom[ok]
        vp = np.pad(v, 20, mode="edge")
        b_sm = bottom.copy()
        b_sm[ok] = np.median(np.stack([vp[i:i + len(v)] for i in range(41)], 0), 0)
        m = m0 & (np.arange(H)[:, None] <= b_sm[None, :] + 1)
        n, lb, st_, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
        if n > 1:
            m = lb == 1 + int(np.argmax(st_[1:, cv2.CC_STAT_AREA]))
        masks["roman-blind"] = fill_holes(m, 3000)
    return masks


def _bed_masks(masks, ctx):
    """PB1 / GB1: the throw by its own tone, not by its clay box (the edit drapes it differently from the clay's two boxes, and the
    football's clay outline overlaps its hang). On a 3 px blur (the waffle's cells and grid averaged) the throw is darker than the duvet
    and the pillows around it: its threshold is the midpoint between its own clay core's 70th percentile of L* and the duvet's 20th;
    the throw is the changed pixels near its clay region under that L*, in one piece with its core, closed and filled; the throw's
    earlier pixels above it go to the duvet; the other products lose the throw's pixels"""
    e_lab = C.blur(ctx["lab_e"], 3.0)
    L = e_lab[..., 0]
    reg = ctx["region"]["bedspread"]
    core = C.ero(reg, 4)
    duv = C.ero(ctx["region"]["bedding"], 4) & ~C.dil(reg, 20)
    thr = 0.5 * (np.percentile(L[core], 70) + np.percentile(L[duv], 20))
    near = C.dil(reg, 90)
    t = near & (L < thr) & (ctx["d"] > 6)
    t = cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(4)).astype(bool)
    t = keep_touching(t, core)
    t = fill_holes(t, 6000)
    t = cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_OPEN, C.disk(1)).astype(bool)
    old = masks["bedspread"]
    for k in masks:
        if k != "bedspread":
            masks[k] = masks[k] & ~t
    if "bedding" in masks:
        masks["bedding"] |= old & ~t
    masks["bedspread"] = t
    ctx.setdefault("notes", {})["throw_L_threshold"] = round(float(thr), 1)
    return masks


OPTS = {"PB3-window": dict(mask_edit=_clean_blind), "PB1-bed": dict(mask_edit=_bed_masks), "GB1-bed": dict(mask_edit=_bed_masks)}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "cut":
        print(json.dumps(cut(a[1], OPTS.get(a[1]))))
    elif a[0] == "compose":
        o8, r = compose(a[1], None, write_files=False)
        cp = os.path.join(K.SCR, f"{a[1]}-canvas.png")
        Image.fromarray(o8).save(cp)
        if len(a) > 2:
            K.save_frame(o8, os.path.join(K.SCR, f"{a[2]}-frame.png"))
        print(cp, json.dumps(r))
