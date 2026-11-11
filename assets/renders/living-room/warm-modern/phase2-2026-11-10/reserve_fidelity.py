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


def curtain_colour():
    """median L*, chroma and hue of the curtain layer (opaque pixels), the card's crop (scratchpad, if present) and white plaster nearby"""
    def stats(lab):
        L_, a_, b_ = np.median(lab.reshape(-1, 3), 0)
        return dict(L=round(float(L_), 1), C=round(float(np.hypot(a_, b_)), 1), hue_deg=round(float(np.degrees(np.arctan2(b_, a_))), 1))
    lay = os.path.join(HERE, "layers/curtains/curtains-aliexpress-beige-linen-sheer-curtains-554205.png")
    L = np.asarray(Image.open(lay)).astype(np.float32) / 255
    out = dict(layer=stats(cv2.cvtColor(L[..., :3], cv2.COLOR_RGB2LAB)[L[..., 3] > 0.99]))
    ref = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/ph2/refs/curtains-weave.png"
    if os.path.exists(ref):
        out["card_crop_supplier_photo"] = stats(cv2.cvtColor(np.asarray(Image.open(ref).convert("RGB")).astype(np.float32) / 255, cv2.COLOR_RGB2LAB))
    g = np.asarray(Image.open(os.path.join(HERE, "graded/default-scene-r12-set-B-graded-v3c.png")).convert("RGB")).astype(np.float32) / 255
    gl = cv2.cvtColor(g, cv2.COLOR_RGB2LAB)
    out["room_white_plaster"] = dict(window_lining=stats(gl[250:700, 780:850]), back_wall=stats(gl[250:450, 1700:2000]))
    return out


def main():
    out = {}
    below = R.scene()
    # ---------------------------------------------------------------- R1
    sil1, V1 = R.load_ph("r1")
    regt1 = np.load(os.path.join(WR, "r1-regt.npy")).astype(np.float32)
    dE1 = X.lab_diff(regt1, below, 1.0)
    idx = np.load(X.IDX_FULL, allow_pickle=True)["idx"]
    glaz = cv2.resize((idx == 4).astype(np.uint8), SIZE, interpolation=cv2.INTER_NEAREST).astype(bool)
    # curtains: the stack's width per row against the clay column, and what it covers of the glass. The r4 index: 4 = the window's frame
    # and mullions, 0 between them = the view through the glass; the first pane's visible strip is x 242-287 at the work size, and the
    # clay column itself ends at 241-244 (it abuts the glass by design, WMC7)
    a = free_alpha("curtains") > 0.5
    s = sil1["curtains"] > 0.5
    small = cv2.resize(idx.astype(np.int32), SIZE, interpolation=cv2.INTER_NEAREST)
    glass = np.zeros(SIZE[::-1], bool)
    glass[:, 242:288] = small[:, 242:288] == 0             # the first pane's visible strip (between the stack and the first mullion)
    glass |= (small == 4) & (np.arange(SIZE[0])[None, :] < 288)
    rows, over = {}, []
    for y in range(40, 1480, 20):
        ra, rs = np.nonzero(a[y])[0], np.nonzero(s[y])[0]
        if len(ra) and len(rs):
            over.append(int(ra.max() - rs.max()))
            if y % 200 == 0:
                rows[y] = dict(alpha_right_px=int(ra.max()), clay_right_px=int(rs.max()),
                               inner_edge_frame_u=round((ra.max() / SIZE[0] * S0.GW - S0.CX) / S0.CW, 4))
    d_c = 2.957
    cov = (a & glass)
    cov_rows = cov.sum(1)
    # the designer's condition (docs/proposals/wm-phase2-f3-decisions-2026-11-11.md 2.5): the armchair's overlap of the stack, >= 0.028,
    # measured as step 0 does (thickness = 2 x the largest inscribed radius of stack AND armchair on the 4072 x 2290 canvas / 3840). The
    # layer has no pixels behind the armchair (it is cut away), so the stack there is rebuilt: from the armchair's top row down to the
    # clay's floor line, from the left edge to the stack's inner edge held at its median over the last 40 visible rows (a lower bound:
    # the hem only flares outward)
    fa = R.W.furn_alpha()
    arm = fa > 0.5
    arm[:, 1000:] = False                                  # the armchair only (the sofa and the table are far right)
    top = int(np.nonzero(arm[:, :270].any(1))[0].min())
    R0 = int(np.median([np.nonzero(a[y])[0].max() for y in range(top - 40, top)]))
    real = a.copy()
    for y in range(top, SIZE[1]):
        if s[y].any():
            real[y, :R0 + 1] = True
    up = lambda m: cv2.resize(m.astype(np.uint8), (S0.GW, S0.GH), interpolation=cv2.INTER_NEAREST).astype(bool)  # noqa: E731
    th_real, th_clay = S0.thickness(up(real & arm)) / S0.CW, S0.thickness(up(s & arm)) / S0.CW
    out["curtains_vs_armchair"] = dict(
        rule="the designer (2026-11-11, 2.5): accepted as a clear overlap only if >= 0.028 in the real layer; step 0's clay: 0.0295",
        method="stack AND armchair, thickness on the canvas / 3840 (step 0's code); the stack behind the armchair rebuilt with its inner edge "
               f"held at x {R0} (work px) from the armchair's top row {top} to the floor line",
        overlap_thickness_real_layer=round(float(th_real), 4), overlap_thickness_clay_same_code=round(float(th_clay), 4),
        armchair_top_row_px=top, stack_inner_edge_px=R0, stack_inner_edge_frame_u=round((R0 / SIZE[0] * S0.GW - S0.CX) / S0.CW, 4),
        passes_0_028=bool(th_real >= 0.028),
        variants_note="the designer: in the variants the stack's inner (room-side) edge stays at R1's, +-0.003 u (= +-7.7 px here)")
    out["curtains"] = dict(
        card="curtains-aliexpress-beige-linen-sheer-curtains-554205", option="hooks-top 150x270", sku="12000029601125492",
        plan="WMC7: one front stack X -2.29..-2.15, Y 2.65-2.95, track Z 2.86, to the floor; never over glazing",
        right_edge_beyond_clay_px=dict(median=float(np.median(over)), max=int(max(over))),
        right_edge_beyond_clay_cm=dict(median=round(float(np.median(over)) / px_per_m_h(d_c) * 100, 1),
                                       max=round(max(over) / px_per_m_h(d_c) * 100, 1)),
        first_pane_strip_px_wide=46, over_glass_px=int(cov.sum()), over_glass_rows=int((cov_rows > 0).sum()),
        over_glass_px_per_row=dict(median=float(np.median(cov_rows[cov_rows > 0])) if cov.any() else 0.0, max=int(cov_rows.max())),
        rows=rows,
        colour=curtain_colour(),
        verdict="PARTIAL (colour), geometry pass. Colour: the layer reads a warm flax / oatmeal (median chroma ~15, hue ~75 deg) where the "
                "card's photo is a pale cream (chroma ~7, hue ~93 deg) and the room's white plaster stays near neutral (chroma 2-5), so the room's "
                "light does not explain it; not recoloured in code (no separate grade; for QA / the designer). Geometry: the stack keeps the WMC7 width (step 2 drew it twice as wide, over the whole first pane). Its "
                "inner edge follows the clay from the track down and the hem flares out to ~2.6 cm beyond it, so the soft edge lies over the "
                "first pane's 46 px glass strip by a median ~10 px (max 17) in the lower rows. Semi-sheer beige linen with slub, matte; it reads "
                "a little warmer and darker than the card's cream in the room's shaded front corner")
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
    # planter and basket. The basket: GrabCut on the render seeded in its body's core (read off the overlay), the pot and the crown
    # marked as background. The pot (the same colour as the wall, so no mask): its rim's two silhouette edges on the rows across the rim,
    # the strongest horizontal gradients of L* left and right of the trunk
    x0, y0, x1, y1 = 880, 560, 1280, 1290
    sub = (regt1[y0:y1, x0:x1] * 255).astype(np.uint8)
    d_ = dE1[y0:y1, x0:x1]
    gcm = np.full(sub.shape[:2], cv2.GC_PR_BGD, np.uint8)
    gcm[d_ < 3] = cv2.GC_BGD
    gcm[d_ > 10] = cv2.GC_PR_FGD
    for (bx0, by0, bx1, by1) in ((940, 990, 1040, 1170), (950, 620, 1100, 800)):
        gcm[by0 - y0:by1 - y0, bx0 - x0:bx1 - x0] = cv2.GC_BGD
    gcm[1080 - y0:1190 - y0, 1085 - x0:1185 - x0] = cv2.GC_FGD
    cv2.grabCut(sub[..., ::-1].copy(), gcm, None, np.zeros((1, 65)), np.zeros((1, 65)), 8, cv2.GC_INIT_WITH_MASK)
    f = np.isin(gcm, (cv2.GC_FGD, cv2.GC_PR_FGD))
    n, lab, st, _ = cv2.connectedComponentsWithStats(f.astype(np.uint8))
    jute = np.zeros(SIZE[::-1], bool)
    jute[y0:y1, x0:x1] = lab == lab[1135 - y0, 1135 - x0]
    Ls = cv2.GaussianBlur(cv2.cvtColor(regt1, cv2.COLOR_RGB2LAB)[..., 0], (0, 0), 1.2)
    gx = np.abs(cv2.Sobel(Ls, cv2.CV_32F, 1, 0, ksize=3))
    rim = []
    for y in range(968, 980):
        rim.append((int(900 + np.argmax(gx[y, 900:990])), int(1100 + np.argmax(gx[y, 1100:1170]))))
    rim_l, rim_r = int(np.median([r_[0] for r_ in rim])), int(np.median([r_[1] for r_ in rim]))
    rim_w = rim_r - rim_l + 1
    clay_pot = R.parts_planter()["pot"] > 0.5
    cys, cxs = np.nonzero(clay_pot)
    clay_w = int(clay_pot[cys.min():cys.min() + 40].sum(1).max())
    clay_b = R.parts_basket()["body"] > 0.5
    by, bx = np.nonzero(clay_b)

    def body_width(m):
        ys_, xs_ = np.nonzero(m)
        h = ys_.max() - ys_.min()
        band = m[ys_.min() + int(0.4 * h):ys_.max() - int(0.1 * h)]
        return int(np.median(band.sum(1)))

    def base_centre(m, r):
        """the base circle's nearest point is the mask's lowest pixel near the centre column; the centre is r behind it"""
        ys_, xs_ = np.nonzero(m)
        xc = 0.5 * (xs_.min() + xs_.max())
        col = m[:, int(xc) - 3:int(xc) + 4]
        yb = int(np.nonzero(col.any(1))[0].max())
        X_, Y_, d_b = unproject(xc, yb, 0.0)
        p = np.array([X_, Y_]) + r * FWD
        return [round(float(p[0]), 3), round(float(p[1]), 3)], float(xc), yb

    wb_r, wb_c = body_width(jute), body_width(clay_b)
    b_r, bxc, byb = base_centre(jute, 0.175 * wb_r / wb_c)
    b_c, cxc, cyb = base_centre(clay_b, 0.175)
    np.savez_compressed(os.path.join(WR, "r1-basket-mask.npz"), basket=jute)
    out["planter"] = dict(
        card="planter-cj-cement-ribbed-belly", option="beige large", sku="CJJT154204209IR",
        plan="slots 1.9.1 WMC2: pot centre (-1.95, 0.42), d 42 x 35.5",
        rim_edges_px=dict(render=[rim_l, rim_r]), rim_width_px=dict(clay=clay_w, render=rim_w),
        rim_width_cm=dict(card=42.0, render=round(42.0 * rim_w / clay_w, 1)), scale=round(rim_w / clay_w, 3),
        base_centre_kept="its base stays at the plan's place (the pot grew upward and outward from it)",
        hidden_by_basket_in_the_render="its lower right (x ~1058-1135) is behind the rendered basket",
        verdict="FAIL: drawn ~1.36x the card (rim ~57 cm against 42, ~48 cm tall against 35.5). A size miss alone could be scaled in code, "
                "but its lower right is hidden by the rendered basket, which is itself off the plan, so the pot cannot be cut whole and "
                "cannot be layered without that basket")
    out["basket"] = dict(
        card="basket-cj-jute-rope-cylinder", option="large", sku="CJYD186026903CX",
        plan="slots 1.7 / 1.9: centre (-1.62, 0.78), d 35 x 39, IN FRONT of the pot",
        mask="GrabCut on the render (work-reserve/r1-basket-mask.npz)",
        body_width_px=dict(clay=wb_c, render=wb_r), body_width_cm=round(35.0 * wb_r / wb_c, 1),
        centre_x_px=dict(clay=round(cxc, 1), render=round(bxc, 1)), base_lowest_y_px=dict(clay=cyb, render=byb),
        floor_centre_m=dict(plan=[-1.62, 0.78], clay_recovered=b_c, render=b_r),
        offset_cm=round(100 * math.hypot(b_r[0] + 1.62, b_r[1] - 0.78), 1),
        in_front_of_pot="yes this time: it stands nearer the camera and hides the pot's lower right (step 2 had it beside the pot)",
        verdict="FAIL (placement): in front of the pot, but its floor centre is off the plan's (-1.62, 0.78) (see offset_cm) and it is a "
                "little large; a placement miss is not fixed in code")
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
        verdict="pass on the card (shape, colour, size) and on step 0's position; the position itself is PROVISIONAL, pending WM-T2 (the "
                "designer, 2026-11-11: (0.72, 1.94) is 0.009 from the throw; the table group may move left under the pendant)")
    gaps = {}
    for s_ in "ABC":
        ca = np.asarray(Image.open(os.path.join(R.W.P1, f"layers/cushions/set-{s_}.png")))[..., 3] > 127
        dt = cv2.distanceTransform((~ca).astype(np.uint8), cv2.DIST_L2, 5)
        g = float(dt[a].min()) if not (a & ca).any() else 0.0
        gaps[s_] = round(g / (S0.CW / S0.GW * SIZE[0]), 4)
    out["bowl"]["gap_to_cushion_set_frame"] = gaps
    out["bowl"]["gap_rule"] = "F3: a gap < 0.02 of the frame width is 'kissing contours' (fails); WM-T2 is needed for the variants anyway (2.4)"
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
