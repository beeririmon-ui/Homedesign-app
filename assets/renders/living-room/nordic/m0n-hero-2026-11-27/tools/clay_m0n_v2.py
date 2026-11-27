#!/usr/bin/env python3
"""
clay_m0n_v2.py: the M0-N clay moved toward the approved Nordic magazine frame (render-agent, 2026-11-27, brief
briefs/nordic-m0n-hero-2026-11-27.md). 0 var2 tokens. Imports ../../fb23-2026-11-26/clay_m0n.py (not edited): same camera, room,
sofa, armchair and product proxies; changed here:
  WINDOW (ARC1: openings and sills may change per style in the tool; the opening's plan position W-living Y 0.90-2.70, head 2.70 kept):
    sill 0.75 -> 0.45 on a built-in window seat (painted, three raised panels, linen seat pad), glazing 0.52-2.64 = tall double
    casements: four lights per leaf under a transom at 2.17-2.23, two fixed lights above; more snow and nearer birches outside.
  SUN (from the magazine frame, not the February 14:00 plan): latitude 60 N, 15 February, hour angle 15 (13:00 solar): alt 16.4,
    az 195.3, golden; the compass of the proposal (-X faces 220) kept. Through the casements onto the rug, the sofa and the back wall.
  PRODUCTS where the slot/engine rendered default differs from ch.7: framed-art = the Morandi triptych style D (3 x 50 x 70, gap 6,
    thin black frame; blank canvases here, the prints go in by code), curtains = the Japanese linen half shade (linen #D9CDB8, 260),
    floor-lamp = the black drum linen (pole and base black, drum D40 x 28, H ~155; moved 6 cm off the wall: (1.52, 0.26)).
  The vase stands on the window seat at (-2.40, 1.10).
Outputs (scratch): guide-hero.png (every product, sky + sun + lamps), guide-plate.png (the empty room: shell, sofa, armchair; sky +
sun), ids.png, depth.png/.json, sun.png (sun share), light-<lamp>.png, v2.json (V7Q6, F3, the light), overlay.jpg.
  python3 clay_m0n_v2.py [--quick] [--res 1920] [--spp 96] [--ha 15]
"""
import argparse
import importlib.util
import json
import math
import os
import sys
import time

SCR = os.environ.setdefault("FB23_SCRATCH", "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/m0n27")
ORIG = "/home/user/homedesign-app/assets/renders/living-room/nordic/fb23-2026-11-26/clay_m0n.py"
spec = importlib.util.spec_from_file_location("clay_m0n", ORIG)
M = importlib.util.module_from_spec(spec)
sys.modules["clay_m0n"] = M
spec.loader.exec_module(M)

import bpy  # noqa: E402
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image  # noqa: E402

box, lbox, cyl, seg, sheet, lathe, mcol, light, b = M.box, M.lbox, M.cyl, M.seg, M.sheet, M.lathe, M.mcol, M.light, M.b
I, F = M.PROD_IDX, M.FILLER_IDX
M.WIN = dict(y=(0.9, 2.7), sill=0.45, head=2.7, wall_out=-2.65, frame=(-2.62, -2.55))
M.SHELL_IDX["window_seat"] = 9
SUN_COLOR = (1.0, 0.88, 0.72)
FLOOR_LAMP = (1.52, 0.26)
M.LAMP_CAL["floor_lamp"] = ((2.10, 0.0, 1.30), 0.22, "back wall right of the drum (Bible: +20-25 %)")
M.GLOW_CAL["floor_lamp_glow"] = (FLOOR_LAMP[0], FLOOR_LAMP[1], 1.41)


def shell2():
    wall = mcol("wall", "#F4F1EC", 0.95, noise=0.012, nscale=(1.5, 1.5, 1.5))
    paint = mcol("paint_wood", "#F4F1EC", 0.55)
    (x0, x1), (y0, y1), h = M.ROOM["x"], M.ROOM["y"], M.ROOM["h"]
    t = 0.35
    S = M.SHELL_IDX
    rng = np.random.default_rng(23)
    box("floor_sub", x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, -0.06, -0.002, mcol("subfloor", "#7A6650", 0.9), S["floor"])
    for i, bx in enumerate(np.arange(x0, x1, 0.25)):
        y = y0 - rng.uniform(0, 1.5)
        while y < y1:
            L = rng.uniform(3.0, 4.0)
            jit = rng.normal(0, 0.035)
            c = np.clip(np.array([0xD6, 0xBF, 0x9E]) * (1 + jit), 0, 255).astype(int)
            mm = mcol(f"oak{i % 6}_{int(jit * 1000)}", "#%02X%02X%02X" % tuple(c), 0.55, noise=0.06, nscale=(60, 2.5, 60))
            box("floor", bx + 0.001, min(bx + 0.25, x1) - 0.001, max(y, y0) + 0.001, min(y + L, y1) - 0.001, -0.002, 0.0, mm, S["floor"])
            y += L
    box("ceiling", x0 - t, x1 + t, y0 - t, y1 + t, h, h + 0.2, wall, S["ceiling"])
    box("back_wall", x0 - t, x1 + t, y0 - t, y0, 0, h, wall, S["back_wall"])
    box("front_wall", x0 - t, x1 + t, y1, y1 + t, 0, h, wall, S["front_wall"])
    wy0, wy1 = M.WIN["y"]
    sill, head = M.WIN["sill"], M.WIN["head"]
    for args in [(x0 - t, x0, y0 - t, wy0, 0, h), (x0 - t, x0, wy1, y1 + t, 0, h), (x0 - t, -2.58, wy0, wy1, 0, sill), (x0 - t, x0, wy0, wy1, head, h)]:
        box("left_wall", *args, wall, S["left_wall"])
    for args in [(x1, x1 + 0.15, y0, 2.97, 0, h), (x1, x1 + 0.15, 4.57, y1, 0, h), (x1, x1 + 0.15, 2.97, 4.57, 2.40, h)]:
        box("right_wall", *args, wall, S["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 1.0, 1.15, 0, h, wall, S["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 6.5, 6.65, 0, h, wall, S["right_wall"])
    box("dining_box", x1 + 4.5, x1 + 4.65, 1.0, 6.65, 0, h, wall, S["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 1.0, 6.65, -0.05, 0.0, mcol("oak_d", "#D6BF9E", 0.6), S["right_wall"])
    box("dining_box", x1 + 0.15, x1 + 4.5, 1.0, 6.65, h, h + 0.1, wall, S["right_wall"])
    for args in [(x0, x1, y0, y0 + 0.015, 0, 0.15), (x1 - 0.015, x1, y0, 2.97, 0, 0.15), (x0, x0 + 0.015, y0, wy0, 0, 0.15),
                 (x0, x0 + 0.015, wy1, y1, 0, 0.15)]:
        box("skirting", *args, paint, S["back_wall"])
    for args in [(x0, x1, y0, y0 + 0.04, h - 0.10, h), (x0, x0 + 0.04, y0, y1, h - 0.10, h), (x1 - 0.04, x1, y0, y1, h - 0.10, h)]:
        box("cornice", *args, wall, S["ceiling"])
    # the window seat: carcass in the reveal and 0.40 into the room, recessed plinth, top board, three raised panels, linen pad
    WS = S["window_seat"]
    box("window_seat", -2.58, -1.90, wy0, wy1, 0.08, 0.42, paint, WS)
    box("window_seat", -2.58, -1.94, wy0 + 0.02, wy1 - 0.02, 0.0, 0.08, paint, WS)
    box("window_seat", -2.58, -1.875, wy0, wy1, 0.42, sill, paint, WS, bev=0.004)
    ys = np.linspace(wy0, wy1, 4)
    for yy in ys:
        box("window_seat", -1.90, -1.888, max(yy - 0.035, wy0), min(yy + 0.035, wy1), 0.08, 0.42, paint, WS)
    for (za, zb) in [(0.08, 0.14), (0.36, 0.42)]:
        box("window_seat", -1.90, -1.888, wy0, wy1, za, zb, paint, WS)
    for k in range(3):
        box("window_seat", -1.888, -1.882, ys[k] + 0.07, ys[k + 1] - 0.07, 0.18, 0.32, paint, WS, bev=0.003)
    box("window_seat", -2.52, -1.90, 1.30, wy1 - 0.06, sill, sill + 0.065, mcol("seat_linen", "#E4DACA", 1.0, noise=0.05, nscale=(200, 200, 200), sheen=0.2), WS, bev=0.02)
    # tall double casements: outer frame 6, centre mullion 6, transom 2.17-2.23; lower sashes 5 with three muntins (four lights), upper fixed lights
    W = S["window"]
    f0, f1 = M.WIN["frame"]
    zb_, zt = sill, head
    box("frame", f0, f1, wy0, wy0 + 0.06, zb_, zt, paint, W)
    box("frame", f0, f1, wy1 - 0.06, wy1, zb_, zt, paint, W)
    box("frame", f0, f1, wy0, wy1, zt - 0.06, zt, paint, W)
    box("frame", f0 - 0.02, f1, wy0, wy1, zb_, zb_ + 0.07, paint, W)
    box("frame", f0, f1, wy0, wy1, 2.17, 2.23, paint, W)
    ym = (wy0 + wy1) / 2
    box("frame", f0, f1, ym - 0.03, ym + 0.03, zb_, zt, paint, W)
    for s0, s1 in [(wy0 + 0.06, ym - 0.03), (ym + 0.03, wy1 - 0.06)]:
        za, zc = zb_ + 0.07, 2.17
        box("sash", f0 + 0.01, f1 + 0.005, s0, s0 + 0.05, za, zc, paint, W)
        box("sash", f0 + 0.01, f1 + 0.005, s1 - 0.05, s1, za, zc, paint, W)
        box("sash", f0 + 0.01, f1 + 0.005, s0, s1, za, za + 0.06, paint, W)
        box("sash", f0 + 0.01, f1 + 0.005, s0, s1, zc - 0.05, zc, paint, W)
        g0, g1 = za + 0.06, zc - 0.05
        for k in (1, 2, 3):
            zm = g0 + k * (g1 - g0) / 4
            box("muntin", f0 + 0.015, f1, s0, s1, zm - 0.015, zm + 0.015, paint, W)
        box("handle", f1, f1 + 0.03, (s1 - 0.08) if s0 < ym else (s0 + 0.05), (s1 - 0.05) if s0 < ym else (s0 + 0.08), 1.30, 1.42, mcol("brass", "#B79A6A", 0.4), W)
    # outside: snow on the ground, birches near and far
    gmat = bpy.data.materials.new("m0n_ground")
    gmat.use_nodes = True
    N, Lk = gmat.node_tree.nodes, gmat.node_tree.links
    bs = N["Principled BSDF"]
    tc, nz, ramp = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeTexNoise"), N.new("ShaderNodeValToRGB")
    nz.inputs["Scale"].default_value = 0.35
    nz.inputs["Detail"].default_value = 6.0
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.22, 0.30
    ramp.color_ramp.elements[0].color = M.srgb2lin("#8C8670")
    ramp.color_ramp.elements[1].color = M.srgb2lin("#F2F3F3")
    Lk.new(tc.outputs["Object"], nz.inputs["Vector"])
    Lk.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    Lk.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.9
    box("ground", -60, x0 - t, -40, 50, -0.35, -0.30, gmat, S["outside"])
    birch = mcol("birch", "#E6E3DC", 0.8, noise=0.25, nscale=(30, 30, 4))
    for (bx, by, r, hh) in [(-4.6, 0.4, 0.10, 9), (-5.4, 2.0, 0.12, 10), (-4.9, 3.3, 0.08, 9), (-6.6, 1.2, 0.09, 9), (-7.5, 0.6, 0.11, 9),
                            (-9.0, 2.2, 0.09, 9), (-8.2, 3.6, 0.13, 10), (-12.0, -0.8, 0.10, 9), (-13.5, 1.5, 0.12, 10),
                            (-11.0, 4.6, 0.08, 8), (-16.0, 3.0, 0.12, 10), (-6.2, -1.6, 0.10, 9)]:
        cyl("birch", bx, by, r, -0.3, hh, birch, S["outside"], r1=r * 0.5, n=16)
    return wall, paint


def remove_keys(keys):
    for k in keys:
        for ob in M.REG.pop(k, []):
            bpy.data.objects.remove(ob, do_unlink=True)


def products2():
    # the japandi print file the original code opens: a blank stand-in (that frame is removed right after)
    p = os.path.join(M.SKU, "framed-art-aliexpress-japandi-bare-branch-70x100-776445__0.jpg")
    if not os.path.exists(p):
        Image.new("RGB", (70, 100), (237, 232, 221)).save(p)
    M.products()
    remove_keys(["curtains", "curtains: front panel (out of frame)", "framed-art", "floor-lamp", "vase", "branches (filler)", "curtain rod (not sold)"])
    for ob in M.LIGHTS.pop("floor_lamp", []):
        bpy.data.objects.remove(ob, do_unlink=True)
    # curtains: the Japanese linen half shade, linen #D9CDB8, 260 from a rod at 2.82 (hem 0.22), stacked beside the window seat
    lin = mcol("linen_curtain", "#D9CDB8", 0.95, alpha=0.62, noise=0.05, nscale=(300, 300, 30))
    rod = mcol("charcoal_metal", "#3A3A3A", 0.5)
    seg("curtain rod (not sold)", (-2.21, 0.42, 2.84), (-2.21, 3.18, 2.84), 0.01, rod, F["curtain rod (not sold)"])
    for (ya, yb_, key) in [(0.46, 0.88, "curtains"), (2.72, 3.14, "curtains: front panel (out of frame)")]:
        sheet(key, lambda s, t, ya=ya, yb_=yb_: (-2.20 + 0.055 * math.sin(2 * math.pi * 5 * s), ya + (yb_ - ya) * s, 0.22 + t * 2.60),
              90, 24, lin, I["curtains"] if key == "curtains" else F[key])
    # framed art: the Morandi triptych, 3 x 50 x 70, gap 6 (162 wide), thin black frames 2 x 3 cm, centred (0.20, 0, 1.475); blank canvases
    blk = mcol("frame_black", "#232323", 0.5)
    canvas = mcol("canvas_cream", "#EDE8DD", 0.95)
    cz = 1.475
    for k in range(3):
        cx = 0.20 + (k - 1) * 0.56
        for args in [(cx - 0.25, cx + 0.25, 0.0, 0.03, cz + 0.33, cz + 0.35), (cx - 0.25, cx + 0.25, 0.0, 0.03, cz - 0.35, cz - 0.33),
                     (cx - 0.25, cx - 0.23, 0.0, 0.03, cz - 0.35, cz + 0.35), (cx + 0.23, cx + 0.25, 0.0, 0.03, cz - 0.35, cz + 0.35)]:
            box("framed-art", *args, blk, I["framed-art"])
        box("framed-art", cx - 0.23, cx + 0.23, 0.0, 0.015, cz - 0.33, cz + 0.33, canvas, I["framed-art"])
    # floor lamp: the black drum linen: base D26, pole, linen drum D40 x 28 (1.27-1.55), lit
    fx, fy = FLOOR_LAMP
    blk2 = mcol("black_metal", "#262626", 0.45)
    cyl("floor-lamp", fx, fy, 0.13, 0.0, 0.025, blk2, I["floor-lamp"], n=48)
    cyl("floor-lamp", fx, fy, 0.011, 0.025, 1.40, blk2, I["floor-lamp"], n=16)
    shade = mcol("drum_linen", "#E4DCCD", 0.9, emit=1.0)
    lathe("floor-lamp", fx, fy, [(0.20, 1.27), (0.20, 1.55)], shade, I["floor-lamp"], n=64, cap_bottom=False, cap_top=False,
          lightgroup="floor_lamp_glow", shadow=False)
    light("floor_lamp_bulb", "POINT", (fx, fy, 1.40), 3.0, "floor_lamp", size=0.05)
    # vase on the window seat's back end + eucalyptus branches (filler)
    vx, vy, vz = -2.40, 1.10, M.WIN["sill"]
    vprof = [(0.045, 0.0), (0.062, 0.03), (0.078, 0.10), (0.080, 0.15), (0.070, 0.22), (0.048, 0.28), (0.036, 0.305), (0.040, 0.32)]
    lathe("vase", vx, vy, vprof, M.mtex("vase", "vase", 0.9), I["vase"], z0=vz, cap_top=False)
    sage = mcol("eucalyptus", "#A3AC98", 0.8)
    rng = np.random.default_rng(5)
    for k in range(6):
        a = rng.uniform(0, 2 * np.pi)
        top = (vx + 0.10 * math.cos(a), vy + 0.22 * math.sin(a), vz + 0.75 + rng.uniform(0, 0.17))
        seg("branches (filler)", (vx, vy, vz + 0.28), top, 0.004, mcol("twig", "#6E6252", 0.8), F["branches (filler)"])
        for j in range(7):
            tt = 0.35 + 0.65 * j / 6
            pp = (vx + (top[0] - vx) * tt, vy + (top[1] - vy) * tt, vz + 0.28 + (top[2] - vz - 0.28) * tt)
            lbox("branches (filler)", 0.035, 0.004, 0.03, sage, F["branches (filler)"], pp, rot=(0, rng.uniform(-40, 40), rng.uniform(0, 180)))
    M.CARD.update({"curtains": "curtains-cj-japanese-linen-half-shade Linen W200 x H260, rod 2.84, hem 0.22 (slot/engine rendered default)",
                   "framed-art": "framed-art-cj-morandi-triptych-sage style D, 3 x 50 x 70, gap 6 (slot/engine rendered default)",
                   "floor-lamp": "floor-lamp-cj-black-drum-linen (card has no size: H ~155, drum D40 x 28, base D26) (slot/engine rendered default)",
                   "vase": "vase-cj-textured-white-stoneware D16 x H32, on the window seat"})
    M.POS.update({"curtains": "the back panel, stack Y 0.46-0.88 beside the window seat", "framed-art": "centres X -0.36, 0.20, 0.76, Z 1.475",
                  "floor-lamp": f"{FLOOR_LAMP} (6 cm off the slots point: the D40 drum)", "vase": "(-2.40, 1.10, 0.45) window seat"})


def world_and_sun2(ha):
    M.SUN = dict(R=220.0, lat=60.0, decl=-12.6, hour_angle=ha, angle=1.2)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("m0n_world")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.70, 0.80, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    sc.world.lightgroup = "sky"
    alt, az = M.sun_alt_az()
    th = math.radians(-(az - M.SUN["R"]))
    d = Vector((math.cos(th) * math.cos(math.radians(alt)), math.sin(th) * math.cos(math.radians(alt)), math.sin(math.radians(alt))))
    L = bpy.data.lights.new("sun", "SUN")
    L.energy, L.angle, L.color = 4.0, math.radians(M.SUN["angle"]), SUN_COLOR
    ob = bpy.data.objects.new("sun", L)
    sc.collection.objects.link(ob)
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    ob.lightgroup = "sun"
    M.LIGHTS["sun"] = [ob]
    return dict(M.SUN, alt=round(alt, 2), az=round(az, 2), color=SUN_COLOR, dir_plan=[round(-d.x, 4), round(d.y, 4), round(d.z, 4)],
                solar_time=f"{12 + ha / 15:.2f} h, 15 February, 60 N")


def sample(mask, n=5000, seed=3):
    ys, xs = np.nonzero(mask)
    if len(ys) > n:
        k = np.random.default_rng(seed).choice(len(ys), n, replace=False)
        ys, xs = ys[k], xs[k]
    return ys, xs


def Lmed(lin_px, k, wb, lift):
    return float(np.median(M.lab(M.tone(lin_px[None], k, wb, lift=lift))[0, :, 0]))


def solve_look(R, masks, ab=(1.8, 9.0), shade_L=78.0, sun_L=96.0, lift=0.004):
    """the sun's weight, the white balance (on the shaded back wall, daylight only) and the exposure (shaded wall L shade_L), so the
    sunlit back wall reads sun_L"""
    ys, xs = sample(masks["shade"])
    ys2, xs2 = sample(masks["sun"])
    sky_s, sun_s = R["sky"][ys, xs], R["sun"][ys, xs]
    sky_t, sun_t = R["sky"][ys2, xs2], R["sun"][ys2, xs2]
    pools_s = R["_pools"][ys, xs]
    pools_t = R["_pools"][ys2, xs2]

    def k_for(lin_px, wb, target):
        lo, hi = 0.01, 400.0
        for _ in range(40):
            k = math.sqrt(lo * hi)
            lo, hi = (k, hi) if Lmed(lin_px, k, wb, lift) < target else (lo, k)
        return math.sqrt(lo * hi)

    print("DBG masks", int(masks["shade"].sum()), int(masks["sun"].sum()), "shade sky/sun/pool", np.median(sky_s @ M.LUMW), np.median(sun_s @ M.LUMW),
          np.median(pools_s @ M.LUMW), "sun px sky/sun/pool", np.median(sky_t @ M.LUMW), np.median(sun_t @ M.LUMW), np.median(pools_t @ M.LUMW), flush=True)
    lo, hi = 0.002, 20.0
    for _ in range(26):
        s_ = math.sqrt(lo * hi)
        day = sky_s + s_ * sun_s
        wb = M.solve_wb(np.median(day, 0)[None, None], ab, None, 0, 0, r=6)
        k = k_for(day + pools_s, wb, shade_L)
        Lt = Lmed(sky_t + s_ * sun_t + pools_t, k, wb, lift)
        lo, hi = (s_, hi) if Lt < sun_L else (lo, s_)
    s_ = math.sqrt(lo * hi)
    day = sky_s + s_ * sun_s
    wb = M.solve_wb(np.median(day, 0)[None, None], ab, None, 0, 0, r=6)
    k = k_for(day + pools_s, wb, shade_L)
    return dict(sun=s_, wb=wb, k=k, lift=lift)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--res", type=int, default=1920)
    ap.add_argument("--spp", type=int, default=96)
    ap.add_argument("--ha", type=float, default=15.0)
    a = ap.parse_args(argv)
    out = os.path.join(SCR, "clay-quick" if a.quick else "clay")
    os.makedirs(out, exist_ok=True)
    W = 640 if a.quick else a.res
    H = W * 9 // 16
    spp = 16 if a.quick else a.spp
    t0 = time.time()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    shell2()
    M.sofa()
    M.armchair()
    products2()
    sun = world_and_sun2(a.ha)
    cam = M.camera()
    pc = M.projection_check(cam, W)
    print("projection check px", pc, sun, flush=True)

    R = M.render_passes("mat", W, H, spp)
    idx, depth = R["index"], R["depth"]

    def plum(lin, p, r=4):
        u, v, _ = M.plan_uv(*p)
        x, y = int(round(u * W)), int(round(v * H))
        return float(np.median(lin[y - r:y + r + 1, x - r:x + r + 1].reshape(-1, 3) @ M.LUMW))

    wts = {g: inc * plum(R["sky"], p) / max(plum(R[g], p), 1e-12) for g, (p, inc, _) in M.LAMP_CAL.items()}
    R["_pools"] = sum(wts[g] * R[g] for g in M.LAMP_GROUPS)
    sunL = R["sun"] @ M.LUMW
    skyL = R["sky"] @ M.LUMW
    poolL = R["_pools"] @ M.LUMW
    bw = idx == M.SHELL_IDX["back_wall"]
    ref = float(np.percentile(sunL[bw], 99.0))        # the direct sun on the back wall; its bounce elsewhere is a few % of it
    masks = dict(shade=bw & (sunL < 0.10 * ref) & (poolL < 0.10 * (skyL + 0.05 * sunL)), sun=bw & (sunL > 0.5 * ref))
    lk = solve_look(R, masks)
    lin = R["sky"] + lk["sun"] * R["sun"] + R["_pools"]
    gw = {}
    for g, p in M.GLOW_CAL.items():
        c = M.crop(lin, p, W, H, r=3)
        cg = M.crop(R[g], p, W, H, r=3)
        lo, hi = 0.0, 50.0
        for _ in range(36):
            w_ = (lo + hi) / 2
            lo, hi = (w_, hi) if M.Lc(c + w_ * cg, lk["k"], lk["wb"], lk["lift"]) < 94.0 else (lo, w_)
        gw[g] = (lo + hi) / 2
    gw["wall_sconce_glow"] = gw["pendant_glow"]
    hero = lin + sum(gw[g] * R[g] for g in M.GLOW_GROUPS)
    img, nfix = M.floor_fix(M.tone(hero, lk["k"], lk["wb"], lift=lk["lift"]), lk["lift"])
    M.save_png(os.path.join(out, "guide-hero.png"), img)
    # light maps (on the materials: for splitting the light layers, not a light measurement)
    sun_share = np.clip(lk["sun"] * sunL / np.maximum(skyL + lk["sun"] * sunL + poolL, 1e-9), 0, 1)
    Image.fromarray(np.rint(sun_share * 65535).astype(np.uint16)).save(os.path.join(out, "sun.png"))
    for g in M.LAMP_GROUPS + ["pendant_glow", "floor_lamp_glow"]:
        lm = R[g] @ M.LUMW
        rf = float(np.percentile(lm, 99.5))
        Image.fromarray(np.clip(np.rint(lm / max(rf, 1e-12) * 65535), 0, 65535).astype(np.uint16)).save(os.path.join(out, f"light-{g.replace('_', '-')}.png"))
    dpos = depth[np.isfinite(depth) & (depth < 1e5)]
    near, far = float(dpos.min()), float(np.percentile(dpos, 99.9))
    inv = np.clip((1 / np.clip(depth, near, far) - 1 / far) / (1 / near - 1 / far), 0, 1)
    Image.fromarray(np.rint(inv * 65535).astype(np.uint16)).save(os.path.join(out, "depth.png"))
    json.dump(dict(encoding="16-bit PNG, value = (1/d - 1/far) / (1/near - 1/far)", near_m=round(near, 4), far_m=round(far, 4), size=[W, H]),
              open(os.path.join(out, "depth.json"), "w"), indent=1)
    Image.fromarray(idx.astype(np.uint16)).save(os.path.join(out, "ids16.png"))
    M.ids_png(os.path.join(out, "ids.png"), idx)
    del R

    # the plate: the empty room (shell, sofa, armchair), sky + sun only
    keep = set(M.SHELL_IDX.values()) | {M.SOFA_IDX, M.ARMCHAIR_IDX}
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.pass_index not in keep:
            ob.hide_render = True
    for g, obs in M.LIGHTS.items():
        if g != "sun":
            for ob in obs:
                ob.hide_render = True
    P = M.render_passes("plate", W, H, spp)
    plin = P["sky"] + lk["sun"] * P["sun"]
    pimg, _ = M.floor_fix(M.tone(plin, lk["k"], lk["wb"], lift=lk["lift"]), lk["lift"])
    M.save_png(os.path.join(out, "guide-plate.png"), pimg)
    Image.fromarray(P["index"].astype(np.uint16)).save(os.path.join(out, "ids16-plate.png"))
    del P
    for ob in bpy.data.objects:
        ob.hide_render = False

    rows, f3 = M.measure(idx, depth, W, H, margin=int(0.6 * W))
    counted = [k for k, r in rows.items() if r.get("v7q6", "").startswith("counted")]
    Lh = M.lab(img)
    rec = dict(id="m0n-clay-v2-2026-11-27", author="render-agent", var2_tokens=0, script="tools/clay_m0n_v2.py (imports fb23-2026-11-26/clay_m0n.py)",
               size=[W, H], spp=spp, camera=M.CAM, projection_check_px=pc, sun=sun, look=dict(sun_weight=round(lk["sun"], 4), wb=[round(x, 4) for x in lk["wb"]],
               k=round(lk["k"], 4), lift=lk["lift"], glow=gw, lamp_weights={g: round(v, 5) for g, v in wts.items()},
               shade_wall_L=round(float(np.median(Lh[masks["shade"]][:, 0])), 1), sun_wall_L=round(float(np.median(Lh[masks["sun"]][:, 0])), 1),
               p0_5_L=round(float(np.percentile(Lh[..., 0], 0.5)), 1), floor_px_fixed=nfix),
               sun_share_pct={k: round(100 * float((sun_share[idx == v] > 0.25).mean()), 1) for k, v in list(I.items()) + list(M.SHELL_IDX.items()) if (idx == v).any()},
               v7q6=rows, v7q6_counted=f"{len(counted)} of {len([r for r in rows.values() if 'v7q6' in r])}", v7q6_counted_list=counted,
               f3_fails=[r for r in f3 if r.get("verdict", "").startswith("FAIL")], seconds=round(time.time() - t0))
    json.dump(rec, open(os.path.join(out, "v2.json"), "w"), indent=1, ensure_ascii=False, default=float)
    M.overlay(os.path.join(out, "overlay.jpg"), img, rows, sun_share > 0.25, np.zeros_like(sun_share, bool), W, H)
    print("DONE", rec["v7q6_counted"], rec["look"], rec["seconds"], "s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
