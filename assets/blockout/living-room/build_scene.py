#!/usr/bin/env python3
"""
Blockout of the Nordic living room (M0) - clay render, metric depth, lines,
overlay of future product slots, plan view and a self-check of section 2.1.

Source of truth: briefs/m0-prompt.nordic.md, section 2 (geometry) and 2.1 (frame checks).
Axes (metres): origin on the floor where the room axis meets the back wall.
X to the right, Y from the back wall toward the camera, Z up.

Run:
    python3 build_scene.py                    # full: 3840x2160, all outputs
    python3 build_scene.py --res 960 --samples 32 --out /tmp/test   # quick preview
Requires: pip install bpy==4.2.0 (Python 3.11), numpy, pillow.
Deterministic: fixed Cycles seed, fixed sample count, CPU, no adaptive sampling.
"""
import argparse
import json
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------------------
# Geometry (m0-prompt section 2)
# --------------------------------------------------------------------------------------
ROOM = dict(x_left=-1.80, x_right=1.90, y_back=0.0, y_front=6.90, h=2.70)
DOOR = dict(x0=-0.45, x1=0.45, h=2.10)                       # in front wall
WINDOW = dict(y0=0.60, y1=2.40, z0=0.45, z1=2.35, mullion_y=1.50, mullion_w=0.06,
              frame_w=0.06, sill_proud=0.04)
SKIRT_H, SKIRT_T = 0.08, 0.012
WALL_T, LEFT_WALL_T = 0.15, 0.25
SOFA = dict(x0=-1.10, x1=1.10, y0=0.03, y1=0.95, back_h=0.78, seat_h=0.44, arm_h=0.60,
            arm_w=0.14, leg_h=0.15, leg_in=0.05, leg_d_top=0.04, leg_d_bot=0.025)
TABLE = dict(cx=0.0, cy=1.72, w=1.40, d=0.70, h=0.38, top_t=0.03, leg_d=0.05, leg_in=0.12,
             n=5.0)
CHAIR = dict(cx=-1.22, cy=2.90, w=0.72, d=0.78, h=0.76, seat_h=0.40, yaw_deg=-35.0)
# yaw -35 deg: the chair faces +X, turned 35 deg toward the back wall / coffee table.
CAM = dict(loc=(0.0, 6.40, 1.20), lens=24.0, sensor_w=36.0, sensor_h=20.25, shift_y=-0.080)

# Future products (overlay only, not in the clay render)
FUTURE = {
    "framed-art":  dict(kind="box", c=(0.0, 0.015, 1.475), s=(1.55, 0.03, 1.00)),
    "pendant":     dict(kind="cyl", c=(0.0, 1.72), r=0.225, z0=2.05, z1=2.32, cord=True),
    "wall-sconce": dict(kind="box", c=(-1.80 + 0.01, 2.88, 1.47), s=(0.02, 0.12, 0.12)),
    "rug":         dict(kind="box", c=(0.0, 1.92, 0.005), s=(2.90, 2.40, 0.01)),
    "planter":     dict(kind="cyl", c=(-1.45, 0.35), r=0.20, z0=0.0, z1=0.45,
                        envelope=dict(r=0.40, z0=0.45, z1=1.65)),
    "floor-lamp":  dict(kind="cyl", c=(1.35, 0.30), r=0.21, z0=1.20, z1=1.50,
                        stem=True, base_r=0.14),
    "pouf":        dict(kind="cyl", c=(0.95, 2.45), r=0.21, z0=0.0, z1=0.42),
}

# Expected frame positions (m0-prompt section 2.1) for the self-check
EXPECTED = {
    "ceiling_band_y": (0.00, 0.08),
    "back_wall_x": (0.31, 0.70), "back_wall_y": (0.08, 0.58),
    "horizon_y": 0.36,
    "sofa": ((0.36, 0.64), (0.44, 0.62)),
    "coffee-table": ((0.39, 0.61), (0.55, 0.69)),
    "armchair": ((0.17, 0.37), (0.50, 0.78)),
    "window_x": (0.20, 0.29), "window_head_y": (0.02, 0.12), "window_sill_y": (0.51, 0.58),
    "left_wall_free_x": (0.00, 0.20),
    "right_wall_x": (0.70, 1.00),
    "front_floor_y": (0.79, 1.00),
    "framed-art": ((0.42, 0.58), (0.21, 0.40)),
    "pendant": ((0.47, 0.53), (0.07, 0.14)),
    "wall-sconce": (0.16, 0.27),
}
TOL = 0.02

CLAY = "#BDBBB7"
FLOOR = "#A8A6A2"

PASS_INDEX = {"sofa": 1, "coffee-table": 2, "armchair": 3, "window": 4, "back-wall": 5,
              "left-wall": 6, "right-wall": 7, "floor": 8, "ceiling": 9, "front-wall": 10,
              "skirting": 11, "sill": 12}


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h):
    h = h.lstrip("#")
    return tuple(srgb_to_lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (1.0,)


def make_mat(name, hexcol, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_lin(hexcol)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    return m


COLL = {}


def coll(name):
    if name not in COLL:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLL[name] = c
    return COLL[name]


def box(name, x0, x1, y0, y1, z0, z1, mat, group, bevel=0.0, seg=3, pidx=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.scale = (x1 - x0, y1 - y0, z1 - z0)
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    ob.data.materials.append(mat)
    coll(group).objects.link(ob)
    if bevel > 0:
        bpy.context.view_layer.update()
        apply_scale(ob)
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = seg
        mod.limit_method = "NONE"
    ob.pass_index = pidx
    return ob


def apply_scale(ob):
    mw = Matrix.Diagonal(ob.scale.to_4d())
    ob.data.transform(mw)
    ob.scale = (1, 1, 1)


def cone(name, x, y, z0, z1, r_bot, r_top, mat, group, verts=32, pidx=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r_bot, radius2=r_top,
                          depth=z1 - z0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = (x, y, (z0 + z1) / 2)
    ob.data.materials.append(mat)
    coll(group).objects.link(ob)
    ob.pass_index = pidx
    return ob


def superellipse_slab(name, cx, cy, a, b, n, z0, z1, mat, group, segs=192, pidx=0):
    pts = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** (2.0 / n), c)
        y = b * math.copysign(abs(s) ** (2.0 / n), s)
        pts.append((x, y))
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = (cx, cy, 0)
    ob.data.materials.append(mat)
    coll(group).objects.link(ob)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width = 0.006
    mod.segments = 2
    mod.limit_method = "ANGLE"
    ob.pass_index = pidx
    return ob


def parent_group(name, objs, pidx, loc=(0, 0, 0), yaw_deg=0.0, group="furniture"):
    root = bpy.data.objects.new(name, None)
    coll(group).objects.link(root)
    for o in objs:
        o.parent = root
        o.pass_index = pidx
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(yaw_deg))
    return root


# --------------------------------------------------------------------------------------
# scene
# --------------------------------------------------------------------------------------
def build_shell(mclay, mfloor):
    R = ROOM
    xl, xr, yb, yf, h = R["x_left"], R["x_right"], R["y_back"], R["y_front"], R["h"]
    t = WALL_T
    g = "shell"
    # floor & ceiling (extend under walls)
    box("floor", xl - LEFT_WALL_T, xr + t, yb - t, yf + t, -0.10, 0.0, mfloor, g, pidx=PASS_INDEX["floor"])
    box("ceiling", xl - LEFT_WALL_T, xr + t, yb - t, yf + t, h, h + 0.15, mclay, g, pidx=PASS_INDEX["ceiling"])
    # back wall
    box("wall_back", xl - LEFT_WALL_T, xr + t, yb - t, yb, 0, h, mclay, g, pidx=PASS_INDEX["back-wall"])
    # right wall
    box("wall_right", xr, xr + t, yb, yf, 0, h, mclay, g, pidx=PASS_INDEX["right-wall"])
    # left wall with window opening
    W = WINDOW
    lx0, lx1 = xl - LEFT_WALL_T, xl
    pl = PASS_INDEX["left-wall"]
    box("wall_left_back", lx0, lx1, yb, W["y0"], 0, h, mclay, g, pidx=pl)
    box("wall_left_front", lx0, lx1, W["y1"], yf, 0, h, mclay, g, pidx=pl)
    box("wall_left_below", lx0, lx1, W["y0"], W["y1"], 0, W["z0"], mclay, g, pidx=pl)
    box("wall_left_above", lx0, lx1, W["y0"], W["y1"], W["z1"], h, mclay, g, pidx=pl)
    # front wall with door opening
    D = DOOR
    pf = PASS_INDEX["front-wall"]
    box("wall_front_left", xl - LEFT_WALL_T, D["x0"], yf, yf + t, 0, h, mclay, g, pidx=pf)
    box("wall_front_right", D["x1"], xr + t, yf, yf + t, 0, h, mclay, g, pidx=pf)
    box("wall_front_above", D["x0"], D["x1"], yf, yf + t, D["h"], h, mclay, g, pidx=pf)
    # closed vestibule behind the door so that no outside light enters except via the window
    vd = 1.20
    box("vest_floor", D["x0"] - 0.6, D["x1"] + 0.6, yf + t, yf + t + vd, -0.10, 0, mfloor, g, pidx=pf)
    box("vest_ceiling", D["x0"] - 0.6, D["x1"] + 0.6, yf + t, yf + t + vd, D["h"], D["h"] + 0.1, mclay, g, pidx=pf)
    box("vest_left", D["x0"] - 0.6, D["x0"] - 0.5, yf + t, yf + t + vd, 0, D["h"], mclay, g, pidx=pf)
    box("vest_right", D["x1"] + 0.5, D["x1"] + 0.6, yf + t, yf + t + vd, 0, D["h"], mclay, g, pidx=pf)
    box("vest_back", D["x0"] - 0.6, D["x1"] + 0.6, yf + t + vd, yf + t + vd + 0.1, 0, D["h"], mclay, g, pidx=pf)

    # skirting boards, 8 cm, wall colour
    ps = PASS_INDEX["skirting"]
    box("skirt_back", xl, xr, yb, yb + SKIRT_T, 0, SKIRT_H, mclay, g, pidx=ps)
    box("skirt_right", xr - SKIRT_T, xr, yb, yf, 0, SKIRT_H, mclay, g, pidx=ps)
    box("skirt_left", xl, xl + SKIRT_T, yb, yf, 0, SKIRT_H, mclay, g, pidx=ps)
    box("skirt_front_l", xl, D["x0"], yf - SKIRT_T, yf, 0, SKIRT_H, mclay, g, pidx=ps)
    box("skirt_front_r", D["x1"], xr, yf - SKIRT_T, yf, 0, SKIRT_H, mclay, g, pidx=ps)

    # window: frame 6 cm visible profile, mullion 6 cm at Y=1.50, two casements, inner sill
    pw = PASS_INDEX["window"]
    fw, fd = W["frame_w"], 0.07
    fx1 = xl - 0.08           # frame inner face, 8 cm reveal from the room
    fx0 = fx1 - fd
    y0, y1, z0, z1 = W["y0"], W["y1"], W["z0"], W["z1"]
    box("win_frame_bottom", fx0, fx1, y0, y1, z0, z0 + fw, mclay, "window", pidx=pw)
    box("win_frame_top", fx0, fx1, y0, y1, z1 - fw, z1, mclay, "window", pidx=pw)
    box("win_frame_back", fx0, fx1, y0, y0 + fw, z0, z1, mclay, "window", pidx=pw)
    box("win_frame_front", fx0, fx1, y1 - fw, y1, z0, z1, mclay, "window", pidx=pw)
    my = W["mullion_y"]
    box("win_mullion", fx0, fx1, my - W["mullion_w"] / 2, my + W["mullion_w"] / 2, z0, z1, mclay, "window", pidx=pw)
    # casement sashes (slim 2 cm step inside the frame so the two casements read)
    sx1, sx0 = fx1 - 0.015, fx1 - 0.055
    for k, (a, b) in enumerate(((y0 + fw, my - W["mullion_w"] / 2), (my + W["mullion_w"] / 2, y1 - fw))):
        s = 0.02
        box(f"win_sash{k}_b", sx0, sx1, a, b, z0 + fw, z0 + fw + s, mclay, "window", pidx=pw)
        box(f"win_sash{k}_t", sx0, sx1, a, b, z1 - fw - s, z1 - fw, mclay, "window", pidx=pw)
        box(f"win_sash{k}_l", sx0, sx1, a, a + s, z0 + fw, z1 - fw, mclay, "window", pidx=pw)
        box(f"win_sash{k}_r", sx0, sx1, b - s, b, z0 + fw, z1 - fw, mclay, "window", pidx=pw)
    # inner sill: top at 0.45, proud 4 cm from the wall, 5 cm ears past the opening
    box("win_sill", fx1, xl + W["sill_proud"], y0 - 0.05, y1 + 0.05, z0 - 0.025, z0, mclay, "window",
        pidx=PASS_INDEX["sill"])


def build_sofa(mclay, mwood):
    S = SOFA
    g = "furniture"
    parts = []
    x0, x1, y0, y1 = S["x0"], S["x1"], S["y0"], S["y1"]
    aw, lh = S["arm_w"], S["leg_h"]
    # legs: round, tapered 4 -> 2.5 cm, 15 cm visible, 5 cm in from the edges
    for lx in (x0 + S["leg_in"], x1 - S["leg_in"]):
        for ly in (y0 + S["leg_in"], y1 - S["leg_in"]):
            parts.append(cone("sofa_leg", lx, ly, 0.0, lh, S["leg_d_bot"] / 2, S["leg_d_top"] / 2, mwood, g))
    # track arms, 14 wide, 60 high, 3 cm radius
    parts.append(box("sofa_arm_L", x0, x0 + aw, y0, y1, lh, S["arm_h"], mclay, g, bevel=0.03))
    parts.append(box("sofa_arm_R", x1 - aw, x1, y0, y1, lh, S["arm_h"], mclay, g, bevel=0.03))
    ix0, ix1 = x0 + aw, x1 - aw
    # back frame and seat deck
    parts.append(box("sofa_backframe", ix0, ix1, y0, y0 + 0.16, lh, 0.62, mclay, g, bevel=0.02))
    parts.append(box("sofa_deck", ix0, ix1, y0 + 0.16, y1, lh, 0.30, mclay, g, bevel=0.015))
    # 3 seat cushions + 3 back cushions
    cw = (ix1 - ix0) / 3.0
    gap = 0.008
    for i in range(3):
        a = ix0 + i * cw + gap / 2
        b = ix0 + (i + 1) * cw - gap / 2
        parts.append(box(f"sofa_seat{i}", a, b, y0 + 0.36, y1, 0.30, S["seat_h"], mclay, g, bevel=0.035))
        parts.append(box(f"sofa_back{i}", a, b, y0 + 0.14, y0 + 0.36, S["seat_h"] - 0.02, S["back_h"],
                         mclay, g, bevel=0.045))
    return parent_group("sofa", parts, PASS_INDEX["sofa"])


def build_table(mwood):
    T = TABLE
    g = "furniture"
    a, b = T["w"] / 2, T["d"] / 2
    parts = [superellipse_slab("table_top", 0, 0, a, b, T["n"], T["h"] - T["top_t"], T["h"], mwood, g)]
    r = T["leg_d"] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cone("table_leg", sx * (a - T["leg_in"]), sy * (b - T["leg_in"]), 0.0,
                              T["h"] - T["top_t"], r, r, mwood, g))
    return parent_group("coffee-table", parts, PASS_INDEX["coffee-table"], loc=(T["cx"], T["cy"], 0))


def build_chair(mclay, mwood):
    C = CHAIR
    g = "furniture"
    hd, hw = C["d"] / 2, C["w"] / 2           # local: x = depth (front = +x), y = width
    parts = []
    lw = 0.045
    arm_z = 0.58
    # 4 legs up to the armrests
    for lx in (hd - 0.06, -hd + 0.06):
        for ly in (hw - 0.03, -hw + 0.03):
            parts.append(box("chair_leg", lx - lw / 2, lx + lw / 2, ly - lw / 2, ly + lw / 2, 0, arm_z - 0.03, mwood, g, bevel=0.005, seg=1))
    # flat 6 cm armrests
    for ly in (hw - 0.03, -hw + 0.03):
        parts.append(box("chair_arm", -hd + 0.02, hd, ly - 0.03, ly + 0.03, arm_z - 0.03, arm_z, mwood, g, bevel=0.006, seg=2))
        parts.append(box("chair_side_rail", -hd + 0.06, hd - 0.06, ly - 0.02, ly + 0.02, 0.20, 0.25, mwood, g))
    # seat rails
    for lx in (hd - 0.06, -hd + 0.06):
        parts.append(box("chair_seat_rail", lx - 0.02, lx + 0.02, -hw + 0.03, hw - 0.03, 0.22, 0.28, mwood, g))
    # seat cushion (top = 40 cm)
    parts.append(box("chair_seat", -hd + 0.18, hd - 0.02, -hw + 0.065, hw - 0.065, 0.27, C["seat_h"], mclay, g, bevel=0.03))
    # reclined back cushion (15 deg) and back posts; top ~ 76 cm
    tilt = math.radians(15)
    L, th = 0.41, 0.13
    bx, bz = -hd + 0.17, 0.34
    bc = box("chair_back", -th / 2, th / 2, -hw + 0.065, hw - 0.065, 0, L, mclay, g, bevel=0.035)
    _base_pivot(bc)
    bc.location = (bx, 0, bz)
    bc.rotation_euler = (0, -tilt, 0)      # top leans back (-x)
    parts.append(bc)
    for ly in (hw - 0.03, -hw + 0.03):
        p = box("chair_back_post", -0.02, 0.02, ly - 0.02, ly + 0.02, 0, 0.50, mwood, g)
        apply_scale(p)
        _base_pivot(p)
        p.location = (-hd + 0.06, ly, 0.26)
        p.rotation_euler = (0, -tilt, 0)
        parts.append(p)
    return parent_group("armchair", parts, PASS_INDEX["armchair"], loc=(C["cx"], C["cy"], 0), yaw_deg=C["yaw_deg"])


def _base_pivot(ob):
    """Move mesh so that the object's origin sits at the bottom-centre of the mesh."""
    me = ob.data
    zmin = min(v.co.z for v in me.vertices)
    for v in me.vertices:
        v.co.z -= zmin


def build_camera():
    cam_data = bpy.data.cameras.new("cam_main")
    cam_data.lens = CAM["lens"]
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.sensor_width = CAM["sensor_w"]
    cam_data.sensor_height = CAM["sensor_h"]
    cam_data.shift_x = 0.0
    cam_data.shift_y = CAM["shift_y"]
    cam_data.clip_start = 0.05
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("cam_main", cam_data)
    cam.location = CAM["loc"]
    cam.rotation_euler = (math.radians(90), 0, math.radians(180))   # level, looking -Y
    # The brief's axes (X right *as seen from the camera*, Y toward the camera, Z up) are
    # left-handed. Blender is right-handed, so a camera looking -Y would see +X on the left.
    # Mirroring the camera (scale x = -1) renders the brief's convention exactly: -X (window
    # wall) on the left of the frame. Geometry and lighting are untouched.
    cam.scale = (-1.0, 1.0, 1.0)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def build_world(strength):
    w = bpy.data.worlds.new("sky")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.92, 0.95, 1.0, 1.0)   # pale overcast sky, ~5500-6000K
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w


def setup_render(res_x, samples, exposure):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.seed = 7
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 6
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 0
    sc.cycles.sample_clamp_indirect = 10.0
    sc.render.resolution_x = res_x
    sc.render.resolution_y = int(round(res_x * 9 / 16))
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.threads_mode = "AUTO"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_object_index = True
    vl.use_pass_normal = True


def setup_compositor(tmpdir):
    sc = bpy.context.scene
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"], comp.inputs["Image"])
    fo = nt.nodes.new("CompositorNodeOutputFile")
    fo.base_path = tmpdir
    fo.format.file_format = "OPEN_EXR"
    fo.format.color_depth = "32"
    fo.format.exr_codec = "ZIP"
    fo.file_slots.clear()
    for name in ("Depth", "IndexOB", "Normal"):
        fo.file_slots.new(name + "_")
        nt.links.new(rl.outputs[name], fo.inputs[name + "_"])


def load_exr(path, channels=1):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    arr = arr.reshape(h, w, 4)[::-1]            # top row first
    bpy.data.images.remove(img)
    return arr[..., :channels] if channels > 1 else arr[..., 0]


# --------------------------------------------------------------------------------------
# projection / checks
# --------------------------------------------------------------------------------------
def proj(cam, p):
    v = world_to_camera_view(bpy.context.scene, cam, Vector(p))
    return (v.x, 1.0 - v.y, v.z)       # x from left, y from top, depth


def eval_world_verts(root):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ch in root.children_recursive:
        if ch.type != "MESH":
            continue
        ev = ch.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        pts.extend([mw @ v.co for v in me.vertices])
        ev.to_mesh_clear()
    return pts


def bbox2d(cam, pts):
    pp = [proj(cam, p) for p in pts]
    xs = [p[0] for p in pp]
    ys = [p[1] for p in pp]
    return (min(xs), max(xs)), (min(ys), max(ys))


def future_shapes():
    """Return {name: list of 3D polylines} for the overlay."""
    out = {}
    for name, f in FUTURE.items():
        lines = []
        if f["kind"] == "box":
            cx, cy, cz = f["c"]
            sx, sy, sz = f["s"]
            xs = (cx - sx / 2, cx + sx / 2)
            ys = (cy - sy / 2, cy + sy / 2)
            zs = (cz - sz / 2, cz + sz / 2)
            corners = [(x, y, z) for x in xs for y in ys for z in zs]
            edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
            for a, b in edges:
                lines.append([corners[a], corners[b]])
            out[name] = dict(lines=lines, hull=corners)
        else:
            cx, cy = f["c"]

            def ring(r, z, n=48):
                return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z) for i in range(n + 1)]
            r0 = ring(f["r"], f["z0"])
            r1 = ring(f["r"], f["z1"])
            lines += [r0, r1]
            for k in range(0, 48, 12):
                lines.append([r0[k], r1[k]])
            hull = r0 + r1
            extra = []
            if f.get("cord"):
                extra.append([(cx, cy, f["z1"]), (cx, cy, ROOM["h"])])
            if f.get("stem"):
                extra.append([(cx, cy, 0.0), (cx, cy, f["z0"])])
                extra += [ring(f["base_r"], 0.0)]
            if f.get("envelope"):
                e = f["envelope"]
                extra += [ring(e["r"], e["z0"]), ring(e["r"], e["z1"])]
                for k in range(0, 48, 12):
                    extra.append([ring(e["r"], e["z0"])[k], ring(e["r"], e["z1"])[k]])
            out[name] = dict(lines=lines, hull=hull, extra=extra)
    return out


def self_check(cam, roots, idx, res):
    H, W = idx.shape
    rep = {"tolerance": TOL, "items": []}

    def add(name, axis, got, exp, note=""):
        if isinstance(exp, (tuple, list)):
            dev = max(abs(got[0] - exp[0]), abs(got[1] - exp[1]))
        else:
            dev = abs(got - exp)
        rep["items"].append(dict(item=name, axis=axis, expected=exp,
                                 measured=[round(g, 4) for g in got] if isinstance(got, (tuple, list)) else round(got, 4),
                                 max_dev=round(dev, 4), ok=bool(dev <= TOL + 1e-9), note=note))

    R, Wn = ROOM, WINDOW
    xl, xr, h = R["x_left"], R["x_right"], R["h"]
    # back wall / ceiling band (analytic, pinhole)
    tl = proj(cam, (xl, 0, h)); br = proj(cam, (xr, 0, 0))
    add("back wall", "x", (tl[0], br[0]), EXPECTED["back_wall_x"])
    add("back wall", "y", (tl[1], br[1]), EXPECTED["back_wall_y"])
    add("ceiling band above back wall", "y", (0.0, tl[1]), EXPECTED["ceiling_band_y"])
    hz = proj(cam, (0, 0, CAM["loc"][2]))
    add("horizon (camera height)", "y", hz[1], EXPECTED["horizon_y"])
    # furniture - projected evaluated geometry and visible mask from the object-index pass
    for name in ("sofa", "coffee-table", "armchair"):
        (x0, x1), (y0, y1) = bbox2d(cam, eval_world_verts(roots[name]))
        exp = EXPECTED[name]
        add(name, "x", (x0, x1), exp[0], "geometry projection")
        add(name, "y", (y0, y1), exp[1], "geometry projection")
        m = idx == PASS_INDEX[name]
        if m.any():
            ys, xs = np.nonzero(m)
            rep["items"].append(dict(item=name, axis="mask", note="visible pixels (object index pass)",
                                     measured=[round(xs.min() / W, 4), round((xs.max() + 1) / W, 4),
                                               round(ys.min() / H, 4), round((ys.max() + 1) / H, 4)]))
    # window opening
    a = proj(cam, (xl, Wn["y0"], Wn["z0"])); b = proj(cam, (xl, Wn["y1"], Wn["z0"]))
    c = proj(cam, (xl, Wn["y0"], Wn["z1"])); d = proj(cam, (xl, Wn["y1"], Wn["z1"]))
    add("window opening", "x", (a[0], b[0]), EXPECTED["window_x"])
    add("window head", "y", (d[1], c[1]), EXPECTED["window_head_y"], "front edge -> back edge")
    add("window sill", "y", (a[1], b[1]), EXPECTED["window_sill_y"], "back edge -> front edge")
    # free left wall in front of the window, Y 2.40 - 4.00
    e = proj(cam, (xl, 4.00, 1.2)); f = proj(cam, (xl, Wn["y1"], 1.2))
    add("left wall free (Y 2.40-4.00)", "x", (max(0.0, e[0]), f[0]), EXPECTED["left_wall_free_x"],
        f"Y=4.00 projects to x={e[0]:.3f} (off-frame when <0); camera sees the left wall from Y={camera_wall_entry(cam, xl):.2f}")
    g = proj(cam, (xr, 0, 1.2))
    add("right wall", "x", (g[0], 1.0), EXPECTED["right_wall_x"])
    # empty front floor - nearest furniture bottom
    add("front floor empty", "y", (rep_floor_top(cam, roots), 1.0), EXPECTED["front_floor_y"],
        "top = lowest projected furniture point")
    # future products
    fs = future_shapes()
    for name in ("framed-art", "pendant"):
        (x0, x1), (y0, y1) = bbox2d(cam, fs[name]["hull"])
        add(name + " (overlay)", "x", (x0, x1), EXPECTED[name][0])
        add(name + " (overlay)", "y", (y0, y1), EXPECTED[name][1])
    sp = proj(cam, (-1.80, 2.88, 1.47))
    add("wall-sconce plate (overlay)", "x", sp[0], EXPECTED["wall-sconce"][0])
    add("wall-sconce plate (overlay)", "y", sp[1], EXPECTED["wall-sconce"][1])
    # pendant gap to picture
    pend = bbox2d(cam, fs["pendant"]["hull"])
    art = bbox2d(cam, fs["framed-art"]["hull"])
    rep["pendant_to_art_gap"] = round(art[1][0] - pend[1][1], 4)
    # other future items: informative
    rep["future_items"] = {}
    for name in FUTURE:
        (x0, x1), (y0, y1) = bbox2d(cam, fs[name]["hull"])
        rep["future_items"][name] = [round(x0, 4), round(x1, 4), round(y0, 4), round(y1, 4)]
    rep["all_ok"] = all(i.get("ok", True) for i in rep["items"])
    return rep


def camera_wall_entry(cam, xl):
    # Y at which the left frame edge meets the left wall (at camera height)
    half = (CAM["sensor_w"] / 2) / CAM["lens"]
    return CAM["loc"][1] - abs(xl) / half


def rep_floor_top(cam, roots):
    best = 0.0
    for r in roots.values():
        for p in eval_world_verts(r):
            best = max(best, proj(cam, p)[1])
    return best


# --------------------------------------------------------------------------------------
# image outputs
# --------------------------------------------------------------------------------------
def write_png16(path, arr16):
    from PIL import Image
    Image.fromarray(arr16.astype(np.uint16)).save(path)


def make_overlay(clay_path, out_path, cam):
    from PIL import Image, ImageDraw, ImageFont
    base = Image.open(clay_path).convert("RGBA")
    W, H = base.size
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    colors = {"framed-art": (230, 80, 60), "pendant": (240, 170, 30), "wall-sconce": (40, 160, 230),
              "rug": (60, 180, 90), "planter": (40, 140, 60), "floor-lamp": (170, 90, 220),
              "pouf": (220, 80, 160)}
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(14, W // 110))
    except Exception:
        font = ImageFont.load_default()
    lw = max(2, W // 900)
    fs = future_shapes()

    def P(p):
        x, y, _ = proj(cam, p)
        return (x * W, y * H)

    def hull2d(points):
        pts = sorted(set((round(x, 2), round(y, 2)) for x, y in points))
        if len(pts) < 3:
            return pts

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        lo, up = [], []
        for p in pts:
            while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
                lo.pop()
            lo.append(p)
        for p in reversed(pts):
            while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
                up.pop()
            up.append(p)
        return lo[:-1] + up[:-1]

    order = ["rug", "framed-art", "planter", "floor-lamp", "pouf", "wall-sconce", "pendant"]
    for name in order:
        col = colors[name]
        sh = fs[name]
        hull = hull2d([P(p) for p in sh["hull"]])
        dr.polygon(hull, fill=col + (60,))
        for line in sh["lines"]:
            dr.line([P(p) for p in line], fill=col + (235,), width=lw)
        for line in sh.get("extra", []):
            pts = [P(p) for p in line]
            for i in range(0, len(pts) - 1, 2):       # dashed
                dr.line([pts[i], pts[i + 1]], fill=col + (200,), width=max(1, lw - 1))
        xs = [p[0] for p in hull]; ys = [p[1] for p in hull]
        label = name
        tx, ty = min(xs), min(ys) - font.size - 4
        if name == "rug":
            tx, ty = max(xs) - font.size * 3, max(ys) + 4
        if name == "wall-sconce":
            tx, ty = max(xs) + 6, min(ys)
        bb = dr.textbbox((tx, ty), label, font=font)
        dr.rectangle((bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2), fill=(255, 255, 255, 200))
        dr.text((tx, ty), label, fill=col + (255,), font=font)
    # horizon
    hy = proj(cam, (0, 0, CAM["loc"][2]))[1] * H
    for x in range(0, W, 24):
        dr.line([(x, hy), (x + 12, hy)], fill=(0, 0, 0, 120), width=1)
    Image.alpha_composite(base, lay).convert("RGB").save(out_path)


def make_lines(depth, idx, normal, out_path):
    from PIL import Image
    d = np.where(np.isfinite(depth) & (depth < 1e4), depth, 50.0)
    edges = np.zeros(d.shape, bool)
    # object-id changes
    edges[:, 1:] |= idx[:, 1:] != idx[:, :-1]
    edges[1:, :] |= idx[1:, :] != idx[:-1, :]
    # depth discontinuities (relative)
    rel = 0.02
    edges[:, 1:] |= np.abs(d[:, 1:] - d[:, :-1]) > rel * np.minimum(d[:, 1:], d[:, :-1])
    edges[1:, :] |= np.abs(d[1:, :] - d[:-1, :]) > rel * np.minimum(d[1:, :], d[:-1, :])
    # normal creases
    n = normal / np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-6)
    edges[:, 1:] |= (n[:, 1:] * n[:, :-1]).sum(2) < 0.85
    edges[1:, :] |= (n[1:, :] * n[:-1, :]).sum(2) < 0.85
    img = np.where(edges, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(out_path)


def render_plan(out_path, roots):
    """Top-down orthographic plan (Workbench), ceiling hidden, camera + frustum drawn."""
    from PIL import Image, ImageDraw
    sc = bpy.context.scene
    keep = (sc.render.engine, sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.use_nodes)
    sc.use_nodes = False
    sc.render.engine = "CYCLES"          # Workbench/EEVEE need OpenGL/EGL (not available headless)
    keep_samples = sc.cycles.samples
    sc.cycles.samples = 32
    hidden = []
    for ob in bpy.data.objects:
        if ob.name.startswith(("ceiling", "vest_ceiling")):
            ob.hide_render = True
            hidden.append(ob)
    cd = bpy.data.cameras.new("cam_plan")
    cd.type = "ORTHO"
    cd.ortho_scale = 7.8
    cp = bpy.data.objects.new("cam_plan", cd)
    cp.location = (0.05, 3.45, 10.0)
    cp.rotation_euler = (0, 0, math.radians(180))   # back wall at the top, camera at the bottom
    cp.scale = (-1.0, 1.0, 1.0)                     # same mirror as the main camera: -X on the left
    sc.collection.objects.link(cp)
    sc.camera = cp
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1800
    sc.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    # draw camera position and horizontal FOV
    img = Image.open(out_path).convert("RGB")
    dr = ImageDraw.Draw(img)

    def P(p):
        x, y, _ = proj(cp, p)
        return (x * img.size[0], y * img.size[1])
    c = CAM["loc"]
    half = math.atan((CAM["sensor_w"] / 2) / CAM["lens"])
    L = 7.0
    for s in (-1, 1):
        dr.line([P((c[0], c[1], 1.0)), P((c[0] + s * L * math.sin(half), c[1] - L * math.cos(half), 1.0))],
                fill=(220, 60, 40), width=3)
    cx, cy = P((c[0], c[1], 1.0))
    dr.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(220, 60, 40))
    img.save(out_path)
    for ob in hidden:
        ob.hide_render = False
    sc.render.engine, sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.use_nodes = keep
    sc.cycles.samples = keep_samples


# --------------------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=3840)
    ap.add_argument("--samples", type=int, default=512)
    ap.add_argument("--sky", type=float, default=6.0, help="world (sky) strength")
    ap.add_argument("--exposure", type=float, default=0.0)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--no-plan", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mclay = make_mat("clay", CLAY)
    mfloor = make_mat("clay_floor", FLOOR)
    mwood = make_mat("clay_wood", CLAY)       # same clay; kept separate for later material swaps
    build_shell(mclay, mfloor)
    roots = {"sofa": build_sofa(mclay, mwood), "coffee-table": build_table(mwood),
             "armchair": build_chair(mclay, mwood)}
    cam = build_camera()
    build_world(a.sky)
    setup_render(a.res, a.samples, a.exposure)
    tmp = os.path.join(a.out, "_passes")
    os.makedirs(tmp, exist_ok=True)
    setup_compositor(tmp)
    bpy.context.view_layer.update()

    sc = bpy.context.scene
    sc.frame_set(1)
    tag = "-4k" if a.res >= 3840 else ""
    clay_main = os.path.join(a.out, f"m0-clay{tag}.png")
    sc.render.filepath = clay_main
    bpy.ops.render.render(write_still=True)

    depth = load_exr(os.path.join(tmp, "Depth_0001.exr"))
    idx = np.rint(load_exr(os.path.join(tmp, "IndexOB_0001.exr"))).astype(np.int32)
    normal = load_exr(os.path.join(tmp, "Normal_0001.exr"), channels=3)

    from PIL import Image
    if a.res >= 3840:
        # the >=2048 deliverable is a Lanczos downscale of the 4K render
        Image.open(clay_main).resize((2048, 1152), Image.LANCZOS).save(os.path.join(a.out, "m0-clay.png"))
    clay_ref = os.path.join(a.out, "m0-clay.png")

    # depth: planar camera Z in metres -> 16-bit millimetres (0 = camera plane, 65535 = sky)
    valid = np.isfinite(depth) & (depth < 1e3)
    mm = np.where(valid, np.clip(np.rint(depth * 1000.0), 0, 65534), 65535).astype(np.uint16)
    write_png16(os.path.join(a.out, "m0-depth.png"), mm)
    np.save(os.path.join(tmp, "depth_m.npy"), depth.astype(np.float32))
    # parallax-friendly view: near = bright, inverse depth normalised, 16-bit
    inv = np.where(valid, 1.0 / np.maximum(depth, 0.05), 0.0)
    near_bright = np.clip(inv / inv[valid].max(), 0, 1)
    write_png16(os.path.join(a.out, "m0-depth-nearbright.png"), np.rint(near_bright * 65535))
    # copy float EXR
    os.replace(os.path.join(tmp, "Depth_0001.exr"), os.path.join(a.out, "m0-depth.exr"))

    make_lines(depth, idx, normal, os.path.join(a.out, "m0-lines.png"))
    make_overlay(clay_main, os.path.join(a.out, "m0-clay-overlay.png"), cam)

    rep = self_check(cam, roots, idx, a.res)
    # depth sanity: centre of back wall must be 6.40 m (planar)
    H, W = depth.shape
    px, py, _ = proj(cam, (0.0, 0.0, 2.40))
    rep["depth_check_back_wall_m"] = round(float(depth[int(py * H), int(px * W)]), 4)
    px, py, _ = proj(cam, (1.89, 0.0, 2.50))
    rep["depth_check_back_wall_corner_m"] = round(float(depth[int(py * H), int(px * W)]), 4)
    with open(os.path.join(a.out, "m0-selfcheck.json"), "w") as fh:
        json.dump(rep, fh, indent=2, ensure_ascii=False)

    # camera json
    cd = cam.data
    fx = CAM["lens"] / CAM["sensor_w"] * a.res
    Hh = sc.render.resolution_y
    camj = dict(
        location_m=list(CAM["loc"]), look="-Y, level (tilt 0, roll 0)",
        blender_rotation_euler_deg=[90, 0, 180], lens_mm=CAM["lens"],
        sensor_mm=[CAM["sensor_w"], CAM["sensor_h"]], sensor_fit="HORIZONTAL",
        shift_x=0.0, shift_y=CAM["shift_y"], shift_y_mm=CAM["shift_y"] * CAM["sensor_w"],
        hfov_deg=round(math.degrees(2 * math.atan(CAM["sensor_w"] / 2 / CAM["lens"])), 3),
        vfov_deg=round(math.degrees(2 * math.atan(CAM["sensor_h"] / 2 / CAM["lens"])), 3),
        resolution=[a.res, Hh],
        intrinsics_px=dict(fx=fx, fy=fx, cx=a.res / 2, cy=Hh / 2 + (-CAM["shift_y"]) * a.res * -1.0 + 0.0),
        note="cy: principal point from the top; shift_y<0 moves the principal point up: cy = H/2 + shift_y*W",
        depth=dict(file="m0-depth.png", type="uint16", unit="mm", kind="planar camera Z (distance to camera plane)",
                   sky_value=65535, exr="m0-depth.exr (float32 metres)"),
    )
    camj["intrinsics_px"]["cy"] = Hh / 2 + CAM["shift_y"] * a.res
    with open(os.path.join(a.out, "m0-camera.json"), "w") as fh:
        json.dump(camj, fh, indent=2)

    if not a.no_plan:
        render_plan(os.path.join(a.out, "plan.png"), roots)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(a.out, "m0-blockout.blend"))
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
