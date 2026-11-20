#!/usr/bin/env python3
"""
framing_wm_dining.py: the warm-modern KITCHEN + DINING as a clay, frames D1 (arrival) and D2 (the pan), render-agent, 2026-11-20. 0 var2 tokens.
Brief: briefs/wm-kitchen-dining-stage1-render-2026-11-20.md, task 1. Spec: master-designer docs/proposals/wm-kitchen-dining-render-2026-11-19.md,
chapter 10 over chapters 1-9: chapter 1 (the architecture KD-1..KD-13, the fixed walnut table, chairs and bench of 1.4, the light of 1.5),
chapter 2 (D1 / D2 unchanged), 3.2 with 10.1 / 10.7 (the defaults that passed the photo check; the gaps stay empty), chapter 7 (rejections).

The scene is the round-4 house clay (../../framing_r4.py, imported, nothing changed there; house plan 1.1) with the kitchen-dining room
rebuilt by wm_shell(), wm_kitchen(), wm_fixed() and wm_products(), as framing_wm_master.py does for the master (same helpers, same post).
Frames (cameras D1 / D2 of docs/house-plan.json: PD (2.80, 3.80, 1.10), yaw -56 / -91, 24 mm, u0 0.52, v0 0.43; the base.png canvas
2720 x 1530 with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57], the round-4 3 % overscan):
  D1 / D2              the defaults clay: shell + kitchen + fixed furniture + the defaults; pendant (D1), sconce and the LED lit
  D1-plate / D2-plate  the empty plate: shell + kitchen + fixed furniture, every product hidden, the lamps off, the LED on (shell_constant)
  D1-shell / D2-shell  the same without the table, chairs and bench: plate / shell is the fixed-furniture shadow (as the living room)
Per frame: <id>.png (toned clay), <id>-depth.png (16 bit, planar, metres = value / 5000), <id>-id.png (legend in selfcheck.json),
<id>-edges.png. selfcheck.json: the projections of 3.2, the boxes, V7Q6 on the clay, the lamps, the post. lock-target.json: named lines.

  cd assets/blockout/house && python3 -B framing/wm-dining-2026-11-20/framing_wm_dining.py --frames D1-plate,D1,D1-shell,D2-plate,D2,D2-shell
"""
import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time

HOUSE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, HOUSE)
_ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]

import framing_r4 as r4  # noqa: E402  (the round-4 house)

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

r3, r2, fr, bh, M = r4.r3, r4.r2, r4.fr, r4.bh, r4.M
bs, ba = r3.bs, r3.ba
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-dining/clay"
OUT = os.path.dirname(os.path.abspath(__file__))
r4.EXR_DIR = os.path.join(SCR, "exr")
CANVAS = (2720, 1530)
K = r4.OS_K
FRAME_BOX = (0.5 * CANVAS[0] * (1 - 1 / K), 0.5 * CANVAS[1] * (1 - 1 / K), 0.5 * CANVAS[0] * (1 + 1 / K), 0.5 * CANVAS[1] * (1 + 1 / K))
DEPTH_UNITS = 5000.0
CAM = dict(loc=(2.80, 3.80, 1.10), yaw={"D1": -56.0, "D2": -91.0})
KD = "kitchen-dining"

# ---- chapter 1 values ---------------------------------------------------------------------------------------------
HEX = dict(plaster="#ECE5DA", oak="#8B6F55", oak_l="#917559", oak_d="#85694F", gap="#2B2724", walnut="#6B4A33", plinth="#3A2A1F",
           stone="#D8C8AE", bronze="#3A322C", taupe="#9C8B7A", bone="#E3DBCF", espresso="#2E2824", brass="#B8955A", hob="#1E1C1B",
           sink="#A99B86", leather="#8A5634", recess="#2E2119",
           # products, from the cards / the photo check (10.1)
           shade="#EFEBE4", cord="#1E1C1B", runner="#A8683F", amphora="#EDE6D9", olive="#7E8461", iron="#262422", candle="#EFE6D6",
           curtain="#E6DDCC", fvase="#E9E6E0", euc="#8E9A88", pad="#C9C0AE", mill="#D8B98F", oil="#E6E1D8", bowl="#ECE7DC", pear="#C9B25A",
           plates="#E8DFCC", mug="#CDBFA6", frame="#5E4130", canvas="#D8C8AE", moon="#2A2826", trav="#D8C2A6", tray="#5E4130",
           soap="#D3BC90", board="#8A5E3B", ptowel="#7A4E2E", paper="#F1EEE8", canister="#E6E3DD", lid="#B08A5E", towel="#A0663A")
ROOM = dict(x=(2.65, 7.25), y=(0.0, 6.20), h=3.00)
SKIN = 0.001
SK = dict(h=0.15, proud=0.015)                                  # skirting 15, 1.5 proud, wall colour (WMC10)
CORNER = dict(c=(7.05, 0.20), r=0.20)                           # [KD-6] the SE corner, tangent at X 7.25 / Y 0
WIN = dict(x=(2.95, 4.75), sill=0.75, head=2.70, y_out=-0.35, frame_d=0.04, sight=0.045, slab_t=0.04, slab_proud=0.02)   # [KD-4]
OPEN = dict(y=(2.97, 4.57), head=2.40)                          # O-living-dining (behind PD), [KD-3] plaster reveals
RUN = dict(front=6.63, y=(0.75, 4.20), top=0.90, top_t=0.04, over=0.03, plinth=0.08, plinth_set=0.08, grip=0.05, grip_d=0.03,
           splash=(0.90, 1.55), splash_t=0.015, sink=(1.00, 1.60), hob=(2.30, 2.90), doors=(1.30, 1.90, 2.30, 2.90, 3.55))
HOOD = dict(x=(6.75, 7.25), y=(2.15, 3.05), z=(1.55, 3.00), r=0.06)        # [KD-9]
SHELVES = dict(x=(7.00, 7.25), ys=((0.75, 2.05), (3.15, 4.20)), z=(1.55, 1.59))  # [KD-10] walnut 4
TALL = dict(y=(4.20, 6.20), top=2.40, niche_y=(4.55, 5.20), niche_z=(0.90, 1.60), niche_back=7.00, oven_y=(5.30, 5.90), oven_z=(0.80, 1.40),
            west_x=(3.95, 6.63), west_y=(5.58, 6.20), west_doors=(4.62, 5.29, 5.96))
TABLE = dict(c=(4.60, 1.65), a=0.80, b=0.425, n=2.6, top=(0.71, 0.75), drums=((4.225, 1.65), (4.975, 1.65)), drum_r=(0.175, 0.20))
CHAIRS = dict(cs=((4.10, 0.90), (4.90, 0.90)), seat=0.45, seat_w=0.46, back_r=0.255, back_z=(0.60, 0.76), leg_r=(0.022, 0.017))
BENCH = dict(x=(3.90, 5.30), y=(2.30, 2.65), z=(0.41, 0.45), r=0.02, legs=((4.00, 4.04), (5.16, 5.20)))
LIGHT = dict(window=4.0, pendant_area_w=40.0, pendant_point_w=14.0, pendant_glow=5.0, sconce_point_w=7.0, sconce_glow=4.0,
             led_w_per_m=10.0, niche_w=4.0, plate_target_Lstar=85.0)

IDS = {0: "nothing / sky", 1: "plaster, east wall (Y 0, window)", 2: "plaster, south wall (X 7.25, kitchen)", 3: "plaster, west wall (Y 6.20)",
       4: "plaster, north wall (X 2.65)", 5: "plaster, rounded corner R 0.20", 6: "ceiling", 7: "ceiling shadow gap (1 cm)",
       8: "curtain slot in the ceiling", 9: "skirting 15, wall colour", 10: "floor, smoked oak planks 22", 11: "floor joints (1.5 mm)",
       12: "window reveals, plaster", 13: "window frame, bronze-espresso", 14: "sill slab, limestone 4 cm", 15: "outside (ground)",
       16: "O-living-dining reveals, plaster",
       20: "table top, walnut (fixed)", 21: "table drum bases, walnut (fixed)", 22: "chairs, walnut (fixed)", 23: "chair seats, cognac leather (fixed)",
       24: "bench, walnut (fixed)",
       30: "lower units, taupe fronts", 31: "plinths, dark", 32: "worktop, limestone 4", 33: "splashback, limestone", 34: "sink basin",
       35: "tap, brushed brass", 36: "hob, black matte", 37: "hood, plaster", 38: "open shelves, walnut 4", 39: "LED profiles",
       40: "tall units south, bone", 41: "tall units west, bone", 42: "coffee niche, walnut lining", 43: "oven, espresso",
       44: "oven bar handle, dark bronze", 45: "grip / door grooves",
       50: "dining-pendant (product)", 51: "pendant cord + canopy (product)", 52: "table-runner (product)", 53: "centerpiece-vase (product)",
       54: "olive sprigs (filler)", 55: "candle-holders (product)", 56: "candles (filler)", 57: "curtains (product)", 58: "floor-vase (product)",
       59: "eucalyptus (filler)", 60: "bench-pad (product)", 61: "condiment-set: mills (product)", 62: "condiment-set: oil cruet (product)",
       63: "bowl (product)", 64: "pears (filler)", 65: "tableware-set (product)", 66: "mug-set (product)", 67: "framed-art frame (product)",
       68: "framed-art canvas (product, blank)", 69: "open-shelf-ceramics: moon jar (product)", 70: "kitchen-sconce (product)",
       71: "sink-set: tray (product)", 72: "sink-set: soap dispenser (product)", 73: "cutting-boards (product)", 74: "paper-towel-holder (product)",
       75: "paper roll (filler)", 76: "canisters (product)", 77: "tea-towel (product)", 90: "other house geometry", 99: "unknown"}
rng_pal = np.random.default_rng(5)
PAL = {0: (0, 0, 0), 1: (236, 229, 218), 2: (214, 205, 192), 3: (196, 188, 178), 4: (180, 172, 160), 5: (225, 215, 200), 6: (245, 241, 233),
       7: (40, 36, 34), 8: (90, 60, 30), 9: (200, 190, 175), 10: (139, 111, 85), 11: (60, 45, 35), 12: (230, 220, 205), 13: (58, 50, 44),
       14: (216, 200, 174), 15: (120, 140, 120), 16: (150, 140, 130), 20: (107, 74, 51), 21: (140, 100, 70), 22: (120, 84, 58),
       23: (138, 86, 52), 24: (160, 115, 80), 30: (156, 139, 122), 31: (58, 42, 31), 32: (216, 200, 174), 33: (200, 185, 160),
       34: (169, 155, 134), 35: (184, 149, 90), 36: (30, 28, 27), 37: (240, 232, 220), 38: (107, 74, 51), 39: (255, 240, 200),
       40: (227, 219, 207), 41: (215, 207, 195), 42: (130, 90, 60), 43: (46, 40, 36), 44: (58, 50, 44), 45: (25, 20, 18)}
for _k in range(50, 78):
    PAL[_k] = tuple(int(v) for v in rng_pal.integers(40, 255, 3))
PAL.update({90: (60, 60, 60), 99: (255, 0, 255)})
PRODUCT_IDS = set(range(50, 78))
FILLER_IDS = {54, 56, 59, 64, 75}
ARCH_IDS = set(range(1, 17)) | set(range(30, 46))
FIXED_IDS = set(range(20, 25))
GROUP_ID = {}
PRODUCTS = ["dining-pendant", "table-runner", "centerpiece-vase", "candle-holders", "curtains", "floor-vase", "bench-pad", "condiment-set",
            "condiment-set-oil", "bowl", "tableware-set", "mug-set", "framed-art", "open-shelf-ceramics", "kitchen-sconce", "sink-set",
            "sink-set-soap", "cutting-boards", "paper-towel-holder", "canisters", "tea-towel"]
FILLERS = [f"{KD}/centerpiece-vase-filler", f"{KD}/candle-holders-filler", f"{KD}/floor-vase-filler", f"{KD}/bowl-filler",
           f"{KD}/paper-towel-holder-filler"]
LEDS = [f"{KD}/wm-led-shelves", f"{KD}/wm-led-niche"]
FRAMES = {"D1": dict(cam="D1", placeholders=PRODUCTS, lamps=[f"{KD}/wm-pendant", f"{KD}/wm-sconce"] + LEDS, also=FILLERS, fixed=True),
          "D1-plate": dict(cam="D1", placeholders=[], lamps=LEDS, fixed=True),
          "D1-shell": dict(cam="D1", placeholders=[], lamps=LEDS, fixed=False),
          "D2": dict(cam="D2", placeholders=PRODUCTS, lamps=[f"{KD}/wm-sconce"] + LEDS, also=FILLERS, fixed=True),
          "D2-plate": dict(cam="D2", placeholders=[], lamps=LEDS, fixed=True),
          "D2-shell": dict(cam="D2", placeholders=[], lamps=LEDS, fixed=False)}
CAPTURE = {}


def mat(name, key, rough=0.9):
    return fr.mat_cache("wm_dining_" + name, HEX[key], rough)


def reg_arch(name, objs, gid, kind="architecture"):
    objs = [o for o in objs if o is not None]
    r2.reg(name, objs, KD, kind)
    GROUP_ID[name] = gid
    return objs


def reg_prod(R, slot, objs, gid, src):
    r3.reg(R, f"{KD}/{slot}", objs, KD, src=src)
    GROUP_ID[f"{KD}/{slot}"] = gid
    return objs


def bx(n, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    return r3.bx("kd_wm_" + n, x0, x1, y0, y1, z0, z1, m, bevel)


def cyl(n, c, r, z0, z1, m, verts=48):
    return r3.cyl("kd_wm_" + n, c, r, z0, z1, m, verts)


def cone(n, c, r0, r1, z0, z1, m, verts=48):
    return r3.cone("kd_wm_" + n, c, r0, r1, z0, z1, m, verts)


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
    return mesh_obj("kd_wm_" + name, v, f, m)


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


def ellipse_xy(c, rx, ry, seg=64, n=2.0):
    out = []
    for k in range(seg):
        t = 2 * math.pi * k / seg
        ct, st = math.cos(t), math.sin(t)
        out.append((c[0] + rx * math.copysign(abs(ct) ** (2 / n), ct), c[1] + ry * math.copysign(abs(st) ** (2 / n), st)))
    return out


def kill_names(prefixes=(), exact=()):
    objs = [o for o in bpy.data.objects if o.name in exact or any(o.name.startswith(p) for p in prefixes)]
    return r2.kill_objs(objs)


# ---------------------------------------------------------------------------------------------------------------
# [KD-1]..[KD-6]: the shell
# ---------------------------------------------------------------------------------------------------------------
OLD_PREFIXES = ("kitchen-dining_cornice", "kitchen-dining_plank", "kitchen-dining_skirt", "W-dining_", "dtab_r2", "dch_r2", "dbench_r2", "klow_",
                "ksink", "ktap", "khob", "khood", "kshelf", "ktall_", "kniche_", "koven", "kled", "kniche_led", "ksconce")


def wm_shell(R):
    notes = []
    for key in [k for k in list(r2.LAMPS) if k.startswith(f"{KD}/")]:
        r3.lamp_off(key)
        r2.LAMPS.pop(key, None)
    n = kill_names(prefixes=OLD_PREFIXES)
    for key in list(fr.REG):
        fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if r3.alive(o)]
    for key in [k for k in list(R) if k.startswith(f"{KD}/")]:
        r3.kill_group(R, key)
    notes.append(f"removed {n} objects of the 1.1 kitchen-dining (cornice, planks 25, skirting, the 1.1 window, the oak table, chairs, "
                 "bench and the kitchen run of round 2) and every kitchen-dining proxy; the round-2 kitchen lamps off")
    x0, x1 = ROOM["x"]
    y0, y1 = ROOM["y"]
    H = ROOM["h"]
    pl, gp = mat("plaster", "plaster", 0.95), mat("gap", "gap", 0.9)
    st, bz = mat("stone", "stone", 0.75), mat("bronze", "bronze", 0.55)
    ye = y0 + SKIN                                            # east (window) wall skin: room face at Y 0.002
    xs = x1 - SKIN                                            # south wall skin: room face at X 7.248
    yw = y1 - SKIN                                            # west wall skin
    xn = x0 + SKIN                                            # north wall skin
    cx, cy = CORNER["c"]
    sh = SK["h"]
    wx0, wx1 = WIN["x"]
    slab_z0 = WIN["sill"] - WIN["slab_t"]
    reg_arch("kd_wm plaster east wall", [r3.bx("kd_wm_pl_e_a", x0, wx0, ye, ye + 0.001, sh, H, pl),
                                         r3.bx("kd_wm_pl_e_b", wx0, wx1, ye, ye + 0.001, sh, slab_z0, pl),
                                         r3.bx("kd_wm_pl_e_c", wx0, wx1, ye, ye + 0.001, WIN["head"], H, pl),
                                         r3.bx("kd_wm_pl_e_d", wx1, cx, ye, ye + 0.001, sh, H, pl)], 1)
    reg_arch("kd_wm plaster south wall", [r3.bx("kd_wm_pl_s", xs - 0.001, xs, cy, y1, sh, H, pl)], 2)
    reg_arch("kd_wm plaster west wall", [r3.bx("kd_wm_pl_w", x0, x1, yw - 0.001, yw, sh, H, pl)], 3)
    reg_arch("kd_wm plaster north wall", [r3.bx("kd_wm_pl_n_a", xn, xn + 0.001, y0, OPEN["y"][0], sh, H, pl),
                                          r3.bx("kd_wm_pl_n_b", xn, xn + 0.001, OPEN["y"][0], OPEN["y"][1], OPEN["head"], H, pl),
                                          r3.bx("kd_wm_pl_n_c", xn, xn + 0.001, OPEN["y"][1], y1, sh, H, pl)], 4)
    rf = CORNER["r"] - 2 * SKIN
    shell = arc((cx, cy), rf, 270, 360, 24) + arc((cx, cy), CORNER["r"] + 0.03, 360, 270, 24)
    reg_arch("kd_wm plaster corner R 0.20", [prism("corner", shell, "z", sh, H, pl)], 5)
    p = SK["proud"]
    skirt = [r3.bx("kd_wm_sk_e", x0, cx, y0, ye + p, 0.0, sh, pl),
             r3.bx("kd_wm_sk_s", xs - p, x1, cy, RUN["y"][0], 0.0, sh, pl),
             r3.bx("kd_wm_sk_w", x0, TALL["west_x"][0], yw - p, y1, 0.0, sh, pl),
             r3.bx("kd_wm_sk_n_a", x0, xn + p, y0, OPEN["y"][0], 0.0, sh, pl), r3.bx("kd_wm_sk_n_b", x0, xn + p, OPEN["y"][1], y1, 0.0, sh, pl),
             prism("sk_corner", arc((cx, cy), CORNER["r"] - 2 * SKIN - p, 270, 360, 24) + arc((cx, cy), CORNER["r"] + 0.03, 360, 270, 24),
                   "z", 0.0, sh, pl)]
    reg_arch("kd_wm skirting 15 (wall colour)", skirt, 9)
    cz = H - 0.0005
    reg_arch("kd_wm ceiling shadow gap", [r3.bx("kd_wm_cg_e", x0, x1, y0, y0 + 0.01, cz - 0.0005, cz, gp),
                                          r3.bx("kd_wm_cg_s", x1 - 0.01, x1, y0, y1, cz - 0.0005, cz, gp),
                                          r3.bx("kd_wm_cg_w", x0, x1, y1 - 0.01, y1, cz - 0.0005, cz, gp),
                                          r3.bx("kd_wm_cg_n", x0, x0 + 0.01, y0, y1, cz - 0.0005, cz, gp)], 7)
    reg_arch("kd_wm curtain slot", [r3.bx("kd_wm_slot", wx0 - 0.10, 5.00, y0 + 0.03, y0 + 0.14, cz - 0.0006, cz, gp)], 8)
    # floor: smoked oak 22 cm planks along Y, staggered, 1.5 mm gaps, three tones (+-2 %), continuous from the living room (no threshold)
    rng = np.random.default_rng(23)
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
                planks.append(r3.bx(f"kd_wm_pk{k}_{j}", xa, xb, ya, yb_, -0.012, 0.0, oaks[int(rng.integers(0, 3))]))
            yk += L
            j += 1
        xk += W
        k += 1
    reg_arch("kd_wm floor smoked oak 22", planks, 10)
    notes.append(f"floor: {len(planks)} planks of 22 cm along Y, staggered ends, 1.5 mm gaps, three tones of #8B6F55")
    # W-dining: plaster reveals, bronze frame at the outer face (45 mm, two fields of 0.90, no transom), limestone slab 4 cm
    yo, fd, s = WIN["y_out"], WIN["frame_d"], WIN["sight"]
    yf = yo + fd
    rev = [r3.bx("kd_wm_rev_a", wx0, wx0 + 0.001, yf, ye, WIN["sill"], WIN["head"], pl),
           r3.bx("kd_wm_rev_b", wx1 - 0.001, wx1, yf, ye, WIN["sill"], WIN["head"], pl),
           r3.bx("kd_wm_rev_h", wx0, wx1, yf, ye, WIN["head"] - 0.001, WIN["head"], pl)]
    reg_arch("kd_wm window reveals (plaster)", rev, 12)
    mx = (wx0 + wx1) / 2
    frm = [r3.bx("kd_wm_wf_a", wx0, wx0 + s, yo, yf, WIN["sill"], WIN["head"], bz), r3.bx("kd_wm_wf_b", wx1 - s, wx1, yo, yf, WIN["sill"], WIN["head"], bz),
           r3.bx("kd_wm_wf_t", wx0, wx1, yo, yf, WIN["head"] - s, WIN["head"], bz), r3.bx("kd_wm_wf_bt", wx0, wx1, yo, yf, WIN["sill"], WIN["sill"] + s, bz),
           r3.bx("kd_wm_wf_m", mx - s / 2, mx + s / 2, yo, yf, WIN["sill"], WIN["head"], bz)]
    reg_arch("kd_wm window frame (bronze)", frm, 13)
    slab = [r3.bx("kd_wm_sill_slab", wx0, wx1, yf, ye + WIN["slab_proud"] - SKIN, slab_z0, WIN["sill"], st, 0.003)]
    reg_arch("kd_wm sill slab (limestone)", slab, 14)
    gs = bpy.data.objects.get("ground_slab")
    if gs is not None:
        reg_arch("kd_wm outside ground", [gs], 15)
    oy0, oy1 = OPEN["y"]
    orv = [r3.bx("kd_wm_or_a", 2.50, x0 + 0.002, oy0, oy0 + 0.001, 0.0, OPEN["head"], pl), r3.bx("kd_wm_or_b", 2.50, x0 + 0.002, oy1 - 0.001, oy1, 0.0, OPEN["head"], pl),
           r3.bx("kd_wm_or_h", 2.50, x0 + 0.002, oy0, oy1, OPEN["head"] - 0.001, OPEN["head"], pl)]
    reg_arch("kd_wm O-living-dining reveals (plaster)", orv, 16)
    notes.append(f"W-dining: frame Y {yo}..{yf} at the outer face, sight {s * 1000:.0f} mm, mullion at X {mx:.2f} (two fields of 0.90), "
                 f"no transom; limestone slab Z {slab_z0:.2f}-{WIN['sill']:.2f}, 2 cm proud; [KD-3] plaster reveals in O-living-dining")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# [KD-7]..[KD-11]: the built kitchen (shell, not sold), and the LED (shell_constant)
# ---------------------------------------------------------------------------------------------------------------
def wm_kitchen():
    notes = []
    tp, pli, st = mat("taupe", "taupe", 0.85), mat("plinth", "plinth", 0.8), mat("stone", "stone", 0.75)
    snk, brs, hb = mat("sink", "sink", 0.7), mat("brass", "brass", 0.4), mat("hob", "hob", 0.55)
    pl, wal, bn = mat("plaster", "plaster", 0.95), mat("walnut", "walnut", 0.7), mat("bone", "bone", 0.85)
    esp, bz, rc = mat("espresso", "espresso", 0.6), mat("bronze", "bronze", 0.55), mat("recess", "recess", 0.9)
    x1 = ROOM["x"][1]
    xf = RUN["front"]
    ya, yb = RUN["y"]
    zt = RUN["top"]
    zp = RUN["plinth"]
    zg = zt - RUN["top_t"] - RUN["grip"]                     # the grip groove under the worktop
    lower = [bx("low_front", xf, x1, ya, yb, zp, zg, tp), bx("low_grip_back", xf + RUN["grip_d"], x1, ya, yb, zg, zt - RUN["top_t"], tp)]
    grooves = [bx("low_grip_shadow", xf + RUN["grip_d"] - 0.001, xf + RUN["grip_d"], ya, yb, zg, zt - RUN["top_t"], rc)]
    for k, yy in enumerate(RUN["doors"]):
        grooves.append(bx(f"low_groove{k}", xf - 0.0005, xf + 0.004, yy - 0.0015, yy + 0.0015, zp, zg, rc))
    grooves.append(bx("low_groove_drawer", xf - 0.0005, xf + 0.004, RUN["hob"][0], RUN["hob"][1], 0.47, 0.473, rc))
    plinths = [bx("low_plinth", xf + RUN["plinth_set"], x1, ya, yb, 0.0, zp, pli)]
    top = [bx("worktop", xf - RUN["over"], x1, ya, yb, zt - RUN["top_t"], zt, st, 0.003)]
    splash = [bx("splash", x1 - 0.002 - RUN["splash_t"], x1 - 0.002, ya, yb, RUN["splash"][0], RUN["splash"][1], st)]
    sink = [bx("sink", 6.73, 7.13, RUN["sink"][0] + 0.03, RUN["sink"][1] - 0.03, zt - 0.20, zt + 0.0005, snk)]
    tap = [cyl("tap", (7.16, 1.30), 0.012, zt, zt + 0.32, brs, 20),
           r2.obox("kd_wm_tap_spout", (7.16, 1.30, zt + 0.31), (6.99, 1.30, zt + 0.31), (0, 1, 0), 0.022, 0.022, brs),
           r2.obox("kd_wm_tap_lever", (7.16, 1.30, zt + 0.20), (7.16, 1.38, zt + 0.22), (1, 0, 0), 0.012, 0.012, brs)]
    hob = [bx("hob", 6.68, 7.20, RUN["hob"][0], RUN["hob"][1], zt - 0.0005, zt + 0.0015, hb)]
    hood = [prism("hood", rrect_xy(HOOD["x"][0], x1 - 0.002, HOOD["y"][0], HOOD["y"][1], HOOD["r"], corners=(True, False, False, True)),
                  "z", HOOD["z"][0], HOOD["z"][1] - 0.001, pl)]
    shelves = [bx(f"shelf{k}", SHELVES["x"][0], x1 - 0.002, a, b, SHELVES["z"][0], SHELVES["z"][1], wal, 0.003) for k, (a, b) in enumerate(SHELVES["ys"])]
    # tall units, south (Y 4.20-6.20) to 2.40, bone, with the walnut-lined coffee niche and the espresso oven
    ty0, ty1 = TALL["y"]
    ny0, ny1 = TALL["niche_y"]
    nz0, nz1 = TALL["niche_z"]
    tall = [bx("tall_a", xf, x1, ty0, ny0, zp, TALL["top"], bn), bx("tall_b", xf, x1, ny1, ty1, zp, TALL["top"], bn),
            bx("tall_c", xf, x1, ny0, ny1, zp, nz0, bn), bx("tall_d", xf, x1, ny0, ny1, nz1, TALL["top"], bn)]
    tall_pl = [bx("tall_plinth", xf + RUN["plinth_set"], x1, ty0, ty1, 0.0, zp, pli)]
    lin = 0.012
    niche = [bx("niche_back", TALL["niche_back"], TALL["niche_back"] + 0.02, ny0, ny1, nz0, nz1, wal),
             bx("niche_s1", xf, TALL["niche_back"], ny0, ny0 + lin, nz0 + lin, nz1 - lin, wal),
             bx("niche_s2", xf, TALL["niche_back"], ny1 - lin, ny1, nz0 + lin, nz1 - lin, wal),
             bx("niche_top", xf, TALL["niche_back"], ny0, ny1, nz1 - lin, nz1, wal), bx("niche_bot", xf, TALL["niche_back"], ny0, ny1, nz0, nz0 + lin, wal)]
    oy0, oy1 = TALL["oven_y"]
    oz0, oz1 = TALL["oven_z"]
    oven = [bx("oven", xf - 0.012, xf, oy0, oy1, oz0, oz1, esp)]
    bar = [bx("oven_bar", xf - 0.050, xf - 0.034, oy0 + 0.03, oy1 - 0.03, oz1 - 0.07, oz1 - 0.054, bz),
           bx("oven_bo1", xf - 0.034, xf - 0.012, oy0 + 0.05, oy0 + 0.065, oz1 - 0.066, oz1 - 0.058, bz),
           bx("oven_bo2", xf - 0.034, xf - 0.012, oy1 - 0.065, oy1 - 0.05, oz1 - 0.066, oz1 - 0.058, bz)]
    for k, (a, b, za, zb) in enumerate(((ny1, ty1, oz0 - 0.0015, oz0 + 0.0015), (ny1, ty1, oz1 - 0.0015, oz1 + 0.0015))):
        grooves.append(bx(f"tall_hgroove{k}", xf - 0.0005, xf + 0.004, a, b, za, zb, rc))
    for k, yy in enumerate((ny0, ny1, 5.70)):
        grooves.append(bx(f"tall_vgroove{k}", xf - 0.0005, xf + 0.004, yy - 0.0015, yy + 0.0015, zp, TALL["top"], rc))
    # tall units on the west wall (X 3.95-6.63, Y 5.58-6.20), bone, to 2.40
    wx0, wx1 = TALL["west_x"]
    wy0, wy1 = TALL["west_y"]
    west = [bx("west_tall", wx0, wx1, wy0, wy1, zp, TALL["top"], bn)]
    west_pl = [bx("west_plinth", wx0, wx1, wy0 + RUN["plinth_set"], wy1, 0.0, zp, pli)]
    for k, xx in enumerate(TALL["west_doors"]):
        grooves.append(bx(f"west_groove{k}", xx - 0.0015, xx + 0.0015, wy0 - 0.004, wy0 + 0.0005, zp, TALL["top"], rc))
    reg_arch("kd_wm lower units (taupe)", lower, 30, kind="furniture")
    reg_arch("kd_wm plinths", plinths + tall_pl + west_pl, 31, kind="furniture")
    reg_arch("kd_wm worktop (limestone)", top, 32, kind="furniture")
    reg_arch("kd_wm splashback (limestone)", splash, 33, kind="furniture")
    reg_arch("kd_wm sink", sink, 34, kind="furniture")
    reg_arch("kd_wm tap (brushed brass)", tap, 35, kind="furniture")
    reg_arch("kd_wm hob", hob, 36, kind="furniture")
    reg_arch("kd_wm hood (plaster)", hood, 37, kind="furniture")
    reg_arch("kd_wm shelves (walnut 4)", shelves, 38, kind="furniture")
    reg_arch("kd_wm tall units south (bone)", tall, 40, kind="furniture")
    reg_arch("kd_wm tall units west (bone)", west, 41, kind="furniture")
    reg_arch("kd_wm coffee niche (walnut)", niche, 42, kind="furniture")
    reg_arch("kd_wm oven (espresso)", oven, 43, kind="furniture")
    reg_arch("kd_wm oven bar (dark bronze)", bar, 44, kind="furniture")
    reg_arch("kd_wm grip and door grooves", grooves, 45, kind="furniture")
    # LED: a hidden 2700 K profile under each shelf (a soft wash on the stone), and one at the top of the niche (shell_constant)
    leds, ll = [], []
    for k, (a, b) in enumerate(SHELVES["ys"]):
        leds.append(bx(f"led{k}", 7.03, 7.06, a + 0.02, b - 0.02, SHELVES["z"][0] - 0.0035, SHELVES["z"][0] - 0.0005, mat("led", "candle", 0.5)))
        ll.append(r2.mk_light(f"kd_wm_led_L{k}", "AREA", (7.045, (a + b) / 2, SHELVES["z"][0] - 0.004), LIGHT["led_w_per_m"] * (b - a), size=0.03,
                              size_y=b - a - 0.04, shape="RECTANGLE", long_axis=(0, 1, 0)))
    nled = bx("niche_led", xf + 0.03, xf + 0.06, ny0 + 0.02, ny1 - 0.02, nz1 - lin - 0.0035, nz1 - lin - 0.0005, mat("led", "candle", 0.5))
    reg_arch("kd_wm LED profiles", leds + [nled], 39, kind="architecture")
    r2.lamp(f"{KD}/wm-led-shelves", KD, "cabinet", [(o, r2.GLOW_LED) for o in leds], ll, "LED under both walnut shelves (shell)", shell=True)
    r2.lamp(f"{KD}/wm-led-niche", KD, "cabinet", [(nled, r2.GLOW_LED)],
            [r2.mk_light("kd_wm_niche_L", "AREA", (xf + 0.045, (ny0 + ny1) / 2, nz1 - lin - 0.004), LIGHT["niche_w"], size=0.03, size_y=ny1 - ny0 - 0.04,
                         shape="RECTANGLE", long_axis=(0, 1, 0))], "coffee-niche LED (shell)", shell=True)
    notes.append("kitchen: taupe lowers (front 6.63) with a shadowed grip groove and 3 mm door grooves, no handles; limestone worktop Z 0.86-0.90 "
                 "and splash Z 0.90-1.55; undermount sink Y 1.03-1.57, brushed-brass L tap, flush black hob; plaster hood with R 0.06 front "
                 "corners; walnut shelves 4 cm with a hidden LED each; bone talls (south and west) to 2.40, walnut niche with LED, espresso oven "
                 "with a dark-bronze bar")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# 1.4: the fixed walnut table, chairs and bench (not sold, plan B)
# ---------------------------------------------------------------------------------------------------------------
def wm_fixed():
    wal, lea = mat("walnut", "walnut", 0.7), mat("leather", "leather", 0.6)
    T = TABLE
    top = [prism("table_top", ellipse_xy(T["c"], T["a"], T["b"], 96, T["n"]), "z", T["top"][0], T["top"][1], wal)]
    drums = [prism(f"table_drum{i}", ellipse_xy(c, T["drum_r"][0], T["drum_r"][1], 48), "z", 0.0, T["top"][0], wal) for i, c in enumerate(T["drums"])]
    ch, seats = [], []
    C = CHAIRS
    for i, (cx, cy) in enumerate(C["cs"]):
        hw = C["seat_w"] / 2
        seats.append(prism(f"chair{i}_seat", rrect_xy(cx - hw, cx + hw, cy - hw, cy + hw, 0.05), "z", C["seat"] - 0.03, C["seat"] + 0.01, lea))
        ch.append(prism(f"chair{i}_frame", rrect_xy(cx - hw, cx + hw, cy - hw, cy + hw, 0.05), "z", C["seat"] - 0.06, C["seat"] - 0.03, wal))
        for j, (dx, dy) in enumerate(((-0.17, -0.17), (0.17, -0.17), (-0.19, 0.19), (0.19, 0.19))):
            ztop = C["back_z"][1] if dy < 0 else C["seat"] - 0.06
            ch.append(cone(f"chair{i}_leg{j}", (cx + dx, cy + dy), C["leg_r"][1], C["leg_r"][0], 0.0, ztop, wal, 20))
        band = arc((cx, cy), C["back_r"], 180, 360, 24) + arc((cx, cy), C["back_r"] - 0.03, 360, 180, 24)
        ch.append(prism(f"chair{i}_back", band, "z", C["back_z"][0], C["back_z"][1], wal))
    B = BENCH
    bench = [prism("bench_seat", rrect_xy(B["x"][0], B["x"][1], B["y"][0], B["y"][1], B["r"]), "z", B["z"][0], B["z"][1], wal)]
    bench += [bx(f"bench_leg{i}", a, b, B["y"][0] + 0.02, B["y"][1] - 0.02, 0.0, B["z"][0], wal) for i, (a, b) in enumerate(B["legs"])]
    reg_arch("kd_wm table top (fixed)", top, 20, kind="furniture")
    reg_arch("kd_wm table drums (fixed)", drums, 21, kind="furniture")
    reg_arch("kd_wm chairs (fixed)", ch, 22, kind="furniture")
    reg_arch("kd_wm chair seats (fixed)", seats, 23, kind="furniture")
    reg_arch("kd_wm bench (fixed)", bench, 24, kind="furniture")
    return top + drums + ch + seats + bench


# ---------------------------------------------------------------------------------------------------------------
# 3.2 + 10.1 + 10.7: the defaults that passed, as boxes at their slot envelopes; the gaps empty
# ---------------------------------------------------------------------------------------------------------------
def wm_products(R):
    notes = []
    C = {k: mat(k, k, rough) for k, rough in (("shade", 0.95), ("cord", 0.5), ("runner", 0.95), ("amphora", 0.95), ("olive", 0.9), ("iron", 0.6),
                                              ("candle", 0.9), ("curtain", 0.95), ("fvase", 0.95), ("euc", 0.9), ("pad", 0.95), ("mill", 0.8),
                                              ("oil", 0.85), ("bowl", 0.85), ("pear", 0.8), ("plates", 0.85), ("mug", 0.9), ("frame", 0.7),
                                              ("canvas", 0.95), ("moon", 0.8), ("trav", 0.85), ("tray", 0.7), ("soap", 0.85), ("board", 0.75),
                                              ("ptowel", 0.75), ("paper", 0.95), ("canister", 0.85), ("lid", 0.8), ("towel", 0.95))}
    zt = TABLE["top"][1]
    pc = TABLE["c"]
    # 1. dining-pendant V1: silk ribbed pumpkin 50 x 19 (the SKU drawing), bottom 1.50; canopy 10, rod and cord to the ceiling; lit
    shade = r3.ell("kd_wm_pendant", pc, 0.25, 1.50, 1.69, C["shade"])
    cord = [cyl("pend_cord", pc, 0.004, 1.69, 2.97, C["cord"], 12), cyl("pend_canopy", pc, 0.05, 2.975, 3.0, C["cord"], 24)]
    reg_prod(R, "dining-pendant", [shade] + cord, 50, "10.1 V1 silk ribbed pumpkin 50 (CJYD304604003CX), 50 x 19, bottom 1.50 at (4.60, 1.65)")
    GROUP_ID[f"{KD}/dining-pendant"] = 50
    pl_ = [r2.mk_light("kd_wm_pend_area", "AREA", (pc[0], pc[1], 1.495), LIGHT["pendant_area_w"], size=0.30),
           r2.mk_light("kd_wm_pend_pt", "POINT", (pc[0], pc[1], 1.58), LIGHT["pendant_point_w"], size=0.08)]
    r2.lamp(f"{KD}/wm-pendant", KD, "ceiling", [(shade, LIGHT["pendant_glow"])], pl_, "silk pumpkin 50 (V1)")
    # 2. runner: caramel linen 40 x 140 along the table axis
    reg_prod(R, "table-runner", [bx("runner", 3.90, 5.30, 1.45, 1.85, zt, zt + 0.004, C["runner"])], 52,
             "10.1 caramel 12000044133070215, 40 x 140, X 3.90-5.30, Y 1.45-1.85")
    # 3. centerpiece: the bone amphora Type C 26 (12 wide, loop handles) on the runner, five olive sprigs to Z 1.18
    zr = zt + 0.004
    amph = [cyl("amph_foot", pc, 0.045, zr, zr + 0.03, C["amphora"], 32), cone("amph_body", pc, 0.05, 0.06, zr + 0.03, zr + 0.17, C["amphora"], 32),
            cone("amph_neck", pc, 0.06, 0.045, zr + 0.17, zr + 0.26, C["amphora"], 32),
            r2.obox("kd_wm_amph_h1", (pc[0] - 0.07, pc[1], zr + 0.15), (pc[0] - 0.07, pc[1], zr + 0.22), (0, 1, 0), 0.025, 0.012, C["amphora"]),
            r2.obox("kd_wm_amph_h2", (pc[0] + 0.07, pc[1], zr + 0.15), (pc[0] + 0.07, pc[1], zr + 0.22), (0, 1, 0), 0.025, 0.012, C["amphora"])]
    reg_prod(R, "centerpiece-vase", amph, 53, "10.1 V1 amphora Type C CJYD234431803CX, 12 x 26, loop handles, at (4.60, 1.65) on the runner")
    olive = [r3.ell("kd_wm_olive", (pc[0] + 0.02, pc[1]), 0.10, zr + 0.24, 1.18, C["olive"])]
    reg_prod(R, "centerpiece-vase-filler", olive, 54, "7.5: five olive sprigs at most, top below Z 1.20")
    # 4. candle-holders V1: matte black iron dishes 10.5 x 3 on ball feet, pillar candles 7 x 10 and 7 x 15 (unlit)
    chs, cds = [], []
    for i, ((cx_, cy_), hh) in enumerate((((4.22, 1.61), 0.10), ((4.34, 1.70), 0.15))):
        chs.append(cyl(f"cand_dish{i}", (cx_, cy_), 0.0525, zt, zt + 0.03, C["iron"], 32))
        cds.append(cyl(f"candle{i}", (cx_, cy_), 0.035, zt + 0.02, zt + 0.02 + hh, C["candle"], 32))
    reg_prod(R, "candle-holders", chs, 55, "10.1 V1 matte black iron pillar dishes 12000057351444960, 10.5 x 3, at (4.22, 1.61) / (4.34, 1.70)")
    reg_prod(R, "candle-holders-filler", cds, 56, "pillar candles 7 x 10 and 7 x 15, cream, unlit (7.4)")
    # 5. curtain: one S-fold panel 132 x 270 stacked by the south jamb, X 4.75-4.95, hem Z 0.12, head 2.82 (out of the ceiling slot)
    folds = []
    xs_ = np.linspace(4.775, 4.955, 5)
    for i, xc in enumerate(xs_):
        folds.append(cyl(f"curt{i}", (float(xc), 0.07 + 0.016 * (i % 2)), 0.032, 0.12, 2.82, C["curtain"], 24))
    reg_prod(R, "curtains", folds, 57, "10.1 linen-blend S-fold 132 x 270 (12000059196236244): one stack X 4.75-4.95, hem Z 0.12 (WM-C3), head 2.82")
    # 6. floor-vase: wabi-sabi white 45 x 28 at (6.92, 0.24) in the rounded corner; eucalyptus to Z 1.30 (7.5: <= 1.40, S <= 18)
    fv = (6.92, 0.24)
    fvase = [cone("fvase_lo", fv, 0.11, 0.14, 0.0, 0.25, C["fvase"], 40), cone("fvase_hi", fv, 0.14, 0.06, 0.25, 0.45, C["fvase"], 40)]
    reg_prod(R, "floor-vase", fvase, 58, "10.1 CJYD219411603CX 45 x 28 at (6.92, 0.24)")
    euc = [r3.ell("kd_wm_euc", (fv[0] - 0.03, fv[1] + 0.03), 0.20, 0.55, 1.30, C["euc"])]
    reg_prod(R, "floor-vase-filler", euc, 59, "eucalyptus to Z 1.30 (7.5)")
    # 7. bench-pad: khaki box cushion 130 x 35 x 5, centred on the bench
    B = BENCH
    reg_prod(R, "bench-pad", [bx("pad", 3.95, 5.25, B["y"][0], B["y"][1], B["z"][1], B["z"][1] + 0.05, C["pad"], 0.012)], 60,
             "10.1 V1 khaki 12000045641914363, 130 x 35 x 5 on the bench, X 3.95-5.25")
    # the worktop and the shelves (Z 0.90 / 1.59)
    zw, zs = RUN["top"], SHELVES["z"][1]
    # 8-9. condiment-set: the rubberwood mill pair 15 (Y 3.06-3.14) and the kiln-white oil bottle with a handle 10 x 18 (Y 3.20)
    mills = [cyl("mill_a", (7.12, 3.07), 0.025, zw, zw + 0.152, C["mill"], 24), cyl("mill_b", (7.14, 3.13), 0.025, zw, zw + 0.11, C["mill"], 24)]
    reg_prod(R, "condiment-set", mills, 61, "10.1 rubberwood mill pair 15.2 (one tall, one short as the photo), Y 3.06-3.14")
    oil = [cone("oil_body", (7.12, 3.21), 0.042, 0.034, zw, zw + 0.12, C["oil"], 32), cone("oil_neck", (7.12, 3.21), 0.02, 0.014, zw + 0.12, zw + 0.18, C["oil"], 24)]
    reg_prod(R, "condiment-set-oil", oil, 62, "10.1 kiln-baked white cruet CJYD289918002BY, 10 x 18 with handle and cork, at (7.12, 3.21)")
    # 10. bowl: glutinous white belly bowl 21 x 6.4 at (7.07, 3.55) with three pears
    bw = (7.07, 3.55)
    reg_prod(R, "bowl", [cone("bowl", bw, 0.06, 0.106, zw, zw + 0.064, C["bowl"], 48)], 63, "10.1 V1 white belly bowl 21.2 x 6.4 at (7.07, 3.55)")
    pears = [r3.ell(f"kd_wm_pear{i}", (bw[0] + dx, bw[1] + dy), 0.036, zw + 0.03, zw + 0.03 + hh, C["pear"]) for i, (dx, dy, hh) in
             enumerate(((-0.03, -0.03, 0.10), (0.03, 0.0, 0.095), (-0.01, 0.04, 0.09)))]
    reg_prod(R, "bowl-filler", pears, 64, "three pears (7.4: the only food)")
    # 11. tableware-set: plates 26.7 / 20.3 and bowls 12 as a stack on the right shelf at (7.12, 3.30)
    tw = (7.12, 3.30)
    plates = [cyl("plates_big", tw, 0.1335, zs, zs + 0.03, C["plates"], 48), cyl("plates_small", tw, 0.1015, zs + 0.03, zs + 0.05, C["plates"], 48),
              cone("plates_bowls", tw, 0.035, 0.06, zs + 0.05, zs + 0.11, C["plates"], 40)]
    reg_prod(R, "tableware-set", plates, 65, "10.1 kiln corrugated set 12000057617920292, plates 26.7 / 20.3 + bowls 12 stacked at (7.12, 3.30)")
    # 12. mug-set: three mugs 9.8 x 9 at Y 3.50-3.70 on the right shelf (light brown, cream rim)
    mugs = [cone(f"mug{i}", (7.11, yy), 0.035, 0.045, zs, zs + 0.09, C["mug"], 32) for i, yy in enumerate((3.53, 3.62, 3.70))]
    reg_prod(R, "mug-set", mugs, 66, "10.1 V1 Light brown CJHS114636401AZ, three mugs at Y 3.53 / 3.62 / 3.70")
    # 13. framed-art: 386242 design 05, 30 x 40 landscape, in a 2 cm walnut float frame 44 x 34 leaning on the left shelf, Y 0.90-1.34
    #     (10.7); the canvas blank #D8C8AE (the print goes in by code)
    fx0, fx1 = 7.18, 7.205
    lean = 0.030
    fr_ = r2.obox("kd_wm_art_frame", (7.195, 1.12, zs), (7.195 + lean, 1.12, zs + 0.34), (0, 1, 0), 0.44, 0.022, C["frame"])
    cv_ = r2.obox("kd_wm_art_canvas", (7.180, 1.12, zs + 0.02), (7.180 + lean * 0.30 / 0.34, 1.12, zs + 0.32), (0, 1, 0), 0.40, 0.008, C["canvas"])
    reg_prod(R, "framed-art", [fr_, cv_], 67, "10.7: 386242-05 landscape (12000038963447935), walnut float frame 44 x 34, Y 0.90-1.34, on the left shelf")
    GROUP_ID["kd_wm framed-art canvas"] = 68
    r2.reg("kd_wm framed-art canvas", [cv_], KD, "proxy")
    _ = (fx0, fx1)
    # 14. open-shelf-ceramics: the black moon jar StyleG 23 x 25 at (7.11, 1.55), top Z 1.84
    mj = (7.12, 1.55)
    jar = [cone("moon_lo", mj, 0.07, 0.115, zs, zs + 0.13, C["moon"], 48), cone("moon_hi", mj, 0.115, 0.06, zs + 0.13, zs + 0.23, C["moon"], 48),
           cyl("moon_mouth", mj, 0.05, zs + 0.23, zs + 0.25, C["moon"], 32)]
    reg_prod(R, "open-shelf-ceramics", jar, 69, "10.1 V1 moon jar StyleG (black) CJJT276473907GT, 23 x 25 at (7.11, 1.55)")
    # 15. kitchen-sconce: travertine dome 15, 12 from the wall, plate at (7.25, 1.80, 2.05); lit (a wash on the plaster round it)
    sc = r3.ell("kd_wm_sconce", (7.19, 1.80), 0.075, 1.975, 2.125, C["trav"])
    reg_prod(R, "kitchen-sconce", [sc], 70, "10.1 V1 travertine dome 15 (CJYD219925401AZ), 12 from the wall, centre (7.19, 1.80, 2.05)")
    sl = [r2.mk_light("kd_wm_sconce_pt", "POINT", (7.215, 1.80, 2.05), LIGHT["sconce_point_w"], size=0.05)]
    r2.lamp(f"{KD}/wm-sconce", KD, "wall", [(sc, LIGHT["sconce_glow"])], sl, "travertine dome 15 (V1)")
    # 16-17. sink-set: the walnut tray 20 x 13 (Y 1.64-1.84) and the sand ribbed dispenser 7.5 x 16.5 on it
    tr = [bx("tray", 7.08, 7.21, 1.645, 1.845, zw, zw + 0.015, C["tray"], 0.003)]
    reg_prod(R, "sink-set", tr, 71, "10.1 walnut tray No. 3 CJJJJTJT41624-Brown, 20 x 13 x 1.5, Y 1.645-1.845")
    sp = [cyl("soap", (7.145, 1.70), 0.0375, zw + 0.015, zw + 0.15, C["soap"], 32), cyl("soap_pump", (7.145, 1.70), 0.012, zw + 0.15, zw + 0.18, C["cord"], 16)]
    reg_prod(R, "sink-set-soap", sp, 72, "10.1 striped bottle CJYD301460604DW, 7.5 x 16.5 (black pump), on the tray at (7.145, 1.70)")
    # 18. cutting board 280363 L: acacia-walnut paddle 33 x 20 with a handle, leaning on the splash at Y 2.00
    bd = r2.obox("kd_wm_board", (7.205, 2.00, zw), (7.225, 2.00, zw + 0.33), (0, 1, 0), 0.20, 0.016, C["board"])
    reg_prod(R, "cutting-boards", [bd], 73, "10.1 V1 280363 L (12000059298718531), 33 x 20 paddle, leaning at Y 2.00")
    # 19. paper-towel holder Style C: round base 13, upright 31, at (7.12, 4.05); a white roll (filler)
    pt = (7.12, 4.05)
    ptw = [cyl("pt_base", pt, 0.065, zw, zw + 0.02, C["ptowel"], 40), cyl("pt_post", pt, 0.012, zw + 0.02, zw + 0.31, C["ptowel"], 16)]
    reg_prod(R, "paper-towel-holder", ptw, 74, "10.1 V1 Style C (12000060575834324), 13 x 31 at (7.12, 4.05)")
    reg_prod(R, "paper-towel-holder-filler", [cyl("pt_roll", pt, 0.055, zw + 0.025, zw + 0.255, C["paper"], 40)], 75, "a plain paper roll")
    # 20. canisters: the white set S / M / L with bamboo lids in the niche, Y 4.70-5.04
    zn = TALL["niche_z"][0] + 0.012
    can = []
    for i, (yy, r, hh) in enumerate(((4.70, 0.055, 0.17), (4.87, 0.055, 0.14), (5.03, 0.05, 0.11))):
        can += [cyl(f"can{i}", (6.84, yy), r, zn, zn + hh - 0.02, C["canister"], 40), cyl(f"can_lid{i}", (6.84, yy), r, zn + hh - 0.02, zn + hh, C["lid"], 40)]
    reg_prod(R, "canisters", can, 76, "10.1 zendrop-2814530 white set, L / M / S 11 x 17 / 14 / 11, bamboo lids, in the niche Y 4.70-5.03")
    # 21. tea-towel: caramel linen 38 x 55 folded lengthwise over the oven bar, Y 5.48-5.72
    xb = RUN["front"] - 0.042
    zb = TALL["oven_z"][1] - 0.062
    tt = [bx("towel_front", xb - 0.012, xb - 0.004, 5.49, 5.68, zb - 0.27, zb + 0.012, C["towel"], 0.003),
          bx("towel_back", xb + 0.004, RUN["front"] - 0.013, 5.49, 5.68, zb - 0.25, zb + 0.012, C["towel"], 0.003)]
    reg_prod(R, "tea-towel", tt, 77, "10.1 V1 caramel 12000059652536005, 38 x 55 folded lengthwise over the oven bar, Y 5.49-5.68")
    notes.append("products: the 21 defaults of 10.1 (chapter 10 SKUs); empty: dining-rug, kitchen-runner, utensil-crock, herb-pots, step-stool, "
                 "the shelf jar and the brush (gaps); framed-art canvas blank #D8C8AE")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# passes (as framing_wm_master.py)
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
    counts = {IDS[k]: int((ids == k).sum()) for k in sorted(set(np.unique(ids).tolist())) if k in IDS}
    return ids, counts, {str(k): v for k, v in pid.items()}


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
    x0, y0, x1, y1 = (int(round(c)) for c in FRAME_BOX)
    mf = m[y0:y1, x0:x1]
    return dict(u=[r4_(u0), r4_(u1)], v=[r4_(v0), r4_(v1)], px=int(m.sum()), frame_pct=round(100 * mf.sum() / ((x1 - x0) * (y1 - y0)), 3),
                height_pct=round(100 * (np.ptp(np.nonzero(mf.any(1))[0]) + 1) / (y1 - y0), 2) if mf.any() else 0.0)


PROJ_PTS = {"pendant centre bottom": (4.60, 1.65, 1.50), "rounded corner, arc mid (45 deg)": (7.05 + 0.198 * math.cos(math.radians(315)), 0.20 + 0.198 * math.sin(math.radians(315)), 1.2),
            "window south jamb": (4.75, 0.0, 1.5), "sink centre": (7.10, 1.30, 0.90), "hood centre (front)": (6.75, 2.60, 2.0),
            "niche centre": (6.63, 4.875, 1.25), "tap": (7.16, 1.30, 1.10), "framed-art centre": (7.20, 1.12, 1.76), "sconce": (7.19, 1.80, 2.05),
            "moon jar top": (7.11, 1.55, 1.84), "mugs": (7.11, 3.62, 1.63), "tableware": (7.12, 3.30, 1.65), "bowl": (7.07, 3.55, 0.93),
            "paper towel": (7.12, 4.05, 1.05), "canisters": (6.84, 4.87, 1.00), "tea towel": (6.58, 5.58, 1.20), "floor vase": (6.92, 0.24, 0.45)}


def checks(fid, cam, ids):
    C = {}
    C["projections_frame_uv"] = {k: [r4_(v) for v in UVf(cam, *p)] for k, p in PROJ_PTS.items()}
    C["boxes_frame"] = {IDS[g]: bbox_f(ids, {g}) for g in sorted(PRODUCT_IDS | FIXED_IDS | {13, 14, 37, 42, 43}) if bbox_f(ids, {g})}
    # V7Q6 (a) on the clay: 0.5 % of the frame, or 0.15 % with 6 % height; groups of three as one; the fillers with their product
    groups = {"dining-pendant": {50}, "table-runner": {52}, "centerpiece-vase": {53, 54}, "candle-holders": {55, 56}, "curtains": {57},
              "floor-vase": {58, 59}, "bench-pad": {60}, "condiment-set (mills + oil)": {61, 62}, "bowl": {63, 64}, "tableware-set": {65},
              "mug-set": {66}, "framed-art": {67, 68}, "open-shelf-ceramics": {69}, "kitchen-sconce": {70}, "sink-set (tray + soap)": {71, 72},
              "cutting-boards": {73}, "paper-towel-holder": {74, 75}, "canisters": {76}, "tea-towel": {77}}
    rows = {}
    for g, s in groups.items():
        b = bbox_f(ids, s)
        if not b:
            continue
        ok = b["frame_pct"] >= 0.5 or (b["frame_pct"] >= 0.15 and b["height_pct"] >= 6.0)
        rows[g] = dict(frame_pct=b["frame_pct"], height_pct=b["height_pct"], passes=bool(ok))
    C["v7q6_clay"] = dict(rule="0.5 % of the frame, or 0.15 % and 6 % height (visibility as the clay shows it)", rows=rows,
                          passing=sorted(k for k, v in rows.items() if v["passes"]))
    return C


def lock_target(cam, depth_img, fid):
    H, W = depth_img.shape
    zt = RUN["top"]
    xf = RUN["front"]
    L = {
        "worktop front edge (Z 0.90)": ((xf - RUN["over"], 0.80, zt), (xf - RUN["over"], 4.15, zt)),
        "worktop underside (Z 0.86)": ((xf - RUN["over"], 0.80, zt - RUN["top_t"]), (xf - RUN["over"], 4.15, zt - RUN["top_t"])),
        "splash top / shelf bottom, left (Z 1.55)": ((7.00, 0.78, 1.55), (7.00, 2.02, 1.55)),
        "left shelf front top edge (Z 1.59)": ((7.00, 0.78, 1.59), (7.00, 2.02, 1.59)),
        "right shelf front top edge (Z 1.59)": ((7.00, 3.18, 1.59), (7.00, 4.17, 1.59)),
        "hood, left vertical (Y 2.15)": ((HOOD["x"][0] + HOOD["r"], HOOD["y"][0], 1.60), (HOOD["x"][0] + HOOD["r"], HOOD["y"][0], 2.90)),
        "hood, right vertical (Y 3.05)": ((HOOD["x"][0] + HOOD["r"], HOOD["y"][1], 1.60), (HOOD["x"][0] + HOOD["r"], HOOD["y"][1], 2.90)),
        "hood bottom front edge (Z 1.55)": ((HOOD["x"][0], 2.22, 1.55), (HOOD["x"][0], 2.98, 1.55)),
        "niche, left edge (Y 4.55)": ((xf, 4.55, 0.92), (xf, 4.55, 1.58)), "niche, right edge (Y 5.20)": ((xf, 5.20, 0.92), (xf, 5.20, 1.58)),
        "niche top edge (Z 1.60)": ((xf, 4.57, 1.60), (xf, 5.18, 1.60)), "niche bottom edge (Z 0.90)": ((xf, 4.57, 0.90), (xf, 5.18, 0.90)),
        "tall units top (Z 2.40)": ((xf, 4.22, 2.40), (xf, 6.18, 2.40)), "oven top edge": ((xf - 0.012, 5.32, TALL["oven_z"][1]), (xf - 0.012, 5.88, TALL["oven_z"][1])),
        "lower plinth line (Z 0.08)": ((xf, 0.80, RUN["plinth"]), (xf, 4.15, RUN["plinth"])),
        "window south jamb (X 4.75)": ((WIN["x"][1], 0.001, 0.80), (WIN["x"][1], 0.001, 2.65)),
        "sill slab front top edge": ((3.0, WIN["slab_proud"], WIN["sill"]), (4.70, WIN["slab_proud"], WIN["sill"])),
        "skirting top, east wall right of the window": ((4.80, SK["proud"], SK["h"]), (6.85, SK["proud"], SK["h"])),
        "floor line, east wall": ((4.80, SK["proud"], 0.0), (6.85, SK["proud"], 0.0)),
        "table top far edge (Z 0.75)": ((4.20, 1.234, 0.75), (5.00, 1.234, 0.75)),
        "bench front top edge (Z 0.45)": ((3.95, BENCH["y"][1], 0.45), (5.25, BENCH["y"][1], 0.45)),
        "ceiling, south wall (Z 3.00)": ((7.249, 0.30, 2.999), (7.249, 6.10, 2.999)),
        "west tall units top (Z 2.40)": ((4.0, TALL["west_y"][0], 2.40), (6.60, TALL["west_y"][0], 2.40)),
    }
    out = {}
    import math as _m
    yaw = _m.radians(CAM["yaw"][FRAMES[fid]["cam"]])
    fwd = (-_m.sin(yaw), -_m.cos(yaw))
    for name, (a, b) in L.items():
        pts, vis = [], 0
        for t in np.linspace(0, 1, 41):
            p = [a[i] + (b[i] - a[i]) * t for i in range(3)]
            u, v = fr.U(cam, *p), fr.V(cam, *p)
            if not (0 <= u < 1 and 0 <= v < 1):
                continue
            x, y = int(u * W), int(v * H)
            dp = abs((p[0] - CAM["loc"][0]) * fwd[0] + (p[1] - CAM["loc"][1]) * fwd[1])
            dd = float(depth_img[y, x])
            seen = abs(dd - dp) < 0.02 + 0.01 * dp
            vis += seen
            pts.append([round(u * CANVAS[0], 2), round(v * CANVAS[1], 2), bool(seen)])
        if pts:
            out[name] = dict(xyz=[list(a), list(b)], px_ends=[px(cam, *a), px(cam, *b)], samples=pts, visible_frac=round(vis / len(pts), 3))
    return out


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def Lstar(rgb01):
    lin = np.where(rgb01 <= 0.04045, rgb01 / 12.92, ((rgb01 + 0.055) / 1.055) ** 2.4)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722])
    return float(np.mean(np.where(Y > 0.008856, 116 * np.cbrt(Y) - 16, 903.3 * Y)))


def tone_frames(frames, cams_obj, ref_frame, out_dir, fixed=None):
    """one exposure and one white balance for every frame (one camera point): the south-wall plaster above the shelves reads #ECE5DA's
    chroma at L* 85 (1.5: the east wall 90-94 by the window, 80-85 at the corner)"""
    import tone_r4 as T
    toner = T.Toner()
    if fixed is None:
        cam = cams_obj[ref_frame]
        ref_pts = [(7.249, 1.20, 2.30), (7.249, 3.70, 2.30)]
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
        fixed = dict(exposure=round(e, 4), wb_gains=[round(float(g), 4) for g in gains],
                     reference=dict(xyz=ref_pts, frame=ref_frame, target_Lstar=LIGHT["plate_target_Lstar"]),
                     note="gains make the south-wall plaster above the shelves read #ECE5DA's chroma; one exposure and balance for the six frames")
    e, gains = fixed["exposure"], np.array(fixed["wb_gains"])
    for fid in frames:
        img, lin = toner.load(os.path.join(r4.EXR_DIR, f"{fid}.exr"))
        t = T.shoulder(toner.tone(img, lin, e, gains))
        bpy.data.images.remove(img)
        T.save_png(t, os.path.join(out_dir, f"{fid}.png"))
    return fixed


def readings(path, ids_path):
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
    ids = np.asarray(Image.open(ids_path))
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    Mx = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ Mx.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    lab = np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
    out = {}
    for g in (1, 2, 3, 5, 10, 13, 14, 20, 24, 30, 32, 33, 37, 38, 40, 41, 42, 43):
        m = ids == g
        if m.sum() > 50:
            out[IDS[g]] = [round(float(x), 1) for x in np.median(lab[m], 0)]
    return out


# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="D1-plate,D1,D1-shell,D2-plate,D2,D2-shell")
    ap.add_argument("--res", type=int, default=CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=1.0)
    ap.add_argument("--dining-window", type=float, default=LIGHT["window"])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry", action="store_true", help="build only; list what is left in the room volume")
    a, _ = ap.parse_known_args(argv)
    out = a.out
    os.makedirs(out, exist_ok=True)
    for d in ("exr", "raw"):
        os.makedirs(os.path.join(SCR, d), exist_ok=True)
    raw = os.path.join(SCR, "raw")
    r3.set_out(raw)
    frames = [f for f in a.frames.split(",") if f]
    t0 = time.time()
    r2.WARM = r3.WARM_R3
    cams, plan_doc = r3.cameras_1_1()
    for fid in FRAMES:
        base = FRAMES[fid]["cam"]
        r3.FRAMES[fid] = r3.FRAMES[base]
        r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT[base]
        cams[fid] = dict(cams[base], id=fid)
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
    LIGHT["window"] = a.dining_window
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name == "winlight_W-dining":
            ob.data.energy *= a.dining_window
            notes["round3"].append(f"dining window area light x{a.dining_window} (= {ob.data.energy:.0f} W): ARC2, daylight the key")
    notes["wm_dining"] = wm_shell(R)
    notes["wm_dining"] += wm_kitchen()
    fixed = wm_fixed()
    notes["wm_dining"] += wm_products(R)
    bpy.context.view_layer.update()
    if a.dry:
        mine = set()
        for k, v in fr.REG.items():
            if k.startswith("kd_wm") or k.startswith(f"{KD}/"):
                mine |= {o.name for o in v["objs"] if r3.alive(o)}
        left = []
        for ob in bpy.data.objects:
            if ob.type != "MESH" or ob.name in mine or ob.name.startswith("kd_wm"):
                continue
            c = ob.matrix_world.translation
            bb = [ob.matrix_world @ __import__("mathutils").Vector(v) for v in ob.bound_box]
            xs_ = [p.x for p in bb]
            ys_ = [p.y for p in bb]
            zs_ = [p.z for p in bb]
            if max(xs_) > 2.70 and min(xs_) < 7.20 and max(ys_) > 0.05 and min(ys_) < 6.15 and max(zs_) > 0.02 and min(zs_) < 2.98:
                left.append((ob.name, [round(min(xs_), 2), round(max(xs_), 2), round(min(ys_), 2), round(max(ys_), 2), round(min(zs_), 2), round(max(zs_), 2)],
                             ob.hide_render))
        print(json.dumps(left, indent=0))
        print(json.dumps(notes["wm_dining"], indent=1))
        return
    rep = dict(stage="warm-modern kitchen-dining clay, D1 / D2 (render-agent, 2026-11-20; docs/proposals/wm-kitchen-dining-render-2026-11-19.md ch. 1, "
                     "2, 3.2 + 10.1 + 10.7, 6)", date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"],
               cameras={k: cams[k] for k in ("D1", "D2")},
               canvas=dict(px=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], K=K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: tone_frames()",
               light=dict(LIGHT), build_notes=notes, ids=IDS, frames={})
    tmp = tempfile.mkdtemp(prefix="wm-dining-")
    r4.OS_STATE["on"] = True
    cam_objs = {}
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
        Rr["checks"] = checks(fid, cam, ids)
        if fid.endswith("-plate"):
            json.dump(dict(frame=f"{fid} clay", canvas=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], camera=cams[F["cam"]],
                           method="analytic projection of the 3D lines; 'samples' are [x, y, seen] in canvas px, seen = the depth pass agrees",
                           lines=lock_target(cam, depth, fid)), open(os.path.join(out, f"{F['cam']}-lock-target.json"), "w"), indent=1)
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr.get("runtime_s"), "s", flush=True)
        cam_objs[fid] = cam
        # keep a frozen copy of the camera for the tone step (the camera object is re-aimed per frame)
        cam_objs[fid] = dict(loc=list(cam.location), rot=list(cam.rotation_euler), sx=cam.data.shift_x, sy=cam.data.shift_y)
    ref = "D1-plate" if "D1-plate" in frames else frames[0]
    cam = S["cam"]
    bh.set_view(cam, cams[FRAMES[ref]["cam"]]["loc"], cams[FRAMES[ref]["cam"]]["yaw"], cams[FRAMES[ref]["cam"]]["u0"], cams[FRAMES[ref]["cam"]]["v0"])
    bpy.context.view_layer.update()
    prev = None
    if os.path.exists(os.path.join(out, "post.json")) and "--retone" not in argv:
        prev = json.load(open(os.path.join(out, "post.json")))
    rep["post"] = tone_frames(frames, {ref: cam}, ref, out, fixed=prev)
    json.dump(rep["post"], open(os.path.join(out, "post.json"), "w"), indent=1)
    for fid in frames:
        rep["frames"][fid]["readings"] = readings(os.path.join(out, f"{fid}.png"), os.path.join(out, f"{fid}-id.png"))
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
