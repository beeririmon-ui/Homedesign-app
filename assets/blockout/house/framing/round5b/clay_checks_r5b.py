#!/usr/bin/env python3
"""
Clay checks of the round-5b clays (house plan 1.2.2, slots 1.6, Bible 1.8.3; render-agent, 2026-11-04; 0 var2 tokens), after the
designer resolved the four round-5 findings: briefs/render-m0-new-camera-2026-11-03.md tasks 1-2, resumed. The round-5 script
(framing/round5/clay_checks_r5.py) is unchanged; this one reads framing/round5b/selfcheck.json and writes
framing/round5b/clay-checks-2026-11-04.json: the camera agreement, every in-frame slot box (slots 1.6 vs the plan's projection vs the
clay), the designer's four points (pouf, armchair, rug, coffee table / sofa), the rug back edge against the pouf top (the designer's
check: a tangent -> pouf h 37), the F3 tangents of the clays, and whether anything still stops the paid renders.

  python3 -I clay_checks_r5b.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
plan = json.load(open(os.path.join(REPO, "docs", "house-plan.json")))
slots = json.load(open(os.path.join(REPO, "data", "slots", "living-room.json")))
sc = json.load(open(os.path.join(HERE, "selfcheck.json")))["frames"]
CAM = next(c for c in plan["cameras"] if c["id"] == "M0")
C, Hc, YAW, U0, V0 = CAM["loc"][:2], CAM["loc"][2], math.radians(CAM["yaw_deg_left"]), CAM["u0"], CAM["v0"]
CX, CY, CW, CH = 116, 65, 3840, 2160


def P(X, Y, Z, yaw=YAW):
    f, r = (-math.sin(yaw), -math.cos(yaw)), (math.cos(yaw), -math.sin(yaw))
    dx, dy = X - C[0], Y - C[1]
    d, x = f[0] * dx + f[1] * dy, r[0] * dx + r[1] * dy
    return U0 + 0.6667 * x / d, V0 + 1.1852 * (Hc - Z) / d, d


def box(pts):
    uv = [P(*p) for p in pts]
    return [round(min(a[0] for a in uv), 3), round(max(a[0] for a in uv), 3), round(min(a[1] for a in uv), 3), round(max(a[1] for a in uv), 3)]


def corners(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def cyl(cx, cy, r, z0, z1, n=144):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), z) for k in range(n) for z in (z0, z1)]


def rrect(cx, cy, w, dp, deg, z0, z1):
    a, out = math.radians(deg), []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = sx * w / 2, sy * dp / 2
            X, Y = cx + lx * math.cos(a) - ly * math.sin(a), cy + lx * math.sin(a) + ly * math.cos(a)
            out += [(X, Y, z0), (X, Y, z1)]
    return out


def to_frame(b, overscan):
    if not overscan:
        return [round(x, 3) for x in b]
    return [round((b[0] * 4072 - CX) / CW, 3), round((b[1] * 4072 - CX) / CW, 3), round((b[2] * 2290 - CY) / CH, 3), round((b[3] * 2290 - CY) / CH, 3)]


def clay_box(fid, key):
    f = sc.get(fid, {})
    b = f.get("boxes", {}).get(key)
    return None if b is None else to_frame(b["box"], bool(f.get("overscan", {}).get("on")))


def vis(fid, key):
    it = sc.get(fid, {}).get("items_visible", {}).get(key, {})
    return dict(visible_pct=it.get("visible_pct"), frame_pct=it.get("frame_area_pct"))


S = {s["id"]: s for s in slots["slots"]}
rows = []


def row(slot, label, proj, clay, part=None, note="", comparable=True):
    m = S[slot].get("m0_1_2", {})
    sb = (m.get("parts") or {}).get(part) if part else m.get("box")
    sbp = m.get("body") if slot == "vase" else sb
    cl = lambda b: None if b is None else [min(max(x, 0.0), 1.0) for x in b]  # noqa: E731
    d_proj = None if (sbp is None or proj is None or not comparable) else round(max(abs(a - b) for a, b in zip(cl(sbp), cl(proj))), 3)
    d_clay = None if (sb is None or clay is None or slot in ("cushions",)) else round(max(abs(a - b) for a, b in zip(cl(sb), cl(clay))), 3)
    worst = max([x for x in (d_proj, d_clay) if x is not None] or [0])
    rows.append(dict(slot=slot, item=label, slots_1_6=sb, projection_plan_constants=proj, clay_round5b=clay, max_diff_projection=d_proj, max_diff_clay=d_clay,
                     verdict=("not comparable (see note)" if (d_proj is None and d_clay is None) else "agrees (<= 0.02)" if worst <= 0.02
                              else "estimate off (0.02-0.05)" if worst <= 0.05 else "CONTRADICTION (> 0.05)"), note=note))


ARM = (-1.23, 2.73)
POUF = (1.45, 2.00)
RUG = (-1.45, 1.85, 0.72, 3.12)
row("sofa", "sofa 220 x 92 x 78 (X -0.90..1.30, Y 0.03-0.95)", box(corners(-0.90, 1.30, 0.03, 0.95, 0.0, 0.78)), clay_box("M0", "sofa 220x92x78 (fixed-product)"))
row("coffee-table", "coffee table 140 x 70 h 38, centre (0.20, 1.72)", box(corners(-0.50, 0.90, 1.37, 2.07, 0.0, 0.38)), clay_box("M0", "coffee table 140x70 h38 (fixed-product)"),
    note="house plan 1.2.2: the top's back edge at v 0.776; its 0.023 overlap with the sofa base accepted as a documented M0 F3 exception")
row("armchair", f"armchair 72 x 78 h 70, centre {ARM}, 25 deg (house plan 1.2.2)", box(rrect(*ARM, 0.72, 0.78, 25, 0.0, 0.70)), clay_box("M0", "armchair 72x78 h70 (fixed-product)"))
row("pendant", "pendant shade 40 x 28, bottom 1.90", box(cyl(0.20, 1.72, 0.20, 1.90, 2.18)), clay_box("M0", "living/pendant"))
row("accent-sconces", "travertine pair, left plate (-0.85, 0, 1.75)", box(corners(-0.92, -0.78, 0.0, 0.12, 1.66, 1.84)), None, part="left")
row("accent-sconces", "travertine pair, right plate (1.25, 0, 1.75)", box(corners(1.18, 1.32, 0.0, 0.12, 1.66, 1.84)), None, part="right",
    note="clay pair box (both cubes) " + str(clay_box("M0", "living/accent-sconces")))
row("vase", "vase body 32, d 22, on the back sash (-2.42, 1.35, 0.75)", box(cyl(-2.42, 1.35, 0.11, 0.75, 1.07)), clay_box("M0", "living/vase"),
    note="the clay box includes the stems (slots 'box'); body compared with the projection")
_rp, _r0 = clay_box("M0-pouf", "living/rug"), clay_box("M0", "living/rug")
_rug_clay = None if (_rp is None or _r0 is None) else [_rp[0], min(1.0, _r0[1]), _rp[2], _rp[3]]
row("rug", "rug 330 x 240, X -1.45..1.85, Y 0.72-3.12 (house plan 1.2.2)", box(corners(RUG[0], RUG[1], RUG[2], RUG[3], 0.0, 0.012)), _rug_clay,
    note=("clay = the 16:9 measurement clay M0-pouf for u0 / v0 / v1 (the M0 canvas box's u0 " + str(_r0[0] if _r0 else None) + " is the left edge in the 3 % "
          "overscan band below the frame) and the pouf-free M0 clay for u1 (in M0-pouf the pouf hides the rug's right end: u1 " + str(_rp[1] if _rp else None) +
          "); the near corners project outside the frame, so the projection box is not comparable"), comparable=False)
row("bowl", "bowl d 24 h 9, centre (0.68, 1.92)", box(cyl(0.68, 1.92, 0.12, 0.38, 0.47)), clay_box("M0", "living/bowl"))
row("candle-holders", "candle holders X 0.42-0.65, Y 1.55-1.75, to Z 0.63", box(corners(0.42, 0.65, 1.55, 1.75, 0.38, 0.63)), clay_box("M0", "living/candle-holders"))
row("table-runner", "runner on the table's left third", None, clay_box("M0", "living/table-runner"))
row("cushions", "cushion set + throw", None, clay_box("M0", "living/cushions"), note="not comparable (the clay boxes the cushion proxies only)")
row("pouf", f"pouf {POUF} d 45 h 36 (M0-pouf)", box(cyl(*POUF, 0.225, 0.0, 0.36)), clay_box("M0-pouf", "living/pouf"),
    note="slot EMPTY in the test (no approved product); measurement clay only", comparable=True)
row("floor-lamp", "floor lamp base (1.52, 0.20)", None, clay_box("M0-pouf", "living/floor-lamp"), note="slot empty in the test (TR3)")


def rim(cx, cy, r, h, n=720):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), h) for k in range(n)]


def line_v_at_u(p0, p1, u, n=4000):
    """v of the projected 3-D segment p0-p1 at image column u (None if the segment does not reach u)."""
    best = None
    for k in range(n + 1):
        t = k / n
        q = [p0[i] + (p1[i] - p0[i]) * t for i in range(3)]
        uu, vv, d = P(*q)
        if d <= 0:
            continue
        if best is None or abs(uu - u) < abs(best[0] - u):
            best = (uu, vv)
    return None if best is None or abs(best[0] - u) > 0.002 else round(best[1], 4)


# --- pouf: the designer's numbers, per diameter / height
pouf_env = {}
lamp_base_low = max(P(1.52 + 0.13 * math.cos(t), 0.20 + 0.13 * math.sin(t), 0.0)[1] for t in [2 * math.pi * k / 144 for k in range(144)])
rug_back = ((RUG[0], RUG[2], 0.012), (RUG[1], RUG[2], 0.012))
rug_right = ((RUG[1], RUG[2], 0.012), (RUG[1], RUG[3], 0.012))
for d_cm in (45, 48):
    for h_cm in (35, 36, 37):
        r, h = d_cm / 200.0, h_cm / 100.0
        b = box(cyl(*POUF, r, 0.0, h))
        rp = [P(*q) for q in rim(*POUF, r, h)]
        top = min(q[1] for q in rp)
        # the rug's back edge against the pouf's top arc: per image column u inside the pouf (in the frame), the top arc v_top(u) (the
        # highest rim point in that column) and the back edge's v; d(u) = v_edge - v_top: > 0 the edge runs below the top (behind the
        # pouf's body), < 0 above it (visible over the pouf); its minimum is how close the edge comes to the pouf's top line
        cols = {}
        for q in rp:
            k = round(q[0], 3)
            cols[k] = min(cols.get(k, 9.0), q[1])
        dd = []
        for u in sorted(cols):
            if 0.0 <= u <= 1.0:
                vb = line_v_at_u(*rug_back, u)
                if vb is not None:
                    dd.append((round(vb - cols[u], 4), u))
        g_min = min(dd) if dd else None
        cross = next((u for (g, u) in sorted(dd, key=lambda x: x[1]) if g >= 0), None)          # where the edge goes behind the top arc
        utop = min(rp, key=lambda q: q[1])
        below_top = None if line_v_at_u(*rug_back, utop[0]) is None else round(line_v_at_u(*rug_back, utop[0]) - utop[1], 4)
        pouf_env[f"d{d_cm} h{h_cm}"] = dict(box=b, left_contour_u=b[0], right_cut_pct=round(max(0.0, (b[1] - 1.0) / (b[1] - b[0])) * 100, 1), top_rim_v=round(top, 3),
                                            bottom_cut=bool(b[3] > 1.0), lamp_base_gap=round(top - lamp_base_low, 3),
                                            rug_back_edge_vs_pouf_top=dict(below_the_top_point_v=below_top, top_point_u=round(utop[0], 3),
                                                                               goes_behind_the_rim_at_u=cross, left_contour_u=b[0],
                                                                               reads=("the edge runs into the rim's upper-left quarter at an acute angle, "
                                                                                      f"{below_top} under the pouf's top point" if below_top is not None else None)))
pf, pfb = sc.get("M0-pouf", {}), sc.get("M0-pouf-b", {})
F3k = lambda f, w: [t for t in f.get("F3_tangents", {}).get("object_object_tangents", []) if w in t["a"] or w in t["b"]] + \
    [t for t in f.get("F3_tangents", {}).get("edge_tangents", []) if w in t["item"]]  # noqa: E731
pouf = dict(
    decision="house plan 1.2.2 / slots 1.6 / Bible 1.8.3 (2026-11-04): centre (1.45, 2.00), d 45-48, h 35-37, cut at the right and bottom edges; EMPTY in the test",
    designer_expects=dict(left_contour_u=[0.905, 0.911], top_rim_v=[0.915, 0.928], right_cut_pct=50, lamp_base_gap=[0.022, 0.034], frame_pct=0.5,
                          rug_back_edge="passes behind the pouf top at an acute angle, 0.01-0.02 below it; if it reads as a tangent: h 37"),
    projection_envelope=pouf_env,
    clay_M0_pouf=dict(proxy="(1.45, 2.00) d 45 h 36", box=clay_box("M0-pouf", "living/pouf"), **vis("M0-pouf", "living/pouf"),
                      lamp_box=clay_box("M0-pouf", "living/floor-lamp"), f3=F3k(pf, "pouf")),
    clay_M0_pouf_b=dict(proxy="(1.45, 2.00) d 48 h 37", box=clay_box("M0-pouf-b", "living/pouf-b"), **vis("M0-pouf-b", "living/pouf-b"), f3=F3k(pfb, "pouf")))
cp = pouf["clay_M0_pouf"]
if cp["box"] and cp["lamp_box"]:
    cp["lamp_base_gap"] = round(cp["box"][2] - cp["lamp_box"][3], 3)

# --- armchair: the left edge (the designer: the arm end and the back post ~0.02-0.025 inside the left edge)
arm_proj = box(rrect(*ARM, 0.72, 0.78, 25, 0.0, 0.70))
armchair = dict(decision="house plan 1.2.2: (-1.27, 2.82) -> (-1.23, 2.73), 25 deg", designer_expects=dict(left_margin=[0.02, 0.025], right_u=[0.31, 0.32], back_below_sill=0.038),
                projection_footprint_box=arm_proj, clay_box=clay_box("M0", "armchair 72x78 h70 (fixed-product)"), **vis("M0", "armchair 72x78 h70 (fixed-product)"),
                clay_left_margin=(None if clay_box("M0", "armchair 72x78 h70 (fixed-product)") is None else clay_box("M0", "armchair 72x78 h70 (fixed-product)")[0]),
                f3=F3k(sc.get("M0", {}), "armchair"))

# --- rug: the designer's numbers (330 x 240)
xs = [RUG[0] + (RUG[1] - RUG[0]) * k / 2000 for k in range(2001)]
back = [P(x, RUG[2], 0.012) for x in xs]
cross_right = next(((round(x, 3), round(v, 3)) for x, (u, v, d) in zip(xs, back) if u >= 1.0), None)
lefts = [P(RUG[0], RUG[2] + (RUG[3] - RUG[2]) * k / 2000, 0.012) for k in range(2001)]
left_exit = next(((round(u, 3), round(v, 3)) for (u, v, d) in lefts if v >= 1.0), None)
rug = dict(decision="house plan 1.2.2: 330 x 240, X -1.45..1.85, Y 0.72-3.12", designer_expects=dict(back_edge_crosses_right_edge_at=dict(X=1.77, v=0.95), left_edge_exits_bottom_u=0.19, visible="about half"),
           projection=dict(back_edge_crosses_right_edge=dict(X=cross_right[0], v=cross_right[1]) if cross_right else None, left_edge_exits_bottom=dict(u=left_exit[0]) if left_exit else None),
           clay_box_M0_pouf=clay_box("M0-pouf", "living/rug"), clay_box_M0=clay_box("M0", "living/rug"), **vis("M0", "living/rug"), f3=F3k(sc.get("M0", {}), "rug"))

# --- coffee table / sofa (accepted exception)
table = dict(decision="house plan 1.2.2: the 0.023 overlap of the table top with the sofa base accepted as a documented M0 F3 exception; the top's back edge at v 0.776",
             clay_box=clay_box("M0", "coffee table 140x70 h38 (fixed-product)"), f3=[t for t in sc.get("M0", {}).get("F3_tangents", {}).get("object_object_tangents", [])
                                                                                        if "coffee" in t["a"] or "coffee" in t["b"]])

stops = [r for r in rows if r["verdict"].startswith("CONTRADICTION")]
out = dict(date="2026-11-04", tokens=0, script="assets/blockout/house/framing/round5b/clay_checks_r5b.py",
           inputs=dict(plan=plan.get("version"), slots=slots.get("version"), selfcheck="assets/blockout/house/framing/round5b/selfcheck.json"),
           camera=dict(M0=CAM["loc"], yaw=CAM["yaw_deg_left"], u0=U0, v0=V0, clay=sc.get("M0", {}).get("camera")),
           slot_boxes=rows, pouf=pouf, armchair=armchair, rug=rug, coffee_table=table,
           f3=dict(M0=sc.get("M0", {}).get("F3_tangents"), M0p=sc.get("M0p", {}).get("F3_tangents"), M0x=sc.get("M0x", {}).get("F3_tangents")),
           contradictions=[f"{r['slot']}: {r['item']} (projection {r['max_diff_projection']}, clay {r['max_diff_clay']})" for r in stops])
json.dump(out, open(os.path.join(HERE, "clay-checks-2026-11-04.json"), "w"), indent=1, ensure_ascii=False)
for r in rows:
    print(f"{r['slot']:15s} slots {r['slots_1_6']} proj {r['projection_plan_constants']} clay {r['clay_round5b']} -> {r['verdict']}")
print("pouf envelope:", json.dumps(pouf_env))
print("pouf clay:", json.dumps(pouf["clay_M0_pouf"])[:600])
print("pouf-b clay:", json.dumps(pouf["clay_M0_pouf_b"])[:600])
print("armchair:", json.dumps(armchair)[:700])
print("rug:", json.dumps(rug)[:700])
print("table:", json.dumps(table)[:500])
print("contradictions:", out["contradictions"])
