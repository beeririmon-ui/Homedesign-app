#!/usr/bin/env python3
"""
Task 1 + task 2 checks of briefs/render-m0-new-camera-2026-11-03.md on the round-5 clays (render-agent, 2026-11-03; 0 var2 tokens).
Reads docs/house-plan.json 1.2.1, data/slots/living-room.json 1.5 and framing/round5/selfcheck.json; writes
framing/round5/clay-checks-2026-11-03.json: the camera agreement, every in-frame slot box (slots 1.5 vs the plan's projection with
the plan constants vs the clay), the pendant and the pouf positions and their Bible rules, the F3 findings of the 1.2 clay, the test
density (V7Q5 b), the Bible 1.8 wall readings, and the contradictions that stop the paid renders.

  python3 -I clay_checks_r5.py
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
CX, CY, CW, CH = 116, 65, 3840, 2160                                   # overscan canvas -> 16:9 frame (plan.json overscan)


def P(X, Y, Z, yaw=YAW):
    f, r = (-math.sin(yaw), -math.cos(yaw)), (math.cos(yaw), -math.sin(yaw))
    dx, dy = X - C[0], Y - C[1]
    d, x = f[0] * dx + f[1] * dy, r[0] * dx + r[1] * dy
    return U0 + 0.6667 * x / d, V0 + 1.1852 * (Hc - Z) / d, d


def box(pts, yaw=YAW):
    uv = [P(*p, yaw=yaw) for p in pts]
    return [round(min(a[0] for a in uv), 3), round(max(a[0] for a in uv), 3), round(min(a[1] for a in uv), 3), round(max(a[1] for a in uv), 3)]


def corners(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def cyl(cx, cy, r, z0, z1, n=72):
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
    f = sc[fid]
    b = f["boxes"].get(key)
    return None if b is None else to_frame(b["box"], bool(f.get("overscan", {}).get("on")))


S = {s["id"]: s for s in slots["slots"]}
rows = []
NOT_COMPARABLE = ("rug",)        # the rug's near corners project below the frame: only the clay's visible box is comparable


def row(slot, label, proj, clay, part=None, note=""):
    m = S[slot]["m0_1_2"]
    sb = (m.get("parts") or {}).get(part) if part else m.get("box")
    if slot == "vase":                      # projection = the body (vs slots 'body'); clay = body + stems (vs slots 'box')
        sbp = m.get("body")
    else:
        sbp = sb
    clamp = lambda b: None if b is None else [min(max(x, 0.0), 1.0) for x in b]  # noqa: E731
    d_proj = None if (sbp is None or proj is None or slot in NOT_COMPARABLE) else round(max(abs(a - b) for a, b in zip(clamp(sbp), clamp(proj))), 3)
    d_clay = None if (sb is None or clay is None or slot in ("cushions",)) else round(max(abs(a - b) for a, b in zip(clamp(sb), clamp(clay))), 3)
    worst = max([x for x in (d_proj, d_clay) if x is not None] or [0])
    rows.append(dict(slot=slot, item=label, slots_1_5=sb, projection_plan_constants=proj, clay_round5=clay, max_diff_projection=d_proj, max_diff_clay=d_clay,
                     verdict=("not comparable (see note)" if (d_proj is None and d_clay is None) else "agrees (<= 0.02)" if worst <= 0.02 else "estimate off (0.02-0.05)" if worst <= 0.05 else "CONTRADICTION (> 0.05)"), note=note))


row("sofa", "sofa 220 x 92 x 78 (X -0.90..1.30, Y 0.03-0.95)", box(corners(-0.90, 1.30, 0.03, 0.95, 0.0, 0.78)), clay_box("M0", "sofa 220x92x78 (fixed-product)"),
    note="42% of the frame width in the clay (0.47-0.89)")
row("coffee-table", "coffee table 140 x 70 h 38, centre (0.20, 1.72)", box(corners(-0.50, 0.90, 1.37, 2.07, 0.0, 0.38)), clay_box("M0", "coffee table 140x70 h38 (fixed-product)"),
    note="the top's far edge is at v 0.78 (plan text 'top v 0.84-0.92' and the slots box v0 0.836 are 0.05-0.06 low); the clay's superellipse corners make u0 0.458")
row("armchair", "armchair 72 x 78 h 70, centre (-1.27, 2.82), 25 deg", box(rrect(-1.27, 2.82, 0.72, 0.78, 25, 0.0, 0.70)), clay_box("M0", "armchair 72x78 h70 (fixed-product)"),
    note="the v4 armchair (arms and back posts) reaches past the left edge of the 16:9 frame: its front arm end ~0.010 from the left edge and the back-left post sliced lengthwise by the edge (clay image); the plan / slots estimate 0.05")
row("pendant", "pendant shade envelope 40-50 x 22-32, bottom 1.90", [min(a, b) if i % 2 == 0 else max(a, b) for i, (a, b) in enumerate(zip(box(cyl(0.20, 1.72, 0.20, 1.90, 2.12)), box(cyl(0.20, 1.72, 0.25, 1.90, 2.22))))],
    clay_box("M0", "living/pendant"), note="clay = the 40 x 28 pumpkin proxy (ellipsoid: its rounded bottom reads 0.218, a flat drum bottom 0.233-0.238)")
row("accent-sconces", "travertine pair, left plate (-0.85, 0, 1.75), 14 x 18 x 12", box(corners(-0.92, -0.78, 0.0, 0.12, 1.66, 1.84)), None, part="left")
row("accent-sconces", "travertine pair, right plate (1.25, 0, 1.75), 14 x 18 x 12", box(corners(1.18, 1.32, 0.0, 0.12, 1.66, 1.84)), None, part="right",
    note="clay pair box (both cubes) " + str(clay_box("M0", "living/accent-sconces")))
row("vase", "vase body 32, d 22, on the back sash (-2.42, 1.35, 0.75)", box(cyl(-2.42, 1.35, 0.11, 0.75, 1.07)), clay_box("M0", "living/vase"),
    note="the clay box includes the stems to Z 1.35 (v0 0.458), as the slots 'box'; body compared")
row("rug", "rug, Bible plan-B test envelope X -1.25..1.65, Y 0.72-3.12 (290 x 240)", box(corners(-1.25, 1.65, 0.72, 3.12, 0.0, 0.012)), clay_box("M0-pouf", "living/rug"),
    note="slots u1 0.969 is the back-right corner; the right edge X 1.65 runs on and leaves the frame through the bottom edge at u 0.993 (projection) / 0.995 (clay): 0.005-0.007 from the bottom-right corner")
row("framed-art", "triptych 3 x 50 x 70, 6 cm gaps, centre (0.20, 0, 1.475)", box(corners(-0.61, 1.01, 0.0, 0.03, 1.125, 1.825)), None,
    note="slot EMPTY in the test (RND2: card incomplete, rights unclear); the slots box is the v4.1 art envelope (Z ~1.00-1.95); art centre u 0.677 (right third, F1)")
row("wall-decor", "wall decor up to 45 x 45, centre (-1.20, 0.02, 1.20)", box(corners(-1.425, -0.975, 0.0, 0.03, 0.975, 1.425)), None, note="slot empty in the test")
row("planter", "planter pot d 38 h 34, centre (-2.00, 0.47)", box(cyl(-2.00, 0.47, 0.19, 0.0, 0.34)), None, part="pot", note="slot empty in the test; corner ray: corner u 0.364, pot 0.362")
row("bowl", "bowl d 24 h 9, centre (0.68, 1.92) on the table", box(cyl(0.68, 1.92, 0.12, 0.38, 0.47)), clay_box("M0", "living/bowl"))
row("candle-holders", "candle holders X 0.42-0.65, Y 1.55-1.75, candles to Z 0.63", box(corners(0.42, 0.65, 1.55, 1.75, 0.38, 0.63)), clay_box("M0", "living/candle-holders"))
row("table-runner", "runner on the table's left third", None, clay_box("M0", "living/table-runner"))
row("cushions", "cushion set + throw on the sofa", None, clay_box("M0", "living/cushions"), note="not comparable: the clay boxes the v4 cushion proxies only; the slots box (0.484-0.901, 0.566-0.898) is the set with the throw's drop")
row("pouf", "pouf (1.18, 2.08) d 45 h 36 (measurement clay M0-pouf)", box(cyl(1.18, 2.08, 0.225, 0.0, 0.36)), clay_box("M0-pouf", "living/pouf"),
    note="the box agrees within 0.014, but the right margin is 0.013 (documents: 0.027), see 'pouf'; slot EMPTY in the test (no approved product: R6Q2 stock unavailable; the 7.5 candidate is a cover of unknown filled height, Bible pouf rule)")
row("floor-lamp", "floor lamp base (1.52, 0.20), shade 35-38", None, clay_box("M0-pouf", "living/floor-lamp"), note="slot empty in the test (TR3); clay = the v4 proxy moved to (1.52, 0.20)")

# pouf envelope (V7Q8 b)
pouf_env = {}
for d_cm in (45, 48):
    for h_cm in (35, 36, 37):
        r, h = d_cm / 200.0, h_cm / 100.0
        b = box(cyl(1.18, 2.08, r, 0.0, h))
        top = min(P(1.18 + r * math.cos(t), 2.08 + r * math.sin(t), h)[1] for t in [2 * math.pi * k / 144 for k in range(144)])
        base_low = max(P(1.52 + 0.13 * math.cos(t), 0.20 + 0.13 * math.sin(t), 0.0)[1] for t in [2 * math.pi * k / 144 for k in range(144)])
        hem = P(1.30, 0.95, 0.15)[1]
        pouf_env[f"d{d_cm} h{h_cm}"] = dict(box=b, right_margin=round(1 - b[1], 3), top_rim_v=round(top, 3), lamp_base_gap=round(top - base_low, 3),
                                            sofa_cover_hem_gap=round(top - hem, 3))
pf, pfb = sc["M0-pouf"], sc["M0-pouf-b"]
pouf = dict(
    decision="V7Q8 (b), 2026-11-03: next to the coffee table, decisively cut; house plan 1.2.1 cameras.M0.frame_est_1_2.pouf; slots 1.5; Bible 1.8.2",
    position_m=[1.18, 2.08], envelope_cm=dict(d=[45, 48], h=[35, 37]),
    documents_say=dict(box=[0.825, 0.973, 0.913, 1.0], right_margin=0.027, visible_pct=27, frame_pct=1.0, lamp_base_gap=0.032, sofa_cover_hem_gap=[0.017, 0.03]),
    clay_M0_pouf=dict(proxy="(1.18, 2.08) d 45 h 36", box=clay_box("M0-pouf", "living/pouf"), right_margin=round(1 - clay_box("M0-pouf", "living/pouf")[1], 3),
                      visible_pct=pf["items_visible"]["living/pouf"]["visible_pct"], frame_pct=pf["items_visible"]["living/pouf"]["frame_area_pct"],
                      lamp_base_gap=round(clay_box("M0-pouf", "living/pouf")[2] - clay_box("M0-pouf", "living/floor-lamp")[3], 3),
                      f3=[t for t in pf["F3_tangents"]["object_object_tangents"] if "pouf" in t["a"] or "pouf" in t["b"]] + [t for t in pf["F3_tangents"]["edge_tangents"] if "pouf" in t["item"]]),
    clay_M0_pouf_b=dict(proxy="designer's pre-authorised fix: (1.18, 2.11) d 45 h 35", box=clay_box("M0-pouf-b", "living/pouf-b"),
                        right_margin=round(1 - clay_box("M0-pouf-b", "living/pouf-b")[1], 3), visible_pct=pfb["items_visible"]["living/pouf-b"]["visible_pct"],
                        frame_pct=pfb["items_visible"]["living/pouf-b"]["frame_area_pct"],
                        f3=[t for t in pfb["F3_tangents"]["object_object_tangents"] if "pouf" in t["a"]] + [t for t in pfb["F3_tangents"]["edge_tangents"] if "pouf" in t["item"]]),
    projection_envelope=pouf_env,
    finding=("The right margin is 0.007-0.013 for every diameter in the 45-48 envelope (the documents' 0.027 takes the half-width symmetric around the centre "
             "u 0.899; at 38 deg off-axis the right side widens), so the Bible's reason for d <= 48 ('the right edge is not a tangent') does not hold; "
             "the floor-lamp base clears the pouf by 0.013 (d48 h37) to 0.025 (d45 h35), under the Bible's 0.02 'no exception' at the large end; "
             "the pouf's top rim covers the foot of the sofa's front-right oak leg (a sliver overlap, F3), which the pre-authorised fix (Y +0.03, h 35) "
             "does not remove (margin 0.011). Visible ~25% and ~1.1% of the frame agree with the documents (27%, 1%). "
             "Moving the pouf left by 0.02-0.04 m (d 45-48) gives 0.02 at the right edge but brings it to 0.00-0.02 m from the coffee table."),
    in_test="empty (no approved product); the slot is a sourcing task under V7Q5 (b)")

pt = sc["M0"]
pendant = dict(
    decision="V7Q7 (b), 2026-11-03: shade bottom 1.90 (was 2.20), hang point (0.20, 1.72, 3.00); Bible 1.8.1 pendant",
    position_m=[0.20, 1.72], shade_bottom_m=1.90, proxy="40 x 28 ribbed pumpkin (m0-v7 c), ellipsoid, bottom 1.90, top 2.18; cord to the hang point as its own group",
    clay_M0=dict(box=clay_box("M0", "living/pendant"), centre_u=round(sum(clay_box("M0", "living/pendant")[:2]) / 2, 3), cord_box=clay_box("M0", "living/pendant-cord"),
                 visible_pct=pt["items_visible"]["living/pendant"]["visible_pct"], frame_pct=pt["items_visible"]["living/pendant"]["frame_area_pct"]),
    clay_M0p=dict(box=clay_box("M0p", "living/pendant")),
    projection_envelope=dict(top_v=[0.046, 0.098], bottom_v=[0.233, 0.238], u=[0.564, 0.682], centre_u=0.622),
    bible_rules=dict(rule1_whole_shade_3pct_below_top=dict(ok=True, top_v_clay=clay_box("M0", "living/pendant")[2], top_v_envelope_min=0.046),
                     rule2_gap_to_art_top_5pct=dict(ok=True, art_top_v_triptych=box(corners(-0.61, 1.01, 0.0, 0.03, 1.125, 1.825))[2], shade_bottom_v=0.238,
                                                    gap=round(box(corners(-0.61, 1.01, 0.0, 0.03, 1.125, 1.825))[2] - 0.238, 3), note="art empty in the test; gap for the 3 x 50 x 70 triptych"),
                     rule3_upper_third=dict(ok=True, bottom_v_max=0.238)),
    cord="exits the top edge (hang point v < 0)", hotspot=[0.622, 0.20], hotspot_inside=True)

f3 = dict(
    M0=dict(edge=pt["F3_tangents"]["edge_tangents"], object_object=pt["F3_tangents"]["object_object_tangents"],
            read=["armchair: front arm end ~0.010 from the left edge of the 16:9 frame, the back-left post sliced lengthwise by the edge (the canvas reports 0.016 "
                  "from the canvas edge); the armchair is cut 18% overall (bottom edge, the planned foreground), so F3's 'cut >= 15 %' exemption applies "
                  "formally, but the left edge itself is a sliver crop",
                  "coffee table / sofa: the table top's far edge slivers over the sofa base (overlap 0.023 thick, 12.8% of the sofa): an F3 object-object "
                  "flag that the 1.1 clay did not have",
                  "rug (Bible test envelope 290 x 240): the right edge leaves the frame through the bottom edge 0.005 from the bottom-right corner (M0-pouf "
                  "16:9 clay); the rug is cut 85%, so the exemption applies formally; a rug of 310-340 (the Bible's 290-340, or the 230 x 330 stand-in of "
                  "m0-v7) leaves through the right edge decisively"]),
    M0p=dict(edge=sc["M0p"]["F3_tangents"]["edge_tangents"], object_object=sc["M0p"]["F3_tangents"]["object_object_tangents"],
             read=["the coffee-table bottom tangent is on the canvas edge (the 16:9 frame cuts the table decisively); the sofa / table sliver as in M0"]),
    M0x=dict(edge=sc["M0x"]["F3_tangents"]["edge_tangents"], object_object=sc["M0x"]["F3_tangents"]["object_object_tangents"],
             read=["dining opening's far jamb at u ~0.625 (plan 0.59), dining table u 0.625-0.79 on the right third, the near jamb outside: as the plan describes; "
                   "the dining-side flags are the round-4 D1 proxies seen through the opening"]))

walls = {fid: {k: v.get("L_final") for k, v in sc[fid]["wall_patches"].items() if k.startswith("bible18") or k.startswith("back_wall") or k.startswith("hero")}
         for fid in ("M0", "M0p", "M0x")}
out = dict(
    date="2026-11-03", brief="briefs/render-m0-new-camera-2026-11-03.md tasks 1-2", script="assets/blockout/house/framing/round5/clay_checks_r5.py",
    json_tool=dict(house_plan="python3 -m json.tool: OK", slots="python3 -m json.tool: OK"),
    camera=dict(plan=CAM["loc"] + [CAM["yaw_deg_left"], CAM["lens"], U0, V0], slots=slots["m0_1_2_camera"]["loc"] + [slots["m0_1_2_camera"]["yaw_deg_left"], slots["m0_1_2_camera"]["lens"],
                slots["m0_1_2_camera"]["u0"], slots["m0_1_2_camera"]["v0"]], bible="(0.83, 4.64, 1.20), yaw 25, 24 mm, u0 0.47, v0 0.50", agree=True,
                poses=dict(M0p="same point, yaw 0", M0x="same point, yaw -35")),
    slot_boxes=rows, pendant=pendant, pouf=pouf, f3_on_the_1_2_clay=f3,
    density_test_V7Q5b=dict(filled=["accent-sconces", "pendant", "curtains", "vase", "rug", "cushions (with the throw)", "table-runner", "candle-holders", "bowl",
                                    "sofa", "coffee-table", "armchair"],
                            empty_sourcing_tasks=["framed-art (RND2: card incomplete: no shipping quote, no retail price, rights unclear)", "pouf (no approved product)",
                                                  "wall-decor", "planter"],
                            empty_by_decision=["floor-lamp (TR3)"], transition_only_empty=["wall-sconce", "basket", "magazine-holder"]),
    walls_clay_L=walls, walls_note="clay toned with the round-4 M0 post (exposure 1.438): back wall by the corner L 86.8 (Bible 90-94), window wall 83.3 (80-88)",
    contradictions=[
        "POUF: house plan 1.2.1 / Bible 1.8.2 / slots 1.5 give u 0.825-0.973 and 0.027 from the right edge; the plan's own projection gives 0.007-0.013 for d 45-48 "
        "(clay d 45: 0.013); lamp-base clearance 0.032 claimed, 0.013-0.025 projected (Bible: < 0.02 rejected, no exception); the top rim covers the foot of the "
        "sofa's front-right leg (sliver overlap) with and without the pre-authorised fix",
        "ARMCHAIR: plan / slots u 0.05-0.29; clay -0.013-0.29: the arm end ~0.010 from the left edge, the back post sliced by the edge",
        "RUG: slots u1 0.969 (the corner); the right edge reaches the bottom edge at 0.993-0.995, 0.005-0.007 from the frame corner",
        "COFFEE TABLE: plan / slots top v 0.84; projection and clay 0.78; with it a new sofa / table sliver overlap (0.023) on the 1.2 clay"],
    decision=("STOP before the paid renders (brief task 1; house plan frame_checks: F1-F12 on the clay before credits). 0 var2 tokens spent. The pouf is empty "
              "in the test, but the armchair, rug and table findings change the paid M0 if the designer nudges them (<= 0.10 m is within the designer's "
              "authority, house plan frame_fixes policy), and M0p / M0x take their cut-outs from M0."),
    for_the_designer=["pouf: accept the 0.013 margin as the planned foreground, or d 45 + X -0.02 (0.02 from the table), or another point; the lamp-base rule at d 48 h 37",
                      "armchair: accept the left-edge crop as part of the cut foreground, or X +0.06..0.08 / a few degrees more yaw so the arm end clears 0.02",
                      "rug: keep 290 (corner tangent), or 310-340 wide so the right edge leaves through the right edge decisively",
                      "coffee table vs sofa base: accept the overlap, or Y +0.05..0.08 so the far edge clears the sofa base"],
)
json.dump(out, open(os.path.join(HERE, "clay-checks-2026-11-03.json"), "w"), indent=1, ensure_ascii=False)
for r in rows:
    print(f"{r['slot']:15s} slots {r['slots_1_5']} proj {r['projection_plan_constants']} clay {r['clay_round5']} -> {r['verdict']}")
print("pouf envelope:", {k: (v["right_margin"], v["lamp_base_gap"], v["sofa_cover_hem_gap"]) for k, v in pouf_env.items()})
print("pouf clay:", pouf["clay_M0_pouf"]["box"], pouf["clay_M0_pouf"]["right_margin"], pouf["clay_M0_pouf"]["lamp_base_gap"], "| fix-b", pouf["clay_M0_pouf_b"]["box"], pouf["clay_M0_pouf_b"]["right_margin"])
print("pendant clay:", pendant["clay_M0"], "rule2 gap", pendant["bible_rules"]["rule2_gap_to_art_top_5pct"]["gap"])
print("walls:", walls)
