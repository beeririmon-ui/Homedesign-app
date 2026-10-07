#!/usr/bin/env python3
"""
Framing options clay (docs/proposals/house-framing.md / .json 0.1, master-designer). 0 var2 credits.

Every option of the proposal is a switchable variant on top of the approved house plan 1.0: the plan geometry is
the default, and an option applies only its own geometry deltas (G-*) and layout. Called from build_house.py:

  python3 build_house.py --framing H-B                 # one option (2K clay + checks), writes framing/
  python3 build_house.py --framing hall                # every option of a room (+ the current frame)
  python3 build_house.py --framing all                 # everything, room by room, then the sheets
  python3 build_house.py --framing sheets              # compare sheets + all-picks + README tables only
  python3 build_house.py                               # no flag: the approved plan clays, exactly as before

Lighting ("editorial clay"): the sky through the windows exactly as the plan clays, PLUS (a) a soft area light
outside every window, invisible to the camera, so the window side reads as one light direction; (b) the opal
roof lights of the option as diffuse emitters at the top of their well, radiance = 0.55 x sky (opal transmission,
not boosted); (c) lamps as 2700 K glows only where the proposal calls them on (hall: console lamp); (d) a light
AO multiply (contact shadows). Checks that depend on light (F7) use a separate sky + roof light pass with (a), (c),
(d) off. Hall and corridor also get a 2700 K practicals pass, as section 6.3 asks.

Outputs (assets/blockout/house/framing/)
  <option>.png            2048x1152, 64 samples, the option's camera
  current-<room>.png      same light as the options, approved plan camera and geometry (fair comparison)
  overlays/<option>.png   thirds grid + every est value (designer) vs measured
  extra/                  sky-only (F7) and practicals passes, mirror crops, sweep contact strips
  <room>-compare.jpg      current | option A | option B (+ overlay row)
  all-picks.jpg           the designer's recommended pick per room
  selfcheck.json          per option: est vs measured, F1-F9, transitions
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
from mathutils import Vector

import build_house as bh

ba, bs, b4 = bh.ba, bh.bs, bh.b4
M = ba.M
P = bs.proj
HERE = bh.HERE
REPO = bh.REPO
OUT = os.environ.get("FRAMING_OUT") or os.path.join(HERE, "framing")
PROPOSAL = os.path.join(REPO, "docs", "proposals", "house-framing.json")

WARM = (1.0, 0.56, 0.25)            # ~2700 K, linear
SKY_COL = (0.93, 0.95, 0.99)
OPAL_T = 0.55                        # opal glazing diffuse transmission
EDIT_EXPOSURE = 0.35                 # editorial renders (the plan clays use +1.0); F7 pass uses +1.0 like the plan clays

# ---------------------------------------------------------------------------------------------------------------
# option table
# ---------------------------------------------------------------------------------------------------------------
OPTIONS = {
    "H-A": dict(room="hall", cam="H0-A", deltas=["G-H1", "G-H4", "G-H5"], lamps=["hall-console"]),
    "H-B": dict(room="hall", cam="H0-B", deltas=["G-H1", "G-H2", "G-H3", "G-H4"], lamps=["hall-console"]),
    "D-A": dict(room="kitchen-dining", cam="D0-A", deltas=["G-D1"], lamps=[]),
    "W-A": dict(room="work", cam="W0-A", deltas=["G-W1"], lamps=[]),
    "W-B": dict(room="work", cam="W0-B", deltas=["G-W2"], lamps=[]),
    "C-A": dict(room="corridor", cam="C0-A", deltas=["G-C1a", "G-C2"], lamps=[]),
    "C-B": dict(room="corridor", cam="C0-B", deltas=["G-C1b", "G-C2", "G-C3"], lamps=[]),
    "K-A-boy": dict(room="boy", cam="K-boy-A", deltas=["G-K1"], lamps=[]),
    "K-B-boy": dict(room="boy", cam="K-boy-B", deltas=["G-K1"], lamps=[]),
    "K-A-girl": dict(room="girl", cam="K-girl-A", deltas=["G-K1"], lamps=[]),
    "K-B-girl": dict(room="girl", cam="K-girl-B", deltas=["G-K1"], lamps=[]),
    "MB-A": dict(room="master", cam="MB0-A", deltas=["G-M1", "G-M2", "G-M3", "G-M4"], lamps=[]),
    "MB-B": dict(room="master", cam="MB0-B", deltas=["G-M4"], lamps=[]),
    "B-A": dict(room="bath", cam="B0-A", deltas=["G-B1", "G-B2"], lamps=[]),
    "B-B": dict(room="bath", cam="B0-B", deltas=["G-B1b"], lamps=[]),
}
ROOM_OPTS = {"hall": ["H-A", "H-B"], "kitchen-dining": ["D-A"], "work": ["W-A", "W-B"], "corridor": ["C-A", "C-B"],
             "boy": ["K-A-boy", "K-B-boy"], "girl": ["K-A-girl", "K-B-girl"], "master": ["MB-A", "MB-B"],
             "bath": ["B-A", "B-B"]}
ROOM_CUR = {"hall": "H0", "kitchen-dining": "D0", "work": "W0", "corridor": "C0", "boy": "K-boy", "girl": "K-girl",
            "master": "MB0", "bath": "B0"}
PICKS = {"hall": "H-B", "kitchen-dining": "D-A", "work": "W-A", "corridor": "C-B", "boy": "K-A-boy",
         "girl": "K-A-girl", "master": "MB-A", "bath": "B-A"}
# K-B for the girl is not in cameras_for_clay; it is the boy K-B camera +3.63 in Y (same shell, as the proposal says)
EXTRA_CAMS = {"K-girl-B": {"id": "K-girl-B", "room": "girl", "loc": [-0.95, 16.63, 1.00], "yaw": 0, "u0": 0.50,
                           "v0": 0.36, "derived": "K-boy-B + 3.63 in Y (not listed in cameras_for_clay)"}}

NEW_IDX = 300                         # pass indices for the option geometry
REG = {}                              # group name -> dict(pidx, objs, room, kind)


def r4(x):
    return bh.r4(x)


def load_prop():
    return json.load(open(PROPOSAL))


def prop_cams(prop):
    C = {c["id"]: dict(c) for c in prop["cameras_for_clay"]}
    C.update(copy.deepcopy(EXTRA_CAMS))
    return C


# ---------------------------------------------------------------------------------------------------------------
# plan deltas (openings / windows) -> patched copy of the plan; the approved plan file is never touched
# ---------------------------------------------------------------------------------------------------------------
def patch_plan(plan, deltas):
    p = copy.deepcopy(plan)
    op = {o["id"]: o for o in p["openings"]}
    wi = {w["id"]: w for w in p["windows"]}
    if "G-H2" in deltas:
        op["O-front-door"]["y"] = [7.80, 8.80]
    if "G-M1" in deltas:
        op["O-corridor-master"]["x"] = [2.00, 2.90]
    if "G-W2" in deltas:
        wi["W-work"]["y"] = [6.85, 8.65]
    if "G-B1" in deltas:
        wi["W-bath"].update(x=[3.45, 4.45], sill=0.90, head=2.40)
    if "G-B1b" in deltas:
        wi["W-bath"].update(x=[3.95, 6.05], sill=1.85, head=2.40)
    return p


# ---------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------
def kill(*prefixes):
    gone = []
    for ob in list(bpy.data.objects):
        if any(ob.name == p or ob.name.startswith(p + "_") or ob.name.startswith(p + ".") or
               (p.endswith("*") and ob.name.startswith(p[:-1])) for p in prefixes):
            gone.append(ob.name)
            bpy.data.objects.remove(ob, do_unlink=True)
    return gone


def reg(name, objs, room, kind="proxy"):
    global NEW_IDX
    pidx = NEW_IDX
    NEW_IDX += 1
    for o in objs:
        o.pass_index = pidx
    REG[name] = dict(pidx=pidx, objs=objs, room=room, kind=kind)
    return objs


def mat_cache(name, hexcol, rough=0.9):
    if name not in M:
        M[name] = bs.make_mat(name, hexcol, rough)
    return M[name]


def emission_mat(name, col, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = tuple(col) + (1.0,)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def mirror_mat():
    m = bpy.data.materials.new("mirror")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.92, 0.92, 0.92, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.02
    return m


def fluted_mat():
    """Fluted / opal glass: diffuse transmission (translucent) with a little straight transparency."""
    m = bpy.data.materials.new("fluted")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tl.inputs["Color"].default_value = (0.86, 0.87, 0.88, 1)
    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    tp.inputs["Color"].default_value = (0.9, 0.9, 0.9, 1)
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.12
    nt.links.new(tl.outputs[0], mx.inputs[1])
    nt.links.new(tp.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m


def bx(n, x0, x1, y0, y1, z0, z1, mat, bevel=0.0, group="framing"):
    return bs.box(n, x0, x1, y0, y1, z0, z1, mat, group, bevel=bevel)


def cyl(n, c, r, z0, z1, mat, group="framing", verts=48):
    return bs.cone(n, c[0], c[1], z0, z1, r, r, mat, group, verts=verts)


def rot_bar(n, a, b, w, mat, group="framing"):
    """Square bar of width w from point a to point b (3D)."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    ob = bs.box(n, -w / 2, w / 2, -w / 2, w / 2, -L / 2, L / 2, mat, group)
    ob.location = (a + b) / 2
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (b - a).normalized().to_track_quat("Z", "Y")
    return ob


def ceiling_with_holes(room_id, R, h, holes, well_top, opal_strength):
    """Rebuild a room ceiling slab (h..TOP) with rectangular holes; each hole gets a light well (thin walls up to
    well_top) closed by an opal emitter at the top. holes: [(x0, x1, y0, y1)]."""
    kill(f"{room_id}_ceiling")
    (rx0, rx1), (ry0, ry1) = R
    xs = sorted({rx0, rx1} | {v for hl in holes for v in hl[:2]})
    ys = sorted({ry0, ry1} | {v for hl in holes for v in hl[2:]})
    k = 0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            c = ((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2)
            if any(hl[0] < c[0] < hl[1] and hl[2] < c[1] < hl[3] for hl in holes):
                continue
            bs.box(f"{room_id}_ceilpc{k}", xs[i], xs[i + 1], ys[j], ys[j + 1], h, bh.TOP, M["ceiling"], "ceiling",
                   pidx=bh.IDX["ceiling"])
            k += 1
    opal = emission_mat("opal", SKY_COL, opal_strength)
    objs = []
    t = 0.04
    for q, (x0, x1, y0, y1) in enumerate(holes):
        # the slab itself is the well up to TOP; extra well walls only above TOP (no overlapping / coplanar faces)
        if well_top > bh.TOP + 1e-6:
            for nm, a in (("a", (x0 - t, x0, y0 - t, y1 + t)), ("b", (x1, x1 + t, y0 - t, y1 + t)),
                          ("c", (x0, x1, y0 - t, y0)), ("d", (x0, x1, y1, y1 + t))):
                if not (abs(a[1] - rx0) < 1e-6 or abs(a[0] - rx1) < 1e-6):      # wall side already there
                    objs.append(bs.box(f"well{q}{nm}", a[0], a[1], a[2], a[3], bh.TOP, well_top, M["wall"], "shell",
                                       pidx=bh.IDX["wall"]))
        e = bs.box(f"opal{q}", x0 - 0.001, x1 + 0.001, y0 - 0.001, y1 + 0.001, well_top - 0.01, well_top, opal,
                   "framing")
        objs.append(e)
    return objs


# ---------------------------------------------------------------------------------------------------------------
# option geometry
# ---------------------------------------------------------------------------------------------------------------
def build_option(opt, plan):
    D = set(OPTIONS[opt]["deltas"]) if opt in OPTIONS else set()
    W, T, A, C, Hd, O, Rg = M["wood"], M["textile"], M["art"], M["curtain"], M["holder"], M["obj"], M["rug"]
    oak = mat_cache("oak_lining", "#CBBBA5")
    lime = mat_cache("limestone", "#DAD3C6", 0.6)
    notes = []
    opal_strength = OPAL_T * 7.0
    # ----------------------------------------------------------------------------------- hall
    if "G-H1" in D:
        objs = ceiling_with_holes("hall", ((0.80, 3.60), (6.35, 9.80)), 3.00, [(0.95, 1.85, 6.70, 8.30)], 3.45,
                                  opal_strength)
        reg("G-H1 roof light", objs, "hall", "architecture")
    if "G-H2" in D:
        kill("front_door_closed")
        reg("front door (G-H2)", [bx("front_door_closed_h2", 3.65, 3.70, 7.80, 8.80, 0.0, 2.40, M["oak_door"])],
            "hall", "architecture")
    if "G-H3" in D:
        kill("console_top", "console_leg", "h_art", "h_lamp", "h_lamp_b", "h_vessel", "h_tray")
        dx = 0.25
        reg("hall console", bh._legs_table("console3", 2.30 + dx, 3.10 + dx, 6.35, 6.70, 0.80, W, leg=0.035, inset=0.03),
            "hall", "furniture")
        reg("hall/framed-art", [bx("h_art3", 2.42 + dx, 2.98 + dx, 6.35, 6.38, 1.30, 1.85, A)], "hall")
        reg("hall/table-lamp", [cyl("h_lamp3", (2.47 + dx, 6.52), 0.12, 1.05, 1.30, C),
                                cyl("h_lamp3_b", (2.47 + dx, 6.52), 0.06, 0.80, 1.05, Hd)], "hall")
        reg("hall/console-vessel", [cyl("h_vessel3", (2.97 + dx, 6.50), 0.07, 0.80, 1.12, O)], "hall")
        reg("hall/key-tray", [bx("h_tray3", 2.66 + dx, 2.84 + dx, 6.44, 6.56, 0.80, 0.83, Hd)], "hall")
    if "G-H4" in D:
        objs = [bx("portal_jamb_a", 0.95, 0.97, 6.27, 6.35, 0.0, 2.40, oak), bx("portal_jamb_b", 2.13, 2.15, 6.27, 6.35, 0.0, 2.40, oak),
                bx("portal_head", 0.97, 2.13, 6.27, 6.35, 2.38, 2.40, oak),
                bx("portal_case_a", 0.85, 0.95, 6.35, 6.38, 0.0, 2.40, oak), bx("portal_case_b", 2.15, 2.25, 6.35, 6.38, 0.0, 2.40, oak),
                bx("portal_case_h", 0.85, 2.25, 6.35, 6.38, 2.40, 2.50, oak)]
        reg("G-H4 oak portal", objs, "hall", "architecture")
        notes.append("G-H4: reveal lining 2 cm on the hall half of the reveal (Y 6.27-6.35) + 10 cm casing on the hall face; assumed profile")
    if "G-H5" in D:
        kill("bench_seat", "bench_end_a", "bench_end_b", "h_hooks", "h_cush")
        objs = [bx("bi_back", 0.80, 0.85, 6.60, 7.80, 0.0, 2.06, oak), bx("bi_cheek_a", 0.80, 1.20, 6.55, 6.60, 0.0, 2.10, oak),
                bx("bi_cheek_b", 0.80, 1.20, 7.80, 7.85, 0.0, 2.10, oak), bx("bi_canopy", 0.85, 1.20, 6.60, 7.80, 2.06, 2.10, oak),
                bx("bi_seat", 0.85, 1.20, 6.60, 7.80, 0.40, 0.45, oak)]
        objs += [bx(f"bi_panel{i}", 0.85, 0.855, 6.60 + 0.20 * i + 0.005, 6.60 + 0.20 * i + 0.195, 0.45, 2.06, oak) for i in range(6)]
        reg("G-H5 built-in bench", objs, "hall", "architecture")
        reg("hall/wall-hooks", [bx("bi_pegrail", 0.855, 0.88, 6.65, 7.75, 1.62, 1.68, Hd)] +
            [cyl(f"bi_peg{i}", (0.90, 6.75 + 0.18 * i), 0.012, 1.63, 1.67, Hd, verts=12) for i in range(6)], "hall")
        reg("hall/bench-cushion", [bx("bi_cush", 0.87, 1.18, 6.62, 7.78, 0.45, 0.50, T, 0.015)], "hall")
        notes.append("G-H5: niche 0.40 deep (= the plan bench depth; 'furred 0.25' read as the panelled back + cheeks, interpretation) between cheeks Y 6.55-7.85, canopy 2.10; peg rail at 1.65 replaces the hook bar")
    # ----------------------------------------------------------------------------------- kitchen-dining
    if "G-D1" in D:
        kill("dining_table_top", "dining_table_leg", "dchair*", "d_pend", "d_cord", "d_runner", "d_vase", "d_cand_a",
             "d_cand_b", "d_bowl", "d_pad*", "kit_wall_units")
        cy = 1.65
        reg("dining table", bh._legs_table("dtab", 3.50, 5.10, cy - 0.425, cy + 0.425, 0.75, W), "kitchen-dining", "furniture")
        ch = bh._chair("dch_a", 3.95, 0.90, "+y", W) + bh._chair("dch_b", 4.65, 0.90, "+y", W)
        reg("dining chairs (2, window side)", ch, "kitchen-dining", "furniture")
        reg("dining bench", [bx("dbench_top", 3.60, 5.00, 2.30, 2.65, 0.41, 0.45, W, bevel=0.004),
                             bx("dbench_l1", 3.66, 3.72, 2.33, 2.62, 0.0, 0.41, W), bx("dbench_l2", 4.88, 4.94, 2.33, 2.62, 0.0, 0.41, W)],
            "kitchen-dining", "furniture")
        reg("kitchen-dining/dining-pendant", [cyl("d_pend2", (4.30, cy), 0.275, 1.50, 1.80, O),
                                              cyl("d_cord2", (4.30, cy), 0.004, 1.80, 3.0, Hd)], "kitchen-dining")
        reg("kitchen-dining/table-runner", [bx("d_runner2", 3.60, 5.00, cy - 0.15, cy + 0.15, 0.75, 0.754, T)], "kitchen-dining")
        reg("kitchen-dining/centerpiece-vase", [cyl("d_vase2", (4.35, cy), 0.08, 0.754, 1.05, O)], "kitchen-dining")
        reg("kitchen-dining/candle-holders", [cyl("d_cand2a", (3.75, cy - 0.06), 0.04, 0.754, 0.98, O),
                                              cyl("d_cand2b", (3.92, cy + 0.06), 0.04, 0.754, 0.92, O)], "kitchen-dining")
        reg("kitchen-dining/seat-pads", [bx(f"d_pad2{i}", cx - 0.20, cx + 0.20, 0.70, 1.10, 0.46, 0.48, T) for i, cx in enumerate((3.95, 4.65))],
            "kitchen-dining")
        reg("kitchen open shelf (draft 0.1)", [bx("k_shelf", 6.97, 7.25, 0.00, 1.50, 1.57, 1.61, oak),
                                               bx("k_upper_rest", 6.90, 7.25, 1.50, 4.00, 1.50, 2.40, M["kit"])], "kitchen-dining", "furniture")
        reg("kitchen-dining/open-shelf-ceramics", [cyl("k_jug", (7.10, 1.20), 0.06, 1.61, 1.85, O), cyl("k_low", (7.10, 1.02), 0.07, 1.61, 1.68, O)],
            "kitchen-dining")
        notes.append("G-D1: table 160x85 (rectangular proxy, draft 0.1 says super-ellipse) at (4.30, 1.65); 2 window-side chairs; bench X 3.60-5.00 Y 2.30-2.65 h 0.45; pendant dia 55 x 30, bottom 1.50; wall units over Y 0.40-1.50 replaced by the draft's open oak shelf (Y 0-1.50, bottom 1.57)")
    # ----------------------------------------------------------------------------------- work
    if "G-W1" in D:
        kill("desk_top", "desk_leg", "desk_chair*", "shelf_unit", "w_lamp", "w_lamp_b", "w_box_a", "w_box_b", "w_tray",
             "w_mag", "w_pot", "w_plant", "w_art", "w_rug", "w_basket", "leaf_hall_work")
        reg("built-in oak desk + shelf", [bx("bdesk_top", -1.625, -0.025, 6.35, 6.95, 0.72, 0.76, oak),
                                          bx("bdesk_side_a", -1.625, -1.585, 6.35, 6.95, 0.0, 0.72, oak),
                                          bx("bdesk_side_b", -0.065, -0.025, 6.35, 6.95, 0.0, 0.72, oak),
                                          bx("bdesk_drawer", -1.585, -1.10, 6.35, 6.93, 0.56, 0.72, oak),
                                          bx("bshelf", -1.625, -0.025, 6.35, 6.62, 1.62, 1.66, oak)], "work", "architecture")
        reg("desk chair", bh._chair("wchair", -0.825, 7.30, "-y", W), "work", "furniture")
        reg("work/framed-art", [bx("w_art2", -1.125, -0.525, 6.35, 6.38, 0.98, 1.48, A)], "work")
        reg("work/shelf-boxes", [bx("w_box2a", -1.50, -1.20, 6.38, 6.60, 1.66, 1.88, O), bx("w_box2b", -0.45, -0.15, 6.38, 6.60, 1.66, 1.80, O)], "work")
        reg("work/desk-lamp", [cyl("w_lamp2", (-0.30, 6.58), 0.09, 1.10, 1.25, C), cyl("w_lamp2_b", (-0.30, 6.58), 0.07, 0.76, 1.10, Hd)], "work")
        reg("work/desk-tray", [bx("w_tray2", -1.45, -1.20, 6.45, 6.70, 0.76, 0.79, Hd)], "work")
        reg("work/magazine-holder", [bx("w_mag2", 0.10, 0.35, 6.40, 6.65, 0.0, 0.42, Hd)], "work")
        reg("work/basket", [cyl("w_basket2", (-1.25, 6.62), 0.15, 0.0, 0.32, O)], "work")
        reg("work/planter", [cyl("w_pot2", (-1.95, 6.70), 0.18, 0.0, 0.40, O), cyl("w_plant2", (-1.95, 6.70), 0.30, 0.40, 1.30, M["crown"])], "work")
        reg("work/rug", [bx("w_rug2", -1.725, 0.075, 6.95, 9.05, 0.0, 0.012, Rg)], "work")
        bx("leaf_hall_work_folded", 0.61, 0.65, 9.00, 9.90, 0.0, 2.40, M["door"], group="doors").pass_index = bh.IDX["door"]
        notes.append("G-W1: built-in desk X -1.625..-0.025 x 0.60 deep, top 0.76; shelf at 1.62; art 60x50 between; chair at Y 7.30; door leaf folded on the south wall X 0.61-0.65 Y 9.00-9.90")
    if "G-W2" in D:
        kill("shelf_unit", "w_box_a", "w_box_b", "w_curt_a", "w_curt_b", "w_rod")
        reg("low shelf (W-B)", [bx("lshelf", -1.90, -0.90, 6.35, 6.70, 0.0, 1.10, W)], "work", "furniture")
        reg("work/shelf-boxes", [bx("w_box3a", -1.80, -1.50, 6.38, 6.66, 1.10, 1.30, O), bx("w_box3b", -1.40, -1.10, 6.38, 6.66, 0.40, 0.62, O)], "work")
        reg("work/curtains", [bx("w_curt3a", -2.30, -2.18, 6.63, 6.85, 0.01, 2.85, C, 0.02), bx("w_curt3b", -2.30, -2.18, 8.65, 8.87, 0.01, 2.85, C, 0.02),
                              bx("w_rod3", -2.25, -2.23, 6.60, 8.90, 2.87, 2.89, Hd)], "work")
        notes.append("G-W2: window 1.80 (mullion); desk under it unchanged (centred Y 7.75); shelf X -1.90..-0.90, h 1.10, 0.40 from the corner")
    # ----------------------------------------------------------------------------------- kids
    if "G-K1" in D:
        for kid, dy in (("boy", 0.0), ("girl", 3.63)):
            kill(f"{kid}_bed_base", f"{kid}_bed_mattress", f"{kid}_bed_head", f"{kid}_desk_top", f"{kid}_desk_leg",
                 f"{kid}_wardrobe", f"{kid}_duvet", f"{kid}_cush", f"{kid}_rug", f"{kid}_wlamp", f"{kid}_shelf", f"{kid}_print*",
                 f"{kid}_tbasket", f"{kid}_toy", f"{kid}_dlamp", f"{kid}_dlamp_b", f"{kid}_hooks", "boy_teepee", "girl_canopy")
            y0 = 10.25 + dy
            yw = 13.73 + dy
            reg(f"{kid} wardrobes (west wall)", [bx(f"{kid}_wr", -2.30, 0.20, yw - 0.60, yw, 0.0, 2.40, M["kit"])], kid, "furniture")
            bed = [bx(f"{kid}_kbed_base", -1.544, 0.344, y0 + 0.006, y0 + 0.894, 0.10, 0.28, oak),
                   bx(f"{kid}_kbed_matt", -1.53, 0.33, y0 + 0.02, y0 + 0.88, 0.28, 0.43, M["bed"], bevel=0.03)]
            reg(f"{kid} bed 90x190", bed, kid, "furniture")
            g = []
            w = 0.045
            for xi, xx in enumerate((-1.55 + w / 2, 0.35 - w / 2)):
                for yi, yy in enumerate((y0 + w / 2, y0 + 0.90 - w / 2)):
                    g.append(bx(f"{kid}_gp{xi}{yi}", xx - w / 2, xx + w / 2, yy - w / 2, yy + w / 2, 0.0, 1.15, oak))
                g.append(rot_bar(f"{kid}_gr{xi}a", (xx, y0 + w / 2, 1.15), (xx, y0 + 0.45, 1.60), w, oak))
                g.append(rot_bar(f"{kid}_gr{xi}b", (xx, y0 + 0.90 - w / 2, 1.15), (xx, y0 + 0.45, 1.60), w, oak))
            g.append(bx(f"{kid}_gridge", -1.55 + 0.004, 0.35 - 0.004, y0 + 0.45 - w / 2 + 0.003, y0 + 0.45 + w / 2 - 0.003, 1.60 - w, 1.60 - 0.003, oak))
            g.append(bx(f"{kid}_geave", -1.55 + w + 0.002, 0.35 - w - 0.002, y0 + 0.90 - w + 0.004, y0 + 0.90 - 0.004, 0.40, 0.40 + w, oak))
            reg(f"{kid} gable 'house' frame", g, kid, "architecture")
            reg(f"{kid}/bedding", [bx(f"{kid}_duv2", -1.30, 0.33, y0 + 0.02, y0 + 0.88, 0.43, 0.50, T, 0.02)], kid)
            reg(f"{kid}/cushions", [bx(f"{kid}_cush2", -1.50, -1.36, y0 + 0.10, y0 + 0.80, 0.43, 0.70, T, 0.03)], kid)
            reg(f"{kid}/soft-toy", [cyl(f"{kid}_toy2", (-0.10, y0 + 0.50), 0.09, 0.50, 0.75, T)], kid)
            reg(f"{kid}/wall-lamp", [bx(f"{kid}_wl2", -1.45, -1.30, y0, y0 + 0.12, 0.95, 1.10, Hd)], kid)
            reg(f"{kid}/framed-prints", [bx(f"{kid}_pr2{i}", a, a + 0.25, y0, y0 + 0.02, 0.78, 1.08, A) for i, a in enumerate((-0.85, -0.45, -0.05))], kid)
            reg(f"{kid}/wall-hooks", [bx(f"{kid}_hk2", 0.55, 1.05, y0, y0 + 0.06, 1.10, 1.17, Hd)], kid)
            reg(f"{kid}/shape-shelf", [bx(f"{kid}_sh2", 0.55, 1.15, y0, y0 + 0.15, 1.45, 1.60, O)], kid)
            reg(f"{kid}/toy-basket", [cyl(f"{kid}_tb2", (1.10, y0 + 0.35), 0.17, 0.0, 0.32, O)], kid)
            reg(f"{kid}/rug", [cyl(f"{kid}_rug2", (-0.60, y0 + 1.80), 0.80, 0.0, 0.012, Rg)], kid)
            if kid == "boy":
                reg("boy/play-structure", [bs.cone("boy_teepee2", -1.92, y0 + 0.41, 0.0, 1.50, 0.375, 0.03, T, "framing", verts=5)], kid)
            else:
                reg("girl/play-structure", [bs.cone("girl_canopy2", -1.70, y0 + 0.45, 0.20, 2.98, 0.45, 0.03, C, "framing", verts=32)], kid)
        notes.append("G-K1: desk + desk lamp of the plan dropped (not in the proposal layout); teepee base 0.75 (the corner beside the bed is 0.75 wide, base <= 0.95 allowed) centred (-1.92, 10.66) on the camera->corner ray; canopy cone hook over the bed's north end (-1.70), hem 0.20")
    # ----------------------------------------------------------------------------------- master
    if "G-M1" in D:
        kill("leaf_corridor_master")
        bx("leaf_corridor_master_m1", 2.90, 2.94, 17.66, 18.56, 0.0, 2.40, M["door"], group="doors").pass_index = bh.IDX["door"]
    if "G-M2" in D:
        kill("wardrobes")
    if "G-M3" in D:
        kill("master_bed_base", "master_bed_mattress", "master_bed_head", "ns_a", "ns_b", "m_duvet", "m_pillow*", "m_throw",
             "m_cush", "m_sconce_a", "m_sconce_b", "m_art", "m_vase", "m_cand_a", "m_cand_b", "m_rug", "m_pot", "m_plant")
        reg("master bed 180x200", bh._bed("mbed", -1.60, 0.20, 17.66, 19.66, "y0", h=0.50, head_h=1.15), "master", "furniture")
        reg("nightstands 45", [bx("mns_a", -2.10, -1.65, 17.66, 18.06, 0.0, 0.55, W), bx("mns_b", 0.25, 0.70, 17.66, 18.06, 0.0, 0.55, W)],
            "master", "furniture")
        reg("master/bedding", [bx("m_duv2", -1.57, 0.17, 18.30, 19.68, 0.50, 0.58, T, 0.02)], "master")
        reg("master/pillowcases", [bx(f"m_pil2{i}", a, a + 0.70, 17.75, 18.20, 0.50, 0.66, T, 0.04) for i, a in enumerate((-1.50, -0.60))], "master")
        reg("master/throw", [bx("m_thr2", -1.61, 0.21, 19.25, 19.65, 0.58, 0.61, T)], "master")
        reg("master/cushions", [bx("m_cus2", -1.00, -0.40, 18.20, 18.32, 0.58, 0.95, T, 0.03)], "master")
        reg("master/bedside-sconces", [bx("m_sc2a", -1.945, -1.805, 17.66, 17.78, 1.25, 1.43, Hd), bx("m_sc2b", 0.405, 0.545, 17.66, 17.78, 1.25, 1.43, Hd)], "master")
        reg("master/framed-art", [bx("m_art2", -1.30, -0.10, 17.66, 17.69, 1.40, 2.00, A)], "master")
        reg("master/nightstand-vase", [cyl("m_vas2", (-1.875, 17.86), 0.06, 0.55, 0.80, O)], "master")
        reg("master/candle-holders", [cyl("m_cn2a", (0.42, 17.88), 0.035, 0.55, 0.72, O), cyl("m_cn2b", (0.53, 17.84), 0.035, 0.55, 0.66, O)], "master")
        reg("master/rug", [bx("m_rug2", -2.20, 0.80, 18.70, 20.90, 0.0, 0.012, Rg)], "master")
        reg("master/planter", [cyl("m_pot2", (1.45, 18.15), 0.20, 0.0, 0.42, O), cyl("m_plt2", (1.45, 18.15), 0.34, 0.42, 1.75, M["crown"])], "master")
        notes.append("G-M3: tall planter (option 'tall planter or lounge chair') at (1.45, 18.15), crown to 1.75; basket and pendant of the plan kept")
    if "G-M4" in D:
        door = (2.00, 2.90) if "G-M1" in D else (1.88, 2.78)
        cream = mat_cache("wainscot", "#EBE6DE")
        groove = mat_cache("groove", "#B9B2A8")
        objs = []
        for k, (s0, s1) in enumerate(((-2.30, door[0]), (door[1], 3.10))):
            objs.append(bx(f"wsc{k}", s0, s1, 17.66, 17.68, 0.0, 1.25, cream))
            objs.append(bx(f"wsc_cap{k}", s0, s1, 17.66, 17.70, 1.25, 1.28, oak))
            x = s0 + 0.10
            while x < s1 - 0.05:
                objs.append(bx(f"wsc_g{k}", x - 0.003, x + 0.003, 17.68, 17.683, 0.15, 1.25, groove))
                x += 0.10
        reg("G-M4 wainscot", objs, "master", "architecture")
    # ----------------------------------------------------------------------------------- bath
    fl = None
    if "G-B1" in D or "G-B1b" in D:
        fl = fluted_mat()
        w = next(w for w in plan["windows"] if w["id"] == "W-bath")
        reg("bath fluted glazing", [bx("fluted_glass", w["x"][0], w["x"][1], 9.62, 9.63, w["sill"], w["head"], fl)], "bath", "architecture")
    if "G-B1" in D:
        kill("vanity", "vanity_top", "wc", "wc_cistern", "b_disp_a", "b_disp_b", "b_vtray", "b_sconce_a", "b_sconce_b", "b_pot",
             "b_plant", "b_mat")
        reg("vanity 110 oak + limestone", [bx("van1", 4.85, 5.95, 9.95, 10.45, 0.30, 0.85, W), bx("van1_top", 4.83, 5.97, 9.95, 10.47, 0.85, 0.88, lime)],
            "bath", "furniture")
        reg("U6 mirror", [bx("mirror", 4.90, 5.90, 9.95, 9.97, 1.15, 1.95, mirror_mat())], "bath", "mirror")
        reg("wc (west wall)", [bx("wc2", 4.55, 4.95, 13.00, 13.59, 0.0, 0.40, M["sanitary"]), bx("wc2_c", 4.50, 5.00, 13.45, 13.59, 0.40, 1.10, M["sanitary"])],
            "bath", "furniture")
        reg("bath/wall-sconces", [bx("b_sc2a", 4.72, 4.82, 9.95, 10.07, 1.45, 1.63, Hd), bx("b_sc2b", 5.98, 6.08, 9.95, 10.07, 1.45, 1.63, Hd)], "bath")
        reg("bath/dispenser-set", [cyl("b_ds2a", (5.05, 10.12), 0.035, 0.88, 1.08, O), cyl("b_ds2b", (5.15, 10.15), 0.035, 0.88, 1.02, O)], "bath")
        reg("bath/vanity-tray", [bx("b_vt2", 5.30, 5.55, 10.02, 10.15, 0.88, 0.90, Hd)], "bath")
        reg("bath/planter", [cyl("b_pt2", (5.78, 10.30), 0.07, 0.88, 1.02, O), cyl("b_pl2", (5.78, 10.30), 0.13, 1.02, 1.32, M["crown"])], "bath")
        reg("bath/bath-mat", [bx("b_mat2", 4.90, 5.90, 10.60, 11.20, 0.0, 0.012, Rg)], "bath")
        notes.append("G-B1/G-B2: mirror 100 x 80 (Z 1.15-1.95; height not given, assumed); sconces flank the mirror; shower, towel ladder, towels and robe hooks of the plan kept (not moved: fix policy)")
    if "G-B1b" in D:
        kill("b_sconce_a", "b_sconce_b")
        reg("U6 mirror", [bx("mirror", 3.90, 5.10, 9.95, 9.97, 1.10, 1.75, mirror_mat())], "bath", "mirror")
        reg("bath/wall-sconces", [bx("b_sc3a", 3.72, 3.84, 9.95, 10.07, 1.30, 1.48, Hd), bx("b_sc3b", 5.16, 5.28, 9.95, 10.07, 1.30, 1.48, Hd)], "bath")
        notes.append("G-B1b: mirror 120 centred on the double vanity (X 3.90-5.10, Z 1.10-1.75); plan sconces (Z 1.75-1.93) collided with the new sill 1.85, moved to flank the mirror at 1.30-1.48")
    if "G-C1a" in D:
        objs = ceiling_with_holes("corridor", ((1.70, 3.10), (9.80, 17.51)), 2.70,
                                  [(2.00, 2.80, y - 0.40, y + 0.40) for y in (11.0, 13.9, 16.4)], bh.TOP, opal_strength)
        reg("G-C1a roof lights", objs, "corridor", "architecture")
    if "G-C1b" in D:
        objs = ceiling_with_holes("corridor", ((1.70, 3.10), (9.80, 17.51)), 2.70, [(1.70, 2.00, 10.00, 17.20)], bh.TOP, opal_strength)
        reg("G-C1b roof-light slot", objs, "corridor", "architecture")
    if "G-C2" in D:
        kill("c_art0", "c_art1", "c_art2")
        reg("corridor/gallery-art", [bx(f"c_art2{i}", 1.70, 1.73, a, a + 0.40, 1.20, 1.70, A) for i, a in enumerate((14.0, 14.6, 15.2))], "corridor")
    if "G-C3" in D:
        objs = [bx("cportal_a", 1.70, 1.74, 9.70, 9.95, 0.0, 2.70, oak), bx("cportal_b", 3.06, 3.10, 9.70, 9.95, 0.0, 2.70, oak),
                bx("cportal_h", 1.74, 3.06, 9.70, 9.95, 2.62, 2.70, oak),
                bx("cportal_ca", 1.60, 1.70, 9.76, 9.80, 0.0, 2.80, oak), bx("cportal_cb", 3.10, 3.20, 9.76, 9.80, 0.0, 2.80, oak),
                bx("cportal_ch", 1.60, 3.20, 9.76, 9.80, 2.70, 2.80, oak)]
        reg("G-C3 oak portal", objs, "corridor", "architecture")
        notes.append("G-C3: 4 cm oak lining Y 9.70-9.95 (lintel drops to 2.62) + 10 cm casing on the hall face; assumed profile")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# light
# ---------------------------------------------------------------------------------------------------------------
def window_lights(plan, strength_w_per_m2=70.0):
    """Soft area light outside every window, invisible to camera / reflections: the window side reads as the one
    light direction (S6). Shape = window, 1.2 m outside the outer face, 0.5 m up, tilted 18 deg down into the room."""
    out = []
    rooms = {r["id"]: r for r in plan["rooms"]}
    for w in plan["windows"]:
        if "plane_x" not in w and "plane_y" not in w:
            continue
        t = w.get("wall_t", 0.35)
        z0, z1 = w["sill"], w["head"]
        if "plane_x" in w:                      # north walls (x0 side): outward = -X
            a0, a1 = w["y"]
            room = rooms[w["room"]]
            sgn = -1 if abs(w["plane_x"] - room["x"][0]) < 1e-6 else 1
            c = Vector((w["plane_x"] + sgn * (t + 1.2), (a0 + a1) / 2, (z0 + z1) / 2 + 0.5))
            inward = Vector((-sgn, 0, 0))
            sx, sy = a1 - a0, z1 - z0
            axis_w = Vector((0, 1, 0))
        else:
            a0, a1 = w["x"]
            room = rooms[w["room"]]
            sgn = -1 if abs(w["plane_y"] - room["y"][0]) < 1e-6 else 1
            c = Vector(((a0 + a1) / 2, w["plane_y"] + sgn * (t + 1.2), (z0 + z1) / 2 + 0.5))
            inward = Vector((0, -sgn, 0))
            sx, sy = a1 - a0, z1 - z0
            axis_w = Vector((1, 0, 0))
        if w["id"] == "W-living":
            t = 0.47
            c.x = -2.30 - (t + 1.2)
        d = (inward * math.cos(math.radians(18)) - Vector((0, 0, math.sin(math.radians(18))))).normalized()
        ld = bpy.data.lights.new(f"winlight_{w['id']}", "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = sx * 1.3, sy * 1.2
        ld.energy = strength_w_per_m2 * sx * sy
        ld.color = (0.97, 0.98, 1.0)
        ob = bpy.data.objects.new(f"winlight_{w['id']}", ld)
        ob.location = c
        q = d.to_track_quat("-Z", "Y")
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = q
        ob.visible_camera = False
        ob.visible_glossy = False
        bpy.context.scene.collection.objects.link(ob)
        out.append(ob)
    return out


def lamp_glow(names, strength=5.0):
    """Turn the named lamp proxies into 2700 K glows (emissive shade). Returns the objects."""
    em = emission_mat("lamp2700", WARM, strength)
    out = []
    for ob in bpy.data.objects:
        if ob.name in names:
            ob.data.materials.clear()
            ob.data.materials.append(em)
            out.append(ob)
    return out


LAMPS = {"hall-console": ["h_lamp", "h_lamp3"],
         "hall-practicals": ["h_lamp", "h_lamp3", "h_ceil"],
         "corridor-practicals": ["c_light_a", "c_light_b"]}


def set_lamps(keys, strength=5.0):
    names = [n for k in keys for n in LAMPS.get(k, [])]
    return lamp_glow(names, strength)


def unglow(objs, mat):
    for ob in objs:
        ob.data.materials.clear()
        ob.data.materials.append(mat)


# ---------------------------------------------------------------------------------------------------------------
# render (EXR passes + AO contact-shadow multiply)
# ---------------------------------------------------------------------------------------------------------------
def setup_comp(tmp, ao=0.30):
    sc = bpy.context.scene
    sc.use_nodes = True
    vl = sc.view_layers[0]
    vl.use_pass_ambient_occlusion = True
    sc.world.light_settings.distance = 0.35
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    if ao > 0:
        mx = nt.nodes.new("CompositorNodeMixRGB")
        mx.blend_type = "MULTIPLY"
        mx.inputs[0].default_value = ao
        nt.links.new(rl.outputs["Image"], mx.inputs[1])
        nt.links.new(rl.outputs["AO"], mx.inputs[2])
        nt.links.new(mx.outputs[0], comp.inputs["Image"])
    else:
        nt.links.new(rl.outputs["Image"], comp.inputs["Image"])
    fo = nt.nodes.new("CompositorNodeOutputFile")
    fo.base_path = tmp
    fo.format.file_format = "OPEN_EXR"
    fo.format.color_depth = "32"
    fo.format.exr_codec = "ZIP"
    fo.file_slots.clear()
    for name in ("Depth", "IndexOB", "Normal"):
        fo.file_slots.new(name + "_")
        nt.links.new(rl.outputs[name], fo.inputs[name + "_"])


def render(path, tmp, res, samples, ao=0.30, passes=True, exposure=None):
    bpy.context.scene.view_settings.exposure = EDIT_EXPOSURE if exposure is None else exposure
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res, int(round(res * 9 / 16))
    sc.cycles.samples = samples
    if passes or ao > 0:
        setup_comp(tmp, ao)
    else:
        sc.use_nodes = False
    sc.frame_set(1)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if not passes:
        return None
    depth = bs.load_exr(os.path.join(tmp, "Depth_0001.exr"))
    idx = np.rint(bs.load_exr(os.path.join(tmp, "IndexOB_0001.exr"))).astype(np.int32)
    normal = bs.load_exr(os.path.join(tmp, "Normal_0001.exr"), channels=3)
    return depth, idx, normal


def mean_L(path):
    from PIL import Image
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(float)
    return round(float((rgb * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1)


# ---------------------------------------------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------------------------------------------
def U(cam, x, y, z=None):
    z = cam.location.z if z is None else z
    return P(cam, (x, y, z))[0]


def V(cam, x, y, z):
    return P(cam, (x, y, z))[1]


def depth_of(C, x, y):
    yaw = math.radians(C["yaw"])
    return (-math.sin(yaw)) * (x - C["loc"][0]) + (-math.cos(yaw)) * (y - C["loc"][1])


def edge_entry(C, axis, val, side):
    q, t = bh.edge_wall_entry(None, dict(yaw=C["yaw"], u0=C["u0"], loc=C["loc"]), (axis, val), side)
    return q


def top_edge_Z(cam, x, y):
    """Z where the top frame edge meets the vertical line through (x, y)."""
    z0, z1 = 0.0, 4.0
    v0, v1 = V(cam, x, y, z0), V(cam, x, y, z1)
    return z0 + (0.0 - v0) * (z1 - z0) / (v1 - v0)


def group_bbox(idx, pidxs):
    m = np.isin(idx, pidxs)
    if m.sum() < 10:
        return None
    H, W = idx.shape
    ys, xs = np.nonzero(m)
    return [xs.min() / W, (xs.max() + 1) / W, ys.min() / H, (ys.max() + 1) / H, int(m.sum())]


def G(name):
    return [REG[name]["pidx"]] if name in REG else []


def plan_group(S, key):
    """pidx of a plan proxy (room/slot) or fixed furniture key."""
    if key in S["prox"]:
        return [S["prox"][key]["pidx"]]
    if key in S["fur"]:
        return [S["fur"][key]["pidx"]]
    return []


def est_rows(opt, S, cam, C, idx):
    """Every est value of the proposal for this option vs measured (Blender projection = the plan pinhole
    equations; object extents from the index pass)."""
    R = []

    def add(key, est, meas, note="", tol=0.02):
        if isinstance(est, (list, tuple)) and isinstance(meas, (list, tuple)):
            dev = [None if (e is None or m is None) else r4(m - e) for e, m in zip(est, meas)]
            flag = any(d is not None and abs(d) > tol for d in dev)
        elif isinstance(est, (int, float)) and isinstance(meas, (int, float)):
            dev = r4(meas - est)
            flag = abs(dev) > tol
        else:
            dev, flag = None, False
        R.append(dict(key=key, est=est, measured=r4(meas) if isinstance(meas, (float, list, tuple)) else meas, dev=dev,
                      flag_gt_tol=bool(flag), tol=tol, note=note))

    def bb(pid):
        b = group_bbox(idx, pid)
        return None if b is None else [r4(b[0]), r4(b[1])], (None if b is None else [r4(b[2]), r4(b[3])])

    hz = cam.location.z
    if opt == "H-A":
        add("door_u", [0.395, 0.636], [U(cam, 0.95, 6.35), U(cam, 2.15, 6.35)])
        u, _ = bb(plan_group(S, "hall-console"))
        add("console_u (pixels)", [0.651, 0.912], u)
        add("left_wall_u end (= door jamb X 0.95)", 0.395, U(cam, 0.95, 6.35))
    elif opt == "H-B":
        add("NE_corner_u (0.80, 6.35)", 0.199, U(cam, 0.80, 6.35))
        add("door_u (jambs X 0.95 / 2.15)", [0.228, 0.484], [U(cam, 0.95, 6.35), U(cam, 2.15, 6.35)])
        add("vista_centre_u (1.55, 6.35)", 0.356, U(cam, 1.55, 6.35))
        u, _ = bb(G("hall console"))
        add("console_u (pixels)", [0.567, 0.81], u)
        add("console_u (geometry, front corners Y 6.70)", [0.567, 0.81], [U(cam, 2.55, 6.70, 0.80), U(cam, 3.35, 6.70, 0.80)])
        add("art_centre_u (2.95, 6.35)", 0.69, U(cam, 2.95, 6.35))
        add("SE_corner_u (3.60, 6.35)", 0.86, U(cam, 3.60, 6.35))
        add("front_door_east_jamb_u (3.60, 7.80)", 1.13, U(cam, 3.60, 7.80))
    elif opt == "D-A":
        add("window_u (jambs X 2.95 / 4.75)", [0.108, 0.463], [U(cam, 2.95, 0.0), U(cam, 4.75, 0.0)])
        add("window head v at the south jamb (4.75, 0, 2.70)", -0.05, V(cam, 4.75, 0.0, 2.70), "est 'about -0.05'", 0.03)
        u, v = bb(G("kitchen-dining/dining-pendant"))
        add("pendant_u (pixels, shade+cord)", [0.509, 0.664], u)
        pm = np.isin(idx, G("kitchen-dining/dining-pendant"))
        shade = [r4(min(U(cam, 4.30 + 0.275 * math.cos(a), 1.65 + 0.275 * math.sin(a), 1.65) for a in np.linspace(0, 6.28, 73))),
                 r4(max(U(cam, 4.30 + 0.275 * math.cos(a), 1.65 + 0.275 * math.sin(a), 1.65) for a in np.linspace(0, 6.28, 73)))]
        add("pendant_u (geometry, shade rim)", [0.509, 0.664], shade)
        vs = [min(V(cam, 4.30 + 0.275 * math.cos(a), 1.65 + 0.275 * math.sin(a), 1.80) for a in np.linspace(0, 6.28, 73)),
              max(V(cam, 4.30 + 0.275 * math.cos(a), 1.65 + 0.275 * math.sin(a), 1.50) for a in np.linspace(0, 6.28, 73))]
        add("pendant_v (geometry, shade top..bottom)", [0.079, 0.23], vs)
        add("SE_corner_u (7.25, 0)", 0.73, U(cam, 7.25, 0.0))
        add("shelf_u (open shelf centre 7.25, 0.75)", 0.80, U(cam, 7.25, 0.75, 1.59))
        u, v = bb(G("dining table"))
        add("table_top_u (pixels, incl. legs)", [0.30, 0.83], u)
        tv = [V(cam, x, y, 0.75) for x in (3.50, 5.10) for y in (1.225, 2.075)]
        add("table_top_v (geometry, top corners)", [0.57, 0.70], [min(tv), max(tv)])
        u, v = bb(G("dining bench"))
        add("bench_u (pixels)", [0.66, 0.87], u)
        add("bench_v top (pixels; est 0.775 -> below the bottom edge)", 0.775, v[0] if v else None, "bottom of bbox = %s" % (v[1] if v else None))
        add("camera_to_pendant_m", 2.36, math.dist((2.75, 3.45, 1.10), (4.30, 1.65, 1.65)))
        add("cornice_wedge_at_corner_v (cornice bottom at the SE corner)", 0.036, V(cam, 7.25, 0.0, 2.875), "est is '<= 0.036'")
    elif opt == "W-A":
        ye = edge_entry(C, "x", -2.30, "left")
        add("window_visible_Y", [7.15, 7.88], [7.15, ye])
        add("window_u", [0.0, 0.136], [0.0, U(cam, -2.30, 7.15)])
        add("window_cut_pct", 39, round(100 * (8.35 - ye) / 1.20, 1), tol=2)
        add("NE_corner_u (-2.30, 6.35)", 0.219, U(cam, -2.30, 6.35))
        add("SE_corner_u (0.65, 6.35)", 0.781, U(cam, 0.65, 6.35))
        u, _ = bb(G("built-in oak desk + shelf"))
        add("desk_centre_u (pixels)", 0.50, (u[0] + u[1]) / 2 if u else None)
        add("door_jamb_Y8.10_u (0.65, 8.10)", 1.06, U(cam, 0.65, 8.10))
        add("top_edge_on_east_wall_Z", 2.46, top_edge_Z(cam, -0.825, 6.35))
        add("camera_to_east_wall_m", 3.50, 9.85 - 6.35)
    elif opt == "W-B":
        add("window_u (Y 8.65 / 6.85)", [0.135, 0.563], [U(cam, -2.30, 8.65), U(cam, -2.30, 6.85)])
        add("NE_corner_u (-2.30, 6.35)", 0.643, U(cam, -2.30, 6.35))
        add("camera_to_corner_m (depth)", 3.49, depth_of(C, -2.30, 6.35), "euclid %.3f" % math.dist(C["loc"][:2], (-2.30, 6.35)))
    elif opt in ("C-A", "C-B"):
        add("gallery_u (prints Y 15.6 / 14.0)", [0.192, 0.35], [U(cam, 1.70, 15.6, 1.45), U(cam, 1.70, 14.0, 1.45)])
        add("nearest_print_top_v (1.70, 15.6, 1.70)", 0.067, V(cam, 1.70, 15.6, 1.70))
        # ceiling enters the frame where the top edge meets Z 2.70 (centre column)
        lo, hi = 9.8, 17.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if V(cam, 2.397, mid, 2.70) < 0:
                hi = mid
            else:
                lo = mid
        add("slot/ceiling visible from Y (top edge meets Z 2.70, centre column)", 13.24, (lo + hi) / 2, "slot visible for Y < this", 0.05)
        add("girl_door_jamb_u (1.70, 16.26)", -0.047, U(cam, 1.70, 16.26))
    elif opt in ("K-A-boy", "K-A-girl"):
        dy = 3.63 if "girl" in opt else 0.0
        ye = edge_entry(C, "x", -2.30, "left")
        add("window_visible_Y", [10.75 + dy, 11.83 + dy], [10.75 + dy, ye])
        add("window_u", [0.0, 0.23], [0.0, U(cam, -2.30, 10.75 + dy)])
        add("window_cut_pct", 23, round(100 * (12.15 + dy - ye) / 1.40, 1), tol=2)
        add("NE_corner_u", 0.303, U(cam, -2.30, 10.25 + dy))
        add("bed_front_u (corners X -1.55 / 0.35 at Y front, Z 0.43)", [0.25, 0.65], [U(cam, -1.55, 11.15 + dy, 0.43), U(cam, 0.35, 11.15 + dy, 0.43)])
        kid = "girl" if "girl" in opt else "boy"
        u, _ = bb(G(f"{kid} bed 90x190"))
        add("bed_u (pixels, whole bed)", [0.25, 0.65], u)
        add("bed_centre_u (-0.60, front)", 0.41, U(cam, -0.60, 11.15 + dy, 0.43))
        add("east_wall_right_edge_X", 1.23, edge_entry(C, "y", 10.25 + dy, "right"), tol=0.05)
        add("SE_corner_u (1.55, Y east)", 1.12, U(cam, 1.55, 10.25 + dy))
        add("top_edge_on_east_wall_Z (at the corner)", 2.11, top_edge_Z(cam, -2.30, 10.25 + dy))
        add("camera_to_corner_m (depth)", 4.16, depth_of(C, -2.30, 10.25 + dy), "euclid %.3f" % math.dist(C["loc"][:2], (-2.30, 10.25 + dy)))
    elif opt in ("K-B-boy", "K-B-girl"):
        dy = 3.63 if "girl" in opt else 0.0
        add("window_u", [0.0, 0.10], [0.0, U(cam, -2.30, 10.75 + dy)])
        add("NE_corner_u", 0.173, U(cam, -2.30, 10.25 + dy))
        add("top_edge_on_east_wall_Z", 1.84, top_edge_Z(cam, -0.95, 10.25 + dy))
    elif opt == "MB-A":
        ye = edge_entry(C, "x", -2.30, "left")
        add("window_visible_Y", [18.10, 18.92], [18.10, ye])
        add("window_u", [0.0, 0.138], [0.0, U(cam, -2.30, 18.10)])
        add("window_cut_pct", 45, round(100 * (19.60 - ye) / 1.50, 1), tol=2)
        add("NE_corner_u (-2.30, 17.66)", 0.185, U(cam, -2.30, 17.66))
        add("bed_centre_u (-0.70, 17.66)", 0.50, U(cam, -0.70, 17.66))
        add("sconces_u (centres X -1.875 / 0.475)", [0.269, 0.731], [U(cam, -1.875, 17.66, 1.34), U(cam, 0.475, 17.66, 1.34)])
        add("door_jamb_X2.00_u (2.00, 17.66)", 1.031, U(cam, 2.00, 17.66))
        add("bed_foot_u (corners at Y 19.66, Z 0.50)", [0.07, 0.93], [U(cam, -1.60, 19.66, 0.50), U(cam, 0.20, 19.66, 0.50)])
        add("bed_foot_top_v (Y 19.66, Z 0.50)", 0.912, V(cam, -0.70, 19.66, 0.50))
        add("bed_head_v (headboard top Z 1.15)", 0.645, V(cam, -0.70, 17.72, 1.15))
        add("top_edge_on_bed_wall_Z", 2.37, top_edge_Z(cam, -0.70, 17.66))
        add("camera_to_bed_wall_m", 3.39, 21.05 - 17.66)
    elif opt == "MB-B":
        add("NE_corner_u (-2.30, 17.66)", 0.341, U(cam, -2.30, 17.66))
    elif opt == "B-A":
        add("north_wall_sliver_u (NE corner 3.25, 9.95)", [0.0, 0.04], [0.0, U(cam, 3.25, 9.95)])
        add("window_u (X 3.45 / 4.45)", [0.103, 0.355], [U(cam, 3.45, 9.95), U(cam, 4.45, 9.95)])
        add("mirror_u (X 4.90 / 5.90)", [0.443, 0.60], [U(cam, 4.90, 9.95, 1.55), U(cam, 5.90, 9.95, 1.55)])
        add("vanity_right_end_u (5.95, back Y 9.95)", 0.606, U(cam, 5.95, 9.95, 0.85), "front Y 10.47: %.3f" % U(cam, 5.97, 10.47, 0.85))
        add("SE_corner_u (6.25, 9.95)", 0.644, U(cam, 6.25, 9.95))
        add("right_edge_on_south_wall_Y", 11.92, edge_entry(C, "x", 6.25, "right"), tol=0.05)
    elif opt == "B-B":
        add("north_wall_sliver_u (NE corner 3.25, 9.95)", None, U(cam, 3.25, 9.95), "no est in the proposal")
        add("clerestory_u (X 3.95 / 6.05)", None, [U(cam, 3.95, 9.95, 2.1), U(cam, 6.05, 9.95, 2.1)], "no est")
        add("mirror_u (X 3.90 / 5.10)", None, [U(cam, 3.90, 9.95, 1.42), U(cam, 5.10, 9.95, 1.42)], "no est")
        add("SE_corner_u (6.25, 9.95)", None, U(cam, 6.25, 9.95), "no est")
    return R


# hero definition per option: (label, point (x, y, z) or REG/plan group name, mode)
HERO = {
    "H-A": [("vista centre (living door centre)", (1.55, 6.35, None), "third")],
    "H-B": [("vista centre (living door centre)", (1.55, 6.35, None), "third"), ("console vignette (art centre)", (2.95, 6.35, None), "third")],
    "D-A": [("pendant (hero: table under the lamp)", (4.30, 1.65, 1.65), "third"), ("table centre", (4.30, 1.65, 0.75), "third")],
    "W-A": [("desk centre", (-0.825, 6.35, None), "centre")],
    "W-B": [("desk centre (under the window)", (-2.00, 7.75, 0.75), "third"), ("NE corner", (-2.30, 6.35, None), "third")],
    "C-A": [("enfilade axis (vanishing point)", (2.397, -50.0, None), "centre")],
    "C-B": [("enfilade axis (vanishing point)", (2.397, -50.0, None), "centre")],
    "K-A-boy": [("NE corner nook", (-2.30, 10.25, None), "third")],
    "K-A-girl": [("NE corner / canopy", (-2.30, 13.88, None), "third")],
    "K-B-boy": [("bed centre (-0.60, east wall)", (-0.60, 10.25, None), "centre")],
    "K-B-girl": [("bed centre (-0.60, east wall)", (-0.60, 13.88, None), "centre")],
    "MB-A": [("bed centre", (-0.70, 17.66, None), "centre")],
    "MB-B": [("NE corner", (-2.30, 17.66, None), "third"), ("bed centre", (-0.25, 17.66, None), "third")],
    "B-A": [("mirror centre (vanity hero)", (5.40, 9.95, 1.55), "third"), ("SE corner", (6.25, 9.95, None), "third")],
    "B-B": [("mirror centre", (4.50, 9.95, 1.42), "third"), ("SE corner", (6.25, 9.95, None), "third")],
}
HERO_WALL = {   # point on the hero wall for F5 (depth along the camera axis); thresholds 3.0 / bath 2.8
    "H-A": (1.55, 6.35), "H-B": (1.55, 6.35), "D-A": (4.30, 0.0), "W-A": (-0.825, 6.35), "W-B": (-2.30, 6.35),
    "C-A": (2.397, 9.80), "C-B": (2.397, 9.80), "K-A-boy": (-2.30, 10.25), "K-A-girl": (-2.30, 13.88),
    "K-B-boy": (-0.95, 10.25), "K-B-girl": (-0.95, 13.88), "MB-A": (-0.70, 17.66), "MB-B": (-2.30, 17.66),
    "B-A": (5.40, 9.95), "B-B": (4.50, 9.95)}
WINDOWS_IN_ROOM = {"hall": [], "corridor": [], "kitchen-dining": ["W-dining"], "work": ["W-work"], "boy": ["W-boy"],
                   "girl": ["W-girl"], "master": ["W-master"], "bath": ["W-bath"]}


def window_check(cam, w):
    """S4/F2 from geometry: visible fraction of the width (mid height), whole-window margins, width share."""
    if "plane_x" in w:
        pts = [(w["plane_x"], y) for y in np.linspace(w["y"][0], w["y"][1], 201)]
    else:
        pts = [(x, w["plane_y"]) for x in np.linspace(w["x"][0], w["x"][1], 201)]
    zm = (w["sill"] + w["head"]) / 2
    uvs = [P(cam, (x, y, zm)) for x, y in pts]
    vis = [0 <= u <= 1 and d > 0 for u, v, d in uvs]
    frac = sum(vis) / len(vis)
    if frac == 0:
        return dict(in_frame=False)
    us = [u for (u, v, d), ok in zip(uvs, vis) if ok]
    vh = [P(cam, (x, y, w["head"]))[1] for x, y in pts]
    vs = [P(cam, (x, y, w["sill"]))[1] for x, y in pts]
    whole = frac == 1.0
    margins = dict(left=r4(min(u for u, v, d in uvs)), right=r4(1 - max(u for u, v, d in uvs)), top=r4(min(vh)), bottom=r4(1 - max(vs)))
    width_share = max(us) - min(us)
    cut_pct = round(100 * (1 - frac), 1)
    head_cut = min(vh) < 0
    if whole:
        ok = all(m >= 0.03 for m in margins.values())
        rule = "whole, >= 0.03 to every edge"
    else:
        ok = cut_pct >= 15
        rule = "cut >= 15% of the width"
    ok_share = width_share <= 0.30
    return dict(in_frame=True, visible_width_pct=round(100 * frac, 1), cut_pct=cut_pct, u=[r4(min(us)), r4(max(us))],
                head_v_min=r4(min(vh)), head_cut_by_top=bool(head_cut), sill_v_max=r4(max(vs)), margins_if_whole=margins,
                width_share=r4(width_share), rule=rule, ok_cut_rule=bool(ok), ok_width_le_30pct=bool(ok_share),
                ok=bool(ok and ok_share))


SHELL_PIDX = [bh.IDX["wall"], bh.IDX["floor"], bh.IDX["ceiling"], 5, 6, 7, 8, 9, 10]


def acceptance(opt, S, cam, C, idx, depth, plan, est):
    room = OPTIONS[opt]["room"]
    H, W = idx.shape
    out = {}
    # F1
    rows = []
    for lab, pt, mode in HERO[opt]:
        x, y, z = pt
        u = U(cam, x, y, z)
        if mode == "centre":
            ok = abs(u - 0.50) <= 0.01 and abs(C["u0"] - 0.50) < 1e-6
            rule = "0.50 +-0.01 (u0 0.50)"
        else:
            ok = 0.30 <= u <= 0.36 or 0.64 <= u <= 0.70
            rule = "0.30-0.36 / 0.64-0.70"
        rows.append(dict(hero=lab, u=r4(u), rule=rule, ok=bool(ok), almost_centre_0_45_0_58=bool(0.45 <= u <= 0.58)))
    out["F1"] = dict(result="pass" if rows[0]["ok"] else "fail", heroes=rows,
                     note="result = first (named) hero; others listed")
    # F2
    wins = {w["id"]: w for w in plan["windows"]}
    wr = {wid: window_check(cam, wins[wid]) for wid in WINDOWS_IN_ROOM[room]}
    wr = {k: v for k, v in wr.items() if v.get("in_frame")}
    out["F2"] = dict(result=("n/a (no window in frame)" if not wr else ("pass" if all(v["ok"] for v in wr.values()) else "fail")),
                     windows=wr)
    # F3 edge tangents: groups (pixels) and architectural lines (geometry)
    tang = []
    names = {}
    for k, v in S["prox"].items():
        names[v["pidx"]] = k
    for k, v in S["fur"].items():
        names[v["pidx"]] = "fixed:" + k
    for k, v in REG.items():
        names[v["pidx"]] = k
    names[bh.IDX["door"]] = "door leaves"
    for pidx, nm in names.items():
        b = group_bbox(idx, [pidx])
        if b is None or b[4] < 200:
            continue
        for side, m in (("left", b[0]), ("right", 1 - b[1]), ("top", b[2]), ("bottom", 1 - b[3])):
            if 0.0 < m < 0.02:
                tang.append(dict(item=nm, side=side, margin=r4(m)))
    arch = []
    for fe in est:
        k = fe["key"]
        if any(s in k for s in ("corner", "jamb", "door_u", "window_u", "sliver")):
            vals = fe["measured"] if isinstance(fe["measured"], list) else [fe["measured"]]
            for val in vals:
                if isinstance(val, (int, float)) and val not in (0.0,) and (abs(val) < 0.02 or abs(val - 1) < 0.02):
                    arch.append(dict(line=k, u=val))
    out["F3"] = dict(result="pass" if not tang and not arch else "fail", object_tangents=tang, architectural_lines_within_0_02_of_edge=arch,
                     note="objects: visible bbox margin 0 < m < 0.02 (touching = cut, allowed); pairwise object-object tangents not measured (visual)")
    # F4 depth layers
    hd = depth_of(C, *HERO_WALL[opt])
    obj = ~np.isin(idx, SHELL_PIDX + [0, bh.IDX["trim"], bh.IDX["threshold"]])
    fg = obj & (depth < 0.55 * hd)
    bg = (depth > hd + 0.4) | (idx == 0)
    fgn = {}
    for pidx in np.unique(idx[fg]):
        n = int((idx[fg] == pidx).sum())
        if n > 0.002 * H * W:
            fgn[names.get(int(pidx), f"idx {int(pidx)}")] = round(n / (H * W), 4)
    out["F4"] = dict(result="pass" if fgn and bg.mean() > 0.02 else ("weak (no foreground object)" if not fgn else "weak (no background)"),
                     hero_wall_depth_m=r4(hd), foreground_objects_frac=fgn, background_frac=round(float(bg.mean()), 4),
                     note="heuristic: foreground = non-shell pixels nearer than 0.55 x hero-wall depth; background = beyond the hero wall + 0.4 m (next room, window, sky)")
    # F5
    lim = 2.8 if room == "bath" else 3.0
    out["F5"] = dict(result="pass" if hd >= lim - 1e-6 else "fail", camera_to_hero_wall_depth_m=r4(hd), min_m=lim,
                     hero_wall_point=HERO_WALL[opt])
    # F6
    calm = np.isin(idx, SHELL_PIDX).mean()
    out["F6"] = dict(result="pass" if calm >= 0.25 else "fail", calm_wall_floor_ceiling_frac=round(float(calm), 3),
                     note="pixels of wall, floor and ceiling (trim, rugs, windows excluded)")
    return out


def mirror_reflection(cam, n=40):
    """F8 / U6: cast the reflected camera rays from a grid on the mirror plane; list every object hit."""
    mirror = next(o for o in bpy.data.objects if o.name == "mirror")
    dg = bpy.context.evaluated_depsgraph_get()
    bbw = [mirror.matrix_world @ Vector(c) for c in mirror.bound_box]
    x0, x1 = min(c.x for c in bbw), max(c.x for c in bbw)
    z0, z1 = min(c.z for c in bbw), max(c.z for c in bbw)
    yface = max(c.y for c in bbw) + 1e-4
    co = cam.matrix_world.translation
    hits = {}
    pts = []
    for i in range(n):
        for j in range(n):
            p = Vector((x0 + (x1 - x0) * (i + 0.5) / n, yface, z0 + (z1 - z0) * (j + 0.5) / n))
            u, v, d = P(cam, p)
            if not (0 <= u <= 1 and 0 <= v <= 1):
                continue
            # visible from the camera?
            dirc = (p - co).normalized()
            ok, loc, nor, fi, ob, _ = bpy.context.scene.ray_cast(dg, co, dirc, distance=(p - co).length + 0.01)
            if not ok or ob.name != "mirror":
                continue
            r = dirc - 2 * dirc.dot(Vector((0, 1, 0))) * Vector((0, 1, 0))
            ok2, loc2, _, _, ob2, _ = bpy.context.scene.ray_cast(dg, p + r * 0.002, r, distance=30)
            nm = ob2.name if ok2 else "sky"
            base = nm.split(".")[0]
            hits.setdefault(base, dict(n=0, y=[], z=[]))
            hits[base]["n"] += 1
            if ok2:
                hits[base]["y"].append(loc2.y)
                hits[base]["z"].append(loc2.z)
            pts.append((u, v))
    tot = sum(h["n"] for h in hits.values())
    out = {}
    for k, h in sorted(hits.items(), key=lambda kv: -kv[1]["n"]):
        out[k] = dict(frac=round(h["n"] / max(1, tot), 3), y=[r4(min(h["y"])), r4(max(h["y"]))] if h["y"] else None,
                      z=[r4(min(h["z"])), r4(max(h["z"]))] if h["z"] else None)
    shell_like = lambda k: k.startswith("hwall") or k.startswith("bath_") or "skirt" in k or "sgap" in k or k.startswith("well")
    non_wall = {k: v for k, v in out.items() if not shell_like(k)}
    allw = [(h["y"], h["z"]) for k, h in hits.items() if k.startswith("hwall") and h["y"]]
    return dict(samples_visible=tot, hits=out, non_wall_objects=sorted(non_wall), ok=not non_wall,
                wall_Y_range=[r4(min(min(a) for a, b in allw)), r4(max(max(a) for a, b in allw))] if allw else None,
                wall_Z_range=[r4(min(min(b) for a, b in allw)), r4(max(max(b) for a, b in allw))] if allw else None)


# ---------------------------------------------------------------------------------------------------------------
# transitions (F9)
# ---------------------------------------------------------------------------------------------------------------
TRANS_FOR = {"H-A": ["T-HC'"], "H-B": ["E0'", "T-HC'"], "D-A": ["T-LD'"], "W-A": ["T-HW'"], "W-B": ["T-HW''"],
             "K-A-boy": ["T-CBoy'"], "K-B-boy": ["T-CBoy''"], "K-A-girl": ["T-CGirl'"], "K-B-girl": ["T-CGirl'' (derived)"],
             "MB-A": ["T-CM'"], "MB-B": ["T-CM (unchanged + pedestal)"], "B-A": ["T-CBath'"], "B-B": ["T-CBath'"],
             "C-A": [], "C-B": []}
EXTRA_TRANS = {
    "T-HW''": {"segments": [{"type": "pan", "at": "H0", "yaw": [25, 60]}, {"type": "dolly", "from": [2.877, 9.039, 1.20], "to": [0.40, 8.65, 1.10], "heading": 60}],
               "play_s_approx": None, "note": "from the W-B text: pan to 60 + oblique dolly H0 -> (0.40, 8.65), 2.51 m"},
    "T-CBoy''": {"segments": [{"type": "dolly", "rail": "C0 -> S1'", "from": [2.397, 17.11, 1.20], "to": [2.641, 13.00, 1.20], "heading": 0},
                              {"type": "slide", "heading": 0, "from": [2.641, 13.00, 1.20], "to": [-0.95, 13.00, 1.00]}],
                 "play_s_approx": None, "note": "from the K-B text: rail to S1' + one slider 3.59 m, no pan"},
    "T-CGirl'' (derived)": {"segments": [{"type": "slide", "heading": 0, "from": [2.397, 17.11, 1.20], "to": [-0.95, 16.63, 1.00]}],
                            "play_s_approx": None, "note": "NOT in the proposal: K-B girl analog, one oblique slide C0 -> (-0.95, 16.63)"},
    "T-CM (unchanged + pedestal)": {"segments": [{"type": "pull-back", "heading": 0, "from": [2.397, 17.11, 1.20], "to": [1.75, 21.05, 1.05]},
                                                  {"type": "pan", "yaw": [0, 35]}], "play_s_approx": 2.4, "note": "plan T-CM with the pedestal to 1.05"},
}


def trans_segments(prop, tid):
    if tid in EXTRA_TRANS:
        return EXTRA_TRANS[tid]
    return next(t for t in prop["transitions_new"] if t["id"] == tid)


def check_transition(prop, tid, plan_p, obs, endcam):
    T = trans_segments(prop, tid)
    opens = bh.all_openings_for_hc1(plan_p)
    segs = []
    pos = None
    for sg in T["segments"]:
        if sg["type"] == "pan":
            segs.append(dict(type="pan", yaw=sg["yaw"]))
            continue
        frm = sg.get("from")
        to = sg.get("to")
        if frm is None and sg.get("rail") == "unchanged":      # T-HC' pull-back on the corridor rail
            frm, to = [2.877, 9.039, 1.20], [2.397, 17.11, 1.20]
        elif frm is None and "rail" in sg:            # rail from C0 to S1'
            frm, to = [2.397, 17.11, 1.20], [2.641, 13.00, 1.20]
        if frm is None:
            if sg.get("id") == "E0":
                frm, to = [2.877, 9.039, 1.20], [1.25, 5.55, 1.20]
        a, b = frm[:2], to[:2]
        jc = bh.jamb_clearance(a, b, opens)
        d, r = bh.seg_clearance(a, b, obs)
        hd = math.degrees(math.atan2(-(b[0] - a[0]), -(b[1] - a[1])))
        segs.append(dict(type=sg["type"], from_=frm, to=to, len_m=r4(math.dist(a, b)), len_plan=sg.get("len_m"),
                         path_dir_deg_left=round(hd, 2), heading=sg.get("heading"), jambs=jc,
                         min_clearance_any_m=r4(d), nearest_any=r[4] if r else None,
                         ok_jambs=bool(all(j["ok"] for j in jc))))
        pos = to
    end_ok = None
    if pos is not None and endcam is not None:
        end_ok = dict(end_pos=pos, cam=endcam["loc"], pos_err_m=r4(math.dist(pos, endcam["loc"])))
    jams = [j for s in segs for j in s.get("jambs", [])]
    return dict(id=tid, note=T.get("note", ""), play_s_designer=T.get("play_s_approx"), segments=segs, end=end_ok,
                min_jamb_clearance_m=r4(min([j["min_jamb_clearance_m"] for j in jams], default=None)) if jams else None,
                ok=bool(jams and all(j["ok"] for j in jams)) if jams else None)


# ---------------------------------------------------------------------------------------------------------------
# overlay
# ---------------------------------------------------------------------------------------------------------------
def make_overlay(clay, out, title, rows, heroes):
    from PIL import Image, ImageDraw
    im = Image.open(clay).convert("RGB")
    W, H = im.size
    dr = ImageDraw.Draw(im, "RGBA")
    for k in (1, 2):
        dr.line([(W * k / 3, 0), (W * k / 3, H)], fill=(255, 255, 255, 170), width=2)
        dr.line([(0, H * k / 3), (W, H * k / 3)], fill=(255, 255, 255, 170), width=2)
    for a, b in ((0.30, 0.36), (0.64, 0.70)):
        dr.rectangle((W * a, 0, W * b, H), fill=(255, 220, 120, 28))
    dr.line([(W / 2, 0), (W / 2, H)], fill=(120, 200, 255, 120), width=1)
    f = ba.font(22)
    fs = ba.font(18, bold=False)
    for h in heroes:
        x = h["u"] * W
        col = (40, 170, 70, 255) if h["ok"] else (220, 60, 40, 255)
        dr.line([(x, 0), (x, H)], fill=col, width=4)
        dr.text((x + 6, H - 70), f"{h['hero']} u {h['u']:.3f}", fill=col, font=fs)
    y = 50
    dr.rectangle((0, 0, W, 40), fill=(255, 255, 255, 220))
    dr.text((10, 8), title, fill=(10, 10, 10), font=f)
    for r in rows:
        txt = f"{r['key']}: est {r['est']}  meas {r['measured']}" + ("  !" if r["flag_gt_tol"] else "")
        w = dr.textlength(txt, font=fs)
        dr.rectangle((6, y - 2, 14 + w, y + 22), fill=(255, 255, 255, 200))
        dr.text((10, y), txt, fill=(200, 30, 20) if r["flag_gt_tol"] else (20, 20, 20), font=fs)
        y += 26
    im.save(out)


# ---------------------------------------------------------------------------------------------------------------
# scene for an option (or for the current plan: opt None)
# ---------------------------------------------------------------------------------------------------------------
def build(opt, plan0, cfg, a):
    global NEW_IDX
    REG.clear()
    NEW_IDX = 300
    D = OPTIONS[opt]["deltas"] if opt else []
    plan = patch_plan(plan0, D)
    S = bh.build_scene(cfg, plan, a)
    sc = bpy.context.scene
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    notes = build_option(opt, plan) if opt else []
    wl = window_lights(plan)
    bpy.context.view_layer.update()
    return S, plan, notes, wl


def set_cam(S, C):
    bh.set_view(S["cam"], C["loc"], C["yaw"], C["u0"], C["v0"])


def run_option(opt, plan0, cfg, a, prop, rep, tmp):
    t0 = time.time()
    room = OPTIONS[opt]["room"]
    S, plan, notes, wl = build(opt, plan0, cfg, a)
    cams = prop_cams(prop)
    C = cams[OPTIONS[opt]["cam"]]
    C = dict(C, yaw=C["yaw"])
    cam = S["cam"]
    set_cam(S, C)
    lamp_objs = set_lamps(OPTIONS[opt]["lamps"])
    p = os.path.join(OUT, f"{opt}.png")
    depth, idx, normal = render(p, os.path.join(tmp, "p"), a.res, a.samples, ao=0.30)
    est = est_rows(opt, S, cam, C, idx)
    acc = acceptance(opt, S, cam, C, idx, depth, plan, est)
    R = dict(option=opt, room=room, camera=C, deltas=OPTIONS[opt]["deltas"], image=f"framing/{opt}.png",
             build_notes=notes, lamps_on=OPTIONS[opt]["lamps"], mean_L_editorial=mean_L(p), est_vs_measured=est,
             est_flags=[r["key"] for r in est if r["flag_gt_tol"]], acceptance=acc,
             camera_clearance_m=None)
    obs = bh.obstacles()
    cl = min((bh.rect_dist(C["loc"][:2], r[:4]), r[4]) for r in obs)
    R["camera_clearance_m"] = dict(min=r4(cl[0]), nearest=cl[1])
    # extra passes
    os.makedirs(os.path.join(OUT, "extra"), exist_ok=True)
    if room in ("hall", "corridor"):
        for o in wl:
            o.hide_render = True
        mat_obj = M["curtain"]
        unglow(lamp_objs, mat_obj)
        fp = os.path.join(OUT, "extra", f"{opt}-skyonly.png")
        render(fp, os.path.join(tmp, "p"), int(960 * a.xs), max(2, int(32 * a.xs)), ao=0.0, passes=False, exposure=a.exposure)
        L = mean_L(fp)
        R["acceptance"]["F7"] = dict(result="pass" if L >= 95 else "fail", mean_L_sky_and_rooflight_only=L, min=95,
                                     image=f"framing/extra/{opt}-skyonly.png",
                                     note="sky + opal roof light (radiance 0.55 x sky), no window boost, no lamps, no AO; 960 px")
        for o in wl:
            o.hide_render = False
        pr = set_lamps(["hall-practicals" if room == "hall" else "corridor-practicals"], 12.0)
        fp = os.path.join(OUT, "extra", f"{opt}-practicals2700K.png")
        render(fp, os.path.join(tmp, "p"), int(1280 * a.xs), max(2, int(48 * a.xs)), ao=0.30, passes=False)
        R["practicals_pass"] = dict(image=f"framing/extra/{opt}-practicals2700K.png", mean_L=mean_L(fp),
                                    lamps=[o.name for o in pr])
        unglow(pr, M["curtain"] if room == "hall" else M["obj"])
        lamp_objs = set_lamps(OPTIONS[opt]["lamps"])
    else:
        R["acceptance"]["F7"] = dict(result="n/a (hall and corridor only)")
    if room == "bath":
        mr = mirror_reflection(cam)
        R["acceptance"]["F8"] = dict(result="pass" if mr["ok"] else "fail", **mr,
                                     note="ray-cast reflection pass: 40x40 grid on the mirror, reflected camera rays; designer est: south wall Y 10.39-12.79, Z 1.1-2.45")
        from PIL import Image
        b = group_bbox(idx, G("U6 mirror"))
        if b:
            im = Image.open(p)
            Wp, Hp = im.size
            pad = 0.03
            crop = im.crop((int(max(0, b[0] - pad) * Wp), int(max(0, b[2] - pad) * Hp), int(min(1, b[1] + pad) * Wp), int(min(1, b[3] + pad) * Hp)))
            crop = crop.resize((crop.width * 2, crop.height * 2))
            crop.save(os.path.join(OUT, "extra", f"{opt}-mirror-crop.png"))
            R["acceptance"]["F8"]["crop"] = f"framing/extra/{opt}-mirror-crop.png"
    else:
        R["acceptance"]["F8"] = dict(result="n/a (no mirror)")
    # F9 transitions
    tr = []
    END = {"E0'": dict(loc=[1.25, 5.55, 1.20]), "T-HC'": dict(loc=[2.397, 17.11, 1.20])}
    for tid in TRANS_FOR.get(opt, []):
        tr.append(check_transition(prop, tid, plan, obs, END.get(tid, C)))
    okj = [t["ok"] for t in tr if t["ok"] is not None]
    R["acceptance"]["F9"] = dict(result=("n/a (frame-only option; transitions unchanged)" if not tr else
                                         ("pass (jambs; end pose; play time = designer estimate, not measured)" if all(okj) and all(
                                             (t["end"] is None or t["end"]["pos_err_m"] <= 0.005) for t in tr) else "fail")),
                                 transitions=tr)
    # sweep strip
    sw = C.get("sweep")
    if sw and not a.no_sweeps:
        R["sweep"] = sweep_strip(opt, S, C, sw, tmp)
    # overlay
    os.makedirs(os.path.join(OUT, "overlays"), exist_ok=True)
    make_overlay(p, os.path.join(OUT, "overlays", f"{opt}.png"), f"{opt} ({room})  cam {C['loc']} yaw {C['yaw']} u0 {C['u0']} v0 {C['v0']}",
                 est, acc["F1"]["heroes"])
    R["overlay"] = f"framing/overlays/{opt}.png"
    R["runtime_s"] = round(time.time() - t0)
    rep.setdefault("options", {})[opt] = R
    return R


def sweep_strip(opt, S, C, sw, tmp):
    from PIL import Image
    tiles = []
    for key, (lo, hi) in sw.items():
        for k in range(5):
            val = lo + (hi - lo) * k / 4
            c = dict(C)
            loc = list(C["loc"])
            if key == "yaw":
                c["yaw"] = val
            elif key == "v0":
                c["v0"] = val
            elif key == "z":
                loc[2] = val
            elif key == "y":
                loc[1] = val
            c["loc"] = loc
            set_cam(S, c)
            fp = os.path.join(tmp, f"sw_{key}_{k}.png")
            render(fp, os.path.join(tmp, "p"), 640, 24, ao=0.3, passes=False)
            tiles.append((Image.open(fp).convert("RGB"), f"{key} = {val:.3f}"))
    set_cam(S, C)
    outp = os.path.join(OUT, "extra", f"{opt}-sweep.jpg")
    bh.make_sheet(tiles, f"{opt} sweep {sw} (5 frames per range, 640 px)", outp, cols=5)
    return f"framing/extra/{opt}-sweep.jpg"


def run_current(room, plan0, cfg, a, rep, tmp):
    """The approved plan camera and geometry, rendered with the same editorial light (fair comparison)."""
    S, plan, notes, wl = build(None, plan0, cfg, a)
    cams = bh.cams_from_plan(plan0)
    C = cams[ROOM_CUR[room]]
    set_cam(S, C)
    lamp_objs = set_lamps(["hall-console"] if room == "hall" else [])
    p = os.path.join(OUT, f"current-{room}.png")
    render(p, os.path.join(tmp, "p"), a.res, a.samples, ao=0.30, passes=False)
    R = dict(room=room, camera=C, image=f"framing/current-{room}.png", mean_L_editorial=mean_L(p))
    if room in ("hall", "corridor"):
        for o in wl:
            o.hide_render = True
        unglow(lamp_objs, M["curtain"])
        fp = os.path.join(OUT, "extra", f"current-{room}-skyonly.png")
        render(fp, os.path.join(tmp, "p"), int(960 * a.xs), max(2, int(32 * a.xs)), ao=0.0, passes=False, exposure=a.exposure)
        R["mean_L_sky_only"] = mean_L(fp)
    rep.setdefault("current", {})[room] = R
    return R


# ---------------------------------------------------------------------------------------------------------------
# sheets
# ---------------------------------------------------------------------------------------------------------------
LABEL = {"current": "CURRENT (plan 1.0)"}


def tile(path, w, label, sub=""):
    from PIL import Image, ImageDraw
    if path and os.path.exists(path):
        im = Image.open(path).convert("RGB").resize((w, int(w * 9 / 16)), Image.LANCZOS)
    else:
        im = Image.new("RGB", (w, int(w * 9 / 16)), (230, 228, 224))
        d = ImageDraw.Draw(im)
        d.text((20, im.height // 2 - 10), sub or "not rendered", fill=(90, 90, 90), font=ba.font(20, bold=False))
        sub = ""
    d = ImageDraw.Draw(im, "RGBA")
    f = ba.font(24)
    fs = ba.font(17, bold=False)
    tw = max(d.textlength(label, font=f), d.textlength(sub, font=fs) if sub else 0)
    d.rectangle((0, 0, tw + 20, 64 if sub else 38), fill=(255, 255, 255, 225))
    d.text((10, 6), label, fill=(15, 15, 15), font=f)
    if sub:
        d.text((10, 38), sub, fill=(60, 60, 60), font=fs)
    return im


def compare_sheet(room, rep):
    from PIL import Image, ImageDraw
    w = 900
    opts = ROOM_OPTS[room]
    cols = [("current", os.path.join(OUT, f"current-{room}.png"), os.path.join(HERE, f"{room}-clay.png"))]
    for o in opts:
        cols.append((o, os.path.join(OUT, f"{o}.png"), os.path.join(OUT, "overlays", f"{o}.png")))
    if room == "kitchen-dining":
        cols.append(("D-B (rejected by the designer)", None, None))
    row1, row2 = [], []
    for name, p, ov in cols:
        if name == "current":
            c = rep.get("current", {}).get(room, {})
            row1.append(tile(p, w, f"CURRENT  {ROOM_CUR[room]}", "plan 1.0 camera, same light"))
            row2.append(tile(ov, w, "CURRENT  original plan clay (sky only)", "assets/blockout/house/" + f"{room}-clay.png"))
            continue
        if p is None:
            row1.append(tile(None, w, name, "not rendered: needs yaw -90 + 2 more pans (proposal 3.2)"))
            row2.append(tile(None, w, name, " "))
            continue
        o = rep.get("options", {}).get(name, {})
        acc = o.get("acceptance", {})
        fails = [k for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9") if str(acc.get(k, {}).get("result", "")).startswith("fail")]
        pick = "  [designer's pick]" if PICKS.get(room) == name else ""
        sub = ("all F-checks pass" if not fails else "fails: " + ", ".join(fails)) + f"  |  est flags: {len(o.get('est_flags', []))}"
        row1.append(tile(p, w, f"{name}{pick}", sub))
        row2.append(tile(ov, w, f"{name}  overlay (thirds, est vs measured)", ""))
    n = len(cols)
    th = int(w * 9 / 16)
    pad, head = 10, 60
    sheet = Image.new("RGB", (n * (w + pad) + pad, head + 2 * (th + pad) + pad), (246, 245, 242))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 14), f"{room}: current | options  (top: clay with the same editorial light; bottom: overlays / original clay)",
           fill=(15, 15, 15), font=ba.font(28))
    for k, (a1, a2) in enumerate(zip(row1, row2)):
        sheet.paste(a1, (pad + k * (w + pad), head))
        sheet.paste(a2, (pad + k * (w + pad), head + th + pad))
    outp = os.path.join(OUT, f"{room}-compare.jpg")
    sheet.save(outp, quality=88)
    return outp


def picks_sheet(rep):
    from PIL import Image, ImageDraw
    w = 900
    th = int(w * 9 / 16)
    rooms = list(ROOM_OPTS)
    cols = 2
    rows = math.ceil(len(rooms) / cols)
    pad, head = 10, 60
    sheet = Image.new("RGB", (cols * (2 * w + pad) + (cols + 1) * pad, head + rows * (th + pad) + pad), (246, 245, 242))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 14), "Designer's recommended pick per room (right) vs current (left); same editorial clay light", fill=(15, 15, 15), font=ba.font(28))
    for k, room in enumerate(rooms):
        o = PICKS[room]
        acc = rep.get("options", {}).get(o, {}).get("acceptance", {})
        fails = [f for f in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9") if str(acc.get(f, {}).get("result", "")).startswith("fail")]
        x = pad + (k % cols) * (2 * w + 2 * pad)
        y = head + (k // cols) * (th + pad)
        sheet.paste(tile(os.path.join(OUT, f"current-{room}.png"), w, f"{room}: current {ROOM_CUR[room]}"), (x, y))
        sheet.paste(tile(os.path.join(OUT, f"{o}.png"), w, f"{room}: {o}", "all F-checks pass" if not fails else "fails: " + ", ".join(fails)),
                    (x + w + pad // 2, y))
    outp = os.path.join(OUT, "all-picks.jpg")
    sheet.save(outp, quality=88)
    return outp


# ---------------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------------
def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--framing", required=True)
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--no-sweeps", action="store_true")
    ap.add_argument("--xs", type=float, default=1.0, help="scale of the extra passes (smoke tests)")
    ap.add_argument("--no-current", action="store_true")
    a, _ = ap.parse_known_args(argv)
    os.makedirs(OUT, exist_ok=True)
    plan_path, plan0 = bh.load_plan()
    spec = json.load(open(b4.SPEC_PATH))
    cfg = b4.v4_config(spec)
    prop = load_prop()
    sc_path = os.path.join(OUT, "selfcheck.json")
    rep = json.load(open(sc_path)) if os.path.exists(sc_path) else {}
    rep.update(proposal="docs/proposals/house-framing.json " + prop["version"], plan=os.path.relpath(plan_path, REPO),
               plan_version=plan0["version"], render=f"{a.res}x{int(a.res * 9 / 16)}, {a.samples} samples, Cycles CPU seed 7, AgX Medium High Contrast, exposure {a.exposure}",
               light="sky (strength %.1f) as the plan clays + soft area light outside every window (camera-invisible) + opal roof lights (radiance %.2f x sky) + 2700 K lamp glows where the proposal calls them on + AO multiply 0.30 (0.35 m)" % (a.sky, OPAL_T))
    tmp = tempfile.mkdtemp(prefix="framing-")
    sel = a.framing
    if sel == "all":
        todo = list(ROOM_OPTS)
    elif sel in ROOM_OPTS:
        todo = [sel]
    elif sel == "sheets":
        todo = []
    else:
        todo = None
    def save():
        json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)
    if todo is None:
        for o in sel.split(","):
            run_option(o, plan0, cfg, a, prop, rep, tmp)
            save()
            print("option", o, flush=True)
    else:
        for room in todo:
            if not a.no_current:
                run_current(room, plan0, cfg, a, rep, tmp)
                save()
                print("current", room, flush=True)
            for o in ROOM_OPTS[room]:
                run_option(o, plan0, cfg, a, prop, rep, tmp)
                save()
                print("option", o, flush=True)
            compare_sheet(room, rep)
    if sel in ("all", "sheets") or sel in ROOM_OPTS:
        for room in ROOM_OPTS:
            if os.path.exists(os.path.join(OUT, f"current-{room}.png")):
                compare_sheet(room, rep)
        picks_sheet(rep)
    save()
