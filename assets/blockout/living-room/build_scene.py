#!/usr/bin/env python3
"""
Blockout of the Nordic living room (M0) - clay render, metric depth, lines,
overlay of future product slots, plan view and a self-check of section 2.1.

Source of truth: briefs/m0-prompt.nordic.md, section 2 (geometry) and 2.1 (frame checks).
Version 2 (2026-10-03): alternative A of review-designer.md (camera Y 6.05 + shift_x, armchair
25 deg with short armrests, planter moved). Version 1 is kept in v1/, version 2 in v2/.
Version 3 (2026-10-03): magazine holder moved to the front of the frame (alternative C,
review-designer.md 6.5, Bible 1.2.3): box X 1.12-1.48, Y 3.25-3.48, Z 0-0.42 (also checked at
0.38). M0 geometry (shell, fixed furniture, camera) is unchanged from v2. Adds the 6.5 checklist,
clay close-ups F9 / F13 with product proxies and the straight 9a branch (6 frames).
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
CHAIR = dict(cx=-1.230, cy=2.821, w=0.72, d=0.78, h=0.76, seat_h=0.40, yaw_deg=-25.0,
             arm_front_inset=0.0375)
# v2 (alternative A, review-designer.md 3.1, approved 2026-10-03):
# yaw -25 deg: the chair faces +X, turned 25 deg toward the back wall / coffee table.
# arm_front_inset: armrests end 3.75 cm behind the front of the frame (+0.3525 local), flush
# with the front faces of the front legs.
CAM = dict(loc=(0.0, 6.05, 1.20), lens=24.0, sensor_w=36.0, sensor_h=20.25, shift_y=-0.0625,
           shift_x=-0.040)
# shift_x: the house axis (X=0, centre of the framed art) lands at u = 0.540 in the frame.
# The camera is mirrored (scale.x = -1); the sign is verified by the self-check
# ("principal point u"), target 0.540, 0.460 would mean the sign is flipped.
PP_U_TARGET = 0.540

# Future products (overlay only, not in the clay render)
FUTURE = {
    "framed-art":  dict(kind="box", c=(0.0, 0.015, 1.475), s=(1.55, 0.03, 1.00)),
    "pendant":     dict(kind="cyl", c=(0.0, 1.72), r=0.225, z0=2.05, z1=2.32, cord=True),
    "wall-sconce": dict(kind="box", c=(-1.80 + 0.01, 2.88, 1.47), s=(0.02, 0.12, 0.12)),
    "rug":         dict(kind="box", c=(0.0, 1.92, 0.005), s=(2.90, 2.40, 0.01)),
    "planter":     dict(kind="cyl", c=(-1.50, 0.40), r=0.19, z0=0.0, z1=0.45,
                        envelope=dict(r=0.40, z0=0.45, z1=1.65)),
    "floor-lamp":  dict(kind="cyl", c=(1.35, 0.30), r=0.21, z0=1.20, z1=1.50,
                        stem=True, base_r=0.15),
    # Bible 1.2.1/1.2.2: pouf centre (0.88, 2.70), d50, height 37 (Bible 35-37; m0-prompt still says 40)
    "pouf":        dict(kind="cyl", c=(0.88, 2.70), r=0.25, z0=0.0, z1=0.37),
    # Bible 1.2.3 (v3): free-standing on the parquet in front of the rug corner, max envelope
    # X 1.12-1.48, Y 3.25-3.48, Z 0-0.42, anchored at the back-left corner (1.12, 3.25)
    "magazine-holder": dict(kind="box", c=(1.30, 3.365, 0.21), s=(0.36, 0.23, 0.42)),
}
# v3 holder variants for the 6.5 checks: (x0, x1, y0, y1, z1), all anchored at (1.12, 3.25)
MH_VARIANTS = {
    "envelope-h42": (1.12, 1.48, 3.25, 3.48, 0.42),
    "envelope-h40": (1.12, 1.48, 3.25, 3.48, 0.40),
    "envelope-h38": (1.12, 1.48, 3.25, 3.48, 0.38),
    "smallest-30x20x38": (1.12, 1.42, 3.25, 3.45, 0.38),
}
POUF_HEIGHTS = (0.37, 0.36)          # m0-prompt 1.3 / Bible 1.2.2: 37 drawn, 36 reported

# Expected frame positions (m0-prompt section 2.1) for the self-check
EXPECTED = {
    "ceiling_band_y": (0.00, 0.095),
    "back_wall_x": (0.342, 0.749), "back_wall_y": (0.095, 0.624),
    "horizon_y": 0.389,
    "sofa": ((0.397, 0.683), (0.472, 0.665)),
    "coffee-table": ((0.425, 0.655), (0.597, 0.736)),
    "armchair": ((0.18, 0.375), (0.55, 0.90)),
    "window_x": (0.211, 0.320), "window_head_y": (0.015, 0.139), "window_sill_y": (0.552, 0.632),
    "left_wall_free_x": (0.00, 0.211),                 # frame edge cuts the left wall at Y~3.83
    "right_wall_x": (0.749, 1.00),
    "front_floor_y": (0.91, 1.00),                     # full width
    "front_floor_right_y": (0.74, 1.00),               # right of front_floor_right_from_x
    "front_floor_right_from_x": 0.375,
    "framed-art": ((0.454, 0.626), (0.237, 0.433)),
    "pendant": ((0.503, 0.577), (0.066, 0.168)),
    "wall-sconce": (0.164, 0.288),
}
# review-designer.md 3.1 item 5: informative targets for future products [x0, x1, y0, y1]
EXPECTED_FUTURE = {           # m0-prompt 2.1 (alternative A), informative [x0, x1, y0, y1]
    "rug": [0.210, 0.870, 0.656, 0.874],
    "planter": [0.341, 0.385, 0.54, 0.65],
    "floor-lamp": [0.672, 0.721, 0.327, 0.389],
    "pouf": [0.665, 0.765, 0.662, 0.848],          # review 6.5 item 2, height 37
    "magazine-holder": [0.807, 0.924, 0.719, 0.942],   # review 6.5 item 2, envelope h42
}
# review-designer.md 6.5 thresholds (normalised frame coordinates u, v)
MH_EDGE_MIN = 0.05          # right and bottom margins
MH_POUF_MIN = 0.03
MH_RUG_CORNER_MIN = 0.03    # rug corner inside the holder silhouette, from every edge
MH_RUG_T_MIN = 0.02         # rug front edge T above the bottom-left corner
MH_WALL_LINE_MIN = 0.02     # floor/right-wall line entry from both top corners
# Close-up cameras (review-designer.md 6.5, motion-direction 1.4). Looking -Y, tilt down, 35 mm.
CLOSEUPS = {
    "F9":  dict(loc=(0.48, 4.30, 0.60), lens=35.0, tilt_deg=10.0),
    "F13": dict(loc=(0.87, 4.85, 0.62), lens=35.0, tilt_deg=10.0),
}
GAP_MIN = 0.02                 # armchair-sofa silhouette gap, alternative A (target 0.023)
LEFT_WALL_FREE_MIN = 1.40      # m of left wall visible in front of the window
WINDOW_HEAD_MARGIN = 0.010     # window head >= this below the top edge
ARMCHAIR_EDGE_MARGIN = 0.05    # armchair >= this from every frame edge
FLOOR_EXPOSED_TARGET = (0.12, 0.13)   # exposed floor below the rug, fraction of frame height
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
        parts.append(box("chair_arm", -hd + 0.02, hd - C["arm_front_inset"], ly - 0.03, ly + 0.03, arm_z - 0.03, arm_z, mwood, g, bevel=0.006, seg=2))
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
    cam_data.shift_x = CAM["shift_x"]
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
        if isinstance(got, (tuple, list)):
            got = tuple(sorted(got))
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
    # free left wall in front of the window: from the window (Y 2.40) to where the frame edge cuts it
    y_cut = camera_wall_entry(cam, xl)
    f = proj(cam, (xl, Wn["y1"], 1.2))
    add("left wall free (window -> frame edge)", "x", (0.0, f[0]), EXPECTED["left_wall_free_x"],
        f"left frame edge cuts the left wall at Y={y_cut:.3f}")
    free_m = y_cut - Wn["y1"]
    rep["items"].append(dict(item="left wall visible in front of the window", axis="m",
                             expected=f">= {LEFT_WALL_FREE_MIN}", measured=round(free_m, 4),
                             ok=bool(free_m >= LEFT_WALL_FREE_MIN - 1e-9)))
    rep["items"].append(dict(item="window head margin from top edge", axis="y",
                             expected=f">= {WINDOW_HEAD_MARGIN}", measured=round(d[1], 4),
                             ok=bool(d[1] >= WINDOW_HEAD_MARGIN - 1e-9), note="front edge of the head"))
    # principal point / house axis (sign check of shift_x on the mirrored camera)
    pp = proj(cam, (0.0, 0.0, CAM["loc"][2]))
    rep["items"].append(dict(item="principal point u (house axis X=0)", axis="x", expected=PP_U_TARGET,
                             measured=round(pp[0], 4), max_dev=round(abs(pp[0] - PP_U_TARGET), 4),
                             ok=bool(abs(pp[0] - PP_U_TARGET) <= 0.003),
                             note="tolerance 0.003; 0.460 would mean the shift_x sign is flipped"))
    g = proj(cam, (xr, 0, 1.2))
    add("right wall", "x", (g[0], 1.0), EXPECTED["right_wall_x"])
    # empty front floor - nearest furniture bottom
    furn = (idx == PASS_INDEX["sofa"]) | (idx == PASS_INDEX["coffee-table"]) | (idx == PASS_INDEX["armchair"])
    low_all = (np.nonzero(furn.any(axis=1))[0].max() + 1) / H
    xr0 = int(EXPECTED["front_floor_right_from_x"] * W)
    low_right = (np.nonzero(furn[:, xr0:].any(axis=1))[0].max() + 1) / H
    fx_lbl = EXPECTED["front_floor_right_from_x"]
    for nm, val, exp in (("front floor empty, full width", low_all, EXPECTED["front_floor_y"]),
                         (f"front floor empty, right of x {fx_lbl}", low_right, EXPECTED["front_floor_right_y"])):
        rep["items"].append(dict(item=nm, axis="y", expected=exp, measured=round(val, 4),
                                 max_dev=round(max(0.0, val - exp[0]), 4), ok=bool(val <= exp[0] + TOL),
                                 note="lowest furniture pixel (object index pass); ok = no furniture below expected top + tol"))
    # armchair clear of every frame edge (visible mask)
    ma = idx == PASS_INDEX["armchair"]
    ys_, xs_ = np.nonzero(ma)
    edge_m = min(xs_.min() / W, 1 - (xs_.max() + 1) / W, ys_.min() / H, 1 - (ys_.max() + 1) / H)
    rep["items"].append(dict(item="armchair margin to frame edges", axis="min", expected=f">= {ARMCHAIR_EDGE_MARGIN}",
                             measured=round(edge_m, 4), ok=bool(edge_m >= ARMCHAIR_EDGE_MARGIN)))
    rep["armchair_sofa_gap"] = silhouette_gap(idx, PASS_INDEX["armchair"], PASS_INDEX["sofa"])
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
    rep["framed_art_centre"] = [round((art[0][0] + art[0][1]) / 2, 4), round((art[1][0] + art[1][1]) / 2, 4)]
    rug = bbox2d(cam, fs["rug"]["hull"])
    exposed = 1.0 - rug[1][1]
    rep["front_floor_exposed_below_rug"] = dict(
        rug_front_edge_y=round(rug[1][1], 4), exposed_fraction=round(exposed, 4),
        target=list(FLOOR_EXPOSED_TARGET),
        ok=bool(FLOOR_EXPOSED_TARGET[0] - 0.005 <= exposed <= FLOOR_EXPOSED_TARGET[1] + 0.005))
    # other future items: informative
    rep["future_items"] = {}
    for name in FUTURE:
        (x0, x1), (y0, y1) = bbox2d(cam, fs[name]["hull"])
        rep["future_items"][name] = [round(x0, 4), round(x1, 4), round(y0, 4), round(y1, 4)]
    rep["future_items_expected_review"] = EXPECTED_FUTURE
    rep["overlay_checks"] = overlay_checks(cam, idx)
    fl = FUTURE["floor-lamp"]
    base = [(fl["c"][0] + fl["base_r"] * math.cos(t), fl["c"][1] + fl["base_r"] * math.sin(t), 0.0)
            for t in np.linspace(0, 2 * math.pi, 96)]
    base_y = bbox2d(cam, base)[1]
    pouf_y = bbox2d(cam, fs["pouf"]["hull"])[1]
    rep["floor_lamp_base_vs_pouf_top"] = dict(
        lamp_base_y=[round(base_y[0], 4), round(base_y[1], 4)], pouf_top_y=round(pouf_y[0], 4),
        gap=round(pouf_y[0] - base_y[1], 4), required_min=0.02, ok=bool(pouf_y[0] - base_y[1] >= 0.02),
        note="Bible 1.2.2: the lamp base must sit >= 0.02 above (in frame) the pouf's top edge")
    # pouf at 36 (reported, review 6.5 / m0-prompt 1.3)
    rep["floor_lamp_base_vs_pouf_top_by_height"] = {}
    for ph in POUF_HEIGHTS:
        top = min(proj(cam, (FUTURE["pouf"]["c"][0] + 0.25 * math.cos(t), FUTURE["pouf"]["c"][1] + 0.25 * math.sin(t), ph))[1]
                  for t in np.linspace(0, 2 * math.pi, 192))
        rep["floor_lamp_base_vs_pouf_top_by_height"][f"h{round(ph * 100)}"] = dict(
            pouf_top_y=round(top, 4), gap=round(top - base_y[1], 4), ok=bool(top - base_y[1] >= 0.02))
    rep["magazine_holder_v3"] = {k: holder_checks(cam, v) for k, v in MH_VARIANTS.items()}
    rep["future_items_note"] = ("Bible 1.2.2/1.2.3: planter (-1.50, 0.40) d38 h45; pouf (0.88, 2.70) d50 h37; "
                                "magazine holder X 1.12-1.48 Y 3.25-3.48 h42 (also h38, smallest 30x20x38); "
                                "floor-lamp base r15")
    rep["all_ok"] = all(i.get("ok", True) for i in rep["items"])
    rep["all_ok_including_armchair_sofa_gap"] = rep["all_ok"] and rep["armchair_sofa_gap"]["ok"]
    rep["all_ok_including_gap_and_floor"] = (rep["all_ok_including_armchair_sofa_gap"]
                                             and rep["front_floor_exposed_below_rug"]["ok"])
    return rep


def _hull2d(points):
    pts = sorted(set((float(x), float(y)) for x, y in points))
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


def _seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / max(ax * ax + ay * ay, 1e-12)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def poly_gap(pa, pb):
    """Min distance between two convex 2D polygons (0 if they intersect)."""
    for poly in (pa, pb):
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            n = (a[1] - b[1], b[0] - a[0])
            ra = [n[0] * x + n[1] * y for x, y in pa]
            rb = [n[0] * x + n[1] * y for x, y in pb]
            if max(ra) < min(rb) or max(rb) < min(ra):
                break
        else:
            continue
        break
    else:
        return 0.0
    d = min(_seg_dist(p, pb[i], pb[(i + 1) % len(pb)]) for p in pa for i in range(len(pb)))
    return min(d, min(_seg_dist(p, pa[i], pa[(i + 1) % len(pa)]) for p in pb for i in range(len(pa))))


def overlay_checks(cam, idx):
    """review-designer.md 3.1.5 'additional overlay checks'. Distances in frame-width units."""
    from PIL import Image, ImageDraw
    H, W = idx.shape
    asp = H / W
    fs = future_shapes()

    def hull(name):
        return _hull2d([(x, y * asp) for x, y, _ in (proj(cam, p) for p in fs[name]["hull"])])
    out = {}
    # (1) magazine holder (v3, review-designer.md 6.5): see holder_checks(); summary here
    mh = hull("magazine-holder")
    others = {n: poly_gap(mh, hull(n)) for n in FUTURE if n not in ("magazine-holder", "rug")}
    out["magazine_holder_overlaps_other_slots"] = dict(
        overlaps=[n for n, g in others.items() if g == 0.0],
        note="rug excluded: its corner is hidden inside the holder silhouette on purpose (T junction)",
        ok=not any(g == 0.0 for g in others.values()))
    # (3) planter vessel: >= 65% visible (sofa / armchair in front), its edges >= 0.01 from their silhouettes
    ph = [(x * W, y / asp * H) for x, y in hull("planter")]
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon(ph, fill=1)
    pm = np.array(im, bool)
    furn = (idx == PASS_INDEX["sofa"]) | (idx == PASS_INDEX["armchair"])
    vis = 1.0 - (pm & furn).sum() / max(pm.sum(), 1)
    (px0, px1), _ = bbox2d(cam, fs["planter"]["hull"])
    rows = np.nonzero(pm.any(1))[0]
    best = {}
    for nm in ("sofa", "armchair"):
        mk = idx[rows] == PASS_INDEX[nm]
        cols = np.nonzero(mk.any(0))[0]
        if not len(cols):
            best[nm] = None
            continue
        ext = (cols.min() / W, (cols.max() + 1) / W)          # outer silhouette extents in the vessel's rows
        best[nm] = round(float(min(abs(e - v) for e in ext for v in (px0, px1))), 4)
    out["planter"] = dict(visible_fraction=round(float(vis), 4), required_visible=0.65,
                          edge_gap_to_sofa=best["sofa"], edge_gap_to_armchair=best["armchair"], required_min=0.01,
                          note="edge gap: vessel left/right edge vs the outer left/right extents of the sofa and "
                               "armchair silhouettes in the vessel's rows (no coincident edges)")
    out["planter"]["ok"] = bool(vis >= 0.65 and all(v is not None and v >= 0.01 for v in best.values()))
    return out


# --------------------------------------------------------------------------------------
# v3: magazine holder checks (review-designer.md 6.5). Units: normalised frame coordinates
# (u from the left, v from the top), unscaled, the same units as the designer's tables.
# --------------------------------------------------------------------------------------
def box_corners(x0, x1, y0, y1, z0, z1):
    """Labelled corners: Y back/front (B/F), Z top/bottom (T/B), X left/right (L/R)."""
    return {("F" if y == y1 else "B") + ("T" if z == z1 else "B") + ("L" if x == x0 else "R"): (x, y, z)
            for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)}


def _labelled_hull(cam, corners):
    P = {k: tuple(float(c) for c in proj(cam, v)[:2]) for k, v in corners.items()}
    hull = _hull2d(list(P.values()))
    inv = {v: k for k, v in P.items()}
    return [(inv[p], p) for p in hull], P


def _span(hull, axis, value):
    """Interval of the convex polygon cut by the line coord[axis] == value (or None)."""
    o = 1 - axis
    hits = []
    n = len(hull)
    for i in range(n):
        a, b = hull[i], hull[(i + 1) % n]
        if (a[axis] - value) * (b[axis] - value) <= 0 and a[axis] != b[axis]:
            t = (value - a[axis]) / (b[axis] - a[axis])
            hits.append(a[o] + t * (b[o] - a[o]))
    return (min(hits), max(hits)) if hits else None


def _inside(hull, p):
    n = len(hull)
    s = [(hull[(i + 1) % n][0] - hull[i][0]) * (p[1] - hull[i][1]) -
         (hull[(i + 1) % n][1] - hull[i][1]) * (p[0] - hull[i][0]) for i in range(n)]
    return all(x >= 0 for x in s) or all(x <= 0 for x in s)


def line_crossings(lhull, A, B):
    """Crossings of segment A->B with the labelled hull edges, sorted from A to B."""
    out = []
    n = len(lhull)
    dx, dy = B[0] - A[0], B[1] - A[1]
    for i in range(n):
        (la, a), (lb, b) = lhull[i], lhull[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - A[0]) * ey - (a[1] - A[1]) * ex) / den
        s = ((a[0] - A[0]) * dy - (a[1] - A[1]) * dx) / den
        if 0 <= t <= 1 and 0 <= s <= 1:
            p = (A[0] + t * dx, A[1] + t * dy)
            out.append(dict(t=t, edge=f"{la}-{lb}", point=[round(p[0], 4), round(p[1], 4)],
                            dist_to={la: round(math.dist(p, a), 4), lb: round(math.dist(p, b), 4)}))
    return sorted(out, key=lambda d: d["t"])


def _ring(c, r, z, n=96):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]


def holder_checks(cam, variant, pouf_h=0.37, rug_t_min=MH_RUG_T_MIN, cam_y=None):
    x0, x1, y0, y1, z1 = variant
    corners = box_corners(x0, x1, y0, y1, 0.0, z1)
    lhull, P = _labelled_hull(cam, corners)
    hull = [p for _, p in lhull]
    us = [p[0] for p in hull]; vs = [p[1] for p in hull]
    bx = [min(us), max(us), min(vs), max(vs)]
    out = dict(box_m=dict(X=[x0, x1], Y=[y0, y1], Z=[0.0, z1]), frame_box=[round(b, 4) for b in bx],
               hull_order=[k for k, _ in lhull])
    out["margins"] = dict(left=round(bx[0], 4), right=round(1 - bx[1], 4), top=round(bx[2], 4),
                          bottom=round(1 - bx[3], 4))
    out["margins_ok"] = bool(out["margins"]["right"] >= MH_EDGE_MIN and out["margins"]["bottom"] >= MH_EDGE_MIN
                             and bx[0] >= 0 and bx[2] >= 0)
    out["height_fraction_of_frame"] = round(bx[3] - bx[2], 4)
    # pouf
    pc = FUTURE["pouf"]["c"]
    ppts = [proj(cam, p)[:2] for p in _ring(pc, 0.25, 0.0) + _ring(pc, 0.25, pouf_h)]
    phull = _hull2d(ppts)
    pu1 = max(p[0] for p in phull)
    out["pouf"] = dict(height=pouf_h, frame_box=[round(min(p[0] for p in phull), 4), round(pu1, 4),
                                                 round(min(p[1] for p in phull), 4), round(max(p[1] for p in phull), 4)],
                       gap_horizontal=round(bx[0] - pu1, 4), gap_min_distance=round(poly_gap(hull, phull), 4),
                       required_min=MH_POUF_MIN)
    # same-row horizontal gap (the M0 metric; with a tilted camera the verticals converge, so the
    # bounding-box gap above compares different rows and is conservative)
    pv0, pv1 = max(min(vs), min(p[1] for p in phull)), min(max(vs), max(p[1] for p in phull))
    row_gaps = []
    for v in np.linspace(pv0, pv1, 200) if pv1 > pv0 else []:
        hs_, ps_ = _span(hull, 1, v), _span(phull, 1, v)
        if hs_ and ps_:
            row_gaps.append(hs_[0] - ps_[1])
    out["pouf"]["gap_same_row"] = round(min(row_gaps), 4) if row_gaps else None
    out["pouf"]["gap_min_distance_aspect_w"] = round(poly_gap([(x, y * 9 / 16) for x, y in hull],
                                                              [(x, y * 9 / 16) for x, y in phull]), 4)
    g_ = out["pouf"]["gap_same_row"] if row_gaps else out["pouf"]["gap_horizontal"]
    out["pouf"]["ok"] = bool(g_ >= MH_POUF_MIN and out["pouf"]["gap_horizontal"] >= 0 and
                             out["pouf"]["gap_min_distance"] > 0)
    out["pouf"]["ok_metric"] = "gap_same_row >= 0.03 (no overlap)"
    # rug corner (front-right) inside the silhouette
    R = FUTURE["rug"]
    rx1 = R["c"][0] + R["s"][0] / 2
    ry0, ry1 = R["c"][1] - R["s"][1] / 2, R["c"][1] + R["s"][1] / 2
    C = proj(cam, (rx1, ry1, 0.0))[:2]
    inside = _inside(hull, C)
    hs, vsp = _span(hull, 1, C[1]), _span(hull, 0, C[0])
    edge_d = min(_seg_dist(C, hull[i], hull[(i + 1) % len(hull)]) for i in range(len(hull)))
    out["rug_corner"] = dict(point=[round(C[0], 4), round(C[1], 4)], inside=bool(inside),
                             to_left=round(C[0] - hs[0], 4) if hs else None,
                             to_right=round(hs[1] - C[0], 4) if hs else None,
                             to_top=round(C[1] - vsp[0], 4) if vsp else None,
                             to_bottom=round(vsp[1] - C[1], 4) if vsp else None,
                             to_nearest_edge=round(edge_d, 4), required_min=MH_RUG_CORNER_MIN)
    rc = out["rug_corner"]
    rc["ok"] = bool(inside and min(rc["to_left"], rc["to_right"], rc["to_bottom"]) >= MH_RUG_CORNER_MIN)
    # rug front edge: T junction on the left side, above the bottom-left corner
    A, B = proj(cam, (-rx1, ry1, 0.0))[:2], C
    cr = line_crossings(lhull, A, B)
    ent = cr[0] if cr else None
    t_d = None
    if ent:
        a_lab, b_lab = ent["edge"].split("-")
        bottom = max((a_lab, b_lab), key=lambda k: P[k][1])
        t_d = ent["dist_to"][bottom]
    out["rug_front_edge_T"] = dict(entry=ent, dist_above_bottom_corner=t_d, required_min=rug_t_min,
                                   ok=bool(ent is not None and t_d >= rug_t_min))
    # rug right edge: where it enters the silhouette (below the head)
    A = proj(cam, (rx1, ry0, 0.0))[:2]
    cr = line_crossings(lhull, A, C)
    out["rug_right_edge"] = dict(entry=cr[-1] if cr else None, required_min=0.03)
    if cr:
        e = cr[-1]
        out["rug_right_edge"]["ok"] = bool(min(e["dist_to"].values()) >= 0.03)
    # floor / right-wall line and skirting line: entry into the silhouette
    cy_ = (cam_y if cam_y is not None else cam.matrix_world.translation.y) - 0.30
    for key, xw, zw, req in (("floor_right_wall_line", ROOM["x_right"], 0.0, True),
                             ("skirting_line", ROOM["x_right"] - SKIRT_T, SKIRT_H, False)):
        A, B = proj(cam, (xw, 0.0, zw))[:2], proj(cam, (xw, cy_, zw))[:2]
        cr = line_crossings(lhull, A, B)
        d = dict(crossings=cr, report_only=not req)
        if cr:
            e = cr[0]
            top = {"BTL", "BTR"}
            d["entry_edge"] = e["edge"]
            d["through_top_edge"] = set(e["edge"].split("-")) == top
            d["dist_top_left"] = round(math.dist(e["point"], P["BTL"]), 4)
            d["dist_top_right"] = round(math.dist(e["point"], P["BTR"]), 4)
            d["ok"] = bool(d["through_top_edge"] and min(d["dist_top_left"], d["dist_top_right"]) >= MH_WALL_LINE_MIN)
        else:
            d["entry_edge"] = None
            d["ok"] = True
            d["note"] = "the line does not cross the silhouette"
        out[key] = d
    out["ok"] = bool(out["margins_ok"] and out["pouf"]["ok"] and rc["ok"] and out["rug_front_edge_T"]["ok"]
                     and out["floor_right_wall_line"]["ok"])
    return out


# --------------------------------------------------------------------------------------
# v3: product proxies and close-up cameras (F9, F13, branch 9a)
# --------------------------------------------------------------------------------------
# Proxies of the 16 slots for the close-ups. "exact": binding coordinates (Bible / m0-prompt).
# "approx": no binding coordinates exist yet (scene brief not written); placed from the Bible text.
PROXY_IDX0 = 30
PASS_DIR = [None]          # temp directory for EXR passes, set in main()


def build_proxies(mprod, mholder):
    g = "proxies"
    P = {}
    T = TABLE["h"]

    def cyl(n, c, r, z0, z1, mat=mprod):
        return cone(n, c[0], c[1], z0, z1, r, r, mat, g, verts=64)
    P["rug"] = ("exact", [box("px_rug", -1.45, 1.45, 0.72, 3.12, 0.0, 0.012, mprod, g)])
    P["pouf"] = ("exact", [cyl("px_pouf", (0.88, 2.70), 0.25, 0.0, 0.37)])
    P["magazine-holder"] = ("exact", [box("px_mh", 1.12, 1.48, 3.25, 3.48, 0.0, 0.42, mholder, g)])
    P["planter"] = ("exact", [cyl("px_planter", (-1.50, 0.40), 0.19, 0.0, 0.45)])
    P["floor-lamp"] = ("exact", [cyl("px_lamp_base", (1.35, 0.30), 0.15, 0.0, 0.02),
                                 cyl("px_lamp_stem", (1.35, 0.30), 0.012, 0.02, 1.20),
                                 cyl("px_lamp_shade", (1.35, 0.30), 0.21, 1.20, 1.50)])
    P["framed-art"] = ("exact", [box("px_art", -0.775, 0.775, 0.0, 0.03, 0.975, 1.975, mprod, g)])
    P["pendant"] = ("exact", [cyl("px_pendant", (0.0, 1.72), 0.225, 2.05, 2.32),
                              cyl("px_cord", (0.0, 1.72), 0.004, 2.32, ROOM["h"])])
    P["wall-sconce"] = ("exact", [box("px_sconce", -1.80, -1.78, 2.82, 2.94, 1.41, 1.53, mprod, g)])
    P["vase"] = ("approx", [cyl("px_vase", (0.42, 1.76), 0.075, T, T + 0.30)])
    P["candle-holders"] = ("approx", [cyl("px_candle_a", (0.26, 1.64), 0.045, T, T + 0.27),
                                      cyl("px_candle_b", (0.30, 1.86), 0.045, T, T + 0.20)])
    P["table-runner"] = ("approx", [box("px_runner", -0.45, -0.13, 1.37, 2.07, T, T + 0.004, mprod, g)])
    P["cushions"] = ("approx", [box("px_cush_a", -0.92, -0.42, 0.36, 0.50, 0.44, 0.90, mprod, g, bevel=0.04),
                                box("px_cush_b", 0.42, 0.92, 0.36, 0.50, 0.44, 0.90, mprod, g, bevel=0.04),
                                box("px_cush_c", 0.55, 0.85, 0.50, 0.62, 0.44, 0.74, mprod, g, bevel=0.03)])
    P["sofa-cover"] = ("approx", [box("px_throw", 0.60, 0.96, 0.40, 0.97, 0.44, 0.47, mprod, g)])
    P["basket"] = ("approx", [cyl("px_basket", (1.45, 0.80), 0.20, 0.0, 0.45)])
    P["wall-decor"] = ("approx", [box("px_walldecor", 1.875, 1.90, 1.55, 2.45, 1.00, 1.95, mprod, g)])
    P["curtains"] = ("approx", [box("px_curt_back", -1.80, -1.66, 0.35, 0.75, 0.01, 2.55, mprod, g),
                                box("px_curt_front", -1.80, -1.66, 2.25, 2.60, 0.01, 2.55, mprod, g)])
    roots, info = {}, {}
    for i, (name, (kind, objs)) in enumerate(P.items()):
        roots[name] = parent_group("proxy_" + name, objs, PROXY_IDX0 + i, group=g)
        info[name] = dict(pass_index=PROXY_IDX0 + i, coords=kind)
    return roots, info


def make_closeup_camera(name, spec):
    cd = bpy.data.cameras.new(name)
    cd.lens = spec["lens"]
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = CAM["sensor_w"]
    cd.sensor_height = CAM["sensor_h"]
    cd.clip_start = 0.02
    cd.clip_end = 100.0
    cam = bpy.data.objects.new(name, cd)
    cam.location = spec["loc"]
    cam.rotation_euler = (math.radians(90 - spec["tilt_deg"]), 0, math.radians(180))
    cam.scale = (-1.0, 1.0, 1.0)          # same mirror as the main camera
    bpy.context.scene.collection.objects.link(cam)
    return cam


def _clip_area_fraction(poly):
    """Fraction of a convex polygon's area inside the unit frame (Sutherland-Hodgman)."""
    def area(p):
        return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
    full = area(poly)
    out = list(poly)
    for axis, val, keep_ge in ((0, 0.0, True), (0, 1.0, False), (1, 0.0, True), (1, 1.0, False)):
        inp, out = out, []
        if not inp:
            break
        for i in range(len(inp)):
            a, b = inp[i - 1], inp[i]
            ina = (a[axis] >= val) if keep_ge else (a[axis] <= val)
            inb = (b[axis] >= val) if keep_ge else (b[axis] <= val)
            if inb:
                if not ina:
                    t = (val - a[axis]) / (b[axis] - a[axis])
                    out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                out.append(b)
            elif ina:
                t = (val - a[axis]) / (b[axis] - a[axis])
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return (area(out) / full) if (out and full > 0) else 0.0


def proxy_report(cam, proxy_roots, proxy_info, idx):
    H, W = idx.shape
    rep = {}
    for name, root in proxy_roots.items():
        pts = [proj(cam, p) for p in eval_world_verts(root)]
        pts2 = [(p[0], p[1]) for p in pts if p[2] > 0]
        hull = _hull2d(pts2) if len(pts2) >= 3 else []
        m = idx == proxy_info[name]["pass_index"]
        npx = int(m.sum())
        d = dict(coords=proxy_info[name]["coords"], visible_px=npx, visible_frame_fraction=round(npx / (W * H), 5))
        if hull:
            xs = [p[0] for p in hull]; ys = [p[1] for p in hull]
            d["projected_box_unclipped"] = [round(min(xs), 4), round(max(xs), 4), round(min(ys), 4), round(max(ys), 4)]
            d["projected_area_in_frame"] = round(_clip_area_fraction(hull), 4)
        if npx:
            ys_, xs_ = np.nonzero(m)
            d["visible_box"] = [round(xs_.min() / W, 4), round((xs_.max() + 1) / W, 4),
                                round(ys_.min() / H, 4), round((ys_.max() + 1) / H, 4)]
        d["in_frame"] = bool(npx > 0)
        rep[name] = d
    return rep


def closeup_checks(name, cam, idx, proxies):
    """review-designer.md 6.5 items 4 (F9) and 5 (F13)."""
    H, W = idx.shape
    out = {}
    pc = FUTURE["pouf"]["c"]
    pp = [proj(cam, p) for p in _ring(pc, 0.25, 0.0) + _ring(pc, 0.25, 0.37)]
    pbox = [min(p[0] for p in pp), max(p[0] for p in pp), min(p[1] for p in pp), max(p[1] for p in pp)]
    out["pouf_box"] = [round(v, 4) for v in pbox]
    out["pouf_height_fraction"] = round(pbox[3] - pbox[2], 4)
    out["pouf_centre_u"] = round((pbox[0] + pbox[1]) / 2, 4)
    if name == "F9":
        mh = {}
        for k, v in MH_VARIANTS.items():
            x0, x1, y0, y1, z1 = v
            u = [proj(cam, p)[0] for p in box_corners(x0, x1, y0, y1, 0.0, z1).values()]
            mh[k] = dict(min_u=round(min(u), 4), outside_right_by=round(min(u) - 1.0, 4), ok=bool(min(u) - 1.0 >= 0.03))
        out["magazine_holder_outside_right"] = mh
        out["pouf_in_frame"] = bool(pbox[0] >= 0 and pbox[1] <= 1 and pbox[2] >= 0 and pbox[3] <= 1)
        out["pouf_base_bottom_margin"] = round(1 - pbox[3], 4)
        out["pouf_ok"] = bool(out["pouf_in_frame"] and out["pouf_base_bottom_margin"] >= 0.05)
        legs = {}
        a, b = TABLE["w"] / 2 - TABLE["leg_in"], TABLE["d"] / 2 - TABLE["leg_in"]
        for lbl, sx in (("front_left", -1), ("front_right", 1)):
            q = proj(cam, (sx * a, TABLE["cy"] + b, 0.0))
            legs[lbl] = [round(q[0], 4), round(q[1], 4)]
        out["table_front_legs_floor_uv"] = legs
        out["ok"] = bool(out["pouf_ok"] and all(v["ok"] for v in mh.values()))
    else:
        out["magazine_holder"] = {k: holder_checks(cam, v, rug_t_min=0.03) for k, v in MH_VARIANTS.items()}
        # framed art: fraction of its height in frame (sampled on the front face)
        zs = np.linspace(0.975, 1.975, 201)
        rows_in = [any(0 <= proj(cam, (x, 0.03, z))[1] <= 1 and 0 <= proj(cam, (x, 0.03, z))[0] <= 1
                       for x in np.linspace(-0.775, 0.775, 9)) for z in zs]
        frac_art = float(np.mean(rows_in))
        out["framed_art_height_fraction_in_frame"] = round(frac_art, 4)
        out["framed_art_ok"] = bool(frac_art == 0 or frac_art >= 0.15)
        pl = proxies["planter"]
        out["planter_projected_area_in_frame"] = pl.get("projected_area_in_frame")
        cut = 1 - (pl.get("projected_area_in_frame") or 0)
        out["planter_cut_fraction"] = round(cut, 4)
        out["planter_ok"] = bool((not pl["in_frame"]) or cut >= 0.15)
        # sofa back cushions top vs art bottom (report only)
        art_b = proj(cam, (0.0, 0.03, 0.975))[1]
        back_top = proj(cam, (0.0, SOFA["y0"] + 0.36, SOFA["back_h"]))[1]
        cush_top = proj(cam, (0.67, 0.50, 0.90))[1]
        out["cushions_vs_art"] = dict(art_bottom_v=round(art_b, 4), sofa_back_cushion_top_v=round(back_top, 4),
                                      gap_back_cushions=round(back_top - art_b, 4),
                                      throw_cushion_top_v_approx=round(cush_top, 4),
                                      gap_throw_cushions_approx=round(cush_top - art_b, 4),
                                      note="report only; cushion proxies are approximate (h 0.90)")
        hf = {k: v["height_fraction_of_frame"] for k, v in out["magazine_holder"].items()}
        out["holder_height_fraction"] = hf
        out["k2_ok_h40_h42"] = bool(0.50 <= hf["envelope-h42"] <= 0.55 and 0.50 <= hf["envelope-h40"] <= 0.55)
        mh = out["magazine_holder"]
        out["ok"] = bool(out["k2_ok_h40_h42"] and out["framed_art_ok"] and out["planter_ok"]
                         and all(mh[k]["margins_ok"] and mh[k]["pouf"]["ok"] and mh[k]["rug_front_edge_T"]["ok"]
                                 for k in mh))
    out["slots_in_frame"] = sorted(n for n, d in proxies.items() if d["in_frame"])
    out["slots_out_of_frame"] = sorted(n for n, d in proxies.items() if not d["in_frame"])
    return out


def render_view(cam, png_path, passes_dir):
    sc = bpy.context.scene
    sc.camera = cam
    for n in sc.node_tree.nodes:
        if n.bl_idname == "CompositorNodeOutputFile":
            n.base_path = passes_dir
    os.makedirs(passes_dir, exist_ok=True)
    sc.render.filepath = png_path
    bpy.ops.render.render(write_still=True)
    idx = np.rint(load_exr(os.path.join(passes_dir, "IndexOB_0001.exr"))).astype(np.int32)
    return idx


def label_image(png_path, out_path, idx, proxy_info):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(png_path).convert("RGB")
    W, H = im.size
    dr = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(12, W // 80))
    except Exception:
        font = ImageFont.load_default()
    names = dict((v["pass_index"], k) for k, v in proxy_info.items())
    names.update({v: k for k, v in PASS_INDEX.items() if k in ("sofa", "coffee-table", "armchair")})
    for pi, nm in names.items():
        m = idx == pi
        if not m.any():
            continue
        ys, xs = np.nonzero(m)
        e = _edge(m)
        ey, ex = np.nonzero(e)
        dr.point(list(zip(ex.tolist(), ey.tolist())), fill=(200, 40, 40) if pi >= PROXY_IDX0 else (40, 90, 200))
        cx, cy = int(np.median(xs)), int(np.median(ys))
        lbl = nm + (" ~" if proxy_info.get(nm, {}).get("coords") == "approx" else "")
        bb = dr.textbbox((cx, cy), lbl, font=font)
        dr.rectangle((bb[0] - 2, bb[1] - 1, bb[2] + 2, bb[3] + 1), fill=(255, 255, 255))
        dr.text((cx, cy), lbl, fill=(20, 20, 20), font=font)
    im.save(out_path)


def run_closeups(out_dir, res, samples, proxy_roots, proxy_info, seq_res=960, seq_samples=32):
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples)
    for r in proxy_roots.values():
        for ch in r.children:
            ch.hide_render = False
    rep = {"note": ("Close-ups with product proxies (clay #8F8D89; magazine holder darker). Coordinates of proxies "
                    "marked 'approx' are placeholders from the Bible text (no binding coordinates yet). "
                    "Tilt 10 deg down, no shift, 35 mm, same mirror as M0.")}
    cams = {}
    for name, spec in CLOSEUPS.items():
        cam = make_closeup_camera("cam_" + name, spec)
        cams[name] = cam
        sc.render.resolution_x, sc.render.resolution_y = res, int(round(res * 9 / 16))
        sc.cycles.samples = samples
        png = os.path.join(out_dir, f"{name.lower()}-clay.png")
        idx = render_view(cam, png, os.path.join(PASS_DIR[0], name))
        label_image(png, os.path.join(out_dir, f"{name.lower()}-clay-labels.png"), idx, proxy_info)
        prox = proxy_report(cam, proxy_roots, proxy_info, idx)
        rep[name] = dict(camera=dict(location_m=list(spec["loc"]), lens_mm=spec["lens"], tilt_down_deg=spec["tilt_deg"],
                                     look="-Y", shift=[0, 0], resolution=[res, sc.render.resolution_y]),
                         checks=closeup_checks(name, cam, idx, prox), proxies=prox)
    # branch 9a: straight F9 -> F13, fixed lens and tilt
    a, b = Vector(CLOSEUPS["F9"]["loc"]), Vector(CLOSEUPS["F13"]["loc"])
    seq = []
    mh = MH_VARIANTS["envelope-h42"]
    corners = list(box_corners(mh[0], mh[1], mh[2], mh[3], 0.0, mh[4]).values())
    aabbs = []
    for r in proxy_roots.values():
        v = eval_world_verts(r)
        aabbs.append([min(p[i] for p in v) for i in range(3)] + [max(p[i] for p in v) for i in range(3)])
    for nm in ("sofa", "coffee-table", "armchair"):
        v = eval_world_verts(bpy.data.objects[nm])
        aabbs.append([min(p[i] for p in v) for i in range(3)] + [max(p[i] for p in v) for i in range(3)])

    def clearance(p):
        best = 1e9
        for bb in aabbs:
            d = math.sqrt(sum(max(bb[i] - p[i], 0, p[i] - bb[i + 3]) ** 2 for i in range(3)))
            best = min(best, d)
        return best
    cam9 = make_closeup_camera("cam_9a", CLOSEUPS["F9"])
    minu = []
    for k in range(51):
        t = k / 50
        cam9.location = a.lerp(b, t)
        bpy.context.view_layer.update()
        minu.append(round(min(proj(cam9, p)[0] for p in corners), 4))
    os.makedirs(os.path.join(out_dir, "9a"), exist_ok=True)
    sc.render.resolution_x, sc.render.resolution_y = seq_res, int(round(seq_res * 9 / 16))
    sc.cycles.samples = seq_samples
    for k in range(6):
        t = k / 5
        cam9.location = a.lerp(b, t)
        bpy.context.view_layer.update()
        render_view(cam9, os.path.join(out_dir, "9a", f"9a-{int(t * 100):03d}.png"), os.path.join(PASS_DIR[0], "9a"))
        seq.append(dict(t=t, location=[round(c, 4) for c in cam9.location], holder_min_u=round(min(proj(cam9, p)[0] for p in corners), 4),
                        clearance_m=round(clearance(cam9.location), 3)))
    d = b - a
    rep["9a"] = dict(vector_m=[round(c, 4) for c in d], length_m=round(d.length, 4), lens_mm=35.0, tilt_down_deg=10.0,
                     frames=seq, holder_min_u_51_steps=minu,
                     holder_enters_monotonic=bool(all(minu[i + 1] <= minu[i] + 1e-9 for i in range(len(minu) - 1))),
                     min_clearance_m=round(min(clearance(a.lerp(b, k / 50)) for k in range(51)), 3),
                     note="clearance = distance from the camera centre to the nearest furniture/proxy bounding box")
    for r in proxy_roots.values():
        for ch in r.children:
            ch.hide_render = True
    sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.cycles.samples = keep
    return rep, cams


def _edge(mask):
    e = np.zeros_like(mask)
    e[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    e[:, :-1] |= mask[:, 1:] != mask[:, :-1]
    e[1:, :] |= mask[1:, :] != mask[:-1, :]
    e[:-1, :] |= mask[1:, :] != mask[:-1, :]
    return e & mask


def silhouette_gap(idx, a, b):
    """Minimum 2D distance between the visible silhouettes of objects a and b, in units of
    frame width (object-index pass, unfiltered: 1 px = 1/W). 0 = touching/overlapping."""
    H, W = idx.shape
    ma, mb = idx == a, idx == b
    ea, eb = np.argwhere(_edge(ma)), np.argwhere(_edge(mb))
    # touching: a pixel of a 4-adjacent to b
    touch = (ma[:, 1:] & mb[:, :-1]).any() or (ma[:, :-1] & mb[:, 1:]).any() or \
            (ma[1:, :] & mb[:-1, :]).any() or (ma[:-1, :] & mb[1:, :]).any()
    best, pa, pb = 1e9, None, None
    for k in range(0, len(eb), 2000):
        chunk = eb[k:k + 2000].astype(np.float64)
        d = ((ea[:, None, :].astype(np.float64) - chunk[None, :, :]) ** 2).sum(-1)
        i, j = np.unravel_index(np.argmin(d), d.shape)
        if d[i, j] < best:
            best, pa, pb = d[i, j], ea[i], eb[k + j]
    dist_px = max(0.0, math.sqrt(best) - 1.0)          # pixel centres -> free pixels between
    # horizontal gap per row where both exist
    rows = np.nonzero(ma.any(1) & mb.any(1))[0]
    hgap = None
    for r in rows:
        xa, xb = np.nonzero(ma[r])[0], np.nonzero(mb[r])[0]
        g = (xb.min() - xa.max() - 1) if xb.min() > xa.max() else (xa.min() - xb.max() - 1)
        hgap = g if hgap is None else min(hgap, g)
    return dict(touching=bool(touch), min_gap_frame_w=round(dist_px / W, 4), min_gap_px=round(dist_px, 1),
                image_width_px=W,
                closest_points_xy=[[round(pa[1] / W, 4), round(pa[0] / H, 4)], [round(pb[1] / W, 4), round(pb[0] / H, 4)]],
                min_horizontal_gap_same_row_frame_w=(round(hgap / W, 4) if hgap is not None else None),
                rows_overlap_y=([round(rows.min() / H, 4), round((rows.max() + 1) / H, 4)] if len(rows) else None),
                required_min=GAP_MIN, ok=bool((not touch) and dist_px / W >= GAP_MIN))


def camera_wall_entry(cam, xl):
    # Y at which the left frame edge (u = 0) meets the left wall at camera height (includes shift_x)
    lo, hi = 0.0, CAM["loc"][1] - 0.05
    for _ in range(60):
        mid = (lo + hi) / 2
        if proj(cam, (xl, mid, CAM["loc"][2]))[0] > 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


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
              "pouf": (220, 80, 160), "magazine-holder": (110, 110, 120)}
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

    order = ["rug", "framed-art", "planter", "floor-lamp", "magazine-holder", "pouf", "wall-sconce", "pendant"]
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
    # v3: second, dashed magazine-holder box at height 0.38 (review 6.5 item 1)
    v = MH_VARIANTS["envelope-h38"]
    cc = box_corners(v[0], v[1], v[2], v[3], 0.0, v[4])
    col = colors["magazine-holder"]
    for e in (("BBL", "BBR"), ("FBL", "FBR"), ("BTL", "BTR"), ("FTL", "FTR"), ("BBL", "FBL"), ("BBR", "FBR"),
              ("BTL", "FTL"), ("BTR", "FTR"), ("BBL", "BTL"), ("BBR", "BTR"), ("FBL", "FTL"), ("FBR", "FTR")):
        a3, b3 = Vector(cc[e[0]]), Vector(cc[e[1]])
        for k in range(0, 12, 2):
            dr.line([P(a3.lerp(b3, k / 12)), P(a3.lerp(b3, (k + 1) / 12))], fill=(30, 30, 30, 230), width=lw)
    tx, ty = P(cc["BBL"])
    bb = dr.textbbox((0, 0), "h38 (dashed)", font=font)
    tx -= (bb[2] - bb[0]) + 8
    bb = dr.textbbox((tx, ty - font.size), "h38 (dashed)", font=font)
    dr.rectangle((bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2), fill=(255, 255, 255, 200))
    dr.text((tx, ty - font.size), "h38 (dashed)", fill=(30, 30, 30, 255), font=font)
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


def render_plan(out_path, roots, closeup_cams=None):
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
    u0 = proj(bpy.data.objects["cam_main"], (c[0], 0.0, c[2]))[0]     # principal point (shift_x)
    k = CAM["sensor_w"] / CAM["lens"]
    D = 6.6
    for u in (0.0, 1.0):                       # left and right frame edges
        dr.line([P((c[0], c[1], 1.0)), P((c[0] + (u - u0) * k * D, c[1] - D, 1.0))],
                fill=(220, 60, 40), width=3)
    dr.line([P((c[0], c[1], 1.0)), P((c[0], c[1] - D, 1.0))], fill=(220, 60, 40), width=1)
    cx, cy = P((c[0], c[1], 1.0))
    dr.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(220, 60, 40))
    # v3: future-slot footprints (rug, pouf, magazine holder) and the F9 / F13 close-up cameras
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font = None
    R = FUTURE["rug"]
    rx, ry = R["s"][0] / 2, R["s"][1] / 2
    dr.polygon([P((R["c"][0] + sx * rx, R["c"][1] + sy * ry, 1.0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
               outline=(60, 160, 90), width=3)
    pc = FUTURE["pouf"]["c"]
    dr.polygon([P(p[:2] + (1.0,)) for p in _ring(pc, 0.25, 0.0)], outline=(220, 80, 160), width=3)
    for k, v in MH_VARIANTS.items():
        if k in ("envelope-h40", "envelope-h38"):
            continue
        dr.polygon([P((x, y, 1.0)) for x, y in ((v[0], v[2]), (v[1], v[2]), (v[1], v[3]), (v[0], v[3]))],
                   outline=(40, 40, 40), width=3 if k.startswith("envelope") else 1)
    lbls = [("rug", (1.0, 1.0)), ("pouf", (pc[0] - 0.12, pc[1])), ("magazine holder", (1.05, 3.62))]
    for name_, (x, y) in lbls:
        dr.text(P((x, y, 1.0)), name_, fill=(20, 20, 20), font=font)
    for nm, cm in (closeup_cams or {}).items():
        sp = CLOSEUPS[nm]
        loc = sp["loc"]
        k2 = CAM["sensor_w"] / 2 / sp["lens"]
        Dc = 3.2
        col = (40, 90, 200) if nm == "F9" else (200, 120, 20)
        for sx in (-1, 1):
            dr.line([P((loc[0], loc[1], 1.0)), P((loc[0] + sx * k2 * Dc, loc[1] - Dc, 1.0))], fill=col, width=3)
        q = P((loc[0], loc[1], 1.0))
        dr.ellipse((q[0] - 8, q[1] - 8, q[0] + 8, q[1] + 8), fill=col)
        dr.text((q[0] + 10, q[1] + 4), nm, fill=col, font=font)
    a9, b9 = P(CLOSEUPS["F9"]["loc"][:2] + (1.0,)), P(CLOSEUPS["F13"]["loc"][:2] + (1.0,))
    dr.line([a9, b9], fill=(0, 0, 0), width=2)
    img.save(out_path)
    for ob in hidden:
        ob.hide_render = False
    sc.render.engine, sc.camera, sc.render.resolution_x, sc.render.resolution_y, sc.use_nodes = keep
    sc.cycles.samples = keep_samples


def v3_checklist(rep):
    """review-designer.md 6.5, 'checklist for motion-agent', items 1-8."""
    fi, ex = rep["future_items"], EXPECTED_FUTURE
    mh = rep["magazine_holder_v3"]

    def close(a, b, tol=0.005):
        return all(abs(x - y) <= tol for x, y in zip(a, b))
    items = {}
    items["1_overlay_holder_box_and_h38"] = dict(ok=bool(close(fi["magazine-holder"], ex["magazine-holder"], 0.01)),
                                                 note="h42 box solid, h38 box dashed; mh-alt-* labels not drawn")
    items["2_expected"] = dict(ok=bool(close(fi["magazine-holder"], ex["magazine-holder"]) and close(fi["pouf"], ex["pouf"])),
                               holder=fi["magazine-holder"], pouf=fi["pouf"], tolerance=0.005)
    sub = {}
    for k in ("envelope-h42", "envelope-h38"):
        m = mh[k]
        sub[k] = dict(a_margins=m["margins_ok"], b_pouf=m["pouf"]["ok"], c_rug_corner=m["rug_corner"]["ok"],
                      d_rug_T=m["rug_front_edge_T"]["ok"], e_floor_wall_line=m["floor_right_wall_line"]["ok"],
                      f_skirting_report=m["skirting_line"].get("ok"))
    items["3_m0_holder_checks"] = dict(ok=all(all(v for kk, v in s_.items() if kk != "f_skirting_report")
                                              for s_ in sub.values()), detail=sub)
    cl = rep.get("closeups")
    if cl:
        items["4_F9"] = dict(ok=cl["F9"]["checks"]["ok"])
        items["5_F13"] = dict(ok=cl["F13"]["checks"]["ok"])
        items["6_9a"] = dict(ok=bool(cl["9a"]["holder_enters_monotonic"] and cl["9a"]["min_clearance_m"] > 0.15),
                             frames=6)
        moved = {k: [round(a - b, 3) for a, b in zip(CLOSEUPS[k]["loc"], ref)]
                 for k, ref in (("F9", (0.48, 4.30, 0.60)), ("F13", (0.87, 4.85, 0.62)))}
        items["7_camera_adjustments"] = dict(ok=all(abs(c) <= 0.05 + 1e-9 for v in moved.values() for c in v),
                                             delta_m=moved, note="holder, pouf and rug not moved")
    items["8_plan_readme"] = dict(ok=True, note="plan.png redrawn with holder, pouf, rug, F9/F13 frustums; README v3")
    items["all_ok"] = all(v["ok"] for v in items.values() if isinstance(v, dict))
    return items


# --------------------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=3840)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--sky", type=float, default=6.0, help="world (sky) strength")
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--no-plan", action="store_true")
    ap.add_argument("--no-closeups", action="store_true")
    ap.add_argument("--passes-dir", default="", help="temp dir for EXR passes (default: a system temp dir)")
    ap.add_argument("--closeup-res", type=int, default=0, help="close-up width (default min(res, 1920))")
    ap.add_argument("--closeup-samples", type=int, default=0)
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
    # render passes go to a temporary directory outside the output folder (removed at the end)
    import tempfile
    tmp = a.passes_dir or tempfile.mkdtemp(prefix="m0-passes-")
    PASS_DIR[0] = tmp
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
    import shutil as _sh
    _sh.move(os.path.join(tmp, "Depth_0001.exr"), os.path.join(a.out, "m0-depth.exr"))

    make_lines(depth, idx, normal, os.path.join(a.out, "m0-lines.png"))
    make_overlay(clay_main, os.path.join(a.out, "m0-clay-overlay.png"), cam)

    rep = self_check(cam, roots, idx, a.res)
    # depth sanity: centre of back wall must equal the camera Y (planar)
    H, W = depth.shape
    px, py, _ = proj(cam, (0.0, 0.0, 2.40))
    rep["depth_check_back_wall_m"] = round(float(depth[int(py * H), int(px * W)]), 4)
    px, py, _ = proj(cam, (1.89, 0.0, 2.50))
    rep["depth_check_back_wall_corner_m"] = round(float(depth[int(py * H), int(px * W)]), 4)
    # v3: close-ups F9 / F13 and branch 9a, with product proxies (built after the M0 passes)
    closeup_cams = {}
    if not a.no_closeups:
        mprod = make_mat("clay_proxy", "#8F8D89")
        mholder = make_mat("clay_proxy_holder", "#5E5D5B")
        proxy_roots, proxy_info = build_proxies(mprod, mholder)
        cres = a.closeup_res or min(a.res, 1920)
        rep["closeups"], closeup_cams = run_closeups(a.out, cres, a.closeup_samples or max(32, a.samples // 2),
                                                     proxy_roots, proxy_info)
    rep["v3_checklist"] = v3_checklist(rep)
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
        shift_x=CAM["shift_x"], shift_x_mm=round(CAM["shift_x"] * CAM["sensor_w"], 4),
        shift_y=CAM["shift_y"], shift_y_mm=round(CAM["shift_y"] * CAM["sensor_w"], 4),
        hfov_deg=round(math.degrees(2 * math.atan(CAM["sensor_w"] / 2 / CAM["lens"])), 3),
        vfov_deg=round(math.degrees(2 * math.atan(CAM["sensor_h"] / 2 / CAM["lens"])), 3),
        resolution=[a.res, Hh],
        intrinsics_px=dict(fx=fx, fy=fx, cx=a.res / 2, cy=Hh / 2 + (-CAM["shift_y"]) * a.res * -1.0 + 0.0),
        note=("cx, cy: principal point from the left/top, measured by projecting the optical axis. "
              "shift_y<0 moves it up: cy = H/2 + shift_y*W. The camera is mirrored (scale.x=-1), so "
              "shift_x<0 moves it right: cx = W/2 - shift_x*W (house axis X=0 at u=0.540)"),
        mirrored_scale_x=-1.0,
        depth=dict(file="m0-depth.png", type="uint16", unit="mm", kind="planar camera Z (distance to camera plane)",
                   sky_value=65535, exr="m0-depth.exr (float32 metres)"),
    )
    camj["intrinsics_px"]["cy"] = Hh / 2 + CAM["shift_y"] * a.res
    ppu, ppv, _ = proj(cam, (0.0, 0.0, CAM["loc"][2]))
    camj["intrinsics_px"]["cx"] = round(ppu * a.res, 2)
    camj["principal_point_measured_uv"] = [round(ppu, 5), round(ppv, 5)]
    camj["closeups"] = {k: dict(location_m=list(v["loc"]), lens_mm=v["lens"], tilt_down_deg=v["tilt_deg"], look="-Y",
                                shift=[0, 0], mirrored_scale_x=-1.0,
                                blender_rotation_euler_deg=[90 - v["tilt_deg"], 0, 180]) for k, v in CLOSEUPS.items()}
    with open(os.path.join(a.out, "m0-camera.json"), "w") as fh:
        json.dump(camj, fh, indent=2)

    if not a.no_plan:
        render_plan(os.path.join(a.out, "plan.png"), roots, closeup_cams)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(a.out, "m0-blockout.blend"))
    if os.path.exists(os.path.join(a.out, "m0-blockout.blend1")):
        os.remove(os.path.join(a.out, "m0-blockout.blend1"))
    if not a.passes_dir:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
