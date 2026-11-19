#!/usr/bin/env python3
"""
compose_b1_defaults.py: the B1 defaults render cut into layers (RND2), render-agent, 2026-11-19. 0 tokens. As B2's compose_defaults.py
and compose_fb10.py (the same helpers, imported):
  1. lock: the render against its own input (lock_b1.py: B2's lock_b2 on the B1 clay lines), one global warp;
  2. tone match: a smooth gain field (sigma 60 px, per channel, linear) of base / render, outside every product zone, the beam
     envelope and the fluted glass: the products sit in the plate's exposure;
  3. each product: GrabCut in its zone (the clay's mask, as placed in the input, grown), seeded where the render differs from the
     base; its shadow is the render's darkening round it (contact rim + a band bounded by the clay's own shadow); z and pid per slot;
  4. the light of the B1 sconce (screen, z 90): where the render is brighter than the stack, inside the clay's beam envelope only
     (local ratio over 1.05 on the plaster, round the lamp), never on a product;
  5. the WM-G1 grade on every file (plate-grade.json's curve, grade_plate.curve_apply); the light solved again on the graded stack;
     the composites recomposed from the files on plate.png (RND2: outside every alpha, shadow and light, plate.png byte for byte).

  python3 compose_b1_defaults.py raw/defaults-r1.png
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.dirname(HERE)
B2T = "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools"
sys.path.insert(0, B2T)
sys.path.insert(0, HERE)
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402
import prep_defaults as PD  # noqa: E402
import lock_b1 as LK  # noqa: E402

CLAY = "/home/user/homedesign-app/assets/blockout/house/framing/wm-bath-b1-2026-11-19/"
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath/b1/"
SHIFT = {59: (-8, -3), 57: (0, -3), 58: (0, -3)}
CARD = "data/products/bath/"
SLOTS = {
    "shower-dispensers": dict(ids=(41,), z=14, band=12, rim=4, margin=14, pid="shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle",
                              card=CARD + "shower-dispensers/shower-dispensers-cj-sand-ribbed-ceramic-pump-bottle.json", sku="CJYD301460604DW"),
    "wall-sconce": dict(ids=(60,), z=14, band=10, rim=4, margin=12, pid="wall-sconce-aliexpress-wabi-sabi-yellow-marble-037853",
                        card=CARD + "wall-sconce/wall-sconce-aliexpress-wabi-sabi-yellow-marble-037853.json", sku="12000048654610384"),
    "bath-mat": dict(ids=(53,), z=18, band=24, rim=8, margin=30, pid="bath-mat-cj-tufted-cotton-frame-beige-40x60-khaki",
                     card=CARD + "bath-mat/bath-mat-cj-tufted-cotton-frame-beige-40x60.json", sku="CJYD289719807GT"),
    "shower-curtain": dict(ids=(40,), z=26, band=60, rim=8, margin=40, pid="shower-curtain-aliexpress-linen-blend-slub-panel-200x270",
                           card=CARD + "shower-curtain/shower-curtain-aliexpress-linen-blend-slub-panel-200x270.json", sku="12000059196236303"),
    "floor-planter": dict(ids=(51, 52), z=30, band=40, rim=10, margin=40, pid="planter-cj-cement-ribbed-belly-beige-medium",
                          card="data/products/planter/planter-cj-cement-ribbed-belly.json", sku="CJJT154204208HS"),
    "bin": dict(ids=(55,), z=42, band=30, rim=8, margin=24, pid="bin-cj-bent-walnut-round-swing-lid-walnut-swing-lid",
                card=CARD + "bin/bin-cj-bent-walnut-round-swing-lid.json", sku="CJJT102413505EV"),
    "toilet-paper-stand": dict(ids=(54, 61), z=44, band=24, rim=6, margin=20, pid="toilet-paper-stand-aliexpress-matte-black-freestanding-toilet-paper-stand-with-black",
                               card=CARD + "toilet-paper-stand/toilet-paper-stand-aliexpress-matte-black-freestanding-toilet-paper-stand-with.json", sku="12000053061878471"),
    "window-sill-vase": dict(ids=(59,), z=46, band=16, rim=6, margin=16, pid="vase-cj-black-matte-stoneware-jar-30-style4",
                             card="data/products/vase/vase-cj-black-matte-stoneware-jar-30.json", sku="CJJT198137605EV"),
    "candle": dict(ids=(57,), z=46, band=12, rim=5, margin=12, pid="candle-cj-ribbed-matte-ceramic-candle-cup-9-white",
                   card=CARD + "candle/candle-cj-ribbed-matte-ceramic-candle-cup-9.json", sku="CJJT120250201AZ"),
    "reed-diffuser": dict(ids=(58,), z=46, band=12, rim=5, margin=14, pid="reed-diffuser-cj-travertine-look-bamboo-lid-milktea",
                          card=CARD + "reed-diffuser/reed-diffuser-cj-travertine-look-bamboo-lid-milktea.json", sku="milk-tea"),
    "toilet-brush": dict(ids=(56,), z=48, band=16, rim=5, margin=14, pid="toilet-brush-cj-fluted-ceramic-holder-black-handle-light-color",
                         card=CARD + "toilet-brush/toilet-brush-cj-fluted-ceramic-holder-black-handle.json", sku="CJYD254508501AZ"),
}
LIGHT_SLOT = "wall-sconce"
PLASTER = (1, 2, 3, 4)


def masks(ids):
    H, W = ids.shape
    out = {}
    for k, s in SLOTS.items():
        m = np.zeros((H, W), bool)
        for g in s["ids"]:
            mg = ids == g
            dx, dy = SHIFT.get(g, (0, 0))
            if dx or dy:
                mg = cv2.warpAffine(mg.astype(np.uint8), np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), flags=cv2.INTER_NEAREST) > 0
            m |= mg
        out[k] = m
    return out


def keep_components(fg, seeds):
    n, lab = cv2.connectedComponents(fg.astype(np.uint8), connectivity=8)
    keep = set(np.unique(lab[seeds & fg])) - {0}
    return np.isin(lab, list(keep)) if keep else fg


def graded_shadow(s, below, cv):
    sg = np.ones(s.shape)
    m = s < 1
    if m.any():
        b = below[m]
        sg[m] = np.clip(cv(b * s[m][:, None]).mean(1) / np.maximum(cv(b).mean(1), 1e-4), 0, 1)
    return sg


def stack(plate, layers, order, light=None):
    out = plate.astype(np.float64) / 255
    for k in order:
        out = C.compose_one(out, *layers[k])
    if light is not None:
        out = C.light_one(out, light)
    return out


def main(rawp):
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    cv = lambda x: G.curve_apply(x, curve)[0]  # noqa: E731
    base = np.asarray(Image.open(os.path.join(ST, "raw", "plate-relit.png")).convert("RGB")).astype(np.float64) / 255
    plate8 = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    H, W = base.shape[:2]
    ids = np.asarray(Image.open(CLAY + "B1-id.png"))
    M = masks(ids)
    allm = np.zeros((H, W), bool)
    for m in M.values():
        allm |= m
    rec = {}
    # 1. lock against the input
    raw = C.load(os.path.join(ST, rawp), (H, W))
    tmp = SCR + "defaults-in.png"
    Image.fromarray(C.q(raw)).save(tmp)
    a_, b_, c_, used = LK.lock(tmp, os.path.join(ST, "inputs", "defaults-input.png"), SCR + "defaults-lock.json")
    src = LK.warp(raw, a_, b_, c_)
    rec["lock"] = dict(y_offset_px=round(a_, 3), y_scale_about_row_707=round(b_, 6), x_offset_px=round(c_, 3), used=used)
    # the clay's local light (beams, shadows) for the envelopes
    b1, pl = PD.load_exr(PD.EXR + "B1.exr"), PD.load_exr(PD.EXR + "B1-plate.exr")
    ra = cv2.GaussianBlur(((b1 + 1e-4) / (pl + 1e-4)).mean(2).astype(np.float32), (0, 0), 3).astype(np.float64)
    clay_shadow = ra < 0.97
    sc = M[LIGHT_SLOT]
    ys, xs = np.nonzero(sc)
    near = np.zeros((H, W), bool)
    near[max(0, ys.min() - 420):ys.max() + 420, max(0, xs.min() - 220):xs.max() + 220] = True
    beam = (ra > 1.05) & np.isin(ids, PLASTER + (5,)) & near
    light_env = C.dil(beam, 30) & ~C.dil(allm, 2) & near
    glass = C.dil(ids == 31, 12)
    # 2. tone match
    keep = ~C.dil(allm, 60) & ~C.dil(light_env, 20) & ~glass & ~C.dil(clay_shadow & C.dil(allm, 80), 10)
    g = C.gain_field(src, base, keep)
    src = C.srgb(C.lin(src) * g)
    rec["gain_p1_p50_p99"] = [round(float(v), 3) for v in np.percentile(g, [1, 50, 99])]
    # 3. the cuts
    d = np.linalg.norm(C.lab_of(src) - C.lab_of(base), axis=-1)
    fg = {}
    order = sorted(SLOTS, key=lambda k: (SLOTS[k]["z"], k))
    for k in order:
        s = SLOTS[k]
        m = M[k]
        zone = C.dil(m, s["margin"])
        hard = np.zeros((H, W), bool)
        for o in SLOTS:
            if o != k:
                hard |= C.ero(M[o], 2) & ~C.dil(m, 2)
        sure = C.ero(m, 3) & (d > 6)
        if sure.sum() < 30:
            sure = C.ero(m, 2)
        f = C.gc_cut(src, sure, C.dil(m, 3), zone, hard)
        fg[k] = keep_components(f, sure)
        rec.setdefault("cut", {})[k] = dict(clay_px=int(m.sum()), alpha_px=int(fg[k].sum()), sure_px=int(sure.sum()))
    np.savez_compressed(SCR + "b1-fg.npz", **{k.replace("-", "_"): v for k, v in fg.items()})
    allfg = np.zeros((H, W), bool)
    for k in order:
        allfg |= fg[k]
    # 4. layers and shadows, graded
    layers, files = {}, {}
    os.makedirs(os.path.join(ST, "layers"), exist_ok=True)
    os.makedirs(os.path.join(ST, "shadows"), exist_ok=True)
    for k in order:
        s = SLOTS[k]
        oth = allfg & ~fg[k]
        sh = C.shadow_of(src, base, fg[k], dict(band=s["band"], rim=s["rim"]), clay_shadow, C.dil(oth, 1))
        a = C.soft(fg[k])
        rgb = cv(C.defringe(src, fg[k]))
        sg = graded_shadow(sh, base, cv)
        a8 = C.q(a)
        rgba = np.dstack([C.q(rgb), a8])
        rgba[..., :3][a8 == 0] = 0
        s8 = C.q(sg)
        lp = os.path.join("layers", k, s["pid"] + ".png")
        spth = os.path.join("shadows", k, s["pid"] + ".png")
        os.makedirs(os.path.join(ST, "layers", k), exist_ok=True)
        os.makedirs(os.path.join(ST, "shadows", k), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(os.path.join(ST, lp))
        Image.fromarray(s8).save(os.path.join(ST, spth))
        layers[k] = (rgba, s8)
        files[k] = (lp, spth)
    # 5. the light (screen), on the graded stack
    st_g = stack(plate8, layers, order)
    srcg = cv(src)
    Lg = 1 - (1 - srcg) / np.maximum(1 - st_g, 1e-3)
    Lg = np.clip(C.blur(Lg, 2.0) if Lg.ndim == 2 else np.stack([C.blur(Lg[..., i], 2.0) for i in range(3)], -1), 0, 1)
    fe = np.clip(C.blur(light_env.astype(np.float64), 10), 0, 1) * light_env
    Lg = Lg * fe[..., None]
    Lg[Lg.max(2) < 0.01] = 0
    L8 = C.q(Lg)
    os.makedirs(os.path.join(ST, "light"), exist_ok=True)
    lpth = os.path.join("light", SLOTS[LIGHT_SLOT]["pid"] + ".png")
    Image.fromarray(L8).save(os.path.join(ST, lpth))
    # 6. the composite from the files, RND2
    o = stack(plate8, layers, order, L8)
    o8 = C.q(o)
    Image.fromarray(o8).save(os.path.join(ST, "b1-defaults.png"))
    C.frame_png(o8, os.path.join(ST, "b1-defaults-frame.png"))
    region = L8.max(2) > 0
    for k in order:
        region |= (layers[k][0][..., 3] > 0) | (layers[k][1] < 255)
    rnd2 = int((np.abs(o8.astype(int) - plate8.astype(int)).max(2)[~region] > 0).sum())
    man = dict(frame="B1", room="bath", style="warm-modern", date="2026-11-19", canvas=[W, H], base="plate.png",
               frame_box=[round(v, 2) for v in G.FRAME], grade="plate-grade.json (B2's WM-G1 curve) on every file",
               compose=dict(order=["base"] + [f"{k}-shadow, {k}" for k in order] + ["light (screen)"],
                            formula="out = round((below * shadow / 255) * (1 - a) + rgb * a), straight alpha; then the light: "
                                    "out = 255 - round((255 - out) * (255 - L) / 255)"),
               layers=[dict(slot=k, product=SLOTS[k]["pid"], card=SLOTS[k]["card"], sku=SLOTS[k]["sku"], z=SLOTS[k]["z"], shadow_z=SLOTS[k]["z"] - 1,
                            default=True, layer=files[k][0], shadow=files[k][1], alpha_px=int((layers[k][0][..., 3] > 0).sum()),
                            shadow_px=int((layers[k][1] < 255).sum())) for k in order],
               light=dict(product=SLOTS[LIGHT_SLOT]["pid"], file=lpth, z=90, blend="screen", px=int((L8.max(2) > 0).sum())),
               variants=[], rnd2=dict(region_px=int(region.sum()), outside_differing_px=rnd2,
                                      rule="outside every alpha, shadow and light: plate.png, pixel for pixel"),
               gaps_left_empty=["shower-stool", "wall-art", "ledge-planter"], record=rec)
    json.dump(man, open(os.path.join(ST, "layers", "manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(rnd2=rnd2, lock=rec["lock"], gain=rec["gain_p1_p50_p99"], cut=rec["cut"], light_px=man["light"]["px"])))


if __name__ == "__main__":
    main(sys.argv[1])
