#!/usr/bin/env python3
"""
clay_m0w.py: FB13 stage 0, the M0-W clay and light map of the warm-modern living room (render-agent, 2026-11-25). 0 var2 tokens.
Source: master-designer docs/proposals/wm-fb13-living-wow-2026-11-25.md 3.1-3.2 ("the last winter sun"); manager's task of 2026-11-25.
Nothing in docs/, data/ or site/ is edited: the camera is written as a proposal file next to the clay (camera-m0w-proposal.json).

The scene is framing_wm_door_final.py's house exactly (imported, not edited: the warm-modern living room of framing_wm_r4, the hall, the
court, the sky 7, the sun object, exposure 0.75, AgX), plus, here:
  a. CAMERA M0-W (proposal 3.1 Q1-b): 35 mm at (0.95, 5.55, 1.05), yaw 14 deg left, level, shift u0 0.50 / v0 0.52; the living-room tool's
     canvas (2720 x 1530, the 16:9 frame at base.png's frame box), so every M0-W asset drops into the tool's layer stack.
  b. SUN (3.1 Q1-a): D0's sun (azimuth 228 from north, clockwise; angle 1.5; 4000 K; strength 8) at altitude 15 (the proposal's "about 15",
     around 15:40), in the TOOL COMPASS the proposal asks for (3.4: "the living-room glazing faces west"): north = -Y, east = +X, south =
     +Y, west = -X (the house plan's compass is north = -X: in it the living glazing faces north and no sun can enter; see the README).
     A second sun map at D0's own altitude 21 is written for comparison.
  c. THE FIXED FURNITURE OF M0-W: the sofa on the same footprint (220 x 92 x 78, seat 44) with rounded arms and a soft back (Q1-c), on the
     Bible's recessed 6 cm walnut plinth; the armchair as r4 (WM-F1). The old fixed coffee table is gone (FB12: the table is a product).
  d. PRODUCT PROXIES at the card sizes, at the current default points (data/slots/living-room.json 1.9.4 by_style.warm-modern; the Olia
     table of FB12 at (0.30, 1.72); the basket of manifest-basket.json), each with its own pass index (800+), plus the fillers: the olive in
     the planter (taller crown, Z 1.15-1.95, so its shadow reaches the plaster), the two pillar candles. Only the planter (olive) and the
     basket are moved, by the solver below (the proposal: the olive's leaf shadow "between the left sconce and the art").
  e. THE LAMPS, ALL LIT, 2700 K: the travertine sconce pair washing the plaster up and down, the floor lamp (light out of the shade's open
     ends: the puddle on the right arm), the pendant (soft glow over the table), and the window-wall sconce (out of frame; its light on the
     armchair). Each lamp's light also as a separate map.
Passes and files (this folder): see README.md. Scratch (EXR, npz) goes to the scratchpad and is deleted at the end.

  python3 clay_m0w.py                       # everything (about 20 min on 4 cores)
  python3 clay_m0w.py --res 680 --samples 2 --quick      # a smoke test, writes to the scratchpad only
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
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 5))
HOUSE = os.path.join(REPO, "assets", "blockout", "house")
sys.path.insert(0, HOUSE)
_MY_ARGV = sys.argv[1:]
sys.argv = [sys.argv[0]]
SCR = os.environ.get("FB13_SCRATCH") or "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13/clay"
os.environ.setdefault("WM_ENTRANCE_SCRATCH", os.path.join(SCR, "wm-entrance"))

import framing_wm_door_final as FF  # noqa: E402  (the whole house, not edited)

import bmesh  # noqa: E402
import bpy  # noqa: E402
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

D, E, W4, fr, bs = FF.D, FF.E, FF.W4, FF.fr, FF.bs
FF.SCRATCH = E.SCRATCH = D.SCRATCH = SCR

# ---- the proposal's numbers -----------------------------------------------------------------------------------------------------
CAM = dict(id="M0-W", loc=[0.95, 5.55, 1.05], yaw=14.0, lens=35.0, u0=0.50, v0=0.52)
SUN = dict(az=228.0, alt=15.0, alt_d0=21.0, angle=1.5, kelvin=4000, strength=8.0)
TOOL_COMPASS = dict(north=[0, -1, 0], east=[1, 0, 0], south=[0, 1, 0], west=[-1, 0, 0],
                    note="proposal 3.4: the living-room glazing (outward normal -X) faces west; the house plan has north = -X")
CANVAS, FRAME_BOX = E.CANVAS, E.FRAME_BOX               # (2720, 1530); the 16:9 frame of base.png
K_U, K_V = CAM["lens"] / 36.0, CAM["lens"] / 36.0 * 16.0 / 9.0
TABLE_TOP = 0.38
OLIA = dict(c=(0.30, 1.72), w=1.20, d=0.65, h=0.38, top=0.04, end=0.04)
SOFA = dict(x=(-0.90, 1.30), y=(0.03, 0.95), h=0.78, seat=0.44, arm_w=0.28, arm_h=0.62, back_d=0.27, plinth=0.06, inset=0.04,
            arm_round=0.12, back_round=0.08)
OLIVE = dict(crown_z=(1.15, 1.95), r=0.32, trunk_r=0.025, leaf=(0.05, 0.012), clusters=34, per_cluster=60, cluster_r=0.10, seed=1540)
# the leaf shadow's target on the back wall: horizontally between the left sconce (X -0.85) and the triptych's left edge (X -0.61)
SHADOW_TARGET_X = -0.73
OLIVE_T = 0.85                                          # metres of sun path from the wall to the crown centre (see solve_olive)
BASKET_CANDIDATES = [(-2.00, 0.30), (-2.02, 0.34), (-1.98, 0.36), (-1.90, 0.30), (-1.85, 0.32), (-1.20, 0.30), (-1.50, 0.30)]
LAMP_K = 2700
PROD_IDX = {"rug": 801, "curtains": 802, "vase": 803, "planter": 804, "basket": 805, "magazine-holder": 806, "floor-lamp": 807,
            "framed-art": 808, "accent-sconces": 809, "pendant": 810, "bowl": 811, "candle-holders": 812, "coffee-table": 813,
            "cushion-left": 814, "cushion-right": 815, "cushion-lumbar": 816, "throw": 817, "wall-sconce": 818}
FILLER_IDX = {"olive (filler)": 830, "candles (filler)": 831, "branch (filler)": 832, "pendant cord": 833}
SOFA_IDX, ARMCHAIR_IDX = 1, 3
LAMPS = {}                                              # slot -> dict(lights=[...], glow=[materials])
OBJS = {}                                               # key -> [objects]
CARD = {"rug": "rug-cj-braided-wool-natural 230 x 330", "curtains": "curtains-aliexpress-linen-blend-s-fold-180502 132 x 270 (sold length)",
        "vase": "vase-cj-textured-white-stoneware large D16 x H32", "planter": "planter-cj-cement-ribbed-belly large D42 x H35.5",
        "basket": "basket-cj-jute-rope-cylinder large D35 x H39", "magazine-holder": "magazine-holder-cj-gunmetal-leather-strap small 35 x 19 x 27.5",
        "floor-lamp": "floor-lamp-cj-pleated-walnut-stem-158 (base 26, shade 37 x 23, H 158)",
        "framed-art": "framed-art-aliexpress-frameless-minimalist-wall-art-631735 3 x 50 x 70",
        "accent-sconces": "accent-sconces-aliexpress-travertine-cylinder-walnut-choice D6.5 x H16, a pair",
        "pendant": "pendant-cj-tiered-fabric-drum D50 (height not stated: 28)", "bowl": "bowl-cj-matte-black-bowl-20 D20 x H8",
        "candle-holders": "candle-holders-cj-travertine-pedestal 7 x 11, a pair", "coffee-table": "coffee-table-idana-javorina-olia-natural 120 x 65 x 38",
        "cushion-left": "set B (approximate box 45 x 45)", "cushion-right": "set B (approximate box 50 x 50)",
        "cushion-lumbar": "set B (approximate box 50 x 30)", "throw": "set B throw Pecan (approximate drape)",
        "wall-sconce": "wall-sconce, window wall plate (-2.30, 3.17, 1.47) (out of frame; light only)"}


def mat(name, hexcol, rough=0.9):
    return fr.mat_cache("m0w_" + name, hexcol, rough)


def reg(key, obs):
    OBJS.setdefault(key, []).extend(obs)
    return obs


def box(key, x0, x1, y0, y1, z0, z1, m, pidx, bevel=0.0):
    ob = bs.box(f"m0w_{key}_{len(OBJS.get(key, []))}", x0, x1, y0, y1, z0, z1, m, "framing", bevel=bevel, seg=4, pidx=pidx)
    return reg(key, [ob])[0]


def cyl(key, cx, cy, r0, z0, z1, m, pidx, r1=None, verts=48, caps=True):
    me = bpy.data.meshes.new(f"m0w_{key}")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=verts, radius1=r0, radius2=r0 if r1 is None else r1, depth=z1 - z0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"m0w_{key}_{len(OBJS.get(key, []))}", me)
    ob.location = (cx, cy, (z0 + z1) / 2)
    ob.data.materials.append(m)
    bs.coll("framing").objects.link(ob)
    ob.pass_index = pidx
    for p in me.polygons:
        p.use_smooth = True
    return reg(key, [ob])[0]


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------------------
def tool_sun_vector(az, alt):
    """Unit vector toward the sun in the TOOL compass (north = -Y, east = +X)."""
    a, h = math.radians(az), math.radians(alt)
    n, e = Vector(TOOL_COMPASS["north"]), Vector(TOOL_COMPASS["east"])
    hz = n * math.cos(a) + e * math.sin(a)
    return Vector((hz.x * math.cos(h), hz.y * math.cos(h), math.sin(h)))


def house_sun_vector(az, alt):
    return FF.sun_vector(az, alt)


def plan_uv(X, Y, Z):
    """the house plan's projection (conventions.projection) at M0-W: frame u, v and the planar depth d (numpy arrays welcome)"""
    y = math.radians(CAM["yaw"])
    fw, rt = (-math.sin(y), -math.cos(y)), (math.cos(y), -math.sin(y))
    dx, dy = np.asarray(X, float) - CAM["loc"][0], np.asarray(Y, float) - CAM["loc"][1]
    d = fw[0] * dx + fw[1] * dy
    x = rt[0] * dx + rt[1] * dy
    return CAM["u0"] + K_U * x / d, CAM["v0"] + K_V * (CAM["loc"][2] - np.asarray(Z, float)) / d, d


def solve_olive(t=OLIVE_T, alt=SUN["alt"]):
    """The crown centre on the sun ray through the shadow target: C = T + t s (s toward the sun). The crown height is fixed by the tree
    (OLIVE crown_z), so the shadow's height on the wall follows from t: Z_T = C_z - t s_z."""
    s = tool_sun_vector(SUN["az"], alt)
    cz = sum(OLIVE["crown_z"]) / 2
    cx, cy = SHADOW_TARGET_X + t * s.x, 0.0 + t * s.y
    return dict(crown_centre=[round(cx, 3), round(cy, 3), round(cz, 3)], shadow_centre_on_wall=[SHADOW_TARGET_X, 0.0, round(cz - t * s.z, 3)],
                sun_path_m=t, toward_sun=[round(v, 4) for v in s])


def shadow_of(p, alt):
    """where the point p's shadow falls on the back wall Y = 0 (or the floor when it reaches it first)"""
    s = tool_sun_vector(SUN["az"], alt)
    t = p[1] / s.y if s.y > 0 else 1e9
    q = [p[0] - t * s.x, 0.0, p[2] - t * s.z]
    if q[2] < 0:
        t = p[2] / s.z
        q = [p[0] - t * s.x, p[1] - t * s.y, 0.0]
    return [round(v, 3) for v in q]


# ---------------------------------------------------------------------------------------------------------------
# the living room of M0-W
# ---------------------------------------------------------------------------------------------------------------
def sofa_m0w():
    """Q1-c: the same footprint, arms rounded (bevel r 0.12 on a 28 cm arm: as round as the arm allows; the proposal's 'r 18-20' read as the
    arm's plan-and-top rounding), a soft back (bevel 0.08), on the Bible's recessed walnut plinth 6 cm (inset 4 cm). Pass index 1."""
    hid = []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.pass_index == SOFA_IDX and not ob.hide_render:
            ob.hide_render = True
            hid.append(ob.name)
    S = SOFA
    boucle, walnut = mat("boucle_griege", "#CDC2B3", 0.95), mat("walnut", "#6B4A33", 0.85)
    (x0, x1), (y0, y1) = S["x"], S["y"]
    p, i = S["plinth"], S["inset"]
    box("sofa", x0 + i, x1 - i, y0 + i, y1 - i, 0.0, p, walnut, SOFA_IDX)
    box("sofa", x0 + S["arm_w"] - 0.02, x1 - S["arm_w"] + 0.02, y0 + S["back_d"] - 0.02, y1, p, S["seat"], boucle, SOFA_IDX, bevel=0.035)
    box("sofa", x0 + 0.02, x1 - 0.02, y0, y0 + S["back_d"], p, S["h"], boucle, SOFA_IDX, bevel=S["back_round"])
    box("sofa", x0, x0 + S["arm_w"], y0, y1, p, S["arm_h"], boucle, SOFA_IDX, bevel=S["arm_round"])
    box("sofa", x1 - S["arm_w"], x1, y0, y1, p, S["arm_h"], boucle, SOFA_IDX, bevel=S["arm_round"])
    return [f"sofa M0-W (Q1-c): X {S['x']}, Y {S['y']}, H {S['h']}, seat {S['seat']}; arms {S['arm_w']} wide to {S['arm_h']}, rounded "
            f"r {S['arm_round']}; back {S['back_d']} deep, rounded r {S['back_round']}; walnut plinth {S['plinth']} inset {S['inset']}; "
            f"hid the r4 / Bible sofa ({len(hid)} objects)"]


def olia():
    hid = []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.pass_index == 2 and not ob.hide_render:
            ob.hide_render = True
            hid.append(ob.name)
    O = OLIA
    oak = mat("oak_natural", "#C8A27A", 0.7)
    cx, cy = O["c"]
    x0, x1, y0, y1 = cx - O["w"] / 2, cx + O["w"] / 2, cy - O["d"] / 2, cy + O["d"] / 2
    pi = PROD_IDX["coffee-table"]
    box("coffee-table", x0, x1, y0, y1, O["h"] - O["top"], O["h"], oak, pi, bevel=0.006)
    box("coffee-table", x0, x0 + O["end"], y0, y1, 0.0, O["h"] - O["top"] + 0.002, oak, pi, bevel=0.004)
    box("coffee-table", x1 - O["end"], x1, y0, y1, 0.0, O["h"] - O["top"] + 0.002, oak, pi, bevel=0.004)
    return [f"coffee table: Olia 120 x 65 x 38 (FB12) at {O['c']}, waterfall ends 4 cm, top 4 cm (the card: top and leg not stated); hid the "
            f"fixed table ({len(hid)} objects)"]


def olive_crown(c, key="olive (filler)"):
    import random
    O = OLIVE
    rnd = random.Random(O["seed"])
    cx, cy = c
    z0, z1 = O["crown_z"]
    zc, rz, R = (z0 + z1) / 2, (z1 - z0) / 2, O["r"]
    lw, ww = O["leaf"]
    verts, faces, centres = [], [], []
    while len(centres) < O["clusters"]:
        p = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if p.length <= 1.0:
            centres.append(Vector((cx + p.x * (R - O["cluster_r"]), cy + p.y * (R - O["cluster_r"]), zc + p.z * (rz - O["cluster_r"]))))
    import mathutils
    for c0 in centres:
        for _ in range(O["per_cluster"]):
            q = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * (abs(rnd.gauss(0, 0.5)) * O["cluster_r"])
            p = c0 + q
            a = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6))).normalized()
            n = a.orthogonal().normalized()
            n.rotate(mathutils.Quaternion(a, rnd.uniform(0, math.pi)))
            s = a.cross(n).normalized()
            L_, W_ = lw * rnd.uniform(0.8, 1.2), ww * rnd.uniform(0.8, 1.2)
            b = len(verts)
            verts += [tuple(p - a * L_ / 2 - s * W_ / 2), tuple(p + a * L_ / 2 - s * W_ / 2), tuple(p + a * L_ / 2 + s * W_ / 2),
                      tuple(p - a * L_ / 2 + s * W_ / 2)]
            faces.append((b, b + 1, b + 2, b + 3))
    me = bpy.data.meshes.new("m0w_olive_crown")
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new("m0w_olive_crown", me)
    bs.coll("framing").objects.link(ob)
    ob.data.materials.append(mat("olive_leaf", "#5E6B4E", 0.9))
    ob.pass_index = FILLER_IDX[key]
    reg(key, [ob])
    # a few branches from the trunk top into the crown
    bark = mat("olive_bark", "#6E665A", 0.95)
    tr = cyl(key, cx, cy, OLIVE["trunk_r"], 0.355, z0 + 0.15, bark, FILLER_IDX[key], r1=OLIVE["trunk_r"] * 0.8, verts=16)
    return len(faces), tr


def products(planter_c, basket_c):
    notes = []
    P = PROD_IDX
    lin, tra, wal = mat("linen", "#E3DACB"), mat("travertine", "#D8C8AE", 0.8), mat("walnut", "#6B4A33", 0.85)
    box("rug", -1.45, 1.85, 0.77, 3.07, 0.0, 0.012, mat("rug_wool", "#CDBFA8", 1.0), P["rug"])
    box("curtains", -2.29, -2.15, 2.65, 2.95, 2.82 - 2.70, 2.82, lin, P["curtains"], bevel=0.02)
    cyl("vase", -2.42, 1.35, 0.08, 0.45, 0.77, mat("stoneware", "#ECE6DC", 0.85), P["vase"], r1=0.06)
    cyl("branch (filler)", -2.42, 1.35, 0.012, 0.77, 1.05, mat("olive_leaf", "#5E6B4E", 0.9), FILLER_IDX["branch (filler)"], r1=0.10, verts=16)
    cyl("planter", planter_c[0], planter_c[1], 0.21, 0.0, 0.355, mat("cement_beige", "#C9BFAE", 0.9), P["planter"], r1=0.19)
    nleaf, _ = olive_crown(planter_c)
    cyl("basket", basket_c[0], basket_c[1], 0.175, 0.0, 0.39, mat("jute", "#B89F78", 1.0), P["basket"])
    box("magazine-holder", -0.645, -0.295, 2.475, 2.665, 0.012, 0.287, mat("gunmetal", "#4A4744", 0.6), P["magazine-holder"])
    fl = (1.44, 0.20)
    cyl("floor-lamp", fl[0], fl[1], 0.13, 0.0, 0.025, wal, P["floor-lamp"])
    cyl("floor-lamp", fl[0], fl[1], 0.0125, 0.025, 1.35, wal, P["floor-lamp"], verts=16)
    for x in (-0.36, 0.20, 0.76):
        box("framed-art", x - 0.25, x + 0.25, 0.0, 0.03, 1.13, 1.83, mat("print", "#BDB3A6", 0.9), P["framed-art"])
    for x in (-0.85, 1.25):
        box("accent-sconces", x - 0.04, x + 0.04, 0.0, 0.025, 1.67, 1.83, wal, P["accent-sconces"])
        cyl("accent-sconces", x, 0.0575, 0.0325, 1.67, 1.83, tra, P["accent-sconces"], verts=32)
    cyl("pendant cord", 0.20, 1.72, 0.004, 2.18, 3.00, wal, FILLER_IDX["pendant cord"], verts=8)
    cyl("bowl", 0.62, 1.94, 0.10, TABLE_TOP, TABLE_TOP + 0.08, mat("matte_black", "#2B2826", 0.7), P["bowl"], r1=0.10)
    cand = mat("candle", "#F2EDE4", 0.6)
    for (x, y, hc) in ((0.205, 1.74, 0.075), (0.355, 1.68, 0.06)):
        cyl("candle-holders", x, y, 0.035, TABLE_TOP, TABLE_TOP + 0.11, tra, P["candle-holders"])
        cyl("candles (filler)", x, y, 0.03, TABLE_TOP + 0.11, TABLE_TOP + 0.11 + hc, cand, FILLER_IDX["candles (filler)"])
    cush = mat("cushion", "#C9B9A2", 0.95)
    box("cushion-left", -0.70, -0.25, 0.24, 0.42, SOFA["seat"], SOFA["seat"] + 0.45, cush, P["cushion-left"], bevel=0.06)
    box("cushion-right", 0.70, 1.20, 0.24, 0.42, SOFA["seat"], SOFA["seat"] + 0.50, cush, P["cushion-right"], bevel=0.06)
    box("cushion-lumbar", 0.25, 0.75, 0.30, 0.46, SOFA["seat"], SOFA["seat"] + 0.30, mat("cushion_caramel", "#B08A62", 0.95), P["cushion-lumbar"],
        bevel=0.05)
    pecan = mat("throw_pecan", "#8C6A4E", 1.0)
    box("throw", 1.04, 1.32, 0.40, 0.97, 0.03, SOFA["arm_h"] + 0.02, pecan, P["throw"], bevel=0.03)
    box("throw", 0.78, 1.04, 0.50, 0.96, SOFA["seat"], SOFA["seat"] + 0.03, pecan, P["throw"], bevel=0.01)
    notes.append(f"products: {len(P)} proxies at card size (pass 801-818); olive (filler) {nleaf} leaf cards, crown Z {OLIVE['crown_z']} "
                 f"r {OLIVE['r']} over the planter at {planter_c}; basket at {basket_c}")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# lamps
# ---------------------------------------------------------------------------------------------------------------
def light(name, kind, loc, energy, dirv=None, size=0.03, beam=None, blend=0.5):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    if kind == "SPOT":
        ld.spot_size = math.radians(beam)
        ld.spot_blend = blend
    if kind in ("SPOT", "POINT"):
        ld.shadow_soft_size = size
    if kind == "AREA":
        ld.shape, ld.size = "DISK", size
    FF.light_blackbody(ld, LAMP_K)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    if dirv is not None:
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Vector(dirv).normalized().to_track_quat("-Z", "Y")
    return ob


def lamps(spot_w=15.0, fl_w=35.0, pd_w=35.0, ws_w=12.0, glow=4.0):
    notes = []
    P = PROD_IDX
    # the travertine sconce pair: wall-wash up and down, tilted 8 deg toward the plaster (-Y)
    gm = FF.emission("m0w_glow_sconce", LAMP_K, glow * 1.5)
    L = []
    t = math.radians(8.0)
    for x in (-0.85, 1.25):
        for z, sgn in ((1.83 + 0.004, 1.0), (1.67 - 0.004, -1.0)):
            L.append(light(f"m0w_sconce_{x}_{'up' if sgn > 0 else 'down'}", "SPOT", (x, 0.0575, z), spot_w, (0.0, -math.sin(t), sgn * math.cos(t)),
                           size=0.012, beam=30.0))
            g = cyl("accent-sconces", x, 0.0575, 0.027, z - 0.0007 * sgn - 0.0007, z - 0.0007 * sgn + 0.0007, gm, P["accent-sconces"], verts=24)
            g.visible_shadow = False
    LAMPS["accent-sconces"] = dict(lights=L, glow=[gm], at=[[-0.85, 0.0575, 1.75], [1.25, 0.0575, 1.75]],
                                   note=f"two 2700 K spots per lamp, up and down, beam 30, tilted 8 deg to the plaster, {spot_w} W each; lit end discs")
    # the floor lamp: an open pleated cone (light leaves by its ends), a bulb inside
    gf = FF.emission("m0w_glow_floor", LAMP_K, glow)
    cyl("floor-lamp", 1.44, 0.20, 0.185, 1.35, 1.58, gf, P["floor-lamp"], r1=0.12, caps=False)
    LAMPS["floor-lamp"] = dict(lights=[light("m0w_floor_bulb", "POINT", (1.44, 0.20, 1.44), fl_w, size=0.03)], glow=[gf], at=[[1.44, 0.20, 1.44]],
                               note=f"bulb {fl_w} W at Z 1.44 inside the open shade (emission {glow}); the puddle falls through the open bottom")
    # the pendant: a tiered drum, open below and above
    gp = FF.emission("m0w_glow_pendant", LAMP_K, glow)
    for (r, z0, z1) in ((0.25, 1.90, 1.99), (0.225, 1.99, 2.08), (0.20, 2.08, 2.18)):
        cyl("pendant", 0.20, 1.72, r, z0, z1, gp, P["pendant"], caps=False)
    LAMPS["pendant"] = dict(lights=[light("m0w_pendant_bulb", "POINT", (0.20, 1.72, 2.02), pd_w, size=0.04)], glow=[gp], at=[[0.20, 1.72, 2.02]],
                            note=f"bulb {pd_w} W at Z 2.02 in a three-tier drum D50 x 28, open below and above (emission {glow})")
    # the window-wall sconce (out of frame): its light on the armchair
    gw = FF.emission("m0w_glow_wsconce", LAMP_K, glow)
    box("wall-sconce", -2.30, -2.275, 3.13, 3.21, 1.40, 1.54, wal_mat(), P["wall-sconce"])
    cyl("wall-sconce", -2.24, 3.17, 0.032, 1.40, 1.54, gw, P["wall-sconce"], verts=24)
    LAMPS["wall-sconce"] = dict(lights=[light("m0w_wsconce_bulb", "POINT", (-2.20, 3.17, 1.47), ws_w, size=0.03)], glow=[gw], at=[[-2.20, 3.17, 1.47]],
                                note=f"window-wall sconce plate (-2.30, 3.17, 1.47), {ws_w} W point (out of frame; its light on the armchair)")
    for k, v in LAMPS.items():
        notes.append(f"lamp {k}: {v['note']}")
    return notes


def wal_mat():
    return mat("walnut", "#6B4A33", 0.85)


def set_lamps(on, glow=True):
    for k, v in LAMPS.items():
        for ob in v["lights"]:
            ob.hide_render = k not in on
        for m in v["glow"]:
            em = next(n for n in m.node_tree.nodes if n.type == "EMISSION")
            if "_keep" not in m:
                m["_keep"] = em.inputs["Strength"].default_value
            em.inputs["Strength"].default_value = m["_keep"] if (k in on and glow) else 0.0


# ---------------------------------------------------------------------------------------------------------------
# camera, renders
# ---------------------------------------------------------------------------------------------------------------
def set_view(cam, res):
    """E.set_view_canvas with the lens at 35 mm: the 16:9 frame at FRAME_BOX inside the 2720 x 1530 canvas, at width res"""
    Wd, Hd = res, int(round(res * CANVAS[1] / CANVAS[0]))
    k = Wd / CANVAS[0]
    fx, fy = (FRAME_BOX[2] - FRAME_BOX[0]) * k, (FRAME_BOX[3] - FRAME_BOX[1]) * Hd / CANVAS[1]
    ox, oy = FRAME_BOX[0] * k, FRAME_BOX[1] * Hd / CANVAS[1]
    cam.location = tuple(CAM["loc"])
    cam.rotation_euler = (math.radians(90), 0, math.radians(180 - CAM["yaw"]))
    cd = cam.data
    cd.sensor_fit = "HORIZONTAL"
    cd.lens = CAM["lens"]
    cd.sensor_width = 36.0 * Wd / fx
    ycor = (20.25 * Hd / fy) / (cd.sensor_width * Hd / Wd)
    sc = bpy.context.scene
    sc.render.pixel_aspect_x, sc.render.pixel_aspect_y = (1.0 / ycor, 1.0) if ycor <= 1.0 else (1.0, ycor)
    U0, V0 = (ox + CAM["u0"] * fx) / Wd, (oy + CAM["v0"] * fy) / Hd
    cd.shift_x = -(U0 - 0.5)
    cd.shift_y = (V0 - 0.5) * ycor * Hd / Wd
    bpy.context.view_layer.update()
    return dict(W=Wd, H=Hd, fx=fx, fy=fy, ox=ox, oy=oy)


def white_override():
    m = bpy.data.materials.get("m0w_white_override")
    if m is None:
        m = bpy.data.materials.new("m0w_white_override")
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
        b.inputs["Roughness"].default_value = 1.0
    return m


def render_linear(tmp, W, H, samples, bounces=None, sky=None, override=False):
    """scene-linear RGB (float32, top row first) of the current light setup; nothing written outside tmp"""
    sc = bpy.context.scene
    bgn = sc.world.node_tree.nodes["Background"]
    keep = dict(sky=bgn.inputs["Strength"].default_value, b=sc.cycles.max_bounces)
    vl = bpy.context.view_layer
    try:
        if sky is not None:
            bgn.inputs["Strength"].default_value = sky
        if bounces is not None:
            sc.cycles.max_bounces = bounces
        if override:
            vl.material_override = white_override()
        FF.render_beauty(os.path.join(tmp, "x.png"), os.path.join(tmp, "p"), W, H, samples, 0.0, 0.0, keep_exr=os.path.join(tmp, "lin.exr"))
        rgb = bs.load_exr(os.path.join(tmp, "lin.exr"), channels=3).astype(np.float32)
    finally:
        bgn.inputs["Strength"].default_value = keep["sky"]
        sc.cycles.max_bounces = keep["b"]
        vl.material_override = None
        for f in ("x.png", "lin.exr"):
            if os.path.exists(os.path.join(tmp, f)):
                os.remove(os.path.join(tmp, f))
        shutil.rmtree(os.path.join(tmp, "p"), ignore_errors=True)
    return rgb


def lum(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def save16(path, x, ref):
    Image.fromarray(np.clip(np.rint(x / max(ref, 1e-9) * 65535), 0, 65535).astype(np.uint16)).save(path, optimize=True)


def hide_products(hide):
    for k, obs in OBJS.items():
        if k == "sofa":
            continue
        for ob in obs:
            ob.hide_render = hide


# ---------------------------------------------------------------------------------------------------------------
# measurements
# ---------------------------------------------------------------------------------------------------------------
def tris_world(obs):
    dg = bpy.context.evaluated_depsgraph_get()
    V, T, n = [], [], 0
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        mw = ev.matrix_world
        v = np.array([tuple(mw @ x.co) for x in me.vertices], np.float64)
        t = np.array([tuple(x.vertices) for x in me.loop_triangles], np.int64)
        ev.to_mesh_clear()
        if len(t):
            V.append(v)
            T.append(t + n)
            n += len(v)
    return (np.concatenate(V), np.concatenate(T)) if V else (np.zeros((0, 3)), np.zeros((0, 3), np.int64))


def silhouette(obs, cv, margin):
    """the full projected silhouette (no occlusion, beyond the frame too) on the render canvas grown by margin px on every side"""
    V, T = tris_world(obs)
    m = np.zeros((cv["H"] + 2 * margin, cv["W"] + 2 * margin), np.uint8)
    if not len(T):
        return m.astype(bool)
    u, v, d = plan_uv(V[:, 0], V[:, 1], V[:, 2])
    xy = np.stack([cv["ox"] + u * cv["fx"] + margin, cv["oy"] + v * cv["fy"] + margin], 1)
    polys = np.round(xy[T] * 4).astype(np.int32)
    ok = (d[T] > 0.05).all(1)
    for tri in polys[ok]:                        # one triangle at a time: fillPoly on a list fills overlaps even-odd
        cv2.fillConvexPoly(m, tri, 1, lineType=cv2.LINE_8, shift=2)
    return m.astype(bool)


def aabb(obs):
    V, _ = tris_world(obs)
    return V.min(0), V.max(0)


def aabb_dist(A, B):
    (a0, a1), (b0, b1) = A, B
    d = np.maximum(0, np.maximum(a0 - b1, b0 - a1))
    return float(np.sqrt((d ** 2).sum()))


_CLOUD = {}


def cloud(obs, n=3000):
    """surface points: the vertices plus n area-weighted samples on the triangles (seeded), cached by object names"""
    key = tuple(sorted(o.name for o in obs)) + tuple(round(c, 4) for o in obs for c in o.location)
    if key in _CLOUD:
        return _CLOUD[key]
    V, T = tris_world(obs)
    if not len(T):
        return V
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    rng = np.random.default_rng(3)
    k = rng.choice(len(T), size=n, p=area / max(area.sum(), 1e-12))
    r1, r2 = rng.random(n), rng.random(n)
    s1 = np.sqrt(r1)
    P = (1 - s1)[:, None] * a[k] + (s1 * (1 - r2))[:, None] * b[k] + (s1 * r2)[:, None] * c[k]
    out = np.concatenate([V, P])
    _CLOUD[key] = out
    return out


def near3d(obsA, obsB, boxA=None, boxB=None):
    """the 3D distance used by F3's 'contact' skip: the box distance, and when the boxes touch, the sampled surface distance"""
    d0 = aabb_dist(boxA or aabb(obsA), boxB or aabb(obsB))
    if d0 >= 0.03:
        return d0
    A, B = cloud(obsA), cloud(obsB)
    best = 1e9
    for i in range(0, len(A), 2000):
        d = np.sqrt(((A[i:i + 2000, None, :] - B[None, :, :]) ** 2).sum(-1)).min()
        best = min(best, float(d))
    return best


def thickness(m):
    if not m.any():
        return 0.0
    dt = cv2.distanceTransform(np.pad(m.astype(np.uint8), 1), cv2.DIST_L2, 5)
    return 2.0 * float(dt.max())


def boundary(m):
    return m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)


def min_dist(a, b):
    if (a & b).any():
        return 0.0
    dt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[a].min())


def f3_pairs(N, FW):
    """step0_clay_checks.py F3 (the rule of framing_r2 frame_selfcheck), on the M0-W index pass and analytic silhouettes"""
    names, out = list(N), []
    pad = int(0.03 * FW)
    for i, k in enumerate(names):
        for j in names[i + 1:]:
            A, B = N[k], N[j]
            ya, xa = np.nonzero(A["vis"])
            yb, xb = np.nonzero(B["vis"])
            if not len(xa) or not len(xb):
                continue
            if xa.min() > xb.max() + pad or xb.min() > xa.max() + pad or ya.min() > yb.max() + pad or yb.min() > ya.max() + pad:
                continue
            d3 = near3d(A["obs"], B["obs"], A["box"], B["box"])
            rec = dict(a=k, b=j, dist3d_m=round(d3, 3))
            if d3 < 0.03:
                rec.update(kind="contact", verdict="skip (physical contact / resting)")
                out.append(rec)
                continue
            inter = A["sil"] & B["sil"]
            if not inter.any():
                g = min_dist(A["vis"], B["vis"])
                rec.update(kind="gap", gap_frame=round(g / FW, 4), verdict="FAIL (kissing, < 0.02)" if g / FW < 0.02 else "clear (>= 0.02)")
                out.append(rec)
                continue
            touching = (cv2.dilate(A["vis"].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & B["vis"]).any()
            if not touching:
                rec.update(kind="overlap-hidden", verdict="skip (overlap only where a third item hides both)")
                out.append(rec)
                continue
            front, back, fn = (A, B, k) if A["dep"] < B["dep"] else (B, A, j)
            inside = float((front["sil"] & back["sil"]).sum()) / max(1, front["sil"].sum())
            th = thickness(inter) / FW
            cover = float(inter.sum()) / max(1, back["sil"].sum())
            rec.update(front=fn, overlap_thickness=round(th, 4), cover_of_back=round(cover, 3))
            if inside >= 0.99:
                seen = boundary(back["sil"]) & cv2.dilate(back["vis"].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                cg = None
                if seen.any() and boundary(front["vis"]).any():
                    dtb = cv2.distanceTransform((~seen).astype(np.uint8), cv2.DIST_L2, 5)
                    cg = float(dtb[boundary(front["vis"])].min())
                rec.update(kind="contained", contour_gap_frame=None if cg is None else round(cg / FW, 4),
                           verdict="FAIL (contour < 0.02 from the visible contour behind)" if cg is not None and cg / FW < 0.02 else "clear (contained)")
            else:
                rec.update(kind="overlap", verdict="FAIL (overlap < 0.03 and < 60 % of the back item)" if th < 0.03 and cover < 0.6 else "decisive overlap")
            out.append(rec)
    return out


def measure(idx, depth, cv, margin):
    """V7Q6, F3, the edge tangents, the framing numbers of 3.1, from the M0-W index pass (render canvas) and the analytic silhouettes"""
    W, H = cv["W"], cv["H"]
    fx0, fy0 = int(round(cv["ox"])), int(round(cv["oy"]))
    fx1, fy1 = int(round(cv["ox"] + cv["fx"])), int(round(cv["oy"] + cv["fy"]))
    frame = np.zeros((H, W), bool)
    frame[fy0:fy1, fx0:fx1] = True
    FA, FW, FH = float(frame.sum()), cv["fx"], cv["fy"]
    sl = (slice(margin, margin + H), slice(margin, margin + W))
    items = {k: OBJS[k] for k in PROD_IDX if k in OBJS}
    items["fixed:sofa"] = [o for o in OBJS["sofa"]]
    items["fixed:armchair"] = [o for o in bpy.data.objects if o.type == "MESH" and o.pass_index == ARMCHAIR_IDX and not o.hide_render]
    pid = dict(PROD_IDX, **{"fixed:sofa": SOFA_IDX, "fixed:armchair": ARMCHAIR_IDX})
    rows, N = {}, {}
    for k, obs in items.items():
        if not obs:
            continue
        sil = silhouette([o for o in obs if not o.hide_render], cv, margin)
        vis = idx == pid[k]
        vis_f = vis & frame
        ys, xs = np.nonzero(vis_f)
        r = dict(card=CARD.get(k, "fixed (not sold)"), visible_px=int(vis_f.sum()), frame_pct=round(100 * vis_f.sum() / FA, 3),
                 silhouette_px=int(sil.sum()), visible_share=round(float(vis_f.sum()) / max(1, sil.sum()), 3))
        if len(xs):
            r["u"] = [round((xs.min() - cv["ox"]) / FW, 4), round((xs.max() + 1 - cv["ox"]) / FW, 4)]
            r["v"] = [round((ys.min() - cv["oy"]) / FH, 4), round((ys.max() + 1 - cv["oy"]) / FH, 4)]
            n_, lab_, st_, _ = cv2.connectedComponentsWithStats(vis_f.astype(np.uint8), connectivity=8)
            big = [st_[i] for i in range(1, n_) if st_[i][4] >= 0.05 * vis_f.sum()]
            r["height_pct"] = round(100 * max(b[3] for b in big) / FH, 2) if big else 0.0          # the tallest part (a pair = two parts)
            r["edge_margins"] = dict(left=r["u"][0], right=round(1 - r["u"][1], 4), top=r["v"][0], bottom=round(1 - r["v"][1], 4))
            r["edge_tangent"] = {s: m for s, m in r["edge_margins"].items() if 0 < m < 0.02}
        sil_c = sil[sl]
        if sil_c.any():
            iou = float((sil_c & vis).sum()) / max(1, float((sil_c | vis).sum()))
            r["iou_visible_in_silhouette"] = round(float((sil_c & vis).sum()) / max(1, vis.sum()), 4)
        if not k.startswith("fixed:") and k != "wall-sconce":
            counted = (r["frame_pct"] >= 0.5 or (r["frame_pct"] >= 0.15 and r.get("height_pct", 0) >= 6.0)) and r["visible_share"] >= 0.5
            r["v7q6"] = "counted" if counted else "NOT counted"
        rows[k] = r
        dd = depth[vis] if vis.any() else None
        N[k] = dict(sil=sil_c, vis=vis_f, box=aabb(obs), obs=[o for o in obs if not o.hide_render],
                    dep=float(np.median(dd)) if dd is not None and len(dd) else 99.0)
        if k == "rug":                                    # the rug's real-area share in the frame and unhidden (a 2 cm grid on its top)
            gx, gy = np.meshgrid(np.arange(-1.45, 1.85, 0.02), np.arange(0.77, 3.07, 0.02))
            uu, vv, dz = plan_uv(gx.ravel(), gy.ravel(), np.full(gx.size, 0.012))
            px_, py_ = np.round(cv["ox"] + uu * FW).astype(int), np.round(cv["oy"] + vv * FH).astype(int)
            inside = (px_ >= fx0) & (px_ < fx1) & (py_ >= fy0) & (py_ < fy1)
            seen = np.zeros_like(inside)
            seen[inside] = idx[py_[inside], px_[inside]] == pid[k]
            r["real_area_share_in_frame"] = round(float(inside.mean()), 3)
            r["real_area_share_seen"] = round(float(seen.mean()), 3)
    f3 = f3_pairs({k: v for k, v in N.items() if v["vis"].any()}, FW)
    # the pendant's shade alone (the cord is a filler)
    psil = silhouette(OBJS["pendant"], cv, margin)
    pvis = (idx == PROD_IDX["pendant"]) & frame
    pend = dict(shade_visible_share=round(float(pvis.sum()) / max(1, psil.sum()), 3), rule="V7Q7 / 3.1: the pendant >= 50 % visible")
    # the glazing in frame: share of the glazing aperture (sky + frame) inside the frame
    glaz = dict(sky_px_in_frame=int(((idx == 0) & frame).sum()), sky_pct_of_frame=round(100 * float(((idx == 0) & frame).sum()) / FA, 2))
    return rows, f3, pend, glaz, frame


def basket_ok_in_plan(x, y, r=0.175, planter_c=None):
    """the basket's plan circle against the walls, the rounded corner, the window bench, the sofa, the planter and the armchair"""
    th = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    px, py = x + r * np.cos(th), y + r * np.sin(th)
    if (px < -2.30 + 0.005).any() or (py < 0.005).any():
        return "wall"
    cc = (-2.0, 0.30)
    corner = (px < cc[0]) & (py < cc[1]) & (np.hypot(px - cc[0], py - cc[1]) > 0.30)
    if corner.any():
        return "rounded corner"
    if ((px < -1.98) & (py > 1.00)).any():
        return "window bench"
    if ((px > SOFA["x"][0] - 0.02) & (py < SOFA["y"][1] + 0.02)).any():
        return "sofa"
    if planter_c is not None and math.hypot(x - planter_c[0], y - planter_c[1]) < 0.21 + r + 0.02:
        return "planter"
    if math.hypot(x - (-1.23), y - 2.73) < 0.55 + r:
        return "armchair"
    return None


def basket_sweep(cv, margin, planter_c):
    """the basket on a 5 cm x 10 cm grid of the left floor: its visible share (nearer occluders removed) and F3 against its neighbours
    (analytic silhouettes on the margin canvas; the gap from precomputed distance fields)"""
    base = OBJS["basket"][0]
    keep = tuple(base.location)
    nb = {"fixed:sofa": OBJS["sofa"], "planter": OBJS["planter"], "olive (filler)": OBJS["olive (filler)"], "magazine-holder": OBJS["magazine-holder"],
          "fixed:armchair": [o for o in bpy.data.objects if o.type == "MESH" and o.pass_index == ARMCHAIR_IDX and not o.hide_render]}
    nsil = {k: silhouette(v, cv, margin) for k, v in nb.items()}
    ndt = {k: cv2.distanceTransform((~v).astype(np.uint8), cv2.DIST_L2, 5) for k, v in nsil.items()}
    nbox = {k: aabb(v) for k, v in nb.items()}
    ndep = {k: float(plan_uv(*(np.array(nbox[k]).mean(0)))[2]) for k in nb}
    FW = cv["fx"]
    frame = np.zeros(nsil["planter"].shape, bool)
    frame[int(margin + cv["oy"]):int(margin + cv["oy"] + cv["fy"]), int(margin + cv["ox"]):int(margin + cv["ox"] + cv["fx"])] = True
    out, skipped = [], {}
    for x in np.round(np.arange(-2.10, -1.249, 0.05), 3):
        for y in np.round(np.arange(0.25, 1.151, 0.10), 3):
            why = basket_ok_in_plan(float(x), float(y), planter_c=planter_c)
            if why:
                skipped[why] = skipped.get(why, 0) + 1
                continue
            base.location = (float(x), float(y), keep[2])
            bpy.context.view_layer.update()
            sil = silhouette([base], cv, margin)
            d = float(plan_uv(x, y, 0.2)[2])
            vis = sil.copy()
            for k, o in nsil.items():
                if ndep[k] < d:
                    vis &= ~o
            vis &= frame
            rec = dict(at=[float(x), float(y)], u_centre=round(float(plan_uv(x, y, 0.2)[0]), 4),
                       visible_share=round(float(vis.sum()) / max(1, sil.sum()), 3), vs={})
            fails = []
            for k, o in nsil.items():
                d3 = near3d([base], nb[k], aabb([base]), nbox[k])
                if d3 < 0.03:
                    rec["vs"][k] = "contact %.3f" % d3
                    if k in ("planter", "fixed:sofa", "fixed:armchair", "magazine-holder"):
                        fails.append(f"{k} 3D {d3:.3f}")
                    continue
                inter = sil & o
                if not inter.any():
                    g = float(ndt[k][vis].min()) / FW if vis.any() else None
                    rec["vs"][k] = None if g is None else round(g, 4)
                    if g is not None and g < 0.02:
                        fails.append(f"{k} gap {g:.4f}")
                else:
                    th = thickness(inter) / FW
                    back = o if ndep[k] > d else sil
                    cover = float(inter.sum()) / max(1, back.sum())
                    rec["vs"][k] = f"overlap {th:.4f} (cover {cover:.2f})"
                    if th < 0.03 and cover < 0.6:
                        fails.append(f"{k} thin overlap {th:.4f}")
            ys_, xs_ = np.nonzero(vis)
            if len(xs_):
                ml = (xs_.min() - margin - cv["ox"]) / FW
                if 0 < ml < 0.02:
                    fails.append(f"left edge {ml:.4f}")
            if rec["visible_share"] < 0.5:
                fails.append(f"visible {rec['visible_share']}")
            rec["fails"] = fails
            rec["verdict"] = "clear" if not fails else "fails"
            out.append(rec)
    base.location = keep
    bpy.context.view_layer.update()
    want = (-1.50, 0.30)                                  # the proposal's expectation: about 0.3 m left of (-1.20, 0.30)
    ok = sorted([r for r in out if r["verdict"] == "clear"], key=lambda r: math.hypot(r["at"][0] - want[0], r["at"][1] - want[1]))
    return dict(grid="X -2.10..-1.25 step 0.05, Y 0.25..1.15 step 0.10 (basket D35 x H39)", skipped_in_plan=skipped, tested=len(out),
                clear=len(ok), best=ok[:6], expectation=list(want), all=out)


def world_of(depth, cv):
    """camera ray x planar depth: world XYZ of every pixel of the render canvas"""
    H, W = depth.shape
    u = ((np.arange(W) + 0.5) - cv["ox"]) / cv["fx"]
    v = ((np.arange(H) + 0.5) - cv["oy"]) / cv["fy"]
    U, V = np.meshgrid(u, v)
    y = math.radians(CAM["yaw"])
    fw, rt = np.array([-math.sin(y), -math.cos(y)]), np.array([math.cos(y), -math.sin(y)])
    x_ = (U - CAM["u0"]) / K_U * depth
    z_ = CAM["loc"][2] - (V - CAM["v0"]) / K_V * depth
    X = CAM["loc"][0] + fw[0] * depth + rt[0] * x_
    Y = CAM["loc"][1] + fw[1] * depth + rt[1] * x_
    return X, Y, z_


def sun_geometry(sunmap, idx, depth, cv, shell_idx, olive_shadow=None):
    lit = sunmap > 0.05
    X, Y, Z = world_of(depth, cv)
    out = {}
    cls = {"floor": [shell_idx.get("floor")], "rug": [PROD_IDX["rug"]], "back wall": [shell_idx.get("back-wall")],
           "sofa": [SOFA_IDX], "coffee table": [PROD_IDX["coffee-table"]], "window bench": [], "armchair": [ARMCHAIR_IDX]}
    for k, ids in cls.items():
        m = lit & np.isin(idx, [i for i in ids if i is not None])
        if not m.any():
            out[k] = dict(px=0)
            continue
        r = dict(px=int(m.sum()))
        if k in ("floor", "rug"):
            pts = np.stack([X[m], Y[m]], 1).astype(np.float32)
            hull = cv2.convexHull(pts)[:, 0, :]
            r.update(plan_x=[round(float(X[m].min()), 3), round(float(X[m].max()), 3)], plan_y=[round(float(Y[m].min()), 3), round(float(Y[m].max()), 3)],
                     hull_xy=[[round(float(a), 3), round(float(b), 3)] for a, b in hull[:: max(1, len(hull) // 24)]])
        elif k == "back wall":
            r.update(wall_x=[round(float(X[m].min()), 3), round(float(X[m].max()), 3)], wall_z=[round(float(Z[m].min()), 3), round(float(Z[m].max()), 3)])
        else:
            ys, xs = np.nonzero(m)
            r.update(u=[round((xs.min() - cv["ox"]) / cv["fx"], 4), round((xs.max() + 1 - cv["ox"]) / cv["fx"], 4)])
        out[k] = r
    if olive_shadow is not None and olive_shadow.any():
        m = olive_shadow
        out["olive leaf shadow"] = dict(px=int(m.sum()), wall_x=[round(float(X[m].min()), 3), round(float(X[m].max()), 3)],
                                        wall_z=[round(float(Z[m].min()), 3), round(float(Z[m].max()), 3)],
                                        centroid_xz=[round(float(X[m].mean()), 3), round(float(Z[m].mean()), 3)],
                                        u=[round((np.nonzero(m)[1].min() - cv["ox"]) / cv["fx"], 4), round((np.nonzero(m)[1].max() + 1 - cv["ox"]) / cv["fx"], 4)])
    return out


def lamp_geometry(maps, idx, depth, cv):
    X, Y, Z = world_of(depth, cv)
    valid = (idx != 0) & (depth < 50)
    out = {}
    for k, L in maps.items():
        Lw = cv2.resize(L, (idx.shape[1], idx.shape[0]), interpolation=cv2.INTER_LINEAR)
        rec = dict(at=LAMPS[k]["at"], uv=[[round(float(a), 4) for a in plan_uv(*p)[:2]] for p in LAMPS[k]["at"]])
        tot = float(Lw[valid].sum())
        if tot > 0:
            ids = np.unique(idx[valid])
            sh = sorted(((float(Lw[valid & (idx == i)].sum()) / tot, int(i)) for i in ids), reverse=True)[:6]
            rec["light_share_by_pass_index"] = [dict(pass_index=i, share=round(v, 3)) for v, i in sh]
            own = PROD_IDX.get(k, -1)
            m = valid & (idx != own)
            thr = np.percentile(Lw[m], 99.7)
            hot = m & (Lw >= thr)
            rec["hot_spot_xyz"] = [round(float(X[hot].mean()), 3), round(float(Y[hot].mean()), 3), round(float(Z[hot].mean()), 3)]
            rec["hot_spot_on"] = [dict(pass_index=int(i), px=int(c)) for i, c in zip(*np.unique(idx[hot], return_counts=True))][:6]
            if k == "floor-lamp":
                sofa = valid & (idx == SOFA_IDX)
                xs = np.nonzero(sofa)[1]
                if len(xs):
                    uu = (xs - cv["ox"]) / cv["fx"]
                    vals = Lw[sofa]
                    rec["puddle_right_arm_vs_left_half"] = round(float(vals[uu > 0.74].mean()) / max(1e-9, float(vals[uu < 0.58].mean())), 2)
        out[k] = rec
    return out


def ids_png(path, idx, shell_idx):
    pal = {0: (255, 255, 255), SOFA_IDX: (120, 160, 200), ARMCHAIR_IDX: (110, 190, 140)}
    rng = np.random.default_rng(7)
    for k, v in list(PROD_IDX.items()) + list(FILLER_IDX.items()):
        pal[v] = tuple(int(c) for c in rng.integers(40, 235, 3))
    out = np.full(idx.shape + (3,), 90, np.uint8)
    for s, v in shell_idx.items():
        out[idx == v] = (200 + (sum(map(ord, s)) % 40), 195, 185)
    for v, c in pal.items():
        out[idx == v] = c
    Image.fromarray(out).save(path, optimize=True)
    return {int(v): c for v, c in pal.items()}


def overlay(path, clay, rows, cv, sunmap, oshadow, lampgeo, scale):
    im = Image.fromarray(clay).convert("RGB")
    W, H = im.size
    im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    dr = ImageDraw.Draw(im, "RGBA")
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    s = scale
    f = [cv["ox"] * s, cv["oy"] * s, (cv["ox"] + cv["fx"]) * s, (cv["oy"] + cv["fy"]) * s]
    dr.rectangle(f, outline=(255, 255, 255, 200), width=1)
    if sunmap is not None:
        m = cv2.resize((sunmap > 0.05).astype(np.uint8), im.size, interpolation=cv2.INTER_NEAREST)
        cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            if len(c) > 4:
                dr.line([tuple(p[0]) for p in c] + [tuple(c[0][0])], fill=(255, 196, 0, 230), width=2)
    if oshadow is not None and oshadow.any():
        m = cv2.resize(oshadow.astype(np.uint8), im.size, interpolation=cv2.INTER_NEAREST)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            if len(c) > 4:
                dr.line([tuple(p[0]) for p in c] + [tuple(c[0][0])], fill=(40, 200, 90, 230), width=2)
    for k, r in rows.items():
        if "u" not in r:
            continue
        x0, x1 = (cv["ox"] + r["u"][0] * cv["fx"]) * s, (cv["ox"] + r["u"][1] * cv["fx"]) * s
        y0, y1 = (cv["oy"] + r["v"][0] * cv["fy"]) * s, (cv["oy"] + r["v"][1] * cv["fy"]) * s
        col = (90, 170, 255, 220) if k.startswith("fixed:") else ((255, 80, 80, 230) if r.get("v7q6") == "NOT counted" else (255, 255, 255, 220))
        dr.rectangle([x0, y0, x1, y1], outline=col, width=1)
        lab = f"{k} {r['frame_pct']:.2f}% vis {int(100 * r['visible_share'])}%"
        dr.text((x0 + 2, max(f[1], y0 - 14)), lab, fill=col, font=font)
    for k, g in lampgeo.items():
        for (u, v) in g["uv"]:
            x, y = (cv["ox"] + u * cv["fx"]) * s, (cv["oy"] + v * cv["fy"]) * s
            dr.ellipse([x - 6, y - 6, x + 6, y + 6], outline=(255, 140, 0, 255), width=2)
            dr.text((x + 8, y - 6), k, fill=(255, 140, 0, 255), font=font)
    dr.text((f[0] + 6, f[3] - 18), "M0-W clay: 35 mm, (0.95, 5.55, 1.05), yaw 14; yellow = direct sun (alt 15); green = olive leaf shadow; "
            "orange = lamps; red box = not counted (V7Q6)", fill=(255, 255, 255, 255), font=font)
    im.save(path, quality=88)


# ---------------------------------------------------------------------------------------------------------------
def beauty_only(a, out, cam, fa, target=74.0):
    """the lit clay and the plate reading at the exposure that puts the shaded back-wall plaster (out of the sun, outside the sconce
    pools) at L* 74; the exposure found by bisection on 680-px renders; clay-m0w.json gets the calibration"""
    jp = os.path.join(out, "clay-m0w.json")
    rec = json.load(open(jp))
    bc = rec["basket_in_clay"]
    OBJS["basket"][0].location = (bc[0], bc[1], OBJS["basket"][0].location.z)
    bpy.context.view_layer.update()
    tmp = tempfile.mkdtemp(prefix="m0w-b-", dir=SCR)
    z = np.load(os.path.join(SCR, "m0w-passes.npz"))
    idx_full = z["idx"]
    sun_full = np.asarray(Image.open(os.path.join(out, "m0w-sun.png"))).astype(np.float32) / 255.0
    sc_full = np.asarray(Image.open(os.path.join(out, "m0w-light-accent-sconces.png"))).astype(np.float32) / 65535.0
    set_lamps(set(LAMPS))
    lo, hi, tries = -4.0, 1.0, []
    cvs = set_view(cam, 680)
    W, H = cvs["W"], cvs["H"]
    wall = cv2.resize((idx_full == 5).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    shade = cv2.resize(sun_full, (W, H), interpolation=cv2.INTER_AREA) < 0.02
    quiet = cv2.resize(sc_full, (W, H), interpolation=cv2.INTER_AREA) < 0.15
    m = wall & shade & quiet
    sunny = wall & (cv2.resize(sun_full, (W, H), interpolation=cv2.INTER_AREA) > 0.5)
    for _ in range(6):
        e = (lo + hi) / 2
        png = os.path.join(tmp, "c.png")
        FF.render_beauty(png, os.path.join(tmp, "b"), W, H, 8, 0.30, e)
        Lm = cv2.cvtColor(np.asarray(Image.open(png).convert("RGB")).astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[..., 0]
        v = float(np.median(Lm[m]))
        tries.append(dict(exposure=round(e, 3), shaded_plaster_L=round(v, 2), sunlit_plaster_L=round(float(np.median(Lm[sunny])), 2) if sunny.any() else None))
        if v > target:
            hi = e
        else:
            lo = e
    best = min(tries, key=lambda t: abs(t["shaded_plaster_L"] - target))
    cv = set_view(cam, a.res)
    png = os.path.join(out, "m0w-clay.png")
    FF.render_beauty(png, os.path.join(tmp, "b"), cv["W"], cv["H"], a.samples, 0.30, best["exposure"])
    Image.open(png).save(png, optimize=True)
    Lc = cv2.cvtColor(np.asarray(Image.open(png).convert("RGB")).astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[..., 0]
    meas = {}
    for k, msk in (("shaded plaster", (idx_full == 5) & (sun_full < 0.02) & (cv2.resize(sc_full, (cv["W"], cv["H"])) < 0.15)),
                   ("sunlit plaster", (idx_full == 5) & (sun_full > 0.5)), ("pendant shade", idx_full == PROD_IDX["pendant"]),
                   ("floor-lamp shade", (idx_full == PROD_IDX["floor-lamp"]) & (Lc > 60)), ("black p0.5", np.ones_like(sun_full, bool))):
        if msk.any():
            meas[k] = round(float(np.percentile(Lc[msk], 0.5 if k == "black p0.5" else 50)), 1)
    set_lamps(set())
    hide_products(True)
    mh = int(round(a.map_res * CANVAS[1] / CANVAS[0]))
    pp = os.path.join(out, "m0w-clay-plate.png")
    set_view(cam, a.map_res)
    FF.render_beauty(pp, os.path.join(tmp, "b"), a.map_res, mh, a.samples, 0.30, best["exposure"])
    Image.open(pp).save(pp, optimize=True)
    hide_products(False)
    set_lamps(set(LAMPS))
    cv = set_view(cam, a.res)
    rows = rec["v7q6"]
    sun_n = sun_full
    # the olive's leaf shadow again (the sun map without the crown), for the overlay
    sun = FF.LIGHTS["sun"]
    set_lamps(set())
    others = [o for o in bpy.data.objects if o.type == "LIGHT" and o is not sun and not o.hide_render]
    for o in others + OBJS["olive (filler)"]:
        o.hide_render = True
    try:
        sno = lum(render_linear(tmp, cv["W"], cv["H"], 8, bounces=0, sky=0.0, override=True))
    finally:
        for o in others + OBJS["olive (filler)"]:
            o.hide_render = False
        set_lamps(set(LAMPS))
    sno = np.clip(sno / rec["sun_map"]["ref_linear"], 0, 1)
    osh = (idx_full == 5) & (sno > 0.10) & (sun_n < 0.6 * sno)
    osh = cv2.morphologyEx(osh.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    overlay(os.path.join(out, "m0w-overlay.jpg"), np.asarray(Image.open(png).convert("RGB")), rows, cv, sun_n, osh, rec["lamp_geometry"], 0.5)
    rec["exposure_calibration"] = dict(target_shaded_plaster_L=target, tries=tries, chosen=best["exposure"], measured_full_res=meas,
                                       note="AgX Medium High Contrast; the clay's materials are clay greys, so the lamp shades and the black point are "
                                            "readings of the clay, not of the finished frame (G1.10 is for the render)")
    rec["render"] = rec["render"].replace(f"exposure {fa.door_exposure}", f"exposure {best['exposure']} (calibrated, see exposure_calibration)")
    json.dump(rec, open(jp, "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(W4.r4.EXR_DIR, ignore_errors=True)
    print("BEAUTY", best, meas, flush=True)


def args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=CANVAS[0])
    ap.add_argument("--map-res", type=int, default=1360)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--quick", action="store_true", help="write to the scratchpad only")
    ap.add_argument("--beauty-only", action="store_true", help="re-render only m0w-clay.png and m0w-clay-plate.png at a calibrated exposure "
                    "(the shaded plaster at L* 74, the proposal's 70-78), the basket where clay-m0w.json put it")
    ap.add_argument("--out", default=HERE)
    return ap.parse_args(argv)


def main(argv):
    a = args(argv)
    out = os.path.join(SCR, "quick") if a.quick else a.out
    os.makedirs(out, exist_ok=True)
    os.makedirs(SCR, exist_ok=True)
    W4.r4.EXR_DIR = os.path.join(SCR, "exr")
    t0 = time.time()
    fa = FF.args([])
    fa.res = a.res
    S, R, cfg, notes = FF.build(fa)
    shell_idx = {k: int(v) for k, v in D.ba.SHELL_IDX.items()}
    sol = solve_olive()
    planter_c = tuple(sol["crown_centre"][:2])
    basket_c = BASKET_CANDIDATES[0]
    ch = sofa_m0w() + olia() + products(planter_c, basket_c) + lamps()
    # the sun: D0's sun in the tool compass, altitude 15
    sun = FF.LIGHTS["sun"]
    sun.data.energy = SUN["strength"]
    sun.rotation_quaternion = (-tool_sun_vector(SUN["az"], SUN["alt"])).to_track_quat("-Z", "Y")
    ch.append(f"sun: az {SUN['az']} alt {SUN['alt']} in the tool compass; toward the sun {[round(v, 4) for v in tool_sun_vector(SUN['az'], SUN['alt'])]}")
    ch += FF.move_olive((-5.4, -1.6))                       # D0's garden olive, moved outside the living glazing (seen in back light)
    bpy.context.view_layer.update()
    print("BUILD", round(time.time() - t0), "s", *ch, sep="\n  ", flush=True)
    cam = S["cam"]
    if a.beauty_only:
        return beauty_only(a, out, cam, fa)
    tmp = tempfile.mkdtemp(prefix="m0w-", dir=SCR)
    rec = dict(stage="FB13 stage 0: the M0-W clay and light map (render-agent, 2026-11-25; docs/proposals/wm-fb13-living-wow-2026-11-25.md 3.1-3.2); "
                     "0 var2 tokens", camera=CAM, canvas=dict(px=list(CANVAS), frame_box=list(FRAME_BOX)), sun=SUN, tool_compass=TOOL_COMPASS,
               house_compass_sun_toward=[round(v, 4) for v in house_sun_vector(SUN["az"], SUN["alt"])], olive_solve=sol, build=ch,
               shell_pass_index=shell_idx, product_pass_index=PROD_IDX, filler_pass_index=FILLER_IDX)
    # 0. the basket: the grid sweep on the analytic silhouettes, then the clay takes the clear point nearest the proposal's expectation
    cv = set_view(cam, a.res)
    margin = int(0.5 * cv["W"])
    sweep = basket_sweep(cv, margin, planter_c)
    rec["basket_sweep"] = {k: v for k, v in sweep.items() if k != "all"}
    json.dump(sweep, open(os.path.join(SCR, "basket-sweep-all.json"), "w"), indent=1)
    if sweep["best"]:
        basket_c = tuple(sweep["best"][0]["at"])
        OBJS["basket"][0].location = (basket_c[0], basket_c[1], OBJS["basket"][0].location.z)
        bpy.context.view_layer.update()
    rec["basket_in_clay"] = list(basket_c)
    print("SWEEP", sweep["tested"], "tested,", sweep["clear"], "clear; basket at", basket_c, flush=True)
    # 1. geometry at the full canvas
    depth, idx, normal = D.geometry_pass(tmp, cv["W"], cv["H"])
    np.savez_compressed(os.path.join(SCR, "m0w-passes.npz"), depth=depth.astype(np.float32), idx=idx.astype(np.int32))
    dsurf = (depth > 0) & (depth < 1e3) & (idx != 0)
    dn, dfar = float(depth[dsurf].min()), float(np.percentile(depth[dsurf], 99.9))
    enc = np.zeros(depth.shape, np.uint16)
    dd = np.clip(depth[dsurf], dn, dfar)
    enc[dsurf] = np.rint(1 + 65534 * (1 / dd - 1 / dfar) / (1 / dn - 1 / dfar)).astype(np.uint16)
    Image.fromarray(enc).save(os.path.join(out, "m0w-depth.png"), optimize=True)
    json.dump(dict(file="m0w-depth.png", size=[cv["W"], cv["H"]], encoding="uint16 grey, near = bright, linear in 1/depth: value = 1 + 65534 * "
                   "(1/d - 1/d_far) / (1/d_near - 1/d_far); 0 = no surface (the view out through the glazing). d = planar depth, metres (as depth.json)",
                   d_near_m=dn, d_far_m=dfar, camera=CAM, frame_box=[FRAME_BOX[0] * cv["W"] / CANVAS[0], FRAME_BOX[1] * cv["H"] / CANVAS[1],
                                                                     FRAME_BOX[2] * cv["W"] / CANVAS[0], FRAME_BOX[3] * cv["H"] / CANVAS[1]],
                   covers="the M0-W clay with every product proxy (the depth of the finishing code's depth of field, and of motion-agent's work)",
                   note="clay depth, not edge-snapped to an image (no M0-W image exists yet)"),
              open(os.path.join(out, "m0w-depth.json"), "w"), indent=1)
    rec["ids_palette"] = ids_png(os.path.join(out, "m0w-ids.png"), idx, shell_idx)
    # the projection check: Blender against the plan's equations
    from bpy_extras.object_utils import world_to_camera_view
    errs = []
    sc = bpy.context.scene
    for p in [(-0.90, 0.95, 0.0), (1.30, 0.95, 0.78), (0.20, 1.72, 1.90), (-2.30, 0.75, 2.70), (-0.85, 0.0, 1.75)]:
        q = world_to_camera_view(sc, cam, Vector(p))
        u, v, _ = plan_uv(*p)
        errs.append(max(abs(q.x * cv["W"] - (cv["ox"] + u * cv["fx"])), abs((1 - q.y) * cv["H"] - (cv["oy"] + v * cv["fy"]))))
    rec["projection_check_px"] = round(max(errs), 3)
    # 2. measurements
    rows, f3, pend, glaz, frame = measure(idx, depth, cv, margin)
    rec["v7q6"] = rows
    rec["v7q6_counted"] = sum(1 for r in rows.values() if r.get("v7q6") == "counted")
    rec["f3"] = [p for p in f3 if p["verdict"].startswith(("FAIL", "decisive", "clear"))]
    rec["f3_fails"] = [p for p in f3 if p["verdict"].startswith("FAIL")]
    rec["pendant"] = pend
    rec["glazing"] = glaz
    # the pendant's clearance under the top edge, and the v0 that gives 0.02 (the drum's top rim, nearest point)
    th = np.linspace(0, 2 * np.pi, 360)
    pu, pv, _ = plan_uv(0.20 + 0.25 * np.cos(th), 1.72 + 0.25 * np.sin(th), np.full(360, 2.18))
    rec["pendant"]["top_clearance_v"] = round(float(pv.min()), 4)
    rec["pendant"]["v0_for_0.02_clearance"] = round(CAM["v0"] + 0.02 - float(pv.min()), 4)
    rec["olive_as_is"] = dict(planter=[-1.95, 0.42], crown_centre_shadow_alt15=shadow_of([-1.95, 0.42, 1.175], SUN["alt"]),
                              note="the r4 planter (-1.95, 0.42) with its r4 crown (Z 0.70-1.65): where its shadow would fall")
    print("MEASURED", rec["v7q6_counted"], "counted;", len(rec["f3_fails"]), "F3 fails; projection", rec["projection_check_px"], "px", flush=True)
    # 3. sun maps (direct sun only, white override: incidence x visibility), with and without the olive crown
    set_lamps(set())
    hide_others = [o for o in bpy.data.objects if o.type == "LIGHT" and o is not sun and not o.hide_render]
    for o in hide_others:
        o.hide_render = True
    try:
        sun_l = lum(render_linear(tmp, cv["W"], cv["H"], 8, bounces=0, sky=0.0, override=True))
        for o in OBJS["olive (filler)"]:
            o.hide_render = True
        sun_no_olive = lum(render_linear(tmp, cv["W"], cv["H"], 8, bounces=0, sky=0.0, override=True))
        for o in OBJS["olive (filler)"]:
            o.hide_render = False
        sun.rotation_quaternion = (-tool_sun_vector(SUN["az"], SUN["alt_d0"])).to_track_quat("-Z", "Y")
        sun21 = lum(render_linear(tmp, a.map_res, int(round(a.map_res * CANVAS[1] / CANVAS[0])), 8, bounces=0, sky=0.0, override=True))
        sun.rotation_quaternion = (-tool_sun_vector(SUN["az"], SUN["alt"])).to_track_quat("-Z", "Y")
    finally:
        for o in hide_others:
            o.hide_render = False
    ref = float(np.percentile(sun_l[sun_l > 1e-6], 99)) if (sun_l > 1e-6).any() else 1.0
    sun_n = np.clip(sun_l / ref, 0, 1)
    Image.fromarray(np.rint(sun_n * 255).astype(np.uint8)).save(os.path.join(out, "m0w-sun.png"), optimize=True)
    s21 = np.clip(sun21 / ref, 0, 1)
    Image.fromarray(np.rint(s21 * 255).astype(np.uint8)).save(os.path.join(out, "m0w-sun-alt21-d0.png"), optimize=True)
    sno = np.clip(sun_no_olive / ref, 0, 1)
    back = idx == shell_idx.get("back-wall", -1)
    oshadow = back & (sno > 0.10) & (sun_n < 0.6 * sno)
    oshadow = cv2.morphologyEx(oshadow.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    rec["sun_map"] = dict(file="m0w-sun.png", ref_linear=ref, note="direct sun only (no sky, no lamp, no bounce), every surface white diffuse "
                          "(incidence x visibility), linear luminance / its 99th percentile, 8 bit; > 13 (0.05) = in direct sun",
                          alt21_file="m0w-sun-alt21-d0.png (D0's own altitude 21, the same reference; 1360 wide)")
    rec["sun_geometry"] = sun_geometry(sun_n, idx, depth, cv, shell_idx, oshadow)
    s21_full = cv2.resize(s21, (cv["W"], cv["H"]), interpolation=cv2.INTER_LINEAR)
    rec["sun_geometry_alt21"] = sun_geometry(s21_full, idx, depth, cv, shell_idx)
    # 4. lamp maps (each lamp alone; no sun, no sky; bounces on; white override: the light's distribution, not albedo)
    sun.hide_render = True
    winl = [o for o in bpy.data.objects if o.type == "LIGHT" and not o.name.startswith("m0w_") and not o.hide_render]
    for o in winl:
        o.hide_render = True
    maps = {}
    mh = int(round(a.map_res * CANVAS[1] / CANVAS[0]))
    try:
        for k in LAMPS:
            set_lamps({k}, glow=False)
            L = lum(render_linear(tmp, a.map_res, mh, a.samples, sky=0.0, override=True))
            maps[k] = L
            r99 = float(np.percentile(L, 99.5)) if L.max() > 0 else 1.0
            save16(os.path.join(out, f"m0w-light-{k}.png"), L, r99)
            LAMPS[k]["map_ref_linear"] = r99
    finally:
        for o in winl:
            o.hide_render = False
        sun.hide_render = False
    rec["lamps"] = {k: dict(note=v["note"], at=v["at"], map=f"m0w-light-{k}.png", map_ref_linear=v.get("map_ref_linear")) for k, v in LAMPS.items()}
    rec["lamp_geometry"] = lamp_geometry(maps, idx, depth, cv)
    # 5. the clay, lit: sun + sky + every lamp
    set_lamps(set(LAMPS))
    png = os.path.join(out, "m0w-clay.png")
    FF.render_beauty(png, os.path.join(tmp, "b"), cv["W"], cv["H"], a.samples, 0.30, fa.door_exposure)
    Image.open(png).save(png, optimize=True)
    # 6. the plate reading (P-W): the empty room in the same sun, lamps off, no product
    set_lamps(set())
    hide_products(True)
    png_p = os.path.join(out, "m0w-clay-plate.png")
    FF.render_beauty(png_p, os.path.join(tmp, "b"), a.map_res, mh, a.samples, 0.30, fa.door_exposure)
    Image.open(png_p).save(png_p, optimize=True)
    hide_products(False)
    set_lamps(set(LAMPS))
    clay = np.asarray(Image.open(png).convert("RGB"))
    overlay(os.path.join(out, "m0w-overlay.jpg"), clay, rows, cv, sun_n, oshadow, rec["lamp_geometry"], 0.5)
    v = rec["v7q6"]
    camp = dict(status="PROPOSAL (FB13, render-agent 2026-11-25): not in docs/house-plan.json; for the master-designer and the owner (Q1-b)",
                camera=dict(id="M0-W", loc=CAM["loc"], yaw_deg_left=CAM["yaw"], lens=CAM["lens"], u0=CAM["u0"], v0=CAM["v0"], level=True),
                replaces=dict(id="M0", loc=[0.83, 4.64, 1.20], yaw_deg_left=25, lens=24, u0=0.47, v0=0.50, source="house-plan.json 1.2"),
                projection=f"u = u0 + {K_U:.4f} x / d; v = v0 + {K_V:.4f} (1.05 - z) / d (house-plan conventions.projection with 35 mm)",
                canvas=dict(px=list(CANVAS), frame_box=list(FRAME_BOX), note="the living-room tool canvas (base.png); the 16:9 frame inside it"),
                sun=dict(SUN, compass=TOOL_COMPASS, toward_sun=[round(x_, 4) for x_ in tool_sun_vector(SUN["az"], SUN["alt"])]),
                measured_on_the_clay=dict(sofa_u=v["fixed:sofa"].get("u"), sofa_width_share=round(v["fixed:sofa"]["u"][1] - v["fixed:sofa"]["u"][0], 3),
                                          table_u=v["coffee-table"].get("u"), art_centre_u=round(sum(v["framed-art"]["u"]) / 2, 4),
                                          pendant=rec["pendant"], armchair_u=v["fixed:armchair"].get("u"), glazing=rec["glazing"],
                                          v7q6_counted=rec["v7q6_counted"], f3_fails=len(rec["f3_fails"])),
                expected_by_the_proposal=dict(sofa_u=[0.36, 0.82], art_centre_u=0.60, table_u=[0.43, 0.73], pendant="whole under the top edge",
                                              ceiling="out", glazing="a third, with the bench and the vase, at the left edge"),
                files="clay-m0w.json (everything), m0w-clay.png, m0w-overlay.jpg")
    json.dump(camp, open(os.path.join(out, "camera-m0w-proposal.json"), "w"), indent=1, ensure_ascii=False)
    rec["files"] = sorted(f for f in os.listdir(out) if f.startswith("m0w-"))
    rec["render"] = (f"Cycles CPU (framing_wm_door_final defaults: seed 7, OIDN, AgX Medium High Contrast, exposure {fa.door_exposure}, sky {fa.sky}), "
                     f"{a.samples} samples; clay {cv['W']} x {cv['H']}; maps {a.map_res} wide")
    rec["runtime_s"] = round(time.time() - t0)
    json.dump(rec, open(os.path.join(out, "clay-m0w.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(W4.r4.EXR_DIR, ignore_errors=True)
    print("DONE", rec["runtime_s"], "s", flush=True)


if __name__ == "__main__":
    main(_MY_ARGV)
