#!/usr/bin/env python3
"""
framing_wm_master_mb1.py: the warm-modern MASTER BEDROOM as a clay, frame MB1 (the second frame: three-quarter view from the foot of the
bed), render-agent, 2026-11-19. 0 var2 tokens.
Brief: briefs/wm-master-mb1-render-2026-11-19.md, step 1. Spec: docs/proposals/wm-master-bedroom-render-2026-11-17.md 13.6-13.11;
docs/proposals/wm-house-20-2026-11-19.md 1.2, 1.3, 1.5, 8 and 6.6a; docs/proposals/wm-mb1-forward-check-2026-11-19.md (the camera).

The scene is the MB0 clay (framing_wm_master.py, imported, nothing changed there: the same shell, bed, nightstands, light and the 3.2 +
12.2 defaults) with what MB1 adds, at the places the passed MB0 render has them:
  - fixed (in the plate): the walnut wall shelf 180 x 24 x 4 (Z 1.46-1.50) and the plan-B studio bench (house-20 1.3): walnut top
    130 x 40 x 5 on two 5 cm end panels, seat at 45, X -1.35..-0.05, Y 19.76-20.16, corners R 1.5;
  - products (boxes / turned shapes at their MB0 places): the two frames (A 54 x 74, B 44 x 34, blank canvases), the two shelf vases,
    the planter (the pot at (1.45, 17.88), 42 x 35.5, with the ficus as a crown), the magazine holder (35 x 19 x 27.5, its long axis
    along the MB0 render's), the carafe (0.33, 17.84), the waffle throw folded on the bench's left half (dropping 18 cm in front), the
    rope basket under its right half (D 30), the braided rug 200 x 300 (X -2.20..0.80, Y 18.30-20.30).
Camera MB1 (the manager's ruling on the motion check): (1.60, 21.20, 1.05), yaw 33.7, 24 mm, tilt 0, u0 0.50, v0 0.418; the MB0
canvas 2720 x 1530 with the 16:9 frame at [77.49, 43.43, 2642.51, 1486.57] (the round-4 overscan).
  MB1         the defaults clay: everything; the sconce pair and the floor lamp lit
  MB1-plate   the empty plate: shell + bed + nightstands + shelf + bench, every product hidden, every lamp off
The tone is MB0's recorded post (one exposure and one white balance for the house light).

  python3 framing_wm_master_mb1.py --frames MB1-plate,MB1 --samples 16
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
sys.argv = [sys.argv[0]]

import framing_wm_master as fm  # noqa: E402  (the MB0 clay; its module code patches fr.render to capture the passes)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

r4, r3, r2, fr, bh = fm.r4, fm.r3, fm.r2, fm.fr, fm.bh
OUT = "/home/user/homedesign-app/assets/renders/master/warm-modern/mb1-2026-11-19/clay"
CAM_MB1 = dict(loc=[1.60, 21.20, 1.05], yaw=33.7, u0=0.50, v0=0.418)
SHELF = dict(x=(-1.60, 0.20), y=(17.66, 17.90), z=(1.46, 1.50))
BENCH = dict(x=(-1.35, -0.05), y=(19.76, 20.16), seat=0.45, top_t=0.05, end_t=0.05, r=0.015)
ART = dict(A=dict(x=(-1.244, -0.695), z=(1.50, 2.243)), B=dict(x=(-0.639, -0.191), z=(1.50, 1.838)), y=(17.70, 17.73), moulding=0.025)
VASES = dict(left=dict(c=(-1.395, 17.78), r=0.11, h=0.32, hexc="#3B3634"), right=dict(c=(0.0, 17.78), r=0.113, h=0.33, hexc="#E8E2D8"))
POT = dict(c=(1.45, 17.88), r=0.21, h=0.355)
CROWN = dict(c=(1.38, 17.98), r=0.32, z=(0.95, 1.75), trunk_top=1.05)
HOLDER = dict(c=(1.04, 18.50), l=0.35, w=0.19, h=0.275, axis_deg=72.0)
CARAFE = dict(c=(0.33, 17.84), r=0.062, z=(0.55, 0.79))
THROW = dict(x=(-1.30, -0.75), y=(19.80, 20.16), z=(0.45, 0.47), drop=0.18)
BASKET = dict(c=(-0.40, 19.96), r=0.15, h=0.30)
RUG = dict(x=(-2.20, 0.80), y=(18.30, 20.30), h=0.012)
MB1_IDS = {28: "wall shelf, walnut (fixed, plan B)", 29: "bench top, walnut (fixed, plan B)", 30: "bench end panels, walnut (fixed, plan B)",
           56: "framed-art (product)", 57: "framed-art-2 (product)", 58: "art canvases (blank)", 59: "shelf-vase-left (product)",
           60: "shelf-vase-right (product)", 61: "planter (product)", 62: "ficus (filler)", 63: "magazine-holder (product)",
           64: "bedside-carafe (product)", 65: "bench-throw (product)", 66: "bench-basket (product)", 67: "rug (product)"}
MB1_PAL = {28: (107, 74, 51), 29: (120, 84, 58), 30: (95, 66, 45), 56: (90, 60, 40), 57: (110, 75, 50), 58: (233, 226, 214),
           59: (59, 54, 52), 60: (232, 226, 216), 61: (203, 191, 174), 62: (111, 127, 98), 63: (74, 74, 76), 64: (176, 160, 140),
           65: (180, 156, 128), 66: (184, 154, 116), 67: (217, 205, 184)}
NEW_PRODUCTS = ["framed-art", "framed-art-2", "shelf-vase-left", "shelf-vase-right", "planter", "magazine-holder", "bedside-carafe",
                "bench-throw", "bench-basket", "rug"]
FRAMES_MB1 = {"MB1": dict(placeholders=fm.PRODUCTS + NEW_PRODUCTS, lamps=["master/bedside-sconces", "master/floor-lamp"],
                          also=fm.FILLERS + ["master/planter-filler"], fixed=True),
              "MB1-plate": dict(placeholders=[], lamps=[], fixed=True)}


def M(name, hexc, rough=0.9):
    return fr.mat_cache("wm_mb1_" + name, hexc, rough)


def rect_loop(cx, cy, l, w, deg):
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    pts = []
    for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts.append((cx + s * l / 2 * ux + t * w / 2 * vx, cy + s * l / 2 * uy + t * w / 2 * vy))
    return pts


def mb1_fixed():
    """the shelf and the plan-B bench: fixed, in the plate"""
    wal = fm.mat("walnut", "walnut", 0.7)
    (x0, x1), (y0, y1), (z0, z1) = SHELF["x"], SHELF["y"], SHELF["z"]
    shelf = [fm.bx("mb1_shelf", x0, x1, y0, y1, z0, z1, wal, 0.003)]
    b = BENCH
    (bx0, bx1), (by0, by1) = b["x"], b["y"]
    top = [fm.prism("mb_wm_mb1_bench_top", fm.rrect_xy(bx0, bx1, by0, by1, b["r"]), "z", b["seat"] - b["top_t"], b["seat"], wal)]
    ends = [fm.bx("mb1_bench_end_l", bx0, bx0 + b["end_t"], by0 + 0.005, by1 - 0.005, 0.0, b["seat"] - b["top_t"], wal, 0.004),
            fm.bx("mb1_bench_end_r", bx1 - b["end_t"], bx1, by0 + 0.005, by1 - 0.005, 0.0, b["seat"] - b["top_t"], wal, 0.004)]
    fm.reg_arch("mb_wm wall shelf (fixed, plan B)", shelf, 28, kind="furniture")
    fm.reg_arch("mb_wm bench top (fixed, plan B)", top, 29, kind="furniture")
    fm.reg_arch("mb_wm bench ends (fixed, plan B)", ends, 30, kind="furniture")
    return shelf + top + ends


def mb1_products(R):
    wal = fm.mat("walnut", "walnut", 0.7)
    canvas = M("canvas", "#D8C8AE", 0.95)
    notes = []
    for key, slot, gid in (("A", "framed-art", 56), ("B", "framed-art-2", 57)):
        (x0, x1), (z0, z1) = ART[key]["x"], ART[key]["z"]
        y0, y1 = ART["y"]
        mo = ART["moulding"]
        objs = [fm.bx(f"mb1_frame_{key}", x0, x1, y0, y1, z0, z1, wal, 0.002)]
        cv = [fm.bx(f"mb1_canvas_{key}", x0 + mo, x1 - mo, y1, y1 + 0.004, z0 + mo, z1 - mo, canvas)]
        fm.reg_prod(R, slot, objs + cv, gid, "13.6 / FB10 (MB0 render)")
        notes.append(f"{slot}: X {x0}..{x1}, Z {z0}..{z1}, blank canvas #D8C8AE")
    for side, slot, gid in (("left", "shelf-vase-left", 59), ("right", "shelf-vase-right", 60)):
        v = VASES[side]
        z0 = SHELF["z"][1]
        if side == "left":
            objs = [fm.cone("mb1_vase_l", v["c"], v["r"] * 0.80, v["r"], z0, z0 + v["h"] * 0.85, M("charcoal", v["hexc"], 0.8)),
                    fm.cone("mb1_vase_l_sh", v["c"], v["r"], v["r"] * 0.70, z0 + v["h"] * 0.85, z0 + v["h"], M("charcoal", v["hexc"], 0.8))]
        else:
            objs = [fm.cone("mb1_vase_r_lo", v["c"], v["r"] * 0.30, v["r"], z0, z0 + v["h"] * 0.70, M("white", v["hexc"], 0.8)),
                    fm.cone("mb1_vase_r_hi", v["c"], v["r"], v["r"] * 0.20, z0 + v["h"] * 0.70, z0 + v["h"], M("white", v["hexc"], 0.8))]
        fm.reg_prod(R, slot, objs, gid, "13.6 / FB10 (MB0 render)")
    pot = [fm.cone("mb1_pot", POT["c"], POT["r"] * 0.80, POT["r"], 0.0, POT["h"] * 0.6, M("cement", "#CBBFAE", 0.9)),
           fm.cone("mb1_pot_top", POT["c"], POT["r"], POT["r"] * 0.86, POT["h"] * 0.6, POT["h"], M("cement", "#CBBFAE", 0.9))]
    fm.reg_prod(R, "planter", pot, 61, "13.2 / FB10 + 13.11 (MB0 render: the pot in code)")
    plant = [fm.cyl("mb1_trunk", POT["c"], 0.02, POT["h"], CROWN["trunk_top"], M("bark", "#C9C2B5", 0.9), 12),
             r3.ell("mb_wm_mb1_crown", CROWN["c"], CROWN["r"], CROWN["z"][0], CROWN["z"][1], M("leaf", "#55654A", 0.9))]
    r3.reg(R, "master/planter-filler", plant, "master", src="ficus Audrey (filler)")
    fm.GROUP_ID["master/planter-filler"] = 62
    h = HOLDER
    hold = [fm.prism("mb_wm_mb1_holder", rect_loop(h["c"][0], h["c"][1], h["l"], h["w"], h["axis_deg"]), "z", 0.0, h["h"],
                     M("gunmetal", "#2A2A2C", 0.6))]
    fm.reg_prod(R, "magazine-holder", hold, 63, "13.2 / FB10 + 13.11 (MB0 render)")
    car = [fm.cone("mb1_carafe", CARAFE["c"], CARAFE["r"] * 0.75, CARAFE["r"], CARAFE["z"][0], CARAFE["z"][0] + 0.16, M("patina", "#B0A08C", 0.9)),
           fm.cone("mb1_carafe_neck", CARAFE["c"], CARAFE["r"], CARAFE["r"] * 0.5, CARAFE["z"][0] + 0.16, CARAFE["z"][1], M("patina", "#B0A08C", 0.9))]
    fm.reg_prod(R, "bedside-carafe", car, 64, "13.6 / FB10 (MB0 render)")
    th = M("waffle", "#B49C80", 0.95)
    (tx0, tx1), (ty0, ty1), (tz0, tz1) = THROW["x"], THROW["y"], THROW["z"]
    thr = [fm.bx("mb1_bthrow", tx0, tx1, ty0, ty1, tz0, tz1, th, 0.005),
           fm.bx("mb1_bthrow_drop", tx0, tx1, ty1, ty1 + 0.02, tz1 - THROW["drop"], tz1, th)]
    fm.reg_prod(R, "bench-throw", thr, 65, "house-20 1.2 (waffle blanket 200 x 230 beige)")
    bas = [fm.cyl("mb1_basket", BASKET["c"], BASKET["r"], 0.0, BASKET["h"], M("jute", "#B89A74", 0.9), 40)]
    fm.reg_prod(R, "bench-basket", bas, 66, "house-20 1.2 (two-tone rope basket 30)")
    (rx0, rx1), (ry0, ry1) = RUG["x"], RUG["y"]
    rug = [fm.bx("mb1_rug", rx0, rx1, ry0, ry1, 0.0, RUG["h"], M("oat", "#D9CDB8", 0.98))]
    fm.reg_prod(R, "rug", rug, 67, "13.8 / house-20 1.2 (braided wool 200 x 300)")
    return notes


def project(x, y, z, cam=CAM_MB1):
    """canvas pixels for a world point (MB1, tilt 0): F 1710 px, CX 1360, the horizon at 765 - (0.5 - v0) * 9/16 * 2565"""
    th = math.radians(cam["yaw"])
    fwd = (-math.sin(th), -math.cos(th))
    right = (math.cos(th), -math.sin(th))
    dx, dy = x - cam["loc"][0], y - cam["loc"][1]
    d = dx * fwd[0] + dy * fwd[1]
    xr = dx * right[0] + dy * right[1]
    hz = 765.0 + (cam["v0"] - 0.5) * 9 / 16 * 2565.0
    return 1360.0 + 1710.0 * xr / d, hz - 1710.0 * (z - cam["loc"][2]) / d


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="MB1-plate,MB1")
    ap.add_argument("--res", type=int, default=fm.CANVAS[0])
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=1.0)
    ap.add_argument("--master-window", type=float, default=fm.LIGHT["window"])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--post-from", default=os.path.join(HERE, "framing", "wm-master-2026-11-17", "selfcheck.json"))
    a, _ = ap.parse_known_args(argv)
    out = a.out
    os.makedirs(out, exist_ok=True)
    for d in ("exr", "npz", "raw"):
        os.makedirs(os.path.join(fm.SCR, d), exist_ok=True)
    raw = os.path.join(fm.SCR, "raw")
    r3.set_out(raw)
    frames = [f for f in a.frames.split(",") if f]
    t0 = time.time()
    fm.IDS.update(MB1_IDS)
    fm.PAL.update(MB1_PAL)
    fm.PRODUCT_IDS.update(set(range(56, 68)))
    fm.FIXED_IDS.update({28, 29, 30})
    r2.WARM = r3.WARM_R3
    cams, plan_doc = r3.cameras_1_1()
    for fid in FRAMES_MB1:
        r3.FRAMES[fid] = r3.FRAMES["MB0"]
        r3.HERO_WALL_PT[fid] = r3.HERO_WALL_PT["MB0"]
        cams[fid] = dict(cams["MB0"], id=fid, loc=list(CAM_MB1["loc"]), yaw=CAM_MB1["yaw"], u0=CAM_MB1["u0"], v0=CAM_MB1["v0"],
                         status="MB1 (render-agent clay; [MB-17] proposed: house-20 1.2, the motion check 5, the manager's ruling)")
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
        if ob.type == "LIGHT" and ob.name == "winlight_W-master":
            ob.data.energy *= a.master_window
    notes["wm_master"] = fm.wm_master(R)
    fixed = fm.wm_fixed() + mb1_fixed()
    notes["wm_master"] += fm.wm_products(R)
    notes["mb1"] = mb1_products(R)
    bpy.context.view_layer.update()
    rep = dict(stage="warm-modern master clay, MB1 (render-agent, 2026-11-19; briefs/wm-master-mb1-render-2026-11-19.md)",
               date=time.strftime("%Y-%m-%d"), plan_version=plan0["version"], camera=cams["MB1"],
               canvas=dict(px=list(fm.CANVAS), frame_box=[round(c, 2) for c in fm.FRAME_BOX], K=fm.K,
                           note="u / v in this file are FRAME fractions (the 16:9 frame), pixels are CANVAS pixels"),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU, OIDN, AgX MHC; post: MB0's recorded post",
               build_notes=notes, ids=fm.IDS, frames={})
    tmp = tempfile.mkdtemp(prefix="wm-master-mb1-")
    r4.OS_STATE["on"] = True
    for fid in frames:
        F = FRAMES_MB1[fid]
        r3.set_hidden(fixed, not F["fixed"])
        fplan = dict(placeholders=F["placeholders"], lamps=F["lamps"], also_visible=F.get("also", []), notes=f"warm-modern {fid}")
        Rr = r3.run_frame(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, {}, cfg)
        depth, idx, normal = fm.CAPTURE["last"]
        ids, counts, pid = fm.save_passes(fid, out, depth, idx, normal)
        Rr["id_px"] = counts
        Rr["pidx_to_id"] = pid
        Rr["boxes_frame"] = {fm.IDS[g]: fm.bbox_f(ids, {g}) for g in sorted(fm.PRODUCT_IDS | fm.FIXED_IDS | {13, 14}) if fm.bbox_f(ids, {g})}
        shutil.copy(os.path.join(raw, f"{fid}.png"), os.path.join(fm.SCR, "raw", f"{fid}-untoned.png"))
        rep["frames"][fid] = Rr
        json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
        print("frame", fid, Rr.get("runtime_s"), "s", flush=True)
    cam = S["cam"]
    post = json.load(open(a.post_from))["post"]
    rep["post"] = fm.tone_frames(frames, cam, frames[0], out, fixed=post)
    rep["projection_check"] = {k: [round(c, 1) for c in project(*p)] for k, p in (("bed foot right corner (0.20, 19.66, 0.28)", (0.20, 19.66, 0.28)),
                                                                                  ("shelf right front top (0.20, 17.90, 1.50)", (0.20, 17.90, 1.50)),
                                                                                  ("bench front left top (-1.35, 20.16, 0.45)", (-1.35, 20.16, 0.45)))}
    rep["build_s"] = round(time.time() - t0)
    json.dump(rep, open(os.path.join(out, "selfcheck.json"), "w"), indent=1, ensure_ascii=False, default=str)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main(_ARGV)
