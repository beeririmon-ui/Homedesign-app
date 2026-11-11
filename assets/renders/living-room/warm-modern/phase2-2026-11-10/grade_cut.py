#!/usr/bin/env python3
"""
grade_cut.py: the v3c display files and layers of the warm-modern tool, phase 2, steps 1-3 (render-agent, 2026-11-10/11).
Brief: briefs/render-wm-tool-phase2-2026-11-10.md. Code only, 0 tokens. New files only (layers/, graded/, manifest, sheet).

Method (phase 1's layers-v3c, extended to a stack of products):
  1. The ungraded stack (stack.py): the base, then each accepted product in slot z order, each changing only its own region.
  2. ONE grade (stack.Grade = phase 1's grade_v3c, base.png reproduced byte for byte): stage k's graded composite C_k is C_{k-1}
     with G(U_k) written into product k's region only, so nothing outside it ever changes (rule ו.5 by construction).
  3. Every layer is CUT from the graded composites, never graded on its own (build_layers_v3c.py's cut): alpha = the product's cut
     (8-bit); RGB = C_k under full alpha, solved at the soft edge over C_{k-1} x shadow, the alpha raised only where the solution
     would leave 0-255; the shadow (multiply, RGB) = per channel the integer S with round(C_{k-1} x S / 255) = C_k, closest to the
     ungraded shadow; S = 255 wherever C_k = C_{k-1}. RGB is bled 32 px under alpha 0 (no effect on the picture).
  4. The cushion sets A / B / C (phase 1, approved) sit at z 55 over the new rug and floor lamp. Where the stack under them did not
     change their approved v3c layer and shadow are kept byte for byte; where it changed (QA 2026-11-10 section 9: 'cut the shadows
     again on the new base') they are re-cut on the new stack the same way.
  5. Products whose pass did not follow the plan or the card are NOT layered here (PENDING, retake with the reserve).
  python3 grade_cut.py        then   python3 layers/verify_layers.py
"""
import hashlib
import json
import os
import shutil

import cv2
import numpy as np
from PIL import Image

import phase2_wm as W
import stack
from phase2_wm import P1

HERE = W.HERE
LAY = os.path.join(HERE, "layers")
GRD = os.path.join(HERE, "graded")
REPO = W.REPO
BLEED = 32
CARDS = {
    "rug": ("rug-cj-braided-wool-natural", {"size": "230x330", "other": "square"}, "CJJT211801818RI"),
    "vase": ("vase-cj-textured-white-stoneware", {"size": "large"}, "CJJT312391803CX"),
    "floor-lamp": ("floor-lamp-cj-pleated-walnut-stem-158", {"other": "3color-floor-lamp"}, "CJYD224754407GT"),
    "framed-art": ("framed-art-aliexpress-frameless-minimalist-wall-art-631735", {"color": "tl2356-3pcs", "size": "50x70-no-frame"}, "12000052586400026"),
    "accent-sconces": ("accent-sconces-aliexpress-travertine-cylinder-walnut-choice", {"style": "round-walnut"}, "12000047535430431"),
    "candle-holders": ("candle-holders-cj-travertine-pedestal", {"size": "70x110mm"}, "CJYD201648001AZ"),
}
ACCEPTED = ["framed-art", "accent-sconces", "vase", "rug", "floor-lamp", "candle-holders"]
PENDING = {
    "curtains": "step 2 drew the stack about twice as wide as the plan's 0.30 m front stack (WMC7), over the first glazing pane",
    "planter": "with the basket in one pass (plan section 2); step 2 put the basket beside the pot and over its right side",
    "basket": "step 2 put it beside the pot (~110 px right of its place), not in front of it",
    "magazine-holder": "step 2 drew it taller than wide; the card is 35 W x 27.5 H",
    "bowl": "step 3 put it at the table's left end, not at its checked place (0.72, 1.94), and ~24 cm wide (card 20)",
    "pendant": "step 3 drew the widest ring ~66 cm (card: Beige 50 cm)",
}
LIGHTS = {"floor-lamp", "accent-sconces"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rhu(x):
    return np.floor(x + 0.5)


def u8(p, mode="RGB"):
    return np.asarray(Image.open(p).convert(mode)).astype(np.float64)


def cut(T, B, a0, r0, region):
    """build_layers_v3c.py cut(), generalised: T graded composite with the product, B graded composite without it (both float 0-255),
    a0 the product's 8-bit alpha, r0 its 8-bit ungraded shadow (H x W), region where the product may change the picture."""
    H, Wd = a0.shape
    prod, full = a0 > 0, a0 == 255
    part = prod & ~full
    same = (np.abs(T - B).max(2) == 0)
    sho = region & ~prod & ~same
    stray = int((~same & ~(prod | sho)).sum())
    S = np.full(B.shape, 255.0)
    b, t = B[sho], T[sho]
    ref = np.repeat(r0[sho][:, None], 3, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        lo = np.ceil((t - 0.5) * 255.0 / b)
        hi = np.ceil((t + 0.5) * 255.0 / b) - 1
    reach = np.where(b > 0, lo <= 255, t == 0)
    lo, hi = np.clip(np.nan_to_num(lo, nan=0), 0, 255), np.clip(np.nan_to_num(hi, nan=255), 0, 255)
    wide = (hi - lo) >= 2
    lo2, hi2 = np.where(wide, lo + 1, lo), np.where(wide, hi - 1, hi)
    pick = np.where(b > 0, np.clip(ref, lo2, hi2), ref)
    S[sho] = np.where(reach, pick, 255.0)
    unreach = int((~reach).any(1).sum())
    S[part] = np.repeat(np.minimum(r0[part], 255.0)[:, None], 3, 1)
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
    best, be, br = None, None, None
    for d in (0, -1, 1):
        c = np.clip(rhu(Lf) + d, 0, 255)
        out = B1 * (1 - af) + c * af
        e, r = np.abs(rhu(out) - t), np.abs(out - t)
        if best is None:
            best, be, br = c, e, r
        else:
            bt = (e < be) | ((e == be) & (r < br))
            best, be, br = np.where(bt, c, best), np.where(bt, e, be), np.where(bt, r, br)
    L[part] = best
    A[part] = a_new
    pm = L * (A / 255.0)[..., None]
    known = A > 0
    zone = ~known & cv2.dilate(known.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * BLEED + 1, 2 * BLEED + 1))).astype(bool)
    n4 = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 4.0)
    d4 = cv2.GaussianBlur((A / 255.0).astype(np.float32), (0, 0), 4.0)
    n12 = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 12.0)
    d12 = cv2.GaussianBlur((A / 255.0).astype(np.float32), (0, 0), 12.0)
    bl = np.where((d4 > 0.01)[..., None], n4 / np.maximum(d4, 1e-12)[..., None], n12 / np.maximum(d12, 1e-12)[..., None])
    ok = zone & ((d4 > 0.01) | (d12 > 1e-4))
    L[ok] = np.clip(rhu(bl[ok]), 0, 255)
    return dict(L=L.astype(np.uint8), A=A.astype(np.uint8), S=S.astype(np.uint8),
                stats=dict(stray_px=stray, alpha_px=int((A > 0).sum()), alpha_255_px=int((A == 255).sum()), soft_px=int(((A > 0) & (A < 255)).sum()),
                           shadow_px=int((S < 255).any(2).sum()), soft_edge_alpha_raised_px=raised, shadow_channel_needs_over_255_px=unreach,
                           bleed_px=int(ok.sum())))


def region_info(m):
    ys, xs = np.nonzero(m)
    H, Wd = m.shape
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    fu = lambda x: round((x / Wd * 4072 - 116) / 3840, 4)  # noqa: E731
    fv = lambda y: round((y / H * 2290 - 65) / 2160, 4)  # noqa: E731
    return dict(px=int(m.sum()), bbox_px=[x0, y0, x1, y1], rect_canvas_uv=[round(x0 / Wd, 4), round(x1 / Wd, 4), round(y0 / H, 4), round(y1 / H, 4)],
                rect_camera_frame_uv=[fu(x0), fu(x1), fv(y0), fv(y1)])


def main():
    os.makedirs(LAY, exist_ok=True)
    os.makedirs(GRD, exist_ok=True)
    G = stack.Grade()
    P = stack.base_parts()
    base8 = u8(os.path.join(P1, "layers-v3c/base.png"))
    assert (G(P["U0"]).astype(np.float64) == base8).all(), "the grade does not reproduce base.png: stop"
    shutil.copyfile(os.path.join(P1, "layers-v3c/base.png"), os.path.join(LAY, "base.png"))
    items = set(ACCEPTED) | {"cushions"}
    results, regions, finals = {}, {}, {}
    cush_changed = {}
    for s in "BAC":
        U, steps = stack.compose(items, P, cushion_set=s, keep_steps=True)
        Aun = np.zeros(P["fa"].shape, np.float32)
        Cprev = base8.copy()
        appr = u8(os.path.join(P1, f"composite-set-{s}-v3-graded-v3c.png"))
        for st in steps:
            k, reg = st["k"], st["region"]
            Aun = np.maximum(Aun, st["a_eff"] if k != "cushions" else st["a"])
            Cg = G(st["U"], Aun).astype(np.float64)
            C = Cprev.copy()
            if k == "cushions":
                delta = reg & (np.abs(Cprev - base8).max(2) > 0)
                delta = cv2.dilate(delta.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & reg
                C[reg] = appr[reg]
                C[delta] = Cg[delta]
                cush_changed[s] = delta
            else:
                C[reg] = Cg[reg]
            a8 = np.clip(rhu(st["a_eff"] * 255), 0, 255).astype(np.int32)
            r8 = np.clip(rhu(st["Sh"] * 255), 0, 255).astype(np.float64)
            if k == "cushions":
                # outside the changed area: the approved v3c files; inside: a fresh cut on the new stack
                LA = np.asarray(Image.open(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png"))).copy()
                SA = np.asarray(Image.open(os.path.join(P1, f"layers-v3c/cushions-set-{s}-shadow.png")).convert("RGB")).copy()
                if delta.any():
                    a0 = np.where(delta, LA[..., 3].astype(np.int32), a8)
                    r = cut(C, Cprev, a0, r8, reg)
                    LA[..., :3][delta] = r["L"][delta]
                    LA[..., 3][delta] = r["A"][delta]
                    SA[delta] = r["S"][delta]
                    st_ = dict(r["stats"], recut_px=int(delta.sum()), kept_approved_px=int((reg & ~delta).sum()))
                else:
                    st_ = dict(recut_px=0, kept_approved_px=int(reg.sum()))
                results[("cushions", s)] = dict(L=LA, S=SA, stats=st_)
            elif s == "B":
                r = cut(C, Cprev, a8, r8, reg)
                if r["stats"]["stray_px"]:
                    raise SystemExit(f"{k}: {r['stats']['stray_px']} px change outside its region: stop")
                results[(k, None)] = dict(L=np.dstack([r["L"], r["A"]]), S=r["S"], stats=r["stats"])
            regions[(k, s)] = reg
            Cprev = C
        finals[s] = Cprev.astype(np.uint8)
        Image.fromarray(finals[s]).save(os.path.join(GRD, f"default-scene-set-{s}-graded-v3c.png"), compress_level=6)
    # the layers above the cushions were cut on set B's stack: valid for A and C only if no cushion region touches them
    above = [k for k in stack.ORDER if stack.ORDER.index(k) > stack.ORDER.index("cushions") and k in ACCEPTED]
    overlap = {k: {s: int((regions[(k, "B")] & regions[("cushions", s)]).sum()) for s in "ABC"} for k in above}
    assert all(v == 0 for o in overlap.values() for v in o.values()), f"a layer above the cushions overlaps a set: {overlap}"
    # per-step graded composites for the sheet (base + the products of each step, set B)
    for name, its in (("step1-rug", {"rug", "cushions"}), ("step2-window-floor", {"rug", "cushions", "vase", "floor-lamp"}),
                      ("step3-wall-table", {"rug", "cushions", "framed-art", "accent-sconces", "candle-holders"})):
        U, steps = stack.compose(its, P, cushion_set="B", keep_steps=True)
        Aun = np.zeros(P["fa"].shape, np.float32)
        C = base8.copy()
        appr = u8(os.path.join(P1, "composite-set-B-v3-graded-v3c.png"))
        for st in steps:
            Aun = np.maximum(Aun, st["a_eff"] if st["k"] != "cushions" else st["a"])
            Cg = G(st["U"], Aun).astype(np.float64)
            if st["k"] == "cushions":
                d = st["region"] & (np.abs(C - base8).max(2) > 0)
                d = cv2.dilate(d.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & st["region"]
                C[st["region"]] = appr[st["region"]]
                C[d] = Cg[d]
            else:
                C[st["region"]] = Cg[st["region"]]
        Image.fromarray(C.astype(np.uint8)).save(os.path.join(GRD, f"{name}-set-B-graded-v3c.png"), compress_level=6)
    # write the layers
    files = {}
    for (k, s), r in results.items():
        if k == "cushions":
            d = os.path.join(LAY, "cushions")
            os.makedirs(d, exist_ok=True)
            lp, sp = os.path.join(d, f"set-{s}.png"), os.path.join(d, f"set-{s}-shadow.png")
        else:
            d = os.path.join(LAY, k)
            os.makedirs(d, exist_ok=True)
            lp, sp = os.path.join(d, f"{CARDS[k][0]}.png"), os.path.join(d, f"{CARDS[k][0]}-shadow.png")
        Image.fromarray(r["L"], "RGBA").save(lp, compress_level=9)
        Image.fromarray(r["S"], "RGB").save(sp, compress_level=9)
        files[(k, s)] = (lp, sp)
    write_manifest(G, files, results, regions, cush_changed, overlap)
    print(json.dumps({f"{k}{'-' + s if s else ''}": v["stats"] for (k, s), v in results.items()}, indent=1))


def write_manifest(G, files, results, regions, cush_changed, overlap):
    J = W.jobs()
    rel = W.rel
    layers = [dict(id="base", file="base.png", blend="normal", z=0, opaque=True,
                   replaces_base_layers=["shell (z 0)", "fixed-furniture-shadow (z 34, multiply)", "fixed-furniture (z 40)"],
                   source=rel(os.path.join(P1, "layers-v3c/base.png")), how="byte copy of the approved v3c base (= shell-furniture-v3-graded-v3c.png)",
                   sha256=sha(os.path.join(LAY, "base.png")))]
    for k in stack.ORDER:
        if k == "cushions":
            layers.append(dict(id="cushions-shadow", slot="cushions", blend="multiply", z=54, per_set="sets.<X>.shadow", white_is_none=True, format="RGB, no alpha"))
            layers.append(dict(id="cushions", slot="cushions", blend="normal", z=55, per_set="sets.<X>.layer", format="RGBA, straight alpha",
                               how="the approved v3c set where the stack under it did not change; re-cut on the new stack where it did (rug, floor lamp)"))
            continue
        if k in PENDING:
            layers.append(dict(id=k, slot=k, z=stack.Z[k], status="pending: retake (reserve, manager approval)", reason=PENDING[k]))
            continue
        lp, sp = files[(k, None)]
        card, opt, sku = CARDS[k]
        st = results[(k, None)]["stats"]
        reg = regions[(k, "B")]
        layers.append(dict(id=f"{k}-shadow", slot=k, blend="multiply", z=stack.Z[k] - 1, file=os.path.relpath(sp, LAY), opaque=True, white_is_none=True,
                           format="RGB, no alpha"))
        rec = dict(id=k, slot=k, blend="normal", z=stack.Z[k], file=os.path.relpath(lp, LAY), format="RGBA, straight alpha",
                   product=dict(card_id=card, card=rel(next(p for p in __import__("glob").glob(os.path.join(REPO, "data/products/**", f"{card}.json"), recursive=True))),
                                option=opt, sku=sku, default=True),
                   region=region_info(reg), build=st,
                   behind_fixed_furniture=k in stack.BEHIND, lit_product_rendered_off=k in LIGHTS)
        if k in stack.BEHIND:
            rec["note"] = ("stands behind the fixed furniture, which the base already holds: its alpha leaves the furniture whole and its soft edge is "
                           "solved against it (composed physically in stack.py: (behind x shadow + product) x (1 - fa) + furniture x fa)")
        layers.append(rec)
    sets = {}
    for s in "BAC":
        lp, sp = files[("cushions", s)]
        sets[s] = dict(layer=os.path.relpath(lp, LAY), shadow=os.path.relpath(sp, LAY),
                       products="as layers-v3c/manifest.json sets." + s, region=region_info(regions[("cushions", s)]),
                       recut_on_new_stack_px=int(cush_changed[s].sum()), build=results[("cushions", s)]["stats"],
                       approved_source=rel(os.path.join(P1, f"layers-v3c/cushions-set-{s}.png")))
    man = dict(
        id="wm-living-room-m0-tool-layers-phase2-steps1-3", room="living-room", style="warm-modern", camera="M0 1.2 (tool)", date="2026-11-11",
        author="render-agent", brief="briefs/render-wm-tool-phase2-2026-11-10.md",
        approval="PH2-WM (owner, 2026-11-10); base and cushions: AP3-WM + QA qa/reports/2026-11-10-wm-tool-layers-v3c.md",
        status="steps 1-3 of phase 2, PARTIAL: 6 of 12 defaults layered, 6 pending a retake (reserve, manager approval). Not QA'd; for the checkpoint "
               "(qa-agent, master-designer). HD_PUBLIC=0 only",
        grade="v3c, ONE display grade (stack.Grade = phase 1 grade_v3c; base.png reproduced byte for byte). Every layer is cut from the graded "
              "composites; no layer is graded on its own; the site applies no further grade",
        grade_params=G.record(),
        size=json.load(open(os.path.join(P1, "layers-v3c/manifest.json")))["size"],
        color="8-bit sRGB, no ICC profile. Blending on the sRGB-encoded values (CSS mix-blend-mode, canvas 2D, the engine's GL path)",
        compose=dict(order=[l_["id"] for l_ in layers if "status" not in l_],
                     formula="for each product in order: out = round((below * shadow / 255) * (1 - a) + rgb * a), a = alpha / 255, straight alpha; "
                             "the cushions: one set at a time, its shadow and its layer together",
                     swap_region="per product: alpha > 0 or any shadow channel < 255; a product (or a set) changes nothing outside its region"),
        layers=layers,
        slot_cushions=dict(default="B", order=["B", "A", "C"], sets=sets,
                           note="layers above the cushions were cut on set B's stack; their regions touch no set's region (checked): " + json.dumps(overlap)),
        pending=PENDING,
        light_layers="the floor lamp and the wall lamps are rendered OFF as products; their light layers are made in code later (plan section 2, step 8)",
        files=dict(build="grade_cut.py (with stack.py, extract.py, phase2_wm.py)", verify="verify_layers.py", verification="verify-layers.json",
                   asset_manifest_entries="asset-manifest-entries.json", verify_usage="python3 verify_layers.py  (numpy + Pillow; exit 0 = pass)"),
        tokens=0,
    )
    json.dump(man, open(os.path.join(LAY, "manifest.json"), "w"), indent=1, ensure_ascii=False)
    J["grade_v3c_phase2"] = dict(rule=man["grade"], params=G.record(), graded=sorted(os.listdir(GRD)))
    json.dump(J, open(W.JOBS, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
