#!/usr/bin/env python3
"""
framing_wm_bath_b1.py: the warm-modern BATH as a clay, frame B1 (the window wall), render-agent, 2026-11-19. 0 var2 tokens.
Brief: briefs/wm-bath-b1-render-2026-11-19.md, step 1. Spec: docs/proposals/wm-bath-render-2026-11-17.md ch. 1 (the WC ledge,
the window, the WC), 3 ("the second frame"), 0א and 12; docs/proposals/wm-house-20-2026-11-19.md 2.2, 8.1 and 6.6א.

The scene is the B2 clay (framing_wm_bath.py, imported, nothing changed there: the same shell, stone, vanity, curtain, niche set,
floor planter and sconce pair) with the window wall of chapter 1 built for B1 by wm_b1():
  - the WC ledge: a plaster box to Z 0.92 under a limestone slab 8 cm thick (top at 1.00, front edge R 1 cm) that runs on, in one
    plane, into the window reveal as its sill (0.35 deep): one T-shaped slab (change 5). The box closes onto the north wall: 1.1 drew
    it from X 3.30, which leaves a 5 cm slot at the corner that B1 sees (the NE corner is in frame at u 0.11);
  - the window W-bath (X 3.45-4.25, sill 1.00, head 2.15): bronze-espresso steel profile #3A322C, 45 mm visible, one field, the fluted
    glass of 1.1 behind it; reveals plastered;
  - the WC: wall-hung, matte warm white #EDE6DA, soft rounded bowl, no high lid; the flush plate a bronze rounded rectangle centred
    on the box;
  - the B1 sconce: the same SKU as the mirror pair (037853 Style B, travertine block 8 x 8 x 16) at the plate (4.70, 9.95, 1.70),
    up and down light at 3000 K, as the pair;
  - the B1 products at their slots (house-20 2.2): the bath mat (Return Frame Khaki 40 x 60, the sample slot), the toilet-paper
    stand (60, base 17, arm 15; one roll as filler), the bin (walnut drum 26 x 32, swing lid), the toilet brush (fluted holder D11,
    40 overall), the candle cup (9 x 9.8) and the reed diffuser (about 7.5 x 11.5, reeds) on the slab, the black jar 30 (15 x 30)
    on the sill. The stool, the small print and the shelf planter are gaps: their places stay empty.
Frames (camera B1 of docs/house-plan.json: CB (3.80, 13.20, 1.15), yaw -22, 24 mm, u0 0.52, v0 0.46; the canvas and the 3 % overscan
of B2):
  B1          the defaults clay: everything above, the B2 products seen from B1 (curtain, niche set, floor planter) and the B1
              products; the B1 sconce, the pair (out of frame), the downlight and the niche LED lit
  B1-plate    the empty plate: shell + WC + ledge + window, every product hidden, every product lamp off (as B2-plate)
The tone is B2's recorded post (one exposure and one white balance for the camera point): --post-from the B2 selfcheck.

  python3 framing_wm_bath_b1.py --frames B1-plate,B1 --samples 16 --post-from framing/wm-bath-2026-11-17/selfcheck.json
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

import framing_wm_bath as W  # noqa: E402  (the B2 clay; its module code patches fr.render to capture the passes)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

r4, r3, r2, fr, bh = W.r4, W.r3, W.r2, W.fr, W.bh
OUT = os.path.join(HERE, "framing", "wm-bath-b1-2026-11-19")
SLAB = dict(x=(3.251, 4.40), y=(9.95, 10.15), z=(0.92, 1.00), r_front=0.01, sill_x=(3.45, 4.25), sill_y=(9.60, 9.95))
WIN = dict(x=(3.45, 4.25), z=(1.00, 2.15), y_glass=9.63, prof=0.045, depth=0.05)
WC = dict(x=(3.67, 4.03), y=(10.15, 10.69), z=(0.27, 0.41), seat=(0.41, 0.43), flush=(3.78, 3.92, 0.70, 0.80))
B1_SCONCE = dict(plate=(4.70, 9.95, 1.70), w=0.08, h=0.16, proj=0.08)
MAT = dict(x=(4.75, 5.15), y=(10.40, 11.00), h=0.015, frame=0.05, band_h=0.006)
STAND = dict(c=(4.49, 10.08), base_r=0.085, pole_r=0.010, h=0.60, arm=0.15)
BIN = dict(c=(4.68, 10.10), r_top=0.13, r_bot=0.096, h=0.32)
BRUSH = dict(c=(4.70, 10.30), r=0.055, holder_h=0.15, handle_r=0.008, top=0.40)
CANDLE = dict(c=(3.99, 10.09), r=0.045, h=0.098)
DIFF = dict(c=(4.10, 10.05), r=0.0375, h=0.115, lid=0.012, reed_top=0.32)
JAR = dict(c=(3.60, 9.75), r_sh=0.075, r_foot=0.052, r_neck=0.055, h=0.30)
HEX_B1 = dict(mat="#C4B08C", mat_frame="#CDBB98", stand="#1E1E1E", paper="#EFEAE2", bin="#6A4A35", brush="#9A6A4E", handle="#1E1E1E",
              candle="#ECE8E1", diff="#E6D8B0", lid="#B98E5A", reed="#222222", jar="#2B2B2B")
B1_IDS = {26: "WC bowl and seat, warm white", 27: "flush plate, bronze", 28: "WC ledge box, plaster", 29: "ledge slab + window sill, limestone",
          30: "window frame, bronze 45 mm", 31: "fluted glass", 32: "window reveals, plaster",
          53: "bath-mat (product)", 54: "toilet-paper-stand (product)", 55: "bin (product)", 56: "toilet-brush (product)",
          57: "candle (product)", 58: "reed-diffuser (product)", 59: "window-sill-vase (product)", 60: "wall-sconce B1 (product)",
          61: "paper roll (filler)"}
B1_PAL = {26: (250, 240, 225), 27: (60, 40, 30), 28: (210, 200, 185), 29: (230, 210, 170), 30: (40, 30, 70), 31: (170, 210, 255), 32: (200, 190, 170),
          53: (255, 140, 0), 54: (0, 255, 255), 55: (128, 64, 0), 56: (255, 0, 0), 57: (255, 200, 200), 58: (0, 128, 128), 59: (128, 0, 255),
          60: (255, 255, 128), 61: (230, 230, 230)}
PRODUCTS_B1 = ["shower-curtain", "shower-dispensers", "floor-planter", "bath-mat", "toilet-paper-stand", "bin", "toilet-brush", "candle",
               "reed-diffuser", "window-sill-vase", "wall-sconce"]
FRAMES_B1 = {"B1": dict(placeholders=PRODUCTS_B1, lamps=["bath/wall-sconce", "bath/vanity-sconces", "bath/shower-downlight", "bath/niche-led"],
                        also=["bath/floor-planter-filler", "bath/toilet-paper-roll"]),
             "B1-plate": dict(placeholders=[], lamps=["bath/shower-downlight", "bath/niche-led"])}


def m(key, rough=0.85):
    return W.fr.mat_cache("wm_bath_b1_" + key, HEX_B1[key], rough)


def wm_b1(R):
    notes = []
    n = W.kill_names(exact=("wc_ledge", "wc_bowl", "wc_seat", "wc_flush"))
    key = "bath WC + limestone ledge (fixed)"
    if key in fr.REG:
        fr.REG[key]["objs"] = [o for o in fr.REG[key]["objs"] if r3.alive(o)]
    notes.append(f"removed the 1.1 WC and ledge ({n} objects): rebuilt to chapter 1")
    pl, st, bz, san = W.mat("plaster", "plaster", 0.95), W.mat("stone", "stone", 0.75), W.mat("bronze", "bronze", 0.55), W.mat("sanitary", "sanitary", 0.6)
    # the B2 clay's plaster skin on the window wall runs over the window (B2 never saw it): cut round the opening
    W.kill_names(exact=("bath_wm_pl_e",))
    wx0, wx1 = WIN["x"]
    wz0, wz1 = WIN["z"]
    ys0 = 9.95 + W.SKIN
    W.reg_arch("bath_wm plaster window wall", [W.bx("pl_e_l", 3.25, wx0, ys0, ys0 + 0.001, W.SKIRT_H, 2.70, pl),
                                               W.bx("pl_e_r", wx1, W.SHOWER["x"][0], ys0, ys0 + 0.001, W.SKIRT_H, 2.70, pl),
                                               W.bx("pl_e_b", wx0, wx1, ys0, ys0 + 0.001, W.SKIRT_H, wz0, pl),
                                               W.bx("pl_e_t", wx0, wx1, ys0, ys0 + 0.001, wz1, 2.70, pl)], 2)
    S_ = SLAB
    box = [W.bx("ledge_box", S_["x"][0], S_["x"][1], S_["y"][0] + W.SKIN, S_["y"][1], 0.0, S_["z"][0], pl)]
    slab = [W.bx("ledge_slab", S_["x"][0], S_["x"][1], S_["y"][0], S_["y"][1], S_["z"][0], S_["z"][1], st, S_["r_front"]),
            W.bx("ledge_sill", S_["sill_x"][0], S_["sill_x"][1], S_["sill_y"][0], S_["sill_y"][1] + 0.001, S_["z"][0], S_["z"][1], st)]
    x0, x1 = WIN["x"]
    z0, z1 = WIN["z"]
    rev = [W.bx("rev_l", x0, x0 + 0.002, 9.60, 9.95, z0, z1, pl), W.bx("rev_r", x1 - 0.002, x1, 9.60, 9.95, z0, z1, pl),
           W.bx("rev_h", x0, x1, 9.60, 9.95, z1 - 0.002, z1, pl)]
    p, yg = WIN["prof"], WIN["y_glass"]
    yf0, yf1 = yg, yg + WIN["depth"]
    frame = [W.bx("win_fl", x0, x0 + p, yf0, yf1, z0, z1, bz), W.bx("win_fr", x1 - p, x1, yf0, yf1, z0, z1, bz),
             W.bx("win_fb", x0, x1, yf0, yf1, z0, z0 + p, bz), W.bx("win_ft", x0, x1, yf0, yf1, z1 - p, z1, bz)]
    wc = [W.bx("wc_bowl_b1", WC["x"][0], WC["x"][1], WC["y"][0], WC["y"][1], WC["z"][0], WC["z"][1], san, 0.07),
          W.bx("wc_seat_b1", WC["x"][0] + 0.005, WC["x"][1] - 0.005, WC["y"][0] + 0.005, WC["y"][1] - 0.005, WC["seat"][0], WC["seat"][1], san, 0.012)]
    fx0, fx1, fz0, fz1 = WC["flush"]
    flush = [W.bx("wc_flush_b1", fx0, fx1, WC["y"][0], WC["y"][0] + 0.008, fz0, fz1, bz, 0.012)]
    W.reg_arch("bath_wm_b1 WC (fixed)", wc, 26, kind="furniture")
    W.reg_arch("bath_wm_b1 flush plate (fixed)", flush, 27, kind="furniture")
    W.reg_arch("bath_wm_b1 ledge box", box, 28)
    W.reg_arch("bath_wm_b1 ledge slab + sill", slab, 29)
    W.reg_arch("bath_wm_b1 window frame", frame, 30)
    W.reg_arch("bath_wm_b1 window reveals", rev, 32)
    if "bath fluted glazing" in fr.REG:
        W.GROUP_ID["bath fluted glazing"] = 31
    notes.append("WC ledge: plaster box to Z 0.92, limestone slab 0.92-1.00 (front R 1 cm) X 3.251-4.40, on into the reveal as the sill "
                 "(X 3.45-4.25, Y 9.60-9.95); window: bronze profile 45 mm, one field, plastered reveals; WC warm white matte, bronze flush plate")
    return notes


def b1_products(R):
    notes = []
    # the B1 sconce: 037853 Style B as the pair, block 8 x 8 x 16 on the window wall, up and down light 3000 K
    old = r2.LAMPS.get("bath/wall-sconce")
    for li in (old or {}).get("lights", []):
        try:
            bpy.data.objects.remove(li, do_unlink=True)
        except ReferenceError:
            pass
    r3.kill_group(R, "bath/wall-sconce")
    px_, py_, pz_ = B1_SCONCE["plate"]
    S_ = B1_SCONCE
    blk = W.bx("b1_sconce", px_ - S_["w"] / 2, px_ + S_["w"] / 2, py_ + W.SKIN, py_ + S_["proj"], pz_ - S_["h"] / 2, pz_ + S_["h"] / 2,
               W.mat("trav", "trav", 0.85), 0.004)
    lights = []
    for k, (dz, rot) in enumerate(((-S_["h"] / 2 - 0.004, 0.0), (S_["h"] / 2 + 0.004, math.pi))):
        li = r2.mk_light(f"bath_wm_b1_sconce_{'du'[k]}", "SPOT", (px_, py_ + S_["proj"] / 2, pz_ + dz), W.LIGHT["sconce_w"])
        li.rotation_euler = (rot, 0.0, 0.0)
        li.data.spot_size = math.radians(W.LIGHT["sconce_spot_deg"])
        li.data.spot_blend = 0.35
        li.data.shadow_soft_size = 0.02
        li.visible_camera = False
        li.data.color = (1.0, 0.80, 0.58)
        lights.append(li)
    W.reg_prod(R, "wall-sconce", [blk], 60, "037853 Style B (the pair's SKU), 8 x 8 x 16 at the plate (4.70, 9.95, 1.70), up-down 3000 K")
    r2.lamp("bath/wall-sconce", "bath", "wall", [(blk, W.LIGHT["sconce_glow"])], lights, "B1 travertine block, Style B, up-down")
    # bath mat, Return Frame Khaki 40 x 60: a tufted field and a raised frame band
    M_ = MAT
    mx0, mx1 = M_["x"]
    my0, my1 = M_["y"]
    f = M_["frame"]
    mat_objs = [W.bx("mat_field", mx0, mx1, my0, my1, 0.0, M_["h"], m("mat", 0.98), 0.004)]
    for nm, a, b, c, d in (("l", mx0 + 0.02, mx0 + 0.02 + f / 2, my0 + 0.02, my1 - 0.02), ("r", mx1 - 0.02 - f / 2, mx1 - 0.02, my0 + 0.02, my1 - 0.02),
                           ("n", mx0 + 0.02, mx1 - 0.02, my0 + 0.02, my0 + 0.02 + f / 2), ("s", mx0 + 0.02, mx1 - 0.02, my1 - 0.02 - f / 2, my1 - 0.02)):
        mat_objs.append(W.bx(f"mat_band_{nm}", a, b, c, d, M_["h"], M_["h"] + M_["band_h"], m("mat_frame", 0.98), 0.002))
    W.reg_prod(R, "bath-mat", mat_objs, 53, "house-20 8.1: Return Frame Khaki 40 x 60 at X 4.75-5.15, Y 10.40-11.00 (the 60 runs 5 cm past the 55 zone, as the card)")
    # toilet-paper stand: base D17, pole to 0.60, arm 15 at the top (toward +X), one roll (filler)
    T = STAND
    c = T["c"]
    stand = [W.cyl("tps_base_b1", c, T["base_r"], 0.0, 0.012, m("stand", 0.6)), W.cyl("tps_pole_b1", c, T["pole_r"], 0.012, T["h"], m("stand", 0.6), 16),
             r2.obox("bath_wm_b1_tps_arm", (c[0], c[1], T["h"] - 0.006), (c[0] + T["arm"], c[1], T["h"] - 0.006), (0, 0, 1), 0.012, 0.012, m("stand", 0.6)),
             r2.obox("bath_wm_b1_tps_tip", (c[0] + T["arm"], c[1], T["h"] - 0.006), (c[0] + T["arm"], c[1], T["h"] - 0.03), (1, 0, 0), 0.012, 0.012, m("stand", 0.6))]
    W.reg_prod(R, "toilet-paper-stand", stand, 54, "12000053061878471: matte black, 60 high, base D17, arm 15; at (4.49, 10.08) (1 cm left of the slot: the D17 base and the D26 bin)")
    roll = [r2.obox("bath_wm_b1_roll", (c[0] + 0.03, c[1], T["h"] - 0.065), (c[0] + 0.135, c[1], T["h"] - 0.065), (0, 0, 1), 0.11, 0.11, m("paper", 0.95))]
    W.reg_prod(R, "toilet-paper-roll", roll, 61, "one roll on the arm (filler)")
    # bin: walnut drum, top D26, foot about D19, 32 high, flat swing lid
    B = BIN
    binm = [r3.cone("bath_wm_b1_bin", B["c"], B["r_bot"], B["r_top"], 0.0, B["h"], m("bin", 0.7), 64),
            W.cyl("bin_lid", B["c"], B["r_top"] - 0.006, B["h"] - 0.004, B["h"] + 0.002, m("bin", 0.7), 64)]
    W.reg_prod(R, "bin", binm, 55, "CJJT102413505EV: walnut veneer drum, top D26, foot about D19, 32 high, swing lid; at (4.68, 10.10) (4 cm right of the slot: the stand's base)")
    # toilet brush: fluted holder D11 x 15, black handle to 0.40
    Br = BRUSH
    brush = [W.cyl("brush_holder", Br["c"], Br["r"], 0.0, Br["holder_h"], m("brush", 0.85), 48),
             W.cyl("brush_handle", Br["c"], Br["handle_r"], Br["holder_h"], Br["top"], m("handle", 0.6), 16)]
    W.reg_prod(R, "toilet-brush", brush, 56, "CJYD254508501AZ: fluted terracotta-brown holder D11 x 15, black handle, 40 overall; at (4.70, 10.30)")
    # candle cup and reed diffuser on the slab (Z 1.00), the black jar on the sill
    zt = SLAB["z"][1]
    W.reg_prod(R, "candle", [W.cyl("candle_cup", CANDLE["c"], CANDLE["r"], zt, zt + CANDLE["h"], m("candle", 0.9), 48)], 57,
               "CJJT120250201AZ: ribbed matte white cup 9 x 9.8 at (3.99, 10.09), Z 1.00")
    D = DIFF
    diff = [W.cyl("diff_body", D["c"], D["r"], zt, zt + D["h"], m("diff", 0.9), 48),
            W.cyl("diff_lid", D["c"], D["r"] - 0.002, zt + D["h"], zt + D["h"] + D["lid"], m("lid", 0.8), 48)]
    for i, (dx, dy, tx) in enumerate(((-0.006, 0.0, -0.03), (0.004, 0.004, 0.0), (0.006, -0.004, 0.03))):
        diff.append(r2.obox(f"bath_wm_b1_reed{i}", (D["c"][0] + dx, D["c"][1] + dy, zt + D["h"]), (D["c"][0] + dx + tx, D["c"][1] + dy, zt + D["reed_top"]),
                            (1, 0, 0), 0.004, 0.004, m("reed", 0.6)))
    W.reg_prod(R, "reed-diffuser", diff, 58, "travertine-look milk-tea vessel about 7.5 x 11.5 (carton 9 x 9 x 13), bamboo lid, three black reeds to Z 1.32; at (4.10, 10.05)")
    J = JAR
    jar = [r3.cone("bath_wm_b1_jar_low", J["c"], J["r_foot"], J["r_sh"], zt, zt + 0.21, m("jar", 0.9), 64),
           r3.cone("bath_wm_b1_jar_sh", J["c"], J["r_sh"], J["r_neck"], zt + 0.21, zt + J["h"] - 0.02, m("jar", 0.9), 64),
           W.cyl("jar_neck", J["c"], J["r_neck"], zt + J["h"] - 0.02, zt + J["h"], m("jar", 0.9), 64)]
    W.reg_prod(R, "window-sill-vase", jar, 59, "CJJT198137605EV (Style4): neutral black matte jar 15 x 30, mouth 11, on the sill at (3.60, 9.75)")
    notes.append("B1 products at their slots (house-20 2.2 / 8.1); the stand 1 cm left and the bin 4 cm right of the slot points so the "
                 "D17 base and the D26 drum do not meet; the shelf planter, the stool and the print are gaps (empty)")
    return notes


def lock_target_b1(cam, depth_img):
    H, Wd = depth_img.shape
    cye = 9.95 + W.CLAD_T
    L = {
        "NE corner (north wall / window wall)": ((3.25, 9.95, 0.08), (3.25, 9.95, 2.70)),
        "cladding end, window wall (X 5.20)": ((5.20, cye, 0.0), (5.20, cye, 2.70)),
        "SE corner (stone inside corner)": ((6.25 - W.CLAD_T, cye, 0.0), (6.25 - W.CLAD_T, cye, 2.70)),
        "cladding joint Z 1.40, east": ((5.20, cye, 1.40), (6.25 - W.CLAD_T, cye, 1.40)),
        "ceiling line, window wall": ((3.25, 9.95, 2.70), (5.20, 9.95, 2.70)),
        "floor line, window wall (ledge to shower)": ((4.40, 9.95, 0.0), (5.20, 9.95, 0.0)),
        "skirting top, window wall": ((4.40, 9.95, 0.08), (5.20, 9.95, 0.08)),
        "ledge slab, front top edge (Z 1.00)": ((3.30, 10.15, 1.00), (4.40, 10.15, 1.00)),
        "ledge slab, front bottom edge (Z 0.92)": ((3.30, 10.15, 0.92), (4.40, 10.15, 0.92)),
        "ledge box, right edge (X 4.40)": ((4.40, 10.15, 0.08), (4.40, 10.15, 0.92)),
        "window, left reveal edge (X 3.45)": ((3.45, 9.95, 1.00), (3.45, 9.95, 2.15)),
        "window, right reveal edge (X 4.25)": ((4.25, 9.95, 1.00), (4.25, 9.95, 2.15)),
        "window, head edge (Z 2.15)": ((3.45, 9.95, 2.15), (4.25, 9.95, 2.15)),
        "floor joint X 4.45": ((4.45, 10.15, 0.0), (4.45, 13.59, 0.0)),
        "floor joint X 5.05": ((5.05, 9.95, 0.0), (5.05, 13.59, 0.0)),
        "floor joint X 3.85": ((3.85, 10.70, 0.0), (3.85, 13.59, 0.0)),
        "floor joint Y 11.15": ((3.25, 11.15, 0.0), (5.20, 11.15, 0.0)),
        "floor joint Y 12.35": ((3.25, 12.35, 0.0), (6.25, 12.35, 0.0)),
    }
    yaw = math.radians(-22.0)
    out = {}
    for name, (a, b) in L.items():
        pts, vis = [], 0
        for t in np.linspace(0, 1, 41):
            p = [a[i] + (b[i] - a[i]) * t for i in range(3)]
            u, v = fr.U(cam, *p), fr.V(cam, *p)
            if not (0 <= u < 1 and 0 <= v < 1):
                continue
            x, y = int(u * Wd), int(v * H)
            dp = -math.sin(yaw) * (p[0] - 3.80) - math.cos(yaw) * (p[1] - 13.20)
            dd = float(depth_img[y, x])
            seen = abs(dd - dp) < 0.02 + 0.01 * dp
            vis += seen
            pts.append([round(u * W.CANVAS[0], 2), round(v * W.CANVAS[1], 2), bool(seen)])
        if pts:
            out[name] = dict(xyz=[list(a), list(b)], px_ends=[W.px(cam, *a), W.px(cam, *b)], samples=pts, visible_frac=round(vis / len(pts), 3))
    return out


def readings_b1(path, cam):
    from PIL import Image
    import colorsys
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255.0
    pts = {"plaster beside the window (4.55, 9.95, 2.00)": (4.55, 9.951, 2.00), "plaster above the window (3.85, 9.95, 2.45)": (3.85, 9.951, 2.45),
           "plaster, north wall (3.25, 11.5, 1.6)": (3.251, 11.5, 1.6), "stone, shower east wall (5.70, 1.70)": (5.70, 9.962, 1.70),
           "ledge slab top (4.20, 10.12, 1.00)": (4.20, 10.12, 1.0), "floor stone (4.3, 11.6)": (4.3, 11.6, 0.0)}
    out = {}
    H, Wd = a.shape[:2]
    for k, p in pts.items():
        uu, vv = fr.U(cam, *p), fr.V(cam, *p)
        x, y = int(uu * Wd), int(vv * H)
        if not (8 <= x < Wd - 8 and 8 <= y < H - 8):
            out[k] = "outside the canvas"
            continue
        q = a[y - 8:y + 8, x - 8:x + 8].reshape(-1, 3).mean(0)
        h, l, s = colorsys.rgb_to_hls(*q)
        lin = W.srgb_to_lin(q * 255)
        Y = float(lin @ np.array([0.2126, 0.7152, 0.0722]))
        Ls = 116 * (Y ** (1 / 3)) - 16 if Y > 0.008856 else 903.3 * Y
        out[k] = dict(rgb=[int(round(c * 255)) for c in q], H=round(h * 360, 1), L_hsl=round(l * 100, 1), L_star=round(Ls, 1))
    x0, y0, x1, y1 = [int(round(c)) for c in W.FRAME_BOX]
    rgb = a[y0:y1, x0:x1] * 255
    out["frame_mean_L_8bit"] = round(float((rgb * [0.2126, 0.7152, 0.0722]).sum(2).mean()), 1)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="B1-plate,B1")
    ap.add_argument("--res", type=int, default=W.CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=W.LIGHT["window"])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--post-from", default=os.path.join(HERE, "framing", "wm-bath-2026-11-17", "selfcheck.json"))
    a, _ = ap.parse_known_args(argv)
    out = a.out
    os.makedirs(out, exist_ok=True)
    for d in ("exr", "npz", "raw"):
        os.makedirs(os.path.join(W.SCR, d), exist_ok=True)
    raw = os.path.join(W.SCR, "raw")
    r3.set_out(raw)
    frames = [f for f in a.frames.split(",") if f]
    t0 = time.time()
    W.IDS.update(B1_IDS)
    W.PAL.update(B1_PAL)
    W.PRODUCT_IDS.update(set(range(53, 62)))
    W.ARCH_IDS.update({28, 29, 30, 31, 32})
    W.FIXED_IDS.update({26, 27})
    r2.WARM = r3.WARM_R3
    cams, plan_doc = r3.cameras_1_1()
    for fid in FRAMES_B1:
        r3.FRAMES[fid] = ("bath", "B1", "bath")
        r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT["B1"]
        cams[fid] = dict(cams["B1"], id=fid)
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
    notes["wm_bath"] = W.wm_bath(R)
    W.wm_vanity()
    notes["wm_bath"] += W.wm_products(R)
    notes["wm_b1"] = wm_b1(R) + b1_products(R)
    bpy.context.view_layer.update()
    rep = dict(stage="warm-modern bath clay, B1 (render-agent, 2026-11-19; briefs/wm-bath-b1-render-2026-11-19.md)",
               date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"], camera=cams["B1"],
               canvas=dict(px=list(W.CANVAS), frame_box=[round(c, 2) for c in W.FRAME_BOX], K=W.K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: B2's recorded post",
               build_notes=notes, ids=W.IDS, frames={})
    prev = os.path.join(out, "selfcheck.json")
    if os.path.exists(prev):
        old = json.load(open(prev))
        rep["frames"] = {k: v for k, v in old.get("frames", {}).items() if k not in frames}
    tmp = tempfile.mkdtemp(prefix="wm-bath-b1-")
    r4.OS_STATE["on"] = True
    for fid in frames:
        F = FRAMES_B1[fid]
        fplan = dict(placeholders=F["placeholders"], lamps=F["lamps"], also_visible=F.get("also", []), notes=f"warm-modern {fid}")
        Rr = r3.run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, {}, cfg)
        depth, idx, normal = W.CAPTURE["last"]
        ids, counts, pid = W.save_passes(fid, out, depth, idx, normal)
        cam = S["cam"]
        Rr["id_px"] = counts
        Rr["pidx_to_id"] = pid
        Rr["boxes_frame"] = {W.IDS[g]: W.bbox_f(ids, {g}) for g in sorted(W.PRODUCT_IDS | W.FIXED_IDS | {29, 30, 31}) if W.bbox_f(ids, {g})}
        if fid == "B1":
            json.dump(dict(frame="B1 clay", canvas=list(W.CANVAS), frame_box=[round(c, 2) for c in W.FRAME_BOX], camera=cams["B1"],
                           method="analytic projection of the 3D lines; 'samples' are [x, y, seen] in canvas px, seen = the depth pass agrees",
                           lines=lock_target_b1(cam, depth)), open(os.path.join(out, "lock-target.json"), "w"), indent=1)
        shutil.copy(os.path.join(raw, f"{fid}.png"), os.path.join(W.SCR, "raw", f"{fid}-untoned.png"))
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr["runtime_s"], "s", flush=True)
    cam = S["cam"]
    fixed = json.load(open(a.post_from))["post"]
    rep["post"] = W.tone_frames(frames, cam, frames[0], out, fixed)
    for fid in frames:
        rep["frames"][fid]["readings"] = readings_b1(os.path.join(out, f"{fid}.png"), cam)
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
