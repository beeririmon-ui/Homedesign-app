#!/usr/bin/env python3
"""
framing_wm_master.py: the warm-modern MASTER BEDROOM as a clay, frame MB0 (the bed wall), render-agent, 2026-11-17. 0 var2 tokens.
Brief: briefs/wm-master-stage1-render-2026-11-17.md, step 1. Spec: master-designer docs/proposals/wm-master-bedroom-render-2026-11-17.md,
chapter 12 over the earlier chapters; chapters 1 (architecture), 2 (the fixed walnut bed and nightstands), 3.2 + 12.2 (the defaults),
6.2-6.8 (camera, frame, light, placement, fillers), 7 (rejection list), 9 (what QA checks).

The scene is the round-4 house clay (framing_r4.py, imported, nothing changed there; house plan 1.1) with the master rebuilt by
wm_master(), wm_fixed() and wm_products():
  - plaster #ECE5DA as 1 mm skins on the four walls, the window reveals and a rounded corner R 0.20 (bed wall / window wall);
    skirting 15 in the wall colour, 1.5 proud (WMC10), following the curve; no G-M4 wainscot, no cornice; ceiling 3.00 with a 1 cm
    shadow gap and a curtain slot over the window;
  - smoked oak #8B6F55 in 22 cm planks along Y (toward the bed wall), staggered end joints, 1.5 mm gaps;
  - W-master in the 1.1 opening (sill 0.75, head 2.70, Y 18.10-19.60): bronze-espresso #3A322C steel, 45 mm sight lines, two equal
    vertical panes, no transom, at the outer face; plaster-wrapped reveals; a 4 cm honed limestone #D8C8AE slab on the sill, 2 cm proud;
  - the corridor door leaf in the wall colour (parked inside, 1.1 G-M1), walnut linings in both openings (out of MB0);
  - chapter 2: the walnut #6B4A33 bed (headboard 180 x 115 x 5, top corners R 12; frame Z 0.06-0.28 flush with the mattress, foot
    corners R 4; recessed dark plinth 6, set back 8; bone mattress #E6DFD3 Z 0.28-0.50, soft corners) and two nightstands 45 x 40 x 55
    (vertical corners R 4, 3 cm top, two drawers with a 4 mm shadow groove and 15 mm finger recesses, recessed plinth 6 set back 4);
  - the defaults of 3.2 with 12.2 as boxes at their slot envelopes: bedding V1, two caramel pillows lying flat, the milk-tea boucle
    lumbar, the Pecan throw folded at the foot, the travertine cone pair on walnut plates (lit), the travertine pedestal pair with
    candles, the walnut tray with the sand bottle and the travertine dish, the fluted column on the sill, the S-fold curtain stacks,
    the pleated floor lamp 43 (lit). Empty: framed-art, planter, bedside-carafe; out of frame: rug, basket, pendant.
Frames (camera MB0 from docs/house-plan.json: (-0.70, 21.05, 1.05), yaw 0, 24 mm, u0 0.50, v0 0.46; the base.png canvas 2720 x 1530
with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57], the round-4 3 % overscan):
  MB0         the defaults clay: shell + fixed furniture + the defaults; the sconce pair and the floor lamp lit
  MB0-plate   the empty plate: shell + bed + nightstands, every product hidden, every lamp off
  MB0-shell   the shell alone (no bed, no nightstands): plate / shell is the fixed-furniture shadow (RND2, as the living room)
Per frame: <id>.png (toned clay), <id>-depth.png (16 bit, planar, metres = value / 5000, 65535 = nothing), <id>-id.png (palette;
legend in selfcheck.json), <id>-edges.png (structure edges). selfcheck.json: the 6.3 numbers, M-HC1..5, lamps, boxes.
lock-target.json: the named lines in canvas pixels for the stills' lock.

  python3 framing_wm_master.py --frames MB0-plate,MB0,MB0-shell --samples 16
  python3 framing_wm_master.py --frames MB0 --res 960 --samples 4 --out /tmp/x          # smoke test
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
_ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]

import framing_r4 as r4  # noqa: E402  (the round-4 house)

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

r3, r2, fr, bh, M = r4.r3, r4.r2, r4.fr, r4.bh, r4.M
bs, ba = r3.bs, r3.ba
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-master"
OUT = os.path.join(HERE, "framing", "wm-master-2026-11-17")
r4.EXR_DIR = os.path.join(SCR, "exr")
CANVAS = (2720, 1530)
K = r4.OS_K
FRAME_BOX = (0.5 * CANVAS[0] * (1 - 1 / K), 0.5 * CANVAS[1] * (1 - 1 / K), 0.5 * CANVAS[0] * (1 + 1 / K), 0.5 * CANVAS[1] * (1 + 1 / K))
DEPTH_UNITS = 5000.0
CAM = dict(loc=(-0.70, 21.05, 1.05), yaw=0.0)

# ---- chapter 1 / 2 / 6 values -----------------------------------------------------------------------------------
HEX = dict(plaster="#ECE5DA", oak="#8B6F55", oak_l="#917559", oak_d="#85694F", gap="#2B2724", walnut="#6B4A33", plinth="#3A2A1F",
           mattress="#E6DFD3", stone="#D8C8AE", bronze="#3A322C", recess="#2E2119",
           duvet="#CDBFA8", pillow="#A8714A", cushion="#E3D8C6", throw="#9A6440", trav="#D9C8AE", arm="#1E1C1B", candle="#EFE6D6",
           tray="#5E4130", bottle="#D6C3A3", dish="#DCCBAF", column="#EFE8D8", curtain="#E6DDCC", shade="#EEE5D3", brass="#B8955A",
           stem="#C9B48F", sage="#8A9A7B", lampwal="#5B3F2C")
ROOM = dict(x=(-2.30, 3.10), y=(17.66, 21.66), h=3.00)
SKIN = 0.001
SK = dict(h=0.15, proud=0.015)                                  # skirting 15, 1.5 proud, wall colour (WMC10)
CORNER = dict(c=(-2.10, 17.86), r=0.20)                         # [MB-2] the rounded corner, tangent at X -2.30 / Y 17.66
WIN = dict(y=(18.10, 19.60), sill=0.75, head=2.70, x_out=-2.65, frame_d=0.04, sight=0.045, slab_t=0.04, slab_proud=0.02)
DOOR = dict(x=(2.00, 2.90), head=2.40)
ENSUITE = dict(y=(19.70, 20.60), head=2.40)
BED = dict(x=(-1.60, 0.20), y=(17.66, 19.66), head_t=0.05, head_h=1.15, head_r=0.12, frame=(0.06, 0.28), frame_r=0.04,
           mat=(0.28, 0.50), plinth_set=0.08)
NS = dict(xs=((-2.10, -1.65), (0.25, 0.70)), y=(17.66, 18.06), h=0.55, r=0.04, top_t=0.03, plinth=0.06, plinth_set=0.04,
          groove=0.004, recess=0.015)
SCONCE = dict(plates=((-1.875, 17.66, 1.34), (0.475, 17.66, 1.34)), plate_r=0.055, plate_t=0.018, axis_y=17.775, cone_r=0.075,
              cone_top_r=0.012, cone_z=(1.19, 1.34))
LAMP = dict(c=(0.95, 18.25), base_r=0.14, stem_r=0.012, shade=(1.28, 1.58), shade_r=(0.215, 0.11), collar=(1.22, 1.29))
CURTAIN = dict(stacks=((17.88, 18.10), (19.60, 19.82)), n=6, r=0.035, x=(-2.255, -2.215), z=(0.12, 2.82))
LIGHT = dict(window=6.0, sconce_spot_w=30.0, sconce_spot_deg=100.0, sconce_point_w=5.0, sconce_glow=4.0, lamp_point_w=45.0,
             lamp_area_w=30.0, lamp_glow=5.0, plate_target_Lstar=87.5)

IDS = {0: "nothing / sky", 1: "plaster, bed wall (Y 17.66)", 2: "plaster, window wall (X -2.30)", 3: "plaster, west wall (Y 21.66)",
       4: "plaster, south wall (X 3.10)", 5: "plaster, rounded corner R 0.20", 6: "ceiling", 7: "ceiling shadow gap (1 cm)",
       8: "curtain slot in the ceiling", 9: "skirting 15, wall colour", 10: "floor, smoked oak planks 22", 11: "floor joints (1.5 mm)",
       12: "window reveals, plaster", 13: "window frame, bronze-espresso", 14: "sill slab, limestone 4 cm", 15: "outside (ground)",
       16: "door leaf / walnut linings (out of MB0)",
       20: "bed headboard, walnut", 21: "bed frame, walnut", 22: "bed plinth, dark", 23: "mattress, bone",
       24: "nightstand carcass + drawer fronts, walnut", 25: "nightstand top, walnut", 26: "nightstand groove / finger recesses",
       27: "nightstand plinth, dark",
       40: "curtains (product)", 41: "sill-vase (product)", 42: "sill stem (filler)", 43: "bedside-sconces, west (product)",
       44: "bedside-sconces, east (product)", 45: "nightstand-tray (product)", 46: "nightstand-vase (product)", 47: "oat stems (filler)",
       48: "trinket-dish (product)", 49: "candle-holders (product)", 50: "candles (filler)", 51: "pillowcases (product)",
       52: "bedding (product)", 53: "cushions (product)", 54: "throw (product)", 55: "floor-lamp (product)", 90: "other house geometry",
       99: "unknown"}
PAL = {0: (0, 0, 0), 1: (236, 229, 218), 2: (214, 205, 192), 3: (196, 188, 178), 4: (180, 172, 160), 5: (225, 215, 200),
       6: (245, 241, 233), 7: (40, 36, 34), 8: (90, 60, 30), 9: (200, 190, 175), 10: (139, 111, 85), 11: (60, 45, 35), 12: (230, 220, 205),
       13: (58, 50, 44), 14: (216, 200, 174), 15: (120, 140, 120), 16: (150, 110, 80),
       20: (107, 74, 51), 21: (140, 100, 70), 22: (58, 42, 31), 23: (230, 223, 211), 24: (120, 84, 58), 25: (160, 115, 80),
       26: (30, 20, 15), 27: (70, 50, 38),
       40: (255, 120, 120), 41: (255, 180, 60), 42: (60, 140, 60), 43: (255, 255, 0), 44: (200, 255, 0), 45: (0, 200, 120),
       46: (0, 160, 255), 47: (120, 120, 255), 48: (200, 0, 200), 49: (255, 0, 120), 50: (250, 240, 200), 51: (168, 113, 74),
       52: (205, 191, 168), 53: (227, 216, 198), 54: (154, 100, 64), 55: (255, 150, 0), 90: (60, 60, 60), 99: (255, 0, 255)}
PRODUCT_IDS = set(range(40, 56))
FILLER_IDS = {42, 47, 50}
ARCH_IDS = set(range(1, 17))
FIXED_IDS = set(range(20, 28))
GROUP_ID = {}
PRODUCTS = ["curtains", "sill-vase", "bedside-sconces", "nightstand-tray", "nightstand-vase", "trinket-dish", "candle-holders",
            "pillowcases", "bedding", "cushions", "throw", "floor-lamp"]
FILLERS = ["master/sill-vase-filler", "master/nightstand-vase-filler", "master/candle-holders-filler"]
FRAMES = {"MB0": dict(placeholders=PRODUCTS, lamps=["master/bedside-sconces", "master/floor-lamp"], also=FILLERS, fixed=True),
          "MB0-plate": dict(placeholders=[], lamps=[], fixed=True),
          "MB0-shell": dict(placeholders=[], lamps=[], fixed=False)}
CAPTURE = {}


def mat(name, key, rough=0.9):
    return fr.mat_cache("wm_master_" + name, HEX[key], rough)


def reg_arch(name, objs, gid, kind="architecture"):
    objs = [o for o in objs if o is not None]
    r2.reg(name, objs, "master", kind)
    GROUP_ID[name] = gid
    return objs


def reg_prod(R, slot, objs, gid, src):
    r3.reg(R, f"master/{slot}", objs, "master", src=src)
    GROUP_ID[f"master/{slot}"] = gid
    return objs


def bx(n, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    return r3.bx("mb_wm_" + n, x0, x1, y0, y1, z0, z1, m, bevel)


def cyl(n, c, r, z0, z1, m, verts=48):
    return r3.cyl("mb_wm_" + n, c, r, z0, z1, m, verts)


def cone(n, c, r0, r1, z0, z1, m, verts=48):
    return r3.cone("mb_wm_" + n, c, r0, r1, z0, z1, m, verts)


def mesh_obj(name, verts, faces, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(m)
    bs.coll("framing").objects.link(ob)
    return ob


def ccw(pts):
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if area > 0 else pts[::-1]


def prism(name, loop, axis, a0, a1, m):
    """Closed prism from a 2D loop. axis 'z': loop in (x, y); 'y': loop in (x, z); 'x': loop in (y, z)."""
    loop = ccw(list(loop))
    n = len(loop)

    def P(p, a):
        if axis == "z":
            return (p[0], p[1], a)
        if axis == "y":
            return (p[0], a, p[1])
        return (a, p[0], p[1])
    v = [P(p, a0) for p in loop] + [P(p, a1) for p in loop]
    f = [list(range(n))[::-1], list(range(n, 2 * n))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return mesh_obj(name, v, f, m)


def arc(c, r, a0, a1, seg=16):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / seg)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / seg)))
            for k in range(seg + 1)]


def rrect_xy(x0, x1, y0, y1, r, corners=(True, True, True, True), seg=10):
    """Rounded rectangle; corners = (x0y0, x1y0, x1y1, x0y1)."""
    pts = []
    spec = [((x0, y0), (x0 + r, y0 + r), 180), ((x1, y0), (x1 - r, y0 + r), 270), ((x1, y1), (x1 - r, y1 - r), 0), ((x0, y1), (x0 + r, y1 - r), 90)]
    for (pt, c, a), on in zip(spec, corners):
        if on:
            pts += arc(c, r, a, a + 90, seg)
        else:
            pts.append(pt)
    return pts


def kill_names(prefixes=(), exact=()):
    objs = [o for o in bpy.data.objects if o.name in exact or any(o.name.startswith(p) for p in prefixes)]
    return r2.kill_objs(objs)


# ---------------------------------------------------------------------------------------------------------------
# chapter 1: the architecture
# ---------------------------------------------------------------------------------------------------------------
def wm_master(R):
    notes = []
    n = kill_names(prefixes=("wsc", "master_cornice", "master_plank", "master_skirt", "W-master_", "m_rod", "mbed_", "mns_"))
    for key in ("G-M4 wainscot", "master bed 180x200", "nightstands 45"):
        if key in fr.REG:
            fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if r3.alive(o)]
    for key in [k for k in list(R) if k.startswith("master/")]:
        r3.kill_group(R, key)
    for key in ("master/bedside-sconces", "master/floor-lamp", "master/pendant"):
        r3.lamp_off(key)
    notes.append(f"removed {n} objects of the 1.1 master (G-M4 wainscot, cornice, planks 25, skirting, the 1.1 window frame, sashes, "
                 "mullion, reveals and sill board, the rod, the 1.1 bed and nightstands) and every master product proxy; master lamps off")
    x0, x1 = ROOM["x"]
    y0, y1 = ROOM["y"]
    H = ROOM["h"]
    pl, gp = mat("plaster", "plaster", 0.95), mat("gap", "gap", 0.9)
    wal, st, bz = mat("walnut", "walnut", 0.7), mat("stone", "stone", 0.75), mat("bronze", "bronze", 0.55)
    yb = y0 + SKIN                                            # bed-wall skin: room face at Y 17.662
    xw = x0 + SKIN                                            # window-wall skin: room face at X -2.298
    cx, cy = CORNER["c"]
    sh = SK["h"]
    wy0, wy1 = WIN["y"]
    slab_z0 = WIN["sill"] - WIN["slab_t"]
    # ---- plaster skins ----
    reg_arch("mb_wm plaster bed wall", [r3.bx("mb_wm_pl_e_a", cx, DOOR["x"][0], yb, yb + 0.001, sh, H, pl),
                                        r3.bx("mb_wm_pl_e_b", DOOR["x"][0], DOOR["x"][1], yb, yb + 0.001, DOOR["head"], H, pl),
                                        r3.bx("mb_wm_pl_e_c", DOOR["x"][1], x1, yb, yb + 0.001, sh, H, pl)], 1)
    reg_arch("mb_wm plaster window wall", [r3.bx("mb_wm_pl_n_a", xw, xw + 0.001, cy, wy0, sh, H, pl),
                                           r3.bx("mb_wm_pl_n_b", xw, xw + 0.001, wy0, wy1, sh, slab_z0, pl),
                                           r3.bx("mb_wm_pl_n_c", xw, xw + 0.001, wy0, wy1, WIN["head"], H, pl),
                                           r3.bx("mb_wm_pl_n_d", xw, xw + 0.001, wy1, y1, sh, H, pl)], 2)
    reg_arch("mb_wm plaster west wall", [r3.bx("mb_wm_pl_w", x0, x1, y1 - SKIN - 0.001, y1 - SKIN, sh, H, pl)], 3)
    xs = x1 - SKIN
    reg_arch("mb_wm plaster south wall", [r3.bx("mb_wm_pl_s_a", xs - 0.001, xs, y0, ENSUITE["y"][0], sh, H, pl),
                                          r3.bx("mb_wm_pl_s_b", xs - 0.001, xs, ENSUITE["y"][0], ENSUITE["y"][1], ENSUITE["head"], H, pl),
                                          r3.bx("mb_wm_pl_s_c", xs - 0.001, xs, ENSUITE["y"][1], y1, sh, H, pl)], 4)
    # ---- the rounded corner R 0.20: a curved skin (room face r 0.198) and its skirting (face r 0.183) ----
    rf = CORNER["r"] - 2 * SKIN
    shell = arc((cx, cy), rf, 180, 270, 24) + arc((cx, cy), CORNER["r"] + 0.03, 270, 180, 24)
    reg_arch("mb_wm plaster corner R 0.20", [prism("mb_wm_corner", shell, "z", sh, H, pl)], 5)
    # ---- skirting 15, 1.5 proud, wall colour; the corner piece follows the curve ----
    p = SK["proud"]
    skirt = [r3.bx("mb_wm_sk_e_a", cx, DOOR["x"][0], y0, yb + p, 0.0, sh, pl), r3.bx("mb_wm_sk_e_b", DOOR["x"][1], x1, y0, yb + p, 0.0, sh, pl),
             r3.bx("mb_wm_sk_n", x0, xw + p, cy, y1, 0.0, sh, pl), r3.bx("mb_wm_sk_w", x0, x1, y1 - SKIN - p, y1, 0.0, sh, pl),
             r3.bx("mb_wm_sk_s_a", xs - p, x1, y0, ENSUITE["y"][0], 0.0, sh, pl), r3.bx("mb_wm_sk_s_b", xs - p, x1, ENSUITE["y"][1], y1, 0.0, sh, pl),
             prism("mb_wm_sk_corner", arc((cx, cy), CORNER["r"] - 2 * SKIN - p, 180, 270, 24) + arc((cx, cy), CORNER["r"] + 0.03, 270, 180, 24),
                   "z", 0.0, sh, pl)]
    reg_arch("mb_wm skirting 15 (wall colour)", skirt, 9)
    # ---- ceiling 3.00 (kept): 1 cm shadow gap and the curtain slot over the window ----
    cz = H - 0.0005
    reg_arch("mb_wm ceiling shadow gap", [r3.bx("mb_wm_cg_e", x0, x1, y0, y0 + 0.01, cz - 0.0005, cz, gp),
                                          r3.bx("mb_wm_cg_n", x0, x0 + 0.01, y0, y1, cz - 0.0005, cz, gp),
                                          r3.bx("mb_wm_cg_w", x0, x1, y1 - 0.01, y1, cz - 0.0005, cz, gp),
                                          r3.bx("mb_wm_cg_s", x1 - 0.01, x1, y0, y1, cz - 0.0005, cz, gp)], 7)
    reg_arch("mb_wm curtain slot", [r3.bx("mb_wm_slot", x0 + 0.03, x0 + 0.14, cy, 19.86, cz - 0.0006, cz, gp)], 8)
    # ---- floor: smoked oak 22 cm planks along Y, staggered, 1.5 mm gaps (the dark base below shows in the gaps) ----
    rng = np.random.default_rng(17)
    oaks = [mat("oak", "oak", 0.8), mat("oak_l", "oak_l", 0.8), mat("oak_d", "oak_d", 0.8)]
    planks = []
    W, g = 0.22, 0.0015
    xk, k = x0, 0
    while xk < x1 - 0.005:
        xa, xb = xk + g / 2, min(xk + W, x1) - g / 2
        yk = y0 - rng.uniform(0.2, 1.8)
        j = 0
        while yk < y1:
            L = rng.uniform(1.3, 2.5)
            ya, yb_ = max(yk, y0) + g / 2, min(yk + L, y1) - g / 2
            if yb_ - ya > 0.05:
                planks.append(r3.bx(f"mb_wm_pk{k}_{j}", xa, xb, ya, yb_, -0.012, 0.0, oaks[int(rng.integers(0, 3))]))
            yk += L
            j += 1
        xk += W
        k += 1
    reg_arch("mb_wm floor smoked oak 22", planks, 10)
    notes.append(f"floor: {len(planks)} planks of 22 cm along Y from X {x0} (strip edges every 0.22), staggered ends, 1.5 mm gaps, "
                 "three tones of #8B6F55 (+-2 %)")
    # ---- W-master: plaster reveals, bronze frame at the outer face (45 mm, two panes, no transom), limestone slab ----
    xo, fd, s = WIN["x_out"], WIN["frame_d"], WIN["sight"]
    xf = xo + fd                                              # inner face of the frame, X -2.61
    rev = [r3.bx("mb_wm_rev_a", xf, xw, wy0, wy0 + 0.001, WIN["sill"], WIN["head"], pl),
           r3.bx("mb_wm_rev_b", xf, xw, wy1 - 0.001, wy1, WIN["sill"], WIN["head"], pl),
           r3.bx("mb_wm_rev_h", xf, xw, wy0, wy1, WIN["head"] - 0.001, WIN["head"], pl)]
    reg_arch("mb_wm window reveals (plaster)", rev, 12)
    my = (wy0 + wy1) / 2
    frm = [r3.bx("mb_wm_wf_a", xo, xf, wy0, wy0 + s, WIN["sill"], WIN["head"], bz), r3.bx("mb_wm_wf_b", xo, xf, wy1 - s, wy1, WIN["sill"], WIN["head"], bz),
           r3.bx("mb_wm_wf_t", xo, xf, wy0, wy1, WIN["head"] - s, WIN["head"], bz), r3.bx("mb_wm_wf_bt", xo, xf, wy0, wy1, WIN["sill"], WIN["sill"] + s, bz),
           r3.bx("mb_wm_wf_m", xo, xf, my - s / 2, my + s / 2, WIN["sill"], WIN["head"], bz)]
    reg_arch("mb_wm window frame (bronze)", frm, 13)
    slab = [r3.bx("mb_wm_sill_slab", xf, xw + WIN["slab_proud"] - SKIN, wy0, wy1, slab_z0, WIN["sill"], st, 0.003)]
    reg_arch("mb_wm sill slab (limestone)", slab, 14)
    gs = bpy.data.objects.get("ground_slab")
    if gs is not None:
        reg_arch("mb_wm outside ground", [gs], 15)
    notes.append(f"W-master: frame X {xo}..{xf} (the outer face; the reveal reads {xw - xf:.2f} deep of the 0.35 wall), sight lines "
                 f"{s * 1000:.0f} mm, mullion at Y {my:.3f}, no transom; limestone slab Z {slab_z0:.2f}-{WIN['sill']:.2f}, front at X "
                 f"{xw + WIN['slab_proud'] - SKIN:.3f} (2 cm proud of the plaster); no glass in the clay (the area light outside)")
    # ---- doors (out of MB0): leaf in the wall colour, walnut linings, no architrave ----
    lf = bpy.data.objects.get("leaf_corridor_master_m1")
    lin = []
    if lf is not None:
        lf.data.materials.clear()
        lf.data.materials.append(pl)
        lin.append(lf)
    dx0, dx1 = DOOR["x"]
    lin += [r3.bx("mb_wm_dl_a", dx0, dx0 + 0.01, 17.51, y0, 0.0, DOOR["head"], wal), r3.bx("mb_wm_dl_b", dx1 - 0.01, dx1, 17.51, y0, 0.0, DOOR["head"], wal),
            r3.bx("mb_wm_dl_h", dx0, dx1, 17.51, y0, DOOR["head"] - 0.01, DOOR["head"], wal)]
    ey0, ey1 = ENSUITE["y"]
    lin += [r3.bx("mb_wm_el_a", x1, 3.25, ey0, ey0 + 0.01, 0.0, ENSUITE["head"], wal), r3.bx("mb_wm_el_b", x1, 3.25, ey1 - 0.01, ey1, 0.0, ENSUITE["head"], wal),
            r3.bx("mb_wm_el_h", x1, 3.25, ey0, ey1, ENSUITE["head"] - 0.01, ENSUITE["head"], wal)]
    reg_arch("mb_wm doors (leaf + walnut linings)", lin, 16)
    notes.append("doors: the corridor leaf (1.1 G-M1, parked inside on X 2.90-2.94) in the wall colour; walnut linings in O-corridor-master "
                 "and O-master-ensuite, no architrave; both outside MB0")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# chapter 2: the fixed walnut bed and nightstands (not sold)
# ---------------------------------------------------------------------------------------------------------------
def wm_fixed():
    wal, pli = mat("walnut", "walnut", 0.7), mat("plinth", "plinth", 0.8)
    mt, rc = mat("mattress", "mattress", 0.95), mat("recess", "recess", 0.9)
    bx0, bx1 = BED["x"]
    by0, by1 = BED["y"]
    yh = by0 + BED["head_t"]
    r = BED["head_r"]
    hb_loop = [(bx0, 0.0), (bx1, 0.0)] + arc((bx1 - r, BED["head_h"] - r), r, 0, 90, 12) + arc((bx0 + r, BED["head_h"] - r), r, 90, 180, 12)
    head = [prism("mb_wm_bed_head", hb_loop, "y", by0, yh, wal)]
    ps = BED["plinth_set"]
    plinth = [r3.bx("mb_wm_bed_plinth", bx0 + ps, bx1 - ps, yh, by1 - ps, 0.0, BED["frame"][0], pli)]
    frame = [prism("mb_wm_bed_frame", rrect_xy(bx0, bx1, yh, by1, BED["frame_r"], corners=(False, False, True, True)), "z",
                   BED["frame"][0], BED["frame"][1], wal)]
    matt = [r3.bx("mb_wm_bed_mattress", bx0, bx1, yh, by1, BED["mat"][0], BED["mat"][1], mt, 0.03)]
    reg_arch("mb_wm bed headboard (fixed)", head, 20, kind="furniture")
    reg_arch("mb_wm bed frame (fixed)", frame, 21, kind="furniture")
    reg_arch("mb_wm bed plinth (fixed)", plinth, 22, kind="furniture")
    reg_arch("mb_wm mattress (fixed)", matt, 23, kind="furniture")
    car, top, grv, npl = [], [], [], []
    ny0, ny1 = NS["y"]
    for i, (x0, x1) in enumerate(NS["xs"]):
        rr = NS["r"]
        car.append(prism(f"mb_wm_ns{i}_carcass", rrect_xy(x0, x1, ny0, ny1, rr), "z", NS["plinth"], NS["h"] - NS["top_t"], wal))
        top.append(prism(f"mb_wm_ns{i}_top", rrect_xy(x0, x1, ny0, ny1, rr), "z", NS["h"] - NS["top_t"], NS["h"], wal))
        zm = (NS["plinth"] + NS["h"] - NS["top_t"]) / 2               # the drawer split, Z 0.29
        ztop = NS["h"] - NS["top_t"]
        g, rcz = NS["groove"], NS["recess"]
        for nm, za, zb in (("groove", zm - g / 2, zm + g / 2), ("rec_hi", ztop - rcz - 0.002, ztop - 0.002), ("rec_lo", zm - g / 2 - rcz, zm - g / 2)):
            grv.append(r3.bx(f"mb_wm_ns{i}_{nm}", x0 + rr, x1 - rr, ny1 - 0.003, ny1 + 0.0005, za, zb, rc))
        s = NS["plinth_set"]
        npl.append(r3.bx(f"mb_wm_ns{i}_plinth", x0 + s, x1 - s, ny0, ny1 - s, 0.0, NS["plinth"], pli))
    reg_arch("mb_wm nightstand carcass (fixed)", car, 24, kind="furniture")
    reg_arch("mb_wm nightstand top (fixed)", top, 25, kind="furniture")
    reg_arch("mb_wm nightstand grooves (fixed)", grv, 26, kind="furniture")
    reg_arch("mb_wm nightstand plinth (fixed)", npl, 27, kind="furniture")
    return head + plinth + frame + matt + car + top + grv + npl


# ---------------------------------------------------------------------------------------------------------------
# 3.2 + 12.2 defaults as boxes at the slot envelopes (6.5 placement)
# ---------------------------------------------------------------------------------------------------------------
def wm_products(R):
    notes = []
    C = {k: mat(k, k, rough) for k, rough in (("duvet", 0.95), ("pillow", 0.95), ("cushion", 0.98), ("throw", 0.95), ("trav", 0.85),
                                              ("arm", 0.5), ("candle", 0.9), ("tray", 0.7), ("bottle", 0.85), ("dish", 0.85),
                                              ("column", 0.85), ("curtain", 0.95), ("shade", 0.95), ("brass", 0.45), ("stem", 0.9),
                                              ("sage", 0.9), ("lampwal", 0.7), ("walnut", 0.7))}
    bx0, bx1 = BED["x"]
    mz = BED["mat"][1]
    yh = BED["y"][0] + BED["head_t"]
    # bedding V1: duvet folded back 30 cm at Y 18.30, 20 cm side and foot drops (walnut frame stays visible), fitted sheet at the head
    d = 0.015
    bed = [r3.bx("mb_wm_duvet", bx0, bx1, 18.30, BED["y"][1], mz, mz + 0.08, C["duvet"], 0.02),
           r3.bx("mb_wm_duvet_fold", bx0, bx1, 18.30, 18.60, mz + 0.08, mz + 0.11, C["duvet"], 0.015),
           r3.bx("mb_wm_duvet_l", bx0 - d, bx0, 18.30, BED["y"][1] + d, mz - 0.20, mz + 0.07, C["duvet"]),
           r3.bx("mb_wm_duvet_r", bx1, bx1 + d, 18.30, BED["y"][1] + d, mz - 0.20, mz + 0.07, C["duvet"]),
           r3.bx("mb_wm_duvet_f", bx0 - d, bx1 + d, BED["y"][1], BED["y"][1] + d, mz - 0.20, mz + 0.07, C["duvet"]),
           r3.bx("mb_wm_sheet", bx0, bx1, yh, 18.31, mz - 0.001, mz + 0.004, C["duvet"]),
           r3.bx("mb_wm_sheet_l", bx0 - 0.004, bx0, yh, 18.31, BED["mat"][0], mz, C["duvet"]),
           r3.bx("mb_wm_sheet_r", bx1, bx1 + 0.004, yh, 18.31, BED["mat"][0], mz, C["duvet"])]
    reg_prod(R, "bedding", bed, 52, "6.5 / 3.2 V1: duvet over the bed, folded back 30 cm at Y 18.30 (Z to 0.61), side and foot drops of 20 cm "
             "(to Z 0.30, the frame Z 0.06-0.28 stays visible), fitted sheet under the pillows")
    pil = [r3.bx(f"mb_wm_pillow{i}", a, b, yh + 0.01, 18.20, mz + 0.005, mz + 0.16, C["pillow"], 0.05) for i, (a, b) in enumerate(((-1.50, -0.80), (-0.60, 0.10)))]
    reg_prod(R, "pillowcases", pil, 51, "12.2: Caramel Pairs 48 x 74, two pillows lying flat against the headboard, X -1.50..-0.80 and -0.60..0.10, "
             "Y 17.72-18.20, Z 0.505-0.66")
    cu = [r2.obox("mb_wm_cushion", (-0.70, 18.29, mz + 0.06), (-0.70, 18.248, mz + 0.36), (1, 0, 0), 0.50, 0.12, C["cushion"])]
    reg_prod(R, "cushions", cu, 53, "12.2: Milk Tea boucle 30 x 50, one, centred, standing and leaning back about 8 deg, X -0.95..-0.45, "
             "Y about 18.26, Z 0.56-0.86")
    ty0, ty1 = 19.26, 19.63
    tz = mz + 0.08
    th = [r3.bx("mb_wm_throw", bx0 - d - 0.005, bx1 + d + 0.005, ty0, ty1, tz, tz + 0.035, C["throw"], 0.01),
          r3.bx("mb_wm_throw_l", bx0 - d - 0.02, bx0 - d - 0.005, ty0, ty1, tz + 0.035 - 0.10, tz + 0.035, C["throw"]),
          r3.bx("mb_wm_throw_r", bx1 + d + 0.005, bx1 + d + 0.02, ty0, ty1, tz + 0.035 - 0.10, tz + 0.035, C["throw"])]
    reg_prod(R, "throw", th, 54, "12.2 Pecan 150 x 200, folded to a 37 cm strip across the foot at Y 19.26-19.63, Z 0.58-0.615, "
             "about 10 cm hanging over each side past the duvet edge")
    # sconce pair: walnut plate on the wall, short black arm, travertine cone opening down; lit 2700 K (spot down + a small point)
    sw, se, lights, glow = [], [], [], []
    for i, (px, py, pz) in enumerate(SCONCE["plates"]):
        plate = r2.obox(f"mb_wm_sc_plate{i}", (px, py + 0.002, pz), (px, py + 0.002 + SCONCE["plate_t"], pz), (1, 0, 0), 2 * SCONCE["plate_r"],
                        2 * SCONCE["plate_r"], C["walnut"])
        armo = r2.obox(f"mb_wm_sc_arm{i}", (px, py + 0.02, pz), (px, SCONCE["axis_y"], pz), (1, 0, 0), 0.012, 0.012, C["arm"])
        cn = cone(f"sc_cone{i}", (px, SCONCE["axis_y"]), SCONCE["cone_r"], SCONCE["cone_top_r"], SCONCE["cone_z"][0], SCONCE["cone_z"][1], C["trav"], 48)
        (sw if i == 0 else se).extend([plate, armo, cn])
        glow.append((cn, LIGHT["sconce_glow"]))
        sp = r2.mk_light(f"mb_wm_sc_spot{i}", "SPOT", (px, SCONCE["axis_y"], SCONCE["cone_z"][0] + 0.03), LIGHT["sconce_spot_w"])
        sp.data.spot_size = math.radians(LIGHT["sconce_spot_deg"])
        sp.data.spot_blend = 0.8
        sp.data.shadow_soft_size = 0.05
        pt = r2.mk_light(f"mb_wm_sc_pt{i}", "POINT", (px, SCONCE["axis_y"], SCONCE["cone_z"][0] + 0.05), LIGHT["sconce_point_w"], size=0.06)
        lights += [sp, pt]
    r3.reg(R, "master/bedside-sconces", sw + se, "master", src="3.2 travertine cone on a walnut plate, D15 x 15, black arm; plates (-1.875 / 0.475, "
           "Z 1.34); cone axis Y 17.775 (projection 0.19), cone Z 1.19-1.34")
    r2.reg("mb_wm bedside-sconces east", se, "master", "proxy")
    GROUP_ID["master/bedside-sconces"] = 43
    GROUP_ID["mb_wm bedside-sconces east"] = 44
    r2.lamp("master/bedside-sconces", "master", "wall", glow, lights, "travertine cone pair (3.2)")
    # right nightstand: travertine pedestal pair 7 x 11 with pillar candles 7 x 10 (low, at the bed) and 7 x 15 (filler)
    ch, cd = [], []
    for i, ((cx_, cy_), ch_h) in enumerate((((0.50, 17.88), 0.10), ((0.61, 17.82), 0.15))):
        z0 = NS["h"]
        ch += [cyl(f"cand_base{i}", (cx_, cy_), 0.035, z0, z0 + 0.015, C["trav"], 32), cyl(f"cand_stem{i}", (cx_, cy_), 0.019, z0 + 0.015, z0 + 0.095, C["trav"], 32),
               cyl(f"cand_cup{i}", (cx_, cy_), 0.035, z0 + 0.095, z0 + 0.11, C["trav"], 32)]
        cd.append(cyl(f"candle{i}", (cx_, cy_), 0.034, z0 + 0.11, z0 + 0.11 + ch_h, C["candle"], 32))
    reg_prod(R, "candle-holders", ch, 49, "3.2 travertine pedestal 7 x 11, pair at (0.50, 17.88) and (0.61, 17.82)")
    reg_prod(R, "candle-holders-filler", cd, 50, "6.8 pillar candles 7 x 10 (at the bed) and 7 x 15, cream, unlit")
    # left nightstand: tray 30 x 20 x 2, parallel to the front, 3 cm from the front edge (6.5); bottle and dish moved onto it (README)
    ty = (NS["y"][1] - 0.03 - 0.20, NS["y"][1] - 0.03)
    tx = (-2.025, -1.725)
    tray = [r3.bx("mb_wm_tray", tx[0], tx[1], ty[0], ty[1], NS["h"], NS["h"] + 0.02, C["tray"], 0.004)]
    reg_prod(R, "nightstand-tray", tray, 45, f"3.2 walnut tray 30 x 20 x 2, X {tx[0]}..{tx[1]}, Y {ty[0]:.2f}-{ty[1]:.2f} (3 cm from the front, 6.5)")
    vz = NS["h"] + 0.02
    vc = (-1.95, 17.90)
    vase = [cyl("bottle_body", vc, 0.055, vz, vz + 0.17, C["bottle"], 40), cone("bottle_shoulder", vc, 0.055, 0.02, vz + 0.17, vz + 0.215, C["bottle"], 40),
            cyl("bottle_neck", vc, 0.017, vz + 0.215, vz + 0.245, C["bottle"], 24)]
    reg_prod(R, "nightstand-vase", vase, 46, f"3.2 Color D sand bottle 11 x 24.5 at ({vc[0]}, {vc[1]}) on the tray (6.5 says 17.84: off the tray's back edge)")
    stems = [r2.obox("mb_wm_oat_a", (vc[0], vc[1], vz + 0.24), (vc[0] - 0.07, vc[1] + 0.01, 1.00), (0, 1, 0), 0.006, 0.006, C["stem"]),
             r2.obox("mb_wm_oat_b", (vc[0] + 0.004, vc[1], vz + 0.24), (vc[0] - 0.03, vc[1] - 0.01, 0.97), (0, 1, 0), 0.006, 0.006, C["stem"]),
             r3.ell("mb_wm_oat_head_a", (vc[0] - 0.062, vc[1] + 0.009), 0.012, 0.93, 1.00, C["stem"]),
             r3.ell("mb_wm_oat_head_b", (vc[0] - 0.028, vc[1] - 0.009), 0.011, 0.91, 0.97, C["stem"])]
    reg_prod(R, "nightstand-vase-filler", stems, 47, "6.8 two dry oat stems to Z 1.00, leaning a little toward the window")
    dish = [r3.bx("mb_wm_dish", -1.84, -1.74, 17.88, 17.98, vz, vz + 0.025, C["dish"], 0.006)]
    reg_prod(R, "trinket-dish", dish, 48, "3.2 travertine 10 x 10 rough edge, empty, at (-1.79, 17.93) on the tray (6.5 says 17.90)")
    # sill: the fluted column 8.5 x 24.7 at (-2.45, 18.30) on the limestone, one sage stem to Z 1.20
    sv = (-2.45, 18.30)
    col = [cyl("sill_vase", sv, 0.0425, WIN["sill"], WIN["sill"] + 0.247, C["column"], 24)]
    reg_prod(R, "sill-vase", col, 41, "3.2 cream fluted column 8.5 x 24.7 at (-2.45, 18.30) on the slab, alone")
    ss = [r2.obox("mb_wm_sill_stem", (sv[0], sv[1], WIN["sill"] + 0.24), (sv[0] + 0.02, sv[1] + 0.05, 1.20), (0, 1, 0), 0.005, 0.005, C["sage"]),
          r3.ell("mb_wm_sill_leaves", (sv[0] + 0.015, sv[1] + 0.035), 0.035, 1.06, 1.20, C["sage"])]
    reg_prod(R, "sill-vase-filler", ss, 42, "6.8 one sage stem to Z 1.20")
    # curtains: S-fold stacks out of the ceiling slot, hem 12 cm above the floor (WM-C3), only the stack at the bed wall in frame
    folds = []
    for si, (ya, yb) in enumerate(CURTAIN["stacks"]):
        ycs = np.linspace(ya + CURTAIN["r"], yb - CURTAIN["r"], CURTAIN["n"])
        for i, yc in enumerate(ycs):
            folds.append(cyl(f"curt{si}_{i}", (CURTAIN["x"][i % 2], float(yc)), CURTAIN["r"], CURTAIN["z"][0], CURTAIN["z"][1], C["curtain"], 24))
    reg_prod(R, "curtains", folds, 40, f"3.2 linen-blend S-fold 132 x 270: two stacks Y 17.88-18.10 and 19.60-19.82, {CURTAIN['n']} folds each "
             f"(X {CURTAIN['x'][0] - CURTAIN['r']:.3f}..{CURTAIN['x'][1] + CURTAIN['r']:.3f}), hem Z 0.12, head 2.82")
    # floor lamp 177278: brass disc, walnut stem, brass collar, cream pleated cone 43 / 22, Z 1.28-1.58; lit
    lc = LAMP["c"]
    shade = cone("lamp_shade", lc, LAMP["shade_r"][0], LAMP["shade_r"][1], LAMP["shade"][0], LAMP["shade"][1], C["shade"], 64)
    fl = [cyl("lamp_base", lc, LAMP["base_r"], 0.0, 0.02, C["brass"], 48), cyl("lamp_stem", lc, LAMP["stem_r"], 0.02, LAMP["shade"][0], C["lampwal"], 16),
          cyl("lamp_collar", lc, 0.016, LAMP["collar"][0], LAMP["collar"][1], C["brass"], 16), shade]
    reg_prod(R, "floor-lamp", fl, 55, "3.2 / 177278: shade D43 (bottom) / 22 (top), Z 1.28-1.58; walnut stem, brass collar and disc base 28")
    ll = [r2.mk_light("mb_wm_lamp_pt", "POINT", (lc[0], lc[1], 1.40), LIGHT["lamp_point_w"], size=0.08),
          r2.mk_light("mb_wm_lamp_area", "AREA", (lc[0], lc[1], LAMP["shade"][0] + 0.02), LIGHT["lamp_area_w"], size=0.36)]
    r2.lamp("master/floor-lamp", "master", "floor", [(shade, LIGHT["lamp_glow"])], ll, "pleated cone 43 (177278)")
    notes.append("products: 3.2 with 12.2 (pillowcases Caramel Pairs, cushion Milk Tea, throw Pecan); empty: framed-art, planter, "
                 "bedside-carafe; rug, basket, pendant not built (no frame)")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# passes
# ---------------------------------------------------------------------------------------------------------------
_render_prev = fr.render


def render_capture(path, tmp, res, samples, ao=0.30, passes=True, exposure=None):
    out = _render_prev(path, tmp, res, samples, ao=ao, passes=passes, exposure=exposure)
    if out is not None:
        CAPTURE["last"] = out
    return out


fr.render = render_capture


def id_map(idx):
    pid = {}
    for name, v in fr.REG.items():
        if name in GROUP_ID:
            pid[v["pidx"]] = GROUP_ID[name]
    pid[bh.IDX["ceiling"]] = 6
    pid[bh.IDX["floor"]] = 11
    out = np.full(idx.shape, 90, np.uint8)
    out[idx == 0] = 0
    for p, g in pid.items():
        out[idx == p] = g
    return out, pid


def edges_of(ids, depth, normal):
    st = np.isin(ids, list(ARCH_IDS | FIXED_IDS))
    e = np.zeros(ids.shape, bool)
    for ax in (0, 1):
        a, b = ids, np.roll(ids, -1, axis=ax)
        sa, sb = st, np.roll(st, -1, axis=ax)
        ch = (a != b) & sa & sb
        d0, d1 = depth, np.roll(depth, -1, axis=ax)
        dj = (np.abs(d0 - d1) > 0.02 * np.minimum(d0, d1)) & sa & sb
        n0, n1 = normal, np.roll(normal, -1, axis=ax)
        cr = ((n0 * n1).sum(-1) < 0.85) & sa & sb
        e |= ch | dj | cr
    e[-1, :] = False
    e[:, -1] = False
    return e


def save_passes(fid, out_dir, depth, idx, normal):
    from PIL import Image
    ids, pid = id_map(idx)
    d = np.where(np.isfinite(depth) & (depth < 13.0), depth * DEPTH_UNITS, 65535).astype(np.uint16)
    Image.fromarray(d).save(os.path.join(out_dir, f"{fid}-depth.png"))
    im = Image.fromarray(ids, "P")
    flat = []
    for k in range(256):
        flat += list(PAL.get(k, (0, 0, 0)))
    im.putpalette(flat)
    im.save(os.path.join(out_dir, f"{fid}-id.png"))
    e = edges_of(ids, depth, normal)
    Image.fromarray((e * 255).astype(np.uint8)).save(os.path.join(out_dir, f"{fid}-edges.png"))
    np.savez_compressed(os.path.join(SCR, "npz", f"{fid}.npz"), depth=depth.astype(np.float32), idx=idx, ids=ids, normal=normal.astype(np.float16))
    counts = {IDS[k]: int((ids == k).sum()) for k in sorted(set(np.unique(ids).tolist()))}
    return ids, counts, {str(k): v for k, v in pid.items()}


# ---------------------------------------------------------------------------------------------------------------
# measurements in FRAME fractions (the 16:9 camera frame inside the canvas)
# ---------------------------------------------------------------------------------------------------------------
def to_frame(u, v):
    return 0.5 + (u - 0.5) * K, 0.5 + (v - 0.5) * K


def UVf(cam, x, y, z):
    return to_frame(fr.U(cam, x, y, z), fr.V(cam, x, y, z))


def px(cam, x, y, z):
    return [round(fr.U(cam, x, y, z) * CANVAS[0], 2), round(fr.V(cam, x, y, z) * CANVAS[1], 2)]


def r4_(x):
    return round(float(x), 4)


def bbox_f(ids, gids):
    m = np.isin(ids, list(gids))
    if m.sum() < 5:
        return None
    H, W = ids.shape
    ys, xs = np.nonzero(m)
    u0, v0 = to_frame(xs.min() / W, ys.min() / H)
    u1, v1 = to_frame((xs.max() + 1) / W, (ys.max() + 1) / H)
    return dict(u=[r4_(u0), r4_(u1)], v=[r4_(v0), r4_(v1)], px=int(m.sum()), frame_pct=round(100 * m.sum() / (H * W) * K * K, 3))


def gap_u(ids, left, right, rows=None):
    H, W = ids.shape
    best = None
    ml, mr = np.isin(ids, list(left)), np.isin(ids, list(right))
    for y in (range(H) if rows is None else rows):
        a, b = np.nonzero(ml[y])[0], np.nonzero(mr[y])[0]
        if len(a) == 0 or len(b) == 0:
            continue
        g = (b.min() - a.max() - 1) / W * K
        best = g if best is None or g < best else best
    return None if best is None else r4_(best)


def vertical_tilt(ids, a, b, rows, x_expect, win=15):
    pts = []
    W = ids.shape[1]
    lo, hi = max(0, int(x_expect) - win), min(W - 1, int(x_expect) + win)
    for y in rows:
        r = ids[y]
        for x in range(lo, hi):
            if r[x] in a and r[x + 1] in b:
                pts.append((y, x + 1))
                break
    if len(pts) < 10:
        return dict(tilt_deg=None, rows=len(pts), note="boundary not visible (covered)")
    ys, xs = np.array(pts, float).T
    k = np.polyfit(ys, xs, 1)[0]
    return dict(tilt_deg=round(math.degrees(math.atan(k)), 3), rows=len(pts))


def checks_6_3(fid, cam, ids, items=None):
    """The 6.3 table, the rejection-list camera numbers (7, plate 4) and M-HC1..5 of master.json, analytic and from the id pass."""
    C = {}
    xw, yb = ROOM["x"][0] + 2 * SKIN, ROOM["y"][0] + 2 * SKIN
    cx, cy = CORNER["c"]
    rf = CORNER["r"] - 2 * SKIN
    # camera numbers (rejection list 4)
    C["bed_centre_u"] = dict(target="0.50 +-0.01", value=r4_(UVf(cam, -0.70, 17.71, 0.80)[0]))
    C["bed_centre_u"]["ok"] = abs(C["bed_centre_u"]["value"] - 0.50) <= 0.01
    a_mid = math.radians(225)
    C["rounded_corner_u"] = dict(target="0.185 +-0.01 (the 1.1 sharp corner)",
                                 sharp_corner_equivalent=r4_(UVf(cam, ROOM["x"][0], ROOM["y"][0], 1.2)[0]),
                                 arc_tangent_window_wall=r4_(UVf(cam, xw, cy, 1.2)[0]), arc_tangent_bed_wall=r4_(UVf(cam, cx, yb, 1.2)[0]),
                                 arc_mid_45deg=r4_(UVf(cam, cx + rf * math.cos(a_mid), cy + rf * math.sin(a_mid), 1.2)[0]))
    C["rounded_corner_u"]["ok"] = abs(C["rounded_corner_u"]["arc_mid_45deg"] - 0.185) <= 0.01
    C["rounded_corner_u"]["note"] = ("with R 0.20 the corner is a band, not a line: it reads from the window-wall tangent to the bed-wall "
                                     "tangent; the arc's mid line is the corner's reading")
    wu = UVf(cam, xw, WIN["y"][0], 1.5)[0]
    left_y = None
    for yy in np.linspace(WIN["y"][0], WIN["y"][1], 3001):
        if UVf(cam, xw, yy, 1.5)[0] <= 0.0:
            left_y = float(yy)
            break
    C["window"] = dict(target="u 0-0.138 +-0.01, cut >= 15 %", jamb_u=r4_(wu), ok=abs(wu - 0.138) <= 0.01,
                       wall_face_Y_at_left_edge=round(left_y, 3) if left_y else None,
                       cut_pct=round(100 * (WIN["y"][1] - left_y) / (WIN["y"][1] - WIN["y"][0]), 1) if left_y else None,
                       bronze_jamb_u=r4_(UVf(cam, WIN["x_out"] + WIN["frame_d"], WIN["y"][0] + WIN["sight"], 1.5)[0]),
                       mullion_u=r4_(UVf(cam, WIN["x_out"] + WIN["frame_d"], 18.85, 1.5)[0]),
                       slab_front_v_at_jamb=r4_(UVf(cam, xw + WIN["slab_proud"], WIN["y"][0], WIN["sill"])[1]),
                       top_edge_Z_at_jamb=round(fr.top_edge_Z(cam, xw, WIN["y"][0]), 3), head_Z=WIN["head"])
    C["corridor_jamb_out"] = dict(u_frame=r4_(UVf(cam, DOOR["x"][0], ROOM["y"][0], 1.2)[0]), canvas_edge_u_frame=r4_(to_frame(1.0, 0.5)[0]),
                                  ok=UVf(cam, DOOR["x"][0], ROOM["y"][0], 1.2)[0] > 1.0)
    C["headboard"] = dict(target="u 0.320-0.680, top v 0.425", u=[r4_(UVf(cam, BED["x"][0], 17.71, 1.0)[0]), r4_(UVf(cam, BED["x"][1], 17.71, 1.0)[0])],
                          top_v=r4_(UVf(cam, -0.70, 17.71, BED["head_h"])[1]))
    C["left_nightstand_top"] = dict(target="u 0.188-0.288, v 0.66", u_front=[r4_(UVf(cam, NS["xs"][0][0], NS["y"][1], NS["h"])[0]),
                                                                            r4_(UVf(cam, NS["xs"][0][1], NS["y"][1], NS["h"])[0])],
                                    v_front_edge=r4_(UVf(cam, -1.875, NS["y"][1], NS["h"])[1]), v_back_edge=r4_(UVf(cam, -1.875, NS["y"][0], NS["h"])[1]))
    cones = []
    for (pxx, pyy, pzz) in SCONCE["plates"]:
        zc = sum(SCONCE["cone_z"]) / 2
        cones.append(dict(u_centre=r4_(UVf(cam, pxx, SCONCE["axis_y"], zc)[0]), v_centre=r4_(UVf(cam, pxx, SCONCE["axis_y"], zc)[1]),
                          v_plate=r4_(UVf(cam, pxx, pyy, pzz)[1]), v_lip=r4_(UVf(cam, pxx, SCONCE["axis_y"] + SCONCE["cone_r"], SCONCE["cone_z"][0])[1])))
    C["cones"] = dict(target="u 0.255 / 0.745 (+-0.01), v 0.35", pair=cones,
                      ok_u=abs(cones[0]["u_centre"] - 0.255) <= 0.01 and abs(cones[1]["u_centre"] - 0.745) <= 0.01,
                      note="v 0.35 is the plate height (Z 1.34) at the cone's depth; the cone hangs below its arm, so its centre reads lower")
    C["art_place_empty"] = dict(target="u 0.412-0.588, v 0.13-0.34 (empty now)",
                                slot_rect=dict(u=[r4_(UVf(cam, -1.30, 17.69, 1.7)[0]), r4_(UVf(cam, -0.10, 17.69, 1.7)[0])],
                                               v=[r4_(UVf(cam, -0.7, 17.69, 2.00)[1]), r4_(UVf(cam, -0.7, 17.69, 1.40)[1])]),
                                note="the slot's 110-120 wide art (X -1.30..-0.10) spans u 0.382-0.618; 0.412-0.588 is a 90 cm wide piece")
    if fid == "MB0":
        bxs = {nm: bbox_f(ids, g) for nm, g in (("curtain", {40}), ("sill_vase", {41}), ("cushion", {53}), ("throw", {54}), ("candle_holders", {49}),
                                                 ("floor_lamp", {55}), ("pillowcases", {51}), ("bedding", {52}), ("sconce_w", {43}), ("sconce_e", {44}),
                                                 ("tray", {45}), ("bottle", {46}), ("dish", {48}))}
        C["boxes_6_3"] = bxs
        # curtain stack and hem
        cb = bxs["curtain"]
        C["curtain_stack"] = dict(target="u about 0.14-0.17, hem v 0.82-0.83", u=cb["u"] if cb else None,
                                  hem_v_front=r4_(UVf(cam, CURTAIN["x"][1] + CURTAIN["r"], CURTAIN["stacks"][0][1] - CURTAIN["r"], CURTAIN["z"][0])[1]),
                                  hem_v_back=r4_(UVf(cam, CURTAIN["x"][1] + CURTAIN["r"], CURTAIN["stacks"][0][0] + CURTAIN["r"], CURTAIN["z"][0])[1]))
        # M-HC2: curtain vs left nightstand (>= 0.02 clear, or >= 0.03 overlap)
        g = gap_u(ids, {40}, {24, 25, 27})
        ns_left = UVf(cam, NS["xs"][0][0], NS["y"][1], 0.3)[0]
        opts = {}
        for (ya, yb_, depth) in ((17.88, 18.10, 0.12), (17.92, 18.10, 0.12), (17.92, 18.10, 0.09), (17.96, 18.10, 0.09), (17.98, 18.10, 0.08),
                                 (18.00, 18.22, 0.12), (18.00, 18.22, 0.09), (18.04, 18.26, 0.12)):
            right = max(UVf(cam, ROOM["x"][0] + depth, yy, 0.3)[0] for yy in (ya, yb_))
            over = max(0.0, yb_ - WIN["y"][0])
            opts[f"stack Y {ya}-{yb_}, {int(depth * 100)} cm off the wall" + (f" ({int(round(over * 100))} cm over the window edge)" if over else "")] = dict(
                right_u=r4_(right), left_u=r4_(UVf(cam, ROOM["x"][0], yb_, 1.5)[0]), gap_to_nightstand=r4_(ns_left - right), ok=ns_left - right >= 0.02)
        C["M-HC2_curtain_vs_nightstand"] = dict(rule=">= 0.02 clear or >= 0.03 overlap", gap_px_rows=g, nightstand_left_u=r4_(ns_left),
                                               ok=g is not None and (g >= 0.02 or g <= -0.03), analytic_options=opts)
        # M-HC3: bedding vs pillowcases (decisive overlap: no mattress sliver between), floor lamp vs throw
        H, W = ids.shape
        pm = ids == 51
        sliver = 0
        cols = np.nonzero(pm.any(0))[0]
        for xcol in cols[::4]:
            col = ids[:, xcol]
            yy = np.nonzero(col == 51)[0]
            if len(yy) == 0:
                continue
            below = col[yy.max() + 1: yy.max() + 12]
            sliver += int(np.isin(below, [23]).any())
        lamp_base = bbox_f(ids, {55})
        C["M-HC3"] = dict(bedding_vs_pillows=dict(columns_checked=int(len(cols[::4])), columns_with_mattress_between=sliver, ok=sliver == 0),
                          floor_lamp_vs_throw=dict(gap_u=gap_u(ids, {54}, {55}), lamp=lamp_base,
                                                   ))
        # the lamp base: is any pixel of the disc (Z <= 0.02) visible? project the disc and test the id pass there
        vis = 0
        tot = 0
        for a in np.linspace(0, 2 * math.pi, 48, endpoint=False):
            for rr in (0.03, 0.08, 0.13):
                u, v = fr.U(cam, LAMP["c"][0] + rr * math.cos(a), LAMP["c"][1] + rr * math.sin(a), 0.02), fr.V(cam, LAMP["c"][0] + rr * math.cos(a), LAMP["c"][1] + rr * math.sin(a), 0.02)
                if 0 <= u < 1 and 0 <= v < 1:
                    tot += 1
                    vis += int(ids[int(v * H), int(u * W)] == 55)
        C["M-HC3"]["floor_lamp_vs_throw"]["base_disc_samples_visible"] = f"{vis}/{tot}"
        C["M-HC3"]["floor_lamp_vs_throw"]["ok"] = vis == 0 or vis > 0.8 * tot
        # M-HC4: the sill vase
        sb = bxs["sill_vase"]
        C["M-HC4_sill_vase"] = dict(target="u about 0.076, v 0.48-0.58; >= 0.05 from the left edge, >= 0.02 from the jamb and the curtain",
                                    box=sb, from_left_edge=sb["u"][0] if sb else None, to_jamb=r4_(wu - sb["u"][1]) if sb else None,
                                    to_curtain=r4_(cb["u"][0] - sb["u"][1]) if (sb and cb) else None)
        if sb:
            C["M-HC4_sill_vase"]["ok"] = sb["u"][0] >= 0.05 and (wu - sb["u"][1]) >= 0.02 and (cb is None or cb["u"][0] - sb["u"][1] >= 0.02)
        # the shade 43 vs the east cone and the right nightstand
        C["shade_43"] = dict(gap_to_east_cone_u=gap_u(ids, {44}, {55}), shade_box=bxs["floor_lamp"],
                             right_nightstand_top_right_u=r4_(UVf(cam, NS["xs"][1][1], NS["y"][1], NS["h"])[0]),
                             shade_bottom_v=r4_(UVf(cam, LAMP["c"][0], LAMP["c"][1] + LAMP["shade_r"][0], LAMP["shade"][0])[1]),
                             right_nightstand_top_v=r4_(UVf(cam, NS["xs"][1][1], NS["y"][1], NS["h"])[1]))
        # the cushion as the hot point
        C["cushion"] = dict(target="u 0.44-0.56, v 0.53-0.66", box=bxs["cushion"])
        C["throw"] = dict(target="u about 0.12-0.88, v 0.78-0.86", box=bxs["throw"])
        C["candle_holders"] = dict(target="u about 0.75-0.77", box=bxs["candle_holders"])
        su = [UVf(cam, LAMP["c"][0] + LAMP["shade_r"][0] * math.cos(t), LAMP["c"][1] + LAMP["shade_r"][0] * math.sin(t), LAMP["shade"][0]) for t in np.linspace(0, 2 * math.pi, 73)]
        sv = UVf(cam, LAMP["c"][0], LAMP["c"][1] - LAMP["shade_r"][1], LAMP["shade"][1])[1]
        C["floor_lamp_shade"] = dict(target="u 0.84-0.94, v 0.24-0.35", shade_u=[r4_(min(q[0] for q in su)), r4_(max(q[0] for q in su))],
                                     shade_v=[r4_(sv), r4_(max(q[1] for q in su))], lamp_box_with_stem=bxs["floor_lamp"])
        C["count_V7Q6"] = count_f10(ids, items or {})
    # verticals (tilt 0 and roll 0 by construction), measured on the id boundaries
    H, W = ids.shape
    rows = range(int(0.10 * H), int(0.55 * H))
    xj = fr.U(cam, xw, WIN["y"][0], 1.6) * W
    C["verticals_deg"] = dict(by_construction="camera tilt 0, roll 0", window_jamb_reveal_to_wall=vertical_tilt(ids, {12, 13, 0, 15}, {2}, rows, xj),
                              target="|tilt| <= 0.5")
    if fid != "MB0-shell":
        xh = fr.U(cam, BED["x"][0], 17.71, 0.9) * W
        C["verticals_deg"]["headboard_left_edge"] = vertical_tilt(ids, {1, 5, 24, 25}, {20}, range(int(0.47 * H), int(0.56 * H)), xh)
    return C


SLOT_IDS = {"curtains": [40], "sill-vase": [41], "bedside-sconces": [43, 44], "nightstand-tray": [45], "nightstand-vase": [46],
            "trinket-dish": [48], "candle-holders": [49], "pillowcases": [51], "bedding": [52], "cushions": [53], "throw": [54],
            "floor-lamp": [55]}


def count_f10(ids, items):
    """house-plan frame_checks.F10 (V7Q6 a): (1) >= 50 % visible and (>= 0.5 % of the frame, or >= 0.15 % with the larger dimension
    >= 6 % of the frame height); (2) a composed group of 3 on one surface counts once if the union of its members not counted alone is
    >= 0.5 %; sets once; fillers and the unsold fixed furniture not counted. Visibility from run_frame's ray-cast (r2.analyse)."""
    rows = {}
    for slot, gl in SLOT_IDS.items():
        b = bbox_f(ids, set(gl))
        vis = (items.get(f"master/{slot}") or {}).get("visible_pct")
        if b is None:
            rows[slot] = dict(counted=False, why="not in frame")
            continue
        hpct = round(100 * (b["v"][1] - b["v"][0]), 2)
        wpct = round(100 * (b["u"][1] - b["u"][0]) * 16 / 9, 2)
        big = max(hpct, wpct)
        ok_area = b["frame_pct"] >= 0.5 or (b["frame_pct"] >= 0.15 and big >= 6.0)
        rows[slot] = dict(frame_pct=b["frame_pct"], larger_dim_pct_of_height=big, visible_pct=vis, counted=bool(ok_area and (vis is None or vis >= 50)),
                          why=None if ok_area and (vis is None or vis >= 50) else ("visible < 50 %" if ok_area else "too small"))
    for grp, members in (("left nightstand group (tray, bottle, dish)", ["nightstand-tray", "nightstand-vase", "trinket-dish"]),):
        rest = [m for m in members if not rows[m]["counted"]]
        u = sum(rows[m].get("frame_pct", 0) for m in rest)
        rows[grp] = dict(members_not_counted_alone=rest, union_pct=round(u, 3), counted=bool(len(rest) > 0 and u >= 0.5),
                         note="counts once only through members not counted alone")
    n = sum(1 for k, v in rows.items() if v.get("counted"))
    return dict(rule="house-plan frame_checks.F10 (V7Q6 a), on the clay", counted=n, minimum=14, rows=rows,
                designer_estimate_3_4="9 (bedding, pillowcases, cushion, throw, curtain, floor lamp, sill vase, left group, sconce pair)")


def lock_target(cam, depth_img):
    H, W = depth_img.shape
    xw, yb = ROOM["x"][0] + 2 * SKIN, ROOM["y"][0] + 2 * SKIN
    yf = NS["y"][1]
    s = WIN["sight"]
    xf = WIN["x_out"] + WIN["frame_d"]
    L = {
        "window jamb at the wall face (Y 18.10)": ((xw, WIN["y"][0], WIN["sill"]), (xw, WIN["y"][0], 2.40)),
        "bronze jamb, inner edge (Y 18.145)": ((xf, WIN["y"][0] + s, WIN["sill"] + s), (xf, WIN["y"][0] + s, 2.40)),
        "sill slab, top front edge (Z 0.75)": ((xw + WIN["slab_proud"], WIN["y"][0], WIN["sill"]), (xw + WIN["slab_proud"], 18.95, WIN["sill"])),
        "sill slab, bottom front edge (Z 0.71)": ((xw + WIN["slab_proud"], WIN["y"][0], WIN["sill"] - WIN["slab_t"]), (xw + WIN["slab_proud"], 18.95, WIN["sill"] - WIN["slab_t"])),
        "skirting top, window wall (Z 0.15)": ((xw + SK["proud"], 17.90, SK["h"]), (xw + SK["proud"], 18.95, SK["h"])),
        "skirting top, bed wall right of the right nightstand": ((0.72, yb + SK["proud"], SK["h"]), (1.95, yb + SK["proud"], SK["h"])),
        "floor line, bed wall right of the right nightstand": ((0.72, yb + SK["proud"], 0.0), (1.95, yb + SK["proud"], 0.0)),
        "headboard, left edge": ((BED["x"][0], 17.71, 0.52), (BED["x"][0], 17.71, BED["head_h"] - BED["head_r"])),
        "headboard, right edge": ((BED["x"][1], 17.71, 0.52), (BED["x"][1], 17.71, BED["head_h"] - BED["head_r"])),
        "headboard, top edge": ((BED["x"][0] + BED["head_r"], 17.71, BED["head_h"]), (BED["x"][1] - BED["head_r"], 17.71, BED["head_h"])),
        "mattress, foot top edge (plate)": ((BED["x"][0] + 0.04, BED["y"][1], BED["mat"][1] - 0.01), (BED["x"][1] - 0.04, BED["y"][1], BED["mat"][1] - 0.01)),
        "mattress, right top edge (plate)": ((BED["x"][1], 18.40, BED["mat"][1] - 0.01), (BED["x"][1], 19.60, BED["mat"][1] - 0.01)),
        "mattress, left top edge (plate)": ((BED["x"][0], 18.40, BED["mat"][1] - 0.01), (BED["x"][0], 19.60, BED["mat"][1] - 0.01)),
        "left nightstand, top front edge (Z 0.55)": ((NS["xs"][0][0] + 0.04, yf, NS["h"]), (NS["xs"][0][1] - 0.04, yf, NS["h"])),
        "left nightstand, top underside (Z 0.52)": ((NS["xs"][0][0] + 0.04, yf, NS["h"] - NS["top_t"]), (NS["xs"][0][1] - 0.04, yf, NS["h"] - NS["top_t"])),
        "left nightstand, drawer groove (Z 0.29)": ((NS["xs"][0][0] + 0.04, yf, 0.29), (NS["xs"][0][1] - 0.04, yf, 0.29)),
        "left nightstand, plinth line (Z 0.06)": ((NS["xs"][0][0] + 0.04, yf, NS["plinth"]), (NS["xs"][0][1] - 0.04, yf, NS["plinth"])),
        "right nightstand, top front edge (Z 0.55)": ((NS["xs"][1][0] + 0.04, yf, NS["h"]), (NS["xs"][1][1] - 0.04, yf, NS["h"])),
        "right nightstand, top underside (Z 0.52)": ((NS["xs"][1][0] + 0.04, yf, NS["h"] - NS["top_t"]), (NS["xs"][1][1] - 0.04, yf, NS["h"] - NS["top_t"])),
        "right nightstand, drawer groove (Z 0.29)": ((NS["xs"][1][0] + 0.04, yf, 0.29), (NS["xs"][1][1] - 0.04, yf, 0.29)),
        "right nightstand, plinth line (Z 0.06)": ((NS["xs"][1][0] + 0.04, yf, NS["plinth"]), (NS["xs"][1][1] - 0.04, yf, NS["plinth"])),
        "left nightstand, left side front edge (X -2.10)": ((NS["xs"][0][0], yf - NS["r"], 0.08), (NS["xs"][0][0], yf - NS["r"], 0.50)),
        "right nightstand, right side front edge (X 0.70)": ((NS["xs"][1][1], yf - NS["r"], 0.08), (NS["xs"][1][1], yf - NS["r"], 0.50)),
        "bed frame, right side top (Z 0.28)": ((BED["x"][1], 18.2, BED["frame"][1]), (BED["x"][1], 19.6, BED["frame"][1])),
        "bed frame, left side top (Z 0.28)": ((BED["x"][0], 18.2, BED["frame"][1]), (BED["x"][0], 19.6, BED["frame"][1])),
    }
    out = {}
    for name, (a, b) in L.items():
        pts, vis = [], 0
        for t in np.linspace(0, 1, 41):
            p = [a[i] + (b[i] - a[i]) * t for i in range(3)]
            u, v = fr.U(cam, *p), fr.V(cam, *p)
            if not (0 <= u < 1 and 0 <= v < 1):
                continue
            x, y = int(u * W), int(v * H)
            dp = CAM["loc"][1] - p[1]
            dd = float(depth_img[y, x])
            seen = abs(dd - dp) < 0.02 + 0.01 * dp
            vis += seen
            pts.append([round(u * CANVAS[0], 2), round(v * CANVAS[1], 2), bool(seen)])
        if pts:
            out[name] = dict(xyz=[list(a), list(b)], px_ends=[px(cam, *a), px(cam, *b)], samples=pts, visible_frac=round(vis / len(pts), 3))
    return out


# ---------------------------------------------------------------------------------------------------------------
# tone: white balance on the plaster, one exposure for the three frames (one camera point)
# ---------------------------------------------------------------------------------------------------------------
def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def Lstar(rgb01):
    lin = np.where(rgb01 <= 0.04045, rgb01 / 12.92, ((rgb01 + 0.055) / 1.055) ** 2.4)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722])
    return float(np.mean(np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)))


def tone_frames(frames, cam, ref_frame, out_dir):
    import tone_r4 as T
    toner = T.Toner()
    ref_pts = [(-0.70, 17.66, 1.85), (-0.40, 17.66, 2.05)]       # the bed wall above the headboard, centre (the art place is empty)
    u = [fr.U(cam, *p) for p in ref_pts]
    v = [fr.V(cam, *p) for p in ref_pts]
    img, lin = toner.load(os.path.join(r4.EXR_DIR, f"{ref_frame}.exr"))
    patch = np.concatenate([T.patch(lin[..., :3], uu, vv, 0.010) for uu, vv in zip(u, v)])
    m = patch.mean(0)
    tgt = srgb_to_lin([0xEC, 0xE5, 0xDA])
    gains = (tgt / tgt[1]) / (m / m[1])
    lo, hi = -3.0, 6.0
    for _ in range(22):
        e = (lo + hi) / 2
        t = toner.tone(img, lin, e, gains)
        L = np.mean([Lstar(T.patch(t, uu, vv, 0.010)) for uu, vv in zip(u, v)])
        if L < LIGHT["plate_target_Lstar"]:
            lo = e
        else:
            hi = e
    bpy.data.images.remove(img)
    post = dict(exposure=round(e, 4), wb_gains=[round(float(g), 4) for g in gains],
                reference=dict(xyz=ref_pts, frame=ref_frame, target_Lstar=LIGHT["plate_target_Lstar"]),
                note="gains make the bed-wall patch read #ECE5DA's chroma; one exposure and one balance for every frame (one camera point); "
                     "target L* 87.5 = inside base.png's back wall (85.5 right .. 90 centre .. 91.4 left)")
    for fid in frames:
        img, lin = toner.load(os.path.join(r4.EXR_DIR, f"{fid}.exr"))
        t = T.shoulder(toner.tone(img, lin, e, gains))
        bpy.data.images.remove(img)
        T.save_png(t, os.path.join(out_dir, f"{fid}.png"))
    return post


def readings(path, ids_path):
    """Median Lab per material id on the toned clay, and the bed-wall L* left / centre / right."""
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
    ids = np.asarray(Image.open(ids_path))
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    Mx = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ Mx.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    lab = np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
    out = {}
    for g in (1, 2, 5, 9, 10, 12, 13, 14, 20, 21, 23, 24, 25):
        m = ids == g
        if m.sum() > 50:
            out[IDS[g]] = [round(float(x), 1) for x in np.median(lab[m], 0)]
    H, W = ids.shape
    wall = ids == 1
    for nm, (xa, xb) in (("bed wall L*, left third", (0.15, 0.33)), ("bed wall L*, centre", (0.40, 0.60)), ("bed wall L*, right third", (0.67, 0.85))):
        mm = wall.copy()
        mm[:, :int(xa * W)] = False
        mm[:, int(xb * W):] = False
        mm[int(0.45 * H):, :] = False
        if mm.sum() > 50:
            out[nm] = round(float(np.median(lab[mm][:, 0])), 1)
    x0, y0, x1, y1 = [int(round(c)) for c in FRAME_BOX]
    rgb = a * 255
    out["frame_mean_L_8bit"] = round(float((rgb[y0:y1, x0:x1] * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1)
    return out


# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="MB0-plate,MB0,MB0-shell")
    ap.add_argument("--res", type=int, default=CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=1.0)
    ap.add_argument("--master-window", type=float, default=LIGHT["window"])
    ap.add_argument("--out", default=OUT)
    a, _ = ap.parse_known_args(argv)
    out = a.out
    os.makedirs(out, exist_ok=True)
    for d in ("exr", "npz", "raw"):
        os.makedirs(os.path.join(SCR, d), exist_ok=True)
    raw = os.path.join(SCR, "raw")
    r3.set_out(raw)
    frames = [f for f in a.frames.split(",") if f]
    t0 = time.time()
    r2.WARM = r3.WARM_R3
    cams, plan_doc = r3.cameras_1_1()
    for fid in FRAMES:
        r3.FRAMES[fid] = r3.FRAMES["MB0"]
        r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT["MB0"]
        cams[fid] = dict(cams["MB0"], id=fid)
    slots = r3.load_slots()
    prop = fr.load_prop()
    plan_path, plan0 = bh.load_plan()
    spec = json.load(open(r3.b4.SPEC_PATH))
    cfg = r3.b4.v4_config(spec)
    S, plan, notes, wl = r2.build_r2(plan0, cfg, a)
    R = r3.registry(S)
    notes["round3"] = r3.neutralise(S) + r3.living_vista(R) + r3.apply_fixes(S, R, slots, cube_lamp=None)
    notes["round4"] = r4.v7_fixes(R)
    notes["round3"] += r3.light_balance(a)
    LIGHT["window"] = a.master_window
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name == "winlight_W-master":
            ob.data.energy *= a.master_window
            notes["round3"].append(f"master window area light x{a.master_window} (= {ob.data.energy:.0f} W): ARC2, daylight the key")
    notes["wm_master"] = wm_master(R)
    fixed = wm_fixed()
    notes["wm_master"] += wm_products(R)
    bpy.context.view_layer.update()
    rep = dict(stage="warm-modern master clay, MB0 (render-agent, 2026-11-17; docs/proposals/wm-master-bedroom-render-2026-11-17.md ch. 1, 2, "
                     "3.2 + 12.2, 6)", date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"], camera=cams["MB0"],
               canvas=dict(px=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], K=K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: tone_frames()",
               light=dict(LIGHT), build_notes=notes, ids=IDS, frames={})
    tmp = tempfile.mkdtemp(prefix="wm-master-")
    r4.OS_STATE["on"] = True
    for fid in frames:
        F = FRAMES[fid]
        r3.set_hidden(fixed, not F["fixed"])
        fplan = dict(placeholders=F["placeholders"], lamps=F["lamps"], also_visible=F.get("also", []), notes=f"warm-modern {fid}")
        Rr = r3.run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, {}, cfg)
        depth, idx, normal = CAPTURE["last"]
        ids, counts, pid = save_passes(fid, out, depth, idx, normal)
        cam = S["cam"]
        r3.set_hidden(fixed, not F["fixed"])
        Rr["id_px"] = counts
        Rr["pidx_to_id"] = pid
        Rr["checks_6_3"] = checks_6_3(fid, cam, ids, Rr.get("items_visible"))
        Rr["boxes_frame"] = {IDS[g]: bbox_f(ids, {g}) for g in sorted(PRODUCT_IDS | FIXED_IDS | {13, 14}) if bbox_f(ids, {g})}
        if fid == "MB0-plate" or (fid == "MB0" and "lock_target" not in rep):
            rep["lock_target"] = "lock-target.json"
            json.dump(dict(frame=f"{fid} clay", canvas=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], camera=cams["MB0"],
                           method="analytic projection of the 3D lines; 'samples' are [x, y, seen] in canvas px, seen = the depth pass agrees",
                           lines=lock_target(cam, depth)), open(os.path.join(out, "lock-target.json"), "w"), indent=1)
        shutil.copy(os.path.join(raw, f"{fid}.png"), os.path.join(SCR, "raw", f"{fid}-untoned.png"))
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr["runtime_s"], "s", flush=True)
    cam = S["cam"]
    ref = "MB0-plate" if "MB0-plate" in frames else frames[0]
    rep["post"] = tone_frames(frames, cam, ref, out)
    for fid in frames:
        rep["frames"][fid]["readings"] = readings(os.path.join(out, f"{fid}.png"), os.path.join(out, f"{fid}-id.png"))
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
