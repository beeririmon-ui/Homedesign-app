#!/usr/bin/env python3
"""
verify_layers_basket.py: re-runnable check of the basket move in M0 (the designer's point (-1.20, 0.30), code only, 2026-11-25;
render-agent, for qa-agent). Reads manifest-basket.json, manifest-lfix.json and the files they name; writes verify-layers-basket.json;
exit 0 = all pass.

    python3.12 -I -B verify_layers_basket.py [manifest-basket.json]

  1 RND2       each rebuilt default = lfix's truth outside the old and the new basket regions (layer alpha > 0 or shadow < 255; 0 px);
               every other layer file is lfix's own (the planter's shadow: see 4 l)
  2 WM-G1      the plate is stage 0's (sha); no default's black point (L* p0.5) below R9's - 0.05
  3 stack      this manifest's 8-bit stack = the truths inside the changed region (0 px), over the canvas within R9's gate (p99.9 <= 2,
               max <= 6)
  4 placement  the decision's conditions, recomputed from the camera (fb12_s0.project) and the lfix layer warped by the recorded affine:
               (a) the contact point and the scale; (b) >= 50 % of the basket visible (alpha); (c) V7Q6: >= 0.15 % of the frame and >= 6 %
               of its height; (d) the arm hides >= 0.020 of the frame width; (e) the arm's top corner >= 0.018 of the frame height above
               the basket's back rim, and the right handle hidden (0 px); (f) the pot: >= 0.02 of the width from the visible basket, no
               basket shadow on it; (g) the rug: the basket not on it, its back-left corner >= 0.02 from the basket, and the floor strip
               between the base and the rug's back edge (expected ~0.015 of the frame height); (h) no basket shadow on the wall or the skirting (a 3 px anti-aliased foot allowed) or on the sofa (fa > 0.98);
               (i) the designer's dot (0.458, 0.75) on full basket alpha, clear of the sofa; (j) fidelity: dE00 against the same file
               moved (median and p95 <= 3); (k) the old spot: no basket alpha or shadow left in the old region outside the new one;
               (l) the pot's contact (planter-shadow): changed only inside the old region, no light ring left between the base and its
               shadow (the pot's own file unchanged)
  5 scan       scan_edge_bleed.py on this manifest: no EDGE row of the basket at x1-x2; its SHADOW rows only on the floor
  6 scope      no tracked file under the warm-modern living room is modified in git (only new files; the folder's README.md allowed)
"""
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(P2, *[".."] * 4))
PLATE_SHA = "7f83091908fb5331e3491598839d790129d36ced1ce01dec3f65f1d75cc265cd"
NEW = (-1.20, 0.30)
DOT = (0.458, 0.75)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FB = _load("fb12_s0", os.path.join(P2, "fb12_s0.py"))
SCAN = _load("scan_edge_bleed", os.path.join(HERE, "scan_edge_bleed.py"))
FX = _load("fix_basket", os.path.join(P2, "fix_basket.py"))          # de2000 and lab only
W, H = FB.W, FB.H
FX0, FY0, FX1, FY1 = FB.FRAME_BOX
FW, FH = FX1 - FX0, FY1 - FY0


def arr(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lstar(a8):
    return cv2.cvtColor(a8.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)[..., 0]


def main():
    man_p = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "manifest-basket.json")
    MD = os.path.dirname(man_p)

    def L(p):                                    # relative to the manifest; files it did not write are this folder's
        q = os.path.normpath(os.path.join(MD, p))
        return q if os.path.exists(q) else os.path.normpath(os.path.join(HERE, p))

    def region(lf, sf):
        return (arr(lf)[..., 3] > 0) | (arr(sf, "RGB") < 255).any(2)

    def stack(man, st, Lf):
        by = {l_["id"]: l_ for l_ in man["layers"]}
        out = []
        for l_ in man["layers"]:
            k = l_["id"]
            if k == "base" or k.endswith("-shadow"):
                continue
            if k == "cushions":
                v = man["slot_cushions"]["sets"][st]
                out.append((k, Lf(v["layer"]), Lf(v["shadow"])))
            else:
                out.append((k, Lf(l_["file"]), Lf(by[k + "-shadow"]["file"])))
        return out

    man = json.load(open(man_p))
    man0 = json.load(open(os.path.join(HERE, "manifest-lfix.json")))
    L0 = lambda p: os.path.normpath(os.path.join(HERE, p))  # noqa: E731
    by, by0 = {l_["id"]: l_ for l_ in man["layers"]}, {l_["id"]: l_ for l_ in man0["layers"]}
    out, ok = {}, True

    # 1 RND2
    others_same = [k for k in by if k not in ("basket", "basket-shadow", "planter-shadow") and by[k].get("file") != by0[k].get("file")] == [] and \
        all(man["slot_cushions"]["sets"][s]["layer"] == man0["slot_cushions"]["sets"][s]["layer"] and
            man["slot_cushions"]["sets"][s]["shadow"] == man0["slot_cushions"]["sets"][s]["shadow"] for s in "BAC")
    R_old = region(L0(by0["basket"]["file"]), L0(by0["basket-shadow"]["file"]))
    R_new = region(L(by["basket"]["file"]), L(by["basket-shadow"]["file"]))
    c1 = dict(other_layers_same_file=bool(others_same), old_region_px=int(R_old.sum()), new_region_px=int(R_new.sum()),
              regions_overlap_px=int((R_old & R_new).sum()))
    for st in "BAC":
        d = (arr(L(man["truths"]["default"][st]), "RGB") != arr(L0(man0["truths"]["default"][st]), "RGB")).any(2)
        c1[f"default_{st}_changed_px"] = int(d.sum())
        c1[f"default_{st}_outside_old_and_new_px"] = int((d & ~(R_old | R_new)).sum())
    c1["pass_"] = bool(c1["other_layers_same_file"] and all(c1[f"default_{st}_outside_old_and_new_px"] == 0 for st in "BAC"))
    out["1_RND2"] = c1
    ok &= c1["pass_"]

    # 2 WM-G1
    plate_p = L(by["base"]["file"])
    r9 = json.load(open(os.path.join(HERE, "manifest-r9.json")))
    c2 = dict(plate_sha_is_stage0=sha(plate_p) == PLATE_SHA)
    for st in "BAC":
        c2[f"default_{st}"] = round(float(np.percentile(lstar(arr(L(man["truths"]["default"][st]), "RGB")), 0.5)), 2)
        c2[f"default_{st}_lfix"] = round(float(np.percentile(lstar(arr(L0(man0["truths"]["default"][st]), "RGB")), 0.5)), 2)
        c2[f"default_{st}_r9"] = round(float(np.percentile(lstar(arr(L0(r9["truths"]["default"][st]), "RGB")), 0.5)), 2)
    c2["pass_"] = bool(c2["plate_sha_is_stage0"] and all(c2[f"default_{st}"] >= c2[f"default_{st}_r9"] - 0.05 for st in "BAC"))
    out["2_WM_G1"] = c2
    ok &= c2["pass_"]

    # 3 the stack
    c3 = {}
    base8 = arr(plate_p, "RGB")
    reg = np.load(os.path.normpath(os.path.join(MD, "..", "work-basket", "regions-basket.npz")))
    for st in "BAC":
        s8 = FB.compose8(base8, stack(man, st, L), {})
        diff = np.abs(s8.astype(int) - arr(L(man["truths"]["default"][st]), "RGB").astype(int)).max(2)
        c3[st] = dict(inside_region_px=int((diff[reg[f"default_{st}"]] > 0).sum()), canvas_p99_9=float(np.percentile(diff, 99.9)), canvas_max=int(diff.max()))
    c3["pass_"] = bool(all(c3[st]["inside_region_px"] == 0 and c3[st]["canvas_p99_9"] <= 2 and c3[st]["canvas_max"] <= 6 for st in "BAC"))
    out["3_stack"] = c3
    ok &= c3["pass_"]

    # 4 placement
    c4 = {}
    mv = by["basket"]["basket_move"]
    a_ = math.radians(FB.CAM["yaw_deg_left"])
    fwd = np.array([-math.sin(a_), -math.cos(a_), 0.0])
    dep = lambda X, Y: float((np.array([X, Y, 0.0]) - np.array(FB.CAM["loc"])) @ fwd)  # noqa: E731
    old = tuple(mv["from_m"])
    c_new = FB.project(NEW[0], NEW[1], 0.0)
    s_exp = dep(*old) / dep(*NEW)
    A = np.array(mv["affine"], np.float64)
    c_old = FB.project(old[0], old[1], 0.0)
    c_map = A @ np.array([c_old[0], c_old[1], 1.0])
    c4["a_contact"] = dict(expected=[round(c_new[0], 2), round(c_new[1], 2)], mapped=[round(float(c_map[0]), 2), round(float(c_map[1]), 2)],
                           scale=round(float(A[0, 0]), 5), scale_expected=round(s_exp, 5),
                           pass_=bool(abs(c_map[0] - c_new[0]) < 0.05 and abs(c_map[1] - c_new[1]) < 0.05 and abs(A[0, 0] - s_exp) < 1e-4 and A[0, 0] == A[1, 1]))
    Lb0 = arr(L0(by0["basket"]["file"]))
    aw = cv2.warpAffine(Lb0[..., 3].astype(np.float32) / 255, A, (W, H), flags=cv2.INTER_CUBIC)
    aw = np.clip(aw, 0, 1)
    Lb, Sb = arr(L(by["basket"]["file"])), arr(L(by["basket-shadow"]["file"]), "RGB")
    av = Lb[..., 3].astype(np.float32) / 255
    fa = arr(os.path.join(P2, "work-fb12s0", "fixed-furniture-fb12s0.png"))[..., 3].astype(np.float32) / 255
    share = float(av.sum() / aw.sum())
    c4["b_visible"] = dict(share=round(share, 4), pass_=share >= 0.50)
    vis = av > 0.5
    inf = np.zeros((H, W), bool)
    inf[int(math.ceil(FY0)):int(FY1), int(math.ceil(FX0)):int(FX1)] = True
    ys, xs = np.nonzero(vis & inf)
    fr_share = float((vis & inf).sum() / (FW * FH))
    hgt = float((ys.max() - ys.min() + 1) / FH)
    c4["c_V7Q6"] = dict(frame_share=round(fr_share, 5), height_share=round(hgt, 4), pass_=bool(fr_share >= 0.0015 and hgt >= 0.06))
    # body rows: below the rim (the topmost row whose unoccluded run is >= 60 % of the body width) and above the base
    full = aw > 0.5
    widths = full.sum(1)
    body_w = int(np.median(widths[widths > 0]))
    rows = np.nonzero(widths >= 0.6 * body_w)[0]
    rim, base = int(rows.min()), int(rows.max())
    br = np.arange(rim + 8, base - 8)
    r_un = np.array([np.nonzero(full[y])[0].max() for y in br])
    r_vis = np.array([np.nonzero(vis[y])[0].max() for y in br])
    hidden = float(np.median(r_un - r_vis) / FW)
    c4["d_arm_hides"] = dict(body_width_px=body_w, hidden_frame_width=round(hidden, 4), visible_right_edge_px=int(np.median(r_vis)),
                             rule=">= 0.020 (the decision: 0.020-0.022, 'not less'; above it the bound is (b), >= 50 % visible)", pass_=bool(hidden >= 0.020))
    x_edge = int(np.median(r_vis))
    arm_rows = [np.nonzero(fa[:, x] > 0.5)[0] for x in range(x_edge + 2, x_edge + 12)]
    arm_top = int(min(r_[r_ > 900].min() for r_ in arm_rows))
    gap_v = (rim - arm_top) / FH
    cx_body = 0.5 * (np.nonzero(full[(rim + base) // 2])[0].min() + np.nonzero(full[(rim + base) // 2])[0].max())
    right_handle_vis = int(((av > 0.25) & (np.arange(H)[:, None] < rim) & (np.arange(W)[None, :] > cx_body)).sum())
    c4["e_arm_corner"] = dict(arm_top_row=arm_top, basket_back_rim_row=rim, gap_frame_height=round(gap_v, 4), right_handle_visible_px=right_handle_vis,
                              pass_=bool(gap_v >= 0.018 and right_handle_vis == 0))
    pot = arr(L(by["planter"]["file"]))[..., 3]
    potm = pot > 127
    pot_right = int(np.nonzero(potm.any(0))[0].max())
    bas_left = int(np.nonzero(vis.any(0))[0].min())
    Dk = 1 - Sb.astype(np.float32).min(2) / 255
    sh_on_pot = int(((Dk >= 2 / 255) & (pot > 25)).sum())
    c4["f_pot"] = dict(pot_right_px=pot_right, basket_left_px=bas_left, gap_frame_width=round((bas_left - pot_right) / FW, 4),
                       basket_shadow_px_on_pot=sh_on_pot, pass_=bool((bas_left - pot_right) / FW >= 0.02 and sh_on_pot == 0))
    rug = arr(L(by["rug"]["file"]))[..., 3] > 127
    on_rug = int((vis & rug).sum())
    corner = (FX0 + 0.408 * FW, FY0 + 0.817 * FH)                       # the rug's back-left corner (the decision's (0.408, 0.817))
    ry, rx = np.nonzero(rug)
    corner_on_rug_px = float(np.hypot(rx - corner[0], ry - corner[1]).min())
    vy, vx = np.nonzero(vis)
    d_rug = float(np.hypot(vx - corner[0], vy - corner[1]).min() / FW)
    strip = []
    for x in range(bas_left, x_edge):
        yb = np.nonzero(vis[:, x])[0]
        yr = np.nonzero(rug[:, x])[0]
        if len(yb) and len(yr[yr > yb.max()]):
            strip.append(int(yr[yr > yb.max()].min() - yb.max() - 1))
    c4["g_rug"] = dict(basket_px_on_rug=on_rug, corner_px=[round(corner[0], 1), round(corner[1], 1)], corner_to_rug_alpha_px=round(corner_on_rug_px, 1),
                       corner_to_basket_frame_width=round(d_rug, 4),
                       floor_strip_px=dict(min=min(strip) if strip else None, median=float(np.median(strip)) if strip else None),
                       floor_strip_frame_height=round(float(np.median(strip)) / FH, 4) if strip else None,
                       pass_=bool(on_rug == 0 and d_rug >= 0.02))
    X_, Y_ = FB.img_to_plane(FB.H_FLOOR)
    floor = (Y_ > 0.004) & (X_ > -2.296) & (np.arange(H)[:, None] > 900)
    on_wall = int(((Dk >= 3 / 255) & ~cv2.dilate(floor.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)).sum())
    on_sofa = int(((Dk >= 2 / 255) & (fa > 0.98)).sum())
    c4["h_shadow_where"] = dict(px_on_wall_or_skirting=on_wall, px_on_sofa=on_sofa, shadow_px=int((Dk > 0).sum()),
                                darkening_max=round(float(Dk.max()), 3), pass_=bool(on_wall == 0 and on_sofa == 0))
    dx, dy = FX0 + DOT[0] * FW, FY0 + DOT[1] * FH
    c4["i_dot"] = dict(px=[round(dx, 1), round(dy, 1)], alpha=int(Lb[int(round(dy)), int(round(dx)), 3]), fa=round(float(fa[int(round(dy)), int(round(dx))]), 3),
                       pass_=bool(Lb[int(round(dy)), int(round(dx)), 3] == 255 and fa[int(round(dy)), int(round(dx))] == 0))
    a0 = Lb0[..., 3:4].astype(np.float32) / 255
    pm = cv2.warpAffine(np.dstack([Lb0[..., :3].astype(np.float32) / 255 * a0, a0]), A, (W, H), flags=cv2.INTER_CUBIC)
    ref = np.clip(pm[..., :3] / np.maximum(pm[..., 3:4], 1e-6), 0, 1)
    core = (Lb[..., 3] == 255) & (aw > 0.999)
    g = float(mv["exposure_gain_linear"])
    new01 = Lb[..., :3][core].astype(np.float32) / 255
    d_raw = FX.de2000(FX.lab(ref[core]), FX.lab(new01))
    d_norm = FX.de2000(FX.lab(ref[core]), FX.lab(FB.l2s(FB.s2l(new01) / g)))
    c4["j_fidelity"] = dict(px=int(core.sum()), exposure_gain=g, dE00_median=round(float(np.median(d_raw)), 3), dE00_p95=round(float(np.percentile(d_raw, 95)), 3),
                            dE00_exposure_normalised_p95=round(float(np.percentile(d_norm, 95)), 3),
                            pass_=bool(np.median(d_raw) <= 3 and np.percentile(d_raw, 95) <= 3))
    old_only = R_old & ~R_new
    c4["k_old_spot"] = dict(old_only_px=int(old_only.sum()), basket_alpha_px=int((Lb[..., 3][old_only] > 0).sum()),
                            basket_shadow_px=int((Sb[old_only] < 255).any(1).sum()),
                            pass_=bool((Lb[..., 3][old_only] > 0).sum() == 0 and (Sb[old_only] < 255).any(1).sum() == 0))
    P0, P1 = arr(L0(by0["planter-shadow"]["file"]), "RGB"), arr(L(by["planter-shadow"]["file"]), "RGB")
    pch = (P0 != P1).any(2)
    a7 = arr(L(by["planter"]["file"]))[..., 3].astype(np.float32) / 255
    inside7 = a7 > 0.5
    d7 = cv2.distanceTransform((~inside7).astype(np.uint8), cv2.DIST_L2, 5)
    zone7 = (np.arange(H)[:, None] >= 1135) & (((a7 > 0) & (a7 < 1)) | ((~inside7) & (d7 <= 3.0))) & \
        (cv2.distanceTransform(R_old.astype(np.uint8), cv2.DIST_L2, 5) >= 8) & (np.arange(H)[:, None] >= 1143)
    kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))

    Sx0 = np.where(inside7[..., None], 255, P0).astype(np.uint8)
    ring0 = np.dstack([cv2.erode(Sx0[..., i], kk) for i in range(3)]).astype(np.float32)   # the original's darkest line within 5 px

    def gap(S):
        return int(((S.astype(np.float32) - ring0) / 255 > 0.06).any(2)[zone7].sum())
    c4["l_pot_contact"] = dict(planter_layer_same_file=by["planter"]["file"] == by0["planter"]["file"], shadow_changed_px=int(pch.sum()),
                               shadow_changed_outside_old_region_px=int((pch & ~R_old).sum()), light_ring_px_before=gap(P0), light_ring_px_after=gap(P1),
                               pass_=bool(by["planter"]["file"] == by0["planter"]["file"] and (pch & ~R_old).sum() == 0 and gap(P1) == 0))
    c4["pass_"] = bool(all(v["pass_"] for k, v in c4.items() if isinstance(v, dict)))
    out["4_placement"] = c4
    ok &= c4["pass_"]

    # 5 the scan
    rows = SCAN.scan(man_p, variants=False)
    bas = [dict(check=r["check"], visibility=r["visibility"], bbox=r["bbox"], px=r["px"], **({"dE_mean": r["dE_mean"]} if r["check"] == "EDGE" else {"dark_mean": r["dark_mean"]}))
           for r in rows if r["layer"] == "basket"]
    bad = [r for r in bas if r["visibility"] == "x1-x2" and (r["check"] == "EDGE" or not floor[r["bbox"][1]:r["bbox"][3] + 1, r["bbox"][0]:r["bbox"][2] + 1].mean() > 0.9)]
    out["5_scan"] = dict(basket_rows=bas, failing=bad, rows_total=len(rows), pass_=not bad)
    ok &= out["5_scan"]["pass_"]

    # 6 scope
    r = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "assets/renders/living-room/warm-modern"], capture_output=True, text=True).stdout
    mod = [ln for ln in r.splitlines() if not ln.startswith("??") and not ln.endswith("phase2-2026-11-10/README.md")]
    out["6_scope"] = dict(tracked_modified=mod, pass_=not mod)
    ok &= out["6_scope"]["pass_"]

    out["all_pass"] = bool(ok)
    json.dump(out, open(os.path.join(MD, "verify-layers-basket.json"), "w"), indent=1)
    print(json.dumps({k: (v.get("pass_") if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))
    print(json.dumps(out["4_placement"], indent=0)[:3000])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
