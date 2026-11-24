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
    fix_rec = opts["edit_fix"](S) if opts.get("edit_fix") else None      # a code fix of the edit itself, before the cut (PB1: the fringe)
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
    if fix_rec:
        rp["edit_fix"] = fix_rec
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
        mctx = dict(e=e, base=base, ids=ids, d=d, region=region, zone=zone, lab_e=lab_e, lab_b=lab_b, kid=kid, box=box, S=S)
        masks = opts["mask_edit"](masks, mctx)
        if mctx.get("notes"):
            rp["mask_edit"] = mctx["notes"]
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
        # its own edge where an upper product of the pass covers it: opaque, in its own colour (never the plate through two soft edges)
        near_upper = C.dil(upper, 3) & m & ~C.ero(m, 3)
        if near_upper.any():
            a = np.where(near_upper, 1.0, a)
            col = np.where(near_upper[..., None], C.defringe(e, m), col)
        # filled under the upper products by 8 px, from its own pixels
        under = C.dil(m, opts.get("under_px", {}).get(pr, 8)) & upper & ~m
        if under.any():
            fill = KC.spread(e, C.ero(m, 1).astype(np.float64), (2.0, 5.0, 12.0))
            col = np.where(under[..., None], fill, col)
            a = np.where(under, 1.0, a)
        a = np.where(a < 0.04, 0.0, a)
        col = floor_lab(col, a > 0)
        out[pr] = (a, col)
        rp["products"][pr] = dict(px=int((a > 0).sum()), clay_px=int(region[pr].sum()), ratio_to_clay=round(float((m.sum() + 1) / (region[pr].sum() + 1)), 3))
    if opts.get("post"):
        pr_ = opts["post"](out, masks, dict(e=e, ids=ids, S=S, kid=kid, rp=rp, box=box))
        if pr_:
            rp["post"] = pr_
            for pr in prods:
                if out[pr] is not None:
                    rp["products"][pr]["px"] = int((out[pr][0] > 0).sum())
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


# the bed passes (PB1 / GB1): the basket's geometry as the clay builds it (framing_wm_kids.py row 17)
BASKET = {"boy": dict(c=(-0.62, 11.58), r=0.175, h=0.39, filler="ball"), "girl": dict(c=(-0.62, 15.21), r=0.20, h=0.45, filler="balls")}


def _hue(lab):
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1])), np.hypot(lab[..., 1], lab[..., 2])


def _gm(e, sig=1.2):
    L = cv2.GaussianBlur(C.to_lab(e)[..., 0].astype(np.float32), (0, 0), sig)
    return np.hypot(cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3))


def _xf(mask, f):
    s, tx, ty, cx, cy = f
    M = np.float32([[s, 0, cx - s * cx + tx], [0, s, cy - s * cy + ty]])
    return cv2.warpAffine(mask.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST).astype(bool)


def _poly(pts):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.rint(cv2.convexHull(np.asarray(pts, np.float32))).astype(np.int32)], 1)
    return m.astype(bool)


def _basket(e, ids, kid):
    """the drawn basket (0 tokens). The clay stands the card's basket where the plan puts it; the edit may stand it nearer, so the clay
    region is not the product. (1) The clay's own outline (body and handles, id 59) moved and scaled onto the edit's edges (a
    similarity fit; the card's size is kept when the scale is about 1); (2) the body: GrabCut seeded with the fitted body below the rim;
    (3) the handles: the jute pixels (C* > 17) of the fitted outline above the rim, as rope (the loop's opening stays open); (4) the
    boy's ball: a circle on the edit's edges, seeded by the bright pixels in the lower half of the opening, kept above the front rim"""
    gm = _gm(e)
    R = (ids == 59).astype(np.uint8)
    cnt, _ = cv2.findContours(R, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    pts = max(cnt, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    pts = pts[pts[:, 1] < H - 15]
    ys, xs = np.nonzero(R)
    cx, cy = float(xs.mean()), float(ys.max())

    def score(s, tx, ty):
        q = np.c_[cx + s * (pts[:, 0] - cx) + tx, cy + s * (pts[:, 1] - cy) + ty]
        q = q[(q[:, 0] >= 0) & (q[:, 0] < W - 1) & (q[:, 1] >= 0) & (q[:, 1] < H - 1)].astype(np.float32)
        return float(cv2.remap(gm, q[:, 0:1], q[:, 1:2], cv2.INTER_LINEAR).mean())
    best = (score(1.0, 0, 0), (1.0, 0, 0))
    ident = best[0]
    for s in np.arange(0.95, 1.35, 0.02):
        for tx in range(-60, 61, 6):
            for ty in range(-40, 161, 6):
                v = score(s, tx, ty)
                if v > best[0]:
                    best = (v, (s, tx, ty))
    s0, tx0, ty0 = best[1]
    for s in np.arange(s0 - 0.03, s0 + 0.031, 0.005):
        for tx in range(tx0 - 6, tx0 + 7):
            for ty in range(ty0 - 6, ty0 + 7):
                v = score(s, tx, ty)
                if v > best[0]:
                    best = (v, (s, tx, ty))
    f = (best[1][0], best[1][1], best[1][2], cx, cy)
    T59 = _xf(R, f)
    g = BASKET[kid]
    th = np.linspace(0, 2 * np.pi, 96)
    top = np.array([K.proj(kid, g["c"][0] + g["r"] * np.cos(a), g["c"][1] + g["r"] * np.sin(a), g["h"]) for a in th])
    top = np.c_[cx + f[0] * (top[:, 0] - cx) + f[1], cy + f[0] * (top[:, 1] - cy) + f[2]]
    ry0, ry1 = float(top[:, 1].min()), float(top[:, 1].max())
    yy = np.arange(H)[:, None]
    lb = C.blur(C.to_lab(e), 1.0)
    hue, Cc = _hue(lb)
    # (2) the body
    zone = C.dil(T59, 30) & (yy > ry0 - 120)
    body = C.gc_cut(e, C.ero(T59, 8) & (yy > ry1 + 15), T59 & (yy > ry0), zone, zone & (yy < ry0 - 75), iters=8)
    body &= yy > ry0 + 0.5 * (ry1 - ry0)                 # above the rim's middle only the handles and the filler are basket
    # (3) the handles
    jute = T59 & (yy < ry1) & (Cc > 17) & (hue > 52) & (hue < 78) & (lb[..., 0] < 82)
    jute = cv2.morphologyEx(jute.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(2)).astype(bool)
    handles = keep_touching(jute, C.dil(body, 3))
    basket = body | handles
    # (4) the ball
    ball_rec = None
    if g["filler"] == "ball":
        hull = _poly(np.c_[np.nonzero(T59)[1], np.nonzero(T59)[0]])
        seed = C.ero(hull, 10) & (yy > ry0 + 0.6 * (ry1 - ry0)) & (yy < ry1 + 10) & (lb[..., 0] > 70) & (Cc < 15)
        seed = cv2.morphologyEx(seed.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
        if seed.sum() > 200:
            sy, sx = np.nonzero(seed)
            mx, hw, by = 0.5 * (sx.min() + sx.max()), 0.5 * (sx.max() - sx.min()), sy.max()
            thc = np.linspace(0, 2 * np.pi, 240)
            fb = (0.0, None)
            for r in np.arange(hw - 12, hw + 13, 1.5):
                for ccx in np.arange(mx - 12, mx + 13, 1.5):
                    for ccy in np.arange(by - r, by + 40, 1.5):
                        qi = np.rint(np.c_[ccx + r * np.cos(thc), ccy + r * np.sin(thc)]).astype(int)
                        qi = qi[(qi[:, 1] < ry1 + 20) & (qi[:, 0] >= 0) & (qi[:, 0] < W) & (qi[:, 1] >= 0)]
                        if len(qi) < 60:
                            continue
                        v = float(gm[qi[:, 1], qi[:, 0]].mean())
                        if v > fb[0]:
                            fb = (v, (float(ccx), float(ccy), float(r)))
            ccx, ccy, r = fb[1]
            xx = np.arange(W)[None, :]
            ball = ((xx - ccx) ** 2 + (yy - ccy) ** 2 <= r * r) & ~C.dil(handles, 1)
            ball &= ~(C.dil(body, 2) & ~ball) | (yy < ry1)
            by_, bx_ = np.nonzero(body)
            basket |= ball & ((yy < ry1 + 0.25 * (ry1 - ry0)) | _poly(np.c_[bx_, by_]))
            ball_rec = [round(v, 1) for v in fb[1]]
    basket = fill_holes(basket, 300)
    rec = dict(fit=dict(scale=round(float(f[0]), 3), shift_px=[int(f[1]), int(f[2])], edge_score=round(best[0], 2), edge_score_clay=round(ident, 2)),
               rim_y=[round(ry0, 1), round(ry1, 1)], handles_px=int(handles.sum()), ball_circle=ball_rec, px=int(basket.sum()),
               clay_px=int((np.isin(ids, (59, 60))).sum()))
    return basket, rec


def _throw_mask(lab_e, d, reg, bed_reg, ids, block):
    """the throw by its own tone and hue on a 3 px blur (the waffle's cells averaged): darker than the duvet, and on the other side of the
    midpoint hue between the throw's clay core and the duvet when the two differ by more than 10 degrees; in one piece with its core;
    the walnut boards and the basket are not throw"""
    lb = C.blur(lab_e, 3.0)
    L = lb[..., 0]
    h, Cc = _hue(lb)
    core = C.ero(reg, 4) & ~block
    duv = C.ero(bed_reg, 4) & ~C.dil(reg, 20) & (d > 6) & ~block
    hc, hd = float(np.median(h[core])), float(np.median(h[duv]))
    Lc90, Ld50 = float(np.percentile(L[core], 90)), float(np.percentile(L[duv], 50))
    L_thr = Lc90 + 0.55 * (Ld50 - Lc90)
    board = C.dil(np.isin(ids, K.FIXED), 1)
    t = C.dil(reg, 140) & (d > 6) & ~board & ~block
    if abs(hd - hc) > 10:
        h_thr = 0.5 * (hc + hd)
        t &= ((L < L_thr) & ((h - h_thr) * np.sign(hc - hd) > 0) & (Cc > 5)) | (L < 28)
    else:
        h_thr = None
        t &= L < L_thr
    t = cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_CLOSE, C.disk(3)).astype(bool)
    t = keep_touching(t, core)
    t = fill_holes(t, 6000)
    t = cv2.morphologyEx(t.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
    t = keep_touching(t, core) & ~block
    return t, dict(hue_throw=round(hc, 1), hue_duvet=round(hd, 1), hue_thr=None if h_thr is None else round(h_thr, 1), hue_sign=float(np.sign(hc - hd)),
                   L_thr=round(L_thr, 1))


def _bed_masks(masks, ctx):
    """PB1 / GB1: the basket by its fitted outline (_basket), the throw by its tone and hue (_throw_mask), not by their clay boxes (the
    edit drapes the throw over the whole foot of the bed and stands the basket nearer than the clay). The basket is the top of the pass:
    it keeps its pixels; the throw loses them; the duvet and the pillows lose both; the duvet takes what the throw's old mask held"""
    e, ids, kid = ctx["e"], ctx["ids"], ctx["kid"]
    bk = ctx.get("basket")
    if bk is None:
        bk, brec = _basket(e, ids, kid)
    else:
        bk, brec = bk
    bk &= ctx["box"]
    t, trec = _throw_mask(ctx["lab_e"], ctx["d"], ctx["region"]["bedspread"], ctx["region"]["bedding"], ids, bk)
    old_t, old_b = masks["bedspread"], masks["toy-basket"]
    for k in masks:
        if k not in ("bedspread", "toy-basket"):
            masks[k] = masks[k] & ~t & ~bk
    le, lb_ = C.blur(ctx["lab_e"], 1.5), C.blur(ctx["lab_b"], 1.5)
    same = (np.abs(le[..., 1] - lb_[..., 1]) < 3.5) & (np.abs(le[..., 2] - lb_[..., 2]) < 4.5)
    taken = t | bk
    for k in masks:
        if k not in ("bedspread", "toy-basket", "bedding"):
            taken |= masks[k]
    cand = (ctx["d"] > 6) & ~same & ctx["box"] & ~taken & C.dil(masks["bedding"] | old_t | old_b, 80)
    pids = K.ids(f"K-{kid}-plate")
    cand &= C.dil(np.isin(pids, (20, 21, 22)) | np.isin(ids, (53, 54, 55, 56, 59, 60)), 12)     # on the bed, never the wall
    cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_OPEN, C.disk(2)).astype(bool)
    # the throw's clay box lies on the bed: what the drawn throw does not cover there is duvet (pale on the pale mattress, so no d test);
    # the basket's clay box reaches the floor and the walnut: only its changed, re-coloured pixels
    # the plate's bare mattress (clay id 22) is all under the set in the edit (a made bed): whatever the other products leave of it is
    # duvet or sheet, even where the pale duvet differs little from the pale mattress
    mattress = (pids == 22) & ctx["box"] & ~taken
    masks["bedding"] = keep_touching(masks["bedding"] | (old_t & ~taken) | (old_b & ~taken & (ctx["d"] > 6) & ~same) | cand | mattress,
                                     C.ero(ctx["region"]["bedding"], 3))
    masks["bedspread"] = t
    masks["toy-basket"] = bk
    ctx.setdefault("notes", {}).update(basket=brec, throw=trec)
    return masks


FRINGE_CM = 2.75          # the card: 2-3 cm


def _fringe_rows(e, t, bk, ids, thr, dep):
    """per column of the throw's free-hanging hem: the lowest strand (the throw's tone and hue on a 0.7 px blur) and the fringe's length
    (from the woven edge, where the gradient turns vertical: a run of anisotropy over 0.4 ending at the tip); px per cm from the clay's
    depth at the hang"""
    lb = C.blur(C.to_lab(e), 0.7)
    L = lb[..., 0]
    hue, Cc = _hue(lb)
    strand = (L < thr["L_thr"]) & (Cc > 5)
    if thr.get("hue_thr") is not None:
        strand &= (hue - thr["hue_thr"]) * thr["hue_sign"] > 0
    strand |= L < 28
    Lp = C.to_lab(e)[..., 0].astype(np.float32)
    gx, gy = cv2.Sobel(Lp, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(Lp, cv2.CV_32F, 0, 1, ksize=3)
    Ax, Ay = cv2.GaussianBlur(gx * gx, (0, 0), 1.5), cv2.GaussianBlur(gy * gy, (0, 0), 1.5)
    an = cv2.blur((Ax - Ay) / (Ax + Ay + 1e-3), (15, 1))
    hidden = C.dil(bk, 2) | C.dil(np.isin(ids, K.FIXED), 2)
    td = C.dil(t, 3)
    rows = {}
    for x in np.nonzero(t.any(0))[0]:
        c = np.nonzero(strand[:, x] & td[:, x])[0]
        if c.size < 20:
            continue
        Ts = int(c.max())
        if Ts + 4 >= H or Ts < 60 or hidden[Ts + 1:Ts + 5, x].any():
            continue
        hi = an[Ts - 50:Ts + 1, x] > 0.4
        runs, st_ = [], None
        for i, v in enumerate(hi):
            if v and st_ is None:
                st_ = i
            if (not v or i == len(hi) - 1) and st_ is not None:
                runs.append((st_, i if v else i - 1))
                st_ = None
        ok = [(a, b) for a, b in runs if b >= len(hi) - 13 and b - a >= 7]
        z = dep[max(Ts - 40, 0):Ts + 1, x]
        z = z[np.isfinite(z)]
        if z.size == 0:
            continue
        free = 0                                     # the duvet below the tip, down to whatever hides it (basket, walnut), at most 60
        while free < 60 and Ts + 1 + free < H and not hidden[Ts + 1 + free, x]:
            free += 1
        rows[int(x)] = dict(Ts=Ts, F=(50 - max(ok, key=lambda r: r[1] - r[0])[0]) if ok else None, pxcm=float(K.F_ / np.median(z) / 100), free=free)
    return rows


def _bed_fix(S):
    """PB1 / GB1, the edit fixed before the cut (0 tokens):
    1. white specks the edit left at the throw's edge on the duvet (a pixel 7 L* over its 7 x 7 median, above L* 85) inpainted;
    2. the fringe: the edit drew it about 4 cm (measured per column, _fringe_rows); the card says 2-3 cm. Along the free-hanging hem the
       strands are cut at 2.75 cm from the woven edge: the strand pixels below that line are inpainted from the duvet between and below
       them (the edit's own duvet and the throw's shade on it stay where they are); the cut line is smooth along the hem and tapers to
       the drawn length at its ends. The basket and the walnut are never touched.
    The basket's fit is made here once and kept for the masks."""
    e, base, ids, kid = S["e"], S["base"], S["ids"], S["kid"]
    lab_e, lab_b = C.to_lab(e), C.to_lab(base)
    d = np.linalg.norm(C.blur(lab_e, 2.0) - C.blur(lab_b, 2.0), axis=-1)
    bk, brec = _basket(e, ids, kid)
    bk &= S["box"]
    t, trec = _throw_mask(lab_e, d, S["region"]["bedspread"], S["region"]["bedding"], ids, bk)
    S["basket_fit"] = (bk, brec)
    L = lab_e[..., 0].astype(np.float32)
    med = cv2.medianBlur(np.clip(L * 2.55, 0, 255).astype(np.uint8), 7).astype(np.float32) / 2.55
    band = C.dil(t, 4) & ~C.ero(t, 2) & ~C.dil(bk, 2)
    specks = C.dil(band & (L - med > 7) & (L > 85), 1) & band
    e2 = KC.inpaint(e, specks, radius=3) if specks.any() else e.copy()
    out = dict(specks_px=int(specks.sum()))
    dep = K.depth(S["P"].get("clay", f"K-{kid}"))
    rows = _fringe_rows(e2, t, bk, ids, trec, dep)
    if len(rows) < 30:
        S["e"] = e2
        return dict(out, fringe="no free-hanging hem found")
    xs = np.array(sorted(rows))
    Ts = np.array([rows[x]["Ts"] for x in xs], float)
    Fm = np.array([np.nan if rows[x]["F"] is None else rows[x]["F"] for x in xs], float)
    px = np.array([rows[x]["pxcm"] for x in xs])
    free = np.array([rows[x]["free"] for x in xs], float)
    n = len(xs)
    win = lambda a, i, k: a[max(0, i - k):i + k + 1]      # noqa: E731
    Ts_s = np.array([np.percentile(win(Ts, i, 8), 75) for i in range(n)])
    Ts_s = np.array([np.median(win(Ts_s, i, 8)) for i in range(n)])
    Fs = np.array([np.nanmedian(win(Fm, i, 15)) if np.isfinite(win(Fm, i, 15)).any() else np.nan for i in range(n)])
    Fs = np.clip(np.where(np.isnan(Fs), np.nanmedian(Fm), Fs), 10, 45)
    tg = FRINGE_CM * px
    lift = np.clip(Fs - tg, 0, None)
    lift = np.where(free >= 4, lift, 0.0)                        # a tip with no duvet below it (basket, walnut) stays
    # contiguous runs of the hem; taper over 15 columns at each end; smooth along the hem
    seg = np.r_[0, np.cumsum(np.diff(xs) > 3)]
    for sg in np.unique(seg):
        idx = np.nonzero(seg == sg)[0]
        k = np.arange(len(idx))
        lift[idx] *= np.clip(np.minimum(k, len(idx) - 1 - k) / 15.0, 0, 1)
    lift = cv2.GaussianBlur(lift.astype(np.float32).reshape(1, -1), (0, 0), 4).ravel()
    # the strands below the new tip line removed: a strand pixel (darker than the brightest of its 5 x 5, by 10 L*, on the throw's side
    # of the hue line, or 25 L* darker) inpainted from the duvet between and below the strands (Telea, 2 px)
    Lr = C.to_lab(e2)
    L0 = Lr[..., 0].astype(np.float32)
    h0, C0 = _hue(Lr)
    mx = cv2.dilate(L0, np.ones((5, 5), np.uint8))
    st_ = (L0 < mx - 10) & (C0 > 4)
    if trec.get("hue_thr") is not None:
        st_ &= (h0 - trec["hue_thr"]) * trec["hue_sign"] > -4
    st_ |= L0 < mx - 25
    cut = np.zeros((H, W), bool)
    hidden = C.dil(bk, 2) | C.dil(np.isin(ids, K.FIXED), 2)
    td = C.dil(t, 3)
    yy = np.arange(H)[:, None]
    for x, T_, D_ in zip(xs, Ts_s, lift):
        if D_ < 1.0:
            continue
        lo = int(np.ceil(T_ - D_))
        cut[lo:int(Ts[xs == x][0]) + 4, x] = True
    rm = C.dil(st_ & cut & td, 1) & cut & ~hidden
    e3 = KC.inpaint(e2, rm, radius=2) if rm.any() else e2
    S["e"] = np.clip(e3, 0, 1)
    cm = Fm / px
    out.update(fringe=dict(columns=int(n), measured=int(np.isfinite(Fm).sum()),
                           drawn_cm_p10_p50_p90=[round(float(v), 2) for v in np.nanpercentile(cm, [10, 50, 90])],
                           target_cm=FRINGE_CM, lift_px_p50_max=[round(float(np.median(lift[lift > 1])), 1) if (lift > 1).any() else 0, round(float(lift.max()), 1)],
                           after_cm_p50=round(float(np.median(((Fs - lift) / px)[lift > 1])), 2) if (lift > 1).any() else None,
                           columns_lifted=int((lift > 1).sum()), strand_px_removed=int(rm.sum())))
    return out


def _bed_masks_fixed(masks, ctx):
    bf = ctx["S"].get("basket_fit")
    if bf is not None:
        ctx["basket"] = bf
    return _bed_masks(masks, ctx)


_BED = dict(edit_fix=_bed_fix, mask_edit=_bed_masks_fixed, under_px={"bedding": 40, "pillowcase": 12})
OPTS = {"PB3-window": dict(mask_edit=_clean_blind), "PB1-bed": _BED, "GB1-bed": _BED}


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
