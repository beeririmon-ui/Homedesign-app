#!/usr/bin/env python3
"""
compose_fb10.py: the FB10 passes on B2 (proposal 12.6, HOUSE2B) cut into layers, render-agent 2026-11-18. 0 tokens.
Runs after compose_defaults.py, --recolour and post_b2.py (the QA-passed defaults); writes only new layers and moves two:
  pass A (raw/fb10-a-r1): the rope basket and the waffle stack on the open shelf, the travertine tray under the soap dispenser
         and the cup; the dispenser and the cup (layers and shadows) rise by the tray's 1.8 cm
  pass T3 (raw/fb10-t3-r1): the khaki waffle tea towel, a third hand-towel variant with its own alpha and shadow
Each render is locked (lock_b2.py) and tone-matched (gain field) to its own input's base (the defaults with the WM-G1 curve
inverted); each product is cut with GrabCut seeded from its placeholder where the render changed; its shadow is the render's
darkening round it (contact rim + band, tapered); everything is graded with plate-grade.json's curve (grade_plate.curve_apply)
and the composites are recomposed from the files (RND2: outside every alpha, shadow and light, plate.png byte for byte).

  python3 compose_fb10.py
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
import compose_defaults as C  # noqa: E402
import grade_plate as G  # noqa: E402
import prep_fb10 as P  # noqa: E402

NEW = {
    "bath-towels": dict(pid="bath-towels-cj-waffle-cotton-milky-white-70x140-brown", z=36, box="towels", band=24, rim=8,
                        card="data/products/bath/bath-towels/bath-towels-cj-waffle-cotton-milky-white-70x140.json", sku="CJYD178122205EV"),
    "storage-basket": dict(pid="storage-basket-cj-two-tone-cotton-rope-basket-38x25x23-tan-white", z=38, box="basket", band=28, rim=10,
                           card="data/products/bath/storage-basket/storage-basket-cj-two-tone-cotton-rope-basket-38x25x23.json", sku="CJYD180710801AZ"),
    "vanity-tray": dict(pid="pool-cj-travertine-organic-tray-24", z=44, box="tray", band=10, rim=5,
                        card="data/products/pool/tray/pool-cj-travertine-organic-tray-24.json", sku="CJYD238979001AZ"),
}
T3 = dict(slot="hand-towel", pid="tea-towel-cj-waffle-cotton-beige-45x65-pair-khaki", sku="CJYD223761707GT",
          card="data/products/dining/tea-towel/tea-towel-cj-waffle-cotton-beige-45x65-pair.json", band=40, rim=12)
SCR = C.SCR


def files(man):
    return {l["slot"]: (np.asarray(Image.open(os.path.join(ST, l["layer"]))), np.asarray(Image.open(os.path.join(ST, l["shadow"]))))
            for l in man["layers"]}


def stack(man, plate, F, skip=(), swap=None, light=True):
    out = plate.astype(np.float64) / 255
    for l in sorted(man["layers"], key=lambda l: l["z"]):
        if l["slot"] in skip:
            continue
        out = C.compose_one(out, *(swap or {}).get(l["slot"], F[l["slot"]]))
    if light:
        out = C.light_one(out, np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB")))
    return out


def locked(path, base, keep):
    r, wr = C.lock_and_warp(path, base.shape[:2])
    g = C.gain_field(r, base, keep)
    return C.srgb(C.lin(r) * g), dict(warp=wr, gain_p1_p50_p99=[round(float(v), 3) for v in np.percentile(g, [1, 50, 99])])


def cut(src, base, ph, zone, hard, prior=None):
    d = np.linalg.norm(C.lab_of(src) - C.lab_of(base), axis=-1)
    sure = C.ero(ph, 4) & (d > 9)
    if prior is not None:
        sure |= prior & zone
    fg = C.gc_cut(src, sure, C.dil(ph, 3), zone, hard)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), connectivity=8)
    if n > 2:
        fg = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return fg


def shadow(src, base, fg, band, rim, block):
    sp = dict(band=band, rim=rim)
    return C.shadow_of(src, base, fg, sp, np.zeros_like(fg), block)


def graded_shadow(s, below_u, cv):
    sg = np.ones(s.shape)
    m = s < 1
    if m.any():
        b = below_u[m]
        sg[m] = np.clip(cv(b * s[m][:, None]).mean(1) / np.maximum(cv(b).mean(1), 1e-4), 0, 1)
    return sg


def write_layer(slot, pid, a, rgb_g, s_g):
    a8 = C.q(a)
    rgba = np.dstack([C.q(rgb_g), a8])
    rgba[..., :3][a8 == 0] = 0
    lp, sh = os.path.join("layers", slot, pid + ".png"), os.path.join("shadows", slot, pid + ".png")
    os.makedirs(os.path.join(ST, "layers", slot), exist_ok=True)
    os.makedirs(os.path.join(ST, "shadows", slot), exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(os.path.join(ST, lp))
    Image.fromarray(C.q(s_g)).save(os.path.join(ST, sh))
    return lp, sh, rgba, C.q(s_g)


def main():
    man_p = os.path.join(ST, "layers", "manifest.json")
    man = json.load(open(man_p))
    if man.get("fb10"):
        sys.exit("fb10 already applied: re-run the chain (compose_defaults, --recolour, post_b2) first")
    curve = json.load(open(os.path.join(ST, "plate-grade.json")))["curve"]
    cv = lambda x: G.curve_apply(x, curve)[0]  # noqa: E731
    plate = np.asarray(Image.open(os.path.join(ST, "plate.png")).convert("RGB"))
    H, W = plate.shape[:2]
    F = files(man)
    rec = {}
    # ---------- pass A ----------
    base_a = P.inv_curve(stack(man, plate, F), curve)
    allfg = np.zeros((H, W), bool)
    for k, (rgba, _) in F.items():
        allfg |= rgba[..., 3] > 0
    ph = {}
    dummy = base_a.copy()
    ids = np.asarray(Image.open(C.CLAY + "B2-plate-id.png"))
    # the same occluders as the input (prep_fb10): the plate's drawer rail edge
    Y = C.blur(C.luma(base_a), 1.0)
    above = np.zeros((H, W), bool)
    for x in range(1340, 2180):
        c = np.nonzero(ids[1000:1450, x] == 21)[0]
        if not len(c):
            continue
        e0 = 1000 + c.max()
        prof = Y[e0 - 5:e0 + 60, x]
        cand = [i for i in range(len(prof) - 14) if prof[i] - prof[i + 4] > 0.06 and prof[i + 4:i + 14].mean() < 0.22]
        if cand:
            above[:e0 - 5 + max(cand) + 2 + 2, x] = True
    onvan = (F["soap-dispenser"][0][..., 3] > 0) | (F["toothbrush-cup"][0][..., 3] > 0) | (F["vanity-vase"][0][..., 3] > 0)
    col = lambda idx, b: np.array([0.5, 0.5, 0.5])  # noqa: E731
    ph["towels"] = P.paint(dummy, P.BOXES["towels"], col, keep_off=above)
    ph["basket"] = P.paint(dummy, P.BOXES["basket"], col, keep_off=above)
    ph["tray"] = P.paint(dummy, P.BOXES["tray"], col, keep_off=onvan)
    zones = {k: C.dil(ph[NEW[k]["box"]], 30 if k != "vanity-tray" else 14) for k in NEW}
    zones["bath-towels"] &= ~above
    zones["storage-basket"] &= ~above
    keep = ~(C.dil(zones["bath-towels"] | zones["storage-basket"] | zones["vanity-tray"], 40))
    src_a, rec["a_render"] = locked(os.path.join(ST, "raw", "fb10-a-r1.png"), base_a, keep)
    fg = {}
    # the tray first needs the dispenser and the cup where they now stand (raised by the tray's thickness)
    rise = int(round(P.px(6.06, 12.62, 0.88)[1] - P.px(6.06, 12.62, 0.898)[1]))   # the tray's 1.8 cm
    lay = {l["slot"]: l for l in man["layers"]}
    raised = np.zeros((H, W), bool)
    for k in ("soap-dispenser", "toothbrush-cup"):
        a_ = F[k][0][..., 3] > 0
        raised[:-rise] |= a_[rise:]
    for k in NEW:
        if k == "vanity-tray":
            # the tray as the render drew it: an oval slab (top ellipse swept down by its front face), read off the render
            # (left and right ends x 1872 / 2087, top surface y 897-927, front face to 937), refined by GrabCut on its colour
            yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float64)
            def oval(cx, cy, a, b, t):
                m = np.zeros((H, W), bool)
                for dy in range(0, t + 1):
                    m |= ((xx_ - cx) / a) ** 2 + ((yy_ - cy - dy) / b) ** 2 <= 1
                return m
            guess = oval(1979.5, 912, 107.5, 15, 10)
            zone_t = C.dil(guess, 10)
            hard_t = ~zone_t | C.dil(F["vanity-vase"][0][..., 3] > 0, 1)
            fg[k] = C.gc_cut(src_a, C.ero(guess, 5) & ~C.dil(raised, 3), C.dil(guess, 3), zone_t, hard_t)
            continue
        hard = allfg & ~C.dil(ph[NEW[k]["box"]], 2)
        for o in NEW:
            if o != k:
                hard |= C.ero(ph[NEW[o]["box"]], 2)
        fg[k] = cut(src_a, base_a, ph[NEW[k]["box"]], zones[k], hard)
        if k in ("bath-towels", "storage-basket"):
            fg[k] &= ~above
    newfg = np.zeros((H, W), bool)
    for k in NEW:
        newfg |= fg[k]
    rec["tray_rise_px"] = rise
    for k in ("soap-dispenser", "toothbrush-cup"):
        rgba, s8 = F[k]
        rgba2 = np.zeros_like(rgba)
        rgba2[:-rise] = rgba[rise:]
        s2 = np.full_like(s8, 255)
        s2[:-rise] = s8[rise:]
        Image.fromarray(rgba2, "RGBA").save(os.path.join(ST, lay[k]["layer"]))
        Image.fromarray(s2).save(os.path.join(ST, lay[k]["shadow"]))
        F[k] = (rgba2, s2)
        lay[k]["raised_on_tray_px"] = rise
    for k in NEW:
        oth = (allfg | newfg) & ~fg[k]
        s = shadow(src_a, base_a, fg[k], NEW[k]["band"], NEW[k]["rim"], C.dil(oth, 1))
        a = C.soft(fg[k])
        rgb = cv(C.defringe(src_a, fg[k]))
        sg = graded_shadow(s, base_a, cv)
        lp, sh, rgba, s8 = write_layer(k, NEW[k]["pid"], a, rgb, sg)
        ys, xs = np.nonzero((rgba[..., 3] > 0) | (s8 < 255))
        man["layers"].append(dict(slot=k, product=NEW[k]["pid"], card=NEW[k]["card"], sku=NEW[k]["sku"], z=NEW[k]["z"], default=True,
                                  layer=lp, shadow=sh, shadow_z=NEW[k]["z"] - 1, pass_="fb10-a", alpha_px=int((rgba[..., 3] > 0).sum()),
                                  shadow_px=int((s8 < 255).sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
        F[k] = (rgba, s8)
    for l in man["layers"]:
        l["pass"] = l.pop("pass_", l.get("pass", "defaults"))
    # ---------- pass T3 ----------
    base_t = P.inv_curve(stack(man, plate, F, skip=("hand-towel",)), curve)
    pht = np.asarray(Image.open(os.path.join(ST, "inputs", "fb10-t3-mask.png"))) > 0
    zt = C.dil(pht, 40)
    keep_t = ~C.dil(zt, 40)
    src_t, rec["t3_render"] = locked(os.path.join(ST, "raw", "fb10-t3-r1.png"), base_t, keep_t)
    ring = F["towel-ring"][0][..., 3] > 0
    lab = C.lab_of(src_t)
    khaki = (lab[..., 0] > 8) & (lab[..., 0] < 60) & (np.hypot(lab[..., 1], lab[..., 2]) > 8) & (lab[..., 2] > 6) & ~C.dil(ring, 2)
    hard_t = (allfg & ~ring & ~(F["hand-towel"][0][..., 3] > 0)) & ~C.dil(pht, 2)
    ft = cut(src_t, base_t, pht, zt, hard_t, prior=C.ero(pht, 10) & khaki)
    # (no wall trim here: the khaki reads like the shadowed plaster in a*/C*, and the T3 base has no towel to confuse the cut)
    oth = (allfg | newfg) & ~F["hand-towel"][0][..., 3].astype(bool) & ~ft
    s = shadow(src_t, base_t, ft, T3["band"], T3["rim"], C.dil(oth & ~ring, 1))
    a = C.soft(ft)
    rgb = cv(C.defringe(src_t, ft))
    sg = graded_shadow(s, base_t, cv)
    lp, sh, rgba_t, s8_t = write_layer("hand-towel", T3["pid"], a, rgb, sg)
    np.save(os.path.join(SCR, "npz", "fb10-t3-fg.npy"), ft)
    np.save(os.path.join(SCR, "npz", "fb10-new-fg.npy"), np.stack([fg[k] for k in NEW]))
    # ---------- composites from the files ----------
    L8 = np.asarray(Image.open(os.path.join(ST, man["light"]["file"])).convert("RGB"))
    def region_of(pairs):
        r = L8.max(2) > 0
        for rgba, s8 in pairs:
            r |= (rgba[..., 3] > 0) | (s8 < 255)
        return r
    out = {}
    o8 = C.q(stack(man, plate, F))
    Image.fromarray(o8).save(os.path.join(ST, "b2-defaults.png"))
    C.frame_png(o8, os.path.join(ST, "b2-defaults-frame.png"))
    reg = region_of(F.values())
    out["defaults"] = int((np.abs(o8.astype(int) - plate.astype(int)).max(2)[~reg] > 0).sum())
    for v in man.get("variants", []):
        sw = {v["slot"]: (np.asarray(Image.open(os.path.join(ST, v["layer"]))), np.asarray(Image.open(os.path.join(ST, v["shadow"]))))}
        ov = C.q(stack(man, plate, F, swap=sw))
        name = v["composite"].rsplit(".", 1)[0]
        Image.fromarray(ov).save(os.path.join(ST, name + ".png"))
        C.frame_png(ov, os.path.join(ST, name + "-frame.png"))
        rv = region_of(list(F.values()) + list(sw.values()))
        out[name] = int((np.abs(ov.astype(int) - plate.astype(int)).max(2)[~rv] > 0).sum())
        d = np.abs(ov.astype(int) - o8.astype(int)).max(2) > 0
        v["differing_px_vs_defaults_outside_alpha"] = int((d & (sw[v["slot"]][0][..., 3] == 0)).sum())
        v["outside_differing_px_vs_plate"] = out[name]
    sw = {"hand-towel": (rgba_t, s8_t)}
    ok = C.q(stack(man, plate, F, swap=sw))
    Image.fromarray(ok).save(os.path.join(ST, "b2-variant-khaki.png"))
    C.frame_png(ok, os.path.join(ST, "b2-variant-khaki-frame.png"))
    rk = region_of(list(F.values()) + [(rgba_t, s8_t)])
    out["b2-variant-khaki"] = int((np.abs(ok.astype(int) - plate.astype(int)).max(2)[~rk] > 0).sum())
    dk = np.abs(ok.astype(int) - o8.astype(int)).max(2) > 0
    swap_reg = (rgba_t[..., 3] > 0) | (s8_t < 255) | (F["hand-towel"][0][..., 3] > 0) | (F["hand-towel"][1] < 255)
    man["variants"] = [x for x in man.get("variants", []) if x["product"] != T3["pid"]] + [dict(
        slot="hand-towel", product=T3["pid"], card=T3["card"], sku=T3["sku"], z=52, default=False, method="its own render (pass T3), own alpha and shadow",
        layer=lp, shadow=sh, composite="b2-variant-khaki.png", alpha_px=int((rgba_t[..., 3] > 0).sum()), shadow_px=int((s8_t < 255).sum()),
        outside_differing_px_vs_plate=out["b2-variant-khaki"], differing_px_vs_defaults_outside_the_swap_region=int((dk & ~swap_reg).sum()))]
    man["rnd2"] = dict(region_px=int(reg.sum()), outside_differing_px=out["defaults"], rule=man["rnd2"]["rule"])
    man["compose"]["order"] = ["base"] + [f"{l['slot']}-shadow, {l['slot']}" for l in sorted(man["layers"], key=lambda l: l["z"])] + ["light (screen)"]
    man["fb10"] = dict(date="2026-11-18", tool="tools/compose_fb10.py", source="docs/proposals/wm-bath-render-2026-11-17.md 12.6 (HOUSE2B)",
                       passes=["fb10-a (nano-banana-2, 400)", "fb10-t3 (nano-banana-2, 400)"], rnd2_outside_differing_px=out, **rec)
    json.dump(man, open(man_p, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(rnd2=out, **rec), default=float))


if __name__ == "__main__":
    main()
