#!/usr/bin/env python3
"""
framing_wm_door_final.py: the FINAL warm-modern entrance as a clay (ENT2: M3 "the built bench" with M2's stone door wall, no sidelight),
render-agent, 2026-11-16. Brief: briefs/wm-door-final-d0-2026-11-16.md, step 1. 0 var2 tokens.
Source: master-designer docs/proposals/wm-entrance-magazine-2026-11-15.md chapter 11 (11.2 the clay changes; 11.1 the D0 spec; 11.5 inside).

The scene is framing_wm_door.py exactly (the court, the door, the S1 cameras, the canvases, the passes), plus, here:
  a. the door wall X 3.95 (Y 6.55-9.60, Z 0-3.00) in honed limestone #D8C8AE: 11 courses (40/30/15/40/20/15/40/15/25/40/20 cm), joints
     5 mm wide and 5 mm deep, head joints at Y 7.05 in courses 2, 4, 6, 8 and at Y 7.30 / 9.30 in course 10 (course 11: Y 8.05, above every
     frame); the finished face stays on X 3.95 (the wall solid is cut back 5 mm behind the stone, the joints show it); the stone wraps the
     jambs and the head to the leaf line X 3.66 with every horizontal joint, sharp corners (the 3 cm fillets are gone); a 5 mm shadow groove
     where the plaster side walls meet the stone; 10 mm gap at the court ceiling; 5 mm joint at the floor; the 1 cm dark foot line leaves this
     wall and the jambs; the leaf: 48 vertical rounded flutes (pitch 20, depth 4, 20 mm flat margins), walnut #6B4A33 (Y 0.083);
  b. one built body on the right wall (Y 6.55), front line Y 7.05: the planter X 3.95-4.75 (plaster body to Z 0.62, limestone rim 8 x 8 cm on
     four sides, soil at Z 0.65) and the bench X 4.75-6.40 (plaster base to Z 0.37, face Y 7.03, limestone seat Z 0.37-0.45 to Y 7.05);
     a 3 x 3 cm shadow recess at the floor under both; the herbs as five grey-green displaced volumes, top <= Z 1.15; the wall light
     (porch-wall-light): cylinder d 100 x 250 on a 15 mm round plate, centre (4.02, 7.40, 1.80), two 2700 K spots up / down (25 deg),
     lit in every court frame; the doormat (porch-doormat) 0.60 x 0.90 x 0.015 at X 3.95-4.55, Y 7.85-8.75, coir albedo #A88B64;
  c. the sun (azimuth 228 from north clockwise, altitude 21, angle 1.5, 4000 K) added to the clay's sky (unchanged), and an olive out of
     every frame: a crown of leaf cards (5 x 1.2 cm leaves in twig clusters) centred (8.20, 10.00), d 3.0, Z 1.8-4.0, trunk d 0.25;
  d. inside: a limestone panel on the hall's far wall, face X 0.81 (10 mm proud), Y 6.35-7.75, Z 0-3.00, the porch courses, head joints at
     Y 7.05 in courses 2, 4, 6, 8, a clean return at Y 7.75, no skirting on it (the plaster skirtings stop 5 mm short); RL-hall out, the
     slot RL-hall-slot in: X 0.80-1.10, Y 6.35-9.80, well 0.45, opal; the jib door, skirtings and oak unchanged.
Frames, cameras, canvases and passes: framing_wm_door.py (D0-closed / -none / -open, HD, HDx, HD57, HT, c1/S00..S11). Extra: -sun.png for
the D0 frames (direct sun only, 8 bit, 255 = in direct sun), and the scene-linear beauty of every frame as EXR in the scratchpad.

  python3 framing_wm_door_final.py --frames all
  python3 framing_wm_door_final.py --frames D0-closed --res 1360 --samples 8 --out /tmp/x       # a quick look
  python3 framing_wm_door_final.py --reclassify                                                  # id + edges again, no render
Then: python3 framing/wm-door-2026-11-16/checks_wm_door_final.py
"""
import argparse
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_ARGV = sys.argv[1:]
sys.argv = [sys.argv[0]]

import framing_wm_door as D  # noqa: E402  (the 2026-11-14 court + door clay; unchanged)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

E, W4, fr, bh, bs, M = D.E, D.W4, D.fr, D.bh, D.bs, D.M

OUT = os.path.join(HERE, "framing", "wm-door-2026-11-16")
SCRATCH = os.path.join(W4.SCRATCH, "wm-door-final")
E.SCRATCH = SCRATCH
D.SCRATCH = SCRATCH

# ---- chapter 11 numbers -------------------------------------------------------------------------------------------------------------
COURSES = [(0.00, 0.40), (0.40, 0.70), (0.70, 0.85), (0.85, 1.25), (1.25, 1.45), (1.45, 1.60), (1.60, 2.00), (2.00, 2.15), (2.15, 2.40),
           (2.40, 2.80), (2.80, 3.00)]
HEADS_COURT = {2: [7.05], 4: [7.05], 6: [7.05], 8: [7.05], 10: [7.30, 9.30], 11: [8.05]}    # course 11 is free (designer); above every frame
HEADS_HALL = {2: [7.05], 4: [7.05], 6: [7.05], 8: [7.05]}
J = 0.0025                                   # half a joint (5 mm wide)
RELIEF = 0.005                               # joint depth
STONE_HEX, JOINT_HEX = "#D8C8AE", "#8F826F"
X_FACE, X_LEAF = 3.95, 3.66
PLANTER = dict(x=(3.95, 4.75), y=(6.55, 7.05), h=0.70, rim=0.08, rim_t=0.08, soil=0.65, body_face=7.03)
BENCH = dict(x=(4.75, 6.40), y=(6.55, 7.05), seat=0.45, slab=0.08, body_face=7.03, recess=0.03)
LAMP = dict(c=(4.02, 7.40, 1.80), d=0.100, h=0.250, plate_t=0.015, plate_d=0.080, beam_deg=25.0, tilt_deg=10.0, kelvin=2700)
MAT = dict(x=(3.95, 4.55), y=(7.85, 8.75), t=0.015, hex="#A88B64")
SUN = dict(az=228.0, alt=21.0, angle=1.5, kelvin=4000)
OLIVE = dict(c=(8.20, 10.00), d=3.0, z=(1.8, 4.0), trunk_d=0.25, leaf=(0.05, 0.012), clusters=90, per_cluster=100, cluster_r=0.26, seed=228,
             trunk_offset=0.60)                       # the trunk stands 0.60 m off the crown axis, across the sun (see olive())
PANEL = dict(x_face=0.81, y=(6.35, 7.75), z=(0.0, 3.00))
SLOT = dict(x=(0.80, 1.10), y=(6.35, 9.80), well=0.45, ceiling=3.00)
FLUTES = dict(n=48, pitch=0.020, depth=0.004, width=0.014, margin=0.020)
PX = dict(stone=720, joint=722, planter=723, bench=724, cap=725, herbs=726, lamp=727, soil=728, mat=729, panel=730, slot=731, olive=732,
          recess=733, glow=734)
NEW_IDS = {84: "door wall, limestone face (X 3.95)", 85: "door reveal, limestone (jambs + head, X 3.66-3.95)",
           86: "limestone joints (5 mm recess; court and hall panel)", 87: "built planter, plaster body", 88: "built bench, plaster base",
           89: "limestone caps (planter rim, bench seat)", 90: "herbs (rosemary + lavender volume)", 91: "wall light porch-wall-light (body + lit diffusers)",
           92: "planter soil", 93: "doormat porch-doormat (coir)", 94: "hall limestone panel (X 0.81)", 95: "hall roof-light slot (well + opal)",
           96: "olive (must be 0 px)", 97: "shadow recesses (bench / planter foot, stone-to-plaster grooves)"}
NEW_PAL = {84: (216, 200, 174), 85: (196, 178, 150), 86: (120, 105, 85), 87: (240, 232, 220), 88: (232, 222, 208), 89: (226, 214, 190),
           90: (120, 150, 110), 91: (255, 170, 60), 92: (80, 60, 45), 93: (168, 139, 100), 94: (205, 190, 165), 95: (255, 255, 200), 96: (0, 120, 0),
           97: (60, 50, 40)}
LIGHTS = dict(sun=None, spots=[], glow_mats=[], slot_mat=None)


def setup_ids():
    D.IDS.update(NEW_IDS)
    E.IDS.update(NEW_IDS)
    D.IDS[61] = "door wall, plaster (none left after ch. 11)"
    E.IDS[61] = D.IDS[61]
    D.IDS[64] = "door reveal, plaster behind the leaf line (X 3.60-3.66)"
    E.IDS[64] = D.IDS[64]
    E.PALETTE.update(NEW_PAL)
    E.ALLOWED.update(set(NEW_IDS) - {96})


# ---------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------
def wbb(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return [min(c[i] for c in cs) for i in range(3)], [max(c[i] for c in cs) for i in range(3)]


def expect_box(name, lo, hi):
    ob = bpy.data.objects[name]
    a, b = wbb(ob)
    assert all(abs(x - y) < 1e-3 for x, y in zip(a + b, list(lo) + list(hi))), (name, a, b)
    return ob


def bx(name, x0, x1, y0, y1, z0, z1, mat, pidx, group="shell", bevel=0.0):
    assert x1 - x0 > 1e-6 and y1 - y0 > 1e-6 and z1 - z0 > 1e-6, (name, x0, x1, y0, y1, z0, z1)
    return bs.box(name, x0, x1, y0, y1, z0, z1, mat, group, bevel=bevel, seg=3, pidx=pidx)


def emission(name, kelvin, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    bb = nt.nodes.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = kelvin
    nt.links.new(bb.outputs[0], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def light_blackbody(light, kelvin):
    light.use_nodes = True
    nt = light.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    bb = nt.nodes.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = kelvin
    nt.links.new(bb.outputs[0], em.inputs["Color"])


def courses_z(k, n, top_gap):
    """Bottom and top of the stone of course k (1-based) of n: a 5 mm joint at the floor, half joints between courses, top_gap at the top."""
    z0, z1 = COURSES[k - 1]
    return z0 + (2 * J if k == 1 else J), z1 - (top_gap if k == n else J)


def split(ya, yb, cuts, edge_joint=(False, False)):
    """[ya, yb] cut at the head joints: the stone pieces, a half joint on each side of a cut."""
    e = [ya] + [c for c in cuts if ya + 1e-6 < c < yb - 1e-6] + [yb]
    out = []
    for i in range(len(e) - 1):
        a = e[i] + (J if (i > 0 or edge_joint[0]) else 0.0)
        b = e[i + 1] - (J if (i < len(e) - 2 or edge_joint[1]) else 0.0)
        out.append((a, b))
    return out


# ---------------------------------------------------------------------------------------------------------------
# a. the door wall and the leaf
# ---------------------------------------------------------------------------------------------------------------
def door_wall_stone():
    notes = []
    wall = M["wall"]
    stone = fr.mat_cache("limestone_wall_ch11", STONE_HEX, 0.75)
    joint = fr.mat_cache("limestone_joint_ch11", JOINT_HEX, 0.95)
    sg = M["shadow_gap"]
    expect_box("hwall_53", (3.60, 6.55, -0.12), (3.95, 7.80, 3.15))
    expect_box("hwall_54", (3.60, 8.80, -0.12), (3.95, 9.60, 3.15))
    expect_box("hwall_55", (3.60, 7.80, 2.40), (3.95, 8.80, 3.15))
    gone = fr.kill("hwall_53", "hwall_54", "hwall_55", "reveal_fillet_a", "reveal_fillet_b", "court_foot_door_wall_a", "court_foot_door_wall_b",
                   "court_foot_jamb_a", "court_foot_jamb_b")
    notes.append(f"removed {gone}")
    xb = X_FACE - RELIEF
    hw = bh.IDX["wall"]
    # the wall solid: plaster behind the leaf line (X 3.60-3.66, the hall side and the 6 cm the leaf covers), and behind the stone the
    # joint-coloured core, cut back 5 mm from X 3.95 and from the reveal planes
    bx("dw_inner_r", 3.60, X_LEAF, 6.55, 7.80, -0.12, 3.15, wall, hw)
    bx("dw_inner_l", 3.60, X_LEAF, 8.80, 9.60, -0.12, 3.15, wall, hw)
    bx("dw_inner_h", 3.60, X_LEAF, 7.80, 8.80, 2.40, 3.15, wall, hw)
    bx("dw_core_r", X_LEAF, xb, 6.55, 7.80 - RELIEF, -0.12, 3.15, joint, PX["joint"])
    bx("dw_core_l", X_LEAF, xb, 8.80 + RELIEF, 9.60, -0.12, 3.15, joint, PX["joint"])
    bx("dw_core_h", X_LEAF, xb, 7.80 - RELIEF, 8.80 + RELIEF, 2.40 + RELIEF, 3.15, joint, PX["joint"])
    n = 0
    nC = len(COURSES)
    for k in range(1, nC + 1):
        za, zb = courses_z(k, nC, 0.010)
        z0, _ = COURSES[k - 1]
        spans = [(6.55, 9.60)] if z0 >= 2.40 - 1e-9 else [(6.55, 7.80), (8.80, 9.60)]
        for (ya, yb) in spans:
            for (a, b) in split(ya, yb, HEADS_COURT.get(k, [])):
                bx(f"dw_stone_{k}_{n}", xb, X_FACE, a, b, za, zb, stone, PX["stone"])
                n += 1
        if k == 10:                                                     # over the opening the head's arris is not a joint
            bx("dw_stone_10_over_door", xb, X_FACE, 7.80, 8.80, 2.40, za, stone, PX["stone"])
        if k <= 9:                                                      # the reveal: jambs to the leaf line, every joint wraps
            zt = 2.40 if k == 9 else zb
            bx(f"dw_jamb_r_{k}", X_LEAF, xb, 7.80 - RELIEF, 7.80, za, zt, stone, PX["stone"])
            bx(f"dw_jamb_l_{k}", X_LEAF, xb, 8.80, 8.80 + RELIEF, za, zt, stone, PX["stone"])
            n += 2
    bx("dw_head_soffit", X_LEAF, xb, 7.80 - RELIEF, 8.80 + RELIEF, 2.40, 2.40 + RELIEF, stone, PX["stone"])
    notes.append(f"door wall: {n} limestone pieces {STONE_HEX} on X {xb}-{X_FACE} (face on X {X_FACE}), 11 courses {[round(b - a, 2) for a, b in COURSES]}, "
                 f"joints 5 x 5 mm, head joints {HEADS_COURT}; the reveal in the same stone to X {X_LEAF} with every horizontal joint, "
                 f"the head one stone, sharp corners; core behind the stone in joint colour {JOINT_HEX}")
    # the plaster side walls stop 5 mm short of the stone: a 5 mm shadow groove, 1.5 mm proud (as the 1 cm foot line)
    e = 0.0015
    bx("groove_right", X_FACE, X_FACE + 0.005, 6.55, 6.55 + e, PLANTER["h"], 3.00, sg, PX["recess"])
    bx("groove_left_lo", X_FACE, X_FACE + 0.005, 9.60 - e, 9.60, 0.01, 0.975, sg, PX["recess"])
    bx("groove_left_hi", X_FACE, X_FACE + 0.005, 9.60 - e, 9.60, 2.15, 3.00, sg, PX["recess"])
    notes.append("5 mm shadow grooves where the side walls meet the stone (right: above the planter; left: below and above the bath window); "
                 "the 1 cm dark foot line stays on the side walls only; the reveal fillets (r 3 cm) are gone")
    return notes


def fluted_leaf():
    """The leaf again, with 48 vertical rounded flutes on its court face (X 3.66), parented to the hinge like the old one."""
    old = bpy.data.objects["wm_front_leaf"]
    mat = old.data.materials[0]
    root = D.LEAF["root"]
    assert abs(root.rotation_euler[2]) < 1e-9
    y0, y1 = D.DOOR["y0"] + 0.001, D.DOOR["y1"] - 0.001
    xi, xo = D.DOOR["x_in"], D.DOOR["x_leaf"]
    f = FLUTES
    span = (y1 - y0) - 2 * f["margin"]
    pitch = span / f["n"]
    r = (f["width"] ** 2 / 4 + f["depth"] ** 2) / (2 * f["depth"])            # arc radius of a groove
    pts = [(xi, y0), (xo, y0)]
    seg = 8
    for k in range(f["n"]):
        c = y0 + f["margin"] + (k + 0.5) * pitch
        a, b = c - f["width"] / 2, c + f["width"] / 2
        pts.append((xo, a))
        th = math.asin((f["width"] / 2) / r)
        for i in range(1, seg):
            t = -th + 2 * th * i / seg
            pts.append((xo - (r * math.cos(t) - (r - f["depth"])), c + r * math.sin(t)))
        pts.append((xo, b))
    pts += [(xo, y1), (xi, y1)]
    z0, z1 = 0.001, D.DOOR["h"] - 0.001
    me = bpy.data.meshes.new("wm_front_leaf_fluted")
    nP = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [list(range(nP))[::-1], list(range(nP, 2 * nP))] + [(i, (i + 1) % nP, (i + 1) % nP + nP, i + nP) for i in range(nP)]
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new("wm_front_leaf_fluted", me)
    bs.coll("doors").objects.link(ob)
    ob.data.materials.append(mat)
    ob.pass_index = D.PIDX["leaf"]
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = root
    ob.matrix_parent_inverse = root.matrix_world.inverted()
    ob.matrix_world = mw
    D.LEAF["objs"] = [o for o in D.LEAF["objs"] if o.name != "wm_front_leaf"] + [ob]
    bpy.data.objects.remove(old, do_unlink=True)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    c = bsdf.inputs["Base Color"].default_value
    Y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    return [f"leaf: {f['n']} vertical rounded flutes, pitch {pitch * 1000:.2f} mm, groove {f['width'] * 1000:.0f} mm wide x {f['depth'] * 1000:.0f} mm deep "
            f"(arc r {r * 1000:.1f} mm), {f['margin'] * 1000:.0f} mm flat margins, full height; walnut material '{mat.name}' base colour linear "
            f"({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}) = #6B4A33, luminance Y {Y:.4f} (the designer's real-walnut albedo 0.083: already so in the 2026-11-14 "
            f"clay; its orange look was the AgX display curve on a bright sky-lit leaf, not the albedo)"]


# ---------------------------------------------------------------------------------------------------------------
# b. the built body, the herbs, the wall light, the doormat
# ---------------------------------------------------------------------------------------------------------------
def built_body():
    wall, sg = M["wall"], M["shadow_gap"]
    stone = fr.mat_cache("limestone_wall_ch11", STONE_HEX, 0.75)
    soil = fr.mat_cache("planter_soil", "#4B3D31", 1.0)
    P, B = PLANTER, BENCH
    (px0, px1), (py0, py1) = P["x"], P["y"]
    r, rt = P["rim"], P["rim_t"]
    rec = B["recess"]
    # the planter: plaster body (face Y 7.03, as the bench), rim 8 x 8 in limestone flush at the front line Y 7.05, soil at Z 0.65
    bx("planter_body", px0, px1, py0, P["body_face"], rec, P["h"] - rt, wall, PX["planter"], bevel=0.01)
    bx("planter_foot", px0, px1, py0, P["body_face"] - rec, 0.0, rec, sg, PX["recess"])
    zr = (P["h"] - rt, P["h"])
    bx("planter_rim_front", px0, px1, py1 - r, py1, *zr, stone, PX["cap"])
    bx("planter_rim_back", px0, px1, py0, py0 + r, *zr, stone, PX["cap"])
    bx("planter_rim_wall", px0, px0 + r, py0 + r, py1 - r, *zr, stone, PX["cap"])
    bx("planter_rim_bench", px1 - r, px1, py0 + r, py1 - r, *zr, stone, PX["cap"])
    bx("planter_soil", px0 + r, px1 - r, py0 + r, py1 - r, P["h"] - rt - 0.04, P["soil"], soil, PX["soil"])
    # the bench: plaster base to Z 0.37 (face Y 7.03), limestone seat Z 0.37-0.45 to Y 7.05 (2 cm proud), 3 x 3 cm recess at the floor
    (bx0, bx1), (by0, by1) = B["x"], B["y"]
    zs = B["seat"] - B["slab"]
    bx("bench_body", bx0, bx1, by0, B["body_face"], rec, zs, wall, PX["bench"], bevel=0.01)
    bx("bench_foot", bx0, bx1, by0, B["body_face"] - rec, 0.0, rec, sg, PX["recess"])
    bx("bench_seat", bx0, bx1, by0, by1, zs, B["seat"], stone, PX["cap"])
    return [f"planter: plaster X {px0}-{px1}, Y {py0}-{P['body_face']}, Z {rec}-{P['h'] - rt}; limestone rim {r * 100:.0f} x {rt * 100:.0f} cm on four "
            f"sides (Z {P['h'] - rt:.2f}-{P['h']}), its front at Y {py1}; soil at Z {P['soil']} in {px1 - px0 - 2 * r:.2f} x {py1 - py0 - 2 * r:.2f}",
            f"bench: plaster base X {bx0}-{bx1}, face Y {B['body_face']}, to Z {zs:.2f}; limestone seat Z {zs:.2f}-{B['seat']} to Y {by1} (2 cm proud, "
            f"its shadow line under it); free seat {bx1 - bx0:.2f} m, nothing on it",
            f"a {rec * 100:.0f} x {rec * 100:.0f} cm shadow recess at the floor under the planter and the bench (one body, one foot line; the "
            f"designer names it for the bench, the clay runs it on under the planter so the front line does not step at X 4.75)"]


def herbs():
    mat = fr.mat_cache("herbs_clay", "#7E8873", 0.95)
    specs = [("rosemary_a", (4.16, 6.75), (0.13, 0.11, 0.255), 0.885), ("rosemary_b", (4.43, 6.71), (0.12, 0.11, 0.245), 0.885),
             ("lavender_a", (4.29, 6.93), (0.16, 0.15, 0.17), 0.80), ("lavender_b", (4.60, 6.88), (0.17, 0.155, 0.16), 0.79),
             ("lavender_c", (4.61, 6.67), (0.14, 0.12, 0.15), 0.78)]
    top = 0.0
    lo_x, hi_x, hi_y = 9.0, 0.0, 0.0
    for i, (nm, (cx, cy), (rx, ry, rz), cz) in enumerate(specs):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
        off = Vector((17.3 * i, 5.1 * i, 2.7 * i))
        for v in bm.verts:
            p = v.co.copy()
            k = 1.0 + 0.10 * noise.noise(p * 2.6 + off) + 0.05 * noise.noise(p * 7.0 + off) + 0.025 * noise.noise(p * 16.0 + off)
            q = Vector((p.x * rx * k, p.y * ry * k, p.z * rz * k))
            z = cz + q.z
            v.co = Vector((cx + q.x, cy + q.y, max(z, PLANTER["soil"] - 0.01)))
        me = bpy.data.meshes.new("herb_" + nm)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("herb_" + nm, me)
        bs.coll("shell").objects.link(ob)
        ob.data.materials.append(mat)
        ob.pass_index = PX["herbs"]
        for p in me.polygons:
            p.use_smooth = True
        zs = [v.co.z for v in me.vertices]
        top = max(top, max(zs))
        hi_x = max(hi_x, max(v.co.x for v in me.vertices))
        lo_x = min(lo_x, min(v.co.x for v in me.vertices))
        hi_y = max(hi_y, max(v.co.y for v in me.vertices))
    return [f"herbs: 2 upright rosemary + 3 lavender volumes (displaced icospheres, grey-green {mat.name}), top Z {top:.3f} (limit 1.15), "
            f"X {lo_x:.3f}-{hi_x:.3f} (spill past the rim X 4.75: {max(0.0, hi_x - 4.75) * 100:.1f} cm), front Y {hi_y:.3f} (past Y 7.05: "
            f"{max(0.0, hi_y - 7.05) * 100:.1f} cm; limit 10)"]


def wall_light(spot_w, glow):
    L = LAMP
    cx, cy, cz = L["c"]
    bronze = fr.mat_cache("bronze_wm", "#3A322C", 0.45)
    r = L["d"] / 2
    z0, z1 = cz - L["h"] / 2, cz + L["h"] / 2
    body = bs.cone("lamp_body", cx, cy, z0, z1, r, r, bronze, "shell", verts=48, pidx=PX["lamp"])
    pl = bs.cone("lamp_plate", 0, 0, -L["plate_t"] / 2, L["plate_t"] / 2, L["plate_d"] / 2, L["plate_d"] / 2, bronze, "shell", verts=40, pidx=PX["lamp"])
    pl.location = (X_FACE + L["plate_t"] / 2, cy, cz)
    pl.rotation_euler = (0.0, math.pi / 2, 0.0)
    bx("lamp_arm", X_FACE + L["plate_t"], cx - r + 0.002, cy - 0.012, cy + 0.012, cz - 0.03, cz + 0.03, bronze, PX["lamp"])
    gm = emission("lamp_glow_2700", L["kelvin"], glow)
    LIGHTS["glow_mats"] = [gm]
    for nm, z in (("lamp_glow_bot", z0 - 0.0008), ("lamp_glow_top", z1 + 0.0008)):
        g = bs.cone(nm, cx, cy, z - 0.0007, z + 0.0007, r * 0.82, r * 0.82, gm, "shell", verts=40, pidx=PX["glow"])
        g.visible_shadow = False
    LIGHTS["spots"] = []
    t = math.radians(L["tilt_deg"])
    for nm, z, sgn in (("lamp_spot_up", z1 + 0.004, 1.0), ("lamp_spot_down", z0 - 0.004, -1.0)):
        ld = bpy.data.lights.new(nm, "SPOT")
        ld.energy = spot_w
        ld.spot_size = math.radians(L["beam_deg"])
        ld.spot_blend = 0.5
        ld.shadow_soft_size = 0.012
        light_blackbody(ld, L["kelvin"])
        ob = bpy.data.objects.new(nm, ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = (cx, cy, z)
        dv = Vector((-math.sin(t), 0.0, sgn * math.cos(t)))               # tilted 10 deg toward the stone (-X)
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = dv.to_track_quat("-Z", "Y")
        LIGHTS["spots"].append(ob)
    body.data.materials[0] = bronze
    return [f"wall light: bronze cylinder d {L['d'] * 1000:.0f} x {L['h'] * 1000:.0f} on a {L['plate_t'] * 1000:.0f} mm round plate d "
            f"{L['plate_d'] * 1000:.0f}, centre {L['c']}; two {L['kelvin']} K spots up / down, beam {L['beam_deg']} deg, tilted {L['tilt_deg']} deg "
            f"toward the stone, {spot_w} W each; lit diffusers at both ends (emission {glow}); lit in every frame"]


def set_lamp(spot_w=None, glow=None):
    for ob in LIGHTS["spots"]:
        if spot_w is not None:
            ob.data.energy = spot_w
        ob.hide_render = (spot_w == 0)
    if glow is not None:
        for m in LIGHTS["glow_mats"]:
            next(n for n in m.node_tree.nodes if n.type == "EMISSION").inputs["Strength"].default_value = glow


def doormat():
    m = fr.mat_cache("coir_mat", MAT["hex"], 1.0)
    bx("porch_doormat", MAT["x"][0], MAT["x"][1], MAT["y"][0], MAT["y"][1], 0.0, MAT["t"], m, PX["mat"])
    return [f"doormat: {MAT['x'][1] - MAT['x'][0]:.2f} x {MAT['y'][1] - MAT['y'][0]:.2f} x {MAT['t']} at X {MAT['x']}, Y {MAT['y']}, coir {MAT['hex']}"]


# ---------------------------------------------------------------------------------------------------------------
# c. the sun and the olive
# ---------------------------------------------------------------------------------------------------------------
def sun_vector(az, alt):
    """Unit vector toward the sun. Plan compass: north = -X, east = -Y, south = +X, west = +Y; azimuth from north, clockwise."""
    a, h = math.radians(az), math.radians(alt)
    nrt, est = Vector((-1.0, 0.0, 0.0)), Vector((0.0, -1.0, 0.0))
    hz = nrt * math.cos(a) + est * math.sin(a)
    return Vector((hz.x * math.cos(h), hz.y * math.cos(h), math.sin(h)))


def add_sun(strength, az=SUN["az"], alt=SUN["alt"]):
    ld = bpy.data.lights.new("sun_ch11", "SUN")
    ld.energy = strength
    ld.angle = math.radians(SUN["angle"])
    light_blackbody(ld, SUN["kelvin"])
    ob = bpy.data.objects.new("sun_ch11", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (-sun_vector(az, alt)).to_track_quat("-Z", "Y")
    LIGHTS["sun"] = ob
    return [f"sun: azimuth {az} (from north, clockwise; north = -X), altitude {alt}, angle {SUN['angle']} deg, {SUN['kelvin']} K, strength {strength}; "
            f"toward the sun {tuple(round(c, 4) for c in sun_vector(az, alt))}; the clay's sky unchanged"]


def set_sun(strength=None, az=None, alt=None):
    ob = LIGHTS["sun"]
    if strength is not None:
        ob.data.energy = strength
        ob.hide_render = strength == 0
    if az is not None or alt is not None:
        q = (-sun_vector(az if az is not None else SUN["az"], alt if alt is not None else SUN["alt"])).to_track_quat("-Z", "Y")
        ob.rotation_quaternion = q


def olive(c=None, **over):
    O = dict(OLIVE)
    O.update(over)
    if c is not None:
        O["c"] = c
    rnd = random.Random(O["seed"])
    cx, cy = O["c"]
    R = O["d"] / 2
    zc, rz = (O["z"][0] + O["z"][1]) / 2, (O["z"][1] - O["z"][0]) / 2
    lw, ww = O["leaf"]
    verts, faces = [], []
    centres = []
    while len(centres) < O["clusters"]:
        p = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if p.length <= 1.0:
            centres.append(Vector((cx + p.x * (R - O["cluster_r"]), cy + p.y * (R - O["cluster_r"]), zc + p.z * (rz - O["cluster_r"]))))
    for c0 in centres:
        for _ in range(O["per_cluster"]):
            q = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1)))
            q = q.normalized() * (abs(rnd.gauss(0, 0.5)) * O["cluster_r"])
            p = c0 + q
            a = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6))).normalized()      # leaf axis
            n = a.orthogonal().normalized()
            n.rotate(__import__("mathutils").Quaternion(a, rnd.uniform(0, math.pi)))
            s = a.cross(n).normalized()
            L_ = lw * rnd.uniform(0.8, 1.2)
            W_ = ww * rnd.uniform(0.8, 1.2)
            b = len(verts)
            verts += [tuple(p - a * L_ / 2 - s * W_ / 2), tuple(p + a * L_ / 2 - s * W_ / 2), tuple(p + a * L_ / 2 + s * W_ / 2),
                      tuple(p - a * L_ / 2 + s * W_ / 2)]
            faces.append((b, b + 1, b + 2, b + 3))
    me = bpy.data.meshes.new("olive_crown")
    me.from_pydata(verts, [], faces)
    leaf = fr.mat_cache("olive_leaf", "#5E6B4E", 0.9)
    ob = bpy.data.objects.new("olive_crown", me)
    bs.coll("shell").objects.link(ob)
    ob.data.materials.append(leaf)
    ob.pass_index = PX["olive"]
    bark = fr.mat_cache("olive_bark", "#6E665A", 0.95)
    # an olive leans: the trunk stands off the crown axis across the sun's azimuth, so its hard shadow runs past the court's right wall out of
    # the frame (under the crown it would draw a pole across the bench and the floor); it climbs into the crown
    sv = sun_vector(SUN["az"], SUN["alt"])
    perp = Vector((sv.y, -sv.x, 0.0)).normalized()
    tb = Vector((cx, cy, 0.0)) + perp * O["trunk_offset"]
    tr = bs.cone("olive_trunk", tb.x, tb.y, 0.0, O["z"][0] + 0.4, O["trunk_d"] / 2, O["trunk_d"] / 2 * 0.7, bark, "shell", verts=24, pidx=PX["olive"])
    LIGHTS["olive"] = [ob, tr]
    return [f"olive: {len(faces)} leaf cards {lw * 100:.0f} x {ww * 100:.1f} cm in {O['clusters']} twig clusters (r {O['cluster_r']}), crown centred "
            f"({cx}, {cy}), d {O['d']}, Z {O['z'][0]}-{O['z'][1]}; trunk d {O['trunk_d']} at ({tb.x:.2f}, {tb.y:.2f}) to Z {O['z'][0] + 0.4:.1f}, "
            f"{O['trunk_offset']} m off the crown axis across the sun (its shadow leaves the court's right wall at X > 5.8, out of every frame)"]


def move_olive(c, **over):
    for o in LIGHTS.get("olive", []):
        bpy.data.objects.remove(o, do_unlink=True)
    return olive(c, **over)


# ---------------------------------------------------------------------------------------------------------------
# d. inside: the stone panel and the slot
# ---------------------------------------------------------------------------------------------------------------
def hall_panel():
    stone = fr.mat_cache("limestone_wall_ch11", STONE_HEX, 0.75)
    joint = fr.mat_cache("limestone_joint_ch11", JOINT_HEX, 0.95)
    xf = PANEL["x_face"]
    xw = 0.80
    xb = xf - RELIEF
    ya, yb = PANEL["y"]
    bx("hp_core", xw, xb, ya, yb - RELIEF, PANEL["z"][0], PANEL["z"][1], joint, PX["joint"])
    n = 0
    nC = len(COURSES)
    for k in range(1, nC + 1):
        za, zb = courses_z(k, nC, 0.0)
        for (a, b) in split(ya, yb, HEADS_HALL.get(k, [])):
            bx(f"hp_stone_{k}_{n}", xb, xf, a, b, za, zb, stone, PX["panel"])
            n += 1
        bx(f"hp_return_{k}", xw, xb, yb - RELIEF, yb, za, zb, stone, PX["panel"])
    # skirtings stop 5 mm short of the stone
    out = []
    for nm, (x0, x1, y0, y1) in (("hall_skirt_x00", (0.80, 0.815, yb + 0.005, 8.10)), ("hall_skirt_y00", (xf + 0.005, 0.95, 6.35, 6.365))):
        old = bpy.data.objects[nm]
        mat = old.data.materials[0]
        pidx = old.pass_index
        lo, hi = wbb(old)
        out.append(f"{nm} {[round(v, 3) for v in lo]}-{[round(v, 3) for v in hi]} -> X {x0}-{x1}, Y {y0}-{y1}")
        bpy.data.objects.remove(old, do_unlink=True)
        ob = bs.box(nm, x0, x1, y0, y1, 0.0, 0.15, mat, "shell", pidx=pidx)
        bs.apply_scale(ob)
        bv = ob.modifiers.new("wmc10_bevel", "BEVEL")
        bv.width, bv.segments, bv.limit_method = 0.003, 2, "ANGLE"
    return [f"hall panel: {n} limestone pieces + {nC} returns, face X {xf} (10 mm proud of X 0.80), Y {ya}-{yb}, Z {PANEL['z'][0]}-{PANEL['z'][1]}, "
            f"the porch courses, head joints {HEADS_HALL}, joints 5 x 5 mm, no skirting on it; skirtings trimmed: {out}"]


def roof_slot(strength):
    gone = fr.kill("hall_ceilpc*", "well0a", "well0b", "well0c", "well0d", "wmh_cgap_x0")
    op = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("opal") and 0.80 <= wbb(o)[0][0] <= 1.0 and wbb(o)[1][1] < 9.0]
    assert len(op) == 1, [o.name for o in op]
    gone.append(op[0].name)
    bpy.data.objects.remove(op[0], do_unlink=True)
    (sx0, sx1), (sy0, sy1) = SLOT["x"], SLOT["y"]
    h, top = SLOT["ceiling"], SLOT["ceiling"] + SLOT["well"]
    wall = M["wall"]
    bx("hall_ceil_ch11", sx1, 3.60, 6.35, 9.80, h, bh.TOP, M["ceiling"], bh.IDX["ceiling"], group="ceiling")
    t = 0.04
    bx("slot_well_side", sx1, sx1 + t, sy0, sy1, bh.TOP, top, wall, PX["slot"])          # X 1.10 face: the slab's edge below TOP
    bx("slot_well_far", sx0 - t, sx0, sy0, sy1, bh.TOP, top, wall, PX["slot"])           # X 0.80 face: the hall wall below TOP
    bx("slot_well_front", sx0 - t, sx1 + t, sy0 - t, sy0, h, top, wall, PX["slot"])      # Y 6.35: the front wall stops at Z 3.00
    bx("slot_well_back", sx0 - t, sx1 + t, sy1, sy1 + t, bh.TOP, top, wall, PX["slot"])  # Y 9.80: hwall_25 to TOP
    m = fr.emission_mat("opal_slot_ch11", fr.SKY_COL, strength)
    LIGHTS["slot_mat"] = m
    bx("slot_opal", sx0 - 0.001, sx1 + 0.001, sy0 - 0.001, sy1 + 0.001, top - 0.01, top, m, PX["slot"], group="framing")
    for nm in ("wmh_cgap_y0", "wmh_cgap_y1"):
        o = bpy.data.objects[nm]
        lo, hi = wbb(o)
        E.set_box(o, sx1, hi[0], lo[1], hi[1], lo[2], hi[2])
    return [f"RL-hall out ({gone}); RL-hall-slot: X {SLOT['x']}, Y {SLOT['y']}, well {SLOT['well']} (Z {h}-{top}), opal emission {strength} "
            f"(sky colour); hall ceiling X {sx1}-3.60; the ceiling shadow gap along X 0.80 removed and the two end ones start at X {sx1}"]


def set_slot(strength):
    m = LIGHTS["slot_mat"]
    next(n for n in m.node_tree.nodes if n.type == "EMISSION").inputs["Strength"].default_value = strength


# ---------------------------------------------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------------------------------------------
def classify_final(idx, depth, normal, f, cv, IM):
    out, (X, Y, Z) = D.classify_door(idx, depth, normal, f, cv, IM)
    with np.errstate(invalid="ignore"):
        nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
        st = idx == PX["stone"]
        out[st & (nx > 0.7)] = 84
        out[st & ~(nx > 0.7)] = 85
        for key, cid in (("joint", 86), ("planter", 87), ("bench", 88), ("cap", 89), ("herbs", 90), ("lamp", 91), ("glow", 91), ("soil", 92),
                         ("mat", 93), ("panel", 94), ("slot", 95), ("olive", 96), ("recess", 97)):
            out[idx == PX[key]] = cid
        hall = (X < 3.60) & (Y > 6.35 - 0.01) & (Y < 9.80 + 0.01)
        out[(idx == IM["house_ceiling"]) & hall & (X < SLOT["x"][1] + 0.003)] = 95
        out[(idx == IM["house_wall"]) & hall & (Z > SLOT["ceiling"] - 0.002)] = 95
        lf = idx == D.PIDX["leaf"]
        face = (np.abs(nx) > 0.3) if D.LEAF["state"] != "open" else (np.abs(ny) > 0.3)
        out[lf & face] = 70
        out[lf & ~face] = 71
    return out, (X, Y, Z)


def edges_final(cls, depth, normal):
    Em = np.zeros(cls.shape, bool)
    d = np.where(depth < 1e4, depth, 1e4)
    soft = np.isin(cls, (10, 25, 30, 60, 67, 70, 90, 92, 93))           # floors, the fluted leaf face, herbs, soil, mat: no normal / depth edges inside
    for ax in (0, 1):
        a = [slice(None), slice(None)]
        b_ = [slice(None), slice(None)]
        a[ax], b_[ax] = slice(0, -1), slice(1, None)
        a, b_ = tuple(a), tuple(b_)
        ch = cls[a] != cls[b_]
        dot = (normal[a] * normal[b_]).sum(-1)
        ch |= (dot < math.cos(math.radians(25))) & (cls[a] != 0) & ~soft[a] & ~soft[b_]
        dd = np.abs(d[a] - d[b_])
        ch |= (dd > 0.03 * np.minimum(d[a], d[b_])) & (dd > 0.03) & ~(soft[a] & soft[b_])
        Em[a] |= ch
    return Em


# ---------------------------------------------------------------------------------------------------------------
# build, render
# ---------------------------------------------------------------------------------------------------------------
def build(a):
    setup_ids()
    S, R, cfg, notes = E.build(a)
    notes["door"] = D.court_and_door()
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name == "winlight_W-bath":
            ob.hide_render = True
    D.hide_like_furn_layer()
    ch = []
    ch += door_wall_stone()
    ch += fluted_leaf()
    ch += built_body()
    ch += herbs()
    ch += wall_light(a.lamp_w, a.lamp_glow)
    ch += doormat()
    ch += add_sun(a.sun)
    ch += olive((a.olive_x, a.olive_y))
    ch += hall_panel()
    ch += roof_slot(a.slot)
    notes["ch11"] = ch
    bpy.context.view_layer.update()
    return S, R, cfg, notes


def names_of(S):
    names = {int(k): list(v) for k, v in D.r2.names_by_pidx(S).items()}
    names.update({E.PIDX["lining"]: ["hall/O-entry-living walnut lining", "architecture"], E.PIDX["lining_gap"]: ["hall/O-entry-living lining shadow gap", "architecture"],
                  E.PIDX["hall_cgap"]: ["hall ceiling shadow gap", "architecture"]})
    names.update({int(v): [k, "shell"] for k, v in D.ba.SHELL_IDX.items()})
    names.update({int(v): ["house " + k, "shell"] for k, v in bh.IDX.items()})
    names.update({int(v): ["door/" + k, "architecture"] for k, v in D.PIDX.items()})
    names.update({int(v): ["ch11/" + k, "architecture"] for k, v in PX.items()})
    return names


def sun_pass(path, tmp, W, H):
    """Direct sun only (no sky, no other light, no bounce): 255 where the sun reaches, for the D0 frames."""
    sc = bpy.context.scene
    bgn = sc.world.node_tree.nodes["Background"]
    keep = dict(sky=bgn.inputs["Strength"].default_value, bounces=sc.cycles.max_bounces, expo=sc.view_settings.exposure, look=sc.view_settings.look,
                vt=sc.view_settings.view_transform)
    hidden = []
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob is not LIGHTS["sun"] and not ob.hide_render:
            ob.hide_render = True
            hidden.append(ob)
    glow = [next(n for n in m.node_tree.nodes if n.type == "EMISSION").inputs["Strength"] for m in LIGHTS["glow_mats"] + [LIGHTS["slot_mat"]]]
    gkeep = [g.default_value for g in glow]
    for g in glow:
        g.default_value = 0.0
    opals = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("opal") and not o.hide_render]
    for o in opals:
        o.hide_render = True
    try:
        bgn.inputs["Strength"].default_value = 0.0
        sc.cycles.max_bounces = 0
        sc.view_settings.view_transform, sc.view_settings.look = "Standard", "None"
        D.render_wh(path, tmp, W, H, 8, 0.0, -5.0, passes=False)
    finally:
        bgn.inputs["Strength"].default_value = keep["sky"]
        sc.cycles.max_bounces = keep["bounces"]
        sc.view_settings.view_transform, sc.view_settings.look = keep["vt"], keep["look"]
        sc.view_settings.exposure = keep["expo"]
        for ob in hidden:
            ob.hide_render = False
        for g, v in zip(glow, gkeep):
            g.default_value = v
        for o in opals:
            o.hide_render = False
    from PIL import Image
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    ref = float(np.percentile(lin[lin > 1e-4], 99)) if (lin > 1e-4).any() else 1.0
    Image.fromarray(np.clip(np.rint(lin / ref * 255), 0, 255).astype(np.uint8)).save(path, optimize=True)
    return dict(ref_linear=round(ref, 5), note="direct sun only (no sky, no lamp, no bounce), Standard view at exposure -5, linear luminance normalised to "
                                                "its 99th percentile = 255 (so it carries albedo and incidence: a plaster wall facing the sun near 255, "
                                                "the floor lower); > 64 = in direct sun")


def exr_beauty(tmp):
    """Add a scene-linear beauty EXR to the compositor of the next render (after render_wh set it up)."""
    sc = bpy.context.scene
    nt = sc.node_tree
    rl = next(n for n in nt.nodes if n.type == "R_LAYERS")
    fo = nt.nodes.new("CompositorNodeOutputFile")
    fo.base_path = tmp
    fo.format.file_format = "OPEN_EXR"
    fo.format.color_depth = "16"
    fo.format.exr_codec = "ZIP"
    fo.file_slots.clear()
    fo.file_slots.new("Beauty_")
    nt.links.new(rl.outputs["Image"], fo.inputs["Beauty_"])


def render_beauty(png, tmp, W, H, samples, ao, exposure, keep_exr=None):
    """D.render_wh, plus the scene-linear beauty as EXR (kept in the scratchpad when keep_exr is a path)."""
    sc = bpy.context.scene
    sc.view_settings.exposure = exposure
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.cycles.samples = samples
    fr.setup_comp(tmp, ao)
    if keep_exr:
        exr_beauty(tmp)
    sc.frame_set(1)
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
    if keep_exr:
        src = os.path.join(tmp, "Beauty_0001.exr")
        if os.path.exists(src):
            os.makedirs(os.path.dirname(keep_exr), exist_ok=True)
            shutil.move(src, keep_exr)


def reclassify(a, F, alias):
    meta = json.load(open(os.path.join(SCRATCH, "meta.json")))
    names = {int(k): v for k, v in meta["pass_index_names"].items()}
    IM = D.index_map_door(names)
    setup_ids()
    E.classify = classify_final
    E.edges_of = edges_final
    for fid in ([k for k in F if k not in alias] if a.frames == "all" else [alias.get(k, k) for k in a.frames.split(",")]):
        npz = os.path.join(SCRATCH, "passes", fid.replace("/", "_") + ".npz")
        jp = os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json")
        if not (os.path.exists(npz) and os.path.exists(jp)):
            continue
        z = np.load(npz)
        rec = json.load(open(jp))
        D.LEAF["state"] = F[fid]["leaf"]
        rec.update(E.save_passes(fid, os.path.join(a.out, fid + ".png"), z["depth"], z["idx"], z["normal"].astype(np.float32) / 127.0, F[fid], rec["canvas"],
                                 IM, a.out, write_npz=False))
        json.dump(rec, open(jp, "w"), indent=1, ensure_ascii=False)
        print("RECLASSIFIED", fid, "not allowed", rec["not_allowed_px"], flush=True)
    for dst, src in alias.items():
        for suf in ("-depth.png", "-id.png", "-edges.png"):
            if os.path.exists(os.path.join(a.out, src + suf)):
                os.makedirs(os.path.dirname(os.path.join(a.out, dst)), exist_ok=True)
                shutil.copyfile(os.path.join(a.out, src + suf), os.path.join(a.out, dst + suf))


def args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--reclassify", action="store_true")
    ap.add_argument("--frames", default="all")
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--station-samples", type=int, default=10)
    ap.add_argument("--door-exposure", type=float, default=0.75, help="the clay's one locked exposure (designer 11.1.8: as the 2026-11-14 clay)")
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6, help="the old RL-hall factor (applies to nothing once the slot replaces it)")
    ap.add_argument("--bath-window", type=float, default=4.5)
    ap.add_argument("--sun", type=float, default=8.0, help="sun strength (W/m2); calibrated, see the README")
    ap.add_argument("--lamp-w", type=float, default=22.0, help="each of the two 2700 K spots (W); calibrated")
    ap.add_argument("--lamp-glow", type=float, default=6.0, help="emission of the lamp's two diffusers")
    ap.add_argument("--slot", type=float, default=20.0, help="opal emission of RL-hall-slot; calibrated (the old RL-hall was 6.16)")
    ap.add_argument("--olive-x", type=float, default=OLIVE["c"][0])
    ap.add_argument("--olive-y", type=float, default=OLIVE["c"][1])
    ap.add_argument("--no-sun-pass", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    a.exposure = 1.0
    return a


def main(argv):
    a = args(argv)
    F, alias, L = D.frames()
    if a.reclassify:
        return reclassify(a, F, alias)
    want = [k for k in F if k not in alias] if a.frames == "all" else [alias.get(k, k) for k in a.frames.split(",")]
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    W4.r4.EXR_DIR = os.path.join(SCRATCH, "exr")
    t0 = time.time()
    res_cli = a.res
    a.res = res_cli or D.REG_CANVAS[0]
    S, R, cfg, notes = build(a)
    IM = D.index_map_door()
    E.classify = classify_final
    E.edges_of = edges_final
    expo = a.door_exposure
    meta = dict(stage="warm-modern FINAL entrance clay (ENT2; master-designer ch. 11), briefs/wm-door-final-d0-2026-11-16.md step 1; "
                      "framing_wm_door_final.py on framing_wm_door.py; 0 var2 tokens", date=time.strftime("%Y-%m-%d"), clip1_length_m=L,
                canvases=dict(reg=dict(px=list(D.REG_CANVAS), frame_box_px=[round(x, 4) for x in D.REG_BOX]), tall=dict(px=list(D.TALL_CANVAS), frame_box_px=list(D.TALL_BOX))),
                render=f"Cycles CPU seed 7, OIDN, AgX Medium High Contrast, exposure {expo} for every frame (one locked exposure, as 2026-11-14)",
                light=dict(sky=a.sky, living_window=a.living_boost, sun=dict(SUN, strength=a.sun), lamp=dict(spot_w=a.lamp_w, glow=a.lamp_glow, **{k: v for k, v in LAMP.items() if k != "c"}),
                           slot_opal=a.slot, olive_centre=[a.olive_x, a.olive_y], every_other_lamp="off"),
                build_notes={k: notes[k] for k in ("wm_entrance", "door", "ch11")}, build_s=round(time.time() - t0), ids=D.IDS, pass_index_names=names_of(S),
                door=D.DOOR, court=D.COURT, stone=D.STONE, pull=D.PULL, jib=D.JIB, courses=COURSES, heads_court=HEADS_COURT, heads_hall=HEADS_HALL,
                planter=PLANTER, bench=BENCH, lamp=LAMP, doormat=MAT, olive=OLIVE, panel=PANEL, slot=SLOT, flutes=FLUTES, index_map=IM, px=PX)
    json.dump(meta, open(os.path.join(SCRATCH, "meta.json"), "w"), indent=1, ensure_ascii=False, default=str)
    print("BUILD", meta["build_s"], "s;", *notes["ch11"], sep="\n  ", flush=True)
    tmp = tempfile.mkdtemp(prefix="wm-door-final-")
    cam = S["cam"]
    from PIL import Image
    for fid in want:
        f = F[fid]
        t1 = time.time()
        D.set_leaf(f["leaf"])
        canvas = D.REG_CANVAS if f["canvas"] == "reg" else D.TALL_CANVAS
        cv = D.set_view(cam, f, res_cli or canvas[0])
        png = os.path.join(a.out, fid + ".png")
        os.makedirs(os.path.dirname(png), exist_ok=True)
        smp = a.station_samples if (fid.startswith("c1/") and fid[-2:] not in ("00", "11")) else a.samples
        depth, idx, normal = D.geometry_pass(tmp, cv["W"], cv["H"])
        render_beauty(png, os.path.join(tmp, "p"), cv["W"], cv["H"], smp, 0.30, expo,
                     keep_exr=None if fid.startswith("c1/") else os.path.join(SCRATCH, "beauty", fid.replace("/", "_") + ".exr"))
        for nm in ("g", os.path.basename(fid)):
            q = os.path.join(W4.r4.EXR_DIR, nm + ".exr")
            if os.path.exists(q):
                os.remove(q)
        Image.open(png).save(png, optimize=True)
        rec = dict(frame=fid, camera=dict(loc=[round(x, 4) for x in f["loc"]], yaw=f["yaw"], lens=24, u0=f["u0"], v0=f["v0"], s_m=None if f["s"] is None else round(f["s"], 4)),
                   leaf=f["leaf"], canvas=cv, samples=smp, exposure=expo, mean_L=fr.mean_L(png))
        rec.update(E.save_passes(fid, png, depth, idx, normal, f, cv, IM, a.out))
        if fid.startswith("D0") and not a.no_sun_pass:
            rec["sun_pass"] = sun_pass(os.path.join(a.out, fid + "-sun.png"), os.path.join(tmp, "s"), cv["W"], cv["H"])
        rec["runtime_s"] = round(time.time() - t1)
        os.makedirs(os.path.join(SCRATCH, "frames"), exist_ok=True)
        json.dump(rec, open(os.path.join(SCRATCH, "frames", fid.replace("/", "_") + ".json"), "w"), indent=1, ensure_ascii=False)
        print("FRAME", fid, rec["runtime_s"], "s  L", rec["mean_L"], " not allowed", rec["not_allowed_px"], flush=True)
    for dst, src in alias.items():
        if src in want:
            for suf in (".png", "-depth.png", "-id.png", "-edges.png"):
                os.makedirs(os.path.dirname(os.path.join(a.out, dst)), exist_ok=True)
                shutil.copyfile(os.path.join(a.out, src + suf), os.path.join(a.out, dst + suf))
    shutil.rmtree(tmp, ignore_errors=True)
    print("DONE", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main(_ARGV)
