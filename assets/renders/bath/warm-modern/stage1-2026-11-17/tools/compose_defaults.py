#!/usr/bin/env python3
"""
compose_defaults.py: B2 with the defaults (output 2), its layers, and the mask-edit variants (render-agent, 2026-11-18). 0 tokens.
Version 2 (2026-11-18): the cut by plain difference (v1) failed on this render: the model re-lit the whole room (window patches on
the left wall, a darker wall by the ring), so "the render differs from the plate" was not "product". v2 segments the products:
  1. lock: the render's lines against the input's (tools/lock_b2.py, the clay's named lines), one global warp (y about the horizon,
     x constant), as the plate. An edit (the sprig fix, a towel variant) is locked the same way on its own.
  2. tone match: a smooth gain field (normalised blur, sigma 60 px, per channel, linear light) of base / render, measured outside
     every product zone, shadow band and light envelope, applied to the render: the products sit in the plate's exposure.
  3. per slot, the alpha: GrabCut (OpenCV, 6 iterations) on the matched render, inside the slot's zone (the clay mask grown by its
     margin). Sure product: the clay core (eroded 4 px) where the render changed (dE76 over 9), plus the slot's colour prior (the
     pothos green, the caramel, the black of the ring, the vase and the pumps); probable product: the clay grown 2 px; sure
     background: outside the zone and the other slots' clay. Only components touching the sure product; holes under 150 px filled;
     a 0.8 px soft edge.
  4. per slot, the shadow (grey multiply on the sRGB values, as the engine does): the render's darkening of the plate (luma ratio,
     blurred 3 px, under 3 % ignored) inside an envelope: a contact rim round the product, plus the clay's own shadow (Cycles,
     B2 / B2-plate local ratio under 0.97) grown 8 px, within the slot's band; feathered 4 px; never on a product.
  5. the light of the sconce pair (screen, z 90): where the render is brighter than the stack (L = 1 - (1 - render) / (1 - stack),
     blurred 2 px, a floor of 0.01), only inside the clay's beam envelope (local ratio over 1.05, on the plaster and the stone top,
     grown 20 px, feathered 10 px), never on a product or the mirror. The light that falls on a product is in its own layer.
  6. the composite: ungraded, then the WM-G1 curve (plate-grade.json) pointwise: product RGB = curve(render); the grey shadow in
     the graded files = mean(curve(below x s)) / mean(curve(below)); the light solved again on the graded stack. The files are
     8-bit, the graded stack starts from plate.png's bytes, and the defaults are recomposed from the files (what the engine does).
     Outside every alpha, shadow and light: plate.png, pixel for pixel (RND2).
Variant mode: the other layers and the light are read from the defaults run's files, untouched; only the variant's layer and
shadow are cut (from its own render), and the variant composite is made from the files.

  python3 compose_defaults.py raw/defaults-r1.png [slot=<edit.png> ...]
  python3 compose_defaults.py raw/defaults-r1.png --variant hand-towel=<edit.png> --pid <product id> --name b2-variant-linen
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import grade_plate as G  # noqa: E402

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-2026-11-17/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath/"
HORIZON = 707.0
FRAME = G.FRAME
PLASTER, TOP, MIRROR = (1, 2, 3, 4), (23,), (17, 18)
# slot: clay ids, zone margin px, extra downward reach px, shadow band px, contact rim px, z, product id, colour prior
SLOTS = {
    "shower-dispensers": dict(ids=(41,), margin=8, band=14, rim=6, z=14, pid="shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle", prior="pump"),
    "vanity-sconces": dict(ids=(42, 43), margin=10, band=6, rim=3, z=14, pid="vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853", prior=None),
    "shower-curtain": dict(ids=(40,), margin=100, band=30, rim=8, z=26, pid="shower-curtain-aliexpress-linen-blend-slub-panel-200x270", prior=None),
    "floor-planter": dict(ids=(51, 52), margin=40, band=40, rim=14, z=30, pid="planter-cj-cement-ribbed-belly-beige-medium", prior="pothos"),
    "soap-dispenser": dict(ids=(44,), margin=8, band=16, rim=8, z=46, pid="soap-dispenser-cj-sand-ribbed-ceramic-pump-bottle", prior="pump"),
    "toothbrush-cup": dict(ids=(45, 46), margin=10, band=16, rim=8, z=46, pid="toothbrush-cup-cj-silver-travertine-cup", prior=None),
    "vanity-vase": dict(ids=(47, 48), margin=30, band=16, rim=8, z=46, pid="vanity-vase-cj-matte-black-pottery-bud-vase-10", prior="vase"),
    "towel-ring": dict(ids=(49,), margin=8, band=14, rim=6, z=50, pid="towel-ring-aliexpress-1-2pcs-bathroom-towel-842335-a3", prior="black"),
    "hand-towel": dict(ids=(50,), margin=40, down=260, band=40, rim=12, z=52, pid="hand-towel-aliexpress-pure-linen-towel-38x55-caramel", prior="caramel"),
}
LIGHT_PID = "vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853"
_LAB = {}


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def dil(m, r):
    return m.astype(bool) if r <= 0 else cv2.dilate(m.astype(np.uint8), disk(r)).astype(bool)


def ero(m, r):
    return m.astype(bool) if r <= 0 else cv2.erode(m.astype(np.uint8), disk(r)).astype(bool)


def blur(a, s):
    return cv2.GaussianBlur(a.astype(np.float32), (0, 0), s).astype(np.float64)


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def luma(a):
    return a @ np.array([0.2126, 0.7152, 0.0722])


def lab_of(img):
    k = id(img)
    if k not in _LAB:
        _LAB[k] = (img, G.to_lab(img))
    return _LAB[k][1]


def load(p, size=None):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64) / 255
    if size is not None and a.shape[:2] != size:
        a = cv2.resize(a.astype(np.float32), (size[1], size[0]), interpolation=cv2.INTER_LANCZOS4).astype(np.float64)
    return np.clip(a, 0, 1)


def q(x):
    return np.clip(np.rint(x * 255), 0, 255).astype(np.uint8)


def prior_mask(kind, img):
    if kind is None:
        return np.zeros(img.shape[:2], bool)
    lab = lab_of(img)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C, h = np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360
    if kind == "pothos":
        return (a < -6) & (b > 2) & (L < 70)
    if kind == "caramel":
        return (C > 22) & (h > 30) & (h < 75) & (L < 70)
    if kind in ("black", "pump"):
        return L < 26
    if kind == "vase":
        return (L < 26) | ((a < -4) & (L < 70) & (C > 5))
    raise ValueError(kind)


def lock_and_warp(path, size):
    """lock the still against the input (lock_b2.py) and warp it; returns the warped still and the warp record"""
    import compose_plate as CP
    img = load(path, size)
    stem = os.path.basename(path).rsplit(".", 1)[0]
    tmp = os.path.join(SCR, "lock-in-" + stem + ".png")
    Image.fromarray(q(img)).save(tmp)                       # the lock reads the still at the canvas size
    lp = os.path.join(SCR, "lock-" + stem + ".json")
    subprocess.run([sys.executable, os.path.join(HERE, "lock_b2.py"), tmp, os.path.join(ST, "inputs/defaults-input.png"), lp],
                   check=True, capture_output=True)
    a, b, c, used = CP.fit(json.load(open(lp)))
    H, W = size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    out = cv2.remap(img.astype(np.float32), xx + c, yy + a + b * (yy - HORIZON), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out, 0, 1).astype(np.float64), dict(file=path, y_offset_px=round(a, 3), y_scale_about_row_707=round(b, 6),
                                                       x_offset_px=round(c, 3), used=used)


def clay_local_ratio():
    """B2 / B2-plate (the clay's Cycles EXRs), blurred 3 px, divided by its own sigma-150 blur: the products' local light and shadow"""
    import prep_defaults as P
    b2, pl = P.load_exr(P.EXR + "B2.exr"), P.load_exr(P.EXR + "B2-plate.exr")
    r = blur(((b2 + 1e-4) / (pl + 1e-4)).mean(2), 3)
    return r / np.maximum(blur(r, 150), 1e-3)


def gain_field(render, base, keep):
    """per channel, linear: blur(base * keep) / blur(render * keep), sigma 60 px (normalised convolution), clamped 0.8-1.25"""
    w = keep.astype(np.float32)
    nb = cv2.GaussianBlur(w, (0, 0), 60) + 1e-6
    g = np.ones_like(render)
    for c in range(3):
        bb = cv2.GaussianBlur((lin(base[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        rr = cv2.GaussianBlur((lin(render[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        g[..., c] = np.clip(bb / np.maximum(rr, 1e-4), 0.8, 1.25)
    return g


def gc_cut(img, d, clay_m, zone, hard_bg, prior):
    H, W = d.shape
    ys, xs = np.nonzero(zone)
    y0, y1, x0, x1 = max(0, ys.min() - 12), min(H, ys.max() + 13), max(0, xs.min() - 12), min(W, xs.max() + 13)
    sl = (slice(y0, y1), slice(x0, x1))
    z, cm = zone[sl], clay_m[sl]
    seeds = (ero(cm, 4) & (d[sl] > 9)) | (prior[sl] & z)
    m = np.full(z.shape, cv2.GC_BGD, np.uint8)
    m[z] = cv2.GC_PR_BGD
    m[z & dil(cm, 2)] = cv2.GC_PR_FGD
    m[hard_bg[sl]] = cv2.GC_BGD
    seeds &= ~hard_bg[sl]
    m[seeds] = cv2.GC_FGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(q(img[sl])[..., ::-1].copy(), m, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    fg = (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)
    n, lab = cv2.connectedComponents(fg.astype(np.uint8), connectivity=8)
    keep = set(np.unique(lab[seeds & fg])) - {0}
    fg = np.isin(lab, list(keep))
    inv = (~fg).astype(np.uint8)
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    small = [i for i in range(1, n2) if stats[i, cv2.CC_STAT_AREA] < 150 and i not in border]
    fg |= np.isin(lab2, small)
    out = np.zeros((H, W), bool)
    out[sl] = fg
    return out


def soft(fg):
    a = blur(fg.astype(np.float64), 0.8)
    a = np.where(ero(fg, 1), 1.0, a)
    a[~dil(fg, 2)] = 0
    return np.clip(a, 0, 1)


def shadow_of(src, base, fg, sp, clay_shadow, block):
    rat = np.clip(blur(luma(src), 3) / np.maximum(blur(luma(base), 3), 1e-4), 0, 1)
    env = (dil(fg, sp["rim"]) | (dil(fg, sp["band"]) & dil(clay_shadow, 8))) & ~block
    s = 1 - np.maximum(0, (1 - rat) - 0.03)
    fe = np.clip(blur(env.astype(np.float64), 4) * 2, 0, 1) * env
    s = 1 - (1 - s) * fe
    s[~env] = 1
    return np.clip(s, 0, 1)


def setup(rawp, overrides):
    base = load(os.path.join(ST, "raw/plate-ungraded-bpl1.png"))
    H, W = base.shape[:2]
    render, wr = lock_and_warp(rawp, (H, W))
    ids = np.asarray(Image.open(CLAY + "B2-id.png"))
    clay = {k: np.isin(ids, v["ids"]) for k, v in SLOTS.items()}
    zones = {}
    for k, sp in SLOTS.items():
        z = dil(clay[k], sp["margin"])
        if sp.get("down"):                               # the render's towel hangs longer than the clay's: the zone runs down
            ys, xs = np.nonzero(z)
            ext = np.zeros_like(z)
            ext[ys.min():min(H, ys.max() + sp["down"]), xs.min():xs.max() + 1] = True
            z |= ext
        zones[k] = z
    cr = clay_local_ratio()
    clay_prod = np.isin(ids, list(range(40, 53)))
    clay_shadow = (cr < 0.97) & ~clay_prod
    beam = (cr > 1.05) & np.isin(ids, PLASTER + TOP)
    light_env = dil(beam, 20) & ~np.isin(ids, MIRROR)
    anyzone = np.zeros((H, W), bool)
    for k in SLOTS:
        anyzone |= dil(zones[k], SLOTS[k]["band"])
    keep = ~(anyzone | dil(light_env, 20))
    g = gain_field(render, base, keep)
    render = srgb(lin(render) * g)
    rec = dict(render=wr, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])], overrides={})
    srcs = {k: render for k in SLOTS}
    for k, op in (overrides or {}).items():
        o, wo = lock_and_warp(op, (H, W))
        go = gain_field(o, base, keep)
        srcs[k] = srgb(lin(o) * go)
        rec["overrides"][k] = dict(warp=wo, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(go, [1, 50, 99])])
    return base, ids, clay, zones, clay_shadow, light_env, srcs, rec


def alpha_for(k, src, base, clay, zones, prior_kind):
    d = np.linalg.norm(lab_of(src) - lab_of(base), axis=-1)
    hard = np.zeros(d.shape, bool)
    for o in SLOTS:
        if o != k:
            hard |= ero(clay[o], 1) & ~dil(clay[k], 3)
    return gc_cut(src, d, clay[k], zones[k], hard, prior_mask(prior_kind, src) & zones[k])


def compose_one(stack, rgba, s8):
    a = rgba[..., 3:4].astype(np.float64) / 255
    return np.rint((stack * 255 * s8[..., None] / 255) * (1 - a) + rgba[..., :3].astype(np.float64) * a) / 255


def light_one(stack, L8):
    return (255 - np.rint((255 - stack * 255) * (255 - L8.astype(np.float64)) / 255)) / 255


def frame_png(o8, path):
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    Image.fromarray(o8).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(path)


def main(rawp, overrides):
    base, ids, clay, zones, clay_shadow, light_env, srcs, rec = setup(rawp, overrides)
    H, W = base.shape[:2]
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    cv = lambda x: G.curve_apply(x, curve)[0]  # noqa: E731
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    rec["plate_png_vs_curve_of_base"] = dict(max=int(np.abs(q(cv(base)).astype(int) - plate8.astype(int)).max()),
                                             px=int((np.abs(q(cv(base)).astype(int) - plate8.astype(int)).max(2) > 0).sum()))
    order = sorted(SLOTS, key=lambda k: SLOTS[k]["z"])
    fg = {k: alpha_for(k, srcs[k], base, clay, zones, SLOTS[k]["prior"]) for k in order}
    alpha = {k: soft(fg[k]) for k in order}
    prod = np.zeros((H, W), bool)
    for k in order:
        prod |= alpha[k] > 0
    shadow = {k: shadow_of(srcs[k], base, fg[k], SLOTS[k], clay_shadow, dil(prod, 1)) for k in order}
    stack_u, stack_g = base.copy(), plate8.astype(np.float64) / 255
    s_g, rgb_g = {}, {}
    for k in order:
        s = shadow[k]
        m = s < 1
        sg = np.ones((H, W))
        if m.any():
            below = stack_u[m]
            sg[m] = np.clip(cv(below * s[m][:, None]).mean(1) / np.maximum(cv(below).mean(1), 1e-4), 0, 1)
        s_g[k] = sg
        rgb_g[k] = cv(srcs[k])
        a = alpha[k][..., None]
        stack_u = stack_u * s[..., None]
        stack_u = stack_u * (1 - a) + srcs[k] * a
        stack_g = stack_g * sg[..., None]
        stack_g = stack_g * (1 - a) + rgb_g[k] * a
    render = srcs["vanity-sconces"]
    lenv = light_env & ~dil(prod, 1)
    Lu = np.where(lenv[..., None] & (render > stack_u), 1 - (1 - render) / np.maximum(1 - stack_u, 1e-3), 0.0)
    Lu = np.clip(blur(np.clip(Lu, 0, 1), 2) - 0.01, 0, 1)
    fe = np.clip(blur(lenv.astype(np.float64), 10) * 2, 0, 1) * lenv
    Lu = Lu * fe[..., None]
    tgt = cv(1 - (1 - stack_u) * (1 - Lu))
    Lg = np.clip(np.where(lenv[..., None], 1 - (1 - tgt) / np.maximum(1 - stack_g, 1e-3), 0.0), 0, 1)
    write_set(order, alpha, s_g, rgb_g, Lg, plate8, rec, rawp, overrides, H, W, fg)


def write_set(order, alpha, s_g, rgb_g, Lg, plate8, rec, rawp, overrides, H, W, fg):
    man = dict(id="wm-bath-b2-layers-2026-11-18", room="bath", style="warm-modern", frame="B2", canvas=[W, H],
               frame_box=[round(v, 2) for v in FRAME], base="plate.png (graded, WM-G1 round 3), byte for byte",
               color="8-bit sRGB, no ICC profile; blending on the sRGB-encoded values",
               compose=dict(order=["base"] + [f"{k}-shadow, {k}" for k in order] + ["light (screen)"],
                            formula="for each product in z order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, "
                                    "straight alpha; then the light: out = 255 - round((255 - out) * (255 - L) / 255)",
                            swap_region="per product: alpha > 0 or shadow < 255; a product changes nothing outside its region"),
               grade="every layer is cut from the graded composite (plate-grade.json, round 3); the site applies no further grade",
               cut="tools/compose_defaults.py v2 (GrabCut in the slot zone, clay-bounded shadows, clay-bounded light)", layers=[])
    rec_stack = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    for k in order:
        sp = SLOTS[k]
        a8 = q(alpha[k])
        rgba = np.dstack([q(rgb_g[k]), a8])
        rgba[..., :3][a8 == 0] = 0
        s8 = q(s_g[k])
        lp = os.path.join(ST, "layers", k, sp["pid"] + ".png")
        sh = os.path.join(ST, "shadows", k, sp["pid"] + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sh), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(lp)
        Image.fromarray(s8).save(sh)
        rec_stack = compose_one(rec_stack, rgba, s8)
        r = (a8 > 0) | (s8 < 255)
        region |= r
        ys, xs = np.nonzero(r)
        man["layers"].append(dict(slot=k, product=sp["pid"], z=sp["z"], default=True, layer=os.path.relpath(lp, ST),
                                  shadow=os.path.relpath(sh, ST), shadow_z=sp["z"] - 1, alpha_px=int((a8 > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
    L8 = q(Lg)
    lpth = os.path.join(ST, "light", LIGHT_PID + ".png")
    os.makedirs(os.path.dirname(lpth), exist_ok=True)
    Image.fromarray(L8).save(lpth)
    out = light_one(rec_stack, L8)
    region |= L8.max(2) > 0
    man["light"] = dict(product=LIGHT_PID, file=os.path.relpath(lpth, ST), z=90, blend="screen", px=int((L8.max(2) > 0).sum()),
                        note="the beams on the plaster and the stone top only; the light that falls on a product is in that product's own layer")
    o8 = q(out)
    Image.fromarray(o8).save(os.path.join(ST, "b2-defaults.png"))
    frame_png(o8, os.path.join(ST, "b2-defaults-frame.png"))
    diff_out = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=diff_out,
                       rule="outside every alpha, shadow and light: plate.png, pixel for pixel")
    man["variants"] = []
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    rec.update(raw=rawp, edits=overrides, alpha_px={k: int((alpha[k] > 0).sum()) for k in order}, light_px=man["light"]["px"],
               rnd2=man["rnd2"])
    json.dump(rec, open(os.path.join(ST, "b2-defaults-compose.json"), "w"), indent=1)
    os.makedirs(os.path.join(SCR, "npz"), exist_ok=True)
    np.savez_compressed(os.path.join(SCR, "npz", "defaults-fg.npz"), **{k: fg[k] for k in order})
    print(json.dumps(man["rnd2"]), json.dumps(rec["gain_p1_p50_p99"]), json.dumps(rec["plate_png_vs_curve_of_base"]),
          {k: (v["warp"]["y_offset_px"], v["warp"]["x_offset_px"]) for k, v in rec["overrides"].items()})


def variant(rawp, slot, vpath, pid, name):
    """the variant's layer and shadow, from its own render; every other file from the defaults run"""
    man = json.load(open(os.path.join(ST, "layers", "manifest.json")))
    base, ids, clay, zones, clay_shadow, light_env, srcs, rec = setup(rawp, {slot: vpath})
    H, W = base.shape[:2]
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    src = srcs[slot]
    others = np.zeros((H, W), bool)
    files = {}
    for l in man["layers"]:
        rgba = np.asarray(Image.open(os.path.join(ST, l["layer"])))
        files[l["slot"]] = (rgba, np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
        if l["slot"] != slot:
            others |= rgba[..., 3] > 0
    fgv = alpha_for(slot, src, base, clay, zones, None)   # no colour prior: the variant's colour is its own
    a = soft(fgv)
    s = shadow_of(src, base, fgv, SLOTS[slot], clay_shadow, dil(others | (a > 0), 1))
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    stack = plate8.astype(np.float64) / 255
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        if l["slot"] != slot and l["z"] < SLOTS[slot]["z"]:
            stack = compose_one(stack, *files[l["slot"]])
    under_knee = int((G.to_lab(stack)[..., 0][s < 1] < curve["knee"] + 2).sum())
    sg = s.copy()                                          # above the knee the curve is the identity: the graded ratio is s
    rgb = G.curve_apply(src, curve)[0]
    a8 = q(a)
    rgba = np.dstack([q(rgb), a8])
    rgba[..., :3][a8 == 0] = 0
    s8 = q(sg)
    lp = os.path.join(ST, "layers", slot, pid + ".png")
    sh = os.path.join(ST, "shadows", slot, pid + ".png")
    Image.fromarray(rgba, "RGBA").save(lp)
    Image.fromarray(s8).save(sh)
    out = plate8.astype(np.float64) / 255
    region = np.zeros((H, W), bool)
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        pair = (rgba, s8) if l["slot"] == slot else files[l["slot"]]
        out = compose_one(out, *pair)
        region |= (pair[0][..., 3] > 0) | (pair[1] < 255)
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    out = light_one(out, L8)
    region |= L8.max(2) > 0
    o8 = q(out)
    Image.fromarray(o8).save(os.path.join(ST, name + ".png"))
    frame_png(o8, os.path.join(ST, name + "-frame.png"))
    diff_out = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    dflt = np.asarray(Image.open(os.path.join(ST, "b2-defaults.png")).convert("RGB"))
    sw = (a8 > 0) | (s8 < 255) | (files[slot][0][..., 3] > 0) | (files[slot][1] < 255)
    diff_vs_defaults = int((np.abs(o8.astype(int) - dflt.astype(int)).max(2)[~sw] > 0).sum())
    lit_on_variant = L8.max(2)[(a8 > 0) & (files[slot][0][..., 3] == 0)]
    uncovered = L8.max(2)[(a8 == 0) & (files[slot][0][..., 3] > 0)]
    v = dict(slot=slot, product=pid, z=SLOTS[slot]["z"], default=False, layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sh, ST),
             composite=name + ".png", alpha_px=int((a8 > 0).sum()), shadow_px=int((s8 < 255).sum()),
             shadow_px_under_knee=under_knee, outside_differing_px_vs_plate=diff_out,
             differing_px_vs_defaults_outside_the_swap_region=diff_vs_defaults,
             light_on_the_variant_outside_the_default=dict(px=int(lit_on_variant.size), max=int(lit_on_variant.max()) if lit_on_variant.size else 0),
             light_hole_where_the_default_was=dict(px=int(uncovered.size), max=int(uncovered.max()) if uncovered.size else 0),
             render=rec["overrides"][slot])
    man["variants"] = [x for x in man.get("variants", []) if x["product"] != pid] + [v]
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    np.save(os.path.join(SCR, "npz", f"variant-{slot}-fg.npy"), fgv)
    print(json.dumps({k: v[k] for k in v if k != "render"}))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--variant" in args:
        i = args.index("--variant")
        slot, vpath = args[i + 1].split("=", 1)
        variant(args[0], slot, vpath, args[args.index("--pid") + 1], args[args.index("--name") + 1])
    else:
        main(args[0], dict(a.split("=", 1) for a in args[1:]))
