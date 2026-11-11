#!/usr/bin/env python3
"""
reserve_fidelity.py: the measured fidelity of the reserve passes R1 and R2 against the cards and house plan 1.3.5 (render-agent, 2026-11-11).
Reads the raw passes (registered and tone-matched, work-reserve/<r>-regt.npy), the cuts (work-reserve/layers) and the tinted placeholders
(work-reserve/ph-<r>.npz); inverts step 0's M0 camera where a position is needed. Writes work-reserve/fidelity-r12.json. 0 tokens.

Per product: size (px -> cm at the product's depth), position (px offset -> cm, or the floor / table point recovered through the camera),
the plan's own constraint (curtains: never over glazing; basket: in front of the pot; pendant: shade bottom 1.90), and the verdict.
A size miss may be scaled in code; a placement miss is a fidelity failure (the reserve brief).

  python3 reserve_fidelity.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "step0"))
import extract as X  # noqa: E402
import reserve_r12 as R  # noqa: E402
import step0_clay_checks as S0  # noqa: E402

WR = R.WR
SIZE = R.SIZE
CAM = S0.CAM
YAW = math.radians(CAM["yaw_deg_left"])
FWD = np.array([-math.sin(YAW), -math.cos(YAW)])
RGT = np.array([math.cos(YAW), -math.sin(YAW)])


def px_per_m_h(d):
    return 0.6667 / d * S0.CW / S0.GW * SIZE[0]


def px_per_m_v(d):
    return 1.1852 / d * S0.CH / S0.GH * SIZE[1]


def unproject(x, y, Z):
    """work pixel (x, y) on the horizontal plane at height Z -> (X, Y)"""
    u = (x / SIZE[0] * S0.GW - S0.CX) / S0.CW
    v = (y / SIZE[1] * S0.GH - S0.CY) / S0.CH
    d = 1.1852 * (CAM["loc"][2] - Z) / (v - CAM["v0"])
    xr = (u - CAM["u0"]) * d / 0.6667
    p = np.array(CAM["loc"][:2]) + d * FWD + xr * RGT
    return float(p[0]), float(p[1]), float(d)


def alpha(k):
    return np.asarray(Image.open(os.path.join(WR, "layers", f"{k}.png")))[..., 3].astype(np.float32) / 255


def free_alpha(k):
    p = os.path.join(WR, "layers", f"{k}-free-alpha.png")
    return np.asarray(Image.open(p)).astype(np.float32) / 255 if os.path.exists(p) else alpha(k)


def iou(a, b):
    return float((a & b).sum() / max(1, (a | b).sum()))


def blob(mask):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if n < 2:
        return mask & False
    return lab == 1 + int(np.argmax(st[1:, 4]))


def main():
    out = {}
    below = R.scene()
    # ---------------------------------------------------------------- R1
    sil1, V1 = R.load_ph("r1")
    regt1 = np.load(os.path.join(WR, "r1-regt.npy")).astype(np.float32)
    dE1 = X.lab_diff(regt1, below, 1.0)
    idx = np.load(X.IDX_FULL, allow_pickle=True)["idx"]
    glaz = cv2.resize((idx == 4).astype(np.uint8), SIZE, interpolation=cv2.INTER_NEAREST).astype(bool)
    # curtains: the stack's width per row against the clay column, and any pixel over the glazing
    a = free_alpha("curtains") > 0.5
    s = sil1["curtains"] > 0.5
    rows = {}
    over = []
    for y in range(40, 1480, 20):
        ra, rs = np.nonzero(a[y])[0], np.nonzero(s[y])[0]
        if len(ra) and len(rs):
            over.append(int(ra.max() - rs.max()))
            if y % 200 == 0:
                rows[y] = dict(alpha_right_px=int(ra.max()), clay_right_px=int(rs.max()))
    d_c = 2.957
    out["curtains"] = dict(
        card="curtains-aliexpress-beige-linen-sheer-curtains-554205", option="hooks-top 150x270", sku="12000029601125492",
        plan="WMC7: one front stack X -2.29..-2.15, Y 2.65-2.95, track Z 2.86, to the floor; never over glazing",
        right_edge_beyond_clay_px=dict(median=float(np.median(over)), max=int(max(over)), min=int(min(over))),
        right_edge_beyond_clay_cm=dict(median=round(float(np.median(over)) / px_per_m_h(d_c) * 100, 1),
                                       max=round(max(over) / px_per_m_h(d_c) * 100, 1)),
        over_glazing_px=int((a & glaz).sum()), rows=rows,
        verdict="pass: the stack keeps the WMC7 width (its right edge follows the clay within a hem flare of a few cm) and covers 0 px of "
                "glazing; semi-sheer beige linen with slub, matte. Colour reads a little warmer / darker than the card's cream in the "
                "room's shaded front corner (the wall behind it is in shade; nothing bright behind it to show the sheerness)")
    # magazine holder: the cut against the projected skeleton (35 x 19 x 27.5, long side to the camera, at (-0.47, 2.57))
    a = alpha("magazine-holder") > 0.5
    v = V1["magazine-holder"] > 0.5
    arch_x = []
    for am in R.parts_rack()["arches"]:
        m = am > 0.5
        ys, xs = np.nonzero(m)
        top = ys.min()
        band = m[top:top + 8]
        arch_x.append(float(np.nonzero(band.any(0))[0].mean()))
    rend_x = []
    for x_c in arch_x:
        win = a[:, int(x_c) - 40:int(x_c) + 40]
        ys, xs = np.nonzero(win)
        top = ys.min()
        rend_x.append(float(np.nonzero(win[top:top + 8].any(0))[0].mean() + int(x_c) - 40))
    out["magazine-holder"] = dict(
        card="magazine-holder-cj-gunmetal-leather-strap", option="color orange, size small", sku="CJYD201631004DW",
        plan="slots 1.9.3 WMC9 / house plan 1.3.4: (-0.47, 2.57) on the rug, long side to the camera, 35 x 19 x 27.5 (Z 0.012-0.287); only "
             "Z > ~0.12 is inside the canvas (its foot is below the frame)",
        iou_cut_vs_skeleton_dil3=round(iou(a, X.dil(v, 3)), 3), cut_px=int(a.sum()), skeleton_px=int(v.sum()),
        arch_tops_x_px=dict(clay=[round(x, 1) for x in arch_x], render=[round(x, 1) for x in rend_x]),
        arch_spacing_cm=dict(clay=round((arch_x[1] - arch_x[0]) / px_per_m_h(2.425) * 100, 1),
                             render=round((rend_x[1] - rend_x[0]) / px_per_m_h(2.425) * 100, 1)),
        verdict="pass: the Orange SKU (glossy black arched tubes, cognac leather slings with rivets), long side to the camera, the arches "
                "and slings on the projected 35 x 19 x 27.5 skeleton; the rug in its gaps stays the rug layer's")
    # planter and basket: the rendered pot (its rim, fully visible) and the rendered basket (jute) against the clay
    lab_ = cv2.cvtColor(regt1, cv2.COLOR_RGB2LAB)
    C = np.hypot(lab_[..., 1], lab_[..., 2])
    box = np.zeros(dE1.shape, bool)
    box[880:1260, 880:1260] = True
    jute = box & (dE1 > 10) & (C > 22) & (lab_[..., 2] > 18)
    jute = blob(cv2.morphologyEx(jute.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)).astype(bool))
    pot = box & (dE1 > 6) & (C < 12) & ~X.dil(jute, 2)
    pot[:900] = False
    pot = blob(cv2.morphologyEx(pot.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)).astype(bool))
    ys, xs = np.nonzero(pot)
    w_rows = pot.sum(1)
    top = int(ys.min())
    rim_row = top + int(np.argmax(w_rows[top:top + 40]))
    rim_w = int(w_rows[rim_row])
    clay_pot = R.parts_planter()["pot"] > 0.5
    cys, cxs = np.nonzero(clay_pot)
    clay_w = int(clay_pot[cys.min():cys.min() + 40].sum(1).max())
    d_p = 4.999
    jy, jx = np.nonzero(jute)
    clay_b = R.parts_basket()["body"] > 0.5
    by, bx = np.nonzero(clay_b)

    def base_centre(m, r):
        """the base circle's nearest point is the mask's lowest pixel near the centre column; its centre is r behind it"""
        ys_, xs_ = np.nonzero(m)
        xc = 0.5 * (xs_.min() + xs_.max())
        col = m[:, int(xc) - 3:int(xc) + 4]
        yb = int(np.nonzero(col.any(1))[0].max())
        X_, Y_, d_ = unproject(xc, yb, 0.0)
        p = np.array([X_, Y_]) + r * FWD
        return [round(float(p[0]), 3), round(float(p[1]), 3)], float(xc), yb

    b_r, bxc, byb = base_centre(jute, 0.175 * (jx.max() - jx.min()) / (bx.max() - bx.min()))
    b_c, cxc, cyb = base_centre(clay_b, 0.175)
    out["planter"] = dict(
        card="planter-cj-cement-ribbed-belly", option="beige large", sku="CJJT154204209IR",
        plan="slots 1.9.1 WMC2: pot centre (-1.95, 0.42), d 42 x 35.5",
        rim_width_px=dict(clay=clay_w, render=rim_w), rim_width_cm=dict(clay=42.0, render=round(42.0 * rim_w / clay_w, 1)),
        scale=round(rim_w / clay_w, 3),
        hidden_by_basket_in_the_render=True,
        verdict="FAIL: drawn ~1.4-1.5x the card (rim ~60 cm, card 42) and its lower right is hidden by a basket that is itself off the plan; "
                "a size miss alone could be scaled in code, but the pot cannot be cut whole without that basket, so it cannot be layered alone")
    out["basket"] = dict(
        card="basket-cj-jute-rope-cylinder", option="large", sku="CJYD186026903CX",
        plan="slots 1.7 / 1.9: centre (-1.62, 0.78), d 35 x 39, IN FRONT of the pot",
        width_px=dict(clay=int(bx.max() - bx.min() + 1), render=int(jx.max() - jx.min() + 1)),
        width_cm=round(35.0 * (jx.max() - jx.min() + 1) / (bx.max() - bx.min() + 1), 1),
        centre_x_px=dict(clay=round(cxc, 1), render=round(bxc, 1)), base_bottom_y_px=dict(clay=cyb, render=byb),
        floor_centre_m=dict(plan=[-1.62, 0.78], clay_recovered=b_c, render=b_r),
        offset_cm=round(100 * math.hypot(b_r[0] + 1.62, b_r[1] - 0.78), 1),
        in_front_of_pot="overlaps the pot's right side (in front of it, nearer the camera), not as the plan: shifted right",
        verdict="FAIL (placement): in front of the pot this time, but ~20 cm right of / behind its plan place and ~15 % large; a placement "
                "miss is not fixed in code")
    # ---------------------------------------------------------------- R2
    sil2, V2 = R.load_ph("r2")
    regt2 = np.load(os.path.join(WR, "r2-regt.npy")).astype(np.float32)
    dE2 = X.lab_diff(regt2, below, 1.0)
    a = alpha("bowl") > 0.5
    v = V2["bowl"] > 0.5
    ys, xs = np.nonzero(a)
    cys, cxs = np.nonzero(v)
    d_b = 2.494
    dx_px, dy_px = float(xs.mean() - cxs.mean()), float(ys.mean() - cys.mean())
    out["bowl"] = dict(
        card="bowl-cj-matte-black-bowl-20", option="style 12 (the only identified variant)", sku="CJJT131449012LO",
        plan="step 0: (0.72, 1.94) on the coffee table (top Z 0.38), D20 x H8",
        iou_cut_vs_clay=round(iou(a, v), 3), width_px=dict(clay=int(cxs.max() - cxs.min() + 1), render=int(xs.max() - xs.min() + 1)),
        width_cm=round(20.0 * (xs.max() - xs.min() + 1) / (cxs.max() - cxs.min() + 1), 1),
        centroid_offset_px=[round(dx_px, 1), round(dy_px, 1)], centroid_offset_cm_h=round(dx_px / px_per_m_h(d_b) * 100, 1),
        verdict="pass: matte black porcelain, deep rounded body on a low foot ring, empty; at its checked place to the right of the candle "
                "holders, the card's size")
    # pendant: the shade's rows against the projection of the 50 cm tiered shade for a range of shade-bottom heights
    win = np.zeros(dE2.shape, bool)
    win[40:520, 1450:1880] = True
    pm = blob(cv2.morphologyEx((win & (dE2 > 8)).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool))
    rws = pm.sum(1)
    shade_rows = np.nonzero(rws > 40)[0]
    ys, xs = np.nonzero(pm)
    clay = sil2["pendant"] > 0.5
    crw = clay.sum(1)
    c_rows = np.nonzero(crw > 40)[0]
    fit = {}
    for zb in np.arange(1.70, 1.951, 0.01):
        bot = max(R.proj(S0.circ(0.20, 1.72, 0.15, zb))[:, 1])
        top = min(R.proj(S0.circ(0.20, 1.72, 0.13, zb + 0.28))[:, 1])
        fit[round(float(zb), 2)] = abs(bot - shade_rows.max()) + abs(top - shade_rows.min())
    zb_fit = min(fit, key=fit.get)
    d_pd = 2.913
    out["pendant"] = dict(
        card="pendant-cj-tiered-fabric-drum", option="Beige-50cm (the single variant)", sku="CJYD247032902BY",
        plan="slots 1.5 (V7Q7 b, the owner): hang point (0.20, 1.72), shade bottom Z 1.90; card Beige 50 (shade height ~28, step 0)",
        shade_rows_px=dict(clay=[int(c_rows.min()), int(c_rows.max())], render=[int(shade_rows.min()), int(shade_rows.max())]),
        width_px=dict(clay=int(np.nonzero(clay[c_rows.min():c_rows.max() + 1].any(0))[0].max() - np.nonzero(clay[c_rows.min():c_rows.max() + 1].any(0))[0].min() + 1), render=int(xs.max() - xs.min() + 1)),
        width_cm=round(50.0 * (xs.max() - xs.min() + 1) / (np.nonzero(clay[c_rows.min():c_rows.max() + 1].any(0))[0].max() - np.nonzero(clay[c_rows.min():c_rows.max() + 1].any(0))[0].min() + 1), 1),
        shade_bottom_Z_fit_m=zb_fit, drop_vs_plan_cm=round((1.90 - zb_fit) * 100, 1),
        centre_x_offset_cm=round((0.5 * (xs.min() + xs.max()) - 0.5 * (np.nonzero(clay[c_rows.min():c_rows.max() + 1].any(0))[0].min()
                                                                      + np.nonzero(clay[c_rows.min():c_rows.max() + 1].any(0))[0].max()))
                                 / px_per_m_h(d_pd) * 100, 1),
        verdict="FAIL (placement): the card's shade (five off-white fabric tiers, 50 cm) at the plan's X / Y, but hung ~11 cm low (shade "
                "bottom ~1.79-1.80 against the owner's 1.90, V7Q7 b); equivalently a larger shade further back. Not moved in code")
    json.dump(dict(date="2026-11-11", script=os.path.relpath(__file__, R.W.REPO), passes={"r1": R.PASSES["r1"], "r2": R.PASSES["r2"]},
                   products=out), open(os.path.join(WR, "fidelity-r12.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("verdict", "plan", "rows")} for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
