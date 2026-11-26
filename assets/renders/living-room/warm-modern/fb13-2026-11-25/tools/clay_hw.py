#!/usr/bin/env python3
"""clay_hw.py: the M0-W clay at v0 0.555 for FB13 stage A steps 2-6 (the plate P-W and the hero H-W). Scratch only: clay_m0w.py is
imported, not edited. Light B only (the last winter sun). The magazine holder is moved (HOLDER) so that it reads in the frame.
  python3 clay_hw.py [res] [samples]
writes into OUT: passes-full.npz, passes-plate.npz, view.json, clay-B-full-on.png, clay-B-full-off.png, clay-B-plate.png, clay-hw.json
"""
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True
SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13-hero"
os.environ["FB13_SCRATCH"] = os.path.join(SP, "clay")
FB13 = "/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25"
sys.path.insert(0, FB13)
RES = int(sys.argv[1]) if len(sys.argv) > 1 else 2720
SMP = int(sys.argv[2]) if len(sys.argv) > 2 else 32
sys.argv = [sys.argv[0]]

import clay_m0w as C  # noqa: E402
import bpy  # noqa: E402
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

C.CAM["v0"] = 0.555
OUT = os.path.join(SP, "out")
os.makedirs(OUT, exist_ok=True)
REC = json.load(open(os.path.join(FB13, "clay-m0w.json")))
HOLDER = (-0.68, 2.25)                                   # the clay had (-0.47, 2.57): 25 % visible at v0 0.555
HOLDER_WAS = (-0.47, 2.57)


def hex_lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)


def set_col(m, hexcol):
    if m is None or not m.use_nodes:
        return False
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Base Color"].default_value = hex_lin(hexcol)
            return True
    return False


def build():
    C.W4.r4.EXR_DIR = os.path.join(C.SCR, "exr")
    os.makedirs(C.SCR, exist_ok=True)
    fa = C.FF.args([])
    fa.res = RES
    S, R, cfg, notes = C.FF.build(fa)
    sol = C.solve_olive()
    planter_c = tuple(sol["crown_centre"][:2])
    C.sofa_m0w() + C.olia() + C.products(planter_c, C.BASKET_CANDIDATES[0]) + C.lamps()
    bc = REC["basket_in_clay"]
    C.OBJS["basket"][0].location = (bc[0], bc[1], C.OBJS["basket"][0].location.z)
    for ob in C.OBJS["magazine-holder"]:
        ob.location.x += HOLDER[0] - HOLDER_WAS[0]
        ob.location.y += HOLDER[1] - HOLDER_WAS[1]
    sun = C.FF.LIGHTS["sun"]
    sun.data.energy = C.SUN["strength"]
    sun.rotation_quaternion = (-C.tool_sun_vector(C.SUN["az"], C.SUN["alt"])).to_track_quat("-Z", "Y")
    C.FF.move_olive((-5.4, -1.6))
    bpy.context.view_layer.update()
    return S["cam"], fa, sun, planter_c, bc


def Lstar(png):
    return cv2.cvtColor(np.asarray(Image.open(png).convert("RGB")).astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[..., 0]


def shifted(path, W, H, scale):
    a = np.asarray(Image.open(path)).astype(np.float32) / scale
    a = cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA)
    dy = 0.035 * (C.FRAME_BOX[3] - C.FRAME_BOX[1]) * H / C.CANVAS[1]
    M = np.float32([[1, 0, 0], [0, 1, dy]])
    return cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def calibrate(cam, tmp, target, mask_fn, lo=-3.0, hi=1.0, n=6):
    cvs = C.set_view(cam, 680)
    W, H = cvs["W"], cvs["H"]
    m, sunny = mask_fn(W, H)
    tries = []
    for _ in range(n):
        e = (lo + hi) / 2
        png = os.path.join(tmp, "c.png")
        C.FF.render_beauty(png, os.path.join(tmp, "b"), W, H, 8, 0.30, e)
        L = Lstar(png)
        v = float(np.median(L[m]))
        tries.append(dict(exposure=round(e, 3), shaded=round(v, 2), sunny=round(float(np.median(L[sunny])), 2) if sunny.any() else None))
        if v > target:
            hi = e
        else:
            lo = e
    best = min(tries, key=lambda t: abs(t["shaded"] - target))
    print("CAL", target, tries, "->", best, flush=True)
    return best


def main():
    cam, fa, sun, planter_c, bc = build()
    tmp = os.path.join(C.SCR, "t")
    os.makedirs(tmp, exist_ok=True)
    for name, hx in {"wall": "#ECE5DA", "ceiling": "#EFE9DF", "plank0": "#927558", "plank1": "#8B6F55", "plank2": "#846A51", "plank3": "#7E644C",
                     "floor_gap": "#4E3D2F", "m0w_rug_wool": "#DDD3C1", "m0w_cement_beige": "#C4B6A1", "m0w_jute": "#C2A06E",
                     "m0w_gunmetal": "#2A2725", "m0w_throw_pecan": "#7A543A"}.items():
        print("RECOLOUR", name, hx, set_col(bpy.data.materials.get(name), hx), flush=True)
    bronze, walnut, bone = C.mat("bronze_frame", "#3A322C", 0.6), C.mat("walnut", "#6B4A33", 0.85), C.mat("bone_boucle", "#ECE5DA", 0.95)
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        if ob.pass_index in (3, 4):
            for sl in ob.material_slots:
                if sl.material is None:
                    continue
                if ob.pass_index == 4 and sl.material.name == "moulding":
                    sl.material = bronze
                elif ob.pass_index == 3 and sl.material.name == "wood":
                    sl.material = walnut
                elif ob.pass_index == 3 and sl.material.name == "chair":
                    sl.material = bone
    for key, hx in (("cushion-left", "#B27F52"), ("cushion-lumbar", "#D8CCB9"), ("cushion-right", "#A39686")):
        m = C.mat("setB_" + key, hx, 0.95)
        for ob in C.OBJS[key]:
            ob.data.materials.clear()
            ob.data.materials.append(m)
    for ob in C.OBJS.pop("branch (filler)", []):
        ob.hide_render = True
    bpy.context.view_layer.update()
    cvg = C.set_view(cam, RES)
    depth, idx, normal = C.D.geometry_pass(tmp, cvg["W"], cvg["H"])
    np.savez_compressed(os.path.join(OUT, "passes-full.npz"), depth=depth.astype(np.float32), idx=idx.astype(np.int32))
    json.dump(dict(cv=cvg, cam=C.CAM, frame_box=list(C.FRAME_BOX), canvas=list(C.CANVAS), holder=HOLDER, holder_was=HOLDER_WAS,
                   planter=list(planter_c), basket=list(bc)), open(os.path.join(OUT, "view.json"), "w"))
    C.hide_products(True)
    depth_p, idx_p, _ = C.D.geometry_pass(tmp, cvg["W"], cvg["H"])
    np.savez_compressed(os.path.join(OUT, "passes-plate.npz"), depth=depth_p.astype(np.float32), idx=idx_p.astype(np.int32))
    C.hide_products(False)
    wall5 = cv2.resize((idx == 5).astype(np.uint8), (680, int(round(680 * C.CANVAS[1] / C.CANVAS[0]))), interpolation=cv2.INTER_NEAREST).astype(bool)

    def mask_fn(W, H):
        s = shifted(os.path.join(FB13, "m0w-sun.png"), W, H, 255.0)
        q = shifted(os.path.join(FB13, "m0w-light-accent-sconces.png"), W, H, 65535.0)
        f = shifted(os.path.join(FB13, "m0w-light-floor-lamp.png"), W, H, 65535.0)
        w = wall5 if wall5.shape == (H, W) else cv2.resize(wall5.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
        return w & (s < 0.02) & (q < 0.15) & (f < 0.15), w & (s > 0.5)

    C.set_lamps(set(C.LAMPS))
    # the owner's note on concept B (2026-11-26, "a little too dramatic"): the sun about a third down. Sun over sky 1.0 (D0's own 8,
    # not 2 x), a wider disc for softer shadow edges, a whiter gold (4300 K, not 4000), the shade at L 77
    sun_k = float(os.environ.get("SUN_K", "1.0"))
    sun.hide_render = False
    sun.data.energy = C.SUN["strength"] * sun_k
    sun.data.angle = __import__("math").radians(float(os.environ.get("SUN_ANGLE", "3.0")))
    for n in sun.data.node_tree.nodes:
        if n.type == "BLACKBODY":
            n.inputs["Temperature"].default_value = float(os.environ.get("SUN_KELVIN", "4300"))
            print("SUN KELVIN", n.inputs["Temperature"].default_value, flush=True)
    bB = calibrate(cam, tmp, float(os.environ.get("TGT_B", "77")), mask_fn)
    cv_ = C.set_view(cam, RES)
    e = bB["exposure"]
    C.FF.render_beauty(os.path.join(OUT, "clay-B-full-on.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], SMP, 0.30, e)
    print("RENDERED full-on", flush=True)
    C.set_lamps(set())
    C.FF.render_beauty(os.path.join(OUT, "clay-B-full-off.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], SMP, 0.30, e)
    print("RENDERED full-off", flush=True)
    C.hide_products(True)
    C.FF.render_beauty(os.path.join(OUT, "clay-B-plate.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], SMP, 0.30, e)
    print("RENDERED plate", flush=True)
    C.hide_products(False)
    C.set_lamps(set(C.LAMPS))
    json.dump(dict(B=bB, sun_k=sun_k, sun_angle_deg=float(os.environ.get("SUN_ANGLE", "3.0")), sun_kelvin=float(os.environ.get("SUN_KELVIN", "4300")), res=RES, samples=SMP, v0=C.CAM["v0"], holder=HOLDER, holder_was=HOLDER_WAS, planter=list(planter_c),
                   basket=list(bc), prod_idx=C.PROD_IDX, filler_idx=C.FILLER_IDX), open(os.path.join(OUT, "clay-hw.json"), "w"), indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(C.W4.r4.EXR_DIR, ignore_errors=True)
    print("DONE", bB, flush=True)


main()
