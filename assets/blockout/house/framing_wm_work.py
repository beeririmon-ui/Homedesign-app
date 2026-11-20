#!/usr/bin/env python3
"""
framing_wm_work.py: the warm-modern WORK ROOM as a clay, frame W0 (the arched-niche desk wall), render-agent, 2026-11-20. 0 var2 tokens.
Brief: briefs/wm-work-stage1-render-2026-11-20.md, task 1. Spec: master-designer docs/proposals/wm-work-render-2026-11-19.md, chapter 10
over chapters 1-9; chapters 1.2 (shell, [WK-1]..[WK-9]), 1.3 (the fixed walnut desk, shelf and chair, plan B), 2.1 (the frame), 3.2 +
10.1 (the defaults and their places), 10.3 (the wall light on the built-out wall), 6.1 (what the clay measures).

The scene is the round-4 house clay (framing_r4.py, imported, nothing changed there; house plan 1.1) with the work room rebuilt by
wm_work(), wm_fixed() and wm_products(), the way framing_wm_master.py rebuilt the master (nothing changed there either):
  - [WK-1] plaster #ECE5DA as 1 mm skins; ceiling 3.00 with a 1 cm shadow gap; skirting 15 in the wall colour (WMC10);
  - [WK-2] smoked oak #8B6F55 in 22 cm planks along Y;
  - [WK-3] both back corners rounded R 0.20, at the built-out face (Y 6.50);
  - [WK-4] the desk wall built out 0.15 to Y 6.50 over the full width; a plaster niche X -1.625..-0.025 (1.60 wide) left at Y 6.35,
    0.15 deep, with a half-round arch R 0.80 springing at Z 1.50 (crown 2.30); plaster inside, no frame, light or colour change;
  - [WK-5] W-work in the 1.1 opening: bronze-espresso #3A322C steel, 45 mm sight lines, two 0.60 panes, no transom; plaster reveals;
    a 4 cm limestone #D8C8AE slab on the sill;
  - [WK-6] the curtain rail sunk in the ceiling gap; S-fold stacks Y 7.03-7.25 (in W0) and 8.35-8.57, hem 12 cm above the floor;
  - [WK-7] walnut linings in O-hall-work, the leaf in the wall colour (outside W0);
  - [WK-9] / 10.3: the wall light's point on the built-out face, (-1.92, 6.50, 1.65);
  - 1.3 (fixed, not sold): the walnut #6B4A33 desk wall to wall in the niche (4 cm top at 0.76, two 4 cm side panels in line with the
    jambs, one central drawer 70 x 45 x 12 with a finger recess, open below), the walnut shelf (4 cm, 25 deep, top face at 1.66; its
    ends follow the arch), the walnut chair (solid rounded back, four round legs, back 0.85) at (-0.825, 7.30), back to the camera;
  - 10.1 defaults as boxes at their places (19 of 20: the desk lamp Lenni is conditional, 10.2, and is not built).
Frames (camera W0 from docs/house-plan.json: (-0.825, 9.85, 1.10), yaw 0, 24 mm, u0 0.50, v0 0.46; the base.png canvas 2720 x 1530 with
the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57], the round-4 3 % overscan):
  W0         the defaults clay: shell + fixed furniture + the defaults; the pendant and the wall light lit
  W0-plate   the empty plate: shell + desk, shelf, chair; every product hidden, every lamp off
  W0-shell   the shell alone (no desk, shelf or chair): plate / shell is the fixed-furniture shadow (RND2, as the living room)
Per frame: <id>.png (toned clay), <id>-depth.png (16 bit, planar, metres = value / 5000, 65535 = nothing), <id>-id.png (palette;
legend in selfcheck.json), <id>-edges.png. selfcheck.json: the 2.1 / 6.1 numbers, lamps, boxes, the V7Q6 count. lock-target.json.

  python3 framing_wm_work.py --frames W0-plate,W0,W0-shell --samples 16
  python3 framing_wm_work.py --frames W0 --res 960 --samples 4 --out /tmp/x          # smoke test
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
bs = r3.bs
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-work/clay"
OUT = os.path.join(HERE, "framing", "wm-work-2026-11-20")
r4.EXR_DIR = os.path.join(SCR, "exr")
CANVAS = (2720, 1530)
K = r4.OS_K
FRAME_BOX = (0.5 * CANVAS[0] * (1 - 1 / K), 0.5 * CANVAS[1] * (1 - 1 / K), 0.5 * CANVAS[0] * (1 + 1 / K), 0.5 * CANVAS[1] * (1 + 1 / K))
DEPTH_UNITS = 5000.0
CAM = dict(loc=(-0.825, 9.85, 1.10), yaw=0.0)

# ---- chapter 1 / 3 / 10 values -----------------------------------------------------------------------------------
HEX = dict(plaster="#ECE5DA", oak="#8B6F55", oak_l="#917559", oak_d="#85694F", gap="#2B2724", walnut="#6B4A33", recess="#2E2119",
           stone="#D8C8AE", bronze="#3A322C", leather="#8A5A3B",
           curtain="#E6DDCC", frame="#6B4A33", mat="#E9E1D3", canvas="#D8C8AE", trav="#D9C8AE", rug="#D9CDBB", rope="#C9A876",
           kraft="#9C8466", cement="#C8BFB0", crown="#6E7A5C", leatherst="#B5652E", gun="#3B3A3D", mags="#DCD3C4",
           beech="#5B3F2C", steel="#1E1C1B", book_bone="#E3DACB", book_oat="#CDBB9C", book_taupe="#9C8E7E", book_esp="#3E322A",
           sand="#E4DDD2", burnt="#4A3A2E", pen="#E2D6BF", pencil="#B79B74", vase="#E3D9C6", hiba="#CFC4B3", dish="#B98E6A",
           shade="#EEE5D3", brass="#B8955A", throw="#93603F")
ROOM = dict(x=(-2.30, 0.65), y=(6.35, 10.10), h=3.00)
YB = 6.50                                                        # [WK-4] the built-out face
SKIN = 0.001
SK = dict(h=0.15, proud=0.015)                                   # skirting 15, 1.5 proud, wall colour (WMC10)
CORNERS = dict(left=dict(c=(-2.10, 6.70), a=(180, 270)), right=dict(c=(0.45, 6.70), a=(270, 360)), r=0.20)   # [WK-3]
NICHE = dict(x=(-1.625, -0.025), back=6.35, c=(-0.825, 1.50), r=0.80)                                            # [WK-4]
WIN = dict(y=(7.15, 8.35), sill=0.75, head=2.70, x_out=-2.65, frame_d=0.04, sight=0.045, slab_t=0.04, slab_proud=0.02)
DOOR = dict(y=(8.10, 9.00), x=(0.65, 0.80), head=2.40)
CURTAIN = dict(stacks=((7.03, 7.25), (8.35, 8.57)), n=6, r=0.037, x=(-2.263, -2.247), z=(0.12, 2.82), rail=(7.01, 8.59))
DESK = dict(x=(-1.625, -0.025), y=(6.35, 6.95), top=(0.72, 0.76), side_t=0.04, drawer=dict(x=(-1.175, -0.475), z=(0.60, 0.72)))
SHELF = dict(y=(6.35, 6.60), z=(1.62, 1.66), inset=0.006)
CHAIR = dict(c=(-0.825, 7.30), seat=(0.43, 0.46), back=(0.62, 0.85), back_r=0.235, back_t=0.025, leg_r=0.020)
SCONCE = dict(c=(-1.92, 6.50, 1.65), s=0.12)                     # 10.3: the travertine cube on the built-out face
PENDANT = dict(c=(-0.825, 6.82), d=0.30, z=(1.58, 1.77))          # 10.1 row 19: silk ribbed pumpkin 30 (height not published: 19)
LIGHT = dict(window=6.0, pend_area_w=26.0, pend_glow=4.0, sconce_spot_w=14.0, sconce_glow=3.0, plate_target_Lstar=87.5)

IDS = {0: "nothing / sky", 1: "plaster, built-out desk wall (Y 6.50) and the arch spandrels", 2: "plaster, window wall (X -2.30)",
       3: "plaster, back wall (Y 10.10)", 4: "plaster, right wall (X 0.65)", 5: "plaster, rounded corners R 0.20", 6: "ceiling",
       7: "ceiling shadow gap", 8: "curtain slot", 9: "skirting", 10: "floor, smoked oak", 11: "floor joints", 12: "window reveals",
       13: "window frame (bronze)", 14: "sill slab (limestone)", 15: "outside ground", 16: "doors (leaf + walnut linings)",
       17: "plaster, niche back wall (Y 6.35)", 18: "plaster, niche jambs and arch soffit",
       20: "desk top (fixed walnut)", 21: "desk side panels (fixed)", 22: "desk drawer front (fixed)", 23: "desk drawer recess (fixed)",
       24: "shelf (fixed walnut)", 25: "chair (fixed walnut)", 26: "chair seat (cognac leather)",
       40: "curtains", 41: "framed-art (frame + mat)", 42: "framed-art canvas", 43: "framed-art-2 (frame + mat)",
       44: "framed-art-2 canvas", 45: "wall-sconce (cube)", 46: "rug", 47: "basket", 48: "waste-basket", 49: "planter",
       50: "planter filler (Rhapis)", 51: "magazine-holder", 52: "magazine filler", 53: "bookends", 54: "bookends filler (books)",
       55: "shelf-vase", 56: "shelf-object (burnt bowl)", 57: "desk-tray", 58: "desk-organizer", 59: "desk-organizer filler (pencils)",
       60: "desk-vase", 61: "desk-candle (Hiba)", 62: "desk-dish", 63: "pendant", 64: "chair-throw", 90: "other"}
PAL = {0: (0, 0, 0), 1: (236, 229, 218), 2: (214, 205, 192), 3: (196, 188, 178), 4: (180, 172, 160), 5: (225, 215, 200),
       6: (250, 248, 244), 7: (60, 56, 52), 8: (90, 84, 78), 9: (205, 196, 182), 10: (139, 111, 85), 11: (70, 55, 42),
       12: (200, 190, 176), 13: (58, 50, 44), 14: (216, 200, 174), 15: (120, 140, 110), 16: (150, 110, 80), 17: (226, 218, 205),
       18: (210, 200, 186), 20: (107, 74, 51), 21: (92, 64, 44), 22: (120, 84, 58), 23: (46, 33, 25), 24: (130, 92, 64),
       25: (82, 57, 40), 26: (138, 90, 59), 40: (230, 221, 204), 41: (160, 110, 70), 42: (216, 200, 174), 43: (170, 120, 80),
       44: (200, 184, 160), 45: (217, 200, 174), 46: (217, 205, 187), 47: (201, 168, 118), 48: (156, 132, 102), 49: (200, 191, 176),
       50: (110, 122, 92), 51: (181, 101, 46), 52: (220, 211, 196), 53: (91, 63, 44), 54: (205, 187, 156), 55: (228, 221, 210),
       56: (74, 58, 46), 57: (220, 205, 180), 58: (226, 214, 191), 59: (183, 155, 116), 60: (227, 217, 198), 61: (207, 196, 179),
       62: (185, 142, 106), 63: (238, 229, 211), 64: (147, 96, 63), 90: (255, 0, 255)}
PRODUCT_IDS = set(range(40, 65))
FILLER_IDS = {42, 44, 50, 52, 54, 59}
ARCH_IDS = set(range(1, 19))
FIXED_IDS = set(range(20, 27))
GROUP_ID = {}
# slot -> (ids, product id from the card + option, 10.1 row)
SLOTS = {"curtains": ([40], 1), "framed-art": ([41, 42], 2), "framed-art-2": ([43, 44], 3), "wall-sconce": ([45], 4), "rug": ([46], 5),
         "basket": ([47], 6), "waste-basket": ([48], 7), "planter": ([49, 50], 8), "magazine-holder": ([51, 52], 9), "bookends": ([53, 54], 10),
         "shelf-vase": ([55], 11), "shelf-object": ([56], 12), "desk-tray": ([57], 13), "desk-organizer": ([58, 59], 14),
         "desk-vase": ([60], 15), "desk-candle": ([61], 17), "desk-dish": ([62], 18), "pendant": ([63], 19), "chair-throw": ([64], 20)}
PRODUCTS = list(SLOTS) + ["framed-art-canvas", "framed-art-2-canvas", "planter-filler", "magazine-holder-filler", "bookends-filler",
                          "desk-organizer-filler"]
FRAMES = {"W0": dict(placeholders=PRODUCTS, lamps=["work/pendant", "work/wall-sconce"], fixed=True),
          "W0-plate": dict(placeholders=[], lamps=[], fixed=True),
          "W0-shell": dict(placeholders=[], lamps=[], fixed=False)}
CAPTURE = {}


def mat(name, key, rough=0.9):
    return fr.mat_cache("wm_work_" + name, HEX[key], rough)


def reg_arch(name, objs, gid, kind="architecture"):
    objs = [o for o in objs if o is not None]
    r2.reg(name, objs, "work", kind)
    GROUP_ID[name] = gid
    return objs


def reg_prod(R, slot, objs, gid, src):
    r3.reg(R, f"work/{slot}", objs, "work", src=src)
    GROUP_ID[f"work/{slot}"] = gid
    return objs


def bx(n, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    return r3.bx("wk_wm_" + n, x0, x1, y0, y1, z0, z1, m, bevel)


def cyl(n, c, r, z0, z1, m, verts=48):
    return r3.cyl("wk_wm_" + n, c, r, z0, z1, m, verts)


def cone(n, c, r0, r1, z0, z1, m, verts=48):
    return r3.cone("wk_wm_" + n, c, r0, r1, z0, z1, m, verts)


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
    """Closed prism from a convex-or-simple 2D loop. axis 'z': loop in (x, y); 'y': loop in (x, z); 'x': loop in (y, z)."""
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


def arch_half(z):
    """the niche's half-width at height z (the jambs below the spring, the arch above)"""
    c, r = NICHE["c"][1], NICHE["r"]
    if z <= c:
        return r
    return math.sqrt(max(r * r - (z - c) ** 2, 0.0))


# ---------------------------------------------------------------------------------------------------------------
# chapter 1: the architecture
# ---------------------------------------------------------------------------------------------------------------
def spandrel(name, y0, y1, m, seg=48):
    """the built-out wall above the arch: per arch segment a convex column from the arch to the ceiling (front face at y1),
    and the arch soffit (the curved reveal, 0.15 deep) as a separate object"""
    cx, cz = NICHE["c"]
    r, H = NICHE["r"], ROOM["h"]
    pts = arc((cx, cz), r, 180, 0, seg)                       # left spring -> crown -> right spring
    n1 = seg + 1
    verts = [(x, y1, z) for x, z in pts] + [(x, y1, H) for x, z in pts]          # the front face at y1, shared vertices
    faces = [[k, k + 1, n1 + k + 1, n1 + k] for k in range(seg)]
    front = mesh_obj(name + "_front", verts, faces, m)
    sv, sf = [], []
    for k in range(seg + 1):
        x, z = pts[k]
        sv += [(x, y0, z), (x, y1, z)]
    for k in range(seg):
        a = 2 * k
        sf.append([a, a + 2, a + 3, a + 1])
    soffit = mesh_obj(name + "_soffit", sv, sf, m)
    return front, soffit


def wm_work(R):
    notes = []
    n = kill_names(prefixes=("work_cornice", "work_plank", "work_skirt", "W-work_", "w_curt_", "w_rod", "bdesk_", "bshelf", "wchair_"))
    for key in ("built-in oak desk + shelf", "desk chair"):
        if key in fr.REG:
            fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if r3.alive(o)]
    for key in [k for k in list(R) if k.startswith("work/")]:
        r3.kill_group(R, key)
    for key in ("work/pendant", "work/wall-sconce", "work/desk-lamp"):
        r3.lamp_off(key)
    r2.LAMPS.pop("work/desk-lamp", None)
    notes.append(f"removed {n} objects of the 1.1 work room (cornices, planks, skirting, the 1.1 window frame, sashes, reveals and sill "
                 "board, curtains and rod, the built-in oak desk + shelf, the chair) and every work product proxy; work lamps off, the "
                 "desk lamp's lamp entry dropped (Lenni is conditional, 10.2: not built)")
    x0, x1 = ROOM["x"]
    y0, y1 = ROOM["y"]
    H = ROOM["h"]
    pl, gp = mat("plaster", "plaster", 0.95), mat("gap", "gap", 0.9)
    wal, st, bz = mat("walnut", "walnut", 0.7), mat("stone", "stone", 0.75), mat("bronze", "bronze", 0.55)
    xw = x0 + SKIN                                            # window-wall skin: room face at X -2.299
    xs = x1 - SKIN                                            # right-wall skin: room face at X 0.649
    yback = y1 - SKIN
    lc, rc = CORNERS["left"]["c"], CORNERS["right"]["c"]
    rr = CORNERS["r"]
    nx0, nx1 = NICHE["x"]
    ny = NICHE["back"]
    sh = SK["h"]
    wy0, wy1 = WIN["y"]
    slab_z0 = WIN["sill"] - WIN["slab_t"]
    # ---- [WK-4] the build-out: two full-height blocks beside the niche, the spandrel over the arch; the niche back skin ----
    bo = [r3.bx("wk_wm_bo_l", x0, nx0, ny, YB, 0.0, H, pl), r3.bx("wk_wm_bo_r", nx1, x1, ny, YB, 0.0, H, pl)]
    reg_arch("wk_wm built-out desk wall", bo, 1)
    sp_front, sp_soffit = spandrel("wk_wm_spandrel", ny, YB, pl)
    reg_arch("wk_wm arch spandrel", [sp_front], 1)
    jambs = [r3.bx("wk_wm_jamb_l", nx0, nx0 + SKIN, ny, YB, 0.0, NICHE["c"][1], pl),         # 1 mm skins on the niche side
             r3.bx("wk_wm_jamb_r", nx1 - SKIN, nx1, ny, YB, 0.0, NICHE["c"][1], pl)]
    reg_arch("wk_wm niche jambs and soffit", jambs + [sp_soffit], 18)
    reg_arch("wk_wm niche back wall", [r3.bx("wk_wm_niche_back", nx0, nx1, ny, ny + SKIN, sh, NICHE["c"][1] + NICHE["r"] + 0.01, pl)], 17)
    # ---- plaster skins on the other walls ----
    reg_arch("wk_wm plaster window wall", [r3.bx("wk_wm_pl_n_a", xw, xw + 0.001, lc[1], wy0, sh, H, pl),
                                           r3.bx("wk_wm_pl_n_b", xw, xw + 0.001, wy0, wy1, sh, slab_z0, pl),
                                           r3.bx("wk_wm_pl_n_c", xw, xw + 0.001, wy0, wy1, WIN["head"], H, pl),
                                           r3.bx("wk_wm_pl_n_d", xw, xw + 0.001, wy1, y1, sh, H, pl)], 2)
    reg_arch("wk_wm plaster back wall", [r3.bx("wk_wm_pl_w", x0, x1, yback - 0.001, yback, sh, H, pl)], 3)
    dy0, dy1 = DOOR["y"]
    reg_arch("wk_wm plaster right wall", [r3.bx("wk_wm_pl_s_a", xs - 0.001, xs, rc[1], dy0, sh, H, pl),
                                          r3.bx("wk_wm_pl_s_b", xs - 0.001, xs, dy0, dy1, DOOR["head"], H, pl),
                                          r3.bx("wk_wm_pl_s_c", xs - 0.001, xs, dy1, y1, sh, H, pl)], 4)
    # ---- [WK-3] the rounded corners R 0.20 (curved skins: room face r 0.198) and their skirting ----
    rf = rr - 2 * SKIN
    corner_objs, corner_sk = [], []
    p = SK["proud"]
    for nm in ("left", "right"):
        c = CORNERS[nm]["c"]
        a0, a1 = CORNERS[nm]["a"]
        shell = arc(c, rf, a0, a1, 24) + arc(c, rr + 0.03, a1, a0, 24)
        corner_objs.append(prism(f"wk_wm_corner_{nm}", shell, "z", sh, H, pl))
        corner_sk.append(prism(f"wk_wm_sk_corner_{nm}", arc(c, rr - 2 * SKIN - p, a0, a1, 24) + arc(c, rr + 0.03, a1, a0, 24), "z", 0.0, sh, pl))
    reg_arch("wk_wm plaster corners R 0.20", corner_objs, 5)
    # ---- skirting 15, 1.5 proud, wall colour: built-out face, niche back between the desk panels, the walls, the corners ----
    skirt = [r3.bx("wk_wm_sk_e_a", lc[0], nx0, YB, YB + p, 0.0, sh, pl), r3.bx("wk_wm_sk_e_b", nx1, rc[0], YB, YB + p, 0.0, sh, pl),
             r3.bx("wk_wm_sk_niche", nx0 + DESK["side_t"], nx1 - DESK["side_t"], ny, ny + p, 0.0, sh, pl),
             r3.bx("wk_wm_sk_n", x0, xw + p, lc[1], y1, 0.0, sh, pl), r3.bx("wk_wm_sk_w", x0, x1, yback - p, y1, 0.0, sh, pl),
             r3.bx("wk_wm_sk_s_a", xs - p, x1, rc[1], dy0, 0.0, sh, pl), r3.bx("wk_wm_sk_s_b", xs - p, x1, dy1, y1, 0.0, sh, pl)] + corner_sk
    reg_arch("wk_wm skirting 15 (wall colour)", skirt, 9)
    # ---- ceiling 3.00 (kept): 1 cm shadow gap round the room (at the built-out face) and the curtain slot over the window ----
    cz = H - 0.0005
    reg_arch("wk_wm ceiling shadow gap", [r3.bx("wk_wm_cg_e", x0, x1, YB, YB + 0.01, cz - 0.0005, cz, gp),
                                          r3.bx("wk_wm_cg_n", x0, x0 + 0.01, YB, y1, cz - 0.0005, cz, gp),
                                          r3.bx("wk_wm_cg_w", x0, x1, y1 - 0.01, y1, cz - 0.0005, cz, gp),
                                          r3.bx("wk_wm_cg_s", x1 - 0.01, x1, YB, y1, cz - 0.0005, cz, gp)], 7)
    reg_arch("wk_wm curtain slot", [r3.bx("wk_wm_slot", x0 + 0.03, x0 + 0.14, CURTAIN["rail"][0], CURTAIN["rail"][1], cz - 0.0006, cz, gp)], 8)
    # ---- [WK-2] floor: smoked oak 22 cm planks along Y, staggered, 1.5 mm gaps (the dark base shows in the gaps) ----
    rng = np.random.default_rng(23)
    oaks = [mat("oak", "oak", 0.8), mat("oak_l", "oak_l", 0.8), mat("oak_d", "oak_d", 0.8)]
    planks = []
    Wp, g = 0.22, 0.0015
    xk, k = x0, 0
    while xk < x1 - 0.005:
        xa, xb = xk + g / 2, min(xk + Wp, x1) - g / 2
        yk = y0 - rng.uniform(0.2, 1.8)
        j = 0
        while yk < y1:
            L = rng.uniform(1.3, 2.5)
            ya, yb_ = max(yk, y0) + g / 2, min(yk + L, y1) - g / 2
            if yb_ - ya > 0.05:
                planks.append(r3.bx(f"wk_wm_pk{k}_{j}", xa, xb, ya, yb_, -0.012, 0.0, oaks[int(rng.integers(0, 3))]))
            yk += L
            j += 1
        xk += Wp
        k += 1
    reg_arch("wk_wm floor smoked oak 22", planks, 10)
    notes.append(f"floor: {len(planks)} planks of 22 cm along Y from X {x0}, staggered ends, 1.5 mm gaps, three tones of #8B6F55")
    # ---- [WK-5] W-work: plaster reveals, bronze frame at the outer face (45 mm, two 0.60 panes, no transom), limestone slab ----
    xo, fd, s = WIN["x_out"], WIN["frame_d"], WIN["sight"]
    xf = xo + fd
    rev = [r3.bx("wk_wm_rev_a", xf, xw, wy0, wy0 + 0.001, WIN["sill"], WIN["head"], pl),
           r3.bx("wk_wm_rev_b", xf, xw, wy1 - 0.001, wy1, WIN["sill"], WIN["head"], pl),
           r3.bx("wk_wm_rev_h", xf, xw, wy0, wy1, WIN["head"] - 0.001, WIN["head"], pl)]
    reg_arch("wk_wm window reveals (plaster)", rev, 12)
    my = (wy0 + wy1) / 2
    frm = [r3.bx("wk_wm_wf_a", xo, xf, wy0, wy0 + s, WIN["sill"], WIN["head"], bz), r3.bx("wk_wm_wf_b", xo, xf, wy1 - s, wy1, WIN["sill"], WIN["head"], bz),
           r3.bx("wk_wm_wf_t", xo, xf, wy0, wy1, WIN["head"] - s, WIN["head"], bz), r3.bx("wk_wm_wf_bt", xo, xf, wy0, wy1, WIN["sill"], WIN["sill"] + s, bz),
           r3.bx("wk_wm_wf_m", xo, xf, my - s / 2, my + s / 2, WIN["sill"], WIN["head"], bz)]
    reg_arch("wk_wm window frame (bronze)", frm, 13)
    slab = [r3.bx("wk_wm_sill_slab", xf, xw + WIN["slab_proud"] - SKIN, wy0, wy1, slab_z0, WIN["sill"], st, 0.003)]
    reg_arch("wk_wm sill slab (limestone)", slab, 14)
    gs = bpy.data.objects.get("ground_slab")
    if gs is not None:
        reg_arch("wk_wm outside ground", [gs], 15)
    notes.append(f"W-work: frame X {xo}..{xf} (outer face), sight lines {s * 1000:.0f} mm, mullion at Y {my:.3f}, no transom; limestone slab "
                 f"Z {slab_z0:.2f}-{WIN['sill']:.2f}, 2 cm proud; no glass in the clay (the area light outside)")
    # ---- [WK-7] the door (outside W0): leaf in the wall colour, walnut linings, no architrave ----
    lin = []
    lf = bpy.data.objects.get("leaf_hall_work_folded")
    if lf is not None:
        lf.data.materials.clear()
        lf.data.materials.append(pl)
        lin.append(lf)
    dx0, dx1 = DOOR["x"]
    lin += [r3.bx("wk_wm_dl_a", dx0, dx1, dy0, dy0 + 0.01, 0.0, DOOR["head"], wal), r3.bx("wk_wm_dl_b", dx0, dx1, dy1 - 0.01, dy1, 0.0, DOOR["head"], wal),
            r3.bx("wk_wm_dl_h", dx0, dx1, dy0, dy1, DOOR["head"] - 0.01, DOOR["head"], wal)]
    reg_arch("wk_wm door (leaf + walnut linings)", lin, 16)
    notes.append(f"[WK-4] build-out to Y {YB} over the full width; niche X {nx0}..{nx1} at Y {ny} (0.15 deep), arch R {NICHE['r']} "
                 f"springing at Z {NICHE['c'][1]} (crown {NICHE['c'][1] + NICHE['r']:.2f}); plaster inside, no frame, no light; "
                 "[WK-3] corners R 0.20 tangent at the built-out face; [WK-7] walnut linings, leaf in the wall colour")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# 1.3: the fixed walnut desk, shelf and chair (plan B: not sold, not counted)
# ---------------------------------------------------------------------------------------------------------------
def wm_fixed():
    wal, rc, lea = mat("walnut", "walnut", 0.7), mat("recess", "recess", 0.9), mat("leather", "leather", 0.6)
    dx0, dx1 = DESK["x"]
    dy0, dy1 = DESK["y"]
    t = DESK["side_t"]
    top = [r3.bx("wk_wm_desk_top", dx0, dx1, dy0, dy1, DESK["top"][0], DESK["top"][1], wal, 0.002)]
    sides = [r3.bx("wk_wm_desk_side_l", dx0, dx0 + t, dy0, dy1, 0.0, DESK["top"][0], wal, 0.002),
             r3.bx("wk_wm_desk_side_r", dx1 - t, dx1, dy0, dy1, 0.0, DESK["top"][0], wal, 0.002)]
    ddx0, ddx1 = DESK["drawer"]["x"]
    dz0, dz1 = DESK["drawer"]["z"]
    drawer = [r3.bx("wk_wm_desk_drawer", ddx0, ddx1, dy1 - 0.45, dy1 - 0.002, dz0, dz1 - 0.004, wal, 0.002)]
    recess = [r3.bx("wk_wm_desk_grip", -0.90, -0.75, dy1 - 0.0025, dy1 - 0.0015, dz0, dz0 + 0.015, rc),
              r3.bx("wk_wm_desk_groove", ddx0, ddx1, dy1 - 0.0025, dy1 - 0.0015, dz1 - 0.004, dz1, rc)]
    reg_arch("wk_wm desk top (fixed)", top, 20, kind="furniture")
    reg_arch("wk_wm desk side panels (fixed)", sides, 21, kind="furniture")
    reg_arch("wk_wm desk drawer (fixed)", drawer, 22, kind="furniture")
    reg_arch("wk_wm desk drawer recess (fixed)", recess, 23, kind="furniture")
    # the shelf: 4 cm, 25 deep, Z 1.62-1.66; its ends follow the arch 6 mm inside it
    za, zb = SHELF["z"]
    cx = NICHE["c"][0]
    seg = 6
    left = [(cx - (arch_half(za + (zb - za) * k / seg) - SHELF["inset"]), za + (zb - za) * k / seg) for k in range(seg + 1)]
    right = [(cx + (arch_half(zb - (zb - za) * k / seg) - SHELF["inset"]), zb - (zb - za) * k / seg) for k in range(seg + 1)]
    shelf = [prism("wk_wm_shelf", left + right, "y", SHELF["y"][0], SHELF["y"][1], wal)]
    reg_arch("wk_wm shelf (fixed)", shelf, 24, kind="furniture")
    # the chair: four round legs, a seat frame with the cognac seat, a continuous solid curved back (plan arc), back to the camera
    ccx, ccy = CHAIR["c"]
    lr = CHAIR["leg_r"]
    bc = (ccx, ccy - 0.02)
    br, bt = CHAIR["back_r"], CHAIR["back_t"]
    rear = [(bc[0] + (br - bt / 2) * math.cos(math.radians(a)), bc[1] + (br - bt / 2) * math.sin(math.radians(a))) for a in (35, 145)]
    legs = [cyl("chair_leg_fl", (ccx - 0.19, ccy - 0.19), lr, 0.0, CHAIR["seat"][0], wal, 24),
            cyl("chair_leg_fr", (ccx + 0.19, ccy - 0.19), lr, 0.0, CHAIR["seat"][0], wal, 24)]
    legs += [cyl(f"chair_leg_r{i}", c, lr, 0.0, CHAIR["back"][0] + 0.02, wal, 24) for i, c in enumerate(rear)]
    seat_frame = [prism("wk_wm_chair_seatframe", rrect_xy(ccx - 0.23, ccx + 0.23, ccy - 0.23, ccy + 0.19, 0.06), "z", CHAIR["seat"][0] - 0.03,
                        CHAIR["seat"][0], wal)]
    seat = [prism("wk_wm_chair_seat", rrect_xy(ccx - 0.215, ccx + 0.215, ccy - 0.215, ccy + 0.175, 0.05), "z", CHAIR["seat"][0], CHAIR["seat"][1], lea)]
    band = arc(bc, br, 15, 165, 30) + arc(bc, br - bt, 165, 15, 30)
    back = [prism("wk_wm_chair_back", band, "z", CHAIR["back"][0], CHAIR["back"][1], wal)]
    reg_arch("wk_wm chair (fixed walnut)", legs + seat_frame + back, 25, kind="furniture")
    reg_arch("wk_wm chair seat (cognac leather)", seat, 26, kind="furniture")
    return top + sides + drawer + recess + shelf + legs + seat_frame + back + seat


# ---------------------------------------------------------------------------------------------------------------
# 10.1 defaults as boxes at their places (3.2 places, 10.1 SKUs)
# ---------------------------------------------------------------------------------------------------------------
def wm_products(R):
    notes = []
    keys = ("curtain", "frame", "mat", "canvas", "trav", "rug", "rope", "kraft", "cement", "crown", "leatherst", "gun", "mags", "beech",
            "steel", "book_bone", "book_oat", "book_taupe", "book_esp", "sand", "burnt", "pen", "pencil", "vase", "hiba", "dish",
            "shade", "throw")
    C = {k: mat(k, k, 0.9) for k in keys}
    top = DESK["top"][1]
    stop = SHELF["z"][1]
    ny = NICHE["back"]
    # curtains: S-fold stacks out of the ceiling slot, hem 12 cm above the floor (WM-C3); the stack at the desk wall is in frame
    folds = []
    for si, (ya, yb) in enumerate(CURTAIN["stacks"]):
        ycs = np.linspace(ya + CURTAIN["r"], yb - CURTAIN["r"], CURTAIN["n"])
        for i, yc in enumerate(ycs):
            folds.append(cyl(f"curt{si}_{i}", (CURTAIN["x"][i % 2], float(yc)), CURTAIN["r"], CURTAIN["z"][0], CURTAIN["z"][1], C["curtain"], 24))
    reg_prod(R, "curtains", folds, 40, "10.1 row 1: linen-blend S-fold 132 x 270, stacks Y 7.03-7.25 and 8.35-8.57, hem Z 0.12, head 2.82")
    # framed-art (the sample slot): walnut float frame 60 x 50 on the niche back wall, bone mat, a 40 x 30 landscape canvas (blank)
    fx0, fx1, fz0, fz1 = -1.125, -0.525, 0.98, 1.48
    fd = 0.03
    fw = 0.022
    art = [bx("art_frame_t", fx0, fx1, ny, ny + fd, fz1 - fw, fz1, C["frame"]), bx("art_frame_b", fx0, fx1, ny, ny + fd, fz0, fz0 + fw, C["frame"]),
           bx("art_frame_l", fx0, fx0 + fw, ny, ny + fd, fz0, fz1, C["frame"]), bx("art_frame_r", fx1 - fw, fx1, ny, ny + fd, fz0, fz1, C["frame"]),
           bx("art_mat", fx0 + fw, fx1 - fw, ny, ny + fd - 0.012, fz0 + fw, fz1 - fw, C["mat"])]
    reg_prod(R, "framed-art", art, 41, "10.1 row 2 / ch. 4: walnut float frame 60 x 50 (X -1.125..-0.525, Z 0.98-1.48) with a bone mat")
    canvas = [bx("art_canvas", -1.025, -0.625, ny, ny + fd - 0.010, 1.08, 1.38, C["canvas"])]
    reg_prod(R, "framed-art-canvas", canvas, 42, "the 40 x 30 print area (blank #D8C8AE; the print goes in by code)")
    # framed-art-2: on the right wall (X 0.65), walnut 44 x 54 portrait, a 30 x 40 print
    xr = ROOM["x"][1] - SKIN
    ay0, ay1, az0, az1 = 7.03, 7.47, 1.15, 1.69
    art2 = [bx("art2_frame_t", xr - fd, xr, ay0, ay1, az1 - fw, az1, C["frame"]), bx("art2_frame_b", xr - fd, xr, ay0, ay1, az0, az0 + fw, C["frame"]),
            bx("art2_frame_l", xr - fd, xr, ay0, ay0 + fw, az0, az1, C["frame"]), bx("art2_frame_r", xr - fd, xr, ay1 - fw, ay1, az0, az1, C["frame"]),
            bx("art2_mat", xr - fd + 0.012, xr, ay0 + fw, ay1 - fw, az0 + fw, az1 - fw, C["mat"])]
    reg_prod(R, "framed-art-2", art2, 43, "10.1 row 3: walnut frame 44 x 54 portrait on the right wall, Y 7.03-7.47, Z 1.15-1.69")
    canvas2 = [bx("art2_canvas", xr - fd + 0.010, xr, 7.10, 7.40, 1.22, 1.62, C["canvas"])]
    reg_prod(R, "framed-art-2-canvas", canvas2, 44, "the 30 x 40 print area (blank; 386242-03 goes in by code)")
    # wall-sconce: the travertine cube 12, up / down, on the built-out face (10.3); lit
    sx, sy, sz = SCONCE["c"]
    s = SCONCE["s"]
    cube = [bx("sconce_cube", sx - s / 2, sx + s / 2, sy, sy + s, sz - s / 2, sz + s / 2, C["trav"], 0.004)]
    glow_t = bx("sconce_glow_t", sx - s / 2 + 0.02, sx + s / 2 - 0.02, sy + 0.02, sy + s - 0.02, sz + s / 2, sz + s / 2 + 0.002, C["shade"])
    glow_b = bx("sconce_glow_b", sx - s / 2 + 0.02, sx + s / 2 - 0.02, sy + 0.02, sy + s - 0.02, sz - s / 2 - 0.002, sz - s / 2, C["shade"])
    reg_prod(R, "wall-sconce", cube + [glow_t, glow_b], 45, "10.1 row 4 / 10.3: travertine cube 12 x 12 x 12 (Type A indoor, up / down) "
             "on the built-out face, centre (-1.92, 6.56, 1.65)")
    lights = []
    for nm, zz, aim in (("up", sz + s / 2 + 0.01, (0, 0, 1)), ("down", sz - s / 2 - 0.01, (0, 0, -1))):
        sp = r2.mk_light(f"wk_wm_sc_{nm}", "SPOT", (sx, sy + s / 2, zz), LIGHT["sconce_spot_w"], aim=aim)
        sp.data.spot_size = math.radians(70)
        sp.data.spot_blend = 0.6
        sp.data.shadow_soft_size = 0.03
        lights.append(sp)
    r2.lamp("work/wall-sconce", "work", "wall", [(glow_t, LIGHT["sconce_glow"]), (glow_b, LIGHT["sconce_glow"])], lights, "travertine cube 12 (10.3)")
    # rug: braided wool 160 x 230 under the chair (X centred on the chair, from the desk front to past the bottom edge)
    rug = [bx("rug", -1.625, -0.025, 6.95, 9.25, 0.0, 0.012, C["rug"])]
    reg_prod(R, "rug", rug, 46, "10.1 row 5: braided wool 160 x 230 (CJJT211801816PK), X -1.625..-0.025, Y 6.95-9.25 (temporary repeat)")
    # basket and bin under the desk
    reg_prod(R, "basket", [cyl("basket", (-1.25, 6.62), 0.15, 0.0, 0.30, C["rope"], 40)], 47, "10.1 row 6: two-tone rope 30 x 30 at (-1.25, 6.62)")
    bin_ = [cyl("bin", (-0.35, 6.70), 0.125, 0.0, 0.26, C["kraft"], 40), cyl("bin_cuff", (-0.35, 6.70), 0.130, 0.26, 0.30, C["kraft"], 40)]
    reg_prod(R, "waste-basket", bin_, 48, "10.1 row 7: kraft Brown XL 25 x 25 x 40, the rim rolled to about 30, at (-0.35, 6.70)")
    # planter in the rounded corner; D42 x H35.5 (card): centre Y 6.74 keeps the 3 cm from the built-out face (3.2 placed D38 at 6.72)
    pc = (-1.95, 6.74)
    pot = [cyl("pot_low", pc, 0.17, 0.0, 0.05, C["cement"], 48), cyl("pot_belly", pc, 0.21, 0.05, 0.28, C["cement"], 48),
           cyl("pot_top", pc, 0.18, 0.28, 0.355, C["cement"], 48)]
    reg_prod(R, "planter", pot, 49, "10.1 row 8: cement ribbed belly Beige Large D42 x H35.5 at (-1.95, 6.74) (temporary repeat)")
    plant = [r3.ell("wk_wm_crown", (pc[0] + 0.02, pc[1] + 0.06), 0.24, 0.62, 1.30, C["crown"])]
    plant += [r2.obox(f"wk_wm_cane{i}", (pc[0] + dx, pc[1] + dy, 0.33), (pc[0] + 1.6 * dx, pc[1] + 1.6 * dy + 0.04, 1.05), (1, 0, 0), 0.012, 0.012, C["crown"])
              for i, (dx, dy) in enumerate(((-0.05, 0.02), (0.04, 0.03), (0.0, 0.07), (0.06, -0.01), (-0.03, 0.08)))]
    reg_prod(R, "planter-filler", plant, 50, "filler: Rhapis excelsa to 1.30 (matt fan leaves, muted green)")
    # magazine holder between the right jamb and the corner: 35 wide (front to the camera) x 19 x 27.5
    mh = [bx("mag_frame", 0.05, 0.40, 6.52, 6.71, 0.0, 0.275, C["gun"]), bx("mag_strap_f", 0.06, 0.39, 6.708, 6.715, 0.06, 0.22, C["leatherst"])]
    reg_prod(R, "magazine-holder", mh, 51, "10.1 row 9: gunmetal + Orange (cognac) straps, 35 x 19 x 27.5, X 0.05-0.40, Y 6.52-6.71 (temporary repeat)")
    mags = [bx(f"mag{i}", 0.08 + 0.10 * i, 0.16 + 0.10 * i, 6.55, 6.68, 0.02, 0.31 - 0.02 * i, C["mags"]) for i in range(3)]
    reg_prod(R, "magazine-holder-filler", mags, 52, "filler: three magazines, no text")
    # the shelf: bookends with books (left), empty centre, the vase and the burnt bowl (right)
    be = []
    for i, x in enumerate((-1.48, -1.175)):
        be += [bx(f"bkend_steel{i}", x, x + 0.025, 6.40, 6.505, stop, stop + 0.004, C["steel"]),
               prism(f"wk_wm_bkend{i}", [(6.40, stop)] + [(6.46 + 0.06 * math.cos(math.radians(a)), stop + 0.11 + 0.06 * math.sin(math.radians(a))) for a in range(0, 181, 15)] + [(6.52, stop)],
                     "x", x, x + 0.025, C["beech"])]
    reg_prod(R, "bookends", be, 53, "10.1 row 10: arch bookends Black walnut (SKU 9), 12 x 10.5 x 17, the pair at X -1.48 and -1.175")
    books, x = [], -1.452
    for i, (w, h, key) in enumerate(((0.035, 0.235, "book_bone"), (0.028, 0.215, "book_oat"), (0.042, 0.245, "book_taupe"), (0.030, 0.225, "book_esp"),
                                     (0.038, 0.23, "book_bone"), (0.032, 0.21, "book_oat"), (0.040, 0.24, "book_taupe"))):
        books.append(bx(f"book{i}", x, x + w - 0.002, 6.39, 6.56, stop, stop + h, C[key]))
        x += w
    reg_prod(R, "bookends-filler", books, 54, f"filler: seven books (bone, oat, taupe, one espresso), X -1.452..{x:.3f}, no readable text")
    reg_prod(R, "shelf-vase", [cyl("svase_body", (-0.48, 6.47), 0.095, stop, stop + 0.24, C["sand"], 48),
                               cone("svase_neck", (-0.48, 6.47), 0.095, 0.05, stop + 0.24, stop + 0.30, C["sand"], 48)], 55,
             "10.1 row 11: coarse sand white Tall 19 x 30 (mouth 10) at (-0.48, 6.47)")
    reg_prod(R, "shelf-object", [cyl("bowl_foot", (-0.19, 6.47), 0.045, stop, stop + 0.03, C["burnt"], 40),
                                 cone("bowl_body", (-0.19, 6.47), 0.06, 0.115, stop + 0.03, stop + 0.09, C["burnt"], 48)], 56,
             "10.1 row 12: burnt paulownia footed bowl 23 x 9, Fire Color, at (-0.19, 6.47)")
    # the desk, left: tray (with the pen cup) and the faceted vase in the back-left corner
    tray = [prism("wk_wm_tray", rrect_xy(-1.375, -1.135, 6.585, 6.755, 0.05), "z", top, top + 0.018, C["trav"])]
    reg_prod(R, "desk-tray", tray, 57, "10.1 row 13: travertine organic tray 24 x 17 x 1.8 at X -1.375..-1.135, Y 6.585-6.755")
    reg_prod(R, "desk-organizer", [cyl("pencup", (-1.26, 6.66), 0.04, top + 0.018, top + 0.128, C["pen"], 32)], 58,
             "10.1 row 14: cave stone pen cup Cream Yellow 8 x 11 on the tray at (-1.26, 6.66)")
    pencils = [r2.obox(f"wk_wm_pencil{i}", (-1.26 + dx, 6.66 + dy, top + 0.10), (-1.26 + 2.2 * dx, 6.66 + 2.2 * dy, top + 0.235), (1, 0, 0), 0.008, 0.008, C["pencil"])
               for i, (dx, dy) in enumerate(((-0.012, 0.0), (0.01, 0.008), (0.004, -0.012)))]
    reg_prod(R, "desk-organizer-filler", pencils, 59, "filler: three pencils in the cup")
    dv = [prism("wk_wm_dvase", [(-1.48 + 0.0925 * math.cos(math.radians(a)), 6.47 + 0.085 * math.sin(math.radians(a))) for a in range(0, 360, 45)], "z",
                top, top + 0.24, C["vase"]),
          cone("dvase_shoulder", (-1.48, 6.47), 0.085, 0.057, top + 0.24, top + 0.30, C["vase"], 8)]
    reg_prod(R, "desk-vase", dv, 60, "10.1 row 15: faceted cream Large 18.5 x 17 x 30 at (-1.48, 6.47), 1.25 cm from the left panel")
    # the desk, right (the lamp is not built: Lenni conditional, 10.2): the Hiba candle bowl and the caramel dish
    reg_prod(R, "desk-candle", [cyl("hiba", (-0.16, 6.55), 0.09, top, top + 0.07, C["hiba"], 40)], 61,
             "10.1 row 17: Hiba ceramic candle bowl 18 x 7 (card), at (-0.16, 6.55): 3.2's (-0.12) would touch the jamb with 18 cm")
    reg_prod(R, "desk-dish", [cyl("dish", (-0.45, 6.78), 0.0425, top, top + 0.025, C["dish"], 32)], 62,
             "10.1 row 18: retro raw rim dish Style A 8.5 x 2.5 at (-0.45, 6.78)")
    # pendant: silk ribbed pumpkin 30 (warm), bottom 1.58; lit
    pz0, pz1 = PENDANT["z"]
    pc_ = PENDANT["c"]
    shade = r3.ell("wk_wm_pendant", pc_, PENDANT["d"] / 2, pz0, pz1, C["shade"])
    cord = cyl("pend_cord", pc_, 0.004, pz1, ROOM["h"], C["steel"], 12)
    reg_prod(R, "pendant", [shade, cord], 63, f"10.1 row 19: silk ribbed pumpkin 30 (warm), Z {pz0}-{pz1} (height not published: 19, the "
             "kitchen lantern's ratio), cord to the ceiling")
    pl_ = [r2.mk_light("wk_wm_pend_area", "AREA", (pc_[0], pc_[1], pz0 - 0.005), LIGHT["pend_area_w"], size=0.18)]
    r2.lamp("work/pendant", "work", "ceiling", [(shade, LIGHT["pend_glow"])], pl_, "silk ribbed pumpkin 30 (10.1)")
    # chair-throw: folded lengthwise to 45, hung over the chair back toward the camera, Z 0.45-0.88
    ccx, ccy = CHAIR["c"]
    yb_out = ccy - 0.02 + CHAIR["back_r"]
    th = [bx("throw_top", ccx - 0.225, ccx + 0.225, yb_out - CHAIR["back_t"] - 0.02, yb_out + 0.012, CHAIR["back"][1], CHAIR["back"][1] + 0.03, C["throw"], 0.01),
          bx("throw_front", ccx - 0.225, ccx + 0.225, yb_out + 0.004, yb_out + 0.020, 0.45, CHAIR["back"][1] + 0.03, C["throw"], 0.006),
          bx("throw_back", ccx - 0.225, ccx + 0.225, yb_out - CHAIR["back_t"] - 0.025, yb_out - CHAIR["back_t"] - 0.008, 0.70, CHAIR["back"][1] + 0.03, C["throw"])]
    reg_prod(R, "chair-throw", th, 64, "10.1 row 20: cotton-linen Brown 200 x 230, folded lengthwise to 45, over the chair back toward the camera, "
             "Z 0.45-0.88")
    notes.append("products: 10.1 defaults (19 of 20; the desk lamp Lenni is conditional, 10.2, not built); fillers: Rhapis, three blank "
                 "magazines, seven books, three pencils")
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
    counts = {IDS.get(k, str(k)): int((ids == k).sum()) for k in sorted(set(np.unique(ids).tolist()))}
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


def gap_v(ids, upper, lower):
    """the smallest vertical gap (frame fraction) between the lowest pixel of `upper` and the highest of `lower`, per column"""
    H, W = ids.shape
    mu, ml = np.isin(ids, list(upper)), np.isin(ids, list(lower))
    best = None
    for x in np.nonzero(mu.any(0) & ml.any(0))[0]:
        a, b = np.nonzero(mu[:, x])[0], np.nonzero(ml[:, x])[0]
        g = (b.min() - a.max() - 1) / H * K
        best = g if best is None or g < best else best
    return None if best is None else r4_(best)


def checks_w0(fid, cam, ids, items=None):
    """2.1 (the frame) and 6.1 (what the clay measures), analytic and from the id pass"""
    C = {}
    cx = NICHE["c"][0]
    C["desk_centre_u"] = dict(target="0.50", value=r4_(UVf(cam, cx, 6.95, 0.76)[0]))
    C["corners_u"] = dict(target="sharp corners 0.2065 / 0.7935 (2.1); the R 0.20 arcs are bands",
                          sharp=[r4_(UVf(cam, ROOM["x"][0], YB, 1.0)[0]), r4_(UVf(cam, ROOM["x"][1], YB, 1.0)[0])],
                          left_band=[r4_(UVf(cam, ROOM["x"][0], 6.70, 1.0)[0]), r4_(UVf(cam, CORNERS["left"]["c"][0], YB, 1.0)[0])],
                          right_band=[r4_(UVf(cam, CORNERS["right"]["c"][0], YB, 1.0)[0]), r4_(UVf(cam, ROOM["x"][1], 6.70, 1.0)[0])])
    C["niche_jambs_u"] = dict(target="0.341 / 0.659", value=[r4_(UVf(cam, NICHE["x"][0], YB, 1.0)[0]), r4_(UVf(cam, NICHE["x"][1], YB, 1.0)[0])])
    C["arch_spring_v"] = dict(target="0.318", value=r4_(UVf(cam, NICHE["x"][0], YB, NICHE["c"][1])[1]))
    crown = r4_(UVf(cam, cx, YB, NICHE["c"][1] + NICHE["r"])[1])
    C["arch_crown_v"] = dict(target=">= 0.03 (0.035 in 2.1)", value=crown, ok=crown >= 0.03)
    b = bbox_f(ids, {18})
    if b:
        C["arch_crown_v"]["soffit_top_in_ids"] = b["v"][0]
    C["window_u"] = dict(target="0-0.136 (cut)", jamb=r4_(UVf(cam, ROOM["x"][0], WIN["y"][0], 1.5)[0]))
    for slot, (gl, row) in SLOTS.items():
        bb = bbox_f(ids, set(gl))
        if bb:
            C.setdefault("boxes", {})[slot] = bb
    # W-HC2: the pendant above the art (in frame), and in front of the shelf's empty centre
    C["W-HC2_pendant_over_art"] = dict(rule=">= 0.03 (or a clear 0.03 overlap)", gap_v=gap_v(ids, {63}, {41, 42}))
    if C["W-HC2_pendant_over_art"]["gap_v"] is not None:
        C["W-HC2_pendant_over_art"]["ok"] = C["W-HC2_pendant_over_art"]["gap_v"] >= 0.03
    pb = bbox_f(ids, {63})
    C["pendant_vs_shelf_centre"] = dict(pendant_u=pb["u"] if pb else None, shelf_empty_centre_u="0.467-0.533 (10.2)",
                                        books_right_u=(bbox_f(ids, {53, 54}) or {}).get("u"), vase_left_u=(bbox_f(ids, {55}) or {}).get("u"))
    # 10.3: the wall light vs the curtain stack and the niche jamb
    C["sconce_vs_stack"] = dict(rule=">= 0.058 (10.3)", gap_u=gap_u(ids, {40}, {45}))
    C["sconce_vs_jamb"] = dict(rule=">= 0.047 (10.3)", value=r4_(UVf(cam, NICHE["x"][0], YB, 1.65)[0] - (bbox_f(ids, {45}) or {"u": [0, 0]})["u"][1]))
    C["sconce_over_plant"] = dict(rule=">= 0.27 m in plan (10.3)", value_m=round(SCONCE["c"][2] - SCONCE["s"] / 2 - 1.30, 3))
    C["planter_vs_built_out_face"] = dict(rule="3 cm (3.2)", value_m=round(6.74 - 0.21 - YB, 3))
    C["magazine_holder_vs_right_jamb"] = dict(gap_u=gap_u(ids, {18, 1}, {51, 52}), plan_m=round(0.05 - NICHE["x"][1], 3))
    tl, tr = UVf(cam, ROOM["x"][1] - SKIN, 7.03, 1.69), UVf(cam, ROOM["x"][1] - SKIN, 7.47, 1.69)
    bl, br = UVf(cam, ROOM["x"][1] - SKIN, 7.03, 1.15), UVf(cam, ROOM["x"][1] - SKIN, 7.47, 1.15)
    C["framed_art_2_trapezoid"] = dict(target="u 0.85-0.91, v 0.17-0.44", corners_uv=dict(tl=[r4_(v) for v in tl], tr=[r4_(v) for v in tr],
                                                                                          bl=[r4_(v) for v in bl], br=[r4_(v) for v in br]))
    C["candle_vs_art"] = dict(rule=">= 0.02 or a clear 0.03 overlap (D-HC3)", gap_u=gap_u(ids, {41, 42}, {61}), gap_v=gap_v(ids, {41, 42}, {61}))
    C["desk_vase_vs_left_panel_m"] = round((-1.48 - 0.0925) - (NICHE["x"][0] + DESK["side_t"]), 4)
    C["bowl_vs_arch_m"] = round(arch_half(SHELF["z"][1] + 0.09) - abs(-0.19 + 0.115 - NICHE["c"][0]), 4)
    return C


def count_v7q6(ids, items):
    """house-plan frame_checks.F10 (V7Q6): >= 50 % visible and (>= 0.5 % of the frame, or >= 0.15 % with the larger dimension >= 6 % of
    the frame height); a group of 3 on one surface counts once (through members not counted alone); fillers and the fixed furniture
    are not counted. Visibility from run_frame's ray cast (r2.analyse)."""
    rows = {}
    for slot, (gl, row) in SLOTS.items():
        b = bbox_f(ids, set(gl))
        vis = (items.get(f"work/{slot}") or {}).get("visible_pct")
        if b is None:
            rows[slot] = dict(counted=False, why="not in frame")
            continue
        hpct = round(100 * (b["v"][1] - b["v"][0]), 2)
        wpct = round(100 * (b["u"][1] - b["u"][0]) * 16 / 9, 2)
        big = max(hpct, wpct)
        ok_area = b["frame_pct"] >= 0.5 or (b["frame_pct"] >= 0.15 and big >= 6.0)
        rows[slot] = dict(frame_pct=b["frame_pct"], larger_dim_pct_of_height=big, visible_pct=vis,
                          counted=bool(ok_area and (vis is None or vis >= 50)), why=None if ok_area and (vis is None or vis >= 50) else
                          ("visible < 50 %" if ok_area else "too small"))
    for grp, members in (("shelf trio (bookends, vase, bowl)", ["bookends", "shelf-vase", "shelf-object"]),
                         ("desk-left trio (vase, tray, pen cup)", ["desk-vase", "desk-tray", "desk-organizer"]),
                         ("desk-right pair (candle, dish; the lamp is not built)", ["desk-candle", "desk-dish"])):
        rest = [m for m in members if not rows[m]["counted"]]
        u = sum(rows[m].get("frame_pct", 0) for m in rest)
        rows[grp] = dict(members_not_counted_alone=rest, union_pct=round(u, 3), counted=bool(len(rest) > 0 and u >= 0.5 and len(members) >= 3),
                         note="counts once only through members not counted alone; a group needs 3 (the desk-right pair has 2 without the lamp)")
    n = sum(1 for k, v in rows.items() if v.get("counted"))
    return dict(rule="house-plan frame_checks.F10 (V7Q6), on the clay", counted=n, rows=rows, designer_estimate="about 12-13 (3.5, 10.5)")


def lock_target(cam, depth_img):
    H, W = depth_img.shape
    xw = ROOM["x"][0] + 2 * SKIN
    s = WIN["sight"]
    xf = WIN["x_out"] + WIN["frame_d"]
    nx0, nx1 = NICHE["x"]
    dy1 = DESK["y"][1]
    L = {
        "window jamb at the wall face (Y 7.15)": ((xw, WIN["y"][0], WIN["sill"]), (xw, WIN["y"][0], 2.40)),
        "bronze jamb, inner edge (Y 7.195)": ((xf, WIN["y"][0] + s, WIN["sill"] + s), (xf, WIN["y"][0] + s, 2.40)),
        "sill slab, top front edge (Z 0.75)": ((xw + WIN["slab_proud"], WIN["y"][0], WIN["sill"]), (xw + WIN["slab_proud"], 7.85, WIN["sill"])),
        "skirting top, window wall (Z 0.15)": ((xw + SK["proud"], 6.80, SK["h"]), (xw + SK["proud"], 9.50, SK["h"])),
        "skirting top, built-out face left of the niche": ((-2.05, YB + SK["proud"], SK["h"]), (nx0 - 0.01, YB + SK["proud"], SK["h"])),
        "skirting top, built-out face right of the niche": ((nx1 + 0.01, YB + SK["proud"], SK["h"]), (0.40, YB + SK["proud"], SK["h"])),
        "niche left jamb (X -1.625, Y 6.50)": ((nx0, YB, 0.80), (nx0, YB, NICHE["c"][1])),
        "niche right jamb (X -0.025, Y 6.50)": ((nx1, YB, 0.80), (nx1, YB, NICHE["c"][1])),
        "desk top, front edge (Z 0.76)": ((nx0 + 0.02, dy1, DESK["top"][1]), (nx1 - 0.02, dy1, DESK["top"][1])),
        "desk top, front underside (Z 0.72)": ((nx0 + 0.05, dy1, DESK["top"][0]), (nx1 - 0.05, dy1, DESK["top"][0])),
        "desk side panel left, front edge": ((nx0 + 0.02, dy1, 0.05), (nx0 + 0.02, dy1, 0.70)),
        "desk side panel right, front edge": ((nx1 - 0.02, dy1, 0.05), (nx1 - 0.02, dy1, 0.70)),
        "shelf, top front edge (Z 1.66)": ((nx0 + 0.04, SHELF["y"][1], SHELF["z"][1]), (nx1 - 0.04, SHELF["y"][1], SHELF["z"][1])),
        "shelf, bottom front edge (Z 1.62)": ((nx0 + 0.04, SHELF["y"][1], SHELF["z"][0]), (nx1 - 0.04, SHELF["y"][1], SHELF["z"][0])),
        "floor line, built-out face right of the niche": ((nx1 + 0.01, YB + SK["proud"], 0.0), (0.40, YB + SK["proud"], 0.0)),
        "skirting top, right wall (Z 0.15)": ((ROOM["x"][1] - SK["proud"], 6.80, SK["h"]), (ROOM["x"][1] - SK["proud"], 8.05, SK["h"])),
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
    # the arch as sampled points (the curve, for the plate check)
    cx, cz = NICHE["c"]
    arcpts = []
    for a in np.linspace(180, 0, 37):
        x, z = cx + NICHE["r"] * math.cos(math.radians(a)), cz + NICHE["r"] * math.sin(math.radians(a))
        arcpts.append(px(cam, x, YB, z))
    out["arch at the built-out face (R 0.80, spring 1.50)"] = dict(xyz="arc", samples=[p_ + [True] for p_ in arcpts], visible_frac=1.0)
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


def tone_frames(frames, cam, ref_frame, out_dir, fixed=None):
    import tone_r4 as T
    toner = T.Toner()
    if fixed is not None:
        e, gains = fixed["exposure"], np.array(fixed["wb_gains"])
        for fid in frames:
            img, lin = toner.load(os.path.join(r4.EXR_DIR, f"{fid}.exr"))
            t = T.shoulder(toner.tone(img, lin, e, gains))
            bpy.data.images.remove(img)
            T.save_png(t, os.path.join(out_dir, f"{fid}.png"))
        return dict(fixed, reused_for=list(frames))
    ref_pts = [(-0.825, YB, 2.62), (0.20, YB, 1.95)]            # the spandrel over the crown, and the built-out face right of the niche
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
                note="gains make the desk-wall patches read #ECE5DA's chroma; one exposure and one balance for every frame (one camera point); "
                     "target L* 87.5 as the master clay")
    for fid in frames:
        img, lin = toner.load(os.path.join(r4.EXR_DIR, f"{fid}.exr"))
        t = T.shoulder(toner.tone(img, lin, e, gains))
        bpy.data.images.remove(img)
        T.save_png(t, os.path.join(out_dir, f"{fid}.png"))
    return post


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
    for g in (1, 2, 5, 9, 10, 12, 13, 14, 17, 18, 20, 21, 24, 25):
        m = ids == g
        if m.sum() > 50:
            out[IDS[g]] = [round(float(x), 1) for x in np.median(lab[m], 0)]
    x0, y0, x1, y1 = [int(round(c)) for c in FRAME_BOX]
    out["frame_mean_L_8bit"] = round(float((a[y0:y1, x0:x1] * 255 * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1)
    return out


# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="W0-plate,W0,W0-shell")
    ap.add_argument("--res", type=int, default=CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=1.0)
    ap.add_argument("--work-window", type=float, default=LIGHT["window"])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--keep-post", action="store_true")
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
        r3.FRAMES[fid] = r3.FRAMES["W0"]
        r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT.get("W0", (-0.825, 6.35))
        cams[fid] = dict(cams["W0"], id=fid)
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
    LIGHT["window"] = a.work_window
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name == "winlight_W-work":
            ob.data.energy *= a.work_window
            notes["round3"].append(f"work window area light x{a.work_window} (= {ob.data.energy:.0f} W): ARC2, daylight the key")
    notes["wm_work"] = wm_work(R)
    fixed = wm_fixed()
    notes["wm_work"] += wm_products(R)
    bpy.context.view_layer.update()
    rep = dict(stage="warm-modern work room clay, W0 (render-agent, 2026-11-20; docs/proposals/wm-work-render-2026-11-19.md ch. 1, 2, 3.2 + "
                     "10.1, 10.3, 6.1)", date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"], camera=cams["W0"],
               canvas=dict(px=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], K=K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: tone_frames()",
               light=dict(LIGHT), build_notes=notes, ids=IDS, slots={k: dict(ids=v[0], row_10_1=v[1]) for k, v in SLOTS.items()}, frames={})
    prev = None
    if a.keep_post and os.path.exists(os.path.join(out, "selfcheck.json")):
        prev = json.load(open(os.path.join(out, "selfcheck.json")))
        rep["frames"] = prev.get("frames", {})
        rep["lock_target"] = prev.get("lock_target")
    tmp = tempfile.mkdtemp(prefix="wm-work-")
    r4.OS_STATE["on"] = True
    for fid in frames:
        F = FRAMES[fid]
        r3.set_hidden(fixed, not F["fixed"])
        fplan = dict(placeholders=F["placeholders"], lamps=F["lamps"], also_visible=[], notes=f"warm-modern {fid}")
        Rr = r3.run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, {}, cfg)
        depth, idx, normal = CAPTURE["last"]
        ids, counts, pid = save_passes(fid, out, depth, idx, normal)
        cam = S["cam"]
        r3.set_hidden(fixed, not F["fixed"])
        Rr["id_px"] = counts
        Rr["pidx_to_id"] = pid
        Rr["checks"] = checks_w0(fid, cam, ids, Rr.get("items_visible"))
        if fid == "W0":
            Rr["V7Q6"] = count_v7q6(ids, Rr.get("items_visible") or {})
        if fid == "W0-plate" or (fid == "W0" and "lock_target" not in rep):
            rep["lock_target"] = "lock-target.json"
            json.dump(dict(frame=f"{fid} clay", canvas=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], camera=cams["W0"],
                           method="analytic projection of the 3D lines; 'samples' are [x, y, seen] in canvas px, seen = the depth pass agrees",
                           lines=lock_target(cam, depth)), open(os.path.join(out, "lock-target.json"), "w"), indent=1)
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr["runtime_s"], "s", flush=True)
    cam = S["cam"]
    ref = "W0-plate" if "W0-plate" in frames else frames[0]
    rep["post"] = tone_frames(frames, cam, ref, out, fixed=prev["post"] if prev else None)
    for fid in frames:
        rep["frames"][fid]["readings"] = readings(os.path.join(out, f"{fid}.png"), os.path.join(out, f"{fid}-id.png"))
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
