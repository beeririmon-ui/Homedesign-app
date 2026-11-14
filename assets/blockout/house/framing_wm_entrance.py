#!/usr/bin/env python3
"""
framing_wm_entrance.py: the warm-modern ENTRANCE as a clay (structure only) and the T-E0 stations, render-agent, 2026-11-14.
Brief: briefs/wm-entrance-clay-2026-11-14.md. 0 var2 tokens.

The scene is the warm-modern r4 clay exactly as framing_wm_r4_layers.py --layer furn renders it (the living room of base.png: shell +
sofa, coffee table, armchair; every product proxy hidden, every lamp off), plus the entrance hall rebuilt from the Nordic 1.1 hall to
master-designer's docs/proposals/wm-entrance-hall-architecture-2026-11-13.md, sections 1.1 and 2 (wm_hall_fixes()):
  - out: the oak portal and its casing (G-H4), the cornice, the console, the bench, the threshold strip, every hall proxy and lamp;
  - O-entry-living: clear opening 1.20 x 2.40 unchanged; the reveal lined in walnut #6B4A33 through the wall depth (jambs and soffit),
    flush with the reveal plane, a 3 mm shadow gap between the wood and the plaster on both faces; no casing, no leaf;
  - ceiling 3.00 with a 1 cm shadow gap; skirting 15 in the wall material, 1.5 proud (as WMC10); floor planks 22 along Y on the living
    room's joint lines, running through the opening with no threshold.
Cameras: read from docs/house-plan.json (cameras H0, H0x, M0; transitions T-E0). Frames:
  H0      yaw 12, shift 0.52 / 0.46
  H0x-a   yaw 25, shift 0.52 / 0.46
  H0x-b   yaw 25, shift 0.47 / 0.50 (M0's shift)
  a/S00..S11, b/S00..S11: 12 stations at even distance on the T-E0 dolly, heading 25 constant; a: the shift goes linearly from
  0.52 / 0.46 to 0.47 / 0.50 with the distance; b: 0.47 / 0.50 throughout. S00 = H0x-a / H0x-b, S11 = M0 (rendered once).
Canvas: the canvas of base.png, 2720 x 1530 with the 16:9 camera frame at [77.49, 43.43, 2642.51, 1486.57] (the 4072 x 2290 overscan
canvas of the M0 clay scaled to 2720 x 1530; the 0.02 % difference between the two scales is kept, as a pixel aspect).
Per frame: <id>.png (lit clay), <id>-depth.png (16-bit, planar depth, metres = value / 5000, 65535 = sky), <id>-id.png (surface ids,
palette PNG; legend in selfcheck.json), <id>-edges.png (structure edges, 1 px); the float passes as npz in the scratchpad.

  python3 framing_wm_entrance.py --frames all                       # 24 renders (about 5 min each at 16 samples)
  python3 framing_wm_entrance.py --frames H0,H0x-a,H0x-b
  python3 framing_wm_entrance.py --frames H0,b/S05 --res 680 --samples 6 --out /tmp/x      # smoke test
Then: python3 framing/wm-entrance-2026-11-14/checks_wm_entrance.py   (the tables, the seam, the contact sheet, selfcheck.json)
"""
import argparse
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
sys.argv = [sys.argv[0], "--layer", "furn"]          # framing_wm_r4_layers reads its layer from sys.argv at import

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import framing_wm_r4_layers as LY  # noqa: E402  (the furn layer: hides every product proxy, the Bible furniture, lamps off)

W4 = LY.W
r4, r3, fr, r2, bh = W4.r4, W4.r3, W4.fr, W4.r2, W4.bh
ba, bs, M = W4.ba, W4.bs, W4.M

OUT = os.path.join(HERE, "framing", "wm-entrance-2026-11-14")
SCRATCH = os.path.join(W4.SCRATCH, "wm-entrance")
PLAN_JSON = os.path.join(bh.REPO, "docs", "house-plan.json")

# the canvas of base.png (assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png)
CANVAS = (2720, 1530)
M0_CANVAS, M0_CROP = (4072, 2290), (116, 65, 3956, 2225)          # framing_r4 overscan canvas and its 16:9 frame
FRAME_BOX = (M0_CROP[0] * CANVAS[0] / M0_CANVAS[0], M0_CROP[1] * CANVAS[1] / M0_CANVAS[1],
             M0_CROP[2] * CANVAS[0] / M0_CANVAS[0], M0_CROP[3] * CANVAS[1] / M0_CANVAS[1])
K_U, K_V = 24.0 / 36.0, 24.0 / 36.0 * 16.0 / 9.0                  # house plan 'projection': 0.6667, 1.1852
DEPTH_UNITS_PER_M = 5000.0                                         # depth PNG: 0.2 mm per unit, 65535 = sky or beyond 13.1 m

# the opening and its lining (designer 1.1; BEAD and LINING_T are the clay's reading, see the README)
OPEN = dict(x0=0.95, x1=2.15, y0=6.20, y1=6.35, h=2.40)
LIN = dict(hex="#6B4A33", t=0.020, gap=0.003, bead=0.003, gap_depth=0.008)
HALL = dict(x=(0.80, 3.60), y=(6.35, 9.80), h=3.00, ceiling_gap=0.01)
PIDX = dict(lining=700, lining_gap=701, hall_cgap=702)             # outside the furn layer's hidden ranges (30-60, 440-599)

# surface ids of the id pass
IDS = {0: "sky / outside (through the glazing)",
       10: "hall floor", 11: "hall left wall (X 0.80)", 12: "hall front wall (Y 6.35)", 13: "hall right wall (X 3.60)",
       14: "hall skirting", 15: "hall ceiling, roof-light well", 17: "hall back wall",
       20: "lining, walnut: left jamb (X 0.95)", 21: "lining, walnut: right jamb (X 2.15)", 22: "lining, walnut: soffit (Z 2.40)",
       23: "lining shadow gap (3 mm)", 24: "plaster bead on the reveal (3 mm)", 25: "floor inside the wall depth (Y 6.20-6.35)",
       30: "living floor", 31: "living back wall (Y 0)", 32: "living window wall (X -2.30)", 33: "living right wall (X 2.50)",
       34: "living front wall (Y 6.20)", 35: "living ceiling", 36: "living dropped band + track slot", 37: "living rounded corner",
       38: "living skirting", 39: "living window (frame, mullions, reveal)", 40: "living window bench",
       41: "sofa", 42: "coffee table", 43: "armchair",
       50: "dining room seen through O-living-dining (plan 1.1 clay as it stands: no warm-modern design exists)",
       98: "geometry without a pass index", 99: "anything else (must be 0 px)"}
ALLOWED = set(IDS) - {50, 98, 99}                     # 50 is reported apart (outside_scope_px): no document shows it
PALETTE = {0: (255, 255, 255), 10: (150, 120, 95), 11: (236, 229, 218), 12: (222, 212, 198), 13: (205, 196, 184), 14: (190, 180, 165),
           15: (245, 240, 230), 17: (170, 165, 160), 20: (107, 74, 51), 21: (130, 92, 62), 22: (88, 60, 40), 23: (20, 20, 20),
           24: (250, 120, 60), 25: (120, 95, 75), 30: (139, 111, 85), 31: (228, 222, 214), 32: (208, 204, 198), 33: (196, 190, 182),
           34: (180, 176, 170), 35: (240, 238, 232), 36: (224, 220, 212), 37: (216, 208, 198), 38: (176, 170, 160),
           39: (58, 50, 44), 40: (216, 200, 174), 41: (120, 160, 200), 42: (200, 140, 90), 43: (110, 190, 140), 50: (150, 90, 200),
           98: (255, 0, 255), 99: (255, 0, 0)}


# ---------------------------------------------------------------------------------------------------------------
# cameras from the plan
# ---------------------------------------------------------------------------------------------------------------
def plan_frames():
    plan = json.load(open(PLAN_JSON))
    C = {c["id"]: c for c in plan["cameras"]}
    T = next(t for t in plan["transitions"] if t["id"] == "T-E0")
    pan, dolly = T["segments"]
    h0, h0x, m0 = C["H0"], C["H0x"], C["M0"]
    assert h0["loc"] == h0x["loc"] and pan["yaw"] == [h0["yaw_deg_left"], h0x["yaw_deg_left"]], "T-E0 pan does not match H0 / H0x"
    assert dolly["from"] == h0["loc"][:2] and dolly["to"] == m0["loc"][:2] and dolly["yaw"] == h0x["yaw_deg_left"] == m0["yaw_deg_left"]
    assert h0["lens"] == m0["lens"] == 24 and h0["loc"][2] == m0["loc"][2] == 1.20
    p0, p1 = h0["loc"], m0["loc"]
    sa, sb = (h0["u0"], h0["v0"]), (m0["u0"], m0["v0"])
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    F = {"H0": dict(loc=p0, yaw=h0["yaw_deg_left"], u0=sa[0], v0=sa[1], s=None, src="house-plan.json cameras.H0"),
         "H0x-a": dict(loc=p0, yaw=h0x["yaw_deg_left"], u0=sa[0], v0=sa[1], s=0.0, src="cameras.H0x, shift of H0 (brief: the plan's value)"),
         "H0x-b": dict(loc=p0, yaw=h0x["yaw_deg_left"], u0=sb[0], v0=sb[1], s=0.0, src="cameras.H0x, shift of M0 (motion-agent; skeleton spec)")}
    n = 12
    for k in range(n):
        t = k / (n - 1)
        loc = [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, p0[2]]
        F[f"a/S{k:02d}"] = dict(loc=loc, yaw=dolly["yaw"], u0=sa[0] + (sb[0] - sa[0]) * t, v0=sa[1] + (sb[1] - sa[1]) * t,
                                s=length * t, src=f"T-E0 dolly station {k}/11, shift linear in the distance (designer 3)")
        F[f"b/S{k:02d}"] = dict(loc=loc, yaw=dolly["yaw"], u0=sb[0], v0=sb[1], s=length * t,
                                src=f"T-E0 dolly station {k}/11, shift of M0 throughout (motion-agent 1)")
    for f in F.values():
        f["loc"] = [float(x) for x in f["loc"]]
    alias = {"a/S00": "H0x-a", "b/S00": "H0x-b", "a/S11": "b/S11"}     # identical cameras: rendered once, copied
    return F, alias, dict(version=plan["version"][:22], length_m=length, len_plan=dolly["len_m"],
                          heading_of_path_deg=math.degrees(math.atan2(-(p1[0] - p0[0]), -(p1[1] - p0[1]))))


def set_view_canvas(cam, f, res):
    """The 16:9 camera frame (24 mm, shift u0 / v0) placed at FRAME_BOX inside the canvas, at the render width res."""
    Wd, Hd = res, int(round(res * 9 / 16))
    k = Wd / CANVAS[0]
    fx, fy = (FRAME_BOX[2] - FRAME_BOX[0]) * k, (FRAME_BOX[3] - FRAME_BOX[1]) * Hd / CANVAS[1]
    ox, oy = FRAME_BOX[0] * k, FRAME_BOX[1] * Hd / CANVAS[1]
    cam.location = (f["loc"][0], f["loc"][1], f["loc"][2])
    cam.rotation_euler = (math.radians(90), 0, math.radians(180 - f["yaw"]))
    cd = cam.data
    cd.sensor_fit = "HORIZONTAL"
    cd.lens = 24.0
    cd.sensor_width = 36.0 * Wd / fx
    ycor = (20.25 * Hd / fy) / (cd.sensor_width * Hd / Wd)          # vertical extent wanted / the square-pixel one
    sc = bpy.context.scene
    sc.render.pixel_aspect_x, sc.render.pixel_aspect_y = (1.0 / ycor, 1.0) if ycor <= 1.0 else (1.0, ycor)
    U0, V0 = (ox + f["u0"] * fx) / Wd, (oy + f["v0"] * fy) / Hd
    cd.shift_x = -(U0 - 0.5)
    cd.shift_y = (V0 - 0.5) * ycor * Hd / Wd
    bpy.context.view_layer.update()
    return dict(W=Wd, H=Hd, fx=fx, fy=fy, ox=ox, oy=oy, pixel_aspect=[sc.render.pixel_aspect_x, sc.render.pixel_aspect_y])


def plan_uv(f, p):
    """The house plan's projection (conventions.projection), independent of Blender: (u, v, d) in frame units."""
    y = math.radians(f["yaw"])
    fw, rt = (-math.sin(y), -math.cos(y)), (math.cos(y), -math.sin(y))
    dx, dy = p[0] - f["loc"][0], p[1] - f["loc"][1]
    d = fw[0] * dx + fw[1] * dy
    x = rt[0] * dx + rt[1] * dy
    return f["u0"] + K_U * x / d, f["v0"] + K_V * (f["loc"][2] - p[2]) / d, d


# ---------------------------------------------------------------------------------------------------------------
# the scene: warm-modern r4 exactly as the furn layer builds it, then the hall
# ---------------------------------------------------------------------------------------------------------------
def build(a):
    rplan = json.load(open(os.path.join(W4.OUT, "plan.json")))
    for fid in r3.ORDER:
        f = rplan["frames"].setdefault(fid, {})
        f.setdefault("placeholders", []), f.setdefault("lamps", None), f.setdefault("also_visible", []), f.setdefault("notes", "")
    cams, _ = r3.cameras_1_1()
    r4.register_poses(rplan, cams)
    slots = r3.load_slots()
    r2.WARM = r3.WARM_R3
    _, plan0 = bh.load_plan()
    spec = json.load(open(r3.b4.SPEC_PATH))
    cfg = r3.b4.v4_config(spec)                       # patched by framing_wm_r4: the warm-modern window, planks 22, no cornice
    S, plan, notes, _ = r2.build_r2(plan0, cfg, a)
    R = r3.registry(S)
    notes["round3"] = r3.neutralise(S) + r3.living_vista(R) + r3.apply_fixes(S, R, slots, cube_lamp=rplan.get("hall_cube_lamp"))
    notes["round4"] = r4.v7_fixes(R)                  # patched: v7 + v8 + the warm-modern living shell (WMC1-WMC10)
    notes["round3"] += r3.light_balance(a)
    bpy.context.view_layer.update()
    r4.prebuild_generics(rplan, S, R, slots)
    notes["wm_entrance"] = wm_hall_fixes(S, R, cfg)
    # structure only: every slot proxy of every room hidden, every lamp off
    for v in R.values():
        r3.set_hidden(v["objs"], True)
    r2.lamps_set([])
    bpy.context.view_layer.update()
    return S, R, cfg, notes


def set_box(ob, x0, x1, y0, y1, z0, z1):
    assert not ob.modifiers and all(abs(abs(c) - 0.5) < 1e-6 for v in ob.data.vertices for c in v.co), ob.name
    ob.scale = (x1 - x0, y1 - y0, z1 - z0)
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def wbb(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return [min(c[i] for c in cs) for i in range(3)], [max(c[i] for c in cs) for i in range(3)]


def replay_living_planks(cfg):
    """build_alts.Shell.planks() again, without building: the same seed and draws, so every column's last plank and its natural end
    (where it would stop if the front wall did not clip it) are known. Checked against the built planks."""
    P = cfg["planks"]
    R_ = cfg["room"]
    xl, xr, yb, yf = R_["x_left"], R_["x_right"], R_["y_back"], R_["y_front"]
    rnd = random.Random(11)
    w, (lmin, lmax) = P["w"], P["len"]
    gap = 0.003
    cols, x, col = [], xl - 0.02, 0
    while x < xr:
        y = yb - 0.02 - rnd.uniform(0, lmax)
        seq = []
        while y < yf + 0.05:
            L = rnd.uniform(lmin, lmax)
            y0, y1 = max(y, yb - 0.02), min(y + L, yf + 0.05)
            built = (y1 - y0) > 0.05
            seq.append(dict(y=y, L=L, y0=y0, y1=y1, built=built, mat=rnd.choice(M["planks"]) if built else None))
            y += L
        cols.append(dict(col=col, x=x, x0=x + gap / 2, x1=min(x + w, xr + 0.02) - gap / 2, seq=seq, y_exit=y))
        x += w
        col += 1
    return cols, dict(w=w, lmin=lmin, lmax=lmax, gap=gap, x_start=xl - 0.02, y_clip=yf + 0.05)


def wm_hall_fixes(S, R, cfg):
    notes = []
    O, L, Hl = OPEN, LIN, HALL
    wall, sg = M["wall"], M["shadow_gap"]
    # ---- out: the Nordic portal and casing, cornice, console, bench, threshold strip, the Nordic planks of the hall ---------------
    gone = fr.kill("portal_jamb_a", "portal_jamb_b", "portal_head", "portal_case_a", "portal_case_b", "portal_case_h",
                   "hall_cornice*", "console3_top", "console3_leg", "bench_seat", "bench_end_a", "bench_end_b",
                   "O-entry-living_threshold", "hall_plank*")
    for k in ("G-H4 oak portal", "hall console"):
        if k in fr.REG:
            fr.REG[k]["objs"] = []
    if "hall-bench" in S["fur"]:
        S["fur"]["hall-bench"]["parts"] = []
    notes.append(f"removed {len(gone)} objects: oak portal + casing (G-H4), cornice, console (G-H3), bench, threshold strip, hall planks 25")
    # ---- the opening: the wall cut back by the lining thickness, then bead | gap | walnut | gap | bead through the depth ---------
    t, g, b, gd = L["t"], L["gap"], L["bead"], L["gap_depth"]
    wa, wb_, wab = (bpy.data.objects[n] for n in ("wall_front_a", "wall_front_b", "wall_front_above"))
    (ax0, ay0, az0), (ax1, ay1, az1) = wbb(wa)
    (bx0, by0, bz0), (bx1, by1, bz1) = wbb(wb_)
    assert abs(ax1 - O["x0"]) < 1e-6 and abs(bx0 - O["x1"]) < 1e-6 and abs(ay0 - O["y0"]) < 1e-6 and abs(ay1 - O["y1"]) < 1e-6
    set_box(wa, ax0, O["x0"] - t, ay0, ay1, az0, az1)
    set_box(wb_, O["x1"] + t, bx1, by0, by1, bz0, bz1)
    set_box(wab, O["x0"] - t, O["x1"] + t, ay0, ay1, O["h"] + t, az1)
    walnut = fr.mat_cache("walnut_wm", L["hex"], 0.85)
    pf = ba.SHELL_IDX["front-wall"]
    y0, y1 = O["y0"], O["y1"]
    bands = [(y0, y0 + b, "bead"), (y0 + b, y0 + b + g, "gap"), (y0 + b + g, y1 - b - g, "wood"), (y1 - b - g, y1 - b, "gap"), (y1 - b, y1, "bead")]
    for i, (ya, yb, kind) in enumerate(bands):
        mat, pidx = {"bead": (wall, pf), "wood": (walnut, PIDX["lining"]), "gap": (sg, PIDX["lining_gap"])}[kind]
        d = gd if kind == "gap" else 0.0          # the gap's bottom sits gap_depth behind the reveal plane
        bs.box(f"wmh_lin_{kind}{i}_jamb_a", O["x0"] - t, O["x0"] - d, ya, yb, 0.0, O["h"] + t, mat, "shell", pidx=pidx)
        bs.box(f"wmh_lin_{kind}{i}_jamb_b", O["x1"] + d, O["x1"] + t, ya, yb, 0.0, O["h"] + t, mat, "shell", pidx=pidx)
        bs.box(f"wmh_lin_{kind}{i}_head", O["x0"] - d, O["x1"] + d, ya, yb, O["h"] + d, O["h"] + t, mat, "shell", pidx=pidx)
    notes.append(f"O-entry-living: clear opening X {O['x0']}-{O['x1']}, Z 0-{O['h']} unchanged; walnut {L['hex']} on both jambs and the soffit, "
                 f"Y {y0 + b + g:.3f}-{y1 - b - g:.3f}, flush with the reveal plane; shadow gap {g * 1000:.0f} mm ({gd * 1000:.0f} mm deep) and a "
                 f"{b * 1000:.0f} mm plaster bead at each face; lining {t * 100:.0f} cm inside the wall; no casing, no leaf")
    # ---- skirting as WMC10 (wall material, 3 mm top arris; 1.5 proud as built), the ceiling shadow gap ---------------------------
    sk = [o for o in bpy.data.objects if o.name.startswith("hall_skirt_") and o.type == "MESH"]
    for o in sk:
        o.data.materials.clear()
        o.data.materials.append(wall)
        bv = o.modifiers.new("wmc10_bevel", "BEVEL")
        bv.width, bv.segments, bv.limit_method = 0.003, 2, "ANGLE"
    (hx0, hx1), (hy0, hy1), h, cg = Hl["x"], Hl["y"], Hl["h"], Hl["ceiling_gap"]
    e = 0.0015
    for nm, bx in (("y0", (hx0, hx1, hy0, hy0 + e)), ("y1", (hx0, hx1, hy1 - e, hy1)), ("x0", (hx0, hx0 + e, hy0, hy1)), ("x1", (hx1 - e, hx1, hy0, hy1))):
        bs.box(f"wmh_cgap_{nm}", bx[0], bx[1], bx[2], bx[3], h - cg, h - 0.0005, sg, "shell", pidx=PIDX["hall_cgap"])
    notes.append(f"{len(sk)} hall skirting boards in the wall material (WMC10); ceiling {h} with a {cg * 100:.0f} cm shadow gap, no cornice")
    # ---- the floor: the living room's plank columns carried through the opening and across the hall ------------------------------
    cols, P = replay_living_planks(cfg)
    built = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and (o.name == "plank_0" or o.name.startswith("plank_")) and o.pass_index == ba.SHELL_IDX["floor"]:
            lo, hi = wbb(o)
            built.setdefault(round(lo[0], 4), []).append((lo[1], hi[1], o))
    worst = 0.0
    for c in cols:
        have = sorted(built.get(round(c["x0"], 4), []), key=lambda q: q[0])
        want = [(s["y0"] + P["gap"] / 2, s["y1"] - P["gap"] / 2) for s in c["seq"] if s["built"]]
        assert len(have) == len(want), (c["col"], len(have), len(want))
        for (ha, hb, _), (wa_, wb2) in zip(have, want):
            worst = max(worst, abs(ha - wa_), abs(hb - wb2))
    assert worst < 1e-4, f"the plank replay does not match the built living planks ({worst})"
    rnd = random.Random(1114)
    gap, w = P["gap"], P["w"]
    n_new, joints = 0, []

    def piece(col, ya, yb, mat):
        """One plank between ya and yb: its part inside the wall depth (opening only) and its part in the hall."""
        nonlocal n_new
        xa, xb = col["x"] + gap / 2, col["x"] + w - gap / 2
        for (ra, rb, xa_, xb_) in ((O["y0"], O["y1"], max(xa, O["x0"]), min(xb, O["x1"])), (hy0, hy1, max(xa, hx0), min(xb, hx1))):
            a_, b_ = max(ya, ra), min(yb, rb)
            if b_ - a_ > 1e-4 and xb_ - xa_ > 1e-4:
                bs.box(f"wmh_plank_{col['col']}", xa_, xb_, a_, b_, -0.012, 0.0, mat, "floor", pidx=bh.IDX["floor"])
                n_new += 1

    k = 0
    while P["x_start"] + k * w < hx1:
        x = P["x_start"] + k * w
        if x + w <= hx0:
            k += 1
            continue
        col = dict(col=k, x=x)
        joints.append(round(x, 4))
        if k < len(cols):                       # a living column: its last plank goes on to its natural end
            last = cols[k]["seq"][-1]
            y = cols[k]["y_exit"]
            if last["built"]:
                piece(col, P["y_clip"] - gap / 2, y - gap / 2, last["mat"])       # butts the built plank at Y 6.2485: one board
            else:
                piece(col, last["y"] + gap / 2, y - gap / 2, rnd.choice(M["planks"]))
        else:                                   # east of the living room: a column that starts under the front wall
            y = hy0 - rnd.uniform(0, P["lmax"])
        while y < hy1:
            Lp = rnd.uniform(P["lmin"], P["lmax"])
            piece(col, y + gap / 2, min(y + Lp, hy1) - gap / 2, rnd.choice(M["planks"]))
            y += Lp
        k += 1
    notes.append(f"floor: {n_new} plank boxes, {w * 100:.0f} cm, along Y, on the living room's joint lines X = {P['x_start']} + {w} k "
                 f"(hall joints at X {joints[0] + w:.2f} .. {joints[-1]:.2f}); the living planks' last boards run on through the opening "
                 f"(no threshold strip); replay vs built living planks: max {worst * 1000:.3f} mm")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# passes
# ---------------------------------------------------------------------------------------------------------------
def geometry_pass(path, tmp, res):
    """Depth, object index and normal at the pixel centres: one sample, pixel filter 0.01 px, no denoising. (In the beauty render
    Cycles writes depth and index from its first sample, which the 1.5 px filter puts up to 0.75 px off the centre.)"""
    sc = bpy.context.scene
    keep = (sc.cycles.filter_width, sc.cycles.use_denoising)
    sc.cycles.filter_width, sc.cycles.use_denoising = 0.01, False
    try:
        out = fr.render(path, tmp, res, 1, ao=0.0)
    finally:
        sc.cycles.filter_width, sc.cycles.use_denoising = keep
    return out


def world_of(depth, f, cv):
    Hh, Ww = depth.shape
    u = ((np.arange(Ww) + 0.5) - cv["ox"]) / cv["fx"]
    v = ((np.arange(Hh) + 0.5) - cv["oy"]) / cv["fy"]
    y = math.radians(f["yaw"])
    fw, rt = (-math.sin(y), -math.cos(y)), (math.cos(y), -math.sin(y))
    d = np.where(depth < 1e4, depth, np.nan)
    xc = (u[None, :] - f["u0"]) * d / K_U
    X = f["loc"][0] + d * fw[0] + xc * rt[0]
    Y = f["loc"][1] + d * fw[1] + xc * rt[1]
    Z = f["loc"][2] - (v[:, None] - f["v0"]) * d / K_V
    return X, Y, Z


def classify(idx, depth, normal, f, cv, S):
    with np.errstate(invalid="ignore"):
        return _classify(idx, depth, normal, f, cv, S)


def _classify(idx, depth, normal, f, cv, S):
    X, Y, Z = world_of(depth, f, cv)
    nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
    e = 2e-3
    in_hall = Y >= OPEN["y1"] - e
    in_living = Y <= OPEN["y0"] + e
    out = np.full(idx.shape, 99, np.uint8)
    SI = ba.SHELL_IDX
    for pidx, cid in ((SI["sofa"], 41), (SI["coffee-table"], 42), (SI["armchair"], 43), (SI["window"], 39), (SI["sill"], 39),
                      (SI["lining"], 39), (SI["back-wall"], 31), (SI["left-wall"], 32), (SI["right-wall"], 33), (SI["ceiling"], 35),
                      (SI["skirting"], 38), (PIDX["lining_gap"], 23)):
        out[idx == pidx] = cid
    for key, cid in (("living/window-bench", 40), ("living/rounded-corner", 37), ("living/curtain-track", 36)):
        if key in fr.REG:
            out[idx == fr.REG[key]["pidx"]] = cid
    for pidx in (PIDX["hall_cgap"], bh.IDX["ceiling"], fr.REG["G-H1 roof light"]["pidx"]):
        out[(idx == pidx) & in_hall] = 15
    m = (idx == SI["floor"]) | (idx == bh.IDX["floor"]) | (idx == bh.IDX["threshold"])
    out[m & in_living] = 30
    out[m & in_hall] = 10
    out[m & ~in_living & ~in_hall] = 25
    m = idx == SI["front-wall"]
    out[m & in_hall] = 12
    out[m & in_living] = 34
    out[m & ~in_living & ~in_hall] = 24
    m = (idx == bh.IDX["wall"]) & in_hall
    out[m & (nx > 0.7)] = 11
    out[m & (ny > 0.7)] = 12
    out[m & (nx < -0.7)] = 13
    out[m & (ny < -0.7)] = 17
    out[(idx == bh.IDX["trim"]) & in_hall] = 14
    m = idx == PIDX["lining"]
    out[m & (nx > 0.7)] = 20
    out[m & (nx < -0.7)] = 21
    out[m & (nz < -0.7)] = 22
    out[m & (np.abs(ny) > 0.7)] = 23                   # the wood's end face, seen inside the 3 mm gap
    # beyond the living room's right wall: the dining room through O-living-dining (plan geometry, not part of this clay's design)
    out[(out == 99) & (X > 2.50 + e) & (Y < OPEN["y0"])] = 50
    sky = depth >= 1e4
    out[sky] = 0
    out[(idx == 0) & ~sky] = 98
    return out, (X, Y, Z)


def edges_of(cls, depth, normal):
    """Structure edges, 1 px: a change of surface id, a normal turn of more than 25 deg, or a depth step of more than 3 % and 3 cm."""
    E = np.zeros(cls.shape, bool)
    d = np.where(depth < 1e4, depth, 1e4)
    floor = np.isin(cls, (10, 25, 30))
    for ax in (0, 1):
        a = [slice(None), slice(None)]
        b_ = [slice(None), slice(None)]
        a[ax], b_[ax] = slice(0, -1), slice(1, None)
        a, b_ = tuple(a), tuple(b_)
        ch = cls[a] != cls[b_]
        dot = (normal[a] * normal[b_]).sum(-1)
        ch |= (dot < math.cos(math.radians(25))) & (cls[a] != 0) & ~floor[a]      # plank joints are not structure
        dd = np.abs(d[a] - d[b_])
        ch |= (dd > 0.03 * np.minimum(d[a], d[b_])) & (dd > 0.03)
        E[a] |= ch
    return E


def save_passes(fid, png, depth, idx, normal, f, cv, S, out_dir):
    from PIL import Image
    base = os.path.join(out_dir, fid)
    d16 = np.clip(np.rint(np.where(depth < 1e4, depth, 1e9) * DEPTH_UNITS_PER_M), 0, 65535).astype(np.uint16)
    Image.fromarray(d16).save(base + "-depth.png", optimize=True)
    cls, (X, Y, Z) = classify(idx, depth, normal, f, cv, S)
    im = Image.frombytes("P", (cls.shape[1], cls.shape[0]), np.ascontiguousarray(cls).tobytes())
    pal = [0] * 768
    for k, c in PALETTE.items():
        pal[3 * k:3 * k + 3] = c
    im.putpalette(pal)
    im.save(base + "-id.png", optimize=True)
    E = edges_of(cls, depth, normal)
    Image.fromarray(np.where(E, 0, 255).astype(np.uint8)).save(base + "-edges.png", optimize=True)
    npz = os.path.join(SCRATCH, "passes", fid.replace("/", "_") + ".npz")
    os.makedirs(os.path.dirname(npz), exist_ok=True)
    np.savez_compressed(npz, depth=depth.astype(np.float32), idx=idx.astype(np.int32),
                        normal=np.clip(np.rint(normal * 127), -127, 127).astype(np.int8), cls=cls)
    ids, cnt = np.unique(cls, return_counts=True)
    vis = {int(i): int(c) for i, c in zip(ids, cnt)}
    raw_ids, raw_cnt = np.unique(idx, return_counts=True)
    return dict(surfaces_px={f"{i} {IDS.get(i, '?')}": c for i, c in vis.items()},
                not_allowed_px={f"{i} {IDS.get(i, '?')}": c for i, c in vis.items() if i not in ALLOWED and i != 50},
                outside_scope_px=vis.get(50, 0),
                pass_indices_px={int(i): int(c) for i, c in zip(raw_ids, raw_cnt)},
                depth_m=dict(min=round(float(depth.min()), 3), max_finite=round(float(depth[depth < 1e4].max()), 3),
                             sky_px=int((depth >= 1e4).sum())), npz=npz)


# ---------------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="all")
    ap.add_argument("--res", type=int, default=CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--station-samples", type=int, default=None, help="samples for the stations S01-S10 (default: --samples)")
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=4.5)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    F, alias, pinfo = plan_frames()
    want = [k for k in F if k not in alias] if a.frames == "all" else a.frames.split(",")
    want = [alias.get(k, k) for k in want]
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    r4.EXR_DIR = os.path.join(SCRATCH, "exr")
    t0 = time.time()
    S, R, cfg, notes = build(a)
    names = {int(k): list(v) for k, v in r2.names_by_pidx(S).items()}
    names.update({PIDX["lining"]: ["hall/O-entry-living walnut lining", "architecture"], PIDX["lining_gap"]: ["hall/O-entry-living lining shadow gap", "architecture"],
                  PIDX["hall_cgap"]: ["hall ceiling shadow gap", "architecture"]})
    names.update({int(v): [k, "shell"] for k, v in ba.SHELL_IDX.items()})
    names.update({int(v): ["house " + k, "shell"] for k, v in bh.IDX.items()})
    meta = dict(stage="warm-modern entrance clay + T-E0 stations (briefs/wm-entrance-clay-2026-11-14.md); framing_wm_entrance.py on "
                      "framing_wm_r4_layers (furn layer); 0 var2 tokens",
                date=time.strftime("%Y-%m-%d"), plan=pinfo, canvas=dict(px=list(CANVAS), frame_box_px=[round(x, 4) for x in FRAME_BOX]),
                render=f"{a.res} px wide, Cycles CPU seed 7, OIDN, AgX Medium High Contrast, exposure +{r4.RENDER_EXPOSURE}",
                light=f"as the M0 furn clay: sky {a.sky}, living window x{a.living_boost}, hall roof light x{a.hall_roof}; every lamp off",
                build_notes={k: notes[k] for k in ("round4", "wm_entrance")}, build_s=round(time.time() - t0), ids=IDS,
                pass_index_names=names, opening=OPEN, lining=LIN, hall=HALL)
    json.dump(meta, open(os.path.join(SCRATCH, "meta.json"), "w"), indent=1, ensure_ascii=False)
    print("BUILD", meta["build_s"], "s;", *notes["wm_entrance"], sep="\n  ", flush=True)
    tmp = tempfile.mkdtemp(prefix="wm-entrance-")
    cam = S["cam"]
    for fid in want:
        f = F[fid]
        t1 = time.time()
        cv = set_view_canvas(cam, f, a.res)
        # the Blender camera against the plan's own projection, on points spread over the scene
        dev = 0.0
        for p in ((0.95, 6.35, 0.0), (2.15, 6.35, 2.40), (0.80, 6.35, 1.2), (3.60, 6.35, 0.5), (-2.30, 0.0, 3.0), (2.50, 0.0, 0.0), (0.20, 1.72, 3.0)):
            pu, pv, pd = plan_uv(f, p)
            if pd < 0.2:
                continue
            bu, bv_, bd = bs.proj(cam, p)
            cu, cv_ = (pu * cv["fx"] + cv["ox"]) / cv["W"], (pv * cv["fy"] + cv["oy"]) / cv["H"]
            dev = max(dev, abs(bu - cu) * cv["W"], abs(bv_ - cv_) * cv["H"], abs(bd - pd) * 1000)
        png = os.path.join(a.out, fid + ".png")
        os.makedirs(os.path.dirname(png), exist_ok=True)
        smp = a.station_samples if (a.station_samples and "/S" in fid and fid[-2:] not in ("00", "11")) else a.samples
        depth, idx, normal = geometry_pass(os.path.join(tmp, "g.png"), os.path.join(tmp, "g"), a.res)
        fr.render(png, os.path.join(tmp, "p"), a.res, smp, ao=0.30)
        for nm in ("g", os.path.basename(fid)):
            exr = os.path.join(r4.EXR_DIR, nm + ".exr")
            if os.path.exists(exr):
                os.remove(exr)                               # the composite EXR is not kept (disk)
        rec = dict(frame=fid, camera=dict(loc=[round(x, 4) for x in f["loc"]], yaw=f["yaw"], lens=24, u0=round(f["u0"], 6), v0=round(f["v0"], 6),
                                           s_m=None if f["s"] is None else round(f["s"], 4), source=f["src"]),
                   canvas=cv, samples=smp, camera_vs_plan_projection_max_px_or_mm=round(dev, 4), mean_L=fr.mean_L(png))
        rec.update(save_passes(fid, png, depth, idx, normal, f, cv, S, a.out))
        rec["runtime_s"] = round(time.time() - t1)
        os.makedirs(os.path.join(SCRATCH, "frames"), exist_ok=True)
        json.dump(rec, open(os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json"), "w"), indent=1, ensure_ascii=False)
        print("FRAME", fid, rec["runtime_s"], "s  L", rec["mean_L"], " cam dev", rec["camera_vs_plan_projection_max_px_or_mm"],
              " not allowed", rec["not_allowed_px"], flush=True)
    for dst, src in alias.items():                            # identical cameras: copies
        if src in want and a.frames == "all":
            for suf in (".png", "-depth.png", "-id.png", "-edges.png"):
                os.makedirs(os.path.dirname(os.path.join(a.out, dst)), exist_ok=True)
                shutil.copyfile(os.path.join(a.out, src + suf), os.path.join(a.out, dst + suf))
    shutil.rmtree(tmp, ignore_errors=True)
    print("DONE", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main(_ARGV)
