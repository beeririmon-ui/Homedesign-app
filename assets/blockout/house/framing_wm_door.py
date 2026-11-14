#!/usr/bin/env python3
"""
framing_wm_door.py: the warm-modern entrance court and FRONT DOOR as a clay, and the cameras of storyboard S1, render-agent, 2026-11-14.
Brief: briefs/wm-door-clay-and-d0-still-2026-11-14.md. 0 var2 tokens.
Sources: master-designer docs/proposals/wm-front-door-2026-11-14.md (1.1 the door and the court, 2 the light, 3 camera D0, 4.2 HD);
motion-agent docs/proposals/wm-arrival-from-door-2026-11-14.md (1 the 3:2 canvas, 2 the list, 3 clip 1 and HT).

The scene = framing_wm_entrance.py (the warm-modern r4 living room of base.png + the warm-modern hall: walnut-lined O-entry-living, no
casing, ceiling shadow gap, 22 cm planks) plus, here (court_and_door()):
  - the covered court X 3.95-7.60, Y 6.55-9.60 (house plan footprint.porch): honed limestone floor #D8C8AE in 60 x 120 slabs, stack bond,
    long side along X, one slab centred on the door axis (Y 8.00-8.60), rows from the leaf line X 3.66, 3 mm joints; the stone runs into
    the reveal to the leaf; plaster ceiling at 3.00; a 1 cm dark line where the plaster meets the stone (no skirting); the open ground
    outside (south and the west gap X 6.60-7.60) as a plain plane at Z 0;
  - O-front-door (X 3.60-3.95, Y 7.80-8.80, Z 0-2.40): plaster reveal 0.29 deep with 3 cm rounded inside corners at the head; a flush
    walnut leaf 6 cm in the inner face (X 3.60-3.66); a vertical bar pull #3A322C, d 25 mm, 600 mm, centre Z 1.05, at Y 7.90, on two
    4 cm standoffs; hinges hidden on the Y 8.80 side, opening inward; leaf state closed / none / open (90 deg: X 2.60-3.60, Y 8.74-8.80);
  - the bath window seen from the court in dark bronze (frame recoloured; its 6 cm clay frame kept, the designer's 45 mm is a render
    instruction); fluted glass as in the round-2 clay;
  - O-hall-work as a closed jib door flush with the hall face X 0.80, wall-coloured, 3 mm shadow gap on three sides (Y 8.10-9.00, to Z 2.40);
    the folded leaf and its threshold plank removed;
  - the oak floor carried into the door opening to the leaf line (X 3.60-3.66), no threshold strip.
Frames (cameras exactly as the two proposals; the plan has none of them yet):
  D0-closed, D0-none, D0-open  (7.40, 8.15, 1.20) yaw 90, shift 0.36 / 0.48, base.png canvas 2720 x 1530
  HD   (2.462, 8.15, 1.20) yaw 90, shift 0.36 / 0.48, 3:2 canvas 2496 x 1664, frame [71.11, 170.00, 2424.89, 1494.00]
  HDx  same point, yaw 25, shift 0.47 / 0.50, 3:2 canvas
  HD57 same point, yaw 57.5, shift 0.415 / 0.49, base.png canvas (reserve, clay only)
  HT   (3.60, 8.15, 1.20) yaw 90, shift 0.36 / 0.48, base.png canvas, leaf open
  c1/S00..S11: 12 stations D0 -> HD at even distance (0.449 m), yaw 90, shift 0.36 / 0.48, leaf open, base.png canvas (S00 = D0-open)
Passes per frame as in wm-entrance-2026-11-14: <id>.png, -depth.png (16-bit, metres = value / 5000, 65535 = sky), -id.png (palette),
-edges.png; float passes (npz) in the scratchpad.

  python3 framing_wm_door.py --frames D0-closed --samples 16
  python3 framing_wm_door.py --frames all
"""
import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_ARGV = sys.argv[1:]

import framing_wm_entrance as E  # noqa: E402  (imports the warm-modern r4 layers: the furn layer of base.png)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

LY, W4 = E.LY, E.W4
fr, r2, bh, ba, bs, M = E.fr, E.r2, E.bh, E.ba, E.bs, E.M

OUT = os.path.join(HERE, "framing", "wm-door-2026-11-14")
SCRATCH = os.path.join(W4.SCRATCH, "wm-door")
E.SCRATCH = SCRATCH

REG_CANVAS, REG_BOX = E.CANVAS, E.FRAME_BOX
TALL_CANVAS, TALL_BOX = (2496, 1664), (71.11, 170.00, 2424.89, 1494.00)          # motion-agent 1 (3:2)
DOOR = dict(x_in=3.60, x_leaf=3.66, x_out=3.95, y0=7.80, y1=8.80, h=2.40, hinge=(3.60, 8.80))
COURT = dict(x=(3.95, 7.60), y=(6.55, 9.60), h=3.00, west_gap_x=(6.60, 7.60))
STONE = dict(hex="#D8C8AE", along_x=1.20, along_y=0.60, y_ref=8.00, x_ref=3.66, joint=0.003)
PULL = dict(y=7.90, z=(0.75, 1.35), d=0.025, standoff=0.04)
JIB = dict(x=(0.65, 0.80), y=(8.10, 9.00), h=2.40, gap=0.003)
PIDX = dict(leaf=710, pull=711, stone=712, court_ceiling=713, ground=714, jib=715, jib_gap=716, foot_line=717, fillet=718)
D0 = dict(loc=[7.40, 8.15, 1.20], yaw=90.0, u0=0.36, v0=0.48)
HDP = dict(loc=[2.462, 8.15, 1.20])

IDS = dict(E.IDS)
IDS.update({60: "court floor, limestone (incl. the reveal floor)", 61: "court wall with the door (X 3.95)", 62: "court left wall (Y 9.60)",
            63: "court right wall (Y 6.55)", 64: "door reveal, plaster (jambs, head, fillets)", 65: "court ceiling", 66: "court wall foot line (1 cm)",
            67: "ground outside the court", 70: "front door leaf, face", 71: "front door leaf, edge", 72: "door pull (bronze)",
            75: "bath window frame (bronze)", 76: "bath window, fluted glass", 82: "jib door of the study (closed)", 83: "jib door shadow gap"})
E.IDS.clear()
E.IDS.update(IDS)
PAL = dict(E.PALETTE)
PAL.update({60: (216, 200, 174), 61: (236, 229, 218), 62: (200, 190, 175), 63: (245, 240, 232), 64: (225, 215, 200), 65: (230, 225, 215),
            66: (40, 40, 40), 67: (120, 130, 110), 70: (107, 74, 51), 71: (70, 45, 30), 72: (58, 50, 44), 75: (58, 50, 44), 76: (170, 175, 180),
            82: (255, 210, 120), 83: (90, 60, 20)})
E.PALETTE.clear()
E.PALETTE.update(PAL)
E.ALLOWED.update({60, 61, 62, 63, 64, 65, 66, 67, 70, 71, 72, 75, 76, 82, 83})
LEAF = dict(state="closed", root=None, objs=[])


# ---------------------------------------------------------------------------------------------------------------
# cameras
# ---------------------------------------------------------------------------------------------------------------
def frames():
    F = {"D0-closed": dict(D0, leaf="closed", canvas="reg"), "D0-none": dict(D0, leaf="none", canvas="reg"), "D0-open": dict(D0, leaf="open", canvas="reg"),
         "HD": dict(loc=HDP["loc"], yaw=90.0, u0=0.36, v0=0.48, leaf="open", canvas="tall"),
         "HDx": dict(loc=HDP["loc"], yaw=25.0, u0=0.47, v0=0.50, leaf="open", canvas="tall"),
         "HD57": dict(loc=HDP["loc"], yaw=57.5, u0=0.415, v0=0.49, leaf="open", canvas="reg"),
         "HT": dict(loc=[3.60, 8.15, 1.20], yaw=90.0, u0=0.36, v0=0.48, leaf="open", canvas="reg")}
    p0, p1 = D0["loc"], HDP["loc"]
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    for k in range(12):
        t = k / 11
        F[f"c1/S{k:02d}"] = dict(loc=[p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, 1.20], yaw=90.0, u0=0.36, v0=0.48, leaf="open",
                                 canvas="reg", s=L * t)
    for f in F.values():
        f["loc"] = [float(x) for x in f["loc"]]
        f.setdefault("s", None)
    alias = {"c1/S00": "D0-open"}
    return F, alias, L


def set_view(cam, f, res_w):
    canvas, box = (REG_CANVAS, REG_BOX) if f["canvas"] == "reg" else (TALL_CANVAS, TALL_BOX)
    Wd = res_w
    Hd = int(round(res_w * canvas[1] / canvas[0]))
    k = Wd / canvas[0]
    fx, fy = (box[2] - box[0]) * k, (box[3] - box[1]) * Hd / canvas[1]
    ox, oy = box[0] * k, box[1] * Hd / canvas[1]
    cam.location = tuple(f["loc"])
    cam.rotation_euler = (math.radians(90), 0, math.radians(180 - f["yaw"]))
    cd = cam.data
    cd.sensor_fit = "HORIZONTAL"
    cd.lens = 24.0
    cd.sensor_width = 36.0 * Wd / fx
    ycor = (20.25 * Hd / fy) / (cd.sensor_width * Hd / Wd)
    sc = bpy.context.scene
    sc.render.pixel_aspect_x, sc.render.pixel_aspect_y = (1.0 / ycor, 1.0) if ycor <= 1.0 else (1.0, ycor)
    U0, V0 = (ox + f["u0"] * fx) / Wd, (oy + f["v0"] * fy) / Hd
    cd.shift_x = -(U0 - 0.5)
    cd.shift_y = (V0 - 0.5) * ycor * Hd / Wd
    bpy.context.view_layer.update()
    return dict(W=Wd, H=Hd, fx=fx, fy=fy, ox=ox, oy=oy, canvas=list(canvas), frame_box=list(box), pixel_aspect=[sc.render.pixel_aspect_x, sc.render.pixel_aspect_y])


# ---------------------------------------------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------------------------------------------
def prism_x(name, pts_yz, x0, x1, mat, pidx, coll="shell"):
    """A prism along X from a (y, z) profile."""
    me = bpy.data.meshes.new(name)
    n = len(pts_yz)
    verts = [(x0, y, z) for y, z in pts_yz] + [(x1, y, z) for y, z in pts_yz]
    faces = [list(range(n)), list(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bs.coll(coll).objects.link(ob)
    ob.data.materials.append(mat)
    ob.pass_index = pidx
    return ob


def court_and_door():
    notes = []
    wall, sg = M["wall"], M["shadow_gap"]
    walnut = fr.mat_cache("walnut_wm", "#6B4A33", 0.85)
    bronze = fr.mat_cache("bronze_wm", "#3A322C", 0.45)
    lime = fr.mat_cache("limestone_court", STONE["hex"], 0.75)
    ground = fr.mat_cache("ground_court", "#8C8A80", 0.95)
    gone = fr.kill("front_door_closed_h2", "front_door_closed", "O-front-door_threshold", "O-front-door_threshold_base", "leaf_hall_work_folded",
                   "O-hall-work_threshold")
    if "front door (G-H2)" in fr.REG:
        fr.REG["front door (G-H2)"]["objs"] = []
    notes.append(f"removed {len(gone)} objects: {gone}")
    # ---- court floor: limestone slabs, joints 3 mm over a dark bed -----------------------------------------------------------------
    (cx0, cx1), (cy0, cy1) = COURT["x"], COURT["y"]
    j = STONE["joint"] / 2
    bs.box("court_bed", DOOR["x_leaf"], cx1, cy0, cy1, -0.12, -0.031, sg, "floor", pidx=PIDX["stone"])
    ys = [STONE["y_ref"] + STONE["along_y"] * k for k in range(-4, 4)]
    rows = sorted({min(max(y, cy0), cy1) for y in ys} | {cy0, cy1})
    cols = [DOOR["x_leaf"] + STONE["along_x"] * k for k in range(0, 5)]
    cols = sorted({min(c, cx1) for c in cols} | {cx1})
    n = 0
    for (ya, yb) in zip(rows[:-1], rows[1:]):
        for (xa, xb) in zip(cols[:-1], cols[1:]):
            for (rx0, rx1, ry0, ry1) in ((DOOR["x_leaf"], DOOR["x_out"], DOOR["y0"], DOOR["y1"]), (DOOR["x_out"], cx1, cy0, cy1)):
                a0, a1, b0, b1 = max(xa, rx0), min(xb, rx1), max(ya, ry0), min(yb, ry1)
                if a1 - a0 < 1e-4 or b1 - b0 < 1e-4:
                    continue
                g0 = j if abs(a0 - xa) < 1e-6 else 0.0          # a joint only at a slab edge, not where the reveal clips it
                g1 = j if abs(a1 - xb) < 1e-6 else 0.0
                h0 = j if abs(b0 - ya) < 1e-6 else 0.0
                h1 = j if abs(b1 - yb) < 1e-6 else 0.0
                bs.box(f"court_slab_{n}", a0 + g0, a1 - g1, b0 + h0, b1 - h1, -0.03, 0.0, lime, "floor", pidx=PIDX["stone"])
                n += 1
    notes.append(f"court floor: {n} limestone pieces {STONE['along_x']} x {STONE['along_y']}, rows on Y {rows}, slab joints across X at {cols}; "
                 f"stone into the reveal to the leaf (X {DOOR['x_leaf']})")
    # ---- ground outside, court ceiling, the dark foot line ---------------------------------------------------------------------------
    bs.box("ground_south", cx1, cx1 + 60, -40, 60, -0.05, -0.001, ground, "shell", pidx=PIDX["ground"])
    bs.box("ground_west", COURT["west_gap_x"][0], cx1, cy1, 60, -0.05, -0.001, ground, "shell", pidx=PIDX["ground"])
    bs.box("court_ceiling", cx0, cx1, cy0, cy1, COURT["h"], bh.TOP, M["ceiling"], "ceiling", pidx=PIDX["court_ceiling"])
    e = 0.0015
    for nm, b in (("door_wall_a", (cx0, cx0 + e, cy0, DOOR["y0"])), ("door_wall_b", (cx0, cx0 + e, DOOR["y1"], cy1)),
                  ("left", (cx0, COURT["west_gap_x"][0], cy1 - e, cy1)), ("right", (cx0, cx1, cy0, cy0 + e)),
                  ("jamb_a", (DOOR["x_leaf"], DOOR["x_out"], DOOR["y0"], DOOR["y0"] + e)), ("jamb_b", (DOOR["x_leaf"], DOOR["x_out"], DOOR["y1"] - e, DOOR["y1"]))):
        bs.box(f"court_foot_{nm}", b[0], b[1], b[2], b[3], 0.0, 0.01, sg, "shell", pidx=PIDX["foot_line"])
    notes.append(f"ground plane outside (south of X {cx1}; west gap X {COURT['west_gap_x']}); court ceiling {COURT['h']}; 1 cm dark line at the wall feet")
    # ---- the reveal: 3 cm fillets at the two head corners, along the reveal depth ------------------------------------------------------
    r = 0.03
    for nm, yc, sgn in (("a", DOOR["y0"], 1), ("b", DOOR["y1"], -1)):
        arc = [(yc + sgn * (r - r * math.cos(t)), DOOR["h"] - (r - r * math.sin(t))) for t in np.linspace(0, math.pi / 2, 9)]
        pts = [(yc, DOOR["h"])] + arc[::-1] if sgn > 0 else [(yc, DOOR["h"])] + arc
        prism_x(f"reveal_fillet_{nm}", pts, DOOR["x_leaf"], DOOR["x_out"], wall, PIDX["fillet"])
    notes.append("reveal: plaster (the house wall), 0.29 visible depth X 3.66-3.95; 3 cm fillets at the jamb / head inside corners")
    # ---- the leaf and the pull, parented to the hinge -----------------------------------------------------------------------------
    root = bpy.data.objects.new("front_door_hinge", None)
    bs.coll("doors").objects.link(root)
    root.location = (DOOR["hinge"][0], DOOR["hinge"][1], 0.0)
    parts = [bs.box("wm_front_leaf", DOOR["x_in"], DOOR["x_leaf"], DOOR["y0"] + 0.001, DOOR["y1"] - 0.001, 0.001, DOOR["h"] - 0.001, walnut, "doors",
                    pidx=PIDX["leaf"])]
    xb = DOOR["x_leaf"] + PULL["standoff"] + PULL["d"] / 2
    parts.append(bs.cone("wm_pull_bar", xb, PULL["y"], PULL["z"][0], PULL["z"][1], PULL["d"] / 2, PULL["d"] / 2, bronze, "doors", verts=24, pidx=PIDX["pull"]))
    for k, z in enumerate((PULL["z"][0] + 0.05, PULL["z"][1] - 0.05)):
        parts.append(bs.box(f"wm_pull_standoff{k}", DOOR["x_leaf"], DOOR["x_leaf"] + PULL["standoff"], PULL["y"] - 0.006, PULL["y"] + 0.006, z - 0.006,
                            z + 0.006, bronze, "doors", pidx=PIDX["pull"]))
    bpy.context.view_layer.update()
    for p in parts:
        mw = p.matrix_world.copy()
        p.parent = root
        p.matrix_parent_inverse = root.matrix_world.inverted()
        p.matrix_world = mw
    LEAF.update(root=root, objs=parts)
    notes.append(f"front door: walnut leaf X {DOOR['x_in']}-{DOOR['x_leaf']}, Y {DOOR['y0']}-{DOOR['y1']}, Z 0-{DOOR['h']}; bar pull d {PULL['d']} "
                 f"Z {PULL['z']} at Y {PULL['y']} on 4 cm standoffs; hinge axis ({DOOR['hinge'][0]}, {DOOR['hinge'][1]}), opens inward")
    # ---- the bath window from the court: dark bronze frame --------------------------------------------------------------------------
    nb = 0
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("W-bath_") and not o.name.startswith("W-bath_reveal") and not o.name.startswith("W-bath_sill"):
            o.data.materials.clear()
            o.data.materials.append(bronze)
            nb += 1
    notes.append(f"W-bath: {nb} frame / sash objects in bronze #3A322C (clay profile 6 cm; the render asks for 45 mm)")
    # ---- the study door as a closed jib door -------------------------------------------------------------------------------------
    g = JIB["gap"]
    bs.box("jib_back", JIB["x"][0], JIB["x"][1] - 0.02, JIB["y"][0], JIB["y"][1], 0.0, JIB["h"], sg, "doors", pidx=PIDX["jib_gap"])
    bs.box("jib_leaf", JIB["x"][1] - 0.05, JIB["x"][1], JIB["y"][0] + g, JIB["y"][1] - g, 0.0, JIB["h"] - g, wall, "doors", pidx=PIDX["jib"])
    notes.append(f"O-hall-work: closed jib leaf flush with X {JIB['x'][1]}, Y {JIB['y'][0] + g:.3f}-{JIB['y'][1] - g:.3f}, Z 0-{JIB['h'] - g:.3f}, "
                 f"3 mm gap on both sides and at the head (no skirting on the leaf)")
    # ---- oak into the door opening to the leaf line --------------------------------------------------------------------------------
    pl = M["planks"]
    for k, (xa, xb_) in enumerate(((DOOR["x_in"], 3.62 - 0.0015), (3.62 + 0.0015, DOOR["x_leaf"]))):
        bs.box(f"door_oak_{k}", xa, xb_, DOOR["y0"], DOOR["y1"], -0.012, 0.0, pl[k % len(pl)], "floor", pidx=bh.IDX["floor"])
    bs.box("door_oak_bed", DOOR["x_in"], DOOR["x_leaf"], DOOR["y0"], DOOR["y1"], -0.12, -0.012, sg, "floor", pidx=bh.IDX["floor"])
    notes.append("oak floor carried into the opening to X 3.66 on the hall's joint line X 3.62; no threshold strip")
    return notes


def set_leaf(state):
    root = LEAF["root"]
    root.rotation_euler = (0, 0, math.radians(-90.0) if state == "open" else 0.0)
    for o in LEAF["objs"]:
        o.hide_render = state == "none"
    LEAF["state"] = state
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------------------------------------------
# render (explicit width and height, so the 3:2 canvas works) and the passes
# ---------------------------------------------------------------------------------------------------------------
def hide_like_furn_layer():
    for ob in bpy.data.objects:
        if ob.type != "LIGHT" and getattr(ob, "pass_index", 0) in LY.HIDE:
            ob.hide_render = True
        elif ob.type == "LIGHT" and ob.name.startswith("lv_") and not ob.hide_render:
            ob.hide_render = True
    LY.bible_furniture()


def render_wh(path, tmp, W, H, samples, ao, exposure, passes=True):
    sc = bpy.context.scene
    sc.view_settings.exposure = exposure
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.cycles.samples = samples
    fr.setup_comp(tmp, ao)
    sc.frame_set(1)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if not passes:
        return None
    depth = bs.load_exr(os.path.join(tmp, "Depth_0001.exr"))
    idx = np.rint(bs.load_exr(os.path.join(tmp, "IndexOB_0001.exr"))).astype(np.int32)
    normal = bs.load_exr(os.path.join(tmp, "Normal_0001.exr"), channels=3)
    return depth, idx, normal


def geometry_pass(tmp, W, H):
    sc = bpy.context.scene
    keep = (sc.cycles.filter_width, sc.cycles.use_denoising)
    sc.cycles.filter_width, sc.cycles.use_denoising = 0.01, False
    try:
        return render_wh(os.path.join(tmp, "g.png"), os.path.join(tmp, "g"), W, H, 1, 0.0, 1.0)
    finally:
        sc.cycles.filter_width, sc.cycles.use_denoising = keep


def classify_door(idx, depth, normal, f, cv, IM):
    with np.errstate(invalid="ignore"):
        out, (X, Y, Z) = E._classify(idx, depth, normal, f, cv, IM)
        nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
        e = 2e-3
        court = X > DOOR["x_in"] + e
        wallm = (idx == IM["house_wall"]) & court
        out[wallm & (X > DOOR["x_out"] - e) & (nx > 0.7)] = 61
        out[wallm & (ny < -0.7) & (Y > COURT["y"][1] - 0.05)] = 62
        out[wallm & (ny > 0.7) & (Y < COURT["y"][0] + 0.05)] = 63
        rev = wallm & (X < DOOR["x_out"] - e) & (Y > DOOR["y0"] - e) & (Y < DOOR["y1"] + e)
        out[rev] = 64
        out[(idx == IM["house_ceiling"]) & court] = 65
        for key, cid in (("stone", 60), ("court_ceiling", 65), ("ground", 67), ("foot_line", 66), ("fillet", 64), ("pull", 72), ("jib", 82), ("jib_gap", 83)):
            out[idx == PIDX[key]] = cid
        lf = idx == PIDX["leaf"]
        big = (np.abs(nx) > 0.7) if LEAF["state"] != "open" else (np.abs(ny) > 0.7)
        out[lf & big] = 70
        out[lf & ~big] = 71
        out[idx == IM["w_bath"]] = 75
        out[idx == IM["fluted"]] = 76
        out[(idx == IM["house_trim"]) & court] = 75                      # the bath window's sill board seen from the court side
        jibside = (idx == IM["house_wall"]) & (X < JIB["x"][1] + e) & (Y > JIB["y"][0] - e) & (Y < JIB["y"][1] + e) & (Z < JIB["h"] + e)
        out[jibside] = 83                                                  # the wall's end faces seen inside the jib door's 3 mm gap
        rest = (out == 99) & (idx == IM["house_wall"]) & court             # arris pixels whose normal is neither face's
        out[rest & (X > DOOR["x_out"] - 0.01)] = 61
        out[rest & (X <= DOOR["x_out"] - 0.01)] = 64
    return out, (X, Y, Z)


def edges_door(cls, depth, normal):
    Em = np.zeros(cls.shape, bool)
    d = np.where(depth < 1e4, depth, 1e4)
    floor = np.isin(cls, (10, 25, 30, 60, 67))
    for ax in (0, 1):
        a = [slice(None), slice(None)]
        b_ = [slice(None), slice(None)]
        a[ax], b_[ax] = slice(0, -1), slice(1, None)
        a, b_ = tuple(a), tuple(b_)
        ch = cls[a] != cls[b_]
        dot = (normal[a] * normal[b_]).sum(-1)
        ch |= (dot < math.cos(math.radians(25))) & (cls[a] != 0) & ~floor[a]
        dd = np.abs(d[a] - d[b_])
        ch |= (dd > 0.03 * np.minimum(d[a], d[b_])) & (dd > 0.03) & ~(floor[a] & floor[b_])
        Em[a] |= ch
    return Em


def index_map_door(names=None):
    IM = E.index_map(names)
    if names is None:
        IM["w_bath"] = bh_windows()["W-bath"]
        IM["fluted"] = int(fr.REG["bath fluted glazing"]["pidx"])
    else:
        IM["w_bath"] = next(int(i) for i, v in names.items() if v[0] == "window W-bath")
        IM["fluted"] = next(int(i) for i, v in names.items() if v[0] == "bath fluted glazing")
    return IM


def bh_windows():
    out = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("W-") and "_" in o.name:
            out.setdefault(o.name.split("_")[0], o.pass_index)
    return out


# ---------------------------------------------------------------------------------------------------------------
def reclassify(a, F, alias):
    """The id and edge passes again from the saved float passes (scratchpad), without a render."""
    meta = json.load(open(os.path.join(SCRATCH, "meta.json")))
    names = meta["pass_index_names"]
    IM = index_map_door(names)
    E.classify = classify_door
    E.edges_of = edges_door
    for fid in ([k for k in F if k not in alias] if a.frames == "all" else [alias.get(k, k) for k in a.frames.split(",")]):
        npz = os.path.join(SCRATCH, "passes", fid.replace("/", "_") + ".npz")
        jp = os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json")
        if not (os.path.exists(npz) and os.path.exists(jp)):
            continue
        z = np.load(npz)
        rec = json.load(open(jp))
        LEAF["state"] = F[fid]["leaf"]
        rec.update(E.save_passes(fid, os.path.join(a.out, fid + ".png"), z["depth"], z["idx"], z["normal"].astype(np.float32) / 127.0, F[fid], rec["canvas"],
                                 IM, a.out, write_npz=False))
        json.dump(rec, open(jp, "w"), indent=1, ensure_ascii=False)
        print("RECLASSIFIED", fid, "not allowed", rec["not_allowed_px"], flush=True)
    for dst, src in alias.items():
        for suf in ("-depth.png", "-id.png", "-edges.png"):
            if os.path.exists(os.path.join(a.out, src + suf)):
                os.makedirs(os.path.dirname(os.path.join(a.out, dst)), exist_ok=True)
                shutil.copyfile(os.path.join(a.out, src + suf), os.path.join(a.out, dst + suf))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--reclassify", action="store_true", help="rewrite the id and edge passes from the saved float passes; no render")
    ap.add_argument("--frames", default="all")
    ap.add_argument("--res", type=int, default=None, help="render width (default: the canvas width)")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--station-samples", type=int, default=10)
    ap.add_argument("--exposure", type=float, default=None, help="render exposure for every frame (default: --door-exposure)")
    ap.add_argument("--door-exposure", type=float, default=0.75, help="one locked exposure for the court, the hall and the living room")
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=4.5)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    a.exposure_cli = a.exposure
    F, alias, L = frames()
    if a.reclassify:
        return reclassify(a, F, alias)
    want = [k for k in F if k not in alias] if a.frames == "all" else [alias.get(k, k) for k in a.frames.split(",")]
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    W4.r4.EXR_DIR = os.path.join(SCRATCH, "exr")
    t0 = time.time()
    a.exposure = 1.0
    res_cli = a.res
    a.res = res_cli or REG_CANVAS[0]
    S, R, cfg, notes = E.build(a)
    notes["door"] = court_and_door()
    for ob in bpy.data.objects:                              # the clay rig's soft light "outside" the bath window stands in the court
        if ob.type == "LIGHT" and ob.name == "winlight_W-bath":
            ob.hide_render = True
            notes["door"].append("winlight_W-bath off: the round-2 rig put the bath window's outside light in the court (3.85, 8.40); "
                                 "the court is lit by the sky alone")
    hide_like_furn_layer()
    IM = index_map_door()
    E.classify = classify_door
    E.edges_of = edges_door
    names = {int(k): list(v) for k, v in r2.names_by_pidx(S).items()}
    names.update({E.PIDX["lining"]: ["hall/O-entry-living walnut lining", "architecture"], E.PIDX["lining_gap"]: ["hall/O-entry-living lining shadow gap", "architecture"],
                  E.PIDX["hall_cgap"]: ["hall ceiling shadow gap", "architecture"]})
    names.update({int(v): [k, "shell"] for k, v in ba.SHELL_IDX.items()})
    names.update({int(v): ["house " + k, "shell"] for k, v in bh.IDX.items()})
    names.update({int(v): ["door/" + k, "architecture"] for k, v in PIDX.items()})
    expo = a.exposure_cli if a.exposure_cli is not None else a.door_exposure
    meta = dict(stage="warm-modern court + front door clay and the S1 cameras (briefs/wm-door-clay-and-d0-still-2026-11-14.md); framing_wm_door.py "
                      "on framing_wm_entrance.py; 0 var2 tokens", date=time.strftime("%Y-%m-%d"), clip1_length_m=L,
                canvases=dict(reg=dict(px=list(REG_CANVAS), frame_box_px=[round(x, 4) for x in REG_BOX]), tall=dict(px=list(TALL_CANVAS), frame_box_px=list(TALL_BOX))),
                render=f"Cycles CPU seed 7, OIDN, AgX Medium High Contrast, exposure {expo} for every frame (one locked exposure)",
                light=f"the entrance clay's light: sky {a.sky}, living window x{a.living_boost}, hall roof light x{a.hall_roof}; every lamp off; the court lit by the sky only",
                build_notes={k: notes[k] for k in ("wm_entrance", "door")}, build_s=round(time.time() - t0), ids=IDS, pass_index_names=names,
                door=DOOR, court=COURT, stone=STONE, pull=PULL, jib=JIB, index_map=IM)
    json.dump(meta, open(os.path.join(SCRATCH, "meta.json"), "w"), indent=1, ensure_ascii=False, default=str)
    print("BUILD", meta["build_s"], "s;", *notes["door"], sep="\n  ", flush=True)
    tmp = tempfile.mkdtemp(prefix="wm-door-")
    cam = S["cam"]
    from PIL import Image
    for fid in want:
        f = F[fid]
        t1 = time.time()
        set_leaf(f["leaf"])
        canvas = REG_CANVAS if f["canvas"] == "reg" else TALL_CANVAS
        cv = set_view(cam, f, res_cli or canvas[0])
        dev = 0.0
        for p in ((3.95, 8.80, 0.0), (3.95, 6.55, 2.0), (0.80, 8.10, 1.0), (0.80, 8.90, 1.9), (0.80, 7.40, 0.6), (0.95, 6.35, 2.4), (2.15, 6.35, 0.3),
                  (-2.30, 0.0, 3.0), (3.60, 7.80, 2.40)):
            pu, pv, pd = E.plan_uv(f, p)
            if pd < 0.2 or not (-cv["ox"] / cv["fx"] <= pu <= (cv["W"] - cv["ox"]) / cv["fx"] and -cv["oy"] / cv["fy"] <= pv <= (cv["H"] - cv["oy"]) / cv["fy"]):
                continue                                   # only points that land on the canvas
            bu, bv_, bd = bs.proj(cam, p)
            cu, cv_ = (pu * cv["fx"] + cv["ox"]) / cv["W"], (pv * cv["fy"] + cv["oy"]) / cv["H"]
            dev = max(dev, abs(bu - cu) * cv["W"], abs(bv_ - cv_) * cv["H"], abs(bd - pd) * 1000)
        png = os.path.join(a.out, fid + ".png")
        os.makedirs(os.path.dirname(png), exist_ok=True)
        smp = a.station_samples if (fid.startswith("c1/") and fid[-2:] not in ("00", "11")) else a.samples
        depth, idx, normal = geometry_pass(tmp, cv["W"], cv["H"])
        render_wh(png, os.path.join(tmp, "p"), cv["W"], cv["H"], smp, 0.30, expo, passes=False)
        for nm in ("g", os.path.basename(fid)):
            q = os.path.join(W4.r4.EXR_DIR, nm + ".exr")
            if os.path.exists(q):
                os.remove(q)
        Image.open(png).save(png, optimize=True)
        rec = dict(frame=fid, camera=dict(loc=[round(x, 4) for x in f["loc"]], yaw=f["yaw"], lens=24, u0=f["u0"], v0=f["v0"], s_m=None if f["s"] is None else round(f["s"], 4)),
                   leaf=f["leaf"], canvas=cv, samples=smp, exposure=expo, camera_vs_plan_projection_max_px_or_mm=round(dev, 4), mean_L=fr.mean_L(png))
        rec.update(E.save_passes(fid, png, depth, idx, normal, f, cv, IM, a.out))
        rec["runtime_s"] = round(time.time() - t1)
        os.makedirs(os.path.join(SCRATCH, "frames"), exist_ok=True)
        json.dump(rec, open(os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json"), "w"), indent=1, ensure_ascii=False)
        print("FRAME", fid, rec["runtime_s"], "s  L", rec["mean_L"], " cam dev", rec["camera_vs_plan_projection_max_px_or_mm"], " not allowed", rec["not_allowed_px"], flush=True)
    for dst, src in alias.items():
        if src in want:
            for suf in (".png", "-depth.png", "-id.png", "-edges.png"):
                os.makedirs(os.path.dirname(os.path.join(a.out, dst)), exist_ok=True)
                shutil.copyfile(os.path.join(a.out, src + suf), os.path.join(a.out, dst + suf))
    shutil.rmtree(tmp, ignore_errors=True)
    print("DONE", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main(_ARGV)
