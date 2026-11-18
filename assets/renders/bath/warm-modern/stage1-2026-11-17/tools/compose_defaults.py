#!/usr/bin/env python3
"""
compose_defaults.py: B2 with the defaults (output 2) and its layers, from the model's render (render-agent, 2026-11-18). 0 tokens.
As the living room's extract.py, adapted to the bath:
  1. lock: the render's lines against the input's (tools/lock_b2.py, the clay's named lines), one global warp (y about the horizon,
     x constant), as the plate;
  2. tone match: a smooth gain field (normalised blur, sigma 60 px, per channel, linear light) of base / render, measured OUTSIDE every
     product zone, light zone and shadow band, applied to the render, so the products sit in the plate's exposure;
  3. per slot, the cut: inside the slot's zone (the clay mask grown by its margin), the clay core (eroded 2 px) plus the pixels where
     the render changed colour or texture against the base (dE76 over 9) and that are NOT a plain darkening (a shadow); only components
     touching the clay core; holes filled; a 1 px soft edge;
  4. per slot, the shadow (multiply, grey): the render's darkening of the base in a band round the product, outside every product
     (luminance ratio, a soft floor: under 2 % is grain);
  5. the light of the sconce pair (screen, z 90): where the render is brighter than the base in the light zone (the clay's local light
     ratio over 1.08, grown 24 px), outside every product: L = 1 - (1 - render) / (1 - base);
  6. the composite, UNGRADED: base x shadows, products over it in the z order, the light screened on top; outside every alpha, shadow
     and light the base pixel for pixel. Then the WM-G1 curve (plate-grade.json) on the composite; the layers are cut from the GRADED
     composite against the graded plate, and the graded defaults are recomposed from them, so the file and the layers agree.
Writes b2-defaults.png, b2-defaults-frame.png, layers/<slot>/<product>.png, shadows/<slot>/<product>.png, light/<product>.png,
layers/manifest.json and b2-defaults-compose.json.

  python3 compose_defaults.py raw/defaults-r1.png
"""
import json
import os
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
# slot: clay ids, zone margin px, shadow band px, z, product id (the layer's file name)
SLOTS = {
    "shower-curtain": dict(ids=(40,), margin=26, band=30, z=26, pid="shower-curtain-aliexpress-linen-blend-slub-panel-200x270"),
    "shower-dispensers": dict(ids=(41,), margin=8, band=10, z=14, pid="shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle"),
    "vanity-sconces": dict(ids=(42, 43), margin=10, band=6, z=14, pid="vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853"),
    "floor-planter": dict(ids=(51, 52), margin=40, band=36, z=30, pid="planter-cj-cement-ribbed-belly-beige-medium"),
    "soap-dispenser": dict(ids=(44,), margin=8, band=12, z=46, pid="soap-dispenser-cj-sand-ribbed-ceramic-pump-bottle"),
    "toothbrush-cup": dict(ids=(45, 46), margin=10, band=12, z=46, pid="toothbrush-cup-cj-silver-travertine-cup"),
    "vanity-vase": dict(ids=(47, 48), margin=12, band=12, z=46, pid="vanity-vase-cj-matte-black-pottery-bud-vase-10"),
    "towel-ring": dict(ids=(49,), margin=8, band=10, z=50, pid="towel-ring-aliexpress-1-2pcs-bathroom-towel-842335-a3"),
    "hand-towel": dict(ids=(50,), margin=14, band=26, z=52, pid="hand-towel-aliexpress-pure-linen-towel-38x55-caramel"),
}
LIGHT_PID = "vanity-sconces-aliexpress-wabi-sabi-yellow-marble-037853"


def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def dil(m, r):
    return m.astype(bool) if r <= 0 else cv2.dilate(m.astype(np.uint8), disk(r)).astype(bool)


def ero(m, r):
    return m.astype(bool) if r <= 0 else cv2.erode(m.astype(np.uint8), disk(r)).astype(bool)


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64) / 255


def save(a, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Image.fromarray(np.clip(np.rint(a * 255), 0, 255).astype(np.uint8)).save(p)


def warp(img, lockp, lt_path):
    sys.path.insert(0, HERE)
    import compose_plate as CP
    a, b, c, used = CP.fit(json.load(open(lockp)))
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    out = cv2.remap(img.astype(np.float32), xx + c, yy + a + b * (yy - HORIZON), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return np.clip(out, 0, 1).astype(np.float64), dict(y_offset_px=round(a, 3), y_scale_about_row_707=round(b, 6), x_offset_px=round(c, 3), used=used)


def light_zone():
    """the clay's local light ratio (as prep_defaults) over 1.08, grown 24 px"""
    import prep_defaults as P
    b2, pl = P.load_exr(P.EXR + "B2.exr"), P.load_exr(P.EXR + "B2-plate.exr")
    r = cv2.GaussianBlur(((b2 + 1e-4) / (pl + 1e-4)).astype(np.float32), (0, 0), 3).astype(np.float64).mean(2)
    wide = cv2.GaussianBlur(r.astype(np.float32), (0, 0), 150).astype(np.float64)
    r = r / np.maximum(wide, 1e-3)
    ids = np.asarray(Image.open(CLAY + "B2-id.png"))
    vanity_wall = np.isin(ids, (1, 5, 17, 18, 20, 21, 22, 23, 24, 25)) | np.isin(ids, (42, 43, 44, 45, 46, 47, 48, 49, 50))
    return dil((r > 1.08) & vanity_wall, 24)


def gain_field(render, base, keep):
    """per channel, linear: blur(base * keep) / blur(render * keep), sigma 60 px (normalised convolution)"""
    w = keep.astype(np.float32)
    nb = cv2.GaussianBlur(w, (0, 0), 60) + 1e-6
    g = np.ones_like(render)
    for c in range(3):
        bb = cv2.GaussianBlur((lin(base[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        rr = cv2.GaussianBlur((lin(render[..., c]) * w).astype(np.float32), (0, 0), 60) / nb
        g[..., c] = np.clip(bb / np.maximum(rr, 1e-4), 0.8, 1.25)
    return g


def cut(render, base, clay_m, zone, others):
    lab_r, lab_b = G.to_lab(render), G.to_lab(base)
    d = np.linalg.norm(lab_r - lab_b, axis=-1)
    Lr, Lb = lab_r[..., 0], lab_b[..., 0]
    cr = np.hypot(lab_r[..., 1], lab_r[..., 2])
    cb = np.hypot(lab_b[..., 1], lab_b[..., 2])
    # a plain darkening (a shadow): lighter than 35 % of the base, darker than 97 %, chroma within 6 of the base's (scaled)
    ratio = (Lr + 1) / (Lb + 1)
    shadowlike = (ratio > 0.45) & (ratio < 0.97) & (np.abs(cr - cb * ratio) < 6)
    core = ero(clay_m, 2)
    fg = core | (zone & (d > 9) & ~shadowlike)
    fg &= ~others
    n, lab = cv2.connectedComponents(fg.astype(np.uint8))
    keep_ids = set(np.unique(lab[core & fg])) - {0}
    fg = np.isin(lab, list(keep_ids))
    # fill holes inside the silhouette
    inv = (~fg).astype(np.uint8)
    n2, lab2 = cv2.connectedComponents(inv)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])))
    holes = ~np.isin(lab2, list(border)) & (inv > 0)
    fg |= holes & zone
    a = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 0.8).astype(np.float64)
    a = np.where(ero(fg, 1), 1.0, a)
    a[~dil(fg, 2)] = 0
    return np.clip(a, 0, 1), d


def main(rawp):
    base = load(os.path.join(ST, "raw/plate-ungraded-bpl1.png"))
    inp = load(os.path.join(ST, "inputs/defaults-input.png"))
    raw = load(rawp)
    H, W = base.shape[:2]
    if raw.shape[:2] != (H, W):
        raw = cv2.resize(raw.astype(np.float32), (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float64)
    # 1. lock against the input
    lockp = os.path.join(SCR, "lock-defaults-r1.json")
    os.system(f"python3 {HERE}/lock_b2.py {rawp} {os.path.join(ST, 'inputs/defaults-input.png')} {lockp} > /dev/null")
    render, wrec = warp(raw, lockp, None)
    ids = np.asarray(Image.open(CLAY + "B2-id.png"))
    clay = {k: np.isin(ids, v["ids"]) for k, v in SLOTS.items()}
    zones = {k: dil(clay[k], SLOTS[k]["margin"]) for k in SLOTS}
    bands = {k: dil(clay[k], SLOTS[k]["margin"] + SLOTS[k]["band"]) for k in SLOTS}
    lz = light_zone()
    anyzone = np.zeros((H, W), bool)
    for k in SLOTS:
        anyzone |= bands[k]
    # 2. tone match outside every zone
    g = gain_field(render, base, ~(anyzone | lz))
    render = srgb(lin(render) * g)
    # 3. cuts, in z order (a nearer product removes itself from the ones below: the towel over the ring)
    order = sorted(SLOTS, key=lambda k: SLOTS[k]["z"])
    alpha = {}
    for k in order:
        others = np.zeros((H, W), bool)
        for o in SLOTS:
            if o != k and SLOTS[o]["z"] > SLOTS[k]["z"]:
                others |= ero(clay[o], 1)
        alpha[k], _ = cut(render, base, clay[k], zones[k], others)
    allA = np.zeros((H, W))
    for k in order:
        allA = np.maximum(allA, alpha[k])
    prod = allA > 0
    # 4. shadows (grey multiply), outside every product
    Yr = lin(render) @ [0.2126, 0.7152, 0.0722]
    Yb = lin(base) @ [0.2126, 0.7152, 0.0722]
    rat = np.clip(cv2.GaussianBlur((Yr / np.maximum(Yb, 1e-4)).astype(np.float32), (0, 0), 1.5).astype(np.float64), 0, 1)
    shadow = {}
    for k in order:
        band = bands[k] & ~dil(prod, 1) & ~lz
        s = np.ones((H, W))
        dark = band & (rat < 0.98)
        s[dark] = rat[dark]
        s = np.where(s > 0.98, 1.0, s)
        s = cv2.GaussianBlur(s.astype(np.float32), (0, 0), 1.0).astype(np.float64)
        s[~band] = 1.0
        shadow[k] = np.clip(s, 0, 1)
    # 5. the light of the pair (screen), outside every product
    lzone = lz & ~dil(prod, 1)
    Lgt = np.zeros((H, W, 3))
    brighter = lzone[..., None] & (render > base + 1.0 / 255)
    Lgt = np.where(brighter, 1 - (1 - render) / np.maximum(1 - base, 1e-3), 0.0)
    Lgt = np.clip(Lgt, 0, 1)
    Lgt = cv2.GaussianBlur(Lgt.astype(np.float32), (0, 0), 1.0).astype(np.float64) * lzone[..., None]
    # 6. the ungraded composite, then the grade, then the layers from the graded composite
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    comp = base.copy()
    for k in order:
        comp = comp * shadow[k][..., None]
        comp = comp * (1 - alpha[k][..., None]) + render * alpha[k][..., None]
    comp = 1 - (1 - comp) * (1 - Lgt)
    comp_g, _ = G.curve_apply(comp, curve)
    plate_g, _ = G.curve_apply(base, curve)
    # layers in the graded domain: product RGB = graded composite under its alpha; shadow = graded ratio (grey) in the band;
    # light = the screen solve on the graded files
    out_layers = {}
    Ypg = lin(plate_g) @ [0.2126, 0.7152, 0.0722]
    stack = plate_g.copy()
    for k in order:
        s_g = np.ones((H, W))
        m = shadow[k] < 1
        if m.any():
            below = lin(stack) @ [0.2126, 0.7152, 0.0722]
            tgt = lin(comp_g) @ [0.2126, 0.7152, 0.0722]
            s_g[m] = np.clip(srgb(np.clip(tgt[m] / np.maximum(below[m], 1e-4), 0, 1) * below[m]) / np.maximum(srgb(below[m]), 1e-4), 0, 1)
        stack = stack * s_g[..., None]
        a = alpha[k]
        stack = stack * (1 - a[..., None]) + comp_g * a[..., None]
        out_layers[k] = (a, s_g)
    Lg = np.zeros((H, W, 3))
    m = lzone[..., None] & (comp_g > stack + 0.5 / 255)
    Lg = np.where(m, 1 - (1 - comp_g) / np.maximum(1 - stack, 1e-3), 0.0)
    Lg = np.clip(Lg, 0, 1) * lzone[..., None]
    final = 1 - (1 - stack) * (1 - Lg)
    # 8-bit files, and the recomposition from the 8-bit files (what the engine does)
    q = lambda x: np.clip(np.rint(x * 255), 0, 255).astype(np.uint8)  # noqa: E731
    man = dict(id="wm-bath-b2-layers-2026-11-18", room="bath", style="warm-modern", frame="B2", canvas=[W, H],
               frame_box=[round(v, 2) for v in FRAME], base="plate.png (graded, WM-G1 round 3)",
               compose=dict(order=["base"] + [f"{k}-shadow, {k}" for k in order] + ["light (screen)"],
                            formula="for each product in z order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255; "
                                    "then the light: out = 255 - (255 - out) * (255 - L) / 255"),
               grade="every layer is cut from the graded composite (plate-grade.json, round 3); the site applies no further grade", layers=[])
    rec_stack = q(plate_g).astype(np.float64) / 255
    for k in order:
        a, s_g = out_layers[k]
        sp = SLOTS[k]
        rgba = np.dstack([q(comp_g), q(a)])
        lp = os.path.join(ST, "layers", k, sp["pid"] + ".png")
        sh = os.path.join(ST, "shadows", k, sp["pid"] + ".png")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        os.makedirs(os.path.dirname(sh), exist_ok=True)
        rgba[..., :3][rgba[..., 3] == 0] = 0
        Image.fromarray(rgba, "RGBA").save(lp)
        Image.fromarray(q(s_g)).save(sh)
        a8 = rgba[..., 3].astype(np.float64) / 255
        s8 = q(s_g).astype(np.float64) / 255
        rec_stack = rec_stack * s8[..., None]
        rec_stack = rec_stack * (1 - a8[..., None]) + rgba[..., :3].astype(np.float64) / 255 * a8[..., None]
        man["layers"].append(dict(slot=k, product=sp["pid"], z=sp["z"], layer=os.path.relpath(lp, ST), shadow=os.path.relpath(sh, ST),
                                  alpha_px=int((rgba[..., 3] > 0).sum()), shadow_px=int((q(s_g) < 255).sum())))
    lpth = os.path.join(ST, "light", LIGHT_PID + ".png")
    os.makedirs(os.path.dirname(lpth), exist_ok=True)
    Image.fromarray(q(Lg)).save(lpth)
    L8 = q(Lg).astype(np.float64) / 255
    rec = 1 - (1 - rec_stack) * (1 - L8)
    man["light"] = dict(product=LIGHT_PID, file=os.path.relpath(lpth, ST), z=90, blend="screen", px=int((q(Lg).max(2) > 0).sum()))
    save(rec, os.path.join(ST, "b2-defaults.png"))
    x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
    Image.fromarray(q(rec)).crop((x0, y0, x1, y1)).resize((1920, 1080), Image.LANCZOS).save(os.path.join(ST, "b2-defaults-frame.png"))
    region = (allA > 0)
    for k in order:
        region |= out_layers[k][1] < 1
    region |= Lg.max(2) > 0
    plate8 = q(plate_g)
    outside = ~region
    diff_out = int((np.abs(q(rec).astype(int) - plate8.astype(int)).max(2)[outside] > 0).sum())
    man["rnd2"] = dict(region_px=int(region.sum()), outside_differing_px=diff_out, rule="outside every alpha, shadow and light: the plate, pixel for pixel")
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1)
    resid = np.abs(q(rec).astype(int) - q(final).astype(int)).max(2)
    json.dump(dict(raw=rawp, warp=wrec, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])],
                   alpha_px={k: int((alpha[k] > 0).sum()) for k in order}, light_px=man["light"]["px"],
                   recompose_vs_direct=dict(max=int(resid.max()), p99=float(np.percentile(resid, 99))), rnd2=man["rnd2"]),
              open(os.path.join(ST, "b2-defaults-compose.json"), "w"), indent=1)
    print(json.dumps(man["rnd2"]), "warp", wrec, "resid max", int(resid.max()))


if __name__ == "__main__":
    main(sys.argv[1])
