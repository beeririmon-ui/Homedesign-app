#!/usr/bin/env python3
"""
framing_wm_hall_2026_11_18.py: the junction clay of the warm-modern arrival v2 (render-agent, 2026-11-18). 0 var2 tokens.
Brief: briefs/wm-arrival-stills-v2-2026-11-18.md, step 1. Spec: master-designer docs/proposals/wm-tour-route-2026-11-17.md 2.2 and 12.0-12.4.

The scene is framing_wm_door_final.py exactly (imported, not edited), plus:
  a. the walnut bench (route 2.2): X 0.81-1.21 (0.40 deep, in front of the hall stone panel), Y 6.70-7.50 (0.80 long), seat top Z 0.45,
     a 5 cm seat slab on two solid 5 cm end panels flush with its ends, open between them, every edge eased r 1.5 cm; walnut #6B4A33 matte;
  b. the walnut console (route 2.2): X 2.55-3.35, Y 6.35-6.70 (against the front wall, right of the living-room opening), top Z 0.80,
     a 5 cm top with its two front corners rounded r 6 cm and eased edges, on two elliptical drum bases 22 x 16 cm in plan, set 8 cm in
     from the ends and centred in the depth;
  c. the two new junction views at HX (2.462, 8.15, 1.20) on the 3:2 tall canvas, shift 0.50 / 0.50 (route 12.3, 12.4): HC (yaw 180) and
     HC130 (yaw 130), the front door leaf CLOSED (route 12.0: closed it is out of both frames);
  d. route 12.0: the dark clay object at HC's left margin (X 3.49, Y 9.62) is the bath window of the court wall (W-bath: bronze frame,
     sash, fluted glass, sill, reveal; X 3.40-4.30), modelled 0.15-0.20 m into the hall's corner (X 3.40-3.60, Y 9.60-9.80). In HC and
     HC130 it is hidden, and the two holes it leaves in the hall's plaster are closed by two plaster patches (house wall, pass index 100):
     X 3.60-3.66 / Y 9.60-9.80 and X 3.45-3.60 / Y 9.80-9.95, both Z 0.975-2.15. Found with `--find`.
  e. the corridor portal (O-hall-corridor, G-C3) as the corridor document's warm-modern finish has it (wm-corridor-architecture-2026-11-14.md
     table 1: "the same geometry, lining 4 cm, head at 2.62; walnut in the reveals and the soffit, no casing"): in HC and HC130 the Nordic
     oak casings (cportal_ca / cb / ch, 10 cm, 4 cm proud) are hidden and the oak linings (cportal_a / b / h, which stood 10 cm proud of the
     hall wall, Y 9.70) are replaced by walnut linings flush with the plaster, Y 9.80-9.95 (route 12.3: "lined in walnut for the full
     wall depth, flush with the plaster, no casing or architrave"). Found with the corridor listing in the scratchpad.
HT, HD and HDx are rendered again with the bench (and the console) and the leaf open, exactly as in framing_wm_door_final.py otherwise.
The lighting, exposure (0.75), samples and passes are those of framing_wm_door_final.py.

  python3 framing_wm_hall_2026_11_18.py --find                      # what stands at (3.49, 9.62)
  python3 framing_wm_hall_2026_11_18.py --frames HC,HC130,HT,HD,HDx
  python3 framing_wm_hall_2026_11_18.py --frames HC --res 832 --samples 4 --out /tmp/x     # a quick look
"""
import argparse
import json
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_MY_ARGV = sys.argv[1:]
sys.argv = [sys.argv[0]]

import framing_wm_door_final as FF  # noqa: E402  (imports framing_wm_door and the whole house; not edited)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

D, E, W4, fr, bs = FF.D, FF.E, FF.W4, FF.fr, FF.bs

OUT = os.path.join(HERE, "framing", "wm-hall-2026-11-18")
SCRATCH = os.environ.get("WM_HALL_SCRATCH") or os.path.join(W4.SCRATCH, "render-arrival", "clay", "scratch")
FF.SCRATCH = E.SCRATCH = D.SCRATCH = SCRATCH

HX = (2.462, 8.15, 1.20)
BENCH = dict(x=(0.81, 1.21), y=(6.70, 7.50), seat=0.45, slab=0.05, panel=0.05, r=0.015)
CONSOLE = dict(x=(2.55, 3.35), y=(6.35, 6.70), top=0.80, slab=0.05, r_front=0.06, ease=0.008, drum=(0.22, 0.16), inset=0.08)
DARK = (3.49, 9.62)
PX = dict(bench=740, console=741)
NEW_IDS = {100: "walnut bench (route 2.2; plan B under F3, fixed)", 101: "walnut console (route 2.2; plan B under F3, fixed)"}
NEW_PAL = {100: (150, 95, 60), 101: (190, 120, 70)}


def wbb(ob):
    return FF.wbb(ob)


def bench():
    walnut = fr.mat_cache("walnut_wm", "#6B4A33", 0.85)
    B = BENCH
    (x0, x1), (y0, y1) = B["x"], B["y"]
    zs = B["seat"] - B["slab"]
    t = B["panel"]
    obs = [FF.bx("bench_seat_wm", x0, x1, y0, y1, zs, B["seat"], walnut, PX["bench"], group="framing", bevel=B["r"]),
           FF.bx("bench_end_a_wm", x0, x1, y0, y0 + t, 0.0, zs + 0.002, walnut, PX["bench"], group="framing", bevel=B["r"]),
           FF.bx("bench_end_b_wm", x0, x1, y1 - t, y1, 0.0, zs + 0.002, walnut, PX["bench"], group="framing", bevel=B["r"])]
    return obs, [f"bench: walnut #6B4A33, X {x0}-{x1}, Y {y0}-{y1}, seat slab Z {zs:.2f}-{B['seat']} ({B['slab'] * 100:.0f} cm), end panels "
                 f"{t * 100:.0f} cm at Y {y0}-{y0 + t:.2f} and {y1 - t:.2f}-{y1}, Z 0-{zs:.2f}, open between them, edges r {B['r'] * 100:.1f} cm"]


def rounded_plan(x0, x1, y0, y1, r, n=10):
    """Plan outline of the console top: the two corners at y1 (the front) rounded r; the back corners (y0, on the wall) square."""
    pts = [(x0, y0), (x1, y0)]
    for k in range(n + 1):                       # front right corner, centre (x1 - r, y1 - r), angle 0 -> 90
        a = math.radians(90.0 * k / n)
        pts.append((x1 - r + r * math.cos(a), y1 - r + r * math.sin(a)))
    for k in range(n + 1):                       # front left corner, centre (x0 + r, y1 - r), angle 90 -> 180
        a = math.radians(90.0 + 90.0 * k / n)
        pts.append((x0 + r + r * math.cos(a), y1 - r + r * math.sin(a)))
    return pts


def prism(name, pts, z0, z1, mat, pidx, ease=0.0):
    me = bpy.data.meshes.new(name)
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bs.coll("framing").objects.link(ob)
    ob.data.materials.append(mat)
    ob.pass_index = pidx
    for p in me.polygons:
        p.use_smooth = False
    if ease > 0:
        bv = ob.modifiers.new("ease", "BEVEL")
        bv.width, bv.segments, bv.limit_method, bv.angle_limit = ease, 3, "ANGLE", math.radians(60)
    return ob


def console():
    walnut = fr.mat_cache("walnut_wm", "#6B4A33", 0.85)
    C = CONSOLE
    (x0, x1), (y0, y1) = C["x"], C["y"]
    zt = C["top"] - C["slab"]
    top = prism("console_top_wm", rounded_plan(x0, x1, y0, y1, C["r_front"]), zt, C["top"], walnut, PX["console"], ease=C["ease"])
    a, b = C["drum"][0] / 2, C["drum"][1] / 2
    yc = (y0 + y1) / 2
    drums = []
    for nm, xc in (("console_drum_l_wm", x0 + C["inset"] + a), ("console_drum_r_wm", x1 - C["inset"] - a)):
        pts = [(xc + a * math.cos(2 * math.pi * k / 48), yc + b * math.sin(2 * math.pi * k / 48)) for k in range(48)]
        drums.append(prism(nm, pts, 0.0, zt + 0.002, walnut, PX["console"]))
    return [top] + drums, [f"console: walnut #6B4A33, top X {x0}-{x1}, Y {y0}-{y1}, Z {zt:.2f}-{C['top']} ({C['slab'] * 100:.0f} cm), front corners "
                           f"r {C['r_front'] * 100:.0f} cm, edges eased {C['ease'] * 1000:.0f} mm; two elliptical drums {C['drum'][0] * 100:.0f} x "
                           f"{C['drum'][1] * 100:.0f} cm, X {x0 + C['inset']:.2f}-{x0 + C['inset'] + 2 * a:.2f} and {x1 - C['inset'] - 2 * a:.2f}-"
                           f"{x1 - C['inset']:.2f}, Y {yc - b:.3f}-{yc + b:.3f}, Z 0-{zt:.2f}"]


def near(xy, r=0.25):
    out = []
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        lo, hi = wbb(ob)
        dx = max(lo[0] - xy[0], 0, xy[0] - hi[0])
        dy = max(lo[1] - xy[1], 0, xy[1] - hi[1])
        if math.hypot(dx, dy) <= r:
            out.append(dict(name=ob.name, pass_index=int(ob.pass_index), hide_render=bool(ob.hide_render), lo=[round(v, 3) for v in lo],
                            hi=[round(v, 3) for v in hi], mat=[m.name for m in ob.data.materials if m]))
    return out


def portal_wm():
    """Route 12.3 / corridor doc table 1: walnut linings flush with the hall plaster, no casing. Returns (hide in HC/HC130, show in HC/HC130)."""
    walnut = fr.mat_cache("walnut_wm", "#6B4A33", 0.85)
    old = [bpy.data.objects[n] for n in ("cportal_a", "cportal_b", "cportal_h", "cportal_ca", "cportal_cb", "cportal_ch")]
    new = []
    for o in old[:3]:
        lo, hi = wbb(o)
        nb = FF.bx(o.name + "_wm", lo[0], hi[0], 9.80, hi[1], lo[2], hi[2], walnut, o.pass_index, group="framing")
        nb.hide_render = True
        new.append(nb)
    return old, new


def frames():
    F, alias, L = D.frames()
    want = {k: dict(F[k]) for k in ("HT", "HD", "HDx")}
    for k, yaw in (("HC", 180.0), ("HC130", 130.0)):
        want[k] = dict(loc=[float(v) for v in HX], yaw=yaw, u0=0.50, v0=0.50, leaf="closed", canvas="tall", s=None)
    return want


def classify(idx, depth, normal, f, cv, IM):
    out, P = FF.classify_final(idx, depth, normal, f, cv, IM)
    out[idx == PX["bench"]] = 100
    out[idx == PX["console"]] = 101
    return out, P


def args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--find", action="store_true")
    ap.add_argument("--frames", default="HC,HC130,HT,HD,HDx")
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--keep-dark", action="store_true", help="do not hide the dark object at (3.49, 9.62) in HC / HC130")
    return ap.parse_args(argv)


def main(argv):
    a = args(argv)
    fa = FF.args([])                               # the final clay's calibrated defaults: sun 8, 22 W, slot 20, exposure 0.75
    fa.res = a.res or D.REG_CANVAS[0]
    os.makedirs(SCRATCH, exist_ok=True)
    W4.r4.EXR_DIR = os.path.join(SCRATCH, "exr")
    t0 = time.time()
    S, R, cfg, notes = FF.build(fa)
    if a.find:
        D.set_leaf("closed")
        print(json.dumps(dict(near_dark=near(DARK, 0.30)), indent=1))
        return
    E.IDS.update(NEW_IDS)
    D.IDS.update(NEW_IDS)
    E.PALETTE.update(NEW_PAL)
    E.ALLOWED.update(NEW_IDS)
    bo, bn = bench()
    co, cn = console()
    dark = [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("W-bath_") or o.name == "fluted_glass2")]
    assert all(wbb(o)[0][0] >= 3.39 and wbb(o)[1][0] <= 4.31 and wbb(o)[0][1] >= 9.59 and wbb(o)[1][1] <= 10.0 for o in dark), [o.name for o in dark]
    wall = FF.M["wall"]
    patches = [FF.bx("hall_patch_bathwin_a", 3.60, 3.66, 9.60, 9.80, 0.975, 2.15, wall, 100),
               FF.bx("hall_patch_bathwin_b", 3.45, 3.60, 9.80, 9.95, 0.975, 2.15, wall, 100)]
    for p in patches:
        p.hide_render = True
    portal_old, portal_new = portal_wm()
    dark_rec = [dict(name=o.name, lo=[round(v, 3) for v in wbb(o)[0]], hi=[round(v, 3) for v in wbb(o)[1]]) for o in dark]
    bpy.context.view_layer.update()
    IM = D.index_map_door()
    E.classify = classify
    E.edges_of = FF.edges_final
    F = frames()
    want = a.frames.split(",")
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="wm-hall-")
    cam = S["cam"]
    from PIL import Image
    recs = {}
    for fid in want:
        f = F[fid]
        t1 = time.time()
        hidden = []
        if fid in ("HC", "HC130") and not a.keep_dark:
            for ob in dark:
                ob.hide_render = True
                hidden.append(ob.name)
            for p in patches:
                p.hide_render = False
            for o in portal_old:
                o.hide_render = True
            for o in portal_new:
                o.hide_render = False
        D.set_leaf(f["leaf"])
        canvas = D.REG_CANVAS if f["canvas"] == "reg" else D.TALL_CANVAS
        cv = D.set_view(cam, f, a.res or canvas[0])
        png = os.path.join(a.out, fid + ".png")
        depth, idx, normal = D.geometry_pass(tmp, cv["W"], cv["H"])
        FF.render_beauty(png, os.path.join(tmp, "p"), cv["W"], cv["H"], a.samples, 0.30, fa.door_exposure,
                         keep_exr=os.path.join(SCRATCH, "beauty", fid + ".exr"))
        for nm in ("g", fid):
            q = os.path.join(W4.r4.EXR_DIR, nm + ".exr")
            if os.path.exists(q):
                os.remove(q)
        Image.open(png).save(png, optimize=True)
        rec = dict(frame=fid, camera=dict(loc=f["loc"], yaw=f["yaw"], lens=24, u0=f["u0"], v0=f["v0"]), leaf=f["leaf"], canvas=cv,
                   samples=a.samples, exposure=fa.door_exposure, hidden_for_this_frame=hidden)
        rec.update(E.save_passes(fid, png, depth, idx, normal, f, cv, IM, a.out))
        for ob_name in hidden:
            bpy.data.objects[ob_name].hide_render = False
        for p in patches:
            p.hide_render = True
        if fid in ("HC", "HC130") and not a.keep_dark:
            for o in portal_old:
                o.hide_render = False
            for o in portal_new:
                o.hide_render = True
        rec["runtime_s"] = round(time.time() - t1)
        recs[fid] = rec
        print("FRAME", fid, rec["runtime_s"], "s; not allowed", rec["not_allowed_px"], flush=True)
    meta = dict(stage="warm-modern junction clay v2 (route 2.2, 12.0-12.4), render-agent 2026-11-18, briefs/wm-arrival-stills-v2-2026-11-18.md step 1; "
                      "framing_wm_hall_2026_11_18.py on framing_wm_door_final.py (not edited); 0 var2 tokens",
                date=time.strftime("%Y-%m-%d"), added=bn + cn, dark_object_hidden_in_HC_HC130=dark_rec, portal_in_HC_HC130="oak casings cportal_ca/cb/ch hidden; linings cportal_a/b/h replaced by walnut boxes at Y 9.80-9.95 (flush), same X and Z", plaster_patches_in_HC_HC130=["X 3.60-3.66, Y 9.60-9.80, Z 0.975-2.15", "X 3.45-3.60, Y 9.80-9.95, Z 0.975-2.15"], bench=BENCH, console=CONSOLE,
                new_ids=NEW_IDS, ids={int(k): v for k, v in E.IDS.items()}, render="as framing_wm_door_final.py: Cycles CPU, OIDN, AgX Medium High "
                "Contrast, exposure 0.75, sun 8, slot 20, lamp 22 W (court only)", frames=recs, build_and_render_s=round(time.time() - t0))
    mp = os.path.join(a.out, "clay-meta.json")
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    old_frames = old.get("frames", {})
    old_frames.update(recs)
    meta["frames"] = old_frames
    for r in meta["frames"].values():
        r.pop("npz", None)
    json.dump(meta, open(mp, "w"), indent=1, ensure_ascii=False, default=str)
    print("DONE", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main(_MY_ARGV)
