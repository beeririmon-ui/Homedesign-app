#!/usr/bin/env python3
"""
framing_wm_bath.py: the warm-modern BATH as a clay, frame B2 (the vanity wall), render-agent, 2026-11-17. 0 var2 tokens.
Brief: briefs/wm-bath-stage1-render-2026-11-17.md, step 1. Spec: master-designer docs/proposals/wm-bath-render-2026-11-17.md,
chapters 1 (the architecture), 7.2-7.8 (camera, composition, layers, architecture in frame, the vanity, products, light).
Manager relay 2026-11-17: the floor planter is out of the defaults (no published Medium), the sconce dimensions are still open.

The scene is the round-4 house clay (framing_r4.py, imported, nothing changed there; the r3/r4 bath of house plan 1.1) with the bath
rebuilt to chapter 1 by wm_bath():
  - plaster #ECE5DA as 1 mm skins on every bath wall outside the shower; 8 cm limestone skirting flush with the plaster;
  - limestone #D8C8AE floor 60 x 120 along Y, 2 mm joints (X every 0.60 from 3.25, Y every 1.20 from 9.95: Y 11.15 is the shower
    edge), continuous into the shower; the 1.1 porcelain tiles, skirting and shadow gaps of the bath are removed;
  - the shower clad in limestone floor to ceiling (2.70), 12 mm, joints Y 10.30 / 10.90 (full height, south wall) and Z 1.40 (both
    walls); the niche Y 10.30-10.90, Z 1.05-1.40, 0.12 deep, lined in the same stone; a hidden 2700 K LED at its head (light only);
  - ceiling 2.70 with a 1 cm shadow gap all round; the L track as a 2.5 cm slot in the ceiling (X 5.20 run and Y 11.15 run);
  - rain head D25 on a wall arm and a round mixer rosette, bronze-espresso #3A322C matte; the downlight of 1.1 kept;
  - the mirror (U6) in its 1.1 envelope Y 11.80-12.80, Z 1.15-1.95: corners R 10, a 15 mm bronze profile, glass inset 4 mm;
  - the vanity (7.6): walnut #6B4A33, 3 cm side panels to the floor (outer front corners rounded: R 3 = the panel thickness, see the
    README), one drawer Z 0.50-0.84 with a 2 cm finger groove, the open shelf clear Z 0.15-0.48 (empty), a 4 cm bottom board, a kick
    recess 0.11 high set back 8 cm, limestone top 4 cm with 1 cm overhang, the vessel basin D40 h13 warm white, a bronze wall spout
    and a separate round handle on round rosettes;
  - the products of 7.7 as boxes at their slot envelopes (B2 defaults, without the floor planter); the sconce pair as provisional
    blocks (the dimensions gate is open): 12 wide, 22 high, 10 deep on the slot plates.
Frames (camera CB from docs/house-plan.json, 24 mm, u0 0.52, v0 0.46, the base.png canvas 2720 x 1530 with the 16:9 frame at
[77.49, 43.43, 2642.51, 1486.57], i.e. the round-4 3 % overscan):
  B2          the defaults clay: shell + vanity + the 7.7 products; the sconce pair and the B1 lamp lit; downlight and niche LED lit
  B2-plate    the empty plate (output 1): shell + vanity, every product hidden, every product lamp off; downlight and niche LED lit
  B2-shell    the shell alone (no vanity): the plate / shell ratio is the fixed-furniture shadow (RND2, as the living room)
Per frame: <id>.png (toned clay), <id>-depth.png (16 bit, planar, metres = value / 5000, 65535 = nothing), <id>-id.png (palette;
legend in selfcheck.json), <id>-edges.png (structure edges). selfcheck.json: the 7.3 numbers, F8, lamps, boxes. lock-target.json:
the named lines in canvas pixels for the stills' lock.

  python3 framing_wm_bath.py --frames B2,B2-plate,B2-shell --samples 16
  python3 framing_wm_bath.py --frames B2 --res 960 --samples 4 --out /tmp/x          # smoke test
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

import framing_r4 as r4  # noqa: E402  (the round-4 house; sets FRAMING_R3_OUT to round4, we re-point it below)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

r3, r2, fr, bh, M = r4.r3, r4.r2, r4.fr, r4.bh, r4.M
bs, ba = r3.bs, r3.ba
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/render-bath"
OUT = os.path.join(HERE, "framing", "wm-bath-2026-11-17")
r4.EXR_DIR = os.path.join(SCR, "exr")
CANVAS = (2720, 1530)
K = r4.OS_K                                                     # 4072 / 3840: canvas = frame / K about the centre
FRAME_BOX = (0.5 * CANVAS[0] * (1 - 1 / K), 0.5 * CANVAS[1] * (1 - 1 / K), 0.5 * CANVAS[0] * (1 + 1 / K), 0.5 * CANVAS[1] * (1 + 1 / K))
DEPTH_UNITS = 5000.0

# ---- chapter 1 / 7 values -------------------------------------------------------------------------------------
HEX = dict(plaster="#ECE5DA", stone="#D8C8AE", joint="#B3A388", gap="#2B2724", walnut="#6B4A33", bronze="#3A322C",
           sanitary="#EDE6DA", curtain="#E4DACB", bottle="#D3BC90", trav="#D6BFA4", cup="#CFC7BA", vase="#262422",
           sprig="#8A9A7B", ring="#2A2624", towel="#B07A44", brush="#C9B48F")
ROOM = dict(x=(3.25, 6.25), y=(9.95, 13.59), h=2.70)
SHOWER = dict(x=(5.20, 6.25), y=(9.95, 11.15))
NICHE = dict(y=(10.30, 10.90), z=(1.05, 1.40), back=6.37)
CLAD_T = 0.012
SKIN = 0.001                                                    # plaster skin 1 mm proud of the wall solid
SKIRT_H = 0.08
MIRROR = dict(y=(11.80, 12.80), z=(1.15, 1.95), r=0.10, profile=0.015, x_profile=6.228, x_glass=6.232)
VAN = dict(x=(5.77, 6.25), y=(11.75, 12.85), side_t=0.03, r_front=0.03, drawer=(0.50, 0.84), shelf=(0.15, 0.48),
           board=(0.11, 0.15), kick_set=0.08, top=(0.84, 0.88), top_over=0.01, basin_c=(6.00, 12.30), basin_r=0.20, basin_h=0.13)
SCONCE = dict(plates=((6.25, 11.62, 1.65), (6.25, 12.98, 1.65)), w=0.12, h=0.22, proj=0.10)
CURTAIN = dict(n=8, x=(5.225, 5.455), y=11.15, zig=0.022, r=0.033, z=(0.0, 2.70))
RING = dict(c=(12.98, 0.87), x=6.215, R=0.08, t=0.006, plate=(6.238, 12.98, 0.95))
TOWEL = dict(top_z=0.875, top_w=0.150, front_bottom=0.50, back_bottom=0.545, bottom_w=0.220, x_front=(6.188, 6.203),
             x_back=(6.227, 6.240))

IDS = {0: "nothing / outside", 1: "plaster, vanity wall (X 6.25)", 2: "plaster, window wall (Y 9.95)", 3: "plaster, north wall (X 3.25)",
       4: "plaster, west wall (Y 13.59)", 5: "skirting, limestone 8 cm (flush)", 6: "ceiling", 7: "ceiling shadow gap (1 cm)",
       8: "curtain slot in the ceiling (2.5 cm)", 9: "floor, limestone 60 x 120", 10: "floor joints (2 mm)",
       11: "shower cladding, vanity wall (south)", 12: "shower cladding, window wall (east)", 13: "cladding joints",
       14: "niche lining (stone)", 15: "shower fittings, bronze (rain head, arm, mixer)", 16: "shower downlight (shell)",
       17: "mirror glass", 18: "mirror profile, bronze 15 mm", 20: "vanity carcass, walnut (sides, back, bottom board, kick)",
       21: "vanity drawer front, walnut", 22: "vanity finger groove", 23: "vanity top, limestone", 24: "basin, warm white",
       25: "tap, bronze (spout, handle, rosettes)",
       40: "shower-curtain (product)", 41: "shower-dispensers x3 (product)", 42: "vanity-sconces, west (product, provisional)",
       43: "vanity-sconces, east (product, provisional)", 44: "soap-dispenser (product)", 45: "toothbrush-cup (product)",
       46: "toothbrush fillers", 47: "vanity-vase (product)", 48: "sprig (filler)", 49: "towel-ring (product)",
       50: "hand-towel (product)", 90: "other house geometry", 99: "unknown"}
PAL = {0: (0, 0, 0), 1: (236, 229, 218), 2: (214, 205, 192), 3: (196, 188, 178), 4: (180, 172, 160), 5: (216, 200, 174),
       6: (245, 241, 233), 7: (40, 36, 34), 8: (90, 60, 30), 9: (200, 185, 160), 10: (120, 105, 85), 11: (230, 214, 186),
       12: (190, 176, 150), 13: (110, 95, 75), 14: (160, 140, 110), 15: (58, 50, 44), 16: (255, 255, 200), 17: (150, 190, 230),
       18: (70, 55, 45), 20: (107, 74, 51), 21: (140, 100, 70), 22: (30, 20, 15), 23: (240, 220, 190), 24: (250, 250, 245),
       25: (20, 20, 60), 40: (255, 120, 120), 41: (255, 180, 60), 42: (255, 255, 0), 43: (200, 255, 0), 44: (0, 200, 120),
       45: (0, 160, 255), 46: (120, 120, 255), 47: (200, 0, 200), 48: (60, 140, 60), 49: (255, 0, 120), 50: (176, 122, 68),
       90: (60, 60, 60), 99: (255, 0, 255)}
PRODUCT_IDS = set(range(40, 51))
ARCH_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}
FIXED_IDS = {20, 21, 22, 23, 24, 25}
GROUP_ID = {}                                                   # fr.REG name -> id (filled by wm_bath)
PRODUCTS_B2 = ["shower-curtain", "shower-dispensers", "vanity-sconces", "soap-dispenser", "toothbrush-cup", "vanity-vase",
               "towel-ring", "hand-towel"]
FRAMES = {"B2": dict(placeholders=PRODUCTS_B2, lamps=["bath/vanity-sconces", "bath/wall-sconce", "bath/shower-downlight", "bath/niche-led"],
                     also=["bath/wall-sconce", "bath/toothbrush-cup-filler", "bath/vanity-vase-filler"], vanity=True),
          "B2-plate": dict(placeholders=[], lamps=["bath/shower-downlight", "bath/niche-led"], vanity=True),
          "B2-shell": dict(placeholders=[], lamps=["bath/shower-downlight", "bath/niche-led"], vanity=False)}
CAPTURE = {}
LIGHT = dict(window=18.0, downlight_x=2.0, downlight_size=0.25, b1_lamp_x=0.4, sconce_w=5.0, niche_led_w=2.4, plate_target_L=84.0)


def mat(name, key, rough=0.9):
    return fr.mat_cache("wm_bath_" + name, HEX[key], rough)


def reg_arch(name, objs, gid, kind="architecture"):
    objs = [o for o in objs if o is not None]
    r2.reg(name, objs, "bath", kind)
    GROUP_ID[name] = gid
    return objs


def reg_prod(R, slot, objs, gid, src):
    r3.reg(R, f"bath/{slot}", objs, "bath", src=src)
    GROUP_ID[f"bath/{slot}"] = gid
    return objs


def bx(n, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    return r3.bx("bath_wm_" + n, x0, x1, y0, y1, z0, z1, m, bevel)


def cyl(n, c, r, z0, z1, m, verts=48):
    return r3.cyl("bath_wm_" + n, c, r, z0, z1, m, verts)


def mesh_obj(name, verts, faces, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(m)
    bs.coll("framing").objects.link(ob)
    return ob


def rrect(y0, y1, z0, z1, r, seg=10):
    """Rounded rectangle in (y, z), counter-clockwise, 4 * (seg + 1) points; same parametrisation for any inset."""
    pts = []
    for cy, cz, a0 in ((y1 - r, z0 + r, -90), (y1 - r, z1 - r, 0), (y0 + r, z1 - r, 90), (y0 + r, z0 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def x_prism(name, loop, x0, x1, m):
    """Prism along X from a (y, z) loop."""
    n = len(loop)
    v = [(x0, y, z) for y, z in loop] + [(x1, y, z) for y, z in loop]
    f = [list(range(n))[::-1], list(range(n, 2 * n))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return mesh_obj(name, v, f, m)


def x_ring(name, outer, inner, x0, x1, m):
    """Annulus prism along X between two loops with the same point count."""
    n = len(outer)
    v = [(x0, y, z) for y, z in outer] + [(x0, y, z) for y, z in inner] + [(x1, y, z) for y, z in outer] + [(x1, y, z) for y, z in inner]
    o0, i0, o1, i1 = 0, n, 2 * n, 3 * n
    f = []
    for i in range(n):
        j = (i + 1) % n
        f.append([o0 + i, o0 + j, i0 + j, i0 + i])            # front annulus (x0)
        f.append([o1 + i, i1 + i, i1 + j, o1 + j])            # back annulus
        f.append([o0 + i, o1 + i, o1 + j, o0 + j])            # outer wall
        f.append([i0 + i, i0 + j, i1 + j, i1 + i])            # inner wall
    return mesh_obj(name, v, f, m)


def z_prism(name, loop_xy, z0, z1, m):
    n = len(loop_xy)
    v = [(x, y, z0) for x, y in loop_xy] + [(x, y, z1) for x, y in loop_xy]
    f = [list(range(n))[::-1], list(range(n, 2 * n))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return mesh_obj(name, v, f, m)


def side_panel(name, y0, y1, round_at, m, z1):
    """Vanity side panel: X 5.77-6.25, Y y0-y1, Z 0-z1; its outer front vertical corner rounded (r = thickness)."""
    x0, x1 = VAN["x"]
    r = VAN["r_front"]
    pts = []
    if round_at == "y0":                                       # outer face at y0: round the corner (x0, y0)
        pts += [(x1, y0), (x1, y1), (x0, y1)]
        cx, cy = x0 + r, y0 + r
        pts += [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in np.linspace(180, 270, 9)]
    else:                                                      # outer face at y1: round the corner (x0, y1)
        cx, cy = x0 + r, y1 - r
        pts += [(x1, y0), (x1, y1)]
        pts += [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in np.linspace(90, 180, 9)]
        pts += [(x0, y0)]
    # make counter-clockwise
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        pts = pts[::-1]
    return z_prism(name, pts, 0.0, z1, m)


def kill_names(prefixes=(), exact=()):
    objs = [o for o in bpy.data.objects if o.name in exact or any(o.name.startswith(p) for p in prefixes)]
    return r2.kill_objs(objs)


def torus_yz(name, cx, cy, cz, R, t, m, seg=48, ring=12):
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for j in range(ring):
            b = 2 * math.pi * j / ring
            rr = R + t * math.cos(b)
            v.append((cx + t * math.sin(b), cy + rr * math.cos(a), cz + rr * math.sin(a)))
    for i in range(seg):
        for j in range(ring):
            a, b = i * ring + j, ((i + 1) % seg) * ring + j
            c, d = ((i + 1) % seg) * ring + (j + 1) % ring, i * ring + (j + 1) % ring
            f.append([a, b, c, d])
    return mesh_obj(name, v, f, m)


# ---------------------------------------------------------------------------------------------------------------
# the warm-modern bath (chapter 1, 7.5-7.7)
# ---------------------------------------------------------------------------------------------------------------
def wm_bath(R):
    notes = []
    # ---- out: the 1.1 bath finishes, fittings, vanity, mirror; every bath product proxy ----
    n = kill_names(prefixes=("bath_tile", "bath_skirt_", "bath_sgap_", "sh_floor", "sh_clad_", "sh_arm", "sh_head", "sh_mixer",
                             "track_x520", "track_y1115", "van2_", "mir_fr_"), exact=(r2.MIRROR_NAME,))
    for key in ("shower limestone (shell)", "shower fittings, matte black (shell)", "bath vanity 110 (fixed)", "U6 mirror",
                "mirror oak frame"):
        if key in fr.REG:
            fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if r3.alive(o)]
    for key in [k for k in list(R) if k.startswith("bath/")]:
        if key not in ("bath/shower-downlight", "bath/ceiling-light", "bath/wall-sconce"):
            r3.kill_group(R, key)
    r3.lamp_off("bath/vanity-sconces")
    notes.append(f"removed {n} objects of the 1.1 bath (porcelain tiles, skirting 15, shadow gaps, cladding to 2.20, matte black fittings "
                 "and track, the oak vanity, the oak-framed mirror) and every bath product proxy")
    x0, x1 = ROOM["x"]
    y0, y1 = ROOM["y"]
    H = ROOM["h"]
    pl, st, jt, gp = mat("plaster", "plaster", 0.95), mat("stone", "stone", 0.75), mat("joint", "joint", 0.9), mat("gap", "gap", 0.9)
    bz, wal = mat("bronze", "bronze", 0.55), mat("walnut", "walnut", 0.7)
    san = mat("sanitary", "sanitary", 0.6)
    # ---- plaster skins (outside the shower) and the flush stone skirting ----
    sx = x1 - SKIN                                           # vanity wall face of the skin
    door = (12.39, 13.39)
    reg_arch("bath_wm plaster vanity wall", [bx("pl_s", sx - 0.001, sx, SHOWER["y"][1], y1, SKIRT_H, H, pl)], 1)
    reg_arch("bath_wm plaster window wall", [bx("pl_e", x0, SHOWER["x"][0], y0 + SKIN, y0 + SKIN + 0.001, SKIRT_H, H, pl)], 2)
    reg_arch("bath_wm plaster north wall", [bx("pl_n_a", x0 + SKIN, x0 + SKIN + 0.001, y0, door[0], SKIRT_H, H, pl),
                                            bx("pl_n_b", x0 + SKIN, x0 + SKIN + 0.001, door[0], door[1], 2.40, H, pl),
                                            bx("pl_n_c", x0 + SKIN, x0 + SKIN + 0.001, door[1], y1, SKIRT_H, H, pl)], 3)
    reg_arch("bath_wm plaster west wall", [bx("pl_w", x0, x1, y1 - SKIN - 0.001, y1 - SKIN, SKIRT_H, H, pl)], 4)
    reg_arch("bath_wm skirting stone 8 (flush)", [bx("sk_s", sx - 0.001, sx, SHOWER["y"][1], y1, 0.0, SKIRT_H, st),
                                                   bx("sk_e", x0, SHOWER["x"][0], y0 + SKIN, y0 + SKIN + 0.001, 0.0, SKIRT_H, st),
                                                   bx("sk_n_a", x0 + SKIN, x0 + SKIN + 0.001, y0, door[0], 0.0, SKIRT_H, st),
                                                   bx("sk_n_c", x0 + SKIN, x0 + SKIN + 0.001, door[1], y1, 0.0, SKIRT_H, st),
                                                   bx("sk_w", x0, x1, y1 - SKIN - 0.001, y1 - SKIN, 0.0, SKIRT_H, st)], 5)
    # ---- ceiling: the 1.1 ceiling at 2.70 stays (pidx ceiling); 1 cm shadow gap and the 2.5 cm curtain slot as dark strips ----
    cz = H - 0.0005
    reg_arch("bath_wm ceiling shadow gap", [bx("cg_s", x1 - 0.01, x1, y0, y1, cz - 0.0005, cz, gp), bx("cg_n", x0, x0 + 0.01, y0, y1, cz - 0.0005, cz, gp),
                                            bx("cg_e", x0, x1, y0, y0 + 0.01, cz - 0.0005, cz, gp), bx("cg_w", x0, x1, y1 - 0.01, y1, cz - 0.0005, cz, gp)], 7)
    reg_arch("bath_wm curtain slot", [bx("slot_x", 5.1875, 5.2125, y0 + CLAD_T, 11.1625, cz - 0.0006, cz, gp),
                                      bx("slot_y", 5.1875, x1 - CLAD_T, 11.1375, 11.1625, cz - 0.0006, cz, gp)], 8)
    # ---- floor: limestone over the whole room (the tiles' plane), joints 2 mm ----
    reg_arch("bath_wm floor limestone", [bx("floor", x0, x1, y0, y1, -0.012, 0.0, st)], 9)
    jts = []
    for xx in np.arange(x0 + 0.60, x1 - 0.01, 0.60):
        jts.append(bx(f"fj_x{xx:.2f}", xx - 0.001, xx + 0.001, y0, y1, 0.0, 0.0004, jt))
    for yy in np.arange(y0 + 1.20, y1 - 0.01, 1.20):
        jts.append(bx(f"fj_y{yy:.2f}", x0, x1, yy - 0.001, yy + 0.001, 0.0, 0.0004, jt))
    reg_arch("bath_wm floor joints", jts, 10)
    # ---- shower cladding to the ceiling, the niche lining ----
    cxs = x1 - CLAD_T                                         # cladding face on the vanity wall (south)
    cye = y0 + CLAD_T                                         # cladding face on the window wall (east)
    ny0, ny1 = NICHE["y"]
    nz0, nz1 = NICHE["z"]
    reg_arch("bath_wm cladding south", [bx("cl_s_a", cxs, x1, cye, ny0, 0.0, H, st), bx("cl_s_b", cxs, x1, ny1, SHOWER["y"][1], 0.0, H, st),
                                        bx("cl_s_c", cxs, x1, ny0, ny1, 0.0, nz0, st), bx("cl_s_d", cxs, x1, ny0, ny1, nz1, H, st)], 11)
    reg_arch("bath_wm cladding east", [bx("cl_e", SHOWER["x"][0], cxs, y0, cye, 0.0, H, st)], 12)
    cj = []
    for yy in (ny0, ny1):                                     # full-height joints at the niche module, interrupted by the niche
        cj += [bx(f"cj_v{yy:.2f}a", cxs - 0.0004, cxs, yy - 0.001, yy + 0.001, 0.0, nz0, jt),
               bx(f"cj_v{yy:.2f}b", cxs - 0.0004, cxs, yy - 0.001, yy + 0.001, nz1, H, jt)]
    cj += [bx("cj_h_s_a", cxs - 0.0004, cxs, cye, ny0, nz1 - 0.001, nz1 + 0.001, jt), bx("cj_h_s_b", cxs - 0.0004, cxs, ny1, SHOWER["y"][1], nz1 - 0.001, nz1 + 0.001, jt),
           bx("cj_h_e", SHOWER["x"][0], cxs, cye, cye + 0.0004, nz1 - 0.001, nz1 + 0.001, jt)]
    reg_arch("bath_wm cladding joints", cj, 13)
    reg_arch("bath_wm niche lining", [bx("ni_back", NICHE["back"] - 0.002, NICHE["back"], ny0, ny1, nz0, nz1, st),
                                      bx("ni_l", cxs, NICHE["back"], ny0, ny0 + 0.002, nz0, nz1, st),
                                      bx("ni_r", cxs, NICHE["back"], ny1 - 0.002, ny1, nz0, nz1, st),
                                      bx("ni_b", cxs, NICHE["back"], ny0, ny1, nz0, nz0 + 0.002, st),
                                      bx("ni_t", cxs, NICHE["back"], ny0, ny1, nz1 - 0.002, nz1, st)], 14)
    led = r2.mk_light("bath_wm_niche_led_L", "AREA", (6.262, (ny0 + ny1) / 2, nz1 - 0.006), LIGHT["niche_led_w"], size=0.56, size_y=0.012,
                      aim=(0.45, 0, -1), long_axis=(0, 1, 0), shape="RECTANGLE")
    led.data.color = r2.WARM
    r2.lamp("bath/niche-led", "bath", "cabinet", [], [led], "hidden LED at the niche head, 2700 K (proposal, change 11)", shell=True)
    dlk = r2.LAMPS.get("bath/shower-downlight")
    for li in (dlk or {}).get("lights", []):
        li.data.energy *= LIGHT["downlight_x"]
        if li.data.type == "AREA":
            li.data.size = LIGHT["downlight_size"]
        else:
            li.data.shadow_soft_size = LIGHT["downlight_size"] / 2
    b1 = r2.LAMPS.get("bath/wall-sconce")
    for li in (b1 or {}).get("lights", []):
        li.data.energy *= LIGHT["b1_lamp_x"]
    notes.append(f"light balance (daylight the key, 7.8): bath window x{LIGHT['window']} (the round-4 clay: x4.5); downlight x{LIGHT['downlight_x']}, "
                 f"area {LIGHT['downlight_size']} m (soft); B1 lamp x{LIGHT['b1_lamp_x']}; sconces {LIGHT['sconce_w']} W each; niche LED {LIGHT['niche_led_w']} W")
    notes.append("shower: limestone 12 mm floor to ceiling on both walls, joints Y 10.30 / 10.90 full height and Z 1.40; niche lined; "
                 "LED as an area light at the niche head (no visible strip)")
    # ---- shower fittings, bronze ----
    arm = r2.obox("bath_wm_rain_arm", (cxs, 10.60, 2.16), (5.95, 10.60, 2.16), (0, 1, 0), 0.016, 0.016, bz)
    head = cyl("rain_head", (5.95, 10.60), 0.125, 2.140, 2.150, bz, 64)
    neck = cyl("rain_neck", (5.95, 10.60), 0.010, 2.150, 2.16, bz, 16)
    ros = r2.obox("bath_wm_mixer_ros", (cxs, 10.60, 0.95), (cxs - 0.008, 10.60, 0.95), (0, 1, 0), 0.075, 0.075, bz)
    knob = r2.obox("bath_wm_mixer_knob", (cxs - 0.008, 10.60, 0.95), (cxs - 0.07, 10.60, 0.95), (0, 1, 0), 0.035, 0.035, bz)
    reg_arch("bath_wm shower fittings bronze", [arm, head, neck, ros, knob], 15)
    # ---- the mirror: rounded corners R 10, 15 mm bronze profile, glass inset 4 mm ----
    my0, my1 = MIRROR["y"]
    mz0, mz1 = MIRROR["z"]
    r, p = MIRROR["r"], MIRROR["profile"]
    outer = rrect(my0, my1, mz0, mz1, r)
    inner = rrect(my0 + p, my1 - p, mz0 + p, mz1 - p, r - p)
    prof = x_ring("bath_wm_mirror_profile", outer, inner, MIRROR["x_profile"], x1 - 0.0005, bz)
    glass = x_prism(r2.MIRROR_NAME, inner, MIRROR["x_glass"], x1 - 0.001, fr.mirror_mat())
    reg_arch("bath_wm mirror glass", [glass], 17, kind="mirror")
    reg_arch("bath_wm mirror profile", [prof], 18)
    notes.append("mirror: the 1.1 envelope Y 11.80-12.80, Z 1.15-1.95; corners R 0.10, bronze profile 15 mm (front X 6.228), glass "
                 "front X 6.232 (named mirror_r2 so the round-2 F8 pass runs on it)")
    return notes


def wm_vanity():
    """7.6: walnut box 110 x 48, h 0.88 with the top. Registered as fixed furniture."""
    x0, x1 = VAN["x"]
    y0, y1 = VAN["y"]
    t = VAN["side_t"]
    wal, gp = mat("walnut", "walnut", 0.7), mat("gap", "gap", 0.9)
    st, san, bz = mat("stone", "stone", 0.75), mat("sanitary", "sanitary", 0.6), mat("bronze", "bronze", 0.55)
    zt0, zt1 = VAN["top"]
    carcass = [side_panel("bath_wm_van_side_a", y0, y0 + t, "y0", wal, zt0),
               side_panel("bath_wm_van_side_b", y1 - t, y1, "y1", wal, zt0),
               bx("van_back", x1 - 0.02, x1, y0 + t, y1 - t, VAN["board"][1], zt0, wal),
               bx("van_divider", x0, x1 - 0.02, y0 + t, y1 - t, VAN["shelf"][1], VAN["drawer"][0], wal),
               bx("van_board", x0, x1 - 0.02, y0 + t, y1 - t, VAN["board"][0], VAN["board"][1], wal),
               bx("van_kick", x0 + VAN["kick_set"], x0 + VAN["kick_set"] + 0.018, y0 + t, y1 - t, 0.0, VAN["board"][0], wal)]
    drawer = [bx("van_drawer", x0, x0 + 0.018, y0 + t + 0.002, y1 - t - 0.002, VAN["drawer"][0] + 0.002, VAN["drawer"][1] - 0.02, wal),
              bx("van_drawer_box", x0 + 0.018, x1 - 0.03, y0 + t + 0.004, y1 - t - 0.004, VAN["drawer"][0] + 0.01, VAN["drawer"][1] - 0.025, wal)]
    groove = [bx("van_groove", x0 + 0.012, x0 + 0.03, y0 + t + 0.002, y1 - t - 0.002, VAN["drawer"][1] - 0.02, zt0, gp)]
    top = [bx("van_top", x0 - VAN["top_over"], x1, y0 - VAN["top_over"], y1 + VAN["top_over"], zt0, zt1, st, 0.008)]
    bc = VAN["basin_c"]
    basin = cyl("van_basin", bc, VAN["basin_r"], zt1, zt1 + VAN["basin_h"], san, 96)
    cut = cyl("van_basin_cut", bc, VAN["basin_r"] - 0.008, zt1 + 0.012, zt1 + VAN["basin_h"] + 0.02, san, 96)
    cut.hide_render = True
    cut.hide_viewport = True
    md = basin.modifiers.new("hollow", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.solver = "EXACT"
    md.object = cut
    tap = [r2.obox("bath_wm_tap_ros", (x1, 12.30, 1.06), (x1 - 0.008, 12.30, 1.06), (0, 1, 0), 0.055, 0.055, bz),
           r2.obox("bath_wm_tap_spout", (x1 - 0.008, 12.30, 1.06), (6.08, 12.30, 1.06), (0, 1, 0), 0.018, 0.018, bz),
           r2.obox("bath_wm_tap_hros", (x1, 12.44, 1.06), (x1 - 0.008, 12.44, 1.06), (0, 1, 0), 0.055, 0.055, bz),
           r2.obox("bath_wm_tap_handle", (x1 - 0.008, 12.44, 1.06), (x1 - 0.05, 12.44, 1.06), (0, 1, 0), 0.032, 0.032, bz)]
    reg_arch("bath_wm vanity carcass (fixed)", carcass, 20, kind="furniture")
    reg_arch("bath_wm vanity drawer (fixed)", drawer, 21, kind="furniture")
    reg_arch("bath_wm vanity groove (fixed)", groove, 22, kind="furniture")
    reg_arch("bath_wm vanity top (fixed)", top, 23, kind="furniture")
    reg_arch("bath_wm basin (fixed)", [basin], 24, kind="furniture")
    reg_arch("bath_wm tap bronze (fixed)", tap, 25, kind="furniture")
    return carcass + drawer + groove + top + [basin] + tap


def wm_products(R):
    """7.7 defaults as boxes at the slot envelopes (no floor planter: manager relay 2026-11-17)."""
    notes = []
    C = dict(curtain=mat("curtain", "curtain", 0.95), bottle=mat("bottle", "bottle", 0.8), trav=mat("trav", "trav", 0.85),
             cup=mat("cup", "cup", 0.85), vase=mat("vase", "vase", 0.8), sprig=mat("sprig", "sprig", 0.9), ring=mat("ring", "ring", 0.6),
             towel=mat("towel", "towel", 0.95), brush=mat("brush", "brush", 0.8))
    # curtain: 8 folds, a 30 cm stack from the L corner along the Y 11.15 run, out of the slot, hem on the floor
    cx = np.linspace(CURTAIN["x"][0], CURTAIN["x"][1], CURTAIN["n"])
    folds = [cyl(f"curt_f{i}", (float(x), CURTAIN["y"] + (CURTAIN["zig"] if i % 2 else -CURTAIN["zig"])), CURTAIN["r"], CURTAIN["z"][0],
                 CURTAIN["z"][1], C["curtain"], 24) for i, x in enumerate(cx)]
    reg_prod(R, "shower-curtain", folds, 40, f"7.7: gathered on the Y 11.15 run, {CURTAIN['n']} folds X {cx[0] - CURTAIN['r']:.3f}-"
             f"{cx[-1] + CURTAIN['r']:.3f} (stack centre {cx.mean():.3f}), Z 0-2.70 (out of the slot, hem on the floor)")
    # niche set: 3 identical bottles 7.5 x 16.5, centred, 4 cm apart
    yc = (NICHE["y"][0] + NICHE["y"][1]) / 2
    bot = []
    for i, dy in enumerate((-0.115, 0.0, 0.115)):
        bot += [cyl(f"shd_{i}", (6.31, yc + dy), 0.0375, 1.05, 1.18, C["bottle"]), cyl(f"shd_pump_{i}", (6.31, yc + dy), 0.011, 1.18, 1.215, C["ring"], 16)]
    reg_prod(R, "shower-dispensers", bot, 41, "7.7: three 7.5 x 16.5 bottles centred in the niche, 4 cm apart (Y 10.485 / 10.60 / 10.715)")
    # the sconce pair: provisional blocks on the plates (12 x 22 x 10), lit 2700 K with the light below the block
    sw, se = [], []
    lights = []
    for i, (px, py, pz) in enumerate(SCONCE["plates"]):
        b = bx(f"sconce_{i}", px - SCONCE["proj"], px, py - SCONCE["w"] / 2, py + SCONCE["w"] / 2, pz - SCONCE["h"] / 2, pz + SCONCE["h"] / 2,
               C["trav"], 0.006)
        (sw if i == 0 else se).append(b)
        li = r2.mk_light(f"bath_wm_sconce_L{i}", "POINT", (px - 0.06, py, pz - SCONCE["h"] / 2 - 0.02), LIGHT["sconce_w"], size=0.04)
        li.data.color = r2.WARM
        lights.append(li)
    r3.reg(R, "bath/vanity-sconces", sw + se, "bath", src="7.7 + sconce gate open: blocks 12 x 22 x 10 on the plates, provisional")
    r2.reg("bath_wm vanity-sconces east", se, "bath", "proxy")       # its own pass index for the id map (east)
    GROUP_ID["bath/vanity-sconces"] = 42
    GROUP_ID["bath_wm vanity-sconces east"] = 43
    r2.lamp("bath/vanity-sconces", "bath", "wall", [(o, r2.GLOW * 0.45) for o in sw + se], lights, "travertine block pair (provisional)")
    # vanity group
    reg_prod(R, "soap-dispenser", [cyl("soap", (6.07, 12.58), 0.0375, 0.88, 1.01, C["bottle"]), cyl("soap_pump", (6.07, 12.58), 0.011, 1.01, 1.045, C["ring"], 16),
                                   r2.obox("bath_wm_soap_nozzle", (6.07, 12.58, 1.04), (6.035, 12.555, 1.04), (0, 0, 1), 0.008, 0.008, C["ring"])],
             44, "7.7: (6.07, 12.58), 7.5 x 16.5, the nozzle toward the basin")
    reg_prod(R, "toothbrush-cup", [cyl("cup", (6.12, 12.68), 0.04, 0.88, 0.99, C["cup"])], 45, "7.7: (6.12, 12.68), 8 x 11")
    br = [r2.obox("bath_wm_brush_a", (6.115, 12.675, 0.90), (6.118, 12.705, 1.07), (1, 0, 0), 0.007, 0.007, C["brush"]),
          r2.obox("bath_wm_brush_b", (6.125, 12.685, 0.90), (6.122, 12.712, 1.065), (1, 0, 0), 0.007, 0.007, C["brush"])]
    reg_prod(R, "toothbrush-cup-filler", br, 46, "7.7: two bamboo brushes (filler), heads up, leaning right, top Z 1.07")
    reg_prod(R, "vanity-vase", [cyl("vase", (6.07, 12.78), 0.035, 0.88, 0.978, C["vase"])], 47, "7.7: (6.07, 12.78), 7 x 9.8 (the card)")
    sp = [r2.obox("bath_wm_sprig_stem", (6.07, 12.78, 0.97), (6.065, 12.74, 1.10), (1, 0, 0), 0.004, 0.004, C["sprig"]),
          r3.ell("bath_wm_sprig_leaves", (6.066, 12.75), 0.025, 1.03, 1.10, C["sprig"])]
    reg_prod(R, "vanity-vase-filler", sp, 48, "7.7: one olive sprig (filler), arching left toward the mirror centre, top Z 1.10")
    # ring and towel
    ring = [torus_yz("bath_wm_ring", RING["x"], RING["c"][0], RING["c"][1], RING["R"], RING["t"], C["ring"]),
            r2.obox("bath_wm_ring_post", (RING["plate"][0], RING["c"][0], RING["c"][1] + RING["R"]), (RING["x"], RING["c"][0], RING["c"][1] + RING["R"]),
                    (0, 1, 0), 0.012, 0.012, C["ring"]),
            r2.obox("bath_wm_ring_plate", (6.25, RING["c"][0], RING["c"][1] + RING["R"]), (RING["plate"][0], RING["c"][0], RING["c"][1] + RING["R"]),
                    (0, 1, 0), 0.03, 0.03, C["ring"])]
    reg_prod(R, "towel-ring", ring, 49, "7.7: (6.238, 12.98), D16 ring on a small plate, Z 0.78-0.96")
    T = TOWEL
    yc = RING["c"][0]

    def layer(nm, xa, xb, zb):
        top, bot = T["top_w"] / 2, T["bottom_w"] / 2
        loop = [(yc - bot, zb), (yc + bot, zb), (yc + top, T["top_z"]), (yc - top, T["top_z"])]
        return x_prism(nm, loop, xa, xb, C["towel"])
    tw = [layer("bath_wm_towel_front", T["x_front"][0], T["x_front"][1], T["front_bottom"]),
          layer("bath_wm_towel_back", T["x_back"][0], T["x_back"][1], T["back_bottom"]),
          r2.obox("bath_wm_towel_fold", (RING["x"], yc - T["top_w"] / 2, RING["c"][1] - RING["R"]), (RING["x"], yc + T["top_w"] / 2, RING["c"][1] - RING["R"]),
                  (1, 0, 0), 0.052, 0.03, C["towel"])]
    reg_prod(R, "hand-towel", tw, 50, f"7.7: two layers through the ring, top Z {T['top_z']} ({T['top_w']*100:.0f} wide), bottoms "
             f"{T['front_bottom']} / {T['back_bottom']}, {T['bottom_w']*100:.0f} wide at the hem")
    notes.append("products: 7.7 defaults without the floor planter; the sconce blocks provisional")
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
    out = np.full(idx.shape, 90, np.uint8)
    out[idx == 0] = 0
    for p, g in pid.items():
        out[idx == p] = g
    return out, pid


def edges_of(ids, depth, normal):
    """Structure edges: id changes among architecture + vanity (products and fillers ignored), depth jumps, crease normals."""
    st = np.isin(ids, list(ARCH_IDS | FIXED_IDS))
    e = np.zeros(ids.shape, bool)
    for ax in (0, 1):
        a = ids
        b = np.roll(ids, -1, axis=ax)
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
    u, v = fr.U(cam, x, y, z), fr.V(cam, x, y, z)
    return [round(u * CANVAS[0], 2), round(v * CANVAS[1], 2)]


def bbox_f(ids, gids):
    m = np.isin(ids, list(gids))
    if m.sum() < 5:
        return None
    H, W = ids.shape
    ys, xs = np.nonzero(m)
    u0, v0 = to_frame(xs.min() / W, ys.min() / H)
    u1, v1 = to_frame((xs.max() + 1) / W, (ys.max() + 1) / H)
    return dict(u=[round(u0, 4), round(u1, 4)], v=[round(v0, 4), round(v1, 4)], px=int(m.sum()), frame_pct=round(100 * m.sum() / (H * W) * K * K, 3))


def gap_u(ids, left, right, rows=None):
    """Smallest horizontal gap (frame u) between the right edge of group `left` and the left edge of group `right`, row by row."""
    H, W = ids.shape
    best = None
    ml, mr = np.isin(ids, list(left)), np.isin(ids, list(right))
    for y in (range(H) if rows is None else rows):
        a, b = np.nonzero(ml[y])[0], np.nonzero(mr[y])[0]
        if len(a) == 0 or len(b) == 0:
            continue
        g = (b.min() - a.max() - 1) / W * K
        best = g if best is None or g < best else best
    return None if best is None else round(float(best), 4)


def vertical_tilt(ids, a, b, rows, x_expect, win=15):
    """Tilt (deg) of the boundary between ids a (left) and b (right), searched within +-win px of x_expect, fitted over rows."""
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


def checks_7_3(fid, cam, ids):
    C = {}
    corner = (6.25 - CLAD_T, 9.95 + CLAD_T)
    cu = UVf(cam, corner[0], corner[1], 1.15)[0]
    C["mirror_centre_u"] = dict(target="0.672 +-0.02", value=round(UVf(cam, 6.25, 12.30, 1.55)[0], 4))
    C["mirror_centre_u"]["ok"] = abs(C["mirror_centre_u"]["value"] - 0.672) <= 0.02
    su = [round(UVf(cam, *SCONCE["plates"][i])[0], 4) for i in (0, 1)]
    sv = [round(UVf(cam, *SCONCE["plates"][i])[1], 4) for i in (0, 1)]
    C["sconce_pair_u"] = dict(target="about 0.522 / 0.873, the same height", value=su, plate_v=sv,
                              ok=abs(su[0] - 0.522) <= 0.02 and abs(su[1] - 0.873) <= 0.02)
    C["SE_corner_line_u"] = dict(value=round(cu, 4), note="the visible stone inside corner (6.238, 9.962)")
    if fid == "B2":
        cb = bbox_f(ids, {40})
        over = round(cb["u"][1] - cu, 4)
        C["curtain_vs_corner"] = dict(rule="overlap >= 0.03, or clear >= 0.02; never touching", stack_u=cb["u"], corner_u=round(cu, 4),
                                      overlap=over, ok=over >= 0.03 or (cu - cb["u"][1]) >= 0.02 or (cb["u"][0] - cu) >= 0.02,
                                      stack_left_third=cb["u"][1] <= 1 / 3 + 0.02)
        # the same rule with the stack centred on the slot's gather point X 5.30 (analytic, same folds shifted)
        sh = 5.30 - float(np.mean(CURTAIN["x"]))
        xs = np.linspace(CURTAIN["x"][0], CURTAIN["x"][1], CURTAIN["n"]) + sh
        right = max(UVf(cam, float(x) + CURTAIN["r"] * math.cos(a), CURTAIN["y"] + (CURTAIN["zig"] if i % 2 else -CURTAIN["zig"]) +
                        CURTAIN["r"] * math.sin(a), 1.0)[0] for i, x in enumerate(xs) for a in np.linspace(0, 2 * math.pi, 73))
        C["curtain_vs_corner"]["if_stack_centred_at_5.30"] = dict(overlap=round(right - cu, 4), ok=right - cu >= 0.03)
        nb = bbox_f(ids, {14})
        C["niche_right_of_curtain"] = dict(niche_u=nb["u"] if nb else None, ok=bool(nb and nb["u"][0] > cb["u"][1]))
        bt = bbox_f(ids, {41})
        C["niche_bottles_visible"] = bt
        # sprig vs mirror bottom (no kissing, >= 0.02)
        sp = bbox_f(ids, {48})
        mb = UVf(cam, 6.25, 12.78, MIRROR["z"][0])[1]
        C["sprig_vs_mirror_bottom"] = dict(sprig_top_v=sp["v"][0] if sp else None, mirror_bottom_v=round(mb, 4),
                                           gap=round(sp["v"][0] - mb, 4) if sp else None, ok=bool(sp and sp["v"][0] - mb >= 0.02))
        # towel vs vanity (>= 0.02), right margin
        g = gap_u(ids, FIXED_IDS, {50})
        tb = bbox_f(ids, {50})
        rb = bbox_f(ids, {49})
        vb = bbox_f(ids, FIXED_IDS)
        C["towel_vs_vanity"] = dict(gap_u=g, ok=g is not None and g >= 0.02, towel=tb, vanity=vb)
        # analytic: the towel hem's near corner vs the vanity's right silhouette (the side panel's back edge / the top's corner)
        van_r = max(UVf(cam, 6.25, VAN["y"][1], 0.5)[0], UVf(cam, 6.25, VAN["y"][1] + VAN["top_over"], 0.86)[0])
        for name, yc in (("ring at Y 12.98 (slot)", 12.98), ("ring at Y 13.04", 13.04), ("ring at Y 13.05", 13.05)):
            hem = UVf(cam, TOWEL["x_front"][0], yc - TOWEL["bottom_w"] / 2, TOWEL["front_bottom"])[0]
            topc = UVf(cam, TOWEL["x_front"][0], yc - TOWEL["top_w"] / 2, TOWEL["top_z"])[0]
            C["towel_vs_vanity"].setdefault("analytic", {})[name] = dict(gap_hem=round(hem - van_r, 4), gap_top=round(topc - van_r, 4),
                                                                          ok=min(hem, topc) - van_r >= 0.02)
        C["towel_under_east_sconce"] = dict(towel_u=tb["u"] if tb else None, sconce_u=su[1], ring_u=rb["u"] if rb else None)
        C["right_margin_after_towel"] = dict(plaster_from_u=tb["u"][1] if tb else None, note="bare plaster to the right edge")
        cl = bbox_f(ids, {12})
        C["left_margin"] = dict(note="floor planter out (manager relay): at the left edge plaster of the window wall (u 0 .. X 5.20), its stone "
                                     "skirting, the floor, then the stone cladding", cladding_east_u=cl["u"] if cl else None,
                                plaster_east=bbox_f(ids, {2}))
    # the ceiling slot as a thin line, top left: where does the top frame edge cut?
    sl = bbox_f(ids, {8})
    def z_at_top(x, y):
        yaw = math.radians(-57.0)
        d = -math.sin(yaw) * (x - 3.80) - math.cos(yaw) * (y - 13.20)
        return round(1.15 + 0.46 * d / 1.1852, 3)
    C["ceiling_slot_line"] = dict(slot_px_in_frame=sl, ok=sl is not None,
                                  top_edge_Z=dict(at_the_curtain_stack=z_at_top(5.34, 11.15), at_the_SE_corner=z_at_top(6.238, 9.962),
                                                  at_the_mirror_wall_centre=z_at_top(6.25, 12.30)),
                                  ceiling_Z=2.70, ceiling_px_canvas=int((ids == 6).sum()))
    # verticals in the clay (tilt 0 by construction), measured on the id boundaries
    H, W = ids.shape
    rows = range(int(0.15 * H), int(0.85 * H))
    xc = fr.U(cam, corner[0], corner[1], 1.5) * W
    xe = fr.U(cam, 6.238, 11.15, 1.8) * W
    C["verticals_deg"] = dict(by_construction="camera tilt 0, roll 0: every vertical is vertical in the clay",
                              SE_corner=vertical_tilt(ids, {12}, {11}, rows, xc),
                              cladding_end_Y_11_15=vertical_tilt(ids, {11}, {1}, range(int(0.08 * H), int(0.45 * H)), xe),
                              target="|tilt| <= 0.5")
    return C


def mirror_f8(cam):
    """F8 on the rounded mirror: r2.mirror_pass casts a 48 x 48 grid on the glass's box; points outside the rounded corners hit the
    profile or the wall and are skipped, so its sample count is the rounded glass."""
    res = r2.mirror_pass(dict(loc=[3.80, 13.20, 1.15]), cam)
    rect = (MIRROR["y"][1] - MIRROR["y"][0] - 2 * MIRROR["profile"]) * (MIRROR["z"][1] - MIRROR["z"][0] - 2 * MIRROR["profile"])
    rr = rect - (4 - math.pi) * (MIRROR["r"] - MIRROR["profile"]) ** 2
    res["rounded_glass_area_m2"] = round(rr, 4)
    res["area_vs_1_1_rect_100x80_inside_15mm"] = round(rr / rect, 4)
    return res


def lock_target(cam, depth_img):
    """Named lines (3D segments) projected to canvas pixels; each sampled along its length and kept where the depth pass sees it."""
    H, W = depth_img.shape
    cxs, cye = 6.25 - CLAD_T, 9.95 + CLAD_T
    L = {
        "SE corner (stone inside corner)": ((cxs, cye, 0.0), (cxs, cye, 2.70)),
        "cladding end, vanity wall (Y 11.15)": ((cxs, 11.15, 0.0), (cxs, 11.15, 2.70)),
        "cladding end, window wall (X 5.20)": ((5.20, cye, 0.0), (5.20, cye, 2.70)),
        "cladding joint Y 10.30, below the niche": ((cxs, 10.30, 0.0), (cxs, 10.30, 1.05)),
        "cladding joint Y 10.30, above the niche": ((cxs, 10.30, 1.40), (cxs, 10.30, 2.70)),
        "cladding joint Y 10.90, below the niche": ((cxs, 10.90, 0.0), (cxs, 10.90, 1.05)),
        "cladding joint Y 10.90, above the niche": ((cxs, 10.90, 1.40), (cxs, 10.90, 2.70)),
        "cladding joint Z 1.40, south (left of the niche)": ((cxs, cye, 1.40), (cxs, 10.30, 1.40)),
        "cladding joint Z 1.40, south (right of the niche)": ((cxs, 10.90, 1.40), (cxs, 11.15, 1.40)),
        "cladding joint Z 1.40, east": ((5.20, cye, 1.40), (cxs, cye, 1.40)),
        "niche sill (Z 1.05)": ((cxs, 10.30, 1.05), (cxs, 10.90, 1.05)),
        "niche head (Z 1.40)": ((cxs, 10.30, 1.40), (cxs, 10.90, 1.40)),
        "ceiling line, vanity wall": ((6.25, 11.15, 2.70), (6.25, 13.59, 2.70)),
        "ceiling line, shower": ((cxs, cye, 2.70), (cxs, 11.15, 2.70)),
        "floor line, vanity wall (shower edge to vanity)": ((6.25, 11.15, 0.0), (6.25, 11.75, 0.0)),
        "floor line, vanity wall (vanity to the right edge)": ((6.25, 12.85, 0.0), (6.25, 13.59, 0.0)),
        "skirting top, vanity wall (right of the vanity)": ((6.25, 12.85, 0.08), (6.25, 13.59, 0.08)),
        "skirting top, vanity wall (left of the vanity)": ((6.25, 11.15, 0.08), (6.25, 11.75, 0.08)),
        "mirror profile, left (Y 11.80)": ((MIRROR["x_profile"], 11.80, 1.25), (MIRROR["x_profile"], 11.80, 1.85)),
        "mirror profile, right (Y 12.80)": ((MIRROR["x_profile"], 12.80, 1.25), (MIRROR["x_profile"], 12.80, 1.85)),
        "mirror profile, top (Z 1.95)": ((MIRROR["x_profile"], 11.90, 1.95), (MIRROR["x_profile"], 12.70, 1.95)),
        "mirror profile, bottom (Z 1.15)": ((MIRROR["x_profile"], 11.90, 1.15), (MIRROR["x_profile"], 12.70, 1.15)),
        "vanity top, front edge (Z 0.88)": ((5.76, 11.74, 0.88), (5.76, 12.86, 0.88)),
        "vanity top, underside (Z 0.84)": ((5.76, 11.74, 0.84), (5.76, 12.86, 0.84)),
        "vanity, front left (Y 11.75)": ((5.77, 11.75, 0.0), (5.77, 11.75, 0.84)),
        "vanity, front right (Y 12.85)": ((5.77, 12.85, 0.0), (5.77, 12.85, 0.84)),
        "vanity, back right at the wall (Y 12.85)": ((6.25, 12.85, 0.0), (6.25, 12.85, 0.84)),
        "drawer, bottom (Z 0.50)": ((5.77, 11.78, 0.50), (5.77, 12.82, 0.50)),
        "open shelf, board top (Z 0.15)": ((5.77, 11.78, 0.15), (5.77, 12.82, 0.15)),
        "floor joint Y 11.15": ((3.85, 11.15, 0.0), (6.25, 11.15, 0.0)),
        "floor joint Y 12.35": ((3.85, 12.35, 0.0), (5.77, 12.35, 0.0)),
        "floor joint X 5.65": ((5.65, 9.95, 0.0), (5.65, 13.59, 0.0)),
        "floor joint X 5.05": ((5.05, 9.95, 0.0), (5.05, 13.59, 0.0)),
        "floor joint X 4.45": ((4.45, 9.95, 0.0), (4.45, 13.59, 0.0)),
    }
    yaw = math.radians(-57.0)
    out = {}
    for name, (a, b) in L.items():
        pts, vis = [], 0
        for t in np.linspace(0, 1, 41):
            p = [a[i] + (b[i] - a[i]) * t for i in range(3)]
            u, v = fr.U(cam, *p), fr.V(cam, *p)
            if not (0 <= u < 1 and 0 <= v < 1):
                continue
            x, y = int(u * W), int(v * H)
            dp = -math.sin(yaw) * (p[0] - 3.80) - math.cos(yaw) * (p[1] - 13.20)
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


def tone_frames(frames, cam, ref_frame, out_dir):
    import tone_r4 as T
    toner = T.Toner()
    ref_pts = [(6.25, 13.30, 2.05), (6.25, 13.30, 1.40)]       # bare plaster right of the east sconce
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
        L = np.mean([T.L_hsl(T.patch(t, uu, vv, 0.010)) for uu, vv in zip(u, v)])
        if L < LIGHT["plate_target_L"]:
            lo = e
        else:
            hi = e
    bpy.data.images.remove(img)
    post = dict(exposure=round(e, 4), wb_gains=[round(float(g), 4) for g in gains], reference=dict(xyz=ref_pts, frame=ref_frame, target_L_hsl=LIGHT["plate_target_L"]),
                note="gains make the plaster patch read #ECE5DA's chroma; one exposure and one balance for every frame (one camera point)")
    for fid in frames:
        img, lin = toner.load(os.path.join(r4.EXR_DIR, f"{fid}.exr"))
        t = T.shoulder(toner.tone(img, lin, e, gains))
        bpy.data.images.remove(img)
        T.save_png(t, os.path.join(out_dir, f"{fid}.png"))
    return post


def plaster_readings(path, cam):
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
    out = {}
    pts = {"plaster left of the mirror (11.70, 1.90)": (6.25, 11.70, 1.90), "plaster right of the mirror (12.90, 1.95)": (6.25, 12.90, 1.95),
           "plaster above the mirror (12.30, 2.30)": (6.25, 12.30, 2.30), "plaster right of the towel (13.25, 1.40)": (6.25, 13.25, 1.40),
           "stone, shower wall left of the niche (10.10, 1.70)": (6.238, 10.10, 1.70), "stone, shower east wall (5.70, 1.70)": (5.70, 9.962, 1.70),
           "walnut, drawer front": (5.77, 12.30, 0.68), "floor stone (5.0, 12.6)": (5.0, 12.6, 0.0)}
    import colorsys
    for k, p in pts.items():
        uu, vv = fr.U(cam, *p), fr.V(cam, *p)
        H, W = a.shape[:2]
        x, y = int(uu * W), int(vv * H)
        if not (8 <= x < W - 8 and 8 <= y < H - 8):
            out[k] = "outside the canvas"
            continue
        q = a[y - 8:y + 8, x - 8:x + 8].reshape(-1, 3).mean(0)
        h, l, s = colorsys.rgb_to_hls(*q)
        lin = srgb_to_lin(q * 255)
        Y = float(lin @ np.array([0.2126, 0.7152, 0.0722]))
        Lstar = 116 * (Y ** (1 / 3)) - 16 if Y > 0.008856 else 903.3 * Y
        out[k] = dict(rgb=[int(round(c * 255)) for c in q], H=round(h * 360, 1), S_hsl=round(s * 100, 1), L_hsl=round(l * 100, 1), L_star=round(Lstar, 1))
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(float)
    x0, y0, x1, y1 = [int(round(c)) for c in FRAME_BOX]
    out["frame_mean_L_8bit"] = round(float((rgb[y0:y1, x0:x1] * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1)
    return out


# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="B2,B2-plate,B2-shell")
    ap.add_argument("--res", type=int, default=CANVAS[0], help="canvas width (the 16:9 frame is res / 1.0604)")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=LIGHT["window"])
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
        r3.FRAMES[fid] = ("bath", "B2", "bath")
        r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT["B2"]
        cams[fid] = dict(cams["B2"], id=fid)
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
    notes["wm_bath"] = wm_bath(R)
    vanity = wm_vanity()
    notes["wm_bath"] += wm_products(R)
    bpy.context.view_layer.update()
    rep = dict(stage="warm-modern bath clay, B2 (render-agent, 2026-11-17; docs/proposals/wm-bath-render-2026-11-17.md ch. 1, 7)",
               date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"], camera=cams["B2"],
               canvas=dict(px=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], K=K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: tone_frames()",
               build_notes=notes, ids=IDS, frames={})
    tmp = tempfile.mkdtemp(prefix="wm-bath-")
    r4.OS_STATE["on"] = True
    for fid in frames:
        F = FRAMES[fid]
        r3.set_hidden(vanity, not F["vanity"])
        fplan = dict(placeholders=F["placeholders"], lamps=F["lamps"], also_visible=F.get("also", []), notes=f"warm-modern {fid}")
        Rr = r3.run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, {}, cfg)
        depth, idx, normal = CAPTURE["last"]
        ids, counts, pid = save_passes(fid, out, depth, idx, normal)
        cam = S["cam"]
        r3.set_hidden(vanity, not F["vanity"])
        Rr["id_px"] = counts
        Rr["pidx_to_id"] = pid
        Rr["checks_7_3"] = checks_7_3(fid, cam, ids)
        Rr["F8_mirror_rounded"] = mirror_f8(cam) if F["vanity"] else None
        Rr["boxes_frame"] = {IDS[g]: bbox_f(ids, {g}) for g in sorted(PRODUCT_IDS | FIXED_IDS | {8, 14, 17, 18}) if bbox_f(ids, {g})}
        if fid == "B2":
            rep["lock_target"] = "lock-target.json"
            json.dump(dict(frame="B2 clay", canvas=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], camera=cams["B2"],
                           method="analytic projection of the 3D lines; 'samples' are [x, y, seen] in canvas px, seen = the depth pass agrees",
                           lines=lock_target(cam, depth)), open(os.path.join(out, "lock-target.json"), "w"), indent=1)
        shutil.copy(os.path.join(raw, f"{fid}.png"), os.path.join(SCR, "raw", f"{fid}-untoned.png"))
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr["runtime_s"], "s", flush=True)
    cam = S["cam"]                                            # still the B2 camera with the overscan, as rendered
    ref = "B2-plate" if "B2-plate" in frames else frames[0]
    rep["post"] = tone_frames(frames, cam, ref, out)
    for fid in frames:
        rep["frames"][fid]["readings"] = plaster_readings(os.path.join(out, f"{fid}.png"), cam)
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
