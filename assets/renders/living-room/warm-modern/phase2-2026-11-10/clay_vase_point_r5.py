#!/usr/bin/env python3
"""
clay_vase_point_r5.py: the vases' one point, in clay, before pass 4' (render-agent, 2026-11-11). 0 tokens, no var2, no network.
Brief: briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md section 1; the designer's rule: docs/proposals/wm-phase2-checkpoint-eye-2026-11-11.md
section 2 ("before 4', in clay").

The three vases at their card sizes, each with the SAME dry olive branch (to Z 1.05), on the limestone bench (Z 0.45), at each candidate
point in the designer's order (all within 0.10 of the slot's (-2.42, 1.35)):
  1. (-2.42, 1.35)   2. (-2.42, 1.30)   3. (-2.45, 1.30)
  default   vase-cj-textured-white-stoneware  Large  D16 x H32 (mouth 9)
  vase 2    vase-cj-charcoal-carved           Style B  W22 x H32 (mouth ~13)
  vase 3    vase-cj-white-plum-hand-thrown    M  W22.4 x H33 (mouth 3.3)
Each body is the card's bounding cylinder (the widest the vase can be at every height: the conservative clay, as step 0 drew the default);
the branch is step 0's cone (r 0.02 -> 0.11, from the mouth to Z 1.05).

The conditions (section 2):
  (a) F3 against the armchair: >= 0.02 of the frame width. Measured two ways, both must pass: against the armchair of step 0's clay
      (the r4 furniture index, the F3 authority; step 0 read 0.0229 for the default at point 1) and against the armchair as the base draws
      it (phase 1's fixed-furniture alpha, the armchair's component), so the picture agrees with the clay.
  (b) the body does not run along a bronze profile (the mullion at Y 1.45 and the end profile at Y 0.75, both in the frame plane X -2.65,
      Z 0.45-2.70): in every row of the body (Z 0.45 to the rim; the branch is not the body) the profile's strip is either >= 0.01 of the
      frame width from the body's contour, or wholly inside the body with >= 0.005 of the frame on each side ("clearly crossing": it
      reads as passing behind the vase, never as an edge along it); a strip that meets the contour fails. The strips are the base's own
      dark bronze (L* < 50, the columns round each projected line, per row; the rendered profiles sit on the projected lines within
      ~1-8 px), and the projected lines with the plan's widest profile (8 cm) are reported beside them.
  The point is the first in the list where all three vases pass (a) and (b). If none passes: the table goes back to the designer and 4'
  goes without the vase.

Writes (new files): step0/vase-point-r5.json, step0/vase-point-r5-overlay.jpg.
  python3 clay_vase_point_r5.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "step0"))
import step0_clay_checks as S0  # noqa: E402

P1 = S0.P1
CW, CH, CX, CY, GW, GH = S0.CW, S0.CH, S0.CX, S0.CY, S0.GW, S0.GH
POINTS = [(-2.42, 1.35), (-2.42, 1.30), (-2.45, 1.30)]
SLOT = (-2.42, 1.35)
Z0 = 0.45
VASES = {
    "vase-cj-textured-white-stoneware": dict(role="default", sku="CJJT312391803CX", option="Large", D=0.16, H=0.32, mouth=0.09),
    "vase-cj-charcoal-carved": dict(role="vase 2 (pass 5')", sku="CJJT276474102BY", option="Style B", D=0.22, H=0.32, mouth=0.13),
    "vase-cj-white-plum-hand-thrown": dict(role="vase 3 (pass 6')", sku="CJJT281811802BY", option="M", D=0.224, H=0.33, mouth=0.033),
}
PROFILES = {"mullion_Y1.45": (-2.65, 1.45), "end_profile_Y0.75": (-2.65, 0.75)}
PLAN_PROFILE_W = 0.08                                  # the plan's widest frame profile (house-plan.json: 'profile 3-8 cm')
F3_MIN, PROFILE_GAP, CROSS_MARGIN = 0.02, 0.01, 0.005


def solids(cx, cy, v):
    body = S0.cyl(cx, cy, v["D"] / 2, Z0, Z0 + v["H"])
    branch = S0.cone(cx, cy, 0.02, 0.11, Z0 + v["H"], 1.05, 24)
    return body, branch


def body_rows(cx, cy, v):
    """per canvas row of the body: its left and right contour (the projected circles of the cylinder at each height)"""
    out = {}
    for z in np.linspace(Z0, Z0 + v["H"], 400):
        pts = [S0.P(cx + v["D"] / 2 * math.cos(t), cy + v["D"] / 2 * math.sin(t), z) for t in np.linspace(0, 2 * math.pi, 180)]
        xs = [CX + u * CW for u, _, _ in pts]
        ys = [CY + vv * CH for _, vv, _ in pts]
        for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
            l_, r_ = out.get(y, (1e9, -1e9))
            out[y] = (min(l_, min(xs)), max(r_, max(xs)))
    return out


def rendered_profiles():
    """the base's dark bronze strips per canvas row, round each projected profile line: (x0, x1) in canvas px, or None"""
    b = np.asarray(Image.open(os.path.join(HERE, "layers/base.png")).convert("RGB")).astype(np.float32) / 255
    L = cv2.cvtColor(b, cv2.COLOR_RGB2LAB)[..., 0]
    sx = GW / b.shape[1]
    out = {}
    for name, (X, Y) in PROFILES.items():
        u = S0.P(X, Y, 1.0)[0]
        xw = (CX + u * CW) / sx
        x0, x1 = int(xw - 30), int(xw + 30)
        _, v_top, _ = S0.P(X, Y, 2.70)
        _, v_bot, _ = S0.P(X, Y, Z0)
        rows = {}
        for yw in range(int((CY + v_top * CH) / sx) + 2, int((CY + v_bot * CH) / sx) - 1):
            dark = np.nonzero(L[yw, x0:x1] < 50)[0]
            if not len(dark):
                continue
            # the longest run of dark columns (the profile), allowing 1-column gaps
            runs, s, p = [], dark[0], dark[0]
            for c in dark[1:]:
                if c > p + 2:
                    runs.append((s, p))
                    s = c
                p = c
            runs.append((s, p))
            s, p = max(runs, key=lambda r_: r_[1] - r_[0])
            rows[yw] = ((x0 + s) * sx, (x0 + p + 1) * sx)
        # the vertical profile only: where it meets the horizontal bottom rail (at the sill) the dark run widens sideways; the vase
        # crosses that rail (a horizontal line), it cannot run along it. Rows wider than 1.5 x the profile's median width, or off its
        # median centre by more than half that width, are the rail (or a reflection), not the profile
        if rows:
            wmed = float(np.median([r_[1] - r_[0] for r_ in rows.values()]))
            cmed = float(np.median([(r_[0] + r_[1]) / 2 for r_ in rows.values()]))
            dropped = [y for y, r_ in rows.items() if (r_[1] - r_[0]) > 1.5 * wmed or abs((r_[0] + r_[1]) / 2 - cmed) > 0.5 * wmed]
            for y in dropped:
                rows.pop(y)
        out[name] = dict(projected_u=round(u, 4), projected_canvas_x=round(CX + u * CW, 1), rows_work=rows,
                         rendered_width_canvas_px_median=round(float(np.median([r_[1] - r_[0] for r_ in rows.values()])), 1) if rows else None,
                         rendered_centre_canvas_x_median=round(float(np.median([(r_[0] + r_[1]) / 2 for r_ in rows.values()])), 1) if rows else None)
    return out, sx


def projected_profile(name):
    X, Y = PROFILES[name]
    us = [S0.P(X, Y + d, 1.0)[0] for d in (-PLAN_PROFILE_W / 2, PLAN_PROFILE_W / 2)]
    us += [S0.P(X + d, Y, 1.0)[0] for d in (-0.02, 0.02)]   # the profile's depth (~4 cm) also shows
    return CX + min(us) * CW, CX + max(us) * CW


def profile_check(rows_body, strip_for_row):
    """min over the body's rows: the strip outside the body -> its gap to the contour (positive); inside -> its margin to the nearer
    contour (positive, 'inside'); meeting the contour -> negative overlap (fails)"""
    worst = None
    for y, (bl, br) in rows_body.items():
        s = strip_for_row(y)
        if s is None:
            continue
        p0, p1 = s
        if p1 <= bl:
            val, kind = bl - p1, "outside"
        elif p0 >= br:
            val, kind = p0 - br, "outside"
        elif p0 >= bl and p1 <= br:
            val, kind = min(p0 - bl, br - p1), "inside"
        else:
            val, kind = -min(p1 - bl, br - p0), "meets the contour"
        need = PROFILE_GAP if kind == "outside" else CROSS_MARGIN
        slack = val / CW - need if kind != "meets the contour" else val / CW - 1.0
        rec = dict(row_canvas=y, gap_px=round(val, 1), gap_frame=round(val / CW, 4), kind=kind, need=need,
                   ok=bool(kind != "meets the contour" and val / CW >= need), _slack=slack)
        if worst is None or slack < worst["_slack"]:
            worst = rec
    if worst is None:
        return dict(kind="no common rows", ok=True, need=None)
    worst.pop("_slack")
    return worst


def main():
    idx = np.load(S0.IDX_FURN, allow_pickle=True)["idx"]
    arm_clay = idx == S0.FURN["armchair"]
    fa = np.asarray(Image.open(os.path.join(P1, "fixed-furniture.png")))[..., 3]
    fa_c = cv2.resize((fa > 127).astype(np.uint8), (GW, GH), interpolation=cv2.INTER_NEAREST).astype(bool)
    n, lab = cv2.connectedComponents(fa_c.astype(np.uint8))
    ids = [i for i in np.unique(lab[S0.ero(arm_clay, 2) if hasattr(S0, "ero") else cv2.erode(arm_clay.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)]) if i > 0]
    arm_render = np.isin(lab, ids) & cv2.dilate(arm_clay.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    rend, sx = rendered_profiles()
    table, first = [], None
    for i, (cx, cy) in enumerate(POINTS, 1):
        prow = dict(point=i, xy=[cx, cy], from_slot_m=round(math.hypot(cx - SLOT[0], cy - SLOT[1]), 3), vases={})
        allok = True
        for card, v in VASES.items():
            body, branch = solids(cx, cy, v)
            sil = S0.raster([body, branch])
            silb = S0.raster([body])
            g_clay = S0.min_dist(sil, arm_clay) / CW
            g_rend = S0.min_dist(sil, arm_render) / CW
            rb = body_rows(cx, cy, v)
            prof = {}
            for name, R in rend.items():
                rows = R["rows_work"]

                def strip_r(y, rows=rows):
                    yw = int(round(y / sx))
                    return rows.get(yw)
                pp = projected_profile(name)
                prof[name] = dict(rendered=profile_check(rb, strip_r),
                                  projected_8cm=profile_check(rb, lambda y, pp=pp: pp))
            ok_a = g_clay >= F3_MIN and g_rend >= F3_MIN
            ok_b = all(p["rendered"]["ok"] and p["projected_8cm"]["ok"] for p in prof.values())
            ys, xs = np.nonzero(silb)
            u_ = S0.P(cx, cy, Z0)
            prow["vases"][card] = dict(role=v["role"], size_cm=[round(v["D"] * 100, 1), round(v["H"] * 100, 1)],
                                       body_frame_box=[round((xs.min() - CX) / CW, 4), round((xs.max() + 1 - CX) / CW, 4),
                                                       round((ys.min() - CY) / CH, 4), round((ys.max() + 1 - CY) / CH, 4)],
                                       base_centre_work_px=[round((CX + u_[0] * CW) / sx, 1), round((CY + u_[1] * CH) / sx, 1)], depth_m=round(u_[2], 3),
                                       armchair=dict(clay_gap_frame=round(g_clay, 4), render_gap_frame=round(g_rend, 4), ok=bool(ok_a)),
                                       bronze=prof, bronze_ok=bool(ok_b), passes=bool(ok_a and ok_b))
            allok &= ok_a and ok_b
        prow["all_three_pass"] = bool(allok)
        table.append(prow)
        if allok and first is None:
            first = i
    chosen = None if first is None else table[first - 1]
    out = dict(date="2026-11-11", author="render-agent", tokens=0, script=os.path.relpath(__file__, S0.REPO),
               brief="briefs/render-wm-tool-phase2-steps4-5-2026-11-11.md section 1",
               rule="docs/proposals/wm-phase2-checkpoint-eye-2026-11-11.md section 2: the first point where all three vases at card size pass "
                    "(F3 >= 0.02 vs the armchair; the body never runs along the bronze mullion Y 1.45 or the end profile Y 0.75: >= 0.01, or "
                    "clearly crossing)",
               method=dict(camera="house plan M0 via step0_clay_checks.P (verticals stay vertical: no pitch)",
                           bodies="the card's bounding cylinder (widest at every height), Z 0.45 to 0.45 + H; branch = step 0's cone to Z 1.05, the same for all",
                           armchair=dict(clay="step 0's r4 furniture index (the F3 authority)", render="phase 1's fixed-furniture alpha, the armchair's component"),
                           bronze=dict(rendered="the base's dark strip (L* < 50) per row, round each projected line; checked per body row",
                                       projected="the plan line +- 4 cm (the widest 8 cm profile) and its 4 cm depth",
                                       crossing="a strip wholly inside the body with >= 0.005 of the frame each side passes ('clearly crossing')"),
                           frame_width_px=CW),
               profiles_rendered_vs_projected={k: {kk: vv for kk, vv in r.items() if kk != "rows_work"} for k, r in rend.items()},
               table=table, chosen_point=None if chosen is None else dict(index=first, xy=chosen["xy"], from_slot_m=chosen["from_slot_m"]),
               verdict=("point %d %s: all three vases pass; vase 1 is re-rendered there in 4', vase 2 in 5', vase 3 in 6'" % (first, chosen["xy"]))
               if chosen else "NO point passes for all three: back to the designer with this table; 4' goes without the vase")
    json.dump(out, open(os.path.join(HERE, "step0/vase-point-r5.json"), "w"), indent=1, ensure_ascii=False)
    overlay(table, first, arm_clay, arm_render, rend, sx)
    for p in table:
        print(p["point"], p["xy"], "ALL PASS" if p["all_three_pass"] else "fails")
        for c, r in p["vases"].items():
            print("   %-34s arm clay %.4f render %.4f | %s" % (c, r["armchair"]["clay_gap_frame"], r["armchair"]["render_gap_frame"],
                  " | ".join("%s %s %.4f/%s %.4f" % (k, b["rendered"]["kind"], b["rendered"].get("gap_frame", 0) or 0, b["projected_8cm"]["kind"],
                                                    b["projected_8cm"].get("gap_frame", 0) or 0) for k, b in r["bronze"].items())), "PASS" if r["passes"] else "FAIL")
    print(out["verdict"])


def overlay(table, first, arm_clay, arm_render, rend, sx):
    bg = Image.open(os.path.join(HERE, "graded/default-scene-r4-set-B-graded-v3c.png")).convert("RGB").resize((GW, GH), Image.LANCZOS)
    a = np.asarray(bg).astype(np.float32)
    x0, y0, x1, y1 = 640, 1000, 1500, 1820
    cols = {"vase-cj-textured-white-stoneware": (40, 200, 120), "vase-cj-charcoal-carved": (220, 60, 60), "vase-cj-white-plum-hand-thrown": (60, 120, 230)}
    p = table[(first or 1) - 1]
    for card, v in VASES.items():
        body, branch = solids(*p["xy"], v)
        m = S0.raster([body, branch])
        e = S0.boundary(cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool))
        a[cv2.dilate(e.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(bool)] = cols[card]
    for m, c in ((arm_clay, (240, 200, 30)), (arm_render, (230, 90, 170))):
        e = S0.boundary(m)
        a[e] = c
    for name, R in rend.items():
        for yw, (p0, p1) in R["rows_work"].items():
            yc = int(round(yw * sx))
            for x in (int(p0), int(p1)):
                if 0 <= x < GW:
                    a[yc:yc + 2, x] = (250, 130, 30)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).crop((x0, y0, x1, y1)).resize((1290, 1230), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    d.text((10, 10), "clay r5: vases at point %s %s (green D16, red W22, blue W22.4)" % ((first or "none"), p["xy"]), fill=(255, 255, 255),
           font=f, stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((10, 36), "armchair: clay (yellow), render (magenta); bronze strips (orange)", fill=(255, 255, 255), font=f, stroke_width=2,
           stroke_fill=(0, 0, 0))
    im.save(os.path.join(HERE, "step0/vase-point-r5-overlay.jpg"), quality=90)


if __name__ == "__main__":
    main()
