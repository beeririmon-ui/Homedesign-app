#!/usr/bin/env python3
"""
Framing clay, ROUND 5: the living room at the M0 1.2.1 camera (briefs/render-m0-new-camera-2026-11-03.md task 2; render-agent,
2026-11-03). 0 var2 tokens. Round 4 (framing_r4.py, framing/round4/) is read only: this file imports framing_r4 and changes nothing
there; every output goes to framing/round5/ (FRAMING_R3_OUT is set before the round-4 import so framing_r3 never writes into round 3/4).

What round 5 changes against round 4 (the geometry; which placeholders a frame shows is framing/round5/plan.json):
  - the M0 camera comes from docs/house-plan.json 1.2.1 as framing_r3.cameras_1_1() reads it: (0.83, 4.64, 1.20), yaw 25, 24 mm,
    u0 0.47, v0 0.50 (user decision V7Q1 b); M0p and M0x at the same point (plan.json poses, yaw 0 / -35, same shift);
  - the pendant proxy (40 x 28 ribbed pumpkin, m0-v7 c) rebuilt with the shade bottom at 1.90 (was 2.20; user decision V7Q7 b,
    Bible 1.8.1 pendant), cord to the 3.00 hang point (0.20, 1.72, 3.00); its area light follows (energy scaled by the square of the
    distance to the table so the pool stays the same);
  - a pouf proxy at (1.18, 2.08), d 45 (the small end of the 45-48 envelope: it is the diameter the designer limited for the right
    margin), h 36 (user decision V7Q8 b; data/slots/living-room.json 1.5), shown only on the measurement clay M0-pouf;
  - the floor-lamp v4 proxies moved 0.08 to (1.52, 0.20) (slots 1.5), shown only on M0-pouf (TR3: no floor lamp in the test);
  - the rug proxy = the Bible plan-B / slots 1.5 envelope X -1.25..1.65, Y 0.72-3.12 (round 4 drew the 230 x 330 stand-in outside it);
  - the living fixed furniture (sofa, coffee table, armchair; pass indices 1-3 of the v4 build) reported as 'furniture' boxes in the
    selfcheck, so lock_v2 reads its fixed edges from this clay (v7_frames.M0_FURNITURE was the 1.1 camera);
  - the Bible 1.8 (BIB1 B1) measurement points added to the wall patches of every living frame: back wall by the corner
    (-1.75, 0, 1.60) [L 90-94] and the window wall (-2.30, 0.30, 1.60) [L 80-88], plus the corner ray and the pendant / pouf readings.
Everything else (round-4 light, +1.35 render exposure, EXR per frame, 3 % overscan for the pan participants, selfcheck shape) is
framing_r4 as it is; the post is tone_r5_fixed.py (the round-4 M0 group post applied as recorded, no re-solve).

  python3 framing_r5.py --frames M0,M0p,M0x --res 3840 --samples 16 --pose-samples 10 --exr <scratch>/r5-exr
  python3 framing_r5.py --frames M0-pouf --res 1920 --samples 8 --exr <scratch>/r5-exr        # measurement clay, 16:9
Outputs: framing/round5/M0.png (overscan canvas 4072x2290), poses/M0p.png, poses/M0x.png, poses/M0-pouf.png (1920x1080),
overlays/, selfcheck-render-A.json; EXRs in --exr.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT5 = os.path.join(HERE, "framing", "round5")
os.environ["FRAMING_R3_OUT"] = OUT5                 # framing_r3 (imported by framing_r4) writes nowhere else
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import framing_r4 as r4  # noqa: E402

r3, fr, r2, bh, M = r4.r3, r4.fr, r4.r2, r4.bh, r4.M
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
r4.EXR_DIR = os.path.join(SCRATCH, "r5-exr")
r4.OUT4 = OUT5                                      # the default --plan / --out of framing_r4.main (overridden on the command line anyway)
r4.GROUPS["A"] = r4.GROUPS["A"] + ["M0-pouf", "M0-pouf-b"]       # the measurement clay passes the --frames filter
PENDANT = dict(hang=(0.20, 1.72, 3.00), bottom=1.90, r=0.20, h=0.28)       # m0-v7 c: ribbed pumpkin 40 (wide, low), Bible envelope 40-50 x 22-32
POUF = dict(c=(1.18, 2.08), d=0.45, h=0.36)                                 # slots 1.5 / Bible 1.8.2: d 45-48, h 35-37
FLOOR_LAMP_DX = -0.08                                                       # (1.60, 0.20) -> (1.52, 0.20), slots 1.5
RUG = dict(x=(-1.25, 1.65), y=(0.72, 3.12))                                 # Bible plan B / slots 1.5 envelope
LIVING_FURNITURE = {1: "sofa 220x92x78 (fixed-product)", 2: "coffee table 140x70 h38 (fixed-product)", 3: "armchair 72x78 h70 (fixed-product)"}
LIVING_FRAMES = ("M0", "M0p", "M0x", "M0-pouf", "M0-pouf-b")


# ---------------------------------------------------------------------------------------------------------------
# geometry changes on top of framing_r4.v7_fixes
# ---------------------------------------------------------------------------------------------------------------
def v8_fixes(R):
    notes = []
    # pendant: shade bottom 1.90 (V7Q7 b)
    r3.kill_group(R, "living/pendant")
    z0, z1 = PENDANT["bottom"], PENDANT["bottom"] + PENDANT["h"]
    c = PENDANT["hang"][:2]
    pend = r3.ell("lv_pend_r5", c, PENDANT["r"], z0, z1, M["curtain"])
    cord = r3.cyl("lv_pcord_r5", c, 0.004, z1, PENDANT["hang"][2], M["holder"], 12)
    r3.reg(R, "living/pendant", [pend], "living",
           src=f"V7Q7 b (house plan 1.2.1, Bible 1.8.1): 40 x 28 pumpkin, shade bottom {z0}, top {z1:.2f}; the cord is living/pendant-cord")
    r3.reg(R, "living/pendant-cord", [cord], "living",
           src=f"the pendant cord {z1:.2f} -> hang point {PENDANT['hang']}, registered apart so the pendant box is the shade alone (Bible pendant rule 1)")
    L = r2.LAMPS.get("living/pendant")
    if L:
        L["glow"] = [(pend, r2.GLOW)]
        L["orig"] = {pend.name: pend.data.materials[0]}
    table_top = 0.38
    e_old, d_old, d_new = 30.0, 2.20 - table_top, z0 - table_top
    r3.lamp_lights_at("living/pendant", [r2.mk_light("lv_pend_L5", "AREA", (c[0], c[1], z0 - 0.005), round(e_old * (d_new / d_old) ** 2, 1), size=0.30)])
    r3.set_hidden([pend, cord], True)
    notes.append(f"living/pendant: shade bottom {z0} (was 2.20), area light {round(e_old * (d_new / d_old) ** 2, 1)} W at {z0 - 0.005:.3f} (pool kept)")
    # pouf (V7Q8 b): shown only where plan.json lists it (M0-pouf)
    r3.kill_group(R, "living/pouf")
    pouf = r3.cyl("lv_pouf_r5", POUF["c"], POUF["d"] / 2, 0.0, POUF["h"], M["textile"])
    r3.reg(R, "living/pouf", [pouf], "living", src=f"V7Q8 b (slots 1.5): centre {POUF['c']}, d {POUF['d']}, h {POUF['h']} (envelope d 45-48, h 35-37)")
    r3.set_hidden([pouf], True)
    notes.append(f"living/pouf: cylinder at {POUF['c']} d {POUF['d']} h {POUF['h']} (measurement clay only)")
    cb = (POUF["c"][0], round(POUF["c"][1] + 0.03, 2))
    poufb = r3.cyl("lv_pouf_r5b", cb, POUF["d"] / 2, 0.0, 0.35, M["textile"])
    r3.reg(R, "living/pouf-b", [poufb], "living", src=f"the designer's pre-authorised fix (house plan 6.1 / Bible pouf 1.8.2: Y +0.03 and h 35): centre {cb}, d {POUF['d']}, h 0.35; M0-pouf-b only")
    r3.set_hidden([poufb], True)
    notes.append(f"living/pouf-b: the pre-authorised fix, centre {cb} h 0.35 (measurement clay M0-pouf-b only)")
    # floor lamp: v4 proxies to (1.52, 0.20); still no light (round 4), shown only on M0-pouf
    n = r3.move(R, "living/floor-lamp", dx=FLOOR_LAMP_DX)
    notes.append(f"living/floor-lamp: {n} v4 proxy objects moved {FLOOR_LAMP_DX} in X to (1.52, 0.20) (slots 1.5); no light (TR3)")
    # rug: the envelope
    r3.kill_group(R, "living/rug")
    rug = r3.bx("lv_rug_r5", RUG["x"][0], RUG["x"][1], RUG["y"][0], RUG["y"][1], 0.0, 0.012, M["rug"])
    r3.reg(R, "living/rug", [rug], "living", src="Bible plan B / slots 1.5 envelope X -1.25..1.65, Y 0.72-3.12 (290 x 240; round 4: 230 x 330 outside it)")
    r3.set_hidden([rug], True)
    notes.append("living/rug: envelope X -1.25..1.65, Y 0.72-3.12")
    return notes


_v7 = r4.v7_fixes


def v7_plus_v8(R):
    return _v7(R) + v8_fixes(R)


r4.v7_fixes = v7_plus_v8


# ---------------------------------------------------------------------------------------------------------------
# the living fixed furniture as 'furniture' boxes (pass indices of the v4 build: sofa 1, coffee-table 2, armchair 3)
# ---------------------------------------------------------------------------------------------------------------
_names0 = r2.names_by_pidx


def names_by_pidx_r5(S):
    names = _names0(S)
    for pidx, nm in LIVING_FURNITURE.items():
        names.setdefault(pidx, (nm, "furniture"))
    return names


r2.names_by_pidx = names_by_pidx_r5


# ---------------------------------------------------------------------------------------------------------------
# wall patches: the Bible 1.8 measurement points for the living frames
# ---------------------------------------------------------------------------------------------------------------
_wp0 = r3.wall_patches


def wall_patches_r5(fid, cam, C, path):
    out = _wp0(fid, cam, C, path)
    if fid in LIVING_FRAMES:
        pts = {"bible18_back_wall_by_corner_L90_94": (-1.75, 0.0, 1.60), "bible18_window_wall_L80_88": (-2.30, 0.30, 1.60),
               "back_wall_behind_art_centre": (0.20, 0.0, 1.95), "back_wall_right_end_L82_86": (1.85, 0.0, 1.60),
               "corner_line_top": (-2.30, 0.0, 2.95)}
        for k, (x, y, z) in pts.items():
            u, v = fr.U(cam, x, y, z), fr.V(cam, x, y, z)
            if 0.02 < u < 0.98 and 0.02 < v < 0.98:
                out[k] = dict(r3.patch_L(path, u, v), xyz=[x, y, z])
            else:
                out[k] = dict(u=round(u, 3), v=round(v, 3), xyz=[x, y, z], note="outside the frame")
    return out


r3.wall_patches = wall_patches_r5


def main(argv):
    if "--plan" not in argv:
        argv = argv + ["--plan", os.path.join(OUT5, "plan.json")]
    if "--out" not in argv:
        argv = argv + ["--out", OUT5]
    if "--exr" not in argv:
        argv = argv + ["--exr", r4.EXR_DIR]
    r4.main(argv)
    # mark the stage of the render selfcheck
    out = argv[argv.index("--out") + 1]
    sc_path = os.path.join(out, "selfcheck-render-A.json")
    rep = json.load(open(sc_path))
    rep["stage"] = ("round 5 (M0 1.2.1 clays: M0, M0p, M0x + the M0-pouf measurement clay; briefs/render-m0-new-camera-2026-11-03.md task 2; "
                    "framing_r5.py on framing_r4; 0 var2 tokens)")
    rep["round5"] = dict(pendant=PENDANT, pouf=POUF, floor_lamp_dx=FLOOR_LAMP_DX, rug=RUG, living_furniture=LIVING_FURNITURE)
    json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
