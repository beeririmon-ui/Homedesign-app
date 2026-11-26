#!/usr/bin/env python3
"""
clay_m0n.py: FB23 / NRD1 stage A step 1, the M0-N clay and light maps of the Nordic living room (render-agent, 2026-11-26). 0 var2 tokens.
Source: master-designer docs/proposals/nordic-house-plan-2026-11-26.md ch. 3 ("one hour for the house": 14:00 in February, clean white sun
through divided casements, 28 mm, height 1.00, almost frontal to the sofa wall, yaw ~8 deg left, the window in the left margin, the knitted
pouf cut in the right foreground, the pendant whole) and ch. 7 (the Nordic living-room list for approval 2: the default of every slot).
Nothing in docs/, data/ or site/ is edited: the camera is a proposal file next to the clay (camera-m0n-proposal.json).

Self-contained (no import of the house framing chain): the living room of docs/house-plan.json (room x -2.3..2.5, y 0..6.2, h 3.0; window
W-living on the -X wall, Y 0.9-2.7, sill 0.75, head 2.7; the dining opening in the right wall X 2.5, Y 2.97-4.57, Z 0-2.40), the Bible's
Nordic shell (mineral #F4F1EC, 15 skirting, 10 cornice, 25 cm white-oiled oak boards #D6BF9E along Y) with the plan's story architecture
(two white wooden casements, three panes each = 6 panes, frame in the outer plane, deep reveal), the Nordic fixed furniture (sofa 220 x 92 x
78, track arms 14 r3, oat; the oak-and-boucle lounge chair at (-1.23, 2.73) 25 deg), and product proxies at the card sizes at the slots
points (data/slots/living-room.json base entries = the Nordic plan B), textured with crops of the SKU photos (references for flux-2).

WORLD: the plan's world is mirrored against Blender (camera right = +X while looking at -Y), so every plan point (x, y, z) is built at
Blender (-x, y, z); plan_uv() keeps the plan's own projection, and the Blender camera is checked against it (projection_check_px).
COMPASS (proposal 3): the Nordic house alone is rotated so the plan's north facade (outward normal -X) faces azimuth 220 (SW).
SUN: 14:00 solar time on 15 February (declination -12.6), at latitude 41 N, where the altitude is the proposal's "about 30" (29.7; at 32 N
it would be 37.0 / az 217.6): azimuth 214.2. Disc 1.5 deg, about 5,500 K, white.

One material render with light groups (sky, sun, pendant, floor_lamp, accent_sconces, wall_sconce): guide A = sky + lamps (no direct sun),
guide B = sky + sun + lamps, from the same pixels. One white-override render: the clay, the sun map and the lamp maps.
  python3 clay_m0n.py                    # everything (scratch: $FB23_SCRATCH)
  python3 clay_m0n.py --quick            # smoke test at 640, scratch only
"""
import argparse
import glob
import json
import math
import os
import shutil
import sys
import time

import bpy  # noqa: E402  (bpy first: it provides bmesh and mathutils)
import bmesh  # noqa: E402
import cv2
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get("FB23_SCRATCH", "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb23")
SKU = os.path.join(SCR, "sku")

# ---- the proposal's numbers (camera solved in solve_cam: see camera-m0n-proposal.json) ----------------------------------------------
CAM = dict(id="M0-N", loc=[0.60, 5.35, 1.00], yaw=8.0, lens=28.0, u0=0.50, v0=0.50)
KU = CAM["lens"] / 36.0
KV = KU * 16.0 / 9.0
SUN = dict(R=220.0, lat=41.0, decl=-12.6, hour_angle=30.0, angle=1.5)
ROOM = dict(x=(-2.3, 2.5), y=(0.0, 6.2), h=3.0)
WIN = dict(y=(0.9, 2.7), sill=0.75, head=2.7, wall_out=-2.65, frame=(-2.62, -2.55))
POUF_C = (1.70, 2.75)                  # solved: 44 % visible, cut by the right and bottom edges, on the rug
LAMP_RGB = (1.0, 0.55, 0.25)            # 2700 K as the 5,000 K camera sees it, scene-linear
GLOW_RGB = (1.0, 0.80, 0.58)            # the lit fabric / paper of a shade (Bible: L 93-97, H 35-45, S 25-45)
BASKET_C = (2.05, 0.55)                 # moved (slots 1.7 point (-1.70, 0.75) hides the planter in M0-N: 11 % visible); proposal
GROUPS = ["sky", "sun", "pendant", "pendant_glow", "floor_lamp", "floor_lamp_glow", "accent_sconces", "wall_sconce", "wall_sconce_glow"]
LAMP_GROUPS = ["pendant", "floor_lamp", "accent_sconces", "wall_sconce"]          # the light the lamps throw (pools, washes)
GLOW_GROUPS = ["pendant_glow", "floor_lamp_glow", "wall_sconce_glow"]           # the lit shades themselves (emission)
# the Bible's light hierarchy (1.4), measured in A's daylight (no sun): the lamp's addition over daylight at a reference point
LAMP_CAL = {"floor_lamp": ((2.10, 0.0, 1.00), 0.22, "back wall right of the lamp (Bible: +20-25 %)"),
            "pendant": ((0.20, 1.72, 0.38), 0.13, "the bare oak at the table centre (Bible: +12-15 %)"),
            "accent_sconces": ((1.25, 0.0, 2.02), 0.15, "the wall above the right sconce (Bible: up to +15 % locally)"),
            "wall_sconce": ((-1.23, 2.73, 0.40), 0.17, "the armchair seat (Bible: +15-20 %)")}
GLOW_CAL = {"pendant_glow": (0.20, 1.72, 2.02), "floor_lamp_glow": (1.52, 0.20, 0.95)}   # shade L*: A 95 (Bible 93-97), B 93
LUMW = np.array([0.2126, 0.7152, 0.0722], np.float32)

PROD_IDX = {"rug": 801, "curtains": 802, "vase": 803, "planter": 804, "basket": 805, "magazine-holder": 806, "floor-lamp": 807,
            "framed-art": 808, "accent-sconces": 809, "pendant": 810, "bowl": 811, "candle-holders": 812, "coffee-table": 813,
            "cushions": 814, "sofa-cover": 815, "wall-sconce": 816, "wall-decor": 817, "table-runner": 818, "pouf": 819, "tray": 820}
FILLER_IDX = {"olive (filler)": 830, "branches (filler)": 831, "candles (filler)": 832, "magazines (filler)": 833, "pendant cord": 834,
              "curtain rod (not sold)": 835, "curtains: front panel (out of frame)": 836}
SHELL_IDX = dict(floor=1, back_wall=2, left_wall=3, window=4, right_wall=5, ceiling=6, outside=7, front_wall=8)
SOFA_IDX, ARMCHAIR_IDX = 11, 13
CARD = {"rug": "rug-cj-braided-wool-natural 330 x 230 (card 230 x 330)", "curtains": "curtains-aliexpress-cotton-linen-curtain-look-902882 S-fold 100 x 275, a panel each side",
        "vase": "vase-cj-textured-white-stoneware D16 x H32", "planter": "planter-cj-seagrass-belly D35 x H37",
        "basket": "basket-cj-jute-rope-cylinder D35 x H39", "magazine-holder": "magazine-holder-cj-felt-log-basket 45 x 32 x 40",
        "floor-lamp": "floor-lamp-aliexpress-wabi-sabi-japan-floor-217361 (card has no size; photo: H 128, shade D17.5 x 85, base 29)",
        "framed-art": "framed-art-aliexpress-japandi-bare-branch-70x100-776445 70 x 100 (thin oak frame added for the clay)",
        "accent-sconces": "accent-sconces-aliexpress-indoor-stone-wall-lamp D6.5 x H16, projection 9, a pair",
        "pendant": "pendant-cj-pleated-pumpkin-lantern-40 D40 x H25", "bowl": "bowl-cj-speckled-ivory-wide-bowl-21 D21.3 x H5.2",
        "candle-holders": "candle-holders-cj-travertine-pedestal 7 x 11, a pair", "coffee-table": "coffee-table-idana-javorina-olia-natural 120 x 65 x 38",
        "cushions": "set A: cushions-cj-boucle-teddy 50, cushions-cj-knitted-chenille-bean-green 45, cushions-cj-linen-look-charcoal 50",
        "sofa-cover": "sofa-cover-cj-cotton-muslin-fringe White 150 x 200 (approximate drape on the right arm)",
        "wall-sconce": "wall-sconce-cj-black-swing-arm-fabric, plate (-2.30, 3.17, 1.47) (out of frame; light only)",
        "wall-decor": "wall-decor-aliexpress-natural-raffia-woven-bohemian-763597 D30", "table-runner": "table-runner-cj-linen-look-sage-fringe 33 x 122",
        "pouf": "pouf-cj-cotton-knit-ball-cover 50 (filled height assumed 35)", "tray": "pool-cj-travertine-organic-tray-24 24 x 17 x 1.8"}
POS = {"rug": "X -1.45..1.85, Y 0.72-3.02 (slots 1.6 envelope, card depth 230)", "curtains": "the back panel (rod 2.82; stack Y 0.50-0.92); the front panel (Y 2.68-3.10) is out of frame and measured apart",
       "vase": "(-2.42, 1.35, 0.75) sill", "planter": "(-2.00, 0.47)", "basket": "(2.05, 0.55): MOVED (slots 1.7 (-1.70, 0.75) hides the planter in M0-N)", "magazine-holder": "(-0.54, 2.52) slots 1.8",
       "floor-lamp": "(1.52, 0.20)", "framed-art": "centre (0.20, 0, 1.475)", "accent-sconces": "(-0.85, 0, 1.75) and (1.25, 0, 1.75)",
       "pendant": "(0.20, 1.72), shade bottom 1.90", "bowl": "(0.68, 1.92)", "candle-holders": "(0.47, 1.62) and (0.58, 1.66) on the tray",
       "coffee-table": "centre (0.20, 1.72)", "cushions": "on the sofa", "sofa-cover": "right arm", "wall-sconce": "(-2.30, 3.17, 1.47)",
       "wall-decor": "(-1.20, 0.02, 1.20)", "table-runner": "midline 31 cm from the left end", "pouf": f"{POUF_C} (new: solved for M0-N)",
       "tray": "(0.52, 1.64) (new slot; placed under the candle holders)"}
TEX = {  # SKU photo crops (fractions x0, y0, x1, y1) used as references inside the input: file, crop, tile metres
    "rug": ("rug-cj-braided-wool-natural__0.jpg", (0.15, 0.15, 0.85, 0.62), 0.9),
    "boucle": ("cushions-cj-boucle-teddy__0.jpg", (0.40, 0.40, 0.70, 0.70), 0.22),
    "sage": ("cushions-cj-knitted-chenille-bean-green__0.jpg", (0.12, 0.45, 0.40, 0.70), 0.25),
    "charcoal": ("cushions-cj-linen-look-charcoal__0.jpg", (0.35, 0.30, 0.65, 0.60), 0.25),
    "throw": ("sofa-cover-cj-cotton-muslin-fringe__1.jpg", (0.45, 0.35, 0.75, 0.65), 0.45),
    "pouf": ("pouf-cj-cotton-knit-ball-cover__0.jpg", (0.35, 0.35, 0.65, 0.60), 0.25),
    "basket": ("basket-cj-jute-rope-cylinder__0.jpg", (0.36, 0.38, 0.60, 0.70), 0.20),
    "planter": ("planter-cj-seagrass-belly__0.jpg", (0.35, 0.45, 0.65, 0.75), 0.22),
    "felt": ("magazine-holder-cj-felt-log-basket__0.jpg", (0.30, 0.42, 0.60, 0.65), 0.30),
    "runner": ("table-runner-cj-linen-look-sage-fringe__2.jpg", (0.35, 0.30, 0.60, 0.55), 0.30),
    "vase": ("vase-cj-textured-white-stoneware__0.jpg", (0.42, 0.30, 0.58, 0.60), 0.12),
    "travertine": ("candle-holders-cj-travertine-pedestal__0.jpg", (0.43, 0.62, 0.57, 0.80), 0.06),
    "tray": ("pool-cj-travertine-organic-tray-24__0.jpg", (0.30, 0.35, 0.60, 0.60), 0.20),
    "bowl": ("bowl-cj-speckled-ivory-wide-bowl-21__0.jpg", (0.30, 0.30, 0.62, 0.62), 0.22),
}
REG = {}                                # key -> [objects]


# ---------------------------------------------------------------------------------------------------------------------------------------
def srgb2lin(h):
    h = h.lstrip("#")
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)) + (1.0,)


def b(p):
    return (-p[0], p[1], p[2])


_MATS = {}


def principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]


def mcol(name, hexcol, rough=0.9, noise=0.0, nscale=(40, 40, 40), emit=None, alpha=None, sheen=0.0):
    key = (name, hexcol, rough, noise, emit, alpha)
    if key in _MATS:
        return _MATS[key]
    m, N, L, bsdf = principled("m0n_" + name)
    bsdf.inputs["Base Color"].default_value = srgb2lin(hexcol)
    bsdf.inputs["Roughness"].default_value = rough
    if sheen:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if noise:
        tc, mp, nz = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeMapping"), N.new("ShaderNodeTexNoise")
        mp.inputs["Scale"].default_value = nscale
        nz.inputs["Scale"].default_value = 1.0
        nz.inputs["Detail"].default_value = 3.0
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        c0 = np.array(srgb2lin(hexcol)[:3])
        mix.inputs[6].default_value = tuple(np.clip(c0 * (1 - noise), 0, 1)) + (1,)
        mix.inputs[7].default_value = tuple(np.clip(c0 * (1 + noise), 0, 1)) + (1,)
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        L.new(mp.outputs["Vector"], nz.inputs["Vector"])
        L.new(nz.outputs["Fac"], mix.inputs["Factor"])
        L.new(mix.outputs[2], bsdf.inputs["Base Color"])
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = GLOW_RGB + (1.0,)
        bsdf.inputs["Emission Strength"].default_value = emit
    if alpha is not None:
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Transmission Weight"].default_value = 0.0
    _MATS[key] = m
    return m


def mtex(name, key, rough=0.95, flip=False):
    """an SKU-photo crop on object coordinates, box projection, mirrored tiling (no seams)"""
    if ("tex", name) in _MATS:
        return _MATS[("tex", name)]
    f, crop, tile = TEX[key]
    im = Image.open(os.path.join(SKU, f)).convert("RGB")
    W, H = im.size
    im = im.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    os.makedirs(os.path.join(SCR, "tex"), exist_ok=True)
    p = os.path.join(SCR, "tex", key + ".png")
    im.save(p)
    m, N, L, bsdf = principled("m0n_tex_" + name)
    tc, mp, it = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeMapping"), N.new("ShaderNodeTexImage")
    it.image = bpy.data.images.load(p)
    it.projection = "BOX"
    it.projection_blend = 0.3
    it.extension = "MIRROR"
    mp.inputs["Scale"].default_value = (1.0 / tile,) * 3
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    L.new(mp.outputs["Vector"], it.inputs["Vector"])
    L.new(it.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    _MATS[("tex", name)] = m
    return m


def mimage_plane(name, img, flip=True, alpha_circle=False):
    """an image on a flat plane via generated coordinates (the art print, the raffia disc)"""
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    os.makedirs(os.path.join(SCR, "tex"), exist_ok=True)
    p = os.path.join(SCR, "tex", name + ".png")
    if alpha_circle:
        img = img.convert("RGBA")
        a = Image.new("L", img.size, 0)
        ImageDraw.Draw(a).ellipse((0, 0, img.size[0] - 1, img.size[1] - 1), fill=255)
        img.putalpha(a)
    img.save(p)
    m, N, L, bsdf = principled("m0n_img_" + name)
    tc, it = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeTexImage")
    it.image = bpy.data.images.load(p)
    it.extension = "CLIP"
    sep, comb = N.new("ShaderNodeSeparateXYZ"), N.new("ShaderNodeCombineXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    L.new(sep.outputs["X"], comb.inputs["X"])
    L.new(sep.outputs["Z"], comb.inputs["Y"])
    L.new(comb.outputs[0], it.inputs["Vector"])
    L.new(it.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha_circle:
        L.new(it.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.95
    return m


def link(name, me, m, pidx, key, lightgroup=None, shadow=True):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if m is not None:
        ob.data.materials.append(m)
    ob.pass_index = pidx
    if lightgroup:
        ob.lightgroup = lightgroup
    ob.visible_shadow = shadow
    REG.setdefault(key, []).append(ob)
    return ob


def bevel(ob, w, seg=3):
    if w > 0:
        md = ob.modifiers.new("bev", "BEVEL")
        md.width, md.segments, md.limit_method = w, seg, "NONE"
    return ob


def box(key, x0, x1, y0, y1, z0, z1, m, pidx, bev=0.0, **kw):
    """an axis-aligned box in PLAN coordinates"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((-((x0 + x1) / 2 + v.co.x * (x1 - x0)), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    return bevel(link(f"{key}_{len(REG.get(key, []))}", me, m, pidx, key, **kw), bev)


def lbox(key, sx, sy, sz, m, pidx, loc, rot=(0, 0, 0), bev=0.0, **kw):
    """a centred box of size (sx, sy, sz) placed at a PLAN location with a PLAN euler (degrees): mirrored to Blender"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    ob = bevel(link(f"{key}_{len(REG.get(key, []))}", me, m, pidx, key, **kw), bev)
    ob.location = b(loc)
    ob.rotation_euler = (math.radians(rot[0]), -math.radians(rot[1]), -math.radians(rot[2]))
    return ob


def lathe(key, cx, cy, prof, m, pidx, n=64, ripple=None, cap_bottom=True, cap_top=True, z0=0.0, sx=1.0, sy=1.0, rotz=0.0, **kw):
    """a surface of revolution from (r, z) pairs, at plan (cx, cy) + z0; ripple = (count, amplitude) for pleats and ribs"""
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        ring = []
        for i in range(n):
            ph = 2 * math.pi * i / n
            rr = r * (1 + (ripple[1] * math.cos(ripple[0] * ph) if ripple else 0.0))
            ring.append(bm.verts.new((rr * math.cos(ph) * sx, rr * math.sin(ph) * sy, z)))
        rings.append(ring)
    for a, c in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], c[j], c[i]))
    if cap_bottom and prof[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and prof[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = link(f"{key}_{len(REG.get(key, []))}", me, m, pidx, key, **kw)
    ob.location = b((cx, cy, z0))
    ob.rotation_euler = (0, 0, -math.radians(rotz))
    return ob


def cyl(key, cx, cy, r, z0, z1, m, pidx, r1=None, n=32, **kw):
    return lathe(key, cx, cy, [(r, z0), (r if r1 is None else r1, z1)], m, pidx, n=n, **kw)


def seg(key, p0, p1, r, m, pidx, **kw):
    """a thin cylinder between two plan points"""
    P0, P1 = Vector(b(p0)), Vector(b(p1))
    d = P1 - P0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r * 0.8, depth=d.length)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    ob = link(f"{key}_{len(REG.get(key, []))}", me, m, pidx, key, **kw)
    ob.location = (P0 + P1) / 2
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return ob


def sheet(key, pts_fn, nu, nv, m, pidx, **kw):
    """a grid surface: pts_fn(s, t) -> plan point, s, t in [0, 1]"""
    bm = bmesh.new()
    V = [[bm.verts.new(b(pts_fn(i / (nu - 1), j / (nv - 1)))) for j in range(nv)] for i in range(nu)]
    for i in range(nu - 1):
        for j in range(nv - 1):
            bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return link(f"{key}_{len(REG.get(key, []))}", me, m, pidx, key, **kw)


def extrude_profile_y(key, prof_xz, y0, y1, m, pidx, **kw):
    """a closed XZ profile (plan) extruded along Y (the Olia's waterfall section)"""
    bm = bmesh.new()
    a = [bm.verts.new(b((x, y0, z))) for x, z in prof_xz]
    c = [bm.verts.new(b((x, y1, z))) for x, z in prof_xz]
    n = len(prof_xz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], c[j], c[i]))
    bm.faces.new(a)
    bm.faces.new(list(reversed(c)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    return link(f"{key}_{len(REG.get(key, []))}", me, m, pidx, key, **kw)


# ---------------------------------------------------------------------------------------------------------------------------------------
# the room
# ---------------------------------------------------------------------------------------------------------------------------------------
def shell():
    wall = mcol("wall", "#F4F1EC", 0.95, noise=0.012, nscale=(1.5, 1.5, 1.5))
    paint = mcol("paint_wood", "#F4F1EC", 0.55)
    (x0, x1), (y0, y1), h = ROOM["x"], ROOM["y"], ROOM["h"]
    t = 0.35
    # floor: 25 cm white-oiled oak boards along Y (lengths 3.0-4.0, staggered), 2 mm joints over a darker subfloor
    rng = np.random.default_rng(23)
    box("floor_sub", x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, -0.06, -0.002, mcol("subfloor", "#7A6650", 0.9), SHELL_IDX["floor"])
    xs = np.arange(x0, x1, 0.25)
    for i, bx in enumerate(xs):
        y = y0 - rng.uniform(0, 1.5)
        while y < y1:
            L = rng.uniform(3.0, 4.0)
            jit = rng.normal(0, 0.035)
            c = np.clip(np.array([0xD6, 0xBF, 0x9E]) * (1 + jit), 0, 255).astype(int)
            mm = mcol(f"oak{i % 6}_{int(jit * 1000)}", "#%02X%02X%02X" % tuple(c), 0.55, noise=0.06, nscale=(60, 2.5, 60))
            box("floor", bx + 0.001, min(bx + 0.25, x1) - 0.001, max(y, y0) + 0.001, min(y + L, y1) - 0.001, -0.002, 0.0, mm, SHELL_IDX["floor"])
            y += L
    box("ceiling", x0 - t, x1 + t, y0 - t, y1 + t, h, h + 0.2, wall, SHELL_IDX["ceiling"])
    # back wall (Y 0), front wall (Y 6.2, solid: behind the camera; the hall doors are not modelled, noted)
    box("back_wall", x0 - t, x1 + t, y0 - t, y0, 0, h, wall, SHELL_IDX["back_wall"])
    box("front_wall", x0 - t, x1 + t, y1, y1 + t, 0, h, wall, SHELL_IDX["front_wall"])
    # left wall with the window opening (outer plane -2.65, reveal 35 to the frame)
    wy0, wy1 = WIN["y"]
    for args in [(x0 - t, x0, y0 - t, wy0, 0, h), (x0 - t, x0, wy1, y1 + t, 0, h), (x0 - t, x0, wy0, wy1, 0, WIN["sill"] - 0.03),
                 (x0 - t, x0, wy0, wy1, WIN["head"], h)]:
        box("left_wall", *args, wall, SHELL_IDX["left_wall"])
    # right wall with the dining opening X 2.5, Y 2.97-4.57, Z 0-2.40, and a closed box behind it (the dining room is not dressed)
    for args in [(x1, x1 + 0.15, y0, 2.97, 0, h), (x1, x1 + 0.15, 4.57, y1, 0, h), (x1, x1 + 0.15, 2.97, 4.57, 2.40, h)]:
        box("right_wall", *args, wall, SHELL_IDX["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 1.0, 1.15, 0, h, wall, SHELL_IDX["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 6.5, 6.65, 0, h, wall, SHELL_IDX["right_wall"])
    box("dining_box", x1 + 4.5, x1 + 4.65, 1.0, 6.65, 0, h, wall, SHELL_IDX["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 1.0, 6.65, -0.05, 0.0, mcol("oak_d", "#D6BF9E", 0.6), SHELL_IDX["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 1.0, 6.65, h, h + 0.1, wall, SHELL_IDX["right_wall"])
    # skirting 15 in the wall colour, cornice 10 (one step)
    for args in [(x0, x1, y0, y0 + 0.015, 0, 0.15), (x1 - 0.015, x1, y0, 2.97, 0, 0.15), (x0, x0 + 0.015, y0, wy0, 0, 0.15),
                 (x0, x0 + 0.015, wy0, wy1, 0, 0.15), (x0, x0 + 0.015, wy1, y1, 0, 0.15)]:
        box("skirting", *args, paint, SHELL_IDX["back_wall"])
    for args in [(x0, x1, y0, y0 + 0.04, h - 0.10, h), (x0, x0 + 0.04, y0, y1, h - 0.10, h), (x1 - 0.04, x1, y0, y1, h - 0.10, h)]:
        box("cornice", *args, wall, SHELL_IDX["ceiling"])
    # the window: inner sill board, outer frame (6 cm), centre mullion 6, two casements (5 cm), 3 panes each (muntins 3.5), no glass
    W = SHELL_IDX["window"]
    box("sill", x0 - 0.33, x0 + 0.04, wy0 - 0.02, wy1 + 0.02, WIN["sill"] - 0.03, WIN["sill"], paint, W)
    f0, f1 = WIN["frame"]
    zb, zt = WIN["sill"], WIN["head"]
    box("frame", f0, f1, wy0, wy0 + 0.06, zb, zt, paint, W)
    box("frame", f0, f1, wy1 - 0.06, wy1, zb, zt, paint, W)
    box("frame", f0, f1, wy0, wy1, zt - 0.06, zt, paint, W)
    box("frame", f0 - 0.02, f1, wy0, wy1, zb, zb + 0.07, paint, W)
    ym = (wy0 + wy1) / 2
    box("frame", f0, f1, ym - 0.03, ym + 0.03, zb, zt, paint, W)
    for s0, s1 in [(wy0 + 0.06, ym - 0.03), (ym + 0.03, wy1 - 0.06)]:
        za, zc = zb + 0.07, zt - 0.06
        box("sash", f0 + 0.01, f1 + 0.005, s0, s0 + 0.05, za, zc, paint, W)
        box("sash", f0 + 0.01, f1 + 0.005, s1 - 0.05, s1, za, zc, paint, W)
        box("sash", f0 + 0.01, f1 + 0.005, s0, s1, za, za + 0.06, paint, W)
        box("sash", f0 + 0.01, f1 + 0.005, s0, s1, zc - 0.05, zc, paint, W)
        g0, g1 = za + 0.06, zc - 0.05
        for k in (1, 2):
            zm = g0 + k * (g1 - g0) / 3
            box("muntin", f0 + 0.015, f1, s0, s1, zm - 0.0175, zm + 0.0175, paint, W)
    # outside: the ground with melting snow, birches, pale sky (world)
    gmat = bpy.data.materials.new("m0n_ground")
    gmat.use_nodes = True
    N, Lk = gmat.node_tree.nodes, gmat.node_tree.links
    bs = N["Principled BSDF"]
    tc, nz, ramp = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeTexNoise"), N.new("ShaderNodeValToRGB")
    nz.inputs["Scale"].default_value = 0.35
    nz.inputs["Detail"].default_value = 6.0
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.50, 0.56
    ramp.color_ramp.elements[0].color = srgb2lin("#8C8670")
    ramp.color_ramp.elements[1].color = srgb2lin("#EEF0F0")
    Lk.new(tc.outputs["Object"], nz.inputs["Vector"])
    Lk.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    Lk.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.9
    box("ground", -60, x0 - t, -40, 50, -0.35, -0.30, gmat, SHELL_IDX["outside"])
    birch = mcol("birch", "#E6E3DC", 0.8, noise=0.25, nscale=(30, 30, 4))
    for (bx, by, r, hh) in [(-7.5, 0.6, 0.11, 9), (-9.0, 2.2, 0.09, 9), (-8.2, 3.6, 0.13, 10), (-12.0, -0.8, 0.10, 9), (-13.5, 1.5, 0.12, 10),
                            (-11.0, 4.6, 0.08, 8), (-16.0, 3.0, 0.12, 10), (-6.2, -1.6, 0.10, 9)]:
        cyl("birch", bx, by, r, -0.3, hh, birch, SHELL_IDX["outside"], r1=r * 0.5, n=16)
    return wall, paint


# ---------------------------------------------------------------------------------------------------------------------------------------
# the fixed furniture: the Nordic sofa (not the warm-modern monolith) and the oak lounge chair
# ---------------------------------------------------------------------------------------------------------------------------------------
def sofa():
    oat = mcol("oat_weave", "#E6DCCB", 1.0, noise=0.04, nscale=(300, 300, 300), sheen=0.3)
    oak = mcol("oak", "#C8A27A", 0.55, noise=0.05, nscale=(80, 4, 80))
    P = SOFA_IDX
    X0, X1, Y0, Y1 = -0.90, 1.30, 0.03, 0.95
    for lx in (X0 + 0.05, X1 - 0.05):
        for ly in (Y0 + 0.06, Y1 - 0.05):
            cyl("sofa", lx, ly, 0.0125, 0.0, 0.16, oak, P, r1=0.02, n=16)
    box("sofa", X0, X1, Y0, Y1, 0.15, 0.30, oat, P, bev=0.03)
    box("sofa", X0, X0 + 0.14, Y0, Y1, 0.15, 0.60, oat, P, bev=0.03)
    box("sofa", X1 - 0.14, X1, Y0, Y1, 0.15, 0.60, oat, P, bev=0.03)
    box("sofa", X0 + 0.14, X1 - 0.14, Y0, Y0 + 0.17, 0.30, 0.62, oat, P, bev=0.03)
    w = (X1 - X0 - 0.28) / 3
    for i in range(3):
        a = X0 + 0.14 + i * w
        box("sofa", a + 0.005, a + w - 0.005, 0.32, Y1 - 0.01, 0.30, 0.44, oat, P, bev=0.045)
        lbox("sofa", w - 0.01, 0.20, 0.40, oat, P, (a + w / 2, 0.27, 0.59), rot=(10, 0, 0), bev=0.06)


def armchair():
    """build_chair_v4's lounge chair (v4-spec fixed_furniture.armchair), at the plan's (-1.23, 2.73), 25 deg, in the Bible's oak + mist boucle"""
    oak = mcol("oak", "#C8A27A", 0.55, noise=0.05, nscale=(80, 4, 80))
    bou = mcol("mist_boucle", "#D9D6D0", 1.0, noise=0.06, nscale=(250, 250, 250), sheen=0.4)
    P = ARMCHAIR_IDX
    root = bpy.data.objects.new("armchair_root", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = b((-1.23, 2.73, 0.0))
    root.rotation_euler = (0, 0, math.radians(25.0))        # plan yaw -25 -> mirrored +25

    def part(sx0, sx1, sy0, sy1, z0, z1, m, bev=0.0, ry=0.0, pivot=None):
        # local plan coords: x = depth (front +), y = width; mirrored X for Blender
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((-((sx0 + sx1) / 2 + v.co.x * (sx1 - sx0)), (sy0 + sy1) / 2 + v.co.y * (sy1 - sy0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
        me = bpy.data.meshes.new("armchair")
        bm.to_mesh(me)
        bm.free()
        ob = bevel(link(f"armchair_{len(REG.get('armchair', []))}", me, m, P, "armchair"), bev)
        ob.parent = root
        return ob

    hd, hw, lw, arm_z = 0.39, 0.36, 0.045, 0.58
    for lx in (hd - 0.06, -hd + 0.06):
        for ly in (hw - 0.03, -hw + 0.03):
            part(lx - lw / 2, lx + lw / 2, ly - lw / 2, ly + lw / 2, 0, arm_z - 0.03, oak, 0.005)
    for ly in (hw - 0.03, -hw + 0.03):
        part(-hd + 0.02, hd - 0.0375, ly - 0.03, ly + 0.03, arm_z - 0.03, arm_z, oak, 0.006)
        part(-hd + 0.06, hd - 0.06, ly - 0.02, ly + 0.02, 0.20, 0.25, oak)
    for lx in (hd - 0.06, -hd + 0.06):
        part(lx - 0.02, lx + 0.02, -hw + 0.03, hw - 0.03, 0.22, 0.28, oak)
    part(-hd + 0.18, hd - 0.02, -hw + 0.065, hw - 0.065, 0.27, 0.40, bou, 0.03)
    # back cushion 34.5 x 13 tilted 15 deg about the pivot (-0.22, 0.34); posts 39 long (v4.1)
    tilt = math.radians(15.0)
    for (L, th, mat, bev, yy) in [(0.345, 0.13, bou, 0.035, (-hw + 0.065, hw - 0.065))]:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * th, v.co.y * (yy[1] - yy[0]), (v.co.z + 0.5) * L))
        me = bpy.data.meshes.new("armchair")
        bm.to_mesh(me)
        bm.free()
        ob = bevel(link(f"armchair_{len(REG.get('armchair', []))}", me, mat, P, "armchair"), bev)
        ob.parent = root
        ob.location = (0.22, 0, 0.34)
        ob.rotation_euler = (0, tilt, 0)
    for ly in (hw - 0.03, -hw + 0.03):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * 0.04, v.co.y * 0.04, (v.co.z + 0.5) * 0.39))
        me = bpy.data.meshes.new("armchair")
        bm.to_mesh(me)
        bm.free()
        ob = link(f"armchair_{len(REG.get('armchair', []))}", me, oak, P, "armchair")
        ob.parent = root
        ob.location = (hd - 0.06, ly, 0.26)
        ob.rotation_euler = (0, tilt, 0)


# ---------------------------------------------------------------------------------------------------------------------------------------
# the products (proxies at the card sizes) and the fillers
# ---------------------------------------------------------------------------------------------------------------------------------------
LIGHTS = {}


def light(name, kind, loc, power, group, size=0.05, aim=None, spot=None, blend=1.0, color=LAMP_RGB):
    L = bpy.data.lights.new(name, kind)
    L.energy = power
    L.color = color[:3]
    if kind in ("POINT", "SPOT"):
        L.shadow_soft_size = size
    if kind == "SPOT":
        L.spot_size, L.spot_blend = math.radians(spot), blend
    ob = bpy.data.objects.new(name, L)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = b(loc)
    if aim is not None:
        d = Vector(b(aim)) - Vector(b(loc))
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    ob.lightgroup = group
    LIGHTS.setdefault(group, []).append(ob)
    return ob


def products():
    I = PROD_IDX
    oak = mcol("oak", "#C8A27A", 0.55, noise=0.05, nscale=(80, 4, 80))
    oak_light = mcol("olia_oak", "#CDAE88", 0.5, noise=0.07, nscale=(90, 3, 90))
    trav = mtex("travertine", "travertine", 0.8)
    # rug: braided natural wool, 330 x 230
    box("rug", -1.45, 1.85, 0.72, 3.02, 0.0, 0.014, mtex("rug", "rug", 1.0), I["rug"], bev=0.004)
    # curtains: two sheer oat S-fold panels on a slim charcoal rod at 2.82
    sheer = mcol("sheer_oat", "#E3D9C6", 0.9, alpha=0.42)
    rod = mcol("charcoal_metal", "#3A3A3A", 0.5)
    seg("curtain rod (not sold)", (-2.21, 0.45, 2.82), (-2.21, 3.15, 2.82), 0.01, rod, FILLER_IDX["curtain rod (not sold)"])
    for (ya, yb_, key) in [(0.50, 0.92, "curtains"), (2.68, 3.10, "curtains: front panel (out of frame)")]:
        sheet(key, lambda s, t, ya=ya, yb_=yb_: (-2.20 + 0.055 * math.sin(2 * math.pi * 5 * s), ya + (yb_ - ya) * s, 0.04 + t * 2.76),
              90, 24, sheer, I["curtains"] if key == "curtains" else FILLER_IDX[key])
    # framed art: 70 x 100 print in a thin oak frame, centre (0.20, 0, 1.475)
    art = Image.open(os.path.join(SKU, "framed-art-aliexpress-japandi-bare-branch-70x100-776445__0.jpg")).convert("RGB")
    W, H = art.size
    tw = min(W, int(H * 0.70))
    th = int(tw / 0.70)
    art = art.crop(((W - tw) // 2, (H - th) // 2, (W - tw) // 2 + tw, (H - th) // 2 + th))
    cx, cz = 0.20, 1.475
    for args in [(cx - 0.35, cx + 0.35, 0.0, 0.03, cz + 0.48, cz + 0.50), (cx - 0.35, cx + 0.35, 0.0, 0.03, cz - 0.50, cz - 0.48),
                 (cx - 0.35, cx - 0.33, 0.0, 0.03, cz - 0.50, cz + 0.50), (cx + 0.33, cx + 0.35, 0.0, 0.03, cz - 0.50, cz + 0.50)]:
        box("framed-art", *args, oak, I["framed-art"])
    box("framed-art", cx - 0.33, cx + 0.33, 0.0, 0.012, cz - 0.48, cz + 0.48, mimage_plane("art", art), I["framed-art"])
    # wall decor: raffia disc D30, centre (-1.20, 0.02, 1.20)
    raf = Image.open(os.path.join(SKU, "wall-decor-aliexpress-natural-raffia-woven-bohemian-763597__0.jpg")).convert("RGB")
    W, H = raf.size
    raf = raf.crop((int(0.06 * W), int(0.14 * H), int(0.90 * W), int(0.98 * H)))
    box("wall-decor", -1.35, -1.05, 0.0, 0.02, 1.05, 1.35, mimage_plane("raffia", raf, alpha_circle=True), I["wall-decor"])
    # accent sconces: travertine cylinders D6.5 x 16 on small walnut plates, up/down light
    wal = mcol("walnut", "#5E4433", 0.5)
    for x in (-0.85, 1.25):
        box("accent-sconces", x - 0.02, x + 0.02, 0.0, 0.015, 1.64, 1.86, wal, I["accent-sconces"])
        cyl("accent-sconces", x, 0.0575, 0.0325, 1.67, 1.83, trav, I["accent-sconces"], n=32)
        light(f"sconce_up_{x}", "SPOT", (x, 0.06, 1.84), 1.6, "accent_sconces", size=0.02, aim=(x, 0.0, 2.6), spot=55, blend=1.0)
        light(f"sconce_dn_{x}", "SPOT", (x, 0.06, 1.66), 1.6, "accent_sconces", size=0.02, aim=(x, 0.0, 0.9), spot=55, blend=1.0)
    # vase on the sill + eucalyptus branches (filler)
    vprof = [(0.045, 0.0), (0.062, 0.03), (0.078, 0.10), (0.080, 0.15), (0.070, 0.22), (0.048, 0.28), (0.036, 0.305), (0.040, 0.32)]
    lathe("vase", -2.42, 1.35, vprof, mtex("vase", "vase", 0.9), I["vase"], z0=WIN["sill"], cap_top=False)
    sage = mcol("eucalyptus", "#A3AC98", 0.8)
    rng = np.random.default_rng(5)
    for k in range(6):
        a = rng.uniform(0, 2 * np.pi)
        top = (-2.42 + 0.20 * math.cos(a) * 0.5, 1.35 + 0.22 * math.sin(a), 1.18 + rng.uniform(0, 0.17))
        seg("branches (filler)", (-2.42, 1.35, 1.03), top, 0.004, mcol("twig", "#6E6252", 0.8), FILLER_IDX["branches (filler)"])
        for j in range(7):
            t = 0.35 + 0.65 * j / 6
            p = (-2.42 + (top[0] + 2.42) * t, 1.35 + (top[1] - 1.35) * t, 1.03 + (top[2] - 1.03) * t)
            lbox("branches (filler)", 0.035, 0.004, 0.03, sage, FILLER_IDX["branches (filler)"], p, rot=(0, rng.uniform(-40, 40), rng.uniform(0, 180)))
    # planter: seagrass belly D35 x H37 + the olive (filler)
    pprof = [(0.11, 0.0), (0.155, 0.06), (0.175, 0.16), (0.165, 0.27), (0.14, 0.34), (0.145, 0.37)]
    lathe("planter", -2.00, 0.47, pprof, mtex("planter", "planter", 1.0), I["planter"], cap_top=False)
    cyl("olive (filler)", -2.00, 0.47, 0.13, 0.30, 0.33, mcol("soil", "#4B3F33", 1.0), FILLER_IDX["olive (filler)"])
    bark = mcol("olive_bark", "#6F6556", 0.9)
    seg("olive (filler)", (-2.00, 0.47, 0.30), (-1.97, 0.45, 1.05), 0.025, bark, FILLER_IDX["olive (filler)"])
    leaf = mcol("olive_leaf", "#9EA893", 0.7, noise=0.12, nscale=(20, 20, 20))
    for k in range(26):
        c = (-1.97 + rng.normal(0, 0.14), 0.47 + rng.normal(0, 0.12), 1.32 + rng.normal(0, 0.17))
        seg("olive (filler)", (-1.97, 0.45, 1.05), c, 0.008, bark, FILLER_IDX["olive (filler)"])
        for j in range(14):
            p = (c[0] + rng.normal(0, 0.06), c[1] + rng.normal(0, 0.06), c[2] + rng.normal(0, 0.05))
            lbox("olive (filler)", 0.055, 0.004, 0.014, leaf, FILLER_IDX["olive (filler)"], p, rot=(rng.uniform(-60, 60), rng.uniform(-60, 60), rng.uniform(0, 180)))
    # basket: jute rope cylinder D35 x 39 + two rope handles
    bprof = [(0.165, 0.0), (0.175, 0.02), (0.175, 0.39)]
    bx_, by_ = BASKET_C
    lathe("basket", bx_, by_, bprof, mtex("basket", "basket", 1.0), I["basket"], cap_top=False, ripple=(60, 0.006))
    jute = mcol("jute", "#B89B72", 1.0)
    for s in (-1, 1):
        for k in range(8):
            a0, a1 = math.pi * k / 8, math.pi * (k + 1) / 8
            p0 = (bx_ + s * 0.17, by_ + 0.05 * math.cos(a0), 0.39 + 0.07 * math.sin(a0))
            p1 = (bx_ + s * 0.17, by_ + 0.05 * math.cos(a1), 0.39 + 0.07 * math.sin(a1))
            seg("basket", p0, p1, 0.008, jute, I["basket"])
    # magazine holder: charcoal felt sling 45 x 32 x 40 between two oak handles, long side to the camera (rotated -8)
    felt = mtex("felt", "felt", 1.0)
    mx, my = -0.54, 2.52
    mh = lathe("magazine-holder", mx, my, [(0.15, 0.0), (0.18, 0.12), (0.21, 0.30)], felt, I["magazine-holder"], n=48, sx=1.07, sy=0.76, rotz=-8, cap_top=False)
    for v in mh.data.vertices:                          # the sling: the rim dips 8 cm in the middle of the long sides
        if v.co.z > 0.2:
            ph = math.atan2(v.co.y / 0.76, v.co.x / 1.07)
            v.co.z = v.co.z - 0.08 * math.sin(ph) ** 2
    for s in (-1, 1):
        a = math.radians(-8)                            # the long axis (cos a, sin a) = the camera's right vector
        hx, hy = mx + s * 0.215 * math.cos(a), my + s * 0.215 * math.sin(a)
        px, py = -math.sin(a), math.cos(a)              # across the holder
        seg("magazine-holder", (hx - 0.13 * px, hy - 0.13 * py, 0.40), (hx + 0.13 * px, hy + 0.13 * py, 0.40), 0.014, oak, I["magazine-holder"])
        for q in (-1, 1):
            seg("magazine-holder", (hx + q * 0.11 * px, hy + q * 0.11 * py, 0.29), (hx + q * 0.13 * px, hy + q * 0.13 * py, 0.40), 0.006, oak, I["magazine-holder"])
    paper = mcol("paper", "#ECE8E0", 0.6)
    for k, dx in enumerate((-0.06, 0.02, 0.09)):
        lbox("magazines (filler)", 0.23, 0.012, 0.30, paper, FILLER_IDX["magazines (filler)"], (mx + dx, my + 0.02 * k - 0.02, 0.25), rot=(8 * (k - 1), 0, -8))
    # floor lamp: paper lantern D17.5 x 85 on an oak tripod, H 128, base 29
    shade_fl = mcol("lantern_paper", "#EAE0CF", 0.9, emit=1.0)
    lathe("floor-lamp", 1.52, 0.20, [(0.0875, 0.43), (0.0875, 1.28)], shade_fl, I["floor-lamp"], n=48, lightgroup="floor_lamp_glow", shadow=False)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        seg("floor-lamp", (1.52 + 0.145 * math.cos(a), 0.20 + 0.145 * math.sin(a), 0.0), (1.52 + 0.05 * math.cos(a), 0.20 + 0.05 * math.sin(a), 0.47), 0.011, oak, I["floor-lamp"])
    light("floor_lamp_bulb", "POINT", (1.52, 0.20, 0.95), 3.0, "floor_lamp", size=0.05)
    # pendant: pleated pumpkin lantern D40 x 25, bottom 1.90, at (0.20, 1.72); cord to the ceiling
    shade_pd = mcol("pleat_fabric", "#F2EEE6", 0.9, emit=1.0)
    pprof = [(0.06, 0.0), (0.13, 0.02), (0.185, 0.07), (0.20, 0.125), (0.185, 0.18), (0.13, 0.23), (0.05, 0.25)]
    lathe("pendant", 0.20, 1.72, pprof, shade_pd, I["pendant"], z0=1.90, n=96, ripple=(24, 0.045), lightgroup="pendant_glow", shadow=False)
    cyl("pendant cord", 0.20, 1.72, 0.003, 2.15, 3.0, mcol("cord", "#EDEAE4", 0.6), FILLER_IDX["pendant cord"], n=8)
    light("pendant_bulb", "POINT", (0.20, 1.72, 2.02), 3.0, "pendant", size=0.06)
    # coffee table: the Olia (120 x 65 x 38, oak, light waterfall), centre (0.20, 1.72)
    cx, cy = 0.20, 1.72
    xa, xb, R, t = cx - 0.60, cx + 0.60, 0.05, 0.04
    prof = []
    for k in range(7):                                  # outer left bend
        a = math.pi - k * (math.pi / 2) / 6
        prof.append((xa + R + R * math.cos(a), 0.38 - R + R * math.sin(a)))
    for k in range(7):                                  # outer right bend
        a = math.pi / 2 - k * (math.pi / 2) / 6
        prof.append((xb - R + R * math.cos(a), 0.38 - R + R * math.sin(a)))
    prof += [(xb, 0.0), (xb - t, 0.0), (xb - t, 0.38 - t), (xa + t, 0.38 - t), (xa + t, 0.0), (xa, 0.0)]
    extrude_profile_y("coffee-table", prof, cy - 0.325, cy + 0.325, oak_light, I["coffee-table"])
    # runner: sage linen 33 x 122 across the left third (midline 31 cm from the left end), hanging over both long edges
    rmat = mcol("runner_sage_linen", "#A7B09A", 1.0, noise=0.08, nscale=(400, 60, 400), sheen=0.2)   # the photo crop carried a plate
    rx = xa + 0.31
    box("table-runner", rx - 0.165, rx + 0.165, cy - 0.33, cy + 0.33, 0.38, 0.384, rmat, I["table-runner"])
    box("table-runner", rx - 0.165, rx + 0.165, cy + 0.329, cy + 0.333, 0.10, 0.384, rmat, I["table-runner"])
    box("table-runner", rx - 0.165, rx + 0.165, cy - 0.333, cy - 0.329, 0.10, 0.384, rmat, I["table-runner"])
    # tray (travertine organic 24 x 17 x 1.8) with the pedestal pair on it; the bowl in front-right
    lathe("tray", 0.52, 1.64, [(0.0, 0.38), (0.105, 0.38), (0.12, 0.392), (0.115, 0.398), (0.0, 0.396)], mtex("tray", "tray", 0.8), I["tray"],
          n=48, sx=1.0, sy=0.71, cap_bottom=False, cap_top=False)
    cprof = [(0.035, 0.0), (0.032, 0.01), (0.018, 0.07), (0.016, 0.085), (0.032, 0.10), (0.034, 0.11)]
    for (hx, hy) in [(0.47, 1.62), (0.58, 1.66)]:
        lathe("candle-holders", hx, hy, cprof, trav, I["candle-holders"], z0=0.398, n=32)
        cyl("candles (filler)", hx, hy, 0.0275, 0.508, 0.608, mcol("wax", "#F3EFE6", 0.6), FILLER_IDX["candles (filler)"], n=24)
    lathe("bowl", 0.68, 1.92, [(0.0, 0.0), (0.05, 0.0), (0.09, 0.025), (0.1065, 0.052), (0.100, 0.052), (0.085, 0.03), (0.0, 0.012)],
          mtex("bowl", "bowl", 0.7), I["bowl"], z0=0.38, n=48, cap_bottom=False, cap_top=False)
    # cushions (set A) and the white muslin throw
    def cushion(sz, mat, loc, rz=0.0, tilt=16):
        ob = lbox("cushions", sz, 0.16, sz, mat, I["cushions"], loc, rot=(tilt, 0, rz), bev=0.07)
        return ob
    cushion(0.50, mtex("boucle", "boucle", 1.0), (-0.48, 0.47, 0.67), rz=6)
    cushion(0.45, mtex("sage", "sage", 1.0), (-0.12, 0.53, 0.645), rz=-4)
    cushion(0.50, mtex("charcoal", "charcoal", 1.0), (0.88, 0.47, 0.67), rz=-6)
    th = mcol("muslin_ivory", "#EEE9DF", 1.0, noise=0.06, nscale=(120, 120, 120), sheen=0.3)        # the White muslin (photo crop read grey)
    # over the right arm, across the right seat in front of the charcoal cushion, and falling down the seat front to the rug
    box("sofa-cover", 1.13, 1.33, 0.30, 0.95, 0.60, 0.632, th, I["sofa-cover"], bev=0.012)
    sheet("sofa-cover", lambda s, t: (0.70 + 0.46 * s, 0.58 + 0.38 * t, 0.448 + 0.02 * math.sin(3 * math.pi * s) * math.sin(math.pi * t)), 24, 16, th, I["sofa-cover"])
    sheet("sofa-cover", lambda s, t: (0.70 + 0.62 * s, 0.965 + 0.025 * math.sin(4 * math.pi * s) * t + 0.06 * max(0.0, t - 0.92) / 0.08, 0.448 - 0.432 * min(t / 0.92, 1.0)), 32, 14, th, I["sofa-cover"])
    # pouf: chunky knit ball 50 (filled height 35), the cut foreground right
    lathe("pouf", POUF_C[0], POUF_C[1], [(0.0, 0.0), (0.19, 0.01), (0.24, 0.07), (0.25, 0.17), (0.23, 0.27), (0.16, 0.335), (0.0, 0.35)],
          mtex("pouf", "pouf", 1.0), I["pouf"], n=64, cap_bottom=False, cap_top=False)
    # wall sconce (out of frame): black plate, swing arm, linen cone; its light on the armchair
    blk = mcol("black", "#2E2E2E", 0.5)
    box("wall-sconce", -2.30, -2.28, 3.12, 3.22, 1.40, 1.54, blk, I["wall-sconce"])
    seg("wall-sconce", (-2.28, 3.17, 1.47), (-1.95, 3.10, 1.47), 0.008, blk, I["wall-sconce"])
    lathe("wall-sconce", -1.95, 3.10, [(0.11, 1.30), (0.07, 1.48)], mcol("linen_shade", "#E9DFCC", 0.9, emit=1.0), I["wall-sconce"], n=32,
          cap_bottom=False, cap_top=False, lightgroup="wall_sconce_glow", shadow=False)
    light("wall_sconce_bulb", "SPOT", (-1.95, 3.10, 1.40), 5.0, "wall_sconce", size=0.04, aim=(-1.23, 2.73, 0.40), spot=80, blend=1.0)


def world_and_sun(sky=1.0, sun=4.0):
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("m0n_world")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.70, 0.80, 1.0, 1.0)       # pale clear sky, about 7,000 K in the shade
    bg.inputs["Strength"].default_value = sky
    sc.world.lightgroup = "sky"
    alt, az = sun_alt_az()
    th = math.radians(-(az - SUN["R"]))                               # Blender (physical) math angle from +X (= the window's outward normal)
    d = Vector((math.cos(th) * math.cos(math.radians(alt)), math.sin(th) * math.cos(math.radians(alt)), math.sin(math.radians(alt))))
    L = bpy.data.lights.new("sun", "SUN")
    L.energy, L.angle, L.color = sun, math.radians(SUN["angle"]), (1.0, 0.985, 0.955)
    ob = bpy.data.objects.new("sun", L)
    sc.collection.objects.link(ob)
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    ob.lightgroup = "sun"
    LIGHTS["sun"] = [ob]
    return dict(alt=round(alt, 2), az=round(az, 2), dir_blender=[round(x, 4) for x in d], dir_plan=[round(-d.x, 4), round(d.y, 4), round(d.z, 4)])


def sun_alt_az():
    la, de, ha = map(math.radians, (SUN["lat"], SUN["decl"], SUN["hour_angle"]))
    alt = math.asin(math.sin(la) * math.sin(de) + math.cos(la) * math.cos(de) * math.cos(ha))
    az = math.acos((math.sin(de) - math.sin(la) * math.sin(alt)) / (math.cos(la) * math.cos(alt)))
    return math.degrees(alt), 360.0 - math.degrees(az)


# ---------------------------------------------------------------------------------------------------------------------------------------
# camera, render, projection
# ---------------------------------------------------------------------------------------------------------------------------------------
def camera():
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("M0-N")
    ob = bpy.data.objects.new("M0-N", cd)
    sc.collection.objects.link(ob)
    y = math.radians(CAM["yaw"])
    f = Vector((math.sin(y), -math.cos(y), 0.0))                    # plan f = (-sin, -cos), mirrored
    r = Vector((-math.cos(y), -math.sin(y), 0.0))                   # plan r = (cos, -sin), mirrored
    up = Vector((0, 0, 1))
    ob.rotation_euler = Matrix((r, up, -f)).transposed().to_euler()
    ob.location = b(CAM["loc"])
    cd.lens, cd.sensor_fit, cd.sensor_width = CAM["lens"], "HORIZONTAL", 36.0
    cd.shift_x = 0.5 - CAM["u0"]
    cd.shift_y = (CAM["v0"] - 0.5) * 9.0 / 16.0
    cd.clip_start, cd.clip_end = 0.05, 200.0
    sc.camera = ob
    return ob


def plan_uv(X, Y, Z):
    y = math.radians(CAM["yaw"])
    dx, dy = X - CAM["loc"][0], Y - CAM["loc"][1]
    d = -math.sin(y) * dx - math.cos(y) * dy
    x = math.cos(y) * dx - math.sin(y) * dy
    return CAM["u0"] + KU * x / d, CAM["v0"] + KV * (CAM["loc"][2] - Z) / d, d


def projection_check(cam, W):
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    worst = 0.0
    for p in [(-2.3, 0.0, 1.6), (2.5, 0.0, 0.5), (0.2, 1.72, 2.15), (0.2, 0.0, 1.475), (-0.9, 0.95, 0.2), (1.7, 2.75, 0.35)]:
        u, v, _ = plan_uv(*p)
        q = world_to_camera_view(sc, cam, Vector(b(p)))
        worst = max(worst, abs(q.x - u) * W, abs((1 - q.y) - v) * W * 9 / 16)
    return round(worst, 3)


def setup_render(W, H, spp, override=None):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.threads_mode, sc.render.threads = "FIXED", os.cpu_count() or 4
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.seed = 23
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 8, 4, 2
    sc.cycles.transmission_bounces, sc.cycles.transparent_max_bounces = 4, 16
    sc.cycles.sample_clamp_indirect = 8.0
    sc.view_settings.view_transform = "Standard"
    vl = bpy.context.view_layer
    vl.use_pass_object_index = True
    vl.use_pass_z = True
    vl.cycles.denoising_store_passes = True
    for g in GROUPS:
        if g not in [x.name for x in vl.lightgroups]:
            vl.lightgroups.add(name=g)
    vl.material_override = override


def render_passes(tag, W, H, spp, override=None):
    """one render; returns dict group -> linear RGB (top row first), plus 'index' and 'depth'"""
    setup_render(W, H, spp, override)
    sc = bpy.context.scene
    out = os.path.join(SCR, "exr", tag)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    fo = nt.nodes.new("CompositorNodeOutputFile")
    fo.base_path = out
    fo.format.file_format, fo.format.color_depth, fo.format.exr_codec = "OPEN_EXR", "16", "ZIP"     # half float: the disk is tight
    fo.file_slots.clear()
    for g in GROUPS:
        dn = nt.nodes.new("CompositorNodeDenoise")
        dn.prefilter = "ACCURATE"
        nt.links.new(rl.outputs["Combined_" + g], dn.inputs["Image"])
        nt.links.new(rl.outputs["Denoising Normal"], dn.inputs["Normal"])
        nt.links.new(rl.outputs["Denoising Albedo"], dn.inputs["Albedo"])
        fo.file_slots.new(g)
        nt.links.new(dn.outputs[0], fo.inputs[g])
    for s in ("IndexOB", "Depth"):
        fo.file_slots.new(s)
        nt.links.new(rl.outputs[s], fo.inputs[s])
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"], comp.inputs[0])
    t0 = time.time()
    bpy.ops.render.render(write_still=False)
    print(f"render {tag} {W}x{H} {spp} spp: {time.time() - t0:.0f} s", flush=True)
    res = {}
    for g in GROUPS + ["IndexOB", "Depth"]:
        f = sorted(glob.glob(os.path.join(out, g + "*.exr")))[0]
        img = bpy.data.images.load(f)
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        a = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(a)
        a = a.reshape(h, w, 4)[::-1]
        bpy.data.images.remove(img)
        res[g] = a[..., :3].copy() if g in GROUPS else a[..., 0].copy()
    shutil.rmtree(out, ignore_errors=True)
    res["index"] = np.rint(res.pop("IndexOB")).astype(np.int32)
    res["depth"] = res.pop("Depth")
    return res


# ---------------------------------------------------------------------------------------------------------------------------------------
# the look (code, not var2): white balance, exposure by target L*, a soft shoulder, sRGB
# ---------------------------------------------------------------------------------------------------------------------------------------
def tone(lin, k, wb=(1, 1, 1), shoulder=0.72, lift=0.0):
    x = lin * np.array(wb, np.float32) * k
    y = np.where(x < shoulder, x, shoulder + (1 - shoulder) * (1 - np.exp(-(x - shoulder) / (1 - shoulder))))
    y = lift + (1 - lift) * np.clip(y, 0, 1)
    s = np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(y, 1 / 2.4) - 0.055)
    return np.clip(s, 0, 1)


def lab(srgb):
    return cv2.cvtColor(srgb.astype(np.float32), cv2.COLOR_RGB2Lab)


def patch(img_lab, p, W, H, r=6):
    u, v, _ = plan_uv(*p)
    x, y = int(round(u * W)), int(round(v * H))
    if not (r <= x < W - r and r <= y < H - r):
        return None
    a = img_lab[y - r:y + r + 1, x - r:x + r + 1].reshape(-1, 3)
    return [round(float(c), 1) for c in np.median(a, 0)]


PATCHES = {"back_wall_by_corner (-1.75,0,1.60)": (-1.75, 0.0, 1.60), "back_wall_right (1.90,0,1.60)": (1.90, 0.0, 1.60),
           "back_wall_above_art (0.20,0,2.30)": (0.20, 0.0, 2.30), "window_wall_reveal_back (-2.30,0.45,1.60)": (-2.30, 0.45, 1.60),
           "rug_front_left (-0.9,2.2,0.014)": (-0.9, 2.2, 0.014), "rug_right (1.30,1.20,0.014)": (1.30, 1.20, 0.014),
           "floor_front_right (2.2,2.9,0)": (2.2, 2.9, 0.0), "sofa_seat_mid (0.20,0.62,0.44)": (0.20, 0.62, 0.44)}


def crop(lin, p, W, H, r=6):
    u, v, _ = plan_uv(*p)
    x, y = int(round(u * W)), int(round(v * H))
    return lin[y - r:y + r + 1, x - r:x + r + 1]


def Lc(c, k, wb, lift):
    return float(np.median(lab(tone(c, k, wb, lift=lift))[..., 0]))


def solve_wb(lin, ab, p, W, H, r=6):
    """gains (G = 1) that put the patch at the target a*, b* (the wall's white balance); lin may be the patch crop itself"""
    cc = lin if lin.shape[0] <= 2 * r + 1 else crop(lin, p, W, H, r)
    c = np.median(cc.reshape(-1, 3), 0)
    Lt = float(cv2.cvtColor(np.float32([[np.clip(c / c.max() * 0.7, 0, 1) ** (1 / 2.2)]]), cv2.COLOR_RGB2Lab)[0, 0, 0])
    s = cv2.cvtColor(np.float32([[[Lt, ab[0], ab[1]]]]), cv2.COLOR_Lab2RGB)[0, 0]
    t = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    g = (t / np.maximum(c, 1e-9))
    return tuple(float(x) for x in g / g[1])


def solve_k(lin, wb, target, p, W, H, lift=0.0):
    c = lin if lin.shape[0] <= 13 else crop(lin, p, W, H)
    lo, hi = 0.01, 400.0
    for _ in range(50):
        k = math.sqrt(lo * hi)
        lo, hi = (k, hi) if Lc(c, k, wb, lift) < target else (lo, k)
    return math.sqrt(lo * hi)


def save_png(path, srgb, dither=True):
    x = srgb * 255.0
    if dither:
        x = x + np.random.default_rng(7).uniform(-0.5, 0.5, x.shape)
    Image.fromarray(np.clip(np.rint(x), 0, 255).astype(np.uint8)).save(path, optimize=True)


# ---------------------------------------------------------------------------------------------------------------------------------------
# measurements (V7Q6 and F3 as clay_m0w.py / framing_r2 frame_selfcheck)
# ---------------------------------------------------------------------------------------------------------------------------------------
def tris_plan(obs):
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
            v[:, 0] *= -1.0
            V.append(v)
            T.append(t + n)
            n += len(v)
    return (np.concatenate(V), np.concatenate(T)) if V else (np.zeros((0, 3)), np.zeros((0, 3), np.int64))


def uv_arr(V):
    y = math.radians(CAM["yaw"])
    dx, dy = V[:, 0] - CAM["loc"][0], V[:, 1] - CAM["loc"][1]
    d = -math.sin(y) * dx - math.cos(y) * dy
    x = math.cos(y) * dx - math.sin(y) * dy
    return CAM["u0"] + KU * x / d, CAM["v0"] + KV * (CAM["loc"][2] - V[:, 2]) / d, d


def silhouette(obs, W, H, margin):
    V, T = tris_plan(obs)
    m = np.zeros((H + 2 * margin, W + 2 * margin), np.uint8)
    if not len(T):
        return m.astype(bool)
    u, v, d = uv_arr(V)
    xy = np.stack([u * W + margin, v * H + margin], 1)
    ok = (d[T] > 0.05).all(1)
    polys = np.round(xy[T] * 4).astype(np.int32)
    for tri in polys[ok]:
        cv2.fillConvexPoly(m, tri, 1, lineType=cv2.LINE_8, shift=2)
    return m.astype(bool)


def aabb(obs):
    V, _ = tris_plan(obs)
    return V.min(0), V.max(0)


def aabb_dist(A, B):
    (a0, a1), (b0, b1) = A, B
    d = np.maximum(0, np.maximum(a0 - b1, b0 - a1))
    return float(np.sqrt((d ** 2).sum()))


def cloud(obs, n=3000):
    V, T = tris_plan(obs)
    if not len(T):
        return V
    a, bb, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(bb - a, c - a), axis=1)
    rng = np.random.default_rng(3)
    k = rng.choice(len(T), size=n, p=area / max(area.sum(), 1e-12))
    r1, r2 = rng.random(n), rng.random(n)
    s1 = np.sqrt(r1)
    return np.concatenate([V, (1 - s1)[:, None] * a[k] + (s1 * (1 - r2))[:, None] * bb[k] + (s1 * r2)[:, None] * c[k]])


def near3d(A, B, bA, bB):
    d0 = aabb_dist(bA, bB)
    if d0 >= 0.03:
        return d0
    P, Q = cloud(A), cloud(B)
    best = 1e9
    for i in range(0, len(P), 1500):
        best = min(best, float(np.sqrt(((P[i:i + 1500, None, :] - Q[None, :, :]) ** 2).sum(-1)).min()))
    return best


def thickness(m):
    if not m.any():
        return 0.0
    dt = cv2.distanceTransform(np.pad(m.astype(np.uint8), 1), cv2.DIST_L2, 5)
    return 2.0 * float(dt.max())


def boundary(m):
    return m & ~cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)


def min_dist(a, c):
    if (a & c).any():
        return 0.0
    dt = cv2.distanceTransform((~c).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[a].min())


def f3_pairs(N, FW):
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


CUT_FRONT = {"pouf"}                    # V7Q6: a cut foreground item counts from 25 % visible (the proposal's cut pouf)


def measure(idx, depth, W, H, margin):
    bpy.context.view_layer.update()
    FA = float(W * H)
    items = {k: REG[k] for k in PROD_IDX if k in REG}
    items["fixed:sofa"] = REG["sofa"]
    items["fixed:armchair"] = REG["armchair"]
    pid = dict(PROD_IDX, **{"fixed:sofa": SOFA_IDX, "fixed:armchair": ARMCHAIR_IDX})
    rows, N = {}, {}
    sl = (slice(margin, margin + H), slice(margin, margin + W))
    for k, obs in items.items():
        sil = silhouette(obs, W, H, margin)
        vis = idx == pid[k]
        ys, xs = np.nonzero(vis)
        r = dict(card=CARD.get(k, "fixed (not sold)"), position=POS.get(k, ""), visible_px=int(vis.sum()), frame_pct=round(100 * vis.sum() / FA, 3),
                 silhouette_px=int(sil.sum()), visible_share=round(float(vis.sum()) / max(1, sil.sum()), 3))
        if len(xs):
            r["u"] = [round(xs.min() / W, 4), round((xs.max() + 1) / W, 4)]
            r["v"] = [round(ys.min() / H, 4), round((ys.max() + 1) / H, 4)]
            n_, lab_, st_, _ = cv2.connectedComponentsWithStats(vis.astype(np.uint8), connectivity=8)
            big = [st_[i] for i in range(1, n_) if st_[i][4] >= 0.05 * vis.sum()]
            r["height_pct"] = round(100 * max(bb[3] for bb in big) / H, 2) if big else 0.0
            r["edge_margins"] = dict(left=r["u"][0], right=round(1 - r["u"][1], 4), top=r["v"][0], bottom=round(1 - r["v"][1], 4))
            r["edge_tangent"] = {s: m for s, m in r["edge_margins"].items() if 0 < m < 0.02}
        if not k.startswith("fixed:") and k != "wall-sconce":
            need = 0.25 if k in CUT_FRONT else 0.5
            counted = (r["frame_pct"] >= 0.5 or (r["frame_pct"] >= 0.15 and r.get("height_pct", 0) >= 6.0)) and r["visible_share"] >= need
            r["v7q6"] = ("counted" if counted else "NOT counted") + (" (cut front: 25 %)" if k in CUT_FRONT else "")
        rows[k] = r
        dd = depth[vis] if vis.any() else None
        N[k] = dict(sil=sil[sl], vis=vis, box=aabb(obs), obs=obs, dep=float(np.median(dd)) if dd is not None and len(dd) else 99.0)
    f3 = f3_pairs({k: v for k, v in N.items() if v["vis"].any()}, W)
    return rows, f3


# ---------------------------------------------------------------------------------------------------------------------------------------
def overlay(path, base, rows, sunmask, lampmask, W, H):
    im = Image.fromarray((base * 255).astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    for mask, col in [(sunmask, (255, 214, 0, 90)), (lampmask, (255, 140, 0, 70))]:
        a = np.zeros((H, W, 4), np.uint8)
        a[mask] = col
        ov = Image.alpha_composite(ov, Image.fromarray(a))
    d = ImageDraw.Draw(ov)
    for k, r in rows.items():
        if "u" not in r:
            continue
        ok = r.get("v7q6", "counted").startswith("counted")
        col = (40, 200, 90, 255) if ok else (230, 40, 40, 255)
        if k.startswith("fixed:"):
            col = (90, 140, 255, 255)
        x0, x1, y0, y1 = r["u"][0] * W, r["u"][1] * W, r["v"][0] * H, r["v"][1] * H
        d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=col, width=2)
        d.text((x0 + 3, y0 + 2), f"{k} {r['frame_pct']:.2f}% vis {int(100 * r['visible_share'])}%", fill=col, font=font)
    d.text((10, H - 24), "green = counted (V7Q6), red = not counted, blue = fixed; yellow = direct sun (B), orange = lamp light", fill=(255, 255, 255, 255), font=font)
    Image.alpha_composite(im, ov).convert("RGB").save(path, quality=88)


def ids_png(path, idx):
    rng = np.random.default_rng(11)
    lut = rng.integers(40, 255, (1024, 3)).astype(np.uint8)
    lut[0] = 0
    Image.fromarray(lut[np.clip(idx, 0, 1023)]).save(path, optimize=True)


# ---------------------------------------------------------------------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--res", type=int, default=1920)
    ap.add_argument("--spp", type=int, default=128)
    ap.add_argument("--clay-spp", type=int, default=64)
    a = ap.parse_args(argv)
    out = os.path.join(SCR, "quick") if a.quick else HERE
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(out, "concepts"), exist_ok=True)
    W = 640 if a.quick else a.res
    H = W * 9 // 16
    spp, cspp = (16, 16) if a.quick else (a.spp, a.clay_spp)
    t0 = time.time()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    shell()
    sofa()
    armchair()
    products()
    sun = world_and_sun(sky=1.0, sun=4.0)
    cam = camera()
    pc = projection_check(cam, W)
    print("projection check px", pc, flush=True)
    if pc > 0.5:
        raise SystemExit(f"camera does not match the plan projection ({pc} px)")

    # ---- 1. the material render: guides A and B from the light groups -----------------------------------------------------------------
    R = render_passes("mat", W, H, spp)

    def plum(lin, p, r=4):
        u, v, _ = plan_uv(*p)
        x, y = int(round(u * W)), int(round(v * H))
        return float(np.median(lin[y - r:y + r + 1, x - r:x + r + 1].reshape(-1, 3) @ LUMW))

    # the lamp pools: one physical weight per lamp, from the Bible's increments over A's daylight; the same in A and B
    day_A = R["sky"]
    wts, cal = {}, {}
    for g, (p, inc, what) in LAMP_CAL.items():
        wts[g] = inc * plum(day_A, p) / max(plum(R[g], p), 1e-12)
        cal[g] = dict(point=p, increment=inc, where=what, weight=round(wts[g], 5))
    pools = sum(wts[g] * R[g] for g in LAMP_GROUPS)
    # A: the Bible's tool light (north light, no direct sun, lamps on). The Bible's corner patch sits behind the back curtain stack in
    #    M0-N, so A and B are both exposed on the plain wall above the art; A at 88 (warm white, b* 7), lifted black L ~11.
    # B: the proposal (14:00 February sun; shaded walls L 80-86 -> 84, a touch cooler, b* 3.5; black point L 12-14).
    # The white balance is solved on the daylight alone (the lamps keep their 2700 K).
    mixes = {"A": dict(sky=1.0, sun=0.0, ab=(1.0, 7.0), target=("back_wall_above_art (0.20,0,2.30)", 87.0), lift=0.006, glow_L=95.0),
             "B": dict(sky=1.0, sun=1.0, ab=(0.5, 3.5), target=("back_wall_above_art (0.20,0,2.30)", 84.0), lift=0.013, glow_L=93.0,
                       sun_target=("rug_right (1.30,1.20,0.014)", 97.0))}
    # B: the sun's weight is solved (with the exposure and white balance inside the loop) so the sunlit cream rug reads L 97 (bright, still textured)
    mxB = mixes["B"]
    pw, pr = PATCHES[mxB["target"][0]], PATCHES[mxB["sun_target"][0]]
    cw = {g: crop(R[g], pw, W, H) for g in ("sky", "sun")}
    cr = {g: crop(R[g], pr, W, H) for g in ("sky", "sun")}
    cpw, cpr = crop(pools, pw, W, H), crop(pools, pr, W, H)
    lo, hi = 0.05, 4.0
    for _ in range(30):
        s_ = math.sqrt(lo * hi)
        wb_ = solve_wb(cw["sky"] + s_ * cw["sun"], mxB["ab"], pw, W, H)
        k_ = solve_k(cw["sky"] + s_ * cw["sun"] + cpw, wb_, mxB["target"][1], pw, W, H, mxB["lift"])
        lo, hi = (s_, hi) if Lc(cr["sky"] + s_ * cr["sun"] + cpr, k_, wb_, mxB["lift"]) < mxB["sun_target"][1] else (lo, s_)
    mxB["sun"] = round(math.sqrt(lo * hi), 4)
    look = {}
    for c, mx in mixes.items():
        day = mx["sky"] * R["sky"] + mx["sun"] * R["sun"]
        lin = day + pools
        mx["wb"] = solve_wb(day, mx["ab"], PATCHES[mx["target"][0]], W, H)
        k = solve_k(lin, mx["wb"], mx["target"][1], PATCHES[mx["target"][0]], W, H, mx["lift"])
        gw = {}
        for g, p in GLOW_CAL.items():                    # the shade's own glow, to the target L* on the shade (bisection)
            lo, hi = 0.0, 50.0
            for _ in range(36):
                w_ = (lo + hi) / 2
                L_ = patch(lab(tone(lin + w_ * R[g], k, mx["wb"], lift=mx["lift"])), p, W, H, r=3)[0]
                lo, hi = (w_, hi) if L_ < mx["glow_L"] else (lo, w_)
            gw[g] = (lo + hi) / 2
        gw["wall_sconce_glow"] = gw["pendant_glow"]     # out of frame: follows the pendant
        lin = lin + sum(gw[g] * R[g] for g in GLOW_GROUPS)
        img = tone(lin, k, mx["wb"], lift=mx["lift"])
        L = lab(img)
        look[c] = dict(mix=dict(sky=mx["sky"], sun=mx["sun"], sun_target=mx.get("sun_target"), lamp_pools=cal, shade_glow_weights={g: round(v, 4) for g, v in gw.items()}),
                       wb_gains=[round(g, 4) for g in mx["wb"]], wb_target_ab=mx["ab"], lift=mx["lift"], exposure_k=round(k, 4), target=mx["target"],
                       patches_Lab={n: patch(L, p, W, H) for n, p in PATCHES.items()},
                       shades_Lab={g: patch(L, p, W, H, r=3) for g, p in GLOW_CAL.items()},
                       lamp_increment_check={g: round(plum(wts[g] * R[g], p) / max(plum(day, p), 1e-12), 3) for g, (p, _, _) in LAMP_CAL.items()},
                       p0_5_L=round(float(np.percentile(L[..., 0], 0.5)), 1), clipped_pct=round(100 * float((img.max(-1) >= 0.995).mean()), 2))
        save_png(os.path.join(out, "concepts", f"guide-{c}.png"), img)
        Image.open(os.path.join(out, "concepts", f"guide-{c}.png")).save(os.path.join(out, "concepts", f"guide-{c}.jpg"), quality=90)
    idx, depth = R["index"], R["depth"]
    del R

    # ---- 2. the clay (white override): B light, sun map, lamp maps ----------------------------------------------------------------------
    wm = bpy.data.materials.new("m0n_white")
    wm.use_nodes = True
    wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    wm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    C = render_passes("clay", W, H, cspp, override=wm)
    clay_look = {}
    for c, mx in mixes.items():
        lin = mx["sky"] * C["sky"] + mx["sun"] * C["sun"] + sum(wts[g] * C[g] for g in LAMP_GROUPS)
        k = solve_k(lin, (1, 1, 1), 74.0, PATCHES["back_wall_above_art (0.20,0,2.30)"], W, H)
        img = tone(lin, k)
        save_png(os.path.join(out, "m0n-clay.png" if c == "B" else "m0n-clay-A.png"), img)
        clay_look[c] = dict(exposure_k=round(k, 4), target="back wall above the art L 74 (the clay is grey; the shades carry no glow here)",
                            patches_L={n: (patch(lab(img), p, W, H) or [None])[0] for n, p in PATCHES.items()})
    # sun map: the sun group's luminance on white surfaces (direct + its own bounce), 16 bit; 'in sun' = > 25 % of p99.5
    sl = C["sun"] @ LUMW
    ref = float(np.percentile(sl, 99.5))
    sunmask = sl > 0.25 * ref
    Image.fromarray(np.clip(np.rint(sl / ref * 65535), 0, 65535).astype(np.uint16)).save(os.path.join(out, "m0n-sun.png"), optimize=True)
    lampmask = np.zeros_like(sunmask)
    lamp_rec = {}
    for g in LAMP_GROUPS:
        lm = C[g] @ LUMW
        rf = float(np.percentile(lm, 99.5))
        Image.fromarray(np.clip(np.rint(lm / max(rf, 1e-12) * 65535), 0, 65535).astype(np.uint16)).save(os.path.join(out, f"m0n-light-{g.replace('_', '-')}.png"), optimize=True)
        lampmask |= lm > 0.30 * rf
        lamp_rec[g] = dict(p99_5=round(rf, 6), lit_px_pct=round(100 * float((lm > 0.30 * rf).mean()), 2), weight=round(wts[g], 5),
                           file=f"m0n-light-{g.replace('_', '-')}.png (16-bit, normalised to p99.5, white surfaces)")
    del C

    # ---- 3. measurements -----------------------------------------------------------------------------------------------------------------
    rows, f3 = measure(idx, depth, W, H, margin=int(0.6 * W))
    shell_ids = set(SHELL_IDX.values())
    sun_on = {}
    for k, pidx in list(PROD_IDX.items()) + [("fixed:sofa", SOFA_IDX), ("fixed:armchair", ARMCHAIR_IDX)]:
        m = idx == pidx
        if m.any():
            sun_on[k] = round(100 * float((sunmask & m).sum()) / float(m.sum()), 1)
    for nm, pidx in SHELL_IDX.items():
        m = idx == pidx
        if m.any():
            sun_on["shell:" + nm] = round(100 * float((sunmask & m).sum()) / float(m.sum()), 1)
    sky_px = (idx == 0)
    # depth (1/d, like ../../warm-modern/depth.json)
    dpos = depth[np.isfinite(depth) & (depth < 1e5)]
    near, far = float(dpos.min()), float(np.percentile(dpos, 99.9))
    inv = np.clip((1 / np.clip(depth, near, far) - 1 / far) / (1 / near - 1 / far), 0, 1)
    Image.fromarray(np.rint(inv * 65535).astype(np.uint16)).save(os.path.join(out, "m0n-depth.png"), optimize=True)
    json.dump(dict(encoding="16-bit PNG, value = (1/d - 1/far) / (1/near - 1/far), d = camera-plane depth in metres (Blender Z pass)", near_m=round(near, 4),
                   far_m=round(far, 4), camera=CAM["id"], size=[W, H]), open(os.path.join(out, "m0n-depth.json"), "w"), indent=1)
    ids_png(os.path.join(out, "m0n-ids.png"), idx)
    overlay(os.path.join(out, "m0n-overlay.jpg"), np.asarray(Image.open(os.path.join(out, "m0n-clay.png"))) / 255.0, rows, sunmask, lampmask, W, H)
    counted = [k for k, r in rows.items() if r.get("v7q6", "").startswith("counted")]
    rec = dict(id="m0n-clay-fb23-2026-11-26", author="render-agent", date="2026-11-26", var2_tokens=0, script="clay_m0n.py",
               size=[W, H], samples=dict(material=spp, clay=cspp, denoise="OIDN per light group (compositor)"),
               camera=CAM, projection_check_px=pc, sun=dict(SUN, **sun), lamps=lamp_rec, look_material=look, look_clay=clay_look,
               v7q6=rows, v7q6_counted=f"{len(counted)} of {len([r for r in rows.values() if 'v7q6' in r])}", v7q6_counted_list=counted,
               f3=f3, f3_fails=[r for r in f3 if r.get("verdict", "").startswith("FAIL")],
               sun_share_pct_per_item=sun_on, sky_pct_of_frame=round(100 * float(sky_px.mean()), 2), seconds=round(time.time() - t0))
    json.dump(rec, open(os.path.join(out, "clay-m0n.json"), "w"), indent=1, ensure_ascii=False, default=float)
    print("DONE", rec["v7q6_counted"], "counted;", len(rec["f3_fails"]), "F3 fails;", rec["seconds"], "s", flush=True)
    shutil.rmtree(os.path.join(SCR, "exr"), ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
