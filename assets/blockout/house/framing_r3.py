#!/usr/bin/env python3
"""
Framing clay, ROUND 3 (Phase B of briefs/nordic-house-render-2026-10-24.md, section 7; 2026-10-25). 0 var2 credits.

What round 3 is: the round-2 combined scene (framing_r2.build_r2: plan 1.1 + the picks H-B, C-B, W-A, MB-A + round-2 kids, bath,
kitchen-dining + S11/S12 additions), re-rendered for the 10 master frames with
  - the camera values of docs/house-plan.json 1.1.x (`cameras`), not the proposal's,
  - 3840 x 2160 (the i2i drafts are 2K+, the masters 4K; the clay lock is measured at the output size),
  - NEUTRAL albedo: every product placeholder in the M0 clay palette (build_alts.PAL), no warm-grey-per-slot colours, the kids'
    colour block as a neutral grey step; lamps at a milder 2700 K (as a 4600 K white balance would see them), so the clay carries
    no peach cast into the draft (render-recipe verdict section 3.4),
  - placeholders ONLY for the slots the designer lists per frame (docs/rooms-render-plan-2026-10-25.md -> framing/round3/plan.json);
    every other slot proxy of the frame's room is removed from the render, and neighbouring rooms show shell + fixed furniture only,
  - the living room seen from H0 / C0 = the M0 clay (shell + sofa, table, armchair; no slot proxies) plus only what plan.json lists
    under `also_visible` (e.g. living/pendant as the 40 cm pumpkin, living/wall-decor 30, living/accent-sconces),
  - the hall about 2/3 stop darker than the living room seen through the portal (--living-boost / --hall-roof, measured in selfcheck),
  - the 1.1.x frame fixes (house-plan.json frame_fixes_1_1_x, data/slots/*.json positions) on the placeholders that are rendered,
  - the verdict's H0 clay changes (section 3): table lamp and its light gone, 4 oval pegs instead of the hook board, vessel 31 x 15 at the
    console's right end, flat oval tray 22 x 9.5 in the middle, basket 30 under the bench's corner end, no board over the console.
Slots that have no round-2 proxy (step-stool, gallery-stool, storage-boxes, bench-throw, sill-vase, trinket-dish, bedside-carafe, ...)
are built from their data/slots plan_m when the plan lists them.

  python3 framing_r3.py --plan framing/round3/plan.json --frames all --res 3840 --samples 48
  python3 framing_r3.py --plan framing/round3/plan.json --frames H0 --res 960 --samples 12 --out /tmp/r3-smoke   # smoke test

Outputs (default OUT = framing/round3/): <frame>.png, overlays/<frame>.png, selfcheck.json, round2-vs-round3.jpg.
Round 2 (framing/round2/) is read only (its images for the comparison sheet) and never written.
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
OUT = os.environ.get("FRAMING_R3_OUT") or os.path.join(HERE, "framing", "round3")
os.environ.setdefault("FRAMING_R2_OUT", OUT)      # framing_r2 must never write into round2 from here

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_house as bh  # noqa: E402
import framing as fr  # noqa: E402
import framing_r2 as r2  # noqa: E402

ba, bs, b4 = bh.ba, bh.bs, bh.b4
M = ba.M
REPO = bh.REPO
R2DIR = os.path.join(HERE, "framing", "round2")
PLAN_JSON = os.path.join(REPO, "docs", "house-plan.json")
SLOTS_DIR = os.path.join(REPO, "data", "slots")

# round-3 frame id -> (room, round-2 frame/pick id, slots file, girl dy)
FRAMES = {
    "D1": ("kitchen-dining", "D1", "dining-room"),
    "D2": ("kitchen-dining", "D2", "dining-room"),
    "H0": ("hall", "H-B", "hall"),
    "C0": ("corridor", "C-B", "corridor"),
    "MB0": ("master", "MB-A", "master"),
    "K-boy": ("boy", "K2-boy", "kids"),
    "K-girl": ("girl", "K2-girl", "kids"),
    "B1": ("bath", "B1", "bath"),
    "B2": ("bath", "B2", "bath"),
    "W0": ("work", "W-A", "work"),
    "M0": ("living", "M0", "living-room"),
}
ORDER = ["D1", "D2", "H0", "C0", "MB0", "K-boy", "K-girl", "B1", "B2", "W0", "M0"]      # house-plan build order, M0 redone last
R2_IMAGE = {"D1": "D1", "D2": "D2", "H0": "H-B-lit", "C0": "C-B-lit", "MB0": "MB-A-lit", "K-boy": "K2-boy", "K-girl": "K2-girl",
            "B1": "B1", "B2": "B2", "W0": "W-A-lit", "M0": "../../../living-room/m0-clay-4k"}
PICKS = {"H0", "C0", "MB0", "W0"}
GIRL_DY = 3.63

# 2700 K lamps as a 4600 K-balanced camera sees them (blackbody 2700 K ~ (1.0, 0.63, 0.30) in D65 linear sRGB, divided by the
# 4600 K white ~ (1.0, 0.85, 0.66)). Round 2 used (1.0, 0.56, 0.25), which read as orange / peach.
WARM_R3 = (1.0, 0.74, 0.45)
PAINT_NEUTRAL = "#CFCAC3"       # the kids' colour block as a neutral grey step (wall #DDD8D1), colour comes from the prompt

CAT_MAT = {"textile": "textile", "lighting": "curtain", "ceramics/tableware": "obj", "storage/function": "obj", "decor/play": "art"}


# ---------------------------------------------------------------------------------------------------------------
# plan (which placeholders per frame) and cameras
# ---------------------------------------------------------------------------------------------------------------
def load_render_plan(path):
    p = json.load(open(path))
    for fid in ORDER:
        p["frames"].setdefault(fid, {})
        f = p["frames"][fid]
        f.setdefault("placeholders", [])
        f.setdefault("lamps", None)          # None = the S12 lamps of the room that are among the placeholders (+ shell lamps)
        f.setdefault("also_visible", [])     # "room/slot" of other rooms seen through openings
        f.setdefault("notes", "")
    return p


def cameras_1_1():
    plan = json.load(open(PLAN_JSON))
    C = {}
    for c in plan["cameras"]:
        if c["id"] in FRAMES and "lens" in c:
            C[c["id"]] = dict(id=c["id"], room=c["room"], loc=list(c["loc"]), yaw=c["yaw_deg_left"], u0=c["u0"], v0=c["v0"],
                              status=c.get("status", c.get("role", "")), hero=c.get("hero", ""))
    missing = [f for f in FRAMES if f not in C]
    if missing:
        raise SystemExit(f"house-plan.json has no camera for {missing}")
    return C, plan


def load_slots():
    out = {}
    for fn in os.listdir(SLOTS_DIR):
        if not fn.endswith(".json") or fn == "filler-replacements.json":
            continue
        d = json.load(open(os.path.join(SLOTS_DIR, fn)))
        out[fn[:-5]] = d
    return out


# ---------------------------------------------------------------------------------------------------------------
# unified registry of slot proxies: "room/slot" -> dict(objs, kind, src)
# ---------------------------------------------------------------------------------------------------------------
def alive(o):
    try:
        o.name
        return True
    except ReferenceError:
        return False


def registry(S):
    R = {}
    for k, v in fr.REG.items():
        if "/" in k and v["kind"] in ("proxy", "proxy-transit"):
            R[k] = dict(objs=[o for o in v["objs"] if alive(o)], kind=v["kind"], src="framing/framing_r2 (REG)")
    for k, v in S["prox"].items():
        objs = [o for o in v["objs"] if alive(o)]
        if objs and k not in R:
            R[k] = dict(objs=objs, kind="proxy", src="build_house.house_proxies (plan)")
    for k, v in S["lslots"].items():
        objs = [o for o in v["main"] + v["extra"] if alive(o)]
        R["living/" + k] = dict(objs=objs, kind="proxy", src="build_alts.build_slots (M0 slots)")
    return R


def set_hidden(objs, hidden):
    for o in objs:
        if alive(o):
            o.hide_render = hidden
            o.hide_viewport = hidden


# ---------------------------------------------------------------------------------------------------------------
# neutral albedo
# ---------------------------------------------------------------------------------------------------------------
def neutralise(S):
    notes = []
    n_wg = 0
    for k, v in fr.REG.items():
        if "/" not in k or v["kind"] not in ("proxy", "proxy-transit"):
            continue
        slot = k.split("/", 1)[1]
        cat = r2.CATEGORY.get(slot, "other")
        mat = M[CAT_MAT.get(cat, "obj")]
        for o in v["objs"]:
            if not alive(o) or o.type != "MESH" or not o.data.materials:
                continue
            m0 = o.data.materials[0]
            if m0 is not None and m0.name.startswith("wg_"):
                o.data.materials.clear()
                o.data.materials.append(mat)
                n_wg += 1
    notes.append(f"{n_wg} placeholder meshes moved from the round-2 warm greys to the M0 palette (textile {ba.PAL['textile']}, "
                 f"shade {ba.PAL['curtain']}, object {ba.PAL['obj']}, decor {ba.PAL['art']}); hardware ({ba.PAL['holder']}) kept")
    # the lamp glow materials are rebuilt by lamps_set from r2.glow_mat (WARM_R3 set before the build)
    pn = fr.mat_cache("paint_neutral", PAINT_NEUTRAL, 0.9)
    n_p = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.materials or o.data.materials[0] is None:
            continue
        if o.data.materials[0].name.startswith("paint_") and o.data.materials[0].name != "paint_neutral":
            o.data.materials.clear()
            o.data.materials.append(pn)
            n_p += 1
    notes.append(f"kids' colour block (G-K4) on {n_p} meshes as neutral grey {PAINT_NEUTRAL} (a readable step below the wall), no hue")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------------------
def bx(n, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
    return bs.box(n, x0, x1, y0, y1, z0, z1, mat, "framing", bevel=bevel)


def cyl(n, c, r, z0, z1, mat, verts=48):
    return bs.cone(n, c[0], c[1], z0, z1, r, r, mat, "framing", verts=verts)


def cone(n, c, r0, r1, z0, z1, mat, verts=48):
    return bs.cone(n, c[0], c[1], z0, z1, r0, r1, mat, "framing", verts=verts)


def ell(n, c, r, z0, z1, mat):
    return ba.ellipsoid(n, c, r, z0, z1, mat, "framing")


def oval_slab(n, cx, cy, rx, ry, z0, z1, mat):
    o = cyl(n, (cx, cy), 1.0, z0, z1, mat, verts=64)
    o.scale = (rx, ry, 1.0)
    bpy.context.view_layer.update()
    bs.apply_scale(o)
    return o


def obox(name, a, b, wvec, w, t, mat):
    return r2.obox(name, a, b, wvec, w, t, mat)


def kill_group(R, key):
    n = 0
    if key in R:
        n = r2.kill_objs([o for o in R[key]["objs"] if alive(o)])
        R[key]["objs"] = []
    if key in fr.REG:
        fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if alive(o)]
    return n


def reg(R, key, objs, room, kind="proxy", src="round 3"):
    objs = [o for o in objs if o is not None]
    fr.reg(key, objs, room, kind)
    R[key] = dict(objs=objs, kind=kind, src=src)
    return objs


def move(R, key, dx=0.0, dy=0.0, dz=0.0):
    n = 0
    for o in R.get(key, {}).get("objs", []):
        if alive(o):
            o.location = (o.location.x + dx, o.location.y + dy, o.location.z + dz)
            n += 1
    return n


def lamp_off(key):
    L = r2.LAMPS.get(key)
    if not L:
        return
    for li in L["lights"]:
        li.hide_render = True
    L["lights"] = []
    L["glow"] = []


def lamp_lights_at(key, lights):
    """Replace a lamp's light sources (after a proxy was rebuilt elsewhere)."""
    L = r2.LAMPS.get(key)
    if not L:
        return
    for li in L["lights"]:
        li.hide_render = True
    L["lights"] = lights
    for li in lights:
        li.hide_render = True


# ---------------------------------------------------------------------------------------------------------------
# generic placeholder from data/slots plan_m (for slots that have no round-2 proxy)
# ---------------------------------------------------------------------------------------------------------------
def generic_proxy(R, room, slot, sdef, dy=0.0):
    pm = sdef.get("plan_m") or {}
    env = sdef.get("envelope_cm") or {}
    cat = r2.CATEGORY.get(slot, "other")
    mat = M[CAT_MAT.get(cat, "obj")]
    name = f"r3_{room}_{slot}".replace("-", "_")
    objs = []
    z = pm.get("z", [0.0, 0.3])
    if "x" in pm and "y" in pm and isinstance(pm["x"][0], (int, float)) and "w_each" in env and isinstance(env["w_each"], list):
        w = sum(env["w_each"]) / 200.0
        xc = (pm["x"][0] + pm["x"][1]) / 2
        for i, x0 in enumerate((xc - w - 0.015, xc + 0.015)):
            objs.append(bx(f"{name}{i}", x0, x0 + w, pm["y"][0] + dy, pm["y"][1] + dy, z[0], z[1], mat, 0.01))
    elif "x" in pm and "y" in pm and isinstance(pm["x"][0], (int, float)):
        objs.append(bx(name, pm["x"][0], pm["x"][1], pm["y"][0] + dy, pm["y"][1] + dy, z[0], z[1], mat, 0.01))
    elif "x" in pm and "y" in pm:                       # list of x ranges (a pair)
        for i, xr in enumerate(pm["x"]):
            objs.append(bx(f"{name}{i}", xr[0], xr[1], pm["y"][0] + dy, pm["y"][1] + dy, z[0], z[1], mat, 0.01))
    elif "center" in pm:
        d = env.get("d") or env.get("pot_d") or env.get("base_d") or [0.20, 0.24]
        r = (sum(d) / len(d) if isinstance(d, list) else d) / 200.0
        objs.append(cyl(name, (pm["center"][0], pm["center"][1] + dy), r, z[0], z[1], mat))
    elif "centers" in pm:
        d = env.get("d") or [0.20, 0.24]
        r = (sum(d) / len(d) if isinstance(d, list) else d) / 200.0
        for i, c in enumerate(pm["centers"]):
            objs.append(cyl(f"{name}{i}", (c[0], c[1] + dy), r, z[0], z[1], mat))
    else:
        return None
    reg(R, f"{room}/{slot}", objs, room, src=f"generic from data/slots ({slot}.plan_m)")
    return objs


# ---------------------------------------------------------------------------------------------------------------
# the verdict's H0 changes + 1.1.x fixes, slot by slot (only the geometry; visibility is decided per frame)
# ---------------------------------------------------------------------------------------------------------------
def apply_fixes(S, R, slots, cube_lamp=None):
    notes = []
    O, Hd, T, A = M["obj"], M["holder"], M["textile"], M["art"]
    # ---- hall (verdict section 3) --------------------------------------------------------------------------
    kill_group(R, "hall/table-lamp")
    lamp_off("hall/table-lamp")
    notes.append("hall/table-lamp: proxy and both light sources removed (verdict 3.1)")
    kill_group(R, "hall/console-vessel")
    reg(R, "hall/console-vessel", [cyl("h_vessel_r3", (3.22, 6.50), 0.075, 0.80, 1.11, O)], "hall",
        src="hall.json: (3.22, 6.50), 31 x 15")
    kill_group(R, "hall/key-tray")
    reg(R, "hall/key-tray", [oval_slab("h_tray_r3", 3.00, 6.50, 0.11, 0.0475, 0.80, 0.83, Hd)], "hall",
        src="hall.json: X 2.91-3.09, Y 6.44-6.56, flat oval 22 x 9.5")
    kill_group(R, "hall/basket")
    reg(R, "hall/basket", [cyl("h_basket_r3", (1.00, 6.85), 0.15, 0.0, 0.26, O)], "hall", src="hall.json 1.1: centre (1.00, 6.85), d 30, h 26 (envelope 26-30; h 28 left 0.0175 to the cushion)")
    kill_group(R, "hall/wall-hooks")
    pegs = [obox(f"h_peg_r3_{i}", (0.80, y, 1.70), (0.86, y, 1.70), (0, 0, 1), 0.035, 0.025, Hd) for i, y in enumerate((6.80, 7.00, 7.20, 7.40))]
    reg(R, "hall/wall-hooks", pegs, "hall", src="verdict 3.2: 4 oval pegs at Z 1.70, no board; R5C1 length 60; Y 6.80-7.40 so the third peg clears the left edge by >= 0.02 (edge meets the wall at Y 7.29) and the fourth is outside")
    # hall/wall-sconce: the designer's card is a 15 cm white fabric cube (h0-B.txt); plate (0.80, 6.95, 1.94), electrical_points_1_1
    kill_group(R, "hall/wall-sconce")
    hcube = bx("h_cube_r3", 0.80, 0.95, 6.875, 7.025, 1.865, 2.015, M["curtain"], 0.012)
    reg(R, "hall/wall-sconce", [hcube], "hall", src="h0-B.txt: wall-sconce-cj-white-fabric-cube-15-hall, 15 cm cube on the plate (0.80, 6.95, 1.94)")
    r2.lamp("hall/wall-sconce", "hall", "wall", [(hcube, r2.GLOW)],
            [r2.mk_light("h_cube_L", "POINT", (0.99, 6.95, 1.94), 12.0, size=0.06)], "15 cm fabric cube wall light (h0-B.txt)")
    kill_group(R, "hall/framed-art")
    reg(R, "hall/framed-art", [bx("h_art_r3", 2.725, 3.175, 6.35, 6.38, 1.30, 1.85, M["art"])], "hall",
        src="h0-B.txt: swinging-line print, option 45 x 55, centred on the console (hall.json X 2.67-3.23 envelope)")
    notes.append("hall/wall-sconce rebuilt as a 15 cm fabric cube (lit); hall/framed-art 45 x 55 centred on X 2.95")
    if cube_lamp:
        c = cube_lamp
        cube = bx("h_cube_r3", c[0] - 0.075, c[0] + 0.075, c[1] - 0.075, c[1] + 0.075, c[2], c[2] + 0.15, M["curtain"], 0.01)
        reg(R, "hall/table-lamp", [cube], "hall", src="plan.json cube_lamp: 15 cm fabric cube, lit")
        r2.lamp("hall/table-lamp", "hall", "task", [(cube, r2.GLOW)],
                [r2.mk_light("h_cube_L", "POINT", (c[0], c[1], c[2] + 0.075), 10.0, size=0.06)], "15 cm fabric cube lamp (plan.json)")
        notes.append(f"hall/table-lamp rebuilt as a 15 cm fabric cube at {c} (plan.json cube_lamp)")
    # storage-boxes / bench-throw are generic from hall.json when listed (pair of boxes; folded throw on the cushion)
    # ---- corridor ------------------------------------------------------------------------------------------
    kill_group(R, "corridor/runner-rug")
    reg(R, "corridor/runner-rug", [bx("c_runner_r3", 2.10, 2.70, 10.10, 17.20, 0.0, 0.012, M["rug"])], "corridor",
        src="corridor.json 1.0: X 2.10-2.70 (60 wide)")
    notes.append("corridor/runner-rug narrowed to 60 (X 2.10-2.70) for the gallery stool (frame_fixes_1_1_x.C0)")
    # ---- work -----------------------------------------------------------------------------------------------
    kill_group(R, "work/pendant")
    wp = cone("w_pend_r3", (-0.825, 6.82), 0.14, 0.07, 1.58, 1.76, M["curtain"])
    reg(R, "work/pendant", [wp, cyl("w_pcord_r3", (-0.825, 6.82), 0.005, 1.76, 3.0, Hd, 12)], "work", src="work.json 1.1: d 28, h 18, bottom 1.58")
    L = r2.LAMPS.get("work/pendant")
    if L:
        L["glow"] = [(wp, r2.GLOW)]
        L["orig"] = {wp.name: wp.data.materials[0]}
        lamp_lights_at("work/pendant", [r2.mk_light("w_pend_L_r3", "AREA", (-0.825, 6.82, 1.575), 24.0, size=0.20)])
    notes.append("work/pendant: d 28, h 18, bottom Z 1.58 (frame_fixes_1_1_x.W0; was d 34, bottom 1.50)")
    kill_group(R, "work/wall-sconce")
    ws_shade = cone("w_sshade_r3", (-2.165, 6.65), 0.065, 0.04, 1.62, 1.78, M["curtain"])
    reg(R, "work/wall-sconce", [cyl("w_splate_r3", (-2.29, 6.65), 0.04, 1.69, 1.71, Hd, 24),
                                obox("w_sarm_r3", (-2.29, 6.65, 1.70), (-2.165, 6.65, 1.78), (0, 1, 0), 0.015, 0.015, Hd), ws_shade], "work",
        src="work.json 1.1.2: plate (-2.30, 6.65, 1.70), straight arm, shade X -2.23..-2.10, d 13")
    L = r2.LAMPS.get("work/wall-sconce")
    if L:
        L["glow"] = [(ws_shade, r2.GLOW)]
        L["orig"] = {ws_shade.name: ws_shade.data.materials[0]}
        lamp_lights_at("work/wall-sconce", [r2.mk_light("w_sconce_L_r3", "POINT", (-2.165, 6.65, 1.60), 12.0, size=0.05)])
    notes.append("work/wall-sconce: plate Y 6.75 -> 6.65, arm sconce (projection 0.135 to the shade centre, shade d 13) per 1.1.2 N2")
    # the plate's shift_x direction: the round-1 curtains of the work room (plan proxies) move with the rod
    wc = R.get("work/curtains", {}).get("objs", [])
    R.setdefault("work/curtains", dict(objs=[], kind="proxy", src="build_house.house_proxies (plan)"))
    for o in wc:
        if alive(o) and o.name == "w_curt_a":
            o.location.y += 0.10
        if alive(o) and o.name == "w_rod":
            r2.kill_objs([o])
    wc = [o for o in wc if alive(o)]
    rod = bx("w_rod_r3", -2.25, -2.23, 7.00, 8.60, 2.81, 2.83, Hd)
    rod.pass_index = wc[0].pass_index if wc else 0
    R["work/curtains"]["objs"] = wc + [rod]
    notes.append("work/curtains: east stack Y 6.93-7.15 -> 7.03-7.25, rod Y 6.90 -> 7.00 (to 8.60), rod Z 2.82 (work.json 1.0.2)")
    # ---- kids (both rooms) ----------------------------------------------------------------------------------
    for kid, dy in (("boy", 0.0), ("girl", GIRL_DY)):
        y0 = 10.25 + dy
        move(R, f"{kid}/toy-basket", dx=0.08, dy=0.13)              # (-0.70, 11.45) -> (-0.62, 11.58)
        move(R, f"{kid}/desk-chair", dx=0.11)                        # (0.55, 11.00) -> (0.66, 11.00)
        move(R, f"{kid}/framed-prints", dz=-0.05)                    # Z 1.42-1.82 -> 1.37-1.77
        if kid == "boy":
            kill_group(R, "boy/skateboard")
            deck = obox("boy_deck_r3", (0.22, y0 + 0.70, 0.03), (0.22, y0 + 0.46, 0.81), (1, 0, 0), 0.20, 0.013, A)
            truck = obox("boy_truck_r3", (0.22, y0 + 0.72, 0.03), (0.22, y0 + 0.705, 0.075), (1, 0, 0), 0.17, 0.05, Hd)
            reg(R, "boy/skateboard", [deck, truck], "boy", src="frame_fixes_1_1_x: steeper lean, foot Y 10.95, top on the desk front edge")
        else:
            kill_group(R, "girl/doll-pram")
            pr = A
            body = [bx("girl_pram_r3", 0.12, 0.40, y0 + 0.57, y0 + 1.03, 0.16, 0.42, pr, 0.03),
                    bx("girl_pramw0_r3", 0.10, 0.12, y0 + 0.60, y0 + 1.00, 0.0, 0.16, pr),
                    bx("girl_pramw1_r3", 0.40, 0.42, y0 + 0.60, y0 + 1.00, 0.0, 0.16, pr),
                    obox("girl_pramh_r3", (0.26, y0 + 1.03, 0.40), (0.26, y0 + 1.05, 0.64), (1, 0, 0), 0.26, 0.02, pr),
                    bx("girl_pramfill_r3", 0.15, 0.37, y0 + 0.62, y0 + 0.98, 0.42, 0.46, T, 0.015)]
            reg(R, "girl/doll-pram", body, "girl", src="kids.json 1.1: long axis Y, X 0.10-0.42, Y 14.43-14.93, handle toward the camera")
    notes.append("kids: toy basket to (-0.62, 11.58) (+girl dy), desk chair to (0.66, 11.00), prints lowered 0.05, boy skateboard steeper "
                 "(foot Y 10.95), girl pram rotated along Y (frame_fixes_1_1_x)")
    # ---- master ---------------------------------------------------------------------------------------------
    move(R, "master/candle-holders", dx=0.08)                        # (0.42/0.53, ..) -> (0.50/0.61, ..)
    move(R, "master/nightstand-vase", dx=-0.075, dy=-0.02)           # (-1.875, 17.86) -> (-1.95, 17.84)
    notes.append("master: candle holders +0.08 X, nightstand vase to (-1.95, 17.84) (master.json 1.0.2)")
    # ---- bath -----------------------------------------------------------------------------------------------
    kill_group(R, "bath/shower-curtain")
    folds = [(5.252, 11.135), (5.297, 11.16), (5.342, 11.13), (5.387, 11.155), (5.432, 11.135), (5.327, 11.095), (5.372, 11.10)]
    reg(R, "bath/shower-curtain", [cyl(f"curt_r3_{i}", c, 0.036, 0.015, 2.655, T, 20) for i, c in enumerate(folds)], "bath",
        src="bath.json 1.1: gathered at (5.30, 11.15), 0.10 past the L corner on the Y 11.15 run; folds centred X 5.34 so the B2 overlap with the corner line is >= 0.03 (smoke tests: 5.31 -> 0.0215, 5.33 -> 0.0246)")
    move(R, "bath/bin", dx=0.005, dy=-0.19)                          # (4.635, 10.29) -> (4.64, 10.10)
    move(R, "bath/toilet-brush", dy=0.255)                            # (4.70, 10.045) -> (4.70, 10.30)
    move(R, "bath/toilet-paper-stand", dy=0.01)                       # (4.50, 10.07) -> (4.50, 10.08)
    notes.append("bath: curtain gathered at (5.30, 11.15); floor group stand (4.50, 10.08), bin (4.64, 10.10), brush in front (4.70, 10.30)")
    # ---- kitchen-dining: card sizes (rooms-render-plan 3, D1 / D2) --------------------------------------------
    kd = "kitchen-dining"
    kill_group(R, f"{kd}/dining-pendant")
    dps = cone("dpend_r3", (4.60, 1.65), 0.25, 0.11, 1.50, 1.86, M["curtain"], 64)
    reg(R, f"{kd}/dining-pendant", [dps, cyl("dpend_r3c", (4.60, 1.65), 0.005, 1.86, 3.0, Hd, 12)], kd, src="plan 3: lantern 50 x 36, bottom 1.50")
    L = r2.LAMPS.get(f"{kd}/dining-pendant")
    if L:
        L["glow"] = [(dps, r2.GLOW)]
        L["orig"] = {dps.name: dps.data.materials[0]}
    kill_group(R, f"{kd}/table-runner")
    reg(R, f"{kd}/table-runner", [bx("drun_r3", 3.90, 5.30, 1.45, 1.85, 0.75, 0.753, T)], kd, src="plan 3: runner 40 x 140")
    kill_group(R, f"{kd}/centerpiece-vase")
    reg(R, f"{kd}/centerpiece-vase", [cyl("dvase_r3", (4.60, 1.65), 0.0875, 0.754, 1.02, O), ell("dvase_olive_r3", (4.60, 1.65), 0.15, 0.96, 1.24, M["crown"])],
        kd, src="plan 3: vase 26.5 x 17.5 at (4.60, 1.65), olive sprigs filler")
    kill_group(R, f"{kd}/candle-holders")
    ch = []
    for i, (c, h) in enumerate((((4.17, 1.61), 0.15), ((4.29, 1.70), 0.10))):                 # 5 cm toward -X (annex 4 says 3; the chair-back sliver needed 2 more)
        ch.append(cyl(f"dcand_r3_{i}p", c, 0.0525, 0.754, 0.784, Hd))
        ch.append(cyl(f"dcand_r3_{i}c", c, 0.035, 0.784, 0.784 + h, O))
    reg(R, f"{kd}/candle-holders", ch, kd, src="plan 3: two iron plates 10.5 x 3 with candles 7 x 15 / 7 x 10, moved 3 cm to -X")
    kill_group(R, f"{kd}/bench-pad")
    reg(R, f"{kd}/bench-pad", [bx("bpad_r3", 3.95, 5.25, 2.30, 2.65, 0.45, 0.48, T, 0.01)], kd, src="plan 3: bench pad 130 x 35 x 3")
    kill_group(R, f"{kd}/condiment-set")
    reg(R, f"{kd}/condiment-set", [cyl("kmill_r3a", (7.12, 3.07), 0.025, 0.90, 1.05, O), cyl("kmill_r3b", (7.12, 3.15), 0.025, 0.90, 1.05, O)],
        kd, src="plan 3: mill pair 15, no oil bottle")
    kill_group(R, f"{kd}/bowl")
    reg(R, f"{kd}/bowl", [cyl("kbowl_r3", (7.07, 3.55), 0.105, 0.90, 0.964, O), ell("kpears_r3", (7.07, 3.55), 0.085, 0.93, 1.03, O)],
        kd, src="plan 3: belly bowl 21 x 6.4 at (7.07, 3.55), pears filler")
    kill_group(R, f"{kd}/tableware-set")
    reg(R, f"{kd}/tableware-set", [cyl("kplates_r3", (7.12, 3.38), 0.14, 1.58, 1.68, O)], kd, src="plan 3: plate stack 28 at (7.12, 3.38), plates only")
    kill_group(R, f"{kd}/mug-set")
    reg(R, f"{kd}/mug-set", [cyl(f"kmug_r3{i}", (7.10, yy), 0.04, 1.58, 1.67, O) for i, yy in enumerate((3.60, 3.70, 3.80))],
        kd, src="plan 3: three mugs 9; group 4 cm further from the right edge (round 2: 0.012 from it; smoke at 2 cm: 0.0167)")
    kill_group(R, f"{kd}/paper-towel-holder")
    reg(R, f"{kd}/paper-towel-holder", [cyl("kptb_r3", (7.12, 4.05), 0.065, 0.90, 0.91, O), cyl("kptr_r3", (7.12, 4.05), 0.06, 0.91, 1.21, O)],
        kd, src="plan 3: upright holder 13 x 31 at (7.12, 4.05)")
    kill_group(R, f"{kd}/canisters")
    reg(R, f"{kd}/canisters", [cyl(f"kcan_r3{i}", (6.82, yy), 0.055, 0.915, 0.915 + h, O) for i, (yy, h) in enumerate(((4.70, 0.22), (4.87, 0.18), (5.04, 0.14)))],
        kd, src="plan 3: three canisters d 11, h 22 / 18 / 14")
    kill_group(R, f"{kd}/tea-towel")
    reg(R, f"{kd}/tea-towel", [bx("ktowel_r3", 6.53, 6.60, 5.49, 5.71, 1.02, 1.35, T, 0.008)], kd,
        src="plan 3: folded towel 22 x 33 on the oven bar, thicker fold so >= 50 % shows (round 2: 47 %)")
    kill_group(R, f"{kd}/dining-rug")
    reg(R, "kitchen-dining/dining-rug", [bx("drug_r3", 3.45, 5.75, 0.55, 2.75, 0.0, 0.010, M["rug"])], "kitchen-dining",
        src="dining-room.json 0.2: X 3.45-5.75, Y 0.55-2.75 (230 x 220)")
    kill_group(R, "kitchen-dining/kitchen-runner")
    reg(R, "kitchen-dining/kitchen-runner", [bx("krun_r3", 6.00, 6.60, 1.00, 3.80, 0.0, 0.010, M["rug"])], "kitchen-dining",
        src="plan 3: Medina runner 60 x 280 (slot X 6.08-6.58 is 50 wide; 60 centred on 6.30, 25 cm clear of the rug)")
    notes.append("kitchen-dining: rug 230 x 220 (X 3.45-5.75), runner 60 x 280 (X 6.00-6.60); pendant 50 x 36, runner 40 x 140, vase 26.5, "
                 "candle plates + candles, bench pad 130 x 35 x 3, mills 15, bowl 21 x 6.4, plate stack 28, mugs 9, towel holder 13 x 31, canisters, tea towel 22 x 33")
    # ---- hall: card sizes --------------------------------------------------------------------------------------
    kill_group(R, "hall/console-vessel")
    reg(R, "hall/console-vessel", [cyl("h_vessel_r3b", (3.22, 6.50), 0.0875, 0.80, 1.065, O)], "hall", src="plan 3: vessel 26.5 at (3.22, 6.50)")
    kill_group(R, "hall/bench-cushion")
    reg(R, "hall/bench-cushion", [bx("h_cush_r3", 0.825, 1.175, 6.60, 7.70, 0.45, 0.48, T, 0.01)], "hall", src="plan 3: bench cushion 110 x 35 x 3")
    reg(R, "hall/bench-throw", [bx("h_throw_r3", 0.835, 1.165, 6.62, 6.95, 0.48, 0.54, T, 0.015)], "hall",
        src="plan 3: folded throw ~33 x 33 x 6 on the cushion at the bench's corner end")
    kill_group(R, "hall/umbrella-stand")
    reg(R, "hall/umbrella-stand", [cyl("h_umb_r3", (3.47, 6.88), 0.095, 0.0, 0.49, O, 6), cyl("h_umbf_r3", (3.45, 6.86), 0.015, 0.49, 0.90, Hd, 12)], "hall",
        src="plan 3: hex bucket 19 x 49 with a closed umbrella; X 3.42 -> 3.47 so it clears the console end (frame_fixes_1_1_x.H0: 0.012 kissing)")
    notes.append("hall: vessel 26.5, cushion 110 x 35 x 3, throw 33 x 33 at the corner end, bucket 19 x 49 moved to X 3.47")
    # ---- corridor: gallery squares 40 x 40 centred Z 1.45, paper lanterns 40 x 22 bottom 2.45 (plan 3, C0) ----
    kill_group(R, "corridor/gallery-art")
    reg(R, "corridor/gallery-art", [bx(f"c_art_r3{i}", 1.70, 1.73, a, a + 0.40, 1.25, 1.65, A) for i, a in enumerate((14.0, 14.6, 15.2))], "corridor",
        src="plan 3: three 40 x 40, Y 14.0-14.4 / 14.6-15.0 / 15.2-15.6, centre Z 1.45")
    kill_group(R, "corridor/ceiling-lights")
    cls, cll = [], []
    for i, y in enumerate((11.70, 15.10)):
        cls.append(ell(f"c_lant_r3{i}", (2.40, y), 0.20, 2.45, 2.67, M["curtain"]))
        cls.append(cyl(f"c_lantc_r3{i}", (2.40, y), 0.004, 2.67, 2.70, Hd, 12))
        cll.append(r2.mk_light(f"c_lant_L_r3{i}", "AREA", (2.40, y, 2.445), 26.0, size=0.30))
    reg(R, "corridor/ceiling-lights", cls, "corridor", src="plan 3: two flat oval paper lanterns 40 x 22 on short cords, bottom 2.45")
    L = r2.LAMPS.get("corridor/ceiling-lights")
    if L:
        L["glow"] = [(o, r2.GLOW) for o in cls if "lant_r3" in o.name and "lantc" not in o.name]
        L["orig"] = {o.name: o.data.materials[0] for o, _ in L["glow"]}
        lamp_lights_at("corridor/ceiling-lights", cll)
    notes.append("corridor: gallery 3 x 40 x 40 at Z 1.25-1.65; lanterns 40 x 22, bottom 2.45, lit")
    # ---- master: card sizes (plan 3, MB0) -----------------------------------------------------------------------
    kill_group(R, "master/framed-art")
    reg(R, "master/framed-art", [bx(f"m_art_r3{i}", x0, x0 + 0.50, 17.66, 17.69, 1.45, 1.95, A) for i, x0 in enumerate((-1.25, -0.65))], "master",
        src="plan 3: two 50 x 50 with a 10 gap, X -1.25..-0.15, centre Z 1.70")
    kill_group(R, "master/bedside-sconces")
    ms = [bx(f"m_sc_r3{i}", x - 0.12, x + 0.12, 17.66, 17.76, 1.24, 1.44, M["curtain"], 0.01) for i, x in enumerate((-1.875, 0.475))]
    reg(R, "master/bedside-sconces", ms, "master", src="plan 3: linen wave flush pair 24 x 20, plates (-1.875 / 0.475, Z 1.34)")
    L = r2.LAMPS.get("master/bedside-sconces")
    if L:
        L["glow"] = [(o, r2.GLOW) for o in ms]
        L["orig"] = {o.name: o.data.materials[0] for o in ms}
    kill_group(R, "master/planter")
    reg(R, "master/planter", [cyl("m_pot_r3", (1.48, 18.15), 0.175, 0.0, 0.37, O), cyl("m_plt_r3", (1.48, 18.15), 0.34, 0.37, 1.75, M["crown"])], "master",
        src="plan 3: seagrass pot cover 35 x 37, olive to 1.75; X 1.45 -> 1.48 for the 0.02 gap to the throw (frame_fixes_1_1_x.MB0)")
    kill_group(R, "master/nightstand-vase")
    reg(R, "master/nightstand-vase", [cyl("m_vas_r3", (-1.95, 17.84), 0.055, 0.55, 0.795, O)], "master", src="plan 3: vase 11 x 24.5 on the nightstand top (no tray)")
    kill_group(R, "master/candle-holders")
    reg(R, "master/candle-holders", [cyl("m_cn_r3a", (0.50, 17.88), 0.035, 0.55, 0.66, O), cyl("m_cn_r3b", (0.61, 17.82), 0.035, 0.55, 0.66, O)], "master",
        src="plan 3: travertine pedestal pair 7 x 11 on the right nightstand")
    kill_group(R, "master/bedding")
    reg(R, "master/bedding", [bx("m_duv_r3", -1.57, 0.17, 18.18, 19.68, 0.50, 0.58, T, 0.02)], "master",
        src="plan 3: washed linen duvet; starts under the pillows (Y 18.18) so the pillow / duvet line is a decisive overlap (round 2 sliver 0.012)")
    kill_group(R, "master/throw")
    reg(R, "master/throw", [bx("m_thr_r3", -1.61, 0.19, 19.25, 19.65, 0.58, 0.61, T)], "master", src="plan 3: folded throw at the bed foot, right end X 0.19")
    kill_group(R, "master/cushions")
    reg(R, "master/cushions", [bx("m_cus_r3", -0.95, -0.45, 18.20, 18.32, 0.58, 0.88, T, 0.03)], "master", src="plan 3: boucle lumbar 30 x 50")
    notes.append("master: art 2 x 50 x 50, sconces 24 x 20 (lit), pot cover 35 x 37, vase on the top, holders 7 x 11, lumbar 30 x 50; sill vase 8.5 x 24.7, dish 9.5 x 3 generic")
    # ---- kids: card sizes (plan 3) --------------------------------------------------------------------------------
    for kid, dy in (("boy", 0.0), ("girl", GIRL_DY)):
        y0 = 10.25 + dy
        kill_group(R, f"{kid}/bookshelf")
        oak = fr.mat_cache("oak_lining", "#CBBBA5")
        books = []
        for i, z in enumerate((1.25, 1.58)):
            for j, (xa, xb) in enumerate(((-1.25, -0.831), (-0.869, -0.45))):
                books.append(bx(f"{kid}_ledge_r3{i}{j}", xa, xb, y0, y0 + 0.10, z - 0.022, z, oak))
                books.append(bx(f"{kid}_lip_r3{i}{j}", xa, xb, y0 + 0.088, y0 + 0.10, z, z + 0.035, oak))
            for j, (xa, w, h) in enumerate(((-1.20, 0.19, 0.25), (-0.99, 0.21, 0.28), (-0.76, 0.18, 0.22), (-0.66, 0.17, 0.24))):
                if i == 1 and j == 3:
                    continue
                books.append(obox(f"{kid}_book_r3{i}{j}", (xa + w / 2, y0 + 0.07, z + 0.002), (xa + w / 2, y0 + 0.012 + 0.003 * j, z + h), (1, 0, 0), w, 0.012, A))
        reg(R, f"{kid}/bookshelf", books, kid, src="plan 3: two 41.9 ledges per tier at Z 1.25 / 1.58, books face-out (filler)")
        kill_group(R, f"{kid}/bedspread")
        reg(R, f"{kid}/bedspread", [bx(f"{kid}_spread_r3", -0.88, -0.36, y0 + 0.03, y0 + 0.96 - 0.02, 0.50, 0.545, T, 0.012),
                                    bx(f"{kid}_spreadhang_r3", -0.88, -0.36, y0 + 0.96 - 0.035, y0 + 0.96 + 0.04, 0.33, 0.545, T, 0.01)], kid,
            src="plan 3: muslin blanket folded on the foot third; starts at X -0.88 (was -0.93) for the 0.02 gap to the cushions")
        kill_group(R, f"{kid}/cushions")
        reg(R, f"{kid}/cushions", [bx(f"{kid}_cu_r3a", -2.17, -1.77, y0 + 0.03, y0 + 0.16, 0.50, 0.90, T, 0.04),
                                   bx(f"{kid}_cu_r3b", -1.80, -1.40, y0 + 0.035, y0 + 0.165, 0.50, 0.90, T, 0.04)], kid,
            src="plan 3: two 40 cushions at the bed head (the 30 x 30 third does not exist in the listing)")
        kill_group(R, f"{kid}/soft-toy")
        reg(R, f"{kid}/soft-toy", [cyl(f"{kid}_toyb_r3", (-2.02, y0 + 0.76), 0.08, 0.50, 0.68, T), ell(f"{kid}_toyh_r3", (-2.02, y0 + 0.76), 0.07, 0.67, 0.80, T)], kid,
            src="plan 3: crochet toy 30 at (-2.02, 11.01), sitting on the duvet, so it crosses the sill line decisively (sliver 0.008 at 28)")
        kill_group(R, f"{kid}/toy-basket")
        tb = [cyl(f"{kid}_tbask_r3", (-0.62, 11.58 + dy), 0.175, 0.013, 0.40, O)]
        if kid == "boy":
            tb.append(ell("boy_football_r3", (-0.58, 11.60 + dy), 0.11, 0.29, 0.51, O))
        else:
            for i, (ox, oy, r) in enumerate(((-0.67, 11.55, 0.07), (-0.55, 11.63, 0.065), (-0.62, 11.68, 0.06))):
                tb.append(ell(f"girl_knit_r3{i}", (ox, oy + dy), r, 0.37, 0.37 + 2 * r, O))
        reg(R, f"{kid}/toy-basket", tb, kid, src="plan 3: jute cylinder 35 x 39 at (-0.62, 11.58), filler football / knitted balls")
        if kid == "boy":
            kill_group(R, "boy/toy-cars")
            reg(R, "boy/toy-cars", [bx("boy_car_r3_0", 0.18, 0.27, y0 + 0.14, y0 + 0.19, 0.70, 0.75, A, 0.01), bx("boy_car_r3_1", 0.29, 0.38, y0 + 0.20, y0 + 0.25, 0.70, 0.75, A, 0.01),
                                    bx("boy_car_r3_2", 0.31, 0.40, y0 + 0.08, y0 + 0.13, 0.70, 0.75, A, 0.01)], "boy", src="plan 3: three beech cars ~9 x 5 at the desk's left end")
    notes.append("kids: ledges 2 x 41.9 per tier, two 40 cushions (third removed), toy 28, basket 35 x 39 at (-0.62, 11.58), cars 9 x 5")
    # ---- bath: card sizes (plan 3, B1 / B2) ------------------------------------------------------------------------
    kill_group(R, "bath/wall-sconce")
    b1s = bx("b1_sconce_r3", 4.635, 4.765, 9.95, 10.06, 1.62, 1.78, M["curtain"], 0.01)
    reg(R, "bath/wall-sconce", [b1s], "bath", src="plan 3: fluted resin up-down 13 x 16 at (4.70, 9.95, 1.70)")
    L = r2.LAMPS.get("bath/wall-sconce")
    if L:
        L["glow"] = [(b1s, r2.GLOW_LED)]
        L["orig"] = {b1s.name: b1s.data.materials[0]}
    kill_group(R, "bath/vanity-sconces")
    vs = [bx(f"vsconce_r3{i}", 6.14, 6.25, yy - 0.065, yy + 0.065, 1.57, 1.73, M["curtain"], 0.01) for i, yy in enumerate((11.62, 12.98))]
    reg(R, "bath/vanity-sconces", vs, "bath", src="plan 3: fluted resin pair 13 x 16 at (6.25, 11.62 / 12.98, 1.65)")
    L = r2.LAMPS.get("bath/vanity-sconces")
    if L:
        L["glow"] = [(o, r2.GLOW_LED) for o in vs]
        L["orig"] = {o.name: o.data.materials[0] for o in vs}
    kill_group(R, "bath/bath-mat")
    reg(R, "bath/bath-mat", [bx("bmat_r3", 4.75, 5.15, 10.40, 11.00, 0.0, 0.012, M["rug"])], "bath", src="plan 3: tufted mat 40 x 60 at X 4.75-5.15")
    kill_group(R, "bath/toilet-paper-stand")
    reg(R, "bath/toilet-paper-stand", [cyl("tps_base_r3", (4.50, 10.08), 0.09, 0.0, 0.015, Hd), cyl("tps_pole_r3", (4.50, 10.08), 0.012, 0.015, 0.65, Hd),
                                       obox("tps_roll_r3", (4.50, 10.08, 0.55), (4.50, 10.21, 0.55), (0, 0, 1), 0.11, 0.11, O),
                                       cyl("tps_spare_r3", (4.50, 10.08), 0.055, 0.015, 0.125, O)], "bath", src="plan 3: floor stand ~65 at (4.50, 10.08)")
    kill_group(R, "bath/candle")
    reg(R, "bath/candle", [cyl("candle_r3", (3.99, 10.09), 0.045, 0.95, 1.048, O)], "bath", src="plan 3: ribbed candle cup 9 x 9.8")
    kill_group(R, "bath/shower-dispensers")
    reg(R, "bath/shower-dispensers", [cyl(f"shd_r3{i}", (6.29, yy), 0.0375, 1.05, 1.215, O) for i, yy in enumerate((10.47, 10.59, 10.71))], "bath",
        src="plan 3: three pump bottles 7.5 x 16.5 in the niche")
    kill_group(R, "bath/soap-dispenser")
    reg(R, "bath/soap-dispenser", [cyl("soapd_r3", (6.07, 12.58), 0.0375, 0.88, 1.045, O)], "bath", src="plan 3: pump bottle 7.5 x 16.5 at (6.07, 12.58)")
    kill_group(R, "bath/toothbrush-cup")
    reg(R, "bath/toothbrush-cup", [cyl("tcup_r3", (6.12, 12.68), 0.04, 0.88, 0.99, O), cone("tbrushes_r3", (6.12, 12.68), 0.012, 0.03, 0.99, 1.07, O, 12)], "bath",
        src="plan 3: travertine cup 8 x 11, brushes to 1.07")
    kill_group(R, "bath/vanity-vase")
    reg(R, "bath/vanity-vase", [cyl("vvase_r3", (6.07, 12.78), 0.038, 0.88, 1.008, O), cone("vsprig_r3", (6.07, 12.78), 0.005, 0.04, 1.008, 1.10, M["crown"], 12)], "bath",
        src="plan 3: bud vase 7.6 x 12.8, sprig to 1.10 (mirror bottom 1.165)")
    kill_group(R, "bath/storage-basket")
    reg(R, "bath/storage-basket", [bx("sbask_r3", 5.86, 6.19, 11.985, 12.415, 0.15, 0.34, T, 0.02)], "bath", src="plan 3: rope basket 43 x 33 x 19 on the open shelf")
    kill_group(R, "bath/hand-towel")
    reg(R, "bath/hand-towel", [bx("htowel_r3", 6.17, 6.225, 12.86, 13.10, 0.66, 0.93, T, 0.01)], "bath",
        src="plan 3: linen hand towel 38 x 55 folded over the ring (24 wide, 27 drop each side)")
    L = r2.LAMPS.get("bath/shower-downlight")
    if L:
        for li in L["lights"]:
            li.data.energy = 4.0
    notes.append("bath: B1 lamp and vanity pair 13 x 16 (lit), mat 40 x 60, stand 65, candle 9 x 9.8, bottles 7.5 x 16.5, cup 8 x 11, bud vase 7.6 x 12.8, "
                 "basket 43 x 33 x 19, hand towel 38 x 55; shower downlight at low power (4 W) for the lit set")
    # ---- work: card sizes (plan 3, W0) ------------------------------------------------------------------------------
    kill_group(R, "work/rug")
    reg(R, "work/rug", [bx("w_rug_r3", -1.675, 0.025, 6.95, 9.05, 0.0, 0.012, M["rug"])], "work", src="plan 3: NYOKO 170 wide under the chair (runs past the bottom edge)")
    kill_group(R, "work/basket")
    reg(R, "work/basket", [cyl("w_basket_r3", (-1.35, 6.60), 0.15, 0.0, 0.30, O)], "work", src="plan 3: rope cylinder 30; (-1.25, 6.62) -> (-1.35, 6.60), the 0.10 nudge allowed, to clear the chair silhouette")
    kill_group(R, "work/waste-basket")
    reg(R, "work/waste-basket", [cyl("w_waste_r3", (-0.30, 6.70), 0.125, 0.0, 0.30, O)], "work", src="plan 3: kraft bin 25 x 30; (-0.35, 6.70) -> (-0.30, 6.70) for the 0.02 gap to the chair")
    kill_group(R, "work/shelf-boxes")
    reg(R, "work/shelf-boxes", [bx("w_box_r3a", -1.50, -1.20, 6.375, 6.62, 1.66, 1.81, T, 0.01), bx("w_box_r3b", -0.45, -0.15, 6.375, 6.62, 1.66, 1.81, T, 0.01)], "work",
        src="plan 3: felt bins 30 x 24.5 x 15 on the shelf")
    kill_group(R, "work/bookends")
    reg(R, "work/bookends", [bx("w_bkend_r3a", -1.03, -1.00, 6.40, 6.53, 1.66, 1.79, Hd), bx("w_bkend_r3b", -0.72, -0.69, 6.40, 6.53, 1.66, 1.79, Hd),
                             bx("w_books_r3", -0.995, -0.725, 6.39, 6.56, 1.66, 1.88, A)], "work", src="plan 3: beech bookends 10.5 x 13 with books (filler)")
    notes.append("work: rug 170 wide, basket 30, bin 25 x 30, felt bins 30 x 24.5 x 15, bookends 10.5 x 13; pen cup 8 x 11 generic on the desk")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# living vista (H0, C0): the M0 clay + listed products
# ---------------------------------------------------------------------------------------------------------------
def living_vista(R):
    """Hide every M0 slot proxy (the living seen through the openings = m0-clay-4k) and build the three products the verdict
    names, registered as living/pendant, living/wall-decor, living/accent-sconces; they are shown only when also_visible lists them."""
    notes = []
    for k in list(R):
        if k.startswith("living/"):
            set_hidden(R[k]["objs"], True)
            R[k]["kind"] = "m0-proxy-hidden"
    reg(R, "living/pendant", [ell("lv_pend_r3", (0.20, 1.72), 0.20, 2.20, 2.48, M["curtain"]),
                              cyl("lv_pcord_r3", (0.20, 1.72), 0.004, 2.48, 3.0, M["holder"], 12)], "living",
        src="verdict 3.3: 40 cm pumpkin pendant, bottom 2.20, hang point (0.20, 1.72)")
    reg(R, "living/wall-decor", [bx("lv_sun_r3", -1.35, -1.05, 0.0, 0.03, 1.05, 1.35, M["art"])], "living",
        src="living-room.json: centre (-1.20, 0.02, 1.20), 30 cm raffia sun")
    reg(R, "living/accent-sconces", [bx("lv_trav_a_r3", -0.89, -0.81, 0.0, 0.09, 1.67, 1.83, M["obj"], 0.004),
                                     bx("lv_trav_b_r3", 1.21, 1.29, 0.0, 0.09, 1.67, 1.83, M["obj"], 0.004)], "living",
        src="living-room.json: plates (-0.85, 0, 1.75) and (1.25, 0, 1.75), 8 x 16, projection 9")
    # m0-v6.txt: the triptych 3 x 50x70 (centre X 0.20, Z 1.475 as the v4 spec art), the 31 cm jar on the sill, the 21 cm bowl
    reg(R, "living/framed-art", [bx(f"lv_art_r3_{i}", xc - 0.25, xc + 0.25, 0.0, 0.03, 1.13, 1.83, M["art"]) for i, xc in enumerate((-0.36, 0.20, 0.76))],
        "living", src="plan 3 (M0): triptych 3 x 50x70, 6 cm gaps, centre Z 1.48, centred on the v4 spec art centre X 0.20")
    reg(R, "living/rug", [bx("lv_rug_r3", -1.45, 1.85, 0.77, 3.07, 0.0, 0.012, M["rug"])], "living",
        src="plan 3 (M0): braided wool rug 230 x 330 (Square, no fringe), centred on the spec rug centre (0.20, 1.92), long side along X")
    reg(R, "living/wall-sconce", [bx("lv_sconce_r3", -2.30, -2.28, 3.11, 3.23, 1.41, 1.53, M["holder"]),
                                  bx("lv_socket_r3", -2.30, -2.29, 3.13, 3.21, 1.25, 1.33, M["holder"]),
                                  obox("lv_scable_r3", (-2.29, 3.17, 1.41), (-2.29, 3.17, 1.33), (0, 1, 0), 0.006, 0.006, M["holder"])], "living",
        src="plan 3 (M0): swing-arm wall lamp plate (-2.30, 3.17, 1.47) + the design socket under it (v4 spec socket (-2.30, 3.17, 1.29))")
    reg(R, "living/vase", [cyl("lv_vase_r3", (-2.42, 1.35), 0.08, 0.75, 1.06, M["obj"]),
                           cone("lv_stems_r3", (-2.42, 1.35), 0.02, 0.09, 1.06, 1.35, M["crown"], 12)], "living",
        src="living-room.json: sill, back casement, base (-2.42, 1.35, 0.75), body 31, stems to 1.35")
    T = bs.TABLE["h"]
    reg(R, "living/bowl", [cyl("lv_bowl_r3", (0.68, 1.92), 0.105, T, T + 0.065, M["obj"])], "living",
        src="living-room.json: coffee table, centre (0.68, 1.92), d 21, h 6.5")
    # M0 lamps (plan 3, M0: pendant, floor lamp, wall sconce, travertine pair lit): the M0 clay has no light sources, so build them
    pend = R["living/pendant"]["objs"][0]
    r2.lamp("living/pendant", "living", "ceiling", [(pend, r2.GLOW)], [r2.mk_light("lv_pend_L", "AREA", (0.20, 1.72, 2.195), 30.0, size=0.30)], "pumpkin pendant 40 (m0-v6)")
    fl = [o for o in R.get("living/floor-lamp", {}).get("objs", []) if alive(o) and o.name == "px_lamp_shade"]
    r2.lamp("living/floor-lamp", "living", "floor", [(o, r2.GLOW) for o in fl],
            [r2.mk_light("lv_flamp_L", "AREA", (1.60, 0.20, 1.195), 24.0, size=0.26), r2.mk_light("lv_flamp_L2", "AREA", (1.60, 0.20, 1.505), 10.0, size=0.2, aim=(0, 0, 1))],
            "floor lamp (m0-v6)")
    r2.lamp("living/wall-sconce", "living", "wall", [(R["living/wall-sconce"]["objs"][0], r2.GLOW)],
            [r2.mk_light("lv_sconce_L", "POINT", (-2.12, 3.17, 1.50), 10.0, size=0.05)], "swing-arm wall lamp (m0-v6)")
    r2.lamp("living/accent-sconces", "living", "wall", [(o, r2.GLOW * 0.6) for o in R["living/accent-sconces"]["objs"]],
            [r2.mk_light(f"lv_trav_L{i}", "POINT", (x, 0.06, 1.75), 5.0, size=0.04) for i, x in enumerate((-0.85, 1.25))], "travertine pair (m0-v6)")
    for k in ("living/pendant", "living/wall-decor", "living/accent-sconces", "living/framed-art", "living/vase", "living/bowl", "living/rug", "living/wall-sconce"):
        set_hidden(R[k]["objs"], True)
    notes.append("living slot proxies hidden by default (= M0 clay); the m0-v6 products (pendant 40, sun 30, travertine pair, triptych, sill jar, "
                 "bowl + the v4 proxies of curtains, wall-sconce, floor-lamp, basket, rug, cushions, runner, candles) shown only where plan.json lists them")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# light balance: living vs hall
# ---------------------------------------------------------------------------------------------------------------
def light_balance(a):
    notes = []
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name == "winlight_W-living":
            ob.data.energy *= a.living_boost
            notes.append(f"living window area light x{a.living_boost} (= {ob.data.energy:.0f} W)")
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name == "winlight_W-bath" and a.bath_window != 1.0:
            ob.data.energy *= a.bath_window
            notes.append(f"bath area light outside the fluted window x{a.bath_window} (= {ob.data.energy:.0f} W): plan 3 B1, the wall beside it toward L 86-90, not global exposure")
    if a.hall_roof != 1.0:
        for ob in bpy.data.objects:
            if ob.type != "MESH" or not ob.name.startswith("opal"):
                continue
            c = ob.matrix_world @ (sum((Vector(v) for v in ob.bound_box), Vector()) / 8)
            if 0.80 <= c.x <= 3.60 and 6.35 <= c.y <= 9.80:            # the hall roof light (G-H1)
                m = ob.data.materials[0].copy()
                m.name = "opal_hall_r3"
                for nd in m.node_tree.nodes:
                    if nd.type == "EMISSION":
                        nd.inputs["Strength"].default_value *= a.hall_roof
                ob.data.materials.clear()
                ob.data.materials.append(m)
                notes.append(f"hall roof-light emission x{a.hall_roof} ({ob.name}, own material copy)")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# per-frame visibility and lamps
# ---------------------------------------------------------------------------------------------------------------
def shell_lamps(room):
    return [k for k, L in r2.LAMPS.items() if L["room"] == room and L["shell"]]


def apply_frame(fid, fplan, S, R, slots):
    room = FRAMES[fid][0]
    dy = GIRL_DY if room == "girl" else 0.0
    want = set(f"{room}/{s}" for s in fplan["placeholders"]) | set(fplan["also_visible"])
    built = []
    sfile = slots[FRAMES[fid][2]]
    sdefs = {s["id"]: s for s in sfile["slots"]}
    for key in sorted(want):
        if key in R and R[key]["objs"]:
            continue
        rm, sl = key.split("/", 1)
        if rm != room or sl not in sdefs:
            continue
        if sdefs[sl].get("kind") == "fixed-product":
            continue
        objs = generic_proxy(R, room, sl, sdefs[sl], dy)
        if objs:
            built.append(key)
    if "work/desk-organizer" in built and "work/desk-tray" not in want:
        move(R, "work/desk-organizer", dz=-0.03)                 # w0.txt: on the desk top (0.76), the tray is empty
    for key, v in R.items():
        set_hidden(v["objs"], key not in want)
    missing = sorted(k for k in want if k not in R or not R[k]["objs"])
    # lamps: listed lamps, else the room's S12 lamps whose proxy is shown + shell lamps
    if fplan["lamps"] is not None:
        lit = list(fplan["lamps"])
    else:
        lit = [k for k in r2.ROOM_LAMPS.get(room, []) if k in want] + shell_lamps(room)
        lit += [k for k in fplan["also_visible"] if k in r2.LAMPS]
    lit = [k for k in lit if k in r2.LAMPS and (r2.LAMPS[k]["shell"] or k in want)]
    lit_now = r2.lamps_set(lit)
    return dict(placeholders_shown=sorted(k for k in want if k in R and R[k]["objs"]), built_generic=built, missing=missing,
                lamps_on=lit_now, lamps_off=sorted(k for k in r2.LAMPS if k.split("/")[0] == room and k not in lit_now))


# ---------------------------------------------------------------------------------------------------------------
# measurements
# ---------------------------------------------------------------------------------------------------------------
def patch_L(path, u, v, w=0.012):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    W, H = im.size
    a = np.asarray(im).astype(float) / 255.0
    x0, x1 = int((u - w) * W), int((u + w) * W)
    y0, y1 = int((v - w * 16 / 9) * H), int((v + w * 16 / 9) * H)
    p = a[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3)
    lin = np.where(p <= 0.04045, p / 12.92, ((p + 0.055) / 1.055) ** 2.4)
    Y = float((lin @ np.array([0.2126, 0.7152, 0.0722])).mean())
    L = float(((p.max(1) + p.min(1)) / 2 * 100).mean())
    return dict(u=u, v=v, L_hsl=round(L, 1), Y_lin=round(Y, 4), stops_vs_mid=round(math.log2(max(Y, 1e-6) / 0.18), 2))


def hall_balance(fid, path, cam, C, cfg):
    """H0 / C0: the living back wall seen through the door vs the hall walls. The verdict's QA point (0.35, 0.40) + measured points."""
    pts = {}
    xd = (cfg["door"]["x0"] + cfg["door"]["x1"]) / 2
    cx, cy = C["loc"][0], C["loc"][1]
    t = (cy - 0.0) / max(cy - 6.35, 1e-6)
    x_hit = cx + (xd - cx) * t                                     # where the ray through the door centre meets the living back wall
    if fid == "H0":
        pts["living_vista_verdict_0.35_0.40"] = (0.35, 0.40)
        pts["living_back_wall_through_door"] = (fr.U(cam, x_hit, 0.0, 1.6), fr.V(cam, x_hit, 0.0, 1.6))
        pts["hall_front_wall_above_console"] = (fr.U(cam, 2.95, 6.35, 2.10), fr.V(cam, 2.95, 6.35, 2.10))
        pts["hall_front_wall_right_of_console"] = (fr.U(cam, 3.50, 6.35, 1.40), fr.V(cam, 3.50, 6.35, 1.40))
        pts["hall_left_wall_above_bench"] = (fr.U(cam, 0.80, 7.40, 1.30), fr.V(cam, 0.80, 7.40, 1.30))
        pts["hall_floor_threshold"] = (fr.U(cam, 1.55, 6.60, 0.0), fr.V(cam, 1.55, 6.60, 0.0))
    elif fid == "C0":
        pts["living_slice_end"] = (fr.U(cam, x_hit, 0.0, 1.5), fr.V(cam, x_hit, 0.0, 1.5))
        pts["hall_end_wall"] = (fr.U(cam, 2.60, 6.35, 1.5), fr.V(cam, 2.60, 6.35, 1.5))
        pts["corridor_left_wall_gallery"] = (fr.U(cam, 1.70, 15.0, 1.0), fr.V(cam, 1.70, 15.0, 1.0))
        pts["corridor_right_wall"] = (fr.U(cam, 3.10, 15.0, 1.3), fr.V(cam, 3.10, 15.0, 1.3))
    out = {"living_back_wall_x_hit": round(x_hit, 3)} if pts else {}
    for k, (u, v) in pts.items():
        if 0.02 < u < 0.98 and 0.02 < v < 0.98:
            out[k] = patch_L(path, u, v)
        else:
            out[k] = dict(u=round(u, 3), v=round(v, 3), note="outside the frame")
    if fid == "H0" and "Y_lin" in out.get("living_back_wall_through_door", {}) and "Y_lin" in out.get("hall_front_wall_above_console", {}):
        a = out["living_back_wall_through_door"]["Y_lin"]
        b = out["hall_front_wall_above_console"]["Y_lin"]
        out["living_minus_hall_stops"] = round(math.log2(max(a, 1e-6) / max(b, 1e-6)), 2)
        out["rule"] = ("hall ~2/3 stop under the living seen through the portal (verdict 3.4 / Bible B5); the verdict's QA point (0.35,0.40) "
                       ">= 8 L over the facing wall")
        out["pass_2_3_stop"] = bool(0.5 <= out["living_minus_hall_stops"] <= 0.9)
        q = out.get("living_vista_verdict_0.35_0.40", {}).get("L_hsl")
        if q is not None:
            out["qa_point_minus_front_wall_L"] = round(q - out["hall_front_wall_above_console"]["L_hsl"], 1)
    return out


def lamp_report(fid, idx, lit):
    H, W = idx.shape
    rows = []
    for k in lit:
        L = r2.LAMPS[k]
        px = 0
        for o, _ in L["glow"]:
            if alive(o) and o.pass_index:
                px += int((idx == o.pass_index).sum())
        rows.append(dict(lamp=k, typology=L["typ"], shell=L["shell"], glow_px=px, visible=bool(px >= 2.5e-5 * H * W)))
    return rows


def item_boxes(S, idx, items):
    """Pixel bboxes [u0, u1, v0, v1] of every visible group (placeholders, fixed furniture, windows, doors): the Step-2 clay-lock
    regions and the per-product +-15% box check read these."""
    out = {}
    names = r2.names_by_pidx(S)
    for k, v in S["lslots"].items():
        names.setdefault(v["pidx"], ("living/" + k, "proxy"))
    for pidx, (nm, kind) in names.items():
        b = fr.group_bbox(idx, [pidx])
        if b is None or b[4] < 40:
            continue
        out[nm] = dict(kind=kind, box=[bh.r4(b[0]), bh.r4(b[1]), bh.r4(b[2]), bh.r4(b[3])], px=b[4])
    return out


HERO_WALL_PT = {"D1": (4.60, 0.0), "D2": (7.25, 2.60), "H0": (2.95, 6.35), "C0": (1.70, 15.0), "MB0": (-0.70, 17.66),
                "K-boy": (-1.50, 10.25), "K-girl": (-1.50, 13.88), "B1": (5.72, 9.95), "B2": (6.25, 12.30), "W0": (-0.825, 6.35),
                "M0": (0.20, 0.0)}


def wall_patches(fid, cam, C, path):
    """uv points on bare wall / ceiling / floor for the grade (white balance + exposure patch) and the Bible L readings."""
    hx, hy = HERO_WALL_PT[fid]
    pts = {"hero_wall_high": (hx, hy, 2.35), "hero_wall_mid": (hx, hy, 1.95)}
    if fid == "D1":
        pts["hero_wall_mid"] = (4.60, 0.0, 2.40)             # above the window head; the window fills the wall below
        pts["kitchen_wall"] = (7.25, 1.00, 2.40)
    if fid == "D2":
        pts["hero_wall_mid"] = (7.25, 1.00, 2.40)
        pts["tall_units"] = (6.63, 5.00, 2.00)
    if fid == "H0":
        pts["left_wall"] = (0.80, 6.70, 2.30)
        pts["living_vista"] = (0.35, 0.40, None)
    if fid == "C0":
        pts["right_wall"] = (3.10, 14.0, 1.6)
    if fid in ("K-boy", "K-girl"):
        dy = GIRL_DY if fid == "K-girl" else 0.0
        pts["paint_block"] = (-0.60, 10.25 + dy, 0.95)
        pts["north_wall"] = (-2.30, 12.60 + dy, 2.2)
    if fid == "MB0":
        pts["wainscot"] = (-0.70, 17.66, 0.95)
    if fid == "B1":
        pts["limestone_shower"] = (6.25, 10.1, 1.9)
        pts["wall_beside_window"] = (4.55, 9.95, 2.0)
    if fid == "B2":
        pts["hero_wall_mid"] = (6.25, 12.30, 2.30)          # above the mirror
    if fid == "W0":
        pts["hero_wall_mid"] = (-0.825, 6.35, 2.10)         # above the shelf
    if fid == "M0":
        pts["hero_wall_mid"] = (0.20, 0.0, 2.10)            # back wall above the triptych
        pts["bible_corner_0.467_0.385"] = (0.467, 0.385, None)
        pts["bible_behind_sofa_0.69_0.22"] = (0.69, 0.22, None)
        pts["bible_right_edge_0.97_0.31"] = (0.97, 0.31, None)
        pts["window_wall_0.10_0.30"] = (0.10, 0.30, None)
    out = {}
    for k, (x, y, z) in pts.items():
        if z is None:
            u, v = x, y
        else:
            u, v = fr.U(cam, x, y, z), fr.V(cam, x, y, z)
        if 0.02 < u < 0.98 and 0.02 < v < 0.98:
            out[k] = dict(patch_L(path, u, v), xyz=[x, y, z])
        else:
            out[k] = dict(u=round(u, 3), v=round(v, 3), xyz=[x, y, z], note="outside the frame")
    out["ceiling"] = patch_L(path, 0.55, 0.04)
    out["floor_centre"] = patch_L(path, 0.50, 0.93)
    return out


def tangents(fid, S, C, idx, items, flags):
    names = r2.names_by_pidx(S)
    tang = []
    for pidx, (nm, kind) in names.items():
        b = fr.group_bbox(idx, [pidx])
        if b is None or b[4] < 200 or kind == "architecture":
            continue
        for side, m in (("left", b[0]), ("right", 1 - b[1]), ("top", b[2]), ("bottom", 1 - b[3])):
            if 0.0 < m < 0.02:
                tang.append(dict(item=nm, side=side, margin=bh.r4(m)))
    return dict(edge_tangents=tang, object_object_tangents=flags,
                note="edge: visible bbox margin 0 < m < 0.02; object-object as round 2 (ray-cast silhouettes, 512x288)")


# ---------------------------------------------------------------------------------------------------------------
# one frame
# ---------------------------------------------------------------------------------------------------------------
def run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, rep, cfg):
    t0 = time.time()
    room, r2id, _ = FRAMES[fid]
    C = cams[fid]
    cam = S["cam"]
    bh.set_view(cam, C["loc"], C["yaw"], C["u0"], C["v0"])
    vis = apply_frame(fid, fplan, S, R, slots)
    bpy.context.view_layer.update()
    p = os.path.join(OUT, f"{fid}.png")
    depth, idx, normal = fr.render(p, os.path.join(tmp, "p"), a.res, a.samples, ao=0.30)
    Rr = dict(frame=fid, room=room, round2_id=r2id, camera=C, image=f"framing/round3/{fid}.png",
              resolution=[a.res, int(round(a.res * 9 / 16))], samples=a.samples, **vis, mean_L=fr.mean_L(p),
              mean_L_round2=None, designer_notes=fplan.get("notes", ""))
    try:
        s2 = json.load(open(os.path.join(R2DIR, "selfcheck.json")))
        Rr["mean_L_round2"] = (s2.get("frames", {}).get(r2id) or s2.get("picks_lit", {}).get(r2id) or {}).get("mean_L_lit")
    except Exception:
        pass
    # est vs measured (architecture + the designer's est values of the proposal), as round 2 / round 1
    try:
        est = r2.est_rows(r2id, S, cam, C, idx) if r2id in r2.FRAMES else fr.est_rows(r2id, S, cam, C, idx)
    except Exception as e:  # noqa: BLE001
        est = []
        Rr["est_error"] = repr(e)
    Rr["est_vs_measured"] = est
    Rr["est_flags"] = [r["key"] for r in est if r.get("flag_gt_tol")]
    # visible items + tangents
    try:
        items, flags = r2.analyse(C, S, idx, room)
        Rr["items_visible"] = {v["name"]: dict(kind=v["kind"], frame_area_pct=round(100 * v["area"], 2), visible_pct=v["visible_pct"],
                                               cut_by_edge_pct=v["cut_pct"]) for v in items.values()}
        Rr["F3_tangents"] = tangents(fid, S, C, idx, items, flags)
        Rr["boxes"] = item_boxes(S, idx, items)
        if r2id in r2.FRAMES:
            Rr["rules_designer"] = r2.designer_rules(r2id, S, cam, C, idx, items)
        if r2id in r2.DENSITY_MIN:
            Rr["density_F10"] = r2.density(items, room, r2id)
    except Exception as e:  # noqa: BLE001
        Rr["analyse_error"] = repr(e)
    # heroes (thirds) from the round-2 / round-1 tables
    heroes = []
    try:
        if r2id in r2.HERO2:
            for lab, pt, mode in r2.HERO2[r2id]:
                if pt == "kitchen hood":
                    continue
                u = fr.U(cam, *pt) if pt[2] is not None else fr.U(cam, pt[0], pt[1])
                heroes.append(dict(hero=lab, u=bh.r4(u), ok=bool(0.30 <= u <= 0.36 or 0.64 <= u <= 0.70)))
        elif r2id in fr.HERO:
            for lab, pt, mode in fr.HERO[r2id]:
                if isinstance(pt, (list, tuple)) and len(pt) == 3:
                    u = fr.U(cam, *pt) if pt[2] is not None else fr.U(cam, pt[0], pt[1])
                    heroes.append(dict(hero=lab, u=bh.r4(u), ok=bool(0.30 <= u <= 0.36 or 0.64 <= u <= 0.70)))
    except Exception as e:  # noqa: BLE001
        Rr["hero_error"] = repr(e)
    Rr["heroes_thirds"] = heroes
    Rr["lamps"] = lamp_report(fid, idx, vis["lamps_on"])
    if room == "bath":
        try:
            Rr["F8_mirror"] = r2.mirror_pass(C, cam)
        except Exception as e:  # noqa: BLE001
            Rr["F8_mirror"] = dict(error=repr(e))
    Rr["wall_patches"] = wall_patches(fid, cam, C, p)
    Rr["light_balance"] = hall_balance(fid, p, cam, C, cfg)
    obs = bh.obstacles()
    cl = min((bh.rect_dist(C["loc"][:2], r[:4]), r[4]) for r in obs)
    Rr["camera_clearance_m"] = dict(min=bh.r4(cl[0]), nearest=cl[1])
    os.makedirs(os.path.join(OUT, "overlays"), exist_ok=True)
    rows = [r for r in est if r.get("est") is not None]
    try:
        fr.make_overlay(p, os.path.join(OUT, "overlays", f"{fid}.png"),
                        f"{fid} ({room}) round 3  cam {C['loc']} yaw {C['yaw']} u0 {C['u0']} v0 {C['v0']}  {a.res}px", rows, heroes)
        Rr["overlay"] = f"framing/round3/overlays/{fid}.png"
    except Exception as e:  # noqa: BLE001
        Rr["overlay_error"] = repr(e)
    r2.lamps_set([])
    Rr["runtime_s"] = round(time.time() - t0)
    rep.setdefault("frames", {})[fid] = Rr
    return Rr


# ---------------------------------------------------------------------------------------------------------------
# comparison sheet
# ---------------------------------------------------------------------------------------------------------------
def sheet(rep, frames):
    from PIL import Image, ImageDraw
    w = 900
    th = int(w * 9 / 16)
    pairs = []
    for fid in frames:
        Rr = rep.get("frames", {}).get(fid, {})
        sub3 = (f"L {Rr.get('mean_L')}  placeholders {len(Rr.get('placeholders_shown', []))}  lamps {len(Rr.get('lamps_on', []))}"
                if Rr else "not rendered")
        pairs.append(((os.path.normpath(os.path.join(R2DIR, R2_IMAGE[fid] + ".png")), f"ROUND 2  {os.path.basename(R2_IMAGE[fid])}", f"L {Rr.get('mean_L_round2')}"),
                      (os.path.join(OUT, f"{fid}.png"), f"ROUND 3  {fid}  ({FRAMES[fid][0]})", sub3)))
    cols = 2
    rows = math.ceil(len(pairs) / cols)
    pad, head = 12, 70
    W = cols * (2 * w + 2 * pad) + pad
    im = Image.new("RGB", (W, head + rows * (th + pad) + pad), (246, 245, 242))
    d = ImageDraw.Draw(im)
    d.text((pad, 16), "Framing round 3 (Phase B clays, 2026-10-25): round 2 | round 3 per frame. 3840x2160, neutral albedo, 1.1.x cameras, "
                      "placeholders only for the designer's list, S12 lamps on. Clay, 0 credits.", fill=(15, 15, 15), font=ba.font(28))
    for k, (l, r) in enumerate(pairs):
        x = pad + (k % cols) * (2 * w + 2 * pad)
        y = head + (k // cols) * (th + pad)
        im.paste(fr.tile(l[0], w, l[1], l[2]), (x, y))
        im.paste(fr.tile(r[0], w, r[1], r[2]), (x + w + pad // 2, y))
    outp = os.path.join(OUT, "round2-vs-round3.jpg")
    im.save(outp, quality=88)
    return outp


# ---------------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------------
def set_out(path):
    global OUT
    OUT = path


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(OUT, "plan.json"))
    ap.add_argument("--frames", default="all")
    ap.add_argument("--res", type=int, default=3840)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0, help="multiplier on the living window area light (hall/living balance)")
    ap.add_argument("--hall-roof", type=float, default=2.0, help="multiplier on the hall roof-light emission (2.0: smoke tests gave living-hall 1.11 stops at 1.0, 0.90 at 1.5; target ~0.67)")
    ap.add_argument("--bath-window", type=float, default=3.0, help="multiplier on the area light outside the fluted bath window (plan 3, B1)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-sheet", action="store_true")
    a, _ = ap.parse_known_args(argv)
    if a.out:
        set_out(a.out)
    os.makedirs(OUT, exist_ok=True)
    frames = ORDER if a.frames == "all" else [f for f in ORDER if f in a.frames.split(",")]
    rplan = load_render_plan(a.plan)
    cams, plan_doc = cameras_1_1()
    slots = load_slots()
    sc_path = os.path.join(OUT, "selfcheck.json")
    rep = json.load(open(sc_path)) if os.path.exists(sc_path) else {}

    def save():
        json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)

    t0 = time.time()
    r2.WARM = WARM_R3                                   # lamp colour for glow materials and light sources built by build_r2
    prop = fr.load_prop()
    plan_path, plan0 = bh.load_plan()
    spec = json.load(open(b4.SPEC_PATH))
    cfg = b4.v4_config(spec)
    S, plan, notes, wl = r2.build_r2(plan0, cfg, a)
    R = registry(S)
    notes["round3"] = []
    notes["round3"] += neutralise(S)
    notes["round3"] += living_vista(R)
    notes["round3"] += apply_fixes(S, R, slots, cube_lamp=rplan.get("hall_cube_lamp"))
    notes["round3"] += light_balance(a)
    bpy.context.view_layer.update()
    # camera check: 1.1.x values vs the round-2 cameras
    r2cams = r2.r2_cams(prop)
    r1cams = fr.prop_cams(prop)
    camcheck = {}
    for fid in ORDER:
        r2id = FRAMES[fid][1]
        old = r2cams.get(r2id) or r1cams.get({"H-B": "H0-B", "C-B": "C0-B", "W-A": "W0-A", "MB-A": "MB0-A"}.get(r2id, ""))
        C = cams[fid]
        same = bool(old and [round(x, 3) for x in old["loc"]] == [round(x, 3) for x in C["loc"]] and old["yaw"] == C["yaw"]
                    and old["u0"] == C["u0"] and old["v0"] == C["v0"])
        camcheck[fid] = dict(plan_1_1=dict(loc=C["loc"], yaw=C["yaw"], u0=C["u0"], v0=C["v0"]),
                             round2=(dict(loc=old["loc"], yaw=old["yaw"], u0=old["u0"], v0=old["v0"]) if old else None), identical=same)
    rep.update(stage="round 3 (Phase B clays, briefs/nordic-house-render-2026-10-24.md section 7)", date=time.strftime("%Y-%m-%d"),
               plan=os.path.relpath(plan_path, REPO), plan_version=plan0["version"], render_plan=os.path.relpath(a.plan, REPO),
               render_plan_version=rplan.get("version"), render_plan_source=rplan.get("source"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU seed 7, OIDN, AgX Medium High Contrast, exposure +{fr.EDIT_EXPOSURE}",
               light=f"round-2 editorial daylight (sky {a.sky} + area light outside every window + roof lights + AO 0.30) + the frame's S12 lamps; "
                     f"lamp colour {WARM_R3} (2700 K as a 4600 K balance sees it; round 2 used {fr.WARM}); living window light x{a.living_boost}; "
                     f"hall roof x{a.hall_roof}; bath window light x{a.bath_window}",
               albedo="M0 clay palette (build_alts.PAL) for every placeholder; kids' colour block as neutral grey " + PAINT_NEUTRAL,
               scene="framing_r2.build_r2 (plan 1.1 + picks H-B, C-B, W-A, MB-A + round-2 kids, bath, kitchen-dining + S11/S12) + round-3 changes",
               cameras=camcheck, build_notes=notes, build_s=round(time.time() - t0),
               lamps={k: dict(room=v["room"], typology=v["typ"], label=v["label"], shell=v["shell"]) for k, v in r2.LAMPS.items()})
    save()
    tmp = tempfile.mkdtemp(prefix="framing-r3-")
    for fid in frames:
        run_frame(fid, rplan["frames"][fid], S, R, slots, cams, plan, prop, tmp, a, rep, cfg)
        save()
        print("frame", fid, rep["frames"][fid]["runtime_s"], "s", "L", rep["frames"][fid]["mean_L"], flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if not a.no_sheet:
        sheet(rep, ORDER)
    save()


if __name__ == "__main__":
    main(sys.argv[1:])
