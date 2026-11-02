#!/usr/bin/env python3
"""
Framing clay, ROUND 4 (v7 wow pass, docs/render-wow-pass-2026-11-02.md section 4.1; transitions poses, docs/transitions-plan-2026-11-02.md
section 3; 2026-11-02). 0 var2 credits. Round 3 (framing/round3/) is read only: this file imports framing_r3 and changes nothing there.

What round 4 adds to round 3:
  - the v7 clay changes of the prompt headers (assets/prompts/recipe-v5.nordic/*-v7.txt): M0 without wall-decor and floor-lamp (and
    without the floor-lamp light), the accent pair as two 12 cm cubes; H0 / C0 without the umbrella stand; K-boy / K-girl without the
    roman blind; W0 planter D38 x H34 + plant to 1.30, no bookends; D1 lantern 50 wide, flat, bottom 1.50 (75 over the table);
  - the 12 transition poses (H0x, H0e, M0p, M0x, PD-35, W0-in, S1', R2m, K-boy-0, K-girl-0, CB-0, MB-in) from plan.json -> poses;
  - the composite (after the AO multiply, before the view transform) saved as a half-float EXR per frame, so the exposure (+1 stop and
    the per-frame trim to the reference wall L 85-90), the bath white balance and the glass roll-off are set in post by tone_r4.py
    without a re-render (exposure is a scene-linear multiply before AgX: identical to rendering at that exposure).

  python3 framing_r4.py --group A --frames all --res 3840 --samples 16            # living boost 1.0: M0, D1, D2, MB0, kids, bath, W0 + poses
  python3 framing_r4.py --group B --frames all --res 3840 --samples 16 --living-boost 6.0   # H0, C0 + H0x, H0e, S1', R2m, MB-in
  python3 framing_r4.py --group B --frames H0 --res 1280 --samples 8 --out /tmp/x --exr /tmp/x/exr     # smoke test
Outputs: framing/round4/<frame>.png (render exposure +1.35, before the post trim), poses/<pose>.png, overlays/, selfcheck-render-<group>.json,
EXRs in --exr (scratchpad by default; not in the repo).
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT4 = os.path.join(HERE, "framing", "round4")
os.environ["FRAMING_R3_OUT"] = OUT4                 # framing_r3 (and framing_r2 through it) never write into round3 from here
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import framing_r3 as r3  # noqa: E402

fr, r2, bh, M = r3.fr, r3.r2, r3.bh, r3.M
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
EXR_DIR = os.path.join(SCRATCH, "r4-exr")
RENDER_EXPOSURE = fr.EDIT_EXPOSURE + 1.0           # round 3 rendered at +0.35; round 4 renders at +1.35 (the post trim starts there)
GROUPS = {"A": ["M0", "D1", "B1", "MB0", "K-boy", "K-girl", "W0", "D2", "B2",
                "M0p", "M0x", "PD-35", "W0-in", "K-boy-0", "K-girl-0", "CB-0"],
          "B": ["H0", "C0", "H0x", "H0e", "S1prime", "R2m", "MB-in"]}


# ---------------------------------------------------------------------------------------------------------------
# EXR of the composite next to every render
# ---------------------------------------------------------------------------------------------------------------
_setup0 = fr.setup_comp
_render0 = fr.render


def setup_comp_r4(tmp, ao=0.30):
    _setup0(tmp, ao)
    nt = bpy.context.scene.node_tree
    comp = [n for n in nt.nodes if n.type == "COMPOSITE"][0]
    fo = [n for n in nt.nodes if n.type == "OUTPUT_FILE"][0]
    src = comp.inputs["Image"].links[0].from_socket
    fo.file_slots.new("Image_")
    slot = fo.file_slots[len(fo.file_slots) - 1]
    slot.use_node_format = False
    slot.format.file_format = "OPEN_EXR"
    slot.format.color_depth = "16"
    slot.format.exr_codec = "ZIP"
    nt.links.new(src, fo.inputs["Image_"])


def render_r4(path, tmp, res, samples, ao=0.30, passes=True, exposure=None):
    out = _render0(path, tmp, res, samples, ao=ao, passes=passes, exposure=RENDER_EXPOSURE if exposure is None else exposure)
    src = os.path.join(tmp, "Image_0001.exr")
    if os.path.exists(src):
        os.makedirs(EXR_DIR, exist_ok=True)
        shutil.copy(src, os.path.join(EXR_DIR, os.path.splitext(os.path.basename(path))[0] + ".exr"))
    return out


fr.setup_comp = setup_comp_r4
fr.render = render_r4

# ---------------------------------------------------------------------------------------------------------------
# overscan (motion-agent, docs/transitions-render-plan-2026-11-02.md "pan gap", via the coordinator 2026-11-02): every still in a
# pan of 21 deg or more gets about 3 % of the frame added on every side: same camera, same focal length in pixels, the 16:9 frame is
# the centre crop. 3840 x 2160 -> 4072 x 2290 (crop box x 116-3956, y 65-2225; 0.0302 / 0.0301 per side). The canvas stays 16:9 so the
# image model gets the aspect it renders; motion-agent's "16:9 + 6 % height" is the canvas cropped to the frame width.
# ---------------------------------------------------------------------------------------------------------------
OS_FRAMES = {"M0p", "M0x", "PD-35", "D1", "D2", "K-boy", "K-boy-0", "K-girl", "K-girl-0", "CB-0", "B1", "B2", "M0"}
OS_RES = (4072, 2290)
OS_K = OS_RES[0] / 3840.0
OS_STATE = dict(on=False, base_sw=None)
_sv0 = bh.set_view


def set_view_r4(cam, loc, yaw, u0=0.52, v0=0.46):
    _sv0(cam, loc, yaw, u0, v0)
    if OS_STATE["base_sw"] is None:
        OS_STATE["base_sw"] = cam.data.sensor_width
    k = OS_K if OS_STATE["on"] else 1.0
    cam.data.sensor_width = OS_STATE["base_sw"] * k
    cam.data.shift_x = cam.data.shift_x / k
    cam.data.shift_y = cam.data.shift_y / k
    bpy.context.view_layer.update()


bh.set_view = set_view_r4


# ---------------------------------------------------------------------------------------------------------------
# the v7 clay changes (geometry; visibility is per frame from plan.json)
# ---------------------------------------------------------------------------------------------------------------
def v7_fixes(R):
    notes = []
    O, Hd, T = M["obj"], M["holder"], M["textile"]
    # M0: accent pair = two 12 cm travertine cubes (wall-sconce-cj-travertine-cube-updown-12), plates at (-0.85, 0, 1.75) / (1.25, 0, 1.75)
    r3.kill_group(R, "living/accent-sconces")
    cubes = [r3.bx(f"lv_cube_r4_{i}", x - 0.06, x + 0.06, 0.0, 0.12, 1.69, 1.81, M["obj"], 0.004) for i, x in enumerate((-0.85, 1.25))]
    r3.reg(R, "living/accent-sconces", cubes, "living", src="m0-v7.txt b: travertine cube 12 x 12 x 12, x2, on the v4 plates (Z 1.75)")
    r3.lamp_off("living/accent-sconces")
    r2.lamp("living/accent-sconces", "living", "wall", [(o, r2.GLOW * 0.6) for o in cubes],
            [r2.mk_light(f"lv_cube_L{i}", "POINT", (x, 0.13, 1.75), 5.0, size=0.04) for i, x in enumerate((-0.85, 1.25))],
            "travertine cube pair 12 (m0-v7)")
    r3.set_hidden(cubes, True)
    notes.append("living/accent-sconces: two 12 cm cubes (was 8 x 16 blocks), lit (m0-v7.txt b)")
    # M0: floor lamp and wall decor out (product check 4): proxies stay hidden (not in plan.json), and the floor-lamp light is removed
    r3.lamp_off("living/floor-lamp")
    notes.append("living/floor-lamp: light sources removed (m0-v7.txt: no floor-lamp light); living/wall-decor not listed anywhere")
    # D1: the silk pumpkin lantern 50, flat, bottom 1.50 (75 over the table top 0.75)
    kd = "kitchen-dining"
    r3.kill_group(R, f"{kd}/dining-pendant")
    lan = r3.ell("dpend_r4", (4.60, 1.65), 0.25, 1.50, 1.80, M["curtain"])
    r3.reg(R, f"{kd}/dining-pendant", [lan, r3.cyl("dpend_r4c", (4.60, 1.65), 0.005, 1.80, 3.0, Hd, 12)], kd,
           src="d1-v7.txt: pendant-cj-silk-pumpkin-lantern 50 wide, flat (30 tall, height not published), bottom kept at 1.50")
    L = r2.LAMPS.get(f"{kd}/dining-pendant")
    if L:
        L["glow"] = [(lan, r2.GLOW)]
        L["orig"] = {lan.name: lan.data.materials[0]}
    notes.append("kitchen-dining/dining-pendant: 50 x 30 flat lantern (ellipsoid), bottom 1.50 (d1-v7.txt clay line)")
    # W0: planter D38 x H34 + the plant to 1.30 (filler), in the corner by the window at the data/slots/work.json position
    # (-1.95, 6.70) as in round 3 (the build_house proxy at (-0.20, 6.62) stood in the desk: fixed 2026-11-02 21:15); bookends out
    r3.kill_group(R, "work/planter")
    r3.reg(R, "work/planter", [r3.cyl("w_pot_r4", (-1.95, 6.70), 0.19, 0.0, 0.34, O),
                               r3.cyl("w_plant_r4", (-1.95, 6.70), 0.30, 0.34, 1.30, M["crown"])], "work",
           src="w0-v7.txt: planter-zendrop-seagrass-belly-38x34 (D38 x H34) + plant to about 1.30, centre (-1.95, 6.70) per data/slots/work.json")
    notes.append("work/planter: D38 x H34 + plant to 1.30; work/bookends not listed (removed)")
    return notes


# ---------------------------------------------------------------------------------------------------------------
# poses: cameras + per-pose plans folded into framing_r3's tables
# ---------------------------------------------------------------------------------------------------------------
def register_poses(rplan, cams):
    for pid, p in rplan["poses"].items():
        base = p["base"]
        room, _, slots_file = r3.FRAMES[base]
        r3.FRAMES[pid] = (room, "pose", slots_file)
        r3.HERO_WALL_PT[pid] = r3.HERO_WALL_PT[base]
        cams[pid] = dict(id=pid, room=cams[base]["room"], loc=list(p["loc"]), yaw=p["yaw"], u0=p["u0"], v0=p["v0"],
                         status=f"transition pose ({p['source']})", hero="")
        rplan["frames"][pid] = dict(placeholders=p["placeholders"], lamps=p["lamps"], also_visible=p["also_visible"], notes=p["source"])


def prebuild_generics(rplan, S, R, slots):
    """Build every generic proxy of every master frame once (apply_frame builds them only for the frame's own room), so a pose
    that sees another room (M0x -> dining, R2m -> boy / bath, MB-in -> corridor) shows them."""
    for fid in r3.ORDER:
        r3.apply_frame(fid, rplan["frames"][fid], S, R, slots)
    r2.lamps_set([])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(OUT4, "plan.json"))
    ap.add_argument("--group", default="A", choices=["A", "B"])
    ap.add_argument("--frames", default="all")
    ap.add_argument("--res", type=int, default=3840)
    ap.add_argument("--samples", type=int, default=36)
    ap.add_argument("--sky", type=float, default=7.0)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--living-boost", type=float, default=1.0)
    ap.add_argument("--hall-roof", type=float, default=1.6)
    ap.add_argument("--bath-window", type=float, default=4.5)
    ap.add_argument("--out", default=None)
    ap.add_argument("--exr", default=None)
    ap.add_argument("--no-overscan", action="store_true")
    ap.add_argument("--pose-samples", type=int, default=None, help="samples for the poses (default: --samples)")
    a, _ = ap.parse_known_args(argv)
    global EXR_DIR
    out = a.out or OUT4
    if a.exr:
        EXR_DIR = a.exr
    os.makedirs(os.path.join(out, "poses"), exist_ok=True)
    rplan = json.load(open(a.plan))
    for fid in r3.ORDER:
        f = rplan["frames"].setdefault(fid, {})
        f.setdefault("placeholders", []), f.setdefault("lamps", None), f.setdefault("also_visible", []), f.setdefault("notes", "")
    cams, plan_doc = r3.cameras_1_1()
    register_poses(rplan, cams)
    group = GROUPS[a.group]
    frames = group if a.frames == "all" else [f for f in group if f in a.frames.split(",")]
    slots = r3.load_slots()
    sc_path = os.path.join(out, f"selfcheck-render-{a.group}.json")
    rep = json.load(open(sc_path)) if os.path.exists(sc_path) else {}

    def save():
        json.dump(rep, open(sc_path, "w"), indent=2, ensure_ascii=False)

    t0 = time.time()
    r2.WARM = r3.WARM_R3
    prop = fr.load_prop()
    plan_path, plan0 = bh.load_plan()
    spec = json.load(open(r3.b4.SPEC_PATH))
    cfg = r3.b4.v4_config(spec)
    S, plan, notes, wl = r2.build_r2(plan0, cfg, a)
    R = r3.registry(S)
    notes["round3"] = r3.neutralise(S) + r3.living_vista(R) + r3.apply_fixes(S, R, slots, cube_lamp=rplan.get("hall_cube_lamp"))
    notes["round4"] = v7_fixes(R)
    notes["round3"] += r3.light_balance(a)
    bpy.context.view_layer.update()
    prebuild_generics(rplan, S, R, slots)
    rep.update(stage="round 4 (v7 clays + transition poses; docs/render-wow-pass-2026-11-02.md 4.1, docs/transitions-plan-2026-11-02.md 3)",
               date=time.strftime("%Y-%m-%d"), group=a.group, plan_version=plan0["version"], render_plan=os.path.relpath(a.plan, r3.REPO),
               render=f"{a.res}x{int(round(a.res * 9 / 16))}, {a.samples} samples, Cycles CPU seed 7, OIDN, AgX Medium High Contrast, "
                      f"render exposure +{RENDER_EXPOSURE} (round 3: +{fr.EDIT_EXPOSURE}); final exposure set in post by tone_r4.py from the EXR",
               light=f"round-3 light; living window x{a.living_boost}; hall roof x{a.hall_roof}; bath window x{a.bath_window}",
               build_notes=notes, build_s=round(time.time() - t0))
    save()
    tmp = tempfile.mkdtemp(prefix="framing-r4-")
    res0 = a.res
    for fid in frames:
        r3.set_out(os.path.join(out, "poses") if fid in rplan["poses"] else out)
        os_on = fid in OS_FRAMES and not a.no_overscan
        OS_STATE["on"] = os_on
        a.res = int(round(res0 * OS_K)) if os_on else res0
        smp0 = a.samples
        if fid in rplan["poses"] and a.pose_samples:
            a.samples = a.pose_samples
        R_ = r3.run_frame(fid, rplan["frames"][fid], S, R, slots, cams, plan, prop, tmp, a, rep, cfg)
        R_["samples"] = a.samples
        a.samples = smp0
        a.res = res0
        OS_STATE["on"] = False
        hres = int(round(res0 * 9 / 16))
        if os_on:
            W_, H_ = int(round(res0 * OS_K)), int(round(int(round(res0 * OS_K)) * 9 / 16))
            ox, oy = (W_ - res0) // 2, (H_ - hres) // 2
            R_["overscan"] = dict(on=True, canvas_px=[W_, H_], frame_px=[res0, hres], crop_box_px=[ox, oy, ox + res0, oy + hres],
                                  per_side_fraction_x=round(ox / res0, 4), per_side_fraction_y=round(oy / hres, 4),
                                  note="same camera and focal length in pixels; the 16:9 frame is the centre crop; uv in this selfcheck "
                                       "(boxes, patches) are fractions of the canvas")
        else:
            R_["overscan"] = dict(on=False, canvas_px=[res0, hres])
        R_["image"] = os.path.relpath(os.path.join(r3.OUT, f"{fid}.png"), os.path.join(HERE))
        R_["exr"] = os.path.join(EXR_DIR, f"{fid}.exr")
        R_["pose"] = fid in rplan["poses"]
        save()
        print("frame", fid, R_["runtime_s"], "s", "L", R_["mean_L"], flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    save()


if __name__ == "__main__":
    main(sys.argv[1:])
