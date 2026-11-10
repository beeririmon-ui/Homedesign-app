#!/usr/bin/env python3
"""
build_layers_v3c.py: the warm-modern tool's layers in the approved v3c display grade.
render-agent, 2026-11-10. Brief: briefs/render-wm-tool-layers-v3c-2026-11-10.md. Owner approval AP3-WM (status/decisions.json),
QA qa/reports/2026-11-07-pilot-phase1-v3c-verify.md. Code only: 0 tokens, no var2, no network. It reads the approved files in the
parent folder and writes new files in this folder only (base.png, cushions-set-{A,B,C}.png, cushions-set-{A,B,C}-shadow.png, manifest.json).

Method: cut from the approved display files; no layer is graded on its own.
  base.png                    a byte copy of ../shell-furniture-v3-graded-v3c.png (the shell, the fixed furniture and their shadow).
  cushions-set-X-shadow.png   multiply, opaque RGB, white = none. In the shadow band of the approved cut (../shadows/cushions/set-X.png < 255,
                              outside the product alpha) each channel is the integer S with round(base * S / 255) == the approved composite,
                              taken as close as possible to the approved (pre-grade) shadow value, so the layer stays the approved shadow
                              wherever the grade allows it. RGB, not grey: the v3c toe lifts L* and keeps a*/b*, so the deep contact
                              shadow comes out more neutral than base x grey. Where a channel would need S > 255 (the composite is
                              brighter than the base there: the toe on dark warm pixels), S = 255 and the residual is counted.
                              Under the soft edge of the product it is the approved shadow value itself; under alpha 255 it is 255.
  cushions-set-X.png          normal (source-over), straight alpha. Alpha = the approved cut (../layers/cushions/set-X.png: hand outlines of
                              ../cushion-polys.json refined by GrabCut, the coffee table subtracted). RGB at alpha 255 = the approved
                              composite pixel itself; at the soft edge, solved so that base x shadow under it and the layer over it give
                              the approved composite pixel; alpha is raised only where that solution would leave 0-255. Under alpha 0 the
                              RGB is bled outward 32 px (an alpha-weighted fill) so lossy web codecs do not pull black into the edge;
                              it adds nothing to the picture.
The masks/stone*.png of grade v3c do not touch the cushion region (0 px), so in this region the grade was exposure + toe only.

  python3 build_layers_v3c.py            then   python3 verify_layers_v3c.py
"""
import hashlib
import json
import os
import shutil

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
REL = lambda p: os.path.relpath(p, REPO)  # noqa: E731
SETS = "ABC"
BASE_SRC = os.path.join(SRC, "shell-furniture-v3-graded-v3c.png")
COMP_SRC = {s: os.path.join(SRC, f"composite-set-{s}-v3-graded-v3c.png") for s in SETS}
ALPHA_SRC = {s: os.path.join(SRC, f"layers/cushions/set-{s}.png") for s in SETS}
SHADOW_SRC = {s: os.path.join(SRC, f"shadows/cushions/set-{s}.png") for s in SETS}
SELECTION = os.path.join(REPO, "data/selections/living-room.warm-modern.json")
SLOTS = os.path.join(REPO, "data/slots/living-room.json")
CANVAS_OVERSCAN = (4072, 2290)        # pilot_wm.py: the overscan canvas; the 3840 x 2160 camera frame sits at (116, 65) inside it
BLEED_PX = 32

# the set's products: the selection's items, verbatim, with the card id, the option and the SKU where the card has exactly one
PRODUCTS = {
    "B": [("cushions-aliexpress-textured-boucle-throw-pillow", {"color": "oatmeal", "size": "50x50"}, "50 x 50 square"),
          ("cushions-cj-wide-stripe-corduroy-light-green", {"color": "camel"}, "corduroy square (card 50 x 50)"),
          ("cushions-cj-linen-look-charcoal", {"color": "beige", "size": "30x50"}, "30 x 50 lumbar"),
          ("sofa-cover-cj-cotton-muslin-fringe", {"other": "pecan", "size": "150x200"}, "throw 150 x 200")],
    "A": [("cushions-cj-boucle-teddy", {"color": "white", "size": "50x50"}, "50 x 50 square"),
          ("cushions-cj-knitted-chenille-bean-green", {"color": "21-camel-color"}, "45 x 45 square"),
          ("cushions-cj-boucle-teddy", {"color": "milk-tea-color", "size": "30x50"}, "30 x 50 lumbar"),
          ("sofa-cover-cj-cotton-muslin-fringe", {"other": "flax-brown", "size": "150x200"}, "throw 150 x 200")],
    "C": [("cushions-cj-boucle-teddy", {"color": "light-brown", "size": "50x50"}, "50 x 50 square"),
          ("cushions-cj-corduroy-patchwork", {"color": "dark-coffee", "size": "45x45"}, "45 x 45 square"),
          ("cushions-cj-linen-look-ivory", {"color": "light-beige-gray"}, "30 x 50 lumbar"),
          ("sofa-cover-cj-cotton-muslin-fringe", {"other": "clay", "size": "150x200"}, "throw 150 x 200")],
}


NOTES = {("A", "cushions-cj-knitted-chenille-bean-green"): "customer-facing colour name: taupe (טאופ), not camel; the SKU photo reads "
                                                     "taupe (selection, cushions picks A note_2026_11_07)"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rgb(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64)


def rhu(x):
    """round half up, the one rounding used for every 8-bit result here"""
    return np.floor(x + 0.5)


def region_info(region, W, H):
    ys, xs = np.nonzero(region)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    fu = lambda x: round((x / W * CANVAS_OVERSCAN[0] - 116) / 3840, 4)  # noqa: E731
    fv = lambda y: round((y / H * CANVAS_OVERSCAN[1] - 65) / 2160, 4)  # noqa: E731
    return dict(px=int(region.sum()), bbox_px=[x0, y0, x1, y1],
                rect_canvas_uv=[round(x0 / W, 4), round(x1 / W, 4), round(y0 / H, 4), round(y1 / H, 4)],
                rect_camera_frame_uv=[fu(x0), fu(x1), fv(y0), fv(y1)])


def cut(s, B):
    T = rgb(COMP_SRC[s])
    a0 = np.asarray(Image.open(ALPHA_SRC[s]))[..., 3].astype(np.int32)
    r0 = np.asarray(Image.open(SHADOW_SRC[s]).convert("L")).astype(np.float64)    # the approved shadows are grey (3 equal channels)
    H, W = a0.shape
    prod, full = a0 > 0, a0 == 255
    part = prod & ~full
    sho = ~prod & (r0 < 255)
    changed = np.abs(T - B).max(2) > 0
    stray = int((changed & ~(prod | sho)).sum())
    if stray:
        raise SystemExit(f"set {s}: {stray} px of the approved composite differ from the base outside the approved cut; stop")

    # --- the shadow (multiply): per channel, the integer closest to the approved shadow that reproduces the composite
    S = np.full(B.shape, 255.0)
    b, t = B[sho], T[sho]
    ref = np.repeat(r0[sho][:, None], 3, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        lo = np.ceil((t - 0.5) * 255.0 / b)
        hi = np.ceil((t + 0.5) * 255.0 / b) - 1
    reach = np.where(b > 0, lo <= 255, t == 0)
    lo, hi = np.clip(np.nan_to_num(lo, nan=0), 0, 255), np.clip(np.nan_to_num(hi, nan=255), 0, 255)
    wide = (hi - lo) >= 2                                   # keep one step off the ends where there is room (other 8-bit rounders)
    lo2, hi2 = np.where(wide, lo + 1, lo), np.where(wide, hi - 1, hi)
    pick = np.where(b > 0, np.clip(ref, lo2, hi2), ref)
    S[sho] = np.where(reach, pick, 255.0)
    unreach_px = int((~reach).any(1).sum())
    # under the soft edge: the approved shadow value itself (what the approved composite was built with); 255 under alpha 255
    S[part] = np.repeat(r0[part][:, None], 3, 1)

    # --- the product layer: alpha = the approved cut; RGB = the composite at 255, solved at the soft edge
    A = a0.astype(np.float64)
    L = np.zeros_like(B)
    L[full] = T[full]
    t, B1, a_ = T[part], B[part] * S[part] / 255.0, A[part]
    with np.errstate(divide="ignore", invalid="ignore"):
        need = np.where(t > B1, (t - B1) / np.maximum(255.0 - B1, 1e-9), np.where(t < B1, (B1 - t) / np.maximum(B1, 1e-9), 0.0)).max(1)
    a_new = np.clip(np.maximum(a_, np.ceil(need * 255.0 - 1e-6)), 1, 255)
    raised = int((a_new > a_).sum())
    af = (a_new / 255.0)[:, None]
    Lf = (t - B1 * (1 - af)) / af
    best, best_e, best_r = None, None, None
    for d in (0, -1, 1):
        c = np.clip(rhu(Lf) + d, 0, 255)
        out = B1 * (1 - af) + c * af
        e, r = np.abs(rhu(out) - t), np.abs(out - t)
        if best is None:
            best, best_e, best_r = c, e, r
        else:
            better = (e < best_e) | ((e == best_e) & (r < best_r))
            best, best_e, best_r = np.where(better, c, best), np.where(better, e, best_e), np.where(better, r, best_r)
    L[part] = best
    A[part] = a_new
    # bleed under alpha 0 (no effect on the picture; protects the edge from lossy codecs)
    pm = L * (A / 255.0)[..., None]
    known = A > 0
    zone = ~known & cv2.dilate(known.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * BLEED_PX + 1, 2 * BLEED_PX + 1))).astype(bool)
    n4 = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 4.0)
    d4 = cv2.GaussianBlur((A / 255.0).astype(np.float32), (0, 0), 4.0)
    n12 = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 12.0)
    d12 = cv2.GaussianBlur((A / 255.0).astype(np.float32), (0, 0), 12.0)
    bl = np.where((d4 > 0.01)[..., None], n4 / np.maximum(d4, 1e-12)[..., None], n12 / np.maximum(d12, 1e-12)[..., None])
    ok = zone & ((d4 > 0.01) | (d12 > 1e-4))
    L[ok] = np.clip(rhu(bl[ok]), 0, 255)

    L8, A8, S8 = L.astype(np.uint8), A.astype(np.uint8), S.astype(np.uint8)
    Image.fromarray(np.dstack([L8, A8]), "RGBA").save(os.path.join(HERE, f"cushions-set-{s}.png"), compress_level=9)
    Image.fromarray(S8, "RGB").save(os.path.join(HERE, f"cushions-set-{s}-shadow.png"), compress_level=9)

    region = (A8 > 0) | (S8 < 255).any(2)
    old_region = prod | sho
    return dict(region=region_info(region, W, H),
                alpha_px=int((A8 > 0).sum()), alpha_255_px=int((A8 == 255).sum()), alpha_soft_px=int(((A8 > 0) & (A8 < 255)).sum()),
                shadow_px=int((S8 < 255).any(2).sum()),
                build=dict(approved_cut_px=int(old_region.sum()), region_outside_approved_cut_px=int((region & ~old_region).sum()),
                           approved_changed_px=int(changed.sum()),
                           soft_edge_alpha_raised_px=raised,
                           shadow_band_px=int(sho.sum()),
                           shadow_band_channel_needs_over_255_px=unreach_px,
                           shadow_differs_from_approved_shadow_px=int((np.abs(S[sho] - np.repeat(r0[sho][:, None], 3, 1)).max(1) > 0).sum()),
                           bleed_px=int(ok.sum())))


def products(s):
    out = []
    sel = json.load(open(SELECTION))["slots"]["cushions"]["picks"]
    items = next(p for p in sel if p["set_id"] == s)["items"]
    for (card, opt, role), item in zip(PRODUCTS[s], items):
        if not item.startswith(card):
            raise SystemExit(f"set {s}: selection item '{item}' does not match card {card}")
        cp = os.path.join(REPO, "data/products", "sofa-cover" if card.startswith("sofa-cover") else "cushions", f"{card}.json")
        c = json.load(open(cp))
        skus = [k["id"] for k in c["options"]["skus"] if all(k["values"].get(a) == v for a, v in opt.items())]
        rec = dict(card_id=c["id"], card=REL(cp), selection_item=item, role=role, option=opt)
        if (s, card) in NOTES:
            rec["note"] = NOTES[(s, card)]
        if len(skus) == 1:
            rec["sku"] = skus[0]
        else:
            rec["sku"] = None
            rec["sku_candidates"] = skus
            rec["sku_note"] = "the selection does not say which; it matters to the shop, not to the picture"
        out.append(rec)
    return out


def main():
    B = rgb(BASE_SRC)
    H, W = B.shape[:2]
    shutil.copyfile(BASE_SRC, os.path.join(HERE, "base.png"))
    sel = json.load(open(SELECTION))["slots"]["cushions"]
    order = [p["set_id"] for p in sel["picks"]]
    slot = next(x for x in json.load(open(SLOTS))["slots"] if x["id"] == "cushions")
    sets = {}
    for s in SETS:
        st = cut(s, B)
        sets[s] = dict(
            layer=f"cushions-set-{s}.png", shadow=f"cushions-set-{s}-shadow.png",
            products=products(s),
            source=dict(approved_composite=REL(COMP_SRC[s]), approved_composite_sha256=sha256(COMP_SRC[s]),
                        alpha_from=REL(ALPHA_SRC[s]), shadow_band_from=REL(SHADOW_SRC[s]),
                        outlines=REL(os.path.join(SRC, "cushion-polys.json"))),
            region=st["region"], alpha_px=st["alpha_px"], alpha_255_px=st["alpha_255_px"], alpha_soft_px=st["alpha_soft_px"],
            shadow_px=st["shadow_px"], build=st["build"])
        print(s, json.dumps(st["build"]), json.dumps(st["region"]))
    man = dict(
        id="wm-living-room-m0-tool-layers-v3c",
        room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-10", author="render-agent",
        brief="briefs/render-wm-tool-layers-v3c-2026-11-10.md",
        approval="AP3-WM (owner, 2026-11-07, status/decisions.json); QA qa/reports/2026-11-07-pilot-phase1-v3c-verify.md",
        status="the approved v3c display files of pilot phase 1 as separate layers; recompositing checked by verify_layers_v3c.py (QA to re-run); "
               "for the tool behind HD_PUBLIC=0; web encoding (WebP/AVIF, widths) is frontend-dev's",
        grade="v3c, one display grade for every pilot file (jobs.json grade_v3c). Every layer is cut from the graded display files; "
              "no layer is graded on its own and the site applies no further grade",
        size=dict(width=W, height=H, aspect="16:9",
                  canvas="the M0 1.2 overscan canvas (4072 x 2290 at 2720 / 4072), the same as the approved display files; for the engine "
                         "every file covers the whole canvas, rect [0, 1, 0, 1]",
                  camera_frame_px=[round(116 / 4072 * W, 2), round(65 / 2290 * H, 2), round((116 + 3840) / 4072 * W, 2), round((65 + 2160) / 2290 * H, 2)],
                  camera_frame_note="the 3840 x 2160 camera frame inside the canvas [x0, y0, x1, y1]; rect_camera_frame_uv and data/slots "
                                    "boxes are in this frame"),
        color="8-bit sRGB, no ICC profile. Blending works on the sRGB-encoded values (CSS mix-blend-mode, canvas 2D and the engine's GL path do)",
        compose=dict(
            order=["base", "cushions-shadow", "cushions"],
            formula="out = round((base * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, straight (not premultiplied) alpha; "
                    "one set at a time: its shadow and its layer swap together",
            swap_region="per set: alpha > 0 or any shadow channel < 255 (region below); a swap A <-> B <-> C changes nothing outside "
                        "the union of the two sets' regions"),
        layers=[
            dict(id="base", file="base.png", blend="normal", z=0, opaque=True,
                 replaces_base_layers=["shell (z 0)", "fixed-furniture-shadow (z 34, multiply)", "fixed-furniture (z 40)"],
                 source=REL(BASE_SRC), how="byte copy of the approved file", sha256=sha256(os.path.join(HERE, "base.png"))),
            dict(id="cushions-shadow", slot="cushions", blend="multiply", z=slot["z"] - 1, opaque=True, per_set="sets.<X>.shadow",
                 white_is_none=True, format="RGB, no alpha",
                 how="in the approved shadow band, per channel the integer S with round(base * S / 255) = the approved composite, the "
                     "closest to the approved (pre-grade) shadow; RGB because the v3c toe neutralises the deep contact shadow; "
                     "under the soft edge the approved shadow value; 255 under alpha 255"),
            dict(id="cushions", slot="cushions", blend="normal", z=slot["z"], per_set="sets.<X>.layer", format="RGBA, straight alpha",
                 how="alpha = the approved cut; RGB = the approved composite where alpha is 255, solved at the soft edge so that "
                     f"base x shadow and the layer give the approved pixel; RGB bled {BLEED_PX} px under alpha 0 (no effect on the picture)"),
        ],
        slot=dict(id="cushions", z=slot["z"], set_of=slot.get("set_of"), default="B", order=order,
                  default_source="data/selections/living-room.warm-modern.json (slots.cushions.default_2026_11_07, CAM1: set B is the default)",
                  sold_as="a set (SET1), a single unit as an option"),
        sets=sets,
        known_limits=[
            "a multiply cannot brighten: in "
            + ", ".join(f"set {s} {sets[s]['build']['shadow_band_channel_needs_over_255_px']} px" for s in SETS)
            + " of the shadow band the v3c toe put one channel (mostly blue) of the approved composite 1-4 levels above the base; there the "
              "shadow channel is 255 and the recomposite is off by up to that much (verify-layers-v3c.json); putting them in the layer's "
              "alpha would have scattered faint pixels outside the product silhouette",
            "the shadow layers are exact for this base only: in the deep contact shadow under the throw the multiplier is cool "
            "(about 140 / 190 / 255), because the v3c toe turned the deepest shadow neutral. If a later slot puts something under the "
            "cushions' shadow (a rug, the sofa cover), cut the shadow again on that base",
            "the soft-edge alpha was raised in "
            + ", ".join(f"set {s} {sets[s]['build']['soft_edge_alpha_raised_px']} px" for s in SETS)
            + " (out of about 11,500 soft px each; median +2 levels) where the solved RGB would have left 0-255",
        ],
        files=dict(build="build_layers_v3c.py", verify="verify_layers_v3c.py", verification="verify-layers-v3c.json",
                   asset_manifest_entries="asset-manifest-entries.json (for assets/manifest.json; this task writes new files only)",
                   verify_usage="python3 verify_layers_v3c.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=0,
    )
    json.dump(man, open(os.path.join(HERE, "manifest.json"), "w"), indent=1, ensure_ascii=False)
    # entries in the format of assets/manifest.json, ready to merge (this task does not edit existing files)
    st_ = ("warm-modern tool, pilot phase 1, v3c layers (briefs/render-wm-tool-layers-v3c-2026-11-10.md; approved composites: owner AP3-WM, "
           "QA qa/reports/2026-11-07-pilot-phase1-v3c-verify.md); recompositing verified by verify_layers_v3c.py; awaiting qa-agent's re-run")
    common = dict(status=st_, style="warm-modern", model="code", room="living-room", created="2026-11-10",
                  recipe=REL(os.path.join(HERE, "build_layers_v3c.py")))
    ents = [dict(id="wm-tool-v3c-base", path=REL(os.path.join(HERE, "base.png")),
                 kind="tool base layer, v3c (shell + fixed furniture + their shadow; byte copy of shell-furniture-v3-graded-v3c.png)", **common)]
    for s in SETS:
        ents.append(dict(id=f"wm-tool-v3c-cushions-{s}", path=REL(os.path.join(HERE, f"cushions-set-{s}.png")),
                         kind=f"tool product layer, cushions set {s}{' (default)' if s == 'B' else ''}, v3c, RGBA straight alpha, normal", **common))
        ents.append(dict(id=f"wm-tool-v3c-cushions-{s}-shadow", path=REL(os.path.join(HERE, f"cushions-set-{s}-shadow.png")),
                         kind=f"tool shadow layer, cushions set {s}, v3c, RGB multiply (white = none)", **common))
    ents.append(dict(id="wm-tool-v3c-manifest", path=REL(os.path.join(HERE, "manifest.json")),
                     kind="tool layer manifest, v3c (order, blends, size, default set B, card ids, sources)", **common))
    json.dump(dict(note="to merge into assets/manifest.json 'assets' (render-agent 2026-11-10; the brief allowed new files only)", assets=ents),
              open(os.path.join(HERE, "asset-manifest-entries.json"), "w"), indent=1, ensure_ascii=False)
    print("manifest.json and asset-manifest-entries.json written")


if __name__ == "__main__":
    main()
