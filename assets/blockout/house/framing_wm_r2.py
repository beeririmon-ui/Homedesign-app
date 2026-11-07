#!/usr/bin/env python3
"""
Framing clay, WARM MODERN r2: the warm-modern living room at the M0 1.2 camera after master-designer's decisions WMC1-WMC5 on the r1 clay
(house plan 1.3.2 section 0א, style_shells_1_3_1.warm-modern.living + r1_decisions_1_3_2; data/slots/living-room.json 1.9.1
by_style.warm-modern; render-agent, 2026-11-07; 0 var2 tokens).

A copy of framing_wm_r1.py (r1 stays as it is, read only; this one writes only to framing/warm-modern-r2/), with:
  - WMC1: the curtain draws one way: no back stack; both panels in one front stack, Y 2.70-3.00 (X -2.28..-2.16), floor to the track;
  - WMC2: the planter at (-1.95, 0.42) (was -2.00, 0.47): the warm-modern pot d 42 x 35.5, the olive crown (filler) r 0.28, Z 0.70-1.65
    (X >= -2.23, Y <= 0.70); the trunk from the pot to 0.80;
  - WMC3: the rounded corner X -2.30 / Y 0 at radius 0.30 (was 0.15);
  - WMC4: the window bench 0.32 deep, X -2.30..-1.98 (was -1.90), Y 0.75-2.85, top 0.45;
  - WMC5: the dropped plaster band X -2.30..-2.05, underside 2.82, from the rounded corner to the front wall; the shadow-gap slot a real
    recess in it, X -2.26..-2.18, up to Z 2.88; the track inside at 2.86; the curtain's head hidden in the slot (drop ~285 to the floor);
    the 1 cm shadow gap to the 3.00 ceiling as in r1;
  - unchanged from r1: the glazing (Y 0.75-2.85, sill 0.45, head 2.70, 3 bays), the vase on the bench (-2.42, 1.35, 0.45), the basket
    (-1.62, 0.78) (the designer's lever (-1.55, 0.80) is reported, not applied), the magazine holder, the round-5b positions and light (ARC2).

  python3 framing_wm_r2.py --frames M0,M0p,M0x --res 3840 --samples 16 --pose-samples 10
Outputs: framing/warm-modern-r2/M0.png (overscan canvas 4072x2290), poses/M0p.png, poses/M0x.png, overlays/, selfcheck-render-A.json;
the index passes (npz) in the scratchpad for clay_checks_wm_r2.py.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "framing", "warm-modern-r2")
os.environ["FRAMING_R3_OUT"] = OUT                  # framing_r3 (imported by framing_r4) writes nowhere else
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402  (after bpy: the pip module registers it)
import numpy as np  # noqa: E402

import framing_r4 as r4  # noqa: E402

r3, fr, r2, bh, M = r4.r3, r4.fr, r4.r2, r4.bh, r4.M
bs, ba = r3.bs, r3.ba
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
r4.EXR_DIR = os.path.join(SCRATCH, "wm-r2-exr")
IDX_DIR = os.path.join(SCRATCH, "wm-r2-idx")
r4.OUT4 = OUT
PENDANT = dict(hang=(0.20, 1.72, 3.00), bottom=1.90, r=0.20, h=0.28)
ARMCHAIR_D = (-1.23 - (-1.27), 2.73 - 2.82)
FLOOR_LAMP_DX = -0.08
RUG = dict(x=(-1.45, 1.85), y=(0.72, 3.12))
LIVING_FURNITURE = {1: "sofa 220x92x78 (fixed-product)", 2: "coffee table 140x70 h38 (fixed-product)", 3: "armchair 72x78 h70 (fixed-product)"}
LIVING_FRAMES = ("M0", "M0p", "M0x")
# the warm-modern shell (house plan 1.3.2 style_shells_1_3_1.warm-modern.living + r1_decisions_1_3_2 WMC1-WMC5)
WM = dict(win=dict(a0=0.75, a1=2.85, z0=0.45, z1=2.70, mullions=(1.45, 2.15), sight=0.045, reveal=0.35),
          bench=dict(x=(-2.30, -1.98), y=(0.75, 2.85), base_top=0.37, top=0.45, slab_hex="#D8C8AE"),                    # WMC4
          corner=dict(c=(-2.30, 0.0), r=0.30), ceiling=dict(h=3.00, gap=0.01),                                          # WMC3
          band=dict(x=(-2.30, -2.05), z=2.82, slot_x=(-2.26, -2.18), slot_top=2.88, slot_y0=0.02),                      # WMC5
          track=dict(z=2.86, x=(-2.235, -2.205), y=(0.70, 3.00)),                                                       # WMC5
          stacks=dict(x=(-2.28, -2.16), y=((2.70, 3.00),), z=(0.005, 2.86)),                                           # WMC1 (one-way)
          planter=dict(c=(-1.95, 0.42), d=0.42, h=0.355, crown_r=0.28, crown_z=(0.70, 1.65), trunk_top=0.80),          # WMC2
          vase_dz=-0.30, basket=dict(c=(-1.62, 0.78), d=0.35, h=0.39), holder=dict(c=(-0.54, 2.52), w=0.32, d=0.22, h=0.40),
          planks_w=0.22)


# ---------------------------------------------------------------------------------------------------------------
# the window in the v4 living build: the config, before the build
# ---------------------------------------------------------------------------------------------------------------
_cfg0 = r3.b4.v4_config


def v4_config_wm(spec):
    cfg = _cfg0(spec)
    w = cfg["window"]
    W = WM["win"]
    w.update(a0=W["a0"], a1=W["a1"], z0=W["z0"], z1=W["z1"], mullion=W["mullions"][0], mullion_w=W["sight"], frame_w=W["sight"],
             glass_bottom_z=W["z0"] + W["sight"])
    cfg["cornice"] = None
    cfg["planks"]["w"] = WM["planks_w"]
    Pl = WM["planter"]
    p = dict(cfg["slots"]["planter"])
    # build_alts: pot = cyl(c, r, z0, z1); crown = ellipsoid(c, env.r, env.z0 + 0.15, env.z1); trunk to env.z0 + 0.25
    p.update(c=list(Pl["c"]), r=Pl["d"] / 2, z0=0.0, z1=Pl["h"],
             envelope=dict(r=Pl["crown_r"], z0=Pl["crown_z"][0] - 0.15, z1=Pl["crown_z"][1]),
             note="warm modern r2 (WMC2): pot d 42 x 35.5 at (-1.95, 0.42); olive crown r 0.28, Z 0.70-1.65")
    cfg["slots"]["planter"] = p
    return cfg


r3.b4.v4_config = v4_config_wm


# ---------------------------------------------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------------------------------------------
def prism(name, pts, z0, z1, mat, pidx, coll="shell"):
    me = bpy.data.meshes.new(name)
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [list(range(n)), list(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    col = bpy.data.collections.get(coll) or bpy.context.scene.collection
    col.objects.link(ob)
    ob.data.materials.append(mat)
    ob.pass_index = pidx
    return ob


def v8_fixes(R):
    """round 5b, unchanged: pendant 1.90, armchair delta, floor lamp proxies moved (not shown), rug 330 x 240"""
    notes = []
    r3.kill_group(R, "living/pendant")
    z0, z1 = PENDANT["bottom"], PENDANT["bottom"] + PENDANT["h"]
    c = PENDANT["hang"][:2]
    pend = r3.ell("lv_pend_r5", c, PENDANT["r"], z0, z1, M["curtain"])
    cord = r3.cyl("lv_pcord_r5", c, 0.004, z1, PENDANT["hang"][2], M["holder"], 12)
    r3.reg(R, "living/pendant", [pend], "living", src=f"V7Q7 b: 40 x 28 pumpkin, shade bottom {z0}")
    r3.reg(R, "living/pendant-cord", [cord], "living", src="the pendant cord, registered apart")
    L = r2.LAMPS.get("living/pendant")
    if L:
        L["glow"] = [(pend, r2.GLOW)]
        L["orig"] = {pend.name: pend.data.materials[0]}
    table_top = 0.38
    e_old, d_old, d_new = 30.0, 2.20 - table_top, z0 - table_top
    r3.lamp_lights_at("living/pendant", [r2.mk_light("lv_pend_L5", "AREA", (c[0], c[1], z0 - 0.005), round(e_old * (d_new / d_old) ** 2, 1), size=0.30)])
    r3.set_hidden([pend, cord], True)
    notes.append(f"living/pendant: shade bottom {z0} (as round 5b)")
    arm = bpy.data.objects.get("armchair")
    if arm is None:
        raise SystemExit("warm modern r1: no 'armchair' root object in the scene")
    arm.location = (arm.location.x + ARMCHAIR_D[0], arm.location.y + ARMCHAIR_D[1], arm.location.z)
    notes.append(f"armchair: root -> {tuple(round(x, 3) for x in arm.location)} (house plan 1.2.2 (-1.23, 2.73); WM-F1: the Nordic geometry)")
    r3.move(R, "living/floor-lamp", dx=FLOOR_LAMP_DX)
    r3.kill_group(R, "living/rug")
    rug = r3.bx("lv_rug_r5", RUG["x"][0], RUG["x"][1], RUG["y"][0], RUG["y"][1], 0.0, 0.012, M["rug"])
    r3.reg(R, "living/rug", [rug], "living", src="house plan 1.2.2: X -1.45..1.85, Y 0.72-3.12 (330 x 240)")
    r3.set_hidden([rug], True)
    notes.append("living/rug: 330 x 240 (as round 5b)")
    return notes


def wm_fixes(R):
    notes = []
    W = WM["win"]
    xl = -2.30
    n0, n1 = W["reveal"], W["reveal"] + 0.07
    # the window: sashes and the sill board out (fixed steel glazing; the bench is the sill), the second mullion in
    gone = [o for o in bpy.data.objects if o.name.startswith(("win_sash", "win_sill"))]
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    mul = bpy.data.objects.get("win_mullion")
    mm = mul.data.materials[0] if mul is not None else M["moulding"]
    m2 = W["mullions"][1]
    bs.box("win_mullion_2", xl - n1, xl - n0, m2 - W["sight"] / 2, m2 + W["sight"] / 2, W["z0"] + W["sight"], W["z1"] - W["sight"], mm, "window",
           pidx=ba.SHELL_IDX["window"])
    notes.append(f"W-living: Y {W['a0']}-{W['a1']}, sill {W['z0']}, head {W['z1']}; mullions at Y {W['mullions']} (3 bays of 0.70), sight lines "
                 f"{W['sight']}; {len(gone)} sash / sill-board objects removed")
    # the bench (plaster base + limestone slab, the slab carried into the reveal to the frame)
    B = WM["bench"]
    lime = fr.mat_cache("limestone_wm", B["slab_hex"], 0.85)
    b_base = bs.box("wm_bench_base", B["x"][0], B["x"][1], B["y"][0], B["y"][1], 0.0, B["base_top"], M["wall"], "shell", pidx=ba.SHELL_IDX["left-wall"])
    b_slab = bs.box("wm_bench_slab", B["x"][0], B["x"][1], B["y"][0], B["y"][1], B["base_top"], B["top"], lime, "shell", pidx=ba.SHELL_IDX["left-wall"])
    b_rev = bs.box("wm_bench_slab_reveal", xl - n0, xl, W["a0"], W["a1"], B["top"] - 0.025, B["top"], lime, "shell", pidx=ba.SHELL_IDX["left-wall"])
    fr.reg("living/window-bench", [b_base, b_slab, b_rev], "living", kind="architecture")
    notes.append(f"window bench X {B['x']}, Y {B['y']}, plaster base to {B['base_top']}, limestone slab {B['slab_hex']} to {B['top']}; slab into the reveal")
    # the rounded corner X -2.30 / Y 0 (plaster, r 0.15, floor to ceiling)
    cx, cy = WM["corner"]["c"]
    r = WM["corner"]["r"]
    arc = [(cx + r + r * math.cos(math.radians(t)), cy + r + r * math.sin(math.radians(t))) for t in np.linspace(-90, -180, 41)]
    pts = [(cx, cy)] + arc
    corner = prism("wm_corner_r30", pts, -0.002, WM["ceiling"]["h"], M["wall"], ba.SHELL_IDX["left-wall"])
    fr.reg("living/rounded-corner", [corner], "living", kind="architecture")
    notes.append(f"corner ({cx}, {cy}) rounded, r {r}, plaster, floor to ceiling")
    # the ceiling shadow gap (1 cm) on the four walls; the cornice is not built (cfg)
    spec = json.load(open(r3.b4.SPEC_PATH))
    rm = spec["room"]
    x0_, x1_, y0_, y1_, h = rm["x_left"], rm["x_right"], rm["y_back"], rm["y_front"], WM["ceiling"]["h"]
    g = WM["ceiling"]["gap"]
    sg = M["shadow_gap"]
    gaps = [bs.box("wm_cgap_back", x0_, x1_, y0_, y0_ + 0.0015, h - g, h - 0.0005, sg, "shell", pidx=ba.SHELL_IDX["back-wall"]),
            bs.box("wm_cgap_left", x0_, x0_ + 0.0015, y0_, y1_, h - g, h - 0.0005, sg, "shell", pidx=ba.SHELL_IDX["left-wall"]),
            bs.box("wm_cgap_right", x1_ - 0.0015, x1_, y0_, y1_, h - g, h - 0.0005, sg, "shell", pidx=ba.SHELL_IDX["right-wall"]),
            bs.box("wm_cgap_front", x0_, x1_, y1_ - 0.0015, y1_, h - g, h - 0.0005, sg, "shell", pidx=ba.SHELL_IDX["front-wall"])]
    notes.append(f"ceiling {h} with a {g * 100:.0f} cm shadow gap on the four walls; no cornice")
    # WMC5: the dropped band X -2.30..-2.05, underside 2.82, from the rounded corner to the front wall, with a real slot recess
    # X -2.26..-2.18 up to 2.88 (the band in three pieces: either side of the slot to the ceiling, and above the slot from 2.88)
    Bd, T = WM["band"], WM["track"]
    zc = h - 0.0005
    band = [bs.box("wm_band_wall_side", Bd["x"][0], Bd["slot_x"][0], y0_, y1_, Bd["z"], zc, M["wall"], "shell", pidx=ba.SHELL_IDX["left-wall"]),
            bs.box("wm_band_room_side", Bd["slot_x"][1], Bd["x"][1], y0_, y1_, Bd["z"], zc, M["wall"], "shell", pidx=ba.SHELL_IDX["left-wall"]),
            bs.box("wm_band_over_slot", Bd["slot_x"][0], Bd["slot_x"][1], y0_, Bd["slot_y0"], Bd["z"], zc, M["wall"], "shell",
                   pidx=ba.SHELL_IDX["left-wall"]),
            bs.box("wm_band_slot_top", Bd["slot_x"][0], Bd["slot_x"][1], Bd["slot_y0"], y1_, Bd["slot_top"], zc, M["wall"], "shell",
                   pidx=ba.SHELL_IDX["left-wall"])]
    slot_dark = bs.box("wm_slot_shadow", Bd["slot_x"][0], Bd["slot_x"][1], Bd["slot_y0"], y1_, Bd["slot_top"] - 0.004, Bd["slot_top"], sg, "shell",
                       pidx=ba.SHELL_IDX["left-wall"])
    rail = bs.box("wm_track_rail", T["x"][0], T["x"][1], T["y"][0], T["y"][1], T["z"] - 0.005, T["z"] + 0.005, M["holder"], "shell",
                  pidx=ba.SHELL_IDX["left-wall"])
    fr.reg("living/curtain-track", band + [slot_dark, rail], "living", kind="architecture")
    notes.append(f"WMC5: the band X {Bd['x']} underside {Bd['z']} to the ceiling, Y {y0_}-{y1_} (through the rounded corner to the front wall); "
                 f"the slot recess X {Bd['slot_x']} up to {Bd['slot_top']} from Y {Bd['slot_y0']}; the track X {T['x']} at {T['z']}, Y {T['y']}")
    # WMC1: one front stack (both panels), Y 2.70-3.00, from the floor to the track (the head hidden in the slot)
    r3.kill_group(R, "living/curtains")
    S_ = WM["stacks"]
    st = [r3.bx(f"wm_curtain_{i}", S_["x"][0], S_["x"][1], ya, yb, S_["z"][0], S_["z"][1], M["curtain"]) for i, (ya, yb) in enumerate(S_["y"])]
    r3.reg(R, "living/curtains", st, "living", src=f"warm modern r2 (WMC1): one front stack Y {S_['y']}, X {S_['x']}, Z {S_['z']} (slots 1.9.1)")
    r3.set_hidden(st, True)
    notes.append(f"WMC1 curtains: one stack Y {S_['y']} X {S_['x']} Z {S_['z']} (drop {round((S_['z'][1] - S_['z'][0]) * 100)} cm)")
    # the vase on the bench
    nv = r3.move(R, "living/vase", dz=WM["vase_dz"])
    notes.append(f"living/vase: {nv} objects moved {WM['vase_dz']} in Z: base (-2.42, 1.35, 0.45), body to 0.76, branches to 1.05")
    # the basket and the magazine holder
    r3.kill_group(R, "living/basket")
    Bk = WM["basket"]
    bk = r3.cyl("wm_basket", Bk["c"], Bk["d"] / 2, 0.0, Bk["h"], M["textile"])
    r3.reg(R, "living/basket", [bk], "living", src=f"warm modern: ({Bk['c']}) d {Bk['d']} h {Bk['h']} (slots 1.9 basket)")
    r3.set_hidden([bk], True)
    r3.kill_group(R, "living/magazine-holder")
    Hd = WM["holder"]
    hd = r3.bx("wm_holder", Hd["c"][0] - Hd["w"] / 2, Hd["c"][0] + Hd["w"] / 2, Hd["c"][1] - Hd["d"] / 2, Hd["c"][1] + Hd["d"] / 2, 0.0, Hd["h"], M["textile"])
    r3.reg(R, "living/magazine-holder", [hd], "living", src=f"slots 1.8: ({Hd['c']}) {Hd['w']} x {Hd['d']} x {Hd['h']}")
    r3.set_hidden([hd], True)
    notes.append(f"basket ({Bk['c']}) d {Bk['d']} h {Bk['h']}; magazine holder ({Hd['c']}) {Hd['w']} x {Hd['d']} x {Hd['h']}")
    return notes


_v7 = r4.v7_fixes


def v7_plus(R):
    return _v7(R) + v8_fixes(R) + wm_fixes(R)


r4.v7_fixes = v7_plus

_names0 = r2.names_by_pidx


def names_by_pidx_wm(S):
    names = _names0(S)
    for pidx, nm in LIVING_FURNITURE.items():
        names.setdefault(pidx, (nm, "furniture"))
    return names


r2.names_by_pidx = names_by_pidx_wm

# the index pass of every frame kept (npz) for the clay checks
_render0 = fr.render
LAST = {}


def render_keep(path, tmp, res, samples, ao=0.30, passes=True, exposure=None):
    out = _render0(path, tmp, res, samples, ao=ao, passes=passes) if exposure is None else _render0(path, tmp, res, samples, ao=ao, passes=passes, exposure=exposure)
    if out is not None:
        LAST["idx"] = out[1]
        LAST["depth"] = out[0]
    return out


fr.render = render_keep
_run0 = r3.run_frame


def run_frame_keep(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, rep, cfg):
    Rr = _run0(fid, fplan, S, R, slots, cams, plan, prop, tmp, a, rep, cfg)
    os.makedirs(IDX_DIR, exist_ok=True)
    names = {int(k): list(v) for k, v in r2.names_by_pidx(S).items()}
    np.savez_compressed(os.path.join(IDX_DIR, f"{fid}.npz"), idx=LAST.get("idx"), depth=LAST.get("depth"))
    json.dump(dict(names=names, shell_idx=dict(ba.SHELL_IDX)), open(os.path.join(IDX_DIR, f"{fid}-names.json"), "w"))
    return Rr


r3.run_frame = run_frame_keep

_wp0 = r3.wall_patches


def wall_patches_wm(fid, cam, C, path):
    out = _wp0(fid, cam, C, path)
    if fid in LIVING_FRAMES:
        pts = {"bible18_back_wall_by_corner_L90_94": (-1.75, 0.0, 1.60), "bible18_window_wall_L80_88": (-2.30, 0.30, 1.60),
               "back_wall_behind_art_centre": (0.20, 0.0, 1.95), "back_wall_right_end_L82_86": (1.85, 0.0, 1.60),
               "corner_line_top": (-2.30, 0.0, 2.95), "bench_slab_mid": (-2.14, 1.80, 0.45)}
        for k, (x, y, z) in pts.items():
            u, v = fr.U(cam, x, y, z), fr.V(cam, x, y, z)
            if 0.02 < u < 0.98 and 0.02 < v < 0.98:
                out[k] = dict(r3.patch_L(path, u, v), xyz=[x, y, z])
            else:
                out[k] = dict(u=round(u, 3), v=round(v, 3), xyz=[x, y, z], note="outside the frame")
    return out


r3.wall_patches = wall_patches_wm


def main(argv):
    if "--plan" not in argv:
        argv = argv + ["--plan", os.path.join(OUT, "plan.json")]
    if "--out" not in argv:
        argv = argv + ["--out", OUT]
    if "--exr" not in argv:
        argv = argv + ["--exr", r4.EXR_DIR]
    r4.main(argv)
    out = argv[argv.index("--out") + 1]
    sc_path = os.path.join(out, "selfcheck-render-A.json")
    rep = json.load(open(sc_path))
    rep["stage"] = ("warm modern r2 (house plan 1.3.2 section 0א WMC1-WMC5, slots 1.9.1 by_style.warm-modern, Bible warm-modern 1.0; M0 1.2 camera; "
                    "framing_wm_r2.py on framing_r4; 0 var2 tokens)")
    rep["warm_modern_r2"] = dict(WM, pendant=PENDANT, armchair_delta=ARMCHAIR_D, rug=RUG, living_furniture=LIVING_FURNITURE)
    json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
