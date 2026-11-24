#!/usr/bin/env python3
"""
framing_wm_dining_d2.py: the warm-modern kitchen-dining clay for 10.9 "D2 takes the stage" (render-agent, 2026-11-24). 0 var2 tokens.
Spec: docs/proposals/wm-kitchen-dining-render-2026-11-19.md 10.9 (over 10.1-10.8), with the manager's rulings of 2026-11-24 (only cards
that passed a photo check; the serving boards are the existing walnut pair card; the bench pad stays khaki; no AE grinders; the AE silk
dome is not rendered (no CE); V2 leaves the wheel).

It is the stage-one clay (../wm-dining-2026-11-20/framing_wm_dining.py, imported, nothing changed there) with:
  [KD-15] D2 at yaw -86 (was -91), same point PD, lens, u0, v0 (a pure rotation about PD);
  [KD-16] the coffee niche Y 4.30-5.20 x Z 0.90-2.05 (was 4.55-5.20 x 0.90-1.60), a walnut shelf with its top at Z 1.50 and an LED under
          it (the top LED stays);
  [KD-17] the products: framed-art 64 x 49 (Y 0.80-1.44, Z 1.59-2.08) with a 50 x 40 canvas (the 40x50 SKU of design 05,
          12000038963447944); the moon jar at Y 1.735; the tableware set in the niche's upper level (the 26.7 and 20.3 plates standing
          on their rims at the back, the bowls in front); the canisters where they were (Y 4.70-5.03, niche floor); two caramel tea towels
          on the oven bar (the 2 pc SKU 12000059652536006: one folded lengthwise, one at full width); new: counter-vessel (the white
          textured jar, Medium Bottle, CJYD219407502BY, 16 x 28) with dried beech branches to Z 2.00 leaning right (id 78, filler 80),
          and serving-boards (the walnut pair: B paddle 39 x 18.5 and F rounded 34 x 19.5, CJJJCFCJ01542) leaning on the splash behind
          the 280363 board (id 79).
  The vessel is at (6.95, 3.88), not 10.9.2's (7.00, 4.00): there it stands in the paper-towel holder Style C at (7.12, 4.05)
  (their bases overlap by about 1.5 cm, and at -86 both project to u 0.60); 0.13 m toward the front-left it stands clear, with the
  holder behind it to the right. Reported for the designer.
Frames: D2-plate and D2 only (D1 is not re-rendered: what changes there comes by projection from D2 and is in front of the wall).

  cd assets/blockout/house && python3 -B framing/wm-dining-2026-11-24/framing_wm_dining_d2.py --frames D2-plate,D2
"""
import importlib.util
import inspect
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(os.path.dirname(HERE), "wm-dining-2026-11-20", "framing_wm_dining.py")
spec = importlib.util.spec_from_file_location("framing_wm_dining", OLD)
fw = importlib.util.module_from_spec(spec)
sys.modules["framing_wm_dining"] = fw
spec.loader.exec_module(fw)

r2, r3, KD = fw.r2, fw.r3, fw.KD

# ---- [KD-15] the camera
fw.CAM["yaw"]["D2"] = -86.0
_cams = r3.cameras_1_1


def cameras_10_9():
    C, plan = _cams()
    C["D2"] = dict(C["D2"], yaw=-86.0, status="10.9 [KD-15]: D2 at yaw -86 (was -91), a pure rotation about PD")
    return C, plan


r3.cameras_1_1 = cameras_10_9

# ---- [KD-16] the niche
fw.TALL.update(niche_y=(4.30, 5.20), niche_z=(0.90, 2.05))
NICHE_SHELF = dict(z=(1.47, 1.50), back=fw.TALL["niche_back"])
_kitchen = fw.wm_kitchen


def wm_kitchen_10_9():
    notes = _kitchen()
    xf = fw.RUN["front"]
    ny0, ny1 = fw.TALL["niche_y"]
    lin = 0.012
    wal = fw.mat("walnut", "walnut", 0.7)
    shelf = fw.bx("niche_shelf", xf + 0.01, NICHE_SHELF["back"], ny0 + lin, ny1 - lin, NICHE_SHELF["z"][0], NICHE_SHELF["z"][1], wal, 0.002)
    led = fw.bx("niche_shelf_led", xf + 0.03, xf + 0.06, ny0 + 0.02, ny1 - 0.02, NICHE_SHELF["z"][0] - 0.0035, NICHE_SHELF["z"][0] - 0.0005,
                fw.mat("led", "candle", 0.5))
    fw.reg_arch("kd_wm niche shelf (walnut)", [shelf], 42, kind="furniture")
    fw.reg_arch("kd_wm niche shelf LED", [led], 39, kind="architecture")
    notes.append("10.9 [KD-16]: niche Y 4.30-5.20 x Z 0.90-2.05, a walnut shelf Z 1.47-1.50 with an LED profile under it")
    return notes


fw.wm_kitchen = wm_kitchen_10_9

# ---- [KD-17] the products
fw.IDS.update({78: "counter-vessel (product)", 79: "serving-boards (product)", 80: "beech branches (filler)"})
for k in (78, 79, 80):
    fw.PAL[k] = tuple(int(v) for v in fw.rng_pal.integers(40, 255, 3))
fw.PRODUCT_IDS |= {78, 79, 80}
fw.FILLER_IDS |= {80}
fw.PRODUCTS += ["counter-vessel", "serving-boards"]
fw.FILLERS += [f"{KD}/counter-vessel-filler"]
fw.HEX.update(vessel="#E8E3DA", beech="#8A5A35", serv="#3E2A1E")

src = inspect.getsource(fw.wm_products)
REPL = [
    # framed-art 64 x 49 with a 50 x 40 canvas, centred on Y 1.12 as before
    ('''    fr_ = r2.obox("kd_wm_art_frame", (7.195, 1.12, zs), (7.195 + lean, 1.12, zs + 0.34), (0, 1, 0), 0.44, 0.022, C["frame"])
    cv_ = r2.obox("kd_wm_art_canvas", (7.180, 1.12, zs + 0.02), (7.180 + lean * 0.30 / 0.34, 1.12, zs + 0.32), (0, 1, 0), 0.40, 0.008, C["canvas"])
    reg_prod(R, "framed-art", [fr_, cv_], 67, "10.7: 386242-05 landscape (12000038963447935), walnut float frame 44 x 34, Y 0.90-1.34, on the left shelf")''',
     '''    lean = 0.043
    fr_ = r2.obox("kd_wm_art_frame", (7.190, 1.12, zs), (7.190 + lean, 1.12, zs + 0.49), (0, 1, 0), 0.64, 0.022, C["frame"])
    cv_ = r2.obox("kd_wm_art_canvas", (7.176, 1.12, zs + 0.045), (7.176 + lean * 0.445 / 0.49, 1.12, zs + 0.445), (0, 1, 0), 0.50, 0.008, C["canvas"])
    reg_prod(R, "framed-art", [fr_, cv_], 67, "10.9: 386242-05, the 40x50 SKU 12000038963447944 landscape, walnut float frame 64 x 49, Y 0.80-1.44, Z 1.59-2.08")'''),
    ("    mj = (7.12, 1.55)", "    mj = (7.12, 1.735)"),
    ('''    reg_prod(R, "open-shelf-ceramics", jar, 69, "10.1 V1 moon jar StyleG (black) CJJT276473907GT, 23 x 25 at (7.11, 1.55)")''',
     '''    reg_prod(R, "open-shelf-ceramics", jar, 69, "10.9: moon jar StyleG (black) CJJT276473907GT, 23 x 25, moved to (7.12, 1.735)")'''),
    # the tableware set in the niche's upper level: two plates standing on their rims at the back, the bowls in front
    ('''    tw = (7.12, 3.30)
    plates = [cyl("plates_big", tw, 0.1335, zs, zs + 0.03, C["plates"], 48), cyl("plates_small", tw, 0.1015, zs + 0.03, zs + 0.05, C["plates"], 48),
              cone("plates_bowls", tw, 0.035, 0.06, zs + 0.05, zs + 0.11, C["plates"], 40)]
    reg_prod(R, "tableware-set", plates, 65, "10.1 kiln corrugated set 12000057617920292, plates 26.7 / 20.3 + bowls 12 stacked at (7.12, 3.30)")''',
     '''    zn2 = 1.50
    plates = [vdisc("plates_big_std", (6.955, 4.66, zn2 + 0.1335 + 0.004), 0.1335, 0.022, C["plates"]),
              vdisc("plates_small_std", (6.935, 4.90, zn2 + 0.1015 + 0.004), 0.1015, 0.022, C["plates"]),
              cone("plates_bowl_a", (6.78, 4.77), 0.035, 0.06, zn2, zn2 + 0.055, C["plates"], 40),
              cone("plates_bowl_b", (6.78, 4.77), 0.035, 0.06, zn2 + 0.03, zn2 + 0.085, C["plates"], 40)]
    reg_prod(R, "tableware-set", plates, 65, "10.9: kiln corrugated set 12000057617920292 in the niche's upper level: plates 26.7 and 20.3 standing on their rims at the back (Y 4.66 / 4.90), two bowls 12 in front (6.78, 4.77)")'''),
    # two caramel towels on the oven bar (the 2 pc SKU)
    ('''    tt = [bx("towel_front", xb - 0.012, xb - 0.004, 5.49, 5.68, zb - 0.27, zb + 0.012, C["towel"], 0.003),
          bx("towel_back", xb + 0.004, RUN["front"] - 0.013, 5.49, 5.68, zb - 0.25, zb + 0.012, C["towel"], 0.003)]
    reg_prod(R, "tea-towel", tt, 77, "10.1 V1 caramel 12000059652536005, 38 x 55 folded lengthwise over the oven bar, Y 5.49-5.68")''',
     '''    tt = [bx("towel_full_front", xb - 0.012, xb - 0.004, 5.36, 5.74, zb - 0.27, zb + 0.012, C["towel"], 0.003),
          bx("towel_full_back", xb + 0.004, RUN["front"] - 0.013, 5.36, 5.74, zb - 0.25, zb + 0.012, C["towel"], 0.003),
          bx("towel_fold_front", xb - 0.020, xb - 0.013, 5.64, 5.84, zb - 0.28, zb + 0.016, C["towel"], 0.003)]
    reg_prod(R, "tea-towel", tt, 77, "10.9: caramel 2 pc 12000059652536006 on the oven bar: one at full width (Y 5.36-5.74), one folded lengthwise in front (Y 5.64-5.84)")'''),
    # new: the vessel with branches, and the serving boards
    ('''    notes.append("products: the 21 defaults of 10.1''',
     '''    vs = (6.95, 3.88)
    ves = [cone("vessel_lo", vs, 0.065, 0.08, zw, zw + 0.10, C["vessel"], 40), cone("vessel_hi", vs, 0.08, 0.05, zw + 0.10, zw + 0.27, C["vessel"], 40),
           cyl("vessel_mouth", vs, 0.05, zw + 0.27, zw + 0.28, C["vessel"], 32)]
    reg_prod(R, "counter-vessel", ves, 78, "10.9 counter-vessel: white textured jar Medium Bottle CJYD219407502BY, 16 x 28, at (6.95, 3.88)")
    br = [r3.ell("kd_wm_beech", (6.97, 4.02), 0.13, zw + 0.25, 2.00, C["beech"])]
    reg_prod(R, "counter-vessel-filler", br, 80, "2-3 dried beech branches, copper leaves, top Z 2.00, leaning right toward the tall unit")
    zw_ = zw
    sb = [r2.obox("kd_wm_serv_F", (7.228, 1.93, zw_), (7.243, 1.93, zw_ + 0.34), (0, 1, 0), 0.195, 0.018, C["serv"]),
          r2.obox("kd_wm_serv_B", (7.226, 2.07, zw_), (7.243, 2.07, zw_ + 0.39), (0, 1, 0), 0.185, 0.018, C["serv"])]
    reg_prod(R, "serving-boards", sb, 79, "10.9 serving-boards: the walnut pair CJJJCFCJ01542, F rounded 34 x 19.5 at Y 1.93 and B paddle 39 x 18.5 at Y 2.07, leaning on the splash behind the 280363 board")
    notes.append("10.9: framed-art 64 x 49, the jar at 1.735, the tableware set in the niche, two towels, the counter-vessel with beech, the serving boards")
    notes.append("products: the 21 defaults of 10.1'''),
]
for a, b in REPL:
    assert a in src, a[:80]
    src = src.replace(a, b)
_c = '''("ptowel", 0.75), ("paper", 0.95), ("canister", 0.85), ("lid", 0.8), ("towel", 0.95))}'''
assert _c in src
src = src.replace(_c,
                  '''("ptowel", 0.75), ("paper", 0.95), ("canister", 0.85), ("lid", 0.8), ("towel", 0.95),
                                              ("vessel", 0.95), ("beech", 0.9), ("serv", 0.7))}''')


def vdisc(n, c, r, t, m, seg=48):
    """a plate standing on its rim, facing the camera side (-X): a disc in the YZ plane, t thick along X"""
    import math as _m
    x0, y0, z0 = c
    vs = []
    for x in (x0 - t / 2, x0 + t / 2):
        for i in range(seg):
            a = 2 * _m.pi * i / seg
            vs.append((x, y0 + r * _m.cos(a), z0 + r * _m.sin(a)))
    faces = [list(range(seg)), list(range(2 * seg - 1, seg - 1, -1))]
    faces += [[i, (i + 1) % seg, seg + (i + 1) % seg, seg + i] for i in range(seg)]
    return fw.mesh_obj("kd_wm_" + n, vs, faces, m)


fw.vdisc = vdisc
exec(compile(src, OLD + " (10.9 products)", "exec"), fw.__dict__)

# the lock lines of the new niche
lsrc = inspect.getsource(fw.lock_target)
for a, b in (('"niche, left edge (Y 4.55)": ((xf, 4.55, 0.92), (xf, 4.55, 1.58))', '"niche, left edge (Y 4.30)": ((xf, 4.30, 0.92), (xf, 4.30, 2.03))'),
             ('"niche, right edge (Y 5.20)": ((xf, 5.20, 0.92), (xf, 5.20, 1.58))', '"niche, right edge (Y 5.20)": ((xf, 5.20, 0.92), (xf, 5.20, 2.03))'),
             ('"niche top edge (Z 1.60)": ((xf, 4.57, 1.60), (xf, 5.18, 1.60))', '"niche top edge (Z 2.05)": ((xf, 4.32, 2.05), (xf, 5.18, 2.05))')):
    assert a in lsrc, a
    lsrc = lsrc.replace(a, b)
exec(compile(lsrc, OLD + " (10.9 lock lines)", "exec"), fw.__dict__)
fw.PROJ_PTS.update({"counter-vessel": (6.95, 3.88, 1.04), "beech top": (6.97, 4.02, 2.00), "serving boards": (7.235, 2.00, 1.10),
                    "niche centre": (6.63, 4.75, 1.48), "framed-art centre": (7.20, 1.12, 1.835), "moon jar top": (7.12, 1.735, 1.84),
                    "tableware": (6.95, 4.78, 1.62)})

if __name__ == "__main__":
    argv = fw._ARGV
    out = HERE
    if "--out" not in argv:
        argv = argv + ["--out", out]
    if not os.path.exists(os.path.join(out, "post.json")):        # the stage-one tone (one exposure and balance for the room)
        shutil.copy(os.path.join(os.path.dirname(OLD), "post.json"), os.path.join(out, "post.json"))
    fw.SCR = fw.SCR.rstrip("/") + "-10.9"
    fw.r4.EXR_DIR = os.path.join(fw.SCR, "exr")
    fw.main(argv)
