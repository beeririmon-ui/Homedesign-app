#!/usr/bin/env python3
"""
Framing clay, ROUND 2 (docs/proposals/house-framing.json key `round_2`, proposal 0.2, master-designer). 0 var2 credits.

One combined scene ("the house as the designer now proposes it"): approved plan 1.0
  + the round-1 picks of the four rooms that round 2 does not reframe (H-B, C-B, W-A, MB-A; their deltas from framing.py)
  + round 2 geometry for kids (G-K1r2, G-K3, G-K4, G-K5), bath (G-B1r2, G-B2r2, G-B3) and kitchen-dining (G-D2..G-D4)
  + the S11 density additions and S12 lighting additions for hall, corridor, work and master.
Every product slot is a proxy at its envelope, each slot in its own warm grey (kids: the specified paint block).
Lamps are 2700 K: emissive shade/strip + a real light source (point / area), so they light the room.

  python3 build_house.py --framing round2              # everything: 6 frames, 4 lit picks, transitions, sheet
  python3 build_house.py --framing K2-boy,B1           # selected round-2 frames (combined scene)
  python3 build_house.py --framing round2-lit          # H-B, C-B, W-A, MB-A re-rendered with the S12 lamps
  python3 build_house.py --framing round2-trans        # P-B, P-D, T-LD'' (+ alternative), T-CBath'' contact sheets
  python3 build_house.py --framing round2-sheets       # all-round2.jpg from what is on disk
Round-1 options (H-A ... B-B, framing.py) and the no-flag build are untouched.

Outputs: assets/blockout/house/framing/round2/
  <frame>.png                 2048x1152, room lamps on (S12), editorial daylight as round 1
  <pick>-lit.png              round-1 pick + S11/S12 additions, lamps on
  extra/<frame>-daylight.png  same frame, lamps off (= round-1 light), 1280 px
  extra/<frame>-alllamps.png  bath: every bath lamp incl. shower downlight + ceiling light (mandatory pass)
  extra/<frame>-sweep.jpg     5-frame contact strips for every sweep range
  extra/B2-mirror-crop.png    the mirror x2
  overlays/<frame>.png        thirds + est vs measured + heroes
  transitions/<T>-sheet.jpg   contact sheets
  all-round2.jpg              round 1 | round 2 per room / frame
  selfcheck.json              F1-F12, density per frame, mirror pass, transitions
"""
import copy
import json
import math
import os
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import build_house as bh
import framing as fr

ba, bs, b4 = bh.ba, bh.bs, bh.b4
M = ba.M
P = bs.proj
HERE = bh.HERE
REPO = bh.REPO
R1 = os.path.join(HERE, "framing")                 # round-1 outputs (read only)
OUT = os.environ.get("FRAMING_R2_OUT") or os.path.join(R1, "round2")
FX, FY = 24.0 / 36.0, 24.0 / 20.25          # focal / sensor (the plan's 0.6667 and 1.1852)

FRAMES = ["K2-boy", "K2-girl", "B1", "B2", "D1", "D2"]
FRAME_ROOM = {"K2-boy": "boy", "K2-girl": "girl", "B1": "bath", "B2": "bath", "D1": "kitchen-dining", "D2": "kitchen-dining"}
PICKS = ["H-B", "C-B", "W-A", "MB-A"]
PICK_ROOM = {"H-B": "hall", "C-B": "corridor", "W-A": "work", "MB-A": "master"}
ROUND1_IMG = {"K2-boy": "K-A-boy", "K2-girl": "K-A-girl", "B1": "B-A", "B2": "B-B", "D1": "D-A", "D2": "D-A"}
DENSITY_MIN = {"D1": 14, "D2": 14, "MB-A": 14, "H-B": 11, "W-A": 11, "K2-boy": 11, "K2-girl": 11, "B1": 11, "B2": 11,
               "C-B": 5}
DENSITY_TARGET = {"full": (15, 18), "lean": (12, 15), "transit": (5, 7)}
FRAME_KIND = {"D1": "full", "D2": "full", "MB-A": "full", "H-B": "lean", "W-A": "lean", "K2-boy": "lean",
              "K2-girl": "lean", "B1": "lean", "B2": "lean", "C-B": "transit"}

WARM = fr.WARM
GLOW = 6.0               # emissive shade strength (lamp on)
GLOW_LED = 14.0          # LED strips / opal discs

# ---------------------------------------------------------------------------------------------------------------
# materials: one warm grey per slot (distinct), lamp shades warm grey when off
# ---------------------------------------------------------------------------------------------------------------
WARM_GREYS = ["#D8CFC3", "#B9AE9F", "#CEC4B6", "#A79C8E", "#E2DACE", "#B3A898", "#C6BCAE", "#9D9387",
              "#D3C8B8", "#AEA393", "#DCD4C9", "#A2978A", "#C2B8AA", "#E7E0D5", "#958B80", "#CABFAF",
              "#BDB2A3", "#D0C6BA", "#ABA092", "#E0D7CB", "#B6AB9C", "#C9C0B4", "#A09588", "#D6CDBF"]
_mat_k = {}


def slot_mat(room, slot):
    """Distinct warm grey per slot: walks the list per room so neighbouring slots differ."""
    key = f"{room}/{slot}"
    if key not in _mat_k:
        n = sum(1 for k in _mat_k if k.split("/")[0] == room)
        col = WARM_GREYS[(n * 7 + len(room)) % len(WARM_GREYS)]
        _mat_k[key] = fr.mat_cache("wg_" + key.replace("/", "_"), col, 0.85)
    return _mat_k[key]


def named_mat(name, hexcol, rough=0.9):
    return fr.mat_cache(name, hexcol, rough)


_em = {}


def glow_mat(strength):
    k = round(strength, 2)
    if k not in _em:
        _em[k] = fr.emission_mat(f"glow2700_{k}", WARM, strength)
    return _em[k]


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------------------
def kill_objs(objs):
    n = 0
    for o in objs:
        try:
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
        except ReferenceError:
            pass
    return n


def bx(n, x0, x1, y0, y1, z0, z1, mat, bevel=0.0, group="framing"):
    return bs.box(n, x0, x1, y0, y1, z0, z1, mat, group, bevel=bevel)


def cyl(n, c, r, z0, z1, mat, verts=40, group="framing"):
    return bs.cone(n, c[0], c[1], z0, z1, r, r, mat, group, verts=verts)


def cone(n, c, r0, r1, z0, z1, mat, verts=40, group="framing"):
    return bs.cone(n, c[0], c[1], z0, z1, r0, r1, mat, group, verts=verts)


def ell(n, c, r, z0, z1, mat, group="framing"):
    return ba.ellipsoid(n, c, r, z0, z1, mat, group)


def obox(name, a, b, wvec, w, t, mat, group="framing"):
    """Box from point a to point b (length axis), width w along wvec (orthogonalised), thickness t."""
    a, b = Vector(a), Vector(b)
    z = b - a
    L = z.length
    z.normalize()
    x = Vector(wvec)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    ob = bs.box(name, -w / 2, w / 2, -t / 2, t / 2, -L / 2, L / 2, mat, group)
    R = Matrix((x, y, z)).transposed()
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = R.to_quaternion()
    ob.location = (a + b) / 2
    return ob


def reg(name, objs, room, kind="proxy"):
    return fr.reg(name, [o for o in objs if o is not None], room, kind)


# ---------------------------------------------------------------------------------------------------------------
# lamps
# ---------------------------------------------------------------------------------------------------------------
LAMPS = {}     # key -> dict(room, typ, glow=[(obj, strength)], lights=[obj], orig={name: mat}, label, shell)


def mk_light(name, kind, loc, energy, size=0.05, size_y=None, aim=(0, 0, -1), long_axis=(0, 1, 0), shape="DISK"):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = WARM
    if kind == "POINT":
        ld.shadow_soft_size = size
    elif kind == "AREA":
        ld.shape = shape
        ld.size = size
        if size_y is not None:
            ld.size_y = size_y
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if kind == "AREA":
        z = -Vector(aim).normalized()
        y = Vector(long_axis)
        y = (y - z * y.dot(z)).normalized()
        x = y.cross(z)
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Matrix((x, y, z)).transposed().to_quaternion()
    ob.visible_camera = False
    ob.visible_glossy = False
    bs.coll("lamps2700").objects.link(ob)
    ob.hide_render = True
    return ob


def lamp(key, room, typ, glow, lights, label, shell=False):
    """glow: [(obj, strength)]; typ: ceiling / wall / task / cabinet / floor."""
    glow = [(o, s) for o, s in glow if o is not None]
    LAMPS[key] = dict(room=room, typ=typ, glow=glow, lights=lights, label=label, shell=shell,
                      orig={o.name: (o.data.materials[0] if o.data.materials else None) for o, _ in glow})


def lamps_set(keys):
    on = set(keys)
    for k, L in LAMPS.items():
        for o, s in L["glow"]:
            try:
                o.data.materials.clear()
                o.data.materials.append(glow_mat(s) if k in on else L["orig"][o.name])
            except ReferenceError:
                pass
        for li in L["lights"]:
            li.hide_render = k not in on
    return sorted(on & set(LAMPS))


ROOM_LAMPS = {        # S12 "lit in frame" per room (both frames of a two-frame room share the state: one pan)
    "boy": ["boy/pendant", "boy/wall-sconce"],
    "girl": ["girl/pendant", "girl/wall-sconce"],
    "bath": ["bath/wall-sconce", "bath/vanity-sconces"],
    "bath-all": ["bath/wall-sconce", "bath/vanity-sconces", "bath/shower-downlight", "bath/ceiling-light"],
    "kitchen-dining": ["kitchen-dining/dining-pendant", "kitchen-dining/kitchen-sconce", "kitchen-dining/led-shelves",
                       "kitchen-dining/led-niche"],
    "hall": ["hall/table-lamp", "hall/wall-sconce"],
    "corridor": ["corridor/ceiling-lights", "corridor/picture-lights"],
    "work": ["work/pendant", "work/wall-sconce", "work/desk-lamp"],
    "master": ["master/bedside-sconces", "master/floor-lamp"],
}
FRAME_LAMPS = {       # lamps the proposal lists as lit AND visible in each frame (F11)
    "K2-boy": ["boy/pendant", "boy/wall-sconce"], "K2-girl": ["girl/pendant", "girl/wall-sconce"],
    "B1": ["bath/wall-sconce"], "B2": ["bath/vanity-sconces"],
    "D1": ["kitchen-dining/dining-pendant", "kitchen-dining/kitchen-sconce", "kitchen-dining/led-shelves"],
    "D2": ["kitchen-dining/kitchen-sconce", "kitchen-dining/led-shelves", "kitchen-dining/led-niche"],
    "H-B": ["hall/table-lamp", "hall/wall-sconce"], "C-B": ["corridor/ceiling-lights", "corridor/picture-lights"],
    "W-A": ["work/pendant", "work/wall-sconce", "work/desk-lamp"], "MB-A": ["master/bedside-sconces", "master/floor-lamp"],
}
LAMP_POWER_NOTE = ("2700 K (linear RGB %s). Shades: emission %.0f; LED strips / opal discs: emission %.0f. Light sources "
                   "(W, Blender radiometric): pendants 30-60 (disc under the shade), sconces 12-20 (point in front of the "
                   "shade), LED profiles 12 W/m (rectangle under the shelf), niche 5, floor lamp 30+12, "
                   "picture lights 8 each; bath ceiling light 18, shower downlight 12. Set by eye for a readable warm pool without clipping; not photometric." % (str(WARM), GLOW, GLOW_LED))


# ---------------------------------------------------------------------------------------------------------------
# plan patch (round 2 window) and the combined scene
# ---------------------------------------------------------------------------------------------------------------
def patch_plan_r2(plan0):
    D = set()
    for o in PICKS:
        D |= set(fr.OPTIONS[o]["deltas"])
    p = fr.patch_plan(plan0, D)
    w = next(w for w in p["windows"] if w["id"] == "W-bath")
    w.update(x=[3.45, 4.25], sill=1.00, head=2.15)             # G-B1r2
    return p


def kill_room(S, rooms):
    """Remove the plan proxies and plan fixed furniture of the rebuilt rooms (round 2 replaces them)."""
    n = 0
    for k in list(S["prox"]):
        if S["prox"][k]["room"] in rooms:
            n += kill_objs(S["prox"][k]["objs"])
            del S["prox"][k]
    for k in list(S["fur"]):
        if S["fur"][k]["room"] in rooms:
            n += kill_objs(S["fur"][k]["parts"])
            del S["fur"][k]
    return n


def build_r2(plan0, cfg, a):
    fr.REG.clear()
    fr.NEW_IDX = 300
    LAMPS.clear()
    _mat_k.clear()
    _em.clear()
    plan = patch_plan_r2(plan0)
    S = bh.build_scene(cfg, plan, a)
    sc = bpy.context.scene
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    notes = {}
    for o in PICKS:                       # round-1 picks: their own deltas, exactly as framing.py builds them
        notes[o] = fr.build_option(o, plan)
    kill_room(S, ("boy", "girl", "bath", "kitchen-dining"))
    for kid, dy in (("boy", 0.0), ("girl", 3.63)):
        notes[kid] = build_kids(kid, dy)
    notes["bath"] = build_bath(plan)
    notes["kitchen-dining"] = build_kitchen()
    notes["additions"] = build_additions(S)
    wl = fr.window_lights(plan)
    lamps_set([])
    bpy.context.view_layer.update()
    return S, plan, notes, wl


# ---------------------------------------------------------------------------------------------------------------
# kids (G-K1r2, G-K3, G-K4, G-K5) -- boy, girl = +3.63 in Y
# ---------------------------------------------------------------------------------------------------------------
def build_kids(kid, dy):
    notes = []
    W = M["wood"]
    oak = fr.mat_cache("oak_lining", "#CBBBA5")
    y0 = 10.25 + dy                       # east wall face
    R = ((-2.30, 1.55), (y0, 13.73 + dy))
    paint_hex = "#A7B09A" if kid == "boy" else "#E8D5CC"
    paint = named_mat(f"paint_{kid}", paint_hex, 0.9)
    # wardrobes on the west wall (from G-K1; behind the camera)
    yw = 13.73 + dy
    reg(f"{kid} wardrobes (west wall)", [bx(f"{kid}_wr2", -2.30, 0.20, yw - 0.60, yw, 0.0, 2.40, M["kit"])], kid, "furniture")
    # G-K4 colour block: 1 mm paint layer 1 mm proud of the east and north walls, Z 0-1.25, crisp line; skirting painted
    pl = []
    pl.append(bx(f"{kid}_paintE", -2.2995, 1.549, y0 + 0.0005, y0 + 0.0015, 0.149, 1.25, paint))
    pl.append(bx(f"{kid}_paintN_a", -2.2985, -2.2975, y0 + 0.001, 10.75 + dy, 0.149, 1.25, paint))
    pl.append(bx(f"{kid}_paintN_b", -2.2985, -2.2975, 10.74 + dy, 12.16 + dy, 0.149, 0.724, paint))
    pl.append(bx(f"{kid}_paintN_c", -2.2985, -2.2975, 12.15 + dy, 13.73 + dy - 0.001, 0.149, 1.25, paint))
    for p in pl:
        p.pass_index = bh.IDX["wall"]
    for ob in bpy.data.objects:
        if ob.name.startswith(f"{kid}_skirt_x0") or ob.name.startswith(f"{kid}_skirt_y0"):
            ob.data.materials.clear()
            ob.data.materials.append(paint)
    notes.append(f"G-K4: paint {paint_hex} as a 1 mm layer 1 mm in front of the east (Y {y0:.2f}) and north (X -2.30) walls, "
                 "Z 0.149-1.25 (under the window only to 0.724, below the sill board); skirting of those two walls in the paint colour")
    # fixed bed 96x196, head on the north wall, boards <= 0.60 (G-K1r2)
    bx0, bx1, by0, by1 = -2.26, -0.30, y0, y0 + 0.96
    bed = [bx(f"{kid}_b2_head", bx0, bx0 + 0.04, by0, by1, 0.0, 0.60, oak, 0.006),
           bx(f"{kid}_b2_foot", bx1 - 0.04, bx1, by0, by1, 0.0, 0.60, oak, 0.006),
           bx(f"{kid}_b2_railR", bx0 + 0.04, bx1 - 0.04, by1 - 0.04, by1, 0.12, 0.36, oak, 0.004),
           bx(f"{kid}_b2_railW", bx0 + 0.04, bx1 - 0.04, by0 + 0.002, by0 + 0.04, 0.12, 0.36, oak),
           bx(f"{kid}_b2_slats", bx0 + 0.04, bx1 - 0.04, by0 + 0.04, by1 - 0.04, 0.20, 0.235, W),
           bx(f"{kid}_b2_matt", bx0 + 0.05, bx1 - 0.05, by0 + 0.05, by1 - 0.05, 0.235, 0.42, M["bed"], 0.03)]
    reg(f"{kid} bed 96x196 (fixed)", bed, kid, "furniture")
    # fixed desk 90x50x70 (G-K3)
    reg(f"{kid} desk 90x50 (fixed)", bh._legs_table(f"{kid}_desk2", 0.10, 1.00, y0, y0 + 0.50, 0.70, oak, leg=0.04, inset=0.03),
        kid, "furniture")
    # --- 15 slots --------------------------------------------------------------------------------------------
    sm = lambda s: slot_mat(kid, s)
    # roman blind inside the reveal, raised to bottom Z 1.85 (3 folds)
    rb = [bx(f"{kid}_blind", -2.43, -2.39, 10.77 + dy, 12.13 + dy, 1.95, 2.69, sm("roman-blind"))]
    for i, z in enumerate((1.85, 1.97, 2.09)):
        rb.append(bx(f"{kid}_blindf{i}", -2.41, -2.355, 10.775 + dy, 12.125 + dy, z, z + 0.11, sm("roman-blind"), 0.02))
    reg(f"{kid}/roman-blind", rb, kid)
    # bedding: duvet + pillow; bedspread folded over the foot third; cushions 2 + 1 on the east wall at the head
    reg(f"{kid}/bedding", [bx(f"{kid}_duv", -1.86, -0.355, by0 + 0.045, by1 - 0.035, 0.42, 0.50, sm("bedding"), 0.02),
                           bx(f"{kid}_duvhang", -1.86, -0.355, by1 - 0.06, by1 + 0.025, 0.30, 0.50, sm("bedding"), 0.015),
                           bx(f"{kid}_pillow", -2.19, -1.88, by0 + 0.12, by1 - 0.10, 0.42, 0.55, sm("bedding"), 0.04)], kid)
    reg(f"{kid}/bedspread", [bx(f"{kid}_spread", -0.93, -0.36, by0 + 0.03, by1 - 0.02, 0.50, 0.545, sm("bedspread"), 0.012),
                             bx(f"{kid}_spreadhang", -0.93, -0.36, by1 - 0.035, by1 + 0.04, 0.33, 0.545, sm("bedspread"), 0.01)], kid)
    reg(f"{kid}/cushions", [bx(f"{kid}_cu1", -2.17, -1.77, by0 + 0.03, by0 + 0.16, 0.50, 0.88, sm("cushions"), 0.04),
                            bx(f"{kid}_cu2", -1.80, -1.42, by0 + 0.035, by0 + 0.165, 0.50, 0.86, sm("cushions"), 0.04),
                            bx(f"{kid}_cu3", -1.99, -1.67, by0 + 0.15, by0 + 0.27, 0.50, 0.76, sm("cushions"), 0.035)], kid)
    st = sm("soft-toy")
    reg(f"{kid}/soft-toy", [cyl(f"{kid}_toyb", (-2.02, by1 - 0.20), 0.085, 0.53, 0.72, st),
                            ell(f"{kid}_toyh", (-2.02, by1 - 0.20), 0.075, 0.71, 0.86, st)], kid)
    # pendant (G-K5 ceiling point), shade bottom 1.45, d 28
    pc = (-1.94, 10.54 + dy)
    pend_shade = cone(f"{kid}_pshade", pc, 0.14, 0.07, 1.45, 1.66, sm("pendant"))
    reg(f"{kid}/pendant", [pend_shade, cyl(f"{kid}_pcord", pc, 0.005, 1.66, 3.0, M["holder"], 12)], kid)
    lamp(f"{kid}/pendant", kid, "ceiling", [(pend_shade, GLOW)],
         [mk_light(f"{kid}_pend_L", "AREA", (pc[0], pc[1], 1.445), 30.0, size=0.20)], "pendant (ceiling point, window corner)")
    # swing-arm wall sconce (G-K5 wall point), arm 0.37 over the desk
    wpt = (0.20, y0, 1.25)
    sc_shade = cone(f"{kid}_sshade", (0.20, y0 + 0.39), 0.075, 0.04, 1.17, 1.31, sm("wall-sconce"))
    reg(f"{kid}/wall-sconce", [bx(f"{kid}_splate", 0.155, 0.245, y0, y0 + 0.02, 1.205, 1.295, M["holder"]),
                               obox(f"{kid}_sarm", (0.20, y0 + 0.02, 1.25), (0.20, y0 + 0.37, 1.31), (1, 0, 0), 0.015, 0.015, M["holder"]),
                               sc_shade], kid)
    lamp(f"{kid}/wall-sconce", kid, "wall", [(sc_shade, GLOW)],
         [mk_light(f"{kid}_sconce_L", "AREA", (0.20, y0 + 0.39, 1.165), 14.0, size=0.12)], "swing-arm sconce over the desk")
    # bookshelf: 2 ledges X -1.25..-0.45 at Z 1.25 and 1.58, books face-out (filler)
    bk = sm("bookshelf")
    books = []
    for i, z in enumerate((1.25, 1.58)):
        books.append(bx(f"{kid}_ledge{i}", -1.25, -0.45, y0, y0 + 0.10, z - 0.022, z, oak))
        books.append(bx(f"{kid}_lip{i}", -1.25, -0.45, y0 + 0.088, y0 + 0.10, z, z + 0.035, oak))
        for j, (xa, w, h) in enumerate(((-1.20, 0.19, 0.25), (-0.99, 0.21, 0.28), (-0.76, 0.18, 0.22), (-0.66, 0.17, 0.24))):
            if i == 1 and j == 3:
                continue
            books.append(obox(f"{kid}_book{i}{j}", (xa + w / 2, y0 + 0.07, z + 0.002), (xa + w / 2, y0 + 0.012 + 0.003 * j, z + h),
                              (1, 0, 0), w, 0.012, bk))
    reg(f"{kid}/bookshelf", books, kid)
    # framed prints: pair of 30x40 portrait, centred on X 0.70 (plan range X 0.45-0.95 cannot hold two 30 cm frames), Z 1.42-1.82
    reg(f"{kid}/framed-prints", [bx(f"{kid}_pr{i}", xa, xa + 0.30, y0 + 0.002, y0 + 0.025, 1.42, 1.82, sm("framed-prints"))
                                 for i, xa in enumerate((0.38, 0.72))], kid)
    notes.append("framed-prints: two 30x40 portrait frames (the slot format) do not fit the plan range X 0.45-0.95 (0.50 m); "
                 "kept the format and centred the pair on X 0.70 with a 4 cm gap: X 0.38-0.68 / 0.72-1.02, Z 1.42-1.82 "
                 "(top matches the est v 0.055)")
    # desk chair, back to camera, kid scale (seat 0.42, back top 0.72 = est back_top_v 0.62)
    ch = sm("desk-chair")
    cx, cy, s = 0.55, 11.00 + dy, 0.19
    chair = [bx(f"{kid}_chs", cx - s, cx + s, cy - s, cy + s, 0.40, 0.43, ch, 0.004),
             bx(f"{kid}_chb", cx - s, cx + s, cy + s - 0.025, cy + s, 0.43, 0.72, ch, 0.004)]
    for ix, lx in enumerate((cx - s + 0.01, cx + s - 0.04)):
        for iy, ly in enumerate((cy - s + 0.01, cy + s - 0.04)):
            chair.append(bx(f"{kid}_chl{ix}{iy}", lx, lx + 0.03, ly, ly + 0.03, 0.0, 0.40, ch))
    reg(f"{kid}/desk-chair", chair, kid)
    do = sm("desk-organizer")
    reg(f"{kid}/desk-organizer", [cyl(f"{kid}_pcup", (0.89, y0 + 0.11), 0.04, 0.70, 0.80, do),
                                  bx(f"{kid}_dtray", 0.70, 0.84, y0 + 0.05, y0 + 0.17, 0.70, 0.716, do),
                                  cyl(f"{kid}_pencils", (0.89, y0 + 0.11), 0.028, 0.80, 0.88, do, 12)], kid)
    # rug 140x200 under the bed foot; toy basket on the rug (+ filler)
    reg(f"{kid}/rug", [bx(f"{kid}_rug2", -1.50, 0.50, 10.95 + dy, 12.35 + dy, 0.0, 0.012, sm("rug"))], kid)
    tb = sm("toy-basket")
    tb_objs = [cyl(f"{kid}_tbask", (-0.70, 11.45 + dy), 0.175, 0.013, 0.36, tb)]
    if kid == "boy":
        tb_objs.append(ell("boy_football", (-0.66, 11.47 + dy), 0.11, 0.25, 0.47, tb))
    else:
        for i, (ox, oy, r) in enumerate(((-0.75, 11.42, 0.07), (-0.63, 11.50, 0.065), (-0.70, 11.55, 0.06))):
            tb_objs.append(ell(f"girl_knit{i}", (ox, oy + dy), r, 0.33, 0.33 + 2 * r, tb))
    reg(f"{kid}/toy-basket", tb_objs, kid)
    if kid == "boy":
        tc = sm("toy-cars")
        reg("boy/toy-cars", [bx("boy_car0", 0.18, 0.30, y0 + 0.14, y0 + 0.20, 0.70, 0.755, tc, 0.01),
                             bx("boy_car1", 0.31, 0.43, y0 + 0.20, y0 + 0.26, 0.70, 0.75, tc, 0.01),
                             bx("boy_car2", 0.34, 0.46, y0 + 0.09, y0 + 0.15, 0.70, 0.76, tc, 0.01)], kid)
        sk = sm("skateboard")
        # natural deck leaning on the desk's front-left edge, nose up, in front of the front-left leg (decisive overlap)
        deck = obox("boy_deck", (0.22, y0 + 0.74, 0.03), (0.22, y0 + 0.46, 0.81), (1, 0, 0), 0.20, 0.013, sk)
        wheels = [obox("boy_truck", (0.22, y0 + 0.76, 0.03), (0.22, y0 + 0.745, 0.075), (1, 0, 0), 0.17, 0.05, M["holder"])]
        reg("boy/skateboard", [deck] + wheels, kid)
    else:
        dl = sm("doll")
        reg("girl/doll", [cyl("girl_dollb", (0.30, y0 + 0.07), 0.055, 0.70, 0.86, dl),
                          ell("girl_dollh", (0.30, y0 + 0.07), 0.05, 0.855, 0.955, dl),
                          bx("girl_dolll", 0.26, 0.34, y0 + 0.08, y0 + 0.20, 0.70, 0.735, dl, 0.01)], kid)
        pr = sm("doll-pram")
        reg("girl/doll-pram", [bx("girl_pram", -0.12, 0.28, y0 + 0.62, y0 + 0.88, 0.16, 0.42, pr, 0.03),
                               bx("girl_pramw0", -0.10, -0.08, y0 + 0.60, y0 + 0.90, 0.0, 0.16, pr),
                               bx("girl_pramw1", 0.24, 0.26, y0 + 0.60, y0 + 0.90, 0.0, 0.16, pr),
                               obox("girl_pramh", (-0.12, y0 + 0.75, 0.40), (-0.24, y0 + 0.75, 0.64), (0, 1, 0), 0.24, 0.02, pr),
                               bx("girl_pramfill", -0.08, 0.24, y0 + 0.65, y0 + 0.85, 0.42, 0.46, pr, 0.015)], kid)
    if kid == "boy":
        notes.append("skateboard: deck centred on X 0.22 so that, seen from K2, it sits over the desk's front-left leg (X 0.13-0.17): the "
                     "rule 'covers the leg decisively' wins over the est u 0.60-0.63 (a deck at X 0.02-0.22 projects beside the leg, "
                     "covering ~50%: tested)")
    notes.append(f"{kid}: bed boards to 0.60, mattress top 0.42 (+ duvet to 0.50); kid chair seat 0.43 / back 0.72 (the est "
                 "back_top_v 0.62 implies ~0.72); slot proxies each in their own warm grey, the paint is the only colour")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# bath (G-B1r2, G-B2r2, G-B3)
# ---------------------------------------------------------------------------------------------------------------
MIRROR_NAME = "mirror_r2"


def build_bath(plan):
    notes = []
    W = M["wood"]
    oak = fr.mat_cache("oak_lining", "#CBBBA5")
    lime = fr.mat_cache("limestone", "#DAD3C6", 0.6)
    blk = named_mat("matte_black", "#2E2C2A", 0.6)
    san = M["sanitary"]
    sm = lambda s: slot_mat("bath", s)
    # fluted glazing in the new window (outer plane, as round 1)
    w = next(w for w in plan["windows"] if w["id"] == "W-bath")
    reg("bath fluted glazing", [bx("fluted_glass2", w["x"][0], w["x"][1], 9.62, 9.63, w["sill"], w["head"], fr.fluted_mat())],
        "bath", "architecture")
    # WC: wall-hung bowl under the window, limestone ledge X 3.30-4.40, top 0.95, depth 0.20 (concealed cistern)
    reg("bath WC + limestone ledge (fixed)", [bx("wc_ledge", 3.30, 4.40, 9.95, 10.15, 0.0, 0.95, lime, 0.004),
                                             bx("wc_bowl", 3.67, 4.03, 10.15, 10.69, 0.27, 0.41, san, 0.06),
                                             bx("wc_seat", 3.68, 4.02, 10.16, 10.68, 0.41, 0.43, san, 0.01),
                                             bx("wc_flush", 3.78, 3.92, 10.15, 10.158, 0.70, 0.80, blk)], "bath", "furniture")
    # shower corner X 5.20-6.25 x Y 9.95-11.15: limestone floor, cladding, niche cut in the south wall (boolean)
    cut = bx("niche_cutter", 6.20, 6.37, 10.30, 10.90, 1.05, 1.40, lime)
    cut.hide_render = True
    cut.hide_viewport = True
    nwall = 0
    for ob in bpy.data.objects:
        if ob.name.startswith("hwall_"):
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            xs, ys, zs = [c.x for c in bb], [c.y for c in bb], [c.z for c in bb]
            if min(xs) <= 6.26 and max(xs) >= 6.36 and min(ys) <= 10.30 and max(ys) >= 10.90 and min(zs) <= 1.05 and max(zs) >= 1.40:
                bpy.context.view_layer.update()
                bs.apply_scale(ob)
                md = ob.modifiers.new("niche", "BOOLEAN")
                md.operation = "DIFFERENCE"
                md.solver = "EXACT"
                md.object = cut
                try:
                    md.material_mode = "TRANSFER"
                except Exception:
                    pass
                nwall += 1
    notes.append(f"shower niche: boolean cut 0.12 deep into the south wall (X 6.25-6.37, Y 10.30-10.90, Z 1.05-1.40) on {nwall} wall solid(s); niche faces take the limestone material")
    t = 0.012
    cl = [bx("sh_floor", 5.20, 6.25, 9.95, 11.15, 0.0, 0.004, lime),
          bx("sh_clad_e", 5.20, 6.25 - t, 9.95, 9.95 + t, 0.004, 2.20, lime),          # east wall (Y 9.95)
          bx("sh_clad_s_a", 6.25 - t, 6.25, 9.95, 10.30, 0.004, 2.20, lime),           # south wall (X 6.25) around the niche
          bx("sh_clad_s_b", 6.25 - t, 6.25, 10.90, 11.15, 0.004, 2.20, lime),
          bx("sh_clad_s_c", 6.25 - t, 6.25, 10.2999, 10.9001, 0.004, 1.05, lime),
          bx("sh_clad_s_d", 6.25 - t, 6.25, 10.2999, 10.9001, 1.40, 2.20, lime)]
    for o in cl:
        o.pass_index = bh.IDX["wall"]
    reg("shower limestone (shell)", cl, "bath", "architecture")
    for o in cl:
        o.pass_index = bh.IDX["wall"]
    reg("shower fittings, matte black (shell)", [obox("sh_arm", (6.25, 10.60, 2.15), (5.92, 10.60, 2.15), (0, 1, 0), 0.02, 0.02, blk),
                                                cyl("sh_head", (5.92, 10.60), 0.11, 2.10, 2.12, blk),
                                                bx("sh_mixer", 6.19, 6.238, 10.55, 10.65, 0.92, 1.00, blk),
                                                bx("track_x520", 5.19, 5.21, 9.95, 11.16, 2.665, 2.69, blk),
                                                bx("track_y1115", 5.19, 6.25, 11.14, 11.16, 2.667, 2.688, blk)], "bath", "architecture")
    # shower downlight (shell) + ceiling flush light (S12 product, seen in transit only)
    dl = cyl("sh_downlight", (5.72, 10.55), 0.045, 2.693, 2.699, named_mat("downlight_off", "#E9E5DF"))
    reg("shower downlight (shell)", [dl], "bath", "architecture")
    lamp("bath/shower-downlight", "bath", "ceiling", [(dl, GLOW_LED)],
         [mk_light("sh_down_L", "AREA", (5.72, 10.55, 2.69), 12.0, size=0.09)], "recessed downlight in the shower (shell)", shell=True)
    cfl = cyl("bath_ceil", (4.75, 11.80), 0.15, 2.64, 2.699, sm("ceiling-light"))
    reg("bath/ceiling-light", [cfl], "bath", "proxy-transit")
    lamp("bath/ceiling-light", "bath", "ceiling", [(cfl, GLOW)],
         [mk_light("bath_ceil_L", "AREA", (4.75, 11.80, 2.635), 18.0, size=0.26)], "flush ceiling light (S12: not in frame)")
    notes.append("bath ceiling light (S12 'flush light, product, seen only in transit') placed at the room centre (4.75, 11.80); "
                 "not a B1/B2 slot, not counted")
    # vanity: single 110 x 48 oak, open shelf, limestone top, vessel basin, matte black wall tap; south wall Y 11.75-12.85
    reg("bath vanity 110 (fixed)", [bx("van2_side_a", 5.77, 6.25, 11.75, 11.78, 0.12, 0.85, oak),
                                    bx("van2_side_b", 5.77, 6.25, 12.82, 12.85, 0.12, 0.85, oak),
                                    bx("van2_drawer", 5.77, 6.25, 11.78, 12.82, 0.55, 0.85, oak),
                                    bx("van2_shelf", 5.79, 6.25, 11.78, 12.82, 0.12, 0.15, oak),
                                    bx("van2_top", 5.75, 6.25, 11.73, 12.87, 0.85, 0.88, lime, 0.003),
                                    cyl("van2_basin", (6.00, 12.30), 0.19, 0.88, 0.99, san, 48),
                                    bx("van2_tap", 6.08, 6.25, 12.29, 12.31, 1.07, 1.09, blk)], "bath", "furniture")
    # U6 mirror 100 x 80, thin oak frame, on the south wall
    mm = fr.mirror_mat()
    mir = bx(MIRROR_NAME, 6.236, 6.25, 11.815, 12.785, 1.165, 1.935, mm)
    fr_ = [bx("mir_fr_l", 6.226, 6.25, 11.80, 11.815, 1.15, 1.95, oak), bx("mir_fr_r", 6.226, 6.25, 12.785, 12.80, 1.15, 1.95, oak),
           bx("mir_fr_b", 6.226, 6.25, 11.815, 12.785, 1.15, 1.165, oak), bx("mir_fr_t", 6.226, 6.25, 11.815, 12.785, 1.935, 1.95, oak)]
    reg("U6 mirror", [mir], "bath", "mirror")
    reg("mirror oak frame", fr_, "bath", "architecture")
    # --- B1 slots ---------------------------------------------------------------------------------------------
    cs = sm("shower-curtain")
    folds = [(5.20, 11.125), (5.212, 11.07), (5.192, 11.015), (5.205, 10.965), (5.255, 11.152), (5.31, 11.162), (5.36, 11.145)]
    reg("bath/shower-curtain", [cyl(f"curt_f{i}", c, 0.036, 0.015, 2.655, cs, 20) for i, c in enumerate(folds)], "bath")
    sd = sm("shower-dispensers")
    reg("bath/shower-dispensers", [cyl(f"shd{i}", (6.29, yy), 0.034, 1.05, 1.05 + h, sd) for i, (yy, h) in
                                   enumerate(((10.47, 0.20), (10.59, 0.20), (10.71, 0.15)))], "bath")
    ss = sm("shower-stool")
    reg("bath/shower-stool", [bx("stool_top", 5.90, 6.20, 10.57, 10.87, 0.42, 0.45, ss, 0.006)] +
        [bx(f"stool_leg{i}", lx, lx + 0.03, ly, ly + 0.03, 0.004, 0.42, ss) for i, (lx, ly) in
         enumerate(((5.92, 10.59), (6.15, 10.59), (5.92, 10.82), (6.15, 10.82)))], "bath")
    reg("bath/bath-mat", [bx("bmat2", 4.75, 5.15, 10.40, 10.95, 0.0, 0.012, sm("bath-mat"))], "bath")
    tp = sm("toilet-paper-stand")
    reg("bath/toilet-paper-stand", [cyl("tps_base", (4.50, 10.07), 0.09, 0.0, 0.015, tp), cyl("tps_pole", (4.50, 10.07), 0.012, 0.015, 0.70, tp),
                                    obox("tps_roll", (4.50, 10.07, 0.58), (4.50, 10.20, 0.58), (0, 0, 1), 0.11, 0.11, tp),
                                    cyl("tps_spare", (4.50, 10.07), 0.055, 0.015, 0.125, tp)], "bath")
    reg("bath/toilet-brush", [cyl("tbrush", (4.70, 10.045), 0.045, 0.0, 0.36, sm("toilet-brush"))], "bath")
    reg("bath/bin", [cyl("pbin", (4.635, 10.29), 0.11, 0.0, 0.30, sm("bin"))], "bath")
    reg("bath/ledge-planter", [cyl("lplant_pot", (4.27, 10.06), 0.065, 0.95, 1.08, sm("ledge-planter")),
                               ell("lplant_crown", (4.27, 10.06), 0.10, 1.05, 1.34, M["crown"])], "bath")
    reg("bath/reed-diffuser", [cyl("reed_b", (4.10, 10.05), 0.035, 0.95, 1.07, sm("reed-diffuser")),
                               cone("reed_s", (4.10, 10.05), 0.008, 0.05, 1.07, 1.28, sm("reed-diffuser"), 12)], "bath")
    reg("bath/candle", [cyl("candle_v", (3.99, 10.09), 0.045, 0.95, 1.04, sm("candle"))], "bath")
    reg("bath/floor-planter", [cyl("fplant_pot", (4.95, 10.20), 0.14, 0.0, 0.34, sm("floor-planter")),
                               ell("fplant_crown", (4.95, 10.20), 0.21, 0.32, 1.08, M["crown"])], "bath")
    b1s = bx("b1_sconce", 4.64, 4.76, 9.95, 10.04, 1.60, 1.80, sm("wall-sconce"), 0.01)
    reg("bath/wall-sconce", [b1s], "bath")
    lamp("bath/wall-sconce", "bath", "wall", [(b1s, GLOW_LED)],
         [mk_light("b1_sconce_L", "POINT", (4.70, 10.10, 1.70), 18.0, size=0.06)], "B1 opal wall light between window and shower")
    # towel ladder leaning on the south wall Y 11.20-11.50, top 1.33, foot 0.24 out; towels hang from two rungs
    tl = sm("towel-ladder")
    lad = []
    for i, yy in enumerate((11.225, 11.475)):
        lad.append(obox(f"lad_rail{i}", (6.01, yy, 0.0), (6.235, yy, 1.33), (0, 1, 0), 0.035, 0.022, tl))
    for i, z in enumerate((0.38, 0.74, 1.10)):
        xr = 6.01 + 0.225 * z / 1.33
        lad.append(obox(f"lad_rung{i}", (xr, 11.205, z), (xr, 11.495, z), (0, 0, 1), 0.018, 0.018, tl))
    reg("bath/towel-ladder", lad, "bath")
    bt = sm("bath-towels")
    tw = []
    for i, z in enumerate((0.74, 1.10)):
        xr = 6.01 + 0.225 * z / 1.33
        tw.append(bx(f"btowel{i}", xr - 0.028, xr + 0.028, 11.255, 11.445, z - (0.36 if i == 0 else 0.26), z + 0.02, bt, 0.01))
    reg("bath/bath-towels", tw, "bath")
    # --- B2 slots ---------------------------------------------------------------------------------------------
    vs = []
    vlights = []
    for i, yy in enumerate((11.62, 12.98)):
        vs.append(bx(f"vsconce{i}", 6.14, 6.25, yy - 0.06, yy + 0.06, 1.55, 1.75, sm("vanity-sconces"), 0.01))
        vlights.append(mk_light(f"vsconce_L{i}", "POINT", (6.06, yy, 1.65), 13.0, size=0.05))
    reg("bath/vanity-sconces", vs, "bath")
    lamp("bath/vanity-sconces", "bath", "wall", [(o, GLOW_LED) for o in vs], vlights, "flat opal pair flanking the mirror (<= 12 cm)")
    reg("bath/soap-dispenser", [cyl("soapd", (6.07, 12.58), 0.035, 0.88, 1.06, sm("soap-dispenser"))], "bath")
    reg("bath/toothbrush-cup", [cyl("tcup", (6.12, 12.68), 0.035, 0.88, 0.98, sm("toothbrush-cup")),
                                cone("tbrushes", (6.12, 12.68), 0.012, 0.03, 0.98, 1.07, sm("toothbrush-cup"), 12)], "bath")
    reg("bath/vanity-vase", [cyl("vvase", (6.07, 12.78), 0.04, 0.88, 1.01, sm("vanity-vase")),
                             cone("vsprig", (6.07, 12.78), 0.005, 0.045, 1.01, 1.12, M["crown"], 12)], "bath")
    reg("bath/towel-ring", [cyl("tring_plate", (6.238, 12.98), 0.012, 0.92, 0.96, blk, 12),
                            obox("tring", (6.20, 12.90, 0.93), (6.20, 13.06, 0.93), (0, 0, 1), 0.012, 0.012, sm("towel-ring")),
                            obox("tring_l", (6.20, 12.90, 0.93), (6.20, 12.90, 0.78), (0, 1, 0), 0.012, 0.012, sm("towel-ring")),
                            obox("tring_r", (6.20, 13.06, 0.93), (6.20, 13.06, 0.78), (0, 1, 0), 0.012, 0.012, sm("towel-ring"))], "bath")
    reg("bath/hand-towel", [bx("htowel", 6.17, 6.225, 12.915, 13.045, 0.50, 0.915, sm("hand-towel"), 0.01)], "bath")
    reg("bath/storage-basket", [bx("sbask", 5.86, 6.20, 11.98, 12.42, 0.15, 0.38, sm("storage-basket"), 0.02)], "bath")
    notes.append("bath proxies: vase sprig kept below the mirror bottom (top 1.12 < 1.165) and the tooth-brushes at 1.07, so the "
                 "vanity group cannot reflect; towel ladder rails 0.035 x 0.022, rungs at 0.38 / 0.74 / 1.10")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# kitchen-dining (G-D2, G-D3, G-D4)
# ---------------------------------------------------------------------------------------------------------------
def build_kitchen():
    notes = []
    W = M["wood"]
    K = M["kit"]
    oak = fr.mat_cache("oak_lining", "#CBBBA5")
    blk = named_mat("matte_black", "#2E2C2A", 0.6)
    plaster = named_mat("mineral_plaster", "#ECE7DF", 0.95)
    top = M["moulding"]
    sm = lambda s: slot_mat("kitchen-dining", s)
    room = "kitchen-dining"
    # table 160x85 at (4.60, 1.65); 2 chairs window side; bench
    reg("dining table 160x85 (fixed)", bh._legs_table("dtab_r2", 3.80, 5.40, 1.225, 2.075, 0.75, W), room, "furniture")
    reg("dining chairs (fixed, window side)", bh._chair("dch_r2a", 4.10, 0.90, "+y", W) + bh._chair("dch_r2b", 4.90, 0.90, "+y", W),
        room, "furniture")
    reg("dining bench (fixed)", [bx("dbench_r2", 3.90, 5.30, 2.30, 2.65, 0.41, 0.45, W, 0.004),
                                 bx("dbench_r2l1", 3.97, 4.03, 2.33, 2.62, 0.0, 0.41, W),
                                 bx("dbench_r2l2", 5.17, 5.23, 2.33, 2.62, 0.0, 0.41, W)], room, "furniture")
    # kitchen run on the south wall (X 7.25)
    run = [bx("klow_carc", 6.63, 7.25, 0.75, 4.20, 0.10, 0.86, K), bx("klow_plinth", 6.70, 7.25, 0.75, 4.20, 0.0, 0.10, M["floor_gap"]),
           bx("klow_top", 6.60, 7.25, 0.75, 4.20, 0.86, 0.90, top, 0.003),
           bx("ksink", 6.73, 7.13, 1.05, 1.55, 0.899, 0.9008, named_mat("sink_steel", "#B7B2AA", 0.4)),
           cyl("ktap", (7.17, 1.30), 0.015, 0.90, 1.22, blk, 16), bx("ktap_spout", 6.96, 7.17, 1.29, 1.31, 1.20, 1.22, blk),
           bx("khob", 6.70, 7.20, 2.30, 2.90, 0.899, 0.9015, named_mat("hob_matte", "#2B2A29", 0.55)),
           bx("khood", 6.75, 7.25, 2.15, 3.05, 1.55, 3.00, plaster, 0.012)]
    for k, (ya, yb) in enumerate(((0.75, 2.05), (3.15, 4.20))):
        run.append(bx(f"kshelf{k}", 7.00, 7.25, ya, yb, 1.55, 1.58, oak, 0.003))
    # tall units Y 4.20-6.20 with the oak-lined coffee niche (Y 4.55-5.20, Z 0.90-1.60) and the oven (Y 5.30-5.90)
    run += [bx("ktall_a", 6.63, 7.25, 4.20, 4.55, 0.0, 2.40, K), bx("ktall_b", 6.63, 7.25, 5.20, 6.20, 0.0, 2.40, K),
            bx("ktall_c", 6.63, 7.25, 4.55, 5.20, 0.0, 0.90, K), bx("ktall_d", 6.63, 7.25, 4.55, 5.20, 1.60, 2.40, K),
            bx("kniche_back", 7.00, 7.25, 4.55, 5.20, 0.90, 1.60, oak),
            bx("kniche_s1", 6.63, 7.00, 4.55, 4.565, 0.915, 1.585, oak), bx("kniche_s2", 6.63, 7.00, 5.185, 5.20, 0.915, 1.585, oak),
            bx("kniche_top", 6.63, 7.00, 4.55, 5.20, 1.585, 1.60, oak), bx("kniche_bot", 6.63, 7.00, 4.55, 5.20, 0.90, 0.915, oak),
            bx("koven", 6.615, 6.63, 5.30, 5.90, 0.80, 1.40, named_mat("oven_glass", "#3B3936", 0.35)),
            bx("koven_bar", 6.575, 6.592, 5.33, 5.87, 1.33, 1.35, blk),
            bx("koven_bo1", 6.592, 6.615, 5.34, 5.36, 1.335, 1.345, blk), bx("koven_bo2", 6.592, 6.615, 5.84, 5.86, 1.335, 1.345, blk),
            bx("ktall_w", 3.95, 6.63, 5.58, 6.20, 0.0, 2.40, K)]
    reg("kitchen run (fixed): lower units, sink, hob, plastered hood, oak shelves, tall units, coffee niche, oven", run, room, "furniture")
    notes.append("kitchen: worktop top 0.90 (est counter v 0.48); hood X 6.75-7.25 x Y 2.15-3.05, Z 1.55-3.00; shelves X 7.00-7.25 "
                 "Z 1.55-1.58; tall units Y 4.20-6.20 to Z 2.40 (plan height) with the niche lining 1.5 cm oak; upper wall units of "
                 "the plan removed (shelves + hood replace them); plan west-wall tall run kept (X 3.95-6.63, Y 5.58-6.20): round 2 does "
                 "not mention it, so the approved plan stands")
    # LED profiles (shell) under the shelves and in the niche
    leds, ll = [], []
    for k, (ya, yb) in enumerate(((0.75, 2.05), (3.15, 4.20))):
        leds.append(bx(f"kled{k}", 7.02, 7.05, ya + 0.02, yb - 0.02, 1.5465, 1.5495, named_mat("led_off", "#E6E2DC")))
        ll.append(mk_light(f"kled_L{k}", "AREA", (7.035, (ya + yb) / 2, 1.544), 12.0 * (yb - ya), size=0.03, size_y=yb - ya - 0.04,
                           shape="RECTANGLE", long_axis=(0, 1, 0)))
    reg("under-shelf LED (shell)", leds, room, "architecture")
    lamp("kitchen-dining/led-shelves", room, "cabinet", [(o, GLOW_LED) for o in leds], ll, "LED profiles under both shelves (shell)", shell=True)
    nled = bx("kniche_led", 6.66, 6.69, 4.57, 5.18, 1.5835, 1.5848, named_mat("led_off", "#E6E2DC"))
    reg("niche LED (shell)", [nled], room, "architecture")
    lamp("kitchen-dining/led-niche", room, "cabinet", [(nled, GLOW_LED)],
         [mk_light("kniche_L", "AREA", (6.675, 4.875, 1.582), 5.0, size=0.03, size_y=0.60, shape="RECTANGLE")], "coffee-niche LED (shell)", shell=True)
    # --- D1 slots ---------------------------------------------------------------------------------------------
    pc = (4.60, 1.65)
    ps = cone("dpend_r2", pc, 0.25, 0.11, 1.50, 1.78, sm("dining-pendant"), 64)
    reg("kitchen-dining/dining-pendant", [ps, cyl("dpend_r2c", pc, 0.005, 1.78, 3.0, M["holder"], 12)], room)
    lamp("kitchen-dining/dining-pendant", room, "ceiling", [(ps, GLOW)],
         [mk_light("dpend_L", "AREA", (pc[0], pc[1], 1.495), 60.0, size=0.38)], "dining pendant d 50")
    reg("kitchen-dining/table-runner", [bx("drun_r2", 3.95, 5.25, 1.50, 1.80, 0.75, 0.754, sm("table-runner"))], room)
    reg("kitchen-dining/centerpiece-vase", [cyl("dvase_r2", pc, 0.08, 0.754, 1.04, sm("centerpiece-vase")),
                                            ell("dvase_olive", pc, 0.15, 0.98, 1.26, M["crown"])], room)
    reg("kitchen-dining/candle-holders", [cyl("dcand_r2a", (4.22, 1.61), 0.04, 0.754, 0.99, sm("candle-holders")),
                                          cyl("dcand_r2b", (4.34, 1.70), 0.04, 0.754, 0.93, sm("candle-holders"))], room)
    reg("kitchen-dining/curtains", [bx("dcurt_r2", 4.76, 4.96, 0.0, 0.12, 0.01, 2.85, sm("curtains"), 0.02),
                                    bx("drod_r2", 2.85, 5.00, 0.05, 0.07, 2.87, 2.89, M["holder"])], room)
    reg("kitchen-dining/floor-vase", [cyl("fvase_r2", (6.92, 0.24), 0.15, 0.0, 0.55, sm("floor-vase")),
                                      ell("fvase_euc", (6.92, 0.24), 0.24, 0.50, 1.32, M["crown"])], room)
    reg("kitchen-dining/bench-pad", [bx("bpad_r2", 3.92, 5.28, 2.32, 2.63, 0.45, 0.49, sm("bench-pad"), 0.012)], room)
    reg("kitchen-dining/dining-rug", [bx("drug_r2", 3.30, 5.90, 0.45, 2.85, 0.0, 0.010, sm("dining-rug"))], room)
    # --- D2 slots ---------------------------------------------------------------------------------------------
    sh = 1.58
    reg("kitchen-dining/framed-art", [obox("kart_r2", (7.15, 1.20, sh), (7.235, 1.20, sh + 0.40), (0, 1, 0), 0.30, 0.02, sm("framed-art"))], room)
    reg("kitchen-dining/open-shelf-ceramics", [cyl("kjug_r2", (7.11, 1.55), 0.06, sh, sh + 0.24, sm("open-shelf-ceramics")),
                                               cyl("kjar_r2", (7.11, 1.72), 0.045, sh, sh + 0.12, sm("open-shelf-ceramics"))], room)
    reg("kitchen-dining/tableware-set", [cyl("kplates_r2", (7.12, 3.38), 0.13, sh, sh + 0.10, sm("tableware-set")),
                                         cyl("kbowls_r2", (7.12, 3.38), 0.08, sh + 0.10, sh + 0.17, sm("tableware-set"))], room)
    reg("kitchen-dining/mug-set", [cyl(f"kmug_r2{i}", (7.10, yy), 0.042, sh, sh + 0.10, sm("mug-set")) for i, yy in
                                   enumerate((3.64, 3.74, 3.84))], room)
    reg("kitchen-dining/herb-pots", [cyl("kherb_r2a", (7.11, 4.00), 0.06, sh, sh + 0.12, sm("herb-pots")),
                                     cyl("kherb_r2b", (7.11, 4.12), 0.055, sh, sh + 0.11, sm("herb-pots")),
                                     ell("kherbs_r2", (7.11, 4.06), 0.11, sh + 0.10, sh + 0.30, M["crown"])], room)
    reg("kitchen-dining/sink-set", [bx("ksstray_r2", 7.05, 7.20, 1.64, 1.86, 0.90, 0.91, sm("sink-set")),
                                    cyl("kssoap_r2", (7.12, 1.70), 0.03, 0.91, 1.10, sm("sink-set")),
                                    cyl("ksbrush_r2", (7.12, 1.80), 0.022, 0.91, 1.08, sm("sink-set"))], room)
    reg("kitchen-dining/utensil-crock", [cyl("kcrock_r2", (7.08, 1.98), 0.065, 0.90, 1.08, sm("utensil-crock")),
                                         cone("kutens_r2", (7.08, 1.98), 0.04, 0.09, 1.08, 1.32, sm("utensil-crock"), 16)], room)
    reg("kitchen-dining/cutting-boards", [obox("kboard_r2a", (7.17, 1.97, 0.90), (7.235, 1.97, 1.36), (0, 1, 0), 0.25, 0.02, sm("cutting-boards")),
                                          obox("kboard_r2b", (7.14, 2.03, 0.90), (7.205, 2.03, 1.28), (0, 1, 0), 0.20, 0.02, sm("cutting-boards"))], room)
    reg("kitchen-dining/condiment-set", [cyl("ksalt_r2", (7.12, 3.06), 0.025, 0.90, 1.08, sm("condiment-set")),
                                         cyl("kpep_r2", (7.12, 3.13), 0.025, 0.90, 1.08, sm("condiment-set")),
                                         cyl("koil_r2", (7.12, 3.21), 0.035, 0.90, 1.12, sm("condiment-set"))], room)
    reg("kitchen-dining/bowl", [cyl("kbowl_r2", (7.07, 3.55), 0.13, 0.90, 0.98, sm("bowl")),
                                ell("kpears_r2", (7.07, 3.55), 0.10, 0.94, 1.06, sm("bowl"))], room)
    reg("kitchen-dining/paper-towel-holder", [cyl("kptb_r2", (7.12, 4.05), 0.075, 0.90, 0.91, sm("paper-towel-holder")),
                                              cyl("kptr_r2", (7.12, 4.05), 0.06, 0.91, 1.19, sm("paper-towel-holder"))], room)
    reg("kitchen-dining/canisters", [cyl(f"kcan_r2{i}", (6.82, yy), 0.06, 0.915, 0.915 + h, sm("canisters")) for i, (yy, h) in
                                     enumerate(((4.70, 0.22), (4.87, 0.18), (5.04, 0.14)))], room)
    reg("kitchen-dining/tea-towel", [bx("ktowel_r2", 6.555, 6.600, 5.48, 5.72, 1.00, 1.36, sm("tea-towel"), 0.008)], room)
    reg("kitchen-dining/kitchen-runner", [bx("krun_r2", 6.00, 6.55, 1.00, 3.80, 0.0, 0.010, sm("kitchen-runner"))], room)
    ks = cone("ksconce_r2", (7.07, 1.80), 0.085, 0.045, 1.96, 2.11, sm("kitchen-sconce"))
    reg("kitchen-dining/kitchen-sconce", [bx("ksconce_pl", 7.23, 7.25, 1.75, 1.85, 2.00, 2.10, M["holder"]),
                                          obox("ksconce_arm", (7.23, 1.80, 2.06), (7.08, 1.80, 2.10), (0, 1, 0), 0.015, 0.015, M["holder"]),
                                          ks], room)
    lamp("kitchen-dining/kitchen-sconce", room, "wall", [(ks, GLOW)],
         [mk_light("ksconce_L", "AREA", (7.07, 1.80, 1.955), 16.0, size=0.14)], "kitchen wall sconce left of the hood")
    notes.append("kitchen proxies from the round-2 slot text; heights assumed (jug 24, plates 10+7, crock 18 + utensils, boards 46/38 "
                 "leaning); D1 dining rug 2.60 x 2.40 (X 3.30-5.90, Y 0.45-2.85): size not given")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# S11 / S12 additions in the four round-1 picks (positions derived; the proposal names the place, not coordinates)
# ---------------------------------------------------------------------------------------------------------------
def find(name):
    return bpy.data.objects.get(name)


def build_additions(S):
    notes = []
    blk = M["holder"]
    # hall (H-B): wall sconce above the bench, umbrella stand, planter by the portal; console lamp lit
    sm = lambda s: slot_mat("hall", s)
    hs = bx("h_sconce_r2", 0.80, 0.89, 6.89, 7.01, 1.85, 2.03, sm("wall-sconce"), 0.01)
    reg("hall/wall-sconce", [hs], "hall")
    lamp("hall/wall-sconce", "hall", "wall", [(hs, GLOW)], [mk_light("h_sconce_L", "POINT", (0.97, 6.95, 1.94), 15.0, size=0.05)],
         "NEW sconce above the bench (H-B left strip)")
    reg("hall/umbrella-stand", [cyl("h_umb_r2", (3.42, 6.88), 0.11, 0.0, 0.50, sm("umbrella-stand")),
                                cyl("h_umbf_r2", (3.40, 6.86), 0.015, 0.50, 0.92, sm("umbrella-stand"), 12)], "hall")
    reg("hall/planter", [cyl("h_pot_r2", (2.37, 6.58), 0.12, 0.0, 0.38, sm("planter")),
                         ell("h_crown_r2", (2.37, 6.58), 0.16, 0.36, 1.32, M["crown"])], "hall")
    tl = find("h_lamp3")
    lamp("hall/table-lamp", "hall", "task", [(tl, GLOW)],
         [mk_light("h_tlamp_L", "POINT", (2.72, 6.62, 1.03), 15.0, size=0.04),
          mk_light("h_tlamp_L2", "POINT", (2.72, 6.55, 1.33), 7.0, size=0.04)], "console table lamp (existing)")
    hc = find("h_ceil")
    lamp("hall/ceiling-light", "hall", "ceiling", [(hc, GLOW)], [mk_light("h_ceil_L", "AREA", (2.20, 8.05, 2.795), 40.0, size=0.30)],
         "hall ceiling pendant (plan proxy; transit only)")
    notes.append("hall: sconce on the left wall at Y 6.95 (centre of the bench strip that H-B shows: the bench centre Y 7.15 is "
                 "u 0.04, too close to the edge), Z 1.85-2.03 because the plan's hook bar sits at 1.65-1.72; umbrella stand (3.42, 6.88) "
                 "by the right wall; planter (2.37, 6.58) between the portal casing and the console")
    # corridor (C-B): 3 picture lights over the gallery prints; the 2 plan ceiling lights lit
    sm = lambda s: slot_mat("corridor", s)
    pls, pll = [], []
    for i, a in enumerate((14.0, 14.6, 15.2)):
        pls.append(bx(f"c_pict{i}", 1.73, 1.80, a + 0.07, a + 0.33, 1.76, 1.79, sm("picture-lights"), 0.004))
        pls.append(bx(f"c_pictarm{i}", 1.70, 1.75, a + 0.19, a + 0.21, 1.78, 1.80, blk))
        pll.append(mk_light(f"c_pict_L{i}", "AREA", (1.78, a + 0.20, 1.755), 8.0, size=0.04, size_y=0.24, shape="RECTANGLE",
                            aim=(-0.45, 0, -1), long_axis=(0, 1, 0)))
    reg("corridor/picture-lights", pls, "corridor")
    lamp("corridor/picture-lights", "corridor", "wall", [(o, GLOW) for o in pls if "arm" not in o.name], pll, "NEW 3 picture lights")
    cls = [find("c_light_a"), find("c_light_b")]
    lamp("corridor/ceiling-lights", "corridor", "ceiling", [(o, GLOW) for o in cls],
         [mk_light(f"c_ceil_L{i}", "AREA", (2.40, y, 2.575), 30.0, size=0.28) for i, y in enumerate((11.70, 15.10))],
         "2 semi-flush ceiling lights (existing)")
    # work (W-A): pendant over the desk, sconce by the window, bookends, waste basket; desk lamp lit
    sm = lambda s: slot_mat("work", s)
    wp = cone("w_pend_r2", (-0.825, 6.82), 0.17, 0.07, 1.50, 1.72, sm("pendant"))
    reg("work/pendant", [wp, cyl("w_pcord_r2", (-0.825, 6.82), 0.005, 1.72, 3.0, blk, 12)], "work")
    lamp("work/pendant", "work", "ceiling", [(wp, GLOW)], [mk_light("w_pend_L", "AREA", (-0.825, 6.82, 1.495), 30.0, size=0.24)],
         "NEW pendant over the desk")
    ws = bx("w_sconce_r2", -2.30, -2.21, 6.69, 6.81, 1.60, 1.80, sm("wall-sconce"), 0.01)
    reg("work/wall-sconce", [ws], "work")
    lamp("work/wall-sconce", "work", "wall", [(ws, GLOW)], [mk_light("w_sconce_L", "POINT", (-2.14, 6.75, 1.70), 14.0, size=0.05)],
         "NEW sconce by the window")
    bk = sm("bookends")
    reg("work/bookends", [bx("w_bkend_a", -1.03, -1.00, 6.40, 6.56, 1.66, 1.82, bk), bx("w_bkend_b", -0.72, -0.69, 6.40, 6.56, 1.66, 1.82, bk),
                          bx("w_books", -0.995, -0.725, 6.39, 6.58, 1.66, 1.90, bk)], "work")
    reg("work/waste-basket", [cyl("w_waste_r2", (-0.35, 6.70), 0.12, 0.0, 0.30, sm("waste-basket"))], "work")
    dlm = find("w_lamp2")
    lamp("work/desk-lamp", "work", "task", [(dlm, GLOW)], [mk_light("w_dlamp_L", "POINT", (-0.30, 6.70, 1.08), 12.0, size=0.04)],
         "desk lamp (existing)")
    notes.append("work: pendant hook (-0.825, 6.82): over the desk front, 3 cm clear of the 1.62 shelf in plan, shade 1.50-1.72; "
                 "sconce on the north wall at Y 6.75 (the only part of the wall 'by the window' that W-A shows: Y 6.35-7.15); "
                 "bookends + books on the shelf X -1.03..-0.69; waste basket under the desk (-0.35, 6.70)")
    # master (MB-A): floor lamp in the reading corner (next to the tall planter), nightstand tray; sconces lit
    sm = lambda s: slot_mat("master", s)
    fl = cone("m_flamp_r2", (0.95, 18.25), 0.19, 0.15, 1.30, 1.58, sm("floor-lamp"))
    reg("master/floor-lamp", [fl, cyl("m_flbase_r2", (0.95, 18.25), 0.15, 0.0, 0.02, blk), cyl("m_flpole_r2", (0.95, 18.25), 0.012, 0.02, 1.30, blk, 12)],
        "master")
    lamp("master/floor-lamp", "master", "floor", [(fl, GLOW)],
         [mk_light("m_flamp_L", "AREA", (0.95, 18.25, 1.295), 30.0, size=0.28),
          mk_light("m_flamp_L2", "AREA", (0.95, 18.25, 1.585), 12.0, size=0.22, aim=(0, 0, 1))], "NEW floor lamp, reading corner")
    reg("master/nightstand-tray", [bx("m_tray_r2", -2.04, -1.72, 17.70, 17.98, 0.55, 0.565, sm("nightstand-tray"))], "master")
    ms = [find("m_sc2a"), find("m_sc2b")]
    lamp("master/bedside-sconces", "master", "wall", [(o, GLOW) for o in ms],
         [mk_light(f"m_sc_L{i}", "POINT", (x, 17.86, 1.34), 12.0, size=0.05) for i, x in enumerate((-1.875, 0.475))], "bedside sconce pair (existing)")
    mp = find("m_pend")
    lamp("master/pendant", "master", "ceiling", [(mp, GLOW)], [mk_light("m_pend_L", "AREA", (0.40, 19.66, 2.445), 40.0, size=0.4)],
         "centre pendant (plan proxy; transit only)")
    notes.append("master: floor lamp at (0.95, 18.25), shade d 38 at 1.30-1.58, next to (in front of) the tall planter: at X 1.40 "
                 "it would sit on the right frame edge (u ~1.0) like the planter; tray under the left nightstand vase")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# cameras
# ---------------------------------------------------------------------------------------------------------------
def r2_cams(prop):
    C = {}
    for c in prop["round_2"]["cameras_for_clay"]:
        C[c["id"]] = dict(c, loc=list(c["loc"]))
    return C


def set_cam(S, C):
    bh.set_view(S["cam"], C["loc"], C["yaw"], C["u0"], C["v0"])


def U(cam, x, y, z=None):
    return fr.U(cam, x, y, z)


def V(cam, x, y, z):
    return fr.V(cam, x, y, z)


def depth_of(C, x, y):
    return fr.depth_of(C, x, y)


# ---------------------------------------------------------------------------------------------------------------
# silhouettes by ray casting (BVH per pass index) -> visibility %, frame cut %, object-object tangents
# ---------------------------------------------------------------------------------------------------------------
GW, GH = 512, 288


def groups_by_pidx():
    out = {}
    for ob in bpy.data.objects:
        if ob.type == "MESH" and not ob.hide_render and ob.pass_index:
            out.setdefault(ob.pass_index, []).append(ob)
    return out


def bvh_of(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    if not polys:
        return None, verts
    return BVHTree.FromPolygons(verts, polys), verts


def cam_basis(C):
    y = math.radians(C["yaw"])
    f = Vector((-math.sin(y), -math.cos(y), 0.0))
    r = Vector((math.cos(y), -math.sin(y), 0.0))
    return f, r, Vector((0, 0, 1.0))


def uv_of_points(C, pts):
    f, r, z = cam_basis(C)
    c = Vector(C["loc"])
    out = []
    for p in pts:
        d = (p - c)
        dd = d.dot(f)
        if dd <= 0.05:
            out.append(None)
            continue
        out.append((C["u0"] + FX * d.dot(r) / dd, C["v0"] - FY * d.dot(z) / dd))
    return out


def silhouette(C, bvh, verts, ext=1.0):
    """Unoccluded silhouette of a group on the GW x GH grid, extended by `ext` frames on every side.
    Returns (mask_inframe [GH, GW] bool, n_total (incl. outside the frame))."""
    uvs = uv_of_points(C, verts)
    if any(q is None for q in uvs):
        u_lo, u_hi, v_lo, v_hi = -ext, 1 + ext, -ext, 1 + ext
    else:
        us = [q[0] for q in uvs]
        vs = [q[1] for q in uvs]
        u_lo, u_hi = max(-ext, min(us)), min(1 + ext, max(us))
        v_lo, v_hi = max(-ext, min(vs)), min(1 + ext, max(vs))
    if u_hi < u_lo or v_hi < v_lo:
        return np.zeros((GH, GW), bool), 0
    f, r, z = cam_basis(C)
    c = Vector(C["loc"])
    i0, i1 = int(math.floor(u_lo * GW)), int(math.ceil(u_hi * GW))
    j0, j1 = int(math.floor(v_lo * GH)), int(math.ceil(v_hi * GH))
    mask = np.zeros((GH, GW), bool)
    n = 0
    for j in range(j0, j1 + 1):
        v = (j + 0.5) / GH
        for i in range(i0, i1 + 1):
            u = (i + 0.5) / GW
            d = f + r * ((u - C["u0"]) / FX) + z * ((C["v0"] - v) / FY)
            hit = bvh.ray_cast(c, d.normalized(), 60.0)
            if hit[0] is not None:
                n += 1
                if 0 <= i < GW and 0 <= j < GH:
                    mask[j, i] = True
    return mask, n


def idx_grid(idx):
    H, W = idx.shape
    jj = ((np.arange(GH) + 0.5) * H / GH).astype(int)
    ii = ((np.arange(GW) + 0.5) * W / GW).astype(int)
    return idx[np.ix_(jj, ii)]


def erode(m):
    p = np.pad(m, 1)
    return p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]


def dilate(m):
    p = np.pad(m, 1)
    return p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]


def thickness(m):
    k = 0
    while m.any() and k < 200:
        m = erode(m)
        k += 1
    return 2 * k


def boundary_pts(m):
    b = m & ~erode(m)
    ys, xs = np.nonzero(b)
    return np.stack([xs, ys], 1).astype(float)


def min_dist(a, b):
    if len(a) == 0 or len(b) == 0:
        return None
    best = 1e9
    for k in range(0, len(a), 2048):
        d = ((a[k:k + 2048, None, :] - b[None, :, :]) ** 2).sum(2)
        best = min(best, float(d.min()))
    return math.sqrt(best)


def aabb(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for ob in objs:
        ev = ob.evaluated_get(dg)
        for c in ev.bound_box:
            w = ob.matrix_world @ Vector(c)
            for k in range(3):
                lo[k], hi[k] = min(lo[k], w[k]), max(hi[k], w[k])
    return lo, hi


def aabb_dist(A, B):
    d2 = 0.0
    for k in range(3):
        g = max(A[0][k] - B[1][k], B[0][k] - A[1][k], 0.0)
        d2 += g * g
    return math.sqrt(d2)


def names_by_pidx(S):
    names = {}
    for k, v in S["prox"].items():
        names[v["pidx"]] = (k, "proxy")
    for k, v in S["fur"].items():
        names[v["pidx"]] = ("fixed:" + k, "furniture")
    for k, v in fr.REG.items():
        names[v["pidx"]] = (k, v["kind"])
    for wid, w in S["house"]["windows"].items():
        names[w["pidx"]] = ("window " + wid, "window")
    names[bh.IDX["door"]] = ("door leaves", "door")
    return names


def analyse(C, S, idx, room, extra_min_area=0.002):
    """Per visible group: visible px fraction of the frame, visible % of the unoccluded silhouette, frame cut %.
    Then object-object tangents among visible items."""
    names = names_by_pidx(S)
    ig = idx_grid(idx)
    H, W = idx.shape
    groups = groups_by_pidx()
    items = {}
    for pidx, objs in groups.items():
        if pidx not in names:
            continue
        nm, kind = names[pidx]
        if kind in ("architecture",):
            continue
        px = int((idx == pidx).sum())
        if px < 0.0005 * H * W and kind != "lamp":
            continue
        bvh, verts = bvh_of(objs)
        if bvh is None:
            continue
        sil, ntot = silhouette(C, bvh, verts)
        vis = ig == pidx
        nin = int(sil.sum())
        items[pidx] = dict(name=nm, kind=kind, room=nm.split("/")[0] if "/" in nm else None, area=px / (H * W),
                           sil=sil, vis=vis, n_sil=ntot, n_sil_in=nin,
                           visible_pct=round(min(100.0, 100.0 * int(vis.sum()) / max(1, ntot)), 1),
                           cut_pct=round(100.0 * (1 - nin / max(1, ntot)), 1), aabb=aabb(objs))
    # tangents
    flags = []
    keys = [k for k, it in items.items() if it["area"] >= extra_min_area]
    pad = int(0.03 * GW)
    for a_i in range(len(keys)):
        for b_i in range(a_i + 1, len(keys)):
            A, B = items[keys[a_i]], items[keys[b_i]]
            d3 = aabb_dist(A["aabb"], B["aabb"])
            if d3 < 0.03:
                continue                      # physical contact / resting: not a compositional tangent
            ya, xa = np.nonzero(A["vis"])
            yb, xb = np.nonzero(B["vis"])
            if len(xa) == 0 or len(xb) == 0:
                continue
            if xa.min() > xb.max() + pad or xb.min() > xa.max() + pad or ya.min() > yb.max() + pad or yb.min() > ya.max() + pad:
                continue
            inter = A["sil"] & B["sil"]
            if not inter.any():
                g = min_dist(boundary_pts(A["vis"]), boundary_pts(B["vis"]))
                if g is not None and g / GW < 0.02:
                    flags.append(dict(a=A["name"], b=B["name"], kind="gap", gap=round(g / GW, 4), dist3d_m=round(d3, 3),
                                      rule="silhouettes apart by < 0.02 (kissing contours)"))
                continue
            touching = (dilate(A["vis"]) & B["vis"]).any()
            if not touching:
                continue
            th = thickness(inter) / GW
            back = B if (inter & A["vis"]).sum() >= (inter & B["vis"]).sum() else A      # the one hidden in the overlap
            cover = float(inter.sum()) / max(1, back["sil"].sum())
            if th < 0.03 and cover < 0.6:
                flags.append(dict(a=A["name"], b=B["name"], kind="overlap", overlap_thickness=round(th, 4), cover_of_back=round(cover, 3),
                                  behind=back["name"], dist3d_m=round(d3, 3), rule="overlap thinner than 0.03 and < 60% of the back item"))
    return items, flags


# ---------------------------------------------------------------------------------------------------------------
# density (S11) / lamps (F11)
# ---------------------------------------------------------------------------------------------------------------
CATEGORY = {}
for _s in ("bedding", "bedspread", "cushions", "soft-toy", "roman-blind", "rug", "curtains", "bench-pad", "table-runner",
           "dining-rug", "tea-towel", "kitchen-runner", "shower-curtain", "bath-mat", "bath-towels", "hand-towel",
           "bench-cushion", "runner-rug", "throw", "pillowcases", "towels"):
    CATEGORY[_s] = "textile"
for _s in ("pendant", "wall-sconce", "vanity-sconces", "kitchen-sconce", "dining-pendant", "table-lamp", "floor-lamp",
           "desk-lamp", "bedside-sconces", "ceiling-lights", "picture-lights", "ceiling-light", "wall-lamp", "wall-sconces"):
    CATEGORY[_s] = "lighting"
for _s in ("centerpiece-vase", "candle-holders", "open-shelf-ceramics", "tableware-set", "mug-set", "condiment-set", "bowl",
           "utensil-crock", "canisters", "vanity-vase", "toothbrush-cup", "soap-dispenser", "shower-dispensers",
           "ledge-planter", "floor-planter", "planter", "herb-pots", "console-vessel", "nightstand-vase", "reed-diffuser",
           "candle", "floor-vase", "vase", "dispenser-set"):
    CATEGORY[_s] = "ceramics/tableware"
for _s in ("bookshelf", "toy-basket", "desk-organizer", "desk-chair", "toilet-paper-stand", "toilet-brush", "bin",
           "towel-ladder", "towel-ring", "storage-basket", "shower-stool", "paper-towel-holder", "sink-set", "cutting-boards",
           "key-tray", "basket", "wall-hooks", "umbrella-stand", "magazine-holder", "shelf-boxes", "desk-tray", "bookends",
           "waste-basket", "nightstand-tray", "vanity-tray"):
    CATEGORY[_s] = "storage/function"
for _s in ("framed-prints", "framed-art", "toy-cars", "skateboard", "doll", "doll-pram", "gallery-art"):
    CATEGORY[_s] = "decor/play"
CATS4 = ["textile", "lighting", "ceramics/tableware", "storage/function"]


def density(items, room, fid):
    rows = []
    for it in items.values():
        if it["kind"] != "proxy" or it["room"] != room:
            continue
        slot = it["name"].split("/", 1)[1]
        ok_vis = it["visible_pct"] >= 50.0
        ok_area = it["area"] >= 0.005
        rows.append(dict(slot=slot, category=CATEGORY.get(slot, "other"), frame_area_pct=round(100 * it["area"], 2),
                         visible_pct=it["visible_pct"], cut_by_edge_pct=it["cut_pct"], counted=bool(ok_vis and ok_area),
                         why_not=None if ok_vis and ok_area else ("visible < 50%" if not ok_vis else "area < 0.5%")))
    rows.sort(key=lambda r: (not r["counted"], -r["frame_area_pct"]))
    n = sum(r["counted"] for r in rows)
    cats = sorted({r["category"] for r in rows if r["counted"]})
    mn = DENSITY_MIN[fid]
    tgt = DENSITY_TARGET[FRAME_KIND[fid]]
    have4 = [c for c in CATS4 if c in cats]
    n02 = sum(1 for r in rows if r["visible_pct"] >= 50.0 and r["frame_area_pct"] >= 0.2)
    n_any = sum(1 for r in rows if r["visible_pct"] >= 50.0)
    return dict(result="pass" if n >= mn and len(have4) == 4 else "fail", counted=n, minimum=mn, target=list(tgt),
                info_counted_if_area_ge_0_2pct=n02, info_counted_any_area_ge_50pct_visible=n_any,
                frame_kind=FRAME_KIND[fid], in_target=bool(tgt[0] <= n <= tgt[1]), categories=cats,
                four_categories_ok=len(have4) == 4, missing_categories=[c for c in CATS4 if c not in cats], slots=rows,
                rule="counted = own-room product proxy >= 50% visible (ray-cast silhouette incl. outside the frame) and >= 0.5% "
                     "of the frame; sets once; fillers, shell, fixed furniture, neighbouring rooms not counted")


def lamp_check(fid, idx, lit):
    H, W = idx.shape
    rows = []
    typ = set()
    for k in FRAME_LAMPS[fid]:
        L = LAMPS.get(k)
        if L is None:
            rows.append(dict(lamp=k, ok=False, why="not built"))
            continue
        px = 0
        for o, _ in L["glow"]:
            px += int((idx == o.pass_index).sum()) if o.pass_index else 0
        on = k in lit
        vis = px >= 2.5e-5 * H * W
        if on and vis:
            typ.add(L["typ"])
        rows.append(dict(lamp=k, label=L["label"], typology=L["typ"], lit=on, visible_px_group=px, visible=vis, ok=bool(on and vis)))
    others = [dict(lamp=k, typology=LAMPS[k]["typ"]) for k in lit if k not in FRAME_LAMPS[fid]]
    ok = all(r["ok"] for r in rows) and len(typ) <= 3
    return dict(result="pass" if ok else "fail", lamps=rows, typologies_lit_visible=sorted(typ), n_typologies=len(typ),
                also_on_in_the_room_not_listed_for_this_frame=others,
                cables="kids + bath: none modelled; pendant suspension cords only (hardwired). Clay cannot show plug cables",
                note="visible = the lamp's glowing part >= 60 px at 2K (2.5e-5 of the frame)")


# ---------------------------------------------------------------------------------------------------------------
# windows (S4 + S4')
# ---------------------------------------------------------------------------------------------------------------
def window_check2(cam, w):
    r = fr.window_check(cam, w)
    if not r.get("in_frame"):
        return r
    hv = r["head_v_min"]
    if hv < 0:
        ok_head = hv <= -0.05
        head_rule = "head cut by the top edge: must be >= 0.05 above it (S4')"
    else:
        ok_head = hv >= 0.03
        head_rule = "head inside: must be >= 0.03 below the top edge (S4')"
    r.update(s4p_head_ok=bool(ok_head), s4p_rule=head_rule, ok=bool(r["ok"] and ok_head))
    return r


# ---------------------------------------------------------------------------------------------------------------
# est vs measured (round_2 est values)
# ---------------------------------------------------------------------------------------------------------------
def est_rows(fid, S, cam, C, idx):
    R = []

    def add(key, est, meas, note="", tol=0.02):
        if isinstance(est, (list, tuple)) and isinstance(meas, (list, tuple)):
            dev = [None if (e is None or m is None) else bh.r4(m - e) for e, m in zip(est, meas)]
            flag = any(d is not None and abs(d) > tol for d in dev)
        elif isinstance(est, (int, float)) and isinstance(meas, (int, float)):
            dev = bh.r4(meas - est)
            flag = abs(dev) > tol
        else:
            dev, flag = None, False
        R.append(dict(key=key, est=est, measured=bh.r4(meas) if isinstance(meas, (float, list, tuple)) else meas, dev=dev,
                      flag_gt_tol=bool(flag), tol=tol, note=note))

    def bbu(name):
        b = fr.group_bbox(idx, fr.G(name))
        return (None, None) if b is None else ([bh.r4(b[0]), bh.r4(b[1])], [bh.r4(b[2]), bh.r4(b[3])])

    if fid in ("K2-boy", "K2-girl"):
        kid = FRAME_ROOM[fid]
        dy = 3.63 if kid == "girl" else 0.0
        y0 = 10.25 + dy
        ye = fr.edge_entry(C, "x", -2.30, "left")
        add("NE_corner_u", 0.303, U(cam, -2.30, y0))
        add("window_u (left edge .. west jamb)", [0.0, 0.23], [0.0, U(cam, -2.30, 10.75 + dy)])
        add("window_cut_pct", 23, round(100 * (12.15 + dy - ye) / 1.40, 1), tol=2)
        add("roman-blind bottom v (Z 1.85 at the jamb)", 0.13, V(cam, -2.30, 10.75 + dy, 1.85))
        add("bed_front_u (corners at Y front, Z 0.50)", [0.15, 0.46], [U(cam, -2.26, y0 + 0.96, 0.50), U(cam, -0.30, y0 + 0.96, 0.50)])
        add("mattress_v (bedding top 0.50 at the front: far / near corner)", [0.64, 0.73], [V(cam, -2.26, y0 + 0.96, 0.50), V(cam, -0.30, y0 + 0.96, 0.50)])
        u, v = bbu(f"{kid}/pendant")
        shade = [min(U(cam, -1.94 + 0.14 * math.cos(t), 10.54 + dy + 0.14 * math.sin(t), 1.45) for t in np.linspace(0, 6.28, 73)),
                 max(U(cam, -1.94 + 0.14 * math.cos(t), 10.54 + dy + 0.14 * math.sin(t), 1.45) for t in np.linspace(0, 6.28, 73))]
        add("pendant_u (shade rim, geometry)", [0.28, 0.33], shade)
        add("pendant_v (shade top 1.66 .. bottom 1.45, centre)", [0.22, 0.30], [V(cam, -1.94, 10.54 + dy, 1.66), V(cam, -1.94, 10.54 + dy, 1.45)])
        add("wall-sconce (plate centre) u", 0.70, U(cam, 0.20, y0, 1.25))
        add("wall-sconce (plate centre) v", 0.33, V(cam, 0.20, y0, 1.25))
        add("wall-sconce shade centre u (arm end, 0.39 out)", None, U(cam, 0.20, y0 + 0.39, 1.24), "no est; the shade sits at the arm end")
        u, v = bbu(f"{kid}/bookshelf")
        add("bookshelf_u (pixels)", [0.43, 0.56], u)
        add("bookshelf_v (pixels)", [0.15, 0.35], v)
        u, v = bbu(f"{kid}/framed-prints")
        add("framed-prints_u (pixels)", [0.75, 0.90], u, "pair X 0.38-1.02 (format kept, see build notes)")
        add("framed-prints top v", 0.055, v[0] if v else None)
        add("desk-chair back centre u", 0.73, U(cam, 0.55, 11.19 + dy, 0.72))
        add("desk-chair back top v", 0.62, V(cam, 0.55, 11.19 + dy, 0.72))
        add("desk_u (top front corners)", [0.63, 0.91], [U(cam, 0.10, y0 + 0.50, 0.70), U(cam, 1.00, y0 + 0.50, 0.70)])
        add("desk top v (front, centre)", 0.60, V(cam, 0.55, y0 + 0.50, 0.70))
        u, v = bbu(f"{kid}/toy-basket")
        add("toy-basket_u (pixels)", [0.27, 0.38], u)
        add("toy-basket_v (pixels)", [0.78, 0.96], v)
        if kid == "boy":
            u, v = bbu("boy/skateboard")
            add("skateboard_u (pixels)", [0.60, 0.63], u)
        add("paint line v (Z 1.25: corner / desk)", [0.34, 0.38], [V(cam, -2.30, y0, 1.25), V(cam, 0.55, y0, 1.25)])
        add("top_edge_on_east_wall_Z (corner)", None, fr.top_edge_Z(cam, -2.30, y0), "round 1 measured 2.54")
    elif fid == "B1":
        add("NE_corner_u (3.25, 9.95)", 0.110, U(cam, 3.25, 9.95))
        add("window_u (X 3.45 / 4.25)", [0.163, 0.353], [U(cam, 3.45, 9.95, 1.5), U(cam, 4.25, 9.95, 1.5)])
        add("window head v (Z 2.15 at the jambs)", [0.05, 0.09], [V(cam, 3.45, 9.95, 2.15), V(cam, 4.25, 9.95, 2.15)])
        add("window sill v (Z 1.00, centre)", 0.52, V(cam, 3.85, 9.95, 1.00))
        u, _ = bbu("bath WC + limestone ledge (fixed)")
        add("wc + ledge u (pixels)", [0.21, 0.33], u)
        add("sconce (4.70, 9.95, 1.70) uv", [0.44, 0.27], [U(cam, 4.70, 9.95, 1.70), V(cam, 4.70, 9.95, 1.70)])
        add("shower east wall u (X 5.20 .. corner)", [0.56, 0.70], [U(cam, 5.20, 9.95), U(cam, 6.25, 9.95)])
        add("SE_corner_u (6.25, 9.95)", 0.699, U(cam, 6.25, 9.95))
        add("shower south wall u (corner .. Y 11.15)", [0.70, 0.88], [U(cam, 6.25, 9.95), U(cam, 6.25, 11.15)])
        u, _ = bbu("bath/shower-curtain")
        add("curtain stack u (pixels)", [0.64, 0.69], u)
        add("right_edge_on_south_wall_Y", 11.65, fr.edge_entry(C, "x", 6.25, "right"), tol=0.05)
        add("floor visible from depth (m)", 2.52, FY * C["loc"][2] / (1 - C["v0"]), "formula", tol=0.03)
    elif fid == "B2":
        add("east wall visible from X (left edge on Y 9.95)", 4.92, fr.edge_entry(C, "y", 9.95, "left"), tol=0.05)
        add("SE_corner_u (6.25, 9.95)", 0.278, U(cam, 6.25, 9.95))
        add("shower south wall u (corner .. Y 11.15)", [0.28, 0.44], [U(cam, 6.25, 9.95), U(cam, 6.25, 11.15)])
        u, _ = bbu("bath/shower-curtain")
        add("curtain stack u (pixels)", [0.22, 0.27], u)
        u, _ = bbu("bath/towel-ladder")
        add("towel ladder u (pixels)", [0.43, 0.52], u)
        add("vanity sconces u (Y 11.62 / 12.98 at the wall)", [0.51, 0.87], [U(cam, 6.25, 11.62, 1.65), U(cam, 6.25, 12.98, 1.65)])
        add("vanity u (wall line Y 11.75 / 12.85)", [0.55, 0.83], [U(cam, 6.25, 11.75, 0.85), U(cam, 6.25, 12.85, 0.85)])
        add("mirror centre u", 0.672, U(cam, 6.25, 12.30, 1.55))
        add("mirror v (top 1.95 / bottom 1.15 at the centre)", [0.09, 0.46], [V(cam, 6.25, 12.30, 1.95), V(cam, 6.25, 12.30, 1.15)])
        add("towel ring u (Y 12.98)", 0.87, U(cam, 6.25, 12.98, 0.95))
    elif fid == "D1":
        add("window_u (left edge .. jamb X 4.75)", [0.0, 0.153], [0.0, U(cam, 4.75, 0.0, 1.5)])
        xe = fr.edge_entry(C, "y", 0.0, "left")
        add("window visible X (left edge meets Y 0)", [4.04, 4.75], [xe, 4.75])
        add("window cut pct", 61, round(100 * (xe - 2.95) / 1.80, 1), tol=2)
        u, _ = bbu("kitchen-dining/curtains")
        add("curtain stack u (pixels, incl. rod)", [0.15, 0.17], u)
        shade = [min(U(cam, 4.60 + 0.25 * math.cos(t), 1.65 + 0.25 * math.sin(t), 1.50) for t in np.linspace(0, 6.28, 73)),
                 max(U(cam, 4.60 + 0.25 * math.cos(t), 1.65 + 0.25 * math.sin(t), 1.50) for t in np.linspace(0, 6.28, 73))]
        add("pendant_u (shade rim, geometry)", [0.27, 0.39], shade)
        add("pendant_v (top 1.78 .. bottom 1.50, centre)", [0.10, 0.24], [V(cam, 4.60, 1.65, 1.78), V(cam, 4.60, 1.65, 1.50)])
        u, _ = bbu("dining table 160x85 (fixed)")
        add("table_top_u (pixels incl. legs)", [0.06, 0.55], u)
        tv = max(V(cam, x, y, 0.75) for x in (3.80, 5.40) for y in (1.225, 2.075))
        add("table near edge v", 0.66, tv)
        add("SE_corner_u (7.25, 0)", 0.444, U(cam, 7.25, 0.0))
        pu, _ = bbu("kitchen-dining/dining-pendant")
        add("pendant (pixels, right edge) to the corner line gap", 0.054, (U(cam, 7.25, 0.0) - pu[1]) if pu else None)
        add("floor vase on the corner line (vase u - corner u)", 0.0, U(cam, 6.92, 0.24, 0.3) - U(cam, 7.25, 0.0), tol=0.02)
        add("sink u (7.25, 1.30)", 0.57, U(cam, 7.25, 1.30, 0.9))
        add("hood u (7.25, 2.60)", 0.75, U(cam, 7.25, 2.60, 2.0))
        add("kitchen sconce uv", [0.635, 0.196], [U(cam, 7.07, 1.80, 2.03), V(cam, 7.07, 1.80, 2.03)])
        add("south wall visible to Y (right edge on X 7.25)", 3.94, fr.edge_entry(C, "x", 7.25, "right"), tol=0.05)
        u, v = bbu("dining bench (fixed)")
        add("bench_u (pixels)", [0.28, 0.63], u, "bottom v %s" % (v[1] if v else None))
        add("floor visible from depth (m)", 2.29, FY * C["loc"][2] / (1 - C["v0"]), "formula", tol=0.03)
    elif fid == "D2":
        add("SE_corner_u (7.25, 0) [out]", -0.07, U(cam, 7.25, 0.0))
        add("south wall visible from Y (left edge on X 7.25)", 0.45, fr.edge_entry(C, "x", 7.25, "left"), tol=0.05)
        u, _ = bbu("kitchen-dining/sink-set")
        add("sink group u (pixels)", [0.10, 0.18], u)
        add("hood centre u (wall line 7.25, 2.60)", 0.328, U(cam, 7.25, 2.60, 2.0))
        add("hood centre u (front face X 6.75)", None, U(cam, 6.75, 2.60, 2.0), "no est")
        add("hood top cut: top edge Z on the wall line (7.25, 2.60)", 2.71, fr.top_edge_Z(cam, 7.25, 2.60), "est 'Z 2.71 at depth 4.45'", tol=0.05)
        add("hood top cut: top edge Z at the hood front X 6.75", None, fr.top_edge_Z(cam, 6.75, 2.60), "no est; the hood box is cut where the frame top meets its front")
        add("lower units u (Y 0.75 / 4.20 at the wall)", [0.05, 0.57], [U(cam, 7.25, 0.75, 0.5), U(cam, 7.25, 4.20, 0.5)])
        add("tall units u (Y 4.20 / 6.20 at the wall)", [0.57, 0.865], [U(cam, 7.25, 4.20, 1.2), U(cam, 7.25, 6.20, 1.2)])
        add("coffee niche u (front Y 4.55 / 5.20)", [0.62, 0.72], [U(cam, 6.63, 4.55, 1.25), U(cam, 6.63, 5.20, 1.25)])
        add("coffee niche u (wall line X 7.25)", [0.62, 0.72], [U(cam, 7.25, 4.55, 1.25), U(cam, 7.25, 5.20, 1.25)], "the designer's u are wall-line values")
        add("shelves v (bottom 1.55 at the wall, Y 1.40)", 0.31, V(cam, 7.25, 1.40, 1.55))
        add("counter v (0.90 at the front edge, Y 2.60)", 0.48, V(cam, 6.60, 2.60, 0.90))
        u, _ = bbu("dining table 160x85 (fixed)")
        ub, _ = bbu("dining bench (fixed)")
        add("table + bench end u (pixels, right edge)", [0.0, 0.20], [0.0, max(u[1] if u else 0, ub[1] if ub else 0)])
    return R


HERO2 = {
    "K2-boy": [("NE corner + pendant (window corner)", (-2.30, 10.25, None), "third"), ("pendant centre", (-1.94, 10.54, 1.56), "third"),
               ("desk sconce plate (right third)", (0.20, 10.25, 1.25), "third")],
    "K2-girl": [("NE corner + pendant (window corner)", (-2.30, 13.88, None), "third"), ("pendant centre", (-1.94, 14.17, 1.56), "third"),
                ("desk sconce plate (right third)", (0.20, 13.88, 1.25), "third")],
    "B1": [("shower curtain stack (L corner 5.20, 11.15)", (5.20, 11.15, None), "third"), ("window centre (left third)", (3.85, 9.95, 1.57), "third"),
           ("WC centre", (3.85, 10.40, 0.40), "third")],
    "B2": [("mirror centre", (6.25, 12.30, 1.55), "third"), ("SE corner (left)", (6.25, 9.95, None), "third")],
    "D1": [("pendant / table centre", (4.60, 1.65, 1.64), "third"), ("table centre", (4.60, 1.65, 0.75), "third")],
    "D2": [("hood centre (pixels)", "kitchen hood", "third"), ("hood centre (wall line)", (7.25, 2.60, 2.0), "third"),
           ("coffee niche centre", (6.63, 4.875, 1.25), "third")],
}
HERO_WALL2 = {"K2-boy": (-2.30, 10.25), "K2-girl": (-2.30, 13.88), "B1": (5.72, 9.95), "B2": (6.25, 12.30), "D1": (4.60, 0.0),
              "D2": (7.25, 2.60)}
WIN_ROOM = {"boy": "W-boy", "girl": "W-girl", "bath": "W-bath", "kitchen-dining": "W-dining"}
SHELL_PIDX = fr.SHELL_PIDX


def hood_bbox_u(idx):
    """Pixel bbox of the hood only (the kitchen-run group is one pass index; hood = the run's pixels above Z 1.55 between
    the shelves: approximated by projecting the hood box)."""
    return None


def acceptance2(fid, S, cam, C, idx, depth, plan, est, items, flags):
    room = FRAME_ROOM[fid]
    H, W = idx.shape
    out = {}
    rows = []
    for lab, pt, mode in HERO2[fid]:
        if pt == "kitchen hood":
            pts = [Vector((x, y, z)) for x in (6.75, 7.25) for y in (2.15, 3.05) for z in (1.55, 3.0)]
            uvs = [P(cam, p) for p in pts]
            vis = [q for q in uvs if q[2] > 0]
            u = (max(0.0, min(q[0] for q in vis)) + min(1.0, max(q[0] for q in vis))) / 2
        else:
            x, y, z = pt
            u = U(cam, x, y, z)
        ok = 0.30 <= u <= 0.36 or 0.64 <= u <= 0.70
        rows.append(dict(hero=lab, u=bh.r4(u), rule="0.30-0.36 / 0.64-0.70", ok=bool(ok), almost_centre_0_45_0_58=bool(0.45 <= u <= 0.58)))
    out["F1"] = dict(result="pass" if rows[0]["ok"] else "fail", heroes=rows, note="result = first (named) hero; others listed")
    wins = {w["id"]: w for w in plan["windows"]}
    wr = window_check2(cam, wins[WIN_ROOM[room]])
    out["F2"] = dict(result=("n/a (no window in frame; S10 second frame)" if not wr.get("in_frame") else ("pass" if wr["ok"] else "fail")),
                     windows={WIN_ROOM[room]: wr} if wr.get("in_frame") else {})
    # F3: edge tangents (pixels), architectural lines near edges, object-object tangents (ray-cast silhouettes)
    names = names_by_pidx(S)
    tang = []
    for pidx, (nm, kind) in names.items():
        b = fr.group_bbox(idx, [pidx])
        if b is None or b[4] < 200 or kind == "architecture":
            continue
        for side, m in (("left", b[0]), ("right", 1 - b[1]), ("top", b[2]), ("bottom", 1 - b[3])):
            if 0.0 < m < 0.02:
                tang.append(dict(item=nm, side=side, margin=bh.r4(m)))
    arch = []
    for fe in est:
        k = fe["key"]
        if any(s in k for s in ("corner", "jamb", "window_u", "window head")) and not any(s in k for s in ("gap", "on the corner line", "visible")):
            vals = fe["measured"] if isinstance(fe["measured"], list) else [fe["measured"]]
            for val in vals:
                if isinstance(val, (int, float)) and val not in (0.0,) and (abs(val) < 0.02 or abs(val - 1) < 0.02):
                    arch.append(dict(line=k, value=val))
    prod_flags = [f for f in flags]
    out["F3"] = dict(result="pass" if not tang and not arch and not prod_flags else "fail", edge_tangents=tang,
                     architectural_lines_within_0_02_of_edge=arch, object_object_tangents=prod_flags,
                     note="edge: visible bbox margin 0 < m < 0.02. object-object: ray-cast silhouettes on a 512x288 grid; pairs "
                          "closer than 0.03 m in 3D (resting / touching) skipped; flagged if contours are < 0.02 apart, or overlap "
                          "by a sliver (< 0.03 thick and < 60% of the item behind). Corner-line rules are in rules_designer.")
    # F4 / F5 / F6
    hd = depth_of(C, *HERO_WALL2[fid])
    objm = ~np.isin(idx, SHELL_PIDX + [0, bh.IDX["trim"], bh.IDX["threshold"]])
    fg = objm & (depth < 0.55 * hd)
    bg = (depth > hd + 0.4) | (idx == 0)
    fgn = {}
    for pidx in np.unique(idx[fg]):
        n = int((idx[fg] == pidx).sum())
        if n > 0.002 * H * W:
            fgn[names.get(int(pidx), (f"idx {int(pidx)}",))[0]] = round(n / (H * W), 4)
    out["F4"] = dict(result="pass" if fgn and bg.mean() > 0.02 else ("weak (no foreground object)" if not fgn else "weak (no background)"),
                     hero_wall_depth_m=bh.r4(hd), foreground_objects_frac=fgn, background_frac=round(float(bg.mean()), 4),
                     note="as round 1: foreground = non-shell pixels nearer than 0.55 x hero-wall depth; background = beyond the hero wall + 0.4 m")
    lim = 2.8 if room == "bath" else 3.0
    out["F5"] = dict(result="pass" if hd >= lim - 1e-6 else "fail", camera_to_hero_wall_depth_m=bh.r4(hd), min_m=lim,
                     hero_wall_point=HERO_WALL2[fid])
    calm = np.isin(idx, SHELL_PIDX).mean()
    out["F6"] = dict(result="pass" if calm >= 0.25 else "fail", calm_wall_floor_ceiling_frac=round(float(calm), 3),
                     note="wall (incl. the kids' paint and the shower limestone), floor, ceiling pixels")
    out["F7"] = dict(result="n/a (hall and corridor only)")
    return out


def item_gap(items, na, nb):
    A = next((v for v in items.values() if v["name"] == na), None)
    B = next((v for v in items.values() if v["name"] == nb), None)
    if A is None or B is None:
        return None
    if (A["vis"] & dilate(B["vis"])).any():
        return 0.0
    g = min_dist(boundary_pts(A["vis"]), boundary_pts(B["vis"]))
    return None if g is None else round(g / GW, 4)


def designer_rules(fid, S, cam, C, idx, items):
    """The named tangent rules of round 2 (section 8.2 / 8.3 / 8.4), measured in pixels."""
    R = []

    def bb(name):
        b = fr.group_bbox(idx, fr.G(name))
        return b

    if fid in ("K2-boy", "K2-girl"):
        kid = FRAME_ROOM[fid]
        dy = 3.63 if kid == "girl" else 0.0
        pb = bb(f"{kid}/pendant")
        cu = U(cam, -2.30, 10.25 + dy, 1.55)
        if pb:
            R.append(dict(rule="corner line runs through the pendant shade", pendant_u=[bh.r4(pb[0]), bh.r4(pb[1])], corner_u=bh.r4(cu),
                          ok=bool(pb[0] + 0.005 < cu < pb[1] - 0.005)))
        # pendant vs window jamb / blind folds >= 0.02 (u at the shade height)
        wj = U(cam, -2.30, 10.75 + dy, 1.55)
        bl = bb(f"{kid}/roman-blind")
        if pb:
            R.append(dict(rule="pendant >= 0.02 from the window (west jamb line at the shade height)", gap=bh.r4(wj - pb[1]) if wj > pb[1] else bh.r4(pb[0] - wj),
                          pendant_u=[bh.r4(pb[0]), bh.r4(pb[1])], jamb_u=bh.r4(wj), ok=bool(wj >= pb[1] + 0.02 or wj <= pb[0] - 0.02)))
        g = item_gap(items, f"{kid}/pendant", f"{kid}/roman-blind")
        if g is not None:
            R.append(dict(rule="pendant >= 0.02 from the blind folds (2D silhouette gap, frame widths)", gap=g, ok=bool(g >= 0.02)))
        g = item_gap(items, f"{kid}/pendant", "window W-" + kid)
        if g is not None:
            R.append(dict(rule="pendant >= 0.02 from the window frame (2D silhouette gap)", gap=g, ok=bool(g >= 0.02)))
        tb = bb(f"{kid}/toy-basket")
        if tb:
            R.append(dict(rule="toy basket vs the bottom edge: cut, or >= 0.03 clear", bottom_v=bh.r4(tb[3]), margin=bh.r4(1 - tb[3]),
                          ok=bool(tb[3] >= 0.999 or 1 - tb[3] >= 0.03)))
        nm = "boy/skateboard" if kid == "boy" else "girl/doll-pram"
        legs = [o for o in bpy.data.objects if o.name.startswith(f"{kid}_desk2_leg")]
        if legs:
            # the front-left leg (smallest X, largest Y)
            leg = min(legs, key=lambda o: (round(o.location.x, 2), -o.location.y))
            lp = leg.pass_index
            item = items.get(fr.G(nm)[0]) if fr.G(nm) else None
            bvh, verts = bvh_of([leg])
            sil, _ = silhouette(C, bvh, verts)
            ig = idx_grid(idx)
            covered = float((sil & (ig == fr.G(nm)[0])).sum()) / max(1, sil.sum())
            R.append(dict(rule=f"{nm.split('/')[1]} covers the front-left desk leg decisively", leg=leg.name,
                          leg_silhouette_px=int(sil.sum()), covered_pct=round(100 * covered, 1), ok=bool(covered >= 0.6)))
    if fid == "B2":
        cb = bb("bath/shower-curtain")
        cu = U(cam, 6.25, 9.95, 1.15)
        if cb:
            over = cb[1] - cu
            ok = over >= 0.03 or (cu - cb[1]) >= 0.02 or (cb[0] - cu) >= 0.02
            R.append(dict(rule="curtain stack vs the SE corner line: overlap >= 0.03 or clear >= 0.02", stack_u=[bh.r4(cb[0]), bh.r4(cb[1])],
                          corner_u=bh.r4(cu), overlap=bh.r4(over), ok=bool(ok)))
        lad = bb("bath/towel-ladder")
        if lad:
            top = 1.33
            R.append(dict(rule="towel ladder top >= 0.20 below the east vanity sconce (bottom 1.55)", ladder_top_z=top, sconce_bottom_z=1.55,
                          gap_m=round(1.55 - top, 3), ok=bool(1.55 - top >= 0.20)))
    if fid == "B1":
        cb = bb("bath/shower-curtain")
        cu = U(cam, 6.25, 9.95, 1.15)
        if cb:
            R.append(dict(rule="curtain stack vs the SE corner line (B1, info)", stack_u=[bh.r4(cb[0]), bh.r4(cb[1])], corner_u=bh.r4(cu),
                          gap=bh.r4(cu - cb[1]), ok=bool(cu - cb[1] >= 0.02 or cb[1] - cu >= 0.03)))
    if fid == "D1":
        pb = bb("kitchen-dining/dining-pendant")
        cu = U(cam, 7.25, 0.0, 1.6)
        if pb:
            R.append(dict(rule="pendant vs the SE corner line >= 0.02 (est gap 0.054)", pendant_right_u=bh.r4(pb[1]), corner_u=bh.r4(cu),
                          gap=bh.r4(cu - pb[1]), ok=bool(cu - pb[1] >= 0.02)))
        fv = bb("kitchen-dining/floor-vase")
        if fv:
            R.append(dict(rule="floor vase on the corner line (line through the vase)", vase_u=[bh.r4(fv[0]), bh.r4(fv[1])], corner_u=bh.r4(cu),
                          ok=bool(fv[0] + 0.01 < cu < fv[1] - 0.01)))
        bn = bb("dining bench (fixed)")
        if bn:
            R.append(dict(rule="bench crosses the bottom edge, away from the sides", bench_u=[bh.r4(bn[0]), bh.r4(bn[1])], bottom_v=bh.r4(bn[3]),
                          ok=bool(bn[3] >= 0.999 and bn[0] >= 0.05 and bn[1] <= 0.95)))
    if fid == "D2":
        tb = bb("dining table 160x85 (fixed)")
        if tb:
            R.append(dict(rule="table + bench end cut by the left edge (foreground)", table_u=[bh.r4(tb[0]), bh.r4(tb[1])], ok=bool(tb[0] <= 0.001)))
    return R


# ---------------------------------------------------------------------------------------------------------------
# mirror (F8): one pass at CB, mirror on the south wall facing -X
# ---------------------------------------------------------------------------------------------------------------
def mirror_pass(C, cam=None, n=48):
    mirror = bpy.data.objects[MIRROR_NAME]
    dg = bpy.context.evaluated_depsgraph_get()
    bbw = [mirror.matrix_world @ Vector(c) for c in mirror.bound_box]
    y0, y1 = min(c.y for c in bbw), max(c.y for c in bbw)
    z0, z1 = min(c.z for c in bbw), max(c.z for c in bbw)
    xface = min(c.x for c in bbw) - 1e-4
    co = Vector(C["loc"])
    hits, inframe = {}, {}
    nrm = Vector((-1, 0, 0))
    for i in range(n):
        for j in range(n):
            p = Vector((xface, y0 + (y1 - y0) * (i + 0.5) / n, z0 + (z1 - z0) * (j + 0.5) / n))
            dirc = (p - co).normalized()
            ok, loc, nor, fi, ob, _ = bpy.context.scene.ray_cast(dg, co, dirc, distance=(p - co).length + 0.01)
            if not ok or ob.name != MIRROR_NAME:
                continue
            r = dirc - 2 * dirc.dot(nrm) * nrm
            ok2, loc2, _, _, ob2, _ = bpy.context.scene.ray_cast(dg, p + r * 0.002, r, distance=30)
            nm = ob2.name if ok2 else "sky"
            base = nm.split(".")[0]
            for tgt in ([hits] + ([inframe] if cam is not None and 0 <= P(cam, p)[0] <= 1 and 0 <= P(cam, p)[1] <= 1 else [])):
                tgt.setdefault(base, dict(n=0, y=[], z=[], x=[]))
                tgt[base]["n"] += 1
                if ok2:
                    tgt[base]["x"].append(loc2.x)
                    tgt[base]["y"].append(loc2.y)
                    tgt[base]["z"].append(loc2.z)

    def summ(H):
        tot = sum(h["n"] for h in H.values())
        out = {}
        for k, h in sorted(H.items(), key=lambda kv: -kv[1]["n"]):
            out[k] = dict(frac=round(h["n"] / max(1, tot), 3), x=[bh.r4(min(h["x"])), bh.r4(max(h["x"]))] if h["x"] else None,
                          y=[bh.r4(min(h["y"])), bh.r4(max(h["y"]))] if h["y"] else None,
                          z=[bh.r4(min(h["z"])), bh.r4(max(h["z"]))] if h["z"] else None)
        return tot, out
    tot, out = summ(hits)
    shell_like = lambda k: k.startswith("hwall") or k.startswith("bath_") or "skirt" in k or "sgap" in k or k.startswith("well")
    non_wall = sorted(k for k in out if not shell_like(k))
    allw = [(h["y"], h["z"]) for k, h in hits.items() if k.startswith("hwall") and h["y"]]
    r = dict(result="pass" if not non_wall else "fail", samples=tot, hits=out, non_wall_objects=non_wall,
             wall_Y_range=[bh.r4(min(min(a) for a, b in allw)), bh.r4(max(max(a) for a, b in allw))] if allw else None,
             wall_Z_range=[bh.r4(min(min(b) for a, b in allw)), bh.r4(max(max(b) for a, b in allw))] if allw else None,
             designer_est="north wall Y 10.03-12.12, Z 1.15-2.70 + a ceiling strip; door 0.27 outside, window 0.08",
             method=f"ray-cast: {n}x{n} grid on the whole mirror from CB, reflected camera rays; every object hit listed")
    if cam is not None:
        t2, o2 = summ(inframe)
        r["inside_frame"] = dict(samples=t2, hits=o2)
    return r


# ---------------------------------------------------------------------------------------------------------------
# rendering helpers
# ---------------------------------------------------------------------------------------------------------------
def render_main(path, tmp, a):
    return fr.render(path, os.path.join(tmp, "p"), a.res, a.samples, ao=0.30)


def render_quick(path, tmp, res, samples):
    fr.render(path, os.path.join(tmp, "p"), res, samples, ao=0.30, passes=False)


def sweep_strip(fid, S, C, sw, tmp, a, measure=None):
    from PIL import Image
    tiles, nums = [], []
    for key, rng in sw.items():
        if key == "constraint":
            continue
        lo, hi = rng
        for k in range(5):
            val = lo + (hi - lo) * k / 4
            c = dict(C, loc=list(C["loc"]))
            c[key] = val
            set_cam(S, c)
            fp = os.path.join(tmp, f"sw_{key}_{k}.png")
            render_quick(fp, tmp, int(640 * a.xs), max(4, int(24 * a.xs)))
            lab = f"{key} = {val:.3f}"
            if measure:
                m = measure(S["cam"], c)
                nums.append(dict({key: round(val, 3)}, **m))
                lab += "  " + "  ".join(f"{k2} {v2}" for k2, v2 in m.items())
            tiles.append((Image.open(fp).convert("RGB"), lab))
    set_cam(S, C)
    outp = os.path.join(OUT, "extra", f"{fid}-sweep.jpg")
    bh.make_sheet(tiles, f"{fid} sweep {dict((k, v) for k, v in sw.items() if k != 'constraint')} (5 frames per range, 640 px, room lamps on)", outp, cols=5)
    return dict(sheet=f"framing/round2/extra/{fid}-sweep.jpg", values=nums)


def sweep_measure(fid):
    def m(cam, c):
        if fid in ("K2-boy", "K2-girl"):
            dy = 3.63 if fid == "K2-girl" else 0.0
            return dict(corner=round(U(cam, -2.30, 10.25 + dy), 3), sconce=round(U(cam, 0.20, 10.25 + dy, 1.25), 3),
                        jamb=round(U(cam, -2.30, 10.75 + dy), 3))
        if fid == "B1":
            return dict(stack=round(U(cam, 5.20, 11.15, 1.2), 3), SE=round(U(cam, 6.25, 9.95), 3), NE=round(U(cam, 3.25, 9.95), 3))
        if fid == "B2":
            return dict(stack=round(U(cam, 5.20, 11.15, 1.2), 3), SE=round(U(cam, 6.25, 9.95), 3), mirror=round(U(cam, 6.25, 12.30, 1.55), 3))
        if fid == "D1":
            return dict(pendant=round(U(cam, 4.60, 1.65, 1.64), 3), SE=round(U(cam, 7.25, 0.0), 3),
                        pend_top_v=round(V(cam, 4.60, 1.65, 1.78), 3))
        if fid == "D2":
            return dict(hood_wall=round(U(cam, 7.25, 2.60, 2.0), 3), niche=round(U(cam, 6.63, 4.875, 1.25), 3))
        return {}
    return m


def crop_mirror(p, idx):
    from PIL import Image
    b = fr.group_bbox(idx, fr.G("U6 mirror"))
    if not b:
        return None
    im = Image.open(p)
    Wp, Hp = im.size
    pad = 0.03
    crop = im.crop((int(max(0, b[0] - pad) * Wp), int(max(0, b[2] - pad) * Hp), int(min(1, b[1] + pad) * Wp), int(min(1, b[3] + pad) * Hp)))
    crop = crop.resize((crop.width * 2, crop.height * 2))
    crop.save(os.path.join(OUT, "extra", "B2-mirror-crop.png"))
    return "framing/round2/extra/B2-mirror-crop.png"


# ---------------------------------------------------------------------------------------------------------------
# transitions
# ---------------------------------------------------------------------------------------------------------------
M0 = dict(loc=[1.25, 5.55, 1.20], yaw=25, u0=0.52, v0=0.46)
C0 = dict(loc=[2.397, 17.11, 1.20], yaw=0, u0=0.50, v0=0.46)


def trans_defs(prop, cams):
    r2 = prop["round_2"]["rooms"]
    PD, CB = cams["D1"], cams["B1"]
    T = {}
    T["P-B"] = dict(start=dict(CB, yaw=-22), segs=[dict(type="pan", yaw=[-22, -57])], end=cams["B2"],
                    play_s=r2["bath"]["transitions"]["P-B (B1<->B2)"]["play_s"], note="B1 -> B2, one pan at CB")
    T["P-D"] = dict(start=dict(PD, yaw=-56), segs=[dict(type="pan", yaw=[-56, -91])], end=cams["D2"],
                    play_s=r2["kitchen-dining"]["transitions"]["P-D (D1<->D2)"]["play_s"], note="D1 -> D2, one pan at PD")
    T["T-LD''"] = dict(start=M0, segs=[dict(type="pan", id="P0", yaw=[25, 0]), dict(type="pan", id="P1", yaw=[0, -35]),
                                       dict(type="dolly", heading=-35, frm=[1.25, 5.55, 1.20], to=[2.80, 3.80, 1.10]),
                                       dict(type="pan", id="P2", yaw=[-35, -56])], end=cams["D1"],
                       play_s=r2["kitchen-dining"]["transitions"]["T-LD''_play_s"], note="4 shots (U10 upper limit)")
    T["T-LD'' alt"] = dict(start=M0, segs=[dict(type="pan", id="P0", yaw=[25, 0]), dict(type="pan", id="P1a", yaw=[0, -28]),
                                           dict(type="pan", id="P1b", yaw=[-28, -56]),
                                           dict(type="dolly", heading=-56, frm=[1.25, 5.55, 1.20], to=[2.80, 3.80, 1.10])],
                           end=cams["D1"], play_s=None, note="designer's alternative to compare: P0 + 2 x 28 deg pans at M0 + dolly heading -56 (14.5 deg oblique)")
    T["T-CBath''"] = dict(start=C0, segs=[dict(type="dolly", heading=0, frm=[2.397, 17.11, 1.20], to=[2.641, 13.00, 1.20]),
                                          dict(type="slide", heading=0, frm=[2.641, 13.00, 1.20], to=[3.80, 13.20, 1.15]),
                                          dict(type="pan", yaw=[0, -22])], end=cams["B1"],
                          play_s=r2["bath"]["transitions"]["T-CBath''_play_s"], note="rail C0 -> S1', slide to CB, pan 0 -> -22")
    return T


def trans_poses(T, pan_step=5.0, move_step=0.25):
    st, end = T["start"], T["end"]
    x, y, z = st["loc"]
    yaw = st["yaw"]
    u0, v0 = st["u0"], st["v0"]
    poses = [dict(x=x, y=y, z=z, yaw=yaw, u0=u0, v0=v0, seg="start", s=0.0)]
    issues = []
    for si, sg in enumerate(T["segs"]):
        lab = sg.get("id", sg["type"]) + f"#{si + 1}"
        if sg["type"] == "pan":
            a0, a1 = sg["yaw"]
            if abs(a0 - yaw) > 1e-6:
                issues.append(f"{lab}: pan starts at {a0}, camera yaw {yaw}")
            n = max(1, math.ceil(abs(a1 - a0) / pan_step - 1e-9))
            for k in range(1, n + 1):
                poses.append(dict(x=x, y=y, z=z, yaw=a0 + (a1 - a0) * k / n, u0=u0, v0=v0, seg=lab, s=0.0))
            yaw = a1
            continue
        fx, fy, fz = sg["frm"]
        tx, ty, tz = sg["to"]
        if math.dist((fx, fy), (x, y)) > 0.005:
            issues.append(f"{lab}: starts at {(fx, fy)}, camera at {(round(x, 3), round(y, 3))}")
        if abs(sg["heading"] - yaw) > 1e-6:
            issues.append(f"{lab}: heading {sg['heading']} != camera yaw {yaw}")
        L = math.dist((fx, fy), (tx, ty))
        n = max(1, math.ceil(L / move_step - 1e-9))
        nu0, nv0 = end["u0"], end["v0"]
        for k in range(1, n + 1):
            t = k / n
            poses.append(dict(x=fx + (tx - fx) * t, y=fy + (ty - fy) * t, z=fz + (tz - fz) * t, yaw=yaw,
                              u0=u0 + (nu0 - u0) * t, v0=v0 + (nv0 - v0) * t, seg=lab, s=round(L * t, 3)))
        x, y, z = tx, ty, tz
        u0, v0 = nu0, nv0
    e = poses[-1]
    end_err = dict(pos_m=bh.r4(math.dist((e["x"], e["y"], e["z"]), end["loc"])), yaw_deg=bh.r4(e["yaw"] - end["yaw"]),
                   u0=bh.r4(e["u0"] - end["u0"]), v0=bh.r4(e["v0"] - end["v0"]))
    return poses, issues, end_err


def trans_check(T, plan, obs):
    opens = bh.all_openings_for_hc1(plan)
    segs = []
    for sg in T["segs"]:
        if sg["type"] == "pan":
            segs.append(dict(type="pan", id=sg.get("id"), yaw=sg["yaw"], deg=abs(sg["yaw"][1] - sg["yaw"][0])))
            continue
        a, b = sg["frm"][:2], sg["to"][:2]
        jc = bh.jamb_clearance(a, b, opens)
        d, r = bh.seg_clearance(a, b, obs)
        hd = math.degrees(math.atan2(-(b[0] - a[0]), -(b[1] - a[1])))
        segs.append(dict(type=sg["type"], from_=sg["frm"], to=sg["to"], len_m=bh.r4(math.dist(a, b)), path_dir_deg_left=round(hd, 2),
                         heading=sg["heading"], oblique_deg=round(((hd - sg["heading"] + 180) % 360) - 180, 2), jambs=jc,
                         min_clearance_any_m=bh.r4(d), nearest_any=r[4] if r else None, ok_jambs=bool(all(j["ok"] for j in jc))))
    jams = [j for s in segs for j in s.get("jambs", [])]
    return segs, (bh.r4(min(j["min_jamb_clearance_m"] for j in jams)) if jams else None), (all(j["ok"] for j in jams) if jams else None)


def run_transition(tid, T, S, plan, obs, tmp, a, rep, render=True):
    from PIL import Image
    poses, issues, end_err = trans_poses(T)
    segs, jmin, jok = trans_check(T, plan, obs)
    shots = len(T["segs"])
    frames = []
    for k, p in enumerate(poses):
        cl = min((bh.rect_dist((p["x"], p["y"]), r[:4]), r[4]) for r in obs)
        frames.append(dict(k=k, x=bh.r4(p["x"]), y=bh.r4(p["y"]), z=bh.r4(p["z"]), yaw=bh.r4(p["yaw"]), u0=bh.r4(p["u0"]), v0=bh.r4(p["v0"]),
                           seg=p["seg"], s_m=p["s"], clearance_m=bh.r4(cl[0]), nearest=cl[1]))
    R = dict(note=T["note"], shots=shots, segments=segs, path_issues=issues, end_pose_error=end_err, min_jamb_clearance_m=jmin,
             jambs_ok=jok, play_s_designer=T.get("play_s"), frames=frames,
             F9=("pass" if (jok in (True, None)) and end_err["pos_m"] <= 0.005 and abs(end_err["yaw_deg"]) < 1e-6 and not issues else "fail"),
             F9_note="jambs >= 0.15 (crossed openings), last pose = the frame camera; play time = designer estimate, not measured")
    if render:
        tiles = []
        rooms = {"P-B": ["bath"], "P-D": ["kitchen-dining"], "T-LD''": ["kitchen-dining"], "T-LD'' alt": ["kitchen-dining"],
                 "T-CBath''": ["corridor", "bath"]}[tid]
        lamps_set([k for r in rooms for k in ROOM_LAMPS[r]])
        for f in frames:
            set_cam(S, dict(loc=[f["x"], f["y"], f["z"]], yaw=f["yaw"], u0=f["u0"], v0=f["v0"]))
            fp = os.path.join(tmp, f"tr_{f['k']:03d}.png")
            render_quick(fp, tmp, int(a.tres * a.xs), max(4, int(a.tsamples * a.xs)))
            lab = f"{f['k']:02d} {f['seg']} s={f['s_m']:.2f} ({f['x']:.2f},{f['y']:.2f},{f['z']:.2f}) yaw {f['yaw']:.1f} clr {f['clearance_m']:.2f}"
            tiles.append((Image.open(fp).convert("RGB"), lab))
        os.makedirs(os.path.join(OUT, "transitions"), exist_ok=True)
        fn = tid.replace("''", "2").replace("'", "1").replace(" ", "-")
        outp = os.path.join(OUT, "transitions", f"{fn}-sheet.jpg")
        bh.make_sheet(tiles, f"{tid}: {T['note']}  ({len(tiles)} frames: pans every <= 5 deg, moves every <= 0.25 m; lamps of the rooms on; "
                             f"designer play time {T.get('play_s')} s)", outp, cols=6)
        R["sheet"] = f"framing/round2/transitions/{fn}-sheet.jpg"
        lamps_set([])
    rep.setdefault("transitions", {})[tid] = R
    return R


# ---------------------------------------------------------------------------------------------------------------
# frames
# ---------------------------------------------------------------------------------------------------------------
def run_frame(fid, S, plan, cams, prop, tmp, a, rep):
    t0 = time.time()
    room = FRAME_ROOM[fid]
    C = cams[fid]
    cam = S["cam"]
    set_cam(S, C)
    lit = lamps_set(ROOM_LAMPS[room])
    p = os.path.join(OUT, f"{fid}.png")
    depth, idx, normal = render_main(p, tmp, a)
    est = est_rows(fid, S, cam, C, idx)
    items, flags = analyse(C, S, idx, room)
    acc = acceptance2(fid, S, cam, C, idx, depth, plan, est, items, flags)
    acc["F3"]["rules_designer"] = designer_rules(fid, S, cam, C, idx, items)
    if any(not r["ok"] for r in acc["F3"]["rules_designer"]):
        acc["F3"]["result"] = "fail"
    R = dict(frame=fid, room=room, camera=C, image=f"framing/round2/{fid}.png", lamps_on=lit,
             mean_L_lit=fr.mean_L(p), est_vs_measured=est, est_flags=[r["key"] for r in est if r["flag_gt_tol"]], acceptance=acc)
    obs = bh.obstacles()
    cl = min((bh.rect_dist(C["loc"][:2], r[:4]), r[4]) for r in obs)
    R["camera_clearance_m"] = dict(min=bh.r4(cl[0]), nearest=cl[1])
    # F8 mirror
    if room == "bath":
        mr = mirror_pass(C, cam)
        acc["F8"] = dict(mr, note="one pass for CB (B1 and B2 share the point); inside_frame = samples whose mirror point is in this frame")
        if fid == "B2":
            acc["F8"]["crop"] = crop_mirror(p, idx)
    else:
        acc["F8"] = dict(result="n/a (no mirror)")
    # F9 transitions arriving at this frame (numbers only here; sheets in run_transitions)
    tmap = {"B1": "T-CBath''", "D1": "T-LD''"}
    T = trans_defs(prop, cams)
    if fid in tmap:
        segs, jmin, jok = trans_check(T[tmap[fid]], plan, obs)
        _, issues, end_err = trans_poses(T[tmap[fid]])
        acc["F9"] = dict(result="pass" if jok and end_err["pos_m"] <= 0.005 and abs(end_err["yaw_deg"]) < 1e-6 and not issues else "fail",
                         transition=tmap[fid], min_jamb_clearance_m=jmin, end_pose_error=end_err, segments=segs, path_issues=issues,
                         note="play time = designer estimate, not measured")
    elif fid in ("K2-boy", "K2-girl"):
        tid = "T-CBoy'" if fid == "K2-boy" else "T-CGirl'"
        tr = fr.check_transition(prop, tid, plan, obs, C)
        acc["F9"] = dict(result="pass" if tr["ok"] and tr["end"]["pos_err_m"] <= 0.005 else "fail", transition=tid + " (round 1, unchanged)",
                         min_jamb_clearance_m=tr["min_jamb_clearance_m"], segments=tr["segments"], end=tr["end"],
                         note="re-checked against the round-2 geometry (new bed, desk, chair, prints)")
    else:
        acc["F9"] = dict(result="n/a (second frame: reached by the pan, see F12)")
    # F10 density, F11 lamps, F12 two-frame
    acc["F10"] = density(items, room, fid)
    acc["F11"] = lamp_check(fid, idx, lit)
    if fid in ("B1", "B2", "D1", "D2"):
        pair = {"B1": "B2", "B2": "B1", "D1": "D2", "D2": "D1"}[fid]
        Cp = cams[pair]
        same = C["loc"] == Cp["loc"] and C["u0"] == Cp["u0"] and C["v0"] == Cp["v0"]
        dyaw = abs(C["yaw"] - Cp["yaw"])
        acc["F12"] = dict(result="pass" if same and dyaw <= 35 + 1e-9 else "fail", pair=pair, same_point=same, loc=C["loc"],
                          pan_deg=dyaw, max_deg=35, pan_sheet="P-B" if room == "bath" else "P-D")
    else:
        acc["F12"] = dict(result="n/a (one-frame room)")
    R["items_visible"] = {v["name"]: dict(kind=v["kind"], frame_area_pct=round(100 * v["area"], 2), visible_pct=v["visible_pct"],
                                          cut_by_edge_pct=v["cut_pct"]) for v in items.values()}
    # daylight comparison (lamps off) + bath all-lamps
    os.makedirs(os.path.join(OUT, "extra"), exist_ok=True)
    lamps_set([])
    fp = os.path.join(OUT, "extra", f"{fid}-daylight.png")
    render_quick(fp, tmp, int(1280 * a.xs), max(4, int(40 * a.xs)))
    R["daylight_pass"] = dict(image=f"framing/round2/extra/{fid}-daylight.png", mean_L=fr.mean_L(fp), note="lamps off = round-1 light")
    if room == "bath":
        lamps_set(ROOM_LAMPS["bath-all"])
        fp = os.path.join(OUT, "extra", f"{fid}-alllamps.png")
        fr.render(fp, os.path.join(tmp, "p"), a.res, a.samples, ao=0.30, passes=False)
        R["all_lamps_pass"] = dict(image=f"framing/round2/extra/{fid}-alllamps.png", mean_L=fr.mean_L(fp), lamps=ROOM_LAMPS["bath-all"])
    lamps_set(ROOM_LAMPS[room])
    sw = C.get("sweep")
    if sw and not a.no_sweeps:
        R["sweep"] = sweep_strip(fid, S, C, sw, tmp, a, sweep_measure(fid))
    os.makedirs(os.path.join(OUT, "overlays"), exist_ok=True)
    rows = [r for r in est if r["est"] is not None]
    fr.make_overlay(p, os.path.join(OUT, "overlays", f"{fid}.png"), f"{fid} ({room})  cam {C['loc']} yaw {C['yaw']} u0 {C['u0']} v0 {C['v0']}",
                    rows, acc["F1"]["heroes"])
    R["overlay"] = f"framing/round2/overlays/{fid}.png"
    lamps_set([])
    R["runtime_s"] = round(time.time() - t0)
    rep.setdefault("frames", {})[fid] = R
    return R


def run_pick(opt, S, plan, prop, tmp, a, rep):
    t0 = time.time()
    room = PICK_ROOM[opt]
    cams = fr.prop_cams(prop)
    C = dict(cams[fr.OPTIONS[opt]["cam"]])
    cam = S["cam"]
    set_cam(S, C)
    lit = lamps_set(ROOM_LAMPS[room])
    p = os.path.join(OUT, f"{opt}-lit.png")
    depth, idx, normal = render_main(p, tmp, a)
    est = fr.est_rows(opt, S, cam, C, idx)
    acc = fr.acceptance(opt, S, cam, C, idx, depth, plan, est)
    items, flags = analyse(C, S, idx, room)
    acc["F3"]["object_object_tangents"] = flags
    acc["F3"]["note"] += "; round 2: object-object tangents measured from ray-cast silhouettes"
    if flags and acc["F3"]["result"] == "pass":
        acc["F3"]["result"] = "fail"
    acc["F10"] = density(items, room, opt)
    acc["F11"] = lamp_check(opt, idx, lit)
    acc["F12"] = dict(result="n/a (one-frame room)")
    r1 = json.load(open(os.path.join(R1, "selfcheck.json")))["options"].get(opt, {})
    R = dict(option=opt, room=room, camera=C, image=f"framing/round2/{opt}-lit.png", lamps_on=lit, mean_L_lit=fr.mean_L(p),
             mean_L_round1=r1.get("mean_L_editorial"), est_flags=[r["key"] for r in est if r["flag_gt_tol"]], acceptance=acc,
             round1_results={k: v.get("result") for k, v in r1.get("acceptance", {}).items()},
             items_visible={v["name"]: dict(kind=v["kind"], frame_area_pct=round(100 * v["area"], 2), visible_pct=v["visible_pct"],
                                            cut_by_edge_pct=v["cut_pct"]) for v in items.values()},
             note="same camera and geometry as round 1 + S11/S12 additions; F7 (sky only) unchanged by lamps: see round-1 selfcheck")
    lamps_set([])
    R["runtime_s"] = round(time.time() - t0)
    rep.setdefault("picks_lit", {})[opt] = R
    return R


# ---------------------------------------------------------------------------------------------------------------
# comparison sheet
# ---------------------------------------------------------------------------------------------------------------
def summary_line(acc):
    keys = ["F1", "F2", "F3", "F4", "F5", "F6", "F8", "F9", "F10", "F11", "F12"]
    fails = [k for k in keys if str(acc.get(k, {}).get("result", "")).startswith("fail")]
    weak = [k for k in keys if str(acc.get(k, {}).get("result", "")).startswith("weak")]
    s = "pass F1-F12" if not fails else "fail: " + ", ".join(fails)
    if weak:
        s += "  (weak: " + ", ".join(weak) + ")"
    return s


def slots_label(acc):
    f = acc.get("F10", {})
    if "counted" not in f:
        return ""
    return (f"  | slots: {f['counted']} by the rule, {f.get('info_counted_any_area_ge_50pct_visible')} if size is ignored "
            f"(min {f['minimum']})")


def summarize(rep):
    """Compact per-frame table + the density reading, for the README and the art director."""
    keys = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
    out = dict(frames={}, density={}, mirror_B2=None, transitions={})
    for grp, sub in (("frames", ""), ("picks_lit", "-lit")):
        for fid, R in rep.get(grp, {}).items():
            acc = R["acceptance"]
            out["frames"][fid + sub] = {k: str(acc.get(k, {}).get("result", "n/a"))[:40] for k in keys}
            out["frames"][fid + sub]["mean_L"] = R.get("mean_L_lit")
            out["frames"][fid + sub]["est_flags"] = len(R.get("est_flags", []))
            d = acc.get("F10", {})
            out["density"][fid + sub] = dict(
                minimum=d.get("minimum"), counted_by_rule=d.get("counted"),
                counted_if_area_ge_0_2pct=d.get("info_counted_if_area_ge_0_2pct"),
                counted_if_size_ignored=d.get("info_counted_any_area_ge_50pct_visible"),
                proxies_of_the_room_seen=len(d.get("slots", [])),
                excluded_small=[x["slot"] for x in d.get("slots", []) if x["why_not"] == "area < 0.5%"],
                excluded_cut_or_hidden=[x["slot"] for x in d.get("slots", []) if x["why_not"] == "visible < 50%"],
                missing_categories=d.get("missing_categories"))
    b2 = rep.get("frames", {}).get("B2", {}).get("acceptance", {}).get("F8")
    if b2:
        out["mirror_B2"] = dict(result=b2["result"], objects_seen=list(b2["hits"]), non_wall=b2["non_wall_objects"],
                                wall_Y=b2["wall_Y_range"], wall_Z=b2["wall_Z_range"], samples_in_frame=b2.get("inside_frame", {}).get("samples"))
    for tid, T in rep.get("transitions", {}).items():
        out["transitions"][tid] = dict(F9=T["F9"], shots=T["shots"], min_jamb_clearance_m=T["min_jamb_clearance_m"],
                                       end_pose_error=T["end_pose_error"], play_s_designer=T["play_s_designer"], sheet=T.get("sheet"))
    out["density_reading"] = (
        "Every slot of the round-2 lists has a proxy (kids 15, bath 21 + ceiling light, kitchen 23; picks: plan slots + S11 additions; "
        "only the corridor's optional picture-ledge was never modelled). The low 'counted' numbers are the counting rule: >= 0.5% of the "
        "frame removes small products (lamps, toy cars, condiment set, dispensers: 0.1-0.4% at 2.5-4.5 m), and >= 50% visible removes "
        "textiles that the composition cuts on purpose (rugs, curtains, blind) or covers (bedding under the bedspread).")
    rep["summary"] = out
    return out


def all_sheet(rep):
    from PIL import Image, ImageDraw
    w = 900
    th = int(w * 9 / 16)
    r1 = json.load(open(os.path.join(R1, "selfcheck.json"))).get("options", {})
    pairs = []
    for fid in FRAMES:
        o1 = ROUND1_IMG[fid]
        a1 = r1.get(o1, {}).get("acceptance", {})
        f1 = [k for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F8", "F9") if str(a1.get(k, {}).get("result", "")).startswith("fail")]
        R = rep.get("frames", {}).get(fid, {})
        acc = R.get("acceptance", {})
        pairs.append(((os.path.join(R1, f"{o1}.png"), f"ROUND 1  {o1}", ("fails: " + ", ".join(f1)) if f1 else "round 1: all pass"),
                      (os.path.join(OUT, f"{fid}.png"), f"ROUND 2  {fid}", (summary_line(acc) + slots_label(acc)) if acc else "not rendered")))
    for opt in PICKS:
        a1 = r1.get(opt, {}).get("acceptance", {})
        f1 = [k for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9") if str(a1.get(k, {}).get("result", "")).startswith("fail")]
        R = rep.get("picks_lit", {}).get(opt, {})
        acc = R.get("acceptance", {})
        pairs.append(((os.path.join(R1, f"{opt}.png"), f"ROUND 1  {opt}", ("fails: " + ", ".join(f1)) if f1 else "round 1: all pass"),
                      (os.path.join(OUT, f"{opt}-lit.png"), f"ROUND 2  {opt}-lit (S11 + S12 lamps)",
                       (summary_line(acc) + slots_label(acc)) if acc else "not rendered")))
    cols = 2
    rows = math.ceil(len(pairs) / cols)
    pad, head = 12, 70
    W = cols * (2 * w + pad) + (cols + 1) * pad + pad
    sheet = Image.new("RGB", (W, head + rows * (th + pad) + pad), (246, 245, 242))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16), "Framing round 2 (proposal 0.2): round 1 | round 2 per room / frame. Clay, 0 credits. Round 2 = room lamps on (2700 K).",
           fill=(15, 15, 15), font=ba.font(30))
    for k, (l, r) in enumerate(pairs):
        x = pad + (k % cols) * (2 * w + 2 * pad)
        y = head + (k // cols) * (th + pad)
        sheet.paste(fr.tile(l[0], w, l[1], l[2]), (x, y))
        sheet.paste(fr.tile(r[0], w, r[1], r[2]), (x + w + pad // 2, y))
    outp = os.path.join(OUT, "all-round2.jpg")
    sheet.save(outp, quality=88)
    return outp


# ---------------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------------
def is_round2(sel):
    parts = sel.split(",")
    return any(p in FRAMES or p.startswith("round2") or p in (o + "-lit" for o in PICKS) for p in parts)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--framing", required=True)
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--no-sweeps", action="store_true")
    ap.add_argument("--xs", type=float, default=1.0, help="scale of the extra passes / sheets (smoke tests)")
    ap.add_argument("--tres", type=int, default=640)
    ap.add_argument("--tsamples", type=int, default=24)
    ap.add_argument("--trans", default="P-B,P-D,T-LD'',T-LD'' alt,T-CBath''")
    a, _ = ap.parse_known_args(argv)
    os.makedirs(OUT, exist_ok=True)
    sel = a.framing.split(",")
    do_frames = [f for f in FRAMES if "round2" in sel or "round2-frames" in sel or f in sel]
    do_picks = [o for o in PICKS if "round2" in sel or "round2-lit" in sel or f"{o}-lit" in sel]
    do_trans = "round2" in sel or "round2-trans" in sel
    do_sheet = "round2" in sel or "round2-sheets" in sel or bool(do_frames or do_picks)
    sc_path = os.path.join(OUT, "selfcheck.json")
    rep = json.load(open(sc_path)) if os.path.exists(sc_path) else {}

    def save():
        json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)
    prop = fr.load_prop()
    if do_frames or do_picks or do_trans:
        plan_path, plan0 = bh.load_plan()
        spec = json.load(open(b4.SPEC_PATH))
        cfg = b4.v4_config(spec)
        t0 = time.time()
        S, plan, notes, wl = build_r2(plan0, cfg, a)
        cams = r2_cams(prop)
        rep.update(proposal="docs/proposals/house-framing.json " + prop["version"] + " (round_2)", plan=os.path.relpath(plan_path, REPO),
                   plan_version=plan0["version"],
                   render=f"{a.res}x{int(a.res * 9 / 16)}, {a.samples} samples, Cycles CPU seed 7, AgX Medium High Contrast, exposure +{fr.EDIT_EXPOSURE} (editorial) as round 1",
                   light="round-1 editorial daylight (sky %.1f + soft area light outside every window + roof lights + AO 0.30) PLUS the room's "
                         "S12 lamps at 2700 K (emissive shade + light source). Daylight-only (lamps off) per frame in extra/." % a.sky,
                   lamp_power=LAMP_POWER_NOTE, scene="one combined scene: plan 1.0 + round-1 picks H-B, C-B, W-A, MB-A + round-2 kids, bath, "
                                                     "kitchen-dining + S11/S12 additions", build_notes=notes,
                   lamps={k: dict(room=v["room"], typology=v["typ"], label=v["label"], shell=v["shell"],
                                  glow=[o.name for o, _ in v["glow"]], lights=[li.name for li in v["lights"]]) for k, v in LAMPS.items()},
                   build_s=round(time.time() - t0))
        save()
        tmp = tempfile.mkdtemp(prefix="framing-r2-")
        for fid in do_frames:
            run_frame(fid, S, plan, cams, prop, tmp, a, rep)
            save()
            print("frame", fid, rep["frames"][fid]["runtime_s"], flush=True)
        for opt in do_picks:
            run_pick(opt, S, plan, prop, tmp, a, rep)
            save()
            print("pick", opt, rep["picks_lit"][opt]["runtime_s"], flush=True)
        if do_trans:
            obs = bh.obstacles()
            T = trans_defs(prop, cams)
            for tid in [t for t in a.trans.split(",") if t]:
                run_transition(tid, T[tid], S, plan, obs, tmp, a, rep, render=True)
                save()
                print("transition", tid, flush=True)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    if do_sheet:
        summarize(rep)
        all_sheet(rep)
    save()
