#!/usr/bin/env python3
"""
framing_wm_kids.py: the warm-modern BOY'S and GIRL'S rooms as a clay, frames K-boy and K-girl, render-agent, 2026-11-24. 0 var2 tokens.
Brief: briefs/wm-kids-stage1-render-2026-11-24.md, task 1. Spec: master-designer docs/proposals/wm-kids-rooms-render-2026-11-19.md,
chapter ד over chapters א-ג: א.1 (the shell and the fixed walnut), א.2 (the frame), א.3.2 + ד.2 (the places; the nest after ד.2),
ב.1 / ב.3 (the girl: the same shell + 3.63 in Y, the blush-clay band, her own textiles, toys and basket).

The scene is the round-4 house clay (framing_r4.py, imported, nothing changed there; house plan 1.1) with the two kids' rooms rebuilt by
wm_kids(), wm_fixed() and wm_products(), the way framing_wm_work.py rebuilt the work room (nothing changed there either):
  - [K-1] plaster #ECE5DA as 1 mm skins; the band: the same plaster in an earth pigment on the east and north walls from Z 0 to 1.25
    (under the window to the slab), boy "olive leaf" #A8A88E, girl "blush clay" #E8D5CC; crisp top line, no rail, no groove; the
    skirting (15, 1.5 proud) in the band colour on those two walls, in the wall colour elsewhere;
  - [K-2] W-boy / W-girl in the 1.1 opening: bronze-espresso #3A322C steel at the outer face, 45 mm sight lines, two equal 0.70 panes,
    no transom; plaster reveals 0.35 deep; a 4 cm honed limestone #D8C8AE slab on the sill, 2 cm proud;
  - [K-3] ceiling 3.00 with a 1 cm shadow gap, no cornice;  [K-4] smoked oak #8B6F55 in 22 cm planks along Y;
  - [K-5] the door (behind the camera): walnut linings, the leaf in the wall colour;  [K-6] the wardrobe front in the wall colour;
  - [K-7] fixed walnut #6B4A33 (plan B, not sold): the bed 96 x 196 (full head and foot boards to 0.60 with R 12 top corners, 3 cm thick,
    an 18 cm side frame in line with the mattress base, a 6 cm recessed plinth, the mattress top at 0.42), the desk 90 x 50 x 70 (3 cm
    top, four 4.5 legs) and the chair (seat 42, rounded back 72) at (0.66, 11.00), back to the camera (gap g5: fixed until found);
  - [K-8] the hero corner (-2.30, 10.25) stays sharp;
  - the defaults that passed the photo check (ד.2) as boxes at their places; the gaps are not built.
Frames (cameras K-boy / K-girl from docs/house-plan.json: (1.10, 13.00 | 16.63, 1.00), yaw 33, 24 mm, u0 0.52, v0 0.44; the round-4
overscan canvas 2720 x 1530 with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57]):
  K-<kid>          the defaults clay: shell + fixed furniture + the defaults; the pendant lit
  K-<kid>-plate    the empty plate: shell + bed (bare mattress), desk, chair; every product hidden, every lamp off
  K-<kid>-shell    the shell alone
  K-<kid>-bed      the bed's textiles and the basket only (no cushions, no soft toy): the placeholders of the bed pass, so the standing
                   pillow is whole where the nest will sit (the nest is the next pass)
Per frame: <id>.png (toned clay), <id>-depth.png (16 bit, metres = value / 5000), <id>-id.png (palette, legend in selfcheck.json),
<id>-edges.png; selfcheck.json; <kid>-lock-target.json. The EXRs stay in the scratchpad (the girl's plate is derived from the boy's
through the ratio of the two plate clays: render-agent tools, stage1-2026-11-24).

  python3 framing_wm_kids.py --frames K-boy-plate,K-boy,K-boy-shell,K-girl-plate,K-girl --samples 16
  python3 framing_wm_kids.py --frames K-boy --res 960 --samples 4 --out /tmp/x          # smoke test
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
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wm-kids/clay"
OUT = os.path.join(HERE, "framing", "wm-kids-2026-11-24")
r4.EXR_DIR = os.path.join(SCR, "exr")
CANVAS = (2720, 1530)
K = r4.OS_K
FRAME_BOX = (0.5 * CANVAS[0] * (1 - 1 / K), 0.5 * CANVAS[1] * (1 - 1 / K), 0.5 * CANVAS[0] * (1 + 1 / K), 0.5 * CANVAS[1] * (1 + 1 / K))
DEPTH_UNITS = 5000.0
DY = {"boy": 0.0, "girl": 3.63}

HEX = dict(plaster="#ECE5DA", band_boy="#A8A88E", band_girl="#E8D5CC", oak="#8B6F55", oak_l="#917559", oak_d="#85694F", gap="#2B2724",
           walnut="#6B4A33", stone="#D8C8AE", bronze="#3A322C", mattress="#E6E0D6",
           blind="#E9E4DA", shade="#F0E8D8", cord="#E8E2D8", frame="#9A7552", art_c="#D9D1C2", art_a="#E8D6C6", ledge="#D9B98F",
           book_oat="#CDBB9C", book_bone="#E3DACB", book_olive="#8E8D6E", book_caramel="#B08A5E", book_taupe="#9C8E7E",
           pencup_walnut="#5E4030", pencup_beech="#D6B48A", pencil="#C9A27A", bookend="#5A3E2B", steel="#262422", car="#C49A73",
           duvet_stripe="#E4DBCD", duvet_dune="#EDE3D0", pillow_stripe="#E2D8C9", pillow_env="#C9B9A0", pillow_ruffle="#C9C5BD",
           spread_boy="#6E6258", spread_girl="#8E7F70", cush_boy="#A98457", cush_girl="#C29C95", bear="#E6DED2", bunny="#E8DCCF",
           bunny_dress="#C9AE9C", jute="#B99B74", cotton="#E8E3DA", football="#D9D2C4", knit="#D8C2B6")
ROOM = dict(x=(-2.30, 1.55), y=(10.25, 13.73), h=3.00)
SKIN = 0.001
BAND_Z = 1.25
SK = dict(h=0.15, proud=0.015)
WIN = dict(y=(10.75, 12.15), sill=0.75, head=2.70, x_out=-2.65, frame_d=0.04, sight=0.045, slab_t=0.04, slab_proud=0.02)
DOOR = dict(y=(12.63, 13.53), x=(1.55, 1.70), head=2.40)
WARD = dict(x=(-2.30, 0.20), y=13.13)
BED = dict(x=(-2.26, -0.30), w=0.96, board_t=0.03, board_h=0.60, r=0.12, plinth=0.06, rail=(0.06, 0.24), matt=(0.24, 0.42))
DESK = dict(x=(0.10, 1.00), d=0.50, top=(0.67, 0.70), leg=0.045)
CHAIR = dict(c=(0.66, 11.00), seat=(0.39, 0.42), half=0.19, back=(0.42, 0.72), back_r=0.21, back_t=0.022, leg_r=0.016)
PENDANT = dict(c=(-1.94, 10.54), d=0.30, z=(1.45, 1.61))
LIGHT = dict(pend_area_w=22.0, pend_glow=4.0, plate_target_Lstar=87.5)

IDS = {0: "nothing / sky", 1: "plaster, east wall above the band (Y 10.25)", 2: "plaster, north (window) wall above the band",
       3: "plaster, west wall / wardrobe front", 4: "plaster, south (door) wall", 5: "band, east wall", 6: "ceiling",
       7: "ceiling shadow gap", 8: "band, north wall", 9: "skirting (wall colour)", 10: "floor, smoked oak", 11: "floor joints",
       12: "window reveals", 13: "window frame (bronze)", 14: "sill slab (limestone)", 15: "outside ground", 16: "door (leaf + linings)",
       19: "skirting (band colour)",
       20: "bed head and foot boards (fixed walnut)", 21: "bed side frame and plinth (fixed walnut)", 22: "mattress (bare)",
       23: "desk top (fixed walnut)", 24: "desk legs (fixed walnut)", 25: "chair (fixed walnut)",
       40: "roman-blind", 41: "pendant", 42: "framed-prints A + B (frames)", 43: "framed-prints A + B (art)", 44: "framed-prints C (frame)",
       45: "framed-prints C (art)", 46: "bookshelf (ledges)", 47: "bookshelf filler (books)", 48: "pen-cup", 49: "pen-cup filler (pencils)",
       50: "bookends", 51: "bookends filler (books)", 52: "toy-cars", 53: "bedding (duvet)", 54: "pillow, lying", 55: "pillow, standing",
       56: "bedspread (sample slot)", 57: "cushions-pair", 58: "soft-toy", 59: "toy-basket", 60: "toy-basket filler", 90: "other"}
PAL = {0: (0, 0, 0), 1: (236, 229, 218), 2: (214, 205, 192), 3: (196, 188, 178), 4: (180, 172, 160), 5: (168, 168, 142), 6: (250, 248, 244),
       7: (60, 56, 52), 8: (150, 150, 126), 9: (205, 196, 182), 10: (139, 111, 85), 11: (70, 55, 42), 12: (200, 190, 176), 13: (58, 50, 44),
       14: (216, 200, 174), 15: (120, 140, 110), 16: (150, 110, 80), 19: (140, 140, 118), 20: (107, 74, 51), 21: (92, 64, 44),
       22: (230, 224, 214), 23: (120, 84, 58), 24: (82, 57, 40), 25: (130, 92, 64),
       40: (233, 228, 218), 41: (240, 232, 216), 42: (154, 117, 82), 43: (217, 209, 194), 44: (170, 130, 95), 45: (200, 190, 175),
       46: (217, 185, 143), 47: (205, 187, 156), 48: (94, 64, 48), 49: (201, 162, 122), 50: (90, 62, 43), 51: (176, 138, 94),
       52: (196, 154, 115), 53: (228, 219, 205), 54: (226, 216, 201), 55: (201, 185, 160), 56: (110, 98, 88), 57: (169, 132, 87),
       58: (230, 222, 210), 59: (185, 155, 116), 60: (217, 210, 196), 90: (255, 0, 255)}
PRODUCT_IDS = set(range(40, 61))
FILLER_IDS = {47, 49, 51, 60}
ARCH_IDS = set(range(1, 20))
FIXED_IDS = set(range(20, 26))
GROUP_ID = {}
# slot (registry key suffix) -> clay ids; the gaps (wall-sconce, rug, skateboard, floor-cushion, night-light, desk-bin, doll, doll-pram)
# are not built; the desk chair is fixed furniture until gap g5 closes
SLOTS = {"roman-blind": [40], "pendant": [41], "framed-prints": [42, 43, 44, 45], "bookshelf": [46, 47], "pen-cup": [48, 49],
         "bookends": [50, 51], "toy-cars": [52], "bedding": [53], "pillow-lying": [54], "pillow-standing": [55], "bedspread": [56],
         "cushions-pair": [57], "soft-toy": [58], "toy-basket": [59, 60]}
CAPTURE = {}


def mat(name, key, rough=0.9):
    return fr.mat_cache("wm_kids_" + name, HEX[key], rough)


def reg_arch(kid, name, objs, gid, kind="architecture"):
    objs = [o for o in objs if o is not None]
    key = f"wm_{kid} {name}"
    r2.reg(key, objs, kid, kind)
    GROUP_ID[key] = gid
    return objs


def reg_prod(R, kid, slot, objs, gid, src):
    key = f"{kid}/{slot}"
    r3.reg(R, key, objs, kid, src=src)
    GROUP_ID[key] = gid
    return objs


def bx(n, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    return r3.bx("kd_wm_" + n, x0, x1, y0, y1, z0, z1, m, bevel)


def cyl(n, c, r, z0, z1, m, verts=48):
    return r3.cyl("kd_wm_" + n, c, r, z0, z1, m, verts)


def cone(n, c, r0, r1, z0, z1, m, verts=48):
    return r3.cone("kd_wm_" + n, c, r0, r1, z0, z1, m, verts)


def ell(n, c, r, z0, z1, m):
    return r3.ell("kd_wm_" + n, c, r, z0, z1, m)


def obox(n, a, b, wvec, w, t, m):
    return r2.obox("kd_wm_" + n, a, b, wvec, w, t, m)


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
    """closed prism from a simple 2D loop. axis 'z': loop in (x, y); 'y': loop in (x, z); 'x': loop in (y, z)."""
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


def rrect(x0, x1, y0, y1, r, corners=(True, True, True, True), seg=10):
    """corners: (x0y0, x1y0, x1y1, x0y1)"""
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
# א.1: the architecture
# ---------------------------------------------------------------------------------------------------------------
def wm_kids(R, kid):
    notes = []
    dy = DY[kid]
    for key in (f"{kid}/pendant", f"{kid}/wall-sconce"):
        r3.lamp_off(key)
        r2.LAMPS.pop(key, None)
    keep = {f"{kid}_ceiling", f"{kid}_floor_base", f"{kid}_wr2"}
    victims = [o for o in bpy.data.objects if (o.name.startswith(f"{kid}_") and o.name not in keep) or o.name.startswith(f"W-{kid}_")]
    n = r2.kill_objs(victims)
    for key in [k for k in list(fr.REG) if k.startswith(f"{kid} ")]:
        fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if r3.alive(o)]
    for key in [k for k in list(R) if k.startswith(f"{kid}/")]:
        r3.kill_group(R, key)
    notes.append(f"{kid}: removed {n} objects of the 1.1 / round-3 room (planks, skirting, cornices, the paint layer, the 1.1 window "
                 "frame, sashes, reveals and sill board, the oak bed and desk, every product proxy); lamps dropped and rebuilt")
    x0, x1 = ROOM["x"]
    y0, y1 = ROOM["y"][0] + dy, ROOM["y"][1] + dy
    H = ROOM["h"]
    pl, gp = mat("plaster", "plaster", 0.95), mat("gap", "gap", 0.9)
    band = mat(f"band_{kid}", f"band_{kid}", 0.95)
    wal, st, bz = mat("walnut", "walnut", 0.7), mat("stone", "stone", 0.75), mat("bronze", "bronze", 0.55)
    sh, p = SK["h"], SK["proud"]
    wy0, wy1 = WIN["y"][0] + dy, WIN["y"][1] + dy
    slab_z0 = WIN["sill"] - WIN["slab_t"]
    xw = x0 + SKIN                       # the north wall's room face, X -2.299
    ye = y0 + SKIN                       # the east wall's room face
    # ---- the east wall: plaster above the band, the band below (0.15-1.25), the band-coloured skirting ----
    reg_arch(kid, "plaster east wall", [bx(f"{kid}_pl_e", x0, x1, y0, ye, BAND_Z, H, pl)], 1)
    reg_arch(kid, "band east wall", [bx(f"{kid}_band_e", x0, x1, y0, ye, sh, BAND_Z, band)], 5)
    # ---- the north (window) wall ----
    reg_arch(kid, "plaster north wall", [bx(f"{kid}_pl_n_a", x0, xw, y0, wy0, BAND_Z, H, pl), bx(f"{kid}_pl_n_c", x0, xw, wy0, wy1, WIN["head"], H, pl),
                                          bx(f"{kid}_pl_n_d", x0, xw, wy1, y1, BAND_Z, H, pl)], 2)
    reg_arch(kid, "band north wall", [bx(f"{kid}_band_n_a", x0, xw, y0, wy0, sh, BAND_Z, band), bx(f"{kid}_band_n_b", x0, xw, wy0, wy1, sh, slab_z0, band),
                                       bx(f"{kid}_band_n_c", x0, xw, wy1, y1, sh, BAND_Z, band)], 8)
    # ---- the west wall (wardrobe front, wall colour) and the south (door) wall; both behind / beside the camera ----
    wr = bpy.data.objects.get(f"{kid}_wr2")
    west = [bx(f"{kid}_pl_w", WARD["x"][1], x1, y1 - SKIN, y1, sh, H, pl)]
    if wr is not None:
        wr.data.materials.clear()
        wr.data.materials.append(pl)
        west.append(wr)
    reg_arch(kid, "plaster west wall and wardrobe front", west, 3)
    dy0, dy1 = DOOR["y"][0] + dy, DOOR["y"][1] + dy
    xs = x1 - SKIN
    reg_arch(kid, "plaster south wall", [bx(f"{kid}_pl_s_a", xs, x1, y0, dy0, sh, H, pl), bx(f"{kid}_pl_s_b", xs, x1, dy0, dy1, DOOR["head"], H, pl),
                                          bx(f"{kid}_pl_s_c", xs, x1, dy1, y1, sh, H, pl)], 4)
    # ---- skirting 15, 1.5 proud: band colour on the east and north walls, wall colour on the south and west ----
    reg_arch(kid, "skirting (band colour)", [bx(f"{kid}_sk_e", x0, x1, y0, ye + p, 0.0, sh, band), bx(f"{kid}_sk_n", x0, xw + p, y0, y1, 0.0, sh, band)], 19)
    reg_arch(kid, "skirting (wall colour)", [bx(f"{kid}_sk_s_a", xs - p, x1, y0, dy0, 0.0, sh, pl), bx(f"{kid}_sk_s_b", xs - p, x1, dy1, y1, 0.0, sh, pl),
                                              bx(f"{kid}_sk_w", WARD["x"][1], x1, y1 - SKIN - p, y1, 0.0, sh, pl)], 9)
    # ---- [K-3] ceiling 3.00 (kept), a 1 cm shadow gap round the room ----
    cz = H - 0.0005
    reg_arch(kid, "ceiling shadow gap", [bx(f"{kid}_cg_e", x0, x1, y0, y0 + 0.01, cz - 0.0005, cz, gp), bx(f"{kid}_cg_n", x0, x0 + 0.01, y0, y1, cz - 0.0005, cz, gp),
                                         bx(f"{kid}_cg_w", x0, x1, y1 - 0.01, y1, cz - 0.0005, cz, gp), bx(f"{kid}_cg_s", x1 - 0.01, x1, y0, y1, cz - 0.0005, cz, gp)], 7)
    # ---- [K-4] floor: smoked oak 22 cm planks along Y, staggered, 1.5 mm gaps ----
    rng = np.random.default_rng(31 if kid == "boy" else 37)
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
                planks.append(bx(f"{kid}_pk{k}_{j}", xa, xb, ya, yb_, -0.012, 0.0, oaks[int(rng.integers(0, 3))]))
            yk += L
            j += 1
        xk += Wp
        k += 1
    reg_arch(kid, "floor smoked oak 22", planks, 10)
    # ---- [K-2] the window: plaster reveals, bronze frame at the outer face (45 mm, two 0.70 panes, no transom), limestone slab ----
    xo, fd, s = WIN["x_out"], WIN["frame_d"], WIN["sight"]
    xf = xo + fd
    rev = [bx(f"{kid}_rev_a", xf, x0, wy0, wy0 + 0.001, WIN["sill"], WIN["head"], pl), bx(f"{kid}_rev_b", xf, x0, wy1 - 0.001, wy1, WIN["sill"], WIN["head"], pl),
           bx(f"{kid}_rev_h", xf, x0, wy0, wy1, WIN["head"] - 0.001, WIN["head"], pl)]
    reg_arch(kid, "window reveals (plaster)", rev, 12)
    my = (wy0 + wy1) / 2
    frm = [bx(f"{kid}_wf_a", xo, xf, wy0, wy0 + s, WIN["sill"], WIN["head"], bz), bx(f"{kid}_wf_b", xo, xf, wy1 - s, wy1, WIN["sill"], WIN["head"], bz),
           bx(f"{kid}_wf_t", xo, xf, wy0, wy1, WIN["head"] - s, WIN["head"], bz), bx(f"{kid}_wf_bt", xo, xf, wy0, wy1, WIN["sill"], WIN["sill"] + s, bz),
           bx(f"{kid}_wf_m", xo, xf, my - s / 2, my + s / 2, WIN["sill"], WIN["head"], bz)]
    reg_arch(kid, "window frame (bronze)", frm, 13)
    reg_arch(kid, "sill slab (limestone)", [bx(f"{kid}_sill_slab", xf, x0 + WIN["slab_proud"], wy0, wy1, slab_z0, WIN["sill"], st, 0.003)], 14)
    gs = bpy.data.objects.get("ground_slab")
    if gs is not None and "wm_boy outside ground" not in fr.REG and kid == "boy":
        reg_arch(kid, "outside ground", [gs], 15)
    # ---- [K-5] the door (behind the camera): leaf in the wall colour, walnut linings ----
    lin = []
    lf = bpy.data.objects.get(f"leaf_corridor_{kid}")
    if lf is not None:
        lf.data.materials.clear()
        lf.data.materials.append(pl)
        lin.append(lf)
    dx0, dx1 = DOOR["x"]
    lin += [bx(f"{kid}_dl_a", dx0, dx1, dy0, dy0 + 0.01, 0.0, DOOR["head"], wal), bx(f"{kid}_dl_b", dx0, dx1, dy1 - 0.01, dy1, 0.0, DOOR["head"], wal),
            bx(f"{kid}_dl_h", dx0, dx1, dy0, dy1, DOOR["head"] - 0.01, DOOR["head"], wal)]
    reg_arch(kid, "door (leaf + walnut linings)", lin, 16)
    notes.append(f"{kid}: band {HEX['band_' + kid]} to Z {BAND_Z} on the east (Y {y0}) and north walls (under the window to the slab, "
                 f"Z {slab_z0:.2f}); window frame X {xo}..{xf}, mullion Y {my:.3f}, two 0.70 panes, no transom; slab Z {slab_z0:.2f}-"
                 f"{WIN['sill']}, 2 cm proud; floor {len(planks)} planks of 22 cm along Y; ceiling shadow gap; corner sharp")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# K-7: the fixed walnut bed, desk and chair (plan B: not sold, not counted)
# ---------------------------------------------------------------------------------------------------------------
def wm_fixed(kid):
    dy = DY[kid]
    y0 = ROOM["y"][0] + dy
    wal, mt = mat("walnut", "walnut", 0.7), mat("mattress", "mattress", 0.95)
    bx0, bx1 = BED["x"]
    by0, by1 = y0, y0 + BED["w"]
    t, h, r = BED["board_t"], BED["board_h"], BED["r"]
    board_loop = rrect(by0, by1, 0.0, h, r, corners=(False, False, True, True), seg=12)        # in (y, z): the top corners R 12
    boards = [prism(f"{kid}_bed_head", board_loop, "x", bx0, bx0 + t, wal), prism(f"{kid}_bed_foot", board_loop, "x", bx1 - t, bx1, wal)]
    rails = [bx(f"{kid}_bed_rail_f", bx0 + t, bx1 - t, by1 - 0.025, by1, BED["rail"][0], BED["rail"][1], wal, 0.003),
             bx(f"{kid}_bed_rail_w", bx0 + t, bx1 - t, by0 + 0.002, by0 + 0.025, BED["rail"][0], BED["rail"][1], wal, 0.003),
             bx(f"{kid}_bed_plinth", bx0 + t + 0.05, bx1 - t - 0.05, by0 + 0.06, by1 - 0.06, 0.0, BED["plinth"], wal)]
    matt = [bx(f"{kid}_bed_matt", bx0 + t + 0.003, bx1 - t - 0.003, by0 + 0.027, by1 - 0.027, BED["matt"][0], BED["matt"][1], mt, 0.03)]
    reg_arch(kid, "bed boards (fixed walnut)", boards, 20, kind="furniture")
    reg_arch(kid, "bed side frame + plinth (fixed walnut)", rails, 21, kind="furniture")
    reg_arch(kid, "mattress (bare)", matt, 22, kind="furniture")
    dx0, dx1 = DESK["x"]
    dt0, dt1 = DESK["top"]
    lg = DESK["leg"]
    top = [bx(f"{kid}_desk_top", dx0, dx1, y0, y0 + DESK["d"], dt0, dt1, wal, 0.008)]
    legs = [bx(f"{kid}_desk_leg{i}", lx, lx + lg, ly, ly + lg, 0.0, dt0, wal, 0.008)
            for i, (lx, ly) in enumerate(((dx0 + 0.02, y0 + 0.02), (dx1 - 0.02 - lg, y0 + 0.02), (dx0 + 0.02, y0 + DESK["d"] - 0.02 - lg),
                                          (dx1 - 0.02 - lg, y0 + DESK["d"] - 0.02 - lg)))]
    reg_arch(kid, "desk top (fixed walnut)", top, 23, kind="furniture")
    reg_arch(kid, "desk legs (fixed walnut)", legs, 24, kind="furniture")
    # the chair: seat 42 (a 3 cm walnut seat with rounded corners), four round legs, a continuous rounded back on the camera side
    ccx, ccy = CHAIR["c"][0], CHAIR["c"][1] + dy
    hw = CHAIR["half"]
    seat = [prism(f"{kid}_chair_seat", rrect(ccx - hw, ccx + hw, ccy - hw, ccy + hw, 0.05), "z", CHAIR["seat"][0], CHAIR["seat"][1], wal)]
    lr = CHAIR["leg_r"]
    legs_c = [cyl(f"{kid}_chair_leg{i}", (ccx + sx * (hw - 0.035), ccy + sy * (hw - 0.035)), lr, 0.0, CHAIR["seat"][0], wal, 20)
              for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1)))]
    bc = (ccx, ccy - 0.03)
    br, bt = CHAIR["back_r"], CHAIR["back_t"]
    band = arc(bc, br, 25, 155, 30) + arc(bc, br - bt, 155, 25, 30)
    back = [prism(f"{kid}_chair_back", band, "z", CHAIR["back"][0] + 0.18, CHAIR["back"][1], wal)]
    posts = [cyl(f"{kid}_chair_post{i}", (bc[0] + (br - bt / 2) * math.cos(math.radians(a)), bc[1] + (br - bt / 2) * math.sin(math.radians(a))), 0.012,
                 CHAIR["seat"][1], CHAIR["back"][0] + 0.19, wal, 16) for i, a in enumerate((40, 90, 140))]
    reg_arch(kid, "chair (fixed walnut, gap g5)", seat + legs_c + back + posts, 25, kind="furniture")
    return boards + rails + matt + top + legs + seat + legs_c + back + posts


# ---------------------------------------------------------------------------------------------------------------
# ד.2 defaults as boxes at their places (א.3.2; the nest after ד.2)
# ---------------------------------------------------------------------------------------------------------------
def books_row(kid, tag, x_from, widths, heights, keys, yb, zb, C, lean_face=True, thick=0.012):
    """face-out picture books on a ledge (lean_face: the cover to the camera, leaning on the back) or spines (thick books)"""
    out, x = [], x_from
    for i, (w, hh, key) in enumerate(zip(widths, heights, keys)):
        if lean_face:
            out.append(obox(f"{kid}_{tag}{i}", (x + w / 2, yb + 0.055, zb + 0.002), (x + w / 2, yb + 0.012, zb + hh), (1, 0, 0), w, thick, C[key]))
            x += w * 0.82
        else:
            out.append(bx(f"{kid}_{tag}{i}", x, x + w - 0.002, yb, yb + 0.17, zb, zb + hh, C[key], 0.002))
            x += w
    return out


def wm_products(R, kid):
    notes = []
    dy = DY[kid]
    y0 = ROOM["y"][0] + dy
    keys = [k for k in HEX if k not in ("plaster", "band_boy", "band_girl", "oak", "oak_l", "oak_d", "gap", "walnut", "stone", "bronze", "mattress")]
    C = {k: mat(k, k, 0.9) for k in keys}
    boy = kid == "boy"
    # 1 roman blind 868827 (Light Filter, bone), inside the reveal, raised to 1.85; no cord, no chain
    wy0, wy1 = WIN["y"][0] + dy, WIN["y"][1] + dy
    rb = [bx(f"{kid}_blind", -2.43, -2.395, wy0 + 0.02, wy1 - 0.02, 1.95, 2.69, C["blind"])]
    for i, z in enumerate((1.85, 1.95, 2.05)):
        rb.append(bx(f"{kid}_blindf{i}", -2.41, -2.355, wy0 + 0.025, wy1 - 0.025, z, z + 0.105, C["blind"], 0.02))
    reg_prod(R, kid, "roman-blind", rb, 40, "ד.2 row 1: roman blind 868827 Light Filter, made to 136, folded to Z 1.85 inside the reveal; no cord")
    # 2 pendant: silk pumpkin 30 (warm), Z 1.45-1.61 at (-1.94, 10.54), the white cord to a small canopy; lit in K-<kid>
    pc = (PENDANT["c"][0], PENDANT["c"][1] + dy)
    pz0, pz1 = PENDANT["z"]
    shade = ell(f"{kid}_pendant", pc, PENDANT["d"] / 2, pz0, pz1, C["shade"])
    cord = cyl(f"{kid}_pend_cord", pc, 0.003, pz1, ROOM["h"] - 0.015, C["cord"], 12)
    canopy = cyl(f"{kid}_pend_canopy", pc, 0.05, ROOM["h"] - 0.02, ROOM["h"], C["cord"], 24)
    reg_prod(R, kid, "pendant", [shade, cord, canopy], 41, "ד.2 row 2: silk pumpkin lantern 30 Warm Light (CJYD243199105EV), Z 1.45-1.61")
    pl_ = [r2.mk_light(f"kd_wm_{kid}_pend_area", "AREA", (pc[0], pc[1], pz0 - 0.005), LIGHT["pend_area_w"], size=0.16)]
    r2.lamp(f"{kid}/pendant", kid, "ceiling", [(shade, LIGHT["pend_glow"])], pl_, "silk pumpkin 30 (ד.2)")
    # 4 framed prints, set of 3 (30 x 40): A and B over the desk on the east wall, C standing on the top ledge against the wall
    fw = 0.018
    pr = []
    art = []
    for i, (xa, xb) in enumerate(((0.38, 0.68), (0.72, 1.02))):
        za, zb = 1.37, 1.77
        pr += [bx(f"{kid}_pf{i}_t", xa, xb, y0, y0 + 0.025, zb - fw, zb, C["frame"]), bx(f"{kid}_pf{i}_b", xa, xb, y0, y0 + 0.025, za, za + fw, C["frame"]),
               bx(f"{kid}_pf{i}_l", xa, xa + fw, y0, y0 + 0.025, za, zb, C["frame"]), bx(f"{kid}_pf{i}_r", xb - fw, xb, y0, y0 + 0.025, za, zb, C["frame"])]
        art.append(bx(f"{kid}_pa{i}", xa + fw, xb - fw, y0, y0 + 0.018, za + fw, zb - fw, C["art_c" if boy else "art_a"]))
    tl = 1.58 + 0.002
    cx0, cx1 = -0.85, -0.55
    frameC = [obox(f"{kid}_pfC_box", (cx0 + 0.15, y0 + 0.070, tl), (cx0 + 0.15, y0 + 0.025, tl + 0.40), (1, 0, 0), 0.30, 0.022, C["frame"])]
    artC = [obox(f"{kid}_paC", (cx0 + 0.15, y0 + 0.0815, tl + fw), (cx0 + 0.15, y0 + 0.0365, tl + 0.40 - fw), (1, 0, 0), 0.30 - 2 * fw, 0.004,
                 C["art_c" if boy else "art_a"])]
    reg_prod(R, kid, "framed-prints", pr + art + frameC + artC, 42,
             "ד.2 row 4: the set of 3, 30 x 40 (boy Type C, girl Type A): A X 0.38-0.68 and B X 0.72-1.02 at Z 1.37-1.77; C on the top ledge")
    for o in art:
        GROUP_ID.setdefault(o.name, 43)
    for o in frameC:
        GROUP_ID.setdefault(o.name, 44)
    for o in artC:
        GROUP_ID.setdefault(o.name, 45)
    # 5 bookshelf: two CJ natural-wood ledge pairs (41.9 x 10.2 x 8.9), tiers with the base top at 1.25 and 1.58, X -1.27..-0.43
    led = []
    for ti, zt in enumerate((1.25, 1.58)):
        for li, (la, lb) in enumerate(((-1.27, -0.851), (-0.849, -0.43))):
            led += [bx(f"{kid}_ledge{ti}{li}_b", la, lb, y0, y0 + 0.102, zt - 0.015, zt, C["ledge"], 0.002),
                    bx(f"{kid}_ledge{ti}{li}_k", la, lb, y0, y0 + 0.012, zt - 0.015, zt - 0.015 + 0.089, C["ledge"], 0.002),
                    bx(f"{kid}_ledge{ti}{li}_f", la, lb, y0 + 0.088, y0 + 0.102, zt, zt + 0.035, C["ledge"], 0.002)]
    books = books_row(kid, "bk_up", -1.255, (0.16, 0.15, 0.14), (0.23, 0.26, 0.21), ("book_oat", "book_bone", "book_caramel"), y0, 1.58, C)
    books += books_row(kid, "bk_lo", -1.255, (0.18, 0.17, 0.16, 0.15), (0.22, 0.25, 0.20, 0.23),
                       ("book_bone", "book_olive" if boy else "book_taupe", "book_oat", "book_caramel"), y0, 1.25, C)
    reg_prod(R, kid, "bookshelf", led + books, 46, "ד.2 row 5 (temporary, gap g2): two pairs of 41.9 ledges, X -1.27..-0.43, tiers 1.25 / 1.58; "
             "face-out picture books (filler, no text); the night light's place on the lower tier (X -0.62..-0.50) left empty (gap g7)")
    for o in books:
        GROUP_ID.setdefault(o.name, 47)
    # 7 pen cup: square 8 x 8 x 11 (boy walnut, girl beech) at (0.89, 10.36), on the desk top 0.70; 5 pencils (filler)
    dt = DESK["top"][1]
    pcx, pcy = 0.89, y0 + 0.11
    cup = [bx(f"{kid}_pencup", pcx - 0.04, pcx + 0.04, pcy - 0.04, pcy + 0.04, dt, dt + 0.11, C["pencup_walnut" if boy else "pencup_beech"], 0.003)]
    pens = [obox(f"{kid}_pencil{i}", (pcx + ddx, pcy + ddy, dt + 0.06), (pcx + 1.8 * ddx, pcy + 1.8 * ddy, dt + 0.175), (1, 0, 0), 0.007, 0.007, C["pencil"])
            for i, (ddx, ddy) in enumerate(((-0.015, 0.0), (0.012, 0.01), (0.004, -0.014), (-0.006, 0.014), (0.016, -0.004)))]
    reg_prod(R, kid, "pen-cup", cup + pens, 48, f"ד.2 row 7: square wood pen cup 8 x 8 x 11, {'Black Walnut' if boy else 'Beech'}, at (0.89, {pcy:.2f})")
    for o in pens:
        GROUP_ID.setdefault(o.name, 49)
    # 8 bookends: the walnut L pair on black steel (card 10 x 11.8 x 15.3), X 0.50-0.70, back of the desk; 4 books between (filler)
    be = []
    for i, (xa, pa, pb) in enumerate(((0.50, 0.528, 0.598), (0.672, 0.602, 0.672))):
        be += [bx(f"{kid}_bkend{i}", xa, xa + 0.028, y0 + 0.05, y0 + 0.15, dt + 0.002, dt + 0.153, C["bookend"], 0.002),
               bx(f"{kid}_bkplate{i}", pa, pb, y0 + 0.05, y0 + 0.15, dt, dt + 0.002, C["steel"])]
    bks = books_row(kid, "bk_desk", 0.530, (0.034, 0.030, 0.038, 0.034), (0.215, 0.235, 0.205, 0.225),
                    ("book_oat", "book_olive" if boy else "book_taupe", "book_caramel", "book_bone"), y0 + 0.035, dt + 0.002, C, lean_face=False)
    reg_prod(R, kid, "bookends", be + bks, 50, "ד.2 row 8: walnut L bookends on black steel, X 0.50-0.70; four picture books (filler), no text")
    for o in bks:
        GROUP_ID.setdefault(o.name, 51)
    # 9 toy cars (boy): three beech teether cars 8.5 x 4.3 on the desk's left end, one turned 30 degrees
    if boy:
        cars = [bx(f"{kid}_car0", 0.19, 0.275, y0 + 0.15, y0 + 0.185, dt, dt + 0.043, C["car"], 0.012),
                bx(f"{kid}_car1", 0.33, 0.415, y0 + 0.20, y0 + 0.235, dt, dt + 0.043, C["car"], 0.012),
                obox(f"{kid}_car2", (0.33, y0 + 0.095, dt + 0.0215), (0.33 + 0.085 * math.cos(math.radians(30)), y0 + 0.095 + 0.085 * math.sin(math.radians(30)),
                                                                     dt + 0.0215), (0, 0, 1), 0.043, 0.035, C["car"])]
        reg_prod(R, kid, "toy-cars", cars, 52, "ד.2 row 9: 754833 Car, three of the four on the desk's left end (X 0.19-0.42), one turned 30 deg")
    # 11 bedding: the duvet over the bed, tucked on the wall side, hanging on the front to 5 cm above the floor
    bx0, bx1 = BED["x"]
    by1 = y0 + BED["w"]
    mtop = BED["matt"][1]
    dz = 0.05
    duv = [bx(f"{kid}_duv", -2.19, bx1 - 0.05, y0 + 0.03, by1 - 0.01, mtop, mtop + dz, C["duvet_stripe" if boy else "duvet_dune"], 0.02),
           bx(f"{kid}_duvhang", -2.19, bx1 - 0.05, by1 - 0.01, by1 + 0.03, 0.05, mtop + dz, C["duvet_stripe" if boy else "duvet_dune"], 0.015)]
    # the girl's Dune is 229 long on a 196 bed: the extra length is tucked in at the foot, inside the 0.60 foot board
    reg_prod(R, kid, "bedding", duv, 53, "ד.2 row 11: " + ("the stripe set Light Brown XS, duvet cover 150 x 200 (and the sheet)" if boy else
                                                       "the Dune duvet cover 229 x 173 (open: real-unit photo)"))
    # the nest (ד.2): the lying pillow in front of the standing pillow; the standing pillow against the head board, crossing the sill line
    ly = [bx(f"{kid}_pillow_lying", -2.14, -1.70, y0 + 0.17, y0 + 0.89, mtop + dz, mtop + dz + 0.12, C["pillow_stripe" if boy else "pillow_ruffle"], 0.04)]
    reg_prod(R, kid, "pillow-lying", ly, 54, "the lying pillow 48 x 74: " + ("in the stripe set's pillowcase" if boy else "in the ruffle pillowcase (pair)"))
    stp = [obox(f"{kid}_pillow_stand", (-2.095, y0 + 0.59, mtop + dz), (-2.205, y0 + 0.59, 0.92), (0, 1, 0), 0.72, 0.12,
                C["pillow_env" if boy else "pillow_ruffle"])]
    reg_prod(R, kid, "pillow-standing", stp, 55, "the standing pillow 48 x 74 against the head board, Z to 0.92: " +
             ("the linen envelope Rain And Dew Hemp" if boy else "the ruffle pillowcase Primary Color"))
    # 13 bedspread (the sample slot): folded to about 57 x 97 on the bed's foot third, the front fold over the side
    sp_ = [bx(f"{kid}_spread", -0.93, -0.36, y0 + 0.03, by1 + 0.02, mtop + dz, mtop + dz + 0.045, C["spread_boy" if boy else "spread_girl"], 0.012),
           bx(f"{kid}_spreadhang", -0.93, -0.36, by1 + 0.02, by1 + 0.05, 0.30, mtop + dz + 0.045, C["spread_boy" if boy else "spread_girl"], 0.01)]
    reg_prod(R, kid, "bedspread", sp_, 56, "ד.2 row 13 / ד.4: waffle gauze 150 x 200, V1 " + ("Deep Chestnut Brown" if boy else "Linen Brown") +
             ", folded on the foot third, X -0.93..-0.36")
    # 14 cushions pair 45: against the east wall at the head, the left one overlapping the standing pillow's edge
    cu = [obox(f"{kid}_cush0", (-1.96, y0 + 0.10, mtop + dz), (-1.96, y0 + 0.055, mtop + dz + 0.43), (1, 0, 0), 0.44, 0.13, C["cush_boy" if boy else "cush_girl"]),
          obox(f"{kid}_cush1", (-1.75, y0 + 0.16, mtop + dz), (-1.76, y0 + 0.12, mtop + dz + 0.42), (1, 0, 0), 0.44, 0.13, C["cush_boy" if boy else "cush_girl"])]
    reg_prod(R, kid, "cushions-pair", cu, 57, "ד.2 row 14: corduroy patchwork 45, " + ("Reindeer Brown" if boy else "dusty pink") +
             ", against the east wall at the head")
    # 16 soft toy: sitting on the lying pillow, before the standing one
    tc = (-2.00, y0 + 0.62)
    z_ = mtop + dz + 0.10
    toy = [ell(f"{kid}_toy_body", tc, 0.075, z_, z_ + 0.17, C["bear" if boy else "bunny"]),
           ell(f"{kid}_toy_head", (tc[0] - 0.01, tc[1]), 0.062, z_ + 0.15, z_ + 0.27, C["bear" if boy else "bunny"])]
    if boy:
        toy += [ell(f"{kid}_toy_ear{i}", (tc[0] - 0.01, tc[1] + s_ * 0.045), 0.022, z_ + 0.25, z_ + 0.295, C["bear"]) for i, s_ in enumerate((-1, 1))]
    else:
        toy += [obox(f"{kid}_toy_ear{i}", (tc[0] - 0.01, tc[1] + s_ * 0.025, z_ + 0.25), (tc[0] - 0.015, tc[1] + s_ * 0.035, z_ + 0.37), (0, 1, 0), 0.03, 0.015,
                     C["bunny"]) for i, s_ in enumerate((-1, 1))]
        toy.append(ell(f"{kid}_toy_dress", tc, 0.08, z_, z_ + 0.12, C["bunny_dress"]))
    reg_prod(R, kid, "soft-toy", toy, 58, "ד.2 row 16: 063285 " + ("bear" if boy else "girl 35") + ", sitting on the lying pillow")
    # 17 toy basket at (-0.62, 11.58), cut by the bottom edge (front layer): jute Large 35 x 39 (boy) / cotton rope white L 40 x 45 (girl)
    bc_ = (-0.62, y0 + 1.33)
    r_, h_ = (0.175, 0.39) if boy else (0.20, 0.45)
    bas = [cyl(f"{kid}_basket", bc_, r_, 0.0, h_, C["jute" if boy else "cotton"], 48)]
    bas += [obox(f"{kid}_handle{i}", (bc_[0] + s_ * (r_ - 0.01), bc_[1], h_ - 0.01), (bc_[0] + s_ * (r_ - 0.01), bc_[1], h_ + 0.06), (0, 1, 0), 0.09, 0.012,
                 C["jute" if boy else "cotton"]) for i, s_ in enumerate((-1, 1))]
    if boy:
        fill = [r3.ell("kd_wm_boy_football", (bc_[0] + 0.02, bc_[1] - 0.02), 0.11, h_ - 0.10, h_ + 0.12, C["football"])]
    else:
        fill = [r3.ell(f"kd_wm_girl_knit{i}", (bc_[0] + ox, bc_[1] + oy), rr, h_ - 0.06, h_ - 0.06 + 2 * rr, C["knit"])
                for i, (ox, oy, rr) in enumerate(((-0.06, -0.03, 0.07), (0.06, 0.01, 0.065), (0.0, 0.07, 0.06)))]
    reg_prod(R, kid, "toy-basket", bas + fill, 59, "ד.2 row 17: " + ("jute rope cylinder Large 35 x 39 with a football (filler)" if boy else
                                                              "cotton rope white L 40 x 45 with three knit balls (filler)"))
    for o in fill:
        GROUP_ID.setdefault(o.name, 60)
    notes.append(f"{kid}: the ד.2 defaults built ({'13' if boy else '12'} slots with a card); the gaps are not built; fillers: books, pencils, "
                 f"{'a football' if boy else 'knit balls'}")
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
OBJ_ID = {}


def id_map(idx):
    """pass index -> id; sub-ids (art, fillers) by object name through the object index of the render (pidx is per group)"""
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


def split_sub_ids(fid, out_dir, cam, kid):
    """the art inside the frames and the fillers get their own ids by a second, cheap pass: their objects are drawn alone in an index
    pass at the same camera (no shading), and their pixels relabel the id image where the main pass shows the parent product"""
    from PIL import Image
    ids = np.asarray(Image.open(os.path.join(out_dir, f"{fid}-id.png"))).copy()
    H_, W_ = ids.shape
    rel = {}
    depth = np.asarray(Image.open(os.path.join(out_dir, f"{fid}-depth.png"))).astype(np.float64) / DEPTH_UNITS
    objs = sorted((GROUP_ID[o.name], o.name) for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o.name in GROUP_ID
                  and o.name.startswith(f"kd_wm_{kid}_"))
    for sub, name in objs:
        o = bpy.data.objects[name]
        parent = {43: (42,), 44: (42,), 45: (42, 44), 47: (46,), 49: (48,), 51: (50,), 60: (59,)}.get(sub)
        if parent is None:
            continue
        # project the object's mesh triangles (analytic camera) and paint where the main pass shows the parent at that depth
        mw = o.matrix_world
        me = o.data
        me.calc_loop_triangles()
        poly = np.zeros((H_, W_), np.uint8)
        import cv2
        for tri in me.loop_triangles:
            pts = []
            for vi in tri.vertices:
                v = mw @ me.vertices[vi].co
                u_, v_ = fr.U(cam, v.x, v.y, v.z), fr.V(cam, v.x, v.y, v.z)
                pts.append((u_ * W_, v_ * H_))
            cv2.fillPoly(poly, [np.round(np.array(pts) * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
        m = (poly > 0) & np.isin(ids, parent)
        ids[m] = sub
        rel[o.name] = int(m.sum())
    # the frame of print C keeps id 44 (it is the same product as A + B)
    im = Image.fromarray(ids.astype(np.uint8), "P")
    flat = []
    for k in range(256):
        flat += list(PAL.get(k, (0, 0, 0)))
    im.putpalette(flat)
    im.save(os.path.join(out_dir, f"{fid}-id.png"))
    return rel


# ---------------------------------------------------------------------------------------------------------------
# measurements in FRAME fractions
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


SPEC_UV = {"roman-blind": "0-0.23 / 0-0.14", "pendant": "0.276-0.330 / 0.25-0.30", "framed-prints": "A+B 0.741-0.926 / 0.05-0.27; C 0.50-0.54 / 0.08-0.22",
           "bookshelf": "0.426-0.556 / 0.13-0.36", "pen-cup": "0.87-0.89 / 0.54-0.59", "bookends": "0.77-0.82 / 0.50-0.58",
           "toy-cars": "0.68-0.75 / 0.55-0.58", "bedding": "0.15-0.46 / 0.55-0.68 (to ~0.80)", "pillow-standing": "0.16-0.28 / 0.47-0.63 (ד.2)",
           "pillow-lying": "0.17-0.29 / 0.58-0.64 (ד.2)", "bedspread": "0.38-0.52 / 0.57-0.72", "cushions-pair": "0.29-0.37 / 0.47-0.60",
           "soft-toy": "0.20-0.24 / 0.49-0.60", "toy-basket": "0.257-0.363 / 0.75-1.00"}


def checks_k(fid, cam, ids, kid):
    dy = DY[kid]
    y0 = ROOM["y"][0] + dy
    C = {}
    C["hero_corner_u"] = dict(target="0.303 (left third)", value=r4_(UVf(cam, ROOM["x"][0], y0, 1.0)[0]))
    C["window_jamb_u"] = dict(target="0.230 (23% cut)", value=r4_(UVf(cam, ROOM["x"][0], WIN["y"][0] + dy, 1.5)[0]))
    C["desk_u"] = dict(target="0.626-0.912", value=[r4_(UVf(cam, DESK["x"][0], y0 + DESK["d"], 0.70)[0]), r4_(UVf(cam, DESK["x"][1], y0 + DESK["d"], 0.70)[0])])
    C["bed_front_u"] = dict(target="0.151-0.461", value=[r4_(UVf(cam, BED["x"][0], y0 + BED["w"], 0.42)[0]), r4_(UVf(cam, BED["x"][1], y0 + BED["w"], 0.42)[0])])
    C["band_line_v_at_corner"] = dict(target="Z 1.25", value=r4_(UVf(cam, ROOM["x"][0], y0, BAND_Z)[1]))
    C["sill_v_at_jamb"] = r4_(UVf(cam, ROOM["x"][0], WIN["y"][0] + dy, WIN["sill"])[1])
    C["bed_boards_below_sill_m"] = round(WIN["sill"] - BED["board_h"], 3)
    for slot, gl in SLOTS.items():
        bb = bbox_f(ids, set(gl))
        if bb:
            C.setdefault("boxes", {})[slot] = dict(bb, spec=SPEC_UV.get(slot))
    # the nest (ד.2): the left cushion overlaps the standing pillow's edge (>= 0.02, no strip between them)
    H, W = ids.shape
    st, cu = ids == 55, ids == 57
    rows = np.nonzero(st.any(1) & cu.any(1))[0]
    gaps = []
    for y in rows:
        a, b = np.nonzero(st[y])[0], np.nonzero(cu[y])[0]
        gaps.append((b.min() - a.max() - 1) / W * K)
    C["nest_cushion_vs_standing_pillow"] = dict(rule="the left cushion overlaps the standing pillow's edge, no strip (ד.2)",
                                                min_gap_u=r4_(min(gaps)) if gaps else None, rows=len(rows))
    C["sill_empty"] = dict(rule="nothing on the sill slab (א.1 safety)", products_over_slab_px=int((np.isin(ids, list(PRODUCT_IDS)) &
                                                                                                    _slab_zone(ids)).sum()))
    return C


def _slab_zone(ids):
    """pixels just above the slab's top face in the image (a 6 px band over id 14)"""
    m = ids == 14
    z = np.zeros_like(m)
    for k in range(1, 7):
        z[:-k] |= m[k:]
    return z & ~m


def silhouettes(cam, kid, R, ids):
    """per slot: the full silhouette of its clay objects (every triangle projected, on a canvas with a 50 % margin, so the parts outside
    the frame count) against its pixels inside the 16:9 frame in the id pass: visible = in-frame px / silhouette px (occlusion + frame cut)"""
    import cv2
    H_, W_ = ids.shape
    out = {}
    fx0, fx1 = int(round(FRAME_BOX[0] * W_ / CANVAS[0])), int(round(FRAME_BOX[2] * W_ / CANVAS[0]))
    fy0, fy1 = int(round(FRAME_BOX[1] * H_ / CANVAS[1])), int(round(FRAME_BOX[3] * H_ / CANVAS[1]))
    inside = np.zeros_like(ids, bool)
    inside[fy0:fy1, fx0:fx1] = True
    for slot, gl in SLOTS.items():
        key = f"{kid}/{slot}"
        if key not in R or not R[key]["objs"]:
            continue
        big = np.zeros((2 * H_, 2 * W_), np.uint8)
        for o in R[key]["objs"]:
            if not r3.alive(o) or o.type != "MESH" or GROUP_ID.get(o.name) in FILLER_IDS:
                continue
            mw = o.matrix_world
            me = o.data
            me.calc_loop_triangles()
            for tri in me.loop_triangles:
                pts = []
                for vi in tri.vertices:
                    v = mw @ me.vertices[vi].co
                    pts.append(((fr.U(cam, v.x, v.y, v.z) + 0.5) * W_, (fr.V(cam, v.x, v.y, v.z) + 0.5) * H_))
                cv2.fillPoly(big, [np.round(np.array(pts) * 8).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=3)
        sil = int(big.sum())
        vis = int((np.isin(ids, list(set(gl) - FILLER_IDS)) & inside).sum())
        out[slot] = dict(silhouette_px=sil, visible_in_frame_px=vis, visible_pct=round(100 * vis / max(sil, 1), 1))
    return out


def count_v7q6(ids, items, kid, sil=None):
    rows = {}
    groups = {"bedding": ["bedding", "pillow-lying"] if kid == "boy" else ["bedding"],
              "pillowcase": ["pillow-standing"] if kid == "boy" else ["pillow-lying", "pillow-standing"]}
    prod_slots = {"roman-blind": ["roman-blind"], "pendant": ["pendant"], "framed-prints": ["framed-prints"], "bookshelf": ["bookshelf"],
                  "pen-cup": ["pen-cup"], "bookends": ["bookends"], "toy-cars": ["toy-cars"], **groups, "bedspread": ["bedspread"],
                  "cushions-pair": ["cushions-pair"], "soft-toy": ["soft-toy"], "toy-basket": ["toy-basket"]}
    for prod, members in prod_slots.items():
        gl = set()
        for m_ in members:
            if m_ in SLOTS:
                gl |= set(SLOTS[m_]) - FILLER_IDS
        b = bbox_f(ids, gl)
        if b is None:
            continue
        vis = None
        if sil:
            sp = sum(sil[m_]["silhouette_px"] for m_ in members if m_ in sil)
            vp = sum(sil[m_]["visible_in_frame_px"] for m_ in members if m_ in sil)
            vis = round(100 * vp / max(sp, 1), 1) if sp else None
        hpct = round(100 * (b["v"][1] - b["v"][0]), 2)
        wpct = round(100 * (b["u"][1] - b["u"][0]) * 16 / 9, 2)
        big = max(hpct, wpct)
        ok_area = b["frame_pct"] >= 0.5 or (b["frame_pct"] >= 0.15 and big >= 6.0)
        rows[prod] = dict(frame_pct=b["frame_pct"], larger_dim_pct_of_height=big, visible_pct=vis,
                          counted=bool(ok_area and (vis is None or vis >= 50)), why=None if ok_area and (vis is None or vis >= 50) else
                          ("visible < 50 %" if ok_area else "too small"))
    n = sum(1 for v in rows.values() if v.get("counted"))
    return dict(rule="house-plan frame_checks.F10 (V7Q6), on the clay; a set counts once (prints, cushions, bookends, cars)", counted=n,
                products=len(rows), rows=rows)


def lock_target(cam, depth_img, kid):
    dy = DY[kid]
    y0 = ROOM["y"][0] + dy
    H, W = depth_img.shape
    xw = ROOM["x"][0] + 2 * SKIN
    s = WIN["sight"]
    xf = WIN["x_out"] + WIN["frame_d"]
    wy0, wy1 = WIN["y"][0] + dy, WIN["y"][1] + dy
    bx0, bx1 = BED["x"]
    L = {
        "hero corner (X -2.30, Y y0)": ((ROOM["x"][0], y0 + 0.002, 0.20), (ROOM["x"][0], y0 + 0.002, 2.60)),
        "band top line, east wall (Z 1.25)": ((-2.25, y0 + 0.001, BAND_Z), (1.45, y0 + 0.001, BAND_Z)),
        "band top line, north wall (Z 1.25)": ((xw, y0 + 0.05, BAND_Z), (xw, wy0 - 0.02, BAND_Z)),
        "window jamb at the wall face (Y wy0)": ((xw, wy0, WIN["sill"]), (xw, wy0, 2.60)),
        "window jamb at the wall face (Y wy1)": ((xw, wy1, WIN["sill"]), (xw, wy1, 2.60)),
        "bronze jamb, inner edge": ((xf, wy0 + s, WIN["sill"] + s), (xf, wy0 + s, 2.50)),
        "sill slab, top front edge (Z 0.75)": ((xw + WIN["slab_proud"], wy0, WIN["sill"]), (xw + WIN["slab_proud"], wy1, WIN["sill"])),
        "skirting top, east wall (Z 0.15)": ((-0.25, y0 + SK["proud"], SK["h"]), (1.45, y0 + SK["proud"], SK["h"])),
        "foot board, top edge (Z 0.60)": ((bx1 - 0.015, y0 + 0.05, BED["board_h"]), (bx1 - 0.015, y0 + BED["w"] - BED["r"], BED["board_h"])),
        "foot board, front edge": ((bx1 - 0.015, y0 + BED["w"], 0.05), (bx1 - 0.015, y0 + BED["w"], BED["board_h"] - BED["r"])),
        "desk top, front edge (Z 0.70)": ((DESK["x"][0] + 0.02, y0 + DESK["d"], DESK["top"][1]), (DESK["x"][1] - 0.02, y0 + DESK["d"], DESK["top"][1])),
        "desk front-left leg": ((DESK["x"][0] + 0.02, y0 + DESK["d"] - 0.02, 0.05), (DESK["x"][0] + 0.02, y0 + DESK["d"] - 0.02, 0.62)),
    }
    out = {}
    cx, cy = CAMS[kid]["loc"][0], CAMS[kid]["loc"][1]
    th = math.radians(CAMS[kid]["yaw"])
    fwd = (-math.sin(th), -math.cos(th))
    for name, (a, b) in L.items():
        pts, vis = [], 0
        for t in np.linspace(0, 1, 41):
            p_ = [a[i] + (b[i] - a[i]) * t for i in range(3)]
            u, v = fr.U(cam, *p_), fr.V(cam, *p_)
            if not (0 <= u < 1 and 0 <= v < 1):
                continue
            x, y = int(u * W), int(v * H)
            dp = (p_[0] - cx) * fwd[0] + (p_[1] - cy) * fwd[1]
            dd = float(depth_img[y, x])
            seen = abs(dd - dp) < 0.03 + 0.01 * dp
            vis += seen
            pts.append([round(u * CANVAS[0], 2), round(v * CANVAS[1], 2), bool(seen)])
        if pts:
            out[name] = dict(xyz=[list(a), list(b)], px_ends=[px(cam, *a), px(cam, *b)], samples=pts, visible_frac=round(vis / len(pts), 3))
    return out


# ---------------------------------------------------------------------------------------------------------------
# tone: white balance on the plaster above the band, one exposure for every frame (one camera, same light in both rooms)
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
    ref_pts = [(-1.55, 10.25, 2.25), (-0.15, 10.25, 2.20)]          # the east wall's plaster above the shelf and between shelf and prints
    u = [fr.U(cam, *p_) for p_ in ref_pts]
    v = [fr.V(cam, *p_) for p_ in ref_pts]
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
                note="gains make the east wall's plaster read #ECE5DA's chroma; one exposure and one balance for every frame of both rooms")
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
    for g in (1, 2, 5, 8, 9, 10, 12, 13, 14, 19, 20, 21, 22, 23, 25):
        m = ids == g
        if m.sum() > 50:
            out[IDS[g]] = [round(float(x), 1) for x in np.median(lab[m], 0)]
    x0, y0, x1, y1 = [int(round(c)) for c in FRAME_BOX]
    out["frame_mean_L_8bit"] = round(float((a[y0:y1, x0:x1] * 255 * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1)
    return out


CAMS = {}


# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="K-boy-plate,K-boy,K-boy-shell,K-girl-plate,K-girl")
    ap.add_argument("--res", type=int, default=CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=1.0)
    ap.add_argument("--kids-window", type=float, default=1.0)
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
    FR = {}
    for kid in ("boy", "girl"):
        base = f"K-{kid}"
        CAMS[kid] = cams[base]
        for suf, F in (("", dict(fixed=True, products=True, lamps=[f"{kid}/pendant"])), ("-plate", dict(fixed=True, products=False, lamps=[])),
                       ("-shell", dict(fixed=False, products=False, lamps=[])),
                       ("-bed", dict(fixed=True, products=True, lamps=[f"{kid}/pendant"],
                                     subset=["bedding", "pillow-lying", "pillow-standing", "bedspread", "toy-basket"]))):
            fid = base + suf
            FR[fid] = dict(F, kid=kid)
            r3.FRAMES[fid] = r3.FRAMES[base]
            r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT.get(base, (-1.50, 10.25 + DY[kid]))
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
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name in ("winlight_W-boy", "winlight_W-girl") and a.kids_window != 1.0:
            ob.data.energy *= a.kids_window
    fixed = {}
    notes["wm_kids"] = []
    for kid in ("boy", "girl"):
        notes["wm_kids"] += wm_kids(R, kid)
        fixed[kid] = wm_fixed(kid)
        notes["wm_kids"] += wm_products(R, kid)
    bpy.context.view_layer.update()
    rep = dict(stage="warm-modern kids' rooms clay, K-boy / K-girl (render-agent, 2026-11-24; docs/proposals/wm-kids-rooms-render-2026-11-19.md "
                     "א.1, א.2, א.3.2, ב.1, ב.3, ד.2)", date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"],
               cameras={k: CAMS[k] for k in CAMS},
               canvas=dict(px=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], K=K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: tone_frames()",
               light=dict(LIGHT), build_notes=notes, ids=IDS, slots=SLOTS, frames={})
    prev = None
    if a.keep_post and os.path.exists(os.path.join(out, "selfcheck.json")):
        prev = json.load(open(os.path.join(out, "selfcheck.json")))
        rep["frames"] = prev.get("frames", {})
    tmp = tempfile.mkdtemp(prefix="wm-kids-")
    r4.OS_STATE["on"] = True
    allfixed = fixed["boy"] + fixed["girl"]
    for fid in frames:
        F = FR[fid]
        kid = F["kid"]
        r3.set_hidden(allfixed, not F["fixed"])
        fplan = dict(placeholders=list(F.get("subset", SLOTS)) if F["products"] else [], lamps=F["lamps"], also_visible=[], notes=f"warm-modern {fid}")
        if kid == "girl":
            fplan["placeholders"] = [s for s in fplan["placeholders"] if s != "toy-cars"]
        Rr = r3.run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, {}, cfg)
        depth, idx, normal = CAPTURE["last"]
        ids, counts, pid = save_passes(fid, out, depth, idx, normal)
        cam = S["cam"]
        r3.set_hidden(allfixed, not F["fixed"])
        if F["products"]:
            Rr["sub_ids"] = split_sub_ids(fid, out, cam, kid)
            from PIL import Image
            ids = np.asarray(Image.open(os.path.join(out, f"{fid}-id.png")))
            Rr["silhouettes"] = silhouettes(cam, kid, R, ids)
            Rr["V7Q6"] = count_v7q6(ids, Rr.get("items_visible") or {}, kid, Rr["silhouettes"])
        Rr["id_px"] = counts
        Rr["pidx_to_id"] = pid
        Rr["checks"] = checks_k(fid, cam, ids, kid)
        if fid.endswith("-plate"):
            json.dump(dict(frame=f"{fid} clay", canvas=list(CANVAS), frame_box=[round(c, 2) for c in FRAME_BOX], camera=cams[fid],
                           method="analytic projection of the 3D lines; 'samples' are [x, y, seen] in canvas px, seen = the depth pass agrees",
                           lines=lock_target(cam, depth, kid)), open(os.path.join(out, f"{kid}-lock-target.json"), "w"), indent=1)
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr["runtime_s"], "s", flush=True)
    cam = S["cam"]
    ref = "K-boy-plate" if "K-boy-plate" in frames else frames[0]
    Cb = CAMS["boy"]
    bh.set_view(cam, Cb["loc"], Cb["yaw"], Cb["u0"], Cb["v0"])          # the reference points are on the boy's east wall
    rep["post"] = tone_frames(frames, cam, ref, out, fixed=prev.get("post") if prev else None)
    for fid in frames:
        rep["frames"][fid]["readings"] = readings(os.path.join(out, f"{fid}.png"), os.path.join(out, f"{fid}-id.png"))
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
