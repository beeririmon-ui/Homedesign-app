#!/usr/bin/env python3
"""clay555.py: the M0-W clay at v0 0.555 for the FB13 stage-A concepts (scratch only; clay_m0w.py is imported, not edited).
  python3 clay555.py explore          # materials by pass index + 680-px previews of B (sun) and A (no sun)
  python3 clay555.py final            # idx/depth at 2048, B and A beauties at calibrated exposures
"""
import json
import os
import sys

sys.dont_write_bytecode = True
SP = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13-concepts-1126"
os.environ["FB13_SCRATCH"] = os.path.join(SP, "clay")
FB13 = "/home/user/homedesign-app/assets/renders/living-room/warm-modern/fb13-2026-11-25"
sys.path.insert(0, FB13)
MODE = sys.argv[1] if len(sys.argv) > 1 else "explore"
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
    fa.res = 2048
    S, R, cfg, notes = C.FF.build(fa)
    sol = C.solve_olive()
    planter_c = tuple(sol["crown_centre"][:2])
    ch = C.sofa_m0w() + C.olia() + C.products(planter_c, C.BASKET_CANDIDATES[0]) + C.lamps()
    bc = REC["basket_in_clay"]
    C.OBJS["basket"][0].location = (bc[0], bc[1], C.OBJS["basket"][0].location.z)
    sun = C.FF.LIGHTS["sun"]
    sun.data.energy = C.SUN["strength"]
    sun.rotation_quaternion = (-C.tool_sun_vector(C.SUN["az"], C.SUN["alt"])).to_track_quat("-Z", "Y")
    C.FF.move_olive((-5.4, -1.6))
    bpy.context.view_layer.update()
    return S["cam"], fa, sun


def materials_report():
    by = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        for sl in ob.material_slots:
            m = sl.material
            if m is None:
                continue
            col = None
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == "BSDF_PRINCIPLED":
                        col = [round(v, 3) for v in n.inputs["Base Color"].default_value[:3]]
            by.setdefault(ob.pass_index, {}).setdefault(m.name, [col, 0])[1] += 1
    for k in sorted(by):
        print("PIDX", k, by[k], flush=True)


def Lstar(png):
    return cv2.cvtColor(np.asarray(Image.open(png).convert("RGB")).astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[..., 0]


def shifted(path, W, H, scale):
    """an existing v0 0.52 canvas map, resized to (W, H) and moved down by the v0 change (0.035 of the frame height)"""
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
    cam, fa, sun = build()
    tmp = os.path.join(C.SCR, "t")
    os.makedirs(tmp, exist_ok=True)
    if MODE == "explore":
        materials_report()
    # the materials the photograph has (the clay's shell is neutral): bone plaster, smoked-oak floor, bronze-espresso glazing frame,
    # the walnut-and-bone armchair, set B's colours on the cushion proxies; the green cone of the branch filler is hidden
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
    gres = 1360 if MODE == "explore" else 2048
    cvg = C.set_view(cam, gres)
    depth, idx, normal = C.D.geometry_pass(tmp, cvg["W"], cvg["H"])
    np.savez_compressed(os.path.join(OUT, "passes555.npz"), depth=depth.astype(np.float32), idx=idx.astype(np.int32))
    json.dump(dict(cv=cvg, cam=C.CAM, frame_box=list(C.FRAME_BOX), canvas=list(C.CANVAS)), open(os.path.join(OUT, "view555.json"), "w"))
    C.hide_products(True)
    depth_p, idx_p, _ = C.D.geometry_pass(tmp, cvg["W"], cvg["H"])
    np.savez_compressed(os.path.join(OUT, "passes555-plate.npz"), depth=depth_p.astype(np.float32), idx=idx_p.astype(np.int32))
    C.hide_products(False)
    wall5 = cv2.resize((idx == 5).astype(np.uint8), (680, int(round(680 * C.CANVAS[1] / C.CANVAS[0]))), interpolation=cv2.INTER_NEAREST).astype(bool)

    def mask_fn(W, H):
        s = shifted(os.path.join(FB13, "m0w-sun.png"), W, H, 255.0)
        q = shifted(os.path.join(FB13, "m0w-light-accent-sconces.png"), W, H, 65535.0)
        f = shifted(os.path.join(FB13, "m0w-light-floor-lamp.png"), W, H, 65535.0)
        w = wall5 if wall5.shape == (H, W) else cv2.resize(wall5.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
        return w & (s < 0.02) & (q < 0.15) & (f < 0.15), w & (s > 0.5)

    C.set_lamps(set(C.LAMPS))
    sun_k = float(os.environ.get("SUN_K", "2.0"))
    tgtB, tgtA = float(os.environ.get("TGT_B", "74")), float(os.environ.get("TGT_A", "78"))
    # B: the last winter sun (the README: the sun about 2 x against the sky for 92-95 in the patch over 70-78 in the shade)
    sun.hide_render = False
    sun.data.energy = C.SUN["strength"] * sun_k
    bB = calibrate(cam, tmp, tgtB, mask_fn)
    res = 680 if MODE == "explore" else 2048
    smp = 8 if MODE == "explore" else 32
    cv_ = C.set_view(cam, res)
    C.FF.render_beauty(os.path.join(OUT, f"clay555-B-{res}.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], smp, 0.30, bB["exposure"])
    if MODE != "explore":
        C.hide_products(True)
        C.FF.render_beauty(os.path.join(OUT, f"clay555-B-plate-{res}.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], smp, 0.30, bB["exposure"])
        C.hide_products(False)
        C.set_lamps(set(C.LAMPS))
    # A: today's light, no direct sun, every lamp on
    sun.hide_render = True
    bA = calibrate(cam, tmp, tgtA, mask_fn)
    cv_ = C.set_view(cam, res)
    C.FF.render_beauty(os.path.join(OUT, f"clay555-A-{res}.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], smp, 0.30, bA["exposure"])
    if MODE != "explore":
        C.hide_products(True)
        C.FF.render_beauty(os.path.join(OUT, f"clay555-A-plate-{res}.png"), os.path.join(tmp, "b"), cv_["W"], cv_["H"], smp, 0.30, bA["exposure"])
        C.hide_products(False)
        C.set_lamps(set(C.LAMPS))
    sun.hide_render = False
    json.dump(dict(B=bB, A=bA, sun_k=sun_k, targets=dict(B=tgtB, A=tgtA), res=res, samples=smp, v0=C.CAM["v0"]),
              open(os.path.join(OUT, f"clay555-{MODE}.json"), "w"), indent=1)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(C.W4.r4.EXR_DIR, ignore_errors=True)
    print("DONE", MODE, bB, bA, flush=True)


main()
