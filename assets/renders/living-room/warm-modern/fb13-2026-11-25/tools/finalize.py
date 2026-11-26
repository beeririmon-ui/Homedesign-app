#!/usr/bin/env python3
"""finalize.py: FB13 stage A, the stack of extract.py -> the shared finish (assets/renders/tools/finish) -> the files of the repo:
plate-PW.png, hero-HW.png, layers/ shadows/ light/, layers/manifest.json, default-frame-m0w.png, checks-m0w.json, qa-sheet-m0w.jpg.
The finish: the layers' edge sharpness to the plate's, depth of field from the clay's depth (35 mm, f/5.6, focus on the sofa wall),
the light wrap, ONE grain field by position (seed 1540) and a vignette of at most 0.15 stop (G1.9 allows 0.25), both baked by
position into the plate and into every layer, so every combination carries the same finish. No bounce tint: the products' colour
on the room is already in the hero's own ratio layers."""
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

import hwlib as L

sys.path.insert(0, os.path.join(L.REPO, "assets/renders/tools/finish"))
import finish as F  # noqa: E402
import pasted_test as PT  # noqa: E402
from extract import ORDER, LAMPS, PRODUCT  # noqa: E402

D = os.path.join(L.OUT, "stack")
OUTP = os.path.join(L.OUT, "prep")
DEST = L.FB13
names = [k for k, _ in ORDER]
Z = dict(ORDER)
rd = lambda p, m: np.asarray(Image.open(p).convert(m))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
VIG_STOP = 0.15


def vignette():
    x0, y0, x1, y1 = L.FB
    yy, xx = np.mgrid[0:L.H, 0:L.W].astype(np.float32)
    rho = np.hypot((xx - (x0 + x1) / 2) / ((x1 - x0) / 2), (yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) / np.sqrt(2.0)
    return (2.0 ** (-VIG_STOP * np.clip(rho, 0, 1.15) ** 2.4)).astype(np.float32)


def bake(rgb8, v, grain):
    lin = L.srgb2lin(rgb8.astype(np.float32) / 255.0) * v[..., None]
    out = L.lin2srgb(lin) * 255.0 + grain[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def main():
    base = rd(os.path.join(D, "base.png"), "RGB")
    lay = [(rd(os.path.join(D, f"layer-{k}.png"), "RGBA"), rd(os.path.join(D, f"shadow-{k}.png"), "RGB")) for k in names]
    lights = [rd(os.path.join(D, f"light-{l}.png"), "RGB") for l in LAMPS]
    hero = rd(os.path.join(OUTP, "hero.png"), "RGB")
    hard = np.load(os.path.join(D, "hard.npz"))
    st = dict(key="M0-W", frame_box=list(L.FB), entries=[dict(name=k, slot=k, product=PRODUCT[k]) for k in names], cfg={})
    rep = {}
    # the stack before the finish against the hero: the products are the hero's (the top opaque pixels of every product)
    raw = F.compose(base, lay, lights)
    top = np.zeros(base.shape[:2], bool)
    cover = np.zeros(base.shape[:2], bool)
    for k in reversed(names):
        a = lay[names.index(k)][0][..., 3] == 255
        top |= a & hard[k] & ~cover
        cover |= lay[names.index(k)][0][..., 3] > 0
    d = np.abs(raw.astype(int) - hero.astype(int)).max(2)
    rep["products_vs_hero_before_finish"] = dict(px=int(top.sum()), mean=round(float(d[top].mean()), 3), p99=float(np.percentile(d[top], 99)),
                                                 px_over_3=int((d[top] > 3).sum()), room_mean=round(float(d[~cover].mean()), 2),
                                                 note="product pixels (opaque, uppermost): the 8-bit stack over the graded hero; the room between them is the plate "
                                                      "in the hero's light (its own texture), so it is not compared pixel for pixel")
    t0 = PT.run_test(st, base, lay, lights, label="before the finish")
    # ---- the finish
    maps = np.load(os.path.join(OUTP, "maps.npz"))
    dm = maps["depth"].astype(np.float64)
    dm[dm > 1e3] = 0
    depth = dict(m=dm, focus=4.3, lens=35.0, N=5.6, px_per_mm=(L.FB[2] - L.FB[0]) / 36.0)
    # the shared finish's own code, as this stack needs it: the plate's depth of field by position and the ONE grain field
    # (finish_room on the plate alone); every layer blurred by its own depth (finish.blur_premult). NOT applied here: the edge
    # sharpness matching, the light wrap, the per-layer grain top-up and the bounce tint: they were made for cut-outs of separate
    # renders; on layers split from one photograph with a feathered fringe they steepen the fringe and put noise on a matte bowl
    st0 = dict(st, entries=[])
    _, fbase, _, grain, frec = F.finish_room(st0, base, [], lights, dict(bounce=0.0, dof=depth, grain=1.2, grain_max=1.2))
    fl = []
    frec['layers'] = {}
    for (Lr, S), k in zip(lay, names):
        a = Lr[..., 3].astype(np.float32) / 255.0
        ys, xs = np.nonzero(a > 0.5)
        yb, xc = min(L.H - 1, int(ys.max()) + 2), int(np.median(xs))
        inside = dm[a > 0.5]
        dz = float(dm[yb, xc]) if dm[yb, xc] > 0 else float(np.median(inside[inside > 0]))
        if k in ('pendant', 'framed-art', 'accent-sconces', 'vase', 'planter'):
            dz = float(np.median(inside[inside > 0]))
        sg = float(F.dof_sigma_px(np.array([dz]), depth['focus'], depth['lens'], depth['N'], depth['px_per_mm'])[0])
        Lf = Lr.astype(np.float32)
        if sg >= 0.35:
            Lf = F.blur_premult(Lf, sg, F.bbox_of(a > 0.02, 24, a.shape))
        fl.append((np.clip(np.rint(Lf), 0, 255).astype(np.uint8), S))
        frec['layers'][k] = dict(dof=dict(depth_m=round(dz, 3), sigma_px=round(sg, 3), blurred=bool(sg >= 0.35)))
    v = vignette()
    base_f = bake(np.clip(np.rint(fbase), 0, 255).astype(np.uint8), v, grain)
    lay_f = []
    for (Lr, S) in fl:
        rgb = bake(Lr[..., :3], v, grain)
        rgb[Lr[..., 3] == 0] = 0
        lay_f.append((np.dstack([rgb, Lr[..., 3]]), S))
    lights_f = [np.clip(np.rint(l.astype(np.float32) * v[..., None]), 0, 255).astype(np.uint8) for l in lights]
    final = F.compose(base_f, lay_f, lights_f)
    t1 = PT.run_test(st, base_f, lay_f, lights_f, label="after the finish")
    # ---- write
    os.makedirs(os.path.join(DEST, "layers"), exist_ok=True)
    Image.fromarray(base_f).save(os.path.join(DEST, "plate-PW.png"), optimize=True)
    Image.fromarray(hero).save(os.path.join(DEST, "hero-HW.png"), optimize=True)
    man_layers, regions = [], {}
    for k, (Lr, S) in zip(names, lay_f):
        pid = PRODUCT[k]
        lp, sp = f"layers/{k}/{pid}.png", f"shadows/{k}/{pid}.png"
        for rel in (lp, sp):
            os.makedirs(os.path.dirname(os.path.join(DEST, rel)), exist_ok=True)
        Image.fromarray(Lr).save(os.path.join(DEST, lp), optimize=True)
        Image.fromarray(S).save(os.path.join(DEST, sp), optimize=True)
        reg = (Lr[..., 3] > 0) | (S < 255).any(2)
        regions[k] = reg
        ys, xs = np.where(Lr[..., 3] > 0)
        man_layers.append(dict(slot=k, product=pid, z=Z[k], shadow_z=Z[k] - 1, default=True, layer=lp, shadow=sp, alpha_px=int((Lr[..., 3] > 0).sum()),
                               shadow_px=int((S < 255).any(2).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                               sold=k != "coffee-table", source="hero-HW.png (seedream-5-pro 2K, one render) cut in code"))
    man_light = []
    for l, lt in zip(LAMPS, lights_f):
        rel = f"light/{PRODUCT[l]}.png"
        os.makedirs(os.path.dirname(os.path.join(DEST, rel)), exist_ok=True)
        Image.fromarray(lt).save(os.path.join(DEST, rel), optimize=True)
        man_light.append(dict(file=rel, z=90, blend="screen", lamps=[l], px=int((lt > 0).any(2).sum())))
        regions[l] = regions[l] | (lt > 0).any(2)
    fr = F.frame_view(final, st, (1920, 1080))
    Image.fromarray(fr).save(os.path.join(DEST, "default-frame-m0w.png"), optimize=True)
    # ---- RND2-style checks on the finished stack
    union = np.zeros(base.shape[:2], bool)
    for r_ in regions.values():
        union |= r_
    lightreg = np.zeros(base.shape[:2], bool)
    for lt in lights_f:
        lightreg |= (lt > 0).any(2)
    out_d = (final != base_f).any(2) & ~(union | lightreg)
    chk = dict(outside_every_region_differing_px=int(out_d.sum()), region_px=int((union | lightreg).sum()))
    per = {}
    for i, k in enumerate(names):
        wo = F.compose(base_f, [x for j, x in enumerate(lay_f) if j != i], [lt for l, lt in zip(LAMPS, lights_f) if l != k])
        dif = (wo != final).any(2)
        per[k] = dict(changed_px=int(dif.sum()), changed_outside_its_region_px=int((dif & ~regions[k]).sum()))
    chk["swap_one_product"] = per
    again = F.frame_view(F.compose(rd(os.path.join(DEST, "plate-PW.png"), "RGB"),
                                   [(rd(os.path.join(DEST, m["layer"]), "RGBA"), rd(os.path.join(DEST, m["shadow"]), "RGB")) for m in man_layers],
                                   [rd(os.path.join(DEST, m["file"]), "RGB") for m in man_light]), st, (1920, 1080))
    chk["default_frame_reproduced_from_files_max_diff"] = int(np.abs(again.astype(int) - rd(os.path.join(DEST, "default-frame-m0w.png"), "RGB").astype(int)).max())
    rep["rnd2"] = chk
    fin = final.astype(np.float32) / 255.0
    rep["light_default_frame"] = L.measure(fin, hero=True)
    rep["light_plate"] = L.measure(base_f.astype(np.float32) / 255.0)
    Lf = L.to_lab(fin)[..., 0]
    lampL = {}
    for l in LAMPS:
        m_ = hard[l] & (Lf > 80)
        lampL[l] = dict(lit_px=int(m_.sum()), L_p50=round(float(np.percentile(Lf[hard[l]], 50)), 1), L_p90=round(float(np.percentile(Lf[hard[l]], 90)), 1),
                        L_p99=round(float(np.percentile(Lf[hard[l]], 99)), 1))
    rep["lamps_L"] = lampL
    pend = hard["pendant"]
    ys = np.where(pend[:, 1200:1800].sum(1) > 30)[0]
    rep["pendant"] = dict(shade_top_row=int(ys.min()), frame_top=round(L.FB[1], 1), margin_pct_of_frame_height=round((ys.min() - L.FB[1]) / (L.FB[3] - L.FB[1]) * 100, 2))
    slim = lambda t: dict(plate_black_p05_L=t["plate_black_p05_L"],
                          rows=[{k: r.get(k) for k in ("layer", "score", "fails", "sharp_ratio", "grain_ratio", "edge_rows_x1", "shadow_rows_x1", "contact", "black", "lamp", "frame_px")}
                                for r in t["rows"]])
    rep["pasted_test"] = dict(before=slim(t0), after=slim(t1),
                              mean_score_before=round(float(np.mean([r.get("score", 0) for r in t0["rows"]])), 2),
                              mean_score_after=round(float(np.mean([r.get("score", 0) for r in t1["rows"]])), 2))
    rep["finish"] = dict(grain=frec.get("grain"), dof_plate=frec.get("dof_plate"), vignette_stop_max=VIG_STOP,
                         layers=frec['layers'], not_applied='edge sharpness matching, light wrap, per-layer grain top-up, bounce tint (see finalize.py)')
    json.dump(rep, open(os.path.join(DEST, "checks-m0w.json"), "w"), indent=1, default=str)
    json.dump(dict(layers=man_layers, light=man_light), open(os.path.join(L.OUT, "manifest-parts.json"), "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("products_vs_hero_before_finish", "rnd2", "light_default_frame", "lamps_L", "pendant")}, default=str)[:3500])
    print("pasted mean score", rep["pasted_test"]["mean_score_before"], "->", rep["pasted_test"]["mean_score_after"])
    for r in t1["rows"]:
        print(f"  {r['layer']:16s} score {r.get('score')} fails {r.get('fails')}")


if __name__ == "__main__":
    main()
