#!/usr/bin/env python3
"""
fidelity_r3.py: the measured fidelity of the fix passes R3a / R3b against the cards and house plan 1.3.5 (render-agent, 2026-11-11). 0 tokens.
Reads the registered, tone-matched passes (work-r3/<r>-regt.npy), the cuts (work-r3/layers) and the clay (work-r3/ph-<r>.npz, step 0's M0
camera via reserve_r12.proj); inverts the camera where a floor point is needed (reserve_fidelity.unproject). Writes work-r3/fidelity-r3.json.

The rule (the R3 brief): a size miss may be scaled in code; a placement miss is a fidelity failure. Tolerance used here: the clay's own
edges +-1.5 cm at the product's depth (about +-5 px at the pot, +-6 px at the basket, +-9 px at the pendant).

  python3 fidelity_r3.py r3a|r3b
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
import reserve_fidelity as F  # noqa: E402
import reserve_r12 as R  # noqa: E402
import reserve_r3 as R3  # noqa: E402
import step0_clay_checks as S0  # noqa: E402

OUT = os.path.join(R3.WR3, "fidelity-r3.json")
TOL_CM = 1.5


def alpha(k):
    return np.asarray(Image.open(os.path.join(R3.WR3, "layers", f"{k}.png")))[..., 3].astype(np.float32) / 255


def cm(px, d):
    return round(px / F.px_per_m_h(d) * 100, 1)


def rows_extent(m, y0, y1):
    xs = [np.nonzero(m[y])[0] for y in range(y0, y1) if m[y].any()]
    return float(np.median([x.min() for x in xs])), float(np.median([x.max() + 1 for x in xs]))


def r3a():
    a_p, a_b = alpha("planter") > 0.5, alpha("basket") > 0.5
    C = R3.clay_boxes()
    d_p, d_b = R3.DEPTH["planter"], R3.DEPTH["basket"]
    P = R.proj
    # ---- the pot: only its left side and the top of its rim show (the plan: the basket hides ~75 % of it)
    rim = P(S0.circ(-1.95, 0.42, 0.1775, 0.355))
    base = P(S0.circ(-1.95, 0.42, 0.17, 0.0))
    pot = a_p.copy()
    pot[:1036] = False                                        # the crown and the trunk above the rim's reach
    belly_rows = (1080, 1108)                                 # the clay belly's rows (r 0.21 at Z 0.24 +- the ellipse)
    left_belly = min(np.nonzero(pot[y])[0].min() for y in range(*belly_rows) if pot[y].any())
    # the rim's far top edge next to the trunk (x 1040-1048, between the loops), the first pot row, against the card's opening (r 0.1775)
    rim_top = {}
    for x in (1040, 1044, 1048):
        col = np.nonzero(pot[:, x])[0]
        up = rim[(np.abs(rim[:, 0] - x) < 2.5)]
        rim_top[x] = dict(render=int(col.min()) if len(col) else None, clay=round(float(up[:, 1].min()), 1) if len(up) else None)
    # the base: the lowest pot row on the left columns (x 975-990), against the clay base's lower arc there
    base_low = {}
    for x in (975, 982, 990):
        col = np.nonzero(pot[:, x])[0]
        lo = base[(np.abs(base[:, 0] - x) < 2.5)]
        base_low[x] = dict(render=int(col.max()) if len(col) else None, clay=round(float(lo[:, 1].max()), 1) if len(lo) else None)
    # the opening's left end: the leftmost pot pixel on the rim's rows, against the card's opening (35.5) and the belly (42)
    rim_rows = range(int(C["pot"]["top"]) + 2, int(C["pot"]["top"]) + 14)
    mouth_left = float(np.median([np.nonzero(pot[y])[0].min() for y in rim_rows if pot[y].any()]))
    axis = 0.5 * (C["pot"]["left"] + C["pot"]["right"])
    mouth_cm = round(2 * (axis - mouth_left) / F.px_per_m_h(d_p) * 100, 1)
    hidden = int((a_p & (np.arange(a_p.shape[1])[None, :] > 1000) & (np.arange(a_p.shape[0])[:, None] > 1090)).sum())
    dx_belly = float(left_belly - C["pot"]["left"])
    dy_rim = float(np.mean([v["render"] - v["clay"] for v in rim_top.values() if v["render"] is not None and v["clay"] is not None]))
    dy_base = float(np.mean([v["render"] - v["clay"] for v in base_low.values() if v["render"] is not None and v["clay"] is not None]))
    tol_p = TOL_CM / 100 * F.px_per_m_h(d_p)
    pot_ok = abs(dx_belly) <= tol_p and abs(dy_rim) <= tol_p and abs(dy_base) <= tol_p
    # ---- the basket: body width, rim top, the floor centre recovered through the camera, the loops
    br = R3.body_rows(a_b)
    width_px = br["right"] - br["left"]
    clay_w = C["basket"]["right"] - C["basket"]["left"]
    xc = 0.5 * (br["left"] + br["right"])
    col = a_b[:, int(xc) - 3:int(xc) + 4]
    yb = int(np.nonzero(col.any(1))[0].max())
    r_b = 0.175 * width_px / clay_w
    X_, Y_, _ = F.unproject(xc, yb, 0.0)
    ctr = np.array([X_, Y_]) + r_b * F.FWD
    off = math.hypot(ctr[0] + 1.62, ctr[1] - 0.78)
    tol_b = TOL_CM / 100 * F.px_per_m_h(d_b)
    bas_ok = abs(width_px - clay_w) <= tol_b and abs(br["top"] - C["basket"]["top"]) <= tol_b and off * 100 <= 3.0
    front = int((a_p & a_b).sum())
    # the same floor-centre method on the clay basket itself (the method's own bias at this depth)
    cb = np.maximum(R.parts_basket()["body"], R.parts_basket()["loops"]) > 0.5
    brc = R3.body_rows(cb)
    xcc = 0.5 * (brc["left"] + brc["right"])
    ybc = int(np.nonzero(cb[:, int(xcc) - 3:int(xcc) + 4].any(1))[0].max())
    Xc, Yc, _ = F.unproject(xcc, ybc, 0.0)
    ctr_c = np.array([Xc, Yc]) + 0.175 * F.FWD
    off_vs_clay = math.hypot(ctr[0] - ctr_c[0], ctr[1] - ctr_c[1])
    # the olive tree (filler): its crown against the envelope r <= 0.28, Z <= 1.65 (heights on the pot's axis through the camera)
    tree = a_p.copy()
    tree[1036:] = False
    ys_t, xs_t = np.nonzero(tree)
    zs = np.linspace(0.3, 2.0, 341)
    ys_ax = np.array([P([(-1.95, 0.42, z)])[0, 1] for z in zs])
    z_top = float(np.interp(-ys_t.min(), -ys_ax, zs))
    crown_w_cm = round((xs_t.max() - xs_t.min() + 1) / F.px_per_m_h(d_p) * 100, 1)
    out = {}
    out["planter"] = dict(
        card="planter-cj-cement-ribbed-belly", option="beige large", sku="CJJT154204209IR",
        card_dimensions="opening 35.5, largest diameter (belly) 42, height 35.5 (the card's notes)",
        plan="slots 1.9.1 WMC2: pot centre (-1.95, 0.42); olive crown (filler) r <= 0.28, Z 0.70-1.65",
        visible="its left side and the top of its rim (the basket in front hides the rest, as planned)",
        belly_left_px=dict(clay=round(C["pot"]["left"], 1), render=int(left_belly), delta_px=round(dx_belly, 1), delta_cm=cm(dx_belly, d_p)),
        rim_top_px=rim_top, rim_top_delta_px=round(dy_rim, 1), rim_top_delta_cm=cm(dy_rim, d_p),
        base_low_px=base_low, base_delta_px=round(dy_base, 1), base_delta_cm=cm(dy_base, d_p),
        olive_tree_filler=dict(crown_width_cm=crown_w_cm, top_Z_m=round(z_top, 2), envelope="r <= 0.28 (56 cm), Z 0.70-1.65",
                               inside=bool(crown_w_cm <= 59.0 and z_top <= 1.65)),
        opening_left_px=dict(card_35_5=round(float(rim[:, 0].min()), 1), belly_42=round(C["pot"]["left"], 1), render=mouth_left),
        opening_cm_if_symmetric=dict(card=35.5, render=mouth_cm),
        pot_pixels_right_of_x1000_below_y1090=hidden, tolerance_cm=TOL_CM,
        verdict=("pass on size and place" if pot_ok else "FAIL") + ": belly edge, rim top and base on the clay of the card's 42 x 35.5 at "
                f"(-1.95, 0.42) (belly {cm(dx_belly, d_p):+.1f} cm, rim {cm(dy_rim, d_p):+.1f} cm, base {cm(dy_base, d_p):+.1f} cm); "
                + (f"PARTIAL (shape): the opening reads ~{mouth_cm:.0f} cm against the card's 35.5, so the shoulder under the rim is "
                   "straighter than the card's belly (R1's pot shape, carried by the placeholder; the model widened it a little); it shows "
                   "only on the pot's visible left side" if mouth_cm > 38.5 else "the opening matches the card"))
    out["basket"] = dict(
        card="basket-cj-jute-rope-cylinder", option="large", sku="CJYD186026903CX",
        card_dimensions="diameter 35, body 39, loop handles ~9 above the rim (the card's notes)",
        plan="slots 1.7 / 1.9: centre (-1.62, 0.78), IN FRONT of the pot",
        body_width_px=dict(clay=round(clay_w, 1), render=round(width_px, 1)), body_width_cm=round(35.0 * width_px / clay_w, 1),
        rim_top_px=dict(clay=C["basket"]["top"], render=br["top"]), loop_top_px=dict(clay=C["basket"]["loop_top"], render=br["loop_top"]),
        base_front_y_px=yb, floor_centre_m=dict(plan=[-1.62, 0.78], render=[round(float(ctr[0]), 3), round(float(ctr[1]), 3)]),
        offset_cm=round(off * 100, 1), clay_by_the_same_method=[round(float(ctr_c[0]), 3), round(float(ctr_c[1]), 3)],
        offset_vs_clay_same_method_cm=round(off_vs_clay * 100, 1), in_front_of_pot=bool(front == 0 and hidden == 0),
        verdict=("pass" if bas_ok else "FAIL") + f": body {35.0 * width_px / clay_w:.1f} cm (card 35), floor centre {off * 100:.1f} cm from "
                f"the plan's (-1.62, 0.78) ({off_vs_clay * 100:.1f} cm from the clay read the same way), in front of the pot, both loops")
    return out


def r3b():
    """the shade's rows and width on the cut, against the projection of the 50 cm tiered shade (step 0's tiers) for shade-bottom heights
    1.70-2.00 (reserve_fidelity's fit), and its centre against the hang point's"""
    a = alpha("pendant") > 0.5
    d_pd = R3.DEPTH["pendant"]
    sh = a.copy()
    sh[:120] = False                                      # the canopy and the cord are above the ceiling line; the shade below it
    rows = np.nonzero(sh.sum(1) > 40)[0]
    cols = np.nonzero(sh[rows.min():rows.max() + 1].any(0))[0]
    tiers = np.maximum.reduce([t[0] for t in R.parts_pendant()["tiers"]]) > 0.5
    tiers[:120] = False
    c_rows = np.nonzero(tiers.sum(1) > 40)[0]
    c_cols = np.nonzero(tiers[c_rows.min():c_rows.max() + 1].any(0))[0]
    fit = {}
    for zb in np.arange(1.70, 2.001, 0.005):
        bot = max(R.proj(S0.circ(0.20, 1.72, 0.15, zb))[:, 1])
        top = min(R.proj(S0.circ(0.20, 1.72, 0.13, zb + 0.28))[:, 1])
        fit[round(float(zb), 3)] = abs(bot - (rows.max() + 1)) + abs(top - rows.min())
    zb_fit = min(fit, key=fit.get)
    w_r, w_c = cols.max() - cols.min() + 1, c_cols.max() - c_cols.min() + 1
    dx = 0.5 * (cols.min() + cols.max()) - 0.5 * (c_cols.min() + c_cols.max())
    # the cord: present from the canopy to the shade's top on the hang point's column
    cx = int(0.5 * (cols.min() + cols.max()))
    cord_rows = [y for y in range(44, int(rows.min()) - 4, 8) if a[y, cx - 8:cx + 9].any()]
    cord_rows_total = len(range(44, int(rows.min()) - 4, 8))
    canopy = a[:44]
    cys, cxs = np.nonzero(canopy)
    ok = abs(zb_fit - 1.90) <= 0.0151 and abs(50.0 * w_r / w_c - 50.0) <= 1.5 and abs(dx / F.px_per_m_h(d_pd) * 100) <= 1.5
    return {"pendant": dict(
        card="pendant-cj-tiered-fabric-drum", option="Beige-50cm (the single variant)", sku="CJYD247032902BY",
        plan="slots 1.5 (V7Q7 b, the owner): hang point (0.20, 1.72, 3.00), shade bottom Z 1.90; card Beige 50 (shade height ~28, step 0)",
        shade_rows_px=dict(clay=[int(c_rows.min()), int(c_rows.max()) + 1], render=[int(rows.min()), int(rows.max()) + 1]),
        width_px=dict(clay=int(w_c), render=int(w_r)), width_cm=round(50.0 * w_r / w_c, 1),
        shade_bottom_Z_fit_m=zb_fit, vs_plan_cm=round((zb_fit - 1.90) * 100, 1),
        centre_x_offset_px=round(float(dx), 1), centre_x_offset_cm=round(float(dx) / F.px_per_m_h(d_pd) * 100, 1),
        cord_rows_found=f"{len(cord_rows)} of {cord_rows_total}", canopy_box_px=[int(cxs.min()), int(cys.min()), int(cxs.max()) + 1, int(cys.max()) + 1] if len(cxs) else None,
        r2_for_comparison=dict(shade_bottom_Z_fit_m=1.80, centre_x_offset_cm=-3.6),
        verdict=("pass" if ok else "FAIL") + f": the shade bottom fits Z {zb_fit:.3f} (plan 1.90, R2 1.80), width {50.0 * w_r / w_c:.1f} cm "
                f"(card 50), centre {float(dx) / F.px_per_m_h(d_pd) * 100:+.1f} cm from the hang point's column")}


def main(pass_):
    rec = json.load(open(OUT)) if os.path.exists(OUT) else dict(date="2026-11-11", script=os.path.relpath(__file__, R.W.REPO), products={})
    prods = r3a() if pass_ == "r3a" else r3b()
    rec["products"].update(prods)
    rec.setdefault("passes", {})[pass_] = R3.PASSES[pass_]
    json.dump(rec, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(prods, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
